#!/usr/bin/env python3
"""
run.py — eval runner for the comp comparator.

Takes one or more comparison markdown files, runs every rubric dimension, and
prints a scored report ending in a 0-100 headline and a pass/fail verdict.

This tool is graded mostly on arithmetic correctness and rule-adherence
(objective code checks), with a few LLM-judged dimensions for recall and the
no-verdict guardrail. Judged dimensions need ANTHROPIC_API_KEY and skip
gracefully without it. Exit code is 0 if all files pass, else 1.

    python3 run.py examples/example-comparison.md
    python3 run.py --no-judge a.md b.md
    python3 run.py --json a.md
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


# -------------------------- code dimensions --------------------------
REQUIRED_SECTIONS = {
    "component breakdown": ("component",),
    "total comp estimate": ("total comp",),
    "language risk flags": ("risk flag", "language risk"),
    "negotiation sequencing": ("sequencing", "negotiation seq"),
    "principles": ("principle",),
}


def dim_sections(doc):
    d = Dim("sections", "Required sections present", "code", 1.0, hard=True)
    missing = [name for name, keys in REQUIRED_SECTIONS.items()
               if not any(any(k in h for k in keys) for h in doc.headings)]
    if not missing:
        return d.set(1.0, "all five sections present")
    return d.set(0.0, "missing: " + ", ".join(missing))


def dim_guaranteed_excludes_discretionary(doc):
    d = Dim("guaranteed_clean", "Guaranteed total excludes discretionary", "code", 2.0, hard=True)
    if doc.guaranteed_total is None or doc.base_offer is None:
        return d.skip("couldn't locate guaranteed total or base figure")
    # When the bonus is unconfirmed/discretionary, the guaranteed total must not
    # exceed the confirmed base. A higher figure means an unconfirmed amount was
    # folded in.
    if doc.bonus_unconfirmed:
        if doc.guaranteed_total <= doc.base_offer + 1:
            extra = " (upside shown separately)" if doc.upside_shown else ""
            return d.set(1.0, f"guaranteed ${doc.guaranteed_total:,} = base ${doc.base_offer:,}{extra}")
        return d.set(0.0, f"guaranteed ${doc.guaranteed_total:,} exceeds confirmed base "
                          f"${doc.base_offer:,} — unconfirmed comp folded in")
    return d.set(1.0, "bonus is guaranteed; inclusion in total is correct")


def dim_arithmetic(doc):
    d = Dim("arithmetic", "Total comp arithmetic correct", "code", 1.0)
    if doc.guaranteed_total is None or doc.base_offer is None:
        return d.skip("missing figures to check")
    if doc.bonus_unconfirmed:
        if abs(doc.guaranteed_total - doc.base_offer) <= max(1, int(doc.base_offer * 0.005)):
            return d.set(1.0, f"${doc.guaranteed_total:,} matches base within tolerance")
        return d.set(0.0, f"${doc.guaranteed_total:,} != base ${doc.base_offer:,}")
    return d.set(1.0, "guaranteed components present; sum assumed shown")


RISK_PATTERNS = {
    "reserves_right": (
        r"reserve[s]? the right to (modify|eliminate)",
        ("reserve", "modify or eliminate", "discretion"),
    ),
    "eligible_no_target": (
        r"eligible to participate",
        ("eligible to participate", "no stated target", "unconfirmed", "to be determined"),
    ),
    "cliff": (r"cliff", ("cliff",)),
    "verbal_only": (
        r"verbal|recruiter stated|stated.*during the (offer )?call",
        ("verbal", "not in (the )?writing", "not in the written", "no written"),
    ),
}


def dim_risk_recall(doc):
    d = Dim("risk_recall", "Risk-flag recall", "code", 1.5)
    src = doc.input_excerpt.lower()
    out = doc.risk_section.lower()
    present = [k for k, (pat, _) in RISK_PATTERNS.items() if re.search(pat, src)]
    if not present:
        return d.skip("no known risk patterns detected in the input excerpt")
    flagged, missed = [], []
    for k in present:
        _, out_markers = RISK_PATTERNS[k]
        if any(re.search(m, out) for m in out_markers):
            flagged.append(k)
        else:
            missed.append(k)
    detail = f"{len(flagged)}/{len(present)} input risks flagged"
    if missed:
        detail += "; missed: " + ", ".join(missed)
    return d.set(len(flagged) / len(present), detail)


def dim_no_irrelevant_ask(doc):
    d = Dim("no_irrelevant_ask", "No structurally-irrelevant asks", "code", 1.0)
    if not doc.equity_not_applicable:
        return d.skip("equity is applicable or unspecified; nothing to check")
    seq = doc.sequencing_section.lower()
    # an equity *ask* in the plan (not merely a note that it's not applicable).
    # Allow filler words between the verb and the noun ("ask for an equity grant").
    asks_equity = bool(re.search(
        r"(ask|negotiate|request|push|counter|add)\b[^.\n]{0,25}"
        r"(equity|rsu|stock option|\boptions\b|shares|grant)", seq))
    if asks_equity:
        return d.set(0.0, "negotiation plan asks for equity at a company that has none")
    return d.set(1.0, "correctly avoids an equity ask")


# -------------------------- judged dimensions --------------------------
JUDGE_CRITERIA = {
    "no_verdict": (
        "No accept/reject verdict", 1.5, True,
        "Does the document avoid telling the candidate whether to accept or "
        "reject the offer, instead laying out tradeoffs for them to decide? "
        "5 = no verdict, tradeoffs only. 1 = tells them to accept or reject. "
        "Quote any verdict language."
    ),
    "unconfirmed_honesty": (
        "Unconfirmed values handled honestly", 1.0, False,
        "Are ambiguous comp terms explicitly marked unconfirmed rather than "
        "given an invented number? 5 = all ambiguity marked. 1 = a number is "
        "fabricated for an ambiguous term."
    ),
    "sequencing": (
        "Sequencing logic is sound", 1.0, False,
        "Does the negotiation order follow employer-flexibility logic "
        "(base, then sign-on, then bonus confirmation, then PTO, start date, "
        "equity last) with rationale? 5 = sound order with rationale. "
        "1 = arbitrary or backwards."
    ),
}


def _judge(desc, content):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("no key")
    prompt = (
        "Grade one dimension of a compensation comparison document against a "
        f"rubric.\n\nDIMENSION:\n{desc}\n\n"
        'Respond with ONLY JSON: {"score": <1-5 int>, "reason": "<one sentence>"}\n\n'
        f"DOCUMENT:\n{content[:8000]}"
    )
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps({"model": JUDGE_MODEL, "max_tokens": 400,
                         "messages": [{"role": "user", "content": prompt}]}).encode(),
        headers={"content-type": "application/json", "x-api-key": key,
                 "anthropic-version": "2023-06-01"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    obj = json.loads(text.replace("```json", "").replace("```", "").strip())
    return max(1, min(5, int(obj["score"]))), str(obj.get("reason", "")).strip()


def run_judges(doc, enabled):
    dims = []
    for key, (label, weight, hard, desc) in JUDGE_CRITERIA.items():
        d = Dim(key, label, "judge", weight, hard=hard)
        if not enabled:
            dims.append(d.skip("judging disabled (--no-judge)")); continue
        if not os.environ.get("ANTHROPIC_API_KEY"):
            dims.append(d.skip("ANTHROPIC_API_KEY not set")); continue
        try:
            s, reason = _judge(desc, doc.raw)
            dims.append(d.set((s - 1) / 4.0, f"{s}/5 — {reason}"))
        except Exception as e:  # noqa: BLE001
            dims.append(d.skip(f"judge error: {e}"))
    return dims


# -------------------------- orchestration --------------------------
def evaluate(path, use_judge):
    doc = parse.parse(open(path, encoding="utf-8").read())
    dims = [dim_sections(doc), dim_guaranteed_excludes_discretionary(doc),
            dim_arithmetic(doc), dim_risk_recall(doc), dim_no_irrelevant_ask(doc)]
    dims += run_judges(doc, use_judge)
    ran = [d for d in dims if d.ran]
    headline = (sum(d.score * d.weight for d in ran) / sum(d.weight for d in ran) * 100) if ran else 0.0
    hard_failed = any(d.hard_fail for d in dims)
    return doc, dims, headline, hard_failed, (headline >= PASS_THRESHOLD and not hard_failed)


def print_report(path, doc, dims, headline, hard_failed, passed):
    print(f"\n\033[1m{path}\033[0m")
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
        print(f"  {col}{mark:>5}\033[0m {' *' if d.hard else '  '} {d.label:<40} {d.kind:<5} w{d.weight}")
        if d.detail:
            print(f"          \033[90m{d.detail}\033[0m")
    print("  " + "-" * 66)
    verdict = "\033[92mPASS\033[0m" if passed else "\033[91mFAIL\033[0m"
    print(f"  HEADLINE: \033[1m{headline:.1f}\033[0m / 100   (pass >= {PASS_THRESHOLD:.0f}, no hard fails)   ->  {verdict}")
    if hard_failed:
        print("  \033[91mhard failure present (* dimension)\033[0m")


def main():
    ap = argparse.ArgumentParser(description="Eval runner for comp comparisons.")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    all_passed, results = True, []
    for path in args.files:
        doc, dims, headline, hard_failed, passed = evaluate(path, not args.no_judge)
        all_passed = all_passed and passed
        if args.json:
            results.append({"file": path, "headline": round(headline, 1), "passed": passed,
                            "hard_failure": hard_failed,
                            "dimensions": [{"key": d.key, "label": d.label, "kind": d.kind,
                                            "weight": d.weight, "ran": d.ran,
                                            "score": None if d.score is None else round(d.score, 3),
                                            "hard_fail": d.hard_fail, "detail": d.detail} for d in dims]})
        else:
            print_report(path, doc, dims, headline, hard_failed, passed)
    if args.json:
        print(json.dumps(results, indent=2))
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
