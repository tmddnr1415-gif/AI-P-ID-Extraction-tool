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
