---
name: job-search-digest
description: >
  Daily job search digest skill. Use this skill whenever a user wants to search for jobs, find new job postings, get a job digest emailed to them, or set up an automated daily job alert. Triggers on phrases like "find me jobs", "search for jobs", "set up a daily job search", "email me new postings", "I'm looking for work", "help me find a job", or any request to track job openings in a specific role or location. The skill interviews the user for their target role(s), location(s), seniority level, and email, then searches LinkedIn (via Apify) and Google/ATS job boards (via Apify RAG browser), assembles a clean HTML email digest, and sends it to their Gmail. It also explains how to schedule the search to run automatically every day.
---

# Job Search Digest

This skill finds fresh job postings for the user, builds a clean email digest, and optionally sets up a daily automated search so they never miss a new opening.

---

## Step 1 — Interview the user

Before searching, collect the following. Ask all at once in a single message so the user can answer everything together:

1. **Target role(s)** — What job titles are they looking for? (e.g. "Product Manager", "Data Engineer", "Scrum Master") Get 1–3 role families. If they're unsure, suggest common variations (Senior, Sr., Principal, Staff).
2. **Location(s)** — Which city/metro, and do they want Remote (US) results too? Common answers: "Boston", "New York", "Remote", "Boston + Remote".
3. **Seniority level** — Mid-level (3–5 yrs exp), Senior (5–8 yrs), or both?
4. **Industry focus** (optional) — Any preferred industries? e.g. AI/ML, Fintech, Healthcare, any. Defaults to "any" if they don't have a preference.
5. **Email address** — Where should the digest be sent?
6. **Schedule** — Do they want this to run automatically every day, or just run it once right now?

Don't proceed until you have at least roles, one location, and an email.

---

## Step 2 — Search LinkedIn via Apify

Use `mcp__Apify__call-actor` with actor `bebity/linkedin-jobs-scraper`.

**Important schema notes for this actor:**
- `experienceLevel` must be a single string: `"3"` = Associate/Mid, `"4"` = Mid-Senior. Run two passes if the user wants both levels.
- `workType`: `"2"` = Remote, omit for on-site/any
- `publishedAt`: `"r86400"` = past 24 hours, `"r604800"` = past week
- `rows`: 50

Run one call per (role family × location). For example, if the user wants "Product Manager" in Boston and Remote, that's 2 calls. Run them in parallel (all in the same tool-call block).

If the actor returns an error saying the trial has expired or the actor must be rented, skip LinkedIn entirely and note it in the email footer — don't block on it. Proceed to Step 3.

If a call returns a `defaultDatasetId`, fetch full results with `mcp__Apify__get-actor-output` (limit 100).

---

## Step 3 — Search Google/ATS boards via Apify RAG browser

Use `mcp__Apify__apify--rag-web-browser` with `maxResults: 5` per query.

Construct queries dynamically from the user's roles and locations. The ATS site cluster to include in every query:

```
(site:greenhouse.io OR site:lever.co OR site:jobs.lever.co OR site:ashbyhq.com OR site:myworkdayjobs.com OR site:apply.workable.com OR site:jobs.smartrecruiters.com OR site:jobs.icims.com OR site:jazzhr.com OR site:amazon.jobs OR site:careers.microsoft.com OR site:linkedin.com/jobs)
```

Query patterns (adapt to the user's actual roles and locations):

- `{ATS_CLUSTER} "{Role Title}" "{City}" when:1d`
- `{ATS_CLUSTER} "{Role Title}" "Remote" ("United States" OR "USA") when:1d`

If the user specified an industry focus (e.g. AI, Fintech), append relevant keywords to the query: `("AI" OR "ML" OR "LLM")` for AI, `("fintech" OR "payments" OR "banking")` for Fintech.

Run all queries in parallel. If a query returns zero results, drop the `when:1d` and retry once — Google sometimes ignores it when results are sparse.

---

## Step 4 — Aggregate and filter

Combine all results into a unified list. For each job, capture:

- **title** — job title as listed
- **company** — company name
- **location** — city/state or "Remote"
- **posted_date** — as shown (e.g. "1 hour ago", "2 days ago")
- **url** — direct link to the posting
- **source** — "LinkedIn" or "Google/ATS"
- **role_family** — map to one of the user's requested role families
- **industry_tag** — best-effort tag based on company name + snippet: tag as the user's preferred industry if keywords match, otherwise "Other". Leave blank if the user didn't specify an industry focus.
- **snippet** — ≤ 150 chars describing the role

Then apply these filters:
- Keep only roles that match one of the user's target role families (case-insensitive title match)
- Drop Director, VP, Head-of, Group Manager titles (unless the user is targeting those levels)
- Drop roles that are clearly outside the user's locations (e.g. EMEA-only remote, LATAM-only)
- Deduplicate by (company + normalized title) and by URL
- Cap at 30 results total; within each (location × role family) group, sort by posted_date ascending (freshest first), with industry-tagged results first if applicable

---

## Step 5 — Build and send the email digest

Use `mcp__5c2711f7-ce9b-491b-8ceb-8e55fc5d3b64__create_draft` to create the Gmail draft.

**Email structure:**
- **To:** the user's email
- **Subject:** `{Role Family 1} / {Role Family 2} Jobs Digest — {Locations} — {YYYY-MM-DD}`
- **HTML body:** two top-level sections ("Boston" and "Remote", or whatever locations the user chose), each with one sub-section per role family. Render each sub-section as a table: Company | Title | Industry (if applicable) | Posted | Apply. Each title should be a hyperlink. Include a header line above the tables: *"Found N new roles in the last 24 hours (X {Location 1} · Y {Location 2})"*. Add a small source attribution per row (LinkedIn / Google).
- **Plain-text body:** same content as a readable fallback.

If zero jobs are found across all searches, still send the email with subject suffix " — no new postings" and a one-line body saying no fresh roles were found.

After drafting, try to send using any available Gmail send tool. If no send tool is available, leave it as a draft and let the user know it's saved in their Drafts folder.

---

## Step 6 — Offer to schedule it daily (if the user said yes)

Use the `schedule` skill to set up a daily run. Explain to the user:

> "I can set this up to run automatically every morning. Just tell me what time you'd like to receive your daily digest (e.g. '8am Eastern'), and I'll schedule it for you."

When creating the scheduled task, the task instructions should include:
- The user's role families, locations, seniority, industry focus, and email — all pre-filled
- A note that this is an automated run (no user present to answer questions)
- The same Steps 2–5 workflow above

---

## Tips and edge cases

- **LinkedIn trial expired:** This is common. If the Apify LinkedIn scraper isn't available, rely entirely on the RAG browser searches and note the limitation in the email footer.
- **Sparse results:** If fewer than 5 jobs are found, widen the time window from `when:1d` to `when:7d` and note the change in the email header.
- **Multiple role families:** Run all searches in parallel to save time. Don't wait for one to finish before starting the next.
- **Remote vs. on-site:** "Remote" means US-based remote only. If a role says "Remote (EMEA)" or "Remote (LATAM)", drop it.
- **Time limit:** If any individual Apify call takes more than 2 minutes with no response, move on and use whatever data has been collected so far.
- **Privacy:** Only ever send the digest to the email the user provided. Never send to other addresses.
