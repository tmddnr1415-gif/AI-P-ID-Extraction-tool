"""그 도면이 SIMILAR·IDENTICAL 의 뜻을 정의하는가 — 범례·NOTES·본문 전수 검색."""
import json, re, sys, collections
from pathlib import Path
sys.path.insert(0, ".")
from app.engine import pidcache
W = re.compile(r"(?<!\w)(IDENTICAL|SIMILAR|SAME|TYPICAL)(?!\w)")
PROJ = {"TC2": "data/TC2_260821.pdf", "AL NOUF1": "data/pid_total.pdf",
        "UAD": "data/UAD_binding.pdf", "SADARA": "app/_data/uploads/2391ee0f1ea6_sadara_1A46.pdf"}
res = {}
for name, pdf in PROJ.items():
    doc, pages = pidcache.load_pages(Path(pdf))
    hits = []
    for pc in pages:
        rows = collections.defaultdict(list)
        for r, t in pc.words:
            rows[round(r.y0, 1)].append((r.x0, t))
        for y in sorted(rows):
            line = " ".join(t for _x, t in sorted(rows[y])).upper()
            for m in W.finditer(line):
                s = max(0, m.start() - 70)
                hits.append((pc.page_no, m.group(1), line[s:m.end() + 90].strip()))
    doc.close()
    res[name] = hits
    print(f"== {name}: 낱말이 든 줄 {len(hits)}")
    by = collections.defaultdict(collections.Counter)
    for pg, w, ctx in hits:
        by[w][re.sub(r"\d", "#", ctx)] += 1
    for w in ("SIMILAR", "IDENTICAL", "SAME", "TYPICAL"):
        if not by[w]: continue
        print(f"  -- {w}: 서로 다른 문맥 {len(by[w])}")
        for ctx, n in by[w].most_common(4):
            print(f"     x{n:3d}  {ctx[:150]}")
json.dump({k: v for k, v in res.items()}, open("out/round36_defn.json", "w"), ensure_ascii=False, indent=1)
