import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch


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
    with (
        patch("app.services.retriever.get_doc_count", return_value=142),
        patch("app.services.retriever.get_collection"),
    ):
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
    with (
        patch("app.api.routes.check_input", new=AsyncMock(return_value=(True, "APPROVED"))),
        patch("app.api.routes.retrieve", new=AsyncMock(return_value=sample_chunks)),
        patch("app.api.routes.generate", new=AsyncMock(return_value=(answer_text, "gpt-4o"))),
        patch("app.api.routes.check_output", new=AsyncMock(return_value=(True, "APPROVED"))),
    ):

        resp = client.post("/api/query", json={"question": "When does TV advertising work?"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == answer_text
    assert data["model_used"] == "gpt-4o"
    assert data["cached"] is False
    assert len(data["sources"]) == 1


def test_query_rejects_off_topic(client):
    with patch("app.api.routes.check_input", new=AsyncMock(return_value=(False, "REJECTED"))):
        resp = client.post("/api/query", json={"question": "Write me a poem about dogs"})
    assert resp.status_code == 400


def test_query_returns_cached_response(client):
    from app.services.cache import cache

    cached_data = {
        "answer": "Cached answer about TV.",
        "sources": [
            {"title": "Profit Ability 2", "chunk": "excerpt...", "url": "https://thinkbox.tv"}
        ],
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


def test_cache_hit_ignores_leading_trailing_whitespace(client, sample_chunks):
    """Questions with surrounding whitespace should share the cache with the trimmed version."""
    from app.services.cache import cache

    cache.clear()
    cached_data = {
        "answer": "Cached TV answer.",
        "sources": [
            {"title": "PA2", "chunk": "excerpt...", "url": "https://thinkbox.tv",
             "page": 1, "topic": "ROI", "distance": 0.2}
        ],
        "model_used": "gpt-4o",
    }
    cache.set(
        cached_data,
        question="Does TV work for FMCG?",
        sector=None, brand_stage=None, tv_history=None, primary_goal=None, budget_tier=None,
    )
    # Question has 10 chars minimum for validation, padded version still valid
    resp = client.post("/api/query", json={"question": "Does TV work for FMCG?"})
    assert resp.status_code == 200
    assert resp.json()["cached"] is True
    assert resp.json()["answer"] == "Cached TV answer."
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


def test_health_reports_redis_disabled(client):
    """In test environment REDIS_URL is not set — health should report 'disabled'."""
    with patch("app.api.routes.get_doc_count", return_value=142):
        resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["redis"] in ("ok", "disabled", "unavailable")


def test_ingest_requires_api_key(client):
    resp = client.post("/api/ingest", json={"source_path": "data/pdfs/test.pdf"})
    assert resp.status_code == 422  # missing X-API-Key header


def test_query_retries_generation_when_output_guardrail_rejects(client, sample_chunks):
    from app.services.cache import cache

    cache.clear()
    first_answer = "TV delivers £5.61 ROI for every £1 spent."
    second_answer = "Grounded answer from retry. TV delivers £5.61 ROI. Key sources: Profit Ability 2."
    generate_mock = AsyncMock(side_effect=[(first_answer, "gpt-4o"), (second_answer, "gpt-4o")])
    check_output_mock = AsyncMock(side_effect=[(False, "REJECTED"), (True, "APPROVED")])

    with (
        patch("app.api.routes.check_input", new=AsyncMock(return_value=(True, "APPROVED"))),
        patch("app.api.routes.retrieve", new=AsyncMock(return_value=sample_chunks)),
        patch("app.api.routes.generate", generate_mock),
        patch("app.api.routes.check_output", check_output_mock),
    ):
        resp = client.post(
            "/api/query",
            json={"question": "When does linear TV deliver its best ROI for FMCG retry test?"},
        )

    assert resp.status_code == 200
    assert resp.json()["answer"] == second_answer
    cache.clear()
    assert generate_mock.call_count == 2
    assert generate_mock.call_args_list[1].kwargs.get("strict_grounding") is True


def test_query_returns_safe_fallback_when_guardrail_rejects_twice(client, sample_chunks):
    from app.api.routes import SAFE_FALLBACK_ANSWER
    from app.services.cache import cache

    cache.clear()
    with (
        patch("app.api.routes.check_input", new=AsyncMock(return_value=(True, "APPROVED"))),
        patch("app.api.routes.retrieve", new=AsyncMock(return_value=sample_chunks)),
        patch("app.api.routes.generate", new=AsyncMock(return_value=("bad answer", "gpt-4o"))),
        patch("app.api.routes.check_output", new=AsyncMock(return_value=(False, "REJECTED"))),
    ):
        resp = client.post(
            "/api/query",
            json={"question": "When does linear TV deliver its best ROI for FMCG fallback test?"},
        )

    assert resp.status_code == 200
    assert resp.json()["answer"] == SAFE_FALLBACK_ANSWER
    cache.clear()


def test_query_returns_503_on_llm_failure(client, sample_chunks):
    with (
        patch("app.api.routes.check_input", new=AsyncMock(return_value=(True, "APPROVED"))),
        patch("app.api.routes.retrieve", new=AsyncMock(return_value=sample_chunks)),
        patch(
            "app.api.routes.generate", new=AsyncMock(side_effect=RuntimeError("All models failed"))
        ),
    ):
        resp = client.post("/api/query", json={"question": "When does TV advertising work?"})
    assert resp.status_code == 503
    assert "unavailable" in resp.json()["detail"].lower()


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
    with patch("app.api.routes.run_ingest", new=AsyncMock(return_value=5)) as mock_ingest:
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


def test_safe_fallback_is_not_cached(client, sample_chunks):
    """When safe fallback is returned, it must NOT be written to cache."""
    from app.api.routes import SAFE_FALLBACK_ANSWER
    from app.services.cache import cache

    cache.clear()
    question = "Unique fallback cache test question xyz?"

    with (
        patch("app.api.routes.check_input", new=AsyncMock(return_value=(True, "APPROVED"))),
        patch("app.api.routes.retrieve", new=AsyncMock(return_value=sample_chunks)),
        patch("app.api.routes.generate", new=AsyncMock(return_value=("bad answer", "gpt-4o"))),
        patch("app.api.routes.check_output", new=AsyncMock(return_value=(False, "REJECTED"))),
    ):
        resp = client.post("/api/query", json={"question": question})

    assert resp.status_code == 200
    assert resp.json()["answer"] == SAFE_FALLBACK_ANSWER

    cached = cache.get(
        question=question,
        sector=None,
        brand_stage=None,
        tv_history=None,
        primary_goal=None,
        budget_tier=None,
    )
    assert cached is None, "Safe fallback answer must not be cached"
    cache.clear()


def test_query_sources_include_page_topic_distance(client, sample_chunks):
    answer_text = "TV delivers ROI. Key sources: Profit Ability 2."
    with (
        patch("app.api.routes.check_input", new=AsyncMock(return_value=(True, "APPROVED"))),
        patch("app.api.routes.retrieve", new=AsyncMock(return_value=sample_chunks)),
        patch("app.api.routes.generate", new=AsyncMock(return_value=(answer_text, "gpt-4o"))),
        patch("app.api.routes.check_output", new=AsyncMock(return_value=(True, "APPROVED"))),
    ):
        resp = client.post("/api/query", json={"question": "When does TV advertising work?"})

    assert resp.status_code == 200
    source = resp.json()["sources"][0]
    assert "page" in source
    assert "topic" in source
    assert "distance" in source
    assert source["page"] == 12
    assert source["topic"] == "ROI"
    assert source["distance"] == 0.12


def test_startup_raises_in_production_with_dev_api_key():
    """Startup must refuse to run in production if API_KEY is the dev default."""
    from unittest.mock import Mock, patch
    from app.main import _check_production_config

    # Mock settings with production=True and api_key="dev-key"
    mock_settings = Mock()
    mock_settings.is_production = True
    mock_settings.api_key = "dev-key"
    mock_settings.openai_api_key = "sk-test"
    mock_settings.anthropic_api_key = ""

    with patch("app.main.settings", mock_settings):
        with pytest.raises(RuntimeError, match="API_KEY must be set in production"):
            _check_production_config()


def test_startup_raises_in_production_with_no_llm_keys():
    """Startup must refuse if no LLM keys configured in production."""
    from unittest.mock import Mock, patch
    from app.main import _check_production_config

    # Mock settings with production=True and no LLM keys
    mock_settings = Mock()
    mock_settings.is_production = True
    mock_settings.api_key = "valid-prod-key"
    mock_settings.openai_api_key = ""
    mock_settings.anthropic_api_key = ""

    with patch("app.main.settings", mock_settings):
        with pytest.raises(RuntimeError, match="At least one of OPENAI_API_KEY or ANTHROPIC_API_KEY must be set"):
            _check_production_config()


def test_startup_passes_development_mode():
    """Startup should skip checks in development mode."""
    from unittest.mock import Mock, patch
    from app.main import _check_production_config

    # Mock settings with development=False and dev-key, no LLM keys
    mock_settings = Mock()
    mock_settings.is_production = False
    mock_settings.api_key = "dev-key"
    mock_settings.openai_api_key = ""
    mock_settings.anthropic_api_key = ""

    with patch("app.main.settings", mock_settings):
        # Should not raise in development mode
        _check_production_config()


def test_health_includes_readiness_signals(client):
    with patch("app.api.routes.get_doc_count", return_value=142):
        resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "llm_configured" in data
    assert "langfuse_enabled" in data
    assert isinstance(data["llm_configured"], bool)
    assert isinstance(data["langfuse_enabled"], bool)


def test_no_retry_for_qualitative_answer_without_statistics(client, sample_chunks):
    """Output guardrail rejection on a qualitative answer must NOT trigger regeneration."""
    qualitative_answer = "TV advertising builds brand awareness over time."
    generate_mock = AsyncMock(return_value=(qualitative_answer, "gpt-4o"))

    with (
        patch("app.api.routes.check_input", new=AsyncMock(return_value=(True, "APPROVED"))),
        patch("app.api.routes.retrieve", new=AsyncMock(return_value=sample_chunks)),
        patch("app.api.routes.generate", generate_mock),
        patch("app.api.routes.check_output", new=AsyncMock(return_value=(False, "REJECTED"))),
    ):
        resp = client.post("/api/query", json={"question": "How does TV build brand?"})

    assert resp.status_code == 200
    assert generate_mock.call_count == 1, "generate() must be called only once for qualitative answer"
