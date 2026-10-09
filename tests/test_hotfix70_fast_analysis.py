"""hotfix70 — 분석을 빠르게, 답은 그대로.

TC2 프로파일(spike/analysis_profile.py · out/hotfix70)에서 시간이 판정이 아니라 **같은 값을 비싸게 다시
만드는 데** 갔다.  고친 넷은 전부 "같은 답" 을 보장하는 변환이고, 여기서 그 보장을 하나씩 못박는다:

  1. 회전 곱 `Point * m` · `Rect * m` → `pidcache.Rot` (PyMuPDF 의 float 계산과 비트까지 같다).
  2. 칠한 상자(`_highlights`)는 장 캐시의 그림에서 — PDF 를 글자 갈래마다 다시 읽지 않는다.
  3. 잉크 인덱스는 선분을 **끝점 칸**에만 넣는다 — 읽는 쪽이 끝점 거리만 잰다.
  4. Typical 표식의 "선이 닿는가" 는 닿을 수 있는 선분만 훑는다.
  5. 마크·별표 찾기의 잉크 획 걸러내기는 장마다 한 번.
"""
from __future__ import annotations

import collections
import math
import random
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "app" / "engine")]

import pidcache  # noqa: E402
import detect_symbols as ds  # noqa: E402


def _f32(v):
    return pidcache._f32(v)


# ---------------------------------------------------------------- 1. 회전 곱
def test_rot_matches_pymupdf_bit_for_bit_on_every_page_rotation():
    assert pidcache._ROT_OK, "이 PyMuPDF 판본에서 빠른 길이 꺼졌다 — 값은 같지만 느리다"
    rng = random.Random(7)
    doc = pymupdf.open()
    for rot in (0, 90, 180, 270):
        pg = doc.new_page(width=1190.55, height=841.89)
        pg.set_rotation(rot)
        m = pg.rotation_matrix
        R = pidcache.Rot(m)
        assert R.fast
        for _ in range(500):
            x, y = _f32(rng.uniform(-10, 2400)), _f32(rng.uniform(-10, 2400))
            p = pymupdf.Point(x, y)
            a, b = pymupdf.Point(p) * m, R.pt(p)
            assert type(a) is type(b) and (repr(a.x), repr(a.y)) == (repr(b.x), repr(b.y))
            r = pymupdf.Rect(x, y, _f32(x + rng.uniform(-5, 60)), _f32(y + rng.uniform(-5, 60)))
            ra, rb = pymupdf.Rect(r) * m, R.rect(r)
            assert type(ra) is type(rb) and vars(ra) == vars(rb) and tuple(map(repr, ra)) == tuple(map(repr, rb))
        pts = [pymupdf.Point(_f32(rng.uniform(-10, 2400)), _f32(rng.uniform(-10, 2400))) for _ in range(400)]
        pairs = list(zip(pts[::2], pts[1::2])) + [(pymupdf.Point(0.0, -0.0), pymupdf.Point(-0.0, 0.0))]
        for (p, q), (u, v) in zip(R.segs(pairs), [(pymupdf.Point(p) * m, pymupdf.Point(q) * m) for p, q in pairs]):
            for a, b in ((p, u), (q, v)):
                assert type(a) is type(b) and vars(a) == vars(b) and (repr(a.x), repr(a.y)) == (repr(b.x), repr(b.y))


def test_rot_falls_back_for_a_matrix_that_is_not_a_page_rotation():
    m = pymupdf.Matrix(0.5, 0.2, -0.3, 1.5, 3.25, 7.75)
    R = pidcache.Rot(m)
    assert not R.fast
    p = pymupdf.Point(12.3, 45.6)
    assert tuple(R.pt(p)) == tuple(p * m)


def test_hot_call_sites_use_rot_not_pymupdf_multiplication():
    src = {n: (ROOT / "app/engine" / n).read_text(encoding="utf-8")
           for n in ("pidcache.py", "detect_symbols.py", "detect_valves.py", "legend_rules.py")}
    assert 'd["bbox"] = R.rect(d["rect"])' in src["pidcache.py"]
    assert "self._segments = Rot(m).segs(" in src["pidcache.py"]
    for name in ("detect_symbols.py", "detect_valves.py"):
        assert "it[1] * m" not in src[name], name
    assert "pymupdf.Point(it[1]) * m" not in src["legend_rules.py"]


# ---------------------------------------------------------------- 2. 칠한 상자
def test_highlights_read_the_page_cache_not_the_pdf_again():
    for name in ("derive_layout.py", "detect_all.py"):
        s = (ROOT / "app/engine" / name).read_text(encoding="utf-8")
        seg = s[s.index("def _highlights(pc)"):]
        seg = seg[:seg.index("\n    return out")]
        assert "pc.drawings()" in seg and "page.get_drawings()" not in seg, name
    s = (ROOT / "app/engine/derive_layout.py").read_text(encoding="utf-8")
    assert "boxes_of = [_highlights(pc) for pc in pages]" in s      # 글자 갈래마다가 아니라 장마다 한 번


# ---------------------------------------------------------------- 3. 끝점 칸 인덱스
def _old_index_put(grid, a, b, cell):
    key = (round(a.x, 2), round(a.y, 2), round(b.x, 2), round(b.y, 2))
    for gx in range(int(min(a.x, b.x) // cell), int(max(a.x, b.x) // cell) + 1):
        for gy in range(int(min(a.y, b.y) // cell), int(max(a.y, b.y) // cell) + 1):
            grid[(gx, gy)].append((a, b, key))


def test_endpoint_index_gives_the_same_touch_answers_as_the_full_span_index():
    rng = random.Random(70)
    for cell in (1.1, 4.2, 11.4):
        old, new = collections.defaultdict(list), collections.defaultdict(list)
        segs = []
        for _ in range(600):
            a = pymupdf.Point(rng.uniform(-20, 300), rng.uniform(-20, 300))
            L = rng.choice((0.5, 3.0, 40.0, 250.0))
            t = rng.uniform(0, 2 * math.pi)
            b = pymupdf.Point(a.x + L * math.cos(t), a.y + L * math.sin(t))
            segs.append((a, b))
            _old_index_put(old, a, b, cell)
            ds._index_put(new, a, b, cell)
        assert sum(map(len, new.values())) < sum(map(len, old.values()))
        keys = [(round(a.x, 2), round(a.y, 2), round(b.x, 2), round(b.y, 2)) for a, b in segs]
        for _ in range(3000):
            p = pymupdf.Point(rng.uniform(-30, 310), rng.uniform(-30, 310))
            tol = rng.choice((0.3, 1.0, 2.5, 9.0))
            own = set(rng.sample(keys, 5))
            assert ds._touches(old, p, tol, own, cell) == ds._touches(new, p, tol, own, cell)


# ---------------------------------------------------------------- 4. Typical 사전 거르기
def test_typical_scans_only_segments_that_can_touch():
    s = (ROOT / "app/engine/typical.py").read_text(encoding="utf-8")
    seg = s[s.index("def circle_marks("):s.index("def _tokens(")]
    assert "half = max(rad, pad.width / 2, pad.height / 2) + 1.0" in seg
    assert seg.count("for a, b in cand)") == 2 and "for a, b in segs)" not in seg


def test_typical_prefilter_keeps_every_segment_the_full_scan_would_count():
    """가까운 선분만 남겨도 `touched` 의 답이 같다 — 무작위 원 · 선분으로 두 판정을 맞댄다."""
    import numpy as np
    import typical
    rng = random.Random(3)
    segs = []
    for _ in range(3000):
        a = pymupdf.Point(rng.uniform(0, 200), rng.uniform(0, 200))
        b = pymupdf.Point(a.x + rng.uniform(-40, 40), a.y + rng.uniform(-40, 40))
        segs.append((a, b))
    xy = np.array([(a.x, a.y, b.x, b.y) for a, b in segs])
    lox, hix = np.minimum(xy[:, 0], xy[:, 2]), np.maximum(xy[:, 0], xy[:, 2])
    loy, hiy = np.minimum(xy[:, 1], xy[:, 3]), np.maximum(xy[:, 1], xy[:, 3])
    for _ in range(400):
        cx, cy = rng.uniform(10, 190), rng.uniform(10, 190)
        w = rng.uniform(4, 14)
        h = w / rng.uniform(0.85, 1.15)
        cb = pymupdf.Rect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
        pad = pymupdf.Rect(cb.x0 - 0.5, cb.y0 - 0.5, cb.x1 + 0.5, cb.y1 + 0.5)
        centre, rad = pymupdf.Point((cb.x0 + cb.x1) / 2, (cb.y0 + cb.y1) / 2), cb.width / 2
        half = max(rad, pad.width / 2, pad.height / 2) + 1.0
        near = np.nonzero((hix >= centre.x - half) & (lox <= centre.x + half)
                          & (hiy >= centre.y - half) & (loy <= centre.y + half))[0]
        cand = [segs[i] for i in near.tolist()]

        def hit(a, b):
            return pad.contains(a) != pad.contains(b) or typical._dist(centre, a, b) < rad
        assert {i for i, (a, b) in enumerate(segs) if hit(a, b)} <= set(near.tolist())
        assert any(hit(a, b) for a, b in segs) == any(hit(a, b) for a, b in cand)


# ---------------------------------------------------------------- 5. 잉크 획 걸러내기
def test_ink_strokes_are_filtered_once_per_page_in_drawing_order():
    class Pc:
        def __init__(self, ds_):
            self._d = ds_
            self.calls = 0

        def drawings(self):
            self.calls += 1
            return self._d
    line = ("l", pymupdf.Point(0, 0), pymupdf.Point(1, 1))
    curve = ("c", pymupdf.Point(0, 0), pymupdf.Point(1, 0), pymupdf.Point(1, 1), pymupdf.Point(0, 1))
    dr = [{"items": [line], "color": (0, 0, 0), "fill": None},
          {"items": [line], "color": (1, 0, 0), "fill": None},          # 빨강 — 잉크 아님
          {"items": [curve], "color": (0, 0, 0), "fill": None},         # 곡선 — 획 아님
          {"items": [line, line], "color": (0, 0, 0), "fill": None},
          {"items": [line], "color": (0, 0, 0), "fill": (0, 0, 0)}]     # 칠함 — 획 아님
    pc = Pc(dr)
    got = ds._ink_strokes(pc)
    assert got == [d for d in dr if ds._is_ink(d) and ds._is_stroke_glyph(d)] == [dr[0], dr[3]]
    ds._ink_strokes(pc)
    assert pc.calls == 1
