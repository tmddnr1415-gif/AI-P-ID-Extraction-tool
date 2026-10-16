"""L32 — 순차 동작 시뮬레이션: START · STOP · RUN · OPEN · CLOSE · TRIP 한 동작을 조건부터 차례로.

두 가지를 낸다.
  * commands(sheets) — 묶음의 출력 행 가운데 동작 행(`… MOV 1 OP CMD` · `START COMMAND` · `… OP REQ` · `RUNNING`)을
    장비마다 모은 목록.  장비 이름은 그 행 설명에서 동작 낱말 · 꼬리 낱말(CMD · REQ)을 뗀 나머지다 (지어내지 않는다).
    낱말은 config/logic_sequence.yaml (계장 영어 · 약어) — 코드에 낱말 목록을 두지 않는다.
  * plan(sheets, page, row) — 그 출력이 서려면 무엇이 필요한지 **조건 나무**.  범례 G003 정의를 거꾸로 읽는 길은
    시뮬레이터가 쓰는 것과 같다 (`sim._back_options` — AND 는 모두 · OR 는 하나 · NOT 은 반대 · 메모리 Q=1 은 SET 하나 +
    RESET 0 · 타이머는 유지 · 매크로는 그 Typical 시트의 입력 단자).  고르지 않는다 — OR 는 '하나를 고르세요' 로 남긴다.
    다른 시트에서 오는 입력 행은 그 자리에 `ref`(시트 · 행)를 달아 두고, 사람이 '그 시트 조건부터' 를 고르면 같은 함수로
    그 시트의 나무를 만든다 (묶음 전체를 한 번에 펼치면 846쪽에서 나무가 폭발한다).
    from-to 가 어긋난 입력 행에는 `ft` 를 달아 화면이 그 단계에서 '어떻게 할지' 를 묻는다.

판정 0줄 — 나무는 묻는 순서일 뿐이고, 답은 화면이 강제 신호로 주며 결과는 늘 같은 시뮬레이터가 낸다.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

from . import sim

NODE_LIMIT = 700        # 한 시트 나무의 마디 상한 — 넘으면 그 아래는 '더 깊다' 로 남긴다 (화면이 그 선을 직접 묻는다)
DEPTH_LIMIT = 90


@lru_cache(maxsize=1)
def vocab():
    p = Path(__file__).resolve().parent.parent.parent / "config" / "logic_sequence.yaml"
    try:
        from app import paths
        p2 = paths.resource("config", "logic_sequence.yaml")
        if p2.exists():
            p = p2
    except Exception:
        pass
    v = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    word_act = {}
    for act, ws in (v.get("actions") or {}).items():
        for w in ws or []:
            word_act[str(w).upper()] = act
    kinds = {}
    for k, ws in (v.get("kinds") or {}).items():
        for w in ws or []:
            kinds[str(w).upper()] = k
    return {"act": word_act, "kind": kinds, "exclude": {str(x).upper() for x in v.get("exclude") or []},
            "status": {str(x).upper() for x in v.get("status_words") or []},
            "negation": {str(x).upper() for x in v.get("negation") or []},
            "order": list((v.get("actions") or {}).keys()),
            "opposites": [tuple(x) for x in v.get("opposites") or [] if isinstance(x, (list, tuple)) and len(x) == 2]}


def _words(t):
    return re.findall(r"[A-Z0-9][A-Z0-9#&./()\-]*", (t or "").upper())


def classify(desc):
    """행 설명 → (동작, 종류, 장비 이름) | None.  동작 낱말이 하나뿐일 때만 (`OPEN/CLOSE` 처럼 둘이면 고르지 않는다)."""
    V = vocab()
    ws = _words(desc)
    if not ws or any(w.strip("()") in V["exclude"] for w in ws):
        return None
    acts = [(i, V["act"][w]) for i, w in enumerate(ws) if w in V["act"]]
    if len({a for _, a in acts}) != 1:
        return None
    act = acts[0][1]
    # L35 — `NO TRIP` · `NOT OPEN` 은 그 동작이 아니라 '그 동작이 없음' 이라는 상태다 (1A1Y `#11 HRSG NO TRIP`: 트립 조건이
    # 하나라도 들어오면 꺼지는 건강 신호 — 동작 학습이 그렇게 읽었다)
    if any(i > 0 and ws[i - 1] in V["negation"] for i, _ in acts):
        return None
    kind = next((V["kind"][w] for w in ws if w in V["kind"]), None)
    if kind is None:
        kind = "state" if any(w in V["status"] for w in ws) else "action"
    drop = {i for i, _ in acts} | {i for i, w in enumerate(ws) if w in V["kind"]}
    equip = " ".join(w for i, w in enumerate(ws) if i not in drop).strip(" -/")
    return act, kind, equip


KIND_RANK = {"command": 0, "request": 1, "action": 2, "state": 3}


def commands(sheets):
    """묶음의 동작 행을 장비마다.  Typical 시트(매크로 안쪽)는 뺀다 — 그 행은 어느 장비의 것도 아니다."""
    typical = {(b.get("macro") or {}).get("page") for s in sheets for b in s["blocks"].values() if b.get("func") == "MACRO"}
    eq = {}
    for s in sheets:
        if s["page"] in typical or s.get("library"):
            continue
        for r in s["rows"]:
            if r["side"] != "R" or r.get("net") is None or not r.get("desc"):
                continue
            c = classify(r["desc"])
            if not c:
                continue
            act, kind, name = c
            name = name or (s.get("title") or s.get("sheet_no") or "")
            key = re.sub(r"[^A-Z0-9]", "", name.upper())
            if not key:
                continue
            e = eq.setdefault(key, {"equip": name, "titles": [], "actions": {}})
            t = s.get("title") or ""
            if t and t not in e["titles"]:
                e["titles"].append(t)
            e["actions"].setdefault(act, []).append({"page": s["page"], "sheet": s.get("sheet_no"), "row": r["n"],
                                                      "desc": r["desc"], "kind": kind, "title": t})
    order = vocab()["order"]
    out = []
    for e in eq.values():
        acts = []
        for a in order:
            items = e["actions"].get(a)
            if items:
                own = lambda x: 0 if re.sub(r"[^A-Z0-9]", "", e["equip"].upper()) in re.sub(
                    r"[^A-Z0-9]", "", (x.get("title") or "").upper()) else 1
                items.sort(key=lambda x: (KIND_RANK.get(x["kind"], 9), own(x), str(x["sheet"]), x["row"]))
                acts.append({"action": a, "rows": items})
        out.append({"equip": e["equip"], "titles": e["titles"][:3], "actions": acts})
    out.sort(key=lambda e: e["equip"])
    return out


GATE_KO = {"and": "AND — 모두 만족", "nand": "NAND", "or": "OR — 하나만 만족하면 됨", "nor": "NOR", "not": "NOT — 반대",
           "memory": "메모리(래치)", "delay_on": "켜짐 지연", "delay_off": "꺼짐 지연", "pulse": "펄스",
           "step": "STEP", "connector": "연결 기호"}


def _row(s, side, n):
    return next((r for r in s["rows"] if r["side"] == side and r["n"] == n), None)


def plan(sheets, page, row, value=1, timers=None):
    """그 시트 그 출력 행이 value 가 되기 위한 조건 나무.

    매크로 상자(MOV · SOV · MOTOR 블록)의 출력은 그 Typical 시트 안의 조건으로 들어가 읽는다 — Typical 의 입력 행은
    상자 입력 단자로 이어져 다시 이 시트의 조건이 되고, Typical 안 누름단추는 펼친 이름(`상자/블록`)으로 강제한다
    (묶음 시뮬레이션이 매크로를 그 이름으로 펼쳐 돌린다 — sim._bundle_run inlined)."""
    by_page = {s["page"]: s for s in sheets}
    s = by_page.get(page)
    if s is None:
        return {"ok": False, "why": "그 쪽은 Logic 표 시트가 아닙니다"}
    r = _row(s, "R", row)
    if r is None or r.get("net") is None:
        return {"ok": False, "why": f"{s.get('sheet_no')} {row}행에 읽힌 출력 선이 없습니다"}
    seq = [0]
    count = [0]
    zero_mode = [False]
    inverted = [False]
    timers = timers or {}
    top = {"s": s, "idx": sim._index(s), "prefix": "", "rowmap": None, "parent": None, "macro": None}
    ctx = {"by_page": by_page}

    def nid():
        seq[0] += 1
        return f"n{page}_{seq[0]}"

    def base(kind, want, text, **kw):
        return {"t": "leaf", "id": nid(), "page": page, "kind": kind, "want": int(want), "text": text, **kw}

    def leaf_of(C, k, w, depth, path):
        sc = C["s"]
        if k.startswith("row:"):
            n = int(k[4:])
            rr = _row(sc, "L", n) or {}
            if C["rowmap"] is not None:
                # Typical 의 입력 행 — 상자의 그 입력 단자 선으로 나가 이 시트의 조건이 된다
                pnet = C["rowmap"].get(n)
                if pnet is None:
                    # 상자에 이 입력의 단자가 없다(그리지 않았거나 못 읽음) — 펼친 매크로 안에서 그 Typical 행의 선은 몰이가
                    # 없는 선이라 직접 답할 수 있다 (L33).  지어낸 연결이 아니라 '사람이 답한 값' 으로 남는다.
                    if rr.get("net") is not None:
                        return base("terminal", w, f"매크로 입력 '{rr.get('desc') or n}' — 상자에 이 단자가 없습니다 (직접 답함)",
                                    key="net:" + C["prefix"] + str(rr["net"]), block=C["macro"],
                                    at=(top["s"]["blocks"].get(C["macro"].split("/")[0]) or {}).get("at"))
                    return base("stuck", w, f"매크로 입력 '{rr.get('desc') or n}' 에 닿는 상자 단자를 읽지 못했습니다",
                                block=C["macro"], at=(C["parent"]["s"]["blocks"].get(C["macro"]) or {}).get("at"))
                sub = expand(C["parent"], ("net", pnet, int(w)), depth + 1, path)
                return {"t": "all", "id": nid(), "page": page, "kids": [sub],
                        "via": {"text": f"매크로 입력 {rr.get('desc') or n}", "want": int(w)}}
            node = base("row", w, rr.get("desc") or f"{n}행", key=k, n=n, fm=rr.get("fm") or "", at=rr.get("at"),
                        kks=rr.get("kks") or "")
            ref = rr.get("ref")
            if ref:
                node["ref"] = {"sheet": ref.get("sheet"), "row": ref.get("src_row") or ref.get("row"),
                               "page": ref.get("page"), "other": bool(ref.get("other_bundle"))}
            ft = rr.get("ft")
            if ft and ft.get("ok") is False:
                node["ft"] = {"why": ft.get("why") or [], "peer": ft.get("peer")}
            elif ref and not ref.get("other_bundle") and ref.get("page") is None:
                node["ft"] = {"why": [f"묶음에 {ref.get('sheet')} 장이 없습니다"], "peer": f"{ref.get('sheet')}-{ref.get('row')}"}
            return node
        if k.startswith("block:"):
            bid = k[6:]
            b = sc["blocks"].get(bid, {})
            at = b.get("at") if not C["prefix"] else (top["s"]["blocks"].get(C["macro"]) or {}).get("at")
            lab = b.get("label") or b.get("func") or bid
            func = (b.get("func") or "").upper()
            kind = "button"
            if "MONITOR" in func:
                kind = "monitor"
                lab = f"감시 블록 {lab} — 아날로그 값이 설정값을 넘으면 1"
            elif "PUSH" in func or "P/B" in func:
                lab = f"누름단추 {lab}"
            elif func:
                lab = f"{lab} ({b.get('func')})" if lab != b.get("func") else lab
            if C["prefix"]:
                lab = f"{lab} (매크로 {C['macro']} 안쪽)"
            return base(kind, w, lab, key="block:" + C["prefix"] + bid, block=C["prefix"] + bid, at=at, func=b.get("func"))
        net = k[4:]
        if C["prefix"] or "/" in net:
            return base("held", w, f"매크로 안쪽 선 — 몰이를 도면에서 읽지 못했습니다 (매크로 {C['macro'] or ''} 의 Typical)",
                        key="net:" + C["prefix"] + net)
        return base("net", w, "도면에서 몰이를 읽지 못한 선", key=k, net=net)

    def gate_label(C, x):
        b = C["s"]["blocks"].get(x, {})
        lg = b.get("logic")
        lab = GATE_KO.get(lg) or (b.get("func") or "블록")
        if lg in ("delay_on", "delay_off", "pulse"):
            t = sim.timer_seconds(b, (timers.get(str(page)) or {}).get(C["prefix"] + x))
            lab = f"{lab} {t:g}초"
        vote = sim._vote_of(b)
        if vote:
            lab = f"투표 {vote[0]}/{vote[1]} — {vote[0]}개 이상"
        if C["prefix"]:
            lab += " (매크로 안쪽)"
        return lab, b

    def macro_node(C, x, want, onet, depth, path):
        b = C["s"]["blocks"][x]
        m = b.get("macro") or {}
        ts = by_page.get(m.get("page"))
        out = next((o for o in m.get("outputs", []) if o.get("net") == onet and o.get("row") is not None), None)
        direct = "net:" + C["prefix"] + str(onet)      # 매크로 안을 못 읽으면 그 출력 단자 선에 직접 답한다 (몰이가 없는 선)
        if ts is None or out is None:
            return base("stuck", want, "이 매크로 출력의 Typical 시트를 잇지 못했습니다 — 매크로 출력에 직접 답합니다",
                        block=C["prefix"] + x, at=b.get("at"), key=direct)
        rowmap = {i["row"]: i["net"] for i in m.get("inputs", []) if i.get("row") is not None and i.get("net") is not None}
        tr = _row(ts, "R", out["row"])
        if tr is None or tr.get("net") is None:
            return base("stuck", want, f"Typical {m.get('sheet')} {out['row']}행에 출력 선이 없습니다 — 매크로 출력에 직접 답합니다",
                        block=C["prefix"] + x, at=b.get("at"), key=direct)
        IC = {"s": ts, "idx": sim._index(ts), "prefix": C["prefix"] + x + "/", "rowmap": rowmap, "parent": C, "macro": x}
        inner = expand(IC, ("net", tr["net"], int(want)), depth + 1, path)
        return {"t": "all", "id": nid(), "page": page, "kids": [inner],
                "gate": {"block": C["prefix"] + x, "label": f"매크로 {m.get('title') or ''} — Typical {m.get('sheet') or '?'} "
                         f"'{out.get('desc') or out.get('pin')}' 의 조건", "func": "MACRO", "logic": None,
                         "at": b.get("at") if not C["prefix"] else None, "want": int(want)}}

    memo = {}

    def expand(C, goal, depth, path):
        # 같은 선 · 같은 값은 나무의 다른 자리에 또 나와도 한 마디다 (같은 id — 한 번 답하면 그 자리 모두 답한 것).
        # 메모리 · OR 가 같은 조건을 여러 갈래에서 다시 부르는 Typical 에서 나무가 폭발하지 않게.
        if goal[0] == "net":
            mk = (C["prefix"], goal[1], int(goal[2]), zero_mode[0])
            if mk in memo:
                return memo[mk]
            node = _expand(C, goal, depth, path)
            memo[mk] = node
            return node
        return _expand(C, goal, depth, path)

    def _expand(C, goal, depth, path):
        count[0] += 1
        want = int(goal[2])
        if count[0] > NODE_LIMIT or depth > DEPTH_LIMIT:
            return base("deep", want, "조건이 너무 깊습니다 — 여기부터는 도면에서 확인")
        if goal[0] == "net":
            key = (C["prefix"], goal[1], want)
            if key in path:
                return base("loop", want, "되먹임 — 앞 단계에서 정해집니다", auto=True)
            path = path | {key}
            if want == 0 and not zero_mode[0] and not sim._inverting(C["s"], C["idx"], goal[1]):
                # 0 이어야 하는 자리 (고장 없음 · 트립 없음 · 반대 명령 없음) — 아무것도 주지 않으면 0 이다.
                # 하나씩 묻지 않고 '이 신호들이 없어야 합니다' 한 단계로 접는다 (시뮬레이터 _solutions 와 같은 생각)
                zero_mode[0] = True
                inverted[0] = False
                try:
                    sub = expand(C, goal, depth, path - {key})
                finally:
                    zero_mode[0] = False
                if inverted[0]:
                    # 그 아래에 NOT · NOR · NAND 가 있으면 '아무것도 주지 않으면 0' 이 아니다 — 접지 않고 하나씩 묻는다
                    return sub
                items, seen_k = [], set()
                for lf in _first_leaves(sub):
                    if lf.get("key") and lf.get("kind") in ("row", "button", "monitor", "net", "terminal") and lf["key"] not in seen_k:
                        seen_k.add(lf["key"])
                        items.append({k: lf.get(k) for k in ("key", "text", "want", "at", "fm", "ref", "ft", "n", "block")})
                return base("zero", 0, "이 신호들이 없어야 합니다 (아무것도 주지 않으면 0)", items=items, auto=not items,
                            net="net:" + C["prefix"] + goal[1])
        gate = goal[1][1] if goal[0] == "drv" and goal[1][0] == "block" else None
        if gate and zero_mode[0]:
            gl = C["s"]["blocks"].get(gate, {}).get("logic")
            if gl in ("not", "nor", "nand") or (gl == "memory" and goal[1][2] == "qn"):
                inverted[0] = True
        if gate and C["s"]["blocks"].get(gate, {}).get("func") == "MACRO":
            if want == 0:
                return base("default0", 0, "아무것도 주지 않으면 0 입니다", auto=True)
            return macro_node(C, gate, want, goal[3], depth, path)
        try:
            opts = sim._back_options(C["s"], C["idx"], goal, True, {**ctx, "rows_only": False})
        except Exception:
            opts = []
        if not opts:
            onet = goal[1] if goal[0] == "net" else goal[3]
            gb = C["s"]["blocks"].get(gate, {}) if gate else {}
            short_gate = gb.get("logic") in sim.MIN_INPUTS or bool(sim._vote_of(gb))
            what = (f"{GATE_KO.get(gb.get('logic')) or gb.get('func') or '게이트'} 의 입력선을 도면에서 다 읽지 못했습니다"
                    if short_gate else f"판정 못 한 블록 '{gb.get('label') or gb.get('func') or '?'}' 이 이 값을 냅니다"
                    if gate else "이 값을 내는 조건을 범례 정의로 찾지 못했습니다")
            # 짧은 게이트는 'hold:' — 읽힌 입력이 출력을 정하면 게이트가 이긴다 (sim L32) · 판정 못 한 블록은 그 선을 직접
            n = base("stuck", want, what, key=("hold:" if short_gate else "net:") + C["prefix"] + str(onet))
            if gate:
                n["block"] = C["prefix"] + gate
                n["at"] = C["s"]["blocks"].get(gate, {}).get("at") if not C["prefix"] else None
            return n
        kids = []
        for add, sub in opts:
            parts = [leaf_of(C, k, w, depth, path) for k, w in add.items()]
            parts += [expand(C, g, depth + 1, path) for g in sub]
            if not parts:
                continue
            kids.append(parts[0] if len(parts) == 1 else {"t": "all", "id": nid(), "page": page, "kids": _order(parts)})
        if not kids:
            node = base("const", want, "언제나 만족 (조건 없음)", auto=True)
        elif len(kids) == 1:
            node = kids[0]
        elif want == 0 and all(_all_want0(k) for k in kids):
            # 0 이 되면 되는 자리 (AND=0 — 하나만 0) — 아무것도 주지 않으면 대개 0 이다.  묻지 않는다.
            node = base("default0", 0, "아무것도 주지 않으면 0 입니다", auto=True)
        else:
            node = {"t": "any", "id": nid(), "page": page, "kids": kids}
        if gate and C["s"]["blocks"].get(gate, {}).get("logic") != "source":
            lab, b = gate_label(C, gate)
            wrap = node if node["t"] != "leaf" and "gate" not in node else {"t": "all", "id": nid(), "page": page, "kids": [node]}
            wrap["gate"] = {"block": C["prefix"] + gate, "label": lab, "func": b.get("func"), "logic": b.get("logic"),
                            "at": b.get("at") if not C["prefix"] else None, "want": want}
            node = wrap
        return node

    tree = expand(top, ("net", r["net"], int(value)), 0, frozenset())
    _finish(tree)
    flat = {}

    def flatten(n):
        if n["id"] in flat:
            return n["id"]
        d = {k: v for k, v in n.items() if k != "kids"}
        flat[n["id"]] = d
        if "kids" in n:
            d["kids"] = [flatten(k) for k in n["kids"]]
        return n["id"]
    root = flatten(tree)
    # 같은 마디가 여러 자리에 나오므로 나무를 펼쳐 보내지 않고 마디 표 + id 로 보낸다 (화면이 다시 잇는다)
    return {"ok": True, "page": page, "sheet": s.get("sheet_no"), "row": row, "desc": r.get("desc"), "net": r["net"],
            "value": int(value), "title": s.get("title"), "root": root, "nodes": flat, "size": count[0],
            "truncated": count[0] > NODE_LIMIT}


def link(p):
    """마디 표 → 나무 (같은 id 는 같은 객체).  시험 · 도구용."""
    if not p.get("ok"):
        return None
    N = {k: dict(v) for k, v in p["nodes"].items()}
    for v in N.values():
        if "kids" in v:
            v["kids"] = [N[i] for i in v["kids"]]
    return N[p["root"]]


ASK = ("row", "button", "monitor", "net", "held", "terminal", "stuck", "zero", "deep")


def _first_leaves(n):
    """나무의 잎 — ANY 는 첫 갈래만."""
    if n["t"] == "leaf":
        return [n]
    kids = n.get("kids") or []
    if n["t"] == "any":
        kids = kids[:1]
    return [x for k in kids for x in _first_leaves(k)]


def _finish(n):
    """마디마다 — 갈 수 있는가(viable: 범례로 찾지 못한 자리가 꼭 거쳐야 하는 길에 없음) · 묻는 수 · 한 줄 요약 ·
    ANY 의 권하는 갈래 (갈 수 있는 것 중 묻는 수가 가장 적은 것)."""
    if n["t"] == "leaf":
        # 되먹임으로 1 을 바라는 자리는 처음 상태에서 서지 않는다 (래치가 이미 켜져 있을 때만) — 권하지 않는다
        n["viable"] = n.get("kind") not in ("stuck", "deep") and not (n.get("kind") == "loop" and n.get("want") == 1)
        n["asks"] = 0 if n.get("auto") else 1
        if n.get("kind") == "loop" and n.get("want") == 1:
            n["summary"] = ["되먹임 — 이미 켜져 있을 때만 (처음 상태에서는 서지 않음)"]
        else:
            n["summary"] = [] if n.get("auto") or n.get("kind") == "zero" else [n.get("text") or ""]
        return n
    for k in n["kids"]:
        _finish(k)
    if n["t"] == "all":
        n["viable"] = all(k["viable"] for k in n["kids"])
        n["asks"] = sum(k["asks"] for k in n["kids"])
        n["summary"] = [x for k in n["kids"] for x in k["summary"]][:4]
    else:
        ok = [i for i, k in enumerate(n["kids"]) if k["viable"]]
        pick = min(ok or range(len(n["kids"])), key=lambda i: n["kids"][i]["asks"])
        n["pick"] = pick
        n["viable"] = bool(ok)
        n["asks"] = 1 + n["kids"][pick]["asks"]
        n["summary"] = n["kids"][pick]["summary"]
    return n


def _all_want0(n):
    if n["t"] == "leaf":
        return n.get("want") == 0
    return all(_all_want0(k) for k in n.get("kids") or [])


def _order(parts):
    """한 무리 안에서 묻는 순서 — 조건(1) · 다른 시트에서 오는 것 → 하위 조건 → 없어야 하는 것(0) → 누름단추(명령) 마지막."""
    def rank(n):
        if n["t"] != "leaf":
            return 1
        if n.get("kind") == "button":
            return 3
        if n.get("want") == 0:
            return 2
        return 0
    return sorted(parts, key=rank)
