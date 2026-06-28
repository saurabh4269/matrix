"""FastAPI sandbox backend, serves the ranker over HTTP.

Single endpoint:
    POST /rank       , accepts an optional small candidates payload, returns
                        the ranked top-N with structured evidence

When no candidates are provided, the backend uses the pre-loaded curated demo
set (sandbox/backend/sample_candidates.json) which mixes labelled tier-5s,
keyword-stuffers, and a honeypot. This is the experience a judge sees on
first load, no upload required.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Ensure src/ is importable
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.conformal import compute_rank_intervals  # noqa: E402
from src.reasoning import generate_reasoning  # noqa: E402
from src.schema import Candidate  # noqa: E402
from src.scoring import score_candidate  # noqa: E402
from src.pairwise import refine_top_n  # noqa: E402


app = FastAPI(title="Redrob Ranker, Sandbox API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Demo candidates ---
SAMPLE_FILE = Path(__file__).parent / "sample_candidates.json"
DEMO_CANDIDATES: list[dict[str, Any]] = []
if SAMPLE_FILE.exists():
    DEMO_CANDIDATES = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))


class JDDigest(BaseModel):
    role: str
    location: str
    experience: str
    style: str
    avoid: list[str]


JD_DIGEST = JDDigest(
    role="Senior AI Engineer.",
    location="Pune or Noida. Hybrid.",
    experience="Five to nine years.",
    style="Hands-on, not architect-only.",
    avoid=[
        "Consulting-only careers.",
        "Framework enthusiasts.",
        "Pure researchers without production.",
    ],
)


class RankRequest(BaseModel):
    candidates: list[dict[str, Any]] | None = None
    top: int = 20


def _rank_payload(candidates_raw: list[dict[str, Any]], top: int) -> dict[str, Any]:
    """Run the ranker on a list of raw candidate dicts. Returns the demo payload."""
    cands = []
    by_id = {}
    for raw in candidates_raw:
        try:
            c = Candidate.model_validate(raw)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid candidate: {e}")
        cands.append(c)
        by_id[c.candidate_id] = c

    scored = []
    for c in cands:
        cs = score_candidate(c)
        if cs.is_honeypot:
            # Surface honeypots explicitly in the sandbox (the trap-demo moment)
            scored.append(cs)
        else:
            scored.append(cs)
    # Sort by linear score, honeypots last
    scored.sort(key=lambda cs: (cs.is_honeypot, -cs.score, cs.candidate_id))

    # Pairwise refinement on top 20
    non_honeypot = [cs for cs in scored if not cs.is_honeypot]
    refined = refine_top_n(non_honeypot, n=min(20, len(non_honeypot)))

    # Conformal-style rank confidence intervals — small N here, but still useful
    rank_intervals = compute_rank_intervals(refined, n_perturbations=30)

    chosen = refined[:top]
    out_rows = []
    for rank, cs in enumerate(chosen, start=1):
        cand = by_id[cs.candidate_id]
        reasoning = generate_reasoning(cand, cs, rank)
        positives = sorted(
            list(cs.must_have) + list(cs.substance) + list(cs.location_probes),
            key=lambda t: t[1],
            reverse=True,
        )
        concerns = [(n, s, e) for n, s, e in cs.anti_snr if s > 0]
        # Whispered hint criterion: plain-language tier-5 surfacing, high
        # substance + low keyword density. We approximate with description
        # specificity high and a non-flashy current title.
        spec_score = next(
            (s for n, s, _ in cs.substance if n == "description_specificity"), 0.0
        )
        years_at_product = next(
            (s for n, s, _ in cs.must_have if n == "years_applied_ml_at_product_co"), 0.0
        )
        is_whispered = rank > 5 and spec_score > 0.5 and years_at_product > 0.4

        ci_lo, ci_hi = rank_intervals.get(cs.candidate_id, (rank, rank))
        out_rows.append({
            "rank": rank,
            "confidence": cs.confidence,
            "rank_ci_95": [ci_lo, ci_hi],
            "breakdown": cs.breakdown,
            "anti_snr_penalty": round(cs.anti_snr_penalty, 3),
            "candidate_id": cs.candidate_id,
            "name": cand.profile.anonymized_name,
            "current_title": cand.profile.current_title,
            "current_company": cand.profile.current_company,
            "years_of_experience": cand.profile.years_of_experience,
            "location": cand.profile.location,
            "headline": cand.profile.headline,
            "summary": cand.profile.summary,
            "career_history": [
                {
                    "title": r.title,
                    "company": r.company,
                    "company_size": r.company_size,
                    "industry": r.industry,
                    "start_date": r.start_date,
                    "end_date": r.end_date,
                    "duration_months": r.duration_months,
                    "is_current": r.is_current,
                    "description": r.description,
                }
                for r in cand.career_history
            ],
            "education": [
                {
                    "institution": e.institution,
                    "degree": e.degree,
                    "field_of_study": e.field_of_study,
                    "start_year": e.start_year,
                    "end_year": e.end_year,
                    "tier": e.tier,
                    "grade": e.grade,
                }
                for e in cand.education
            ],
            "certifications": [
                {"name": c.name, "issuer": c.issuer, "year": c.year}
                for c in cand.certifications
            ],
            "reasoning": reasoning,
            "whispered": is_whispered,
            "snr_high": [
                {"name": n, "score": round(s, 3), "evidence": e}
                for n, s, e in positives[:5]
                if s > 0.1
            ],
            "snr_low": [
                {"name": sk.name, "proficiency": sk.proficiency,
                 "endorsements": sk.endorsements, "duration_months": sk.duration_months,
                 "verified": sk.name in cand.redrob_signals.skill_assessment_scores}
                for sk in cand.skills[:8]
            ],
            "concerns": [
                {"name": n, "score": round(s, 3), "evidence": e}
                for n, s, e in concerns[:2]
            ],
            "behavioural": {
                "open_to_work": cand.redrob_signals.open_to_work_flag,
                "response_rate": cand.redrob_signals.recruiter_response_rate,
                "response_time_hours": cand.redrob_signals.avg_response_time_hours,
                "last_active": cand.redrob_signals.last_active_date,
                "notice_days": cand.redrob_signals.notice_period_days,
                "applications_30d": cand.redrob_signals.applications_submitted_30d,
                "saved_by_recruiters_30d": cand.redrob_signals.saved_by_recruiters_30d,
                "profile_views_30d": cand.redrob_signals.profile_views_received_30d,
                "interview_completion_rate": cand.redrob_signals.interview_completion_rate,
                "github_activity": cand.redrob_signals.github_activity_score,
                "verified_email": cand.redrob_signals.verified_email,
                "verified_phone": cand.redrob_signals.verified_phone,
                "linkedin_connected": cand.redrob_signals.linkedin_connected,
                "behav_modifier_total": round(cs.behavioural_modifier, 3),
                "behav_breakdown": [
                    {"name": n, "score": round(s, 3), "evidence": e}
                    for n, s, e in cs.behavioural
                ],
            },
        })

    return {
        "jd_digest": JD_DIGEST.model_dump(),
        "ranked": out_rows,
        "total_evaluated": len(cands),
    }


@app.get("/api/jd")
def get_jd() -> dict[str, Any]:
    return JD_DIGEST.model_dump()


@app.get("/api/demo")
def get_demo() -> dict[str, Any]:
    """Pre-loaded demo using the curated sample candidates."""
    if not DEMO_CANDIDATES:
        raise HTTPException(status_code=500, detail="No demo candidates loaded.")
    return _rank_payload(DEMO_CANDIDATES, top=20)


@app.get("/api/discarded")
def get_discarded() -> dict[str, Any]:
    """Return the graveyard: every demo candidate that was either honeypot-
    quarantined or heavily penalised by anti-SNR probes, with the rule(s) that
    fired. Surfaces the system's defences for inspection."""
    if not DEMO_CANDIDATES:
        return {"discarded": []}
    cands = [Candidate.model_validate(c) for c in DEMO_CANDIDATES]
    out = []
    for cand in cands:
        cs = score_candidate(cand)
        if cs.is_honeypot:
            out.append({
                "candidate_id": cand.candidate_id,
                "name": cand.profile.anonymized_name,
                "current_title": cand.profile.current_title,
                "current_company": cand.profile.current_company,
                "discard_kind": "honeypot",
                "rules_fired": [
                    {"name": k, "evidence": v} for k, v in cs.honeypot_evidence.items()
                ],
            })
        elif cs.anti_snr_penalty < 0.3:
            out.append({
                "candidate_id": cand.candidate_id,
                "name": cand.profile.anonymized_name,
                "current_title": cand.profile.current_title,
                "current_company": cand.profile.current_company,
                "discard_kind": "heavy_anti_snr",
                "rules_fired": [
                    {"name": n, "score": round(s, 3), "evidence": e}
                    for n, s, e in cs.anti_snr if s > 0
                ],
            })
    return {"discarded": out}


@app.post("/api/rank")
def rank(req: RankRequest) -> dict[str, Any]:
    candidates = req.candidates or DEMO_CANDIDATES
    if not candidates:
        raise HTTPException(status_code=400, detail="No candidates provided.")
    if len(candidates) > 100:
        raise HTTPException(status_code=400, detail="Max 100 candidates per request.")
    return _rank_payload(candidates, top=req.top)


# Static frontend (built React app)
STATIC = Path(__file__).parent.parent / "frontend" / "dist"
if STATIC.exists():
    app.mount("/", StaticFiles(directory=str(STATIC), html=True), name="static")
