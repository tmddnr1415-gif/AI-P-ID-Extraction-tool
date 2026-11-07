"""48회차 — 별표 소유권 경쟁에 밸브도 들어간다.

16회차가 "한 마크는 심볼 하나에만 붙는다" 를 세웠고 19회차가 그 "가깝다" 를
유클리드로 고쳤는데, **경쟁자 목록이 버블끼리로 좁혀져 있었다.**  밸브는 계기
검출 뒤에 서므로 `detect()` 가 알 수 없었고, `_valve_rows` 는 아예 `others` 를
넘기지 않았다.  실측(`spike/mark_owner_probe.py`):

    AL NOUF1  마크 546 · 다툼 0        ← 게이트가 구조적으로 안전한 이유
    SADARA    마크  10 · 다툼 0
    TC2       버블이 밸브 것을 3 · 밸브가 버블 것을 32
    UAD       24 · 24

여기 시험은 **새 규칙을 만들지 않았다는 것**과 **두 갈래가 같은 사각형을
본다는 것**을 못박는다.  거리 판정은 19회차 `_mark_gap` 그대로다.
"""
import ast
import pathlib
import sys

import pymupdf
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "engine"))

import detect_symbols as ds      # noqa: E402
import detect_valves as dv       # noqa: E402


class _Body:
    """`dv.mark_rects` 가 보는 것만 가진 최소 몸체."""

    def __init__(self, rect, actuator_rect=None):
        self.rect = pymupdf.Rect(*rect)
        self.actuator_rect = actuator_rect


def _mark(x, y, stars=1, form="GLYPH"):
    return ds.Mark(x, y, stars, form)


def test_mark_rects_is_the_same_choice_the_rows_make():
    """액추에이터가 있으면 두 사각형, 없으면 하나 — 19회차 `also` 와 같다."""
    body = _Body((100, 100, 120, 120), (100, 70, 114, 84))
    rects = dv.mark_rects(body)
    assert len(rects) == 2
    assert tuple(rects[0]) == (100, 70, 114, 84)   # 액추에이터가 먼저
    assert rects[1] is body.rect
    assert dv.mark_rects(_Body((10, 10, 30, 30))) == (pymupdf.Rect(10, 10, 30, 30),)


def test_rows_and_the_contest_read_the_same_function():
    """두 벌을 두면 경쟁에서 이긴 마크를 읽을 때 놓친다."""
    src = (ROOT / "app" / "pipeline.py").read_text()
    body = src[src.index("def _valve_rows("):]
    body = body[:body.index("\ndef ", 1)]
    assert "dv.mark_rects(b)" in body, "행이 사각형을 스스로 고르면 안 된다"
    assert "b.actuator_rect else b.rect" not in body, "사각형 고르기가 두 벌이다"


def test_valve_rows_passes_rivals():
    src = (ROOT / "app" / "pipeline.py").read_text()
    body = src[src.index("def _valve_rows("):]
    body = body[:body.index("\ndef ", 1)]
    assert "others=others" in body
    assert 'get("bubbles")' in body, "버블이 경쟁 상대에 없다"
    assert "own_tag" in body, "자기 태그 버블을 남으로 세고 있다"


def test_detect_takes_rivals_and_adds_them_to_others():
    """`detect` 가 `rivals` 를 **`others` 에 더한다** — 다른 규칙을 만들지 않는다."""
    src = (ROOT / "app" / "engine" / "detect_symbols.py").read_text()
    tree = ast.parse(src)
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "detect")
    assert "rivals" in [a.arg for a in fn.args.args]
    seg = src[src.index("mark_rules, vmark = read_vendor_mark(bubble"):]
    seg = seg[:400]
    assert "others=" in seg and "_rival_rects(rivals, bubble)" in seg


def test_a_tag_bubble_is_not_a_rival_of_the_valve_it_names():
    """AL NOUF1 p7 — 밸브 울타리 위 `**` 오른쪽 4.7pt 에 NRV 태그 버블이 선다.

    남으로 보면 오른쪽 별 하나만 버블이 가져가 `**` 가 쪼개지고 뜻이
    ST SUPPLIER → HRSG 로 바뀐다.  도면은 이미 그 둘을 한 항목으로 그렸다.
    """
    bubble = pymupdf.Rect(756.7, 1158.0, 800.0, 1180.0)
    valve = pymupdf.Rect(740.0, 1180.0, 755.0, 1194.0)
    rivals = [((valve,), bubble)]          # 이 밸브의 태그가 바로 그 버블
    assert ds._rival_rects(rivals, bubble) == []
    other = pymupdf.Rect(100, 100, 140, 114)
    assert ds._rival_rects(rivals, other) == [valve]
    assert ds._rival_rects([((valve,), None)], bubble) == [valve]


def test_the_nearer_family_takes_the_mark():
    """밸브가 더 가까우면 버블은 그 마크를 갖지 않는다 (그 반대도)."""
    lay = ds.LAYOUT
    bubble = pymupdf.Rect(200, 200, 240, 214)
    # 버블 위 창 안이지만 밸브 몸체가 훨씬 가깝다.
    valve = pymupdf.Rect(196, 186, 210, 196)
    mark = _mark(203, 191)
    assert ds.in_mark_window(bubble, mark.x, mark.y, lay)
    rules, ev = ds.read_vendor_mark(bubble, [mark], [], {1: "SE"}, lay)
    assert ev and ev["stars"] == 1              # 경쟁자가 없으면 버블이 가져간다
    rules, ev = ds.read_vendor_mark(bubble, [mark], [], {1: "SE"}, lay,
                                    others=[valve])
    assert ev is None                            # 밸브가 더 가까우면 안 가져간다


def test_the_mark_is_not_counted_twice_for_one_item():
    """액추에이터 창과 몸체 창에 다 들어와도 한 번만 세어진다 (19회차)."""
    lay = ds.LAYOUT
    act = pymupdf.Rect(300, 300, 314, 314)
    body = pymupdf.Rect(299, 312, 315, 330)
    mark = _mark(305, 296)
    rules, ev = ds.read_vendor_mark(act, [mark], [], {1: "SE"}, lay,
                                    also=(body,))
    assert ev["stars"] == 1


def test_no_new_distance_rule():
    """거리는 19회차 `_mark_gap` 하나다 — 새 함수가 생기면 안 된다."""
    src = (ROOT / "app" / "engine" / "detect_symbols.py").read_text()
    tree = ast.parse(src)
    names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    assert "_mark_gap" in names
    assert not {n for n in names if n.endswith("_gap")} - {"_mark_gap", "_x_gap"}
