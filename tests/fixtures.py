"""Hand-crafted candidate fixtures for unit testing.

Each fixture is a minimal dict that satisfies the schema and encodes a
specific archetype the system needs to handle correctly:

  TIER_5_FIXTURE         , strong ML/IR engineer at product co
  TIER_4_FIXTURE         , adjacent strong with one gap
  KEYWORD_STUFFER_FIXTURE, Marketing Manager with AI keywords (the trap)
  CONSULTING_ONLY_FIXTURE, entire career at TCS
  BIGCORP_ONLY_FIXTURE   , entire career at FAANG-scale companies
  FRAMEWORK_ENTHUSIAST_FIXTURE, LangChain-only, no production
  TITLE_CHASER_FIXTURE   , three short-tenure recent roles
  HONEYPOT_FIXTURES      , six honeypots, one per rule

Used by tests/* to ensure each probe and rule fires (and only fires) on the
right candidates.
"""
from __future__ import annotations

from src.schema import Candidate


def make_candidate(**overrides) -> Candidate:
    """Build a baseline candidate with sensible defaults; override fields per test."""
    base = {
        "candidate_id": overrides.pop("candidate_id", "CAND_0000001"),
        "profile": {
            "anonymized_name": "Test Candidate",
            "headline": "Engineer",
            "summary": "Software engineer with a few years of experience building things.",
            "location": "Bangalore, India",
            "country": "India",
            "years_of_experience": 6.0,
            "current_title": "Software Engineer",
            "current_company": "Some Company",
            "current_company_size": "201-500",
            "current_industry": "Software",
            **overrides.pop("profile", {}),
        },
        "career_history": overrides.pop("career_history", []),
        "education": overrides.pop("education", []),
        "skills": overrides.pop("skills", []),
        "certifications": overrides.pop("certifications", []),
        "languages": overrides.pop("languages", []),
        "redrob_signals": {
            "profile_completeness_score": 80.0,
            "signup_date": "2024-01-01",
            "last_active_date": "2026-05-01",
            "open_to_work_flag": True,
            "profile_views_received_30d": 10,
            "applications_submitted_30d": 5,
            "recruiter_response_rate": 0.5,
            "avg_response_time_hours": 12.0,
            "skill_assessment_scores": {},
            "connection_count": 100,
            "endorsements_received": 50,
            "notice_period_days": 30,
            "expected_salary_range_inr_lpa": {"min": 20.0, "max": 30.0},
            "preferred_work_mode": "hybrid",
            "willing_to_relocate": True,
            "github_activity_score": 40.0,
            "search_appearance_30d": 5,
            "saved_by_recruiters_30d": 3,
            "interview_completion_rate": 0.8,
            "offer_acceptance_rate": -1.0,
            "verified_email": True,
            "verified_phone": True,
            "linkedin_connected": True,
            **overrides.pop("redrob_signals", {}),
        },
        **overrides,
    }
    return Candidate.model_validate(base)


# ----- Tier-5: textbook strong ML/IR engineer at product co -----
TIER_5_FIXTURE = make_candidate(
    candidate_id="CAND_0000010",
    profile={
        "current_title": "Senior AI Engineer",
        "current_company": "Razorpay",
        "current_company_size": "1001-5000",
        "current_industry": "Fintech",
        "years_of_experience": 7.0,
        "summary": (
            "Senior AI engineer with 7 years building production retrieval systems. "
            "Shipped a hybrid BM25+dense pipeline serving 50M queries/month. "
            "Owned the NDCG/MRR evaluation harness and the offline-online correlation work."
        ),
    },
    career_history=[
        {
            "company": "Razorpay",
            "title": "Senior AI Engineer",
            "start_date": "2023-01-01",
            "end_date": None,
            "duration_months": 36,
            "is_current": True,
            "industry": "Fintech",
            "company_size": "1001-5000",
            "description": (
                "Built and shipped a production retrieval system using BGE embeddings and FAISS HNSW "
                "indexes. Owned the NDCG evaluation harness; reduced p95 latency from 240ms to 80ms "
                "after discovering a quantization bug. Cross-encoder rerank on top 50."
            ),
        },
        {
            "company": "Swiggy",
            "title": "Machine Learning Engineer",
            "start_date": "2019-06-01",
            "end_date": "2022-12-30",
            "duration_months": 42,
            "is_current": False,
            "industry": "Food Delivery",
            "company_size": "1001-5000",
            "description": (
                "Built recommendation ranking models on TensorFlow; deployed via TFServing. "
                "Used Sentence Transformers for query understanding. Owned the A/B test framework."
            ),
        },
    ],
    skills=[
        {"name": "Python", "proficiency": "expert", "endorsements": 50, "duration_months": 84},
        {"name": "FAISS", "proficiency": "advanced", "endorsements": 20, "duration_months": 36},
        {"name": "BGE", "proficiency": "advanced", "endorsements": 12, "duration_months": 24},
        {"name": "Sentence Transformers", "proficiency": "expert", "endorsements": 25, "duration_months": 30},
    ],
    redrob_signals={
        "skill_assessment_scores": {"Python": 92.0, "FAISS": 85.0},
        "github_activity_score": 78.0,
        "interview_completion_rate": 0.95,
        "saved_by_recruiters_30d": 18,
    },
)


# ----- Keyword stuffer: Marketing Manager with AI keywords -----
KEYWORD_STUFFER_FIXTURE = make_candidate(
    candidate_id="CAND_0000020",
    profile={
        "current_title": "Marketing Manager",
        "current_company": "Acme Marketing",
        "current_company_size": "51-200",
        "current_industry": "Marketing",
        "years_of_experience": 8.0,
        "summary": (
            "Marketing leader with 8 years experience. Exploring AI tools and prompt engineering."
        ),
    },
    career_history=[
        {
            "company": "Acme Marketing",
            "title": "Marketing Manager",
            "start_date": "2018-01-01",
            "end_date": None,
            "duration_months": 96,
            "is_current": True,
            "industry": "Marketing",
            "company_size": "51-200",
            "description": (
                "Ran content marketing campaigns. Managed budget of $200K. Used ChatGPT for "
                "research and drafting. Owned brand voice and editorial calendar."
            ),
        },
    ],
    skills=[
        {"name": "RAG", "proficiency": "expert", "endorsements": 0, "duration_months": 6},
        {"name": "LangChain", "proficiency": "expert", "endorsements": 0, "duration_months": 4},
        {"name": "Pinecone", "proficiency": "expert", "endorsements": 0, "duration_months": 3},
        {"name": "Fine-tuning LLMs", "proficiency": "expert", "endorsements": 0, "duration_months": 2},
        {"name": "Embeddings", "proficiency": "expert", "endorsements": 0, "duration_months": 4},
        {"name": "Vector Search", "proficiency": "advanced", "endorsements": 0, "duration_months": 5},
        {"name": "NLP", "proficiency": "advanced", "endorsements": 0, "duration_months": 4},
    ],
)


# ----- Consulting-only: entire career at TCS -----
CONSULTING_ONLY_FIXTURE = make_candidate(
    candidate_id="CAND_0000030",
    profile={
        "current_title": "Software Engineer",
        "current_company": "TCS",
        "current_company_size": "10001+",
        "current_industry": "IT Services",
        "years_of_experience": 8.0,
    },
    career_history=[
        {
            "company": "TCS",
            "title": "Software Engineer",
            "start_date": "2018-01-01",
            "end_date": None,
            "duration_months": 96,
            "is_current": True,
            "industry": "IT Services",
            "company_size": "10001+",
            "description": "Java backend development for various enterprise clients.",
        },
    ],
)


# ----- Bigcorp-only: career entirely at 10001+ companies -----
BIGCORP_ONLY_FIXTURE = make_candidate(
    candidate_id="CAND_0000040",
    profile={
        "current_title": "Senior Software Engineer",
        "current_company": "Google",
        "current_company_size": "10001+",
        "current_industry": "Software",
        "years_of_experience": 10.0,
    },
    career_history=[
        {
            "company": "Google",
            "title": "Senior Software Engineer",
            "start_date": "2020-01-01",
            "end_date": None,
            "duration_months": 72,
            "is_current": True,
            "industry": "Software",
            "company_size": "10001+",
            "description": "Worked on infrastructure team. Built internal tooling.",
        },
        {
            "company": "Microsoft",
            "title": "Software Engineer",
            "start_date": "2016-01-01",
            "end_date": "2019-12-31",
            "duration_months": 48,
            "is_current": False,
            "industry": "Software",
            "company_size": "10001+",
            "description": "Worked on Office team.",
        },
    ],
)


# ----- Framework enthusiast: LangChain-only, recent, no production -----
FRAMEWORK_ENTHUSIAST_FIXTURE = make_candidate(
    candidate_id="CAND_0000050",
    profile={
        "current_title": "Backend Developer",
        "current_company": "Acme",
        "years_of_experience": 3.0,
    },
    career_history=[
        {
            "company": "Acme",
            "title": "Backend Developer",
            "start_date": "2024-01-01",
            "end_date": None,
            "duration_months": 24,
            "is_current": True,
            "industry": "Software",
            "company_size": "11-50",
            "description": "Wrote some API code. Experimented with LangChain for a side project.",
        },
    ],
    skills=[
        {"name": "LangChain", "proficiency": "intermediate", "endorsements": 2, "duration_months": 6},
        {"name": "RAG", "proficiency": "intermediate", "endorsements": 1, "duration_months": 6},
    ],
)


# ----- Title chaser: three short-tenure recent roles -----
TITLE_CHASER_FIXTURE = make_candidate(
    candidate_id="CAND_0000060",
    profile={
        "current_title": "Principal Engineer",
        "current_company": "StartupC",
        "years_of_experience": 6.0,
    },
    career_history=[
        {"company": "StartupC", "title": "Principal Engineer", "start_date": "2025-08-01",
         "end_date": None, "duration_months": 10, "is_current": True, "industry": "Software",
         "company_size": "11-50", "description": "Built things."},
        {"company": "StartupB", "title": "Staff Engineer", "start_date": "2024-02-01",
         "end_date": "2025-07-30", "duration_months": 17, "is_current": False, "industry": "Software",
         "company_size": "51-200", "description": "Built things."},
        {"company": "StartupA", "title": "Senior Engineer", "start_date": "2022-08-01",
         "end_date": "2024-01-30", "duration_months": 17, "is_current": False, "industry": "Software",
         "company_size": "11-50", "description": "Built things."},
    ],
)


# ----- Honeypots -----
HONEYPOT_CHRONOLOGICAL = make_candidate(
    candidate_id="CAND_0000070",
    career_history=[
        {
            "company": "X Corp",
            "title": "Engineer",
            "start_date": "2024-12-01",
            "end_date": "2020-01-01",  # end before start
            "duration_months": 24,
            "is_current": False,
            "industry": "Software",
            "company_size": "201-500",
            "description": "Work.",
        }
    ],
)

HONEYPOT_DURATION_EXCEEDS_YOE = make_candidate(
    candidate_id="CAND_0000071",
    profile={"years_of_experience": 5.0},
    career_history=[
        {"company": "A", "title": "E", "start_date": "2014-01-01", "end_date": "2019-01-01",
         "duration_months": 60, "is_current": False, "industry": "S", "company_size": "201-500",
         "description": "Work."},
        {"company": "B", "title": "E", "start_date": "2019-01-01", "end_date": "2024-01-01",
         "duration_months": 60, "is_current": False, "industry": "S", "company_size": "201-500",
         "description": "Work."},
    ],
)

HONEYPOT_SINGLE_ROLE_EXCEEDS_YOE = make_candidate(
    candidate_id="CAND_0000072",
    profile={"years_of_experience": 3.0},
    career_history=[
        {"company": "A", "title": "E", "start_date": "2015-01-01", "end_date": None,
         "duration_months": 120, "is_current": True, "industry": "S", "company_size": "201-500",
         "description": "Work."},
    ],
)

HONEYPOT_EXPERT_ZERO_MONTHS = make_candidate(
    candidate_id="CAND_0000073",
    skills=[
        {"name": "Python", "proficiency": "expert", "endorsements": 0, "duration_months": 0},
        {"name": "TensorFlow", "proficiency": "expert", "endorsements": 0, "duration_months": 0},
        {"name": "PyTorch", "proficiency": "expert", "endorsements": 0, "duration_months": 0},
        {"name": "FAISS", "proficiency": "expert", "endorsements": 0, "duration_months": 0},
    ],
)

HONEYPOT_COMPANY_AGE = make_candidate(
    candidate_id="CAND_0000074",
    career_history=[
        {"company": "CRED", "title": "Engineer", "start_date": "2015-01-01",
         "end_date": "2020-01-01", "duration_months": 60, "is_current": False,
         "industry": "Fintech", "company_size": "1001-5000",
         "description": "Worked at CRED before it existed."},
    ],
)
