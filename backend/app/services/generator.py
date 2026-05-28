import logging
from litellm import acompletion
from app.core.config import get_settings
from app.models import StructuredAnswer

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

You must respond with a single JSON object matching this exact schema:
{
  "summary": ["paragraph 1", "paragraph 2"],
  "stats": [
    {
      "value": "£5.61",
      "unit": "ROI per £1 spent",
      "context": "Average across 141 brands and 14 categories",
      "source": "Profit Ability 2",
      "page": 12
    }
  ],
  "chart": {
    "title": "Average ROI per £1 · by channel",
    "source": "Profit Ability 2",
    "unit": "£",
    "bars": [
      { "label": "TV", "value": 5.61, "highlight": true },
      { "label": "Digital", "value": 3.21 }
    ]
  },
  "checklist": [
    "Set a minimum 12-month commitment to see compounding brand effect",
    "Allocate at least 60% of budget to TV for maximum base effects"
  ],
  "followups": [
    "How does this change for a DTC brand?",
    "What is the minimum budget to see TV ROI?"
  ]
}

Schema rules:
- "summary": 2–4 paragraphs of prose. Citation superscripts [1], [2] etc. may appear inline.
- "stats": 1–3 key statistics found verbatim in the research context. Order them to match their first mention in summary (stat[0] surfaces after summary[0], stat[1] after summary[1], etc.). Use an empty list if no concrete statistics are available.
- "chart": include ONLY when the answer compares 2+ values across channels, time periods, or categories. Set to null for qualitative answers. Bar values must come from the research context — never invented.
- "checklist": 3–5 concise, actionable bullet points — include ONLY when the question asks for planning guidance, key considerations, a checklist, or how to evaluate an investment. Set to null for factual or ROI comparison questions. Each item should be a practical decision a planner can act on.
- "followups": 2–3 short follow-up questions a planner might naturally ask next. Use an empty list if none relevant.

Rules you must follow:
1. Only cite statistics and findings from the provided research context.
2. Never invent figures, ROI numbers, or study names.
3. Always ground your advice in the specific context provided.
4. Be direct and practical — you are a planner giving real advice.
5. Return only the JSON object — no markdown fences, no preamble.
"""

STRICT_GROUNDING_ADDENDUM = """
Extra rules for this attempt:
- Quote or closely paraphrase only statistics that appear verbatim in the research context.
- If the context does not contain a specific number, do not state one — describe qualitatively instead.
- The JSON schema must still be followed exactly — return the same JSON structure.
"""


def build_prompt(
    question: str,
    chunks: list[dict],
    sector: str | None = None,
    brand_stage: str | None = None,
    budget_tier: str | None = None,
    primary_goal: str | None = None,
    strict_grounding: bool = False,
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
Return only the JSON object — no markdown fences, no preamble, no trailing text."""

    system = SYSTEM_PROMPT + (STRICT_GROUNDING_ADDENDUM if strict_grounding else "")
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_message},
    ]


def _parse_response(raw: str) -> dict:
    """Validate LLM JSON against StructuredAnswer schema. Raises on invalid input."""
    return StructuredAnswer.model_validate_json(raw).model_dump()


async def generate(
    question: str,
    chunks: list[dict],
    sector: str | None = None,
    brand_stage: str | None = None,
    budget_tier: str | None = None,
    primary_goal: str | None = None,
    strict_grounding: bool = False,
) -> tuple[dict, str]:
    """
    Calls LiteLLM with primary model, falls back to secondary on failure.
    Traces to LangFuse if keys are configured.
    Returns (answer_dict, model_used).
    """
    messages = build_prompt(
        question=question,
        chunks=chunks,
        sector=sector,
        brand_stage=brand_stage,
        budget_tier=budget_tier,
        primary_goal=primary_goal,
        strict_grounding=strict_grounding,
    )

    lf = _get_langfuse()
    root_obs = None
    if lf:
        try:
            root_obs = lf.start_observation(
                name="query",
                input={"question": question, "sector": sector},
            )
        except Exception as e:
            logger.warning(f"Langfuse observation start failed: {e}")

    for model in [settings.primary_model, settings.fallback_model]:
        gen_obs = None
        try:
            logger.info(f"Calling LiteLLM with model: {model}")
            if root_obs:
                gen_obs = root_obs.start_observation(
                    name=f"llm-{model}",
                    as_type="generation",
                    model=model,
                )

            call_kwargs = dict(
                model=model,
                messages=messages,
                max_tokens=1500,
                temperature=0.3,
                timeout=60,
            )
            if model == settings.primary_model:
                call_kwargs["response_format"] = {"type": "json_object"}

            response = await acompletion(**call_kwargs)
            raw = response.choices[0].message.content
            answer = _parse_response(raw)
            logger.info(f"Generated response with {model}")

            if gen_obs:
                summary_preview = answer["summary"][0][:200] if answer["summary"] else ""
                gen_obs.update(output={"answer": summary_preview, "model": model})
                gen_obs.end()
            if root_obs:
                root_obs.update(output={"model_used": model})
                root_obs.end()

            return answer, model

        except Exception as e:
            logger.warning(f"Model {model} failed: {e}")
            if gen_obs:
                try:
                    gen_obs.update(output={"error": str(e)}, level="ERROR")
                    gen_obs.end()
                except Exception:
                    logger.debug("Langfuse failed to record model error", exc_info=True)
            if model == settings.fallback_model:
                if root_obs:
                    try:
                        root_obs.update(output={"error": "all models failed"}, level="ERROR")
                        root_obs.end()
                    except Exception:
                        pass
                raise

    raise RuntimeError("All models failed")
