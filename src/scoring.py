"""Scoring composition — combine all probe outputs into a single score per candidate.

The scoring function follows the spec in final_plan §7:

    must_have_score    = weighted_sum(must_have probes)
    nice_to_have_score = weighted_sum(nice_to_have probes)
    substance_score    = weighted_sum(substance probes)
    anti_snr_penalty   = ∏(1 − probe)  for anti-SNR probes
    behavioural_modifier = product of behavioural probes
    location_logistics = weighted_sum(location probes)
    honeypot_gate      = 0 if any honeypot rule fires else 1

    raw = (
        1.0 · must_have_score
      + 0.3 · nice_to_have_score
      + 0.6 · substance_score
      + 0.1 · location_logistics
    ) × anti_snr_penalty × behavioural_modifier × honeypot_gate

Each probe carries equal weight within its category for the initial baseline;
LightGBM-Rank weight tuning happens in Phase 7 against the labelled eval set.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.honeypot import detect as honeypot_detect
from src.probes import anti_snr, behavioural, location, must_have, substance
from src.schema import Candidate


# ---------------------------------------------------------------------------
# Per-probe weights — uniform inside category as starting point; tuned later.
# Values picked so each category's max contribution matches the §7 mix.
# ---------------------------------------------------------------------------

# Must-have category targets sum = ~1.0 across 5 probes
MUST_HAVE_WEIGHTS = {
    "production_embeddings_retrieval": 0.25,
    "production_vector_db": 0.20,
    "ranking_eval_framework": 0.15,
    "python_proficiency": 0.10,
    "years_applied_ml_at_product_co": 0.30,
}

SUBSTANCE_WEIGHTS = {
    "description_specificity": 0.20,
    "narrative_arc_density": 0.10,
    "production_emphasis": 0.15,
    "verification_ratio": 0.15,
    "acceleration": 0.05,
    "summary_thoughtfulness": 0.05,
    "company_stage_alignment": 0.10,
    "shipper_vs_researcher_ratio": 0.10,
    "named_employer_micro_boost": 0.10,
}

LOCATION_WEIGHTS = {
    "location_match": 0.50,
    "yoe_band_fit": 0.40,
    "certifications_micro_boost": 0.10,
}

# Anti-SNR penalties — each probe's score directly contributes to penalty.
# Multiplied as ∏(1 − w·s). w=1 means full penalty when probe fires at 1.0.
ANTI_SNR_WEIGHTS = {
    "consulting_only": 0.95,  # near-zeroes the candidate
    "bigcorp_only": 0.40,
    "pure_research_career": 0.95,
    "no_production_code_18mo": 0.70,
    "framework_enthusiast": 0.50,
    "title_chaser": 0.30,
    "cv_speech_robo_only": 0.70,
    "manager_drift": 0.30,
    "keyword_dense_junior": 0.70,
    "remote_only_vs_hybrid_jd": 0.30,
    "dilution": 0.50,
}

# Behavioural — used as multiplicative modifier directly, no extra weights.
# Component-wise product: effectively_available × notice_curve × trust × engagement.
# Engagement has lighter weight via a clipped contribution.

# Category-level multipliers in the final composition
CATEGORY_WEIGHTS = {
    "must_have": 1.0,
    "substance": 0.6,
    "location": 0.1,
}


# ---------------------------------------------------------------------------
# Per-candidate result dataclass
# ---------------------------------------------------------------------------

@dataclass
class CandidateScore:
    candidate_id: str
    score: float                      # final composite
    is_honeypot: bool                 # if any honeypot rule fired
    honeypot_evidence: dict[str, str] = field(default_factory=dict)

    must_have: list[tuple[str, float, str]] = field(default_factory=list)
    substance: list[tuple[str, float, str]] = field(default_factory=list)
    behavioural: list[tuple[str, float, str]] = field(default_factory=list)
    anti_snr: list[tuple[str, float, str]] = field(default_factory=list)
    location_probes: list[tuple[str, float, str]] = field(default_factory=list)

    must_have_sum: float = 0.0
    substance_sum: float = 0.0
    location_sum: float = 0.0
    anti_snr_penalty: float = 1.0
    behavioural_modifier: float = 1.0


def score_candidate(cand: Candidate) -> CandidateScore:
    """Apply all probes to a candidate and return a CandidateScore.

    Honeypot candidates get score = −1.0 and never appear in top-100.
    """
    result = CandidateScore(candidate_id=cand.candidate_id, score=0.0, is_honeypot=False)

    # ----- Honeypot gate -----
    hp = honeypot_detect(cand)
    if hp:
        result.is_honeypot = True
        result.honeypot_evidence = hp
        result.score = -1.0
        return result

    # ----- Must-have probes -----
    must = must_have.run_all(cand)
    result.must_have = must
    for name, score, _ in must:
        result.must_have_sum += MUST_HAVE_WEIGHTS.get(name, 0.0) * score

    # ----- Substance probes -----
    sub = substance.run_all(cand)
    result.substance = sub
    for name, score, _ in sub:
        result.substance_sum += SUBSTANCE_WEIGHTS.get(name, 0.0) * score

    # ----- Location probes -----
    loc = location.run_all(cand)
    result.location_probes = loc
    for name, score, _ in loc:
        result.location_sum += LOCATION_WEIGHTS.get(name, 0.0) * score

    # ----- Anti-SNR penalty (multiplicative) -----
    anti = anti_snr.run_all(cand)
    result.anti_snr = anti
    penalty = 1.0
    for name, score, _ in anti:
        penalty *= max(0.0, 1.0 - ANTI_SNR_WEIGHTS.get(name, 0.0) * score)
    result.anti_snr_penalty = penalty

    # ----- Behavioural modifier (multiplicative product) -----
    behav = behavioural.run_all(cand)
    result.behavioural = behav
    # Weighted geometric mean across the four behavioural probes:
    # use product of (score^weight), weights chosen below.
    behav_weights = {
        "effectively_available": 0.45,
        "notice_period_curve": 0.30,
        "trust_modifier": 0.10,
        "engagement_quality": 0.15,
    }
    behav_modifier = 1.0
    for name, score, _ in behav:
        w = behav_weights.get(name, 0.0)
        # Floor each behavioural at 0.1 to avoid total annihilation from any single signal
        behav_modifier *= max(0.1, score) ** w
    result.behavioural_modifier = behav_modifier

    # ----- Composite -----
    base = (
        CATEGORY_WEIGHTS["must_have"] * result.must_have_sum
        + CATEGORY_WEIGHTS["substance"] * result.substance_sum
        + CATEGORY_WEIGHTS["location"] * result.location_sum
    )
    result.score = base * penalty * behav_modifier
    return result


def score_all(candidates) -> list[CandidateScore]:
    """Apply scoring to an iterable of candidates."""
    return [score_candidate(c) for c in candidates]
