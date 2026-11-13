"""valve40 — Instrument review: Line List · List reading · number parsing · the planted-error scenario over all 14 forms
(test data drawn from the cards only; nothing from a client)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "spike"))


def test_nums_and_quantity():
    from app.valve import instreview as R
    assert R.nums("0-25 barg") == [0, 25] and R.nums("0 - 25") == [0, 25]
    assert R.nums("85 -29 degC") == [85, -29] and R.nums("120 m3/h") == [120] and R.nums("CL300") == []
    q = R.quantity({"value": "", "sub": {"Max": "12", "Nor": "10.5", "Min": "8", "Unit": "barg"}})
    assert (q["max"], q["nor"], q["min"], q["unit"]) == (12, 10.5, 8, "barg")
    q = R.quantity({"value": "8 / 10.5 / 12 barg"})                    # min/nor/max order on some forms
    assert (q["max"], q["min"]) == (12, 8)


def test_linelist_swapped_size_columns(tmp_path):
    import valve_inst_scenario as SC
    from app.valve import linelist
    p = tmp_path / "ll.xlsx"
    SC.write_linelist(p, south_swap=True)
    ll = linelist.read(p.read_bytes(), "ll.xlsx")
    assert len(ll["lines"]) == 2
    a = ll["lines"][0]
    assert a["size_inch"] == '6"' and a["size_mm"] == "150" and a["pipe_class"] == "TC1A" and a["design_p"] == "3.5"
    row, how = linelist.find(ll, 'TS1001-6"-TC1A-N')
    assert row is a and how == ""
    row, how = linelist.find(ll, "TS-1001")                           # only the start of the number
    assert row is a and "앞부분" in how


def test_list_reader_round_trip(tmp_path):
    import valve_make_test_list as ML
    from app.valve import instlists
    recs = [{"tag": "71PT-9001A", "service": "TEST SERVICE", "pid_no": "TEST-PID-1", "range_min": "0", "range_max": "25", "range_unit": "barg",
             "manufacturer": "TEST MFR", "model": "M-1", "datasheet_no": "TEST-IN-DS-0601"},
            {"tag": "71FT-9100", "service": "TEST FLOW", "pid_no": "TEST-PID-2"}]
    for kind in ("instrument_index", "io_list"):
        d = ML.synthetic(kind)
        ML.fill(d, kind, recs)
        p = tmp_path / f"{kind}.pdf"
        d.save(p)
        r = instlists.read_pdf(str(p))
        assert r["kind"] == kind and r["n_tags"] == 2
        a = r["by_tag"]["71PT9001A"]
        assert a["service"] == "TEST SERVICE" and a["pid_no"] == "TEST-PID-1" and a["range"] == "0 ~ 25 barg"
    ds = [{"tag": "71PT-9001A", "tag_key": "71PT9001A", "kind": "pt", "values": {"service": "OTHER", "range": "0-25 barg"}},
          {"tag": "71LT-1", "tag_key": "71LT1", "kind": "lt", "values": {}}]
    rows = instlists.compare(ds, r, "IO List")
    res = {(x["rule"], x["tag"], x["field"]): x["result"] for x in rows}
    assert res[("LIST-01", "71PT-9001A", "Service")] == "값 다름" and res[("LIST-01", "71PT-9001A", "Range")] == "OK"
    assert res[("LIST-00", "71LT-1", "Tag")] == "누락" and res[("LIST-02", "71FT-9100", "Tag")] == "List 에만"


def test_scenario_all_forms_planted_errors(tmp_path):
    """Every form: clean tag → no finding; planted errors → each found; List errors → each found (through the real API)."""
    import valve_inst_scenario as SC
    out = SC.main([str(tmp_path / "scen")])
    assert not out["errors"], out["errors"]
    t = out["total"]
    assert t["expected"] >= 70 and t["missed"] == 0 and t["extra"] == 0, [f for f in out["forms"] if f["missed"] or f["extra"]]
    assert out["list"]["missed"] == [] and out["list"]["extra"] == []
    assert out["summary_total"]["tags"] == 28 and out["summary_total"]["ok_tags"] == 14


def test_markup_pdf_shading_and_callouts(tmp_path, monkeypatch):
    """Findings go INTO the PDF: a shaded Square on the cell + a FreeText callout (leader line + arrow) with the reason."""
    import pymupdf
    import valve_inst_scenario as SC
    SC.main([str(tmp_path / "scen"), "--keep"])
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "scen" / "data"))
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    rows = c.get("/api/valve/projects/1/inst/sheets?kind=pt").json()["rows"]
    bad = next(r for r in rows if r["tag"].endswith("B"))
    r = c.get(f"/api/valve/inst/sheets/{bad['id']}/markup.pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    d = pymupdf.open("pdf", r.content)
    pg = d[0]
    ann = list(pg.annots())
    calls = [a for a in ann if a.type[1] == "FreeText"]
    shades = [a for a in ann if a.type[1] == "Square" and "shading" in a.info["subject"]]
    assert len(calls) == bad["issues"] and len(shades) >= bad["issues"] - 1
    xr = calls[0].xref
    assert d.xref_get_key(xr, "IT")[1] == "/FreeTextCallout" and d.xref_get_key(xr, "LE")[1] == "/OpenArrow"
    assert any("IN-LL-02" in a.info["subject"] for a in calls)
    assert pg.rect.width > 595 + 200                       # widened for the callout column
    # item screens: one reference at a time (PDS · PMS · Line List) + revision compare
    f = c.get("/api/valve/projects/1/inst/findings?kind=pt&group=pds").json()
    assert f["ref"] == "TEST_PDS.pdf" and f["counts"].get("Mismatch") == 1 and all(x["rule"].startswith("IN-PDS") for x in f["rows"])
    ll = c.get("/api/valve/projects/1/inst/findings?kind=pt&group=line").json()
    assert {x["rule"] for x in ll["rows"] if x["result"] == "Mismatch"} == {"IN-LL-01", "IN-LL-02", "IN-LL-03"}
    good = next(r for r in rows if r["tag"].endswith("A"))
    cmp_ = c.get(f"/api/valve/inst/compare?prev={good['id']}&new={bad['id']}").json()
    assert any(x["std_key"] == "piping_class" and x["change"] == "Modified" for x in cmp_["rows"])
    assert bad["vals"]["design_pressure"] and "area" in bad
    # Instrument List / IO List cover Valve tags too: a Valve datasheet of the same project that the list does not have
    import time
    from tests.test_valve import make_pdf
    j = c.post("/api/valve/projects/1/upload", data={"kind": "datasheet"}, files=[("files", ("ds.pdf", make_pdf()))]).json()
    for _ in range(300):
        if c.get(f"/api/valve/jobs/{j['id']}").json()["status"] == "done":
            break
        time.sleep(0.1)
    lc = c.get("/api/valve/projects/1/inst/listcmp?list=instrument_index").json()
    vr = [x for x in lc["rows"] if x.get("valve_ds")]
    assert lc["n_valve"] >= 1 and lc["n_inst"] == 28 and vr and vr[0]["kind"] == "ball" and vr[0]["rule"] == "LIST-00" and vr[0]["result"] == "누락"
    # document · revision register: latest uploaded vs latest reviewed, Valve + Instrument + reference documents
    c.put(f"/api/valve/inst/sheets/{good['id']}/status", json={"status": "Accepted"}, headers={"X-Author": "tester"})
    reg = c.get("/api/valve/docreg?project=TEST%20INSTRUMENT").json()
    by = {(r["kind"], r["tag"]): r for r in reg["rows"]}
    g = by[("pt", good["tag"])]
    assert g["reviewed"]["rev"] == g["latest"]["rev"] == "A" and g["reviewed"]["reviewed_by"] == "tester" and not g["pending"] and g["link"]["sheet"] == good["id"]
    assert by[("pt", bad["tag"])]["pending"] and by[("pt", bad["tag"])]["reviewed"] is None
    assert any(r["kind"] == "ball" and r["link"].get("ds") for r in reg["rows"])
    assert {"instindex", "iolist", "pms", "pds", "linelist"} <= {r["kind"] for r in reg["rows"]} and reg["counts"]["reviewed"] == 1
    allp = c.get("/api/valve/projects/1/inst/markup.pdf")
    assert allp.status_code == 200 and pymupdf.open("pdf", allp.content).get_toc()[0][1] == "Summary"


def test_engineer_decisions_codes_crs_and_open_items(tmp_path, monkeypatch):
    """Dismiss / modify / confirm a finding, carry it to the next Rev, review code + suggestion, CRS Excel, HOLD rule."""
    import io
    import time
    import openpyxl
    import pymupdf
    import valve_inst_scenario as SC
    import valve_make_test_ds as M
    from app.valve import instrument
    SC.main([str(tmp_path / "scen"), "--keep"])
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "scen" / "data"))
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    H = {"X-Author": "engineer"}
    bad = next(r for r in c.get("/api/valve/projects/1/inst/sheets?kind=pt").json()["rows"] if r["tag"].endswith("B"))
    d = c.get(f"/api/valve/inst/sheets/{bad['id']}").json()
    assert d["suggested_code"] == "2" and d["review_code"] == "" and [x["code"] for x in d["codes"]] == ["1", "2", "3", "4", "5"]
    open_ = [x for x in d["review"] if x["result"] in ("Mismatch", "Missing", "Review Required")]
    n0 = d["issues"]
    pms = next(x for x in open_ if x["rule"] == "IN-PMS-01")
    # dismiss needs a reason
    assert c.put(f"/api/valve/inst/sheets/{bad['id']}/decisions", json={"fkey": pms["fkey"], "decision": "Dismissed"}, headers=H).status_code == 400
    assert c.put(f"/api/valve/inst/sheets/{bad['id']}/decisions", json={"fkey": pms["fkey"], "decision": "Dismissed", "reason_cat": "Project specification exception"}, headers=H).status_code == 200
    ll = next(x for x in open_ if x["rule"] == "IN-LL-02")
    c.put(f"/api/valve/inst/sheets/{bad['id']}/decisions", json={"fkey": ll["fkey"], "decision": "Modified", "text": "Design pressure shall be 3.5 barg min. per line list."}, headers=H)
    pds = next(x for x in open_ if x["rule"] == "IN-PDS-01")
    c.put(f"/api/valve/inst/sheets/{bad['id']}/decisions", json={"fkey": pds["fkey"], "decision": "Confirmed"}, headers=H)
    d = c.get(f"/api/valve/inst/sheets/{bad['id']}").json()
    by = {x.get("fkey"): x for x in d["review"]}
    assert by[pms["fkey"]]["result"] == "Dismissed" and d["issues"] == n0 - 1
    assert by[ll["fkey"]]["reason"].startswith("Design pressure shall") and by[pds["fkey"]]["decision"]["decision"] == "Confirmed"
    # review code
    assert c.put(f"/api/valve/inst/sheets/{bad['id']}/code", json={"code": "9"}, headers=H).status_code == 400
    assert c.put(f"/api/valve/inst/sheets/{bad['id']}/code", json={"code": "2"}, headers=H).json()["review_code"] == "2"
    # mark-up PDF: dismissed finding left out, modified wording used
    pg = pymupdf.open("pdf", c.get(f"/api/valve/inst/sheets/{bad['id']}/markup.pdf").content)[0]
    texts = [a.info["content"] for a in pg.annots() if a.type[1] == "FreeText"]
    assert len(texts) == d["issues"] and not any("[IN-PMS-01]" in t for t in texts) and any("Design pressure shall be 3.5" in t for t in texts)
    # CRS: one row per open comment, engineer wording, code
    wb = openpyxl.load_workbook(io.BytesIO(c.get("/api/valve/projects/1/inst/crs.xlsx?kind=pt").content))
    ws = wb["CRS"]
    hdr = [x.value for x in ws[3]]
    rows = [dict(zip(hdr, [x.value for x in r])) for r in ws.iter_rows(min_row=4) if r[0].value]
    mine = [r for r in rows if r["Tag"] == bad["tag"]]
    assert len(mine) == d["issues"] and all(r["Review Code"].startswith("2") for r in mine)
    assert any(r["Comment (EN)"].startswith("Design pressure shall") for r in mine) and not any(r["Rule"] == "IN-PMS-01" for r in mine)
    assert "Vendor Reply" in hdr and wb["Review Codes"].max_row >= 3
    # a Rev B of the same tag (still wrong) inherits the decisions, marked with their origin; HOLD left in a cell → IN-OPN-01
    card = instrument.cards()["601"]
    rows_b = SC.build_sheet(card, "pt", bad["tag"], "TEST SERVICE PT", True, "manufacturer")
    rows_b[1]["21"] = "HOLD"
    doc = M.synthetic(card)
    for blk, rv in rows_b.items():
        M.fill(doc, dict(card, items=[i for i in card["items"] if i["block"] == blk]), {"rows": rv, "title": {"doc_no": "TEST-IN-DS-601B", "rev": "B"}})
    j = c.post("/api/valve/projects/1/upload", data={"kind": "instrument"}, files=[("files", ("revb.pdf", doc.tobytes()))]).json()
    for _ in range(300):
        if c.get(f"/api/valve/jobs/{j['id']}").json()["status"] == "done":
            break
        time.sleep(0.1)
    nb = next(r for r in c.get("/api/valve/projects/1/inst/sheets?kind=pt").json()["rows"] if r["tag"] == bad["tag"])
    assert nb["rev"] == "B" and nb["id"] != bad["id"]
    db = c.get(f"/api/valve/inst/sheets/{nb['id']}").json()
    byb = {x.get("fkey"): x for x in db["review"]}
    assert byb[pms["fkey"]]["result"] == "Dismissed" and byb[pms["fkey"]]["decision"]["origin"] == "Rev A"
    assert any(x["rule"] == "IN-OPN-01" and x["result"] == "Review Required" for x in db["review"])
    # project review-code set
    assert c.put("/api/valve/projects/1/inst/codes", json={"codes": [{"code": "A", "label": "Approved"}, {"code": "A", "label": "x"}]}, headers=H).status_code == 400
    assert c.put("/api/valve/projects/1/inst/codes", json={"codes": [{"code": "A", "label": "Approved"}, {"code": "B", "label": "Approved with comments"}]}, headers=H).status_code == 200
    assert [x["code"] for x in c.get("/api/valve/projects/1/inst/codes").json()["codes"]] == ["A", "B"]


def _sheet_from(fid, rows_by_block, tmp_path, name):
    import valve_make_test_ds as M
    from app.valve import instrument
    card = instrument.cards()[fid]
    doc = M.synthetic(card)
    for blk, rv in rows_by_block.items():
        M.fill(doc, dict(card, items=[i for i in card["items"] if i["block"] == blk]), {"rows": rv, "title": {"doc_no": "TEST-" + fid, "rev": "A"}})
    p = tmp_path / name
    doc.save(p)
    return instrument.read_pdf(str(p), name)["sheets"][0]


def test_control_valve_sizing_checks(tmp_path):
    """Form 101 read back from a PDF: rated Cv vs calculated, gas Cv recomputed per IEC 60534-2-1, choked flow, noise."""
    from app.valve import instcalc, instreview, instrument
    cv, x, choked = instcalc.gas_cv(10000, 10, 8, 313.15, 44, 1.3, 0.95, 0.7)
    assert abs(cv - 68.35) < 0.1 and abs(x - 0.2) < 1e-9 and not choked
    mk = lambda mx, nr, mn, u: {"Max": mx, "Nor": nr, "Min": mn, "Unit": u}   # noqa: E731
    sh = _sheet_from("101", {
        1: {"1": "71FV-0001", "46": "100"},
        2: {"8": mk("Vapor", "Vapor", "Vapor", ""), "10": mk("10000", "8000", "800", "kg/h"), "11": mk("8.99", "8.99", "8.99", "barg"),
            "12": mk("6.99", "6.99", "6.99", "barg"), "13": mk("40", "40", "40", "degC"), "15": mk("44", "44", "44", ""),
            "17": mk("1.3", "1.3", "1.3", ""), "18": mk("0.95", "0.95", "0.95", ""), "24": mk("0.7", "0.7", "0.7", ""),
            "26": mk("95", "55", "4", ""), "31": "92 dBA", "32": "85 dBA"}}, tmp_path, "cv.pdf")
    assert sh["form_id"] == "101"
    rows = instcalc.cv_checks(instrument.values(sh))
    by = {}
    for r in rows:
        by.setdefault(r["rule"], []).append(r)
    assert any(r["result"] == instreview.REVIEW and "90" not in r["reason"] and "여유" in r["reason"] for r in by["IN-CV-01"])   # 95 % of rated
    assert any("Min Cv" in r["item"] for r in by["IN-CV-01"])                                                               # 4 % of rated
    mx = next(r for r in by["IN-CV-02"] if "Max" in r["item"])
    assert mx["result"] == instreview.REVIEW and "68." in mx["ref"]                                                          # 95 vs 68.3 recomputed
    assert by["IN-CV-04"][0]["result"] == instreview.MISMATCH                                                               # 92 > 85 dBA
    assert all(r["human"] for r in rows)


def test_psv_api526_checks(tmp_path):
    from app.valve import instcalc, instreview, instrument
    sh = _sheet_from("701", {1: {"1": "71PSV-0001", "9": "Conventional", "26": "10 barg", "30": "25 %", "34": "2 barg",
                                 "42": "1.5 in2", "43": "1.287 in2", "44": "1 1/2 J 2"}}, tmp_path, "psv.pdf")
    assert sh["form_id"] == "701"
    vals = instrument.values(sh)
    rows = instcalc.psv_checks(vals, instreview.canonical(vals))
    res = {r["rule"]: r["result"] for r in rows}
    assert res == {"IN-PSV-01": instreview.OK, "IN-PSV-02": instreview.MISMATCH, "IN-PSV-03": instreview.REVIEW, "IN-PSV-04": instreview.REVIEW}
    assert instcalc.API526["J"] == 1.287 and instcalc._area_in2({"value": "830 mm2"}) == 830 / 645.16


def test_crs_round_trip_and_progress(tmp_path, monkeypatch):
    """CRS out → vendor fills Reply / Status → CRS in: replies attach to the comments, Closed leaves the open count;
    weekly progress counts decisions and closed comments."""
    import io
    import openpyxl
    import valve_inst_scenario as SC
    SC.main([str(tmp_path / "scen"), "--keep"])
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "scen" / "data"))
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    H = {"X-Author": "engineer"}
    bad = next(r for r in c.get("/api/valve/projects/1/inst/sheets?kind=ft").json()["rows"] if r["tag"].endswith("B"))
    n0 = bad["issues"]
    d = c.get(f"/api/valve/inst/sheets/{bad['id']}").json()
    f0 = next(x for x in d["review"] if x["result"] == "Mismatch")
    c.put(f"/api/valve/inst/sheets/{bad['id']}/decisions", json={"fkey": f0["fkey"], "decision": "Confirmed"}, headers=H)
    wb = openpyxl.load_workbook(io.BytesIO(c.get("/api/valve/projects/1/inst/crs.xlsx?kind=ft").content))
    ws = wb["CRS"]
    hdr = [x.value for x in ws[3]]
    col = {h: i + 1 for i, h in enumerate(hdr)}
    mine = [r for r in range(4, ws.max_row + 1) if ws.cell(r, col["Tag"]).value == bad["tag"]]
    assert len(mine) == n0 and all("|" in ws.cell(r, col["Ref (do not edit)"]).value for r in mine)
    ws.cell(mine[0], col["Vendor Reply"], "Agreed. Corrected in Rev B.")
    ws.cell(mine[0], col["Status"], "Closed")
    ws.cell(mine[1], col["Vendor Reply"], "Disagree — see calc note.")
    ws.cell(mine[1], col["Ref (do not edit)"], "")                      # vendor wiped the ref: matched by Tag + Rule + Field
    ws.insert_rows(1)                                                   # and added a line on top
    b = io.BytesIO()
    wb.save(b)
    r = c.post("/api/valve/projects/1/inst/crs", files={"file": ("crs_reply.xlsx", b.getvalue())}, headers=H).json()
    assert r["matched"] >= 2 and r["replies"] == 2 and r["closed"] == 1 and not r["unmatched"]
    nb = next(x for x in c.get("/api/valve/projects/1/inst/sheets?kind=ft").json()["rows"] if x["id"] == bad["id"])
    assert nb["issues"] == n0 - 1 and nb["counts"]["Closed"] == 1
    d = c.get(f"/api/valve/inst/sheets/{bad['id']}").json()
    replies = [x["reply"] for x in d["review"] if x.get("reply")]
    assert {y["status"] for y in replies} == {"Closed", "Open"} and any(y["reply"].startswith("Disagree") for y in replies)
    # the next CRS shows the replies; the mark-up PDF leaves the closed one out
    ws2 = openpyxl.load_workbook(io.BytesIO(c.get("/api/valve/projects/1/inst/crs.xlsx?kind=ft").content))["CRS"]
    vals = [[x.value for x in row] for row in ws2.iter_rows(min_row=4)]
    assert any("Agreed. Corrected in Rev B." in (v[col["Vendor Reply"] - 1] or "") and v[col["Status"] - 1] == "Closed" for v in vals)
    # a file that is not a CRS
    bad_file = io.BytesIO()
    openpyxl.Workbook().save(bad_file)
    assert c.post("/api/valve/projects/1/inst/crs", files={"file": ("x.xlsx", bad_file.getvalue())}).status_code == 400
    pr = c.get("/api/valve/projects/1/inst/progress?kind=ft").json()
    assert len(pr["weeks"]) == 12 and pr["weeks"][-1]["decisions"] >= 1 and pr["weeks"][-1]["closed"] == 1 and pr["weeks"][-1]["received"] == 2
    assert pr["now"]["closed"] == 1 and pr["now"]["no_code"] == 2


def test_area_rule_from_tag_prefix():
    """Area learned from the project's own documents: a prefix used on one area decides it; a prefix used on two sites is
    split by the document / P&ID system number; no evidence → no area (with the reason)."""
    from app.valve import arearule as A
    ev = ([{"tag": "98BDV 980002", "doc_no": "98-51-IN-DTS-00002", "zone": "North"}] * 3
          + [{"tag": "98XV 980010", "doc_no": "999-98-IN-DTS-00002", "zone": "South"}] * 2
          + [{"tag": "315MOV 980004", "doc_no": "315-51-IN-DTS-00010", "zone": "W15"},
             {"tag": "19XV 122", "doc_no": "999-19-IN-DTS-00061", "zone": "South Brownfield"},
             {"doc_no": "03-02-PR-DTS-00002", "zone": "North"},
             {"doc_no": "999-98-PR-DTS-00023", "zone": "North · South"}])          # a document naming two areas: no evidence
    r = A.learn(ev)
    assert r["prefix"]["98"] == {"North": 3, "South": 2} and r["prefix"]["315"] == {"W15": 1}
    assert A.area_for(r, "315FT-0001")[0] == "W15" and A.area_for(r, "19PT-11")[0] == "South Brownfield"
    assert A.area_for(r, "98PT-1001", doc_no="98-51-IN-DTS-00009")[0] == "North"
    assert A.area_for(r, "98PT-1001", pid_no="999-98-PR-PID-00012")[0] == "South"
    z, why = A.area_for(r, "98PT-1001")
    assert z == "" and "가를 수 없음" in why
    assert A.area_for(r, "03TT-1")[0] == "North"                                     # unit number leading the documents
    assert A.area_for(r, "71PT-9100") == ("", "Tag 앞 '71' 의 Area 근거가 없음")
    rows = {x["prefix"]: x for x in A.table(r)}
    assert rows["98"]["by_system"] == {"98": "North", "999": "South"} and rows["315"]["area"] == "W15"


def test_shared_reference_documents_one_place_for_the_family(tmp_path, monkeypatch):
    """valve40 (user 2026-11-13): PDS · PMS · Line List · Lists are entered once (공통 자료) and every Valve kind and Instrument
    type of the project family reviews against them — an upload from a Globe page lands on the family's base project."""
    import time
    import valve_inst_scenario as SC
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    from fastapi.testclient import TestClient
    from app.main import app
    from app.valve import api, inst_api, store
    c = TestClient(app)
    base = c.post("/api/valve/projects", json={"name": "TEST FAMILY"}).json()["id"]
    globe = c.post("/api/valve/projects", json={"name": "TEST FAMILY · Globe Valve"}).json()["id"]
    psv = c.post("/api/valve/projects", json={"name": "TEST FAMILY · PSV"}).json()["id"]
    alone = c.post("/api/valve/projects", json={"name": "OTHER · Globe Valve"}).json()["id"]
    con = store.connect()
    assert [api.ref_pid(con, p) for p in (base, globe, psv, alone)] == [base, base, base, alone]
    assert sorted(api.family(con, globe)) == sorted([base, globe, psv])
    SC.write_pds(tmp_path / "pds.pdf", [{"tag": "71PT-9001A", "op": "10.5", "dp": "19.6", "dt": "85"}])
    SC.write_linelist(tmp_path / "ll.xlsx")

    def up(pid, kind, f):
        r = c.post(f"/api/valve/projects/{pid}/upload", data={"kind": kind}, files=[("files", (f.name, f.read_bytes()))]).json()
        for _ in range(300):
            if c.get(f"/api/valve/jobs/{r['id']}").json()["status"] == "done":
                return
            time.sleep(0.05)
    up(globe, "process", tmp_path / "pds.pdf")                    # entered from a Globe page …
    up(base, "linelist", tmp_path / "ll.xlsx")
    rows = store.rows(con, "SELECT project_id, kind FROM document ORDER BY id")
    assert [(r["project_id"], r["kind"]) for r in rows] == [(base, "process"), (base, "linelist")]      # … kept once, on the base project
    for p in (base, globe, psv):                                  # every Valve kind sees both
        s = c.get(f"/api/valve/projects/{p}/summary").json()
        assert s["has_process"], p
        kinds = {d["kind"]: d.get("shared", False) for d in s["documents"]}
        assert kinds == {"process": p != base, "linelist": p != base}
        assert api._process_for(con, p)[0] is not None
        assert inst_api._merged_linelist(con, p)[0] is not None   # and so does every Instrument type
    assert not c.get(f"/api/valve/projects/{alone}/summary").json()["has_process"]     # another family does not


def test_area_rule_table_and_index_area(tmp_path, monkeypatch):
    """valve40 (user 2026-11-13): the engineer's pasted rule table (section = group · 'Tag 접두어 | 건수 | Area | Unit | 메모' ·
    'XS: 98GTD- / 98SD-' lines) and the Instrument Index AREA column re-classify tags into area · sub-area · unit; each table row
    is checked against the Index rows it covers.  Area names here are made up."""
    from app.valve import arearule as A
    text = """1. Greenfield
  o XS: 98GTD- / 98SD-
  o W15: 315GE83xxxxC
2. Brownfield XN (Area 컬럼: AG1 / AG2)
Tag 접두어\t건수\tArea 컬럼\tUnit\tExhibit 6 대응
1, 2\t20 / 20\tAG1\t09\tN1 Train 1, 2
20\t10\tAG2\t33\tN2 Degasser
3. Brownfield XS
| Tag 접두어 | 건수 | Area 컬럼 | Unit | 메모 |
|---|---|---|---|---|
| 19 | 44 | AGS-TR1 | 19 | S1 Train 1 |
| 84 | 24 | AGS-TR1 (17), AGS-TR3 (7) | 84 | Flare |
"""
    rows = A.parse_table(text)
    assert [(r["group"], r["patterns"], r["subs"], r["unit"]) for r in rows] == [
        ("Greenfield", ["98GTD", "98SD"], ["XS"], ""), ("Greenfield", ["315GE83"], ["W15"], ""),
        ("Brownfield XN", ["1", "2"], ["AG1"], "09"), ("Brownfield XN", ["20"], ["AG2"], "33"),
        ("Brownfield XS", ["19"], ["AGS-TR1"], "19"), ("Brownfield XS", ["84"], ["AGS-TR1", "AGS-TR3"], "84")]
    assert rows[-1]["sub_n"] == {"AGS-TR1": 17, "AGS-TR3": 7} and rows[2]["note"] == "N1 Train 1, 2"
    ev = [{"tag": "1-ZLS-090975", "sub": "AG1 BROWNFIELD"}, {"tag": "2-ZLS-090975", "sub": "AG1 BROWNFIELD"},
          {"tag": "2-ZT-090976", "sub": "AG2 BROWNFIELD"},                                     # an Index row the table disagrees with
          {"tag": "84PT-001", "sub": "AGS-TR3"}, {"tag": "71PT-1", "sub": "AX9"},
          {"tag": "01XV-1", "zone": "North Brownfield", "doc_no": "02-08-IN-1"}, {"tag": "19XV-1", "zone": "South Brownfield"},
          {"tag": "71XV-1", "zone": "North"}]
    r = A.learn(ev, rows)
    assert r["alias"] == {"Brownfield XN": "North Brownfield", "Brownfield XS": "South Brownfield"}     # '1' = '01'
    c = A.classify(r, "1-ZLS-090999")
    assert (c["area"], c["sub"], c["unit"], c["note"]) == ("North Brownfield", "AG1", "09", "N1 Train 1, 2")
    assert A.classify(r, "15PT-1")["area"] == "" and A.classify(r, "19PT-9")["sub"] == "AGS-TR1"
    c = A.classify(r, "84PT-001", index_sub="AGS-TR3")                                         # the Index decides the split row
    assert (c["area"], c["sub"]) == ("South Brownfield", "AGS-TR3") and "Index AREA" in c["basis"]
    assert A.classify(r, "84PT-999")["sub"] == "" and "가를 수 없음" in A.classify(r, "84PT-999")["basis"]
    assert A.classify(r, "98GTD-1001")["sub"] == "XS" and A.classify(r, "98GTDX-1")["sub"] != "XS"   # whole letter group only
    assert A.classify(r, "315GE83001C")["sub"] == "W15"
    c = A.classify(r, "71PT-2")                                                                 # no table row: learned from the Index
    assert (c["area"], c["sub"]) == ("North", "AX9")
    chk = {tuple(x["patterns"]): x for x in A.check_table(r)}
    assert (chk[("1", "2")]["n_ok"], chk[("1", "2")]["n_index"], chk[("1", "2")]["other"]) == (2, 3, {"AG2 BROWNFIELD": 1})
    # through the API: saved once per family, read back, every tag re-classified
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    from fastapi.testclient import TestClient
    from app.main import app
    cl = TestClient(app)
    base = cl.post("/api/valve/projects", json={"name": "TEST AREA"}).json()["id"]
    globe = cl.post("/api/valve/projects", json={"name": "TEST AREA · Globe Valve"}).json()["id"]
    assert cl.put(f"/api/valve/projects/{globe}/inst/arearule", json={"text": "nothing here"}).status_code == 400
    j = cl.put(f"/api/valve/projects/{globe}/inst/arearule", json={"text": text}).json()
    assert len(j["table"]) == 6 and cl.get(f"/api/valve/projects/{base}/inst/arearule").json()["text"] == text
