"""L34 — 누름단추를 활성으로 누르면 그 신호가 동작한다 (사용자 지시).

* 누른 신호는 화면과 같은 묶음 시뮬레이션이 범례대로 퍼뜨린다 — 게이트를 건너뛰지 않는다 (L18)
* 못 가면 어디서 왜 멈췄는지 · 누른 채로 그 동작(단추 이름의 낱말이 든 출력)이 나가려면 무엇을 더 켤지
* 매크로를 펼칠 때 Typical 의 입력 행과 출력 행이 한 선이면 입력 단자 → 출력 단자로 그대로 넘긴다
"""
from pathlib import Path

from app.logic import sim

ROOT = Path(__file__).resolve().parents[1]
P = lambda b, n, d, role="": {"block": b, "net": n, "dir": d, "role": role, "cell": 0}


def _sheet(page, no, rows, blocks=None, ports=None):
    nets = {r["net"]: {"segs": []} for r in rows if r.get("net")}
    for p in ports or []:
        nets.setdefault(p["net"], {"segs": []})
    return {"page": page, "sheet_no": no, "rows": rows, "blocks": blocks or {}, "ports": ports or [], "nets": nets}


PB = lambda label: {"func": "PB", "logic": "source", "group": "", "param": {}, "label": label}
G = lambda f, lg: {"func": f, "logic": lg, "group": "", "param": {}, "label": f}


def _start_stop():
    # PB START → AND(허가 7행) → 출력 71 'START CMD' · PB STOP → OR → 출력 72 'STOP CMD'
    rows = [{"n": 7, "side": "L", "net": "perm", "desc": "PERMISSIVE"},
            {"n": 71, "side": "R", "net": "st", "desc": "START CMD"},
            {"n": 72, "side": "R", "net": "sp", "desc": "STOP CMD"}]
    blocks = {"PB1": PB("PB START"), "PB2": PB("PB STOP"), "A": G("AND", "and"), "O": G("OR", "or")}
    ports = [P("PB1", "pb", "out"), P("A", "pb", "in"), P("A", "perm", "in"), P("A", "st", "out"),
             P("PB2", "pb2", "out"), P("O", "pb2", "in"), P("O", "x", "in"), P("O", "sp", "out")]
    return _sheet(1, "G1", rows, blocks, ports)


def test_pressing_a_button_through_an_or_operates_its_output():
    s = _start_stop()
    r = sim.press([s], 1, "PB2")
    assert r["ok"] and [t["row"] for t in r["reached"]] == [72]


def test_a_gate_still_decides_and_the_plan_keeps_the_button_pressed():
    s = _start_stop()
    r = sim.press([s], 1, "PB1")
    assert not r["ok"]                                        # 허가가 0 이라 AND 가 막는다 — 건너뛰지 않는다
    assert r["stop"]["block"] == "A" and r["stop"]["logic"] == "and"
    assert [x["value"] for x in r["stop"]["inputs"]] == [1, 0]
    assert r["plan"]["target"]["row"] == 71 and r["plan"]["add"] == {"row:7": 1}
    # 권한 조합을 실제로 주면 출력이 선다 (게이트가 판정)
    b = sim.simulate_bundle([s], {1: {"block:PB1": 1, "row:7": 1}}, None, 1)
    assert b["focus"]["frames"][-1]["values"]["st"] == 1
    # 사람이 허가를 0 으로 준 채면 권하지 않는다
    r = sim.press([s], 1, "PB1", forces={1: {"row:7": 0}})
    assert not r["ok"] and r["plan"] is None


def test_plan_prefers_the_output_named_like_the_button():
    # START 단추 하나가 OR 로 START CMD 와 (다른 조건과 AND 로) STOP CMD 에 닿아도 START 쪽만 권한다
    rows = [{"n": 7, "side": "L", "net": "c", "desc": "C"}, {"n": 8, "side": "L", "net": "d", "desc": "D"},
            {"n": 70, "side": "R", "net": "stop", "desc": "STOP COMMAND"},
            {"n": 71, "side": "R", "net": "start", "desc": "START COMMAND"}]
    blocks = {"PB": PB("START"), "A1": G("AND", "and"), "A2": G("AND", "and")}
    ports = [P("PB", "p", "out"), P("A1", "p", "in"), P("A1", "c", "in"), P("A1", "stop", "out"),
             P("A2", "p", "in"), P("A2", "d", "in"), P("A2", "start", "out")]
    r = sim.press([_sheet(1, "G1", rows, blocks, ports)], 1, "PB")
    assert r["plan"]["target"]["row"] == 71 and r["plan"]["add"] == {"row:8": 1}


def test_button_into_a_macro_and_typical_pass_through_line():
    # Typical: 입력 10(START REQ) → AND(입력 11) → 출력 70 · 입력 12(RUNNING) 와 출력 71(RUNNING) 이 한 선
    typ = _sheet(2, "T1", [{"n": 10, "side": "L", "net": "t1"}, {"n": 11, "side": "L", "net": "t2"},
                           {"n": 12, "side": "L", "net": "run"},
                           {"n": 70, "side": "R", "net": "to", "desc": "START COMMAND"},
                           {"n": 71, "side": "R", "net": "run", "desc": "RUNNING"}],
                 {"G": G("AND", "and")}, [P("G", "t1", "in"), P("G", "t2", "in"), P("G", "to", "out")])
    mac = {"func": "MACRO", "logic": "macro", "group": "", "param": {}, "label": "",
           "macro": {"sheet": "T1", "page": 2, "title": "MOTOR BLOCK",
                     "inputs": [{"net": "p1", "pin": "M_STRT", "row": 10}, {"net": "p2", "pin": "EN", "row": 11},
                                {"net": "p3", "pin": "FB_RUN", "row": 12}],
                     "outputs": [{"net": "po", "pin": "C_START", "row": 70}, {"net": "pr", "pin": "RUNNG", "row": 71}]}}
    par = _sheet(1, "A1", [{"n": 2, "side": "L", "net": "p2", "desc": "ENABLE"},
                           {"n": 3, "side": "L", "net": "p3", "desc": "RUNNING FB"},
                           {"n": 80, "side": "R", "net": "po", "desc": "START CMD"},
                           {"n": 81, "side": "R", "net": "pr", "desc": "RUNNING"}],
                 {"M": mac, "PB": PB("START")},
                 [P("PB", "p1", "out"), P("M", "p1", "in"), P("M", "p2", "in"), P("M", "p3", "in"),
                  P("M", "po", "out"), P("M", "pr", "out")])
    # 통과 선 — 입력 행 3 이 1 이면 매크로 출력 RUNNING 도 1 (예전엔 입력 단자 선이 끊겼다)
    b = sim.simulate_bundle([par, typ], {1: {"row:3": 1}}, None, 1)
    assert b["focus"]["frames"][-1]["values"]["pr"] == 1
    r = sim.press([par, typ], 1, "PB")
    assert not r["ok"] and r["stop"]["macro"]["block"] == "M" and r["stop"]["logic"] == "and"
    assert r["plan"]["target"]["net"] == "po" and r["plan"]["add"] == {"row:2": 1}


def test_press_api_and_screen_wiring():
    api = (ROOT / "app/logic/api.py").read_text(encoding="utf-8")
    assert '"/logic/api/jobs/{job}/sheet/{page}/press"' in api
    js = (ROOT / "app/static/logic.js").read_text(encoding="utf-8")
    # 누름단추는 따라가기 모드에서도 1/0 메뉴 (입력 행 동그라미와 같다)
    i, j = js.index('else if (!hasIn && b.logic === "source") forceMenu'), js.index('else if (L.mode === "trace") traceFrom("block:"')
    assert i < j
    assert "pressReport(" in js and "/press`" in js and "renderPressCard" in js
