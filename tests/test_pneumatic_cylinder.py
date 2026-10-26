"""56회차 — 공압 실린더·파일럿 상자를 A3 도면에서도 찾는다.

9차 피드백이 세 번 되풀이한 *"TC2 에서 XV·PCV·TCV 가 식별되지 않는다"* 의
원인은 둘이었고 **둘 다 AL NOUF1(A1 용지)에서 잰 절대 pt** 였다.

㉠ `legend_rules.closed_boxes` 의 기본 창 `(9.0, 40.0)` pt.  TC2 는 같은
   실린더 상자를 7.08 로 그리므로 **범례에서 실린더를 한 개도 못 찾고**,
   `cylinder_side` 가 비면 `detect_valves._pneumatic_cylinders` 가 통째로 꺼진다.
㉡ 도면 장의 파일럿 상자가 *글자를 기다리는 상자*로 읽혔다.  범례는 이미
   가르는 기준을 인쇄해 두었다 — **칸막이가 있으면 글자 상자가 아니다**
   (`derive_pneumatic` 의 머리말).  그 문장을 범례 장에서만 쓰고 도면 장에서는
   쓰지 않아, 읽을 글자가 없는 상자가 `actuator=NONE` 으로 끝났다.

여기서 못박는 것 넷:

1. 창은 **그 시트가 그린 돔의 배수**다 — 코드에 새 절대 pt 가 없다.
2. AL NOUF1 을 소수점까지 재현한다 (돔 14.22 × 배수 = 9.0 · 40.0) — 게이트.
3. 절반 축척의 상자는 배수 창에서만 잡히고 옛 절대 창에서는 안 잡힌다.
4. 칸막이 규칙은 **범례가 그 위치를 재 줬을 때만** 판정한다.  못 쟀으면
   판정하지 않는다 (없는 기준을 지어내지 않는다).
"""
import dataclasses

import pymupdf

from app.engine import detect_valves as dv
from app.engine import legend_rules as lr


def _box_segments(x0, y0, side, *, divider=None, scale=1.0):
    """네 변이 그어진 상자와, 있으면 가로지르는 칸막이 — `(p0, p1)` 목록."""
    s = side * scale
    segs = [((x0, y0), (x0 + s, y0)),
            ((x0, y0 + s), (x0 + s, y0 + s)),
            ((x0, y0), (x0, y0 + s)),
            ((x0 + s, y0), (x0 + s, y0 + s))]
    if divider is not None:
        y = y0 + s * divider
        segs.append(((x0, y), (x0 + s, y)))
    return [(pymupdf.Point(*a), pymupdf.Point(*b)) for a, b in segs]


def test_the_band_reproduces_the_old_absolute_window():
    """게이트 — AL NOUF1 의 돔 14.22 를 되곱하면 옛 (9.0, 40.0) 이다."""
    lo, hi = (lr.ENCLOSURE_BASIS * b for b in lr.ENCLOSURE_BAND)
    assert abs(lo - 9.0) < 1e-9 and abs(hi - 40.0) < 1e-9
    # 그리고 그 창은 기본값과 같은 값이다 — 두 벌이 아니다.
    assert lr.ENCLOSURE_SIDES == (9.0, 40.0)


def test_a_half_scale_box_needs_the_scaled_band():
    """절반으로 그린 상자는 옛 절대 창에서 사라지고 배수 창에서 잡힌다."""
    index = lr.stroke_index(_box_segments(100.0, 100.0, 7.08, divider=0.5))
    assert list(lr.closed_boxes(index)) == []          # 옛 (9.0, 40.0)
    sides = (7.08 * lr.ENCLOSURE_BAND[0], 7.08 * lr.ENCLOSURE_BAND[1])
    got = list(lr.closed_boxes(index, sides=sides))
    assert len(got) == 1 and got[0][4]                  # 칸막이가 있다


def test_a_full_scale_box_is_found_either_way():
    """A1 축척은 두 창 모두에서 같은 답을 낸다 — 배수가 좁히지 않는다."""
    index = lr.stroke_index(_box_segments(100.0, 100.0, 14.16, divider=0.5))
    sides = (14.22 * lr.ENCLOSURE_BAND[0], 14.22 * lr.ENCLOSURE_BAND[1])
    assert len(list(lr.closed_boxes(index))) == 1
    assert len(list(lr.closed_boxes(index, sides=sides))) == 1


def _layout(divider=(0.387, 0.613)):
    return dataclasses.replace(dv.LAYOUT, cyl_divider=divider)


def test_a_divided_box_is_a_cylinder_not_a_letter_box():
    """범례가 그렇게 말한다 — 칸막이가 글자 상자와 실린더를 가른다."""
    horiz, _vert = lr.stroke_index(
        _box_segments(100.0, 100.0, 9.96, divider=0.5))
    b = pymupdf.Rect(100.0, 100.0, 109.96, 109.96)
    assert dv._box_divider(b, horiz, _layout())


def test_an_undivided_box_is_not():
    horiz, _vert = lr.stroke_index(_box_segments(100.0, 100.0, 9.96))
    b = pymupdf.Rect(100.0, 100.0, 109.96, 109.96)
    assert not dv._box_divider(b, horiz, _layout())


def test_a_stroke_that_does_not_cross_the_whole_box_is_not_a_divider():
    """`H` 의 가로획처럼 상자 안쪽에만 있는 획은 칸막이가 아니다."""
    segs = _box_segments(100.0, 100.0, 9.96)
    segs += [(pymupdf.Point(103.0, 105.0), pymupdf.Point(107.0, 105.0))]
    horiz, _vert = lr.stroke_index(segs)
    b = pymupdf.Rect(100.0, 100.0, 109.96, 109.96)
    assert not dv._box_divider(b, horiz, _layout())


def test_without_the_legend_nothing_is_judged():
    """범례가 칸막이 자리를 못 쟀으면 판정하지 않는다 (§9 ④)."""
    horiz, _vert = lr.stroke_index(
        _box_segments(100.0, 100.0, 9.96, divider=0.5))
    b = pymupdf.Rect(100.0, 100.0, 109.96, 109.96)
    assert not dv._box_divider(b, horiz, _layout(divider=()))
