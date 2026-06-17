#!/usr/bin/env python3
"""
run.py — the eval runner for the interview cheat sheet generator.

It takes one or more generated cheat-sheet HTML files, runs every dimension
defined in rubric.md against each one, and prints a scored report ending in a
single headline number (0-100) plus a pass/fail verdict.

Design notes
------------
- The SKILL.md is the spec ("what good looks like"). rubric.md turns each rule
  into a gradeable check. This file is the thing that actually runs them, so a
  cheat sheet can be measured instead of eyeballed.
- Code-checked dimensions are pure stdlib (via parse.py) and always run.
- LLM-judged dimensions call the Anthropic API and only run when
  ANTHROPIC_API_KEY is set; otherwise they're skipped and excluded from the
  score (the report says so explicitly). No key is ever written to disk or
  printed.
- A dimension that has nothing to grade (e.g. no anchor bars present) is
  excluded from the mean rather than scored zero, and the report notes it.

Usage
-----
    python3 run.py path/to/prep.html [more.html ...]
    python3 run.py --no-judge prep.html      # force code-only run
    python3 run.py --json prep.html          # machine-readable output

Exit code is 0 if every file passes, 1 otherwise (handy for CI).
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

import parse


WPM = 130.0
OVER_TARGET_FACTOR = 1.25      # "significantly over" threshold from SKILL.md
ANCHOR_TOKEN_MAXLEN = 18
MAX_CUES_PER_SECTION = 2
PASS_THRESHOLD = 85.0
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "claude-sonnet-4-6")


# --------------------------------------------------------------------------
# A small result container for one dimension.
# --------------------------------------------------------------------------
class Dim:
    def __init__(self, key, label, kind, weight, hard=False):
        self.key = key
        self.label = label
        self.kind = kind          # "code" | "judge"
        self.weight = weight
        self.hard = hard          # binary correctness gate (dims 1 and 5)
        self.ran = False
        self.score = None         # normalized 0-1
        self.hard_fail = False
        self.detail = ""          # human-readable explanation / findings

    def set(self, score, detail, ran=True):
        self.score = score
        self.detail = detail
        self.ran = ran
        if self.hard and ran and score is not None and score < 1.0:
            self.hard_fail = True
        return self

    def skip(self, reason):
        self.ran = False
        self.detail = reason
        return self


# --------------------------------------------------------------------------
# Code-checked dimensions
# --------------------------------------------------------------------------
def dim_em_dashes(doc):
    d = Dim("em_dashes", "No em dashes", "code", 1.0, hard=True)
    if not doc.em_dash_contexts:
        return d.set(1.0, "none found")
    sample = "; ".join(c[:50] for c in doc.em_dash_contexts[:3])
    return d.set(0.0, f"{len(doc.em_dash_contexts)} found, e.g. \u2026{sample}\u2026")


def dim_anchor_discipline(doc):
    d = Dim("anchor_discipline", "Anchor word discipline", "code", 1.0)
    bars = [b for s in doc.sections for b in s.anchor_bars]
    if not bars:
        return d.skip("no anchor bars in document")
    bad = []
    for b in bars:
        n = len(b.tokens)
        ok = (3 <= n <= 5) and all(
            len(t) <= ANCHOR_TOKEN_MAXLEN and " " not in t for t in b.tokens
        )
        if not ok:
            bad.append(" / ".join(b.tokens) or "(empty bar)")
    passed = len(bars) - len(bad)
    detail = f"{passed}/{len(bars)} bars within spec"
    if bad:
        detail += "; offenders: " + " | ".join(bad[:3])
    return d.set(passed / len(bars), detail)


def dim_pacing_restraint(doc):
    d = Dim("pacing_restraint", "Pacing cue restraint", "code", 1.0)
    scripts = [s for s in doc.sections if s.is_script]
    if not scripts:
        return d.skip("no script sections")
    over = [(s.id, s.cue_count) for s in scripts if s.cue_count > MAX_CUES_PER_SECTION]
    passed = len(scripts) - len(over)
    detail = f"{passed}/{len(scripts)} sections within {MAX_CUES_PER_SECTION}-cue budget"
    if over:
        detail += "; over: " + ", ".join(f"{sid}({c})" for sid, c in over)
    return d.set(passed / len(scripts), detail)


def _target_seconds(round_type, section_id):
    is_pitch = "pitch" in section_id.lower()
    if round_type == "recruiter":
        return 90 if is_pitch else 90
    if round_type == "exec":
        return 90 if is_pitch else 120
    # hiring_manager or unknown -> default to the more generous HM targets
    return 120


def dim_talk_time(doc):
    d = Dim("talk_time", "Talk-time targets", "code", 1.0)
    scripts = [s for s in doc.sections if s.is_script and s.script_text.split()]
    if not scripts:
        return d.skip("no measurable script text")
    over = []
    for s in scripts:
        words = len(s.script_text.split())
        secs = words / WPM * 60
        target = _target_seconds(doc.round_type, s.id)
        if secs > target * OVER_TARGET_FACTOR:
            over.append(f"{s.id}({secs:.0f}s>{target}s)")
    passed = len(scripts) - len(over)
    note = "" if doc.round_type != "unknown" else " [round undetected, used HM targets]"
    detail = f"{passed}/{len(scripts)} scripts within target{note}"
    if over:
        detail += "; over: " + ", ".join(over)
    return d.set(passed / len(scripts), detail)


def dim_nav_integrity(doc):
    d = Dim("nav_integrity", "Navigation integrity", "code", 1.0, hard=True)
    orphan_links = [h for h in doc.nav_hrefs if h not in doc.present_ids]
    section_ids = [s.id for s in doc.sections]
    unlinked = [sid for sid in section_ids if sid not in doc.nav_hrefs]
    if not orphan_links and not unlinked:
        return d.set(1.0, f"all {len(doc.nav_hrefs)} nav links resolve; every section linked")
    parts = []
    if orphan_links:
        parts.append("dead links: " + ", ".join(orphan_links))
    if unlinked:
        parts.append("unlinked sections: " + ", ".join(unlinked))
    return d.set(0.0, "; ".join(parts))


def dim_stories_paragraph(doc):
    d = Dim("stories_paragraph", "Stories in paragraph format", "code", 0.5)
    stories = [s for s in doc.sections if s.is_script]
    if not stories:
        return d.skip("no story/script sections")
    bad = [s.id for s in stories if s.has_list_in_story]
    passed = len(stories) - len(bad)
    detail = f"{passed}/{len(stories)} story sections are prose"
    if bad:
        detail += "; lists found in: " + ", ".join(bad)
    return d.set(passed / len(stories), detail)


# --------------------------------------------------------------------------
# LLM-judged dimensions
# --------------------------------------------------------------------------
JUDGE_CRITERIA = {
    "spoken_tone": (
        "Spoken, first-person tone", 1.0,
        "Do the scripts read like natural speech the candidate would say out "
        "loud (contractions, natural rhythm, no written-document phrasing)? "
        "5 = natural speech throughout. 1 = reads like a formal written doc."
    ),
    "honesty": (
        "Honesty calibration", 1.5,
        "For any answer touching a weakness or gap, does it state plainly what "
        "the candidate does and does not have, then redirect to a real adjacent "
        "strength, without ever implying unearned expertise? "
        "5 = consistently honest and calibrated. 1 = inflates or implies "
        "expertise the candidate doesn't have. Quote any overclaim you find."
    ),
    "attribution": (
        "Attribution integrity", 1.0,
        "Are individual contributions ('I did X') kept distinct from team or "
        "others' work ('my team did X')? "
        "5 = contributions cleanly attributed. 1 = team/other work silently "
        "claimed in the first person."
    ),
}


def _call_anthropic(prompt):
    """Minimal stdlib call to the Anthropic Messages API. Returns text or raises."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("no key")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps({
            "model": JUDGE_MODEL,
            "max_tokens": 400,
            "messages": [{"role": "user", "content": prompt}],
        }).encode(),
        headers={
            "content-type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


def _judge(criterion_desc, scripts_text):
    prompt = (
        "You are grading one dimension of an interview cheat sheet against a "
        "rubric. Read the candidate's scripts, then score the dimension below.\n\n"
        f"DIMENSION:\n{criterion_desc}\n\n"
        "Respond with ONLY a JSON object, no markdown, no preamble:\n"
        '{\"score\": <integer 1-5>, \"reason\": \"<one sentence>\"}\n\n'
        f"SCRIPTS:\n{scripts_text[:6000]}"
    )
    text = _call_anthropic(prompt).strip()
    text = text.replace("```json", "").replace("```", "").strip()
    obj = json.loads(text)
    score = int(obj["score"])
    return max(1, min(5, score)), str(obj.get("reason", "")).strip()


def run_judges(doc, enabled):
    dims = []
    for key, (label, weight, desc) in JUDGE_CRITERIA.items():
        d = Dim(key, label, "judge", weight)
        if not enabled:
            dims.append(d.skip("judging disabled (--no-judge)"))
            continue
        if not os.environ.get("ANTHROPIC_API_KEY"):
            dims.append(d.skip("ANTHROPIC_API_KEY not set"))
            continue
        scripts_text = "\n\n".join(
            f"[{s.id}]\n{s.script_text}" for s in doc.sections if s.is_script
        )
        if not scripts_text.strip():
            dims.append(d.skip("no script text to judge"))
            continue
        try:
            raw_score, reason = _judge(desc, scripts_text)
            dims.append(d.set((raw_score - 1) / 4.0, f"{raw_score}/5 — {reason}"))
        except Exception as e:  # noqa: BLE001 - report any judge failure, don't crash
            dims.append(d.skip(f"judge error: {e}"))
    return dims


# --------------------------------------------------------------------------
# Orchestration + reporting
# --------------------------------------------------------------------------
def evaluate(path, use_judge):
    doc = parse.parse(open(path, encoding="utf-8").read())
    dims = [
        dim_em_dashes(doc),
        dim_anchor_discipline(doc),
        dim_pacing_restraint(doc),
        dim_talk_time(doc),
        dim_nav_integrity(doc),
        dim_stories_paragraph(doc),
    ]
    dims += run_judges(doc, use_judge)

    ran = [d for d in dims if d.ran]
    if ran:
        wsum = sum(d.weight for d in ran)
        headline = sum(d.score * d.weight for d in ran) / wsum * 100
    else:
        headline = 0.0
    hard_failed = any(d.hard_fail for d in dims)
    passed = headline >= PASS_THRESHOLD and not hard_failed
    return doc, dims, headline, hard_failed, passed


def print_report(path, doc, dims, headline, hard_failed, passed):
    print(f"\n\033[1m{path}\033[0m")
    print(f"  round: {doc.round_type}   sections: {len(doc.sections)}   "
          f"scripts: {sum(1 for s in doc.sections if s.is_script)}")
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
        hard = " *" if d.hard else "  "
        print(f"  {col}{mark:>5}\033[0m {hard} {d.label:<28} {d.kind:<5} w{d.weight}")
        if d.detail:
            print(f"          \033[90m{d.detail}\033[0m")
    print("  " + "-" * 66)
    verdict = "\033[92mPASS\033[0m" if passed else "\033[91mFAIL\033[0m"
    print(f"  HEADLINE: \033[1m{headline:.1f}\033[0m / 100   "
          f"(pass >= {PASS_THRESHOLD:.0f}, no hard fails)   ->  {verdict}")
    if hard_failed:
        print("  \033[91mhard failure present (* dimension) — fails regardless of score\033[0m")


def main():
    ap = argparse.ArgumentParser(description="Eval runner for interview cheat sheets.")
    ap.add_argument("files", nargs="+", help="generated cheat-sheet HTML file(s)")
    ap.add_argument("--no-judge", action="store_true", help="run code checks only")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a report")
    args = ap.parse_args()

    all_passed = True
    results = []
    for path in args.files:
        doc, dims, headline, hard_failed, passed = evaluate(path, not args.no_judge)
        all_passed = all_passed and passed
        if args.json:
            results.append({
                "file": path,
                "headline": round(headline, 1),
                "passed": passed,
                "hard_failure": hard_failed,
                "dimensions": [
                    {"key": d.key, "label": d.label, "kind": d.kind,
                     "weight": d.weight, "ran": d.ran,
                     "score": None if d.score is None else round(d.score, 3),
                     "hard_fail": d.hard_fail, "detail": d.detail}
                    for d in dims
                ],
            })
        else:
            print_report(path, doc, dims, headline, hard_failed, passed)

    if args.json:
        print(json.dumps(results, indent=2))
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
