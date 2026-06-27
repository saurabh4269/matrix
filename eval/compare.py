"""eval/compare.py, diff two submission CSVs.

Useful for understanding what a system change actually did:
  - candidates added/removed from top 100
  - rank deltas for shared candidates
  - rank-band churn (how much did top-10 change?)

Usage:
    python -m eval.compare --a submissions/baseline.csv --b submissions/hybrid.csv
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path


def load(path: str) -> dict[str, tuple[int, float]]:
    """Return candidate_id -> (rank, score) from a submission CSV."""
    out = {}
    with open(path, "r", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            out[row["candidate_id"]] = (int(row["rank"]), float(row["score"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="Baseline submission CSV.")
    ap.add_argument("--b", required=True, help="New submission CSV.")
    ap.add_argument("--top", type=int, default=10, help="Print rank diff up to this rank.")
    args = ap.parse_args()

    a = load(args.a)
    b = load(args.b)

    ids_a = set(a)
    ids_b = set(b)

    added = ids_b - ids_a
    removed = ids_a - ids_b
    shared = ids_a & ids_b

    print(f"A: {Path(args.a).name}  ({len(a)} candidates)")
    print(f"B: {Path(args.b).name}  ({len(b)} candidates)")
    print()
    print(f"  Shared:      {len(shared):>3}")
    print(f"  Added in B:  {len(added):>3}")
    print(f"  Removed:     {len(removed):>3}")
    print()

    # Rank movement on shared candidates
    deltas = []
    for cid in shared:
        ra, _ = a[cid]
        rb, _ = b[cid]
        deltas.append((cid, ra, rb, rb - ra))
    deltas.sort(key=lambda t: abs(t[3]), reverse=True)

    moved = [d for d in deltas if d[3] != 0]
    print(f"  Moved (shared candidates with rank change): {len(moved)}")
    if moved:
        print(f"  Median move (absolute):                     {sorted(abs(d[3]) for d in moved)[len(moved)//2]}")
    print()

    # Top-10 churn
    top10_a = {cid for cid, (r, _) in a.items() if r <= 10}
    top10_b = {cid for cid, (r, _) in b.items() if r <= 10}
    top10_churn = len(top10_a ^ top10_b) / 2
    print(f"  Top-10 churn: {int(top10_churn)} candidates differ")
    print(f"    Only in A's top-10: {sorted(top10_a - top10_b)}")
    print(f"    Only in B's top-10: {sorted(top10_b - top10_a)}")
    print()

    # Show the largest rank moves
    print(f"Largest rank moves (positive = ranked lower in B):")
    for cid, ra, rb, delta in deltas[:15]:
        sign = "+" if delta > 0 else ""
        print(f"  {cid}  rank {ra:>3} -> {rb:>3}  ({sign}{delta})")

    # Top-N comparison side by side
    print()
    print(f"Top {args.top} side by side:")
    print(f"  {'rank':<4}  {'A':<14}  {'B':<14}")
    sorted_a = sorted(a.items(), key=lambda t: t[1][0])
    sorted_b = sorted(b.items(), key=lambda t: t[1][0])
    for i in range(args.top):
        ca = sorted_a[i][0] if i < len(sorted_a) else "–"
        cb = sorted_b[i][0] if i < len(sorted_b) else "–"
        same = "  " if ca == cb else "* "
        print(f"  {i+1:<4}  {ca:<14}  {cb:<14}  {same}")


if __name__ == "__main__":
    main()
