"""L38 — 맞닿게 쌓아 그린 표시등 원 (1A5J · 19VA R·G·R·G·Y 세로 줄).

원을 사분원 넷으로 따로 그리고 위 원의 아래 끝이 아래 원의 위 끝이라, 끝으로 묶으면 한 무리가 되어 원이 하나도
서지 않았다 — 원 조각이 선으로 남아 표시등 줄의 입력선 전부와 옆 NOT 의 입·출력이 한 선이 됐다 (값이 안 멈춤).
"""
from __future__ import annotations

import pymupdf

from app.logic import geom
from tests.test_logic_l21_form import _arcs


def test_touching_stacked_circles_each_make_a_circle(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=200, height=200)
    r = 5.65
    for k in range(5):
        _arcs(page, 60, 40 + 2 * r * k, r)          # 맞닿음 — 위 원의 아래 끝 = 아래 원의 위 끝
    _arcs(page, 140, 40, r)                           # 홀로 선 원 — 예전처럼
    p = tmp_path / "stack.pdf"
    doc.save(p)
    pr = geom.read(pymupdf.open(p)[0], 1)
    cs = sorted((round(c.cx), round(c.cy)) for c, _ in pr.rings)
    assert cs == sorted([(60, round(40 + 2 * r * k)) for k in range(5)] + [(140, 40)])
    assert all(abs(c.r - r) < 0.1 for c, _ in pr.rings)
