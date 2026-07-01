"""One-line-per-submission leaderboard.

Glob submissions/*.csv, look for sibling .manifest.yaml / .judge.yaml /
.eval.yaml files, and print a wide table so we can see at a glance:

  label      git_sha    when    n   top10_overlap_v4   judge_tau   ndcg10_gold  p5_gold   notes
  team_v4    a7f3994    today   100  10/10              0.92        —            —         baseline
  team_v5    c0908…     today   100  9/10               0.88        0.87         0.80      ce-rerank on
  team_v6    …          today   100  8/10               0.94        0.93         0.85      debate-rerank

The leaderboard is how we know which experiment actually moved the needle.

Usage:
    python -m eval.leaderboard
    python -m eval.leaderboard --baseline submissions/team_v4.csv \\
                                --gold eval/labelled.jsonl
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def _read_csv_ids(p: Path) -> list[str]:
    out = []
    with open(p, "r", encoding="utf-8") as fp:
        for r in csv.DictReader(fp):
            out.append((int(r["rank"]), r["candidate_id"]))
    return [c for _, c in sorted(out)]


def _set_overlap(a: list[str], b: list[str], k: int) -> str:
    sa, sb = set(a[:k]), set(b[:k])
    return f"{len(sa & sb)}/{k}"


def _gold_eval(submission_csv: Path, labels_path: Path | None) -> dict[str, float | str]:
    """Run eval.metrics if labels exist."""
    if not labels_path or not labels_path.exists():
        return {"ndcg10": "-", "ndcg50": "-", "map": "-", "p10": "-", "composite": "-"}
    try:
        from eval.metrics import evaluate
    except Exception:
        return {"ndcg10": "ERR", "ndcg50": "ERR", "map": "ERR", "p5": "ERR", "p10": "ERR"}
    label_by_id: dict[str, dict] = {}
    with open(labels_path, "r", encoding="utf-8") as fp:
        for line in fp:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            label_by_id[d["candidate_id"]] = d
    if not label_by_id:
        return {"ndcg10": "—", "ndcg50": "—", "map": "—", "p5": "—", "p10": "—"}
    sub_ids = _read_csv_ids(submission_csv)
    try:
        m = evaluate(sub_ids, label_by_id)
        return {
            "ndcg10": f"{m['ndcg@10']:.3f}",
            "ndcg50": f"{m['ndcg@50']:.3f}",
            "map": f"{m['map']:.3f}",
            "p10": f"{m['p@10']:.3f}",
            "composite": f"{m['composite']:.3f}",
        }
    except Exception as e:
        return {"ndcg10": f"ERR:{e}", "ndcg50": "-", "map": "-", "p10": "-", "composite": "-"}


def _load(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as fp:
            return yaml.safe_load(fp)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--submissions-dir", default="submissions")
    ap.add_argument("--baseline", default=None, help="CSV path to compare overlaps against.")
    ap.add_argument("--gold", default="eval/labelled.jsonl",
                    help="Ground-truth labels (from merge_labels). If absent, gold columns show '—'.")
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--out", default=None, help="Write the table to this file too.")
    args = ap.parse_args()

    sub_dir = Path(args.submissions_dir)
    csvs = sorted(sub_dir.glob("*.csv"))
    if not csvs:
        print(f"No submission CSVs in {sub_dir}")
        return

    baseline_path = Path(args.baseline) if args.baseline else None
    baseline_ids = _read_csv_ids(baseline_path) if baseline_path and baseline_path.exists() else None

    gold_path = Path(args.gold)

    rows = []
    for csv_path in csvs:
        manifest = _load(csv_path.with_name(csv_path.stem + ".manifest.yaml"))
        judge = _load(csv_path.with_name(csv_path.stem + ".judge.yaml"))
        ids = _read_csv_ids(csv_path)

        label = manifest.get("label") if manifest else csv_path.stem
        sha = (manifest.get("git", {}).get("sha", "—")[:7]) if manifest else "—"
        when = manifest.get("created_at", "—")[:10] if manifest else "—"
        n = len(ids)

        overlap = _set_overlap(baseline_ids, ids, args.top_k) if baseline_ids else "—"

        if judge:
            agree = judge.get("agreement_vs_submission", {})
            tau_key = f"top_{args.top_k}_kendall_tau"
            tau = agree.get(tau_key, "—")
            tau = f"{tau:.2f}" if isinstance(tau, (int, float)) else "—"
        else:
            tau = "—"

        gold = _gold_eval(csv_path, gold_path)

        notes = ""
        if manifest:
            extra = manifest.get("extra") or {}
            flags = []
            if extra.get("cross_encoder_rerank"):
                flags.append("ce")
            if extra.get("debate_rerank"):
                flags.append("debate")
            if extra.get("hrms"):
                flags.append("hrms")
            notes = ",".join(flags) if flags else ""
            if manifest.get("git", {}).get("dirty"):
                notes = (notes + " dirty").strip()

        rows.append({
            "label": label,
            "sha": sha,
            "when": when,
            "n": n,
            f"overlap@{args.top_k}": overlap,
            "judge_tau": tau,
            "ndcg10": gold["ndcg10"],
            "ndcg50": gold["ndcg50"],
            "map": gold["map"],
            "p10": gold["p10"],
            "composite": gold["composite"],
            "notes": notes,
        })

    # Print table
    cols = list(rows[0].keys())
    widths = {c: max(len(c), max(len(str(r[c])) for r in rows)) for c in cols}
    header = "  ".join(f"{c:<{widths[c]}}" for c in cols)
    sep = "  ".join("-" * widths[c] for c in cols)
    lines = [header, sep]
    for r in rows:
        lines.append("  ".join(f"{str(r[c]):<{widths[c]}}" for c in cols))
    out_str = "\n".join(lines)
    print(out_str)
    print()
    print("Legend:")
    print(f"  overlap@{args.top_k}: top-{args.top_k} candidates shared with baseline")
    print(f"  judge_tau   : Kendall tau between submission and LLM-judge proxy ranking")
    print(f"  ndcg10/50, map, p10: against {gold_path} (— if no labels)")

    if args.out:
        Path(args.out).write_text(out_str + "\n", encoding="utf-8")
        print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
