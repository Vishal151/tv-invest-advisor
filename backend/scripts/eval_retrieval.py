"""
Retrieval evaluation benchmark.

Runs the golden Q&A dataset against the live retriever and reports Recall@K,
Precision@K, and MRR overall and per question-type. Use it as a reproducible
benchmark before/after retrieval changes, and as a regression check.

Usage:
    cd backend
    uv run scripts/eval_retrieval.py
    uv run scripts/eval_retrieval.py --k 1,3,5 --out eval/results/run.json
    uv run scripts/eval_retrieval.py --type noisy
    uv run scripts/eval_retrieval.py --ignore-threshold   # pure ranker, no distance filter

Requires the real corpus (not LLM_MOCK) and an ingested ChromaDB collection.
"""

# SQLite fix must be first
__import__("pysqlite3")
import sys  # noqa: E402

sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

import argparse  # noqa: E402
import asyncio  # noqa: E402
import json  # noqa: E402
import logging  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings  # noqa: E402
from app.services.retriever import get_doc_count, retrieve  # noqa: E402
from eval.matching import (  # noqa: E402
    build_recall_flags,
    build_relevances,
    count_relevant_targets,
)
from eval.metrics import mean, precision_at_k, recall_at_k, reciprocal_rank  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()


async def evaluate_question(q: dict, ks: list[int]) -> dict:
    """Retrieve for one question and score it against its gold relevance."""
    filters = q.get("filters") or {}
    chunks = await retrieve(
        question=q["question"],
        sector=filters.get("sector"),
        topic=filters.get("topic"),
        top_k=max(ks),
    )
    relevances = build_relevances(chunks, q["relevant"])
    recall_flags = build_recall_flags(chunks, q["relevant"])
    total = count_relevant_targets(q["relevant"])
    return {
        "id": q["id"],
        "type": q["type"],
        "rr": reciprocal_rank(relevances),
        "recall": {k: recall_at_k(recall_flags, total, k) for k in ks},
        "precision": {k: precision_at_k(relevances, k) for k in ks},
        "targets_found": sum(recall_flags),
        "total_relevant": total,
    }


def aggregate(rows: list[dict], ks: list[int]) -> dict:
    """Mean MRR / Recall@K / Precision@K over a set of per-question rows."""
    return {
        "mrr": mean([r["rr"] for r in rows]),
        "recall": {k: mean([r["recall"][k] for r in rows]) for k in ks},
        "precision": {k: mean([r["precision"][k] for r in rows]) for k in ks},
        "count": len(rows),
    }


def print_report(rows: list[dict], ks: list[int]) -> dict:
    """Print the console report and return the structured summary."""
    overall = aggregate(rows, ks)
    types = sorted({r["type"] for r in rows})
    by_type = {t: aggregate([r for r in rows if r["type"] == t], ks) for t in types}

    kcols = "".join(f"  R@{k}".rjust(8) for k in ks) + "".join(f"  P@{k}".rjust(8) for k in ks)
    header = f"{'group':<16}{'MRR':>8}{kcols}{'n':>5}"

    def line(name: str, agg: dict) -> str:
        rec = "".join(f"{agg['recall'][k]:>8.3f}" for k in ks)
        prec = "".join(f"{agg['precision'][k]:>8.3f}" for k in ks)
        return f"{name:<16}{agg['mrr']:>8.3f}{rec}{prec}{agg['count']:>5}"

    print("\n" + "=" * len(header))
    print("RETRIEVAL EVALUATION")
    print("=" * len(header))
    print(header)
    print("-" * len(header))
    print(line("OVERALL", overall))
    print("-" * len(header))
    for t in types:
        print(line(t, by_type[t]))

    misses = [r for r in rows if r["rr"] == 0.0]
    if misses:
        print("\nMisses (no relevant result retrieved):")
        for r in misses:
            print(f"  - {r['id']} ({r['type']})")

    return {"overall": overall, "by_type": by_type}


async def main():
    parser = argparse.ArgumentParser(description="Evaluate retrieval against the golden dataset.")
    parser.add_argument("--k", default="1,3,5", help="Comma-separated K values (default 1,3,5)")
    parser.add_argument("--dataset", default="eval/golden_qa.json", help="Path to golden dataset")
    parser.add_argument("--out", default=None, help="Optional path to write JSON results")
    parser.add_argument("--type", default=None, help="Only evaluate one question type")
    parser.add_argument(
        "--ignore-threshold",
        action="store_true",
        help="Disable the distance filter to measure pure ranker quality",
    )
    args = parser.parse_args()

    if settings.llm_mock:
        logger.error("LLM_MOCK is set — evaluation needs the real corpus. Unset it and retry.")
        sys.exit(1)
    if get_doc_count() == 0:
        logger.error("ChromaDB collection is empty — ingest the corpus first.")
        sys.exit(1)

    if args.ignore_threshold:
        settings.retrieval_distance_threshold = 2.0
        logger.info("Distance filter disabled (pure ranker mode)")

    ks = sorted(int(k) for k in args.k.split(","))
    backend_dir = Path(__file__).parent.parent
    dataset = json.loads((backend_dir / args.dataset).read_text(encoding="utf-8"))
    questions = dataset["questions"]
    if args.type:
        questions = [q for q in questions if q["type"] == args.type]

    logger.info(
        f"Evaluating {len(questions)} questions at K={ks} (corpus: {get_doc_count()} chunks)"
    )
    rows = [await evaluate_question(q, ks) for q in questions]
    summary = print_report(rows, ks)

    if args.out:
        out_path = backend_dir / args.out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "corpus_doc_count": get_doc_count(),
            "dataset_version": dataset.get("version"),
            "k_values": ks,
            "ignore_threshold": args.ignore_threshold,
            "overall": summary["overall"],
            "by_type": summary["by_type"],
            "per_question": rows,
        }
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        logger.info(f"Wrote results to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
