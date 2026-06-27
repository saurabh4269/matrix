"""Substance / trust probes — high-SNR signals that defeat the keyword-stuffer trap.

These look at the *substance* of descriptions: do they name specific systems,
use cause-effect language, demonstrate production thinking? AI-tailored
resumes have keywords; they don't have substance.
"""
from __future__ import annotations

from src.heuristics import PRODUCT_COMPANIES, BIGCORP_SIZE, SMALL_MID_SIZES
from src.probes._text import (
    SPECIFIC_TECHNICAL_ENTITIES,
    NARRATIVE_CONNECTIVES,
    PRODUCTION_VERBS,
    HANDS_ON_VERBS,
    RESEARCH_VERBS,
    count_phrase_hits,
    distinct_phrase_hits,
    count_tokens,
    saturating,
)
from src.schema import Candidate


def _all_descriptions(cand: Candidate) -> str:
    return " ".join(r.description or "" for r in cand.career_history)


def description_specificity(cand: Candidate) -> tuple[float, str]:
    """Count of distinct specific named technical entities per 100 tokens.

    AI-tailored resumes have generic verbs; real engineers name specific systems.
    High-SNR signal.
    """
    text = _all_descriptions(cand)
    n_tokens = count_tokens(text)
    if n_tokens < 50:
        return 0.0, ""

    distinct = distinct_phrase_hits(text, SPECIFIC_TECHNICAL_ENTITIES)
    density = distinct / (n_tokens / 100.0)  # entities per 100 tokens

    # density of 3+ is high. Saturate at 6.
    score = saturating(density, threshold=6.0)
    return score, f"{distinct} specific systems named, density {density:.1f}/100 tokens"


def narrative_arc_density(cand: Candidate) -> tuple[float, str]:
    """Cause-effect connectives per role. Real engineers describe problem→fix arcs."""
    n_roles = len(cand.career_history)
    if n_roles == 0:
        return 0.0, ""
    text = _all_descriptions(cand)
    hits = count_phrase_hits(text, NARRATIVE_CONNECTIVES)
    if hits == 0:
        return 0.0, ""
    per_role = hits / n_roles
    score = saturating(per_role, threshold=2.0)
    return score, f"{hits} narrative connective(s) across {n_roles} role(s)"


def production_emphasis(cand: Candidate) -> tuple[float, str]:
    """Production-shipping language density in recent role descriptions."""
    recent = cand.career_history[:3]
    if not recent:
        return 0.0, ""
    text = " ".join(r.description or "" for r in recent)
    hits = count_phrase_hits(text, PRODUCTION_VERBS)
    if hits == 0:
        return 0.0, ""
    score = saturating(hits, threshold=5)
    return score, f"{hits} production-shipping verb(s) in recent roles"


def verification_ratio(cand: Candidate) -> tuple[float, str]:
    """Fraction of claimed skills that have a verified assessment score.

    High-SNR meta-signal — candidates who have actually tested their claims.
    """
    n_claimed = len(cand.skills)
    if n_claimed == 0:
        return 0.0, ""
    n_assessed = len(cand.redrob_signals.skill_assessment_scores)
    if n_assessed == 0:
        return 0.0, ""
    ratio = min(1.0, n_assessed / n_claimed)
    # Also weight by the actual scores — high scores boost
    avg_score = (
        sum(cand.redrob_signals.skill_assessment_scores.values()) / n_assessed
        if n_assessed else 0
    ) / 100.0
    score = saturating(ratio * (0.5 + 0.5 * avg_score), threshold=0.5)
    return score, f"{n_assessed}/{n_claimed} skills verified, avg {avg_score*100:.0f}/100"


def acceleration(cand: Candidate) -> tuple[float, str]:
    """Promotion intervals shrinking over career — career acceleration."""
    roles = cand.career_history
    if len(roles) < 3:
        return 0.0, ""
    # Compare avg of first half vs second half (most recent)
    half = len(roles) // 2
    recent = roles[:half]  # most recent
    older = roles[half:]
    recent_avg = sum(r.duration_months for r in recent) / len(recent)
    older_avg = sum(r.duration_months for r in older) / len(older)
    if older_avg <= 0:
        return 0.0, ""
    # Acceleration = recent durations shorter (faster moves)
    ratio = older_avg / recent_avg
    if ratio < 1.2:  # not really accelerating
        return 0.0, ""
    score = saturating((ratio - 1.0) / 1.0, threshold=1.0)
    return score, f"recent avg tenure {recent_avg:.0f}mo vs older avg {older_avg:.0f}mo"


def summary_thoughtfulness(cand: Candidate) -> tuple[float, str]:
    """JD says 'we work async-first and write a lot'. Summary length + specificity proxy."""
    summary = cand.profile.summary or ""
    n_tokens = count_tokens(summary)
    if n_tokens < 30:
        return 0.0, ""
    # Lower bound at 30 tokens, saturate at 150 (substantive paragraph)
    length_score = saturating(n_tokens, threshold=150)
    # Bonus if the summary itself contains specific technical entities
    specificity = distinct_phrase_hits(summary, SPECIFIC_TECHNICAL_ENTITIES)
    spec_bonus = saturating(specificity, threshold=4)
    score = 0.6 * length_score + 0.4 * spec_bonus
    return score, f"summary {n_tokens} tokens, {specificity} specific term(s)"


def company_stage_alignment(cand: Candidate) -> tuple[float, str]:
    """Redrob is Series-A (~50-200 size). Boost candidates with recent small/mid-co experience."""
    if not cand.career_history:
        return 0.0, ""
    recent = cand.career_history[:3]
    small_mid_months = sum(
        r.duration_months for r in recent if r.company_size in SMALL_MID_SIZES
    )
    total = sum(r.duration_months for r in recent)
    if total == 0:
        return 0.0, ""
    ratio = small_mid_months / total
    if ratio < 0.3:
        return 0.0, ""
    score = saturating(ratio, threshold=0.8)
    return score, f"{ratio:.0%} of recent tenure at 11–500 size companies"


def shipper_vs_researcher_ratio(cand: Candidate) -> tuple[float, str]:
    """JD: 'tilt slightly toward shipper than researcher'."""
    text = _all_descriptions(cand)
    if not text:
        return 0.0, ""
    ship = count_phrase_hits(text, HANDS_ON_VERBS)
    research = count_phrase_hits(text, RESEARCH_VERBS)
    if ship + research == 0:
        return 0.0, ""
    ratio = ship / (ship + research)
    if ratio < 0.5:
        return 0.0, ""
    score = saturating((ratio - 0.5) / 0.5, threshold=1.0)
    return score, f"{ship} hands-on vs {research} research verbs (shipper ratio {ratio:.0%})"


def named_employer_micro_boost(cand: Candidate) -> tuple[float, str]:
    """Small boost for known ML/IR-strong employers. +0.05 per, capped."""
    known = {
        "google", "meta", "facebook", "amazon", "apple", "microsoft",
        "stripe", "shopify", "airbnb", "pinterest", "spotify",
        "openai", "anthropic", "databricks", "snowflake", "scale ai",
        "linkedin", "twitter", "netflix", "uber",
    }
    hits = sum(
        1 for r in cand.career_history
        if r.company.strip().lower() in known
    )
    if hits == 0:
        return 0.0, ""
    score = min(0.3, 0.1 * hits)  # cap micro-boost
    return score, f"{hits} role(s) at known ML/IR employer(s)"


ALL_SUBSTANCE_PROBES = [
    ("description_specificity", description_specificity),
    ("narrative_arc_density", narrative_arc_density),
    ("production_emphasis", production_emphasis),
    ("verification_ratio", verification_ratio),
    ("acceleration", acceleration),
    ("summary_thoughtfulness", summary_thoughtfulness),
    ("company_stage_alignment", company_stage_alignment),
    ("shipper_vs_researcher_ratio", shipper_vs_researcher_ratio),
    ("named_employer_micro_boost", named_employer_micro_boost),
]


def run_all(cand: Candidate) -> list[tuple[str, float, str]]:
    return [
        (name, score, ev)
        for name, fn in ALL_SUBSTANCE_PROBES
        for score, ev in [fn(cand)]
        if score > 0
    ]
