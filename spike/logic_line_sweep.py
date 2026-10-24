"""L52 — 묶음의 모든 신호를 켜고 끄며 **모든 선(line)이 활성화되는가 · 모든 게이트가 범례대로인가** 를 센다 (읽기만).

L48 `logic_full_sim.py` 가 게이트 · 매크로를 봤다면 이것은 **선 하나하나**를 본다.  장마다 아무것도 안 줌 · 입력 하나씩 1 ·
모두 1 · 모두 1 에서 하나씩 0 (입력 행 + 누름단추/신호원) 을 돌리고, 그 모든 틀에서 **한 번도 1 이 되지 않은 선**을
모아 왜 그런지 가른다:
  const0      범례 FORCED INPUT `0` 등 — 도면이 0 으로 묶어 둔 선 (정상)
  floating    몰이가 없는 선 — 선 끝 · 읽기 빈틈
  unknown     판정 못 한 블록이 모는 선
  short       입력을 다 읽지 못한 게이트가 모는 선 (읽기 빈틈)
  analog      아날로그 연산 · 감시 블록이 모는 선 (값이 정한다 — 이 점검은 값을 안 준다)
  macro       매크로 출력 단자 선 (Typical 안 조건이 정한다)
  connector   짝 없는 연결 기호 · 장 밖에서 오는 연결
  upstream    앞 선이 1 이 안 돼서 (뿌리는 다른 선) — 뿌리 쪽에 센다
  logic_dead  입력 선은 전부 1 이 된 적이 있는데 출력은 한 번도 1 이 아님 — **논리 자체** (NOT 가 늘 1 인 입력 ·
              AND 가 서로 반대인 입력 · 메모리가 RESET 우선에 묶임 · 펄스 …).  사람이 볼 자리.
그리고 묶음 전체의 입력을 **한꺼번에** 1 로 두고(모든 신호 활성화) 같은 것을 센다.
게이트 점검은 L18 + L46 — 입력을 다 읽은 게이트는 범례 값 · 덜 읽은 게이트는 빠진 칸을 0 으로 채운 값과 같아야 한다.

  PID_DATA_DIR=… python3 spike/logic_line_sweep.py <job> [--max-sheets N] [--out 파일.json] [--no-global]
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
GATES = set(sim.MIN_INPUTS) | {"vote"}


def _label(s, net):
    """선이 닿는 행 · 블록 이름 한 줄 (사람이 찾아가기 쉽게)."""
    rows = [f"{r['side']}{r['n']}" for r in s["rows"] if r.get("net") == net]
    blks = sorted({p["block"] for p in s["ports"] if p["net"] == net})
    return " ".join(rows + blks)[:60]


def gate_faults(s, frames, holds=()):
    """L18 (다 읽은 게이트 = 범례 값) + L46 (덜 읽은 게이트 = 빠진 칸 0)."""
    ins, outs, drivers, _, _ = sim._index(s)
    bad = []
    for bid, b in s["blocks"].items():
        lg = b.get("logic")
        vote = sim._vote_of(b)
        if lg not in sim.MIN_INPUTS and not vote:
            continue
        iv_nets = [n for n, _, _ in ins[bid]]
        need = vote[1] if vote else sim.MIN_INPUTS[lg]
        short = len(iv_nets) < need
        for on, role, _ in outs[bid]:
            if len(drivers.get(on, [])) != 1:
                continue
            for fr in frames:
                unread = set(fr.get("unread") or ())
                if on in unread:
                    continue
                iv = [fr["values"].get(n, 0) for n in iv_nets]
                if fr["values"].get(on) is None:
                    continue
                if vote:
                    want = sim._vote3(list(iv) + [0] * max(0, vote[1] - len(iv)), *vote, sim._vote_op(b))
                else:
                    want = sim.gate3(lg, iv, 0)
                if want is not None and fr["values"][on] != want:
                    bad.append({"block": bid, "logic": lg or "vote", "short": short, "t": fr["t"], "in": iv,
                                "out": fr["values"][on]})
                    break
    return bad


def connector_faults(s, frames):
    """연결 기호 — 나오는 기호의 선은 같은 무리 들어가는 선의 OR 이어야 한다 (무리 안에 들어가는 선이 있을 때)."""
    ins, outs, drivers, _, groups = sim._index(s)
    bad = []
    for g, members in groups.items():
        src = [n for m in members for n, _, _ in ins.get(m, [])]
        dst = [n for m in members for n, _, _ in outs.get(m, [])]
        if not src or not dst:
            continue
        for on in dst:
            if len(drivers.get(on, [])) != 1:
                continue
            for fr in frames:
                v = fr["values"].get(on)
                want = 1 if any(fr["values"].get(n) == 1 for n in src) else 0
                if v is not None and v != want:
                    bad.append({"group": g, "net": on, "t": fr["t"], "want": want, "out": v})
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


def _is_const0(s, bid):
    b = s["blocks"][bid]
    lab = "".join(ch for ch in (b.get("label") or "").upper() if ch.isalnum())
    return b.get("logic") == "source" and lab in ("0", "0SIGNAL", "SIGNAL0")


def classify_dead(s, dead, ever1, short_all, floating_all):
    """1 이 된 적 없는 선 → 갈래.  upstream 은 뿌리까지 따라가 뿌리의 갈래를 함께 적는다."""
    ins, outs, drivers, sinks, groups = sim._index(s)
    B = s["blocks"]
    memo = {}

    def why(net, depth=0):
        if net in memo:
            return memo[net]
        memo[net] = ("cycle", net)
        drv = drivers.get(net, [])
        if not drv:
            r = ("floating", net)
        else:
            kinds = []
            for kind, x, role in drv:
                if kind == "row":
                    kinds.append(("row", net))            # 입력 행은 모두 1 로 줬다 — 여기 오면 안 된다
                    continue
                b = B[x]
                lg = b.get("logic")
                func = b.get("func")
                if _is_const0(s, x):
                    kinds.append(("const0", net))
                elif func == "MACRO":
                    kinds.append(("macro", net))
                elif func == "UNKNOWN" or lg == "unknown":
                    kinds.append(("unknown", net))
                elif func == "CONNECTOR":
                    g = b.get("group") or x
                    src = [n for m in groups.get(g, [x]) for n, _, _ in ins.get(m, [])]
                    if not src:
                        kinds.append(("connector", net))
                    else:
                        up = [n for n in src if n not in ever1]
                        kinds.append(why(up[0], depth + 1) if up and depth < 60 else ("logic_dead", net))
                elif lg in ("source", "sink", "light", "status"):
                    kinds.append(("source0", net) if lg == "source" else ("sink", net))
                elif x in short_all:
                    kinds.append(("short", net))
                elif lg in ("analog", "monitor", None) or b.get("analog"):
                    kinds.append(("analog", net))
                else:
                    iv = [n for n, r_, _ in ins.get(x, []) if r_ not in ("t",)]
                    dead_in = [n for n in iv if n not in ever1]
                    # 입력에 타이머 · 메모리 출력이 섞인 게이트 — 켜고 끄기(정지 조합)로는 못 세우는 자리다
                    # (펄스 ↔ 지연의 때 맞춤 · 래치 뒤 입력이 바뀌어야 함).  논리 자체와 갈라 센다.
                    src_lg = {(B[y].get("logic") if k == "block" else "row") for n in iv
                              for k, y, _ in drivers.get(n, [])}
                    if lg == "not":
                        # 입력이 늘 1 — 그 입력이 판정 못 한 블록 · 몰이 없는 선 · 아날로그에서 오면 그쪽이 뿌리다
                        up = why(iv[0], depth + 1) if iv and depth < 60 else ("not_always1", net)
                        kinds.append(up if up[0] in ("floating", "unknown", "short", "analog", "macro", "connector")
                                     else ("not_always1", net))
                    elif lg in ("delay_on", "delay_off", "pulse") and not dead_in:
                        kinds.append(("timer", net))               # 입력은 1 이 되는데 때 맞춤(기본 5초)에 걸림
                    elif not dead_in and lg in ("and", "vote", "nor", "nand", "or") and \
                            src_lg & {"delay_on", "delay_off", "pulse"}:
                        kinds.append(("timer", net))
                    elif not dead_in and lg in ("and", "vote", "nor", "nand", "or", "memory") and \
                            (src_lg & {"memory", "toggle"} or lg == "memory"):
                        kinds.append(("memory_seq", net))
                    elif dead_in and lg in ("and", "vote", "delay_on", "delay_off", "pulse", "pass", "step", "toggle",
                                            "or", "nor", "nand", "memory"):
                        # 입력 중 1 이 안 된 것이 있다 — OR 은 전부 죽어야 뿌리가 위다
                        if lg in ("or", "nor", "nand") and len(dead_in) < len(iv):
                            kinds.append(("logic_dead", net))
                        else:
                            kinds.append(why(dead_in[0], depth + 1) if depth < 60 else ("cycle", net))
                    else:
                        kinds.append(("logic_dead", net))
            order = ["floating", "unknown", "short", "macro", "analog", "connector", "const0", "source0", "sink",
                     "timer", "memory_seq", "not_always1", "logic_dead", "cycle", "row"]
            kinds.sort(key=lambda k: order.index(k[0]) if k[0] in order else 99)
            r = kinds[0]
        memo[net] = r
        return r

    out = {}
    for n in dead:
        kind, root = why(n)
        out[n] = {"kind": kind if root == n else "upstream", "root": root, "root_kind": kind}
    return out


def sweep_sheet(s, sheets, cache, found, stats):
    ins, outs, drivers, sinks, groups = sim._index(s)
    rows_in = [r["n"] for r in s["rows"] if r["side"] == "L" and r.get("net") is not None]
    srcs = [bid for bid, b in s["blocks"].items() if b.get("logic") == "source" and not ins.get(bid)
            and not _is_const0(s, bid)]
    keys = [f"row:{n}" for n in rows_in] + [f"block:{b}" for b in srcs]
    # 하나씩 0 도 본다 — 다른 장에서 쉬는 값(입력 0 의 NOT)이 1 로 들어오는 입력 행은 0 으로 주어야 뒤 NOT 이 선다
    cases = [{}] + [{k: 1} for k in keys] + [{k: 0} for k in keys]
    if keys:
        allon = {k: 1 for k in keys}
        cases += [allon] + [{**allon, k: 0} for k in keys]
    ever1, ever = set(), collections.defaultdict(set)
    short_all, floating_all = set(), set()
    allon_vals = None
    n_frames = 0
    for f in cases:
        stats["runs"] += 1
        try:
            r = sim.simulate_bundle(sheets, {s["page"]: f} if f else {}, None, s["page"], cache=cache, light=True)["focus"]
        except Exception as ex:
            found["error"].append({"sheet": s.get("sheet_no"), "forces": f, "error": repr(ex),
                                   "trace": traceback.format_exc()[-600:]})
            continue
        frames = r["frames"]
        n_frames += len(frames)
        g = gate_faults(s, frames)
        if g:
            found["gate"].append({"sheet": s.get("sheet_no"), "forces": f, "faults": g[:3]})
        c = connector_faults(s, frames)
        if c:
            found["connector"].append({"sheet": s.get("sheet_no"), "forces": f, "faults": c[:3]})
        if any("안정되지" in n for n in r.get("notes") or []):
            found["unstable"].append({"sheet": s.get("sheet_no"), "forces": f})
        last = frames[-1]["values"]
        op = opposites(s, last)
        if op:
            found["opposite"].append({"sheet": s.get("sheet_no"), "forces": f, "pairs": op})
        short_all.update(r.get("short_gates") or [])
        for fr in frames:
            floating_all.update(fr.get("unread") or ())
            for n, v in fr["values"].items():
                if n in s["nets"]:
                    ever[n].add(v)
                    if v == 1:
                        ever1.add(n)
        if f and len(f) == len(keys) and all(v == 1 for v in f.values()):
            allon_vals = last
    dead = [n for n in s["nets"] if n not in ever1]
    cls = classify_dead(s, dead, ever1, short_all, floating_all)
    # 2단계 — 켜고 끄기 조합(하나씩 · 모두 · 모두에서 하나 뺌)이 못 세운 선을 범례 정의로 거꾸로 풀어 본다 (L14 scenario).
    # 조합이 있으면 '논리 자체' 가 아니라 이 점검의 조합이 모자란 것이다 → reachable.  몰이 없는 선을 직접 켜야만
    # 서면(direct_nets) 읽기 빈틈이 길에 있다 → reachable_direct.
    for n, v in cls.items():
        if v["kind"] not in ("logic_dead", "timer", "memory_seq", "not_always1"):
            continue
        try:
            sc = sim.scenario(s, f"net:{n}", 1, sheets=sheets, cache=cache)
        except Exception as ex:                                  # noqa: BLE001
            v["scenario_error"] = repr(ex)
            continue
        if sc.get("ok"):
            direct1 = [k for k in sc.get("direct_nets") or () if (sc.get("forces") or {}).get(k) == 1]
            v["kind"] = "reachable_direct" if direct1 else "reachable"
            v["forces"] = sc.get("forces")
            v["steady"] = sc.get("steady")
        else:
            v["why"] = sc.get("why")
    kinds = collections.Counter(v["kind"] if v["kind"] != "upstream" else "upstream" for v in cls.values())
    roots = collections.Counter(v["root_kind"] for v in cls.values())
    stats["nets"] += len(s["nets"])
    stats["nets_on"] += len(ever1)
    stats["frames"] += n_frames
    for k, v in kinds.items():
        stats[f"dead_{k}"] += v
    for k, v in roots.items():
        stats[f"root_{k}"] += v
    for n, v in cls.items():
        if v["kind"] in ("logic_dead", "floating", "unknown", "short", "macro", "connector", "cycle", "row", "sink",
                         "reachable", "reachable_direct", "timer", "memory_seq", "not_always1"):
            found["dead"].append({"sheet": s.get("sheet_no"), "page": s["page"], "net": n, "kind": v["kind"],
                                  "at": _label(s, n), "forces": v.get("forces"), "steady": v.get("steady"),
                                  "why": v.get("why"),
                                  "driver": [(k, x, (s["blocks"].get(x) or {}).get("logic")) for k, x, _ in
                                             drivers.get(n, [])][:2]})
    if dead:
        found["sheet_dead"].append({"sheet": s.get("sheet_no"), "nets": len(s["nets"]), "dead": len(dead),
                                    "kinds": dict(kinds), "roots": dict(roots)})
    stats["sheets"] += 1
    return allon_vals


def global_all_on(res, sheets, cache, found, stats):
    """묶음 전체 입력(모든 장의 입력 행 · 누름단추)을 한꺼번에 1 — 모든 신호 활성화.  그래도 0 인 선을 장마다 센다."""
    forces = {}
    for s in res["sheets"]:
        ins, _, _, _, _ = sim._index(s)
        ks = {f"row:{r['n']}": 1 for r in s["rows"] if r["side"] == "L" and r.get("net") is not None}
        ks.update({f"block:{bid}": 1 for bid, b in s["blocks"].items()
                   if b.get("logic") == "source" and not ins.get(bid) and not _is_const0(s, bid)})
        if ks:
            forces[s["page"]] = ks
    t0 = time.time()
    try:
        r = sim.simulate_bundle(sheets, forces, None, None, cache=cache, light=True)
    except Exception as ex:
        found["error"].append({"sheet": "GLOBAL", "error": repr(ex), "trace": traceback.format_exc()[-600:]})
        return
    by_page = {s["page"]: s for s in sheets}
    tot = collections.Counter()
    per = []
    results = cache.get("_last_results") or {}
    for page in sorted(results.keys()):
        s = by_page.get(page)
        if not s or not s.get("rows"):
            continue
        p = results[page]
        frames = p.get("frames") or []
        if not frames:
            continue
        on = {n for fr in frames for n, v in fr["values"].items() if v == 1 and n in s["nets"]}
        dead = [n for n in s["nets"] if n not in on]
        short = set(p.get("short_gates") or ())
        cls = classify_dead(s, dead, on, short, set())
        kinds = collections.Counter(v["kind"] for v in cls.values())
        tot.update(kinds)
        tot["nets"] += len(s["nets"])
        tot["on"] += len(on)
        g = gate_faults(s, frames)
        if g:
            found["global_gate"].append({"sheet": s.get("sheet_no"), "faults": g[:3]})
        per.append({"sheet": s.get("sheet_no"), "nets": len(s["nets"]), "on": len(on), "dead": dict(kinds)})
    stats["global_seconds"] = round(time.time() - t0, 1)
    found["global"] = {"totals": dict(tot), "sheets": per}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("--max-sheets", type=int, default=0)
    ap.add_argument("--out")
    ap.add_argument("--no-global", action="store_true")
    a = ap.parse_args()
    res = api._result(a.job)
    sheets = api._all_sheets(res)
    cache = {}
    t0 = time.time()
    stats = collections.Counter()
    found = {"gate": [], "connector": [], "unstable": [], "opposite": [], "error": [], "dead": [], "sheet_dead": [],
             "global_gate": []}
    todo = [s for s in res["sheets"] if s.get("rows")]
    if a.max_sheets:
        todo = todo[:a.max_sheets]
    for s in todo:
        sweep_sheet(s, sheets, cache, found, stats)
        if stats["sheets"] % 50 == 0:
            print(f"… {stats['sheets']}/{len(todo)} 장 · {round(time.time() - t0)}초", flush=True)
    if not a.no_global:
        global_all_on(res, sheets, cache, found, stats)
    counts = {k: (len(v) if isinstance(v, list) else 1) for k, v in found.items()}
    out = {"job": a.job, "seconds": round(time.time() - t0, 1), "stats": dict(stats), "counts": counts,
           "found": found}
    print(json.dumps({k: out[k] for k in ("seconds", "stats", "counts")}, ensure_ascii=False))
    if a.out:
        Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
