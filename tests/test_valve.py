"""Valve Datasheet Review (app/valve) — extraction, grouping, revision compare, Valve List fill, API.

The client's datasheets / TBE are not in the repository.  These tests draw a small ruled datasheet with
PyMuPDF in the same shape (row numbers · label cells · value cells · title block · NOTES on sheet 2) and
a matching appendix workbook.  With VALVE_SAMPLES=<folder with Datasheet.pdf> the real file is read too.
"""
from __future__ import annotations

import io
import os
import time
from pathlib import Path

import openpyxl
import pymupdf
import pytest

from app.valve import api, extract, schema, store, tbe

ROWS = [  # (no, [labels], [values]) — consecutive like the real form; fields are found by label, not number  — two labels pair with left / right value halves
    (1, ["Tag No.", "Item No."], ["00XV 921", "VTA"]),
    (2, ["Manufacturer", "Model"], ["VTA", "VTA"]),
    (3, ["Service"], ["AGAS FR N2 BOOT LVL VLV"]),
    (4, ["Piping class"], ["1C0K8"]),
    (5, ["Operating Pressure", "Design Pressure"], ["", ""]),
    (6, ["Body Size", "Body Type"], ['2"', "Ball (Full Bore) - Floating"]),
    (7, ["Connections", "Rating"], ["Flanged RF (ASME B16.5)", "150#"]),
    (8, ["Body material"], ["316/316L SS A351-CF8M/CF3M"]),
    (9, ["Seat Material", "Seal Material"], ["RTFE", "Graphite (VTA)"]),
    (10, ["Bolting / Gasket"], ["Note-1"]),
    (11, ["Packing Type"], ["General note - 8"]),
    (12, ["Manufacturer", "Model No."], ["Bettis", "G-01"]),
]
X_NUM, X_L1, X_L2, X_V, X_MID, X_R = 122, 136, 222, 313, 438, 572


def _sheet(doc, rev, sheet, of, tag_rows, notes=None, values=None):
    pg = doc.new_page(width=595, height=842)
    pg.insert_text((400, 110), "ON / OFF VALVE", fontsize=14)
    pg.insert_text((420, 125), "00-09-IN-DTS-00003", fontsize=8)
    pg.insert_text((410, 140), f"SHEET {sheet} OF {of}", fontsize=8)
    pg.insert_text((410, 150), "REV.", fontsize=8)
    pg.insert_text((470, 150), rev, fontsize=8)
    pg.insert_text((410, 160), "DATE", fontsize=8)
    pg.insert_text((470, 160), "19/9/2026", fontsize=8)
    y = 200
    caption_top = y
    for no, labels, vals in tag_rows:
        if values and no in values:
            vals = values[no]
        pg.draw_rect(pymupdf.Rect(43, y, X_R, y + 12), width=0.5)
        xs = [X_NUM, X_L1, X_V, X_R] + ([X_L2, X_MID] if len(labels) == 2 else [])
        for x in xs:
            pg.draw_line((x, y), (x, y + 12), width=0.5)
        pg.insert_text((X_NUM + 4, y + 9), str(no), fontsize=7)
        lx = [X_L1 + 3, X_L2 + 3]
        for i, lab in enumerate(labels):
            pg.insert_text((lx[i], y + 9), lab, fontsize=7)
        vx = [X_V + 3, X_MID + 3] if len(labels) == 2 else [X_V + 3]
        for i, v in enumerate(vals):
            if v:
                pg.insert_text((vx[i], y + 9), v, fontsize=7)
        y += 12
    # caption bands left of the numbers: the last row sits in its own ACTUATOR band, as on the real form
    split = y - 12 if len(tag_rows) > 4 else y
    for a in (caption_top, split, y):
        pg.draw_line((43, a), (X_NUM, a), width=0.5)
    pg.insert_text((50, (caption_top + split) / 2), "GENERAL" if sheet == 1 else "ACCESSORIES", fontsize=7)
    if split < y:
        pg.insert_text((50, split + 9), "ACTUATOR" if sheet == 1 else "ACCESSORIES", fontsize=7)
    if notes:
        pg.insert_text((57, y + 30), "NOTES :", fontsize=8)
        ny = y + 45
        for i, t in enumerate(notes, 1):
            pg.insert_text((49, ny), f"{i}. {t}", fontsize=7)
            ny += 12
    return pg


def make_pdf(rev="A", values=None) -> bytes:
    doc = pymupdf.open()
    _sheet(doc, rev, 1, 2, ROWS, values=values)
    acc = [(52 + i, ["Filter Regulator" if i == 0 else f"Tubing {i}"], ["NA"]) for i in range(9)]
    _sheet(doc, rev, 2, 2, acc, notes=[
        "Gasket material: FG-316 SS PERF TANG INSERT, CL150. Stud Bolt material: Continuous thread, CR-MO A193-B7.",
        "Position Transmitter with 24V DC."])
    return doc.tobytes()


@pytest.fixture()
def pdf_path(tmp_path):
    p = tmp_path / "ds.pdf"
    p.write_bytes(make_pdf())
    return p


def test_tag_normalisation_and_type():
    assert schema.norm_tag("00XV 921") == schema.norm_tag("00XV-921") == "00XV921"
    assert schema.valve_type("98ESDV -004") == "ESDV"
    assert schema.valve_type("315MOV980004") == "MOV"


def test_revision_order():
    assert sorted(["1", "A", "0", "B", "2"], key=store.rev_key) == ["A", "B", "0", "1", "2"]


def test_extract_fields_positions_notes(pdf_path):
    res = extract.read_pdf(str(pdf_path))
    dss = extract.group_datasheets(res)
    assert len(dss) == 1
    d = dss[0]
    assert d["tag_key"] == "00XV921" and d["rev"] == "A" and d["pages"] == [1, 2]
    f = d["fields"]
    assert f["body_size"]["value"] == '2"' and f["body_size"]["page"] == 1 and f["body_size"]["bbox"]
    assert f["rating"]["value"] == "150#"
    assert f["seat_material"]["value"] == "RTFE" and f["seal_material"]["value"] == "Graphite (VTA)"
    assert f["manufacturer"]["status"] == "placeholder"          # VTA is kept, flagged, not guessed
    assert f["op_pressure"]["status"] == "blank"                 # empty cell -> Not Found, never invented
    assert f["act_manufacturer"]["value"] == "Bettis"            # same label in a later group, no clash
    assert [n["no"] for n in d["notes"]] == [1, 2]
    assert f["bolting_gasket"]["ref"]["kind"] == "note" and "FG-316" in f["bolting_gasket"]["ref"]["text"]


def test_compare_revisions():
    def full(rev, values):
        p = io.BytesIO(make_pdf(rev, values))
        tmp = Path(os.environ.get("TMPDIR", "/tmp")) / f"valve_cmp_{rev}.pdf"
        tmp.write_bytes(p.getvalue())
        d = extract.group_datasheets(extract.read_pdf(str(tmp)))[0]
        return {"fields": [dict(v, key=k, edited_value=None) for k, v in d["fields"].items()], "notes": d["notes"]}
    a = full("A", None)
    b = full("B", {6: ['3"', "Ball (Full Bore) - Floating"], 9: ["PEEK", "Graphite (VTA)"]})
    rows = {r["key"]: r for r in api.compare(a, b)}
    assert rows["body_size"]["change"] == "Modified" and rows["body_size"]["new"] == '3"'
    assert rows["seat_material"]["change"] == "Modified"
    assert rows["rating"]["change"] == "Unchanged"
    assert rows["body_size"]["new_bbox"]                         # the screen can point at it


def _template() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "TBE Appendix-XV"
    ws["A1"] = "TBE APPENDIX FOR ON-OFF BALL VALVE (XVs - Pneumatic Actuators)"
    hdr = ["S. No.", "Tag Number", "Vendor", "Valve Body", None, None, None]
    sub = [None, None, "Supplier", "Mfr. / Model", "Piping Class", "Body Size", "Seat Material"]
    for c, v in enumerate(hdr, 1):
        ws.cell(2, c, v)
    for c, v in enumerate(sub, 1):
        ws.cell(4, c, v)
    ws.merge_cells("D2:G3")
    rows = [(1, "00XV921", "Requirement", "VTC", "1C0K8", '2"', "PTFE"), (None, None, "AMPO", None, None, None, None)]
    for r, vals in enumerate(rows, 5):
        for c, v in enumerate(vals, 1):
            ws.cell(r, c, v)
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


def test_valve_list_fill_keeps_format_and_marks_changes(pdf_path):
    d = extract.group_datasheets(extract.read_pdf(str(pdf_path)))[0]
    d["document_id"] = 1
    new = dict(d, tag="19XV 122", tag_key="19XV122")
    out, rep = tbe.build(_template(), [d, new], {1: "ds.pdf"})
    wb = openpyxl.load_workbook(io.BytesIO(out))
    ws = wb["TBE Appendix-XV"]
    assert rep["updated"] == ["00XV921"] and rep["new"] == ["19XV122"]
    seat = [c for c in rep["changes"] if c["column"] == "seat material"]
    assert seat and seat[0]["previous"] == "PTFE" and seat[0]["new"] == "RTFE"
    assert ws.cell(5, 7).value == "RTFE" and ws.cell(5, 7).comment and "Previous: PTFE" in ws.cell(5, 7).comment.text
    assert ws.cell(5, 4).value == "VTC"                         # 'VTA / VTA' says less than the list: kept
    assert "D2:G3" in [str(m) for m in ws.merged_cells.ranges]  # template structure untouched
    tags = [ws.cell(r, 2).value for r in range(5, ws.max_row + 1)]
    assert "19XV122" in tags                                     # new tag appended to the XV sheet
    assert "Datasheet Notes" in wb.sheetnames
    sup = [ws.cell(r, 3).value for r in range(5, ws.max_row + 1)]
    assert "AMPO" not in sup and sup == ["Requirement", "Requirement"]   # vendor rows dropped: one row per tag
    assert tags == ["00XV921", "19XV122"]
    keep = openpyxl.load_workbook(io.BytesIO(tbe.build(_template(), [d], {1: "ds.pdf"}, vendor_rows=True)[0]))["TBE Appendix-XV"]
    assert keep.cell(6, 3).value == "AMPO"                       # the option keeps them


def test_api_upload_review_and_export(tmp_path, monkeypatch, pdf_path):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(api.router)
    c = TestClient(app)
    H = {"X-Author": "%ED%85%8C%EC%8A%A4%ED%8A%B8"}
    pid = c.post("/api/valve/projects", json={"name": "CO2 PJT"}).json()["id"]
    j = c.post(f"/api/valve/projects/{pid}/upload", data={"kind": "datasheet"},
               files=[("files", ("ds.pdf", pdf_path.read_bytes(), "application/pdf"))], headers=H).json()
    for _ in range(100):
        if c.get(f"/api/valve/jobs/{j['id']}").json()["status"] == "done":
            break
        time.sleep(0.1)
    s = c.get(f"/api/valve/projects/{pid}/summary").json()
    assert s["kpi"]["tags"] == 1
    ds = c.get(f"/api/valve/datasheets/{s['tags'][0]['id']}").json()
    f = next(x for x in ds["fields"] if x["key"] == "body_size")
    ds2 = c.put(f"/api/valve/datasheets/{ds['id']}/fields/{f['id']}", json={"value": '3"'}, headers=H).json()
    g = next(x for x in ds2["fields"] if x["key"] == "body_size")
    assert g["value"] == '2"' and g["edited_value"] == '3"' and g["edited_by"] == "테스트"   # read value kept
    assert ds2["history"][0]["action"] == "edit"
    r = c.post(f"/api/valve/datasheets/{ds['id']}/comments", json={"text": "check", "page": 1, "bbox": [300, 300, 400, 320]},
               headers=H).json()
    assert r["comments"][0]["bbox"] == [300, 300, 400, 320]
    m = c.post("/api/valve/markup.pdf", json={"document_id": ds["document_id"], "pages": ds["pages"],
               "items": [{"page": 1, "bbox": [300, 300, 400, 320], "category": "comment", "text": "check"}]})
    assert m.status_code == 200 and len(list(pymupdf.open(stream=m.content, filetype="pdf")[0].annots())) == 1
    assert c.get(f"/api/valve/documents/{ds['document_id']}/page/1.png?zoom=1").status_code == 200
    x = c.get(f"/api/valve/projects/{pid}/valvelist.xlsx")
    assert x.status_code == 200 and "Valve List (tool format)" in openpyxl.load_workbook(io.BytesIO(x.content)).sheetnames


@pytest.mark.skipif(not os.environ.get("VALVE_SAMPLES"), reason="client sample files are not in the repository")
def test_real_datasheet_sample():
    """VALVE_SAMPLES=<folder>/Datasheet.pdf (CO2 PJT, 456 pages): 164 datasheets, notes on every one."""
    res = extract.read_pdf(str(Path(os.environ["VALVE_SAMPLES"]) / "Datasheet.pdf"))
    dss = extract.group_datasheets(res)
    assert len(dss) == 164
    assert all(d["notes"] for d in dss)
    review = sum(1 for d in dss for f in d["fields"].values() if f["status"] == "review")
    assert review <= 80


# ── material equivalence · PMS · issues · contractor exports (round 2) ─────────────────────────

from app.valve import exports, issues, material, pms  # noqa: E402


@pytest.mark.parametrize("req, ds, want", [
    ("ASTM A351 CF8M", "316/316L SS A351-CF8M/CF3M", material.COMPLIANT),     # user report 2026-10-31
    ("316 SS / HF", "SS 316/HF", material.COMPLIANT),                          # user report 2026-10-31
    ("SS 316/HF", "316 SS / HF", material.COMPLIANT),
    ("CS A216-WCB", "Carbon Steel ASTM A216 Grade WCB", material.COMPLIANT),
    ("RTFE", "RTFE ST", material.COMPLIANT),
    ("ASTM A351 CF8M", "Carbon Steel ASTM A216 Grade WCB", material.NON),
    ("RTFE", "PEEK", material.NON),
    ("316/316L SS A351-CF8M/CF3M", "ASTM A351 CF8M", material.COMPLIANT),     # the other direction, same material
    ("ASTM A351 CF8M", "A182 F316", material.REVIEW),                          # same family: engineer decides
    ("316 SS/HF", "SS 316", material.REVIEW),                                  # hard-facing not stated
    ("316 SS / HF", "VTA", material.REVIEW),
])
def test_material_compare(req, ds, want):
    assert material.compare(req, ds)[0] == want


def _pms_pdf(path):
    doc = pymupdf.open()
    pg = doc.new_page(width=595, height=842)
    pg.insert_text((10, 40), "PIPING MATERIAL SPECIFICATION - QN AND W15 AREA", fontsize=8)
    pg.insert_textbox(pymupdf.Rect(10, 60, 400, 200), "Class: 1C0K8\nClass 150, 316/316L, SS, RF, NACE\n"
                      "NACE Requirement: MR0175/ISO 15156\nFlange Class: CLASS 150\nMaterial: STAINLESS STEEL\n"
                      "Valve Trim: TRIM 12 (316 SS/HF)", fontsize=7)
    pg.insert_textbox(pymupdf.Rect(10, 300, 470, 360), "PVBSED15RF02TD08U703\n0.5\n-\n2\nBALL VALVE, 316/316L SS "
                      "A351-CF8M/CF3M, CL150, RF, B16.10, FLOATING, FULL PORT, 316 SS BALL/STEM, RTFE ST, FIRE TESTED TO "
                      "API 607, NACE MR0175/ISO 15156", fontsize=6)
    doc.save(str(path))


def test_pms_read_and_check(tmp_path):
    p = tmp_path / "pms.pdf"
    _pms_pdf(p)
    P = pms.read_pms(str(p))
    c = P["areas"]["QN"]["1C0K8"]
    assert c["rating"] == 150 and "316 SS/HF" in c["trim"] and c["items"][0]["to"] == 2.0
    F = {k: {"value": v, "page": 1, "bbox": [0, 0, 1, 1]} for k, v in {
        "piping_class": "1C0K8", "body_size": '2"', "body_type": "Ball (Full Bore) - Floating", "rating": "150#",
        "nace": "Yes", "body_material": "ASTM A351 CF8M", "ball_material": "SS 316/HF", "stem_material": "316 SS / HF",
        "seat_material": "PEEK"}.items()}
    rows = {r["item"]: r for r in pms.check(F, P, "QN")}
    assert rows["Pressure Class"]["result"] == material.COMPLIANT
    assert rows["Body Material"]["result"] == material.COMPLIANT          # CF8M inside CF8M/CF3M
    assert rows["Trim (Ball) Material"]["result"] == material.COMPLIANT   # notation only
    assert rows["Seat Material"]["result"] == material.NON and rows["Seat Material"]["pms_page"] == 1
    F["rating"]["value"] = "300#"
    assert {r["item"]: r for r in pms.check(F, P, "QN")}["Pressure Class"]["result"] == material.NON


def _ds_for_issues():
    fields = [
        {"key": "tag", "value": "00XV 921", "page": 1, "bbox": [1, 1, 2, 2], "row": 1, "display": "Tag"},
        {"key": "line_no", "value": 'PW2409631-2"(1C0K8)-N', "page": 1, "bbox": [1, 3, 2, 4], "row": 5, "display": "Line No."},
        {"key": "piping_class", "value": "1C3AS1", "page": 1, "bbox": [1, 5, 2, 6], "row": 9, "display": "Piping class"},
        {"key": "body_size", "value": "", "page": 1, "bbox": [1, 7, 2, 8], "row": 21, "display": "Valve Size"},
        {"key": "rating", "value": "HOLD", "page": 1, "bbox": [1, 9, 2, 10], "row": 22, "display": "Rating"},
        {"key": "elec_connection", "value": "M20 (General Note-46)", "page": 1, "bbox": [1, 11, 2, 12], "row": 49,
         "display": "Electrical Connection"},
        {"key": "raw.13", "value": "Liquid", "page": 1, "bbox": [1, 13, 2, 14], "row": 13, "status": "review", "display": "Row 13"},
    ]
    return {"fields": [dict(f, edited_value=None, status=f.get("status", "ok")) for f in fields], "notes": [],
            "pages": [1, 2], "sheets": [[1, 1, 2], [2, 2, 2]], "doc_no": "00-09-IN-DTS-00003", "comments": []}


def test_issues_rules():
    got = issues.compute(_ds_for_issues(), {str(n): "x" for n in range(1, 20)})
    t = {(i["type"], i["key"]) for i in got}
    assert ("Data Missing", "body_size") in t
    assert ("Open Item", "rating") in t
    assert ("Data Error", "piping_class") in t                           # (1C0K8) in Line No. vs 1C3AS1
    assert ("Data Error", "elec_connection") in t                        # General Note 46 not in the document
    assert ("Extraction Review", "raw.13") in t
    ext = next(i for i in got if i["type"] == "Extraction Review")
    assert ext["no"] == len(got)                                         # internal checks numbered last
    assert all(i["sheet"] == 1 and i["of"] == 2 for i in got)


def test_contractor_exports(tmp_path):
    src = tmp_path / "ds.pdf"
    src.write_bytes(make_pdf())
    rows = [dict(i, ds_id=7, tag="00XV921", doc_no="00-09-IN-DTS-00003", rev="A", document_id=3, filename="ds.pdf",
                 valve_type="XV") for i in issues.compute(_ds_for_issues(), {str(n): "x" for n in range(1, 20)})
            if i["type"] != "Extraction Review"]
    x = exports.issues_xlsx(rows, "http://pc:8000", "CO2 PJT", "tester", ["ds.pdf"])
    ws = openpyxl.load_workbook(io.BytesIO(x))["Issue List"]
    head = [c.value for c in ws[1]]
    for h in ("Tag Number", "Doc. No.", "Rev.", "Sheet", "PDF Page", "Issue Type", "Description", "Required / Expected"):
        assert h in head
    assert ws.cell(2, head.index("Sheet") + 1).value == "1 of 2"
    assert "ds=7" in ws.cell(2, head.index("Open in Tool") + 1).hyperlink.target
    pdf = pymupdf.open(stream=exports.markup_pdf([{"path": str(src), "pages": [1, 2], "tag": "00XV921", "doc_no": "D",
                                                   "rev": "A", "filename": "ds.pdf", "issues": rows}], "CO2 PJT"), filetype="pdf")
    flags = [a.flags for p in pdf for a in p.annots()]
    assert flags and all(f & pymupdf.PDF_ANNOT_IS_PRINT for f in flags)   # mark-ups print with the page
    assert pdf.page_count == 3                                           # 2 datasheet pages + Issue Summary


# ── valve03: notes · process reference · equivalence · odd pages · reviewer mark-ups ──────────────────────

def test_note_helpers():
    notes = [{"no": 8, "text": "Bolting /Nut: A193 B8M / A194 8M", "page": 2, "bbox": [1, 1, 2, 2]},
             {"no": 9, "text": "Body / Bonnet: 316/316L SS dual certified", "page": 2, "bbox": [1, 3, 2, 4]}]
    w = extract.wrong_note("Body/Bonnet Material", notes[0], notes)          # Note 8 is about bolting, Note 9 about body
    assert w and w["no"] == 9
    assert extract.wrong_note("Bolting", notes[0], notes) is None
    assert extract.note_value(notes[1]["text"]) == "316/316L SS dual certified"
    assert extract.note_value("Body material shall be 316/316L SS") == "316/316L SS"
    assert extract.note_value("Actuator Type: Motorized, multi-turn") == "Motorized, multi-turn"
    assert extract.note_value("x " * 120) == ""                              # long paragraph: stays a reference
    assert extract.pure_reference("General Note - 3") and not extract.pure_reference("316 SS (Note 3)")
    ref = extract.process_reference([{"no": 4, "text": "For Process data please refer to Doc.No.: 03-02-PR-DTS-00002"}], {})
    assert ref and ref["where"] == "Note 4" and "PR-DTS" in ref["doc"]
    assert extract.process_reference([{"no": 1, "text": "Painting as per spec"}], {}) is None


def test_blank_process_data_always_flagged():
    """User request 2026-10-31: every blank PROCESS DATA item is marked, also when the sheet refers to a Process DS."""
    ds = _ds_for_issues()
    ds["fields"] += [dict(key=k, value="", edited_value=None, status="blank", page=1, bbox=[1, 15 + n, 2, 16 + n], row=12 + n,
                          display=d, section=sec) for n, (k, d, sec) in enumerate([("fluid", "Fluid", "process"), ("corrosive", "Corrosive", "special"),
                          ("max_dp_closed", "Max. Diff. Pressure", "process"), ("flow.max", "Flow Rate (Max)", "process"),
                          ("flow.nor", "Flow Rate (Nor)", "process"), ("flow.min", "Flow Rate (Min)", "process")])]
    miss = {i["key"]: i for i in issues.compute(ds, {}) if i["type"] == "Data Missing"}
    assert {"fluid", "corrosive", "max_dp_closed", "flow"} <= set(miss)              # Max/Nor/Min counted once
    ds["process_ref"] = {"doc": "03-02-PR-DTS-00002", "where": "Note 4"}
    rows = [{"ds_key": "fluid", "pd": "SOUR WATER", "pd_unit": "", "result": "Referenced"}]
    miss = {i["key"]: i for i in issues.compute(ds, {}, process_rows=rows) if i["type"] == "Data Missing"}
    assert "fluid" in miss and "03-02-PR-DTS-00002" in miss["fluid"]["description"] and miss["fluid"]["expected"] == "SOUR WATER"
    assert miss["fluid"]["bbox"] and miss["fluid"]["severity"] == "Major"
    ds["fields"][-2]["value"] = "10"                                              # one case given -> the parameter is not missing
    assert "flow" not in {i["key"] for i in issues.compute(ds, {}) if i["type"] == "Data Missing"}


@pytest.mark.parametrize("a, b, want", [
    ("Yes", "Yes (MR0175/ISO 15156)", True),
    ("Flanged, RTJ", "Flanged RTJ (ASME B16.5)", True),
    ("1C3AS2", "1C3AS2-A", False),                                           # short qualifier changes the meaning
    ("316 SS", "316L SS", False),
    ("316 SS / HF", "SS 316/HF", True),
])
def test_material_equivalent(a, b, want):
    assert material.equivalent(a, b) is want


def test_pms_item_layouts():
    a = pms.parse_item("PBVF1A2B3C4\n0.5 - 1.5\nBALL VALVE, FULL BORE, A182 F316")
    assert a and (a["from"], a["to"]) == (0.5, 1.5) and a["kind"] == "BALL VALVE"
    b = pms.parse_item("PBVF1A2B3C5\n2 - 24 / 0.5 - 1\nBALL VALVE, REDUCED BORE")
    assert b and b["branch"] == [0.5, 1.0]
    assert pms.parse_item("not a code\n1\nX") is None


def test_odd_pages_read_like_a4(tmp_path):
    src = pymupdf.open(stream=make_pdf(), filetype="pdf")
    a3 = pymupdf.open()                                                       # same sheet printed on A3
    for p in src:
        q = a3.new_page(width=p.rect.width * 1.414, height=p.rect.height * 1.414)
        q.show_pdf_page(q.rect, src, p.number)
    path = tmp_path / "a3.pdf"
    a3.save(path)
    base = tmp_path / "a4.pdf"
    base.write_bytes(make_pdf())
    f4 = extract.group_datasheets(extract.read_pdf(str(base)))[0]["fields"]
    f3 = extract.group_datasheets(extract.read_pdf(str(path)))[0]["fields"]
    assert {k: f["value"] for k, f in f3.items()} == {k: f["value"] for k, f in f4.items()}
    k = "body_size"
    assert abs(f3[k]["bbox"][0] - f4[k]["bbox"][0] * 1.414) < 2              # boxes stay on the A3 page
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF-1.4 garbage")
    with pytest.raises(extract.PdfError):
        extract.read_pdf(str(bad))


def test_reviewer_markups(tmp_path, monkeypatch, pdf_path):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(api.router)
    c = TestClient(app)
    pid = c.post("/api/valve/projects", json={"name": "CO2 PJT"}).json()["id"]
    j = c.post(f"/api/valve/projects/{pid}/upload", data={"kind": "datasheet"},
               files=[("files", ("ds.pdf", pdf_path.read_bytes(), "application/pdf"))]).json()
    for _ in range(100):
        if c.get(f"/api/valve/jobs/{j['id']}").json()["status"] == "done":
            break
        time.sleep(0.1)
    dsid = c.get(f"/api/valve/projects/{pid}/summary").json()["tags"][0]["id"]
    url = f"/api/valve/datasheets/{dsid}/comments"
    shapes = [{"kind": "cloud", "category": "error", "text": "Body material wrong", "bbox": [100, 100, 200, 140]},
              {"kind": "arrow", "category": "comment", "text": "see", "bbox": [50, 50, 90, 90], "points": [[50, 50], [90, 90]]},
              {"kind": "pen", "category": "missing", "text": "", "bbox": [10, 10, 40, 30],
               "points": [[[10, 10], [20, 30], [40, 12]]]},
              {"kind": "text", "category": "question", "text": "Torque?", "bbox": [300, 300, 420, 330]},
              {"kind": "note", "category": "comment", "text": "sticky", "bbox": [450, 300, 466, 316]},
              {"kind": "highlight", "category": "comment", "text": "", "bbox": [100, 400, 300, 412]},
              {"kind": "ellipse", "category": "comment", "text": "", "bbox": [100, 500, 160, 540]}]
    ids = [c.post(url, json=dict(s, page=1)).json()["new_comment_id"] for s in shapes]
    assert c.post(url, json={"kind": "star", "page": 1, "bbox": [1, 1, 2, 2]}).status_code == 400
    assert c.post(url, json={"kind": "pen", "page": 1, "bbox": [1, 1, 2, 2], "points": [[1, 1]]}).status_code == 400
    ds = c.put(f"/api/valve/comments/{ids[0]}", json={"bbox": [110, 110, 230, 160]}).json()   # moved / resized
    assert next(x for x in ds["comments"] if x["id"] == ids[0])["bbox"] == [110, 110, 230, 160]
    assert len(c.put(f"/api/valve/comments/{ids[6]}", json={"delete": True}).json()["comments"]) == 6
    ds = c.put(f"/api/valve/comments/{ids[6]}", json={"restore": True}).json()                 # undo of a delete
    assert len(ds["comments"]) == 7
    mi = {i["comment_id"]: i for i in ds["issues"] if i.get("comment_id")}
    assert mi[ids[0]]["type"] == "Data Error" and mi[ids[0]]["color"] == "error"
    assert mi[ids[2]]["type"] == "Data Missing" and mi[ids[2]]["points"] == shapes[2]["points"]
    assert mi[ids[3]]["type"] == "Reviewer Comment" and mi[ids[3]]["description"].startswith("Question")
    tag = ds["tag_key"]
    pdf = pymupdf.open(stream=c.get(f"/api/valve/projects/{pid}/markup.pdf?tag={tag}").content, filetype="pdf")
    kinds = {a.type[1] for p in pdf for a in p.annots()}
    assert {"Square", "Line", "Ink", "FreeText", "Text", "Highlight", "Circle"} <= kinds
    assert all(a.flags & pymupdf.PDF_ANNOT_IS_PRINT for p in pdf for a in p.annots())
    txt = [a.info["content"] for p in pdf for a in p.annots() if a.type[1] == "FreeText" and a.info["content"] == "Torque?"]
    assert txt                                                                # the text box prints the reviewer's words
    iss = next(i for i in ds["issues"] if not i.get("comment_id"))
    c.put(f"/api/valve/datasheets/{dsid}/issues/{iss['ikey']}", json={"status": "Dismissed", "note": "per spec"})
    fb = c.get(f"/api/valve/projects/{pid}/feedback.json").json()
    assert fb["kind"] == "valve-feedback" and fb["verdicts"][0]["verdict"] == "Dismissed"
    assert {m["category"] for m in fb["missed"]} == {"error", "missing"}       # what the rules did not raise
    import importlib.util
    spec = importlib.util.spec_from_file_location("valve_voc", Path(__file__).resolve().parents[1] / "spike" / "valve_voc.py")
    voc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(voc)
    _, sc = voc.score(fb)
    assert sc["precision"][iss["type"]]["false"] == 1 and sc["missed"] == {"error": 1, "missing": 1}


def test_reread_keeps_review(tmp_path, monkeypatch, pdf_path):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(api.router)
    c = TestClient(app)
    pid = c.post("/api/valve/projects", json={"name": "P"}).json()["id"]

    def wait(j):
        for _ in range(100):
            if c.get(f"/api/valve/jobs/{j['id']}").json()["status"] == "done":
                return
            time.sleep(0.1)
    wait(c.post(f"/api/valve/projects/{pid}/upload", data={"kind": "datasheet"},
                files=[("files", ("ds.pdf", pdf_path.read_bytes(), "application/pdf"))]).json())
    ds = c.get(f"/api/valve/datasheets/{c.get(f'/api/valve/projects/{pid}/summary').json()['tags'][0]['id']}").json()
    f = next(x for x in ds["fields"] if x["key"] == "body_size")
    c.put(f"/api/valve/datasheets/{ds['id']}/fields/{f['id']}", json={"value": '3"'})
    c.post(f"/api/valve/datasheets/{ds['id']}/comments", json={"kind": "cloud", "page": 1, "bbox": [1, 1, 50, 50], "text": "x"})
    wait(c.post(f"/api/valve/documents/{ds['document_id']}/retry").json())
    s = c.get(f"/api/valve/projects/{pid}/summary").json()
    assert s["kpi"]["datasheets"] == 1                                       # refreshed, not duplicated
    d2 = c.get(f"/api/valve/datasheets/{ds['id']}").json()
    g = next(x for x in d2["fields"] if x["key"] == "body_size")
    assert g["id"] == f["id"] and g["edited_value"] == '3"' and len(d2["comments"]) == 1


def test_judging_code_never_reads_feedback():
    """P&ID hotfix82 rule: the reviewers' answers score the tool; they must not steer it."""
    import ast
    root = Path(__file__).resolve().parents[1] / "app" / "valve"
    for name in ("extract", "schema", "material", "pms", "issues", "tbe"):
        tree = ast.parse((root / f"{name}.py").read_text(encoding="utf-8"))
        words = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | \
                {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        assert not any("feedback" in w or "verdict" in w or "issue_state" in w for w in words), name


# ── valve05: what a reviewer sees on the page (visual check of all 456 sample pages) ──────────────────────

def test_words_on_one_line_keep_their_order():
    # 'SWAGELOK' sits 0.9 pt lower than '(General Note - 7)' — a 3-pt bucket used to split them into two lines
    ws = [(315.8, 217.6, 355.6, 224.2, "SWAGELOK"), (362.5, 216.7, 394.5, 224.4, "(General"),
          (396.8, 216.7, 414.3, 224.4, "Note"), (416.6, 216.7, 419.3, 224.4, "-"), (421.6, 216.7, 428.9, 224.4, "7)")]
    assert extract._text(ws) == "SWAGELOK (General Note - 7)"
    two = ws + [(315.8, 226.0, 340.0, 233.0, "next")]
    assert extract._text(two).endswith(" next")


def test_colon_pairs_split_label_and_value():
    ws = [(81, 162, 94, 170, "Tag"), (97, 162, 112, 170, "No.:"), (116, 162, 143, 170, "98MOV"), (148, 162, 176, 170, "980001"),
          (330, 162, 369, 170, "Instrument"), (371, 162, 389, 170, "Type"), (391, 162, 394, 170, ":"),
          (395, 162, 418, 170, "Motor"), (420, 162, 457, 170, "Operated")]
    got = [(a, extract._text(b)) for a, b in extract._colon_pairs(ws)]
    assert got == [("Tag No.", "98MOV 980001"), ("Instrument Type", "Motor Operated")]


def test_hidden_text_is_not_read(tmp_path):
    doc = pymupdf.open()
    pg = doc.new_page()
    pg.insert_text((100, 100), "N/A or other", fontsize=8)              # an Excel drop-down remnant …
    pg.draw_rect(pymupdf.Rect(98, 90, 170, 103), color=None, fill=(1, 1, 1))   # … painted over afterwards
    pg.insert_text((100, 200), "Cell", fontsize=8)                       # shaded cell drawn BEFORE its text stays
    pg.draw_rect(pymupdf.Rect(300, 192, 340, 203), color=None, fill=(0.9, 0.9, 0.9))
    pg.insert_text((302, 200), "VTA", fontsize=8)
    pg.insert_text((100, 300), "visible", fontsize=8)
    words = extract._visible(pg.get_text("words"), extract._hidden_boxes(pg))
    assert [w[4] for w in words] == ["Cell", "VTA", "visible"]


def test_sheet_doc_number_and_repeated_header_checks():
    ds = _ds_for_issues()
    ds["sheet_doc_mismatch"] = [{"page": 2, "sheet": 2, "printed": "00-09-IN-DTS-0000"}]
    ds["fields"].append({"key": "line_no.4", "value": 'PW2409631-3"(1C0K8)-N', "edited_value": None, "page": 2,
                         "bbox": [1, 1, 2, 2], "row": 4, "display": "Line Number", "status": "ok"})
    got = issues.compute(ds, {str(n): "x" for n in range(1, 20)})
    d = [i["description"] for i in got if i["type"] == "Data Error"]
    assert any("prints Document No. '00-09-IN-DTS-0000'" in x for x in d)
    assert any("Line No." in x or "line_no" in x or "sheet 1 says" in x for x in d)


# ── valve07: Process Data verification (Phase 3) · revision comparison Excel ──────────────────────────────

def _process_pdf(path, tag="00XV-921", fail="FC", line='PW2409631-2"(1C0K8)-N', op_p="0.46", pid="98-98-PR-PID-00001"):
    """A ruled 'Process Data for On-Off Valve' table like Annexure 7: two header lines, a unit line, one tag row."""
    doc = pymupdf.open()
    pg = doc.new_page(width=1190, height=842)
    pg.insert_text((540, 60), "Process Data for On-Off Valve", fontsize=9)
    heads = [("Sr no.", ""), ("Tag Number", ""), ("PID No", ""), ("Line No", ""), ("Valve Size", ""), ("Pipe Class", ""), ("Service Fluid", ""),
             ("Process Fluid Phase", ""), ("Operating Pressure", "bar(g)"), ("Design Pressure", "bar(g)"), ("Operating Temperature", "°C"),
             ("Design Temperature", "°C"), ("Upstream/downstream max pressure difference for Closing", "bar"), ("Safety Position", ""),
             ("Required Tightness", "")]
    vals = ["1", tag, pid, line, '2"', "1C0K8", "SOUR WATER", "Vapor", op_p, "3.50", "47.27", "90", "4.5", fail, "TSO"]
    xs = [20, 60, 130, 220, 340, 390, 440, 520, 590, 650, 710, 780, 850, 980, 1040, 1120]
    for x in xs:
        pg.draw_line((x, 70), (x, 200), width=0.5)
    for y in (70, 110, 125, 140, 200):
        pg.draw_line((20, y), (1120, y), width=0.5)
    for (h, u), x0, x1 in zip(heads, xs, xs[1:]):
        words = h.split()
        half = (len(words) + 1) // 2
        pg.insert_text((x0 + 2, 85), " ".join(words[:half]), fontsize=5.5)
        if words[half:]:
            pg.insert_text((x0 + 2, 100), " ".join(words[half:]), fontsize=5.5)
        if u:
            pg.insert_text((x0 + 2, 120), u, fontsize=5.5)
    for v, x0 in zip(vals, xs):
        pg.insert_text((x0 + 2, 160), v, fontsize=5.5)
    doc.save(str(path))


def test_process_read_and_check(tmp_path):
    from app.valve import process as pr
    p = tmp_path / "pd.pdf"
    _process_pdf(p)
    pd = pr.read_process_data(str(p))
    assert pd["n_tags"] == 1 and "00XV921" in pd["by_tag"]
    row = pd["by_tag"]["00XV921"]
    assert row["values"]["op_pressure"]["v"] == "0.46" and row["values"]["op_pressure"]["unit"] == "bar(g)"
    assert row["values"]["dp_close"]["v"] == "4.5" and row["values"]["fail_position"]["v"] == "FC"
    # comparison rules
    assert pr.compare_item("op_pressure", "0.46", "bar-g", "0.46", "bar(g)")[0] == pr.MATCH
    assert pr.compare_item("op_pressure", "0.46", "bar", "0.46", "bar(g)")[0] == pr.REVIEW         # basis not written
    assert pr.compare_item("op_pressure", "6.7", "psig", "0.46", "bar(g)")[0] == pr.MATCH         # 6.7 psig = 0.462 bar(g)
    assert pr.compare_item("op_pressure", "1.5", "bar-a", "0.46", "bar(g)")[0] == pr.REVIEW       # different basis
    assert pr.compare_item("dp_close", "65", "psi", "4.5", "bar")[0] == pr.MATCH                   # differential: dimension only
    assert pr.compare_item("op_temp", "117", "°F", "47.27", "°C")[0] == pr.MATCH
    assert pr.compare_item("design_temp", "95", "ºC", "90", "°C")[0] == pr.MISMATCH
    assert pr.compare_item("fail_position", "Close", "", "FC", "")[0] == pr.MATCH
    assert pr.compare_item("fail_position", "Close", "", "FO", "")[0] == pr.MISMATCH
    assert pr.compare_item("tightness", "Tight Shut-Off", "", "TSO", "")[0] == pr.MATCH
    assert pr.compare_item("fluid_state", "Gas", "", "Vapor", "")[0] == pr.MATCH
    assert pr.compare_item("pid_no", "98-98-PR-PID-00013", "", "98-98-PR-PID-00012 98- 98-PR-PID-00013", "")[0] == pr.MATCH
    assert pr.compare_item("line_no", 'AG2440-24"(1C3AS1-QG1)-E', "", 'AG2440-24"(1C3AS1)-E', "")[0] == pr.REVIEW
    assert pr.compare_item("line_no", 'PW1-2"(1C0K8)-N', "", 'PW2-2"(1C0K8)-N', "")[0] == pr.MISMATCH
    assert pr.compare_item("flow", "10", "m3/h", "-", "m3/h")[0] == pr.NOT_IN_PD
    # whole datasheet: blank process fields with a Process DS reference are 'Referenced', not blank
    ds = {"tag_key": "00XV921", "tag": "00XV 921", "process_ref": {"where": "Note 4"},
          "fields": [{"key": "op_pressure", "value": "", "edited_value": None, "unit": "bar-g", "page": 1, "bbox": [1, 1, 2, 2]},
                     {"key": "fail_position", "value": "Open", "edited_value": None, "unit": "", "page": 1, "bbox": [1, 1, 2, 2]}]}
    rows = {r["key"]: r for r in pr.check(ds, pd)}
    assert rows["op_pressure"]["result"] == pr.REFERENCED and rows["fail_position"]["result"] == pr.MISMATCH
    assert pr.check({"tag_key": "ZZ1", "tag": "ZZ1", "fields": []}, pd)[0]["result"] == pr.NOT_IN_PD


def test_process_api_and_revision_excel(tmp_path, monkeypatch, pdf_path):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(api.router)
    c = TestClient(app)
    pid = c.post("/api/valve/projects", json={"name": "P"}).json()["id"]

    def up(kind, name, data):
        j = c.post(f"/api/valve/projects/{pid}/upload", data={"kind": kind}, files=[("files", (name, data, "application/pdf"))]).json()
        for _ in range(100):
            if c.get(f"/api/valve/jobs/{j['id']}").json()["status"] == "done":
                return
            time.sleep(0.1)
    up("datasheet", "dsA.pdf", pdf_path.read_bytes())
    up("datasheet", "dsB.pdf", make_pdf(rev="B", values={5: ["10 bar-g", "16 bar-g"], 6: ['3"', "Ball (Full Bore) - Floating"]}))
    pp = tmp_path / "pd.pdf"
    _process_pdf(pp, op_p="0.46")                                          # Rev B datasheet says 10 bar-g
    up("process", "pd.pdf", pp.read_bytes())
    s = c.get(f"/api/valve/projects/{pid}/summary").json()
    assert s["has_process"] and s["kpi"]["process_mismatch"] >= 1
    r = c.get(f"/api/valve/projects/{pid}/process").json()
    assert r["process_doc"]["tags"] == 1 and any(x["result"] == "Mismatch" and x["key"] == "op_pressure" for x in r["rows"])
    ds = c.get(f"/api/valve/datasheets/{s['tags'][0]['id']}").json()
    assert ds["process_doc"] and any(i["type"] == "Process Mismatch" for i in ds["issues"])
    x = c.get(f"/api/valve/projects/{pid}/revisions.xlsx")
    assert x.status_code == 200 and int(x.headers["X-Count"]) >= 1
    ws = openpyxl.load_workbook(io.BytesIO(x.content))["Revision Changes"]
    assert [c.value for c in ws[1]][:4] == ["Tag Number", "Doc. No.", "Previous Rev.", "New Rev."] and ws.max_row >= 2


def test_hold_anywhere_is_flagged():
    """User request 2026-10-31: every HOLD / TBC must be commented so it gets released and a value given."""
    ds = _ds_for_issues()
    ds["fields"] += [dict(key=k, value=v, edited_value=None, status="ok", page=1, bbox=[1, 20 + n, 2, 21 + n], row=30 + n, display=d)
                     for n, (k, v, d) in enumerate([("area_class", "HOLD", "Area Classification"),
                                                   ("fire_safe", "HOLD (in accordance with API 607/ API 6FA)", "Fire Safe"),
                                                   ("sov_tag", "Note-9, Hold-1", "Solenoid Tag"), ("typical", "TBC", "Typical Detail"),
                                                   ("painting", "Holding paint system", "Painting")])]
    ds["notes"] = [{"no": 8, "text": "VTA - Vendor to Advise, TBC - To be Confirmed, NA - Not Applicable.", "page": 2, "bbox": [1, 1, 2, 2]},
                   {"no": 9, "text": "Partial Stroke Test: TBC based on SIL verification.", "page": 2, "bbox": [1, 3, 2, 4]},
                   {"no": 1, "text": "Typical representation is on hold.", "page": 2, "bbox": [1, 5, 2, 6], "section": "HOLD"}]
    got = {i["key"]: i for i in issues.compute(ds, {}) if i["type"] == "Open Item"}
    assert {"area_class", "fire_safe", "sov_tag", "typical", "rating", "note.9", "note.hold.1"} <= set(got)
    assert "painting" not in got and "note.8" not in got                       # 'Holding' is a word · the legend only defines TBC
    assert "HOLD 1: Typical representation" in got["sov_tag"]["description"]  # 'Hold-1' points at the HOLD list
    assert all(i["severity"] == "Major" and i["color"] == "missing" for i in got.values())


def _pms_pdf_v10(path):
    """Class sheet like 98-98-PI-SPC-00001: header trim 13CR (gate/globe), ball item 316 SS BALL/STEM, P-T table, notes."""
    doc = pymupdf.open()
    pg = doc.new_page(width=595, height=842)
    pg.insert_text((10, 40), "PIPING MATERIAL SPECIFICATION - QN AND W15 AREA", fontsize=8)
    pg.insert_textbox(pymupdf.Rect(10, 50, 300, 560), "Class:\n1C3AS2\nClass 150, Killed CS, RF, 3.0mm C.A, NACE\n"
                      "Corrosion Allowance: 3 MM\nNACE Requirement: MR0175/ISO 15156\nFlange Class: CLASS 150\n"
                      "Material: CARBON STEEL\nValve Trim: TRIM 8 (13CR/HF)\nTemperature / Pressure Limits\nASME B16.5, Group: 1.1\n"
                      "Temperature\n(DegC)\nPressure\n(BARG)\n38\n19.6\n93\n17.9\n149\n15.8\n204\n13.7\n260\n11.7\n"
                      "Service:\nCarbon Dioxide\nHydrocarbon\nDefault Schedule Table\nGeneral Class Notes\n002\n"
                      "ALL MATERIALS SHALL COMPLY WITH NACE MR 0175 / ISO-15156\n018\n"
                      "THE USE OF RPTFE SOFT SEATED MATERIALS IS RESTRICTED TO MAX. TEMPERATURE OF 230°C\n034\n"
                      "ALL SS 316/SS316L SHALL BE DUAL GRADE CERTIFIED\nItem Specific Notes\n030\nFOR FULL PORT VALVES\nPrinted: x",
                      fontsize=6)
    pg.insert_textbox(pymupdf.Rect(310, 300, 590, 360), "PVBSED15RF02TD08U709\n0.5\n-\n2\nBALL VALVE, CS A216-WCB, CL150, RF, "
                      "FLOATING, FULL PORT, 316 SS BALL/STEM, RTFE ST, FIRE TESTED TO API 607, NACE MR0175/ISO 15156", fontsize=6)
    doc.save(str(path))


def test_pms_ball_item_trim_governs_and_header_lists(tmp_path):
    p = tmp_path / "pms.pdf"
    _pms_pdf_v10(p)
    c = pms.read_pms(str(p))["areas"]["QN"]["1C3AS2"]
    assert c["pt"][0] == (38.0, 19.6) and c["pt"][-1] == (260.0, 11.7) and "Carbon Dioxide" in c["services"]
    assert "230" in c["class_notes"]["018"] and "DUAL GRADE" in c["class_notes"]["034"] and "030" in c["item_notes"]
    F = {k: {"value": v, "page": 1, "bbox": [0, 0, 1, 1]} for k, v in {
        "piping_class": "1C3AS2", "body_size": '2"', "body_type": "Ball (Full Bore)", "rating": "150#", "nace": "Yes",
        "body_material": "CS A216-WCB", "ball_material": "316 SS/HF", "stem_material": "316 SS/HF", "seat_material": "RTFE"}.items()}
    rows = {r["item"]: r for r in pms.check(F, {"areas": {"QN": {"1C3AS2": c}}}, "QN")}
    # header says 13CR (gate/globe trim) but the ball valve item says 316 SS BALL/STEM — the item governs
    assert rows["Trim (Ball) Material"]["result"] == material.COMPLIANT and "PMS item" in rows["Trim (Ball) Material"]["reason"]
    assert rows["Stem Material"]["req"] == "316 SS"


def test_material_review_rules(tmp_path):
    from app.valve import matreview
    p = tmp_path / "pms.pdf"
    _pms_pdf_v10(p)
    c = pms.read_pms(str(p))["areas"]["QN"]["1C3AS2"]
    f = lambda k, v, row: {"key": k, "value": v, "edited_value": None, "page": 1, "bbox": [1, row, 2, row + 1], "row": row, "display": k}  # noqa: E731
    ds = {"fields": [f("body_material", "CS A216-WCB", 24), f("ball_material", "316 SS/HF", 25), f("stem_material", "ASTM A564 Type 630", 27),
                     f("seat_material", "RTFE", 26), f("pipe_material", "ITCS A333-6", 11), f("nace", "Yes", 30), f("fire_safe", "Yes API 607", 31),
                     f("bolting_gasket", "Note-1", 28)],
          "notes": [{"no": 1, "text": "Stud Bolt material: Continuous thread, CR-MO A193-B7, W/ 2 HVY HEX NUTS, A194-2H", "page": 2, "bbox": None}]}
    proc = [{"key": "design_temp", "pd": "260", "pd_unit": "°C", "pd_page": 5, "pd_bbox": [0, 0, 1, 1]},
            {"key": "design_pressure", "pd": "15", "pd_unit": "bar(g)", "pd_page": 5, "pd_bbox": None},
            {"key": "fluid", "pd": "AMINE", "pd_unit": "", "pd_page": 5, "pd_bbox": None}]
    got = {m["rule"]: m for m in matreview.review(ds, {"20": "Elastomers shall prevent rapid gas decompression."}, c, proc)}
    assert got["MR-01"]["level"] == "Action" and "230" in got["MR-01"]["comment"]          # PMS note 018 vs Process 260 °C
    assert got["MR-03"]["level"] == "Action" and "11.7" in got["MR-03"]["comment"]          # 15 barg > 11.7 barg at 260 °C
    assert got["MR-04"]["level"] == "Action"                                                # WCB body in an LTCS (A333) line
    assert got["MR-08"]["level"] == "Confirm" and "H1150D" in got["MR-08"]["comment"]       # 17-4PH stem, NACE, no H1150D
    assert got["MR-11"]["level"] == "Confirm"                                               # B7 (not B7M) with NACE
    assert got["MR-14"]["level"] == "Confirm"                                               # AMINE not in the class service list
    assert {"MR-09", "MR-13", "MR-15"} <= set(got)
    for m in got.values():                                                                  # every finding cites its basis and evidence
        assert m["basis"] and m["evidence"]
    # no values → no opinion
    assert matreview.review({"fields": [f("body_material", "", 24)], "notes": []}) == []
    iss = issues.compute({"fields": ds["fields"], "notes": ds["notes"], "pages": [1]}, {}, material_rows=list(got.values()))
    mi = [i for i in iss if i["type"] == "Material Review"]
    assert {i["severity"] for i in mi} == {"Major", "Minor"} and not any(i["rule"] in ("MR-09", "MR-13", "MR-15") for i in mi)
