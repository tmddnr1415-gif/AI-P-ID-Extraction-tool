"""[B]★ 이력 표를 캡션으로 찾으면 그 안에 무엇이 있는가 — 위치와 문자를 갈라 잰다.

이력 표는 **위치**를 주고 글리프 사전은 **문자**를 준다.  둘은 다른 것이므로
따로 답한다: (1) 표 폭 괘선이 몇 줄인가 (2) 그 REV 칸에 획이 실제로 있는가.

    python3 spike/hist_rows_probe.py <pdf> [장 수]
"""
from __future__ import annotations

import collections
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))
sys.path.insert(0, str(ROOT / "spike"))

import pymupdf                                   # noqa: E402
from app.engine import pidcache                  # noqa: E402
from app.engine import derive_layout as dl       # noqa: E402
from app.engine import extract_titleblocks as tb  # noqa: E402
import hist_measure as hm                        # noqa: E402


def main() -> int:
    pdf = sys.argv[1]
    take = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    doc, pages = pidcache.load_pages(pdf)
    fr = dl._frame(pages)
    left, top, right, bottom, column, _xs, _ys = fr
    pc, ws = hm.column_words(pages, column)
    letter = statistics.median([r.height for r, _t in ws])
    cy, items = hm.caption_row(ws, letter / 4)
    if cy is None:
        print("★ 캡션 없음"); return 0
    cap = {t.upper(): r for r, t in items}
    cap_top = min(r.y0 for r in cap.values())
    cap_bot = max(r.y1 for r in cap.values())
    print("## %s" % Path(pdf).name)
    print("타이틀블록 열 x>=%.1f · 오른쪽 끝 %.1f · 캡션 y %.2f~%.2f"
          % (column, right, cap_top, cap_bot))
    print("REV. x %.1f~%.1f · DATE x %.1f~%.1f"
          % (cap["REV."].x0, cap["REV."].x1, cap["DATE"].x0, cap["DATE"].x1))

    for p in pages[:take]:
        # 표 폭 괘선 — 왼쪽이 열 경계 근처에서 시작해 오른쪽 끝까지 간다
        wide = sorted({round(r.y0, 2) for r in p.rects()
                       if abs(r.height) < 1.0
                       and r.x0 <= column + letter and r.x1 >= right - letter})
        above = [y for y in wide if y < cap_top]
        below = [y for y in wide if y > cap_bot]
        print("  p%d — 표 폭 괘선 %d줄 (캡션 위 %d · 아래 %d)"
              % (p.page_no, len(wide), len(above), len(below)))
        for side, ys in (("위", above), ("아래", below)):
            if len(ys) < 2:
                continue
            gaps = [round(ys[i + 1] - ys[i], 2) for i in range(len(ys) - 1)]
            print("     %s: y %.2f~%.2f · 간격 %s · 중앙 %.2f"
                  % (side, ys[0], ys[-1], sorted(set(gaps))[:6], statistics.median(gaps)))
            # 그 띠들의 REV 칸에 획이 있는가 — 아래에서 위로 A·B·C 순
            bands = list(zip(ys, ys[1:]))[::-1]
            for i, (y0, y1) in enumerate(bands[:6]):
                clip = pymupdf.Rect(cap["REV."].x0, y0 + 1.0,
                                    cap["REV."].x1, y1 - 1.0)
                if clip.height <= 0:
                    print("        %d행 y %.2f~%.2f  ★ 높이 0 이하 (inset 이 행보다 큼)"
                          % (i, y0, y1)); continue
                chars = tb.segment_chars(p.page, clip, tb.LAYOUT)
                words = [t for r, t in p.words
                         if clip.x0 <= r.x0 and r.x1 <= clip.x1
                         and clip.y0 <= r.y0 and r.y1 <= clip.y1]
                print("        %d행 y %8.2f~%8.2f 높이 %5.2f · 획덩이 %d · 텍스트 %s"
                      % (i, y0, y1, y1 - y0, len(chars), words[:3]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
