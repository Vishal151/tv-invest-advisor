import pytest


def test_ingest_rejects_path_traversal():
    from app.services.ingestor import run_ingest
    import asyncio

    with pytest.raises(ValueError, match="outside the allowed directory"):
        asyncio.run(run_ingest("../../etc/passwd"))


def test_ingest_rejects_absolute_path_outside_allowed():
    from app.services.ingestor import run_ingest
    import asyncio

    with pytest.raises(ValueError, match="outside the allowed directory"):
        asyncio.run(run_ingest("/etc/passwd"))


def test_ingest_rejects_sibling_directory():
    from app.services.ingestor import run_ingest
    import asyncio

    with pytest.raises(ValueError, match="outside the allowed directory"):
        asyncio.run(run_ingest("../some-other-dir/file.pdf"))


def test_document_registry_is_single_source_of_truth():
    """H2: scripts/ingest.py must use the registry from app.services.ingestor, not a copy."""
    from app.services.ingestor import DOCUMENT_REGISTRY as app_registry
    from scripts.ingest import DOCUMENT_REGISTRY as script_registry

    assert script_registry is app_registry


def test_registry_covers_full_corpus_with_canonical_urls():
    """H2: the unified registry holds all 13 corpus documents with the URLs the
    ingested corpus was actually built with."""
    from app.services.ingestor import DOCUMENT_REGISTRY

    assert len(DOCUMENT_REGISTRY) == 13
    assert DOCUMENT_REGISTRY["profit-ability-2.pdf"]["source_url"].endswith(
        "profit-ability-2-the-new-business-case-for-advertising"
    )


def test_chunk_text_shared_by_all_ingestion_paths():
    """H2: one chunker — both scripts must import chunk_text from app.services.ingestor."""
    from app.services.ingestor import chunk_text
    from scripts.ingest import chunk_text as script_chunk
    from scripts.ingest_scraped import chunk_text as scraped_chunk

    assert script_chunk is chunk_text
    assert scraped_chunk is chunk_text


def test_chunk_text_splits_with_overlap():
    from app.services.ingestor import chunk_text

    text = " ".join(f"w{i}" for i in range(1000))
    chunks = chunk_text(text, chunk_size=800, overlap=100)

    assert len(chunks) == 2
    assert chunks[0].split()[700:] == chunks[1].split()[:100]


def test_chunk_text_drops_tiny_fragments():
    from app.services.ingestor import chunk_text

    assert chunk_text("only five words here now", chunk_size=800, overlap=100) == []


def test_ingest_allowed_dir_is_anchored_to_repo_not_cwd(tmp_path, monkeypatch):
    """A data/pdfs directory under an arbitrary CWD must not become the trust anchor."""
    from app.services.ingestor import run_ingest
    import asyncio

    lookalike = tmp_path / "data" / "pdfs"
    lookalike.mkdir(parents=True)
    (lookalike / "profit-ability-2.pdf").write_bytes(b"%PDF-1.4")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="outside the allowed directory"):
        asyncio.run(run_ingest(str(lookalike / "profit-ability-2.pdf")))


def test_ingest_accepts_repo_data_pdfs_regardless_of_cwd(tmp_path, monkeypatch):
    """The documented dev setup runs uvicorn from backend/ — the repo data/pdfs
    dir must still be the allowed root (FileNotFoundError proves the path check
    passed for a file that does not exist there)."""
    from pathlib import Path
    from app.core.config import get_settings
    from app.services.ingestor import run_ingest
    import asyncio

    monkeypatch.chdir(tmp_path)
    repo_pdfs = Path(get_settings().pdf_dir)
    with pytest.raises(FileNotFoundError):
        asyncio.run(run_ingest(str(repo_pdfs / "no-such-file.pdf")))
