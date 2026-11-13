"""Deliverables for the design contractor: Issue List (xlsx) and the marked-up datasheet PDF.

Issue List  one row per issue: Tag · Doc. No. · Rev · Sheet x of y · file · PDF page · row · field · value ·
            issue type · description · required/expected · severity · status · reviewer note, plus two links —
            'Open in tool' (deep link to the page and point) and 'PDF page' (the original at that page).
Mark-up PDF the datasheet pages that have issues, copied from the originals (originals untouched), each issue
            boxed in its colour with a printed number label; after each datasheet an 'Issue Summary' page that
            lists the numbers; a cover page with counts per tag; a bookmark per tag.  Annotations carry the
            print flag, so 'print with mark-ups' shows them on paper.

Colours: red = data error / PMS non-compliance · orange = data missing / open item · yellow = revision change ·
blue = reviewer correction / comment · purple = extraction check (internal).
"""
from __future__ import annotations

import datetime as dt
import html
from copy import copy
import io
from urllib.parse import quote

import openpyxl
import pymupdf
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.valve import extract

RGB = {"error": (0.86, 0.15, 0.15), "missing": (1.0, 0.55, 0.0), "process": (0.95, 0.45, 0.05), "revision": (0.95, 0.76, 0.0),
       "comment": (0.18, 0.40, 0.90), "extract": (0.48, 0.30, 0.86), "material": (0.05, 0.55, 0.55)}
HEXFILL = {"error": "FBE3E1", "missing": "FFE8CC", "process": "FFE0C2", "revision": "FFF4C2", "comment": "E3ECFD", "extract": "EFE6FB", "material": "D9F2F2"}


def deep_link(base: str, project: str, i: dict) -> str:
    return (f"{base.rstrip('/')}/valve/?project={quote(project)}&ds={i['ds_id']}&key={quote(i['key'])}"
            f"&page={i.get('page') or ''}#review")


def pdf_link(base: str, i: dict) -> str:
    return f"{base.rstrip('/')}/api/valve/documents/{i['document_id']}/file#page={i.get('page') or 1}"


# ── Summary pivot (shared by the Issue List and the Valve List) ───────────────────

class _AreaOrder(dict):
    """valve40: also the site labels of the area rule table ('QN' · 'QN Brownfield N1' · 'QS' · 'W15') — QN, then QS, then W15."""
    def get(self, k, d=None):
        if k in self:
            return self[k]
        k = k or ""
        return 0.5 if k.startswith("QN") else 1.5 if k.startswith("QS") else 3 if k.startswith("W15") else d


AREA_ORDER = _AreaOrder({"North": 0, "South": 1, "Brownfield": 2, "North Brownfield": 2.1, "South Brownfield": 2.2, "W15": 3})


def summary_sheet(wb, title: str, heading: str, recs: list[dict], cat_name: str, cats: list[str], index: int | None = None,
                  extra: list[tuple[str, callable]] = ()):
    """Pivot sheet: No. · Area · Site · Unit × categories · Total (+ extra columns), filterable, then a Total row and a
    'By Area' table.  recs: dicts with area, site, unit and the category under `cat`; extra: (header, fn(list of recs) -> value)."""
    head_fill, head_font = PatternFill("solid", fgColor="1F2D4D"), Font(bold=True, color="FFFFFF")
    tot_fill, bold = PatternFill("solid", fgColor="E8EDF5"), Font(bold=True)
    ws = wb.create_sheet(title, index) if index is not None else wb.create_sheet(title)
    ws.cell(1, 1, heading).font = Font(bold=True, size=13)
    hdr = ["No.", "Area", "Site", "Unit"] + cats + ["Total"] + [h for h, _ in extra]
    for n, h in enumerate(hdr, 1):
        c = ws.cell(3, n, h)
        c.fill, c.font, c.alignment = head_fill, head_font, Alignment(wrap_text=True, vertical="center", horizontal="center")
        ws.column_dimensions[get_column_letter(n)].width = 6 if n == 1 else 12 if n <= 4 else 11
    groups: dict[tuple, list] = {}
    for r in recs:
        groups.setdefault((r.get("area") or "", r.get("site") or "", r.get("unit") or ""), []).append(r)
    keys = sorted(groups, key=lambda k: (AREA_ORDER.get(k[0], 9), k[1], k[2]))

    def line(L):
        cnt = [sum(1 for r in L if r["cat"] == c) or None for c in cats]
        return cnt + [len(L)] + [fn(L) for _, fn in extra]
    row = 4
    for n, k in enumerate(keys, 1):
        for col, v in enumerate([n, k[0] or "(not stated)", k[1], k[2]] + line(groups[k]), 1):
            ws.cell(row, col, v)
        row += 1
    ws.auto_filter.ref = f"A3:{get_column_letter(len(hdr))}{max(4, row - 1)}"
    for col, v in enumerate(["", "Total", "", ""] + line(recs), 1):
        c = ws.cell(row, col, v)
        c.fill, c.font = tot_fill, bold
    row += 3
    ws.cell(row - 1, 1, f"By Area — {cat_name}").font = Font(bold=True, size=12)
    hdr2 = ["No.", "Area", "Units"] + cats + ["Total"] + [h for h, _ in extra]
    for n, h in enumerate(hdr2, 1):
        c = ws.cell(row, n, h)
        c.fill, c.font, c.alignment = head_fill, head_font, Alignment(wrap_text=True, horizontal="center")
    areas: dict[str, list] = {}
    for r in recs:
        areas.setdefault(r.get("area") or "(not stated)", []).append(r)
    for n, a in enumerate(sorted(areas, key=lambda a: AREA_ORDER.get(a, 9)), 1):
        row += 1
        units = ", ".join(sorted({r.get("unit") or "" for r in areas[a]} - {""}))
        for col, v in enumerate([n, a, units] + line(areas[a]), 1):
            ws.cell(row, col, v)
    row += 1
    for col, v in enumerate(["", "Total", ""] + line(recs), 1):
        c = ws.cell(row, col, v)
        c.fill, c.font = tot_fill, bold
    ws.freeze_panes = "E4"
    return ws


def _area_sheet(wb, rows: list[dict], project: str):
    """'Summary by Area' sheet: one row per Area (North · South · Brownfield · W15) — units, tags, issue types,
    severity and review status — and the same per Area split by issue type × severity underneath."""
    head_fill, head_font = PatternFill("solid", fgColor="1F2D4D"), Font(bold=True, color="FFFFFF")
    tot_fill, bold = PatternFill("solid", fgColor="E8EDF5"), Font(bold=True)
    ws = wb.create_sheet("Summary by Area", 2)
    ws.cell(1, 1, f"Issue Summary by Area — {project}").font = Font(bold=True, size=13)
    types = [t for t in ["Data Error", "Data Missing", "Open Item", "PMS Non-Compliance", "PMS Review", "Process Mismatch", "Material Review",
                         "Valve Review", "Revision Change", "Reviewer Correction", "Reviewer Comment", "Extraction Review"] if any(i["type"] == t for i in rows)]
    statuses = [s for s in ["Open", "Confirmed", "Sent to Contractor", "Resolved", "Closed"] if any(i.get("status") == s for i in rows)] + \
        sorted({i.get("status") or "Open" for i in rows} - {"Open", "Confirmed", "Sent to Contractor", "Resolved", "Closed", "Dismissed"})
    hdr = ["No.", "Area", "Units", "Tags", "Total", "Major", "Minor"] + types + [f"Status: {s}" for s in statuses]
    for n, h in enumerate(hdr, 1):
        c = ws.cell(3, n, h)
        c.fill, c.font, c.alignment = head_fill, head_font, Alignment(wrap_text=True, vertical="center", horizontal="center")
        ws.column_dimensions[get_column_letter(n)].width = 6 if n == 1 else 12 if n == 2 else 22 if n == 3 else 11
    ws.row_dimensions[3].height = 32
    areas: dict[str, list] = {}
    for i in rows:
        areas.setdefault(i.get("area_name") or "(not stated)", []).append(i)

    def line(L):
        return [len({i["tag"] for i in L}), len(L), sum(1 for i in L if i["severity"] == "Major") or None,
                sum(1 for i in L if i["severity"] == "Minor") or None] + \
            [sum(1 for i in L if i["type"] == t) or None for t in types] + [sum(1 for i in L if (i.get("status") or "Open") == s) or None for s in statuses]
    r = 4
    order = sorted(areas, key=lambda a: AREA_ORDER.get(a, 9))
    for n, a in enumerate(order, 1):
        units = ", ".join(sorted({f"{i.get('site')}-{i.get('plant_unit')}" if a == "Brownfield" else (i.get("plant_unit") or "")
                                  for i in areas[a]} - {"", "-"}))
        for col, v in enumerate([n, a, units] + line(areas[a]), 1):
            ws.cell(r, col, v)
        r += 1
    ws.auto_filter.ref = f"A3:{get_column_letter(len(hdr))}{max(4, r - 1)}"
    for col, v in enumerate(["", "Total", ""] + line(rows), 1):
        c = ws.cell(r, col, v)
        c.fill, c.font = tot_fill, bold
    # per Area: issue type × severity
    r += 3
    ws.cell(r - 1, 1, "By Area × Issue Type × Severity").font = Font(bold=True, size=12)
    hdr2 = ["No.", "Area", "Issue Type", "Major", "Minor", "Info / Internal", "Total", "Tags"]
    for n, h in enumerate(hdr2, 1):
        c = ws.cell(r, n, h)
        c.fill, c.font, c.alignment = head_fill, head_font, Alignment(horizontal="center")
    k = 0
    for a in order:
        for t in types:
            L = [i for i in areas[a] if i["type"] == t]
            if not L:
                continue
            k += 1
            r += 1
            maj, mi = sum(1 for i in L if i["severity"] == "Major"), sum(1 for i in L if i["severity"] == "Minor")
            for col, v in enumerate([k, a, t, maj or None, mi or None, (len(L) - maj - mi) or None, len(L), len({i["tag"] for i in L})], 1):
                ws.cell(r, col, v)
    ws.freeze_panes = "C4"
    return ws


# ── Issue List (xlsx) ──────────────────────────────────────────────────────────

COLS = [("No.", 6), ("Area", 11), ("Site", 8), ("Unit", 6), ("Tag Number", 16), ("Valve Type", 8), ("Doc. No.", 20), ("Rev.", 6), ("Sheet", 9),
        ("PDF File", 22), ("PDF Page", 8), ("Row", 6), ("Field", 26), ("Datasheet Value", 30), ("Issue Type", 18),
        ("Description", 60), ("Required / Expected", 34), ("Evidence", 46), ("Basis", 30), ("Severity", 9), ("Status", 11), ("Reviewer Note", 30),
        ("Open in Tool", 13), ("PDF Page Link", 13),
        ("Rule ID", 12), ("Engineer Decision", 14), ("Decision Reason", 30)]          # valve29: appended, earlier columns unchanged
CI = {name: n for n, (name, _) in enumerate(COLS, 1)}           # column number by name


def ev_text(i: dict, n: int = 3) -> str:
    """valve28: the proof behind a finding, one line — 'PMS p.12 Class 1C3AS2 · Ball valve: 316 SS trim | Process Data p.54 Design Temp: 260 °C'."""
    out = []
    for e in (i.get("evidence") or [])[:n]:
        if not e:
            continue
        where = e.get("where") or ""
        pg = f" p.{e['page']}" if e.get("page") else ""
        txt = str(e.get("text") or "").strip().replace("\n", " ")
        out.append(f"{e.get('doc') or ''}{pg} {where}: {txt[:70]}".strip(" :"))
    return " | ".join(out)


def verification_sheet(wb, ver: list[dict]):
    """valve28: tags × checks — ✓ pass · ✗ findings · – not evaluable (reason in the cell comment column)."""
    from app.valve.checks import REGISTRY
    ws = wb.create_sheet("Verification")
    ids = [c[0] for c in REGISTRY]
    ws.append(["No.", "Area", "Unit", "Tag Number", "Doc. No.", "Rev.", "Pass", "Fail", "N/A"] + ids)
    ws.append(["", "", "", "", "", "", "", "", ""] + [c[1] for c in REGISTRY])
    for n, v in enumerate(ver, 1):
        st = {c["id"]: c for c in v["verification"]["checks"]}
        ws.append([n, v.get("area", ""), v.get("unit", ""), v["tag"], v.get("doc_no", ""), v.get("rev", ""),
                   v["verification"]["summary"]["pass"], v["verification"]["summary"]["fail"], v["verification"]["summary"]["na"]]
                  + [("✗" + (f" {st[i]['findings']}" if st[i]["findings"] > 1 else "") if st[i]["status"] == "fail" else "✓" if st[i]["status"] == "pass" else "–") if i in st else "" for i in ids])
    head_fill, head_font = PatternFill("solid", fgColor="1F2D4D"), Font(bold=True, color="FFFFFF")
    for c in ws[1]:
        c.fill, c.font = head_fill, head_font
    for c in ws[2]:
        c.font = Font(italic=True, color="5A6478", size=8)
        c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[2].height = 48
    for col, w in zip("ABCDEFGHI", (5, 10, 6, 16, 20, 5, 6, 6, 6)):
        ws.column_dimensions[col].width = w
    for k in range(10, 10 + len(ids)):
        ws.column_dimensions[get_column_letter(k)].width = 7
    red, grey = PatternFill("solid", fgColor="FBE3E1"), Font(color="9AA3B2")
    for r in range(3, ws.max_row + 1):
        for k in range(10, 10 + len(ids)):
            cell = ws.cell(r, k)
            cell.alignment = Alignment(horizontal="center")
            if str(cell.value or "").startswith("✗"):
                cell.fill = red
            elif cell.value == "–":
                cell.font = grey
    ws.freeze_panes = "E3"
    ws.auto_filter.ref = f"A2:{get_column_letter(9 + len(ids))}{max(2, ws.max_row)}"
    # reasons a check could not run, counted — the honest part of the report
    reasons = {}
    for v in ver:
        for c in v["verification"]["checks"]:
            if c["status"] == "n/a":
                reasons[(c["id"], c["reason"])] = reasons.get((c["id"], c["reason"]), 0) + 1
    if reasons:
        ws.append([])
        ws.append(["Not evaluable — why", "", "", "Check", "Reason", "Tags"])
        for (cid, why), n in sorted(reasons.items(), key=lambda x: -x[1]):
            ws.append(["", "", "", cid, why, n])


def _proto(ws, border=None, alignment=None, font=None, fill=None):
    """A cell style built once (valve29) on a scratch sheet of the same workbook; its StyleArray is copied to every cell that
    needs it (styles live in the workbook, so the copy is valid on any sheet).  The scratch sheet is removed at once."""
    wb = ws.parent
    tmp = wb.create_sheet("_style_tmp")
    c = tmp.cell(1, 1)
    if border is not None:
        c.border = border
    if alignment is not None:
        c.alignment = alignment
    if font is not None:
        c.font = font
    if fill is not None:
        c.fill = fill
    st = copy(c._style)
    wb.remove(tmp)
    return st


def requirements_xlsx(R: dict, project: str, base: str = "", area: str = "", req: str = "") -> bytes:
    """valve29 — Special Requirements at a glance: 'Summary by Area' · 'Summary by Unit' (Tag counts per requirement) ·
    'By Tag' (each requirement's text with its source, Excel filter).  area / req narrow the By Tag sheet like the screen."""
    wb = openpyxl.Workbook()
    thin = Side(style="thin", color="C9CFDB")
    box = Border(top=thin, bottom=thin, left=thin, right=thin)
    head_fill, head_font = PatternFill("solid", fgColor="1F2D4D"), Font(bold=True, color="FFFFFF")
    req_fill, tot_fill, on_fill = PatternFill("solid", fgColor="7A5A00"), PatternFill("solid", fgColor="E8EDF5"), PatternFill("solid", fgColor="FFF6D6")
    cols = R["columns"]

    def header(ws, row, names, req_from):
        for n, h in enumerate(names, 1):
            c = ws.cell(row, n, h)
            c.fill, c.font, c.border = (req_fill if n >= req_from else head_fill), head_font, box
            c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        ws.row_dimensions[row].height = 42

    ws = wb.active
    ws.title = "Summary by Area"
    ws.cell(1, 1, f"Special Requirements — {project} (Tags whose datasheet / notes require it · newest revision)").font = Font(bold=True, size=13)
    names = ["No.", "Area", "Units", "Tags"] + cols
    header(ws, 3, names, 5)
    r = 4
    for n, a in enumerate(R["by_area"], 1):
        for k, v in enumerate([n, a["area"], ", ".join(a["units"]), a["tags"]] + [a["counts"].get(h) or None for h in cols], 1):
            c = ws.cell(r, k, v)
            c.border = box
            if k > 4 and v:
                c.fill = on_fill
        r += 1
    for k, v in enumerate(["", "Total", "", R["total"]["tags"]] + [R["total"]["counts"].get(h) or None for h in cols], 1):
        c = ws.cell(r, k, v)
        c.fill, c.font, c.border = tot_fill, Font(bold=True), box
    for k, w in enumerate([5, 12, 22, 7] + [13] * len(cols), 1):
        ws.column_dimensions[get_column_letter(k)].width = w
    ws.freeze_panes = "E4"

    wu = wb.create_sheet("Summary by Unit")
    names = ["No.", "Area", "Site", "Unit", "Tags"] + cols
    header(wu, 1, names, 6)
    for n, u in enumerate(R["by_unit"], 1):
        for k, v in enumerate([n, u["area"], u["site"], u["unit"], u["tags"]] + [u["counts"].get(h) or None for h in cols], 1):
            c = wu.cell(n + 1, k, v)
            c.border = box
            if k > 5 and v:
                c.fill = on_fill
    for k, w in enumerate([5, 12, 9, 7, 7] + [13] * len(cols), 1):
        wu.column_dimensions[get_column_letter(k)].width = w
    wu.auto_filter.ref = f"A1:{get_column_letter(len(names))}{max(2, len(R['by_unit']) + 1)}"
    wu.freeze_panes = "F2"

    wt = wb.create_sheet("By Tag")
    names = ["No.", "Area", "Site", "Unit", "Tag Number", "Valve Type", "Rev.", "DS Document No.", "Count"] + cols
    header(wt, 1, names, 10)
    tags = [t for t in R["tags"] if (not area or t["area"] == area) and (not req or req in t["on"])]
    wrap = Alignment(wrap_text=True, vertical="top")
    for n, t in enumerate(tags, 1):
        vals = [n, t["area"], t["site"], t["unit"], t["tag"], t["valve_type"], t["rev"], t["doc_no"], len(t["on"])] + [t["cells"].get(h) or "" for h in cols]
        for k, v in enumerate(vals, 1):
            c = wt.cell(n + 1, k, v)
            c.border, c.alignment = box, wrap
            if k >= 10 and cols[k - 10] in t["on"]:
                c.fill = on_fill
        if base:
            c = wt.cell(n + 1, 5)
            c.hyperlink = deep_link(base, project, {"ds_id": t["ds_id"], "key": "tag", "page": None})
            c.font = Font(color="2F5BD8", underline="single", bold=True)
    for k, w in enumerate([5, 11, 8, 6, 16, 9, 5, 20, 7] + [30] * len(cols), 1):
        wt.column_dimensions[get_column_letter(k)].width = w
    wt.auto_filter.ref = f"A1:{get_column_letter(len(names))}{max(2, len(tags) + 1)}"
    wt.freeze_panes = "F2"
    info = wb.create_sheet("Info")
    for row in (["Project", project], ["Generated", dt.datetime.now().strftime("%Y-%m-%d %H:%M")], ["Filter", f"Area={area or 'all'} · Requirement={req or 'all'}"],
                ["Rule", "A requirement counts for a tag when its cell is filled and is not 'Not Required' — the datasheet row decides, Notes / General Notes add (sources in brackets)."]):
        info.append(row)
    info.column_dimensions["A"].width, info.column_dimensions["B"].width = 12, 110
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def digest_sheet(wb, entries: list[dict], project: str, lang: str = "en"):
    """valve35 — 'Comments (Typical)': the same comment on several tags is ONE row (its tags listed), touching Data Missing
    on one page is ONE block comment.  The full Issue List sheet keeps every finding."""
    from app.valve import i18n
    ws = wb.create_sheet("Comments (Typical)", 0)
    for x in wb.worksheets:                                  # open on this sheet (only one tab selected)
        x.sheet_view.tabSelected = x is ws
    wb.active = 0
    head = ["No.", "Kind", "Issue Type", "Rule", "Field", "Description", "Required / Expected", "Tags", "Tag Numbers", "Doc. No. / Page",
            "Severity", "Status"]
    widths = [6, 16, 18, 8, 22, 70, 30, 7, 40, 26, 9, 11]
    ws.append([f"Review comments — {project} · {len(entries)} comments (same comment on several tags = one Typical row; "
               f"touching Data Missing on one page = one block)"])
    ws["A1"].font = Font(bold=True, size=12)
    ws.append(head)
    hf, hfont = PatternFill("solid", fgColor="1F2D4D"), Font(bold=True, color="FFFFFF")
    for n, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(n)].width = w
        c = ws.cell(2, n)
        c.fill, c.font, c.alignment = hf, hfont, Alignment(wrap_text=True, vertical="center")
    wrap = Alignment(wrap_text=True, vertical="top")
    fills = {}
    for n, e in enumerate(entries, 1):
        typ = e["kind"] == "typical"
        units = e["units"] if typ else [e]
        kind = (f"Typical ({len(e['tags'])} tags)" if lang != "ko" else f"Typical ({len(e['tags'])}개 Tag)") if typ else \
            ("Block" if e["kind"] == "block" else "")
        if e["kind"] == "block" or (typ and e.get("of_kind") == "block"):
            kind += (" · block" if typ else "")
        m0 = e["members"][0]
        where = "; ".join(f"{u['members'][0].get('doc_no', '')} p.{u.get('page') or ''}" for u in units[:6]) + (" …" if len(units) > 6 else "")
        ws.append([n, kind, e["type"], e.get("check") or "", e.get("field") or "", i18n.pick(e.get("description"), e.get("description_ko"), lang),
                   e.get("expected") or "", len(e["tags"]) if typ else 1, ", ".join(e["tags"]) if typ else m0.get("tag", ""), where,
                   e.get("severity") or "", e.get("status") or ""])
        r = n + 2
        for k in range(1, len(head) + 1):
            ws.cell(r, k).alignment = wrap
        col = e.get("color") or ""
        if col not in fills:
            fills[col] = PatternFill("solid", fgColor=HEXFILL.get(col, "FFFFFF"))
        ws.cell(r, 3).fill = fills[col]
        if typ:
            ws.cell(r, 2).font = Font(bold=True)
    ws.freeze_panes = "C3"
    ws.auto_filter.ref = f"A2:{get_column_letter(len(head))}{max(2, len(entries) + 2)}"
    return ws


def issues_xlsx(rows: list[dict], base: str, project: str, by: str = "", sources: list[str] | None = None,
                verification: list[dict] | None = None, digest_entries: list[dict] | None = None, lang: str = "en") -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Issue List"
    thin = Side(style="thin", color="C9CFDB")
    head_fill, head_font = PatternFill("solid", fgColor="1F2D4D"), Font(bold=True, color="FFFFFF")
    ws.append([c for c, _ in COLS])
    for n, (_, w) in enumerate(COLS, 1):
        ws.column_dimensions[get_column_letter(n)].width = w
        c = ws.cell(1, n)
        c.fill, c.font = head_fill, head_font
        c.alignment = Alignment(wrap_text=True, vertical="center")
    rows = sorted(rows, key=lambda i: (AREA_ORDER.get(i.get("area_name") or "", 9), i.get("site") or "", i.get("plant_unit") or "",
                                       i["tag"]))                 # Area → Site → Unit → Tag; inside a tag the datasheet order stays
    box, wrap = Border(top=thin, bottom=thin, left=thin, right=thin), Alignment(wrap_text=True, vertical="top")
    st_base = _proto(ws, border=box, alignment=wrap)
    st_link = _proto(ws, border=box, alignment=wrap, font=Font(color="2F5BD8", underline="single"))
    st_link_b = _proto(ws, border=box, alignment=wrap, font=Font(color="2F5BD8", underline="single", bold=True))
    st_fill = {}
    for n, i in enumerate(rows, 1):
        sheet = f"{i['sheet']} of {i['of']}" if i.get("sheet") else ""
        val = (i.get("value") or "") + (f" {i['unit']}" if i.get("unit") and i.get("value") else "")
        ws.append([n, i.get("area_name", ""), i.get("site", ""), i.get("plant_unit", ""), i["tag"], i.get("valve_type", ""), i["doc_no"], i["rev"], sheet, i.get("filename", ""), i.get("page"),
                   i.get("row"), i["field"], val or "(blank)", i["type"], i["description"], i.get("expected", ""),
                   ev_text(i), (f"[{i['check']}] " if i.get("check") else "") + (i.get("basis") or ""),
                   i["severity"], i["status"], i.get("note", ""), "Open", "PDF p." + str(i.get("page") or ""),
                   i.get("check") or "", i.get("decision") or "",
                   " · ".join(x for x in (i.get("reason_cat"), i.get("conclusion")) if x)])
        r = n + 1                                            # valve29: ws.max_row rescans the sheet on every call (3.9 s / 2,900 rows)
        row = [ws.cell(r, k) for k in range(1, len(COLS) + 1)]   # ws[r] rescans the whole sheet for max_column
        for cell in row:                                     # valve29: one prepared style per kind of cell, copied — openpyxl
            cell._style = copy(st_base)                      # otherwise hashes a new Border/Alignment for every cell (13 s → 2 s)
        if i["color"] not in st_fill:
            st_fill[i["color"]] = _proto(ws, border=box, alignment=wrap, fill=PatternFill("solid", fgColor=HEXFILL.get(i["color"], "FFFFFF")))
        row[CI["Issue Type"] - 1]._style = copy(st_fill[i["color"]])
        if base:
            for col, url in ((CI["Open in Tool"], deep_link(base, project, i)), (CI["PDF Page Link"], pdf_link(base, i))):
                row[col - 1].hyperlink = url
                row[col - 1]._style = copy(st_link)
            row[CI["Tag Number"] - 1].hyperlink = deep_link(base, project, i)       # the tag itself also jumps to the point
            row[CI["Tag Number"] - 1]._style = copy(st_link_b)
    ws.freeze_panes = ws.cell(2, CI["Tag Number"] + 1).coordinate          # No. · Area · Site · Unit · Tag stay visible
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLS))}{max(1, ws.max_row)}"

    summary_sheet(wb, "Summary", f"Issue Summary — {project} (by Area / Site / Unit)",
                  [{"area": i.get("area_name"), "site": i.get("site"), "unit": i.get("plant_unit"), "cat": i["type"], "sev": i["severity"],
                    "tag": i["tag"]} for i in rows], "Issue Type",
                  [t for t in ["Data Error", "Data Missing", "Open Item", "PMS Non-Compliance", "PMS Review", "Process Mismatch", "Material Review",
                               "Valve Review", "Revision Change", "Reviewer Correction", "Reviewer Comment", "Extraction Review"]
                   if any(i["type"] == t for i in rows)], index=1,
                  extra=[("Major", lambda L: sum(1 for r in L if r["sev"] == "Major") or None),
                         ("Minor", lambda L: sum(1 for r in L if r["sev"] == "Minor") or None),
                         ("Tags", lambda L: len({r["tag"] for r in L}))])
    _area_sheet(wb, rows, project)
    if verification:
        verification_sheet(wb, verification)
    sm = wb.create_sheet("Summary by Tag")
    types = [t for t in ["Data Error", "Data Missing", "Open Item", "PMS Non-Compliance", "PMS Review", "Revision Change",
                         "Process Mismatch", "Material Review", "Valve Review", "Reviewer Correction", "Reviewer Comment", "Extraction Review"]
             if any(i["type"] == t for i in rows)]
    sm.append(["No.", "Area", "Site", "Unit", "Tag Number", "Doc. No.", "Rev.", "Total"] + types)
    for c in range(1, len(types) + 9):
        sm.cell(1, c).fill, sm.cell(1, c).font = head_fill, head_font
        sm.column_dimensions[get_column_letter(c)].width = 6 if c == 1 else 11 if c <= 4 else 14 if c > 7 else 20
    tags = {}
    for i in rows:
        t = tags.setdefault(i["tag"], {"doc": i["doc_no"], "rev": i["rev"], "n": {},
                                       "loc": (i.get("area_name", ""), i.get("site", ""), i.get("plant_unit", ""))})
        t["n"][i["type"]] = t["n"].get(i["type"], 0) + 1
    for n, (tag, t) in enumerate(sorted(tags.items(), key=lambda kv: (AREA_ORDER.get(kv[1]["loc"][0], 9), kv[1]["loc"][1], kv[1]["loc"][2], kv[0])), 1):
        sm.append([n, *t["loc"], tag, t["doc"], t["rev"], sum(t["n"].values())] + [t["n"].get(x, 0) or None for x in types])
    sm.append(["", "Total", "", "", "", "", "", len(rows)] + [sum(1 for i in rows if i["type"] == x) for x in types])
    for c in range(1, len(types) + 9):
        sm.cell(sm.max_row, c).font = Font(bold=True)
    sm.freeze_panes = "F2"
    sm.auto_filter.ref = f"A1:{get_column_letter(len(types) + 8)}{max(1, sm.max_row - 1)}"

    if digest_entries is not None:
        digest_sheet(wb, digest_entries, project, lang)
    info = wb.create_sheet("Info")
    for row in [["Valve Datasheet Review — Issue List"], ["Project", project],
                ["Generated", dt.datetime.now().strftime("%Y-%m-%d %H:%M")], ["Generated by", by or "-"],
                ["Source files", ", ".join(sources or [])], [],
                ["Issue Type", "Meaning"],
                ["Data Error", "The datasheet contradicts itself or refers to a note that does not exist"],
                ["Data Missing", "A required field is on the form but has no value"],
                ["Open Item", "A required field is still HOLD / TBC"],
                ["PMS Non-Compliance", "Differs from the Piping Material Specification (material compared by grade, not spelling)"],
                ["PMS Review", "Could not be confirmed against the PMS — engineer to confirm"],
                ["Revision Change", "Changed from the previous revision of the same tag"],
                ["Material Review / Valve Review", "Material and valve-design comments of the review tool (Action = Major, Confirm = Minor)"],
                ["Area / Site / Unit", "From the datasheet title (QELNG North / South / W15; 'SYSTEM xx - UNIT yy' = existing plant = Brownfield) "
                                       "and the P&ID number — use the Excel filter on these columns"],
                ["Reviewer Correction / Comment", "Entered by the reviewer"],
                [], ["Every row is linked: 'Open' opens the review tool at the field, 'PDF p.' opens the original page."]]:
        info.append(row)
    info["A1"].font = Font(bold=True, size=13)
    info.column_dimensions["A"].width = 30
    info.column_dimensions["B"].width = 100
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


# ── marked-up PDF ──────────────────────────────────────────────────────────────

def _ascii(s: str) -> str:
    return (s or "").replace("→", "->").replace("≤", "<=").replace("—", "-").replace("·", "-")


def _story_pages(html_body: str) -> pymupdf.Document:
    css = ("body{font-family:sans-serif;font-size:8pt;} h1{font-size:12pt;margin:0 0 4pt 0;} p{margin:0 0 6pt 0;}"
           "table{border-collapse:collapse;width:100%;} th{background-color:#1F2D4D;color:#FFFFFF;text-align:left;}"
           "th,td{border:0.5pt solid #9AA3B2;padding:2pt 3pt;vertical-align:top;}")
    buf = io.BytesIO()
    w = pymupdf.DocumentWriter(buf)
    story = pymupdf.Story(html=html_body, user_css=css)
    box = pymupdf.paper_rect("a4-l")
    more = 1
    while more:
        dev = w.begin_page(box)
        more, _ = story.place(box + (30, 30, -30, -30))
        story.draw(dev)
        w.end_page()
    w.close()
    return pymupdf.open("pdf", buf.getvalue())


def _swatch(color):
    r, g, b = RGB.get(color, (0.5, 0.5, 0.5))
    return f"#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"


def _info(a, i):
    a.set_info(title=f"#{i['no']} {i['type']} ({i['severity']})" + (f" — {i['by']}" if i.get("by") else ""),
               content=f"{i['field']}: {i.get('value') or '(blank)'}\n{i['description']}"
                       + (f"\nRequired / expected: {i['expected']}" if i.get("expected") else ""))
    a.set_flags(pymupdf.PDF_ANNOT_IS_PRINT)


def _hex(c):
    c = str(c or "").lstrip("#")
    return (int(c[0:2], 16) / 255, int(c[2:4], 16) / 255, int(c[4:6], 16) / 255) if len(c) == 6 else None


_GLYPH = {"✓": [[(0.15, 0.55), (0.4, 0.8), (0.88, 0.2)]], "✗": [[(0.15, 0.15), (0.85, 0.85)], [(0.85, 0.15), (0.15, 0.85)]]}


def _markup(page, i, col):
    """A reviewer's own mark-up, drawn as the same kind of PDF annotation (editable in Acrobat / Bluebeam).
    valve23: style {color, width, opacity, size, stamp} · underline / strike / squiggle · stamps."""
    kind, r, pts = i.get("kind") or "rect", pymupdf.Rect(*i["bbox"]), i.get("points")
    st = i.get("style") or {}
    col = _hex(st.get("color")) or col
    wd = float(st.get("width") or 1.6)
    if kind == "highlight":
        a = page.add_highlight_annot(r)
        a.set_colors(stroke=col)
        a.set_opacity(float(st.get("opacity") or 0.45))
    elif kind in ("underline", "strike", "squiggle"):
        a = {"underline": page.add_underline_annot, "strike": page.add_strikeout_annot, "squiggle": page.add_squiggly_annot}[kind](r)
        a.set_colors(stroke=col)
    elif kind == "stamp":
        label = st.get("stamp") or i.get("text_raw") or "STAMP"
        if label in _GLYPH:                                     # ✓ ✗ drawn as ink so every PDF reader shows them
            a = page.add_ink_annot([[(r.x0 + x * r.width, r.y0 + y * r.height) for x, y in stk] for stk in _GLYPH[label]])
            a.set_colors(stroke=col)
            a.set_border(width=max(2.0, wd * 1.5))
        else:
            fs = float(st.get("size") or max(8, min(28, r.height * 0.6)))
            frame = page.add_rect_annot(r)                      # coloured frame as its own Square annot (readers vary on FreeText borders)
            frame.set_colors(stroke=col, fill=(1, 1, 1))
            frame.set_border(width=max(1.2, wd))
            frame.set_opacity(0.9)
            _info(frame, i)
            frame.update()
            a = page.add_freetext_annot(r, label, fontsize=fs, fontname="hebo", text_color=col, align=1)
            a.set_border(width=0)
    elif kind in ("line", "arrow") and pts and len(pts) >= 2:
        a = page.add_line_annot(pymupdf.Point(*pts[0]), pymupdf.Point(*pts[-1]))
        a.set_colors(stroke=col)
        a.set_border(width=wd)
        if kind == "arrow":
            a.set_line_ends(pymupdf.PDF_ANNOT_LE_NONE, pymupdf.PDF_ANNOT_LE_OPEN_ARROW)
    elif kind in ("polyline", "polygon") and pts and len(pts) >= 2:
        P = [pymupdf.Point(*p) for p in pts]
        a = page.add_polygon_annot(P) if kind == "polygon" else page.add_polyline_annot(P)
        a.set_colors(stroke=col)
        a.set_border(width=wd)
    elif kind == "callout" and pts:
        txt = i.get("text_raw") or i["description"]
        try:                                                    # FreeText with a leader line ending in an arrow (Acrobat 'Callout')
            a = page.add_freetext_annot(r, txt, fontsize=float(st.get("size") or 9), text_color=col, fill_color=(1, 1, 1),
                                        border_color=col, callout=[pymupdf.Point(*p) for p in pts[:3]],
                                        line_end=pymupdf.PDF_ANNOT_LE_OPEN_ARROW, rich_text=True)
        except (TypeError, ValueError):                         # older PyMuPDF: box + separate arrow line
            ln = page.add_line_annot(pymupdf.Point(*pts[-1]), pymupdf.Point(*pts[0]))
            ln.set_colors(stroke=col)
            ln.set_line_ends(pymupdf.PDF_ANNOT_LE_NONE, pymupdf.PDF_ANNOT_LE_OPEN_ARROW)
            _info(ln, i)
            ln.update()
            a = page.add_freetext_annot(r, txt, fontsize=float(st.get("size") or 9), text_color=col, fill_color=(1, 1, 1))
        a.set_border(width=max(0.8, wd * 0.6))
    elif kind == "typewriter":
        a = page.add_freetext_annot(r, i.get("text_raw") or i["description"], fontsize=float(st.get("size") or 10), text_color=col)
        a.set_border(width=0)
    elif kind == "pen" and pts:
        a = page.add_ink_annot([[tuple(p) for p in stk] for stk in pts])
        a.set_colors(stroke=col)
        a.set_border(width=wd)
    elif kind == "text":
        a = page.add_freetext_annot(r, i.get("text_raw") or i["description"], fontsize=float(st.get("size") or 9), text_color=col,
                                    fill_color=(1, 1, 1))
        a.set_border(width=0.8)
    elif kind == "note":
        a = page.add_text_annot(r.tl, i["description"], icon="Comment")
        a.set_colors(stroke=col)
    else:                                                       # rect · cloud · ellipse
        a = page.add_circle_annot(r) if kind == "ellipse" else page.add_rect_annot(r)
        a.set_colors(stroke=col)
        a.set_border(width=wd, clouds=2 if kind == "cloud" else 0)
    _info(a, i)
    if kind in ("text", "stamp", "typewriter", "callout"):      # a free-text box shows its content: keep the reviewer's words
        a.set_info(content=(st.get("stamp") if kind == "stamp" else "") or i.get("text_raw") or i["description"])
    a.update()
    return r


def _annotate(page, i):
    if not i.get("bbox"):
        return
    col = RGB.get(i["color"], RGB["comment"])
    if i.get("comment_id"):
        r = _markup(page, i, col)
        _label(page, r, i, col)
        return
    r = pymupdf.Rect(*i["bbox"]) + (-1.5, -1.5, 1.5, 1.5)
    if r.width < 6:
        r.x1 = r.x0 + 6
    if r.height < 6:
        r.y1 = r.y0 + 6
    if i["color"] == "revision":
        a = page.add_highlight_annot(r)
        a.set_colors(stroke=col)
        a.set_opacity(0.5)
    else:
        a = page.add_rect_annot(r)
        fill = {"missing": (1, 0.92, 0.80), "process": (1, 0.88, 0.76), "error": None}.get(i["color"])
        a.set_colors(stroke=col, fill=fill)
        a.set_border(width=1.4, dashes=[3, 2] if i["color"] in ("comment", "extract") else None)
        if fill:
            a.set_opacity(0.55)
    _info(a, i)
    a.update()
    _label(page, r, i, col)


def _label(page, r, i, col):
    lab = pymupdf.Rect(r.x0 - 13, r.y0 - 1, r.x0 - 1, r.y0 + 8)
    if lab.x0 < 2:
        lab = pymupdf.Rect(r.x0, r.y0 - 10, r.x0 + 12, r.y0 - 1)
    t = page.add_freetext_annot(lab, str(i["no"]), fontsize=6.5, text_color=(1, 1, 1), fill_color=col, align=1)
    t.set_flags(pymupdf.PDF_ANNOT_IS_PRINT)
    t.update(text_color=(1, 1, 1), fill_color=col)


MARGIN_W = 250                                           # pt added to the right of a datasheet page for the comments
_MCSS = ("*{font-family:sans-serif;} body{font-size:6.6pt;line-height:1.18;color:#1B2433;} p{margin:0 0 3.2pt 0;}"
         ".h{font-size:7.6pt;font-weight:bold;color:#1F2D4D;margin:0 0 4pt 0;border-bottom:0.6pt solid #1F2D4D;}"
         ".n{color:#FFFFFF;font-weight:bold;} .t{font-weight:bold;} .r{color:#5A6478;} .q{color:#0E5A3A;}")


def _cmt_html(i) -> str:
    """One numbered comment as printed beside the page: [no] Type · Field — description · Required … · reviewer."""
    who = f" <span class='r'>({html.escape(i['by'])})</span>" if i.get("by") else ""
    val = i.get("value")
    req = f" <span class='q'>Required: {html.escape(_ascii(i['expected']))}</span>" if i.get("expected") else ""
    v = f" <span class='r'>[{html.escape(_ascii(str(val))[:60])}]</span>" if val and not i.get("comment_id") else ""
    evs = ev_text(i, 2)
    ev = f"<br/><span class='r'>Evidence: {html.escape(_ascii(evs))}</span>" if evs else ""
    return (f"<p><span class='n' style='background-color:{_swatch(i['color'])}'>&nbsp;{i['no']}&nbsp;</span> "
            f"<span class='t'>{html.escape(i['type'])}</span> · {html.escape(_ascii(i.get('field') or ''))}{v}{who}<br/>"
            f"{html.escape(_ascii(i.get('description') or '')).replace(chr(10), '<br/>')}{req}{ev}</p>")


def _comment_margin(out, pno: int, items: list[dict], head: str) -> list[dict]:
    """valve25: widen the page to the right and print its numbered comments there, so the comments print with the page in
    every viewer (no pop-ups needed).  Returns the comments that did not fit (they go to a continuation page)."""
    page = out[pno]
    if page.rotation or not items:
        return items
    mb = page.mediabox
    page.set_mediabox(pymupdf.Rect(mb.x0, mb.y0, mb.x1 + MARGIN_W, mb.y1))
    pr = page.rect
    page.draw_rect(pymupdf.Rect(pr.x1 - MARGIN_W, pr.y0, pr.x1, pr.y1), color=None, fill=(0.97, 0.975, 0.985), overlay=False)
    page.draw_line((pr.x1 - MARGIN_W, pr.y0 + 14), (pr.x1 - MARGIN_W, pr.y1 - 14), color=(0.62, 0.66, 0.74), width=0.6)
    box = pymupdf.Rect(pr.x1 - MARGIN_W + 8, pr.y0 + 14, pr.x1 - 8, pr.y1 - 14)
    hd = f"<p class='h'>{html.escape(head)}</p>"
    n = len(items)
    while n > 0:
        more = f"<p class='r'>… {len(items) - n} more on the next page</p>" if n < len(items) else ""
        spare, _ = page.insert_htmlbox(box, hd + "".join(_cmt_html(i) for i in items[:n]) + more, css=_MCSS, scale_low=0.8)
        if spare >= 0:
            return items[n:]
        n = n - max(1, n // 4) if n > 8 else n - 1
    page.insert_htmlbox(box, hd + "<p class='r'>Comments on the next page.</p>", css=_MCSS)
    return items


def _comment_page(items: list[dict], head: str, size) -> pymupdf.Document:
    buf = io.BytesIO()
    w = pymupdf.DocumentWriter(buf)
    story = pymupdf.Story(html=f"<p class='h'>{html.escape(head)}</p>" + "".join(_cmt_html(i) for i in items), user_css=_MCSS)
    box = pymupdf.Rect(0, 0, *size)
    more = 1
    while more:
        dev = w.begin_page(box)
        more, _ = story.place(box + (36, 36, -36, -36))
        story.draw(dev)
        w.end_page()
    w.close()
    return pymupdf.open("pdf", buf.getvalue())


@extract.pdf_locked
def markup_pdf(entries: list[dict], project: str, title: str = "Valve Datasheet Review — Mark-up",
               summary_pages: bool = True, margin: bool = True, flatten: bool = True) -> bytes:
    """valve25: margin — each page carries its numbered comments (program + reviewer) printed beside it;
    flatten — annotations are baked into the page so every viewer and printer shows them exactly as on screen
    (off = editable annotations for Acrobat / Bluebeam)."""
    """entries: [{path, pages, tag, doc_no, rev, filename, issues}] in output order."""
    out = pymupdf.open()
    toc, srcs, skipped = [], {}, []
    if len(entries) > 1:                                   # cover: counts per tag
        rows = "".join(
            f"<tr><td>{html.escape(e['tag'])}</td><td>{html.escape(e['doc_no'])}</td><td>{html.escape(e['rev'])}</td>"
            f"<td>{len(e['issues'])}</td><td>{sum(1 for i in e['issues'] if i['color'] == 'error')}</td>"
            f"<td>{sum(1 for i in e['issues'] if i['color'] == 'missing')}</td>"
            f"<td>{sum(1 for i in e['issues'] if i['color'] == 'revision')}</td>"
            f"<td>{sum(1 for i in e['issues'] if i['color'] in ('comment', 'extract'))}</td></tr>" for e in entries)
        cover = _story_pages(
            f"<h1>{html.escape(_ascii(title))}</h1><p>Project: {html.escape(project)} - generated "
            f"{dt.datetime.now():%Y-%m-%d %H:%M} - {sum(len(e['issues']) for e in entries)} issues on {len(entries)} datasheets.</p>"
            "<p>Box colours: <b>red</b> data error / PMS non-compliance, <b>orange</b> data missing / open item, "
            "<b>yellow</b> revision change, <b>blue</b> reviewer correction / comment. Each box has a number; the "
            "Issue Summary page after each datasheet explains it.</p>"
            "<table><tr><th>Tag</th><th>Doc. No.</th><th>Rev.</th><th>Issues</th><th>Error/PMS</th><th>Missing/Open</th>"
            f"<th>Revision</th><th>Reviewer</th></tr>{rows}</table>")
        out.insert_pdf(cover)
        toc.append([1, "Cover - issue counts", 1])
    for e in entries:
        if e["path"] not in srcs:
            try:
                srcs[e["path"]] = extract.open_stored(e["path"])
            except extract.PdfError:                         # valve38: a broken stored copy skips that tag, not the whole file
                skipped.append(e["tag"])
                continue
        src = srcs[e["path"]]
        # valve29: each datasheet is built in its own small document and appended once.  Working on the growing output
        # re-loaded a page per annotation from an ever larger page tree (500 tags: 182 s, quadratic) — same pages, same marks.
        sub = pymupdf.open()
        pmap = {}
        for p in e["pages"]:
            if 1 <= p <= src.page_count:
                sub.insert_pdf(src, from_page=p - 1, to_page=p - 1)
                pmap[p] = sub.page_count - 1
        if not pmap:
            sub.close()
            continue
        pages = {p: sub[k] for p, k in pmap.items()}       # each page loaded once
        for i in e["issues"]:
            if i.get("page") in pages:
                _annotate(pages[i["page"]], i)
        if margin:                                         # last page first: continuation pages shift later indexes only
            for p in sorted(pmap, key=lambda k: -pmap[k]):
                its = [i for i in e["issues"] if i.get("page") == p]
                head = f"{e['tag']} · Rev.{e['rev']} · p.{p} — Review comments ({len(its)})"
                rest = _comment_margin(sub, pmap[p], its, head)
                if rest:
                    pg = sub[pmap[p]]
                    sub.insert_pdf(_comment_page(rest, head + " (cont.)", (pg.rect.width, pg.rect.height)),
                                   start_at=pmap[p] + 1)
        if flatten:
            sub.bake(annots=True, widgets=True)            # mark-ups become page content: identical on screen, print, any viewer
        start = out.page_count
        out.insert_pdf(sub)
        sub.close()
        toc.append([1, f"{e['tag']}  Rev.{e['rev']}  ({len(e['issues'])})", start + 1])
        if summary_pages and e["issues"]:
            trs = "".join(
                f"<tr><td><span style='background-color:{_swatch(i['color'])};color:#FFFFFF'>&nbsp;{i['no']}&nbsp;</span></td>"
                f"<td>{i['sheet'] or ''} of {i['of'] or ''} (p.{i.get('page') or ''})</td><td>{i.get('row') or ''}</td>"
                f"<td>{html.escape(_ascii(i['field']))}</td><td>{html.escape(_ascii(i.get('value') or '(blank)'))}</td>"
                f"<td>{html.escape(i['type'])}</td><td>{html.escape(_ascii(i['description'])).replace(chr(10), '<br/>')}</td>"
                f"<td>{html.escape(_ascii(i.get('expected') or ''))}</td><td>{html.escape(i['status'])}</td></tr>"
                for i in e["issues"])
            s = _story_pages(
                f"<h1>Issue Summary - {html.escape(e['tag'])}</h1><p>Doc. No. {html.escape(e['doc_no'])} - Rev. "
                f"{html.escape(e['rev'])} - file {html.escape(e.get('filename') or '')} - PDF pages "
                f"{', '.join(map(str, e['pages']))}</p><table><tr><th>No.</th><th>Sheet</th><th>Row</th><th>Field</th>"
                f"<th>Datasheet Value</th><th>Issue</th><th>Description</th><th>Required / Expected</th><th>Status</th></tr>"
                f"{trs}</table>")
            out.insert_pdf(s)
    for d in srcs.values():
        d.close()
    if skipped:                                              # valve38: say which tags are missing and why — not silently
        note = _story_pages(f"<h2>Not included</h2><p>The server's stored copy of the original PDF could not be opened for: "
                            f"{html.escape(', '.join(skipped))}.</p><p>Upload the same datasheet file again in Document Management "
                            "(the stored copy is rewritten; tags, findings and decisions stay).</p>")
        out.insert_pdf(note, start_at=0)
        toc = [[lv, t, pg + note.page_count] for lv, t, pg in toc]
    if out.page_count == 0:
        out.new_page()
        out[0].insert_text((72, 72), "No issues selected.", fontsize=12)
    out.set_toc(toc)
    return out.tobytes(garbage=4, deflate=True, use_objstms=1)    # garbage=4: logos and fonts stored once (8x smaller)


# ── Revision comparison (xlsx) ───────────────────────────────────────────────────

def revisions_xlsx(entries: list[dict], project: str, by: str = "") -> bytes:
    """entries: [{tag, doc_no, prev_rev, new_rev, rows: compare rows}] — one line per changed cell."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Revision Changes"
    cols = [("Tag Number", 16), ("Doc. No.", 20), ("Previous Rev.", 12), ("New Rev.", 10), ("Field", 28), ("Row", 6),
            ("Previous Value", 36), ("New Value", 36), ("Change", 11), ("PDF Page", 9)]
    head_fill, head_font = PatternFill("solid", fgColor="1F2D4D"), Font(bold=True, color="FFFFFF")
    ws.append([c for c, _ in cols])
    for n, (_, w) in enumerate(cols, 1):
        ws.column_dimensions[get_column_letter(n)].width = w
        c = ws.cell(1, n)
        c.fill, c.font = head_fill, head_font
    fills = {"Modified": "FFF4C2", "Added": "E1F1FF", "Deleted": "FBE3E1"}
    n = 0
    for e in entries:
        for r in e["rows"]:
            if r["change"] == "Unchanged":
                continue
            ws.append([e["tag"], e["doc_no"], e["prev_rev"], e["new_rev"], r.get("display") or r["key"], r.get("row"),
                       r.get("previous") or "", r.get("new") or "", r["change"], r.get("new_page") or r.get("prev_page")])
            n += 1
            ws.cell(ws.max_row, 9).fill = PatternFill("solid", fgColor=fills.get(r["change"], "FFFFFF"))
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{max(1, ws.max_row)}"
    sm = wb.create_sheet("Summary")
    sm.append(["Tag Number", "Doc. No.", "Revisions", "Modified", "Added", "Deleted"])
    for e in entries:
        c = {k: sum(1 for r in e["rows"] if r["change"] == k) for k in ("Modified", "Added", "Deleted")}
        sm.append([e["tag"], e["doc_no"], f"{e['prev_rev']} → {e['new_rev']}", c["Modified"], c["Added"], c["Deleted"]])
    info = wb.create_sheet("Info")
    info.append(["Project", project]), info.append(["Generated", dt.datetime.now().strftime("%Y-%m-%d %H:%M")]), info.append(["By", by])
    info.append(["Rule", "Material written differently but meaning the same (316 SS / HF = SS 316/HF) counts as Unchanged"])
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue(), n
