"""L48 — 묶음의 모든 누름단추 · 신호원을 하나씩 눌러 본다 (sim.press · 읽기만).

단추마다: 바로 동작 (reached) · 조건을 더 켜면 동작 (plan) · 범례대로 멈춤 (stop · 조건이 안 맞음) · 끊긴 연결(dead_end) ·
표적 없음 (그 단추에서 닿는 출력이 없다) · 예외.

  PID_DATA_DIR=… python3 spike/logic_press_sweep.py <job> [--max N] [--out 파일.json]
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.logic import api, sim  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("--max", type=int, default=0)
    ap.add_argument("--out")
    a = ap.parse_args()
    res = api._result(a.job)
    sheets = api._all_sheets(res)
    cache = {}
    t0 = time.time()
    c = collections.Counter()
    found = collections.defaultdict(list)
    todo = []
    for s in res["sheets"]:
        ins = sim._index(s)[0]
        for bid, b in s["blocks"].items():
            if b.get("logic") == "source" and not ins.get(bid) and b.get("func") in ("PUSH BUTTON", "SIGNAL", "BUTTON"):
                todo.append((s, bid))
    if a.max:
        todo = todo[:a.max]
    for i, (s, bid) in enumerate(todo):
        try:
            r = sim.press(sheets, s["page"], bid, cache=cache)
        except Exception as ex:
            c["error"] += 1
            found["error"].append({"sheet": s["sheet_no"], "block": bid, "error": repr(ex), "trace": traceback.format_exc()[-500:]})
            continue
        lab = (s["blocks"][bid].get("label") or "")[:30]
        if r["ok"]:
            c["reached"] += 1
            found["reached"].append({"sheet": s["sheet_no"], "block": bid, "label": lab, "n": len(r["reached"])})
        elif r.get("plan") and r["plan"].get("ok"):
            c["plan"] += 1
            found["plan"].append({"sheet": s["sheet_no"], "block": bid, "label": lab})
        elif not r.get("targets"):
            c["no_target"] += 1
            found["no_target"].append({"sheet": s["sheet_no"], "block": bid, "label": lab})
        elif r.get("stop") and r["stop"].get("dead_end"):
            c["dead_end"] += 1
            found["dead_end"].append({"sheet": s["sheet_no"], "block": bid, "label": lab, "stop": r["stop"]})
        else:
            c["stop"] += 1
            st = r.get("stop") or {}
            found["stop"].append({"sheet": s["sheet_no"], "block": bid, "label": lab, "at": st.get("block"),
                                  "logic": st.get("logic"), "func": st.get("func"), "macro": (st.get("macro") or {}).get("sheet")})
        if (i + 1) % 100 == 0:
            print(f"… {i + 1}/{len(todo)} · {round(time.time() - t0)}초", flush=True)
    out = {"job": a.job, "seconds": round(time.time() - t0, 1), "buttons": len(todo), "counts": dict(c),
           "found": {k: v[:80] for k, v in found.items()}, "found_all": dict(found)}
    print(json.dumps({k: out[k] for k in ("seconds", "buttons", "counts")}, ensure_ascii=False))
    if a.out:
        Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
