---
name: comp-comparator
description: >
  Compares one or more job offers against your target compensation and against
  each other, breaking total comp into components (base, sign-on, bonus,
  equity, benefits), flagging risk factors in offer letter language (verbal
  vs. written commitments, discretionary vs. guaranteed bonus, cliff vesting,
  etc.), and producing a structured comparison plus a sequenced negotiation
  plan. Use this when the user has received an offer, is comparing multiple
  offers, or wants help preparing for a compensation negotiation conversation.
---

# Comp Comparator

Turns one or more offers into a structured comparison against your target
compensation, flags language risks in the offer itself, and produces a
sequenced negotiation plan.

## Inputs

**Required:**
1. **Target compensation** — your floor and target, broken down by component
   if possible (base, bonus target, equity expectations, must-have benefits)
2. **Offer details** — for each offer: base, sign-on bonus, performance
   bonus structure (target % and whether guaranteed/discretionary), equity
   (if any, with vesting schedule), PTO, start date, and any other negotiable
   terms mentioned
3. **Offer letter language** — relevant excerpts describing bonus eligibility,
   equity vesting, or any clauses that could change after signing (e.g.
   "company reserves the right to modify or eliminate bonus programs")

**Optional:**
4. **Market data** — if available, comparable comp data for the role/level/
   location (Glassdoor, Levels.fyi, etc.) to contextualize whether an offer
   is below, at, or above market
5. **Pipeline context** — other offers or active interview stages, since this
   affects leverage and urgency

## Output

A markdown comparison document with these sections:

### 1. Component breakdown table

One row per comp component (base, sign-on, performance bonus, equity,
benefits, PTO, start date), one column per offer plus a "your target" column.
Use clear values, not ranges, where the offer specifies a number. Where the
offer is ambiguous (e.g. "annual bonus structure" with no stated target %),
mark it as **unconfirmed** rather than guessing a number.

### 2. Total comp estimate

For each offer, sum a conservative total comp estimate. Show the calculation
explicitly (e.g. base + (base × bonus% if guaranteed, or $0 if discretionary
and unconfirmed) + equity annualized if applicable). Never include
discretionary or unconfirmed bonus amounts in the "guaranteed" total; show
them as a separate "potential upside" line.

### 3. Language risk flags

Read the offer letter language and flag any clause that could let the
employer change, reduce, or eliminate a stated benefit after signing.
Common patterns to flag:

- "Company reserves the right to modify or eliminate [bonus/benefit] programs
  at its discretion"
- Bonus described as "eligible to participate in" without a stated target,
  guarantee, or formula
- Equity with a 1-year cliff and no acceleration language
- Start date tied to "mutual agreement" without a hard date
- Any verbal commitment (from a recruiter or hiring manager) that does not
  appear in the written offer

For each flag, state plainly: what was said verbally (if applicable) vs. what
the document actually says, and what the practical risk is if the gap is
never closed.

### 4. Negotiation sequencing plan

A prioritized, ordered list of what to negotiate and in what sequence,
following the principle of asking for things in order of employer flexibility
(typically: base → sign-on → bonus structure/written confirmation → PTO →
start date → equity). For each item:

- What to ask for
- Why this sequence (what you'd be giving up by asking out of order, e.g.
  asking for equity before securing a written bonus commitment)
- A soft-no vs. hard-no read: what response would signal "there's room" vs.
  "this is final," based on how the response is phrased

### 5. Negotiation principles to remember

A short list of general negotiation principles relevant to this offer,
written as reminders, not generic advice. Examples:
- Never volunteer your current or expected salary number if asked first;
  redirect to the employer's range
- If a benefit was promised verbally but isn't in writing, ask for it in
  writing before signing, framed as routine ("could we get that bonus
  structure reflected in the offer letter for my records?") rather than
  adversarial
- If the company has a structural reason a benefit category doesn't apply
  (e.g. a mutual company with no shareholders has no equity to offer), don't
  ask for that category; it signals you didn't do basic research

## Multi-offer comparison

If multiple offers are provided, add a section ranking them by total
guaranteed comp, then separately by total comp including potential upside,
and note where the rankings diverge (an offer that looks better on paper but
carries more unconfirmed/discretionary risk).

## Accuracy rules

- Never convert a discretionary or unconfirmed bonus into a guaranteed dollar
  amount in the totals. Show it separately.
- If verbal and written terms conflict, always treat the written term as
  current truth and flag the conflict; don't average or split the difference.
- Do not provide a recommendation on whether to accept an offer as financial
  advice. Lay out the comparison, the risks, and the negotiation plan, and
  let the candidate decide. If asked directly "should I take this," restate
  the tradeoffs rather than giving a verdict.
