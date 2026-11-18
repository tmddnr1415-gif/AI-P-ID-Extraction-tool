"""valve41 — the ISA-20 style 'INSTRUMENT SPECIFICATION' sheet (company PC 2026-11-18: the South control-valve / regulator
datasheets were read as one datasheet without a tag).  The sheet is drawn here with made-up values (nothing from a client):
ruled cells, two number columns, no colons, title block at the bottom, a notes sheet 2."""
from __future__ import annotations

import time

import pymupdf

PITCH, Y0 = 11.25, 22.0
XF0, XN0, XN1, XA, XR0, XR1, XRD, XF1, XBD = 46, 97, 110, 307, 358, 373, 460, 568, 200


def _y(n):                                            # top of row n (right rows 56.. sit beside 31..)
    return Y0 + ((n - 1) if n <= 55 else (n - 56 + 30)) * PITCH


def _sheet(doc, tag, rev="B", size="4", extra=None):
    p = doc.new_page(width=595, height=842)
    L = lambda x0, y0, x1, y1: p.draw_line((x0, y0), (x1, y1), width=0.5)     # noqa: E731
    T = lambda x, n, s: p.insert_text((x, _y(n) + 8.5), s, fontsize=8)        # noqa: E731
    top, mid, bot = _y(1), _y(31), _y(55) + PITCH
    for x in (XF0, XN0, XN1, XA, XF1):
        L(x, top, x, bot)
    for x in (XR0, XR1, XRD):
        L(x, mid, x, _y(83) + PITCH)
    L(XBD, mid, XBD, bot)
    for n in range(1, 32):                                                     # rows 1-30 over the whole width
        L(XN0, _y(n), XF1, _y(n))
    for n in range(31, 57):
        L(XN0, _y(n), XA, _y(n))
    for n in range(56, 85):
        L(XR0, _y(n), XF1, _y(n))
    for n in (1, 14, 31, 49, 56):                                              # caption bands, left
        L(XF0, _y(n), XN0, _y(n))
    for n in (56, 63, 67, 76, 79, 84):                                         # caption bands, right
        L(XA, _y(n), XR0, _y(n))
    for n in range(1, 56):
        T(104 if n < 10 else 101.5, n, str(n))
    for n in range(56, 84):
        T(361, n, str(n))
    for x, n, s in ((55, 6, "GENERAL"), (52, 20, "PROCESS"), (48, 22, "CONDITIONS"), (56, 38, "BODY"), (56, 39, "AND"), (56, 40, "TRIM"),
                    (51, 52, "ACTUATOR"), (310, 58, "POSITIONER"), (313, 64, "SOLENOID"), (313, 65, "VALVE"), (311, 70, "AIR"),
                    (324, 70, "SET"), (313, 77, "TESTS"), (313, 80, "PURCHASE")):
        p.insert_text((x, _y(n) + 8), s, fontsize=6.8)

    def cell(n, splits):                                                       # vertical sub-rules of one row
        for x in splits:
            L(x, _y(n), x, _y(n) + PITCH)

    rows = {1: [("Tag No.", 114)], 2: [("Service", 114)], 3: [("Line No.", 114), ("P&ID", 211)], 4: [("Area Classification", 114)],
            5: [("Ambient Temperature:", 114), ("Min.", 257), ("Max.", 284)], 7: [("Tightness Requirements", 114)],
            9: [("Power Failure Position", 114)], 11: [("Line Size and Schedule", 114), ("Inlet", 257), ("Outlet", 284)],
            12: [("Pipe Material", 114)], 14: [("Process Fluid", 114)], 15: [("Upstream Condition", 114)],
            18: [("Flow Rate", 114)], 19: [("Inlet Pressure", 114)], 21: [("Inlet Temperature", 114)], 28: [("Flow Coefficient Cv", 114)],
            31: [("MFR", 114), ("Model", 155)], 32: [("Body Type", 114)], 33: [("Body Size", 114), ("Trim Size", 155)],
            35: [("End Connec. & Rating", 114)], 36: [("Body Material", 114)], 45: [("Seat Material", 114)],
            49: [("MFR", 114), ("Model", 155)], 50: [("Type", 114)], 52: [("Air Failure Valve:", 114)],
            56: [("MFR", 377), ("Model", 423)], 57: [("Signal: Inlet", 377), ("Outlet", 423)], 62: [("Positioner Tag", 377)],
            63: [("MFR", 377), ("Model", 423)], 64: [("Type", 377)], 73: [("Set Pressure", 377)], 76: [("Hydro. Pressure", 377)],
            81: [("Purchase Order Num.", 377)], 83: [("Serial Number", 377)]}
    for n, labs in rows.items():
        for s, x in labs:
            T(x, n, s)
    vals = {1: [(tag, 310)], 2: [("TEST SERVICE LINE", 310)], 3: [("71TST-1001-4\"-TC1A-A-N", 310), ("777-71-PR-PID-00012", 440)],
            4: [("Zone 2, IIB, T3", 310)], 5: [("4", 310), ("°C", 375), ("49", 440), ("°C", 505)], 7: [("ANSI IV (standard)", 310)],
            9: [("Open", 310)], 11: [(size, 310), ("in", 344), ("80", 375), (size, 440), ("in", 505)], 12: [("TEST PIPE MATERIAL", 310)],
            14: [("Nitrogen", 310)], 15: [("Gas/Vapor", 310)], 17: [("Units", 318), ("@ Max. Flow", 372), ("@ Norm. Flow", 440), ("@ Min. Flow", 508)],
            18: [("kg/h", 310), ("1200", 372), ("900", 440)], 19: [("bar-g", 310), ("12.5", 372), ("11", 440), ("9.5", 508)], 21: [("°C", 310)],
            31: [("VTA", 203), ("VTA", 256)], 32: [("Single Seat Globe (VTA)", 203)], 33: [(size, 203), ("in", 232), ("VTA", 256)],
            35: [("RF,1500#", 203)], 36: [("TEST BODY MATERIAL", 203)], 45: [("316L SS", 203)], 49: [("VTA", 203), ("TEST-ACT", 256)],
            50: [("Note-3", 203)], 52: [("Close", 203)], 56: [("VTA", 464), ("TEST-POS", 517)], 57: [("4-20 mA DC", 464), ("3-15 psi", 517)],
            62: [("71FY -900", 464)], 63: [("NA", 464), ("NA", 517)], 64: [("NA", 464)], 73: [("4 barg (VTA)", 464)],
            76: [("Required (General Note-14)", 464)], 81: [("TBC", 464)], 83: [("TBC", 464)]}
    vals.update(extra or {})
    for n, vs in vals.items():
        for s, x in vs:
            T(x, n, s)
    cell(3, (207, 437)); cell(5, (253, 281, 372, 435, 501)); cell(11, (253, 281, 341, 372, 435, 440, 501))
    for n in range(17, 31):
        cell(n, (356, 426, 496))
    for n in (31, 33, 49):
        cell(n, (151, 252) if n != 33 else (151, 228, 252))
    for n in (56, 57, 63):
        cell(n, (419, 513))
    yb = _y(83) + PITCH + 30                                               # the title block under the table
    p.insert_text((315, yb), "INSTRUMENT SPECIFICATION", fontsize=9)
    p.insert_text((345, yb + 12), "Control Valve", fontsize=9)
    for i, (r, by, d, t) in enumerate((("B", "TT", "7/21/2026", "Issued for Approval"), ("A", "TT", "7/19/2026", "Issued for Check"))):
        yy = yb + 28 + i * 11
        for x, s in ((48, r), (75, by), (105, d), (155, t)):
            p.insert_text((x, yy), s, fontsize=8)
    yy = yb + 50
    for x, s in ((440, "Sheet"), (468, "1"), (500, "of"), (512, "2")):
        p.insert_text((x, yy - 11), s, fontsize=8)
    for x, s in ((300, "Code: 1"), (375, "Doc. No.:"), (415, "777-71-IN-DTS-00001"), (525, "Rev.:"), (548, rev)):
        p.insert_text((x, yy), s, fontsize=8)
    q = doc.new_page(width=595, height=842)                                    # sheet 2: notes only
    for y, s in ((60, "Notes:"), (74, "1. Gasket material: TEST GASKET, SPIRAL WOUND"), (86, "2. Stud bolt material: TEST BOLT"),
                 (98, "3. Pneumatic spring diaphragm actuator")):
        q.insert_text((60, y), s, fontsize=8)
    q.insert_text((315, 700), "INSTRUMENT SPECIFICATION", fontsize=9)
    q.insert_text((345, 712), "Control Valve", fontsize=9)
    for x, s in ((440, "Sheet"), (468, "2"), (500, "of"), (512, "2")):
        q.insert_text((x, 739), s, fontsize=8)
    for x, s in ((300, "Code: 1"), (375, "Doc. No.:"), (415, "777-71-IN-DTS-00001"), (525, "Rev.:"), (548, rev)):
        q.insert_text((x, 750), s, fontsize=8)


def _pdf(tags=("71FV -900", "71LV -901")):
    doc = pymupdf.open()
    for i, t in enumerate(tags):
        _sheet(doc, t, size="4" if i == 0 else "2")
    data = doc.tobytes()
    doc.close()
    return data


def test_isa20_sheet_is_read_cell_by_cell(tmp_path):
    from app.valve import extract
    f = tmp_path / "isa.pdf"
    f.write_bytes(_pdf())
    ds = extract.group_datasheets(extract.read_pdf(str(f)))
    assert [(d["tag"], d["pages"], d.get("form"), d["rev"], d["doc_no"]) for d in ds] == [
        ("71FV -900", [1, 2], "ISA20", "B", "777-71-IN-DTS-00001"), ("71LV -901", [3, 4], "ISA20", "B", "777-71-IN-DTS-00001")]
    d = ds[0]
    F = {k: (v["value"], v["unit"]) for k, v in d["fields"].items()}
    assert d["family"] == "globe" and d["valve_type"] == "FV" and d["sheets"] == [[1, 1, 2], [2, 2, 2]]
    assert F["service"] == ("TEST SERVICE LINE", "") and F["line_no"][0] == '71TST-1001-4"-TC1A-A-N' and F["pid_no"][0] == "777-71-PR-PID-00012"
    assert F["ambient_temp_min"] == ("4", "°C") and F["ambient_temp_max"] == ("49", "°C")                # a heading and its two parts
    assert F["line_size_inlet"] == ("4", "in") and F["line_schedule_inlet"][0] == "80" and F["line_size_outlet"] == ("4", "in")
    assert F["flow.max"] == ("1200", "kg/h") and F["flow.nor"][0] == "900" and F["flow.min"][0] == ""   # Units | Max | Norm | Min
    assert F["inlet_pressure.min"] == ("9.5", "bar-g") and F["op_temp.nor"] == ("", "°C")
    # the same label in different blocks: body · actuator · positioner · solenoid
    assert F["manufacturer"][0] == "VTA" and F["act_model"][0] == "TEST-ACT" and F["pos_model"][0] == "TEST-POS" and F["sov_model"][0] == "NA"
    assert F["act_type"][0] == "Note-3" and F["sov_type"][0] == "NA" and F["fail_position"][0] == "Close"
    assert F["body_size"] == ("4", "in") and F["trim_size"][0] == "VTA" and F["connections"][0] == "RF,1500#" and F["rating"][0] == "1500#"
    assert F["pos_signal"][0] == "4-20 mA DC" and F["pos_output"] == ("3-15", "psi") and F["fluid"][0] == "Nitrogen"
    assert not [k for k in d["fields"] if k.startswith("x.")]
    assert d["fields"]["po_no"]["section"] == "purchase" and d["fields"]["calc_cv.max"]["section"] == "sizing"
    assert [n["no"] for n in d["notes"]] == [1, 2, 3] and "TEST GASKET" in d["notes"][0]["text"]
    assert d["rev_history"] and d["date"] == "7/21/2026"
    bb = d["fields"]["tag"]["bbox"]                                                                       # the value's own box on the page
    assert 300 < bb[0] < 320 and bb[1] < 40
    assert ds[1]["fields"]["body_size"]["value"] == "2"


def test_isa20_upload_reread_and_review(tmp_path, monkeypatch):
    """Through the API: tags and areas; 'TBC' in the PURCHASE block is not an Open Item; a tag-less datasheet left by an older
    reading of the same file goes when the file is read again."""
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.valve import api, store
    app = FastAPI()
    app.include_router(api.router)
    c = TestClient(app)
    pid = c.post("/api/valve/projects", json={"name": "T · Globe Valve"}).json()["id"]

    def wait(j):
        for _ in range(400):
            if c.get(f"/api/valve/jobs/{j['id']}").json()["status"] == "done":
                return
            time.sleep(0.05)
        raise AssertionError("job did not finish")
    wait(c.post(f"/api/valve/projects/{pid}/upload", data={"kind": "datasheet"}, files=[("files", ("isa.pdf", _pdf(), "application/pdf"))]).json())
    s = c.get(f"/api/valve/projects/{pid}/summary").json()
    assert sorted(t["tag_key"] for t in s["tags"]) == ["71FV900", "71LV901"] and s["documents"][0]["info"]["reader"]
    I = c.get(f"/api/valve/projects/{pid}/issues").json()["issues"]
    assert not [i for i in I if i["type"] == "Open Item" and "Purchase" in (i.get("field") or "")]
    assert any(i["check"] == "DM-02" for i in I)                                 # blank process cells are still a finding
    con = store.connect()
    doc = store.one(con, "SELECT id FROM document WHERE project_id=?", pid)["id"]
    con.execute("INSERT INTO datasheet(project_id, document_id, tag, tag_key, rev, pages, notes, rev_history, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (pid, doc, "", "", "", "[1]", "[]", "[]", store.now()))            # what the older reader left
    con.commit()
    wait(c.post(f"/api/valve/documents/{doc}/retry").json())
    rows = store.rows(con, "SELECT tag_key, rev FROM datasheet WHERE document_id=? ORDER BY tag_key", doc)
    assert [(r["tag_key"], r["rev"]) for r in rows] == [("71FV900", "B"), ("71LV901", "B")]
