# Eval — Comp Comparator

This folder measures whether a generated comp comparison is *accurate and
conservative about money* and stays out of giving accept/reject advice.

Unlike the cheat-sheet eval (which leans on LLM judges for subjective writing
quality), this tool is graded mostly by **objective code checks**: does the
arithmetic add up, is a discretionary bonus correctly kept out of the
guaranteed total, did the output flag the risky clauses that were actually in
the offer letter. That difference is the point — a reasoning/math tool has
checkable right answers, so most of its quality bar is code, not taste.

## Files

- `rubric.md` — each SKILL.md rule as a gradeable dimension, with type and weight.
- `parse.py` — pulls figures, the input offer language, and section structure
  out of a comparison markdown file. Stdlib only.
- `run.py` — runs every dimension and prints a scored report.

## Run it

```bash
# code checks only
python3 run.py --no-judge ../examples/example-comparison.md

# include the judged dimensions (no-verdict guardrail, sequencing, etc.)
export ANTHROPIC_API_KEY=sk-...
python3 run.py ../examples/example-comparison.md

# contrast a correct doc against a deliberately flawed one
python3 run.py --no-judge ../examples/example-comparison.md ../examples/example-comparison-flawed.md
```

## What the fixtures show

- `example-comparison.md` — a correct analysis. Scores 100 on code checks.
- `example-comparison-flawed.md` — the same offer analyzed badly: a
  discretionary bonus folded into the guaranteed total, the offer-letter risk
  clauses left unflagged, and an equity ask at a company with no equity. The
  eval catches all three and fails the run. The contrast between the two is the
  demonstration that the eval actually discriminates good from bad.

Hard gates: required sections, guaranteed-total cleanliness, and the
no-verdict guardrail. A run passes at **>= 85 with no hard failures.**
