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

from . import analog as A

DEFAULT_T = 5.0           # L22 — 도면이 시간을 적지 않은 타이머 (사용자 지시: 기본 5초 · L15 는 10초였다)
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
        if r["side"] == "L" and r.get("net") is not None:          # 사람이 만든 행(L24)은 선이 없을 수 있다
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
# L16 — 이 블록이 모는 선은 사람이 직접 켜지 않는다 (목표로 두고 게이트가 판정한다)
GATE_LOGIC = {"and", "or", "nand", "nor", "not", "vote", "memory", "delay_on", "delay_off", "pulse", "step"}
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


def _back_propagate(B, ins, drivers, groups, net_force, user):
    """→ ({"row:n"|"block:id": 값}, [모순 설명]).  사람이 준 선 값에서 앞으로(몰이 쪽으로) 범례 정의를 거꾸로 푼다.
    AND=1 → 모든 입력 1 · NAND=0 → 모든 입력 1 · OR=0 → 모든 입력 0 · NOR=1 → 모든 입력 0 · NOT → 반대 ·
    입력 하나뿐인 OR · 타이머(GT/DT/PD)=1 → 입력 1 · 연결 기호 → 묶음의 들어오는 선.  그 밖(OR=1 · AND=0 · 메모리 ·
    판정 못 한 블록)은 정해지지 않으므로 멈춘다.  사람이 직접 준 값은 바꾸지 않는다."""
    req, implied, conflicts = {}, {}, []

    def setleaf(key, v):
        if key in user:
            if user[key] != v:
                conflicts.append(f"{key} 를 사람이 {user[key]} 로 주었는데 뒤쪽 조건은 {v} 를 요구")
            return
        if implied.get(key, v) != v:
            conflicts.append(f"{key} 가 0 과 1 을 함께 요구받음")
            return
        implied[key] = v

    def back(net, v, depth=0):
        if depth > 80:
            return
        if net in req:
            if req[net] != v:
                conflicts.append(f"선 #{net} 이 0 과 1 을 함께 요구받음")
            return
        req[net] = v
        drv = drivers.get(net, [])
        if len(drv) > 1 and v == 1:
            return                                    # 몰이가 둘 이상인 선이 1 — 어느 쪽인지 정해지지 않는다
        for kind, x, role in drv:
            if kind == "row":
                setleaf(f"row:{x}", v)
                continue
            b = B[x]
            lg = b.get("logic")
            iv = [n for n, _, _ in ins[x]]
            if lg == "source":
                setleaf(f"block:{x}", v)
            elif lg == "and" and v == 1 or lg == "nand" and v == 0:
                for n in iv:
                    back(n, 1, depth + 1)
            elif lg == "or" and v == 0 or lg == "nor" and v == 1:
                for n in iv:
                    back(n, 0, depth + 1)
            elif lg == "or" and v == 1 and len(iv) == 1:
                back(iv[0], 1, depth + 1)
            elif lg == "not" and iv:
                back(iv[0], 1 - v, depth + 1)
            elif lg in ("delay_on", "delay_off", "pulse") and v == 1 and len(iv) == 1:
                back(iv[0], 1, depth + 1)
            elif lg == "memory":
                # L16 — Q=1(또는 반대 출력 D=0) 이 나오려면 SET 이 1 이어야 하고 (SET 입력이 하나일 때만 정해진다),
                # SET 우선이 아니면 RESET 은 0 이어야 한다.  Q=0 은 '한 번도 SET 안 됨' 일 수도 있어 정해지지 않는다.
                q1 = (v == 1) != (role == "qn")
                if q1:
                    sets = [n for n, r_, _ in ins[x] if r_ == "set"]
                    if len(sets) == 1:
                        back(sets[0], 1, depth + 1)
                    if (b.get("param") or {}).get("dominant") != "set":
                        for n, r_, _ in ins[x]:
                            if r_ == "reset":
                                back(n, 0, depth + 1)
            elif lg == "connector":
                g = groups.get(b.get("group") or x, [x])
                gin = [n for gid in g for n, _, _ in ins[gid]]
                if len(gin) == 1 or v == 0:
                    for n in gin:
                        back(n, v, depth + 1)

    for net, v in net_force.items():
        back(net, v)
    return implied, conflicts


def _secs(v):
    """사람이 적은 타이머 시간 — 0 보다 크고 하루 이하인 수만."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if 0 < f <= 86400 else None


def timer_seconds(b, override=None):
    """L15 — 타이머 시간: 사람이 바꾼 값(요청 · L22 저장된 값) → 도면이 적은 값(`t= 3sec`) → 기본 DEFAULT_T."""
    prm = b.get("param") or {}
    for v in (override, prm.get("t_user"), prm.get("t")):
        f = _secs(v)
        if f is not None:
            return f
    return DEFAULT_T


def _frame(t, val, depth, note):
    """화면은 1/0 만 본다 — 모름은 0 (출력 없음) 으로 내고 어느 선이 모름이었는지는 `unread` 에 남긴다."""
    return {"t": t, "values": {n: (0 if v is None else v) for n, v in val.items()},
            "unread": sorted(n for n, v in val.items() if v is None),
            "depth": depth, "note": note}


def _simulate_once(s, forces=None, state=None, now=0.0, timers=None, soft=None, settled=(), extra=None, analog=None):
    """forces = {"net:<id>": 0|1, "row:<n>": 0|1, "block:<id>": 0|1}  ·  state = 이전 호출이 돌려준 것.
    soft = {n: 0|1} — L16 다른 시트에서 이어져 오는 입력 행 값.  사람이 준 값이 아니므로 거꾸로 맞추기가 다른 값을
    요구하면 그 값이 이긴다 (`pulled` 에 남아 묶음이 보내는 시트의 출력까지 줄줄이 켠다).
    settled = 보내는 시트에 이미 요청한 입력 행 — 그 시트가 실제로 낸 값을 그대로 쓴다 (그 시트 게이트가 막았으면 0).

    → {"frames": [{"t", "values", "depth", "note"}], "state", "notes"}
    """
    forces = dict(forces or {})
    tset = {str(k): float(v) for k, v in (timers or {}).items() if _secs(v) is not None}
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
    # L26 — 아날로그 값(MED · 입력 행)과 감시 블록(HHH · HH …)의 설정값: 값과 설정값이 다 있으면 감시 출력이 1/0
    an_net, an_blk, an_keys = A.nets(s, analog, (ins, outs, drivers, sinks))
    mons = {m["block"]: m for m in A.monitors(s, an_net, (ins, outs, drivers, sinks))}
    net_force = {k[4:]: v for k, v in forces.items() if k.startswith("net:")}
    row_force = {int(k[4:]): v for k, v in forces.items() if k.startswith("row:")}
    blk_force = {k[6:]: v for k, v in forces.items() if k.startswith("block:")}
    row_force0, blk_force0 = dict(row_force), dict(blk_force)
    # L9 — 오른쪽(출력) 행을 사람이 1/0 으로 주면 그 행의 선을 그 값으로.
    # L16 — 단 그 선을 **게이트가 몰면** 그 값은 '목표' 다: 선을 직접 그 값으로 두지 않고, 거꾸로 맞추기로 게이트 앞
    # 입력을 줄줄이 정한 뒤 게이트가 범례대로 판정한다 (사용자 지시 — "AND 의 12 · 14 번이 활성화 안 되었는데 AND 의
    # Output 이 나가면 안 된다").  몰이가 없는 선 · 판정 못 한 블록 · 연결 기호 · 누름단추가 모는 선은 예전처럼 직접 준다.
    for r in s["rows"]:
        if r["side"] == "R" and r["n"] in row_force and r.get("net") is not None:
            net_force.setdefault(r["net"], row_force[r["n"]])
    goals = {}
    for n in list(net_force):
        if any(kind == "block" and _gate_like(B[x]) for kind, x, _ in drivers.get(n, [])):
            goals[n] = net_force.pop(n)
    # L17 — 게이트 블록 자체를 사람이 1/0 으로 주어도 같다 (입력이 안 읽힌 게이트를 눌러 켠 경우): 출력 선을 목표로.
    for bid in list(blk_force):
        if bid in B and _gate_like(B[bid]):
            v = blk_force.pop(bid)
            for n, role, _ in outs[bid]:
                goals.setdefault(n, (1 - v) if role == "qn" else v)
    # L13 — 연결 기호(같은 글자 A ↔ A)는 한 신호다: 사람이 그 묶음의 어느 기호 · 그 기호에 닿은 선을 1/0 으로 주면
    # 같은 묶음의 다른 기호에서 나가는 선도 그 값이다 (사용자 지시 — "A 가 활성화되면 반대쪽 A 도").
    for gid, members in groups.items():
        if len(members) < 2:
            continue
        nets = {n for m in members for n, _, _ in ins[m] + outs[m]}
        v = next((blk_force[m] for m in members if m in blk_force), None)
        if v is None:
            v = next((net_force[n] for n in nets if n in net_force), None)
        if v is None:
            continue
        for m in members:
            for n, _, _ in outs[m]:
                net_force.setdefault(n, v)

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
            m = mons.get(bid)
            if m and m["out"] is not None:
                return m["out"]                        # L26 — 아날로그 값이 설정값을 넘었는가
            return 0                                   # 누름단추 · HMI — 사람이 누르지 않으면 0
        if lg == "sink":
            return 0
        if lg == "pass":                               # 이음점 · 그대로 넘김 (사람이 가르친 종류 · L25)
            return _or3(iv) if iv else None
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
            T = timer_seconds(b, tset.get(bid))
            if bid not in tset and not b.get("param", {}).get("t"):
                notes.add(f"타이머 시간을 읽지 못한 블록은 {DEFAULT_T:g}초로 보았습니다 (블록을 눌러 바꿀 수 있습니다)")
            ts["T"] = T
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

    # L13 — 거꾸로 맞추기: 사람이 게이트 **뒤** 선(또는 출력 행)을 1/0 으로 주면, 그 값이 나오도록 범례 조건으로
    # 정해지는 입력을 앞쪽으로 따라가며 정한다 (사용자 지시 — "AND 이후 신호를 활성화하면 Gate input 들은 AND output 이
    # 나갈 수 있는 조건으로 0 or 1 로 모두 강제").  정해지지 않는 자리(OR=1 · AND=0 · 메모리)에서는 멈춘다.
    implied, conflicts = _back_propagate(B, ins, drivers, groups, {**net_force, **goals},
                                         {**{f"row:{k}": v for k, v in row_force.items()},
                                          **{f"block:{k}": v for k, v in blk_force.items()}})
    for k, v in (extra or {}).items():
        if k not in implied and not (k.startswith("row:") and int(k[4:]) in row_force) \
                and not (k.startswith("block:") and k[6:] in blk_force):
            implied[k] = v                             # L17 — 정해지지 않는 자리에서 고른 갈래
    for k, v in implied.items():
        if k.startswith("row:"):
            row_force.setdefault(int(k[4:]), v)
        elif k.startswith("block:"):
            blk_force.setdefault(k[6:], v)
    pulled = {}
    user_rows = {int(k[4:]) for k in forces if k.startswith("row:")}
    for n, v in (soft or {}).items():
        n = int(n)
        if n in settled and n not in user_rows:
            row_force[n] = v
            continue
        if n in row_force:
            if f"row:{n}" in implied and row_force[n] != v:
                pulled[n] = row_force[n]               # 앞쪽 시트에서 오는 값과 다른 값이 필요하다 — 묶음이 이어서 켠다
            continue
        row_force[n] = v
    if conflicts:
        notes.add("거꾸로 맞추기에서 한 신호가 0 과 1 을 함께 요구받았습니다 — " + " · ".join(conflicts[:3]))

    def _running(fr, now_):
        """L15 — 이 틀에서 시간을 세는 타이머 (화면이 카운트다운을 그린다)."""
        fr["running"] = [{"block": bid, "left": round(ts["due"] - now_, 3), "T": ts.get("T", DEFAULT_T)}
                         for bid, ts in sorted(st["tim"].items()) if ts.get("due") is not None]
        return fr

    frames = []
    t = st["t"]
    val = {}
    for _ in range(20):
        val, depth = settle(val)
        if not timers_step(val, t):
            break
    frames.append(_running(_frame(t, val, depth, "누른 순간"), t))
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
        fr = _running(_frame(t, val, depth, f"{', '.join(labels)} 경과"), t)
        fr["fired"] = fired
        frames.append(fr)
    st["t"] = t
    # L16 — 목표로 둔 출력 중 게이트 조건이 끝내 맞지 않은 것 (어느 틀에서든 그 값이 되었으면 맞은 것 — 타이머 뒤)
    unmet = []
    for n, want in goals.items():
        if not any(fr["values"].get(n, 0) == want for fr in frames):
            blk = next((x for kind, x, _ in drivers.get(n, []) if kind == "block"), None)
            last_unread = set(frames[-1]["unread"])
            unmet.append({"net": n, "want": want, "got": frames[-1]["values"].get(n, 0), "block": blk,
                          "logic": (("vote" if _vote_of(B[blk]) else B[blk].get("logic")) if blk else None),
                          # L17 — 그 게이트 입력 중 도면에서 몰이를 못 읽은 선 (조건을 확인할 수 없어 출력을 내지 않는다)
                          "unread": [m for m, _, _ in (ins[blk] if blk else []) if m in last_unread]})
    if unmet:
        notes.add(f"출력 선을 직접 켜지 않습니다 — 게이트 조건이 맞을 때만 나갑니다.  조건을 다 채우지 못한 출력 {len(unmet)}개"
                  " (앞쪽 입력이 0 으로 고정됐거나, OR · 메모리처럼 어느 입력인지 정해지지 않는 자리)")
    if short:
        notes.add(f"입력을 다 읽지 못한 게이트 {len(short)}개는 그 입력 조건을 확인할 수 없어 출력을 내지 않습니다 (도면에서 확인)")
    if any(m["value"] is not None and m["sp"] is None for m in mons.values()):
        notes.add("설정값이 없는 감시 블록은 값을 맞대지 못했습니다 — 블록을 눌러 설정값을 적을 수 있습니다")
    return {"frames": frames, "state": st, "notes": sorted(notes), "short_gates": sorted(short),
            "analog": {"nets": an_net, "blocks": an_blk, "keys": an_keys, "monitors": list(mons.values()),
                       "default_ma": A.DEFAULT_MA},
            "implied": implied, "conflicts": conflicts,
            "goals": [{"net": n, "want": v} for n, v in goals.items()], "unmet": unmet, "pulled": pulled,
            "_goals": goals, "_user": {**{f"row:{k}": v for k, v in row_force0.items()},
                                       **{f"block:{k}": v for k, v in blk_force0.items()}}}


def _gate_like(b):
    return b.get("logic") in GATE_LOGIC or bool(_vote_of(b))


CHOICE_TRIES = 16          # L17 — 정해지지 않는 자리(OR=1 · AND=0 · 메모리 …)에서 앞으로 돌려 볼 갈래 수
CHOICE_STEPS = 4000        # 갈래를 찾는 깊이 우선 걸음 상한 (큰 장에서 막히지 않게)


def simulate(s, forces=None, state=None, now=0.0, timers=None, soft=None, settled=(), analog=None):
    """forces = {"net:<id>": 0|1, "row:<n>": 0|1, "block:<id>": 0|1}  ·  state = 이전 호출이 돌려준 것.
    soft = {n: 0|1} — L16 다른 시트에서 이어져 오는 입력 행 값.  사람이 준 값이 아니므로 거꾸로 맞추기가 다른 값을
    요구하면 그 값이 이긴다 (`pulled` 에 남아 묶음이 보내는 시트의 출력까지 줄줄이 켠다).
    settled = 보내는 시트에 이미 요청한 입력 행 — 그 시트가 실제로 낸 값을 그대로 쓴다 (그 시트 게이트가 막았으면 0).

    L17 — 게이트가 모는 출력을 1/0 으로 주면 그 값은 목표다.  범례 정의로 정해지는 입력(AND=1 → 전부 1 …)은 바로 정하고,
    정해지지 않는 자리(OR=1 → 입력 하나 · AND=0 → 입력 하나 · NOR=0 · NAND=1 · 투표 A/B · 메모리 · 타이머 · STEP)는
    갈래를 하나씩 골라 **앞으로 돌려** 목표가 서는 조합을 쓴다 (출력은 언제나 게이트가 판정한다 — 직접 켜지 않는다).

    → {"frames": [{"t", "values", "depth", "note"}], "state", "notes", "unmet", "choice", …}
    """
    import copy
    st0 = copy.deepcopy(state) if state else None
    res = _simulate_once(s, forces, copy.deepcopy(st0) if st0 else None, now, timers, soft, settled, analog=analog)
    goals = res.pop("_goals")
    user = res.pop("_user")
    if not res["unmet"]:
        return res
    idx = _index(s)
    unmet_goals = [("net", u["net"], u["want"]) for u in res["unmet"]]
    best, tried, seen = res, 0, set()
    for strict0 in (True, False):
        for leaves in _solutions(s, idx, unmet_goals, False, strict0, {"rows_only": False}, max_steps=CHOICE_STEPS):
            if tried >= CHOICE_TRIES:
                break
            if any(user.get(k, w) != w for k, w in leaves.items()):
                continue                               # 사람이 직접 준 값과 어긋나는 갈래
            if any("/" in k for k in leaves):
                continue                               # 펼친 매크로 안쪽(Typical 의 누름단추 · 행)은 부모 장에서 누를 수 없다
            key = tuple(sorted(leaves.items()))
            if key in seen:
                continue
            seen.add(key)
            tried += 1
            r = _simulate_once(s, forces, copy.deepcopy(st0) if st0 else None, now, timers, soft, settled, extra=leaves,
                               analog=analog)
            r.pop("_goals"), r.pop("_user")
            if len(r["unmet"]) < len(best["unmet"]):
                best = r
                best["choice"] = {k: v for k, v in leaves.items()}
            if not r["unmet"]:
                break
        if not best["unmet"]:
            break
    if best is not res:
        best["notes"] = sorted(set(best["notes"]) | {
            "정해지지 않는 게이트(OR · 메모리 · 투표 …)는 입력 갈래를 하나 골라 앞으로 돌려 확인했습니다"})
    return best


# L9 — 따라가기가 게이트를 지날지는 범례 정의가 정한다.  따라가는 신호를 1, 그 게이트의 다른
# 입력을 0 으로 보고 출력이 1 이 될 때만 뒤로 간다: OR·NAND 는 지나고 AND·NOR·NOT 은 멈춘다
# (AND 는 **모든** 입력이 따라온 선이어야 지난다 — 사용자 지시 *"AND gate 이면 모든 신호가 active
# 되어야 후단 output 이 active"*).  메모리·타이머·STEP·연결 기호·판정 못 한 블록은 연결만 본다.
def trace(s, start, direction="down"):
    """연결을 따라간다 — 넷에서 시작해 블록을 지나 다음 넷으로 (깊이 순서).

    start = "net:<id>" | "row:<n>" | "block:<id>".  연결 기호는 같은 묶음끼리 건너간다.
    L14 — 연결 따라가기는 **연결**만 본다: 게이트의 다른 입력이 활성이 아니어도 지나간다 (사용자 확정).
    게이트 조건을 지키는 것은 동작 시뮬레이션이다.  `blocked` 는 옛 화면과의 짝으로 언제나 빈 목록.
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
        nets0 = [r["net"] for r in s["rows"] if r["n"] == n and r.get("net") is not None]
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
            "blocks": [{"block": b, "depth": d} for b, d in sorted(seen_b.items(), key=lambda kv: kv[1])],
            "blocked": blocked}


# ------------------------------------------------------------------ 묶음 전체 (시트 사이)

MAX_PASSES = 12
from . import refs as _RF   # noqa: E402  (L21 · L23 일반 꼴)     # 시트-행 꼴 (시트 이름은 그 묶음에 있는지로 거른다)


def _row_values(s, values):
    """오른쪽(출력) 행마다 그 행 넷의 값."""
    return {r["n"]: values.get(r["net"], 0) for r in s["rows"] if r["side"] == "R" and r.get("net") is not None}


def simulate_bundle(sheets, forces=None, state=None, focus=None, timers=None, analog=None):
    """묶음의 모든 장을 함께 돌린다 — 한 장의 출력 행이 1 이면 그 행을 FM 으로 받는 다른 장의 입력 행도 1.

    연결은 도면이 적은 그대로다: 왼쪽 행의 FM `G034-71` (analyse._cross_refs 가 맞댄 `ref`).
    사람이 그 입력 행을 직접 0/1 로 준 것이 도면 연결보다 이긴다.  끝없는 되먹임은 MAX_PASSES 에서 멈추고 말한다.

    forces = {page: {key: 0|1}} · state = {page: 이전 state} · focus = 화면이 보는 장
    → {"focus": 그 장의 simulate 결과, "linked": {page: {row: 값}}, "pages": [...], "state": {page: st}, "notes"}
    """
    forces = {int(k): v for k, v in (forces or {}).items()}
    state = {int(k): v for k, v in (state or {}).items()}
    timers = {int(k): v for k, v in (timers or {}).items() if str(k).isdigit() and isinstance(v, dict)}
    analog = {int(k): v for k, v in (analog or {}).items() if str(k).isdigit() and isinstance(v, dict)}
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
              for sh, rn in _RF.find(text, wide=True, known=by_no):
                t = by_no.get(sh)
                if not t or not any(x["n"] == int(rn) and x["side"] == "L" for x in t["rows"]):
                    continue
                e = (int(rn), s["page"], owner)
                if e not in feeds[t["page"]]:
                    feeds[t["page"]].append(e)
    an_given = _analog_bundle(by_page, feeds, analog)
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
    macro_view = {}
    inline = {}                       # page → (매크로를 펼친 한 장, {bid: (m, 펼친 Typical)})

    # L15 — 매크로 블록을 펼친다: Typical 시트의 블록·선을 이 장 안에 이름을 붙여 넣고, Typical 입력 행의 선 =
    # 상자의 입력 단자 선 · Typical 출력 행의 선 = 상자의 출력 단자 선으로 잇는다.  한 장을 한 번에 돌리므로
    # **시간이 같이 흐른다** — Typical 안의 펄스(PD)·지연 타이머가 그 시간 동안 상자의 출력을 1 로 낸다.
    # (L12 는 Typical 을 따로 돌려 마지막 틀만 가져와, 펄스로 나가는 STOP · START 명령이 부모 장에 닿지 않았다.)
    def inlined(page):
        if page in inline:
            return inline[page]
        s0 = by_page[page]
        items = macros.get(page)
        if not items:
            inline[page] = (s0, {})
            return inline[page]
        boxes = {bid for bid, _ in items}
        blocks = {k: v for k, v in s0["blocks"].items() if k not in boxes}
        ports = [p for p in s0["ports"] if p["block"] not in boxes]
        nets = dict(s0.get("nets") or {})
        for bid, m in items:
            ts = by_page[m["page"]]
            alias = {}
            for x in m["inputs"]:
                tn = next((r["net"] for r in ts["rows"] if r["n"] == x.get("row") and r["side"] == "L"), None)
                if tn is not None and x.get("net") is not None:
                    alias[tn] = x["net"]
            for x in m["outputs"]:
                tn = next((r["net"] for r in ts["rows"] if r["n"] == x.get("row") and r["side"] == "R"), None)
                if tn is not None and x.get("net") is not None:
                    alias[tn] = x["net"]
            nm = lambda n, bid=bid, alias=alias: alias.get(n, f"{bid}/{n}")
            for k, v in ts["blocks"].items():
                nb = dict(v)
                if nb.get("group"):
                    nb["group"] = f"{bid}/{nb['group']}"
                blocks[f"{bid}/{k}"] = nb
            for p_ in ts["ports"]:
                ports.append({**p_, "block": f"{bid}/{p_['block']}", "net": nm(p_["net"])})
            for n in (ts.get("nets") or {}):
                nets.setdefault(nm(n), {"segs": []})
        s1 = {**s0, "blocks": blocks, "ports": ports, "nets": nets}
        inline[page] = (s1, dict(items))
        return inline[page]

    def strip(res):
        """펼친 Typical 의 선·블록은 화면의 장에 없다 — 결과에서 뺀다 (값은 상자 단자 선으로 이미 나왔다)."""
        own = lambda k: "/" not in str(k)
        for fr in res["frames"]:
            fr["values"] = {k: v for k, v in fr["values"].items() if own(k)}
            fr["depth"] = {k: v for k, v in fr["depth"].items() if own(k)}
            fr["unread"] = [k for k in fr["unread"] if own(k)]
            # 펼친 Typical 안에서 세는 타이머는 그 매크로 상자 위에서 센다 (남은 시간이 가장 긴 것)
            run = {}
            for x in fr.get("running", []):
                k = str(x["block"]).split("/", 1)[0]
                if k not in run or x["left"] > run[k]["left"]:
                    run[k] = {**x, "block": k}
            fr["running"] = list(run.values())
            if "fired" in fr:
                fr["fired"] = [b for b in fr["fired"] if own(b)]
        res["short_gates"] = [b for b in res["short_gates"] if own(b)]
        return res

    def macro_views(page, items, values):
        view = {}
        for bid, m in items.items():
            orow = {x["row"]: (1 if values.get(x["net"]) == 1 else 0) for x in m["outputs"] if x.get("row") is not None}
            # 짝 출력(이름 끝 1/0 — CMD1 ↔ CMD0 · 열림 ↔ 닫힘)이 함께 1 이면 모순이다 — 숨기지 않고 알린다
            conflict = []
            outs1 = [x for x in m["outputs"] if x.get("row") is not None and orow.get(x["row"]) == 1]
            for i_, a in enumerate(outs1):
                for b_ in outs1[i_ + 1:]:
                    pa, pb = _pin_skel(a.get("pin")), _pin_skel(b_.get("pin"))
                    if len(pa) >= 3 and pa[:-1] == pb[:-1] and {pa[-1], pb[-1]} == {"I", "O"}:
                        conflict.append(f"{a.get('pin')} 과 {b_.get('pin')} 이 함께 1 ({m.get('sheet')} {a['row']}행 · {b_['row']}행)")
            view[bid] = {"sheet": m.get("sheet"), "page": m["page"], "conflict": conflict,
                         "inputs": {str(x["row"]): (1 if values.get(x["net"]) == 1 else 0) for x in m["inputs"] if x.get("row")},
                         "outputs": {str(r): v for r, v in orow.items()}}
        return view

    todo = set(by_page)
    notes = set()
    chain = {}                        # L16 — 줄줄이 켜기가 보내는 시트에 준 목표 {page: {row:n: v}} (사람 값 아님)
    pulls = []
    for _ in range(MAX_PASSES):
        if not todo:
            break
        changed_out = set()
        redo = set()
        for page in sorted(todo):
            s = by_page[page]
            lin = inputs_of(page)
            s_run, items = inlined(page)
            user = forces.get(page, {})
            f = {k: v for k, v in chain.get(page, {}).items() if k not in user}
            f.update(user)                            # 사람이 준 값이 이긴다
            soft = {n: v for n, v in lin.items() if f"row:{n}" not in f}
            tm = dict(timers.get(page) or {})
            for bid, m in items.items():
                for k, v in (timers.get(m["page"]) or {}).items():
                    tm[f"{bid}/{k}"] = v
            asked = {n for n, sp, sr in feeds.get(page, ()) if f"row:{sr}" in chain.get(sp, {})}
            res = simulate(s_run, f, state.get(page), timers=tm, soft=soft, settled=asked, analog=an_given.get(page))
            # L16 — 줄줄이: 이 시트의 출력을 내려면 다른 시트에서 오는 입력이 1 이어야 하면, 그 입력을 보내는 시트의
            # 출력 행도 목표로 켠다 (그 시트에서 다시 거꾸로 맞추기 — 게이트가 막으면 거기서 머문다).
            for n, v in (res.get("pulled") or {}).items():
                for rn, sp, sr in feeds.get(page, ()):
                    if rn != n:
                        continue
                    k = f"row:{sr}"
                    if k in forces.get(sp, {}) or chain.get(sp, {}).get(k) == v:
                        continue
                    if k in chain.get(sp, {}):
                        notes.add(f"줄줄이 켜기에서 {by_page[sp].get('sheet_no')} {sr}행이 0 과 1 을 함께 요구받았습니다")
                        continue
                    chain.setdefault(sp, {})[k] = v
                    pulls.append({"page": page, "sheet_no": s.get("sheet_no"), "row": n, "value": v,
                                  "from_page": sp, "from_sheet": by_page[sp].get("sheet_no"), "from_row": sr})
                    redo.add(sp)
                    redo.add(page)
            if items:
                macro_view[page] = macro_views(page, items, res["frames"][-1]["values"])
                strip(res)
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
    for p in chain:
        hop.setdefault(p, 0)
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
        if on_in or user or chain.get(page):
            vals = results[page]["frames"][-1]["values"]
            pages.append({"page": page, "sheet_no": s.get("sheet_no"), "user": bool(user),
                          "hop": hop.get(page),
                          "linked_in": on_in, "on_out": on_out,
                          "on_nets": sum(1 for v in vals.values() if v == 1),
                          "from": sorted({(by_page[sp].get("sheet_no"), sr) for n, sp, sr in feeds.get(page, ())
                                          if n in on_in}),
                          "to": sorted({by_page[q].get("sheet_no") for q, fd in feeds.items()
                                        for _, sp, sr in fd if sp == page and sr in on_out}),
                          # L19 — 현황 팝업: 사람이 준 신호 · 줄줄이 켠 목표 · 들어온 입력 · 나간 출력을 글로
                          "forced": [_force_label(s, k, v) for k, v in sorted(user.items())],
                          "chained": [_force_label(s, k, v) for k, v in sorted(chain.get(page, {}).items())
                                      if k not in user],
                          "inputs": [_row_label(s, "L", n) for n in on_in],
                          "outputs": [_row_label(s, "R", n) for n in on_out]})
    # 사람이 준 신호가 닿은 장(hop)에서 이동하다 만난 것만 — 아무것도 안 줘도 1 인 선(입력 0 의 NOT 등)은 빼고
    design = [e for e in _design_errors(sheets, by_page, by_no, out_rows, results) if e["page"] in hop]
    for page, view in macro_view.items():
        for bid, v in view.items():
            for c in v.get("conflict") or []:
                design.insert(0, {"page": page, "sheet_no": by_page[page].get("sheet_no") or "", "row": 0, "at_row": 0,
                                  "to": v.get("sheet") or "", "target_sheet": v.get("sheet") or "", "target_row": 0,
                                  "target_page": v.get("page"), "desc": "매크로 블록", "kind": "error",
                                  "why": f"모순 — {c}.  Typical 시트를 읽은 결과가 범례 동작과 맞지 않습니다 (도면 읽기 확인)"})
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
            "chain_forces": {p: v for p, v in chain.items() if v},
            "analog_given": an_given,
            "pulled": pulls,
            "state": {p: r["state"] for p, r in results.items()},
            "notes": sorted(notes)}


def _analog_bundle(by_page, feeds, analog):
    """L26 — 아날로그 값도 시트 사이로 간다: 출력 행의 선이 값을 가지면 그 행을 받는 입력 행도 그 값
    (사람이 그 입력 행에 직접 준 값이 이긴다).  시간이 없는 값이라 가라앉을 때까지 몇 번 돌리면 된다.
    → {page: {"block:<id>"|"row:<n>": 값}}"""
    given = {p: dict(v) for p, v in analog.items() if p in by_page}
    # L27 — 사람이 아무것도 안 줘도 아날로그 입력은 기본 8 mA 라 감시 블록이 맞댈 값이 선다 → 시트 사이로도 간다
    idxs = {}
    src_pages = set(given)
    for p, s in by_page.items():
        if any(A.is_analog_block(b) or A.monitor_kind(b) for b in s["blocks"].values()):
            idxs[p] = _index(s)
            src_pages.add(p)
    if not src_pages:
        return given
    for _ in range(MAX_PASSES):
        moved = False
        memo = {}
        for page, fd in feeds.items():
            for n, sp, sr in fd:
                if sp not in src_pages:
                    continue
                s = by_page[sp]
                src = next((r for r in s["rows"] if r["side"] == "R" and r["n"] == sr and r.get("net") is not None), None)
                if src is None:
                    continue
                if sp not in memo:
                    memo[sp] = A.nets(s, given.get(sp), idxs.get(sp) or _index(s))[0]
                v = memo[sp].get(src["net"])
                k = f"row:{n}"
                user = analog.get(page, {})
                if v is None or k in user or given.get(page, {}).get(k) == {"eng": v}:
                    continue
                given.setdefault(page, {})[k] = {"eng": v}
                src_pages.add(page)
                moved = True
        if not moved:
            break
    return given


def _row_label(s, side, n):
    """행 하나를 사람 말로 — 설명 · FM/TO 글자 (표에서 읽은 그대로 · 설명 없는 행은 위로 처음 설명이 있는 행)."""
    rows = [x for x in (s.get("table") or s["rows"]) if x["side"] == side]
    r = next((x for x in rows if x["n"] == n), None) or next((x for x in s["rows"] if x["side"] == side and x["n"] == n), {})
    desc = (r.get("desc") or "").strip()
    if not desc:
        for x in sorted(rows, key=lambda x: -x["n"]):
            if x["n"] < n and (x.get("desc") or "").strip():
                desc = x["desc"].strip()
                break
    return {"row": n, "side": side, "desc": desc,
            "ref": (r.get("fm") if side == "L" else r.get("to")) or ""}


def _force_label(s, key, value):
    """사람이 준 강제 하나를 사람 말로 — row:n 은 그 행 · net 은 그 선을 모는 블록 · block 은 그 블록."""
    kind, _, k = str(key).partition(":")
    o = {"key": key, "value": value, "kind": kind}
    if kind == "row" and k.isdigit():
        n = int(k)
        side = "R" if any(x["side"] == "R" and x["n"] == n for x in s["rows"]) and \
            not any(x["side"] == "L" and x["n"] == n for x in s["rows"]) else "L"
        o.update(_row_label(s, side, n))
    elif kind == "block":
        b = s["blocks"].get(k) or {}
        o.update({"block": k, "func": b.get("func") or "", "label": b.get("label") or ""})
    elif kind == "net":
        drv = next((p["block"] for p in s["ports"] if p.get("net") == k and p.get("dir") == "out"), None)
        b = s["blocks"].get(drv) or {}
        o.update({"net": k, "block": drv, "func": b.get("func") or "", "label": b.get("label") or ""})
    return o


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


def _pin_skel(t):
    return re.sub(r"[^A-Z0-9]", "", (t or "").upper()).replace("0", "O").replace("1", "I")


def _norm_desc(t):
    return re.sub(r"[^A-Z0-9]", "", (t or "").upper())


def _design_errors(sheets, by_page, by_no, out_rows, results=None):
    """**활성(1)인 신호**가 TO · FM 을 따라 이동하는 자리에서 도면끼리 어긋난 곳 (사용자 지시 L11).

    보내는 쪽: 1 인 출력 행(주인 행)과 그 아래로 이어지는 TO 줄들의 TO 마다 —
      ① TO 의 시트가 이 묶음에 없다  ② 그 시트에 그 행 입력이 없다  ③ 그 행이 비어 있다(설명·FM 없음)
      ④ 그 행의 FM 이 이 신호를 가리키지 않는다(다른 곳 · 없음)  → 설계 오류.
      설명만 다르면 '확인' (연결은 맞다 · L5 와 같은 구분).  시트 이름 머리글이 이 묶음과 다르면(Loop `P…` 등) 다른 묶음 —
      여기서 확인할 수 없다고만 말한다.
    받는 쪽: FM 으로 1 을 받은 입력 행 — 보내는 행의 TO 목록에 이 장-행이 없으면(TO 가 다른 곳만 적음) 설계 오류.
    판정은 읽은 글자 그대로이고(fromto 와 같은 규칙) 고치지 않는다.
    """
    bundle = _RF.Bundle(by_no)
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
                for sh, rn in _RF.find(text, wide=True, known=by_no):
                    rn = int(rn)
                    base = {"page": page, "sheet_no": me, "row": owner, "at_row": at, "to": f"{sh}-{rn}",
                            "target_sheet": sh, "target_row": rn, "desc": od}
                    if bundle.other(sh):
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
                    back = [(a, int(b)) for a, b in _RF.find(fm, wide=True, known=by_no)]
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
                   for a, b in _RF.find(text, wide=True, known=by_no) if bundle.mine(a)]
            if tos and (me, r["n"]) not in tos:
                src = by_page[sp].get("sheet_no") or ""
                add({"page": sp, "sheet_no": src, "row": own, "at_row": own, "to": f"{me}-{r['n']}",
                     "target_sheet": me, "target_row": r["n"], "target_page": page, "desc": r.get("desc") or "",
                     "kind": "error",
                     "why": f"{me}-{r['n']} 의 FM 은 {r.get('fm')} 인데 {src}-{own} 의 TO 는 "
                            f"{', '.join(f'{a}-{b}' for a, b in tos)} 만 적습니다 (잘못 연결)"})
    # 1 이 된 입력 행 — 그 행의 FM 이 from-to 대조(L5)에서 일치하지 않으면 (사람이 직접 준 입력 포함, 사용자 규칙 2)
    for s in sheets:
        res = (results or {}).get(s["page"])
        if not res:
            continue
        vals = res["frames"][-1]["values"]
        me = s.get("sheet_no") or ""
        for r in s["rows"]:
            ft = r.get("ft") or {}
            if r["side"] != "L" or ft.get("ok") is not False or vals.get(r["net"]) != 1:
                continue
            add({"page": s["page"], "sheet_no": me, "row": r["n"], "at_row": r["n"], "to": r.get("fm") or "",
                 "target_sheet": me, "target_row": r["n"], "target_page": s["page"], "desc": r.get("desc") or "",
                 "kind": "error", "side": "L",
                 "why": f"입력 {me}-{r['n']} 의 FM {r.get('fm') or ''} — " + " · ".join(ft.get("why") or ["일치하지 않습니다"])})
    order = {"error": 0, "warn": 1, "other": 2}
    out.sort(key=lambda e: (order[e["kind"]], e["sheet_no"], e["row"], e["to"]))
    return out



# ------------------------------------------------------------------ 출력까지 예시 (L14)
#
# 사용자 지시 — *"동작 시뮬레이션은 input 과 최종 output 까지 모든 신호 활성화"*.  사람이 고른 출력(오른쪽 행 · 선)이 1 이
# 되려면 왼쪽 입력 행 · 누름단추를 어떻게 줘야 하는지 범례 G003 정의를 거꾸로 풀어 **한 조합**을 찾고, 그 조합만 넣어
# (출력은 강제하지 않고) 앞으로 돌려 정말 그 출력이 서는지 확인한다.  거꾸로 풀기는 정해지지 않는 자리에서 갈래를 고른다
# (OR=1 이면 입력 하나 · AND=0 이면 입력 하나 · 메모리 Q=1 이면 SET 하나 + RESET 모두 0) — 고른 조합이 앞으로 돌려서
# 서지 않으면 다음 갈래로 (되먹임 래치에서 "Q 가 이미 1 이니까" 같은 순환 갈래가 그렇게 걸러진다).
# 도면에서 못 읽은 선(몰이 없음)은 먼저 피하고, 그것밖에 없으면 그 선을 직접 주는 조합을 내고 그렇다고 말한다.

def _back_options(s, idx, goal, allow_net, ctx=None):
    ins, outs, drivers, sinks, groups = idx
    ctx = ctx or {}
    B = s["blocks"]
    kind = goal[0]
    if kind == "net":
        _, net, v = goal
        drv = drivers.get(net, [])
        if not drv:
            return [({f"net:{net}": v}, [])] if (allow_net or v == 0) else []
        if len(drv) == 1:
            return [({}, [("drv", drv[0], v, net)])]
        if v == 1:
            return [({}, [("drv", d, 1, net)]) for d in drv]
        return [({}, [("drv", d, 0, net) for d in drv])]
    _, (dk, x, role), v, onet = goal
    if dk == "row":
        ok_rows = ctx.get("rows_allowed")
        if v == 1 and ok_rows is not None and x not in ok_rows:
            return []                                  # 매크로 상자에서 몰 수 없는 Typical 행 (단자를 못 읽었다)
        return [({f"row:{x}": v}, [])]
    b = B[x]
    lg = b.get("logic")
    iv = [n for n, _, _ in ins[x]]
    one = lambda nets, val: [({}, [("net", n, val)]) for n in nets]
    allg = lambda nets, val: [({}, [("net", n, val) for n in nets])]
    short = len(iv) < MIN_INPUTS.get(lg, 0)
    if lg == "source":
        if v == 1 and not ins[x] and re.sub(r"[^0-9A-Z]", "", (b.get("label") or "").upper()) == "1":
            return [({}, [])]                          # ACTIVATION — 언제나 1
        if ctx.get("rows_only") and v == 1:
            return []                                  # 매크로 안 Typical 시트 — 상자 입력 단자(행)로만 몬다
        return [({f"block:{x}": v}, [])]
    if b.get("func") == "MACRO":
        # L12 매크로 — 그 출력 단자의 Typical 행이 1 이 되는 Typical 입력 행 조합을 찾아 상자의 입력 단자 선으로 옮긴다
        m = b.get("macro") or {}
        ts = (ctx.get("by_page") or {}).get(m.get("page"))
        if v == 0:
            return [({}, [])]
        out = next((o for o in m.get("outputs", []) if o.get("net") == onet and o.get("row") is not None), None)
        if ts is None or out is None:
            return []
        by_row = {x["row"]: x["net"] for x in m.get("inputs", []) if x.get("row")}
        key = (m["page"], out["row"], tuple(sorted(by_row)))
        cache = ctx.setdefault("macro_cache", {})
        if key not in cache:
            cache[key] = scenario(ts, f"row:{out['row']}", 1, rows_only=True, rows_allowed=set(by_row))
        sc = cache[key]
        if not sc.get("ok") or any(sc["forces"].get(k) == 1 for k in sc.get("direct_nets") or ()):
            return []
        goals, held = [], {}
        for k, w in sc["forces"].items():
            if k.startswith("net:"):
                # L15 — Typical 안에서 몰이를 못 읽어 0 으로 붙든 선: 펼친 장의 그 선(블록 이름/선)을 0 으로 둔다
                held[f"net:{x}/{k[4:]}"] = 0
                continue
            if not k.startswith("row:") or w != 1:
                continue
            n_ = by_row.get(int(k[4:]))
            if n_ is None:
                return []                              # 그 Typical 입력 행에 닿는 단자를 못 읽었다
            goals.append(("net", n_, 1))
        return [(held, goals)]
    if lg in ("and", "nand"):
        want_all = (v == 1) == (lg == "and")         # AND=1 · NAND=0 → 모든 입력 1
        if want_all:
            return [] if short else allg(iv, 1)
        return one(iv, 0) or [({}, [])]
    if lg in ("or", "nor"):
        want_one = (v == 1) == (lg == "or")          # OR=1 · NOR=0 → 입력 하나가 1
        if want_one:
            return one(iv, 1)
        return ([] if (short and v == 1) else allg(iv, 0)) if iv else ([({}, [])] if v == 0 else [])
    if lg == "not":
        if not iv:
            return [({}, [])] if v == 0 else []      # 입력이 안 읽힌 NOT 은 1 을 내지 않는다 (0 으로 보인다)
        return [({}, [("net", iv[0], 1 - v)])]
    vote = _vote_of(b)
    if vote:
        a, n = vote
        if v == 0:
            return allg(iv, 0)
        if len(iv) < a:
            return []
        from itertools import combinations
        return [({}, [("net", m, 1) for m in c]) for c in list(combinations(iv, a))[:6]]
    if lg == "memory":
        want = v if role != "qn" else 1 - v
        S = [n for n, r, _ in ins[x] if r == "set"]
        R = [n for n, r, _ in ins[x] if r == "reset"]
        if want == 1:
            return [({}, [("net", n, 1)] + [("net", r, 0) for r in R]) for n in S]
        # Q=0 — SET 이 모두 0 이면 (한 번도 SET 안 된 상태에서) 0 이다.  이미 SET 된 래치는 RESET 하나가 1 이어야 한다
        # (SET 우선이면 SET 도 모두 0 이어야 한다 — 그래서 어느 갈래든 SET 은 0).
        return [({}, [("net", n, 0) for n in S])] + [({}, [("net", r, 1)] + [("net", n, 0) for n in S]) for r in R]
    if lg in ("delay_on", "delay_off", "pulse"):
        return one(iv, 1) if v == 1 else allg(iv, 0)
    if lg == "step":
        si = [n for n, r, _ in ins[x] if r == "step_in"]
        cr = [n for n, r, _ in ins[x] if r == "crit"]
        if v == 0:
            return allg(si, 0)
        if role == "step_out":
            return [({}, [("net", a, 1), ("net", c, 1)]) for a in si for c in cr]
        return one(si, 1)
    if lg == "connector":
        g = groups.get(b.get("group") or x, [x])
        gin = [n for gid in g for n, _, _ in ins[gid]]
        if not gin:
            return [({f"block:{x}": v}, [])]
        return one(gin, 1) if v == 1 else allg(gin, 0)
    return [({}, [])] if v == 0 else []            # 판정 못 한 블록 · 매크로 — 1 을 낼 수 없다


def _inverting(s, idx, net):
    """그 선을 모는 블록이 0 을 내려면 입력이 1 이어야 하는가 (NOT · NOR · NAND · 메모리 Q̄)."""
    for dk, x, role in idx[2].get(net, []):
        if dk == "block":
            lg = s["blocks"][x].get("logic")
            if lg in ("not", "nor", "nand") or (lg == "memory" and role == "qn"):
                return True
    return False


def _solutions(s, idx, goals, allow_net, strict0=False, ctx=None, max_steps=None):
    """깊이 우선 — (leaves, required nets) 를 하나씩 낸다."""
    stack = [(list(goals), {}, {})]
    steps = 0
    while stack:
        steps += 1
        if max_steps and steps > max_steps:
            return
        todo, leaves, req = stack.pop()
        if not todo:
            yield leaves
            continue
        g, rest = todo[0], todo[1:]
        if g[0] == "net" and g[2] == 0 and not strict0 and not _inverting(s, idx, g[1]):
            # 0 은 아무것도 주지 않으면 대개 그대로 0 이다 — 거꾸로 따라가지 않는다 (되먹임 래치에서 Q=1 과 R=0 이
            # 서로를 요구하는 순환을 만들지 않으려고).  맞는지는 앞으로 돌려서 확인한다 (_reached).
            stack.append((rest, leaves, req))
            continue
        if g[0] == "net":
            if g[1] in req:
                if req[g[1]] == g[2]:
                    stack.append((rest, leaves, req))
                continue
            req = {**req, g[1]: g[2]}
        alts = _back_options(s, idx, g, allow_net, ctx)
        branch = []
        for add, sub in alts:
            ok = all(leaves.get(k, w) == w for k, w in add.items())
            if ok:
                branch.append((sub + rest, {**leaves, **add}, req))
        stack.extend(reversed(branch))               # 앞 갈래를 먼저 본다


def _reached(s, forces, net, value, sheets=None):
    """그 조합만 넣고 앞으로 돌려 그 선이 value 가 되는 틀이 있는가 (펄스처럼 잠깐 서는 것도 선 것이다).
    매크로 블록이 있는 장은 묶음째 돌린다 (매크로 출력은 Typical 시트가 낸다)."""
    if sheets:
        # 화면과 같은 길 — 묶음째 돌린다 (다른 장에서 연결로 들어오는 입력 · 매크로 출력이 화면과 같다)
        r = simulate_bundle(sheets, {s["page"]: forces}, focus=s["page"])["focus"]
    else:
        r = simulate(s, forces)
    hit = [fr["t"] for fr in r["frames"] if fr["values"].get(net) == value]
    return r, hit


def scenario(s, target, value=1, limit=160, sheets=None, rows_only=False, rows_allowed=None):
    """target = "row:<n>"(오른쪽 행) | "net:<id>".  → {"ok", "forces", "net", "frames", "why", "direct_nets"}"""
    if target.startswith("row:"):
        n = int(target[4:])
        net = next((r.get("net") for r in s["rows"] if r["n"] == n and r["side"] == "R"), None)
        if net is None:
            return {"ok": False, "why": f"{n}행에 읽힌 선이 없습니다", "forces": {}}
    else:
        net = target[4:]
    idx = _index(s)
    ctx = {"rows_only": rows_only, "rows_allowed": rows_allowed, "by_page": {x["page"]: x for x in (sheets or [])}}
    tried = 0
    seen = set()
    pulse = None
    for allow_net, strict0 in ((False, True), (False, False), (True, True), (True, False)):
        n_pass = 0
        for leaves in _solutions(s, idx, [("net", net, value)], allow_net, strict0, ctx):
            n_pass += 1
            if n_pass > limit // 4:
                break
            key = tuple(sorted(leaves.items()))
            if key in seen:
                continue
            seen.add(key)
            tried += 1
            forces = {k: w for k, w in leaves.items() if not (w == 0 and not k.startswith("net:"))}
            r, hit = _reached(s, forces, net, value, sheets)
            if hit:
                direct = sorted(k for k in forces if k.startswith("net:"))
                ans = {"ok": True, "net": net, "forces": forces, "at": hit[0],
                       "direct_nets": direct, "tried": tried, "frames": len(r["frames"]),
                       "notes": r["notes"], "short_gates": r["short_gates"],
                       "steady": r["frames"][-1]["values"].get(net) == value}
                if ans["steady"]:
                    return ans                        # 마지막 틀까지 서 있다 — 입력부터 최종 출력까지 켜진 채
                pulse = pulse or ans                  # 잠깐 서는 것(펄스) — 더 나은 조합이 없을 때만
    if pulse:
        pulse["notes"] = pulse["notes"] + ["이 출력은 펄스로 잠깐 섰다가 꺼집니다 (도면의 PD · 되먹임)"]
        return pulse
    why = ("이 출력까지 가는 입력 조합을 범례 정의로 찾지 못했습니다 — 몰이를 못 읽은 선 · 판정 못 한 블록 · "
           "입력을 다 읽지 못한 게이트가 길에 있습니다") if tried == 0 else \
          f"조합 {tried}개를 앞으로 돌려 봤지만 출력이 서지 않았습니다 (되먹임 · 타이머 · 도면 읽기 확인)"
    return {"ok": False, "net": net, "forces": {}, "why": why, "tried": tried}
