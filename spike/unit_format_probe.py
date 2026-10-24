"""36회차 [D-1 4] — 그 도면이 자기 유닛코드를 NOTES 에서 어떤 꼴로 적는가.

장마다 도면번호의 유닛 자리(2자리)를 읽고, 그 장의 번호 붙은 NOTES 문단에서 **같은 숫자**가
어떤 꼴(`DD` · `D-D` · `#DD` · `NO.DD` · `UNIT DD` …)로 인쇄되는지 센다.  꼴이 문서에서
읽히면 "유닛 표기 꼴" 은 코드에 나열할 것이 아니라 도면이 말해 주는 것이다.
그리고 그 꼴로 문단의 표기를 세면 유닛이 아닌 것이 잡히는지(오검) 전수로 낸다.
"""
import json, re, sys, collections
from pathlib import Path
sys.path.insert(0, ".")
from app.engine import pidcache, projectconfig as pcfg
PROJ = {"AL NOUF1": ("data/pid_total.pdf", "AL_NOUF1", [1960.0, 35.0, 2384.0, 1250.0], 2330.0),
        "SADARA": ("app/_data/uploads/2391ee0f1ea6_sadara_1A46.pdf", "SADARA", None, None),
        "TC2": ("data/TC2_260821.pdf", "TC2", None, None),
        "UAD": ("data/UAD_binding.pdf", "UAD", None, None)}
FORMS = {"D-D": lambda c: rf"(?<![\w-]){c[0]}\s*-\s*{c[1]}(?![\w-])",
         "#DD": lambda c: rf"#\s*{c}(?!\d)",
         "NO.DD": lambda c: rf"NO\.?\s*{c}(?!\d)",
         "WORD DD": lambda c: rf"(?:UNIT|GROUP|TRAIN)S?\s*{c}(?!\d)",
         "bare DD": lambda c: rf"(?<![\w#.-]){c}(?![\w-])"}
out = {}
for name, (pdf, tag, area0, xmax0) in PROJ.items():
    res = json.load(open(f"out/regression_3p/{tag}.json"))["result"]
    lay = (res.get("applied_rules") or {}).get("layout") or {}
    moved = {m["key"]: m["now"] for m in (lay.get("moved") or []) if isinstance(m, dict)}
    area = area0 or moved["regions.notes_area"]; xmax = xmax0 or moved["regions.notes_text_x_max"]
    code_of = {}
    for r in res["rows"]:
        dn = r.get("drawing_no") or ""
        if "-" in dn: code_of[r["page_no"]] = dn.split("-")[1][:2]
    doc, pages = pidcache.load_pages(Path(pdf))
    seen = collections.Counter(); ex = {}
    # 오검 후보: 학습된 꼴로 문단 안 모든 2자리 표기를 주웠을 때, 유닛 문단이 아닌 곳에서 잡히는 것
    for pc in pages:
        c = code_of.get(pc.page_no)
        if not c: continue
        paras = [re.sub(r"\s+", " ", p.upper()).strip() for p in pcfg._note_paragraphs(pc, area, xmax)]
        paras = [p for p in paras if pcfg._NUMBERED.match(p)]
        for f, mk in FORMS.items():
            pat = re.compile(mk(c))
            for p in paras:
                if pat.search(p):
                    seen[(c, f)] += 1
                    ex.setdefault((c, f), f"p{pc.page_no}: {p[:120]}")
                    break
    doc.close()
    out[name] = {"codes": sorted(set(code_of.values())), "own_code_in_notes": [{"code": k[0], "form": k[1], "sheets": v, "example": ex[k]} for k, v in seen.most_common()]}
    print(f"== {name}: 도면번호 유닛코드 {sorted(set(code_of.values()))} · 행 있는 장 {len(code_of)}")
    for k, v in seen.most_common():
        print(f"   코드 {k[0]} 를 NOTES 가 `{k[1]}` 꼴로 적은 장 {v:3d}   {ex[k][:100]}")
json.dump(out, open("out/round36/unit_format_probe.json", "w"), ensure_ascii=False, indent=1)
