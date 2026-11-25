"""L95 — 매크로 안쪽(Typical 시트)의 **논리 연산자 하나하나**가 신호에 따라 범례 정의대로 답하는지 채점한다.

시뮬레이터(`sim.py`)의 게이트 함수를 쓰지 않고, 범례(19VA 15쪽) 글을 그대로 옮긴 **따로 만든 채점기**로 틀(frame)마다 맞대 본다:
  AND   OUTPUT EXISTS ONLY WHEN ALL INPUTS ARE PRESENT            OR    … WHEN ONE OR MORE INPUTS ARE PRESENT
  NOT   OUTPUT EXISTS ONLY WHEN INPUT IS NOT PRESENT              자격 OR  참인 입력 수를 n 과 맞댄다 (≥ · > …)
  ON    … INPUT HAS BEEN CONTINUOUSLY PRESENT FOR A PRESET TIME    OFF   … INPUT IS PRESENT AND FOR A PRESET TIME AFTER THE INPUT IS NOT PRESENT
  ⎍     OUTPUT EXISTS FOR TIME T WHEN INPUT TRANSIT FROM LOW TO HIGH
  메모리  SET 이 있으면 서고 RESET 이 있을 때까지 이어진다 · S 또는 R 를 두른 원 = 둘 다 있을 때의 출력
  이음 기호 · 넘김  들어오는 선의 OR

신호 주기: 아무것도 안 줌 · 입력 하나씩 1 · 모두 1 · 모두 1 에서 하나씩 0 · 무작위 순서(상태를 이어 준다) · 입력 하나씩 바꾸며 걷기 ·
새것을 보여 주는 입력을 골라 걷기 · 시간을 멈춘 채 걷기(타이머가 세는 도중에 입력을 바꾼다 — sim 의 horizon) · 풀이가 찾은 조합에서 하나씩 뒤집기 ·
연산자마다 입력 선을 직접 겨눈 조합(모두 1 · 하나씩 0 · 모두 0 · 하나씩 1 · 메모리는 SET→놓기→RESET→놓기→둘 다).
틀마다 그 **한 순간 안의 중간 값**(sim.MICRO)까지 채점한다 — 타이머가 끝나며 제 입력을 끄는 식의 순간 변화가 보인다.
채점은 **틀에 실제로 선 값**으로 한다 (겨눈 값이 아니라) — 그래서 겨눔이 막혀도 틀린 채점이 나오지 않는다.

연산자마다 남기는 것: 채점 횟수 · 어긋남 · 본 것 (게이트: 입력 하나가 혼자 출력을 바꾸는 것을 본 입력 수 · 메모리: 서기/지우기/이어감/둘 다 ·
타이머: 시간 세기 시작 / 시간 뒤 바뀜).  그림: 원본 쪽 위에 연산자 상자를 칠한다 (초록 = 다 봄 · 연두 = 일부만 봄 · 빨강 = 어긋남 · 회색 = 못 켬).
읽기만 한다 (분석 폴더에 쓰지 않는다).

  PID_DATA_DIR=<데이터> python3 spike/macro_operator_check_l95.py <job> <out 폴더> [시트 이름,…]
"""
from __future__ import annotations

import collections
import itertools
import json
import random
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "spike"))
from app.logic import api, sim, store  # noqa: E402

RANDOM_RUNS = 120
GUIDED_STEPS = 40          # 새것을 보여 주는 입력을 골라 걷는 걸음 수 (세 번 · 걸음마다 입력 수만큼 돌려 본다)
TIMED_STEPS = 50           # 시간을 멈춘 채 걷는 걸음 수 (타이머가 있는 장만 · 세 번)
WALKS, WALK_STEPS = 24, 30   # 한 번에 입력 하나만 바꾸는 걸음 (장마다)
GATES = ("and", "or", "nand", "nor", "not")
TIMERS = ("delay_on", "delay_off", "pulse")
EPS = 1e-6
COL = {"full": (0.0, 0.62, 0.25), "part": (0.55, 0.78, 0.1), "bad": (0.9, 0.1, 0.1), "none": (0.55, 0.55, 0.55)}
CMP = {"ge": lambda k, n: k >= n, "gt": lambda k, n: k > n, "le": lambda k, n: k <= n, "lt": lambda k, n: k < n,
       "eq": lambda k, n: k == n, "ne": lambda k, n: k != n}


def ref_gate(lg, iv, vote=None, op="ge"):
    """범례 글 그대로.  iv 에 모르는 값(None)이 있으면 채점하지 않는다 (None)."""
    if any(v not in (0, 1) for v in iv):
        return None
    if vote:
        return 1 if CMP[op](sum(iv), vote[0]) else 0
    if lg == "and":
        return 1 if iv and all(iv) else 0
    if lg == "or":
        return 1 if any(iv) else 0
    if lg == "nand":
        return 0 if iv and all(iv) else 1
    if lg == "nor":
        return 0 if any(iv) else 1
    if lg == "not":
        return 0 if any(iv) else 1
    return None


STATEFUL = TIMERS + ("memory", "toggle")


def _stateful_upstream(s, nets, ins, drivers, target=None):
    """이 선들의 앞쪽에 기억 · 시간 소자(메모리 · 타이머 · 토글)가 있는가 — 있으면 **한 순간 안에서** 값이 섰다 꺼질 수 있다
    (타이머가 끝나며 메모리를 지우고, 지워진 메모리가 타이머 입력을 끄는 식).  틀은 그 순간의 끝 값만 보여 준다."""
    seen, todo = set(), list(nets)
    while todo:
        n = todo.pop()
        if n in seen:
            continue
        seen.add(n)
        if target is not None and n in target:
            return True                                # target 을 주면: 그 선이 앞쪽에 있는가 (기억 · 시간 소자를 지나서도 따라간다)
        for kind, x, _ in drivers.get(n, []):
            if kind != "block":
                continue
            b = s["blocks"][x]
            if target is None and b.get("logic") in STATEFUL:
                return True
            members = [x]
            if b.get("logic") == "connector":
                members = [m for m, bb in s["blocks"].items() if bb.get("group") and bb.get("group") == b.get("group")] or [x]
            for m in members:
                todo.extend(n2 for n2, _, _ in ins.get(m, []))
    return False


class Op:
    """연산자 하나의 채점 장부."""

    def __init__(self, s, bid, b, ins, outs, drivers):
        self.bid, self.b = bid, b
        self.vote = sim._vote_of(b)
        self.kind = "vote" if self.vote else b.get("logic")
        self.op = (b.get("param") or {}).get("op") or "ge"
        self.ins = [(n, r) for n, r, _ in ins[bid]]
        self.outs = [(n, r) for n, r, _ in outs[bid] if len(drivers.get(n, [])) == 1]       # 다른 블록과 함께 모는 선은 이 블록의 답이 아니다
        self.need = self.vote[1] if self.vote else (sim.min_inputs(b, self.kind) if self.kind in sim.MIN_INPUTS else 0)
        self.checks = 0
        self.bad = []
        self.seen = collections.Counter()            # 본 일 (갈래 → 횟수)
        self.tuples = set()                          # 게이트: (입력 값들, 출력)
        self.q = 0                                   # 메모리: 지난 틀의 Q
        self.tm = None                               # 타이머: 채점기의 기억 {"inp", "rise", "fall", "was1"}
        self.T = sim.timer_seconds(b) if self.kind in TIMERS else None
        self.glitch = _stateful_upstream(s, [n for n, _ in self.ins], ins, drivers)
        # 제 출력이 제 입력으로 되돌아오는가 (자기유지 고리 · 고장 래치) — 그런 게이트는 '입력 하나만 다른 두 상태' 가 구조상 안 생기는 칸이 있다
        self.selfloop = _stateful_upstream(s, [n for n, _ in self.ins], ins, drivers, {n for n, _, _ in outs[bid]})

    def reset(self):
        self.q = 0
        self.tm = None

    # ── 틀 하나 채점 ─────────────────────────────────────────────────────────────────────────────────
    def check(self, fr, unread, micro=False):
        v = fr["values"]
        if not self.outs or any(n in unread for n, _ in self.outs):
            return
        k = self.kind
        if k in GATES or k == "vote":
            iv = [v.get(n) for n, _ in self.ins]
            iv_f = iv + [0] * max(0, self.need - len(iv))                       # L46 — 연결 안 된 칸은 비활성(0)
            want = ref_gate(k, iv_f, self.vote, self.op)
            for on, _ in self.outs:
                got = v.get(on)
                if want is None or got not in (0, 1):
                    continue
                self.checks += 1
                self.tuples.add((tuple(iv), got))
                if got != want:
                    self._bad(fr, f"입력 {iv} → 출력 {got} (범례대로면 {want})")
        elif k == "memory":
            S = [v.get(n) for n, r in self.ins if r == "set"]
            R = [v.get(n) for n, r in self.ins if r == "reset"]
            if any(x not in (0, 1) for x in S + R):
                return
            s_, r_ = int(any(S)), int(any(R))
            dom = (self.b.get("param") or {}).get("dominant") or ""
            for on, role in self.outs:
                got = v.get(on)
                if got not in (0, 1) or role not in ("q", "qn"):
                    continue
                q = got if role == "q" else 1 - got
                self.checks += 1
                if s_ and not r_:
                    self.seen["set"] += 1
                    if q != 1:
                        self._bad(fr, f"SET 만 1 인데 출력 {q}")
                elif r_ and not s_:
                    self.seen["reset"] += 1
                    if q != 0:
                        self._bad(fr, f"RESET 만 1 인데 출력 {q}")
                elif s_ and r_:
                    self.seen["both"] += 1
                    if dom and q != (1 if dom == "set" else 0):
                        self._bad(fr, f"S · R 함께 1 · {dom.upper()} 우선인데 출력 {q}")
                    if not dom:
                        self.seen["both_nodom"] += 1
                else:
                    self.seen["hold1" if q else "hold0"] += 1
                    if q != self.q:
                        # 한 순간 안에서 SET(또는 RESET)이 섰다 꺼진 것 — 앞쪽에 기억 · 시간 소자가 있을 때만 있을 수 있다
                        self.seen["hold_changed"] += 1
                        if not self.glitch:
                            self._bad(fr, f"S · R 둘 다 0 인데 출력이 {self.q} → {q} 로 바뀜 (앞쪽에 기억 · 시간 소자 없음)")
                if role == "q":
                    self.q = q
        elif k in TIMERS:
            inp = [v.get(n) for n, r in self.ins if r not in ("t", "reset")]
            rst = [v.get(n) for n, r in self.ins if r == "reset"]
            if any(x not in (0, 1) for x in inp + rst):
                return
            i_, t = int(any(inp)), fr["t"]
            tm = self.tm or {"inp": 0, "rise": None, "fall": None}
            if any(rst):
                tm = {"inp": i_, "rise": None, "fall": None}
                want = 0
            else:
                if i_ and not tm["inp"]:
                    tm["rise"] = t
                    self.seen["start"] += 1
                if not i_ and tm["inp"]:
                    tm["fall"] = t
                    if k == "delay_on":
                        tm["rise"] = None
                tm["inp"] = i_
                if k == "delay_on":
                    want = 1 if i_ and tm["rise"] is not None and t - tm["rise"] >= self.T - EPS else 0
                elif k == "delay_off":
                    want = 1 if i_ or (tm["fall"] is not None and t - tm["fall"] < self.T - EPS) else 0
                else:
                    want = 1 if tm["rise"] is not None and t - tm["rise"] < self.T - EPS else 0
            self.tm = tm
            if micro:
                for on, _ in self.outs:                  # 끝나자마자 제 입력을 끄는 타이머는 출력 1 이 순간 안에서만 보인다 — 본 것으로는 센다
                    if v.get(on) in (0, 1):
                        self.seen[f"out{v.get(on)}"] += 1
                return                                   # 순간 안의 중간 값 — 타이머 출력은 그 순간이 끝나야 정해진다.  입력이 언제 섰고 꺼졌는지만 적어 둔다
            restarted = any(x["block"] == self.bid and abs(x["left"] - self.T) < 1e-3 for x in fr.get("running") or ())
            for on, _ in self.outs:
                got = v.get(on)
                if got not in (0, 1):
                    continue
                self.checks += 1
                self.seen[f"out{got}"] += 1
                if bid_fired(fr, self.bid):
                    self.seen["fired"] += 1
                if got != want and self.glitch and restarted and not any(rst) and \
                        ((k == "pulse" and got == 1) or (k == "delay_on" and got == 0 and i_) or (k == "delay_off" and got == 1 and not i_)):
                    # 이 순간 안에서 입력이 섰다 꺼졌다(또는 꺼졌다 섰다) — 시간을 이 순간부터 다시 센다.  그 뒤 틀은 이 시각으로 다시 채점한다
                    self.seen["instant_edge"] += 1
                    tm["fall" if k == "delay_off" else "rise"] = t
                    continue
                if got != want:
                    self._bad(fr, f"입력 {i_} · t={t:g} · T={self.T:g} → 출력 {got} (범례대로면 {want})")
        elif k in ("pass", "connector_out"):
            iv = [v.get(n) for n, _ in self.ins]
            if not iv or any(x not in (0, 1) for x in iv):
                return
            for on, _ in self.outs:
                got = v.get(on)
                if got in (0, 1):
                    self.checks += 1
                    self.tuples.add((tuple(iv), got))
                    if got != int(any(iv)):
                        self._bad(fr, f"입력 {iv} → 출력 {got} (그대로 넘김이면 {int(any(iv))})")

    def _bad(self, fr, msg):
        if len(self.bad) < 5:
            self.bad.append({"t": fr["t"], "msg": msg})
        self.seen["bad"] += 1

    # ── 얼마나 봤나 ──────────────────────────────────────────────────────────────────────────────────
    def coverage(self):
        """→ (본 것, 볼 것, 글)."""
        k = self.kind
        if k in GATES or k == "vote" or k == "pass":
            n = len(self.ins)
            nets = [x for x, _ in self.ins]
            solo = set()
            by = collections.defaultdict(set)
            for iv, o in self.tuples:
                by[iv].add(o)
            keys = list(by)
            for a, b in itertools.combinations(keys, 2):
                d = [i for i in range(n) if a[i] != b[i]]
                # 같은 선이 두 칸에 물린 입력은 함께 움직인다 — 한 선으로 센다
                if d and len({nets[i] for i in d}) == 1 and by[a] != by[b]:
                    solo.update(d)
            return len(solo), n, f"입력 {n}개 중 {len(solo)}개가 혼자 출력을 바꾸는 것을 봄"
        if k == "memory":
            need = ["set", "reset", "hold1", "hold0", "both"]
            got = [x for x in need if self.seen[x]]
            return len(got), len(need), "봄: " + " · ".join(got)
        if k in TIMERS:
            need = ["start", "out1", "out0", "fired"]
            got = [x for x in need if self.seen[x]]
            return len(got), len(need), "봄: " + " · ".join(got)
        return 0, 0, ""


def bid_fired(fr, bid):
    return bid in (fr.get("fired") or ())


def operators(s):
    ins, outs, drivers, sinks, groups = sim._index(s)
    ops = {}
    for bid, b in s["blocks"].items():
        lg = b.get("logic")
        if lg in GATES or lg in TIMERS or lg in ("memory", "pass") or sim._vote_of(b):
            ops[bid] = Op(s, bid, b, ins, outs, drivers)
    return ops, (ins, outs, drivers, sinks, groups)


def check_sheet(s, sheets, cache):
    ops, (ins, outs, drivers, sinks, groups) = operators(s)
    rows_in = [r["n"] for r in s["rows"] if r["side"] == "L" and r.get("net") is not None]
    srcs = [bid for bid, b in s["blocks"].items() if b.get("logic") == "source" and (not ins.get(bid) or b.get("func") == "SIGNAL MONITOR")]
    keys = [f"row:{n}" for n in dict.fromkeys(rows_in)] + [f"block:{b}" for b in srcs]
    stat = collections.Counter()

    def sim_step(f, st, hz=None):
        stat["runs"] += 1
        try:
            rr = sim.simulate_bundle(sheets, {s["page"]: f} if f else {}, st, s["page"], cache=cache, light=True, horizon=hz)
        except Exception as e:                             # noqa: BLE001
            stat["errors"] += 1
            stat[f"err:{type(e).__name__}"] += 1
            return None, None
        return rr.get("state"), rr["focus"]["frames"]

    def grade(frames):
        for fr in frames:
            stat["frames"] += 1
            unread = set(fr.get("unread") or ())
            # 한 순간 안의 중간 값들 → 끝 값 순서로 채점 (sim.MICRO — 타이머가 본 그대로의 입력 변화가 보인다)
            for mv in fr.get("micro") or ():
                stat["micro"] += 1
                mf = {"t": fr["t"], "values": mv, "running": (), "fired": ()}
                for o in ops.values():
                    o.check(mf, unread, micro=True)
            for o in ops.values():
                o.check(fr, unread)

    def run(seq):
        """걸음들을 상태를 이어 가며 돌리고 틀마다 채점."""
        for o in ops.values():
            o.reset()
        st = None
        for f in seq:
            st, frames = sim_step(f, st)
            if frames is None:
                return
            grade(frames)

    sigs = set()

    def sig_of(frames):
        """이 틀들이 보여 준 것 — (연산자, 입력 값들, 출력 값들).  새것이 많은 걸음을 고르려고 쓴다 (채점과는 따로)."""
        out = set()
        for fr in frames:
            for v in list(fr.get("micro") or ()) + [fr["values"]]:
                for bid, o in ops.items():
                    out.add((bid, tuple(v.get(n) for n, _ in o.ins), tuple(v.get(n) for n, _ in o.outs)))
        return out

    def guided(start, steps, timed=False):
        """본 적 없는 것을 가장 많이 보여 주는 입력 하나를 골라 뒤집으며 걷는다 (순서가 있어야 서는 자리를 찾아간다).
        timed — 시간을 멈춘 채(기다림 0) 입력을 바꾸고, '다음 타이머까지 기다림' 도 한 걸음으로 친다: 타이머가 세는 **도중에** 입력이
        바뀌어야 서는 자리 (명령 뒤 10초 안에 열림이 꺼짐 → 3초 뒤 불일치 고장 · 대기 시간 전에 START 를 놓음)."""
        for o in ops.values():
            o.reset()
        hz = 0 if timed else None
        cur = dict(start)
        st, frames = sim_step(cur, None, hz)
        if frames is None:
            return
        grade(frames)
        sigs.update(sig_of(frames))
        for _ in range(steps):
            best = None
            order = list(keys)
            rng.shuffle(order)
            cands = [({**cur, k: 1 - cur.get(k, 0)}, hz) for k in order]
            run_ = frames[-1].get("running") or () if timed else ()
            if run_:
                cands.append((cur, min(x["left"] for x in run_)))          # 입력은 그대로 두고 가장 먼저 끝나는 타이머까지 기다린다
            for f, h in cands:
                st2, fr2 = sim_step(f, st, h)
                if fr2 is None:
                    continue
                new = len(sig_of(fr2) - sigs)
                if best is None or new > best[0]:
                    best = (new, f, st2, fr2)
            if best is None:
                return
            if best[0] == 0:                               # 새로 보이는 것이 없다 — 아무 걸음이나 하나 골라 이어 간다
                f, h = rng.choice(cands)
                st2, fr2 = sim_step(f, st, h)
                if fr2 is None:
                    return
                best = (0, f, st2, fr2)
            _, cur, st, frames = best
            grade(frames)
            sigs.update(sig_of(frames))
        if timed:                                          # 끝으로 남은 타이머를 다 흘린다
            st, frames = sim_step(cur, st, None)
            if frames is not None:
                grade(frames)

    allon = {k: 1 for k in keys}
    run([{}])
    for k in keys:
        run([{k: 1}, {}])
    if keys:
        run([allon, {}])
        for k in keys:
            run([allon, {**allon, k: 0}, allon])
    rng = random.Random(95)
    for _ in range(RANDOM_RUNS if keys else 0):
        a = {k: rng.randint(0, 1) for k in keys}
        b = {k: (v if rng.random() < 0.7 else 1 - v) for k, v in a.items()}
        c = {k: (v if rng.random() < 0.7 else 1 - v) for k, v in b.items()}
        run([a, b, c, a])
    # 한 번에 입력 하나만 바꾸며 걷는다 (상태를 이어 준다) — 순서가 있어야 서는 자리: 명령 → 열림 → 열림이 꺼짐 → 불일치 고장 같은 것
    for w in range(WALKS if keys else 0):
        cur = {} if w % 3 == 0 else ({k: 1 for k in keys} if w % 3 == 1 else {k: rng.randint(0, 1) for k in keys})
        seq = [dict(cur)]
        for _ in range(WALK_STEPS):
            k = rng.choice(keys)
            cur[k] = 1 - cur.get(k, 0)
            seq.append(dict(cur))
        run(seq)
    for start in ({}, {k: 1 for k in keys}, {}) if keys else ():
        guided(start, GUIDED_STEPS)
    has_timer = any(o.kind in TIMERS for o in ops.values())
    for start in ({}, {}, {k: 1 for k in keys}) if keys and has_timer else ():
        guided(start, TIMED_STEPS, timed=True)
    # 연산자 출력마다 풀이(범례 정의로 거꾸로 찾은 입력 조합)를 주고, 그 자리에서 입력을 하나씩 뒤집었다 되돌린다
    for bid, o in ops.items():
        for on, _ in o.outs:
            try:
                sc = sim.scenario(s, f"net:{on}", 1, sheets=sheets, cache=cache, rows_only=True)
            except Exception:                              # noqa: BLE001
                stat["scenario_err"] += 1
                continue
            stat["scenarios"] += 1
            if not sc.get("ok"):
                continue
            f = {k: v for k, v in (sc.get("forces") or {}).items() if not k.startswith("net:")}
            seq = [f]
            for k in keys:
                seq += [{**f, k: 1 - f.get(k, 0)}, f]
            run(seq)
    # 연산자마다 입력 선을 직접 겨눈다 (시뮬레이터가 그 값이 나오게 앞쪽을 맞춘다 — 막히면 실제 선 값으로 채점될 뿐이다)
    for bid, o in ops.items():
        nets = list(dict.fromkeys(n for n, _ in o.ins))
        if not nets or len(nets) > 8:
            continue
        if o.kind == "memory":
            S = [n for n, r in o.ins if r == "set"]
            R = [n for n, r in o.ins if r == "reset"]
            f = lambda sv, rv: {**{f"net:{n}": sv for n in S}, **{f"net:{n}": rv for n in R}}      # noqa: E731
            run([f(1, 0), f(0, 0), f(0, 1), f(0, 0), f(1, 1), f(0, 0)])
            run([f(1, 1), f(0, 0), f(1, 0), f(1, 1)])
        elif o.kind in TIMERS:
            f = lambda x: {f"net:{n}": x for n in nets}                                              # noqa: E731
            run([f(1), f(0), f(1)])
        else:
            one, zero = {f"net:{n}": 1 for n in nets}, {f"net:{n}": 0 for n in nets}
            run([one])
            run([zero])
            for n in nets:
                run([one, {**one, f"net:{n}": 0}])
                run([zero, {**zero, f"net:{n}": 1}])
    return ops, stat, len(keys)


def paint(pdf, s, ops, out):
    import pymupdf
    pg = pdf[s["page"] - 1]
    sh = pg.new_shape()
    for o in ops.values():
        got, need, _ = o.coverage()
        kind = "bad" if o.bad else ("none" if not o.checks or not got else ("full" if got >= need else "part"))
        x0, y0, x1, y1 = o.b["bbox"]
        sh.draw_rect(pymupdf.Rect(x0 - 1.5, y0 - 1.5, x1 + 1.5, y1 + 1.5))
        sh.finish(color=COL[kind], fill=COL[kind], width=1.4, fill_opacity=0.28, stroke_opacity=0.95)
    sh.commit()
    lg = s.get("logic") or [0, 0, pg.rect.width, pg.rect.height]
    pg.get_pixmap(dpi=120, clip=pymupdf.Rect(lg[0] - 250, lg[1] - 30, lg[2] + 250, lg[3] + 10)).save(out)


def main():
    import pymupdf
    job, out = sys.argv[1], Path(sys.argv[2])
    only = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else None
    out.mkdir(parents=True, exist_ok=True)
    sim.MICRO = True
    res = api._result(job)
    sheets = api._all_sheets(res)
    typ = [s for s in res["sheets"] if re.fullmatch(r"\d{4}", s.get("sheet_no") or "") and s.get("rows") and (not only or s["sheet_no"] in only)]
    cache = {}
    rows, tot, bykind = [], collections.Counter(), collections.defaultdict(collections.Counter)
    t0 = time.time()
    pdf = pymupdf.open(str(store.root() / job / "source.pdf"))
    for s in typ:
        ops, stat, nkeys = check_sheet(s, sheets, cache)
        row = {"sheet": s["sheet_no"], "title": (s.get("title") or "")[:40], "inputs": nkeys, "runs": stat["runs"], "frames": stat["frames"],
               "errors": stat["errors"], "ops": len(ops), "checks": 0, "bad_ops": 0, "full": 0, "part": 0, "none": 0, "detail": []}
        for bid, o in sorted(ops.items()):
            got, need, txt = o.coverage()
            cls = "bad" if o.bad else ("none" if not o.checks or not got else ("full" if got >= need else "part"))
            row["checks"] += o.checks
            row["bad_ops" if o.bad else cls] += 1
            k = bykind[o.kind]
            k["n"] += 1
            k["checks"] += o.checks
            k[cls] += 1
            k["bad_checks"] += o.seen["bad"]
            k["instant_edge"] += o.seen["instant_edge"]
            if o.kind == "memory":
                k["hold_changed"] += o.seen["hold_changed"]
                k[f"dom:{(o.b.get('param') or {}).get('dominant') or '-'}"] += 1
            if cls != "full":
                why = ("입력을 다 못 읽음" if o.kind in GATES and (len(o.ins) < max(o.need, 1) or not o.outs) else
                       "자기유지 고리 — 그 조합이 구조상 안 생김" if o.selfloop and o.checks else
                       "신호가 닿지 않음 (앞쪽 읽기 빈틈)" if not got else "일부 조합만 봄")
                k[f"why:{why}"] += 1
                row["detail"].append({"block": bid, "kind": o.kind, "label": o.b.get("label"), "class": cls, "why": why, "checks": o.checks, "seen": txt,
                                      "bad": o.bad, "in": len(o.ins), "out": len(o.outs)})
        rows.append(row)
        for k in ("runs", "frames", "errors", "ops", "checks", "bad_ops", "full", "part", "none"):
            tot[k] += row[k]
        if pdf is not None:
            try:
                paint(pdf, s, ops, str(out / f"{s['sheet_no']}.png"))
            except Exception as e:                         # noqa: BLE001
                print("paint", s["sheet_no"], e)
        print(f"{s['sheet_no']} 입력 {nkeys:3d} · 돌림 {stat['runs']:5d} · 연산자 {len(ops):3d} · 채점 {row['checks']:7d} · 어긋남 {row['bad_ops']} · "
              f"다 봄 {row['full']} · 일부 {row['part']} · 못 봄 {row['none']}", flush=True)
    summary = {"job": job, "sheets": len(typ), "seconds": round(time.time() - t0), "total": dict(tot),
               "by_kind": {k: dict(v) for k, v in bykind.items()}, "rows": rows}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print("합계", dict(tot))
    for k, v in sorted(bykind.items()):
        print(f"  {k:10s}", dict(v))


if __name__ == "__main__":
    main()
