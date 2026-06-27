"""Stratified sampler — selects 300 candidates across 5 buckets for hand-labelling.

Single pass over the 100K JSONL. Reservoir-style sampling per bucket so memory
stays small. Emits three artefacts:

  eval/sample_to_label.jsonl   — full candidate records, for the merger
  eval/candidates_to_label.md  — scannable Markdown cards
  eval/labels.csv              — empty CSV template the user fills
  eval/sampling_report.md      — bucket counts, heuristic doc, calibration

Usage:
    python -m eval.sample \\
        --candidates "C:/Users/.../candidates.jsonl" \\
        --out-dir ./eval \\
        --per-bucket 60 \\
        --seed 42
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

from src.cards import render_card
from src.heuristics import (
    assign_bucket,
    count_jd_keyword_skills,
    fires_any_structural_paradox,
    has_ml_title_anywhere,
    has_ml_title_current,
    has_product_company_in_history,
    is_consulting_only_career,
    retrieval_mentions_in_descriptions,
)
from src.load import iter_candidates
from src.schema import Candidate


BUCKETS = [
    "likely_tier5",
    "likely_tier4",
    "adjacent_mid",
    "likely_keyword_stuffer",
    "honeypot_suspect",
    "random_control",
]

# How much we want each bucket OVER-SAMPLED before reservoir thinning, to
# avoid wasted slots in rare buckets:
OVERSAMPLE_FACTOR = 3


def _stable_hash(s: str) -> int:
    return int(hashlib.md5(s.encode("utf-8")).hexdigest(), 16)


def reservoir_sample(stream, k: int, key=None) -> list:
    """Standard reservoir sampling — yields up to k items uniformly from a stream
    of unknown length. `key` deterministically seeds randomness from each item
    so the output is reproducible across runs."""
    pool = []
    for i, item in enumerate(stream):
        if len(pool) < k:
            pool.append(item)
        else:
            # Use a stable-hash seeded RNG for reproducibility
            seed = key(item) if key else i
            rng = random.Random(seed)
            j = rng.randint(0, i)
            if j < k:
                pool[j] = item
    return pool


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--candidates",
        required=True,
        help="Path to candidates.jsonl (full 100K file).",
    )
    ap.add_argument("--out-dir", default="./eval", help="Output directory.")
    ap.add_argument(
        "--per-bucket",
        type=int,
        default=60,
        help="Target candidates per bucket (5 buckets × per-bucket = total).",
    )
    ap.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility.",
    )
    ap.add_argument(
        "--max-scan",
        type=int,
        default=None,
        help="Optional cap on candidates scanned (for dry-run testing).",
    )
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    bucket_counts_raw = Counter()  # total candidates that fell into each bucket
    bucket_oversampled = {b: [] for b in BUCKETS}  # reservoir per bucket

    # Diagnostic counters for the sampling report
    diag = Counter()

    t0 = time.time()
    print(f"Scanning candidates from {args.candidates}…", file=sys.stderr)

    for i, cand in enumerate(iter_candidates(args.candidates)):
        if args.max_scan is not None and i >= args.max_scan:
            break

        # Diagnostics
        if has_ml_title_current(cand):
            diag["ml_title_current"] += 1
        if has_ml_title_anywhere(cand):
            diag["ml_title_anywhere"] += 1
        if has_product_company_in_history(cand):
            diag["product_co_in_history"] += 1
        if is_consulting_only_career(cand):
            diag["consulting_only"] += 1
        flags = fires_any_structural_paradox(cand)
        if flags:
            diag["structural_paradox_any"] += 1
            for f in flags:
                diag[f"paradox:{f}"] += 1

        bucket = assign_bucket(cand)
        bucket_counts_raw[bucket] += 1

        # Reservoir sample within each bucket
        k = args.per_bucket * OVERSAMPLE_FACTOR
        pool = bucket_oversampled[bucket]
        n_seen = bucket_counts_raw[bucket]
        if len(pool) < k:
            pool.append(cand)
        else:
            seed = _stable_hash(cand.candidate_id + str(args.seed))
            rng = random.Random(seed)
            j = rng.randint(0, n_seen - 1)
            if j < k:
                pool[j] = cand

        if (i + 1) % 10_000 == 0:
            elapsed = time.time() - t0
            print(
                f"  {i+1:>7,} candidates scanned ({elapsed:5.1f}s) — "
                f"buckets: {dict(bucket_counts_raw)}",
                file=sys.stderr,
            )

    total_scanned = i + 1
    print(
        f"Scan complete: {total_scanned:,} candidates in {time.time()-t0:.1f}s",
        file=sys.stderr,
    )

    # Thin each bucket from over-sampled pool down to args.per_bucket
    selected = []
    for b in BUCKETS:
        pool = bucket_oversampled[b]
        # Use seed-stable shuffle for reproducibility
        rng = random.Random(args.seed + hash(b))
        rng.shuffle(pool)
        chosen = pool[: args.per_bucket]
        for c in chosen:
            selected.append((b, c))
        print(
            f"  bucket {b:25s} — raw count: {bucket_counts_raw[b]:>7,}  "
            f"reservoir: {len(pool):>4}  selected: {len(chosen):>3}",
            file=sys.stderr,
        )

    # Sort selected for stable card numbering (by bucket then candidate_id)
    selected.sort(key=lambda t: (BUCKETS.index(t[0]), t[1].candidate_id))

    # --- Emit eval/sample_to_label.jsonl --------------------------------------
    sample_path = out_dir / "sample_to_label.jsonl"
    with open(sample_path, "w", encoding="utf-8") as fp:
        for bucket, cand in selected:
            obj = {"bucket": bucket, "candidate": cand.model_dump()}
            fp.write(json.dumps(obj, ensure_ascii=False) + "\n")
    print(f"Wrote {sample_path}", file=sys.stderr)

    # --- Emit eval/candidates_to_label.md -------------------------------------
    md_path = out_dir / "candidates_to_label.md"
    with open(md_path, "w", encoding="utf-8") as fp:
        fp.write("# Redrob — Candidates to Label\n\n")
        fp.write(
            "Read each card (~30s). Fill in `eval/labels.csv` with one row per `candidate_id`.\n\n"
            "**Tier scale (against JD):** 0 honeypot · 1 clear no · 2 weak · 3 maybe · 4 strong · 5 ideal\n\n"
            "**Touchstone:** *if you had this candidate and only this JD, "
            "would you forward them to the hiring manager?* → tier 4+. *Worth a call but not forward?* → tier 3.\n\n"
        )
        for idx, (bucket, cand) in enumerate(selected, start=1):
            fp.write(render_card(cand, bucket, idx))
    print(f"Wrote {md_path}", file=sys.stderr)

    # --- Emit eval/labels.csv (template) --------------------------------------
    labels_path = out_dir / "labels.csv"
    with open(labels_path, "w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow(
            [
                "card_index",
                "candidate_id",
                "bucket",
                "tier",  # 0-5, REQUIRED
                "is_honeypot",  # TRUE/FALSE, REQUIRED
                "trap_class",  # one of: clean, keyword_stuffer, consulting_only, bigcorp_only,
                               # plain_language_tier5, cv_speech_robotics_only, title_chaser, other
                "primary_strength",  # 3-12 words, REQUIRED for tier>=3
                "primary_concern",  # optional
                "notes",  # optional
            ]
        )
        for idx, (bucket, cand) in enumerate(selected, start=1):
            writer.writerow(
                [idx, cand.candidate_id, bucket, "", "", "", "", "", ""]
            )
    print(f"Wrote {labels_path}", file=sys.stderr)

    # --- Emit eval/sampling_report.md -----------------------------------------
    report_path = out_dir / "sampling_report.md"
    with open(report_path, "w", encoding="utf-8") as fp:
        fp.write("# Sampling Report\n\n")
        fp.write(
            f"- **Total scanned:** {total_scanned:,}\n"
            f"- **Per-bucket target:** {args.per_bucket}\n"
            f"- **Seed:** {args.seed}\n"
            f"- **Total selected:** {sum(args.per_bucket for _ in BUCKETS)}\n\n"
        )
        fp.write("## Raw bucket distribution across all 100K candidates\n\n")
        fp.write("| Bucket | Count | % of pool |\n|---|---|---|\n")
        for b in BUCKETS:
            n = bucket_counts_raw[b]
            pct = 100.0 * n / total_scanned if total_scanned else 0
            fp.write(f"| `{b}` | {n:,} | {pct:.2f}% |\n")
        fp.write("\n")

        fp.write("## Diagnostic signals\n\n")
        fp.write("| Signal | Count |\n|---|---|\n")
        for k in sorted(diag.keys()):
            fp.write(f"| `{k}` | {diag[k]:,} |\n")
        fp.write("\n")

        fp.write("## Bucket assignment heuristics\n\n")
        fp.write(
            "Priority order (first match wins, mutually exclusive):\n\n"
            "1. **`likely_tier5`** — current title contains ML/AI/IR signal "
            "AND has a known product company in history AND ≥2 retrieval-substance "
            "mentions in `career_history.description`. Tier-5 wins over honeypot — "
            "if a real ML engineer happens to fire a paradox rule, we want to see it.\n"
            "2. **`honeypot_suspect`** — any structural paradox fires (salary, "
            "date inversion, duration > YoE+2, single role > YoE+12mo, "
            "≥3 expert skills with 0 months) AND not already tier-5.\n"
            "3. **`likely_tier4`** — any past title is ML/AI/IR AND (product co "
            "anywhere OR ≥3 retrieval-substance mentions).\n"
            "4. **`likely_keyword_stuffer`** — ≥6 JD-keyword skills AND no ML "
            "title anywhere AND ≤1 retrieval-substance mentions. The trap "
            "signature: keywords on the surface, no execution underneath.\n"
            "5. **`adjacent_mid`** — any ML title OR ≥1 retrieval mention OR "
            "≥2 JD keywords. Mid-strength signal.\n"
            "6. **`random_control`** — fallthrough. No signal in any direction. "
            "Boring negatives — anchors the bottom of the relevance scale.\n\n"
            "These are heuristics for *stratification*, not labels. Hand-label "
            "is the truth signal.\n\n"
        )

        fp.write("## How to use this sample\n\n")
        fp.write(
            "1. Open `candidates_to_label.md` in a Markdown previewer (VS Code Ctrl+Shift+V).\n"
            "2. Open `labels.csv` in your spreadsheet/editor.\n"
            "3. For each card (~30s each): fill `tier` (0–5), `is_honeypot` (TRUE/FALSE), "
            "`trap_class`, and `primary_strength` (for tier≥3).\n"
            "4. Touchstone for tier: *would you forward this candidate to the hiring manager?*\n"
            "5. Calibration check after labelling: tier 5 should stay rare (~10–20 out of 300). "
            "If you find yourself labelling 50+ as tier 5, recalibrate against JD stinginess.\n"
            "6. When done, run `python -m eval.merge_labels` to merge labels back into the "
            "candidate JSONL for the metric pipeline.\n"
        )
    print(f"Wrote {report_path}", file=sys.stderr)

    print(f"\nDone. Total selected: {len(selected)}", file=sys.stderr)


if __name__ == "__main__":
    main()
