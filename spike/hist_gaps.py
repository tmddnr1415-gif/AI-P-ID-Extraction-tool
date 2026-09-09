"""[B2] 이력 표 행 간격의 산포 — 머리글 행이 갈리는가.

    python3 spike/hist_gaps.py <pdf>

이력 띠 안에서 **가장 흔한 간격**을 기준으로 각 간격이 몇 % 벗어나는지 센다.
문턱을 정하기 전에 분포에 **빈 띠**가 있는지 보기 위한 것이다 (§8).
"""
from __future__ import annotations

import collections
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))

import pidcache                       # noqa: E402
import derive_layout as dl            # noqa: E402
from app import pipeline              # noqa: E402


def main() -> int:
    pdf = sys.argv[1]
    doc, pages = pidcache.load_pages(pdf)
    fr = dl._frame(pages)
    if fr is None:
        print("_frame 이 None 을 냈다"); return 1
    left, top, right, bottom, column, xs, ys_ = fr
    inner = [x for x in xs if column < x < right]
    print("   column %.2f · notes inner %s · right %.2f" % (column, [round(x,2) for x in inner], right))
    edge = inner[-1] if inner else right
    inset = 1.2
    dev = collections.Counter()
    rows = collections.Counter()
    for pc in pages:
        ys = sorted({round(r.y0, 2) for r in pc.rects()
                     if abs(r.height) < 1.0
                     and r.x0 <= column + inset and r.x1 >= edge - inset})
        runs = dl._equal_gap_runs(ys)
        if not runs:
            continue
        y0, y1, gap, _n = min(runs, key=lambda b: b[2])
        band = [y for y in ys if y0 - 0.01 <= y <= y1 + 0.01]
        # 띠 바로 아래·위의 괘선 한 줄씩도 함께 본다 (머리글 행이 거기 있다)
        below = [y for y in ys if y > y1][:1]
        above = [y for y in ys if y < y0][-1:]
        full = sorted(above + band + below)
        gaps = [round(full[i + 1] - full[i], 2) for i in range(len(full) - 1)]
        if not gaps:
            continue
        mode = statistics.mode(gaps)
        rows[len(band) - 1] += 1
        for g in gaps:
            dev[round(abs(g - mode) / mode * 100, 1)] += 1
    print("## %s" % Path(pdf).name)
    print("   띠 안 행 수 분포 %s" % dict(sorted(rows.items())))
    print("   최빈 간격에서 벗어난 정도(%) → 간격 수")
    for k in sorted(dev):
        print("     %6.1f%%  %d" % (k, dev[k]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
