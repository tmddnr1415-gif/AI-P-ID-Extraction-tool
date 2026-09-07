"""벤더 별표를 놓치지 않았는지 — **검출기에게 묻지 않고** 확인한다 (18회차).

## 왜 이 파일이 있나

16회차는 이렇게 보고했다.

    58장 전수: 별표가 있는데 벤더가 아닌 검출 **0** ·
               별표도 상자도 없는데 벤더인 검출 **0**

그런데 3차 피드백이 같은 종류의 오류를 네 건 더 지목했다.  원인은 **검사가
자기 자신에게 물었다**는 것이다:

    "별표가 있는가" 를 `read_vendor_mark` 에게 물었고,
    `read_vendor_mark` 는 `find_marks` 가 준 마크만 보고,
    `find_marks` 는 그 장 범례 별표 크기 ±0.6pt 밖의 글리프를 **이미 버렸다**.

버려진 별표는 검사에도 안 보인다.  그래서 검사는 언제나 0 을 낸다 — 검출기가
무엇을 놓치든.

## 이 파일의 검사는 무엇이 다른가

`find_marks` 를 **부르지 않는다.**  잉크 획 글리프 뭉치(`_glyph_clusters`)를
그대로 놓고, 그것이 **버블의 마크 자리**(config 실측값 `mark_above` 25.0 ·
`mark_x_slack` 6.0)에 있는지만 본다.  크기는 보지 않는다 — 크기가 바로 검출기가
틀린 지점이기 때문이다.

## 그리고 이 검사 자체를 검사한다

`test_the_audit_catches_a_detector_that_was_made_blind` 가 검출기를 **일부러
멀게 만들고** 검사가 그것을 잡는지 본다.  검사가 그때도 0 을 내면 그 검사는
16회차의 것과 같은 종류이므로 믿을 수 없다.

**이것이 이 회차의 방법론이다 — 검사는 검출기와 다른 재료를 써야 하고,
검사가 실패할 수 있다는 것을 보여야 한다.**
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))

PDF = ROOT / "data" / "pid_total.pdf"
pytestmark = pytest.mark.skipif(not PDF.exists(), reason="sample PDF not present")


def glyphs_in_mark_position(pc, lay, bubbles):
    """마크 자리에 있는 잉크 획 글리프 — **크기를 보지 않는다.**"""
    import detect_symbols as ds
    out = []
    for c in ds._glyph_clusters(pc, lay):
        if c.x1 > lay.drawing_area[2]:
            continue
        cx, cy = (c.x0 + c.x1) / 2, (c.y0 + c.y1) / 2
        for b in bubbles:
            if (b.x0 - lay.mark_x_slack <= cx <= b.x1 + lay.mark_x_slack
                    and b.y0 - lay.mark_above <= cy <= b.y0):
                out.append((c, b, cx, cy))
                break
    return out


def audit_page(pc, lay, *, sizes_override=None):
    """그 장에서 **놓친 별표**를 센다.

    ⚠ 묻는 대상은 **행이 된 버블**이다.  버블이 있어도 그 자리가 계기가
      아니면(범례 장의 삽화가 그렇다) 그 위의 글리프는 벤더 마크가 아니라
      그림의 일부다 — 실측: p3(Symbol & Legend)의 PSV 삽화에서 스템 해치가
      별표와 같은 크기·모양으로 잡힌다.  **페이지로 분기하지 않고** "이
      버블이 검출을 냈나" 로 가린다.

    `sizes_override` 는 검사 자체를 시험하기 위한 자리다 — 검출기를 일부러
    멀게 만들 때 쓴다.
    """
    import detect_symbols as ds
    dets, *_ = ds.detect(pc, lay=lay, rules=ds.RULESET_V3,
                         allow_glyph_sizes=ds.KNOWN_GLYPH_SIZES)
    if not dets:
        return []
    all_bubbles = ds.find_bubbles(pc, lay)
    bubbles = [b for b in all_bubbles
               if any(b.x0 - 1 <= d.center[0] <= b.x1 + 1
                      and b.y0 - 1 <= d.center[1] <= b.y1 + 1 for d in dets)]
    if not bubbles:
        return []
    _, glyph_size = ds.read_mark_dictionary(pc, lay)
    if sizes_override is None:
        marks = ds.find_marks(pc, lay, glyph_size,
                              allow_sizes=ds.KNOWN_GLYPH_SIZES, bubbles=bubbles)
    else:
        marks = ds.find_marks(pc, lay, sizes_override[0],
                              allow_sizes=(), bubbles=())
    counted = {(round(m.x, 1), round(m.y, 1)) for m in marks}
    missed = []
    for c, b, cx, cy in glyphs_in_mark_position(pc, lay, bubbles):
        if (round(cx, 1), round(cy, 1)) not in counted:
            missed.append({"x": round(cx, 1), "y": round(cy, 1),
                           "w": round(c.width, 2), "h": round(c.height, 2),
                           "bubble": [round(v, 1) for v in (b.x0, b.y0, b.x1, b.y1)]})
    return missed


def _pages():
    from pidcache import load_pages
    _doc, pages = load_pages(PDF)
    return pages


@pytest.mark.slow
def test_no_asterisk_in_a_mark_position_is_silently_dropped():
    """도면에 찍힌 별표가 조용히 사라지지 않는다 — 58장 전수.

    ⚠ 분석 대상 장에서만 묻는다 (`analysis_scope`).  범례·표지 장에는
      버블처럼 생긴 것이 표 안에 있고 그 위의 글리프는 마크가 아니라 표의
      항목이다 — 그 장들은 행을 내지도 않는다.
    """
    import detect_symbols as ds
    lay = ds.LAYOUT
    missed = {}
    for pc in _pages():
        if not pc.analysis_scope:
            continue
        m = audit_page(pc, lay)
        if m:
            missed[pc.page_no] = m
    assert not missed, (
        "마크 자리에 별표가 있는데 마크로 안 세어졌다 — 페이지별 건수 "
        + str({k: len(v) for k, v in missed.items()})
        + f"  첫 건: {next(iter(missed.values()))[0] if missed else ''}")


@pytest.mark.slow
def test_the_audit_catches_a_detector_that_was_made_blind():
    """**검사 자체를 검사한다.**

    검출기가 이 문서에 없는 크기만 인정하도록 일부러 멀게 만든다.  그러면
    별표는 도면에 그대로 있는데 하나도 안 세어지므로, 검사는 **반드시**
    그것을 잡아야 한다.  여기서 0 이 나오면 그 검사는 16회차의 것과 같은
    종류(검출기에게 되묻는 것)이고 아무것도 보장하지 못한다.
    """
    import detect_symbols as ds
    lay = ds.LAYOUT
    blind = ((99.0, 99.0),)          # 이 문서에 없는 크기
    caught = 0
    for pc in _pages():
        if not pc.analysis_scope:
            continue
        caught += len(audit_page(pc, lay, sizes_override=blind))
    assert caught > 0, (
        "검출기를 멀게 만들었는데도 검사가 아무것도 못 잡았다 — "
        "이 검사는 검출기와 같은 재료를 쓰고 있다")
