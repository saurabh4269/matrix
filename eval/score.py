"""eval/score.py, score a submission CSV against the labelled eval set.

Usage:
    python -m eval.score --labels eval/labelled.jsonl --submission submissions/x.csv

Outputs the four hackathon metrics + composite + honeypot rate. Use this every
time you change a probe weight; numbers must move in the right direction
before you trust the change.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from eval.metrics import evaluate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--labels",
        default="eval/labelled.jsonl",
        help="Path to labelled.jsonl produced by merge_labels.py",
    )
    ap.add_argument(
        "--submission",
        required=True,
        help="Path to submission CSV (candidate_id,rank,score,reasoning).",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Emit results as JSON to stdout instead of human-readable.",
    )
    args = ap.parse_args()

    # Load labels
    labels_path = Path(args.labels)
    if not labels_path.exists():
        print(f"FATAL: labels file not found at {labels_path}", file=sys.stderr)
        print(
            "  Did you run `python -m eval.merge_labels` after filling labels.csv?",
            file=sys.stderr,
        )
        sys.exit(1)
    label_by_id: dict[str, dict] = {}
    with open(labels_path, "r", encoding="utf-8") as fp:
        for line in fp:
            if not line.strip():
                continue
            obj = json.loads(line)
            cid = obj["candidate"]["candidate_id"]
            label_by_id[cid] = obj.get("label", {})

    if not label_by_id:
        print(f"FATAL: no labels found in {labels_path}", file=sys.stderr)
        sys.exit(1)

    # Load submission CSV
    ranked: list[str] = []
    with open(args.submission, "r", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            ranked.append(row["candidate_id"])

    if not ranked:
        print(f"FATAL: submission {args.submission} is empty", file=sys.stderr)
        sys.exit(1)

    # Coverage report, how many of the submission's top-100 overlap with labels
    in_labelled = sum(1 for c in ranked if c in label_by_id)

    metrics = evaluate(ranked, label_by_id)
    metrics["labelled_overlap_in_top_100"] = in_labelled
    metrics["labelled_total"] = len(label_by_id)
    metrics["submission_size"] = len(ranked)

    if args.json:
        print(json.dumps(metrics, indent=2))
        return

    print(f"Submission: {args.submission}")
    print(f"Labels:     {args.labels}  ({len(label_by_id)} candidates labelled)")
    print(f"Overlap:    {in_labelled}/{len(ranked)} of submission top-100 are in the labelled set")
    print()
    print(f"  NDCG@10               {metrics['ndcg@10']:.4f}    (weight 0.50)")
    print(f"  NDCG@50               {metrics['ndcg@50']:.4f}    (weight 0.30)")
    print(f"  MAP                   {metrics['map']:.4f}    (weight 0.15)")
    print(f"  P@10                  {metrics['p@10']:.4f}    (weight 0.05)")
    print(f"  -----------------------------------------------")
    print(f"  Composite             {metrics['composite']:.4f}")
    print()
    print(f"  Honeypot rate top-100 {metrics['honeypot_rate_top_100']*100:.1f}%  ({'PASS' if metrics['honeypot_rate_top_100'] <= 0.10 else 'FAIL, Stage-3 DQ at >10%'})")
    print(f"  Honeypot rate top-10  {metrics['honeypot_rate_top_10']*100:.1f}%")
    print()

    if in_labelled < 20:
        print(
            f"⚠ Only {in_labelled} of your top-100 overlap with the labelled set. "
            f"Metric estimates have high variance. Consider labelling more candidates "
            f"or running a larger sample.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
