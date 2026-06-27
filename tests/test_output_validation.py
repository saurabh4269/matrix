"""Tests for the output Pydantic schema and the full scoring → CSV pipeline."""
from __future__ import annotations

import csv
import io

import pytest
from pydantic import ValidationError

from src.scoring import score_candidate
from src.schema import SubmissionRow
from tests.fixtures import (
    TIER_5_FIXTURE,
    KEYWORD_STUFFER_FIXTURE,
    CONSULTING_ONLY_FIXTURE,
    BIGCORP_ONLY_FIXTURE,
    FRAMEWORK_ENTHUSIAST_FIXTURE,
)


def test_submission_row_validates_correct_input():
    row = SubmissionRow(
        candidate_id="CAND_0000001",
        rank=1,
        score=0.987,
        reasoning="Good fit because reasons.",
    )
    assert row.candidate_id == "CAND_0000001"


def test_submission_row_rejects_bad_id():
    with pytest.raises(ValidationError):
        SubmissionRow(candidate_id="bad_id", rank=1, score=0.5, reasoning="r")


def test_submission_row_rejects_out_of_range_rank():
    with pytest.raises(ValidationError):
        SubmissionRow(candidate_id="CAND_0000001", rank=0, score=0.5, reasoning="r")
    with pytest.raises(ValidationError):
        SubmissionRow(candidate_id="CAND_0000001", rank=101, score=0.5, reasoning="r")


def test_submission_row_rejects_extra_fields():
    with pytest.raises(ValidationError):
        SubmissionRow(
            candidate_id="CAND_0000001",
            rank=1,
            score=0.5,
            reasoning="r",
            extra_field="nope",
        )


def test_tier5_outranks_keyword_stuffer():
    cs_tier5 = score_candidate(TIER_5_FIXTURE)
    cs_stuffer = score_candidate(KEYWORD_STUFFER_FIXTURE)
    assert cs_tier5.score > cs_stuffer.score, (
        f"Tier-5 score {cs_tier5.score} should beat keyword-stuffer score {cs_stuffer.score}"
    )


def test_tier5_outranks_consulting_only():
    cs_tier5 = score_candidate(TIER_5_FIXTURE)
    cs_cons = score_candidate(CONSULTING_ONLY_FIXTURE)
    assert cs_tier5.score > cs_cons.score


def test_tier5_outranks_bigcorp_only():
    cs_tier5 = score_candidate(TIER_5_FIXTURE)
    cs_big = score_candidate(BIGCORP_ONLY_FIXTURE)
    assert cs_tier5.score > cs_big.score


def test_tier5_outranks_framework_enthusiast():
    cs_tier5 = score_candidate(TIER_5_FIXTURE)
    cs_fw = score_candidate(FRAMEWORK_ENTHUSIAST_FIXTURE)
    assert cs_tier5.score > cs_fw.score


def test_pipeline_produces_valid_csv_row():
    """End-to-end: score → SubmissionRow → CSV-safe string."""
    cs = score_candidate(TIER_5_FIXTURE)
    row = SubmissionRow(
        candidate_id=cs.candidate_id,
        rank=1,
        score=max(0.001, cs.score),
        reasoning="A reasoning string."
    )
    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
    writer.writerow([row.candidate_id, row.rank, row.score, row.reasoning])
    out = buf.getvalue().strip()
    assert "CAND_0000010" in out
    assert ",1," in out
