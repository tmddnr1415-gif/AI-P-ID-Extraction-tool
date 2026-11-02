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


def test_engineer_edits_the_comment(tmp_path, monkeypatch):
    """valve29 (user): the tool's comment can be corrected / supplemented; status and decision stay, the tool's text is kept."""
    c, pid, up = _client(tmp_path, monkeypatch)
    up("ds_A.pdf", _pdf("A", values={2: ["HOLD", "TBC"], 10: ["Note-7"]}))
    a = _first(c, pid)
    it = next(i for i in a["issues"] if i["type"] == "Data Error")
    url = f"/api/valve/datasheets/{a['id']}/issues-text/{it['ikey']}"
    assert c.put(url, json={"text": "Bolting note reference is wrong — shall refer to Note 1.", "expected": "Note 1"}, headers={"X-Author": "eng"}).json()["ok"]
    b = {i["ikey"]: i for i in _first(c, pid)["issues"]}[it["ikey"]]
    assert b["description"].startswith("Bolting note reference") and b["expected"] == "Note 1" and b["edited"] is True
    assert b["original_description"] == it["description"] and b["status"] == "Open"
    # a later decision keeps the engineer's words
    c.put(f"/api/valve/datasheets/{a['id']}/issues/{it['ikey']}", json={"decision": "Confirmed"})
    b = {i["ikey"]: i for i in _first(c, pid)["issues"]}[it["ikey"]]
    assert b["status"] == "Confirmed" and b["description"].startswith("Bolting note reference") and b["expected"] == "Note 1"
    # it reaches the contractor's Excel; the edit is logged
    ws = openpyxl.load_workbook(io.BytesIO(c.get(f"/api/valve/projects/{pid}/issues.xlsx").content))["Issue List"]
    head = [h.value for h in ws[1]]
    assert any((ws.cell(r, head.index("Description") + 1).value or "").startswith("Bolting note reference") for r in range(2, ws.max_row + 1))
    assert any(x["decision"] == "Edited" for x in c.get(f"/api/valve/projects/{pid}/rules/decisions").json()["rows"])
    # back to the tool's own text
    c.put(url, json={"text": "", "expected": ""})
    b = {i["ikey"]: i for i in _first(c, pid)["issues"]}[it["ikey"]]
    assert b["description"] == it["description"] and not b.get("edited")
    assert c.put(f"/api/valve/datasheets/{a['id']}/issues-text/Nope:x", json={"text": "x"}).status_code == 404


def test_dense_phase_co2_is_a_special_requirement():
    from app.valve import requirements
    ds = {"fields": [], "notes": [{"no": 9, "text": "Fluid Phase: Dense phase CO2."}, {"no": 2, "text": "Fugitive emission Class A type tested."}]}
    gn = {"2": "The valves (for dense/supercritical phase, liquid and gas service) shall be TSO where specified."}
    R = requirements.find(ds, gn)
    dense = [r for r in R if r["key"] == "dense_co2"]
    assert [r["source"] for r in dense] == ["Note 9"]                        # the conditional General Note is not this valve's phase
    cols = requirements.columns(R)
    assert cols["Dense Phase CO2"] == "Yes (Note 9)" and cols["Fugitive Emission (ISO 15848)"].startswith("Yes")
    assert "Dense phase CO2 (Note 9)" in requirements.summary(R)
    assert not [r for r in requirements.find({"fields": [], "notes": [{"no": 1, "text": "Fluid Phase: Gas."}]}, {}) if r["key"] == "dense_co2"]


def test_reference_document_versions(tmp_path, monkeypatch):
    """valve29: a finding names WHICH PMS / Process Data it was checked against — the newest upload — and the earlier ones."""
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    from app.valve import store as st
    con = st.connect()
    pid = con.execute("INSERT INTO project(name, created_at) VALUES ('P', '2026-11-01')").lastrowid
    for n, day in ((1, "2026-10-01"), (2, "2026-10-20")):
        con.execute("INSERT INTO document(project_id, kind, filename, status, uploaded_at) VALUES (?,?,?,?,?)", (pid, "process", f"PD_rev{n}.pdf", "done", day))
    con.commit()
    new = st.one(con, "SELECT id, filename FROM document WHERE filename='PD_rev2.pdf'")
    from app.valve import api
    ref = api._doc_ref(con, pid, "process", new)
    assert ref["filename"] == "PD_rev2.pdf" and ref["uploaded_at"] == "2026-10-20" and [e["filename"] for e in ref["earlier"]] == ["PD_rev1.pdf"]


def test_special_requirements_summary_and_excel(tmp_path, monkeypatch):
    """valve29: special requirements (PFP · Fugitive · Fire Safe · Dense CO2 …) at a glance — by Area / Unit / Tag, same in Excel."""
    c, pid, up = _client(tmp_path, monkeypatch)
    up("ds_A.pdf", _pdf("A", notes=["Fluid Phase: Dense phase CO2.", "Fugitive emission Class A type tested."]))
    R = c.get(f"/api/valve/projects/{pid}/requirements").json()
    assert R["total"] == {"tags": 1, "counts": {"Fugitive Emission (ISO 15848)": 1, "Dense Phase CO2": 1}}
    assert len(R["tags"]) == 1 and "Dense Phase CO2" in R["columns"]
    t = R["tags"][0]
    assert {k for k, v in t["cells"].items() if v} <= set(R["columns"]) and "Dense Phase CO2" in t["on"]
    assert sum((r.get("counts") or {}).get("Dense Phase CO2", 0) for r in (R["by_area"].values() if isinstance(R["by_area"], dict) else R["by_area"])) == 1
    wb = openpyxl.load_workbook(io.BytesIO(c.get(f"/api/valve/projects/{pid}/requirements.xlsx").content))
    assert {"Summary by Area", "Summary by Unit", "By Tag", "Info"} <= set(wb.sheetnames)
    ws = wb["By Tag"]
    head = [h.value for h in ws[1]]
    assert ws.max_row == 2 and "Dense Phase CO2" in head
    # a filter that matches nothing gives an empty tag sheet, not an error
    wb = openpyxl.load_workbook(io.BytesIO(c.get(f"/api/valve/projects/{pid}/requirements.xlsx?req=PFP").content))
    assert wb["By Tag"].max_row == 1


def test_new_database_first_use_from_many_threads(tmp_path, monkeypatch):
    """A new installation: the warm-up thread and the first screen request open the empty database together."""
    import threading
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "fresh"))
    from app.valve import store as st
    errs = []

    def go():
        try:
            st.connect().execute("SELECT count(*) FROM project").fetchone()
        except Exception as e:                              # noqa: BLE001
            errs.append(e)
    th = [threading.Thread(target=go) for _ in range(8)]
    [t.start() for t in th]
    [t.join() for t in th]
    assert errs == []


def test_screen_answers_cached_until_the_next_write(tmp_path, monkeypatch):
    """valve29 speed: summary · rules · requirements answers are reused, but never after a write (decision, edit …)."""
    c, pid, up = _client(tmp_path, monkeypatch)
    up("ds_A.pdf", _pdf("A"))
    a = _first(c, pid)
    s1 = c.get(f"/api/valve/projects/{pid}/summary").json()
    assert c.get(f"/api/valve/projects/{pid}/summary").json() == s1                    # reused, same answer
    r1 = c.get(f"/api/valve/projects/{pid}/rules/performance").json()
    it = next(i for i in a["issues"] if i["type"] == "Data Missing")
    c.put(f"/api/valve/datasheets/{a['id']}/issues/{it['ikey']}", json={"decision": "Dismissed", "reason_cat": "Other"}, headers={"X-Author": "eng"})
    s2 = c.get(f"/api/valve/projects/{pid}/summary").json()
    r2 = c.get(f"/api/valve/projects/{pid}/rules/performance").json()
    assert s2 != s1 and r2 != r1                                                        # the write is seen at once
    c.put(f"/api/valve/datasheets/{a['id']}/status", json={"status": "Accepted"}, headers={"X-Author": "eng"}).raise_for_status()
    assert c.get(f"/api/valve/projects/{pid}/summary").json() != s2


def test_accessory_rules_positioner_transmitter_solenoid():
    """valve29 AC-01..05 — positioner · position transmitter · solenoid valves, judged only on what the datasheet and its own
    General Notes say (no make, voting or SIL is assumed)."""
    from app.valve import expert, knowledge
    for k in ("acc.positioner", "acc.pos_tx", "acc.sov", "acc.sov_redundant", "acc.pst"):
        assert knowledge.get(k)["ref"]
    gn = {"15": "Emerson Fisher DVC (latest proven in use model) shall be provided as valve positioner part of ESDV/BDV assembly.",
          "20": "ESDV/BDV/XV shall be provided with position transmitters as default. Limit switches shall not be used. Position "
                "transmitters which are specifically connected to safety systems for UZ logic/safety interlock shall be SIL 2 rated."}

    def run(fields, notes, vt="ESDV"):
        ds = {"valve_type": vt, "fields": [{"key": k, "value": v, "display": k} for k, v in fields.items()],
              "notes": [{"no": n + 1, "text": t} for n, t in enumerate(notes)]}
        return {r["rule"]: r for r in expert.review(ds, gn) if r["rule"].startswith("AC-")}

    ok = run({"sil": "SIL 2", "limit_switch": "NA", "sov_tag": "Note-2"},
             ["Position Transmitter 4-20 mA HART & SIL 2.", "SOVs (98ESDY-1A & 98ESDY-1B) in 1oo2 arrangement.",
              "Emerson Fisher DVC Smart positioner, HART."])
    assert ok == {}                                                              # everything stated → silent
    r = run({"sil": "SIL 2", "limit_switch": "Required, 2 x SPDT", "sov_tag": "Note-2"},
            ["Position Transmitter 4-20 mA HART.", "SOVs (98ESDY-1A & 98ESDY-1B).", "Positioner: Siemens SIPART PS2."])
    assert set(r) == {"AC-01", "AC-03", "AC-04", "AC-05"}
    assert r["AC-01"]["level"] == "Action" and "General Note 20" in r["AC-01"]["short"]
    assert r["AC-05"]["level"] == "Confirm" and "98ESDY-1A" in r["AC-05"]["short"] and r["AC-05"]["kb"] == "acc.sov_redundant"
    assert r["AC-03"]["level"] == "Note"                                         # SIL of the transmitter: confirm, not an error
    assert any(e["where"] == "General Note 15" for e in r["AC-04"]["evidence"])
    r = run({"limit_switch": "NA"}, ["Solenoid valve coil Class H."], vt="XV")
    assert set(r) == {"AC-02"}                                                   # GN 20 lists XV; no transmitter anywhere
    assert run({"limit_switch": "NA"}, [], vt="MOV") == {}                       # MOV is not in GN 20 → not asked


def test_reference_document_revisions_read_from_the_document(tmp_path):
    """valve29 first screen: Rev · date of the loaded PMS / Process Data come from the document's own revision table."""
    import pymupdf
    from app.valve import docrev
    assert docrev.parse_date("20/Sep/2026").isoformat() == "2026-09-20" and docrev.parse_date("08/09/2026").isoformat() == "2026-09-08"
    assert docrev.parse_date("19/9/2026").isoformat() == "2026-09-19" and docrev.parse_date("Rev") is None
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text((40, 40), "Doc. No.:")
    p.insert_text((40, 52), "98-98-PI-SPC-00001")
    p.insert_text((300, 40), "Rev. 0,")
    for y, (rev, date, desc) in zip((600, 615, 630), (("0", "20/Sep/2026", "Approved For Construction"), ("B", "02/Aug/2026", "Issued For Approval"),
                                                      ("A", "05/Mar/2026", "Issued for IDC"))):
        p.insert_text((40, y), rev)
        p.insert_text((80, y), date)
        p.insert_text((180, y), desc)
    p.insert_text((36, 650), "Rev.")
    q = doc.new_page()                                        # a process datasheet inside the annexure, its own table
    q.insert_text((40, 40), "01-09-PR-DTS-00002")
    for y, (rev, date) in zip((600, 615), (("B", "08/09/2026"), ("A", "20/08/2026"))):
        q.insert_text((40, y), rev)
        q.insert_text((300, y), date)
    q.insert_text((38, 630), "REV")
    f = tmp_path / "x.pdf"
    doc.save(f)
    r = docrev.read(f)
    assert (r["doc_no"], r["header_rev"], r["rev"], r["date"]) == ("98-98-PI-SPC-00001", "0", "0", "20/Sep/2026")
    assert r["desc"].startswith("Approved For Construction")
    assert [(x["doc_no"], x["rev"], x["date"]) for x in r["parts"]] == [("01-09-PR-DTS-00002", "B", "08/09/2026")]
    assert docrev.newest(r["parts"])["rev"] == "B"
    assert docrev.read(tmp_path / "missing.pdf")["rev"] == ""                     # unreadable → empty, never guessed


def test_summary_names_the_latest_datasheet_revisions(tmp_path, monkeypatch):
    c, pid, up = _client(tmp_path, monkeypatch)
    up("ds_A.pdf", _pdf("A"))
    L = c.get(f"/api/valve/projects/{pid}/summary").json()["latest_docs"]
    assert L["datasheet"]["tags"] == 1 and L["datasheet"]["by_rev"] == {"A": 1} and L["datasheet"]["filename"] == "ds_A.pdf"
    assert "pms" not in L and "process" not in L                                  # not uploaded → not shown as if it were


def test_delete_uploaded_document_goes_to_trash_and_restores(tmp_path, monkeypatch):
    """valve32: an upload can be removed (with its datasheets, comments and decisions) and put back from the trash."""
    c, pid, up = _client(tmp_path, monkeypatch)
    up("ds_A.pdf", _pdf("A"))
    up("ds_B.pdf", _pdf("B", values={2: ["HOLD", "TBC"]}))
    docs = c.get(f"/api/valve/projects/{pid}/summary").json()["documents"]
    b = next(d for d in docs if d["filename"] == "ds_B.pdf")
    dsb = c.get(f"/api/valve/projects/{pid}/summary").json()["tags"][0]
    assert dsb["rev"] == "B"
    it = next(i for i in c.get(f"/api/valve/datasheets/{dsb['id']}").json()["issues"] if i["type"] == "Open Item")
    c.put(f"/api/valve/datasheets/{dsb['id']}/issues/{it['ikey']}", json={"decision": "Dismissed", "reason_cat": "Other"}, headers={"X-Author": "eng"})
    imp = c.get(f"/api/valve/documents/{b['id']}/impact").json()
    assert imp["datasheets"] == 1 and imp["decisions"] >= 1 and imp["tags_gone"] == 0       # Rev A keeps the tag
    r = c.delete(f"/api/valve/documents/{b['id']}", headers={"X-Author": "eng"}).json()
    assert r["ok"] and r["datasheets"] == 1
    s = c.get(f"/api/valve/projects/{pid}/summary").json()
    assert [d["filename"] for d in s["documents"]] == ["ds_A.pdf"] and s["tags"][0]["rev"] == "A"
    assert c.get(f"/api/valve/datasheets/{dsb['id']}").status_code == 404
    tr = c.get(f"/api/valve/projects/{pid}/trash").json()["items"]
    assert len(tr) == 1 and tr[0]["filename"] == "ds_B.pdf"
    assert c.post(f"/api/valve/projects/{pid}/trash/{tr[0]['name']}/restore", headers={"X-Author": "eng"}).json()["ok"]
    s = c.get(f"/api/valve/projects/{pid}/summary").json()
    assert s["tags"][0]["rev"] == "B" and len(s["documents"]) == 2
    st = {i["ikey"]: i for i in c.get(f"/api/valve/datasheets/{dsb['id']}").json()["issues"]}[it["ikey"]]
    assert st["status"] == "Dismissed"                                       # the decision came back with it
    assert c.get(f"/api/valve/projects/{pid}/trash").json()["items"] == []
    assert c.delete("/api/valve/documents/9999").status_code == 404


def test_first_screen_valve_summary_matches_the_project(tmp_path, monkeypatch):
    """valve33: the first-screen Valve Summary records (one per newest-revision tag) add up to the project's numbers."""
    c, pid, up = _client(tmp_path, monkeypatch)
    up("ds_A.pdf", _pdf("A", values={2: ["HOLD", "TBC"]}, notes=["Fluid Phase: Dense phase CO2.", "Fugitive emission Class A."]))
    V = c.get(f"/api/valve/projects/{pid}/valve-summary").json()
    s = c.get(f"/api/valve/projects/{pid}/summary").json()
    assert len(V["tags"]) == s["kpi"]["tags"] == 1
    t = V["tags"][0]
    issues = c.get(f"/api/valve/projects/{pid}/issues").json()["issues"]
    from app.valve import issues as issuesmod
    assert t["open"] == sum(1 for i in issues if i["type"] in issuesmod.CONTRACTOR_TYPES and i["status"] != "Dismissed")
    assert "Dense Phase CO2" in t["req"] and "Dense Phase CO2" in V["reqs"] and t["type"] in V["types"]
    assert V["has_valvelist"] is False and t["new"] is None                  # no Valve List → 'New Tags' is not claimed
