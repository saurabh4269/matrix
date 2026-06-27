"""Behavioural availability probes — multiplicative modifier on the overall score.

JD says: 'active on Redrob platform (or has clear signal of being in the job
market) so we can actually talk to them'. The behavioural signals are what
distinguish 'on paper good' from 'actually hireable'.
"""
from __future__ import annotations

import math
from datetime import date

from src.probes._text import saturating
from src.schema import Candidate


REF_DATE = date(2026, 6, 1)  # dataset reference date


def _days_since(date_str: str | None) -> int:
    if not date_str:
        return 9999
    try:
        d = date.fromisoformat(date_str[:10])
    except Exception:
        return 9999
    return (REF_DATE - d).days


def effectively_available(cand: Candidate) -> tuple[float, str]:
    """open_to_work × min(1, response/0.3) × decay(last_active, halflife=60d).

    Multiplicative — combines three independent availability signals.
    """
    s = cand.redrob_signals
    open_factor = 1.0 if s.open_to_work_flag else 0.6

    resp_factor = min(1.0, s.recruiter_response_rate / 0.3) if s.recruiter_response_rate > 0 else 0.3

    days = _days_since(s.last_active_date)
    decay = math.exp(-days / 60.0)  # half-life ~42 days

    score = open_factor * resp_factor * decay
    ev = (
        f"open_to_work={s.open_to_work_flag}, response_rate={s.recruiter_response_rate:.2f}, "
        f"last_active={days}d ago"
    )
    return score, ev


def notice_period_curve(cand: Candidate) -> tuple[float, str]:
    """Piecewise: ≤30d=1.0, 30→90 linear to 0.5, 90+→0.3 floor."""
    days = cand.redrob_signals.notice_period_days
    if days <= 30:
        score = 1.0
    elif days <= 90:
        score = 1.0 - 0.5 * ((days - 30) / 60.0)
    else:
        score = 0.3
    return score, f"notice {days}d"


def trust_modifier(cand: Candidate) -> tuple[float, str]:
    """Verified contact + LinkedIn — small but real bonus."""
    s = cand.redrob_signals
    flags = sum([s.verified_email, s.verified_phone, s.linkedin_connected])
    if flags == 0:
        return 0.7, "no verification flags"  # mild penalty
    if flags == 1:
        return 0.85, "1/3 verifications"
    if flags == 2:
        return 0.95, "2/3 verifications"
    return 1.0, "fully verified (email+phone+LinkedIn)"


def engagement_quality(cand: Candidate) -> tuple[float, str]:
    """interview_completion × saved_by_recruiters × github_activity (for AI Eng JD)."""
    s = cand.redrob_signals

    icr = s.interview_completion_rate
    icr_score = icr  # already 0-1

    saved_score = saturating(s.saved_by_recruiters_30d, threshold=10)

    if s.github_activity_score < 0:
        gh_score = 0.4  # no GitHub linked — soft penalty for engineering JD
        gh_ev = "no GitHub linked"
    else:
        gh_score = saturating(s.github_activity_score, threshold=60)
        gh_ev = f"GitHub {s.github_activity_score:.0f}/100"

    score = (icr_score + saved_score + gh_score) / 3.0
    ev = (
        f"interview_completion={icr:.2f}, saved_by_recruiters={s.saved_by_recruiters_30d}, "
        f"{gh_ev}"
    )
    return score, ev


ALL_BEHAVIOURAL_PROBES = [
    ("effectively_available", effectively_available),
    ("notice_period_curve", notice_period_curve),
    ("trust_modifier", trust_modifier),
    ("engagement_quality", engagement_quality),
]


def run_all(cand: Candidate) -> list[tuple[str, float, str]]:
    """Behavioural probes always return a score (used as multiplicative modifier),
    so we include all of them, not just non-zero."""
    return [
        (name, score, ev)
        for name, fn in ALL_BEHAVIOURAL_PROBES
        for score, ev in [fn(cand)]
    ]
