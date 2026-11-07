"""L64c — 계기 리스트(Instrument List Excel): TAG → 설명 · 다시 올리면 바뀐 설명을 그림에 반영하고 표시 · 없어진 TAG 는 화면이 경고."""
from __future__ import annotations

import io

import openpyxl
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.logic import draw, instruments


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    from app.logic import api
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def _xlsx(rows, title="INSTRUMENT LIST"):
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "LIST"
    ws.append([title]); ws.append([])
    ws.append(["NO.", "KKS NO.", "INSTRUMENT TYPE", "DESCRIPTION", "REMARK"])
    for i, (tag, typ, desc) in enumerate(rows, 1):
        ws.append([i, tag, typ, desc, ""])
    b = io.BytesIO(); wb.save(b); return b.getvalue()


def _up(client, data, project="P1", name="list.xlsx"):
    return client.post("/logic/api/drawings/instruments", files={"file": (name, data)}, data={"project": project, "author": "홍길동"})


def test_parse_finds_header_and_tags():
    got = instruments.parse(_xlsx([("10 MAA10 CP001", "PT", "HP STEAM PRESS"), ("10MAA10CT001", "TT", "HP STEAM TEMP")]), "a.xlsx")
    assert got["found"][0]["row"] == 3
    assert set(got["tags"]) == {"10MAA10CP001", "10MAA10CT001"}                  # 공백 없는 대문자로 맞댄다
    assert got["tags"]["10MAA10CP001"]["desc"] == "HP STEAM PRESS" and got["tags"]["10MAA10CP001"]["type"] == "PT"
    with pytest.raises(ValueError):
        b = io.BytesIO(); wb = openpyxl.Workbook(); wb.active.append(["A", "B"]); wb.save(b)
        instruments.parse(b.getvalue(), "x.xlsx")


def test_reupload_updates_changed_descriptions_and_marks_them(client):
    r = _up(client, _xlsx([("10MAA10CP001", "PT", "HP STEAM PRESS"), ("10MAA10CT001", "TT", "HP STEAM TEMP"),
                           ("10MAA10CL001", "LT", "DRUM LEVEL")]))
    assert r.status_code == 200 and r.json()["n"] == 3
    pub = client.get("/logic/api/drawings/instruments", params={"project": "P1"}).json()
    assert pub["tags"]["10MAA10CT001"] == ["10MAA10CT001", "HP STEAM TEMP", "TT"]
    d = client.post("/logic/api/drawings", json={"name": "S", "author": "홍길동", "project": "P1"}).json()
    d["left"] = {"1": {"fm": "", "kks": "10MAA10CP001", "desc": "HP STEAM PRESS"},          # 리스트에서 불러온 설명
                 "2": {"fm": "", "kks": "10MAA10CT001", "desc": "MY OWN TEXT"},             # 사람이 고친 설명
                 "3": {"fm": "", "kks": "10MAA10CL001", "desc": "DRUM LEVEL"}}
    client.put(f"/logic/api/drawings/{d['id']}", json={"author": "홍길동", "doc": d})
    other = client.post("/logic/api/drawings", json={"name": "O", "author": "홍길동", "project": "P2"}).json()
    other["left"] = {"1": {"fm": "", "kks": "10MAA10CP001", "desc": "HP STEAM PRESS"}}
    client.put(f"/logic/api/drawings/{other['id']}", json={"author": "홍길동", "doc": other})
    # v2 — CP001 설명 바뀜 · CT001 설명 바뀜 · CL001 없어짐
    r = _up(client, _xlsx([("10MAA10CP001", "PT", "HP STEAM PRESSURE"), ("10MAA10CT001", "TT", "HP STEAM TEMPERATURE"),
                           ("10MAA10CF001", "FT", "FW FLOW")]), name="list_v2.xlsx").json()
    assert {c["tag"] for c in r["changed"]} == {"10MAA10CP001", "10MAA10CT001"}
    assert [x["tag"] for x in r["removed"]] == ["10MAA10CL001"] and r["added"] == 1
    assert r["rows"] == 1 and r["kept"] == 1 and r["drawings"] == 1
    d2 = client.get(f"/logic/api/drawings/{d['id']}").json()
    assert d2["left"]["1"]["desc"] == "HP STEAM PRESSURE" and d2["left"]["1"]["inst"]["old"] == "HP STEAM PRESS"
    assert d2["left"]["2"]["desc"] == "MY OWN TEXT" and "inst" not in d2["left"]["2"]          # 사람이 고친 설명은 그대로
    assert client.get(f"/logic/api/drawings/{other['id']}").json()["left"]["1"]["desc"] == "HP STEAM PRESS"   # 다른 프로젝트는 안 건드림
    pub = client.get("/logic/api/drawings/instruments", params={"project": "P1"}).json()
    assert "10MAA10CL001" not in pub["tags"] and pub["version"] == 2                          # 화면은 이것으로 '식별되지 않음' 경고
    # 그림을 저장해도 표시가 남는다 (사람이 '표시 지우기' 하기 전까지)
    client.put(f"/logic/api/drawings/{d['id']}", json={"author": "홍길동", "doc": d2})
    assert client.get(f"/logic/api/drawings/{d['id']}").json()["left"]["1"]["inst"]["old"] == "HP STEAM PRESS"


def test_upload_rejects_without_author_or_header(client):
    r = client.post("/logic/api/drawings/instruments", files={"file": ("a.xlsx", _xlsx([("T1", "", "D")]))}, data={"project": "P"})
    assert r.status_code == 400
    r = _up(client, b"not an excel", name="bad.xlsx")
    assert r.status_code == 400 and "엑셀" in r.json()["detail"]


def test_screen_code_uses_the_list():
    from pathlib import Path
    js = (Path(__file__).resolve().parent.parent / "app" / "static" / "logic_draw.js").read_text(encoding="utf-8")
    assert "function instAC" in js and "instFill" in js and "inst-miss" in js and "식별되지 않습니다" in js
