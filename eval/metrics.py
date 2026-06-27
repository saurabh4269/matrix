"""Ranking metrics, NDCG@k, MAP, P@k, for evaluating against the labelled set.

All four metrics match those in the hackathon's composite score:
    Final = 0.50·NDCG@10 + 0.30·NDCG@50 + 0.15·MAP + 0.05·P@10
"""
from __future__ import annotations

import math
from typing import Iterable


def _dcg(relevances: list[float]) -> float:
    """Discounted cumulative gain. Position is 1-indexed inside the formula."""
    return sum(
        (2**r - 1) / math.log2(i + 2)
        for i, r in enumerate(relevances)
    )


def ndcg_at_k(ranked_relevances: list[float], k: int) -> float:
    """NDCG@k. `ranked_relevances` is the relevance value at each rank (rank 1 first)."""
    if not ranked_relevances or k <= 0:
        return 0.0
    actual = _dcg(ranked_relevances[:k])
    ideal = _dcg(sorted(ranked_relevances, reverse=True)[:k])
    return actual / ideal if ideal > 0 else 0.0


def precision_at_k(ranked_relevances: list[float], k: int, threshold: float = 3.0) -> float:
    """Fraction of top-k where relevance >= threshold (default tier 3+)."""
    if k <= 0:
        return 0.0
    top = ranked_relevances[:k]
    if not top:
        return 0.0
    return sum(1 for r in top if r >= threshold) / k


def average_precision(
    ranked_relevances: list[float], threshold: float = 1.0
) -> float:
    """Mean average precision across relevance levels.

    `threshold` defines what counts as relevant (default >= 1 = any non-zero tier).
    For each relevant item at position i (1-indexed), accumulate precision@i.
    """
    relevant_count = 0
    score_sum = 0.0
    total_relevant = sum(1 for r in ranked_relevances if r >= threshold)
    if total_relevant == 0:
        return 0.0
    for i, r in enumerate(ranked_relevances, start=1):
        if r >= threshold:
            relevant_count += 1
            score_sum += relevant_count / i
    return score_sum / total_relevant


def composite(
    ranked_relevances: list[float],
    *,
    ndcg10_weight: float = 0.50,
    ndcg50_weight: float = 0.30,
    map_weight: float = 0.15,
    p10_weight: float = 0.05,
) -> float:
    """The hackathon's composite score formula."""
    return (
        ndcg10_weight * ndcg_at_k(ranked_relevances, 10)
        + ndcg50_weight * ndcg_at_k(ranked_relevances, 50)
        + map_weight * average_precision(ranked_relevances)
        + p10_weight * precision_at_k(ranked_relevances, 10, threshold=3.0)
    )


def honeypot_rate_top_k(is_honeypot_ranked: list[bool], k: int = 100) -> float:
    """Fraction of top-k that are honeypots. >0.10 → Stage-3 DQ."""
    top = is_honeypot_ranked[:k]
    if not top:
        return 0.0
    return sum(1 for h in top if h) / len(top)


def evaluate(
    ranked_candidate_ids: list[str],
    label_by_id: dict[str, dict],
    k_for_p: int = 10,
) -> dict:
    """End-to-end eval: takes a ranked list of candidate IDs + a label lookup,
    returns the four metrics plus composite plus honeypot rate.

    Candidates in `ranked_candidate_ids` not present in `label_by_id` are
    treated as relevance 0 (tier 0), they were neither labelled positive nor
    labelled honeypot, so they don't help or hurt.
    """
    relevances = []
    is_honeypot = []
    for cid in ranked_candidate_ids:
        lab = label_by_id.get(cid)
        if lab is None:
            relevances.append(0.0)
            is_honeypot.append(False)
        else:
            relevances.append(float(lab.get("tier", 0)))
            is_honeypot.append(bool(lab.get("is_honeypot", False)))

    return {
        "ndcg@10": ndcg_at_k(relevances, 10),
        "ndcg@50": ndcg_at_k(relevances, 50),
        "map": average_precision(relevances),
        "p@10": precision_at_k(relevances, 10),
        "composite": composite(relevances),
        "honeypot_rate_top_100": honeypot_rate_top_k(is_honeypot, 100),
        "honeypot_rate_top_10": honeypot_rate_top_k(is_honeypot, 10),
    }
