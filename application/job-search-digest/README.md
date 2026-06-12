# Job Search Digest

**Stage:** Application

A Claude skill that automates the daily grind of checking multiple job boards. It searches LinkedIn and ATS-hosted postings (Greenhouse, Lever, Ashby, Workday, etc.), filters and deduplicates results against your target roles, and emails a clean HTML digest. Optionally schedules itself to run every morning.

## The problem

Job searching means checking the same handful of sites every day, scanning for new postings that match your target roles, and ignoring the noise (wrong seniority, wrong location, duplicate listings across boards). Doing this manually, daily, across multiple role families and locations, is repetitive and easy to fall behind on.

## What it does

1. Interviews you once for target roles, locations, seniority, industry focus, and email
2. Searches LinkedIn (via Apify) and Google/ATS job boards (via an Apify RAG browser) in parallel
3. Aggregates results, tags them by role family and industry
4. Applies filters: role match, seniority cutoffs, location relevance, dedup by company + normalized title and by URL
5. Builds an HTML + plain-text email digest, grouped by location and role family
6. Sends via Gmail, or optionally schedules a daily run

## Design decisions

- **Dedup key is (company + normalized title), not just URL** — the same role often gets posted on both LinkedIn and the company's ATS with different URLs. Deduping only by URL would produce duplicates.
- **Graceful degradation on LinkedIn** — Apify's LinkedIn scraper actor has had trial/availability issues. Rather than failing the whole run, the skill detects the error and falls back to ATS/Google search only, noting the limitation in the email footer.
- **Adaptive time window** — searches start with `when:1d` (last 24 hours). If results are sparse (<5 jobs), it widens to `when:7d` and flags the change, rather than silently returning an empty digest.
- **Seniority filtering by title, not by request** — drops Director/VP/Head-of titles by default unless the user is explicitly targeting that level, since those postings tend to flood results for senior IC/manager searches.
- **Privacy guardrail** — the digest is only ever sent to the email address the user provided in the interview step, never to any address that might appear elsewhere.

## What I specified vs. what was generated

I defined the workflow steps, the filtering logic (dedup strategy, seniority cutoffs, location rules, fallback behavior), the ATS site cluster, and the email structure. Claude Code implemented the skill against those specifications.

## Status

Built and ready to use as part of an active job search.
