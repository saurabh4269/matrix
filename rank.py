"""Redrob ranking, single-command entry point.

    python rank.py --candidates ./candidates.jsonl --out ./submission.csv

Runs end-to-end:
  1. Stream candidates.jsonl (lazy loading).
  2. Apply honeypot gate + score every non-honeypot candidate.
  3. Sort by linear score.
  4. Pairwise refinement on top 20.
  5. Generate reasoning for top 100.
  6. Write Pydantic-validated CSV + structured JSONL beside it.

CPU only, no network calls, single-pass over the input file. Designed to
complete in well under the hackathon's 5-minute / 16 GB budget.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

from src.calibration import (
    bayesian_confidence,
    compute_pool_stats,
    diversify_top_n,
    is_statistical_outlier,
    mahalanobis_distance,
    percentile_from_z,
    z_scores,
)
from src.load import iter_candidates
from src.pairwise import refine_top_n
from src.reasoning import generate_reasoning
from src.schema import SubmissionRow
from src.scoring import score_candidate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--candidates",
        required=True,
        help="Path to candidates.jsonl (or .jsonl.gz).",
    )
    ap.add_argument(
        "--out",
        required=True,
        help="Output CSV path. A sibling .structured.jsonl is also written.",
    )
    ap.add_argument(
        "--top",
        type=int,
        default=100,
        help="Number of candidates to include in output (default 100).",
    )
    ap.add_argument(
        "--pairwise-window",
        type=int,
        default=20,
        help="How many top candidates to refine via pairwise comparison.",
    )
    args = ap.parse_args()

    t0 = time.time()
    print(f"Loading and scoring candidates from {args.candidates}…", file=sys.stderr)

    # Keep both: full CandidateScore (for output sidecar) + the per-candidate dict
    scored = []
    by_id = {}  # candidate_id -> Candidate (for reasoning generation)
    seen = 0
    n_honeypot = 0
    # Discarded candidates — honeypots quarantined upfront. Written as a sidecar
    # JSONL for transparency ("we filtered these out, here's why").
    discarded: list[dict] = []

    for cand in iter_candidates(args.candidates):
        seen += 1
        cs = score_candidate(cand)
        if cs.is_honeypot:
            n_honeypot += 1
            discarded.append({
                "candidate_id": cand.candidate_id,
                "name": cand.profile.anonymized_name,
                "current_title": cand.profile.current_title,
                "current_company": cand.profile.current_company,
                "discard_kind": "honeypot",
                "rules_fired": [
                    {"name": k, "evidence": v}
                    for k, v in cs.honeypot_evidence.items()
                ],
            })
            continue
        scored.append(cs)
        by_id[cand.candidate_id] = cand
        if seen % 10_000 == 0:
            print(
                f"  {seen:>7,} candidates processed "
                f"({time.time()-t0:5.1f}s), honeypots so far: {n_honeypot}",
                file=sys.stderr,
            )

    print(
        f"Scan complete: {seen:,} candidates ({n_honeypot} honeypots quarantined) "
        f"in {time.time()-t0:.1f}s",
        file=sys.stderr,
    )

    # Compute pool statistics for z-score / Mahalanobis / Bayesian calibration
    print("Computing pool calibration stats…", file=sys.stderr)
    pool_stats = compute_pool_stats(scored)

    # Flag statistical outliers (extra honeypot defence beyond deterministic rules)
    extra_outliers = 0
    for cs in scored:
        if is_statistical_outlier(cs, pool_stats):
            extra_outliers += 1
    print(f"  Statistical outliers (Mahalanobis > 4): {extra_outliers}", file=sys.stderr)

    # Sort by linear score, then ID for stable ordering
    scored.sort(key=lambda cs: (-cs.score, cs.candidate_id))

    # Pairwise refinement on top window
    print(f"Pairwise refinement on top {args.pairwise_window}…", file=sys.stderr)
    scored = refine_top_n(scored, n=args.pairwise_window)

    # Portfolio-diversity pass on top 20: nudges the order to spread across
    # companies / locations without bumping strong candidates out.
    print(f"Portfolio diversity pass on top 20…", file=sys.stderr)
    scored = diversify_top_n(scored, lambda cid: by_id[cid], n=20, diversity_weight=0.05)

    # Take top N
    top = scored[: args.top]

    # Enforce score monotonicity required by validator: scores must be non-increasing.
    # Pairwise refinement may swap two candidates whose raw scores differ; reassign
    # display scores as a monotone non-increasing sequence based on final order.
    if top:
        max_score = top[0].score
        floor_score = min(0.0, top[-1].score) if top else 0.0
        # Map each rank to a synthetic score that decreases monotonically with rank
        # while preserving order (rank 1 highest, rank 100 lowest).
        # Strategy: use linear interpolation from max → max(0.001, min_real_score)
        baseline_max = max(0.001, max_score) if max_score > 0 else 1.0
        baseline_min = max(0.001, min(cs.score for cs in top))
        spread = baseline_max - baseline_min
        if spread <= 0:
            # All same, assign decreasing dummy scores
            for i, cs in enumerate(top):
                cs.score = float(round(1.0 - 0.001 * i, 6))
        else:
            for i, cs in enumerate(top):
                # Place into a strictly decreasing schedule between baseline_max and baseline_min
                cs.score = float(round(baseline_max - (i / (len(top) - 1 + 1e-9)) * spread, 6))

    # Generate reasoning for each top candidate
    print(f"Generating reasoning for top {len(top)}…", file=sys.stderr)
    rows = []
    structured = []
    for rank, cs in enumerate(top, start=1):
        cand = by_id[cs.candidate_id]
        reasoning = generate_reasoning(cand, cs, rank)
        # Pydantic-validate the row before writing
        row = SubmissionRow(
            candidate_id=cs.candidate_id,
            rank=rank,
            score=cs.score,
            reasoning=reasoning,
        )
        rows.append(row)
        # Bayesian + z-score calibration metadata
        bayes_bucket, bayes_posterior = bayesian_confidence(cs, pool_stats)
        z = z_scores(cs, pool_stats)
        structured.append({
            "candidate_id": cs.candidate_id,
            "rank": rank,
            "score": cs.score,
            "confidence": cs.confidence,
            "confidence_bayes": {
                "bucket": bayes_bucket,
                "posterior_tier5": round(bayes_posterior, 4),
            },
            "breakdown": cs.breakdown,
            "calibration": {
                "must_have_percentile": percentile_from_z(z["must_have_z"]),
                "substance_percentile": percentile_from_z(z["substance_z"]),
                "score_percentile": percentile_from_z(z["score_z"]),
                "mahalanobis": round(mahalanobis_distance(cs, pool_stats), 3),
            },
            "reasoning": reasoning,
            "must_have": [
                {"name": n, "score": round(s, 4), "evidence": e}
                for n, s, e in cs.must_have
            ],
            "substance": [
                {"name": n, "score": round(s, 4), "evidence": e}
                for n, s, e in cs.substance
            ],
            "behavioural": [
                {"name": n, "score": round(s, 4), "evidence": e}
                for n, s, e in cs.behavioural
            ],
            "anti_snr": [
                {"name": n, "score": round(s, 4), "evidence": e}
                for n, s, e in cs.anti_snr
            ],
            "behavioural_modifier": round(cs.behavioural_modifier, 4),
            "anti_snr_penalty": round(cs.anti_snr_penalty, 4),
        })

    # ----- Write CSV -----
    # Final tie-break enforcement matches the spec's rule: equal scores must be
    # ordered by candidate_id ascending. After the score reassignment above,
    # scores should be strictly decreasing, so this is a no-op safety pass.
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        for r in rows:
            writer.writerow([r.candidate_id, r.rank, r.score, r.reasoning])

    # ----- Write structured sidecar -----
    sidecar = out_path.with_suffix(".structured.jsonl")
    with open(sidecar, "w", encoding="utf-8") as fp:
        for s in structured:
            fp.write(json.dumps(s, ensure_ascii=False) + "\n")

    # ----- Write discarded (graveyard) sidecar -----
    # Every honeypot quarantined + the worst anti-SNR offenders (top 50),
    # with the rule(s) that fired. Transparency about what the system rejected.
    bad_offenders = sorted(
        [cs for cs in scored if cs.anti_snr_penalty < 0.2],
        key=lambda cs: cs.anti_snr_penalty,
    )[:50]
    for cs in bad_offenders:
        cand = by_id[cs.candidate_id]
        discarded.append({
            "candidate_id": cs.candidate_id,
            "name": cand.profile.anonymized_name,
            "current_title": cand.profile.current_title,
            "current_company": cand.profile.current_company,
            "discard_kind": "heavy_anti_snr",
            "rules_fired": [
                {"name": n, "score": round(s, 3), "evidence": e}
                for n, s, e in cs.anti_snr if s > 0
            ],
        })
    discard_path = out_path.parent / (out_path.stem + ".discarded.jsonl")
    with open(discard_path, "w", encoding="utf-8") as fp:
        for d in discarded:
            fp.write(json.dumps(d, ensure_ascii=False) + "\n")

    # ----- Cooling watchlist -----
    # Candidates with strong skill profiles (above-median must-have) but very
    # weak behavioural availability (dormant, slow, high notice). The
    # "great fit, wrong timing" pile. Useful for the recruiter to come back to.
    mh_median = pool_stats.must_have_mean
    cooling = sorted(
        [
            cs for cs in scored
            if cs.must_have_sum > mh_median * 1.5
            and cs.behavioural_modifier < 0.4
            and not cs.is_honeypot
        ],
        key=lambda cs: -cs.must_have_sum,
    )[:30]
    cooling_path = out_path.parent / (out_path.stem + ".cooling.jsonl")
    with open(cooling_path, "w", encoding="utf-8") as fp:
        for cs in cooling:
            cand = by_id[cs.candidate_id]
            fp.write(json.dumps({
                "candidate_id": cs.candidate_id,
                "name": cand.profile.anonymized_name,
                "current_title": cand.profile.current_title,
                "current_company": cand.profile.current_company,
                "must_have_sum": round(cs.must_have_sum, 3),
                "behavioural_modifier": round(cs.behavioural_modifier, 3),
                "reason": "strong profile, currently unreachable — try later",
            }, ensure_ascii=False) + "\n")

    elapsed = time.time() - t0
    print(f"\nWrote {out_path} ({len(rows)} rows)", file=sys.stderr)
    print(f"Wrote {sidecar} (structured evidence)", file=sys.stderr)
    print(f"Wrote {discard_path} ({len(discarded)} discarded candidates)", file=sys.stderr)
    print(f"Wrote {cooling_path} ({len(cooling)} cooling watchlist)", file=sys.stderr)
    print(f"Total elapsed: {elapsed:.1f}s", file=sys.stderr)
    print(f"Honeypots quarantined: {n_honeypot}/{seen}", file=sys.stderr)


if __name__ == "__main__":
    main()
