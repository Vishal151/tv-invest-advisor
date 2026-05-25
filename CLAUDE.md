# TV Investment Advisor — Project Brief for AI Agents
 
## How to use this file
If you are an AI agent starting a new session, read this file completely before
touching any code. When done, confirm you have read it and state which section
we are working on. Do not begin work until the human confirms.
 
## Project root
`~/code/Vishal151/CODE-training/tv-invest-advisor/`
 
## What this is
A RAG-powered web application that helps brands and agencies understand when and
how TV advertising investment could work for them, grounded in Thinkbox's
published research. Think of it as a senior media planner available 24/7.
 
## Who it's for
- Brand marketers deciding whether to invest in TV
- Media agencies advising clients on TV strategy
- Potential future commission: Thinkbox themselves may adopt this to showcase
  their research corpus
## Why it exists (portfolio context)
Built as a portfolio project targeting AI backend engineer roles (specifically
ITV's AI Backend Engineer role). Demonstrates: RAG pipelines, FastAPI, LiteLLM
gateway, ChromaDB, LangFuse observability, guardrails, response caching, React
frontend, Docker Compose.
 
---
 
## Current build status
 
| Component | Status | Notes |
|-----------|--------|-------|
| Project structure | ✅ Done | Folders, .gitignore, CLAUDE.md |
| backend/app/core/config.py | ✅ Done | Settings, env vars, redis_url/redis_enabled |
| backend/app/main.py | ✅ Done | FastAPI app, lifespan startup warmup, _check_redis() |
| backend/app/api/routes.py | ✅ Done | /query, /ingest, /health; Pydantic validators; 503 on LLM failure |
| backend/app/services/embedder.py | ✅ Done | OpenAI embedding wrapper |
| backend/app/services/retriever.py | ✅ Done | ChromaDB retrieval + metadata filter |
| backend/app/services/generator.py | ✅ Done | LiteLLM call, GPT-4o primary / Claude fallback |
| backend/app/services/cache.py | ✅ Done | ResponseCache (dict) + RedisCache; factory selects based on REDIS_URL |
| backend/app/services/guardrails.py | ✅ Done | Input/output LLM checks (GPT-4o-mini) |
| backend/scripts/ingest.py | ✅ Done | PDF ingestion pipeline |
| backend/scripts/test_retrieval.py | ✅ Done | Retrieval quality smoke test |
| backend/.env.example | ✅ Done | Includes REDIS_URL (commented out for local dev) |
| backend/Dockerfile | ✅ Done | uv official image, non-root user, no dev deps in prod |
| backend/.flake8 | ✅ Done | black-compatible config (E203, W503, E501 ignored) |
| backend/pyproject.toml | ✅ Done | black + flake8 + fakeredis in dev deps |
| frontend (Next.js) | ⬜ Todo | Initialised, not built yet |
| docker-compose.yml | ✅ Done | Redis service + healthcheck; backend depends_on redis |
| Data corpus ingested | ✅ Done | Thinkbox PDFs ingested into ChromaDB |
 
Update this table as work progresses.
 
---
 
## Project structure
 
```
tv-invest-advisor/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app, mounts routes, CORS
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py         # /api/query, /api/ingest, /api/health
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── config.py         # Settings via pydantic-settings
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── embedder.py       # OpenAI text-embedding-3-small wrapper
│   │       ├── retriever.py      # ChromaDB retrieval + metadata filter
│   │       ├── generator.py      # LiteLLM → GPT-4o, Anthropic fallback
│   │       ├── cache.py          # Hash-based response cache
│   │       └── guardrails.py     # Input + output LLM reviewer
│   ├── scripts/
│   │   ├── ingest.py             # Offline: PDF → chunks → embeddings → ChromaDB
│   │   └── test_retrieval.py     # Smoke test retrieval quality
│   ├── chroma_db/                # ChromaDB persistence (gitignored)
│   ├── pyproject.toml
│   ├── .env.example
│   └── .env                      # Gitignored, never commit
├── frontend/                     # Next.js 15, App Router, TypeScript, Tailwind
│   ├── app/
│   ├── components/
│   └── (standard Next.js structure)
├── data/
│   └── pdfs/                     # Thinkbox PDFs (gitignored, add manually)
├── docker-compose.yml
├── .gitignore
└── CLAUDE.md                     # This file
```
 
---
 
## Backend architecture
 
### Query flow (live path)
```
User inputs (structured + optional freeform)
  → cache lookup (hash of all inputs)
  → [cache hit] return stored response immediately
  → [cache miss] input guardrail (GPT-4o-mini: is this on-topic?)
  → [rejected] return safe refusal message
  → [approved] build retrieval query from structured inputs + question
  → ChromaDB retrieval (top-5 chunks, metadata-filtered by sector/topic)
  → LiteLLM → GPT-4o (primary) / Claude (fallback)
  → output guardrail (GPT-4o-mini: citations grounded? stats hallucinated?)
  → [failed] retry once with tighter prompt → fallback to safe template
  → cache write (TTL 7 days)
  → return answer + source citations + model_used
```
 
### Ingestion flow (offline, run manually)
```
Thinkbox PDFs → pypdf extract text → chunk (800 tokens, 100 overlap)
  → OpenAI text-embedding-3-small (1536-dim)
  → ChromaDB upsert with metadata
```
 
### Key services
- **FastAPI** — REST API, async, Pydantic v2 models
- **LiteLLM** — model gateway: OpenAI primary, Anthropic fallback, cost tracking
- **ChromaDB** — persistent local vector store (chroma_db/ directory)
- **LangFuse** — traces every query: latency, tokens, cost, guardrail outcomes
- **Cache** — Redis in production (REDIS_URL set), dict in development; both implement the same interface; TTL 7 days; graceful degradation on Redis errors
---
 
## API specification
 
### POST /api/query
**Request:**
```json
{
  "question": "When does TV work best for FMCG brands?",
  "sector": "FMCG",
  "brand_stage": "scale-up",
  "tv_history": "never",
  "primary_goal": "brand",
  "budget_tier": "100k-500k"
}
```
All fields except `question` are optional enums — see config.py for valid values.
 
**Response:**
```json
{
  "answer": "Based on Thinkbox research...",
  "sources": [
    {
      "title": "Profit Ability 2",
      "chunk": "TV delivered the highest ROI...",
      "url": "https://thinkbox.tv/research/profit-ability-2"
    }
  ],
  "cached": false,
  "model_used": "gpt-4o"
}
```
 
### GET /api/health
```json
{ "status": "ok", "chroma_docs": 142, "version": "0.1.0", "redis": "ok" }
```
`redis` field: `"ok"` | `"disabled"` | `"unavailable"`
 
### POST /api/ingest
Protected by `X-API-Key` header. Triggers ingestion of a single document.
```json
{ "source_path": "data/pdfs/profit-ability-2.pdf" }
```
 
---
 
## ChromaDB metadata schema
 
Collection name: `thinkbox_docs`
 
| Field | Type | Example | Notes |
|-------|------|---------|-------|
| source_title | str | "Profit Ability 2" | Shown in citation card |
| source_url | str | "https://thinkbox.tv/..." | Linked in UI |
| topic | str | "ROI" | ROI, small_business, effectiveness, planning, creative, viewing |
| sector | str | "FMCG" | Sector-specific or "all" |
| page | int | 12 | Source page number |
| chunk_index | int | 23 | Position within document |
 
Topic and sector fields enable metadata filtering at retrieval time.
 
---
 
## Corpus (Thinkbox research documents)
 
| Document | Year | Topic tag | Key data points |
|----------|------|-----------|-----------------|
| Profit Ability 2 | 2024 | ROI | £5.61 ROI/£1, 141 brands, 14 categories |
| Profit Ability 1 | 2018 | ROI | 2,000+ campaigns, short vs long-term payback |
| As Seen on TV / Supercharge | 2019 | small_business | 300+ campaigns, 80% of sales, 4-month payback |
| Peter Field white paper | 2024 | effectiveness | 10 years IPA data, attention/emotion/trust |
| Payback 3 & 4 | 2014 | ROI | 4,500+ campaigns, seasonal windows by sector |
| TV Viewing Report | 2024 | viewing | 2h36m daily, BVOD 29% of 16-34 viewing |
| Signalling Success | 2020 | effectiveness | Brand fame, trust, mental availability |
| Demand Generator | 2019 | planning | WPP econometric meta-analysis |
 
PDFs live in `data/pdfs/` — download from thinkbox.tv, add manually.
 
---
 
## Environment variables
 
```bash
# LLM providers (both needed for fallback)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
 
# LangFuse — free at cloud.langfuse.com
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
 
# API security
API_KEY=your-random-secret    # protects POST /api/ingest
 
# CORS
CORS_ORIGINS=http://localhost:3000
 
# Redis cache (leave empty to use in-memory dict cache for local dev)
# REDIS_URL=redis://localhost:6379/0
 
# App
APP_ENV=development           # development | production
LOG_LEVEL=INFO
```
 
---
 
## Key technical decisions
 
### Decision 1: ChromaDB over managed vector DB (May 2026)
- **Choice**: ChromaDB, local persistent
- **Why**: Zero cost, no external dependency, runs in Docker, sufficient for
  8-10 doc corpus at this stage
- **Trade-off**: Not horizontally scalable
- **Production path**: Swap for Qdrant or pgvector via same retriever interface
- **Do not**: Add a managed vector DB without being asked
### Decision 2: LiteLLM gateway over direct OpenAI SDK (May 2026)
- **Choice**: LiteLLM wrapping OpenAI + Anthropic
- **Why**: Explicitly named in ITV job description. Adds model routing,
  fallback chains, cost tracking with zero code change to swap providers
- **Trade-off**: Slight overhead, one extra dependency
- **Do not refactor**: Keep LiteLLM even if it feels like overkill
### Decision 3: Redis in production, dict cache in development (May 2026)
- **Choice**: `cache.py` exposes a common interface (`get`, `set`, `clear`). On startup, `_make_cache()` checks `REDIS_URL`: set → `RedisCache` (wraps `redis-py`); unset → `ResponseCache` (dict). Docker Compose sets `REDIS_URL=redis://redis:6379/0`.
- **Why**: Production needs a durable shared cache. Development needs zero infrastructure. Redis errors degrade gracefully to cache-miss (never 500).
- **Testing**: `fakeredis.FakeRedis` used in tests — no real Redis needed in CI.
- **Do not**: Remove the `ResponseCache` fallback or let Redis errors propagate to callers.
### Decision 4: Two-stage guardrails — input + output (May 2026)
- **Choice**: GPT-4o-mini for both checks (cheap, fast)
- **Why**: Input keeps tool on-topic. Output verifies every stat traces to
  a Thinkbox source. Hallucinated stats in a media planning tool cause
  real commercial harm
- **Do not**: Remove either guardrail stage
### Decision 5: Structured inputs shape retrieval (May 2026)
- **Choice**: sector, brand_stage, tv_history, primary_goal, budget_tier
  passed as ChromaDB metadata filters alongside the freeform question
- **Why**: Without structured context, retrieval is generic and less useful
---
 
## Development setup
 
```bash
# Backend
cd backend
cp .env.example .env          # fill in your keys
uv run uvicorn app.main:app --reload --port 8000
 
# Lint and format
uv run black .
uv run flake8 .
 
# Tests
uv run pytest
 
# Ingest corpus (run once, or when adding new docs)
uv run scripts/ingest.py
 
# Test retrieval quality
uv run scripts/test_retrieval.py
 
# Frontend
cd frontend
npm run dev                   # http://localhost:3000
```
 
### Frontend config (Next.js)
- `output: 'export'` — static export for production serving by FastAPI
- `trailingSlash: true` — consistent routing
- `images: { unoptimized: true }` — required for static export
- Development: API calls to `http://localhost:8000`
- Production: relative URLs (frontend served from same domain as API)
---
 
## Docker
 
```bash
docker-compose up --build         # full stack
docker-compose up backend         # backend only
docker-compose up --build backend # rebuild after code changes
docker-compose logs -f backend    # follow logs
docker-compose down               # stop everything
```
 
---
 
## Known issues and workarounds
 
Populate as encountered using this format:
 
```
### Issue: <title> (<date>)
**Symptom**: What went wrong
**Root cause**: Why it happened
**Fix**: What was done to resolve it
```
### Issue: ChromaDB requires SQLite >= 3.35.0 (May 2026)
**Symptom**: RuntimeError on import — system SQLite too old
**Root cause**: Ubuntu ships older SQLite, ChromaDB needs 3.35.0+
**Fix**: uv add pysqlite3-binary, monkey-patch at top of retriever.py
 
---
 
## Future enhancements (not in scope for v1)
 
- Scheduled corpus refresh — auto-ingest new Thinkbox research on publish
- LangFuse evaluation dataset — score retrieval quality over time
- Redis cache — already in docker-compose; consider Redis Cluster for HA
- Streaming responses — SSE for long answers
- User auth — Clerk or similar if multi-tenant
- Terraform deployment to GCP Cloud Run or AWS App Runner
---
 
## Do not
 
- Hallucinate statistics not present in the Thinkbox corpus
- Invent source URLs or document titles
- Remove the LiteLLM gateway and call OpenAI SDK directly
- Remove either guardrail stage (input or output)
- Add Celery or other infrastructure without being explicitly asked
- Use `import *` anywhere in the codebase
- Commit `.env`, anything in `chroma_db/`, or anything in `data/pdfs/`