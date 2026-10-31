"""hotfix86 — '도면 가르치기' 할 일 목록의 **예시 그림**을 만든다.

할 일마다 "다른 프로젝트에서는 무엇을 어떻게 눌렀나" 를 보인다.  그림은 저장소에 있는
두 문서(AL NOUF1 · QFE)를 그대로 잘라 누를 자리에 붉은 상자와 손가락 표시를 그린 것이고,
설명 글자는 그림에 넣지 않는다 (화면 HTML 이 말한다 — 한글 글꼴을 그림에 묻히지 않으려고).

    python3 spike/teach_examples.py          # app/static/img/teach/*.png 를 다시 만든다

PDF 가 없는 기계에서는 그렇게 말하고 멈춘다 (그림은 저장소에 이미 있다).
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "app" / "static" / "img" / "teach"
NOUF1 = ROOT / "data" / "pid_total.pdf"
QFE = ROOT / "data" / "QFE_260326.pdf"

RED = (214, 40, 40)
GREEN = (15, 143, 128)
BLUE = (47, 91, 216)


def crop(pdf: Path, page_no: int, clip, width_px: int) -> tuple[Image.Image, float]:
    """한 장의 `clip`(pt) 을 가로 `width_px` 로.  돌려주는 것은 그림과 pt→px 배율."""
    doc = pymupdf.open(str(pdf))
    page = doc[page_no - 1]
    r = pymupdf.Rect(clip)
    zoom = width_px / r.width
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=r, alpha=False)
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    return img, zoom


def _px(rect, clip, zoom):
    return [(rect[0] - clip[0]) * zoom, (rect[1] - clip[1]) * zoom,
            (rect[2] - clip[0]) * zoom, (rect[3] - clip[1]) * zoom]


def box(draw, rect, color=RED, pad=4, width=4):
    x0, y0, x1, y1 = rect
    draw.rounded_rectangle([x0 - pad, y0 - pad, x1 + pad, y1 + pad], radius=6,
                           outline=color, width=width)


def finger(draw, x, y, color=RED):
    """누르는 자리 — 화살 끝이 (x, y)."""
    draw.polygon([(x, y), (x + 34, y + 12), (x + 20, y + 18), (x + 30, y + 40),
                  (x + 22, y + 44), (x + 12, y + 22), (x + 2, y + 34)], fill=color,
                 outline=(255, 255, 255))


def shade(img, rect, color=GREEN, alpha=48):
    over = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(over).rectangle(rect, fill=color + (alpha,), outline=color + (220,), width=3)
    return Image.alpha_composite(img.convert("RGBA"), over).convert("RGB")


def border(img, color=(214, 208, 196)):
    ImageDraw.Draw(img).rectangle([0, 0, img.width - 1, img.height - 1], outline=color, width=2)
    return img


def save(img, name):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    img.save(path, optimize=True)
    print(f"{path.relative_to(ROOT)}  {img.width}x{img.height}  {path.stat().st_size // 1024}KB")


def dwg_no():
    """도면번호 — 타이틀블록에 인쇄된 이 장의 번호 글자를 누른다."""
    for pdf, name, clip, word in (
            (NOUF1, "ex_dwgno_1.png", (1880, 1470, 2384, 1684), (2070, 1579, 2203, 1597)),
            (QFE, "ex_dwgno_2.png", (1980, 1520, 2384, 1684), (2123, 1620, 2241, 1630))):
        img, z = crop(pdf, 6, clip, 520)
        d = ImageDraw.Draw(img)
        w = _px(word, clip, z)
        box(d, w)
        finger(d, w[2] - 6, w[3] + 2)
        save(border(img), name)


def legend():
    """범례 장 — 밸브·액추에이터 기호표가 그려진 장 (O) · 배관이 그려진 P&ID 장 (X)."""
    doc = pymupdf.open(str(NOUF1))
    full = (0, 0, doc[1].rect.width, doc[1].rect.height)
    img, z = crop(NOUF1, 2, full, 420)
    d = ImageDraw.Draw(img)
    words = doc[1].get_text("words")
    for a, b in zip(words, words[1:]):           # 칸 제목 `LINE VALVES` (큰 글자)만
        if a[4] == "LINE" and b[4] == "VALVES" and a[3] - a[1] > 20:
            box(d, _px((a[0], a[1], b[2], b[3]), full, z), pad=8, width=3)
    save(border(img, GREEN), "ex_legend_yes.png")
    img, z = crop(NOUF1, 6, full, 420)
    save(border(img, RED), "ex_legend_no.png")


def bubble():
    """계기 버블 — PT·TT 같은 글자가 든 원·타원의 글자를 누른다."""
    for pdf, name, clip, rect in (
            (NOUF1, "ex_bubble_1.png", (395, 400, 560, 530), (431.3, 437.4, 499.3, 460.1)),
            (QFE, "ex_bubble_2.png", (1560, 410, 1720, 520), (1605.4, 450.7, 1673.4, 473.3))):
        img, z = crop(pdf, 6, clip, 360)
        d = ImageDraw.Draw(img)
        b = _px(rect, clip, z)
        box(d, b, pad=6)
        finger(d, b[2] - 6, b[3] - 4)              # 버블 오른쪽 아래 — 글자를 가리지 않게
        save(border(img), name)


def notes():
    """NOTES — 제목 글자를 누르면 그 아래 노트 칸을 읽는다 (초록)."""
    for pdf, name, clip, word, area in (
            (NOUF1, "ex_notes_1.png", (1940, 40, 2384, 420), (2033, 63, 2067, 77), (1968, 58, 2350, 420)),
            (QFE, "ex_notes_2.png", (1990, 40, 2384, 380), (2068, 62, 2095, 71), (2015, 56, 2370, 380))):
        img, z = crop(pdf, 6, clip, 420)
        img = shade(img, _px(area, clip, z))
        d = ImageDraw.Draw(img)
        w = _px(word, clip, z)
        box(d, w)
        finger(d, w[2] + 2, (w[1] + w[3]) / 2)
        save(border(img), name)


def main():
    missing = [p for p in (NOUF1, QFE) if not p.exists()]
    if missing:
        sys.exit("PDF 가 없습니다: " + ", ".join(str(p) for p in missing)
                 + " — 예시 그림은 저장소의 app/static/img/teach/ 에 이미 있습니다.")
    dwg_no(); legend(); bubble(); notes()


if __name__ == "__main__":
    main()
