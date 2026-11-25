"""L95 — 매크로 연산자 점검에서 나온 것: 기다리는 시간(horizon) · 한 순간 안의 중간 값(MICRO) · 따로 만든 채점기."""
import sys
from pathlib import Path

from app.logic import sim

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "spike"))
from tests.test_logic_l51_functions import _blk, _lrow, _port, _rrow, _sheet, _timer  # noqa: E402


def _window():
    """명령(row 1) 이 5초 이어지면 고장(F) · 고장은 래치.  '되돌림'(row 2)이 있다가 꺼지면 2초 뒤 불일치(D) —
    명령 뒤 5초 **안에** 되돌림이 꺼져야 D 가 선다 (5초가 지나면 F 가 먼저 선다 · 19VA 0013 SOV 의 꼴)."""
    blocks = {"T5": _blk("ON DELAY", "delay_on", param={"t": 5}), "T2": _blk("ON DELAY", "delay_on", param={"t": 2}),
              "N": _blk("NOT", "not"), "A": _blk("AND", "and"), "M": _blk("MEMORY", "memory", param={"dominant": "reset"}),
              "NC": _blk("NOT", "not"), "D": _blk("AND", "and")}
    ports = [_port("T5", "cmd", "in"), _port("T5", "t5", "out"), _port("N", "fb", "in"), _port("N", "nfb", "out"),
             _port("A", "t5", "in"), _port("A", "nfb", "in"), _port("A", "fault", "out"),
             _port("M", "fb", "in", role="set"), _port("NC", "cmd", "in"), _port("NC", "ncmd", "out"), _port("M", "ncmd", "in", role="reset"),
             _port("M", "was", "out", role="q"), _port("D", "was", "in"), _port("D", "nfb", "in"), _port("D", "d0", "out"),
             _port("T2", "d0", "in"), _port("T2", "disc", "out")]
    return _sheet(blocks, ports, [_lrow(1, "cmd"), _lrow(2, "fb"), _rrow(70, "fault"), _rrow(71, "disc")])


def _last(r, net):
    return r["focus"]["frames"][-1]["values"].get(net)


def test_horizon_none_runs_timers_out_as_before():
    s = _timer("delay_on", 3)
    r = sim.simulate_bundle([s], {1: {"row:1": 1}}, None, 1)
    assert [fr["t"] for fr in r["focus"]["frames"]] == [0.0, 3.0] and _last(r, "y") == 1


def test_horizon_holds_time_so_an_input_can_change_while_a_timer_counts():
    s = _window()
    # 끝까지 흘리면: 명령 + 되돌림 → 되돌림 꺼짐 → 이미 5초가 지나 있어 고장이 바로 서고 불일치는 못 선다
    r = sim.simulate_bundle([s], {1: {"row:1": 1, "row:2": 1}}, None, 1)
    r = sim.simulate_bundle([s], {1: {"row:1": 1}}, r["state"], 1)
    assert _last(r, "fault") == 1
    # 시간을 멈추고(0초) 명령 + 되돌림 → 되돌림 꺼짐 → 2초만 흘린다: 불일치가 서고, 5초 타이머는 3초 남아 있다
    r = sim.simulate_bundle([s], {1: {"row:1": 1, "row:2": 1}}, None, 1, horizon=0)
    assert [x["block"] for x in r["focus"]["frames"][-1]["running"]] == ["T5"]
    r = sim.simulate_bundle([s], {1: {"row:1": 1}}, r["state"], 1, horizon=0)
    assert sorted(x["block"] for x in r["focus"]["frames"][-1]["running"]) == ["T2", "T5"] and _last(r, "disc") == 0
    r = sim.simulate_bundle([s], {1: {"row:1": 1}}, r["state"], 1, horizon=2)
    last = r["focus"]["frames"][-1]
    assert last["values"]["disc"] == 1 and last["values"]["fault"] == 0
    assert [(x["block"], x["left"]) for x in last["running"]] == [("T5", 3.0)]
    # 그 뒤 끝까지 흘리면 남은 3초가 지나 고장이 선다 (남은 타이머는 상태에 그대로 있었다)
    r = sim.simulate_bundle([s], {1: {"row:1": 1}}, r["state"], 1)
    assert _last(r, "fault") == 1 and r["focus"]["frames"][-1]["t"] == 5.0


def test_horizon_answer_is_not_mixed_with_the_run_out_answer_in_the_bundle_memo():
    s = _timer("delay_on", 3)
    cache = {}
    a = sim.simulate_bundle([s], {1: {"row:1": 1}}, None, 1, cache=cache, horizon=0)
    b = sim.simulate_bundle([s], {1: {"row:1": 1}}, None, 1, cache=cache)
    c = sim.simulate_bundle([s], {1: {"row:1": 1}}, None, 1, cache=cache, horizon=0)
    assert (_last(a, "y"), _last(b, "y"), _last(c, "y")) == (0, 1, 0)


def test_micro_frames_show_the_values_inside_one_instant_only_when_asked():
    s = _timer("pulse", 2)
    assert "micro" not in sim.simulate_bundle([s], {1: {"row:1": 1}}, None, 1)["focus"]["frames"][0]
    sim.MICRO = True
    try:
        fr = sim.simulate_bundle([s], {1: {"row:1": 1}}, None, 1)["focus"]["frames"][0]
    finally:
        sim.MICRO = False
    assert fr["values"]["y"] == 1 and fr["micro"] and fr["micro"][0]["y"] == 0      # 입력이 선 뒤 · 펄스가 서기 전


def test_independent_grader_catches_a_wrong_gate_and_passes_a_right_one():
    """채점기는 시뮬레이터의 게이트 함수를 쓰지 않는다 — 값이 틀리면 잡아야 한다."""
    import macro_operator_check_l95 as M
    assert M.ref_gate("and", [1, 1, 0]) == 0 and M.ref_gate("or", [0, 0, 1]) == 1 and M.ref_gate("not", [0]) == 1
    assert M.ref_gate("and", [1, None]) is None
    assert M.ref_gate("vote", [1, 1, 1], (2, 3), "eq") == 0 and M.ref_gate("vote", [1, 1, 0], (2, 3), "ge") == 1
    s = _window()
    ops, _ = M.operators(s)
    good = {"t": 0.0, "values": {"cmd": 1, "fb": 0, "t5": 0, "nfb": 1, "fault": 0, "ncmd": 0, "was": 0, "d0": 0, "disc": 0}}
    for o in ops.values():
        o.check(good, set())
    assert not any(o.bad for o in ops.values())
    bad = {"t": 0.0, "values": {**good["values"], "fault": 1}}                      # AND(0, 1) 인데 1
    ops["A"].check(bad, set())
    assert ops["A"].bad
    late = {"t": 9.0, "values": {**good["values"]}}                                 # 명령이 9초 이어졌는데 5초 타이머가 0
    ops["T5"].check(late, set())
    assert ops["T5"].bad


def test_vote_sign_survives_into_the_drawing_and_its_simulation():
    """`2=3`(정확히) 를 그림으로 들여도 부호가 남는다 — 분석 쪽은 '정확히', 그림 쪽은 '이상' 으로 돌아 19VA *_G014 다섯 장이 어긋났었다."""
    from app.logic import draw, draw_sim
    d = draw.clean({"blocks": [{"id": "v", "kind": "VOTE", "x": 400, "y": 300, "param": {"a": 2, "b": 3, "op": "eq"}},
                               {"id": "w", "kind": "VOTE", "x": 400, "y": 340, "param": {"a": 2, "b": 3}}], "wires": []})
    assert [(b["text"], b["param"].get("op")) for b in d["blocks"]] == [("2=3", "eq"), ("2/3", None)]
    s = draw_sim.to_sheet(d, 1)
    assert sorted((b["label"], b["param"]["op"]) for b in s["blocks"].values() if b.get("logic") == "vote") == [("2/3", "ge"), ("2=3", "eq")]
