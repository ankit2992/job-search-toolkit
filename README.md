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

## Evals

Each tool has an `eval/` folder that makes quality measurable rather than
subjective. The three tools fail in different ways, so each eval uses a
different strategy:

| Tool | Eval strategy | What it catches |
|------|--------------|-----------------|
| **Comp Comparator** | Arithmetic + rules | Bonus folded into guaranteed total, missing risk-clause flags, equity ask at a no-equity company |
| **Job Search Digest** | Retrieval precision | Duplicates, seniority/location filter violations, malformed URLs, off-target titles |
| **Interview Cheat Sheet** | LLM-judged quality | Tone, honesty calibration, attribution — dimensions with no single right answer |

Run any eval from its folder:

```bash
# comp comparator
python3 negotiation/comp-comparator/eval/run.py negotiation/comp-comparator/examples/example-comparison.md

# job search digest
python3 application/job-search-digest/eval/run.py application/job-search-digest/examples/example-digest.json
```

The judged dimensions (tone, honesty) in the cheat-sheet eval require
`export ANTHROPIC_API_KEY=...` before running.

## A note on how these were built

For each tool, I defined the problem, the workflow steps, and the specific
design tradeoffs (filtering logic, risk flags, content structure, honesty
calibration rules). Claude Code implemented each skill against those
specifications. Each tool's README documents what I specified versus what
was generated, and its current status (in active use vs. newly built).

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


