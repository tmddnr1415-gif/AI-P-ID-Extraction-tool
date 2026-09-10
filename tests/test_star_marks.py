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
