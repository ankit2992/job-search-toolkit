# Comp Comparator

**Stage:** Offer Negotiation

A Claude skill that takes one or more job offers, breaks them into comp
components, flags risky offer-letter language, and produces a sequenced
negotiation plan.

## The problem

Offer letters bury the gap between what's promised verbally and what's
actually written down. A recruiter might say "the bonus is typically around
X%," but if the letter only says "eligible to participate in a program the
company can modify or eliminate," that verbal number isn't part of your comp
until it's in writing. Negotiating multiple components at once, or in the
wrong order, can also waste leverage on lower-impact asks.

## What it does

Given your target comp, the offer details, and the actual offer letter
language, it produces:

1. A component-by-component comparison table (base, bonus, equity, PTO,
   start date) against your target
2. A conservative total-comp estimate that excludes unconfirmed or
   discretionary amounts, with potential upside shown separately
3. Explicit flags for offer-letter language that could let terms change after
   signing (discretionary bonus clauses, verbal-only commitments, cliff
   vesting, etc.)
4. A sequenced negotiation plan (typically base → bonus confirmation → PTO →
   start date → equity), with guidance on reading soft-no vs. hard-no
   responses
5. General negotiation principles relevant to the specific offer

## Design decisions

- **Verbal vs. written is the central distinction.** The skill treats the
  written offer as the only source of truth for totals, and verbal
  commitments as "potential upside" until confirmed in writing. This matches
  a common real-world gap: recruiters often communicate more generously than
  what's contractually binding.
- **No financial advice.** The skill explicitly does not recommend whether to
  accept an offer. It lays out the comparison and the risks; the decision
  stays with the candidate. (This also matches a general principle: AI tools
  shouldn't make financial decisions for you, only inform them.)
- **Sequencing matters.** The negotiation plan is ordered, not just a list,
  because asking for things out of order (e.g. equity at a company
  structurally unable to offer it, or PTO before addressing a below-range
  base) wastes the highest-leverage moment in the process.
- **Soft-no vs. hard-no framing.** Helps the candidate read responses in
  real time rather than treating every "let me check" the same as every
  "this is final."

## Example

`examples/example-comparison.md` is a fully worked fictional example showing
the output format: component breakdown, total comp estimate, language risk
flags, and a sequenced negotiation plan.

## What I specified vs. what was generated

I defined the structure of the comparison (component breakdown, the
verbal-vs-written distinction, the negotiation sequencing principle, and the
no-financial-advice constraint) based on patterns from real negotiation
conversations. Claude generated the skill implementation and the example
against that specification.

## Status

Newly built. Designed for use in upcoming offer evaluations.
