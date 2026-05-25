import logging
from openai import OpenAI
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def embed(text: str) -> list[float]:
    """
    Embed a single string using OpenAI text-embedding-3-small.
    Returns a list of 1536 floats.
    """
    client = get_client()
    response = client.embeddings.create(
        model=settings.embedding_model,
        input=text.strip(),
    )
    return response.data[0].embedding


def embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Embed multiple strings in a single API call.
    More efficient than calling embed() in a loop.
    """
    client = get_client()
    response = client.embeddings.create(
        model=settings.embedding_model,
        input=[t.strip() for t in texts],
    )
    # API returns embeddings in the same order as input
    return [item.embedding for item in response.data]