"""
Ingest scraped research text files into ChromaDB.

Usage:
    cd backend
    uv run scripts/ingest_scraped.py

Reads .txt files from ../../data/scraped/ relative to backend root.
Each file must begin with SOURCE:, URL:, TOPIC:, SECTOR: header lines.
"""

# SQLite fix must be first
__import__("pysqlite3")
import sys  # noqa: E402

sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

import asyncio  # noqa: E402
import hashlib  # noqa: E402
import logging  # noqa: E402
from pathlib import Path  # noqa: E402

import chromadb  # noqa: E402
from chromadb.config import Settings as ChromaSettings  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings  # noqa: E402
from app.services.embedder import embed_batch  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()


def parse_header(text: str) -> tuple[dict, str]:
    """
    Parses SOURCE/URL/TOPIC/SECTOR header lines from the top of a text file.
    Returns (metadata_dict, body_text).
    """
    lines = text.strip().splitlines()
    metadata = {}
    body_start = 0

    for i, line in enumerate(lines):
        if line.startswith("SOURCE:"):
            metadata["source_title"] = line[len("SOURCE:") :].strip()
        elif line.startswith("URL:"):
            metadata["source_url"] = line[len("URL:") :].strip()
        elif line.startswith("PUBLISHED:"):
            pass  # informational only
        elif line.startswith("TOPIC:"):
            metadata["topic"] = line[len("TOPIC:") :].strip()
        elif line.startswith("SECTOR:"):
            metadata["sector"] = line[len("SECTOR:") :].strip()
        elif line.strip() == "" and i > 0 and metadata:
            body_start = i + 1
            break

    body = "\n".join(lines[body_start:]).strip()
    return metadata, body


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        if len(chunk_words) > 20:
            chunks.append(" ".join(chunk_words))
        start += chunk_size - overlap
    return chunks


async def ingest_text_file(
    txt_path: Path,
    collection: chromadb.Collection,
) -> int:
    """Ingests a single .txt research file. Returns chunks added."""
    logger.info(f"Ingesting: {txt_path.name}")
    text = txt_path.read_text(encoding="utf-8")
    metadata, body = parse_header(text)

    if not metadata.get("source_title"):
        logger.warning(f"No SOURCE: header in {txt_path.name} — skipping")
        return 0

    chunks = chunk_text(body, chunk_size=settings.chunk_size, overlap=settings.chunk_overlap)
    if not chunks:
        logger.warning(f"No chunks from {txt_path.name}")
        return 0

    logger.info(f"Produced {len(chunks)} chunks — embedding...")

    batch_size = 50
    total_added = 0

    for batch_start in range(0, len(chunks), batch_size):
        batch = chunks[batch_start : batch_start + batch_size]

        # Build IDs first to check what already exists
        ids = [
            hashlib.sha256(
                f"{metadata['source_title']}_scraped_{batch_start + i}".encode()
            ).hexdigest()[:16]
            for i in range(len(batch))
        ]

        existing = collection.get(ids=ids, include=[])["ids"]
        new_indices = [i for i, cid in enumerate(ids) if cid not in existing]

        if not new_indices:
            logger.info("  Already ingested — skipping")
            total_added += len(batch)
            continue

        new_chunks = [batch[i] for i in new_indices]
        new_ids = [ids[i] for i in new_indices]
        embeddings = await embed_batch(new_chunks)

        documents, metadatas = [], []
        for i, (chunk, _) in enumerate(zip(new_chunks, embeddings)):
            chunk_index = batch_start + new_indices[i]
            documents.append(chunk)
            metadatas.append({**metadata, "page": chunk_index + 1, "chunk_index": chunk_index})

        collection.upsert(
            ids=new_ids, embeddings=embeddings, documents=documents, metadatas=metadatas
        )
        total_added += len(batch)

    logger.info(f"  {txt_path.name} — {total_added} chunks ingested")
    return total_added


def delete_source_chunks(collection: chromadb.Collection, source_title: str) -> int:
    """Delete all chunks for a given source_title. Returns count deleted."""
    results = collection.get(where={"source_title": source_title}, include=[])
    ids = results["ids"]
    if ids:
        collection.delete(ids=ids)
        logger.info(f"  Deleted {len(ids)} existing chunks for '{source_title}'")
    return len(ids)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Ingest scraped research text files into ChromaDB."
    )
    parser.add_argument("--force", action="store_true", help="Delete and re-ingest all sources.")
    args = parser.parse_args()

    backend_dir = Path(__file__).parent.parent
    data_dir = backend_dir.parent / "data" / "scraped"

    if not data_dir.exists():
        logger.error(f"Scraped data directory not found: {data_dir}")
        sys.exit(1)

    client = chromadb.PersistentClient(
        path=str(backend_dir / settings.chroma_db_path.lstrip("./")),
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(
        name=settings.chroma_collection,
        metadata={"hnsw:space": "cosine"},
    )

    logger.info(f"ChromaDB collection: {settings.chroma_collection}")
    logger.info(f"Existing docs: {collection.count()}")

    txt_files = sorted(data_dir.glob("*.txt"))
    if not txt_files:
        logger.error(f"No .txt files found in {data_dir}")
        sys.exit(1)

    if args.force:
        logger.info("--force: deleting existing scraped chunks before re-ingesting")
        for txt_path in txt_files:
            text = txt_path.read_text(encoding="utf-8")
            metadata, _ = parse_header(text)
            if metadata.get("source_title"):
                delete_source_chunks(collection, metadata["source_title"])

    total_chunks = 0
    for txt_path in txt_files:
        total_chunks += asyncio.run(ingest_text_file(txt_path, collection))

    logger.info(f"\nIngestion complete — {total_chunks} chunks added")
    logger.info(f"Collection now has {collection.count()} chunks")


if __name__ == "__main__":
    main()
