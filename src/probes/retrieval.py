"""Hybrid retrieval probes, BM25 and dense-embedding cosine against the JD.

Both scores are read from pre-computed artefacts (data/bm25_scores.npy +
data/dense_scores.npy). At ranking time we only do an O(1) dict lookup
per candidate, no embedding model loaded, no compute on the hot path.

This module returns a (score, evidence) per probe per candidate; the
scorer composes them as one additive feature group with weight α·bm25 +
(1−α)·dense_cos per the spec.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from src.probes._text import saturating
from src.schema import Candidate


_DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# Loaded lazily on first use
_bm25_by_id: dict[str, float] | None = None
_dense_by_id: dict[str, float] | None = None
_bm25_max: float = 1.0
_dense_max: float = 1.0


def _load_artefacts() -> bool:
    """Load BM25 + (optional) dense artefacts. Returns True if at least BM25 is usable.

    Dense embeddings are an optional second channel; if dense_scores.npy is
    missing (e.g. embedding precompute didn't finish), we run with BM25 only.
    """
    global _bm25_by_id, _dense_by_id, _bm25_max, _dense_max

    if _bm25_by_id is not None:
        return True

    ids_path = _DATA_DIR / "candidate_ids.json"
    bm25_path = _DATA_DIR / "bm25_scores.npy"
    dense_path = _DATA_DIR / "dense_scores.npy"

    if not ids_path.exists() or not bm25_path.exists():
        return False

    with open(ids_path, "r", encoding="utf-8") as fp:
        ids = json.load(fp)
    bm25 = np.load(bm25_path)
    _bm25_by_id = dict(zip(ids, bm25.tolist()))
    _bm25_max = max(_bm25_by_id.values()) if _bm25_by_id else 1.0

    if dense_path.exists():
        dense = np.load(dense_path)
        _dense_by_id = dict(zip(ids, dense.tolist()))
        _dense_max = max(_dense_by_id.values()) if _dense_by_id else 1.0
    else:
        _dense_by_id = {}
        _dense_max = 1.0
    return True


def bm25_jd_match(cand: Candidate) -> tuple[float, str]:
    """BM25 score of the JD against this candidate's text, normalized."""
    if not _load_artefacts() or _bm25_by_id is None:
        return 0.0, ""
    raw = _bm25_by_id.get(cand.candidate_id, 0.0)
    if raw <= 0 or _bm25_max <= 0:
        return 0.0, ""
    score = raw / _bm25_max
    return saturating(score, threshold=0.6), f"BM25 score {raw:.2f} (top corpus = {_bm25_max:.2f})"


def dense_cosine_jd_match(cand: Candidate) -> tuple[float, str]:
    """Dense embedding cosine. Returns 0 if dense artefacts not available."""
    if not _load_artefacts() or not _dense_by_id:
        return 0.0, ""
    raw = _dense_by_id.get(cand.candidate_id, 0.0)
    if raw <= 0:
        return 0.0, ""
    return saturating(raw, threshold=0.7), f"semantic similarity {raw:.3f}"


ALL_RETRIEVAL_PROBES = [
    ("bm25_jd_match", bm25_jd_match),
    ("dense_cosine_jd_match", dense_cosine_jd_match),
]


def run_all(cand: Candidate) -> list[tuple[str, float, str]]:
    return [
        (name, score, ev)
        for name, fn in ALL_RETRIEVAL_PROBES
        for score, ev in [fn(cand)]
        if score > 0
    ]
