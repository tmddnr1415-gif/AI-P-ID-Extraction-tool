"""hotfix73 — 속도를 위해 바꾼 색인이 예전과 **같은 값**을 낸다 (회전 장 · 회전 없는 장).

`_leader_index` · `_ink_index` 는 직선을 점마다 다시 옮기던 것을 `pc.segments()`(이미 옮긴 것)로
바꿨다.  예전 방식을 이 시험 안에 그대로 두고 칸마다 맞댄다."""
from __future__ import annotations

import collections
import sys
from pathlib import Path

import pymupdf
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app" / "engine"))
import detect_symbols as ds  # noqa: E402
import detect_valves as dv  # noqa: E402
import pidcache  # noqa: E402


def _page(tmp_path, rot):
    d = pymupdf.open()
    pg = d.new_page(width=1191, height=842)
    for i in range(40):
        pg.draw_line((20 + i * 13.3, 30 + i * 7.1), (300 + i * 9.7, 500 - i * 3.3))
    pg.draw_bezier((100, 100), (150, 50), (200, 150), (250, 100))
    pg.draw_rect(pymupdf.Rect(400, 300, 470, 340))
    pg.draw_quad(pymupdf.Rect(600, 600, 650, 640).quad)
    pg.set_rotation(rot)
    p = tmp_path / f"r{rot}.pdf"
    d.save(p)
    _doc, pcs = pidcache.load_pages(p)
    return _doc, pcs[0]


def _old_leader(pc, cell):
    R = pidcache.Rot(pc.page.rotation_matrix)
    grid = collections.defaultdict(list)
    for d in pc.drawings():
        for it in d["items"]:
            if it[0] != "l":
                continue
            a, c = R.pt(it[1]), R.pt(it[2])
            for p in (a, c):
                grid[(int(p.x // cell), int(p.y // cell))].append((a, c))
    return grid


def _key(seg):
    a, b = seg
    return (repr(a.x), repr(a.y), repr(b.x), repr(b.y))


@pytest.mark.parametrize("rot", [0, 90, 270])
def test_leader_index_matches_point_by_point(tmp_path, rot):
    _doc, pc = _page(tmp_path, rot)
    new, old = dv._leader_index(pc, 25.0), _old_leader(pc, 25.0)
    assert set(new) == set(old)
    for k in old:
        assert [_key(s) for s in new[k]] == [_key(s) for s in old[k]]


@pytest.mark.parametrize("rot", [0, 270])
def test_ink_index_holds_the_same_segments(tmp_path, rot):
    _doc, pc = _page(tmp_path, rot)
    m = pc.page.rotation_matrix
    new = ds._ink_index(pc, m, 10.0)
    R = pidcache.Rot(m)
    old = collections.defaultdict(list)
    for d in pc.drawings():
        for it in d["items"]:
            if it[0] == "l":
                a, b = R.pt(it[1]), R.pt(it[2])
            elif it[0] == "c":
                a, b = R.pt(it[1]), R.pt(it[4])
            elif it[0] == "qu":
                a, b = R.pt(it[1].ul), R.pt(it[1].lr)
            elif it[0] == "re":
                r = R.rect(it[1])
                for a, b in ((r.tl, r.tr), (r.tr, r.br), (r.br, r.bl), (r.bl, r.tl)):
                    ds._index_put(old, a, b, 10.0)
                continue
            else:
                continue
            ds._index_put(old, a, b, 10.0)
    assert set(new) == set(old)
    for k in old:   # 칸 안의 순서는 답(`_touches` — 하나라도 닿나)과 무관하다 — 모음으로 맞댄다
        assert sorted(e[2] for e in new[k]) == sorted(e[2] for e in old[k])


@pytest.mark.parametrize("rot", [0, 270])
def test_strokes_in_and_stroke_index_are_unchanged(tmp_path, rot):
    import legend_rules
    _doc, pc = _page(tmp_path, rot)
    lay = dv.ValveLayout()
    for rect in (pymupdf.Rect(0, 0, 600, 600), pymupdf.Rect(50, 40, 260, 300), pymupdf.Rect(390, 290, 480, 350)):
        old = []
        for p0, p1 in pc.segments():
            if not (rect.x0 - 0.3 <= min(p0.x, p1.x) and max(p0.x, p1.x) <= rect.x1 + 0.3
                    and rect.y0 - 0.3 <= min(p0.y, p1.y) and max(p0.y, p1.y) <= rect.y1 + 0.3):
                continue
            dx, dy = p1.x - p0.x, p1.y - p0.y
            length = (dx * dx + dy * dy) ** 0.5
            if length < 0.8 or length > max(rect.width, rect.height) * 1.1:
                continue
            old.append((p0, p1, abs(dx), abs(dy), length))
        assert dv._strokes_in(pc, rect, lay) == old
    a = legend_rules.stroke_index(pc.segments(), min_len=1.0)
    a[0]["mutated by a caller"] = [(0, 1)]                  # 한 호출자가 고쳐도
    b = legend_rules.stroke_index(pc.segments(), min_len=1.0)
    c = legend_rules._stroke_index(pc.segments(), 0.4, 1.0)
    assert "mutated by a caller" not in b[0]               # 다음 호출자에게 새지 않는다
    assert dict(b[0]) == dict(c[0]) and dict(b[1]) == dict(c[1])
    legend_rules.release_stroke_memo(); dv.release_strokes()
