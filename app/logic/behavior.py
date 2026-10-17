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
LEARN_TRIES_DEEP = 400   # L36 — 첫 학습에서 안 선 명령은 더 깊이 (시간이 걸려도 좋다 — 사용자)
INNER_ANY_DEEP = 10
INNER_ANY = 6             # 조합을 바꿔 보는 갈래(OR · 메모리 …) 수 상한 — 나머지는 나무가 권한 갈래
VERSION = 3              # L36 — 다른 길 · 함께 바뀌는 출력 · 펄스 길이 (L35 이해) — 이해(막는 신호 · 유지 · 반대 명령 짝)를 더했다 · 바뀌면 다시 배운다
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


def learn_one(sheets, page, row, want=1, cache=None, timers=None, deep=False):
    p = sequence.plan(sheets, page, row, want)
    if not p.get("ok"):
        return {"page": page, "row": row, "reached": False, "why": p.get("why") or "조건을 읽지 못함"}
    tree = sequence.link(p)
    if tree["t"] == "leaf" and tree.get("key") == f"net:{p['net']}":
        # 출력 선 자체를 모는 것이 없다 — 그 선을 직접 주는 것은 답이 아니다 (도면에서 선이 끊긴 자리)
        return {"page": page, "row": row, "reached": False, "tried": 0, "undriven": True,
                "why": "출력선이 끊김 (마크업으로 이을 수 있음)"}
    anys = _anys(tree)[:INNER_ANY_DEEP if deep else INNER_ANY]
    choices = [{}]
    for a in anys:                                   # 나무가 권한 갈래부터 · 하나씩만 바꾼 조합 → 둘 …
        alts = [i for i in range(len(a["kids"])) if i != a.get("pick", 0)]
        choices += [{a["id"]: i} for i in alts]
    for a, b in itertools.combinations(anys, 2):
        for i in range(len(a["kids"])):
            for j in range(len(b["kids"])):
                choices.append({a["id"]: i, b["id"]: j})
    if deep:                                         # L36 — 깊이 배우기: 갈래 셋을 함께 바꾼 조합까지
        for a, b, c in itertools.combinations(anys, 3):
            for i in range(len(a["kids"])):
                for j in range(len(b["kids"])):
                    for k in range(len(c["kids"])):
                        choices.append({a["id"]: i, b["id"]: j, c["id"]: k})
    tried, seen, best, hits, stop_at = 0, set(), None, [], None
    # 한 신호를 두 자리가 반대로 바라면 — 1 을 두는 조합과 앞자리(나무 순서) 것을 두는 조합을 둘 다 돌려 본다
    for ch, prefer in ((c, pr) for c in choices for pr in (1, 0)):
        F = _forces(tree, ch, prefer)
        key = repr(sorted((pg, sorted(v.items())) for pg, v in F.items()))
        if key in seen:
            continue
        seen.add(key)
        tried += 1
        if tried > (LEARN_TRIES_DEEP if deep else LEARN_TRIES) or (stop_at is not None and tried > stop_at):
            break
        hit, steady, _ = _hit(sheets, F, page, p["net"], want, cache, timers)
        # L35 — 도면이 상수(FORCED INPUT 0/1)로 묶어 둔 신호를 뒤집는 조합은 마지막에 고른다 (그 길은 도면이 막아 둔 길)
        clean = not _flips_const(sheets, F)
        if hit and clean:
            hits.append(F)
        if hit and (best is None or (clean, steady) > (best[2], best[1])):
            best = (F, steady, clean)
            if steady and clean and stop_at is None:
                stop_at = tried + ALT_SEARCH       # L36 — 찾은 뒤에도 몇 조합 더 돌려 다른 길을 찾는다
    if best is None:
        blk = _blocker(sheets, page, tree, _forces(tree, {}), cache)
    stuck = [{"text": v.get("text"), "page": v.get("page"), "block": v.get("block")}
             for v in p["nodes"].values() if v.get("kind") == "stuck"]
    if best is None:
        return {"page": page, "row": row, "reached": False, "tried": tried, "stuck": stuck[:6], "blocked_at": blk,
                "why": ("도면 읽기 빈틈이 길에 있음" if stuck else
                        "어느 조합으로도 안 섬 (되먹임 · 다른 시트)")}
    need = _minimize(sheets, best[0], page, p["net"], want, cache, timers)
    labels = _labels(sheets, need)
    holds = sum(1 for v in need.values() for k in v if k.startswith("hold:") or (k.startswith("net:") and "/" in k))
    out = {"page": page, "row": row, "net": p["net"], "reached": True, "steady": best[1], "tried": tried, "forces": need,
           "labels": labels, "holds": holds, "signals": sum(len(v) for v in need.values())}
    try:
        out.update(understand(sheets, p, need, page, want, cache, timers))
    except Exception as ex:                          # 이해가 실패해도 배운 조합은 남긴다
        out["understand_error"] = str(ex)
    try:
        out["alts"] = _alternatives(sheets, hits, need, page, p["net"], want, cache, timers)
    except Exception as ex:
        out["alts"] = []
        out["understand_error"] = out.get("understand_error") or str(ex)
    return out


ALT_SEARCH = 12           # 첫 길을 찾은 뒤 더 돌려 보는 조합 수
ALT_MAX = 3               # 다른 길(다른 최소 조합)을 몇 개까지 남기나 — L36


def _alternatives(sheets, hits, need, page, net, want, cache, timers):
    """L36 — 같은 명령을 내는 **다른 길**.  학습 중 선 조합(상수를 뒤집지 않은 것) 가운데 줄이고 나서 남는 신호의
    모음이 앞의 것과 다른 것 (OR 갈래 · 자동/수동 · 다른 시트에서 오는 요청).  판정은 시뮬레이터가 이미 했다."""
    sig = lambda F: frozenset((pg, k, v) for pg, d in F.items() for k, v in d.items())
    if not sig(need):
        return []                                     # 아무것도 안 줘도 서는 명령 — 다른 길을 말할 것이 없다
    known = {sig(need)}
    out = []
    for F in hits:
        if len(out) >= ALT_MAX:
            break
        if sig(F) in known:
            continue
        m = _minimize(sheets, F, page, net, want, cache, timers)
        s = sig(m)
        if s in known or not s:
            known.add(sig(F))
            continue
        known |= {s, sig(F)}
        ls = _labels(sheets, m)
        if all(l.get("assumed") or "const" in l for l in ls):
            continue                                  # 도면 읽기 빈틈에만 기대는 길은 '다른 길' 이 아니다
        out.append({"forces": m, "labels": ls})
    return out


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
                c = _const(b)
                if c is not None:
                    text = f"도면이 언제나 {c} 로 묶은 신호 '{lab}'"
            elif kind == "block":
                box, _, inner = x.partition("/")
                mac = (s.get("blocks", {}).get(box) or {}).get("macro") or {}
                ib = ((by.get(mac.get("page")) or {}).get("blocks") or {}).get(inner) or {}
                lab = (ib.get("label") or ib.get("func") or "").strip()
                text = f"매크로 안쪽 {lab} ({mac.get('sheet') or box})" if lab else f"매크로 {box} 안쪽 블록"
            elif kind == "hold":
                text = "입력을 다 읽지 못한 게이트 — 만족으로 봄"
            else:
                text = "매크로 단자 없음 · 몰이를 못 읽은 선 — 직접 줌" if "/" in x else "몰이를 못 읽은 선 — 직접 줌"
            item = {"page": pg, "sheet": s.get("sheet_no"), "key": k, "value": v, "text": text,
                    "assumed": kind == "hold" or kind == "net"}
            if kind == "block" and "/" not in x and _const(s.get("blocks", {}).get(x) or {}) is not None:
                item["const"] = _const(s["blocks"][x])
            out.append(item)
    return out


def _flips_const(sheets, F):
    by = {s["page"]: s for s in sheets}
    for pg, fs in F.items():
        B = (by.get(pg) or {}).get("blocks") or {}
        for k, v in fs.items():
            if k.startswith("block:") and "/" not in k:
                c = _const(B.get(k[6:]) or {})
                if c is not None and c != v:
                    return True
    return False


def _const(b):
    """FORCED INPUT — 들어오는 선 없는 신호 상자에 글자 '0' 또는 '1' 하나 (범례 · L21).  사람이 누르는 단추가 아니다."""
    if b.get("logic") != "source":
        return None
    lab = "".join(ch for ch in (b.get("label") or "").upper() if ch.isalnum())
    return int(lab) if lab in ("0", "1") else None


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


# ------------------------------------------------------------------ L35 — 로직 이해: 켜는 것 · 막는 것 · 유지 · 끄는 것

PROBE_MAX = 12            # 막는 신호 · 끄는 신호 후보를 돌려 보는 수 상한 (명령 하나)


def _probe_keys(p, need):
    """조건 나무가 '없어야 한다(0)' 고 말한 실제 신호 — 막는 신호(인터록 · 트립 · 반대 명령)의 후보.
    판정은 아래에서 시뮬레이터가 한다 (후보일 뿐)."""
    have = need.get(p["page"], {})
    keys, seen = [], set()
    for v in p["nodes"].values():
        cand = []
        if v.get("t") == "leaf" and v.get("want") == 0 and v.get("kind") in ("row", "button", "monitor") and v.get("key"):
            cand.append(v)
        if v.get("kind") == "zero":
            cand += [it for it in v.get("items") or [] if it.get("key") and it["key"].split(":")[0] in ("row", "block")]
        for it in cand:
            k = it["key"]
            if k.startswith("block:") and "/" not in k and _const((p.get("_blocks") or {}).get(k[6:]) or {}) is not None:
                continue
            if k in seen or k in have:
                continue
            seen.add(k)
            keys.append(k)
    return keys[:PROBE_MAX]


def _last(sheets, forces, state, page, net, cache, timers):
    r = sim.simulate_bundle(sheets, forces, state, page, timers=timers, cache=cache)
    fr = (r["focus"] or {}).get("frames") or []
    return (fr[-1]["values"].get(net) if fr else None), [f["values"].get(net) for f in fr], r.get("state") or {}


def understand(sheets, p, need, page, want, cache, timers):
    """그 명령이 선 조합(need)에서 — 판정 0줄, 전부 같은 묶음 시뮬레이터로 앞으로 돌려 본 결과다.
      * always_on — 아무 신호도 안 줘도 그 값인가 (입력 0 의 NOT 처럼 — 확인 대상)
      * interlocks — 선 상태에 그 신호를 1 로 더하면 명령이 안 서는 것 (막는 신호 · 트립 · 반대 명령)
      * latch — 누름단추(없으면 모든 신호)를 놓아도 유지되는가 (자기유지 · 메모리) — 잠깐 서는 명령은 묻지 않는다
      * stoppers — 유지되는 명령에서 그 신호가 1 이 되면 꺼지는 것 · drops — 그 허가가 0 이 되면 꺼지는 것"""
    net = p["net"]
    out = {}
    p = dict(p, _blocks=next((s["blocks"] for s in sheets if s["page"] == page), {}), row_n=p.get("row"))
    tied = [l["text"] for l in _labels(sheets, need) if "const" in l and l["const"] != l["value"]]
    if tied:
        out["tied_off"] = tied                        # 상수에 묶인 신호를 뒤집어야만 선다 — 도면이 이 명령을 쓰지 않게 묶어 둠
    base, _, _ = _last(sheets, {}, None, page, net, cache, timers)
    out["always_on"] = base == want
    keys = _probe_keys(p, need)
    inter = {}
    for k in keys:
        F = {pg: dict(v) for pg, v in need.items()}
        F.setdefault(page, {})[k] = 1
        if not _hit(sheets, F, page, net, want, cache, timers)[0]:
            inter.setdefault(page, {})[k] = 1
    out["interlocks"] = _labels(sheets, inter)
    r1 = sim.simulate_bundle(sheets, need, None, page, timers=timers, cache=cache)
    fr = (r1["focus"] or {}).get("frames") or []
    v1, st = (fr[-1]["values"].get(net) if fr else None), r1.get("state") or {}
    out["pulse_s"] = _pulse_len(fr, net, want)
    try:
        out["effects"] = _effects(sheets, r1, page, p["row_n"], cache, timers)
    except Exception:
        out["effects"] = []
    if v1 != want:
        out["latch"] = None                           # 잠깐 서는 명령 (펄스) — 놓으면 꺼지는 것이 정의다
        return out
    buttons = {pg: {k for k in v if k.startswith("block:")} for pg, v in need.items()}
    if not any(buttons.values()):
        buttons = {pg: set(v) for pg, v in need.items()}
        out["latch_released"] = "all"
    else:
        out["latch_released"] = "buttons"
    rest = {pg: {k: x for k, x in v.items() if k not in buttons.get(pg, ())} for pg, v in need.items()}
    rest = {pg: v for pg, v in rest.items() if v}
    v2, _, st2 = _last(sheets, rest, st, page, net, cache, timers)
    out["latch"] = v2 == want
    if not out["latch"]:
        return out
    stop, drop = {}, {}
    for k in keys:
        F = {pg: dict(v) for pg, v in rest.items()}
        F.setdefault(page, {})[k] = 1
        if _last(sheets, F, st2, page, net, cache, timers)[0] != want:
            stop.setdefault(page, {})[k] = 1
    for pg, v in rest.items():
        for k, x in v.items():
            if x != 1 or not k.startswith("row:"):
                continue
            F = {q: dict(w) for q, w in rest.items()}
            F[pg][k] = 0
            if _last(sheets, F, st2, page, net, cache, timers)[0] != want:
                drop.setdefault(pg, {})[k] = 0
    out["stoppers"] = _labels(sheets, stop)
    out["drops"] = _labels(sheets, drop)
    return out


EFFECT_MAX = 24


def _pulse_len(frames, net, want):
    """잠깐 나가는 명령이면 몇 초 나가는가 — 틀의 시각(t) 으로 (서 있으면 None)."""
    on = None
    for f in frames:
        v = f["values"].get(net)
        if v == want and on is None:
            on = f.get("t", 0)
        elif v != want and on is not None:
            return round((f.get("t", 0) or 0) - (on or 0), 2)
    return None


def _effects(sheets, r1, page, row, cache, timers):
    """L36 — 그 명령이 서면 묶음에서 **함께 1 이 되는 출력 행** (다른 장비 · 다른 시트로 이어지는 것).
    신호가 닿은 장(hop)의 출력만 보고, 아무것도 안 줬을 때도 1 인 것은 뺀다 — 이 명령 때문에 바뀐 것만."""
    by = {s["page"]: s for s in sheets}
    cand = [(c["page"], n, c.get("hop")) for c in r1.get("pages") or [] if c.get("hop") is not None
            for n in c.get("on_out") or [] if not (c["page"] == page and n == row)]
    if not cand:
        return []
    sim.simulate_bundle(sheets, {}, None, page, timers=timers, cache=cache)
    res0 = (cache or {}).get("_last_results") or {}
    out = []
    for pg, n, hop in sorted(cand, key=lambda x: (x[2], x[0], x[1])):
        s = by.get(pg) or {}
        r = next((x for x in s.get("rows", []) if x["side"] == "R" and x["n"] == n), None)
        if not r or r.get("net") is None:
            continue
        fr0 = (res0.get(pg) or {}).get("frames") or []
        if fr0 and fr0[-1]["values"].get(r["net"]) == 1:
            continue
        out.append({"page": pg, "sheet": s.get("sheet_no"), "row": n, "text": r.get("desc") or f"{n}행",
                    "to": r.get("to") or "", "hop": hop})
        if len(out) >= EFFECT_MAX:
            break
    return out


def _pairs(sheets, items, opposites, cache, timers):
    """한 장비의 반대 명령 짝 (START↔STOP · OPEN↔CLOSE) 을 같이 돌려 본다 — 두 명령이 선 조합을 함께 주고
    두 출력이 함께 1 이 되는가 (되면 '동시 지령 가능' — 논리 안에 서로를 막는 신호가 없다 · 확인 대상).
    함께 안 서면 무엇이 가르는가 — 한 명령의 꼭 필요한 신호가 다른 명령의 '막는 신호' 인 것."""
    by = {x["action"]: x for x in items if x.get("reached")}
    out = []
    for a, b in opposites:
        if a not in by or b not in by:
            continue
        A, B = by[a], by[b]
        F = {pg: dict(v) for pg, v in A["forces"].items()}
        for pg, v in B["forces"].items():
            F.setdefault(pg, {}).update(v)
        both = None
        if A.get("net") is not None and B.get("net") is not None:
            va, _, _ = _last(sheets, F, None, A["page"], A["net"], cache, timers)
            vb, _, _ = _last(sheets, F, None, B["page"], B["net"], cache, timers)
            both = va == 1 and vb == 1
        split = None
        if not both:
            for X, Y in ((A, B), (B, A)):
                blk = {(l["page"], l["key"]) for l in Y.get("interlocks") or []}
                hit = [l for l in X.get("labels") or [] if (l["page"], l["key"]) in blk and l["value"] == 1]
                if hit:
                    split = hit[0]["text"]
                    break
        cond = lambda x: [l["text"] for l in x.get("labels") or [] if not l.get("assumed")][:4]
        out.append({"a": a, "b": b, "both": both, "exclusive": both is False, "split": split,
                    "a_at": [A["page"], A["row"]], "b_at": [B["page"], B["row"]], "a_need": cond(A), "b_need": cond(B)})
    return out


def summarize(items, pairs):
    """묶음 전체 — 사람이 먼저 봐야 할 것을 센다 (판정 아님 · 배운 결과를 모아 세기만)."""
    from collections import Counter
    perm, block = Counter(), Counter()
    text = {}
    for x in items:
        for l in x.get("labels") or []:
            if l.get("assumed") or l["key"].startswith("block:") or "const" in l:
                continue
            k = (l["sheet"], l["key"], l["value"])
            perm[k] += 1
            text[k] = l["text"]
        for l in x.get("interlocks") or []:
            k = (l["sheet"], l["key"], 1)
            block[k] += 1
            text[k] = l["text"]
    top = lambda c: [{"sheet": k[0], "key": k[1], "value": k[2], "text": text[k], "count": n} for k, n in c.most_common(8) if n >= 2]
    reached = [x for x in items if x.get("reached")]
    return {
        "commands": len(items), "reached": len(reached),
        "latched": sum(1 for x in reached if x.get("latch")),
        "momentary": sum(1 for x in reached if x.get("latch") is False),
        "pulse": sum(1 for x in reached if "latch" in x and x["latch"] is None),
        "with_interlock": sum(1 for x in reached if x.get("interlocks")),
        "tied_off": [{"equip": x["equip"], "action": x["action"], "sheet": x["sheet"], "row": x["row"], "page": x["page"],
                      "text": x["tied_off"][0]} for x in reached if x.get("tied_off")],
        "always_on": [{"equip": x["equip"], "action": x["action"], "sheet": x["sheet"], "row": x["row"], "page": x["page"]}
                      for x in reached if x.get("always_on")],
        "unreached": len(items) - len(reached),
        "both_on": [p for p in pairs if p.get("both")],
        "exclusive": sum(1 for p in pairs if p.get("exclusive")),
        "common_need": top(perm), "common_block": top(block),
    }


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
            if not res.get("reached") and not res.get("undriven") and not res.get("stuck"):
                try:                                  # 갈래 조합이 모자랐을 수 있다 — 더 깊이 다시
                    deep = learn_one(sheets, r["page"], r["row"], 1, cache, timers, deep=True)
                    deep["deep"] = True
                    if deep.get("reached"):
                        res = deep
                    else:
                        res["deep_tried"] = deep.get("tried")
                except Exception:
                    pass
            res.update(equip=e["equip"], action=a["action"], sheet=r["sheet"], desc=r["desc"], kind=r["kind"])
            out.append(res)
            done += 1
            if progress:
                progress(done, total)
    # L35 — 장비마다 반대 명령 짝 · 묶음 전체에서 자주 쓰이는 허가 / 막는 신호
    opp = sequence.vocab().get("opposites") or []
    eqs = {}
    for x in out:
        eqs.setdefault(x["equip"], []).append(x)
    pairs = []
    for name, items in eqs.items():
        try:
            for pr in _pairs(sheets, items, opp, cache, timers):
                pairs.append({"equip": name, **pr})
        except Exception:
            pass
    ok = sum(1 for x in out if x["reached"])
    return {"version": VERSION, "pairs": pairs, "summary": summarize(out, pairs), "seconds": round(time.time() - t0, 1), "total": total, "reached": ok,
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
    return f"v{VERSION}:{rm}:{overrides.mtime(d)}"


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
