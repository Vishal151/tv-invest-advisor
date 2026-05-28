import pytest
from unittest.mock import patch
from app.services.generator import generate
from app.services.guardrails import check_input, check_output
from app.services.retriever import retrieve
from app.core.config import get_settings


@pytest.fixture(autouse=True)
def enable_mock_mode(monkeypatch):
    monkeypatch.setattr(get_settings(), "llm_mock", True)
    yield
    monkeypatch.setattr(get_settings(), "llm_mock", False)


@pytest.fixture
def sample_chunks():
    return [
        {
            "text": "TV advertising delivered an average ROI of £5.61 for every £1 spent.",
            "metadata": {
                "source_title": "Profit Ability 2",
                "source_url": "https://www.thinkbox.tv/research",
                "topic": "ROI",
                "sector": "all",
                "page": 12,
                "chunk_index": 1,
            },
            "distance": 0.1,
        }
    ]


async def test_generate_returns_mock_response(sample_chunks):
    answer, model = await generate(question="Does TV work?", chunks=sample_chunks)
    assert model == "mock"
    assert isinstance(answer["summary"], list)
    assert len(answer["summary"]) > 0


async def test_generate_mock_does_not_call_litellm(sample_chunks):
    with patch("app.services.generator.acompletion") as mock_llm:
        await generate(question="Does TV work?", chunks=sample_chunks)
    mock_llm.assert_not_called()


async def test_check_input_approves_in_mock_mode():
    approved, reason = await check_input(question="anything goes in mock mode")
    assert approved is True


async def test_check_input_mock_does_not_call_litellm():
    with patch("app.services.guardrails.acompletion") as mock_llm:
        await check_input(question="test")
    mock_llm.assert_not_called()


async def test_check_output_approves_in_mock_mode(sample_chunks):
    approved, reason = await check_output(answer="any answer", chunks=sample_chunks)
    assert approved is True


async def test_retrieve_returns_mock_chunks():
    chunks = await retrieve(question="Does TV work?")
    assert len(chunks) > 0
    assert "text" in chunks[0]
    assert "metadata" in chunks[0]


async def test_retrieve_mock_does_not_call_embedder():
    with patch("app.services.embedder.embed") as mock_embed:
        await retrieve(question="test")
    mock_embed.assert_not_called()
