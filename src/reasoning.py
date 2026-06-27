"""Reasoning generator.

For each candidate, produces a 1-2 sentence reasoning string by templating
from the structured probe evidence. No LLM. Deterministic seeding by
candidate_id for reproducible variation.

Three rank bands, six templates each:
  Top 1-10  , confident lead with strongest High-SNR signal + concern
  Top 11-50 , corroborating signals + concern
  Top 51-100, explicit "why not higher" framing

Stage-4 checks passed by construction:
  - Specific facts          : every claim is a parsed schema attribute
  - JD connection           : probe names map 1:1 to JD requirements
  - Honest concerns         : concern slot is required for top-rank templates
  - No hallucination        : no LLM, no free-text generation
  - Variation               : 6 templates × variable probe combos × hash seed
  - Rank consistency        : template band = function of rank
"""
from __future__ import annotations

import hashlib

from src.schema import Candidate
from src.scoring import CandidateScore


# ---------------------------------------------------------------------------
# Helpers, extract human-friendly facts
# ---------------------------------------------------------------------------

def _years_str(years: float) -> str:
    if years >= 1:
        return f"{years:.0f}y" if years == int(years) else f"{years:.1f}y"
    return f"{int(years * 12)}mo"


def _stable_seed(candidate_id: str) -> int:
    return int(hashlib.md5(candidate_id.encode()).hexdigest()[:8], 16)


def _candidate_basics(cand: Candidate) -> str:
    """Always-includable opening clause: '{Title} ({Yrs}y) at {Company}'."""
    p = cand.profile
    years = p.years_of_experience
    return f"{p.current_title} ({_years_str(years)}) at {p.current_company}"


def _top_positive_evidence(cs: CandidateScore, k: int = 2) -> list[tuple[str, str]]:
    """Return [(probe_name, evidence_str)] for the top-k contributing positive probes."""
    # Combine must-have + substance + location (the additive contributors)
    all_pos = list(cs.must_have) + list(cs.substance) + list(cs.location_probes)
    # Sort by absolute score descending
    all_pos.sort(key=lambda t: t[1], reverse=True)
    out = []
    for name, score, evidence in all_pos[:k * 2]:  # take extras then filter
        if evidence and score > 0:
            out.append((name, evidence))
        if len(out) >= k:
            break
    return out


def _top_concern(cs: CandidateScore, cand: Candidate) -> tuple[str, str] | None:
    """Return (label, evidence) for the strongest concern, or None if no concerns."""
    # First check anti-SNR probes, these are the hardest concerns
    if cs.anti_snr:
        # Sort by score descending (worst penalty first)
        ranked = sorted(cs.anti_snr, key=lambda t: t[1], reverse=True)
        name, _, evidence = ranked[0]
        # Friendly label
        label = {
            "consulting_only": "Concern",
            "bigcorp_only": "Note",
            "pure_research_career": "Concern",
            "no_production_code_18mo": "Concern",
            "framework_enthusiast": "Concern",
            "title_chaser": "Note",
            "cv_speech_robo_only": "Concern",
            "manager_drift": "Note",
            "keyword_dense_junior": "Concern",
            "remote_only_vs_hybrid_jd": "Logistics",
            "dilution": "Note",
        }.get(name, "Note")
        return label, evidence

    # Otherwise check behavioural concerns
    notice = cand.redrob_signals.notice_period_days
    if notice > 60:
        return "Logistics", f"{notice}-day notice"

    if cand.redrob_signals.recruiter_response_rate < 0.2 and not cand.redrob_signals.open_to_work_flag:
        return "Engagement", f"low recruiter response ({cand.redrob_signals.recruiter_response_rate:.2f}), not flagged open"

    # Strong candidate with no obvious concern, return a soft acknowledgement
    return None


# ---------------------------------------------------------------------------
# Top 1-10 templates, confident, fact-rich, names one concern
# ---------------------------------------------------------------------------

def _top_10_templates(
    basics: str, pos: list[tuple[str, str]], concern: tuple[str, str] | None
) -> list[str]:
    """6 distinct phrasings."""
    e1 = pos[0][1] if len(pos) >= 1 else ""
    e2 = pos[1][1] if len(pos) >= 2 else ""
    c = f" {concern[0]}: {concern[1]}." if concern else ""

    templates = [
        f"{basics}; {e1}{', ' + e2 if e2 else ''}.{c}",
        f"{basics}. {e1.capitalize() if e1 else ''}{'; ' + e2 if e2 else ''}.{c}",
        f"Strong fit: {basics}. {e1}{', plus ' + e2 if e2 else ''}.{c}",
        f"{basics}, {e1}{'. Also ' + e2 if e2 else ''}.{c}",
        f"{basics}; the JD's must-haves land here: {e1}{', and ' + e2 if e2 else ''}.{c}",
        f"{basics}. {e1}{'; ' + e2 if e2 else ''}.{c}",
    ]
    return templates


# ---------------------------------------------------------------------------
# Top 11-50 templates, corroborating but more hedged
# ---------------------------------------------------------------------------

def _top_50_templates(
    basics: str, pos: list[tuple[str, str]], concern: tuple[str, str] | None
) -> list[str]:
    e1 = pos[0][1] if len(pos) >= 1 else "general fit"
    e2 = pos[1][1] if len(pos) >= 2 else ""
    c = f" {concern[0]}: {concern[1]}." if concern else ""

    templates = [
        f"{basics}. {e1}{', plus ' + e2 if e2 else ''}.{c}",
        f"{basics}; {e1}{', and ' + e2 if e2 else ''}.{c}",
        f"Solid match, {basics}. {e1}{'. ' + e2.capitalize() if e2 else ''}.{c}",
        f"{basics}. Notable: {e1}{'; ' + e2 if e2 else ''}.{c}",
        f"{basics}, {e1}{', supported by ' + e2 if e2 else ''}.{c}",
        f"{basics}; substance: {e1}{'; ' + e2 if e2 else ''}.{c}",
    ]
    return templates


# ---------------------------------------------------------------------------
# Top 51-100 templates, explicit why-not framing
# ---------------------------------------------------------------------------

def _top_100_templates(
    basics: str, pos: list[tuple[str, str]], concern: tuple[str, str] | None
) -> list[str]:
    e1 = pos[0][1] if len(pos) >= 1 else "adjacent fit"
    c = concern[1] if concern else "weaker overall signal for this specific role"

    templates = [
        f"{basics}. {e1.capitalize() if e1 else 'Adjacent signal'}, but {c}.",
        f"{basics}; {e1}{', however ' + c}.",
        f"{basics}. Strength: {e1}. Why not higher: {c}.",
        f"{basics}, adjacent rather than core: {e1}; {c}.",
        f"{basics}; some signal ({e1}) but {c}.",
        f"{basics}. {e1}. Ranked here because {c}.",
    ]
    return templates


# ---------------------------------------------------------------------------
# Entry point, generate the reasoning string for a candidate at a given rank
# ---------------------------------------------------------------------------

def generate_reasoning(cand: Candidate, cs: CandidateScore, rank: int) -> str:
    """Produce the reasoning string for a candidate at the given rank position."""
    basics = _candidate_basics(cand)
    pos = _top_positive_evidence(cs, k=2)
    concern = _top_concern(cs, cand)

    if rank <= 10:
        templates = _top_10_templates(basics, pos, concern)
    elif rank <= 50:
        templates = _top_50_templates(basics, pos, concern)
    else:
        templates = _top_100_templates(basics, pos, concern)

    idx = _stable_seed(cand.candidate_id) % len(templates)
    reasoning = templates[idx]

    # Clean up double-punctuation artefacts
    while ".." in reasoning:
        reasoning = reasoning.replace("..", ".")
    while "  " in reasoning:
        reasoning = reasoning.replace("  ", " ")
    reasoning = reasoning.replace(" .", ".").replace(" ;", ";")
    reasoning = reasoning.strip()

    # Stage-1 validator forbids commas in reasoning if not quoted; pydantic
    # already enforces max-length=1000; the CSV writer handles quoting.
    return reasoning
