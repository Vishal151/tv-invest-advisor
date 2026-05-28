import logging
import os
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

from app.core.config import get_settings
from app.core.limiter import limiter
from app.api.routes import router

settings = get_settings()


def _configure_logging() -> None:
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, settings.log_level)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
    logging.basicConfig(level=settings.log_level)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


_configure_logging()
logger = logging.getLogger(__name__)


def _check_production_config() -> None:
    """Raises RuntimeError if required production settings are missing or insecure."""
    if not settings.is_production:
        return
    if settings.api_key == "dev-key":
        raise RuntimeError(
            "API_KEY must be set in production — 'dev-key' is not a valid production secret"
        )
    if not settings.openai_api_key and not settings.anthropic_api_key:
        raise RuntimeError("At least one of OPENAI_API_KEY or ANTHROPIC_API_KEY must be set")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _check_production_config()
    logger.info(f"Starting TV Investment Advisor v{settings.version} [{settings.app_env}]")

    # Warm up ChromaDB — initialises connection so first request isn't slow
    try:
        from app.services.retriever import get_collection

        col = get_collection()
        logger.info(f"ChromaDB ready — {col.count()} chunks")
    except Exception as e:
        logger.warning(f"ChromaDB warmup failed: {e}")

    # Check Redis connectivity at startup
    from app.services.cache import check_redis_status

    redis_status = check_redis_status()
    logger.info(f"Redis: {redis_status}")
    if settings.redis_enabled and redis_status == "unavailable":
        logger.warning("Redis is configured but unreachable — cache will fail gracefully")

    # Warn on missing LLM keys in development
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY is not set — LLM calls will fail")
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY is not set — fallback model unavailable")

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

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

_static_dir = os.getenv("STATIC_DIR", "")
if _static_dir and os.path.isdir(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
