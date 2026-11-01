"""valve29 Phase 1 — Engineering Feedback Loop: decisions beside the status, decision log, rule performance, rule change
procedure (never an automatic change), carry-over of decisions to the next revision, and the guard that judging code
never reads any of it."""
from __future__ import annotations

import ast
import datetime as dt
import io
from pathlib import Path

import openpyxl

from app.valve import checks, ruleperf
from tests.test_valve_revision import _client, _pdf


def _first(c, pid):
    return c.get(f"/api/valve/datasheets/{c.get(f'/api/valve/projects/{pid}/summary').json()['tags'][0]['id']}").json()


def test_decisions_map_onto_status_and_are_logged(tmp_path, monkeypatch):
    c, pid, up = _client(tmp_path, monkeypatch)
    up("ds_A.pdf", _pdf("A", values={2: ["HOLD", "TBC"], 10: ["Note-7"]}))      # + 2 Open Items · 1 missing-note Data Error
    a = _first(c, pid)
    dm = [i for i in a["issues"] if i["type"] == "Data Missing"]
    other = [i for i in a["issues"] if i["type"] not in ("Data Missing", "Revision Change") and not i.get("comment_id")]
    assert len(dm) >= 2 and len(other) >= 3
    miss = dm[:2] + other[:2]
    H = {"X-Author": "eng"}
    url = lambda i: f"/api/valve/datasheets/{a['id']}/issues/{i['ikey']}"   # noqa: E731
    # Dismissed without a reason category is refused; with one it maps to status Dismissed
    assert c.put(url(miss[0]), json={"decision": "Dismissed", "note": "x"}, headers=H).status_code == 400
    r = c.put(url(miss[0]), json={"decision": "Dismissed", "reason_cat": "Vendor Clarification", "note": "VTA reply", "conclusion": "ok"}, headers=H).json()
    assert r == {"ok": True, "status": "Dismissed", "decision": "Dismissed"}
    assert c.put(url(miss[1]), json={"decision": "Not Applicable", "reason_cat": "Not Applicable"}, headers=H).json()["status"] == "Dismissed"
    assert c.put(url(miss[2]), json={"decision": "Deferred"}, headers=H).json()["status"] == "Open"
    r = c.put(url(miss[3]), json={"decision": "Modified", "reason_cat": "Other", "modified_text": "Provide design pressure (barg).",
                                  "modified_severity": "Minor"}, headers=H).json()
    assert r["status"] == "Confirmed"
    assert c.put(url(miss[0]), json={"decision": "Bogus"}, headers=H).status_code == 400
    assert c.put(url(miss[0]), json={"decision": "Dismissed", "reason_cat": "Because"}, headers=H).status_code == 400
    # the old status-only call still works (bulk / older screens) and counts as a decision
    oi = other[2]
    assert c.put(f"/api/valve/datasheets/{a['id']}/issues/{oi['ikey']}", json={"status": "Confirmed", "note": ""}).json()["decision"] == "Confirmed"
    b = _first(c, pid)
    st = {i["ikey"]: i for i in b["issues"]}
    assert st[miss[0]["ikey"]]["decision"] == "Dismissed" and st[miss[0]["ikey"]]["reason_cat"] == "Vendor Clarification"
    assert st[miss[2]["ikey"]]["status"] == "Open" and st[miss[2]["ikey"]]["decision"] == "Deferred"
    m = st[miss[3]["ikey"]]
    assert m["description"] == "Provide design pressure (barg)." and m["severity"] == "Minor"
    assert m["original_description"] == miss[3]["description"] and m["original_severity"] == miss[3]["severity"]
    # decision log: one row per change, with the snapshot of the finding as the engineer saw it
    L = c.get(f"/api/valve/projects/{pid}/rules/decisions?rule=DM-02").json()["rows"]
    assert len(L) >= 2 and all(x["rule"] == "DM-02" and x["rule_ver"] == "1" and x["finding"] for x in L)
    dm = next(x for x in L if x["decision"] == "Dismissed")
    assert dm["reason_cat"] == "Vendor Clarification" and dm["reason"] == "VTA reply" and dm["conclusion"] == "ok" and dm["by"] == "eng"
    # rule performance
    P = c.get(f"/api/valve/projects/{pid}/rules/performance").json()
    r = next(x for x in P["rules"] if x["rule"] == "DM-02")
    assert (r["dismissed"], r["not_applicable"]) == (1, 1) and r["decided"] == 2 and r["dismissal_rate"] == 1.0 and r["tool_cause"] == 0
    assert r["reasons"] == {"Vendor Clarification": 1, "Not Applicable": 1} and r["source"] == checks.GENERAL
    rid = checks.rule_of(miss[3]["check"])
    assert next(x for x in P["rules"] if x["rule"] == rid)["modified"] >= 1
    # Issue List Excel carries the rule id and the decision
    x = c.get(f"/api/valve/projects/{pid}/issues.xlsx?dismissed=1").content
    ws = openpyxl.load_workbook(io.BytesIO(x))["Issue List"]
    head = [h.value for h in ws[1]]
    assert head[-3:] == ["Rule ID", "Engineer Decision", "Decision Reason"]
    rows = [[ws.cell(r, k + 1).value for k in range(len(head))] for r in range(2, ws.max_row + 1)]
    assert any(r[-2] == "Dismissed" and "Vendor Clarification" in (r[-1] or "") for r in rows)
    # feedback json v2
    fb = c.get(f"/api/valve/projects/{pid}/feedback.json").json()
    assert fb["version"] == 2 and any(v["decision"] == "Dismissed" and v["reason_cat"] == "Vendor Clarification" and v["rule"] == "DM-02" for v in fb["verdicts"])


def test_decision_and_reason_carried_to_next_revision(tmp_path, monkeypatch):
    c, pid, up = _client(tmp_path, monkeypatch)
    up("ds_A.pdf", _pdf("A"))
    a = _first(c, pid)
    op = next(i for i in a["issues"] if i["type"] == "Data Missing" and i["key"].startswith("op_pressure"))
    c.put(f"/api/valve/datasheets/{a['id']}/issues/{op['ikey']}", json={"decision": "Not Applicable", "reason_cat": "Project Specification Exception"})
    up("ds_B.pdf", _pdf("B", values={6: ['3"', "Ball (Full Bore) - Floating"]}))
    b = _first(c, pid)
    it = {i["ikey"]: i for i in b["issues"]}[op["ikey"]]
    assert b["rev"] == "B" and it["status"] == "Dismissed" and it["decision"] == "Not Applicable"
    assert it["reason_cat"] == "Project Specification Exception" and it["note"].startswith("Carried from Rev A")


def test_rule_change_procedure_gates(tmp_path, monkeypatch):
    c, pid, up = _client(tmp_path, monkeypatch)
    H = {"X-Author": "lead"}
    assert c.post(f"/api/valve/projects/{pid}/rule-changes", json={"rule": "MR-03"}).status_code == 400          # needs ①②
    assert c.post(f"/api/valve/projects/{pid}/rule-changes", json={"rule": "XX-99", "current_logic": "a", "proposed_logic": "b", "reason": "c"}).status_code == 400
    r = c.post(f"/api/valve/projects/{pid}/rule-changes", json={"rule": "MR-03", "current_logic": "a", "proposed_logic": "b", "reason": "35 % dismissed"}, headers=H).json()
    cid = r["id"]
    assert r["status"] == "Proposed"
    row = c.get(f"/api/valve/projects/{pid}/rule-changes").json()["rows"][0]
    assert (row["from_ver"], row["to_ver"]) == ("1", "2")
    assert c.put(f"/api/valve/rule-changes/{cid}", json={"status": "Approved"}).status_code == 400              # not tested yet
    assert c.put(f"/api/valve/rule-changes/{cid}", json={"status": "Tested", "regression": "baseline unchanged"}).status_code == 400   # simulation missing
    assert c.put(f"/api/valve/rule-changes/{cid}", json={"status": "Tested", "simulation": "sim 3000 1.000"}).json()["status"] == "Tested"
    assert c.put(f"/api/valve/rule-changes/{cid}", json={"status": "Approved"}, headers=H).json()["status"] == "Approved"
    # Applied only once the code's rule version is the proposed one — the record never changes a rule by itself
    assert c.put(f"/api/valve/rule-changes/{cid}", json={"status": "Applied"}).status_code == 400
    assert checks.RULE_VERSION["MR-03"] == "1"
    row = c.get(f"/api/valve/projects/{pid}/rule-changes").json()["rows"][0]
    assert row["approved_by"] == "lead" and row["status"] == "Approved"


def test_performance_trend_and_flag():
    today = dt.date(2026, 11, 1)
    F = [{"check": "MR-03", "decision": "Dismissed", "status": "Dismissed", "reason_cat": "Incorrect Rule Logic"}] * 4 + \
        [{"check": "MR-03", "decision": "Confirmed", "status": "Confirmed"}] * 6 + [{"check": "MR-03", "status": "Resolved"}] + \
        [{"check": "PMS-trim", "status": "Open"}]
    log = [{"rule": "MR-03", "decision": "Dismissed", "at": "2026-10-03T10:00:00"}, {"rule": "MR-03", "decision": "Confirmed", "at": "2026-11-01T09:00:00"},
           {"rule": "MR-03", "decision": "Confirmed", "at": "2026-07-01T09:00:00"}]
    P = ruleperf.performance(F, log, {"rp_min_n": "10", "rp_dismiss_rate": "0.3"}, today)
    assert P["months"] == ["2026-09", "2026-10", "2026-11"]
    r = next(x for x in P["rules"] if x["rule"] == "MR-03")
    assert (r["total"], r["decided"], r["resolved"], r["tool_cause"]) == (11, 11, 1, 4)
    assert r["dismissal_rate"] == round(4 / 11, 3) and r["review_suggested"] is True
    assert r["trend"]["2026-10"] == {"Dismissed": 1} and r["trend"]["2026-11"] == {"Confirmed": 1} and "2026-07" not in r["trend"]
    p = next(x for x in P["rules"] if x["rule"] == "PMS")
    assert p["total"] == 1 and p["undecided"] == 1 and p["dismissal_rate"] is None and p["review_suggested"] is False
    assert P["rules"][0]["rule"] == "MR-03"                                                   # flagged rules first
    P2 = ruleperf.performance(F, log, {"rp_min_n": 20}, today)
    assert not next(x for x in P2["rules"] if x["rule"] == "MR-03")["review_suggested"]       # too few decisions for this project's bar


def test_settings_validation(tmp_path, monkeypatch):
    c, pid, up = _client(tmp_path, monkeypatch)
    r = c.put(f"/api/valve/projects/{pid}/settings", json={"rp_min_n": "5", "rp_dismiss_rate": 2, "x": 1}).json()
    assert r["saved"] == {"rp_min_n": "5"}
    assert c.get(f"/api/valve/projects/{pid}/rules/performance").json()["settings"]["rp_min_n"] == 5


def test_judging_code_never_reads_decisions():
    """Engineer decisions score the rules; they must not steer them (extends the valve04 feedback guard)."""
    root = Path(__file__).resolve().parents[1] / "app" / "valve"
    banned = ("decision_log", "rule_change", "ruleperf", "project_setting", "feedback")
    for name in ("extract", "schema", "material", "pms", "issues", "tbe", "matreview", "expert", "tagrules", "process",
                 "requirements", "checks", "revisions", "knowledge"):
        tree = ast.parse((root / f"{name}.py").read_text(encoding="utf-8"))
        words = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | \
                {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)} | \
                {a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
        assert not any(b in w for w in words for b in banned), name


def test_source_traceability(tmp_path, monkeypatch):
    """valve29 §7: reader version on every datasheet read; every finding says how it compared (operator · tolerance · result)."""
    from app.valve import extract
    c, pid, up = _client(tmp_path, monkeypatch)
    up("ds_A.pdf", _pdf("A", values={2: ["HOLD", "TBC"], 10: ["Note-7"]}))
    a = _first(c, pid)
    assert a["parser_version"] == extract.PARSER_VERSION
    f = next(x for x in a["fields"] if x["key"] == "seat_material")
    assert f["page"] and f["bbox"] and f["value"] == "RTFE" and a["document_id"] and a["filename"] == "ds_A.pdf"
    ops = {i["check"]: (i["op"], i["tol"], i["result"]) for i in a["issues"] if i.get("check")}
    assert ops["DM-02"][0] == "present" and ops["DM-02"][2] == "Missing"
    assert ops["OI-01"][2] == "Open (HOLD/TBC)" and ops["DE-08"][0] == "exists"
    for i in a["issues"]:
        if i.get("check"):
            assert "op" in i and "result" in i and i["result"]          # every rule finding carries a result
    L = c.get(f"/api/valve/projects/{pid}/issues").json()["issues"]
    assert all("result" in i for i in L if i.get("check"))                # the list API keeps it (valve28 dropped it)


def test_excel_styles_after_fast_path():
    """valve29 perf: cell styles are prepared once and copied — the sheet must look exactly as before (fill · border · link)."""
    from app.valve import exports
    rows = [{"ikey": f"Data Missing:k{n}", "type": t, "color": col, "severity": "Major", "key": f"k{n}", "field": "F", "row": 1, "value": "",
             "unit": "", "description": "d", "expected": "", "page": 1, "bbox": [1, 1, 2, 2], "sheet": 1, "of": 1, "status": "Open", "note": "",
             "tag": f"T{n}", "doc_no": "D", "rev": "A", "ds_id": n, "document_id": 1, "filename": "f.pdf", "area_name": "North", "site": "",
             "plant_unit": "98", "valve_type": "XV", "check": "DM-02", "evidence": []}
            for n, (t, col) in enumerate([("Data Missing", "missing"), ("Data Error", "error"), ("Data Missing", "missing")] * 40)]
    ws = openpyxl.load_workbook(io.BytesIO(exports.issues_xlsx(rows, "http://pc:8000", "P")))["Issue List"]
    head = [c.value for c in ws[1]]
    it, tg = head.index("Issue Type") + 1, head.index("Tag Number") + 1
    assert ws.max_row == len(rows) + 1                                   # no stray rows from the style scratch cells
    for r in (2, 3, 60, ws.max_row):
        assert ws.cell(r, 1).border.top.style == "thin" and ws.cell(r, 1).alignment.wrap_text
        assert ws.cell(r, it).fill.fgColor.rgb == "00" + exports.HEXFILL[rows[r - 2]["color"]]
        assert ws.cell(r, tg).hyperlink and ws.cell(r, tg).font.b and ws.cell(r, tg).font.color.rgb == "002F5BD8"
    assert "_style_tmp" not in openpyxl.load_workbook(io.BytesIO(exports.issues_xlsx(rows[:3], "", "P"))).sheetnames


def test_compact_issue_list_same_information(tmp_path, monkeypatch):
    """valve29 perf: the screens read ?compact=1 — once the per-datasheet fields are merged back, every row equals the full
    list minus the proof fields (which the workbench reads per datasheet)."""
    c, pid, up = _client(tmp_path, monkeypatch)
    up("ds_A.pdf", _pdf("A", values={2: ["HOLD", "TBC"], 10: ["Note-7"]}))
    full = c.get(f"/api/valve/projects/{pid}/issues").json()
    comp = c.get(f"/api/valve/projects/{pid}/issues?compact=1").json()
    assert len(full["issues"]) == len(comp["issues"]) and comp["counts"] == full["counts"]
    proof = {"evidence", "basis", "op", "tol", "original_description", "original_severity", "pms_bbox", "pms_page"}
    for a, b in zip(full["issues"], comp["issues"]):
        b = dict(b, **comp["ds"][str(b["ds_id"])])
        assert {k: v for k, v in a.items() if k not in proof} == {k: v for k, v in b.items() if v not in (None, "", [])}
        assert not proof & set(comp["issues"][0])
    assert c.get(f"/api/valve/projects/{pid}/issues?compact=1").content == c.get(f"/api/valve/projects/{pid}/issues?compact=1").content
