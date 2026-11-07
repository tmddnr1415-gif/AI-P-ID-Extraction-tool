"""[B] 이력 표 실측 — 세 문서의 개정 이력 표가 실제로 어떻게 생겼나 (24회차).

**코드를 고치기 전에 잰다.**  PDF 원본 좌표(엔진과 같은 derotate 공간)에서 읽고
화면이나 사진을 보지 않는다.

    python3 spike/hist_measure.py <pdf> [잴 장 수]

줄 묶기
    `derive_layout._column_lines` 는 y 중심을 **0.1pt 로 반올림**해 묶는다.
    SADARA 는 같은 캡션 줄의 낱말 중심이 `REV.` 1828.092 ↔ `DESCRIPTION` 1827.912
    로 **0.18pt** 어긋나 있어 그 반올림에서 두 줄로 쪼개지고, 캡션이 안 잡힌다.
    여기서는 **그 열 낱말 높이의 1/4** 안이면 같은 줄로 본다 (SADARA 10.62 → 2.66pt).
    분모는 그 도면에서 잰 값이고 상수가 아니다.
"""
from __future__ import annotations

import collections
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))

from app.engine import pidcache              # noqa: E402
from app.engine import derive_layout as dl   # noqa: E402

CAPTION = ("REV.", "DATE", "DESCRIPTION")


def column_words(pages, column):
    """타이틀블록 열의 낱말이 가장 많은 장 — 그 장이 기하를 말한다."""
    best = None
    for pc in pages:
        ws, seen = [], set()
        for r, t in pc.words:
            if r.x0 < column:
                continue
            k = (round(r.x0, 2), round(r.y0, 2), t)
            if k in seen:
                continue
            seen.add(k)
            ws.append((r, t))
        if best is None or len(ws) > len(best[1]):
            best = (pc, ws)
    return best


def caption_row(ws, tol):
    """인쇄된 `REV. DATE DESCRIPTION` 줄 — 허용치 안에서 같은 줄로 묶는다."""
    rows = collections.defaultdict(list)
    for r, t in sorted(ws, key=lambda z: (z[0].y0 + z[0].y1) / 2):
        c = (r.y0 + r.y1) / 2
        key = next((k for k in rows if abs(k - c) <= tol), c)
        rows[key].append((r, t))
    for c, items in sorted(rows.items()):
        items.sort(key=lambda z: z[0].x0)
        words = [t.upper() for _r, t in items]
        if words[:3] == list(CAPTION):
            return c, items
    return None, []


def main() -> int:
    pdf = sys.argv[1]
    take = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    doc, pages = pidcache.load_pages(pdf)
    p0 = pages[0]
    print("## %s" % Path(pdf).name)
    print("종이 %.1f x %.1f pt · 회전 %s · 쪽 %d"
          % (p0.width, p0.height, p0.source_rotation, len(pages)))

    fr = dl._frame(pages)
    if fr is None:
        print("★ 테두리 괘선을 못 찾았습니다")
        return 0
    left, top, right, bottom, column, _xs, _ys = fr
    print("테두리 left %.1f top %.1f right %.1f bottom %.1f · 타이틀블록 열 x>=%.1f"
          % (left, top, right, bottom, column))

    pc, ws = column_words(pages, column)
    hs = [r.height for r, _t in ws]
    letter = statistics.median(hs)
    tol = letter / 4.0
    print("기준 장 p%d · 열 낱말 %d개 · 글자 높이 중앙 %.2f → 줄 허용치 %.2f"
          % (pc.page_no, len(ws), letter, tol))

    cy, items = caption_row(ws, tol)
    if cy is None:
        print("★ `REV. DATE DESCRIPTION` 캡션이 이 열에 없습니다 — 이 경로로 유도 불가")
        return 0
    print("캡션 줄 중심 y=%.2f" % cy)
    for r, t in items[:6]:
        print("     x %8.1f ~ %8.1f  y %8.2f~%8.2f  %s" % (r.x0, r.x1, r.y0, r.y1, t))
    cap_bottom = max(r.y1 for r, _t in items)

    # 캡션 아래의 가로 괘선 — 그 열 안에서만, 장별로
    for p in pages[:take]:
        rules = [(round(r.y0, 2), round(r.x0, 1), round(r.x1, 1), round(abs(r.height), 3))
                 for r in p.rects()
                 if abs(r.height) < 1.0 and r.x1 > column and r.y0 > cap_bottom]
        rules.sort()
        span = collections.Counter((a, b) for _y, a, b, _h in rules)
        print("  p%d — 캡션 아래 가로 괘선 %d개 · 서로 다른 x 범위 %d"
              % (p.page_no, len(rules), len(span)))
        for (a, b), n in span.most_common(2):
            band = sorted(r for r in rules if (r[1], r[2]) == (a, b))
            gaps = [round(band[i + 1][0] - band[i][0], 2) for i in range(len(band) - 1)]
            print("     x %8.1f ~ %8.1f  ×%d  y %.2f~%.2f  두께 %s"
                  % (a, b, n, band[0][0], band[-1][0],
                     sorted({h for _y, _a, _b, h in band})))
            if gaps:
                print("        행 높이 %s · 중앙 %.2f · 최소 %.2f · 최대 %.2f · 표본 %d"
                      % (sorted(set(gaps))[:6], statistics.median(gaps),
                         min(gaps), max(gaps), len(gaps)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
