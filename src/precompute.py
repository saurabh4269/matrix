"""Pre-computation pipeline, embeddings + BM25 index for hybrid retrieval.

Runs once, **outside** the 5-minute ranking budget. Outputs:
  data/candidate_ids.json       , list of candidate IDs in row order
  data/embeddings.npy           , float32 array of shape (N, 384)
  data/bm25_corpus.pkl          , pickled BM25Okapi index
  data/jd_text.txt              , the JD text used (for reproducibility)

Usage:
    python -m src.precompute --candidates ./candidates.jsonl --out-dir ./data

Model: all-MiniLM-L6-v2 (384-dim, ~80MB). Chosen for speed + size, not peak
accuracy. The score it produces is a *complementary signal* alongside the
structured probes, not the primary scorer.
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np

from src.load import iter_candidates
from src.schema import Candidate


# The JD's text, manually distilled from the official job_description.docx.
# Kept here in code (rather than read at runtime) so the precompute step is
# fully reproducible and self-contained.
JD_TEXT = """
Senior AI Engineer, Founding Team at Redrob AI, a Series A AI-native talent
intelligence platform. Pune or Noida, India. Hybrid. 5-9 years of experience.

We need:
  - Production experience with embeddings-based retrieval systems
    (sentence-transformers, OpenAI embeddings, BGE, E5, bi-encoder, dense retrieval).
    Real production deployment, embedding drift, index refresh, retrieval-quality
    regression in production.
  - Production experience with vector databases or hybrid search infrastructure
    (Pinecone, Weaviate, Qdrant, Milvus, OpenSearch, Elasticsearch, FAISS, HNSW).
  - Strong Python.
  - Hands-on experience designing evaluation frameworks for ranking systems,
    NDCG, MRR, MAP, offline-to-online correlation, A/B test interpretation.

Nice to have:
  - LLM fine-tuning experience (LoRA, QLoRA, PEFT).
  - Learning-to-rank models (XGBoost-rank or neural LTR).
  - Prior HR-tech, recruiting, marketplace product exposure.
  - Distributed systems or large-scale inference optimization.
  - Open-source contributions in AI/ML.

Avoid: consulting-only careers (TCS/Infosys/Wipro/etc), pure research-only
careers without production, framework enthusiasts (LangChain tutorial level),
title-chasers (1.5-year job-hop pattern), CV/speech/robotics specialists
without NLP/IR exposure.

The hire will own the intelligence layer, ranking, retrieval, and matching
systems. They will ship a v2 ranking system, set up evaluation infrastructure,
and drive long-term architecture as the engineering team grows from 4 to 12.
""".strip()


def _candidate_text(c: Candidate) -> str:
    """Build the embedding/BM25 input for a candidate.

    Concatenates: headline + summary + each role's description.
    Lowercase + stripped, BM25 tokenization expects this.
    """
    parts = [
        c.profile.headline or "",
        c.profile.summary or "",
    ]
    for r in c.career_history:
        parts.append(f"{r.title} at {r.company}: {r.description or ''}")
    text = " ".join(parts).strip()
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--out-dir", default="./data")
    ap.add_argument(
        "--model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="HuggingFace model id for the dense embedder.",
    )
    ap.add_argument("--batch-size", type=int, default=128)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Persist the JD text used
    (out_dir / "jd_text.txt").write_text(JD_TEXT, encoding="utf-8")

    # ---- Load candidates + build text corpus + BM25 index ----
    print(f"Loading candidates from {args.candidates}…", file=sys.stderr)
    t0 = time.time()
    ids: list[str] = []
    texts: list[str] = []
    tokens_for_bm25: list[list[str]] = []
    for c in iter_candidates(args.candidates):
        ids.append(c.candidate_id)
        text = _candidate_text(c)
        texts.append(text)
        tokens_for_bm25.append(text.lower().split())
    print(f"  Loaded {len(ids):,} candidates in {time.time()-t0:.1f}s", file=sys.stderr)

    # ---- BM25 index ----
    print("Building BM25 index…", file=sys.stderr)
    t0 = time.time()
    from rank_bm25 import BM25Okapi
    bm25 = BM25Okapi(tokens_for_bm25)
    with open(out_dir / "bm25_corpus.pkl", "wb") as fp:
        pickle.dump(bm25, fp)
    print(f"  BM25 built in {time.time()-t0:.1f}s", file=sys.stderr)

    # Pre-compute the JD's BM25 score against the whole corpus so we can ship
    # that directly (the BM25Okapi pickle is ~hundreds of MB; ship the score
    # vector instead).
    print("Scoring JD against corpus…", file=sys.stderr)
    t0 = time.time()
    bm25_scores = bm25.get_scores(JD_TEXT.lower().split())
    np.save(out_dir / "bm25_scores.npy", bm25_scores.astype(np.float32))
    print(
        f"  BM25 scored {len(bm25_scores):,} candidates in {time.time()-t0:.1f}s "
        f"(max={bm25_scores.max():.2f}, mean={bm25_scores.mean():.2f})",
        file=sys.stderr,
    )

    # ---- Dense embeddings ----
    print(f"Loading model {args.model}…", file=sys.stderr)
    t0 = time.time()
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(args.model)
    print(f"  Model loaded in {time.time()-t0:.1f}s", file=sys.stderr)

    print(f"Embedding {len(texts):,} candidates (batch_size={args.batch_size})…", file=sys.stderr)
    t0 = time.time()
    emb = model.encode(
        texts,
        batch_size=args.batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,  # so we can use raw dot-product as cosine
    ).astype(np.float32)
    print(f"  Embedded in {time.time()-t0:.1f}s (shape={emb.shape})", file=sys.stderr)

    jd_emb = model.encode(
        [JD_TEXT],
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype(np.float32)

    # Cosine = dot product since normalized
    dense_scores = (emb @ jd_emb.T).flatten()

    np.save(out_dir / "embeddings.npy", emb)
    np.save(out_dir / "dense_scores.npy", dense_scores)

    with open(out_dir / "candidate_ids.json", "w", encoding="utf-8") as fp:
        json.dump(ids, fp)

    print(
        f"\nDone. Artefacts written to {out_dir}:",
        file=sys.stderr,
    )
    for f in sorted(out_dir.iterdir()):
        size_mb = f.stat().st_size / 1e6
        print(f"  {f.name:30s}  {size_mb:7.1f} MB", file=sys.stderr)


if __name__ == "__main__":
    main()
