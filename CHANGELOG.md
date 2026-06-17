# Changelog

## [Unreleased]

## 2026-06-17 — Eval harnesses

Added automated eval suites across all three tools. Each eval is matched to
how that specific tool fails, rather than using a one-size-fits-all approach:

- **Interview Cheat Sheet** — LLM-judged dimensions (spoken tone, honesty
  calibration, attribution integrity) plus code checks (em-dash gate,
  anchor-word discipline, pacing-cue budget, talk-time targets, nav integrity).
  Runs without an API key via `--no-judge`; exits non-zero for CI.

- **Comp Comparator** — arithmetic and rules checks: guaranteed total never
  includes discretionary components, risk clauses in the offer letter are
  recalled, no equity ask at a company that has none. Ships with a correct
  fixture (100/100) and a deliberately-flawed one (15/100) to demonstrate
  the eval discriminates rather than rubber-stamps.

- **Job Search Digest** — retrieval precision checks: deduplication, seniority
  and location filter adherence, URL validity, role-family precision. All
  objective — no LLM judge needed. Planted defects in the fixture catch
  duplicates, over-level titles, EMEA-only remotes, and off-target roles.

Also: strengthened `.gitignore` to block `.env` and `*.key` from being
accidentally committed; added data-privacy notice for API-judged runs.

## 2026-06-12 — Initial release

Launched three tools covering the full job search lifecycle:

- **Job Search Digest** (`application/`) — searches LinkedIn and ATS boards
  daily, deduplicates by company + normalized title, emails a filtered digest.
  Key design choices: adaptive search window when results are sparse,
  graceful fallback when a source is unavailable, privacy-scoped to one
  destination address.

- **Interview Cheat Sheet Generator** (`interview/`) — generates a
  single-file HTML prep sheet for a specific interview round: full
  first-person scripts, anchor-word memory aids, pacing cues, and
  honestly-calibrated gap answers. Used in a live hiring-manager loop
  during an active search.

- **Comp Comparator** (`negotiation/`) — compares offers against target comp,
  flags risky offer-letter language (verbal commitments, discretionary bonus
  clauses), and produces a sequenced negotiation plan. Ran on the final offer
  of a 4-month search; flagged a verbal bonus commitment as unconfirmed
  upside before signing.
