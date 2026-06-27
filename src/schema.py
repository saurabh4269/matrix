"""Pydantic models for input candidates and output rows.

Loose on candidate input (real data has nulls and inconsistencies); strict on
submission output (so we cannot emit malformed CSV by construction).
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Input, Candidate sub-models (lenient with extras + nulls)
# ---------------------------------------------------------------------------

class Profile(BaseModel):
    model_config = ConfigDict(extra="allow")
    anonymized_name: str = ""
    headline: str = ""
    summary: str = ""
    location: str = ""
    country: str = ""
    years_of_experience: float = 0.0
    current_title: str = ""
    current_company: str = ""
    current_company_size: str = ""
    current_industry: str = ""


class CareerRole(BaseModel):
    model_config = ConfigDict(extra="allow")
    company: str = ""
    title: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_months: int = 0
    is_current: bool = False
    industry: str = ""
    company_size: str = ""
    description: str = ""


class Education(BaseModel):
    model_config = ConfigDict(extra="allow")
    institution: str = ""
    degree: str = ""
    field_of_study: str = ""
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    grade: Optional[str] = None
    tier: str = "unknown"


class Skill(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str = ""
    proficiency: str = "beginner"
    endorsements: int = 0
    duration_months: int = 0


class Certification(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str = ""
    issuer: str = ""
    year: Optional[int] = None


class Language(BaseModel):
    model_config = ConfigDict(extra="allow")
    language: str = ""
    proficiency: str = "basic"


class SalaryRange(BaseModel):
    model_config = ConfigDict(extra="allow")
    min: float = 0.0
    max: float = 0.0


class RedrobSignals(BaseModel):
    model_config = ConfigDict(extra="allow")
    profile_completeness_score: float = 0.0
    signup_date: Optional[str] = None
    last_active_date: Optional[str] = None
    open_to_work_flag: bool = False
    profile_views_received_30d: int = 0
    applications_submitted_30d: int = 0
    recruiter_response_rate: float = 0.0
    avg_response_time_hours: float = 0.0
    skill_assessment_scores: dict[str, float] = Field(default_factory=dict)
    connection_count: int = 0
    endorsements_received: int = 0
    notice_period_days: int = 0
    expected_salary_range_inr_lpa: SalaryRange = Field(default_factory=SalaryRange)
    preferred_work_mode: str = "flexible"
    willing_to_relocate: bool = False
    github_activity_score: float = -1.0
    search_appearance_30d: int = 0
    saved_by_recruiters_30d: int = 0
    interview_completion_rate: float = 0.0
    offer_acceptance_rate: float = -1.0
    verified_email: bool = False
    verified_phone: bool = False
    linkedin_connected: bool = False


class Candidate(BaseModel):
    model_config = ConfigDict(extra="allow")
    candidate_id: str
    profile: Profile = Field(default_factory=Profile)
    career_history: list[CareerRole] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)
    redrob_signals: RedrobSignals = Field(default_factory=RedrobSignals)


# ---------------------------------------------------------------------------
# Output, strict; non-conformant rows cannot be constructed
# ---------------------------------------------------------------------------

import re
CAND_ID_PATTERN = re.compile(r"^CAND_[0-9]{7}$")


class SubmissionRow(BaseModel):
    """A single row of the submission CSV. Cannot be malformed by construction."""
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(pattern=r"^CAND_[0-9]{7}$")
    rank: int = Field(ge=1, le=100)
    score: float
    reasoning: str = Field(min_length=0, max_length=1000)
