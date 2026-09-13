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
            sh = page.new_shape(); sh.draw_polyline([(x, y), (x + dash / 2, y), (x + dash, y)]); sh.finish(width=0.3, closePath=False); sh.commit()
            x += dash + gap
    # 캡 둘 — 호를 3점 폴리라인 토막으로
    for cx, a0 in ((x0 + r, math.pi / 2), (x0 + w - r, -math.pi / 2)):
        cy = y0 + r
        step = (dash + gap) / r
        a = a0
        while a < a0 + math.pi:
            pts = [(cx + r * math.cos(a + k * step * 0.4 * (dash / (dash + gap))),
                    cy + r * math.sin(a + k * step * 0.4 * (dash / (dash + gap)))) for k in range(3)]
            sh = page.new_shape(); sh.draw_polyline(pts); sh.finish(width=0.3, closePath=False); sh.commit()
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
        sh.draw_sector(c, (cx, y0), 180 if side < 0 else -180, fullSector=False)
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


def test_rotated_page_puts_dashed_bubbles_where_the_words_are(tmp_path):
    """★ 40회차 결함 — 파선 토막을 `d["rect"]`(회전 전)로 읽으면 270° 장(UAD)에서
    사각형이 낱말과 다른 자리에 서서 검출이 0 이 된다.  회전 장에서도 파선 윤곽이
    회전 0 장과 같은 **표시 좌표**에 서야 한다."""
    doc = pymupdf.open(); page = doc.new_page(width=600, height=400)
    for i in range(3):
        _solid_stadium(page, 60 + i * 60, 60, 34, 11)
    _stadium_dashes(page, 300, 200, 34, 11)
    page.set_rotation(270)
    path = tmp_path / "rot.pdf"; doc.save(path); doc.close()
    from app.engine import pidcache
    _d, pages = pidcache.load_pages(str(path))
    pc = pages[0]
    solid = ds.bubble_outlines(pc)
    dashed = ds.dashed_bubble_outlines(pc, solid)
    assert len(dashed) == 1
    # 표시 좌표에서의 자리: 회전 270° 는 (x, y) → (y, W - x) 꼴이므로 스타디움이 세로가 된다
    r = dashed[0].rect
    assert dashed[0].axis == "V" and abs(r.height - 34) < 3 and abs(r.width - 11) < 3
    exp = pymupdf.Rect(300, 200, 334, 211) * pc.page.rotation_matrix
    assert abs(r.x0 - exp.x0) < 3 and abs(r.y0 - exp.y0) < 3


def test_unique_endpoint_linking_matches_pairwise_rule():
    """41회차 — 유일점으로 접어도 "어느 끝점이든 tol 안이면 같은 성분" 과 같은 성분이 나온다.
    꼭짓점을 공유하는 토막(SHX 획 꼴)과 떨어진 토막을 섞어 두 방법을 맞댄다."""
    import random
    rng = random.Random(41)
    pieces = []
    for _ in range(60):
        x, y = rng.uniform(0, 100), rng.uniform(0, 100)
        pieces.append(((x, y), (x + 1.0, y), pymupdf.Rect(x, y, x + 1, y + 0.01)))
        pieces.append(((x, y), (x, y + 1.0), pymupdf.Rect(x, y, x + 0.01, y + 1)))   # 같은 꼭짓점
    tol = 1.2
    comp = ds._link_pieces(pieces, tol)
    got = sorted(sorted(v) for v in comp.values())
    # 기준: 쌍별 규칙을 그대로 (느리지만 정의 그대로)
    n = len(pieces); parent = list(range(n))
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for i in range(n):
        for j in range(i + 1, n):
            if any(math.hypot(p[0] - q[0], p[1] - q[1]) <= tol for p in pieces[i][:2] for q in pieces[j][:2]):
                parent[find(j)] = find(i)
    ref = {}
    for i in range(n):
        ref.setdefault(find(i), []).append(i)
    assert got == sorted(sorted(v) for v in ref.values())


def test_gap_mode_ignores_shared_vertices_like_before():
    """주인이 둘 이상인 유일점의 끝점은 다른 토막이 거리 0 에 있으므로 최빈에 안 든다 —
    옛 계산(끝점마다 가장 가까운 다른 토막 끝점 · 0.3 초과)과 같은 값."""
    pieces = []
    for k in range(10):                       # 파선 열: 길이 2 · 틈 1.5
        x = k * 3.5
        pieces.append(((x, 0.0), (x + 2.0, 0.0), pymupdf.Rect(x, 0, x + 2, 0.01)))
    for k in range(5):                        # 꼭짓점을 공유하는 획 쌍 (글자)
        x, y = 50 + k * 4, 20.0
        pieces.append(((x, y), (x + 1, y), pymupdf.Rect(x, y, x + 1, y + 0.01)))
        pieces.append(((x, y), (x, y + 1), pymupdf.Rect(x, y, x + 0.01, y + 1)))
    assert ds._endpoint_gap_mode(pieces) == 1.5
