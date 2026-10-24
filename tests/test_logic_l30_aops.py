"""L30 — 아날로그 연산자(∑ · △ · ÷ · × · A · T · 수식 · PID · DEV …) 식별 · 계산 · 사람이 넣는 값 · 메모.

사용자 지시: 아날로그 연산자 식별과 기능이 되도록 · 값이나 설정이 필요하면 연산자를 눌러 넣을 수 있게 ·
메모 기능(P&ID 분석툴 참조) · 모든 기능은 가볍고 빠르게.
"""
from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.logic import analog, aops, api, memo, overrides, sim, store

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "app/static/logic.js").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _own_data(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear()
    yield
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear()


def _P(b, n, d, at=(0, 0), side=""):
    return {"block": b, "net": n, "dir": d, "role": "", "cell": 0, "at": list(at), "side": side}


def _blk(func, logic, label, bbox, param=None):
    return {"kind": "RECT", "func": func, "logic": logic, "label": label, "read": label, "score": 0,
            "bbox": list(bbox), "cells": [list(bbox)], "param": dict(param or {}), "group": "", "pointer": None,
            "roles": {}, "key": "|" + label}


def _sheet():
    """입력 10(0~100 %) · 상수 A(5) → ∑ (IN1 + IN2 × −1) → 감시 H/(40) → 출력 72.
    △(+ 입력 10 · − 상수) · ÷(IN1 / IN2) · T(Flag 행 20 이 1 이면 IN1) · DEV(D 3) → 출력 80 · 표시등 G."""
    R = {"lo": 0.0, "hi": 100.0, "unit": "%"}
    rows = [{"n": 10, "side": "L", "net": "a", "desc": "FLOW A", "fm": "FIELD", "at": [120, 100], "range": R},
            {"n": 12, "side": "L", "net": "b", "desc": "FLOW B", "fm": "FIELD", "at": [120, 140], "range": R},
            {"n": 20, "side": "L", "net": "f", "desc": "SELECT", "fm": "FIELD", "at": [120, 300]},
            {"n": 72, "side": "R", "net": "h", "desc": "HIGH", "to": ""},
            {"n": 80, "side": "R", "net": "dv", "desc": "DEVIATION", "to": ""}]
    blocks = {
        "A1": _blk("UNKNOWN", "unknown", "A", (200, 160, 210, 170), {"a_const": {"v": 5.0, "unit": "%", "text": "A : 5%"}}),
        "S1": _blk("SUMMING", "unknown", "∑", (300, 100, 320, 120),
                   {"pins": {"a": {"name": "IN1"}, "k": {"name": "IN2", "coef": -1.0}}}),
        "H1": _blk("SIGNAL MONITOR", "source", "H/", (400, 100, 412, 110), {"sp": 40, "sp_unit": "%"}),
        "D1": _blk("UNKNOWN", "unknown", "", (300, 200, 320, 220),
                   {"aop_fig": {"op": "diff", "name": "DIFFERENCE", "score": 1.0},
                    "pins": {"a": {"name": "+", "coef": 1.0}, "k": {"name": "-", "coef": -1.0}}}),
        "V1": _blk("UNKNOWN", "unknown", "÷ IN1 / IN2", (300, 250, 320, 270),
                   {"pins": {"a": {"name": "IN1"}, "b": {"name": "IN2"}}}),
        "T1": _blk("UNKNOWN", "unknown", "T", (300, 300, 320, 320),
                   {"pins": {"a": {"name": "IN1"}, "b": {"name": "IN2"}, "f": {"name": "FLAG"}}}),
        "E1": _blk("UNKNOWN", "unknown", "DEV", (300, 350, 320, 370), {"a_drawing": {"d": {"v": 3.0, "unit": "", "text": "D : 3"}}}),
        "G1": _blk("UNKNOWN", "unknown", "G", (450, 360, 456, 366)),
    }
    ports = [_P("A1", "k", "out"),
             _P("S1", "a", "in"), _P("S1", "k", "in"), _P("S1", "s", "out"),
             _P("H1", "s", "in"), _P("H1", "h", "out"),
             _P("D1", "a", "in"), _P("D1", "k", "in"), _P("D1", "d", "out"),
             _P("V1", "a", "in"), _P("V1", "b", "in"), _P("V1", "v", "out"),
             _P("T1", "a", "in"), _P("T1", "b", "in"), _P("T1", "f", "in"), _P("T1", "t", "out"),
             _P("E1", "a", "in"), _P("E1", "b", "in"), _P("E1", "dv", "out"),
             _P("G1", "dv", "in")]
    nets = {n: {"segs": [], "dashed": False} for n in ("a", "b", "f", "k", "s", "h", "d", "v", "t", "dv")}
    s = {"page": 1, "sheet_no": "G001", "title": "T", "logic": [100, 0, 500, 800], "pitch": 10, "frame": None,
         "nets": nets, "order": {}, "blocks": blocks, "ports": ports, "rows": rows, "table": [dict(r) for r in rows],
         "dangling": [], "stray_arrows": [], "findings": []}
    return s


def ma(v):
    return 4 + v / 100 * 16


def _out(res, s, n):
    r = next(x for x in s["rows"] if x["n"] == n)
    return res["frames"][-1]["values"].get(r["net"])


def test_operators_are_identified_from_the_legend_symbol_and_name():
    s = _sheet()
    changed = aops.identify([s])
    B = s["blocks"]
    assert changed == {1}
    assert (B["A1"]["aop"], B["A1"]["func"]) == ("const", "ANALOG SIGNAL GENERATOR")
    assert B["S1"]["aop"] == "sum" and B["S1"]["func"] == "SUMMING", "이름만 붙은 블록에도 연산 이름"
    assert B["D1"]["aop"] == "diff", "글자 없이 그림(△)만 든 상자"
    assert B["V1"]["aop"] == "div" and B["T1"]["aop"] == "transfer" and B["E1"]["aop"] == "dev"
    assert (B["G1"]["func"], B["G1"]["logic"]) == ("INDICATION", "sink"), "표시등 — 받기만"
    assert "aop" not in B["H1"], "감시 블록은 연산자가 아니다"


def test_a_symbol_without_the_right_shape_is_not_guessed():
    s = _sheet()
    s["ports"] = [p for p in s["ports"] if p["block"] != "A1"]       # 상수인데 나가는 선이 없다
    s["ports"].append(_P("A1", "k", "in"))
    s["ports"].append(_P("A1", "z", "in"))
    aops.identify([s])
    assert s["blocks"]["A1"]["func"] == "UNKNOWN" and "aop" not in s["blocks"]["A1"]


@pytest.mark.parametrize("v,h", [(30, 0), (50, 1)])
def test_sum_with_the_printed_coefficient_feeds_the_monitor(v, h):
    s = _sheet()
    aops.identify([s])
    r = sim.simulate(s, {}, analog={"row:10": ma(v)})
    ops = r["analog"]["ops"]
    assert ops["S1"]["out"] == pytest.approx(v - 5), "IN1 + IN2 × (−1) — 도면이 IN2 : -1 이라고 적었다"
    assert _out(r, s, 72) == h, "∑ = v − 5 가 H/ 40 을 넘으면 1"
    assert ops["D1"]["out"] == pytest.approx(v - 5), "△ = (+) − (−)"
    assert ops["A1"]["out"] == 5.0


def test_divide_follows_the_printed_in1_over_in2_and_zero_is_refused():
    s = _sheet()
    aops.identify([s])
    r = sim.simulate(s, {}, analog={"row:10": ma(60), "row:12": ma(20)})
    assert r["analog"]["ops"]["V1"]["out"] == pytest.approx(3.0)
    r = sim.simulate(s, {}, analog={"row:10": ma(60), "row:12": 4})
    assert r["analog"]["ops"]["V1"]["out"] is None and "0 으로" in r["analog"]["ops"]["V1"]["why"]


def test_transfer_follows_the_digital_flag_and_deviation_gives_one_or_zero():
    s = _sheet()
    aops.identify([s])
    r0 = sim.simulate(s, {}, analog={"row:10": ma(60), "row:12": ma(20)})
    assert r0["analog"]["ops"]["T1"]["out"] == pytest.approx(20.0), "Flag 0 → IN2"
    r1 = sim.simulate(s, {"row:20": 1}, analog={"row:10": ma(60), "row:12": ma(20)})
    assert r1["analog"]["ops"]["T1"]["out"] == pytest.approx(60.0), "Flag 1 → IN1"
    assert _out(r1, s, 80) == 1, "|60 − 20| > D 3 → 1"
    r2 = sim.simulate(s, {}, analog={"row:10": ma(21), "row:12": ma(20)})
    assert _out(r2, s, 80) == 0, "|21 − 20| ≤ 3 → 0"


def test_user_values_win_and_a_user_net_value_is_not_overwritten():
    s = _sheet()
    aops.identify([s])
    s["blocks"]["S1"]["param"]["a_user"] = {"coef": {"k": 1.0}}
    r = sim.simulate(s, {}, analog={"row:10": ma(30)})
    assert r["analog"]["ops"]["S1"]["out"] == pytest.approx(35.0), "사람이 계수를 +1 로"
    r = sim.simulate(s, {}, analog={"row:10": ma(30), "net:s": {"eng": 77}})
    assert r["analog"]["nets"]["s"] == 77 and _out(r, s, 72) == 1, "그 선에 넣은 값이 연산자 출력을 이긴다"


def test_formula_is_evaluated_safely():
    assert aops.eval_formula("((10^(2*A-28))/2)+A", {"A": 14}) == pytest.approx(14.5)
    assert aops.formula_vars("F*E/9/0.96/10") == ["E", "F"]
    with pytest.raises(Exception):
        aops.eval_formula("__import__('os').system('x')", {})
    b = _blk("UNKNOWN", "unknown", "OUT = A*2+1", (0, 0, 10, 10))
    assert aops.op_of(b) == "formula"
    assert aops.compute("formula", b, [("n", {"name": "A"})], {"n": 3.0}) == (7.0, "")


def test_pins_and_constants_are_read_from_the_drawing(tmp_path):
    """입력 선 끝 이름(IN1 · IN2 : -1)은 가까운 짝부터 한 단자에 하나 · 옆 'A : 5%' 는 상수."""
    s = _sheet()
    s["blocks"]["S1"]["param"] = {}
    s["blocks"]["A1"]["param"] = {}
    for p in s["ports"]:
        if p["block"] == "S1":
            p["at"], p["side"] = {"a": ([300, 105], "L"), "k": ([310, 120], "B"), "s": ([320, 110], "R")}[p["net"]]
    doc = pymupdf.open()
    pg = doc.new_page(width=600, height=400)
    pg.insert_text((288, 104), "IN1", fontsize=4)
    pg.insert_text((312, 128), "IN2 : -1", fontsize=4)
    pg.insert_text((212, 162), "A : 5%", fontsize=4)
    doc.save(tmp_path / "x.pdf")
    aops.identify([s])
    analog.read_drawing(tmp_path / "x.pdf", [s])
    pins = s["blocks"]["S1"]["param"]["pins"]
    assert pins["a"]["name"] == "IN1" and pins["k"] == {"name": "IN2", "coef": -1.0}
    assert s["blocks"]["A1"]["param"]["a_const"] == {"v": 5.0, "unit": "%", "text": "A : 5%"}


def test_figure_match_prefers_the_single_glyph_operator():
    tri = [[x, 15 - abs(7 - x) * 2] for x in range(16)] + [[x, 15] for x in range(16)]
    figs = [{"fig": tri, "name": "ABSOLUTE VALUE"}, {"fig": tri, "name": "DIFFERENCE"}, {"fig": [[0, 0], [15, 15]], "name": "SUMMING"}]
    from app.logic.blocks import _stretch
    m = aops._best_fig(_stretch(tri), [{**f, "fig": _stretch(f["fig"])} for f in figs])
    assert m["op"] == "diff", "같은 그림을 두 이름이 쓰면 그 그림 한 글자가 기호인 연산"


def test_aparam_cleaning_rejects_bad_values():
    assert overrides.clean_aparams({"k": "2", "coef": {"a": "-1"}, "table": [[0, 0], [100, 50]], "c": 1, "op": "gain"}) == \
        {"k": 2.0, "c": 1, "coef": {"a": -1.0}, "table": [[0.0, 0.0], [100.0, 50.0]], "op": "gain"}
    for bad in ({"k": "x"}, {"c": 2}, {"table": [[1, 2]]}, {"op": "nope"}, {"out": 1e13}):
        with pytest.raises(ValueError):
            overrides.clean_aparams(bad)


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def _job(s):
    job, d = store.new_job("toy.pdf")
    doc = pymupdf.open()
    doc.new_page(width=600, height=400)
    doc.save(d / "source.pdf")
    store.write_result(d, {"pdf_pages": 1, "sheets": [s], "kinds": {}, "dictionary": {},
                           "legend": {"pages": [], "symbols": {}, "figures": []}, "seconds": 1, "note": ""})
    st = store.read_status(d)
    st.update({"state": "done", "sheets": 1})
    store.write_status(d, st)
    return job, d


def test_operator_panel_api_saves_values_with_author(client):
    s = _sheet()
    s["blocks"]["S1"]["label"] = s["blocks"]["S1"]["read"] = "K"        # 비례 — K 가 도면에 없다
    s["blocks"]["S1"]["func"] = "UNKNOWN"
    job, d = _job(s)
    one = client.post(f"/logic/api/jobs/{job}/sheet/1/aop", json={"block": "S1", "analog": {"row:10": ma(40)}}).json()
    assert one["op"] == "gain" and one["out"] is None and "K" in one["why"]
    url = f"/logic/api/jobs/{job}/overrides/aparam"
    assert client.post(url, json={"page": 1, "block": "S1", "params": {"k": 2}}).status_code == 400, "이름 없이는 저장 안 함"
    assert client.post(url, json={"page": 1, "block": "H1", "params": {"k": 2}, "author": "홍"}).status_code == 400
    assert client.post(url, json={"page": 1, "block": "S1", "params": {"k": 2}, "author": "홍길동"}).status_code == 200
    r = client.post(f"/logic/api/jobs/{job}/simulate", json={"page": 1, "analog": {"1": {"row:10": ma(40)}}}).json()
    assert r["focus"]["analog"]["ops"]["S1"]["out"] == pytest.approx(80.0)
    # 판정 못 한 상자를 연산자로 정한다
    assert client.post(url, json={"page": 1, "block": "G1", "params": {"op": "const", "value": 7}, "author": "홍길동"}).status_code == 200
    sh = client.get(f"/logic/api/jobs/{job}/sheet/1").json()
    assert sh["blocks"]["G1"]["aop"] == "const" and sh["blocks"]["G1"]["param"]["a_user"]["by"] == "홍길동"
    client.post(url, json={"page": 1, "block": "S1", "params": None, "author": "홍길동"})
    ov = overrides.load(d)
    assert [h["kind"] for h in ov["history"]] == ["aparam", "aparam", "aparam"] and "S1" not in ov["aparams"].get("1", {})
    assert "a_user" not in (d / "result.json").read_text(encoding="utf-8"), "분석 결과 파일은 그대로"
    voc = client.get("/logic/api/aops").json()
    assert voc["ops"]["sum"]["ko"].startswith("합") and voc["needs"]["gain"][0][0] == "k"


def test_memo_on_a_block_and_area_and_other_analyses_of_the_project(client):
    s = _sheet()
    job, d = _job(s)
    job2, d2 = _job(_sheet())
    for dd in (d, d2):
        st = store.read_status(dd)
        st["project"] = "P1"
        store.write_status(dd, st)
    r = client.post(f"/logic/api/jobs/{job}/memo", json={"page": 1, "sheet_no": "G001", "text": "Σ 계수 확인", "author": "홍",
                                                        "rect": [310, 90, 300, 130], "block": "S1"}).json()
    assert r["rect"] == [300.0, 90.0, 310.0, 130.0] and r["at"] == [310.0, 90.0] and r["block"] == "S1"
    assert client.post(f"/logic/api/jobs/{job}/memo", json={"page": 1, "text": "x", "author": "홍", "rect": [1, 2]}).status_code == 400
    other = client.get(f"/logic/api/jobs/{job2}/memo").json()
    assert other["items"] == [] and [m["text"] for m in other["others"]] == ["Σ 계수 확인"]
    assert other["others"][0]["from_job"] == job, "같은 프로젝트 다른 분석의 같은 시트 메모 (읽기만)"


def test_screen_wires_the_operator_panel_and_pin_form():
    assert "function opMenu(" in JS and "else if (b.aop) opMenu(bid, e);" in JS
    assert "function pinForm(" in JS and "날짜" in JS and "작성자" in JS and "메모 내용" in JS
    assert "function drawOpMarks(" in JS and "drawOpMarks(g, fs)" in JS
    assert "/overrides/aparam" in JS and "/sheet/${L.page}/aop" in JS
    assert "L.analogResPage === L.page" in JS, "다른 장의 시뮬레이션 결과를 이 장에 쓰지 않는다"


def test_bundle_reuses_per_sheet_analog_work():
    """같은 장에 같은 값이면 지난 계산 — 연산자가 많은 묶음에서도 값 하나 바꾸는 데 장마다 다시 세지 않는다."""
    s = _sheet()
    aops.identify([s])
    cache = {}
    a = sim.simulate_bundle([s], {}, None, 1, analog={1: {"row:10": ma(50)}}, cache=cache)
    n1 = len(cache.get("an_nets", {}))
    b = sim.simulate_bundle([s], {}, None, 1, analog={1: {"row:10": ma(50)}}, cache=cache)
    assert a["focus"]["analog"]["ops"]["S1"]["out"] == b["focus"]["analog"]["ops"]["S1"]["out"]
    assert len(cache.get("an_nets", {})) == n1
