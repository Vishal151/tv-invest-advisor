# Stage 1: compile Next.js static export
FROM node:22-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci --quiet
COPY frontend/ .
RUN npm run build

# Stage 2: Python runtime serving both API and static files
FROM python:3.13-slim AS runtime
RUN pip install uv --quiet
WORKDIR /app

ENV UV_CACHE_DIR=/app/.cache/uv

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-group dev --no-install-project

COPY backend/app/ ./app/
COPY backend/scripts/ ./scripts/
COPY --from=frontend-builder /frontend/out ./static

ARG APP_UID=1001
ARG APP_GID=1001
RUN mkdir -p chroma_db data/pdfs .cache/uv \
    && groupadd -g "${APP_GID}" appuser \
    && useradd -u "${APP_UID}" -g appuser --no-create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app

USER ${APP_UID}

ENV STATIC_DIR=/app/static
# In this image the code lives at /app/app, so the config default (repo-layout
# relative) would miss — point ingestion at the compose bind mount explicitly
ENV PDF_DIR=/app/data/pdfs

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
