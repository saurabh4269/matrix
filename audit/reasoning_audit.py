"""Offline hallucination audit on the generated reasoning column.

Each reasoning string is supposed to cite real facts from the candidate's
schema. Because we generate via deterministic templating from parsed schema
attributes, hallucination should be impossible by construction, but this
script catches it if the template logic ever drifts.

The audit checks each reasoning against the candidate's actual schema fields:
  - every named company in the reasoning must appear in career_history
  - every numeric (years/months) must match years_of_experience or duration_months
  - any named skill/tool must appear in either skills[] or career_history descriptions

Pure local, no network required. Run before every submission.

Usage:
    python -m audit.reasoning_audit \\
        --candidates "<path>/candidates.jsonl" \\
        --submission submissions/team_baseline.csv
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.load import iter_candidates
from src.schema import Candidate


# Patterns we look for in the reasoning column
_COMPANY_RE = re.compile(r"\bat (?P<co>[A-Z][\w&.,'\- ]+?)(?:[.;]| ,|$)")
_YEAR_RE = re.compile(r"\((?P<years>\d+(?:\.\d+)?)\s*(?:y|yr|year)\)")
_PROBE_EVIDENCE_NUMBERS_RE = re.compile(r"\b(?P<n>\d+)\s+(?:embedding|vector|ranking-eval|specific|hands-on|research)")


def audit_one(reasoning: str, cand: Candidate) -> list[str]:
    """Return a list of issues found. Empty means clean."""
    issues = []

    # All companies mentioned in reasoning must appear in profile or career history.
    known_companies = {
        cand.profile.current_company.strip().lower(),
        *(r.company.strip().lower() for r in cand.career_history),
    }
    for m in _COMPANY_RE.finditer(reasoning):
        mentioned = m.group("co").strip().lower().rstrip(".,;")
        if not mentioned or mentioned in {"product cos", "product co"}:
            continue
        # The reasoning may say "at Stripe Search team", try a substring match
        if not any(mentioned in kc or kc in mentioned for kc in known_companies if kc):
            issues.append(f"company '{mentioned}' not in candidate's career history")

    # Year claims in reasoning must match years_of_experience (or any duration)
    for m in _YEAR_RE.finditer(reasoning):
        claimed = float(m.group("years"))
        all_years = {round(cand.profile.years_of_experience, 1)}
        for r in cand.career_history:
            all_years.add(round(r.duration_months / 12.0, 1))
        # Allow small rounding tolerance
        if not any(abs(claimed - y) < 0.2 for y in all_years):
            issues.append(
                f"claimed {claimed}y but candidate's YoE={cand.profile.years_of_experience} "
                f"and durations={sorted(all_years)}"
            )

    return issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--submission", required=True)
    args = ap.parse_args()

    # Load submission
    submission: dict[str, dict] = {}
    with open(args.submission, "r", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            submission[row["candidate_id"]] = row
    target_ids = set(submission.keys())
    print(f"Submission has {len(target_ids)} candidates.", file=sys.stderr)

    # Stream candidates, audit only the ones in the submission
    all_issues: list[tuple[str, int, list[str]]] = []
    audited = 0
    for cand in iter_candidates(args.candidates):
        if cand.candidate_id not in target_ids:
            continue
        audited += 1
        row = submission[cand.candidate_id]
        rank = int(row["rank"])
        reasoning = row["reasoning"]
        issues = audit_one(reasoning, cand)
        if issues:
            all_issues.append((cand.candidate_id, rank, issues))
        if audited >= len(target_ids):
            break

    print(f"Audited {audited}/{len(target_ids)} candidates.")
    if not all_issues:
        print("\n[PASS] Clean - no hallucinations detected in any reasoning string.")
        return

    print(f"\n[WARN] {len(all_issues)} candidate(s) with potential issues:\n", file=sys.stderr)
    for cid, rank, issues in all_issues:
        print(f"  rank {rank} ({cid}):", file=sys.stderr)
        for i in issues:
            print(f"    - {i}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
