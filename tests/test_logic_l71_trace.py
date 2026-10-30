"""L71 — 연산자를 누르면 계산 과정: 들어오는 값(어느 입력 행 · 계기에서) → 범례 식 → 값을 넣은 식 → 출력.

사용자 지시: signal processing symbol 을 클릭하면 input 값 → 적용 수식 → output 을 단계별로 ·
수식은 실제 값을 대입한 형태 (예: (A + B) × K = (12.0 + 3.5) × 0.8 = 12.4) · 입력이 어느 계기/태그에서 오는지도.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.logic import aop_trace, aops, sim
from tests.test_logic_l30_aops import _job, _own_data, _sheet, client, ma  # noqa: F401  (client · _own_data 는 fixture)

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "app/static/logic.js").read_text(encoding="utf-8")


def _I(pin, v, coef=None, net=None):
    return {"net": net or pin or "x", "pin": pin, "coef": coef, "value": v}


def test_trace_writes_the_legend_formula_with_the_values_put_in():
    t = aop_trace.trace("sum", {}, [_I("IN1", 12.0), _I("IN2", 3.5, -1.0)], 8.5)
    assert (t["sym"], t["sub"], t["res"]) == ("M = IN1 − IN2", "12 − 3.5", "8.5")
    t = aop_trace.trace("mean", {}, [_I("", 10.0, net="a"), _I("", 20.0, net="b")], 15.0)
    assert t["sym"] == "M = (X1 + X2) / 2" and t["sub"] == "(10 + 20) / 2"
    t = aop_trace.trace("gain", {"k": 0.8}, [_I("", 15.5)], 12.4)
    assert t["sub"] == "0.8 × 15.5" and t["res"] == "12.4" and ["K", "0.8"] in t["params"]
    t = aop_trace.trace("hilim", {"h": 50}, [_I("", 70.0)], 50.0)
    assert t["sym"] == "M = MIN(X1, H)" and t["sub"] == "MIN(70, 50)"
    t = aop_trace.trace("max", {}, [_I("", 3.0, net="a"), _I("", 7.0, net="b")], 7.0)
    assert t["sub"] == "MAX(3, 7)"
    t = aop_trace.trace("sqrt", {}, [_I("", -4.0)], None, why="음수의 제곱근")
    assert t["sub"] == "√(−4)" and t["res"] == "?" and t["note"] == "음수의 제곱근"


def test_two_input_order_is_the_one_compute_used():
    """÷ 는 도면 글자 'IN1 / IN2' · △ 는 + − 부호 — aops._two 와 같은 순서로 적는다 (거꾸로 적지 않는다)."""
    ins = [_I("IN2", 20.0), _I("IN1", 60.0)]
    assert aop_trace.trace("div", {}, ins, 3.0, label="÷ IN1 / IN2")["sub"] == "60 ÷ 20"
    ins = [_I("-", 5.0, -1.0, net="k"), _I("+", 60.0, 1.0, net="a")]
    t = aop_trace.trace("diff", {}, ins, 55.0)
    assert t["sub"] == "60 − 5"
    assert aop_trace.trace("diff", {"order": ["k", "a"]}, ins, -55.0)["sub"] == "5 − 60", "사람이 정한 앞 · 뒤"


def test_formula_and_transfer_and_deviation_are_spelled_out():
    t = aop_trace.trace("formula", {}, [_I("A", 9.5)], 1.496, label="OUT = A * 0.16 - 0.024")
    assert t["sym"] == "M = A * 0.16 - 0.024" and t["sub"] == "9.5 * 0.16 - 0.024"
    ins = [_I("IN1", 10.0), _I("IN2", 20.0), _I("FLAG", None)]
    assert aop_trace.trace("transfer", {}, ins, 20.0, why="조건 0 → IN2")["sub"] == "C = 0 → IN2 = 20"
    t = aop_trace.trace("dev", {"d": 3}, [_I("", 60.0, net="a"), _I("", 20.0, net="b")], None, 1)
    assert t["sub"].startswith("|60 − 20| > 3") and t["res"] == "1"


def test_the_trace_value_is_never_its_own_calculation():
    """과정은 받은 출력을 적을 뿐 — 같은 입력이라도 출력이 없으면 '?' (판정 0줄)."""
    t = aop_trace.trace("sum", {}, [_I("IN1", 1.0), _I("IN2", 2.0)], None)
    assert t["res"] == "?"


def test_panel_api_adds_trace_and_where_each_input_comes_from(client):  # noqa: F811
    s = _sheet()
    job, d = _job(s)
    one = client.post(f"/logic/api/jobs/{job}/sheet/1/aop",
                      json={"block": "S1", "analog": {"row:10": ma(60)}}).json()
    assert one["trace"]["sub"] == "60 − 5" and one["trace"]["res"] == "55"
    src = one["sources"]
    assert src["a"]["kind"] == "row" and "FLOW A" in src["a"]["text"], "입력 행 · 설명 (계기)"
    assert src["k"]["kind"] == "op" and src["k"]["block"] == "A1", "상수 블록에서"
    # 동작 시뮬레이션 결과를 주면 다시 세지 않고 그 값으로 과정만 더한다
    s2 = _sheet()
    aops.identify([s2])
    r = sim.simulate(s2, {}, analog={"row:10": ma(30)})
    sd = r["analog"]["ops"]["S1"]
    two = client.post(f"/logic/api/jobs/{job}/sheet/1/aop", json={"block": "S1", "detail": sd}).json()
    assert two["out"] == pytest.approx(25.0) and two["trace"]["sub"] == "30 − 5"


def test_source_walks_through_operators_to_the_input_rows():
    s = _sheet()
    aops.identify([s])
    idx = sim._index(s)[:4]
    from app.logic import analog
    tp = analog._topo(s, idx)
    so = aop_trace.sources(s, "s", "H1", idx, tp["ops"], tp["io"])
    assert so["block"] == "S1" and any("FLOW A" in o for o in so["origins"])


def test_screen_draws_the_trace_steps_in_the_operator_panel():
    assert "function opTraceHtml(" in JS and "${opTraceHtml(d)}" in JS
    assert "detail: sd" in JS, "시뮬레이션 값은 그대로 서버에 넘겨 과정만 받는다"
    assert "flashNeed([ts.dataset.trsrc])" in JS, "입력을 누르면 그 행 · 블록을 도면에서 짚는다"
