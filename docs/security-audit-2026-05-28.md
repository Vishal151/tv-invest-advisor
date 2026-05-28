# Security & Dead-Code Audit — TV Investment Advisor
_Date: 2026-05-28_

## Executive summary

- **Overall posture: mixed.** The application demonstrates good security hygiene in several areas (path-traversal prevention, gitignored `.env`, production startup checks, strict LLM output validation, safe JSON cache deserialization), but the network/transport and LLM-prompt layers are materially under-hardened for a production RAG service handling business-sensitive data.
- **Severity counts:** 15 High, 13 Medium, 13 Low, 6 Informational (44 verified findings).
- **Top risks:** (1) systemic prompt-injection exposure — user questions, PDF chunk content, and ingest-time metadata are interpolated into LLM and guardrail prompts with no escaping or delimiters, and the input guardrail fails *open* on error; (3) nginx terminates traffic over plain HTTP with no TLS and no security headers, running as root.
- **Biggest attack-surface wins:** remove two unused production dependencies (`httpx`, `requests`), pin all Docker base images, and lock down the unauthenticated `/api/health` and `/api/corpus` reconnaissance endpoints (add auth + rate limiting). These are low-effort, high-ROI changes.
- **Cross-cutting theme:** "secure-by-default" is inverted in config (`APP_ENV` defaults to `development`, `api_key` defaults to `dev-key`), guarded only by a runtime startup check. The check is effective today but represents a single point of failure for the entire production-hardening posture.
- **Dead code is low-risk but real:** several unused frontend components/props, two non-functional UI buttons (Copy/Regenerate), unused pytest fixtures and config fields, plus one genuine **runtime bug** — a missing `await` in `ingest_scraped.py` that will crash the script.

## Severity legend & counts

| Severity | Count | Meaning |
|----------|-------|---------|
| High | 15 | Serious weakness; exploitable or near-term production risk |
| Medium | 13 | Defense-in-depth gap or info disclosure |
| Low | 13 | Minor hygiene / hardening / dead code |
| Info | 6 | No action required (verified-correct or cosmetic) |

> **IMPORTANT — secrets hygiene reminder:** Never place real API keys or secrets in any file that lives inside a git repository, even if it is currently gitignored. `.gitignore` entries can be accidentally removed, tooling can commit ignored files, and files are routinely copied into backups, CI artefacts, and container images where the protection no longer applies. Always use a local secrets manager (e.g. 1Password, `pass`, or OS keychain) and inject secrets at runtime via environment variables or a secrets-management service. Treat any key that has ever touched a file on disk as compromised.

## High findings

### [HIGH] Indirect prompt injection via unescaped chunk content in LLM prompts
- **File:** `backend/app/services/generator.py:114-119` (and `guardrails.py:49-58`)
- **Category:** security / injection
- **Issue:** PDF chunk text is interpolated directly into the LLM user prompt with no escaping or delimiters. A malicious/poisoned PDF can carry instructions ("Ignore previous instructions…") that the model executes. The output guardrail uses the same vulnerable pattern, so it is not a reliable backstop.
- **Evidence:**
  ```python
  context_parts.append(
      f"[{i}] Source: {meta.get('source_title','Unknown')} "
      f"(page {meta.get('page','?')})\n{chunk['text']}")  # no escaping
  ```
- **Recommendation:** Wrap all retrieved content in XML-style data tags (`<chunk id="1">…</chunk>`) and instruct the model to treat tag contents as literal data, never instructions. Apply the same pattern in both generator and guardrail prompts.

### [HIGH] Direct prompt injection via unescaped user question (input guardrail)
- **File:** `backend/app/services/guardrails.py:92`
- **Category:** security / injection
- **Issue:** The raw user `question` (only `.strip()`ed, length-validated 5–500) is `.format()`-substituted into `INPUT_GUARD_PROMPT`. A crafted question can inject instructions into the guardrail classifier itself (e.g. force an `APPROVED` decision), defeating the on-topic check.
- **Evidence:**
  ```python
  prompt = INPUT_GUARD_PROMPT.format(question=question, context=context)
  ```
- **Recommendation:** Wrap the question in explicit delimiters (`<question>…</question>`) with a system instruction that tag contents are a literal query, not commands. Prefer separate message roles over template substitution.

### [HIGH] Identical injection risk in output guardrail prompt
- **File:** `backend/app/services/guardrails.py:123-125`
- **Category:** security / injection
- **Issue:** Both `{chunks}` and `{answer}` are `.format()`-injected unescaped into `OUTPUT_GUARD_PROMPT`. Either an injected main-LLM answer or poisoned corpus chunks can manipulate the guardrail, rendering the secondary defense bypassable.
- **Evidence:**
  ```python
  prompt = OUTPUT_GUARD_PROMPT.format(
      chunks=_format_chunks_for_review(chunks),  # unescaped
      answer=answer,                             # unescaped
  )
  ```
- **Recommendation:** Apply the same tag-based data/instruction separation as above to chunks and answer.

### [HIGH] Unsafe metadata extraction from user-controlled text files
- **File:** `backend/scripts/ingest_scraped.py:35-60` (stored line ~127; injected at `generator.py:117`, `guardrails.py:55`)
- **Category:** security / injection
- **Issue:** `ingest_scraped.py` reads `SOURCE:/URL:/TOPIC:/SECTOR:` headers from `.txt` files with no validation, stores them in ChromaDB, and they are later interpolated into LLM and guardrail prompts. A poisoned `.txt` header is a stored prompt-injection vector. Contrast with `ingestor.py`, which uses a trusted `DOCUMENT_REGISTRY`.
- **Evidence:**
  ```python
  if line.startswith("SOURCE:"):
      metadata["source_title"] = line[len("SOURCE:"):].strip()  # no validation
  ```
- **Recommendation:** Validate `topic`/`sector` against `settings.valid_topics`/`valid_sectors`; source title/URL against a trusted registry. Reject files with invalid metadata.

### [HIGH] API key verified with non-constant-time comparison
- **File:** `backend/app/api/routes.py:115-118`
- **Category:** security / auth-access
- **Issue:** `verify_api_key` uses `!=`, which short-circuits character-by-character and is theoretically vulnerable to timing attacks. The protected `/ingest` endpoint has no rate limiting, raising practical feasibility.
- **Evidence:**
  ```python
  if x_api_key != settings.api_key:
      raise HTTPException(status_code=401, detail="Invalid API key")
  ```
- **Recommendation:** `import hmac; if not hmac.compare_digest(x_api_key, settings.api_key): ...`

### [HIGH] Missing rate limiting on state-mutating `/api/ingest`
- **File:** `backend/app/api/routes.py:274-275`
- **Category:** security / auth-access
- **Issue:** `/ingest` is protected only by API key, with no rate limit. `limiter` is already imported and used on `/query` (line 145). An authenticated attacker can flood resource-intensive ingest calls (OpenAI embeddings + vector upserts), causing cost/resource exhaustion.
- **Evidence:**
  ```python
  @router.post("/ingest", dependencies=[Depends(verify_api_key)])
  async def ingest(request: IngestRequest):
  ```
- **Recommendation:** Add `@limiter.limit("5/minute")` (conservative for an admin op).

### [HIGH] Dangerous CORS: wildcards combined with credentials, no origin validation
- **File:** `backend/app/main.py:112-118`
- **Category:** security / config (merged: two High + one Medium finding reference this block)
- **Issue:** `allow_credentials=True` with `allow_methods=["*"]` and `allow_headers=["*"]` violates least privilege. The API only uses GET/POST. Critically, `cors_origins` (`config.py:27`) has no validation preventing `"*"`, so a future env misconfiguration would create a CSRF-grade hole.
- **Evidence:**
  ```python
  CORSMiddleware,
  allow_origins=settings.cors_origins_list,
  allow_credentials=True,
  allow_methods=["*"], allow_headers=["*"],
  ```
- **Recommendation:** `allow_methods=["GET","POST"]`, `allow_headers=["Content-Type","X-API-Key"]`. Add a validator rejecting `"*"` in origins whenever credentials are enabled.

### [HIGH] `API_KEY` defaults to weak `dev-key`
- **File:** `backend/app/core/config.py:34`
- **Category:** config / secrets-config
- **Issue:** Default `api_key="dev-key"` protects `/ingest`. A production startup check (`main.py:55-69`) raises if `APP_ENV=production` and the key is still `dev-key` — effective, but the entire safeguard hinges on `APP_ENV` being set and the lifespan check running. Validation also checks equality only, not entropy.
- **Evidence:**
  ```python
  api_key: str = Field(default="dev-key", description="Protects POST /api/ingest")
  ```
- **Recommendation:** Remove the weak default (require explicit config), inject via secrets manager, use a 32+ char random key. (One Low-rated duplicate of this finding is merged here; rated High per the secrets-config verifier.)

### [HIGH] Backend healthcheck reports healthy while dependencies are down
- **File:** `docker-compose.yml:40-51` (root cause: `routes.py:124-135`)
- **Category:** infra / infra-hardening
- **Issue:** The healthcheck only checks HTTP reachability of `/api/health`, which **always returns 200** regardless of Redis/ChromaDB state (`check_redis_status()` and `get_doc_count()` swallow exceptions). Containers report healthy while non-functional, breaking orchestration/failover.
- **Evidence:**
  ```yaml
  test: ["CMD","python","-c","import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"]
  ```
- **Recommendation:** Make `/api/health` return 503 when a critical dependency (ChromaDB; Redis if enabled) is unavailable, so the Docker healthcheck reflects real readiness.

### [HIGH] nginx serves traffic over unencrypted HTTP (no TLS)
- **File:** `nginx/nginx.conf:4`
- **Category:** config / infra-hardening
- **Issue:** nginx listens only on port 80, no SSL anywhere. All frontend and proxied API traffic — user queries, responses, `X-API-Key` — travels in cleartext, exposed to network eavesdropping.
- **Evidence:**
  ```
  listen 80;   # no ssl_certificate, no listen 443, no https redirect
  ```
- **Recommendation:** Add `listen 443 ssl http2;` with certs (Let's Encrypt), enforce TLS1.2+, redirect 80→443.

### [HIGH] Missing security headers in nginx
- **File:** `nginx/nginx.conf:1-28`
- **Category:** config / infra-hardening
- **Issue:** No `add_header` for CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy. Frontend is exposed to clickjacking, MIME-sniffing, and XSS-amplifying conditions.
- **Evidence:** server block contains only `proxy_set_header X-Real-IP`/`X-Forwarded-For`; no security `add_header` directives.
- **Recommendation:** Add `X-Frame-Options "SAMEORIGIN"`, `X-Content-Type-Options "nosniff"`, `Referrer-Policy`, a tuned CSP, and `Strict-Transport-Security` (with TLS), all with `always`.

### [HIGH] nginx container runs as root
- **File:** `nginx/Dockerfile:1-14`
- **Category:** security / infra-hardening
- **Issue:** No `USER` directive or user creation; `nginx:alpine` master runs as root. The backend service correctly drops privileges — nginx does not. Compromise yields container root.
- **Evidence:** No `USER` / `adduser` in `nginx/Dockerfile`; no `user nginx;` in `nginx.conf`.
- **Recommendation:** Create and switch to a non-root nginx user and set `user nginx;` in the config.

### [HIGH] Docker base images unpinned (no patch/digest)
- **Files:** `Dockerfile:2,10`; `backend/Dockerfile:1`; `nginx/Dockerfile:2,11`
- **Category:** dependency / infra-hardening (three findings merged — same class across all Dockerfiles)
- **Issue:** Images pin only major.minor (`node:22-alpine`, `python:3.13-slim`, `node:20-alpine`, `nginx:alpine`). Builds are non-reproducible and silently pull in upstream changes/CVEs.
- **Evidence:**
  ```dockerfile
  FROM node:22-alpine AS frontend-builder
  FROM python:3.13-slim AS runtime
  FROM nginx:alpine
  ```
- **Recommendation:** Pin to patch version + SHA256 digest (`FROM python:3.13.x-slim@sha256:...`) across all Dockerfiles.

### [HIGH] Missing `await` on `embed_batch` — runtime crash in `ingest_scraped.py`
- **File:** `backend/scripts/ingest_scraped.py:121`
- **Category:** dead-code / correctness
- **Issue:** `embed_batch()` is `async` but called without `await`, returning a coroutine instead of embeddings; the subsequent `zip` (line 124) and `collection.upsert` (line 130) operate on a coroutine and crash. The enclosing `ingest_text_file()` is sync, so it cannot directly `await`.
- **Evidence:**
  ```python
  embeddings = embed_batch(new_chunks)  # missing await
  ```
- **Recommendation:** Make `ingest_text_file()` async and `await embed_batch(...)`, or call via `asyncio.run()`. Match the correct pattern in `ingest.py:218` / `ingestor.py:143`.

## Medium findings

### [MEDIUM] Unauthenticated `/api/health` leaks system info
- **File:** `backend/app/api/routes.py:124-135` — Category: security/auth-access
- **Issue:** Public endpoint exposes chroma doc count, Redis status, version, `llm_configured`, `langfuse_enabled` — useful reconnaissance.
- **Recommendation:** Require API key or return minimal `{status:"ok"}`; at minimum mask `llm_configured`/`langfuse_enabled` in production.

### [MEDIUM] Unauthenticated `/api/corpus` exposes ingested-doc metadata
- **File:** `backend/app/api/routes.py:138-141` — Category: security/auth-access
- **Issue:** Public `get_corpus_summary()` returns per-document titles, topics, chunk counts, URLs — full corpus enumeration.
- **Recommendation:** Add `Depends(verify_api_key)`, or return aggregate counts only.

### [MEDIUM] Rate limiting only on `/api/query`
- **File:** `backend/app/api/routes.py:145` — Category: security/auth-access
- **Issue:** `/health`, `/corpus`, `/ingest` have no rate limiting, enabling unlimited recon and (for ingest) resource abuse.
- **Recommendation:** `100/minute` on `/health` and `/corpus`; `5/minute` on `/ingest`.

### [MEDIUM] No security headers in FastAPI app
- **File:** `backend/app/main.py:99-125` — Category: infra
- **Issue:** App sets no X-Content-Type-Options, X-Frame-Options, HSTS, or CSP (relevant for the standalone/no-nginx deployment).
- **Recommendation:** Add a security-headers middleware (`nosniff`, `DENY`, HSTS in prod, `default-src 'self'`).

### [MEDIUM] Weak `question` validation + guardrail fails open
- **File:** `backend/app/api/routes.py:40` (fail-open at `guardrails.py:108`) — Category: config/injection
- **Issue:** `question` has length-only validation; if the guardrail LLM errors/rate-limits it returns `True` (approved), so malicious input reaches the main LLM unfiltered. No injection-resistant formatting downstream.
- **Recommendation:** Primary fix is delimiter/role-based prompting (see High injection findings). Consider failing closed or degrading to a safe template on guardrail error.

### [MEDIUM] Exception details leaked to client in `/ingest`
- **File:** `backend/app/api/routes.py:280-282` — Category: security/secrets-config
- **Issue:** `str(e)` for `FileNotFoundError`/`ValueError` returns internal paths, the `data/pdfs` directory, and `DOCUMENT_REGISTRY` hints to the client.
- **Recommendation:** Return generic messages ("Document not found" / "Invalid request"); log details server-side.

### [MEDIUM] `APP_ENV` defaults to `development`
- **File:** `backend/app/core/config.py:21` — Category: config/secrets-config
- **Issue:** If `APP_ENV` is unset in a deployment, the app runs in dev mode and exposes `/docs`. Secure-by-default is inverted.
- **Recommendation:** Default to `production`; set `APP_ENV=development` explicitly in dev.

### [MEDIUM] FastAPI `/docs` exposed when not explicitly production
- **File:** `backend/app/main.py:104-105` — Category: config/infra-hardening
- **Issue:** `/docs` and `/openapi.json` are exposed unless `is_production` is true; raw/cloud deploys without `APP_ENV=production` leak the API schema.
- **Recommendation:** Also gate `openapi_url` on production; enforce `APP_ENV=production` in all prod deploys.

### [MEDIUM] Unused production dependency: `httpx`
- **File:** `backend/pyproject.toml:8` — Category: dependency
- **Issue:** `httpx>=0.28.1` declared but never imported anywhere — pure CVE surface and lock-file bloat.
- **Recommendation:** Remove from production deps (move to dev only if a test needs it).

### [MEDIUM] Unused production dependency: `requests`
- **File:** `backend/pyproject.toml:19` — Category: dependency
- **Issue:** `requests>=2.34.2` declared but never imported; all HTTP goes through OpenAI/LiteLLM/Chroma/Redis clients.
- **Recommendation:** Remove from `pyproject.toml`.

### [MEDIUM] Uvicorn binds `0.0.0.0` (risk in standalone compose)
- **File:** `Dockerfile:35` — Category: config/infra-hardening
- **Issue:** Binding to all interfaces is fine behind nginx in `docker-compose.yml`, but `docker-compose.standalone.yml` maps `8000:8000` to the host, exposing the backend directly and bypassing nginx rate limiting.
- **Recommendation:** Behind nginx, bind `127.0.0.1`. For standalone, ensure the host port mapping is intended and that rate limiting still applies, or front it with a proxy.

### [MEDIUM] Non-functional `Copy` / `Regenerate` buttons
- **File:** `frontend/components/thread/AssistantBubble.tsx:84-101` — Category: dead-code
- **Issue:** Buttons render with `cursor:'pointer'` but have no `onClick`; no `handleCopy`/`handleRegenerate` exists. Clicking does nothing — UX confusion.
- **Recommendation:** Implement the handlers or remove the buttons until implemented.

### [MEDIUM] Error `reference` shown to users but never tracked
- **File:** `frontend/lib/types.ts:61` (gen `api.ts:96,118`; shown `ErrorCard.tsx:77`) — Category: dead-code
- **Issue:** `ErrorCard` tells users to "share with support" a reference ID, but no logging/Sentry/request-ID correlation captures it anywhere — a promised feature with no backing mechanism.
- **Recommendation:** Wire references to server-side logging/error tracking, or remove the "share with support" affordance.

### [MEDIUM] CI uses plaintext (test) secrets in env block
- **File:** `.github/workflows/ci.yml:33-36` — Category: security/infra-hardening
- **Issue:** `OPENAI_API_KEY: test-key` etc. hardcoded. Harmless values, but the pattern invites real-secret leakage.
- **Recommendation:** Use `${{ secrets.* }}` even for test placeholders.

### [MEDIUM] No explicit GitHub Actions workflow permissions
- **File:** `.github/workflows/ci.yml:1-8` — Category: security/infra-hardening
- **Issue:** No `permissions:` block, so `GITHUB_TOKEN` defaults to broad read/write.
- **Recommendation:** Add `permissions: { contents: read }` at workflow level.

### [MEDIUM] nginx container lacks a healthcheck
- **File:** `docker-compose.yml:53-65` — Category: infra/infra-hardening
- **Issue:** No healthcheck on nginx (redis and backend have them). A hung/crashed nginx won't be detected or restarted.
- **Recommendation:** Add a `wget --spider http://localhost/` healthcheck.

## Low / Informational findings

- `backend/app/core/config.py:34` — weak `dev-key` default (config-dimension duplicate of the High secrets finding) — remove default; rely on secrets injection, not just startup check.
- `backend/app/main.py:104-105` — `/docs` exposed in dev to unauthenticated users — optionally require API key for `/docs` even in dev.
- `backend/app/services/retriever.py:194-223` — sector/topic reach Chroma filter unvalidated *at point of use* — no action; validated upstream (`routes.py:50`), topic not user-supplied.
- `backend/app/api/routes.py:19-20` — stat-detection regex — no ReDoS risk; runs on LLM output only — no action.
- `backend/pyproject.toml:5-23` — all deps use `>=` pinning — adopt `uv.lock` for reproducible CI/prod builds.
- `backend/tests/conftest.py:7-11` — unused fixture `mock_settings` — remove.
- `backend/tests/conftest.py:47-51` — unused fixture `mock_retrieve` — remove.
- `backend/app/core/config.py:47` — unused field `embedding_dimensions` — remove (dim fixed by model).
- `backend/scripts/ingest.py:144-145` — unused chunk keys `word_start`/`word_end` — remove.
- `frontend/components/atoms/Chart.tsx:6,8` — unused prop `dense` — remove or implement.
- `frontend/components/atoms/Headline.tsx:10` — unused component (test-only) — remove component + test.
- `frontend/components/atoms/Trace.tsx:8` — unused component (test-only) — remove component + test.
- `frontend/components/atoms/Trace.tsx:5` — unused prop `onDone` — remove (secondary to unused Trace).
- `docker-compose.yml:2-13` — Redis has memory limit but no CPU limit — add `cpus: "0.5"`.
- **Info** `backend/app/services/ingestor.py:107-113` — path traversal correctly prevented via `resolve()` + containment check — no action.
- **Info** `backend/app/services/cache.py:79` — `json.loads` on app-generated, hash-keyed cache values — safe, no action.
- **Info** `backend/pyproject.toml:6-21` — all 9 target deps actively used — no action.
- **Info** `frontend/package.json:13-37` — core deps exact-pinned, dev deps caret — sound, no action.
- **Info** `frontend/lib/types.ts:19,21` — `Headline` type unused; `ChartBar` only used internally — optionally remove `Headline`, make `ChartBar` non-exported.
- **Info** `frontend/lib/api.ts:12,62` — `mapResponse`/`makeReference` private, used only internally — correct scoping, no action.

## Attack-surface reduction summary

| Item | File / location | Reason | Action |
|------|-----------------|--------|--------|
| `httpx` dependency | `backend/pyproject.toml:8` | Declared, never imported — pure CVE surface | Remove from prod deps |
| `requests` dependency | `backend/pyproject.toml:19` | Declared, never imported | Remove from `pyproject.toml` |
| `mock_settings` fixture | `backend/tests/conftest.py:7-11` | Never used by any test | Delete |
| `mock_retrieve` fixture | `backend/tests/conftest.py:47-51` | Never used by any test | Delete |
| `embedding_dimensions` field | `backend/app/core/config.py:47` | Referenced nowhere; dim fixed by model | Delete |
| `word_start`/`word_end` chunk keys | `backend/scripts/ingest.py:144-145` | Created, never read | Delete keys |
| `Headline` component + test | `frontend/components/atoms/Headline.tsx`, its test | No production import | Delete both |
| `Trace` component + `onDone` prop + test | `frontend/components/atoms/Trace.tsx`, its test | No production import | Delete both |
| `dense` prop | `frontend/components/atoms/Chart.tsx:6,8` | Declared, never used | Delete prop |
| `Copy`/`Regenerate` buttons | `frontend/components/thread/AssistantBubble.tsx:84-101` | No handlers; non-functional UI | Remove or implement |
| `Headline` type / exported `ChartBar` | `frontend/lib/types.ts:19,21` | Unused / internal-only export | Remove / un-export |
| `/api/health`, `/api/corpus` payloads | `backend/app/api/routes.py:124-141` | Unauthenticated recon surface | Auth + minimize payload |

## Prioritised remediation roadmap

### Quick wins (hours; high ROI)
1. **Fix the `await` bug** in `ingest_scraped.py:121` — currently crashes the script. (High, correctness)
2. **Constant-time API key compare** with `hmac.compare_digest` (`routes.py:115-118`). (High)
3. **Restrict CORS** to GET/POST + explicit headers, drop wildcards, add an origin validator rejecting `"*"` with credentials (`main.py:112-118`). (High)
4. **Rate-limit `/ingest` (5/min)**, `/health` and `/corpus` (100/min) (`routes.py`). (High/Medium)
5. **Remove `httpx` and `requests`** from `pyproject.toml`. (Medium)
6. **Generic error responses** in `/ingest` (`routes.py:280-282`). (Medium)
7. Delete dead code: unused fixtures, config field, chunk keys, `Headline`/`Trace` components + props, `dense` prop. (Low)

### Short term (days)
9. **Eliminate prompt-injection exposure** — wrap user question, chunk content, and answer in XML-style data tags with explicit "literal data" instructions in both generator and guardrail prompts (`generator.py:114-119`, `guardrails.py:92,123-125`). (3× High)
10. **Validate ingest-time metadata** in `ingest_scraped.py` against whitelists/registry. (High)
11. **Make `/api/health` return 503** on critical-dependency failure so Docker healthchecks are meaningful (`routes.py:124-135`, `docker-compose.yml:40-51`). (High)
12. **Auth/minimize `/api/health` and `/api/corpus`** payloads. (Medium ×2)
13. **Guardrail fail-closed** (or safe-template) on error; reconsider failing open (`guardrails.py:108`). (Medium)
14. **CI hardening**: move test secrets to `${{ secrets.* }}`, add `permissions: { contents: read }`. (Medium ×2)

### Hardening (longer-term posture)
15. **TLS on nginx** (`listen 443 ssl http2`, redirect 80→443) — eliminates cleartext API-key/query transit. (High)
16. **nginx security headers** (CSP, HSTS, X-Frame-Options, nosniff, Referrer-Policy) + **FastAPI security-headers middleware** for the standalone path. (High + Medium)
17. **Run nginx as non-root**. (High)
18. **Pin all Docker base images** to patch + SHA256 digest; adopt `uv.lock` for reproducible Python builds. (High + Low)
19. **Invert config defaults**: `APP_ENV=production`, remove `api_key="dev-key"` default; inject both via a secrets manager. Gate `openapi_url` on production. (High + Medium)
20. **Operational completeness**: add nginx healthcheck, Redis CPU limit, bind backend to `127.0.0.1` behind nginx, and wire error `reference` IDs to real server-side tracking. (Medium/Low)

## Refuted / dismissed during verification

- **".dockerignore does not exclude node_modules in nginx build stage"** — Refuted: `**/node_modules` correctly excludes `frontend/node_modules` per Docker pattern matching, and only `/app/out` is copied to the final stage; no evidence node_modules enter the build context.