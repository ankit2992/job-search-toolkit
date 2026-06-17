"""
parse.py — extract the structures the rubric cares about from a generated
cheat sheet HTML file. Stdlib only (re + html), so the eval runs anywhere
without installing anything.

The cheat sheet markup is well-defined by the template, so we parse against
its known class names rather than doing general HTML parsing.
"""

import re
import html as _html
from dataclasses import dataclass, field


@dataclass
class AnchorBar:
    tokens: list


@dataclass
class Section:
    id: str
    raw: str          # raw HTML of the section block
    text: str         # visible text, tags stripped
    script_text: str  # script text only (probes/cues/anchors removed)
    is_script: bool   # does this section contain a spoken script / story?
    cue_count: int
    anchor_bars: list = field(default_factory=list)
    has_list_in_story: bool = False


@dataclass
class Doc:
    title: str
    eyebrow: str
    round_type: str          # 'recruiter' | 'hiring_manager' | 'exec' | 'unknown'
    nav_hrefs: list          # list of section ids referenced by nav (deduped, order kept)
    sections: list           # list[Section]
    em_dash_contexts: list   # list of short text snippets containing an em dash
    present_ids: list        # every element id present in the document
    raw: str


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_tags(s):
    return _WS_RE.sub(" ", _html.unescape(_TAG_RE.sub(" ", s))).strip()


def _detect_round(eyebrow, title):
    blob = (eyebrow + " " + title).lower()
    if any(k in blob for k in ("recruiter", "phone screen", "screen ")):
        return "recruiter"
    if any(k in blob for k in ("hiring manager", "hm round", "manager round")):
        return "hiring_manager"
    if any(k in blob for k in ("exec", "cio", "cto", "vp ", "leadership")):
        return "exec"
    return "unknown"


def parse(html_text):
    raw = html_text

    # --- title + eyebrow ---
    m = re.search(r"<title>(.*?)</title>", raw, re.S | re.I)
    title = _strip_tags(m.group(1)) if m else ""
    m = re.search(r'class="page-eyebrow"[^>]*>(.*?)<', raw, re.S | re.I)
    eyebrow = _strip_tags(m.group(1)) if m else ""

    # --- nav hrefs (in document order, deduped) ---
    nav_hrefs = []
    nav_block = raw
    m = re.search(r'<nav.*?</nav>|class="sidebar".*?</div>\s*</div>', raw, re.S | re.I)
    # nav items live in the sidebar; just scan all anchor hrefs that point to ids
    for href in re.findall(r'class="nav-item[^"]*"[^>]*href="#([^"]+)"', raw):
        if href not in nav_hrefs:
            nav_hrefs.append(href)
    # template sometimes orders href before class; catch that too
    for href in re.findall(r'href="#([^"]+)"[^>]*class="nav-item', raw):
        if href not in nav_hrefs:
            nav_hrefs.append(href)

    # --- em dash contexts (visible content only: skip <style>/<script>) ---
    body = re.sub(r"<style.*?</style>|<script.*?</script>", "", raw, flags=re.S | re.I)
    em_contexts = []
    for m in re.finditer(r".{0,40}\u2014.{0,40}", _strip_tags(body)):
        em_contexts.append(m.group(0).strip())

    # --- every element id present, for nav resolution ---
    present_ids = re.findall(r'\bid="([^"]+)"', raw)

    # --- split into navigable section blocks ---
    # A navigable block is a <div> whose class list includes "section" or
    # "context-strip". Attribute order varies (id may appear before or after
    # class), so scan each <div ...> open tag and test its attributes rather
    # than assuming a fixed order.
    starts = []
    for m in re.finditer(r"<div\b([^>]*)>", raw):
        attrs = m.group(1)
        cls_m = re.search(r'class="([^"]*)"', attrs)
        id_m = re.search(r'id="([^"]+)"', attrs)
        if not cls_m or not id_m:
            continue
        classes = cls_m.group(1).split()
        if "section" in classes or "context-strip" in classes:
            starts.append((m.start(), id_m.group(1)))
    sections = []
    for i, (pos, sid) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(raw)
        block = raw[pos:end]
        # trim trailing footer/script if this is the last block
        block = re.split(r"<script\b|</main>", block, maxsplit=1)[0]

        text = _strip_tags(block)
        cue_count = len(re.findall(r"\[PAUSE\]|\[SLOW\]", block))

        # anchor bars within this section
        anchor_bars = []
        for ab in re.findall(r'class="anchor-bar".*?</div>', block, re.S):
            toks = re.findall(r'class="anc">([^<]+)<', ab)
            if toks:
                anchor_bars.append(AnchorBar(tokens=[t.strip() for t in toks]))

        # does this section carry a spoken script / story?
        is_script = bool(
            re.search(r'class="(story-card|beat|qa-|script|answer)', block)
        ) or len(anchor_bars) > 0

        # script-only text: drop probe blocks, cue tags, anchor bars, headers
        st = block
        st = re.sub(r'class="anchor-bar".*?</div>', " ", st, flags=re.S)
        st = re.sub(r'<[^>]*class="[^"]*probe[^"]*".*?</div>', " ", st, flags=re.S)
        st = re.sub(r'class="section-header".*?</div>', " ", st, flags=re.S)
        st = st.replace("[PAUSE]", " ").replace("[SLOW]", " ")
        script_text = _strip_tags(st)

        has_list = bool(
            re.search(r'class="story-card".*?<(ul|ol)\b', block, re.S)
        )

        sections.append(Section(
            id=sid, raw=block, text=text, script_text=script_text,
            is_script=is_script, cue_count=cue_count,
            anchor_bars=anchor_bars, has_list_in_story=has_list,
        ))

    return Doc(
        title=title, eyebrow=eyebrow,
        round_type=_detect_round(eyebrow, title),
        nav_hrefs=nav_hrefs, sections=sections,
        em_dash_contexts=em_contexts, present_ids=present_ids, raw=raw,
    )
