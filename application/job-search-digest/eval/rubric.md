# Job Search Digest — Eval Rubric

The digest is a *retrieval and filtering* tool. Its quality is almost entirely
about precision and rule-adherence: did it return only roles that match the
request, drop the wrong seniority, drop the wrong locations, remove duplicates,
and stay within the cap. Those are objective, so this eval is **mostly code,
with essentially no "taste" component** — the opposite end of the spectrum from
the cheat-sheet eval. One optional LLM dimension exists only to double-check
fuzzy title matches; the tool can be meaningfully graded without it.

The eval consumes a **run record**: a small JSON file containing the criteria
the user gave plus the jobs the skill returned. You need both, because you
can't judge whether a result is "relevant" without knowing what was asked for.
The digest skill should log this record per run (one small addition to Step 4),
which is good eval hygiene regardless.

Each dimension has a **type** and **weight**.

---

## Code-checked dimensions

### 1. Result cap respected — `code`, weight 1.0
SKILL.md Step 4: "Cap at 30 results total."
**Pass:** the record contains at most 30 jobs.

### 2. Deduplication — `code`, weight 1.5, HARD
SKILL.md: "Deduplicate by (company + normalized title) and by URL."
**Pass:** no two jobs share a normalized (company, title) key, and no two
share a URL. Duplicates are listed.

### 3. Schema completeness — `code`, weight 1.0, HARD
SKILL.md Step 4 lists required fields per job (title, company, location,
posted_date, url, source, role_family, snippet).
**Score:** fraction of jobs with every required field present and non-empty.

### 4. URL validity — `code`, weight 1.0
A digest whose links don't work is useless.
**Score:** fraction of URLs that are well-formed (http/https scheme + a
domain). Malformed links are listed.

### 5. Seniority filter adherence — `code`, weight 1.5
SKILL.md: "Drop Director, VP, Head-of, Group Manager titles ... unless the
user is targeting those levels."
**Score:** fraction of jobs whose title level is within the requested
seniority. Over-level titles that leaked through are listed.

### 6. Location adherence — `code`, weight 1.5
SKILL.md: "Drop roles that are clearly outside the user's locations (e.g.
EMEA-only remote, LATAM-only)." Remote means US-based remote only.
**Score:** fraction of jobs whose location matches a requested location and
isn't a non-US remote region. Offenders are listed.

### 7. Role-family precision — `code`, weight 2.0
The core metric of a search digest: are the returned titles actually the
roles that were asked for? Highest weight because it's the whole point.
A title is on-target if it contains a requested role family as a contiguous
phrase (after light normalization). This is a heuristic — it deliberately
treats "Product Marketing Manager" as *not* a "Product Manager," which is the
kind of near-miss a sloppy filter lets through.
**Score:** fraction of jobs on-target. Off-target titles are listed.

---

## Optional LLM-judged dimension

Requires `ANTHROPIC_API_KEY`; skipped gracefully without it. The tool does not
need this to be graded — it exists only to catch fuzzy title mismatches the
contiguous-phrase heuristic in dimension 7 might get wrong in either direction.

### 8. Relevance review — `judge`, weight 1.0
The judge sees the requested role families and the returned titles and reports
how many are genuinely the right kind of role.
**5:** every title is a true match. **1:** many off-target titles slipped in.

---

## Headline score

Weighted mean of dimensions that ran, normalized to 0-100. Hard gates:
deduplication and schema completeness. A run passes at **>= 85 with no hard
failures.**
