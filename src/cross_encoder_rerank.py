"""Optional cross-encoder rerank on the top 50.

The pairwise refinement (src/pairwise.py) works by hand-coded JD-priority
tiebreakers. A cross-encoder model — trained specifically to score
(query, passage) pairs — can be more accurate at the same job. We use the
small CPU-friendly cross-encoder/ms-marco-MiniLM-L-6-v2 (~80MB, ~30ms per
candidate on CPU at 256 tokens).

Runs OPTIONALLY:
  - If sentence-transformers is installed, the model is loaded and applied
    to the top 50 (a few seconds of CPU work).
  - If not installed, the rerank is a no-op and the pairwise refinement
    output stands.

The cross-encoder output is BLENDED with the linear score (not a hard
overwrite) — alpha controls the mix, default 0.4. This protects against a
weak cross-encoder run blowing up the careful structured scoring.
"""
from __future__ import annotations

import sys
from typing import Callable

from src.jd_config import get_config
from src.schema import Candidate
from src.scoring import CandidateScore


def candidate_passage(cand: Candidate) -> str:
    """Build the passage we feed the cross-encoder. Mirrors precompute.py's text."""
    parts = [
        cand.profile.headline or "",
        cand.profile.summary or "",
    ]
    for r in cand.career_history[:5]:
        parts.append(f"{r.title} at {r.company}: {r.description or ''}")
    text = " ".join(parts).strip()
    # Truncate to ~512 chars so we don't blow past the encoder's 512-token cap
    return text[:2000]


def rerank_with_cross_encoder(
    ordered: list[CandidateScore],
    cand_lookup: Callable[[str], Candidate],
    n: int = 50,
    alpha: float = 0.4,
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
) -> list[CandidateScore]:
    """Re-rank the top n by blending linear score with cross-encoder relevance.

    final_score = (1 - alpha) * normalised_linear + alpha * normalised_cross
    The blend keeps strong structured-signal candidates from being demoted by
    a cross-encoder that doesn't know about behavioural availability or
    honeypot rules.
    """
    if not ordered or n <= 0:
        return ordered

    try:
        from sentence_transformers import CrossEncoder  # type: ignore
    except ImportError:
        print(
            "Cross-encoder rerank skipped: sentence-transformers not installed.",
            file=sys.stderr,
        )
        return ordered

    top = ordered[:n]
    tail = ordered[n:]

    jd_text = get_config().jd_text

    print(
        f"Loading cross-encoder {model_name} (~80MB)…",
        file=sys.stderr,
    )
    try:
        model = CrossEncoder(model_name)
    except Exception as e:
        print(f"Cross-encoder load failed: {e}. Skipping rerank.", file=sys.stderr)
        return ordered

    passages = [candidate_passage(cand_lookup(cs.candidate_id)) for cs in top]
    pairs = [(jd_text, p) for p in passages]

    print(f"Scoring {len(pairs)} candidate-JD pairs…", file=sys.stderr)
    raw_scores = model.predict(pairs, show_progress_bar=False)

    # Normalise both signals to [0, 1] before blending
    lin = [cs.score for cs in top]
    cross = list(map(float, raw_scores))

    def norm(xs):
        lo, hi = min(xs), max(xs)
        if hi - lo < 1e-9:
            return [0.5] * len(xs)
        return [(x - lo) / (hi - lo) for x in xs]

    lin_n = norm(lin)
    cross_n = norm(cross)

    blended = [
        (1.0 - alpha) * lin_n[i] + alpha * cross_n[i]
        for i in range(len(top))
    ]

    # Re-sort by blended score; preserve CandidateScore objects untouched
    indexed = list(zip(top, blended))
    indexed.sort(key=lambda t: -t[1])
    return [cs for cs, _ in indexed] + tail
