FROM python:3.13-slim
RUN pip install uv --quiet

WORKDIR /app

# Copy lockfiles first — layer cached until deps change
COPY pyproject.toml uv.lock ./

# Install production deps only; --frozen ensures lockfile is honoured
RUN uv sync --frozen --no-group dev --no-install-project

# Copy application source
COPY app/ ./app/
COPY scripts/ ./scripts/

# Create volume mount points and non-root user
RUN mkdir -p chroma_db data/pdfs \
    && adduser --disabled-password --no-create-home --gecos "" --uid 1001 appuser \
    && chown -R appuser:appuser /app

USER appuser

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
