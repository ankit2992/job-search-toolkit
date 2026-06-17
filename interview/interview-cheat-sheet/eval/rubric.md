# Interview Cheat Sheet — Eval Rubric

This is the quality spec for the cheat sheet generator, expressed as gradeable
criteria. Every rule here is lifted directly from `../SKILL.md`. The skill says
what "good" looks like in prose; this rubric turns each rule into a check that
produces a number, so quality can be measured instead of eyeballed.

The principle: **the SKILL.md is the PRD. This rubric is how we prove the output
meets it.** A generated cheat sheet either clears the bar or it doesn't, and we
can see exactly where it falls short.

Each dimension has a **type**:
- `code` — objectively checkable in Python, no judgment needed (cheap, exact)
- `judge` — needs an LLM to assess (subjective quality, scored 1-5)

And a **weight** used to roll the dimension scores up into one headline number.

---

## Code-checked dimensions (deterministic)

### 1. No em dashes — `code`, weight 1.0
SKILL.md: "No em dashes. Use periods, commas, or rephrase."
**Pass:** zero em dash (—) characters in visible content.
**Fail:** any present. Each occurrence is reported with its surrounding text.

### 2. Anchor word discipline — `code`, weight 1.0
SKILL.md: "extract 3-5 short capitalized anchor words ... keep them terse."
**Pass per anchor bar:** 3 to 5 tokens, each token short (<= 18 chars), no
spaces inside a token (anchor words are single recall tokens, not phrases).
**Score:** fraction of anchor bars that pass.

### 3. Pacing cue restraint — `code`, weight 1.0
SKILL.md: "Don't overuse these. 1-2 per script section is usually enough."
**Pass per section:** at most 2 cue tags ([PAUSE] + [SLOW] combined).
**Score:** fraction of script sections within budget. Over-budget sections
are listed with their counts.

### 4. Talk-time targets — `code`, weight 1.0
SKILL.md: spoken duration = words / 130 wpm * 60, with per-round targets:
recruiter ~90s pitch; hiring manager ~120s pitch and up to 120s per story;
exec ~90s pitch and up to 120s per story. "Flag any script that's
significantly over target."
**Pass per script:** computed seconds <= target * 1.25 (the "significantly
over" threshold). Round type is detected from the page eyebrow/title.
**Score:** fraction of scripts within target.

### 5. Navigation integrity — `code`, weight 1.0
SKILL.md: "Each .section needs a matching sidebar .nav-item with a href='#id'
that matches the section's id ... don't link to empty sections, and don't omit
a section from the sidebar if it's in the page."
**Pass:** every nav href points to a real section id, and every section has a
nav item. Orphan links and unlinked sections are both reported.

### 6. Stories in paragraph format — `code`, weight 0.5
SKILL.md: "Paragraph format for stories, not bullet points."
**Pass per story card:** no `<ul>`/`<ol>` list inside the story body.
**Score:** fraction of story cards that are prose, not lists.

---

## LLM-judged dimensions (subjective)

These need a model because there's no single right answer — only better and
worse. The judge is given the rubric criterion and scores 1-5 with a reason.
Requires `ANTHROPIC_API_KEY`; skipped gracefully if absent.

### 7. Spoken, first-person tone — `judge`, weight 1.0
SKILL.md: "First person, spoken language. Every script is something the
candidate would actually say out loud — contractions, natural rhythm, no
jargon they wouldn't use in conversation."
**5:** reads like natural speech throughout. **1:** reads like a written
document (formal connectors, no contractions, list-like phrasing).

### 8. Honesty calibration — `judge`, weight 1.5
SKILL.md: "Never write a script that implies expertise the candidate doesn't
have ... honest framing wins more trust than overclaiming." This is the
highest-weighted judged dimension because it's the skill's core promise.
**5:** gap-area answers state plainly what the candidate does and doesn't
have, then redirect to a real adjacent strength. **1:** any answer that
inflates or implies unearned expertise. Overclaims are quoted in the report.

### 9. Attribution integrity — `judge`, weight 1.0
SKILL.md: "Distinguish 'I did X' from 'my team did X' ... Don't quietly claim
it as the candidate's."
**5:** individual vs team contributions are kept distinct. **1:** team or
other-people's work is silently claimed in the first person.

---

## Headline score

Weighted mean of all dimensions that ran, normalized to 0-100. Code dimensions
contribute their pass-fraction (0-1); judged dimensions contribute (score-1)/4
(mapping 1-5 onto 0-1). A dimension that can't run (e.g. judge with no API key,
or talk-time with no detectable scripts) is excluded from the mean and noted.

A run is considered **passing** at >= 85 with **no hard failures**. Hard
failures are dimensions 1 (em dashes) and 5 (nav integrity): they're binary
correctness issues, not matters of degree, so any failure there fails the run
regardless of the headline number.
