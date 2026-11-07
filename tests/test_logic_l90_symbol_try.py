"""L90 — 기호 · 매크로 창에서 두 번 누름: 기호 하나 해 보기 (POST /logic/api/drawings/symbol_sim).
그 기호만 든 그림을 작성 시뮬레이션(draw_sim)이 그대로 돌린다 — 따로 흉내 내지 않는다.  화면은 spike/ui_human_draw_l86.py 의 L90 단계."""
from app.logic import draw_sim as S


def last(r):
    return r["frames"][-1]["out"]


def test_gates():
    assert last(S.symbol_sim("AND", k=3, inputs=[1, 1, 0])) == [0]
    assert last(S.symbol_sim("AND", k=2, inputs=[1, 1])) == [1]
    assert last(S.symbol_sim("OR", inputs=[0, 1])) == [1]
    assert last(S.symbol_sim("NAND", inputs=[1, 1])) == [0]
    assert last(S.symbol_sim("NOR", inputs=[0, 0])) == [1]
    assert last(S.symbol_sim("NOT", inputs=[1])) == [0]
    assert last(S.symbol_sim("VOTE", k=3, inputs=[1, 1, 0], param={"a": 2})) == [1]
    assert last(S.symbol_sim("VOTE", k=3, inputs=[1, 0, 0], param={"a": 2})) == [0]


def test_timers_run_in_time():
    r = S.symbol_sim("GT", param={"t": 3}, inputs=[1])
    assert [(f["t"], f["out"]) for f in r["frames"]] == [(0.0, [0]), (3.0, [1])]
    on = S.symbol_sim("DT", param={"t": 2}, inputs=[1])
    off = S.symbol_sim("DT", param={"t": 2}, inputs=[0], state=on["state"])          # 1 → 0 : 2초 뒤 0 (앞 상태를 이어 간다)
    assert last(on) == [1] and [(f["t"], f["out"]) for f in off["frames"]] == [(0.0, [1]), (2.0, [0])]
    p = S.symbol_sim("PD", param={"t": 2}, inputs=[1])
    assert [f["out"][0] for f in p["frames"]] == [1, 0]


def test_memory_latches():
    m1 = S.symbol_sim("MEMORY", inputs=[1, 0])
    m2 = S.symbol_sim("MEMORY", inputs=[0, 0], state=m1["state"])
    m3 = S.symbol_sim("MEMORY", inputs=[0, 1], state=m2["state"])
    assert last(m1)[0] == 1 and last(m2)[0] == 1 and last(m3)[0] == 0


def test_sources_constants_and_text_boxes():
    assert last(S.symbol_sim("PB", press=1)) == [1]
    assert last(S.symbol_sim("BOX", text="1", noin=True)) == [1]
    assert last(S.symbol_sim("BOX", text="0", noin=True)) == [0]
    r = S.symbol_sim("BOX", text="DI", inputs=[1])                                   # 글자 상자의 뜻은 글자 — DI = 켜짐 지연
    assert r["block"]["logic"] == "delay_on" and r["frames"][-1]["out"] == [1] and r["frames"][-1]["t"] > 0
    assert S.symbol_sim("BOX", text="∑", inputs=[1])["aop"] == "sum"                # 아날로그는 신호 처리 시뮬레이션으로 보낸다


def test_endpoint(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PID_DRAW_SEED", "0")
    from app import main
    c = TestClient(main.app)
    r = c.post("/logic/api/drawings/symbol_sim", json={"kind": "AND", "k": 2, "inputs": [1, 1]}).json()
    assert r["frames"][-1]["out"] == [1] and r["inputs"] == ["IN1", "IN2"] and r["block"]["func"] == "AND"
    assert c.post("/logic/api/drawings/symbol_sim", json={"kind": "XX"}).status_code == 400
    assert c.post("/logic/api/drawings/symbol_sim", json={"kind": "MACRO"}).json().get("error")
