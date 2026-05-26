FROM python:3.13-slim
RUN pip install uv --quiet

WORKDIR /app

# Match host uid/gid on Linux/WSL so bind-mounted chroma_db is writable (see .env.example)
ARG APP_UID=1001
ARG APP_GID=1001

# Copy lockfiles first — layer cached until deps change
COPY pyproject.toml uv.lock ./

# Install production deps only; --frozen ensures lockfile is honoured
RUN uv sync --frozen --no-group dev --no-install-project

# Copy application source
COPY app/ ./app/
COPY scripts/ ./scripts/

RUN mkdir -p chroma_db data/pdfs \
    && groupadd -g "${APP_GID}" appuser \
    && useradd -u "${APP_UID}" -g appuser --no-create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app

USER ${APP_UID}

ENV UV_CACHE_DIR=/app/.cache/uv

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
