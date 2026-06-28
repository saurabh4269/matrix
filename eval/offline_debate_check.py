"""Offline multi-agent debate to sanity-check the user's hand labels.

vision.md's "Multi-Agent Forensic Reranker" idea, surviving the runtime
compute spec by moving the agents OFFLINE: they don't rank candidates;
they audit your labels.

For each labelled candidate (read from eval/labelled.jsonl), three LLM
agents independently produce a tier guess (0-5) given only the candidate's
profile + the JD. Their distribution is compared to your label. The script
flags candidates where:
  - All three agents disagree with you (probably miscalibrated)
  - The three agents themselves wildly disagree (genuinely borderline)

You then revisit those flagged rows in labels.csv and decide if your label
should change. The agents do NOT overwrite your labels; they just point at
the cases worth a second look.

Network IS allowed here because this runs offline, before the submission.
Uses the ANTHROPIC_API_KEY env var if set; falls back to a deterministic
no-op if not set (script reports 'no model available').

Usage:
  export ANTHROPIC_API_KEY=...
  python -m eval.offline_debate_check --labelled eval/labelled.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

from src.jd_config import get_config


def _build_candidate_brief(rec: dict) -> str:
    """Compact one-paragraph candidate brief for the LLM."""
    cand = rec["candidate"]
    profile = cand["profile"]
    roles = cand.get("career_history", [])[:5]
    skills = cand.get("skills", [])[:10]

    role_lines = []
    for r in roles:
        d = (r.get("description") or "")[:240]
        role_lines.append(
            f"  - {r['title']} @ {r['company']} "
            f"({r.get('duration_months', 0)}mo, {r.get('company_size', '')}): {d}"
        )

    skill_lines = ", ".join(
        f"{s['name']} ({s.get('proficiency')}, {s.get('duration_months', 0)}mo, "
        f"{s.get('endorsements', 0)}e)"
        for s in skills
    )

    return (
        f"Candidate: {profile.get('anonymized_name', '?')}\n"
        f"Current: {profile.get('current_title', '?')} @ "
        f"{profile.get('current_company', '?')} ({profile.get('years_of_experience', 0)}y)\n"
        f"Location: {profile.get('location', '?')}, {profile.get('country', '?')}\n"
        f"Summary: {(profile.get('summary') or '')[:600]}\n"
        f"Career:\n" + "\n".join(role_lines) + "\n"
        f"Skills: {skill_lines}\n"
    )


PERSONAS = [
    {
        "name": "Hard Technical Cynic",
        "system": (
            "You are a senior engineering hiring manager who looks for deep technical "
            "execution. You ignore brand names and look for high-impact ownership and "
            "concrete, named systems in the candidate's role descriptions. You are "
            "skeptical of credential-only profiles. Output ONLY a JSON object: "
            '{"tier": <0-5>, "rationale": "<10-30 words>"}.'
        ),
    },
    {
        "name": "Growth Scout",
        "system": (
            "You evaluate trajectory: promotion velocity, whether the candidate is "
            "outgrowing their current role, and whether they're moving toward this "
            "JD's domain or away from it. You favour high-potential under-titled "
            "candidates over plateaued senior ones. Output ONLY a JSON object: "
            '{"tier": <0-5>, "rationale": "<10-30 words>"}.'
        ),
    },
    {
        "name": "Contextual Matchmaker",
        "system": (
            "You evaluate whether the candidate's historical environment matches the "
            "JD's operational reality (Series-A AI startup, hybrid Pune/Noida, "
            "founding-team energy, hands-on engineering). Output ONLY a JSON object: "
            '{"tier": <0-5>, "rationale": "<10-30 words>"}.'
        ),
    },
]


def _call_anthropic(system: str, user: str, model: str = "claude-haiku-4-5-20251001") -> str:
    """Tiny wrapper around the Anthropic SDK. Returns the model's text reply."""
    try:
        import anthropic  # type: ignore
    except ImportError:
        raise RuntimeError("Install anthropic: pip install anthropic")
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=model,
        max_tokens=256,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in msg.content if hasattr(b, "text"))


def _parse_tier(s: str) -> tuple[int, str]:
    """Best-effort parse of '{"tier": N, "rationale": ...}'."""
    s = s.strip()
    # Find the first {...} block
    start = s.find("{")
    end = s.rfind("}")
    if start < 0 or end <= start:
        return -1, s[:80]
    try:
        obj = json.loads(s[start : end + 1])
        return int(obj.get("tier", -1)), str(obj.get("rationale", ""))[:200]
    except Exception:
        return -1, s[:80]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labelled", default="eval/labelled.jsonl")
    ap.add_argument("--out", default="eval/debate_disagreements.md")
    ap.add_argument("--limit", type=int, default=None,
                    help="Only audit first N labelled candidates (for testing)")
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "No ANTHROPIC_API_KEY set. This script needs one to call the LLM.\n"
            "Set it with: export ANTHROPIC_API_KEY=sk-... (then re-run).",
            file=sys.stderr,
        )
        sys.exit(1)

    jd_text = get_config().jd_text

    records: list[dict] = []
    with open(args.labelled, "r", encoding="utf-8") as fp:
        for line in fp:
            if line.strip():
                records.append(json.loads(line))
    print(f"Loaded {len(records)} labelled candidates.", file=sys.stderr)
    if args.limit:
        records = records[: args.limit]

    flagged: list[dict] = []
    for i, rec in enumerate(records):
        brief = _build_candidate_brief(rec)
        user_label = int(rec.get("label", {}).get("tier", -1))
        user_msg = (
            f"Job description:\n{jd_text}\n\n"
            f"Candidate brief:\n{brief}\n\n"
            f"Give a tier 0-5 for how well this candidate fits the JD."
        )
        votes = []
        for persona in PERSONAS:
            try:
                resp = _call_anthropic(persona["system"], user_msg)
                tier, rationale = _parse_tier(resp)
                if tier >= 0:
                    votes.append((persona["name"], tier, rationale))
            except Exception as e:
                print(f"  {persona['name']} failed: {e}", file=sys.stderr)

        if len(votes) < 2:
            continue

        tiers = [v[1] for v in votes]
        agent_median = statistics.median(tiers)
        agent_spread = max(tiers) - min(tiers)
        delta = agent_median - user_label

        # Flag if all agents agree with each other (low spread) and disagree
        # with the user by 2+ tiers; or if the agents are widely split (3+).
        if (agent_spread <= 1 and abs(delta) >= 2) or agent_spread >= 3:
            flagged.append({
                "candidate_id": rec["candidate"]["candidate_id"],
                "name": rec["candidate"]["profile"].get("anonymized_name", "?"),
                "user_tier": user_label,
                "agent_median": agent_median,
                "agent_spread": agent_spread,
                "votes": votes,
            })

        if (i + 1) % 25 == 0:
            print(f"  {i+1}/{len(records)} reviewed, {len(flagged)} flagged so far.",
                  file=sys.stderr)

    # Write a Markdown report
    out = Path(args.out)
    with open(out, "w", encoding="utf-8") as fp:
        fp.write("# Debate disagreements with your labels\n\n")
        fp.write(f"Reviewed {len(records)} candidates. Flagged {len(flagged)}.\n\n")
        fp.write("These are candidates where three independent LLM agents either:\n")
        fp.write("- All agreed with each other but disagreed with your label by 2+ tiers, or\n")
        fp.write("- Disagreed widely with each other (3+ tier spread).\n\n")
        fp.write("Worth a second look. The agents do NOT overwrite your labels.\n\n")
        for f in flagged:
            fp.write(f"## {f['name']} ({f['candidate_id']})\n\n")
            fp.write(f"- Your tier: **{f['user_tier']}**\n")
            fp.write(f"- Agent median: **{f['agent_median']}** (spread {f['agent_spread']})\n\n")
            for name, tier, rationale in f["votes"]:
                fp.write(f"  - **{name}** said tier {tier}: {rationale}\n")
            fp.write("\n")
    print(f"\nWrote {out} with {len(flagged)} flagged candidates.", file=sys.stderr)


if __name__ == "__main__":
    main()
