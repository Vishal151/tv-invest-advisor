import logging
from openai import AsyncOpenAI
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_client = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def embed(text: str) -> list[float]:
    """Embed a single string. Returns 1536 floats."""
    client = get_client()
    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=text.strip(),
    )
    return response.data[0].embedding


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple strings in one API call."""
    client = get_client()
    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=[t.strip() for t in texts],
    )
    return [item.embedding for item in response.data]
