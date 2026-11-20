"""valve42 — the project's Valve Specifications as review basis (user 2026-11-20: 'Spec 을 학습해 이를 기반으로 코멘트').
The specifications are drawn here with made-up clauses in the same layout (nothing from a client): a cover, a contents page,
a header repeated on every page, numbered clauses, a clause number alone on its line, bullets alone on their line."""
from __future__ import annotations

import time

import pymupdf

HEAD = ["TEST UNIT, SPECIFICATION, {t}", "Doc. ID:", "{dn}", "Rev.: Date: Page:"]


def _spec(title, dn, body):
    doc = pymupdf.open()
    p = doc.new_page()
    y = 60
    for s in ("TEST OWNER", "DOCUMENT TITLE:", f"TEST UNIT, SPECIFICATION, {title}", "", "C", "01-02-2026", "Issued for Design",
              "DOCUMENT NO", "TEST/PRJ/1", dn, "C", "1 of 3"):
        p.insert_text((60, y), s, fontsize=9)
        y += 13
    p = doc.new_page()                                                   # contents page
    for i in range(8):
        p.insert_text((60, 80 + 14 * i), f"{i + 1}.0  SECTION {i + 1} " + "." * 40 + f" {i + 3}", fontsize=9)
    lines = body.strip("\n").split("\n")
    for start in range(0, len(lines), 40):
        p = doc.new_page()
        y = 40
        for h in HEAD:
            p.insert_text((60, y), h.format(t=title, dn=dn), fontsize=8)
            y += 11
        y += 10
        for s in lines[start:start + 40]:
            p.insert_text((60, y), s, fontsize=9)
            y += 13
    data = doc.tobytes()
    doc.close()
    return data


ONOFF = """10.0  SELECTION OF TEST VALVES
10.1  General
10.1.5  The valve shall have zero leakage requirement as per API 598 / ISO 5208 Rate A
10.2  Valve Bodies
10.2.1  Ball valves must be fire safe (in accordance with API 607/ API 6FA). Chrome plated balls are not acceptable.
10.2.3  Valves shall be flanged. Flangeless, wafer-type bodies are not acceptable, unless approved.
10.2.4  Extension bonnets shall be specified as follows:
a. Extension bonnets for fluid operating temperature
down to -100 °C or above +230 °C.
10.2.7  Valves in CO2, hazardous and toxic service to be provided
with Class A type tested fugitive emission packing
in accordance with ISO 15848-1.
10.3
Valve Actuators
10.3.5  Actuators shall be sized as follows: a. 10 inch and smaller: Less than 10 second for air fail action (Actuator Spring Power).
b. 12 inch and larger: Less than 1 second per inch for air fail action (Actuator Spring Power).
10.3.7  Actuator torque shall be 1.5 times the valve torque required at full rated differential pressure.
10.3.12  Pneumatic diaphragm type actuators shall not be used.
12.4.1  Valves shall be provided with position transmitters as default. Limit switches shall not be used.
12.5.1  All instruments shall be provided with IP 66 or better enclosures.
"""
CV = """11.0 CONTROL VALVE SELECTION
11.1
General
•
The Control valves Leakage class shall be minimum class IV. Tight shut off needs class VI.
•
All resilient seated valves shall be fire safe designed in accordance with API 607 or API 6FA.
14.0 CONTROL VALVE SOUND LEVELS
➢ All valves predicted sound levels shall not exceed 85 dBA as measured 1 m downstream.
15.1
General Requirements
•
The safety factor shall be 1.5 for actuator sizing for general service control valves.
•
Valve positioners shall have analog 4-20mA output with HART protocol.
"""


def _parse(tmp_path, name, data):
    from app.valve import vspec
    f = tmp_path / name
    f.write_bytes(data)
    return vspec.read_spec(str(f))


def test_spec_is_read_into_clauses(tmp_path):
    s = _parse(tmp_path, "onoff.pdf", _spec("ON/OFF VALVE", "777-51-IN-SPC-00003", ONOFF))
    assert (s["doc_no"], s["rev"], s["scope"]) == ("777-51-IN-SPC-00003", "C", "onoff")
    nos = [c["no"] for c in s["clauses"]]
    assert "10.1.5" in nos and "10.2.7" in nos and "10.3" in nos and "12.5.1" in nos
    assert not any("SECTION" in c["text"] or "Doc. ID" in c["text"] for c in s["clauses"])          # contents · page header gone
    c = next(c for c in s["clauses"] if c["no"] == "10.3")
    assert c["text"].startswith("Valve Actuators")                                               # number alone on its line
    v = _parse(tmp_path, "cv.pdf", _spec("CONTROL VALVE", "777-51-IN-SPC-00002", CV))
    assert v["scope"] == "cv" and {"11.1 (1)", "11.1 (2)", "14.0 (1)", "15.1 (1)", "15.1 (2)"} <= {c["no"] for c in v["clauses"]}


def _ds(vt, family, form, **vals):
    return {"valve_type": vt, "family": family, "form": form, "notes": [], "general_notes": {},
            "fields": [{"key": k, "value": v} for k, v in vals.items()]}


def test_spec_checks_take_their_values_from_the_clauses(tmp_path):
    from app.valve import vspec
    on = _parse(tmp_path, "onoff.pdf", _spec("ON/OFF VALVE", "777-51-IN-SPC-00003", ONOFF))
    cv = _parse(tmp_path, "cv.pdf", _spec("CONTROL VALVE", "777-51-IN-SPC-00002", CV))
    bad = _ds("XV", "ball", "80", body_size='2"', leakage_class="ISO 5208 Rate B", ball_material="316 SS chrome plated",
              connections="Wafer type", act_type="Pneumatic diaphragm", stroke_closed="15 s", act_safety_factor="1.2",
              op_temp="-120", bonnet_type="Bolted", limit_switch="2 x proximity", ingress="IP 65", fluid="CO2")
    got = {f["check"]: f for f in vspec.findings(bad, [on, cv])}
    assert set(got) == {"SP-01", "SP-02", "SP-04", "SP-05", "SP-06", "SP-07", "SP-08", "SP-09", "SP-10", "SP-11", "SP-12"}
    assert got["SP-10"]["expected"] == "< 10 s" and got["SP-11"]["expected"] == "≥ 1.5" and got["SP-02"]["expected"].endswith("Rate A")
    assert got["SP-04"]["evidence"][0]["text"] == "Chrome plated balls are not acceptable." and got["SP-04"]["evidence"][0]["where"] == "§10.2.1"
    assert "777-51-IN-SPC-00003 §10.2.1" in got["SP-04"]["basis"]
    big = _ds("SDV", "ball", "80", body_size='16"', stroke_closed="14", fire_safe="Fire safe to API 607", leakage_class="API 598 / ISO 5208 Rate A")
    assert not vspec.findings(big, [on])                                                        # 16 s allowed for 16" · fire safe stated
    good = _ds("XV", "ball", "80", body_size='2"', leakage_class="API 598 / ISO 5208 Rate A", fire_safe="API 607", ball_material="316 SS / HF",
               fluid="CO2", packing_type="ISO 15848-1 Class A", stroke_closed="6", act_safety_factor="1.5")
    assert vspec.findings(good, [on]) == []
    c = _ds("FV", "globe", "ISA20", leakage_class="ANSI Class III", seat_material="PTFE", spl_pred="90 dBA", act_safety_factor="1.3",
            pos_signal="4-20 mA DC")
    assert {f["check"] for f in vspec.findings(c, [on, cv])} == {"SP-01", "SP-03", "SP-11", "SP-13", "SP-14"}    # only the CV spec applies
    assert vspec.findings(c, [on]) == []                                                        # no CV spec uploaded: nothing required


def test_spec_upload_gives_findings_with_clause_and_korean(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.valve import api
    from tests.test_valve_revision import _pdf
    app = FastAPI()
    app.include_router(api.router)
    c = TestClient(app)
    pid = c.post("/api/valve/projects", json={"name": "SPEC T"}).json()["id"]

    def up(kind, name, data):
        j = c.post(f"/api/valve/projects/{pid}/upload", data={"kind": kind}, files=[("files", (name, data, "application/pdf"))]).json()
        for _ in range(400):
            if c.get(f"/api/valve/jobs/{j['id']}").json()["status"] == "done":
                return
            time.sleep(0.05)
        raise AssertionError("job did not finish")
    up("datasheet", "ds.pdf", _pdf("A"))
    before = {i["ikey"] for i in c.get(f"/api/valve/projects/{pid}/issues").json()["issues"]}
    up("vspec", "spec.pdf", _spec("ON/OFF VALVE", "777-51-IN-SPC-00003", ONOFF))
    docs = [d for d in c.get(f"/api/valve/projects/{pid}/summary").json()["documents"] if d["kind"] == "vspec"]
    assert docs and docs[0]["info"]["scope"] == "onoff" and docs[0]["info"]["clauses"] >= 10
    issues = c.get(f"/api/valve/projects/{pid}/issues").json()["issues"]
    assert before <= {i["ikey"] for i in issues}                                               # nothing that was there goes away
    sp = [i for i in issues if i["type"] == "Spec Compliance"]
    assert sp and all(i["evidence"][0]["where"].startswith("§") and i["basis"].startswith("Project specification") for i in sp)
    assert all("요구" in (i.get("description_ko") or "") for i in sp)
