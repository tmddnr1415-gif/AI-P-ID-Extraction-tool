"""어휘 조건이 실제로 거르는 문단은 몇 개인가 — 유닛 2개 이상인데 네 낱말이 없는 NOTES 문단."""
import json, re, sys, collections
from pathlib import Path
sys.path.insert(0, ".")
from app.engine import pidcache, projectconfig as pcfg
PROJ = {"AL NOUF1": ("data/pid_total.pdf", "AL_NOUF1", [1960.0, 35.0, 2384.0, 1250.0], 2330.0),
        "TC2": ("data/TC2_260821.pdf", "TC2", None, None),
        "UAD": ("data/UAD_binding.pdf", "UAD", None, None),
        "SADARA": ("app/_data/uploads/2391ee0f1ea6_sadara_1A46.pdf", "SADARA", None, None)}
head, rng = pcfg.note_vocabulary()   # 36회차부터 2-tuple (낱말 문지기 없음)
for name, (pdf, tag, area0, xmax0) in PROJ.items():
    res = json.load(open(f"out/regression_3p/{tag}.json"))["result"]
    lay = (res.get("applied_rules") or {}).get("layout") or {}
    moved = {m["key"]: m["now"] for m in (lay.get("moved") or []) if isinstance(m, dict)}
    area = area0 or moved["regions.notes_area"]; xmax = xmax0 or moved["regions.notes_text_x_max"]
    doc, pages = pidcache.load_pages(Path(pdf))
    tot = kept = risky = 0; ex = []
    for pc in pages:
        for para in pcfg._note_paragraphs(pc, area, xmax):
            up = re.sub(r"\s+", " ", para.upper()).strip()
            toks = list(dict.fromkeys(pcfg._unit_tokens(up, head)))
            if len(toks) < 2 or rng.search(up):
                continue
            tot += 1
            if True: kept += 1   # 36회차: 낱말 조건이 없어져 전부 kept
            else:
                risky += 1
                if len(ex) < 4: ex.append((pc.page_no, len(toks), up[:190]))
    doc.close()
    print(f"== {name}: 유닛 2개 이상인 NOTES 문단 {tot} · 낱말 있음 {kept} · **낱말 없음 {risky}**")
    for pg, n, t in ex: print(f"    p{pg} 유닛{n}개: {t}")
