"""TC2 의 밸브·액추에이터가 왜 0행인가 — 값을 절반으로 두면 달라지는가.

저장소 코드는 고치지 않는다.  `actuator_stem` 유도 결과만 A3 축척(1/2)으로
갈아 끼우고 같은 코드로 다시 재서, 붙는 액추에이터 수를 비교한다.
"""
import sys, os, json, collections, copy
sys.path.insert(0, os.getcwd())
from app import pipeline
from app.engine import pidcache, detect_valves as dv

lay_items = json.load(open("out/tc2/head.json"))["applied_rules"]["layout"]["items"]
pipeline.CFG.overlay({it["key"]: it["value"] for it in lay_items if it["source"] == "DERIVED"})
pipeline._rebind_config()
doc, pages = pidcache.load_pages("data/TC2_260821.pdf")
sub = pages[5:20]                      # p6~p20 · 15장

def run(scale, tag):
    lay, derived = dv.derive_layout(pages)
    st = derived["actuator_stem"]
    if scale != 1.0:
        vals = {k: (round(v * scale, 3) if isinstance(v, (int, float)) else v)
                for k, v in st.values.items()}
        st = type(st)(values=vals, source=st.source, note=st.note)
        derived = dict(derived); derived["actuator_stem"] = st
        lay, _ = dv.derive_layout(pages, derived=derived)
    dv.LAYOUT = lay
    res, glyphs = dv.analyse_all(sub, frozenset(), derive=True)
    bodies = acts = 0
    kinds = collections.Counter()
    for r in res.values():
        for b in r["bodies"]:
            bodies += 1
            a = getattr(b, "actuator", None)
            if a and str(a) != "NONE":
                acts += 1
                kinds[str(a)] += 1
    print("%-22s stem=%s" % (tag, st.values))
    print("   몸체 %4d · 액추에이터 붙은 몸체 %3d · 종류 %s · 글리프 letters=%s"
          % (bodies, acts, dict(kinds), glyphs.letters))

run(1.0, "현행(A1 폴백 값)")
run(0.5, "값을 절반으로")
