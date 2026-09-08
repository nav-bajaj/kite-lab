"""Extract Nifty 500 constituent changes from an NSE press-release text dump.

Layout of the releases (pdftotext -layout) is stable across 2020-2026:

    N) Nifty 500          (the prefix is a number OR a letter: "2)" / "b)")
    The following companies are being excluded:
      Sr. No.   Company Name              Symbol
        1       3M India Ltd.             3MINDIA
    The following companies are being included:
      ...

The section runs until the next "N) <index name>" header. Only a header whose
name is exactly "Nifty 500" counts - "Nifty500 Shariah", "Nifty500 Value 50"
and "Nifty Smallcap 500" are different indices that must not be folded in.

Table headers repeat when a table spans a page break, so header lines are
skipped rather than treated as terminators.
"""
from __future__ import annotations

import re
from datetime import datetime

SECTION_HDR = re.compile(r"^\s*([0-9]{1,2}|[a-zA-Z])[\)\.]\s*(.+?)\s*$")
ROW = re.compile(r"^\s*(\d{1,3})\s+(.+?)\s{2,}([A-Z0-9][A-Z0-9&.\-]*)\s*$")
# a row whose name column wrapped away entirely: "  16        JCHAC"
ORPHAN_ROW = re.compile(r"^\s*(\d{1,3})\s{4,}([A-Z0-9][A-Z0-9&.\-]*)\s*$")
# a bare continuation fragment of a company name (no number, no symbol)
NAME_FRAGMENT = re.compile(r"^\s{3,}([A-Za-z(][^\s].*?)\s*$")
HDR_ROW = re.compile(r"Sr\.?\s*No\.?\s+Company\s+Name", re.I)
EFF = re.compile(
    r"effective\s+from\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})", re.I)
EXCL_CUE = re.compile(r"being\s+excluded|are\s+excluded", re.I)
INCL_CUE = re.compile(r"being\s+included|are\s+included", re.I)
NONE_CUE = re.compile(r"No\s+(inclusion|exclusion|change)", re.I)
TERMINATORS = re.compile(r"About NSE Indices|Press contact|Disclaimer", re.I)


def effective_date(text: str):
    m = EFF.search(text)
    return _coerce(m.group(1)) if m else None


def _is_target_header(line: str) -> bool:
    """True only for the Nifty 500 itself.

    Case and inner spacing vary across years ("Nifty 500" in 2022+, "NIFTY 500"
    in 2021), so both are normalised away. The comparison stays an equality
    test rather than a prefix match because "Nifty500 Shariah", "Nifty 500
    Value 50" and "Nifty Smallcap 500" are separate indices.
    """
    m = SECTION_HDR.match(line)
    if not m:
        return False
    name = re.sub(r"\s+", " ", m.group(2)).strip().rstrip(":").upper()
    return name == "NIFTY 500"


def nifty500_sections(text: str) -> list[tuple[int, list[str]]]:
    """Every Nifty 500 section, as (start_line_index, lines).

    A release can carry more than one: the August 2020 release, for example,
    has a "NIFTY 500" eligibility-criteria table near the top and the actual
    semi-annual replacements much further down. Taking only the first finds
    the criteria table and silently reports no changes, so all of them are
    returned and the caller merges - non-replacement sections contribute no
    rows because they have no included/excluded cue.
    """
    lines = text.splitlines()
    starts = [i for i, ln in enumerate(lines) if _is_target_header(ln)]
    out = []
    for st in starts:
        body = []
        for ln in lines[st + 1:]:
            if TERMINATORS.search(ln):
                break
            m = SECTION_HDR.match(ln)
            if m and not ROW.match(ln):
                break
            body.append(ln)
        out.append((st, body))
    return out


def _effective_for(text: str, before_line: int):
    """Effective date governing the section starting at `before_line`.

    Releases bundle several changes with different effective dates, so the
    date that applies is the last one stated at or above the section header;
    the first date in the document is only a fallback.
    """
    lines = text.splitlines()
    for i in range(before_line, -1, -1):
        m = EFF.search(lines[i])
        if m:
            d = _coerce(m.group(1))
            if d:
                return d
    return effective_date(text)


def _coerce(raw: str):
    raw = re.sub(r"\s+", " ", raw.replace(",", " ")).strip()
    for fmt in ("%B %d %Y", "%b %d %Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    return None


def _unwrap(lines: list[str]) -> list[str]:
    """Rejoin table rows whose company-name column wrapped over two lines.

    Long names are laid out by pdftotext as a fragment above the numbered
    line, the number and symbol alone, then the rest of the name below:

            Johnson Controls - Hitachi Air Conditioning India
          16                                              JCHAC
            Ltd.

    Left alone the numbered line parses as a row with an empty name, which
    then fails to match any member. This folds the fragments back in.
    """
    out: list[str] = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        m = ORPHAN_ROW.match(ln)
        if m and not HDR_ROW.search(ln):
            num, sym = m.group(1), m.group(2)
            parts = []
            # fragment immediately above, if it was not already consumed
            if out and NAME_FRAGMENT.match(out[-1]) and not ROW.match(out[-1]):
                parts.append(out.pop().strip())
            j = i + 1
            while j < len(lines) and NAME_FRAGMENT.match(lines[j]) and \
                    not ROW.match(lines[j]) and not ORPHAN_ROW.match(lines[j]):
                parts.append(lines[j].strip())
                j += 1
            name = " ".join(parts).strip()
            out.append(f"  {num}   {name}   {sym}" if name else ln)
            i = j
            continue
        out.append(ln)
        i += 1
    return out


def parse_changes(text: str) -> dict:
    """-> {"excluded": [(name, symbol)], "included": [...], "effective": date}"""
    res = {"excluded": [], "included": [], "effective": None}
    for start, sec in nifty500_sections(text):
        bucket = None
        found = {"excluded": [], "included": []}
        for ln in _unwrap(sec):
            if EXCL_CUE.search(ln):
                bucket = "excluded"
                continue
            if INCL_CUE.search(ln):
                bucket = "included"
                continue
            if NONE_CUE.search(ln):
                bucket = None
                continue
            if HDR_ROW.search(ln):
                continue
            m = ROW.match(ln)
            if m and bucket:
                # trailing "*" / "#" are footnote markers, not part of the name
                name = m.group(2).strip().rstrip("*#^@").strip()
                sym = m.group(3).strip()
                if sym in {"Symbol", "Name"} or not name:
                    continue
                found[bucket].append((name, sym))
        if found["excluded"] or found["included"]:
            res["excluded"] += found["excluded"]
            res["included"] += found["included"]
            if res["effective"] is None:
                res["effective"] = _effective_for(text, start)
    if res["effective"] is None:
        res["effective"] = effective_date(text)
    return res
