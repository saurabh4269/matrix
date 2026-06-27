"""Cheap heuristics for stratified sampling and pre-fired structural flags.

These run in a single pass per candidate, ~1ms each. They are intentionally
crude — calibration ground truth comes from hand-labelling, not these.
"""
from __future__ import annotations

import re

from src.schema import Candidate


# Title regexes — coarse but sufficient for stratification heuristics
_ML_TITLE_RE = re.compile(
    r"\b("
    r"ml|machine[\s\-]?learning|ai|artificial[\s\-]?intelligence|"
    r"applied[\s\-]?scientist|research[\s\-]?engineer|"
    r"data[\s\-]?scientist|nlp|natural[\s\-]?language|"
    r"search[\s\-]?engineer|information[\s\-]?retrieval|"
    r"recommendation|ranking|retrieval|relevance"
    r")\b",
    re.IGNORECASE,
)

_RETRIEVAL_VERB_RE = re.compile(
    r"\b("
    r"retriev|rank|embedding|vector|bm25|faiss|pinecone|weaviate|qdrant|"
    r"milvus|opensearch|elasticsearch|hnsw|"
    r"ndcg|mrr|map|recall@|hit[\s\-]?rate|"
    r"bge|e5|sentence[\s\-]?transformer|cross[\s\-]?encoder|"
    r"recommendation|relevance|semantic[\s\-]?search"
    r")\b",
    re.IGNORECASE,
)

_PRODUCTION_VERB_RE = re.compile(
    r"\b("
    r"production|prod|shipped|deployed|deployment|in[\s\-]?prod|"
    r"users|scale|latency|sla|on[\s\-]?call|throughput|qps"
    r")\b",
    re.IGNORECASE,
)

# Indian IT services / consulting firms (the JD's hard-no list)
CONSULTING_FIRMS = {
    "tcs", "tata consultancy services", "tata consultancy",
    "infosys", "wipro", "accenture", "cognizant", "capgemini",
    "hcl", "hcl technologies", "lti", "larsen & toubro infotech",
    "mindtree", "tech mahindra", "mphasis", "ibm services",
    "deloitte", "kpmg", "ey", "pwc",
}

# Product companies — broad list including FAANG, Indian unicorns, global ML/IR
# This is intentionally generous. Used as a soft positive signal.
PRODUCT_COMPANIES = {
    # FAANG / big tech (these also trigger bigcorp_only at scale)
    "google", "meta", "facebook", "amazon", "apple", "microsoft", "netflix",
    "openai", "anthropic", "cohere", "databricks", "snowflake",
    # Indian unicorns
    "swiggy", "zomato", "ola", "uber", "razorpay", "cred", "phonepe",
    "paytm", "freshworks", "zoho", "byju", "unacademy", "meesho",
    "nykaa", "lenskart", "urban company", "udaan", "policybazaar",
    # ML/IR known
    "stripe", "shopify", "airbnb", "pinterest", "spotify", "linkedin",
    "twitter", "reddit", "discord", "notion", "linear", "vercel",
    "scale ai", "hugging face", "weights & biases", "scale",
}

BIGCORP_SIZE = "10001+"
SMALL_MID_SIZES = {"11-50", "51-200", "201-500"}


def _normalize_company(name: str) -> str:
    return name.strip().lower()


def has_ml_title_anywhere(cand: Candidate) -> bool:
    """Any past or current title contains an ML/AI/IR signal."""
    if _ML_TITLE_RE.search(cand.profile.current_title or ""):
        return True
    return any(_ML_TITLE_RE.search(r.title or "") for r in cand.career_history)


def has_ml_title_current(cand: Candidate) -> bool:
    return bool(_ML_TITLE_RE.search(cand.profile.current_title or ""))


def retrieval_mentions_in_descriptions(cand: Candidate) -> int:
    text = " ".join(r.description or "" for r in cand.career_history)
    return len(_RETRIEVAL_VERB_RE.findall(text))


def production_mentions_in_descriptions(cand: Candidate) -> int:
    text = " ".join(r.description or "" for r in cand.career_history)
    return len(_PRODUCTION_VERB_RE.findall(text))


def is_consulting_only_career(cand: Candidate) -> bool:
    if not cand.career_history:
        return False
    return all(
        _normalize_company(r.company) in CONSULTING_FIRMS
        for r in cand.career_history
    )


def is_bigcorp_only_career(cand: Candidate) -> bool:
    if not cand.career_history:
        return False
    return all(r.company_size == BIGCORP_SIZE for r in cand.career_history)


def has_product_company_in_history(cand: Candidate) -> bool:
    return any(
        _normalize_company(r.company) in PRODUCT_COMPANIES
        for r in cand.career_history
    )


def count_jd_keyword_skills(cand: Candidate) -> int:
    """Count of skills that match JD's named technologies (keyword density proxy)."""
    keywords = {
        "rag", "pinecone", "weaviate", "qdrant", "faiss", "milvus",
        "embedding", "embeddings", "bge", "e5", "sentence-transformers",
        "vector search", "vector database", "vector db",
        "fine-tuning llms", "fine-tuning", "fine tuning",
        "lora", "qlora", "peft", "langchain", "llamaindex",
        "elasticsearch", "opensearch", "ndcg", "mrr",
        "transformers", "transformer", "llm", "llms",
        "semantic search", "ranking", "retrieval",
        "ml", "machine learning", "deep learning", "nlp",
    }
    n = 0
    for s in cand.skills:
        if s.name.strip().lower() in keywords:
            n += 1
    return n


# ---------------------------------------------------------------------------
# Honeypot-suspect heuristics (used for bucket E in sampling — NOT the final
# honeypot detector; that lives in src/honeypot.py with stricter rules).
# ---------------------------------------------------------------------------

def salary_paradox(cand: Candidate) -> bool:
    s = cand.redrob_signals.expected_salary_range_inr_lpa
    return s.min > s.max and s.max > 0


def date_inversion_in_career(cand: Candidate) -> bool:
    for r in cand.career_history:
        if r.start_date and r.end_date:
            if r.start_date > r.end_date:
                return True
    return False


def duration_exceeds_experience(cand: Candidate) -> bool:
    total_months = sum(r.duration_months for r in cand.career_history)
    return total_months / 12.0 > cand.profile.years_of_experience + 2


def single_role_exceeds_experience(cand: Candidate) -> bool:
    yoe_months = cand.profile.years_of_experience * 12
    return any(r.duration_months > yoe_months + 12 for r in cand.career_history)


def expert_with_zero_months(cand: Candidate) -> bool:
    n = sum(1 for s in cand.skills if s.proficiency == "expert" and s.duration_months == 0)
    return n >= 3


def fires_any_structural_paradox(cand: Candidate) -> list[str]:
    """Returns a list of paradox names that fire. Used for honeypot bucket sampling
    and as pre-fired flags on the labelling cards.

    NOTE: salary_paradox (min > max) is excluded — empirical check shows
    18.9% of the synthesized dataset has min > max, so it's a data-generation
    artifact, not a honeypot signal. The function `salary_paradox()` is kept
    around for diagnostics but not used here.
    """
    flags = []
    if date_inversion_in_career(cand):
        flags.append("date_inversion")
    if duration_exceeds_experience(cand):
        flags.append("duration>experience")
    if single_role_exceeds_experience(cand):
        flags.append("single_role>experience")
    if expert_with_zero_months(cand):
        flags.append("expert_zero_months")
    return flags


# ---------------------------------------------------------------------------
# Bucket assignment — single pass, mutually exclusive priority order
# ---------------------------------------------------------------------------

def assign_bucket(cand: Candidate) -> str:
    """Assign each candidate to exactly one stratification bucket.

    Priority order (first match wins) is calibrated so each bucket gets a
    distinct candidate population. Six mutually-exclusive buckets:
      likely_tier5, likely_tier4, adjacent_mid, likely_keyword_stuffer,
      honeypot_suspect, random_control.
    """
    paradoxes = fires_any_structural_paradox(cand)

    has_ml_now = has_ml_title_current(cand)
    has_ml_ever = has_ml_title_anywhere(cand)
    retrieval_mentions = retrieval_mentions_in_descriptions(cand)
    has_product_co = has_product_company_in_history(cand)
    jd_kw_count = count_jd_keyword_skills(cand)

    # Likely tier-5: ML title (now) + product co + retrieval substance.
    # Tier-5 wins even if a paradox also fires — that's a labelling discovery
    # worth surfacing (real candidate flagged as honeypot would be a false-positive
    # honeypot rule we want to find).
    if has_ml_now and has_product_co and retrieval_mentions >= 2:
        return "likely_tier5"

    # Honeypot suspect: structural paradox fires AND not tier-5-like.
    # These are the candidates the honeypot detector should catch.
    if paradoxes:
        return "honeypot_suspect"

    # Likely tier-4: ML title (anywhere) + (product co OR strong retrieval).
    if has_ml_ever and (has_product_co or retrieval_mentions >= 3):
        return "likely_tier4"

    # Keyword-stuffer trap: high JD-keyword density + NO ML title + low retrieval
    # substance. Keywords on the surface, no execution underneath.
    if jd_kw_count >= 6 and not has_ml_ever and retrieval_mentions <= 1:
        return "likely_keyword_stuffer"

    # Adjacent-mid: some signal but not at tier-4 level.
    if has_ml_ever or retrieval_mentions >= 1 or jd_kw_count >= 2:
        return "adjacent_mid"

    # Random control: no signal in any direction. Boring negatives — necessary
    # to anchor the bottom of the relevance scale during weight tuning.
    return "random_control"
