# Production Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add strict LLM output validation, LLM mock mode, Playwright E2E tests, and a single-container Dockerfile — four production patterns present in sibling projects but missing here.

**Architecture:** Tasks 1–3 build on each other (validation tightens the contract → mock mode enables offline E2E → E2E tests use mock mode). Task 4 is independent and can be done in a separate session. All changes are incremental with tests validated at each step.

**Tech Stack:** Pydantic v2, pytest-asyncio, Playwright 1.49, Node 22 + Python 3.13 multi-stage Docker.

---

## File structure

| File | Action | Purpose |
|------|--------|---------|
| `backend/app/models.py` | Create | Shared Pydantic models for LLM output (extracted from routes.py) |
| `backend/app/api/routes.py` | Modify | Import models from app.models instead of defining inline |
| `backend/app/services/generator.py` | Modify | `_parse_response` validates via `StructuredAnswer.model_validate_json`; add `MOCK_ANSWER` constant and mock short-circuit |
| `backend/app/services/guardrails.py` | Modify | Skip LLM calls when `settings.llm_mock` is True |
| `backend/app/services/retriever.py` | Modify | Return `MOCK_CHUNKS` when `settings.llm_mock` is True |
| `backend/app/core/config.py` | Modify | Add `llm_mock: bool = False` setting |
| `backend/.env.example` | Modify | Document `LLM_MOCK` flag |
| `backend/tests/unit/test_generator.py` | Modify | Rename `test_generate_falls_back_on_invalid_json` → asserts exception raised |
| `backend/tests/unit/test_mock_mode.py` | Create | Tests for mock short-circuits in generator, guardrails, retriever |
| `e2e/package.json` | Create | Playwright test runner project |
| `e2e/playwright.config.ts` | Create | Starts both servers, points at localhost:3000 |
| `e2e/tests/app.spec.ts` | Create | 4 E2E tests covering load, query, API health, refusal |
| `Dockerfile` | Create | Multi-stage: Node 22 build → Python 3.13 runtime, single port |
| `backend/app/main.py` | Modify | Conditionally mount static files when `STATIC_DIR` env var is set |
| `docker-compose.standalone.yml` | Create | One-container alternative (no Redis/nginx) for portfolio demos |

---

## Task 1: Extract shared models + strict Pydantic validation

**Context:** `StructuredAnswer` and its sub-models are defined in `routes.py` (lines 81–107) but `generator.py`'s `_parse_response()` uses manual `setdefault` fallbacks that silently swallow malformed LLM responses. This task moves the models to a shared location and makes `_parse_response()` raise loudly on bad schema so routes.py returns 503 instead of serving a silently broken answer.

**Files:**
- Create: `backend/app/models.py`
- Modify: `backend/app/api/routes.py` (lines 81–107)
- Modify: `backend/app/services/generator.py` (lines 1, 132–145)
- Modify: `backend/tests/unit/test_generator.py` (lines 226–239)

- [ ] **Step 1: Write the failing test**

Replace `test_generate_falls_back_on_invalid_json` (lines 226–239 of `backend/tests/unit/test_generator.py`) with a test that expects an exception:

```python
async def test_generate_raises_on_invalid_json(sample_chunks):
    """generate() raises when LLM returns plain prose — routes.py catches this as 503."""
    prose = "TV delivers strong returns. Based on Thinkbox research, brands see 5x ROI."
    with (
        patch(
            "app.services.generator.acompletion",
            new=AsyncMock(return_value=_make_litellm_response(prose)),
        ),
        patch("app.services.generator._get_langfuse", return_value=None),
    ):
        with pytest.raises(Exception):
            await generate(question="Does TV work?", chunks=sample_chunks)
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend && uv run pytest tests/unit/test_generator.py::test_generate_raises_on_invalid_json -v
```

Expected: `FAILED` — current `_parse_response` returns a fallback dict, so no exception is raised.

- [ ] **Step 3: Create `backend/app/models.py`**

```python
from pydantic import BaseModel


class AnswerStat(BaseModel):
    value: str
    unit: str
    context: str
    source: str
    page: int = 0


class AnswerChartBar(BaseModel):
    label: str
    value: float
    highlight: bool = False


class AnswerChart(BaseModel):
    title: str
    source: str
    unit: str
    bars: list[AnswerChartBar]


class StructuredAnswer(BaseModel):
    summary: list[str]
    stats: list[AnswerStat] = []
    chart: AnswerChart | None = None
    checklist: list[str] | None = None
    followups: list[str] = []
```

- [ ] **Step 4: Update `routes.py` to import from `app.models`**

Remove the four class definitions (lines 81–107) and add the import at the top of the imports block:

```python
from app.models import AnswerStat, AnswerChartBar, AnswerChart, StructuredAnswer
```

The `Source`, `QueryResponse`, `IngestRequest`, `HealthResponse` classes stay in routes.py — they are route-specific.

- [ ] **Step 5: Rewrite `_parse_response()` in `generator.py`**

Add the import at line 1 (after existing imports):

```python
from app.models import StructuredAnswer
```

Replace `_parse_response` (lines 132–145) with:

```python
def _parse_response(raw: str) -> dict:
    """Validate LLM JSON against StructuredAnswer schema. Raises on invalid input."""
    return StructuredAnswer.model_validate_json(raw).model_dump()
```

- [ ] **Step 6: Run all backend tests**

```bash
cd backend && uv run pytest tests/ -v
```

Expected: all tests `PASSED`. The updated `test_generate_raises_on_invalid_json` should pass. All integration tests in `test_routes.py` are unaffected (they mock `generate` at the routes level).

- [ ] **Step 7: Commit**

```bash
git add backend/app/models.py backend/app/api/routes.py backend/app/services/generator.py backend/tests/unit/test_generator.py
git commit -m "refactor: extract StructuredAnswer models and enforce strict Pydantic validation in generator"
```

---

## Task 2: LLM mock mode

**Context:** Running E2E tests or developing offline requires no real API key. This task adds `LLM_MOCK=true` env flag that short-circuits all LLM calls (generator, guardrails, retriever) and returns deterministic responses. Pattern from the `finally` project.

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/.env.example`
- Modify: `backend/app/services/generator.py`
- Modify: `backend/app/services/guardrails.py`
- Modify: `backend/app/services/retriever.py`
- Create: `backend/tests/unit/test_mock_mode.py`

- [ ] **Step 1: Write failing tests for mock mode**

Create `backend/tests/unit/test_mock_mode.py`:

```python
import pytest
from unittest.mock import patch, AsyncMock
from app.services.generator import generate
from app.services.guardrails import check_input, check_output
from app.services.retriever import retrieve
from app.core.config import get_settings


@pytest.fixture(autouse=True)
def enable_mock_mode(monkeypatch):
    monkeypatch.setattr(get_settings(), "llm_mock", True)
    yield
    monkeypatch.setattr(get_settings(), "llm_mock", False)


@pytest.fixture
def sample_chunks():
    return [
        {
            "text": "TV advertising delivered an average ROI of £5.61 for every £1 spent.",
            "metadata": {
                "source_title": "Profit Ability 2",
                "source_url": "https://www.thinkbox.tv/research",
                "topic": "ROI",
                "sector": "all",
                "page": 12,
                "chunk_index": 1,
            },
            "distance": 0.1,
        }
    ]


async def test_generate_returns_mock_response(sample_chunks):
    answer, model = await generate(question="Does TV work?", chunks=sample_chunks)
    assert model == "mock"
    assert isinstance(answer["summary"], list)
    assert len(answer["summary"]) > 0


async def test_generate_mock_does_not_call_litellm(sample_chunks):
    with patch("app.services.generator.acompletion") as mock_llm:
        await generate(question="Does TV work?", chunks=sample_chunks)
    mock_llm.assert_not_called()


async def test_check_input_approves_in_mock_mode():
    approved, reason = await check_input(question="anything goes in mock mode")
    assert approved is True


async def test_check_input_mock_does_not_call_litellm():
    with patch("app.services.guardrails.acompletion") as mock_llm:
        await check_input(question="test")
    mock_llm.assert_not_called()


async def test_check_output_approves_in_mock_mode(sample_chunks):
    approved, reason = await check_output(answer="any answer", chunks=sample_chunks)
    assert approved is True


async def test_retrieve_returns_mock_chunks():
    chunks = await retrieve(question="Does TV work?")
    assert len(chunks) > 0
    assert "text" in chunks[0]
    assert "metadata" in chunks[0]


async def test_retrieve_mock_does_not_call_embedder():
    with patch("app.services.retriever.embed") as mock_embed:
        await retrieve(question="test")
    mock_embed.assert_not_called()
```

- [ ] **Step 2: Run tests to confirm they all fail**

```bash
cd backend && uv run pytest tests/unit/test_mock_mode.py -v
```

Expected: all 7 tests `FAILED` — `llm_mock` attribute doesn't exist yet.

- [ ] **Step 3: Add `llm_mock` to settings**

In `backend/app/core/config.py`, add after the `langfuse_host` line (line 54):

```python
# ── Mock mode ──────────────────────────────────────────────────────────────
llm_mock: bool = Field(default=False, description="Return deterministic mock responses. Set LLM_MOCK=true for offline dev/E2E.")
```

- [ ] **Step 4: Update `.env.example`**

Add at the end of `backend/.env.example`:

```
# ── Mock mode (offline development / E2E testing) ────────────────────────
# LLM_MOCK=false
```

- [ ] **Step 5: Add mock short-circuit and `MOCK_ANSWER` to `generator.py`**

Add `MOCK_ANSWER` constant after the `STRICT_GROUNDING_ADDENDUM` block (after line 81):

```python
MOCK_ANSWER: dict = {
    "summary": [
        "Mock: TV advertising delivers strong ROI based on Thinkbox research.",
        "Mock: Brands investing consistently in TV outperform those that don't.",
    ],
    "stats": [
        {
            "value": "£5.61",
            "unit": "ROI per £1 spent",
            "context": "Average across 141 brands and 14 categories",
            "source": "Profit Ability 2",
            "page": 12,
        }
    ],
    "chart": None,
    "checklist": None,
    "followups": ["What is the best sector for TV advertising?"],
}
```

At the top of the `generate()` function body (before the `messages = build_prompt(...)` call), add:

```python
if settings.llm_mock:
    logger.info("LLM mock mode active — returning deterministic response")
    return MOCK_ANSWER.copy(), "mock"
```

- [ ] **Step 6: Add mock short-circuit to `guardrails.py`**

At the top of `check_input()`, after the `context_parts = []` line, add:

```python
if settings.llm_mock:
    return True, "APPROVED"
```

At the top of `check_output()`, before the `prompt = OUTPUT_GUARD_PROMPT...` line, add:

```python
if settings.llm_mock:
    return True, "APPROVED"
```

- [ ] **Step 7: Add `MOCK_CHUNKS` and mock short-circuit to `retriever.py`**

Add the constant after the module-level `settings = get_settings()` line:

```python
MOCK_CHUNKS: list[dict] = [
    {
        "text": "TV advertising delivered an average ROI of £5.61 for every £1 spent, "
                "based on analysis of 141 brands across 14 categories.",
        "metadata": {
            "source_title": "Profit Ability 2",
            "source_url": "https://www.thinkbox.tv/research/thinkbox-research/profit-ability-2",
            "topic": "ROI",
            "sector": "all",
            "page": 12,
            "chunk_index": 1,
        },
        "distance": 0.1,
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
```

At the top of `retrieve()`, before `from app.services.embedder import embed`, add:

```python
if settings.llm_mock:
    logger.info("LLM mock mode active — returning mock chunks")
    return MOCK_CHUNKS
```

- [ ] **Step 8: Run all tests**

```bash
cd backend && uv run pytest tests/ -v
```

Expected: all tests `PASSED` including all 7 new mock mode tests.

- [ ] **Step 9: Commit**

```bash
git add backend/app/core/config.py backend/.env.example backend/app/services/generator.py backend/app/services/guardrails.py backend/app/services/retriever.py backend/tests/unit/test_mock_mode.py
git commit -m "feat: add LLM_MOCK mode — deterministic responses for offline dev and E2E testing"
```

---

## Task 3: Playwright E2E tests

**Context:** Neither the frontend nor the backend has end-to-end test coverage. This task adds a Playwright suite in `e2e/` that starts both servers with `LLM_MOCK=true` and exercises the full query flow in a real browser. Pattern from the `finally` and `prelegal` projects.

**Files:**
- Create: `e2e/package.json`
- Create: `e2e/playwright.config.ts`
- Create: `e2e/tests/app.spec.ts`

- [ ] **Step 1: Create `e2e/package.json`**

```json
{
  "name": "tv-invest-advisor-e2e",
  "version": "1.0.0",
  "scripts": {
    "test": "playwright test",
    "test:ui": "playwright test --ui",
    "test:headed": "playwright test --headed"
  },
  "devDependencies": {
    "@playwright/test": "^1.49.0"
  }
}
```

- [ ] **Step 2: Install Playwright**

```bash
cd e2e && npm install && npx playwright install chromium
```

Expected: `chromium` browser downloaded.

- [ ] **Step 3: Create `e2e/playwright.config.ts`**

```typescript
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL: 'http://localhost:3000',
    headless: true,
  },
  webServer: [
    {
      command:
        'cd ../backend && LLM_MOCK=true APP_ENV=development uv run uvicorn app.main:app --host 0.0.0.0 --port 8000',
      url: 'http://localhost:8000/api/health',
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
    {
      command: 'cd ../frontend && NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev',
      url: 'http://localhost:3000',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
})
```

- [ ] **Step 4: Create `e2e/tests/app.spec.ts`**

```typescript
import { test, expect } from '@playwright/test'

test('health endpoint returns ok', async ({ request }) => {
  const res = await request.get('http://localhost:8000/api/health')
  expect(res.status()).toBe(200)
  const body = await res.json()
  expect(body.status).toBe('ok')
})

test('homepage loads with question input', async ({ page }) => {
  await page.goto('/')
  const textarea = page.getByPlaceholder('Ask Cue about your TV investment…')
  await expect(textarea).toBeVisible()
  const submitBtn = page.getByRole('button', { name: 'Ask' })
  await expect(submitBtn).toBeDisabled()
})

test('submit button enables when question is typed', async ({ page }) => {
  await page.goto('/')
  const textarea = page.getByPlaceholder('Ask Cue about your TV investment…')
  const submitBtn = page.getByRole('button', { name: 'Ask' })

  await textarea.fill('Does TV advertising work for FMCG brands?')
  await expect(submitBtn).toBeEnabled()
})

test('submitting a question shows a mock answer', async ({ page }) => {
  await page.goto('/')
  const textarea = page.getByPlaceholder('Ask Cue about your TV investment…')
  await textarea.fill('Does TV advertising work for FMCG brands?')

  await page.getByRole('button', { name: 'Ask' }).click()

  // Mock answer text rendered by AssistantBubble
  await expect(
    page.getByText('Mock: TV advertising delivers strong ROI based on Thinkbox research.')
  ).toBeVisible({ timeout: 20_000 })
})
```

- [ ] **Step 5: Run E2E tests**

```bash
cd e2e && npm test
```

Expected: all 4 tests `PASSED`. If the `submitting a question` test times out, confirm the backend is starting with `LLM_MOCK=true` by checking startup logs.

- [ ] **Step 6: Commit**

```bash
git add e2e/
git commit -m "feat: add Playwright E2E tests with LLM_MOCK mode — full query flow covered"
```

---

## Task 4: Single-container Dockerfile

**Context:** The current `docker-compose.yml` runs redis + backend + nginx as three separate containers. For portfolio demos, `prelegal` and `finally` both produce a single-container `docker run` experience. This task adds a root-level `Dockerfile` that compiles the frontend and serves it from FastAPI's `StaticFiles` — no nginx, no Redis needed (Redis is optional; in-memory cache is used when `REDIS_URL` is absent).

**Files:**
- Create: `Dockerfile` (project root)
- Modify: `backend/app/main.py`
- Create: `docker-compose.standalone.yml`

- [ ] **Step 1: Update `backend/app/main.py` to conditionally mount static files**

Add the import at the top of the existing imports in `main.py`:

```python
import os
from fastapi.staticfiles import StaticFiles
```

Add the following block at the very end of `main.py` — AFTER the `app.include_router(router, prefix="/api")` line — so API routes always take precedence:

```python
_static_dir = os.getenv("STATIC_DIR", "")
if _static_dir and os.path.isdir(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
```

- [ ] **Step 2: Verify existing tests still pass**

```bash
cd backend && uv run pytest tests/ -v
```

Expected: all tests `PASSED`. The `STATIC_DIR` env var is not set in test runs so the mount never activates.

- [ ] **Step 3: Create the root-level `Dockerfile`**

```dockerfile
# Stage 1: compile Next.js static export
FROM node:22-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci --quiet
COPY frontend/ .
# NEXT_PUBLIC_API_URL left empty — browser makes requests to relative /api/* URLs
RUN npm run build

# Stage 2: Python runtime serving both API and static files
FROM python:3.13-slim AS runtime
RUN pip install uv --quiet
WORKDIR /app

# Install Python deps first (cached until pyproject.toml changes)
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-group dev --no-install-project

# Copy backend source and compiled frontend
COPY backend/app/ ./app/
COPY backend/scripts/ ./scripts/
COPY --from=frontend-builder /frontend/out ./static

RUN mkdir -p chroma_db data/pdfs

ARG APP_UID=1001
ARG APP_GID=1001
RUN groupadd -g "${APP_GID}" appuser \
    && useradd -u "${APP_UID}" -g appuser --no-create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app

USER ${APP_UID}

ENV UV_CACHE_DIR=/app/.cache/uv
ENV STATIC_DIR=/app/static

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: Create `docker-compose.standalone.yml`**

```yaml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        APP_UID: ${UID:-1001}
        APP_GID: ${GID:-1001}
    user: "${UID:-1001}:${GID:-1001}"
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    volumes:
      - ./backend/chroma_db:/app/chroma_db
      - ./data/pdfs:/app/data/pdfs:ro
    restart: unless-stopped
    healthcheck:
      test:
        [
          "CMD",
          "python",
          "-c",
          "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')",
        ]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
```

- [ ] **Step 5: Build and smoke-test the standalone container**

```bash
docker compose -f docker-compose.standalone.yml up --build
```

In a second terminal:

```bash
curl http://localhost:8000/api/health
# Expected: {"status":"ok", ...}

curl http://localhost:8000/
# Expected: HTML response (Next.js index page)
```

- [ ] **Step 6: Stop and commit**

```bash
docker compose -f docker-compose.standalone.yml down
git add Dockerfile docker-compose.standalone.yml backend/app/main.py
git commit -m "feat: single-container Dockerfile — Next.js compiled into FastAPI StaticFiles"
```

---

## Self-review

**Spec coverage check:**
- ✅ Strict Pydantic validation on LLM output — Task 1
- ✅ LLM mock mode short-circuits generator, guardrails, retriever — Task 2
- ✅ E2E Playwright tests for full query flow — Task 3
- ✅ Single-container deployment option — Task 4

**Placeholder scan:** None found — all steps contain executable code or commands with expected output.

**Type consistency:**
- `StructuredAnswer` defined in Task 1 `models.py`, imported in `generator.py` (`_parse_response`) and `routes.py` — consistent.
- `MOCK_ANSWER` dict keys (`summary`, `stats`, `chart`, `checklist`, `followups`) match `StructuredAnswer` fields — consistent.
- `MOCK_CHUNKS` list-of-dict structure matches what `retrieve()` returns and what `generate()` accepts as `chunks` — consistent.
- `get_settings()` is `lru_cache` singleton — `monkeypatch.setattr(get_settings(), "llm_mock", True)` mutates the cached instance; `monkeypatch` restores on teardown — correct approach.
- `STATIC_DIR` env var in standalone `Dockerfile` matches the `os.getenv("STATIC_DIR", "")` check in `main.py` — consistent.
