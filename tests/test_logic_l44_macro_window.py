"""L44 — 매크로 새 창은 Typical 을 따로 돌리지 않고, 부모 시트의 실제 행과 이어진 값을 그린다.

엔지니어는 Typical 을 참조해 실제 시트에서 입력 행 번호를 마음대로 배치한다 (예: 부모 14행 OP REQ → 단자 A_OPN →
Typical 16행).  그래서 새 창에는 Typical 행마다 부모 시트의 실제 행을 붙이고, 값은 부모 장에 펼쳐 같이 돈 묶음 계산
그대로 보낸다."""
from __future__ import annotations

from pathlib import Path

from app.logic import sim
from tests.test_logic_review import _sheet

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "app/static/logic.js").read_text(encoding="utf-8")

P = lambda b, n, d: {"block": b, "net": n, "dir": d, "role": "", "cell": 0}


def _bundle():
    typ = _sheet(2, "T1", [{"n": 16, "side": "L", "net": "t1"}, {"n": 9, "side": "L", "net": "t2"},
                           {"n": 70, "side": "R", "net": "to", "desc": "OPEN COMMAND"}],
                 {"G": {"func": "AND", "logic": "and", "group": "", "param": {}}},
                 [P("G", "t1", "in"), P("G", "t2", "in"), P("G", "to", "out")])
    mac = {"func": "MACRO", "logic": "macro", "group": "", "param": {}, "label": "",
           "macro": {"sheet": "T1", "page": 2,
                     "inputs": [{"net": "p1", "pin": "A_OPN", "row": 16}, {"net": "p2", "pin": "A_SEL", "row": 9}],
                     "outputs": [{"net": "po", "pin": "C_OPN", "row": 70}]}}
    pb = {"func": "PUSH BUTTON", "logic": "source", "group": "", "param": {}, "label": "AUTO"}
    par = _sheet(1, "BL11_G131", [{"n": 14, "side": "L", "net": "p1", "desc": "XV OP REQ"},
                                  {"n": 73, "side": "R", "net": "po", "desc": "XV OP CMD"}],
                 {"M": mac, "PB": pb},
                 [P("M", "p1", "in"), P("M", "p2", "in"), P("M", "po", "out"), P("PB", "p2", "out")])
    return [par, typ]


def test_macro_inner_carries_parent_values_and_actual_rows():
    sheets = _bundle()
    for cache in (None, {}):
        for _ in range(2):                                 # 두 번째는 기억(펼친 장 · 장 계산)에서
            out = sim.simulate_bundle(sheets, {1: {"row:14": 1, "block:PB": 1}}, None, 1, cache=cache)
            inner = out["macro_inner"][1]["M"]
            last = inner["frames"][-1]["values"]
            assert last.get("t1") == 1 and last.get("t2") == 1 and last.get("to") == 1     # Typical 선 이름으로
            links = {(x["side"], x["row"]): x for x in inner["links"]}
            assert links[("L", 16)]["rows"] == [{"n": 14, "desc": "XV OP REQ"}]          # 부모 14행 → Typical 16행
            assert links[("L", 9)]["rows"] == [] and "AUTO" in links[("L", 9)]["src"]   # 부모의 누름단추가 몬다
            assert links[("R", 70)]["rows"][0]["n"] == 73
            assert inner["sheet_no"] == "BL11_G131"
            assert "_inner" not in out["macros"][1]["M"]                                  # 화면 몸통에는 싣지 않는다
            assert out["focus"]["frames"][-1]["values"]["po"] == 1                        # 판정은 그대로


def test_macro_window_does_not_simulate_the_typical_on_its_own():
    assert "if (macroLinked()) { askParentMacro(); return; }" in JS          # 새 창의 runSim 은 부모에게 묻는다
    assert "if (macroLinked()) { macroWindowForce(key, v); return; }" in JS  # 새 창의 입력은 부모 시트의 행으로
    assert '"macro-ask"' in JS and '"macro-set"' in JS
    assert "const inner = (L.macroInner || {})[key]" in JS                   # 부모가 펼친 값을 보낸다
    assert "loadTeach(id, !fromWin && !MACRO_FROM" in JS                     # 새 창에 가르치기 창을 덮지 않는다


def _latch_bundle():
    """L45 — Typical 안: (단자 16행 t1 · 단자 없는 x) → OR → s → 래치 S · 몰이 없는 r → 래치 R · Q → 70행."""
    typ = _sheet(2, "T1", [{"n": 16, "side": "L", "net": "t1"}, {"n": 70, "side": "R", "net": "q"}],
                 {"O": {"func": "OR", "logic": "or", "group": "", "param": {}},
                  "MM": {"func": "MEMORY", "logic": "memory", "group": "", "param": {}}},
                 [P("O", "t1", "in"), P("O", "x", "in"), P("O", "s", "out"),
                  {**P("MM", "s", "in"), "role": "set"}, {**P("MM", "r", "in"), "role": "reset"},
                  {**P("MM", "q", "out"), "role": "q"}])
    mac = {"func": "MACRO", "logic": "macro", "group": "", "param": {}, "label": "",
           "macro": {"sheet": "T1", "page": 2, "inputs": [{"net": "p1", "pin": "A", "row": 16}],
                     "outputs": [{"net": "po", "pin": "Q", "row": 70}]}}
    par = _sheet(1, "G1", [{"n": 14, "side": "L", "net": "p1"}, {"n": 73, "side": "R", "net": "po"}],
                 {"M": mac}, [P("M", "p1", "in"), P("M", "po", "out")])
    return [par, typ]


def test_macro_window_can_force_signals_inside_the_typical():
    sheets = _latch_bundle()
    out = sim.simulate_bundle(sheets, {}, None, 1, cache={})
    inner = out["macro_inner"][1]["M"]
    assert inner["alias"] == {"t1": "p1", "q": "po"}                # 단자 선은 부모 선 이름
    assert inner["frames"][-1]["values"].get("q") is None
    # 새 창에서 단자 없는 OR 입력 x 를 1 로 → 부모 장에 펼친 이름 net:M/x 로 준다 → 래치 SET → Q → 부모 73행
    out = sim.simulate_bundle(sheets, {1: {"net:M/x": 1}}, None, 1, cache={})
    last = out["macro_inner"][1]["M"]["frames"][-1]["values"]
    assert last.get("s") == 1 and last.get("q") == 1
    assert out["focus"]["frames"][-1]["values"]["po"] == 1
    # 래치 RESET 선(몰이 없음)을 1 로 → Q 0 (기본 메모리: SET 0 · RESET 1)
    out = sim.simulate_bundle(sheets, {1: {"net:M/r": 1}}, None, 1, cache={})
    assert out["macro_inner"][1]["M"]["frames"][-1]["values"].get("q") is None
    assert "function macroParentKey" in JS and "macroChildForces" in JS
