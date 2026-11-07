"""[B]★ 이력 표의 열 경계를 세로 괘선으로 가를 수 있는가 (24회차).

앞 실측이 정한 것: **간격이 서로 같은 괘선 띠**가 세 문서 전부에 있고, 그중
**위쪽(= 행이 더 촘촘한 쪽)** 이 이력 표다.  여기서는 그 띠를 가로지르는
**세로 괘선**으로 REV·DATE 열을 가를 수 있는지 잰다.  전부 모양이고 절대 pt 가 없다.

    python3 spike/hist_cols_probe.py <pdf> [장 수]
"""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))
sys.path.insert(0, str(ROOT / "spike"))

from app.engine import pidcache               # noqa: E402
from app.engine import derive_layout as dl    # noqa: E402
import hist_measure as hm                     # noqa: E402
from hist_shape_probe import runs_of_equal_gaps  # noqa: E402


def main() -> int:
    pdf = sys.argv[1]
    take = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    doc, pages = pidcache.load_pages(pdf)
    left, top, right, bottom, column, xs, _ys = dl._frame(pages)
    inner = [x for x in xs if column < x < right]
    edge = inner[-1] if inner else right
    pc, ws = hm.column_words(pages, column)
    letter = statistics.median([r.height for r, _t in ws])
    cy, items = hm.caption_row(ws, letter / 4)
    cap = {t.upper(): r for r, t in items} if cy else {}
    print("## %s" % Path(pdf).name)
    print("열 %.1f~%.1f · 글자 %.2f · 캡션 %s"
          % (column, edge, letter, "있음" if cap else "없음"))
    if cap:
        print("   캡션 REV. x %.1f~%.1f · DATE x %.1f~%.1f"
              % (cap["REV."].x0, cap["REV."].x1, cap["DATE"].x0, cap["DATE"].x1))

    for p in pages[:take]:
        ys = sorted({round(r.y0, 2) for r in p.rects()
                     if abs(r.height) < 1.0
                     and r.x0 <= column + letter and r.x1 >= edge - letter})
        bands = runs_of_equal_gaps(ys)
        if not bands:
            print("  p%d — 균일 띠 없음" % p.page_no); continue
        bands.sort(key=lambda b: b[4])          # 행이 촘촘한 쪽이 이력 표
        _a, _b, y0, y1, gap = bands[0]
        print("  p%d — 이력 띠 y %.2f~%.2f · 행 높이 %.2f (띠 %d개 중 가장 촘촘)"
              % (p.page_no, y0, y1, gap, len(bands)))
        # 그 띠를 세로로 가로지르는 괘선 = 열 경계
        vx = sorted({round(r.x0, 2) for r in p.rects()
                     if abs(r.width) < 1.0
                     and r.y0 <= y0 + gap and r.y1 >= y1 - gap
                     and column - letter <= r.x0 <= edge + letter})
        print("     열 경계 %d개: %s" % (len(vx), [round(v, 1) for v in vx][:10]))
        if len(vx) >= 3:
            print("     → 1열 %.1f~%.1f · 2열 %.1f~%.1f"
                  % (vx[0], vx[1], vx[1], vx[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
