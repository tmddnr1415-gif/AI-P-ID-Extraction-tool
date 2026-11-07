"""L70 — 홉 바로 뒤의 짧은 토막은 글자 획이 아니라 선이다 (19VA 0015 MTS 사진 · 연결 점검 '선 끝이 아무 데도 닿지 않습니다').

선이 다른 선을 반원(홉)으로 건너뛴 뒤 곧 연결점 · 블록 변에 닿으면 그 사이 토막이 글자 크기(0.45 행)보다 짧다.
짧은 토막은 '두 끝이 다 무언가에 닿을 때만' 선으로 쳤는데, 홉 쪽 끝은 호(글자 크기 곡선)에만 닿아 글자로 버려졌다 →
홉 건너편 끝이 매달리고(C1) · NOT 은 입력을 잃었다(C3).

합성 한 장 `XY_G-070`:
  A  3행 → 500 에서 내려가 6행 선을 홉으로 건너 → 3pt 토막 → 연결점 → R60 · R61
  B  12행 → 연결점(600) → 오른쪽으로 세로선(640)을 홉으로 건너 → 3pt 토막 → NOT 상자 → R62  (연결점에서 R63 갈래)
     세로선 640 은 1행 → 20행 높이 → R64
"""
from __future__ import annotations

import math

import pymupdf
import pytest

from app.logic import analyse, sim
from tests.test_logic_l23_generic import LX0, LX1, H, P, W, K, _line, _sheet, _text_box, ry


def _dot(page, x, y, r=1.56, n=12):
    """19VA 의 연결점 — 가운데에서 부채꼴 삼각형 여럿을 칠해 만든 원판."""
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        sh = page.new_shape()
        sh.draw_polyline([pymupdf.Point(x, y), pymupdf.Point(x + r * math.cos(a0), y + r * math.sin(a0)),
                          pymupdf.Point(x + r * math.cos(a1), y + r * math.sin(a1))])
        sh.finish(color=None, fill=K, width=0, closePath=True); sh.commit()


def _arc(page, a, c1, c2, b):
    sh = page.new_shape()
    sh.draw_bezier(pymupdf.Point(*a), pymupdf.Point(*c1), pymupdf.Point(*c2), pymupdf.Point(*b))
    sh.finish(color=K, width=0.72, closePath=False); sh.commit()


R = 1.4


def _draw(page):
    _sheet(page, "XY_G-070", {3: ("", "A"), 6: ("", "PASS 6"), 12: ("", "B"), 1: ("", "C")},
           {56: ("ROW 6", ""), 60: ("A ONE", ""), 61: ("A TWO", ""), 62: ("NOT B", ""), 63: ("B COPY", ""),
            64: ("C PASS", "")})
    # A — 세로선이 6행 선을 건너뛰고 3pt 아래 연결점
    y3, y6 = ry(3), ry(6)
    _line(page, (LX0, y6), (LX1, y6))
    _line(page, (LX0, y3), (500, y3), (500, y6 - R))
    _arc(page, (500, y6 - R), (500 + 1.9 * R, y6 - R), (500 + 1.9 * R, y6 + R), (500, y6 + R))
    yd = y6 + R + 3.0
    _line(page, (500, y6 + R), (500, yd))
    _dot(page, 500, yd)
    _line(page, (500, yd), (760, yd), (760, ry(60)), (LX1, ry(60)))
    _line(page, (500, yd), (500, ry(9)), (740, ry(9)), (740, ry(61)), (LX1, ry(61)))
    # B — 가로선이 세로선(640)을 건너뛰고 3pt 뒤 NOT 상자
    y12 = ry(12)
    _line(page, (LX0, ry(1)), (640, ry(1)), (640, ry(20)), (780, ry(20)), (780, ry(64)), (LX1, ry(64)))
    _line(page, (LX0, y12), (600, y12))
    _dot(page, 600, y12)
    _line(page, (600, y12), (640 - R, y12))
    _arc(page, (640 - R, y12), (640 - R, y12 - 1.9 * R), (640 + R, y12 - 1.9 * R), (640 + R, y12))
    _line(page, (640 + R, y12), (640 + R + 3.0, y12))
    out = _text_box(page, 640 + R + 3.0, y12, "NOT")
    _line(page, out, (800, out[1]), (800, ry(62)), (LX1, ry(62)))
    _line(page, (600, y12), (600, ry(16)), (720, ry(16)), (720, ry(63)), (LX1, ry(63)))


@pytest.fixture(scope="module")
def sheet(tmp_path_factory):
    doc = pymupdf.open()
    _draw(doc.new_page(width=W, height=H))
    p = tmp_path_factory.mktemp("l70") / "hopstub.pdf"
    doc.save(p)
    res = analyse.analyse(str(p))
    return next(s for s in res["sheets"] if s["sheet_no"] == "XY_G-070")


def _net(s, side, n):
    return next(r["net"] for r in s["rows"] if r["side"] == side and r["n"] == n)


def test_no_dangling_end_at_the_hops(sheet):
    codes = [f["code"] for f in sheet["findings"]]
    assert "C1_DANGLING" not in codes, [f for f in sheet["findings"] if f["code"] == "C1_DANGLING"]
    assert "C3_GATE_NO_INPUT" not in codes


def test_hop_then_short_stub_to_dot_stays_one_line(sheet):
    s = sheet
    a = _net(s, "L", 3)
    assert a == _net(s, "R", 60) == _net(s, "R", 61)
    assert _net(s, "L", 6) == _net(s, "R", 56) != a                  # 건너뛴 선과는 잇지 않는다


def test_hop_then_short_stub_feeds_the_not(sheet):
    s = sheet
    assert _net(s, "L", 12) == _net(s, "R", 63)
    assert _net(s, "L", 1) == _net(s, "R", 64) != _net(s, "L", 12)
    r = sim.simulate(s, {"row:12": 1})
    v = r["frames"][-1]["values"]
    assert v[_net(s, "R", 62)] == 0 and v[_net(s, "R", 63)] == 1
    r = sim.simulate(s, {"row:12": 0})
    assert r["frames"][-1]["values"][_net(s, "R", 62)] == 1
