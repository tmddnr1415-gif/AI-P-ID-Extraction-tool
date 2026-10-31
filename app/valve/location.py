"""Area and Unit of a datasheet — read from the documents, for the Excel filters (Issue List · Valve List).

Area   North · South · W15 (from the datasheet document title: 'CO2 SEQUESTRATION IN QELNG NORTH / QELNG SOUTH /
       W15 INJECTION AREA'), or Brownfield when the title names an existing plant system
       ('… QELNG SOUTH (SYSTEM 999 – UNIT 19)' — the datasheets themselves call these 'QELNG South Brownfield System 19')
       or the datasheet's notes say 'brownfield'.  Site keeps North / South / W15 for brownfield too.
Unit   the title's 'UNIT nn'; otherwise the P&ID number ('98-98-PR-PID-00011' → 98, '002-08-84-PR-DR-PI-104' → 84);
       otherwise the tag's leading digits ('315MOV980004' → 315).
Every answer carries how it was found ('basis'); nothing is filled when no document says it.
"""
from __future__ import annotations

import re

_SYS_UNIT = re.compile(r"SYSTEM\s*(\d+)\s*[-–—]\s*UNIT\s*(\d+)", re.I)


def title_for(doc_no: str, docs: dict) -> str:
    """The document title; when the sheets print another number than the cover ('02-09-IN-DTS-00006' on the sheets,
    '02-09-IN-DTS-00003' on the cover — flagged as a Data Error), the cover with the same system-unit prefix."""
    d = docs.get(doc_no) or {}
    if d.get("title"):
        return d["title"]
    m = re.match(r"^(\d+-\d+-[A-Z]+-[A-Z]+)-", doc_no or "")
    if m:
        for k, v in docs.items():
            if k.startswith(m.group(1) + "-") and v.get("title"):
                return v["title"]
    return ""


def locate(doc_no: str = "", title: str = "", pid_no: str = "", tag: str = "", notes_text: str = "") -> dict:
    t = (title or "").upper()
    site = "North" if "NORTH" in t else "South" if "SOUTH" in t else "W15" if "W15" in t else ""
    su = _SYS_UNIT.search(title or "")
    brown = bool(su) or bool(re.search(r"brown\s*-?\s*field", notes_text or "", re.I))
    area = "Brownfield" if brown else site
    basis = []
    if site:
        basis.append(f"title '{site.upper()}'")
    if su:
        basis.append(f"title 'SYSTEM {su.group(1)} - UNIT {su.group(2)}' (existing plant system)")
    elif brown:
        basis.append("datasheet notes say 'brownfield'")
    unit, ub = "", ""
    if su:
        unit, ub = su.group(2), "title"
    else:
        m = re.match(r"^\s*(\d+)-(\d+)-PR-PID", pid_no or "", re.I) or re.match(r"^\s*\d+-(\d+)-(\d+)-PR-", pid_no or "", re.I)
        if m:
            unit, ub = m.group(2), "P&ID No."
        else:
            m = re.match(r"^\s*(\d+)", tag or "")
            if m:
                unit, ub = m.group(1), "tag prefix"
    if unit:
        basis.append(f"unit from {ub}")
    return {"area": area, "site": site, "unit": unit, "system": su.group(1) if su else "", "basis": " · ".join(basis)}
