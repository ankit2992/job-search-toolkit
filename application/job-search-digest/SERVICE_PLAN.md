# Job Search Digest — Free Multi-User Service Plan

This document plans the evolution of the digest from a **single-user Claude skill**
(interview → search → email *draft*) into a **free, hosted, multi-user service** that
anyone non-technical can sign up for and that **sends real emails automatically**.

It also records the design decisions behind that evolution, so the *why* is captured
alongside the *what* — same principle as the rest of this repo.

---

## Goals (what changed)

| Dimension | Skill (today) | Service (target) |
|---|---|---|
| Audience | Technical / Claude users | **Anyone, non-technical** |
| Email | Creates a *draft*, can't send | **Auto-sends** |
| Users | One | **Many, batched** |
| Cost to operator | Apify (paid) + Claude tokens | **$0 on free tiers** (to ~100 daily users) |
| Trigger | Manual / Claude schedule | **Nightly cron, unattended** |

---

## Architecture (validated, not theoretical)

```
curated company boards
        │  (fetched ONCE per nightly run — cost scales with # boards, not # users)
        ▼
   shared job pool  ──►  in-run dedup  ──►  cached pool
        │
        ▼  (cheap, per user)
   for each user:  filter by criteria  ─►  remove already-sent  ─►  render  ─►  send
                                              ▲
                                       per-user "seen" set
```

**Prototype result (proven):** 5 boards (Greenhouse, Ashby, Lever) → **1,176 unique
jobs** fetched once with **no API key and no cost**, then served to 2 users with
different criteria (21 and 30 matches) **without re-fetching**. The scaling property
holds: a 100th user adds no fetch cost.

---

## Build steps (in order)

1. **Tighten the filter** — word-boundary role matching (so "engineer" ≠ "engineering
   manager") + freshness sort. Mirrors the `role-family precision` dimension already
   weighted highest in `eval/rubric.md`.
2. **Per-user "already-sent" memory** *(the dedup-across-days guard — see Decision 4)*.
3. **Auto-send** via Resend free tier (replaces the draft-only dead end).
4. **Nightly cron** via GitHub Actions (free for public repos).
5. **One-page signup form** (static host free tier) — the piece that delivers the
   "anyone can use it" goal.
6. **Expand the curated board list** — reach = number of company slugs we track.

---

## Decision Log

Each entry: the decision, the choice, why, and the tradeoff we accepted.

### D1 — Data source: free per-company ATS APIs, not a job-search API
- **Choice:** Pull directly from Greenhouse / Ashby / Lever public board APIs (no key, no cost).
- **Why:** Apify's LinkedIn scraper is paid and its trial expires — a day-one paywall for
  a "free for anyone" product. The ATS APIs are the *source* postings, often fresher than
  aggregators.
- **Tradeoff accepted:** These are **per-company**, not a global search. Coverage = the
  curated board list, not "the whole internet." We treat this as a feature (quality filter,
  not spray-and-pray), consistent with the project's philosophy.

### D2 — Filtering is code, not an LLM
- **Choice:** Role/location/seniority filtering and dedup run as plain code.
- **Why:** `eval/rubric.md` already establishes the digest is a *retrieval & precision*
  problem with checkable answers — "mostly code, essentially no taste component." Removing
  the LLM from the hot path is what makes the service genuinely $0 and fast.
- **Tradeoff accepted:** Fuzzy title matching is heuristic; near-miss titles need tuning
  rather than model judgment.

### D3 — Fetch once, filter per user (batching)
- **Choice:** One shared nightly fetch into a deduped pool; each user is a cheap in-memory
  filter over that pool.
- **Why:** Cost and rate limits scale with **number of boards**, not **number of users**.
  This is what keeps many users on free tiers.
- **Tradeoff accepted:** The pool must cover the *union* of all users' target boards, so
  fetch volume grows with board diversity (still deduped — each board fetched once).

### D4 — Dedup across days uses a per-user "seen" set, not a time window
- **Problem:** "Only show jobs from the last 24h" does **not** prevent repeats:
  - Greenhouse exposes `updated_at` (last *edited*), not posted time — an edit re-enters
    the 24h window and re-sends a job the user already saw.
  - Close-and-repost gives a job a new ID + new URL, so it looks brand new.
- **Choice:** After each send, store a per-user fingerprint of every job emailed; filter
  those out on the next run. The 24h window only bounds fetch size — the **seen set is the
  real no-repeat guarantee.**
- **Fingerprint key:** a normalized hash of `(company + cleaned title + location)` —
  **not** URL or job ID, because those change on a repost while the fingerprint stays
  stable. Expire entries after ~30–60 days so a genuinely re-opened role can resurface.
- **Tradeoff accepted:** Fuzzy keys can occasionally over-suppress two genuinely different
  roles with near-identical titles; location is included in the key to reduce this, and we
  bias toward "rather suppress a near-dup than spam a real dup." The seen set doubles as the
  user's history.

### D5 — Email send: Resend free tier
- **Choice:** Send transactional HTML via Resend (3,000 emails/month free).
- **Why:** The connected Gmail tooling is **draft-only** (no send capability), which is why
  the skill currently can't auto-send. Resend is purpose-built, has good deliverability, and
  the free tier ≈ 100 daily users.
- **Tradeoff accepted:** A third-party dependency; beyond ~3k/month it becomes paid. Keep
  the draft path as a fallback when no send key is configured.

### D6 — Scheduling: GitHub Actions cron
- **Choice:** Run the nightly job as a scheduled GitHub Action.
- **Why:** Free for public repos, no server to maintain, unattended (no human to click
  "send" — which is exactly why D5's auto-send is required).
- **Tradeoff accepted:** GitHub cron timing can drift by a few minutes; irrelevant because
  the seen set (D4), not exact timing, prevents repeats.

### D7 — One repo, scoped `service/` subfolder (don't split yet)
- **Choice:** The hosted service lives in this same repo under
  `application/job-search-digest/service/`, co-located with its spec (`SKILL.md`)
  and eval (`eval/`). The other two skills stay untouched in the repo.
- **Why:** The product's value is the *find → prep → negotiate* lifecycle as one story;
  splitting into thin repos discards that. The service is *derived from* the skill — the
  spec and eval apply to both. Secrets (Resend key, etc.) work as encrypted GitHub Actions
  secrets in a public repo, so nothing forces a split.
- **Split triggers (revisit only if one becomes true):** the service grows a separate
  frontend+backend with its own release cycle; the service needs different visibility than
  the skills (one private, one public); or outside contributors need scoped access.
- **Tradeoff accepted:** A deployable app and a clean eval-driven showcase share one repo;
  the `service/` boundary keeps them from muddying each other.

### D8 — Engagement tracking: clicks via Resend webhook (Phase 2)
- **Choice:** When the service goes multi-user on a verified domain, enable **click**
  tracking through Resend and POST events to a small webhook that stores them per user
  (tagged by user + role). **Opens are tracked but distrusted.**
- **Why:** Click data shows which roles/companies actually resonate — useful for engagement
  and the launch writeup. Resend provides open/click tracking + event webhooks built-in, so
  we don't build pixels/redirects ourselves.
- **Tradeoff accepted:** Open rates are polluted by Apple Mail Privacy Protection and image
  blocking, so they're directional at best — clicks are the trustworthy signal. Requires a
  verified sending domain (not the test sender). **Not built in Phase 1 (no users to measure).**

### D9 — Salary: show the source's own summary, flag when it varies, silent when absent
- **Choice:** Display **base salary only** from **structured** API fields, never total comp.
  For Ashby we read only `compensationType == "Salary"` components (`minValue`/`maxValue`)
  and deliberately **exclude `EquityCashValue`, bonus, and commission**; Lever's `salaryRange`
  is base by nature. The chip is labelled "base" so it can't be misread as total comp. Render
  **only when data exists**; when a company has geographic zones (multiple base tiers), show
  the overall span + "varies by location" rather than picking one number.
- **Why:** A wrong salary is worse than none for a credibility tool. The source already
  computes an honest summary across zones — we defer to it and let the posting be the source
  of truth (same principle as the comp-comparator skill).
- **Tradeoff accepted:** Coverage is partial — strong on Ashby, sparse on Lever, **none on
  Greenhouse** (no structured field; we deliberately do *not* parse description free-text,
  which is fragile and bloats fetches). We do **not** resolve the user's specific zone — the
  API doesn't reliably geo-label tiers, so a guess would be false precision.

### D10 — Link trust: provenance by design + a liveness check for staleness
- **Provenance:** Every apply link comes directly from the company's own first-party ATS API
  (Greenhouse/Ashby/Lever) over HTTPS — no aggregator, scraper, or user-submitted link in the
  path. So "is it what it says it is?" is answered by construction: no spoofing surface (D1).
- **Broken links:** Re-fetching the full board each run means the pool only holds currently-open
  roles. To catch roles that close between fetch and click, a **liveness check** HEAD/GETs each
  shown URL once (pool-level, shared across users) and drops definitive 404/410s.
- **Tradeoff accepted:** A flaky check must never delete a real posting, so we drop **only** on
  definitive "gone" codes and keep on any error/block/timeout. This means **soft-404s** (200
  "position closed" pages) still slip through — liveness is a guard, not a guarantee. Toggle via
  `JOBDIGEST_LIVENESS=0`.

### D11 — Scheduling + state persistence on ephemeral runners
- **Choice:** A GitHub Actions cron (`.github/workflows/digest.yml`) runs the digest daily and
  on-demand. Because runners are ephemeral, the seen-set is **committed back to the repo** after
  each run so D4's no-repeat guarantee survives across days.
- **Privacy:** The seen-set is keyed by a **hash of the email**, never the raw address, so the
  committed state carries no PII even in a public repo.
- **Tradeoff accepted:** Daily auto-commits add noise to history (`[skip ci]` keeps them from
  re-triggering). This is a Phase-1 dogfood mechanism; a real multi-user version (Phase 2) would
  move state to a database instead of the repo. Cron fires in UTC, so the local send time shifts
  an hour with daylight saving.

---

## Where the free tier ends (honesty about scale)

- **Resend:** 3,000 emails/month ≈ 100 daily users. Beyond that, batch delivery + paid plan.
- **Fetch volume:** grows with board *diversity*, not user count.
- **Reach:** limited to curated boards — no free global job search exists.

For a personal project or a modest user base: **genuinely $0.**

---

## Open questions / next to spitball

- How are company boards curated — fixed list, user-suggested, or auto-discovered?
- Signup form: no-login (email-only) vs. a lightweight account?
- Unsubscribe / edit-criteria flow (needed before any real users).
