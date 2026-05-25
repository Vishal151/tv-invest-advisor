import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


@pytest.fixture
def sample_chunks():
    return [
        {
            "text": "TV advertising delivered an average ROI of £5.61 for every £1 spent.",
            "metadata": {
                "source_title": "Profit Ability 2",
                "source_url": "https://www.thinkbox.tv/research/thinkbox-research/profit-ability-2",
                "topic": "ROI",
                "sector": "all",
                "page": 12,
                "chunk_index": 3,
            },
            "distance": 0.12,
        }
    ]


@pytest.fixture
def client():
    """Test client with ChromaDB mocked out so the app can start."""
    with patch("app.services.retriever.get_doc_count", return_value=142), \
         patch("app.services.retriever.get_collection"):
        from app.main import app
        return TestClient(app)


def test_health_returns_ok(client):
    with patch("app.api.routes.get_doc_count", return_value=142):
        resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["chroma_docs"] == 142
    assert "version" in data


def test_query_returns_answer(client, sample_chunks):
    answer_text = "TV delivers £5.61 ROI. Key sources: Profit Ability 2."
    with patch("app.api.routes.check_input", return_value=(True, "APPROVED")), \
         patch("app.api.routes.retrieve", return_value=sample_chunks), \
         patch("app.api.routes.generate", return_value=(answer_text, "gpt-4o")), \
         patch("app.api.routes.check_output", return_value=(True, "APPROVED")):

        resp = client.post("/api/query", json={"question": "When does TV advertising work?"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == answer_text
    assert data["model_used"] == "gpt-4o"
    assert data["cached"] is False
    assert len(data["sources"]) == 1


def test_query_rejects_off_topic(client):
    with patch("app.api.routes.check_input", return_value=(False, "REJECTED")):
        resp = client.post("/api/query", json={"question": "Write me a poem about dogs"})
    assert resp.status_code == 400


def test_query_returns_cached_response(client):
    from app.services.cache import cache
    cached_data = {
        "answer": "Cached answer about TV.",
        "sources": [{"title": "Profit Ability 2", "chunk": "excerpt...", "url": "https://thinkbox.tv"}],
        "model_used": "gpt-4o",
    }
    # The route passes all 6 kwargs to cache.get, so set must match exactly
    cache.set(
        cached_data,
        question="Does TV work for FMCG?",
        sector=None,
        brand_stage=None,
        tv_history=None,
        primary_goal=None,
        budget_tier=None,
    )

    resp = client.post("/api/query", json={"question": "Does TV work for FMCG?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["cached"] is True
    assert data["answer"] == "Cached answer about TV."

    cache.clear()


def test_query_rejects_invalid_sector(client):
    resp = client.post(
        "/api/query",
        json={"question": "Does TV work?", "sector": "InvalidSector"},
    )
    assert resp.status_code == 422


def test_query_validates_min_length(client):
    resp = client.post("/api/query", json={"question": "Hi"})
    assert resp.status_code == 422


def test_ingest_requires_api_key(client):
    resp = client.post("/api/ingest", json={"source_path": "data/pdfs/test.pdf"})
    assert resp.status_code == 422  # missing X-API-Key header


def test_ingest_rejects_wrong_key(client):
    resp = client.post(
        "/api/ingest",
        json={"source_path": "data/pdfs/test.pdf"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert resp.status_code == 401


def test_ingest_valid_document(client):
    """Ingest route should call the ingest pipeline and return chunk count."""
    from app.api.routes import verify_api_key
    client.app.dependency_overrides[verify_api_key] = lambda: "dev-key"
    with patch("app.api.routes.run_ingest", return_value=5) as mock_ingest:
        resp = client.post(
            "/api/ingest",
            json={"source_path": "data/pdfs/profit-ability-2.pdf"},
            headers={"X-API-Key": "dev-key"},
        )
    client.app.dependency_overrides.clear()
    assert resp.status_code == 200
    data = resp.json()
    assert data["chunks_added"] == 5
    mock_ingest.assert_called_once_with("data/pdfs/profit-ability-2.pdf")
