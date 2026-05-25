import pytest
from unittest.mock import patch, MagicMock
import app.services.retriever as retriever_module


def _make_chroma_result(docs, metadatas, distances):
    """Build a ChromaDB-shaped query result."""
    return {
        "documents": [docs],
        "metadatas": [metadatas],
        "distances": [distances],
    }


@pytest.fixture(autouse=True)
def reset_retriever_globals():
    """Reset module-level singletons before each test so patches work cleanly."""
    original_client = retriever_module._client
    original_collection = retriever_module._collection
    retriever_module._client = None
    retriever_module._collection = None
    yield
    retriever_module._client = original_client
    retriever_module._collection = original_collection


@pytest.fixture
def mock_collection():
    """A mock ChromaDB collection."""
    col = MagicMock()
    col.count.return_value = 42
    return col


def test_retrieve_returns_chunks(mock_collection):
    mock_collection.query.return_value = _make_chroma_result(
        docs=["TV delivers strong ROI."],
        metadatas=[{"source_title": "Profit Ability 2", "page": 1}],
        distances=[0.15],
    )

    with (
        patch("app.services.retriever.chromadb.PersistentClient") as mock_client,
        patch("app.services.retriever.embed", return_value=[0.1] * 1536),
    ):
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        from app.services.retriever import retrieve

        chunks = retrieve(question="Does TV work?")

    assert len(chunks) == 1
    assert chunks[0]["text"] == "TV delivers strong ROI."
    assert chunks[0]["metadata"]["source_title"] == "Profit Ability 2"
    assert chunks[0]["distance"] == 0.15


def test_retrieve_calls_embed_with_question(mock_collection):
    mock_collection.query.return_value = _make_chroma_result([], [], [])

    with (
        patch("app.services.retriever.chromadb.PersistentClient") as mock_client,
        patch("app.services.retriever.embed", return_value=[0.1] * 1536) as mock_embed,
    ):
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        from app.services.retriever import retrieve

        retrieve(question="When does TV pay back?")

    mock_embed.assert_called_once_with("When does TV pay back?")


def test_retrieve_applies_sector_filter(mock_collection):
    mock_collection.query.return_value = _make_chroma_result([], [], [])

    with (
        patch("app.services.retriever.chromadb.PersistentClient") as mock_client,
        patch("app.services.retriever.embed", return_value=[0.1] * 1536),
    ):
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        from app.services.retriever import retrieve

        retrieve(question="q", sector="FMCG")

    call_kwargs = mock_collection.query.call_args.kwargs
    where = call_kwargs["where"]
    assert where is not None
    assert "$or" in str(where)
    assert "FMCG" in str(where)


def test_retrieve_no_filter_when_no_sector(mock_collection):
    mock_collection.query.return_value = _make_chroma_result([], [], [])

    with (
        patch("app.services.retriever.chromadb.PersistentClient") as mock_client,
        patch("app.services.retriever.embed", return_value=[0.1] * 1536),
    ):
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        from app.services.retriever import retrieve

        retrieve(question="q")

    call_kwargs = mock_collection.query.call_args.kwargs
    assert call_kwargs["where"] is None


def test_get_doc_count(mock_collection):
    retriever_module._collection = mock_collection
    from app.services.retriever import get_doc_count

    count = get_doc_count()
    assert count == 42
