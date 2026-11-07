"""L49 — 게이트 · 매크로를 누르면: 이 출력이 켜지려면 앞쪽 어떤 신호가 켜져야 하는지 (출력마다 조건 나무 · 판정 0줄).

로직을 모르는 사람이 '이 명령이 나가려면 무엇이 있어야 하나' 를 보고 로직이 맞게 짜였는지 검토하는 자리다.
나무는 순차 동작(L32)과 같은 길(_plan_net)이라 같은 조건을 말한다."""
from __future__ import annotations

from pathlib import Path

from app.logic import sequence
from tests.test_logic_l32_sequence import _B, _P, _bundle, _client, _job, _own_data, _sheet  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "app/static/logic.js").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/logic.html").read_text(encoding="utf-8")


def _need_texts(plan):
    return [x["text"] for x in plan["signals"]["need"]]


def test_gate_click_lists_upstream_signals_per_output_net():
    sh = _bundle()
    # 마지막 AND(A2) — 출력 cmd 가 1 이 되려면: 허가 1 · TRIP 0(없어야) · (AUTO REQ 또는 누름단추) 하나
    r = sequence.needs(sh, 1, "block:A2")
    assert r["ok"] and r["kind"] == "gate" and r["block"] == "A2" and r["logic"] == "and"
    assert [o["net"] for o in r["outputs"]] == ["cmd"]
    o = r["outputs"][0]
    assert "출력 90행" in o["desc"] and "PUMP A START CMD" in o["desc"]
    p = o["plan"]
    assert p["ok"] and p["net"] == "cmd"
    sig = p["signals"]
    assert "PUMP A START PERMISSIVE" in _need_texts(p)
    assert any(z["text"] == "PUMP A TRIP" and z["want"] == 0 for z in sig["zero"])
    assert sig["forks"] == 1                                  # OR 갈래 하나 — 화면이 '다음 중 하나' 로 그린다
    # 첫 AND(A1) — 허가 1 · TRIP 0 뿐 · 갈래 없음
    r1 = sequence.needs(sh, 1, "block:A1")
    p1 = r1["outputs"][0]["plan"]
    assert _need_texts(p1) == ["PUMP A START PERMISSIVE"] and p1["signals"]["forks"] == 0
    assert "AND" in r1["outputs"][0]["desc"]                  # 이 선이 어디로 가는지 (다음 블록)


def test_needs_is_the_same_tree_as_the_sequence_plan():
    sh = _bundle()
    a = sequence.plan(sh, 1, 90)
    b = sequence.needs(sh, 1, "net:cmd")["outputs"][0]["plan"]
    strip = lambda p: {k: v for k, v in p.items() if k not in ("row", "desc")}
    assert strip(a) == strip(b)
    assert sequence.needs(sh, 1, "block:A2")["outputs"][0]["plan"]["nodes"] == a["nodes"]


def test_macro_lists_signals_per_output_pin():
    # Typical T001: 입력 1(AUTO) AND 입력 2(PERM) → 출력 90 OPEN CMD · 입력 3 → 출력 91 CLOSE CMD
    typ = _sheet(9, "T001", [
        {"n": 1, "side": "L", "net": "a", "desc": "AUTO", "fm": ""}, {"n": 2, "side": "L", "net": "p", "desc": "PERMIT", "fm": ""},
        {"n": 3, "side": "L", "net": "c", "desc": "CLOSE REQ", "fm": ""},
        {"n": 90, "side": "R", "net": "o", "desc": "OPEN CMD", "to": ""}, {"n": 91, "side": "R", "net": "c", "desc": "CLOSE CMD", "to": ""},
    ], {"A": _B("and")}, [_P("A", "a", "in"), _P("A", "p", "in"), _P("A", "o", "out")])
    host = _sheet(1, "G001", [
        {"n": 1, "side": "L", "net": "n1", "desc": "VALVE AUTO SELECT", "fm": ""},
        {"n": 2, "side": "L", "net": "n2", "desc": "VALVE OPEN PERMISSIVE", "fm": ""},
        {"n": 3, "side": "L", "net": "n3", "desc": "VALVE CLOSE REQ", "fm": ""},
        {"n": 90, "side": "R", "net": "cmdo", "desc": "VALVE OPEN CMD", "to": ""},
        {"n": 91, "side": "R", "net": "cmdc", "desc": "VALVE CLOSE CMD", "to": ""},
    ], {"M": _B("source", "MOV BLOCK", "MACRO", macro={"page": 9, "sheet": "T001", "title": "MOV BLOCK",
            "inputs": [{"pin": "AUTO", "row": 1, "net": "n1"}, {"pin": "PERM", "row": 2, "net": "n2"}, {"pin": "CLS", "row": 3, "net": "n3"}],
            "outputs": [{"pin": "CMDO", "row": 90, "net": "cmdo", "desc": "OPEN COMMAND"}, {"pin": "CMDC", "row": 91, "net": "cmdc", "desc": "CLOSE COMMAND"},
                        {"pin": "FLT", "row": None, "net": None, "desc": "FAULT"}]})},
        [_P("M", "n1", "in"), _P("M", "n2", "in"), _P("M", "n3", "in"), _P("M", "cmdo", "out"), _P("M", "cmdc", "out")])
    r = sequence.needs([host, typ], 1, "block:M")
    assert r["ok"] and r["kind"] == "macro" and r["label"] == "MOV BLOCK"
    pins = {o["pin"]: o for o in r["outputs"]}
    assert set(pins) == {"CMDO", "CMDC", "FLT"}
    assert sorted(_need_texts(pins["CMDO"]["plan"])) == ["VALVE AUTO SELECT", "VALVE OPEN PERMISSIVE"]
    assert _need_texts(pins["CMDC"]["plan"]) == ["VALVE CLOSE REQ"]
    assert pins["FLT"]["plan"]["ok"] is False and "읽지 못" in pins["FLT"]["plan"]["why"]
    # 매크로 안쪽 게이트가 나무에 '매크로 … 의 조건' 으로 선다
    nodes = pins["CMDO"]["plan"]["nodes"].values()
    assert any((n.get("gate") or {}).get("func") == "MACRO" for n in nodes)


def test_needs_says_why_when_nothing_can_be_read():
    sh = _bundle()
    r = sequence.needs(sh, 1, "block:PB")                               # 누름단추 — 그 단추를 누르는 것이 곧 조건
    assert r["ok"] and [x["text"] for x in r["outputs"][0]["plan"]["signals"]["need"]] == ["누름단추 START"]
    assert sequence.needs(sh, 1, "block:ZZ")["ok"] is False
    assert sequence.needs(sh, 1, "row:90")["ok"] is False
    assert sequence.needs(sh, 77, "block:A2")["ok"] is False
    r = sequence.needs(sh, 1, "net:pb")
    assert r["ok"] and r["kind"] == "net" and [x["key"] for x in r["outputs"][0]["plan"]["signals"]["need"]] == ["block:PB"]


def test_needs_api_and_screen_wiring():
    job = _job(_bundle())
    c = _client()
    r = c.post(f"/logic/api/jobs/{job}/needs", json={"page": 1, "target": "block:A2"}).json()
    assert r["ok"] and r["outputs"][0]["plan"]["signals"]["need"][0]["text"] == "PUMP A START PERMISSIVE"
    assert c.post(f"/logic/api/jobs/{job}/needs", json={"page": 1, "target": "row:90"}).status_code == 400
    assert c.post(f"/logic/api/jobs/{job}/needs", json={"target": "block:A2"}).status_code == 400
    # 화면: 입력이 있는 게이트를 누르면 메뉴(어느 모드든) · 매크로 메뉴 · 근거 패널 단추 · 끌어 옮기는 창 · 항목 누르면 그 자리 ·
    # 주황 점등 · 조건 채워 켜기는 출력을 직접 켜지 않고 activateOutput(목표) 로
    for k in ("function gateOutMenu", "else gateOutMenu(bid, e);", 'data-m="needs"', "button[data-needs]", "/logic/api/jobs/${L.job}/needs",
              "function ndTreeHtml", "다음 중 <b>하나</b>", "flashNeed(ks)", 'await activateOutput("net:" + o.net)', "bindNeeds();"):
        assert k in JS, k
    assert 'id="needs"' in HTML and 'id="needs-h"' in HTML
    assert "prompt(" not in JS.split("function needsOpen")[1].split("function bindSeq")[0]
