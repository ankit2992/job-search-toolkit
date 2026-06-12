# Interview Cheat Sheet Generator

**Stage:** Interview

A Claude skill that generates a single-file HTML "cheat sheet" for one specific
interview round — built for glancing at during the call, not for studying
beforehand.

## The problem

Generic interview prep ("research the company, practice your stories") doesn't
help in the moment. What helps is having the actual words you'll say, with
delivery cues, organized so you can find the right section in seconds if the
conversation goes somewhere unexpected.

## What it does

Given a job description, your background, your existing story bank, and
context about a specific round (interviewer, format, focus), it produces a
navigable HTML page with:

- A context strip (company/role facts to have cold)
- A pre-call checklist
- Full first-person scripts for "certain" questions (tell me about yourself,
  why did you leave, salary expectations)
- Scripts for "likely" questions mapped to your existing stories, each with a
  short anchor-word sequence as a memory aid if you go blank
- Probe/follow-up sections for when an interviewer asks for a second example
- Honestly-calibrated answers for "possible" questions that touch your known
  gaps — explicitly designed to avoid overclaiming
- A closing list of questions to ask them

## Design decisions

- **Anchor-word bars, not full outlines.** A story is told in your own words
  in the moment; the anchor bar (`WrongAssumption → Escalated → Delivered`)
  is just a recall sequence if you freeze mid-story. It's a memory aid, not a
  script to read.
- **Inline pacing cues, used sparingly.** `[PAUSE]` and `[SLOW]` mark the 1-2
  moments per answer that actually matter, like landing a number or a payoff
  line. Cue overload defeats the purpose.
- **Reuse stories, don't invent new ones per interview.** The same 4-6 stories
  get reframed for different roles and rounds. This keeps your answers
  consistent across a multi-round process and across companies.
- **Honesty calibration is a first-class section, not an afterthought.** For
  questions touching real gaps, the generated answer states plainly what
  experience you do and don't have, then redirects to the adjacent strength
  that's real. The skill explicitly avoids generating scripts that imply
  expertise you don't have.
- **Talk-time math.** Scripts are checked against word-count-based time
  estimates (130 wpm) so a "90 second" answer is actually close to 90 seconds,
  not 3 minutes of dense text.

## Reusable template

`templates/cheat-sheet-template.html` contains the full design system (CSS
variables, sidebar nav, section/component classes) extracted as a generic
template with placeholder content. `examples/example-prep-sheet.html` is a
fully worked example using a fictional company and role, showing what a
completed cheat sheet looks like.

## What I specified vs. what was generated

I defined the structure (sections, ordering, anchor-bar concept, pacing cue
conventions, honesty-calibration approach) and the visual design system
through iteration across multiple real prep sessions. Claude generated the
HTML/CSS implementation and the per-interview content against that
specification.

## Status

Used for multiple real interview rounds as part of an active job search. The
template and example here are genericized; real prep sheets contain
company-specific and personal content and are not included in this repo.
