"""L32 — 순차 동작 시뮬레이션 (START · STOP · OPEN · CLOSE · TRIP 을 조건부터 차례로).

  * 동작 행 목록 — 출력 행 설명에서 동작 낱말(config/logic_sequence.yaml)로 가르고 장비마다 모은다.
  * 조건 나무 — 범례 정의를 거꾸로 (시뮬레이터와 같은 `_back_options`).  AND 는 모두 · OR 는 고르기 · 다른 시트 조건은 ref ·
    from-to 가 어긋난 입력은 ft · 매크로는 그 Typical 안으로 · 같은 조건은 한 마디(같은 id).
  * 읽지 못한 게이트 입력에 사람이 답한 값(hold:) — 읽힌 입력이 출력을 정하면 게이트가 이긴다 (논리 원칙 L18).
  * 갈래 시험 — 갈래마다 같은 시뮬레이터로 미리 돌려 본다.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.logic import api, sequence, sim, store

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "app/static/logic.js").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _own_data(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PID_LOGIC_WARM", "0")
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear()
    yield
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear()


def _P(b, n, d, role=""):
    return {"block": b, "net": n, "dir": d, "role": role, "cell": 0}


def _B(lg, label="", func=None, **kw):
    return {"func": func or lg.upper(), "logic": lg, "group": "", "label": label, "param": {}, "bbox": [0, 0, 10, 10], **kw}


def _sheet(page, no, rows, blocks, ports, title=None):
    nets = {r["net"] for r in rows if r.get("net")} | {p["net"] for p in ports}
    for r in rows:
        r.setdefault("at", [10, r["n"] * 10])
    return {"page": page, "sheet_no": no, "title": title or ("T" + no), "logic": [100, 0, 500, 800], "pitch": 10,
            "frame": None, "nets": {n: {"segs": []} for n in nets}, "order": {}, "blocks": blocks, "ports": ports,
            "rows": rows, "table": [dict(r) for r in rows], "dangling": [], "stray_arrows": [], "findings": []}


def _bundle():
    """G001: (PERMISSIVE AND NOT TRIP) AND (AUTO REQ OR 누름단추 START) → 90행 PUMP A START CMD.
       AUTO REQ 는 G002-90 에서 온다 (G002: 두 입력 AND).  G003 은 TO 가 어긋난 FM 을 받는다."""
    g1 = _sheet(1, "G001", [
        {"n": 1, "side": "L", "net": "perm", "desc": "PUMP A START PERMISSIVE", "fm": ""},
        {"n": 2, "side": "L", "net": "trip", "desc": "PUMP A TRIP", "fm": ""},
        {"n": 3, "side": "L", "net": "areq", "desc": "PUMP A AUTO START REQ", "fm": "G002-90",
         "ref": {"sheet": "G002", "row": 90, "page": 2, "other_bundle": False, "src_row": 90}},
        {"n": 90, "side": "R", "net": "cmd", "desc": "PUMP A START CMD", "to": ""},
        {"n": 91, "side": "R", "net": "cmd2", "desc": "PUMP A FAIL TO START FAULT", "to": ""},
    ], {"N": _B("not"), "A1": _B("and"), "O": _B("or"), "A2": _B("and"), "PB": _B("source", "START", "PUSH BUTTON")},
        [_P("N", "trip", "in"), _P("N", "ntrip", "out"),
         _P("A1", "perm", "in"), _P("A1", "ntrip", "in"), _P("A1", "ok", "out"),
         _P("PB", "pb", "out"),
         _P("O", "areq", "in"), _P("O", "pb", "in"), _P("O", "req", "out"),
         _P("A2", "ok", "in"), _P("A2", "req", "in"), _P("A2", "cmd", "out")], title="PUMP A")
    g2 = _sheet(2, "G002", [
        {"n": 1, "side": "L", "net": "x", "desc": "LEVEL OK", "fm": ""},
        {"n": 2, "side": "L", "net": "y", "desc": "SYSTEM READY", "fm": ""},
        {"n": 90, "side": "R", "net": "z", "desc": "PUMP A AUTO START REQ", "to": "G001-3"},
    ], {"A": _B("and")}, [_P("A", "x", "in"), _P("A", "y", "in"), _P("A", "z", "out")])
    g3 = _sheet(3, "G003", [
        {"n": 1, "side": "L", "net": "w", "desc": "PUMP A AUTO START REQ", "fm": "G002-90",
         "ref": {"sheet": "G002", "row": 90, "page": 2, "other_bundle": False, "src_row": 90},
         "ft": {"ok": False, "why": ["G002-90 의 TO 는 G001-3 를 가리킵니다"], "peer": "G002-90"}},
        {"n": 90, "side": "R", "net": "v", "desc": "VALVE B OPEN CMD", "to": ""},
    ], {"A": _B("and"), "S": _B("source", "OPEN", "PUSH BUTTON")},
        [_P("A", "w", "in"), _P("S", "s", "out"), _P("A", "s", "in"), _P("A", "v", "out")])
    return [g1, g2, g3]


def _leaves(p):
    return [v for v in p["nodes"].values() if v["t"] == "leaf"]


def test_classify_reads_action_kind_and_equipment_from_the_row_text():
    assert sequence.classify("AB HHP MAIN STM DRN MOV 1 OP CMD") == ("OPEN", "command", "AB HHP MAIN STM DRN MOV 1")
    assert sequence.classify("PUMP A START REQUEST")[:2] == ("START", "request")
    assert sequence.classify("CCW PUMP B RUNNING")[:2] == ("RUN", "state")
    assert sequence.classify("FAIL TO START FAULT") is None             # 고장 · 알림 행은 동작이 아니다
    assert sequence.classify("CCW SPRAY PP A SUCTION STR DP H") is None   # STR = 스트레이너
    assert sequence.classify("OPEN/CLOSE") is None                        # 동작이 둘이면 고르지 않는다


def test_commands_group_rows_by_equipment_and_put_commands_first():
    cm = sequence.commands(_bundle())
    by = {e["equip"]: e for e in cm}
    assert "PUMP A" in by and "VALVE B" in by
    acts = {a["action"]: a["rows"] for a in by["PUMP A"]["actions"]}
    assert acts["START"][0]["kind"] == "command" and acts["START"][0]["row"] == 90
    assert all("FAULT" not in r["desc"] for rows in acts.values() for r in rows)


def test_plan_reads_the_gate_definitions_backwards():
    p = sequence.plan(_bundle(), 1, 90, 1)
    assert p["ok"]
    tree = sequence.link(p)
    assert tree["gate"]["logic"] == "and" and tree["t"] == "all"
    lv = {v.get("key"): v for v in _leaves(p) if v.get("key")}
    assert lv["row:1"]["want"] == 1                                  # PERMISSIVE 1
    zero = [v for v in _leaves(p) if v["kind"] == "zero"]            # TRIP 은 없어야 한다 (NOT 의 입력 0)
    assert any(i["key"] == "row:2" for z in zero for i in z["items"])
    anys = [v for v in p["nodes"].values() if v["t"] == "any"]       # OR — 자동 요청 · 누름단추 중 하나
    assert len(anys) == 1 and len(anys[0]["kids"]) == 2
    assert lv["row:3"]["ref"]["sheet"] == "G002" and lv["block:PB"]["kind"] == "button"


def test_cross_sheet_condition_follows_the_fm_with_the_same_planner():
    p = sequence.plan(_bundle(), 2, 90, 1)
    keys = {v.get("key") for v in _leaves(p)}
    assert {"row:1", "row:2"} <= keys


def test_input_with_a_broken_from_to_carries_the_reason():
    p = sequence.plan(_bundle(), 3, 90, 1)
    ft = [v for v in _leaves(p) if v.get("ft")]
    assert ft and "G001-3" in ft[0]["ft"]["why"][0]


def test_repeated_condition_is_one_node():
    """같은 선 · 같은 값은 한 마디 — 한 번 답하면 그 자리 모두 답한 것."""
    s = _sheet(1, "G001", [{"n": 1, "side": "L", "net": "a", "desc": "A"},
                           {"n": 90, "side": "R", "net": "o", "desc": "X START CMD"}],
               {"A1": _B("and"), "A2": _B("and"), "A3": _B("and")},
               [_P("A1", "a", "in"), _P("A1", "a", "in"), _P("A1", "m", "out"),
                _P("A2", "a", "in"), _P("A2", "m", "in"), _P("A2", "n", "out"),
                _P("A3", "m", "in"), _P("A3", "n", "in"), _P("A3", "o", "out")])
    p = sequence.plan([s], 1, 90, 1)
    assert sum(1 for v in _leaves(p) if v.get("key") == "row:1") == 1


def test_hold_answers_only_what_the_drawing_could_not_read():
    """입력선을 다 읽지 못한 게이트: 사람이 '빠진 입력은 만족' 이라고 답한 값은 출력이 정해지지 않을 때만 쓴다."""
    s = _sheet(1, "G001", [{"n": 1, "side": "L", "net": "a", "desc": "A"},
                           {"n": 90, "side": "R", "net": "o", "desc": "OUT"}],
               {"N": _B("not"), "A": _B("and")},
               [_P("N", "q", "out"), _P("A", "a", "in"), _P("A", "q", "in"), _P("A", "o", "out")])
    last = lambda f: sim.simulate(s, f)["frames"][-1]["values"]
    # L46 — 입력이 연결 안 된 NOT 은 입력을 비활성(0)으로 보아 1 을 낸다
    assert last({"row:1": 1})["q"] == 1 and last({"row:1": 1})["o"] == 1
    v = last({"row:1": 1, "hold:q": 0})            # 사람이 '빠진 입력은 1' 이라고 답하면 그 값
    assert v["q"] == 0 and v["o"] == 0
    # AND 하나만 읽힌 자리 — 읽힌 입력이 0 이면 출력은 0 으로 정해진다: 사람 값이 이기지 않는다
    s2 = _sheet(1, "G001", [{"n": 1, "side": "L", "net": "a", "desc": "A"},
                            {"n": 90, "side": "R", "net": "o", "desc": "OUT"}],
                {"A": _B("and")}, [_P("A", "a", "in"), _P("A", "o", "out")])
    assert sim.simulate(s2, {"row:1": 0, "hold:o": 1})["frames"][-1]["values"]["o"] == 0
    assert sim.simulate(s2, {"row:1": 1, "hold:o": 1})["frames"][-1]["values"]["o"] == 1


def test_stuck_short_gate_offers_a_hold_key():
    s = _sheet(1, "G001", [{"n": 90, "side": "R", "net": "o", "desc": "X OPEN CMD"}],
               {"N": _B("not")}, [_P("N", "o", "out")])
    p = sequence.plan([s], 1, 90, 1)
    st = [v for v in _leaves(p) if v["kind"] == "stuck"]
    assert st and st[0]["key"] == "hold:o"


def test_macro_is_followed_into_its_typical_and_back_to_the_box_terminals():
    typ = _sheet(9, "T009", [{"n": 10, "side": "L", "net": "t1", "desc": "MANUAL OPEN REQUEST"},
                             {"n": 11, "side": "L", "net": "t2", "desc": "REMOTE"},
                             {"n": 70, "side": "R", "net": "to", "desc": "OPEN COMMAND"}],
                 {"G": _B("and")}, [_P("G", "t1", "in"), _P("G", "t2", "in"), _P("G", "to", "out")])
    mac = _B("macro", "MOV", "MACRO", macro={"sheet": "T009", "page": 9, "title": "MOV",
                                              "inputs": [{"net": "pbn", "pin": "M_OPN", "row": 10}, {"net": "rmt", "pin": "REM", "row": 11}],
                                              "outputs": [{"net": "cmd", "pin": "C_OPN", "row": 70, "desc": "OPEN COMMAND"}]})
    g = _sheet(1, "G001", [{"n": 6, "side": "L", "net": "rmt", "desc": "MOV 1 RMT", "fm": "MOV"},
                           {"n": 73, "side": "R", "net": "cmd", "desc": "MOV 1 OP CMD"}],
               {"M": mac, "PB": _B("source", "OPEN", "PUSH BUTTON")},
               [_P("PB", "pbn", "out"), _P("M", "pbn", "in"), _P("M", "rmt", "in"), _P("M", "cmd", "out")])
    sheets = [g, typ]
    p = sequence.plan(sheets, 1, 73, 1)
    keys = {v.get("key") for v in _leaves(p)}
    assert {"block:PB", "row:6"} <= keys                              # Typical 입력 → 상자 단자 → 이 시트의 신호
    tree = sequence.link(p)
    assert tree["gate"]["func"] == "MACRO"
    r = sim.simulate_bundle(sheets, {1: {"block:PB": 1, "row:6": 1}}, None, 1)["focus"]
    assert r["frames"][-1]["values"]["cmd"] == 1                      # 나무가 말한 조건을 주면 명령이 선다


def _client():
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def _job(sheets):
    res = {"pdf_pages": len(sheets), "sheets": sheets, "kinds": {}, "dictionary": {}, "note": "", "seconds": 1}
    job, d = store.new_job("toy.pdf")
    store.write_result(d, res)
    st = store.read_status(d)
    st.update({"state": "done", "sheets": len(sheets), "seconds": 1})
    store.write_status(d, st)
    return job


def test_api_lists_commands_builds_plans_and_tries_branches():
    job = _job(_bundle())
    c = _client()
    items = c.get(f"/logic/api/jobs/{job}/commands").json()["items"]
    assert any(e["equip"] == "PUMP A" for e in items)
    p = c.post(f"/logic/api/jobs/{job}/sequence", json={"page": 1, "row": 90}).json()
    assert p["ok"] and p["root"] in p["nodes"]
    base = {"1": {"row:1": 1}}
    r = c.post(f"/logic/api/jobs/{job}/sequence/try", json={
        "page": 1, "net": p["net"], "want": 1, "forces": base,
        "options": [{"1": {"block:PB": 1}}, {"1": {"row:2": 1, "block:PB": 1}}, {}]}).json()["options"]
    assert [o["reached"] for o in r] == [True, False, False]          # 누름단추면 선다 · TRIP 이 있으면 막힌다
    assert c.post(f"/logic/api/jobs/{job}/sequence", json={"page": "x"}).status_code == 400
    # hold: 는 화면의 시뮬레이션 요청에서도 버려지지 않는다
    sim_body = c.post(f"/logic/api/jobs/{job}/simulate", json={"forces": {"1": {"hold:o": 1, "row:1": 1}}, "page": 1}).json()
    assert "focus" in sim_body


def test_sequence_module_names_no_action_words_and_imports_no_p_and_id_engine():
    src = (ROOT / "app/logic/sequence.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    words = {"START", "STOP", "OPEN", "CLOSE", "TRIP", "CMD", "COMMAND", "REQ"}
    consts = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert not (consts & words), "동작 낱말은 config/logic_sequence.yaml 에 둔다"
    for n in ast.walk(tree):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            mod = getattr(n, "module", "") or ""
            assert "engine" not in mod and "pipeline" not in mod


def test_screen_asks_step_by_step_and_tries_branches_with_the_simulator():
    for name in ("seqStart", "seqWalk", "seqForces", "seqAnswer", "seqBack", "seqFinish", "seqTry", "seqTryLeaf", "seqLink"):
        assert f"function {name}(" in JS
    assert "/sequence/try" in JS and "nofollow" in JS
    assert 'data-a="follow"' in JS and 'data-a="errgo"' in JS     # 다른 시트 조건부터 · 정합성 오류에서 묻기
