"""36회차 [D] — 유닛 표기의 꼴은 그 도면이 말한다 (`projectconfig.learn_unit_forms`).

TC2 p33·p34 는 `TYPICAL FOR 3-1 & 3-2 SIMILAR P & ID SHALL BE APPLICABLE FOR 4-1 & 4-2` 라고
적어 `UNIT` 낱말이 없고, 옆 장 p35 는 같은 문장에 `UNIT` 이 있어 x8 이었는데 두 장은 x1 이었다.
문서가 자기 코드 `31` 을 `UNIT 3-1` 로 적는 것을 18장에서 배우면 `D-D` 꼴은 낱말 없이도 유닛이다.
맨 숫자는 배우지 않는다 — 문단 번호·날짜와 갈릴 길이 없다.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app" / "engine"))
import projectconfig     # noqa: E402


class _Page:
    def __init__(self, page_no, lines):
        self.page_no = page_no
        self.words = [(_R(10.0, 20.0 * i), t) for i, t in enumerate(lines)]


class _R:
    def __init__(self, x0, y0):
        self.x0, self.y0 = x0, y0


AREA = (0.0, 0.0, 1000.0, 1000.0)
TC2_LIKE = "1. THIS P&ID IS FOR UNIT 3-1. AND, SIMILAR SCHEME IS APPLICABLE TO UNIT 3-2, UNIT 4-1."
P33 = "5. THE P & ID IS TYPICAL FOR 3-1 & 3-2 SIMILAR P & ID SHALL BE APPLICABLE FOR 4-1 & 4-2."


def test_the_document_teaches_the_hyphenated_form_from_its_own_sheet_code():
    pages = [_Page(1, [TC2_LIKE]), _Page(2, [TC2_LIKE])]
    forms = projectconfig.learn_unit_forms(pages, AREA, 1000.0, {1: "31", 2: "31"})
    assert forms == {"D-D": 2}


def test_one_sheet_is_not_enough_to_learn_a_form():
    pages = [_Page(1, [TC2_LIKE])]
    assert projectconfig.learn_unit_forms(pages, AREA, 1000.0, {1: "31"}) == {}


def test_a_learned_form_counts_units_printed_without_the_word():
    head, _rng = projectconfig.note_vocabulary(None)
    assert projectconfig._unit_tokens(P33, head) == []                       # 27회차 그대로면 0
    assert projectconfig._unit_tokens(P33, head, forms=("D-D",)) == ["3-1", "3-2", "4-1", "4-2"]
    span = projectconfig.note_unit_span(_Page(33, [P33]), AREA, 1000.0, forms=("D-D",))
    assert span.count == 4 and span.units == ["3-1", "3-2", "4-1", "4-2"]


def test_the_form_comes_from_the_sheet_code_not_from_any_number():
    # 코드 00 인 장이 `DWG.NO. 00GEN00` 을 적어도 그것은 유닛 낱말 뒤가 아니다 — 배우지 않는다
    pages = [_Page(1, ["1. REFER TO SYMBOL & LEGEND DWG.NO. 00GEN00-M05-0002~0005."]),
             _Page(2, ["1. REFER TO SYMBOL & LEGEND DWG.NO. 00GEN00-M05-0002~0005."])]
    assert projectconfig.learn_unit_forms(pages, AREA, 1000.0, {1: "00", 2: "00"}) == {}


def test_bare_digits_are_never_learned_as_a_form():
    # `UNIT 10` 이라고 적어도 맨 `DD` 꼴은 배우지 않는다 — `10. LOCATION OF …` 와 갈릴 수 없다
    pages = [_Page(1, ["1. THIS P&ID IS FOR UNIT 10, IDENTICAL FOR UNIT 20."]),
             _Page(2, ["1. THIS P&ID IS FOR UNIT 10, IDENTICAL FOR UNIT 20."])]
    assert projectconfig.learn_unit_forms(pages, AREA, 1000.0, {1: "10", 2: "10"}) == {}


def test_without_a_learned_form_a_date_or_list_number_is_not_a_unit():
    head, _rng = projectconfig.note_vocabulary(None)
    for text in ("10. LOCATION OF RUPTURE DISC WILL BE DECIDED.",
                 "REV A 26.08.21 FOR INTERNAL USE",
                 "SET : 00 barg, DN200, SEE NOTE 3"):
        assert projectconfig._unit_tokens(text, head, forms=("D-D", "#DD")) == []
