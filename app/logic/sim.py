"""시트 한 장의 논리를 돌린다 — 사람이 넣은 강제 신호(forcing)로 실제 로직처럼.

입력은 analyse.py 가 낸 시트 JSON 그대로다 (다시 읽지 않는다).

값은 디지털 둘뿐: 1(활성) · 0(비활성) — 화면에는 그 둘만 보인다 (사용자 지시 L3).
  * 왼쪽 행 입력 · 누름단추 · 들어오는 선이 없는 블록은 **사람이 활성화하지 않으면 0** 이다.
  * L10 — **입력 조건이 만족되지 않으면 출력은 나오지 않는다** (사용자 지시 · 모든 로직 · 모든 프로젝트 같은 원리).
    도면에서 **읽지 못한 입력**(몰이가 없는 선 · 판정 못 한 블록의 출력 · 범례가 여러 입력으로 그리는 AND/OR/NAND/NOR
    에서 둘 미만만 읽힌 칸 · 입력이 안 읽힌 NOT)은 안에서 '모름' 으로 계산한다 (Kleene 3값).  모름이 출력을 바꿀 수
    있으면 그 출력은 0 이고 `unread` 에 남는다 — 예: 입력이 안 읽힌 NOT 은 1 을 내지 않는다 · 입력 하나만 읽힌 AND 는
    그 하나가 1 이어도 1 을 내지 않는다.  모름과 상관없이 정해지는 출력은 그대로 낸다 (읽힌 입력 하나가 1 인 OR).
  * 선(넷)을 직접 강제하면 그 넷의 값은 몰이와 상관없이 그 값이다.
  * 블록 동작은 범례 G003 정의 (config/logic_symbols.yaml) — AND · OR · NOT · NAND · NOR ·
    메모리(우선 칸) · GT/DT/PD 타이머 (시간은 타이머 옆에 인쇄된 t 를 읽은 값 · 못 읽으면 1초로 보고 그렇게 말한다).
  * STEP 상자는 **근사 모델**이다: C_STEP = STEP_IN, STEP_OUT = STEP_IN AND CRIT.  설계서가 정의하는
    시퀀스 동작(이전 스텝 해제 · 단계 시간)은 아직 넣지 않았다 — 화면이 그렇게 말한다.

결과는 '틀(frame)' 들이다.  틀 0 = 사람이 누른 순간 안정된 상태, 그 뒤 = 타이머가 끝날 때마다의 상태.
각 틀에서 넷마다 값과 **깊이**(강제한 자리에서 블록 몇 개를 지나 왔나)를 준다 — 화면이 깊이 순서로 그린다.
"""
from __future__ import annotations

import re
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


# L10 — 3값(1 · 0 · None=모름).  범례 G003 정의를 그대로 옮긴 것이고, 모름은 "도면에서 읽지 못한 입력" 이다.
def _and3(vs):
    if not vs or any(v == 0 for v in vs):
        return 0 if vs else None
    return 1 if all(v == 1 for v in vs) else None


def _or3(vs):
    if any(v == 1 for v in vs):
        return 1
    return 0 if vs and all(v == 0 for v in vs) else None


def _not3(v):
    return None if v is None else (0 if v == 1 else 1)


def _b(v):
    """모름은 상태를 바꾸지 않는다 (메모리 S/R · 타이머 입력) — 0 으로 본다."""
    return 1 if v == 1 else 0


# 범례 G003 이 여러 입력(A·B·C…X)으로 그리는 게이트는 입력이 둘 이상이다 · NOT 은 하나다.
# 그보다 적게 읽혔으면 모자란 칸은 '모름' 이다 (그 칸의 선을 도면에서 못 읽었다).
MIN_INPUTS = {"and": 2, "nand": 2, "or": 2, "nor": 2, "not": 1}
_VOTE = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")       # 범례 'A/B' — A 개 이상 입력이 있을 때만 출력


def _vote_of(b):
    """판정 못 한 블록이라도 글자가 범례의 A/B 꼴이면 투표 블록이다 (OUTPUT EXISTS ONLY WHEN AT LEAST A OUT OF B
    INPUTS ARE PRESENT).  → (A, B) | None"""
    if b.get("logic") == "vote":
        p = b.get("param", {})
        return int(p.get("a", 0)), int(p.get("b", 0))
    if b.get("logic") != "unknown":
        return None
    m = _VOTE.match(b.get("label") or "")
    if not m:
        return None
    a, n = int(m.group(1)), int(m.group(2))
    return (a, n) if 0 < a <= n else None


def _vote3(vs, a, n):
    vs = list(vs) + [None] * max(0, n - len(vs))
    ones = sum(1 for v in vs if v == 1)
    unk = sum(1 for v in vs if v is None)
    if ones >= a:
        return 1
    return 0 if ones + unk < a else None


def gate3(lg, iv):
    """범례 정의 게이트 하나 — 읽힌 입력 수가 모자라면 모자란 칸을 모름으로 채운다."""
    iv = list(iv) + [None] * max(0, MIN_INPUTS.get(lg, 0) - len(iv))
    if lg == "and":
        return _and3(iv)
    if lg == "nand":
        return _not3(_and3(iv))
    if lg == "or":
        return _or3(iv)
    if lg == "nor":
        return _not3(_or3(iv))
    if lg == "not":
        return _not3(iv[0])
    return None


def _frame(t, val, depth, note):
    """화면은 1/0 만 본다 — 모름은 0 (출력 없음) 으로 내고 어느 선이 모름이었는지는 `unread` 에 남긴다."""
    return {"t": t, "values": {n: (0 if v is None else v) for n, v in val.items()},
            "unread": sorted(n for n, v in val.items() if v is None),
            "depth": depth, "note": note}


def simulate(s, forces=None, state=None, now=0.0):
    """forces = {"net:<id>": 0|1, "row:<n>": 0|1, "block:<id>": 0|1}  ·  state = 이전 호출이 돌려준 것.

    → {"frames": [{"t", "values", "depth", "note"}], "state", "notes"}
    """
    forces = dict(forces or {})
    st = {"mem": {}, "tim": {}, "sr": {}, "t": now}
    short = set()                     # 입력을 다 읽지 못한 게이트 (L10)
    if state:
        st["mem"].update(state.get("mem", {}))
        st["sr"].update(state.get("sr", {}))
        st["tim"].update({k: dict(v) for k, v in state.get("tim", {}).items()})
        st["t"] = max(now, state.get("t", 0.0))
    ins, outs, drivers, sinks, groups = _index(s)
    B = s["blocks"]
    notes = set()
    net_force = {k[4:]: v for k, v in forces.items() if k.startswith("net:")}
    row_force = {int(k[4:]): v for k, v in forces.items() if k.startswith("row:")}
    blk_force = {k[6:]: v for k, v in forces.items() if k.startswith("block:")}
    # L9 — 오른쪽(출력) 행을 사람이 1/0 으로 주면 그 행의 선을 그 값으로 (그 선을 모는 블록보다 이긴다)
    for r in s["rows"]:
        if r["side"] == "R" and r["n"] in row_force and r.get("net") is not None:
            net_force.setdefault(r["net"], row_force[r["n"]])

    def block_out(bid, role, cell, val):
        b = B[bid]
        lg = b["logic"]
        if bid in blk_force:
            return blk_force[bid]
        iv = [val.get(n) for n, _, _ in ins[bid]]
        if lg == "source":
            # 범례 G003 ACTIVATION — 글자 '1' 하나인 상자: OUTPUT ALWAYS EXISTS WHEN THIS FUNCTION ACTIVATE
            # (MOV 블록의 EN_OPEN · EN_CLOSE 허가처럼 언제나 서 있는 조건 · 사람이 0 으로 줄 수는 있다)
            if not ins[bid] and re.sub(r"[^0-9A-Z]", "", (b.get("label") or "").upper()) == "1":
                return 1
            return 0                                   # 누름단추 · HMI — 사람이 누르지 않으면 0
        if lg == "sink":
            return 0
        if lg in MIN_INPUTS:
            if len(iv) < MIN_INPUTS[lg]:
                short.add(bid)
            return gate3(lg, iv)
        vote = _vote_of(b)
        if vote:
            if len(iv) < vote[1]:
                short.add(bid)
            return _vote3(iv, *vote)
        if lg == "memory":
            q = st["mem"].get(bid, 0)
            return q if role != "qn" else _not(q)
        if lg in ("delay_on", "delay_off", "pulse"):
            return st["tim"].get(bid, {}).get("out", 0)
        if lg == "step":
            si = _or3([val.get(n) for n, r, _ in ins[bid] if r == "step_in"])
            cr = _or3([val.get(n) for n, r, _ in ins[bid] if r == "crit"])
            notes.add("STEP 상자는 근사 모델입니다 (C_STEP = STEP_IN · STEP_OUT = STEP_IN AND CRIT)")
            if role == "c_step":
                return si
            if role == "step_out":
                return _and3([si, cr])
            return si
        if lg == "connector":
            g = groups.get(b["group"] or bid, [bid])
            vals = [val.get(n) for gid in g for n, _, _ in ins[gid]]
            return _or3(vals) if vals else None        # 짝 기호의 입력을 못 읽었으면 모름
        if ins[bid]:
            notes.add("판정 못 한 블록은 출력을 내지 않습니다 (그 선을 직접 1 로 줄 수 있습니다)")
        return None

    def settle(val_prev):
        val = dict(val_prev)
        depth = {}
        for it in range(MAX_ITER):
            changed = False
            # 메모리 상태 갱신
            for bid, b in B.items():
                if b["logic"] != "memory" or bid in blk_force:
                    continue
                if any(n not in val and n in s["nets"] for n, _, _ in ins[bid]):
                    continue                        # 입력 선이 아직 안 정해졌다 (첫 바퀴) — 정해진 뒤에 본다
                S = _b(_or3([val.get(n) for n, r, c in ins[bid] if r == "set"]))
                R = _b(_or3([val.get(n) for n, r, c in ins[bid] if r == "reset"]))
                q = st["mem"].get(bid, 0)
                dom = b.get("param", {}).get("dominant", "")
                both_before = st["sr"].get(bid) == 1
                st["sr"][bid] = 1 if (S == 1 and R == 1) else 0
                if S == 1 and R == 1:
                    # 범례 G003: SET 우선 → C=1 · RESET 우선 → C=0 · 기본 메모리 → 상태가 바뀐다 (함께 1 이 되는 순간 한 번)
                    nq = 1 if dom == "set" else (0 if dom == "reset" else (q if both_before else _not(q)))
                    if not dom:
                        notes.add("기본 메모리에 S·R 이 함께 1 — 범례대로 상태를 한 번 바꿨습니다")
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
                        v, d = None, 0                 # L10 — 몰이가 없는 선 = 도면에서 못 읽은 입력
                    else:
                        v = _or3(vs) if len(vs) > 1 else vs[0]
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
            inp = _b(_or3([val.get(n) for n, _, _ in ins[bid]]))
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
    frames.append(_frame(t, val, depth, "누른 순간"))
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
        fr = _frame(t, val, depth, f"{', '.join(labels)} 경과")
        fr["fired"] = fired
        frames.append(fr)
    st["t"] = t
    if short:
        notes.add(f"입력을 다 읽지 못한 게이트 {len(short)}개는 그 입력 조건을 확인할 수 없어 출력을 내지 않습니다 (도면에서 확인)")
    return {"frames": frames, "state": st, "notes": sorted(notes), "short_gates": sorted(short)}


# L9 — 따라가기가 게이트를 지날지는 범례 정의가 정한다.  따라가는 신호를 1, 그 게이트의 다른
# 입력을 0 으로 보고 출력이 1 이 될 때만 뒤로 간다: OR·NAND 는 지나고 AND·NOR·NOT 은 멈춘다
# (AND 는 **모든** 입력이 따라온 선이어야 지난다 — 사용자 지시 *"AND gate 이면 모든 신호가 active
# 되어야 후단 output 이 active"*).  메모리·타이머·STEP·연결 기호·판정 못 한 블록은 연결만 본다.
_GATED = ("and", "nand", "or", "nor", "not")


def _gate_passes(lg, iv):
    """따라온 입력 1 · 나머지 0 · 읽지 못한 칸은 모름 — 출력이 확실히 1 일 때만 지난다 (L10)."""
    return gate3(lg, iv) == 1


def trace(s, start, direction="down"):
    """연결을 따라간다 — 넷에서 시작해 블록을 지나 다음 넷으로 (깊이 순서).

    start = "net:<id>" | "row:<n>" | "block:<id>".  연결 기호는 같은 묶음끼리 건너간다.
    아래로 갈 때 게이트는 범례 정의대로 — 따라온 입력만 1 로 보아 출력이 0 이면 거기서 멈추고
    `blocked` 에 사유를 적는다 (위로 거슬러 올라갈 때는 어디서 오는지를 전부 본다).
    → {"order": [{"net", "depth"}], "blocks": [{"block", "depth"}],
       "blocked": [{"block", "depth", "logic", "have", "need", "reason"}]}
    """
    ins, outs, drivers, sinks, groups = _index(s)
    B = s["blocks"]
    blocked = []
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
                    lg = B[bid].get("logic", "")
                    if lg in _GATED:
                        iv = [1 if n in seen_n else 0 for n, _, _ in ins[bid]]
                        if not _gate_passes(lg, iv):
                            have, need = sum(iv), len(iv)
                            if need < MIN_INPUTS.get(lg, 0):
                                reason = (f"{lg.upper()} — 입력을 {need}개만 읽었습니다 · 범례는 "
                                          f"{MIN_INPUTS[lg]}개 이상으로 그립니다 — 입력 조건을 확인할 수 없어 멈춥니다")
                            elif lg == "and":
                                reason = f"AND — 입력 {need}개 중 {have}개만 따라왔습니다 · 모두 활성이어야 뒤로 갑니다"
                            else:
                                reason = f"{lg.upper()} — 이 입력이 1 이면 출력은 0 입니다 (범례 정의)"
                            blocked.append({"block": bid, "depth": depth, "logic": lg,
                                            "have": have, "need": need, "reason": reason})
                            continue
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
    stopped = {x["block"] for x in blocked}
    return {"order": [{"net": n, "depth": d} for n, d in sorted(seen_n.items(), key=lambda kv: kv[1])],
            "blocks": [{"block": b, "depth": d} for b, d in sorted(seen_b.items(), key=lambda kv: kv[1])
                       if b not in stopped],
            "blocked": blocked}


# ------------------------------------------------------------------ 묶음 전체 (시트 사이)

MAX_PASSES = 12
_TO_REF = re.compile(r"\b([A-Z]+\d+)-(\d+)\b")     # 시트-행 꼴 (시트 이름은 그 묶음에 있는지로 거른다)


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
    # L9 — 보내는 쪽 TO 칸도 연결이다 (`G055-95` 의 TO `G025-10` → G025 시트 10행).  받는 쪽 FM 이 다른 곳을
    # 가리켜도(도면 어긋남 — from-to 점검이 붉게 말한다) 도면이 TO 로 보냈으면 신호는 간다.  TO 목록은 아래
    # 행으로 이어지므로 설명 없는 행의 TO 는 위로 처음 설명이 있는 행의 것이다 (fromto 와 같은 규칙).
    for s in sheets:
        for owner, tos in _to_runs(s).items():
            for _, text in tos:
              for sh, rn in _TO_REF.findall(text.replace(" ", "")):
                t = by_no.get(sh)
                if not t or not any(x["n"] == int(rn) and x["side"] == "L" for x in t["rows"]):
                    continue
                e = (int(rn), s["page"], owner)
                if e not in feeds[t["page"]]:
                    feeds[t["page"]].append(e)
    out_rows = {}                     # page → {row: 값}
    results = {}
    link_in = {}                      # page → {row: 값}

    def inputs_of(page):
        o = {}
        for n, sp, sr in feeds.get(page, ()):
            # 한 입력에 연결이 둘(FM 과 남의 TO)이면 어느 쪽이든 1 이면 1
            o[n] = 1 if (o.get(n) == 1 or out_rows.get(sp, {}).get(sr, 0) == 1) else 0
        return o

    # L12 — 매크로 블록: 그 상자의 입력 단자 값을 Typical 시트의 입력 행에 주고 그 시트를 돌려, 출력 행 값을
    # 상자의 출력 단자 선으로 낸다 (그 장 안에서 되먹임이 가라앉을 때까지 다시 돈다).
    macros = defaultdict(list)
    for s0 in sheets:
        for bid, b in s0["blocks"].items():
            m = b.get("macro") or {}
            if b.get("func") == "MACRO" and m.get("page") in by_page:
                macros[s0["page"]].append((bid, m))
    macro_force, macro_view, macro_state = {}, {}, {}

    def eval_macros(page, values):
        f, view, nst = {}, {}, {}
        old = (state.get(page) or {}).get("macros", {})
        for bid, m in macros.get(page, ()):
            ts = by_page[m["page"]]
            tf = {f"row:{x['row']}": (1 if values.get(x["net"]) == 1 else 0) for x in m["inputs"] if x.get("row")}
            res = simulate(ts, tf, old.get(bid))
            nst[bid] = res["state"]
            orow = _row_values(ts, res["frames"][-1]["values"])
            for x in m["outputs"]:
                if x.get("row") is not None:
                    f[f"net:{x['net']}"] = orow.get(x["row"], 0)
            view[bid] = {"sheet": m.get("sheet"), "page": m["page"],
                         "inputs": {str(x["row"]): (1 if values.get(x["net"]) == 1 else 0) for x in m["inputs"] if x.get("row")},
                         "outputs": {str(x["row"]): orow.get(x["row"], 0) for x in m["outputs"] if x.get("row") is not None}}
        return f, view, nst

    todo = set(by_page)
    notes = set()
    for _ in range(MAX_PASSES):
        if not todo:
            break
        changed_out = set()
        redo = set()
        for page in sorted(todo):
            s = by_page[page]
            lin = inputs_of(page)
            for _k in range(4 if macros.get(page) else 1):
                f = {f"row:{n}": v for n, v in lin.items()}
                f.update(macro_force.get(page, {}))      # 매크로가 모는 출력 선
                f.update(forces.get(page, {}))           # 사람이 준 값이 이긴다
                res = simulate(s, f, state.get(page))
                if not macros.get(page):
                    break
                mf, view, nst = eval_macros(page, res["frames"][-1]["values"])
                macro_view[page], macro_state[page] = view, nst
                if mf == macro_force.get(page):
                    break
                macro_force[page] = mf
            if macros.get(page):
                res["state"]["macros"] = macro_state.get(page, {})
            results[page] = res
            link_in[page] = lin
            rv = _row_values(s, res["frames"][-1]["values"])
            if rv != out_rows.get(page):
                out_rows[page] = rv
                changed_out.add(page)
        todo = {p for p, fd in feeds.items() if any(sp in changed_out for _, sp, _ in fd)
                and inputs_of(p) != link_in.get(p)} | redo
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
                          "to": sorted({by_page[q].get("sheet_no") for q, fd in feeds.items()
                                        for _, sp, sr in fd if sp == page and sr in on_out})})
    # 사람이 준 신호가 닿은 장(hop)에서 이동하다 만난 것만 — 아무것도 안 줘도 1 인 선(입력 0 의 NOT 등)은 빼고
    design = [e for e in _design_errors(sheets, by_page, by_no, out_rows) if e["page"] in hop]
    for e in design:
        if e["kind"] == "error":
            for c in pages:
                if c["page"] == e["page"]:
                    c["errors"] = c.get("errors", 0) + 1
    focus_res = results.get(focus) if focus is not None else None
    return {"focus": focus_res,
            "design_errors": design,
            "macros": {p: v for p, v in macro_view.items() if v},
            "linked": {p: {n: v for n, v in lin.items() if f"row:{n}" not in forces.get(p, {})}
                       for p, lin in link_in.items() if lin},
            "pages": pages,
            "state": {p: r["state"] for p, r in results.items()},
            "notes": sorted(notes)}


# ------------------------------------------------------------------ 이동하다 만난 설계 오류 (L11)

def _to_runs(s):
    """주인 행 → [(TO 가 적힌 행 n, 그 행의 TO 글자)] — TO 목록은 설명 없는 아래 행으로 이어진다 (fromto 와 같은 규칙).
    표(`table`)를 읽는다 — 선이 없는 이어진 TO 줄(G055 96 · TO G042-6)은 `rows` 에 없다."""
    o, owner = {}, None
    for r in sorted((x for x in (s.get("table") or s["rows"]) if x["side"] == "R"), key=lambda x: x["n"]):
        if (r.get("desc") or "").strip():
            owner = r["n"]
        elif not (r.get("to") or "").strip():
            owner = None
        if owner is not None and (r.get("to") or "").strip():
            o.setdefault(owner, []).append((r["n"], r["to"]))
    return o


def _norm_desc(t):
    return re.sub(r"[^A-Z0-9]", "", (t or "").upper())


def _design_errors(sheets, by_page, by_no, out_rows):
    """**활성(1)인 신호**가 TO · FM 을 따라 이동하는 자리에서 도면끼리 어긋난 곳 (사용자 지시 L11).

    보내는 쪽: 1 인 출력 행(주인 행)과 그 아래로 이어지는 TO 줄들의 TO 마다 —
      ① TO 의 시트가 이 묶음에 없다  ② 그 시트에 그 행 입력이 없다  ③ 그 행이 비어 있다(설명·FM 없음)
      ④ 그 행의 FM 이 이 신호를 가리키지 않는다(다른 곳 · 없음)  → 설계 오류.
      설명만 다르면 '확인' (연결은 맞다 · L5 와 같은 구분).  시트 이름 머리글이 이 묶음과 다르면(Loop `P…` 등) 다른 묶음 —
      여기서 확인할 수 없다고만 말한다.
    받는 쪽: FM 으로 1 을 받은 입력 행 — 보내는 행의 TO 목록에 이 장-행이 없으면(TO 가 다른 곳만 적음) 설계 오류.
    판정은 읽은 글자 그대로이고(fromto 와 같은 규칙) 고치지 않는다.
    """
    prefixes = {no[:1] for no in by_no}
    out = []
    seen = set()

    def add(e):
        k = (e["page"], e["row"], e["to"], e["why"])
        if k not in seen:
            seen.add(k)
            out.append(e)

    run_of = {s["page"]: _to_runs(s) for s in sheets}

    def in_table(t, rn):
        for x in t.get("table") or t["rows"]:
            if x["side"] == "L" and x["n"] == rn:
                return x
        return None
    for s in sheets:
        page, me = s["page"], s.get("sheet_no") or ""
        on = {n for n, v in out_rows.get(page, {}).items() if v == 1}
        for owner, tos in run_of[page].items():
            if owner not in on:
                continue
            od = next((r.get("desc") for r in s["rows"] if r["side"] == "R" and r["n"] == owner), "")
            for at, text in tos:
                for sh, rn in _TO_REF.findall(text.replace(" ", "")):
                    rn = int(rn)
                    base = {"page": page, "sheet_no": me, "row": owner, "at_row": at, "to": f"{sh}-{rn}",
                            "target_sheet": sh, "target_row": rn, "desc": od}
                    if sh[:1] not in prefixes:
                        add({**base, "kind": "other", "target_page": None,
                             "why": f"TO {sh}-{rn} — 다른 묶음(이 묶음에 없는 시트 계열)으로 갑니다 · 여기서는 확인할 수 없습니다"})
                        continue
                    t = by_no.get(sh)
                    if t is None:
                        add({**base, "kind": "error", "target_page": None,
                             "why": f"TO {sh}-{rn} — {sh} 시트가 이 묶음에 없습니다"})
                        continue
                    tr = in_table(t, rn)
                    base["target_page"] = t["page"]
                    if tr is None:
                        add({**base, "kind": "error", "why": f"TO {sh}-{rn} — {sh} 시트에 {rn}행 입력이 없습니다"})
                        continue
                    if not (tr.get("desc") or "").strip() and not (tr.get("fm") or "").strip():
                        add({**base, "kind": "error", "why": f"TO {sh}-{rn} — 그 행이 비어 있습니다 (받는 신호가 정의되어 있지 않음)"})
                        continue
                    fm = (tr.get("fm") or "").strip()
                    if not fm:
                        add({**base, "kind": "error", "why": f"TO {sh}-{rn} — 그 행에 FM 이 없습니다 (어디서 오는지 적혀 있지 않음)"})
                        continue
                    # FM 이 이 신호(주인 행 또는 그 아래로 이어진 TO 줄)를 가리키는가
                    back = [(a, int(b)) for a, b in _TO_REF.findall(fm.replace(" ", ""))]
                    mine = {(me, n) for n, _ in tos} | {(me, owner)}
                    if not any(x in mine for x in back):
                        add({**base, "kind": "error",
                             "why": f"TO {sh}-{rn} — 그 행의 FM 은 {fm} 을 가리킵니다 (이 신호 {me}-{owner} 가 아님 · 잘못 연결)"})
                        continue
                    a, b = _norm_desc(od), _norm_desc(tr.get("desc"))
                    if a and b and a != b:
                        add({**base, "kind": "warn",
                             "why": f"TO {sh}-{rn} — 연결은 맞고 설명이 다릅니다: '{od}' ↔ '{tr.get('desc')}'"})
    # 받는 쪽 — FM 으로 1 을 받았는데 보내는 행의 TO 목록에 이 장-행이 없다
    for s in sheets:
        page, me = s["page"], s.get("sheet_no") or ""
        for r in s["rows"]:
            ref = r.get("ref") or {}
            if r["side"] != "L" or ref.get("page") not in by_page:
                continue
            sp, own = ref["page"], ref.get("src_row", ref.get("row"))
            if out_rows.get(sp, {}).get(own) != 1:
                continue
            tos = [(a, int(b)) for _, text in run_of[sp].get(own, [])
                   for a, b in _TO_REF.findall(text.replace(" ", "")) if a[:1] in prefixes]
            if tos and (me, r["n"]) not in tos:
                src = by_page[sp].get("sheet_no") or ""
                add({"page": sp, "sheet_no": src, "row": own, "at_row": own, "to": f"{me}-{r['n']}",
                     "target_sheet": me, "target_row": r["n"], "target_page": page, "desc": r.get("desc") or "",
                     "kind": "error",
                     "why": f"{me}-{r['n']} 의 FM 은 {r.get('fm')} 인데 {src}-{own} 의 TO 는 "
                            f"{', '.join(f'{a}-{b}' for a, b in tos)} 만 적습니다 (잘못 연결)"})
    order = {"error": 0, "warn": 1, "other": 2}
    out.sort(key=lambda e: (order[e["kind"]], e["sheet_no"], e["row"], e["to"]))
    return out

