"""valve28 — every finding of the verification engine carries its proof: check id, basis, evidence with page + value."""
from __future__ import annotations

import io

import openpyxl

from app.valve import exports, issues


def test_evidence_on_every_engine_finding():
    F = [{"key": "line_no", "display": "Line No.", "value": 'P98981016-2"(1C3AS2)-N', "page": 1, "bbox": [1, 1, 2, 2], "row": 5},
         {"key": "piping_class", "display": "Piping class", "value": "1C0K8", "page": 1, "bbox": [1, 3, 2, 4], "row": 9},
         {"key": "line_size_inlet", "display": "Line Size", "value": "4", "page": 1, "bbox": [1, 5, 2, 6], "row": 10},
         {"key": "op_pressure", "display": "Operating Pressure", "value": "100", "unit": "barg", "page": 1, "bbox": [1, 7, 2, 8], "row": 14, "section": "process"},
         {"key": "design_pressure", "display": "Design Pressure", "value": "50", "unit": "barg", "page": 1, "bbox": [3, 7, 4, 8], "row": 14, "section": "process"},
         {"key": "design_temp", "display": "Design Temperature", "value": "", "unit": "°C", "page": 1, "bbox": [3, 9, 4, 10], "row": 15, "section": "process"},
         {"key": "fail_position", "display": "Valve fail safe position", "value": "Close", "page": 1, "bbox": [1, 11, 2, 12], "row": 17},
         {"key": "air_failure", "display": "Action on Air Failure", "value": "Fail Open", "page": 1, "bbox": [1, 13, 2, 14], "row": 41}]
    for f in F:
        f.setdefault("edited_value", None)
    ds = {"fields": F, "notes": [], "pages": [1], "sheets": [[1, 1, 1]], "comments": [], "tag_key": "T1", "process_ref": None}
    prows = [{"key": "design_temp", "ds_key": "design_temp", "item": "Design Temperature", "ds": "", "pd": "260", "pd_unit": "°C", "result": "Referenced",
              "reason": "", "pd_page": 54, "pd_bbox": [1, 1, 2, 2], "pd_doc": "CO2S-SSG-IN-REQ-00009"},
             {"key": "design_pressure", "ds_key": "design_pressure", "item": "Design Pressure", "ds": "50", "pd": "60", "pd_unit": "barg", "result": "Mismatch",
              "reason": "Datasheet 50 barg ≠ Process Data 60 barg", "pd_page": 54, "pd_bbox": [1, 1, 2, 2], "pd_doc": "CO2S-SSG-IN-REQ-00009", "ds_page": 1, "ds_bbox": [3, 7, 4, 8]}]
    prev = [{"key": "piping_class", "display": "Piping class", "change": "Modified", "previous": "1C3AS2", "new": "1C0K8", "prev_page": 1, "prev_bbox": [9, 9, 9, 9], "new_page": 1, "new_bbox": [1, 3, 2, 4]}]
    out = issues.compute(ds, {}, None, "", prev, {}, process_rows=prows,
                         material_rows=[{"rule": "MR-01", "level": "Action", "severity": "Major", "title": "t", "key": "seat_material", "short": "s",
                                         "basis": "PMS 1C3AS2 Note 018", "evidence": [{"doc": "PMS", "where": "class 1C3AS2 · note 018", "page": 12, "bbox": None, "text": "RTFE 230 °C"}]}])
    by = {i["check"]: i for i in out if i.get("check")}
    assert {"DE-01", "DE-02", "DE-03", "DE-04", "DM-02", "PD-design_pressure", "MR-01", "REV-01"} <= set(by)
    assert all(i.get("check") and i.get("basis") for i in out if i["type"] not in ("Reviewer Comment", "Reviewer Correction", "Extraction Review"))
    assert by["DE-01"]["evidence"][0]["text"] == 'P98981016-2"(1C3AS2)-N' and by["DE-01"]["evidence"][0]["page"] == 1
    assert by["PD-design_pressure"]["evidence"][0]["doc"].startswith("Process Data") and by["PD-design_pressure"]["evidence"][0]["page"] == 54
    assert by["DM-02"]["evidence"][0]["text"] == "260 °C" and "CO2S-SSG" in by["DM-02"]["expected"]
    assert by["REV-01"]["evidence"][0]["text"] == "1C3AS2" and by["MR-01"]["evidence"][0]["doc"] == "PMS"
    txt = exports.ev_text(by["PD-design_pressure"])
    assert "Process Data CO2S-SSG-IN-REQ-00009 p.54 Design Pressure: 60 barg" == txt
    rows = [dict(i, tag="T1", doc_no="D", rev="A", ds_id=1, document_id=1, filename="ds.pdf", area_name="North", site="", plant_unit="98", valve_type="On/Off")
            for i in out]
    wb = openpyxl.load_workbook(io.BytesIO(exports.issues_xlsx(rows, "http://pc:8000", "P", "t", ["ds.pdf"])))
    ws = wb["Issue List"]
    head = [c.value for c in ws[1]]
    assert "Evidence" in head and "Basis" in head
    col = head.index("Evidence") + 1
    assert any("p.54" in str(ws.cell(r, col).value or "") for r in range(2, ws.max_row + 1))


def test_check_registry_report():
    from app.valve import checks
    issues_ = [{"check": "DE-01", "status": "Open"}, {"check": "PMS-trim", "status": "Open"}, {"check": "PMS-rating", "status": "Dismissed"},
               {"check": "MR-01", "status": "Open"}]
    r = checks.report(issues_, {"has_pms": True, "pms_class": True, "piping_class": "1C3AS2", "has_process": False, "pd_row": False,
                                "design_temp": 260, "has_prev": False, "has_peers": False, "has_tagrules": True})
    st = {c["id"]: c for c in r["checks"]}
    assert st["DE-01"]["status"] == "fail" and st["PMS"]["status"] == "fail" and st["PMS"]["findings"] == 1      # the dismissed one does not count
    assert st["PD"]["status"] == "n/a" and st["PD"]["reason"] == "Process Data not uploaded"
    assert st["REV-01"]["status"] == "n/a" and st["PC-01"]["status"] == "n/a" and st["TG-02"]["status"] == "pass"
    assert st["MR-02"]["status"] == "pass" and st["DE-02"]["status"] == "pass"
    s = r["summary"]
    assert s["pass"] + s["fail"] + s["na"] == s["total"] == len(checks.REGISTRY) and s["fail"] == 3
    # without PMS the class-based rules are n/a, not pass
    r2 = checks.report([], {"has_pms": False, "design_temp": None, "has_prev": True, "has_peers": True, "has_tagrules": False})
    st2 = {c["id"]: c for c in r2["checks"]}
    assert st2["MR-10"]["reason"] == "PMS not uploaded" and st2["MR-02"]["reason"].startswith("No design temperature") and st2["TG-03"]["status"] == "n/a"
