"""
Retrieval evaluation metrics.

Pure functions over a rank-ordered list of relevance judgements. Each metric
takes ``relevances`` — a list of bools where index 0 is the top-ranked result
and True marks a relevant hit — so the maths is decoupled from ChromaDB, the
gold-label schema, and the matching rule.
"""


def recall_at_k(relevances: list[bool], total_relevant: int, k: int) -> float:
    """Fraction of all relevant items that appear in the top-k results.

    Returns 0.0 when the query has no relevant items (a vacuous query).
    """
    if total_relevant <= 0:
        return 0.0
    hits = sum(1 for r in relevances[:k] if r)
    return hits / total_relevant


def precision_at_k(relevances: list[bool], k: int) -> float:
    """Fraction of the top-k results that are relevant.

    The denominator is k (standard Precision@K), not the number of results
    returned, so under-filling the top-k counts against precision.
    """
    if k <= 0:
        return 0.0
    hits = sum(1 for r in relevances[:k] if r)
    return hits / k


def reciprocal_rank(relevances: list[bool]) -> float:
    """1 / rank of the first relevant result (rank is 1-indexed). 0.0 if none."""
    for rank, relevant in enumerate(relevances, start=1):
        if relevant:
            return 1.0 / rank
    return 0.0


def mean(values: list[float]) -> float:
    """Arithmetic mean; 0.0 for an empty list. Aggregates per-query scores."""
    return sum(values) / len(values) if values else 0.0
