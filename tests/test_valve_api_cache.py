"""valve21 — cached responses must survive the gzip middleware (a cached Response object had its headers mutated in place,
so the second GET of /grid failed with ERR_CONTENT_LENGTH_MISMATCH and the Valve List never loaded)."""
from __future__ import annotations

import io

import pymupdf
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.gzip import GZipMiddleware

from app.valve import api


def _pdf():
    doc = pymupdf.open()
    pg = doc.new_page(width=595, height=842)
    pg.insert_text((40, 60), "On / Off Valve", fontsize=10)
    pg.insert_text((40, 90), "Doc. No.: 98-51-IN-DTS-00002", fontsize=8)
    pg.insert_text((40, 120), "1 Tag No. 98ESDV 980001", fontsize=8)
    pg.insert_text((40, 140), "21 Body Size 2\"", fontsize=8)
    return doc.tobytes()


def test_grid_and_issues_twice_under_gzip(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    app = FastAPI()
    app.add_middleware(GZipMiddleware, minimum_size=1)
    app.include_router(api.router)
    c = TestClient(app)
    pid = c.post("/api/valve/projects", json={"name": "P"}).json()["id"]
    c.post(f"/api/valve/projects/{pid}/upload", data={"kind": "datasheet"}, files=[("files", ("ds.pdf", _pdf(), "application/pdf"))])
    for _ in range(100):
        j = c.get(f"/api/valve/projects/{pid}/summary").json()
        if not any(d["status"] in ("queued", "running") for d in j["documents"]):
            break
    for u in (f"/api/valve/projects/{pid}/grid", f"/api/valve/projects/{pid}/issues", f"/api/valve/projects/{pid}/summary",
              f"/api/valve/projects/{pid}/pms", f"/api/valve/projects/{pid}/process", f"/api/valve/projects/{pid}/tagging"):
        a, b = c.get(u), c.get(u)                       # second call is served from the cache
        assert a.status_code == 200 and b.status_code == 200, u
        assert a.json() == b.json(), u
    assert c.get("/api/valve/version").json()["version"].startswith("valve")
