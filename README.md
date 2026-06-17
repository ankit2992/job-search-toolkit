# Job Search Toolkit

A small collection of Claude skills built around the job search lifecycle:
**Application → Interview → Negotiation**. Each tool solves a specific,
recurring problem from an active job search, built by specifying the
requirements and design decisions and using Claude Code to implement them.

## Why this exists

Job searching is repetitive in ways that are well-suited to automation and
structure: the same boards need checking daily, interview prep follows
recurring patterns across companies, and offers need to be compared against
the same kind of risk factors every time. These tools encode the decisions
I'd otherwise make manually and inconsistently, every time.

## Used in a real search

These tools were built and used during an active 4-month job search
(250+ applications across fintech, insurtech, and big tech):

- **Job Search Digest** ran daily during the sourcing phase
- **Interview Cheat Sheet** was used to prep live interview loops,
  including the one that led to the signed offer
- **Comp Comparator** was run on the final offer — it flagged a verbal
  bonus commitment as unconfirmed upside, which changed how I evaluated
  the written terms

## Tools

### [Application — Job Search Digest](./application/job-search-digest)

Searches LinkedIn and ATS job boards daily, filters and deduplicates results
against target roles, and emails a digest. Optionally runs on a schedule.

**Key design choices:** dedup by company + normalized title (not just URL),
graceful fallback when a data source is unavailable, adaptive search window
when results are sparse, privacy-scoped to a single destination email.

<img width="1123" height="610" alt="image" src="https://github.com/user-attachments/assets/c8030205-77f9-4735-8b41-14e38ea72243" />

### [Interview — Interview Cheat Sheet Generator](./interview/interview-cheat-sheet)

Generates a single-file HTML "cheat sheet" for a specific interview round —
full first-person scripts with delivery pacing cues, anchor-word memory aids,
and honestly-calibrated answers for known gaps.

**Key design choices:** anchor words as recall aids rather than scripts to
read, sparing use of pacing cues, reuse of a fixed story bank across rounds,
and an explicit honesty-calibration pattern for gap-area questions that
avoids overclaiming.

<img width="1897" height="898" alt="image" src="https://github.com/user-attachments/assets/9c9a184e-e079-46de-baaf-ca8fcb66e43a" />

**[View live example →](https://ankit2992.github.io/job-search-toolkit/interview/interview-cheat-sheet/examples/example-prep-sheet.html)**

### [Negotiation — Comp Comparator](./negotiation/comp-comparator)

Compares an offer (or multiple offers) against a target comp, flags risky
offer-letter language (verbal vs. written commitments, discretionary bonus
clauses, etc.), and produces a sequenced negotiation plan.

**Key design choices:** written offer language is the source of truth,
verbal commitments are tracked as unconfirmed upside, negotiation steps are
sequenced by leverage, and the tool deliberately stops short of giving
financial advice.

## A note on how these were built

For each tool, I defined the problem, the workflow steps, and the specific
design tradeoffs (filtering logic, risk flags, content structure, honesty
calibration rules). Claude Code implemented each skill against those
specifications. Each tool's README documents what I specified versus what
was generated, and its current status (in active use vs. newly built).

## Evaluation

Each tool ships with an **eval suite** — an automated harness that scores a
generated output against a rubric and produces a single pass/fail verdict. The
principle throughout: the `SKILL.md` is the spec, and the eval is how the
output is proven to meet it, measured instead of eyeballed.

The more interesting decision was that the three tools are evaluated in three
different ways, because they fail in different ways:

| Tool | What kind of problem | How it's graded |
|---|---|---|
| Interview Cheat Sheet | Generation quality | LLM-judged (tone, honesty, attribution) + code format checks |
| Job Search Digest | Retrieval & filtering | Objective code checks (precision, dedup, seniority/location, URLs) |
| Comp Comparator | Structured reasoning & math | Arithmetic verification + risk-flag recall + a no-advice guardrail |

A search tool is a *precision* problem with checkable right answers; a comp
tool is an *arithmetic-correctness* problem; only the cheat sheet is a
subjective *quality* problem that genuinely needs an LLM judge. Matching the
eval method to the failure mode is the point.

Each `eval/` folder is self-contained and runnable:

```bash
# code-only checks, no API key required
python3 interview/interview-cheat-sheet/eval/run.py --no-judge interview/interview-cheat-sheet/examples/example-prep-sheet.html
python3 negotiation/comp-comparator/eval/run.py --no-judge negotiation/comp-comparator/examples/example-comparison.md
python3 application/job-search-digest/eval/run.py --no-judge application/job-search-digest/examples/example-digest.json

# include the LLM-judged dimensions
export ANTHROPIC_API_KEY=sk-...
python3 negotiation/comp-comparator/eval/run.py negotiation/comp-comparator/examples/example-comparison.md
```

Each suite ships with fixtures that demonstrate it discriminates good from bad:
the comp eval scores a correct analysis 100 and a deliberately-flawed one 15
(discretionary bonus folded into the guaranteed total, risk clauses unflagged,
an equity ask at a company with no equity); the digest eval catches a planted
duplicate, an over-level title, a non-US-remote role, and an off-target
"Product Marketing Manager." Runners exit non-zero on failure, so they drop
straight into CI.

## What's next

Ideas under consideration, in priority order:

- **Follow-up tracker** — application status and outreach cadence
  management; the biggest remaining manual step in the workflow
- **Interviewer research module** — pre-round briefs on interviewer
  backgrounds and likely question areas, feeding into the cheat sheet
- **Post-offer checklist** — first-90-days planning, benefits election
  deadlines, and title/level documentation

## Structure

```
job-search-toolkit/
├── application/
│   └── job-search-digest/
│       ├── SKILL.md
│       ├── README.md
│       ├── eval/
│       │   ├── rubric.md
│       │   ├── parse.py
│       │   ├── run.py
│       │   └── README.md
│       └── examples/
│           └── example-digest.json
├── interview/
│   └── interview-cheat-sheet/
│       ├── SKILL.md
│       ├── README.md
│       ├── eval/
│       │   ├── rubric.md
│       │   ├── parse.py
│       │   ├── run.py
│       │   └── README.md
│       ├── templates/
│       │   └── cheat-sheet-template.html
│       └── examples/
│           └── example-prep-sheet.html
└── negotiation/
    └── comp-comparator/
        ├── SKILL.md
        ├── README.md
        ├── eval/
        │   ├── rubric.md
        │   ├── parse.py
        │   ├── run.py
        │   └── README.md
        └── examples/
            ├── example-comparison.md
            └── example-comparison-flawed.md
```

All examples use fictional companies, roles, and numbers.


