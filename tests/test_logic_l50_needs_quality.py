"""L50 — needs 전수 시뮬레이션이 잡은 것: 기본 상태에서 이미 그 값인 출력 · 입력선을 못 읽은 판정 블록의 사유 ·
다음 블록 이름 줄이기 · 1 ↔ 0 토글 (화면)."""
from pathlib import Path

from app.logic import sequence

ROOT = Path(__file__).resolve().parents[1]


def _sheet(blocks, ports, rows=(), nets=None):
    order = {n: [[0, 0, 1, 1, 0.0]] for n in {p["net"] for p in ports}}
    return {"page": 1, "sheet_no": "T001", "title": "t", "pitch": 10.0, "blocks": blocks, "ports": ports,
            "rows": list(rows), "table": {}, "nets": nets or {n: {"segs": [[0, 0, 1, 1]], "jumps": [], "dashed": False} for n in order},
            "order": order, "findings": [], "logic": [0, 0, 100, 100]}


def _blk(func, logic, label=None, **kw):
    d = {"kind": "RECT", "func": func, "logic": logic, "label": label or func, "read": label or func, "bbox": [0, 0, 10, 10],
         "cells": [[0, 0, 10, 10]], "param": {}, "group": "", "pointer": None, "roles": {}, "key": "|", "at": [5, 5]}
    d.update(kw)
    return d


def _port(block, net, d, role=""):
    return {"block": block, "net": net, "dir": d, "at": [0, 0], "side": "L" if d == "in" else "R", "cell": 0, "role": role}


def test_not_of_and_is_already_on_by_default():
    # 행 1 · 2 → AND → NOT → 출력 행.  아무것도 주지 않으면 AND 0 → NOT 1 : '이미 1' 이라고 말해야 한다
    blocks = {"B1": _blk("AND", "and"), "B2": _blk("NOT", "not")}
    ports = [_port("B1", "1", "in"), _port("B1", "2", "in"), _port("B1", "3", "out"), _port("B2", "3", "in"), _port("B2", "4", "out")]
    rows = [{"n": 1, "side": "L", "net": "1", "desc": "A", "fm": "", "kks": ""}, {"n": 2, "side": "L", "net": "2", "desc": "B", "fm": "", "kks": ""},
            {"n": 70, "side": "R", "net": "4", "desc": "OUT", "fm": "", "kks": ""}]
    s = _sheet(blocks, ports, rows)
    r = sequence.needs([s], 1, "block:B2")
    assert r["ok"] and len(r["outputs"]) == 1
    o = r["outputs"][0]
    assert o["now"] == 1 and o["plan"]["signals"]["already"] is True
    # 꺼지려면 — AND 가 1 이어야 하므로 두 행이 꼭 필요
    r0 = sequence.needs([s], 1, "block:B2", value=0)
    sg = r0["outputs"][0]["plan"]["signals"]
    assert sorted(x["text"] for x in sg["need"]) == ["A", "B"] and sg["already"] is False and r0["outputs"][0]["now"] == 1


def test_memory_without_read_inputs_names_the_missing_lines():
    blocks = {"B1": _blk("MEMORY", "memory", "S/R", param={"dominant": "reset"}, roles={"set_cell": 0, "reset_cell": 1})}
    ports = [_port("B1", "9", "out", "q")]
    rows = [{"n": 70, "side": "R", "net": "9", "desc": "OUT", "fm": "", "kks": ""}]
    s = _sheet(blocks, ports, rows)
    r = sequence.needs([s], 1, "block:B1")
    gaps = r["outputs"][0]["plan"]["signals"]["gaps"]
    assert gaps and "SET · RESET 입력선" in gaps[0]["text"] and "판정 못 한" not in gaps[0]["text"]


def test_next_block_label_is_short():
    long = "MOV BLOCK (OPEN CLOSE) <TYPE-III-1>\nA-MD ENOPENCMD CMDO AOPEN ASTOP CB-OPEN ENCLOSE"
    assert sequence._block_short({"func": "MACRO", "macro": {"title": long}}, "B9") == "MOV BLOCK (OPEN CLOSE) <TYP…"
    assert sequence._block_short({"func": "AND", "label": "AND"}, "B9") == "AND"


def test_screen_has_value_toggle_and_already_on_text():
    js = (ROOT / "app/static/logic.js").read_text(encoding="utf-8")
    html = (ROOT / "app/static/logic.html").read_text(encoding="utf-8")
    assert 'id="needs-val"' in html
    assert 'needsOpen(ND.target, ND.value === 1 ? 0 : 1)' in js
    assert "이 출력이 꺼지려면" in js and "sig.already" in js
