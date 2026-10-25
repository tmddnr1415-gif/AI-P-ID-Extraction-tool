"""L57 — LOGIC 작도 그림을 PDF 되읽기 없이 바로 시뮬레이션한다 (draw_sim.to_sheet → sim.simulate_bundle).

판정은 전부 sim · analog · aops · fromto 가 한다 — draw_sim 은 꼴만 바꾼다.  그린 게이트가 범례 G003 대로 돌고 · 묶음이면
FROM/TO 와 매크로(Typical)를 넘어가고 · 글자 상자 보기(상수 · 이음점 · 토글 · 감시 · 아날로그 연산 · STEP)가 뜻을 갖고 ·
저장 전 그림(body.doc)이 그대로 돈다.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.logic import draw as D, draw_sim as DS

N = D.N_DEFAULT
ROOT = Path(__file__).resolve().parent.parent


def ry(n):
    return D.ry(n, N)


class _W:
    i = 0

    def __call__(self, pts, **kw):
        _W.i += 1
        return {"id": "w%d" % _W.i, "pts": [list(p) for p in pts], **kw}


W = _W()


def _blk(bid, kind, x, row_c, **param):
    sp = D.SYMBOLS[kind]
    b = {"id": bid, "kind": kind, "x": x, "y": round(row_c - sp["h"] / 2, 2), "w": sp["w"], "h": sp["h"], "text": sp["text"], "param": dict(param)}
    if kind == "VOTE":
        b["text"] = f"{param.get('a', 2)}/{param.get('b', 3)}"
    return b


def _doc(sheet_no="S1", **kw):
    d = D.new_doc(sheet_no, "홍길동")
    d["sheet_no"] = sheet_no
    d.update(kw)
    d.update(D.clean(d))
    d["id"] = (sheet_no.lower() * 12)[:12]
    return d


def _outs(res, sheet):
    v = res["focus"]["frames"][-1]["values"]
    return {r["n"]: v.get(r["net"]) for r in sheet["rows"] if r["side"] == "R" and r.get("net") is not None}


def _gate_doc(kind, n_in, **param):
    """입력 행 1..n_in → 게이트 → 출력 행 N+1"""
    cy = sum(ry(i) for i in range(1, n_in + 1)) / n_in
    g = _blk("g", kind, 500, cy, **param)
    bar = D.bar_of(g) if D.SYMBOLS[kind].get("bar") else None
    wires = [W([(320, ry(i)), (500, ry(i))]) for i in range(1, n_in + 1)]
    if kind == "MEMORY":
        wires = [W([(320, ry(1)), (500, g["y"] + g["h"] / 4)]), W([(320, ry(2)), (500, g["y"] + 3 * g["h"] / 4)])]
    out_y = g["y"] + g["h"] / 4 if kind == "MEMORY" else cy
    wires.append(W([(500 + g["w"], out_y), (700, out_y), (700, ry(N + 1)), (870, ry(N + 1))]))
    left = {str(i): {"desc": f"IN{i}", "fm": "", "kks": ""} for i in range(1, n_in + 1)}
    return _doc("S1", blocks=[g], wires=wires, left=left, right={str(N + 1): {"desc": "OUT", "kks": "", "to": ""}})


def _run(doc, forces, state=None, analog=None):
    r = DS.simulate([doc], doc["id"], forces={doc["id"]: forces}, state=state or {}, analog={doc["id"]: analog or {}})
    return r


# ───────────────────────── 게이트는 범례대로 ─────────────────────────

@pytest.mark.parametrize("kind,n_in,truth", [
    ("AND", 2, {(0, 0): 0, (1, 0): 0, (0, 1): 0, (1, 1): 1}),
    ("OR", 2, {(0, 0): 0, (1, 0): 1, (0, 1): 1, (1, 1): 1}),
    ("NAND", 2, {(0, 0): 1, (1, 0): 1, (0, 1): 1, (1, 1): 0}),
    ("NOR", 2, {(0, 0): 1, (1, 0): 0, (0, 1): 0, (1, 1): 0}),
    ("NOT", 1, {(0,): 1, (1,): 0}),
    ("VOTE", 3, {(0, 0, 0): 0, (1, 0, 0): 0, (1, 1, 0): 1, (1, 1, 1): 1}),
])
def test_drawn_gates_follow_the_legend_truth_table(kind, n_in, truth):
    doc = _gate_doc(kind, n_in, **({"a": 2, "b": 3} if kind == "VOTE" else {}))
    sh = DS.sheets_of([doc])[0]
    g = sh["blocks"]["g"]
    assert g["logic"] == D.SYMBOLS[kind]["logic"]
    assert sum(1 for p in sh["ports"] if p["block"] == "g" and p["dir"] == "in") == n_in     # 막대에 닿은 선이 전부 입력
    for ins, want in truth.items():
        forces = {f"row:{i + 1}": v for i, v in enumerate(ins)}
        assert _outs(_run(doc, forces), sh)[N + 1] == want, (kind, ins)


def test_memory_latches_and_reset_dominant_wins():
    doc = _gate_doc("MEMORY", 2, dominant="reset")
    sh = DS.sheets_of([doc])[0]
    roles = {p["role"] for p in sh["ports"] if p["block"] == "g"}
    assert {"set", "reset", "q"} <= roles
    r1 = _run(doc, {"row:1": 1, "row:2": 0})
    assert _outs(r1, sh)[N + 1] == 1
    r2 = _run(doc, {"row:1": 0, "row:2": 0}, state=r1["state"])
    assert _outs(r2, sh)[N + 1] == 1                       # 래치
    r3 = _run(doc, {"row:1": 1, "row:2": 1}, state=r2["state"])
    assert _outs(r3, sh)[N + 1] == 0                       # RESET 우선


def test_timer_waits_its_seconds_and_frames_count_down():
    doc = _gate_doc("GT", 1, t=3)
    sh = DS.sheets_of([doc])[0]
    r = _run(doc, {"row:1": 1})
    fr = r["focus"]["frames"]
    assert _outs(r, sh)[N + 1] == 1 and fr[-1]["t"] >= 3.0
    assert any(x["block"] == "g" for f in fr for x in f.get("running", []))   # 세는 동안 running 에 남는다 (화면 카운트다운)
    assert fr[0]["values"][sh["rows"][-1]["net"]] == 0                          # 처음 틀에는 아직 0


# ───────────────────────── 묶음: FROM/TO · 매크로 ─────────────────────────

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    from app.logic import api
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def _three_sheet_set(client):
    from tests.test_logic_l56_sets import _three_sheet_set as mk
    return mk(client)


def test_set_simulates_through_macro_typical_and_from_to(client):
    sid, main, typ, rx = _three_sheet_set(client)
    rx["blocks"] = [_blk("n1", "NOT", 500, ry(2))]
    rx["left"] = {"2": {"fm": f"G001-{N + 1}", "kks": "", "desc": "MOV OPEN CMD"}}
    rx["right"] = {str(N + 1): {"desc": "NOT OPEN", "kks": "", "to": ""}}
    g = D.SYMBOLS["NOT"]
    rx["wires"] = [W([(320, ry(2)), (500, ry(2))]), W([(500 + g["w"], ry(2)), (700, ry(2)), (700, ry(N + 1)), (870, ry(N + 1))])]
    client.put(f"/logic/api/drawings/{rx['id']}", json={"author": "홍길동", "doc": rx})
    r = client.post(f"/logic/api/drawings/{main['id']}/simulate", json={"forces": {main["id"]: {"row:5": 1}}}).json()
    assert "error" not in r
    out = {x["n"]: r["focus"]["frames"][-1]["values"].get(x["net"]) for x in r["sheet"]["rows"] if x["side"] == "R"}
    assert out[N + 1] == 0                                 # AOPEN 만 — Typical AND 가 막는다
    r = client.post(f"/logic/api/drawings/{main['id']}/simulate", json={"forces": {main["id"]: {"row:5": 1, "row:6": 1}}}).json()
    out = {x["n"]: r["focus"]["frames"][-1]["values"].get(x["net"]) for x in r["sheet"]["rows"] if x["side"] == "R"}
    assert out[N + 1] == 1                                 # 매크로를 지나 CMD
    assert r["linked"][rx["id"]] == {"2": 1} or r["linked"][rx["id"]] == {2: 1}
    r2 = client.post(f"/logic/api/drawings/{rx['id']}/simulate", json={"forces": {main["id"]: {"row:5": 1, "row:6": 1}}}).json()
    out2 = {x["n"]: r2["focus"]["frames"][-1]["values"].get(x["net"]) for x in r2["sheet"]["rows"] if x["side"] == "R"}
    assert out2[N + 1] == 0                                # 받는 장: FM 으로 1 을 받아 NOT → 0
    assert r2["sheet"]["rows"][0]["ref"]["sheet"] == "G001"


def test_unsaved_drawing_in_body_is_simulated_as_is(client):
    doc = client.post("/logic/api/drawings", json={"name": "LIVE", "author": "홍길동"}).json()
    doc["sheet_no"] = "L1"
    live = _gate_doc("OR", 2)
    live["id"] = doc["id"]
    r = client.post(f"/logic/api/drawings/{doc['id']}/simulate", json={"doc": live, "forces": {doc["id"]: {"row:1": 1}}}).json()
    out = {x["n"]: r["focus"]["frames"][-1]["values"].get(x["net"]) for x in r["sheet"]["rows"] if x["side"] == "R"}
    assert out[N + 1] == 1
    saved = client.get(f"/logic/api/drawings/{doc['id']}").json()
    assert saved["blocks"] == [] and saved["wires"] == []    # 저장은 안 바뀐다
    sheet = client.get(f"/logic/api/drawings/{doc['id']}/sheet").json()
    assert sheet["blocks"] == {}


# ───────────────────────── 선 묶기 ─────────────────────────

def test_crossing_wires_do_not_join_but_dots_and_t_do():
    ws = [W([(400, 200), (600, 200)]), W([(500, 150), (500, 250)]),             # 교차 — 연결 아님
          W([(400, 300), (600, 300)], dots=[[500, 300]]), W([(500, 250), (500, 350)]),   # 점 — 연결 (둘째 선과 끝이 맞닿아 같이 묶인다)
          W([(400, 400), (600, 400)]), W([(500, 400), (500, 450)])]               # T — 끝이 몸통 위 = 연결
    ids = [w["id"] for w in ws]
    doc = _doc("S1", wires=ws)
    sh = DS.sheets_of([doc])[0]
    nets = [set(n["wires"]) for n in sh["nets"].values()]
    assert {ids[0]} in nets                                 # 교차한 가로선은 혼자
    assert any({ids[1], ids[2], ids[3]} <= k for k in nets)   # 세로선 둘(끝 맞닿음) + 점으로 붙은 가로선
    assert {ids[4], ids[5]} in nets                         # T 접합


# ───────────────────────── 글자 상자 보기 ─────────────────────────

def _preset_doc(text, n_in=1):
    pr = next(p for p in D.BOX_PRESETS if p["text"] == text)
    w, h = pr.get("w", 16), pr.get("h", 9)
    b = {"id": "b", "kind": "BOX", "x": 400, "y": round(ry(2) - h / 2, 2), "w": w, "h": h, "text": text, "param": {}}
    for k in ("lines", "above"):
        if pr.get(k):
            b["param"][k] = pr[k]
    if pr.get("time"):
        b["param"]["t"] = 1
    wires = [W([(400 + w, ry(2)), (870, ry(N + 2))])]
    left = {}
    if text == "STEP":
        wires = [W([(320, ry(1)), (400, b["y"] + 18.0)]), W([(320, ry(2)), (400, b["y"] + 29.3)]), W([(440, b["y"] + 18.0), (870, ry(N + 2))])]
        left = {"1": {"desc": "STEP IN", "fm": "", "kks": ""}, "2": {"desc": "CRIT", "fm": "", "kks": ""}}
    elif text not in ("1", "0", "A", "SIG") and not pr.get("src"):
        for i in range(n_in):
            yy = ry(2) + (i - (n_in - 1) / 2) * 3.0
            wires.append(W([(320, ry(1 + i)), (360, ry(1 + i)), (360, yy), (400, yy)]))
            left[str(1 + i)] = {"desc": f"IN{i + 1}", "fm": "", "kks": ""}
    if text == "RUN" or pr.get("sink"):            # 받기만 하는 것 — 들어오는 선 하나 · 나가는 선 없음
        wires = [W([(320, ry(2)), (400, ry(2))])]
        left = {"2": {"desc": "RUNIN", "fm": "", "kks": ""}}
    if pr.get("kind") == "TEXT":                     # 글(주석)은 선이 안 닿는다
        wires, left = [], {}
        b["kind"] = "TEXT"
    notes = [pr["note"]] if pr.get("note") else []
    return _doc("S1", blocks=[b], wires=wires, left=left, right={str(N + 2): {"desc": "OUT", "kks": "", "to": ""}}, notes=notes)


@pytest.mark.parametrize("text", [p["text"] for p in D.BOX_PRESETS])
def test_every_box_preset_has_a_meaning_in_the_simulator(text):
    pr = next(p for p in D.BOX_PRESETS if p["text"] == text)
    doc = _preset_doc(text, n_in=2 if text in ("Σ", "△", "×", "÷", "DEV", "EQUAL", "MED", "|△|", "AVG", ">", "<", "BIT_CNT", "COUNTER") else 1)
    sh = DS.sheets_of([doc])[0]
    if pr.get("kind") == "TEXT":                     # 주석 — 판정 대상이 아니다
        assert "b" not in sh["blocks"] or sh["blocks"]["b"]["logic"] in ("", "unknown")
        return
    b = sh["blocks"]["b"]
    assert not (b["func"] == "UNKNOWN" and b["logic"] == "unknown" and not b.get("aop")), (text, b["func"], b["logic"])
    assert any(p["block"] == "b" for p in sh["ports"])


def test_constant_toggle_monitor_and_step_behave():
    # 상수 1 → 바로 1
    d1 = _preset_doc("1")
    assert _outs(_run(d1, {}), DS.sheets_of([d1])[0])[N + 2] == 1
    # 토글 — 오르는 변마다 뒤집힌다
    dt = _preset_doc("SRST")
    sh = DS.sheets_of([dt])[0]
    assert sh["blocks"]["b"]["logic"] == "toggle"
    r1 = _run(dt, {"row:1": 1}); r2 = _run(dt, {"row:1": 0}, state=r1["state"]); r3 = _run(dt, {"row:1": 1}, state=r2["state"])
    assert (_outs(r1, sh)[N + 2], _outs(r2, sh)[N + 2], _outs(r3, sh)[N + 2]) == (1, 1, 0)
    # 감시 HH/ — 블록 위 글 '191 barg' 가 설정값 · 선 글 '0~250 barg' 가 범위 · 17 mA = 203 > 191 → 1 · 16 mA = 187.5 → 0
    dm = _preset_doc("HH/")
    dm["wires"][1]["label"] = "0~250 barg"
    dm.update(D.clean(dm)); dm["id"] = "s1" * 6
    sh = DS.sheets_of([dm])[0]
    assert sh["blocks"]["b"]["param"]["sp"] == 191.0 and sh["rows"][0]["range"]["hi"] == 250.0
    assert _outs(_run(dm, {}, analog={"row:1": 17.0}), sh)[N + 2] == 1
    assert _outs(_run(dm, {}, analog={"row:1": 16.0}), sh)[N + 2] == 0
    # STEP — STEP IN 과 CRIT 가 1 이어야 STEP OUT
    ds = _preset_doc("STEP")
    sh = DS.sheets_of([ds])[0]
    assert {p["role"] for p in sh["ports"] if p["block"] == "b"} == {"step_in", "crit", "step_out"}
    assert _outs(_run(ds, {"row:1": 1}), sh)[N + 2] == 0
    assert _outs(_run(ds, {"row:1": 1, "row:2": 1}), sh)[N + 2] == 1


def test_analog_sum_block_adds_its_inputs():
    d = _preset_doc("Σ", n_in=2)
    for w in d["wires"][1:]:
        w["label"] = "0~100 %"
    d.update(D.clean(d)); d["id"] = "s1" * 6
    sh = DS.sheets_of([d])[0]
    assert sh["blocks"]["b"].get("aop") == "sum"
    r = _run(d, {}, analog={"row:1": 12.0, "row:2": 8.0})            # 50 % + 25 % = 75
    assert r["focus"]["analog"]["keys"]["block:b"]["eng"] == pytest.approx(75.0)


# ───────────────────────── 경계 ─────────────────────────

def test_draw_sim_never_renders_pdf_or_runs_the_analyser():
    src = (ROOT / "app" / "logic" / "draw_sim.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert "to_pdf" not in names and "pymupdf" not in src and "analyse(" not in src
    assert "simulate_bundle" in names                                   # 판정은 sim 이
    js = (ROOT / "app" / "static" / "logic_draw.js").read_text(encoding="utf-8")
    assert "/simulate" in js and "GATE_LOGIC" in js and "simPaint" in js
    assert "/export.pdf" not in js.split("function runSim")[1].split("function simStop")[0]
