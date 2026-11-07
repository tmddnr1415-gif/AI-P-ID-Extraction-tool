"""L63 — 공통 Typical 사전: 씨앗으로 처음부터 들고 있고 (빈 서버에서도), 사람이 작도에서 고쳐 저장하면 모든 프로젝트가 그것을 쓴다."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PID_TYPICAL_SEED", "1")
    from app.logic import api
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def test_fresh_server_already_knows_the_common_typicals(client):
    from app.logic import library
    r = client.get("/logic/api/drawings/typicals").json()
    assert r["seed"] >= 20 and len(r["items"]) == r["seed"]
    titles = " ".join(i["title"] for i in r["items"])
    for w in ("MOV", "SOV", "GROUP", "SWGR"):
        assert w in titles
    assert all(i["origin"] == "seed" and i["pins_in"] and i["pins_out"] for i in r["items"])
    assert len(library.load()["typicals"]) == r["seed"]             # 분석(macro.link)도 같은 사전을 읽는다


def test_user_edits_a_typical_and_can_revert(client):
    from app.logic import library
    items = client.get("/logic/api/drawings/typicals").json()["items"]
    it = next(i for i in items if "MOV" in i["title"])
    d = client.post(f"/logic/api/drawings/typicals/{it['id']}/open", json={"author": "홍길동"}).json()
    assert d["typical"] and d["source"]["typlib"] == it["id"]
    again = client.post(f"/logic/api/drawings/typicals/{it['id']}/open", json={"author": "홍길동"}).json()
    assert again["id"] == d["id"]                                   # 꺼낸 그림이 있으면 그것을
    k = next(k for k, v in d["left"].items() if v.get("desc"))
    d["left"][k]["desc"] = "EDITED SIGNAL NAME"
    r = client.put(f"/logic/api/drawings/{d['id']}", json={"author": "홍길동", "doc": d})
    assert r.status_code == 200
    r = client.post("/logic/api/drawings/typicals", json={"did": d["id"], "author": "홍길동"})
    assert r.status_code == 200, r.text
    ty = library.typicals()[it["id"]]
    assert ty["origin"] == "user" and ty["edited"]["author"] == "홍길동"
    assert any(t.get("desc") == "EDITED SIGNAL NAME" for t in ty["sheet"]["table"])   # 분석기로 되읽은 시트에 반영
    lst = {i["id"]: i for i in client.get("/logic/api/drawings/typicals").json()["items"]}
    assert lst[it["id"]]["origin"] == "user"
    r = client.post(f"/logic/api/drawings/typicals/{it['id']}/revert", json={"author": "홍길동"}).json()
    assert library.typicals()[it["id"]]["origin"] == "seed"
    back = client.get(f"/logic/api/drawings/{d['id']}").json()
    assert back["left"][k]["desc"] != "EDITED SIGNAL NAME"


def test_saving_needs_a_name_and_project_typical_can_be_added(client):
    from app.logic import draw, library
    a = client.post("/logic/api/drawings", json={"name": "T1", "author": "홍길동"}).json()
    seed_id = next(iter(library.seed_typicals()))
    src = draw.from_sheet(library.seed_typicals()[seed_id]["sheet"], "T9001", "홍길동")
    src = {k: v for k, v in src.items() if k not in ("id",)}
    src.update(sheet_no="T9001", title="MY NEW TYPICAL", typical=True)
    client.put(f"/logic/api/drawings/{a['id']}", json={"author": "홍길동", "doc": src})
    assert client.post("/logic/api/drawings/typicals", json={"did": a["id"], "author": ""}).status_code == 400
    r = client.post("/logic/api/drawings/typicals", json={"did": a["id"], "author": "홍길동"}).json()
    assert library.typicals()[r["id"]]["title"] == "MY NEW TYPICAL" and r.get("did")
    r2 = client.post(f"/logic/api/drawings/typicals/{r['id']}/revert", json={"author": "홍길동"}).json()
    assert r2.get("removed") and r["id"] not in library.typicals()
