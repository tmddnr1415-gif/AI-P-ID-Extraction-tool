"""벤더 별표 축이 이 문서에서 어디까지 사는가 — 장마다 단계별로 센다.

    python3 spike/mark_probe.py <pdf> [최대 장수]

단계는 넷이고, **어디서 0 이 되는지**가 곧 원인이다:

    ① 그 장 NOTES 가 별표를 정의하는가      `read_mark_dictionary`
    ② 도면에서 별표를 알아보는가            `find_marks`
    ③ 그 별표가 버블·밸브에 붙는가          `read_vendor_mark`
    ④ 붙지 않은 잉크 획 뭉치가 남는가       독립 감사 (`_glyph_clusters` 직접)

낯선 양식은 파이프라인이 **유도값을 전부 얹으므로**(`_fit_layout`) 여기서도
같게 얹는다 — 안 그러면 도면 영역·NOTES 영역이 남의 좌표가 된다.
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
    vals = lay_d.values()
    moved = pipeline.CFG.overlay(vals)
    pipeline._rebind_config()
    L = ds.LAYOUT
    print("## %s (%d쪽) · 유도값 %d칸 얹음" % (Path(pdf).name, len(pages), len(moved)))
    print("   drawing_area %s · notes_area %s · notes_text_x_max %s"
          % (L.drawing_area, L.notes_area, L.notes_text_x_max))
    print("   mark_above %s · mark_side %s · glyph_sizes %s"
          % (L.mark_above, L.mark_side, ds.KNOWN_GLYPH_SIZES))

    tot = collections.Counter()
    for pc in pages[:limit]:
        try:
            dct, gsize = ds.read_mark_dictionary(pc, L)
        except Exception as exc:
            dct, gsize = {}, "예외 %s" % exc
        bubbles = ds.find_bubbles(pc, L)
        drawn = ds.drawn_mark_sizes(pc, L, bubbles)
        marks = ds.find_marks(pc, L, glyph_size=gsize if isinstance(gsize, tuple) else None,
                              allow_sizes=ds.KNOWN_GLYPH_SIZES, bubbles=bubbles)
        kinds = collections.Counter(m.form for m in marks)
        boxes = ds.find_package_boxes(pc, L) if hasattr(ds, "find_package_boxes") else []
        box_marks = ds.package_box_marks(boxes, marks) if boxes else {}
        attached = 0
        rects = list(bubbles)          # find_bubbles 는 Rect 를 낸다
        for r in rects:
            hits, _ev = ds.read_vendor_mark(r, marks, box_marks, dct, L,
                                            others=[x for x in rects if x is not r])
            if hits:
                attached += 1
        tot["장"] += 1
        tot["사전"] += 1 if dct else 0
        tot["버블"] += len(bubbles)
        tot["마크"] += len(marks)
        tot["붙음"] += attached
        if dct or marks or drawn:
            print("  p%-3d 사전 %-38s 정의줄크기 %-12s 도면크기 %-16s 버블 %3d 마크 %2d%s 붙음 %2d"
                  % (pc.page_no, dict(dct) if dct else "-", gsize, drawn or "-",
                     len(bubbles), len(marks), dict(kinds) or "", attached))
    print("합계:", dict(tot))
    return 0




def audit(pdf: str, limit: int = 10**9) -> int:
    """독립 감사 — `find_marks` 를 부르지 않고 버블 마크 자리의 잉크 뭉치를 전수로 센다.

    18·19회차의 교훈: **판정에 쓰는 축을 검사도 쓰면 "전수 0건" 이 나온다.**
    여기서는 크기 필터를 걸지 않고 자리만 보고, 나온 크기의 분포를 그대로 낸다.
    """
    doc, pages = pidcache.load_pages(pdf)
    lay_d = dl.derive(pages, pipeline.CFG)
    pipeline.CFG.overlay(lay_d.values())
    pipeline._rebind_config()
    L = ds.LAYOUT
    sizes = collections.Counter()
    per_page = collections.Counter()
    bub_with = 0
    bub_tot = 0
    for pc in pages[:limit]:
        bubbles = ds.find_bubbles(pc, L)
        bub_tot += len(bubbles)
        clusters = [c for c in ds._glyph_clusters(pc, L)
                    if c.x1 <= L.drawing_area[2]]
        for b in bubbles:
            near = [c for c in clusters
                    if ds.in_mark_window(b, (c.x0 + c.x1) / 2,
                                         (c.y0 + c.y1) / 2, L)]
            if near:
                bub_with += 1
                per_page[pc.page_no] += len(near)
                for c in near:
                    sizes[(round(c.width, 1), round(c.height, 1))] += 1
    print("## 독립 감사 — %s" % Path(pdf).name)
    print("   버블 %d · 마크 자리에 잉크 뭉치가 있는 버블 %d" % (bub_tot, bub_with))
    print("   크기 분포 (많은 순 20):")
    for s, n in sizes.most_common(20):
        print("     %-14s %d" % (str(s), n))
    print("   장별 뭉치 수:", dict(sorted(per_page.items())))
    return 0


if __name__ == "__main__":
    if "--audit" in sys.argv:
        sys.argv.remove("--audit")
        raise SystemExit(audit(sys.argv[1],
                               int(sys.argv[2]) if len(sys.argv) > 2 else 10**9))
    raise SystemExit(main())
