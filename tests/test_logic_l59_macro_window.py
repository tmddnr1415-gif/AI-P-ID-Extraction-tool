"""L59 — LOGIC 작도 화면의 매크로 새 창 · 범례 기호 전부.

* `draw_sim.simulate(..., inner=["<그림>:<상자>"])` 는 부모 장에 펼쳐 같이 돈 Typical 안의 값(틀마다 · Typical 선 이름)과
  Typical 행 ↔ 부모 행 연결, Typical 그림 id 를 `macro_inner` 로 낸다 — 새 창은 따로 돌리지 않고 그 값을 그린다 (검토 화면 L44 와 같다).
* 매크로 블록의 `macro.did` 로 새 창이 열 Typical 그림을 안다.
* 삼성 범례의 기호 보기는 전부 시뮬레이터에서 뜻을 갖는다 (L57 시험이 보기마다 돈다) — 여기서는 수가 범례를 덮는지 본다.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.logic import draw as D

N = D.N_DEFAULT


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    from app.logic import api
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def test_macro_inner_values_follow_the_parent_sheet(client):
    from tests.test_logic_l56_sets import _three_sheet_set
    sid, main, typ, rx = _three_sheet_set(client)
    mb = main["blocks"][0]
    r = client.post(f"/logic/api/drawings/{main['id']}/simulate", json={"forces": {main["id"]: {"row:5": 1}}}).json()
    assert r["sheet"]["blocks"][mb["id"]]["macro"]["did"] == typ["id"]          # 새 창이 열 Typical 그림
    assert r["macro_inner"] == {}                                                # 묻지 않으면 안 낸다
    key = f"{main['id']}:{mb['id']}"
    r = client.post(f"/logic/api/drawings/{main['id']}/simulate", json={"forces": {main["id"]: {"row:5": 1}}, "inner": [key]}).json()
    mi = r["macro_inner"][key]
    assert mi["typ_did"] == typ["id"] and mi["parent_did"] == main["id"]
    # Typical 1행(AOPEN)은 부모 5행(PB OPEN)과 이어진다 · 2행(ACLOSE)은 6행
    links = {x["row"]: x for x in mi["links"] if x["side"] == "L"}
    assert [q["n"] for q in links[1]["rows"]] == [5] and [q["n"] for q in links[2]["rows"]] == [6]
    # 값 — Typical 시트의 선 이름으로.  5행만 1 → AOPEN 선 1 · CMD 선 0
    tsheet = client.get(f"/logic/api/drawings/{typ['id']}/sheet").json()
    net_of_row = {x["n"]: x["net"] for x in tsheet["rows"]}
    last = mi["frames"][-1]["values"]
    assert last.get(net_of_row[1]) == 1 and last.get(net_of_row[N + 1]) in (None, 0)
    r = client.post(f"/logic/api/drawings/{main['id']}/simulate", json={"forces": {main["id"]: {"row:5": 1, "row:6": 1}}, "inner": [key]}).json()
    last = r["macro_inner"][key]["frames"][-1]["values"]
    assert last.get(net_of_row[N + 1]) == 1                                      # 둘 다 1 → Typical AND → CMD 1 (부모 장과 같은 시간)
    # 새 창이 Typical 안의 선을 부모 이름으로 준다 — 펼친 이름 `<상자>/<선>`
    inner_net = net_of_row[N + 1]
    pk = mi["alias"].get(str(inner_net)) or f"{mb['id']}/{inner_net}"
    r = client.post(f"/logic/api/drawings/{main['id']}/simulate", json={"forces": {main["id"]: {"row:5": 1, "net:" + pk: 0}}, "inner": [key]}).json()
    assert "error" not in r


def test_box_presets_cover_the_samsung_legend():
    texts = {p["text"] for p in D.BOX_PRESETS}
    # SIGNAL PROCESSING SYMBOLS (19VA · 알다프라와 같은 표준) 의 기호
    for t in ["1", "0", "ON", "FL", "I", "S", "HH/", "HHH/", "H/", "/L", "/LL", "/LLL", "MED", "Σ", "AVG", "△", "|△|", "ABS", "K", "-K", "±",
              "∫", "D/DT", "×", "÷", "√", "Xⁿ", "F(X)", "F(T)", ">", "<", "HL", "LL", "V>", "LAG", "T", "PID", "A", "A/T", "DEV", "EQUAL",
              "BIT_CNT", "COUNTER", "I/P", "STATEMENT OF SPECIAL REQUIREMENTS"]:
        assert t in texts, t
    assert next(p for p in D.BOX_PRESETS if p["text"].startswith("STATEMENT"))["kind"] == "TEXT"
    # 나머지 범례 기호는 기호 사전에 있다 — AND · OR · NOT · ON/OFF DELAY(GT/DT) · 펄스(PD) · 메모리 · 자격 OR(VOTE) · 누름단추 · ALM · SOE · 연결 기호 · 표시등
    for k in ["AND", "OR", "NOT", "NAND", "NOR", "GT", "DT", "PD", "VOTE", "MEMORY", "PB", "ANN", "SOE", "CONN", "LAMP", "MACRO", "TEXT"]:
        assert k in D.SYMBOLS, k
