# Fix for systems with SQLite < 3.35.0 (common on Linux)
__import__("pysqlite3")
import sys  # noqa: E402

sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

import logging  # noqa: E402
import chromadb  # noqa: E402
from chromadb.config import Settings as ChromaSettings  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.services.embedder import embed  # noqa: E402

logger = logging.getLogger(__name__)
settings = get_settings()

_client = None
_collection = None


def get_collection():
    """Returns the ChromaDB collection, initialising if needed."""
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(
            path=settings.chroma_db_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            f"ChromaDB collection '{settings.chroma_collection}' "
            f"loaded — {_collection.count()} docs"
        )
    return _collection


def get_doc_count() -> int:
    """Returns total number of chunks in the collection."""
    try:
        return get_collection().count()
    except Exception:
        return 0


def retrieve(
    question: str,
    sector: str | None = None,
    brand_stage: str | None = None,
    topic: str | None = None,
    top_k: int | None = None,
) -> list[dict]:
    """
    Embed the question and retrieve the top-k most relevant chunks.

    Applies metadata filters when sector or topic are provided,
    so a scale-up FMCG brand gets sector-relevant chunks.

    Returns a list of dicts: {text, metadata, distance}
    """
    collection = get_collection()
    k = top_k or settings.retrieval_top_k

    # Build ChromaDB where filter from structured inputs
    where = _build_where_filter(sector=sector, topic=topic)

    query_embedding = embed(question)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        where=where if where else None,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append(
            {
                "text": doc,
                "metadata": meta,
                "distance": dist,
            }
        )

    logger.info(f"Retrieved {len(chunks)} chunks for: '{question[:50]}...'")
    return chunks


def _build_where_filter(
    sector: str | None,
    topic: str | None,
) -> dict | None:
    """
    Build a ChromaDB metadata filter.
    Only filters on fields that are explicitly provided.
    Falls back to 'all' for sector if no match expected.
    """
    conditions = []

    if sector:
        # Match chunks tagged for this sector OR tagged 'all'
        conditions.append(
            {
                "$or": [
                    {"sector": {"$eq": sector}},
                    {"sector": {"$eq": "all"}},
                ]
            }
        )

    if topic:
        conditions.append({"topic": {"$eq": topic}})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}
