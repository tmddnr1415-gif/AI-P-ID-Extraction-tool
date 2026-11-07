"""L56 — 작도 기호 크기 · 배치를 분석한 묶음들에서 배운다 → config/logic_draw_style.json

  PID_DATA_DIR=<데이터 폴더> python3 spike/draw_style_learn.py <job …> [--out config/logic_draw_style.json]

값은 행 간격(P) 배율의 중앙값이라 양식 · 종이 · 축척을 넘는다 (§9).  기호 모양은 바꾸지 않는다 — 크기와 세로 열만.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.logic import draw_sets, store  # noqa: E402

if __name__ == "__main__":
    argv = sys.argv[1:]
    out = ROOT / "config" / "logic_draw_style.json"
    if "--out" in argv:
        out = Path(argv[argv.index("--out") + 1])
        del argv[argv.index("--out"):argv.index("--out") + 2]
    results, sources = [], []
    for job in argv:
        d = store.root() / job
        res = json.loads((d / "result.json").read_text(encoding="utf-8"))
        results.append(res)
        sources.append({"job": job, "name": store.read_status(d).get("name", ""), "sheets": len(res.get("sheets") or [])})
    style = draw_sets.learn_style(results, sources)
    out.write_text(json.dumps(style, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in style.items() if k != "sources"}, ensure_ascii=False, indent=1))
