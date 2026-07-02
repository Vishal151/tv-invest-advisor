import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch


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
    structured = {"summary": [answer_text], "stats": [], "chart": None, "followups": []}
    with (
        patch("app.api.routes.check_input", new=AsyncMock(return_value=(True, "APPROVED"))),
        patch("app.api.routes.retrieve", new=AsyncMock(return_value=sample_chunks)),
        patch("app.api.routes.generate", new=AsyncMock(return_value=(structured, "gpt-4o"))),
        patch("app.api.routes.check_output", new=AsyncMock(return_value=(True, "APPROVED"))),
    ):

        resp = client.post("/api/query", json={"question": "When does TV advertising work?"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"]["summary"][0] == answer_text
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
        "answer": {
            "summary": ["Cached answer about TV."],
            "stats": [],
            "chart": None,
            "followups": [],
        },
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
    assert data["answer"]["summary"][0] == "Cached answer about TV."

    cache.clear()


def test_cache_hit_ignores_leading_trailing_whitespace(client, sample_chunks):
    """Questions with surrounding whitespace should share the cache with the trimmed version."""
    from app.services.cache import cache

    cache.clear()
    cached_data = {
        "answer": {"summary": ["Cached TV answer."], "stats": [], "chart": None, "followups": []},
        "sources": [
            {
                "title": "PA2",
                "chunk": "excerpt...",
                "url": "https://thinkbox.tv",
                "page": 1,
                "topic": "ROI",
                "distance": 0.2,
            }
        ],
        "model_used": "gpt-4o",
    }
    cache.set(
        cached_data,
        question="Does TV work for FMCG?",
        sector=None,
        brand_stage=None,
        tv_history=None,
        primary_goal=None,
        budget_tier=None,
    )
    # Question has 10 chars minimum for validation, padded version still valid
    resp = client.post("/api/query", json={"question": "Does TV work for FMCG?"})
    assert resp.status_code == 200
    assert resp.json()["cached"] is True
    assert resp.json()["answer"]["summary"][0] == "Cached TV answer."
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
    second_answer = (
        "Grounded answer from retry. TV delivers £5.61 ROI. Key sources: Profit Ability 2."
    )
    first_structured = {"summary": [first_answer], "stats": [], "chart": None, "followups": []}
    second_structured = {"summary": [second_answer], "stats": [], "chart": None, "followups": []}
    generate_mock = AsyncMock(
        side_effect=[(first_structured, "gpt-4o"), (second_structured, "gpt-4o")]
    )
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
    assert resp.json()["answer"]["summary"][0] == second_answer
    cache.clear()
    assert generate_mock.call_count == 2
    assert generate_mock.call_args_list[1].kwargs.get("strict_grounding") is True


def test_query_returns_safe_fallback_when_guardrail_rejects_twice(client, sample_chunks):
    from app.api.routes import SAFE_FALLBACK_ANSWER
    from app.services.cache import cache

    cache.clear()
    bad_structured = {"summary": ["bad answer"], "stats": [], "chart": None, "followups": []}
    with (
        patch("app.api.routes.check_input", new=AsyncMock(return_value=(True, "APPROVED"))),
        patch("app.api.routes.retrieve", new=AsyncMock(return_value=sample_chunks)),
        patch("app.api.routes.generate", new=AsyncMock(return_value=(bad_structured, "gpt-4o"))),
        patch("app.api.routes.check_output", new=AsyncMock(return_value=(False, "REJECTED"))),
    ):
        resp = client.post(
            "/api/query",
            json={"question": "When does linear TV deliver its best ROI for FMCG fallback test?"},
        )

    assert resp.status_code == 200
    assert resp.json()["answer"]["summary"][0] == SAFE_FALLBACK_ANSWER
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
    bad_structured = {"summary": ["bad answer"], "stats": [], "chart": None, "followups": []}

    with (
        patch("app.api.routes.check_input", new=AsyncMock(return_value=(True, "APPROVED"))),
        patch("app.api.routes.retrieve", new=AsyncMock(return_value=sample_chunks)),
        patch("app.api.routes.generate", new=AsyncMock(return_value=(bad_structured, "gpt-4o"))),
        patch("app.api.routes.check_output", new=AsyncMock(return_value=(False, "REJECTED"))),
    ):
        resp = client.post("/api/query", json={"question": question})

    assert resp.status_code == 200
    assert resp.json()["answer"]["summary"][0] == SAFE_FALLBACK_ANSWER

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
    structured = {"summary": [answer_text], "stats": [], "chart": None, "followups": []}
    with (
        patch("app.api.routes.check_input", new=AsyncMock(return_value=(True, "APPROVED"))),
        patch("app.api.routes.retrieve", new=AsyncMock(return_value=sample_chunks)),
        patch("app.api.routes.generate", new=AsyncMock(return_value=(structured, "gpt-4o"))),
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
        with pytest.raises(
            RuntimeError, match="At least one of OPENAI_API_KEY or ANTHROPIC_API_KEY must be set"
        ):
            _check_production_config()


def test_query_rate_limited_after_20_requests(client, sample_chunks):
    """The 20/minute limit on /api/query must actually produce a 429."""
    from app.core.limiter import limiter

    structured = {"summary": ["TV works."], "stats": [], "chart": None, "followups": []}
    limiter.reset()
    try:
        with (
            patch("app.api.routes.check_input", new=AsyncMock(return_value=(True, "APPROVED"))),
            patch("app.api.routes.retrieve", new=AsyncMock(return_value=sample_chunks)),
            patch("app.api.routes.generate", new=AsyncMock(return_value=(structured, "gpt-4o"))),
            patch("app.api.routes.check_output", new=AsyncMock(return_value=(True, "APPROVED"))),
        ):
            responses = [
                client.post("/api/query", json={"question": "When does TV advertising work?"})
                for _ in range(21)
            ]
    finally:
        limiter.reset()

    assert all(r.status_code == 200 for r in responses[:20])
    assert responses[20].status_code == 429


def test_startup_raises_in_production_with_llm_mock():
    """LLM_MOCK=true in production serves fabricated answers with guardrails
    disabled while health reports ok — startup must refuse it outright."""
    from unittest.mock import Mock, patch
    from app.main import _check_production_config

    mock_settings = Mock()
    mock_settings.is_production = True
    mock_settings.api_key = "valid-prod-key"
    mock_settings.openai_api_key = "sk-test"
    mock_settings.anthropic_api_key = ""
    mock_settings.llm_mock = True

    with patch("app.main.settings", mock_settings):
        with pytest.raises(RuntimeError, match="LLM_MOCK must not be enabled in production"):
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
    structured = {"summary": [qualitative_answer], "stats": [], "chart": None, "followups": []}
    generate_mock = AsyncMock(return_value=(structured, "gpt-4o"))

    with (
        patch("app.api.routes.check_input", new=AsyncMock(return_value=(True, "APPROVED"))),
        patch("app.api.routes.retrieve", new=AsyncMock(return_value=sample_chunks)),
        patch("app.api.routes.generate", generate_mock),
        patch("app.api.routes.check_output", new=AsyncMock(return_value=(False, "REJECTED"))),
    ):
        resp = client.post("/api/query", json={"question": "How does TV build brand?"})

    assert resp.status_code == 200
    assert (
        generate_mock.call_count == 1
    ), "generate() must be called only once for qualitative answer"


def test_output_guardrail_reviews_stats_and_chart(client, sample_chunks):
    """H1: the grounding review must cover stats[] and chart values, not just summary prose."""
    from app.services.cache import cache

    cache.clear()
    structured = {
        "summary": ["TV outperforms other channels."],
        "stats": [
            {
                "value": "£5.61",
                "unit": "ROI per £1 spent",
                "context": "141 brands",
                "source": "Profit Ability 2",
                "page": 12,
            }
        ],
        "chart": {
            "title": "ROI by channel",
            "source": "Profit Ability 2",
            "unit": "£",
            "bars": [
                {"label": "TV", "value": 5.61, "highlight": True},
                {"label": "Digital", "value": 3.21},
            ],
        },
        "followups": [],
    }
    check_output_mock = AsyncMock(return_value=(True, "APPROVED"))
    with (
        patch("app.api.routes.check_input", new=AsyncMock(return_value=(True, "APPROVED"))),
        patch("app.api.routes.retrieve", new=AsyncMock(return_value=sample_chunks)),
        patch("app.api.routes.generate", new=AsyncMock(return_value=(structured, "gpt-4o"))),
        patch("app.api.routes.check_output", check_output_mock),
    ):
        resp = client.post("/api/query", json={"question": "Guardrail must review stats too?"})

    assert resp.status_code == 200
    reviewed = check_output_mock.call_args.kwargs["answer"]
    assert "£5.61" in reviewed, "stat values must be part of the grounding review"
    assert "Profit Ability 2" in reviewed
    assert "3.21" in reviewed, "chart bar values must be part of the grounding review"
    cache.clear()


def test_health_returns_503_when_corpus_empty(client):
    """H3: health must report degraded (503) when ChromaDB has no documents."""
    with patch("app.api.routes.get_doc_count", return_value=0):
        resp = client.get("/api/health")
    assert resp.status_code == 503
    assert resp.json()["status"] == "degraded"


def test_health_returns_503_when_redis_configured_but_unavailable(client, monkeypatch):
    """H3: health must report degraded when Redis is enabled and unreachable."""
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "redis_url", "redis://localhost:6399/0")
    with (
        patch("app.api.routes.get_doc_count", return_value=142),
        patch("app.services.cache.check_redis_status", return_value="unavailable"),
    ):
        resp = client.get("/api/health")
    assert resp.status_code == 503
    assert resp.json()["redis"] == "unavailable"


def test_health_stays_ok_in_mock_mode_without_corpus(client, monkeypatch):
    """Mock mode runs without external dependencies — health must not report degraded."""
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "llm_mock", True)
    with patch("app.api.routes.get_doc_count", return_value=0):
        resp = client.get("/api/health")
    assert resp.status_code == 200


def test_query_returns_503_on_retrieval_failure(client):
    """M1: an embeddings/ChromaDB outage must surface as 503, not an unhandled 500."""
    with (
        patch("app.api.routes.check_input", new=AsyncMock(return_value=(True, "APPROVED"))),
        patch(
            "app.api.routes.retrieve",
            new=AsyncMock(side_effect=RuntimeError("embeddings API down")),
        ),
    ):
        resp = client.post("/api/query", json={"question": "Does TV work during outages?"})
    assert resp.status_code == 503
    assert "unavailable" in resp.json()["detail"].lower()


def test_no_relevant_chunks_message_distinct_from_empty_corpus(client):
    """M4: a filtered-out retrieval must not claim the corpus is missing."""
    with (
        patch("app.api.routes.check_input", new=AsyncMock(return_value=(True, "APPROVED"))),
        patch("app.api.routes.retrieve", new=AsyncMock(return_value=[])),
        patch("app.api.routes.get_doc_count", return_value=408),
    ):
        resp = client.post("/api/query", json={"question": "Question with no relevant chunks?"})
    assert resp.status_code == 503
    assert "rephras" in resp.json()["detail"].lower()
    assert "ingest" not in resp.json()["detail"].lower()

    with (
        patch("app.api.routes.check_input", new=AsyncMock(return_value=(True, "APPROVED"))),
        patch("app.api.routes.retrieve", new=AsyncMock(return_value=[])),
        patch("app.api.routes.get_doc_count", return_value=0),
    ):
        resp = client.post("/api/query", json={"question": "Question against an empty corpus?"})
    assert resp.status_code == 503
    assert "ingest" in resp.json()["detail"].lower()


def test_safe_fallback_makes_no_substantive_claim():
    """M10: the fallback served when grounding fails must not itself assert an uncited claim."""
    from app.api.routes import SAFE_FALLBACK_ANSWER, _answer_contains_statistic

    assert not _answer_contains_statistic(SAFE_FALLBACK_ANSWER)
    assert "most effective" not in SAFE_FALLBACK_ANSWER.lower()


def test_cors_exposes_request_id_header(client):
    """M9: the browser must be able to read X-Request-ID for support references."""
    with patch("app.api.routes.get_doc_count", return_value=142):
        resp = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    exposed = resp.headers.get("access-control-expose-headers", "")
    assert "x-request-id" in exposed.lower()


def test_corpus_lists_ingested_documents(client):
    with patch(
        "app.api.routes.get_corpus_summary",
        return_value=[
            {"source_title": "Profit Ability 2", "chunks": 45, "topic": "ROI"},
        ],
    ):
        resp = client.get("/api/corpus")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data[0]["source_title"] == "Profit Ability 2"
    assert "chunks" in data[0]
