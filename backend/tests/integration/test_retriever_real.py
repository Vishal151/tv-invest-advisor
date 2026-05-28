"""Integration tests using a real in-memory ChromaDB collection."""

# Fix for systems with SQLite < 3.35.0 (common on Linux)
__import__("pysqlite3")
import sys  # noqa: E402

sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

import chromadb  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture
def seeded_collection(monkeypatch):
    """In-memory ChromaDB collection with test chunks, patched into retriever."""
    client = chromadb.Client()
    collection = client.create_collection(
        name="test_thinkbox",
        metadata={"hnsw:space": "cosine"},
    )
    collection.add(
        ids=["1", "2", "3"],
        embeddings=[[0.1] * 1536, [0.2] * 1536, [0.3] * 1536],
        documents=["TV ROI research.", "FMCG sector data.", "Viewing patterns."],
        metadatas=[
            {"sector": "all", "topic": "ROI", "source_title": "PA2", "page": 1},
            {"sector": "FMCG", "topic": "ROI", "source_title": "PA2", "page": 5},
            {"sector": "all", "topic": "viewing", "source_title": "TVR", "page": 3},
        ],
    )
    monkeypatch.setattr("app.services.retriever._collection", collection)
    return collection


def test_where_filter_matches_sector_and_all(seeded_collection):
    from app.services.retriever import _build_where_filter

    where = _build_where_filter(sector="FMCG", topic=None)
    assert where is not None
    assert "$or" in where
    conditions = where["$or"]
    sectors = [c["sector"]["$eq"] for c in conditions]
    assert "FMCG" in sectors
    assert "all" in sectors


def test_where_filter_is_none_without_inputs():
    from app.services.retriever import _build_where_filter

    assert _build_where_filter(sector=None, topic=None) is None


def test_where_filter_topic_only():
    from app.services.retriever import _build_where_filter

    where = _build_where_filter(sector=None, topic="viewing")
    assert where == {"topic": {"$eq": "viewing"}}


def test_enriched_query_prepends_context():
    from app.services.retriever import _build_enriched_query

    q = _build_enriched_query(
        question="When should I advertise?",
        sector="FMCG",
        brand_stage="scale-up",
        primary_goal="brand",
    )
    assert "FMCG" in q
    assert "scale-up" in q
    assert "brand" in q
    assert "When should I advertise?" in q


def test_enriched_query_no_context_returns_question():
    from app.services.retriever import _build_enriched_query

    q = _build_enriched_query(question="When should I advertise?")
    assert q == "When should I advertise?"


def test_filter_by_distance():
    from app.services.retriever import _filter_by_distance

    chunks = [
        {"text": "chunk1", "distance": 0.1},
        {"text": "chunk2", "distance": 0.5},
        {"text": "chunk3", "distance": 1.0},
    ]
    filtered = _filter_by_distance(chunks, threshold=0.6)
    assert len(filtered) == 2
    assert filtered[0]["text"] == "chunk1"
    assert filtered[1]["text"] == "chunk2"


def test_filter_by_distance_empty():
    from app.services.retriever import _filter_by_distance

    chunks = [
        {"text": "chunk1", "distance": 0.9},
        {"text": "chunk2", "distance": 1.0},
    ]
    filtered = _filter_by_distance(chunks, threshold=0.5)
    assert len(filtered) == 0
