"""Write a manifest YAML beside a submission CSV.

A manifest captures everything needed to reproduce a result and to attribute
ranking changes to a config change:
  - git SHA
  - active JD config (path + name)
  - probe weights snapshot
  - top-100 candidate IDs + scores
  - timestamp + ranker version flags (cross-encoder on/off, debate on/off)
  - basic distribution stats (median score, score range, honeypot count)

Usage:
    python -m eval.track --submission submissions/team_v4.csv
    python -m eval.track --submission submissions/team_v5.csv --label "ce-on"

The label is appended to the manifest filename so we can tell experiments
apart at a glance. If the JD config differs from the default, that gets
recorded too.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.jd_config import get_config, load_jd  # noqa: E402


def _git_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()
    except Exception:
        return "unknown"


def _git_dirty() -> bool:
    try:
        out = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, stderr=subprocess.DEVNULL,
        )
        return bool(out.decode().strip())
    except Exception:
        return False


def _load_csv(path: Path) -> list[dict[str, Any]]:
    rows = []
    with open(path, "r", encoding="utf-8") as fp:
        for r in csv.DictReader(fp):
            rows.append({
                "candidate_id": r["candidate_id"],
                "rank": int(r["rank"]),
                "score": float(r["score"]),
            })
    return rows


def _stats(rows: list[dict[str, Any]]) -> dict[str, float]:
    scores = sorted(r["score"] for r in rows)
    n = len(scores)
    return {
        "n": n,
        "min_score": scores[0] if scores else 0.0,
        "max_score": scores[-1] if scores else 0.0,
        "median_score": scores[n // 2] if n else 0.0,
        "p90_score": scores[int(n * 0.9)] if n else 0.0,
    }


def _structured_summary(structured_path: Path) -> dict[str, Any]:
    """Pull a few signals out of the structured JSONL beside the CSV."""
    if not structured_path.exists():
        return {}
    honeypot = 0
    confidence_counts = {"high": 0, "medium": 0, "low": 0}
    main_risk_count = 0
    next_action_count = 0
    with open(structured_path, "r", encoding="utf-8") as fp:
        for line in fp:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("is_honeypot"):
                honeypot += 1
            c = r.get("confidence")
            if c in confidence_counts:
                confidence_counts[c] += 1
            if r.get("main_risk"):
                main_risk_count += 1
            if r.get("next_action"):
                next_action_count += 1
    return {
        "honeypot_count": honeypot,
        "confidence_distribution": confidence_counts,
        "rows_with_main_risk": main_risk_count,
        "rows_with_next_action": next_action_count,
    }


def write_manifest(
    submission_csv: Path,
    label: str | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    rows = _load_csv(submission_csv)

    cfg = get_config()
    weights_dict = cfg.weights.model_dump() if cfg.weights else {}

    manifest = {
        "submission": submission_csv.name,
        "label": label or submission_csv.stem,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git": {
            "sha": _git_sha(),
            "dirty": _git_dirty(),
        },
        "jd": {
            "name": cfg.name,
            "display_name": cfg.display_name,
            "yoe_peak": cfg.yoe.peak,
            "yoe_sigma": cfg.yoe.sigma,
        },
        "weights_snapshot": weights_dict,
        "extra": extra or {},
        "stats": _stats(rows),
        "structured": _structured_summary(submission_csv.with_name(submission_csv.stem + ".structured.jsonl")),
        "top_20_ids": [r["candidate_id"] for r in sorted(rows, key=lambda x: x["rank"])[:20]],
        "top_100_ids": [r["candidate_id"] for r in sorted(rows, key=lambda x: x["rank"])[:100]],
    }

    out = submission_csv.with_name(submission_csv.stem + ".manifest.yaml")
    out.write_text(yaml.safe_dump(manifest, sort_keys=False, default_flow_style=False), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--submission", required=True, help="Submission CSV path.")
    ap.add_argument("--label", default=None, help="Short label for this run, e.g. 'ce-on', 'debate-rerank'.")
    ap.add_argument("--jd", default=None, help="Path to JD YAML used (otherwise reads active config).")
    ap.add_argument("--extra", default=None, help="JSON string of extra fields to record.")
    args = ap.parse_args()

    sub = Path(args.submission)
    if not sub.exists():
        print(f"FATAL: {sub} not found.", file=sys.stderr)
        sys.exit(1)

    if args.jd:
        # Force-load the requested JD so the manifest records its weights
        from src.jd_config import set_config
        set_config(load_jd(args.jd))

    extra = json.loads(args.extra) if args.extra else None
    out = write_manifest(sub, label=args.label, extra=extra)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
