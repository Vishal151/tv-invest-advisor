import hashlib
import logging
from pathlib import Path

from app.core.config import get_settings
from app.services.retriever import get_collection

logger = logging.getLogger(__name__)
settings = get_settings()

# Single source of truth for corpus metadata — scripts/ingest.py imports this.
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
    "TB_FromGoodToGreat_Whitepaper.pdf": {
        "source_title": "From Good to Great: Improving the Odds",
        "source_url": "https://www.thinkbox.tv/research/reports/from-good-to-great-improving-the-odds",
        "topic": "creative",
        "sector": "all",
    },
    "The_Value_Of_TV_Report_Richard_Shotton_and_Thinkbox_2024.pdf": {
        "source_title": "The Value of TV: A Behavioural Science Perspective",
        "source_url": "https://www.thinkbox.tv/research/reports/the-value-of-tv-a-behavioural-science-perspective",
        "topic": "effectiveness",
        "sector": "all",
    },
    "Giving_attention_a_little_attention.pdf": {
        "source_title": "Giving Attention a Little Attention",
        "source_url": "https://www.thinkbox.tv/research/reports/giving-attention-a-little-attention-download-the-white-paper",
        "topic": "creative",
        "sector": "all",
    },
    "Effectiveness_In_Context.pdf": {
        "source_title": "Effectiveness in Context",
        "source_url": "https://www.thinkbox.tv/research/reports/effectiveness-in-context-free-download",
        "topic": "effectiveness",
        "sector": "all",
    },
    "Media_in_focus_marketing_effectiveness_in_the_digital_era.pdf": {
        "source_title": "Media in Focus: Marketing Effectiveness in the Digital Era",
        "source_url": "https://www.thinkbox.tv/research/reports/media-in-focus-free-download",
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


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Splits text into overlapping word-based chunks, dropping fragments of
    20 words or fewer. Shared by all ingestion paths."""
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        chunk_words = words[start : start + chunk_size]
        if len(chunk_words) > 20:
            chunks.append(" ".join(chunk_words))
        start += chunk_size - overlap

    return chunks


async def run_ingest(source_path: str) -> int:
    """
    Ingests a single PDF at source_path into ChromaDB.
    Returns the number of chunks added.
    Raises FileNotFoundError for missing files, ValueError for unknown documents.
    """
    from app.services.embedder import embed_batch

    pdf_path = Path(source_path).resolve()
    allowed_dir = Path("data/pdfs").resolve()

    if not str(pdf_path).startswith(str(allowed_dir) + "/") and pdf_path != allowed_dir:
        raise ValueError(
            f"source_path '{source_path}' is outside the allowed directory 'data/pdfs'"
        )

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
        for text in chunk_text(page_text, settings.chunk_size, settings.chunk_overlap):
            all_chunks.append({"text": text, "page": page_num})

    if not all_chunks:
        return 0

    collection = get_collection()
    total_added = 0
    batch_size = 50

    for batch_start in range(0, len(all_chunks), batch_size):
        batch = all_chunks[batch_start : batch_start + batch_size]
        embeddings = await embed_batch([c["text"] for c in batch])
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
