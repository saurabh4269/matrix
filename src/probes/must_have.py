"""Must-have probes, JD's "absolutely need" requirements.

Each probe returns (score in [0,1], evidence_string). High weight in the
composite. Map directly to a sentence in the JD.

JD must-haves:
  1. Production experience with embeddings-based retrieval systems
  2. Production experience with vector DB / hybrid search
  3. Strong Python
  4. Designing evaluation frameworks for ranking systems (NDCG/MRR/MAP)
  5. (Implicit but heavily weighted) Years of applied ML at product companies
"""
from __future__ import annotations

from src.heuristics import (
    _ML_TITLE_RE,
    PRODUCT_COMPANIES,
)
from src.probes._text import (
    EMBEDDING_TOOLS,
    VECTOR_DB_TOOLS,
    RANKING_EVAL_TERMS,
    PRODUCTION_VERBS,
    count_phrase_hits,
    distinct_phrase_hits,
    saturating,
)
from src.schema import Candidate


def _all_descriptions(cand: Candidate) -> str:
    return " ".join(r.description or "" for r in cand.career_history)


def _all_skills_text(cand: Candidate) -> str:
    return " ".join(s.name or "" for s in cand.skills)


def production_embeddings_retrieval(cand: Candidate) -> tuple[float, str]:
    """Mentions of embedding/retrieval tools in description text + skill list."""
    desc = _all_descriptions(cand)
    skills = _all_skills_text(cand)

    desc_hits = distinct_phrase_hits(desc, EMBEDDING_TOOLS)
    skill_hits = distinct_phrase_hits(skills, EMBEDDING_TOOLS)

    if desc_hits == 0 and skill_hits == 0:
        return 0.0, ""

    # Description hits are worth ~3x skill hits, substance > claim
    score = saturating(desc_hits * 3 + skill_hits, threshold=6)
    evidence_parts = []
    if desc_hits:
        evidence_parts.append(f"{desc_hits} embedding/retrieval mention(s) in descriptions")
    if skill_hits:
        evidence_parts.append(f"{skill_hits} embedding tool(s) in skills")
    return score, "; ".join(evidence_parts)


def production_vector_db(cand: Candidate) -> tuple[float, str]:
    """Mentions of vector DB / hybrid search tools."""
    desc = _all_descriptions(cand)
    skills = _all_skills_text(cand)

    desc_hits = distinct_phrase_hits(desc, VECTOR_DB_TOOLS)
    skill_hits = distinct_phrase_hits(skills, VECTOR_DB_TOOLS)

    if desc_hits == 0 and skill_hits == 0:
        return 0.0, ""

    score = saturating(desc_hits * 3 + skill_hits, threshold=5)
    evidence_parts = []
    if desc_hits:
        evidence_parts.append(f"{desc_hits} vector-DB mention(s) in descriptions")
    if skill_hits:
        evidence_parts.append(f"{skill_hits} vector tool(s) in skills")
    return score, "; ".join(evidence_parts)


def ranking_eval_framework(cand: Candidate) -> tuple[float, str]:
    """Mentions of NDCG/MRR/MAP/A-B test in descriptions, JD literally names these."""
    desc = _all_descriptions(cand)
    hits = distinct_phrase_hits(desc, RANKING_EVAL_TERMS)
    if hits == 0:
        return 0.0, ""
    score = saturating(hits, threshold=3)
    return score, f"{hits} ranking-eval term(s) (NDCG/MRR/MAP/A-B) in descriptions"


def python_proficiency(cand: Candidate) -> tuple[float, str]:
    """Python skill claim + endorsements + duration + assessment score (if any)."""
    py = next(
        (s for s in cand.skills if s.name.strip().lower() == "python"),
        None,
    )
    if py is None:
        # Maybe no explicit Python skill but the descriptions mention Python heavily?
        desc = _all_descriptions(cand).lower()
        if desc.count("python") >= 2:
            return 0.4, "Python mentioned in role descriptions but not listed as skill"
        return 0.0, ""

    # Trust formula
    prof_weight = {"beginner": 0.3, "intermediate": 0.5, "advanced": 0.8, "expert": 1.0}.get(
        py.proficiency, 0.5
    )
    duration_weight = saturating(py.duration_months, threshold=36)  # 3y cap
    endorsement_weight = saturating(py.endorsements, threshold=10)

    base = prof_weight * (0.4 + 0.4 * duration_weight + 0.2 * endorsement_weight)

    # Assessment score multiplier (High-SNR, tested vs claimed)
    assess = cand.redrob_signals.skill_assessment_scores.get("Python")
    if assess is not None:
        ev = f"Python ({py.proficiency}, {py.duration_months}mo, {py.endorsements}e) verified {assess:.0f}/100"
        return min(1.0, base * (0.7 + 0.3 * (assess / 100))), ev

    return base, f"Python ({py.proficiency}, {py.duration_months}mo, {py.endorsements}e), not verified"


def years_applied_ml_at_product_co(cand: Candidate) -> tuple[float, str]:
    """Sum of duration_months across roles where (ML title) AND (product co).

    This is the single strongest predictor of fit. JD wants 4-5 years of applied
    ML at product companies.
    """
    months = 0
    n_roles = 0
    examples = []
    for r in cand.career_history:
        is_ml = bool(_ML_TITLE_RE.search(r.title or ""))
        is_product = r.company.strip().lower() in PRODUCT_COMPANIES
        if is_ml and is_product:
            months += r.duration_months
            n_roles += 1
            if len(examples) < 2:
                examples.append(f"{r.duration_months}mo at {r.company}")

    if months == 0:
        return 0.0, ""

    years = months / 12.0
    # JD targets 4–5 years; we saturate at 5y
    score = saturating(years, threshold=5.0)
    return score, f"{years:.1f}y of ML at product cos ({n_roles} role(s): {', '.join(examples)})"


ALL_MUST_HAVE_PROBES = [
    ("production_embeddings_retrieval", production_embeddings_retrieval),
    ("production_vector_db", production_vector_db),
    ("ranking_eval_framework", ranking_eval_framework),
    ("python_proficiency", python_proficiency),
    ("years_applied_ml_at_product_co", years_applied_ml_at_product_co),
]


def run_all(cand: Candidate) -> list[tuple[str, float, str]]:
    """Run every must-have probe. Returns [(name, score, evidence)]."""
    return [
        (name, score, ev)
        for name, fn in ALL_MUST_HAVE_PROBES
        for score, ev in [fn(cand)]
        if score > 0
    ]
