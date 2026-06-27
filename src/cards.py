"""Render a Candidate as a scannable Markdown card for hand-labelling.

The goal is ~30 seconds per card. Pre-extract the highest-signal fields and
fire structural-paradox flags up front so the labeller doesn't dig through
raw JSON.
"""
from __future__ import annotations

from src.schema import Candidate
from src.heuristics import fires_any_structural_paradox, is_consulting_only_career


def _proficiency_glyph(p: str) -> str:
    return {"beginner": "·", "intermediate": "◦", "advanced": "●", "expert": "★"}.get(
        p, "·"
    )


def _verified_glyphs(s) -> str:
    g = ""
    g += "✓" if s.verified_email else "·"
    g += "✓" if s.verified_phone else "·"
    g += "✓" if s.linkedin_connected else "·"
    return g


def render_card(cand: Candidate, bucket: str, card_index: int) -> str:
    """Render one candidate as a Markdown card section."""
    p = cand.profile
    s = cand.redrob_signals

    # Career path, most recent first, compact
    career_lines = []
    for r in cand.career_history[:5]:
        end = "present" if r.is_current or not r.end_date else r.end_date[:7]
        start = r.start_date[:7] if r.start_date else "?"
        career_lines.append(
            f"  - **{r.title}** @ {r.company} ({r.company_size}, {r.industry}), "
            f"{start} → {end}, {r.duration_months}mo"
        )
        # Append a one-line clip of the description so the labeller sees substance
        desc = (r.description or "").strip().replace("\n", " ")
        if desc:
            clip = desc[:240] + ("…" if len(desc) > 240 else "")
            career_lines.append(f"    > {clip}")

    # Education, top entry
    edu_line = "(none)"
    if cand.education:
        e = cand.education[0]
        edu_line = (
            f"{e.degree} in {e.field_of_study} @ {e.institution} "
            f"({e.start_year}–{e.end_year}, tier: {e.tier})"
        )

    # Top skills, first 10
    skill_lines = []
    for sk in cand.skills[:10]:
        assess = s.skill_assessment_scores.get(sk.name)
        assess_str = f" [tested: {assess:.0f}/100]" if assess is not None else ""
        skill_lines.append(
            f"  - {_proficiency_glyph(sk.proficiency)} {sk.name} "
            f"({sk.proficiency}, {sk.duration_months}mo, {sk.endorsements}e)"
            f"{assess_str}"
        )

    # Pre-fired structural flags, paradoxes + consulting-only
    flags = fires_any_structural_paradox(cand)
    if is_consulting_only_career(cand):
        flags.append("consulting_only_career")
    flag_str = ", ".join(flags) if flags else "–"

    # Behavioural snapshot
    salary = s.expected_salary_range_inr_lpa
    behav = (
        f"  - Open to work: **{s.open_to_work_flag}** · "
        f"Last active: **{s.last_active_date}** · "
        f"Response rate: **{s.recruiter_response_rate:.2f}**\n"
        f"  - Notice: **{s.notice_period_days}d** · "
        f"GitHub: **{s.github_activity_score:.0f}/100** · "
        f"Verified (email/phone/LI): **{_verified_glyphs(s)}**\n"
        f"  - Skill assessments: **{len(s.skill_assessment_scores)}** · "
        f"Interview completion: **{s.interview_completion_rate:.2f}** · "
        f"Saved by recruiters: **{s.saved_by_recruiters_30d}**\n"
        f"  - Salary expected: {salary.min:.1f}–{salary.max:.1f} LPA · "
        f"Work mode: {s.preferred_work_mode} · "
        f"Relocate: {s.willing_to_relocate}"
    )

    summary = (p.summary or "").strip().replace("\n", " ")
    if len(summary) > 600:
        summary = summary[:600] + "…"

    return f"""---

## #{card_index:03d} · {p.anonymized_name or "(unnamed)"} · `{cand.candidate_id}`

**Bucket:** `{bucket}`  ·  **⚠ Pre-fired flags:** `{flag_str}`

**Headline:** {p.headline or "(none)"}

**Current:** **{p.current_title}** @ {p.current_company} ({p.current_company_size}, {p.current_industry}) · {p.years_of_experience:.1f}y total · {p.location}, {p.country}

**Summary:** {summary or "(none)"}

**Career:**
{chr(10).join(career_lines) if career_lines else "  (none)"}

**Education:** {edu_line}

**Top skills:**
{chr(10).join(skill_lines) if skill_lines else "  (none)"}

**Behavioural signals:**
{behav}
"""
