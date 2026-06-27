# redrob-ranker

> *We treat the JD as the algorithm. Each requirement becomes a probe over the candidate schema. Every probe is tagged High-SNR, Medium-SNR, Low-SNR, or Anti-SNR, and we weight by class.*

A candidate ranker for the Redrob *Intelligent Candidate Discovery & Ranking* hackathon. Ranks the top 100 of 100,000 candidates against a single Senior AI Engineer job description, with structured reasoning for every rank.

## Reproduce

```bash
pip install -r requirements.txt

# Produce the submission CSV (run on the official candidates.jsonl)
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
```

Runtime: **~230 seconds** on CPU, ~2 GB peak RAM. Well inside the 5-min / 16 GB / no-network / no-GPU budget. CSV passes `validate_submission.py` from the bundle.

## What's in here

```
redrob-ranker/
├── rank.py                       # single entry point
├── src/
│   ├── schema.py                 # Pydantic models (lenient input, strict output)
│   ├── load.py                   # streaming JSONL reader
│   ├── heuristics.py             # cheap helpers (regexes, company dicts)
│   ├── honeypot.py               # six deterministic structural-impossibility rules
│   ├── scoring.py                # composition of all probes into a single score
│   ├── pairwise.py               # top-20 refinement on JD-priority tiebreakers
│   ├── reasoning.py              # 6 templates × 3 rank bands, deterministic seeding
│   └── probes/
│       ├── must_have.py          # JD's "absolutely need" probes
│       ├── substance.py          # anti-stuffer / High-SNR signals
│       ├── behavioural.py        # Redrob signals availability + trust
│       ├── anti_snr.py           # JD-explicit disqualifiers / red flags
│       └── location.py           # logistics, YoE band, certifications
├── eval/                         # stratified sampler + labelling artefacts + metrics
├── sandbox/                      # FastAPI + React/Vite/Tailwind/Framer Motion demo
├── final_plan.md                 # complete project blueprint, read this for design rationale
└── submissions/                  # generated CSVs
```

## The SNR architecture (in one paragraph)

The dataset has three explicit traps: keyword-stuffers, plain-language tier-5s, and behavioural twins. A naive embedding-cosine pipeline falls for all three. We don't.

Every signal in a candidate's record is tagged by how hard it is to fake. **High-SNR** signals (named technical systems in description text, verified skill assessment scores, GitHub activity, narrative cause-effect chains, production verbs in recent roles) carry 2–3× the weight of **Low-SNR** signals (bare skill claims with zero endorsements, generic action verbs, raw YoE alone). **Anti-SNR** flags (consulting-only careers, bigcorp-only careers, framework-enthusiast pattern, manager-drift) apply as a multiplicative penalty. **Honeypots** are gated out by six deterministic structural-impossibility rules and never enter the top-100 by construction.

Behavioural signals (open-to-work, response rate, last-active decay, notice period) are a multiplicative modifier on the overall score, a perfect-paper candidate who hasn't logged in for six months gets multiplied down toward zero.

Top 20 are refined via pairwise comparison against JD-priority tiebreakers (production evidence > years; description specificity > keyword count; verified > claimed) because NDCG@10, 50% of the composite score, is fundamentally a pairwise problem.

## Reasoning, by construction

Reasoning is composed by templating from the top contributing probes per candidate. **No LLM at runtime.** Six templates per rank band × variable probe combinations × deterministic seeding from `candidate_id` produce >600 effective phrasings without ever fabricating a fact. Stage-4 checks are passed by construction, every claim cites a parsed schema attribute, concerns are explicitly named on top-rank candidates, the tone matches the rank because the band IS a function of rank.

Top 1–10 sample:

> *"Strong fit: Lead AI Engineer (6.7y) at Razorpay. 5 embedding/retrieval mention(s) in descriptions; 1 embedding tool(s) in skills, plus 2 vector-DB mention(s) in descriptions; 2 vector tool(s) in skills."*

## Sandbox

A working sandbox lives in `sandbox/`. React + Vite + Tailwind frontend, FastAPI backend, single Docker container, HuggingFace-Space compatible. It implements the six-act journey described in `final_plan.md §15`, the JD digest landing, the deck (one candidate at a time, keyboard-first), whispered hints on plain-language tier-5s, the pause, the shortlist review, and the closing reflection.

See `sandbox/README.md` for development and deployment instructions.

## Lineage

Sandbox UI base components (React + Vite + Tailwind config patterns) were lifted from the team's prior project, [KnowTruly.me](https://github.com/<owner>/matrix-main), a public repository. The ranking algorithm, probe library, scoring composition, pairwise refinement, reasoning generator, eval set, honeypot detector, is built fresh for this submission. UI pages, animations, micro-copy, and the journey choreography are custom for this submission.

## Eval set

300 candidates stratified across six buckets (likely tier-5, likely tier-4, adjacent mid, likely keyword-stuffer, honeypot suspect, random control) labelled by hand. `eval/sample.py` runs the stratification; `eval/candidates_to_label.md` is the human-friendly labelling experience; `eval/merge_labels.py` merges filled labels back; `eval/metrics.py` computes NDCG@10/50/MAP/P@10 + honeypot rate. The labelled set is the only iteration signal in a no-leaderboard hackathon.

## Known limitations

- **Dense embeddings deferred.** Hybrid retrieval (BM25 + sentence-transformer cosine) is in the plan but not in the current build. The structured-feature scorer is competitive on its own; embeddings will be added in submission #3 if eval-set NDCG@10 improves.
- **Eval set ≠ ground truth.** Our 300 hand labels approximate the hidden ground truth; risk of overfitting to our biases.
- **Single JD only.** Probe weights are tuned to this JD; generalising means re-deriving probes.
- **Company-age dictionary is small.** The tenure-exceeds-company-age honeypot rule only fires on ~30 well-known companies; broader coverage requires more data.

## License

MIT for the code. Public dataset belongs to Redrob.
