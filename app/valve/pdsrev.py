"""valve43 — Process Data Sheet (PDS) revision comparison (user 2026-11-26: '같은 PDS 명의 수정 PDS 를 넣으면 이전 Rev. 과
비교한 검토 결과를 Excel 로').

When a PDS whose document number is already loaded comes in again (a new Rev.), every On-Off / MOV tag of the earlier
Rev. is compared with the new one, column by column:

  Status   Changed · No Change · New (not in the earlier Rev.) · Delete (not found in the new Rev.) ·
           (valve44, user 2026-11-26: which tag became which is never guessed — only the same tag number is compared)
  중요도   High — sizing / rating inputs (Line · Valve Size, Bore, Design P/T, Max ΔP, Pipe Class rating letter)
           Med  — process inputs (Operating P/T, flow, ΔP, density, viscosity, phase, fluid, operating time, tightness,
                  fail position, actuator, quantity, pipe-class code scheme with the same rating letter)
           Min  — document consistency (location, P&ID, Line No notation, MW, normal position, notes, remarks, 'FV/')
           a numeric change of 2 % or less is one level lower; a value written where the earlier Rev. had none is Min;
           quote / separator differences (18' · 18", P98-6"(X)-N · P98-6(X)N) are not changes.
Nothing is guessed: both values are what the two PDFs say; a column only one Rev. has is shown, not compared."""
from __future__ import annotations

import re

from app.valve import schema

# (key, header) — the columns of a comparison sheet after No · Status · Tag · Rev. · Row
FIELDS = [
    ("location", "Location"), ("quantity", "Quantity"), ("pid_no", "PID No"), ("valve_type", "Valve type"), ("line_no", "Line No"),
    ("line_size", "Line Size"), ("valve_size", "Valve Size"), ("bore", "Valve Bore"), ("piping_class", "Pipe Class"),
    ("fluid", "Service Fluid"), ("fluid_state", "Phase"), ("flow", "Flow Rate (m3/h)"), ("max_dp", "Max Pressure Drop (bar)"),
    ("op_temp", "Operating Temp (°C)"), ("design_temp", "Design Temp (°C)"), ("op_pressure", "Operating Press (barg)"),
    ("design_pressure", "Design Press (barg)"), ("mol_weight", "MW (kg/kmol)"), ("density", "Density (kg/m3)"),
    ("viscosity", "Viscosity (cP)"), ("dp_open", "Max ΔP Opening (bar)"), ("dp_close", "Max ΔP Closing (bar)"),
    ("stroke_open_s", "Op. Time Open (s)"), ("stroke_close_s", "Op. Time Close (s)"), ("normal_position", "Normal Position"),
    ("fail_position", "Fail Safe Position"), ("tightness", "Tightness"), ("act_type", "Actuator"),
    ("dense_phase", "Dense/Supercritical CO2"), ("notes", "Notes"), ("remarks", "Remarks"),
]
HIGH = {"line_size", "valve_size", "bore", "design_pressure", "design_temp", "dp_open", "dp_close"}
MED = {"op_pressure", "op_temp", "flow", "max_dp", "density", "viscosity", "fluid_state", "fluid", "stroke_open_s", "stroke_close_s",
       "tightness", "fail_position", "act_type", "quantity"}
NUMERIC = {"flow", "max_dp", "op_temp", "design_temp", "op_pressure", "design_pressure", "mol_weight", "density", "viscosity",
           "dp_open", "dp_close", "stroke_open_s", "stroke_close_s", "quantity"}
LEVELS = ("Min", "Med", "High")
SIZE_KEYS = ("line_size", "valve_size")
# x.<label> columns of the reader that are one of the fields under another spelling
ALIASES = {"fail_position": ("fail_position", "x.fail_safe_position", "x.safety_position"),
           "act_type": ("act_type", "x.actuator", "x.actutaor_driver_type", "x.actuator_driver_type")}
OUT_OF_SCOPE = re.compile(r"control valve|pressure relief|relief valve|\bpsv\b|safety valve", re.I)


def _field(values: dict, key: str) -> str | None:
    """The cell the PDF gives for a field — None when the PDF has no such column, '' when it is empty."""
    if key == "dense_phase":
        k = next((k for k in values if k.startswith("x.dense")), None)
        return values[k]["v"] if k else None
    for k in ALIASES.get(key, (key,)):
        if k in values:
            return values[k]["v"]
    return None


def _has_col(columns: list[dict], key: str) -> bool:
    keys = {c.get("key") or "x." + re.sub(r"[^a-z0-9]+", "_", c.get("label", ""))[:30] for c in columns}
    if key == "dense_phase":
        return any(k.startswith("x.dense") for k in keys)
    return any(k in keys for k in ALIASES.get(key, (key,)))


def _blank(v) -> bool:
    return v is None or str(v).strip() in ("", "-", "–", "N/A", "NA")


def _num(v):
    m = re.fullmatch(r"\s*(?:FV\s*/\s*)?([-+]?\d+(?:\.\d*)?|[-+]?\.\d+)\s*", str(v or ""), re.I)
    return float(m.group(1)) if m else None


def _txt(v) -> str:                                          # spaces next to punctuation are notation: ', FV' · ',FV' · 'API5L- X65'
    return re.sub(r"\s*([,;:/()\-])\s*", r"\1", re.sub(r"\s+", " ", str(v or "")).strip().upper())


def _sep(v) -> str:                                          # Line No / P&ID: separators and quotes are notation
    return re.sub(r"[^A-Z0-9]", "", _txt(v))


def _size(v) -> str:
    return re.sub(r"\s+", "", _txt(v).replace("'", '"').replace("”", '"').replace("″", '"')).rstrip('"')


def _down(level: str) -> str:
    return LEVELS[max(0, LEVELS.index(level) - 1)]


def judge(key: str, old, new) -> str | None:
    """The importance of one cell's change ('High' · 'Med' · 'Min'), None when it is not a change."""
    if _blank(old) and _blank(new):
        return None
    if key in SIZE_KEYS or key == "bore":
        if _size(old) == _size(new):
            return None
    elif key in ("line_no", "pid_no"):
        if _sep(old) == _sep(new):
            return None
    elif _txt(old) == _txt(new):
        return None
    if key == "piping_class":
        if _blank(old) or _blank(new):
            return "Min"
        return "High" if _txt(old)[:1] != _txt(new)[:1] else "Med"
    level = "High" if key in HIGH else "Med" if key in MED else "Min"
    if _blank(old):                                          # a value written where the earlier Rev. had none
        return "Min"
    if key == "design_pressure" and re.match(r"\s*FV\s*/", str(new or ""), re.I) and not re.match(r"\s*FV\s*/", str(old or ""), re.I):
        a, b = _num(old), _num(new)
        if a is not None and a == b:
            return "Min"                                     # only 'FV/' added
    if key in NUMERIC:
        a, b = _num(old), _num(new)
        if a is not None and b is not None:
            if a == b:
                return None                                  # '36.' · '36.00' · '36'
            if abs(a - b) <= 0.02 * max(abs(a), abs(b)):
                return _down(level)
    return level


def _rows(parsed: dict, scope_only: bool = True) -> tuple[dict, dict]:
    """{tag_key: flat row} of the On-Off / MOV tables of a parsed PDS (process.read_process_data), and per-section facts."""
    cols, sections = [], set()
    titles = {}
    for p in parsed.get("pages", []):
        titles[p["page"]] = p.get("title", "")
    out = {}
    for r in parsed.get("rows", []):
        title = titles.get(r.get("page"), "")
        if OUT_OF_SCOPE.search(title):                       # Control Valve · PSV sections are not compared
            if scope_only:
                continue
            sec = "Control Valve · PSV"
        else:
            sec = "MOV" if re.search(r"motor operated", title, re.I) else "On-Off"
        sections.add(sec)
        if r["tag_key"] in out:
            continue
        flat = {k: _field(r["values"], k) for k, _ in FIELDS}
        flat.update(tag=r["tag"], tag_key=r["tag_key"], page=r.get("page"), section=sec)
        out[r["tag_key"]] = flat
    for p in parsed.get("pages", []):
        cols.extend(p.get("columns") or [])
    have = {k for k, _ in FIELDS if _has_col(cols, k)} if cols else {k for k, _ in FIELDS}
    return out, {"sections": sections, "columns": have}


def _diff(o: dict, n: dict, both: set) -> dict:
    return {k: lv for k, _ in FIELDS if k in both and (lv := judge(k, o.get(k), n.get(k)))}


def _top(d: dict) -> str:
    return max(d.values(), key=LEVELS.index) if d else ""


_STOP = {"TO", "FROM", "OF", "AND", "THE", "IN", "AT", "FOR", "ON", "WITH", "VIA", "&"}   # small words: not a place
RENAMED = "Tag 변경"         # valve49: a New tag the engineer tied to an earlier (Delete) tag — never guessed by the program


def compare(old: dict, new: dict, links: dict | None = None) -> dict:
    """old · new = parsed PDS (process.read_process_data, the earlier and the newer Rev. of one document number).
    links = {new tag_key: {"old": earlier tag_key, "by", "at"}} — set by the engineer on the screen (valve49, user 2026-11-27:
    'New 에 이전 Tag(분석 결과 Delete)를 병기 → Tag 변경으로 관리 · Summary 에 반영').  A link counts only where the new tag
    is New and the earlier tag is Delete in THIS pair; the pair is then compared like a Changed tag.
    → {"items": [{status, tag, old_tag, old, new, imp: {key: level}, overall, note, section, link}], "counts": {...}, ...}"""
    O, fo = _rows(old)
    N, fn = _rows(new)
    both = fo["columns"] & fn["columns"]
    items = []
    linked = {nk: L for nk, L in (links or {}).items() if nk in N and nk not in O and L.get("old") in O and L["old"] not in N}
    used_old = {L["old"] for L in linked.values()}
    # user 2026-11-26: no guessing which tag became which — the same tag number is compared, every other tag of the
    # earlier Rev. is Delete and every other tag of the newer Rev. is New
    for k in N:                                              # 1. the same tag in both Revs.
        if k in O:
            imp = _diff(O[k], N[k], both)
            items.append({"status": "Changed" if imp else "No Change", "tag": N[k]["tag"], "tag_key": k, "old": O[k], "new": N[k],
                          "imp": imp, "overall": _top(imp), "note": "", "section": N[k]["section"]})
    for k in N:                                              # 2. only in the new Rev.: tied by the engineer, or New
        if k in linked:
            L = linked[k]
            o = O[L["old"]]
            imp = _diff(o, N[k], both)
            items.append({"status": RENAMED, "tag": N[k]["tag"], "tag_key": k, "old_tag": o["tag"], "old": o, "new": N[k], "imp": imp,
                          "overall": _top(imp), "section": N[k]["section"], "link": {"old": L["old"], "by": L.get("by", ""), "at": L.get("at", "")},
                          "note": f"Tag 변경 (사용자 지정{(' · ' + L['by']) if L.get('by') else ''}{(' · ' + L['at'][:10]) if L.get('at') else ''}): "
                                  f"이전 Rev. {o['tag']} → 최신 Rev. {N[k]['tag']}"})
        elif k not in O:
            items.append({"status": "New", "tag": N[k]["tag"], "tag_key": k, "old": None, "new": N[k], "imp": {},
                          "overall": "New", "note": "", "section": N[k]["section"]})
    for k in O:                                              # 3. not in the new Rev. (and not tied to a new tag)
        if k not in N and k not in used_old:
            sec = O[k]["section"]
            note = (f"최신 Rev. 에 {sec} 섹션 미수록 – 삭제 또는 별도 문서 이관 여부 확인 필요" if sec not in fn["sections"] else "")
            items.append({"status": "Delete", "tag": O[k]["tag"], "tag_key": k, "old": O[k], "new": None, "imp": {},
                          "overall": "Delete", "note": note, "section": sec})
    # valve55 (user 2026-11-27: 'Location 과 Line Size 기준으로 삭제 · 추가가 아닌 Tag 변경이 의심되면 별도 표기'): a HINT only —
    # a New and a Delete of this pair with the same Location and the same Line Size name each other; New · Delete stay
    # (the engineer decides with a link, valve49).  Notation-insensitive (spaces next to punctuation · quote marks).
    # Location by its words (a revised PDS rewords it: 'DEHYDRATED CO2 GAS TO 98-V9814' → '… FROM TEG CONTACTOR 1 TO 4TH STAGE
    # KOD (98-V9814)'): at least 60 % of the shorter Location's words in the other, small words left out; Line Size equal.
    def _words(row):
        return set(re.findall(r"[A-Z0-9]+", _txt((row or {}).get("location")))) - _STOP

    def _same_place(a, b):
        A, B = _words(a), _words(b)
        ls_a, ls_b = _size((a or {}).get("line_size")), _size((b or {}).get("line_size"))
        if len(A) < 2 or len(B) < 2 or not ls_a or _blank(ls_a) or ls_a != ls_b:
            return False
        return len(A & B) >= 0.6 * min(len(A), len(B))
    def _line(row):                                          # line number + size, without the class: 'P98981131-10"(XC0KL-A)-N' → 'P9898113110'
        ln, pc = _sep((row or {}).get("line_no")), _sep((row or {}).get("piping_class"))
        i = ln.find(pc) if pc else -1
        return ln[:i] if i > 0 else ln

    def _pid(row):
        m = re.search(r"(\d{3,6})\s*$", str((row or {}).get("pid_no") or ""))
        return m.group(1) if m else ""

    def _score(o, n):                                        # same line · same P&ID, one point each — ranks the candidates, decides nothing
        return bool(_line(o) and _line(o) == _line(n)) + bool(_pid(o) and _pid(o) == _pid(n))
    news = [it for it in items if it["status"] == "New"]
    dels = [it for it in items if it["status"] == "Delete"]
    # valve57 (accuracy): a reworded Location hid real pairs ('PROPANE INLET TO CO2 COOLER' → 'CO2 COOLER (98-E9825) PROPANE
    # INLET' was caught, 'PROPANE REFRIGERANT TO CO2 COOLER' → 'FROM TEG CHILLER PACKAGE TO CO2 COOLER' was not) — the same
    # line (number + size) on the same P&ID is a second ground.  Pairs the engineer marked 'not this' are left out.
    def _same_line(a, b):
        return bool(_line(a) and _line(a) == _line(b) and _pid(a) and _pid(a) == _pid(b))
    no = {k[1:] for k in (links or {}) if k.startswith("!")}
    why = {}
    pairs = {}
    for n in news:
        for o in dels:
            if f"{n['tag_key']}|{o['tag_key']}" in no:
                continue
            place, line = _same_place(o["old"], n["new"]), _same_line(o["old"], n["new"])
            if place or line:
                pairs[(id(o), id(n))] = _score(o["old"], n["new"])
                why[(o["tag"], n["tag"])] = (["Location · Line Size"] if place else []) + (["Line 번호 · P&ID"] if line else [])
    best_n = {}
    best_o = {}
    for (oi, ni), sc in pairs.items():
        best_n[ni] = max(best_n.get(ni, -1), sc)
        best_o[oi] = max(best_o.get(oi, -1), sc)
    for n in news:                                           # shown only where each is the other's best match (ties: all)
        for o in dels:
            sc = pairs.get((id(o), id(n)))
            if sc is not None and sc == best_n[id(n)] and sc == best_o[id(o)]:
                n.setdefault("suspect", []).append(o["tag"])
                o.setdefault("suspect", []).append(n["tag"])
    # valve56 (user 2026-11-27: '변경 의심 Tag 에 대해 이전 · 최신 · 변경 의심 값도 행을 추가해서 — 프로세스 데이터'): each suspected
    # tag's process data comes with the item, and the columns where it differs from the item's own values
    by_tag = {it["tag"]: it for it in items if it["status"] in ("New", "Delete")}
    for it in items:
        for t in it.get("suspect", []):
            other = by_tag.get(t)
            if not other:
                continue
            mine, theirs = (it["new"], other["old"]) if it["status"] == "New" else (it["old"], other["new"])
            it.setdefault("suspect_vals", []).append({
                "tag": t, "side": "old" if it["status"] == "New" else "new",
                "why": why.get((t, it["tag"]) if it["status"] == "New" else (it["tag"], t), []),
                "values": {k: (theirs or {}).get(k) for k, _ in FIELDS},
                "diff": [k for k, _ in FIELDS if k in both and judge(k, (mine or {}).get(k), (theirs or {}).get(k))]})
    order = {k: i for i, k in enumerate(N)}
    oorder = {k: i for i, k in enumerate(O)}
    rank = {"Delete": 2, "New": 0}
    items.sort(key=lambda it: (rank.get(it["status"], 0) == 2, order.get(it["tag_key"], len(order) + oorder.get(it["tag_key"], 0))))
    counts = {"old_tags": len(O), "new_tags": len(N)}
    for it in items:
        s = it["status"]
        if s in ("Changed", RENAMED):
            if it["overall"]:
                counts[f"changed_{it['overall'].lower()}"] = counts.get(f"changed_{it['overall'].lower()}", 0) + 1
        counts[s] = counts.get(s, 0) + 1
    excluded = sorted((fn["columns"] - fo["columns"]) | (fo["columns"] - fn["columns"]))
    return {"items": items, "counts": counts, "excluded_columns": [dict(FIELDS)[k] for k in excluded],
            "old_sections": sorted(fo["sections"]), "new_sections": sorted(fn["sections"])}


# valve48 (user 2026-11-27: '변경 summary 도 별도로') — the numbers of the Excel's Summary and Sizing sheets, for the screen.
# (key, group, item, basis, test(item) → bool) — the same definitions as the Sizing sheet's formulas.
SIZING_KEYS = ("line_size", "valve_size", "bore", "piping_class", "design_temp", "design_pressure", "dp_open", "dp_close")


def _has(it, keys, levels):
    return any(it["imp"].get(k) in levels for k in keys)


SIZING = [
    ("line_size", "Size", "Line Size 변경", "Line Size 값 변경", lambda it: _has(it, ("line_size",), ("High", "Med"))),
    ("valve_size", "Size", "Valve Size 변경", "Valve Size 값 변경 (Valve 재선정)", lambda it: _has(it, ("valve_size",), ("High", "Med"))),
    ("bore", "Size", "Valve Bore 변경", "Full/Reduced Bore 변경 (공란→값 추가 제외)", lambda it: _has(it, ("bore",), ("High", "Med"))),
    ("design", "Sizing 영향", "Design Pressure / Temperature 변경", "Rating·재질·Seat 재검토 (FV 표기 추가·2% 이내 소폭 변경 제외)",
     lambda it: _has(it, ("design_temp", "design_pressure"), ("High", "Med"))),
    ("dp", "Sizing 영향", "Max ΔP (Opening/Closing) 변경", "Actuator Torque 재계산", lambda it: _has(it, ("dp_open", "dp_close"), ("High", "Med"))),
    ("class_rating", "Sizing 영향", "Pipe Class Rating 변경", "Class 첫 문자(Rating) 변경 → Rating/재질 재검토", lambda it: _has(it, ("piping_class",), ("High",))),
    ("class_scheme", "Sizing 영향", "Pipe Class 코드 체계 변경", "Rating 문자 동일 – PMS로 재질/Rating 확인", lambda it: _has(it, ("piping_class",), ("Med",))),
    ("high", "Sizing 영향", "Ball Sizing 영향 큰 변경 (High)", "위 Size/설계조건/ΔP 중 High 1개 이상 → Size·Torque 재검토 필요",
     lambda it: _has(it, SIZING_KEYS, ("High",))),
    ("med", "Sizing 영향", "공정조건 변경 (Med)", "운전 P/T, 유량, 밀도, 상, 운전시간 등 – 재확인 권장 (High 없는 Tag)", lambda it: it["overall"] == "Med"),
    ("min", "Sizing 영향", "문서 정합성 변경만 (Min)", "Location, P&ID, Line No 표기 등 – Sizing 영향 없음", lambda it: it["overall"] == "Min"),
    ("nochange", "Sizing 영향", "변경 없음", "No Change", lambda it: it["status"] == "No Change"),
    ("new", "추가/삭제", "New (추가)", "이전 Rev.에 없음", lambda it: it["status"] == "New"),
    ("delete", "추가/삭제", "Delete (삭제) – 전체", "최신 Rev.에서 미확인", lambda it: it["status"] == "Delete"),
    ("delete_mov", "추가/삭제", "  └ 그중 MOV", "최신 Rev.에 MOV 섹션 없음 – 이관 여부 확인", lambda it: it["status"] == "Delete" and "MOV" in it["tag"].upper()),
    ("suspect", "추가/삭제", "변경 의심 (미확정)", "New 중 Location·Line Size 또는 Line 번호·P&ID 가 같은 Delete 가 있음 – Rev. 비교에서 확정/아님",
     lambda it: it["status"] == "New" and bool(it.get("suspect"))),
    ("renamed", "추가/삭제", "Tag 변경 (사용자 지정)", "New 에 이전 Tag 를 병기 – 그 Tag 와 비교 (New · Delete 에서 빠짐)", lambda it: it["status"] == RENAMED),
]


def change_summary(R: dict) -> dict:
    """compare(...) → {"counts": Summary-sheet row, "sizing": {key: [tags]}, "high": [rows], "size": [rows]} (Excel's numbers)."""
    items = R["items"]
    c = R["counts"]
    counts = {"old_tags": c["old_tags"], "new_tags": c["new_tags"], "High": c.get("changed_high", 0), "Med": c.get("changed_med", 0),
              "Min": c.get("changed_min", 0), "No Change": c.get("No Change", 0), "New": c.get("New", 0), "Delete": c.get("Delete", 0),
              RENAMED: c.get(RENAMED, 0)}
    sizing = {k: [it["tag"] for it in items if test(it)] for k, _, _, _, test in SIZING}
    lab = dict(FIELDS)
    renamed = [{"tag": it["tag"], "old_tag": it.get("old_tag", ""), "overall": it["overall"], "note": it["note"]} for it in items if it["status"] == RENAMED]
    high = [{"tag": it["tag"], "old_tag": it.get("old_tag", ""), "item": lab[k], "key": k, "old": (it["old"] or {}).get(k), "new": (it["new"] or {}).get(k), "status": it["status"]}
            for it in items for k, lv in it["imp"].items() if lv == "High"]
    size = [{"tag": it["tag"], "old_tag": it.get("old_tag", ""), "item": lab[k], "key": k, "old": (it["old"] or {}).get(k), "new": (it["new"] or {}).get(k)}
            for it in items for k, lv in it["imp"].items() if k in SIZE_KEYS and lv in ("High", "Med")]
    return {"counts": counts, "sizing": sizing, "high": high, "size": size, "renamed": renamed}


# ── the document's revision ────────────────────────────────────────────────────────────────────────────────────────

_REV_FOOT = re.compile(r"\b\d{2,4}-\d{2}-[A-Z]{2}-[A-Z]{3}-\d{5}[_ ]Rev\.?\s*([A-Z]?\d{0,2})\b", re.I)
_REV_BLOCK = re.compile(r"SHT\.\s+REV\.\s+1\s+([A-Z]\d?|\d{1,2})\s", re.I)
_REV_NAME = re.compile(r"\d{5}(?:_\d{4})?[_ -]+(?:Rev\.?\s*)?([A-Z]\d?|\d{1,2})(?=[_ .-]|$)", re.I)


def rev_of(text_pages: list[str], filename: str = "") -> str:
    """'B' · 'C0' · '0' — the file name right after the document number ('…-00023_C0.pdf' · '…-00023_0001_0_…'), else the
    footer '<doc no>_Rev.0', else the title block 'SHT. REV. 1 <rev>' (an advance copy can keep the earlier block)."""
    m = _REV_NAME.search(filename or "")
    if m:
        return m.group(1).upper()
    for t in text_pages[1:3] + text_pages[:1]:
        m = _REV_FOOT.search(t or "")
        if m and m.group(1):
            return m.group(1).upper()
    m = _REV_BLOCK.search(re.sub(r"\s+", " ", text_pages[0] if text_pages else "") + " ")
    return m.group(1).upper() if m else ""


def tagkey(t: str) -> str:
    return schema.norm_tag(t)


# ── the Excel (the layout of the engineers' own comparison workbook) ─────────────────────────────────────────────────

FILL_STATUS = {"Changed": "FFF2CC", "No Change": "", "New": "C6E0B4", "Delete": "D9D9D9", "Tag 변경": "F8CBAD"}
FILL_LEVEL = {"High": "FFC7CE", "Med": "FFEB9C", "Min": "E2EFDA"}
WIDTHS = {"A": 5, "B": 13, "C": 15, "D": 14, "E": 7, "F": 7, "G": 22, "H": 9, "I": 16, "J": 9, "K": 22, "L": 9, "M": 9, "N": 9,
          "O": 9, "P": 11}
LANGS = ("ko", "en")

# valve45 (user 2026-11-26: '이런 양식으로 영어와 한글 선택적으로') — every word the workbook writes, per language.
# Status words · importance levels · field headers stay as the engineers write them (English) in both.
T = {
    "ko": {
        "prev": "이전", "new": "최신", "imp": "중요도", "spare": "이전 Tag", "overall": "중요도(종합)", "note": "비고 / 사유",
        "suspect": '(변경 의심 "{t}")', "susrow": '변경 의심', "no_prev": "(이전 Rev. 없음)", "no_new": "({r} 미확인)", "high_sheet": "High 변경 목록", "size_sheet": "Summary (Sizing 영향)",
        "sheet_title": "{L}. {dn}{area} – {o} vs {n} Process Data 변경 비교",
        "sheet_note": "각 Tag: 1행 이전 Rev. / 2행 최신 {n}(변경값 붉은 글씨) / 3행 중요도(변경 항목별 High·Med·Min). "
                      "Status·Tag·종합 중요도는 1행에만 표기. 중요도 기준은 Summary 시트 참조.",
        "sum_title": "Process Data Sheet (On-Off Valve / MOV) Rev. 비교 Summary",
        "sum_note": "출처: 각 DTS 최신 Rev. vs 이전 Rev. ({files}). 수치는 각 시트를 COUNTIFS로 집계.",
        "sum_cols": ["Doc", "Doc No.", "Area", "이전 Rev.", "이전 Tag 수", "{n} Tag 수", "Changed (High)", "Changed (Med)", "Changed (Min)",
                     "No Change", "New", "Delete", "Tag 변경"],
        "total": "합계", "crit_title": "중요도 기준 (Size 변경 / Sizing Cal. 영향)",
        "crit": [
            ("High", "Line Size, Valve Size, Valve Bore, Design Pressure, Design Temperature, Max ΔP(Opening/Closing), Pipe Class Rating 문자 변경 "
                     "→ Valve Size·Rating·Actuator Torque 재검토 필요"),
            ("Med", "Operating P/T, Flow rate, Max Pressure Drop, Density, Viscosity, Phase, Service Fluid, Operating Time, Tightness, "
                    "Fail-safe/Actuator, Quantity, Pipe Class 코드 체계 변경(Rating 문자 동일) → Sizing 입력값 영향, 재확인 권장"),
            ("Min", 'Location, P&ID No, Line No 표기, MW, Normal Position, Notes, Remarks, Design P의 "FV/" 표기 추가 → Sizing 영향 없음(문서 정합성)'),
            ("보정", "수치 변경폭이 2% 이하이면 한 단계 낮춤(High→Med, Med→Min). Line/Valve Size의 따옴표 표기 차이(18' vs 18\")와 "
                     "Line No/P&ID의 구분기호 차이는 변경으로 보지 않음."),
            ("Status", "Changed / No Change / New(이전 Rev.에 없고 {n}에 있음) / Delete(이전 Rev.에 있고 {n}에 없음). "
                       "Tag 변경 추정은 하지 않음 – Tag 번호 기준으로만 비교. Tag 변경 = 사용자가 New 에 이전 Tag(Delete)를 병기한 것 – 그 Tag 와 비교 (D 열 = 이전 Tag). "
                       '(변경 의심 "X") = New · Delete 중 Location 이 비슷하고 Line Size 가 같은 짝 – 참고 표시일 뿐 상태는 그대로.'),
        ],
        "ref": "참고", "ref_cols": '{docs} 에만 있는 "{cols}" 열은 다른 Rev.에 없어 비교 대상에서 제외(값은 표시). ',
        "ref_scope": "이전 Rev.의 Control Valve·PSV 섹션은 On-Off/MOV 비교 범위 밖으로 제외.",
        "warn": "주의", "warn_mov": "최신 Rev.에 MOV 섹션이 없음 → 이전 Rev. MOV Tag({list})는 Delete로 표기. 삭제인지 별도 문서 이관인지 확인 필요.",
        "mov_note": "{n}에 {sec} 섹션 미수록 – 삭제 또는 별도 문서 이관 여부 확인 필요",
        "high_cols": ["Doc", "Doc No.", "Tag", "-", "항목", "이전 Rev. 값", "{n} 값", "Status"],
        "size_title": "Rev. 변경 Summary – Line Size 변경 / Ball Valve Sizing 영향 / 추가·삭제 수량",
        "size_note": '모든 수량은 Tag 기준이며 각 비교 시트의 "중요도" 행을 COUNTIFS로 집계. Tag 번호가 같은 항목만 비교하며, Tag 변경 추정은 하지 않음.',
        "size_cols": ["구분", "항목", "판단 기준"], "sum": "합계",
        "size_rows": [
            ("Tag 수", "이전 Rev. Tag 수", "이전 Rev. 문서 기준"), ("Tag 수", "{n} Tag 수", "최신 {n} 문서 기준"),
            ("Size", "Line Size 변경", "Line Size 값 변경"), ("Size", "Valve Size 변경", "Valve Size 값 변경 (Valve 재선정)"),
            ("Size", "Valve Bore 변경", "Full/Reduced Bore 변경 (공란→값 추가 제외)"),
            ("Sizing 영향", "Design Pressure / Temperature 변경", "Rating·재질·Seat 재검토 (FV 표기 추가·2% 이내 소폭 변경 제외)"),
            ("Sizing 영향", "Max ΔP (Opening/Closing) 변경", "Actuator Torque 재계산 (2% 이내 제외 시 High만 해당)"),
            ("Sizing 영향", "Pipe Class Rating 변경", "Class 첫 문자(Rating) 변경 → Rating/재질 재검토"),
            ("Sizing 영향", "Pipe Class 코드 체계 변경", "예: XC0KL-A→XC0K8 (Rating 문자 동일) – PMS로 재질/Rating 확인"),
            ("Sizing 영향", "Ball Sizing 영향 큰 변경 (High)", "위 Size/설계조건/ΔP 중 High 1개 이상 → Size·Torque 재검토 필요"),
            ("Sizing 영향", "공정조건 변경 (Med)", "운전 P/T, 유량, 밀도, 상, 운전시간 등 – 재확인 권장 (High 없는 Tag)"),
            ("Sizing 영향", "문서 정합성 변경만 (Min)", "Location, P&ID, Line No 표기 등 – Sizing 영향 없음"),
            ("Sizing 영향", "변경 없음", "No Change"), ("추가/삭제", "New (추가)", "이전 Rev.에 없음"),
            ("추가/삭제", "Delete (삭제) – 전체", "{n}에서 미확인"), ("추가/삭제", "  └ 그중 MOV", "{n}에 MOV 섹션 없음 – 이관 여부 확인"),
            ("추가/삭제", "Tag 변경 (사용자 지정)", "New 에 이전 Tag 를 병기 – 그 Tag 와 비교 (New · Delete 에서 빠짐)"),
        ],
        "list_title": "Line Size / Valve Size 변경 Tag 목록", "list_cols": ["Doc", "Tag", "-", "항목", "이전 Rev.", "{n}"],
        "file": "PDS_Rev_Comparison",
    },
    "en": {
        "prev": "Previous", "new": "Latest", "imp": "Importance", "spare": "Previous Tag", "overall": "Overall Importance", "note": "Remarks / Reason",
        "suspect": '(suspected rename "{t}")', "susrow": 'Suspected', "no_prev": "(not in previous Rev.)", "no_new": "(not found in {r})", "high_sheet": "High Changes", "size_sheet": "Summary (Sizing Impact)",
        "sheet_title": "{L}. {dn}{area} – {o} vs {n} Process Data Change Comparison",
        "sheet_note": "Each tag: row 1 previous Rev. / row 2 latest {n} (changed values in red) / row 3 importance (High·Med·Min per changed item). "
                      "Status, Tag and overall importance on row 1 only. Importance criteria: see the Summary sheet.",
        "sum_title": "Process Data Sheet (On-Off Valve / MOV) Revision Comparison Summary",
        "sum_note": "Source: latest Rev. vs previous Rev. of each DTS ({files}). Figures are COUNTIFS over each sheet.",
        "sum_cols": ["Doc", "Doc No.", "Area", "Previous Rev.", "Previous Tags", "{n} Tags", "Changed (High)", "Changed (Med)", "Changed (Min)",
                     "No Change", "New", "Delete", "Tag Renamed"],
        "total": "Total", "crit_title": "Importance Criteria (Size Change / Sizing Calculation Impact)",
        "crit": [
            ("High", "Line Size, Valve Size, Valve Bore, Design Pressure, Design Temperature, Max ΔP (Opening/Closing), Pipe Class rating letter change "
                     "→ review Valve Size, Rating and Actuator Torque"),
            ("Med", "Operating P/T, Flow rate, Max Pressure Drop, Density, Viscosity, Phase, Service Fluid, Operating Time, Tightness, "
                    "Fail-safe/Actuator, Quantity, Pipe Class code scheme change (same rating letter) → sizing inputs affected, re-check recommended"),
            ("Min", 'Location, P&ID No, Line No notation, MW, Normal Position, Notes, Remarks, "FV/" added to Design P → no sizing impact (document consistency)'),
            ("Adjust", "A numeric change of 2% or less is one level lower (High→Med, Med→Min). Quote differences in Line/Valve Size (18' vs 18\") and "
                       "separator differences in Line No/P&ID are not changes."),
            ("Status", "Changed / No Change / New (not in the previous Rev., in {n}) / Delete (in the previous Rev., not in {n}). "
                       "Tag renumbering is not inferred – compared by tag number only. Tag Renamed = a previous (Delete) tag given on a New tag by the user – compared with it (column D = previous tag). "
                       '(suspected rename "X") = a New and a Delete with a similar Location and the same Line Size – a note only, the status stays.'),
        ],
        "ref": "Note", "ref_cols": 'The "{cols}" column(s) only in {docs} are not in the other Rev. and are excluded from comparison (values shown). ',
        "ref_scope": "Control Valve and PSV sections of the previous Rev. are outside the On-Off/MOV comparison and excluded.",
        "warn": "Caution", "warn_mov": "The latest Rev. has no MOV section → MOV tags of the previous Rev. ({list}) are marked Delete. "
                                      "Confirm whether deleted or moved to a separate document.",
        "mov_note": "No {sec} section in {n} – confirm whether deleted or moved to a separate document",
        "high_cols": ["Doc", "Doc No.", "Tag", "-", "Item", "Previous Rev. Value", "{n} Value", "Status"],
        "size_title": "Revision Change Summary – Line Size Change / Ball Valve Sizing Impact / Added & Deleted Quantities",
        "size_note": 'All quantities are per tag, counted with COUNTIFS over the "Importance" rows of each comparison sheet. '
                     "Only the same tag numbers are compared; tag renumbering is not inferred.",
        "size_cols": ["Group", "Item", "Criterion"], "sum": "Total",
        "size_rows": [
            ("Tags", "Previous Rev. tags", "Previous Rev. document"), ("Tags", "{n} tags", "Latest {n} document"),
            ("Size", "Line Size change", "Line Size value changed"), ("Size", "Valve Size change", "Valve Size value changed (valve reselection)"),
            ("Size", "Valve Bore change", "Full/Reduced Bore changed (blank → value excluded)"),
            ("Sizing impact", "Design Pressure / Temperature change", "Review rating, material, seat (FV notation and changes within 2% excluded)"),
            ("Sizing impact", "Max ΔP (Opening/Closing) change", "Recalculate actuator torque (within 2% excluded: High only)"),
            ("Sizing impact", "Pipe Class rating change", "First letter (rating) of the class changed → review rating/material"),
            ("Sizing impact", "Pipe Class code scheme change", "e.g. XC0KL-A→XC0K8 (same rating letter) – confirm material/rating with PMS"),
            ("Sizing impact", "Major Ball sizing change (High)", "One or more High in size / design conditions / ΔP above → review size and torque"),
            ("Sizing impact", "Process condition change (Med)", "Operating P/T, flow, density, phase, operating time – re-check recommended (tags without High)"),
            ("Sizing impact", "Document consistency only (Min)", "Location, P&ID, Line No notation – no sizing impact"),
            ("Sizing impact", "No change", "No Change"), ("Added/Deleted", "New (added)", "Not in the previous Rev."),
            ("Added/Deleted", "Delete (deleted) – all", "Not found in {n}"), ("Added/Deleted", "  └ of which MOV", "No MOV section in {n} – confirm transfer"),
            ("Added/Deleted", "Tag renamed (set by user)", "Previous tag given on a New tag – compared with it (out of New · Delete)"),
        ],
        "list_title": "Tags with Line Size / Valve Size Change", "list_cols": ["Doc", "Tag", "-", "Item", "Previous Rev.", "{n}"],
        "file": "PDS_Rev_Comparison",
    },
}


def _col(i: int) -> str:
    from openpyxl.utils import get_column_letter
    return get_column_letter(i)


def _rev(r: str) -> str:
    return f"Rev.{r}" if r else "Rev.?"


def delete_note(item: dict, new_rev: str, lang: str = "ko") -> str:
    """The fact-only reason a Delete carries: the latest Rev. has no section of that valve kind at all."""
    return T[lang]["mov_note"].format(n=_rev(new_rev), sec=item["section"]) if item.get("note") else ""


def workbook(docs: list[dict], lang: str = "ko") -> bytes:
    """docs: [{doc_no, area, old_rev, new_rev, old_name, new_name, result: compare(...)}] → .xlsx bytes in the engineers'
    v2 layout (No · Status · Tag · spare · Rev. · Row, three rows per tag, Status/Tag/overall on the first row only)."""
    import io

    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    L_ = T[lang if lang in T else "ko"]
    REN = "Tag Renamed" if lang == "en" else RENAMED                                   # the status word as written in this book
    SL = lambda st: REN if st == RENAMED else st                                      # noqa: E731

    def note_of(it, new_rev):
        if it["status"] == "Delete":
            return delete_note(it, new_rev, lang)
        if it["status"] == RENAMED and lang == "en":
            L = it.get("link") or {}
            who = "".join(f" · {x}" for x in (L.get("by"), (L.get("at") or "")[:10]) if x)
            return f"Tag renamed (set by user{who}): previous Rev. {it.get('old_tag', '')} → latest Rev. {it['tag']}"
        return it["note"]
    thin, med = Side(style="thin", color="999999"), Side(style="medium", color="000000")
    box = Border(left=thin, right=thin, top=thin, bottom=thin)
    first = Border(left=thin, right=thin, top=med, bottom=thin)
    head_fill, head_font = PatternFill("solid", fgColor="1F3864"), Font(color="FFFFFF", bold=True, size=9)
    f9, f9b, red = Font(size=9), Font(size=9, bold=True), Font(size=9, color="FF0000")
    wrap = Alignment(wrap_text=True, vertical="center")
    mid = Alignment(horizontal="center", vertical="center", wrap_text=True)

    def fill(c):
        return PatternFill("solid", fgColor=c) if c else PatternFill()

    def header(ws, row, names):
        for i, h in enumerate(names, 1):
            c = ws.cell(row, i, h)
            c.fill, c.font, c.alignment, c.border = head_fill, head_font, mid, box
        ws.row_dimensions[row].height = 42

    news = {d["new_rev"] for d in docs}
    NR = _rev(next(iter(news))) if len(news) == 1 else ("최신 Rev." if lang == "ko" else "Latest Rev.")
    fmt = lambda t: t.format(n=NR)                                                    # noqa: E731
    wb = Workbook()
    sm = wb.active
    sm.title = "Summary"
    letters = [chr(65 + i) for i in range(len(docs))]
    names = [f"{L}. {d['doc_no']}"[:31] for L, d in zip(letters, docs)]
    keys = [k for k, _ in FIELDS]
    ci = {k: 7 + i for i, k in enumerate(keys)}                                       # G … AK
    nAL, nAM = 7 + len(keys), 8 + len(keys)
    AL = _col(nAL)
    high_rows, size_rows = [], []

    for L, d, sn in zip(letters, docs, names):                                        # ── one sheet per document
        ws = wb.create_sheet(sn)
        R, o_r, n_r = d["result"], _rev(d["old_rev"]), _rev(d["new_rev"])
        ws.cell(1, 1, L_["sheet_title"].format(L=L, dn=d["doc_no"], area=f" ({d['area']})" if d.get("area") else "", o=o_r, n=n_r)).font = Font(bold=True, size=12)
        ws.cell(2, 1, L_["sheet_note"].format(n=n_r)).font = Font(size=9)
        header(ws, 4, ["No", "Status", "Tag", L_["spare"], "Rev.", "Row"] + [h for _, h in FIELDS] + [L_["overall"], L_["note"]])
        r = 5
        for no, it in enumerate(R["items"], 1):
            st, o, n = it["status"], it["old"], it["new"]
            sv = it.get("suspect_vals") or []
            seq = [(L_["prev"], o, "o"), (L_["new"], n, "n")] + [(L_["susrow"], x["values"], x) for x in sv] + [(L_["imp"], None, "i")]
            nb = len(seq)
            for j, (row_name, src, kind) in enumerate(seq):
                rr = r + j
                for col in range(1, nAM + 1):
                    c = ws.cell(rr, col)
                    c.border, c.font, c.alignment = (first if j == 0 else box), f9, wrap
                ws.cell(rr, 5, o_r if kind == "o" else n_r if kind == "n" else (o_r if kind["side"] == "old" else n_r) if isinstance(kind, dict) else None)
                ws.cell(rr, 6, row_name)
                for k in keys:
                    c = ws.cell(rr, ci[k])
                    if isinstance(kind, dict) and k == keys[0]:          # the suspected tag's name in the Tag column
                        tc = ws.cell(rr, 3, f"↳ {kind['tag']}")
                        tc.font = Font(size=9, italic=True, bold=True, color="C55A11")
                    if isinstance(kind, dict):                           # valve56: the suspected tag's own values
                        v = src.get(k)
                        c.value = v if v not in (None, "") else None
                        c.font = Font(size=9, italic=True, color="833C0B")
                        if k in kind["diff"]:
                            c.fill = fill("FCE4D6")
                        continue
                    if kind == "i":
                        lv = it["imp"].get(k)
                        if lv:
                            c.value, c.fill, c.font = lv, fill(FILL_LEVEL[lv]), f9b
                    elif src is not None:
                        v = src.get(k)
                        c.value = v if v not in (None, "") else None
                        if kind == "n" and (k in it["imp"] or st == "New") and c.value is not None:
                            c.font = red
                if kind == "o" and o is None:
                    ws.cell(rr, ci["location"], L_["no_prev"].format(r=o_r))
                if kind == "n" and n is None:
                    ws.cell(rr, ci["location"], L_["no_new"].format(r=n_r))
            ws.row_dimensions[r + nb - 1].height = 15
            ws.cell(r, 1, no).alignment = mid
            c = ws.cell(r, 2, SL(st))
            c.fill = fill(FILL_STATUS.get(st, ""))
            ws.cell(r, 3, it["tag"])
            ws.cell(r, 4, it.get("old_tag") or None)
            if it.get("suspect"):                                                # valve55: the hint under the tag
                c = ws.cell(r + 1, 3, L_["suspect"].format(t=", ".join(it["suspect"])))
                c.font, c.fill = Font(size=8, italic=True, bold=True, color="C55A11"), fill("FCE4D6")
            c = ws.cell(r, nAL, it["overall"] or None)
            c.alignment = mid
            if it["overall"] in FILL_LEVEL:
                c.fill = fill(FILL_LEVEL[it["overall"]])
            ws.cell(r, nAM, note_of(it, d["new_rev"]) or None).alignment = wrap
            for col in (1, nAL, nAM):
                ws.merge_cells(start_row=r, start_column=col, end_row=r + nb - 1, end_column=col)
            for k, lv in it["imp"].items():
                label = dict(FIELDS)[k]
                if lv == "High":
                    high_rows.append([L, d["doc_no"], it["tag"], it.get("old_tag") or None, label, (o or {}).get(k), (n or {}).get(k), SL(st)])
                if k in SIZE_KEYS and lv in ("High", "Med"):
                    size_rows.append([L, it["tag"], it.get("old_tag") or None, label, (o or {}).get(k), (n or {}).get(k)])
            r += nb
        for k, w in WIDTHS.items():
            ws.column_dimensions[k].width = w
        for i in range(17, nAL):
            ws.column_dimensions[_col(i)].width = 9
        ws.column_dimensions[AL].width, ws.column_dimensions[_col(nAM)].width = 10, 50
        ws.freeze_panes = "G5"
        ws.auto_filter.ref = f"A4:{_col(nAM)}{max(r - 1, 4)}"

    P = L_["prev"]                                                                    # the row Status · overall stand on

    def cnt(sn, st=None, lv=None, tag=None):
        q = f"'{sn}'!"
        parts = ([f'{q}$B:$B,"{st}"'] if st else []) + [f'{q}$F:$F,"{P}"'] + ([f'{q}${AL}:${AL},"{lv}"'] if lv else []) + ([f'{q}$C:$C,"{tag}"'] if tag else [])
        return "COUNTIFS(" + ",".join(parts) + ")"

    # ── Summary
    sm.cell(1, 1, L_["sum_title"]).font = Font(bold=True, size=14)
    files = " · ".join(f"{d['old_name']} → {d['new_name']}" for d in docs)
    sm.cell(2, 1, L_["sum_note"].format(files=files)).font = Font(size=9)
    cols = [fmt(c) for c in L_["sum_cols"]]
    header(sm, 4, cols)
    for i, (L, d, sn) in enumerate(zip(letters, docs, names)):
        rr = 5 + i
        row = [L, d["doc_no"], d.get("area") or "", _rev(d["old_rev"]), d["result"]["counts"]["old_tags"], d["result"]["counts"]["new_tags"]]
        row += [f"={cnt(sn, 'Changed*', lv)}+{cnt(sn, REN, lv)}" for lv in ("High", "Med", "Min")]
        row += [f"={cnt(sn, s)}" for s in ("No Change", "New", "Delete", REN)]
        for j, v in enumerate(row, 1):
            c = sm.cell(rr, j, v)
            c.border, c.font = box, Font(size=10)
    tr = 5 + len(docs)
    sm.cell(tr, 1, L_["total"]).font = Font(bold=True)
    for j in range(5, len(cols) + 1):
        c = sm.cell(tr, j, f"=SUM({_col(j)}5:{_col(j)}{tr - 1})")
        c.font, c.border = Font(bold=True), box
    cr = tr + 2
    sm.cell(cr, 1, L_["crit_title"]).font = Font(bold=True)
    notes = [(k, fmt(t)) for k, t in L_["crit"]]
    extra = {}
    for d in docs:
        R = d["result"]
        for c in R.get("excluded_columns", []):
            extra.setdefault(c, []).append(d["doc_no"])
    notes.append((L_["ref"], "".join(L_["ref_cols"].format(cols=c, docs=", ".join(v)) for c, v in extra.items()) + L_["ref_scope"]))
    gone = [(d["doc_no"].split("-")[0], sum(1 for it in d["result"]["items"] if it["status"] == "Delete" and it["section"] == "MOV"))
            for d in docs if "MOV" in d["result"]["old_sections"] and "MOV" not in d["result"]["new_sections"]]
    if gone:
        notes.append((L_["warn"], L_["warn_mov"].format(list=", ".join(f"{a}: {b}" for a, b in gone))))
    for i, (k, t) in enumerate(notes):
        rr = cr + 1 + i
        a = sm.cell(rr, 1, k)
        a.font, a.fill, a.border = Font(bold=True, size=10), fill(FILL_LEVEL.get(k, "")), box
        b = sm.cell(rr, 2, t)
        b.alignment, b.font = Alignment(wrap_text=True, vertical="center"), Font(size=10)
        sm.merge_cells(start_row=rr, start_column=2, end_row=rr, end_column=len(cols))
        sm.row_dimensions[rr].height = 30
    for k, w in zip("ABCDEFGHIJKLM", (6, 22, 18, 9, 10, 10, 10, 10, 10, 10, 8, 8, 10)):
        sm.column_dimensions[k].width = w

    # ── High list
    hl = wb.create_sheet(L_["high_sheet"])
    header(hl, 1, [fmt(c) for c in L_["high_cols"]])
    for i, row in enumerate(high_rows, 2):
        for j, v in enumerate(row, 1):
            c = hl.cell(i, j, v)
            c.border, c.font = box, Font(size=9)
        hl.cell(i, 7).font = Font(size=9, color="FF0000")
    for k, w in zip("ABCDEFGH", (5, 20, 16, 14, 22, 22, 22, 22)):
        hl.column_dimensions[k].width = w
    hl.freeze_panes = "A2"
    hl.auto_filter.ref = f"A1:H{max(1, len(high_rows) + 1)}"

    # ── Sizing summary
    sz = wb.create_sheet(L_["size_sheet"])
    sz.cell(1, 1, L_["size_title"]).font = Font(bold=True, size=14)
    sz.cell(2, 1, L_["size_note"]).font = Font(size=9)
    header(sz, 4, L_["size_cols"] + names + [L_["sum"]])
    I_ = L_["imp"]

    def sp(sn, cols_, levels):
        q = f"'{sn}'!"
        terms = "+".join(f'({q}${c}$5:${c}$5000="{lv}")' for c in cols_ for lv in levels)
        return f'=SUMPRODUCT(({q}$F$5:$F$5000="{I_}")*(({terms})>0))'
    C = lambda k: _col(ci[k])                                                         # noqa: E731
    calc = [lambda sn, d: d["result"]["counts"]["old_tags"], lambda sn, d: d["result"]["counts"]["new_tags"],
            lambda sn, d: sp(sn, [C("line_size")], ("High", "Med")), lambda sn, d: sp(sn, [C("valve_size")], ("High", "Med")),
            lambda sn, d: sp(sn, [C("bore")], ("High", "Med")), lambda sn, d: sp(sn, [C("design_temp"), C("design_pressure")], ("High", "Med")),
            lambda sn, d: sp(sn, [C("dp_open"), C("dp_close")], ("High", "Med")), lambda sn, d: sp(sn, [C("piping_class")], ("High",)),
            lambda sn, d: sp(sn, [C("piping_class")], ("Med",)),
            lambda sn, d: sp(sn, [C(k) for k in ("line_size", "valve_size", "bore", "piping_class", "design_temp", "design_pressure", "dp_open", "dp_close")], ("High",)),
            lambda sn, d: "=" + cnt(sn, lv="Med"), lambda sn, d: "=" + cnt(sn, lv="Min"), lambda sn, d: "=" + cnt(sn, st="No Change"),
            lambda sn, d: "=" + cnt(sn, st="New"), lambda sn, d: "=" + cnt(sn, st="Delete"), lambda sn, d: "=" + cnt(sn, st="Delete", tag="*MOV*"), lambda sn, d: "=" + cnt(sn, st=REN)]
    for i, ((g, name, basis), fn) in enumerate(zip(L_["size_rows"], calc)):
        rr = 5 + i
        for j, v in enumerate([g, fmt(name), fmt(basis)] + [fn(sn, d) for sn, d in zip(names, docs)], 1):
            c = sz.cell(rr, j, v)
            c.border, c.font = box, Font(size=10)
        c = sz.cell(rr, 4 + len(docs), f"=SUM(D{rr}:{_col(3 + len(docs))}{rr})")
        c.border, c.font = box, Font(bold=True, size=10)
        if i >= 2 and i <= 12:
            sz.cell(rr, 1).fill = fill("FCE4D6")
    lr = 5 + len(calc) + 1
    sz.cell(lr, 1, L_["list_title"]).font = Font(bold=True)
    header(sz, lr + 1, [fmt(c) for c in L_["list_cols"]])
    for i, row in enumerate(size_rows):
        for j, v in enumerate(row, 1):
            c = sz.cell(lr + 2 + i, j, v)
            c.border, c.font = box, Font(size=10)
    for k, w in zip("ABCDEFG", (12, 34, 46, 20, 20, 20, 10)):
        sz.column_dimensions[k].width = w
    sz.freeze_panes = "A5"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
