"""별표 축의 **재현율**을 장마다 센다 (25회차가 안 잰 축).

    python3 spike/star_recall.py <pdf> [최대 장수]

25회차는 "더한 것이 전부 별표인가"(정밀도)만 쟀다.  여기서는 반대를 묻는다 —
**그 장이 인쇄한 별표 중 몇 개를 마크로 냈는가**.  단계마다 몇 개가 남는지
그대로 적어, 0 이 되는 자리가 곧 원인이 되게 한다.

    ① star_groups            획의 관계로 알아본 뭉치
    ② 그중 버블 마크 창 안    자리까지 맞는 것 (= 그 장이 별표를 찍은 자리)
    ④ 크기 두 번 이상         그 장에서 배운 크기
    ⑤ star_marks 결과         실제로 더해지는 마크
    ⑥ find_marks 전체         기존 경로까지 합친 것
    ⑦ read_vendor_mark 붙음   버블에 실제로 붙은 것
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


def main() -> int:
    pdf = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10**9
    doc, pages = pidcache.load_pages(pdf)
    lay_d = dl.derive(pages, pipeline.CFG)
    pipeline.CFG.overlay(lay_d.values())
    pipeline._rebind_config()
    L = ds.LAYOUT
    print("## 별표 재현율 — %s" % Path(pdf).name)
    print("   %-4s %5s %6s %6s %6s %6s %6s %6s  %s"
          % ("쪽", "버블", "①뭉치", "②창안", "③획수", "④크기", "⑤별표", "⑦붙음", "정의줄/까닭"))
    tot = collections.Counter()
    lost = collections.Counter()
    for pc in pages[:limit]:
        bubbles = ds.find_bubbles(pc, L)
        if not bubbles:
            continue
        short = sorted(min(b.width, b.height) for b in bubbles)
        maxlen = short[len(short) // 2]
        groups = [g for g in ds.star_groups(pc, L, maxlen)
                  if g[0].x1 <= L.drawing_area[2]]
        inwin = [g for g in groups
                 if any(ds.in_mark_window(b, (g[0].x0 + g[0].x1) / 2,
                                          (g[0].y0 + g[0].y1) / 2, L) for b in bubbles)]
        # 26회차 — 정의줄 획수 게이트는 없어졌다.  자리를 남겨 두어 옛 로그와
        # 열이 맞게 한다 (③ = ② 가 된다).
        defn = None
        after_n = list(inwin)
        seen = collections.Counter((round(g[0].width, 1), round(g[0].height, 1))
                                   for g in after_n)
        learned = {k for k, n in seen.items() if n >= 2}
        after_s = [g for g in after_n if (round(g[0].width, 1), round(g[0].height, 1)) in learned]
        stars = ds.star_marks(pc, L, bubbles)
        dct, gsize = ds.read_mark_dictionary(pc, L)
        marks = ds.find_marks(pc, L, glyph_size=gsize if isinstance(gsize, tuple) else None,
                              allow_sizes=ds.KNOWN_GLYPH_SIZES, bubbles=bubbles)
        boxes = ds.find_package_boxes(pc, L)
        box_marks = ds.package_box_marks(boxes, marks) if boxes else {}
        rects = list(bubbles)
        attached = sum(1 for r in rects
                       if ds.read_vendor_mark(r, marks, box_marks, dct, L,
                                              others=[x for x in rects if x is not r])[0])
        why = ""
        if inwin and not after_n:
            why = "★ 정의줄 획수 %d 와 본문 %s 가 다름" % (
                defn[0], sorted({g[1] for g in inwin}))
            lost["정의줄 획수"] += len(inwin)
        elif after_n and not after_s:
            why = "크기가 한 번뿐 %s" % dict(seen)
            lost["크기 1회"] += len(after_n)
        elif inwin and not attached:
            why = "붙지 않음"
            lost["안 붙음"] += len(inwin)
        if inwin or stars:
            print("   p%-3d %5d %6d %6d %6d %6d %6d %6d  %s"
                  % (pc.page_no, len(bubbles), len(groups), len(inwin),
                     len(after_n), len(after_s), len(stars), attached,
                     ("%s획 %s" % (defn[0], defn[1]) if defn else "정의줄 없음") + " " + why))
        tot["장"] += 1
        tot["②창안"] += len(inwin)
        tot["⑤별표"] += len(stars)
        tot["⑦붙음"] += attached
    print("합계:", dict(tot))
    print("잃은 자리:", dict(lost))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
