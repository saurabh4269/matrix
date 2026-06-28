# matrix

A candidate ranker built for the Redrob *Intelligent Candidate Discovery & Ranking* hackathon.

You give it a list of 100,000 candidate profiles and one job description. It gives you back the 100 best fits, in order, with a short note for each one explaining why it ranked them where it did.

The job we ranked against in this submission is a Senior AI Engineer role at Redrob, hybrid in Pune or Noida, 5 to 9 years of experience.

## How to run it

```bash
pip install -r requirements.txt

python rank.py --candidates ./candidates.jsonl --out ./submission.csv
```

That's it. One command. It runs in about 3 minutes 40 seconds on a normal laptop, uses around 2 GB of RAM, needs no internet connection, no GPU. The CSV passes the official `validate_submission.py` cleanly.

## The idea behind it

Most candidate rankers in this hackathon will probably embed everything into vectors, do a cosine similarity against the JD, and call it a day. We didn't want to do that because the dataset has traps that are designed to break exactly that approach.

So we did something different. We read the JD line by line and turned each line into a small check we can run against any candidate. Things like:

- Does their work history mention production deployment of an embedding system?
- Does their description say "shipped" and "deployed" or just "researched" and "explored"?
- Did they actually pass a Python assessment, or are they just claiming Python on their profile?
- Is their entire career at consulting firms? The JD says that's a hard no.
- Are they reachable? Open to work, recent activity, decent response rate?

Each check is a small Python function. Each one gives a candidate a score from 0 to 1 plus a short sentence explaining what it found. The final rank is the weighted sum of all those checks, multiplied by how reachable they are.

Every JD-specific thing (vocabularies, weights, company lists, location preferences, the JD text itself) lives in a single YAML file under `jds/`. The Python code reads from it. To rank against a different role, edit the YAML. No code changes.

We tag each check by how easy it is to fake:

- **High trust**: things you can't really bluff. Verified skill assessment scores. Specific tool names in your role descriptions. Activity on the platform.
- **Low trust**: things anyone can claim. A bare skill name with zero endorsements. Generic action verbs. Years of experience without context.

High-trust signals get more weight. Low-trust signals get less. This is what makes it hard for a candidate who just stuffed their profile with AI buzzwords to outrank someone who actually built real systems.

## How we communicate the score to a recruiter

The numeric score by itself doesn't mean much to someone who has to decide. So every ranked candidate carries four pieces of trust metadata alongside their rank:

- **A confidence label**: high, medium, or low. Derived from how many strong probes fired, not from the score itself. A candidate who clears the must-haves comfortably gets a high-confidence pill; someone who scrapes by on a few signals gets medium.
- **A score breakdown**: a horizontal stacked bar that shows what fraction of the score came from must-haves, substance, retrieval, and location. A recruiter can see whether this person's rank is held up by skills, by description substance, or by location fit.
- **Pool calibration**: percentiles for the candidate's must-have, substance, and overall scores against the whole 100,000-candidate pool. "97th percentile in substance" tells you a lot more than "0.8 substance score."
- **Mahalanobis distance**: a statistical outlier measure that flags candidates whose probe vector is unusually far from the pool's centre. Catches profiles that pass the deterministic honeypot rules but still look statistically odd.

## Diversity in the shortlist

When the top 10 is dominated by a single company (we saw this in early runs: 4 candidates from Razorpay in a row), it stops being useful. Even if the linear scorer thinks they're all the best, a recruiter can't talk to 4 people from the same place.

So after the pairwise refinement, we do a small portfolio-style diversity pass on the top 20. It gently spreads the order across companies and locations without bumping strong candidates out of the top 10. Borrows the idea from portfolio theory: a diverse shortlist beats a concentrated one even when the concentrated one has a higher average score.

## Math we borrowed from other fields

Where ideas came from. Each one earns its place by either improving the ranking, increasing trust, or proving correctness.

| What | Where it's from | What it does for us |
|---|---|---|
| **Z-score standardisation** | Quantitative finance | Gives the recruiter pool-relative percentiles. "97th percentile in substance" beats "0.8 substance score" for any human reader |
| **Mahalanobis outlier distance** | Anomaly detection | Statistical outlier complement to our deterministic honeypot rules. Flags candidates whose probe vector is unusually far from the centre |
| **Bayesian posterior** for confidence | Bayesian statistics | Naive-Bayes posterior `P(tier-5 \| evidence)` reframes the heuristic confidence buckets as a proper probability |
| **Portfolio diversity (MMR)** | Portfolio theory | The reason our top-10 has 9 unique companies instead of 4 Razorpay candidates back-to-back |
| **Expected Reciprocal Rank (ERR)** | Information retrieval | A second eval metric that models the recruiter as stopping after the first satisfying hit (closer to actual recruiter behaviour than NDCG) |
| **Shannon entropy** of skill claims | Information theory | Catches AI-tailored resumes whose skill distribution is suspiciously uniform. Real engineers have messy claim distributions |
| **Conformal-style rank intervals** | Conformal prediction | "Sarah is rank 1, stable in 1-3" instead of just "rank 1". 50 score-perturbations per candidate, 95% rank CI |
| **Pairwise NDCG@10 optimisation** | Learning-to-rank | NDCG@10 is intrinsically a pairwise problem on the top 10; our pairwise refinement targets exactly that |

What we **didn't** borrow and why:
- Survival analysis (for notice periods): overkill, the piecewise curve works
- Bradley-Terry-Luce (for pairwise): about the same as hand-coded tiebreakers in practice
- LightGBM-Rank weight learning: the highest-impact possible math addition, but it needs labelled training data we don't have yet. Once the eval set is labelled, this slots in directly

## The honeypot defence

The dataset has about 80 impossible profiles seeded into it. Things like "8 years at a company founded 3 years ago" or "expert at 10 skills with 0 months experience in each". If your top 100 has more than 10 of these, you get disqualified.

We catch them with six small structural checks:

1. Career dates that go backwards (end date before start date).
2. Total career duration that's way more than the candidate's claimed years.
3. A single role longer than their entire stated experience.
4. Three or more "expert" skills with zero months of experience each.
5. Tenure at a company that started before that company existed.
6. Assessment scores for skills the candidate never claimed.

Any candidate that trips one of these is dropped from the running, no exceptions. Our last run quarantined 222 candidates out of 100,000. Zero of them ended up in our top 100.

## The reasoning column

For each of the top 100 we have to write a short note explaining the rank. We don't use an LLM for this because LLMs can hallucinate facts that aren't in the candidate's profile, and that gets you penalised in the manual review.

Instead, each note is templated from the actual probes that scored highest for that candidate. Six different sentence shapes per rank band, picked deterministically from the candidate's ID, so the same candidate always gets the same note but different candidates get different phrasings. Every claim in the note is something we can point to in the profile.

We also ran the entire top 100 through a sanity check that compares every claim in the note against the candidate's actual record. Zero hallucinations.

## What's in the repo

```
matrix/
├── rank.py                       single command, makes the submission CSV
├── jds/
│   └── ai_engineer.yaml          the active JD as a config file
├── src/
│   ├── jd_config.py              loads jds/*.yaml; everything JD-specific reads from here
│   ├── schema.py                 candidate / submission data shapes
│   ├── load.py                   reads candidates.jsonl one at a time
│   ├── honeypot.py               the six honeypot checks
│   ├── heuristics.py             helper regexes, company lookups (driven by JD config)
│   ├── scoring.py                puts all the checks together into one score
│   ├── calibration.py            pool z-scores, Mahalanobis, Bayesian confidence, diversity
│   ├── pairwise.py               re-orders the top 20 with finer rules
│   ├── reasoning.py              writes the short note for each rank
│   ├── precompute.py             builds the BM25 index (run this once)
│   └── probes/
│       ├── must_have.py          checks for things the JD says we need
│       ├── substance.py          checks for real work behind the claims
│       ├── behavioural.py        availability, trust, responsiveness
│       ├── anti_snr.py           red flags the JD lists explicitly
│       ├── location.py           where they are, years of experience
│       └── retrieval.py          BM25 score, optional dense embedding score
├── eval/                         tools for labelling 300 candidates by hand
├── audit/                        the hallucination check
├── tests/                        29 tests, all passing
├── sandbox/                      a small web UI so you can browse the ranking
├── data/                         precomputed BM25 scores
├── final_plan.md                 the full design doc
├── NEXT_STEPS.md                 what's left to do
└── submissions/                  the actual CSV we'd submit + structured + discarded + cooling sidecars
```

## The sandbox

There's a small web app in `sandbox/`. You can run it locally with:

```bash
cd sandbox/frontend && npm install && npm run build && cd ../..
python -m uvicorn sandbox.backend.main:app --host 127.0.0.1 --port 8765
```

Then open `http://127.0.0.1:8765`. It walks you through the top 20 candidates one at a time, the way you'd actually use the tool if you were a recruiter. There's a key for each action: Enter to shortlist someone, right arrow to skip, P to see their full profile.

The whole thing is one Docker container, set up to deploy directly to HuggingFace Spaces.

## What's still on me to do

See `NEXT_STEPS.md`. The short version: label 290 candidates by hand to actually measure how well the ranker works, fill in my team identity in `submission_metadata.yaml`, push the sandbox to HuggingFace, and submit the CSV to the portal.

## Things this submission could do better

A few honest limitations:

- We have a sentence-transformer embedding channel wired up but the precompute didn't finish on this machine. BM25 is doing the retrieval work for now. On a faster machine the embedding step would add a second signal.
- We tested against our own hand-labelled set, not the actual hidden ground truth. There's some risk we tuned the system to our own biases.
- The vocabularies in the probes are tuned for this specific JD. Pointing the system at a different role means rewriting those vocabularies.

## License

MIT for the code. The dataset itself belongs to Redrob.
