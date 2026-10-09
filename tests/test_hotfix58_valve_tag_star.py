"""hotfix58 — 밸브 태그 버블 위의 별표는 그 밸브의 것이다.

현장(EPIC Rev.E p9): `**` 가 MOV **태그 버블 위**에 찍혀 있는데 MOV 가 SCT 로 나갔다.
밸브가 별표를 읽는 자리(`mark_rects`)가 몸체·액추에이터뿐이었고, 같은 버블의 별표를
몸체를 못 찾은 밸브(53회차 [B-3] 버블 자리 행)는 버블에서 읽고 있었다.
"""
import pymupdf

from app.engine import detect_symbols as ds
from app.engine import detect_valves as dv


def _mov(tag=True):
    return dv.Body(kind="GATE", rect=pymupdf.Rect(400, 600, 409, 605), axis="H",
                   actuator="MOTOR", actuator_rect=(399, 580, 410, 591),
                   tag="MOV" if tag else "",
                   tag_rect=(390, 540, 430, 552) if tag else ())


def _read(body, marks, others=()):
    rect, *also = dv.mark_rects(body)
    return ds.read_vendor_mark(rect, marks, (), {2: "HRSG"}, ds.LAYOUT,
                               also=tuple(also), others=others)


STAR_ABOVE_TAG = [ds.Mark(408, 536, 1, "GLYPH"), ds.Mark(412, 536, 1, "GLYPH")]


def test_tag_bubble_is_where_the_valve_reads_its_star():
    assert pymupdf.Rect(390, 540, 430, 552) in dv.mark_rects(_mov())
    hit, ev = _read(_mov(), STAR_ABOVE_TAG)
    assert hit == ["VENDOR_MARK_GLYPH"] and ev["stars"] == 2 and ev["meaning"] == "HRSG"


def test_untagged_valve_reads_as_before():
    assert dv.mark_rects(_mov(tag=False)) == (pymupdf.Rect(399, 580, 410, 591),
                                               pymupdf.Rect(400, 600, 409, 605))
    assert _read(_mov(tag=False), STAR_ABOVE_TAG) == ([], None)


def test_a_star_on_the_valve_and_its_bubble_counts_once():
    marks = STAR_ABOVE_TAG + [ds.Mark(404, 575, 1, "GLYPH")]   # 액추에이터 위에도 하나
    _hit, ev = _read(_mov(), marks)
    assert ev["stars"] == 3                                     # 넷이 아니라 셋 — 각 마크 한 번


def test_a_nearer_neighbour_bubble_still_wins_its_own_star():
    """옆 계기 버블 바로 위 별표는 그 버블의 것 — 경쟁 규칙(16·19회차)은 그대로다."""
    neighbour = pymupdf.Rect(432, 540, 470, 552)
    marks = [ds.Mark(450, 536, 1, "GLYPH"), ds.Mark(454, 536, 1, "GLYPH")]
    assert _read(_mov(), marks, others=[neighbour]) == ([], None)


def test_item_rects_still_names_the_tag_bubble_for_rivalry():
    rects, tag = dv.item_rects(_mov())
    assert tag == pymupdf.Rect(390, 540, 430, 552) and tag in rects
