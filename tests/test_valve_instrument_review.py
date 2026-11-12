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
