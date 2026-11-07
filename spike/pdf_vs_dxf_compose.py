"""PDF 결과 ↔ DXF 결과를 한 장에 나란히 놓는다 (측정 전용).

    python3 spike/pdf_vs_dxf_compose.py out/pdf_vs_dxf
"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

D = Path(sys.argv[1] if len(sys.argv) > 1 else "out/pdf_vs_dxf")
facts = {(f["kind"], f["page"]): f for f in json.loads((D / "facts.json").read_text())}
F = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FB = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
big = ImageFont.truetype(FB if Path(FB).exists() else F, 26)
mid = ImageFont.truetype(F, 19)
sml = ImageFont.truetype(F, 16)
PAGES = [11, 12, 13, 14, 15]
sheets = []
for n in PAGES:
    p = facts[("PDF", n)]; d = facts[("DXF", n)]
    left = Image.open(D / f"p{n}_PDF_grid.png").convert("RGB")
    grid = Image.open(D / f"p{n}_DXF_grid.png").convert("RGB")
    ovl = Image.open(D / f"p{n}_DXF_overlay.png").convert("RGB")
    for im in (left, grid):
        im.thumbnail((980, 760))
    ovl.thumbnail((980, 900))
    W = 2020
    H = 120 + max(left.height, grid.height + ovl.height + 40) + 40
    page = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(page)
    dr.text((20, 18), f"UAD  p{n}   {d['drawing_no']}", fill="black", font=big)
    dr.text((20, 56), f"같은 장을 PDF 로 읽으면 {p['rows']}행 · DXF 로 읽으면 {d['rows']}행",
            fill=(150, 0, 0) if p["rows"] < d["rows"] else "black", font=mid)
    dr.line([(0, 104), (W, 104)], fill=(200, 200, 200), width=2)
    dr.line([(1000, 104), (1000, H)], fill=(200, 200, 200), width=2)
    y = 120
    dr.text((20, y), f"① PDF 입력 — 행 {p['rows']}", fill=(120, 0, 0), font=mid)
    dr.text((20, y + 26), "⚠ 이 작업 환경에 UAD PDF 파일이 없어 도면 그림은 띄우지 못합니다.",
            fill=(120, 120, 120), font=sml)
    dr.text((20, y + 48), "   숫자는 45회차에 저장된 그 PDF 의 분석 결과에서 온 것입니다.",
            fill=(120, 120, 120), font=sml)
    page.paste(left, (20, y + 76))
    dr.text((1020, y), f"② DXF 입력 — 행 {d['rows']}", fill=(0, 90, 0), font=mid)
    page.paste(ovl, (1020, y + 30))
    page.paste(grid, (1020, y + 30 + ovl.height + 16))
    sheets.append(page)
out = Path("out/UAD_PDF_vs_DXF.pdf")
sheets[0].save(out, save_all=True, append_images=sheets[1:], resolution=100)
for n, im in zip(PAGES, sheets):
    im.save(D / f"비교_p{n}.png")
print("→", out, len(sheets), "장")
