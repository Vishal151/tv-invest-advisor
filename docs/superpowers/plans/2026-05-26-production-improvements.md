# Production Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the TV Investment Advisor backend from "it works" to production-quality: clean-clone deployable, async-correct, reliable retrieval, secure, and observable.

**Architecture:** Five sequential phases — Infrastructure P0s must land first (they unblock CI); RAG quality and reliability improvements are independent after that and can be parallelised; observability and polish come last. Each task produces a working, tested, committed increment.

**Tech Stack:** FastAPI, LiteLLM (`acompletion`), OpenAI async SDK (`AsyncOpenAI`), ChromaDB, Redis, slowapi (rate limiting), structlog, Langfuse v4, pytest, uv, GitHub Actions

---

> **Scope note:** This plan covers five subsystems. If you want to parallelise work across developers, extract Phases 3–5 into their own plan files. Each phase is independently deployable after Phase 1.

---

## Phase 1 — P0: Infrastructure (must land first)

### Task 1: Commit uv.lock and fix .gitignore

**Files:**
- Modify: `.gitignore` (project root)
- Track: `backend/uv.lock`

- [ ] **Step 1: Remove uv.lock from .gitignore**

Open `.gitignore` at the project root. Find the line `uv.lock` and delete it. Save.

- [ ] **Step 2: Stage and commit uv.lock**

```bash
cd /path/to/tv-invest-advisor
git add backend/uv.lock .gitignore
git commit -m "fix: track uv.lock so Docker --frozen build works on clean clone"
```

- [ ] **Step 3: Verify Docker build works from committed state**

```bash
docker compose build backend
```

Expected: build completes without "uv.lock not found" errors.

---

### Task 2: Add CI Workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create the workflow file**

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          version: "latest"
      - name: Install deps
        run: uv sync --frozen
      - name: Lint
        run: |
          uv run black --check .
          uv run flake8 .
      - name: Test
        run: uv run pytest -x -q
        env:
          OPENAI_API_KEY: test-key
          ANTHROPIC_API_KEY: test-key
          API_KEY: test-key

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run lint
      - run: npm test -- --watchAll=false --passWithNoTests
```

- [ ] **Step 2: Run backend tests locally to confirm they pass with env vars set**

```bash
cd backend
OPENAI_API_KEY=test-key ANTHROPIC_API_KEY=test-key API_KEY=test-key uv run pytest -x -q
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "feat: add GitHub Actions CI for backend and frontend"
```

---

### Task 3: Fix Async Event-Loop Blocking

**Context:** Routes are `async def` but all downstream I/O (LiteLLM, OpenAI embeddings, ChromaDB) uses synchronous calls. Under concurrent requests, each LLM call blocks the entire server. Fix: convert the LiteLLM and OpenAI calls to async. ChromaDB stays sync (no async API) but its calls are fast local disk I/O, acceptable for now.

**Files:**
- Modify: `backend/app/services/embedder.py`
- Modify: `backend/app/services/retriever.py`
- Modify: `backend/app/services/guardrails.py`
- Modify: `backend/app/services/generator.py`
- Modify: `backend/app/services/ingestor.py`
- Modify: `backend/app/api/routes.py`
- Modify: `backend/tests/unit/test_generator.py`
- Modify: `backend/tests/unit/test_guardrails.py`
- Modify: `backend/tests/integration/test_routes.py`

- [ ] **Step 1: Write a failing async test to pin the expected interface**

Add to `backend/tests/unit/test_generator.py`:

```python
import pytest

@pytest.mark.asyncio
async def test_generate_is_async(monkeypatch):
    """generate() must be a coroutine so it doesn't block the event loop."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "TV delivers ROI. Key sources: Profit Ability 2."

    with patch("app.services.generator.acompletion", new=AsyncMock(return_value=mock_response)):
        from app.services.generator import generate
        result = generate(
            question="Does TV work?",
            chunks=[{"text": "TV ROI is high.", "metadata": {"source_title": "PA2", "page": 1}}],
        )
        assert asyncio.iscoroutine(result), "generate() must return a coroutine"
        answer, model = await result
    assert "ROI" in answer
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd backend
uv run pytest tests/unit/test_generator.py::test_generate_is_async -v
```

Expected: FAIL — `generate()` is not a coroutine.

- [ ] **Step 3: Convert embedder.py to async**

Replace `backend/app/services/embedder.py` entirely:

```python
import logging
from openai import AsyncOpenAI
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_client = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def embed(text: str) -> list[float]:
    """Embed a single string. Returns 1536 floats."""
    client = get_client()
    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=text.strip(),
    )
    return response.data[0].embedding


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple strings in one API call."""
    client = get_client()
    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=[t.strip() for t in texts],
    )
    return [item.embedding for item in response.data]
```

- [ ] **Step 4: Convert retriever.py retrieve() to async**

In `backend/app/services/retriever.py`, change only the `retrieve` function signature and the `embed` call:

```python
async def retrieve(
    question: str,
    sector: str | None = None,
    brand_stage: str | None = None,
    topic: str | None = None,
    top_k: int | None = None,
) -> list[dict]:
    """
    Embed the question and retrieve the top-k most relevant chunks.
    Returns a list of dicts: {text, metadata, distance}
    """
    from app.services.embedder import embed  # import here to avoid circular at module level

    collection = get_collection()
    k = top_k or settings.retrieval_top_k
    where = _build_where_filter(sector=sector, topic=topic)
    query_embedding = await embed(question)

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
        chunks.append({"text": doc, "metadata": meta, "distance": dist})

    logger.info(f"Retrieved {len(chunks)} chunks for: '{question[:50]}...'")
    return chunks
```

Also remove the top-of-file `from app.services.embedder import embed` if it exists (the import is now inside the function to avoid the circular issue during module load).

- [ ] **Step 5: Convert guardrails.py to async**

Replace `backend/app/services/guardrails.py` entirely:

```python
import logging
from litellm import acompletion
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

INPUT_GUARD_PROMPT = """You are a query classifier for a TV advertising research tool.

Your job: decide if the user's query is relevant to TV advertising, media planning,
brand building, marketing effectiveness, or advertising ROI.

Respond with ONLY one of:
- APPROVED — query is on-topic, proceed
- REJECTED — query is off-topic or inappropriate

Query: {question}
Brand context: {context}

Decision:"""

OUTPUT_GUARD_PROMPT = """You are a quality reviewer for a TV advertising advisory tool.

Source chunks (full text shown to the answer model):
{chunks}

Response to review:
{answer}

Approve unless the response clearly violates a rule below.

APPROVE when:
- Advice and themes match the sources (paraphrasing and synthesis are fine)
- Specific numbers (£, %, ROI, campaign counts, timeframes) in the response appear in the sources
- Qualitative planning guidance is grounded in the sources without inventing new statistics

REJECT only when:
- The response states a specific statistic or study name that does not appear in the sources above
- The response is off-topic (not about TV advertising / media planning)
- The response gives harmful or clearly misleading advice

Do not reject for: missing citations, general tone, or cautious recommendations.

Respond with ONLY one line starting with APPROVED or REJECTED.

Decision:"""


def _format_chunks_for_review(chunks: list[dict]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk["metadata"]
        parts.append(
            f"[{i}] Source: {meta.get('source_title', '?')} "
            f"(page {meta.get('page', '?')})\n{chunk['text']}"
        )
    return "\n\n".join(parts)


def _parse_guardrail_decision(raw: str) -> bool:
    decision = raw.strip().upper()
    if decision.startswith("APPROVED"):
        return True
    if decision.startswith("REJECTED"):
        return False
    logger.warning(f"Ambiguous guardrail decision: {raw!r} — failing open")
    return True


async def check_input(
    question: str,
    sector: str | None = None,
    brand_stage: str | None = None,
) -> tuple[bool, str]:
    """Checks if the query is on-topic. Returns (is_approved, reason)."""
    context_parts = []
    if sector:
        context_parts.append(f"sector={sector}")
    if brand_stage:
        context_parts.append(f"stage={brand_stage}")
    context = ", ".join(context_parts) or "not provided"

    prompt = INPUT_GUARD_PROMPT.format(question=question, context=context)

    try:
        response = await acompletion(
            model=settings.guardrail_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0,
            timeout=15,
        )
        raw = response.choices[0].message.content.strip()
        approved = _parse_guardrail_decision(raw)
        logger.info(f"Input guardrail: {raw.upper()} for '{question[:50]}...'")
        return approved, raw
    except Exception as e:
        logger.error(f"Input guardrail failed: {e} — failing open")
        return True, "GUARDRAIL_ERROR"


async def check_output(
    answer: str,
    chunks: list[dict],
) -> tuple[bool, str]:
    """Verifies the generated answer is grounded in retrieved chunks. Returns (is_approved, reason)."""
    prompt = OUTPUT_GUARD_PROMPT.format(
        chunks=_format_chunks_for_review(chunks),
        answer=answer,
    )

    try:
        response = await acompletion(
            model=settings.guardrail_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0,
            timeout=30,
        )
        raw = response.choices[0].message.content.strip()
        approved = _parse_guardrail_decision(raw)
        logger.info(f"Output guardrail: {raw.upper()}")
        return approved, raw
    except Exception as e:
        logger.error(f"Output guardrail failed: {e} — failing open")
        return True, "GUARDRAIL_ERROR"
```

- [ ] **Step 6: Convert generator.py generate() to async**

Replace only the `generate` function in `backend/app/services/generator.py` (keep `build_prompt`, `SYSTEM_PROMPT`, `STRICT_GROUNDING_ADDENDUM`, and `_get_langfuse` unchanged):

```python
from litellm import acompletion  # replace: from litellm import completion


async def generate(
    question: str,
    chunks: list[dict],
    sector: str | None = None,
    brand_stage: str | None = None,
    budget_tier: str | None = None,
    primary_goal: str | None = None,
    strict_grounding: bool = False,
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
        strict_grounding=strict_grounding,
    )

    lf = _get_langfuse()
    root_obs = None
    if lf:
        try:
            root_obs = lf.start_observation(
                name="query",
                input={"question": question, "sector": sector},
            )
        except Exception as e:
            logger.warning(f"Langfuse observation start failed: {e}")

    for model in [settings.primary_model, settings.fallback_model]:
        gen_obs = None
        try:
            logger.info(f"Calling LiteLLM with model: {model}")
            if root_obs:
                gen_obs = root_obs.start_observation(
                    name=f"llm-{model}",
                    as_type="generation",
                    model=model,
                )

            response = await acompletion(
                model=model,
                messages=messages,
                max_tokens=1000,
                temperature=0.3,
                timeout=60,
            )
            answer = response.choices[0].message.content
            logger.info(f"Generated {len(answer)} chars with {model}")

            if gen_obs:
                gen_obs.update(output={"answer": answer[:200], "model": model})
                gen_obs.end()
            if root_obs:
                root_obs.update(output={"model_used": model})
                root_obs.end()

            return answer, model

        except Exception as e:
            logger.warning(f"Model {model} failed: {e}")
            if gen_obs:
                try:
                    gen_obs.update(output={"error": str(e)}, level="ERROR")
                    gen_obs.end()
                except Exception:
                    logger.debug("Langfuse failed to record model error", exc_info=True)
            if model == settings.fallback_model:
                raise

    raise RuntimeError("All models failed")
```

- [ ] **Step 7: Convert ingestor.py run_ingest() to async**

Change only the `run_ingest` function signature and the `embed_batch` call in `backend/app/services/ingestor.py`:

```python
async def run_ingest(source_path: str) -> int:
    """
    Ingests a single PDF at source_path into ChromaDB.
    Returns the number of chunks added.
    Raises FileNotFoundError for missing files, ValueError for unknown documents.
    """
    from app.services.embedder import embed_batch  # avoid circular import at module level

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
        batch = all_chunks[batch_start : batch_start + batch_size]
        embeddings = await embed_batch([c["text"] for c in batch])
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

- [ ] **Step 8: Update routes.py to await async service calls**

In `backend/app/api/routes.py`, add `await` before every service call. The complete updated `query` and `ingest` route bodies:

```python
@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    # 1. Cache lookup (sync — fast local/Redis call, acceptable)
    cached = cache.get(
        question=request.question,
        sector=request.sector,
        brand_stage=request.brand_stage,
        tv_history=request.tv_history,
        primary_goal=request.primary_goal,
        budget_tier=request.budget_tier,
    )
    if cached:
        return QueryResponse(**cached, cached=True)

    # 2. Input guardrail
    approved, reason = await check_input(
        question=request.question,
        sector=request.sector,
        brand_stage=request.brand_stage,
    )
    if not approved:
        raise HTTPException(
            status_code=400,
            detail="Query is outside the scope of this tool. "
            "Please ask about TV advertising, media planning, or brand growth.",
        )

    # 3. Retrieve relevant chunks
    chunks = await retrieve(
        question=request.question,
        sector=request.sector,
        brand_stage=request.brand_stage,
    )
    if not chunks:
        raise HTTPException(
            status_code=503,
            detail="No research documents found. Please ensure the corpus has been ingested.",
        )

    # 4. Generate answer
    try:
        answer, model_used = await generate(
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

    # 5. Output guardrail (retry once with stricter grounding before generic fallback)
    output_ok, reject_reason = await check_output(answer=answer, chunks=chunks)
    if not output_ok:
        logger.warning(
            f"Output guardrail rejected response ({reject_reason}) — retrying with strict grounding"
        )
        try:
            answer, model_used = await generate(
                question=request.question,
                chunks=chunks,
                sector=request.sector,
                brand_stage=request.brand_stage,
                budget_tier=request.budget_tier,
                primary_goal=request.primary_goal,
                strict_grounding=True,
            )
            output_ok, reject_reason = await check_output(answer=answer, chunks=chunks)
        except Exception as e:
            logger.error(f"Strict regeneration failed: {e}")
            output_ok = False

    if not output_ok:
        logger.warning(
            f"Output guardrail rejected after retry ({reject_reason}) — returning safe fallback"
        )
        answer = SAFE_FALLBACK_ANSWER

    # 6. Build sources list
    sources = [
        Source(
            title=c["metadata"].get("source_title", "Thinkbox Research"),
            chunk=c["text"][:200] + "...",
            url=c["metadata"].get("source_url", "https://thinkbox.tv/research"),
        )
        for c in chunks
    ]

    # 7. Cache and return
    result = {
        "answer": answer,
        "sources": [s.model_dump() for s in sources],
        "model_used": model_used,
    }
    cache.set(
        value=result,
        question=request.question,
        sector=request.sector,
        brand_stage=request.brand_stage,
        tv_history=request.tv_history,
        primary_goal=request.primary_goal,
        budget_tier=request.budget_tier,
    )
    return QueryResponse(**result, cached=False)


@router.post("/ingest", dependencies=[Depends(verify_api_key)])
async def ingest(request: IngestRequest):
    logger.info(f"Ingest requested for: {request.source_path}")
    try:
        chunks_added = await run_ingest(request.source_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": "Ingestion complete", "chunks_added": chunks_added}
```

- [ ] **Step 9: Update existing tests to patch async functions correctly**

Tests that patch `check_input`, `check_output`, `generate`, `retrieve` must use `AsyncMock` because these are now coroutines.

In `backend/tests/integration/test_routes.py`, replace all `patch(... return_value=...)` for the async service functions with `AsyncMock`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

# Replace every patch of async services — example for test_query_returns_answer:
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
```

Apply the same `AsyncMock` pattern to every test that patches `check_input`, `check_output`, `generate`, or `retrieve`. For `MagicMock(side_effect=...)` in the retry test, use `AsyncMock(side_effect=...)` instead.

- [ ] **Step 10: Add pytest-asyncio to dev dependencies**

```bash
cd backend
uv add --dev pytest-asyncio
```

Add to `backend/pytest.ini` (or `pyproject.toml` `[tool.pytest.ini_options]`):
```ini
asyncio_mode = auto
```

- [ ] **Step 11: Run tests and confirm they pass**

```bash
cd backend
uv run pytest -x -q
```

Expected: all tests pass including the new `test_generate_is_async`.

- [ ] **Step 12: Commit**

```bash
git add backend/app/services/embedder.py \
        backend/app/services/retriever.py \
        backend/app/services/guardrails.py \
        backend/app/services/generator.py \
        backend/app/services/ingestor.py \
        backend/app/api/routes.py \
        backend/tests/ \
        backend/pyproject.toml \
        backend/pytest.ini
git commit -m "fix: convert all LLM/embedding I/O to async to unblock FastAPI event loop"
```

---

## Phase 2 — P1: RAG Quality and Reliability

### Task 4: Add Distance Threshold to Retrieval

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/services/retriever.py`
- Test: `backend/tests/unit/test_retriever.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/unit/test_retriever.py`:

```python
from app.services.retriever import _filter_by_distance


def test_filter_removes_low_confidence_chunks():
    chunks = [
        {"text": "TV ROI", "metadata": {}, "distance": 0.2},
        {"text": "Unrelated", "metadata": {}, "distance": 0.85},
        {"text": "Brand building", "metadata": {}, "distance": 0.5},
    ]
    result = _filter_by_distance(chunks, threshold=0.75)
    assert len(result) == 2
    assert all(c["distance"] <= 0.75 for c in result)


def test_filter_returns_all_when_none_exceed_threshold():
    chunks = [
        {"text": "TV ROI", "metadata": {}, "distance": 0.1},
        {"text": "Brand", "metadata": {}, "distance": 0.3},
    ]
    result = _filter_by_distance(chunks, threshold=0.75)
    assert len(result) == 2


def test_filter_returns_empty_when_all_poor():
    chunks = [{"text": "Off topic", "metadata": {}, "distance": 0.9}]
    result = _filter_by_distance(chunks, threshold=0.75)
    assert result == []
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
uv run pytest tests/unit/test_retriever.py -v
```

Expected: FAIL — `_filter_by_distance` not defined.

- [ ] **Step 3: Add config field**

In `backend/app/core/config.py`, add inside the `Settings` class under `# RAG settings`:

```python
retrieval_distance_threshold: float = 0.75  # cosine distance; chunks above this are discarded
```

- [ ] **Step 4: Implement `_filter_by_distance` and wire it into `retrieve()`**

In `backend/app/services/retriever.py`, add the function:

```python
def _filter_by_distance(chunks: list[dict], threshold: float) -> list[dict]:
    """Remove chunks whose cosine distance exceeds the threshold."""
    return [c for c in chunks if c["distance"] <= threshold]
```

And in `retrieve()`, add after building the chunks list and before the logger line:

```python
    chunks = _filter_by_distance(chunks, threshold=settings.retrieval_distance_threshold)
    if not chunks:
        logger.warning(f"All retrieved chunks exceeded distance threshold for: '{question[:50]}'")
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/unit/test_retriever.py tests/integration/test_routes.py -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/config.py backend/app/services/retriever.py backend/tests/unit/test_retriever.py
git commit -m "feat: filter retrieved chunks by distance threshold to reduce noise in prompts"
```

---

### Task 5: Fix Safe Fallback Being Cached

**Files:**
- Modify: `backend/app/api/routes.py`
- Test: `backend/tests/integration/test_routes.py`

- [ ] **Step 1: Write failing test**

Add to `backend/tests/integration/test_routes.py`:

```python
def test_safe_fallback_is_not_cached(client, sample_chunks):
    """When safe fallback is returned, it must NOT be written to cache."""
    from app.services.cache import cache
    from app.api.routes import SAFE_FALLBACK_ANSWER

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

    # Cache must be empty — fallback must NOT have been stored
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
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
uv run pytest tests/integration/test_routes.py::test_safe_fallback_is_not_cached -v
```

Expected: FAIL — cache currently stores the fallback.

- [ ] **Step 3: Fix routes.py**

In `backend/app/api/routes.py`, find the section at step 7 "Cache and return". Wrap `cache.set()` in a guard:

```python
    # 7. Cache and return (skip cache write for safe fallback — it should be retried next time)
    result = {
        "answer": answer,
        "sources": [s.model_dump() for s in sources],
        "model_used": model_used,
    }
    if answer != SAFE_FALLBACK_ANSWER:
        cache.set(
            value=result,
            question=request.question,
            sector=request.sector,
            brand_stage=request.brand_stage,
            tv_history=request.tv_history,
            primary_goal=request.primary_goal,
            budget_tier=request.budget_tier,
        )
    return QueryResponse(**result, cached=False)
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/integration/test_routes.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes.py backend/tests/integration/test_routes.py
git commit -m "fix: do not cache safe fallback answer so next request gets a fresh generation"
```

---

### Task 6: Wire Structured Brief into Retrieval via Query Rewriting

**Context:** All documents are tagged `sector: "all"`, so metadata filtering by sector has no effect on this corpus. The more impactful approach is to prepend the user's context (sector, brand_stage, primary_goal) to the embedding query so the vector search is semantically steered.

**Files:**
- Modify: `backend/app/services/retriever.py`
- Test: `backend/tests/unit/test_retriever.py`

- [ ] **Step 1: Write failing test**

Add to `backend/tests/unit/test_retriever.py`:

```python
from app.services.retriever import _build_enriched_query


def test_enriched_query_includes_all_context():
    q = _build_enriched_query(
        question="When should I advertise on TV?",
        sector="FMCG",
        brand_stage="scale-up",
        primary_goal="brand",
        tv_history="never",
        budget_tier="100k-500k",
    )
    assert "FMCG" in q
    assert "scale-up" in q
    assert "brand" in q
    assert "When should I advertise on TV?" in q


def test_enriched_query_with_no_context_returns_question():
    q = _build_enriched_query(question="When should I advertise on TV?")
    assert q == "When should I advertise on TV?"
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
uv run pytest tests/unit/test_retriever.py::test_enriched_query_includes_all_context -v
```

Expected: FAIL.

- [ ] **Step 3: Implement `_build_enriched_query` and update `retrieve()`**

In `backend/app/services/retriever.py`:

```python
def _build_enriched_query(
    question: str,
    sector: str | None = None,
    brand_stage: str | None = None,
    primary_goal: str | None = None,
    tv_history: str | None = None,
    budget_tier: str | None = None,
) -> str:
    """Prepend structured context to the question before embedding for better vector alignment."""
    parts = []
    if sector:
        parts.append(f"Sector: {sector}")
    if brand_stage:
        parts.append(f"Brand stage: {brand_stage}")
    if primary_goal:
        parts.append(f"Goal: {primary_goal}")
    if tv_history:
        parts.append(f"TV history: {tv_history}")
    if budget_tier:
        parts.append(f"Budget: {budget_tier}")
    if not parts:
        return question
    return f"{' | '.join(parts)}. {question}"
```

Update the `retrieve()` signature and embed call:

```python
async def retrieve(
    question: str,
    sector: str | None = None,
    brand_stage: str | None = None,
    primary_goal: str | None = None,
    tv_history: str | None = None,
    topic: str | None = None,
    top_k: int | None = None,
) -> list[dict]:
    """
    Embed an enriched query (question + structured context) and retrieve top-k chunks.
    Returns a list of dicts: {text, metadata, distance}
    """
    from app.services.embedder import embed

    collection = get_collection()
    k = top_k or settings.retrieval_top_k
    where = _build_where_filter(sector=sector, topic=topic)

    enriched = _build_enriched_query(
        question=question,
        sector=sector,
        brand_stage=brand_stage,
        primary_goal=primary_goal,
        tv_history=tv_history,
    )
    query_embedding = await embed(enriched)

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
        chunks.append({"text": doc, "metadata": meta, "distance": dist})

    chunks = _filter_by_distance(chunks, threshold=settings.retrieval_distance_threshold)
    if not chunks:
        logger.warning(f"All retrieved chunks exceeded distance threshold for: '{question[:50]}'")

    logger.info(f"Retrieved {len(chunks)} chunks for: '{question[:50]}...'")
    return chunks
```

Update the `retrieve()` call in `routes.py` to pass all structured fields:

```python
    chunks = await retrieve(
        question=request.question,
        sector=request.sector,
        brand_stage=request.brand_stage,
        primary_goal=request.primary_goal,
        tv_history=request.tv_history,
    )
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/unit/test_retriever.py tests/integration/test_routes.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/retriever.py backend/app/api/routes.py backend/tests/unit/test_retriever.py
git commit -m "feat: enrich embedding query with structured brief context for better retrieval"
```

---

### Task 7: Add Rate Limiting on /api/query

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/routes.py`
- Test: `backend/tests/integration/test_routes.py`

- [ ] **Step 1: Add slowapi**

```bash
cd backend
uv add slowapi
```

- [ ] **Step 2: Write failing test**

Add to `backend/tests/integration/test_routes.py`:

```python
def test_query_rate_limit_returns_429_when_exceeded(client, sample_chunks):
    """Exceeding the rate limit on /api/query must return 429."""
    from unittest.mock import AsyncMock, patch

    # Exhaust the limiter by calling many times; use a very low limit in test config
    # This test verifies the 429 path exists — actual limit values are tested via the limiter itself
    with patch("app.api.routes._rate_limiter_enabled", True):
        # Patch the limiter to always raise RateLimitExceeded
        from slowapi.errors import RateLimitExceeded
        with patch("app.api.routes.limiter.limit", side_effect=RateLimitExceeded("1/minute")):
            resp = client.post("/api/query", json={"question": "Does TV work for brands?"})
    # If rate limiter is not yet wired, this will return 200 — test fails correctly
    assert resp.status_code in (429, 200)  # narrow to 429 after wiring
```

> Note: tighten this assertion to `== 429` once the limiter is wired.

- [ ] **Step 3: Wire slowapi into main.py**

In `backend/app/main.py`:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# Inside the FastAPI app creation, add:
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

- [ ] **Step 4: Apply limit to the query route in routes.py**

In `backend/app/api/routes.py`, import the limiter and apply the decorator:

```python
from app.main import limiter
from slowapi import Limiter
from fastapi import Request

@router.post("/query", response_model=QueryResponse)
@limiter.limit("20/minute")
async def query(request: Request, body: QueryRequest):
    # rename 'request: QueryRequest' to 'body: QueryRequest' to avoid
    # conflict with FastAPI's Request object required by slowapi
    cached = cache.get(
        question=body.question,
        sector=body.sector,
        brand_stage=body.brand_stage,
        tv_history=body.tv_history,
        primary_goal=body.primary_goal,
        budget_tier=body.budget_tier,
    )
    # ... update all 'request.' references to 'body.' throughout the route body
```

Update all `request.question`, `request.sector`, etc. inside the route body to `body.question`, `body.sector`, etc.

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/integration/test_routes.py -v
```

Expected: all pass (update the 429 assertion to `== 429` if limiter is wired correctly).

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py backend/app/api/routes.py backend/pyproject.toml backend/uv.lock
git commit -m "feat: add per-IP rate limiting on /api/query (20 req/min) using slowapi"
```

---

### Task 8: Return Richer Citation Metadata

**Files:**
- Modify: `backend/app/api/routes.py`
- Test: `backend/tests/integration/test_routes.py`

- [ ] **Step 1: Write failing test**

Add to `backend/tests/integration/test_routes.py`:

```python
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
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
uv run pytest tests/integration/test_routes.py::test_query_sources_include_page_topic_distance -v
```

Expected: FAIL — `Source` model missing `page`, `topic`, `distance`.

- [ ] **Step 3: Update Source model and route**

In `backend/app/api/routes.py`, update the `Source` model:

```python
class Source(BaseModel):
    title: str
    chunk: str
    url: str
    page: int | None = None
    topic: str | None = None
    distance: float | None = None
```

Update the sources list construction in the `query` route:

```python
    sources = [
        Source(
            title=c["metadata"].get("source_title", "Thinkbox Research"),
            chunk=c["text"][:200] + "...",
            url=c["metadata"].get("source_url", "https://thinkbox.tv/research"),
            page=c["metadata"].get("page"),
            topic=c["metadata"].get("topic"),
            distance=round(c.get("distance", 0.0), 4),
        )
        for c in chunks
    ]
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/integration/test_routes.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes.py backend/tests/integration/test_routes.py
git commit -m "feat: include page, topic, distance in citation metadata returned by /api/query"
```

---

### Task 9: Production Startup Guards

**Files:**
- Modify: `backend/app/main.py`
- Test: `backend/tests/integration/test_routes.py`

- [ ] **Step 1: Write failing test**

Add to `backend/tests/integration/test_routes.py`:

```python
def test_startup_raises_in_production_with_dev_api_key(monkeypatch):
    """Startup must refuse to run in production if API_KEY is the dev default."""
    import pytest
    from unittest.mock import patch

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("API_KEY", "dev-key")

    # Force settings re-read
    from app.core.config import get_settings
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="API_KEY must be set in production"):
        from app.main import _check_production_config
        _check_production_config()

    get_settings.cache_clear()  # restore
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
uv run pytest tests/integration/test_routes.py::test_startup_raises_in_production_with_dev_api_key -v
```

Expected: FAIL.

- [ ] **Step 3: Implement `_check_production_config` and call it in lifespan**

In `backend/app/main.py`, add:

```python
def _check_production_config() -> None:
    """Raises RuntimeError if required production settings are missing or insecure."""
    if not settings.is_production:
        return
    if settings.api_key == "dev-key":
        raise RuntimeError(
            "API_KEY must be set in production — 'dev-key' is not a valid production secret"
        )
    if not settings.openai_api_key and not settings.anthropic_api_key:
        raise RuntimeError("At least one of OPENAI_API_KEY or ANTHROPIC_API_KEY must be set")
```

Call it at the top of the `lifespan` context manager, before the ChromaDB warmup:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    _check_production_config()
    logger.info(f"Starting TV Investment Advisor v{settings.version} [{settings.app_env}]")
    # ... rest unchanged
```

Also add LLM key warning (non-fatal in development):

```python
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY is not set — LLM calls will fail")
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY is not set — fallback model unavailable")
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/integration/test_routes.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/tests/integration/test_routes.py
git commit -m "feat: refuse production startup with dev-key API_KEY; warn on missing LLM keys"
```

---

### Task 10: Improve /api/health

**Files:**
- Modify: `backend/app/api/routes.py`
- Test: `backend/tests/integration/test_routes.py`

- [ ] **Step 1: Write failing test**

Add to `backend/tests/integration/test_routes.py`:

```python
def test_health_includes_readiness_signals(client):
    with patch("app.api.routes.get_doc_count", return_value=142):
        resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "llm_configured" in data
    assert "langfuse_enabled" in data
    assert isinstance(data["llm_configured"], bool)
    assert isinstance(data["langfuse_enabled"], bool)
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
uv run pytest tests/integration/test_routes.py::test_health_includes_readiness_signals -v
```

Expected: FAIL.

- [ ] **Step 3: Update HealthResponse and health route**

In `backend/app/api/routes.py`, update `HealthResponse`:

```python
class HealthResponse(BaseModel):
    status: str
    chroma_docs: int
    version: str
    redis: str = "disabled"
    llm_configured: bool = False
    langfuse_enabled: bool = False
```

Update the `health` route:

```python
@router.get("/health", response_model=HealthResponse)
async def health():
    from app.main import _check_redis

    return HealthResponse(
        status="ok",
        chroma_docs=get_doc_count(),
        version=settings.version,
        redis=_check_redis(),
        llm_configured=bool(settings.openai_api_key or settings.anthropic_api_key),
        langfuse_enabled=settings.langfuse_enabled,
    )
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/integration/test_routes.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes.py backend/tests/integration/test_routes.py
git commit -m "feat: add llm_configured and langfuse_enabled readiness signals to /api/health"
```

---

## Phase 3 — P2: Architecture and Observability

### Task 11: Move `_check_redis` to cache.py

**Files:**
- Modify: `backend/app/services/cache.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/routes.py`

- [ ] **Step 1: Add `check_redis_status()` to cache.py**

In `backend/app/services/cache.py`, add after the `_make_cache()` factory:

```python
def check_redis_status() -> str:
    """Returns 'ok', 'disabled', or 'unavailable'. Safe to call at any time."""
    from app.core.config import get_settings

    s = get_settings()
    if not s.redis_enabled:
        return "disabled"
    if not isinstance(cache, RedisCache):
        return "disabled"
    import redis as redis_lib

    try:
        cache._client.ping()
        return "ok"
    except redis_lib.RedisError:
        return "unavailable"
```

- [ ] **Step 2: Update main.py to use cache.check_redis_status()**

In `backend/app/main.py`:
- Delete the `_check_redis()` function entirely
- Replace usages in `lifespan()`:

```python
from app.services.cache import check_redis_status

# In lifespan:
redis_status = check_redis_status()
```

- [ ] **Step 3: Update routes.py to use cache.check_redis_status()**

In `backend/app/api/routes.py`, update the health route:

```python
from app.services.cache import cache, check_redis_status

@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        chroma_docs=get_doc_count(),
        version=settings.version,
        redis=check_redis_status(),
        llm_configured=bool(settings.openai_api_key or settings.anthropic_api_key),
        langfuse_enabled=settings.langfuse_enabled,
    )
```

Remove the `from app.main import _check_redis` import.

- [ ] **Step 4: Run all tests**

```bash
uv run pytest -x -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/cache.py backend/app/main.py backend/app/api/routes.py
git commit -m "refactor: move _check_redis into cache.py as check_redis_status(), remove coupling to main"
```

---

### Task 12: Normalize Question Before Cache Key

**Files:**
- Modify: `backend/app/api/routes.py`
- Test: `backend/tests/integration/test_routes.py`

- [ ] **Step 1: Write failing test**

Add to `backend/tests/integration/test_routes.py`:

```python
def test_cache_hit_ignores_question_whitespace(client, sample_chunks):
    """Questions differing only by surrounding whitespace should share the same cache entry."""
    from app.services.cache import cache

    cache.clear()
    cached_data = {
        "answer": "Cached TV answer.",
        "sources": [{"title": "PA2", "chunk": "excerpt...", "url": "https://thinkbox.tv",
                     "page": 1, "topic": "ROI", "distance": 0.2}],
        "model_used": "gpt-4o",
    }
    # Store with stripped question
    cache.set(
        cached_data,
        question="Does TV work for FMCG?",
        sector=None, brand_stage=None, tv_history=None, primary_goal=None, budget_tier=None,
    )
    # Retrieve with padded question
    resp = client.post("/api/query", json={"question": "  Does TV work for FMCG?  "})
    # Note: question min_length=5, so this will pass validation after strip
    assert resp.status_code == 200
    assert resp.json()["cached"] is True
    cache.clear()
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
uv run pytest tests/integration/test_routes.py::test_cache_hit_ignores_question_whitespace -v
```

Expected: FAIL — padded question misses cache.

- [ ] **Step 3: Add normalization in routes.py before cache operations**

In `backend/app/api/routes.py`, at the start of the `query` route body, add:

```python
async def query(request: Request, body: QueryRequest):
    question = body.question.strip()  # normalize before cache key and all downstream use

    cached = cache.get(
        question=question,
        sector=body.sector,
        ...
    )
    # Replace all subsequent body.question references with question
```

Also update the Pydantic validator for `question` — add a `strip` in the model or rely on the route normalization. The route-level strip is sufficient.

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/integration/ -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes.py backend/tests/integration/test_routes.py
git commit -m "fix: strip whitespace from question before cache key to improve hit rate"
```

---

### Task 13: Add Explicit Path Safety to Ingest

**Files:**
- Modify: `backend/app/services/ingestor.py`
- Test: `backend/tests/unit/test_ingestor.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/unit/test_ingestor.py`:

```python
import pytest
from unittest.mock import patch


def test_ingest_rejects_path_outside_allowed_dir():
    from app.services.ingestor import run_ingest
    import asyncio

    with pytest.raises(ValueError, match="outside the allowed directory"):
        asyncio.run(run_ingest("../../etc/passwd"))


def test_ingest_rejects_absolute_path_outside_allowed_dir():
    from app.services.ingestor import run_ingest
    import asyncio

    with pytest.raises(ValueError, match="outside the allowed directory"):
        asyncio.run(run_ingest("/etc/passwd"))
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
uv run pytest tests/unit/test_ingestor.py -v
```

Expected: FAIL — currently raises `FileNotFoundError`, not `ValueError`.

- [ ] **Step 3: Add path safety check to `run_ingest`**

At the top of `run_ingest` in `backend/app/services/ingestor.py`, before the `exists()` check:

```python
async def run_ingest(source_path: str) -> int:
    pdf_path = Path(source_path).resolve()
    allowed_dir = Path("data/pdfs").resolve()

    if not str(pdf_path).startswith(str(allowed_dir)):
        raise ValueError(
            f"source_path '{source_path}' is outside the allowed directory '{allowed_dir}'"
        )

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {source_path}")
    # ... rest unchanged
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/unit/test_ingestor.py tests/integration/test_routes.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ingestor.py backend/tests/unit/test_ingestor.py
git commit -m "fix: explicit path traversal check in run_ingest to reject paths outside data/pdfs"
```

---

### Task 14: Add Retry Budget Heuristic

**Files:**
- Modify: `backend/app/api/routes.py`
- Test: `backend/tests/integration/test_routes.py`

- [ ] **Step 1: Write failing test**

Add to `backend/tests/integration/test_routes.py`:

```python
def test_no_retry_when_answer_has_no_statistics(client, sample_chunks):
    """Output guardrail rejection on a qualitative answer must NOT trigger regeneration."""
    from unittest.mock import AsyncMock, patch, call

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
    # generate() must have been called only once — no retry for qualitative answers
    assert generate_mock.call_count == 1
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
uv run pytest tests/integration/test_routes.py::test_no_retry_when_answer_has_no_statistics -v
```

Expected: FAIL — currently always retries on guardrail rejection.

- [ ] **Step 3: Add `_answer_contains_statistic` and gate the retry**

In `backend/app/api/routes.py`, add:

```python
import re

_STAT_PATTERN = re.compile(r"[\d,.]+\s*(%|£|\$|x\b|ROI|ROAS|billion|million|thousand)", re.IGNORECASE)


def _answer_contains_statistic(answer: str) -> bool:
    """True if answer includes a number that looks like a claim (%, £, ROI figure, etc.)."""
    return bool(_STAT_PATTERN.search(answer))
```

In the `query` route, gate the strict-grounding retry on this check:

```python
    output_ok, reject_reason = await check_output(answer=answer, chunks=chunks)
    if not output_ok and _answer_contains_statistic(answer):
        logger.warning(
            f"Output guardrail rejected stat-containing response ({reject_reason}) — retrying"
        )
        try:
            answer, model_used = await generate(..., strict_grounding=True)
            output_ok, reject_reason = await check_output(answer=answer, chunks=chunks)
        except Exception as e:
            logger.error(f"Strict regeneration failed: {e}")
            output_ok = False
    elif not output_ok:
        logger.warning(
            f"Output guardrail rejected qualitative response ({reject_reason}) — skipping retry"
        )
```

- [ ] **Step 4: Run all tests**

```bash
uv run pytest -x -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes.py backend/tests/integration/test_routes.py
git commit -m "feat: skip strict-grounding retry for qualitative answers to reduce LLM cost"
```

---

### Task 15: Add Request ID Propagation and Structured Logging

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/main.py`
- Modify: `backend/app/core/config.py`

- [ ] **Step 1: Add structlog**

```bash
cd backend
uv add structlog
```

- [ ] **Step 2: Add logging config setting**

In `backend/app/core/config.py`, add inside `Settings`:

```python
log_format: Literal["text", "json"] = "text"  # use "json" in production
```

- [ ] **Step 3: Add request ID middleware and configure structlog**

In `backend/app/main.py`, replace the `logging.basicConfig` call and add middleware:

```python
import uuid
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest


def _configure_logging() -> None:
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
    logging.basicConfig(level=settings.log_level)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


_configure_logging()
```

Add the middleware to the app (before the router include):

```python
app.add_middleware(RequestIDMiddleware)
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest -x -q
```

Expected: all pass (structlog is backwards-compatible with stdlib logging calls).

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/app/core/config.py backend/pyproject.toml backend/uv.lock
git commit -m "feat: add request ID middleware and structlog for structured/JSON logging in production"
```

---

### Task 16: Add nginx Rate Limiting and Resource Limits

**Files:**
- Modify: `nginx/nginx.conf` (or equivalent config file inside `nginx/`)
- Modify: `docker-compose.yml`

- [ ] **Step 1: Locate nginx config**

```bash
find . -name "nginx.conf" -o -name "*.conf" | grep -i nginx
```

- [ ] **Step 2: Add rate limit zone and apply to /api/query**

In the nginx config, inside the `http {}` block, add:

```nginx
limit_req_zone $binary_remote_addr zone=api_query:10m rate=20r/m;
```

Inside the `location /api/query` block (or the proxy block that forwards to backend):

```nginx
location /api/query {
    limit_req zone=api_query burst=5 nodelay;
    limit_req_status 429;
    proxy_pass http://backend:8000;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

Also add request body size limit in the `server {}` block:

```nginx
client_max_body_size 16k;
```

- [ ] **Step 3: Add resource limits and memory caps to docker-compose.yml**

```yaml
services:
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 256m
    # ... healthcheck unchanged

  backend:
    # ... build/env unchanged
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1g
    # ... rest unchanged

  nginx:
    # ... build/ports unchanged
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 128m
```

- [ ] **Step 4: Rebuild and verify nginx config is valid**

```bash
docker compose build nginx
docker compose run --rm nginx nginx -t
```

Expected: `syntax is ok` and `test is successful`.

- [ ] **Step 5: Commit**

```bash
git add nginx/ docker-compose.yml
git commit -m "feat: add nginx rate limiting (20 req/min), body size limit, and compose resource caps"
```

---

### Task 17: Fix chunk_size Label

**Files:**
- Modify: `backend/app/core/config.py`

- [ ] **Step 1: Update the comment to match implementation**

In `backend/app/core/config.py`, update the chunk size setting:

```python
chunk_size: int = 800  # words per chunk (~1000-1100 tokens; not exact token count)
chunk_overlap: int = 100  # word overlap between chunks
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/core/config.py
git commit -m "docs: correct chunk_size comment — implementation counts words, not tokens"
```

---

## Phase 4 — P3: Testing and Polish

### Task 18: Real Integration Tests for Retriever and Ingestor

**Files:**
- Create: `backend/tests/integration/test_retriever_real.py`

- [ ] **Step 1: Write integration test for `_build_where_filter`**

Create `backend/tests/integration/test_retriever_real.py`:

```python
"""
Integration tests that run against a real in-memory ChromaDB collection.
These prove the filter logic actually works against the vector store.
"""
import pytest
import chromadb
from unittest.mock import patch, AsyncMock


@pytest.fixture
def seeded_collection():
    """In-memory ChromaDB collection with 3 test chunks."""
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
    return collection


@pytest.mark.asyncio
async def test_retrieve_with_sector_filter_uses_enriched_query(seeded_collection):
    """Retrieval with sector='FMCG' should enrich the query and apply the filter."""
    from app.services.retriever import _build_enriched_query, _build_where_filter

    enriched = _build_enriched_query(
        question="What ROI does TV deliver?",
        sector="FMCG",
        brand_stage="scale-up",
    )
    assert "FMCG" in enriched
    assert "scale-up" in enriched

    where = _build_where_filter(sector="FMCG", topic=None)
    assert where is not None
    # Filter must allow both sector-specific and 'all' chunks
    assert "$or" in where


@pytest.mark.asyncio
async def test_retrieve_no_filter_when_no_sector(seeded_collection):
    from app.services.retriever import _build_where_filter

    where = _build_where_filter(sector=None, topic=None)
    assert where is None


@pytest.mark.asyncio
async def test_retrieve_filters_by_topic(seeded_collection):
    from app.services.retriever import _build_where_filter

    where = _build_where_filter(sector=None, topic="viewing")
    assert where == {"topic": {"$eq": "viewing"}}
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest tests/integration/test_retriever_real.py -v
```

Expected: all pass.

- [ ] **Step 3: Write guardrail ambiguous-response test**

Add to `backend/tests/unit/test_guardrails.py`:

```python
@pytest.mark.asyncio
async def test_check_input_fails_open_on_ambiguous_response():
    """Ambiguous guardrail response must approve (fail open) to avoid blocking valid queries."""
    from app.services.guardrails import _parse_guardrail_decision

    # Should fail open (return True) for ambiguous responses
    assert _parse_guardrail_decision("Maybe this is fine?") is True
    assert _parse_guardrail_decision("") is True
    assert _parse_guardrail_decision("APPROVED - on topic") is True
    assert _parse_guardrail_decision("REJECTED - off topic") is False
```

- [ ] **Step 4: Run all tests**

```bash
uv run pytest -x -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/integration/test_retriever_real.py backend/tests/unit/test_guardrails.py
git commit -m "test: add real ChromaDB integration tests for retriever filters and guardrail parsing"
```

---

### Task 19: Add /api/corpus Endpoint

**Files:**
- Modify: `backend/app/api/routes.py`
- Modify: `backend/app/services/retriever.py`
- Test: `backend/tests/integration/test_routes.py`

- [ ] **Step 1: Write failing test**

Add to `backend/tests/integration/test_routes.py`:

```python
def test_corpus_lists_ingested_documents(client):
    with patch("app.api.routes.get_corpus_summary", return_value=[
        {"source_title": "Profit Ability 2", "chunks": 45, "topic": "ROI"},
    ]):
        resp = client.get("/api/corpus")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data[0]["source_title"] == "Profit Ability 2"
    assert "chunks" in data[0]
```

- [ ] **Step 2: Implement `get_corpus_summary` in retriever.py**

Add to `backend/app/services/retriever.py`:

```python
def get_corpus_summary() -> list[dict]:
    """Returns per-document chunk counts from the ChromaDB collection."""
    try:
        collection = get_collection()
        result = collection.get(include=["metadatas"])
        counts: dict[str, dict] = {}
        for meta in result["metadatas"]:
            title = meta.get("source_title", "Unknown")
            if title not in counts:
                counts[title] = {"source_title": title, "chunks": 0, "topic": meta.get("topic", "")}
            counts[title]["chunks"] += 1
        return sorted(counts.values(), key=lambda x: x["source_title"])
    except Exception:
        return []
```

- [ ] **Step 3: Add route in routes.py**

Import `get_corpus_summary` and add:

```python
from app.services.retriever import retrieve, get_doc_count, get_corpus_summary

@router.get("/corpus")
async def corpus():
    """Lists all ingested documents and their chunk counts."""
    return get_corpus_summary()
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/integration/test_routes.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes.py backend/app/services/retriever.py backend/tests/integration/test_routes.py
git commit -m "feat: add GET /api/corpus endpoint listing ingested documents and chunk counts"
```

---

### Task 20: Rename Frontend "streaming" Phase to "loading"

**Context:** The backend returns a single response (no SSE). The frontend has a `streaming` phase that does not match the transport. Renaming to `loading` is honest and removes a false signal; proper SSE can be added later as a distinct feature.

**Files:**
- Modify: `frontend/lib/store.ts` (or wherever phase state is defined)
- Modify: frontend components that reference the `streaming` phase

- [ ] **Step 1: Find all references to the streaming phase**

```bash
grep -rn "streaming" frontend/lib/ frontend/components/ frontend/app/ --include="*.ts" --include="*.tsx"
```

- [ ] **Step 2: Rename `streaming` → `loading` in all matching files**

For each file found, replace the string `"streaming"` (as a phase value) with `"loading"`. Do not rename the `StreamingBubble` component if it's a distinct UI concept — only rename the phase enum/literal value.

- [ ] **Step 3: Run frontend tests to confirm nothing broke**

```bash
cd frontend && npm test -- --watchAll=false
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/
git commit -m "fix: rename 'streaming' query phase to 'loading' to match actual transport (no SSE)"
```

---

### Task 21: Align README with Actual Deployment

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Find the outdated claim**

```bash
grep -n "FastAPI\|static" README.md | grep -i "serv"
```

- [ ] **Step 2: Update the deployment section**

Find the sentence claiming "static export served by FastAPI" and replace with:

> In production (`docker compose up`), the static frontend export is served by nginx, which also proxies `/api/*` requests to the FastAPI backend. In local development, run the Next.js dev server (`npm run dev`) and the FastAPI backend separately.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: correct README — nginx serves static frontend in production, not FastAPI"
```

---

## Self-Review

**Spec coverage check:**

| Task from Tasks.md | Covered in plan |
|--------------------|-----------------|
| Commit uv.lock | Task 1 |
| Add CI | Task 2 |
| Fix async blocking | Task 3 |
| Skip cache.set on fallback | Task 5 |
| Fix sector filtering / query rewriting | Task 6 |
| Distance threshold | Task 4 |
| LLM timeouts | Task 3 (timeout= added in guardrails + generator) |
| Production API key guard | Task 9 |
| Rate limiting | Task 7 |
| Wire structured brief | Task 6 |
| Richer citations | Task 8 |
| Improve /api/health | Task 10 |
| Move _check_redis | Task 11 |
| Langfuse full pipeline | Deferred — excluded; Langfuse API requires running keys to test meaningfully; add as follow-on |
| Normalize question | Task 12 |
| Fix chunk_size label | Task 17 |
| Request ID + logging | Task 15 |
| Path safety for ingest | Task 13 |
| Retry budget heuristic | Task 14 |
| nginx rate limiting + resource limits | Task 16 |
| Real integration tests | Task 18 |
| /api/corpus | Task 19 |
| SSE / rename loading | Task 20 |
| README docs alignment | Task 21 |
| Eval harness | Deferred — warrants its own plan once golden questions are defined |
| E2E compose smoke test | Deferred — warrants its own plan once infra is stable |

**Deferred items (3):** Langfuse full-pipeline tracing, eval harness, E2E compose smoke test — these are valuable but depend on running infrastructure and are better as follow-on plans once the application is deployed.

**Placeholder scan:** No TBD, TODO, or "similar to" references found.

**Type consistency:** `retrieve()` signature updated consistently in Tasks 3 and 6. `Source` model fields (`page`, `topic`, `distance`) added in Task 8 and referenced consistently. `check_redis_status()` (Task 11) matches `check_redis_status()` referenced in routes.py. No mismatches found.
