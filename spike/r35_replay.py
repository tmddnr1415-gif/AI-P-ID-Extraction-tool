"""35회차 [D] — 지운 상태로 돌리고, 멈추면 그 상수 **하나만** 되살려 다시 돈다.

    python3 spike/r35_replay.py --pdf /tmp/r35_probe.pdf --tag probe [--max 20] [--no-strip]

상태는 `out/round35/replay_<tag>.json` 에 쌓인다 (되살린 순서 · 회차별 결과).
자식 프로세스는 worktree(/tmp/r35_strip)에서 돌고 PID_DATA_DIR 은 임시다.
★ 엔진을 고치지 않는다.  되살리기는 환경변수 `R35_RESTORED` 하나다.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WT = Path("/tmp/r35_strip")
KEYS = ROOT / "out/round35/strip_keys.json"

CHILD = r'''
import json, sys, traceback, time
t0 = time.time()
def find_missing(tb):
    seen = []
    while tb:
        for v in list(tb.tb_frame.f_locals.values()):
            for cand in ([v] + (list(v.values()) if isinstance(v, dict) else list(v) if isinstance(v, (list, tuple)) else [])):
                if type(cand).__name__ == "Missing":
                    seen.append(cand.name)
        tb = tb.tb_next
    return seen
try:
    from app import pipeline
    result = pipeline.analyse(sys.argv[1])
    fp = pipeline.fingerprint(result)
    rows = result["rows"]
    print("R35" + json.dumps({"ok": True, "rows": len(rows), "fingerprint": fp[:8], "fp_full": fp,
        "qty": sum(int(r.get("qty") or 0) for r in rows), "seconds": round(time.time() - t0, 1),
        "derived": len(((result.get("applied_rules") or {}).get("layout") or {}).get("items") or []),
        "moved": len(((result.get("applied_rules") or {}).get("layout") or {}).get("moved") or []),
        "legend_sources": {k: (v or {}).get("source") for k, v in (result.get("legend") or {}).items() if isinstance(v, dict)},
        "rows_dump": [(r["key"], r["tab"], r["type"], r["qty"], r["valve_type"], r["vendor_supply"], r["scope"], r["needs_review"], list(r["rect"])) for r in rows]}))
except BaseException as exc:
    tb = sys.exc_info()[2]
    names = find_missing(tb)
    msg = str(exc) if type(exc).__name__ == "MissingConstant" else ""
    if msg: names = [msg.split(" (")[0]] + names
    tail = traceback.format_exc().splitlines()[-6:]
    print("R35" + json.dumps({"ok": False, "error_type": type(exc).__name__, "error": str(exc)[:300],
        "missing": names[0] if names else None, "missing_all": sorted(set(names)), "trace_tail": tail,
        "seconds": round(time.time() - t0, 1)}))
'''

def run_once(pdf: str, restored: list, strip: bool) -> dict:
    env = dict(os.environ, PYTHONPATH=str(WT), PID_DATA_DIR=tempfile.mkdtemp(prefix="r35-"),
               R35_RESTORED=",".join(restored))
    if strip:
        env["R35_STRIP_KEYS"] = str(KEYS); env["R35_STRIP_AT_LOAD"] = "project.code"
    else:
        env.pop("R35_STRIP_KEYS", None); env["R35_NO_STRIP"] = "1"
    p = subprocess.run([sys.executable, "-c", CHILD, pdf], cwd=str(WT), env=env,
                       capture_output=True, text=True, timeout=3600)
    line = [l for l in p.stdout.splitlines() if l.startswith("R35")]
    if not line:
        return {"ok": False, "error_type": "NoOutput", "error": (p.stderr or "")[-600:], "missing": None}
    return json.loads(line[-1][3:])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True); ap.add_argument("--tag", required=True)
    ap.add_argument("--max", type=int, default=20); ap.add_argument("--no-strip", action="store_true")
    ap.add_argument("--restored", default="", help="쉼표로 이은 시작 복원 목록 (2단계용)")
    a = ap.parse_args()
    state_p = ROOT / "out/round35" / f"replay_{a.tag}.json"
    state = json.loads(state_p.read_text()) if state_p.exists() else {"restored": [], "runs": []}
    if a.restored and not state["restored"]:
        state["restored"] = [s for s in a.restored.split(",") if s]
    t_all = time.time()
    base_n = len(state["restored"])   # 이번 실행에서 되살린 수만 상한에 센다 (2단계 사전 복원분 제외)
    while True:
        n = len(state["runs"])
        r = run_once(a.pdf, state["restored"], not a.no_strip)
        dump = r.pop("rows_dump", None)
        rec = {"iter": n, "restored_before": list(state["restored"]), **r}
        state["runs"].append(rec)
        if dump is not None:
            (ROOT / "out/round35" / f"rows_{a.tag}_{n}.json").write_text(json.dumps(dump))
        print(json.dumps({k: v for k, v in rec.items() if k not in ("trace_tail", "legend_sources")}, ensure_ascii=False), flush=True)
        state_p.write_text(json.dumps(state, ensure_ascii=False, indent=1))
        if r.get("ok") or a.no_strip:
            break
        if not r.get("missing"):
            print("★ 이름 없는 실패 — 변환기 통과가 더 필요하거나 (c) 갈래다.  멈춘다.", flush=True)
            print("\n".join(r.get("trace_tail") or []), flush=True); break
        if r["missing"] in state["restored"]:
            print("★ 같은 상수에서 다시 멈췄다 — 복원이 안 먹는다.  멈춘다.", flush=True); break
        if len(state["restored"]) - base_n >= a.max:
            print(f"★ 되살린 횟수 {a.max} 도달 — 멈춘다.", flush=True); break
        if time.time() - t_all > 4 * 3600:
            print("★ 4시간 초과 — 멈춘다.", flush=True); break
        state["restored"].append(r["missing"])
    state_p.write_text(json.dumps(state, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
