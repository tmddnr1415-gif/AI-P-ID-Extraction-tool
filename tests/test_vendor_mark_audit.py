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

## ★ 그런데 18회차의 이 검사도 한 축을 판정기와 공유하고 있었다 (19회차)

4차 피드백이 **세 번째로** 같은 지적을 했다 (p25 · p27 · p30).  이 검사는
그때도 0 을 냈다.  이유는 축이 **하나만** 독립이었기 때문이다:

    크기 축   `find_marks` 를 안 부른다              → 독립  ✔
    자리 축   "마크 자리" 를 판정기와 **똑같은 식**   → 공유  ✘
              (`b.y0 - mark_above <= cy <= b.y0` · `x±mark_x_slack`)

그 식은 **"별표는 버블 위에 찍힌다"** 를 가정한다.  p25 · p30 의 별표는
버블 **옆**에 찍혀 있어서, 판정기도 검사기도 그것을 **보지 못했다**.
변이 시험도 크기만 흔들었지 자리는 흔들지 않았다.

## 이 파일의 검사는 무엇이 다른가 (19회차 개정)

`find_marks` 를 **부르지 않고**, 자리도 판정기의 창을 쓰지 않는다.
잉크 획 글리프 뭉치(`_glyph_clusters`)를 놓고 **방향을 가리지 않은 채**
가장 가까운 버블에 붙인다 — 반경은 이 문서가 답한 값(`AUDIT_REACH`)이고
판정기의 어느 창보다 **넓다**.  크기도 자리도 보지 않는다: 둘 다 검출기가
틀렸던 축이기 때문이다.

## 그리고 이 검사 자체를 두 축으로 검사한다

  · `..._made_blind`          크기를 일부러 멀게 만들면 잡는가
  · `..._made_blind_sideways` **자리를 옆으로 옮기면 잡는가** ← 19회차 신설

검사가 그때도 0 을 내면 그 검사는 16·18회차의 것과 같은 종류이므로 믿을 수
없다.

**이것이 방법론이다 — 검사는 검출기와 **모든** 축에서 다른 재료를 써야 하고,
축마다 검사가 실패할 수 있다는 것을 보여야 한다.**
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


# 검사의 반경.  **판정기의 어느 창보다 넓어야 한다** — 좁으면 검사가
# 판정기의 눈이 된다 (18회차가 그랬다).  값은 이 문서가 답했다: 마크에서
# 가장 가까운 버블까지의 체비쇼프 간격이 0~8pt 에 380개로 몰리고 **9~11pt 에
# 13개, 12~13pt 는 0개**다.  그 빈 띠 바깥의 21pt 무리(65개)까지 덮도록
# 판정기의 최대 창과 같은 25.0 을 쓴다 — 검사는 넓게 보고 사람이 가른다.
AUDIT_REACH = 25.0


def glyphs_near_bubbles(pc, lay, bubbles, reach=AUDIT_REACH):
    """버블 둘레의 잉크 획 글리프 — **크기도 방향도 보지 않는다.**

    ★ 19회차.  판정기의 창(`ds.in_mark_window`)을 **쓰지 않는다.**  그 창을
    쓰면 검사가 판정기와 같은 눈이 되고, 그것이 18회차가 이 세 장을 못 잡은
    이유다.  여기서는 방향을 가리지 않고 **가장 가까운 버블**에 붙인다.
    """
    import detect_symbols as ds
    out = []
    for c in ds._glyph_clusters(pc, lay):
        if c.x1 > lay.drawing_area[2]:
            continue
        cx, cy = (c.x0 + c.x1) / 2, (c.y0 + c.y1) / 2
        best = None
        for b in bubbles:
            dx = max(b.x0 - cx, cx - b.x1, 0.0)
            dy = max(b.y0 - cy, cy - b.y1, 0.0)
            gap = max(dx, dy)
            if gap <= reach and (best is None or gap < best[0]):
                best = (gap, b)
        if best is not None:
            out.append((c, best[1], cx, cy))
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
    for c, b, cx, cy in glyphs_near_bubbles(pc, lay, bubbles):
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


# 18회차까지의 마크 창 — 가로 6.0pt (`mark_x_slack`, 19회차에 사라진 값).
# 시험이 옛 판정기를 재현하는 자리이므로 숫자를 여기 그대로 둔다.
_OLD_X_SLACK = 6.0


def _above_only(rect, x, y, lay):
    """18회차까지의 마크 창 — **위 하나뿐**.

    이것이 그때 판정기와 감사가 **함께** 쓰던 식이다.  옆에 찍힌 별표는
    두 쪽 어디에도 안 보였고, 그래서 감사는 언제나 0 을 냈다.
    """
    return (rect.x0 - _OLD_X_SLACK <= x <= rect.x1 + _OLD_X_SLACK
            and rect.y0 - lay.mark_above <= y <= rect.y0)


@pytest.mark.slow
def test_the_audit_catches_a_detector_that_was_made_blind_sideways(monkeypatch):
    """**검사 자체를 검사한다 — 이번엔 자리 축이다 (19회차 신설).**

    검출기의 마크 창을 18회차의 것(**위 하나뿐**)으로 되돌린다.  별표는
    도면에 그대로 있고 크기도 그대로인데, 옆에 찍힌 것은 `drawn_mark_sizes`
    가 못 보므로 크기가 인정되지 않아 `find_marks` 에서 떨어진다.

    검사가 이것을 잡아야 한다.  못 잡으면 그 검사는 **자리 축에서 판정기와
    같은 눈**이고, 그것이 18회차의 감사가 p25·p27·p30 을 세 번째 지적까지
    못 잡은 이유다.
    """
    import detect_symbols as ds
    lay = ds.LAYOUT
    monkeypatch.setattr(ds, "in_mark_window", _above_only)
    caught = {}
    for pc in _pages():
        if not pc.analysis_scope:
            continue
        m = audit_page(pc, lay)
        if m:
            caught[pc.page_no] = len(m)
    assert caught, (
        "마크 창을 위 하나로 되돌렸는데도 검사가 아무것도 못 잡았다 — "
        "이 검사는 자리 축에서 검출기와 같은 재료를 쓰고 있다 (18회차가 그랬다)")


# 렌더로 확인한 **주인이 따로 있는 검출** — 버블 25pt 안에 잉크 획 글리프가
# 있는데 그 검출이 벤더가 아닌 것.  값은 (페이지, 건수) 이고 근거 캡처는
# `out/round19/8_캡처/` 에 있다.
#
#   p3   1   FE 아래 24.8pt                            (버블 것이 아님)
#   p7   5   PCV·MOV 의 **액추에이터**(돔 · M 원) 옆     p7_wide.png
#   p33  3   LG 옆 **사각 심볼**(삼각형 2개)의 것        p33_LI.png
#   p35  2   왼쪽 **밸브** 위의 별표 (옆 21.0pt)         p35_LIT21.png
#   p37  1   액추에이터의 **네모친 별표 심볼**            p37_TCV.png
#   p46  1   위쪽 **밸브** 아래 (옆 14.1pt)              p46_RO14.png
#   p47  1   같음                                        —
#   p49  1   같음                                        —
#
# ⚠ 이 목록은 "없다" 가 아니라 **"있고, 그 주인이 따로 있다"** 이다.
#   16·18회차가 "전수 0건" 이라고 적은 자리에 이 숫자를 둔다.
#   기준선(18회차 HEAD)에서는 **112건** 이었다.
UNCLAIMED_EXPLAINED = {3: 1, 7: 5, 33: 3, 35: 2, 37: 1, 46: 1, 47: 1, 49: 1}


def unclaimed_glyph_detections(pc, lay):
    """버블 둘레에 글리프가 있는데 **벤더로 판정되지 않은** 검출.

    ★ 19회차 신설.  `test_no_asterisk_in_a_mark_position_is_silently_dropped`
    는 **알아봤는가**(`find_marks` 가 세었나)를 묻고, 이것은 **붙었는가**를
    묻는다.  둘은 다른 질문이고, 4차 피드백이 지목한 p25·p30 은 **알아보기는
    했는데 안 붙은** 경우였다 — 그래서 18회차의 시험이 통과하면서도 별표가
    SCT 로 남았다.  같은 실수를 막으려면 두 질문을 다 물어야 한다.
    """
    import detect_symbols as ds
    dets, *_ = ds.detect(pc, lay=lay, rules=ds.RULESET_V3,
                         allow_glyph_sizes=ds.KNOWN_GLYPH_SIZES)
    if not dets:
        return []
    all_bubbles = ds.find_bubbles(pc, lay)
    pair = []
    for b in all_bubbles:
        for d in dets:
            if (b.x0 - 1 <= d.center[0] <= b.x1 + 1
                    and b.y0 - 1 <= d.center[1] <= b.y1 + 1):
                pair.append((b, d))
                break
    if not pair:
        return []
    with_glyph = {(round(b.x0, 1), round(b.y0, 1))
                  for _c, b, _x, _y in glyphs_near_bubbles(
                      pc, lay, [b for b, _ in pair])}
    return [(round(b.x0, 1), round(b.y0, 1))
            for b, d in pair
            if (round(b.x0, 1), round(b.y0, 1)) in with_glyph
            and not d.evidence.get("vendor_mark")]


@pytest.mark.slow
def test_every_glyph_beside_a_bubble_is_claimed_or_explained():
    """버블 옆의 글리프가 **아무에게도 안 붙는** 일이 조용히 늘지 않는다.

    16·18회차는 이 자리에 "전수 0건" 을 적었다.  그 값은 판정 함수에게
    되물어 나온 것이었고, 실제로는 기준선에서 **112건**이 붙지 않고 있었다.
    지금 남은 것은 `UNCLAIMED_EXPLAINED` 뿐이고 그 한 건씩을 렌더로 확인했다 —
    전부 밸브 · 액추에이터 · 옆 사각 심볼의 마크다.
    """
    import detect_symbols as ds
    lay = ds.LAYOUT
    got = {}
    for pc in _pages():
        if not pc.analysis_scope:
            continue
        m = unclaimed_glyph_detections(pc, lay)
        if m:
            got[pc.page_no] = len(m)
    assert got == UNCLAIMED_EXPLAINED, (
        "붙지 않은 글리프의 내역이 달라졌다 — 실측 " + str(got)
        + " · 렌더로 확인해 둔 것 " + str(UNCLAIMED_EXPLAINED))
