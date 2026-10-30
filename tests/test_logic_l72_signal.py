"""L72 — 신호 처리 시뮬레이션 페이지: 연산자마다 입력 · 설정값을 넣고 계산 과정 · 출력 · 시간 응답을 본다.

사용자 지시: 'Logic 작성' 처럼 사용자가 직접 값을 넣어 보는 페이지 · symbol 종류별 탭 · 숫자 입력 + 슬라이더 ·
파라미터(게인 · 바이어스 · 시정수 · 상하한) · 계산 과정과 출력을 즉시 · 시간 블록(Lead/Lag · Rate limit …)은 시간 그래프.
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.logic import aop_trace, aops, api

ROOT = Path(__file__).resolve().parents[1]
PAGE_JS = (ROOT / "app/static/logic_signal.js").read_text(encoding="utf-8")
LOGIC_HTML = (ROOT / "app/static/logic.html").read_text(encoding="utf-8")


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def test_page_and_meta(client):
    assert client.get("/logic/signal").status_code == 200
    m = client.get("/logic/api/aopsim").json()
    assert {"sum", "div", "sqrt", "max", "min", "mean", "fx", "hilim", "lolim", "lag", "leadlag", "velim"} <= set(m["ops"])
    assert {"lag", "leadlag", "velim", "integral", "deriv"} == set(m["time_ops"])
    assert 'href="/logic/signal"' in LOGIC_HTML, "LOGIC 머리에 메뉴"


def test_page_uses_the_same_calculation_as_the_drawing(client):
    r = client.post("/logic/api/aopsim", json={"op": "gain", "inputs": [{"value": 15.5}], "params": {"k": 0.8}}).json()
    assert r["out"] == pytest.approx(12.4) and r["trace"]["sub"] == "0.8 × 15.5"
    b = {"label": "", "param": {"a_user": {"k": 0.8}}}
    assert r["out"] == aops.compute("gain", b, [("n0", None)], {"n0": 15.5})[0]
    r = client.post("/logic/api/aopsim", json={"op": "div", "inputs": [{"pin": "IN1", "value": 6}, {"pin": "IN2", "value": 0}]}).json()
    assert r["out"] is None and "0 으로" in r["why"]
    r = client.post("/logic/api/aopsim", json={"op": "transfer", "inputs": [{"pin": "IN1", "value": 1}, {"pin": "IN2", "value": 2}], "cond": 0}).json()
    assert r["out"] == 2 and r["trace"]["sub"] == "C = 0 → IN2 = 2"
    r = client.post("/logic/api/aopsim", json={"op": "dev", "inputs": [{"value": 10}, {"value": 2}], "params": {"d": 3}}).json()
    assert r["dig"] == 1
    r = client.post("/logic/api/aopsim", json={"op": "count", "inputs": [{"value": 1}, {"value": 0}, {"value": 1}]}).json()
    assert r["out"] == 2
    assert client.post("/logic/api/aopsim", json={"op": "nope"}).status_code == 400
    assert client.post("/logic/api/aopsim", json={"op": "sum", "inputs": [{"value": 1}] * 17}).status_code == 400


def _at(r, t):
    return r["y"][min(range(len(r["t"])), key=lambda i: abs(r["t"][i] - t))]


def test_time_blocks_follow_their_textbook_response(client):
    step = {"kind": "step", "x0": 0, "x1": 100, "t1": 5}
    r = client.post("/logic/api/aopsim/timeline", json={"op": "lag", "params": {"t": 5}, "input": step, "T": 40}).json()
    assert _at(r, 10) == pytest.approx(100 * (1 - math.exp(-1)), abs=0.5), "1 시정수 뒤 63 %"
    assert r["y"][0] == 0 and r["y"][-1] == pytest.approx(100, abs=0.5)
    r = aop_trace.timeline("leadlag", {"tlead": 10, "tlag": 5}, step, T=40)
    assert max(r["y"]) == pytest.approx(200, rel=0.02), "계단 순간 k·T₁/T₂ 배"
    r = aop_trace.timeline("velim", {"r": 2}, step, T=30)
    assert _at(r, 15) == pytest.approx(20, abs=0.1) and r["y"][-1] == pytest.approx(50, abs=0.1), "초당 2 씩만"
    r = aop_trace.timeline("integral", {"t": 10}, {"kind": "step", "x0": 0, "x1": 10, "t1": 5}, T=30)
    assert r["y"][-1] == pytest.approx(25, abs=0.1)
    r = aop_trace.timeline("deriv", {"t": 2}, {"kind": "ramp", "x0": 0, "x1": 100, "t1": 5}, T=30)
    assert _at(r, 20) == pytest.approx(8, abs=0.1), "Td × 기울기"
    assert len(r["t"]) <= aop_trace.MAX_PTS + 1
    assert client.post("/logic/api/aopsim/timeline", json={"op": "sum"}).status_code == 400


def test_page_wiring():
    assert "/logic/api/aopsim/timeline" in PAGE_JS and 'type="range"' in PAGE_JS, "숫자 + 슬라이더 · 시간 그래프"
    assert "function loadUrl(" in PAGE_JS and 'q.get("s")' in PAGE_JS, "도면에서 지금 값을 채워 연다"
    assert "my !== seq" in PAGE_JS, "늦게 온 계산은 버린다 (슬라이더를 끌어도 마지막 값만)"


def test_operator_panel_opens_the_page_with_the_current_values():
    """L73 — 도면 연산자 판의 '시뮬레이션에서 열기': 지금 입력 값 · 계수 · 어디서 · 설정값 · 전환 조건을 ?s= 로 채워 새 창."""
    js = (ROOT / "app/static/logic.js").read_text(encoding="utf-8")
    assert "function opSimUrl(" in js and 'data-a="sim"' in js and 'window.open(opSimUrl(bid, d), "_blank")' in js
    assert '"/logic/signal?s=" + encodeURIComponent(JSON.stringify(o))' in js
    assert 'for (const k of ["coef", "order", "out", "op"]) delete pr[k];' in js, "출력값 고정은 빼고 · 계수와 순서는 입력에 싣는다"
    page_ops = set(js.split("const SIM_PAGE_OPS = new Set([")[1].split("])")[0].replace('"', "").replace("\n", "").replace(" ", "").split(","))
    meta_ops = set(aops.vocab()["ops"]) | set(aops.vocab()["digital_ops"])
    assert page_ops <= meta_ops and {"pid", "ft", "counter"}.isdisjoint(page_ops), "페이지에 탭이 있는 연산만"
    for op in page_ops:
        assert f'"{op}"' in PAGE_JS, f"페이지 탭에 {op}"
