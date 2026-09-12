"""승수 어휘 실측 — 네 프로젝트의 NOTES 가 어느 낱말을 인쇄하는가.

읽기 전용.  파이프라인을 돌리지 않고 `pc.words` 만 읽어 `note_unit_span` 을 그대로 부른다.
NOTES 영역은 그 회귀 실행이 **실제로 적용한** 값(`applied_rules.layout`)을 쓴다.
"""
import json, re, sys, collections
from pathlib import Path
sys.path.insert(0, ".")
from app.engine import pidcache, projectconfig

WORDS = ["IDENTICAL", "SIMILAR", "SAME", "TYPICAL"]
# 그 밖의 후보 — 도면이 "같다" 를 다르게 부르는지 본다 (세지 않고 찾기만)
OTHER = ["COMMON", "DUPLICAT", "APPLICABLE", "REPRESENTATIVE", "EQUAL", "ALIKE", "REPEAT", "MIRROR"]
PROJ = {"AL NOUF1": ("data/pid_total.pdf", "AL_NOUF1"),
        "SADARA": ("app/_data/uploads/2391ee0f1ea6_sadara_1A46.pdf", "SADARA"),
        "TC2": ("data/TC2_260821.pdf", "TC2"),
        "UAD": ("data/UAD_binding.pdf", "UAD")}
ALNOUF_AREA = json.loads(sys.argv[1]) if len(sys.argv) > 1 else None
out = {}
for name, (pdf, tag) in PROJ.items():
    res = json.load(open(f"out/regression_3p/{tag}.json"))["result"]
    lay = (res.get("applied_rules") or {}).get("layout") or {}
    moved = {m["key"]: m["now"] for m in (lay.get("moved") or []) if isinstance(m, dict)}
    items = {it["key"]: it.get("value") for it in (lay.get("items") or []) if isinstance(it, dict)}
    area = moved.get("regions.notes_area") or ALNOUF_AREA or items.get("regions.notes_area")
    xmax = moved.get("regions.notes_text_x_max") or (ALNOUF_AREA and ALNOUF_AREA[2]) or items.get("regions.notes_text_x_max")
    doc, pages = pidcache.load_pages(Path(pdf))
    rec = {"pdf": pdf, "area": area, "x_max": xmax, "pages": len(pages),
           "sheet": collections.Counter(), "notes": collections.Counter(),
           "other_sheet": collections.Counter(), "spans": {}, "paras": {}}
    for pc in pages:
        txt = " ".join(t for _r, t in pc.words).upper()
        for w in WORDS:
            n = len(re.findall(r"(?<!\w)%s(?!\w)" % w, txt))
            if n: rec["sheet"][w] += n
        for w in OTHER:
            n = len(re.findall(r"(?<!\w)%s" % w, txt))
            if n: rec["other_sheet"][w] += n
        paras = projectconfig._note_paragraphs(pc, area, xmax)
        keep = [re.sub(r"\s+", " ", p.upper()).strip() for p in paras]
        keep = [p for p in keep if any(re.search(r"(?<!\w)%s(?!\w)" % w, p) for w in WORDS + OTHER)]
        if keep: rec["paras"][pc.page_no] = keep
        for p in keep:
            for w in WORDS:
                if re.search(r"(?<!\w)%s(?!\w)" % w, p): rec["notes"][w] += 1
        span = projectconfig.note_unit_span(pc, area, xmax)
        if span.count or span.ambiguous or span.units:
            rec["spans"][pc.page_no] = {"count": span.count, "units": span.units,
                                        "ambiguous": span.ambiguous, "text": span.text}
    doc.close()
    rec["sheet"] = dict(rec["sheet"]); rec["notes"] = dict(rec["notes"]); rec["other_sheet"] = dict(rec["other_sheet"])
    out[name] = rec
    print(name, "쪽", rec["pages"], "| 시트 전체", rec["sheet"], "| NOTES 문단", rec["notes"],
          "| span", len(rec["spans"]), flush=True)
json.dump(out, open("out/round36_vocab_census.json", "w"), ensure_ascii=False, indent=1)
