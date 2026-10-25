"""L48 — 묶음의 모든 신호를 켜고 끄며 모든 게이트 · 매크로를 돌려 본다 (읽기만 · 분석 폴더에 쓰지 않는다).

L33 의 켜고 끄기(입력 행)에 더해 **누름단추 · 신호원 블록**도 켜고, 매크로는 단자 연결과 출력까지 센다.
장마다: 아무것도 안 줌 · 입력 행 하나씩 1 · 누름단추 하나씩 1 · 모두 1 · 모두 1 에서 하나씩 0.  틀마다 확인:
  ① 게이트 원칙 (L18) — 입력을 다 읽은 게이트의 출력이 범례 값과 같은가
  ② 안정 · ③ 반대 명령 동시 1 · ④ 예외
  ⑤ 어느 경우에도 1 이 되지 않는 게이트 (몰이가 끊겼거나 입력을 못 읽은 자리 — 읽기 빈틈 후보)
  ⑥ 매크로 — Typical 을 못 찾은 상자 · 못 이은 단자 · 모두 1 에서 출력 단자가 1 이 되는가 · 안쪽 입력 덜 읽은 게이트

  PID_DATA_DIR=… python3 spike/logic_full_sim.py <job> [--max-sheets N] [--out 파일.json]
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
                unread = set(fr.get("unread") or ())
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
    found = {"gate": [], "unstable": [], "opposite": [], "error": [], "never_on": [], "short": [],
             "macro_unlinked": [], "macro_pins": [], "macro_dead_out": [], "unknown": []}
    todo = [s for s in res["sheets"] if s.get("rows")]
    if a.max_sheets:
        todo = todo[:a.max_sheets]
    for s in todo:
        ins, outs, drivers, _, _ = sim._index(s)
        rows_in = [r["n"] for r in s["rows"] if r["side"] == "L" and r.get("net") is not None]
        srcs = [bid for bid, b in s["blocks"].items() if b.get("logic") == "source" and not ins.get(bid)]
        keys = [f"row:{n}" for n in rows_in] + [f"block:{b}" for b in srcs]
        cases = [{}] + [{k: 1} for k in keys]
        if keys:
            allon = {k: 1 for k in keys}
            cases += [allon] + [{**allon, k: 0} for k in keys]
        seen = collections.defaultdict(set)          # 게이트 출력 선 → 본 값들
        short_all = set()
        allon_vals = None
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
            last = r["frames"][-1]["values"]
            op = opposites(s, last)
            if op:
                found["opposite"].append({"sheet": s.get("sheet_no"), "forces": f, "pairs": op})
            short_all.update(r.get("short_gates") or [])
            for fr in r["frames"]:
                unread = set(fr.get("unread") or ())
                for bid in s["blocks"]:
                    for on, _, _ in outs.get(bid, []):
                        v = fr["values"].get(on)
                        if v is not None and on not in unread:
                            seen[bid].add(v)
            if f and all(v == 1 for v in f.values()) and len(f) == len(keys):
                allon_vals = last
        # ⑤ 어느 경우에도 1 이 안 된 게이트
        for bid, b in s["blocks"].items():
            lg = b.get("logic")
            if lg in ("source", "connector", "unknown", "macro", "light", "status", None) or not outs.get(bid):
                continue
            if bid in short_all:
                continue
            vals = seen.get(bid, set())
            if vals and 1 not in vals:
                found["never_on"].append({"sheet": s.get("sheet_no"), "block": bid, "logic": lg,
                                          "n_in": len(ins.get(bid, []))})
        if short_all:
            found["short"].append({"sheet": s.get("sheet_no"), "blocks": sorted(short_all)[:20], "n": len(short_all)})
            stats["short_gates"] += len(short_all)
        # ⑥ 매크로
        for bid, b in s["blocks"].items():
            if b.get("func") != "MACRO":
                continue
            stats["macros"] += 1
            m = b.get("macro") or {}
            if not m.get("page"):
                found["macro_unlinked"].append({"sheet": s.get("sheet_no"), "block": bid, "why": m.get("why", "")})
                continue
            stats["macros_linked"] += 1
            unl = [p["pin"] for p in (m.get("inputs") or []) + (m.get("outputs") or []) if p.get("row") is None]
            n_pins = len(m.get("inputs") or []) + len(m.get("outputs") or [])
            stats["macro_pins"] += n_pins
            stats["macro_pins_unlinked"] += len(unl)
            if unl:
                found["macro_pins"].append({"sheet": s.get("sheet_no"), "block": bid, "typical": m.get("sheet"),
                                            "unlinked": unl[:12], "n": len(unl), "of": n_pins})
            if allon_vals is not None:
                outs_m = [(p["pin"], allon_vals.get(p["net"])) for p in (m.get("outputs") or []) if p.get("row") is not None]
                if outs_m and all(v != 1 for _, v in outs_m):
                    found["macro_dead_out"].append({"sheet": s.get("sheet_no"), "block": bid, "typical": m.get("sheet"),
                                                    "outputs": outs_m[:10]})
        unk = [bid for bid, b in s["blocks"].items() if b.get("func") == "UNKNOWN"]
        if unk:
            found["unknown"].append({"sheet": s.get("sheet_no"), "blocks": unk[:10], "n": len(unk)})
            stats["unknown_blocks"] += len(unk)
        stats["sheets"] += 1
        if stats["sheets"] % 50 == 0:
            print(f"… {stats['sheets']}/{len(todo)} 장 · {round(time.time() - t0)}초", flush=True)
    out = {"job": a.job, "seconds": round(time.time() - t0, 1), "stats": dict(stats),
           "counts": {k: len(v) for k, v in found.items()}, "found": {k: v[:60] for k, v in found.items()},
           "found_all": found}
    print(json.dumps({k: out[k] for k in ("seconds", "stats", "counts")}, ensure_ascii=False))
    if a.out:
        Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
