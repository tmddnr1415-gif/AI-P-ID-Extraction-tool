"""L26 — MED 값 · 감시 블록(HHH · HH …) 설정값.

사용자 지시: MED Function Block 을 누르면 값을 지정하고, 오른쪽 HHH · HH 는 사람이 설정값을 넣는다 —
HH 는 넘지만 HHH 보다 낮으면 HH 만 활성 · HHH 보다 높으면 HH · HHH 모두 활성.
"""
from __future__ import annotations

import pymupdf
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.logic import analog, api, overrides, sim, store


def _P(b, n, d, at=(0, 0)):
    return {"block": b, "net": n, "dir": d, "role": "", "cell": 0, "at": list(at)}


def _blk(func, logic, label, bbox, param=None):
    return {"kind": "RECT", "func": func, "logic": logic, "label": label, "read": label, "score": 0,
            "bbox": list(bbox), "cells": [list(bbox)], "param": dict(param or {}), "group": "", "pointer": None,
            "roles": {}, "key": "|" + label}


def _sheet():
    """1A1Y HR_P007 꼴: 입력 10·13·16 → MED → HHH/(202.4) · HH/(191) → 출력 72 · 78 · MED 값은 출력 74 로 G002 입력 3."""
    R = {"lo": 0.0, "hi": 250.0, "unit": "barg"}
    rows = [{"n": 10, "side": "L", "net": "a", "desc": "PRESS A", "fm": "FIELD", "at": [120, 100], "range": R},
            {"n": 13, "side": "L", "net": "b", "desc": "PRESS B", "fm": "FIELD", "at": [120, 130], "range": R},
            {"n": 16, "side": "L", "net": "c", "desc": "PRESS C", "fm": "FIELD", "at": [120, 160], "range": R},
            {"n": 72, "side": "R", "net": "h3", "desc": "PRESS > H3", "to": ""},
            {"n": 78, "side": "R", "net": "h2", "desc": "PRESS > H2", "to": ""},
            {"n": 74, "side": "R", "net": "m", "desc": "PRESS", "to": "G002-3"}]
    blocks = {"MED": _blk("MEDIAN SELECTION", "unknown", "MED", (300, 120, 330, 140)),
              "H3": _blk("SIGNAL MONITOR", "source", "HHH/", (400, 100, 412, 110), {"sp": 202.4, "sp_unit": "barg"}),
              "H2": _blk("SIGNAL MONITOR", "source", "HH/", (400, 160, 412, 170), {"sp": 191, "sp_unit": "barg"})}
    ports = [_P("MED", "a", "in"), _P("MED", "b", "in"), _P("MED", "c", "in"), _P("MED", "m", "out"),
             _P("H3", "m", "in"), _P("H3", "h3", "out"), _P("H2", "m", "in"), _P("H2", "h2", "out")]
    nets = {n: {"segs": [], "dashed": False} for n in "abcmh3h2"}
    nets.update({"h3": {"segs": [], "dashed": False}, "h2": {"segs": [], "dashed": False}})
    s1 = {"page": 1, "sheet_no": "G001", "title": "T", "logic": [100, 0, 500, 800], "pitch": 10, "frame": None,
          "nets": nets, "order": {}, "blocks": blocks, "ports": ports, "rows": rows, "table": [dict(r) for r in rows],
          "dangling": [], "stray_arrows": [], "findings": []}
    rows2 = [{"n": 3, "side": "L", "net": "x", "desc": "PRESS", "fm": "G001-74"},
             {"n": 70, "side": "R", "net": "y", "desc": "LOW", "to": ""}]
    s2 = {"page": 2, "sheet_no": "G002", "title": "T", "logic": [100, 0, 500, 800], "pitch": 10, "frame": None,
          "nets": {"x": {"segs": [], "dashed": False}, "y": {"segs": [], "dashed": False}}, "order": {},
          "blocks": {"L1": _blk("SIGNAL MONITOR", "source", "/L", (300, 100, 312, 110), {"sp": 50})},
          "ports": [_P("L1", "x", "in"), _P("L1", "y", "out")], "rows": rows2, "table": [dict(r) for r in rows2],
          "dangling": [], "stray_arrows": [], "findings": []}
    return s1, s2


def _out(res, s, n):
    r = next(x for x in s["rows"] if x["n"] == n)
    return res["frames"][-1]["values"].get(r["net"])


def test_monitor_kind_reads_the_letters():
    assert analog.monitor_kind({"label": "HHH/", "func": "SIGNAL MONITOR", "logic": "source"}) == ("high", "HHH")
    assert analog.monitor_kind({"label": "/LL", "func": "SIGNAL MONITOR", "logic": "source"}) == ("low", "LL")
    assert analog.monitor_kind({"label": "AND", "func": "AND", "logic": "and"}) is None
    assert analog.compare("high", 191.0, 191.0) == 0, "같은 값은 넘은 것이 아니다"


def ma(v):
    return 4 + v / 250 * 16                                  # 0~250 barg ↔ 4~20 mA


@pytest.mark.parametrize("v,hh,hhh", [(150, 0, 0), (195, 1, 0), (210, 1, 1)])
def test_med_value_against_hh_and_hhh(v, hh, hhh):
    s1, _ = _sheet()
    r = sim.simulate(s1, {}, analog={"block:MED": ma(v)})
    assert (_out(r, s1, 78), _out(r, s1, 72)) == (hh, hhh)
    mons = {m["block"]: m for m in r["analog"]["monitors"]}
    assert mons["H2"]["value"] == pytest.approx(v) and mons["H3"]["sp"] == 202.4
    assert mons["H2"]["sp_ma"] == pytest.approx(ma(191), abs=1e-3)


def test_default_is_eight_milliamps():
    s1, _ = _sheet()
    r = sim.simulate(s1, {})
    k = r["analog"]["keys"]
    assert k["row:10"] == {"ma": 8.0, "eng": 62.5, "range": {"lo": 0.0, "hi": 250.0, "unit": "barg", "src": "drawing"},
                           "src": "default"}
    assert r["analog"]["blocks"]["MED"] == 62.5 and (_out(r, s1, 78), _out(r, s1, 72)) == (0, 0)
    s1["blocks"]["H2"]["param"]["sp_user"] = 50
    assert _out(sim.simulate(s1, {}), s1, 78) == 1, "기본 8 mA = 62.5 barg 가 설정값 50 을 넘는다"


def test_milliamps_outside_four_to_twenty_are_ignored():
    s1, _ = _sheet()
    r = sim.simulate(s1, {}, analog={"block:MED": 25})
    assert "block:MED" not in r["analog"]["keys"] or r["analog"]["keys"]["block:MED"]["src"] != "user"


def test_without_a_range_there_is_no_engineering_value():
    s1, _ = _sheet()
    for r_ in s1["rows"]:
        r_.pop("range", None)
    r = sim.simulate(s1, {}, analog={"row:10": 12})
    assert r["analog"]["keys"]["row:10"]["eng"] is None and _out(r, s1, 78) == 0
    s1["rows"][0]["range_user"] = {"lo": 0, "hi": 100, "unit": "%"}
    r = sim.simulate(s1, {}, analog={"row:10": 12})
    assert r["analog"]["keys"]["row:10"]["eng"] == 50.0, "사람이 적은 범위로 바꾼다"


def test_med_without_a_value_is_the_median_of_its_inputs():
    s1, _ = _sheet()
    r = sim.simulate(s1, {}, analog={"row:10": ma(100), "row:13": ma(196), "row:16": ma(240)})
    assert r["analog"]["blocks"]["MED"] == pytest.approx(196)
    assert (_out(r, s1, 78), _out(r, s1, 72)) == (1, 0)
    s1["rows"][2].pop("range")
    r = sim.simulate(s1, {}, analog={"row:10": ma(100), "row:13": ma(196)})
    assert "MED" not in r["analog"]["blocks"], "입력 하나라도 모르면 계산하지 않는다"


def test_no_value_keeps_the_old_behaviour():
    s1, _ = _sheet()
    for r_ in s1["rows"]:
        r_.pop("range", None)
    assert _out(sim.simulate(s1, {}), s1, 78) == 0
    assert _out(sim.simulate(s1, {"block:H2": 1}), s1, 78) == 1, "값이 없으면 예전처럼 1/0 을 직접 준다"
    s1, _ = _sheet()
    assert _out(sim.simulate(s1, {"block:H2": 0}, analog={"block:MED": 20}), s1, 78) == 0, "사람이 준 1/0 이 이긴다"


def test_user_setpoint_beats_the_drawing():
    s1, _ = _sheet()
    s1["blocks"]["H2"]["param"]["sp_user"] = 200
    r = sim.simulate(s1, {}, analog={"block:MED": ma(195)})
    assert _out(r, s1, 78) == 0


def test_analog_value_crosses_sheets():
    s1, s2 = _sheet()
    s1["rows"][-1]["ref"] = None
    s2["rows"][0]["ref"] = {"page": 1, "row": 74, "src_row": 74}
    out = sim.simulate_bundle([s1, s2], {}, None, 2, analog={1: {"block:MED": ma(40)}})
    assert out["analog_given"][2]["row:3"]["eng"] == pytest.approx(40)
    assert _out(out["focus"], s2, 70) == 1, "40 < /L 50 → 1"


def test_setpoint_printed_above_the_block_is_read(tmp_path):
    s1, _ = _sheet()
    for b in s1["blocks"].values():
        b["param"].pop("sp", None)
    doc = pymupdf.open()
    pg = doc.new_page(width=600, height=400)
    pg.insert_text((398, 97), "202.4 barg", fontsize=4)
    pg.insert_text((398, 157), "N2", fontsize=4)             # 수가 아니면 설정값이 아니다 (이름만 남긴다)
    pg.insert_text((130, 106), "0~250 barg", fontsize=4)     # 입력선 아래 범위
    pg.insert_text((130, 136), "4~20mA", fontsize=4)         # 신호 범위는 공학 범위가 아니다
    doc.save(tmp_path / "x.pdf")
    for r_ in s1["rows"]:
        r_.pop("range", None)
    s1["nets"]["a"]["segs"] = [[120, 100, 300, 100]]
    s1["nets"]["b"]["segs"] = [[120, 130, 300, 130]]
    assert analog.read_drawing(tmp_path / "x.pdf", [s1]) == 2
    assert s1["blocks"]["H3"]["param"]["sp"] == 202.4 and s1["blocks"]["H3"]["param"]["sp_unit"] == "barg"
    assert "sp" not in s1["blocks"]["H2"]["param"] and s1["blocks"]["H2"]["param"]["sp_label"] == "N2"
    assert s1["rows"][0]["range"]["lo"] == 0 and s1["rows"][0]["range"]["hi"] == 250 and s1["rows"][0]["range"]["unit"] == "barg"
    assert "range" not in s1["rows"][1]


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def test_setpoint_api_keeps_author_and_history(client):
    s1, s2 = _sheet()
    job, d = store.new_job("toy.pdf")
    store.write_result(d, {"pdf_pages": 2, "sheets": [s1, s2], "kinds": {}, "dictionary": {},
                           "legend": {"pages": [], "symbols": {}, "figures": []}, "seconds": 1, "note": ""})
    st = store.read_status(d)
    st.update({"state": "done", "sheets": 2})
    store.write_status(d, st)
    url = f"/logic/api/jobs/{job}/overrides/setpoint"
    assert client.post(url, json={"page": 1, "block": "H2", "sp": 200}).status_code == 400, "이름 없이는 저장 안 함"
    assert client.post(url, json={"page": 1, "block": "MED", "sp": 1, "author": "홍"}).status_code == 400
    assert client.post(url, json={"page": 1, "block": "H2", "sp": "x", "author": "홍"}).status_code == 400
    assert client.post(url, json={"page": 1, "block": "H2", "sp": 200, "author": "홍길동"}).status_code == 200
    sim_url = f"/logic/api/jobs/{job}/simulate"
    r = client.post(sim_url, json={"page": 1, "analog": {"1": {"block:MED": ma(195)}}}).json()
    assert {m["block"]: m["out"] for m in r["focus"]["analog"]["monitors"]} == {"H2": 0, "H3": 0}
    client.post(url, json={"page": 1, "block": "H2", "sp": None, "author": "홍길동"})
    r = client.post(sim_url, json={"page": 1, "analog": {"1": {"block:MED": ma(195)}}}).json()
    assert {m["block"]: m["out"] for m in r["focus"]["analog"]["monitors"]} == {"H2": 1, "H3": 0}
    rurl = f"/logic/api/jobs/{job}/overrides/range"
    assert client.post(rurl, json={"page": 1, "key": "row:10", "lo": 0, "hi": 0, "author": "홍"}).status_code == 400
    assert client.post(rurl, json={"page": 1, "key": "row:99", "lo": 0, "hi": 1, "author": "홍"}).status_code == 400
    assert client.post(rurl, json={"page": 1, "key": "row:10", "lo": 0, "hi": 500, "unit": "barg",
                                   "author": "홍길동"}).status_code == 200
    r = client.post(sim_url, json={"page": 1}).json()
    assert r["focus"]["analog"]["keys"]["row:10"]["eng"] == 125.0, "8 mA × 0~500"
    client.post(rurl, json={"page": 1, "key": "row:10", "lo": None, "author": "홍길동"})
    ov = overrides.load(d)
    assert [h["kind"] for h in ov["history"]] == ["setpoint", "setpoint", "range", "range"] and not ov["setpoints"]
    assert (d / "result.json").read_text(encoding="utf-8").count("sp_user") == 0, "분석 결과 파일은 그대로"
