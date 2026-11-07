"""Comment digest (valve35) — fewer, readable comments.  Presentation only: every finding, its rule and its status stay
exactly as issues.compute made them; this only decides how they are SHOWN and PRINTED.

  block    on one page of one datasheet, three or more Data Missing findings of the same check (DM-01 required field ·
           DM-02 process data) whose boxes touch or sit one row apart -> ONE comment around the whole area:
           'Process data missing — 9 items (Fluid, Sour Service, …); ref. 98-98-PR-DTS-00023 (Note 8). Provide values.'
  typical  the same comment (same type · rule · wording — for a block the same items and reference) on two or more tags
           -> ONE row 'Typical — 62 tags', the tags listed under it (detail view keeps every one).

Reviewer comments, reviewer corrections and comments an engineer re-worded are never merged (their words are their own).
"""
from __future__ import annotations

import re
from statistics import median

BLOCK_CHECKS = {"DM-01": ("Datasheet data missing", "데이터시트 값 누락"),
                "DM-02": ("Process data missing", "Process Data 누락")}
MIN_BLOCK = 3
_REF = re.compile(r";\s*ref\.\s*(.+?)\.\s*Provide value\.$")
_SEV = {"Major": 0, "Minor": 1, "Info": 2, "Internal": 3}


def _name(i: dict) -> str:
    return re.sub(r"\s*\((?:Max/Nor/Min|Nor)\)$", "", str(i.get("field") or i.get("key") or ""))


def _own_words(i: dict) -> bool:
    return bool(i.get("comment_id") or i.get("edited") or i.get("type") in ("Reviewer Comment", "Reviewer Correction"))


def _union(bbs):
    bbs = [b for b in bbs if b]
    if not bbs:
        return None
    return [round(min(b[0] for b in bbs), 1), round(min(b[1] for b in bbs), 1), round(max(b[2] for b in bbs), 1), round(max(b[3] for b in bbs), 1)]


def _runs(items: list[dict]) -> list[list[dict]]:
    """Split one page's findings of one check into touching runs (top to bottom).  'Touching' = the next box starts no
    more than about one row below the previous ones (1.4 × the median row height on that page)."""
    with_bb = sorted((i for i in items if i.get("bbox")), key=lambda i: (i["bbox"][1], i["bbox"][0]))
    if not with_bb:
        return [[i] for i in items]
    gap = 1.4 * median(max(1.0, i["bbox"][3] - i["bbox"][1]) for i in with_bb)
    runs, cur, bottom = [], [], None
    for i in with_bb:
        if cur and i["bbox"][1] - bottom > gap:
            runs.append(cur)
            cur, bottom = [], None
        cur.append(i)
        bottom = i["bbox"][3] if bottom is None else max(bottom, i["bbox"][3])
    runs.append(cur)
    return runs + [[i] for i in items if not i.get("bbox")]


def _block(run: list[dict]) -> dict:
    i0, chk = run[0], run[0].get("check")
    en_head, ko_head = BLOCK_CHECKS[chk]
    names = list(dict.fromkeys(_name(i) for i in run))
    refs = {m.group(1) for m in (_REF.search(i.get("description") or "") for i in run) if m}
    ref = refs.pop() if len(refs) == 1 else ""
    lst = ", ".join(names)
    desc = f"{en_head} — {len(names)} items ({lst})" + (f"; ref. {ref}" if ref else "") + ". Provide values."
    desc_ko = f"{ko_head} — {len(names)}개 항목 ({lst})" + (f" — 참조 {ref}" if ref else "") + ". 값을 기입 바랍니다."
    sts = {i.get("status", "Open") for i in run}
    return {"kind": "block", "type": i0["type"], "check": chk, "color": i0.get("color"), "severity": min((i.get("severity") or "Major" for i in run), key=lambda s: _SEV.get(s, 9)),
            "description": desc, "description_ko": desc_ko, "field": f"{en_head.split()[0]} data ({len(names)})", "items": names, "ref": ref,
            "ds_id": i0.get("ds_id"), "tag": i0.get("tag"), "page": i0.get("page"), "sheet": i0.get("sheet"), "of": i0.get("of"),
            "bbox": _union(i.get("bbox") for i in run), "status": sts.pop() if len(sts) == 1 else "Mixed",
            "expected": "; ".join(f"{_name(i)}: {i['expected']}" for i in run if i.get("expected")),
            "members": run, "sig": ("block", i0["type"], chk, tuple(names), ref)}


def _single(i: dict) -> dict:
    return {"kind": "single", "type": i["type"], "check": i.get("check"), "color": i.get("color"), "severity": i.get("severity"),
            "description": i.get("description"), "description_ko": i.get("description_ko"), "field": i.get("field"),
            "ds_id": i.get("ds_id"), "tag": i.get("tag"), "page": i.get("page"), "sheet": i.get("sheet"), "of": i.get("of"),
            "bbox": i.get("bbox"), "status": i.get("status", "Open"), "expected": i.get("expected"), "members": [i],
            "sig": None if _own_words(i) else ("one", i["type"], i.get("check"), i.get("key"), i.get("description"), i.get("expected"))}


def blocks(rows: list[dict]) -> list[dict]:
    """Findings of one or many datasheets -> units (a block or a single finding), in the order the rows came."""
    groups: dict[tuple, list] = {}
    for i in rows:
        if i.get("type") == "Data Missing" and i.get("check") in BLOCK_CHECKS and not _own_words(i):
            groups.setdefault((i.get("ds_id"), i.get("page"), i.get("check")), []).append(i)
    in_block: dict[int, dict] = {}
    for items in groups.values():
        if len(items) < MIN_BLOCK:
            continue
        for run in _runs(items):
            if len(run) >= MIN_BLOCK:
                b = _block(run)
                for i in run:
                    in_block[id(i)] = b
    out, seen = [], set()
    for i in rows:
        b = in_block.get(id(i))
        if b is None:
            out.append(_single(i))
        elif id(b) not in seen:
            seen.add(id(b))
            out.append(b)
    return out


def digest(rows: list[dict], min_tags: int = 2) -> list[dict]:
    """Units -> typical rows (same comment on `min_tags` or more tags) and the rest, in the order the rows came."""
    units = blocks(rows)
    by_sig: dict[tuple, list] = {}
    for u in units:
        if u["sig"] is not None:
            by_sig.setdefault(u["sig"], []).append(u)
    out, done = [], set()
    for u in units:
        L = by_sig.get(u["sig"]) if u["sig"] is not None else None
        if not L or len({x["tag"] for x in L}) < min_tags:
            out.append(u)
            continue
        if u["sig"] in done:
            continue
        done.add(u["sig"])
        tags = list(dict.fromkeys(x["tag"] for x in L))
        sts = {x["status"] for x in L}
        out.append({**{k: u[k] for k in ("type", "check", "color", "description", "description_ko", "field", "expected")},
                    "kind": "typical", "of_kind": u["kind"], "severity": min((x["severity"] or "Major" for x in L), key=lambda s: _SEV.get(s, 9)),
                    "tags": tags, "n": len(L), "status": sts.pop() if len(sts) == 1 else "Mixed",
                    "units": L, "members": [m for x in L for m in x["members"]], "tag": tags[0], "ds_id": L[0]["ds_id"],
                    "page": L[0]["page"], "bbox": L[0]["bbox"]})
    return out


def typical_text(e: dict, lang: str = "en") -> str:
    """The heading a typical row prints: 'Typical (62 tags): …'."""
    if e.get("kind") != "typical":
        return ""
    return f"Typical ({len(e['tags'])} tags)" if lang == "en" else f"Typical ({len(e['tags'])}개 Tag 공통)"


def wire(entries: list[dict]) -> list[dict]:
    """For the screens: members as 'ds_id|ikey' references (the full findings are already on the page)."""
    def ref(i):
        return f"{i.get('ds_id')}|{i.get('ikey')}"

    def unit(u):
        return {k: v for k, v in {"kind": u["kind"], "ds_id": u.get("ds_id"), "tag": u.get("tag"), "page": u.get("page"), "sheet": u.get("sheet"),
                                  "bbox": u.get("bbox"), "field": u.get("field"), "status": u.get("status"), "severity": u.get("severity"),
                                  "m": [ref(i) for i in u["members"]]}.items() if v not in (None, "", [])}
    out = []
    for e in entries:
        w = {k: e.get(k) for k in ("kind", "type", "check", "color", "severity", "description", "description_ko", "field", "expected", "status")
             if e.get(k) not in (None, "")}
        w["m"] = [ref(i) for i in e["members"]]
        if e["kind"] == "typical":
            w.update(of_kind=e["of_kind"], tags=e["tags"], units=[unit(u) for u in e["units"]])
        else:
            w.update({k: e[k] for k in ("ds_id", "tag", "page", "sheet", "bbox") if e.get(k) not in (None, "")})
        out.append(w)
    return out
