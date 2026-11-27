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
    _row("77XV003", line_no='P7703-8"(YC0KL-N)-N', pid_no="777-98-PR-PID-00012", line_size='8"', piping_class="YC0KL-N"),   # → another line
    _row("77XV004", line_no='P7704-2"(XC0KL-A)-N', line_size='2"', valve_size='2"'),     # gone (77XV104 is new on its line)
    _row("77XV005", line_no='P7705-3"(XC0KL-A)-N'),                          # gone (77XV005A · 77XV005B are new)
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


def test_compare_statuses_no_tag_guessing(tmp_path):
    """valve44 (user 2026-11-26): which tag became which is never guessed — only the same number is compared."""
    from app.valve import pdsrev
    R = pdsrev.compare(_parse(tmp_path, "o.pdf", _pds(OLD, "B")), _parse(tmp_path, "n.pdf", _pds(NEW, "0", extra=True)))
    st = {i["tag_key"]: i for i in R["items"]}
    a = st["77XV001"]
    assert a["status"] == "Changed" and a["imp"] == {"valve_size": "High", "line_no": "Min", "piping_class": "Med", "op_temp": "Min"}
    assert a["overall"] == "High"
    assert st["77XV002"]["status"] == "No Change"
    assert st["77XV003"]["status"] == "Changed" and st["77XV003"]["note"] == ""        # another line now: still just Changed
    # on the same line as a gone tag · a letter added · a new number: all New; every number the new Rev. lacks: Delete
    assert {k for k, i in st.items() if i["status"] == "New"} == {"77XV104", "77XV005A", "77XV005B", "77XV103", "77XV200"}
    assert {k for k, i in st.items() if i["status"] == "Delete"} == {"77XV004", "77XV005", "77XV006", "77MOV001"}
    assert all(i["note"] == "" for i in R["items"] if i["status"] == "New")
    assert "MOV 섹션 미수록" in st["77MOV001"]["note"]
    assert {i["status"] for i in R["items"]} == {"Changed", "No Change", "New", "Delete"}
    assert R["excluded_columns"] == ["Dense/Supercritical CO2"]                             # only the new Rev. has it: not compared
    assert R["counts"]["old_tags"] == 7 and R["counts"]["new_tags"] == 8


def _book(tmp_path, lang):
    import openpyxl
    from app.valve import pdsrev
    R = pdsrev.compare(_parse(tmp_path, "o.pdf", _pds(OLD, "B")), _parse(tmp_path, "n.pdf", _pds(NEW, "0", extra=True)))
    data = pdsrev.workbook([{"doc_no": DN, "area": "QN", "old_rev": "B", "new_rev": "0", "old_name": "o.pdf", "new_name": "n.pdf", "result": R}], lang)
    return openpyxl.load_workbook(io.BytesIO(data))


def test_workbook_layout_v2_korean(tmp_path):
    """valve45: the engineers' v2 layout — No · Status · Tag · (예비) · Rev. · Row, three rows per tag, No · Status · Tag ·
    overall importance on the first row only (No · overall · remarks merged over the three rows)."""
    wb = _book(tmp_path, "ko")
    assert wb.sheetnames == ["Summary", f"A. {DN}", "High 변경 목록", "Summary (Sizing 영향)"]
    ws = wb[f"A. {DN}"]
    assert [ws.cell(4, c).value for c in (1, 2, 3, 4, 5, 6, 38, 39)] == ["No", "Status", "Tag", "이전 Tag", "Rev.", "Row", "중요도(종합)", "비고 / 사유"]
    assert [ws.cell(r, 6).value for r in (5, 6, 7)] == ["이전", "최신", "중요도"] and ws.freeze_panes == "G5"
    assert (ws.cell(5, 2).value, ws.cell(5, 3).value, ws.cell(5, 38).value) == ("Changed", "77XV001", "High")
    assert ws.cell(6, 2).value is None and ws.cell(6, 3).value is None                     # first row only
    assert {"A5:A7", "AL5:AL7", "AM5:AM7"} <= {str(m) for m in ws.merged_cells.ranges}
    assert ws.cell(5, 5).value == "Rev.B" and ws.cell(6, 5).value == "Rev.0"
    assert ws.cell(7, 13).value == "High" and ws.cell(6, 13).font.color.rgb.endswith("FF0000")
    sm = wb["Summary"]
    assert [sm.cell(4, c).value for c in range(1, 13)][4:] == ["이전 Tag 수", "Rev.0 Tag 수", "Changed (High)", "Changed (Med)", "Changed (Min)",
                                                               "No Change", "New", "Delete"]
    assert '"이전"' in sm.cell(5, 7).value and sm.cell(5, 5).value == 7 and sm.cell(5, 6).value == 8
    hl = wb["High 변경 목록"]
    assert ("77XV001", "Valve Size", '6"', '4"') in {(hl.cell(r, 3).value, hl.cell(r, 5).value, hl.cell(r, 6).value, hl.cell(r, 7).value)
                                                    for r in range(2, hl.max_row + 1)}
    assert not any("변경 의심" in str(c.value or "") for w in wb for row in w.iter_rows() for c in row)


def test_workbook_english_same_layout(tmp_path):
    ko, en = _book(tmp_path, "ko"), _book(tmp_path, "en")
    assert en.sheetnames == ["Summary", f"A. {DN}", "High Changes", "Summary (Sizing Impact)"]
    ws = en[f"A. {DN}"]
    assert [ws.cell(4, c).value for c in (4, 38, 39)] == ["Previous Tag", "Overall Importance", "Remarks / Reason"]
    assert [ws.cell(r, 6).value for r in (5, 6, 7)] == ["Previous", "Latest", "Importance"]
    assert '"Previous"' in en["Summary"].cell(5, 7).value and '"Importance"' in en["Summary (Sizing Impact)"].cell(7, 4).value
    k, e = ko[f"A. {DN}"], ws                                                              # the same cells, the same values
    assert all(k.cell(r, c).value == e.cell(r, c).value for r in range(5, k.max_row + 1) for c in range(7, 38)
               if k.cell(r, 6).value != "중요도" and not str(k.cell(r, c).value or "").startswith("("))
    hangul = [c.value for w in en for row in w.iter_rows() for c in row
              if isinstance(c.value, str) and any("\uac00" <= ch <= "\ud7a3" for ch in c.value)]
    assert hangul == []                                                                    # no Korean left in the English book


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
    assert (rc["old_rev"], rc["new_rev"]) == ("B", "0") and rc["counts"]["New"] == 5 and rc["counts"]["Delete"] == 4
    assert "이전" in docs[f"{DN}_0001_0_Advanced_Copy.pdf"]["info"]["note"]
    r = c.get(f"/api/valve/projects/{pid}/pds_revcompare.xlsx")
    assert r.status_code == 200 and r.headers["x-count"] == "1" and "_KO_" in r.headers["content-disposition"]
    r = c.get(f"/api/valve/projects/{pid}/pds_revcompare.xlsx?lang=en")
    assert r.status_code == 200 and "_EN_" in r.headers["content-disposition"]
    con = api.store.connect()
    P, _ = api._process_for(con, pid)
    assert "77XV200" in P["by_tag"] and "77XV006" not in P["by_tag"]                         # the newest Rev. is what the review uses


def test_pds_menu_endpoints(tmp_path, monkeypatch):
    """valve46 (user 2026-11-27: 'PDS 분석 메뉴'): PDS 현황 · Tag 목록 · Rev. 비교 (any two Revs.) · Excel of one number."""
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.valve import api
    app = FastAPI()
    app.include_router(api.router)
    c = TestClient(app)
    pid = c.post("/api/valve/projects", json={"name": "PDS MENU T"}).json()["id"]

    def up(name, data):
        j = c.post(f"/api/valve/projects/{pid}/upload", data={"kind": "process"}, files=[("files", (name, data, "application/pdf"))]).json()
        for _ in range(400):
            if c.get(f"/api/valve/jobs/{j['id']}").json()["status"] == "done":
                return
            time.sleep(0.05)
        raise AssertionError("job did not finish")
    up(f"{DN}_B.pdf", _pds(OLD, "B"))
    s = c.get(f"/api/valve/projects/{pid}/pds/summary").json()
    assert s["totals"] == {"documents": 1, "uploads": 1, "tags": 7, "revised": 0} and s["documents"][0]["compare"] is None
    assert s["documents"][0]["revs"][0]["sections"] == {"On-Off": 6, "MOV": 1}
    assert c.get(f"/api/valve/projects/{pid}/pds/compare", params={"doc_no": DN}).status_code == 404
    up(f"{DN}_C.pdf", _pds(NEW, "C", extra=True))
    up(f"{DN}_0001_0_Advanced_Copy.pdf", _pds(NEW, "0", extra=True))
    s = c.get(f"/api/valve/projects/{pid}/pds/summary").json()
    d = s["documents"][0]
    assert [r["rev"] for r in d["revs"]] == ["0", "C", "B"] and d["compare"]["counts"]["No Change"] == 8          # 0 vs C: same values
    t = c.get(f"/api/valve/projects/{pid}/pds/tags").json()
    assert len(t["rows"]) == 8 and {r["rev"] for r in t["rows"]} == {"0"} and any(f["key"] == "valve_size" for f in t["fields"])
    ids = {r["rev"]: r["id"] for r in d["revs"]}
    cm = c.get(f"/api/valve/projects/{pid}/pds/compare", params={"doc_no": DN, "old": ids["B"], "new": ids["0"]}).json()
    assert (cm["old"]["rev"], cm["new"]["rev"]) == ("B", "0") and cm["counts"]["New"] == 5 and cm["counts"]["Delete"] == 4
    one = next(i for i in cm["items"] if i["tag"] == "77XV001")
    assert one["imp"]["valve_size"] == "High" and one["old"]["valve_size"] == '6"' and one["new"]["valve_size"] == '4"'
    assert "MOV" in next(i for i in cm["items"] if i["tag"] == "77MOV001")["note"]
    r = c.get(f"/api/valve/projects/{pid}/pds_revcompare.xlsx", params={"lang": "en", "doc_no": DN, "old": ids["B"], "new": ids["0"]})
    assert r.status_code == 200 and r.headers["x-count"] == "1"


def test_pds_page_is_wired():
    from pathlib import Path
    js = Path("app/static/valve/pds.js").read_text(encoding="utf-8")
    vjs = Path("app/static/valve/valve.js").read_text(encoding="utf-8")
    assert "'pds'" in js and "PDS 현황" in js and "Rev. 비교" in js and "window.PDS = " in js
    assert "PDSV = ['pdash', 'psum', 'ptags', 'pcmp']" in vjs and "window.PDS?.render" in vjs
    assert '<script src="pds.js"></script>' in Path("app/static/valve/index.html").read_text(encoding="utf-8")
    dash = Path("dashboard/dashboard.html").read_text(encoding="utf-8")
    assert "kind=pds" in dash and "'pdsv'" in dash


def test_change_summary_counts(tmp_path):
    """valve48 (user 2026-11-27: '변경 summary 도 별도로'): the Summary and Sizing sheets' numbers, computed once for the screen."""
    from app.valve import pdsrev
    X = pdsrev.change_summary(pdsrev.compare(_parse(tmp_path, "o.pdf", _pds(OLD, "B")), _parse(tmp_path, "n.pdf", _pds(NEW, "0", extra=True))))
    c = X["counts"]
    assert (c["old_tags"], c["new_tags"], c["New"], c["Delete"], c["No Change"]) == (7, 8, 5, 4, 1)
    sz = X["sizing"]
    assert sz["valve_size"] == ["77XV001", "77XV003"] and sz["line_size"] == ["77XV003"] and sz["delete_mov"] == ["77MOV001"]
    assert sz["class_rating"] == ["77XV003"] and sz["class_scheme"] == ["77XV001"]          # YC0KL-N → XC0K8 · XC0KL-A → XC0K8
    assert {r["tag"] for r in X["size"]} == {"77XV001", "77XV003"} and all(r["new"] for r in X["high"])
    assert [k for k, *_ in pdsrev.SIZING][:3] == ["line_size", "valve_size", "bore"]


def test_user_link_makes_a_tag_change(tmp_path):
    """valve49 (user 2026-11-27): the engineer names a New tag's earlier tag (a Delete) → 'Tag 변경', compared and counted."""
    import openpyxl
    from app.valve import pdsrev
    o, n = _parse(tmp_path, "o.pdf", _pds(OLD, "B")), _parse(tmp_path, "n.pdf", _pds(NEW, "0", extra=True))
    links = {"77XV104": {"old": "77XV004", "by": "eng", "at": "2026-11-27T10:00:00"},
             "77XV200": {"old": "77XV001"}}                                                   # 77XV001 is not a Delete: ignored
    R = pdsrev.compare(o, n, links)
    st = {i["tag_key"]: i for i in R["items"]}
    t = st["77XV104"]
    assert t["status"] == "Tag 변경" and t["old_tag"] == "77XV004" and t["imp"] == {"line_no": "Min", "piping_class": "Med"} and "eng" in t["note"]
    assert "77XV004" not in st and st["77XV200"]["status"] == "New"
    assert (R["counts"]["Tag 변경"], R["counts"]["New"], R["counts"]["Delete"]) == (1, 4, 3)
    X = pdsrev.change_summary(R)
    assert X["counts"]["Tag 변경"] == 1 and X["sizing"]["renamed"] == ["77XV104"] and X["renamed"][0]["old_tag"] == "77XV004"
    wb = openpyxl.load_workbook(io.BytesIO(pdsrev.workbook([{"doc_no": DN, "area": "", "old_rev": "B", "new_rev": "0", "old_name": "o", "new_name": "n", "result": R}])))
    ws = wb[f"A. {DN}"]
    row = next(r for r in range(5, ws.max_row + 1) if ws.cell(r, 3).value == "77XV104")
    assert (ws.cell(row, 2).value, ws.cell(row, 4).value) == ("Tag 변경", "77XV004")
    sm = wb["Summary"]
    assert sm.cell(4, 13).value == "Tag 변경" and "Tag 변경" in sm.cell(5, 13).value and "Tag 변경" in sm.cell(5, 7).value


def test_link_api_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.valve import api
    app = FastAPI()
    app.include_router(api.router)
    c = TestClient(app)
    pid = c.post("/api/valve/projects", json={"name": "PDS LINK T"}).json()["id"]

    def up(name, data):
        j = c.post(f"/api/valve/projects/{pid}/upload", data={"kind": "process"}, files=[("files", (name, data, "application/pdf"))]).json()
        for _ in range(400):
            if c.get(f"/api/valve/jobs/{j['id']}").json()["status"] == "done":
                return
            time.sleep(0.05)
    up(f"{DN}_B.pdf", _pds(OLD, "B"))
    up(f"{DN}_0001_0_Advanced_Copy.pdf", _pds(NEW, "0", extra=True))
    r = c.put(f"/api/valve/projects/{pid}/pds/links", json={"doc_no": DN, "new_tag": "77XV-104", "old_tag": "77XV004"}).json()
    assert r["links"]["77XV104"]["old"] == "77XV004"
    cm = c.get(f"/api/valve/projects/{pid}/pds/compare", params={"doc_no": DN}).json()
    assert next(i for i in cm["items"] if i["tag"] == "77XV104")["status"] == "Tag 변경" and cm["counts"]["Delete"] == 3
    cs = c.get(f"/api/valve/projects/{pid}/pds/change_summary").json()
    assert cs["documents"][0]["counts"]["Tag 변경"] == 1 and any(r["key"] == "renamed" for r in cs["sizing_rows"])
    assert c.get(f"/api/valve/projects/{pid}/pds/summary").json()["documents"][0]["compare"]["counts"]["Tag 변경"] == 1
    c.put(f"/api/valve/projects/{pid}/pds/links", json={"doc_no": DN, "new_tag": "77XV104", "old_tag": ""})
    cm = c.get(f"/api/valve/projects/{pid}/pds/compare", params={"doc_no": DN}).json()
    assert next(i for i in cm["items"] if i["tag"] == "77XV104")["status"] == "New" and cm["counts"]["Delete"] == 4


def test_xgrid_is_light_and_alive():
    """valve50 (user 2026-11-27: '모든 셀이 살아 있어야 하고 매우 가볍게'): the PDS screens draw on xgrid.js — only the rows and
    columns on screen, every cell selectable · keyboard · Ctrl+C · name box / formula bar."""
    from pathlib import Path
    g = Path("app/static/valve/xgrid.js").read_text(encoding="utf-8")
    for must in ("requestAnimationFrame", "ArrowUp", "copy()", "xgname", "xgfx", "data-rz", "selectAll", "setRows", "destroy",
                 "'wheel'", "xgjump", "xgl1", "xgr1", "e.altKey && (k === 'PageDown'",             # valve53: side movement
                 "function setFreeze", "xgfreeze", "xgfzb", "localStorage.setItem(FK", "xfzl"):    # valve54: freeze panes
        assert must in g, must
    js = Path("app/static/valve/pds.js").read_text(encoding="utf-8")
    assert js.count("grid('") >= 4 and "window.XGrid(host, { key: 'pds.' + id, ...opt })" in js
    html = Path("app/static/valve/index.html").read_text(encoding="utf-8")
    assert html.index('xgrid.js') < html.index('pds.js')
