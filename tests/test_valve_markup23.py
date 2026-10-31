"""valve23 — annotator mark-ups: underline / strike / squiggle / stamp with a style (colour · width) round-trip to the PDF."""
from __future__ import annotations

import time

import pymupdf
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.valve import api
from tests.test_valve import make_pdf


def test_annotator_marks_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    app = FastAPI()
    app.include_router(api.router)
    c = TestClient(app)
    pid = c.post("/api/valve/projects", json={"name": "P"}).json()["id"]
    jb = c.post(f"/api/valve/projects/{pid}/upload", data={"kind": "datasheet"}, files=[("files", ("ds.pdf", make_pdf(), "application/pdf"))]).json()
    for _ in range(100):
        if c.get(f"/api/valve/jobs/{jb['id']}").json()["status"] == "done":
            break
        time.sleep(0.1)
    j = c.get(f"/api/valve/projects/{pid}/summary").json()
    ds, tag = j["tags"][0]["id"], j["tags"][0]["tag_key"]
    marks = [
        {"page": 1, "kind": "underline", "bbox": [40, 112, 160, 124], "style": {"color": "#1aa35a", "width": 2}},
        {"page": 1, "kind": "strike", "bbox": [40, 132, 120, 144]},
        {"page": 1, "kind": "squiggle", "bbox": [40, 52, 140, 66], "style": {"color": "#8e3fd6"}},
        {"page": 1, "kind": "stamp", "bbox": [300, 60, 380, 82], "style": {"stamp": "APPROVED", "color": "#db2626"}},
        {"page": 1, "kind": "stamp", "bbox": [400, 60, 418, 78], "style": {"stamp": "✓"}},
        {"page": 1, "kind": "pen", "bbox": [200, 200, 260, 240], "points": [[[200, 200], [230, 240], [260, 200]]], "style": {"width": 5, "color": "#111111"}},
        {"page": 1, "kind": "rect", "bbox": [50, 300, 150, 340], "style": {"color": "zzz", "width": 99}},   # bad colour dropped · width clamped
    ]
    ids = []
    for m in marks:
        r = c.post(f"/api/valve/datasheets/{ds}/comments", json=dict(m, text="", category="comment"))
        assert r.status_code == 200, r.text
        ids.append(r.json()["new_comment_id"])
    d = c.get(f"/api/valve/datasheets/{ds}").json()
    by = {x["id"]: x for x in d["comments"]}
    assert by[ids[0]]["style"] == {"color": "#1aa35a", "width": 2.0} and by[ids[3]]["style"]["stamp"] == "APPROVED"
    assert by[ids[6]]["style"] == {"width": 8.0}                                  # clamp, invalid colour ignored
    assert c.put(f"/api/valve/comments/{ids[1]}", json={"style": {"color": "#ff8c00"}}).status_code == 200
    assert c.put(f"/api/valve/comments/{ids[0]}", json={"style": None}).status_code == 200
    assert c.post(f"/api/valve/datasheets/{ds}/comments", json={"page": 1, "kind": "banana", "bbox": [1, 1, 2, 2], "text": "x"}).status_code == 400
    pdf = c.get(f"/api/valve/projects/{pid}/markup.pdf?tag={tag}").content
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    types = sorted(a.type[1] for pg in doc for a in pg.annots())
    for t in ("Underline", "StrikeOut", "Squiggly", "FreeText", "Ink"):
        assert t in types, (t, types)
    assert any(a.info.get("content") == "APPROVED" for pg in doc for a in pg.annots())
    assert sum(1 for pg in doc for a in pg.annots() if a.type[1] == "Ink") >= 2            # pen + the ✓ glyph
