"""47회차 — 고른 행 둘레를 크게 잘라 붙인다 (새로 난 행이 진짜인가를 눈으로 본다).

    python3 spike/crop_rows.py <결과.json> <PDF> <내보낼폴더> <장:i,장:i,...> [꼬리표]

장:i 는 그 장의 i 번째(0부터) 대상 행이다.  대상은 `--tab` 없이는 밸브 탭
(MOV·PNEUMATIC·BFV) 이고, 잘라내는 반경은 그 행 사각형의 긴 변 × 8 이다
(상수가 아니라 그 행이 정한다).

★ 실 DB 를 열지 않는다 (17회차 격리) — 결과 json 과 PDF 만 읽는다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import fitz

ZOOM = 8.0
PAD_RATIO = 8.0
VALVE_TABS = ("MOV", "PNEUMATIC", "BFV")


def main() -> int:
    src, pdf_path, outdir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    picks = [x for x in sys.argv[4].split(",") if x]
    tag = sys.argv[5] if len(sys.argv) > 5 else "crop"
    outdir.mkdir(parents=True, exist_ok=True)
    result = json.loads(src.read_text())["result"]
    rows = result["rows"]
    doc = fitz.open(pdf_path)
    for pick in picks:
        page_no, idx = pick.split(":")
        page_no, idx = int(page_no), int(idx)
        here = [r for r in rows if r["page_no"] == page_no and r.get("tab") in VALVE_TABS]
        if idx >= len(here):
            print(f"p{page_no}:{idx} — 그 장의 밸브 행은 {len(here)}개뿐")
            continue
        r = here[idx]
        x0, y0, x1, y1 = r["rect"]
        pad = max(x1 - x0, y1 - y0) * PAD_RATIO
        page = doc[page_no - 1]
        clip = fitz.Rect(x0 - pad, y0 - pad, x1 + pad, y1 + pad) & page.rect
        pm = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), clip=clip)
        out = outdir / f"{tag}_p{page_no}_{idx}.png"
        pm.save(out)
        ev = r.get("evidence", {})
        print(f"{out.name}  {r['type']} · {r.get('valve_type')} · {r['scope']} · "
              f"몸체 {ev.get('body')} · 액추에이터 {ev.get('actuator')} "
              f"({ev.get('actuator_basis')}) · rect {r['rect']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
