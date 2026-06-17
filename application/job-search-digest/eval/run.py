#!/usr/bin/env python3
"""
run.py — eval runner for the job search digest.

Takes one or more digest run records (JSON: criteria + returned jobs), runs
every rubric dimension, and prints a scored report with a 0-100 headline and a
pass/fail verdict.

This tool is graded almost entirely by objective code checks (precision, dedup,
seniority/location filtering, URL validity). One optional LLM dimension exists
only to double-check fuzzy title matches and is skipped without an API key.
Exit code is 0 if all records pass, else 1.

    python3 run.py ../examples/example-digest.json
    python3 run.py --no-judge record.json
    python3 run.py --json record.json
"""

import argparse
import json
import os
import re
import sys
import urllib.request

import parse

PASS_THRESHOLD = 85.0
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "claude-sonnet-4-6")

OVER_LEVEL = re.compile(
    r"\b(director|vp|vice president|head of|group manager|chief|svp|cto|cpo)\b", re.I)
TARGET_LEVELS = {"director", "vp", "head", "executive", "principal-leadership"}
NON_US_REMOTE = re.compile(r"\b(emea|latam|apac|europe|india|uk only|canada only)\b", re.I)
URL_OK = re.compile(r"^https?://[^\s/]+\.[^\s/]+", re.I)


class Dim:
    def __init__(self, key, label, kind, weight, hard=False):
        self.key, self.label, self.kind, self.weight, self.hard = key, label, kind, weight, hard
        self.ran, self.score, self.hard_fail, self.detail = False, None, False, ""

    def set(self, score, detail):
        self.score, self.detail, self.ran = score, detail, True
        if self.hard and score is not None and score < 1.0:
            self.hard_fail = True
        return self

    def skip(self, reason):
        self.ran, self.detail = False, reason
        return self


def dim_cap(rec):
    d = Dim("cap", "Result cap respected", "code", 1.0)
    n = len(rec.jobs)
    return d.set(1.0 if n <= 30 else 0.0, f"{n} jobs (cap 30)")


def dim_dedup(rec):
    d = Dim("dedup", "Deduplication", "code", 1.5, hard=True)
    seen_key, seen_url, dupes = {}, {}, []
    for j in rec.jobs:
        key = (parse.normalize_company(j.get("company")), parse.normalize_title(j.get("title")))
        if key in seen_key:
            dupes.append(f"{j.get('company')} / {j.get('title')}")
        seen_key[key] = True
        u = (j.get("url") or "").strip().lower()
        if u and u in seen_url:
            dupes.append(f"url {u}")
        seen_url[u] = True
    if not dupes:
        return d.set(1.0, "no duplicates")
    return d.set(0.0, "duplicates: " + "; ".join(dupes))


def dim_schema(rec):
    d = Dim("schema", "Schema completeness", "code", 1.0, hard=True)
    if not rec.jobs:
        return d.skip("no jobs in record")
    bad = []
    for j in rec.jobs:
        missing = [f for f in parse.REQUIRED_FIELDS if not str(j.get(f, "")).strip()]
        if missing:
            bad.append(f"{j.get('title', '?')}: missing {','.join(missing)}")
    passed = len(rec.jobs) - len(bad)
    detail = f"{passed}/{len(rec.jobs)} jobs complete"
    if bad:
        detail += "; " + " | ".join(bad[:3])
    return d.set(passed / len(rec.jobs), detail)


def dim_urls(rec):
    d = Dim("urls", "URL validity", "code", 1.0)
    if not rec.jobs:
        return d.skip("no jobs")
    bad = [j.get("url", "") for j in rec.jobs if not URL_OK.match((j.get("url") or "").strip())]
    passed = len(rec.jobs) - len(bad)
    detail = f"{passed}/{len(rec.jobs)} URLs well-formed"
    if bad:
        detail += "; malformed: " + ", ".join(b or "(empty)" for b in bad[:3])
    return d.set(passed / len(rec.jobs), detail)


def dim_seniority(rec):
    d = Dim("seniority", "Seniority filter adherence", "code", 1.5)
    if not rec.jobs:
        return d.skip("no jobs")
    targeting_leadership = any(
        lvl.lower() in TARGET_LEVELS for lvl in rec.criteria.get("seniority", []))
    leaked = [j.get("title") for j in rec.jobs
              if OVER_LEVEL.search(j.get("title", "")) and not targeting_leadership]
    passed = len(rec.jobs) - len(leaked)
    detail = f"{passed}/{len(rec.jobs)} within requested seniority"
    if leaked:
        detail += "; over-level: " + ", ".join(leaked)
    return d.set(passed / len(rec.jobs), detail)


def dim_location(rec):
    d = Dim("location", "Location adherence", "code", 1.5)
    if not rec.jobs:
        return d.skip("no jobs")
    wanted = [w.lower() for w in rec.criteria.get("locations", [])]
    remote_wanted = any("remote" in w for w in wanted)
    cities = [w for w in wanted if "remote" not in w]
    off = []
    for j in rec.jobs:
        loc = (j.get("location") or "").lower()
        if NON_US_REMOTE.search(loc):
            off.append(j.get("location")); continue
        is_remote = "remote" in loc
        matches_city = any(c.split(",")[0] in loc for c in cities)
        if not ((is_remote and remote_wanted) or matches_city):
            off.append(j.get("location"))
    passed = len(rec.jobs) - len(off)
    detail = f"{passed}/{len(rec.jobs)} in-region"
    if off:
        detail += "; off-location: " + ", ".join(off)
    return d.set(passed / len(rec.jobs), detail)


def dim_role_precision(rec):
    d = Dim("role_precision", "Role-family precision", "code", 2.0)
    if not rec.jobs:
        return d.skip("no jobs")
    families = [parse.normalize_title(f) for f in rec.criteria.get("role_families", [])]
    if not families:
        return d.skip("no role families in criteria")
    off = []
    for j in rec.jobs:
        norm = parse.normalize_title(j.get("title"))
        # contiguous-phrase match against any requested family
        full = (j.get("title") or "").lower()
        if not any(fam and fam in re.sub(r"[^\w\s]", " ", full) for fam in families):
            off.append(j.get("title"))
    passed = len(rec.jobs) - len(off)
    detail = f"{passed}/{len(rec.jobs)} on-target"
    if off:
        detail += "; off-target: " + ", ".join(off)
    return d.set(passed / len(rec.jobs), detail)


def dim_relevance_judge(rec, enabled):
    d = Dim("relevance_judge", "Relevance review", "judge", 1.0)
    if not enabled:
        return d.skip("judging disabled (--no-judge)")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return d.skip("ANTHROPIC_API_KEY not set")
    if not rec.jobs:
        return d.skip("no jobs")
    titles = "\n".join(f"- {j.get('title')}" for j in rec.jobs)
    fams = ", ".join(rec.criteria.get("role_families", []))
    desc = (f"The user is searching for these role families: {fams}.\n"
            "Of the returned job titles below, how well do they match? "
            "5 = every title is the right kind of role. 1 = many are off-target "
            "(e.g. marketing/sales/leadership roles when an IC/PM role was asked for).\n\n"
            f"TITLES:\n{titles}")
    try:
        key = os.environ["ANTHROPIC_API_KEY"]
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps({"model": JUDGE_MODEL, "max_tokens": 400,
                             "messages": [{"role": "user", "content":
                                           desc + '\n\nRespond ONLY with JSON: '
                                           '{"score": <1-5 int>, "reason": "<one sentence>"}'}]}).encode(),
            headers={"content-type": "application/json", "x-api-key": key,
                     "anthropic-version": "2023-06-01"}, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        obj = json.loads(text.replace("```json", "").replace("```", "").strip())
        s = max(1, min(5, int(obj["score"])))
        return d.set((s - 1) / 4.0, f"{s}/5 — {obj.get('reason', '')}")
    except Exception as e:  # noqa: BLE001
        return d.skip(f"judge error: {e}")


def evaluate(path, use_judge):
    rec = parse.load(path)
    dims = [dim_cap(rec), dim_dedup(rec), dim_schema(rec), dim_urls(rec),
            dim_seniority(rec), dim_location(rec), dim_role_precision(rec),
            dim_relevance_judge(rec, use_judge)]
    ran = [d for d in dims if d.ran]
    headline = (sum(d.score * d.weight for d in ran) / sum(d.weight for d in ran) * 100) if ran else 0.0
    hard_failed = any(d.hard_fail for d in dims)
    return rec, dims, headline, hard_failed, (headline >= PASS_THRESHOLD and not hard_failed)


def print_report(path, rec, dims, headline, hard_failed, passed):
    print(f"\n\033[1m{path}\033[0m")
    print(f"  asked for: {', '.join(rec.criteria.get('role_families', []))}  "
          f"in {', '.join(rec.criteria.get('locations', []))}  |  {len(rec.jobs)} jobs returned")
    print("  " + "-" * 66)
    for d in dims:
        if not d.ran:
            mark, col = "skip", "\033[90m"
        elif d.hard_fail:
            mark, col = "FAIL", "\033[91m"
        elif d.score >= 0.999:
            mark, col = "pass", "\033[92m"
        elif d.score >= 0.5:
            mark, col = f"{d.score:.0%}", "\033[93m"
        else:
            mark, col = f"{d.score:.0%}", "\033[91m"
        print(f"  {col}{mark:>5}\033[0m {' *' if d.hard else '  '} {d.label:<28} {d.kind:<5} w{d.weight}")
        if d.detail:
            print(f"          \033[90m{d.detail}\033[0m")
    print("  " + "-" * 66)
    verdict = "\033[92mPASS\033[0m" if passed else "\033[91mFAIL\033[0m"
    print(f"  HEADLINE: \033[1m{headline:.1f}\033[0m / 100   (pass >= {PASS_THRESHOLD:.0f}, no hard fails)   ->  {verdict}")
    if hard_failed:
        print("  \033[91mhard failure present (* dimension)\033[0m")


def main():
    ap = argparse.ArgumentParser(description="Eval runner for job search digests.")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    all_passed, results = True, []
    for path in args.files:
        rec, dims, headline, hard_failed, passed = evaluate(path, not args.no_judge)
        all_passed = all_passed and passed
        if args.json:
            results.append({"file": path, "headline": round(headline, 1), "passed": passed,
                            "hard_failure": hard_failed,
                            "dimensions": [{"key": d.key, "label": d.label, "kind": d.kind,
                                            "weight": d.weight, "ran": d.ran,
                                            "score": None if d.score is None else round(d.score, 3),
                                            "hard_fail": d.hard_fail, "detail": d.detail} for d in dims]})
        else:
            print_report(path, rec, dims, headline, hard_failed, passed)
    if args.json:
        print(json.dumps(results, indent=2))
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
