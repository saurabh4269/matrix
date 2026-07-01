"""LLM-judge tournament on a submission's top-20.

Three personas from vision.md ("Hard Technical Cynic", "Growth & Trajectory
Scout", "Contextual Matchmaker") vote pairwise on the candidates. We
aggregate votes via Copeland (count of pair-wins per candidate) to produce
a proxy ranking, then measure agreement with our submission.

Output: eval YAML with:
  - per-candidate Copeland score (votes won)
  - proxy ranking
  - top-K agreement vs submission (overlap + Kendall tau)
  - per-persona disagreement signal (does Cynic systematically disagree?)
  - cost estimate

This is the SILVER tier of our eval — proxy, not ground truth, but a
useful "did the experiment make the top-20 more defensible" signal.

Pair budget: top-K=10 → C(10,2)=45 pairs × 3 personas = 135 calls.
At Haiku pricing that's ~$0.50 per run.

Usage:
    export ANTHROPIC_API_KEY=...
    python -m eval.judge --submission submissions/team_v4.csv \\
                         --structured submissions/team_v4.structured.jsonl \\
                         --top-k 10
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# Personas — direct quotes from vision.md table
# ---------------------------------------------------------------------------

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
    "You will compare two candidates for the role above. For each, you have:\n"
    "  - name, title, company, years of experience, location\n"
    "  - the model's structured reasoning + highlights + concerns\n"
    "  - behavioural availability snapshot\n\n"
    "Decide which candidate is the STRONGER fit FROM YOUR PERSONA's POINT OF VIEW.\n"
    "Output ONLY a single JSON object, nothing else:\n"
    '  {"winner": "A" | "B", "confidence": "high" | "medium" | "low", "reason": "<one short sentence>"}\n'
    "If they are roughly equal from your lens, pick the slightly better one and use confidence=low."
)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_submission(csv_path: Path) -> list[dict[str, Any]]:
    rows = []
    with open(csv_path, "r", encoding="utf-8") as fp:
        for r in csv.DictReader(fp):
            rows.append({
                "candidate_id": r["candidate_id"],
                "rank": int(r["rank"]),
                "score": float(r["score"]),
                "reasoning": r.get("reasoning", ""),
            })
    return sorted(rows, key=lambda x: x["rank"])


def load_structured(jsonl_path: Path) -> dict[str, dict[str, Any]]:
    by_id = {}
    if not jsonl_path.exists():
        return by_id
    with open(jsonl_path, "r", encoding="utf-8") as fp:
        for line in fp:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            by_id[r["candidate_id"]] = r
    return by_id


def render_card(row: dict[str, Any], extra: dict[str, Any] | None) -> str:
    """Compact text card the model can read in <300 tokens."""
    parts = [
        f"Name: {extra.get('name') if extra else row['candidate_id']}",
    ]
    if extra:
        parts.extend([
            f"Title: {extra.get('current_title', '?')} at {extra.get('current_company', '?')}",
            f"YoE: {extra.get('years_of_experience', '?')}",
            f"Location: {extra.get('location', '?')}",
        ])
    parts.append(f"Model reasoning: {row['reasoning']}")
    if extra and extra.get("snr_high"):
        highs = [h.get("evidence", "") for h in extra["snr_high"][:3]]
        parts.append("Highlights: " + " | ".join(highs))
    if extra and extra.get("concerns"):
        concerns = [c.get("evidence", "") for c in extra["concerns"][:2]]
        if concerns:
            parts.append("Concerns: " + " | ".join(concerns))
    if extra and extra.get("behavioural"):
        b = extra["behavioural"]
        parts.append(
            f"Behavioural: open_to_work={b.get('open_to_work')}, "
            f"notice={b.get('notice_days')}d, "
            f"availability_modifier={b.get('behav_modifier_total')}"
        )
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

def call_persona(
    client, model: str, persona_prompt: str, jd_text: str,
    card_a: str, card_b: str,
) -> dict[str, Any]:
    """Return parsed JSON {winner, confidence, reason} or {} on error."""
    sys_prompt = f"{persona_prompt}\n\nROLE CONTEXT:\n{jd_text[:1500]}\n\n{INSTRUCTION}"
    user_msg = f"Candidate A:\n{card_a}\n\n---\n\nCandidate B:\n{card_b}"
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=200,
            system=sys_prompt,
            messages=[{"role": "user", "content": user_msg}],
        )
    except Exception as e:
        print(f"  LLM error: {e}", file=sys.stderr)
        return {}
    raw = "".join(b.text for b in msg.content if hasattr(b, "text")).strip()
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    try:
        d = json.loads(raw)
        if d.get("winner") in ("A", "B"):
            return d
    except Exception:
        pass
    return {}


# ---------------------------------------------------------------------------
# Tournament
# ---------------------------------------------------------------------------

def tournament(
    submission_rows: list[dict[str, Any]],
    structured: dict[str, dict[str, Any]],
    jd_text: str,
    top_k: int,
    model: str = "claude-haiku-4-5-20251001",
    progress: bool = True,
) -> dict[str, Any]:
    try:
        import anthropic  # type: ignore
    except ImportError:
        raise RuntimeError("pip install anthropic")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("Set ANTHROPIC_API_KEY")
    client = anthropic.Anthropic()

    top = submission_rows[:top_k]
    pair_count = (top_k * (top_k - 1)) // 2
    call_budget = pair_count * len(PERSONAS)
    if progress:
        print(f"  pairs: {pair_count}, personas: {len(PERSONAS)}, total calls: {call_budget}", file=sys.stderr)

    wins: dict[str, int] = defaultdict(int)  # Copeland: count of pair-wins (any persona majority)
    persona_wins: dict[str, dict[str, int]] = {p: defaultdict(int) for p in PERSONAS}
    failed_calls = 0
    t0 = time.time()
    call_idx = 0
    for i in range(top_k):
        for j in range(i + 1, top_k):
            ra, rb = top[i], top[j]
            a, b = ra["candidate_id"], rb["candidate_id"]
            card_a = render_card(ra, structured.get(a))
            card_b = render_card(rb, structured.get(b))
            persona_votes: dict[str, str] = {}
            for pkey, pprompt in PERSONAS.items():
                call_idx += 1
                d = call_persona(client, model, pprompt, jd_text, card_a, card_b)
                if not d:
                    failed_calls += 1
                    continue
                winner_id = a if d["winner"] == "A" else b
                persona_votes[pkey] = winner_id
                persona_wins[pkey][winner_id] += 1
                if progress and call_idx % 15 == 0:
                    elapsed = time.time() - t0
                    print(f"    {call_idx}/{call_budget} ({elapsed:.0f}s)", file=sys.stderr)
            # Majority vote across personas → Copeland pair-win
            if persona_votes:
                from collections import Counter
                tally = Counter(persona_votes.values())
                majority_winner = tally.most_common(1)[0][0]
                wins[majority_winner] += 1

    elapsed = time.time() - t0
    proxy_ranking = sorted(
        ((cid, wins.get(cid, 0)) for cid in (r["candidate_id"] for r in top)),
        key=lambda x: -x[1],
    )
    return {
        "top_k": top_k,
        "model": model,
        "elapsed_seconds": round(elapsed, 1),
        "calls_total": call_budget,
        "calls_failed": failed_calls,
        "pair_wins_by_candidate": dict(wins),
        "proxy_ranking_by_copeland": [{"candidate_id": cid, "wins": w} for cid, w in proxy_ranking],
        "per_persona_wins": {p: dict(c) for p, c in persona_wins.items()},
    }


# ---------------------------------------------------------------------------
# Agreement metrics
# ---------------------------------------------------------------------------

def kendall_tau(rank_a: list[str], rank_b: list[str]) -> float:
    """Kendall's tau-b between two rankings of the same candidate set."""
    common = set(rank_a) & set(rank_b)
    if len(common) < 2:
        return 0.0
    ids = list(common)
    idx_a = {c: rank_a.index(c) for c in ids}
    idx_b = {c: rank_b.index(c) for c in ids}
    concordant = discordant = 0
    n = len(ids)
    for i in range(n):
        for j in range(i + 1, n):
            ai, aj = idx_a[ids[i]], idx_a[ids[j]]
            bi, bj = idx_b[ids[i]], idx_b[ids[j]]
            if (ai - aj) * (bi - bj) > 0:
                concordant += 1
            elif (ai - aj) * (bi - bj) < 0:
                discordant += 1
    total = n * (n - 1) // 2
    return (concordant - discordant) / total if total else 0.0


def compute_agreement(
    submission_top: list[str], proxy_top: list[str], top_k: int,
) -> dict[str, Any]:
    sub_k = submission_top[:top_k]
    proxy_k = proxy_top[:top_k]
    overlap = len(set(sub_k) & set(proxy_k))
    return {
        f"top_{top_k}_set_overlap": overlap,
        f"top_{top_k}_set_overlap_ratio": round(overlap / top_k, 3) if top_k else 0.0,
        f"top_{top_k}_kendall_tau": round(kendall_tau(sub_k, proxy_k), 3),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--submission", required=True)
    ap.add_argument("--structured", default=None, help="Optional structured.jsonl beside the CSV.")
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--jd-text", default=None, help="JD text file. Defaults to data/jd_text.txt.")
    ap.add_argument("--model", default="claude-haiku-4-5-20251001")
    ap.add_argument("--out", default=None, help="Output YAML path. Defaults to <submission>.judge.yaml.")
    args = ap.parse_args()

    sub_path = Path(args.submission)
    if not sub_path.exists():
        print(f"FATAL: {sub_path} not found.", file=sys.stderr)
        sys.exit(1)

    rows = load_submission(sub_path)
    structured_path = Path(args.structured) if args.structured else sub_path.with_name(sub_path.stem + ".structured.jsonl")
    structured = load_structured(structured_path)

    jd_text_path = Path(args.jd_text) if args.jd_text else ROOT / "data" / "jd_text.txt"
    if not jd_text_path.exists():
        print(f"FATAL: JD text not at {jd_text_path}. Pass --jd-text.", file=sys.stderr)
        sys.exit(1)
    jd_text = jd_text_path.read_text(encoding="utf-8")

    print(f"Running judge tournament on top-{args.top_k} of {sub_path.name}", file=sys.stderr)
    result = tournament(rows, structured, jd_text, top_k=args.top_k, model=args.model)

    submission_top = [r["candidate_id"] for r in rows[:args.top_k]]
    proxy_top = [x["candidate_id"] for x in result["proxy_ranking_by_copeland"]]
    agreement = compute_agreement(submission_top, proxy_top, top_k=args.top_k)

    out_data = {
        "submission": sub_path.name,
        "judge": result,
        "submission_top": submission_top,
        "agreement_vs_submission": agreement,
    }

    out_path = Path(args.out) if args.out else sub_path.with_name(sub_path.stem + ".judge.yaml")
    out_path.write_text(yaml.safe_dump(out_data, sort_keys=False, default_flow_style=False), encoding="utf-8")
    print(f"\nWrote {out_path}")
    print(f"  top-{args.top_k} overlap: {agreement[f'top_{args.top_k}_set_overlap']}/{args.top_k}")
    print(f"  kendall tau:    {agreement[f'top_{args.top_k}_kendall_tau']}")


if __name__ == "__main__":
    main()
