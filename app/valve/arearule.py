"""Area from the tag's leading number — a rule LEARNED from the project's own documents, never typed into the code.

Evidence (each tag / document whose area a document states):
  · the Valve datasheets of the project family (area from the datasheet title / PDS cover, as the Valve first screen
    shows it: North · South · North Brownfield · South Brownfield · W15)
  · the process datasheets inside the Process Data annexure (each part's own title block)
From it two tables are counted:
  prefix → areas       the tag's leading digits ('98' of 98PT-1001, '315' of 315MOV980004)
  system → areas       the first segment of the document / P&ID number ('999' of 999-98-PR-PID-00001, '98' of 98-51-IN-…)
A prefix whose evidence all says one area decides it.  A prefix used in several areas (one new unit built on two sites)
is decided by the document / P&ID system of that tag when that system says one area.  Otherwise no area — and why.
"""
from __future__ import annotations

import collections
import re

_PRE = re.compile(r"^\s*(\d+)")
_SYS = re.compile(r"^\s*([0-9]{2,4})-")


def prefix(tag: str) -> str:
    m = _PRE.match(tag or "")
    return m.group(1) if m else ""


def system(no: str) -> str:
    """'999-98-PR-PID-00001' → '999' · '98-51-IN-DTS-00002' → '98' · '002-08-84-PR-DR-…' → '002' · 'D-84-1225' → ''."""
    m = _SYS.match(no or "")
    return m.group(1) if m else ""


def learn(evidence: list[dict]) -> dict:
    """evidence: [{tag?, doc_no?, zone}] → {prefix: {zone: n}, system: {zone: n}, pair: {(prefix, system): {zone: n}}, n}."""
    P, Y, PY = collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)
    n = 0
    for e in evidence:
        z = e.get("zone") or ""
        if not z or " · " in z:                           # a document naming several areas is no evidence for one
            continue
        p, s = prefix(e.get("tag", "")), system(e.get("doc_no", ""))
        if p:
            P[p][z] += 1
        if s:
            Y[s][z] += 1
        if p and s:
            PY[(p, s)][z] += 1
        n += 1
    return {"prefix": {k: dict(v) for k, v in P.items()}, "system": {k: dict(v) for k, v in Y.items()},
            "pair": {f"{a}|{b}": dict(v) for (a, b), v in PY.items()}, "n": n}


def _one(c: dict | None) -> str:
    return next(iter(c)) if c and len(c) == 1 else ""


def area_for(rule: dict, tag: str, doc_no: str = "", pid_no: str = "") -> tuple[str, str]:
    """(area, basis) for one tag; ('', why) when the evidence does not decide."""
    if not rule or not rule.get("n"):
        return "", ""
    p = prefix(tag)
    pc = rule["prefix"].get(p) if p else None
    if pc and len(pc) == 1:
        z = _one(pc)
        return z, f"Tag 앞 '{p}' = {z} (근거 {sum(pc.values())}건)"
    for no in (pid_no, doc_no):                             # the same prefix on two sites: the document / P&ID system decides
        s = system(no)
        if not s:
            continue
        z = _one(rule["pair"].get(f"{p}|{s}")) or (_one(rule["system"].get(s)) if pc else "")
        if z and (not pc or z in pc):
            return z, f"Tag 앞 '{p}' 는 {' · '.join(pc)} 에 다 쓰임 → 번호 '{s}-…' = {z}" if pc else f"번호 '{s}-…' = {z}"
    if not pc and p and _one(rule["system"].get(p)):        # the unit number also leads the documents ('03-02-PR-DTS-…')
        z = _one(rule["system"][p])
        return z, f"Tag 앞 '{p}' = 문서 번호 '{p}-…' 의 {z}"
    if not pc:
        s = system(pid_no) or system(doc_no)
        z = _one(rule["system"].get(s)) if s else ""
        if z:
            return z, f"Tag 앞 '{p}' 는 근거 없음 · 번호 '{s}-…' = {z}"
        return "", f"Tag 앞 '{p}' 의 Area 근거가 없음" if p else ""
    return "", f"Tag 앞 '{p}' 는 {' · '.join(pc)} 에 다 쓰임 — 문서 / P&ID 번호로 가를 수 없음"


def table(rule: dict) -> list[dict]:
    """The learned rule as rows for the screen: prefix · areas with counts · decided area or how it is split."""
    rows = []
    for p, c in sorted((rule or {}).get("prefix", {}).items(), key=lambda x: (len(x[0]), x[0])):
        split = {}
        if len(c) > 1:
            for k, v in rule["pair"].items():
                a, s = k.split("|")
                if a == p and len(v) == 1:
                    split[s] = next(iter(v))
        rows.append({"prefix": p, "areas": c, "n": sum(c.values()), "area": _one(c),
                     "by_system": split, "rule": _one(c) or (" · ".join(f"'{s}-…' → {z}" for s, z in sorted(split.items())) or "가를 수 없음")})
    return rows
