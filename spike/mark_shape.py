"""[B] 별표는 어떤 **모양**인가 — 두 문서에서 같은 잣대로 잰다.

    python3 spike/mark_shape.py <pdf> [--marks-only]

크기가 아니라 모양으로 가르려면 먼저 모양을 재야 한다.  뭉치 하나에 대해:

    획 수      그 뭉치를 이루는 직선 항목의 수
    갈래 수    서로 다른 방향의 수 (15도 칸으로 묶음)
    중심 쏠림  각 획의 중점이 뭉치 중심에서 얼마나 떨어졌나 / 뭉치 크기
               (**비율이다** — 23회차 §6: 비율·모양은 축척을 넘는다)

`--marks-only` 는 지금 판정기가 마크로 인정한 뭉치만 본다 (AL NOUF1 에서
"별표란 이런 것" 의 표본이 된다).
"""
from __future__ import annotations

import collections
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))

import pidcache                       # noqa: E402
import derive_layout as dl            # noqa: E402
import detect_symbols as ds           # noqa: E402
from app import pipeline              # noqa: E402


def segments_in(pc, rect, lay):
    """그 사각형 안에 든 **곧은 획**들 — 뭉치를 이루는 원재료.

    ⚠ `pidcache.drawings()` 는 **bbox 만** 회전 정규화한다 (`d["rect"] * m`).
    항목 좌표는 원래 공간에 남아 있으므로 여기서 같은 행렬을 곱해야 한다 —
    안 그러면 회전된 장에서 중점이 엉뚱한 곳에 찍힌다 (실측: 쏠림 91~358).
    """
    m = pc.page.rotation_matrix
    out = []
    for d in pc.drawings():
        if not ds._is_ink(d) or not ds._is_stroke_glyph(d):
            continue
        b = d["bbox"]
        if not (rect.x0 - 0.6 <= b.x0 and b.x1 <= rect.x1 + 0.6
                and rect.y0 - 0.6 <= b.y0 and b.y1 <= rect.y1 + 0.6):
            continue
        for it in d["items"]:
            if it[0] == "l":
                out.append((it[1] * m, it[2] * m))
    return out


def features(rect, segs):
    """(획 수, 갈래 수, 중심 쏠림 비율)"""
    if not segs:
        return 0, 0, None
    cx, cy = (rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2
    size = max(rect.width, rect.height) or 1.0
    dirs = set()
    worst = 0.0
    for a, b in segs:
        ang = math.degrees(math.atan2(b.y - a.y, b.x - a.x)) % 180.0
        dirs.add(int(ang // 15))
        mx, my = (a.x + b.x) / 2, (a.y + b.y) / 2
        worst = max(worst, math.hypot(mx - cx, my - cy) / size)
    return len(segs), len(dirs), round(worst, 3)


def main() -> int:
    pdf = sys.argv[1]
    marks_only = "--marks-only" in sys.argv
    doc, pages = pidcache.load_pages(pdf)
    lay = dl.derive(pages, pipeline.CFG)
    pipeline.CFG.overlay({k: v for k, v in lay.values().items()
                          if not (isinstance(v, (list, tuple)) and len(v) == 0)})
    pipeline._rebind_config()
    L = ds.LAYOUT
    segc, dirc, offc = collections.Counter(), collections.Counter(), collections.Counter()
    n = 0
    for pc in pages:
        clusters = [c for c in ds._glyph_clusters(pc, L) if c.x1 <= L.drawing_area[2]]
        if marks_only:
            dct, gs = ds.read_mark_dictionary(pc, L)
            sizes = ([gs] if gs else []) + list(ds.KNOWN_GLYPH_SIZES)
            clusters = [c for c in clusters
                        if any(abs(c.width - w) <= 0.6 and abs(c.height - h) <= 0.6
                               for w, h in sizes)]
        for c in clusters:
            s, d_, off = features(c, segments_in(pc, c, L))
            if not s:
                continue
            n += 1
            segc[s] += 1
            dirc[d_] += 1
            offc[round(off, 1)] += 1
    print("## %s%s — 뭉치 %d개" % (Path(pdf).name, " (마크로 인정된 것만)" if marks_only else "", n))
    print("   획 수      %s" % sorted(segc.items()))
    print("   갈래 수    %s" % sorted(dirc.items()))
    print("   중심 쏠림  %s" % sorted(offc.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
