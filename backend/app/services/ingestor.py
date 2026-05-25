import hashlib
import logging
from pathlib import Path

from app.core.config import get_settings
from app.services.embedder import embed_batch
from app.services.retriever import get_collection

logger = logging.getLogger(__name__)
settings = get_settings()

DOCUMENT_REGISTRY: dict[str, dict] = {
    "profit-ability-2.pdf": {
        "source_title": "Profit Ability 2",
        "source_url": "https://www.thinkbox.tv/research/thinkbox-research/profit-ability-2-the-business-case-for-advertising",
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


def _extract_pages(pdf_path: Path) -> list[tuple[str, int]]:
    """Returns [(page_text, page_number), ...] skipping empty pages."""
    from pypdf import PdfReader
    reader = PdfReader(str(pdf_path))
    pages = []
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text()
        if text and text.strip():
            pages.append((text.strip(), i))
    return pages


def _chunk_text(text: str, page_number: int) -> list[dict]:
    """Splits text into overlapping word-based chunks."""
    words = text.split()
    chunks = []
    start = 0
    chunk_size = settings.chunk_size
    overlap = settings.chunk_overlap

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        if len(chunk_words) > 20:
            chunks.append({
                "text": " ".join(chunk_words),
                "page": page_number,
            })
        start += chunk_size - overlap

    return chunks


def run_ingest(source_path: str) -> int:
    """
    Ingests a single PDF at source_path into ChromaDB.
    Returns the number of chunks added.
    Raises FileNotFoundError for missing files, ValueError for unknown documents.
    """
    pdf_path = Path(source_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {source_path}")

    doc_metadata = DOCUMENT_REGISTRY.get(pdf_path.name)
    if doc_metadata is None:
        raise ValueError(
            f"'{pdf_path.name}' not in DOCUMENT_REGISTRY. "
            "Add it to app/services/ingestor.py to ingest it."
        )

    pages = _extract_pages(pdf_path)
    if not pages:
        logger.warning(f"No text extracted from {pdf_path.name}")
        return 0

    all_chunks = []
    for page_text, page_num in pages:
        all_chunks.extend(_chunk_text(page_text, page_num))

    if not all_chunks:
        return 0

    collection = get_collection()
    total_added = 0
    batch_size = 50

    for batch_start in range(0, len(all_chunks), batch_size):
        batch = all_chunks[batch_start: batch_start + batch_size]
        embeddings = embed_batch([c["text"] for c in batch])
        ids, documents, metadatas = [], [], []

        for i, (chunk, _) in enumerate(zip(batch, embeddings)):
            chunk_index = batch_start + i
            chunk_id = hashlib.sha256(
                f"{doc_metadata['source_title']}_{chunk['page']}_{chunk_index}".encode()
            ).hexdigest()[:16]
            ids.append(chunk_id)
            documents.append(chunk["text"])
            metadatas.append({**doc_metadata, "page": chunk["page"], "chunk_index": chunk_index})

        collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        total_added += len(batch)

    logger.info(f"Ingested {total_added} chunks from {pdf_path.name}")
    return total_added
