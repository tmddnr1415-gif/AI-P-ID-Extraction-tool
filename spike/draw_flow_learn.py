"""L92 — '다음 기호' 차례를 들고 있는 로직도(작도 씨앗 묶음)에서 배운다 → config/logic_draw_flow.json

  python3 spike/draw_flow_learn.py [config/logic_draw_seed/<씨앗>.json.gz …] [--out config/logic_draw_flow.json]

씨앗 = 분석한 로직도를 그대로 들여온 그림들 (19VA 827장).  기호의 출력이 어느 기호의 입력으로 갔는지 · 같은 행에서 곧게 이은 간격(행 간격 배율) ·
타이머 시간 값을 센다.  작성 화면은 프로젝트(묶음)의 그림에서 같은 것을 런타임에 다시 재고, 그림이 적을 때만 이 바탕을 쓴다.
"""
from __future__ import annotations

import gzip
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.logic import draw_sets, draw_sim  # noqa: E402

if __name__ == "__main__":
    argv = sys.argv[1:]
    out = ROOT / "config" / "logic_draw_flow.json"
    if "--out" in argv:
        out = Path(argv[argv.index("--out") + 1])
        del argv[argv.index("--out"):argv.index("--out") + 2]
    seeds = [Path(a) for a in argv] or sorted((ROOT / "config" / "logic_draw_seed").glob("*.json.gz"))
    docs, sources = [], []
    for fp in seeds:
        d = json.load(gzip.open(fp))
        docs += d["docs"]
        sources.append({"seed": fp.name, "set": d.get("name") or "", "sheets": len(d["docs"]), "rev": d.get("rev")})
    t = time.time()
    sheets = [draw_sim.to_sheet(doc, i + 1) for i, doc in enumerate(docs)]
    res = draw_sets.learn_flow(docs, sheets)
    res = {"_about": "LOGIC 작도 '다음 기호' 차례 (L92) — 들고 있는 로직도(작도 씨앗)에서 센 것. spike/draw_flow_learn.py 가 다시 만든다.",
           "source": sources, "at": time.strftime("%Y-%m-%d %H:%M:%S"), **res}
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(docs)}장 · 이어짐 {res['pairs']}건 · 열쇠 {len(res['next'])} · 간격(가운데) {res['gap_all_p']}P · {time.time() - t:.0f}s → {out}")
    for k in ("k:AND", "k:OR", "k:NOT", "k:GT", "k:MEMORY", "p:H/", "k:PB"):
        print(" ", k, res["next"].get(k, [])[:6], res["gap_p"].get(k))
