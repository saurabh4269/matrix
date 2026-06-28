"""Per-JD configuration, loaded from YAML.

The ranker code reads from `get_config()`. The default config is
`jds/ai_engineer.yaml`, which encodes the exact Senior AI Engineer JD this
submission is calibrated for. To swap in a different JD, call `set_config()`
with a different loaded JDConfig before the probes / scoring run.

This file is the SINGLE source of all JD-specific things. Nothing else in
src/ should hardcode a vocabulary, a regex, a weight, or a company list.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class JDDigest(BaseModel):
    """The user-facing JD summary shown on the landing screen."""
    role: str
    location: str
    experience: str
    style: str
    avoid: list[str]


class YoESpec(BaseModel):
    """Target experience-band for `yoe_band_fit` probe."""
    peak: float = 7.0
    sigma: float = 2.5


class LocationSpec(BaseModel):
    """JD location preference + visa policy."""
    preferred_cities: list[str] = Field(default_factory=list)
    country: str = ""
    visa_sponsorship: bool = False


class CompaniesSpec(BaseModel):
    """Company-classification dictionaries."""
    consulting_firms: list[str] = Field(default_factory=list)
    product_companies: list[str] = Field(default_factory=list)
    named_employers: list[str] = Field(default_factory=list)


class SizesSpec(BaseModel):
    """Company-size buckets used by stage-alignment / bigcorp probes."""
    bigcorp_size: str = "10001+"
    small_mid_sizes: list[str] = Field(default_factory=list)


class MustHaveSpec(BaseModel):
    """JD's `absolutely need` vocabulary."""
    python_skill_name: str = "Python"
    embedding_tools: list[str] = Field(default_factory=list)
    vector_db_tools: list[str] = Field(default_factory=list)
    ranking_eval_terms: list[str] = Field(default_factory=list)
    framework_skills: list[str] = Field(default_factory=list)


class SubstanceVocab(BaseModel):
    """Substance probe vocabularies + research-org regex."""
    hands_on_verbs: list[str] = Field(default_factory=list)
    research_verbs: list[str] = Field(default_factory=list)
    production_verbs: list[str] = Field(default_factory=list)
    manager_verbs: list[str] = Field(default_factory=list)
    deployment_verbs: list[str] = Field(default_factory=list)
    narrative_connectives: list[str] = Field(default_factory=list)
    research_org_pattern: str = ""


class TitlePatterns(BaseModel):
    """Regexes that classify candidate titles.

    relevant_titles : matches a candidate as "in the JD's core domain"
    nlp_ir          : matches the JD's specific subdomain (NLP / IR for AI Eng)
    excluded_subdomain : adjacent-but-not-relevant fields (CV / speech / robotics
                        for AI Eng); triggers anti-SNR `cv_speech_robo_only` if
                        the candidate is *only* in this subdomain.
    """
    relevant_titles: str
    nlp_ir: str = ""
    excluded_subdomain: str = ""


class Weights(BaseModel):
    """All scoring weights live here so a JD can re-tune without code changes."""
    must_have: dict[str, float] = Field(default_factory=dict)
    substance: dict[str, float] = Field(default_factory=dict)
    anti_snr: dict[str, float] = Field(default_factory=dict)
    retrieval: dict[str, float] = Field(default_factory=dict)
    location: dict[str, float] = Field(default_factory=dict)
    category: dict[str, float] = Field(default_factory=dict)
    behavioural: dict[str, float] = Field(default_factory=dict)


class JDConfig(BaseModel):
    """One JD = one of these. Everything probe-relevant is here."""
    model_config = ConfigDict(extra="forbid")

    name: str
    display_name: str

    digest: JDDigest

    # Full JD text, used by precompute for BM25 + dense retrieval
    jd_text: str

    yoe: YoESpec = Field(default_factory=YoESpec)
    location: LocationSpec = Field(default_factory=LocationSpec)
    title_patterns: TitlePatterns

    must_haves: MustHaveSpec = Field(default_factory=MustHaveSpec)
    substance: SubstanceVocab = Field(default_factory=SubstanceVocab)
    specific_technical_entities: list[str] = Field(default_factory=list)

    companies: CompaniesSpec = Field(default_factory=CompaniesSpec)
    sizes: SizesSpec = Field(default_factory=SizesSpec)
    honeypot_company_ages: dict[str, int] = Field(default_factory=dict)

    weights: Weights = Field(default_factory=Weights)


# ---------------------------------------------------------------------------
# Loader + global accessor
# ---------------------------------------------------------------------------

_DEFAULT_JD_PATH = Path(__file__).resolve().parent.parent / "jds" / "ai_engineer.yaml"
_active_config: Optional[JDConfig] = None


def load_jd(path: str | Path) -> JDConfig:
    """Read a JD YAML file from disk."""
    with open(path, "r", encoding="utf-8") as fp:
        data = yaml.safe_load(fp)
    return JDConfig.model_validate(data)


def list_available_jds() -> list[Path]:
    """List all jds/*.yaml in the repo (for the JD-selector UI)."""
    jds_dir = _DEFAULT_JD_PATH.parent
    if not jds_dir.exists():
        return []
    return sorted(jds_dir.glob("*.yaml"))


def get_config() -> JDConfig:
    """Return the active JD config. Loads `jds/ai_engineer.yaml` on first call."""
    global _active_config
    if _active_config is None:
        _active_config = load_jd(_DEFAULT_JD_PATH)
    return _active_config


def set_config(cfg: JDConfig) -> None:
    """Swap the active JD config. Call before importing probe modules if you
    want them to pick up new vocabularies at module-import time."""
    global _active_config
    _active_config = cfg
    # Invalidate downstream caches (regexes built from vocabularies, etc.)
    _invalidate_caches()


# ---------------------------------------------------------------------------
# Cache invalidation hooks. Probe modules that pre-compile regexes from the
# active config register their reset functions here.
# ---------------------------------------------------------------------------

_cache_invalidators: list = []


def register_cache_invalidator(fn) -> None:
    _cache_invalidators.append(fn)


def _invalidate_caches() -> None:
    for fn in _cache_invalidators:
        try:
            fn()
        except Exception:
            pass
