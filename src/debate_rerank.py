"""Multi-agent debate reranker for the top window.

vision.md §3 "Multi-Agent Forensic Reranker" made real, but run OFFLINE
(pre-submission) so we don't blow the 5min/CPU/no-net runtime constraint.

Three personas — Hard Technical Cynic, Growth & Trajectory Scout,
Contextual Matchmaker — vote pairwise over the top N (default 12).
We aggregate via Copeland scoring (count of pair-wins under
majority-of-personas) and blend the resulting normalized score with the
original linear score:

    final_score = (1 - alpha) * original + alpha * copeland_normalized

This preserves the linear ranker's signal for borderline cases while
letting the agents' consensus reorder genuinely close pairs.

Network IS allowed here because rank.py runs this only when the
--debate-rerank flag is set, which we only set at submission time (not
during the locked 5min eval).
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from typing import Callable

from src.schema import Candidate
from src.scoring import CandidateScore


# Shared persona prompts with the judge harness (eval/judge.py). We keep two
# copies because the judge is a measurement tool and the reranker is an
# operator — they should be independently maintainable.
PERSONAS: dict[str, str] = {
    "technical_cynic": (
        "You are the HARD TECHNICAL CYNIC. You look for deep technical execution, "
        "structural logic in career progression, and rigorous project delivery. "
        "You IGNORE flashy brand names. You favor candidates with high-impact ownership "
        "in obscure or niche technical work over those with shallow exposure at famous companies. "
        "You are highly skeptical of AI-tailored bullet points and generic action verbs."
    ),
    "growth_scout": (
        "You are the GROWTH & TRAJECTORY SCOUT. You analyze adaptability, promotion velocity, "
        "and whether the candidate is currently under-titled or punching above their weight class. "
        "You favor candidates who are clearly outgrowing their current engineering ecosystem and "
        "ready for a massive leap. Pedigree without velocity bores you; velocity without pedigree "
        "excites you."
    ),
    "contextual_matchmaker": (
        "You are the CONTEXTUAL MATCHMAKER. You evaluate the alignment between the candidate's "
        "historical environment and the EXECUTION REALITY of the new role. "
        "You favor candidates whose past company DNA (pace, scale, engineering culture) maps "
        "well onto the target role's operational reality. You validate whether a candidate from "
        "an adjacent field has the transferable foundational logic to dominate the new role."
    ),
}


INSTRUCTION = (
    "You will compare two candidates for the target role. Decide which is the STRONGER fit "
    "FROM YOUR PERSONA's point of view.\n"
    'Output ONLY one JSON object: {"winner": "A" | "B", "reason": "<one short sentence>"}'
)


def _card(cand: Candidate, cs: CandidateScore) -> str:
    """Compact text card under 250 tokens."""
    parts = [
        f"Name: {cand.profile.anonymized_name}",
        f"Title: {cand.profile.current_title} at {cand.profile.current_company}",
        f"YoE: {cand.profile.years_of_experience}",
        f"Location: {cand.profile.location}",
    ]
    # Top 3 must-haves
    top_must = sorted(cs.must_have, key=lambda t: -t[1])[:3]
    if top_must:
        parts.append("Must-haves: " + " | ".join(f"{n}={s:.2f}" for n, s, _ in top_must))
    # Top 2 substance signals
    top_sub = sorted(cs.substance, key=lambda t: -t[1])[:2]
    if top_sub:
        parts.append("Substance: " + " | ".join(f"{n}={s:.2f}" for n, s, _ in top_sub))
    # Worst 2 anti-snr
    worst = sorted(cs.anti_snr, key=lambda t: -t[1])[:2]
    if worst and any(s > 0 for _, s, _ in worst):
        parts.append("Concerns: " + " | ".join(f"{n}={s:.2f}" for n, s, _ in worst if s > 0))
    # Behavioural
    parts.append(
        f"Behavioural modifier: {cs.behavioural_modifier:.2f}"
    )
    return "\n".join(parts)


def _call_persona(client, model: str, persona_prompt: str, jd_text: str,
                  card_a: str, card_b: str) -> str | None:
    """Return 'A' or 'B' or None on error."""
    sys_prompt = f"{persona_prompt}\n\nROLE CONTEXT:\n{jd_text[:1500]}\n\n{INSTRUCTION}"
    user_msg = f"Candidate A:\n{card_a}\n\n---\n\nCandidate B:\n{card_b}"
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=150,
            system=sys_prompt,
            messages=[{"role": "user", "content": user_msg}],
        )
    except Exception as e:
        print(f"  debate LLM error: {e}", file=sys.stderr)
        return None
    raw = "".join(b.text for b in msg.content if hasattr(b, "text")).strip()
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    try:
        d = json.loads(raw)
        w = d.get("winner")
        if w in ("A", "B"):
            return w
    except Exception:
        pass
    return None


def rerank_with_debate(
    scored: list[CandidateScore],
    lookup_candidate: Callable[[str], Candidate],
    *,
    n: int = 12,
    alpha: float = 0.4,
    model: str = "claude-haiku-4-5-20251001",
    jd_text_path: str | None = None,
) -> list[CandidateScore]:
    """Reorder the top-n by Copeland(majority-of-3-personas). Out-of-window
    candidates keep their original order. Returns the new full list."""
    if not scored:
        return scored
    if n <= 1:
        return scored

    try:
        import anthropic  # type: ignore
    except ImportError:
        print("  anthropic SDK not installed — debate rerank skipped.", file=sys.stderr)
        return scored
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("  ANTHROPIC_API_KEY not set — debate rerank skipped.", file=sys.stderr)
        return scored

    # JD text — defaults to data/jd_text.txt
    from pathlib import Path
    if jd_text_path is None:
        jd_text_path = str(Path(__file__).resolve().parent.parent / "data" / "jd_text.txt")
    try:
        jd_text = Path(jd_text_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        # Fallback to the digest from the active JD config
        from src.jd_config import get_config
        d = get_config().digest
        jd_text = f"{d.role}\n{d.location}\n{d.experience}\n{d.style}"

    window = scored[:n]
    tail = scored[n:]

    client = anthropic.Anthropic()
    pair_count = (n * (n - 1)) // 2
    call_budget = pair_count * len(PERSONAS)
    print(f"  debate: {pair_count} pairs × {len(PERSONAS)} personas = {call_budget} calls", file=sys.stderr)

    # Precompute cards
    cards: dict[str, str] = {}
    for cs in window:
        cards[cs.candidate_id] = _card(lookup_candidate(cs.candidate_id), cs)

    wins: dict[str, int] = defaultdict(int)
    persona_wins: dict[str, dict[str, int]] = {p: defaultdict(int) for p in PERSONAS}
    failed = 0
    t0 = time.time()
    call_idx = 0
    for i in range(n):
        for j in range(i + 1, n):
            a, b = window[i].candidate_id, window[j].candidate_id
            votes: dict[str, str] = {}
            for pkey, pprompt in PERSONAS.items():
                call_idx += 1
                w = _call_persona(client, model, pprompt, jd_text, cards[a], cards[b])
                if w is None:
                    failed += 1
                    continue
                winner_id = a if w == "A" else b
                votes[pkey] = winner_id
                persona_wins[pkey][winner_id] += 1
                if call_idx % 30 == 0:
                    print(f"    {call_idx}/{call_budget} ({time.time()-t0:.0f}s)", file=sys.stderr)
            if votes:
                tally = Counter(votes.values())
                majority = tally.most_common(1)[0][0]
                wins[majority] += 1

    elapsed = time.time() - t0
    print(
        f"  debate complete: {call_budget - failed}/{call_budget} calls succeeded "
        f"in {elapsed:.0f}s",
        file=sys.stderr,
    )

    # Normalise Copeland (0 to 1)
    max_wins = max(wins.values()) if wins else 1
    max_wins = max(max_wins, 1)
    copeland_norm = {cid: wins.get(cid, 0) / max_wins for cid in (cs.candidate_id for cs in window)}

    # Also normalise original score within the window so blending isn't dominated
    orig_scores = [cs.score for cs in window]
    omin, omax = min(orig_scores), max(orig_scores)
    spread = max(omax - omin, 1e-9)
    orig_norm = {cs.candidate_id: (cs.score - omin) / spread for cs in window}

    # Blend
    blended_score: dict[str, float] = {
        cid: (1 - alpha) * orig_norm[cid] + alpha * copeland_norm[cid]
        for cid in copeland_norm
    }

    # Re-sort the window by blended score (desc), break ties by candidate_id asc
    window_reranked = sorted(
        window,
        key=lambda cs: (-blended_score.get(cs.candidate_id, 0.0), cs.candidate_id),
    )

    # Log moves
    orig_order = [cs.candidate_id for cs in window]
    new_order = [cs.candidate_id for cs in window_reranked]
    moves = sum(1 for a, b in zip(orig_order, new_order) if a != b)
    print(f"  debate: {moves} positions in top {n} changed.", file=sys.stderr)

    return window_reranked + tail
