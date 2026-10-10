"""[B]★ 캡션 없이 이력 표를 찾을 수 있는가 — 모양으로만 본다.

AL NOUF1 은 `REV. DATE DESCRIPTION` 을 **인쇄하지 않는다** (찾은 캡션은
dwg_no · project_name · project_no · title 넷뿐).  그래서 캡션 앵커만으로는
기준선 문서가 빠진다.  대신 **표의 모양**으로 찾을 수 있는지 잰다:

    타이틀블록 열을 가로지르는 괘선 중,
    간격이 서로 같은 것이 연달아 여러 줄 있는 띠

23회차 원리 그대로 — 절대 pt 가 아니라 **모양**이다.

    python3 spike/hist_shape_probe.py <pdf> [장 수]
"""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))
sys.path.insert(0, str(ROOT / "spike"))

import pymupdf                                    # noqa: E402
from app.engine import pidcache                   # noqa: E402
from app.engine import derive_layout as dl        # noqa: E402
from app.engine import extract_titleblocks as tb  # noqa: E402
import hist_measure as hm                         # noqa: E402


def runs_of_equal_gaps(ys, rel_tol=0.05):
    """간격이 서로 (상대오차 안에서) 같은 연속 구간들."""
    out, i = [], 0
    gaps = [ys[k + 1] - ys[k] for k in range(len(ys) - 1)]
    while i < len(gaps):
        j = i
        while j + 1 < len(gaps) and abs(gaps[j + 1] - gaps[i]) <= rel_tol * gaps[i]:
            j += 1
        if j > i:                      # 최소 두 간격 = 괘선 세 줄
            out.append((i, j, ys[i], ys[j + 1], statistics.median(gaps[i:j + 1])))
        i = j + 1
    return out


def main() -> int:
    pdf = sys.argv[1]
    take = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    doc, pages = pidcache.load_pages(pdf)
    left, top, right, bottom, column, xs, _ys = dl._frame(pages)
    # 표의 오른쪽 끝은 시트 가장자리가 아니라 **노트 열의 안쪽 괘선**이다 —
    # AL NOUF1 은 거기서 멈춘다 (2330.3 ↔ 시트 끝 2345.3).  이미 유도되는 값이다.
    inner = [x for x in xs if column < x < right]
    edge = inner[-1] if inner else right
    pc, ws = hm.column_words(pages, column)
    letter = statistics.median([r.height for r, _t in ws])
    cy, items = hm.caption_row(ws, letter / 4)
    print("## %s" % Path(pdf).name)
    print("열 x>=%.1f · 표 오른쪽 끝 %.1f (시트 끝 %.1f) · 글자 높이 %.2f · 이력 캡션 %s"
          % (column, edge, right, letter, "있음 y=%.2f" % cy if cy else "없음"))

    for p in pages[:take]:
        ys = sorted({round(r.y0, 2) for r in p.rects()
                     if abs(r.height) < 1.0
                     and r.x0 <= column + letter and r.x1 >= edge - letter})
        print("  p%d — 표 폭 괘선 %d줄" % (p.page_no, len(ys)))
        for a, b, y0, y1, gap in runs_of_equal_gaps(ys):
            n = b - a + 1
            print("     띠: 괘선 %d줄 · y %.2f~%.2f · 행 높이 %.2f (행 %d개)"
                  % (n + 1, y0, y1, gap, n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
