"""같은 도면을 **다른 종이 크기로** 다시 낸다 — 종이 크기에 판정이 흔들리는지 재는 도구.

    python3 spike/rescale_pdf.py 원본.pdf 출력.pdf 배율 [장수]

쪽을 제자리에서 바꾼다: 내용 스트림 앞에 `cm` 한 줄(배율)을 얹고 쪽 상자를 그만큼 키운다.
글꼴·회전·선이 그대로다 (`show_pdf_page` 로 옮기면 TC2 한 장의 낱말이 594 → 179 로 준다 —
실측).  회전 0 인 쪽의 주석(SHX 글자)은 사각형도 같은 배율로 옮긴다.
"""
import sys
import pymupdf

src, out, s = sys.argv[1], sys.argv[2], float(sys.argv[3])
n = int(sys.argv[4]) if len(sys.argv) > 4 else 0
d = pymupdf.open(src)
if n and n < len(d):
    d.select(list(range(n)))
for p in d:
    mb = p.mediabox
    p.clean_contents()
    for x in p.get_contents():
        body = d.xref_stream(x)
        d.update_stream(x, b"q %.6f 0 0 %.6f %.4f %.4f cm\n" % (s, s, -mb.x0 * s, -mb.y0 * s)
                        + body + b"\nQ\n")
    # 주석(SHX 글자 · 검토 메모)은 **PDF 좌표의 /Rect** 를 같은 배율로 — 회전과 무관하게.
    # (`annot.set_rect` 는 회전된 표시 좌표를 받아 270° 쪽에서 엉뚱한 자리로 간다.)
    for ax in (d.xref_get_key(p.xref, "Annots")[1] or "").replace("[", " ").replace("]", " ").split(" R"):
        ax = ax.strip().split(" ")[0] if ax.strip() else ""
        if not ax.isdigit():
            continue
        kind, val = d.xref_get_key(int(ax), "Rect")
        if kind != "array":
            continue
        nums = [float(v) for v in val.strip("[]").split()]
        d.xref_set_key(int(ax), "Rect", "[" + " ".join(f"{(v - (mb.x0 if i % 2 == 0 else mb.y0)) * s:.4f}"
                                                      for i, v in enumerate(nums)) + "]")
    box = f"[0 0 {mb.width * s:.4f} {mb.height * s:.4f}]"
    for k in ("MediaBox", "CropBox", "TrimBox", "BleedBox", "ArtBox"):
        if k == "MediaBox" or d.xref_get_key(p.xref, k)[0] != "null":
            d.xref_set_key(p.xref, k, box)
d.save(out, garbage=3)
p = d[0]
print(out, len(d), round(p.rect.width), round(p.rect.height))
