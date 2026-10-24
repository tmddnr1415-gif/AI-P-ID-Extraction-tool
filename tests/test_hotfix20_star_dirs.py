"""hotfix20 — 글리프 채널의 별표는 **방향이 셋 이상인 획 뭉치**다.

크기 창을 문서 단위로 곱하자 절반 축척 문서(TC2)에서 밸브 날개 틱(1획)·파선
모서리(2획)가 별표 크기가 되어 SCOPE 가 뒤집혔다 (p7 MOV · p25 PIT · p16 PI).
AL NOUF1 pt 로 적힌 크기 하한이 우연히 걸러 주던 것이다.  가르는 것은 크기가
아니라 모양이고, 값은 `star_groups` 가 본문 별표에 요구하는 것과 같다 (38회차).
방향은 **뭉치 자리의 모든 획**에서 센다 — 별표의 가로·세로 획은 납작해 크기
걸림에서 떨어지고 대각선보다 길게 뻗는다 (AL NOUF1 p26: 8획 · 4방향).
"""
import types

import pymupdf

from app.engine import detect_symbols as ds


def _drawing(x, y, segs, fill=None):
    items = [("l", pymupdf.Point(x + a, y + b), pymupdf.Point(x + c, y + d)) for a, b, c, d in segs]
    xs = [p.x for it in items for p in it[1:]]; ys = [p.y for it in items for p in it[1:]]
    return {"items": items, "rect": pymupdf.Rect(min(xs), min(ys), max(xs), max(ys)),
            "bbox": pymupdf.Rect(min(xs), min(ys), max(xs), max(ys)),
            "fill": fill, "color": (0.0, 0.0, 0.0), "width": 0.5}


STAR = [(0, 2, 4, 2), (2, 0, 2, 4), (0.6, 0.6, 3.4, 3.4), (0.6, 3.4, 3.4, 0.6)]     # + and x, 4 directions
TICK = [(0.4, 0.4, 2.2, 2.0)]                                                        # one diagonal stroke
CORNER = [(0, 1.8, 1.8, 1.8), (1.8, 0, 1.8, 1.8)]                                    # dashed-line corner


def _page(drawings):
    return types.SimpleNamespace(drawings=lambda: drawings, page_no=1)


def _lay():
    return ds.Layout(mark_blob=(0.75, 8.0), mark_glyph_span=(1.5, 8.0), mark_cluster_gap=2.0,
                     mark_above=25.0, note_line_gap=20.0, box_mark_margin=20.0,
                     brk_max_mark=28.3, scope_text_tol=1.0, drop_x_tol=1.0, drop_end_tol=1.0,
                     scope_box_both_edges=False)


def test_stroke_directions_are_binned_into_four():
    assert ds._stroke_dirs(_drawing(0, 0, STAR)) == {0, 1, 2, 3}
    assert len(ds._stroke_dirs(_drawing(0, 0, TICK))) == 1
    assert len(ds._stroke_dirs(_drawing(0, 0, CORNER))) == 2


def test_clusters_report_directions_of_every_stroke_at_that_place():
    # 별표를 획 하나씩 따로 그린 문서 (AL NOUF1 p26 · TC2) — 납작한 획도 방향에 든다
    drawings = [_drawing(100, 100, [seg]) for seg in STAR]
    drawings += [_drawing(200, 100, TICK), _drawing(300, 100, [CORNER[0]]), _drawing(300, 100, [CORNER[1]])]
    got = {(round(bb.x0), round(bb.y0)): n for bb, n in ds._glyph_clusters(_page(drawings), _lay(), with_dirs=True)}
    assert got[(101, 101)] >= ds.STAR_MIN_DIRS          # 별표
    assert all(n < ds.STAR_MIN_DIRS for k, n in got.items() if k != (101, 101))   # 틱·모서리
    assert ds.STAR_MIN_DIRS == 3


def test_glyph_channel_and_size_learning_use_the_direction_rule():
    import inspect
    for fn in (ds.find_marks, ds.drawn_mark_sizes):
        src = inspect.getsource(fn)
        assert "with_dirs=True" in src and "ndirs < STAR_MIN_DIRS" in src
