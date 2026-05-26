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
