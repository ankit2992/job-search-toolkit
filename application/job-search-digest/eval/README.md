# Eval — Job Search Digest

This folder measures whether a generated digest returned *the right jobs*:
only roles matching the request, the right seniority, the right locations, no
duplicates, valid links, within the cap.

This tool sits at the opposite end of the spectrum from the cheat-sheet eval.
A digest is a retrieval-and-filtering problem, so its quality is **objective**
— precision, dedup, and rule-adherence are all code checks. There's almost no
subjective "taste" to grade. The eval therefore runs fully without an API key;
the single LLM dimension is optional and only sanity-checks fuzzy title matches.

## The run record

The eval consumes a JSON **run record**: the criteria the user gave plus the
jobs the skill returned. You can't judge "relevance" without knowing what was
asked for, so both are needed. The digest skill should log this record on each
run (a one-line addition to Step 4 of the skill) — useful for evaluation and
for debugging a bad digest later.

```jsonc
{
  "criteria": { "role_families": [...], "locations": [...], "seniority": [...] },
  "jobs": [ { "title": ..., "company": ..., "url": ..., ... } ]
}
```

## Run it

```bash
python3 run.py --no-judge ../examples/example-digest.json
# with the optional LLM relevance check:
export ANTHROPIC_API_KEY=sk-...
python3 run.py ../examples/example-digest.json
```

## What the fixture shows

`example-digest.json` is a realistic run with five planted defects: a duplicate
posting (same role on LinkedIn and an ATS with different URLs), a Director-level
title that should have been dropped, an EMEA-only remote role, an off-target
"Product Marketing Manager," and a URL missing its scheme. The eval catches all
five across the dedup, seniority, location, URL, and role-precision dimensions
and fails the run. Swap in a clean record and it passes.

Hard gates: deduplication and schema completeness. A run passes at **>= 85 with
no hard failures.**
