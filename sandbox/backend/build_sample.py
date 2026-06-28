"""Build sandbox/backend/sample_candidates.json, the curated demo set.

Picks: top 12 of the real ranking, 6 keyword-stuffers (to demonstrate trap
defense), 2 honeypots (will be quarantined), 5 plain-language tier-5s
(to surface the whispered hint moment). Total ~25.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.heuristics import assign_bucket
from src.load import iter_candidates


CHALLENGE_FILE = (
    r"C:/Users/shmishra/Documents/Matrix/[PUB] India_runs_data_and_ai_challenge/"
    r"India_runs_data_and_ai_challenge/candidates.jsonl"
)

OUT_FILE = Path(__file__).parent / "sample_candidates.json"

CSV_FILE = ROOT / "submissions" / "team_v3.csv"


def main():
    # Load the top-12 from our baseline submission
    top_ids: list[str] = []
    with open(CSV_FILE, "r", encoding="utf-8") as fp:
        next(fp)  # header
        for i, line in enumerate(fp):
            if i >= 12:
                break
            top_ids.append(line.split(",")[0])

    print(f"Top 12 candidate IDs from baseline: {top_ids[:3]}...", file=sys.stderr)

    # Pull buckets in one streaming pass
    selected_top: dict[str, dict] = {}
    keyword_stuffers: list[dict] = []
    honeypot_candidates: list[dict] = []
    tier5_likely: list[dict] = []

    for cand in iter_candidates(CHALLENGE_FILE):
        cid = cand.candidate_id

        if cid in top_ids:
            selected_top[cid] = cand.model_dump()

        bucket = assign_bucket(cand)
        if bucket == "likely_keyword_stuffer" and len(keyword_stuffers) < 6:
            keyword_stuffers.append(cand.model_dump())
        elif bucket == "honeypot_suspect" and len(honeypot_candidates) < 2:
            honeypot_candidates.append(cand.model_dump())
        elif bucket == "likely_tier5" and cid not in top_ids and len(tier5_likely) < 5:
            tier5_likely.append(cand.model_dump())

        if (
            len(selected_top) == len(top_ids)
            and len(keyword_stuffers) >= 6
            and len(honeypot_candidates) >= 2
            and len(tier5_likely) >= 5
        ):
            break

    # Combine: top picks first, then stuffers, honeypots, additional tier-5s
    out = (
        [selected_top[i] for i in top_ids if i in selected_top]
        + tier5_likely
        + keyword_stuffers
        + honeypot_candidates
    )

    with open(OUT_FILE, "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=2)

    print(
        f"Wrote {OUT_FILE} with {len(out)} candidates "
        f"({len(selected_top)} top + {len(tier5_likely)} tier5 + "
        f"{len(keyword_stuffers)} stuffers + {len(honeypot_candidates)} honeypots)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
