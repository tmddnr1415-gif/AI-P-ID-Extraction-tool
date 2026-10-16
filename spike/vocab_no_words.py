"""어휘 없이 — NOTES 문단이 유닛 표기를 2개 이상 열거하면 그것을 배수로 본다.

낱말 목록을 아예 안 쓰는 길이 있는가를 재는 것이지, 엔진을 고치는 것이 아니다.
`note_unit_span` 에서 **같음 낱말 조건만** 빼고 나머지는 그대로 쓴다.
"""
import json, re, sys, collections
from pathlib import Path
sys.path.insert(0, ".")
from app.engine import pidcache, projectconfig as pcfg

def span_nowords(pc, area, xmax):
    head, rng = pcfg.note_vocabulary()   # 36회차부터 2-tuple
    best = None
    for para in pcfg._note_paragraphs(pc, area, xmax):
        up = re.sub(r"\s+", " ", para.upper()).strip()
        toks = list(dict.fromkeys(pcfg._unit_tokens(up, head)))
        if len(toks) < 2 or rng.search(up):
            continue
        if best is None or len(toks) > len(best[1]):
            best = (len(toks), toks, up)
    return best

PROJ = {"AL NOUF1": ("data/pid_total.pdf", "AL_NOUF1", [1960.0, 35.0, 2384.0, 1250.0], 2330.0),
        "TC2": ("data/TC2_260821.pdf", "TC2", None, None),
        "UAD": ("data/UAD_binding.pdf", "UAD", None, None),
        "SADARA": ("app/_data/uploads/2391ee0f1ea6_sadara_1A46.pdf", "SADARA", None, None)}
out = {}
for name, (pdf, tag, area0, xmax0) in PROJ.items():
    res = json.load(open(f"out/regression_3p/{tag}.json"))["result"]
    lay = (res.get("applied_rules") or {}).get("layout") or {}
    moved = {m["key"]: m["now"] for m in (lay.get("moved") or []) if isinstance(m, dict)}
    area = area0 or moved["regions.notes_area"]; xmax = xmax0 or moved["regions.notes_text_x_max"]
    rows = res["rows"]; per_page = collections.Counter(r["page_no"] for r in rows)
    table = (res["multipliers"] or {}).get("table") or {}
    legend = (res["multipliers"] or {}).get("source") == "LEGEND"
    code = {r["page_no"]: ((r.get("drawing_no") or "").split("-")[1][:2]
                           if "-" in (r.get("drawing_no") or "") else None) for r in rows}
    doc, pages = pidcache.load_pages(Path(pdf))
    diff, qty = [], 0
    for pc in pages:
        if pc.page_no not in per_page: continue
        now = pcfg.note_unit_span(pc, area, xmax)
        alt = span_nowords(pc, area, xmax)
        a = alt[0] if alt else None
        if (now.count or None) != a:
            diff.append({"page": pc.page_no, "now": now.count, "no_words": a,
                         "text": (alt[2] if alt else now.text)[:200], "rows": per_page[pc.page_no]})
        f = table.get(code.get(pc.page_no)) if legend else (a if a else table.get(code.get(pc.page_no)))
        qty += (f or 0) * per_page[pc.page_no]
    doc.close()
    out[name] = {"qty_no_words": qty, "changed_pages": diff}
    print(f"== {name}: 어휘 없이 Q'ty {qty} · 달라진 장 {len(diff)}")
    for x in diff[:8]:
        print(f"   p{x['page']} 행{x['rows']:3d}  현행 {x['now']} → 어휘없이 {x['no_words']}   {x['text'][:120]}")
json.dump(out, open("out/round36_no_words.json", "w"), ensure_ascii=False, indent=1)
