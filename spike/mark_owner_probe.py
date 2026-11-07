"""48회차 [B] — 별표 소유권 경쟁에 **누가 들어 있나** 를 전수로 센다.

47회차가 드러낸 것: TC2 p15 LIT · p25 LI 가 **옆 밸브의 별표까지 claim** 해
`**` 가 되고 그 장 NOTES 가 `**` 를 정의하지 않아 이름을 잃는다.

`read_vendor_mark(rect, …, others=…)` 의 `others` 는 **경쟁자 목록**이고
(16회차 · 19회차 `_mark_gap` 유클리드), 실제로 넘어가는 것은:

    계기 (detect_symbols:1822)  others = 다른 **버블**            ← 밸브 없음
    밸브 (pipeline:3390)        others 를 **아예 안 넘긴다**      ← 경쟁자 0
    마크업 제안 (pipeline:3088) others = 다른 **버블**            ← 밸브 없음

즉 두 가족이 서로를 못 본다.  이 도구는 그 자리를 센다 — 판정을 부르지 않고
같은 1차 재료(`in_mark_window` · `_mark_gap`)로 **누가 더 가까운가**만 본다.
(찾았는가는 47회차가 독립 채널로 이미 쟀다.  여기 물음은 *누구 것인가* 이고,
그 정답은 렌더가 준다 — 표본을 크롭해 눈으로 확인한다.)

    python3 spike/mark_owner_probe.py <이름> <PDF> [장,장,...]

★ 실 DB 를 열지 않는다 · config 는 끝에 되돌린다 (22회차).
★ 전수 전에 `--time` 으로 장당 시간을 먼저 잰다 (47회차 1시간 42분 재발 방지).
"""
from __future__ import annotations

import collections
import copy
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))

import pymupdf                                     # noqa: E402
from app.engine import detect_symbols as ds        # noqa: E402
from app.engine import detect_valves as dv         # noqa: E402
from app.engine import pidcache                    # noqa: E402


def _valve_rects(pc, vlay):
    """그 장의 밸브 — `pipeline` 이 별표를 읽는 것과 **같은 사각형들**."""
    out = []
    for b in dv.find_bodies(pc, vlay):
        mark_rect = (pymupdf.Rect(*b.actuator_rect) if b.actuator_rect else b.rect)
        also = (b.rect,) if b.actuator_rect else ()
        out.append((b.kind, (mark_rect,) + tuple(also)))
    return out


def page_report(pc, lay, vlay):
    outlines = ds.bubble_outlines(pc, lay)
    outlines = outlines + ds.dashed_bubble_outlines(pc, outlines)
    bubbles = [o.rect for o in outlines]
    valves = _valve_rects(pc, vlay)
    if not bubbles and not valves:
        return None
    mark_dict, gsize = ds.read_mark_dictionary(pc, lay)
    marks = ds.find_marks(pc, lay, glyph_size=gsize if isinstance(gsize, tuple) else None,
                          allow_sizes=ds.KNOWN_GLYPH_SIZES, bubbles=bubbles,
                          outlines=outlines)
    rows = []
    for k in marks:
        # 창에 든 사람들 — 가족별로
        bub = [(ds._mark_gap(r, k.x, k.y), r) for r in bubbles
               if ds.in_mark_window(r, k.x, k.y, lay)]
        val = [(min(ds._mark_gap(r, k.x, k.y) for r in rs), kind, rs[0]) for kind, rs in valves
               if any(ds.in_mark_window(r, k.x, k.y, lay) for r in rs)]
        if not bub and not val:
            continue
        near_b = min((g for g, _ in bub), default=None)
        near_v = min((g for g, _k, _r in val), default=None)
        verdict = "OK"
        if bub and val:
            # 지금 규칙: 버블은 **다른 버블**만 경쟁자로 본다 → 밸브가 더 가까워도 가져간다
            if near_v < near_b:
                verdict = "BUBBLE_TAKES_VALVE"      # 버블이 밸브 것을 가져간다
            elif near_b < near_v:
                verdict = "VALVE_TAKES_BUBBLE"      # 밸브는 경쟁자가 아예 없다
            else:
                verdict = "TIE"
        rows.append({"x": round(k.x, 2), "y": round(k.y, 2), "stars": k.stars,
                     "form": k.form, "bubbles": len(bub), "valves": len(val),
                     "near_bubble": None if near_b is None else round(near_b, 2),
                     "near_valve": None if near_v is None else round(near_v, 2),
                     "valve_kinds": sorted({kind for _g, kind, _r in val}),
                     "verdict": verdict})
    return {"page": pc.page_no, "marks": len(marks), "bubbles": len(bubbles),
            "valves": len(valves), "contested": rows}


def main() -> int:
    name, pdf = sys.argv[1], Path(sys.argv[2])
    wanted = {int(x) for x in sys.argv[3].split(",")} if len(sys.argv) > 3 else None
    import derive_layout as dl
    from app import pipeline

    snap = copy.deepcopy(pipeline.CFG.data)
    doc = None
    try:
        doc, pages = pidcache.load_pages(pdf)
        pipeline.CFG.overlay(dl.derive(pages, pipeline.CFG).values())
        pipeline._rebind_config()
        lay = ds.LAYOUT
        vlay, _prov = dv.derive_layout(pages)
        out, times = [], []
        for pc in pages:
            if wanted and pc.page_no not in wanted:
                continue
            if not pc.analysis_scope:
                continue
            t0 = time.time()
            rep = page_report(pc, lay, vlay)
            ds.release_ink()
            times.append(round(time.time() - t0, 2))
            if rep:
                out.append(rep)
        tally = collections.Counter(r["verdict"] for p in out for r in p["contested"])
        print(json.dumps({
            "project": name, "pages": len(out),
            "seconds_per_page": {"n": len(times), "max": max(times or [0]),
                                 "total": round(sum(times), 1)},
            "verdicts": dict(tally),
            "contested_pages": [p for p in out
                                if any(r["verdict"] != "OK" for r in p["contested"])],
        }, ensure_ascii=False, indent=1))
    finally:
        if doc is not None:
            doc.close()
        if pipeline.CFG.data != snap:
            pipeline.CFG.data = snap
            pipeline._rebind_config()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
