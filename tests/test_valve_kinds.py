"""valve37 — Globe · Butterfly · PSV datasheets (forms 101 · 701 · Code 80 with a bottom title block).

Synthetic pages that copy the layouts of the client samples (no client file in the repository).  With
VALVE_KIND_SAMPLES=<folder> holding globe_cv.pdf · bfv_cv.pdf · bfv_onoff.pdf · psv.pdf the real samples are read too.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pymupdf
import pytest

from app.valve import api, extract, forms_ext, schema

BLACK = (0, 0, 0)


def _ul(pg, a, b, y):                                       # a value underline (thin filled rectangle), as on Form 701
    pg.draw_rect(pymupdf.Rect(a, y + 2.2, b, y + 2.8), color=BLACK, fill=BLACK, width=0)


# ── Form 701 (PSV) ─────────────────────────────────────────────────────────────────────────────────────────

S1, S2, S3 = (224, 301), (352, 428), (458, 571)
W1, W2, W3 = (196, 301), (324, 428), (450, 555)
PSV_ROWS = [  # (label, [(sub or None, value, bold, x) ...], underlines)
    ("Tag No.", [(None, "98PRV 980001A", 1, 240)], [(196, 370)]),
    ("Service", [(None, "RELIEF GAS FR K-1", 1, 240)], [(196, 560)]),
    ("P&ID No./Line No./Equipment No.", [(None, "00-00-PR-PID-00001", 1, 200), (None, "/", 0, 310), (None, 'L100-6"(A1)', 1, 330),
                                         (None, "/", 0, 440), (None, "-", 1, 500)], [W1, W2, W3]),
    ("Service Class", [("Inlet", "YC0KL", 1, 240), ("Outlet", "YC0KL-N", 1, 370)], [S1, S2]),
    ("Quantity Tags", [(None, "1 No.", 1, 250)], [(196, 370)]),
    ("Code & Standard", [(None, "API 520, 526 & ASME SEC VIII", 1, 210)], [(196, 370)]),
    ("Type", [(None, "Conventional", 1, 250)], [(196, 370)]),
    ("Seat", [("Type", "Soft Seat", 1, 244), ("Tightness", "As per API 527", 1, 360)], []),   # no underlines on this row
    ("Inlet", [("Size", '3"', 1, 258), ("Rating", "600#", 1, 378), ("Type", "RF Flange", 1, 497)], [S1, S2, S3]),
    ("Outlet", [("Size", '4"', 1, 258), ("Rating", "150#", 1, 378), ("Type", "RF Flange", 1, 497)], []),
    ("Body / Bonnet / Seat (Nozzle)", [(None, "A216-WCB", 1, 220), (None, "A216-WCB", 1, 345), (None, "316 SS", 1, 480)], [W1, W2, W3]),
    ("Adjusting Rings / Spring / Bellows", [(None, "VTA", 1, 240), (None, "Carbon Steel", 1, 337), (None, "N/A", 1, 494)], []),
    ("Fluid / Phase", [(None, "Flare gas", 1, 220), (None, "Gas", 1, 360)], [W1, W2]),
    ("Set Pressure", [(None, "45", 1, 240), (None, "bar-g", 1, 365)], [W1, W2]),
    ("Operating Pressure", [(None, "bar-g", 1, 365)], [W1, W2]),
    ("Max. Relieving Flow Rate", [(None, "12000", 1, 240), (None, "kg/h", 1, 365)], [W1, W2]),
    ("Design Pressure", [(None, "50", 1, 240)], [W1, W2, W3]),
    ("Calculated Area", [(None, "1.20", 1, 240)], [W1]),
    ("Selected Area", [(None, "1.29", 1, 240)], [W1]),
    ("Orifice Designation", [(None, "J", 1, 255)], [(196, 370)]),
    ("Cap / Lifting Lever / Test Gag", [(None, "Screwed", 1, 220), (None, "Not Required", 1, 345), (None, "Not Required", 1, 480)], [W1, W2, W3]),
    ("Manufacturer", [(None, "VTA", 1, 255)], [(196, 370)]),
]


def _psv_page(doc, sheet=1, of=2, tag="98PRV 980001A"):
    pg = doc.new_page(width=595, height=842)
    pg.insert_text((45, 70), "Form No : 701", fontsize=9)
    pg.insert_text((240, 125), "Pressure Relief Valve", fontsize=15, fontname="hebo")
    pg.insert_text((450, 120), "DOCUMENT NO.", fontsize=8)
    pg.insert_text((470, 140), tag, fontsize=9, fontname="hebo")
    pg.insert_text((450, 190), f"SHEET {sheet} OF {of}", fontsize=8)
    pg.insert_text((450, 210), "REV.", fontsize=8)
    pg.insert_text((520, 210), "A", fontsize=8)
    return pg


def make_psv_pdf() -> bytes:
    doc = pymupdf.open()
    pg = _psv_page(doc)
    y0, p = 260, 11.25
    y_end = y0 + p * len(PSV_ROWS) + 4
    for x in (43, 61.5, 77.2, 186.8, 573):
        pg.draw_line((x, y0 - 4), (x, y_end), width=0.75)
    for i, ch in enumerate("TAG"):                           # vertical caption letters left of the labels
        pg.insert_text((64, y0 + 4 + i * 4.5), ch, fontsize=4.5)
    for i, (lab, vals, uls) in enumerate(PSV_ROWS):
        y = y0 + i * p + 8
        pg.insert_text((50 if i < 9 else 46, y), str(i + 1), fontsize=8)
        pg.insert_text((81, y), lab, fontsize=8)
        for sub, v, bold, x in vals:
            if sub:
                sx = {S1[0]: 196, S2[0]: 324, S3[0]: 434}
                sxx = min(sx.values(), key=lambda a: abs(a - x + 40))
                pg.insert_text((sxx, y), sub, fontsize=5.5)
            pg.insert_text((x, y), v, fontsize=8, fontname="hebo" if bold else "helv")
        for a, b in uls:
            _ul(pg, a, b, y)
    pg2 = _psv_page(doc, 2, 2)
    pg2.insert_text((150, 300), "Tag No.", fontsize=8)
    pg2.insert_text((300, 300), "98PRV 980001A", fontsize=8, fontname="hebo")
    pg2.insert_text((45, 320), "Individual Notes :", fontsize=8)
    pg2.insert_text((45, 340), "1. Vendor shall provide Cold Differential Test Pressure (CDTP).", fontsize=8, fontname="hebo")
    pg2.insert_text((45, 355), "2. Bolt and Nuts Material : ASTM A193-B7M / A194-2HM", fontsize=8, fontname="hebo")
    pg2.insert_text((45, 600), "Common Notes :", fontsize=8)
    pg2.insert_text((45, 620), "1. Painting as per project specification.", fontsize=8)
    return doc.tobytes()


def test_psv_form_701(tmp_path):
    p = tmp_path / "psv.pdf"
    p.write_bytes(make_psv_pdf())
    res = extract.read_pdf(str(p))
    dss = extract.group_datasheets(res)
    assert len(dss) == 1
    d = dss[0]
    F = {k: f["value"] for k, f in d["fields"].items()}
    U = {k: f["unit"] for k, f in d["fields"].items()}
    assert d["form"] == "701" and d["family"] == "psv" and d["pages"] == [1, 2]
    assert F["tag"] == "98PRV 980001A" and F["service"] == "RELIEF GAS FR K-1"
    assert (F["pid_no"], F["line_no"], F["equipment_no"]) == ("00-00-PR-PID-00001", 'L100-6"(A1)', "-")   # '/' between slots dropped
    assert (F["piping_class"], F["piping_class_outlet"]) == ("YC0KL", "YC0KL-N")
    assert (F["seat_type"], F["seat_tightness"]) == ("Soft Seat", "As per API 527")       # sub-labels open slots (no underline)
    assert (F["inlet_size"], F["inlet_rating"], F["inlet_facing"]) == ('3"', "600#", "RF Flange")
    assert (F["outlet_size"], F["outlet_rating"], F["outlet_facing"]) == ('4"', "150#", "RF Flange")
    assert (F["body_material"], F["bonnet_material"], F["nozzle_material"]) == ("A216-WCB", "A216-WCB", "316 SS")
    assert (F["rings_material"], F["spring_material"], F["bellows_material"]) == ("VTA", "Carbon Steel", "N/A")   # page slot grid
    assert (F["fluid"], F["fluid_state"]) == ("Flare gas", "Gas")
    assert F["set_pressure"] == "45" and U["set_pressure"] == "bar-g"                    # unit slot -> the value before it
    assert F["op_pressure"] == "" and U["op_pressure"] == "bar-g"
    assert F["relieving_flow"] == "12000" and U["relieving_flow"] == "kg/h"
    assert F["orifice"] == "J" and F["calc_area"] == "1.20" and F["selected_area"] == "1.29"
    assert (F["cap_type"], F["lifting_lever"], F["test_gag"]) == ("Screwed", "Not Required", "Not Required")
    assert "design_pressure_2" not in F and "tag_2" not in F                              # empty extra slots make no field
    assert not any(k.startswith(("x.", "raw.")) for k in F)
    assert d["doc_no"] == ""                                                               # the DOCUMENT NO. cell holds the tag
    texts = [n["text"] for n in d["notes"]]
    assert len(texts) == 3 and "CDTP" in texts[0] and d["notes"][2].get("section") == "Common Notes"


# ── Form 101 (Control Valve) ───────────────────────────────────────────────────────────────────────────────

C1 = [("TAG", [("Tag No.", "01FV 9401"), ("PID No.", "01-09-PR-PID-00004"), ("Service", "FR ABS OVHD GAS"), ("Valve Type", "Globe Control Valve")]),
      ("VALVEGEN", [("Manufacturer Name", "VTA"), ("Air Failure Action", "Close"), ("Leakage Class", "ANSI IV")]),
      ("GENERAL", [("Line No.", "AG1441-24\"(1C3AS1)"), ("ServiceClass", "1C3AS1"), ("Design Pressure", ["98", "/", "bar-g"]),
                   ("Instrument Air Supply", None), ("Mechanical Design Pressure", "10 barg"),
                   ("Operating Pressure(Max/Min)", ["7.5", "/", "4.5", "bar-g"]), ("Type", "Ex 'd'")]),
      ("POSITNR", [("Positioner Type", "Smart HART"), ("Manufacturer", "Fisher"), ("Model", "DVC6200")]),
      ("BODY", [("Body Size", "3"), ("Rating", "600#"), ("Body/Bonnet Material", "A216-WCB")]),
      ("TRIM", [("Trim Type", "Cage"), ("Size", "3\""), ("Rated Cv", "120"), ("Characteristic", "Equal %"),
                ("Plug / Ball / Disc", "316 SS"), ("Seat", "316 SS"), ("Stem", "17-4PH")])]
C2 = [("ACTUATOR", [("Manuf.", "Emerson"), ("Model", "667"), ("Type of Actuator", "Spring-diaphragm"), ("Size", "40"), ("Yoke", "CS"),
                    ("Stroke Speed", "VTA")]),
      ("PAINT", [("Painting System", "Gen Note-9"), ("Body", "RAL 7035"), ("Handwheel", "RAL 1003")]),
      ("VALACC", [("Handwheel", "Yes"), ("Lubricant Material", "VTA"), ("Mechanical Valve Stopper", "N/A")]),
      ("PNEUMATIC", [("Air Tube Material", "SS316"), ("Size", "1/2\""), ("Air Set", None), ("Manufacturer", "Bellofram"),
                     ("Volume Tank", None), ("Tag No.", "N/A")]),
      ("ELECTRICAL", [("Solenoid Valve", None), ("Tag No", "01SY 9401"), ("Power Supply", "24 VDC"),
                      ("Type of Position Indication", "Position Transmitter"), ("Tag No", "01ZT 9401"), ("Rating", "IP66"),
                      ("Model", "3051"), ("Manuf.", "Rosemount")])]


def _column(pg, blocks, n0, x_num, y0, p):
    y, n = y0, n0
    x_lab = x_num + 26
    pg.draw_line((x_num - 8, y - 9), (x_num + 22, y - 9), width=0.5)
    for cap, rows in blocks:
        top = y - 9
        for lab, val in rows:
            pg.insert_text((x_num - (5 if n < 10 else 9 if n < 100 else 13), y), str(n), fontsize=8)
            if val is None:
                pg.insert_text((x_lab, y), lab, fontsize=8)                        # a bare caption row (heading)
            else:
                pg.insert_text((x_lab, y), f"{lab} :", fontsize=8)
                x = x_lab + pymupdf.get_text_length(f"{lab} : ", fontsize=8)
                for v in (val if isinstance(val, list) else [val]):
                    bold = v != "/"
                    pg.insert_text((x, y), v, fontsize=8, fontname="hebo" if bold else "helv")
                    x += pymupdf.get_text_length(v + " ", fontname="hebo" if bold else "helv", fontsize=8) + 2
            y += p
            n += 1
        bottom = y - 9
        for i, ch in enumerate(cap[: max(1, int((bottom - top) / 4.6) - 1)]):
            pg.insert_text((x_num + 6, top + 6 + i * 4.6), ch, fontsize=4.2)
        pg.draw_line((x_num - 8, bottom), (x_num + 22, bottom), width=0.5)
    return n


def make_cv_pdf() -> bytes:
    doc = pymupdf.open()
    pg = doc.new_page(width=595, height=842)
    pg.insert_text((45, 70), "Form No : 101", fontsize=9)
    pg.insert_text((260, 125), "Control Valve", fontsize=15, fontname="hebo")
    pg.insert_text((450, 120), "DOCUMENT NO.", fontsize=8)
    pg.insert_text((460, 140), "01-09-IN-DTS-00001", fontsize=9, fontname="hebo")
    pg.insert_text((450, 190), "SHEET 1 OF 1", fontsize=8)
    pg.insert_text((450, 210), "REV.", fontsize=8)
    pg.insert_text((520, 210), "A", fontsize=8)
    n1 = _column(pg, C1, 1, 58, 270, 11.2)
    _column(pg, C2, 53, 330, 270, 11.2)
    assert n1 > 20
    return doc.tobytes()


def test_control_valve_form_101(tmp_path):
    p = tmp_path / "cv.pdf"
    p.write_bytes(make_cv_pdf())
    d = extract.group_datasheets(extract.read_pdf(str(p)))[0]
    F = {k: f["value"] for k, f in d["fields"].items()}
    assert d["form"] == "101" and d["family"] == "globe"
    # the same printed label means different things in different blocks
    assert F["pos_manufacturer"] == "Fisher" and F["pos_model"] == "DVC6200"
    assert F["act_manufacturer"] == "Emerson" and F["act_model"] == "667" and F["act_size"] == "40"
    assert F["trim_size"] == '3"' and F["rated_cv"] == "120" and F["flow_char"] == "Equal %"
    assert F["paint_body"] == "RAL 7035" and F["paint_handwheel"] == "RAL 1003" and F["handwheel"] == "Yes"
    assert F["tubing"] == "SS316" and F["tubing_size"] == '1/2"' and F["afr_manufacturer"] == "Bellofram" and F["vt_tag"] == "N/A"
    assert F["sov_tag"] == "01SY 9401" and F["sov_power_supply"] == "24 VDC"
    assert F["pos_tx_tag"] == "01ZT 9401" and F["pos_tx_ingress"] == "IP66" and F["pos_tx_model"] == "3051"
    assert F["rating"] == "600#" and F["tag"] == "01FV 9401"                               # not the transmitter's 'Rating' / tags
    assert F["design_pressure"] == "98" and d["fields"]["design_pressure"]["unit"] == "bar-g"
    assert F["ia_design_pressure"] == "10 barg" and F["ia_op_pressure"] == "7.5" and F["ia_op_pressure_min"] == "4.5"
    assert "op_pressure" not in F                                                         # instrument air, not process pressure
    assert F["ex_type"] == "Ex 'd'"


def test_form_101_helpers():
    r = {"key": "ex_type", "value": "Ex / ' / d / ' / / Ex ‘n’ / Ex ‘ec’"}
    forms_ext._tidy_value(r)
    assert r["value"] == "Ex 'd' / Ex ‘n’ / Ex ‘ec’"
    r = {"key": "ex_type", "value": "Ex ‘n’ or Ex ‘ec’"}
    forms_ext._tidy_value(r)
    assert r["value"] == "Ex ‘n’ or Ex ‘ec’"
    r = {"key": "design_temp", "value": "195 / -30 / ºC", "unit": "", "status": "ok"}
    extra = forms_ext._split_pair(r)
    assert (r["value"], r["unit"], extra[0]["key"], extra[0]["value"]) == ("195", "ºC", "design_temp_min", "-30")
    sh = {"rows": [{"label": f"Calculated CV ({c})", "key": f"x.calculated_cv.{c.lower()}", "value": v, "unit": "", "bbox": None,
                    "section": "process", "status": "ok"} for c, v in (("Max", "90"), ("Nor", "70"), ("Min", ""))]
                  + [{"label": f"Design Pressure ({c})", "key": f"x.design_pressure.{c.lower()}", "value": v, "unit": "",
                      "bbox": [10, 10, 20, 20] if v else None, "section": "process", "status": "ok"}
                     for c, v in (("Max", "98"), ("Nor", "/"), ("Min", "bar-g"))]}
    forms_ext.fix_101_sheet2(sh, {"doc_no": "D-1"})
    k = {r["key"]: r for r in sh["rows"]}
    assert k["calc_cv.max"]["section"] == "sizing" and k["calc_cv.max"]["value"] == "90"
    assert k["sz_design_pressure"]["value"] == "98" and k["sz_design_pressure"]["unit"] == "bar-g"


# ── Code 80 with the title block at the bottom + a notes-only sheet 2 (Butterfly On/Off) ─────────────────────

X_NUM, X_L1, X_L2, X_V, X_MID, X_R = 122, 136, 222, 313, 438, 572
BFV_ROWS = [(1, ["Tag No.", "Item No."], ["53SDV090093", "VTA"]), (2, ["Service"], ["AGAS FR 53-C0933"]),
            (3, ["PID No."], ["QCS-53-09-PR-DR-PI-406"]), (4, ["Line N°"], ['P53093520-32"(1C6AS-A)']),
            (5, ["Piping class"], ["1C6AS-A"]), (6, ["Body Size", "Body Type"], ['32"', "Triple Offset-Butterfly Valve"]),
            (7, ["Connections", "Rating"], ["RF", "150#"]), (8, ["Body material"], ["CS ASTM A216-WCB"]),
            (9, ["Ball / Disc Material"], ["SS 316"]), (10, ["Seat Trim Material", "Seat Seal Material"], ["SS 316", "SS 316"]),
            (11, ["Valve Power Failure position"], ["Fail close"]), (12, ["Bolting / Gasket"], ["Note-1"])]


def _footer(pg, sheet):
    pg.insert_text((50, 770), "A    AS    8/4/2026    Issued for Inter-Discipline Check", fontsize=7)
    pg.insert_text((330, 760), "DATA SHEET", fontsize=7)
    pg.insert_text((325, 770), "ON / OFF VALVE", fontsize=7)
    pg.insert_text((440, 785), "Sheet", fontsize=7)
    pg.insert_text((500, 785), str(sheet), fontsize=7)
    pg.insert_text((530, 785), "of", fontsize=7)
    pg.insert_text((550, 785), "2", fontsize=7)
    pg.insert_text((320, 800), "Code: 80", fontsize=7)
    pg.insert_text((400, 800), "Dwg. No.: xxxxx", fontsize=7)
    pg.insert_text((540, 800), "Rev.:A", fontsize=7)


def make_bfv_pdf() -> bytes:
    doc = pymupdf.open()
    pg = doc.new_page(width=595, height=842)
    y = 80
    for no, labels, vals in BFV_ROWS:
        pg.draw_rect(pymupdf.Rect(43, y, X_R, y + 12), width=0.5)
        for x in [X_NUM, X_L1, X_V, X_R] + ([X_L2, X_MID] if len(labels) == 2 else []):
            pg.draw_line((x, y), (x, y + 12), width=0.5)
        pg.insert_text((X_NUM + 4, y + 9), str(no), fontsize=7)
        for i, lab in enumerate(labels):
            pg.insert_text(([X_L1 + 3, X_L2 + 3][i], y + 9), lab, fontsize=7)
        for i, v in enumerate(vals):
            pg.insert_text(([X_V + 3, X_MID + 3] if len(labels) == 2 else [X_V + 3])[i], v, fontsize=7) if False else \
                pg.insert_text((([X_V + 3, X_MID + 3] if len(labels) == 2 else [X_V + 3])[i], y + 9), v, fontsize=7)
        y += 12
    _footer(pg, 1)
    pg2 = doc.new_page(width=595, height=842)
    pg2.insert_text((50, 80), "Notes:", fontsize=7)
    pg2.insert_text((50, 95), "1. Gasket shall be SPIRAL WOUND, 316 SS, CL600.", fontsize=7)
    pg2.insert_text((50, 105), "Stud Bolt Material: CR-MO A193-B7M.", fontsize=7)
    pg2.insert_text((50, 115), "2. Position Transmitter with 24V DC and 4-20 mA HART.", fontsize=7)
    _footer(pg2, 2)
    return doc.tobytes()


def test_code80_bottom_title_block_and_notes_sheet(tmp_path):
    p = tmp_path / "bfv.pdf"
    p.write_bytes(make_bfv_pdf())
    res = extract.read_pdf(str(p))
    dss = extract.group_datasheets(res)
    assert len(dss) == 1 and not res["other_pages"]
    d = dss[0]
    assert d["pages"] == [1, 2] and d["rev"] == "A" and d["sheets"] == [[1, 1, 2], [2, 2, 2]]
    assert d["family"] == "butterfly" and d["fields"]["ball_material"]["display"] == "Disc Material"
    F = {k: f["value"] for k, f in d["fields"].items()}
    assert F["line_no"].startswith("P53093520") and F["fail_position"] == "Fail close"
    assert F["seat_material"] == "SS 316" and F["seal_material"] == "SS 316"
    assert [n["no"] for n in d["notes"]] == [1, 2] and "Stud Bolt" in d["notes"][0]["text"]
    assert d["fields"]["bolting_gasket"]["ref"]["no"] == 1                                # 'Note-1' resolves to sheet 2


def test_kind_helpers():
    assert schema.project_kind("CO2 PJT") == "ball" and schema.project_kind("CO2 PJT · Globe Valve") == "globe"
    assert schema.project_kind("X · PSV") == "psv" and schema.project_kind("X · Butterfly Valve") == "butterfly"
    fam = lambda form, **kw: schema.family(form, {k: {"value": v} for k, v in kw.items()})   # noqa: E731
    assert fam("101", body_type="Butterfly Control Valve - Triple Offset") == "butterfly"
    assert fam("101", instrument_type="Air Actuated CV (Globe) E/P positioner") == "globe"
    assert fam("on/off", body_type="Ball (Full Bore) - Floating") == "ball"
    assert fam("701") == "psv"
    assert schema.lookup_101("Manufacturer", "POSTNR.") [0] == "pos_manufacturer"
    assert schema.lookup_101("Tag No", "ELECTRICALACC.", "Solenoid Valve")[0] == "sov_tag"
    assert schema.lookup_101("Tag No", "ELECTRICALACC.", "Solenoid Valve", "POSIND")[0] == "pos_tx_tag"


# ── the menus: one project per kind, Ball-only rules stay in Ball projects ───────────────────────────────────

def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    api._KIND_CACHE.clear()
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def _upload(c, pid, name, data):
    j = c.post(f"/api/valve/projects/{pid}/upload", data={"kind": "datasheet"},
               files=[("files", (name, data, "application/pdf"))], headers={"X-Author": "t"}).json()
    for _ in range(150):
        st = c.get(f"/api/valve/jobs/{j['id']}").json()
        if st["status"] == "done":
            return st
        time.sleep(0.1)
    raise AssertionError("upload did not finish")


def test_kind_projects_and_rules(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    pid = c.post("/api/valve/projects", json={"name": "CO2 PJT · PSV"}).json()["id"]
    st = _upload(c, pid, "psv.pdf", make_psv_pdf())
    assert not st["warn"]
    st = _upload(c, pid, "cv.pdf", make_cv_pdf())
    assert "Globe Valve 1장" in st["warn"]                                                 # put in the wrong menu: said, kept
    s = c.get(f"/api/valve/projects/{pid}/summary").json()
    assert s["kpi"]["datasheets"] == 2
    psv = next(c.get(f"/api/valve/datasheets/{t['id']}").json() for t in s["tags"] if t["tag"].startswith("98PRV"))
    assert psv["kind"] == "psv" and psv["family"] == "psv" and psv["form"] == "701"
    assert psv["material_review"] == [] and psv["pms"] is None
    ball_only = [x for x in psv["verification"]["checks"] if x["group"] in ("Material", "Design", "PMS")]
    assert ball_only and all(x["status"] == "n/a" and "Ball Valve rule" in x["reason"] for x in ball_only)
    miss = {i["key"] for i in psv["issues"] if i["type"] == "Data Missing"}
    assert "op_pressure" in miss                                                          # blank PROCESS DATA item, once
    assert len([i for i in psv["issues"] if i["ikey"] == "Data Missing:op_pressure"]) == 1


def test_ball_project_unchanged_kind(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    pid = c.post("/api/valve/projects", json={"name": "CO2 PJT"}).json()["id"]
    from tests.test_valve import make_pdf
    _upload(c, pid, "ds.pdf", make_pdf())
    s = c.get(f"/api/valve/projects/{pid}/summary").json()
    d = c.get(f"/api/valve/datasheets/{s['tags'][0]['id']}").json()
    assert d["kind"] == "ball" and d["family"] == "ball"
    assert not any("Ball Valve rule" in (x.get("reason") or "") for x in d["verification"]["checks"])


@pytest.mark.skipif(not os.environ.get("VALVE_KIND_SAMPLES"), reason="client sample files are not in the repository")
def test_real_kind_samples():
    D = Path(os.environ["VALVE_KIND_SAMPLES"])
    want = {"globe_cv.pdf": ("101", "globe", 3, 6), "bfv_cv.pdf": ("101", "butterfly", 2, 0),
            "bfv_onoff.pdf": (None, "butterfly", 2, 9), "psv.pdf": ("701", "psv", 2, 5)}
    for name, (form, fam, pages, notes) in want.items():
        d = extract.group_datasheets(extract.read_pdf(str(D / name)))[0]
        assert (d.get("form"), d["family"], len(d["pages"]), len(d["notes"])) == (form, fam, pages, notes), name
        assert not [k for k in d["fields"] if k.startswith("x.")], name
