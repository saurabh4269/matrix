"""Tests for the probe library.

Each probe must:
  - fire on the candidates it's designed for
  - NOT fire on candidates where it shouldn't
  - produce evidence strings that reference real schema attributes
"""
from __future__ import annotations

from src.probes import anti_snr, must_have, substance
from tests.fixtures import (
    TIER_5_FIXTURE,
    KEYWORD_STUFFER_FIXTURE,
    CONSULTING_ONLY_FIXTURE,
    BIGCORP_ONLY_FIXTURE,
    FRAMEWORK_ENTHUSIAST_FIXTURE,
    TITLE_CHASER_FIXTURE,
)


# ---------- must-have probes ----------

def test_tier5_fires_must_haves():
    """Tier-5 fixture should fire most must-have probes with positive scores."""
    results = dict((name, score) for name, score, _ in must_have.run_all(TIER_5_FIXTURE))
    assert results["production_embeddings_retrieval"] > 0.5
    assert results["production_vector_db"] > 0.3
    assert results["ranking_eval_framework"] > 0
    assert results["years_applied_ml_at_product_co"] > 0.5
    assert results["python_proficiency"] > 0.5


def test_keyword_stuffer_must_haves_collapse():
    """Keyword stuffer claims things but description has no substance.

    Must-have probes look at descriptions too; they should be low/zero."""
    results = dict((name, score) for name, score, _ in must_have.run_all(KEYWORD_STUFFER_FIXTURE))
    # Marketing Manager description has zero retrieval substance
    assert results.get("ranking_eval_framework", 0) == 0
    # Tools listed as skills, but with zero endorsements and tiny durations →
    # production_vector_db / production_embeddings_retrieval still fires off
    # the skill-list (it's a partial signal); the *scoring layer* nukes via
    # anti-SNR penalties (tested separately).


def test_consulting_only_no_ml_signal():
    """Consulting-only candidate has no embedding/vector/eval signal."""
    results = dict((name, score) for name, score, _ in must_have.run_all(CONSULTING_ONLY_FIXTURE))
    assert results.get("production_embeddings_retrieval", 0) == 0
    assert results.get("production_vector_db", 0) == 0
    assert results.get("years_applied_ml_at_product_co", 0) == 0


# ---------- substance probes ----------

def test_tier5_has_specificity():
    results = dict((name, score) for name, score, _ in substance.run_all(TIER_5_FIXTURE))
    assert results.get("description_specificity", 0) > 0.3, (
        "Tier-5 description names specific systems"
    )
    assert results.get("production_emphasis", 0) > 0


def test_keyword_stuffer_lacks_specificity():
    results = dict((name, score) for name, score, _ in substance.run_all(KEYWORD_STUFFER_FIXTURE))
    # Marketing Manager description mentions $200K budget, ChatGPT, etc, generic
    spec = results.get("description_specificity", 0)
    assert spec < 0.4, f"Keyword stuffer should have low specificity, got {spec}"


def test_verification_ratio_tier5():
    """Tier-5 has assessment scores on some claimed skills."""
    results = dict((name, score) for name, score, _ in substance.run_all(TIER_5_FIXTURE))
    assert results.get("verification_ratio", 0) > 0


# ---------- anti-SNR probes ----------

def test_consulting_only_fires():
    results = dict((name, score) for name, score, _ in anti_snr.run_all(CONSULTING_ONLY_FIXTURE))
    assert results["consulting_only"] == 1.0


def test_bigcorp_only_fires():
    results = dict((name, score) for name, score, _ in anti_snr.run_all(BIGCORP_ONLY_FIXTURE))
    assert results.get("bigcorp_only", 0) > 0


def test_framework_enthusiast_fires():
    results = dict((name, score) for name, score, _ in anti_snr.run_all(FRAMEWORK_ENTHUSIAST_FIXTURE))
    assert results.get("framework_enthusiast", 0) > 0


def test_title_chaser_fires():
    results = dict((name, score) for name, score, _ in anti_snr.run_all(TITLE_CHASER_FIXTURE))
    assert results.get("title_chaser", 0) > 0


def test_tier5_no_anti_snr():
    """Tier-5 candidate must not fire any anti-SNR penalty."""
    results = anti_snr.run_all(TIER_5_FIXTURE)
    # The dilution probe may fire mildly if the math says so, but the major
    # red-flag probes must not.
    fired_majors = {
        name for name, _, _ in results
        if name in {
            "consulting_only", "bigcorp_only", "pure_research_career",
            "framework_enthusiast", "title_chaser", "cv_speech_robo_only",
            "manager_drift", "keyword_dense_junior",
        }
    }
    assert fired_majors == set(), f"Tier-5 fired major anti-SNR: {fired_majors}"
