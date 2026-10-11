"""시트 한 장의 논리를 돌린다 — 사람이 넣은 강제 신호(forcing)로 실제 로직처럼.

입력은 analyse.py 가 낸 시트 JSON 그대로다 (다시 읽지 않는다).

값은 디지털 둘뿐: 1(활성) · 0(비활성).  "알 수 없음" 을 두지 않는다 (사용자 지시 L3).
  * 왼쪽 행 입력 · 누름단추 · 들어오는 선이 없는 블록은 **사람이 활성화하지 않으면 0** 이다.
  * 몰이가 없는 선 · 판정 못 한 블록의 출력은 0 이다 (사람이 그 선을 직접 1 로 줄 수는 있다).
  * 선(넷)을 직접 강제하면 그 넷의 값은 몰이와 상관없이 그 값이다.
  * 블록 동작은 범례 G003 정의 (config/logic_symbols.yaml) — AND · OR · NOT · NAND · NOR ·
    메모리(우선 칸) · GT/DT/PD 타이머 (시간은 타이머 옆에 인쇄된 t 를 읽은 값 · 못 읽으면 1초로 보고 그렇게 말한다).
  * STEP 상자는 **근사 모델**이다: C_STEP = STEP_IN, STEP_OUT = STEP_IN AND CRIT.  설계서가 정의하는
    시퀀스 동작(이전 스텝 해제 · 단계 시간)은 아직 넣지 않았다 — 화면이 그렇게 말한다.

결과는 '틀(frame)' 들이다.  틀 0 = 사람이 누른 순간 안정된 상태, 그 뒤 = 타이머가 끝날 때마다의 상태.
각 틀에서 넷마다 값과 **깊이**(강제한 자리에서 블록 몇 개를 지나 왔나)를 준다 — 화면이 깊이 순서로 그린다.
"""
from __future__ import annotations

from collections import defaultdict

DEFAULT_T = 1.0
MAX_ITER = 300
MAX_FRAMES = 24


def _index(s):
    ins = defaultdict(list)          # block → [(net, role, cell)]
    outs = defaultdict(list)         # block → [(net, role, cell)]
    drivers = defaultdict(list)      # net → [("block", id, role) | ("row", n)]
    sinks = defaultdict(list)        # net → [block]
    for p in s["ports"]:
        if p["dir"] == "in":
            ins[p["block"]].append((p["net"], p.get("role", ""), p.get("cell", 0)))
            sinks[p["net"]].append(p["block"])
        else:
            outs[p["block"]].append((p["net"], p.get("role", ""), p.get("cell", 0)))
            drivers[p["net"]].append(("block", p["block"], p.get("role", "")))
    for r in s["rows"]:
        if r["side"] == "L":
            drivers[r["net"]].append(("row", r["n"], ""))
    # 연결 기호: 같은 묶음의 '들어가는' 기호 넷 → '나오는' 기호의 출력
    groups = defaultdict(list)
    for bid, b in s["blocks"].items():
        if b["func"] == "CONNECTOR":
            groups[b["group"] or bid].append(bid)
    return ins, outs, drivers, sinks, groups


def _and(vs):
    return 1 if vs and all(v == 1 for v in vs) else 0


def _or(vs):
    return 1 if any(v == 1 for v in vs) else 0


def _not(v):
    return 0 if v == 1 else 1


def simulate(s, forces=None, state=None, now=0.0):
    """forces = {"net:<id>": 0|1, "row:<n>": 0|1, "block:<id>": 0|1}  ·  state = 이전 호출이 돌려준 것.

    → {"frames": [{"t", "values", "depth", "note"}], "state", "notes"}
    """
    forces = dict(forces or {})
    st = {"mem": {}, "tim": {}, "t": now}
    if state:
        st["mem"].update(state.get("mem", {}))
        st["tim"].update({k: dict(v) for k, v in state.get("tim", {}).items()})
        st["t"] = max(now, state.get("t", 0.0))
    ins, outs, drivers, sinks, groups = _index(s)
    B = s["blocks"]
    notes = set()
    net_force = {k[4:]: v for k, v in forces.items() if k.startswith("net:")}
    row_force = {int(k[4:]): v for k, v in forces.items() if k.startswith("row:")}
    blk_force = {k[6:]: v for k, v in forces.items() if k.startswith("block:")}

    def block_out(bid, role, cell, val):
        b = B[bid]
        lg = b["logic"]
        if bid in blk_force:
            return blk_force[bid]
        iv = [val.get(n) for n, _, _ in ins[bid]]
        if lg in ("source",) or (not ins[bid] and lg in ("unknown", "sink")):
            return 0
        if lg == "and":
            return _and(iv)
        if lg == "nand":
            return _not(_and(iv))
        if lg == "or":
            return _or(iv)
        if lg == "nor":
            return _not(_or(iv))
        if lg == "not":
            return _not(iv[0] if iv else 0)
        if lg == "memory":
            q = st["mem"].get(bid, 0)
            return q if role != "qn" else _not(q)
        if lg in ("delay_on", "delay_off", "pulse"):
            return st["tim"].get(bid, {}).get("out", 0)
        if lg == "step":
            si = _or([val.get(n) for n, r, _ in ins[bid] if r == "step_in"])
            cr = _or([val.get(n) for n, r, _ in ins[bid] if r == "crit"])
            notes.add("STEP 상자는 근사 모델입니다 (C_STEP = STEP_IN · STEP_OUT = STEP_IN AND CRIT)")
            if role == "c_step":
                return si
            if role == "step_out":
                return _and([si, cr])
            return si
        if lg == "connector":
            g = groups.get(b["group"] or bid, [bid])
            vals = [val.get(n) for gid in g for n, _, _ in ins[gid]]
            return _or(vals) if vals else 0
        if ins[bid]:
            notes.add("판정 못 한 블록의 출력은 0 으로 보았습니다 (그 선을 직접 1 로 줄 수 있습니다)")
        return 0

    def settle(val_prev):
        val = dict(val_prev)
        depth = {}
        for it in range(MAX_ITER):
            changed = False
            # 메모리 상태 갱신
            for bid, b in B.items():
                if b["logic"] != "memory" or bid in blk_force:
                    continue
                S = _or([val.get(n) for n, r, c in ins[bid] if r == "set"])
                R = _or([val.get(n) for n, r, c in ins[bid] if r == "reset"])
                q = st["mem"].get(bid, 0)
                dom = b.get("param", {}).get("dominant", "")
                if S == 1 and R == 1:
                    nq = 1 if dom == "set" else (0 if dom == "reset" else q)
                    if not dom:
                        notes.add("기본 메모리에 S·R 이 함께 1 — 범례는 '상태가 바뀐다' 고 정의합니다 (여기서는 그대로 둡니다)")
                elif S == 1:
                    nq = 1
                elif R == 1:
                    nq = 0
                else:
                    nq = q
                if nq != q:
                    st["mem"][bid] = nq
                    changed = True
            for nid in s["nets"]:
                if nid in net_force:
                    v = net_force[nid]
                    d = 0
                else:
                    vs, ds = [], []
                    for kind, x, role in drivers.get(nid, []):
                        if kind == "row":
                            vs.append(row_force.get(x, 0))
                            ds.append(0)
                        else:
                            cell = 0
                            vs.append(block_out(x, role, cell, val))
                            dd = [depth.get(n, 0) for n, _, _ in ins[x]]
                            ds.append((max(dd) if dd else 0) + 1)
                    if not vs:
                        v, d = 0, 0
                    else:
                        v = _or(vs) if len(vs) > 1 else vs[0]
                        d = max(ds) if ds else 0
                if val.get(nid, "x") != v:
                    val[nid] = v
                    changed = True
                if depth.get(nid) != d:
                    depth[nid] = d
            if not changed:
                return val, depth
        notes.add("값이 안정되지 않았습니다 (되먹임 고리가 흔들림) — 마지막 값을 보입니다")
        return val, depth

    def timers_step(val, t):
        """입력 변화로 타이머 상태 갱신.  즉시 바뀐 것이 있으면 True."""
        changed = False
        for bid, b in B.items():
            lg = b["logic"]
            if lg not in ("delay_on", "delay_off", "pulse"):
                continue
            ts = st["tim"].setdefault(bid, {"out": 0, "inp": 0, "due": None, "to": None})
            inp = _or([val.get(n) for n, _, _ in ins[bid]]) or 0
            T = float(b.get("param", {}).get("t") or DEFAULT_T)
            if not b.get("param", {}).get("t"):
                notes.add("타이머 시간을 읽지 못한 블록은 1초로 보았습니다")
            prev = ts["inp"]
            if lg == "delay_on":
                if inp == 1 and prev != 1:
                    ts["due"], ts["to"] = t + T, 1
                elif inp != 1:
                    if ts["out"] != 0:
                        ts["out"] = 0
                        changed = True
                    ts["due"] = None
            elif lg == "delay_off":
                if inp == 1:
                    if ts["out"] != 1:
                        ts["out"] = 1
                        changed = True
                    ts["due"] = None
                elif prev == 1:
                    ts["due"], ts["to"] = t + T, 0
            elif lg == "pulse":
                if inp == 1 and prev != 1:
                    if ts["out"] != 1:
                        ts["out"] = 1
                        changed = True
                    ts["due"], ts["to"] = t + T, 0
            ts["inp"] = inp
        return changed

    frames = []
    t = st["t"]
    val = {}
    for _ in range(20):
        val, depth = settle(val)
        if not timers_step(val, t):
            break
    frames.append({"t": t, "values": val, "depth": depth, "note": "누른 순간"})
    while len(frames) < MAX_FRAMES:
        due = [(ts["due"], bid) for bid, ts in st["tim"].items() if ts.get("due") is not None]
        if not due:
            break
        t2 = min(d for d, _ in due)
        fired = []
        for d, bid in due:
            if d <= t2 + 1e-9:
                ts = st["tim"][bid]
                ts["out"] = ts["to"]
                ts["due"] = None
                fired.append(bid)
        t = t2
        for _ in range(20):
            val, depth = settle(val)
            if not timers_step(val, t):
                break
        labels = [B[b].get("param", {}).get("text") or B[b]["func"] for b in fired]
        frames.append({"t": t, "values": val, "depth": depth,
                       "note": f"{', '.join(labels)} 경과", "fired": fired})
    st["t"] = t
    return {"frames": frames, "state": st, "notes": sorted(notes)}


def trace(s, start, direction="down"):
    """논리와 상관없이 연결만 따라간다 — 넷에서 시작해 블록을 지나 다음 넷으로 (깊이 순서).

    start = "net:<id>" | "row:<n>" | "block:<id>".  연결 기호는 같은 묶음끼리 건너간다.
    → {"order": [{"net", "depth"}], "blocks": [{"block", "depth"}]}
    """
    ins, outs, drivers, sinks, groups = _index(s)
    B = s["blocks"]
    nets0 = []
    if start.startswith("net:"):
        nets0 = [start[4:]]
    elif start.startswith("row:"):
        n = int(start[4:])
        nets0 = [r["net"] for r in s["rows"] if r["n"] == n]
    elif start.startswith("block:"):
        bid = start[6:]
        nets0 = [n for n, _, _ in (outs[bid] if direction == "down" else ins[bid])]
    seen_n = {n: 0 for n in nets0}
    seen_b = {}
    frontier = list(nets0)
    depth = 0
    while frontier and depth < 200:
        depth += 1
        nxt = []
        for nid in frontier:
            if direction == "down":
                bs = sinks.get(nid, [])
            else:
                bs = [x for k, x, _ in drivers.get(nid, []) if k == "block"]
            for bid in bs:
                if bid in seen_b:
                    continue
                seen_b[bid] = depth
                if direction == "down":
                    nn = [n for n, _, _ in outs[bid]]
                    if B[bid]["func"] == "CONNECTOR":
                        for gid in groups.get(B[bid]["group"] or bid, []):
                            nn += [n for n, _, _ in outs[gid]]
                            seen_b.setdefault(gid, depth)
                else:
                    nn = [n for n, _, _ in ins[bid]]
                    if B[bid]["func"] == "CONNECTOR":
                        for gid in groups.get(B[bid]["group"] or bid, []):
                            nn += [n for n, _, _ in ins[gid]]
                            seen_b.setdefault(gid, depth)
                for n in nn:
                    if n not in seen_n:
                        seen_n[n] = depth
                        nxt.append(n)
        frontier = nxt
    return {"order": [{"net": n, "depth": d} for n, d in sorted(seen_n.items(), key=lambda kv: kv[1])],
            "blocks": [{"block": b, "depth": d} for b, d in sorted(seen_b.items(), key=lambda kv: kv[1])]}


# ------------------------------------------------------------------ 묶음 전체 (시트 사이)

MAX_PASSES = 12


def _row_values(s, values):
    """오른쪽(출력) 행마다 그 행 넷의 값."""
    return {r["n"]: values.get(r["net"], 0) for r in s["rows"] if r["side"] == "R" and r.get("net") is not None}


def simulate_bundle(sheets, forces=None, state=None, focus=None):
    """묶음의 모든 장을 함께 돌린다 — 한 장의 출력 행이 1 이면 그 행을 FM 으로 받는 다른 장의 입력 행도 1.

    연결은 도면이 적은 그대로다: 왼쪽 행의 FM `G034-71` (analyse._cross_refs 가 맞댄 `ref`).
    사람이 그 입력 행을 직접 0/1 로 준 것이 도면 연결보다 이긴다.  끝없는 되먹임은 MAX_PASSES 에서 멈추고 말한다.

    forces = {page: {key: 0|1}} · state = {page: 이전 state} · focus = 화면이 보는 장
    → {"focus": 그 장의 simulate 결과, "linked": {page: {row: 값}}, "pages": [...], "state": {page: st}, "notes"}
    """
    forces = {int(k): v for k, v in (forces or {}).items()}
    state = {int(k): v for k, v in (state or {}).items()}
    by_page = {s["page"]: s for s in sheets}
    by_no = {s["sheet_no"]: s for s in sheets if s.get("sheet_no")}
    # 받는 쪽: page → [(row n, 보내는 page, 보내는 row)]
    feeds = defaultdict(list)
    for s in sheets:
        for r in s["rows"]:
            ref = r.get("ref")
            if r["side"] == "L" and ref and ref.get("page") in by_page:
                feeds[s["page"]].append((r["n"], ref["page"], ref.get("src_row", ref["row"])))
    out_rows = {}                     # page → {row: 값}
    results = {}
    link_in = {}                      # page → {row: 값}

    def inputs_of(page):
        o = {}
        for n, sp, sr in feeds.get(page, ()):
            o[n] = out_rows.get(sp, {}).get(sr, 0)
        return o

    todo = set(by_page)
    notes = set()
    for _ in range(MAX_PASSES):
        if not todo:
            break
        changed_out = set()
        for page in sorted(todo):
            s = by_page[page]
            lin = inputs_of(page)
            f = {f"row:{n}": v for n, v in lin.items()}
            f.update(forces.get(page, {}))           # 사람이 준 값이 이긴다
            res = simulate(s, f, state.get(page))
            results[page] = res
            link_in[page] = lin
            rv = _row_values(s, res["frames"][-1]["values"])
            if rv != out_rows.get(page):
                out_rows[page] = rv
                changed_out.add(page)
        todo = {p for p, fd in feeds.items() if any(sp in changed_out for _, sp, _ in fd)
                and inputs_of(p) != link_in.get(p)}
    else:
        if todo:
            notes.add(f"시트 사이 되먹임이 {MAX_PASSES}번 안에 가라앉지 않았습니다 — 마지막 상태를 보입니다")
    # 사람이 준 장에서 1 인 연결을 따라 닿은 장 — 몇 장을 건너왔나 (화면이 그 순서로 보인다)
    hop = {p: 0 for p in forces if forces[p]}
    frontier = list(hop)
    while frontier:
        nxt = []
        for p in frontier:
            for q, fd in feeds.items():
                if q in hop:
                    continue
                if any(sp == p and out_rows.get(p, {}).get(sr) == 1 for _, sp, sr in fd):
                    hop[q] = hop[p] + 1
                    nxt.append(q)
        frontier = nxt
    pages = []
    for page, s in sorted(by_page.items()):
        lin = {n: v for n, v in link_in.get(page, {}).items() if f"row:{n}" not in forces.get(page, {})}
        user = forces.get(page, {})
        on_in = sorted(n for n, v in lin.items() if v == 1)
        on_out = sorted(n for n, v in out_rows.get(page, {}).items() if v == 1)
        if on_in or user:
            vals = results[page]["frames"][-1]["values"]
            pages.append({"page": page, "sheet_no": s.get("sheet_no"), "user": bool(user),
                          "hop": hop.get(page),
                          "linked_in": on_in, "on_out": on_out,
                          "on_nets": sum(1 for v in vals.values() if v == 1),
                          "from": sorted({(by_page[sp].get("sheet_no"), sr) for n, sp, sr in feeds.get(page, ())
                                          if n in on_in}),
                          "to": sorted({x["sheet"] for r in s["rows"] if r["side"] == "R" and r["n"] in on_out
                                        for x in r.get("refs_in", []) if x["sheet"] in by_no})})
    focus_res = results.get(focus) if focus is not None else None
    return {"focus": focus_res,
            "linked": {p: {n: v for n, v in lin.items() if f"row:{n}" not in forces.get(p, {})}
                       for p, lin in link_in.items() if lin},
            "pages": pages,
            "state": {p: r["state"] for p, r in results.items()},
            "notes": sorted(notes)}
