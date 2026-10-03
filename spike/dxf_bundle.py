"""32장 raw+overlay 를 한 장 PDF 로 묶고 [F] 표를 쓴다 (55회차).

    python3 spike/dxf_bundle.py out/round55_uad_dxf out/round55/UAD_DXF.json out/round45/UAD_after.json
"""
import json, sys, collections
from pathlib import Path
from PIL import Image, ImageDraw

D = Path(sys.argv[1]); dxf = json.loads(Path(sys.argv[2]).read_text()); dxf = dxf.get("result", dxf)
pdf = json.loads(Path(sys.argv[3]).read_text()); pdf = pdf.get("result", pdf)
table = json.loads((D / "table.json").read_text())
pp = collections.Counter(r["page_no"] for r in pdf["rows"])
pages = []
for t in table:
    n = t["page"]
    ims = []
    for kind in ("raw", "overlay"):
        f = D / f"p{n:02d}_{kind}.png"
        if f.exists():
            im = Image.open(f).convert("RGB")
            im.thumbnail((1600, 1100))
            ims.append(im)
    if not ims:
        continue
    W = max(i.width for i in ims); H = sum(i.height for i in ims) + 60 * len(ims) + 40
    page = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(page)
    y = 10
    d.text((10, y), f"p{n}  {t['drawing_no']}  ·  {t['kind']}  ·  등급 {t['tier']}  ·  DXF 행 {t['rows']} (상자 {t['boxes']})  ·  PDF 행 {pp.get(n, 0)}", fill="black")
    y += 30
    for im, kind in zip(ims, ("원본 렌더", "식별 오버레이")):
        d.text((10, y), kind, fill=(90, 90, 90)); y += 20
        page.paste(im, (0, y)); y += im.height + 40
    pages.append(page)
out = D / "UAD_DXF_32장.pdf"
pages[0].save(out, save_all=True, append_images=pages[1:], resolution=100)
L = ["# [F] UAD DXF 32장 — 원본 · 오버레이 · 표 (55회차)", "",
     f"그림: `{D}/p<번호>_raw.png` · `p<번호>_overlay.png` · 한 장 묶음 `{out.name}` ({len(pages)}장).", "",
     "| 장 | 도면번호 | 종류 | 등급 | DXF 행 | 상자 | 범례 칸 합 | PDF 행 | 차이 |", "| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |"]
eq_bad = 0
for t in table:
    n = t["page"]; diff = t["rows"] - pp.get(n, 0)
    if t["legend_sum"] != t["boxes"]: eq_bad += 1
    L.append(f"| {n} | {t['drawing_no']} | {t['kind']} | {t['tier']} | {t['rows']} | {t['boxes']} | {t['legend_sum']} | {pp.get(n,0)} | {diff:+d} |")
L += ["", f"33회차 등식(칸 합 = 상자 수) 어긋난 장: **{eq_bad}** · 합 DXF {sum(t['rows'] for t in table)} ↔ PDF {sum(pp.values())} (PDF 는 45회차 저장 결과 301행)", ""]
(D / "README.md").write_text("\n".join(L) + "\n", encoding="utf8")
print("→", out, len(pages), "장 · 등식 어긋남", eq_bad)
