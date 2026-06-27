# Next steps — what to do from here

End-to-end build is complete. To win the hackathon, here's what you actually need to do, in priority order.

---

## 1. Label the eval set (~3–6 hours of focused work)

This is the **single highest-leverage thing left**. Without it, every weight change is unverifiable.

```bash
# In VS Code or your editor:
#   - Open eval/candidates_to_label.md (Ctrl+Shift+V for preview)
#   - Open eval/labels.csv side-by-side
#
# For each of the ~290 cards (~30s each):
#   - Read the card
#   - Fill in: tier (0-5), is_honeypot (TRUE/FALSE), trap_class, primary_strength

# Touchstone for tier:
#   "If I had this candidate and only this JD, would I forward them to the
#    hiring manager?" → tier 4+
#   "Worth a call but not necessarily forward?" → tier 3

# When done:
python -m eval.merge_labels
```

Calibration: tier-5 should stay rare. If you find yourself marking >30 candidates tier-5, recalibrate against JD stinginess.

---

## 2. Score the current submission against your labels

```bash
python -m eval.score \
  --labels eval/labelled.jsonl \
  --submission submissions/team_baseline.csv
```

This prints NDCG@10/50, MAP, P@10, composite, and honeypot rate. Memorise the baseline numbers — every weight change after this gets measured against them.

---

## 3. Tune weights

Edit `src/scoring.py`:
- `MUST_HAVE_WEIGHTS`
- `SUBSTANCE_WEIGHTS`
- `ANTI_SNR_WEIGHTS`
- `RETRIEVAL_WEIGHTS` (active once Phase 3 finishes)
- `CATEGORY_WEIGHTS`

Re-run rank.py → re-score → measure NDCG@10. Only keep changes that improve the metric.

**Known issue to address first:** location penalty is too light. Spot-check showed a remote-only candidate outside India at rank 7. Increasing `LOCATION_WEIGHTS["location_match"]` or `ANTI_SNR_WEIGHTS["remote_only_vs_hybrid_jd"]` should fix this. Verify with the eval set.

---

## 4. Re-run with hybrid retrieval (after Phase 3 precompute finishes)

```bash
# One-time, outside the 5-min budget:
python -m src.precompute \
  --candidates "<path>/candidates.jsonl" \
  --out-dir ./data

# Then re-run the ranker:
python rank.py \
  --candidates "<path>/candidates.jsonl" \
  --out submissions/team_hybrid.csv

# Diff against baseline:
python -m eval.compare \
  --a submissions/team_baseline.csv \
  --b submissions/team_hybrid.csv

# Score the new one:
python -m eval.score \
  --labels eval/labelled.jsonl \
  --submission submissions/team_hybrid.csv
```

If hybrid beats baseline on NDCG@10 → use hybrid. If not → drop the retrieval probe (set `CATEGORY_WEIGHTS["retrieval"] = 0`) and stay with the probe-only system.

---

## 5. Deploy the sandbox

```bash
# Local dev (two terminals):
cd sandbox/backend && pip install -r requirements.txt
cd ../..
uvicorn sandbox.backend.main:app --reload --port 8000

cd sandbox/frontend && npm install && npm run dev
# open http://localhost:5173
```

Production deploy to HuggingFace Spaces:
1. Create a new HF Space (type = Docker).
2. Push this repository to that Space's git remote.
3. HF auto-builds the Dockerfile in `sandbox/Dockerfile`.

Add the resulting URL to `submission_metadata.yaml` under `sandbox_link`.

---

## 6. Fill submission metadata

Edit `submission_metadata.yaml`:
- `team_name`
- `primary_contact` (name, email, phone)
- `team_members`
- `github_repo` (the actual public URL once you push)
- `sandbox_link` (from step 5)
- `compute.platform`, `compute.os`, `compute.python_version`

---

## 7. Submit

**Submission #1 (now / today):** the baseline CSV at `submissions/team_baseline.csv` passes the official validator and produces 222 honeypots quarantined and a top-10 of mostly Indian product-co AI engineers. Submit this as your first slot if you want to lock in a valid floor while you tune.

Rename the file: `cp submissions/team_baseline.csv submissions/<team_id>.csv` (your registered participant ID).

**Submission #2 (after tuning):** the polished system. Submit this when:
- The labelled-set NDCG@10 is meaningfully higher than baseline
- Top 100 has been manually reviewed (no obvious mistakes)
- Honeypot rate is ≤2% (confirmed via `python -m eval.score`)

**Submission #3 (hedge):** only if it improves eval-set NDCG@10 on a held-out slice. The spec counts your last valid submission — never break what works.

---

## What's in the box

```
redrob-ranker/
├── rank.py                       — single-command entry point
├── README.md                     — one-page system overview
├── final_plan.md                 — the design blueprint (1,125 lines)
├── NEXT_STEPS.md                 — this file
├── requirements.txt
├── submission_metadata.yaml      — fill in before submitting
├── src/
│   ├── schema.py                 ✓ Pydantic models (lenient input, strict output)
│   ├── load.py                   ✓ streaming JSONL loader
│   ├── heuristics.py             ✓ cheap helpers — regexes, company dicts
│   ├── honeypot.py               ✓ 6 deterministic rules
│   ├── scoring.py                ✓ composition (must_have + substance + retrieval + location)
│   ├── pairwise.py               ✓ top-20 refinement
│   ├── reasoning.py              ✓ 6 templates × 3 bands, deterministic seeding
│   ├── precompute.py             ✓ embeddings + BM25 (run once, outside 5-min budget)
│   └── probes/
│       ├── must_have.py          ✓ 5 probes
│       ├── substance.py          ✓ 9 probes
│       ├── behavioural.py        ✓ 4 probes (multiplicative)
│       ├── anti_snr.py           ✓ 11 probes (negative)
│       ├── location.py           ✓ 3 probes
│       └── retrieval.py          ✓ BM25 + dense cosine
├── eval/
│   ├── sample.py                 ✓ 290 stratified candidates emitted
│   ├── candidates_to_label.md    ✓ ready for hand-labelling
│   ├── labels.csv                ✓ template, fill in tier/honeypot/trap/strength
│   ├── merge_labels.py           — run after filling labels.csv
│   ├── score.py                  — run after merge_labels to see metrics
│   ├── metrics.py                — NDCG@k, MAP, P@k, composite
│   └── compare.py                — diff two submission CSVs
├── sandbox/                      ✓ React + FastAPI + Docker
├── tests/                        ✓ 29 tests, all passing
└── submissions/
    └── team_baseline.csv         ✓ valid, ready to submit
```

`✓` = built and tested. `—` = ready to use, waits on your input.

---

## Stage-5 narrative cheat sheet

When you're in the 30-minute defend-your-work call, lead with this:

> *We rejected the conventional embedding-cosine-rerank architecture because the dataset was explicitly designed to defeat it. We treated the JD as the algorithm — every requirement maps to a probe over the candidate schema. Probes are tagged High-SNR, Medium-SNR, Low-SNR, or Anti-SNR, and weighted by class. Tested or unfakeable signals dominate; self-asserted claims are downweighted.*
>
> *Honeypots are gated out by six deterministic structural-impossibility rules. Behavioural availability is multiplicative — a perfect-paper candidate who hasn't logged in for six months gets multiplied down toward zero.*
>
> *Reasoning is composed directly from the top contributing probes per candidate — no LLM at runtime — so it can't hallucinate by construction.*
>
> *Pairwise refinement on the top 20 because NDCG@10 is fundamentally a pairwise problem on the top 10.*
>
> *Every probe weight is independently SGD-updatable. In production, every recruiter override is one gradient step. No retraining.*

That's the 90-second answer. Each sentence maps to a specific design choice in the code, which you can walk through.
