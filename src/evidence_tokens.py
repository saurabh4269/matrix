"""Extract the exact tokens the ranker considered — for UI highlighting.

Every token we return has to satisfy TWO constraints:
  1. It appears in the active JD's declared vocabulary (must_haves,
     specific_technical_entities, companies, etc.). No JD-vocab hit → not
     ours to highlight.
  2. It appears verbatim (case-insensitive) somewhere in the candidate's
     summary or a career-history description. If we can't point at real text,
     we don't highlight.

This is an anti-hallucination guarantee: every highlighted token has a
verifiable source both in the JD and in the resume.

Two buckets:
  - positive tokens: come from the JD's positive vocabularies
  - concern tokens: come from the JD's consulting_firms (or other negative
    dictionaries in the future)

Returns duplicates deduplicated + sorted for stable output.
"""
from __future__ import annotations

import re

from src.jd_config import JDConfig
from src.schema import Candidate


def _profile_text(cand: Candidate) -> str:
    """Concatenate all text a recruiter would see on the resume."""
    parts: list[str] = []
    if cand.profile.summary:
        parts.append(cand.profile.summary)
    if cand.profile.headline:
        parts.append(cand.profile.headline)
    for role in cand.career_history:
        parts.append(role.title or "")
        parts.append(role.company or "")
        if role.description:
            parts.append(role.description)
    return "\n".join(parts)


def _positive_vocab(cfg: JDConfig) -> list[str]:
    """Every token from the JD's positive vocabularies, lowercased + dedup."""
    seen: set[str] = set()
    out: list[str] = []
    for src in (
        cfg.must_haves.embedding_tools,
        cfg.must_haves.vector_db_tools,
        cfg.must_haves.ranking_eval_terms,
        cfg.must_haves.framework_skills,
        cfg.specific_technical_entities,
        cfg.companies.product_companies,
        cfg.companies.named_employers,
    ):
        for t in src:
            t = (t or "").strip()
            if not t:
                continue
            key = t.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(t)
    # Also the JD's primary language name
    py = cfg.must_haves.python_skill_name
    if py and py.lower() not in seen:
        seen.add(py.lower())
        out.append(py)
    return out


def _concern_vocab(cfg: JDConfig) -> list[str]:
    """Concern-tone tokens (consulting firms + JD-declared avoid targets)."""
    seen: set[str] = set()
    out: list[str] = []
    for t in cfg.companies.consulting_firms:
        t = (t or "").strip()
        if not t:
            continue
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


def _find_in_text(text_lower: str, tokens: list[str]) -> list[str]:
    """Return tokens that appear as whole words (case-insensitive) in text.

    Whole-word constraint prevents e.g. 'go' matching 'Google', or 'r'
    matching every noun. Short tokens (<3 chars) are dropped for that reason.
    """
    out: list[str] = []
    for t in tokens:
        if len(t) < 3:
            continue
        # \b for whole word, escape special chars in the token
        pat = r"\b" + re.escape(t.lower()) + r"\b"
        if re.search(pat, text_lower):
            out.append(t)
    return out


def extract_matched_tokens(
    cand: Candidate,
    cfg: JDConfig,
) -> dict[str, list[str]]:
    """Return matched tokens by tone. Both lists are deduped + sorted."""
    text = _profile_text(cand)
    text_lower = text.lower()

    positive = _find_in_text(text_lower, _positive_vocab(cfg))
    concern = _find_in_text(text_lower, _concern_vocab(cfg))

    return {
        "positive": sorted(set(positive)),
        "concern": sorted(set(concern)),
    }
