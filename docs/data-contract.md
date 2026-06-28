# Data contract

The system reads candidates from a `candidates.jsonl` file. This document describes the exact shape of each record and what each field is used for. The Python validation lives in `src/schema.py` (Pydantic); this file is the human-readable counterpart.

The contract is **lenient on input** (real data has nulls, missing fields, inconsistencies) and **strict on output** (the submission CSV cannot be malformed by construction). If your data deviates from this contract, the loader will surface the row that broke.

## Top-level shape

Each line of `candidates.jsonl` is one JSON object with these top-level keys:

| Field | Type | Required | Notes |
|---|---|---|---|
| `candidate_id` | string | yes | Must match pattern `^CAND_[0-9]{7}$` |
| `profile` | object | yes | Identity, current role, summary |
| `career_history` | array of objects | yes | At least one role, in reverse-chronological order |
| `education` | array of objects | no | Empty list allowed |
| `skills` | array of objects | no | Empty list allowed |
| `certifications` | array of objects | no | Empty list allowed |
| `languages` | array of objects | no | Empty list allowed |
| `redrob_signals` | object | yes | Platform behavioural signals; see below |

## `profile`

| Field | Type | Notes |
|---|---|---|
| `anonymized_name` | string | Display name |
| `headline` | string | One-line role description |
| `summary` | string | Multi-sentence "about me". Used by substance + retrieval probes |
| `location` | string | "City, Region" or "City" |
| `country` | string | Country name |
| `years_of_experience` | number | Self-reported total. Sanity-checked against career_history |
| `current_title` | string | Used for title-relevance regex matching |
| `current_company` | string | Looked up against the JD's product/consulting/named-employer lists |
| `current_company_size` | string | One of `1-10`, `11-50`, `51-200`, `201-500`, `501-1000`, `1001-5000`, `5001-10000`, `10001+` |
| `current_industry` | string | Free-form |

## `career_history[*]`

Each role:

| Field | Type | Notes |
|---|---|---|
| `company` | string | Same lookup as profile.current_company |
| `title` | string | Probed by relevant-titles regex from the JD config |
| `start_date` | string `YYYY-MM-DD` or null | If null, role start unknown |
| `end_date` | string or null | Null means "current" (unless `is_current` says otherwise) |
| `duration_months` | int | Used by honeypot rules: any single role > YoE + 12 months is impossible |
| `is_current` | bool | One role should have this set true |
| `industry` | string | Free-form |
| `company_size` | string | Same enum as profile |
| `description` | string | The substance probes mine this. Specific tools named here count for trust; bare verbs do not |

## `education[*]`

| Field | Type | Notes |
|---|---|---|
| `institution` | string | |
| `degree` | string | |
| `field_of_study` | string | |
| `start_year` | int | |
| `end_year` | int | |
| `grade` | string or null | GPA / percentage / class |
| `tier` | string | One of `tier_1`, `tier_2`, `tier_3`, `tier_4`, `unknown`. **Weighted at zero by default** — pedigree neutrality is a deliberate design choice |

## `skills[*]`

| Field | Type | Notes |
|---|---|---|
| `name` | string | Matched against the JD config's must-have vocabularies |
| `proficiency` | string | `beginner` / `intermediate` / `advanced` / `expert` |
| `endorsements` | int | Trust modifier — bare claims with 0 endorsements are downweighted |
| `duration_months` | int | Trust modifier — claims with 0 months are downweighted, 3+ expert skills at 0 months trigger the honeypot rule |

## `certifications[*]`

| Field | Type | Notes |
|---|---|---|
| `name` | string | Matched against known cloud / ML certs |
| `issuer` | string | |
| `year` | int | |

## `redrob_signals`

The 23 platform signals. All are technically optional in the JSONL but the schema provides safe defaults if missing.

| Field | Type | Range | Used by |
|---|---|---|---|
| `profile_completeness_score` | number | 0–100 | Not currently used |
| `signup_date` | string | YYYY-MM-DD | Not currently used |
| `last_active_date` | string | YYYY-MM-DD | `effectively_available` probe — exponential decay with 60-day half-life |
| `open_to_work_flag` | bool | — | `effectively_available` |
| `profile_views_received_30d` | int | ≥0 | `engagement_quality` |
| `applications_submitted_30d` | int | ≥0 | `effectively_available` — actively-searching boost |
| `recruiter_response_rate` | number | 0–1 | `effectively_available` |
| `avg_response_time_hours` | number | ≥0 | `effectively_available` — response-speed multiplier |
| `skill_assessment_scores` | dict[str, 0–100] | — | `verification_ratio` probe + `python_proficiency` |
| `connection_count` | int | ≥0 | Not currently used |
| `endorsements_received` | int | ≥0 | Per-skill endorsements used instead |
| `notice_period_days` | int | 0–180 | `notice_period_curve` |
| `expected_salary_range_inr_lpa` | {min, max} | both ≥0 | Honeypot rule for impossible ranges (currently disabled — synthesized dataset artefact) |
| `preferred_work_mode` | string | `onsite` / `hybrid` / `remote` / `flexible` | `remote_only_vs_hybrid_jd` anti-SNR |
| `willing_to_relocate` | bool | — | `location_match` |
| `github_activity_score` | number | -1 to 100, -1 = no GitHub | `engagement_quality` |
| `search_appearance_30d` | int | ≥0 | Not currently used |
| `saved_by_recruiters_30d` | int | ≥0 | `engagement_quality` |
| `interview_completion_rate` | number | 0–1 | `engagement_quality` |
| `offer_acceptance_rate` | number | -1 to 1, -1 = no history | `closability` probe |
| `verified_email` | bool | — | `trust_modifier` |
| `verified_phone` | bool | — | `trust_modifier` |
| `linkedin_connected` | bool | — | `trust_modifier` |

## Output contract

The submission CSV format is fixed by the hackathon spec and not negotiable:

```
candidate_id,rank,score,reasoning
CAND_0081846,1,1.199136,"Strong fit: Lead AI Engineer (6.7y) at Razorpay..."
```

Rules enforced by `src/schema.py`:

- `candidate_id`: matches `^CAND_[0-9]{7}$`
- `rank`: integer, 1 ≤ rank ≤ 100, exactly once each
- `score`: float, monotonically non-increasing with rank
- `reasoning`: string, max 1000 chars, no LLM-generated content (templated from probes only)

A `<submission>.structured.jsonl` sidecar carries the rich evidence:

```json
{
  "candidate_id": "CAND_0081846",
  "rank": 1,
  "score": 1.199,
  "confidence": "high",
  "confidence_bayes": {"bucket": "high", "posterior_tier5": 0.8421},
  "breakdown": {"must_have": 0.62, "substance": 0.21, "retrieval": 0.10, "location": 0.07},
  "next_action": "Send the technical screen this week. Fast-track candidate.",
  "main_risk": "",
  "calibration": {
    "must_have_percentile": 99.2, "substance_percentile": 97.8,
    "score_percentile": 99.5, "mahalanobis": 3.4,
    "rank_ci_95": [1, 2]
  },
  "reasoning": "...",
  "must_have": [{"name": "...", "score": 0.95, "evidence": "..."}, ...],
  "substance": [...],
  "behavioural": [...],
  "anti_snr": [...],
  "behavioural_modifier": 0.96,
  "anti_snr_penalty": 1.0
}
```

And two more sidecars per run:

- `<submission>.discarded.jsonl` — every honeypot quarantined + the 50 heaviest anti-SNR offenders, with the rule(s) that fired. For transparency.
- `<submission>.cooling.jsonl` — the 30 strongest profiles whose behavioural availability is low. "Great fit, wrong timing — revisit later."

## Validation

```bash
# Official hackathon validator
python "<bundle>/validate_submission.py" submissions/<your>.csv

# Local audit: every reasoning string verified against the candidate's actual profile
python -m audit.reasoning_audit \
  --candidates ./candidates.jsonl \
  --submission submissions/<your>.csv
```

Both should pass cleanly. The audit catches any drift in the templated reasoning generator.
