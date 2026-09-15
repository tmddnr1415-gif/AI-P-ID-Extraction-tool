"""36회차 [D-1] — 네 프로젝트 NOTES 의 "유닛 표기처럼 보이는 것" 전수.

    python3 spike/unit_token_survey.py

읽기 전용.  번호 붙은 NOTES 문단 안의 숫자 꼴을 전부 내고(원문 인용), 앞에 GROUP/UNIT/TRAIN 이
있는가 없는가로 가르고, "숫자인데 유닛이 아닌 것"(SET : 00 barg · DN200 · NOTE 3 …)을 센다.
그리고 그 도면이 유닛 표기의 꼴을 스스로 말하는지 본다 — 범례 승수표의 유닛코드 · 도면번호의 유닛 자리.
"""
import json, re, sys, collections
from pathlib import Path
sys.path.insert(0, ".")
from app.engine import pidcache, projectconfig as pcfg

PROJ = {"AL NOUF1": ("data/pid_total.pdf", "AL_NOUF1", [1960.0, 35.0, 2384.0, 1250.0], 2330.0),
        "SADARA": ("app/_data/uploads/2391ee0f1ea6_sadara_1A46.pdf", "SADARA", None, None),
        "TC2": ("data/TC2_260821.pdf", "TC2", None, None),
        "UAD": ("data/UAD_binding.pdf", "UAD", None, None)}
# 숫자 꼴 후보 — 가르기 위한 것이지 판정 규칙이 아니다
NUM = re.compile(r"(?<![A-Z0-9])(#\s*\d{1,2}|NO\.?\s*\d{1,2}(?:\s*-\s*\d{1,2})?|\d{1,2}\s*-\s*\d{1,2}|\d{1,2})(?![A-Z0-9-])")
HEAD = re.compile(r"(?:GROUP|UNIT|TRAIN)S?\s*(?:NO\.?|#)?\s*$")
out = {}
for name, (pdf, tag, area0, xmax0) in PROJ.items():
    res = json.load(open(f"out/regression_3p/{tag}.json"))["result"]
    lay = (res.get("applied_rules") or {}).get("layout") or {}
    moved = {m["key"]: m["now"] for m in (lay.get("moved") or []) if isinstance(m, dict)}
    area = area0 or moved["regions.notes_area"]; xmax = xmax0 or moved["regions.notes_text_x_max"]
    mult = res.get("multipliers") or {}
    codes = collections.Counter()
    for r in res["rows"]:
        dn = r.get("drawing_no") or ""
        if "-" in dn: codes[dn.split("-")[1][:2]] += 1
    doc, pages = pidcache.load_pages(Path(pdf))
    forms = collections.Counter(); headed = collections.Counter(); ex = collections.defaultdict(list)
    nonunit = collections.Counter(); nonunit_ex = collections.defaultdict(list)
    n_paras = 0
    for pc in pages:
        for para in pcfg._note_paragraphs(pc, area, xmax):
            up = re.sub(r"\s+", " ", para.upper()).strip()
            if not pcfg._NUMBERED.match(up):
                continue
            n_paras += 1
            for m in NUM.finditer(up):
                tok = m.group(1)
                shape = re.sub(r"\d", "D", re.sub(r"\s+", "", tok))
                before = up[max(0, m.start() - 12):m.start()]
                has_head = bool(HEAD.search(before))
                after = up[m.end():m.end() + 14]
                ctx = up[max(0, m.start() - 45):m.end() + 30]
                # 유닛 문단(유닛 머리 낱말이 어디든 있는 문단) 안인가
                unit_para = bool(re.search(r"(?<!\w)(?:GROUP|UNIT|TRAIN)S?(?!\w)", up))
                key = (shape, has_head, unit_para)
                forms[key] += 1
                if len(ex[key]) < 3: ex[key].append(f"p{pc.page_no}: …{ctx}…")
                if not unit_para:
                    what = re.sub(r"\d+", "N", (before[-8:] + "|" + tok + "|" + after[:8]).strip())
                    nonunit[what] += 1
                    if len(nonunit_ex[what]) < 2: nonunit_ex[what].append(f"p{pc.page_no}: …{ctx}…")
    doc.close()
    out[name] = {"numbered_paras": n_paras, "mult_source": mult.get("source"), "mult_table": mult.get("table"),
                 "drawing_unit_codes": dict(codes),
                 "forms": [{"shape": k[0], "head_word_before": k[1], "in_unit_paragraph": k[2], "n": v, "examples": ex[k]}
                           for k, v in sorted(forms.items(), key=lambda t: -t[1])],
                 "non_unit_numbers": [{"pattern": k, "n": v, "examples": nonunit_ex[k]} for k, v in nonunit.most_common(25)]}
    print(f"== {name}: 번호 문단 {n_paras} · 승수표 {mult.get('source')} {mult.get('table')} · 도면번호 유닛코드 {dict(codes)}")
    for f in out[name]["forms"][:8]:
        print(f"   {f['shape']:8s} 머리낱말 {str(f['head_word_before']):5s} 유닛문단 {str(f['in_unit_paragraph']):5s} x{f['n']:4d}  {f['examples'][0][:110]}")
    print(f"   유닛 문단 밖 숫자: {sum(x['n'] for x in out[name]['non_unit_numbers'])}종류합 · 상위 {[ (x['pattern'], x['n']) for x in out[name]['non_unit_numbers'][:6]]}")
json.dump(out, open("out/round36/unit_token_survey.json", "w"), ensure_ascii=False, indent=1)
