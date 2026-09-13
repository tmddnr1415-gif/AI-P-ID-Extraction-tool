"""33회차 [D-1] — 한 프로세스에서 이어 분석할 때 **지금** RSS 가 돌아오는가.

32회차 순서 시험은 `ru_maxrss`(최고 수위)를 적었다.  그 값은 정의상 **내려올 수
없으므로** "메모리가 안 돌아온다" 는 결론을 그 숫자로는 낼 수 없다.  여기서는
단계마다 `/proc/self/status` 의 VmRSS(지금) · VmHWM(최고) 를 따로 읽고, 분석
결과를 놓고 `gc.collect()` 한 뒤의 값까지 적는다.  파이썬 쪽 보유는
`tracemalloc` 로 파일별 상위를 찍는다 (C 확장 — PyMuPDF·numpy — 의 할당은
tracemalloc 에 안 잡힌다.  그 몫은 VmRSS − tracemalloc 으로만 보인다).

    python3 spike/mem_probe.py AL_NOUF1 TC2 SADARA UAD [--trace]

★ 엔진을 고치지 않는다.  재는 도구다.
"""
from __future__ import annotations

import gc
import json
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PDFS = {p["name"].replace(" ", "_"): p["pdf"] for p in
        json.loads((ROOT / "spike" / "projects_3p.json").read_text())["projects"]}


def rss() -> dict:
    out = {}
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith(("VmRSS", "VmHWM")):
            k, v = line.split(":", 1)
            out[k] = round(int(v.split()[0]) / 1048576.0, 2)   # kB → GB
    return out


def top_files(snap, n=8) -> list:
    stats = snap.statistics("filename")
    return [{"file": s.traceback[0].filename.replace(str(ROOT) + "/", ""),
             "mb": round(s.size / 1048576.0, 1), "blocks": s.count}
            for s in stats[:n]]


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    trace = "--trace" in sys.argv
    names = args or ["AL_NOUF1", "TC2", "SADARA", "UAD"]
    from app import pipeline
    if trace:
        tracemalloc.start(1)
    log = [{"stage": "start", **rss()}]
    print(json.dumps(log[-1]), flush=True)
    for name in names:
        t0 = time.time()
        result = pipeline.analyse(str(ROOT / PDFS[name]))
        rec = {"stage": f"{name} 직후", "rows": len(result["rows"]),
               "fingerprint": pipeline.fingerprint(result)[:8],
               "seconds": round(time.time() - t0, 1), **rss()}
        if trace:
            rec["py_mb"] = round(tracemalloc.get_traced_memory()[0] / 1048576.0, 1)
            rec["top"] = top_files(tracemalloc.take_snapshot())
        log.append(rec); print(json.dumps(rec, ensure_ascii=False), flush=True)
        del result
        gc.collect()
        rec = {"stage": f"{name} 결과 놓고 gc", **rss()}
        if trace:
            rec["py_mb"] = round(tracemalloc.get_traced_memory()[0] / 1048576.0, 1)
            rec["top"] = top_files(tracemalloc.take_snapshot())
        log.append(rec); print(json.dumps(rec, ensure_ascii=False), flush=True)
    out = ROOT / "out" / "round33" / ("mem_%s%s.json" % ("-".join(names), "_trace" if trace else ""))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(log, ensure_ascii=False, indent=1))
    print("→", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
