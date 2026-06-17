# Eval — Interview Cheat Sheet

This folder turns the cheat-sheet generator's quality bar into something
measurable. The generator's `../SKILL.md` describes what "good" looks like in
prose. An eval is how you prove a generated sheet actually meets it, instead of
eyeballing one and calling it fine.

The idea, in one line: **the SKILL.md is the spec; this eval is the test suite
for a probabilistic system** where there's no single "correct" output, only
better and worse ones.

## Files

- `rubric.md` — every SKILL.md rule restated as a gradeable dimension, with a
  type (`code` or `judge`), a weight, and a pass condition. This is the
  contract.
- `parse.py` — extracts the structures the rubric cares about (sections,
  scripts, anchor bars, pacing cues, nav links) from a generated HTML file.
  Stdlib only.
- `run.py` — runs every dimension against one or more files and prints a scored
  report ending in a single 0-100 headline plus a pass/fail verdict.

## Run it

```bash
# code checks only (no API key needed)
python3 run.py --no-judge ../examples/example-prep-sheet.html

# full run including the three LLM-judged dimensions
export ANTHROPIC_API_KEY=sk-...
python3 run.py path/to/your-generated-prep.html

# machine-readable output for CI
python3 run.py --json prep.html
```

Exit code is `0` if every file passes and `1` otherwise, so this drops straight
into a CI step that gates new generations.

## How scoring works

Each dimension produces a 0-1 score: code dimensions report the fraction of
items that passed; judged dimensions map a 1-5 rating onto 0-1. The headline is
the weighted mean of every dimension that ran, scaled to 100. Dimensions that
can't run (no API key, or nothing of that kind to grade) are excluded from the
mean and noted, never scored zero.

Two dimensions are **hard gates** (`*` in the report): em-dash use and
navigation integrity. These are binary correctness issues, so any failure there
fails the whole run regardless of the headline number.

A run passes at **>= 85 with no hard failures.**

## What the fixture shows

`example-prep-sheet.html` is a real generated cheat sheet — and it intentionally
**fails** the eval (74.5, hard failure on em dashes). That's expected and the
point: the eval caught spec violations in the reference output itself. Specifically:

- **Em dashes** (hard gate) — 9 found in titles and pacing notes; the SKILL.md
  prohibits them in all written content
- **Pacing cue restraint** — two sections exceed the 2-cue budget

Running the eval on your own generated sheet (not the example) is the real use.
If it passes on a generated sheet but flags the example, the harness is working
correctly.
