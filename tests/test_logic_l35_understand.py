"""L35 — 로직 이해: 명령마다 시뮬레이터로 켜고 · 막고 · 놓고 · 꺼 본 결과 (막는 신호 · 자기유지 · 끄는 신호 ·
늘 켜짐 · 상수로 묶인 길 · 반대 명령 동시 지령)."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.logic import api, behavior, sequence, store
from tests.test_logic_l32_sequence import _B, _P, _bundle, _sheet

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "app/static/logic.js").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _own_data(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PID_LOGIC_WARM", "0")
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear()
    yield
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear()


def _keys(ls):
    return {l["key"] for l in ls or []}


def test_trip_blocks_the_command_and_a_plain_and_is_momentary():
    r = behavior.learn_one(_bundle(), 1, 90, 1, {})
    assert r["reached"]
    assert "row:2" in _keys(r["interlocks"])          # TRIP 이 1 이면 안 선다
    assert r["latch"] is False                         # 메모리가 없다 — 놓으면 꺼진다
    assert r["always_on"] is False


def _latched():
    """SET = AND(PERMISSIVE, PB START) · RESET = OR(PB STOP, TRIP) → MEMORY Q → 90행 FAN A START CMD."""
    g = _sheet(1, "G001", [
        {"n": 1, "side": "L", "net": "perm", "desc": "FAN A PERMISSIVE", "fm": ""},
        {"n": 2, "side": "L", "net": "trip", "desc": "FAN A TRIP", "fm": ""},
        {"n": 90, "side": "R", "net": "q", "desc": "FAN A START CMD", "to": ""},
    ], {"A": _B("and"), "O": _B("or"), "M": _B("memory", func="MEMORY"),
        "PS": _B("source", "START", "PUSH BUTTON"), "PT": _B("source", "STOP", "PUSH BUTTON")},
        [_P("PS", "ps", "out"), _P("PT", "pt", "out"),
         _P("A", "perm", "in"), _P("A", "ps", "in"), _P("A", "set", "out"),
         _P("O", "pt", "in"), _P("O", "trip", "in"), _P("O", "rst", "out"),
         _P("M", "set", "in", "set"), _P("M", "rst", "in", "reset"), _P("M", "q", "out", "q")], title="FAN A")
    g["blocks"]["M"]["param"] = {"dominant": "reset"}
    return [g]


def test_latch_is_found_and_its_stop_signals():
    r = behavior.learn_one(_latched(), 1, 90, 1, {})
    assert r["reached"], r
    assert r["latch"] is True and r["latch_released"] == "buttons"   # 누름단추를 놓아도 유지
    assert {"block:PT", "row:2"} <= _keys(r["stoppers"])            # STOP · TRIP 이 끈다
    assert {"block:PT", "row:2"} <= _keys(r["interlocks"])
    assert not r["drops"]                                            # 허가를 잃어도 래치는 유지 (이 회로)


def test_always_on_command_is_reported_with_what_turns_it_off():
    g = _sheet(1, "G001", [
        {"n": 1, "side": "L", "net": "ok", "desc": "COMPR NO FLT", "fm": ""},
        {"n": 90, "side": "R", "net": "stp", "desc": "COMPR STOP CMD", "to": ""},
    ], {"N": _B("not")}, [_P("N", "ok", "in"), _P("N", "stp", "out")], title="COMPR")
    r = behavior.learn_one([g], 1, 90, 1, {})
    assert r["reached"] and r["always_on"] is True
    assert "row:1" in _keys(r["interlocks"])


def _tied(with_button):
    blocks = {"O": _B("or"), "A": _B("and"), "Z": _B("source", "0", "SIGNAL")}
    ports = [_P("Z", "z", "out"), _P("O", "z", "in"), _P("A", "perm", "in"), _P("A", "o", "in"), _P("A", "cmd", "out")]
    if with_button:
        blocks["PB"] = _B("source", "OPEN", "PUSH BUTTON")
        ports += [_P("PB", "pb", "out"), _P("O", "pb", "in")]
    ports.append(_P("O", "o", "out"))
    return [_sheet(1, "G001", [{"n": 1, "side": "L", "net": "perm", "desc": "MOV READY", "fm": ""},
                               {"n": 90, "side": "R", "net": "cmd", "desc": "MOV OPEN CMD", "to": ""}],
                   blocks, ports, title="MOV")]


def test_constant_tied_path_is_named_and_avoided_when_another_path_exists():
    r = behavior.learn_one(_tied(False), 1, 90, 1, {})
    assert r["reached"] and r["tied_off"]                            # 상수 '0' 을 뒤집어야만 선다
    assert any(l.get("const") == 0 for l in r["labels"])
    r = behavior.learn_one(_tied(True), 1, 90, 1, {})
    assert r["reached"] and not r.get("tied_off")                    # 누름단추 길이 있으면 그 길
    assert "block:PB" in {k for v in r["forces"].values() for k in v}


def _pair(interlocked):
    rows = [{"n": 1, "side": "L", "net": "a", "desc": "VALVE OPEN PERMISSIVE", "fm": ""},
            {"n": 2, "side": "L", "net": "b", "desc": "VALVE CLOSE PERMISSIVE", "fm": ""},
            {"n": 90, "side": "R", "net": "op", "desc": "VALVE OPEN CMD", "to": ""},
            {"n": 91, "side": "R", "net": "cl", "desc": "VALVE CLOSE CMD", "to": ""}]
    blocks = {"AO": _B("and"), "AC": _B("and"), "PO": _B("source", "OPEN", "PUSH BUTTON"), "PC": _B("source", "CLOSE", "PUSH BUTTON")}
    ports = [_P("PO", "po", "out"), _P("PC", "pc", "out"), _P("AO", "a", "in"), _P("AO", "po", "in"), _P("AO", "op", "out"),
             _P("AC", "b", "in"), _P("AC", "pc", "in"), _P("AC", "cl", "out")]
    if interlocked:                                   # CLOSE 는 OPEN 허가가 없을 때만
        blocks["N"] = _B("not")
        ports += [_P("N", "a", "in"), _P("N", "na", "out"), _P("AC", "na", "in")]
    return [_sheet(1, "G001", rows, blocks, ports, title="VALVE")]


def test_opposite_commands_both_on_or_split_by_a_signal():
    out = behavior.learn(_pair(False), {})
    p = next(p for p in out["pairs"] if p["equip"] == "VALVE")
    assert p["both"] is True and not p["exclusive"]
    assert out["summary"]["both_on"]
    out = behavior.learn(_pair(True), {})
    p = next(p for p in out["pairs"] if p["equip"] == "VALVE")
    assert p["exclusive"] and p["both"] is False and "VALVE OPEN PERMISSIVE" in p["split"]


def test_negated_action_is_a_status_not_a_command():
    assert sequence.classify("#11 HRSG NO TRIP") is None
    assert sequence.classify("PUMP NO 1 START CMD")[0] == "START"     # 'NO' 가 동작 바로 앞이 아니면 그대로
    assert ("START", "STOP") in sequence.vocab()["opposites"]


def test_version_bump_makes_old_learning_stale(tmp_path):
    (tmp_path / "result.json").write_text("{}")
    assert behavior.key_of(tmp_path).startswith(f"v{behavior.VERSION}:")


def test_screen_shows_the_understanding():
    for f in ("understandHtml", "seqInsightHtml"):
        assert f"function {f}" in JS, f
    assert 'data-a="insight"' in JS and 'SEQ.view === "insight"' in JS
