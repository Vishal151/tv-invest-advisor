"""
Retrieval quality smoke test.

Usage (after ingesting the corpus):
    cd backend
    uv run scripts/test_retrieval.py

Runs a set of representative queries and prints the top-3 results for each.
Manual inspection confirms retrieval is working correctly.
"""

# SQLite fix must be first
__import__("pysqlite3")
import sys  # noqa: E402

sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

import asyncio  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.retriever import retrieve, get_doc_count  # noqa: E402

SMOKE_QUERIES = [
    {
        "question": "What ROI does TV advertising deliver?",
        "sector": None,
        "expected_source": "Profit Ability",
    },
    {
        "question": "How does TV advertising work for small businesses?",
        "sector": None,
        "expected_source": "As Seen on TV",
    },
    {
        "question": "How much time do people spend watching TV each day?",
        "sector": None,
        "expected_source": "TV Viewing Report",
    },
    {
        "question": "What is the relationship between TV and brand effectiveness?",
        "sector": None,
        "expected_source": "Effectiveness",
    },
    {
        "question": "When should an FMCG brand invest in TV advertising?",
        "sector": "FMCG",
        "expected_source": None,
    },
]


async def run_smoke_test():
    total_docs = get_doc_count()
    print(f"\nChromaDB collection: {total_docs} chunks\n")

    if total_docs == 0:
        print("ERROR: No documents in ChromaDB. Run scripts/ingest.py first.")
        sys.exit(1)

    passed = 0
    for query in SMOKE_QUERIES:
        print(f"Query: {query['question']}")
        if query["sector"]:
            print(f"  Sector filter: {query['sector']}")

        chunks = await retrieve(question=query["question"], sector=query["sector"], top_k=3)

        if not chunks:
            print("  FAIL: No chunks returned\n")
            continue

        print(f"  Retrieved {len(chunks)} chunks:")
        for i, chunk in enumerate(chunks, 1):
            title = chunk["metadata"].get("source_title", "?")
            page = chunk["metadata"].get("page", "?")
            distance = chunk["distance"]
            preview = chunk["text"][:120].replace("\n", " ")
            print(f"    [{i}] {title} p.{page} (dist={distance:.3f})")
            print(f"        {preview}...")

        if query["expected_source"]:
            sources = [c["metadata"].get("source_title", "") for c in chunks]
            matched = any(query["expected_source"].lower() in s.lower() for s in sources)
            status = "PASS" if matched else "WARN (expected source not in top 3)"
            if matched:
                passed += 1
        else:
            status = "PASS (no expected source specified)"
            passed += 1

        print(f"  {status}\n")

    total = len(SMOKE_QUERIES)
    print(f"Results: {passed}/{total} queries returned expected sources")


if __name__ == "__main__":
    asyncio.run(run_smoke_test())
