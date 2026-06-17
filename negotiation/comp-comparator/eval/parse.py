"""
parse.py — pull the structures the comp rubric cares about out of a comparison
markdown file. Stdlib only.

The comparison doc is also self-documenting: it contains its own inputs (offer
letter excerpt, verbal context) near the top. We read those so the eval can
check whether the output flagged the risks that were actually present in the
offer, rather than grading risk-flagging in a vacuum.
"""

import re
from dataclasses import dataclass, field


@dataclass
class Doc:
    raw: str
    headings: list                       # all heading texts, lowercased
    input_excerpt: str                   # offer-letter language + verbal context
    base_offer: int = None               # base salary from the component table (offer col)
    guaranteed_total: int = None         # stated guaranteed total comp
    upside_shown: bool = False           # is a separate upside line present?
    bonus_unconfirmed: bool = False      # is the bonus marked unconfirmed/discretionary?
    equity_not_applicable: bool = False  # does the offer structurally lack equity?
    risk_section: str = ""               # text of the risk-flags section
    sequencing_section: str = ""         # text of the negotiation sequencing section
    money: list = field(default_factory=list)


_MONEY_RE = re.compile(r"\$\s?([\d][\d,]*)(?:\.\d+)?")


def _money(s):
    """First dollar amount in a string, as an int, or None."""
    m = _MONEY_RE.search(s)
    return int(m.group(1).replace(",", "")) if m else None


def _section(raw, *keywords):
    """Return the text of the first heading whose title contains any keyword,
    up to the next same-or-higher-level heading."""
    lines = raw.splitlines()
    out, capturing = [], False
    for ln in lines:
        h = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if h:
            title = h.group(2).lower()
            if capturing:
                break
            if any(k in title for k in keywords):
                capturing = True
                continue
        elif capturing:
            out.append(ln)
    return "\n".join(out).strip()


def parse(md_text):
    raw = md_text
    headings = [m.group(1).strip().lower()
                for m in re.finditer(r"^#{1,6}\s+(.*)$", raw, re.M)]

    # --- inputs block: offer letter excerpt + verbal context ---
    input_excerpt = _section(raw, "input")
    # fall back: grab any blockquote/italic excerpt near the top if no Inputs heading
    if not input_excerpt:
        input_excerpt = "\n".join(raw.splitlines()[:30])

    risk_section = _section(raw, "risk flag", "language risk")
    sequencing_section = _section(raw, "sequencing", "negotiation seq")

    # --- base salary: component-table row whose first cell is "base" ---
    base_offer = None
    for ln in raw.splitlines():
        if ln.strip().startswith("|"):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if cells and cells[0].lower() == "base":
                # offer is the last numeric cell on the row
                for cell in reversed(cells[1:]):
                    v = _money(cell)
                    if v:
                        base_offer = v
                        break
            if cells and "performance bonus" in cells[0].lower():
                rowtext = ln.lower()
                if any(k in rowtext for k in
                       ("unconfirmed", "discretionary", "eligible to participate", "to be determined")):
                    pass  # handled below globally too

    # --- guaranteed total + upside ---
    guaranteed_total = None
    m = re.search(r"guaranteed total[^$\n]*\$?\s?([\d][\d,]*)", raw, re.I)
    if m:
        guaranteed_total = int(m.group(1).replace(",", ""))
    upside_shown = bool(re.search(r"upside|not guaranteed|potential", raw, re.I))

    blob = raw.lower()
    bonus_unconfirmed = any(k in blob for k in
                            ("unconfirmed", "discretionary", "eligible to participate",
                             "to be determined", "no stated target"))
    equity_not_applicable = any(k in blob for k in
                                ("mutual company", "no equity", "equity isn't part",
                                 "equity is not", "not applicable", "n/a"))

    return Doc(
        raw=raw, headings=headings, input_excerpt=input_excerpt,
        base_offer=base_offer, guaranteed_total=guaranteed_total,
        upside_shown=upside_shown, bonus_unconfirmed=bonus_unconfirmed,
        equity_not_applicable=equity_not_applicable,
        risk_section=risk_section, sequencing_section=sequencing_section,
        money=[int(x.replace(",", "")) for x in _MONEY_RE.findall(raw)],
    )
