# What's left for you to do

Almost everything is built. These four items genuinely need your hands or your account; I cannot do them on your behalf.

---

## 1. Label the eval set — required for metric-driven weight tuning

This is the only step that needs *recruiter judgment* against the JD. I can't substitute for you here.

```bash
# Open these side-by-side in VS Code:
#   eval/candidates_to_label.md  (Ctrl+Shift+V for preview)
#   eval/labels.csv

# ~30s per card. 290 cards = ~3 hours of focused work.
# Fill in:
#   tier              0-5
#   is_honeypot       TRUE/FALSE
#   trap_class        clean | keyword_stuffer | consulting_only | ...
#   primary_strength  one-line free text (required for tier ≥ 3)

# When done:
python -m eval.merge_labels

# Then I (or you) can run weight tuning against actual NDCG@10:
python -m eval.score --submission submissions/team_v2.csv
```

Touchstone: *"If I had this candidate and only this JD, would I forward them to the hiring manager?"* → tier 4+. *"Worth a call but not necessarily forward?"* → tier 3.

Calibration: tier-5 should stay rare (~10-20 out of 300). If you label >30 as tier-5, recalibrate against JD stinginess.

---

## 2. Fill in `submission_metadata.yaml` — needs your team identity

Edit these fields:
```yaml
team_name: "..."
primary_contact:
  name: "..."
  email: "..."
  phone: "..."
team_members: [...]
github_repo: "..."   # once you push to GitHub
sandbox_link: "..."  # once you deploy to HuggingFace
```

I left placeholders. Otherwise these are personal/team details I don't have.

---

## 3. Push to GitHub (public repo) and deploy sandbox

```bash
gh repo create redrob-ranker --public --source=. --remote=origin
git push -u origin main
```

For the sandbox (HuggingFace Space):
1. Sign in to https://huggingface.co.
2. Create new Space → Docker template.
3. Connect the GitHub repo, or push the repo there directly.
4. The Dockerfile in `sandbox/Dockerfile` is HF-compatible.

These need your accounts — I can't act as you.

---

## 4. Submit to the hackathon portal

Last submission counts. You can submit `submissions/team_v2.csv` (current best) today as a valid floor while you iterate on weights with labels.

```bash
# Sanity-check before upload:
python "C:/Users/shmishra/Documents/Matrix/[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/validate_submission.py" submissions/team_v2.csv
```

Filename must be `<your_team_id>.csv`. Rename before upload.

---

## What I'll keep doing in the background

- Iterate weights as you give me feedback on what looks off in the deck.
- Add features you want.
- Re-rank and re-audit on every change.
- Compare submissions to see what each change actually did.

Just tell me what to do.
