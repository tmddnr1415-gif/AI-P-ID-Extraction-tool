"""[B] 정의줄의 별표를 **획으로** 읽을 수 있는가 — 도면이 별표를 어떻게 그리는지.

    python3 spike/legend_star.py <pdf>

NOTES 열의 정의줄(별표 뜻을 적은 줄) 왼쪽에 놓인 것이 (가) 텍스트 `*`/`(*)` 인지
(나) 획으로 그린 별표인지 가른다.  (나)면 획 수·크기·중점 퍼짐을 그 자리에서 읽는다
— 그것이 §9 ①②(범례·NOTES 에서 읽기)다.  (가)면 도면은 모양을 말하지 않으므로
본문 실물(④)로 간다고 보고한다.
"""
from __future__ import annotations

import collections
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))

import pymupdf                        # noqa: E402
import pidcache                       # noqa: E402
import derive_layout as dl            # noqa: E402
import detect_symbols as ds           # noqa: E402
from app import pipeline              # noqa: E402


def stroke_groups(pc, region, maxlen, tol):
    """짧은 곧은 획 중 중점이 한 점에 모이는 무리 — (rect, 획 수, 방향 수, 퍼짐)."""
    m = pc.page.rotation_matrix
    segs = []
    for d in pc.drawings():
        if not ds._is_ink(d) or not ds._is_stroke_glyph(d):
            continue
        b = d["bbox"]
        if not region.intersects(b) or max(b.width, b.height) > maxlen:
            continue
        for it in d["items"]:
            if it[0] != "l":
                continue
            a, c = it[1] * m, it[2] * m
            ln = math.hypot(c.x - a.x, c.y - a.y)
            if not (0.5 <= ln <= maxlen):
                continue
            segs.append(((a.x + c.x) / 2, (a.y + c.y) / 2,
                         int(math.degrees(math.atan2(c.y - a.y, c.x - a.x)) % 180 // 15), a, c))
    used, out = set(), []
    for i, s in enumerate(segs):
        if i in used:
            continue
        near = [j for j in range(len(segs)) if j not in used
                and math.hypot(segs[j][0] - s[0], segs[j][1] - s[1]) <= tol]
        if len(near) < 2 or len({segs[j][2] for j in near}) < 2:
            continue
        used |= set(near)
        xs = [p.x for j in near for p in (segs[j][3], segs[j][4])]
        ys = [p.y for j in near for p in (segs[j][3], segs[j][4])]
        spread = max(math.hypot(segs[j][0] - s[0], segs[j][1] - s[1]) for j in near)
        out.append((pymupdf.Rect(min(xs), min(ys), max(xs), max(ys)), len(near),
                    len({segs[j][2] for j in near}), round(spread, 2)))
    return out


def main() -> int:
    pdf = sys.argv[1]
    doc, pages = pidcache.load_pages(pdf)
    if "pid_total" not in pdf:
        lay = dl.derive(pages, pipeline.CFG)
        pipeline.CFG.overlay({k: v for k, v in lay.values().items()
                              if not (isinstance(v, (list, tuple)) and len(v) == 0)})
        pipeline._rebind_config()
    L = ds.LAYOUT
    notes = pymupdf.Rect(*L.notes_area)
    how = collections.Counter()
    shapes = collections.Counter()
    sizes = collections.Counter()
    spreads = collections.Counter()
    for pc in pages:
        dct, gs = ds.read_mark_dictionary(pc, L)
        if not dct:
            continue
        lines = ds._notes_lines(pc, L)
        # 정의줄: 텍스트 별표로 시작하는 줄 / 왼쪽에 글리프가 있는 줄
        text_marked = [ln for ln in lines if ds.MARK_TEXT_RE.match(ln["words"][0])]
        groups = stroke_groups(pc, notes, maxlen=12.0, tol=1.0)
        drawn = []
        for ln in lines:
            for r, ns, nd, sp in groups:
                cy = (r.y0 + r.y1) / 2
                if ln["y"] - 4 <= cy <= ln["y1"] + 4 and r.x1 <= ln["x0"] + 1:
                    drawn.append((ln["text"][:40], ns, nd, round(r.width, 1), round(r.height, 1), sp))
        kind = ("텍스트" if text_marked and not drawn else
                "획" if drawn and not text_marked else
                "둘 다" if drawn and text_marked else "없음")
        how[kind] += 1
        for _t, ns, nd, w, h, sp in drawn:
            shapes[(ns, nd)] += 1
            sizes[(w, h)] += 1
            spreads[round(sp, 1)] += 1
        print("  p%-3d 사전 %-40s %s %s" % (pc.page_no, str(dct)[:40], kind,
                                              drawn[:2] if drawn else
                                              [ln["words"][0] for ln in text_marked][:3]))
    print("## %s — 사전 있는 장 %d" % (Path(pdf).name, sum(how.values())))
    print("   정의줄의 별표 표기:", dict(how))
    if shapes:
        print("   획으로 그린 것의 (획 수, 방향 수):", sorted(shapes.items()))
        print("   크기:", sizes.most_common(6))
        print("   중점 퍼짐:", sorted(spreads.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
