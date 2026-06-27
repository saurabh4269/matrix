"""Behavioural availability probes, multiplicative modifier on the overall score.

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
    """Multiplicative combination of multiple availability signals.

    open_to_work × min(1, response/0.3) × decay(last_active, 60d)
        × response_speed × actively_searching
    """
    s = cand.redrob_signals
    open_factor = 1.0 if s.open_to_work_flag else 0.6

    resp_factor = min(1.0, s.recruiter_response_rate / 0.3) if s.recruiter_response_rate > 0 else 0.3

    days = _days_since(s.last_active_date)
    decay = math.exp(-days / 60.0)  # half-life ~42 days

    # Response speed: fast responders are more engaged.
    # 0-12h = 1.0, 12-48h = 0.95, 48-168h = 0.85, >168h = 0.7
    rt = s.avg_response_time_hours
    if rt <= 0:
        rt_factor = 0.9  # unknown
    elif rt <= 12:
        rt_factor = 1.0
    elif rt <= 48:
        rt_factor = 0.95
    elif rt <= 168:
        rt_factor = 0.85
    else:
        rt_factor = 0.7

    # Actively searching: applications_submitted_30d > 0 = in the market right now
    apps = s.applications_submitted_30d
    if apps >= 5:
        search_factor = 1.15  # very active
    elif apps >= 1:
        search_factor = 1.05  # active
    else:
        search_factor = 0.95  # passive (still keeps them in play)

    score = open_factor * resp_factor * decay * rt_factor * search_factor
    score = min(1.2, score)  # cap upside
    ev = (
        f"open_to_work={s.open_to_work_flag}, response_rate={s.recruiter_response_rate:.2f} "
        f"(avg {rt:.0f}h), last_active={days}d ago, {apps} application(s) this month"
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
    """Verified contact + LinkedIn, small but real bonus."""
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
    """interview_completion × saved_by_recruiters × github_activity × market_pull (profile_views).

    The first three are about the candidate's reliability + engineering presence;
    profile_views_received_30d is the market's revealed interest in this candidate.
    """
    s = cand.redrob_signals

    icr_score = s.interview_completion_rate  # 0-1 already

    saved_score = saturating(s.saved_by_recruiters_30d, threshold=10)

    if s.github_activity_score < 0:
        gh_score = 0.4  # no GitHub linked, soft penalty for engineering JD
        gh_ev = "no GitHub linked"
    else:
        gh_score = saturating(s.github_activity_score, threshold=60)
        gh_ev = f"GitHub {s.github_activity_score:.0f}/100"

    # Profile views received, recruiter-revealed interest. Saturates fast.
    views_score = saturating(s.profile_views_received_30d, threshold=20)

    score = (icr_score + saved_score + gh_score + views_score) / 4.0
    ev = (
        f"interview_completion={icr_score:.2f}, saved_by_recruiters={s.saved_by_recruiters_30d}, "
        f"{gh_ev}, profile_views={s.profile_views_received_30d}"
    )
    return score, ev


def closability(cand: Candidate) -> tuple[float, str]:
    """Offer-acceptance history. Hits with -1 (no history) get a neutral 0.9.

    Strong closability is rare but a real positive, a candidate who accepts
    1.0 of the offers they've received is unusually predictable to close.
    """
    s = cand.redrob_signals
    rate = s.offer_acceptance_rate
    if rate < 0:
        return 0.9, "no offer history"
    if rate >= 0.7:
        return 1.0, f"offer acceptance {rate:.0%}"
    if rate >= 0.4:
        return 0.85, f"offer acceptance {rate:.0%}"
    return 0.7, f"offer acceptance {rate:.0%}, low historical close rate"


ALL_BEHAVIOURAL_PROBES = [
    ("effectively_available", effectively_available),
    ("notice_period_curve", notice_period_curve),
    ("trust_modifier", trust_modifier),
    ("engagement_quality", engagement_quality),
    ("closability", closability),
]


def run_all(cand: Candidate) -> list[tuple[str, float, str]]:
    """Behavioural probes always return a score (used as multiplicative modifier),
    so we include all of them, not just non-zero."""
    return [
        (name, score, ev)
        for name, fn in ALL_BEHAVIOURAL_PROBES
        for score, ev in [fn(cand)]
    ]
