import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.routes import router

settings = get_settings()

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def _check_redis() -> str:
    """Returns 'ok', 'disabled', or 'unavailable'."""
    if not settings.redis_enabled:
        return "disabled"
    from app.services.cache import cache, RedisCache

    if not isinstance(cache, RedisCache):
        return "disabled"
    import redis as redis_lib

    try:
        cache._client.ping()
        return "ok"
    except redis_lib.RedisError:
        return "unavailable"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting TV Investment Advisor v{settings.version} [{settings.app_env}]")

    # Warm up ChromaDB — initialises connection so first request isn't slow
    try:
        from app.services.retriever import get_collection

        col = get_collection()
        logger.info(f"ChromaDB ready — {col.count()} chunks")
    except Exception as e:
        logger.warning(f"ChromaDB warmup failed: {e}")

    # Check Redis connectivity at startup
    redis_status = _check_redis()
    logger.info(f"Redis: {redis_status}")
    if settings.redis_enabled and redis_status == "unavailable":
        logger.warning("Redis is configured but unreachable — cache will fail gracefully")

    yield
    logger.info("Shutting down")


app = FastAPI(
    title="TV Investment Advisor",
    description="RAG-powered TV advertising advisor grounded in Thinkbox research",
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
