"""Conservative honeypot detector.

Only fires on truly impossible profiles. Borderline cases get heavy soft
penalties in `probes/anti_snr.py` but stay in the candidate pool.

Returns a dict of (rule_name -> evidence_str) for every rule that fires.
Empty dict = candidate is clean.

NOTE: salary_paradox (min>max) is intentionally NOT included, see
src/heuristics.py for the empirical finding that 18.9% of the synthesized
dataset has min>max, making it a data artifact rather than a honeypot signal.
"""
from __future__ import annotations

from src.schema import Candidate


# Known company founding years, used by the tenure-exceeds-company-age rule.
# Stays small and conservative; only firms that obviously didn't exist before
# their founding year. False-positive cost is high (drops a real candidate),
# so this list is intentionally short.
COMPANY_FOUNDED = {
    # AI / ML co's with recent founding
    "openai": 2015,
    "anthropic": 2021,
    "cohere": 2019,
    "hugging face": 2016,
    "huggingface": 2016,
    "scale ai": 2016,
    "weights & biases": 2017,
    "weights and biases": 2017,
    "wandb": 2017,
    "databricks": 2013,
    "snowflake": 2012,
    "stripe": 2010,
    "perplexity": 2022,
    "perplexity ai": 2022,
    "mistral": 2023,
    "mistral ai": 2023,
    # Indian unicorns / scale-ups (commonly mis-claimed)
    "razorpay": 2014,
    "cred": 2018,
    "swiggy": 2014,
    "zomato": 2008,
    "phonepe": 2015,
    "byju's": 2011,
    "byjus": 2011,
    "unacademy": 2015,
    "udaan": 2016,
    "meesho": 2015,
    "yellow.ai": 2016,
    "yellow ai": 2016,
    "aganitha": 2017,
}


def _normalize_company(name: str) -> str:
    return name.strip().lower()


def detect(cand: Candidate) -> dict[str, str]:
    """Return dict of {rule_name: evidence} for every rule that fires."""
    fires: dict[str, str] = {}

    # ----- Rule 1: chronological paradox -----
    for r in cand.career_history:
        if r.start_date and r.end_date and r.start_date > r.end_date:
            fires["chronological_paradox"] = (
                f"{r.company}/{r.title}: start={r.start_date} > end={r.end_date}"
            )
            break

    # ----- Rule 2: total career duration vastly exceeds claimed YoE -----
    total_months = sum(r.duration_months for r in cand.career_history)
    yoe = cand.profile.years_of_experience
    if yoe > 0 and total_months / 12.0 > yoe + 2.5:
        fires["duration_exceeds_yoe"] = (
            f"career sums to {total_months/12:.1f}y, but claims {yoe:.1f}y YoE"
        )

    # ----- Rule 3: single role exceeds claimed YoE -----
    yoe_months = yoe * 12
    for r in cand.career_history:
        if yoe > 0 and r.duration_months > yoe_months + 12:
            fires["single_role_exceeds_yoe"] = (
                f"{r.company}/{r.title}: {r.duration_months}mo "
                f"exceeds total YoE {yoe:.1f}y by >1y"
            )
            break

    # ----- Rule 4: ≥3 expert skills with 0 months duration -----
    n_expert_zero = sum(
        1 for s in cand.skills
        if s.proficiency == "expert" and s.duration_months == 0
    )
    if n_expert_zero >= 3:
        fires["expert_with_zero_months"] = (
            f"{n_expert_zero} skills marked 'expert' with 0 months duration"
        )

    # ----- Rule 5: tenure at a known-young company exceeds company age -----
    # Reference year used to compute company age. The dataset is from 2026.
    REF_YEAR = 2026
    for r in cand.career_history:
        if not r.start_date:
            continue
        norm = _normalize_company(r.company)
        founded = COMPANY_FOUNDED.get(norm)
        if founded is None:
            continue
        try:
            start_year = int(r.start_date[:4])
        except (ValueError, TypeError):
            continue
        if start_year < founded:
            fires["tenure_exceeds_company_age"] = (
                f"started at {r.company} in {start_year}, "
                f"but {r.company} was founded {founded}"
            )
            break
        # Also fire if claimed duration exceeds time the company has existed.
        company_age_months = (REF_YEAR - founded) * 12
        if r.duration_months > company_age_months + 6:
            fires["tenure_exceeds_company_age"] = (
                f"{r.duration_months}mo at {r.company}, "
                f"but company only ~{company_age_months}mo old"
            )
            break

    # ----- Rule 6: at least one assessed skill score for a skill the candidate
    # didn't claim. Mild-but-real inconsistency (synthesized profile bug). -----
    skill_names = {s.name.strip().lower() for s in cand.skills}
    orphan_assessments = [
        k for k in cand.redrob_signals.skill_assessment_scores
        if k.strip().lower() not in skill_names
    ]
    if len(orphan_assessments) >= 3:
        fires["orphan_skill_assessments"] = (
            f"{len(orphan_assessments)} assessment scores for skills "
            f"the candidate didn't claim: {orphan_assessments[:3]}…"
        )

    return fires


def is_honeypot(cand: Candidate) -> bool:
    """True if any honeypot rule fires."""
    return bool(detect(cand))
