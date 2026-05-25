import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


@pytest.fixture
def mock_settings(monkeypatch):
    """Override settings so tests never need real env vars."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.setenv("API_KEY", "test-api-key")


@pytest.fixture
def sample_chunks() -> list[dict]:
    """Realistic chunk data matching ChromaDB retrieval output."""
    return [
        {
            "text": "TV advertising delivered an average ROI of £5.61 for every £1 spent, "
            "based on analysis of 141 brands across 14 categories.",
            "metadata": {
                "source_title": "Profit Ability 2",
                "source_url": "https://www.thinkbox.tv/research/thinkbox-research/profit-ability-2",
                "topic": "ROI",
                "sector": "all",
                "page": 12,
                "chunk_index": 3,
            },
            "distance": 0.12,
        },
        {
            "text": "Brands that invest in TV consistently outperform those that do not "
            "on measures of brand fame, trust, and mental availability.",
            "metadata": {
                "source_title": "TV is at the Heart of Effectiveness",
                "source_url": "https://www.thinkbox.tv/research/reports/tv-is-at-the-heart-of-effectiveness-whitepaper-by-peter-field",
                "topic": "effectiveness",
                "sector": "all",
                "page": 8,
                "chunk_index": 14,
            },
            "distance": 0.18,
        },
    ]


@pytest.fixture
def mock_retrieve(sample_chunks):
    """Patches retriever.retrieve to return sample_chunks."""
    with patch("app.services.retriever.retrieve", return_value=sample_chunks) as m:
        yield m


@pytest.fixture
def mock_generate():
    """Patches generator.generate to return a realistic answer."""
    answer = (
        "Based on Thinkbox research (Profit Ability 2), TV advertising delivers "
        "an average ROI of £5.61 per £1 spent. Key sources: Profit Ability 2."
    )
    with patch("app.services.generator.generate", return_value=(answer, "gpt-4o")) as m:
        yield m


@pytest.fixture
def mock_check_input():
    """Patches guardrails.check_input to approve all queries."""
    with patch("app.services.guardrails.check_input", return_value=(True, "APPROVED")) as m:
        yield m


@pytest.fixture
def mock_check_output():
    """Patches guardrails.check_output to approve all outputs."""
    with patch("app.services.guardrails.check_output", return_value=(True, "APPROVED")) as m:
        yield m


@pytest.fixture
def mock_doc_count():
    """Patches retriever.get_doc_count to return a realistic count."""
    with patch("app.services.retriever.get_doc_count", return_value=142) as m:
        yield m


@pytest.fixture
def test_client(mock_doc_count):
    """Returns a TestClient with all external services mocked at import time."""
    with patch("app.services.retriever.get_collection"):
        from app.main import app

        return TestClient(app)
