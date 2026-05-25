FROM python:3.13-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml ./

RUN uv sync --no-group dev

COPY app/ ./app/
COPY scripts/ ./scripts/

RUN mkdir -p chroma_db data/pdfs

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
