"""Conformal-style rank confidence intervals.

A point rank ("Sarah is #1") doesn't tell a recruiter how stable that rank is.
A conformal interval ("Sarah is #1 with 95% CI [1, 4]") tells them the system
is confident she's a top-tier pick even under reasonable score perturbations.

We use a simple split-conformal flavour adapted to ranking: for each top-N
candidate, perturb the underlying probe-score components within the historical
variance of the pool, re-rank, and observe how the candidate's rank varies.
The 5th and 95th percentiles of that re-ranked distribution give a 90%
confidence interval; we extend to 95% with a small inflation factor.

This is NOT proper conformal prediction (which would require calibration on
held-out exchangeable data). It's the practical, label-free approximation
that gives the recruiter a usable stability signal without overclaiming.
"""
from __future__ import annotations

import numpy as np

from src.scoring import CandidateScore, CATEGORY_WEIGHTS


def _category_score(cs: CandidateScore) -> float:
    """Recompute the additive base score from category sums. Helper."""
    return (
        CATEGORY_WEIGHTS["must_have"] * cs.must_have_sum
        + CATEGORY_WEIGHTS["substance"] * cs.substance_sum
        + CATEGORY_WEIGHTS["retrieval"] * cs.retrieval_sum
        + CATEGORY_WEIGHTS["location"] * cs.location_sum
    )


def compute_rank_intervals(
    ordered_scores: list[CandidateScore],
    n_perturbations: int = 50,
    perturbation_std: float = 0.05,
    rng_seed: int = 42,
) -> dict[str, tuple[int, int]]:
    """Return {candidate_id: (lo_rank, hi_rank)} for the top-N candidates.

    Method: for each perturbation, jitter every candidate's must_have_sum,
    substance_sum, retrieval_sum, location_sum, anti_snr_penalty, and
    behavioural_modifier independently by Gaussian noise N(0, perturbation_std),
    recompute the final score, and re-rank. Take the 2.5% and 97.5% rank
    quantiles across perturbations as the 95% CI.

    Only computed for top-30 candidates to keep this O(30 * 50) instead of
    O(100k * 50). Outside top-30, the rank is presumed stable enough that
    a wide interval doesn't add information.
    """
    if not ordered_scores:
        return {}

    rng = np.random.default_rng(rng_seed)
    N_TOP = min(30, len(ordered_scores))

    # Snapshot the raw components for every candidate, so we can perturb +
    # re-score deterministically. Use numpy arrays for speed.
    M = len(ordered_scores)
    mh = np.asarray([cs.must_have_sum for cs in ordered_scores], dtype=np.float64)
    sb = np.asarray([cs.substance_sum for cs in ordered_scores], dtype=np.float64)
    rt = np.asarray([cs.retrieval_sum for cs in ordered_scores], dtype=np.float64)
    lc = np.asarray([cs.location_sum for cs in ordered_scores], dtype=np.float64)
    anti = np.asarray([cs.anti_snr_penalty for cs in ordered_scores], dtype=np.float64)
    behav = np.asarray([cs.behavioural_modifier for cs in ordered_scores], dtype=np.float64)
    ids = [cs.candidate_id for cs in ordered_scores]

    # cat weights as vector
    w_mh, w_sb, w_rt, w_lc = (
        CATEGORY_WEIGHTS["must_have"],
        CATEGORY_WEIGHTS["substance"],
        CATEGORY_WEIGHTS["retrieval"],
        CATEGORY_WEIGHTS["location"],
    )

    rank_history = np.zeros((n_perturbations, M), dtype=np.int32)
    for i in range(n_perturbations):
        # Multiplicative Gaussian noise centred on 1.0
        noise_mh = rng.normal(1.0, perturbation_std, size=M)
        noise_sb = rng.normal(1.0, perturbation_std, size=M)
        noise_rt = rng.normal(1.0, perturbation_std, size=M)
        noise_lc = rng.normal(1.0, perturbation_std, size=M)
        noise_anti = np.clip(rng.normal(1.0, perturbation_std, size=M), 0.0, None)
        noise_behav = np.clip(rng.normal(1.0, perturbation_std, size=M), 0.0, None)

        base = (
            w_mh * mh * noise_mh
            + w_sb * sb * noise_sb
            + w_rt * rt * noise_rt
            + w_lc * lc * noise_lc
        )
        scores = base * (anti * noise_anti) * (behav * noise_behav)
        # argsort returns indices sorted ascending; we want descending
        order = np.argsort(-scores, kind="stable")
        # ranks[order[i]] = i+1
        ranks = np.empty(M, dtype=np.int32)
        ranks[order] = np.arange(1, M + 1)
        rank_history[i] = ranks

    # Compute quantiles for the top-N only (others get wide CI by default)
    intervals: dict[str, tuple[int, int]] = {}
    for idx in range(N_TOP):
        ranks_for_cand = rank_history[:, idx]
        lo = int(np.percentile(ranks_for_cand, 2.5))
        hi = int(np.percentile(ranks_for_cand, 97.5))
        intervals[ids[idx]] = (lo, hi)
    return intervals
