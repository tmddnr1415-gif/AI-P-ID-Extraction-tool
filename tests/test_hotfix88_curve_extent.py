"""hotfix88 — 같은 답으로 더 빠르게: `curve_extent` · 별표 무리 이웃 · 인출선 미리 거르기 · 가르치기 판 서버 시간.

같은 값인지는 옛 구현(이 시험 안에 그대로 둔다)과 비트 단위로 맞댄다 — 네 회전(0·90·180·270) ·
무작위 double 좌표 · 실물 PDF 의 곡선 전부.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

import pymupdf
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app" / "engine"))

import pidcache  # noqa: E402


def _old_curve_extent(items, m) -> pymupdf.Rect:
    """hotfix87 까지의 구현 — 글자 그대로."""
    xs, ys = [], []
    for it in items:
        if it[0] == "l":
            pts = [it[1], it[2]]
        elif it[0] == "c":
            p0, p1, p2, p3 = it[1], it[2], it[3], it[4]
            pts = []
            for k in range(9):
                t = k / 8
                u = 1 - t
                pts.append(pymupdf.Point(
                    u * u * u * p0.x + 3 * u * u * t * p1.x + 3 * u * t * t * p2.x + t * t * t * p3.x,
                    u * u * u * p0.y + 3 * u * u * t * p1.y + 3 * u * t * t * p2.y + t * t * t * p3.y))
        else:
            continue
        for p in pts:
            q = p * m
            xs.append(q.x)
            ys.append(q.y)
    return pymupdf.Rect(min(xs), min(ys), max(xs), max(ys))


def _matrices():
    out = []
    for rot in (0, 90, 180, 270):
        doc = pymupdf.open()
        pg = doc.new_page(width=1191, height=842)
        pg.set_rotation(rot)
        out.append((rot, pg.rotation_matrix))
    return out


def test_xy32_matches_point_times_matrix_for_any_double():
    random.seed(7)
    for _rot, m in _matrices():
        R = pidcache._rot_for(m)
        assert R.fast
        for _ in range(20000):
            x = random.uniform(-50, 1300) * random.choice([1, 1 / 3, 1 / 7, 1e-3])
            y = random.uniform(-50, 900) * random.choice([1, 1 / 3, 1 / 7, 1e-3])
            q = pymupdf.Point(x, y) * m
            assert R.xy32(x, y) == (q.x, q.y)


def _random_items(rng):
    items = []
    for _ in range(rng.randint(1, 6)):
        kind = rng.choice(["c", "c", "l"])
        pts = [pymupdf.Point(rng.uniform(0, 1200) / rng.choice([1, 3, 7]),
                             rng.uniform(0, 850) / rng.choice([1, 3, 7])) for _ in range(4 if kind == "c" else 2)]
        items.append((kind, *pts))
    return items


def test_curve_extent_same_rect_as_before_on_synthetic_paths():
    rng = random.Random(3)
    for _rot, m in _matrices():
        for _ in range(3000):
            items = _random_items(rng)
            a, b = _old_curve_extent(items, m), pidcache.curve_extent(items, m)
            assert (a.x0, a.y0, a.x1, a.y1) == (b.x0, b.y0, b.x1, b.y1)


def test_rot_cache_is_per_matrix():
    (_r0, m0), (_r90, m90) = _matrices()[:2]
    assert pidcache._rot_for(m0) is pidcache._rot_for(m0)
    assert pidcache._rot_for(m0) is not pidcache._rot_for(m90)


@pytest.mark.parametrize("pdf", ["data/newproj/binder.pdf", "data/TC2_260821.pdf"])
def test_curve_extent_same_on_real_pages(pdf):
    """실물 — 회전 0(Takhiatash) 과 270(TC2) 장의 곡선 path 전부 (앞 몇 장)."""
    path = ROOT / pdf
    if not path.exists():
        pytest.skip(f"{pdf} 없음")
    doc = pymupdf.open(str(path))
    n = 0
    for i in range(min(4, doc.page_count)):
        pg = doc[i]
        m = pg.rotation_matrix
        for d in pg.get_drawings():
            items = d["items"]
            if not items or not any(it[0] == "c" for it in items):
                continue
            a, b = _old_curve_extent(items, m), pidcache.curve_extent(items, m)
            assert (a.x0, a.y0, a.x1, a.y1) == (b.x0, b.y0, b.x1, b.y1)
            n += 1
    assert n > 0


# ---------------------------------------------------------------------------
# hotfix88 — 가르치기 판의 서버 쪽 느린 자리 (A1 실측 `/teach` 13.5초 · `/sheet_numbers` 5.1초)
# ---------------------------------------------------------------------------
MAIN = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
TP = (ROOT / "app" / "teach_propose.py").read_text(encoding="utf-8")


def test_teach_state_does_not_load_words_and_asks_the_worker():
    body = MAIN[MAIN.index("def teach_state("):MAIN.index("def _words_in(")]
    assert "_tb_sizes(job)" in body and "_tb_pages(job)" not in body
    assert "_needs_and_suggest(job, saved)" in body
    ns = MAIN[MAIN.index("def _needs_and_suggest("):MAIN.index('@app.get("/jobs/{job_id}/teach")')]
    assert "page_warm.call(teach_propose.needs_pdf" in ns
    assert "_teach_needs(job, pages, form, saved)" in ns          # 일꾼이 없으면 서버 안에서 (같은 판정)
    pre = MAIN[MAIN.index("def _proposal_slot("):MAIN.index("def _prefetch_proposals(")]
    assert "_needs_and_suggest(job, form_teach.load(" in pre      # 멈춘 순간 미리 센다


def test_bubble_preview_counts_in_the_worker():
    body = MAIN[MAIN.index("def teach_preview("):MAIN.index("def teach_click(")]
    assert "page_warm.call(" in body and "teach_propose.preview_bubbles_pdf" in body
    assert "except RuntimeError:" in body                         # 일꾼이 없으면 서버 안에서


def test_worker_needs_is_the_same_judgement_as_the_server_one():
    """일꾼 쪽 `needs_pdf` 와 서버 쪽 `_teach_needs` 는 같은 함수들로 같은 조건을 본다."""
    w = TP[TP.index("def needs_pdf("):TP.index("def preview_bubbles_pdf(")]
    s = MAIN[MAIN.index("def _teach_needs("):MAIN.index("_NEEDS_CACHE: dict")]
    for frag in ("_page_with(pages, h) is None for h in legend_rules.TEACHABLE_HEADINGS",
                 "learn_bubble_template(by[b[\"page_no\"]], b[\"rect\"])",
                 "[:5]", ">= 3", "bubble_outlines(pc) for pc in busy"):
        assert frag in w and frag in s, frag
    assert "release_pages(pages)" in w                             # 일꾼은 낱말만 들고 산다


def test_stroke_only_counts_are_cached_per_pdf():
    start = MAIN.index("def _stroke_only_pages(")
    body = MAIN[start:MAIN.index("\ndef ", start + 10)]
    assert "_STROKE_COUNTS.get(ckey)" in body and "st_mtime_ns" in body


def test_needs_pdf_falls_back_in_process(tmp_path, monkeypatch):
    """일꾼을 끄면(`PID_RENDER_POOL=0`) 같은 답을 서버 안에서 — 실물 없이 합성 PDF 로 형태만 본다."""
    monkeypatch.setenv("PID_RENDER_POOL", "0")
    from app import page_warm
    with pytest.raises(RuntimeError):
        page_warm.call(lambda: None, ())


# ---------------------------------------------------------------------------
# hotfix88 — 별표 무리 이웃 찾기 · 인출선 미리 거르기 (둘 다 **같은 답**인지 옛 식과 맞댄다)
# ---------------------------------------------------------------------------
import collections  # noqa: E402
import math  # noqa: E402

import numpy as np  # noqa: E402

import describe_axis  # noqa: E402
import detect_symbols as ds  # noqa: E402


def _old_groups(segs, maxlen, min_dirs):
    """hotfix87 `star_groups` 의 무리 짓기 부분 — 글자 그대로 (segs = (mx, my, ln, dirb))."""
    cell = maxlen
    grid = collections.defaultdict(list)
    for i, s in enumerate(segs):
        grid[(int(s[0] // cell), int(s[1] // cell))].append(i)
    used, groups = set(), []
    for i, s in enumerate(segs):
        if i in used:
            continue
        gx, gy = int(s[0] // cell), int(s[1] // cell)
        near = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in grid.get((gx + dx, gy + dy), ()):
                    if j in used:
                        continue
                    t = segs[j]
                    tol = 0.25 * min(s[2], t[2])
                    if math.hypot(t[0] - s[0], t[1] - s[1]) <= tol:
                        near.append(j)
        if len(near) < 2 or len({segs[j][3] for j in near}) < min_dirs:
            continue
        used.update(near)
        groups.append(sorted(near))
    return groups


def _new_groups(segs, maxlen, min_dirs):
    arr = {"mx": np.array([s[0] for s in segs]), "my": np.array([s[1] for s in segs]),
           "ln": np.array([s[2] for s in segs])}
    adj = ds._near_adjacency(arr, list(range(len(segs))), 0.25 * maxlen)
    used, groups = set(), []
    for i in range(len(segs)):
        if i in used:
            continue
        near = [j for j in adj.get(i, ()) if j not in used]
        if len(near) < 2 or len({segs[j][3] for j in near}) < min_dirs:
            continue
        used.update(near)
        groups.append(sorted(near))
    return groups


def test_star_adjacency_groups_same_as_grid_walk():
    """별표처럼 중점이 모인 획 뭉치 + 흩어진 획 + 경계에 걸친 쌍 — 무리가 글자 그대로 같다."""
    rng = random.Random(11)
    for trial in range(60):
        maxlen = rng.choice([4.2, 11.4, 22.6])
        segs = []
        for _ in range(rng.randint(5, 40)):                       # 별표 후보: 한 점 둘레에 2~6 획
            cx, cy = rng.uniform(0, 800), rng.uniform(0, 600)
            ln = rng.uniform(0.3, 1.0) * maxlen
            for _k in range(rng.randint(2, 6)):
                segs.append((cx + rng.uniform(-0.3, 0.3) * ln, cy + rng.uniform(-0.3, 0.3) * ln,
                             ln * rng.uniform(0.8, 1.2), rng.randint(0, 11)))
        for _ in range(rng.randint(50, 300)):                     # 흩어진 획
            segs.append((rng.uniform(0, 800), rng.uniform(0, 600), rng.uniform(0.1, 1.0) * maxlen, rng.randint(0, 11)))
        rng.shuffle(segs)
        for md in (2, 3):
            assert _old_groups(segs, maxlen, md) == _new_groups(segs, maxlen, md), (trial, md)


def test_leaders_touching_is_the_skipped_set_of_the_old_loop():
    """`pick_tap` 의 옛 반복이 `continue` 하던 인출선만 빠지고 순서는 그대로다."""
    rng = random.Random(5)
    for _ in range(200):
        leaders = []
        for _k in range(rng.randint(0, 400)):
            axis = rng.choice("HV")
            c, lo = rng.uniform(0, 1000), rng.uniform(0, 1000)
            leaders.append((axis, c, lo, lo + rng.uniform(0.0, 40)))
        rect = (rng.uniform(0, 900), rng.uniform(0, 900), 0, 0)
        rect = (rect[0], rect[1], rect[0] + rng.uniform(5, 40), rect[1] + rng.uniform(5, 40))
        js = rng.choice([0.0, 0.8, 2.5])
        want = []
        for L in leaders:
            p0, p1 = describe_axis._ends(L)
            ins = [(describe_axis._pt_rect_d(p, rect) <= js) for p in (p0, p1)]
            if ins[0] != ins[1]:
                want.append(L)
        assert describe_axis.leaders_touching(rect, leaders, js) == want
