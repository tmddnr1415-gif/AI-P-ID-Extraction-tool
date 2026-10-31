"""L84 — 분석 시트에서 들여온 그림의 선을 **연결은 그대로 두고** 적은 선으로 다시 묶는다 (작도 화면을 가볍게).

분석 결과의 그물은 선분 기록이라, 들여오면 토막마다 선 하나가 된다 (draw.from_sheet).  19VA 0007 은 3,549선 —
파선 틀 하나가 토막 854개, 같은 토막이 두 번 적힌 것, 접합 없이 이어진 토막들.  화면은 선마다 SVG 서너 개를 그리므로
그만큼 무겁다.

묶는 규칙 (같은 분석 그물 `n<그물>_<k>` 안에서만):
  1. 같은 토막이 두 번 — 하나만 남긴다 (연결점 · 표시는 남은 것에 옮긴다).
  2. 두 선의 끝이 한 점에서 만나고 그 점에 다른 것이 없으면(다른 선 끝 · 몸통 · 연결점 · 단자 · 행 자리 · 화살촉) 한 선으로 잇는다.
  3. 파선 — 같은 직선 위로 틈(그 토막 길이 안)을 두고 이어지는 토막들은 한 파선으로 (화면은 무늬로 그린다).
     모서리에서 꺾여 이어지는 파선 틀도 한 선.

**판정 불변** — 묶기 전과 뒤를 시뮬레이터 꼴(draw_sim.to_sheet)로 바꿔, 단자 · 행이 어느 그물에 붙는지가 같은지 본다.
다르면 그 그물은 묶지 않고 다시 한다 (값 하나라도 다르면 원래 그림 그대로).
"""
from __future__ import annotations

import math
import re
from collections import defaultdict

JOIN = 0.6                   # draw_sim.JOIN 과 같은 뜻 — 선 끝 맞닿음
TOL = 2.5                    # draw_sim.TOL — 단자 · 행 자리
_ID = re.compile(r"^n([^_]+)_\d+$")
VERSION = 1


_GRP: dict = {}


def _grp(w):
    i = w.get("id")
    g = _GRP.get(i, 0)
    if g == 0:
        m = _ID.match(str(i or ""))
        g = _GRP[i] = m.group(1) if m else None
        if len(_GRP) > 200000:
            _GRP.clear()
    return g


def _d(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _dir(pts, at_start):
    """끝에서 몸통 쪽 단위 방향."""
    a, b = (pts[0], pts[1]) if at_start else (pts[-1], pts[-2])
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy) or 1.0
    return dx / n, dy / n


def _seglen(pts, at_start):
    a, b = (pts[0], pts[1]) if at_start else (pts[-1], pts[-2])
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _on_seg(p, a, b, tol):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    if L2 < 1e-9:
        return _d(p, a) <= tol
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2
    t = max(0.0, min(1.0, t))
    return math.hypot(a[0] + t * dx - p[0], a[1] + t * dy - p[1]) <= tol


def _axial(w):
    """가로 · 세로 토막만으로 된 선 — 기운 획(화살촉 · 기호 외곽)은 묶지 않는다 (draw.orthogonal_wires 가 기운 토막을 ㄱ 으로 고친다)."""
    return all(abs(a[0] - b[0]) < 0.05 or abs(a[1] - b[1]) < 0.05 for a, b in zip(w["pts"], w["pts"][1:]))


def _simplify(pts):
    """한 직선 위 가운데 꼭짓점 · 겹친 점을 뺀다."""
    out = []
    for p in pts:
        p = [round(p[0], 2), round(p[1], 2)]
        if out and _d(out[-1], p) < 0.01:
            continue
        while len(out) >= 2:
            a, b = out[-2], out[-1]
            cross = (b[0] - a[0]) * (p[1] - b[1]) - (b[1] - a[1]) * (p[0] - b[0])
            dot = (b[0] - a[0]) * (p[0] - b[0]) + (b[1] - a[1]) * (p[1] - b[1])
            if abs(cross) < 0.05 * max(1.0, math.hypot(p[0] - a[0], p[1] - a[1])) and dot > 0:
                out.pop()
            else:
                break
        out.append(p)
    return out


class _Idx:
    """점 · 선분 칸 색인 (8pt 칸)."""
    C = 8.0

    def __init__(self):
        self.cells = defaultdict(list)

    def add_pt(self, p, v):
        self.cells[(int(p[0] // self.C), int(p[1] // self.C))].append(v)

    def add_box(self, x0, y0, x1, y1, v):
        C = self.C
        for cx in range(int(min(x0, x1) // C), int(max(x0, x1) // C) + 1):
            for cy in range(int(min(y0, y1) // C), int(max(y0, y1) // C) + 1):
                self.cells[(cx, cy)].append(v)

    def near(self, p, r=1):
        C = self.C
        gx, gy = int(p[0] // C), int(p[1] // C)
        cells = self.cells
        if r == 1:
            out = []
            for cx in (gx - 1, gx, gx + 1):
                for cy in (gy - 1, gy, gy + 1):
                    v = cells.get((cx, cy))
                    if v:
                        out += v
            return out
        out = []
        for cx in range(gx - r, gx + r + 1):
            for cy in range(gy - r, gy + r + 1):
                v = cells.get((cx, cy))
                if v:
                    out += v
        return out


def _fixed_points(doc):
    """단자 · 행 자리 — 여기서는 선을 잇지 않는다 (단자는 선 끝을 먼저 찾는다)."""
    from . import draw as D
    pts = []
    for b in doc.get("blocks") or []:
        if b.get("kind") in D.SYMBOLS:
            try:
                pts += [(q[0], q[1]) for q in D.ports_of(b)]
            except Exception:
                pass
    boxes = []
    for b in doc.get("blocks") or []:                 # 상자 변 · 입력 막대 — 선 끝이 닿은 자리가 곧 단자다 (draw_sim.to_sheet)
        if b.get("kind") in D.SYMBOLS and b.get("kind") != "TEXT" and b.get("w") and b.get("h"):
            x0, y0, x1, y1 = b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]
            if D.SYMBOLS[b["kind"]].get("bar"):
                try:
                    br = D.bar_of(b)
                    x0, y0, x1, y1 = min(x0, br[0]), min(y0, br[1]), max(x1, br[2]), max(y1, br[3])
                except Exception:
                    pass
            boxes.append((x0, y0, x1, y1))
    N = int(doc.get("N") or D.N_DEFAULT)
    for n in range(1, N + 1):
        y = D.ry(n, N)
        pts += [(D.LX0, y), (D.LX1, y)]
    return pts, boxes


def _merge_pass(wires, keep_groups, fixed):
    """한 번 훑어 묶을 수 있는 것을 다 묶는다.  wires 는 고쳐 쓴다 (None = 지워짐)."""
    # 1) 같은 토막 두 번
    seen = {}
    for i, w in enumerate(wires):
        g = _grp(w)
        if g is None or g in keep_groups or len(w["pts"]) != 2:
            continue
        a, b = tuple(round(v, 2) for v in w["pts"][0]), tuple(round(v, 2) for v in w["pts"][1])
        k = (g, bool(w.get("dashed")), min(a, b), max(a, b))
        j = seen.get(k)
        if j is None:
            seen[k] = i
            continue
        keep = wires[j]
        marked = lambda x: x.get("arrow") or x.get("label") or x.get("marks")
        if marked(w) and marked(keep):
            continue                                      # 둘 다 표시가 있으면 둘 다 둔다
        if marked(w):
            keep, w = w, keep                             # 표시가 있는 쪽을 남긴다 (자리 j)
            wires[j] = keep
        d0 = keep.get("dots") or []
        extra = [d for d in (w.get("dots") or []) if d not in d0]
        if extra:
            keep["dots"] = d0 + extra
        keep["_src"] = keep.get("_src", []) + w.get("_src", [])
        wires[i] = None
    # 1b) 같은 직선 위 다른 토막 안에 통째로 든 토막 (화살촉 · 겹쳐 적힌 토막) — 큰 쪽에 맡긴다
    segs = _Idx()
    two = [i for i, w in enumerate(wires) if w is not None and len(w["pts"]) == 2 and _grp(w) is not None and _grp(w) not in keep_groups]
    for i in two:
        a, b = wires[i]["pts"]
        segs.add_box(a[0], a[1], b[0], b[1], i)
    for i in sorted(two, key=lambda i: math.hypot(wires[i]["pts"][1][0] - wires[i]["pts"][0][0], wires[i]["pts"][1][1] - wires[i]["pts"][0][1])):
        w = wires[i]
        if w is None or w.get("arrow") or w.get("label") or w.get("marks"):
            continue
        a, b = w["pts"]
        for j in segs.near(a):
            o = wires[j]
            if j == i or o is None or _grp(o) != _grp(w) or bool(o.get("dashed")) != bool(w.get("dashed")):
                continue
            c, d = o["pts"]
            if _on_seg(a, c, d, 0.05) and _on_seg(b, c, d, 0.05):
                extra = [x for x in (w.get("dots") or []) if x not in (o.get("dots") or [])]
                if extra:
                    o["dots"] = (o.get("dots") or []) + extra
                o["_src"] = o.get("_src", []) + w.get("_src", [])
                wires[i] = None
                break
    live = [i for i, w in enumerate(wires) if w is not None]

    # 색인 — 모든 선의 끝 · 몸통 · 연결점
    ends = _Idx()
    body = _Idx()
    dots = []
    for i in live:
        w = wires[i]
        ends.add_pt(w["pts"][0], (i, 0))
        ends.add_pt(w["pts"][-1], (i, 1))
        for a, b in zip(w["pts"], w["pts"][1:]):
            body.add_box(a[0], a[1], b[0], b[1], i)
        dots += [tuple(d) for d in (w.get("dots") or [])]
    dot_idx = _Idx()
    for d in dots:
        dot_idx.add_pt(d, d)
    fixed, boxes = fixed
    fix_idx = _Idx()
    for p in fixed:
        fix_idx.add_pt(p, p)
    box_idx = _Idx()
    for bx in boxes:
        box_idx.add_box(bx[0] - TOL, bx[1] - TOL, bx[2] + TOL, bx[3] + TOL, bx)

    def busy(p, me, other, gap=0.0):
        """점 p 에 묶을 두 선 말고 다른 것이 있는가 (끝 · 몸통 · 연결점 · 단자 · 행)."""
        if any(_d(d, p) <= 1.0 + gap for d in dot_idx.near(p)):
            return True
        if any(_d(q, p) <= TOL + gap for q in fix_idx.near(p)):
            return True
        m = TOL + 0.5 + gap
        if any(bx[0] - m <= p[0] <= bx[2] + m and bx[1] - m <= p[1] <= bx[3] + m for bx in box_idx.near(p)):
            return True
        for j, k in ends.near(p):
            if j in (me, other) or wires[j] is None:
                continue
            q = wires[j]["pts"][0 if k == 0 else -1]
            if _d(q, p) <= JOIN + gap:
                return True
        for j in set(body.near(p)):
            if j in (me, other) or wires[j] is None:
                continue
            pts = wires[j]["pts"]
            if any(_on_seg(p, a, b, JOIN + gap) for a, b in zip(pts, pts[1:])):
                return True
        return False

    def cands(i, k):
        """끝 (i, k) 에 이을 수 있는 같은 그물의 끝들."""
        w = wires[i]
        if not _axial(w):
            return []
        g, dashed = _grp(w), bool(w.get("dashed"))
        pts = w["pts"]
        e = pts[0] if k == 0 else pts[-1]
        ux, uy = _dir(pts, k == 0)
        L = w.get("_dl") or _seglen(pts, k == 0)          # 파선 무늬 길이 — 묶기 전 토막 길이 (묶은 긴 선의 끝 토막 길이가 아니라)
        out, seen_ = [], set()
        r = 1 if not dashed else 1 + int((L + JOIN) // _Idx.C)
        for j, kk in ends.near(e, r):
            if j == i or wires[j] is None or (j, kk) in seen_:
                continue
            seen_.add((j, kk))                             # 이은 선은 색인에 새 끝이 더 들어가 있다
            o = wires[j]
            if _grp(o) != g or bool(o.get("dashed")) != dashed or not _axial(o):
                continue
            q = o["pts"][0] if kk == 0 else o["pts"][-1]
            vx, vy = _dir(o["pts"], kk == 0)
            if ux * vx + uy * vy > 0.5:                    # 되접힘 — 두 토막이 겹친다 (잇지 않는다)
                continue
            if _d(q, e) <= JOIN:
                out.append((j, kk, 0.0))
                continue
            if not dashed:
                continue
            # 파선 틈 — 같은 직선 · 반대 방향 · 틈은 두 토막 중 긴 쪽 길이 안
            ahead = (e[0] - q[0]) * ux + (e[1] - q[1]) * uy
            side = abs((q[0] - e[0]) * uy - (q[1] - e[1]) * ux)
            if side <= JOIN and 0 < ahead <= max(L, o.get("_dl") or _seglen(o["pts"], kk == 0)) + JOIN and ux * vx + uy * vy < -0.98:
                out.append((j, kk, ahead))
        touch = [c for c in out if c[2] == 0.0]
        return touch or out                                # 맞닿은 토막이 있으면 그것 (틈을 메운 토막이 따로 적힌 파선)

    merged = 0
    for i in live:
        for k in (0, 1):
            w = wires[i]
            if w is None:
                break
            if (w.get("arrow") == ("start" if k == 0 else "end")) or len(w["pts"]) < 2 or _grp(w) in keep_groups:
                continue
            c = cands(i, k)
            if len(c) != 1:
                continue
            j, kk, gap = c[0]
            o = wires[j]
            if o.get("arrow") == ("start" if kk == 0 else "end"):
                continue
            back = cands(j, kk)
            if len(back) != 1 or back[0][0] != i:
                continue
            e = w["pts"][0] if k == 0 else w["pts"][-1]
            q = o["pts"][0] if kk == 0 else o["pts"][-1]
            mid = ((e[0] + q[0]) / 2, (e[1] + q[1]) / 2)
            if busy(e, i, j) or busy(q, i, j) or (gap > JOIN and busy(mid, i, j, gap / 2)):
                continue
            if (w.get("label") and o.get("label")) or (w.get("arrow") and o.get("arrow")):
                continue
            # 잇기 — w 의 끝 k 뒤에 o 를 붙인다 (w 를 남긴다)
            a = w["pts"] if k == 1 else w["pts"][::-1]
            b = o["pts"] if kk == 0 else o["pts"][::-1]
            pts = _simplify(a + b)
            if len(pts) < 2:
                continue
            arrow = None                                   # 화살촉은 이은 자리가 아닌 끝에만 있다 (위에서 걸렀다)
            if w.get("arrow"):                             # a = w (k=1 이면 그대로 · k=0 이면 뒤집음) → w 의 남은 끝이 새 선의 처음
                arrow = "start"
            if o.get("arrow"):                             # b = o 의 남은 끝이 새 선의 끝
                arrow = "end" if not arrow else None       # 두 끝 다 화살촉이면 하나로 못 적는다 — 아래에서 거른다
            nw = {kx: v for kx, v in w.items() if kx not in ("pts", "arrow", "dots", "marks", "label")}
            nw["pts"] = pts
            nw["_src"] = w.get("_src", []) + o.get("_src", [])
            nw["fx"] = 1
            if w.get("dashed"):
                nw["_dl"] = max(w.get("_dl") or _seglen(w["pts"], True), o.get("_dl") or _seglen(o["pts"], True))
            if arrow:
                nw["arrow"] = arrow
            for f in ("dots", "marks"):
                v = (w.get(f) or []) + (o.get(f) or [])
                if v:
                    nw[f] = v
            lab = w.get("label") or o.get("label")
            if lab:
                nw["label"] = lab
            wires[i] = nw
            wires[j] = None
            # 색인 고침 — 새 끝을 넣는다 (지운 선은 None 이라 건너뛴다)
            ends.add_pt(nw["pts"][0], (i, 0))
            ends.add_pt(nw["pts"][-1], (i, 1))
            for a_, b_ in zip(o["pts"], o["pts"][1:]):           # w 의 토막은 이미 i 로 들어 있다 · o 의 것만 i 로 (틈은 아래 한 줄)
                body.add_box(a_[0], a_[1], b_[0], b_[1], i)
            body.add_box(e[0], e[1], q[0], q[1], i)
            merged += 1
    return merged


def _pkey(p):
    """단자 열쇠 — 상자 변에 닿은 단자의 자리는 그 변에 먼저 닿은 선 끝이라 선 차례에 따라 달라진다 (뜻은 같다).
    같은 그물 · 같은 방향의 단자는 블록마다 하나만 적히므로(to_sheet 의 seen) 변도 그 차례를 따른다 — 블록 · 방향 · 역할 · 핀 · 칸으로 견준다."""
    return ("p", p["block"], p["dir"], p.get("role") or "", p.get("pin") or "", p.get("cell") or 0)


def _signature(doc, wires):
    """시뮬레이터가 보는 연결 — 단자 · 행을 그물별로 묶은 것 (그물 이름과 무관하게 견준다)."""
    from . import draw_sim as DS
    d = dict(doc)
    d["wires"] = wires
    s = DS.to_sheet(d, 1, {})
    by = defaultdict(set)
    for p in s["ports"]:
        by[p["net"]].add(_pkey(p))
    for r in s["rows"]:
        if r.get("net") is not None:
            by[r["net"]].add(("r", r["side"], r["n"]))
    dashed = {k: bool(v.get("dashed")) for k, v in s["nets"].items()}
    sig = frozenset((frozenset(v), dashed.get(k, False)) for k, v in by.items())
    ranges = tuple(sorted((r["side"], r["n"], (r.get("range") or {}).get("text", "")) for r in s["rows"]))
    return sig, ranges, s, None


def _wire_nets(wires):
    """원래 선 id → 그물 번호 (선 목록의 _src 로 펼친다)."""
    from . import draw_sim as DS
    blocks = _BLOCKS.get("b") or []
    ws = DS._drop_inside([w for w in wires if len(w.get("pts") or []) >= 2], blocks)
    net_of, _ = DS._nets_of(ws)
    out = {}
    for i, w in enumerate(ws):
        for sid in w.get("_src") or [w["id"]]:
            out[sid] = net_of[i]
    return out


_BLOCKS: dict = {}


def _straight(ws, doc):
    from . import draw as D
    try:
        for _ in range(3):
            nx = D.orthogonal_wires(ws, blocks=doc.get("blocks") or [])
            if [w["pts"] for w in nx] == [w["pts"] for w in ws]:
                break
            ws = nx
    except Exception:
        pass
    return ws


def compact(doc: dict) -> tuple[list, dict]:
    """그림 → (묶은 선 목록, 보고).  연결이 하나라도 달라지면 그 분석 그물은 묶지 않고 다시 · 끝내 다르면 원래 선 목록."""
    orig = [dict(w) for w in (doc.get("wires") or []) if len(w.get("pts") or []) >= 2]
    rep = {"before": len(doc.get("wires") or []), "after": len(doc.get("wires") or []), "kept_groups": 0, "ok": True}
    if not any(_grp(w) is not None for w in orig) or len({w.get("id") for w in orig}) != len(orig):
        return doc.get("wires") or [], rep
    for w in orig:
        w["_src"] = [w["id"]]
    fixed = _fixed_points(doc)
    _BLOCKS["b"] = doc.get("blocks") or []
    n0 = _wire_nets(orig)
    sig0, rng0, s0, _ = _signature(doc, orig)
    gid = {w["id"]: _grp(w) for w in orig}
    # 화면은 예전 그림을 받을 때 선을 곧게 편다 (draw.orthogonal_wires · L64).  편 모양에서 묶는다 — 묶은 뒤에 펴면 가운데가 된
    # 꼭짓점이 끝점과 달리 움직여 다른 선에 닿을 수 있다.  묶은 그림은 받을 때 다시 펴지 않는다 (draw_api.get_drawing).
    st = _straight([dict(w, pts=[list(p) for p in w["pts"]]) for w in orig], doc)
    if _wire_nets(st) == n0 and _signature(doc, st)[:2] == (sig0, rng0):
        orig = st

    def attempt(keep):
        """keep 의 그룹은 묶지 않고 한 번 — (선 목록, 같은가, 다르게 된 그룹들)."""
        ws = [dict(w, pts=[list(p) for p in w["pts"]]) for w in orig]
        for _ in range(6):
            if not _merge_pass(ws, keep, fixed):
                break
            ws = [w for w in ws if w is not None]
        ws = [w for w in ws if w is not None]
        n1 = _wire_nets(ws)
        # 선 단위로 견준다 — 묶은 뒤 한 그물에 묶기 전 그물 둘 이상이 섞였거나, 묶기 전 한 그물이 갈라졌으면 그 선들의 그룹
        after = defaultdict(set)
        before = defaultdict(set)
        for sid, a_ in n1.items():
            after[a_].add(n0.get(sid))
            before[n0.get(sid)].add(a_)
        mixed_a = {x for x, bs in after.items() if len(bs) > 1}
        split_b = {x for x, as_ in before.items() if len(as_) > 1}
        bad_ids = set(n1) ^ set(n0)
        for sid in n1:
            if n1[sid] in mixed_a or n0.get(sid) in split_b:
                bad_ids.add(sid)
        groups = {gid.get(x) for x in bad_ids} - {None}
        if groups:
            return ws, False, groups
        sig1, rng1, s1, _ = _signature(doc, ws)
        if sig1 == sig0 and rng1 == rng0:
            return ws, True, set()
        # 선은 같은데 단자 · 행이 다르다 — 그 단자 · 행이 붙은 그물(묶기 전 · 뒤)을 이루는 원래 선들의 그룹
        want = {frozenset(m) for m, _ in sig0}
        have = {frozenset(m) for m, _ in sig1}
        src_of = {w["id"]: w.get("_src") or [w["id"]] for w in ws}
        for k, net in s1["nets"].items():
            if _members(s1, k) and frozenset(_members(s1, k)) not in want:
                for wid in net.get("wires") or []:
                    groups |= {gid.get(x) for x in src_of.get(wid, [wid])}
        for k, net in s0["nets"].items():
            if _members(s0, k) and frozenset(_members(s0, k)) not in have:
                groups |= {gid.get(x) for x in net.get("wires") or []}
        groups.discard(None)
        return ws, False, groups

    def done(ws, keep):
        for w in ws:
            w.pop("_src", None)
            w.pop("_dl", None)
        rep.update(after=len(ws), kept_groups=len(keep))
        return ws, rep

    keep = set()
    for _ in range(12):
        ws, ok, groups = attempt(keep)
        if ok:
            return done(ws, keep)
        if not groups - keep:
            break
        keep |= groups
    # 곧게 펴기는 그림 전체의 좌표를 모으므로 다른 그룹을 묶은 것이 여기에 번질 수 있다 — 묶인 그룹을 반씩 덜어 가며 찾는다
    merged = sorted({gid.get(s_) for w in ws for s_ in (w.get("_src") or []) if len(w.get("_src") or []) > 1} - keep - {None}, key=str)
    if merged and attempt(keep | set(merged))[1]:
        cand = merged
        while len(cand) > 1:
            h = len(cand) // 2
            if attempt(keep | set(cand[:h]))[1]:
                cand = cand[:h]
            elif attempt(keep | set(cand[h:]))[1]:
                cand = cand[h:]
            else:
                break
        keep |= set(cand)
        ws, ok, _ = attempt(keep)
        if ok:
            return done(ws, keep)
    rep.update(ok=False)
    return doc.get("wires") or [], rep


def _members(s, net):
    out = set()
    for p in s["ports"]:
        if p["net"] == net:
            out.add(_pkey(p))
    for r in s["rows"]:
        if r.get("net") == net:
            out.add(("r", r["side"], r["n"]))
    return out


def imported(doc: dict) -> bool:
    """분석에서 들여온 선(`n<그물>_<k>`)이 있는 그림."""
    return any(_grp(w) is not None for w in doc.get("wires") or [])


def compact_doc(doc: dict) -> dict:
    """그림을 고쳐 쓴다 (선만) — `compact` 표시를 남겨 다시 하지 않는다."""
    if (doc.get("compact") or 0) >= VERSION:
        return {"skipped": True}
    ws, rep = compact(doc)
    if rep.get("ok") and rep["after"] < rep["before"]:
        doc["wires"] = ws
    doc["compact"] = VERSION
    return rep
