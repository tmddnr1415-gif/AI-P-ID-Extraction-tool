"""valve26 — Rev B after Rev A: reviewed automatically, review decisions carried, resolved / not addressed / new counted."""
from __future__ import annotations

import time

import pymupdf

from app.valve import api, revisions
from tests.test_valve import ROWS, _sheet


def _pdf(rev, values=None, notes=None):
    doc = pymupdf.open()
    _sheet(doc, rev, 1, 1, ROWS, notes=notes or ["Bolting: A193 B8M"], values=values)
    data = doc.tobytes()
    doc.close()
    return data


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(api.router)
    c = TestClient(app)
    pid = c.post("/api/valve/projects", json={"name": "P"}).json()["id"]

    def up(name, data):
        j = c.post(f"/api/valve/projects/{pid}/upload", data={"kind": "datasheet"}, files=[("files", (name, data, "application/pdf"))],
                   headers={"X-Author": "eng"}).json()
        for _ in range(200):
            if c.get(f"/api/valve/jobs/{j['id']}").json()["status"] == "done":
                return
            time.sleep(0.05)
        raise AssertionError("job did not finish")
    return c, pid, up


def test_pure_rules():
    cmp_rows = [{"key": "design_pressure", "change": "Added"}, {"key": "seat_material", "change": "Unchanged"}]
    prev = {"Data Missing:design_pressure": {"status": "Dismissed", "note": "n/a"},
            "Material Review:seat_material.MR-01": {"status": "Confirmed", "note": ""},
            "Data Missing:op_pressure": {"status": "Resolved"}}
    new_ikeys = {"Material Review:seat_material.MR-01", "Data Missing:op_pressure"}
    out = revisions.carry_states(prev, cmp_rows, new_ikeys, "A")
    assert [(o["ikey"], o["status"]) for o in out] == [("Material Review:seat_material.MR-01", "Confirmed")]   # changed field · resolved: not carried
    assert "not addressed" in out[0]["note"]
    rr = revisions.rev_review([{"ikey": "Data Missing:design_pressure", "type": "Data Missing"}, {"ikey": "Material Review:seat_material.MR-01", "type": "Material Review"}],
                              [{"ikey": "Material Review:seat_material.MR-01", "type": "Material Review"}, {"ikey": "Data Error:line_no", "type": "Data Error"}],
                              {k: v for k, v in prev.items() if "design_pressure" not in k}, cmp_rows, "A")   # an Open issue that is gone = resolved
    assert (rr["resolved"], rr["still_open"], rr["new"]) == (1, 1, 1) and rr["changed_fields"] == 1


def test_rev_b_inherits_review(tmp_path, monkeypatch):
    c, pid, up = _client(tmp_path, monkeypatch)
    up("ds_A.pdf", _pdf("A"))
    a = c.get(f"/api/valve/datasheets/{c.get(f'/api/valve/projects/{pid}/summary').json()['tags'][0]['id']}").json()
    assert a["rev"] == "A" and a["rev_review"] is None
    miss = [i for i in a["issues"] if i["type"] == "Data Missing"]
    op = next(i for i in miss if i["key"].startswith("op_pressure"))
    dp = next(i for i in miss if i["key"].startswith("design_pressure"))
    H = {"X-Author": "eng"}
    c.put(f"/api/valve/datasheets/{a['id']}/issues/{op['ikey']}", json={"status": "Dismissed", "note": "process DS"}, headers=H)
    c.put(f"/api/valve/datasheets/{a['id']}/issues/{dp['ikey']}", json={"status": "Confirmed"}, headers=H)
    fid = next(f for f in a["fields"] if f["key"] == "seat_material")
    c.post(f"/api/valve/datasheets/{a['id']}/comments", json={"text": "seat P-T curve?", "field_key": "seat_material"}, headers=H)
    # Rev B: body size changed, seat unchanged, both process cells still blank
    up("ds_B.pdf", _pdf("B", values={6: ['3"', "Ball (Full Bore) - Floating"]}))
    tags = c.get(f"/api/valve/projects/{pid}/summary").json()["tags"]
    assert len(tags) == 1 and tags[0]["rev"] == "B"
    b = c.get(f"/api/valve/datasheets/{tags[0]['id']}").json()
    assert b["rev"] == "B" and b["rev_review"]["prev_rev"] == "A"
    st = {i["ikey"]: i for i in b["issues"]}
    assert st[op["ikey"]]["status"] == "Dismissed" and "Carried from Rev A" in st[op["ikey"]]["note"]      # same objection, same blank
    assert st[dp["ikey"]]["status"] == "Confirmed" and st[dp["ikey"]].get("since") == "A"
    assert st[dp["ikey"]]["description"].startswith("Not addressed since Rev A") and st[dp["ikey"]]["severity"] == "Major"
    assert b["rev_review"]["still_open"] == 1 and b["rev_review"]["changed_fields"] >= 1
    assert any(i["type"] == "Revision Change" and i["key"] == "body_size" for i in b["issues"])
    cm = [x for x in b["comments"] if x["field_key"] == "seat_material"]
    assert cm and cm[0]["origin"] == "Rev A" and cm[0]["text"] == "seat P-T curve?"
    assert any(h["action"] == "carry" for h in b["history"])
    # Rev C fixes the design pressure: the confirmed issue is gone -> resolved, nothing carried for it
    up("ds_C.pdf", _pdf("C", values={5: ["", "10 barg"], 6: ['3"', "Ball (Full Bore) - Floating"]}))
    tags = c.get(f"/api/valve/projects/{pid}/summary").json()["tags"]
    cc = c.get(f"/api/valve/datasheets/{tags[0]['id']}").json()
    assert cc["rev"] == "C" and dp["ikey"] not in {i["ikey"] for i in cc["issues"]}
    assert cc["rev_review"]["resolved"] >= 1 and cc["rev_review"]["still_open"] == 0
    assert {i["ikey"]: i for i in cc["issues"]}[op["ikey"]]["status"] == "Dismissed"              # dismissed in A, still dismissed in C
