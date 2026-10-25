"""hotfix116 — 판넬 공간확보 최신판(대시보드 2026-10-24): 프로젝트 → 룸 → Rev · 지우기(휴지통)를 /space 서버도 한다."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from app import space
from app.main import app

ROOT = Path(__file__).resolve().parent.parent
ME = {"X-Author": quote("홍길동")}
OTHER = {"X-Author": quote("김철수")}


def _plan(rev="A"):
    return {"room": {"w": 21000, "l": 18000}, "types": [{"id": "t1", "name": "SC", "w": 800, "d": 800}],
            "panels": [{"id": "p1", "type": "t1", "x": 0, "y": 0}], "info": {"rev": rev}}


@pytest.fixture()
def client():
    shutil.rmtree(space._root(), ignore_errors=True)
    with TestClient(app) as c:
        yield c
    shutil.rmtree(space._root(), ignore_errors=True)


def test_rooms_and_revs(client):
    p = client.post("/space/api/projects", json={"name": "AMIRAL"}, headers=ME).json()
    r = client.post(f"/space/api/{p['id']}/rooms", json={"name": "CER-1"}, headers=ME).json()
    assert r["createdBy"] == "홍길동" and r["revs"] == []
    assert client.post(f"/space/api/{p['id']}/rooms", json={"name": "cer-1"}, headers=ME).status_code == 409
    r = client.post(f"/space/api/{p['id']}/rooms/{r['id']}/revs", json={"rev": "A", "note": "첫 배치"}, headers=ME).json()
    assert [v["rev"] for v in r["revs"]] == ["A"]
    assert client.post(f"/space/api/{p['id']}/rooms/{r['id']}/revs", json={"rev": "A"}, headers=ME).status_code == 409
    m = client.post(f"/space/api/{p['id']}/saves", content=json.dumps({"data": _plan("B"), "room": r["id"]}), headers=ME).json()
    assert m["room"] == r["id"] and m["roomName"] == "CER-1" and m["rev"] == "B"
    got = client.get(f"/space/api/{p['id']}").json()
    assert [v["rev"] for v in got["rooms"][0]["revs"]] == ["A", "B"]          # 저장한 Rev 도 룸 목록에
    lst = client.get("/space/api/projects").json()["projects"][0]
    assert lst["rooms"] == [{"id": r["id"], "name": "CER-1", "revs": ["A", "B"]}]


def test_delete_moves_to_trash_and_only_maker(client):
    p = client.post("/space/api/projects", json={"name": "X"}, headers=ME).json()
    r = client.post(f"/space/api/{p['id']}/rooms", json={"name": "R"}, headers=ME).json()
    client.post(f"/space/api/{p['id']}/rooms/{r['id']}/revs", json={"rev": "A"}, headers=ME)
    m = client.post(f"/space/api/{p['id']}/saves", content=json.dumps({"data": _plan("A"), "room": r["id"]}), headers=ME).json()
    assert client.delete(f"/space/api/{p['id']}/rooms/{r['id']}/revs?rev=A", headers=OTHER).status_code == 403
    assert client.delete(f"/space/api/{p['id']}/rooms/{r['id']}/revs?rev=A", headers=ME).json() == {"status": "ok", "saves": 1}
    assert not (space._root() / p["id"] / "saves" / f"{m['id']}.json").exists()
    assert list((space._root() / "_trash" / p["id"]).glob("*_rev/saves/*.json"))
    assert client.delete(f"/space/api/{p['id']}/rooms/{r['id']}", headers=ME).json()["status"] == "ok"
    assert client.get(f"/space/api/{p['id']}").json()["rooms"] == []
    assert client.delete(f"/space/api/{p['id']}", headers=OTHER).status_code == 403
    assert client.delete(f"/space/api/{p['id']}", headers=ME).json()["status"] == "ok"
    assert client.get("/space/api/projects").json() == {"projects": []}       # _trash 는 목록에 안 나온다
    assert list((space._root() / "_trash").glob(f"{p['id']}_*_project/deleted.json"))


def test_screen_is_the_latest_dashboard_version():
    """대시보드 브랜치의 최신 판넬 화면을 들여왔는지 — 그 판에만 있는 기능 몇 개가 있어야 한다."""
    h = (ROOT / "app" / "static" / "space" / "index.html").read_text(encoding="utf-8")
    for k in ("hmRoomNew", "hmRevNew", "hmProjDel", "set('view','3d')", "open3d", "/space/api", "askYes(", "askText("):
        assert k in h, k
    for bad in ("confirm(", "prompt(", "alert("):                             # 대시보드 iframe 은 막는다
        assert bad not in h, bad
    js = h[h.index("<script>") + 8:h.rindex("</script>")]
    r = subprocess.run(["node", "-e", "new Function(require('fs').readFileSync(0,'utf8'))"], input=js,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_dashboard_loader_forwards_to_pid_server():
    """대시보드 폴더의 apps/space/index.html 은 P&ID 서버(8000)의 /space 로 넘긴다 (주소 뒤 값 그대로)."""
    h = (ROOT / "dashboard_apps" / "space" / "index.html").read_text(encoding="utf-8")
    assert "PID_PORT = 8000" in h and "'/space' + location.search" in h and "/version" in h and "location.replace(target)" in h
    for bad in ("confirm(", "prompt(", "alert("):
        assert bad not in h
