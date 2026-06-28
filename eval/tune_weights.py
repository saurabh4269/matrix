"""Learn probe weights from labelled data using LightGBM-Rank.

Run after `python -m eval.merge_labels` produces eval/labelled.jsonl.

  python -m eval.tune_weights \\
      --candidates  C:/.../candidates.jsonl  \\
      --labels      eval/labelled.jsonl       \\
      --out         eval/learned_weights.yaml

The script:
  1. Loads the labelled candidates + their tier (0-5)
  2. Computes every probe score for each candidate (the same code path as
     rank.py uses)
  3. Builds a feature matrix X (candidates × probes) and a relevance vector
     y (tier 0-5)
  4. Fits a LightGBM-Ranker with pairwise loss and NDCG@10 eval metric
  5. Extracts the model's feature importances and treats them as relative
     probe weights inside each category
  6. Writes a learned-weights YAML that can be merged into a JD config

This is the single highest-impact math addition we can make. It just needs
the labels.

If LightGBM is unavailable, falls back to a simple least-squares fit against
the per-candidate score sum, which is theoretically weaker but works without
extra dependencies.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml

from src.load import iter_candidates
from src.scoring import (
    ANTI_SNR_WEIGHTS,
    LOCATION_WEIGHTS,
    MUST_HAVE_WEIGHTS,
    RETRIEVAL_WEIGHTS,
    SUBSTANCE_WEIGHTS,
    score_candidate,
)


# Each row in the feature matrix is laid out as:
#   [must_have probes...] [substance probes...] [retrieval probes...]
#   [location probes...] [anti_snr probes...] [behavioural raw values]
FEATURE_ORDER = (
    [("must_have", k) for k in MUST_HAVE_WEIGHTS]
    + [("substance", k) for k in SUBSTANCE_WEIGHTS]
    + [("retrieval", k) for k in RETRIEVAL_WEIGHTS]
    + [("location", k) for k in LOCATION_WEIGHTS]
    + [("anti_snr", k) for k in ANTI_SNR_WEIGHTS]
)
N_FEATS = len(FEATURE_ORDER)


def build_feature_row(cs) -> np.ndarray:
    """Project a CandidateScore into the feature vector."""
    by_cat = defaultdict(dict)
    for cat_name, items in [
        ("must_have", cs.must_have),
        ("substance", cs.substance),
        ("retrieval", cs.retrieval),
        ("location", cs.location_probes),
        ("anti_snr", cs.anti_snr),
    ]:
        for name, score, _ in items:
            by_cat[cat_name][name] = score
    row = np.zeros(N_FEATS, dtype=np.float64)
    for i, (cat, name) in enumerate(FEATURE_ORDER):
        row[i] = by_cat.get(cat, {}).get(name, 0.0)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", required=True, help="Path to candidates.jsonl")
    ap.add_argument("--labels", default="eval/labelled.jsonl",
                    help="Path to labelled.jsonl from merge_labels")
    ap.add_argument("--out", default="eval/learned_weights.yaml",
                    help="Where to write the learned-weights YAML")
    args = ap.parse_args()

    # Load labels into {candidate_id: tier}
    label_by_id: dict[str, int] = {}
    with open(args.labels, "r", encoding="utf-8") as fp:
        for line in fp:
            if not line.strip():
                continue
            obj = json.loads(line)
            cid = obj["candidate"]["candidate_id"]
            tier = obj.get("label", {}).get("tier")
            if tier is not None:
                label_by_id[cid] = int(tier)

    if not label_by_id:
        print("FATAL: no labels found. Run `python -m eval.merge_labels` first.",
              file=sys.stderr)
        sys.exit(1)
    print(f"Loaded {len(label_by_id)} labelled candidates.", file=sys.stderr)

    # Score every labelled candidate (full probe extraction)
    X: list[np.ndarray] = []
    y: list[int] = []
    print("Computing probe features for labelled candidates…", file=sys.stderr)
    target_ids = set(label_by_id.keys())
    seen = 0
    for cand in iter_candidates(args.candidates):
        if cand.candidate_id not in target_ids:
            continue
        cs = score_candidate(cand)
        if cs.is_honeypot:
            # Honeypots have score=-1 and don't go into the training set
            continue
        X.append(build_feature_row(cs))
        y.append(label_by_id[cand.candidate_id])
        seen += 1
        if seen >= len(target_ids):
            break

    X_arr = np.asarray(X)
    y_arr = np.asarray(y, dtype=np.int32)
    print(f"Training set: {X_arr.shape[0]} candidates × {X_arr.shape[1]} features",
          file=sys.stderr)

    # ----- Try LightGBM-Ranker -----
    feature_importance: np.ndarray
    try:
        import lightgbm as lgb
        # Single group — all candidates are "for this one JD"
        group = [X_arr.shape[0]]
        model = lgb.LGBMRanker(
            objective="lambdarank",
            metric="ndcg",
            ndcg_eval_at=[10, 50],
            n_estimators=200,
            learning_rate=0.05,
            num_leaves=15,
            min_data_in_leaf=5,
            verbose=-1,
        )
        model.fit(X_arr, y_arr, group=group)
        feature_importance = np.asarray(model.feature_importances_, dtype=np.float64)
        method = "lightgbm-rank"
        print(f"LightGBM-Ranker fit complete.", file=sys.stderr)
    except ImportError:
        # Fall back: per-feature Spearman-style correlation with tier label
        print("LightGBM not installed — falling back to correlation-based weights.",
              file=sys.stderr)
        feature_importance = np.zeros(N_FEATS, dtype=np.float64)
        for i in range(N_FEATS):
            if X_arr[:, i].std() < 1e-9:
                feature_importance[i] = 0.0
                continue
            # Pearson correlation between feature column and tier
            c = float(np.corrcoef(X_arr[:, i], y_arr)[0, 1])
            feature_importance[i] = max(0.0, c)  # only positive correlations
        method = "pearson-correlation-fallback"

    # ----- Normalise to relative weights inside each category -----
    learned: dict[str, dict[str, float]] = defaultdict(dict)
    for i, (cat, name) in enumerate(FEATURE_ORDER):
        learned[cat][name] = float(feature_importance[i])

    # Normalise each category so weights sum to a reasonable total.
    # Must-have: ~1.0. Substance: ~1.0. Anti-SNR: keep as relative penalties.
    for cat in ["must_have", "substance", "retrieval", "location"]:
        total = sum(learned[cat].values())
        if total > 0:
            for name in learned[cat]:
                learned[cat][name] = round(learned[cat][name] / total, 4)
        else:
            # Degenerate — keep the existing weights from scoring.py
            existing = {
                "must_have": MUST_HAVE_WEIGHTS,
                "substance": SUBSTANCE_WEIGHTS,
                "retrieval": RETRIEVAL_WEIGHTS,
                "location": LOCATION_WEIGHTS,
            }[cat]
            for name, w in existing.items():
                learned[cat][name] = w
    # Anti-SNR: rescale to [0, 1] keeping relative magnitudes
    anti = learned["anti_snr"]
    if anti and max(anti.values()) > 0:
        peak = max(anti.values())
        for name in anti:
            anti[name] = round(min(0.95, anti[name] / peak), 4)
    else:
        for name, w in ANTI_SNR_WEIGHTS.items():
            anti[name] = w

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fp:
        yaml.safe_dump({
            "method": method,
            "n_training": X_arr.shape[0],
            "weights": dict(learned),
        }, fp, default_flow_style=False, sort_keys=False)

    print(f"\nWrote {out_path}", file=sys.stderr)
    print(f"\nTo use these weights, copy the 'weights' block into your JD YAML\n"
          f"and rerun python rank.py.", file=sys.stderr)


if __name__ == "__main__":
    main()
