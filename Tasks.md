# Production Tasks — TV Investment Advisor

---

## Outstanding — post-audit (2026-06-12)

Current source of truth: `docs/audit-2026-06-12.md` ("Outstanding work after remediation").
All High and most Medium audit findings are fixed. Remaining:

- [ ] Full-pipeline LangFuse tracing (root trace per request; spans for cache, guardrails, retrieval, generation) — pair with extracting `routes.query()` into an `answer_query()` service (M3)
- [ ] Sector filter decision: tag sector-specific chunks at ingest or remove the inert filter; A/B via eval (M5)
- [ ] Tune or remove the 0.75 retrieval distance threshold against the eval benchmark (M4 remainder)
- [ ] Pin Docker base images to patch + SHA256 digest (M11 remainder)
- [ ] Retrieval roadmap: BM25 hybrid + rerank, comparison-query decomposition, smaller chunks — A/B via eval
- [ ] Low findings L1–L14 (see audit doc); highest value: Literal types for request enums, thread titles + persistence, E2E job in CI

The sections below are the original (May 2026) task list, kept for history — most items are done.

---

## P0 — Blocking: must fix before "production-ready"

- [ ] Commit `backend/uv.lock` — remove from `.gitignore`; Dockerfile copies it so clean-clone Docker build fails
- [ ] Add CI workflow (`.github/workflows/ci.yml`): backend `uv run pytest`, `uv run black --check`, `uv run flake8`; frontend `npm test`, `npm run lint`; optional `docker compose build`
- [ ] Fix async event-loop blocking — routes are `async def` but all downstream calls are synchronous blocking I/O (LiteLLM `completion()`, OpenAI `embed()`, ChromaDB). Switch to `litellm.acompletion()` + `openai.AsyncOpenAI`, or wrap blocking calls with `asyncio.run_in_executor`

---

## P1 — High impact, low effort

- [ ] Skip `cache.set()` when returning safe fallback — currently the generic fallback message is cached for 7 days, so the same question never gets a real retry
- [ ] Fix sector filtering — every document in `DOCUMENT_REGISTRY` is tagged `sector: "all"`, so the `$or` filter always matches everything; either add sector-tagged docs or rewrite the query based on sector context instead of filtering
- [ ] Add distance threshold in `retrieve()` — filter out chunks where `distance > threshold` (e.g. 0.7) so poor-quality retrievals don't inflate prompts and increase hallucination risk
- [ ] Add timeouts to all LLM calls — `completion(model=..., timeout=30)` in both `generator.py` and `guardrails.py`; also bound the OpenAI embedding call
- [ ] Guard against dev API key in production — in `lifespan()`, raise `RuntimeError` if `app_env == "production"` and `api_key == "dev-key"`
- [ ] Add rate limiting on `/api/query` — use Redis (already in production stack) as limiter backend; per-IP limit (e.g. 20/min); return 429 with retry-after header
- [ ] Wire structured brief into retrieval — `brand_stage`, `tv_history`, `primary_goal`, `budget_tier` currently only affect cache key and prompt context; use them to rewrite or weight the retrieval query
- [ ] Return richer citation metadata — include `page`, `topic`, and `distance` in the `Source` response model; frontend currently shows placeholder zeros
- [ ] Improve `/api/health` — add `llm_configured` (bool) and `langfuse_enabled` (bool) readiness signals; already returns `chroma_docs` and `redis`

---

## P2 — Architecture and observability

- [ ] Move `_check_redis` out of `app/main.py` — it belongs in `app/services/cache.py`; health route importing a private function from the app entry point is a coupling smell and circular-import risk
- [ ] Extend Langfuse tracing to full pipeline — create one trace root per `/api/query` request in routes.py with spans for: cache lookup, input guardrail, retrieval (k + filters + distances), generation, output guardrail + retry path; currently only `generate()` is traced
- [ ] Normalize question before cache key — `str.strip()` (and optionally `.lower()`) before hashing; `"TV ROI? "` and `"TV ROI?"` currently miss each other
- [ ] Fix `chunk_size` label — config says `# tokens per chunk` but `ingestor.py` splits by words; rename or align the implementation (word count ≠ token count)
- [ ] Add request ID propagation — accept `X-Request-ID` header (or generate one); include in all log lines and error responses for correlation
- [ ] Switch to structured JSON logging in production — use `structlog` or `python-json-logger` behind a config flag (`app_env == "production"`)
- [ ] Add path safety check to ingest — explicitly validate `source_path` resolves inside an allowed directory (e.g. `data/pdfs/`) before calling `run_ingest`; current implicit protection via `DOCUMENT_REGISTRY` is undocumented
- [ ] Add retry budget heuristic — only trigger strict-grounding retry if the first answer contains a number/statistic (simple regex); skip regeneration for purely qualitative answers to reduce unnecessary LLM cost
- [ ] Centralise ingestion logic — `scripts/ingest.py`, `app/services/ingestor.py`, `scripts/ingest_scraped.py` share chunking and metadata concerns; move shared logic to avoid drift
- [ ] Add nginx rate limiting — add `limit_req_zone` per-IP in nginx config as a first-line defence before requests hit Python
- [ ] Add resource limits to docker-compose — set `mem_limit` and `restart: unless-stopped` policies for backend and Redis

---

## P3 — Polish and portfolio "wow factor"

- [ ] Add real integration tests — test `retrieve()` against a seeded in-memory ChromaDB collection (proves `_build_where_filter` actually works); test guardrail prompt parsing for ambiguous model responses; test `run_ingest` end-to-end against a small test PDF
- [ ] Add E2E smoke test — curl-based or Playwright test that validates nginx → backend wiring from a running compose stack
- [ ] Add security edge-case tests — ingest path traversal attempt, rate-limit 429 behaviour once implemented
- [ ] SSE streaming — backend `StreamingResponse` + frontend incremental rendering; frontend currently has a `streaming` phase that the backend doesn't support; either implement or rename to `loading`
- [ ] Add `/api/corpus` endpoint — list ingested documents with chunk counts; useful for demos and debugging
- [ ] Add eval harness — a small golden-question set (TV questions → expected Thinkbox sources); run as a manual or CI script; wire results into Langfuse as evaluation scores
- [ ] Docs: align README with actual deployment — README says "static export served by FastAPI" but production uses nginx; update to match reality
- [ ] Add `llm_configured` check at startup — warn (not fail) if `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` is empty, so misconfigured deployments are obvious in logs immediately

---

## Deferred (out of scope for v1)

- Multi-tenancy / RBAC — only introduce once there is a real user/tenant model
- Managed vector DB (Qdrant, pgvector) — swap via existing retriever interface only when corpus outgrows ChromaDB
- Celery or background task workers — not needed at current scale
- Terraform / cloud deployment — infrastructure-as-code once hosting target is decided
