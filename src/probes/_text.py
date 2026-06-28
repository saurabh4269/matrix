"""Shared text-mining utilities for substance / must-have probes.

Vocabularies are loaded lazily from the active JD config in src/jd_config.py.
Edit jds/*.yaml to change them; do NOT hardcode lists here.
"""
from __future__ import annotations

import re
from functools import lru_cache

from src.jd_config import get_config, register_cache_invalidator


@lru_cache(maxsize=1)
def embedding_tools() -> set[str]:
    return set(get_config().must_haves.embedding_tools)


@lru_cache(maxsize=1)
def vector_db_tools() -> set[str]:
    return set(get_config().must_haves.vector_db_tools)


@lru_cache(maxsize=1)
def ranking_eval_terms() -> set[str]:
    return set(get_config().must_haves.ranking_eval_terms)


@lru_cache(maxsize=1)
def production_verbs() -> set[str]:
    return set(get_config().substance.production_verbs)


@lru_cache(maxsize=1)
def hands_on_verbs() -> set[str]:
    return set(get_config().substance.hands_on_verbs)


@lru_cache(maxsize=1)
def research_verbs() -> set[str]:
    return set(get_config().substance.research_verbs)


@lru_cache(maxsize=1)
def specific_technical_entities() -> set[str]:
    return set(get_config().specific_technical_entities)


@lru_cache(maxsize=1)
def narrative_connectives() -> set[str]:
    return set(get_config().substance.narrative_connectives)


def _reset_caches() -> None:
    for fn in (
        embedding_tools, vector_db_tools, ranking_eval_terms,
        production_verbs, hands_on_verbs, research_verbs,
        specific_technical_entities, narrative_connectives,
    ):
        fn.cache_clear()
    _PHRASE_CACHE.clear()


register_cache_invalidator(_reset_caches)


# Backwards-compat aliases (uppercase symbol names referenced elsewhere).
def __getattr__(name: str):
    if name == "EMBEDDING_TOOLS":
        return embedding_tools()
    if name == "VECTOR_DB_TOOLS":
        return vector_db_tools()
    if name == "RANKING_EVAL_TERMS":
        return ranking_eval_terms()
    if name == "PRODUCTION_VERBS":
        return production_verbs()
    if name == "HANDS_ON_VERBS":
        return hands_on_verbs()
    if name == "RESEARCH_VERBS":
        return research_verbs()
    if name == "SPECIFIC_TECHNICAL_ENTITIES":
        return specific_technical_entities()
    if name == "NARRATIVE_CONNECTIVES":
        return narrative_connectives()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    return (text or "").lower()


def count_tokens(text: str) -> int:
    return len((text or "").split())


def _is_word_token(phrase: str) -> bool:
    return " " not in phrase and "-" not in phrase and "." not in phrase


# Cache of (single_word_regex, multi_word_list) per phrase-set identity.
_PHRASE_CACHE: dict[int, tuple[re.Pattern, list[str]]] = {}


def _compile_phrase_set(phrases) -> tuple[re.Pattern, list[str]]:
    """Accept any iterable; build a precompiled alternation + multi-word list."""
    phrases = set(phrases)
    key = id(phrases)
    cached = _PHRASE_CACHE.get(key)
    if cached is not None:
        return cached
    words = [p.lower() for p in phrases if _is_word_token(p)]
    multi = sorted(
        (p.lower() for p in phrases if not _is_word_token(p)),
        key=len, reverse=True,
    )
    if words:
        pattern = re.compile(
            r"\b(?:" + "|".join(re.escape(w) for w in words) + r")\b",
            re.IGNORECASE,
        )
    else:
        pattern = re.compile(r"^$")
    _PHRASE_CACHE[key] = (pattern, multi)
    return pattern, multi


def count_phrase_hits(text: str, phrases) -> int:
    if not text:
        return 0
    t = _normalize(text)
    word_re, multi = _compile_phrase_set(phrases)
    n = len(word_re.findall(t))
    for m in multi:
        n += t.count(m)
    return n


def distinct_phrase_hits(text: str, phrases) -> int:
    if not text:
        return 0
    t = _normalize(text)
    word_re, multi = _compile_phrase_set(phrases)
    distinct = set(m.lower() for m in word_re.findall(t))
    for m in multi:
        if m in t:
            distinct.add(m)
    return len(distinct)


def saturating(value: float, threshold: float) -> float:
    if threshold <= 0:
        return 0.0
    return min(1.0, value / threshold)
