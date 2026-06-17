# Comp Comparator — Eval Rubric

The comp comparator's job is to be *accurate and conservative* about money, and
to never cross into giving accept/reject advice. So unlike the cheat sheet
(which is graded mostly on subjective writing quality), this tool is graded
mostly on **arithmetic correctness and rule-adherence** — things a machine can
check exactly. The few judged dimensions cover recall and tone.

The principle is the same: **the SKILL.md is the spec, this rubric proves the
output meets it.** Every rule below is lifted from `../SKILL.md`.

Each dimension has a **type** (`code` = exact/objective, `judge` = needs an LLM)
and a **weight**.

The eval reads a single comparison markdown file. That file also contains its
own inputs (the offer letter excerpt and verbal context) at the top, which is
what lets the eval check whether the output flagged the risks actually present
in the offer.

---

## Code-checked dimensions

### 1. Required sections present — `code`, weight 1.0, HARD
SKILL.md output spec lists five sections: component breakdown, total comp
estimate, language risk flags, negotiation sequencing, principles.
**Pass:** all five section headings are present. Missing sections are listed.

### 2. Guaranteed total excludes discretionary comp — `code`, weight 2.0, HARD
SKILL.md: "Never convert a discretionary or unconfirmed bonus into a guaranteed
dollar amount in the totals. Show it separately." This is the tool's core
promise and the highest-weighted dimension.
**Pass:** the stated guaranteed total equals the sum of only the confirmed/
guaranteed components (base plus any guaranteed sign-on), and the
discretionary/unconfirmed amount appears on a separate "upside" line, not in
the guaranteed figure.
**Fail:** the guaranteed total is larger than the confirmed components — i.e.
an unconfirmed bonus has been folded in.

### 3. Total comp arithmetic is correct — `code`, weight 1.0
SKILL.md: "Show the calculation explicitly."
**Pass:** the guaranteed total matches the base figure from the component
table (within a small rounding tolerance) when bonus is unconfirmed, or the
shown sum when components are guaranteed.

### 4. Risk-flag recall — `code`, weight 1.5
SKILL.md lists risk patterns to flag (reserves-the-right-to-modify,
eligible-to-participate-with-no-target, cliff vesting, verbal-not-written).
The eval scans the input excerpt for these patterns, then checks the output's
risk-flags section addresses each one found.
**Score:** fraction of input risk patterns that the output actually flagged.
Missed patterns are reported.

### 5. No structurally-irrelevant asks — `code`, weight 1.0
SKILL.md: don't ask for a comp category the company structurally can't offer
(e.g. equity at a mutual company with no shareholders).
**Pass:** if the inputs/output indicate equity is not applicable, the
negotiation plan does not include an equity ask.

---

## LLM-judged dimensions

Require `ANTHROPIC_API_KEY`; skipped gracefully if absent.

### 6. No accept/reject verdict — `judge`, weight 1.5, HARD
SKILL.md: "Do not provide a recommendation on whether to accept an offer...
If asked directly 'should I take this,' restate the tradeoffs rather than
giving a verdict." This is a guardrail, so it's a hard gate.
**5:** lays out tradeoffs and lets the candidate decide. **1:** tells the
candidate to accept or reject. Any verdict language is quoted in the report.

### 7. Unconfirmed values handled honestly — `judge`, weight 1.0
SKILL.md: ambiguous values are marked **unconfirmed** rather than guessed.
**5:** every ambiguous term is explicitly marked unconfirmed. **1:** a number
is invented for an ambiguous term.

### 8. Sequencing logic is sound — `judge`, weight 1.0
SKILL.md: negotiate in order of employer flexibility (base → sign-on → bonus
confirmation → PTO → start date → equity), with rationale.
**5:** order follows flexibility logic with clear rationale. **1:** arbitrary
or backwards ordering.

---

## Headline score

Weighted mean of dimensions that ran, normalized to 0-100. Code dimensions
contribute their pass-fraction; judged dimensions contribute (score-1)/4. A
dimension that can't run is excluded and noted.

Hard gates: dimensions 1, 2, and 6. Any hard failure fails the run regardless
of headline. A run passes at **>= 85 with no hard failures.**
