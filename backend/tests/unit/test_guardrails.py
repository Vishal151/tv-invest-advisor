import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.guardrails import (
    _format_chunks_for_review,
    _parse_guardrail_decision,
    check_input,
    check_output,
)


def _mock_acompletion(decision: str) -> AsyncMock:
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = decision
    async_mock = AsyncMock(return_value=mock_response)
    return async_mock


@pytest.fixture
def sample_chunks():
    return [
        {
            "text": "TV delivers £5.61 ROI per £1 spent.",
            "metadata": {"source_title": "Profit Ability 2"},
            "distance": 0.1,
        }
    ]


async def test_check_input_approved():
    with patch("app.services.guardrails.acompletion", new=_mock_acompletion("APPROVED")):
        approved, reason = await check_input(question="When does TV work for FMCG?")
    assert approved is True


async def test_check_input_rejected():
    with patch("app.services.guardrails.acompletion", new=_mock_acompletion("REJECTED")):
        approved, reason = await check_input(question="Write me a poem about dogs")
    assert approved is False


async def test_check_input_fails_open_on_error():
    with patch(
        "app.services.guardrails.acompletion", new=AsyncMock(side_effect=RuntimeError("API down"))
    ):
        approved, reason = await check_input(question="anything")
    assert approved is True
    assert "GUARDRAIL_ERROR" in reason


async def test_check_output_approved(sample_chunks):
    with patch("app.services.guardrails.acompletion", new=_mock_acompletion("APPROVED")):
        approved, reason = await check_output(
            answer="TV delivers £5.61 ROI. Key sources: Profit Ability 2.",
            chunks=sample_chunks,
        )
    assert approved is True


async def test_check_output_rejected(sample_chunks):
    with patch("app.services.guardrails.acompletion", new=_mock_acompletion("REJECTED")):
        approved, reason = await check_output(
            answer="TV delivers 99% ROI guaranteed.",
            chunks=sample_chunks,
        )
    assert approved is False


def test_format_chunks_for_review_uses_full_text(sample_chunks):
    long_tail = "x" * 500
    sample_chunks[0]["text"] = "ROI headline. " + long_tail
    formatted = _format_chunks_for_review(sample_chunks)
    assert long_tail in formatted
    assert "..." not in formatted  # no truncation marker from old 300-char limit


def test_parse_guardrail_decision():
    assert _parse_guardrail_decision("APPROVED") is True
    assert _parse_guardrail_decision("REJECTED — contains hallucinations") is False
    assert _parse_guardrail_decision("maybe approved?") is True  # ambiguous → fail open


async def test_check_output_fails_open_on_error(sample_chunks):
    with patch(
        "app.services.guardrails.acompletion", new=AsyncMock(side_effect=RuntimeError("API down"))
    ):
        approved, reason = await check_output(answer="anything", chunks=sample_chunks)
    assert approved is True


def test_parse_guardrail_decision_fails_open_on_ambiguous():
    assert _parse_guardrail_decision("Maybe this is fine?") is True
    assert _parse_guardrail_decision("") is True
    assert _parse_guardrail_decision("APPROVED - on topic") is True
    assert _parse_guardrail_decision("REJECTED - off topic") is False
