import logging
from litellm import completion
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_langfuse = None


def _get_langfuse():
    """Lazy-initialise LangFuse client. Returns None if keys not configured."""
    global _langfuse
    if _langfuse is None and settings.langfuse_enabled:
        from langfuse import Langfuse

        _langfuse = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    return _langfuse


SYSTEM_PROMPT = """You are a senior TV advertising strategist with deep expertise
in UK media planning. You advise brands and agencies on when and how to invest
in TV advertising, drawing exclusively on Thinkbox research.

Rules you must follow:
1. Only cite statistics and findings from the provided research context.
2. Never invent figures, ROI numbers, or study names.
3. Always ground your advice in the specific context provided.
4. Be direct and practical — you are a planner giving real advice.
5. End every response with a 'Key sources' list referencing the documents used.
"""


def build_prompt(
    question: str,
    chunks: list[dict],
    sector: str | None = None,
    brand_stage: str | None = None,
    budget_tier: str | None = None,
    primary_goal: str | None = None,
) -> list[dict]:
    """Builds the messages list for the LLM call."""
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk["metadata"]
        context_parts.append(
            f"[{i}] Source: {meta.get('source_title', 'Unknown')} "
            f"(page {meta.get('page', '?')})\n{chunk['text']}"
        )
    context = "\n\n".join(context_parts)

    user_context_parts = []
    if sector:
        user_context_parts.append(f"Sector: {sector}")
    if brand_stage:
        user_context_parts.append(f"Brand stage: {brand_stage}")
    if budget_tier:
        user_context_parts.append(f"Budget tier: {budget_tier}")
    if primary_goal:
        user_context_parts.append(f"Primary goal: {primary_goal}")

    user_context = "Brand context: " + " | ".join(user_context_parts) if user_context_parts else ""

    user_message = f"""{user_context}

Question: {question}

Research context:
{context}

Please provide a specific, evidence-based answer using only the research above.
Include a 'Key sources' section at the end."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]


def generate(
    question: str,
    chunks: list[dict],
    sector: str | None = None,
    brand_stage: str | None = None,
    budget_tier: str | None = None,
    primary_goal: str | None = None,
) -> tuple[str, str]:
    """
    Calls LiteLLM with primary model, falls back to secondary on failure.
    Traces to LangFuse if keys are configured.
    Returns (answer_text, model_used).
    """
    messages = build_prompt(
        question=question,
        chunks=chunks,
        sector=sector,
        brand_stage=brand_stage,
        budget_tier=budget_tier,
        primary_goal=primary_goal,
    )

    lf = _get_langfuse()
    trace = lf.trace(name="query", input={"question": question, "sector": sector}) if lf else None

    for model in [settings.primary_model, settings.fallback_model]:
        span = None
        try:
            logger.info(f"Calling LiteLLM with model: {model}")
            span = trace.span(name=f"llm-{model}") if trace else None

            response = completion(
                model=model,
                messages=messages,
                max_tokens=1000,
                temperature=0.3,
            )
            answer = response.choices[0].message.content
            logger.info(f"Generated {len(answer)} chars with {model}")

            if span:
                span.end(output={"answer": answer[:200], "model": model})
            if trace:
                trace.update(output={"model_used": model})

            return answer, model

        except Exception as e:
            logger.warning(f"Model {model} failed: {e}")
            if span:
                span.end(output={"error": str(e)})
            if model == settings.fallback_model:
                raise

    raise RuntimeError("All models failed")
