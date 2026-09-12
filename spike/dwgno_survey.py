"""37회차 [B-1] — 도면번호 칸에 인쇄된 낱말의 모양 전수 (네 프로젝트).

도면번호 칸(`title_block.dwg_no_region` — 그 실행이 적용한 값)에 든 낱말을 장마다 읽고
모양(글자 L · 숫자 D · 기호 그대로)으로 접는다.  `formats.drawing_no` 를 그 도면에서
유도할 수 있는지 보는 실측이고, 엔진을 고치지 않는다.
"""
import json, re, sys, collections
from pathlib import Path
sys.path.insert(0, ".")
from app.engine import pidcache
PROJ = {"AL NOUF1": ("data/pid_total.pdf", "AL_NOUF1"), "SADARA": ("app/_data/uploads/2391ee0f1ea6_sadara_1A46.pdf", "SADARA"),
        "TC2": ("data/TC2_260821.pdf", "TC2"), "UAD": ("data/UAD_binding.pdf", "UAD")}
def shape(t): return "".join("L" if c.isalpha() else "D" if c.isdigit() else c for c in t)
def seg_shape(t): return "-".join(("%s%d" % ("L" if s.isalpha() else "D" if s.isdigit() else "A", len(s))) for s in t.split("-"))
out = {}
for name, (pdf, tag) in PROJ.items():
    res = json.load(open(f"out/regression_3p/{tag}.json"))["result"]
    lay = (res.get("applied_rules") or {}).get("layout") or {}
    moved = {m["key"]: m["now"] for m in (lay.get("moved") or []) if isinstance(m, dict)}
    import yaml
    cfg = yaml.safe_load(open("config/project_alnouf1.yaml"))
    region = moved.get("title_block.dwg_no_region") or cfg["title_block"]["dwg_no_region"]
    pat = re.compile(cfg["formats"]["drawing_no"])
    tbs = {t["page_no"]: t for t in res.get("titleblocks") or []}
    doc, pages = pidcache.load_pages(Path(pdf))
    x0, y0, x1, y1 = region
    shapes = collections.Counter(); ex = {}; per_page = []
    for pc in pages:
        ws = [t for r, t in pc.words if x0 <= (r.x0 + getattr(r, "x1", r.x0)) / 2 <= x1 and y0 <= r.y0 <= y1]
        cand = [t for t in ws if "-" in t and any(c.isdigit() for c in t)]
        read = tbs.get(pc.page_no, {}).get("drawing_no")
        for t in cand:
            k = seg_shape(t); shapes[k] += 1; ex.setdefault(k, (pc.page_no, t))
        per_page.append({"page": pc.page_no, "words": ws[:8], "candidates": cand, "engine_read": read,
                         "matches_config": bool(read and pat.match(read))})
    doc.close()
    out[name] = {"region": region, "shapes": dict(shapes), "examples": {k: v for k, v in ex.items()}, "pages": per_page}
    unread = [p["page"] for p in per_page if not p["engine_read"]]
    print(f"== {name}: 칸 {region} · 엔진이 읽은 장 {sum(1 for p in per_page if p['engine_read'])}/{len(per_page)} · 못 읽은 장 {unread}")
    for k, v in shapes.most_common(): print(f"   {k:28s} x{v:3d}   p{ex[k][0]}: {ex[k][1]}")
    for p in per_page:
        if not p["engine_read"] and p["candidates"]: print(f"   ★ p{p['page']} 칸 안 후보: {p['candidates']}")
json.dump(out, open("out/round37_dwgno_survey.json", "w"), ensure_ascii=False, indent=1)
