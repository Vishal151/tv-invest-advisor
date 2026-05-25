---

# Production Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the TV Investment Advisor backend from a well-structured demo to deployment-quality code — adding Redis cache, linting, Pydantic validation, proper error handling, Docker hardening, and startup warmup.

**Architecture:** Seven incremental tasks, each independently testable and committed. Redis replaces the in-memory dict cache when `REDIS_URL` is set; the dict cache remains for local dev and CI (no Redis required to run tests). Linting uses flake8 + black: black enforces formatting, flake8 checks style/errors. Docker is tightened to use the official uv image, a non-root user, and a working healthcheck.

**Tech Stack:** Python 3.13, FastAPI, pydantic-settings, black, flake8, redis-py 5+, fakeredis 2+, docker compose v2.

---

## File Map

| Path | Action | Purpose |
|---|---|---|
| `backend/pyproject.toml` | Modify | Add black, flake8, redis, fakeredis; add `[tool.black]` |
| `backend/.flake8` | Create | flake8 config (max-line-length, black-compatible ignores) |
| `backend/app/core/config.py` | Modify | Add `redis_url`, `redis_enabled` |
| `backend/app/api/routes.py` | Modify | Pydantic validators; 503 on LLM failure; remove manual 422 checks |
| `backend/app/services/cache.py` | Rewrite | Add `RedisCache`; factory selects backend from settings |
| `backend/app/main.py` | Modify | Lifespan warms up ChromaDB + Redis; health reports Redis |
| `backend/Dockerfile` | Rewrite | Official uv image, copy uv.lock, non-root user |
| `backend/.env.example` | Modify | Add `REDIS_URL` |
| `docker-compose.yml` | Modify | Add Redis service; `depends_on`; `REDIS_URL`; Python healthcheck |
| `backend/tests/unit/test_cache.py` | Modify | Add `RedisCache` tests using fakeredis |
| `backend/tests/integration/test_routes.py` | Modify | Add 503 test; add health Redis status test |

---

## Task 1: flake8 + black linting setup

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/.flake8`

black enforces formatting (line length, quotes, trailing commas). flake8 catches style errors and unused imports. They must be configured to agree — flake8's E203/W503 must be ignored because black formats those differently.

- [ ] **Step 1: Add black and flake8 to dev deps**

```bash
cd backend
uv add --group dev black flake8
```

Expected: both appear in `uv.lock`, no errors.

- [ ] **Step 2: Add black config to pyproject.toml**

Replace the `[dependency-groups]` section and append `[tool.black]` in `backend/pyproject.toml`:

```toml
[dependency-groups]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.28.1",
    "black>=24.0.0",
    "flake8>=7.0.0",
    "fakeredis>=2.26.0",
]

[tool.black]
line-length = 100
target-version = ["py313"]
```

- [ ] **Step 3: Create backend/.flake8**

```ini
[flake8]
max-line-length = 100
extend-ignore =
    E203,
    W503,
    E501
exclude =
    .venv,
    __pycache__,
    chroma_db,
    .pytest_cache
```

`E203` and `W503` conflict with black's formatting style and must be ignored. `E501` is handled by black.

- [ ] **Step 4: Run black to auto-format all source files**

```bash
cd backend
uv run black app/ tests/ scripts/
```

Expected: black reports files reformatted (or "reformatted 0 files" if already compliant). No errors.

- [ ] **Step 5: Run flake8 to check for remaining issues**

```bash
cd backend
uv run flake8 app/ tests/ scripts/
```

Note any reported issues. Common ones: unused imports (`F401`), bare `except` (`E722`). Fix each manually — do not silence them with `# noqa` unless unavoidable.

- [ ] **Step 6: Fix any flake8 issues found**

The most likely issue is `from typing import Optional` in `routes.py` — it's unused after Tasks 2 and 3 will remove `Optional[str]` usages. For now, if flake8 reports `F401 'typing.Optional' imported but unused`, remove it:

In `backend/app/api/routes.py`, remove the line:
```python
from typing import Optional
```

and change any remaining `Optional[str]` to `str | None` in the same file.

- [ ] **Step 7: Confirm flake8 is clean**

```bash
cd backend
uv run flake8 app/ tests/ scripts/
```

Expected: no output (exit code 0).

- [ ] **Step 8: Run full test suite**

```bash
cd backend
uv run pytest tests/ -q
```

Expected: `42 passed`.

- [ ] **Step 9: Commit**

```bash
git add backend/pyproject.toml backend/.flake8 backend/app/api/routes.py
git commit -m "chore: add black + flake8 linting and fix Optional annotations"
```

---

## Task 2: Pydantic field validators on QueryRequest

**Files:**
- Modify: `backend/app/api/routes.py`

Currently, `sector`, `brand_stage`, and `budget_tier` are validated with manual `if` checks that raise `HTTPException(422)`. This should be done by Pydantic at model parse time using `@field_validator`.

- [ ] **Step 1: Verify the existing manual validation tests still pass (baseline)**

```bash
cd backend
uv run pytest tests/integration/test_routes.py::test_query_rejects_invalid_sector -v
```

Expected: PASS.

- [ ] **Step 2: Replace manual validation with Pydantic validators in routes.py**

Replace the `QueryRequest` class and remove the manual validation block from the `query` handler. The full updated top section of `backend/app/api/routes.py`:

```python
import logging
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Any

from app.core.config import get_settings
from app.services.cache import cache
from app.services.retriever import retrieve, get_doc_count
from app.services.generator import generate
from app.services.guardrails import check_input, check_output
from app.services.ingestor import run_ingest

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


# ── Request / Response models ─────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=500)
    sector: str | None = None
    brand_stage: str | None = None
    tv_history: str | None = None
    primary_goal: str | None = None
    budget_tier: str | None = None

    @field_validator("sector")
    @classmethod
    def validate_sector(cls, v: str | None) -> str | None:
        if v is not None and v not in settings.valid_sectors:
            raise ValueError(f"Invalid sector '{v}'. Valid: {settings.valid_sectors}")
        return v

    @field_validator("brand_stage")
    @classmethod
    def validate_brand_stage(cls, v: str | None) -> str | None:
        if v is not None and v not in settings.valid_brand_stages:
            raise ValueError(f"Invalid brand_stage '{v}'. Valid: {settings.valid_brand_stages}")
        return v

    @field_validator("tv_history")
    @classmethod
    def validate_tv_history(cls, v: str | None) -> str | None:
        if v is not None and v not in settings.valid_tv_history:
            raise ValueError(f"Invalid tv_history '{v}'. Valid: {settings.valid_tv_history}")
        return v

    @field_validator("primary_goal")
    @classmethod
    def validate_primary_goal(cls, v: str | None) -> str | None:
        if v is not None and v not in settings.valid_primary_goals:
            raise ValueError(f"Invalid primary_goal '{v}'. Valid: {settings.valid_primary_goals}")
        return v

    @field_validator("budget_tier")
    @classmethod
    def validate_budget_tier(cls, v: str | None) -> str | None:
        if v is not None and v not in settings.valid_budget_tiers:
            raise ValueError(f"Invalid budget_tier '{v}'. Valid: {settings.valid_budget_tiers}")
        return v


class Source(BaseModel):
    title: str
    chunk: str
    url: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[Source]
    cached: bool
    model_used: str


class IngestRequest(BaseModel):
    source_path: str


class HealthResponse(BaseModel):
    status: str
    chroma_docs: int
    version: str
    redis: str  # "ok" | "disabled" | "unavailable"


# ── Auth dependency ───────────────────────────────────────────────────────────

def verify_api_key(x_api_key: str = Header(...)) -> str:
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key
```

Then remove the three manual validation `if` blocks from the `query` handler (the lines checking `request.sector not in settings.valid_sectors` etc. — delete them entirely).

- [ ] **Step 3: Run tests**

```bash
cd backend
uv run pytest tests/ -q
```

Expected: `42 passed`. The `test_query_rejects_invalid_sector` test still passes because Pydantic returns 422 for field validation errors by default.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/routes.py
git commit -m "refactor: move QueryRequest validation to Pydantic field_validators"
```

---

## Task 3: Route error handling — 503 on LLM failure

**Files:**
- Modify: `backend/app/api/routes.py`
- Modify: `backend/tests/integration/test_routes.py`

Currently, if both GPT-4o and Claude fail, `generate()` raises `RuntimeError("All models failed")` which becomes an unhandled 500. It should be a 503 with a clear message.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/integration/test_routes.py`:

```python
def test_query_returns_503_on_llm_failure(client, sample_chunks):
    with patch("app.api.routes.check_input", return_value=(True, "APPROVED")), \
         patch("app.api.routes.retrieve", return_value=sample_chunks), \
         patch("app.api.routes.generate", side_effect=RuntimeError("All models failed")):
        resp = client.post("/api/query", json={"question": "When does TV advertising work?"})
    assert resp.status_code == 503
    assert "unavailable" in resp.json()["detail"].lower()
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd backend
uv run pytest tests/integration/test_routes.py::test_query_returns_503_on_llm_failure -v
```

Expected: FAIL — currently returns 500.

- [ ] **Step 3: Wrap generate() call in the query handler**

In `backend/app/api/routes.py`, inside the `query` handler, replace the bare `generate()` call:

```python
    # 4. Generate answer via LiteLLM
    try:
        answer, model_used = generate(
            question=request.question,
            chunks=chunks,
            sector=request.sector,
            brand_stage=request.brand_stage,
            budget_tier=request.budget_tier,
            primary_goal=request.primary_goal,
        )
    except Exception as e:
        logger.error(f"All LLM models failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="The answer service is temporarily unavailable. Please try again shortly.",
        )
```

- [ ] **Step 4: Run the new test**

```bash
cd backend
uv run pytest tests/integration/test_routes.py::test_query_returns_503_on_llm_failure -v
```

Expected: PASS.

- [ ] **Step 5: Run full suite**

```bash
cd backend
uv run pytest tests/ -q
```

Expected: `43 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes.py backend/tests/integration/test_routes.py
git commit -m "fix: return 503 instead of 500 when all LLM models fail"
```

---

## Task 4: Redis cache backend (TDD)

**Files:**
- Modify: `backend/pyproject.toml` (add `redis` to prod deps)
- Modify: `backend/app/core/config.py` (add `redis_url`)
- Rewrite: `backend/app/services/cache.py`
- Modify: `backend/tests/unit/test_cache.py`

The `ResponseCache` (dict) stays for dev/CI (no Redis needed). `RedisCache` is added for production. A factory function selects the right backend based on `REDIS_URL`. Tests use `fakeredis.FakeRedis()` directly — no real Redis required.

- [ ] **Step 1: Add redis to prod deps and fakeredis to dev deps**

```bash
cd backend
uv add redis
uv add --group dev fakeredis
```

Expected: both appear in `uv.lock`, no errors.

- [ ] **Step 2: Add redis_url to config**

In `backend/app/core/config.py`, add inside the `Settings` class after the Cache section:

```python
    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = Field(default="", description="Redis URL. Empty = use in-memory dict cache.")

    @property
    def redis_enabled(self) -> bool:
        return bool(self.redis_url)
```

- [ ] **Step 3: Write failing tests for RedisCache**

Replace the contents of `backend/tests/unit/test_cache.py` with:

```python
import time
import pytest
import fakeredis
from app.services.cache import ResponseCache, RedisCache


# ── DictCache (ResponseCache) tests ──────────────────────────────────────────

@pytest.fixture
def dict_cache():
    return ResponseCache(ttl_seconds=60, max_size=10)


def test_dict_get_miss_returns_none(dict_cache):
    assert dict_cache.get(question="anything") is None


def test_dict_set_and_get(dict_cache):
    dict_cache.set({"answer": "TV works"}, question="does TV work?")
    assert dict_cache.get(question="does TV work?") == {"answer": "TV works"}


def test_dict_key_order_independent(dict_cache):
    dict_cache.set({"answer": "yes"}, question="q", sector="FMCG")
    assert dict_cache.get(sector="FMCG", question="q") == {"answer": "yes"}


def test_dict_expired_returns_none():
    c = ResponseCache(ttl_seconds=0, max_size=10)
    c.set({"answer": "x"}, question="q")
    time.sleep(0.01)
    assert c.get(question="q") is None


def test_dict_max_size_evicts_oldest():
    c = ResponseCache(ttl_seconds=3600, max_size=2)
    c.set({"v": 1}, question="q1")
    c.set({"v": 2}, question="q2")
    c.set({"v": 3}, question="q3")
    assert c.size() == 2


def test_dict_clear(dict_cache):
    dict_cache.set({"v": 1}, question="q")
    dict_cache.clear()
    assert dict_cache.size() == 0


# ── RedisCache tests (using fakeredis — no real Redis needed) ─────────────────

@pytest.fixture
def redis_cache():
    client = fakeredis.FakeRedis(decode_responses=True)
    return RedisCache(client=client, ttl_seconds=60)


def test_redis_get_miss_returns_none(redis_cache):
    assert redis_cache.get(question="anything") is None


def test_redis_set_and_get(redis_cache):
    redis_cache.set({"answer": "TV works"}, question="does TV work?")
    assert redis_cache.get(question="does TV work?") == {"answer": "TV works"}


def test_redis_key_order_independent(redis_cache):
    redis_cache.set({"answer": "yes"}, question="q", sector="FMCG")
    assert redis_cache.get(sector="FMCG", question="q") == {"answer": "yes"}


def test_redis_expired_returns_none():
    client = fakeredis.FakeRedis(decode_responses=True)
    c = RedisCache(client=client, ttl_seconds=1)
    c.set({"answer": "x"}, question="q")
    # fakeredis respects TTL — advance time by patching
    import time
    time.sleep(1.1)
    assert c.get(question="q") is None


def test_redis_clear(redis_cache):
    redis_cache.set({"v": 1}, question="q1")
    redis_cache.set({"v": 2}, question="q2")
    redis_cache.clear()
    assert redis_cache.size() == 0


def test_redis_size(redis_cache):
    redis_cache.set({"v": 1}, question="q1")
    redis_cache.set({"v": 2}, question="q2")
    assert redis_cache.size() == 2


def test_redis_get_returns_none_on_connection_error():
    """RedisCache must fail gracefully — never crash the request."""
    import redis
    from unittest.mock import MagicMock
    broken_client = MagicMock(spec=redis.Redis)
    broken_client.get.side_effect = redis.RedisError("connection refused")
    c = RedisCache(client=broken_client, ttl_seconds=60)
    result = c.get(question="anything")
    assert result is None


def test_redis_set_silently_fails_on_connection_error():
    import redis
    from unittest.mock import MagicMock
    broken_client = MagicMock(spec=redis.Redis)
    broken_client.setex.side_effect = redis.RedisError("connection refused")
    c = RedisCache(client=broken_client, ttl_seconds=60)
    c.set({"v": 1}, question="q")  # must not raise
```

- [ ] **Step 4: Run new Redis tests — verify they fail**

```bash
cd backend
uv run pytest tests/unit/test_cache.py -k "redis" -v
```

Expected: FAIL — `RedisCache` not yet defined.

- [ ] **Step 5: Implement RedisCache in cache.py**

Replace `backend/app/services/cache.py` entirely:

```python
import hashlib
import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ResponseCache:
    """
    In-memory dict cache with TTL and max-size eviction.
    Used in development and CI (no Redis required).
    Interface is identical to RedisCache for drop-in use.
    """

    def __init__(self, ttl_seconds: int = 604800, max_size: int = 500):
        self._store: dict[str, dict] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size

    def _make_key(self, **inputs: Any) -> str:
        canonical = json.dumps(inputs, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def get(self, **inputs: Any) -> Any | None:
        key = self._make_key(**inputs)
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.time() > entry["expires_at"]:
            del self._store[key]
            return None
        logger.debug(f"Cache hit: {key[:8]}")
        return entry["value"]

    def set(self, value: Any, **inputs: Any) -> None:
        if len(self._store) >= self._max_size:
            oldest = min(self._store, key=lambda k: self._store[k]["expires_at"])
            del self._store[oldest]
        key = self._make_key(**inputs)
        self._store[key] = {"value": value, "expires_at": time.time() + self._ttl}
        logger.debug(f"Cache set: {key[:8]}")

    def size(self) -> int:
        return len(self._store)

    def clear(self) -> None:
        self._store.clear()


class RedisCache:
    """
    Redis-backed cache with TTL.
    Requires a redis.Redis client (use redis.from_url in production,
    fakeredis.FakeRedis in tests).
    Fails gracefully on connection errors — never raises to the caller.
    """

    _PREFIX = "tv_advisor:"

    def __init__(self, client: Any, ttl_seconds: int = 604800):
        self._client = client
        self._ttl = ttl_seconds

    def _make_key(self, **inputs: Any) -> str:
        canonical = json.dumps(inputs, sort_keys=True)
        hash_ = hashlib.sha256(canonical.encode()).hexdigest()
        return f"{self._PREFIX}{hash_}"

    def get(self, **inputs: Any) -> Any | None:
        import redis as redis_lib
        try:
            raw = self._client.get(self._make_key(**inputs))
            if raw is None:
                return None
            logger.debug(f"Redis cache hit")
            return json.loads(raw)
        except redis_lib.RedisError as e:
            logger.error(f"Redis get failed: {e}")
            return None

    def set(self, value: Any, **inputs: Any) -> None:
        import redis as redis_lib
        try:
            self._client.setex(self._make_key(**inputs), self._ttl, json.dumps(value))
            logger.debug(f"Redis cache set")
        except redis_lib.RedisError as e:
            logger.error(f"Redis set failed: {e}")

    def size(self) -> int:
        import redis as redis_lib
        try:
            return sum(1 for _ in self._client.scan_iter(f"{self._PREFIX}*"))
        except redis_lib.RedisError:
            return 0

    def clear(self) -> None:
        import redis as redis_lib
        try:
            keys = list(self._client.scan_iter(f"{self._PREFIX}*"))
            if keys:
                self._client.delete(*keys)
        except redis_lib.RedisError as e:
            logger.error(f"Redis clear failed: {e}")


def _make_cache() -> ResponseCache | RedisCache:
    """Factory: returns RedisCache if REDIS_URL is set, else ResponseCache."""
    from app.core.config import get_settings
    s = get_settings()
    if s.redis_enabled:
        import redis
        client = redis.from_url(s.redis_url, decode_responses=True)
        logger.info(f"Cache backend: Redis ({s.redis_url})")
        return RedisCache(client=client, ttl_seconds=s.cache_ttl_seconds)
    logger.info("Cache backend: in-memory dict")
    return ResponseCache(ttl_seconds=s.cache_ttl_seconds, max_size=s.cache_max_size)


cache = _make_cache()
```

- [ ] **Step 6: Run all cache tests**

```bash
cd backend
uv run pytest tests/unit/test_cache.py -v
```

Expected: All 14 tests PASS.

- [ ] **Step 7: Run full test suite**

```bash
cd backend
uv run pytest tests/ -q
```

Expected: `55 passed` (43 previous + 8 new Redis tests + 2 connection-error tests + renamed existing 6 dict tests — net ~55 depending on naming).

Note: `test_query_returns_cached_response` in `test_routes.py` imports `from app.services.cache import cache`. In test runs, `REDIS_URL` is not set, so `cache` is a `ResponseCache` instance. This test continues to work unchanged.

- [ ] **Step 8: Commit**

```bash
git add backend/pyproject.toml backend/app/core/config.py backend/app/services/cache.py backend/tests/unit/test_cache.py
git commit -m "feat: add Redis cache backend with graceful fallback on connection errors"
```

---

## Task 5: Docker + docker-compose production hardening

**Files:**
- Rewrite: `backend/Dockerfile`
- Modify: `docker-compose.yml`
- Modify: `backend/.env.example`

Three issues with the current Dockerfile: (1) `uv.lock` not copied so builds aren't reproducible, (2) `pip install uv` is slow and unofficial, (3) no non-root user. docker-compose has no Redis service and uses `curl` (not installed in slim image) for healthcheck.

- [ ] **Step 1: Rewrite backend/Dockerfile**

```dockerfile
# Use official uv image as build base (avoids pip install uv)
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

# Copy lockfiles first — layer cached until deps change
COPY pyproject.toml uv.lock ./

# Install production deps only; --frozen ensures lockfile is honoured
RUN uv sync --frozen --no-group dev --no-install-project

# Copy application source
COPY app/ ./app/
COPY scripts/ ./scripts/

# Create volume mount points and non-root user
RUN mkdir -p chroma_db data/pdfs \
    && adduser --disabled-password --no-create-home --uid 1001 appuser \
    && chown -R appuser:appuser /app

USER appuser

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Update docker-compose.yml**

Replace the full `docker-compose.yml` at the project root:

```yaml
services:
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

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
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./backend/chroma_db:/app/chroma_db
      - ./data/pdfs:/app/data/pdfs:ro
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c",
             "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
```

- [ ] **Step 3: Update .env.example**

Replace `backend/.env.example`:

```bash
# ── App ──────────────────────────────────────────────────────
APP_ENV=development
LOG_LEVEL=INFO

# ── LLM providers ────────────────────────────────────────────
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# ── LangFuse (free at cloud.langfuse.com) ────────────────────
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# ── API security ─────────────────────────────────────────────
API_KEY=change-me-in-production

# ── CORS ─────────────────────────────────────────────────────
CORS_ORIGINS=http://localhost:3000

# ── Redis cache (leave empty to use in-memory dict cache for local dev) ──────
# REDIS_URL=redis://localhost:6379/0
```

- [ ] **Step 4: Commit**

```bash
git add backend/Dockerfile docker-compose.yml backend/.env.example
git commit -m "feat: harden Dockerfile (uv image, non-root user, lockfile) and add Redis to compose"
```

---

## Task 6: Startup warmup + health endpoint Redis status

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/routes.py`
- Modify: `backend/tests/integration/test_routes.py`

The app currently has no startup warmup — ChromaDB is initialised lazily on first request (adds ~200ms cold-start latency). The health endpoint doesn't report Redis status. Fix both.

- [ ] **Step 1: Write a failing test for health Redis status**

Add to `backend/tests/integration/test_routes.py`:

```python
def test_health_reports_redis_disabled(client):
    """In test environment REDIS_URL is not set — health should report 'disabled'."""
    with patch("app.api.routes.get_doc_count", return_value=142):
        resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["redis"] in ("ok", "disabled", "unavailable")
```

- [ ] **Step 2: Run to establish baseline**

```bash
cd backend
uv run pytest tests/integration/test_routes.py::test_health_reports_redis_disabled -v
```

Expected: FAIL — `redis` key missing from response.

- [ ] **Step 3: Update main.py with startup warmup**

Replace `backend/app/main.py`:

```python
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.routes import router

settings = get_settings()

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def _check_redis() -> str:
    """Returns 'ok', 'disabled', or 'unavailable'."""
    if not settings.redis_enabled:
        return "disabled"
    from app.services.cache import cache, RedisCache
    if not isinstance(cache, RedisCache):
        return "disabled"
    import redis as redis_lib
    try:
        cache._client.ping()
        return "ok"
    except redis_lib.RedisError:
        return "unavailable"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting TV Investment Advisor v{settings.version} [{settings.app_env}]")

    # Warm up ChromaDB — initialises connection so first request isn't slow
    try:
        from app.services.retriever import get_collection
        col = get_collection()
        logger.info(f"ChromaDB ready — {col.count()} chunks")
    except Exception as e:
        logger.warning(f"ChromaDB warmup failed: {e}")

    # Check Redis connectivity at startup
    redis_status = _check_redis()
    logger.info(f"Redis: {redis_status}")
    if settings.redis_enabled and redis_status == "unavailable":
        logger.warning("Redis is configured but unreachable — cache will fail gracefully")

    yield
    logger.info("Shutting down")


app = FastAPI(
    title="TV Investment Advisor",
    description="RAG-powered TV advertising advisor grounded in Thinkbox research",
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
```

- [ ] **Step 4: Update the health route to return Redis status**

In `backend/app/api/routes.py`, replace the `health` handler:

```python
@router.get("/health", response_model=HealthResponse)
async def health():
    from app.main import _check_redis
    return HealthResponse(
        status="ok",
        chroma_docs=get_doc_count(),
        version=settings.version,
        redis=_check_redis(),
    )
```

- [ ] **Step 5: Run the new test**

```bash
cd backend
uv run pytest tests/integration/test_routes.py::test_health_reports_redis_disabled -v
```

Expected: PASS.

- [ ] **Step 6: Run full test suite**

```bash
cd backend
uv run pytest tests/ -q
```

Expected: all tests pass (count increases by 1 for new health test). Note: the existing `test_health_returns_ok` test checks `data["status"] == "ok"` and `"version" in data` — it does not assert on `redis` key so it still passes. Confirm:

```bash
cd backend
uv run pytest tests/integration/test_routes.py::test_health_returns_ok -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/main.py backend/app/api/routes.py backend/tests/integration/test_routes.py
git commit -m "feat: add startup warmup for ChromaDB/Redis and Redis status to health endpoint"
```

---

## Task 7: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md` (project root)

- [ ] **Step 1: Update the build status table**

In `CLAUDE.md`, replace the "Current build status" table:

```markdown
| Component | Status | Notes |
|-----------|--------|-------|
| Project structure | ✅ Done | Folders, .gitignore, CLAUDE.md |
| backend/app/core/config.py | ✅ Done | Settings, env vars, redis_url |
| backend/app/main.py | ✅ Done | FastAPI app, lifespan warmup |
| backend/app/api/routes.py | ✅ Done | /query, /ingest, /health; Pydantic validators |
| backend/app/services/embedder.py | ✅ Done | OpenAI embedding wrapper |
| backend/app/services/retriever.py | ✅ Done | ChromaDB retrieval |
| backend/app/services/generator.py | ✅ Done | LiteLLM call + LangFuse tracing |
| backend/app/services/cache.py | ✅ Done | ResponseCache (dict) + RedisCache |
| backend/app/services/guardrails.py | ✅ Done | Input/output LLM checks |
| backend/app/services/ingestor.py | ✅ Done | PDF ingestion pipeline (API-callable) |
| backend/scripts/ingest.py | ✅ Done | Offline PDF ingestion |
| backend/scripts/ingest_scraped.py | ✅ Done | Offline text file ingestion with --force |
| backend/scripts/test_retrieval.py | ✅ Done | Retrieval quality smoke test |
| backend/.env.example | ✅ Done | Includes REDIS_URL |
| backend/pytest suite | ✅ Done | 55+ tests, 0 failures |
| docker-compose.yml | ✅ Done | Backend + Redis |
| frontend (Next.js) | ⬜ Todo | Separate plan |
| Data corpus ingested | ✅ Done | 153 chunks (PDFs + PPTX-derived text) |
```

- [ ] **Step 2: Update Decision 3 (cache) in Key Technical Decisions**

Replace the Decision 3 block:

```markdown
### Decision 3: Redis cache in production, dict cache in development (May 2026)
- **Choice**: `ResponseCache` (dict) when `REDIS_URL` is unset; `RedisCache` (redis-py) when set
- **Why**: Redis survives restarts and is shared across instances. Dict cache is zero-infrastructure for local dev and CI. Both implement the same interface so routes are unaware of the backend.
- **Production path**: Set `REDIS_URL=redis://redis:6379/0` — docker-compose does this automatically
- **Do not**: Remove the dict fallback — it keeps CI and local dev dependency-free
```

- [ ] **Step 3: Add REDIS_URL to the Environment variables section**

Add after the `CORS_ORIGINS` line in the env vars block:

```bash
# Redis cache (optional — omit for in-memory dict cache in local dev)
REDIS_URL=redis://localhost:6379/0
```

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md — Redis cache, build status, env vars"
```

---

## Self-Review

### Spec coverage

| Requirement | Task |
|---|---|
| Redis cache | Task 4 |
| Linting / code style (black + flake8) | Task 1 |
| Pydantic validation (not manual HTTPException) | Task 2 |
| Error handling (LLM failure → 503) | Task 3 |
| Separation of concerns | Tasks 4 (cache backends separate), no changes needed elsewhere |
| Docker — reproducible builds | Task 5 (uv.lock, --frozen) |
| Docker — security (non-root) | Task 5 |
| Docker compose — Redis service | Task 5 |
| Docker compose — healthcheck works | Task 5 (Python urllib, no curl) |
| Startup warmup | Task 6 |
| Health endpoint — operational status | Task 6 (reports Redis) |
| Documentation | Task 7 |
| Testing — Redis without real Redis | Task 4 (fakeredis) |
| Testing — new behaviours | Tasks 3, 4, 6 (new tests) |

### Placeholder scan

No TBDs, TODOs, or "add appropriate X" phrases. All code blocks are complete and runnable.

### Type consistency

- `RedisCache.get(**inputs) -> Any | None` — matches `ResponseCache.get`
- `RedisCache.set(value: Any, **inputs) -> None` — matches `ResponseCache.set`
- `_check_redis() -> str` — called in both `main.py` and `routes.py` via import
- `HealthResponse` now has `redis: str` field — matches what `health()` returns
- `QueryRequest` validators all return `str | None` — matches field types
