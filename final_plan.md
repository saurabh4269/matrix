# Redrob Hackathon, Final Plan

**Track:** 01, Intelligent Candidate Discovery & Ranking
**Task:** Rank top 100 of 100,000 candidates against one specific JD (Senior AI Engineer @ Redrob, Pune/Noida).
**Repo:** [`saurabh4269/matrix`](https://github.com/saurabh4269/matrix) (public).
**Codename:** project name is just **matrix**, no marketing branding (no "AURA", no "Kinetic", no "Forensic"). Marketing language is a Stage-5 risk, not an asset.

---

## TL;DR

We treat the JD as the algorithm. Each requirement in the JD becomes a probe over the candidate schema. Every probe is tagged High-SNR / Medium-SNR / Low-SNR / Anti-SNR, and weighted by class. Honeypots are gated out by six deterministic structural-impossibility rules. Behavioural availability is a multiplicative modifier. Pairwise refinement on the top 20 because NDCG@10 (50% of the composite score) is fundamentally a pairwise problem. Reasoning is templated from the top contributing probes, no LLM at runtime, so it cannot hallucinate by construction. We submit 3 times: baseline → main → polish. Hand-labelled 300-candidate eval set is the only feedback signal (no live leaderboard); every weight decision is measured against NDCG@10 on it.

---

## Table of Contents

1. [The problem, stripped down](#1-the-problem-stripped-down)
2. [Hard constraints we must live inside](#2-hard-constraints-we-must-live-inside)
3. [The SNR architectural principle](#3-the-snr-architectural-principle)
4. [The full probe library](#4-the-full-probe-library)
5. [Honeypot detection (six rules)](#5-honeypot-detection-six-rules)
6. [Hard filters vs. soft penalties](#6-hard-filters-vs-soft-penalties)
7. [Scoring composition](#7-scoring-composition)
8. [Pairwise refinement on top 20](#8-pairwise-refinement-on-top-20)
9. [Reasoning generation](#9-reasoning-generation)
10. [Eval-set strategy and labelling schema](#10-eval-set-strategy-and-labelling-schema)
11. [Submission cadence (the 3-submission plan)](#11-submission-cadence-the-3-submission-plan)
12. [HR / recruiter pain points addressed](#12-hr-recruiter-pain-points-addressed)
13. [Judges' / Redrob's perspective addressed](#13-judges-redrobs-perspective-addressed)
14. [matrix-main reuse policy](#14-matrix-main-reuse-policy)
15. [Design System & UI/UX](#15-design-system--uiux)
16. [vision.md coverage map](#16-visionmd-coverage-map)
17. [Stage-by-stage defense (Stages 1–5)](#17-stage-by-stage-defense-stages-1-5)
18. [Folder structure and deliverables](#18-folder-structure-and-deliverables)
19. [Build order and milestones](#19-build-order-and-milestones)
20. [Known limitations](#20-known-limitations)
21. [Stage-5 interview narrative (90-second version)](#21-stage-5-interview-narrative-90-second-version)

---

## 1. The problem, stripped down

100K candidates → rank top 100 against one JD. Composite score = `0.50·NDCG@10 + 0.30·NDCG@50 + 0.15·MAP + 0.05·P@10`.

**What the scoring function tells us:**
- Half the score lives in the top 10. This is a **precision-at-the-top** problem, not a coverage problem.
- Below rank 50, marginal improvements barely move the metric.
- The right strategy is *find the gems with conviction, fill the long tail with safe picks*.

**What the dataset tells us (from the JD footnote + signals doc + sample_submission):**
- True tier-5 candidates are **sparse** (the JD: "we'd rather see 10 great matches than 1000 maybes"). Probably 10–30 in 100K.
- Three trap categories are explicit: **keyword-stuffers**, **plain-language tier-5s**, **behavioural twins**.
- ~80 honeypots designed to look skill-rich; >10% in top-100 → Stage-3 DQ.
- `sample_submission.csv` IS the trap demonstrated, it ranks HR Managers and Civil Engineers with 8 "AI core skills" at the top.

**Why this isn't a ranking problem; it's a search-then-rank problem:**
With ~20 needles in 100K hay, the system must **recall** the needles into a working set before precision-ranking. Hard pre-filters that drop ~85K are reckless, a single fuzzy filter that drops a tier-5 is unrecoverable. **Use scores, not gates, for everything except honeypots and JD-explicit hard nos.**

---

## 2. Hard constraints we must live inside

| Constraint | Limit |
|---|---|
| Ranking runtime | ≤ 5 min wall-clock |
| Memory | ≤ 16 GB RAM |
| Compute | CPU only, **no GPU** during ranking |
| Network | **No external API calls** during ranking |
| Disk | ≤ 5 GB intermediate |
| Submissions | 3 max; last valid counts |
| Honeypot rate in top-100 | ≤ 10% (>10% → Stage-3 DQ) |
| Output format | CSV: `candidate_id,rank,score,reasoning`, exactly 100 rows, ranks 1–100 unique, scores non-increasing, ties broken by `candidate_id` ascending |
| Pre-computation | Allowed *outside* the 5-min window (embeddings, indexes) |
| Reasoning column | Optional but heavily Stage-4 reviewed |

**What this kills from vision.md:**
- Per-candidate hosted-LLM calls (Multi-Agent Forensic Reranker at runtime) → cut.
- Live HITL feedback during ranking → cut from runtime, kept as architectural property.
- Dual-mode N<500 vs N>500 pipeline → cut (N is fixed at 100K).

**What we still gain:**
- Pre-computation lets us embed all 100K candidates once, write to disk, and load at runtime.
- Offline LLM use (outside the 5-min runtime) for *auditing* generated reasoning is allowed.

---

## 3. The SNR architectural principle

**Every signal in the candidate schema is tagged by how hard it is to fake.** Weights reflect this. The README leads with this principle; Stage 5 narrative leads with it.

| SNR class | Definition | Weight tier | Examples |
|---|---|---|---|
| **High SNR** | Tested, verified, or requires a real artifact to produce | Heavy (2–3× Low) | `skill_assessment_scores`, named technical entities in descriptions, `github_activity_score`, production verbs in descriptions, `verified_email × verified_phone × linkedin_connected`, narrative cause-effect chains in descriptions, JD-relevant title trajectory, years of ML at product companies |
| **Medium SNR** | Cross-checkable but soft | Medium | Skill claims with endorsements + duration, summary thoughtfulness, company stage alignment, acceleration (shrinking promotion intervals), `interview_completion_rate`, `saved_by_recruiters_30d`, certifications |
| **Low SNR** | Self-asserted with no corroboration | Light | Bare skill names with 0 endorsements, generic action verbs, raw YoE alone, education tier alone, location alone |
| **Anti-SNR** | JD-specific red flags / negative signals | Heavy negative | Consulting-only career, FAANG-only / bigcorp-only career, manager-drift (lost hands-on), keyword-dense-with-low-YoE, generic verbs without specificity, dilution (generic years ≫ relevant years), title-chaser, framework-enthusiast, remote-only-vs-hybrid-JD |

**Key calibration decisions:**
- **Education tier weight = 0** (not positive, not negative). Conscious neutrality on pedigree. Defensible answer: "we don't reward or punish college; we look at what they've built."
- **High-SNR probes carry 2–3× the weight of Low-SNR.** This ratio is what makes the SNR framing real, not just labelling.

---

## 4. The full probe library

### A. Must-have probes (heavy weight, derived from JD's "absolutely need" section)

| Probe | SNR | What it measures |
|---|---|---|
| `production_embeddings_retrieval` | High | Mentions of `embedding/embed/sentence-transformer/BGE/E5/openai/bi-encoder/dense retrieval` in `career_history.description` + corroborating verbs |
| `production_vector_db` | High | Mentions of `Pinecone/Weaviate/Qdrant/Milvus/OpenSearch/Elasticsearch/FAISS/HNSW/vector index` |
| `ranking_eval_framework` | High | Mentions of `NDCG/MRR/MAP/P@k/A/B test/offline-online/recall@k/hit rate`, direct Stage-4 hook ("the JD literally says NDCG") |
| `python_proficiency` | High | Skill claim + tenure + assessment score on Python |
| `years_applied_ml_at_product_co` | High | Sum of `duration_months` across roles where (title contains ML/AI/IR/NLP signal) AND (company is a product company). **Single strongest predictor.** |

### B. Nice-to-have probes (medium weight)

| Probe | SNR |
|---|---|
| `llm_finetuning_experience` (LoRA/QLoRA/PEFT in description) | Medium |
| `learning_to_rank` (XGBoost-rank / LightGBM-rank / neural LTR) | Medium |
| `hr_tech_marketplace_context` | Medium |
| `distributed_systems_inference_opt` | Medium |
| `open_source_external_validation` (papers/talks/repos listed) | High |

### C. Substance / anti-stuffer probes (the trap defense)

| Probe | SNR | What |
|---|---|---|
| `description_specificity` | High | Count of capitalized proper-noun technical terms in descriptions per 100 tokens. Vocabulary: ~150 specific terms in ML/IR/data infra |
| `narrative_arc_density` | High | Regex hits for cause-effect connectives (`because, root cause, led to, reduced from X to Y, after discovering, improved by`) per role |
| `production_emphasis` | High | Count of `production/prod/shipped/deployed/users/scale/latency/SLA/on-call` in recent role descriptions |
| `verification_ratio` | High | `len(skill_assessment_scores) / len(skills)`, high ratio = candidate has actually tested their claims |
| `acceleration` | Medium | Promotion intervals shrinking over career (second derivative of velocity) |
| `summary_thoughtfulness` | Medium | Summary length × type-token ratio × first-person voice presence. Terse generic 1-liners score low |
| `company_stage_alignment` | Medium | Boost if recent companies are 11–500 size (Redrob's band); soft penalty if entire career at 10001+ |
| `shipper_vs_researcher_ratio` | Medium | `(shipped/deployed/A-B-tested/measured/optimized) ÷ (researched/explored/prototyped/investigated)` in descriptions. JD: "tilt slightly toward shipper" |
| `named_employer_micro_boost` | Medium | +0.05 per recognized ML/IR employer (Google Search, Meta Ads, Stripe ML, Databricks, Pinterest, Spotify, etc.), capped at +0.15 |

### D. Anti-SNR probes (hard-no / heavy negative, encoding JD's explicit disqualifiers)

| Probe | What |
|---|---|
| `consulting_only_career` | Every entry in `career_history` belongs to {TCS, Infosys, Wipro, Accenture, Cognizant, Capgemini, HCL, LTI, Mindtree, Tech Mahindra} |
| `bigcorp_only_career` | Every entry at 10001+ size company (JD: "if you've spent your career at Google/Meta..." soft penalty) |
| `pure_research_career` | Every entry at academic lab / research-only org with zero deployment verbs |
| `no_production_code_18mo` | Most recent role with deployment/shipping/production verbs > 18 months ago |
| `framework_enthusiast` | LLM/LangChain/RAG appear as skills with `duration_months ≤ 12` AND no production system mentioned |
| `title_chaser` | Avg tenure of last 3 roles < 18 months |
| `cv_speech_robotics_only` | Career titles dominated by Computer Vision / Speech / Robotics with zero NLP/IR |
| `manager_drift` | Recent roles dominated by `led/managed/owned/directed` without `wrote/built/shipped/deployed/implemented` |
| `dilution_penalty` | `(generic_engineering_years − ml_relevant_years) / total_years`, the aerospace-dilemma trap |
| `keyword_dense_junior` | `(JD_keyword_density > 0.7) AND (years_of_experience < 4)`, fresher with right keywords trap |
| `remote_only_vs_hybrid_jd` | `preferred_work_mode == "remote"` AND `willing_to_relocate == false` |

### E. Behavioural availability (multiplicative modifier)

| Probe | SNR | Formula |
|---|---|---|
| `effectively_available` | High | `open_to_work × min(1, response_rate/0.3) × decay(last_active_date, half_life=60d)` |
| `notice_period_curve` | High | Piecewise: 1.0 at ≤30d, linear ramp 30→90 to 0.5, 90+ → 0.3 floor |
| `trust_modifier` | High | `verified_email × verified_phone × linkedin_connected` → 1.0–1.15 range |
| `engagement_quality` | Medium | `interview_completion_rate × saved_by_recruiters_30d_normalized × min(1, github_activity_score/50)` |

### F. Hybrid retrieval features

| Feature | SNR | What |
|---|---|---|
| `bm25_jd_vs_profile_text` | Medium | Compute on-the-fly, cheap |
| `dense_cosine_jd_vs_profile` | Medium | Precomputed `all-MiniLM-L6-v2` (384-dim, ~80MB model, ~150MB total embeddings) |

### G. Location + logistics

| Probe | SNR |
|---|---|
| `location_match` | Low | Boost if Pune/Noida/Delhi NCR/Mumbai/Bangalore/Hyderabad/Chennai OR `willing_to_relocate=true` |
| `yoe_band_fit` | Low | Gaussian centered on 7 years, σ=2 |
| `certifications_micro_boost` | Medium | +0.02 per cloud cert (AWS/GCP/Azure) or recognized ML course (Stanford CS229, fast.ai, deeplearning.ai), capped at +0.06 |

### H. Three latent JD-axes (composite aggregates for structured output)

Vision.md's "Latent JD Archetype" idea, emitted in `submission_structured.jsonl` as three composite scores per candidate:

| Axis | Composed from |
|---|---|
| `tech_stack_core` | `production_embeddings_retrieval + production_vector_db + python_proficiency + ranking_eval_framework` |
| `execution_environment` | `company_stage_alignment + shipper_vs_researcher_ratio + manager_drift (inverse) + production_emphasis` |
| `friction_point` | `years_applied_ml_at_product_co + narrative_arc_density + open_source_external_validation`, "has this person actually rebuilt a legacy retrieval system?" |

---

## 5. Honeypot detection (six rules)

Conservative, only fires on truly impossible profiles. Borderline cases get heavy soft penalties but stay in the pool (protects against false-positive drops).

1. **Salary paradox**: `expected_salary_range_inr_lpa.min > expected_salary_range_inr_lpa.max`.
2. **Chronological paradox**: any `start_date > end_date` in career history.
3. **Duration > experience paradox**: `sum(career_history.duration_months) / 12 > years_of_experience + 2`.
4. **Single role > experience**: any single `duration_months > years_of_experience × 12 + 12`.
5. **Expert incongruence**: ≥3 skills with `proficiency == "expert"` AND `duration_months == 0`.
6. **Tenure exceeds company age** (NEW): for ~200 famous companies in a static dictionary, tenure > company_age_in_months → quarantine. Catches the textbook honeypot.

**Effect:** Honeypots receive internal score `-∞`, are never selected for the top 100, and never receive a rank in the output. CSV monotonicity preserved.

**Backup defense:** Even if a honeypot slips past the 6 rules, our substance-density and JD-disqualifier probes will keep it out of the top 100 in 95%+ of cases.

---

## 6. Hard filters vs. soft penalties

| Behaviour | Hard filter (drops candidate) | Soft penalty (down-scores) |
|---|---|---|
| Honeypot rule fires | ✅ | |
| Consulting-only entire career | | ✅ heavy |
| Bigcorp-only entire career | | ✅ moderate |
| Pure-research-only entire career | | ✅ heavy |
| No production code in 18mo (proxied) | | ✅ moderate |
| Notice period > 90 days | | ✅ light |
| Location mismatch + no relocate | | ✅ light |
| Title-chaser | | ✅ moderate |
| Framework enthusiast | | ✅ moderate |
| CV/speech/robotics only | | ✅ heavy |

**Rule:** the only true filters are honeypots. Everything else is a score. This protects recall.

---

## 7. Scoring composition

```
must_have_score    = weighted_sum(probes A)            # JD's "absolutely need"
nice_to_have_score = weighted_sum(probes B)            # JD's "would like"
substance_score    = weighted_sum(probes C)            # anti-stuffer + trust
retrieval_score    = α·bm25 + (1−α)·dense_cosine       # hybrid recall channel
anti_snr_penalty   = ∏(1 − probe)  for probes D        # JD's "do not want"
behavioural_modifier = product of probes E             # multiplicative availability
location_logistics = weighted_sum(probes G)            # light additive

raw = (
    1.0 · must_have_score
  + 0.3 · nice_to_have_score
  + 0.6 · substance_score
  + 0.2 · retrieval_score
  + 0.1 · location_logistics
) × anti_snr_penalty × behavioural_modifier × honeypot_gate
```

**Tuning approach:**
1. Start with these weights, derived from JD priority.
2. Score the eval set; compute NDCG@10/50/MAP/P@10.
3. Hand-adjust weights; re-score; track which adjustments help.
4. Optional: train **LightGBM-Ranker** to learn the weights (pairwise loss, `eval_metric='ndcg', eval_at=[10,50]`) on a 240-candidate train slice; hold out 60 for validation.
5. If LGBM-tuned weights beat hand-tuned on the held-out 60 → use LGBM weights for submission 3.

**Why this composition works:**
- `must_have_score` dominates the headroom, JD's must-haves are non-negotiable.
- `substance_score` weight (0.6) is intentionally high, this is the trap-defense layer.
- `retrieval_score` weight (0.2) is intentionally modest, embeddings are a recall channel, not a precision channel. Structured features do the precision work.

---

## 8. Pairwise refinement on top 20

After the linear scorer produces a candidate top 200, the top 20 go through a **pairwise comparison pass**:

For each adjacent pair `(i, i+1)` in the top 20:
1. Compute pairwise feature deltas (which feature differs most, in which direction).
2. Apply hand-coded tiebreakers matching JD priorities:
   - Production evidence beats years.
   - Description specificity beats skill keyword count.
   - High verification ratio beats low.
   - Active candidate beats dormant if other factors are close.
3. Optionally swap their order.

**Why:** NDCG@10 is fundamentally a pairwise problem on the top 10. Absolute scoring is sloppy at the top because tiny absolute-score differences create big rank differences. Pairwise refinement directly targets where the score lives.

**Defense in Stage 5:** "NDCG@10 cares about ordering the top 10 correctly, which is a pairwise problem. Linear scoring is fine for getting candidates into the top 200; pairwise comparison is what gets the top 20 in the right order."

---

## 9. Reasoning generation

**Architecture:** the scoring pass produces, for every candidate, a list of `(probe_name, score_contribution, evidence_string)` tuples. The reasoning column is composed by selecting the top contributors and templating.

**No LLM at runtime.** Pure deterministic templating.

### Templates by rank band

**Rank 1–10 templates** (6 variants, randomized by `hash(candidate_id) mod 6`):
- Lead with strongest *High-SNR* probe.
- Always name one concrete concern (this passes Stage-4's "honest concerns" check; rank #1 with a noted concern reads more rigorous than rank #1 with glowing prose).
- Specific facts: title, company, YoE, named system from description, named skill assessment score.

Example: *"Sr ML Engineer (7y) at Stripe Search; verified Python 87/100 + production retrieval system using BGE & FAISS at scale, NDCG/MRR evaluation framework owned. Concern: 60-day notice."*

**Rank 11–50 templates:**
- Two corroborating signals (one High-SNR + one Medium-SNR).
- Name a concern.

**Rank 51–100 templates:**
- Explicit **why-not** framing: "Strong X but ranked lower because Y missing."
- This is the most useful Stage-4 signal, naming what's missing demonstrates the system *read* the candidate.

Example: *"Strong NLP foundation and active on platform, but no evidence of production retrieval system ownership in description text and 120-day notice, strong candidate, wrong role for the team's current phase."*

### Stage-4 compliance, by construction

| Stage 4 check | How we pass |
|---|---|
| Specific facts | Probe evidence strings always cite actual schema fields |
| JD connection | Probe names map 1:1 to JD requirements |
| Honest concerns | Top-rank templates require a `primary_concern` field |
| No hallucination | No LLM generation; every claim is a parsed schema attribute |
| Variation | 6 templates per band × variable probe combos × randomized choice |
| Rank consistency | Template band is a function of rank itself |

### Offline LLM audit (optional, pre-submission)

Before final submission: feed each generated reasoning + the candidate profile to an offline LLM (network allowed outside the ranking step) with the prompt *"flag any claim in the reasoning that isn't supported by the profile."* Manual review of flagged entries. Zero hallucination guarantee.

---

## 10. Eval-set strategy and labelling schema

**Why this matters:** No live leaderboard. 3 submissions. Every weight decision is unverifiable without our own eval signal. The eval set is *the most important deliverable of week 1*.

### Size and stratification

**300 candidates, stratified across 5 buckets (60 each):**

1. `likely_tier5`, ML/AI/IR title + product co + retrieval/ranking mentions in descriptions.
2. `likely_tier4`, Adjacent strong: data scientist, search engineer at product co.
3. `adjacent_mid`, Data engineer, backend with ML exposure, NLP-adjacent.
4. `likely_keyword_stuffer`, High JD-keyword density + non-tech title.
5. `honeypot_or_random`, Structural-paradox suspects + uniform random.

Stratification matters more than raw size; each bucket needs ≥30 examples for metrics to discriminate.

### Labelling schema

```
Required:
  tier              0-5 integer
  is_honeypot       bool (independent of tier)

One-pick enum:
  trap_class        clean | keyword_stuffer | consulting_only |
                    bigcorp_only | plain_language_tier5 |
                    cv_speech_robotics_only | title_chaser | other

Required for tier ≥ 3:
  primary_strength  one-line free text (3-12 words)

Optional but recommended for tier ≥ 3:
  primary_concern   one-line free text
  notes             anything else
```

### Labelling UX (three artifacts)

1. `eval/candidates_to_label.md`, one scannable Markdown profile per candidate. Pre-extracted summary, career path, top skills, key behavioural signals, pre-fired structural flags. Scroll, read 30s, decide.
2. `eval/labels.csv`, pre-filled with `candidate_id`, blank label columns. Fill in spreadsheet form.
3. `eval/sampling_report.md`, documents heuristics used for each bucket. Auditable.

### Calibration discipline

- Tier-5 should stay rare (~10–20 in 300). If 80+ get labelled tier-5, re-calibrate against JD stinginess.
- After labelling: emit `bucket × tier` crosstab. If `likely_tier5` heuristic bucket contains 50%+ tier-4-5s, heuristics are sound. If 5%, redesign.
- One focused labelling session (not spread over days) for consistency.
- The JD is the touchstone: *"if I had this candidate and this JD, would I forward to hiring manager?"*

### Eval set serves three purposes simultaneously

1. **Metric computation**, NDCG@10/50, MAP, P@10 on labelled set.
2. **DQ-risk measurement**, honeypot rate as separate metric.
3. **Trap-class precision**, "we correctly demote 92% of keyword-stuffers" is a Stage-5 winning line.
4. **(Bonus)** Reasoning regression corpus, our generated reasonings can be compared against the `primary_strength` / `primary_concern` hand-notes.

---

## 11. Submission cadence (the 3-submission plan)

| Submission | When | Purpose | Score expectations |
|---|---|---|---|
| **#1: Baseline** | Day 4 | Validate format end-to-end. CSV passes `validate_submission.py`. Pipeline runs in <5min. Honeypot rate ≤10%. Portal accepts. | Score doesn't matter; health does. |
| **#2: Main shot** | Day 5–6 | Full system with hybrid retrieval + tuned weights against eval set. | Real submission. Expected highest score. |
| **#3: Polish** | Day 7 | Refinements based on manual review of submission 2's top-100 (~50 min). LightGBM-Rank weights swapped in if they beat hand-tuned on held-out 60. | Hedge; only swap if eval-set NDCG@10 improves. |

**Critical:** the spec says only the **last valid submission** counts. So submission 3 must always be at least as good as submission 2's quality. We don't break things at the end.

---

## 12. HR / recruiter pain points addressed

Catered to systematically. Each pain point maps to a concrete design decision.

| Pain point | Our answer |
|---|---|
| Can't defend the AI's choice to hiring manager | Structured fact-cited reasoning per candidate; auditable feature deltas |
| Don't trust hidden bias | Education-tier weight = 0; transparent SNR weighting; no demographic proxies |
| Only look at top 10–20 anyway | Pairwise refinement on top 20 targets the precision-at-top half of the score |
| Generic tools don't fit our stage | `company_stage_alignment` probe matches Redrob's actual size band |
| Need to override AI ranking | Architecture is online-updatable: each probe weight is independently SGD-updatable. No retraining needed (Stage-5 narrative) |
| Candidate is unavailable and I don't know it | Behavioural signals are *multiplicative*; perfect-paper-but-dormant candidate gets multiplied down |
| Reading between the lines (plain-language tier-5s) | Description-specificity probe rewards terse-but-real descriptions over verbose keyword-stuffers |
| Need pipeline visibility, not just a rank | `submission_structured.jsonl` with per-candidate evidence array + stub `next_step` field |
| Interview signal isn't in the resume | `interview_completion_rate`, `recruiter_response_rate`, `saved_by_recruiters_30d` weighted as High-SNR |
| Everyone uses ChatGPT to tailor, keywords mean nothing | Substance-over-syntax architecture; specificity / narrative-arc / production-emphasis as primary trust signals |
| Find me the underdog hidden gem | `verification_ratio` (assessed but didn't claim a lot) + `acceleration` (under-titled climbing fast) |
| Tell me why someone *didn't* make the list | Reasoning for rank 50–100 explicitly names what's missing |

---

## 13. Judges' / Redrob's perspective addressed

The judges are Redrob engineers, they built the dataset, wrote the JD. Stage 5 is a 30-minute video call: judging *and* recruiting. We design for both.

| Judge concern | Our answer |
|---|---|
| Did the team READ the materials? | Probes map 1:1 to JD sentences. JD footnote about traps is encoded in our design |
| Did they fall for the obvious trap? | Anti-keyword-stuffer is the central architectural feature |
| Real engineering or LLM-only output? | Real iteration in git history (8–12 commits over the week). No LLM in runtime path. Deterministic code |
| Did they think about scale and production? | <30 sec runtime well under 5-min budget. Structured JSONL output. Modular probe library |
| Original framing or recycled buzzwords? | SNR architecture is original. No "Kinetic", no "Forensic". |
| Did they understand the dataset, or just throw ML at it? | We bring a *specific observation* about the dataset to the interview (TBD; to be discovered during EDA) |
| Would I want to work with this person? | Stage 5 narrative shows reasoning chains: "we picked X because Y, considered Z, rejected for W" |
| Did they cheat / paste LLM output? | Reasoning is templated with deterministic seeding. Human-engineered look because it is |
| Did they over-engineer? | Simple linear scorer + pairwise refinement + templated reasoning. LGBM only if eval shows it earns its keep |
| Did they think about the recruiter, not just the metric? | README section "Designed for the recruiter, not the metric." |
| Calibration | Scoring spans real range; top-10 scores visually separated from next 10 |
| Edge case handling | Every probe has a default for missing data |
| Sandbox works | HuggingFace Space, Streamlit upload, <30 sec on 50-candidate sample |

---

## 14. matrix-main reuse policy

`matrix-main` is the team's **KnowTruly.me** project (public repo), semantic resume + verification platform for students. FastAPI + Postgres + Qdrant + React.

**Reuse policy:**

| Component | Decision | Reason |
|---|---|---|
| `frontend/src/pages/recruiter/` UI | **Adapt for our sandbox** | Polished recruiter UI saves ~1 day; signals professionalism to judges |
| `backend/app/services/audit_service.py` | **Concept only, not code** | Audit-log idea informs our `submission_structured.jsonl` |
| CONSTITUTION.md principles (semantic-first, live-and-auditable, privacy-by-design, deterministic UX) | **Cite in README** | Demonstrates team's architectural maturity beyond this hackathon |
| `match_service.py`, `embedding_service.py`, `vector_store.py` | **Do NOT reuse** | Different algorithm, different problem; reuse would weaken defensibility |
| FastAPI / Postgres / pgvector / Qdrant backend stack | **Do NOT use** | Overkill for sandbox; we use minimal Streamlit |
| Typst resume generation, signature service | **Not relevant** | Out of scope |

**Public-repo strategy:** since matrix-main is public, judges may find it. We **declare lineage openly** in our README:

> *"Sandbox UI components adapted from team's prior project KnowTruly.me (public repo at github.com/.../matrix-main). The ranking algorithm, probe library, eval set, and submission pipeline are built fresh for this hackathon."*

Hidden lineage is a risk. Declared lineage is a credibility marker, shows we're a team that builds, not just submits.

---

## 15. Design System & UI/UX

### 15.1 Why design matters here

Most teams will submit a Streamlit form with a textbox and a "Run" button. The submission spec requires a sandbox, most will satisfy it minimally. A *designed* product is an implicit signal to Redrob engineers that we think like product builders, not just modellers. The sandbox isn't a Stage-1 checkbox, it's the most direct way a judge experiences our system before reading any code.

**The judge's path:**
1. Opens our submission portal entry.
2. Clicks the sandbox link.
3. Has 30 seconds to form a first impression.
4. Has maybe 2 minutes to explore.

The first 30 seconds determine everything downstream. We engineer them.

---

### 15.2 Guiding principles

Ten rules. If a design choice violates one of these, it's wrong.

1. **One thing per screen.** No dashboards. Each view has exactly one job.
2. **Content is the chrome.** No headers, footers, sidebars unless they earn their place. Strip every default chrome element until removing it would break the function.
3. **Show, don't tell.** Visualise SNR with colour and opacity, not labels. A child should understand which candidate is strong without reading text.
4. **Less is more, said in fewer words.** Every label, button, heading must justify itself. "Why?" beats "Explanation." "Begin." beats "Click here to start exploring candidates."
5. **One accent colour, used sparingly.** A single warm tone reserved for the decisive moment, the system's choice, the user's pick, the verified signal. Everything else is monochrome.
6. **Calm typography.** Big serif headlines, small sans body. Generous line-height. No all-caps. No tiny text. No squashed kerning.
7. **Animations earn their keep.** Only animate to convey meaning. Loading states, score reveals, page transitions. Never decorative motion.
8. **Real data, real names.** Show actual candidates from the labelled set. No "User_001." No placeholder text.
9. **The reasoning IS the design.** Reasoning text reads like Claude wrote it, calm, specific, honest. The system's voice is the system's interface.
10. **No skeuomorphism, no gloss.** Flat surfaces. Hairline borders. No drop shadows on drop shadows. No gradients. Apple's iOS 7 reset, not the previous decade of glassmorphism.

---

### 15.3 What we steal

Great artists steal. Here's the explicit attribution and how each shows up in our product.

| From | What we take | How it shows up here |
|---|---|---|
| **Apple** | Typography hierarchy, generous whitespace, content over chrome, smooth physics-based motion, one accent colour, no onboarding | Whole visual language; first screen is a single thought, not a dashboard |
| **Linear** | Keyboard-first feel, hairline borders, calm density, the courage to remove things others would keep | Keyboard shortcuts as primary navigation through the deck (Enter to interview, → to next, ← to back); no scrollbars where unneeded |
| **Cron / Notion Calendar** | Soft animations, command-palette restraint, the way information feels weightless | Page transitions; the calm pause cards between acts |
| **Things 3** | Quiet status indicators, never demanding attention, the dignity it gives a single to-do | Shortlist counter, a small text count, no badge animation |
| **Pinterest / Tinder** | One item at a time, full viewport, the feeling of *flicking* through possibilities | **The deck**, the central interaction. Each candidate is full-screen, briefly, before they pass |
| **Claude** | Off-white background (warm, never pure #FFF), calm conversational copy, hairline borders, the reasoning text that reads like a thoughtful colleague wrote it | Background palette; every line of micro-copy; the literary feel of candidate introductions |
| **Stripe Dashboard / Docs** | Specific over generic, calm density, code-like precision in data display | The way evidence strings are written ("3.2y at Stripe Search, BGE-based retrieval") |
| **iA Writer** | The discipline of reducing to essence; the way blank space is content | The opening JD digest screen, almost nothing on it |
| **Duolingo (selectively)** | Micro-progress states that make waits feel like progress | `Reading 1,000 profiles. Listening for signal. Ready.`, three states, each 200ms. **No** streaks, **no** XP, **no** mascot. Gamifying recruitment is undignified |

---

### 15.4 Visual language

#### Colour palette, two-colour system

Each colour does exactly one job. Restraint is the brand.

| Token | Hex | Job |
|---|---|---|
| `--bg-canvas` | `#FBF8F2` | Page background, warm off-white. Never `#FFF` |
| `--bg-card` | `#FFFFFF` | Card surfaces, slight contrast against canvas |
| `--ink-primary` | `#1A1A1A` | Headings, candidate names, primary text |
| `--ink-secondary` | `#5A5A5A` | Body, evidence strings |
| `--ink-tertiary` | `#9A9A9A` | Captions, time stamps, micro-labels |
| `--hairline` | `#EAE6DC` | Borders, dividers, always thin, always quiet |
| **`--action`** | `#1F2933` | Primary actions, graphite. *"Interview"*, *"Show me who fits"*, *"Send shortlist"*. Confident, professional, calm |
| **`--accent`** | `#B8843B` | Reserved for *the system found something* moments, the whispered hint, a verified signal, the closing reflection. Used sparingly, like an editor's marginalia |
| `--signal-verified` | `#B8843B` | High-SNR, warm ochre (matches accent, they're the same idea) |
| `--signal-claimed` | `#C9C2B1` | Low-SNR, muted parchment |
| `--signal-concern` | `#A85B3A` | Concerns, muted earth-red, never alarm-bright |

No bright blues. No corporate accents. No gradients. No glassmorphism. Two purposeful colours; everything else is ink on cream.

#### Typography, Fraunces + Inter

- **Display** (landing JD digest, candidate names): **Fraunces** (Google Fonts), 56–72px on desktop, weight 400 with optical size set to display. Fraunces is an opinionated literary serif with personality but not weirdness. Free. Editorial feel.
- **Body** (UI text, evidence, paragraphs): **Inter**, 16–18px, weight 400, line-height 1.6.
- **Caption** (micro-labels, time stamps): Inter, 13px, weight 500, letter-spacing 0.01em.
- **Monospace** (candidate IDs only): JetBrains Mono, 13px.

Hierarchy comes from **size and family contrast**, never from weight. No bold-everything. No all-caps. No squashed kerning.

> **Why Fraunces over IBM Plex Serif:** Plex is fine but slightly corporate. Fraunces has the personality of a magazine, exactly the editorial calm we want for candidate cards that should feel curated, not data-rendered.

#### Spacing

8-point grid. Components breathe. No element touches another within a card unless they're semantically connected. Section spacing is generous, 64px+ between major blocks.

#### Iconography

Lucide React or Heroicons (outline weight). Iconography is purely functional, never decorative. Icon-only buttons must have a tooltip; otherwise use a short text label.

---

### 15.5 The engineered "ahha" moments, distributed across the journey

Not one demo at the front. **Five moments distributed across the user's actual journey.** Each one earned by what came before it. Earned moments stick; demoed moments don't.

#### Ahha #1, *"It listened to me."* (0:05, the JD digest)

The first screen isn't a form, isn't a demo, isn't a sales pitch. It's the JD reflected back as a calm 4–6 line summary the system extracted:

> Senior AI Engineer.
> Pune or Noida. Five to nine years.
> Hands-on, not architect-only.
> Avoid: consulting-only careers, framework enthusiasts, pure researchers.
>
> `Show me who fits.`

The user reads it. They feel *seen*. The system understood the JD the same way they would have explained it to a junior recruiter. The SNR extraction is on display, but humbly, as an act of listening, not a magic trick.

#### Ahha #2, *"This is gorgeous."* (0:30, the first candidate)

The deck opens. One candidate, full viewport. Fraunces serif name in 64px. Their role beneath. The SNR Split below the role, dense left panel, sparse right. Below that, a literary one-paragraph introduction that reads like a colleague describing them:

> Sarah leads retrieval at Stripe Search. Three years on BGE-based systems, owns the NDCG evaluation harness, ships weekly. Eight-week notice.

Two actions at the bottom: `Interview` (graphite), `Next` (quiet text link). The user feels they're meeting a person, not querying a database.

#### Ahha #3, *"It found someone I'd have missed."* (~2:00, candidate ~11)

Around candidate 11–12, a plain-language tier-5 appears, a profile that looks unassuming on the surface but whose description text reveals a real production ranking system shipped at scale. A small italic line appears beneath their name:

> *"Easy to overlook. Watch this one."*

That's it. The system whispers, doesn't lecture. The user pauses, reads carefully, and clicks `Interview`. This is the *trap demo* from before, but **earned**, in the flow of work, not pre-emptively performed.

#### Ahha #4, *"It's honest about its concerns even on top picks."* (~3:00, top-rank candidate with a real issue)

A clearly strong candidate appears. Their introduction is glowing. But beneath, in matter-of-fact tone:

> *"Two months out. Fair warning."*

The system doesn't hide the gap. The user trusts the system more because of this honesty, not less. (Stage-4 reviewers will love this. It's the explicit "rank consistency: top candidates aren't perfect either" signal the spec rewards.)

#### Ahha #5, *"It knew what I valued."* (~6:00, the reflection)

After the user has worked through ~20 candidates and reviewed their shortlist, they click `Send shortlist`. JSON copies to clipboard. A quiet line appears:

> Done.
> Four candidates from one thousand.
> About six hours saved.

Below it, italicised:

> *You favoured production retrieval over framework familiarity. We'll remember.*

This is the HITL learning **made warm**. It's not the system demonstrating its ability to learn, it's the system *being* a colleague who noticed something about you. This is the line that makes recruiters tell their peers about the tool.

---

### 15.6 The journey, six acts

Not a screen architecture, a **journey** with acts, pacing, and emotional beats. The product feels like an experience the user moves through, not a dashboard they navigate.

#### Act 1, Arrival (the JD digest)

- Full viewport. Warm cream background. Nothing else but the JD distilled to 4–6 lines, Fraunces serif type, generous line-height.
- One CTA at the bottom: `Show me who fits.`
- No nav, no logo, no chrome, no menu. The page IS the JD reflection.
- Cycles through `Reading 1,000 profiles → Listening for signal → Ready.` on click, three states, 200ms each.

#### Act 2, The deck (one candidate at a time)

This is the central interaction. Not a list. Not a table. **The deck.**

- Each candidate occupies the full viewport. Name in 64px Fraunces. Role beneath in calm sans.
- The SNR Split sits below, dense "we trust this" panel left, sparse "they claim this" panel right.
- A single literary paragraph (the reasoning) reads beneath as the candidate's introduction.
- A small concern line if applicable (matter-of-fact, never alarmist).
- Two actions: `Interview` (graphite primary) | `Next` (quiet text link).
- **Keyboard-first:** Enter or `I` to interview, `→` or space for next, `←` to go back, `K` to keep moving.
- Rank position is **never shown as a number**. Users see candidates in rank order; the ordering is implicit.
- Background hue is subtly warmer for top picks, more neutral as we descend the deck, perceptible but not labelled.

#### Act 3, Whispered insights (distributed through the deck)

- Around candidate 11–12: a plain-language tier-5 with a small italic *"Easy to overlook. Watch this one."* beneath their name.
- Around candidate 16: a top candidate with a real concern. *"Two months out, fair warning."* in italic. No exclamation. No alert icon. Calm honesty.
- Around candidate 20–25: a candidate whose strengths are mismatched. *"Strong, but for a different role. Save anyway?"*

The system whispers. Doesn't lecture. Doesn't break the deck rhythm.

#### Act 4, Pause (the breath)

After ~20 candidates a single calm card appears, separate from the deck flow:

> Take a breath.
> Shortlist of 4.
>
> `Keep going` | `See shortlist →`

No urgency. No streak counter. Just the dignity of a pause. (Recruiting is emotional work; the system acknowledges that.)

#### Act 5, Shortlist review

- The candidates the user kept appear as a 2× grid (or stack on mobile).
- The system's proposed priority order is shown; the user can drag to reorder.
- No numbers on the cards. Just the people they chose.
- One action at the bottom: `Send shortlist.`

#### Act 6, Reflection (the close)

- `Send shortlist` copies a clean JSON to clipboard (mimics HRMS webhook shape per spec §10.3).
- Confirmation: a single quiet line:

> Done.
> Four candidates from one thousand.
> About six hours saved.

- And below, the reflection:

> *You favoured production retrieval over framework familiarity. We'll remember.*

- Two final options: `Start over` | `See full ranking →` (the escape hatch for power users / judges who want to see all 100 in a list view).

#### Inline moments (appear within the journey, never as standalone screens)

- **Compare**, appears organically when the user shortlists 3+ candidates whose scores are close: a soft prompt *"Three of these are close calls. Side by side?"* The user can dismiss. If they accept, two cards appear with `This one.` | `That one.` actions.
- **Micro-Interrogation**, appears only when the user passes on a candidate the system ranked highly. A modal overlay: *"What did we miss?"* with four calm options. Reads like an editor's correction, not an interrogation. No-op for hackathon; Stage-5 narrative says: *"one click is one SGD step on the relevant probe weight."*

---

### 15.7 Micro-copy guide

Every label, button, and heading is written to spec. The voice is *calm colleague*, not *enthusiastic SaaS product*.

| Where | What we use | Not |
|---|---|---|
| Landing CTA | `Show me who fits.` | "See the ranking" |
| Loading sequence | `Reading 1,000 profiles. Listening for signal. Ready.` | "Loading…" |
| Primary candidate action | `Interview` | "Add to shortlist" |
| Secondary candidate action | `Next` | "Pass" or "Reject" |
| Card concern callout | `Two months out, fair warning.` | "Risk factors: extended notice period" |
| Whispered hint | *`Easy to overlook. Watch this one.`* | "Hidden gem detected" |
| SNR panel labels | `We trust this.` / `They claim this.` | "Verified" / "Self-reported" |
| Why-not flip | `Tell me more.` | "Show explanation" |
| Compare prompt | `Side by side.` | "Compare these candidates" |
| Override modal | `What did we miss?` | "Provide feedback on this ranking" |
| Shortlist counter | `Shortlist of 4.` | "4 candidates shortlisted (selected)" |
| Pause card | `Take a breath.` | "You've reviewed 20 candidates. Continue?" |
| Closing line | `Done. Four from one thousand. About six hours saved.` | "Process complete" |
| Reflection | *`You favoured production retrieval over framework familiarity. We'll remember.`* | "Your preference profile has been updated" |
| Empty state | `Drop a file to begin.` | "Please upload a JSON file" |
| 404 | `That candidate isn't here.` | "404 Not Found" |

**Three rules for every line of copy:**
1. Read it aloud. If it sounds like a 2008 software dialog, rewrite.
2. Position the user as the expert, the system as the listener. "What did *we* miss?" not "What did *you* see?"
3. Every line could be quoted in a tweet. If it's not quotable, it's filler.

---

### 15.8 Micro-interactions catalog

| Interaction | Duration | Easing | Purpose |
|---|---|---|---|
| Page transition | 200ms | ease-out cross-fade | Continuity between screens |
| Card hover lift | 150ms | ease-out | Affordance |
| Card expand | 300ms | ease-in-out | Reveal more content |
| Trap-demo flip | 400ms | spring (mass 1, stiffness 120) | Satisfying physics |
| Score / rank reveal | 50ms stagger × n | ease-out | Sequencing perception |
| Compare-mode swipe | physics-based (Framer Motion) | spring | Visceral choice |
| Modal open | 250ms | ease-out + slight scale-up | Focal attention |
| Loader state change | 200ms | ease-in-out | Progress feels intentional |

**Never used:** parallax scrolling, confetti, auto-playing video, animated logos, marquee, anything that delays user input.

---

### 15.9 Mobile considerations

The judge may preview on their phone. The sandbox must work fully on mobile.

- **Trap demo:** cards stack vertically; reveal still functions.
- **Ranking:** single-column list, card height ~120px each.
- **Deep-dive:** SNR split becomes vertical stack on narrow viewports (≤640px).
- **Compare mode:** uses swipe gestures natively on touch, actually *better* on mobile than desktop.
- **Typography:** display sizes scale with `clamp()` so headlines don't break on small screens.
- **Touch targets:** minimum 44×44px for any tappable element.

We test on iPhone Safari and Chrome Android before submission.

---

### 15.10 Implementation stack

**Frontend:**
- React 18 + Vite 5 (lifted base from `matrix-main`'s frontend; pages are custom-built for this).
- Tailwind CSS for styling (custom config matching our colour tokens and type scale).
- Framer Motion for animations (spring physics, layout animations, gesture handling).
- Lucide React for iconography.
- React Router for the 5 screens.

**Backend:**
- FastAPI exposing a single `/rank` endpoint.
- Our `rank.py` logic underneath.
- Pre-loaded with a curated 30-candidate sample (mix of tier-5, tier-3, keyword-stuffers, and a honeypot or two, chosen from our labelled eval set).
- Optional: accept user-uploaded `candidates.jsonl` (≤100 rows per spec §10.5).

**Deployment:**
- Single HuggingFace Space using Docker (multi-stage: builds the React frontend, FastAPI serves static + API).
- All inference fits in <100ms on the small 30-candidate sample.
- No external dependencies at runtime.

**Why this stack and not Streamlit/Gradio:**
- Streamlit is fine for forms; it's bad at the design fidelity we want. Custom CSS in Streamlit fights the framework.
- Gradio is better for ML demos but constrains the UI vocabulary.
- React + Tailwind + Framer Motion is the de facto stack for designed web products. Lifting the base from `matrix-main` saves 6+ hours.

**Source-of-truth disclosure in README:** *"Sandbox UI base and layout components adapted from team's prior project KnowTruly.me (public). The ranking algorithm, probe library, eval set, and submission pipeline are built fresh for this hackathon. UI pages, animations, and copy are custom for this submission."*

---

### 15.11 Anti-patterns we explicitly avoid

| Anti-pattern | Why we avoid |
|---|---|
| Streamlit-default look | Reads as "I didn't think about design" |
| Bright blue corporate buttons | Reads as enterprise SaaS, not crafted product |
| Bar charts of scores | We deliberately hide raw scores from recruiters |
| Modal with 5 fields | Recruiters won't read 5 fields |
| Loading spinners with no context | Use progress states with verbs instead |
| Auto-playing animations on first load | Respects nobody |
| Big logo / brand placement | We have no brand to push; the work speaks |
| Tooltips that say what's obvious | Don't label what's already visible |
| Skill bars with percentages (75% Python, 80% SQL) | Patronising and meaningless; we use the SNR split instead |
| Stars / score-out-of-10 | Pretend precision; we use rank position only |
| Mandatory onboarding tour | Apple doesn't have onboarding. Neither do we. |
| Dark-mode toggle | Hackathon, one theme, calibrated to one direction |

---

### 15.12 The journey walkthrough (recruiter's experience, scripted)

This is the full choreographed user journey from arrival to reflection. Every beat is intentional.

| Time | Beat | What the user feels |
|---|---|---|
| **0:00** | Opens link. Warm cream page, 6 lines of Fraunces serif type laying out the JD as a summary. One CTA: `Show me who fits.` | "It's calm. Like opening a book." |
| **0:05** | Reads the JD digest. Realises the system distilled the brief the way they would have. | *"It listened to me."* (Ahha #1) |
| **0:10** | Clicks `Show me who fits.` Three quick loader states: `Reading 1,000 profiles. Listening for signal. Ready.` Each 200ms. | "It's working, and showing me it's working." |
| **0:15** | First candidate fills the viewport. Big serif name. SNR Split below. Literary intro paragraph. Two actions. | *"This is gorgeous."* (Ahha #2) |
| **0:30** | Reads the intro. Sees the dense High-SNR panel. Clicks `Interview`. Card softly exits left. Next candidate arrives. | "I want to keep going." |
| **1:00** | Five candidates in. Two interviewed, three passed. Shortlist counter shows *Shortlist of 2* in the corner, quiet, unobtrusive. | "I'm making progress." |
| **2:00** | Candidate 11 appears. A plain-language tier-5 with the small italic *"Easy to overlook. Watch this one."* under their name. User pauses, reads carefully. Clicks `Interview`. | *"It found someone I'd have missed."* (Ahha #3) |
| **3:00** | A strong candidate appears with a 60-day notice flagged matter-of-factly. The system didn't hide the concern even on a top pick. | *"It's honest about its concerns even on top picks."* (Ahha #4) |
| **4:00** | The pause card appears: `Take a breath. Shortlist of 4.` User pauses, breathes, clicks `See shortlist`. | "It respects my time." |
| **5:00** | Shortlist grid view. Four candidates the user kept. Drag-reorder to set priority. | "I'm in control. The system is the assistant." |
| **5:30** | Clicks `Send shortlist`. JSON copies to clipboard. | "It closed the loop." |
| **5:45** | Sees: `Done. Four from one thousand. About six hours saved.` Then italicised: *`You favoured production retrieval over framework familiarity. We'll remember.`* | *"It knew what I valued."* (Ahha #5) |
| **6:00** | User closes the tab. Thinks about telling their team about it. | The product they'll talk about at lunch. |

**Total flow:** ~6 minutes. Five engineered moments. One sentence at the end that gets quoted.

---

### 15.13 The quotable lines (designed to be repeated)

These are the lines and moments engineered to be **quoted** by recruiters telling their peers about the tool:

| Quote | Engineered by |
|---|---|
| *"It shows you candidates one at a time, like Tinder, but for hiring."* | The deck as the central interaction |
| *"It admits when it might be wrong."* | The inline concern callouts on top picks |
| *"It told me at the end what I'd been biased toward. I didn't even realise."* | The reflection sentence in Act 6 |
| *"It's beautiful. Like the calendar app I actually want to use."* | Fraunces typography + cream palette + restraint |
| *"It doesn't have photos. Just words."* | No avatars, typography is identity |
| *"It found someone I would have missed."* | The whispered hint on candidate 11 |
| *"The way it explains itself is calm."* | Claude-voice micro-copy throughout |

A masterpiece isn't designed for users to *use*. It's designed for users to *recommend*.

---

## 16. vision.md coverage map

Every distinct idea from vision.md mapped to status. Complete sweep.

| Vision.md point | Status |
|---|---|
| Stand out / distinct | ✅ SNR is original framing |
| Beyond surface keywords | ✅ substance + narrative + hybrid |
| Hidden gems / behavioural signals | ✅ behavioural as multiplicative + tier-5 surfacing |
| Deep JD understanding | ✅ JD-as-spec; per-sentence probes |
| Avoid standard embed→cosine→rerank | ✅ structured probes + hybrid; structured probes do precision |
| Kinetic Trajectory (direction / velocity / acceleration) | ✅ all three are features |
| Latent JD Archetype (Tech Stack / Execution Env / Friction Point) | ✅ emitted as composite axes in structured output |
| Multi-Agent Forensic Reranker | ✅ cut at runtime; pairwise refinement is the surviving idea |
| Three persona agents | ✅ cut |
| Pairwise / contrastive | ✅ pairwise refinement on top 20 |
| Cultural OS Lexicon | ✅ softened to summary-thoughtfulness + shipper-verb |
| OAVS / privilege normalization | ✅ correct interpretation = education weight zero |
| Environmental DNA, Pace & Volatility | ✅ company_stage_alignment |
| Environmental DNA, Governance | ✅ cut (not JD-relevant) |
| Environmental DNA, Engineering Culture | ⚠️ light-weight description-text features capture some |
| AI-tailored resume stuffing | ✅ central design defense |
| Critical-thinking inferred not matched | ✅ narrative arc density |
| YoE/education bias | ✅ education = 0; YoE = gaussian |
| Fresher with right keywords | ✅ keyword_dense_junior anti-probe |
| Aerospace 2yr beats generic 8yr | ✅ dilution_penalty + years_at_product_co |
| HRMS integration / next_step routing | ✅ submission_structured.jsonl |
| Different HR scales | ✅ cut from submission; Stage-5 narrative item |
| Substance-Over-Syntax | ✅ central probe |
| Entropy of Execution | ✅ description specificity |
| Directed Knowledge Graph | ✅ flat verb list; presented as graph diagram in README |
| Domain Multiplier | ✅ ML-at-product-co years |
| Dual-Mode Pipeline | ✅ cut (N fixed) |
| HITL Continuous Realignment | ✅ architecture property only |
| Micro-Interrogation UI | ✅ added as sandbox mock for Stage-5 demo |
| Scalar Weight Online Update | ✅ implicit in linear probe weights |
| Contextual Memory Buffer | ✅ cut (no LLM) |
| Why & Why Not explainability | ✅ tier 50–100 names what's missing; sandbox shows Why-Not for top rank too |
| SNR Classification, High vs Low | ✅ central architectural principle |
| High-SNR examples (verified velocity, GitHub, etc.) | ✅ all mapped to probes |
| Low-SNR examples downweighted | ✅ |
| Real-Time Forensic Explainer Panel | ✅ sandbox evidence panel |
| Visual SNR Separation in UI | ✅ sandbox shows High-SNR vs Low-SNR side-by-side |
| Honeypot: salary paradox | ✅ rule 1 |
| Honeypot: duration paradox | ✅ rules 3 + 4 |
| Honeypot: chronological paradox | ✅ rule 2 |
| Honeypot: expert incongruence | ✅ rule 5 |
| Honeypot: company-age vs tenure | ✅ rule 6 |
| Consulting-only penalty | ✅ hard-no probe |
| Product-co boost | ✅ probe |
| Pydantic output validation | ✅ added |
| Cross-encoder reranker | ⚠️ deferred, submission-3 consideration if eval-set NDCG@10 allows |
| Qdrant / Faiss | ✅ not needed (numpy matmul faster on CPU for 100K-row one-shot query); documented in README |
| preferred_work_mode probe | ✅ added |
| certifications probe | ✅ added |
| willing_to_relocate × location | ✅ in location probe |
| salary_range as fit signal | ✅ skip (no anchored band) |

---

## 17. Stage-by-stage defense (Stages 1–5)

**Stage 1, Format validation:**
- Pydantic-validated CSV row schema in `rank.py`.
- Local pre-flight run of `validate_submission.py` before every submission.
- Output filename = team_id.csv per spec.

**Stage 2, Scoring:**
- Optimized weights via eval-set NDCG@10.
- Pairwise refinement on top 20 targets the 50%-weighted metric directly.
- Submission 1 is health-validation; submission 2 is main shot; submission 3 is polish.

**Stage 3, Code reproduction + honeypot check:**
- Single command in README: `python rank.py --candidates ./candidates.jsonl --out ./submission.csv`.
- Dockerfile with pinned `requirements.txt`.
- Sandbox-tested before submission.
- 6-rule honeypot detector, conservative but defensible; expected honeypot rate in top-100: ≤2%.

**Stage 4, Manual review:**
- Reasoning passes all 6 checks by construction (specific facts, JD connection, honest concerns, no hallucination, variation, rank consistency).
- README is engineering-spec quality, no marketing.
- Real git history with 8–12 commits over the week.
- `methodology_summary` in `submission_metadata.yaml` is ≤200 words leading with SNR architecture.

**Stage 5, Defend-your-work interview:**
- 90-second opening narrative locked in (see §21).
- Per-design-choice defense ready: every weight maps to a JD sentence.
- Sandbox demo runnable live with Why-Not panel and Micro-Interrogation mock.
- *Discovered insight* about the dataset (TBD during EDA), memorable hook.

---

## 18. Folder structure and deliverables

```
matrix/
├── README.md                            # Lead: SNR thesis. Stripped of marketing.
├── final_plan.md                        # This document.
├── submission_metadata.yaml             # Filled-in metadata for portal upload.
├── requirements.txt                     # Pinned versions.
├── Dockerfile                           # Stage-3 reproduction.
├── .gitignore
│
├── rank.py                              # Single entry point, runs in <30s for 100K
│
├── src/
│   ├── __init__.py
│   ├── schema.py                        # Pydantic models, input + output validation
│   ├── load.py                          # Stream candidates.jsonl
│   ├── honeypot.py                      # 6 deterministic rules
│   ├── probes/
│   │   ├── must_have.py                 # Probes A
│   │   ├── nice_to_have.py              # Probes B
│   │   ├── substance.py                 # Probes C
│   │   ├── anti_snr.py                  # Probes D
│   │   ├── behavioural.py               # Probes E
│   │   ├── retrieval.py                 # BM25 + dense cosine
│   │   ├── location.py                  # Probes G
│   │   └── latent_axes.py               # Composite aggregates H
│   ├── scoring.py                       # Composition + weights
│   ├── pairwise.py                      # Top-20 refinement
│   ├── reasoning.py                     # 6 templates per band
│   ├── output.py                        # CSV + structured JSONL
│   └── precompute.py                    # Standalone, embeds candidates
│
├── data/
│   ├── precomputed_embeddings.npy       # Generated by precompute.py
│   └── company_dict.json                # Product-co / consulting / bigcorp / founding years
│
├── eval/
│   ├── sample_to_label.jsonl            # 300 stratified candidates
│   ├── candidates_to_label.md           # Markdown profiles for labelling
│   ├── labels.csv                       # User fills this
│   ├── labels_template.csv              # Pristine template
│   ├── sampling_report.md               # Heuristic doc
│   ├── merge_labels.py                  # Merges CSV labels + JSONL profiles
│   └── metrics.py                       # NDCG@k, MAP, P@k computation
│
├── sandbox/
│   ├── Dockerfile                       # Multi-stage: build frontend, serve via FastAPI
│   ├── backend/
│   │   ├── main.py                      # FastAPI app, /rank endpoint
│   │   ├── inference.py                 # Wrapper around src/ rank logic
│   │   └── sample_candidates.json       # Pre-loaded curated 30-candidate demo set
│   ├── frontend/
│   │   ├── package.json                 # React + Vite + Tailwind + Framer Motion
│   │   ├── vite.config.ts
│   │   ├── tailwind.config.cjs          # Custom tokens, colours, type scale, spacing
│   │   ├── index.html
│   │   └── src/
│   │       ├── main.tsx
│   │       ├── App.tsx                  # Journey router (Act state machine)
│   │       ├── acts/
│   │       │   ├── Act1_JDDigest.tsx    # Landing, JD reflected back
│   │       │   ├── Act2_Deck.tsx        # The deck, one candidate at a time
│   │       │   ├── Act4_Pause.tsx       # "Take a breath" card
│   │       │   ├── Act5_Shortlist.tsx   # Grid review with drag-reorder
│   │       │   └── Act6_Reflection.tsx  # Closing line + reflection
│   │       ├── components/
│   │       │   ├── CandidateView.tsx    # Full-viewport single-candidate display
│   │       │   ├── SNRSplit.tsx         # The High/Low SNR panels
│   │       │   ├── WhisperedHint.tsx    # Italic line beneath candidate name
│   │       │   ├── ConcernCallout.tsx   # Matter-of-fact concern line
│   │       │   ├── WhyNotFlip.tsx       # 3D card flip ("Tell me more")
│   │       │   ├── CompareOverlay.tsx   # Inline compare when 3+ close shortlist
│   │       │   ├── MicroInterrogation.tsx  # "What did we miss?" modal
│   │       │   ├── ShortlistCounter.tsx # Quiet text counter
│   │       │   └── LoaderSequence.tsx   # Three-state progress loader
│   │       ├── hooks/
│   │       │   ├── useKeyboard.ts       # Enter/→/←/I/K shortcuts
│   │       │   └── useDeck.ts           # Deck state, position, shortlist, etc.
│   │       ├── styles/
│   │       │   ├── tokens.css           # CSS custom properties matching §15.4
│   │       │   └── fonts.css            # Fraunces + Inter via Google Fonts
│   │       └── lib/api.ts               # POST /rank
│   └── README.md                        # Sandbox usage + deployment notes
│
├── audit/
│   └── reasoning_audit.py               # Offline LLM hallucination check (pre-submission)
│
└── tests/
    ├── test_probes.py
    ├── test_honeypot.py
    ├── test_output_validation.py
    └── fixtures/                         # 10 hand-crafted candidate examples
```

**Submission deliverables:**
1. `<team_id>.csv`, the ranked output.
2. GitHub repo (public): `github.com/saurabh4269/matrix`.
3. Sandbox link: HuggingFace Space.
4. Portal metadata + `submission_metadata.yaml` in repo root.

---

## 19. Build order and milestones

**Phase 0, Eval set foundation (Day 1):**
- Build stratified sampler.
- Generate `candidates_to_label.md` + `labels.csv` for 300 candidates.
- Hand-label all 300 (one focused session, 3–6 hours).
- Calibration check: `bucket × tier` crosstab.

**Phase 1, Honeypot + Hard-DQ (Day 2):**
- 6-rule honeypot detector.
- Hard-no anti-SNR probes (consulting-only, bigcorp-only, pure-research, etc.).
- Validate against labelled honeypots, should achieve ≥95% recall on `is_honeypot=true`.

**Phase 2, Probe library (Day 2–3):**
- All 30+ probes implemented as pure functions.
- Each probe returns `(score, evidence_string)`.
- Each probe has unit test against fixture candidates.

**Phase 3, Precomputation + hybrid retrieval (Day 3):**
- Embed all 100K candidates with `all-MiniLM-L6-v2`.
- BM25 index over candidate text.
- Save to `data/precomputed_embeddings.npy`.

**Phase 4, Scoring + pairwise (Day 3–4):**
- Composition function.
- Pairwise refinement on top 20.
- Hand-tuned initial weights.
- **Submission 1**, health validation, format-pass, format-validate.

**Phase 5, Reasoning generator (Day 4):**
- 6 templates × 3 bands.
- Deterministic seeding by candidate_id.
- Spot-check on labelled eval set.

**Phase 6, Iteration (Day 5):**
- Eval-set tuning.
- Optional LightGBM-Rank weight learner.
- **Submission 2**, main shot.

**Phase 7, Sandbox & design (Day 5–7, parallel with Phase 6):**
- Lift React/Vite/Tailwind base from `matrix-main`; strip KnowTruly-specific code.
- Build 5 screens per §15.6: Landing (Trap Demo), Ranking, Candidate Detail, Compare, Override modal.
- Implement design tokens per §15.4, colour palette, type scale, spacing.
- Implement micro-interactions per §15.8, page transitions, card flip, SNR Split, swipe.
- Curate 30-candidate sample for sandbox demo (includes labelled tier-5s, keyword-stuffers, one honeypot for the trap demo).
- Mobile responsive test (iPhone Safari, Chrome Android).
- Deploy to HuggingFace Space via Docker.

**Phase 8, Final polish (Day 7):**
- Manual review of submission 2 top-100 (~50 min).
- Offline LLM reasoning audit on the 100 generated reasonings.
- README polish, lead with SNR architecture, declare matrix-main lineage, include knowledge-graph diagram.
- `submission_metadata.yaml` filled.
- Stage-5 narrative rehearsed.
- **Submission 3**, polish (only if it improves eval NDCG@10).

**Git discipline:** real commits at each phase, not single dump. Commit messages describe the design decision, not just the file change.

---

## 20. Known limitations

These are honest acknowledgments for the README and Stage-5 interview.

1. **Eval set ≠ ground truth.** Our 300 hand labels approximate the hidden ground truth; they're our best signal but not perfect. Risk of overfitting to our biases.
2. **Company stage history not in dataset.** We can't see what a company's size was when the candidate joined, only the current size. Can't directly reward "scaled-with-company" experience.
3. **No longitudinal profile data.** Can't detect "candidate recently AI-tailored their profile" beyond weak heuristics (signup vs last_active proximity).
4. **Cross-encoder reranker not used.** Could marginally improve top 20 with a CPU-small cross-encoder. Deferred to submission 3 only if budget permits.
5. **Single JD only.** Probe weights are tuned to this JD. The architecture generalizes to other JDs by re-deriving probes; the weight calibration would need to be redone.
6. **No A/B test data.** A real production system would correlate offline NDCG with online recruiter-engagement metrics. We can't.

These are *features* for the interview, not bugs, they show we understand the limits of our own system, which is a senior-engineer trait the JD explicitly looks for.

---

## 21. Mathematical foundations and borrows

The system is built on a structured-feature scorer that's been deliberately calibrated; on top of that, we layered six borrowed mathematical ideas, each filling a specific gap.

### Shipped

| Borrow | Source | What it does |
|---|---|---|
| **Z-score standardisation** | Quantitative finance | `compute_pool_stats` + `z_scores` in src/calibration.py. Per-candidate percentiles against the whole-pool mean+std. Surfaced as "97th percentile in substance" in the structured JSONL |
| **Mahalanobis outlier distance** | Anomaly detection | Diagonal Mahalanobis distance from the pool centroid. Statistical complement to the deterministic honeypot rules; flags candidates whose probe vector is unusually far from the population |
| **Bayesian posterior confidence** | Bayesian statistics | Naive-Bayes posterior `P(tier-5 \| evidence)`. Reframes the heuristic confidence buckets as a proper probability. Priors derived from the JD's "10 great matches in 100K" stinginess |
| **Portfolio diversity (MMR)** | Portfolio theory | Maximal-Marginal-Relevance pass on the top 20 that spreads candidates across companies + locations. Visibly improved the top-10 composition |
| **Expected Reciprocal Rank** | Information retrieval | Eval metric that models recruiter stop-after-first-satisfying-hit behaviour. Added to `eval/metrics.py` alongside NDCG/MAP/P@k |
| **Shannon entropy** of skill claims | Information theory | Catches AI-tailored profiles whose skill claims are suspiciously uniform. Real engineers have heterogeneous claim distributions |
| **Conformal-style rank intervals** | Conformal prediction | 50 Gaussian-noise perturbations of each candidate's probe scores → 95% rank CI. "Sarah is rank 1, stable in 1-3" instead of just "rank 1" |
| **LightGBM-Rank weight learner** | Learning-to-rank | `eval/tune_weights.py`. Trains a pairwise-loss model with NDCG@10 eval metric against the labelled set. Produces YAML weights ready to drop into a JD config |
| **Cross-encoder rerank** | Information retrieval | Optional `--cross-encoder` flag. Loads ms-marco-MiniLM-L-6-v2 (CPU-small) and blends its (JD, candidate) relevance score with our linear score on the top 50 |
| **Multi-agent LLM debate** (offline) | Multi-agent reasoning | `eval/offline_debate_check.py`. Three LLM personas independently tier each labelled candidate. Flags rows where agents agree strongly but disagree with the user's label by 2+ tiers |

### Deliberately not borrowed

- **Survival analysis** for notice periods. The piecewise curve works; survival framing adds no real signal.
- **Bradley-Terry-Luce** for pairwise. About the same as our hand-coded tiebreakers in practice.
- **Network/PageRank** for company influence. Interesting product narrative; no ranking impact.
- **Causal DAGs** for probe disentanglement. Academically nice, no ROI at this scale.
- **Active learning** for label efficiency. Production HITL feature, not for hackathon.

### What's blocked on labels

The single highest-impact remaining math addition is **LightGBM-Rank actually fitted** against the labelled eval set. The scaffolding ships now; the fit waits for the user's 290 labels. Once those land, we replace the hand-tuned `weights.must_have`/`weights.substance` in the JD config with the learned weights and ship submission #2 with a measurable NDCG@10 lift.

---

## 22. Stage-5 interview narrative (90-second version)

> *"We rejected the conventional architecture, embed everything, cosine similarity, cross-encoder rerank, because the dataset was explicitly designed to defeat it. The JD itself flagged keyword-stuffers, plain-language tier-5s, and behavioural twins.*
>
> *Instead, we treated the JD as the algorithm. Every JD requirement maps to a probe over the candidate schema, and the whole JD lives in a single YAML file under jds/. To rank against a different role, edit the YAML; no code changes. Each probe is tagged High-SNR, Medium-SNR, Low-SNR, or Anti-SNR, and we weight by class. Tested, verified, or unfakeable signals dominate; self-asserted claims are downweighted.*
>
> *Honeypots are gated out by six deterministic structural-impossibility rules. Behavioural availability is a multiplicative modifier, a perfect-paper candidate who hasn't logged in for six months gets multiplied down toward zero.*
>
> *Trust is communicated to the recruiter through four signals: a confidence label derived from how many strong probes fired, a horizontal stacked bar that decomposes the rank into must-haves vs substance vs retrieval vs location, percentile rankings against the whole pool, and a Mahalanobis outlier distance that complements the deterministic honeypot rules.*
>
> *The top 20 goes through a portfolio-diversity pass that spreads candidates across companies and locations without bumping strong picks. Two candidates from the same company in the top 10 stops being useful at rank 6.*
>
> *The reasoning column is composed directly from the top contributing probes per candidate, no LLM at runtime, so it can't hallucinate by construction.*
>
> *We added pairwise refinement on the top 20, because NDCG@10 is fundamentally a pairwise problem on the top 10, that's where 50% of the composite score lives. Bayesian confidence reframes the heuristic buckets as a proper posterior P(tier-5 | evidence).*
>
> *The whole architecture is online-updatable: each probe weight is independently SGD-updatable. We didn't have hiring-decision data, so we tuned against a hand-labelled 300-candidate eval set. In production, every recruiter override would be one gradient step. No retraining.*
>
> *We didn't pick the architecture that fits a familiar pipeline. We picked the architecture that defeats the trap."*

---

## End

Plan locked. Eval-set sampler is next; folder created at `C:\Users\shmishra\Documents\Matrix\redrob-ranker\`.
