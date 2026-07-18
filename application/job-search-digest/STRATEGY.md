# Strategy — Visa-Sponsorship Job Digest

Companion to `SERVICE_PLAN.md`. That file records *how* the service is built (design
decisions D1–D12). This file records *why* it exists, *who* it's for, and *how* it goes
to market — the context that would otherwise live only in conversation.

---

## The goal (what success actually means here)

This is not a venture play. The goals, in order:

1. **Credibility** — a real, shipped, documented product that shows I can conceive, build,
   and reason about a system end to end.
2. **Personal brand** — become known for something concrete and useful.
3. **Get in front of companies** — a memorable calling card in conversations/interviews.
4. **Get users** — a real (even small) user base is stronger proof than a solo project, and
   the signup list is the audience for a future launch.

Implication: optimize for **shipping + a sharp story + rigor**, not user count or beating
incumbents. A polished repo + one working thing + a good writeup beats a half-built platform.

---

## Target audience

**International students and workers who need visa sponsorship** — primarily **F-1/OPT**
students looking ahead to the **H-1B** path, plus current H-1B seekers. Acute, recurring pain:
most job boards don't surface whether an employer sponsors, so they waste enormous effort on
roles that were never open to them.

Distribution is concentrated and word-of-mouth: university international-student offices,
r/f1visa / r/h1b, OPT WhatsApp/Discord groups. Niches share *sharp* tools — which is why
focus matters.

---

## Competitive landscape (why we pivoted)

**General daily-digest space is a red ocean.** Direct free/mature competitors already do the
generic version, often with more coverage than we could match:

- **OpenJobRadar** — free, no tier gates, monitors 15+ ATS platforms, daily email digest.
- **FirstPost** — 150k+ companies, career-page alerts, free starter + paid Pro.
- **Scoutify** — 10k+ career pages, alerts from ~$5/wk, auto-apply.
- Plus open-source clones (job-board-aggregator, etc.) and Apify actors.

**What none of them do well:** the full lifecycle (find → prep → negotiate), AI-grade reasoning,
and — critically — **visa sponsorship filtering.** That gap is the wedge.

**Decision:** don't compete on the generic digest. Reposition around **visa sponsorship**
(see `SERVICE_PLAN.md` D12), where the pain is high and the field is thin.

---

## Positioning

**Full pivot at the positioning layer; zero waste at the engineering layer.** The engine
(fetch → pool → filter → dedup → seen-set → liveness → email) is unchanged — sponsorship is
filters + tags on top. So we keep the general capability internally but **market only to visa
holders**, with one sharp line: *"New jobs at companies that sponsor visas — in your inbox."*

Rejected: "sponsorship as a mode/toggle." It's a marketing hedge that buys nothing (same code)
while diluting the sharp identity that drives word-of-mouth.

---

## The honesty bar (non-negotiable — high stakes)

Users make life decisions on this. Therefore:

- Sponsorship is a **company-level history, not a job-level guarantee.** Tag *"Has sponsored
  H-1B (2023–25)"* — never *"this job sponsors."*
- Pair with a reliable **job-level negative filter**: exclude roles whose text says "no
  sponsorship / must be authorized without sponsorship / US citizen / security clearance."
- Same principle as the salary chip (D9): defer to the source, label honestly, never overclaim.

---

## Phased plan

- **Phase 1 (built):** working general engine, dogfooded to one inbox, daily cron, documented.
- **Phase 1.5 (now):** add the sponsorship signal — sponsor dataset + JD negative-filter +
  sponsorship chip + reframed signup. Re-dogfood.
- **Phase 2:** waitlist/signup page (the launch-audience asset), verified sending domain
  (branded sender + click tracking, D8), more sponsoring-employer boards.
- **Launch:** a writeup + the LinkedIn **new-job announcement** as the hook — pointing at the
  working demo + waitlist.

**Launch timing constraint:** the LinkedIn announcement is held until a separate active
interview resolves (announcing a role publicly while interviewing elsewhere can hurt the other
process). The build proceeds regardless; only the public post waits. Don't let it slip months —
the "just started" hook goes stale.

---

## Legal & compliance guardrails (required before public signup)

Not legal advice — a working checklist of self-imposed rules. The theme: this is an
*informational* tool; never let it look like a guarantee or advice service.

1. **Disclaimer, visible on the page and in every email:** informational only; not
   immigration or legal advice; sponsorship history ≠ a guarantee any employer will sponsor
   any role; verify with the employer. (Extends the D12 honesty rule.)
2. **Never give individual visa advice** in emails, replies, or communities — that edges
   toward unauthorized practice of immigration law. Point people to attorneys / DSOs.
3. **CAN-SPAM (mandatory once anyone but the operator receives email):** working
   unsubscribe honored promptly, valid physical mailing address in the footer, truthful
   subject lines. Unsubscribe is a Phase-2 hard requirement, not a nice-to-have.
4. **Privacy:** collect only email + preferences; simple privacy policy (what we collect,
   what we send, never sell); delete on request; emails stay hashed in any public state.
5. **Data sources:** USCIS/DOL data is public-domain government data. ATS endpoints are
   public, unauthenticated feeds companies publish for job distribution — we link *to* their
   postings. If a company asks to be removed, remove them.
6. **Naming:** avoid anything confusable with incumbents (H1BVisaJobs, MyVisaJobs).
7. **Gates that require a professional:** (a) the operator's own visa status vs. running or
   monetizing a side project — check with an immigration attorney if applicable; (b) any
   monetization → revisit structure (LLC) and terms with a lawyer first.

## Open questions

- Sponsor dataset: USCIS Employer Data Hub vs DOL LCA disclosure — freshness vs granularity.
- How to match messy employer names in the visa data to ATS company slugs.
- Signup: no-login (email only) vs lightweight accounts.
- Whether to surface sponsorship *strength* (volume of past sponsorships) or just yes/no.
