import logging
import re
from fastapi import APIRouter, HTTPException, Header, Depends, Request
from pydantic import BaseModel, Field, field_validator

from app.core.config import get_settings
from app.core.limiter import limiter
from app.services.cache import cache
from app.services.retriever import retrieve, get_doc_count
from app.services.generator import generate
from app.services.guardrails import check_input, check_output
from app.services.ingestor import run_ingest

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()

_STAT_PATTERN = re.compile(
    r"[\d,.]+\s*(%|£|\$|x\b|ROI|ROAS|billion|million|thousand)", re.IGNORECASE
)


def _answer_contains_statistic(answer: str) -> bool:
    """True if answer includes a number that looks like a quantitative claim."""
    return bool(_STAT_PATTERN.search(answer))

SAFE_FALLBACK_ANSWER = (
    "Based on Thinkbox research, TV advertising is consistently shown "
    "to be the most effective channel for driving long-term profit growth. "
    "Please refine your question for a more specific answer."
)


# ── Request / Response models ─────────────────────────────────────────────────


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=500)
    sector: str | None = None
    brand_stage: str | None = None
    tv_history: str | None = None
    primary_goal: str | None = None
    budget_tier: str | None = None

    @field_validator("sector")
    @classmethod
    def validate_sector(cls, v: str | None) -> str | None:
        if v is not None and v not in settings.valid_sectors:
            raise ValueError(f"Invalid sector '{v}'. Valid: {settings.valid_sectors}")
        return v

    @field_validator("brand_stage")
    @classmethod
    def validate_brand_stage(cls, v: str | None) -> str | None:
        if v is not None and v not in settings.valid_brand_stages:
            raise ValueError(f"Invalid brand_stage '{v}'. Valid: {settings.valid_brand_stages}")
        return v

    @field_validator("tv_history")
    @classmethod
    def validate_tv_history(cls, v: str | None) -> str | None:
        if v is not None and v not in settings.valid_tv_history:
            raise ValueError(f"Invalid tv_history '{v}'. Valid: {settings.valid_tv_history}")
        return v

    @field_validator("primary_goal")
    @classmethod
    def validate_primary_goal(cls, v: str | None) -> str | None:
        if v is not None and v not in settings.valid_primary_goals:
            raise ValueError(f"Invalid primary_goal '{v}'. Valid: {settings.valid_primary_goals}")
        return v

    @field_validator("budget_tier")
    @classmethod
    def validate_budget_tier(cls, v: str | None) -> str | None:
        if v is not None and v not in settings.valid_budget_tiers:
            raise ValueError(f"Invalid budget_tier '{v}'. Valid: {settings.valid_budget_tiers}")
        return v


class Source(BaseModel):
    title: str
    chunk: str
    url: str
    page: int | None = None
    topic: str | None = None
    distance: float | None = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[Source]
    cached: bool
    model_used: str


class IngestRequest(BaseModel):
    source_path: str


class HealthResponse(BaseModel):
    status: str
    chroma_docs: int
    version: str
    redis: str = "disabled"
    llm_configured: bool = False
    langfuse_enabled: bool = False


# ── Auth dependency ───────────────────────────────────────────────────────────


def verify_api_key(x_api_key: str = Header(...)) -> str:
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get("/health", response_model=HealthResponse)
async def health():
    from app.services.cache import check_redis_status

    return HealthResponse(
        status="ok",
        chroma_docs=get_doc_count(),
        version=settings.version,
        redis=check_redis_status(),
        llm_configured=bool(settings.openai_api_key or settings.anthropic_api_key),
        langfuse_enabled=settings.langfuse_enabled,
    )


@router.post("/query", response_model=QueryResponse)
@limiter.limit("20/minute")
async def query(request: Request, body: QueryRequest):
    question = body.question.strip()

    # 1. Cache lookup
    cached = cache.get(
        question=question,
        sector=body.sector,
        brand_stage=body.brand_stage,
        tv_history=body.tv_history,
        primary_goal=body.primary_goal,
        budget_tier=body.budget_tier,
    )
    if cached:
        return QueryResponse(**cached, cached=True)

    # 2. Input guardrail
    approved, reason = await check_input(
        question=question,
        sector=body.sector,
        brand_stage=body.brand_stage,
    )
    if not approved:
        raise HTTPException(
            status_code=400,
            detail="Query is outside the scope of this tool. "
            "Please ask about TV advertising, media planning, or brand growth.",
        )

    # 3. Retrieve relevant chunks
    chunks = await retrieve(
        question=question,
        sector=body.sector,
        brand_stage=body.brand_stage,
        primary_goal=body.primary_goal,
        tv_history=body.tv_history,
        budget_tier=body.budget_tier,
    )
    if not chunks:
        raise HTTPException(
            status_code=503,
            detail="No research documents found. " "Please ensure the corpus has been ingested.",
        )

    # 4. Generate answer via LiteLLM
    try:
        answer, model_used = await generate(
            question=question,
            chunks=chunks,
            sector=body.sector,
            brand_stage=body.brand_stage,
            budget_tier=body.budget_tier,
            primary_goal=body.primary_goal,
        )
    except Exception as e:
        logger.error(f"All LLM models failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="The answer service is temporarily unavailable. Please try again shortly.",
        )

    # 5. Output guardrail (retry once with stricter grounding before generic fallback)
    output_ok, reject_reason = await check_output(answer=answer, chunks=chunks)
    if not output_ok and _answer_contains_statistic(answer):
        logger.warning(
            f"Output guardrail rejected stat-containing response ({reject_reason}) — retrying"
        )
        try:
            answer, model_used = await generate(
                question=question,
                chunks=chunks,
                sector=body.sector,
                brand_stage=body.brand_stage,
                budget_tier=body.budget_tier,
                primary_goal=body.primary_goal,
                strict_grounding=True,
            )
            output_ok, reject_reason = await check_output(answer=answer, chunks=chunks)
        except Exception as e:
            logger.error(f"Strict regeneration failed: {e}")
            output_ok = False
    elif not output_ok:
        logger.warning(
            f"Output guardrail rejected qualitative response ({reject_reason}) — skipping retry"
        )

    if not output_ok:
        logger.warning(
            f"Output guardrail rejected after retry ({reject_reason}) — returning safe fallback"
        )
        answer = SAFE_FALLBACK_ANSWER

    # 6. Build sources list
    sources = [
        Source(
            title=c["metadata"].get("source_title", "Thinkbox Research"),
            chunk=c["text"][:200] + "...",
            url=c["metadata"].get("source_url", "https://thinkbox.tv/research"),
            page=c["metadata"].get("page"),
            topic=c["metadata"].get("topic"),
            distance=round(c.get("distance", 0.0), 4),
        )
        for c in chunks
    ]

    # 7. Cache and return (skip cache write for safe fallback — retry should be attempted next time)
    result = {
        "answer": answer,
        "sources": [s.model_dump() for s in sources],
        "model_used": model_used,
    }
    if answer != SAFE_FALLBACK_ANSWER:
        cache.set(
            value=result,
            question=question,
            sector=body.sector,
            brand_stage=body.brand_stage,
            tv_history=body.tv_history,
            primary_goal=body.primary_goal,
            budget_tier=body.budget_tier,
        )

    return QueryResponse(**result, cached=False)


@router.post("/ingest", dependencies=[Depends(verify_api_key)])
async def ingest(request: IngestRequest):
    logger.info(f"Ingest requested for: {request.source_path}")
    try:
        chunks_added = await run_ingest(request.source_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": "Ingestion complete", "chunks_added": chunks_added}
