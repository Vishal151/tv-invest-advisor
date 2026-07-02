# Local development commands — run everything from the repo root.
#
#   make start          start backend (:8000) + frontend (:3000) in the background
#   make start MOCK=1   same, but backend in mock mode (no API keys, no corpus)
#   make stop           stop both
#   make status         show what's running + health
#   make logs           tail both server logs
#   make dev            both servers in the foreground (Ctrl-C stops everything)
#   make test           all checks: black, flake8, pytest, eslint, jest
#   make e2e            Playwright E2E suite (mock mode)
#   make ingest         ingest PDFs from data/pdfs/ into ChromaDB

.PHONY: dev start stop status logs test e2e ingest

RUN_DIR := .run
MOCK ?= 0
ifeq ($(MOCK),1)
BACKEND_ENV := LLM_MOCK=true
else
BACKEND_ENV :=
endif

# The browser needs to know where the API lives; created once if missing.
frontend/.env.local:
	echo 'NEXT_PUBLIC_API_URL=http://localhost:8000' > frontend/.env.local

dev: frontend/.env.local
	@trap 'kill 0' INT TERM; \
	( cd backend && $(BACKEND_ENV) uv run uvicorn app.main:app --reload --port 8000 ) & \
	( cd frontend && npm run dev ) & \
	wait

# setsid puts each server in its own process group so stop can kill the whole
# tree (uv/uvicorn-reloader and next both spawn children).
start: frontend/.env.local
	@mkdir -p $(RUN_DIR)
	@if [ -f $(RUN_DIR)/backend.pid ] && kill -0 $$(cat $(RUN_DIR)/backend.pid) 2>/dev/null; then \
		echo "backend already running (pid $$(cat $(RUN_DIR)/backend.pid))"; \
	else \
		cd backend && setsid nohup env $(BACKEND_ENV) uv run uvicorn app.main:app --reload --port 8000 \
			> $(CURDIR)/$(RUN_DIR)/backend.log 2>&1 & echo $$! > $(CURDIR)/$(RUN_DIR)/backend.pid; \
		echo "backend starting on :8000 $(if $(filter 1,$(MOCK)),[mock mode],)"; \
	fi
	@if [ -f $(RUN_DIR)/frontend.pid ] && kill -0 $$(cat $(RUN_DIR)/frontend.pid) 2>/dev/null; then \
		echo "frontend already running (pid $$(cat $(RUN_DIR)/frontend.pid))"; \
	else \
		cd frontend && setsid nohup npm run dev \
			> $(CURDIR)/$(RUN_DIR)/frontend.log 2>&1 & echo $$! > $(CURDIR)/$(RUN_DIR)/frontend.pid; \
		echo "frontend starting on :3000"; \
	fi
	@echo "open http://localhost:3000  ·  make logs to follow output  ·  make stop to shut down"

stop:
	@for s in backend frontend; do \
		if [ -f $(RUN_DIR)/$$s.pid ]; then \
			kill -- -$$(cat $(RUN_DIR)/$$s.pid) 2>/dev/null && echo "$$s stopped" || echo "$$s was not running"; \
			rm -f $(RUN_DIR)/$$s.pid; \
		else \
			echo "$$s was not running"; \
		fi; \
	done

status:
	@for s in backend frontend; do \
		if [ -f $(RUN_DIR)/$$s.pid ] && kill -0 $$(cat $(RUN_DIR)/$$s.pid) 2>/dev/null; then \
			echo "$$s: running (pid $$(cat $(RUN_DIR)/$$s.pid))"; \
		else \
			echo "$$s: stopped"; \
		fi; \
	done
	@code=$$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health 2>/dev/null); \
	if [ -z "$$code" ] || [ "$$code" = "000" ]; then \
		echo "backend health: unreachable"; \
	else \
		echo "backend health: HTTP $$code"; \
	fi

logs:
	tail -f $(RUN_DIR)/backend.log $(RUN_DIR)/frontend.log

test:
	cd backend && uv run black --check . && uv run flake8 . && uv run pytest
	cd frontend && npm run lint && npm test

e2e:
	cd e2e && npm test

ingest:
	cd backend && uv run scripts/ingest.py
