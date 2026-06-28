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
