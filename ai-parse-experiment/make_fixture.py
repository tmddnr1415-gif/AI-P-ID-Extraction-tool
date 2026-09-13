"""배관 검증용 합성 P&ID 를 만든다. **정확도 측정용이 아니다.**

실제 도면(AL NOUF1)과 발주처 정답지는 기밀이라 저장소에 없다.
그래서 이 실험의 파이프라인이 실제로 도는지를 보이려면 넣을 것이 필요하다.
이 파일이 만드는 것은 그 용도이며, 여기서 나온 숫자는 **판독 성적이 아니다.**

만드는 것: 계기 버블 · 타이틀블록 · NOTES(별표 정의 + 승수) 를 가진 A1 장 3쪽.
텍스트 레이어가 살아 있으므로 render.py 의 결정적 추출이 그대로 동작한다.
"""

from __future__ import annotations

import json
from pathlib import Path

import fitz

A1_W, A1_H = 2384, 1684  # pt (약 33"×23")

# (페이지, 도면번호, 제목, 계통, 계기 목록[(토큰, x비율, y비율, 벤더별표)], NOTES)
SHEETS = [
    (
        "D00P-10LBA10-M05-0001",
        "P&ID FOR HP STEAM SYSTEM GROUP 10",
        [("PT", .18, .30, False), ("PT", .18, .38, False),
         ("TT", .34, .30, False), ("TT", .34, .38, False),
         ("TT", .50, .30, True), ("TT", .50, .38, True),
         ("ZS", .66, .34, False)],
        ["GENERAL NOTES :",
         "1. * DENOTES EQUIPMENT WILL BE SUPPLIED BY HRSG VENDOR.",
         "2. THIS P&ID IS FOR UNIT 3-1. AND, SIMILAR FOR 3-2",
         "3. REFER TO SYMBOL AND LEGEND SHEET."],
    ),
    (
        "D00P-10PGB10-M05-0004",
        "P&ID FOR CLOSED COOLING WATER SYSTEM GROUP 10",
        [("PT", .20, .28, False), ("TT", .20, .44, False),
         ("TT", .40, .28, False), ("TT", .40, .44, False),
         ("LT", .60, .36, False), ("FE", .74, .36, False), ("FT", .80, .36, False)],
        ["NOTES :",
         "1. CONFIGURATION IS IDENTICAL FOR GROUP#20",
         "2. GENERATOR HYDROGEN GAS COOLER CCW SUPPLY"],
    ),
    (
        "D00P-00GEN00-M05-0001",
        "SYMBOL AND LEGEND",
        [],
        ["LEGEND :", "PT  PRESSURE TRANSMITTER", "TT  TEMPERATURE TRANSMITTER",
         "*   VENDOR SUPPLIED ITEM"],
    ),
]

EQUIP = ["HP STEAM HEADER", "BFP A/B MOTOR COOLER", "CLEAN DRAIN TANK"]
LINES = ["FROM HRSG#11 MAIN", "TO HP BYPASS#11 VALVE", "CCW SUPPLY HEADER"]


def build(out_pdf: Path) -> dict:
    doc = fitz.open()
    truth = []
    for idx, (dno, title, insts, notes) in enumerate(SHEETS, start=1):
        page = doc.new_page(width=A1_W, height=A1_H)
        page.draw_rect(fitz.Rect(30, 30, A1_W - 30, A1_H - 30), color=(0, 0, 0), width=2)

        # 타이틀블록 — 우하단
        page.draw_rect(fitz.Rect(A1_W * .58, A1_H * .80, A1_W - 40, A1_H - 40), width=1.5)
        page.insert_text((A1_W * .60, A1_H * .86), title, fontsize=20)
        page.insert_text((A1_W * .60, A1_H * .91), dno, fontsize=20)
        page.insert_text((A1_W * .60, A1_H * .95), "AL NOUF1 PROJECT / SAMSUNG", fontsize=13)

        # NOTES — 우상단
        for k, line in enumerate(notes):
            page.insert_text((A1_W * .74, A1_H * (.10 + k * .035)), line, fontsize=14)

        # 설비 · 배관 라벨
        for k, e in enumerate(EQUIP[:2]):
            page.insert_text((A1_W * .12, A1_H * (.58 + k * .06)), e, fontsize=15)
        for k, l in enumerate(LINES[:2]):
            page.insert_text((A1_W * .12, A1_H * (.18 + k * .045)), l, fontsize=15)

        # 계기 버블
        for tok, fx, fy, vendor in insts:
            cx, cy, r = A1_W * fx, A1_H * fy, 34
            page.draw_circle(fitz.Point(cx, cy), r, width=1.6)
            page.insert_text((cx - 18, cy - 4), tok, fontsize=17)
            page.insert_text((cx - 14, cy + 18), ".....", fontsize=15)
            if vendor:
                page.insert_text((cx + r + 4, cy - r + 8), "*", fontsize=20)
            truth.append({
                "page": idx, "token": tok, "vendor": vendor,
                "rect": [round((cx - r) / A1_W, 4), round((cy - r) / A1_H, 4),
                         round((cx + r) / A1_W, 4), round((cy + r) / A1_H, 4)],
            })

    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_pdf))
    doc.close()
    return {"sheets": [s[0] for s in SHEETS], "symbols": truth}


if __name__ == "__main__":
    import sys
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "out/fixture/synthetic_pid.pdf")
    meta = build(out)
    (out.parent / "synthetic_truth.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{out} — {len(meta['sheets'])}장, 심볼 {len(meta['symbols'])}개")
