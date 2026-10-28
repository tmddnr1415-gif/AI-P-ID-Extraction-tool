"""32회차 [C-3 ⑨] — **한 프로세스에서** 네 프로젝트를 순서를 바꿔 돌린다.

회귀 하네스(`regression_3p.py`)는 프로젝트마다 **자식 프로세스**라 전역 누출을
잡을 수 없다 — 그것이 21·22회차가 현장에서만 드러난 이유다.  이 도구는 한
프로세스 안에서 이어 돌리고 **행 수 · 지문 · 최대 RSS** 를 적는다.

    python3 spike/order_leak.py AL_NOUF1 SADARA TC2 UAD
    python3 spike/order_leak.py UAD TC2 SADARA AL_NOUF1

★ 엔진을 고치지 않는다.  값이 순서에 달리면 그것이 발견이다.
"""
from __future__ import annotations

import json
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PDFS = {p["name"].replace(" ", "_"): p["pdf"] for p in
        json.loads((ROOT / "spike" / "projects_3p.json").read_text())["projects"]}


def main() -> int:
    names = sys.argv[1:] or ["SADARA", "AL_NOUF1"]
    from app import pipeline
    out = []
    for name in names:
        t0 = time.time()
        result = pipeline.analyse(str(ROOT / PDFS[name]))
        fp = pipeline.fingerprint(result)
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1048576.0
        rec = {"name": name, "rows": len(result["rows"]),
               "fingerprint": fp[:8],
               "qty": sum(int(r.get("qty") or 0) for r in result["rows"]),
               "seconds": round(time.time() - t0, 1),
               "max_rss_gb_so_far": round(rss, 2)}
        out.append(rec)
        print(json.dumps(rec, ensure_ascii=False), flush=True)
    Path(ROOT / "out" / "round32" / ("order_%s.json" % "-".join(names))).write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
