"""DXF ↔ PDF 대조 — 목록만 낸다, 고치지 않는다 (55회차 [G]).

    python3 spike/dxf_vs_pdf.py out/round55/UAD_DXF.json out/round45/UAD_after.json out/round55_dxf_vs_pdf.md

짝은 **태그**로 짓는다 (UAD 는 실행 도면이라 태그가 있다).  태그가 없는 행은
(장, TYPE) 개수로만 대조한다.
  ㉠ 둘 다 있다 · ㉡ DXF 만 있다 (PDF 미검출 후보) · ㉢ PDF 만 있다 (PDF 오검출 후보 —
  DXF 쪽이 놓친 것일 수도 있다 · 렌더로 확인할 목록)
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path

dxf = json.loads(Path(sys.argv[1]).read_text()); dxf = dxf.get("result", dxf)
pdf = json.loads(Path(sys.argv[2]).read_text()); pdf = pdf.get("result", pdf)
out = Path(sys.argv[3]) if len(sys.argv) > 3 else None


def tagged(rows):
    m = {}
    for r in rows:
        t = (r.get("tag_no") or "").strip()
        if t:
            m.setdefault(t, []).append(r)
    return m


dt, pt = tagged(dxf["rows"]), tagged(pdf["rows"])
both = sorted(set(dt) & set(pt)); only_d = sorted(set(dt) - set(pt)); only_p = sorted(set(pt) - set(dt))
lines = ["# DXF ↔ PDF 대조 (UAD · 태그로 짝) — 목록만, 고치지 않는다", "",
         f"DXF 행 {len(dxf['rows'])} (태그 있는 행 {sum(len(v) for v in dt.values())} · 서로 다른 태그 {len(dt)})",
         f"PDF 행 {len(pdf['rows'])} (태그 있는 행 {sum(len(v) for v in pt.values())} · 서로 다른 태그 {len(pt)}) — `{sys.argv[2]}`", "",
         f"| | 태그 수 |", "| --- | ---: |",
         f"| ㉠ 둘 다 | **{len(both)}** |", f"| ㉡ DXF 만 (PDF 미검출 후보) | **{len(only_d)}** |",
         f"| ㉢ PDF 만 (PDF 오검출 후보 · DXF 가 놓쳤을 수도) | **{len(only_p)}** |", ""]
# TYPE 이 다른 ㉠
diff_type = [(t, dt[t][0]["type"], pt[t][0]["type"]) for t in both if dt[t][0]["type"] != pt[t][0]["type"]]
lines += [f"㉠ 중 TYPE 이 다른 짝 {len(diff_type)}: " + ", ".join(f"`{t}` DXF {a} ↔ PDF {b}" for t, a, b in diff_type[:30]), ""]
def by_page(m):
    c = collections.Counter()
    for t, rows in m.items():
        c[rows[0]["page_no"]] += 1
    return c
lines += ["## ㉡ DXF 만 — 장별 (PDF 판정을 고칠 목록)", ""]
c = by_page({t: dt[t] for t in only_d})
for pg in sorted(c):
    tags = [t for t in only_d if dt[t][0]["page_no"] == pg]
    lines.append(f"- p{pg}: {c[pg]}건 — " + ", ".join(f"{dt[t][0]['type']} `{t}`" for t in tags[:12]) + (" …" if len(tags) > 12 else ""))
lines += ["", "## ㉢ PDF 만 — 장별 (렌더로 확인할 목록)", ""]
c = by_page({t: pt[t] for t in only_p})
for pg in sorted(c):
    tags = [t for t in only_p if pt[t][0]["page_no"] == pg]
    lines.append(f"- p{pg}: {c[pg]}건 — " + ", ".join(f"{pt[t][0]['type']} `{t}`" for t in tags[:12]) + (" …" if len(tags) > 12 else ""))
# 장별 행 수 표
lines += ["", "## 장별 행 수 (태그 유무와 무관)", "", "| 장 | 도면번호 | DXF 등급 | DXF 행 | PDF 행 | 차이 |", "| ---: | --- | --- | ---: | ---: | ---: |"]
dp = collections.Counter(r["page_no"] for r in dxf["rows"]); pp = collections.Counter(r["page_no"] for r in pdf["rows"])
for p in dxf["pages"]:
    n = p["page_no"]; tier = (dxf.get("dxf", {}).get("tiers", {}).get(str(n)) or {}).get("tier", "-")
    lines.append(f"| {n} | {p['drawing_no']} | {tier} | {dp.get(n,0)} | {pp.get(n,0)} | {dp.get(n,0)-pp.get(n,0):+d} |")
lines.append(f"| 합 | | | {len(dxf['rows'])} | {len(pdf['rows'])} | {len(dxf['rows'])-len(pdf['rows']):+d} |")
text = "\n".join(lines) + "\n"
if out:
    out.write_text(text, encoding="utf8")
print(text[:3000])
