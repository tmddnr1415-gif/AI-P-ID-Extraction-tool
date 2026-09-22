"""p11~p15 그림을 한 장 PDF 로 묶고 README 표를 쓴다 (측정 전용).

    python3 spike/dxf_p11_p15_bundle.py out/uad_dxf_p11_p15 out/round55/UAD_DXF.json out/round45/UAD_after.json
"""
import collections, json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

D = Path(sys.argv[1]); dxf = json.loads(Path(sys.argv[2]).read_text()); dxf = dxf.get("result", dxf)
pdf = json.loads(Path(sys.argv[3]).read_text()); pdf = pdf.get("result", pdf)
facts = {f["page"]: f for f in json.loads((D / "facts.json").read_text())}
PAGES = [11, 12, 13, 14, 15]
FONT = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
font = ImageFont.truetype(FONT, 18) if Path(FONT).exists() else ImageFont.load_default()
small = ImageFont.truetype(FONT, 15) if Path(FONT).exists() else ImageFont.load_default()

rows = dxf["rows"]; un = dxf.get("unjudged_symbols") or []
pdf_rows = collections.Counter(r["page_no"] for r in pdf["rows"])
pages = {p["page_no"]: p for p in dxf["pages"]}
KINDS = ["p{}_1_raw.png", "p{}_2_overlay.png", "p{}_2b_overlay_zoom.png", "p{}_3_grid.png"]
CAPS = ["① 도면만 (오버레이 칸 전부 끔 · 맞춤)", "② 식별 오버레이 + 범례 (맞춤)",
        "②b 계기가 가장 몰린 구역 (확대 5.1배)", "③ 그 장 행 전부 (검색창에 도면번호)"]

stat, sheets = [], []
for n in PAGES:
    mine = [r for r in rows if r["page_no"] == n]
    f = facts[n]; p = pages[n]
    ty = collections.Counter(r.get("type") or "(빈칸)" for r in mine)
    src = collections.Counter((r.get("evidence") or {}).get("source") for r in mine)
    codes = collections.Counter()
    for r in mine:
        for c in ((r.get("evidence") or {}).get("review_codes") or []):
            codes[c] += 1
    stat.append({
        "page": n, "dwg": p["drawing_no"], "tier": f["tier"], "rows": len(mine),
        "boxes": f["boxes"], "legend": f["legend_sum"], "grid": f["grid_rows"],
        "tagged": sum(1 for r in mine if (r.get("tag_no") or "") not in ("", "....."))," ": "",
        "attr": src.get("DXF_ATTRIB", 0), "btext": src.get("DXF_BLOCK_TEXT", 0),
        "geom": src.get("DXF_GEOMETRY", 0), "types": ty, "codes": codes,
        "unjudged": [s for s in un if s["page_no"] == n], "pdf": pdf_rows.get(n, 0),
        "zoom": (f["zoom_fit"], f["zoom_dense"]), "centre": f["dense_centre"],
    })

# ── 한 장 PDF
for s in stat:
    n = s["page"]
    ims = [(Image.open(D / k.format(n)).convert("RGB"), c) for k, c in zip(KINDS, CAPS)
           if (D / k.format(n)).exists()]
    for im, _ in ims:
        im.thumbnail((1500, 1050))
    W = max(max(i.width for i, _ in ims), 1200) + 20
    H = sum(i.height for i, _ in ims) + 46 * len(ims) + 70
    page = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(page); y = 12
    d.text((10, y), f"p{n}  {s['dwg']}  ·  등급 {s['tier']}  ·  행 {s['rows']}"
                    f" (상자 {s['boxes']} · 범례 칸 합 {s['legend']} · 그리드 {s['grid']})"
                    f"  ·  태그 {s['tagged']}  ·  PDF 행 {s['pdf']}", fill="black", font=font)
    y += 34
    for im, cap in ims:
        d.text((10, y), cap, fill=(90, 90, 90), font=small); y += 22
        page.paste(im, (10, y)); y += im.height + 24
    sheets.append(page)
out = Path("out/uad_dxf_p11_p15.pdf")
sheets[0].save(out, save_all=True, append_images=sheets[1:], resolution=100)

# ── README
L = ["# UAD DXF p11~p15 — 식별 결과 화면 (측정 전용 · 엔진 0줄)", "",
     "55회차 결과(`out/round55/UAD_DXF.json` · 449행 · 지문 `003078d7`)를 **그대로 열어**",
     "브라우저로 찍었습니다 — 재분석하지 않았고 렌더 함수를 직접 부르지 않았습니다.",
     f"그림 {len(PAGES) * 4}장 · 한 장 묶음 `{out}`.", "",
     "| 장 | 도면번호 | 등급 | 행 | 상자 | 범례 칸 합 | 그리드 행 | 태그 붙은 행 | 속성/블록글자/기하 | PDF 행 |",
     "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |"]
for s in stat:
    L.append(f"| {s['page']} | {s['dwg']} | {s['tier']} | {s['rows']} | {s['boxes']} | {s['legend']} |"
             f" {s['grid']} | {s['tagged']} | {s['attr']} / {s['btext']} / {s['geom']} | {s['pdf']} |")
tot = sum(s["rows"] for s in stat)
bad = sum(1 for s in stat if not (s["rows"] == s["boxes"] == s["legend"] == s["grid"]))
L += ["", f"다섯 장 합 **{tot}행**입니다.  같은 다섯 장을 PDF 로 읽으면 **{sum(s['pdf'] for s in stat)}행**"
      " 입니다 (45회차 저장 결과) — 그 다섯 장은 **글자가 전부 획(SHX)** 이라 PDF 경로가"
      " 타이틀블록조차 못 읽었고, 45회차에 사람이 도면번호를 적어 준 뒤에도 계기 행이 서지"
      " 않았습니다.  DXF 는 같은 글자를 속성으로 들고 있어 읽힙니다.",
      f"**33회차 등식** (범례 칸 합 = 상자 수 = 행 수 = 그리드 행 수) 어긋난 장: **{bad}**.", "",
      "## 그림 파일", "",
      "| 파일 | 무엇 |", "| --- | --- |"]
for k, c in zip(KINDS, CAPS):
    L.append(f"| `{k.format('<n>')}` | {c} |")
L += ["| `p<n>_4_pdf_overlay.png` | **찍지 못했습니다** — 이 작업 환경에 UAD **PDF 가 없습니다**"
      " (`data/` 에 `pid_total.pdf` · `TC2_260821.pdf` · `uad_dxf.zip` 뿐이고"
      " `spike/projects_3p.json` 이 가리키는 `data/UAD_binding.pdf` 도 없습니다)."
      " 아래 표의 `PDF 행` 열은 45회차에 저장된 결과(`out/round45/UAD_after.json` · 301행)에서 셌습니다. |",
      "",
      "확대 구역은 고르지 않고 **셌습니다** — 그 장 검출 상자의 중심으로 170pt 정사각 창을 훑어"
      " 가장 많이 든 자리를 집습니다 (`spike/dxf_shots_p11_p15.py` 의 `dense_window`)."
      " 확대율은 다섯 장 모두 맞춤 0.34 → 1.72 (5.1배)입니다.", "", "## 장별 내역", ""]
for s in stat:
    L.append(f"**p{s['page']}** · {s['dwg']} · 등급 {s['tier']} · {s['rows']}행")
    L.append("")
    L.append("- TYPE: " + ", ".join(f"{k} {v}" for k, v in s["types"].most_common()))
    L.append("- 판독 경로: 속성 {attr} · 블록 안 글자 {btext} · 기하 {geom}".format(**s))
    L.append("- 검토 사유: " + (", ".join(f"{k} {v}" for k, v in s["codes"].most_common()) or "없음"))
    uw = collections.Counter(x["why"] for x in s["unjudged"])
    ul = collections.Counter(x.get("label") or "" for x in s["unjudged"])
    L.append(f"- 미판정 심볼 {len(s['unjudged'])}건 — "
             + (", ".join(f"{k} {v}" for k, v in uw.items()) or "없음")
             + (" · " + ", ".join(f"`{k}` {v}" for k, v in ul.most_common(5)) if ul else ""))
    L.append("")

K20 = ["PIT", "TIT", "TI", "PI", "TG", "PG", "FE", "FIT", "SG", "LIT",
       "LS", "MOV", "XV", "PCV", "PV", "LV", "TV", "FV", "AIT", "TW"]
ty5 = collections.Counter(r.get("type") or "" for r in rows if 11 <= r["page_no"] <= 15)
L += ["## 요구 20종 — 이 다섯 장에서", "",
      "| 종류 | 행 | 종류 | 행 | 종류 | 행 | 종류 | 행 |", "| --- | ---: | --- | ---: | --- | ---: | --- | ---: |"]
for i in range(0, 20, 4):
    L.append("| " + " | ".join(f"{k} | {ty5.get(k, 0)}" for k in K20[i:i + 4]) + " |")
L += ["", "`TG`·`PG`·`SG`·`PV`·`LV`·`TV`·`FV` 는 51회차가 네 도면 전수로 **0건**임을 확인한 것들이고,"
      " 이 다섯 장에도 그 낱말이 인쇄돼 있지 않습니다.  `MOV`·`XV`·`PCV`·`AIT`·`TW` 도 이 다섯 장에는"
      " 없습니다 (UAD 다른 장에는 있습니다 — 55회차 20종 표).", "",
      "## 빠진 것 — 목록만 (이 자리에서 고치지 않습니다)", "",
      "| 무엇 | 장 · 건 | 왜 | 판단 |", "| --- | --- | --- | --- |",
      "| `RO` (제한 오리피스) | p11 1 · p14 4 | 속성 TYPE 이 `RO` 인데 **이 문서 ISA 표가 `R`·`O` 를 정의하지 않습니다** |"
      " 도면이 말하지 않는 것이라 지어내지 않았습니다 (51회차 `ZSO` 와 같은 자리).  PDF 경로는 이 문서에서 `RO` 3행을 냅니다 — 어느 쪽이 맞는지는 **실무 판단** |",
      "| `INST_LOCAL MOUNTED` 블록 4개 | p12 4 | TYPE 자리에 **태그 문자열**(`00EGD21CP501` …)이 들어 있어 ISA 로 안 풀립니다 —"
      " 그 블록에서 속성 역할이 갈리지 않았습니다 | 55회차 `attribute_roles` 의 한계.  **다음 회차 후보** |",
      "| `Ball Valve (Close)` 13 · `INTERLOCK-1` 8 | 다섯 장 | 범례 장에 없는 블록 | 밸브·인터록 심볼이고 범례가 뜻을 정하지 않았습니다 — 등록 화면 몫 |",
      "| `PIP BLIND FLANGE` 14 · `PIP FLANGED NOZZLE` 9 · `PIP FRONT FACING NOZZLE` 3 · `REDUCER01` · `STREAM NUM` 3 | 다섯 장 | 범례 장에 없는 블록 |"
      " 배관 부속·흐름 번호라 **행이 아닌 것이 맞습니다** |",
      "| 태그는 있는데 TYPE 이 빈 행 14 | p11 3 · p12 2 · p13 5 · p14 4 | 밸브 태그(`…AA191`)인데 몸체·액추에이터를 못 읽었습니다 |"
      " 53회차 [B-3] 그대로 — 탭을 지어내지 않고 검토로 올립니다 (`TAGGED_VALVE_NO_ACTUATOR`) |",
      "| 모든 행에 `MULTIPLIER_FROM_CONFIG` | 105/105 | 이 DXF 에 승수표도 유닛 노트도 없습니다 | 30회차 [13] 과 같습니다 — 31회차 사람 지정 자리가 답합니다 |",
      ""]
(D / "README.md").write_text("\n".join(L) + "\n", encoding="utf8")
print("→", out, len(sheets), "장 · 등식 어긋남", bad)
