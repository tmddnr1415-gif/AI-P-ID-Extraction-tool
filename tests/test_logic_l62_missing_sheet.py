"""L62 — FM/TO 가 가리키는 시트가 묶음에 아직 없으면 '미작성' · 그 시트를 나중에 만들면 칸이 저절로 이어진다."""
from __future__ import annotations

from pathlib import Path

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


def _setup(client):
    a = client.post("/logic/api/drawings", json={"name": "G001", "author": "홍길동"}).json()
    N = a["N"]
    a.update({"sheet_no": "G001",
              "right": {str(N + 3): {"desc": "PUMP START CMD", "kks": "", "to": "G002-5"}},
              "left": {"7": {"fm": "G002-" + str(N + 9), "kks": "", "desc": "PUMP RUNNING"}}})
    r = client.put(f"/logic/api/drawings/{a['id']}", json={"author": "홍길동", "doc": a, "set": "abc123abc123", "set_name": "묶음"})
    assert r.status_code == 200, r.text
    return r.json(), N


def test_missing_sheet_is_listed_then_autolinked_when_created(client):
    a, N = _setup(client)
    st = client.get("/logic/api/drawings/sets/abc123abc123").json()
    miss = st["links"]["missing"]
    assert set(miss) == {"G002"} and len(miss["G002"]) == 2          # 출력 TO 하나 · 입력 FM 하나
    d = client.post("/logic/api/drawings/sets/abc123abc123/sheet", json={"sheet_no": "G002", "author": "홍길동", "N": N}).json()
    assert d["left"]["5"]["fm"] == f"G001-{N + 3}" and d["left"]["5"]["desc"] == "PUMP START CMD"
    assert "G001-7" in d["right"][str(N + 9)]["to"]
    assert len(d["autolinked"]) == 2
    st = client.get("/logic/api/drawings/sets/abc123abc123").json()
    assert st["links"]["missing"] == {}
    L = st["links"]["docs"][a["id"]]
    assert L["right"][str(N + 3)]["targets"][0]["did"] == d["id"] and L["right"][str(N + 3)]["ft"]["ok"] is not False


def test_naming_a_sheet_later_also_links(client):
    a, N = _setup(client)
    b = client.post("/logic/api/drawings/sets/abc123abc123/sheet", json={"author": "홍길동", "N": N}).json()   # 이름 없이
    assert not b.get("left")
    b["sheet_no"] = "G002"
    client.put(f"/logic/api/drawings/{b['id']}", json={"author": "홍길동", "doc": b})
    r = client.post("/logic/api/drawings/sets/abc123abc123/autolink", json={"did": b["id"], "author": "홍길동"}).json()
    assert {c["field"] for c in r["changed"]} == {"fm", "to"}
    assert client.get(f"/logic/api/drawings/{b['id']}").json()["left"]["5"]["fm"] == f"G001-{N + 3}"


def test_screen_shows_states_without_dialog_boxes():
    js = (Path(__file__).resolve().parent.parent / "app/static/logic_draw.js").read_text(encoding="utf-8")
    body = js[js.index("const LINK_ST"):js.index("function linkInfo")]
    for w in ("미작성", "불일치", "설명 다름"):
        assert w in body
    assert "prompt(" not in body and "confirm(" not in body
    assert "addSheet(name)" in js and ".dw-miss button" in js
