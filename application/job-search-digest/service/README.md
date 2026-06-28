# Digest Service

The hosted, auto-sending, multi-user implementation of the Job Search Digest.
Derived from the skill's spec (`../SKILL.md`) and graded by the same eval
(`../eval/`). Design and decisions live in `../SERVICE_PLAN.md`.

> **Status: Phase 1 — building for one real inbox.** Multi-user signup is Phase 2
> and intentionally not started yet.

## Layout

```
service/
├── README.md      ← this file
├── boards.json    ← curated company boards (the service's reach; D1)
└── digest.py      ← engine: fetch boards once → pool → dedup → filter → render
```

## Run (current prototype)

```bash
python3 digest.py
```

Fetches every board in `boards.json` once into a shared, deduped pool, then prints
a filtered digest per sample user. No API key, no cost.

## Build status (per SERVICE_PLAN.md)

- [x] Fetch free ATS APIs (Greenhouse / Ashby / Lever) — validated, 1,176 jobs
- [x] Fetch once, filter per user (batching)
- [x] **Step 1** — tighten filter: word-boundary role match + freshness sort
- [x] **Step 2** — per-user "already-sent" seen-set (D4)
- [x] **Step 3** — auto-send via Resend (D5) — *code done; set `RESEND_API_KEY` to send*
- [x] **Step 4** — nightly cron via GitHub Actions (D6, D11) — *needs `RESEND_API_KEY` repo secret*
- [ ] **Step 5** — one-page signup form (Phase 2)
- [ ] **Step 6** — expand curated board list (with liveness check)
