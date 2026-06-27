"""Location / logistics / certifications — low-weight additive probes."""
from __future__ import annotations

from src.probes._text import saturating
from src.schema import Candidate


PREFERRED_LOCATIONS = {
    "pune", "noida", "delhi", "new delhi", "ncr", "gurugram", "gurgaon",
    "mumbai", "bangalore", "bengaluru", "hyderabad", "chennai",
}


def location_match(cand: Candidate) -> tuple[float, str]:
    """Boost if location is one of the JD-preferred Indian metros OR willing to relocate."""
    loc = (cand.profile.location or "").lower()
    if any(city in loc for city in PREFERRED_LOCATIONS):
        return 1.0, f"located in preferred city: {cand.profile.location}"
    if cand.redrob_signals.willing_to_relocate:
        return 0.7, f"willing to relocate from {cand.profile.location}"
    country = (cand.profile.country or "").lower()
    if country == "india":
        return 0.5, f"in India but not preferred city ({cand.profile.location})"
    return 0.1, f"outside India, not willing to relocate ({cand.profile.location})"


def yoe_band_fit(cand: Candidate) -> tuple[float, str]:
    """JD wants 5–9 years; gaussian centered on 7y."""
    import math
    yoe = cand.profile.years_of_experience
    if yoe <= 0:
        return 0.0, "no experience claimed"
    sigma = 2.5
    score = math.exp(-((yoe - 7) ** 2) / (2 * sigma**2))
    return score, f"{yoe:.1f}y experience (JD target 5–9y, peak 7y)"


def certifications_micro_boost(cand: Candidate) -> tuple[float, str]:
    """Cloud certs (AWS/GCP/Azure) or known ML courses — small positive."""
    known_issuers = {"aws", "amazon", "google", "gcp", "azure", "microsoft",
                     "coursera", "deeplearning.ai", "fast.ai", "stanford"}
    known_keywords = {"aws", "gcp", "azure", "tensorflow", "pytorch",
                      "machine learning", "deep learning", "data science"}
    boost = 0.0
    relevant_names = []
    for c in cand.certifications:
        issuer = (c.issuer or "").lower()
        name = (c.name or "").lower()
        if any(k in issuer for k in known_issuers) or any(k in name for k in known_keywords):
            boost += 0.1
            relevant_names.append(c.name)
    score = min(0.3, boost)
    if score == 0:
        return 0.0, ""
    return score, f"{len(relevant_names)} relevant cert(s): {', '.join(relevant_names[:2])}"


ALL_LOCATION_PROBES = [
    ("location_match", location_match),
    ("yoe_band_fit", yoe_band_fit),
    ("certifications_micro_boost", certifications_micro_boost),
]


def run_all(cand: Candidate) -> list[tuple[str, float, str]]:
    return [
        (name, score, ev)
        for name, fn in ALL_LOCATION_PROBES
        for score, ev in [fn(cand)]
        if score > 0
    ]
