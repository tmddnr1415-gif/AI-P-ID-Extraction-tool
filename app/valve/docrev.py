"""Which revision of a reference document is loaded — read from the document itself (valve29, first screen).

    read(path) -> {"doc_no", "rev", "date", "desc", "header_rev", "parts": [{"doc_no", "rev", "date", "desc", "page"}]}

Two places say it, both read only from the PDF text layer (no OCR, nothing guessed):
  · the page header block  'Doc. No.: 98-98-PI-SPC-00001 … Rev. 0'                 → doc_no · header_rev
  · the revision table      rows 'REV | DATE | DESCRIPTION' (top or bottom of a cover) → rev · date · desc of the newest row
A row is a rev token (0 · 1 · A · B …) and a date on the same line (|dy| < 4 pt) near a 'REV' heading.  The newest row is
the one with the latest date (day-first dates, as on these documents); when no date can be read, rev/date stay empty and
the header revision is shown instead.  A Process Data PDF is usually a requisition annexure holding several process
datasheets (…-PR-DTS-…): each one's own revision table is read as a `part`.
"""
from __future__ import annotations

import datetime as dt
import re

import pymupdf

_MON = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}
_DATE = re.compile(r"^(\d{1,2})[/.\-]([A-Za-z]{3}|\d{1,2})[/.\-](\d{2}|\d{4})$")
_REVTOK = re.compile(r"^(?:\d{1,2}|[A-Z])$")
_PART = re.compile(r"\b\d{2,3}-\d{2,3}-[A-Z]{2}-DTS-\d{5}\b")


def parse_date(s: str) -> dt.date | None:
    """'08/09/2026' · '20/Sep/2026' · '19/9/2026' · '20-Sep-26' → date (day first).  None when it is not a date."""
    m = _DATE.match(str(s or "").strip())
    if not m:
        return None
    d, mo, y = m.groups()
    mo = _MON.get(mo.lower()[:3]) if mo.isalpha() else int(mo)
    y = int(y) + (2000 if len(y) == 2 else 0)
    try:
        return dt.date(y, mo, int(d))
    except (TypeError, ValueError):
        return None


def rev_table(page) -> dict | None:
    """Newest row of the revision table on this page: {rev, date, desc} (date as written on the document)."""
    words = page.get_text("words")
    heads = [w for w in words if re.fullmatch(r"REV\.?|Rev\.?", w[4])]
    if not heads:
        return None
    rows = []
    for w in words:
        if not _REVTOK.match(w[4]):
            continue
        for h in heads:                                     # the rev column sits under / over its heading
            if abs((w[0] + w[2]) / 2 - (h[0] + h[2]) / 2) < 30 and 0 < abs(w[1] - h[1]) < 200:
                break
        else:
            continue
        line = sorted((x for x in words if abs(x[1] - w[1]) < 4 and x[0] > w[2]), key=lambda x: x[0])
        date = next((x[4] for x in line if parse_date(x[4])), None)
        if not date:
            continue
        desc = " ".join(x[4] for x in line if x[4] != date and not parse_date(x[4]))
        desc = re.split(r"\s{2,}|\b[A-Z]{2,3}\s*/\s*[A-Z]{2,3}\b", desc)[0].strip()
        rows.append({"rev": w[4], "date": date, "desc": desc[:80], "_d": parse_date(date), "_y": w[1]})
    if not rows:
        return None
    best = max(rows, key=lambda r: (r["_d"], -r["_y"]))
    return {k: best[k] for k in ("rev", "date", "desc")}


def read(path) -> dict:
    out = {"doc_no": "", "rev": "", "date": "", "desc": "", "header_rev": "", "parts": []}
    try:
        doc = pymupdf.open(path)
    except Exception:                                       # noqa: BLE001  (unreadable file: nothing to show, nothing invented)
        return out
    try:
        first = doc[0].get_text() if doc.page_count else ""
        m = re.search(r"Doc\.?\s*No\.?\s*:?\s*\n?\s*([A-Z0-9][A-Z0-9\-_/]{6,})", first)
        out["doc_no"] = m.group(1) if m else ""
        m = re.search(r"\bRev\.?\s*([0-9]{1,2}|[A-Z])\b\s*,?", first)
        out["header_rev"] = m.group(1) if m else ""
        t = rev_table(doc[0]) if doc.page_count else None
        if t:
            out.update(t)
        seen = set()
        for i in range(doc.page_count):                     # process datasheets inside a requisition annexure
            txt = doc[i].get_text()
            for p in _PART.findall(txt):
                if p in seen or p == out["doc_no"]:
                    continue
                seen.add(p)
                r = rev_table(doc[i]) or {}
                out["parts"].append({"doc_no": p, "page": i + 1, "rev": r.get("rev", ""), "date": r.get("date", ""), "desc": r.get("desc", "")})
    finally:
        doc.close()
    return out


def newest(items: list[dict]) -> dict | None:
    """The item with the latest readable date."""
    dated = [x for x in items if parse_date(x.get("date"))]
    return max(dated, key=lambda x: parse_date(x["date"])) if dated else None
