"""가상 광장 — 대시보드 '최근 변경 이력' 아래에 iframe 으로 들어가는 작은 마을."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import plaza
from app.main import app

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def client():
    plaza.reset()
    with TestClient(app) as c:
        yield c
    plaza.reset()


def test_page_is_served(client):
    r = client.get("/plaza?embed=1&user=홍길동")
    assert r.status_code == 200 and "pz-map" in r.text
    assert client.get("/static/plaza.js").status_code == 200


def test_join_move_say_shows_in_snapshot(client):
    a = client.post("/plaza/api/join", json={"name": " 홍길동 ", "look": 5, "x": 25, "y": 15}).json()
    b = client.post("/plaza/api/join", json={"name": "김철수"}).json()
    assert a["name"] == "홍길동"
    assert client.post("/plaza/api/move", json={"id": a["id"], "x": 26, "y": 15, "dir": 3}).status_code == 200
    r = client.post("/plaza/api/say", json={"id": b["id"], "text": "안녕하세요\n\n반갑습니다"})
    assert r.json()["text"] == "안녕하세요 반갑습니다"
    snap = plaza.snapshot()
    me = next(p for p in snap["players"] if p["id"] == a["id"])
    assert (me["x"], me["y"], me["dir"]) == (26, 15, 3)
    him = next(p for p in snap["players"] if p["id"] == b["id"])
    assert him["say"] == "안녕하세요 반갑습니다" and him["say_left"] > 0
    assert snap["online"] == 2
    assert any(m["name"] == "김철수" and m["text"] == "안녕하세요 반갑습니다" for m in snap["log"])


def test_limits(client):
    assert client.post("/plaza/api/join", json={"name": "  "}).status_code == 400
    a = client.post("/plaza/api/join", json={"name": "가" * 50}).json()
    assert len(a["name"]) == plaza.NAME_MAX
    assert client.post("/plaza/api/say", json={"id": a["id"], "text": "   "}).status_code == 400
    r = client.post("/plaza/api/say", json={"id": a["id"], "text": "말" * 300}).json()
    assert len(r["text"]) == plaza.SAY_MAX
    assert client.post("/plaza/api/say", json={"id": "nope", "text": "x"}).status_code == 404
    client.post("/plaza/api/move", json={"id": a["id"], "x": 9999, "y": -5, "dir": 0})
    p = plaza.snapshot()["players"][0]
    assert (p["x"], p["y"]) == (plaza.MAP_W - 1, 0)


def test_leave_and_idle_prune(client):
    a = client.post("/plaza/api/join", json={"name": "이영희"}).json()
    assert client.post("/plaza/api/leave", content=f'{{"id": "{a["id"]}"}}').status_code == 200
    assert plaza.snapshot()["online"] == 0
    b = client.post("/plaza/api/join", json={"name": "박민수"}).json()
    import time
    assert plaza.snapshot(time.time() + plaza.IDLE_S + 1)["online"] == 0   # 스트림 없이 조용하면 나간다
    assert any("떠났습니다" in m["text"] for m in plaza.snapshot()["log"])
    assert b["id"]


def test_screen_rules():
    js = (ROOT / "app/static/plaza.js").read_text(encoding="utf-8")
    # 대시보드 iframe 은 prompt/confirm 을 막는다 · 사람이 적은 글은 HTML 로 넣지 않는다
    assert not re.search(r"\b(prompt|confirm|alert)\s*\(", js)
    assert "innerHTML" not in js
    # 메뉴를 따로 만들지 않는다 (사용자 지시) — 대시보드 카드 안에 들어간다
    assert "/plaza" not in (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    m = re.search(r"const T = 32, W = (\d+), H = (\d+);", js)
    assert m and (int(m.group(1)), int(m.group(2))) == (plaza.MAP_W, plaza.MAP_H)
