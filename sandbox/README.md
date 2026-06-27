# Sandbox — Redrob Ranker

A hosted environment where organisers can run the ranker end-to-end on a small candidate sample. Designed for the 6-act journey described in `final_plan.md §15`.

## What it shows

1. **Act 1 — JD Digest.** The JD reflected back as a 4–6 line summary.
2. **Act 2 — The deck.** One candidate at a time, full viewport. Press Enter to interview, → to skip.
3. **Whispered hints + concern callouts.** Inline italic lines that surface plain-language tier-5s and honest concerns.
4. **Act 4 — Pause.** A breath every 7 candidates if the shortlist is growing.
5. **Act 5 — Shortlist review.** Drag-reorder the people you kept.
6. **Act 6 — Reflection.** Closing line that names what the user valued.

## Local development

```bash
# Backend
cd sandbox/backend
pip install -r requirements.txt
cd ../..
uvicorn sandbox.backend.main:app --reload --port 8000

# Frontend (separate terminal)
cd sandbox/frontend
npm install
npm run dev
# open http://localhost:5173
```

Vite dev server proxies `/api` calls to `http://localhost:8000` (see `vite.config.ts`).

## Production build (single container)

```bash
cd <repo root>
docker build -f sandbox/Dockerfile -t redrob-sandbox .
docker run -p 7860:7860 redrob-sandbox
# open http://localhost:7860
```

## HuggingFace Space deployment

This Dockerfile is HF-Space compatible. To deploy:

1. Create a new HF Space, type = Docker.
2. Push this repository to that Space's git remote.
3. HF auto-detects the Dockerfile and builds.

The Space serves on port 7860 by default.

## Pre-loaded sample

`backend/sample_candidates.json` contains 25 curated candidates:
- 12 from the top of our 100K-candidate ranking (real tier-5s)
- 5 additional likely tier-5 candidates (the "easy to overlook" ones — surface the whispered hint)
- 6 keyword-stuffers (demonstrate that the system demotes them)
- 2 honeypots (demonstrate the quarantine — they never appear in the deck)

Rebuild this set with `python sandbox/backend/build_sample.py`.

## API

`GET /api/jd` — returns the JD digest as JSON.
`GET /api/demo` — runs the ranker on the pre-loaded sample, returns the full ranked payload.
`POST /api/rank` — runs the ranker on a candidates list passed in the body (≤100 candidates).

See `lib/api.ts` for the response shape.
