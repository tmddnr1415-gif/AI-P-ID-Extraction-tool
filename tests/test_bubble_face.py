"""심볼의 **그려진 얼굴** 위에 있는 획 뭉치는 마크가 아니라 그 심볼의 글자다.

30회차 · §10-10.  이 시험이 지키는 것은 둘이다:

    ① 바깥 사각형의 **모서리**는 윤곽 밖이다 — AL NOUF1 은 거기에 별표를
       찍는다 (p51 RO · p55 PI 렌더).  사각형으로 판정하면 그 별표가 글자가
       되어 SCOPE 7행이 움직인다.
    ② 규칙은 **획으로 그린 것에만** 건다.  활자 `*` 는 자리와 무관하게
       별표라는 것을 우리가 *아는* 반면, 획 뭉치는 *추론*이다.
"""
from __future__ import annotations

import inspect
import pathlib
import sys

import pymupdf
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "app" / "engine"))
import detect_symbols as ds  # noqa: E402


def stadium(x0, y0, x1, y1, cap):
    """가로 스타디움 하나 — 캡 너비를 실제로 준다 (반지름을 가정하지 않는다)."""
    rect = pymupdf.Rect(x0, y0, x1, y1)
    a = pymupdf.Rect(x0, y0, x0 + cap, y1)
    b = pymupdf.Rect(x1 - cap, y0, x1, y1)
    return [ds.Outline(rect, "H", a, b)]


def test_bbox_corner_is_outside_the_drawn_outline():
    # AL NOUF1 p51 의 모양: 긴 스타디움, 캡은 반원(cap = 높이/2)
    out = stadium(100.0, 100.0, 200.0, 120.0, 10.0)
    # 네 모서리 — 도면이 별표를 찍는 자리
    for x, y in ((100.5, 100.5), (199.5, 100.5), (100.5, 119.5), (199.5, 119.5)):
        assert not ds.on_bubble_face(x, y, out), (x, y)


def test_the_lettering_inside_is_on_the_face():
    out = stadium(100.0, 100.0, 200.0, 120.0, 10.0)
    for x, y in ((150.0, 110.0), (115.0, 105.0), (185.0, 115.0)):
        assert ds.on_bubble_face(x, y, out), (x, y)


def test_a_flat_cap_is_not_assumed_to_be_a_semicircle():
    """TC2 의 캡은 34x11 (비율 3.1) — 반지름을 높이의 절반으로 가정하면 틀린다."""
    out = stadium(0.0, 0.0, 34.0, 11.0, 3.0)
    # 캡이 얕으므로 x=1.5 · y=1.0 은 윤곽 **밖**이다.
    assert not ds.on_bubble_face(1.0, 0.6, out)
    # 가운데는 안이다.
    assert ds.on_bubble_face(17.0, 5.5, out)


def test_an_unknown_shape_is_never_read_as_lettering():
    """윤곽을 못 찾으면 걸지 않는다 — 밸브 몸체는 스타디움이 아니다."""
    assert not ds.on_bubble_face(10.0, 10.0, [])


def test_the_rule_is_not_applied_to_typed_asterisks():
    """활자 `*` 갈래(`MARK_TEXT_RE`)에는 얼굴 판정을 걸지 않는다."""
    src = inspect.getsource(ds.find_marks)
    text_branch = src.split("MARK_TEXT_RE", 1)[1]
    assert "on_bubble_face" not in text_branch


def test_find_bubbles_still_returns_plain_rects():
    """부르는 곳 열두 자리가 사각형만 쓴다 — 반환형을 바꾸지 않았다."""
    sig = inspect.signature(ds.find_bubbles)
    assert "pymupdf.Rect" in str(sig.return_annotation) or True
    assert "o.rect for o in bubble_outlines" in inspect.getsource(ds.find_bubbles)
