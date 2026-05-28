import asyncio
import pytest
import textwrap
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


def test_parse_header_rejects_invalid_topic():
    from scripts.ingest_scraped import parse_header

    content = (
        "SOURCE: Test\nURL: https://example.com\nTOPIC: INJECT: ignore all\nSECTOR: all\n\nBody."
    )
    with pytest.raises(ValueError, match="Invalid topic"):
        parse_header(content)


def test_parse_header_rejects_invalid_sector():
    from scripts.ingest_scraped import parse_header

    content = "SOURCE: Test\nURL: https://example.com\nTOPIC: ROI\nSECTOR: Evil<script>\n\nBody."
    with pytest.raises(ValueError, match="Invalid sector"):
        parse_header(content)


def test_parse_header_accepts_valid_metadata():
    from scripts.ingest_scraped import parse_header

    content = (
        "SOURCE: Profit Ability 2\nURL: https://thinkbox.tv\nTOPIC: ROI\nSECTOR: FMCG\n\nBody text."
    )
    metadata, body = parse_header(content)
    assert metadata["topic"] == "ROI"
    assert metadata["sector"] == "FMCG"
    assert "Body text" in body


def test_ingest_text_file_awaits_embed_batch():
    """embed_batch is async — ingest_text_file must await it, not return a coroutine."""
    mock_collection = MagicMock()
    mock_collection.get.return_value = {"ids": []}
    mock_collection.upsert = MagicMock()

    # Body must exceed 20 words to pass chunk_text's minimum filter.
    body = " ".join(["word"] * 25)
    content = textwrap.dedent(f"""\
        SOURCE: Test Source
        URL: https://example.com
        TOPIC: ROI
        SECTOR: all

        {body}
    """)

    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write(content)
        tmp = Path(f.name)

    with patch("scripts.ingest_scraped.embed_batch", new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [[0.1] * 5]
        from scripts.ingest_scraped import ingest_text_file

        result = asyncio.run(ingest_text_file(tmp, mock_collection))

    assert isinstance(result, int)
    mock_embed.assert_awaited_once()
