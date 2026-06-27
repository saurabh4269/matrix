"""Pairwise refinement on the top 20.

NDCG@10 (50% of the composite score) is fundamentally a pairwise problem on
the top 10. Linear absolute scoring can be sloppy at the very top, tiny
absolute differences create big rank differences. So after linear scoring,
we re-rank the top 20 using hand-coded JD-priority tiebreakers.

Rules (in priority order, first decisive comparison wins):
  1. Years of applied ML at product co, more is better
  2. Description specificity, more named systems = more substance
  3. Ranking-eval framework mentions, JD literally names NDCG/MRR/MAP
  4. Production embeddings retrieval, must-have
  5. Verification ratio, tested > claimed
  6. Behavioural availability, actually hireable beats theoretically hireable
  7. Linear score as tiebreaker
  8. Candidate ID (lexicographic) as ultimate tiebreaker, matches spec
"""
from __future__ import annotations

from src.scoring import CandidateScore


def _probe_score(cs: CandidateScore, category: str, probe_name: str) -> float:
    """Look up the score of a single probe from a CandidateScore."""
    probes = getattr(cs, category, None)
    if not probes:
        return 0.0
    for name, score, _ in probes:
        if name == probe_name:
            return score
    return 0.0


def _pairwise_compare(a: CandidateScore, b: CandidateScore) -> int:
    """Return negative if a should come before b, positive if b first, 0 if tied.

    Used with functools.cmp_to_key for sorting.
    """
    THRESHOLD = 0.05  # how big a probe-score gap counts as decisive

    # 1. Years of applied ML at product co
    a_yrs = _probe_score(a, "must_have", "years_applied_ml_at_product_co")
    b_yrs = _probe_score(b, "must_have", "years_applied_ml_at_product_co")
    if abs(a_yrs - b_yrs) > THRESHOLD:
        return -1 if a_yrs > b_yrs else 1

    # 2. Description specificity
    a_spec = _probe_score(a, "substance", "description_specificity")
    b_spec = _probe_score(b, "substance", "description_specificity")
    if abs(a_spec - b_spec) > THRESHOLD:
        return -1 if a_spec > b_spec else 1

    # 3. Ranking-eval framework
    a_eval = _probe_score(a, "must_have", "ranking_eval_framework")
    b_eval = _probe_score(b, "must_have", "ranking_eval_framework")
    if abs(a_eval - b_eval) > THRESHOLD:
        return -1 if a_eval > b_eval else 1

    # 4. Production embeddings retrieval
    a_pe = _probe_score(a, "must_have", "production_embeddings_retrieval")
    b_pe = _probe_score(b, "must_have", "production_embeddings_retrieval")
    if abs(a_pe - b_pe) > THRESHOLD:
        return -1 if a_pe > b_pe else 1

    # 5. Verification ratio
    a_vr = _probe_score(a, "substance", "verification_ratio")
    b_vr = _probe_score(b, "substance", "verification_ratio")
    if abs(a_vr - b_vr) > THRESHOLD:
        return -1 if a_vr > b_vr else 1

    # 6. Behavioural availability
    if abs(a.behavioural_modifier - b.behavioural_modifier) > THRESHOLD:
        return -1 if a.behavioural_modifier > b.behavioural_modifier else 1

    # 7. Linear score
    if abs(a.score - b.score) > 1e-9:
        return -1 if a.score > b.score else 1

    # 8. Ultimate tiebreak, candidate_id ascending (matches submission spec)
    if a.candidate_id < b.candidate_id:
        return -1
    if a.candidate_id > b.candidate_id:
        return 1
    return 0


def refine_top_n(scored: list[CandidateScore], n: int = 20) -> list[CandidateScore]:
    """Take a linearly-sorted list and re-order the top n via pairwise rules.

    Returns the full list with positions [0:n] re-sorted by pairwise rules and
    positions [n:] left as-is (already sorted by linear score).
    """
    from functools import cmp_to_key

    top = scored[:n]
    tail = scored[n:]

    refined = sorted(top, key=cmp_to_key(_pairwise_compare))
    return refined + tail
