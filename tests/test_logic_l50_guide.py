"""L50 — 순차 동작 안내를 명령마다 끝까지 따라가 본 시뮬레이션이 잡은 것: 권하는 갈래끼리 어긋남 · 펄스 = 0 ·
상자 단자 없는 Typical 입력이 출력 행과 한 선 · 권하는 길을 시뮬레이터로 시험한 표시(tested)."""
from app.logic import sequence, sim


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


def _port(block, net, d, role=""):
    return {"block": block, "net": net, "dir": d, "at": [0, 0], "side": "L" if d == "in" else "R", "cell": 0, "role": role}


def _lrow(n, net, desc):
    return {"n": n, "side": "L", "net": net, "desc": desc, "fm": "", "kks": ""}


def _rrow(n, net, desc):
    return {"n": n, "side": "R", "net": net, "desc": desc, "fm": "", "kks": ""}


def _forces(p):
    return sequence._tree_forces(sequence.link(p), p["page"])


def test_recommended_branches_do_not_contradict_each_other():
    # OUT = AND(A, OR(A, B))  ·  OR=1 갈래: A 또는 B.  앞에서 A=1 이 꼭 필요하니 OR 갈래도 A 로 — B 를 따로 묻지 않는다
    # 반대로 OUT2 = AND(A, NOT(OR(A, B))) 는 OR=0 → A=0 · B=0 이라 A 가 1 이면서 0 — 어긋남을 숨기지 않고 적는다
    blocks = {"O": _blk("OR", "or"), "A1": _blk("AND", "and")}
    ports = [_port("O", "a", "in"), _port("O", "b", "in"), _port("O", "o", "out"), _port("A1", "a", "in"), _port("A1", "o", "in"), _port("A1", "y", "out")]
    rows = [_lrow(1, "a", "A"), _lrow(2, "b", "B"), _rrow(70, "y", "OUT")]
    s = _sheet(blocks, ports, rows)
    p = sequence.plan([s], 1, 70, 1)
    sg = p["signals"]
    assert sorted(x["key"] for x in sg["need"]) == ["row:1"] and sg["tested"] == 1
    assert all("어긋나는" not in g["text"] for g in sg["gaps"])


def test_conflict_is_reported_when_no_branch_fits():
    # OUT = AND(A, NOT(A)) — 어느 갈래도 없다: A 는 1 이면서 0.  시험은 0 이고 요약이 그 사실을 말한다
    blocks = {"N": _blk("NOT", "not"), "A1": _blk("AND", "and")}
    ports = [_port("N", "a", "in"), _port("N", "na", "out"), _port("A1", "a", "in"), _port("A1", "na", "in"), _port("A1", "y", "out")]
    rows = [_lrow(1, "a", "A"), _rrow(70, "y", "OUT")]
    p = sequence.plan([_sheet(blocks, ports, rows)], 1, 70, 1)
    assert p["signals"]["tested"] == 0


def test_pulse_zero_is_default_not_a_demand_on_its_input():
    # Q = 메모리(SET=A, RESET=PD(B)) 를 1 로: RESET 0 은 '펄스는 가만히 있으면 0' — B 를 0 으로 묻지 않는다
    blocks = {"M": _blk("MEMORY", "memory", "S/R", roles={"set_cell": 0, "reset_cell": 1}), "P": _blk("PD", "pulse")}
    ports = [_port("P", "b", "in"), _port("P", "pb", "out"), _port("M", "a", "in", "set"), _port("M", "pb", "in", "reset"), _port("M", "q", "out", "q")]
    rows = [_lrow(1, "a", "A"), _lrow(2, "b", "B"), _rrow(70, "q", "Q")]
    p = sequence.plan([_sheet(blocks, ports, rows)], 1, 70, 1)
    keys = [n.get("key") for n in sequence._first_leaves(sequence.link(p))]
    assert "row:2" not in keys
    assert [x["key"] for x in p["signals"]["need"]] == ["row:1"] and p["signals"]["zero"] == [] and p["signals"]["tested"] == 1


def test_tested_flag_uses_the_simulator_and_cache_is_optional():
    blocks = {"A1": _blk("AND", "and")}
    ports = [_port("A1", "a", "in"), _port("A1", "b", "in"), _port("A1", "y", "out")]
    rows = [_lrow(1, "a", "A"), _lrow(2, "b", "B"), _rrow(70, "y", "OUT")]
    s = _sheet(blocks, ports, rows)
    p1 = sequence.plan([s], 1, 70, 1)
    cache = {}
    p2 = sequence.plan([s], 1, 70, 1, None, cache)
    assert p1["signals"]["tested"] == 1 == p2["signals"]["tested"]
    assert {k: v for k, v in p1["nodes"].items()} == {k: v for k, v in p2["nodes"].items()}
    assert sequence.needs([s], 1, "block:A1", cache=cache)["outputs"][0]["plan"]["signals"]["tested"] == 1


def test_screen_shows_tested_badge():
    from pathlib import Path
    js = (Path(__file__).resolve().parents[1] / "app/static/logic.js").read_text(encoding="utf-8")
    assert "시험 확인" in js and "sig.tested" in js
