"""Shared text-mining utilities for substance / must-have probes.

Vocabularies are JD-coupled — derived from the Senior AI Engineer JD's stated
must-haves and named technologies. Each set is small, hand-curated, and tagged.
"""
from __future__ import annotations

import re


# JD-named retrieval / embedding tools
EMBEDDING_TOOLS = {
    "sentence-transformers", "sentence transformers", "bge", "e5", "openai embeddings",
    "embedding", "embeddings", "bi-encoder", "biencoder", "dense retrieval",
    "dense embedding", "sentence-bert", "sbert",
}

# JD-named vector DB / hybrid search infrastructure
VECTOR_DB_TOOLS = {
    "pinecone", "weaviate", "qdrant", "milvus", "opensearch", "elasticsearch",
    "faiss", "hnsw", "ivf", "vector database", "vector db", "vector index",
    "scann", "annoy",
}

# Ranking eval framework — JD names NDCG, MRR, MAP
RANKING_EVAL_TERMS = {
    "ndcg", "mrr", "map", "recall@", "precision@", "p@", "hit rate", "hits@",
    "offline evaluation", "offline-online", "a/b test", "ab test",
}

# Production / deployment verbs (high-SNR shipping signal)
PRODUCTION_VERBS = {
    "production", "prod", "shipped", "deployed", "deployment", "in prod",
    "users", "scale", "latency", "sla", "on-call", "on call", "throughput",
    "qps", "served", "live",
}

# Hands-on engineering verbs (shipper-side of shipper-vs-researcher)
HANDS_ON_VERBS = {
    "wrote", "built", "shipped", "deployed", "implemented", "coded", "developed",
    "engineered", "designed", "prototyped", "integrated", "refactored",
    "debugged", "optimized", "optimised", "tuned", "trained", "fine-tuned",
    "fine tuned",
}

# Research verbs (researcher-side)
RESEARCH_VERBS = {
    "researched", "explored", "investigated", "studied", "analyzed", "analysed",
    "evaluated", "compared", "measured", "examined", "surveyed",
}

# Named specific systems / tools — used for description_specificity probe.
# These are the high-SNR signals: AI-tailored resumes can fabricate generic
# verbs but rarely name specific systems with the same density.
SPECIFIC_TECHNICAL_ENTITIES = {
    # ML frameworks
    "pytorch", "tensorflow", "jax", "flax", "huggingface", "transformers",
    "sentence-transformers", "scikit-learn", "sklearn", "xgboost", "lightgbm",
    "catboost", "spacy", "nltk", "fastai",
    # LLM-specific
    "lora", "qlora", "peft", "deepspeed", "vllm", "tgi", "tensorrt", "onnx",
    "ggml", "gguf", "llama.cpp",
    # Retrieval / vector
    "bge", "e5", "openai embeddings", "instructor", "cohere embeddings",
    "faiss", "pinecone", "weaviate", "qdrant", "milvus", "scann", "annoy",
    "elasticsearch", "opensearch", "vespa",
    # Eval / observability
    "ndcg", "mrr", "map", "wandb", "weights & biases", "mlflow", "tensorboard",
    # Data infra
    "kafka", "spark", "airflow", "dbt", "snowflake", "redshift", "bigquery",
    "databricks", "delta lake", "iceberg",
    # Serving / infra
    "kubernetes", "k8s", "docker", "ray", "argo", "fastapi", "grpc",
    "redis", "postgres", "postgresql", "mongodb", "cassandra",
    # Cloud
    "aws", "gcp", "azure", "sagemaker", "vertex", "ec2", "s3", "lambda",
    # Methods
    "rag", "fine-tuning", "fine tuning", "supervised fine-tuning", "sft",
    "rlhf", "dpo", "ipo", "kto", "lstm", "transformer", "bert", "gpt",
    "diffusion", "vae", "gan", "rnn", "cnn", "attention",
    # Search / IR specific
    "bm25", "tf-idf", "tfidf", "hnsw", "ivf", "pq", "product quantization",
    "learning to rank", "ltr", "two-tower", "cross-encoder", "bi-encoder",
}

# Narrative-arc connectives — cause-effect indicators of real engineering
NARRATIVE_CONNECTIVES = {
    "because", "root cause", "led to", "resulted in", "reduced from",
    "improved by", "after discovering", "debugged", "diagnosed",
    "identified that", "found that", "we realized", "we discovered",
    "due to", "as a result", "consequently", "which caused",
    "this enabled", "this allowed", "to address", "to mitigate",
}


def _normalize(text: str) -> str:
    return (text or "").lower()


def count_tokens(text: str) -> int:
    """Crude whitespace token count."""
    return len((text or "").split())


def _is_word_token(phrase: str) -> bool:
    return " " not in phrase and "-" not in phrase and "." not in phrase


# Module-level cache of precompiled (single_words_regex, multi_word_list) per phrase set.
# Phrase sets are passed by identity, so we use id() as the cache key.
_PHRASE_CACHE: dict[int, tuple[re.Pattern, list[str]]] = {}


def _compile_phrase_set(phrases: set[str]) -> tuple[re.Pattern, list[str]]:
    key = id(phrases)
    cached = _PHRASE_CACHE.get(key)
    if cached is not None:
        return cached
    words = [p.lower() for p in phrases if _is_word_token(p)]
    multi = sorted(
        (p.lower() for p in phrases if not _is_word_token(p)),
        key=len,
        reverse=True,  # longer first to avoid partial matches
    )
    if words:
        pattern = re.compile(
            r"\b(?:" + "|".join(re.escape(w) for w in words) + r")\b",
            re.IGNORECASE,
        )
    else:
        pattern = re.compile(r"^$")  # never matches
    _PHRASE_CACHE[key] = (pattern, multi)
    return pattern, multi


def count_phrase_hits(text: str, phrases: set[str]) -> int:
    """Total count of phrase hits (each occurrence counted) within `text`."""
    if not text:
        return 0
    t = _normalize(text)
    word_re, multi = _compile_phrase_set(phrases)
    n = len(word_re.findall(t))
    for m in multi:
        n += t.count(m)
    return n


def distinct_phrase_hits(text: str, phrases: set[str]) -> int:
    """Number of distinct phrases that appear in `text` at least once."""
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
    """Map [0, ∞) → [0, 1] with saturation at `threshold`. Linear in [0, threshold]."""
    if threshold <= 0:
        return 0.0
    return min(1.0, value / threshold)
