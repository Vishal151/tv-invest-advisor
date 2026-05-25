import logging
from litellm import completion
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

Check the following response against these rules:
1. Every statistic must be attributable to the provided source chunks
2. No invented study names, ROI figures, or percentages
3. Response stays on the topic of TV advertising and media planning
4. No harmful or misleading advice

Source chunks used:
{chunks}

Response to review:
{answer}

Respond with ONLY one of:
- APPROVED — response is grounded and accurate
- REJECTED — response contains hallucinations or off-topic content

Decision:"""


def check_input(
    question: str,
    sector: str | None = None,
    brand_stage: str | None = None,
) -> tuple[bool, str]:
    """
    Checks if the query is on-topic before hitting the main LLM.
    Returns (is_approved, reason).
    """
    context_parts = []
    if sector:
        context_parts.append(f"sector={sector}")
    if brand_stage:
        context_parts.append(f"stage={brand_stage}")
    context = ", ".join(context_parts) or "not provided"

    prompt = INPUT_GUARD_PROMPT.format(question=question, context=context)

    try:
        response = completion(
            model=settings.guardrail_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0,
        )
        decision = response.choices[0].message.content.strip().upper()
        approved = decision.startswith("APPROVED")
        logger.info(f"Input guardrail: {decision} for '{question[:50]}...'")
        return approved, decision
    except Exception as e:
        # On guardrail failure, fail open (allow through) and log
        logger.error(f"Input guardrail failed: {e} — failing open")
        return True, "GUARDRAIL_ERROR"


def check_output(
    answer: str,
    chunks: list[dict],
) -> tuple[bool, str]:
    """
    Verifies the generated answer is grounded in the retrieved chunks.
    Returns (is_approved, reason).
    """
    chunks_text = "\n\n".join(
        f"[{i+1}] {c['metadata'].get('source_title', '?')}: {c['text'][:300]}..."
        for i, c in enumerate(chunks)
    )

    prompt = OUTPUT_GUARD_PROMPT.format(
        chunks=chunks_text,
        answer=answer,
    )

    try:
        response = completion(
            model=settings.guardrail_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0,
        )
        decision = response.choices[0].message.content.strip().upper()
        approved = decision.startswith("APPROVED")
        logger.info(f"Output guardrail: {decision}")
        return approved, decision
    except Exception as e:
        # On guardrail failure, fail open and log — don't block valid responses
        logger.error(f"Output guardrail failed: {e} — failing open")
        return True, "GUARDRAIL_ERROR"
