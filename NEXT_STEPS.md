# What's left for you to do

Almost everything is built. These four things genuinely need your hands or your accounts. I cannot do them on your behalf.

---

## 1. Label the eval set

This is the only step that needs recruiter-style judgment against the JD. It is also the highest-impact thing left, because:

- It is the only way we can actually *measure* whether a weight change improved our NDCG@10.
- Without it, every probe-weight tuning is guesswork.
- With it, we can also wire in LightGBM-Rank (proper learning-to-rank against your labels), which is the single biggest possible accuracy lift.

The whole process is a one-time thing. Once labelled, the file gets reused for every iteration.

### What you'll be doing in plain English

You are going to look at 290 candidate profiles, one at a time, and for each one decide: *if this were a real candidate in my inbox for this Senior AI Engineer role at Redrob, where would I put them?*

You assign each candidate to one of six tiers (0 through 5). You also tag what kind of candidate they are (clean fit, a keyword-stuffer trap, a consulting-only person, etc.). You write a one-line note about what their main strength is. That's it.

### How long it will take

- Fast cards (clearly tier-5 or clearly tier-0 / honeypots): ~15 seconds each.
- Mid cards (have to read the description carefully): ~60 seconds each.
- Borderline cards (could be tier-3 or tier-4): ~90 seconds.

Average across all 290 cards: about **3 to 4 hours of focused work**. You can do it in one sitting or split across two sessions. Don't try to spread it over days because the calibration drifts (you'll over-tier in some sessions and under-tier in others).

### The file layout

Two files in `eval/`:

- **`candidates_to_label.md`** is the candidate profiles, one card per candidate, in a scannable Markdown format. Open this in VS Code and hit **Ctrl+Shift+V** to get the rendered preview. Scroll through it on the right side of your screen.
- **`labels.csv`** is where you put your answers. Open it in any spreadsheet (Excel, Google Sheets, VS Code's CSV viewer). The columns are pre-filled with candidate IDs in the same order as the cards.

Put the two windows side by side. As you scroll a card, fill in its row.

### How to read a card

Each card has the candidate's name, current role, summary, career history (with descriptions), top skills, education, behavioural signals, and any pre-fired structural flags (e.g. `consulting_only_career`, `date_inversion`).

The information that actually matters for the JD, in order:

1. **Career history**: do their recent roles look like real production ML / IR / retrieval work? Are their descriptions specific (named tools, named systems) or vague?
2. **Current role**: is it a JD-relevant title at a JD-relevant company? "AI Engineer at Razorpay" is the obvious yes. "Marketing Manager at Wipro" is the obvious no.
3. **Skills**: how many are JD-relevant? Do they have assessment scores (the dataset has `skill_assessment_scores` which means tested)?
4. **Behavioural signals**: open to work, recent activity, response rate, notice period.
5. **Pre-fired flags**: if the card warns of `consulting_only_career` or `date_inversion`, take that seriously.

### What each tier means

Read this once carefully. Then refer back as needed.

#### Tier 5 — Ideal candidate

This is someone you would put in your top 10 in a heartbeat. They check the JD's must-haves clearly and visibly. Examples of what tier-5 looks like for this JD:

- Senior AI Engineer or Lead ML Engineer at a real product company (Razorpay, Stripe, Meta, Zomato, etc.).
- 5-9 years experience, with at least 3 years on production retrieval / ranking / embeddings work.
- Career history descriptions name specific systems: BGE, FAISS, sentence-transformers, NDCG, MRR, vector DBs, etc.
- Verified Python assessment score, GitHub activity, recently active on the platform.
- Often based in Pune/Noida/Bangalore or willing to relocate.

**Tier-5 should be rare.** The JD says they want "10 great matches in 100K". In your 290-candidate sample, expect to find **5 to 15 tier-5 candidates** at most. If you're labelling 30+ as tier-5, you're being too generous.

#### Tier 4 — Strong fit

Forward-to-hiring-manager material, but with one notable gap or concern.

- Strong ML/IR background but slightly off the experience band (e.g. 4 years or 11 years).
- Strong work history but at a less-recognised company.
- All the must-haves, but a 120-day notice period.
- Excellent description substance but not currently active on the platform.

Expect ~15-30 tier-4s in 290 cards.

#### Tier 3 — Adjacent fit

Worth a screen call but you'd want to verify a lot. Not someone you'd forward without a screen.

- Data Engineer or Backend Engineer with significant ML adjacent work, not core ML.
- Mid-level ML engineer (3-4 years), interesting but probably too junior for "Senior".
- Strong skills but career mostly outside the JD's domain (e.g. heavy CV/speech with some NLP exposure).
- Solid Indian product company experience but the ML side is shallow.

Expect ~30-60 tier-3s.

#### Tier 2 — Weak fit

You probably wouldn't move forward, but you can see why someone might. Adjacent skills, some signal, but the gaps are real.

- Skills overlap with JD but career is mostly non-ML (e.g. backend engineer who took an ML course).
- Junior or fresher with a strong project portfolio but no production experience.
- Mid-level engineer at consulting firms who has done some ML at one of them.

Expect ~50-100 tier-2s.

#### Tier 1 — Clear no

Wrong field, wrong level, wrong everything. You'd reject after reading the title.

- Marketing Managers, Operations Managers, Civil Engineers, Mechanical Engineers, HR people who happen to claim AI skills.
- Pure backend devs with zero ML signal anywhere in career history.
- Career entirely at services consulting firms.

Most of the random_control bucket will fall here. Expect ~60-100 tier-1s.

#### Tier 0 — Honeypot

A profile that's structurally impossible or fake. The dataset includes some seeded honeypots that the JD warns about. Patterns:

- Career dates that don't add up (e.g. 8 years claimed but career history sums to 25 years).
- "Expert" at 5+ skills with 0 months experience in each.
- Started at a known company *before* that company was founded.
- A single role that exceeds the candidate's total claimed years of experience.

Tier-0 should align with `is_honeypot = TRUE` in your CSV row.

Expect ~30-40 tier-0s (your `honeypot_suspect` bucket has 40 candidates, most of those should be tier-0).

### What the trap_class options mean

After the tier, you tag one of these:

- **clean** — a normal candidate. Use this for most tier-2 through tier-5 candidates.
- **keyword_stuffer** — a candidate whose profile has lots of JD-relevant keywords as skills but whose career history is in an unrelated role (e.g. Marketing Manager who lists "RAG, Pinecone, Embeddings" as skills). The classic trap the JD warned about.
- **consulting_only** — entire career at one or more consulting firms (TCS, Infosys, Wipro, etc.).
- **bigcorp_only** — entire career at 10000+ employee companies (Google, Meta, Amazon, etc.).
- **plain_language_tier5** — the inverse of keyword-stuffer. Profile looks unassuming, doesn't use the JD's buzzwords, but career history shows real production ML/IR work. The JD specifically asked us to find these.
- **cv_speech_robo_only** — candidate is a CV/speech/robotics specialist with no NLP/IR exposure. The JD's explicit "we will not move forward on this" category.
- **title_chaser** — three or more roles in a row, each less than 18 months. Job-hopper.
- **other** — anything else worth flagging.

### Writing the primary_strength

For any candidate you tier as 3 or higher, write a one-line note (3-12 words) about what their main strength is. Examples:

- "Production retrieval at Stripe Search team for 3 years."
- "Strong NLP background but currently at Adobe rather than a startup."
- "Solid ML at Zomato, would interview but notice 90 days."
- "Recommendation systems at Nykaa, plus strong open-source GitHub."

This serves two purposes: it forces you to verbalise *why* you tiered them where you did (catches your own mistakes), and it doubles as a regression test for our reasoning generator (we can check our generated reasoning against your hand-written one).

### What to do when you're uncertain

You will be uncertain on maybe 30 of the 290 cards. Some tactics:

- **Read the description text of their two most recent roles in full.** That's where the truth lives. Skills lists can lie.
- **Default to the lower tier** when you're truly torn between two adjacent tiers. NDCG penalises over-promotion of weak candidates more than under-promotion of strong ones.
- **If the card has multiple pre-fired flags**, take that seriously even if the profile looks good. Two flags is usually two real problems.
- **If you can't decide**, write a note in the `notes` column and move on. You can revisit your `notes` rows at the end and recalibrate together.

### Workflow, concretely

```bash
# 1. Open the two files side by side in VS Code:
#    eval/candidates_to_label.md   (Ctrl+Shift+V to render)
#    eval/labels.csv
#
# 2. For each card (~30s on average):
#    Read the card. Look at career history, current role, skills, signals.
#    In labels.csv, fill in the row:
#      tier              0-5 integer
#      is_honeypot       TRUE or FALSE
#      trap_class        clean / keyword_stuffer / consulting_only / etc.
#      primary_strength  (required for tier >= 3, one short line)
#      primary_concern   (optional, what worries you about this candidate)
#      notes             (optional, anything that doesn't fit above)
#
# 3. When you're done with all 290:
python -m eval.merge_labels
#    This validates your CSV and produces eval/labelled.jsonl
#    If validation fails, it tells you which row.
#
# 4. Score the current submission against your labels:
python -m eval.score --submission submissions/team_v3.csv
#    Prints NDCG@10, NDCG@50, MAP, P@10, ERR@10, composite, honeypot rate.
#    This is your baseline. Every weight change after this gets measured
#    against these numbers.
```

### Calibration check (do this after every 100 cards)

The eval set is only useful if your tiering is consistent. Sanity checks:

- After 100 cards, count how many you've marked tier-5. If it's more than 10, you're being too generous, recalibrate downward.
- After 100 cards, count how many tier-0s. If you're under 10, you might be missing honeypots, recheck the structural-flag warnings.
- The `bucket × tier` crosstab in `eval/sampling_report.md` will tell us how well our heuristic buckets predicted your tiers, which is a calibration signal for the whole system.

---

## 2. Fill in your team identity

Open `submission_metadata.yaml` and replace the TODOs:

```yaml
team_name: "..."
primary_contact:
  name: "..."
  email: "..."
  phone: "..."
team_members:
  - name: "..."
    email: "..."
    role: "..."
github_repo: "https://github.com/saurabh4269/matrix"   # already set
sandbox_link: "..."                                     # once you deploy to HF Space
```

The github_repo is already set to the right URL. The sandbox_link goes in once you deploy.

---

## 3. Deploy the sandbox to HuggingFace Spaces

```bash
# 1. Sign in to https://huggingface.co
# 2. Create a new Space:
#    - Owner: your username
#    - Space name: matrix-ranker (or whatever)
#    - License: MIT
#    - Space SDK: Docker
# 3. The Space will give you a git URL. Push to it:
git remote add hf https://huggingface.co/spaces/<your-username>/matrix-ranker
git push hf main
# 4. HF auto-detects the sandbox/Dockerfile and builds the Space.
# 5. Wait ~5 minutes for the build. The Space URL is your sandbox_link.
```

---

## 4. Submit to the hackathon portal

```bash
# Sanity check first:
python "C:/Users/shmishra/Documents/Matrix/[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/validate_submission.py" submissions/team_v3.csv

# Then rename to your team_id:
cp submissions/team_v3.csv submissions/<your_team_id>.csv

# Upload that file via the portal.
```

Spec rules: 3 submissions max, last valid one counts. Submit `team_v3.csv` first as a safe floor, then iterate with labels and submit again later.

---

## What I'll keep doing in the background

When you give me labels (or any feedback on the deck), I will:

- Wire LightGBM-Rank against your labels and tune the weights against actual NDCG@10.
- Re-run rank.py and diff against the previous submission to show what changed.
- Audit reasoning for hallucinations on every re-run.
- Add new features as you ask for them.

Just tell me what to do next.
