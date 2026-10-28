"""L64a — 새 LOGIC 은 학습한 양식(아래 타이틀블록)으로 · 선은 언제나 가로·세로 (사선 금지) · 게이트 글자는 상자 안에."""
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


def _diag(wires, tol=0.01):
    n = 0
    for w in wires:
        for a, b in zip(w["pts"], w["pts"][1:]):
            if abs(a[0] - b[0]) > tol and abs(a[1] - b[1]) > tol:
                n += 1
    return n


def test_new_drawing_takes_the_learned_form_and_title_block(client):
    r = client.post("/logic/api/drawings", json={"name": "N", "author": "홍길동", "form": draw.DEFAULT_FORM,
                                                 "project_name": "AL DHAFRA", "doc_no": "1A5J-00GEN00-J09-0002", "rev": "2",
                                                 "sheet_no": "FG_G-301", "title": "FUEL GAS TEST"})
    d = r.json()
    assert d["form"] == "a5j" and d["project_name"] == "AL DHAFRA" and d["sheet_no"] == "FG_G-301"
    pdf = client.get(f"/logic/api/drawings/{d['id']}/export.pdf").content
    import pymupdf
    page = pymupdf.open(stream=pdf, filetype="pdf")[0]
    text = page.get_text()
    assert "AL DHAFRA" in text and "FG_G-301" in text and "FUEL GAS TEST" in text
    # 타이틀블록은 종이 아래쪽에
    hits = page.search_for("FG_G-301")
    assert hits and min(h.y0 for h in hits) > page.rect.height * 0.75
    # 묶음의 새 장은 같은 양식을 물려받는다
    sid = "abc123def456"
    d = client.put(f"/logic/api/drawings/{d['id']}", json={"author": "홍길동", "doc": d, "set": sid, "set_name": "S", "order": 1}).json()
    s2 = client.post(f"/logic/api/drawings/sets/{sid}/sheet", json={"author": "홍길동", "name": "two"}).json()
    assert s2["form"] == "a5j" and s2["project_name"] == "AL DHAFRA"


def test_wires_are_always_horizontal_or_vertical():
    N = draw.N_DEFAULT
    y1, y2 = draw.ry(1, N), draw.ry(2, N)
    blk = {"id": "a", "kind": "AND", "x": 500, "y": y1 - 2, "w": 16, "h": 9, "text": "AND", "param": {}}
    wires = [{"id": "", "pts": [[320, y1], [500.0, y1 + 0.8]]},                       # 거의 곧은 선 (1pt 비킴)
             {"id": "", "pts": [[516, y1 + 2.5], [600, y2 + 1.2], [870, y2]]},       # 사선 토막
             {"id": "", "pts": [[600.6, y1 + 30], [601.0, y2 + 60]]}]                # 거의 세로
    out = draw.orthogonal_wires(wires, blocks=[blk])
    assert _diag(out) == 0
    assert out[0]["pts"][0] == [320, y1]                                              # 행 자리는 그대로
    c = draw.clean({**draw.new_doc("x", "a"), "blocks": [blk], "wires": wires})
    assert _diag(c["wires"]) == 0


def test_close_parallel_inputs_are_not_merged():
    """3pt 떨어져 나란한 두 입력이 한 선으로 합쳐지면 안 된다 (Σ 두 입력)."""
    N = draw.N_DEFAULT
    y = draw.ry(2, N)
    wires = [{"id": "", "pts": [[320, draw.ry(1, N)], [360, draw.ry(1, N)], [360, y - 1.5], [400, y - 1.5]]},
             {"id": "", "pts": [[320, y], [360, y], [360, y + 1.5], [400, y + 1.5]]}]
    blk = {"id": "b", "kind": "BOX", "x": 400, "y": y - 4.5, "w": 16, "h": 9, "text": "Σ", "param": {}}
    out = draw.orthogonal_wires(wires, blocks=[blk])
    assert out[0]["pts"][-1][1] != out[1]["pts"][-1][1]


def test_symbol_strokes_keep_their_slant():
    """◇ 같은 기호 획은 신호선이 아니다 — 그대로."""
    w = [{"id": "", "pts": [[600, 300], [606, 304]]}]
    assert draw.orthogonal_wires(w, blocks=[])[0]["pts"] == [[600, 300], [606, 304]]


def test_gate_text_fits_its_box():
    fs = draw.fit_fs("AND", 16 - 2.2, 7)
    assert fs * 0.6 * 3 <= 16 - 2.2 + 0.5 and fs >= 1.6


def test_link_menu_and_linked_window_code():
    """L64b — FROM/TO 값을 누르면 이동 / 새 창 · 새 창은 연 창과 같은 입력으로 돈다 (화면 코드)."""
    from pathlib import Path
    js = (Path(__file__).resolve().parent.parent / "app" / "static" / "logic_draw.js").read_text(encoding="utf-8")
    assert "function linkMenu" in js and "openPeerWin" in js and "새 창으로" in js
    assert '"dsheet-sim"' in js and '"dsheet-set"' in js and '"dsheet-ask"' in js
    body = js.split("async function runSim")[1].split("\nfunction ")[0]
    assert "sendPeers" in body and "inState" in body                  # 연 창이 쓴 입력(직전 상태)을 그대로 내려보낸다
    assert "confirm(" not in js and "prompt(" not in js and "alert(" not in js   # 대시보드 iframe 은 막는다 (L25c)
