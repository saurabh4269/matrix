"""Per-candidate prescriptive next action + main risk.

For each top-100 candidate, derive a one-line recruiter recommendation from
their probe profile. Borrowed from TellTale's per-opportunity 'next action'
column: tells the recruiter *what to do* with this candidate, not just the
rank.

Pure deterministic rules over CandidateScore fields. No LLM, no network.
"""
from __future__ import annotations

from src.scoring import ANTI_SNR_WEIGHTS, CandidateScore


def next_action(cs: CandidateScore, current_title: str = "") -> str:
    """Return a short recruiter-facing recommendation."""
    title = (current_title or "").lower()

    # Strong availability concerns dominate
    avail = cs.behavioural_modifier
    notice_probe = next((s for n, s, _ in cs.behavioural if n == "notice_period_curve"), 1.0)
    if avail < 0.25:
        return "Reach out, but flag low responsiveness. Set lower expectations."
    if notice_probe < 0.5:
        return "Phone-screen first to confirm timing fits the role's start window."

    # Strong skill profile + high availability → fast-track
    strong_must = sum(1 for _, s, _ in cs.must_have if s > 0.5)
    if cs.confidence == "high" and strong_must >= 4 and avail > 0.6:
        return "Send the technical screen this week. Fast-track candidate."
    if cs.confidence == "high" and strong_must >= 3:
        return "Send the technical screen. Top-of-funnel candidate."

    # Medium confidence + relevant role
    if cs.confidence == "medium" and ("engineer" in title or "scientist" in title):
        return "Phone-screen first to verify production deployment depth."

    # Anti-SNR concerns
    major_anti = sorted(
        [(n, s) for n, s, _ in cs.anti_snr if s > 0.3 and ANTI_SNR_WEIGHTS.get(n, 0) >= 0.5],
        key=lambda x: -x[1],
    )
    if major_anti:
        worst = major_anti[0][0]
        if worst == "consulting_only":
            return "Skip. Consulting-only career conflicts with the JD's explicit no."
        if worst == "framework_enthusiast":
            return "Skip unless follow-up reveals real production work behind the frameworks."
        if worst == "cv_speech_robo_only":
            return "Skip. Wrong subdomain for this role."
        if worst == "no_production_code_18mo":
            return "Skip unless they can show recent shipping work in a sample project."
        if worst == "title_chaser":
            return "Phone-screen with a focus on their reasons for short tenures."
        return "Phone-screen with care. Anti-signal concerns to verify."

    # Default — adjacent fit
    return "Add to a future-roles list. Adjacent fit, not core."


def main_risk(cs: CandidateScore) -> str:
    """Return the single biggest concern, or empty string if none."""
    # The strongest anti-SNR finding
    if cs.anti_snr:
        ranked = sorted(cs.anti_snr, key=lambda t: -t[1])
        name, _, evidence = ranked[0]
        labels = {
            "consulting_only": "Consulting-only career",
            "bigcorp_only": "Bigcorp-only career",
            "pure_research_career": "Research-only background",
            "no_production_code_18mo": "No recent production code",
            "framework_enthusiast": "Framework-heavy, low production",
            "title_chaser": "Short tenures",
            "cv_speech_robo_only": "Adjacent subdomain (CV/speech), not NLP/IR",
            "manager_drift": "Manager-heavy recent roles",
            "keyword_dense_junior": "Keyword-dense for years of experience",
            "remote_only_vs_hybrid_jd": "Remote-only against hybrid JD",
            "dilution": "Mostly non-relevant tenure",
        }
        return f"{labels.get(name, name)}: {evidence}"

    # Behavioural concerns
    if cs.behavioural_modifier < 0.4:
        return "Effectively unavailable: low response rate, dormant, or long notice"

    # Look at behavioural breakdown for the weakest dimension
    behav_min = min(((n, s) for n, s, _ in cs.behavioural), key=lambda t: t[1], default=None)
    if behav_min and behav_min[1] < 0.5:
        labels = {
            "effectively_available": "Limited availability or low responsiveness",
            "notice_period_curve": "Long notice period",
            "trust_modifier": "Unverified contact details",
            "engagement_quality": "Limited engagement history on the platform",
            "closability": "Low historical offer-acceptance rate",
        }
        return labels.get(behav_min[0], "Behavioural concern")

    return ""


# ---------------------------------------------------------------------------
# HRMS routing — vision.md §4 (HRMS Data Contract).
#
# The structured.jsonl beside the submission CSV mimics standard HRMS
# webhook payload shapes (Greenhouse / Workday style) so downstream systems
# can route on `next_step` without parsing prose. Pure-rule mapping over the
# same CandidateScore the next_action() text uses, so the prescriptive
# string and the structured action never disagree.
# ---------------------------------------------------------------------------

def why_not_higher(cs: CandidateScore) -> list[str]:
    """Up to 3 plain-English reasons this candidate didn't rank higher.

    Deterministic, derived from probe values. Never uses internal probe
    names or math jargon in the strings we return — every sentence should
    read naturally to a recruiter who has never opened our code.

    Returns [] if nothing's holding them back (truly strong pick).
    """
    bullets: list[str] = []

    # 1. Anti-SNR — the strongest concern that fired.
    if cs.anti_snr:
        worst = max(cs.anti_snr, key=lambda t: t[1])
        if worst[1] > 0.3:
            labels = {
                "consulting_only": "Their history is all consulting-firm work, so it's hard to gauge product-shipping speed.",
                "bigcorp_only": "Their history is all large-company work — untested at startup pace.",
                "pure_research_career": "The career leans toward academic research, light on production shipping.",
                "no_production_code_18mo": "No shipping work in the last 18 months.",
                "framework_enthusiast": "The skill list leans on frameworks without the production depth to back them up.",
                "title_chaser": "Short tenures across their recent roles.",
                "cv_speech_robo_only": "They work in a related subfield, not the JD's core NLP / IR area.",
                "manager_drift": "Recent roles have been more managerial than hands-on.",
                "keyword_dense_junior": "Their skill list is unusually dense for the years of experience shown.",
                "remote_only_vs_hybrid_jd": "They're remote-only, and this JD is hybrid.",
                "dilution": "Most of the career tenure is in unrelated titles.",
            }
            bullets.append(labels.get(worst[0], worst[2]))

    # 2. Weakest must-have — the strongest requirement they didn't clearly meet.
    if cs.must_have:
        weak_must = min(cs.must_have, key=lambda t: t[1])
        if weak_must[1] < 0.4:
            humanised = {
                "yoe_band_fit": "Their years of experience sit outside the JD's preferred band.",
                "years_applied_ml_at_product_co": "Limited applied-ML time at a product company.",
                "production_deployment_evidence": "Production-deployment evidence is thin.",
                "nlp_ir_focus": "NLP / IR isn't the centre of their work history.",
                "vector_search_depth": "Vector-search depth is implied but not clearly demonstrated.",
                "python_proficiency": "Python looks weaker than the role expects.",
            }.get(weak_must[0])
            if humanised:
                bullets.append(humanised)

    # 3. Behavioural drag — surface the specific weak dimension, not the
    #    aggregate multiplier. Recruiters care WHY availability is soft.
    if cs.behavioural_modifier < 0.7:
        behav_labels = {
            "notice_period_curve":     "Long notice period — they won't start soon.",
            "effectively_available":   "Not very active on the platform right now.",
            "engagement_quality":      "Light engagement history — they may not be actively looking.",
            "trust_modifier":          "Contact details aren't fully verified — harder to reach.",
            "closability":             "Their offer-acceptance history is on the lower side.",
        }
        # Pick the single weakest behavioural dimension
        weakest = None
        for name, score, _ev in cs.behavioural:
            if name in behav_labels and (weakest is None or score < weakest[1]):
                weakest = (name, score)
        if weakest and weakest[1] < 0.6:
            bullets.append(behav_labels[weakest[0]])
        else:
            bullets.append(
                "Availability is softer than typical — notice, responsiveness, or activity."
            )

    # 4. Substance soft-spot
    if cs.substance:
        weak_sub = min(cs.substance, key=lambda t: t[1])
        if weak_sub[1] < 0.3 and weak_sub[0] == "description_specificity":
            bullets.append("Their career descriptions are light on specifics — hard to verify claims.")

    return bullets[:3]


_HRMS_STEPS = {
    "TRIGGER_TECHNICAL_ASSESSMENT": "tech-screen-async",
    "SEND_RECRUITER_SCREEN":        "recruiter-screen-15m",
    "PHONE_SCREEN_TIMING":          "phone-screen-timing",
    "MANUAL_REVIEW":                "manual-review-needed",
    "SKIP_HARD_NO":                 "auto-decline",
}


def hrms_routing_action(cs: CandidateScore, jd_slug: str = "ai_engineer") -> dict[str, str]:
    """Map a CandidateScore to an HRMS routing payload.

    Returns:
        {next_step, assessment_id, priority, sla_hours}

    Decision tree matches the prose recommendation from next_action() so the
    two are always consistent.
    """
    avail = cs.behavioural_modifier
    notice_probe = next((s for n, s, _ in cs.behavioural if n == "notice_period_curve"), 1.0)
    strong_must = sum(1 for _, s, _ in cs.must_have if s > 0.5)
    major_anti = sorted(
        [(n, s) for n, s, _ in cs.anti_snr if s > 0.3 and ANTI_SNR_WEIGHTS.get(n, 0) >= 0.5],
        key=lambda x: -x[1],
    )

    # Hard-no anti-SNR → auto-decline
    if major_anti:
        worst = major_anti[0][0]
        if worst in {"consulting_only", "cv_speech_robo_only", "no_production_code_18mo"}:
            return {
                "next_step": "SKIP_HARD_NO",
                "assessment_id": "",
                "priority": "low",
                "sla_hours": "48",
                "reason_code": f"anti_snr:{worst}",
            }
        return {
            "next_step": "MANUAL_REVIEW",
            "assessment_id": "",
            "priority": "low",
            "sla_hours": "72",
            "reason_code": f"anti_snr:{worst}",
        }

    # Availability blocks → phone-screen first
    if avail < 0.25 or notice_probe < 0.5:
        return {
            "next_step": "PHONE_SCREEN_TIMING",
            "assessment_id": f"timing-{jd_slug}-v1",
            "priority": "medium",
            "sla_hours": "48",
            "reason_code": "availability_constraint",
        }

    # High-confidence + strong must-haves → fast-track to assessment
    if cs.confidence == "high" and strong_must >= 3:
        return {
            "next_step": "TRIGGER_TECHNICAL_ASSESSMENT",
            "assessment_id": f"tech-{jd_slug}-v1",
            "priority": "high",
            "sla_hours": "24",
            "reason_code": "fast_track",
        }

    # Medium confidence → recruiter screen
    if cs.confidence == "medium":
        return {
            "next_step": "SEND_RECRUITER_SCREEN",
            "assessment_id": f"recruiter-{jd_slug}-v1",
            "priority": "medium",
            "sla_hours": "48",
            "reason_code": "medium_confidence",
        }

    # Low confidence / adjacent fit
    return {
        "next_step": "MANUAL_REVIEW",
        "assessment_id": "",
        "priority": "low",
        "sla_hours": "72",
        "reason_code": "adjacent_fit",
    }
