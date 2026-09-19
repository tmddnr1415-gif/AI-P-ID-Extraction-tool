"""도면이 버블에 이름을 붙인 밸브는 품목이다 (53회차 · 8차 피드백 s4·s5·s6).

지키는 것 다섯:
  ① 태그가 있으면 액추에이터가 없어도 행이 된다 — **태그가 없으면 안 된다**
     (이 문서의 수동 밸브 2,653개가 그 규칙으로 빠져 있고 그대로 있어야 한다)
  ② 탭을 지어내지 않는다 — 액추에이터가 정하는 값이라 없으면 검토로 간다
  ③ 밸브 태그 버블에 쌓인 신호 버블은 그 밸브로 접힌다 (ZSC·ZSO·ZT)
  ④ 연쇄는 **행이 없는 버블도 디딤돌로** 쓴다 (ZSO 는 행이 되지 않는다)
  ⑤ 몸체를 못 찾아도 버블이 있으면 행이 되고, **모양 칸은 비운다**
"""
from __future__ import annotations

import inspect
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import pipeline  # noqa: E402


def row(key, rect, *, anchor=None, tag_rect=None, tag=None, page_no=1):
    ev = {}
    if anchor:
        ev["anchor"] = anchor
    if tag_rect:
        ev["tag_rect"] = list(tag_rect)
        ev["tag"] = tag or "XV"
    return pipeline.Row(key=key, tab="REVIEW", page_no=page_no, drawing_no="D",
                        rect=tuple(rect), evidence=ev)


# --------------------------------------------------------------------------
# ①② 태그가 있으면 품목 — 규칙이 좁다는 것까지 소스로 못박는다
# --------------------------------------------------------------------------

def test_the_gate_keeps_a_tagged_body_and_still_drops_an_untagged_one():
    src = inspect.getsource(pipeline._valve_rows)
    assert "if cls == dv.CLASS_EXCLUDED and not unread and not tagged:" in src
    # 태그 여부는 몸체가 들고 있는 값이지 낱말 목록이 아니다
    assert 'tagged = bool(getattr(b, "tag", "") or "")' in src


def test_the_tab_is_not_invented():
    """액추에이터가 없으면 어느 산출물인지 도면이 말하지 않는다 — 검토로 간다."""
    assert pipeline._VALVE_TAB.get("EXCLUDED") is None
    src = inspect.getsource(pipeline._valve_rows)
    assert "_VALVE_TAB.get(cls, TAB_REVIEW)" in src
    assert pipeline._TAGGED_NO_ACTUATOR_CODE == "TAGGED_VALVE_NO_ACTUATOR"


# --------------------------------------------------------------------------
# ③④ 신호 버블 접기
# --------------------------------------------------------------------------

def test_a_signal_bubble_touching_a_valve_tag_folds_into_it():
    valve = row("v", (0, 0, 0, 0), tag_rect=(100, 200, 160, 220), tag="XV")
    sig = row("s", (100, 180, 160, 200), anchor="ZSO")     # 바로 위, 틈 0
    owned, folded = pipeline._valve_tag_signals([valve, sig])
    assert folded == {"s"}
    assert owned["v"] == [("ZSO", sig)]


def test_a_bubble_that_does_not_touch_is_left_alone():
    valve = row("v", (0, 0, 0, 0), tag_rect=(100, 200, 160, 220), tag="XV")
    far = row("s", (100, 100, 160, 120), anchor="ZSO")     # 80pt 위
    owned, folded = pipeline._valve_tag_signals([valve, far])
    assert folded == set() and owned == {}


def test_a_bubble_beside_it_is_not_a_stack():
    """가로로 겹치지 않으면 쌓인 것이 아니라 옆에 있는 것이다."""
    valve = row("v", (0, 0, 0, 0), tag_rect=(100, 200, 160, 220), tag="XV")
    beside = row("s", (170, 200, 230, 220), anchor="ZSO")
    _owned, folded = pipeline._valve_tag_signals([valve, beside])
    assert folded == set()


def test_the_chain_steps_through_a_bubble_that_has_no_row():
    """p21 이 그렇다 — `ZSC` / `ZSO` / `XV` 인데 `ZSO` 는 범례 표에 `O` 가 없어
    행이 되지 않는다.  행만 타면 거기서 끊겨 `ZSC` 가 남는다 (실측 7행)."""
    valve = row("v", (0, 0, 0, 0), tag_rect=(100, 200, 160, 220), tag="XV")
    top = row("zsc", (100, 160, 160, 180), anchor="ZSC")   # 두 칸 위
    middle = (100, 180, 160, 200)                          # 행이 없는 ZSO 버블
    owned, folded = pipeline._valve_tag_signals(
        [valve, top], {1: [middle, (100, 200, 160, 220), (100, 160, 160, 180)]})
    assert folded == {"zsc"}, "행이 없는 버블을 디딤돌로 못 쓰면 여기서 끊긴다"
    assert owned["v"] == [("ZSC", top)]


def test_without_the_stepping_stones_the_far_one_is_not_reached():
    """④ 를 검사하는 시험이 실제로 무언가를 잡는지 — 디딤돌을 빼면 실패해야 한다."""
    valve = row("v", (0, 0, 0, 0), tag_rect=(100, 200, 160, 220), tag="XV")
    top = row("zsc", (100, 160, 160, 180), anchor="ZSC")
    _owned, folded = pipeline._valve_tag_signals([valve, top])   # 버블 목록 없음
    assert folded == set()


# --------------------------------------------------------------------------
# ⑤ 몸체를 못 찾은 태그 버블
# --------------------------------------------------------------------------

def test_a_tag_bubble_with_no_body_becomes_a_row_with_the_shape_left_blank():
    src = inspect.getsource(pipeline._valve_rows)
    assert 'for text, bub in (res.get("tags") or ()):' in src
    assert "_TAG_NO_BODY_CODE" in src
    # 모양을 지어내지 않는다 — 몸체·액추에이터 칸이 빈 문자열로 나간다
    assert 'type="",' in src and 'valve_type="",' in src
    assert pipeline._TAG_NO_BODY_CODE == "VALVE_TAG_NO_BODY"


def test_the_new_codes_are_named_on_the_screen():
    from app import main
    for code in (pipeline._TAGGED_NO_ACTUATOR_CODE, pipeline._TAG_SIGNAL_CODE,
                 pipeline._TAG_NO_BODY_CODE):
        assert code in main.REVIEW_LABELS, f"{code} 가 화면에서 이름이 없다"
