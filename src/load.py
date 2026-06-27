"""Streaming candidate loader.

Operates on the 100K-record `candidates.jsonl` file without loading the whole
thing into memory. Yields validated Candidate objects one at a time.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Iterator

from src.schema import Candidate


def iter_candidates(path: str | Path) -> Iterator[Candidate]:
    """Yield Candidate objects from a .jsonl or .jsonl.gz file."""
    p = Path(path)
    opener = gzip.open if p.suffix == ".gz" else open
    with opener(p, "rt", encoding="utf-8") as fp:
        for line in fp:
            if not line.strip():
                continue
            obj = json.loads(line)
            yield Candidate.model_validate(obj)


def count_candidates(path: str | Path) -> int:
    """Cheap line count of the candidates file (matches yielded record count)."""
    p = Path(path)
    opener = gzip.open if p.suffix == ".gz" else open
    n = 0
    with opener(p, "rb") as fp:
        for line in fp:
            if line.strip():
                n += 1
    return n
