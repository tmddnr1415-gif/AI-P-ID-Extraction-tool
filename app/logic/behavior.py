"""L33 — 동작 학습: 묶음의 모든 START · STOP · OPEN · CLOSE · TRIP 을 시뮬레이터로 켜고 꺼 보며 무엇이 그 명령을 내는지 배운다.

동작마다 (sequence.commands 의 대표 행):
  1. 조건 나무(sequence.plan)를 거꾸로 읽어 '실제 신호(입력 행 · 누름단추 · 감시 블록)' 와 '읽지 못한 게이트(hold)' 의 조합을 만든다.
     OR · 메모리 같은 갈래는 조합을 바꿔 가며 (LEARN_TRIES 개까지) **같은 묶음 시뮬레이터로 앞으로 돌려** 명령이 서는지 본다.
     짐작하지 않는 것: 매크로 안쪽의 몰이를 못 읽은 선 (그 선이 AUTO 모드처럼 다른 길을 막을 수 있다 — L32 실측).
  2. 선 조합에서 신호를 하나씩 빼 보며 **꼭 필요한 신호만** 남긴다 (빼도 서면 필요 없는 신호).
  3. 결과를 남긴다 — 선다/안 선다 · 잠깐 서는가(펄스) · 꼭 필요한 신호 · 읽지 못한 자리에 답한 것(hold) · 막는 자리.
판정 0줄 — 결과는 언제나 시뮬레이터가 낸다.  배운 것은 분석 폴더 `behavior.json` 에 두고 화면이 읽는다 (사람 값을 고치면 다시 배운다).
"""
from __future__ import annotations

import itertools
import time

from . import sequence, sim

LEARN_TRIES = 64          # 동작 하나에 돌려 보는 갈래 조합 수 상한
INNER_ANY = 6             # 조합을 바꿔 보는 갈래(OR · 메모리 …) 수 상한 — 나머지는 나무가 권한 갈래
REAL = ("row", "button", "monitor", "stuck", "terminal", "net")


def _anys(tree):
    out, seen = [], set()

    def walk(n):
        if id(n) in seen:
            return
        seen.add(id(n))
        if n["t"] == "any":
            out.append(n)
        for k in n.get("kids") or []:
            walk(k)
    walk(tree)
    return out


def _forces(tree, choice, prefer=1):
    """조합 하나 — 고른 갈래를 따라 실제 신호는 바라는 값으로 (sequence 의 잎 그대로)."""
    F = {}
    seen = set()

    def visit(n):
        if n["t"] == "leaf":
            if n.get("key") and n.get("kind") in REAL:
                d = F.setdefault(n["page"], {})
                # 같은 신호를 한 자리는 1, 다른 자리는 0 으로 바라면 1 을 둔다 — 0 을 바라는 자리는 대개 '없어야 하는 것'
                # (되먹임 · 반대 모드) 이라 주지 않으면 0 이지만, 1 을 바라는 자리는 주지 않으면 서지 않는다 (L33 실측: REMOTE)
                if n["key"] not in d or (prefer == 1 and n["want"] == 1):
                    d[n["key"]] = n["want"]
            return
        if n["t"] == "any":
            visit(n["kids"][choice.get(n["id"], n.get("pick", 0))])
            return
        if id(n) in seen:
            return
        seen.add(id(n))
        for k in n["kids"]:
            visit(k)
    visit(tree)
    return F


def _hit(sheets, forces, page, net, want, cache, timers):
    r = sim.simulate_bundle(sheets, forces, None, page, timers=timers, cache=cache)["focus"] or {"frames": []}
    vals = [fr["values"].get(net) for fr in r["frames"]]
    return (want in vals), (bool(vals) and vals[-1] == want), r


def _minimize(sheets, forces, page, net, want, cache, timers):
    """빼도 서는 신호는 뺀다 — 남는 것이 그 명령에 꼭 필요한 신호다."""
    cur = {p: dict(v) for p, v in forces.items()}
    for p in sorted(cur):
        for k in sorted(cur[p]):
            if k not in cur[p]:
                continue
            trial = {pp: {kk: vv for kk, vv in vv_.items() if not (pp == p and kk == k)} for pp, vv_ in cur.items()}
            trial = {pp: v for pp, v in trial.items() if v}
            if _hit(sheets, trial, page, net, want, cache, timers)[0]:
                cur = trial
    return cur


def learn_one(sheets, page, row, want=1, cache=None, timers=None):
    p = sequence.plan(sheets, page, row, want)
    if not p.get("ok"):
        return {"page": page, "row": row, "reached": False, "why": p.get("why") or "조건 나무를 만들지 못했습니다"}
    tree = sequence.link(p)
    if tree["t"] == "leaf" and tree.get("key") == f"net:{p['net']}":
        # 출력 선 자체를 모는 것이 없다 — 그 선을 직접 주는 것은 답이 아니다 (도면에서 선이 끊긴 자리)
        return {"page": page, "row": row, "reached": False, "tried": 0, "undriven": True,
                "why": "이 출력 행의 선을 모는 블록을 도면에서 읽지 못했습니다 (선이 끊김 — 마크업 · 가르치기로 이을 수 있습니다)"}
    anys = _anys(tree)[:INNER_ANY]
    choices = [{}]
    for a in anys:                                   # 나무가 권한 갈래부터 · 하나씩만 바꾼 조합 → 둘 …
        alts = [i for i in range(len(a["kids"])) if i != a.get("pick", 0)]
        choices += [{a["id"]: i} for i in alts]
    for a, b in itertools.combinations(anys, 2):
        for i in range(len(a["kids"])):
            for j in range(len(b["kids"])):
                choices.append({a["id"]: i, b["id"]: j})
    tried, seen, best = 0, set(), None
    # 한 신호를 두 자리가 반대로 바라면 — 1 을 두는 조합과 앞자리(나무 순서) 것을 두는 조합을 둘 다 돌려 본다
    for ch, prefer in ((c, pr) for c in choices for pr in (1, 0)):
        F = _forces(tree, ch, prefer)
        key = repr(sorted((pg, sorted(v.items())) for pg, v in F.items()))
        if key in seen:
            continue
        seen.add(key)
        tried += 1
        if tried > LEARN_TRIES:
            break
        hit, steady, _ = _hit(sheets, F, page, p["net"], want, cache, timers)
        if hit and (best is None or (steady and not best[1])):
            best = (F, steady)
            if steady:
                break
    if best is None:
        blk = _blocker(sheets, page, tree, _forces(tree, {}), cache)
    stuck = [{"text": v.get("text"), "page": v.get("page"), "block": v.get("block")}
             for v in p["nodes"].values() if v.get("kind") == "stuck"]
    if best is None:
        return {"page": page, "row": row, "reached": False, "tried": tried, "stuck": stuck[:6], "blocked_at": blk,
                "why": ("도면을 다 읽지 못한 자리(판정 못 한 블록 · 못 읽은 단자)가 길에 있습니다" if stuck else
                        "어느 조합으로도 서지 않습니다 (되먹임 · 다른 시트 조건)")}
    need = _minimize(sheets, best[0], page, p["net"], want, cache, timers)
    labels = _labels(sheets, need)
    holds = sum(1 for v in need.values() for k in v if k.startswith("hold:") or (k.startswith("net:") and "/" in k))
    return {"page": page, "row": row, "reached": True, "steady": best[1], "tried": tried, "forces": need, "labels": labels,
            "holds": holds, "signals": sum(len(v) for v in need.values())}


def _labels(sheets, forces):
    """꼭 필요한 신호를 사람 말로 — 시트 · 행 설명 · 블록 글자 (화면이 장을 다시 받지 않게)."""
    by = {s["page"]: s for s in sheets}
    out = []
    for pg, fs in sorted(forces.items()):
        s = by.get(pg) or {}
        for k, v in sorted(fs.items()):
            kind, _, x = k.partition(":")
            text = ""
            if kind == "row":
                r = next((r for r in s.get("rows", []) if r["side"] == "L" and r["n"] == int(x)), None)
                text = (r or {}).get("desc") or f"{x}행"
                fm = (r or {}).get("fm")
                if fm:
                    text += f" (FM {fm})"
            elif kind == "block" and "/" not in x:
                b = s.get("blocks", {}).get(x) or {}
                lab = (b.get("label") or "").strip()
                text = f"{b.get('func') or '블록'} '{lab}'" if lab else (b.get("func") or "블록")
            elif kind == "block":
                text = f"매크로 {x.split('/')[0]} 안쪽 블록"
            elif kind == "hold":
                text = "입력을 다 읽지 못한 게이트 — 만족으로 봄"
            else:
                text = "매크로 단자 없음 · 몰이를 못 읽은 선 — 직접 줌" if "/" in x else "몰이를 못 읽은 선 — 직접 줌"
            out.append({"page": pg, "sheet": s.get("sheet_no"), "key": k, "value": v, "text": text,
                        "assumed": kind == "hold" or kind == "net"})
    return out


def _blocker(sheets, page, tree, forces, cache):
    """서지 않을 때 — 나무를 따라 내려가며 바라는 값이 안 나온 가장 깊은 게이트 (펼친 매크로 안쪽까지).
    시뮬레이터가 낸 값을 읽기만 한다."""
    if cache is None or "topo" not in cache:
        return None
    try:
        s1 = cache["topo"][4][page][0]
    except (KeyError, IndexError, TypeError):
        return None
    r = sim.simulate(s1, forces.get(page, {}))
    vals = r["frames"][-1]["values"]
    unread = set(r["frames"][-1].get("unread") or ())
    ins, outs, _, _, _ = sim._index(s1)
    seen, last = set(), [None]

    def walk(n):
        if id(n) in seen:
            return
        seen.add(id(n))
        g = n.get("gate")
        if g and g["block"] in s1["blocks"]:
            ok = any(vals.get(o) == g["want"] and o not in unread for o, _, _ in outs[g["block"]])
            if ok:
                return
            last[0] = {"block": g["block"], "label": g["label"], "want": g["want"],
                       "inputs": [{"net": i, "value": None if i in unread else vals.get(i)} for i, _, _ in ins[g["block"]]]}
        if n["t"] == "leaf":
            return
        for k in (n["kids"] if n["t"] == "all" else [n["kids"][n.get("pick", 0)]]):
            walk(k)
    walk(tree)
    return last[0]


def learn(sheets, cache=None, timers=None, progress=None):
    """묶음 전체 — 장비 · 동작마다 대표 행 하나 (명령 > 요청 > 동작 > 상태)."""
    cache = cache if cache is not None else {}
    t0 = time.time()
    cmds = sequence.commands(sheets)
    total = sum(len(e["actions"]) for e in cmds)
    out, done = [], 0
    for e in cmds:
        for a in e["actions"]:
            r = a["rows"][0]
            try:
                res = learn_one(sheets, r["page"], r["row"], 1, cache, timers)
            except Exception as ex:                  # 한 동작이 실패해도 나머지는 배운다 — 사유를 남긴다
                res = {"page": r["page"], "row": r["row"], "reached": False, "why": f"시뮬레이션 실패 — {ex}"}
            res.update(equip=e["equip"], action=a["action"], sheet=r["sheet"], desc=r["desc"], kind=r["kind"])
            out.append(res)
            done += 1
            if progress:
                progress(done, total)
    ok = sum(1 for x in out if x["reached"])
    return {"version": 1, "seconds": round(time.time() - t0, 1), "total": total, "reached": ok,
            "with_hold": sum(1 for x in out if x.get("holds")), "items": out}


# ------------------------------------------------------------------ 저장 · 읽기 (분석 폴더 behavior.json)

FILE = "behavior.json"
RUNNING = "behavior.running"


def key_of(d):
    """배운 것이 어느 결과 · 어느 사람 값으로 배운 것인가 — 바뀌면 다시 배운다."""
    from . import overrides
    try:
        rm = (d / "result.json").stat().st_mtime_ns
    except OSError:
        rm = None
    return f"{rm}:{overrides.mtime(d)}"


def load(d):
    import json
    try:
        return json.loads((d / FILE).read_text(encoding="utf-8"))
    except Exception:
        return None


def learn_dir(d):
    """분석 폴더 하나 — 사람 값까지 얹은 결과로 배운다 (화면이 시뮬레이션하는 것과 같은 결과)."""
    import json
    from . import api, store
    job = d.name
    res = api._result(job)
    sheets = api._all_sheets(res)
    key = key_of(d)
    t0 = [0.0]

    def progress(done, total):
        if time.time() - t0[0] < 1 and done != total:
            return
        t0[0] = time.time()
        try:
            store._atomic(d / RUNNING, json.dumps({"done": done, "total": total, "at": time.time()}))
        except Exception:
            pass
    try:
        out = learn(sheets, {}, progress=progress)
        out["key"] = key
        out["learned_at"] = time.time()
        store._atomic(d / FILE, json.dumps(out, ensure_ascii=False))
    finally:
        try:
            (d / RUNNING).unlink()
        except OSError:
            pass
    return out
