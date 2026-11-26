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
HEADERS = ["No", "Status", "Tag", "Rev.", "Row"] + [h for _, h in FIELDS] + ["중요도(종합)", "비고 / 사유"]
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


def _rows(parsed: dict) -> tuple[dict, dict]:
    """{tag_key: flat row} of the On-Off / MOV tables of a parsed PDS (process.read_process_data), and per-section facts."""
    cols, sections = [], set()
    titles = {}
    for p in parsed.get("pages", []):
        titles[p["page"]] = p.get("title", "")
    out = {}
    for r in parsed.get("rows", []):
        title = titles.get(r.get("page"), "")
        if OUT_OF_SCOPE.search(title):                       # Control Valve · PSV sections are not compared
            continue
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


def compare(old: dict, new: dict) -> dict:
    """old · new = parsed PDS (process.read_process_data, the earlier and the newer Rev. of one document number).
    → {"items": [{status, tag, old, new, imp: {key: level}, overall, note, section}], "counts": {...}, ...}"""
    O, fo = _rows(old)
    N, fn = _rows(new)
    both = fo["columns"] & fn["columns"]
    items = []
    # user 2026-11-26: no guessing which tag became which — the same tag number is compared, every other tag of the
    # earlier Rev. is Delete and every other tag of the newer Rev. is New
    for k in N:                                              # 1. the same tag in both Revs.
        if k in O:
            imp = _diff(O[k], N[k], both)
            items.append({"status": "Changed" if imp else "No Change", "tag": N[k]["tag"], "tag_key": k, "old": O[k], "new": N[k],
                          "imp": imp, "overall": _top(imp), "note": "", "section": N[k]["section"]})
    for k in N:                                              # 2. only in the new Rev.
        if k not in O:
            items.append({"status": "New", "tag": N[k]["tag"], "tag_key": k, "old": None, "new": N[k], "imp": {},
                          "overall": "New", "note": "", "section": N[k]["section"]})
    for k in O:                                              # 3. not in the new Rev.
        if k not in N:
            sec = O[k]["section"]
            note = (f"최신 Rev. 에 {sec} 섹션 미수록 – 삭제 또는 별도 문서 이관 여부 확인 필요" if sec not in fn["sections"] else "")
            items.append({"status": "Delete", "tag": O[k]["tag"], "tag_key": k, "old": O[k], "new": None, "imp": {},
                          "overall": "Delete", "note": note, "section": sec})
    order = {k: i for i, k in enumerate(N)}
    oorder = {k: i for i, k in enumerate(O)}
    rank = {"Delete": 2, "New": 0}
    items.sort(key=lambda it: (rank.get(it["status"], 0) == 2, order.get(it["tag_key"], len(order) + oorder.get(it["tag_key"], 0))))
    counts = {"old_tags": len(O), "new_tags": len(N)}
    for it in items:
        s = it["status"]
        if s == "Changed":
            if it["overall"]:
                counts[f"changed_{it['overall'].lower()}"] = counts.get(f"changed_{it['overall'].lower()}", 0) + 1
        counts[s] = counts.get(s, 0) + 1
    excluded = sorted((fn["columns"] - fo["columns"]) | (fo["columns"] - fn["columns"]))
    return {"items": items, "counts": counts, "excluded_columns": [dict(FIELDS)[k] for k in excluded],
            "old_sections": sorted(fo["sections"]), "new_sections": sorted(fn["sections"])}


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

FILL_STATUS = {"Changed": "FFF2CC", "No Change": "", "New": "C6E0B4", "Delete": "D9D9D9"}
FILL_LEVEL = {"High": "FFC7CE", "Med": "FFEB9C", "Min": "E2EFDA"}
WIDTHS = {"A": 5, "B": 11, "C": 15, "D": 7, "E": 7, "F": 22, "G": 9, "H": 16, "I": 9, "J": 22, "K": 9, "L": 9, "M": 9,
          "N": 9, "O": 11}
CRITERIA = [
    ("High", "Line Size, Valve Size, Valve Bore, Design Pressure, Design Temperature, Max ΔP(Opening/Closing), Pipe Class Rating 문자 변경 "
             "→ Valve Size·Rating·Actuator Torque 재검토 필요"),
    ("Med", "Operating P/T, Flow rate, Max Pressure Drop, Density, Viscosity, Phase, Service Fluid, Operating Time, Tightness, "
            "Fail-safe/Actuator, Quantity, Pipe Class 코드 체계 변경(Rating 문자 동일) → Sizing 입력값 영향, 재확인 권장"),
    ("Min", 'Location, P&ID No, Line No 표기, MW, Normal Position, Notes, Remarks, Design P의 "FV/" 표기 추가, 이전에 없던 값의 기재 '
            "→ Sizing 영향 없음(문서 정합성)"),
    ("보정", "수치 변경폭이 2% 이하이면 한 단계 낮춤(High→Med, Med→Min). Line/Valve Size의 따옴표 표기 차이(18' vs 18\")와 "
             "Line No/P&ID의 구분기호 · 띄어쓰기 차이는 변경으로 보지 않음."),
    ("Status", "Changed / No Change (같은 Tag 번호끼리 비교) / New(이전 Rev.에 없던 Tag 번호) / Delete(최신 Rev.에 없는 Tag 번호) — "
               "Tag 번호가 바뀐 것인지는 추정하지 않음"),
]


def _col(i: int) -> str:
    from openpyxl.utils import get_column_letter
    return get_column_letter(i)


def workbook(docs: list[dict]) -> bytes:
    """docs: [{doc_no, area, old_rev, new_rev, old_name, new_name, result: compare(...)}] → the .xlsx bytes."""
    import io

    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    thin = Side(style="thin", color="999999")
    box = Border(left=thin, right=thin, top=thin, bottom=thin)
    head_fill, head_font = PatternFill("solid", fgColor="1F3864"), Font(color="FFFFFF", bold=True, size=9)
    f9, red, bold = Font(size=9), Font(size=9, color="FF0000"), Font(bold=True, size=12)
    wrap = Alignment(wrap_text=True, vertical="center")

    def fill(c):
        return PatternFill("solid", fgColor=c) if c else PatternFill()

    def header(ws, row, names):
        for i, h in enumerate(names, 1):
            c = ws.cell(row, i, h)
            c.fill, c.font, c.alignment, c.border = head_fill, head_font, Alignment(wrap_text=True, horizontal="center", vertical="center"), box
        ws.row_dimensions[row].height = 42

    wb = Workbook()
    sm = wb.active
    sm.title = "Summary"
    letters = [chr(65 + i) for i in range(len(docs))]
    names = [f"{L}. {d['doc_no']}"[:31] for L, d in zip(letters, docs)]
    rev = lambda r: f"Rev.{r}" if r else "Rev.?"                                     # noqa: E731
    keys = [k for k, _ in FIELDS]
    ci = {k: 6 + i for i, k in enumerate(keys)}                                       # field → column number
    AL, AM = _col(6 + len(keys)), _col(7 + len(keys))
    high_rows, size_rows = [], []

    for L, d, sn in zip(letters, docs, names):                                        # ── one sheet per document
        ws = wb.create_sheet(sn)
        R = d["result"]
        ws.cell(1, 1, f"{L}. {d['doc_no']}" + (f" ({d['area']})" if d.get("area") else "")
                + f" – {rev(d['old_rev'])} vs {rev(d['new_rev'])} Process Data 변경 비교").font = bold
        ws.cell(2, 1, f"각 Tag: 1행 이전 {rev(d['old_rev'])} / 2행 최신 {rev(d['new_rev'])}(변경값 붉은 글씨) / 3행 중요도(변경 항목별 High·Med·Min). "
                      f"중요도 기준은 Summary 시트 참조. 이전: {d.get('old_name', '')} · 최신: {d.get('new_name', '')}").font = Font(size=9, italic=True)
        header(ws, 4, HEADERS)
        r = 5
        for no, it in enumerate(R["items"], 1):
            st, o, n = it["status"], it["old"], it["new"]
            for j, (row_name, src) in enumerate((("이전", o), ("최신", n), ("중요도", None))):
                rr = r + j
                vals = [no, st, it["tag"], rev(d["old_rev"]) if j == 0 else rev(d["new_rev"]) if j == 1 else None, row_name]
                for i, v in enumerate(vals, 1):
                    c = ws.cell(rr, i, v)
                    c.font, c.border, c.alignment = f9, box, wrap
                ws.cell(rr, 2).fill = fill(FILL_STATUS.get(st, ""))
                for k in keys:
                    c = ws.cell(rr, ci[k])
                    c.border, c.font, c.alignment = box, f9, wrap
                    if j == 2:
                        lv = it["imp"].get(k)
                        if lv:
                            c.value, c.fill = lv, fill(FILL_LEVEL[lv])
                    elif src is not None:
                        v = src.get(k)
                        c.value = v if v not in (None, "") else None
                        if j == 1 and (k in it["imp"] or st == "New") and c.value is not None:
                            c.font = red
                if j == 0 and o is None:
                    ws.cell(rr, ci["location"], f"(이전 {rev(d['old_rev'])} 없음)")
                if j == 1 and n is None:
                    ws.cell(rr, ci["location"], f"(최신 {rev(d['new_rev'])} 미확인)")
                c = ws.cell(rr, 6 + len(keys), it["overall"] or None if j == 1 else None)
                c.font, c.border = f9, box
                if j == 1 and it["overall"] in FILL_LEVEL:
                    c.fill = fill(FILL_LEVEL[it["overall"]])
            c = ws.cell(r, 7 + len(keys), it["note"] or None)
            c.font, c.alignment, c.border = f9, wrap, box
            ws.merge_cells(f"{AM}{r}:{AM}{r + 2}")
            for k, lv in it["imp"].items():
                if lv == "High":
                    high_rows.append([L, d["doc_no"], it["tag"], dict(FIELDS)[k], (o or {}).get(k), (n or {}).get(k), st])
                if k in SIZE_KEYS and lv in ("High", "Med"):
                    size_rows.append([L, it["tag"], dict(FIELDS)[k], (o or {}).get(k), (n or {}).get(k)])
            r += 3
        for k, w in WIDTHS.items():
            ws.column_dimensions[k].width = w
        for i in range(16, 6 + len(keys)):
            ws.column_dimensions[_col(i)].width = 9
        ws.column_dimensions[AL].width, ws.column_dimensions[AM].width = 10, 50
        ws.freeze_panes = "F5"
        ws.auto_filter.ref = f"A4:{AM}{max(r - 1, 4)}"

    # ── Summary
    sm.cell(1, 1, "Process Data Sheet (On-Off Valve / MOV) Rev. 비교 Summary").font = Font(bold=True, size=14)
    sm.cell(2, 1, "출처: 각 PDS 의 최신 Rev. vs 바로 앞 Rev. (같은 문서 번호로 올린 순서). 수치는 각 시트를 COUNTIFS 로 집계.").font = Font(size=9, italic=True)
    cols = ["Doc", "Doc No.", "Area", "이전 Rev.", "최신 Rev.", "이전 Tag 수", "최신 Tag 수", "Changed (High)", "Changed (Med)", "Changed (Min)",
            "No Change", "New", "Delete"]
    header(sm, 4, cols)
    for i, (L, d, sn) in enumerate(zip(letters, docs, names)):
        rr, q = 5 + i, f"'{sn}'!"

        def cnt(st, lv=None, q=q):
            f = f'COUNTIFS({q}$B:$B,"{st}",{q}$E:$E,"최신"' + (f',{q}${AL}:${AL},"{lv}"' if lv else "") + ")"
            return f
        row = [L, d["doc_no"], d.get("area") or "", rev(d["old_rev"]), rev(d["new_rev"]), d["result"]["counts"]["old_tags"], d["result"]["counts"]["new_tags"]]
        row += [f"={cnt('Changed', lv)}" for lv in ("High", "Med", "Min")]
        row += [f"={cnt(s)}" for s in ("No Change", "New", "Delete")]
        for j, v in enumerate(row, 1):
            c = sm.cell(rr, j, v)
            c.border, c.font = box, Font(size=10)
    tr = 5 + len(docs)
    sm.cell(tr, 1, "합계").font = Font(bold=True)
    for j in range(6, len(cols) + 1):
        c = sm.cell(tr, j, f"=SUM({_col(j)}5:{_col(j)}{tr - 1})")
        c.font, c.border = Font(bold=True), box
    cr = tr + 2
    sm.cell(cr, 1, "중요도 기준 (Size 변경 / Sizing Cal. 영향)").font = Font(bold=True)
    notes = list(CRITERIA)
    excl = sorted({x for d in docs for x in d["result"].get("excluded_columns", [])})
    notes.append(("참고", ("한쪽 Rev. 에만 있는 열(" + ", ".join(excl) + ")은 비교 대상에서 제외(값은 표시). " if excl else "")
                  + "Control Valve · PSV 섹션은 On-Off/MOV 비교 범위 밖으로 제외."))
    gone = [(d["doc_no"], sum(1 for it in d["result"]["items"] if it["status"] == "Delete" and it["section"] == "MOV"))
            for d in docs if "MOV" in d["result"]["old_sections"] and "MOV" not in d["result"]["new_sections"]]
    if gone:
        notes.append(("주의", "최신 Rev. 에 MOV 섹션이 없음 → 이전 Rev. MOV Tag(" + ", ".join(f"{a}: {b}" for a, b in gone)
                      + ")는 Delete 로 표기. 삭제인지 별도 문서 이관인지 확인 필요."))
    for i, (k, t) in enumerate(notes):
        rr = cr + 1 + i
        a = sm.cell(rr, 1, k)
        a.font, a.fill, a.border = Font(bold=True, size=10), fill(FILL_LEVEL.get(k, "")), box
        b = sm.cell(rr, 2, t)
        b.alignment, b.font = Alignment(wrap_text=True, vertical="center"), Font(size=10)
        sm.merge_cells(start_row=rr, start_column=2, end_row=rr, end_column=len(cols))
        sm.row_dimensions[rr].height = 30
    for k, w in zip("ABCDEFGHIJKLMNO", (6, 22, 18, 9, 9, 10, 10, 10, 10, 10, 10, 8, 8, 10, 10)):
        sm.column_dimensions[k].width = w

    # ── High list
    hl = wb.create_sheet("High 변경 목록")
    header(hl, 1, ["Doc", "Doc No.", "Tag", "항목", "이전 Rev. 값", "최신 Rev. 값", "Status"])
    for i, row in enumerate(high_rows, 2):
        for j, v in enumerate(row, 1):
            c = hl.cell(i, j, v)
            c.border, c.font = box, Font(size=9)
        hl.cell(i, 6).font = Font(size=9, color="FF0000")
    for k, w in zip("ABCDEFG", (5, 20, 16, 22, 22, 22, 22)):
        hl.column_dimensions[k].width = w
    hl.freeze_panes = "A2"
    hl.auto_filter.ref = f"A1:G{max(1, len(high_rows) + 1)}"

    # ── Sizing summary
    sz = wb.create_sheet("Summary (Sizing 영향)")
    sz.cell(1, 1, "Rev. 변경 Summary – Line Size 변경 / Ball Valve Sizing 영향 / 추가·삭제 수량").font = Font(bold=True, size=14)
    sz.cell(2, 1, '모든 수량은 Tag 기준이며 각 비교 시트의 "중요도" 행을 집계. 같은 Tag 번호끼리만 비교').font = Font(size=9, italic=True)
    header(sz, 4, ["구분", "항목", "판단 기준"] + names + ["합계"])

    def sp(sn, cols_, levels):
        q = f"'{sn}'!"
        terms = "+".join(f'({q}${c}$5:${c}$5000="{lv}")' for c in cols_ for lv in levels)
        return f'=SUMPRODUCT(({q}$E$5:$E$5000="중요도")*(({terms})>0))'

    def cf(sn, st=None, lv=None, tag=None):
        q = f"'{sn}'!"
        parts = ([f'{q}$B:$B,"{st}"'] if st else []) + [f'{q}$E:$E,"최신"'] + ([f'{q}${AL}:${AL},"{lv}"'] if lv else []) + ([f'{q}$C:$C,"{tag}"'] if tag else [])
        return "=COUNTIFS(" + ",".join(parts) + ")"
    C = lambda k: _col(ci[k])                                                         # noqa: E731
    items = [("Tag 수", "이전 Rev. Tag 수", "이전 Rev. 문서 기준", lambda sn, d: d["result"]["counts"]["old_tags"]),
             ("Tag 수", "최신 Rev. Tag 수", "최신 Rev. 문서 기준", lambda sn, d: d["result"]["counts"]["new_tags"]),
             ("Size", "Line Size 변경", "Line Size 값 변경", lambda sn, d: sp(sn, [C("line_size")], ("High", "Med"))),
             ("Size", "Valve Size 변경", "Valve Size 값 변경 (Valve 재선정)", lambda sn, d: sp(sn, [C("valve_size")], ("High", "Med"))),
             ("Size", "Valve Bore 변경", "Full/Reduced Bore 변경 (공란→값 추가 제외)", lambda sn, d: sp(sn, [C("bore")], ("High", "Med"))),
             ("Sizing 영향", "Design Pressure / Temperature 변경", "Rating·재질·Seat 재검토 (FV 표기 추가·2% 이내 소폭 변경 제외)",
              lambda sn, d: sp(sn, [C("design_temp"), C("design_pressure")], ("High", "Med"))),
             ("Sizing 영향", "Max ΔP (Opening/Closing) 변경", "Actuator Torque 재계산", lambda sn, d: sp(sn, [C("dp_open"), C("dp_close")], ("High", "Med"))),
             ("Sizing 영향", "Pipe Class Rating 변경", "Class 첫 문자(Rating) 변경 → Rating/재질 재검토", lambda sn, d: sp(sn, [C("piping_class")], ("High",))),
             ("Sizing 영향", "Pipe Class 코드 체계 변경", "Rating 문자 동일 – PMS로 재질/Rating 확인", lambda sn, d: sp(sn, [C("piping_class")], ("Med",))),
             ("Sizing 영향", "Ball Sizing 영향 큰 변경 (High)", "위 Size/설계조건/ΔP 중 High 1개 이상 → Size·Torque 재검토 필요",
              lambda sn, d: sp(sn, [C(k) for k in ("line_size", "valve_size", "bore", "piping_class", "design_temp", "design_pressure", "dp_open", "dp_close")], ("High",))),
             ("Sizing 영향", "공정조건 변경 (Med)", "운전 P/T, 유량, 밀도, 상, 운전시간 등 – 재확인 권장 (High 없는 Tag)", lambda sn, d: cf(sn, lv="Med")),
             ("Sizing 영향", "문서 정합성 변경만 (Min)", "Location, P&ID, Line No 표기 등 – Sizing 영향 없음", lambda sn, d: cf(sn, lv="Min")),
             ("Sizing 영향", "변경 없음", "No Change", lambda sn, d: cf(sn, st="No Change")),
             ("추가/삭제", "New (추가)", "이전 Rev.에 없음", lambda sn, d: cf(sn, st="New")),
             ("추가/삭제", "Delete (삭제) – 전체", "최신 Rev.에서 미확인", lambda sn, d: cf(sn, st="Delete")),
             ("추가/삭제", "  └ 그중 MOV", "최신 Rev.에 MOV 섹션 없음 – 이관 여부 확인", lambda sn, d: cf(sn, st="Delete", tag="*MOV*"))]
    for i, (g, name, basis, fn) in enumerate(items):
        rr = 5 + i
        for j, v in enumerate([g, name, basis] + [fn(sn, d) for sn, d in zip(names, docs)], 1):
            c = sz.cell(rr, j, v)
            c.border, c.font = box, Font(size=10)
        c = sz.cell(rr, 4 + len(docs), f"=SUM(D{rr}:{_col(3 + len(docs))}{rr})")
        c.border, c.font = box, Font(bold=True, size=10)
        if g in ("Size", "Sizing 영향"):
            sz.cell(rr, 1).fill = fill("FCE4D6")
    lr = 5 + len(items) + 1
    sz.cell(lr, 1, "Line Size / Valve Size 변경 Tag 목록").font = Font(bold=True)
    header(sz, lr + 1, ["Doc", "Tag", "항목", "이전 Rev.", "최신 Rev."])
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
