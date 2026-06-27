"""Probe library, pure functions that score candidates against JD requirements.

Each probe returns either:
  - (score: float in [0, 1], evidence: str)        for additive / multiplicative probes
  - (fires: bool, evidence: str)                   for binary anti-SNR / hard-DQ probes

Probes are organised by SNR class and JD category:
  must_have.py      , JD's "absolutely need" requirements (high weight)
  nice_to_have.py   , JD's "would like" requirements (medium weight)
  substance.py      , anti-stuffer / trust signals (high SNR)
  anti_snr.py       , JD-explicit disqualifiers / red flags
  behavioural.py    , Redrob_signals availability + trust
  retrieval.py      , BM25 + dense cosine against the JD text
  location.py       , location, YoE band, certifications, work mode
"""
