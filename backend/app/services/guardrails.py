import logging
from litellm import acompletion
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

INPUT_GUARD_PROMPT = """You are a query classifier for a TV advertising research tool.

Your job: decide if the user's query is relevant to TV advertising, media planning,
brand building, marketing effectiveness, or advertising ROI.

Respond with ONLY one of:
- APPROVED — query is on-topic, proceed
- REJECTED — query is off-topic or inappropriate

Query: {question}
Brand context: {context}

Decision:"""

OUTPUT_GUARD_PROMPT = """You are a quality reviewer for a TV advertising advisory tool.

Source chunks (full text shown to the answer model):
{chunks}

Response to review:
{answer}

Approve unless the response clearly violates a rule below.

APPROVE when:
- Advice and themes match the sources (paraphrasing and synthesis are fine)
- Specific numbers (£, %, ROI, campaign counts, timeframes) in the response appear in the sources
- Qualitative planning guidance is grounded in the sources without inventing new statistics

REJECT only when:
- The response states a specific statistic or study name that does not appear in the sources above
- The response is off-topic (not about TV advertising / media planning)
- The response gives harmful or clearly misleading advice

Do not reject for: missing citations, general tone, or cautious recommendations.

Respond with ONLY one line starting with APPROVED or REJECTED.

Decision:"""


def _format_chunks_for_review(chunks: list[dict]) -> str:
    """Same chunk text the generator sees — avoid false rejects from truncation."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk["metadata"]
        parts.append(
            f"[{i}] Source: {meta.get('source_title', '?')} "
            f"(page {meta.get('page', '?')})\n{chunk['text']}"
        )
    return "\n\n".join(parts)


def _parse_guardrail_decision(raw: str) -> bool:
    """True if approved. Expects model to lead with APPROVED or REJECTED."""
    decision = raw.strip().upper()
    if decision.startswith("APPROVED"):
        return True
    if decision.startswith("REJECTED"):
        return False
    # Ambiguous — fail open so valid answers are not replaced by the generic fallback
    logger.warning(f"Ambiguous guardrail decision: {raw!r} — failing open")
    return True


async def check_input(
    question: str,
    sector: str | None = None,
    brand_stage: str | None = None,
) -> tuple[bool, str]:
    """
    Checks if the query is on-topic before hitting the main LLM.
    Returns (is_approved, reason).
    """
    if settings.llm_mock:
        return True, "APPROVED"

    context_parts = []
    if sector:
        context_parts.append(f"sector={sector}")
    if brand_stage:
        context_parts.append(f"stage={brand_stage}")
    context = ", ".join(context_parts) or "not provided"

    prompt = INPUT_GUARD_PROMPT.format(question=question, context=context)

    try:
        response = await acompletion(
            model=settings.guardrail_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0,
            timeout=15,
        )
        raw = response.choices[0].message.content.strip()
        approved = _parse_guardrail_decision(raw)
        logger.info(f"Input guardrail: {raw.upper()} for '{question[:50]}...'")
        return approved, raw
    except Exception as e:
        # On guardrail failure, fail open (allow through) and log
        logger.error(f"Input guardrail failed: {e} — failing open")
        return True, "GUARDRAIL_ERROR"


async def check_output(
    answer: str,
    chunks: list[dict],
) -> tuple[bool, str]:
    """
    Verifies the generated answer is grounded in the retrieved chunks.
    Returns (is_approved, reason).
    """
    if settings.llm_mock:
        return True, "APPROVED"

    prompt = OUTPUT_GUARD_PROMPT.format(
        chunks=_format_chunks_for_review(chunks),
        answer=answer,
    )

    try:
        response = await acompletion(
            model=settings.guardrail_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0,
            timeout=30,
        )
        raw = response.choices[0].message.content.strip()
        approved = _parse_guardrail_decision(raw)
        logger.info(f"Output guardrail: {raw.upper()}")
        return approved, raw
    except Exception as e:
        # On guardrail failure, fail open and log — don't block valid responses
        logger.error(f"Output guardrail failed: {e} — failing open")
        return True, "GUARDRAIL_ERROR"
