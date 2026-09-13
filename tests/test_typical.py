"""38회차 [D] — Typical 참조.  모양으로 읽고, 캡션이 있는 id 만 참조로 센다, 곱하는 곳은 하나."""
from __future__ import annotations
import sys
from pathlib import Path
import pymupdf
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "engine")); sys.path.insert(0, str(ROOT))
import typical  # noqa: E402
from app import pipeline as P  # noqa: E402


class _PC:
    """words · drawings() · segments() 만 가진 가짜 쪽."""
    def __init__(self, words, circles, hlines):
        self.words = [(pymupdf.Rect(*r), t) for r, t in words]
        self._c = circles; self._h = hlines
    def drawings(self):
        return [{"items": [("c",)] * 4, "bbox": pymupdf.Rect(x - d / 2, y - d / 2, x + d / 2, y + d / 2)}
                for x, y, d in self._c]
    def segments(self):
        return [(pymupdf.Point(x0, y), pymupdf.Point(x1, y)) for x0, x1, y in self._h]


AREA = pymupdf.Rect(0, 0, 900, 800)


def _tc2_like():
    # 라인 표식 D 셋(y=300) · 캡션 D (600,660) + 제목 · 상자 y 650~800 x 500~900 · 모터 M 원 하나
    words = [((598, 658, 602, 662), "D"), ((607, 658, 618, 662), "HRH"), ((620, 658, 640, 662), "TYPICAL"),
             ((642, 658, 680, 662), "CONFIGURATION"),
             ((198, 298, 202, 302), "D"), ((398, 298, 402, 302), "D"), ((498, 298, 502, 302), "D"),
             ((298, 398, 302, 402), "M")]
    circles = [(600, 660, 7.1), (200, 300, 7.1), (400, 300, 7.1), (500, 300, 7.1), (300, 400, 7.1)]
    hlines = [(500, 900, 650), (500, 900, 800), (0, 900, 300)]
    return _PC(words, circles, hlines)


def test_marks_captions_boxes_and_refs_are_read_by_shape():
    t = typical.analyse(_tc2_like(), AREA, ceiling=11.4)
    assert sorted(m.id for m in t.marks) == ["D", "D", "D", "D", "M"]
    assert len(t.details) == 1 and t.details[0].id == "D"
    assert t.details[0].caption.startswith("HRH TYPICAL")           # ':' 없이도 캡션
    assert [round(v) for v in t.details[0].box] == [500, 650, 900, 800]
    assert t.refs == {"D": 3} and "M" not in t.refs                 # 캡션 없는 M 은 참조가 아니다
    assert not t.ambiguous


def test_a_circle_as_big_as_a_bubble_is_not_a_mark():
    t = typical.analyse(_tc2_like(), AREA, ceiling=7.0)             # 상한이 원보다 작다
    assert t.marks == [] and t.details == []


def test_two_captions_with_the_same_id_are_ambiguous_not_multiplied():
    pc = _tc2_like()
    pc.words += [((598, 708, 602, 712), "D"), ((607, 708, 630, 712), "OTHER")]
    pc._c.append((600, 710, 7.1))
    t = typical.analyse(pc, AREA, ceiling=11.4)
    assert t.ambiguous == {"D"}


class _Row:
    def __init__(self, page_no, rect, qty):
        self.page_no, self.rect, self.qty, self.evidence, self.needs_review = page_no, rect, qty, {"qty_basis": "1 symbol x 8 (NOTES)"}, ""


def test_apply_multiplies_only_rows_inside_the_detail_box():
    t = typical.analyse(_tc2_like(), AREA, ceiling=11.4)
    inside, outside, none = _Row(1, (600, 700, 630, 712), 8), _Row(1, (100, 100, 130, 112), 8), _Row(1, (610, 700, 640, 712), None)
    stats = P._apply_typical([inside, outside, none], {1: t})
    assert inside.qty == 24 and outside.qty == 8 and none.qty is None
    assert inside.evidence["typical"]["refs"] == 3 and "x 3 (Typical D" in inside.evidence["qty_basis"]
    assert stats["rows_multiplied"] == 1 and stats["rows_in_detail"] == 2


def test_ambiguous_rows_are_flagged_not_multiplied():
    pc = _tc2_like()
    pc.words += [((598, 708, 602, 712), "D"), ((607, 708, 630, 712), "OTHER")]
    pc._c.append((600, 710, 7.1))
    t = typical.analyse(pc, AREA, ceiling=11.4)
    r = _Row(1, (600, 700, 630, 712), 8)
    P._apply_typical([r], {1: t})
    assert r.qty == 8 and "TYPICAL_AMBIGUOUS" in r.evidence["review_codes"]


def test_the_only_place_that_multiplies_is_apply_typical():
    src = (ROOT / "app" / "pipeline.py").read_text()
    assert src.count("typical.analyse(") == 1 and src.count("= _apply_typical(") == 1
