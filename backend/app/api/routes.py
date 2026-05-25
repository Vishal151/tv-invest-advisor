import logging
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, Field
from typing import Optional

from app.core.config import get_settings
from app.services.cache import cache
from app.services.retriever import retrieve, get_doc_count
from app.services.generator import generate
from app.services.guardrails import check_input, check_output

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


# ── Request / Response models ─────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=500)
    sector: Optional[str] = None
    brand_stage: Optional[str] = None
    tv_history: Optional[str] = None
    primary_goal: Optional[str] = None
    budget_tier: Optional[str] = None


class Source(BaseModel):
    title: str
    chunk: str
    url: str


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


# ── Auth dependency ───────────────────────────────────────────────────────────

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        chroma_docs=get_doc_count(),
        version=settings.version,
    )


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    # Validate enum inputs
    if request.sector and request.sector not in settings.valid_sectors:
        raise HTTPException(status_code=422, detail=f"Invalid sector: {request.sector}")
    if request.brand_stage and request.brand_stage not in settings.valid_brand_stages:
        raise HTTPException(status_code=422, detail=f"Invalid brand_stage")
    if request.budget_tier and request.budget_tier not in settings.valid_budget_tiers:
        raise HTTPException(status_code=422, detail=f"Invalid budget_tier")

    # 1. Cache lookup
    cached = cache.get(
        question=request.question,
        sector=request.sector,
        brand_stage=request.brand_stage,
        tv_history=request.tv_history,
        primary_goal=request.primary_goal,
        budget_tier=request.budget_tier,
    )
    if cached:
        return QueryResponse(**cached, cached=True)

    # 2. Input guardrail
    approved, reason = check_input(
        question=request.question,
        sector=request.sector,
        brand_stage=request.brand_stage,
    )
    if not approved:
        raise HTTPException(
            status_code=400,
            detail="Query is outside the scope of this tool. "
                   "Please ask about TV advertising, media planning, or brand growth.",
        )

    # 3. Retrieve relevant chunks
    chunks = retrieve(
        question=request.question,
        sector=request.sector,
        brand_stage=request.brand_stage,
    )
    if not chunks:
        raise HTTPException(
            status_code=503,
            detail="No research documents found. "
                   "Please ensure the corpus has been ingested.",
        )

    # 4. Generate answer via LiteLLM
    answer, model_used = generate(
        question=request.question,
        chunks=chunks,
        sector=request.sector,
        brand_stage=request.brand_stage,
        budget_tier=request.budget_tier,
        primary_goal=request.primary_goal,
    )

    # 5. Output guardrail
    output_ok, _ = check_output(answer=answer, chunks=chunks)
    if not output_ok:
        logger.warning("Output guardrail rejected response — returning safe fallback")
        answer = (
            "Based on Thinkbox research, TV advertising is consistently shown "
            "to be the most effective channel for driving long-term profit growth. "
            "Please refine your question for a more specific answer."
        )

    # 6. Build sources list
    sources = [
        Source(
            title=c["metadata"].get("source_title", "Thinkbox Research"),
            chunk=c["text"][:200] + "...",
            url=c["metadata"].get("source_url", "https://thinkbox.tv/research"),
        )
        for c in chunks
    ]

    # 7. Cache and return
    result = {
        "answer": answer,
        "sources": [s.model_dump() for s in sources],
        "model_used": model_used,
    }
    cache.set(
        value=result,
        question=request.question,
        sector=request.sector,
        brand_stage=request.brand_stage,
        tv_history=request.tv_history,
        primary_goal=request.primary_goal,
        budget_tier=request.budget_tier,
    )

    return QueryResponse(**result, cached=False)


@router.post("/ingest", dependencies=[Depends(verify_api_key)])
async def ingest(request: IngestRequest):
    logger.info(f"Ingest requested for: {request.source_path}")
    return {"message": "Ingest endpoint ready — pipeline coming next."}