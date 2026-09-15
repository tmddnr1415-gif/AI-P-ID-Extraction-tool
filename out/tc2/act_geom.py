"""TC2 의 액추에이터가 실제로 어떻게 그려져 있나 — 도면에서 잰다.

밸브 몸체 위에 있는 작은 원(액추에이터 후보)을 찾아 원 지름 · 원 아래 간격 ·
원 중심에서 몸체까지 거리를 센다.  AL NOUF1 값(폴백)과 나란히 놓는다.
"""
import sys, os, json, collections, statistics
sys.path.insert(0, os.getcwd())
from app import pipeline
from app.engine import pidcache, detect_valves as dv

lay_items = json.load(open("out/tc2/head.json"))["applied_rules"]["layout"]["items"]
pipeline.CFG.overlay({it["key"]: it["value"] for it in lay_items if it["source"] == "DERIVED"})
pipeline._rebind_config()
doc, pages = pidcache.load_pages("data/TC2_260821.pdf")
lay, derived = dv.derive_layout(pages)
dv.LAYOUT = lay
sub = pages[5:20]
res, _g = dv.analyse_all(sub, frozenset(), derive=True)

dia, gap, c2b = [], [], []
pairs = 0
for pc in sub:
    r = res.get(pc.page_no)
    if not r:
        continue
    circles = []
    for d in pc.drawings():
        b = d["bbox"]; items = d["items"]
        if not items or not all(i[0] == "c" for i in items):
            continue
        if max(b.width, b.height) <= 0:
            continue
        if min(b.width, b.height) / max(b.width, b.height) < 0.85:
            continue
        if not (5.0 <= min(b.width, b.height) <= 20.0):
            continue
        circles.append(b)
    for body in r["bodies"]:
        bx = body.rect
        cxb = (bx[0] + bx[2]) / 2
        for c in circles:
            cx = (c.x0 + c.x1) / 2
            if abs(cx - cxb) > 3.0:
                continue
            d_gap = bx[1] - c.y1                     # 원 아래에서 몸체 위까지
            if not (0.0 <= d_gap <= 25.0):
                continue
            pairs += 1
            dia.append(round(min(c.width, c.height), 2))
            gap.append(round(d_gap, 2))
            c2b.append(round((bx[1] + bx[3]) / 2 - (c.y0 + c.y1) / 2, 2))
            break

def s(v):
    return "n=%d 중앙 %.2f 최소 %.2f 최대 %.2f" % (len(v), statistics.median(v), min(v), max(v)) if v else "n=0"

print("p6~p20 · 몸체 %d개 중 위에 원이 있는 것 %d개" % (sum(len(r["bodies"]) for r in res.values()), pairs))
print("  원 지름       :", s(dia))
print("  원-몸체 간격  :", s(gap))
print("  원중심→몸체중심:", s(c2b))
print()
print("현행 규칙이 요구하는 값 (AL NOUF1 폴백):")
print("  stem_gap 0.0 (스템이 원에 닿아야) · stem_length 19.86 · centre_to_body 26.97 · stem_offaxis 0.03")
