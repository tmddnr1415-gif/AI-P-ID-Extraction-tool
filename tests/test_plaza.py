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
    import shutil
    shutil.rmtree(plaza._dir(), ignore_errors=True)        # 시험마다 역할 · 외형 파일을 비운다
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


def test_space_attack_hits_whoever_stands_in_front(client):
    a = client.post("/plaza/api/join", json={"name": "김철수", "x": 29, "y": 15}).json()
    b = client.post("/plaza/api/join", json={"name": "홍길동", "x": 28, "y": 15}).json()
    c = client.post("/plaza/api/join", json={"name": "이영희", "x": 29, "y": 20}).json()
    client.post("/plaza/api/move", json={"id": a["id"], "x": 29, "y": 15, "dir": 2})   # 왼쪽을 본다
    r = client.post("/plaza/api/attack", json={"id": a["id"]}).json()
    assert r["hit"] == ["홍길동"]
    snap = {p["name"]: p for p in plaza.snapshot()["players"]}
    assert snap["홍길동"]["hit_seq"] == 1 and snap["홍길동"]["hit_by"] == "김철수"
    assert snap["김철수"]["act_seq"] == 1 and snap["이영희"]["hit_seq"] == 0
    # 한 번 휘두르는 동안 또 누르면 무시
    assert client.post("/plaza/api/attack", json={"id": a["id"]}).json()["hit"] == []
    assert plaza.snapshot()["players"][0]["act_seq"] == 1
    assert client.post("/plaza/api/attack", json={"id": "nope"}).status_code == 404
    assert c["id"] and b["id"]
    js = (ROOT / "app/static/plaza.js").read_text(encoding="utf-8")
    assert '"/plaza/api/attack"' in js and 'ev.code === "Space"' in js


def test_face_ranges_match_the_screen():
    js = (ROOT / "app/static/plaza.js").read_text(encoding="utf-8")
    names = {"hair": "HAIRS", "hairc": "HAIRC", "skin": "SKINS", "eyes": "EYES", "beard": "BEARDS",
             "cloth": "CLOTHS", "pants": "PANTS"}
    for key, const in names.items():
        m = re.search(rf"const {const} = \[(.*?)\];", js, re.S)
        assert m, const
        assert len(re.findall(r'"[^"]*"', m.group(1))) == plaza.LOOK_RANGES[key], key


def test_face_is_saved_per_name_and_comes_back(client):
    a = client.post("/plaza/api/join", json={"name": "박민수"}).json()
    assert a["face"] is None and a["role"] == "member"
    face = {"hair": 6, "hairc": 2, "skin": 1, "eyes": 4, "beard": 3, "cloth": 2, "pants": 5}
    assert client.post("/plaza/api/look", json={"id": a["id"], "look": face}).json()["face"] == face
    assert client.post("/plaza/api/look", json={"id": a["id"], "look": {"hair": "x"}}).status_code == 400
    assert plaza.clean_look({**face, "hair": 99})["hair"] == 99 % plaza.LOOK_RANGES["hair"]
    client.post("/plaza/api/leave", content=f'{{"id": "{a["id"]}"}}')
    b = client.post("/plaza/api/join", json={"name": "박민수", "face": {**face, "hair": 0}}).json()
    assert b["face"] == face                              # 저장된 얼굴이 이긴다


def test_roles_come_from_the_server_and_only_operators_change_them(client):
    rolefile = plaza._roles_file()
    a = client.post("/plaza/api/join", json={"name": "홍길동"}).json()
    assert rolefile.exists() and a["role"] == "member"   # 빈 틀을 만든다
    import json
    rolefile.write_text(json.dumps({"operators": ["홍길동"], "group_leader": ["이영희"]}, ensure_ascii=False), encoding="utf-8")
    import os, time
    os.utime(rolefile, (time.time() + 5, time.time() + 5))
    b = client.post("/plaza/api/join", json={"name": "김철수"}).json()
    assert b["role"] == "member"
    assert client.post("/plaza/api/role", json={"id": b["id"], "target": "김철수", "role": "leader"}).status_code == 403
    assert client.get(f"/plaza/api/roles?id={b['id']}").status_code == 403
    op = client.post("/plaza/api/join", json={"name": "홍길동"}).json()
    assert op["role"] == "operator"
    r = client.post("/plaza/api/role", json={"id": op["id"], "target": "김철수", "role": "unit"}).json()
    assert "김철수" in r["roles"]["unit_leaders"]
    assert {p["name"]: p["role"] for p in plaza.snapshot()["players"]}["김철수"] == "unit"
    assert client.post("/plaza/api/role", json={"id": op["id"], "target": "김철수", "role": "king"}).status_code == 400
    assert plaza.role_of("이영희") == "leader"
    js = (ROOT / "app/static/plaza.js").read_text(encoding="utf-8")
    assert "왕관" in js and "사모" in js and "노비" in js and "부여성 남쪽" in js


def test_movement_is_arrow_keys_only():
    js = (ROOT / "app/static/plaza.js").read_text(encoding="utf-8")
    m = re.search(r"const KEYDIR = \{(.*?)\};", js, re.S)
    keys = set(re.findall(r"(\w+):", m.group(1)))
    assert keys == {"ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight", "Down", "Up", "Left", "Right"}
    assert "arrowOf(ev)" in js                              # code · keyCode 도 본다 (입력기 켜진 PC)
