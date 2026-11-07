"""hotfix132 (D4) — LOGIC 작도 저장 충돌: 화면이 연 판(base: saves · updated)을 보내고 서버 판이 다르면 409 ·
force 또는 절전모드 되보내기(X-Offline-Replay)는 덮어쓴다 · base 없는 옛 요청은 지금처럼."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.logic import draw


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    from app.logic import api
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def _new(client):
    r = client.post("/logic/api/drawings", json={"name": "충돌", "author": "홍길동", "N": 50})
    assert r.status_code == 200
    return r.json()


def test_stale_base_is_409_and_first_save_kept(client):
    d0 = _new(client)
    base = {"saves": d0["saves"], "updated": d0["updated"]}
    r1 = client.put(f"/logic/api/drawings/{d0['id']}", json={"author": "김영희", "doc": {"name": "영희 판"}, "base": base})
    assert r1.status_code == 200 and r1.json()["saves"] == 1
    r2 = client.put(f"/logic/api/drawings/{d0['id']}", json={"author": "홍길동", "doc": {"name": "길동 판"}, "base": base})
    assert r2.status_code == 409
    j = r2.json()
    assert "김영희" in j["detail"] and "저장했습니다" in j["detail"] and j["current"]["saves"] == 1
    cur = draw.load(d0["id"])
    assert cur["name"] == "영희 판" and cur["saves"] == 1
    assert "base" not in cur and "force" not in cur


def test_force_and_offline_replay_overwrite(client):
    d0 = _new(client)
    base = {"saves": d0["saves"], "updated": d0["updated"]}
    client.put(f"/logic/api/drawings/{d0['id']}", json={"author": "김영희", "doc": {"name": "영희 판"}, "base": base})
    r = client.put(f"/logic/api/drawings/{d0['id']}", json={"author": "홍길동", "doc": {"name": "길동 판"}, "base": base, "force": True})
    assert r.status_code == 200 and r.json()["name"] == "길동 판" and r.json()["saves"] == 2
    r = client.put(f"/logic/api/drawings/{d0['id']}", json={"author": "박철수", "doc": {"name": "철수 판"}, "base": base},
                   headers={"X-Offline-Replay": "1"})
    assert r.status_code == 200 and r.json()["name"] == "철수 판" and r.json()["saves"] == 3
    assert "force" not in draw.load(d0["id"])


def test_without_base_old_requests_still_save(client):
    d0 = _new(client)
    client.put(f"/logic/api/drawings/{d0['id']}", json={"author": "김영희", "doc": {"name": "영희 판"}})
    r = client.put(f"/logic/api/drawings/{d0['id']}", json={"author": "홍길동", "doc": {"name": "길동 판"}})
    assert r.status_code == 200 and r.json()["saves"] == 2


def test_matching_base_saves_and_set_make_body(client):
    d0 = _new(client)
    r = client.put(f"/logic/api/drawings/{d0['id']}", json={"author": "홍길동", "doc": {"name": "A"}, "set": "abc123abc123",
                                                           "set_name": "묶음", "base": {"saves": 0, "updated": d0["updated"]}})
    assert r.status_code == 200 and r.json()["set"] == "abc123abc123"
    cur = draw.load(d0["id"])
    r = client.put(f"/logic/api/drawings/{d0['id']}", json={"author": "홍길동", "doc": {"name": "B"}, "base": {"saves": cur["saves"], "updated": cur["updated"]}})
    assert r.status_code == 200 and r.json()["name"] == "B"


def test_save_conflict_raised_inside_lock():
    doc = draw.save_new(draw.new_doc("잠금", "홍길동"))
    cur = draw.load(doc["id"])
    with pytest.raises(draw.Conflict) as ei:
        draw.save(doc["id"], {"name": "x"}, "김영희", base={"saves": (cur.get("saves") or 0) + 7, "updated": cur.get("updated")})
    assert ei.value.current["saves"] == (cur.get("saves") or 0)
