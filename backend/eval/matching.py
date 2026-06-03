"""
Maps retrieved chunks to relevance judgements against a golden question.

Relevance is judged at page granularity: a result is relevant when its
``(source_title, page)`` matches one of the question's relevant targets.
A relevant entry with no ``pages`` (or ``pages: null``) matches on
``source_title`` alone — used for scraped sources whose page numbers are
synthetic. Retrieved chunks are first collapsed to distinct pages so a dense
page split across several chunks counts once, keeping recall bounded by 1.0.
"""


def dedupe_to_pages(chunks: list[dict]) -> list[dict]:
    """Collapse retrieved chunks to distinct (source_title, page) metadata,
    preserving rank order (first occurrence wins)."""
    seen = set()
    pages = []
    for chunk in chunks:
        meta = chunk["metadata"]
        key = (meta.get("source_title"), meta.get("page"))
        if key not in seen:
            seen.add(key)
            pages.append(meta)
    return pages


def target_key(meta: dict, relevant: list[dict]):
    """The gold target a result matches, or None.

    Page-list specs yield ``(spec_index, page)``; title-only specs yield
    ``(spec_index, None)`` so every page of that document maps to one target.
    """
    title = meta.get("source_title")
    page = meta.get("page")
    for idx, spec in enumerate(relevant):
        if spec["source_title"] != title:
            continue
        pages = spec.get("pages")
        if not pages:
            return (idx, None)
        if page in pages:
            return (idx, page)
    return None


def is_relevant(meta: dict, relevant: list[dict]) -> bool:
    """True if a result matches any relevant target (title-or-page)."""
    return target_key(meta, relevant) is not None


def build_relevances(chunks: list[dict], relevant: list[dict]) -> list[bool]:
    """Rank-ordered relevance per distinct retrieved page. Drives precision and MRR
    (every result that answers the question counts)."""
    return [is_relevant(meta, relevant) for meta in dedupe_to_pages(chunks)]


def build_recall_flags(chunks: list[dict], relevant: list[dict]) -> list[bool]:
    """Rank-ordered flags where True marks the first result to hit each distinct
    target. Drives recall, so summing flags counts distinct targets found and stays
    bounded by the total target count even when many pages share one title-only target."""
    seen = set()
    flags = []
    for meta in dedupe_to_pages(chunks):
        key = target_key(meta, relevant)
        if key is not None and key not in seen:
            seen.add(key)
            flags.append(True)
        else:
            flags.append(False)
    return flags


def count_relevant_targets(relevant: list[dict]) -> int:
    """Number of distinct gold targets. A title-only spec counts as one."""
    total = 0
    for spec in relevant:
        pages = spec.get("pages")
        total += len(pages) if pages else 1
    return total
