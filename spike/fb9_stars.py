"""9차 [C] — 별표를 세는 두 규칙을 **나란히** 재는 도구 (54회차).

측정만 한다.  `star_groups` 를 그대로 부르되 `_touches` 만 갈아 끼워
"닿았다" 의 뜻을 바꾼 결과를 함께 낸다:

  (가) 지금 규칙 — 끝점이 다른 선분의 **어디든** 허용치 안이면 닿았다
  (나) 끝점 규칙 — 다른 선분의 **끝점**에 허용치 안일 때만 닿았다

(나) 의 근거는 25회차가 이 조건을 넣은 이유 그대로다: *나비의 대각선은
삼각형 **꼭짓점**에서 밑변·이웃 변과 만나고, 별표의 획은 허공에서 끝난다.*
꼭짓점은 끝점이 모이는 자리이지 선분의 한가운데가 아니다.

    python3 spike/fb9_stars.py data/TC2_260821.pdf
"""
from __future__ import annotations

import collections
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app" / "engine"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pidcache                                          # noqa: E402
import detect_symbols as ds                              # noqa: E402


def _touches_ends(grid, p, tol, own, cell):
    """다른 선분의 **끝점**에만 닿았다고 본다."""
    gx, gy = int(p.x // cell), int(p.y // cell)
    rings = int(tol // cell) + 1
    span = range(-rings, rings + 1)
    for dx in span:
        for dy in span:
            for a, b, key in grid.get((gx + dx, gy + dy), ()):
                if key in own:
                    continue
                if (math.hypot(p.x - a.x, p.y - a.y) <= tol
                        or math.hypot(p.x - b.x, p.y - b.y) <= tol):
                    return True
    return False


def census(pdf: str) -> dict:
    doc, pages = pidcache.load_pages(pdf)
    orig = ds._touches
    out = {}
    for name, fn in (("now", orig), ("ends", _touches_ends)):
        ds._touches = fn
        total = collections.Counter()
        per_page = {}
        for pc in pages:
            outlines = ds.bubble_outlines(pc, ds.LAYOUT)
            if not outlines:
                continue
            marks = ds.star_marks(pc, ds.LAYOUT, outlines=outlines)
            per_page[pc.page_no] = [(round(m.x, 2), round(m.y, 2)) for m in marks]
            total["marks"] += len(marks)
            total["pages"] += 1
        out[name] = (dict(total), per_page)
    ds._touches = orig
    return out


def main() -> int:
    pdf = sys.argv[1]
    res = census(pdf)
    (t_now, p_now), (t_end, p_end) = res["now"], res["ends"]
    print(pdf)
    print("  지금 규칙 :", t_now)
    print("  끝점 규칙 :", t_end)
    for pno in sorted(set(p_now) | set(p_end)):
        a, b = set(p_now.get(pno, ())), set(p_end.get(pno, ()))
        if a != b:
            print("   p%-3d  지금 %2d  끝점 %2d   더해짐 %s   사라짐 %s"
                  % (pno, len(a), len(b), sorted(b - a)[:8], sorted(a - b)[:8]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
