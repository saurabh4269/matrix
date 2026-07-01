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
    """Return up to 3 bullet points explaining what kept this candidate from
    a higher rank. Deterministic, derived from probe values.

    vision.md's 'Why and Why Not' explainability — we already have the 'why'
    (the reasoning string + snr_high highlights). This is the 'why not'.

    Returns [] if nothing's holding them back (truly strong pick).
    """
    bullets: list[str] = []

    # 1. Anti-SNR is the loudest signal — surface the strongest finding even
    #    if it's already in main_risk so the user sees it framed as a ceiling.
    if cs.anti_snr:
        worst = max(cs.anti_snr, key=lambda t: t[1])
        if worst[1] > 0.3:
            labels = {
                "consulting_only": "Consulting-only history reduces product-velocity confidence.",
                "bigcorp_only": "Bigcorp-only history reduces zero-to-one confidence.",
                "pure_research_career": "Research-heavy career reduces production-shipping confidence.",
                "no_production_code_18mo": "No shipping work in the last 18 months.",
                "framework_enthusiast": "Skill list reads framework-heavy without matching production depth.",
                "title_chaser": "Short tenures across recent roles.",
                "cv_speech_robo_only": "Adjacent subdomain, not the JD's NLP / IR focus.",
                "manager_drift": "Recent roles trend manager-heavy, not hands-on.",
                "keyword_dense_junior": "Keyword density is high for the stated years of experience.",
                "remote_only_vs_hybrid_jd": "Remote-only against the JD's hybrid preference.",
                "dilution": "Most tenure is in non-relevant titles.",
            }
            bullets.append(labels.get(worst[0], f"{worst[0]} signal: {worst[2]}"))

    # 2. Weakest must-have. If a high-weight must-have probe scored low, that
    #    held the linear score down.
    if cs.must_have:
        weak_must = min(cs.must_have, key=lambda t: t[1])
        if weak_must[1] < 0.4:
            humanised = {
                "yoe_band_fit": "Years of experience outside the JD's preferred band.",
                "years_applied_ml_at_product_co": "Limited applied-ML tenure at a product company.",
                "production_deployment_evidence": "Production deployment evidence is thin.",
                "nlp_ir_focus": "NLP / IR focus is not central to their work history.",
                "vector_search_depth": "Vector search depth is implied but not specifically demonstrated.",
                "python_proficiency": "Python proficiency lower than expected for this role.",
            }.get(weak_must[0])
            if humanised:
                bullets.append(humanised)

    # 3. Behavioural drag — explicit if the modifier is pulling them down.
    if cs.behavioural_modifier < 0.7:
        bullets.append(
            f"Behavioural modifier × {cs.behavioural_modifier:.2f} (notice, responsiveness, "
            "or activity is dampening the composite)."
        )

    # 4. Substance soft-spot
    if cs.substance:
        weak_sub = min(cs.substance, key=lambda t: t[1])
        if weak_sub[1] < 0.3 and weak_sub[0] == "description_specificity":
            bullets.append("Career descriptions are thin on specifics — hard to verify claims.")

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
