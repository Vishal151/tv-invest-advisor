from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Literal
from functools import lru_cache


class Settings(BaseSettings):
    """
    Central settings — all values loaded from environment / .env file.
    Access anywhere via: from app.core.config import get_settings; settings = get_settings()
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    app_env: Literal["development", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["text", "json"] = "text"
    version: str = "0.1.0"

    # ── CORS ─────────────────────────────────────────────────────────────────
    cors_origins: str = Field(default="http://localhost:3000")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # ── API security ─────────────────────────────────────────────────────────
    api_key: str = Field(default="dev-key", description="Protects POST /api/ingest")

    # ── LLM providers ────────────────────────────────────────────────────────
    openai_api_key: str = Field(default="", description="OpenAI API key")
    anthropic_api_key: str = Field(default="", description="Anthropic API key")

    # Primary model (via LiteLLM)
    primary_model: str = "gpt-4o"
    fallback_model: str = "claude-3-5-sonnet-20241022"
    guardrail_model: str = "gpt-4o-mini"  # cheap + fast for input/output checks

    # Embedding model
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # ── LangFuse observability ────────────────────────────────────────────────
    langfuse_public_key: str = Field(default="", description="LangFuse public key")
    langfuse_secret_key: str = Field(default="", description="LangFuse secret key")
    langfuse_host: str = "https://cloud.langfuse.com"

    # ── Mock mode ──────────────────────────────────────────────────────────────
    llm_mock: bool = Field(default=False, description="Return deterministic mock responses. Set LLM_MOCK=true for offline dev/E2E.")

    # ── ChromaDB ─────────────────────────────────────────────────────────────
    chroma_db_path: str = "./chroma_db"
    chroma_collection: str = "thinkbox_docs"

    # ── RAG settings ─────────────────────────────────────────────────────────
    retrieval_top_k: int = 5  # chunks returned per query
    retrieval_distance_threshold: float = 0.75  # cosine distance; chunks above this are discarded
    chunk_size: int = 800  # words per chunk (~1000-1100 tokens; not exact token count)
    chunk_overlap: int = 100  # word overlap between chunks

    # ── Cache ────────────────────────────────────────────────────────────────
    cache_ttl_seconds: int = 60 * 60 * 24 * 7  # 7 days
    cache_max_size: int = 500  # max entries in dict cache

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = Field(default="", description="Redis URL. Empty = use in-memory dict cache.")

    @property
    def redis_enabled(self) -> bool:
        return bool(self.redis_url)

    # ── Valid enum values for structured query inputs ─────────────────────────
    valid_sectors: list[str] = [
        "FMCG",
        "Retail",
        "Finance",
        "Auto",
        "Telco",
        "Travel",
        "DTC",
        "Other",
    ]
    valid_brand_stages: list[str] = [
        "start-up",
        "scale-up",
        "established",
        "large",
    ]
    valid_tv_history: list[str] = [
        "never",
        "tried",
        "regular",
    ]
    valid_primary_goals: list[str] = [
        "sales",
        "brand",
        "both",
        "unsure",
    ]
    valid_budget_tiers: list[str] = [
        "under-100k",
        "100k-500k",
        "500k-2m",
        "2m-plus",
        "undecided",
    ]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def langfuse_enabled(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    Use this everywhere — never instantiate Settings() directly.
    """
    return Settings()
