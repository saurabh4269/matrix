"""Merge filled-in labels.csv with sample_to_label.jsonl.

Output: eval/labelled.jsonl, one JSON object per labelled candidate, containing
both the candidate record and the human labels. This is the canonical eval-set
consumed by metrics.py and the weight tuner.

Usage:
    python -m eval.merge_labels
        [--sample eval/sample_to_label.jsonl]
        [--labels eval/labels.csv]
        [--out    eval/labelled.jsonl]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path


VALID_TIERS = {"0", "1", "2", "3", "4", "5"}
VALID_HONEYPOT = {"TRUE", "FALSE", "true", "false", "True", "False", "1", "0"}
VALID_TRAP = {
    "clean", "keyword_stuffer", "consulting_only", "bigcorp_only",
    "plain_language_tier5", "cv_speech_robotics_only", "title_chaser", "other",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", default="eval/sample_to_label.jsonl")
    ap.add_argument("--labels", default="eval/labels.csv")
    ap.add_argument("--out", default="eval/labelled.jsonl")
    args = ap.parse_args()

    # Load sample (full candidate records keyed by id)
    by_id = {}
    with open(args.sample, "r", encoding="utf-8") as fp:
        for line in fp:
            if line.strip():
                obj = json.loads(line)
                by_id[obj["candidate"]["candidate_id"]] = obj

    if not by_id:
        print(f"FATAL: {args.sample} is empty", file=sys.stderr)
        sys.exit(1)

    # Load labels
    issues = []
    tier_counts = Counter()
    trap_counts = Counter()
    honeypot_count = 0
    labelled = 0
    out_records = []

    with open(args.labels, "r", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            cid = row.get("candidate_id", "").strip()
            tier_s = row.get("tier", "").strip()
            hp_s = row.get("is_honeypot", "").strip()
            trap = row.get("trap_class", "").strip()
            strength = row.get("primary_strength", "").strip()
            concern = row.get("primary_concern", "").strip()
            notes = row.get("notes", "").strip()

            if not cid:
                continue  # blank line
            if cid not in by_id:
                issues.append(f"{cid}: not present in sample")
                continue
            if not tier_s:
                # unlabelled, skip silently
                continue
            if tier_s not in VALID_TIERS:
                issues.append(f"{cid}: invalid tier {tier_s!r}")
                continue
            if hp_s and hp_s not in VALID_HONEYPOT:
                issues.append(f"{cid}: invalid is_honeypot {hp_s!r}")
                continue
            if trap and trap not in VALID_TRAP:
                issues.append(f"{cid}: invalid trap_class {trap!r}")
                continue

            tier = int(tier_s)
            is_honeypot = hp_s.lower() in {"true", "1"}
            if tier >= 3 and not strength:
                issues.append(f"{cid}: tier {tier} requires primary_strength")

            tier_counts[tier] += 1
            if is_honeypot:
                honeypot_count += 1
            if trap:
                trap_counts[trap] += 1
            labelled += 1

            rec = by_id[cid]
            rec["label"] = {
                "tier": tier,
                "is_honeypot": is_honeypot,
                "trap_class": trap or "clean",
                "primary_strength": strength,
                "primary_concern": concern,
                "notes": notes,
            }
            out_records.append(rec)

    # Write merged JSONL
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fp:
        for rec in out_records:
            fp.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # Report
    print(f"Labelled candidates: {labelled} / {len(by_id)}")
    print(f"  Tier distribution: {dict(sorted(tier_counts.items()))}")
    print(f"  Honeypots: {honeypot_count}")
    print(f"  Trap classes: {dict(trap_counts)}")

    if issues:
        print(f"\n{len(issues)} ISSUE(S):", file=sys.stderr)
        for i in issues[:20]:
            print(f"  - {i}", file=sys.stderr)
        if len(issues) > 20:
            print(f"  ... and {len(issues) - 20} more", file=sys.stderr)
        sys.exit(1)

    # Calibration guidance
    n_tier5 = tier_counts.get(5, 0)
    if labelled >= 100 and n_tier5 > labelled * 0.15:
        print(
            f"\n⚠ Calibration warning: {n_tier5} tier-5 in {labelled} labels "
            f"({n_tier5/labelled*100:.1f}%). JD implies tier-5 should be rare "
            f"(~5–10% of sample). Consider tightening.",
            file=sys.stderr,
        )

    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
