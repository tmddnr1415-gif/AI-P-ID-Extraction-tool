"""Logic 시트 한 장의 신호 연결도 — 선을 잇고(넷) · 블록을 세우고 · 단자를 붙인다.

규칙 (전부 관계 · 허용치는 표 행 간격 P 의 배율 — geom.py 머리말):
  * 선 둘이 끝점끼리 닿거나, 한 선의 끝점이 다른 선의 몸통 위에 있으면(T) 이어진다.
  * 몸통끼리 가로지르면 이어지지 않는다 — 범례 G003 "BROKEN LINE REPRESENTS NO LOGIC CONNECTION".
    연결점(작은 원 · 칠한 점)이 그 자리에 있을 때만 이어진다 ("DOT REPRESENTS LOGIC CONNECTION").
  * 화살촉이 붙은 끝은 신호가 **들어가는** 끝이다.  꼭지가 닿는 것(입력 막대 · 상자 변 · 원)이 받는 쪽이다.
  * 입력 막대 = 화살촉 꼭지가 몸통에 닿는 곧은 선 중 블록(원 · 상자)에 붙은 것 — 그 블록의 입력 변이다.
  * 원에 붙은 칠한 삼각형은 연결 기호의 꼭지다 — 꼭지에서 나가는 선은 기호가 **내보내는** 선이고,
    원 몸통에 닿는 선은 기호로 **들어가는** 선이다.
  * 블록 상자 변에 화살촉 없이 닿은 끝: 오른쪽 변이면 나가는 단자, 왼쪽 변이면 들어오는 단자,
    위·아래 변이면 넷 안에서 정한다 (다른 몰이가 있으면 들어오는 쪽).
  * LOGIC 영역 왼쪽 경계에 닿은 끝은 그 행의 입력, 오른쪽 경계는 그 행의 출력이다.
  * 상자 셋 이상을 품는 큰 사각형은 블록이 아니라 묶음 테두리다 (Typical 의 MOTOR BLOCK 테두리).
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field

from . import geom
from .geom import DOT_MAX, GLYPH_MAX, RECT_MIN, TOUCH


# ------------------------------------------------------------------ 작은 기하

def _d(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _on_seg(p, s, tol):
    """점 p 가 선분 s 위(끝점 포함)에 있나 — 거리와 매개변수."""
    ax, ay, bx, by = s.x0, s.y0, s.x1, s.y1
    vx, vy = bx - ax, by - ay
    L2 = vx * vx + vy * vy
    if L2 == 0:
        return _d(p, (ax, ay)) <= tol, 0.0
    t = ((p[0] - ax) * vx + (p[1] - ay) * vy) / L2
    tc = max(0.0, min(1.0, t))
    q = (ax + tc * vx, ay + tc * vy)
    return _d(p, q) <= tol, t


def _in_rect(p, r, tol):
    return r[0] - tol <= p[0] <= r[2] + tol and r[1] - tol <= p[1] <= r[3] + tol


def _rect_edge(p, r, tol):
    """점이 사각형 변 위에 있으면 그 변 이름."""
    x0, y0, x1, y1 = r
    if not _in_rect(p, r, tol):
        return None
    cands = [(abs(p[0] - x0), "L"), (abs(p[0] - x1), "R"), (abs(p[1] - y0), "T"), (abs(p[1] - y1), "B")]
    dd, side = min(cands)
    return side if dd <= tol else None


# ------------------------------------------------------------------ 결과 구조

@dataclass
class Block:
    id: str
    kind: str                       # RECT | CIRCLE | CONNECTOR | LIGHT
    bbox: tuple
    cells: list = field(default_factory=list)   # 상자 칸 [(x0,y0,x1,y1)] (위→아래, 왼→오)
    bus: list = field(default_factory=list)     # 입력 막대 선분 [(x0,y0,x1,y1)]
    pointer: tuple | None = None    # 연결 기호의 꼭지 (x, y)
    glyphs: list = field(default_factory=list)  # 안의 글자 획 path 번호
    label: str = ""
    func: str = ""


@dataclass
class Port:
    block: str
    net: int
    dir: str                        # in | out | ?
    at: tuple
    side: str = ""                  # L R T B (상자) · ''
    cell: int = 0


@dataclass
class Sheet:
    page: int
    layout: object
    nets: dict = field(default_factory=dict)         # id → {"segs": [...], "dashed": bool}
    blocks: dict = field(default_factory=dict)
    ports: list = field(default_factory=list)
    rows: list = field(default_factory=list)         # {"n", "side", "net", "at"}
    dangling: list = field(default_factory=list)     # 아무것도 닿지 않은 선 끝 (x, y, net)
    stray_arrows: list = field(default_factory=list)
    glyph_polys: list = field(default_factory=list)
    all_glyphs: list = field(default_factory=list)   # 장 전체의 글자 크기 획 (표 칸 글자 포함)
    words: list = field(default_factory=list)


# ------------------------------------------------------------------ 만들기

def build(prims: geom.Prims, lay=None) -> Sheet | None:
    lay = lay or geom.layout(prims)
    if lay is None:
        return None
    P = lay.pitch
    tol = TOUCH * P
    LX0, LY0, LX1, LY1 = lay.logic
    inside = lambda bb: bb[0] >= LX0 - tol and bb[2] <= LX1 + tol and bb[1] >= LY0 - tol and bb[3] <= LY1 + tol

    sh = Sheet(prims.page, lay)

    def on_border(p):
        # LOGIC 영역 테두리 자체(표의 괘선)는 신호선이 아니다
        return all((s.vert and (abs(s.x0 - LX0) <= tol or abs(s.x0 - LX1) <= tol)) or
                   (s.horiz and (abs(s.y0 - LY0) <= tol or abs(s.y0 - LY1) <= tol)) for s in p.segs)
    polys = [p for p in prims.polys if inside(p.bbox) and not on_border(p)]
    wires, glyphs = [], []
    for p in polys:
        (glyphs if p.size < GLYPH_MAX * P else wires).append(p)

    circles = [c for c in prims.circles if inside(c.bbox)]
    dots = [c for c in circles if 2 * c.r < DOT_MAX * P]
    dots += _blob_dots([b for b in prims.blobs if inside(b)], P)
    bigc = [c for c in circles if 2 * c.r >= DOT_MAX * P]
    arrows = [a for a in prims.arrows if inside(a.bbox)]

    # ---- 상자: 겹친 사각형(이중 테두리)은 하나로, 변을 나눈 사각형(S/Ro · PB|START)은 한 블록의 칸으로
    rects = [r for r in prims.rects if inside((r.x0, r.y0, r.x1, r.y1))
             and r.w >= RECT_MIN * P and r.h >= RECT_MIN * P]
    assembled, used = _assemble_rects(wires + glyphs, rects, P, tol)
    if assembled:
        rects += assembled
        wires = [p for p in wires if id(p) not in used]
        glyphs = [p for p in glyphs if id(p) not in used]
    rects = _dedupe_nested(rects, tol * 4)
    frames = _group_frames(rects, bigc)
    rects = [r for r in rects if id(r) not in frames]
    groups = _touching_groups(rects, tol)

    blocks = []
    for g in groups:
        bb = (min(r.x0 for r in g), min(r.y0 for r in g), max(r.x1 for r in g), max(r.y1 for r in g))
        cells = sorted(((r.x0, r.y0, r.x1, r.y1) for r in g), key=lambda c: (round(c[1], 1), c[0]))
        blocks.append(Block(f"B{len(blocks) + 1}", "RECT", bb, cells=cells))

    # 입력 막대에 붙은 ㄷ자 꺾은선 = 막대와 함께 닫힌 상자 (상자를 qu 대신 선으로 그린 AND 게이트)
    straight = [p for p in wires if len(p.segs) == 1 and (p.segs[0].vert or p.segs[0].horiz)]
    for p in list(wires):
        if len(p.segs) < 3 or not all(s.vert or s.horiz for s in p.segs):
            continue
        free = _free_ends(p.segs)
        if len(free) != 2:
            continue
        for q in straight:
            s0 = q.segs[0]
            if all(_on_seg(e, s0, tol)[0] for e in free):
                bb = p.bbox
                if s0.vert:
                    cell = (min(bb[0], s0.x0), bb[1], max(bb[2], s0.x0), bb[3])
                else:
                    cell = (bb[0], min(bb[1], s0.y0), bb[2], max(bb[3], s0.y0))
                if cell[2] - cell[0] < RECT_MIN * P or cell[3] - cell[1] < RECT_MIN * P:
                    continue
                blocks.append(Block(f"B{len(blocks) + 1}", "RECT", cell, cells=[cell]))
                wires.remove(p)
                break

    # 사각형 칸에 붙어 상자를 닫는 꺾은선 (PB|START 의 PB 칸) — 두 끝이 같은 칸의 모서리
    for p in list(wires):
        if len(p.segs) < 2 or not all(s.vert or s.horiz for s in p.segs):
            continue
        cnt = defaultdict(int)
        for sg in p.segs:
            for q in sg.ends():
                cnt[(round(q[0], 2), round(q[1], 2))] += 1
        free = [q for q, c in cnt.items() if c == 1]
        if len(free) != 2:
            continue
        for b in blocks:
            hitc = None
            for c in b.cells:
                corners = [(c[0], c[1]), (c[2], c[1]), (c[0], c[3]), (c[2], c[3])]
                if all(any(_d(q, k) <= tol for k in corners) for q in free):
                    hitc = c
                    break
            if hitc:
                bb = p.bbox
                b.cells.append((min(bb[0], hitc[0]), min(bb[1], hitc[1]), max(bb[2], hitc[2]), max(bb[3], hitc[3])) if False else bb)
                b.cells.sort(key=lambda c: (round(c[1], 1), c[0]))
                b.bbox = (min(b.bbox[0], bb[0]), min(b.bbox[1], bb[1]), max(b.bbox[2], bb[2]), max(b.bbox[3], bb[3]))
                wires.remove(p)
                break

    # 블록 안에 갇힌 꺾은선(변에 닿지 않는 것)은 글자다 — STEP 상자처럼 글자가 큰 블록
    def enclosed(p):
        for b in blocks:
            x0, y0, x1, y1 = b.bbox
            if p.bbox[0] >= x0 - tol and p.bbox[2] <= x1 + tol and p.bbox[1] >= y0 - tol and p.bbox[3] <= y1 + tol:
                return True
        return False
    moved = [p for p in wires if enclosed(p)]
    if moved:
        glyphs += moved
        wires = [p for p in wires if not enclosed(p)]

    # ---- 빗금으로 칠한 상자(■) · 마름모(◆) = 선 위의 인터페이스 표시 (범례 G003) — 블록이 아니다
    markers = [m for m in prims.markers if inside(m) and max(m[2] - m[0], m[3] - m[1]) >= DOT_MAX * P]

    def hatch_in(bb):
        hs = [p for p in glyphs + wires if len(p.segs) == 1 and p.bbox[0] >= bb[0] - tol and p.bbox[2] <= bb[2] + tol
              and p.bbox[1] >= bb[1] - tol and p.bbox[3] <= bb[3] + tol]
        return hs
    for b in list(blocks):
        if len(b.cells) != 1:
            continue
        hs = hatch_in(b.bbox)
        short = min(b.bbox[2] - b.bbox[0], b.bbox[3] - b.bbox[1])
        # 빗금은 상자를 가로지른다 — 굵은 글자를 칠한 짧은 띠(G010 의 START 칸)와 가른다
        long_ = [p for p in hs if p.segs[0].length >= 0.4 * short]
        if len(long_) >= 3 and len(hs) >= 6:
            ang = sorted(math.degrees(math.atan2(p.segs[0].y1 - p.segs[0].y0, p.segs[0].x1 - p.segs[0].x0)) % 180
                         for p in long_)
            dirs = [1] if ang[-1] - ang[0] <= 10 or (ang[0] + 180 - ang[-1]) <= 10 else [1, 2, 3]
            others = [p for p in glyphs if p not in hs and _in_rect(((p.bbox[0] + p.bbox[2]) / 2, (p.bbox[1] + p.bbox[3]) / 2), b.bbox, 0)]
            if len(dirs) <= 2 and len(others) <= 1:
                blocks.remove(b)
                markers.append(b.bbox)
    for m in markers:
        hs = set(id(p) for p in hatch_in(m))
        glyphs = [p for p in glyphs if id(p) not in hs]
        wires = [p for p in wires if id(p) not in hs]

    # ---- 원 블록 · 연결 기호 (원 + 칠한 꼭지 삼각형)
    pointer_arrows = set()
    straight1 = [p for p in wires + glyphs if len(p.segs) == 1]
    for c in bigc:
        b = Block(f"B{len(blocks) + 1}", "CIRCLE", c.bbox)
        for k, a in enumerate(arrows):
            if abs(_d(a.base, (c.cx, c.cy)) - c.r) <= max(tol, 0.25 * c.r) and _d(a.tip, (c.cx, c.cy)) > c.r:
                b.kind = "CONNECTOR"
                b.pointer = a.tip
                pointer_arrows.add(k)
                break
        if b.kind == "CIRCLE":
            # 선 둘이 원에서 나와 한 꼭지에서 만나면 꼭지 삼각형 (안을 빗금으로 칠한 양식)
            on_c = []
            for p in straight1:
                e0, e1 = p.segs[0].ends()
                for a_, t_ in ((e0, e1), (e1, e0)):
                    if abs(_d(a_, (c.cx, c.cy)) - c.r) <= max(tol, 0.25 * c.r) and _d(t_, (c.cx, c.cy)) > c.r * 1.2:
                        on_c.append((p, t_))
            for i in range(len(on_c)):
                for j in range(i + 1, len(on_c)):
                    if _d(on_c[i][1], on_c[j][1]) <= tol:
                        tip = on_c[i][1]
                        b.kind = "CONNECTOR"
                        b.pointer = tip
                        tri = (min(tip[0], c.cx), min(tip[1], c.cy - c.r), max(tip[0], c.cx), max(tip[1], c.cy + c.r))
                        drop = {id(on_c[i][0]), id(on_c[j][0])}
                        drop |= {id(p) for p in glyphs if len(p.segs) == 1 and p.bbox[0] >= min(c.cx + c.r * 0.5, tip[0]) - tol
                                 and _in_rect((p.bbox[0], p.bbox[1]), tri, tol) and _in_rect((p.bbox[2], p.bbox[3]), tri, tol)
                                 and not _in_rect(((p.bbox[0] + p.bbox[2]) / 2, (p.bbox[1] + p.bbox[3]) / 2), c.bbox, -tol)}
                        wires = [p for p in wires if id(p) not in drop]
                        glyphs = [p for p in glyphs if id(p) not in drop]
                        break
                if b.kind == "CONNECTOR":
                    break
        b.circle = c
        blocks.append(b)

    # 블록 사이를 잇는 짧은 토막 — 글자 크기라도 두 끝이 다 블록 · 화살촉 · 선에 닿으면 선이다
    wire_segs0 = [sg for p in wires for sg in p.segs]

    def anchored(q):
        return (any(_block_edge(q, b, tol) for b in blocks) or
                any(_in_rect(q, a.bbox, tol) for a in arrows) or
                any(_on_seg(q, w, tol)[0] for w in wire_segs0))
    for p in list(glyphs):
        if len(p.segs) != 1 or not (p.segs[0].vert or p.segs[0].horiz):
            continue
        a, b = p.segs[0].ends()
        if any(p.bbox[0] >= bl.bbox[0] - tol and p.bbox[2] <= bl.bbox[2] + tol and
               p.bbox[1] >= bl.bbox[1] - tol and p.bbox[3] <= bl.bbox[3] + tol for bl in blocks):
            continue                    # 블록 안의 글자 획
        if anchored(a) and anchored(b):
            glyphs.remove(p)
            wires.append(p)

    # ---- 입력 막대: 화살촉 꼭지가 몸통에 닿는 곧은 선 중 블록에 붙은 것
    tip_arrows = [a for k, a in enumerate(arrows) if k not in pointer_arrows]
    bus_of = {}                         # id(poly) → block
    for p in wires:
        if len(p.segs) != 1:
            continue
        s = p.segs[0]
        if not (s.vert or s.horiz):
            continue
        if not any(_on_seg(a.tip, s, tol)[0] for a in tip_arrows):
            continue
        b = _block_touching_bus(s, blocks, tol)
        if b is not None:
            bus_of[id(p)] = b
            b.bus.append((s.x0, s.y0, s.x1, s.y1))
    wires = [p for p in wires if id(p) not in bus_of]

    # ---- 파선: 글자 크기 조각 중 한 줄로 늘어선 것 (끝이 선이나 단자에 닿는 줄만)
    short = [p for p in wires if p.size < P]
    dashed, rest = _dash_chains(glyphs + short, [p for p in wires if p.size >= P], blocks, arrows, dots, P, tol)
    taken = {id(p) for p in glyphs + short} - {id(p) for p in rest}
    glyphs = [p for p in glyphs if id(p) not in taken]
    wires = [p for p in wires if id(p) not in taken] + dashed

    # ---- 선 잇기 (union-find on segments)
    segs = []                           # (seg, poly)
    for p in wires:
        for s in p.segs:
            segs.append((s, p))
    parent = list(range(len(segs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        a, b = find(i), find(j)
        if a != b:
            parent[b] = a

    # 같은 path 안의 조각은 하나
    first = {}
    for i, (s, p) in enumerate(segs):
        if id(p) in first:
            union(first[id(p)], i)
        else:
            first[id(p)] = i
    # 격자 색인
    cell = max(P, 1.0)
    grid = defaultdict(list)
    for i, (s, p) in enumerate(segs):
        for gx in range(int(min(s.x0, s.x1) // cell) - 1, int(max(s.x0, s.x1) // cell) + 2):
            for gy in range(int(min(s.y0, s.y1) // cell) - 1, int(max(s.y0, s.y1) // cell) + 2):
                grid[(gx, gy)].append(i)

    def near(pt):
        return grid.get((int(pt[0] // cell), int(pt[1] // cell)), [])

    # 파선의 안쪽 토막 끝은 잇지 않는다 — 가로지르는 실선과 우연히 닿아도 연결이 아니다
    free_of = {}
    for p in wires:
        if p.dashed:
            cnt = defaultdict(int)
            for sg in p.segs:
                for q in sg.ends():
                    cnt[(round(q[0], 2), round(q[1], 2))] += 1
            free_of[id(p)] = {q for q, c in cnt.items() if c == 1}

    def joinable(e, p):
        f = free_of.get(id(p))
        return f is None or (round(e[0], 2), round(e[1], 2)) in f

    for i, (s, p) in enumerate(segs):
        for e in s.ends():
            if not joinable(e, p):
                continue
            for j in near(e):
                if j == i or segs[j][1] is p:
                    continue
                if _on_seg(e, segs[j][0], tol)[0]:
                    union(i, j)
    bridged = []
    # 연결점 (칠한 점 · 속 빈 작은 원)
    for c in dots:
        hit = []
        for j in near((c.cx, c.cy)):
            s = segs[j][0]
            if _on_seg((c.cx, c.cy), s, c.r + tol)[0]:
                hit.append(j)
        for j in hit[1:]:
            union(hit[0], j)
    # 마커(◆ ■)는 선 위에 그린 표시 — 양쪽 선을 잇는다
    for m in markers:
        hit = [j for j in near(((m[0] + m[2]) / 2, (m[1] + m[3]) / 2))
               if any(_in_rect(e, m, tol) for e in segs[j][0].ends())]
        for j in hit[1:]:
            union(hit[0], j)

    # 끊어 그린 교차 — 한 직선의 두 끝이 마주 보고 그 틈을 다른 선이 직각으로 지나가면 같은 선이다
    # (범례 G003: "BROKEN LINE REPRESENTS NO LOGIC CONNECTION" — 지나가는 선과는 잇지 않는다)
    loose = []
    for i, (s, p) in enumerate(segs):
        if not (s.vert or s.horiz):
            continue
        for e in s.ends():
            if not joinable(e, p):
                continue
            if any(j != i and _on_seg(e, segs[j][0], tol)[0] for j in near(e)):
                continue
            if any(_d(e, (c.cx, c.cy)) <= c.r + tol for c in dots):
                continue
            if any(_block_edge(e, b, tol * 2) for b in blocks) or any(_in_rect(e, a.bbox, tol) for a in arrows):
                continue
            # 바깥쪽 방향 (선분 안쪽 → 끝)
            o = s.ends()[1] if e == s.ends()[0] else s.ends()[0]
            loose.append((e, i, ("v" if s.vert else "h"), (e[0] - o[0], e[1] - o[1])))
    for a in range(len(loose)):
        ea, ia, axa, va = loose[a]
        for b in range(a + 1, len(loose)):
            eb, ib, axb, vb = loose[b]
            if axa != axb or find(ia) == find(ib):
                continue
            if axa == "v" and abs(ea[0] - eb[0]) > 0.05:
                continue
            if axa == "h" and abs(ea[1] - eb[1]) > 0.05:
                continue
            g = _d(ea, eb)
            if g == 0 or g > P:
                continue
            # 서로를 향하는가
            if (eb[0] - ea[0]) * va[0] + (eb[1] - ea[1]) * va[1] <= 0:
                continue
            if (ea[0] - eb[0]) * vb[0] + (ea[1] - eb[1]) * vb[1] <= 0:
                continue
            mid = ((ea[0] + eb[0]) / 2, (ea[1] + eb[1]) / 2)
            crossed = False
            for j in near(mid):
                t = segs[j][0]
                if (axa == "v" and t.horiz or axa == "h" and t.vert) and _on_seg(mid, t, g / 2)[0]:
                    crossed = True
                    break
            if crossed:
                union(ia, ib)
                bridged.append((ea, eb))

    roots = {}
    for i in range(len(segs)):
        r = find(i)
        roots.setdefault(r, len(roots) + 1)
    seg_net = [roots[find(i)] for i in range(len(segs))]
    for i, (s, p) in enumerate(segs):
        n = sh.nets.setdefault(seg_net[i], {"segs": [], "dashed": False})
        n["segs"].append((round(s.x0, 2), round(s.y0, 2), round(s.x1, 2), round(s.y1, 2)))
        if p.dashed:
            n["dashed"] = True

    for ea, eb in bridged:
        for i, (sg, p) in enumerate(segs):
            if _d(ea, sg.ends()[0]) < 1e-6 or _d(ea, sg.ends()[1]) < 1e-6:
                sh.nets[seg_net[i]].setdefault("jumps", []).append(
                    (round(ea[0], 2), round(ea[1], 2), round(eb[0], 2), round(eb[1], 2)))
                break

    # ---- 선 끝 붙이기
    deg = defaultdict(int)              # 끝점이 다른 조각과 닿는가
    for i, (s, p) in enumerate(segs):
        for e in s.ends():
            if not joinable(e, p):
                continue
            touched = False
            for j in near(e):
                if j != i and (segs[j][1] is p or joinable(e, p)) and _on_seg(e, segs[j][0], tol)[0]:
                    touched = True
                    break
            if not touched:
                for c in dots:
                    if _d(e, (c.cx, c.cy)) <= c.r + tol:
                        touched = True
                        break
            if not touched and any(_d(e, q) < 1e-6 for br in bridged for q in br):
                touched = True
            if not touched:
                deg[(i, e)] = 0

    used_arrows = set()
    for (i, e) in list(deg):
        net = seg_net[i]
        att = _attach(e, segs[i][0], blocks, tip_arrows, bus_of, lay, tol, markers)
        if att is None:
            sh.dangling.append((round(e[0], 2), round(e[1], 2), net))
            continue
        kind, info = att
        if kind == "row":
            side, n = info
            sh.rows.append({"n": n, "side": side, "net": net, "at": (round(e[0], 2), round(e[1], 2))})
        elif kind == "port":
            b, d, side, ci, at, ak = info
            if ak is not None:
                used_arrows.add(ak)
            sh.ports.append(Port(b.id, net, d, (round(at[0], 2), round(at[1], 2)), side, ci))
        elif kind == "arrow-nowhere":
            sh.stray_arrows.append((round(info[0], 2), round(info[1], 2), net))

    # 아무 데도 닿지 않는 작은 넷은 글자다 (큰 글씨의 획 — 블록 밖 제목 · 각주)
    attached = {pt.net for pt in sh.ports} | {r["net"] for r in sh.rows}
    for nid in list(sh.nets):
        if nid in attached:
            continue
        xs = [v for sg in sh.nets[nid]["segs"] for v in (sg[0], sg[2])]
        ys = [v for sg in sh.nets[nid]["segs"] for v in (sg[1], sg[3])]
        if max(max(xs) - min(xs), max(ys) - min(ys)) < P:
            del sh.nets[nid]
            sh.dangling = [d for d in sh.dangling if d[2] != nid]
            sh.stray_arrows = [d for d in sh.stray_arrows if d[2] != nid]

    # 위·아래 변 단자의 방향 — 넷에 다른 몰이가 있으면 들어오는 쪽
    drivers = defaultdict(int)
    for pt in sh.ports:
        if pt.dir == "out":
            drivers[pt.net] += 1
    for r in sh.rows:
        if r["side"] == "L":
            drivers[r["net"]] += 1
    for pt in sh.ports:
        if pt.dir == "?":
            pt.dir = "in" if drivers[pt.net] else "out"
            if pt.dir == "out":
                drivers[pt.net] += 1

    # 글자 획 → 블록 안
    for b in blocks:
        bb = b.bbox
        for p in glyphs:
            cx, cy = (p.bbox[0] + p.bbox[2]) / 2, (p.bbox[1] + p.bbox[3]) / 2
            if _in_rect((cx, cy), bb, 0):
                b.glyphs.append(p.pid)
    sh.blocks = {b.id: b for b in blocks}
    sh.glyph_polys = glyphs
    fr = prims.frame
    sh.frame = fr
    sh.all_glyphs = [p for p in prims.polys if p.size < P and
                     (fr is None or (p.bbox[0] >= fr[0] and p.bbox[2] <= fr[2] and p.bbox[1] >= fr[1] and p.bbox[3] <= fr[3]))]          # 표 칸 글자는 한 행 안에 든다
    sh.words = prims.words
    return sh


def _assemble_rects(polys, rects, P, tol):
    """흩어진 선분 넷이 둘러싼 상자 — 모서리를 비스듬히 깎거나 변을 따로 그린 양식 (G010 의 START 칸).

    위·아래 가로선이 같은 폭으로 마주 보고, 양 끝 세로선이 그 사이를 덮으면 상자다.  모서리 틈은 짧은 변의
    25% 까지 (깎은 모서리 · 겹선).  크기는 블록 크기(행 간격의 0.2~6배)만.  이미 있는 사각형과 겹치면 두지 않는다.
    """
    H, V = [], []
    for p in polys:
        if len(p.segs) > 6:                 # 글자 획 (곡선을 잘게 그린 것)
            continue
        for sg in p.segs:
            if sg.length < RECT_MIN * P * 0.5:
                continue
            if sg.horiz:
                H.append((min(sg.x0, sg.x1), max(sg.x0, sg.x1), sg.y0, p))
            elif sg.vert:
                V.append((min(sg.y0, sg.y1), max(sg.y0, sg.y1), sg.x0, p))
    H.sort(key=lambda h: h[2])
    out, used = [], set()
    have = [(r.x0, r.y0, r.x1, r.y1) for r in rects]
    for i, (a0, a1, ya, pa) in enumerate(H):
        if a1 - a0 > 6 * P:
            continue
        for b0, b1, yb, pb in H[i + 1:]:
            h = yb - ya
            if h > 6 * P:
                break
            if h < RECT_MIN * P:
                continue
            w = min(a1, b1) - max(a0, b0)
            g = 0.25 * min(w, h)
            if w < RECT_MIN * P or abs(a0 - b0) > g or abs(a1 - b1) > g:
                continue
            x0, x1 = min(a0, b0), max(a1, b1)
            sides = []
            for xx in (x0, x1):
                cand = [v for v in V if abs(v[2] - xx) <= g and v[0] <= ya + g and v[1] >= yb - g]
                if not cand:
                    break
                sides.append(cand[0])
            if len(sides) != 2:
                continue
            bb = (x0, ya, x1, yb)
            area = (bb[2] - bb[0]) * (bb[3] - bb[1])
            if any(_overlap_frac(bb, q) > 0.5 and (q[2] - q[0]) * (q[3] - q[1]) < 3 * area for q in have):
                continue
            out.append(geom.Rect(*bb))
            have.append(bb)
            # 상자 변으로만 쓰인 선만 치운다 — 상자보다 긴 세로선은 입력 막대일 수 있다 (그대로 둔다)
            for q, span in ((pa, (a0, a1)), (pb, (b0, b1))):
                if len(q.segs) == 1 or q.size <= (x1 - x0) + g:
                    used.add(id(q))
            for v in sides:
                if v[1] - v[0] <= h + 2 * g and (len(v[3].segs) == 1 or v[3].size <= max(h, x1 - x0) + 2 * g):
                    used.add(id(v[3]))
            break
    return out, used


def _overlap_frac(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    if w <= 0 or h <= 0:
        return 0.0
    return (w * h) / min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))


def _blob_dots(blobs, P):
    """칠한 조각들이 모여 만든 작은 원판 = 연결점 (점을 네 조각 · 여러 띠로 칠한 양식)."""
    small = [b for b in blobs if max(b[2] - b[0], b[3] - b[1]) < DOT_MAX * P]
    n = len(small)
    par = list(range(n))

    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    for i in range(n):
        a = small[i]
        for j in range(i + 1, n):
            b = small[j]
            if a[0] <= b[2] + 0.01 and b[0] <= a[2] + 0.01 and a[1] <= b[3] + 0.01 and b[1] <= a[3] + 0.01:
                par[f(j)] = f(i)
    grp = defaultdict(list)
    for i in range(n):
        grp[f(i)].append(small[i])
    out = []
    for g in grp.values():
        bb = (min(b[0] for b in g), min(b[1] for b in g), max(b[2] for b in g), max(b[3] for b in g))
        w, h = bb[2] - bb[0], bb[3] - bb[1]
        if len(g) >= 2 and w > 0 and 0.75 < h / w < 1.33 and max(w, h) < DOT_MAX * P:
            out.append(geom.Circle((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2, (w + h) / 4, bb))
    return out


def _free_ends(segs):
    cnt = defaultdict(int)
    for sg in segs:
        for q in sg.ends():
            cnt[(round(q[0], 2), round(q[1], 2))] += 1
    return [q for q, c in cnt.items() if c == 1]


def _dedupe_nested(rects, gap):
    """이중 테두리 — 다른 사각형 안쪽에 gap 이내로 붙은 사각형은 버린다."""
    out = []
    for r in rects:
        inner = False
        for o in rects:
            if o is r:
                continue
            if (o.x0 <= r.x0 and o.y0 <= r.y0 and o.x1 >= r.x1 and o.y1 >= r.y1 and
                    (r.x0 - o.x0) <= gap and (o.x1 - r.x1) <= gap and (r.y0 - o.y0) <= gap and (o.y1 - r.y1) <= gap and
                    (o.w > r.w or o.h > r.h)):
                inner = True
                break
        if not inner:
            out.append(r)
    return out


def _group_frames(rects, circles):
    frames = set()
    for r in rects:
        n = sum(1 for o in rects if o is not r and o.x0 >= r.x0 and o.x1 <= r.x1 and o.y0 >= r.y0 and o.y1 <= r.y1)
        n += sum(1 for c in circles if r.x0 <= c.cx <= r.x1 and r.y0 <= c.cy <= r.y1)
        if n >= 3:
            frames.add(id(r))
    return frames


def _touching_groups(rects, tol):
    """변을 맞댄 사각형끼리 한 블록."""
    n = len(rects)
    par = list(range(n))

    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    for i in range(n):
        a = rects[i]
        for j in range(i + 1, n):
            b = rects[j]
            ov_x = min(a.x1, b.x1) - max(a.x0, b.x0)
            ov_y = min(a.y1, b.y1) - max(a.y0, b.y0)
            share_h = (abs(a.y1 - b.y0) <= tol or abs(b.y1 - a.y0) <= tol) and ov_x > 0.5 * min(a.w, b.w)
            share_v = (abs(a.x1 - b.x0) <= tol or abs(b.x1 - a.x0) <= tol) and ov_y > 0.5 * min(a.h, b.h)
            if share_h or share_v:
                par[f(j)] = f(i)
    out = defaultdict(list)
    for i in range(n):
        out[f(i)].append(rects[i])
    return list(out.values())


def _block_touching_bus(s, blocks, tol):
    for b in blocks:
        if b.kind == "RECT":
            x0, y0, x1, y1 = b.bbox
            if s.vert and (abs(s.x0 - x0) <= tol or abs(s.x0 - x1) <= tol):
                lo, hi = sorted((s.y0, s.y1))
                if min(hi, y1) - max(lo, y0) > 0:
                    return b
            if s.horiz and (abs(s.y0 - y0) <= tol or abs(s.y0 - y1) <= tol):
                lo, hi = sorted((s.x0, s.x1))
                if min(hi, x1) - max(lo, x0) > 0:
                    return b
        else:
            c = b.circle
            # 막대가 원에 닿는다 (접선)
            ok, _ = _on_seg((c.cx - c.r, c.cy), s, tol) if s.vert else (False, 0)
            if not ok and s.vert:
                ok, _ = _on_seg((c.cx + c.r, c.cy), s, tol)
            if not ok and s.horiz:
                ok = _on_seg((c.cx, c.cy - c.r), s, tol)[0] or _on_seg((c.cx, c.cy + c.r), s, tol)[0]
            if ok:
                return b
    return None


def _block_edge(q, b, tol):
    if b.kind == "RECT":
        return any(_rect_edge(q, c, tol) for c in b.cells)
    c = b.circle
    return abs(_d(q, (c.cx, c.cy)) - c.r) <= tol


def _attach(e, seg, blocks, arrows, bus_of, lay, tol, markers=()):
    LX0, LY0, LX1, LY1 = lay.logic
    # 0) 경계에 붙은 인터페이스 표시(◆ ■)에 닿은 끝 — 그 표시가 선 대신 경계까지 간다
    for m in markers:
        if _in_rect(e, m, tol * 2):
            cy = (m[1] + m[3]) / 2
            mw = m[2] - m[0]
            if m[0] - LX0 <= mw:                    # 표시가 경계에 붙어 있다 (그 폭 안)
                return "row", ("L", _row_at(lay.left_rows, cy))
            if LX1 - m[2] <= mw:
                return "row", ("R", _row_at(lay.right_rows, cy))
    # 1) 화살촉이 붙은 끝 — 꼭지가 닿는 것이 받는 쪽
    for k, a in enumerate(arrows):
        if _d(e, a.base) <= tol or _d(e, a.tip) <= tol or _in_rect(e, a.bbox, tol):
            tip = a.tip
            # 꼭지에서 화살 방향으로 조금 더 — 꼭지가 변에 정확히 안 닿는 그림도 있다
            probe = (tip[0] + a.dir[0] * tol, tip[1] + a.dir[1] * tol)
            for b in blocks:
                for bs in b.bus:
                    s = geom.Seg(*bs)
                    if _on_seg(tip, s, tol * 2)[0] or _on_seg(probe, s, tol * 2)[0]:
                        return "port", (b, "in", "BUS", 0, tip, k)
            for b in blocks:
                if b.kind == "RECT":
                    for ci, c in enumerate(b.cells):
                        side = _rect_edge(tip, c, tol * 2) or _rect_edge(probe, c, tol * 2)
                        if side:
                            return "port", (b, "in", side, ci, tip, k)
                else:
                    c = b.circle
                    if abs(_d(tip, (c.cx, c.cy)) - c.r) <= tol * 2 or abs(_d(probe, (c.cx, c.cy)) - c.r) <= tol * 2:
                        return "port", (b, "in", "", 0, tip, k)
            if abs(tip[0] - LX1) <= tol * 3:
                return "row", ("R", _row_at(lay.right_rows, tip[1]))
            return "arrow-nowhere", tip
    # 2) 연결 기호의 꼭지에서 나가는 선
    for b in blocks:
        if b.kind == "CONNECTOR" and b.pointer and _d(e, b.pointer) <= tol * 2:
            return "port", (b, "out", "", 0, e, None)
    # 3) 상자 변 · 원
    for b in blocks:
        if b.kind == "RECT":
            for ci, c in enumerate(b.cells):
                side = _rect_edge(e, c, tol)
                if side:
                    d = {"R": "out", "L": "in"}.get(side, "?")
                    return "port", (b, d, side, ci, e, None)
        else:
            c = b.circle
            if abs(_d(e, (c.cx, c.cy)) - c.r) <= tol * 2:
                # 꼭지 있는 연결 기호의 몸통 = 들어감 · 꼭지 없는 원은 넷 안에서 정한다 (다른 몰이가 있으면 들어감)
                d = "in" if b.kind == "CONNECTOR" else "?"
                return "port", (b, d, "", 0, e, None)
    # 4) LOGIC 경계 = 표의 행
    if abs(e[0] - LX0) <= tol * 3:
        return "row", ("L", _row_at(lay.left_rows, e[1]))
    if abs(e[0] - LX1) <= tol * 3:
        return "row", ("R", _row_at(lay.right_rows, e[1]))
    return None


def _row_at(rows, y):
    for n, a, b in rows:
        if a <= y <= b:
            return n
    return None


def _dash_chains(glyphs, wires, blocks, arrows, dots, P, tol):
    """파선 — 한 직선 위에 늘어선 짧은 조각들.

    조각은 축정렬 선분 하나 또는 꺾인 두 선분이다.  이웃 조각과 같은 직선 위에 있고 틈이 조각 길이의
    0.2~1.5배일 때 잇는다 (파선의 틈은 토막 길이와 같은 자리수다 — 글자 획 사이의 틈은 그렇지 않다).
    조각 셋 이상이면서 끝 하나가, 또는 조각 둘이면서 두 끝이 모두 선 · 블록 · 화살촉 · 연결점에 닿을
    때만 파선이다.
    """
    def enclosed(p):
        return any(b.kind == "RECT" and p.bbox[0] >= b.bbox[0] - tol and p.bbox[2] <= b.bbox[2] + tol and
                   p.bbox[1] >= b.bbox[1] - tol and p.bbox[3] <= b.bbox[3] + tol for b in blocks)
    pieces = [p for p in glyphs if len(p.segs) <= 2 and all(s.vert or s.horiz for s in p.segs)
              and all(s.length > 0 for s in p.segs) and not enclosed(p)]
    if len(pieces) < 2:
        return [], glyphs
    ends = []                                   # (pt, piece, axis 'h'|'v', seg length)
    for k, p in enumerate(pieces):
        cnt = defaultdict(int)
        for sg in p.segs:
            for q in sg.ends():
                cnt[(round(q[0], 2), round(q[1], 2))] += 1
        for sg in p.segs:
            for q in sg.ends():
                if cnt[(round(q[0], 2), round(q[1], 2))] == 1:
                    ends.append((q, k, "h" if sg.horiz else "v", sg.length))
    par = list(range(len(pieces)))

    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    def term(q):
        # 화살촉 · 블록 변에 닿은 끝은 거기서 끝난다 — 건너뛰어 잇지 않는다
        return any(_in_rect(q, a.bbox, tol) for a in arrows) or any(_block_edge(q, b, tol) for b in blocks)

    grid = defaultdict(list)
    for idx, (q, k, ax, L) in enumerate(ends):
        grid[(int(q[0] // P), int(q[1] // P))].append(idx)
    bridges, cand = [], []
    for ia, (qa, ka, axa, La) in enumerate(ends):
        gx, gy = int(qa[0] // P), int(qa[1] // P)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for ib in grid.get((gx + dx, gy + dy), []):
                    if ib <= ia:
                        continue
                    qb, kb, axb, Lb = ends[ib]
                    if kb == ka or axa != axb:
                        continue
                    same_line = abs(qa[1] - qb[1]) < 0.05 if axa == "h" else abs(qa[0] - qb[0]) < 0.05
                    if not same_line:
                        continue
                    if term(qa) or term(qb):
                        continue
                    g = _d(qa, qb)
                    Lm = max(La, Lb)
                    if 0.2 * Lm <= g <= 1.5 * Lm:
                        cand.append((g, ia, ib))
    # 끝마다 가장 가까운 짝 하나만 (먼 짝을 또 이으면 토막을 건너뛴 다리가 생긴다)
    used = set()
    for g, ia, ib in sorted(cand):
        if ia in used or ib in used:
            continue
        used.update((ia, ib))
        qa, ka = ends[ia][0], ends[ia][1]
        qb, kb = ends[ib][0], ends[ib][1]
        if f(ka) != f(kb):
            par[f(kb)] = f(ka)
        bridges.append((qa, qb, ka))
    groups = defaultdict(list)
    for k in range(len(pieces)):
        groups[f(k)].append(k)
    out, taken = [], set()
    wire_segs = [s for p in wires for s in p.segs]

    def touches(q):
        return (any(_on_seg(q, w, tol)[0] for w in wire_segs) or
                any(_in_rect(q, a.bbox, tol) for a in arrows) or
                any(_d(q, (c.cx, c.cy)) <= c.r + tol for c in dots) or
                any(_block_edge(q, b, tol * 2) for b in blocks))
    for root, ks in groups.items():
        if len(ks) < 2:
            continue
        kset = set(ks)
        segs = [s for k in ks for s in pieces[k].segs]
        for qa, qb, ka in bridges:
            if ka in kset:
                segs.append(geom.Seg(qa[0], qa[1], qb[0], qb[1]))
        cnt = defaultdict(int)
        for sg in segs:
            for q in sg.ends():
                cnt[(round(q[0], 2), round(q[1], 2))] += 1
        free = [q for q, c in cnt.items() if c == 1]
        # 파선은 고르다 — 토막 길이와 틈이 서로 두 배 안 (글자 획은 고르지 않다)
        lens = [sg.length for k in ks for sg in pieces[k].segs]
        gaps_ = [_d(qa, qb) for qa, qb, ka in bridges if ka in kset]
        if max(lens) > 2 * min(lens) or (gaps_ and max(gaps_) > 2 * min(gaps_)):
            continue
        Lmed = sorted(lens)[len(lens) // 2]
        near_arrow = lambda q: any(_d(q, a.base) <= 1.5 * Lmed for a in arrows)
        hit = sum(1 for q in free if touches(q) or near_arrow(q))
        if not ((len(ks) >= 3 and hit >= 1) or (len(ks) == 2 and hit >= 2 and len(free) == 2)):
            continue
        # 파선이 화살촉 앞에서 틈 하나를 두고 끝나면 그 틈도 잇는다 (토막 길이 1.5배 안 · 같은 직선)
        Lmed = sorted(lens)[len(lens) // 2]
        for q in free:
            for a in arrows:
                if _d(q, a.base) <= 1.5 * Lmed and (abs(q[0] - a.base[0]) < tol or abs(q[1] - a.base[1]) < tol):
                    segs.append(geom.Seg(q[0], q[1], a.base[0], a.base[1]))
                    break
        pts = [q for s in segs for q in s.ends()]
        out.append(geom.Poly(segs, geom._bbox(pts), dashed=True, pid=pieces[ks[0]].pid))
        taken.update(id(pieces[k]) for k in ks)
    return out, [p for p in glyphs if id(p) not in taken]
