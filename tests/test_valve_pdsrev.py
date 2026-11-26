"""valve43 — a revised PDS (same document number) is compared with the earlier Rev. into the engineers' Excel layout
(user 2026-11-26).  The PDS is drawn here with made-up tags and values in the same table form (nothing from a client):
rules drawn cell by cell, a location written on three lines centred in a tall row (its first line sits ABOVE the row's
Sr. No.), an On-Off and an MOV section, a column only the newer Rev. has."""
from __future__ import annotations

import io
import time

import pymupdf

DN = "777-98-PR-DTS-00001"
COLS = [("Sr no.", ""), ("Tag Number", ""), ("Location", ""), ("Quantity", ""), ("PID No", ""), ("Valve type", ""), ("Line No", ""),
        ("Line Size", ""), ("Valve Size", ""), ("Valve Bore", ""), ("Pipe Class", ""), ("Service Fluid", ""), ("Process Fluid Phase", ""),
        ("Flow rate", "m3/h"), ("Maximum Pressure Drop", "bar"), ("Operating Temperature", "°C"), ("Design Temperature", "°C"),
        ("Operating Pressure", "bar(g)"), ("Design Pressure", "bar(g)"), ("Molecular Weight", "kg/kmol"), ("Required Tightness", "")]
KEYS = ["sr", "tag", "location", "quantity", "pid_no", "valve_type", "line_no", "line_size", "valve_size", "bore", "piping_class",
        "fluid", "fluid_state", "flow", "max_dp", "op_temp", "design_temp", "op_pressure", "design_pressure", "mol_weight", "tightness"]
W = [18, 52, 70, 22, 62, 36, 80, 26, 26, 24, 34, 40, 30, 26, 30, 34, 34, 34, 34, 34, 30]


def _row(tag, **kv):
    base = {"tag": tag, "location": "FIRST LINE OF SERVICE|SECOND LINE|THIRD LINE", "quantity": "1", "pid_no": "777-98-PR-PID-00010",
            "valve_type": "BALL VALVE", "line_no": 'P7701-6"(XC0KL-A)-N', "line_size": '6"', "valve_size": '6"', "bore": "Full",
            "piping_class": "XC0KL-A", "fluid": "CO2", "fluid_state": "Vapor", "flow": "-", "max_dp": "-", "op_temp": "50.00",
            "design_temp": "85.00", "op_pressure": "100.00", "design_pressure": "154.00", "mol_weight": "44.10", "tightness": "TSO"}
    base.update(kv)
    return base


def _pds(sections, rev, extra=False):
    """sections: [(title, [row dict])] — one page each, after a cover page."""
    doc = pymupdf.open()
    cover = doc.new_page(width=1190, height=842)
    for i, s in enumerate(["PROCESS DATA SHEET FOR ON-OFF VALVE, MOTOR OPERATED VALVE (MOV)", "REV SHT. REV.", f"1 {rev}", "DOCUMENT NUMBER", DN]):
        cover.insert_text((60, 80 + 14 * i), s, fontsize=9)
    cols = COLS + ([("Dense Phase/Supercritical Phase CO2", "")] if extra else [])
    widths = W + ([34] if extra else [])
    xs = [20]
    for w in widths:
        xs.append(xs[-1] + w)
    sr = 0
    for title, rows in sections:
        pg = doc.new_page(width=1190, height=842)
        pg.insert_text((480, 60), title, fontsize=9)
        pg.insert_text((900, 820), f"{DN}_Rev.{rev}", fontsize=7)
        ys = [70, 110, 125, 140] + [140 + 36 * (i + 1) for i in range(len(rows))]
        for y0, y1 in zip(ys, ys[1:]):                                       # verticals drawn cell by cell (one piece per row)
            for x in xs:
                pg.draw_line((x, y0), (x, y1), width=0.5)
        for y in ys:
            pg.draw_line((xs[0], y), (xs[-1], y), width=0.5)
        for (h, u), x0 in zip(cols, xs):
            words = h.split()
            half = (len(words) + 1) // 2
            pg.insert_text((x0 + 1, 85), " ".join(words[:half]), fontsize=4.5)
            if words[half:]:
                pg.insert_text((x0 + 1, 100), " ".join(words[half:]), fontsize=4.5)
            if u:
                pg.insert_text((x0 + 1, 120), u, fontsize=4.5)
        pg.insert_text((480, 135), "On-Off valve (Refer to Note no.s 1~5)", fontsize=5)
        for i, r in enumerate(rows):
            sr += 1
            mid = 140 + 36 * i + 20
            vals = dict(r, sr=str(sr))
            for k, x0 in zip(KEYS + (["dense"] if extra else []), xs):
                v = vals.get(k, "Yes" if k == "dense" else "")
                if k == "location":
                    for j, part in enumerate(v.split("|")):                 # three lines centred: the first is above the Sr. line
                        pg.insert_text((x0 + 1, mid - 9 + 9 * j), part, fontsize=4.5)
                else:
                    pg.insert_text((x0 + 1, mid), v, fontsize=4.5)
    data = doc.tobytes()
    doc.close()
    return data


OLD = [("Process Data for On-Off Valve", [
    _row("77XV001"),                                                         # → valve size 6"→4" (High), op temp +1 % (Med→Min)
    _row("77XV002", line_no='P7702-4"(XC0KL-A)-N', line_size='4"', valve_size="4'"),     # → notation only: No Change
    _row("77XV003", line_no='P7703-8"(YC0KL-N)-N', pid_no="777-98-PR-PID-00012", line_size='8"', piping_class="YC0KL-N"),   # number reused elsewhere
    _row("77XV004", line_no='P7704-2"(XC0KL-A)-N', line_size='2"', valve_size='2"'),     # renamed to 77XV104 on the same line
    _row("77XV005", line_no='P7705-3"(XC0KL-A)-N'),                          # split into 77XV005A · 77XV005B
    _row("77XV006", line_no='P7706-3"(XC0KL-A)-N')]),                         # gone
    ("Process Data for Motor Operated Valve", [_row("77MOV001", line_no='P7790-6"(XC0KL-A)-N')])]
NEW = [("Process Data for On-Off Valve", [
    _row("77XV001", line_no='P7701-6(XC0K8)N', piping_class="XC0K8", valve_size='4"', op_temp="50.50"),
    _row("77XV002", line_no='P7702 - 4"(XC0KL-A)-N', line_size="4''", valve_size='4"'),
    _row("77XV003", line_no='P7781-2(XC0K8)N', pid_no="777-98-PR-PID-00058", line_size='2"', valve_size='2"', piping_class="XC0K8",
         design_temp="60.00"),
    _row("77XV104", line_no='P7704-2(XC0K8)N', line_size='2"', valve_size='2"', piping_class="XC0K8"),
    _row("77XV005A", line_no='P7705-3"(XC0KL-A)-N', design_pressure="FV/154.00"),
    _row("77XV005B", line_no='P7705-3"(XC0KL-A)-N'),
    _row("77XV103", line_no='P7703-8"(XC0K8)-N', pid_no="777-98-PR-PID-00012", line_size='8"', piping_class="XC0K8"),
    _row("77XV200", line_no='P7799-2"(XC0KL-A)-N', line_size='2"', valve_size='2"')])]


def _parse(tmp_path, name, data):
    from app.valve import process
    f = tmp_path / name
    f.write_bytes(data)
    return process.read_process_data(str(f))


def test_reader_takes_rules_drawn_cell_by_cell_and_rows_by_their_rules(tmp_path):
    P = _parse(tmp_path, "old.pdf", _pds(OLD, "B"))
    assert P["n_tags"] == 7 and P["doc_no"] == DN and P["rev"] == "B" and P["v"] >= 2
    r = P["by_tag"]["77XV002"]["values"]
    assert r["location"]["v"] == "FIRST LINE OF SERVICE SECOND LINE THIRD LINE"     # no line of the next row, none lost
    assert r["line_no"]["v"] == 'P7702-4"(XC0KL-A)-N' and r["piping_class"]["v"] == "XC0KL-A" and r["fluid"]["v"] == "CO2"


def test_judge_levels():
    from app.valve.pdsrev import judge
    assert judge("valve_size", '18"', "18'") is None and judge("line_no", 'P1-6"(X)-N', "P1-6(X)N") is None
    assert judge("valve_size", '6"', '4"') == "High" and judge("design_temp", "213.00", "209.00") == "Med"    # ≤ 2 %: one lower
    assert judge("op_temp", "55.90", "57.00") == "Min" and judge("op_pressure", "127.99", "133.00") == "Med"
    assert judge("piping_class", "XC0KL-A", "XC0K8") == "Med" and judge("piping_class", "YC0KL-N", "XC0K8") == "High"
    assert judge("design_pressure", "98", "FV/98.00") == "Min" and judge("op_temp", "36.", "36.00") is None
    assert judge("density", "-", "510.83") == "Min" and judge("remarks", "sour service, FV", "sour service,FV") is None


def test_compare_statuses_and_reasons(tmp_path):
    from app.valve import pdsrev
    R = pdsrev.compare(_parse(tmp_path, "o.pdf", _pds(OLD, "B")), _parse(tmp_path, "n.pdf", _pds(NEW, "0", extra=True)))
    st = {(i["tag_key"], i["old_tag"]): i for i in R["items"]}
    a = st[("77XV001", "")]
    assert a["status"] == "Changed" and a["imp"] == {"valve_size": "High", "line_no": "Min", "piping_class": "Med", "op_temp": "Min"}
    assert a["overall"] == "High"
    assert st[("77XV002", "")]["status"] == "No Change"
    assert st[("77XV003", "")]["status"] == "Changed (Tag 재사용 의심)" and "77XV103" in st[("77XV003", "")]["note"]
    assert st[("77XV103", "77XV003")]["status"] == "Tag 변경 의심"
    assert st[("77XV104", "77XV004")]["status"] == "Tag 변경 의심" and "동일 Line" in st[("77XV104", "77XV004")]["note"]
    assert st[("77XV005A", "77XV005")]["status"] == st[("77XV005B", "77XV005")]["status"] == "Tag 변경 의심"
    assert st[("77XV005A", "77XV005")]["imp"] == {"design_pressure": "Min"}                 # only 'FV/' added
    assert st[("77XV200", "")]["status"] == "New" and st[("77XV006", "")]["status"] == "Delete"
    mov = st[("77MOV001", "")]
    assert mov["status"] == "Delete" and "MOV 섹션 미수록" in mov["note"]
    assert R["excluded_columns"] == ["Dense/Supercritical CO2"]                             # only the new Rev. has it: not compared
    assert R["counts"]["old_tags"] == 7 and R["counts"]["new_tags"] == 8


def test_workbook_layout(tmp_path):
    import openpyxl
    from app.valve import pdsrev
    R = pdsrev.compare(_parse(tmp_path, "o.pdf", _pds(OLD, "B")), _parse(tmp_path, "n.pdf", _pds(NEW, "0", extra=True)))
    data = pdsrev.workbook([{"doc_no": DN, "area": "QN", "old_rev": "B", "new_rev": "0", "old_name": "o.pdf", "new_name": "n.pdf", "result": R}])
    wb = openpyxl.load_workbook(io.BytesIO(data))
    assert wb.sheetnames == ["Summary", f"A. {DN}", "High 변경 목록", "Summary (Sizing 영향)"]
    ws = wb[f"A. {DN}"]
    assert [ws.cell(4, c).value for c in (1, 2, 3, 6, 38, 39)] == ["No", "Status", "Tag (Rev.0)", "Row", "중요도(종합)", "비고 / 사유"]
    assert [ws.cell(r, 6).value for r in (5, 6, 7)] == ["이전", "최신", "중요도"] and ws.freeze_panes == "G5"
    assert ws.cell(5, 3).value == "77XV001" and ws.cell(5, 5).value == "Rev.B" and ws.cell(6, 5).value == "Rev.0"
    assert ws.cell(7, 13).value == "High" and ws.cell(6, 13).font.color.rgb.endswith("FF0000") and ws.cell(6, 38).value == "High"
    assert "COUNTIFS" in wb["Summary"].cell(5, 8).value and wb["Summary"].cell(5, 6).value == 7
    hl = wb["High 변경 목록"]
    assert ("77XV001", "Valve Size", '6"', '4"') in {(hl.cell(r, 3).value, hl.cell(r, 5).value, hl.cell(r, 6).value, hl.cell(r, 7).value)
                                                    for r in range(2, hl.max_row + 1)}


def test_upload_same_number_compares_and_gives_the_excel(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.valve import api
    app = FastAPI()
    app.include_router(api.router)
    c = TestClient(app)
    pid = c.post("/api/valve/projects", json={"name": "PDS REV T"}).json()["id"]

    def up(name, data):
        j = c.post(f"/api/valve/projects/{pid}/upload", data={"kind": "process"}, files=[("files", (name, data, "application/pdf"))]).json()
        for _ in range(400):
            if c.get(f"/api/valve/jobs/{j['id']}").json()["status"] == "done":
                return
            time.sleep(0.05)
        raise AssertionError("job did not finish")
    assert c.get(f"/api/valve/projects/{pid}/pds_revcompare.xlsx").status_code == 404
    up(f"{DN}_B.pdf", _pds(OLD, "B"))
    up(f"{DN}_0001_0_Advanced_Copy.pdf", _pds(NEW, "0", extra=True))
    docs = {d["filename"]: d for d in c.get(f"/api/valve/projects/{pid}/summary").json()["documents"] if d["kind"] == "process"}
    rc = docs[f"{DN}_0001_0_Advanced_Copy.pdf"]["info"]["revcompare"]
    assert (rc["old_rev"], rc["new_rev"]) == ("B", "0") and rc["counts"]["New"] == 1 and rc["counts"]["Delete"] == 2
    assert "이전" in docs[f"{DN}_0001_0_Advanced_Copy.pdf"]["info"]["note"]
    r = c.get(f"/api/valve/projects/{pid}/pds_revcompare.xlsx")
    assert r.status_code == 200 and r.headers["x-count"] == "1"
    con = api.store.connect()
    P, _ = api._process_for(con, pid)
    assert "77XV200" in P["by_tag"] and "77XV006" not in P["by_tag"]                         # the newest Rev. is what the review uses
