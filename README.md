# Cue — TV Investment Advisor

A RAG-powered web application that helps brands and agencies understand when and how TV advertising could work for them, grounded in Thinkbox's published research. Think of it as a senior media planner available 24/7.

Built as a portfolio project targeting AI backend engineer roles — demonstrating RAG pipelines, LiteLLM gateway, ChromaDB, LangFuse observability, guardrails, Redis caching, and a React frontend.

---

## Architecture

```
Browser (Next.js)
    │
    │  POST /api/query
    ▼
FastAPI
    ├── Cache lookup (Redis / in-memory dict)
    ├── Input guardrail  (GPT-4o-mini — is this on-topic?)
    ├── ChromaDB retrieval (top-5 chunks, metadata-filtered)
    ├── LiteLLM → GPT-4o (primary) / Claude 3.5 Sonnet (fallback)
    ├── Output guardrail (GPT-4o-mini — are citations grounded?)
    └── Cache write (TTL 7 days)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS v4, Zustand v5 |
| Backend | FastAPI, Python 3.13, Pydantic v2 |
| LLM gateway | LiteLLM (OpenAI primary, Anthropic fallback) |
| Vector store | ChromaDB (local persistent) |
| Observability | LangFuse (traces, costs, guardrail outcomes) |
| Cache | Redis (production) / in-memory dict (development) |
| Containerisation | Docker Compose |

---

## Quick Start

### Local development

**Backend:**
```bash
cd backend
cp .env.example .env   # fill in API keys
uv run uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev            # http://localhost:3000
```

### Docker (full stack)

```bash
cp backend/.env.example backend/.env   # fill in API keys
docker-compose up --build
```

The backend runs at `http://localhost:8000`. The frontend dev server proxies API calls to it.

### Ingest the corpus

Download the [Thinkbox research PDFs](https://www.thinkbox.tv/research) into `data/pdfs/`, then:

```bash
cd backend
uv run scripts/ingest.py
```

---

## Environment Variables

Create `backend/.env` from `backend/.env.example`:

```bash
# LLM providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# LangFuse observability (free at cloud.langfuse.com)
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# API key for POST /api/ingest
API_KEY=change-me-in-production

# CORS (comma-separated)
CORS_ORIGINS=http://localhost:3000

# Redis — leave empty to use in-memory dict cache for local dev
# REDIS_URL=redis://localhost:6379/0
```

---

## API Reference

### `POST /api/query`

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

All fields except `question` are optional. Valid enum values:

| Field | Values |
|-------|--------|
| `sector` | `FMCG` `Retail` `Finance` `Auto` `Telco` `Travel` `DTC` `Other` |
| `brand_stage` | `start-up` `scale-up` `established` `large` |
| `tv_history` | `never` `tried` `regular` |
| `primary_goal` | `sales` `brand` `both` `unsure` |
| `budget_tier` | `under-100k` `100k-500k` `500k-2m` `2m-plus` `undecided` |

Response:
```json
{
  "answer": "Based on Thinkbox research...",
  "sources": [
    { "title": "Profit Ability 2", "chunk": "TV delivered...", "url": "https://thinkbox.tv/..." }
  ],
  "cached": false,
  "model_used": "gpt-4o"
}
```

### `GET /api/health`

```json
{ "status": "ok", "chroma_docs": 142, "version": "0.1.0", "redis": "ok" }
```

`redis`: `"ok"` | `"disabled"` | `"unavailable"`

### `POST /api/ingest`

Requires `X-API-Key` header. Ingests a single document.

```json
{ "source_path": "data/pdfs/profit-ability-2.pdf" }
```

---

## Project Structure

```
tv-invest-advisor/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app, lifespan startup, CORS
│   │   ├── api/routes.py         # /api/query, /api/ingest, /api/health
│   │   ├── core/config.py        # Settings via pydantic-settings
│   │   └── services/
│   │       ├── embedder.py       # OpenAI text-embedding-3-small
│   │       ├── retriever.py      # ChromaDB retrieval + metadata filter
│   │       ├── generator.py      # LiteLLM → GPT-4o / Claude fallback
│   │       ├── cache.py          # Redis + in-memory dict, same interface
│   │       ├── guardrails.py     # Input + output LLM checks
│   │       └── ingestor.py       # PDF → chunks → embeddings → ChromaDB
│   ├── scripts/
│   │   ├── ingest.py             # Offline corpus ingestion
│   │   └── test_retrieval.py     # Retrieval quality smoke test
│   ├── tests/                    # pytest unit + integration tests
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── app/                      # Next.js App Router
│   ├── components/               # atoms / composer / thread / rail / layout
│   ├── overlays/                 # HistoryDrawer, ExportModal
│   ├── lib/                      # types.ts, api.ts, store.ts (Zustand)
│   └── __tests__/                # Jest + React Testing Library (62 tests)
├── data/pdfs/                    # Thinkbox PDFs (gitignored — add manually)
├── docker-compose.yml
└── README.md
```

---

## Key Design Decisions

**LiteLLM gateway** — wraps OpenAI and Anthropic behind a single interface. Model routing, fallback chains, and cost tracking work without touching call sites. Kept even where it feels like overkill because it's a named requirement for the target role.

**ChromaDB local** — zero cost, no external dependency, runs in Docker. Sufficient for an 8-10 document corpus. Swap path: same `retriever.py` interface → Qdrant or pgvector.

**Two-stage guardrails** — GPT-4o-mini checks input (on-topic?) and output (stats grounded in sources?). Hallucinated statistics in a media planning tool cause real commercial harm, so both stages are non-negotiable.

**Redis / dict cache** — `cache.py` exposes a `get`/`set`/`clear` interface. `REDIS_URL` set → `RedisCache`; unset → `ResponseCache` (dict). Redis errors degrade gracefully to cache-miss, never 500. `fakeredis` in tests — no real Redis needed in CI.

**Static export** — `frontend/` builds to static files (`output: 'export'`), served by FastAPI in production. One deployment unit, no Node.js runtime needed in production.

---

## Development

```bash
# Backend — lint and test
cd backend
uv run black .
uv run flake8 .
uv run pytest

# Frontend — lint and test
cd frontend
npm run lint
npm test
```
