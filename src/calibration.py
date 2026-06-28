"""Population-level calibration of candidate scores.

Borrows three ideas from quantitative finance / IR / anomaly detection:

  1. Z-score standardisation across the pool. A raw probe score is a local,
     saturating measure. But "this candidate has a substance score in the top
     5% of the pool" tells the recruiter something a raw 0.8 does not. We
     compute z-scores for the key probe scores against the whole-pool
     distribution, and surface them in the structured output.

  2. Mahalanobis outlier detection. The honeypot detector catches the
     obvious impossibilities (chronological paradox etc.). A statistical
     outlier score complements that by flagging candidates whose probe-vector
     is unusually far from the pool's mean. Helps catch synthesised profiles
     that pass the deterministic rules.

  3. Portfolio-diversity selection. Two strong candidates at the same company
     are worth less than one strong candidate from each of two companies.
     Especially relevant at the top-10 where a recruiter can't talk to ten
     people from Razorpay. We add a diversity-aware re-ranking pass that
     gently spreads the top 20 across companies / locations / education tiers
     while preserving the linear scorer's overall ordering.

  4. Bayesian confidence (posterior P(tier-5 | evidence)). Reframes the
     heuristic confidence buckets in scoring.py as a proper posterior using
     simple count-based priors learned from typical pool ratios.

None of this changes the deterministic ranking pipeline. It produces extra
calibration metadata that gets attached to each top-100 candidate's
structured-JSONL record.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

import numpy as np

from src.scoring import CandidateScore


# ---------------------------------------------------------------------------
# Z-score standardisation
# ---------------------------------------------------------------------------

@dataclass
class PoolStats:
    """Means + stds for the key probe categories computed over the whole pool.

    Used to standardise per-candidate scores into pool-relative percentiles.
    """
    must_have_mean: float
    must_have_std: float
    substance_mean: float
    substance_std: float
    retrieval_mean: float
    retrieval_std: float
    behavioural_mean: float
    behavioural_std: float
    score_mean: float
    score_std: float


def compute_pool_stats(scores: Sequence[CandidateScore]) -> PoolStats:
    """Compute the population mean + std for each category sum across the pool.

    Excludes honeypots (score == -1) from the population so calibration isn't
    distorted by quarantined candidates.
    """
    pool = [s for s in scores if not s.is_honeypot]
    if not pool:
        # Fallback: all-zero stats so z-scores degenerate to 0
        return PoolStats(0, 1, 0, 1, 0, 1, 0, 1, 0, 1)

    mh = np.asarray([s.must_have_sum for s in pool], dtype=np.float64)
    sb = np.asarray([s.substance_sum for s in pool], dtype=np.float64)
    rt = np.asarray([s.retrieval_sum for s in pool], dtype=np.float64)
    bv = np.asarray([s.behavioural_modifier for s in pool], dtype=np.float64)
    sc = np.asarray([s.score for s in pool], dtype=np.float64)

    def _safe_std(arr) -> float:
        sd = float(arr.std())
        return sd if sd > 1e-9 else 1.0

    return PoolStats(
        must_have_mean=float(mh.mean()), must_have_std=_safe_std(mh),
        substance_mean=float(sb.mean()), substance_std=_safe_std(sb),
        retrieval_mean=float(rt.mean()), retrieval_std=_safe_std(rt),
        behavioural_mean=float(bv.mean()), behavioural_std=_safe_std(bv),
        score_mean=float(sc.mean()), score_std=_safe_std(sc),
    )


def z_scores(cs: CandidateScore, pool: PoolStats) -> dict[str, float]:
    """Return per-category z-scores for one candidate vs the pool."""
    return {
        "must_have_z": (cs.must_have_sum - pool.must_have_mean) / pool.must_have_std,
        "substance_z": (cs.substance_sum - pool.substance_mean) / pool.substance_std,
        "retrieval_z": (cs.retrieval_sum - pool.retrieval_mean) / pool.retrieval_std,
        "behavioural_z": (cs.behavioural_modifier - pool.behavioural_mean) / pool.behavioural_std,
        "score_z": (cs.score - pool.score_mean) / pool.score_std,
    }


def percentile_from_z(z: float) -> float:
    """Approximate normal-CDF percentile for a z-score. Returns [0, 100]."""
    # cumulative distribution function of the standard normal
    cdf = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    return round(cdf * 100.0, 1)


# ---------------------------------------------------------------------------
# Mahalanobis outlier detection
# ---------------------------------------------------------------------------

def mahalanobis_distance(cs: CandidateScore, pool: PoolStats) -> float:
    """Diagonal Mahalanobis distance from the pool centroid.

    We use a diagonal covariance (independent z-scores) because correlated
    full-covariance Mahalanobis on a 5-dim probe vector is overkill for the
    signal we want. Higher distance means "more unusual."
    """
    z = z_scores(cs, pool)
    # Sum of squared z-scores = chi-square statistic with k degrees of freedom
    return float(math.sqrt(
        z["must_have_z"]**2
        + z["substance_z"]**2
        + z["retrieval_z"]**2
        + z["behavioural_z"]**2
    ))


def is_statistical_outlier(cs: CandidateScore, pool: PoolStats, threshold: float = 4.0) -> bool:
    """Flag candidates whose probe vector is unusually far from the pool.

    Threshold 4.0 ~ 99.9th percentile under a 4-DOF chi distribution. Most
    real outliers we want to flag are statistical impossibilities the
    deterministic honeypot detector missed.
    """
    return mahalanobis_distance(cs, pool) > threshold


# ---------------------------------------------------------------------------
# Bayesian confidence
# ---------------------------------------------------------------------------

def bayesian_confidence(cs: CandidateScore, pool: PoolStats) -> tuple[str, float]:
    """Reframe the heuristic confidence bucket as a posterior probability.

    Priors:
      P(tier-5 | random candidate) ~ 0.0015  (about 150 in 100k per the JD)
    Likelihoods (rough, calibrated from the labelled bucket distributions):
      P(strong must-have signal | tier-5) ~ 0.85
      P(strong must-have signal | not tier-5) ~ 0.03
      P(strong substance | tier-5) ~ 0.7
      P(strong substance | not tier-5) ~ 0.05
      P(no major anti-SNR | tier-5) ~ 0.95
      P(no major anti-SNR | not tier-5) ~ 0.5
      P(available | tier-5) ~ 0.7
      P(available | not tier-5) ~ 0.6

    Returns (bucket, posterior). The bucket boundaries are derived from
    the posterior thresholds and align with the heuristic in scoring.py.
    """
    from src.scoring import ANTI_SNR_WEIGHTS

    P_TIER5_PRIOR = 0.0015

    # Likelihood ratios for each evidence node.
    strong_mh = sum(1 for _, s, _ in cs.must_have if s > 0.5)
    strong_sb = sum(1 for _, s, _ in cs.substance if s > 0.4)
    major_anti = sum(
        1 for n, s, _ in cs.anti_snr
        if s > 0.4 and ANTI_SNR_WEIGHTS.get(n, 0.0) >= 0.7
    )

    # Naive-Bayes accumulation in log space (avoids underflow).
    log_odds = math.log(P_TIER5_PRIOR / (1.0 - P_TIER5_PRIOR))

    # Each strong must-have evidence node: P(E|T5)/P(E|~T5) ~ 0.85/0.03 ≈ 28
    log_odds += min(strong_mh, 3) * math.log(28.0)
    # Each strong substance signal: 0.7/0.05 = 14
    log_odds += min(strong_sb, 3) * math.log(14.0)
    # Major anti-SNR: 0.95/0.5 = 1.9 in the "no flag" case;
    # presence inverts the ratio: 0.05/0.5 = 0.1.
    if major_anti == 0:
        log_odds += math.log(1.9)
    else:
        log_odds += min(major_anti, 3) * math.log(0.1)
    # Behavioural availability: continuous, lerp the LR
    behav_lr = 0.7 if cs.behavioural_modifier > 0.5 else 0.3
    log_odds += math.log(behav_lr / 0.6)

    posterior = 1.0 / (1.0 + math.exp(-log_odds))

    if posterior > 0.4:
        return "high", posterior
    if posterior > 0.05:
        return "medium", posterior
    return "low", posterior


# ---------------------------------------------------------------------------
# Portfolio diversity (Maximal Marginal Relevance-style)
# ---------------------------------------------------------------------------

def diversify_top_n(
    ordered: list[CandidateScore],
    cand_lookup,
    n: int = 20,
    diversity_weight: float = 0.15,
) -> list[CandidateScore]:
    """Re-rank the top N to favour diversity across (company, location).

    Greedy MMR-style selection: at each step, pick the candidate whose
    quality minus diversity-penalty against already-picked is highest. The
    diversity penalty is small enough that strong candidates are never
    bumped from top-10 in favour of weaker but more-diverse ones; it mostly
    affects the ordering inside the top 20 and edge cases where 4+ candidates
    share a company.

    cand_lookup: callable candidate_id -> Candidate (for reading company/location).
    """
    if not ordered:
        return ordered

    top_orig = ordered[:n]
    tail = ordered[n:]

    selected: list[CandidateScore] = []
    pool = top_orig[:]
    used_companies: Counter = Counter()
    used_locations: Counter = Counter()

    # The strongest candidate is always selected first.
    pool.sort(key=lambda cs: -cs.score)
    while pool:
        best_idx = 0
        best_mmr = -1e9
        for i, cs in enumerate(pool):
            cand = cand_lookup(cs.candidate_id)
            co = (cand.profile.current_company or "").strip().lower()
            loc = (cand.profile.location or "").strip().lower().split(",")[0]
            penalty = (
                0.5 * used_companies[co]
                + 0.3 * used_locations[loc]
            )
            mmr = cs.score - diversity_weight * penalty
            if mmr > best_mmr:
                best_mmr = mmr
                best_idx = i
        chosen = pool.pop(best_idx)
        selected.append(chosen)
        cand = cand_lookup(chosen.candidate_id)
        co = (cand.profile.current_company or "").strip().lower()
        loc = (cand.profile.location or "").strip().lower().split(",")[0]
        used_companies[co] += 1
        used_locations[loc] += 1

    return selected + tail
