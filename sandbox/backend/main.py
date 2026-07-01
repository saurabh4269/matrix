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
from src.jd_config import (  # noqa: E402
    get_config,
    list_available_jds,
    load_jd,
    set_config,
)
from src.evidence_tokens import extract_matched_tokens  # noqa: E402
from src.next_action import hrms_routing_action, main_risk, next_action, why_not_higher  # noqa: E402
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


def _current_digest() -> dict[str, Any]:
    """Dump the active JD's digest. Re-reads on every call so switching the
    active JD via /api/jd/select is reflected immediately."""
    d = get_config().digest
    return {
        "role": d.role,
        "location": d.location,
        "experience": d.experience,
        "style": d.style,
        "avoid": list(d.avoid),
    }


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
    # Reassign scores to a strictly-decreasing sequence so rank and score
    # never contradict each other in the UI (rank.py does the same for
    # the submission CSV).
    if chosen:
        top_score = max(chosen[0].score, 0.001)
        bottom_score = max(min(cs.score for cs in chosen), 0.001)
        spread = max(top_score - bottom_score, 1e-9)
        n_chosen = len(chosen)
        for i, cs in enumerate(chosen):
            if n_chosen == 1:
                continue
            cs.score = float(round(top_score - (i / (n_chosen - 1)) * spread, 6))
    _jd_slug = get_config().name
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
            "score": round(cs.score, 4),
            "confidence": cs.confidence,
            "rank_ci_95": [ci_lo, ci_hi],
            "breakdown": cs.breakdown,
            "anti_snr_penalty": round(cs.anti_snr_penalty, 3),
            "next_action": next_action(cs, current_title=cand.profile.current_title),
            "main_risk": main_risk(cs),
            "why_not_higher": why_not_higher(cs),
            "hrms_routing_action": hrms_routing_action(cs, jd_slug=_jd_slug),
            "matched_tokens": extract_matched_tokens(cand, get_config()),
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
        "jd_digest": _current_digest(),
        "ranked": out_rows,
        "total_evaluated": len(cands),
    }


@app.get("/api/jd")
def get_jd() -> dict[str, Any]:
    return _current_digest()


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


# --- JD selection + custom-JD bootstrap ---------------------------------

JDS_DIR = ROOT / "jds"
_ACTIVE_JD_NAME = "ai_engineer"  # bootstrap default, mirrors jd_config._DEFAULT_JD_PATH


class JDSelectRequest(BaseModel):
    name: str


class JDBootstrapRequest(BaseModel):
    text: str
    name: str | None = None


@app.get("/api/jds")
def list_jds() -> dict[str, Any]:
    """List every jds/*.yaml available for the JD-picker UI."""
    items = []
    for p in list_available_jds():
        if p.name.startswith("_"):
            continue  # skip _template.yaml
        try:
            cfg = load_jd(p)
        except Exception:
            continue
        items.append({
            "name": cfg.name,
            "display_name": cfg.display_name,
            "digest": {
                "role": cfg.digest.role,
                "location": cfg.digest.location,
                "experience": cfg.digest.experience,
                "style": cfg.digest.style,
                "avoid": list(cfg.digest.avoid),
            },
            "is_active": cfg.name == _ACTIVE_JD_NAME,
        })
    return {"jds": items, "active": _ACTIVE_JD_NAME}


@app.post("/api/jd/select")
def select_jd(req: JDSelectRequest) -> dict[str, Any]:
    """Swap the active JD config. Subsequent /api/demo calls re-rank against
    the new vocab + weights."""
    global _ACTIVE_JD_NAME
    safe = "".join(ch for ch in req.name if ch.isalnum() or ch in ("_", "-"))
    if not safe or safe != req.name:
        raise HTTPException(status_code=400, detail="Invalid JD name.")
    path = JDS_DIR / f"{safe}.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"JD '{safe}' not found.")
    try:
        cfg = load_jd(path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"JD file is invalid: {e}")
    set_config(cfg)
    _ACTIVE_JD_NAME = cfg.name
    return {"active": cfg.name, "digest": _current_digest()}


@app.post("/api/jd/bootstrap")
def bootstrap_jd(req: JDBootstrapRequest) -> dict[str, Any]:
    """Accept raw JD text, run the LLM-extract bootstrap, save a new YAML,
    and activate it. Returns the new active digest."""
    if not req.text or len(req.text.strip()) < 80:
        raise HTTPException(status_code=400, detail="Paste at least a few lines of JD text.")
    try:
        from jds.bootstrap import build_yaml, call_llm
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bootstrap import failed: {e}")

    # Slugify the requested name (or derive from the JD text's first line)
    if req.name:
        slug_src = req.name
    else:
        slug_src = req.text.strip().splitlines()[0][:40]
    slug = "".join(
        ch.lower() if ch.isalnum() else "_"
        for ch in slug_src
    ).strip("_") or "custom_jd"
    slug = slug[:48]

    # Don't clobber an existing file with the same slug; append a counter.
    out = JDS_DIR / f"{slug}.yaml"
    counter = 2
    while out.exists():
        out = JDS_DIR / f"{slug}_{counter}.yaml"
        counter += 1

    try:
        extracted = call_llm(req.text)
        extracted["digest"]["_full_text"] = req.text
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM extraction failed: {e}")

    base = load_jd(JDS_DIR / "ai_engineer.yaml").model_dump()
    cfg_dict = build_yaml(out.stem, extracted, mined=None, base=base)

    try:
        import yaml as _yaml
        out.write_text(
            _yaml.safe_dump(cfg_dict, default_flow_style=False, sort_keys=False, width=100),
            encoding="utf-8",
        )
        new_cfg = load_jd(out)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write/validate JD: {e}")

    set_config(new_cfg)
    global _ACTIVE_JD_NAME
    _ACTIVE_JD_NAME = new_cfg.name
    return {
        "active": new_cfg.name,
        "yaml_path": str(out.relative_to(ROOT)),
        "digest": _current_digest(),
    }


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
