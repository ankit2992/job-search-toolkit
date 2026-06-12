---
name: interview-cheat-sheet
description: >
  Generates a personalized, single-file HTML interview cheat sheet for a specific
  interview round. Takes a job description, the candidate's background and story
  bank, and round-specific context (interviewer, format, focus areas), and produces
  a navigable HTML page with a fixed sidebar, full first-person scripts for likely
  questions, inline delivery pacing cues, anchor-word memory aids, probe/follow-up
  sections, and a closing "questions to ask" list. Use this when the user wants a
  prep sheet, cheat sheet, or talking-points page for an upcoming interview, ideally
  after a job-description-based prep guide has already identified the likely
  question categories.
---

# Interview Cheat Sheet Generator

Produces a single-file HTML "cheat sheet" for one specific interview round —
designed to be read on a second monitor or phone during the call, not as a
study document. Optimized for glanceability and delivery, not analysis.

## Inputs

**Required:**
1. **Round context** — company, role, interviewer name/title (if known), round
   type (recruiter screen / hiring manager / panel / exec), format and duration,
   and the primary goal of this round (e.g. "pass to hiring manager round")
2. **Candidate background** — resume or summary, with key metrics already
   pressure-tested (i.e. verified, not estimated)
3. **Story bank** — the candidate's existing accomplishment stories. Reuse
   stories across interviews; do not invent new ones. Each story should map
   to 3-5 short "anchor words" that act as a recall sequence.
4. **Likely question categories** — ideally sourced from a prior JD-analysis
   step (see the `interview-prep-kit` style of skill). If not provided,
   derive categories from the JD and role family.

**Optional:**
5. **Known gaps** — areas where the candidate's experience is thin. These get
   honest, calibrated scripts rather than overclaiming.
6. **Comp context** — if a salary/comp question is anticipated.

## Output

A single self-contained HTML file: `{company-slug}-{round-name}-prep.html`.
No external dependencies except Google Fonts (DM Sans, DM Mono, Instrument
Serif) — must render correctly even if fonts fail to load.

## Content structure

Organize the page into these sections, in this order. Not every section
applies to every round — include only what's relevant to the round type and
duration.

1. **Context strip** — 3-4 small cards giving situational facts the candidate
   should have cold: company/deal context, the role's strategic framing, a
   key program or initiative named in the JD, and the round's focus.
2. **Pre-call checklist** — a short checklist of things to confirm or review
   right before the call (numbers to know, names to remember, etc.)
3. **Certain questions** — questions virtually guaranteed to come up
   ("tell me about yourself", "why this company", "why did you leave your
   last role", "salary expectations"). Full first-person scripts.
4. **Career walkthrough** — only for rounds likely to ask "walk me through
   your resume." A beat-by-beat script, one beat per job, each under ~20
   seconds, with an anchor bar showing the sequence of employers/roles.
5. **Likely questions** — questions strongly implied by the JD, mapped to the
   candidate's story bank. Each question gets a full script using the
   relevant story, with an anchor-word bar and a probe/follow-up section for
   if the interviewer asks a second story on the same topic.
6. **Possible questions** — lower-probability but plausible questions,
   especially ones touching the candidate's known gaps. These get honestly
   calibrated answers (see Honesty calibration below), not full scripts.
7. **Questions to ask them** — 3-5 questions for the candidate to ask,
   ordered by priority, each with a one-line note on why it matters. Always
   end with a "what are next steps" question.

## Writing rules

- **First person, spoken language.** Every script is something the candidate
  would actually say out loud — contractions, natural rhythm, no jargon they
  wouldn't use in conversation.
- **No em dashes.** Use periods, commas, or rephrase.
- **Paragraph format for stories**, not bullet points. Stories are told, not
  presented.
- **Inline pacing cues** using two tags only:
  - `[PAUSE]` — a beat of silence, usually after landing a key number or
    statement
  - `[SLOW]` — slow down for the next clause, usually the payoff line
  Don't overuse these. 1-2 per script section is usually enough. Cues should
  mark moments that matter, not be sprinkled decoratively.
- **Anchor-word bars.** For any story or walkthrough, extract 3-5 short
  capitalized anchor words (e.g. `WrongAssumption → Escalated → Delivered`)
  that act as a recall sequence if the candidate goes blank mid-story. These
  are memory aids, not content — keep them terse.
- **Talk-time targets.** Calculate approximate spoken duration as
  `word_count / 130 wpm * 60` seconds, run only on the script text (exclude
  cue notes and probe sections). Target ranges by round type:
  - Recruiter screen: ~90 sec for the main pitch
  - Hiring manager round: ~120 sec for the main pitch, up to 120 sec per story
  - Exec/CIO round: ~90 sec pitch, up to 120 sec per story
  Flag any script that's significantly over target.

## Honesty calibration

For "possible questions" touching known gaps, follow this pattern instead of
a full script:

1. State plainly what experience the candidate does and doesn't have
2. Redirect to the adjacent strength that *is* real
3. If pushed for more depth, give an honest second-layer answer that's
   calibrated, not inflated (e.g. "intermediate", "working knowledge, not
   expert")

Never write a script that implies expertise the candidate doesn't have. The
goal is "honest framing wins more trust than overclaiming," stated directly
in the cheat sheet itself as a coaching note if useful.

## Accuracy rules

- Do date math explicitly. Don't estimate tenures or gaps.
- If a metric appears more than once in source material with different
  values, flag it rather than picking one silently.
- Distinguish "I did X" from "my team did X" — if a detail belongs to someone
  else (an idea that was engineering's, a system that ops ran), keep that
  attribution in the script. Don't quietly claim it as the candidate's.

## Building the HTML

Use `templates/cheat-sheet-template.html` as the starting point. It defines
the full design system: CSS variables, sidebar navigation, section/component
classes (context cards, anchor bars, story "beats," Q&A cards, probe
sections, cue callouts, the closing "ask" list), and the scroll-spy sidebar
script.

- Copy the CSS and component structure as-is. Don't redesign it.
- Replace all placeholder content with real content for this round.
- Build the sidebar to match the sections actually included — don't link to
  empty sections, and don't omit a section from the sidebar if it's in the
  page.
- Each `.section` needs a matching sidebar `.nav-item` with a `href="#id"`
  that matches the section's `id`.
- Color-code nav items and section tags by category using the existing color
  classes (`navy`, `gold`, `blue`, `green`, `red`, `purple`) — pick
  consistently per category (e.g. all "certain" questions one color, all
  "likely questions tied to a story" another).

See `examples/example-prep-sheet.html` for a fully worked (fictional)
example.
