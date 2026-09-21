"""55회차 표 셋 — [B] 32장 인벤토리 · [C] 범례 블록 사전 · [D] 20종 표 (PDF 와 나란히).

    python3 spike/dxf_report_tables.py out/round55/UAD_DXF.json out/round45/UAD_after.json out/round55
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path

dxf = json.loads(Path(sys.argv[1]).read_text()); dxf = dxf.get("result", dxf)
pdf = json.loads(Path(sys.argv[2]).read_text()); pdf = pdf.get("result", pdf)
OUT = Path(sys.argv[3]); OUT.mkdir(parents=True, exist_ok=True)
rows = dxf["rows"]
tb = {t["page_no"]: t for t in dxf["titleblocks"]}
tiers = dxf["dxf"]["tiers"]

# ── [B] 인벤토리 ──────────────────────────────────────────────────────
L = ["# [B] DXF 32장 판독 · 인벤토리 · 등급 (55회차)", "",
     f"순서 규칙: **{dxf['dxf']['order_rule']}** · 건너뛴 입력 {dxf['dxf']['skipped_inputs'] or '없음'} · "
     f"도면번호 형식(두 장 이상 인쇄된 모양): `{dxf['dxf']['drawing_no_pattern']}`", "",
     "등급은 **블록 단위로 세어 장 단위로 이름 붙인 것**이다 — 1급(TYPE·태그 속성) · 2급(범례 계기 블록 + 안의 글자) · "
     "기하(범례 계기 원 크기의 닫힌 도형 + 안의 글자).  `PDF임포트` 는 `PDF_*` 층에 놓인 엔티티 비율이다 "
     "(AutoCAD PDFIMPORT 의 흔적 — EXPLODE 가 아니라 **PDF 를 다시 들여온 장**).", "",
     "| 장 | 파일 | 버전 | 감사오류 | INSERT | 속성INSERT | CIRCLE | LWPOLY | ATTDEF | 끈 층 | PDF임포트 | 도면번호 | REV | 종류 | 등급 | 1급/2급/기하 | 행 |",
     "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- | ---: |"]
for inv in dxf["dxf"]["sheets"]:
    n = inv["no"]; t = tb.get(n, {}); ti = tiers.get(str(n), {})
    if inv.get("error"):
        L.append(f"| {n} | {inv['file'][:38]} | — | — | | | | | | | | | | ★ 실패 | | | |  {inv['error'][:40]}")
        continue
    e = inv["entities"]
    L.append(f"| {n} | {inv['file'][:38]} | {inv['version']} | {inv['audit_errors']} | {inv['insert']} | {inv['insert_with_attribs']} | "
             f"{e.get('CIRCLE',0)} | {e.get('LWPOLYLINE',0)} | {e.get('ATTDEF',0)} | {len(inv['hidden_layers'])} | {inv['pdf_import_share']:.0%} | "
             f"{t.get('drawing_no','')} | {t.get('rev','')} | {t.get('page_kind','')} | {ti.get('tier','—')} | "
             f"{ti.get('attr','')}/{ti.get('block','')}/{ti.get('geometry','')} | {sum(1 for r in rows if r['page_no']==n)} |")
vers = collections.Counter(i.get("version") for i in dxf["dxf"]["sheets"] if not i.get("error"))
L += ["", f"버전: {dict(vers)} · 읽기 실패 0 · 등급 분포: {dict(collections.Counter(v['tier'] for v in tiers.values()))}", "",
      "## 속성 역할 (값이 정했다)", "",
      f"- TYPE 역할: `{'`, `'.join(dxf['dxf']['attribute_roles']['type'])}`",
      f"- 태그 역할: `{'`, `'.join(dxf['dxf']['attribute_roles']['tag'])}`", "",
      "| 속성 이름 | n | ISA 풀림 | 태그 모양 | 최빈 모양 | 장 수 | 태그 짝 |", "| --- | ---: | ---: | ---: | --- | ---: | --- |"]
for t, f in sorted(dxf["dxf"]["attribute_roles"]["facts"].items(), key=lambda kv: -kv[1]["n"])[:18]:
    L.append(f"| `{t[:48]}` | {f['n']} | {f.get('isa_share',0):.0%} | {f['tag_share']:.0%} | `{f['top_shape']}` | {f['shape_sheets']} | {'✔' if f.get('paired_with_tag') else ''} |")
L += ["", "## 끈 층 (레이어 표의 off · frozen · plot=0 — 이름으로 거르지 않았다)", ""]
hid = collections.Counter(l for i in dxf["dxf"]["sheets"] for l in i.get("hidden_layers", []))
L.append(", ".join(f"`{l}`({n}장)" for l, n in hid.most_common()))
(OUT / "round55_dxf_inventory.md").write_text("\n".join(L) + "\n", encoding="utf8")

# ── [C] 범례 블록 사전 ────────────────────────────────────────────────
B = dxf["dxf"]["blocks"]
L = ["# [C] 범례 블록 사전 — 범례 장(002~005)에서 읽었다 · 코드에 이름 0 (55회차)", "",
     "종류는 **구획 머리말**(그 장에서 가장 큰 글자)과 **옆 캡션**(심볼 중심을 품는 줄의 오른쪽 글자)이 정한다.  "
     "TYPE·태그 역할 속성을 선언한 블록은 구획과 무관하게 계기다.  이름은 열쇠일 뿐이다.", "",
     f"블록 {len(B)} — " + " · ".join(f"{k} {v}" for k, v in collections.Counter(b['kind'] for b in B.values()).most_common()), "",
     "| 블록 이름 | 종류 | 몸체/액추에이터 | 구획 | 캡션 | 속성(ATTDEF) |", "| --- | --- | --- | --- | --- | --- |"]
for name, b in sorted(B.items(), key=lambda kv: (kv[1]["kind"], kv[0])):
    if b["kind"] == "other" and not b["captions"]:
        continue
    secs = ", ".join(f"{s or '(없음)'}×{n}" for s, n in sorted(b["sections"].items(), key=lambda kv: -kv[1])[:3])
    L.append(f"| `{name[:34]}` | {b['kind']} | {b['body'] or b['actuator']} | {secs[:60]} | {' / '.join(b['captions'][:2])[:60]} | {len(b['attdefs'])} |")
L += ["", "## 둘째 체계 — 범례에 없는 블록인데 범례 계기 원과 같은 반지름을 그린 것", "",
      "p16~p18 이 쓰는 `AS_INST` 체계의 계기 블록은 범례 장에 **없다**.  블록 정의가 범례 계기 원과 같은 반지름(±25%)의 "
      "원/호를 그리면 2급으로 세되, 행에 사유 `DXF_BLOCK_NOT_IN_LEGEND` 를 단다 (이름이 아니라 기하로 갈랐다).", "",
      "- " + ", ".join(f"`{n}`" for n in dxf["dxf"].get("blocks_outside_legend_round", [])), "",
      "## ISA 문자표", "",
      f"`{dxf['legend']['isa_table']['source']}` — {dxf['legend']['isa_table']['note']}", ""]
(OUT / "round55_legend_blocks.md").write_text("\n".join(L) + "\n", encoding="utf8")

# ── [D] 20종 표 ───────────────────────────────────────────────────────
KINDS = ["PIT", "TIT", "TI", "PI", "TG", "PG", "FE", "FIT", "SG", "LIT", "LS", "MOV", "XV", "PCV", "PV", "LV", "TV", "FV", "AIT", "TW"]
ALIAS = {"PV": "PCV", "LV": "LCV", "TV": "TCV", "FV": "FCV"}
def count(rs, k):
    kk = ALIAS.get(k, k)
    return sum(1 for r in rs if (r.get("type") == kk) or (r.get("evidence", {}).get("tag") == kk))
def printed(res, k):
    kk = ALIAS.get(k, k)
    n = 0
    for u in res.get("unjudged_symbols") or []:
        if (u.get("label") or "") == kk: n += 1
    for v in res.get("valve_tags") or []:
        if v.get("tag") == kk: n += 1
    return n
L = ["# [D] 요구 20종 — DXF ↔ PDF 나란히 (UAD · 55회차)", "",
     "행 = 그 TYPE(또는 밸브 태그)로 나간 행.  미판정 = 그 낱말을 찾았는데 행이 안 된 것 (`unjudged_symbols` + `valve_tags`).  "
     "`PV·LV·TV·FV` 는 `PCV·LCV·TCV·FCV` 와 같은 것으로 센다 (51회차 결정).  PDF 열은 45회차 저장 결과(301행 · 사람 지정 도면번호 포함).", "",
     "| 종류 | DXF 행 | DXF 미판정 | PDF 행 | PDF 미판정 |", "| --- | ---: | ---: | ---: | ---: |"]
for k in KINDS:
    L.append(f"| {k} | {count(rows,k)} | {printed(dxf,k)} | {count(pdf['rows'],k)} | {printed(pdf,k)} |")
L += ["", "TYPE 전체 (DXF): " + ", ".join(f"{t or '(밸브 태그 행)'} {n}" for t, n in collections.Counter(r["type"] for r in rows).most_common(30)), "",
      "TYPE 전체 (PDF): " + ", ".join(f"{t or '(밸브 태그 행)'} {n}" for t, n in collections.Counter(r["type"] for r in pdf["rows"]).most_common(30)), ""]
(OUT / "round55_census20.md").write_text("\n".join(L) + "\n", encoding="utf8")
print("→ 세 표를 썼다:", OUT)
