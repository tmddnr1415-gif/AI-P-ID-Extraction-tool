"""25회차 — 별표를 **획의 관계**로 읽는다 (§9).

두 문서의 실측을 합성 PDF 로 재현한다:
  · TC2 는 별표의 획 넷(╲ ╱ │ ─)을 각각 **별개 path** 로 그린다 → 예전 `_glyph_clusters`
    는 세로·가로획을 "납작하다" 며 뭉치기 전에 버렸다.
  · 밸브 나비의 두 대각선도 중심에서 교차한다 → "한 점에서 만난다" 만으로는 별표와
    같다.  가르는 것은 **획 끝이 아무 데도 닿지 않는다** 는 것이다.
"""
import sys
from pathlib import Path

import pymupdf
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app" / "engine"))

import detect_symbols as ds   # noqa: E402
import pidcache               # noqa: E402


def _page_with(tmp_path, draw):
    doc = pymupdf.open()
    page = doc.new_page(width=600, height=400)
    draw(page)
    path = tmp_path / "s.pdf"
    doc.save(path)
    doc.close()
    _d, pages = pidcache.load_pages(path)
    return pages[0]


def _star(page, cx, cy, r):
    """획 넷을 **따로** 그린 별표 (TC2 방식)."""
    for (dx, dy) in ((r, 0), (0, r), (r, r), (r, -r)):
        page.draw_line(pymupdf.Point(cx - dx, cy - dy), pymupdf.Point(cx + dx, cy + dy),
                       width=0.3)


def _bowtie(page, cx, cy, w, h):
    """밸브 나비 — 두 대각선이 중심에서 만나고 끝은 세로변에 닿는다."""
    page.draw_line(pymupdf.Point(cx - w, cy - h), pymupdf.Point(cx + w, cy + h), width=0.3)
    page.draw_line(pymupdf.Point(cx - w, cy + h), pymupdf.Point(cx + w, cy - h), width=0.3)
    page.draw_line(pymupdf.Point(cx - w, cy - h), pymupdf.Point(cx - w, cy + h), width=0.3)
    page.draw_line(pymupdf.Point(cx + w, cy - h), pymupdf.Point(cx + w, cy + h), width=0.3)


def test_a_star_drawn_stroke_by_stroke_is_one_group(tmp_path):
    pc = _page_with(tmp_path, lambda pg: _star(pg, 100, 100, 1.4))
    groups = ds.star_groups(pc, ds.LAYOUT, maxlen=11.0)
    assert len(groups) == 1
    rect, strokes, dirs = groups[0]
    assert strokes == 4 and dirs >= 2
    assert abs(rect.width - 2.8) < 0.2 and abs(rect.height - 2.8) < 0.2


def test_a_valve_bowtie_is_not_a_star(tmp_path):
    """대각선이 한 점에서 만나지만 끝이 세로변에 닿는다 → 별표가 아니다."""
    pc = _page_with(tmp_path, lambda pg: _bowtie(pg, 200, 100, 8, 4))
    assert ds.star_groups(pc, ds.LAYOUT, maxlen=30.0) == []


def test_the_old_cluster_rule_still_misses_the_stroke_by_stroke_star(tmp_path):
    """가산인 이유 — 예전 규칙은 이 별표를 못 본다 (납작한 획을 먼저 버린다)."""
    pc = _page_with(tmp_path, lambda pg: _star(pg, 100, 100, 1.4))
    assert [c for c in ds._glyph_clusters(pc, ds.LAYOUT)
            if abs((c.x0 + c.x1) / 2 - 100) < 3] == []


def test_no_absolute_size_in_the_star_rule():
    """§9 ② — 상한은 부르는 쪽이 그 장에서 주고, 허용치는 비율이다."""
    import inspect
    src = inspect.getsource(ds.star_groups)
    assert "0.25 * min(" in src            # 획 길이의 비율
    assert "if not maxlen or maxlen <= 0" in src   # 상한이 없으면 아무것도 안 낸다
    src2 = inspect.getsource(ds.star_marks)
    assert "min(b.width, b.height)" in src2        # 상한 = 그 장 버블의 짧은 변


# --------------------------------------------------------------------------
# 26회차 — 정의줄과 본문이 **다르게 그린** 문서 (TC2 실측 모양)
# --------------------------------------------------------------------------
def _sheet_like_tc2(tmp_path):
    """정의줄은 2획 별표 + `By SE`, 본문은 4획 별표 두 개가 버블 위에.

    실측 그대로다 — TC2 는 정의줄을 (2획 1.8×1.7pt), 본문을 (4획 2.9×2.9pt) 로
    그린다.  25회차는 "정의줄 획 수와 같아야 한다" 를 조건으로 두어 **본문
    별표를 전부 버렸다** (254개 중 174개 · `out/round25_tc2_scope_defect.md`).
    """
    doc = pymupdf.open()
    page = doc.new_page(width=2384, height=1684)      # 기본 Layout 의 종이
    page.insert_text(pymupdf.Point(2000, 104), "By SE", fontsize=8)
    _star(page, 1990, 100, 0.9)                        # 정의줄 별표 — 2획이 되게
    page.draw_line(pymupdf.Point(1989.1, 100), pymupdf.Point(1990.9, 100), width=0.3)
    for cx in (300, 500):
        _star(page, cx, 300, 1.4)                      # 본문 별표 — 4획
    path = tmp_path / "tc2like.pdf"
    doc.save(path)
    doc.close()
    _d, pages = pidcache.load_pages(path)
    return pages[0]


def _bubbles_under(cxs, cy):
    return [pymupdf.Rect(cx - 17, cy + 6, cx + 17, cy + 17.4) for cx in cxs]


def test_the_body_star_survives_a_definition_line_drawn_differently(tmp_path):
    """★ 26회차 회귀 — 정의줄의 획 수로 본문을 거르지 않는다."""
    pc = _sheet_like_tc2(tmp_path)
    marks = ds.star_marks(pc, ds.LAYOUT, bubbles=_bubbles_under((300, 500), 300))
    assert len(marks) == 2


def test_a_definition_star_drawn_with_strokes_is_read_into_the_dictionary(tmp_path):
    """★ 26회차 — `* By SE` 를 획으로 그려도 뜻을 읽는다 (사전이 비면 이름이 없다)."""
    pc = _sheet_like_tc2(tmp_path)
    dictionary, glyph_size = ds.read_mark_dictionary(pc, ds.LAYOUT)
    assert dictionary == {1: "By SE"}
    # 획으로 그린 정의줄은 **뜻만** 준다 — 그 크기는 본문의 크기가 아니다.
    assert glyph_size is None


def test_the_supplier_name_is_read_whatever_the_case(tmp_path):
    """도면이 `By SE` 라고 소문자로 적어도 이름은 `SE` 다 (자리 규칙은 그대로)."""
    sys.path.insert(0, str(ROOT))
    from app import pipeline
    assert pipeline._supplier_name("By SE") == "SE"
    assert pipeline._supplier_name("DENOTES EQUIPMENT WILL BE SUPPLIED BY HRSG.") == "HRSG"


def test_a_mark_whose_named_supplier_is_us_is_our_scope(tmp_path):
    """★ 26회차 — `BY SCT` 로 정의된 표시는 타사 공급이 아니다 (TC2 p12 실측 2행)."""
    sys.path.insert(0, str(ROOT))
    from app import pipeline

    class _D:
        rules_hit = ["VENDOR_MARK_GLYPH"]
        evidence = {"vendor_mark": {"meaning": "BY SCT"}}

    class _E:
        rules_hit = ["VENDOR_MARK_GLYPH"]
        evidence = {"vendor_mark": {"meaning": "SUPPLIED BY HRSG."}}

    assert pipeline._scope_of(_D()) == "SCT"
    assert pipeline._scope_of(_E()) == "VENDOR(HRSG)"


# --------------------------------------------------------------------------
# 26회차 — **재현율**을 묻는 검사 (25회차가 안 물어서 세 번째로 같은 지적이 왔다)
# --------------------------------------------------------------------------
#
# 25회차는 "더한 마크가 전부 별표인가"(정밀도)만 재고 접촉 시트로 확인했다.
# 접촉 시트는 **찾은 것만** 보여 주므로 못 찾은 것을 드러낼 수 없다.  여기서는
# 반대를 묻는다 — **그 장이 인쇄한 별표 중 몇 개를 마크로 냈는가.**
#
# 후보를 찾는 채널은 검출기와 **다르다**: `star_groups` 를 부르지 않고, 자유
# 끝점도 크기 학습도 보지 않고, 짧은 곧은 획의 중점이 겹치는 무리를 셋 이상만
# 모은다 (밸브 나비는 중심에 중점이 둘뿐이라 빠진다).
TC2 = ROOT / "data" / "TC2_260821.pdf"


def _midpoint_clusters(pc, maxlen):
    """중점이 겹치는 짧은 획 무리 — 검출기의 함수를 하나도 부르지 않는다.

    별표의 **모양**만 본다: 팔이 셋 이상 방향으로 뻗고(15° 칸) 길이가 서로 같다.
    검출기가 쓰는 것(자유 끝점 · 그 장에서 배운 크기)은 **일부러 안 본다** —
    같은 축을 쓰면 검사가 검출기의 눈이 된다 (18·19회차).

    실측(TC2 p6): 실제 별표 9개는 전부 방향 3~4 · 길이비 1.02~1.06 이고,
    해칭 무리(밸브의 검은 점 · 유량계 몸통)는 방향 1~2 이거나 길이비 1.17 이상이다.
    """
    import math
    m = pc.page.rotation_matrix
    segs = []
    for d in pc.drawings():
        for it in d["items"]:
            if it[0] != "l":
                continue
            a, b = it[1] * m, it[2] * m
            ln = math.hypot(b.x - a.x, b.y - a.y)
            if 0 < ln <= maxlen:
                segs.append(((a.x + b.x) / 2, (a.y + b.y) / 2, ln,
                             int(math.degrees(math.atan2(b.y - a.y, b.x - a.x))
                                 % 180 // 15)))
    segs.sort()
    out, used = [], [False] * len(segs)
    for i, s in enumerate(segs):
        if used[i]:
            continue
        group = [i]
        for j in range(i + 1, len(segs)):
            if used[j] or segs[j][0] - s[0] > maxlen:
                break
            tol = 0.25 * min(s[2], segs[j][2])
            if math.hypot(segs[j][0] - s[0], segs[j][1] - s[1]) <= tol:
                group.append(j)
        if len(group) < 3:
            continue
        for j in group:
            used[j] = True
        lens = [segs[j][2] for j in group]
        if len({segs[j][3] for j in group}) >= 3 and max(lens) / min(lens) <= 1.1:
            out.append((s[0], s[1], len(group)))
    return out


# 렌더로 확인한 것 (19회차 방법론 — "전수 0건" 이라고 적지 않고 한 건씩 본다):
# 방향·길이비 조건 전에는 밸브의 **검은 점 해칭**과 유량계 몸통이 이 채널에 잡혔다
# (`out/round26/p6_unclaimed.png`).  둘 다 별표가 아니고 검출기는 자유 끝점 조건으로
# 옳게 걸렀다.  조건을 넣은 뒤 p6 에서 남는 것은 **실제 별표뿐**이다.


@pytest.mark.slow
@pytest.mark.skipif(not TC2.exists(), reason="TC2 PDF not present")
def test_every_asterisk_a_tc2_page_prints_becomes_a_mark():
    """★ 26회차 회귀 — 현장 보고가 지목한 그 장(p6)에서 별표를 하나도 안 놓친다."""
    marks, printed = _tc2_page6_marks()
    # 이 채널은 **아래로만 틀린다** — 검출기는 이 장에서 마크 11개를 내고 그중
    # 9개가 버블에 붙는데, 여기서는 모양 조건이 더 좁아 7개가 남는다.  검사는
    # 하한이지 인구조사가 아니다 (실측 7 — 하나라도 줄면 규칙이 좁아진 것이다).
    assert len(printed) >= 7, printed
    for cx, cy, _n in printed:
        assert any(abs(m.x - cx) < 1.0 and abs(m.y - cy) < 1.0 for m in marks), (cx, cy)


@pytest.mark.slow
@pytest.mark.skipif(not TC2.exists(), reason="TC2 PDF not present")
def test_the_recall_check_catches_the_definition_line_gate(monkeypatch):
    """검사 자체를 검사한다 — 25회차의 조건을 되살리면 이 검사가 잡는가.

    잡지 못하면 이 검사는 25회차의 접촉 시트와 같은 종류이므로 믿을 수 없다.
    """
    real = ds.star_groups

    def gated(pc, lay=ds.LAYOUT, maxlen=0.0, region=None):
        groups = real(pc, lay, maxlen, region)
        if region is not None:
            return groups
        defn = [g for g in real(pc, lay, maxlen,
                                region=__import__("pymupdf").Rect(*lay.notes_area))]
        return [g for g in groups if not defn or g[1] == defn[0][1]]

    monkeypatch.setattr(ds, "star_groups", gated)
    marks, printed = _tc2_page6_marks()
    missed = [p for p in printed
              if not any(abs(m.x - p[0]) < 1.0 and abs(m.y - p[1]) < 1.0 for m in marks)]
    assert missed, "게이트를 되살렸는데 검사가 아무것도 못 잡았다"


def _tc2_page6_marks():
    """★ config 를 **되돌린다** (22회차).

    이 시험은 TC2 의 좌표를 전역 `CFG` 에 얹는데, 되돌리지 않으면 같은
    프로세스에서 뒤에 도는 AL NOUF1 시험이 **남의 좌표로** 돈다.  실제로
    26회차 slow 스위트에서 벤더 마크 감사 두 건이 그렇게 깨졌다 — 제품이
    아니라 이 시험의 결함이었다 (`analyse` 는 `finally` 로 되돌린다).
    """
    import copy

    sys.path.insert(0, str(ROOT))
    import derive_layout as dl
    from app import pipeline
    snapshot = copy.deepcopy(pipeline.CFG.data)
    try:
        return _tc2_page6_marks_inner(dl, pipeline)
    finally:
        if pipeline.CFG.data != snapshot:
            pipeline.CFG.data = snapshot
            pipeline._rebind_config()


def _tc2_page6_marks_inner(dl, pipeline):
    _doc, pages = pidcache.load_pages(TC2)
    pipeline.CFG.overlay(dl.derive(pages, pipeline.CFG).values())
    pipeline._rebind_config()
    lay = ds.LAYOUT
    pc = [p for p in pages if p.page_no == 6][0]
    bubbles = ds.find_bubbles(pc, lay)
    dct, gsize = ds.read_mark_dictionary(pc, lay)
    marks = ds.find_marks(pc, lay, glyph_size=gsize if isinstance(gsize, tuple) else None,
                          allow_sizes=ds.KNOWN_GLYPH_SIZES, bubbles=bubbles)
    short = sorted(min(b.width, b.height) for b in bubbles)
    printed = [c for c in _midpoint_clusters(pc, short[len(short) // 2])
               if any(ds.in_mark_window(b, c[0], c[1], lay) for b in bubbles)]
    return marks, printed
