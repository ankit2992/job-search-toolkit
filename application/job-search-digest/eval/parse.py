"""
parse.py — load a digest run record (criteria + returned jobs) from JSON and
provide the normalization helpers the rubric needs. Stdlib only.
"""

import json
import re
from dataclasses import dataclass


REQUIRED_FIELDS = ["title", "company", "location", "posted_date",
                   "url", "source", "role_family", "snippet"]

_SENIORITY_PREFIX = re.compile(
    r"^\s*(senior|sr\.?|staff|principal|lead|junior|jr\.?|associate)\s+", re.I)
_LEVEL_SUFFIX = re.compile(r"\b(i{1,3}|iv|v|[1-4])\b\.?\s*$", re.I)
_PUNCT = re.compile(r"[^\w\s]")
_WS = re.compile(r"\s+")


@dataclass
class Record:
    raw: dict
    criteria: dict
    jobs: list


def normalize_title(title):
    """Lowercase, drop a seniority prefix, drop text after a comma, drop a
    trailing level number/roman numeral, strip punctuation."""
    t = (title or "").split(",")[0].lower()
    t = _SENIORITY_PREFIX.sub("", t)
    t = _LEVEL_SUFFIX.sub("", t)
    t = _PUNCT.sub(" ", t)
    return _WS.sub(" ", t).strip()


def normalize_company(company):
    c = (company or "").lower()
    c = re.sub(r"\b(inc|llc|ltd|corp|co|the)\b", "", c)
    c = _PUNCT.sub(" ", c)
    return _WS.sub(" ", c).strip()


def load(path):
    data = json.load(open(path, encoding="utf-8"))
    return Record(raw=data, criteria=data.get("criteria", {}), jobs=data.get("jobs", []))
