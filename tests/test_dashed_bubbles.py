"""40회차 — 파선으로 그린 버블을 그 장의 실선 버블 크기로 세운다.

UAD 벤더 스키드 안 계기(LIT·PDIT·PI 48행)의 버블은 2~3pt 직선 토막으로 그려져
`c` 캡이 없다.  상수는 없다 — 토막 상한·틈·크기 전부 그 장에서 읽는다.
"""
import math
import pymupdf
import pytest

from app.engine import detect_symbols as ds


def _stadium_dashes(page, x0, y0, w, h, dash=2.4, gap=1.8):
    """가로 스타디움을 파선 토막(각각 짧은 폴리라인)으로 그린다."""
    r = h / 2
    # 옆면 둘
    for y in (y0, y0 + h):
        x = x0 + r
        while x + dash <= x0 + w - r:
            sh = page.new_shape(); sh.draw_polyline([(x, y), (x + dash / 2, y), (x + dash, y)]); sh.finish(width=0.3); sh.commit()
            x += dash + gap
    # 캡 둘 — 호를 3점 폴리라인 토막으로
    for cx, a0 in ((x0 + r, math.pi / 2), (x0 + w - r, -math.pi / 2)):
        cy = y0 + r
        step = (dash + gap) / r
        a = a0
        while a < a0 + math.pi:
            pts = [(cx + r * math.cos(a + k * step * 0.4 * (dash / (dash + gap))),
                    cy + r * math.sin(a + k * step * 0.4 * (dash / (dash + gap)))) for k in range(3)]
            sh = page.new_shape(); sh.draw_polyline(pts); sh.finish(width=0.3); sh.commit()
            a += step


def _solid_stadium(page, x0, y0, w, h):
    r = h / 2
    sh = page.new_shape()
    sh.draw_line((x0 + r, y0), (x0 + w - r, y0)); sh.finish(width=0.3)
    sh.draw_line((x0 + r, y0 + h), (x0 + w - r, y0 + h)); sh.finish(width=0.3)
    sh.commit()
    for cx, side in ((x0 + r, -1), (x0 + w - r, 1)):
        sh = page.new_shape()
        # 반원 캡 (베지어 둘)
        c = (cx, y0 + r)
        sh.draw_sector(c, (cx, y0), 180 if side < 0 else -180)
        sh.finish(width=0.3, closePath=False); sh.commit()


@pytest.fixture
def page_with_both(tmp_path):
    doc = pymupdf.open(); page = doc.new_page(width=600, height=400)
    for i in range(3):
        _solid_stadium(page, 60 + i * 60, 60, 34, 11)
    _stadium_dashes(page, 300, 200, 34, 11)
    _stadium_dashes(page, 400, 200, 34, 11)
    path = tmp_path / "dashed.pdf"; doc.save(path); doc.close()
    from app.engine import pidcache
    _d, pages = pidcache.load_pages(str(path))
    return pages[0]


def test_dashed_stadiums_are_found_at_the_solid_size(page_with_both):
    pc = page_with_both
    solid = ds.bubble_outlines(pc)
    assert len(solid) >= 3
    dashed = ds.dashed_bubble_outlines(pc, solid)
    assert len(dashed) == 2
    for o in dashed:
        assert o.style == "DASHED"
        assert abs(o.rect.width - 34) <= 4 and abs(o.rect.height - 11) <= 4


def test_no_solid_bubble_means_no_dashed_guess(tmp_path):
    doc = pymupdf.open(); page = doc.new_page(width=600, height=400)
    _stadium_dashes(page, 300, 200, 34, 11)
    path = tmp_path / "only_dashed.pdf"; doc.save(path); doc.close()
    from app.engine import pidcache
    _d, pages = pidcache.load_pages(str(path))
    assert ds.dashed_bubble_outlines(pages[0], []) == []


def test_outline_default_style_is_solid():
    r = pymupdf.Rect(0, 0, 10, 4)
    o = ds.Outline(r, "H", r, r)
    assert o.style == "SOLID"


def test_gap_is_read_from_the_page_not_a_constant(page_with_both):
    pieces = ds._dash_pieces(page_with_both, 11.4)
    gap = ds._endpoint_gap_mode(pieces)
    assert 1.5 <= gap <= 2.2      # 합성 파선의 틈 1.8 — 페이지에서 읽힌다
