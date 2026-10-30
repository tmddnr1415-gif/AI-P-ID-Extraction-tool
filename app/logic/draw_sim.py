"""L57 — LOGIC 작도 그림을 **PDF 로 내보내 다시 읽지 않고** 분석 결과 시트 꼴로 바꿔 시뮬레이터에 바로 넣는다.

작도 화면이 그린 것(블록 · 선 · 표 행 · 매크로)은 전부 자리와 종류를 알고 있다 — 분석기가 그림에서 어림해 읽는 일을
여기서는 할 필요가 없고, 선이 어느 단자 · 어느 행에 닿았는지만 세면 `sim.simulate_bundle` 이 받는 꼴(blocks · ports ·
nets · rows · table)이 된다.  **판정은 전부 `sim` · `analog` · `aops` · `fromto` 가 한다** — 여기는 꼴을 바꾸기만 한다.

규칙 (분석기 geom/graph 가 그림에서 읽는 규칙과 같은 뜻):
  · 선끼리는 끝이 맞닿거나 · 끝이 다른 선의 몸통 위에 있거나(T) · 연결점(dot)이 몸통 위에 있을 때 한 그물.  지나치는 교차는 연결 아님.
  · 선 끝이 블록 단자(`draw.ports_of`) 2.5pt 안이면 그 단자 · LOGIC 영역 왼쪽 끝(LX0)의 행 가운데면 왼쪽 행 · 오른쁜 끝(LX1)이면 오른쪽 행.
  · 매크로 상자의 단자는 Typical 시트(같은 묶음의 그림 · `param.typ` = 시트 이름)의 행 번호(`pins[].row`)로 바로 잇는다 (macro.link 불필요).
  · 글자 상자(BOX)의 뜻은 분석기와 같은 `blocks.isa_word` 로 — 모르는 글자는 '판정 못 한 블록' (aops.identify 가 연산자 이름을 붙인다).
"""
from __future__ import annotations

import os
import re
from collections import defaultdict

from . import draw as D

TOL = 2.5                 # 선 끝 ↔ 단자 · 행 자리 (from_sheet.snap 과 같은 값)
JOIN = 0.6                # 선 끝 ↔ 선 끝 · 선 끝 ↔ 몸통 (분석기 geom 의 끝점 맞닿음과 같은 뜻)

_FUNC = {"AND": ("AND", "and"), "OR": ("OR", "or"), "NAND": ("NAND", "nand"), "NOR": ("NOR", "nor"), "NOT": ("NOT", "not"),
         "GT": ("GT", "delay_on"), "DT": ("DT", "delay_off"), "PD": ("PD", "pulse"), "VOTE": ("VOTE", "vote"),
         "MEMORY": ("MEMORY", "memory"), "PB": ("PB", "source"), "ANN": ("ANN", "sink"), "SOE": ("SOE", "sink"),
         "CONN": ("CONNECTOR", "connector"), "LAMP": ("LIGHT", "sink"), "MACRO": ("MACRO", "macro")}
_CONST = {"1", "0", "ON"}
_VOTE_RE = re.compile(r"^\s*(\d+)\s*([/<>=≥≤]|>=|<=|!=)\s*(\d+)\s*$")
_VOTE_OP = {"/": "ge", "≥": "ge", ">=": "ge", ">": "gt", "<": "lt", "≤": "le", "<=": "le", "=": "eq", "!=": "ne"}


# ───────────────────────────── 선 → 그물 ─────────────────────────────

def _segs(w):
    pts = w["pts"]
    return [(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]) for i in range(len(pts) - 1)]


def _on_body(px, py, sg, tol=JOIN):
    x0, y0, x1, y1 = sg
    if abs(x0 - x1) < 0.2:                       # 세로
        return abs(px - x0) <= tol and min(y0, y1) + tol < py < max(y0, y1) - tol
    if abs(y0 - y1) < 0.2:                       # 가로
        return abs(py - y0) <= tol and min(x0, x1) + tol < px < max(x0, x1) - tol
    # 기운 선 — 점과 선분의 거리
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy or 1.0
    t = ((px - x0) * dx + (py - y0) * dy) / L2
    if not (0.05 < t < 0.95):
        return False
    qx, qy = x0 + t * dx, y0 + t * dy
    return abs(qx - px) + abs(qy - py) <= tol


class _UF:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, a):
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


CELL = 24.0                # L65 — 선 상자 색인 칸 (pt).  답은 그대로 · 맞대는 짝만 줄인다


class _Grid:
    """선마다 상자(여유 pad)를 칸에 넣어 둔다 — 점·상자 근처의 선만 꺼낸다 (같은 순서: 선 번호 순)."""
    def __init__(self, wires, pad):
        self.cells = defaultdict(list)
        self.box = []
        for i, w in enumerate(wires):
            xs = [p[0] for p in w["pts"]] + [d[0] for d in w.get("dots") or []]
            ys = [p[1] for p in w["pts"]] + [d[1] for d in w.get("dots") or []]
            b = (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)
            self.box.append(b)
            for cx in range(int(b[0] // CELL), int(b[2] // CELL) + 1):
                for cy in range(int(b[1] // CELL), int(b[3] // CELL) + 1):
                    self.cells[(cx, cy)].append(i)

    def near(self, b):
        out = set()
        for cx in range(int(b[0] // CELL), int(b[2] // CELL) + 1):
            for cy in range(int(b[1] // CELL), int(b[3] // CELL) + 1):
                for j in self.cells.get((cx, cy), ()):
                    q = self.box[j]
                    if q[0] <= b[2] and b[0] <= q[2] and q[1] <= b[3] and b[1] <= q[3]:
                        out.add(j)
        return sorted(out)


def _end_dir(w, k):
    """선 w 의 끝 k(0 · 1)에서 선이 뻗어 나가는 방향 (단위 벡터)."""
    pts = w["pts"]
    a, b = (pts[0], pts[1]) if k == 0 else (pts[-1], pts[-2])
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = (dx * dx + dy * dy) ** 0.5 or 1.0
    return dx / n, dy / n


def _crossing(i, k, j, wires, ends, endmap):
    """L82 — 선 i 의 끝 k 가 선 j 의 몸통에 닿았는데, 반대쪽으로 **같은 직선이 이어지면**(다른 토막의 끝이 그 자리에서
    반대 방향으로 뻗음) 연결이 아니라 지나가는 교차다.  CAD 가 교차 자리에서 선을 둘로 끊어 그린 것 (분석기 graph.passes_through 와 같은 뜻).
    그 자리에 연결점(dot)이 있으면 연결이다 — 부르는 쪽이 dot 을 따로 본다."""
    if endmap is None:
        return False
    ex, ey = ends[i][k]
    ux, uy = _end_dir(wires[i], k)
    for m, mk in endmap.get((round(ex), round(ey)), ()):
        if m == i or m == j:
            continue
        qx, qy = ends[m][mk]
        if abs(qx - ex) + abs(qy - ey) > JOIN:
            continue
        vx, vy = _end_dir(wires[m], mk)
        if ux * vx + uy * vy < -0.98:                      # 반대 방향 · 한 직선
            return True
    # 같은 선 i 가 그 자리를 꺾임 없이 지나가는 경우는 몸통-몸통이라 여기 오지 않는다
    return False


class _DashInner:
    """L83 — 파선의 **안쪽 토막 끝**은 제 줄의 다음 토막에만 잇는다.
    들여온 파선은 토막마다 선 하나다.  분석기(graph.joinable)는 파선 한 줄의 안쪽 토막 끝을 다른 선에 잇지 않는다 —
    두 파선이 엇갈리는 자리(19VA 0006 매크로 틀 × 신호 파선)에서 토막 끝이 우연히 맞닿아도 연결이 아니다.
    안쪽 끝 = 그 끝에서 같은 직선으로 반대쪽에 다른 파선 토막이 이어진다.  틈은 그 도면의 토막 길이로 잰다
    (두 토막 중 긴 쪽 길이 안 — 파선 무늬의 틈은 토막보다 짧다).  무언가에 닿은 끝만 그때 잰다 (827장 첫 계산을 늘리지 않게)."""
    C = 8.0                                            # 끝 색인 칸 (pt) — 답은 그대로 · 견줄 끝만 줄인다

    def __init__(self, wires, ends):
        self.ends, self.memo = ends, {}
        self.info = {}                                 # 파선 토막 → (길이, 끝마다 몸통 쪽 방향)
        self.cells = defaultdict(list)
        C = self.C
        for i, w in enumerate(wires):
            if w.get("dashed") and len(w["pts"]) == 2:
                (x0, y0), (x1, y1) = ends[i]
                self.info[i] = (((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5, (_end_dir(w, 0), _end_dir(w, 1)))
                for k, (x, y) in enumerate(ends[i]):
                    self.cells[(int(x // C), int(y // C))].append((i, k))
        self.Lmax = max((v[0] for v in self.info.values()), default=0.0)

    def next_of(self, i, k):
        """끝 (i, k) 에서 이어지는 같은 줄 토막들 (빈 집합이면 바깥 끝 — 다른 선에 이을 수 있다)."""
        got = self.memo.get((i, k))
        if got is not None:
            return got
        if i not in self.info:
            return ()
        L, dirs = self.info[i]
        ex, ey = self.ends[i][k]
        ux, uy = dirs[k]                               # 몸통 쪽 · 이어지는 토막은 그 반대쪽에 있다
        C, info, ends = self.C, self.info, self.ends
        r = int((max(L, self.Lmax) + JOIN) // C) + 1
        gx, gy = int(ex // C), int(ey // C)
        nxt = set()                                    # 이어지는 쪽 칸만 본다 (몸통 반대쪽으로 r 칸 · 옆으로 한 칸)
        for cx in range(gx - r if ux > 0.5 else gx - 1, (gx + r if ux < -0.5 else gx + 1) + 1):
            for cy in range(gy - r if uy > 0.5 else gy - 1, (gy + r if uy < -0.5 else gy + 1) + 1):
                for m, mk in self.cells.get((cx, cy), ()):
                    if m == i:
                        continue
                    qx, qy = ends[m][mk]
                    ahead = (ex - qx) * ux + (ey - qy) * uy     # e 에서 이어지는 쪽으로 간 거리
                    if ahead < -JOIN or abs((qx - ex) * uy - (qy - ey) * ux) > JOIN:     # 뒤쪽 · 직선에서 벗어남
                        continue
                    Lm, dm = info[m]
                    vx, vy = dm[mk]
                    if ahead <= max(L, Lm) + JOIN and ux * vx + uy * vy < -0.98:
                        nxt.add(m)
        self.memo[(i, k)] = nxt
        return nxt

    def blocks(self, i, k, j):
        nxt = self.next_of(i, k)
        return bool(nxt) and j not in nxt


def _pair_joined(i, j, wires, ends, segs, endmap=None, inner=None):
    # 끝이 저 선의 끝 · 꺾임점(L66 — 꺾임에서 세 갈래로 갈라짐) · 몸통에 닿으면 한 그물 (분석기 graph 도 맞닿은 토막 끝을 잇는다)
    # L82 — 몸통에 닿은 끝이라도 반대쪽에 같은 직선이 이어지면 지나가는 교차 (연결 아님)
    # L83 — 파선의 안쪽 토막 끝은 제 줄의 다음 토막에만 잇는다 (연결점 dot 은 아래에서 따로)
    for k, a in enumerate(ends[i]):
        if (any(abs(a[0] - b[0]) + abs(a[1] - b[1]) <= JOIN for b in wires[j]["pts"]) or
                any(_on_body(a[0], a[1], sg) for sg in segs[j]) and not _crossing(i, k, j, wires, ends, endmap)):
            if inner is None or not inner.blocks(i, k, j):
                return True
    for k, b in enumerate(ends[j]):
        if (any(abs(b[0] - a[0]) + abs(b[1] - a[1]) <= JOIN for a in wires[i]["pts"]) or
                any(_on_body(b[0], b[1], sg) for sg in segs[i]) and not _crossing(j, k, i, wires, ends, endmap)):
            if inner is None or not inner.blocks(j, k, i):
                return True
    for dx, dy in (wires[i].get("dots") or []):
        if any(_on_body(dx, dy, sg, 1.0) for sg in segs[j]) or any(abs(dx - b[0]) + abs(dy - b[1]) <= 1.0 for b in ends[j]):
            return True
    for dx, dy in (wires[j].get("dots") or []):
        if any(_on_body(dx, dy, sg, 1.0) for sg in segs[i]) or any(abs(dx - b[0]) + abs(dy - b[1]) <= 1.0 for b in ends[i]):
            return True
    return False


def _nets_of(wires, grid=None):
    """선 → 그물 번호 (0..) · 그물마다 선 목록.  L65 — 상자가 겹치는 짝만 맞댄다 (예전엔 모든 짝 · 3343선 장 한 장에 50초)."""
    n = len(wires)
    uf = _UF(n)
    ends = [[(w["pts"][0][0], w["pts"][0][1]), (w["pts"][-1][0], w["pts"][-1][1])] for w in wires]
    segs = [_segs(w) for w in wires]
    pad = max(JOIN, 1.0)
    g = grid or _Grid(wires, pad)
    endmap = defaultdict(list)                     # L82 — 끝점 색인 (교차 판정 — 반대쪽에 같은 직선이 이어지는가)
    for i, (a, b) in enumerate(ends):
        for k, (x, y) in enumerate((a, b)):
            for cx in (round(x) - 1, round(x), round(x) + 1):
                for cy in (round(y) - 1, round(y), round(y) + 1):
                    endmap[(cx, cy)].append((i, k))
    inner = _DashInner(wires, ends)                 # L83 — 파선 안쪽 토막 끝
    for i in range(n):
        for j in g.near(g.box[i]):
            if j > i and _pair_joined(i, j, wires, ends, segs, endmap, inner):
                uf.union(i, j)
    roots = {}
    net_of = []
    for i in range(n):
        r = uf.find(i)
        if r not in roots:
            roots[r] = len(roots)
        net_of.append(roots[r])
    members = defaultdict(list)
    for i, k in enumerate(net_of):
        members[k].append(i)
    return net_of, members


def _touch(px, py, wires, segs, net_of, grid=None):
    """점(단자 · 행 자리)에 닿는 그물 — 선 끝 TOL 안이 먼저 · 없으면 몸통 위."""
    cand = grid.near((px - TOL, py - TOL, px + TOL, py + TOL)) if grid is not None else range(len(wires))
    best, bd = None, TOL + 1e-9
    for i in cand:
        w = wires[i]
        for q in (w["pts"][0], w["pts"][-1]):
            d = abs(q[0] - px) + abs(q[1] - py)
            if d < bd:
                best, bd = net_of[i], d
    if best is not None:
        return best
    for i in cand:
        if any(_on_body(px, py, sg, TOL) for sg in segs[i]):
            return net_of[i]
    return None


def _side(b, x, y):
    x0, y0, x1, y1 = b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]
    d = {"L": abs(x - x0), "R": abs(x - x1), "T": abs(y - y0), "B": abs(y - y1)}
    return min(d, key=d.get)


# ───────────────────────────── 블록 → 시뮬레이터 블록 ─────────────────────────────

def _block(b, notes=()):
    kind = b["kind"]
    p = dict(b.get("param") or {})
    text = (b.get("text") or "").strip()
    out = {"kind": "RECT", "func": "UNKNOWN", "logic": "unknown", "label": text, "read": text, "score": 1.0,
           "bbox": [b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]], "cells": [], "param": {}, "group": "",
           "pointer": None, "roles": {}, "drawn": kind}
    if kind in _FUNC:
        out["func"], out["logic"] = _FUNC[kind]
    if kind in ("GT", "DT", "PD"):
        out["param"]["t"] = p.get("t", 5)
    elif kind == "VOTE":
        out["param"] = {"a": int(p.get("a", 2)), "b": int(p.get("b", 3)), "op": "ge"}
        out["label"] = f"{out['param']['a']}/{out['param']['b']}"
    elif kind == "MEMORY":
        out["param"] = {"dominant": p.get("dominant") or ""}
        out["roles"] = {"set_cell": 0, "reset_cell": 1}
        out["cells"] = [[b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"] / 2], [b["x"], b["y"] + b["h"] / 2, b["x"] + b["w"], b["y"] + b["h"]]]
        out["label"] = "S/R"
    elif kind == "PB":
        out["label"] = ("PB " + (b.get("label") or "")).strip()
    elif kind == "CONN":
        out["group"] = text.upper()
        out["kind"] = "CIRCLE"
        g = D.block_geometry(b)
        if g.get("pointer"):
            out["pointer"] = list(g["pointer"][-1])
    elif kind == "LAMP":
        out["kind"] = "CIRCLE"
        out["label"] = text[:2]
    elif kind == "MACRO":
        out["func"], out["logic"] = "MACRO", "macro"
        out["label"] = p.get("title") or ""
        out["read"] = out["label"]
        out["pins"] = {}
        out["lines"] = []
    elif kind == "BOX":
        _box_meaning(out, b, text, notes)
    for k in ("above", "sp", "sp_unit", "sp_level", "sp_label", "out", "k", "lo", "hi"):
        if p.get(k) not in (None, ""):
            out["param"][k] = p[k]
    return out


_TOGGLES: list = [None, frozenset()]


def _learned_toggles() -> frozenset:
    """공통 Typical 사전의 시트에서 분석기가 토글(장 NOTE 의 INVERT 정의)로 읽은 글자들."""
    from . import library
    m = library.mtime()
    if _TOGGLES[0] == ("ok", m):
        return _TOGGLES[1]
    out = set()
    try:
        for ty in library.typicals().values():
            for b in ((ty.get("sheet") or {}).get("blocks") or {}).values():
                if b.get("logic") == "toggle":
                    w = re.sub(r"[^0-9A-Z]", "", str(b.get("label") or b.get("read") or "").upper())
                    if w:
                        out.add(w)
    except Exception:
        pass
    _TOGGLES[:] = [("ok", m), frozenset(out)]
    return _TOGGLES[1]


def _box_meaning(out, b, text, notes=()):
    """글자 상자 — 분석기와 같은 사전(blocks.isa_word · 범례 기능 이름 · ISA 약어).  투표 글자 `2/3` · 상수 `1`/`0`/`ON` ·
    STEP · 그 밖은 판정 못 한 블록으로 두어 aops.identify 가 연산자(Σ · MED · T …)를 알아본다."""
    from . import blocks as BL
    t = text.upper()
    key = re.sub(r"[^0-9A-Z]", "", t)
    if key in _CONST:
        out["func"], out["logic"], out["label"] = "CONST", "source", "0" if key == "0" else "1"
        return
    m = _VOTE_RE.match(t)
    if m and 0 < int(m.group(1)) <= int(m.group(3)):
        out["func"], out["logic"] = "VOTE", "vote"
        out["param"] = {"a": int(m.group(1)), "b": int(m.group(3)), "op": _VOTE_OP.get(m.group(2), "ge")}
        return
    if t.startswith("STEP"):
        out["func"], out["logic"] = "STEP", "step"
        return
    if key in ("PASS", "BUFFER"):
        out["func"], out["logic"] = "BUFFER", "pass"
        return
    from . import analog as A
    if A._MON.match(t):
        out["func"], out["logic"] = A.MONITOR_FUNC, "source"           # 감시 블록 — 값 · 설정값이 있으면 비교로 1/0 (analog.monitors)
        return
    # 그 장 NOTES 가 이 낱말을 따옴표로 부르며 INVERT 를 말하면 토글 (분석기 blocks._note_defined 와 같은 규칙)
    if re.fullmatch(r"[A-Z][A-Z0-9_]{1,11}", key):
        joined = " ".join(str(n) for n in notes).upper()
        for m in re.finditer("[\\'\"\u201c\u201d]" + re.escape(key) + "[\\'\"\u201c\u201d]", joined):
            if re.search("INVERT", joined[max(0, m.start() - 160): m.end() + 160]):
                out["func"], out["logic"] = "TOGGLE", "toggle"
                out["param"]["note"] = "NOTE — 입력이 참으로 바뀔 때마다 출력이 뒤집힌다"
                return
    # L81 — 그 장에 NOTE 가 없어도(예전에 다시 그린 장) 공통 Typical 사전이 토글로 배운 낱말이면 토글
    if key and key in _learned_toggles():
        out["func"], out["logic"] = "TOGGLE", "toggle"
        out["param"]["note"] = "공통 Typical 사전 — 그 장 NOTE 가 토글로 정의한 글자"
        return
    hit = None
    try:
        hit = BL.isa_word(text)
    except Exception:
        hit = None
    if hit and hit.get("logic"):
        lg = hit["logic"]
        if lg == "const":
            out["func"], out["logic"], out["label"] = "CONST", "source", "1"
        elif lg == "memory":
            out["func"], out["logic"] = "MEMORY", "memory"
            out["roles"] = {"set_cell": 0, "reset_cell": 1}
            out["cells"] = [[b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"] / 2], [b["x"], b["y"] + b["h"] / 2, b["x"] + b["w"], b["y"] + b["h"]]]
            out["param"] = {"dominant": ""}
        else:
            out["func"] = {"and": "AND", "or": "OR", "not": "NOT", "nand": "NAND", "nor": "NOR", "delay_on": "GT",
                           "delay_off": "DT", "pulse": "PD"}.get(lg, str(hit["name"]))
            out["logic"] = lg
            if lg in ("delay_on", "delay_off", "pulse"):
                out["param"]["t"] = (b.get("param") or {}).get("t", 5)
        return
    # 모르는 글자 — 들어오는 선 없이 나가는 선만 있으면 이름 붙은 신호 상자(source) 는 to_sheet 가 단자를 센 뒤 정한다


# ───────────────────────────── 한 장 ─────────────────────────────

def _drop_inside(wires: list, blocks: list) -> list:
    """L81 — 기호 상자 **안에 통째로 든** 선 토막은 신호선이 아니라 그 기호의 그림이다 (분석 시트를 들여올 때 ⊠ 안쪽 획이
    선으로 옮겨진 것 — 19VA Typical 0013).  남겨 두면 입력선과 출력선이 상자 한가운데서 만나 한 신호가 되고, NOT 이면
    자기 입력을 자기가 뒤집어 시뮬레이션이 끝없이 되풀이된다 (827장 묶음 첫 시뮬레이션 23초).  변에 닿는 선은 그대로 단자다."""
    boxes = [(b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]) for b in blocks
             if b.get("kind") in D.SYMBOLS and b.get("kind") not in ("TEXT", "MACRO") and b.get("w") and b.get("h")]
    if not boxes:
        return wires
    E = 0.05

    def inside(w):
        xs, ys = [p[0] for p in w["pts"]], [p[1] for p in w["pts"]]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        return any(bx0 - E <= x0 and x1 <= bx1 + E and by0 - E <= y0 and y1 <= by1 + E for bx0, by0, bx1, by1 in boxes)
    return [w for w in wires if not inside(w)]


def to_sheet(doc: dict, page: int, typ_pages: dict | None = None) -> dict:
    """그림 하나 → 분석 결과 시트 꼴.  typ_pages = {Typical 시트 이름: 그 그림의 page} (매크로 잇기)."""
    N = int(doc.get("N") or D.N_DEFAULT)
    wires = [w for w in (doc.get("wires") or []) if len(w.get("pts") or []) >= 2]
    wires = _drop_inside(wires, doc.get("blocks") or [])
    grid = _Grid(wires, max(JOIN, 1.0))
    net_of, members = _nets_of(wires, grid)
    segs = [_segs(w) for w in wires]
    nets = {}
    for k, idxs in members.items():
        nets[str(k)] = {"segs": [[round(v, 2) for v in sg] for i in idxs for sg in segs[i]], "jumps": [],
                        "dashed": any(wires[i].get("dashed") for i in idxs),
                        "wires": [wires[i]["id"] for i in idxs]}
    blocks, ports = {}, []
    io = defaultdict(lambda: [0, 0])
    drawn = {b["id"]: b for b in doc.get("blocks") or [] if b.get("kind") in D.SYMBOLS and b["kind"] != "TEXT"}
    ends = []                                             # 선 끝 — (x, y, 그물)
    for i, w in enumerate(wires):
        for q in (w["pts"][0], w["pts"][-1]):
            ends.append((q[0], q[1], net_of[i]))
    end_cells = defaultdict(list)                         # L65 — 선 끝 색인 (블록마다 그 상자 근처 끝만 · 원래 순서)
    for k, (ex, ey, _) in enumerate(ends):
        end_cells[(int(ex // CELL), int(ey // CELL))].append(k)

    def ends_near(x0, y0, x1, y1):
        ks = []
        for cx in range(int((x0 - TOL) // CELL), int((x1 + TOL) // CELL) + 1):
            for cy in range(int((y0 - TOL) // CELL), int((y1 + TOL) // CELL) + 1):
                ks.extend(end_cells.get((cx, cy), ()))
        return [ends[k] for k in sorted(ks)]
    for bid, b in drawn.items():
        sb = _block(b, doc.get("notes") or ())
        blocks[bid] = sb
        seen = set()

        def add(x, y, dr, role, cell=0, pin=None):
            net = _touch(x, y, wires, segs, net_of, grid)
            if net is None or (net, dr, role, pin) in seen:
                return
            seen.add((net, dr, role, pin))
            pd = {"block": bid, "net": str(net), "dir": dr, "at": [round(x, 2), round(y, 2)], "side": _side(b, x, y), "cell": cell,
                  "role": role if b["kind"] == "MEMORY" else ""}
            if b["kind"] == "MACRO":
                pd["pin"] = pin or ""
                sb["pins"][f"{pd['at'][0]},{pd['at'][1]}"] = pin or ""
            ports.append(pd)
            io[bid][0 if dr == "in" else 1] += 1
        spec = D.SYMBOLS[b["kind"]]
        for x, y, dr, role in D.ports_of(b):                # 정해진 단자 자리 (원 · 매크로 · 메모리 칸 · 출력)
            cell = (0 if role in ("set", "q") else 1) if b["kind"] == "MEMORY" else 0
            add(x, y, dr, role, cell, role if b["kind"] == "MACRO" else None)
        if spec.get("circle") or spec.get("macro") or spec.get("note"):
            continue
        # 상자 변 · 입력 막대에 닿은 선 끝은 전부 단자다 (분석기 graph: 막대에 닿은 선 = 입력 · 변에 닿은 선 = 그 변의 단자)
        x0, y0, x1, y1 = b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]
        bar = D.bar_of(b) if spec.get("bar") else None
        bx0, by0, bx1, by1 = min(x0, bar[0]) if bar else x0, min(y0, bar[1]) if bar else y0, max(x1, bar[2]) if bar else x1, max(y1, bar[3]) if bar else y1
        for ex, ey, _ in ends_near(bx0, by0, bx1, by1):
            if bar and abs(ex - bar[0]) <= TOL and bar[1] - TOL <= ey <= bar[3] + TOL:
                add(ex, ey, "in", "", 0)
            elif abs(ex - x0) <= TOL and y0 - TOL <= ey <= y1 + TOL:
                cell = 0 if ey < (y0 + y1) / 2 else 1
                role = ("set" if cell == 0 else "reset") if b["kind"] == "MEMORY" else ""
                add(ex, ey, "in", role, cell if b["kind"] == "MEMORY" else 0)
            elif abs(ex - x1) <= TOL and y0 - TOL <= ey <= y1 + TOL:
                cell = 0 if ey < (y0 + y1) / 2 else 1
                role = ("q" if cell == 0 else "qn") if b["kind"] == "MEMORY" else ""
                add(ex, ey, "out", role, cell if b["kind"] == "MEMORY" else 0)
            elif x0 - TOL <= ex <= x1 + TOL and (abs(ey - y0) <= TOL or abs(ey - y1) <= TOL) and spec.get("logic") not in ("source",):
                add(ex, ey, "in", "", 0)                   # 위 · 아래 변 — 타이머의 t(위) · 리셋(아래) 은 sim._index 가 side 로 가른다
    # STEP 상자 — 단자 역할은 그 높이의 글줄 이름 (STEP IN · CRIT · STEP OUT · C-STEP CMD)
    for bid, sb in blocks.items():
        if sb["func"] != "STEP":
            continue
        b = drawn[bid]
        names = {"STEP IN": "step_in", "STEPIN": "step_in", "CRIT": "crit", "STEP OUT": "step_out", "STEPOUT": "step_out",
                 "C-STEP CMD": "c_step", "CSTEP": "c_step", "C-STEP": "c_step"}
        lines = [(b["y"] + ln[1], str(ln[2]).upper().strip()) for ln in (b.get("param") or {}).get("lines") or []]
        for pt in ports:
            if pt["block"] != bid:
                continue
            want = ("step_out", "c_step") if pt["dir"] == "out" else ("step_in", "crit")
            best = min(((abs(pt["at"][1] - ly), nm) for ly, nm in lines if nm in names and names[nm] in want), default=None)
            if best and best[0] <= D.PITCH:
                sb["roles"][f"{pt['at'][0]},{pt['at'][1]}"] = names[best[1]]
                pt["role"] = names[best[1]]
    # 글자 상자의 남은 뜻 · 입력 하나뿐인 AND/OR 는 그렇게 그린 것 (L53 as_drawn)
    for bid, sb in blocks.items():
        n_in, n_out = io[bid]
        if sb["func"] == "UNKNOWN" and sb["logic"] == "unknown" and drawn[bid]["kind"] == "BOX":
            if n_in == 0 and n_out > 0 and not _looks_analog(sb["label"]):
                sb["func"], sb["logic"] = "SIGNAL", "source"            # 이름 붙은 신호 상자 (들어오는 선 없음)
            elif n_in > 0 and n_out == 0 and len(sb["label"]) <= 3 and sb["label"].isalpha():
                sb["func"], sb["logic"] = "DISPLAY", "sink"             # 상태 표시 글자 상자 (받기만)
        if sb["logic"] in ("and", "or", "nand", "nor") and n_in == 1:
            sb["param"]["as_drawn"] = 1
    # 행
    rows, table = [], []
    for side, key, x_ in (("L", "left", D.LX0), ("R", "right", D.LX1)):
        cells = doc.get(key) or {}
        rng = range(1, N + 1) if side == "L" else range(N + 1, 2 * N + 1)
        for n in rng:
            v = cells.get(str(n)) or {}
            y = D.ry(n, N)
            net = _touch(x_, y, wires, segs, net_of, grid)
            t = {"side": side, "n": n, "kks": v.get("kks", ""), "desc": v.get("desc", ""), "y0": round(y - D.PITCH / 2, 2), "y1": round(y + D.PITCH / 2, 2)}
            if side == "L":
                t["fm"] = v.get("fm", "")
            else:
                t["to"] = v.get("to", "")
            table.append(t)
            if net is not None or v.get("desc") or v.get("fm") or v.get("to"):
                r = {"n": n, "side": side, "net": str(net) if net is not None else None, "at": [x_, round(y, 2)],
                     "desc": v.get("desc", ""), "kks": v.get("kks", "")}
                r["fm" if side == "L" else "to"] = v.get("fm" if side == "L" else "to", "")
                rows.append(r)
    # 매크로 ↔ Typical (단자의 행 번호로)
    typ_pages = typ_pages or {}
    for bid, b in drawn.items():
        if b["kind"] != "MACRO":
            continue
        p = b.get("param") or {}
        pg = typ_pages.get((p.get("typ") or "").strip())
        pins_net = {q["pin"]: q for q in ports if q["block"] == bid}

        def items(pins):
            out = []
            for q in pins or []:
                pt = pins_net.get(q.get("name"))
                out.append({"at": f"{pt['at'][0]},{pt['at'][1]}" if pt else "", "net": pt["net"] if pt else None,
                            "pin": q.get("name", ""), "row": q.get("row"), "desc": "", "score": 1.0 if q.get("row") else 0})
            return out
        m = {"sheet": p.get("typ") or "", "page": pg, "title": p.get("title") or "", "score": 1.0 if pg else 0,
             "inputs": items(p.get("pins_in")), "outputs": items(p.get("pins_out")), "cands": []}
        if pg is None:
            m["why"] = f"이 묶음에 Typical 시트 '{p.get('typ') or '?'}' 가 없습니다"
        blocks[bid]["macro"] = m
    # 선 아래 글 → 아날로그 범위 (`0~250 barg`) · 블록 위 글 → 감시 설정값 — 분석기와 같은 읽기 함수에 같은 꼴의 낱말을 준다
    _apply_texts(doc, wires, segs, net_of, blocks, rows)
    s = {"page": page, "sheet_no": doc.get("sheet_no") or "", "title": doc.get("title") or "", "did": doc.get("id"),
         "logic": [D.LX0, D.TOP, D.LX1, D.TOP + N * D.PITCH], "pitch": D.PITCH, "frame": [0, 0, D.W, D.H],
         "nets": nets, "blocks": blocks, "ports": ports, "rows": rows, "table": table, "dangling": [], "stray_arrows": [],
         "findings": [], "typical": bool(doc.get("typical")), "N": N}
    try:
        from .analyse import _net_order
        s["order"] = _net_order(s)
    except Exception:
        s["order"] = {}
    return s


_ANALOG_HINT = re.compile(r"[Σ∑√∫△÷×]|^(MED|AVG|MAX|MIN|ABS|SQRT|PID|SEL|DEV|HI|LO|BIAS|K|-K|T|F\(X\)|OUT|EQUAL|BIT_CNT|SPC|A)$", re.I)


def _looks_analog(label):
    return bool(_ANALOG_HINT.search((label or "").strip()))


def _words_of(texts):
    """[(cx, cy, 글, fs, anchor)] → 분석기 낱말 꼴 [(x0, y0, x1, y1, 글)] — 낱말마다 어림 폭."""
    ws = []
    for cx, cy, t, fs, *rest in texts:
        anchor = rest[0] if rest else "middle"
        parts = str(t).split()
        if not parts:
            continue
        total = sum(len(p) for p in parts) * fs * D._CHAR_W + (len(parts) - 1) * fs * 0.3
        x = cx - total / 2 if anchor == "middle" else (cx - total if anchor == "end" else cx)
        for p in parts:
            w = len(p) * fs * D._CHAR_W
            ws.append((round(x, 2), round(cy - fs / 2, 2), round(x + w, 2), round(cy + fs / 2, 2), p))
            x += w + fs * 0.3
    return ws


def _apply_texts(doc, wires, segs, net_of, blocks, rows):
    from . import analog as A
    ws = []
    for b in doc.get("blocks") or []:
        ab = (b.get("param") or {}).get("above")
        if ab and b.get("kind") in D.SYMBOLS:
            ws += _words_of([[b["x"] + b["w"] / 2, b["y"] - 0.5 * D.PITCH, ab, D.ABOVE_FS]])
    for w in wires:
        if w.get("label"):
            pos = D.wire_label_pos(w)
            if pos:
                ws += _words_of([[pos[0], pos[1], w["label"], 4.2]])
    if not ws:
        return
    s = {"blocks": blocks, "ports": [], "rows": rows, "nets": {}, "pitch": D.PITCH}
    for bid, sb in blocks.items():
        if A.monitor_kind(sb) and sb.get("param", {}).get("sp") is None:
            try:
                A._read_setpoint(sb, ws)
            except Exception:
                pass
    # 범위 — 행의 선 바로 아래 글 (분석기 _read_ranges 와 같은 규칙: 그 행의 가로 토막 아래 1.5P 안)
    for r in rows:
        if r["side"] != "L" or r.get("net") is None:
            continue
        for i, w in enumerate(wires):
            if str(net_of[i]) != r["net"] or not w.get("label"):
                continue
            m = A._RANGE.match(w["label"].strip())
            if m:
                unit = (m.group(3) or "")
                if re.fullmatch(r"\d.*", unit):
                    unit = ""
                r["range"] = {"lo": A.num(m.group(1)), "hi": A.num(m.group(2)), "unit": unit, "text": m.group(0).strip()}
                break


# ───────────────────────────── 묶음 ─────────────────────────────

_SHEET_MEMO: dict = {}         # L65 — 그림 내용 지문 → to_sheet 결과(pickle).  묶음에서 고친 장만 다시 바꾼다 (받을 때마다 새 사본 — 뒤에서 고쳐 쓴다)


def _to_sheet_memo(doc: dict, page: int, typ_pages: dict, dkey: str | None = None) -> dict:
    import hashlib, json, pickle
    if dkey:                                             # 부르는 쪽이 그림 내용 열쇠를 안다 (저장 기록 · 화면 그림 지문)
        key = json.dumps([dkey, page, sorted(typ_pages.items())])
    else:
        key = hashlib.sha1(json.dumps([doc, page, sorted(typ_pages.items())], sort_keys=True, default=str).encode()).hexdigest()
    hit = _SHEET_MEMO.get(key)
    if hit is not None:
        return pickle.loads(hit)
    # L81 — 디스크에도 둔다 (그 그림 폴더의 sheet.pkl · 열쇠 + 코드 판).  서버를 다시 켜도 827장을 다시 바꾸지 않는다 (약 5초)
    did = doc.get("id") if dkey else None
    fp = None
    if did and D.ID_RE.match(str(did)):
        fp = D.root() / did / "sheet.pkl"
        try:
            k2, blob = pickle.loads(fp.read_bytes())
            if k2 == (key, _code_ver()):
                _SHEET_MEMO[key] = blob
                return pickle.loads(blob)
        except Exception:
            pass
    sh = to_sheet(doc, page, typ_pages)
    if len(_SHEET_MEMO) > 3000:
        _SHEET_MEMO.clear()
    blob = _SHEET_MEMO[key] = pickle.dumps(sh, protocol=pickle.HIGHEST_PROTOCOL)
    if fp is not None and fp.parent.exists():
        try:
            tmp = fp.with_name(f"sheet.{os.getpid()}.tmp")
            tmp.write_bytes(pickle.dumps(((key, _code_ver()), blob), protocol=pickle.HIGHEST_PROTOCOL))
            os.replace(tmp, fp)
        except Exception:
            pass
    return sh


_VER: list = []


def _code_ver() -> str:
    """시트로 바꾸는 코드가 바뀌면 디스크 사본을 쓰지 않는다."""
    if not _VER:
        import hashlib
        from pathlib import Path
        h = hashlib.sha1()
        for f in ("draw_sim.py", "draw.py", "blocks.py", "analog.py"):
            try:
                h.update((Path(__file__).parent / f).read_bytes())
            except OSError:
                pass
        _VER.append(h.hexdigest()[:16])
    return _VER[0]


def sheets_of(docs: list, keys: dict | None = None) -> list:
    """묶음의 그림들 → 시트 목록 (page = 1..) · FROM/TO 잇기 · 연산자 이름 · 매크로 ↔ Typical."""
    from . import fromto, aops
    typ_pages = {}
    for i, d in enumerate(docs):
        if d.get("typical") and (d.get("sheet_no") or "").strip():
            typ_pages[d["sheet_no"].strip()] = i + 1
    sheets = [_to_sheet_memo(d, i + 1, typ_pages, (keys or {}).get(d.get("id"))) for i, d in enumerate(docs)]
    try:
        fromto.check(sheets)
    except Exception:
        pass
    try:
        aops.identify(sheets)
    except Exception:
        pass
    return sheets


def simulate(docs: list, focus_did: str, forces=None, state=None, timers=None, analog=None, cache=None, inner=None, keys=None) -> dict:
    """묶음째 시뮬레이션 — 열쇠는 그림 id (화면이 아는 것).  → sim.simulate_bundle 결과 + focus 장의 그물 ↔ 선 id 지도.
    inner = ["<그림 id>:<매크로 상자 id>", …] — 열린 매크로 새 창마다, 부모 장에 펼쳐 같이 돈 Typical 안의 값(틀마다 · Typical 선 이름)을
    `macro_inner` 로 낸다 (L59 · 검토 화면 L44 와 같은 값 — sim.simulate_bundle 의 macro_inner 그대로, 쪽 번호만 그림 id 로)."""
    from . import sim
    sheets = (cache or {}).get("sheets") if cache is not None else None
    if sheets is None:
        sheets = sheets_of(docs, keys)
        if cache is not None:
            cache["sheets"] = sheets
    page_of = {s["did"]: s["page"] for s in sheets}
    did_of = {s["page"]: s["did"] for s in sheets}
    conv = lambda m: {page_of[k]: v for k, v in (m or {}).items() if k in page_of}
    focus = page_of.get(focus_did)
    if focus is None:
        return {"error": "그 그림이 묶음에 없습니다"}
    st = {}
    for k, v in (state or {}).items():
        if k in page_of:
            st[page_of[k]] = v
    res = sim.simulate_bundle(sheets, forces=conv(forces), state=st, focus=focus, timers=conv(timers), analog=conv(analog),
                              cache=cache)
    s = sheets[focus - 1]
    mi = {}
    for key in (inner or []) if isinstance(inner, list) else []:
        did, _, bid = str(key).partition(":")
        pg = page_of.get(did)
        v = ((res.get("macro_inner") or {}).get(pg) or {}).get(bid) if pg else None
        if v is None:
            continue
        mb = (sheets[pg - 1]["blocks"].get(bid) or {}).get("macro") or {}
        mi[f"{did}:{bid}"] = {**v, "typ_did": did_of.get(mb.get("page")), "parent_did": did}
    out = {"focus": res.get("focus"), "macro_inner": mi, "notes": res.get("notes", []), "pulled": res.get("pulled", []),
           "design_errors": res.get("design_errors", []), "linked": {did_of.get(k, k): v for k, v in (res.get("linked") or {}).items()},
           "state": {did_of.get(k, k): v for k, v in (res.get("state") or {}).items()},
           "pages": [{**p, "did": did_of.get(p.get("page"))} for p in (res.get("pages") or [])],
           "sheet": {"nets": {k: {"wires": v["wires"]} for k, v in s["nets"].items()},
                     "blocks": {k: {"func": b["func"], "logic": b["logic"], "label": b.get("label", ""), "aop": b.get("aop"),
                                    "macro": {"page": (b.get("macro") or {}).get("page"), "sheet": (b.get("macro") or {}).get("sheet"),
                                              "did": did_of.get((b.get("macro") or {}).get("page")),
                                              "why": (b.get("macro") or {}).get("why")} if b.get("macro") else None,
                                    "param": b.get("param", {})} for k, b in s["blocks"].items()},
                     "ports": s["ports"],
                     "rows": [{"n": r["n"], "side": r["side"], "net": r.get("net"), "ref": r.get("ref"), "ft": r.get("ft")} for r in s["rows"]]},
           "default_t": sim.DEFAULT_T}
    return out
