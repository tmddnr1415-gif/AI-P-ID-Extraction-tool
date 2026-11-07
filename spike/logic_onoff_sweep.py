"""L33 — 묶음의 모든 입력을 하나씩 켜고 꺼 보며 시뮬레이터가 논리대로 도는지 본다 (읽기만 · 분석 폴더에 쓰지 않는다).

장마다: 아무것도 안 줌 · 입력 행 하나씩 1 · 모두 1 · 모두 1 에서 하나씩 0.  틀마다 확인하는 것:
  ① 게이트 원칙 (L18) — 입력을 다 읽은 AND · OR · NAND · NOR · NOT · 투표의 출력이 그 틀의 입력으로 범례가 내는 값과 같은가
  ② 안정 — '값이 안정되지 않았습니다' (되먹임이 흔들림)
  ③ 모순 — 같은 장비의 반대 명령(OPEN ↔ CLOSE · START ↔ STOP)이 같은 마지막 틀에 둘 다 1
  ④ 예외 — 시뮬레이션이 죽지 않는가

  PID_DATA_DIR=… python3 spike/logic_onoff_sweep.py <job> [--max-sheets N] [--out 파일.json]
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

from app.logic import api, sequence, sim  # noqa: E402

OPPOSITE = {("OPEN", "CLOSE"), ("START", "STOP")}


def gate_faults(s, frames):
    ins, outs, drivers, _, _ = sim._index(s)
    bad = []
    for bid, b in s["blocks"].items():
        lg = b.get("logic")
        vote = sim._vote_of(b)
        if lg not in sim.MIN_INPUTS and not vote:
            continue
        iv_nets = [n for n, _, _ in ins[bid]]
        if len(iv_nets) < (vote[1] if vote else sim.MIN_INPUTS[lg]):
            continue
        for on, role, _ in outs[bid]:
            if len(drivers.get(on, [])) != 1:
                continue
            for fr in frames:
                unread = set(fr.get("unread") or ())        # 화면에는 0 으로 보이지만 '모름' 인 선 (L10)
                if on in unread or any(n in unread for n in iv_nets):
                    continue
                iv = [fr["values"].get(n) for n in iv_nets]
                if any(v is None for v in iv) or fr["values"].get(on) is None:
                    continue
                want = sim._vote3(iv, *vote) if vote else sim.gate3(lg, iv)
                if want is not None and fr["values"][on] != want:
                    bad.append({"block": bid, "logic": lg or "vote", "t": fr["t"], "in": iv, "out": fr["values"][on]})
                    break
    return bad


def opposites(s, values):
    by = collections.defaultdict(dict)
    for r in s["rows"]:
        if r["side"] != "R" or r.get("net") is None:
            continue
        c = sequence.classify(r.get("desc"))
        if c and c[1] == "command" and values.get(r["net"]) == 1:
            by[c[2]][c[0]] = r["n"]
    return [(eq, a, b) for eq, acts in by.items() for a, b in OPPOSITE if a in acts and b in acts]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("--max-sheets", type=int, default=0)
    ap.add_argument("--out")
    a = ap.parse_args()
    res = api._result(a.job)
    sheets = api._all_sheets(res)
    cache = {}
    t0 = time.time()
    stats = collections.Counter()
    found = {"gate": [], "unstable": [], "opposite": [], "error": []}
    todo = [s for s in res["sheets"] if s.get("rows")]
    if a.max_sheets:
        todo = todo[:a.max_sheets]
    for s in todo:
        ins = [r["n"] for r in s["rows"] if r["side"] == "L" and r.get("net") is not None]
        cases = [{}] + [{f"row:{n}": 1} for n in ins]
        if ins:
            allon = {f"row:{n}": 1 for n in ins}
            cases += [allon] + [{**allon, f"row:{n}": 0} for n in ins]
        for f in cases:
            stats["runs"] += 1
            try:
                r = sim.simulate_bundle(sheets, {s["page"]: f} if f else {}, None, s["page"], cache=cache)["focus"]
            except Exception as ex:
                found["error"].append({"sheet": s.get("sheet_no"), "forces": f, "error": repr(ex),
                                       "trace": traceback.format_exc()[-600:]})
                continue
            g = gate_faults(s, r["frames"])
            if g:
                found["gate"].append({"sheet": s.get("sheet_no"), "forces": f, "faults": g[:3]})
            if any("안정되지" in n for n in r.get("notes") or []):
                found["unstable"].append({"sheet": s.get("sheet_no"), "forces": f})
            op = opposites(s, r["frames"][-1]["values"])
            if op:
                found["opposite"].append({"sheet": s.get("sheet_no"), "forces": f, "pairs": op})
        stats["sheets"] += 1
    out = {"job": a.job, "seconds": round(time.time() - t0, 1), "stats": dict(stats),
           "counts": {k: len(v) for k, v in found.items()}, "found": {k: v[:40] for k, v in found.items()}}
    print(json.dumps({k: out[k] for k in ("seconds", "stats", "counts")}, ensure_ascii=False))
    if a.out:
        Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
