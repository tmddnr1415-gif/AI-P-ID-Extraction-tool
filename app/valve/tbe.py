"""Valve List (TBE Appendix format) — fill the reference workbook from extracted datasheets.

The reference Valve List (e.g. CO2S-SSG-IN-TBE-00009) is **edited in place** with openpyxl, so its sheets,
column order, merged cells, widths, styles and filters stay as they were (spec §2.1 / §4.3):

  · Each appendix sheet's header (the rows above the first tag) is read into column paths
    ('Accessories › Solenoid Valve › Body Material').  A column is filled only if its path is in COLUMNS.
  · A tag already in the sheet: its 'Requirement' row is compared cell by cell; a changed cell is overwritten,
    filled yellow and given a comment 'Previous: …'.
  · A new tag: a block (Requirement row + the vendor rows the sheet uses) is appended in the style of the
    sheet's first block, in the sheet whose title names the valve type.
  · The vendor rows under each Requirement row (AMPO · OMS · NEWAY …) are removed from the output by default
    (vendor_rows=False) — the list carries the datasheet requirement only.
  · Every written cell carries a comment with its source (file · page · datasheet row).
  · Columns appended at the right: DS Document No. · DS Rev. · DS Source · Datasheet Notes · Tool Status ·
    Changed Columns.  A 'Datasheet Notes' sheet lists every note on its own row.

Which datasheet field feeds which TBE column was checked against the TBE's own Requirement rows for all
164 tags (docs/valve/DESIGN.md §4): e.g. TBE 'Leakage Class' = datasheet 'Tightness requirement' (164/164).
Columns with no datasheet source (Corrosion Allowance on On/Off sheets, Face to Face, Valve PT Rating,
Dense Phase CO2, RAL colours, Technical Acceptance, Remarks) are left as they are.
"""
from __future__ import annotations

import copy
import io
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import openpyxl
from openpyxl.comments import Comment
from openpyxl.styles import PatternFill
from openpyxl.utils import get_column_letter

from app.valve import material, requirements, schema

YELLOW = PatternFill("solid", fgColor="FFF2A8")
GREEN = PatternFill("solid", fgColor="DDF3E2")
EXTRA_HEADERS = ["Area", "Site", "Unit", "DS Document No.", "DS Rev.", "DS Source (file · page)", "Special Requirements (Notes)", "Expert Review (Tool)", "Datasheet Notes", "Tool Status",
                 "Changed Columns"]


def _n(s) -> str:
    return re.sub(r"\s+", " ", str(s or "").replace("\n", " ")).strip().lower()


def _cmp(s) -> str:
    """Compare form: case, spaces and the inch mark ('24 in' == '24\"') do not count as a change."""
    t = str(s or "").upper().replace("INCH", '"').replace(" IN", '"')
    t = re.sub(r"^FAIL\s+", "", t.strip())                 # 'Fail Close' == 'Close' (TBE writes the action only)
    if re.fullmatch(r"\d+(\.0+)?", t.strip()):
        t = str(int(float(t)))
    return re.sub(r"[^0-9A-Z\"#/.]", "", t)


# ── value builders: field dict -> (value, [field keys used]) ──────────────────────────────────

def _is_placeholder(v) -> bool:
    return schema.norm_label(v) in schema.PLACEHOLDERS or schema.norm_label(v) in ("vtc", "vta / vta", "na / na")


def _f(fields, *keys):
    for k in keys:
        f = fields.get(k)
        if f and _val(f):
            return _val(f), [k]
    return "", []


def _val(f):
    return schema.effective(f)


def _pair(fields, a, b):
    va, vb = _val(fields.get(a, {})), _val(fields.get(b, {}))
    if not va and not vb:
        return "", []
    return (f"{va} / {vb}" if va and vb and va != vb else va or vb), [a, b]


def _note_part(fields, key, label):
    """'Note-1' -> the 'Gasket material: …' / 'Stud Bolt material: …' part of datasheet note 1."""
    f = fields.get(key)
    if not f:
        return "", []
    ref = f.get("ref") or {}
    txt = ref.get("text", "") if isinstance(ref, dict) else ""
    # stop at the next '<X> material:' heading or where prose starts ('. Pressure boundary bolting shall …') —
    # the specification itself is written in capitals
    m = re.search(label + r"\s*:\s*(.+?)(?=(?:Stud Bolt|Gasket|Bolt and nuts?)\s+material\s*:|\.\s+[A-Z][a-z]+\s+[a-z]|$)",
                  txt, re.I)
    if m:
        return m.group(1).strip().rstrip("."), [key]
    return _val(f), [key]


def _word(fields, key, words):
    v = _val(fields.get(key, {}))
    for w in words:
        if w.lower() in v.lower():
            return w.title() if w.islower() else w, [key]
    return "", []


# (path test, builder).  First match wins.  Path = lower-case 'parent › child' text.
COLUMNS = [
    (lambda p: p.endswith("tag number") and "color" not in p and "ral" not in p, "TAG"),
    (lambda p: p.startswith("valve body") and "mfr" in p, lambda f: _pair(f, "manufacturer", "model")),
    (lambda p: p == "piping class", lambda f: _f(f, "piping_class")),
    (lambda p: p == "corrosion allowance", lambda f: _f(f, "corrosion_allowance", "corrosion_req")),
    (lambda p: p == "body type", lambda f: _word(f, "body_type", ["Trunnion", "Floating"])),
    (lambda p: p == "body cover", lambda f: _f(f, "bonnet_type")),
    (lambda p: p == "body size", lambda f: _f(f, "body_size")),
    (lambda p: p == "rating", lambda f: _f(f, "rating")),
    (lambda p: p == "connection type", lambda f: _f(f, "connections")),
    (lambda p: p == "body material", lambda f: _f(f, "body_material")),
    (lambda p: "full / reduced bore" in p, lambda f: _word(f, "body_type", ["Full Bore", "Reduced Bore"]) if
     _word(f, "body_type", ["Full Bore", "Reduced Bore"])[0] else _word(f, "trim_type", ["Full Bore", "Reduced Bore"])),
    (lambda p: p == "ball material", lambda f: _f(f, "ball_material")),
    (lambda p: p in ("packing material", "packing"), lambda f: _f(f, "packing_material")),
    (lambda p: p.startswith("packing type"), lambda f: _f(f, "packing_type")),
    (lambda p: p in ("stem material", "stem") , lambda f: _f(f, "stem_material")),
    (lambda p: p == "seal material", lambda f: _f(f, "seal_material")),
    (lambda p: p == "seat material", lambda f: _f(f, "seat_material")),
    (lambda p: p.startswith("gasket material"), lambda f: _note_part(f, "bolting_gasket", "Gasket material")
     if f.get("bolting_gasket") else _f(f, "gasket_material")),
    (lambda p: p.startswith("stud bolt material"), lambda f: _note_part(f, "bolting_gasket", "Stud Bolt material")),
    (lambda p: p in ("face to face dimension", "end to end dimension"), lambda f: _f(f, "face_to_face")),
    (lambda p: p == "type of actuator", lambda f: _f(f, "act_type")),
    (lambda p: p in ("actuator material", "actuator material › case"), lambda f: _f(f, "act_material")),
    (lambda p: p == "safety factor", lambda f: _f(f, "act_safety_factor")),
    (lambda p: p == "stroke time", lambda f: _f(f, "act_stroke_time", "stroke_time_s")),
    (lambda p: p == "applicable valve typical", lambda f: _f(f, "typical")),
    (lambda p: p == "actuator › mfr. / model", lambda f: _pair(f, "act_manufacturer", "act_model")),
    (lambda p: "solenoid valve › mfr" in p, lambda f: _pair(f, "sov_manufacturer", "sov_model")),
    (lambda p: "solenoid valve › body material" in p, lambda f: _f(f, "sov_body_material")),
    (lambda p: "solenoid valve › valve type" in p, lambda f: _f(f, "sov_type")),
    (lambda p: "solenoid valve › power consumption" in p, lambda f: _f(f, "power_supply")),
    (lambda p: "solenoid valve › ip rating" in p, lambda f: _f(f, "ingress")),
    (lambda p: "position transmitter" in p, lambda f: _f(f, "pos_tx")),
    (lambda p: "air filter regulator › mfr" in p, lambda f: _f(f, "afr")),
    (lambda p: p.startswith("nace"), lambda f: _f(f, "nace")),
    (lambda p: p.startswith("sil requirement"), lambda f: _f(f, "sil")),
    (lambda p: p.startswith("fire safe"), lambda f: _f(f, "fire_safe")),
    (lambda p: p == "fireproofing", lambda f: _f(f, "fireproofing")),
    (lambda p: p.startswith("leakage"), lambda f: _f(f, "tightness", "leakage_class")),
    (lambda p: p in ("air failure", "hydraulic failure"), lambda f: _f(f, "air_failure", "fail_position")),
    (lambda p: p == "power failure", lambda f: _f(f, "power_failure", "fail_position")),
]


# ── reading the reference workbook ─────────────────────────────────────────────────────────────

def xls_to_xlsx(data: bytes) -> bytes:
    """Old .xls -> .xlsx.  On the company PC Excel itself does it (PowerShell + COM), so the formatting is
    Excel's own conversion.  Elsewhere (or if Excel is missing) the caller gets a clear error."""
    if sys.platform != "win32":
        raise RuntimeError(".xls 는 이 서버에서 열 수 없습니다 — Excel 에서 '다른 이름으로 저장 → .xlsx' 로 바꿔 넣어 주세요")
    with tempfile.TemporaryDirectory() as td:
        src, dst = Path(td) / "in.xls", Path(td) / "out.xlsx"
        src.write_bytes(data)
        ps = ("$x=New-Object -ComObject Excel.Application;$x.DisplayAlerts=$false;"
              f"$w=$x.Workbooks.Open('{src}');$w.SaveAs('{dst}',51);$w.Close($false);$x.Quit()")
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, timeout=120,
                           capture_output=True)
        except Exception as e:                                         # noqa: BLE001 — any failure = same advice
            raise RuntimeError(".xls 를 .xlsx 로 바꾸지 못했습니다 (Excel 없음?) — Excel 에서 '다른 이름으로 저장 → "
                               f".xlsx' 로 바꿔 넣어 주세요 ({type(e).__name__})")
        if not dst.exists():
            raise RuntimeError(".xls 변환 결과가 없습니다 — Excel 에서 .xlsx 로 저장해 넣어 주세요")
        return dst.read_bytes()


def _merged_value(ws, r, c):
    v = ws.cell(r, c).value
    if v not in (None, ""):
        return v
    for m in ws.merged_cells.ranges:
        if m.min_row <= r <= m.max_row and m.min_col <= c <= m.max_col:
            return ws.cell(m.min_row, m.min_col).value
    return None


def analyse_sheet(ws):
    """Header rows, column paths, data blocks of an appendix sheet — or None if it has no 'Tag Number' column."""
    tag_col = hdr_top = None
    for r in range(1, min(ws.max_row, 12) + 1):
        for c in range(1, min(ws.max_column, 6) + 1):
            if _n(ws.cell(r, c).value) == "tag number":
                tag_col, hdr_top = c, r
                break
        if tag_col:
            break
    if not tag_col:
        return None
    supplier_col = tag_col + 1
    first = None
    for r in range(hdr_top + 1, ws.max_row + 1):
        if _n(ws.cell(r, supplier_col).value) == "requirement":
            first = r
            break
    if not first:
        return None
    paths = {}
    for c in range(1, ws.max_column + 1):
        parts = []
        for r in range(hdr_top, first):
            v = _n(_merged_value(ws, r, c))
            if v and v not in parts:
                parts.append(v)
        paths[c] = " › ".join(parts)
    # a 'Valve Body' group header over the first columns makes their paths 'valve body › …'; the TBE also
    # uses plain names (Piping Class) under it — keep the leaf when the parent is that group.
    for c, p in paths.items():
        if p.startswith("valve body › ") and "mfr" not in p:
            paths[c] = p[len("valve body › "):]
        if p.startswith("accessories › "):
            paths[c] = p[len("accessories › "):]
        if p.startswith("color (ral code) › "):
            paths[c] = "color › " + p[len("color (ral code) › "):]
    blocks, r = [], first
    while r <= ws.max_row:
        if _n(ws.cell(r, supplier_col).value) == "requirement":
            n = 1
            while r + n <= ws.max_row and ws.cell(r + n, supplier_col).value not in (None, "") \
                    and _n(ws.cell(r + n, supplier_col).value) != "requirement":
                n += 1
            blocks.append({"row": r, "rows": n, "tag": str(_merged_value(ws, r, tag_col) or "").strip()})
            r += n
        else:
            r += 1
    last_col = max(c for c in range(1, ws.max_column + 1) if any(ws.cell(rr, c).value not in (None, "")
                                                                     for rr in range(hdr_top, first)))
    title = " ".join(str(ws.cell(rr, cc).value) for rr in range(1, hdr_top) for cc in range(1, 4)
                     if ws.cell(rr, cc).value)
    return {"title": title, "hdr_top": hdr_top, "first": first, "tag_col": tag_col, "supplier_col": supplier_col,
            "paths": paths, "blocks": blocks, "last_col": last_col}


def describe(data: bytes) -> dict:
    """What the screen shows for an uploaded reference: sheets, columns and tags per sheet."""
    wb = openpyxl.load_workbook(io.BytesIO(data))
    out = []
    for ws in wb.worksheets:
        a = analyse_sheet(ws)
        if not a:
            out.append({"sheet": ws.title, "kind": "other"})
            continue
        mapped = [p for c, p in a["paths"].items() if p and _builder(p)]
        out.append({"sheet": ws.title, "kind": "appendix", "title": a["title"], "tags": [b["tag"] for b in a["blocks"]],
                    "columns": [p for p in a["paths"].values() if p], "mapped": mapped})
    return {"sheets": out}


def _builder(path):
    for test, b in COLUMNS:
        if test(path):
            return b
    return None


_TYPE_WORDS = {"XV": ["XV"], "ESDV": ["ESDV"], "SDV": ["SDV"], "BDV": ["BDV"], "MOV": ["MOTOR", "MOV"]}


def pick_sheet(sheets: dict, ds: dict):
    """Sheet for a new tag: title names the valve type; actuator medium breaks ties (Hydraulic vs Pneumatic)."""
    medium = _n(_val(ds["fields"].get("act_medium", {})) + " " + _val(ds["fields"].get("act_type", {})))
    best, score = None, 0
    for name, a in sheets.items():
        t = a["title"].upper()
        s = sum(2 for w in _TYPE_WORDS.get(ds["valve_type"], [ds["valve_type"]]) if re.search(rf"\b{w}S?\b", t))
        if not s:
            continue
        if "HYDRAULIC" in t:
            s += 1 if "hydraulic" in medium else -1
        elif "PNEUMATIC" in t and "hydraulic" not in medium:
            s += 0.5
        s -= 0.1 * len(re.findall(r"\b(?:XV|SDV|ESDV|BDV|MOV)S?\b", t))
        if s > score:
            best, score = name, s
    return best


# ── writing ────────────────────────────────────────────────────────────────────────────────────

def _copy_style(src, dst):
    if src.has_style:
        dst.font, dst.border, dst.fill = copy.copy(src.font), copy.copy(src.border), copy.copy(src.fill)
        dst.number_format, dst.alignment, dst.protection = src.number_format, copy.copy(src.alignment), copy.copy(src.protection)


def _src_text(ds, keys, docname):
    pages = sorted({ds["fields"][k].get("page") for k in keys if k in ds["fields"] and ds["fields"][k].get("page")})
    rows = sorted({ds["fields"][k].get("row") for k in keys if k in ds["fields"] and ds["fields"][k].get("row")})
    edited = [k for k in keys if ds["fields"].get(k, {}).get("edited_value") is not None]
    t = f"Source: {docname} p.{','.join(map(str, pages))} (row {','.join(map(str, rows))})"
    if edited:
        e = ds["fields"][edited[0]]
        t += f"\nEdited by {e.get('edited_by') or '-'} {e.get('edited_at') or ''}"
    return t


def _drop_vendor_rows(ws, a) -> int:
    """Keep only the 'Requirement' row of every tag block (the vendor rows AMPO · OMS · NEWAY … are dropped —
    user request 2026-10-31).  One pass: values · styles · comments · row heights move up, merged cells that
    spanned a block become single-row, merges inside a kept row move with it.  Returns rows removed."""
    first = a["first"]
    keep = [r for r in range(first, ws.max_row + 1)
            if _n(ws.cell(r, a["supplier_col"]).value) == "requirement"
            or not any(r in range(b["row"], b["row"] + b["rows"]) for b in a["blocks"])]
    if len(keep) == ws.max_row - first + 1:
        return 0
    new_of = {old: first + i for i, old in enumerate(keep)}
    merges = [m for m in ws.merged_cells.ranges if m.max_row >= first]
    for m in merges:
        ws.unmerge_cells(str(m))
    heights = {r: ws.row_dimensions[r].height for r in keep}
    max_col = ws.max_column
    for old in keep:
        new = new_of[old]
        if new == old:
            continue
        for c in range(1, max_col + 1):
            src, dst = ws.cell(old, c), ws.cell(new, c)
            dst.value, dst._style = src.value, copy.copy(src._style)
            dst.comment = copy.copy(src.comment) if src.comment else None
    removed = ws.max_row - (first + len(keep) - 1)
    ws.delete_rows(first + len(keep), removed)
    for old, h in heights.items():
        ws.row_dimensions[new_of[old]].height = h
    for r in range(first + len(keep), first + len(keep) + removed):
        ws.row_dimensions[r].height = None
    for m in merges:                                     # re-merge what still spans more than one cell
        r0 = new_of.get(m.min_row)
        if r0 is None:
            continue
        rows = [new_of[r] for r in range(m.min_row, m.max_row + 1) if r in new_of]
        r1 = max(rows)
        if r1 > r0 or m.max_col > m.min_col:
            ws.merge_cells(start_row=r0, start_column=m.min_col, end_row=r1, end_column=m.max_col)
    return removed


ALL_COLS = [("Area", 11), ("Site", 8), ("Unit", 6), ("Tag Number", 16), ("Tag Prefix", 7), ("Function", 8), ("Loop No.", 9), ("Valve Type", 9), ("DS Document No.", 20), ("DS Rev.", 6),
            ("Service", 30), ("P&ID No.", 22), ("Line No.", 24), ("Piping Class", 11), ("Size", 7), ("Rating", 8), ("Body Type", 24),
            ("End Connection", 20), ("Body Material", 26), ("Ball Material", 16), ("Stem Material", 16), ("Seat Material", 12),
            ("Fail Position", 9), ("Leakage Class", 20), ("NACE", 14), ("Special Requirements (Notes)", 40), ("Expert Review (Tool)", 40),
            ("Open Issues", 8), ("Valve List Sheet", 22), ("Tool Status", 12), ("DS Source (file · page)", 30)]
_ALL_KEYS = {"Service": "service", "P&ID No.": "pid_no", "Line No.": "line_no", "Piping Class": "piping_class", "Size": "body_size",
             "Rating": "rating", "Body Type": "body_type", "End Connection": "connections", "Body Material": "body_material",
             "Ball Material": "ball_material", "Stem Material": "stem_material", "Seat Material": "seat_material",
             "Fail Position": "fail_position", "Leakage Class": "leakage_class", "NACE": "nace"}


def _all_valves(wb, datasheets, docnames, link, sheet_of, report):
    """'All Valves' sheet: every tag (latest revision) on one row, with Area · Site · Unit first — filter with Excel."""
    from openpyxl.styles import Alignment, Font, PatternFill
    from app.valve import issues as issuesmod
    ws = wb.create_sheet("All Valves", 1 if len(wb.worksheets) > 1 else 0)
    ws.append([c for c, _ in ALL_COLS])
    for n, (_, w) in enumerate(ALL_COLS, 1):
        c = ws.cell(1, n)
        c.fill, c.font = PatternFill("solid", fgColor="1F2D4D"), Font(bold=True, color="FFFFFF")
        c.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(n)].width = w
    status = {k: s for s, ks in (("NEW", report["new"]), ("UPDATED", report["updated"]), ("UNCHANGED", report["unchanged"]),
                                 ("NO SHEET", report["no_sheet"])) for k in ks}
    order = {"North": 0, "South": 1, "Brownfield": 2, "W15": 3}
    for d in sorted(datasheets, key=lambda d: (order.get((d.get("location") or {}).get("area"), 9),
                                               (d.get("location") or {}).get("unit", ""), d["tag_key"])):
        loc, F = d.get("location") or {}, d["fields"]
        reqs = requirements.find(d, d.get("general_notes"))
        mr = [m for m in d.get("material_review") or [] if m["level"] != "Note"]
        n_open = sum(1 for i in d.get("issues") or [] if i["type"] in issuesmod.CONTRACTOR_TYPES and i.get("status") != "Dismissed")
        from app.valve import tagrules
        tp = tagrules.parse(_val(F.get("tag", {})) or d["tag_key"]) or {}
        row = {"Area": loc.get("area", ""), "Site": loc.get("site", ""), "Unit": loc.get("unit", ""), "Tag Number": d["tag_key"],
               "Tag Prefix": tp.get("prefix", ""), "Function": tp.get("func", ""), "Loop No.": (tp.get("number", "") + tp.get("suffix", "")) if tp else "",
               "Valve Type": d.get("valve_type", ""), "DS Document No.": d["doc_no"], "DS Rev.": d["rev"],
               "Special Requirements (Notes)": requirements.summary(reqs)[:32000],
               "Expert Review (Tool)": "\n".join(m.get("short") or m["title"] for m in mr)[:32000], "Open Issues": n_open,
               "Valve List Sheet": sheet_of.get(d["tag_key"], ""), "Tool Status": status.get(d["tag_key"], ""),
               "DS Source (file · page)": f"{docnames.get(d['document_id'], '')} p.{d['pages'][0]}" if d.get("pages") else ""}
        for h, k in _ALL_KEYS.items():
            row[h] = _val(F.get(k, {})) if k in F else ""
        ws.append([row.get(c, "") for c, _ in ALL_COLS])
        r = ws.max_row
        for n in range(1, len(ALL_COLS) + 1):
            ws.cell(r, n).alignment = Alignment(wrap_text=True, vertical="top")
        if link:
            ws.cell(r, 4).hyperlink = link(d, "tag")
            ws.cell(r, 4).font = Font(color="2F5BD8", underline="single", bold=True)
    ws.freeze_panes = "E2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(ALL_COLS))}{max(2, ws.max_row)}"


def build(template: bytes | None, datasheets: list[dict], docnames: dict, project: str = "",
          link=None, vendor_rows: bool = False) -> tuple[bytes, dict]:
    """-> (xlsx bytes, report).  `datasheets`: latest revision per tag, each with fields{key: field dict}.
    link(ds, field_key) -> url: when given, every written cell links to that field in the review tool
    (clicking the cell in Excel opens the PDF page at the point the value was read)."""
    report = {"updated": [], "new": [], "unchanged": [], "not_in_datasheets": [], "no_sheet": [], "changes": [], "kept": []}
    if template:
        wb = openpyxl.load_workbook(io.BytesIO(template))
    else:
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
    sheets = {}
    for ws in wb.worksheets:
        a = analyse_sheet(ws)
        if a and not vendor_rows and _drop_vendor_rows(ws, a):
            a = analyse_sheet(ws)                        # blocks are one row each now
        if a:
            sheets[ws.title] = a
    by_tag = {}
    for name, a in sheets.items():
        for b in a["blocks"]:
            by_tag.setdefault(schema.norm_tag(b["tag"]), (name, b))
    dsmap = {d["tag_key"]: d for d in datasheets}

    for name, a in sheets.items():                      # extra columns, header styled like the last header cell
        ws = wb[name]
        a["extra"] = {}
        for i, h in enumerate(EXTRA_HEADERS):
            c = a["last_col"] + 1 + i
            cell = ws.cell(a["hdr_top"], c, h)
            _copy_style(ws.cell(a["hdr_top"], a["last_col"]), cell)
            if a["first"] - 1 > a["hdr_top"]:
                ws.merge_cells(start_row=a["hdr_top"], start_column=c, end_row=a["first"] - 1, end_column=c)
            ws.column_dimensions[get_column_letter(c)].width = 10 if h in ("Area", "Site", "Unit") else 34 if h in ("Datasheet Notes", "Special Requirements (Notes)", "Expert Review (Tool)") else 18
            a["extra"][h] = c

    def write_block(ws, a, row, ds, is_new):
        changed = []
        docname = docnames.get(ds["document_id"], "")
        for c, path in a["paths"].items():
            b = _builder(path)
            if not b or c == a["supplier_col"]:
                continue
            if b == "TAG":
                if is_new:
                    ws.cell(row, c, ds["tag_key"])
                continue
            val, keys = b(ds["fields"])
            if not keys:
                continue
            if isinstance(val, str):
                val = re.sub(r"[ \t]{2,}", " ", val).strip()     # 'Chevron  type  V  pack' as printed with wide spacing
            cell = ws.cell(row, c)
            if link:
                cell.hyperlink = link(ds, keys[0])
            old = cell.value
            if _cmp(old) == _cmp(val) or (old not in (None, "") and val and material.same(str(old), val)):
                continue                                # '316 SS / HF' == 'SS 316/HF': same value, other notation
            if old not in (None, "") and val and material.equivalent(str(old), val):
                cell.comment = Comment(f"Datasheet says: {val}\n(same content — list kept)\n" + _src_text(ds, keys, docname),
                                       "Valve Review")
                report["kept"].append({"tag": ds["tag_key"], "sheet": ws.title, "column": path, "list": str(old), "datasheet": val})
                continue
            if not val and not is_new:                  # the datasheet is silent: keep what the list says
                continue
            note = _src_text(ds, keys, docname)
            ref = next((ds["fields"][k].get("ref") for k in keys if ds["fields"].get(k, {}).get("ref")), None)
            bare = re.sub(r"\(?\s*(general\s*)?note\s*[-–:#]?\s*\d+(\s*,\s*\d+)*\s*\)?", "", val, flags=re.I).strip()
            soft = _is_placeholder(val) or not bare or _is_placeholder(bare)
            if soft and not is_new and old not in (None, ""):
                # 'VTA' / 'General note - 3' says less than the list already does: keep the list, leave a trace
                txt = f"Datasheet says: {val}"
                if ref and ref.get("text"):
                    txt += f"\n→ {'General note' if ref.get('kind') == 'general' else 'Note'} {ref.get('no')}: {ref['text'][:400]}"
                cell.comment = Comment(txt + "\n" + note, "Valve Review")
                report["kept"].append({"tag": ds["tag_key"], "sheet": ws.title, "column": path, "list": str(old), "datasheet": val})
                continue
            if is_new and ref and ref.get("text") and soft:
                val = f"{val}: {ref['text']}"
            cell.value = val
            if not is_new:
                cell.fill = YELLOW
                note = f"Previous: {old if old not in (None, '') else '(blank)'}\n" + note
                changed.append(path)
                report["changes"].append({"tag": ds["tag_key"], "sheet": ws.title, "column": path,
                                          "previous": "" if old is None else str(old), "new": val})
            cell.comment = Comment(note, "Valve Review")
        e = a["extra"]
        notes = " | ".join(f"{n['no']}) {n['text']}" for n in ds["notes"])
        loc = ds.get("location") or {}
        for h in ("Area", "Site", "Unit"):
            ws.cell(row, e[h], loc.get(h.lower(), ""))
        ws.cell(row, e["DS Document No."], ds["doc_no"])
        ws.cell(row, e["DS Rev."], ds["rev"])
        src = ws.cell(row, e["DS Source (file · page)"], f"{docname} p.{'-'.join(map(str, [ds['pages'][0], ds['pages'][-1]]))}")
        if link:
            src.hyperlink = link(ds, "tag")
        ws.cell(row, e["Datasheet Notes"], notes[:32000])
        reqs = requirements.find(ds, ds.get("general_notes"))
        ws.cell(row, e["Special Requirements (Notes)"], requirements.summary(reqs)[:32000])
        mr = ds.get("material_review") or []
        ws.cell(row, e["Expert Review (Tool)"], "\n".join(f"{m.get('short') or m['title']}"
                                                            for m in mr if m["level"] != "Note")[:32000] or
                ("No action — notes in tool" if mr else ""))
        ws.cell(row, e["Tool Status"], "NEW" if is_new else ("UPDATED" if changed else "UNCHANGED"))
        ws.cell(row, e["Changed Columns"], "; ".join(changed))
        for h, c in e.items():
            _copy_style(ws.cell(row, a["last_col"]), ws.cell(row, c))
            ws.cell(row, c).alignment = copy.copy(ws.cell(row, a["last_col"]).alignment)
        if is_new:
            ws.cell(row, e["Tool Status"]).fill = GREEN
        return changed

    for key, ds in sorted(dsmap.items()):
        if key in by_tag:
            name, b = by_tag[key]
            ch = write_block(wb[name], sheets[name], b["row"], ds, False)
            report["updated" if ch else "unchanged"].append(key)
            continue
        name = pick_sheet(sheets, ds)
        if not name:
            report["no_sheet"].append(key)
            continue
        ws, a = wb[name], sheets[name]
        proto = a["blocks"][0]
        last = a["blocks"][-1]
        start = max(ws.max_row, last["row"] + last["rows"] - 1) + 1
        for i in range(proto["rows"]):                   # copy the first block's look (row heights, styles, vendor names)
            src_r = proto["row"] + i
            ws.row_dimensions[start + i].height = ws.row_dimensions[src_r].height
            for c in range(1, a["last_col"] + 1):
                _copy_style(ws.cell(src_r, c), ws.cell(start + i, c))
            if i:
                ws.cell(start + i, a["supplier_col"], ws.cell(src_r, a["supplier_col"]).value)
        ws.cell(start, a["supplier_col"], "Requirement")
        for m in list(ws.merged_cells.ranges):          # S.No. / Tag merged over the block, like the prototype
            if m.min_row == proto["row"] and m.max_row == proto["row"] + proto["rows"] - 1 and m.max_col < a["supplier_col"]:
                ws.merge_cells(start_row=start, start_column=m.min_col, end_row=start + proto["rows"] - 1, end_column=m.max_col)
        try:
            sno = max(float(ws.cell(bb["row"], 1).value) for bb in a["blocks"] if isinstance(ws.cell(bb["row"], 1).value, (int, float)))
            ws.cell(start, 1, sno + 1)
        except ValueError:
            pass
        write_block(ws, a, start, ds, True)
        a["blocks"].append({"row": start, "rows": proto["rows"], "tag": key})
        report["new"].append(key)

    for key, (name, b) in by_tag.items():
        if key not in dsmap:
            ws, a = wb[name], sheets[name]
            ws.cell(b["row"], a["extra"]["Tool Status"], "NOT IN UPLOADED DATASHEETS")
            report["not_in_datasheets"].append(key)

    for name, a in sheets.items():                      # Excel filter on every valve-type sheet: Area · Site · Unit · any column
        ws = wb[name]
        ws.auto_filter.ref = f"A{a['first'] - 1}:{get_column_letter(max(a['extra'].values()))}{max(ws.max_row, a['first'])}"
    _all_valves(wb, datasheets, docnames, link, {k: n for k, (n, _) in by_tag.items()}, report)

    if report["no_sheet"] or not sheets:                 # no reference, or a type no sheet names: tool's own list
        ws = wb.create_sheet("Valve List (tool format)")
        keys = []
        for d in datasheets:
            for k, f in d["fields"].items():
                if k not in keys and not k.startswith(("raw.", "x.")):
                    keys.append(k)
        disp = {k: next((d["fields"][k].get("display") for d in datasheets if k in d["fields"]), k) for k in keys}
        ws.append(["Tag Number", "Valve Type", "DS Document No.", "DS Rev."] + [disp[k] for k in keys if k != "tag"] +
                  ["Datasheet Notes", "DS Source"])
        todo = datasheets if not sheets else [dsmap[k] for k in report["no_sheet"]]
        for d in sorted(todo, key=lambda d: d["tag_key"]):
            ws.append([d["tag_key"], d["valve_type"], d["doc_no"], d["rev"]] +
                      [_val(d["fields"].get(k, {})) for k in keys if k != "tag"] +
                      [" | ".join(f"{n['no']}) {n['text']}" for n in d["notes"]),
                       f"{docnames.get(d['document_id'], '')} p.{d['pages'][0]}"])
        ws.auto_filter.ref = ws.dimensions
        ws.freeze_panes = "B2"

    ns = wb.create_sheet("Datasheet Notes")
    ns.append(["Tag Number", "DS Document No.", "DS Rev.", "Note No.", "Note", "Page", "File"])
    for d in sorted(datasheets, key=lambda d: d["tag_key"]):
        for n in d["notes"]:
            ns.append([d["tag_key"], d["doc_no"], d["rev"], n["no"], n["text"], n.get("page"),
                       docnames.get(d["document_id"], "")])
    ns.auto_filter.ref = ns.dimensions
    ns.freeze_panes = "A2"
    ns.column_dimensions["E"].width = 120

    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue(), report
