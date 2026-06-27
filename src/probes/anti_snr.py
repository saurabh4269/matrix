"""Anti-SNR probes, JD-explicit disqualifiers and red flags.

The JD names specific disqualifiers under "Things we explicitly do NOT want".
Each disqualifier here is encoded as a probe that returns (score, evidence)
where score is in [0, 1]:
  - 1.0 = the disqualifier strongly applies (heavy penalty)
  - 0.0 = does not apply
  - intermediate = partial (e.g., career mostly consulting but not entirely)

These are used in the final scorer as a multiplicative penalty:
    anti_snr_penalty = ∏(1 − probe_score)

So a probe firing at 1.0 zeros the candidate's overall score; firing at 0.3
multiplies by 0.7.

Per the spec, these are NEVER hard filters, recall is precious. Heavy penalty
only.
"""
from __future__ import annotations

import re

from src.heuristics import (
    CONSULTING_FIRMS,
    BIGCORP_SIZE,
    has_ml_title_anywhere,
)
from src.schema import Candidate


# ---------------------------------------------------------------------------
# Consulting-only career, JD's hardest no
# ---------------------------------------------------------------------------

def consulting_only(cand: Candidate) -> tuple[float, str]:
    """Every entry in career_history is at a consulting firm."""
    if not cand.career_history:
        return 0.0, ""
    companies = [r.company.strip().lower() for r in cand.career_history]
    in_consulting = [c in CONSULTING_FIRMS for c in companies]
    if all(in_consulting):
        return 1.0, f"entire career at consulting firms ({len(companies)} roles)"
    # Soft signal: mostly-consulting (≥75% of tenure in consulting)
    total_months = sum(r.duration_months for r in cand.career_history)
    consulting_months = sum(
        r.duration_months
        for r in cand.career_history
        if r.company.strip().lower() in CONSULTING_FIRMS
    )
    if total_months > 0 and consulting_months / total_months >= 0.75:
        return 0.5, f"{consulting_months/total_months:.0%} of career at consulting firms"
    return 0.0, ""


# ---------------------------------------------------------------------------
# Bigcorp-only career, JD soft no (Google/Meta well-scoped-role mismatch)
# ---------------------------------------------------------------------------

def bigcorp_only(cand: Candidate) -> tuple[float, str]:
    """Every recent role at a 10001+ company."""
    if not cand.career_history:
        return 0.0, ""
    if all(r.company_size == BIGCORP_SIZE for r in cand.career_history):
        return 0.7, f"entire career at 10001+ companies ({len(cand.career_history)} roles)"
    # Looking at just last 3 roles
    recent = cand.career_history[:3]
    if recent and all(r.company_size == BIGCORP_SIZE for r in recent):
        return 0.4, "all recent roles at 10001+ companies"
    return 0.0, ""


# ---------------------------------------------------------------------------
# Pure-research career, JD's first explicit hard no
# ---------------------------------------------------------------------------

_DEPLOYMENT_VERBS_RE = re.compile(
    r"\b(deploy(ed|ment)?|production|in prod|shipped|users|"
    r"a/b|ab[\s\-]?test|rolled[\s\-]?out|launched|live|api|service)\b",
    re.IGNORECASE,
)

_RESEARCH_ORG_RE = re.compile(
    r"\b(research|lab|labs|university|institute|academia|cnrs|"
    r"max planck|allen institute|google research|microsoft research|"
    r"deepmind|fair)\b",
    re.IGNORECASE,
)


def pure_research_career(cand: Candidate) -> tuple[float, str]:
    """All career entries at research-only orgs AND zero deployment verbs anywhere."""
    if not cand.career_history:
        return 0.0, ""

    research_only = all(
        _RESEARCH_ORG_RE.search(r.company) or _RESEARCH_ORG_RE.search(r.industry or "")
        for r in cand.career_history
    )
    all_text = " ".join(r.description or "" for r in cand.career_history)
    no_deployment = not _DEPLOYMENT_VERBS_RE.search(all_text)

    if research_only and no_deployment:
        return 1.0, "entire career at research orgs, no deployment evidence"
    if research_only:
        return 0.4, "entire career at research orgs (some deployment verbs)"
    return 0.0, ""


# ---------------------------------------------------------------------------
# No production code in last 18 months, JD says they will not move forward
# ---------------------------------------------------------------------------

_HANDS_ON_VERBS_RE = re.compile(
    r"\b(wrote|built|shipped|deployed|implemented|coded|developed|"
    r"engineered|designed|prototyped|integrated|refactored|"
    r"debugged|optimized|tuned|trained|fine[\s\-]?tuned)\b",
    re.IGNORECASE,
)


def no_production_code_18mo(cand: Candidate) -> tuple[float, str]:
    """Most recent role has no hands-on verbs in description. Proxy for the JD's
    "haven't written production code in 18 months" disqualifier."""
    if not cand.career_history:
        return 0.0, ""
    # Look at all roles in last 18 months (sort by recency; current first)
    recent = [r for r in cand.career_history if r.is_current or r.duration_months <= 18]
    if not recent:
        recent = cand.career_history[:1]
    recent_text = " ".join(r.description or "" for r in recent)
    if not _HANDS_ON_VERBS_RE.search(recent_text):
        return 0.8, "no hands-on/shipping verbs in recent role descriptions"
    return 0.0, ""


# ---------------------------------------------------------------------------
# Framework enthusiast, JD's explicit anti-LangChain-tutorial signal
# ---------------------------------------------------------------------------

_FRAMEWORK_SKILLS = {
    "langchain", "llamaindex", "llama-index", "haystack",
    "autogen", "crewai", "agentops",
}


def framework_enthusiast(cand: Candidate) -> tuple[float, str]:
    """Framework-named skills with low tenure AND no corresponding production
    system in description text."""
    framework_skills = [
        s for s in cand.skills
        if s.name.strip().lower() in _FRAMEWORK_SKILLS
    ]
    if not framework_skills:
        return 0.0, ""

    # All framework skills are recent (≤12 months) and very recent (≤6mo)
    avg_dur = sum(s.duration_months for s in framework_skills) / len(framework_skills)
    if avg_dur > 12:
        return 0.0, ""

    # And no production system mentioned in description text
    all_desc = " ".join(r.description or "" for r in cand.career_history).lower()
    has_production = any(
        kw in all_desc
        for kw in ["production", "shipped", "users", "scale", "deployed", "in prod"]
    )
    if not has_production:
        return 0.7, (
            f"{len(framework_skills)} framework-named skill(s) avg "
            f"{avg_dur:.0f}mo, no production evidence"
        )
    return 0.3, f"{len(framework_skills)} recent framework skills"


# ---------------------------------------------------------------------------
# Title-chaser, last 3 roles each < 18 months
# ---------------------------------------------------------------------------

def title_chaser(cand: Candidate) -> tuple[float, str]:
    """Avg tenure of last 3 roles < 18 months."""
    recent_3 = cand.career_history[:3]
    if len(recent_3) < 3:
        return 0.0, ""
    avg_dur = sum(r.duration_months for r in recent_3) / 3
    if avg_dur < 18:
        return 0.5, f"avg tenure of last 3 roles: {avg_dur:.0f}mo"
    return 0.0, ""


# ---------------------------------------------------------------------------
# CV/Speech/Robotics specialist without NLP/IR, JD will not move forward
# ---------------------------------------------------------------------------

_CV_SPEECH_ROBO_RE = re.compile(
    r"\b(computer[\s\-]?vision|cv\s+engineer|image[\s\-]?classification|"
    r"object[\s\-]?detection|segmentation|speech[\s\-]?recognition|"
    r"asr|tts|text[\s\-]?to[\s\-]?speech|robotics|slam|"
    r"autonomous[\s\-]?vehicle|lidar)\b",
    re.IGNORECASE,
)

_NLP_IR_TITLE_RE = re.compile(
    r"\b(nlp|natural[\s\-]?language|information[\s\-]?retrieval|"
    r"search|ranking|retrieval|recommendation|relevance|text|"
    r"applied[\s\-]?scientist[\s\w]*nlp)\b",
    re.IGNORECASE,
)


def cv_speech_robo_only(cand: Candidate) -> tuple[float, str]:
    """Titles dominated by CV/speech/robotics AND no NLP/IR title anywhere."""
    titles_text = " ".join(
        r.title or "" for r in cand.career_history
    ) + " " + (cand.profile.current_title or "")
    descs_text = " ".join(r.description or "" for r in cand.career_history)

    has_cv_speech = bool(_CV_SPEECH_ROBO_RE.search(titles_text + " " + descs_text))
    has_nlp_ir = bool(_NLP_IR_TITLE_RE.search(titles_text)) or "retrieval" in descs_text.lower()

    if has_cv_speech and not has_nlp_ir:
        return 0.6, "career dominated by CV/speech/robotics, no NLP/IR exposure"
    return 0.0, ""


# ---------------------------------------------------------------------------
# Manager-drift, JD wants hands-on, not "just architect / tech-lead"
# ---------------------------------------------------------------------------

_MANAGER_VERBS_RE = re.compile(
    r"\b(led|managed|owned|directed|oversaw|coordinated|"
    r"mentored|architected|strategized|stakeholders)\b",
    re.IGNORECASE,
)


def manager_drift(cand: Candidate) -> tuple[float, str]:
    """Recent roles dominated by manager verbs and short on hands-on verbs."""
    recent = cand.career_history[:2]
    if not recent:
        return 0.0, ""
    text = " ".join(r.description or "" for r in recent)
    mgr_count = len(_MANAGER_VERBS_RE.findall(text))
    hands_count = len(_HANDS_ON_VERBS_RE.findall(text))
    if mgr_count >= 4 and hands_count <= 1:
        return 0.5, f"{mgr_count} manager-verbs vs {hands_count} hands-on verbs in recent roles"
    return 0.0, ""


# ---------------------------------------------------------------------------
# Keyword-dense junior, high JD-keyword density paired with low YoE
# ---------------------------------------------------------------------------

def keyword_dense_junior(cand: Candidate) -> tuple[float, str]:
    """≥6 JD-relevant skills but <4 years of experience, trap signature."""
    from src.heuristics import count_jd_keyword_skills

    n_kw = count_jd_keyword_skills(cand)
    yoe = cand.profile.years_of_experience
    if n_kw >= 6 and yoe < 4:
        return 0.6, f"{n_kw} JD-keyword skills with only {yoe:.1f}y experience"
    if n_kw >= 4 and yoe < 2:
        return 0.4, f"{n_kw} JD-keyword skills with {yoe:.1f}y experience"
    return 0.0, ""


# ---------------------------------------------------------------------------
# Remote-only vs hybrid JD
# ---------------------------------------------------------------------------

def remote_only_vs_hybrid_jd(cand: Candidate) -> tuple[float, str]:
    """JD is hybrid Pune/Noida. Remote-only AND can't relocate = soft mismatch."""
    s = cand.redrob_signals
    if s.preferred_work_mode == "remote" and not s.willing_to_relocate:
        # If they're already in an Indian metro the work_mode might still match
        # the hybrid requirement. But if they're explicitly remote-only AND not
        # willing to relocate, that's a mismatch with hybrid Pune/Noida.
        loc = (cand.profile.location or "").lower()
        country = (cand.profile.country or "").lower()
        if country != "india":
            return 0.5, "remote-only, not willing to relocate, currently outside India"
        if not any(
            city in loc for city in ["pune", "noida", "delhi", "ncr", "gurugram", "gurgaon"]
        ):
            return 0.3, "remote-only, not willing to relocate"
    return 0.0, ""


# ---------------------------------------------------------------------------
# Dilution, generic engineering years ≫ relevant ML years
# ---------------------------------------------------------------------------

def dilution(cand: Candidate) -> tuple[float, str]:
    """High generic-tenure to relevant-tenure ratio. The aerospace dilemma."""
    from src.heuristics import _ML_TITLE_RE

    total_months = sum(r.duration_months for r in cand.career_history)
    relevant_months = sum(
        r.duration_months for r in cand.career_history
        if _ML_TITLE_RE.search(r.title or "")
    )
    if total_months < 24 or relevant_months == 0:
        # Not enough history to dilute, or no ML titles at all
        # (the other probes, consulting_only, dilution doesn't add signal here)
        return 0.0, ""
    ratio = relevant_months / total_months
    if ratio < 0.2:
        return 0.4, f"only {ratio:.0%} of career in ML titles"
    if ratio < 0.4:
        return 0.2, f"only {ratio:.0%} of career in ML titles"
    return 0.0, ""


# ---------------------------------------------------------------------------
# Aggregate caller
# ---------------------------------------------------------------------------

ALL_ANTI_SNR_PROBES = [
    ("consulting_only", consulting_only),
    ("bigcorp_only", bigcorp_only),
    ("pure_research_career", pure_research_career),
    ("no_production_code_18mo", no_production_code_18mo),
    ("framework_enthusiast", framework_enthusiast),
    ("title_chaser", title_chaser),
    ("cv_speech_robo_only", cv_speech_robo_only),
    ("manager_drift", manager_drift),
    ("keyword_dense_junior", keyword_dense_junior),
    ("remote_only_vs_hybrid_jd", remote_only_vs_hybrid_jd),
    ("dilution", dilution),
]


def run_all(cand: Candidate) -> list[tuple[str, float, str]]:
    """Run every anti-SNR probe. Returns [(name, score, evidence)] for ones that fire."""
    results = []
    for name, fn in ALL_ANTI_SNR_PROBES:
        score, evidence = fn(cand)
        if score > 0:
            results.append((name, score, evidence))
    return results
