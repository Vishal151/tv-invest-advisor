import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.generator import build_prompt, generate


@pytest.fixture
def sample_chunks():
    return [
        {
            "text": "TV delivers £5.61 ROI per £1 spent across 141 brands.",
            "metadata": {"source_title": "Profit Ability 2", "page": 12},
            "distance": 0.1,
        }
    ]


def test_build_prompt_includes_question(sample_chunks):
    messages = build_prompt(
        question="Does TV work for FMCG?",
        chunks=sample_chunks,
    )
    user_content = messages[1]["content"]
    assert "Does TV work for FMCG?" in user_content


def test_build_prompt_includes_chunk_text(sample_chunks):
    messages = build_prompt(question="q", chunks=sample_chunks)
    user_content = messages[1]["content"]
    assert "TV delivers £5.61 ROI" in user_content


def test_build_prompt_includes_source_title(sample_chunks):
    messages = build_prompt(question="q", chunks=sample_chunks)
    user_content = messages[1]["content"]
    assert "Profit Ability 2" in user_content


def test_build_prompt_includes_sector_context(sample_chunks):
    messages = build_prompt(question="q", chunks=sample_chunks, sector="FMCG")
    user_content = messages[1]["content"]
    assert "FMCG" in user_content


def test_build_prompt_has_system_message(sample_chunks):
    messages = build_prompt(question="q", chunks=sample_chunks)
    assert messages[0]["role"] == "system"
    assert "Thinkbox" in messages[0]["content"]


def _make_litellm_response(content: str) -> MagicMock:
    """Build a MagicMock that looks like a LiteLLM completion response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content
    return mock_response


def test_generate_is_async():
    """generate() must be a coroutine so it doesn't block the event loop."""
    result = generate(
        question="Does TV work?",
        chunks=[{"text": "TV ROI is high.", "metadata": {"source_title": "PA2", "page": 1}}],
    )
    assert asyncio.iscoroutine(result), "generate() must return a coroutine"
    result.close()  # clean up without running


async def test_generate_returns_answer_and_model(sample_chunks):
    with (
        patch(
            "app.services.generator.acompletion",
            new=AsyncMock(
                return_value=_make_litellm_response(
                    "TV delivers strong ROI. Key sources: Profit Ability 2."
                )
            ),
        ),
        patch("app.services.generator._get_langfuse", return_value=None),
    ):
        answer, model = await generate(question="Does TV work?", chunks=sample_chunks)

    assert "ROI" in answer
    assert model == "gpt-4o"


async def test_generate_falls_back_on_primary_failure(sample_chunks):
    fallback_content = "Based on research, TV works. Key sources: Profit Ability 2."
    call_count = 0

    async def side_effect(**kwargs):
        nonlocal call_count
        call_count += 1
        if "gpt-4o" in kwargs.get("model", ""):
            raise RuntimeError("OpenAI down")
        return _make_litellm_response(fallback_content)

    with (
        patch("app.services.generator.acompletion", side_effect=side_effect),
        patch("app.services.generator._get_langfuse", return_value=None),
    ):
        answer, model = await generate(question="q", chunks=sample_chunks)

    assert answer == fallback_content
    assert model != "gpt-4o"
    assert call_count == 2


async def test_generate_uses_langfuse_v4_observation_api(sample_chunks):
    """Langfuse v4 uses start_observation(), not the removed trace() API."""
    mock_root = MagicMock()
    mock_gen = MagicMock()
    mock_lf = MagicMock()
    mock_lf.start_observation.return_value = mock_root
    mock_root.start_observation.return_value = mock_gen

    with (
        patch(
            "app.services.generator.acompletion",
            new=AsyncMock(
                return_value=_make_litellm_response(
                    "TV delivers strong ROI. Key sources: Profit Ability 2."
                )
            ),
        ),
        patch("app.services.generator._get_langfuse", return_value=mock_lf),
    ):
        await generate(question="Does TV work?", chunks=sample_chunks)

    mock_lf.start_observation.assert_called_once_with(
        name="query",
        input={"question": "Does TV work?", "sector": None},
    )
    mock_root.start_observation.assert_called_once_with(
        name="llm-gpt-4o",
        as_type="generation",
        model="gpt-4o",
    )
    mock_gen.update.assert_called_once()
    mock_gen.end.assert_called_once()
    mock_root.update.assert_called_once()
    mock_root.end.assert_called_once()


async def test_generate_does_not_crash_without_langfuse(sample_chunks):
    """Tracing is a no-op when langfuse_enabled is False — generate() must not crash."""
    with (
        patch(
            "app.services.generator.acompletion",
            new=AsyncMock(
                return_value=_make_litellm_response(
                    "TV works well. Key sources: Profit Ability 2."
                )
            ),
        ),
        patch("app.services.generator._get_langfuse", return_value=None),
    ):
        answer, model = await generate(question="q", chunks=sample_chunks)
        assert "TV works" in answer
