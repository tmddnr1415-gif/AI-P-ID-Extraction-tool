"""32회차 [D] — 합성 도면 여덟을 **한 번에 하나씩** 돌리고 사실만 적는다.

    python3 spike/run_synthetic.py [파일...]

각 도면마다 묻는 것 (프롬프트 D-2):
  · 완주하는가 · 몇 행 · 몇 초 · 최대 RSS
  · 멈추면 **사유를 말하는가** — 조용히 0행으로 "성공" 하지 않는가
  · 읽은 파라미터가 몇 개인가 (축3 ⑥ 의 재료)
  · **남의 도면 값으로 폴백한 자리**가 몇 개 · 무엇인가

프로세스를 나누는 이유는 회귀 하네스와 같다 — 메모리를 돌려받고 최대 RSS 를
따로 재기 위해서다.  **엔진을 고치지 않는다.**
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SYN = ROOT / "tests" / "data" / "synthetic"
OUT = ROOT / "out" / "round32" / "synthetic"

CHILD = r'''
import json, resource, sys, time, traceback
from pathlib import Path
sys.path.insert(0, %r)
pdf, out = sys.argv[1], sys.argv[2]
rec = {"pdf": Path(pdf).name}
t0 = time.time()
try:
    from app import pipeline
    timings = {}
    result = pipeline.analyse(pdf, timings=timings)
    result["fingerprint"] = pipeline.fingerprint(result)
    rec["status"] = "done"
    rec["rows"] = len(result["rows"])
    rec["qty"] = sum(int(r.get("qty") or 0) for r in result["rows"])
    rec["fingerprint"] = result["fingerprint"][:8]
    rec["pages_with_rows"] = len({r["page_no"] for r in result["rows"]})
    rec["tier"] = (result.get("evidence_tier") or {}).get("tier")
    rec["tagged_rows"] = (result.get("evidence_tier") or {}).get("tagged_rows")
    lay = (result.get("applied_rules") or {}).get("layout") or {}
    rec["derived_items"] = len(lay.get("items") or [])
    src = {}
    for key, d in ((result.get("applied_rules") or {}).get("legend") or {}).items():
        s = d.get("source") if isinstance(d, dict) else None
        if s:
            src.setdefault(s, []).append(key)
    rec["legend_sources"] = {k: sorted(v) for k, v in src.items()}
    rec["timings"] = {k: round(v, 1) for k, v in sorted(
        timings.items(), key=lambda kv: -kv[1])[:4]}
    Path(out).write_text(json.dumps({"result": result}, default=str))
except BaseException as exc:
    rec["status"] = "stopped"
    rec["error_type"] = type(exc).__name__
    rec["error"] = str(exc)[:400]
    rec["trace_tail"] = traceback.format_exc().strip().splitlines()[-3:]
rec["seconds"] = round(time.time() - t0, 1)
rec["max_rss_gb"] = round(
    resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1048576.0, 2)
print("@@" + json.dumps(rec, ensure_ascii=False))
''' % (str(ROOT),)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    files = [Path(a) for a in sys.argv[1:]] or sorted(SYN.glob("*.pdf"))
    recs = []
    for f in files:
        print(f"· {f.name} …", flush=True)
        p = subprocess.run([sys.executable, "-c", CHILD, str(f),
                            str(OUT / (f.stem + ".json"))],
                           capture_output=True, text=True, timeout=3600)
        line = [l for l in p.stdout.splitlines() if l.startswith("@@")]
        rec = json.loads(line[-1][2:]) if line else {
            "pdf": f.name, "status": "no-output",
            "stderr_tail": p.stderr.strip().splitlines()[-3:]}
        recs.append(rec)
        print("   " + json.dumps({k: v for k, v in rec.items()
                                  if k not in ("legend_sources", "timings")},
                                 ensure_ascii=False), flush=True)
    (ROOT / "out" / "round32" / "synthetic_runs.json").write_text(
        json.dumps(recs, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
