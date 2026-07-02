# Cue — TV Investment Advisor

[![CI](https://github.com/Vishal151/tv-invest-advisor/actions/workflows/ci.yml/badge.svg)](https://github.com/Vishal151/tv-invest-advisor/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

A RAG-powered web application that helps brands and agencies understand when and how TV advertising could work for them, grounded in Thinkbox's published research. Think of it as a senior media planner available 24/7.

Built as a portfolio project targeting AI backend engineer roles — demonstrating RAG pipelines, LiteLLM gateway, ChromaDB, LangFuse observability, guardrails, Redis caching, and a React frontend. Retrieval quality is measured against a hand-labelled golden dataset — see [Retrieval Evaluation](#retrieval-evaluation).

---

## Demo

![Cue demo](docs/demo/demo.gif)

<table>
<tr>
<td width="50%">

**Empty state** — suggested prompts and corpus rail

![Empty state](docs/demo/01-empty-state.png)

</td>
<td width="50%">

**Question typed** — context chips set, Ask enabled

![Question typed](docs/demo/03-question-typed.png)

</td>
</tr>
<tr>
<td width="50%">

**Answer** — stat pill, source citations, follow-ups

![Answer](docs/demo/04-answer.png)

</td>
<td width="50%">

**PDF export** — A4 preview with brief summary and sources

![Export modal](docs/demo/05-export-modal.png)

</td>
</tr>
</table>

> Screenshots and video captured via `cd e2e && npm run capture-demo` (uses `LLM_MOCK=true` — no API keys required).

---

## Architecture

Cue is a RAG application: a Next.js chat UI calls a FastAPI backend that retrieves Thinkbox research from ChromaDB, generates grounded answers via LiteLLM, and caches responses in Redis (or an in-memory dict when `REDIS_URL` is unset).

### Deployment

**Local dev** — Next.js serves the UI on `:3000`; the browser calls FastAPI on `:8000` via `NEXT_PUBLIC_API_URL`. **Docker** — nginx serves the static export and proxies `/api/*` to the backend; Redis backs the cache.

```mermaid
flowchart TB
    subgraph dev["Local development"]
        BrowserDev["Browser"]
        NextDev["Next.js dev server :3000"]
        APIdev["FastAPI :8000"]
        BrowserDev -->|"UI"| NextDev
        BrowserDev -->|"POST /api/query"| APIdev
    end

    subgraph prod["Docker Compose (production)"]
        BrowserProd["Browser :80"]
        Nginx["nginx<br/>static export + /api proxy"]
        APIprod["FastAPI backend"]
        Redis["Redis"]
        ChromaProd["ChromaDB<br/>chroma_db/"]
        BrowserProd --> Nginx
        Nginx -->|"/api/*"| APIprod
        APIprod --> Redis
        APIprod --> ChromaProd
    end

    subgraph external["External services"]
        OpenAI["OpenAI<br/>embeddings + LLMs"]
        Anthropic["Anthropic<br/>fallback LLM"]
        LangFuse["LangFuse<br/>traces & costs"]
    end

    ChromaDev["ChromaDB<br/>chroma_db/"]
    APIdev --> ChromaDev
    APIdev --> OpenAI
    APIdev --> Anthropic
    APIdev --> LangFuse
    APIprod --> OpenAI
    APIprod --> Anthropic
    APIprod --> LangFuse
```

### Query pipeline

Structured brief fields (`sector`, `brand_stage`, etc.) shape cache keys and ChromaDB metadata filters alongside the freeform question.

```mermaid
flowchart TD
    UI["Next.js UI<br/>Zustand store → lib/api.ts"]
    API["POST /api/query<br/>FastAPI routes.py"]

    UI -->|"question + brief"| API

    API --> CacheGet{"Cache lookup<br/>Redis or dict"}
    CacheGet -->|hit| ReturnCached["Return cached answer"]
    CacheGet -->|miss| InputGuard["Input guardrail<br/>GPT-4o-mini via LiteLLM"]
    InputGuard -->|rejected| Refuse["400 — off-topic refusal"]
    InputGuard -->|approved| Retrieve["ChromaDB retrieval<br/>embed query + top-5 chunks, metadata filter"]
    Retrieve --> Chroma[(ChromaDB<br/>thinkbox_docs)]
    Chroma --> Generate["Answer generation<br/>LiteLLM → GPT-4o → Claude fallback"]
    Generate --> OutputGuard["Output guardrail<br/>GPT-4o-mini — stats grounded?"]
    OutputGuard -->|failed| SafeFallback["Safe template answer"]
    OutputGuard -->|approved| BuildSources["Build source citations"]
    SafeFallback --> BuildSources
    BuildSources --> CacheSet["Cache write<br/>TTL 7 days"]
    CacheSet --> ReturnFresh["Return answer + sources"]
    Generate -.->|traces| LF[LangFuse]

    ReturnCached --> UI
    ReturnFresh --> UI
    Refuse --> UI
```

### Frontend structure

```mermaid
flowchart LR
    Page["app/page.tsx"] --> CueApp["CueApp"]
    CueApp --> Store["Zustand store<br/>lib/store.ts"]
    Store --> ApiClient["lib/api.ts"]
    CueApp --> Composer["Composer + Brief chips"]
    CueApp --> Thread["Thread bubbles<br/>answer / refusal / error"]
    CueApp --> Rails["EvidenceRail + CorpusRail"]
    CueApp --> Overlays["HistoryDrawer + ExportModal"]
    ApiClient -->|"POST /api/query"| Backend["FastAPI"]
```

### Offline ingestion

Run manually via `scripts/ingest.py` or `POST /api/ingest` (API key required).

```mermaid
flowchart LR
    PDFs["Thinkbox PDFs<br/>data/pdfs/"] --> Ingest["ingest.py / ingestor.py"]
    Ingest --> Extract["pypdf text extract"]
    Extract --> Chunk["Chunk 800 tokens<br/>100 overlap"]
    Chunk --> EmbedIngest["OpenAI embeddings<br/>text-embedding-3-small"]
    EmbedIngest --> Upsert["ChromaDB upsert<br/>metadata: topic, sector, page"]
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
| Containerisation | Docker Compose (dev) / single-container Dockerfile (standalone) |
| E2E tests | Playwright (mock mode, no API keys required) |

---

## Quick Start

### Try it without API keys (mock mode)

The fastest way to see the app working — no API keys, no corpus, no Docker.
`LLM_MOCK=true` runs the full pipeline against deterministic fixtures (it's how
the E2E tests and the demo above run). Requires [uv](https://docs.astral.sh/uv/)
and Node 22+.

```bash
cd frontend && npm install && cd ..   # first time only
make start MOCK=1                     # backend :8000 + frontend :3000, detached
# open http://localhost:3000
make stop                             # shut everything down
```

`make status` shows what's running, `make logs` tails both servers, and
`make dev` runs both in the foreground instead (Ctrl-C stops them). Or run the
servers by hand:

```bash
# Terminal 1 — backend in mock mode
cd backend
LLM_MOCK=true uv run uvicorn app.main:app --port 8000

# Terminal 2 — frontend
cd frontend
npm install
echo 'NEXT_PUBLIC_API_URL=http://localhost:8000' > .env.local
npm run dev            # open http://localhost:3000
```

### Local development (real answers)

Real answers need LLM API keys **and an ingested corpus** — until both are in
place, every query returns 503. See [Ingest the corpus](#ingest-the-corpus).

**Backend:**
```bash
cd backend
cp .env.example .env   # fill in OPENAI_API_KEY (and ANTHROPIC_API_KEY for fallback)
uv run uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
echo 'NEXT_PUBLIC_API_URL=http://localhost:8000' > .env.local
npm run dev            # http://localhost:3000
```

### Docker (full stack — nginx + Redis)

```bash
cp backend/.env.example backend/.env   # fill in API keys
cp .env.example .env                   # set UID/GID so ChromaDB bind mount is writable
docker compose up --build
```

Open **http://localhost** — nginx serves the UI and proxies `/api/*` to the
backend (which is not directly published in this setup). The root `.env` sets
`UID` and `GID` to match your host user (required on Linux/WSL so
`./backend/chroma_db` is not read-only inside the container); run `id -u` and
`id -g` if unsure.

Until the corpus is ingested, `/api/health` reports `degraded` (503) and the
container shows as such — that's expected on a fresh clone, not a broken build.

### Standalone single-container (no nginx or Redis dependency)

```bash
cp backend/.env.example backend/.env   # required — the config check refuses default keys in production
docker compose -f docker-compose.standalone.yml up --build
```

The root `Dockerfile` is a multi-stage build: Node 22 builds the Next.js static export, then Python 3.13 runs FastAPI and serves the static files via `STATIC_DIR`. All traffic on `:8000`.

### Ingest the corpus

Download the research PDFs from [thinkbox.tv/research](https://www.thinkbox.tv/research)
into `data/pdfs/`, named exactly as the ingestion registry expects (embedding them
uses your OpenAI key):

| Filename | Document |
|----------|----------|
| `profit-ability-2.pdf` | Profit Ability 2 |
| `profit-ability-1.pdf` | Profit Ability 1 |
| `as-seen-on-tv.pdf` | As Seen on TV: Supercharging Small Business |
| `peter-field-white-paper.pdf` | TV is at the Heart of Effectiveness |
| `payback-4.pdf` | Payback 4: Pathways to Profit |
| `tv-viewing-report-2024.pdf` | TV Viewing Report 2024 |
| `signalling-success.pdf` | Signalling Success |
| `demand-generator.pdf` | Demand Generator |

The full filename ↔ metadata mapping (including scraped sources) lives in
`DOCUMENT_REGISTRY` in `backend/app/services/ingestor.py` — a file not listed
there is rejected. Then:

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

# Mock mode — returns deterministic answers without calling any LLM/embeddings API
# Useful for offline development and E2E tests
# LLM_MOCK=false
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
  "answer": {
    "summary": ["Based on Thinkbox research, TV delivers £5.61 ROI per £1 spent [1]."],
    "stats": [{ "value": "£5.61", "unit": "ROI per £1 spent", "context": "141 brands, 14 categories", "source": "Profit Ability 2", "page": 12 }],
    "chart": null,
    "checklist": null,
    "followups": ["How does this change for a DTC brand?"]
  },
  "sources": [
    { "title": "Profit Ability 2", "chunk": "TV delivered...", "url": "https://thinkbox.tv/..." }
  ],
  "cached": false,
  "model_used": "gpt-4o"
}
```

### `GET /api/health`

```json
{
  "status": "ok",
  "chroma_docs": 408,
  "version": "0.1.0",
  "redis": "ok",
  "llm_configured": true,
  "langfuse_enabled": true
}
```

`redis`: `"ok"` | `"disabled"` | `"unavailable"`

Returns **503** with `"status": "degraded"` when the corpus is empty or Redis is
configured but unreachable (never in mock mode). A fresh clone is degraded until
ingestion — the Docker healthchecks treat any HTTP response as alive for this
reason.

### `GET /api/corpus`

Lists ingested documents with chunk counts — powers the corpus rail in the UI.

```json
[{ "source_title": "Profit Ability 2", "chunks": 45, "topic": "ROI" }]
```

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
│   │   ├── main.py               # FastAPI app, lifespan startup, CORS, static file mount
│   │   ├── models.py             # Shared Pydantic models (StructuredAnswer, AnswerStat, etc.)
│   │   ├── api/routes.py         # /api/query, /api/ingest, /api/health
│   │   ├── core/config.py        # Settings via pydantic-settings (incl. LLM_MOCK)
│   │   └── services/
│   │       ├── embedder.py       # OpenAI text-embedding-3-small
│   │       ├── retriever.py      # ChromaDB retrieval + metadata filter
│   │       ├── generator.py      # LiteLLM → GPT-4o / Claude fallback; strict JSON validation
│   │       ├── cache.py          # Redis + in-memory dict, same interface
│   │       ├── guardrails.py     # Input + output LLM checks
│   │       └── ingestor.py       # PDF → chunks → embeddings → ChromaDB
│   ├── scripts/
│   │   ├── ingest.py             # Offline corpus ingestion
│   │   └── test_retrieval.py     # Retrieval quality smoke test
│   ├── tests/                    # pytest unit + integration tests
│   ├── Dockerfile                # Backend-only image (used by docker-compose.yml)
│   └── pyproject.toml
├── frontend/
│   ├── app/                      # Next.js App Router
│   ├── components/               # atoms / composer / thread / rail / layout
│   ├── overlays/                 # HistoryDrawer, ExportModal
│   ├── lib/                      # types.ts, api.ts, store.ts (Zustand)
│   └── __tests__/                # Jest + React Testing Library (62 tests)
├── e2e/                          # Playwright E2E tests (LLM_MOCK=true, no API keys needed)
│   ├── tests/app.spec.ts
│   └── playwright.config.ts
├── data/pdfs/                    # Thinkbox PDFs (gitignored — add manually)
├── Dockerfile                    # Multi-stage: Node 22 → Python 3.13 (standalone)
├── docker-compose.yml            # Full stack: nginx + Redis + backend
├── docker-compose.standalone.yml # Single-container: FastAPI serves static + API
└── README.md
```

---

## Key Design Decisions

**LiteLLM gateway** — wraps OpenAI and Anthropic behind a single interface. Model routing, fallback chains, and cost tracking work without touching call sites. Kept even where it feels like overkill because it's a named requirement for the target role.

**ChromaDB local** — zero cost, no external dependency, runs in Docker. Sufficient for an 8-10 document corpus. Swap path: same `retriever.py` interface → Qdrant or pgvector.

**Two-stage guardrails** — GPT-4o-mini checks input (on-topic?) and output (stats grounded in sources?). Hallucinated statistics in a media planning tool cause real commercial harm, so both stages are non-negotiable.

**Redis / dict cache** — `cache.py` exposes a `get`/`set`/`clear` interface. `REDIS_URL` set → `RedisCache`; unset → `ResponseCache` (dict). Redis errors degrade gracefully to cache-miss, never 500. `fakeredis` in tests — no real Redis needed in CI.

**Static export + nginx reverse proxy** — `frontend/` builds to static files (`output: 'export'`). In production (`docker compose up`), nginx serves the static export on `:80` and proxies `/api/*` to FastAPI. In local development, run Next.js dev server (`npm run dev`) on `:3000` and FastAPI on `:8000` separately. No Node.js runtime in production.

**Strict LLM output validation** — `generator.py` validates every LLM response against `StructuredAnswer` (Pydantic v2). Invalid JSON or schema mismatches raise immediately; `routes.py` catches these as 503s. No silent fallbacks that could mask hallucinations.

**LLM mock mode** — Set `LLM_MOCK=true` to short-circuit all LLM and embedding calls. Generator, guardrails, and retriever return deterministic fixtures. Used for offline development and Playwright E2E tests — no API keys or live services needed.

---

## Retrieval Evaluation

Retrieval quality is measured, not assumed. A hand-labelled golden dataset
(`backend/eval/golden_qa.json`, 25 questions across five types — exact-keyword,
semantic, noisy, comparison, multi-doc) is scored against the live retriever with
Recall@K, Precision@K, and MRR.

```bash
cd backend
uv run scripts/eval_retrieval.py                       # production path
uv run scripts/eval_retrieval.py --ignore-threshold    # pure ranker (no distance filter)
uv run scripts/eval_retrieval.py --out eval/results/run.json   # save a snapshot
```

**Baseline** (408-chunk corpus; relevance judged at page level for the long PDFs,
title level for short/scraped sources):

| Question type | MRR | R@1 | R@3 | R@5 | P@5 |
|---------------|-----|-----|-----|-----|-----|
| **Overall**   | **0.87** | **0.55** | **0.81** | **0.89** | **0.38** |
| exact-keyword | 0.90 | 0.70 | 0.80 | 0.80 | 0.24 |
| semantic      | 1.00 | 0.80 | 0.90 | 1.00 | 0.60 |
| noisy         | 1.00 | 0.80 | 0.90 | 1.00 | 0.28 |
| comparison    | 0.67 | 0.15 | 0.75 | 0.95 | 0.40 |
| multi-doc     | 0.77 | 0.30 | 0.70 | 0.70 | 0.40 |

Metrics are hand-rolled pure functions (`backend/eval/metrics.py`, unit-tested) — no
heavy eval dependency. The script doubles as a regression check: re-run before and
after any retrieval change and keep the change only if the numbers move.

### What the eval surfaced, and where to improve next

These are evidence-led hypotheses — none are implemented yet, by design. Each should
be A/B'd against this benchmark before adoption:

- **The distance filter is inert.** Production and `--ignore-threshold` runs are
  identical, so the 0.75 cosine-distance cutoff prunes nothing at top-5. Either lower
  it so it actually gates low-confidence chunks, or remove it.
- **Comparison questions rank poorly at the top** (R@1 = 0.15). "A vs B" queries
  retrieve a blend of both sides. Decomposing into two sub-queries, retrieving each,
  then merging before a rerank should lift the best answer to rank 1.
- **Multi-doc misses the second source** (R@5 = 0.70). The supporting document often
  sits just outside top-5. Retrieve wider (k = 8–10) and rerank to 5 with a
  cross-encoder to pull it up.
- **Exact-keyword precision is noisy** (P@5 = 0.24). Number/term queries ("£4.11",
  "60:40") are where lexical matching shines — a BM25 + dense hybrid is the most
  promising single change to test here.

---

## Development

Everything below is wrapped in the root `Makefile`: `make start [MOCK=1]` /
`make stop` / `make status` / `make logs` / `make dev` / `make test` /
`make e2e` / `make ingest`.

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

# E2E tests (Playwright — starts backend + frontend automatically)
cd e2e
npm install
npx playwright install chromium
npm test
```

E2E tests use `LLM_MOCK=true` so no API keys are required. Playwright spins up both servers automatically via `webServer` config.

### Contributing

Issues and PRs are welcome. Before pushing, run the four checks above
(`black`/`flake8`/`pytest` and `npm run lint`/`npm test`) — CI enforces all of
them on every PR.

---

## Disclaimer & Attribution

This project is an independent educational and experimental tool and is not affiliated with, endorsed by, or sponsored by Thinkbox or any associated organisations. All referenced reports, trademarks, and source materials remain the property of their respective owners.

The application references publicly available research documents and provides grounded citations and references to original sources where possible.

---

## License

Licensed under the [Apache License 2.0](LICENSE). You are free to use, modify, and distribute this work, including commercially, provided you retain attribution as set out in the [NOTICE](NOTICE) file.
