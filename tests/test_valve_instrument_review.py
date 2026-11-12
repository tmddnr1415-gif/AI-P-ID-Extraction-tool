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
