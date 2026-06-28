#!/usr/bin/env python3
"""
Job Search Digest — service engine (Phase 1).

Pipeline (see ../SERVICE_PLAN.md):
  boards.json -> fetch each board ONCE -> shared pool -> in-run dedup
  -> per-user filter (word-boundary role match, seniority, location, freshness sort)
  -> remove already-sent (per-user seen set, D4) -> render

No API key, no paid dependency. Stdlib only.

Run: python3 digest.py
"""
import json, re, os, hashlib, datetime, urllib.request, urllib.error, concurrent.futures
from pathlib import Path

HERE = Path(__file__).parent
STATE_DIR = HERE / "state"
SEEN_FILE = STATE_DIR / "seen.json"
SEEN_TTL_DAYS = 60          # a re-opened role can resurface after this (D4)
UA = {"User-Agent": "job-search-digest/0.1 (+github.com/ankit2992/job-search-toolkit)"}

# Resend: key comes from the environment ONLY — never hardcode (D5).
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
# `or` (not a default arg): a GitHub secret that isn't set arrives as "" not missing.
RESEND_FROM = os.environ.get("RESEND_FROM") or "onboarding@resend.dev"

# --------------------------------------------------------------------------
# Fetch + normalize: each ATS -> common job shape
# --------------------------------------------------------------------------
def _get_json(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=15) as r:
            return json.load(r)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError, ValueError) as e:
        print(f"   ! skip {url}: {e}")
        return None

def _parse_dt(s):
    """Best-effort ISO parse -> aware UTC datetime; unknown -> epoch (sorts last)."""
    if not s:
        return datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    try:
        dt = datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        return datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)

# Salary is BASE only (D9) — never blends equity/bonus/commission, never misleads.
CUR = {"USD": "$", "GBP": "£", "EUR": "€", "CAD": "C$", "AUD": "A$"}

def _amt(n, sym):
    if not n:
        return ""
    return f"{sym}{round(n / 1000)}K" if n >= 1000 else f"{sym}{int(n)}"

def _range(lo, hi, sym):
    return f"{_amt(lo, sym)} – {_amt(hi, sym)}" if lo and hi else (_amt(lo or hi, sym))

def _ashby_base_salary(comp):
    """Pull ONLY compensationType=='Salary' components; ignore equity/bonus. Returns (str, varies)."""
    salary_comps = [c for t in (comp.get("compensationTiers") or [])
                    for c in (t.get("components") or [])
                    if c.get("compensationType") == "Salary"]
    mins = [c["minValue"] for c in salary_comps if c.get("minValue")]
    maxs = [c["maxValue"] for c in salary_comps if c.get("maxValue")]
    if not mins and not maxs:
        return "", False
    sym = CUR.get((salary_comps[0].get("currencyCode") if salary_comps else "USD"), "$")
    varies = len(salary_comps) > 1                       # multiple base tiers = zoned pay
    return _range(min(mins) if mins else None, max(maxs) if maxs else None, sym), varies

def fetch_greenhouse(slug):
    # Greenhouse exposes no structured salary field (D9) -> salary left blank.
    d = _get_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=false")
    return [dict(company=slug, title=j.get("title", ""),
                 location=(j.get("location") or {}).get("name", ""),
                 url=j.get("absolute_url", ""), updated=j.get("updated_at", ""),
                 salary="", salary_varies=False, source="greenhouse")
            for j in (d or {}).get("jobs", [])]

def fetch_ashby(slug):
    d = _get_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true")
    out = []
    for j in (d or {}).get("jobs", []):
        show = j.get("shouldDisplayCompensationOnJobPostings", True)
        salary, varies = _ashby_base_salary(j.get("compensation") or {}) if show else ("", False)
        out.append(dict(company=slug, title=j.get("title", ""),
                        location=j.get("location", "") or ("Remote" if j.get("isRemote") else ""),
                        url=j.get("jobUrl") or j.get("applyUrl", ""), updated=j.get("publishedAt", ""),
                        salary=salary, salary_varies=varies, source="ashby"))
    return out

def fetch_lever(slug):
    out = []
    for j in (_get_json(f"https://api.lever.co/v0/postings/{slug}?mode=json") or []):
        ts = j.get("createdAt")
        rng = j.get("salaryRange") or {}                  # Lever's salaryRange is base salary
        sym = CUR.get(rng.get("currency", "USD"), "$")
        out.append(dict(company=slug, title=j.get("text", ""),
                        location=(j.get("categories") or {}).get("location", ""),
                        url=j.get("hostedUrl", ""),
                        updated=datetime.datetime.fromtimestamp(ts / 1000, datetime.timezone.utc).isoformat() if ts else "",
                        salary=_range(rng.get("min"), rng.get("max"), sym), salary_varies=False,
                        source="lever"))
    return out

FETCHERS = {"greenhouse": fetch_greenhouse, "ashby": fetch_ashby, "lever": fetch_lever}

# --------------------------------------------------------------------------
# Normalization + identity (D4: fingerprint, not URL/ID)
# --------------------------------------------------------------------------
SENIORITY_PREFIX = re.compile(r"\b(sr|snr|senior|staff|principal|lead|junior|jr|mid|entry)\b\.?", re.I)

def _norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())).strip()

def _norm_title(t):
    # collapse "Sr." vs "Senior" so reposts/edits map to the same fingerprint
    return re.sub(r"\s+", " ", SENIORITY_PREFIX.sub("", _norm(t))).strip()

def fingerprint(job):
    key = f"{_norm(job['company'])}|{_norm_title(job['title'])}|{_norm(job['location'])}"
    return hashlib.sha1(key.encode()).hexdigest()[:16]

# --------------------------------------------------------------------------
# Fetch ALL boards ONCE -> shared deduped pool
# --------------------------------------------------------------------------
def build_pool(boards):
    pool, seen_url, seen_key = [], set(), set()
    print("Fetching boards (once, shared across all users):")
    for b in boards:
        jobs = FETCHERS[b["ats"]](b["slug"])
        print(f"   {b['ats']:10} {b['slug']:14} -> {len(jobs)} jobs")
        for j in jobs:
            fp = fingerprint(j)
            if not j["url"] or j["url"] in seen_url or fp in seen_key:
                continue
            seen_url.add(j["url"]); seen_key.add(fp)
            j["fp"] = fp
            j["ts"] = _parse_dt(j["updated"])
            pool.append(j)
    print(f"   => shared pool: {len(pool)} unique jobs\n")
    return pool

# --------------------------------------------------------------------------
# Step 1: per-user filter — word-boundary match, seniority, location, freshness
# --------------------------------------------------------------------------
SENIOR_DROP = re.compile(r"\b(director|vp|vice president|head of|chief|group manager)\b", re.I)

def _role_re(roles):
    # \b...\b so "engineer" does NOT match "engineering manager"
    return re.compile("|".join(rf"\b{re.escape(r.lower())}\b" for r in roles), re.I)

def match_user(pool, user):
    role_re = _role_re(user["roles"])
    locs = [l.lower() for l in user["locations"]]
    wants_remote = any("remote" in l for l in locs)
    needles = [l.replace("remote", "").strip() for l in locs if l.replace("remote", "").strip()]

    hits = []
    for j in pool:
        if not role_re.search(j["title"]):                          # role family (word-boundary)
            continue
        if not user.get("target_leadership") and SENIOR_DROP.search(j["title"]):
            continue                                                # seniority cutoff
        loc = j["location"].lower()
        if not (any(n in loc for n in needles) or (wants_remote and "remote" in loc)):
            continue                                                # location
        hits.append(j)

    hits.sort(key=lambda j: j["ts"], reverse=True)                  # freshness: newest first
    return hits[:30]                                                # cap

# --------------------------------------------------------------------------
# Step 2: per-user already-sent memory (D4)
# --------------------------------------------------------------------------
def _uid(email):
    # Key the seen-set by a hash, never the raw email, so persisted state carries no PII.
    return hashlib.sha1(email.lower().strip().encode()).hexdigest()[:16]

def load_seen():
    if SEEN_FILE.exists():
        return json.loads(SEEN_FILE.read_text())
    return {}

def save_seen(seen):
    STATE_DIR.mkdir(exist_ok=True)
    SEEN_FILE.write_text(json.dumps(seen, indent=2))

def filter_unseen(hits, seen_for_user):
    return [j for j in hits if j["fp"] not in seen_for_user]

def record_sent(seen, email, hits, today):
    uid = _uid(email)
    user_seen = seen.setdefault(uid, {})
    for j in hits:
        user_seen.setdefault(j["fp"], today)
    cutoff = (datetime.date.fromisoformat(today) - datetime.timedelta(days=SEEN_TTL_DAYS)).isoformat()
    seen[uid] = {fp: d for fp, d in user_seen.items() if d >= cutoff}   # expire old (D4)

# --------------------------------------------------------------------------
# Render (console for now; Step 3 swaps in Resend HTML email)
# --------------------------------------------------------------------------
def render(user, hits):
    print("=" * 70)
    print(f"DIGEST -> {user['email']}  |  {', '.join(user['roles'])}  @  {', '.join(user['locations'])}")
    print(f"{len(hits)} new roles (not previously sent)")
    print("-" * 70)
    for j in hits[:15]:
        when = j["updated"][:10] if j["updated"] else "-"
        print(f"  - {j['title'][:42]:42} {j['company']:12} {j['location'][:18]:18} {when}")
    if not hits:
        print("  (nothing new today)")
    print()

# --------------------------------------------------------------------------
# Step 3: HTML email + Resend send (D5). Key from env only.
# --------------------------------------------------------------------------
def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

ACCENT = "#4f46e5"        # <- change this one value to rebrand the email color
BRAND = "Job Digest"      # <- and this for the header label

def _company_name(slug):
    return slug.replace("-", " ").replace("_", " ").title()

def _salary_chip(j):
    if not j.get("salary"):
        return ""
    note = "base · varies by location" if j.get("salary_varies") else "base"
    return (
        f"<div style='margin-top:8px'>"
        f"<span style='display:inline-block;background:#ecfdf5;color:#047857;font-size:12px;"
        f"font-weight:700;padding:3px 9px;border-radius:6px'>{_esc(j['salary'])}</span>"
        f" &nbsp;<span style='color:#9ca3af;font-weight:400;font-size:12px'>{note}</span></div>"
    )

def _card(j):
    when = j["updated"][:10] if j["updated"] else ""
    meta = " &nbsp;·&nbsp; ".join(filter(None, [
        f"<b style='color:#374151'>{_esc(_company_name(j['company']))}</b>",
        _esc(j["location"]) or None,
        f"<span style='color:#9ca3af'>{when}</span>" if when else None,
    ]))
    return (
        f"<tr><td style='padding:16px 24px;border-bottom:1px solid #f0f0f2'>"
        f"<table role='presentation' width='100%' cellpadding='0' cellspacing='0'><tr>"
        f"<td style='vertical-align:top'>"
        f"<a href='{_esc(j['url'])}' style='font-size:16px;font-weight:600;color:#111827;"
        f"text-decoration:none;line-height:1.35'>{_esc(j['title'])}</a>"
        f"<div style='margin-top:5px;font-size:13px;color:#6b7280'>{meta}</div>"
        f"{_salary_chip(j)}"
        f"</td>"
        f"<td style='vertical-align:top;text-align:right;white-space:nowrap;padding-left:14px'>"
        f"<a href='{_esc(j['url'])}' style='display:inline-block;background:{ACCENT};color:#fff;"
        f"font-size:13px;font-weight:600;padding:8px 16px;border-radius:8px;text-decoration:none'>Apply &rarr;</a>"
        f"</td></tr></table></td></tr>"
    )

def render_html(user, hits):
    cards = "".join(_card(j) for j in hits) if hits else (
        "<tr><td style='padding:40px 24px;text-align:center;color:#9ca3af;font-size:14px'>"
        "No new roles since your last digest.</td></tr>")
    return (
        f"<div style='background:#f4f4f7;padding:24px 12px;font-family:-apple-system,BlinkMacSystemFont,"
        f"\"Segoe UI\",Roboto,Helvetica,Arial,sans-serif'>"
        f"<table role='presentation' width='100%' cellpadding='0' cellspacing='0' "
        f"style='max-width:600px;margin:0 auto;background:#fff;border-radius:14px;overflow:hidden;"
        f"box-shadow:0 1px 3px rgba(0,0,0,.08)'>"
        # header
        f"<tr><td style='padding:28px 24px 22px;border-bottom:3px solid {ACCENT}'>"
        f"<div style='font-size:12px;letter-spacing:1.5px;text-transform:uppercase;color:{ACCENT};"
        f"font-weight:700'>{BRAND}</div>"
        f"<div style='font-size:22px;font-weight:700;color:#111827;margin-top:6px'>"
        f"{len(hits)} new role{'s' if len(hits)!=1 else ''} for you</div>"
        f"<div style='color:#6b7280;font-size:14px;margin-top:4px'>"
        f"{_esc(', '.join(user['roles']))} &nbsp;·&nbsp; {_esc(', '.join(user['locations']))}</div>"
        f"</td></tr>"
        # cards
        f"{cards}"
        # footer
        f"<tr><td style='padding:20px 24px;color:#9ca3af;font-size:12px;line-height:1.5;background:#fafafa'>"
        f"Sourced directly from company career boards. You only see roles you haven&rsquo;t been sent before."
        f"</td></tr>"
        f"</table></div>"
    )

def send_email(to, subject, html):
    payload = json.dumps({"from": RESEND_FROM, "to": [to], "subject": subject, "html": html}).encode()
    req = urllib.request.Request(
        "https://api.resend.com/emails", data=payload, method="POST",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json",
                 # default Python-urllib UA gets Cloudflare-blocked (err 1010); look like a normal client
                 "User-Agent": "Mozilla/5.0 (compatible; job-search-digest/0.1)"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            print(f"   sent -> {to} (id {json.load(r).get('id', '?')})")
            return True
    except urllib.error.HTTPError as e:
        print(f"   ! send failed ({e.code}): {e.read().decode()[:200]}")
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"   ! send failed: {e}")
    return False

# --------------------------------------------------------------------------
# Liveness: drop links that are definitively gone (404/410). Provenance is
# already trustworthy (first-party ATS APIs) — this only guards against roles
# that closed since the fetch. Soft-404s (200 "closed" pages) slip past.
# --------------------------------------------------------------------------
LIVENESS_CHECK = os.environ.get("JOBDIGEST_LIVENESS", "1") != "0"
LIVENESS_TIMEOUT = 8
LIVENESS_WORKERS = 10
BROWSER_UA = "Mozilla/5.0 (compatible; job-search-digest/0.1)"

def _is_live(url):
    """False ONLY on a definitive 'gone' status. On any error/block: keep it
    (a flaky check must never delete a real posting)."""
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method, headers={"User-Agent": BROWSER_UA})
            with urllib.request.urlopen(req, timeout=LIVENESS_TIMEOUT) as r:
                return r.status < 400
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                return False                      # definitively gone
            if e.code in (403, 405, 429) and method == "HEAD":
                continue                          # HEAD blocked -> retry with GET
            return True                           # other codes: don't penalize
        except (urllib.error.URLError, TimeoutError, ValueError):
            return True                           # network hiccup: benefit of the doubt
    return True

def dead_links(urls):
    """Check each unique URL ONCE (pool-level, shared across users)."""
    if not LIVENESS_CHECK or not urls:
        return set()
    dead = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=LIVENESS_WORKERS) as ex:
        for url, live in zip(urls, ex.map(_is_live, urls)):
            if not live:
                dead.add(url)
    print(f"   liveness: checked {len(urls)} links, dropped {len(dead)} dead")
    return dead

# --------------------------------------------------------------------------
def main():
    boards = json.loads((HERE / "boards.json").read_text())["boards"]
    users = json.loads((HERE / "users.json").read_text())["users"]
    # Keep your real email out of the (public) repo: DIGEST_TO overrides the first user.
    if os.environ.get("DIGEST_TO") and users:
        users[0]["email"] = os.environ["DIGEST_TO"]
    today = datetime.date.today().isoformat()

    pool = build_pool(boards)                       # fetched ONCE
    seen = load_seen()
    sending = bool(RESEND_API_KEY)
    print(f"Email: {'Resend via ' + RESEND_FROM if sending else 'console only (set RESEND_API_KEY to send)'}\n")

    # Candidate hits per user (filtered + unseen), then liveness-check the
    # union of their URLs ONCE so each link is verified a single time.
    candidates = {u["email"]: filter_unseen(match_user(pool, u), seen.get(_uid(u["email"]), {})) for u in users}
    dead = dead_links(list({j["url"] for hits in candidates.values() for j in hits}))

    for u in users:                                 # reused per user
        hits = [j for j in candidates[u["email"]] if j["url"] not in dead]
        render(u, hits)
        delivered = True
        if sending and hits:
            subject = f"{u['roles'][0]} jobs - {today} - {len(hits)} new"
            delivered = send_email(u["email"], subject, render_html(u, hits))
        if delivered:                               # record only what reached the user (D4)
            record_sent(seen, u["email"], hits, today)
    save_seen(seen)

if __name__ == "__main__":
    main()
