"""
Offline ingestion pipeline.

Usage:
    cd backend
    uv run scripts/ingest.py                         # ingest all PDFs in data/pdfs/
    uv run scripts/ingest.py --file profit-ability-2.pdf  # single file

Reads PDFs from ../../data/pdfs/ relative to backend root.
Stores chunks in ChromaDB at ./chroma_db/
"""

# SQLite fix must be first
__import__("pysqlite3")
import sys
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

import argparse
import hashlib
import logging
import os
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from pypdf import PdfReader

# Allow imports from app/
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.services.embedder import embed_batch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()

# ── Document registry ─────────────────────────────────────────────────────────
# Maps filename → metadata for the Thinkbox corpus.
# Add new documents here when expanding the corpus.

DOCUMENT_REGISTRY: dict[str, dict] = {
    "profit-ability-2.pdf": {
        "source_title": "Profit Ability 2",
        "source_url": "https://www.thinkbox.tv/research/thinkbox-research/profit-ability-2-the-new-business-case-for-advertising",
        "topic": "ROI",
        "sector": "all",
    },
    "profit-ability-1.pdf": {
        "source_title": "Profit Ability 1",
        "source_url": "https://www.thinkbox.tv/research/thinkbox-research/profit-ability-the-business-case-for-advertising",
        "topic": "ROI",
        "sector": "all",
    },
    "as-seen-on-tv.pdf": {
        "source_title": "As Seen on TV: Supercharging Small Business",
        "source_url": "https://www.thinkbox.tv/research/thinkbox-research/as-seen-on-tv-supercharging-your-small-business",
        "topic": "small_business",
        "sector": "all",
    },
    "peter-field-white-paper.pdf": {
        "source_title": "TV is at the Heart of Effectiveness",
        "source_url": "https://www.thinkbox.tv/research/reports/tv-is-at-the-heart-of-effectiveness-whitepaper-by-peter-field",
        "topic": "effectiveness",
        "sector": "all",
    },
    "payback-4.pdf": {
        "source_title": "Payback 4: Pathways to Profit",
        "source_url": "https://www.thinkbox.tv/research/thinkbox-research/payback-4",
        "topic": "ROI",
        "sector": "all",
    },
    "tv-viewing-report-2024.pdf": {
        "source_title": "TV Viewing Report 2024",
        "source_url": "https://www.thinkbox.tv/research/nickable-charts/viewing-and-audiences/tv-viewing-report",
        "topic": "viewing",
        "sector": "all",
    },
    "signalling-success.pdf": {
        "source_title": "Signalling Success",
        "source_url": "https://www.thinkbox.tv/research/thinkbox-research/signalling-success",
        "topic": "effectiveness",
        "sector": "all",
    },
    "demand-generator.pdf": {
        "source_title": "Demand Generator",
        "source_url": "https://www.thinkbox.tv/research/thinkbox-research/demand-generation",
        "topic": "planning",
        "sector": "all",
    },
}


# ── PDF extraction ────────────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: Path) -> list[tuple[str, int]]:
    """
    Extracts text from a PDF, page by page.
    Returns list of (page_text, page_number) tuples.
    Skips empty pages.
    """
    reader = PdfReader(str(pdf_path))
    pages = []
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text()
        if text and text.strip():
            pages.append((text.strip(), i))
    logger.info(f"Extracted {len(pages)} pages from {pdf_path.name}")
    return pages


# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_text(
    text: str,
    page_number: int,
    chunk_size: int = 800,
    overlap: int = 100,
) -> list[dict]:
    """
    Splits text into overlapping word-based chunks.
    Returns list of dicts with text and positional info.
    """
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)

        if len(chunk_words) > 20:  # skip very short chunks
            chunks.append({
                "text": chunk_text,
                "page": page_number,
                "word_start": start,
                "word_end": end,
            })

        start += chunk_size - overlap

    return chunks


# ── Ingestion ─────────────────────────────────────────────────────────────────

def ingest_document(
    pdf_path: Path,
    collection: chromadb.Collection,
    doc_metadata: dict,
) -> int:
    """
    Ingests a single PDF into ChromaDB.
    Returns the number of chunks added.
    """
    logger.info(f"Ingesting: {pdf_path.name}")

    # Extract text
    pages = extract_text_from_pdf(pdf_path)
    if not pages:
        logger.warning(f"No text extracted from {pdf_path.name} — skipping")
        return 0

    # Chunk all pages
    all_chunks = []
    for page_text, page_num in pages:
        chunks = chunk_text(
            page_text,
            page_number=page_num,
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap,
        )
        all_chunks.extend(chunks)

    if not all_chunks:
        logger.warning(f"No chunks produced for {pdf_path.name} — skipping")
        return 0

    logger.info(f"Produced {len(all_chunks)} chunks — embedding...")

    # Embed in batches of 50 (API limit friendly)
    batch_size = 50
    total_added = 0

    for batch_start in range(0, len(all_chunks), batch_size):
        batch = all_chunks[batch_start: batch_start + batch_size]
        texts = [c["text"] for c in batch]

        embeddings = embed_batch(texts)

        ids = []
        metadatas = []
        documents = []

        for i, (chunk, embedding) in enumerate(zip(batch, embeddings)):
            chunk_index = batch_start + i

            # Deterministic ID — prevents duplicates on re-run
            chunk_id = hashlib.sha256(
                f"{doc_metadata['source_title']}_{chunk['page']}_{chunk_index}".encode()
            ).hexdigest()[:16]

            ids.append(chunk_id)
            documents.append(chunk["text"])
            metadatas.append({
                **doc_metadata,
                "page": chunk["page"],
                "chunk_index": chunk_index,
            })

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        total_added += len(batch)
        logger.info(
            f"  Batch {batch_start // batch_size + 1}: "
            f"{total_added}/{len(all_chunks)} chunks stored"
        )

    logger.info(f"✓ {pdf_path.name} — {total_added} chunks ingested")
    return total_added


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ingest Thinkbox PDFs into ChromaDB")
    parser.add_argument(
        "--file",
        type=str,
        help="Ingest a single file by name (e.g. profit-ability-2.pdf)",
        default=None,
    )
    args = parser.parse_args()

    # Paths
    backend_dir = Path(__file__).parent.parent
    data_dir = backend_dir.parent / "data" / "pdfs"

    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        logger.error("Create it and add Thinkbox PDFs: mkdir -p data/pdfs")
        sys.exit(1)

    # Connect to ChromaDB
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

    # Determine which files to ingest
    if args.file:
        files = [data_dir / args.file]
        if not files[0].exists():
            logger.error(f"File not found: {files[0]}")
            sys.exit(1)
    else:
        files = sorted(data_dir.glob("*.pdf"))
        if not files:
            logger.error(f"No PDFs found in {data_dir}")
            logger.error("Download Thinkbox research PDFs and place them there.")
            sys.exit(1)

    # Ingest
    total_chunks = 0
    for pdf_path in files:
        filename = pdf_path.name
        doc_metadata = DOCUMENT_REGISTRY.get(filename)

        if doc_metadata is None:
            logger.warning(
                f"'{filename}' not in DOCUMENT_REGISTRY — skipping. "
                f"Add it to the registry in scripts/ingest.py"
            )
            continue

        chunks_added = ingest_document(pdf_path, collection, doc_metadata)
        total_chunks += chunks_added

    logger.info(f"\n✓ Ingestion complete — {total_chunks} total chunks added")
    logger.info(f"✓ Collection now has {collection.count()} chunks")


if __name__ == "__main__":
    main()