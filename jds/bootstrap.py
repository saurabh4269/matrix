"""Bootstrap a new JD YAML config from raw JD text + the candidate pool.

Three sources combine to produce a starter YAML:

  1. LLM extraction from the JD text:
     - digest (role, location, experience, style, 3-4 avoid bullets)
     - yoe (peak, sigma)
     - location (preferred_cities, country, visa_sponsorship)
     - title_patterns (relevant_titles regex, nlp_ir regex, excluded_subdomain regex)
     - must_haves.python_skill_name (the role's primary language)
     - must_haves.embedding_tools (named tech stack for this domain)
     - must_haves.vector_db_tools (data layer for this domain)
     - must_haves.ranking_eval_terms (metrics / orchestration for this domain)
     - must_haves.framework_skills (the JD's "don't be a tutorial-level user")
     - specific_technical_entities (~50 named systems for this domain)

  2. Candidate pool mining (optional, --candidates flag):
     - companies.product_companies (most common product-co names in the pool)
     - Augment specific_technical_entities with frequent named entities

  3. Reusable defaults from ai_engineer.yaml:
     - substance vocabularies (English verbs, narrative connectives)
     - sizes
     - weights (sensible starting point; tune via eval/tune_weights.py later)
     - behavioural weights
     - companies.consulting_firms (well-known list, JD-agnostic)
     - honeypot_company_ages (the known-young-co dictionary)

Usage:
    export ANTHROPIC_API_KEY=...

    # Minimal:
    python -m jds.bootstrap \\
        --jd-text path/to/jd.txt \\
        --out jds/<role>.yaml

    # With pool mining:
    python -m jds.bootstrap \\
        --jd-text path/to/jd.txt \\
        --candidates path/to/candidates.jsonl \\
        --out jds/<role>.yaml

After this runs, skim the YAML. The LLM gets ~80% right but you should:
  - Verify the regexes compile and match what you expect
  - Add/remove items from the vocabularies if the LLM missed something
  - Tune weights if the hand-defaults are obviously wrong for the role
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

from src.jd_config import load_jd
from src.load import iter_candidates


# ---------------------------------------------------------------------------
# LLM extraction
# ---------------------------------------------------------------------------

EXTRACTION_SYSTEM = """You extract structured configuration fields from a job description for a candidate-ranking system.

Output ONLY a single JSON object. No prose before or after. No code fences. Just the raw JSON.

The JSON object must have these keys:

{
  "digest": {
    "role": "Short title sentence ending with period.",
    "location": "City or Region. Work mode (hybrid/onsite/remote).",
    "experience": "X to Y years.",
    "style": "One-line cultural/style note.",
    "avoid": ["3-4 explicit disqualifiers as single sentences"]
  },
  "yoe": {"peak": <float>, "sigma": <float>},
  "location": {
    "preferred_cities": ["lowercase city names, no diacritics"],
    "country": "Country name",
    "visa_sponsorship": <bool>
  },
  "title_patterns": {
    "relevant_titles": "<Python regex matching the JD's core role titles, word-boundary anchored, IGNORECASE assumed>",
    "nlp_ir": "<Python regex matching the JD's specific subdomain (the narrow focus inside the role)>",
    "excluded_subdomain": "<Python regex matching adjacent-but-not-this-JD subdomains (people whose career is in this area get penalised)>"
  },
  "primary_language": "Python | JavaScript | TypeScript | Go | Rust | Java | etc.",
  "embedding_tools": ["named tools/libraries this role's main tech stack uses (10-20 items, lowercase)"],
  "vector_db_tools": ["named data layer / storage / infra tools (5-15 items, lowercase)"],
  "ranking_eval_terms": ["named evaluation/orchestration/quality metrics relevant to this role (5-15 items, lowercase)"],
  "framework_skills": ["frameworks the JD says it does NOT want the candidate to be only a tutorial-level user of (2-8 items, lowercase)"],
  "specific_technical_entities": ["50-100 named tools/systems/methods that an engineer in this role would mention in their work descriptions, lowercase"],
  "yoe_strict": <bool: true if the JD calls out the year range as strict, false if flexible>
}

Rules:
- All vocabulary lists are lowercase.
- Regexes must be valid Python regex. Use \\b for word boundaries. Use [\\s\\-]? between words that may or may not be hyphenated.
- For visa_sponsorship: true if the JD says they sponsor visas, false otherwise (assume false if unclear).
- For excluded_subdomain: think about what the JD explicitly does NOT want (e.g. for an AI Engineer role, CV/speech/robotics specialists).
- yoe.peak should be the midpoint of the stated range. yoe.sigma should be ~2.5 if flexible, ~1.5 if strict.
- avoid bullets: 3-4 items, each one sentence, derived from the JD's "do not" or "avoid" statements.

Be specific. Output only the JSON."""


def call_llm(jd_text: str, model: str = "claude-haiku-4-5-20251001") -> dict:
    """Call Anthropic Claude to extract structured fields from the JD text."""
    try:
        import anthropic  # type: ignore
    except ImportError:
        raise RuntimeError(
            "Install anthropic SDK: pip install anthropic"
        )
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. The bootstrap script needs an LLM call to extract fields."
        )

    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=model,
        max_tokens=4000,
        system=EXTRACTION_SYSTEM,
        messages=[{"role": "user", "content": f"Job description:\n\n{jd_text}\n\nExtract."}],
    )
    raw = "".join(b.text for b in msg.content if hasattr(b, "text"))
    # Strip code fences if the model added them
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Candidate pool mining
# ---------------------------------------------------------------------------

def mine_pool(candidates_path: Path, n_top_companies: int = 50,
              n_top_entities: int = 80) -> dict:
    """Mine the candidate pool for common product-company names + technical entities."""
    company_counts: Counter = Counter()
    company_sizes: dict[str, set] = {}
    # Rough entity extraction: capitalized multi-word tokens in description text
    # plus the JD-vocab keywords from candidates' skill lists.
    skill_counts: Counter = Counter()

    print(f"Mining {candidates_path}…", file=sys.stderr)
    n_seen = 0
    for cand in iter_candidates(candidates_path):
        n_seen += 1
        # Current company
        co = (cand.profile.current_company or "").strip().lower()
        sz = cand.profile.current_company_size or ""
        if co and 3 <= len(co) <= 40:
            company_counts[co] += 1
            company_sizes.setdefault(co, set()).add(sz)
        # Career history companies
        for r in cand.career_history:
            rc = (r.company or "").strip().lower()
            rs = r.company_size or ""
            if rc and 3 <= len(rc) <= 40:
                company_counts[rc] += 1
                company_sizes.setdefault(rc, set()).add(rs)
        # Skills
        for s in cand.skills:
            n = (s.name or "").strip().lower()
            if 2 <= len(n) <= 40:
                skill_counts[n] += 1
        if n_seen % 25000 == 0:
            print(f"  {n_seen:>7,} candidates mined", file=sys.stderr)

    # Product-company filter: company appears in 11-5000 size buckets (not bigcorp)
    # AND not in the canonical consulting firm list
    consulting_set = {
        "tcs", "tata consultancy services", "tata consultancy",
        "infosys", "wipro", "accenture", "cognizant", "capgemini",
        "hcl", "hcl technologies", "lti", "mindtree", "tech mahindra",
        "mphasis", "deloitte", "kpmg", "ey", "pwc",
    }
    product_candidates = []
    for co, count in company_counts.most_common(500):
        if co in consulting_set:
            continue
        sizes = company_sizes.get(co, set())
        # If the company shows up at small/mid sizes anywhere, it's a product co
        if any(s in {"11-50", "51-200", "201-500", "501-1000", "1001-5000"} for s in sizes):
            product_candidates.append(co)
            if len(product_candidates) >= n_top_companies:
                break

    # Top skills as a backup vocabulary
    top_skills = [s for s, _ in skill_counts.most_common(n_top_entities)]

    return {
        "product_companies": product_candidates,
        "pool_skills": top_skills,
    }


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def build_yaml(
    name: str,
    extracted: dict,
    mined: dict | None,
    base: dict,
) -> dict:
    """Assemble the final config from LLM extraction + pool mining + base defaults."""
    digest = extracted["digest"]
    yoe = extracted["yoe"]
    location = extracted["location"]
    title_patterns = extracted["title_patterns"]

    # Reuse base substance vocab (English verbs are JD-agnostic)
    substance = base.get("substance", {})

    # Merge specific technical entities: LLM extraction + pool-mined skills
    extracted_entities = set(extracted.get("specific_technical_entities", []))
    if mined:
        pool_skills = mined.get("pool_skills", [])
        # Use first 30 most-common pool skills as additional entities
        extracted_entities.update(pool_skills[:30])
    entities = sorted(extracted_entities)

    # Companies
    consulting_firms = base.get("companies", {}).get("consulting_firms", [])
    product_companies = []
    if mined and mined.get("product_companies"):
        product_companies = sorted(set(mined["product_companies"]))
    else:
        product_companies = base.get("companies", {}).get("product_companies", [])
    named_employers = base.get("companies", {}).get("named_employers", [])

    # Sizes — same defaults
    sizes = base.get("sizes", {"bigcorp_size": "10001+", "small_mid_sizes": ["11-50", "51-200", "201-500"]})

    # Honeypot company ages — keep base, can be edited
    honeypot_ages = base.get("honeypot_company_ages", {})

    # Weights — start from base defaults; tuneable via eval/tune_weights.py
    weights = base.get("weights", {})

    return {
        "name": name,
        "display_name": digest["role"].rstrip(".").strip(),
        "digest": {
            "role": digest["role"],
            "location": digest["location"],
            "experience": digest["experience"],
            "style": digest["style"],
            "avoid": digest["avoid"],
        },
        "jd_text": digest.get("_full_text", ""),
        "yoe": {
            "peak": float(yoe.get("peak", 7.0)),
            "sigma": float(yoe.get("sigma", 2.5)),
        },
        "location": {
            "preferred_cities": [c.lower() for c in location.get("preferred_cities", [])],
            "country": location.get("country", ""),
            "visa_sponsorship": bool(location.get("visa_sponsorship", False)),
        },
        "title_patterns": {
            "relevant_titles": title_patterns["relevant_titles"],
            "nlp_ir": title_patterns.get("nlp_ir", ""),
            "excluded_subdomain": title_patterns.get("excluded_subdomain", ""),
        },
        "must_haves": {
            "python_skill_name": extracted.get("primary_language", "Python"),
            "embedding_tools": [t.lower() for t in extracted.get("embedding_tools", [])],
            "vector_db_tools": [t.lower() for t in extracted.get("vector_db_tools", [])],
            "ranking_eval_terms": [t.lower() for t in extracted.get("ranking_eval_terms", [])],
            "framework_skills": [t.lower() for t in extracted.get("framework_skills", [])],
        },
        "substance": substance,
        "specific_technical_entities": entities,
        "companies": {
            "consulting_firms": consulting_firms,
            "product_companies": product_companies,
            "named_employers": named_employers,
        },
        "sizes": sizes,
        "honeypot_company_ages": honeypot_ages,
        "weights": weights,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Bootstrap a new JD YAML config from raw JD text.")
    ap.add_argument("--jd-text", required=True, help="Path to the JD text file")
    ap.add_argument("--name", default=None, help="Slug for the JD (defaults to filename stem)")
    ap.add_argument("--candidates", default=None,
                    help="Optional: path to candidates.jsonl for pool-derived vocabularies")
    ap.add_argument("--out", required=True, help="Output YAML path")
    ap.add_argument("--base", default="jds/ai_engineer.yaml",
                    help="Base config to inherit substance vocab / weights / sizes from")
    ap.add_argument("--model", default="claude-haiku-4-5-20251001",
                    help="Anthropic model id")
    args = ap.parse_args()

    jd_text_path = Path(args.jd_text)
    if not jd_text_path.exists():
        print(f"FATAL: {jd_text_path} not found.", file=sys.stderr)
        sys.exit(1)
    jd_text = jd_text_path.read_text(encoding="utf-8")

    name = args.name or jd_text_path.stem.replace("-", "_").lower()

    print(f"Bootstrapping JD config: {name}", file=sys.stderr)
    print(f"  Reading base from {args.base}", file=sys.stderr)
    base = load_jd(args.base).model_dump()

    print(f"  Calling LLM ({args.model}) to extract structured fields…", file=sys.stderr)
    extracted = call_llm(jd_text, model=args.model)
    # Attach the raw JD text so it ends up in the output
    extracted["digest"]["_full_text"] = jd_text

    mined = None
    if args.candidates:
        mined = mine_pool(Path(args.candidates))
        print(
            f"  Pool mined: {len(mined['product_companies'])} product cos, "
            f"{len(mined['pool_skills'])} skill candidates",
            file=sys.stderr,
        )

    config = build_yaml(name, extracted, mined, base)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fp:
        yaml.safe_dump(config, fp, default_flow_style=False, sort_keys=False, width=100)

    # Validate the config loads cleanly under JDConfig
    print(f"  Validating {out}…", file=sys.stderr)
    try:
        load_jd(out)
        print(f"  PASS — JD config is valid.", file=sys.stderr)
    except Exception as e:
        print(f"  FAIL — JD config doesn't validate: {e}", file=sys.stderr)
        print("  Edit the file manually to fix; the field that broke is reported above.",
              file=sys.stderr)
        sys.exit(2)

    print(f"\nWrote {out}\n", file=sys.stderr)
    print("Next steps:", file=sys.stderr)
    print("  1. Skim the YAML and verify regexes / vocab lists.", file=sys.stderr)
    print(f"  2. Run: python rank.py --jd {out} --candidates <...> --out ...", file=sys.stderr)


if __name__ == "__main__":
    main()
