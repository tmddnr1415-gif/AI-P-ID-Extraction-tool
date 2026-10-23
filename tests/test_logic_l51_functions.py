"""L51 — 로직 펑션(심볼)의 동작 원리를 범례 정의로 못박는다.
HRSG G003 'SYMBOL & LEGEND' · 19VA 'SIGNAL PROCESSING SYMBOLS (1/4~4/4)' 의 DEFINITION 을 진리표로 옮긴 것이다.
시뮬레이터를 고치는 회차는 이 시험이 지켜야 한다 (L18 상시 원칙과 같은 자리)."""
import itertools

from app.logic import sim, aops, analog


def _sheet(blocks, ports, rows=(), page=1):
    order = {n: [[0, 0, 1, 1, 0.0]] for n in {p["net"] for p in ports}}
    return {"page": page, "sheet_no": f"T{page:03d}", "title": "t", "pitch": 10.0, "blocks": blocks, "ports": ports,
            "rows": list(rows), "table": {}, "nets": {n: {"segs": [[0, 0, 1, 1]], "jumps": [], "dashed": False} for n in order},
            "order": order, "findings": [], "logic": [0, 0, 100, 100]}


def _blk(func, logic, label=None, **kw):
    d = {"kind": "RECT", "func": func, "logic": logic, "label": label or func, "read": label or func, "bbox": [0, 0, 10, 10],
         "cells": [[0, 0, 10, 10]], "param": {}, "group": "", "pointer": None, "roles": {}, "key": "|", "at": [5, 5]}
    d.update(kw)
    return d


def _port(block, net, d, role="", side=None):
    return {"block": block, "net": net, "dir": d, "at": [0, 0], "side": side or ("L" if d == "in" else "R"), "cell": 0, "role": role}


def _lrow(n, net, desc="in"):
    return {"n": n, "side": "L", "net": net, "desc": desc, "fm": "", "kks": ""}


def _rrow(n, net, desc="out"):
    return {"n": n, "side": "R", "net": net, "desc": desc, "fm": "", "kks": ""}


def _gate(logic, n_in):
    blocks = {"G": _blk(logic.upper(), logic)}
    ports = [_port("G", f"i{k}", "in") for k in range(n_in)] + [_port("G", "y", "out")]
    rows = [_lrow(k + 1, f"i{k}") for k in range(n_in)] + [_rrow(70, "y")]
    return _sheet(blocks, ports, rows)


def _out(s, forces, net="y", timers=None):
    r = sim.simulate(s, forces, None, 0.0, timers or {})
    return [fr["values"].get(net) for fr in r["frames"]], r


# ---------------------------------------------------------------- 범례 G003 — 논리 게이트
def test_and_or_nand_nor_not_truth_tables():
    for n in (2, 3):
        for bits in itertools.product((0, 1), repeat=n):
            f = {f"row:{k + 1}": v for k, v in enumerate(bits)}
            assert _out(_gate("and", n), f)[0][-1] == int(all(bits))        # OUTPUT TRUE ONLY IF ALL INPUTS ARE TRUE
            assert _out(_gate("or", n), f)[0][-1] == int(any(bits))         # OUTPUT TRUE ONLY IF ANY INPUT IS TRUE
            assert _out(_gate("nand", n), f)[0][-1] == int(not all(bits))   # OUTPUT TRUE ONLY IF ANY INPUT IS FALSE
            assert _out(_gate("nor", n), f)[0][-1] == int(not any(bits))    # OUTPUT TRUE IF ALL INPUTS ARE FALSE
    assert _out(_gate("not", 1), {"row:1": 1})[0][-1] == 0 and _out(_gate("not", 1), {"row:1": 0})[0][-1] == 1


def test_unconnected_input_counts_as_zero_l46():
    s = _gate("and", 2)
    s["ports"] = [p for p in s["ports"] if p["net"] != "i1"]      # 둘째 입력 칸이 연결 안 됨
    assert _out(s, {"row:1": 1})[0][-1] == 0                      # 빈 칸 = 0 → AND 는 0
    s2 = _gate("or", 2); s2["ports"] = [p for p in s2["ports"] if p["net"] != "i1"]
    assert _out(s2, {"row:1": 1})[0][-1] == 1


# ---------------------------------------------------------------- 타이머 GT · DT · PD
def _timer(logic, t=3, extra=()):
    blocks = {"T": _blk(logic.upper(), logic, param={"t": t})}
    ports = [_port("T", "i", "in"), _port("T", "y", "out")] + [_port("T", n, "in", side=sd) for n, sd in extra]
    rows = [_lrow(1, "i")] + [_lrow(2 + k, n) for k, (n, _) in enumerate(extra)] + [_rrow(70, "y")]
    return _sheet(blocks, ports, rows)


def test_on_delay_output_rises_after_t_and_stays_while_input_stays():
    vals, r = _out(_timer("delay_on", 3), {"row:1": 1})
    ts = [fr["t"] for fr in r["frames"]]
    assert vals[0] == 0 and vals[-1] == 1 and ts[-1] >= 3           # 0 → 1 after t
    # 입력이 0 이면 출력 0 (유지 안 됨)
    assert _out(_timer("delay_on", 3), {"row:1": 0})[0][-1] == 0


def test_on_delay_optional_reset_input_at_bottom_clears_output():
    # 범례 G003 GT: OUTPUT REMAINS 1 UNTIL INPUT CHANGES TO 0 OR OPTIONAL RESET [R] CHANGES TO 1 — R 은 아래 단자
    s = _timer("delay_on", 3, extra=[("r", "B")])
    assert _out(s, {"row:1": 1, "row:2": 0})[0][-1] == 1
    assert _out(s, {"row:1": 1, "row:2": 1})[0][-1] == 0


def test_time_value_input_at_top_is_not_a_logic_input():
    # 1A5J · 19VA — 위쪽 단자에 'WAITING TIME' 행이 닿는다: 시간 매개변수이지 입력이 아니다 (OR 하면 그 행 하나로 타이머가 돈다)
    s = _timer("delay_on", 3, extra=[("tv", "T")])
    assert _out(s, {"row:1": 0, "row:2": 1})[0][-1] == 0
    assert _out(s, {"row:1": 1, "row:2": 0})[0][-1] == 1


def test_off_delay_holds_for_t_after_input_drops():
    s = _timer("delay_off", 3)
    vals, r = _out(s, {"row:1": 1})
    assert vals[-1] == 1                                            # 입력 1 → 바로 1
    st = r["state"]
    r2 = sim.simulate(s, {"row:1": 0}, st, r["frames"][-1]["t"], {})
    v2 = [fr["values"].get("y") for fr in r2["frames"]]
    assert v2[0] == 1 and v2[-1] == 0                               # 입력이 0 → t 동안 1 유지 → 0


def test_pulse_output_lasts_t_after_rising_edge():
    vals, r = _out(_timer("pulse", 3), {"row:1": 1})
    assert vals[0] == 1 and vals[-1] == 0 and r["frames"][-1]["t"] >= 3


# ---------------------------------------------------------------- 메모리 (기본 · SET 우선 · RESET 우선)
def _mem(dom):
    blocks = {"M": _blk("MEMORY", "memory", "S/R", param={"dominant": dom}, roles={"set_cell": 0, "reset_cell": 1})}
    ports = [_port("M", "s", "in", "set"), _port("M", "r", "in", "reset"), _port("M", "q", "out", "q"), _port("M", "d", "out", "qn")]
    rows = [_lrow(1, "s"), _lrow(2, "r"), _rrow(70, "q"), _rrow(71, "d")]
    return _sheet(blocks, ports, rows)


def test_memory_set_reset_and_outputs_always_opposite():
    for dom in ("", "set", "reset"):
        s = _mem(dom)
        vals, r = _out(s, {"row:1": 1, "row:2": 0}, net="q")
        assert vals[-1] == 1 and r["frames"][-1]["values"]["d"] == 0            # A=1 → C=1 · D=0
        r2 = sim.simulate(s, {"row:1": 0, "row:2": 0}, r["state"], 1.0, {})
        assert r2["frames"][-1]["values"]["q"] == 1                           # A→0 이어도 C 유지
        r3 = sim.simulate(s, {"row:1": 0, "row:2": 1}, r2["state"], 2.0, {})
        assert r3["frames"][-1]["values"]["q"] == 0 and r3["frames"][-1]["values"]["d"] == 1   # B=1 → C=0 · D=1


def test_memory_both_inputs_follow_dominance():
    assert _out(_mem("set"), {"row:1": 1, "row:2": 1}, net="q")[0][-1] == 1            # SET DOMINANT: both 1 → C=1
    assert _out(_mem("reset"), {"row:1": 1, "row:2": 1}, net="q")[0][-1] == 0          # RESET DOMINANT: both 1 → C=0
    # BASIC: both simultaneously 1 → outputs change state (한 번) — 0 에서 시작했으니 1
    assert _out(_mem(""), {"row:1": 1, "row:2": 1}, net="q")[0][-1] == 1


# ---------------------------------------------------------------- 자격 OR · A/B 투표 · ACTIVATION · EQUAL
def _vote(a, b, op):
    blocks = {"V": _blk("VOTE", "vote", f"{a}/{b}", param={"a": a, "b": b, "op": op})}
    ports = [_port("V", f"i{k}", "in") for k in range(b)] + [_port("V", "y", "out")]
    rows = [_lrow(k + 1, f"i{k}") for k in range(b)] + [_rrow(70, "y")]
    return _sheet(blocks, ports, rows)


def test_qualified_or_signs_follow_legend():
    # 범례 G003 QUALIFIED OR GATE '( * ) n' — ≥ · > · ≤ · < · = · ≠ (19VA: In > N · In >= N · In < N · In <= N · In = N)
    for op, f in sim.VOTE_OPS.items():
        for bits in itertools.product((0, 1), repeat=3):
            got = _out(_vote(2, 3, op), {f"row:{k + 1}": v for k, v in enumerate(bits)})[0][-1]
            assert got == int(f(sum(bits), 2)), (op, bits, got)


def test_coincidence_matrix_a_of_b_is_at_least():
    s = _vote(2, 3, "ge")
    assert _out(s, {"row:1": 1, "row:2": 0, "row:3": 0})[0][-1] == 0
    assert _out(s, {"row:1": 1, "row:2": 1, "row:3": 0})[0][-1] == 1
    assert _out(s, {"row:1": 1, "row:2": 1, "row:3": 1})[0][-1] == 1


def test_activation_box_is_always_on():
    blocks = {"A": _blk("SIGNAL", "source", "1")}
    s = _sheet(blocks, [_port("A", "y", "out")], [_rrow(70, "y")])
    assert _out(s, {})[0][-1] == 1
    assert _out(s, {"block:A": 0})[0][-1] == 0                                  # 사람이 0 으로 줄 수는 있다


def test_equal_outputs_one_when_both_inputs_same():
    # 19VA EQUAL (IN1 · IN2 → OUT) · HRSG '=' : IF INPUT A AND B ARE SAME, OUTPUT C IS LOGIC 1 — 디지털 둘
    blocks = {"E": _blk("EQUAL", "unknown", "EQUAL", aop="equal")}
    ins = [("a", {"name": "IN1"}), ("b", {"name": "IN2"})]
    assert analog._digital("equal", blocks["E"], ins, {}, {"a": 1, "b": 1}) == 1
    assert analog._digital("equal", blocks["E"], ins, {}, {"a": 1, "b": 0}) == 0
    assert analog._digital("equal", blocks["E"], ins, {"a": 5.0, "b": 5.0}, {}) == 1


# ---------------------------------------------------------------- 아날로그 (19VA SIGNAL PROCESSING SYMBOLS 2/4 · 3/4)
def _ab(**pr):
    return _blk("OP", "unknown", "OP", param={"a_user": dict(pr)})    # 사람이 넣은 값 자리 (aops.params)


def test_analog_formulas_match_legend_math_equations():
    two = [("a", {"name": "IN1"}), ("b", {"name": "IN2"})]
    v = {"a": 6.0, "b": 2.0}
    assert aops.compute("sum", _ab(), two, v)[0] == 8                    # M = X1 + X2
    assert aops.compute("sum", _ab(), [("a", {"name": "+"}), ("b", {"name": "-"})], v)[0] == 4   # 부호 계수
    assert aops.compute("mean", _ab(), two, v)[0] == 4                   # 평균
    assert aops.compute("diff", _ab(), two, v)[0] == 4                   # X1 − X2
    assert aops.compute("absdiff", _ab(), [("a", {"name": "IN1"}), ("b", {"name": "IN2"})], {"a": 2.0, "b": 6.0})[0] == 4
    assert aops.compute("mul", _ab(), two, v)[0] == 12 and aops.compute("div", _ab(), two, v)[0] == 3
    one = [("a", {"name": "X"})]
    assert aops.compute("gain", _ab(k=2), one, {"a": 3.0})[0] == 6 and aops.compute("rgain", _ab(k=2), one, {"a": 3.0})[0] == -6
    assert aops.compute("sqrt", _ab(), one, {"a": 9.0})[0] == 3 and aops.compute("pow", _ab(n=2), one, {"a": 3.0})[0] == 9
    assert aops.compute("abs", _ab(), one, {"a": -4.0})[0] == 4
    assert aops.compute("hilim", _ab(h=5), one, {"a": 9.0})[0] == 5 and aops.compute("hilim", _ab(h=5), one, {"a": 3.0})[0] == 3
    assert aops.compute("lolim", _ab(l=5), one, {"a": 1.0})[0] == 5 and aops.compute("lolim", _ab(l=5), one, {"a": 7.0})[0] == 7
    assert aops.compute("bias", _ab(b=1.5), one, {"a": 2.0})[0] == 3.5
    three = [("a", {"name": "IN1"}), ("b", {"name": "IN2"}), ("c", {"name": "IN3"})]
    v3 = {"a": 1.0, "b": 9.0, "c": 5.0}
    assert aops.compute("max", _ab(), three, v3)[0] == 9 and aops.compute("min", _ab(), three, v3)[0] == 1
    # MEDIAN: M = MIN(MAX(X1,X2), MAX(X1,X3), MAX(X2,X3)) = 5
    assert aops.compute("median", _ab(), three, v3)[0] == min(max(1, 9), max(1, 5), max(9, 5)) == 5


def test_transfer_picks_in1_when_condition_is_one():
    ins = [("a", {"name": "IN1"}), ("b", {"name": "IN2"}), ("c", {"name": "FLAG"})]
    v = {"a": 10.0, "b": 20.0}
    assert aops.compute("transfer", _ab(), ins, v, {"c": 1})[0] == 10     # M = IN1 if C=1
    assert aops.compute("transfer", _ab(), ins, v, {"c": 0})[0] == 20     # M = IN2 if C=0


def test_signal_monitor_states_strict_on_high_inclusive_on_low():
    # 3/4: STATE 2 (ALARM) X > H · L: STATE 1 (ALARM) X < L · STATE 2 X >= L — 같은 값은 넘은 것이 아니다
    assert analog.compare("high", 10.0, 10.0) == 0 and analog.compare("high", 10.1, 10.0) == 1
    assert analog.compare("low", 10.0, 10.0) == 0 and analog.compare("low", 9.9, 10.0) == 1


def test_deviation_is_one_when_difference_exceeds_d():
    ins = [("a", {"name": "IN1"}), ("b", {"name": "IN2"})]
    assert analog._digital("dev", _ab(d=3), ins, {"a": 10.0, "b": 6.0}, {}) == 1
    assert analog._digital("dev", _ab(d=3), ins, {"a": 10.0, "b": 8.0}, {}) == 0
