"""Tests for the honeypot detector.

Each test confirms the rule fires (or doesn't) on the expected fixture, and
that the conservative rule set does NOT fire on legitimate strong candidates.
"""
from __future__ import annotations

from src.honeypot import detect, is_honeypot
from tests.fixtures import (
    TIER_5_FIXTURE,
    KEYWORD_STUFFER_FIXTURE,
    CONSULTING_ONLY_FIXTURE,
    BIGCORP_ONLY_FIXTURE,
    HONEYPOT_CHRONOLOGICAL,
    HONEYPOT_DURATION_EXCEEDS_YOE,
    HONEYPOT_SINGLE_ROLE_EXCEEDS_YOE,
    HONEYPOT_EXPERT_ZERO_MONTHS,
    HONEYPOT_COMPANY_AGE,
)


def test_tier5_is_not_honeypot():
    """Strong real candidate must never fire a honeypot rule."""
    assert detect(TIER_5_FIXTURE) == {}
    assert not is_honeypot(TIER_5_FIXTURE)


def test_keyword_stuffer_is_not_honeypot():
    """Trap candidate (keyword stuffer) is bad but not a honeypot, penalised by probes."""
    assert detect(KEYWORD_STUFFER_FIXTURE) == {}


def test_consulting_only_is_not_honeypot():
    """Consulting-only is a JD anti-SNR penalty, not a honeypot."""
    assert detect(CONSULTING_ONLY_FIXTURE) == {}


def test_bigcorp_only_is_not_honeypot():
    """Bigcorp-only is a soft penalty, not a honeypot."""
    assert detect(BIGCORP_ONLY_FIXTURE) == {}


def test_chronological_paradox_fires():
    fires = detect(HONEYPOT_CHRONOLOGICAL)
    assert "chronological_paradox" in fires
    assert is_honeypot(HONEYPOT_CHRONOLOGICAL)


def test_duration_exceeds_yoe_fires():
    fires = detect(HONEYPOT_DURATION_EXCEEDS_YOE)
    assert "duration_exceeds_yoe" in fires


def test_single_role_exceeds_yoe_fires():
    fires = detect(HONEYPOT_SINGLE_ROLE_EXCEEDS_YOE)
    assert "single_role_exceeds_yoe" in fires


def test_expert_zero_months_fires():
    fires = detect(HONEYPOT_EXPERT_ZERO_MONTHS)
    assert "expert_with_zero_months" in fires


def test_company_age_fires():
    fires = detect(HONEYPOT_COMPANY_AGE)
    assert "tenure_exceeds_company_age" in fires
