import asyncio
import textwrap
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


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
