# Sampling Report

- **Total scanned:** 100,000
- **Per-bucket target:** 50
- **Seed:** 42
- **Total selected:** 300

## Raw bucket distribution across all 100K candidates

| Bucket | Count | % of pool |
|---|---|---|
| `likely_tier5` | 154 | 0.15% |
| `likely_tier4` | 536 | 0.54% |
| `adjacent_mid` | 7,992 | 7.99% |
| `likely_keyword_stuffer` | 3,607 | 3.61% |
| `honeypot_suspect` | 40 | 0.04% |
| `random_control` | 87,671 | 87.67% |

## Diagnostic signals

| Signal | Count |
|---|---|
| `consulting_only` | 9,745 |
| `ml_title_anywhere` | 1,154 |
| `ml_title_current` | 1,047 |
| `paradox:duration>experience` | 23 |
| `paradox:expert_zero_months` | 21 |
| `paradox:single_role>experience` | 20 |
| `product_co_in_history` | 12,355 |
| `structural_paradox_any` | 44 |

## Bucket assignment heuristics

Priority order (first match wins, mutually exclusive):

1. **`likely_tier5`** — current title contains ML/AI/IR signal AND has a known product company in history AND ≥2 retrieval-substance mentions in `career_history.description`. Tier-5 wins over honeypot — if a real ML engineer happens to fire a paradox rule, we want to see it.
2. **`honeypot_suspect`** — any structural paradox fires (salary, date inversion, duration > YoE+2, single role > YoE+12mo, ≥3 expert skills with 0 months) AND not already tier-5.
3. **`likely_tier4`** — any past title is ML/AI/IR AND (product co anywhere OR ≥3 retrieval-substance mentions).
4. **`likely_keyword_stuffer`** — ≥6 JD-keyword skills AND no ML title anywhere AND ≤1 retrieval-substance mentions. The trap signature: keywords on the surface, no execution underneath.
5. **`adjacent_mid`** — any ML title OR ≥1 retrieval mention OR ≥2 JD keywords. Mid-strength signal.
6. **`random_control`** — fallthrough. No signal in any direction. Boring negatives — anchors the bottom of the relevance scale.

These are heuristics for *stratification*, not labels. Hand-label is the truth signal.

## How to use this sample

1. Open `candidates_to_label.md` in a Markdown previewer (VS Code Ctrl+Shift+V).
2. Open `labels.csv` in your spreadsheet/editor.
3. For each card (~30s each): fill `tier` (0–5), `is_honeypot` (TRUE/FALSE), `trap_class`, and `primary_strength` (for tier≥3).
4. Touchstone for tier: *would you forward this candidate to the hiring manager?*
5. Calibration check after labelling: tier 5 should stay rare (~10–20 out of 300). If you find yourself labelling 50+ as tier 5, recalibrate against JD stinginess.
6. When done, run `python -m eval.merge_labels` to merge labels back into the candidate JSONL for the metric pipeline.
