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

We tag each check by how easy it is to fake:

- **High trust**: things you can't really bluff. Verified skill assessment scores. Specific tool names in your role descriptions. Activity on the platform.
- **Low trust**: things anyone can claim. A bare skill name with zero endorsements. Generic action verbs. Years of experience without context.

High-trust signals get more weight. Low-trust signals get less. This is what makes it hard for a candidate who just stuffed their profile with AI buzzwords to outrank someone who actually built real systems.

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
├── src/
│   ├── schema.py                 candidate / submission data shapes
│   ├── load.py                   reads candidates.jsonl one at a time
│   ├── honeypot.py               the six honeypot checks
│   ├── heuristics.py             helper regexes, company lookups
│   ├── scoring.py                puts all the checks together into one score
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
└── submissions/                  the actual CSV we'd submit
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
