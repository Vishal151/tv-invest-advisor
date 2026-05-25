# TV Investment Advisor — Backend TDD Completion Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a complete pytest test suite to the existing backend, wire up the two missing features (LangFuse tracing, `/api/ingest` pipeline), implement `test_retrieval.py`, and add `docker-compose.yml` — leaving a fully tested, production-grade backend.

**Architecture:** TDD retrofit — write failing tests first (using `unittest.mock` to avoid real API calls), then verify existing implementations pass them, fixing any gaps. External calls (OpenAI, LiteLLM, ChromaDB) are always mocked in unit tests; an optional `--live` marker gates tests that require real API keys.

**Tech Stack:** pytest, pytest-asyncio, httpx (ASGI test client), unittest.mock — all added to `pyproject.toml` dev deps.

---

## File Map

Files created or modified by this plan:

| Path | Action | Purpose |
|---|---|---|
| `backend/pyproject.toml` | Modify | Add pytest + test deps |
| `backend/pytest.ini` | Create | pytest config (asyncio mode, testpaths) |
| `backend/tests/__init__.py` | Create | Package marker |
| `backend/tests/conftest.py` | Create | Shared fixtures (test app, mock settings) |
| `backend/tests/unit/test_cache.py` | Create | Cache logic |
| `backend/tests/unit/test_config.py` | Create | Settings loading |
| `backend/tests/unit/test_generator.py` | Create | Prompt building + LiteLLM mock |
| `backend/tests/unit/test_guardrails.py` | Create | Input/output guardrail mocks |
| `backend/tests/unit/test_retriever.py` | Create | ChromaDB query mock |
| `backend/tests/integration/test_routes.py` | Create | FastAPI route tests via httpx |
| `backend/app/services/generator.py` | Modify | Add LangFuse tracing |
| `backend/app/api/routes.py` | Modify | Wire `/api/ingest` to pipeline |
| `backend/scripts/test_retrieval.py` | Replace | Retrieval quality smoke test |
| `backend/docker-compose.yml` | Create | Backend service definition |

---

## Task 1: Add pytest dependencies and configuration

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/pytest.ini`

- [ ] **Step 1: Add dev dependencies to pyproject.toml**

Add a `[dependency-groups]` section (uv convention for dev deps):

```toml
[project]
name = "backend"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "chromadb>=1.5.9",
    "fastapi>=0.136.3",
    "httpx>=0.28.1",
    "langfuse>=4.6.1",
    "litellm>=1.86.0",
    "openai>=2.38.0",
    "pydantic>=2.13.4",
    "pydantic-settings>=2.14.1",
    "pypdf>=6.12.1",
    "pysqlite3-binary>=0.5.4.post2",
    "python-dotenv>=1.2.2",
    "requests>=2.34.2",
    "uvicorn>=0.48.0",
]

[dependency-groups]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.28.1",
]
```

- [ ] **Step 2: Create pytest.ini**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 3: Install dev deps**

```bash
cd backend
uv add --group dev pytest pytest-asyncio httpx
```

Expected: `uv.lock` updated, no errors.

- [ ] **Step 4: Verify pytest is available**

```bash
cd backend
uv run pytest --version
```

Expected: `pytest 8.x.x`

- [ ] **Step 5: Create test directory structure**

```bash
mkdir -p backend/tests/unit backend/tests/integration
touch backend/tests/__init__.py backend/tests/unit/__init__.py backend/tests/integration/__init__.py
```

- [ ] **Step 6: Commit**

```bash
cd backend
git add pyproject.toml pytest.ini uv.lock tests/
git commit -m "chore: add pytest infrastructure and test directory structure"
```

---

## Task 2: Create shared test fixtures (conftest.py)

**Files:**
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Write conftest.py**

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_settings(monkeypatch):
    """Override settings so tests never need real env vars."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.setenv("API_KEY", "test-api-key")


@pytest.fixture
def sample_chunks() -> list[dict]:
    """Realistic chunk data matching ChromaDB retrieval output."""
    return [
        {
            "text": "TV advertising delivered an average ROI of £5.61 for every £1 spent, "
                    "based on analysis of 141 brands across 14 categories.",
            "metadata": {
                "source_title": "Profit Ability 2",
                "source_url": "https://www.thinkbox.tv/research/thinkbox-research/profit-ability-2",
                "topic": "ROI",
                "sector": "all",
                "page": 12,
                "chunk_index": 3,
            },
            "distance": 0.12,
        },
        {
            "text": "Brands that invest in TV consistently outperform those that do not "
                    "on measures of brand fame, trust, and mental availability.",
            "metadata": {
                "source_title": "TV is at the Heart of Effectiveness",
                "source_url": "https://www.thinkbox.tv/research/reports/tv-is-at-the-heart-of-effectiveness-whitepaper-by-peter-field",
                "topic": "effectiveness",
                "sector": "all",
                "page": 8,
                "chunk_index": 14,
            },
            "distance": 0.18,
        },
    ]


@pytest.fixture
def mock_retrieve(sample_chunks):
    """Patches retriever.retrieve to return sample_chunks."""
    with patch("app.services.retriever.retrieve", return_value=sample_chunks) as m:
        yield m


@pytest.fixture
def mock_generate():
    """Patches generator.generate to return a realistic answer."""
    answer = (
        "Based on Thinkbox research (Profit Ability 2), TV advertising delivers "
        "an average ROI of £5.61 per £1 spent. Key sources: Profit Ability 2."
    )
    with patch("app.services.generator.generate", return_value=(answer, "gpt-4o")) as m:
        yield m


@pytest.fixture
def mock_check_input():
    """Patches guardrails.check_input to approve all queries."""
    with patch("app.services.guardrails.check_input", return_value=(True, "APPROVED")) as m:
        yield m


@pytest.fixture
def mock_check_output():
    """Patches guardrails.check_output to approve all outputs."""
    with patch("app.services.guardrails.check_output", return_value=(True, "APPROVED")) as m:
        yield m


@pytest.fixture
def mock_doc_count():
    """Patches retriever.get_doc_count to return a realistic count."""
    with patch("app.services.retriever.get_doc_count", return_value=142) as m:
        yield m


@pytest.fixture
def test_client(mock_doc_count):
    """Returns a TestClient with all external services mocked at import time."""
    # Patch ChromaDB before app import to avoid SQLite version check
    with patch("app.services.retriever.get_collection"):
        from app.main import app
        return TestClient(app)
```

- [ ] **Step 2: Run conftest import check (no test yet)**

```bash
cd backend
uv run pytest tests/conftest.py --collect-only 2>&1 | head -10
```

Expected: `no tests ran` — no errors on import.

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add shared fixtures to conftest"
```

---

## Task 3: Unit tests for cache.py

**Files:**
- Create: `backend/tests/unit/test_cache.py`

- [ ] **Step 1: Write failing test — cache miss returns None**

```python
# tests/unit/test_cache.py
import time
import pytest
from app.services.cache import ResponseCache


@pytest.fixture
def cache():
    return ResponseCache(ttl_seconds=60, max_size=10)


def test_get_miss_returns_none(cache):
    result = cache.get(question="anything")
    assert result is None


def test_set_and_get_returns_value(cache):
    cache.set({"answer": "TV works"}, question="does TV work?")
    result = cache.get(question="does TV work?")
    assert result == {"answer": "TV works"}


def test_cache_key_is_order_independent(cache):
    cache.set({"answer": "yes"}, question="q", sector="FMCG")
    # Same inputs, different kwarg order — same key
    result = cache.get(sector="FMCG", question="q")
    assert result == {"answer": "yes"}


def test_expired_entry_returns_none(cache):
    short_cache = ResponseCache(ttl_seconds=0, max_size=10)
    short_cache.set({"answer": "x"}, question="q")
    time.sleep(0.01)
    assert short_cache.get(question="q") is None


def test_max_size_evicts_oldest(cache):
    small_cache = ResponseCache(ttl_seconds=3600, max_size=2)
    small_cache.set({"v": 1}, question="q1")
    small_cache.set({"v": 2}, question="q2")
    small_cache.set({"v": 3}, question="q3")   # triggers eviction
    assert small_cache.size() == 2


def test_clear_empties_cache(cache):
    cache.set({"v": 1}, question="q")
    cache.clear()
    assert cache.size() == 0
```

- [ ] **Step 2: Run test**

```bash
cd backend
uv run pytest tests/unit/test_cache.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_cache.py
git commit -m "test: unit tests for ResponseCache"
```

---

## Task 4: Unit tests for config.py

**Files:**
- Create: `backend/tests/unit/test_config.py`

- [ ] **Step 1: Write tests**

```python
# tests/unit/test_config.py
import pytest
from app.core.config import Settings


def test_cors_origins_list_single():
    s = Settings(cors_origins="http://localhost:3000")
    assert s.cors_origins_list == ["http://localhost:3000"]


def test_cors_origins_list_multiple():
    s = Settings(cors_origins="http://localhost:3000,https://example.com")
    assert s.cors_origins_list == ["http://localhost:3000", "https://example.com"]


def test_is_production_false_by_default():
    s = Settings()
    assert not s.is_production


def test_is_production_true():
    s = Settings(app_env="production")
    assert s.is_production


def test_langfuse_enabled_when_both_keys_set():
    s = Settings(langfuse_public_key="pk-lf-abc", langfuse_secret_key="sk-lf-abc")
    assert s.langfuse_enabled


def test_langfuse_disabled_when_keys_missing():
    s = Settings(langfuse_public_key="", langfuse_secret_key="")
    assert not s.langfuse_enabled


def test_valid_sectors_contains_expected_values():
    s = Settings()
    assert "FMCG" in s.valid_sectors
    assert "Retail" in s.valid_sectors


def test_valid_budget_tiers_contains_expected_values():
    s = Settings()
    assert "under-100k" in s.valid_budget_tiers
    assert "2m-plus" in s.valid_budget_tiers
```

- [ ] **Step 2: Run tests**

```bash
cd backend
uv run pytest tests/unit/test_config.py -v
```

Expected: All 8 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_config.py
git commit -m "test: unit tests for Settings config"
```

---

## Task 5: Unit tests for generator.py

**Files:**
- Create: `backend/tests/unit/test_generator.py`

Note: We mock `litellm.completion` so no real API call occurs. The mock returns a realistic response object matching LiteLLM's actual return type.

- [ ] **Step 1: Write tests**

```python
# tests/unit/test_generator.py
import pytest
from unittest.mock import patch, MagicMock
from app.services.generator import build_prompt, generate


@pytest.fixture
def sample_chunks():
    return [
        {
            "text": "TV delivers £5.61 ROI per £1 spent across 141 brands.",
            "metadata": {"source_title": "Profit Ability 2", "page": 12},
            "distance": 0.1,
        }
    ]


def test_build_prompt_includes_question(sample_chunks):
    messages = build_prompt(
        question="Does TV work for FMCG?",
        chunks=sample_chunks,
    )
    user_content = messages[1]["content"]
    assert "Does TV work for FMCG?" in user_content


def test_build_prompt_includes_chunk_text(sample_chunks):
    messages = build_prompt(question="q", chunks=sample_chunks)
    user_content = messages[1]["content"]
    assert "TV delivers £5.61 ROI" in user_content


def test_build_prompt_includes_source_title(sample_chunks):
    messages = build_prompt(question="q", chunks=sample_chunks)
    user_content = messages[1]["content"]
    assert "Profit Ability 2" in user_content


def test_build_prompt_includes_sector_context(sample_chunks):
    messages = build_prompt(question="q", chunks=sample_chunks, sector="FMCG")
    user_content = messages[1]["content"]
    assert "FMCG" in user_content


def test_build_prompt_has_system_message(sample_chunks):
    messages = build_prompt(question="q", chunks=sample_chunks)
    assert messages[0]["role"] == "system"
    assert "Thinkbox" in messages[0]["content"]


def _make_litellm_response(content: str, model: str = "gpt-4o") -> MagicMock:
    """Build a MagicMock that looks like a LiteLLM completion response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content
    return mock_response


def test_generate_returns_answer_and_model(sample_chunks):
    with patch("app.services.generator.completion") as mock_completion:
        mock_completion.return_value = _make_litellm_response(
            "TV delivers strong ROI. Key sources: Profit Ability 2."
        )
        answer, model = generate(question="Does TV work?", chunks=sample_chunks)

    assert "ROI" in answer
    assert model == "gpt-4o"


def test_generate_falls_back_on_primary_failure(sample_chunks):
    fallback_content = "Based on research, TV works. Key sources: Profit Ability 2."
    call_count = 0

    def side_effect(**kwargs):
        nonlocal call_count
        call_count += 1
        if "gpt-4o" in kwargs.get("model", ""):
            raise RuntimeError("OpenAI down")
        return _make_litellm_response(fallback_content)

    with patch("app.services.generator.completion", side_effect=side_effect):
        answer, model = generate(question="q", chunks=sample_chunks)

    assert answer == fallback_content
    assert "claude" in model or "anthropic" in model or model != "gpt-4o"
    assert call_count == 2  # primary failed, fallback succeeded
```

- [ ] **Step 2: Run tests**

```bash
cd backend
uv run pytest tests/unit/test_generator.py -v
```

Expected: All 7 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_generator.py
git commit -m "test: unit tests for generator with mocked LiteLLM"
```

---

## Task 6: Unit tests for guardrails.py

**Files:**
- Create: `backend/tests/unit/test_guardrails.py`

- [ ] **Step 1: Write tests**

```python
# tests/unit/test_guardrails.py
import pytest
from unittest.mock import patch, MagicMock
from app.services.guardrails import check_input, check_output


def _mock_completion(decision: str) -> MagicMock:
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = decision
    return mock


@pytest.fixture
def sample_chunks():
    return [
        {
            "text": "TV delivers £5.61 ROI per £1 spent.",
            "metadata": {"source_title": "Profit Ability 2"},
            "distance": 0.1,
        }
    ]


def test_check_input_approved():
    with patch("app.services.guardrails.completion", return_value=_mock_completion("APPROVED")):
        approved, reason = check_input(question="When does TV work for FMCG?")
    assert approved is True


def test_check_input_rejected():
    with patch("app.services.guardrails.completion", return_value=_mock_completion("REJECTED")):
        approved, reason = check_input(question="Write me a poem about dogs")
    assert approved is False


def test_check_input_fails_open_on_error():
    with patch("app.services.guardrails.completion", side_effect=RuntimeError("API down")):
        approved, reason = check_input(question="anything")
    assert approved is True  # fail open
    assert "GUARDRAIL_ERROR" in reason


def test_check_output_approved(sample_chunks):
    with patch("app.services.guardrails.completion", return_value=_mock_completion("APPROVED")):
        approved, reason = check_output(
            answer="TV delivers £5.61 ROI. Key sources: Profit Ability 2.",
            chunks=sample_chunks,
        )
    assert approved is True


def test_check_output_rejected(sample_chunks):
    with patch("app.services.guardrails.completion", return_value=_mock_completion("REJECTED")):
        approved, reason = check_output(
            answer="TV delivers 99% ROI guaranteed.",  # hallucinated stat
            chunks=sample_chunks,
        )
    assert approved is False


def test_check_output_fails_open_on_error(sample_chunks):
    with patch("app.services.guardrails.completion", side_effect=RuntimeError("API down")):
        approved, reason = check_output(answer="anything", chunks=sample_chunks)
    assert approved is True  # fail open
```

- [ ] **Step 2: Run tests**

```bash
cd backend
uv run pytest tests/unit/test_guardrails.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_guardrails.py
git commit -m "test: unit tests for guardrails with mocked LiteLLM"
```

---

## Task 7: Unit tests for retriever.py

**Files:**
- Create: `backend/tests/unit/test_retriever.py`

We mock ChromaDB and the embedder so no SQLite or API calls are made.

- [ ] **Step 1: Write tests**

```python
# tests/unit/test_retriever.py
import pytest
from unittest.mock import patch, MagicMock


def _make_chroma_result(docs, metadatas, distances):
    """Build a ChromaDB-shaped query result."""
    return {
        "documents": [docs],
        "metadatas": [metadatas],
        "distances": [distances],
    }


@pytest.fixture(autouse=True)
def mock_chroma_and_embed():
    """Patch ChromaDB client and embed at module level so retriever never touches disk."""
    with patch("app.services.retriever.chromadb.PersistentClient") as mock_client, \
         patch("app.services.retriever.embed", return_value=[0.1] * 1536) as mock_embed, \
         patch("app.services.retriever._client", None), \
         patch("app.services.retriever._collection", None):

        mock_collection = MagicMock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        mock_collection.count.return_value = 42
        yield mock_collection, mock_embed


def test_retrieve_returns_chunks(mock_chroma_and_embed):
    mock_collection, _ = mock_chroma_and_embed
    mock_collection.query.return_value = _make_chroma_result(
        docs=["TV delivers strong ROI."],
        metadatas=[{"source_title": "Profit Ability 2", "page": 1}],
        distances=[0.15],
    )

    from app.services.retriever import retrieve
    chunks = retrieve(question="Does TV work?")

    assert len(chunks) == 1
    assert chunks[0]["text"] == "TV delivers strong ROI."
    assert chunks[0]["metadata"]["source_title"] == "Profit Ability 2"
    assert chunks[0]["distance"] == 0.15


def test_retrieve_calls_embed_with_question(mock_chroma_and_embed):
    mock_collection, mock_embed = mock_chroma_and_embed
    mock_collection.query.return_value = _make_chroma_result([], [], [])

    from app.services.retriever import retrieve
    retrieve(question="When does TV pay back?")

    mock_embed.assert_called_once_with("When does TV pay back?")


def test_retrieve_applies_sector_filter(mock_chroma_and_embed):
    mock_collection, _ = mock_chroma_and_embed
    mock_collection.query.return_value = _make_chroma_result([], [], [])

    from app.services.retriever import retrieve
    retrieve(question="q", sector="FMCG")

    call_kwargs = mock_collection.query.call_args.kwargs
    where = call_kwargs["where"]
    assert where is not None
    # Should contain an $or filter matching FMCG or 'all'
    assert "$or" in str(where)
    assert "FMCG" in str(where)


def test_retrieve_no_filter_when_no_sector(mock_chroma_and_embed):
    mock_collection, _ = mock_chroma_and_embed
    mock_collection.query.return_value = _make_chroma_result([], [], [])

    from app.services.retriever import retrieve
    retrieve(question="q")

    call_kwargs = mock_collection.query.call_args.kwargs
    assert call_kwargs["where"] is None


def test_get_doc_count(mock_chroma_and_embed):
    from app.services.retriever import get_doc_count, _collection
    # Force collection to be set
    import app.services.retriever as retriever_module
    mock_collection, _ = mock_chroma_and_embed
    retriever_module._collection = mock_collection
    count = get_doc_count()
    assert count == 42
```

- [ ] **Step 2: Run tests**

```bash
cd backend
uv run pytest tests/unit/test_retriever.py -v
```

Expected: All 5 tests PASS. If the `autouse` patch pattern causes import issues, adjust the patch targets — the key is mocking `chromadb.PersistentClient` and `app.services.retriever.embed`.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_retriever.py
git commit -m "test: unit tests for retriever with mocked ChromaDB"
```

---

## Task 8: Integration tests for API routes

**Files:**
- Create: `backend/tests/integration/test_routes.py`

These use FastAPI's `TestClient` and mock all services — no real API or DB calls.

- [ ] **Step 1: Write tests**

```python
# tests/integration/test_routes.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


@pytest.fixture
def client(sample_chunks):
    """Test client with all external services patched."""
    with patch("app.services.retriever.get_doc_count", return_value=142), \
         patch("app.services.retriever.get_collection"), \
         patch("app.services.retriever._client", None), \
         patch("app.services.retriever._collection", None):

        from app.main import app
        return TestClient(app)


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


def test_health_returns_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["chroma_docs"] == 142
    assert "version" in data


def test_query_returns_answer(client, sample_chunks):
    answer_text = "TV delivers £5.61 ROI. Key sources: Profit Ability 2."
    with patch("app.services.guardrails.check_input", return_value=(True, "APPROVED")), \
         patch("app.services.retriever.retrieve", return_value=sample_chunks), \
         patch("app.services.generator.generate", return_value=(answer_text, "gpt-4o")), \
         patch("app.services.guardrails.check_output", return_value=(True, "APPROVED")):

        resp = client.post("/api/query", json={"question": "When does TV advertising work?"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == answer_text
    assert data["model_used"] == "gpt-4o"
    assert data["cached"] is False
    assert len(data["sources"]) == 1


def test_query_rejects_off_topic(client):
    with patch("app.services.guardrails.check_input", return_value=(False, "REJECTED")):
        resp = client.post("/api/query", json={"question": "Write me a poem about dogs"})

    assert resp.status_code == 400


def test_query_returns_cached_response(client):
    from app.services.cache import cache
    cached_data = {
        "answer": "Cached answer about TV.",
        "sources": [{"title": "Profit Ability 2", "chunk": "excerpt...", "url": "https://thinkbox.tv"}],
        "model_used": "gpt-4o",
    }
    cache.set(cached_data, question="Does TV work for FMCG?")

    resp = client.post("/api/query", json={"question": "Does TV work for FMCG?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["cached"] is True
    assert data["answer"] == "Cached answer about TV."

    cache.clear()  # cleanup


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
```

- [ ] **Step 2: Run all tests**

```bash
cd backend
uv run pytest tests/ -v
```

Expected: All tests PASS. Total should be ~32 tests across unit and integration.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_routes.py
git commit -m "test: integration tests for all API routes"
```

---

## Task 9: Add LangFuse tracing to generator.py

**Files:**
- Modify: `backend/app/services/generator.py`

LangFuse tracing is conditional on `langfuse_enabled`. If keys are absent, tracing is a no-op. This keeps development lightweight.

- [ ] **Step 1: Write a test first**

Add to `tests/unit/test_generator.py`:

```python
def test_generate_does_not_crash_without_langfuse_keys(sample_chunks):
    """Tracing must be a no-op when LangFuse keys are absent."""
    with patch("app.services.generator.completion") as mock_completion, \
         patch("app.core.config.get_settings") as mock_get_settings:

        mock_settings = MagicMock()
        mock_settings.langfuse_enabled = False
        mock_settings.primary_model = "gpt-4o"
        mock_settings.fallback_model = "claude-3-5-sonnet-20241022"
        mock_get_settings.return_value = mock_settings

        mock_completion.return_value = _make_litellm_response(
            "TV works well. Key sources: Profit Ability 2."
        )
        # Re-import to pick up patched settings
        from importlib import reload
        import app.services.generator as gen_module
        answer, model = gen_module.generate(question="q", chunks=sample_chunks)
        assert "TV works" in answer
```

- [ ] **Step 2: Run this test — it should pass already (tracing not yet added)**

```bash
cd backend
uv run pytest tests/unit/test_generator.py::test_generate_does_not_crash_without_langfuse_keys -v
```

Expected: PASS (confirms no crash today either).

- [ ] **Step 3: Add LangFuse tracing to generator.py**

Replace `backend/app/services/generator.py` with:

```python
import logging
from litellm import completion
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# LangFuse client — lazy-initialised only if keys are configured
_langfuse = None


def _get_langfuse():
    global _langfuse
    if _langfuse is None and settings.langfuse_enabled:
        from langfuse import Langfuse
        _langfuse = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    return _langfuse


SYSTEM_PROMPT = """You are a senior TV advertising strategist with deep expertise
in UK media planning. You advise brands and agencies on when and how to invest
in TV advertising, drawing exclusively on Thinkbox research.

Rules you must follow:
1. Only cite statistics and findings from the provided research context.
2. Never invent figures, ROI numbers, or study names.
3. Always ground your advice in the specific context provided.
4. Be direct and practical — you are a planner giving real advice.
5. End every response with a 'Key sources' list referencing the documents used.
"""


def build_prompt(
    question: str,
    chunks: list[dict],
    sector: str | None = None,
    brand_stage: str | None = None,
    budget_tier: str | None = None,
    primary_goal: str | None = None,
) -> list[dict]:
    """Builds the messages list for the LLM call."""
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk["metadata"]
        context_parts.append(
            f"[{i}] Source: {meta.get('source_title', 'Unknown')} "
            f"(page {meta.get('page', '?')})\n{chunk['text']}"
        )
    context = "\n\n".join(context_parts)

    user_context_parts = []
    if sector:
        user_context_parts.append(f"Sector: {sector}")
    if brand_stage:
        user_context_parts.append(f"Brand stage: {brand_stage}")
    if budget_tier:
        user_context_parts.append(f"Budget tier: {budget_tier}")
    if primary_goal:
        user_context_parts.append(f"Primary goal: {primary_goal}")

    user_context = (
        "Brand context: " + " | ".join(user_context_parts)
        if user_context_parts
        else ""
    )

    user_message = f"""{user_context}

Question: {question}

Research context:
{context}

Please provide a specific, evidence-based answer using only the research above.
Include a 'Key sources' section at the end."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]


def generate(
    question: str,
    chunks: list[dict],
    sector: str | None = None,
    brand_stage: str | None = None,
    budget_tier: str | None = None,
    primary_goal: str | None = None,
) -> tuple[str, str]:
    """
    Calls LiteLLM with primary model, falls back to secondary on failure.
    Traces to LangFuse if keys are configured.
    Returns (answer_text, model_used).
    """
    messages = build_prompt(
        question=question,
        chunks=chunks,
        sector=sector,
        brand_stage=brand_stage,
        budget_tier=budget_tier,
        primary_goal=primary_goal,
    )

    lf = _get_langfuse()
    trace = lf.trace(name="query", input={"question": question, "sector": sector}) if lf else None

    for model in [settings.primary_model, settings.fallback_model]:
        try:
            logger.info(f"Calling LiteLLM with model: {model}")
            span = trace.span(name=f"llm-{model}") if trace else None

            response = completion(
                model=model,
                messages=messages,
                max_tokens=1000,
                temperature=0.3,
            )
            answer = response.choices[0].message.content
            logger.info(f"Generated {len(answer)} chars with {model}")

            if span:
                span.end(output={"answer": answer[:200], "model": model})
            if trace:
                trace.update(output={"model_used": model})

            return answer, model

        except Exception as e:
            logger.warning(f"Model {model} failed: {e}")
            if span:
                span.end(output={"error": str(e)})
            if model == settings.fallback_model:
                raise

    raise RuntimeError("All models failed")
```

- [ ] **Step 4: Run all tests to confirm nothing broke**

```bash
cd backend
uv run pytest tests/ -v
```

Expected: All tests PASS (same count as before).

- [ ] **Step 5: Commit**

```bash
git add app/services/generator.py
git commit -m "feat: add LangFuse tracing to generator (no-op when keys absent)"
```

---

## Task 10: Wire /api/ingest to ingest pipeline

The `/api/ingest` route currently returns a stub message. This task connects it to the real pipeline so documents can be ingested via the API.

**Files:**
- Modify: `backend/app/api/routes.py`
- Create: `backend/app/services/ingestor.py` (extract pipeline logic from scripts/ingest.py)

- [ ] **Step 1: Write failing test for the ingest route**

Add to `tests/integration/test_routes.py`:

```python
def test_ingest_valid_document(client):
    """Ingest route should call the ingest pipeline and return chunk count."""
    with patch("app.api.routes.run_ingest", return_value=5) as mock_ingest:
        resp = client.post(
            "/api/ingest",
            json={"source_path": "data/pdfs/profit-ability-2.pdf"},
            headers={"X-API-Key": "dev-key"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["chunks_added"] == 5
    mock_ingest.assert_called_once_with("data/pdfs/profit-ability-2.pdf")
```

- [ ] **Step 2: Run this test — verify it fails**

```bash
cd backend
uv run pytest tests/integration/test_routes.py::test_ingest_valid_document -v
```

Expected: FAIL — `run_ingest` not yet defined.

- [ ] **Step 3: Create app/services/ingestor.py**

This extracts the core logic from `scripts/ingest.py` as a callable function:

```python
# app/services/ingestor.py
import hashlib
import logging
from pathlib import Path

from app.core.config import get_settings
from app.services.embedder import embed_batch
from app.services.retriever import get_collection

logger = logging.getLogger(__name__)
settings = get_settings()

DOCUMENT_REGISTRY: dict[str, dict] = {
    "profit-ability-2.pdf": {
        "source_title": "Profit Ability 2",
        "source_url": "https://www.thinkbox.tv/research/thinkbox-research/profit-ability-2-the-business-case-for-advertising",
        "topic": "ROI",
        "sector": "all",
    },
    "profit-ability-1.pdf": {
        "source_title": "Profit Ability 1",
        "source_url": "https://www.thinkbox.tv/research/thinkbox-research/profit-ability-the-business-case-for-advertising",
        "topic": "ROI",
        "sector": "all",
    },
    "as-seen-on-tv.pdf": {
        "source_title": "As Seen on TV: Supercharging Small Business",
        "source_url": "https://www.thinkbox.tv/research/thinkbox-research/as-seen-on-tv-supercharging-your-small-business",
        "topic": "small_business",
        "sector": "all",
    },
    "peter-field-white-paper.pdf": {
        "source_title": "TV is at the Heart of Effectiveness",
        "source_url": "https://www.thinkbox.tv/research/reports/tv-is-at-the-heart-of-effectiveness-whitepaper-by-peter-field",
        "topic": "effectiveness",
        "sector": "all",
    },
    "payback-4.pdf": {
        "source_title": "Payback 4: Pathways to Profit",
        "source_url": "https://www.thinkbox.tv/research/thinkbox-research/payback-4",
        "topic": "ROI",
        "sector": "all",
    },
    "tv-viewing-report-2024.pdf": {
        "source_title": "TV Viewing Report 2024",
        "source_url": "https://www.thinkbox.tv/research/nickable-charts/viewing-and-audiences/tv-viewing-report",
        "topic": "viewing",
        "sector": "all",
    },
    "signalling-success.pdf": {
        "source_title": "Signalling Success",
        "source_url": "https://www.thinkbox.tv/research/thinkbox-research/signalling-success",
        "topic": "effectiveness",
        "sector": "all",
    },
    "demand-generator.pdf": {
        "source_title": "Demand Generator",
        "source_url": "https://www.thinkbox.tv/research/thinkbox-research/demand-generation",
        "topic": "planning",
        "sector": "all",
    },
}


def _extract_pages(pdf_path: Path) -> list[tuple[str, int]]:
    """Returns [(page_text, page_number), ...] skipping empty pages."""
    from pypdf import PdfReader
    reader = PdfReader(str(pdf_path))
    pages = []
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text()
        if text and text.strip():
            pages.append((text.strip(), i))
    return pages


def _chunk_text(text: str, page_number: int) -> list[dict]:
    """Splits text into overlapping word-based chunks."""
    words = text.split()
    chunks = []
    start = 0
    chunk_size = settings.chunk_size
    overlap = settings.chunk_overlap

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        if len(chunk_words) > 20:
            chunks.append({
                "text": " ".join(chunk_words),
                "page": page_number,
            })
        start += chunk_size - overlap

    return chunks


def run_ingest(source_path: str) -> int:
    """
    Ingests a single PDF at source_path into ChromaDB.
    Returns the number of chunks added. Raises ValueError for unknown documents.
    """
    pdf_path = Path(source_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {source_path}")

    doc_metadata = DOCUMENT_REGISTRY.get(pdf_path.name)
    if doc_metadata is None:
        raise ValueError(
            f"'{pdf_path.name}' not in DOCUMENT_REGISTRY. "
            "Add it to app/services/ingestor.py to ingest it."
        )

    pages = _extract_pages(pdf_path)
    if not pages:
        logger.warning(f"No text extracted from {pdf_path.name}")
        return 0

    all_chunks = []
    for page_text, page_num in pages:
        all_chunks.extend(_chunk_text(page_text, page_num))

    if not all_chunks:
        return 0

    collection = get_collection()
    total_added = 0
    batch_size = 50

    for batch_start in range(0, len(all_chunks), batch_size):
        batch = all_chunks[batch_start: batch_start + batch_size]
        embeddings = embed_batch([c["text"] for c in batch])
        ids, documents, metadatas = [], [], []

        for i, (chunk, _) in enumerate(zip(batch, embeddings)):
            chunk_index = batch_start + i
            chunk_id = hashlib.sha256(
                f"{doc_metadata['source_title']}_{chunk['page']}_{chunk_index}".encode()
            ).hexdigest()[:16]
            ids.append(chunk_id)
            documents.append(chunk["text"])
            metadatas.append({**doc_metadata, "page": chunk["page"], "chunk_index": chunk_index})

        collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        total_added += len(batch)

    logger.info(f"Ingested {total_added} chunks from {pdf_path.name}")
    return total_added
```

- [ ] **Step 4: Wire routes.py to run_ingest**

In `backend/app/api/routes.py`, replace the stub `/api/ingest` handler:

```python
# Add this import at the top of routes.py:
from app.services.ingestor import run_ingest

# Replace the stub handler:
@router.post("/ingest", dependencies=[Depends(verify_api_key)])
async def ingest(request: IngestRequest):
    logger.info(f"Ingest requested for: {request.source_path}")
    try:
        chunks_added = run_ingest(request.source_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": "Ingestion complete", "chunks_added": chunks_added}
```

- [ ] **Step 5: Run the new test**

```bash
cd backend
uv run pytest tests/integration/test_routes.py::test_ingest_valid_document -v
```

Expected: PASS.

- [ ] **Step 6: Run full test suite**

```bash
cd backend
uv run pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add app/services/ingestor.py app/api/routes.py
git commit -m "feat: wire /api/ingest to pipeline via ingestor service"
```

---

## Task 11: Implement test_retrieval.py smoke test

**Files:**
- Replace: `backend/scripts/test_retrieval.py`

This script tests retrieval quality against the real ChromaDB — it's a diagnostic tool, not part of the test suite. Run it manually after ingesting documents.

- [ ] **Step 1: Write the script**

```python
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
import sys
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.retriever import retrieve, get_doc_count

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
        "expected_source": None,  # any grounding is acceptable
    },
]


def run_smoke_test():
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

        chunks = retrieve(question=query["question"], sector=query["sector"], top_k=3)

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
    run_smoke_test()
```

- [ ] **Step 2: Commit**

```bash
git add scripts/test_retrieval.py
git commit -m "feat: implement test_retrieval.py smoke test script"
```

---

## Task 12: Write docker-compose.yml

**Files:**
- Create: `backend/docker-compose.yml` (move to project root)

Actually per CLAUDE.md the `docker-compose.yml` lives at the project root. The empty file is already there.

- [ ] **Step 1: Write the compose file**

```yaml
# docker-compose.yml (project root: tv-invest-advisor/)
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - APP_ENV=production
      - LOG_LEVEL=INFO
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - LANGFUSE_PUBLIC_KEY=${LANGFUSE_PUBLIC_KEY}
      - LANGFUSE_SECRET_KEY=${LANGFUSE_SECRET_KEY}
      - LANGFUSE_HOST=${LANGFUSE_HOST:-https://cloud.langfuse.com}
      - API_KEY=${API_KEY}
      - CORS_ORIGINS=${CORS_ORIGINS:-http://localhost:3000}
    volumes:
      - ./backend/chroma_db:/app/chroma_db
      - ./data/pdfs:/app/data/pdfs:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

- [ ] **Step 2: Create the Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files first (layer cache)
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --no-group dev

# Copy source
COPY app/ ./app/
COPY scripts/ ./scripts/

# Create directories that will be mounted as volumes
RUN mkdir -p chroma_db data/pdfs

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml backend/Dockerfile
git commit -m "feat: add docker-compose and Dockerfile for backend"
```

---

## HUMAN STEP A: Run the ingest script

> **Prompt to user:** The corpus ingestion requires real API keys (already in `.env`) and your PDF files. Two PDFs are present (`profit-ability-2.pdf`, `peter-field-white-paper.pdf`). You can ingest these now, and add more PDFs later.
>
> To download additional PDFs, visit https://www.thinkbox.tv/research/ and download the remaining reports listed in CLAUDE.md. Place them in `data/pdfs/`.
>
> When ready, run:
> ```bash
> cd backend
> uv run scripts/ingest.py
> ```
>
> This takes 2–3 minutes per PDF (embedding API calls). After it completes, run:
> ```bash
> uv run scripts/test_retrieval.py
> ```
> to verify retrieval quality. Paste the output here before continuing to the frontend.

---

## Task 13: Frontend — Advisor UI

> **Note:** This is a separate subsystem. Create a separate plan file: `docs/superpowers/plans/2026-05-25-frontend-advisor-ui.md` when ready to build the frontend.

The frontend needs to implement:
- A query form with `question` (textarea) + optional structured fields (sector, brand_stage, tv_history, primary_goal, budget_tier) as dropdowns
- A response panel displaying `answer` (markdown), `sources` as citation cards, `model_used` badge, and a `cached` indicator
- API calls to `http://localhost:8000/api/query`
- Error states (off-topic rejection, no documents, network error)

The frontend plan should be written separately once the backend is confirmed working end-to-end.

---

## Self-Review

### Spec coverage check

| CLAUDE.md requirement | Task covering it |
|---|---|
| config.py settings | Task 4 (tests) |
| FastAPI app | Task 8 (integration tests) |
| /api/query with guardrails + cache + retrieval + generation | Task 8 |
| /api/health with chroma_docs count | Task 8 |
| /api/ingest protected by API key | Tasks 8, 10 |
| Cache — hash of all inputs, TTL 7 days | Task 3 |
| Input guardrail (on-topic check) | Task 6, Task 8 |
| Output guardrail (hallucination check) | Task 6, Task 8 |
| LiteLLM primary + fallback | Task 5 |
| ChromaDB retrieval + metadata filtering | Task 7 |
| LangFuse tracing (conditional) | Task 9 |
| Ingest pipeline | Task 10, 11 |
| docker-compose | Task 12 |
| Ingest script | Task 11 |
| Frontend | Task 13 (deferred, separate plan) |

### Gaps addressed
- DOCUMENT_REGISTRY is duplicated between `scripts/ingest.py` and `app/services/ingestor.py` — this is intentional. The script is an offline tool; the service is the API-callable version. They are independent. If the corpus grows, keep both in sync.
- `scripts/ingest.py` is not modified — it remains a working offline tool. `ingestor.py` extracts the same logic for API-callable use.

### Type consistency
- `run_ingest(source_path: str) -> int` — matches usage in routes.py
- `retrieve(question, sector, brand_stage, topic, top_k) -> list[dict]` — matches existing signature
- `generate(question, chunks, sector, brand_stage, budget_tier, primary_goal) -> tuple[str, str]` — unchanged
- `check_input(question, sector, brand_stage) -> tuple[bool, str]` — unchanged
- `check_output(answer, chunks) -> tuple[bool, str]` — unchanged
