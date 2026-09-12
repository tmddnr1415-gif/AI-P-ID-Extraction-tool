"""32회차 [D] — **스스로 깨뜨려 보려고** 만드는 합성 도면 여덟.

왜 처음부터 그리지 않는가
    범례·타이틀블록·ISA 표·버블을 손으로 그리면 그것은 *내가 아는 규칙*을
    그린 것이라, 통과해도 도구가 범용이라는 증거가 안 된다.  그래서 **실제
    도면(AL NOUF1)의 범례 4장 + P&ID 2장을 재료로 쓰고 한 축만 바꾼다** —
    종이 · 회전 · 줄 간격 · 범례 자리 · 범례 유무 · 이력 표 유무 · 태그.

만드는 방법 둘
    `copy`   `insert_pdf` — 원본을 **그대로** 옮긴다 (주석·글꼴 보존)
    `scale`  새 종이에 `show_pdf_page` — 내용이 **배율로 다시 그려진다**
             ⚠ 이 경로는 **주석을 옮기지 않는다** (UAD 의 SHX 글자가 그 예)

한계는 `out/round32/5_synthetic.md` 에 적는다.  합성은 실제 도면을 대표하지
않는다 — 획으로 그린 글자 · 개정 클라우드 · 패키지 상자 · 오탈자는 재현되지
않는다.

    python3 spike/make_synthetic.py            # 여덟 개를 만든다
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tests" / "data" / "synthetic"
SRC = ROOT / "data" / "pid_total.pdf"
LEGEND = [1, 2, 3, 4]          # 0-based — 범례 p2·p3·p4·p5
PID = [5, 6]                   # 0-based — P&ID p6·p7
A1 = (2384.0, 1684.0)
# 이력 표 띠 (AL NOUF1 config title_block) — ⑦ 이 이 띠를 **안 그린다**
HIST = (1960.0, 1190.0, 2384.0, 1400.0)


def _copy(pages, rotate=None) -> pymupdf.Document:
    """원본 그대로 — 쪽 나무만 바꾼다."""
    src = pymupdf.open(SRC)
    doc = pymupdf.open()
    for p in pages:
        doc.insert_pdf(src, from_page=p, to_page=p)
    if rotate is not None:
        for page in doc:
            page.set_rotation(rotate)
    src.close()
    return doc


def _scale(pages, size) -> pymupdf.Document:
    """새 종이에 배율로 다시 그린다 (주석은 따라오지 않는다)."""
    src = pymupdf.open(SRC)
    doc = pymupdf.open()
    w, h = size
    for p in pages:
        page = doc.new_page(width=w, height=h)
        page.show_pdf_page(pymupdf.Rect(0, 0, w, h), src, p)
    src.close()
    return doc


def _scale_without_history(pages, size) -> pymupdf.Document:
    """이력 표 띠만 **빼고** 그린다 — 덮지 않는다.

    흰 사각형으로 덮으면 괘선은 내용 스트림에 그대로 남아 `history_rows` 가
    찾아낸다.  그래서 그 띠를 **아예 안 그린다** (세 조각으로 나눠 옮긴다).
    """
    src = pymupdf.open(SRC)
    doc = pymupdf.open()
    w, h = size
    sx, sy = w / A1[0], h / A1[1]
    x0, y0, x1, y1 = HIST
    for p in pages:
        page = doc.new_page(width=w, height=h)
        for clip in (pymupdf.Rect(0, 0, x0, A1[1]),               # 왼쪽 전부
                     pymupdf.Rect(x0, 0, A1[0], y0),              # 오른쪽 위
                     pymupdf.Rect(x0, y1, A1[0], A1[1])):         # 오른쪽 아래
            page.show_pdf_page(
                pymupdf.Rect(clip.x0 * sx, clip.y0 * sy,
                             clip.x1 * sx, clip.y1 * sy), src, p, clip=clip)
    src.close()
    return doc


def _with_tags(size, rows_json: Path) -> pymupdf.Document:
    """A4 로 줄이고 **버블 안에 태그를 활자로 인쇄**한다 (⑧).

    태그는 검출 사각형 **안**에 있어야 한다 (`tags.assign` 이 교집합을 본다).
    자리는 그 도면의 실제 검출 좌표를 쓴다 — 지어낸 자리가 아니다.
    """
    blob = json.loads(rows_json.read_text())
    res = blob.get("result", blob)
    doc = _scale(PID, size)
    w, h = size
    sx, sy = w / A1[0], h / A1[1]
    want = {6: 0, 7: 1}                       # 원본 쪽번호 → 합성 쪽 index
    seq = {6: 0, 7: 0}
    for r in res["rows"]:
        pno = int(r["page_no"])
        if pno not in want:
            continue
        seq[pno] += 1
        rect = r["rect"]
        page = doc[want[pno]]
        # `00GKB01CL001A` 와 같은 모양 — 글자·숫자 run 이 되풀이되는 체계
        tag = "%02dLBA%02dCP%03d" % (10 + want[pno], 10 + seq[pno] % 7, seq[pno])
        x = rect[0] * sx + 1.0
        y = (rect[1] + rect[3]) / 2 * sy + 2.0
        page.insert_text((x, y), tag, fontsize=2.4, fontname="helv")
    return doc


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    made = []

    def save(doc, name, note):
        path = OUT / name
        doc.save(path, deflate=True)
        doc.close()
        made.append({"file": name, "note": note,
                     "bytes": path.stat().st_size})
        print(f"  {name:34s} {path.stat().st_size:>9,}B  {note}")

    print("합성 도면 — 재료는 AL NOUF1 범례 4장 + P&ID 2장")
    save(_scale(LEGEND + PID, (3370.0, 2384.0)), "01_a0.pdf",
         "A0 3370x2384 (배율 1.41)")
    save(_scale(LEGEND + PID, (842.0, 595.0)), "02_a4.pdf",
         "A4 842x595 (배율 0.353)")
    save(_copy(LEGEND + PID, rotate=90), "03a_rotate90.pdf", "/Rotate 90")
    save(_copy(LEGEND + PID, rotate=180), "03b_rotate180.pdf", "/Rotate 180")
    save(_scale(LEGEND + PID, (476.8, 336.8)), "04_tight_lines.pdf",
         "0.2 배 — 줄 간격이 버킷(5·7pt) 아래로 내려간다")
    save(_copy(PID + LEGEND), "05_legend_last.pdf", "범례가 마지막 장")
    save(_copy(PID), "06_no_legend.pdf", "범례 없음")
    save(_scale_without_history(LEGEND + PID, A1), "07_no_history.pdf",
         "이력 표 띠를 안 그림")
    save(_with_tags((842.0, 595.0), ROOT / "out" / "regression_3p" / "AL_NOUF1.json"),
         "08_a4_tagged.pdf", "A4 + 버블 안에 태그 활자")

    (OUT / "README.md").write_text(
        "# 합성 시험 도면 (32회차 [D])\n\n"
        "`spike/make_synthetic.py` 가 만든다.  재료는 **AL NOUF1 범례 4장 +\n"
        "P&ID 2장**이고 각 파일은 **한 축만** 바꾼다.  결과는\n"
        "`out/round32/5_synthetic.md` 에 있다.\n\n"
        "| 파일 | 바꾼 축 |\n| --- | --- |\n"
        + "".join(f"| `{m['file']}` | {m['note']} |\n" for m in made)
        + "\n⚠ **합성은 실제 도면을 대표하지 않는다** — 배율 경로(`show_pdf_page`)는\n"
          "주석을 옮기지 않으므로 UAD 의 SHX 글자 같은 것은 재현되지 않고, 개정\n"
          "클라우드 · 패키지 상자 · 도면 오탈자도 여기에 없다.\n",
        encoding="utf-8")
    print(f"{len(made)}개 · {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
