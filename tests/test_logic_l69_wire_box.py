"""L69 — 배선이 만든 네모는 블록이 아니다 (19VA 0017 MIT · 사용자 사진 '선 연결이 안 된다').

게이트 입력 막대에 들어가는 신호선 둘 + 그 둘 사이를 잇는 세로선(위 끝이 연결점)이 막대와 함께 닫힌 네모가 되어
'판정 못 한 블록(입력)' 으로 섰고, 그 안을 지나는 선과 건너뛰기(홉) 호가 글자로 먹혀 선이 끊겼다.
상자의 변에는 연결점이 없다 — 연결점이 변 위에 있으면 그 네모는 배선이다.

합성 한 장 `XY_G-069`:
  2행 → 연결점(540) → OR 막대 (600)  ·  연결점에서 세로선이 7행 높이를 홉으로 건너 9행 높이까지 → R60
  7행 → 535 에서 꺾여 5행 높이로 올라가 → OR 막대
  1행 → 가운데(570)로 내려와 2행 · 5행 높이를 홉으로 지나간다 → R62
"""
from __future__ import annotations

import pymupdf
import pytest

from app.logic import analyse, sim
from tests.test_logic_l23_generic import LX0, LX1, H, P, W, K, _line, _sheet, _text_box, ry


def _dot(page, x, y, r=1.56, n=12):
    """19VA 의 연결점 — 가운데에서 부채꼴 삼각형 여럿을 칠해 만든 원판."""
    import math
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        sh = page.new_shape()
        sh.draw_polyline([pymupdf.Point(x, y), pymupdf.Point(x + r * math.cos(a0), y + r * math.sin(a0)),
                          pymupdf.Point(x + r * math.cos(a1), y + r * math.sin(a1))])
        sh.finish(color=None, fill=K, width=0, closePath=True); sh.commit()


def _hop_v(page, x, y0, y1, ycross, r=1.4):
    """세로선이 ycross 높이의 가로선을 반원으로 건너뛴다."""
    _line(page, (x, y0), (x, ycross - r))
    sh = page.new_shape()
    sh.draw_bezier(pymupdf.Point(x, ycross - r), pymupdf.Point(x + 1.9 * r, ycross - r),
                   pymupdf.Point(x + 1.9 * r, ycross + r), pymupdf.Point(x, ycross + r))
    sh.finish(color=K, width=0.72, closePath=False); sh.commit()
    _line(page, (x, ycross + r), (x, y1))


def _draw(page):
    _sheet(page, "XY_G-069", {2: ("", "A"), 7: ("", "B"), 1: ("", "C")},
           {55: ("OR AB", ""), 60: ("A COPY", ""), 62: ("C PASS", "")})
    y2, y5, y7, y9 = ry(2), ry(5), ry(7), ry(9)
    yo = (y2 + y5) / 2
    out = _text_box(page, 600, yo, "OR", bar=True)
    _line(page, (600, y2 - 4), (600, y5 + 4))                    # 막대가 두 입력을 덮게
    _line(page, (LX0, y2), (538.5, y2))
    _dot(page, 540, y2)
    _line(page, (541.5, y2), (600, y2))
    _hop_v(page, 540, y2 + 1.56, y9, y5)
    _line(page, (540, y9), (800, y9), (800, ry(60)), (LX1, ry(60)))
    _line(page, (LX0, y7), (535, y7), (535, y5), (600, y5))
    _line(page, (LX0, ry(1)), (570, ry(1)))
    _hop_v(page, 570, ry(1), y5 - 3, y2)
    _hop_v(page, 570, y5 - 3, ry(12), y5)
    _line(page, (570, ry(12)), (780, ry(12)), (780, ry(62)), (LX1, ry(62)))
    _line(page, out, (820, yo), (820, ry(55)), (LX1, ry(55)))


@pytest.fixture(scope="module")
def sheet(tmp_path_factory):
    doc = pymupdf.open()
    _draw(doc.new_page(width=W, height=H))
    p = tmp_path_factory.mktemp("l69") / "wirebox.pdf"
    doc.save(p)
    res = analyse.analyse(str(p))
    return next(s for s in res["sheets"] if s["sheet_no"] == "XY_G-069")


def _net(s, side, n):
    return next(r["net"] for r in s["rows"] if r["side"] == side and r["n"] == n)


def test_wiring_loop_with_a_junction_dot_is_not_a_block(sheet):
    s = sheet
    # 예전에는 배선 네모가 OR 상자와 한 블록으로 묶여 OR 이 535~614 로 부풀었다
    boxes = [b for b in s["blocks"].values() if b["bbox"][0] < 590 and b["bbox"][2] > 560]
    assert not boxes, boxes
    orb = next(b for b in s["blocks"].values() if b["logic"] == "or")
    assert orb["bbox"][2] - orb["bbox"][0] < 20


def test_wires_inside_the_loop_stay_connected(sheet):
    s = sheet
    orb = next(k for k, b in s["blocks"].items() if b["logic"] == "or")
    ins, *_ = sim._index(s)
    assert {n for n, _, _ in ins[orb]} == {_net(s, "L", 2), _net(s, "L", 7)}
    assert _net(s, "L", 2) == _net(s, "R", 60)                  # 연결점에서 내려간 선은 2행 신호
    assert _net(s, "L", 1) == _net(s, "R", 62)                  # 홉으로 지나간 선은 끊기지 않는다
    assert len({_net(s, "L", 2), _net(s, "L", 7), _net(s, "L", 1)}) == 3
    r = sim.simulate(s, {"row:7": 1})
    assert r["frames"][-1]["values"][_net(s, "R", 55)] == 1
    r = sim.simulate(s, {"row:1": 1})
    v = r["frames"][-1]["values"]
    assert v[_net(s, "R", 62)] == 1 and v[_net(s, "R", 55)] == 0
