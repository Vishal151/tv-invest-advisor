"""Unit tests for the retrieval evaluation metrics and matching rule.

Pure math and dict matching — no corpus, LLM, or async involved.
"""

from eval.matching import (
    build_recall_flags,
    build_relevances,
    count_relevant_targets,
    dedupe_to_pages,
    is_relevant,
)
from eval.metrics import mean, precision_at_k, recall_at_k, reciprocal_rank

# ── recall_at_k ─────────────────────────────────────────────────────────────


def test_recall_all_relevant_in_topk():
    assert recall_at_k([True, True], total_relevant=2, k=5) == 1.0


def test_recall_none_relevant():
    assert recall_at_k([False, False, False], total_relevant=2, k=5) == 0.0


def test_recall_partial():
    assert recall_at_k([True, False, True, False], total_relevant=4, k=5) == 0.5


def test_recall_zero_total_is_vacuous():
    assert recall_at_k([True], total_relevant=0, k=5) == 0.0


def test_recall_respects_k_cutoff():
    # Relevant hit sits at rank 4, outside k=3.
    assert recall_at_k([False, False, False, True], total_relevant=1, k=3) == 0.0


# ── precision_at_k ──────────────────────────────────────────────────────────


def test_precision_all_relevant():
    assert precision_at_k([True, True, True], k=3) == 1.0


def test_precision_alternating():
    assert precision_at_k([True, False, True, False], k=4) == 0.5


def test_precision_denominator_is_k_when_underfilled():
    # Only one result, both relevant, but k=3 -> denominator stays 3.
    assert precision_at_k([True], k=3) == 1 / 3


def test_precision_zero_k():
    assert precision_at_k([True], k=0) == 0.0


# ── reciprocal_rank ─────────────────────────────────────────────────────────


def test_rr_first_relevant():
    assert reciprocal_rank([True, False]) == 1.0


def test_rr_second_relevant():
    assert reciprocal_rank([False, True]) == 0.5


def test_rr_third_relevant():
    assert reciprocal_rank([False, False, True]) == 1 / 3


def test_rr_none_relevant():
    assert reciprocal_rank([False, False]) == 0.0


def test_rr_empty():
    assert reciprocal_rank([]) == 0.0


# ── mean ────────────────────────────────────────────────────────────────────


def test_mean_normal():
    assert mean([1.0, 0.0, 0.5]) == 0.5


def test_mean_single():
    assert mean([0.25]) == 0.25


def test_mean_empty():
    assert mean([]) == 0.0


# ── matching rule (title-or-page) ────────────────────────────────────────────


def _chunk(title, page):
    return {"metadata": {"source_title": title, "page": page}}


def test_match_on_page():
    relevant = [{"source_title": "Profit Ability 2", "pages": [12, 13]}]
    assert is_relevant(_chunk("Profit Ability 2", 12)["metadata"], relevant) is True
    assert is_relevant(_chunk("Profit Ability 2", 99)["metadata"], relevant) is False


def test_match_title_only_for_synthetic_pages():
    relevant = [{"source_title": "Signalling Success", "pages": None}]
    assert is_relevant(_chunk("Signalling Success", 7)["metadata"], relevant) is True


def test_non_match_on_wrong_title():
    relevant = [{"source_title": "Profit Ability 2", "pages": [12]}]
    assert is_relevant(_chunk("Demand Generator", 12)["metadata"], relevant) is False


def test_dedupe_collapses_repeated_pages():
    chunks = [
        _chunk("Profit Ability 2", 12),
        _chunk("Profit Ability 2", 12),
        _chunk("Profit Ability 2", 13),
    ]
    assert len(dedupe_to_pages(chunks)) == 2


def test_build_relevances_end_to_end():
    chunks = [
        _chunk("Profit Ability 2", 12),  # relevant
        _chunk("Profit Ability 2", 12),  # duplicate page -> collapsed
        _chunk("Demand Generator", 4),  # not relevant
    ]
    relevant = [{"source_title": "Profit Ability 2", "pages": [12]}]
    rels = build_relevances(chunks, relevant)
    assert rels == [True, False]
    assert count_relevant_targets(relevant) == 1
    assert recall_at_k(rels, count_relevant_targets(relevant), k=5) == 1.0


def test_count_relevant_targets_mixed():
    relevant = [
        {"source_title": "Profit Ability 2", "pages": [12, 13]},
        {"source_title": "Signalling Success", "pages": None},
    ]
    assert count_relevant_targets(relevant) == 3


def test_recall_flags_title_only_not_inflated():
    # Several pages of one title-only document collapse to ONE target,
    # so recall stays bounded by 1.0 (the bug this guards against).
    chunks = [
        _chunk("The Value of TV", 3),
        _chunk("The Value of TV", 5),
        _chunk("The Value of TV", 9),
    ]
    relevant = [{"source_title": "The Value of TV", "pages": None}]
    flags = build_recall_flags(chunks, relevant)
    assert flags == [True, False, False]
    rec = recall_at_k(flags, count_relevant_targets(relevant), k=5)
    assert rec == 1.0
    # Precision still counts every relevant result.
    assert build_relevances(chunks, relevant) == [True, True, True]


def test_recall_flags_distinct_pages_each_count():
    chunks = [_chunk("Profit Ability 2", 9), _chunk("Profit Ability 2", 30)]
    relevant = [{"source_title": "Profit Ability 2", "pages": [9, 30]}]
    flags = build_recall_flags(chunks, relevant)
    assert flags == [True, True]
    assert recall_at_k(flags, count_relevant_targets(relevant), k=5) == 1.0
