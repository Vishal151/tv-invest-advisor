import pytest
from unittest.mock import patch, MagicMock
from app.services.guardrails import check_input, check_output


def _mock_completion(decision: str) -> MagicMock:
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = decision
    return mock


@pytest.fixture
def sample_chunks():
    return [
        {
            "text": "TV delivers £5.61 ROI per £1 spent.",
            "metadata": {"source_title": "Profit Ability 2"},
            "distance": 0.1,
        }
    ]


def test_check_input_approved():
    with patch("app.services.guardrails.completion", return_value=_mock_completion("APPROVED")):
        approved, reason = check_input(question="When does TV work for FMCG?")
    assert approved is True


def test_check_input_rejected():
    with patch("app.services.guardrails.completion", return_value=_mock_completion("REJECTED")):
        approved, reason = check_input(question="Write me a poem about dogs")
    assert approved is False


def test_check_input_fails_open_on_error():
    with patch("app.services.guardrails.completion", side_effect=RuntimeError("API down")):
        approved, reason = check_input(question="anything")
    assert approved is True
    assert "GUARDRAIL_ERROR" in reason


def test_check_output_approved(sample_chunks):
    with patch("app.services.guardrails.completion", return_value=_mock_completion("APPROVED")):
        approved, reason = check_output(
            answer="TV delivers £5.61 ROI. Key sources: Profit Ability 2.",
            chunks=sample_chunks,
        )
    assert approved is True


def test_check_output_rejected(sample_chunks):
    with patch("app.services.guardrails.completion", return_value=_mock_completion("REJECTED")):
        approved, reason = check_output(
            answer="TV delivers 99% ROI guaranteed.",
            chunks=sample_chunks,
        )
    assert approved is False


def test_check_output_fails_open_on_error(sample_chunks):
    with patch("app.services.guardrails.completion", side_effect=RuntimeError("API down")):
        approved, reason = check_output(answer="anything", chunks=sample_chunks)
    assert approved is True
