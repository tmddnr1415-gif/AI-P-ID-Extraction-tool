"""hotfix48 — 액추에이터 사정거리 규칙(절대 pt ↔ 울타리 크기 비율)을 **밸브 단계만** 돌려 비교한다.

    python3 spike/act_reach_probe.py <pdf> <out.json> [page_no ...]

장마다 `find_bodies` 한 번 · `attach_actuators` 를 규칙별로(abs · ratio) 돌려 붙은 액추에이터
(kind · 몸체 사각형)를 적는다.  분석 경로를 부르지 않으므로 지문·DB 에 닿지 않는다.
장을 주면 그 장만(범례 장은 유도를 위해 언제나 연다).
"""
from __future__ import annotations
import copy, dataclasses, json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.engine import detect_valves as dv, detect_symbols as ds, pidcache, legend_rules as lr

pdf, out = sys.argv[1], Path(sys.argv[2])
want = [int(a) for a in sys.argv[3:]]
t0 = time.time()
doc, pages = pidcache.load_pages(pdf)
vlay, _ = dv.derive_layout(pages)
print(f"layout: act_reach {vlay.act_reach} ratio {vlay.act_reach_ratio} ({getattr(vlay, 'act_reach_source', '')}) "
      f"act_box {vlay.act_box} unit {vlay.unit} · {time.time() - t0:.1f}s", flush=True)
legend_pages = {lr._page_with(pages, h).page_no for h in (lr.ACTUATOR_HEADING,) if lr._page_with(pages, h)}
res = {"layout": {"act_reach": vlay.act_reach, "act_reach_ratio": vlay.act_reach_ratio,
                  "act_reach_source": getattr(vlay, "act_reach_source", ""), "act_box": list(vlay.act_box)},
       "pages": {}}
for pc in pages:
    if want and pc.page_no not in want:
        continue
    if pc.page_no in legend_pages:
        continue
    t1 = time.time()
    bodies = dv.find_bodies(pc, vlay)
    per = {}
    for mode in ("abs", "ratio"):
        lay = dataclasses.replace(vlay, act_reach_ratio=0.0) if mode == "abs" else vlay
        bs = copy.deepcopy(bodies)
        dv.attach_actuators(pc, bs, lay)
        per[mode] = [(b.kind, b.actuator, [round(v, 1) for v in (b.rect.x0, b.rect.y0, b.rect.x1, b.rect.y1)])
                     for b in bs if b.actuator != "NONE"]
    diff = [x for x in per["ratio"] if x not in per["abs"]] + [("-",) + tuple(x) for x in per["abs"] if x not in per["ratio"]]
    res["pages"][pc.page_no] = {"bodies": len(bodies), "abs": per["abs"], "ratio": per["ratio"], "diff": diff}
    print(f"p{pc.page_no}: bodies {len(bodies)} · abs {len(per['abs'])} · ratio {len(per['ratio'])} · diff {len(diff)} · {time.time() - t1:.1f}s", flush=True)
    if diff and len(diff) <= 6:
        for d in diff: print("   ", d, flush=True)
tot_abs = sum(len(v["abs"]) for v in res["pages"].values()); tot_ratio = sum(len(v["ratio"]) for v in res["pages"].values())
tot_diff = sum(len(v["diff"]) for v in res["pages"].values())
res["totals"] = {"abs": tot_abs, "ratio": tot_ratio, "diff": tot_diff, "seconds": round(time.time() - t0, 1)}
out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print("TOTAL abs", tot_abs, "ratio", tot_ratio, "diff", tot_diff, f"{time.time() - t0:.0f}s")
