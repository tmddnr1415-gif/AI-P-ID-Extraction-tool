"""정의줄 획수 게이트를 뺐을 때 무엇이 달라지는가 — **재기만 한다** (코드 수정 없음).

    python3 spike/star_gate_probe.py <pdf> [최대 장수]

`star_marks` 의 세 조건 중 **정의줄 획 수만** 빼고 나머지(자유 끝점 · 그 장에서
배운 크기 · 기존 마크 자리 건너뛰기)는 그대로 둔 변형을 프로세스 안에서만
갈아 끼우고, `find_marks` 의 결과를 현행과 나란히 센다.  버블에 실제로 붙는
것까지 세어 **행이 몇 개 움직이는지**를 낸다.
"""
from __future__ import annotations

import collections
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))

import pidcache                       # noqa: E402
import derive_layout as dl            # noqa: E402
import detect_symbols as ds           # noqa: E402
from app import pipeline              # noqa: E402


def star_marks_nogate(pc, lay, bubbles=None, existing=()):
    """현행 `star_marks` 에서 `if defn: groups = [...]` 두 줄만 뺀 것."""
    if bubbles is None:
        bubbles = ds.find_bubbles(pc, lay)
    if not bubbles:
        return []
    short = sorted(min(b.width, b.height) for b in bubbles)
    maxlen = short[len(short) // 2]
    groups = [g for g in ds.star_groups(pc, lay, maxlen)
              if g[0].x1 <= lay.drawing_area[2]]
    if not groups:
        return []
    seen = collections.Counter()
    for r, _n, _d in groups:
        cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
        if any(ds.in_mark_window(b, cx, cy, lay) for b in bubbles):
            seen[(round(r.width, 1), round(r.height, 1))] += 1
    learned = {k for k, n in seen.items() if n >= 2}
    if not learned:
        return []
    out = []
    for r, _n, _d in groups:
        if (round(r.width, 1), round(r.height, 1)) not in learned:
            continue
        cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
        span = max(r.width, r.height)
        if any(abs(k.x - cx) <= span and abs(k.y - cy) <= span for k in existing):
            continue
        out.append(ds.Mark(cx, cy, 1, "GLYPH"))
    return out


def measure(pc, L):
    """(마크 수, 마크가 붙은 버블 수, 벤더 이름) — 지금 걸린 `star_marks` 로."""
    bubbles = ds.find_bubbles(pc, L)
    dct, gsize = ds.read_mark_dictionary(pc, L)
    marks = ds.find_marks(pc, L, glyph_size=gsize if isinstance(gsize, tuple) else None,
                          allow_sizes=ds.KNOWN_GLYPH_SIZES, bubbles=bubbles)
    boxes = ds.find_package_boxes(pc, L)
    box_marks = ds.package_box_marks(boxes, marks) if boxes else {}
    rects = list(bubbles)
    hit = 0
    for r in rects:
        rules, _ev = ds.read_vendor_mark(r, marks, box_marks, dct, L,
                                         others=[x for x in rects if x is not r])
        if rules:
            hit += 1
    return len(marks), hit, dict(dct)


def main() -> int:
    pdf = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10**9
    doc, pages = pidcache.load_pages(pdf)
    lay_d = dl.derive(pages, pipeline.CFG)
    pipeline.CFG.overlay(lay_d.values())
    pipeline._rebind_config()
    L = ds.LAYOUT
    print("## 정의줄 획수 게이트 유무 — %s" % Path(pdf).name)
    print("   %-5s %14s %14s   %s" % ("쪽", "현행 마크/붙음", "게이트없이 마크/붙음", "사전"))
    tot = collections.Counter()
    moved = []
    orig = ds.star_marks
    for pc in pages[:limit]:
        ds.star_marks = orig
        a_m, a_h, dct = measure(pc, L)
        pc._ink_index = None           # 같은 조건에서 다시 재려고 비운다
        ds.star_marks = star_marks_nogate
        b_m, b_h, _ = measure(pc, L)
        ds.star_marks = orig
        tot["현행마크"] += a_m; tot["현행붙음"] += a_h
        tot["신규마크"] += b_m; tot["신규붙음"] += b_h
        if (a_m, a_h) != (b_m, b_h):
            moved.append(pc.page_no)
            print("   p%-4d %7d /%5d %9d /%5d   %s"
                  % (pc.page_no, a_m, a_h, b_m, b_h,
                     list(dct.values())[0][:46] if dct else "(없음)"))
    print("합계:", dict(tot))
    print("움직인 장 %d개: %s" % (len(moved), moved))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
