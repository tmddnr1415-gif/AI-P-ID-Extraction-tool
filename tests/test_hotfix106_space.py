"""hotfix106 — 판넬 공간확보가 P&ID · LOGIC 과 같은 서버(8000)의 /space 로 돈다."""
from __future__ import annotations

import ast
import json
import shutil
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from app import space
from app.main import app

ROOT = Path(__file__).resolve().parent.parent
ME = {"X-Author": quote("홍길동")}


def _plan(n=3):
    return {"room": {"w": 21000, "l": 18000}, "types": [{"id": "t1", "name": "SC", "w": 800, "d": 800}],
            "panels": [{"id": f"p{i}", "type": "t1", "x": i * 800, "y": 0} for i in range(n)], "info": {"rev": "A"}}


@pytest.fixture()
def client():
    shutil.rmtree(space._root(), ignore_errors=True)
    with TestClient(app) as c:
        yield c
    shutil.rmtree(space._root(), ignore_errors=True)


def test_page_and_api_paths(client):
    r = client.get("/space?embed=1&user=홍길동")
    assert r.status_code == 200 and "판넬 공간확보" in r.text and "/space/api" in r.text
    assert client.get("/space/api/projects").json() == {"projects": []}


def test_save_needs_a_name_and_keeps_history(client):
    r = client.post("/space/api/projects", json={"name": "AL DHAFRA"})
    assert r.status_code == 401 and "이름" in r.json()["error"]
    p = client.post("/space/api/projects", json={"name": "AL DHAFRA"}, headers=ME).json()
    assert p["createdBy"] == "홍길동"
    assert client.post("/space/api/projects", json={"name": "al dhafra"}, headers=ME).status_code == 409
    m1 = client.post(f"/space/api/{p['id']}/saves", content=json.dumps({"data": _plan(3), "memo": "첫 안"}), headers=ME).json()
    m2 = client.post(f"/space/api/{p['id']}/saves", content=json.dumps({"data": _plan(5)}), headers=ME).json()
    got = client.get(f"/space/api/{p['id']}").json()
    assert [m["id"] for m in got["saves"]] == [m2["id"], m1["id"]]        # 최신이 앞 (대시보드와 같다)
    assert client.get(f"/space/api/{p['id']}/saves/{m1['id']}").json()["data"]["panels"].__len__() == 3
    assert client.get("/space/api/recent?n=1").json()["saves"][0]["id"] == m2["id"]
    bad = client.post(f"/space/api/{p['id']}/saves", content=json.dumps({"data": {"room": {}}}), headers=ME)
    assert bad.status_code == 400 and "배치안" in bad.json()["error"]


def test_notes_only_own_can_be_deleted(client):
    p = client.post("/space/api/projects", json={"name": "X"}, headers=ME).json()
    n = client.post(f"/space/api/{p['id']}/notes", json={"text": "기둥 확인"}, headers=ME).json()
    other = {"X-Author": quote("김철수")}
    assert client.delete(f"/space/api/{p['id']}/notes/{n['id']}", headers=other).status_code == 403
    assert client.delete(f"/space/api/{p['id']}/notes/{n['id']}", headers=ME).json() == {"status": "ok"}


def test_bad_ids_are_refused(client):
    assert client.get("/space/api/..%2F..").status_code in (400, 404)
    assert client.get("/space/api/abc").status_code == 400


def test_import_from_dashboard_is_idempotent(client):
    pid, s1, s2 = "lzk1abc123", "lzk1abc124", "lzk1abc125"
    remote = {
        "/projects": {"projects": [{"id": pid, "name": "TC2", "createdAt": "2026-10-20T01:00:00.000Z", "createdBy": "이영희"}]},
        f"/{pid}": {"project": {"id": pid, "name": "TC2", "createdAt": "2026-10-20T01:00:00.000Z", "createdBy": "이영희"},
                    "saves": [{"id": s2, "at": "2026-10-21T00:00:00.000Z", "by": "이영희"},
                              {"id": s1, "at": "2026-10-20T02:00:00.000Z", "by": "이영희"}],
                    "notes": [{"id": "lzk1note01", "at": "2026-10-20T03:00:00.000Z", "by": "이영희", "text": "n"}]},
        f"/{pid}/saves/{s1}": {"meta": {"id": s1, "at": "2026-10-20T02:00:00.000Z", "by": "이영희"}, "data": _plan(2)},
        f"/{pid}/saves/{s2}": {"meta": {"id": s2, "at": "2026-10-21T00:00:00.000Z", "by": "이영희"}, "data": _plan(4)},
    }
    g = space.import_dashboard("홍길동", "http://127.0.0.1:8080", fetch=remote.__getitem__)
    assert (g["projects_new"], g["saves_new"], g["notes_new"]) == (1, 2, 1)
    got = client.get(f"/space/api/{pid}").json()
    assert got["project"]["createdBy"] == "이영희" and [m["id"] for m in got["saves"]] == [s2, s1]
    again = space.import_dashboard("홍길동", "http://127.0.0.1:8080", fetch=remote.__getitem__)
    assert (again["projects_new"], again["saves_new"], again["notes_new"], again["saves_seen"]) == (0, 0, 0, 2)


def test_import_refuses_outside_addresses():
    with pytest.raises(space._Err):
        space.import_dashboard("홍길동", "http://8.8.8.8:8080", fetch=lambda p: {})
    with pytest.raises(space._Err):
        space.import_dashboard("홍길동", "file:///etc", fetch=lambda p: {})


def test_page_has_no_browser_dialogs():
    src = (ROOT / "app/static/space/index.html").read_text(encoding="utf-8")
    assert "confirm(" not in src and "prompt(" not in src and "alert(" not in src   # 대시보드 iframe 은 막는다


def test_router_is_mounted_and_imports_no_engine():
    tree = ast.parse((ROOT / "app/space.py").read_text(encoding="utf-8"))
    mods = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | \
           {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not any(m and ("engine" in m or "pipeline" in m) for m in mods)
    assert "include_router(_space.router)" in (ROOT / "app/main.py").read_text(encoding="utf-8")
