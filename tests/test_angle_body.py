"""54회차 — 앵글 밸브는 반쪽 `CHECK` 가 없어도 몸체다 (9차 피드백 [A]).

18회차가 `ANGLE` 을 넣을 때 `_fold_angle_bodies` 는 *반쪽을 접는* 자리였다.
그래서 두 삼각형이 각각 배관 끝막대를 갖는 문서(AL NOUF1)에서만 몸체가 섰고,
끝막대 없이 배관 모서리에 바로 앉은 문서에서는 **범례가 정의한 모양을 찾아
놓고 버렸다** — TC2 `_angle_figures` 6개 중 4개가 그랬고, 그중 p10 의 둘이
9차 피드백이 지목한 `XV` 다.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "engine"))

import detect_valves as dv    # noqa: E402
import pidcache               # noqa: E402


def _angle(page, ax, ay, r):
    """범례 p2 `ANGLE` — 꼭짓점을 맞댄 두 중공 삼각형을 **한 객체**로 그린다.

    실측 (TC2 legend p2 ↔ p10 본문): 한 객체 · 선 6개 · `fill=None` ·
    꼭짓점에 끝점 네 개 · 7.4 x 7.5pt.
    """
    pts = [
        (ax, ay), (ax + r, ay - r / 2),          # 가로 삼각형
        (ax + r, ay - r / 2), (ax + r, ay + r / 2),
        (ax + r, ay + r / 2), (ax, ay),
        (ax, ay), (ax - r / 2, ay + r),          # 세로 삼각형
        (ax - r / 2, ay + r), (ax + r / 2, ay + r),
        (ax + r / 2, ay + r), (ax, ay),
    ]
    sh = page.new_shape()
    for i in range(0, len(pts), 2):
        sh.draw_line(pymupdf.Point(*pts[i]), pymupdf.Point(*pts[i + 1]))
    sh.finish(width=0.3, fill=None, closePath=False)
    sh.commit()


def _page(tmp_path, draw, rotate=0):
    doc = pymupdf.open()
    page = doc.new_page(width=900, height=700)
    draw(page)
    if rotate:
        page.set_rotation(rotate)
    path = tmp_path / "a.pdf"
    doc.save(path)
    doc.close()
    _d, pages = pidcache.load_pages(path)
    return pages[0]


def test_an_angle_figure_with_no_check_halves_is_still_a_body(tmp_path):
    pc = _page(tmp_path, lambda pg: _angle(pg, 300, 300, 8))
    figs = dv._angle_figures(pc, dv.LAYOUT)
    assert len(figs) == 1, figs
    bodies = dv._fold_angle_bodies(pc, [], dv.LAYOUT)
    assert [b.kind for b in bodies] == ["ANGLE"]
    assert bodies[0].evidence["halves"] == 0        # 접을 반쪽이 없었다는 사실이 남는다


def test_the_apex_is_in_display_coordinates(tmp_path):
    """회전 장에서 꼭짓점과 사각형이 **같은 좌표계**여야 한다 (41회차 [C] 와 같은 덫).

    `attach_actuators` 는 앵글의 어긋남을 rect 중심이 아니라 꼭짓점에서 잰다.
    획은 회전 **전** 좌표로 오고 `bbox` 는 표시 좌표라, 그대로 두면 회전 장에서
    두 값이 서로 다른 평면에 있게 된다.
    """
    pc = _page(tmp_path, lambda pg: _angle(pg, 300, 300, 8), rotate=270)
    figs = dv._angle_figures(pc, dv.LAYOUT)
    assert len(figs) == 1, figs
    box, apex, _axis = figs[0]
    assert box.x0 - 0.5 <= apex[0] <= box.x1 + 0.5
    assert box.y0 - 0.5 <= apex[1] <= box.y1 + 0.5


def test_the_rule_still_comes_from_the_legend_shape():
    """§9 — 조건은 그대로다: 중공 · 한 객체 · 선 6개 · 꼭짓점에 끝점 4개."""
    src = inspect.getsource(dv._angle_figures)
    assert 'd.get("fill") is not None' in src
    assert "len(items) != 6" in src
    assert "if n != 4:" in src
