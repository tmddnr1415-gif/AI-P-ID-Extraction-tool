"""45회차 — 고른 장을 도면 그대로 렌더하고 그 위에 검출 상자를 얹는다.

    python3 spike/shot_pages.py <결과.json> <PDF> <내보낼폴더> <장,장,...> [꼬리표]

UI 를 띄우지 않는다 (장을 직접 고르기 위해서다 — `shot_overlay.py` 는 행이
있는 장만 균등 간격으로 뽑으므로 **행이 0 인 장을 찍을 수 없다**).
색은 `app/static/app.js` 의 SCOPE 네 갈래와 같은 뜻으로 쓰되, 여기서는
사람이 전·후를 비교하는 용도이므로 상자와 숫자만 얹는다.

★ 실 DB 를 열지 않는다 (17회차 격리) — 결과 json 과 PDF 만 읽는다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import fitz

ZOOM = 2.0
COLOR = {"SCT": (0.05, 0.45, 0.95), "VENDOR": (0.90, 0.35, 0.05)}
GREY = (0.45, 0.45, 0.45)


def scope_colour(scope: str):
    if not scope:
        return GREY
    return COLOR["SCT"] if scope.upper().startswith("SCT") else COLOR["VENDOR"]


def main() -> int:
    src, pdf_path, outdir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    pages = [int(x) for x in sys.argv[4].split(",")]
    tag = sys.argv[5] if len(sys.argv) > 5 else "shot"
    outdir.mkdir(parents=True, exist_ok=True)
    blob = json.loads(src.read_text())
    result = blob["result"]
    rows = result["rows"]
    pinfo = {int(p["page_no"]): p for p in result["pages"]}

    doc = fitz.open(pdf_path)
    made = []
    for no in pages:
        page = doc[no - 1]
        mine = [r for r in rows if int(r["page_no"]) == no]
        shape = page.new_shape()
        for r in mine:
            rect = r.get("rect")
            if not rect:
                continue
            box = fitz.Rect(*rect)
            shape.draw_rect(box)
            shape.finish(color=scope_colour(r.get("scope") or ""), width=1.6)
        shape.commit(overlay=True)
        pm = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM))
        out = outdir / f"{tag}_p{no:02d}.png"
        pm.save(out)
        info = pinfo.get(no, {})
        made.append((no, len(mine), info.get("page_kind", "?"),
                     info.get("drawing_no", ""), out.stat().st_size))
    for no, n, kind, dwg, size in made:
        print(f"p{no:<3} rows={n:<4} kind={kind:<8} dwg={dwg or '-':<24} {size//1024}KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
