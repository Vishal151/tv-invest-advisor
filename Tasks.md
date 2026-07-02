# Production Tasks — TV Investment Advisor

Current sources of truth:
- `docs/audit-2026-06-12.md` — full audit; "Outstanding work after remediation" lists what's open
- App review (2026-07-02) — "fix now" batch shipped in PR #2; "fix soon" batch shipped after it

---

## Outstanding

- [ ] Full-pipeline LangFuse tracing (root trace per request; spans for cache, guardrails, retrieval, generation) — pair with extracting `routes.query()` into an `answer_query()` service (audit M3)
- [ ] Sector filter decision: tag sector-specific chunks at ingest or remove the inert filter; A/B via eval (audit M5)
- [ ] Tune or remove the 0.75 retrieval distance threshold against the eval benchmark (audit M4 remainder)
- [ ] Pin Docker base images to patch + SHA256 digest (audit M11 remainder)
- [ ] Retrieval roadmap: BM25 hybrid + rerank, comparison-query decomposition, smaller chunks — A/B via eval
- [ ] App review "later" tier: responsive layout (no media queries today), modal a11y (Escape/focus trap/aria-live), cache entry versioning, dependency audit step in CI, embedder timeout, Redis maxmemory policy, scraped-ingestion page/sector metadata
- [ ] Audit Low findings L1–L14 (see audit doc); highest value: Literal types for request enums, thread titles + persistence, E2E job in CI

---

## Done (high level)

- **2026-07-02 — app review fix-soon batch**: store thread-race fix (in-flight answers land in the asking thread; navigation preserves turns) + 9-test `ask()`/`retry()` lifecycle suite; 422 mapping + composer length limits (5–500); evidence-rail citation ownership (older answers' citations no longer highlight the wrong source; click expands collapsed rail); ingest allowed-dir anchored via `PDF_DIR` setting instead of process CWD
- **2026-07-02 — app review fix-now batch (PR #2)**: frontend recovery from malformed 200s; per-client rate limiting behind nginx (`TRUST_PROXY_HEADERS`); `LLM_MOCK` rejected in production; degraded-tolerant Docker healthchecks; README keyless quickstart + badges + corpus table
- **2026-06-12 — audit remediation**: all High + 10 Medium findings (guardrail covers stats/chart, unified ingestion registry/chunker, honest `/api/health`, request-ID logging, live CorpusRail, fallback never cached, 429/X-Request-ID UX)
- **May 2026 — original build**: the P0–P3 list that used to live here is complete except the items carried into "Outstanding" above (full tracing, sector filter, nginx `limit_req`, SSE streaming, retry-budget heuristic — the last two are consider-later)
