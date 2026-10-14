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
from collections import Counter, defaultdict
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
    # 따로 그린 호 조각이 닫힌 원 (L21 · 19VA OR · 메모리 우선 표시 원) — 글자보다 큰 것만 원이다
    ring_pids = set()
    ovals = []
    for c, pids in getattr(prims, "rings", []):
        if inside(c.bbox) and 2 * c.r >= GLYPH_MAX * P:
            c.ring = True
            if getattr(c, "oval", False):
                # 타원은 둥근 상자로 — 단자는 왼쪽·오른쪽 끝.  안에 진짜 글자(ANN)가 있을 때만 (선 글자 묶음은 예전 그대로)
                if not any(c.bbox[0] <= (w[0] + w[2]) / 2 <= c.bbox[2] and c.bbox[1] <= (w[1] + w[3]) / 2 <= c.bbox[3]
                           for w in prims.words):
                    continue
                r_ = geom.Rect(*c.bbox)
                r_.rounded = True
                ovals.append(r_)
            else:
                circles.append(c)
            ring_pids |= pids
    if ring_pids:
        wires = [p for p in wires if p.pid not in ring_pids or not getattr(p, "curved", False)]
        glyphs = [p for p in glyphs if p.pid not in ring_pids or not getattr(p, "curved", False)]
    dots = [c for c in circles if 2 * c.r < DOT_MAX * P]
    dots += _blob_dots([b for b in prims.blobs if inside(b)], P)
    bigc = [c for c in circles if 2 * c.r >= DOT_MAX * P]
    arrows = [a for a in prims.arrows if inside(a.bbox)]

    # ---- 상자: 겹친 사각형(이중 테두리)은 하나로, 변을 나눈 사각형(S/Ro · PB|START)은 한 블록의 칸으로
    rects = [r for r in prims.rects if inside((r.x0, r.y0, r.x1, r.y1))
             and r.w >= RECT_MIN * P and r.h >= RECT_MIN * P] + ovals
    rects, split_by = _split_by_divider(rects, wires + glyphs, P, tol)
    if split_by:
        wires = [p for p in wires if id(p) not in split_by]
        glyphs = [p for p in glyphs if id(p) not in split_by]
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
    # 블록 이름은 겹치지 않게 — 빗금 표시로 판정해 빠진 블록 뒤에 len+1 을 쓰면 앞 블록과 같은 이름이 되어
    # 한쪽이 사라졌다 (G009 의 AND 가 램프 G 에 덮였다)
    nid = lambda: f"B{max([int(b.id[1:]) for b in blocks] + [0]) + 1}"
    for g in groups:
        bb = (min(r.x0 for r in g), min(r.y0 for r in g), max(r.x1 for r in g), max(r.y1 for r in g))
        cells = sorted(((r.x0, r.y0, r.x1, r.y1) for r in g), key=lambda c: (round(c[1], 1), c[0]))
        blocks.append(Block(nid(), "RECT", bb, cells=cells))
        blocks[-1].rounded = any(getattr(r, "rounded", False) for r in g)

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
                blocks.append(Block(nid(), "RECT", cell, cells=[cell]))
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
    tri_cand = [p for p in wires + glyphs if len(p.segs) <= 3 and all(sg.length > 0 for sg in p.segs)]
    marks_in = []
    for c in bigc:
        if any(
                bl.kind == "RECT" and _in_rect((c.cx, c.cy), bl.bbox, 0)
                and (getattr(c, "ring", False) or 2 * c.r >= 0.6 * min(bl.bbox[2] - bl.bbox[0], bl.bbox[3] - bl.bbox[1]))
                # L23 — 칸을 채우는 원(글자를 두른 원 · 1A1Y 메모리 R)만 표시다.  큰 매크로 상자 안의 연결 기호 원은 블록이다 and c.bbox[0] >= bl.bbox[0] - tol
                and c.bbox[2] <= bl.bbox[2] + tol and c.bbox[1] >= bl.bbox[1] - tol and c.bbox[3] <= bl.bbox[3] + tol
                for bl in blocks):
            marks_in.append(c)            # 상자 안 글자를 두른 원 = 그 칸의 표시 (메모리 우선 칸 · 범례 MEMORY) — 블록이 아니다
            continue
        b = Block(nid(), "CIRCLE", c.bbox)
        for k, a in enumerate(arrows):
            if abs(_d(a.base, (c.cx, c.cy)) - c.r) <= max(tol, 0.25 * c.r) and _d(a.tip, (c.cx, c.cy)) > c.r:
                b.kind = "CONNECTOR"
                b.pointer = a.tip
                pointer_arrows.add(k)
                break
        if b.kind == "CIRCLE":
            # 선 둘이 원에서 나와 한 꼭지에서 만나면 꼭지 삼각형 (안을 빗금으로 칠한 양식)
            # 꼭지 삼각형의 두 변은 한 경로(선 셋)로 그리기도 한다 · 안의 빗금(서로 붙은 짧은 획)이
            # 원에 닿아 가짜 꼭지를 만들지 않게, 두 변이 원 위에서 벌어져야 하고(밑변 = 현) 가장 먼 꼭지를 쓴다
            on_c = []
            for p in tri_cand:
                for sg in p.segs:
                    e0, e1 = sg.ends()
                    for a_, t_ in ((e0, e1), (e1, e0)):
                        if abs(_d(a_, (c.cx, c.cy)) - c.r) <= max(tol, 0.25 * c.r) and _d(t_, (c.cx, c.cy)) > c.r * 1.2:
                            on_c.append((p, t_, a_))
            best = None
            for i in range(len(on_c)):
                for j in range(i + 1, len(on_c)):
                    if (on_c[i][0] is not on_c[j][0] or len(on_c[i][0].segs) > 1) and \
                            _d(on_c[i][1], on_c[j][1]) <= tol and _d(on_c[i][2], on_c[j][2]) >= 0.5 * c.r:
                        far = _d(on_c[i][1], (c.cx, c.cy))
                        if best is None or far > best[0]:
                            best = (far, i, j)
            if best is not None:
                _, i, j = best
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
        # 화살은 막대를 가로질러 꽂힌다 — 화살과 나란한 선은 그 화살이 달린 신호선이지 막대가 아니다
        # (선이 꼭지를 조금 지나 상자 변까지 그려진 G012 AND 입력 실측)
        if not any(_on_seg(a.tip, s, tol)[0] and
                   (abs(a.tip[1] - a.base[1]) > abs(a.tip[0] - a.base[0]) if s.horiz else
                    abs(a.tip[0] - a.base[0]) > abs(a.tip[1] - a.base[1])) for a in tip_arrows):
            # L21 — 화살 없이 선이 막대에 닿는 양식 (19VA AND · OR): 막대가 작은 블록의 들어오는 변 가운데에
            # 붙고 그 블록보다 위아래로 길게 뻗으면 입력 막대다 (범례 SIGNAL PROCESSING SYMBOLS 의 AND · OR 그림)
            b = _bar_gate(s, blocks, tol)
            if b is not None:
                bus_of[id(p)] = b
                b.bus.append((s.x0, s.y0, s.x1, s.y1))
                b.bar = True
            continue
        b = _block_touching_bus(s, blocks, tol)
        if b is not None:
            bus_of[id(p)] = b
            b.bus.append((s.x0, s.y0, s.x1, s.y1))
    wires = [p for p in wires if id(p) not in bus_of]

    # ---- 파선: 글자 크기 조각 중 한 줄로 늘어선 것 (끝이 선이나 단자에 닿는 줄만)
    short = [p for p in wires if p.size < P]
    dashed, rest = _dash_chains(glyphs + short, [p for p in wires if p.size >= P], blocks, arrows, dots, P, tol,
                                bounds=(LX0, LX1))
    taken = {id(p) for p in glyphs + short} - {id(p) for p in rest}
    glyphs = [p for p in glyphs if id(p) not in taken]
    wires = [p for p in wires if id(p) not in taken] + dashed
    pdf_dashed = [p for p in wires if p.dashed]
    keep = {id(p) for p in _drop_dashed_frames(pdf_dashed, (LX1 - LX0, LY1 - LY0), tol, P)}
    wires = [p for p in wires if not p.dashed or id(p) in keep]

    # ---- 선 잇기 (union-find on segments)
    segs = []                           # (seg, poly)
    seen_seg = set()
    flick_tips = []
    for p in wires:
        for s in p.segs:
            # L13 — 선 끝의 '열린 화살촉' 획: 같은 path 의 축 선분 끝에 붙은 짧은 사선 (글자 크기보다 작다).
            # 획을 선으로 치면 그 끝이 '닿은 끝' 이 되어 받는 게이트의 단자가 서지 않는다 (G012 OR 입력 막대 실측).
            if not (s.vert or s.horiz) and s.length < GLYPH_MAX * P and _flick(s, p, tol, GLYPH_MAX * P):
                continue
            # 같은 선을 두 번 그린 것(겹선)은 하나 — 겹친 짝이 서로의 끝을 '닿은 끝' 으로 만들어 단자가
            # 서지 않았다 (G037 GT → STEP_IN 실측)
            k = tuple(sorted(((round(s.x0, 2), round(s.y0, 2)), (round(s.x1, 2), round(s.y1, 2)))))
            if k in seen_seg:
                continue
            seen_seg.add(k)
            segs.append((s, p))
    # 다른 선 위에 통째로 포개진 짧은 축 선분(덧그린 토막)도 뺀다 — 그 끝이 긴 선의 끝을 '닿은 끝' 으로
    # 만들어 게이트 출력 단자가 서지 않았다 (G013 OR 출력 위 1.9pt 덧선 실측)
    lines_ = defaultdict(list)
    for i, (sg, p) in enumerate(segs):
        if sg.horiz:
            lines_[("h", round(sg.y0, 1))].append((min(sg.x0, sg.x1), max(sg.x0, sg.x1), i))
        elif sg.vert:
            lines_[("v", round(sg.x0, 1))].append((min(sg.y0, sg.y1), max(sg.y0, sg.y1), i))
    inner = set()
    for spans in lines_.values():
        if len(spans) < 2:
            continue
        for a0, a1, i in spans:
            if any(j != i and b0 <= a0 + 0.01 and b1 >= a1 - 0.01 and (b1 - b0) > (a1 - a0) + 0.01
                   for b0, b1, j in spans):
                inner.add(i)
    if inner:
        segs = [x for i, x in enumerate(segs) if i not in inner]
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
    # L13 — 한 path 에 떨어진 선이 여럿 들어 있을 수 있다 (CAD 가 같은 모양 선을 한 path 로 내보냄).  끝이 맞닿은
    # 조각만 잇는다 — 파선(틈이 있는 한 줄)만 path 하나를 통째로 한 선으로 본다.
    by_poly = defaultdict(list)
    for i, (s, p) in enumerate(segs):
        by_poly[id(p)].append(i)
    for idx in by_poly.values():
        p = segs[idx[0]][1]
        if p.dashed:
            for i in idx[1:]:
                union(idx[0], i)
            continue
        for a in range(len(idx)):
            for b in range(a + 1, len(idx)):
                sa, sb = segs[idx[a]][0], segs[idx[b]][0]
                if any(_d(x, y) <= tol for x in sa.ends() for y in sb.ends()):
                    union(idx[a], idx[b])
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

    def passes_through(i, e, j):
        """e(선분 i 의 끝)가 선분 j 의 몸통에 닿는데, i 와 한 직선으로 맞은편에 이어지는 선분이 e 에서 시작하면 —
        두 선이 서로 **지나가는** 교차다 (CAD 가 교차점에서 선을 끊어 그린 것).  범례 G003: 연결은 점(DOT)으로만 표시한다."""
        sj = segs[j][0]
        if _d(e, sj.ends()[0]) <= tol or _d(e, sj.ends()[1]) <= tol:
            return False                                 # j 의 끝 — 꺾임·T 가 아니라 맞닿음
        si = segs[i][0]
        if not (si.vert or si.horiz):
            return False
        o = si.ends()[1] if _d(e, si.ends()[0]) <= tol else si.ends()[0]
        out = (e[0] - o[0], e[1] - o[1])
        for k in near(e):
            if k in (i, j):
                continue
            sk = segs[k][0]
            if (sk.vert != si.vert) or (sk.horiz != si.horiz):
                continue
            qa, qb = sk.ends()
            for q, r in ((qa, qb), (qb, qa)):
                if _d(q, e) <= tol and (r[0] - e[0]) * out[0] + (r[1] - e[1]) * out[1] > 0:
                    return True
        return False

    for i, (s, p) in enumerate(segs):
        for e in s.ends():
            if not joinable(e, p):
                continue
            for j in near(e):
                if j == i or segs[j][1] is p:
                    continue
                if _on_seg(e, segs[j][0], tol)[0] and not passes_through(i, e, j):
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
    # 상자 변 위의 속 빈 작은 원 = 그 상자의 단자 (매크로 블록이 단자를 원으로 그린다 · G061 MOTOR GROUP BLOCK)
    pin_dot = {}
    for c in dots:
        for b in blocks:
            if b.kind != "RECT":
                continue
            for ci, cell_ in enumerate(b.cells):
                side = _rect_edge((c.cx, c.cy), cell_, max(tol, c.r))
                if side in ("L", "R"):
                    pin_dot[id(c)] = (b, ci, side)
                    break
            if id(c) in pin_dot:
                break
    pin_ports = []
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
                        pd = pin_dot.get(id(c))
                        if pd is not None and (s.horiz if pd[2] in ("L", "R") else s.vert):
                            b_, ci_, side_ = pd
                            pin_ports.append((i, b_, ci_, side_, (c.cx, c.cy)))
                        break
            if not touched and any(_d(e, q) < 1e-6 for br in bridged for q in br):
                touched = True
            if not touched:
                deg[(i, e)] = 0

    used_arrows = set()
    seen_pin = set()
    for i, b_, ci_, side_, at in pin_ports:
        k = (b_.id, round(at[0], 2), round(at[1], 2), seg_net[i])
        if k in seen_pin:
            continue
        seen_pin.add(k)
        sh.ports.append(Port(b_.id, seg_net[i], "in" if side_ == "L" else "out",
                             (round(at[0], 2), round(at[1], 2)), side_, ci_))
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
    for b in blocks:
        b.shape = _shape_of(b, glyphs, tol)
        b.marks = [((c.cx, c.cy), c.r) for c in marks_in if _in_rect((c.cx, c.cy), b.bbox, 0)]
    sh.blocks = {b.id: b for b in blocks}
    sh.glyph_polys = glyphs
    fr = prims.frame
    sh.frame = fr
    sh.all_glyphs = [p for p in prims.polys if p.size < P and
                     (fr is None or (p.bbox[0] >= fr[0] and p.bbox[2] <= fr[2] and p.bbox[1] >= fr[1] and p.bbox[3] <= fr[3]))]          # 표 칸 글자는 한 행 안에 든다
    sh.words = prims.words
    return sh


def _bar_gate(s, blocks, tol):
    """세로 막대 s 가 작은 블록(상자 · 원)의 왼쪽(들어오는 쪽) 가운데에 붙고 그 블록보다 위아래로 길면 그 블록."""
    if not s.vert:
        return None
    lo, hi = sorted((s.y0, s.y1))
    for b in blocks:
        if b.kind == "RECT":
            if len(b.cells) != 1:
                continue
            x0, y0, x1, y1 = b.bbox
            touch = abs(s.x0 - x0) <= tol
            cy = (y0 + y1) / 2
        elif b.kind == "CIRCLE":
            c = b.circle
            x0, y0, x1, y1 = c.bbox
            touch = abs(s.x0 - (c.cx - c.r)) <= tol
            cy = c.cy
        else:
            continue
        h = y1 - y0
        if touch and lo <= y0 + tol and hi >= y1 - tol and (hi - lo) >= h and abs((lo + hi) / 2 - cy) <= 0.25 * (hi - lo):
            return b
    # L23 — 막대가 한쪽으로만 길게 뻗은 그림 (1A5J LEAD SELECTION 의 AND: 상자 위 변에서 아래 입력까지).  가운데 조건만
    # 풀고, 막대가 상자 높이를 다 덮으며 상자 높이의 1.5 배 이상이고 그 상자 하나에만 붙을 때만.
    hit = []
    for b in blocks:
        if b.kind != "RECT" or len(b.cells) != 1:
            continue
        x0, y0, x1, y1 = b.bbox
        if abs(s.x0 - x0) <= tol and lo <= y0 + tol and hi >= y1 - tol and (hi - lo) >= 1.5 * (y1 - y0):
            hit.append(b)
    return hit[0] if len(hit) == 1 else None


def _shape_of(b, glyphs, tol):
    """블록 모양 열쇠 — 범례 그림과 맞대는 단위 (legend.py · blocks.classify 가 같은 열쇠를 쓴다).

    BAR_BOX  입력 막대 + 작은 네모    BAR_CIRCLE  입력 막대 + 작은 원
    CROSS_BOX  대각선 둘이 가로지르는 네모 (⊠)    ROUND_BOX  한쪽 끝이 둥근 상자    PULSE_BOX  ⎍ 획이 든 네모
    """
    bar = getattr(b, "bar", False) or bool(b.bus)
    if b.kind == "CIRCLE":
        return "BAR_CIRCLE" if bar else ""
    if b.kind != "RECT" or len(b.cells) != 1:
        return ""
    if bar:
        return "BAR_BOX"
    if getattr(b, "rounded", False):
        return "ROUND_BOX"
    x0, y0, x1, y1 = b.bbox
    w, h = x1 - x0, y1 - y0
    inner = [p for p in glyphs if p.bbox[0] >= x0 - tol and p.bbox[2] <= x1 + tol and p.bbox[1] >= y0 - tol and p.bbox[3] <= y1 + tol]
    diag = [sg for p in inner for sg in p.segs if not (sg.vert or sg.horiz) and sg.length >= 0.8 * math.hypot(w, h)]
    if len(diag) >= 2:
        return "CROSS_BOX"
    for p in inner:
        ax = [sg for sg in p.segs if sg.vert or sg.horiz]
        if len(p.segs) >= 5 and len(ax) == len(p.segs) and sum(1 for sg in ax if sg.vert) >= 2 and \
                (p.bbox[2] - p.bbox[0]) >= 0.4 * w:
            return "PULSE_BOX"
    return ""


def _split_by_divider(rects, polys, P, tol):
    """네모 하나를 가로로 가르는 선(양 끝이 좌·우 변에 닿는 가로선) = 위·아래 두 칸 (19VA MEMORY S/R · L21)."""
    out, used = [], set()
    for r in rects:
        hit = None
        if RECT_MIN * P <= r.w <= 3 * P and r.h >= 1.5 * r.w * 0.9:
            for p in polys:
                if len(p.segs) != 1 or not p.segs[0].horiz:
                    continue
                sg = p.segs[0]
                a, b = sorted((sg.x0, sg.x1))
                if abs(a - r.x0) <= tol and abs(b - r.x1) <= tol and r.y0 + 0.3 * r.h < sg.y0 < r.y1 - 0.3 * r.h:
                    hit = (sg.y0, p)
                    break
        if hit is None:
            out.append(r)
            continue
        y, p = hit
        out.append(geom.Rect(r.x0, r.y0, r.x1, y))
        out.append(geom.Rect(r.x0, y, r.x1, r.y1))
        used.add(id(p))
    return out, used


def _assemble_rects(polys, rects, P, tol):
    """흩어진 선분 넷이 둘러싼 상자 — 모서리를 비스듬히 깎거나 변을 따로 그린 양식 (G010 의 START 칸).

    위·아래 가로선이 같은 폭으로 마주 보고, 양 끝 세로선이 그 사이를 덮으면 상자다.  모서리 틈은 짧은 변의
    25% 까지 (깎은 모서리 · 겹선).  크기는 블록 크기(행 간격의 0.2~6배)만.  이미 있는 사각형과 겹치면 두지 않는다.
    """
    H, V = [], []
    for p in polys:
        if len(p.segs) > 6:                 # 글자 획 (곡선을 잘게 그린 것)
            continue
        if getattr(p, "curved", False):
            # L21 — 둥근 끝(곡선으로 그린 반원): 두 끝이 한 세로줄이면 그 줄이 상자의 변이고, 상자는 곡선이 닿는 데까지
            fe = _free_ends(p.segs)
            cb = getattr(p, "cbbox", p.bbox)
            if len(fe) == 2 and abs(fe[0][0] - fe[1][0]) < 0.05 and abs(fe[0][1] - fe[1][1]) >= RECT_MIN * P:
                x = fe[0][0]
                ext = cb[2] if cb[2] - x > x - cb[0] else cb[0]
                if abs(ext - x) < 0.1 * abs(fe[0][1] - fe[1][1]):
                    ext = x                 # 거의 곧은 곡선 — 둥근 끝이 아니다
                V.append((min(fe[0][1], fe[1][1]), max(fe[0][1], fe[1][1]), x, p, ext))
            continue
        for sg in p.segs:
            if sg.length < RECT_MIN * P * 0.5:
                continue
            if sg.horiz:
                H.append((min(sg.x0, sg.x1), max(sg.x0, sg.x1), sg.y0, p))
            elif sg.vert:
                V.append((min(sg.y0, sg.y1), max(sg.y0, sg.y1), sg.x0, p, sg.x0))
    H.sort(key=lambda h: h[2])
    out, used = [], set()
    have = [(r.x0, r.y0, r.x1, r.y1) for r in rects]
    edge = set()                            # 이미 어느 상자의 변이 된 가로선 (다른 상자의 변으로 다시 쓰지 않는다)
    for i, (a0, a1, ya, pa) in enumerate(H):
        if a1 - a0 > 6 * P or i in edge:
            continue
        # 마주 보는 아래 변 — 폭이 가장 잘 맞는 것 (겹 테두리 · 깎은 모서리 단추(G013 OPEN/STOP/CLOSE/AUTO)는
        # 안쪽 테두리가 바깥과 폭이 조금 달라 '처음 맞는 것' 을 고르면 이웃 단추의 변과 짝지어졌다)
        best = None
        for k, (b0, b1, yb, pb) in enumerate(H[i + 1:], start=i + 1):
            h = yb - ya
            if h > 6 * P:
                break
            if h < RECT_MIN * P or k in edge:
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
                # 곧은 변이 있으면 곧은 변 (곡선 끝은 곧은 변이 없을 때만 — 예전 상자를 바꾸지 않는다)
                cand.sort(key=lambda v: getattr(v[3], "curved", False))
                sides.append(cand[0])
            if len(sides) != 2:
                continue
            miss = abs(a0 - b0) + abs(a1 - b1)
            if best is None or miss < best[0] - 0.01 or (abs(miss - best[0]) <= 0.01 and h < best[1]):
                best = (miss, h, k, b0, b1, yb, pb, x0, x1, sides, g)
        if best is None:
            continue
        _, h, k, b0, b1, yb, pb, x0, x1, sides, g = best
        rounded = any(v[4] != v[2] for v in sides)
        if sides[0][4] != sides[0][2]:
            x0 = min(x0, sides[0][4])           # 둥근 끝 — 상자는 곡선이 닿는 데까지
        if sides[1][4] != sides[1][2]:
            x1 = max(x1, sides[1][4])
        bb = (x0, ya, x1, yb)
        area = (bb[2] - bb[0]) * (bb[3] - bb[1])
        if any(_overlap_frac(bb, q) > 0.5 and (q[2] - q[0]) * (q[3] - q[1]) < 3 * area for q in have):
            continue
        rr = geom.Rect(*bb)
        rr.rounded = rounded
        out.append(rr)
        have.append(bb)
        edge.update((i, k))
        # 상자 안쪽의 가로선(겹 테두리의 안쪽 변)도 이 상자의 것이다 — 이웃 상자의 변과 짝짓지 않는다
        edge.update(j for j, (c0, c1, yc, _) in enumerate(H)
                    if ya - tol <= yc <= yb + tol and c0 >= x0 - tol and c1 <= x1 + tol)
        # 상자 변으로만 쓰인 선만 치운다 — 상자보다 긴 세로선은 입력 막대일 수 있다 (그대로 둔다)
        for q, span in ((pa, (a0, a1)), (pb, (b0, b1))):
            if len(q.segs) == 1 or q.size <= (x1 - x0) + g:
                used.add(id(q))
        for v in sides:
            if v[1] - v[0] <= h + 2 * g and (len(v[3].segs) == 1 or v[3].size <= max(h, x1 - x0) + 2 * g):
                used.add(id(v[3]))
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


def _flick(s, p, tol, wire_min):
    """사선 s 의 한 끝이 같은 path 의 **선 길이** 축 선분(글자 획보다 긴 것) 끝과 맞닿는가 — 열린 화살촉의 한 획.
    큰 글자(제목)의 사선 획은 짧은 획끼리 붙어 있어 걸리지 않는다."""
    for t in p.segs:
        if t is s or not (t.vert or t.horiz) or t.length <= s.length or t.length < wire_min:
            continue
        for a in s.ends():
            for b in t.ends():
                if _d(a, b) <= tol:
                    return True
    return False


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
            # 꼭지는 선(연결점)에 꽂히고 밑동이 블록 변에 붙어 있다 — 블록 출력이 화살 하나로 선에 들어간다
            # (G009 NOT ▶○ FLT 실측: NOT 과 연결점 사이에 선이 없다)
            for b in blocks:
                if b.kind == "RECT":
                    for ci, c in enumerate(b.cells):
                        side = _rect_edge(a.base, c, tol * 2)
                        if side:
                            return "port", (b, "out", side, ci, a.base, None)
                else:
                    c = b.circle
                    if abs(_d(a.base, (c.cx, c.cy)) - c.r) <= tol * 2:
                        return "port", (b, "out", "", 0, a.base, None)
            return "arrow-nowhere", tip
    # 2) 연결 기호의 꼭지에서 나가는 선
    for b in blocks:
        if b.kind == "CONNECTOR" and b.pointer and _d(e, b.pointer) <= tol * 2:
            return "port", (b, "out", "", 0, e, None)
        # 선이 꼭지 삼각형 안쪽에서 시작한다 (빗금 칠한 꼭지 · G012 'R' 실측) — 원과 꼭지 사이, 축 가까이
        if b.kind == "CONNECTOR" and b.pointer and getattr(b, "circle", None) is not None:
            c = b.circle
            ax = (b.pointer[0] - c.cx, b.pointer[1] - c.cy)
            L = math.hypot(*ax)
            if L > 0:
                t = ((e[0] - c.cx) * ax[0] + (e[1] - c.cy) * ax[1]) / L
                off = abs((e[0] - c.cx) * ax[1] - (e[1] - c.cy) * ax[0]) / L
                if c.r - tol <= t <= L + tol and off <= 0.5 * c.r:
                    return "port", (b, "out", "", 0, e, None)
    # 2b) 화살 없이 입력 막대에 닿은 끝 (L21 · 19VA) — 막대의 블록으로 들어간다
    for b in blocks:
        if getattr(b, "bar", False):
            for bs in b.bus:
                if _on_seg(e, geom.Seg(*bs), tol)[0]:
                    return "port", (b, "in", "BUS", 0, e, None)
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


def _drop_dashed_frames(dashed, span, tol, P):
    """파선으로 두른 큰 네모(매크로 · 묶음 틀)는 신호선이 아니다 (1A5J MACRO-PS 의 점선 틀 · L23).

    서로 끝이 닿는 파선 줄들을 묶어, 그 묶음의 모든 선분이 묶음 바깥 네모의 네 변 위에 있고 네 변을 다 쓰며
    그 네모가 LOGIC 영역 가로·세로의 3분의 1 이상이면 틀이다.  틀을 신호선으로 두면 틀에 걸친 단자 원들이 한 선으로
    이어져 서로 다른 신호가 한 값이 된다."""
    if len(dashed) < 2:
        return dashed
    par = list(range(len(dashed)))

    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    ends = [[q for sg in p.segs for q in sg.ends()] for p in dashed]
    for i in range(len(dashed)):
        for j in range(i + 1, len(dashed)):
            if any(_d(a, b) <= P for a in ends[i] for b in ends[j]):     # 틀 위 단자 원(< P)이 끊은 자리도 잇는다
                par[f(i)] = f(j)
    groups = defaultdict(list)
    for i in range(len(dashed)):
        groups[f(i)].append(i)
    drop = set()
    for idx in groups.values():
        segs = [sg for i in idx for sg in dashed[i].segs]
        xs = [v for sg in segs for v in (sg.x0, sg.x1)]
        ys = [v for sg in segs for v in (sg.y0, sg.y1)]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        if x1 - x0 < span[0] / 3 or y1 - y0 < span[1] / 3:
            continue
        sides = set()
        ok = True
        for sg in segs:
            if sg.horiz and abs(sg.y0 - y0) <= tol:
                sides.add("T")
            elif sg.horiz and abs(sg.y0 - y1) <= tol:
                sides.add("B")
            elif sg.vert and abs(sg.x0 - x0) <= tol:
                sides.add("L")
            elif sg.vert and abs(sg.x0 - x1) <= tol:
                sides.add("R")
            else:
                ok = False
                break
        if ok and len(sides) == 4:
            drop.update(idx)
    return [p for i, p in enumerate(dashed) if i not in drop]


def _dash_chains(glyphs, wires, blocks, arrows, dots, P, tol, bounds=None):
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
    # 끝에 작은 화살촉 획이 붙은 짧은 토막(파선의 마지막 토막 · 19VA) — 그 곧은 몸통은 파선에 이어 붙인다
    tipped = [(p, [sg for sg in p.segs if (sg.vert or sg.horiz) and sg.length >= 2 * tol]) for p in glyphs
              if 2 <= len(p.segs) <= 6 and any(not (x.vert or x.horiz) for x in p.segs)]
    tipped = [(p, ax) for p, ax in tipped if len(ax) == 1]

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
        even = max(lens) <= 2 * min(lens)
        if not even and len(ks) >= 4:
            # 쇄선(긴 토막 + 짧은 토막이 번갈아 · 19VA 신호선) — 가장 흔한 길이가 가장 긴 토막이면 고른 파선이다
            common = Counter(round(x, 1) for x in lens).most_common(1)[0][0]
            even = common >= 0.9 * max(lens)
        gaps_ok = not gaps_ or max(gaps_) <= 2 * min(gaps_) or \
            (len(ks) >= 4 and sorted(gaps_)[len(gaps_) // 2] * 2 >= max(lens) * 0.4)   # 쇄선 · 점(길이 0)을 건너뛴 틈 — 틈 대부분이 고르면
        if not even or not gaps_ok:
            continue
        Lmed = sorted(lens)[len(lens) // 2]
        near_arrow = lambda q: any(_d(q, a.base) <= 1.5 * Lmed for a in arrows)
        hit = sum(1 for q in free if touches(q) or near_arrow(q))
        # 고른 토막 넷 이상이 한 직선에 늘어선 것은 그 자체로 파선이다 — 끝이 다른 파선에만 닿아도 (19VA 는
        # 신호선 대부분이 파선이라 '실선에 닿는 끝' 을 요구하면 파선끼리 이어진 그물이 통째로 빠졌다 · L21)
        # 틈마다 다른 선이 가로지르면 파선이 아니라 건너뛰기(홉)로 끊어 그린 실선이다 — 그때는 예전 규칙만
        crossed = sum(1 for qa, qb, ka in bridges if ka in kset and any(
            _on_seg(((qa[0] + qb[0]) / 2, (qa[1] + qb[1]) / 2), w, tol)[0] and (w.vert != (abs(qa[0] - qb[0]) < 0.05))
            for w in wire_segs))
        long_run = len(ks) >= 4 and crossed * 2 < len(ks)
        if bounds and long_run:
            hit += sum(1 for q in free if min(abs(q[0] - bounds[0]), abs(q[0] - bounds[1])) <= 1.2 * max(gaps_ + [Lmed]))
        if not ((len(ks) >= 3 and hit >= 1) or (len(ks) == 2 and hit >= 2 and len(free) == 2) or long_run):
            continue
        # 파선이 화살촉 앞에서 틈 하나를 두고 끝나면 그 틈도 잇는다 (토막 길이 1.5배 안 · 같은 직선)
        Lmed = sorted(lens)[len(lens) // 2]
        for q in free:
            for a in arrows:
                if _d(q, a.base) <= 1.5 * Lmed and (abs(q[0] - a.base[0]) < tol or abs(q[1] - a.base[1]) < tol):
                    segs.append(geom.Seg(q[0], q[1], a.base[0], a.base[1]))
                    break
        # 파선이 블록 · 막대 · 실선 앞에서 틈 하나를 두고 끝나면 그 틈을 잇는다 (19VA — 마지막 토막이 기호에 안 닿는다 · L21)
        if long_run:
            reach = 1.2 * max(gaps_ + [Lmed])        # 틈 하나 또는 토막 하나 길이까지
            for q0 in free:
                q = q0
                for _ in range(2):                    # 끝 → (화살촉 토막) → 그 끝에서 한 번 더
                    if touches(q) or (bounds and min(abs(q[0] - bounds[0]), abs(q[0] - bounds[1])) <= tol):
                        break
                    sg = next((x for x in segs if _d(q, x.ends()[0]) < 0.01 or _d(q, x.ends()[1]) < 0.01), None)
                    if sg is None or not (sg.vert or sg.horiz):
                        break
                    o = sg.ends()[1] if _d(q, sg.ends()[0]) < 0.01 else sg.ends()[0]
                    L_ = _d(q, o) or 1.0
                    ux, uy = (q[0] - o[0]) / L_, (q[1] - o[1]) / L_
                    t, nxt = 0.25, None
                    while t <= reach:
                        pt = (q[0] + ux * t, q[1] + uy * t)
                        tip = next(((p, ax) for p, ax in tipped if id(p) not in taken and
                                    _on_seg(pt, ax[0], tol)[0] and (ax[0].vert == sg.vert)), None)
                        if tip is not None:
                            a0, a1 = sorted(tip[1][0].ends(), key=lambda e: _d(e, q))
                            segs.append(geom.Seg(q[0], q[1], a0[0], a0[1]))
                            segs.extend(tip[1])
                            taken.add(id(tip[0]))
                            nxt = a1
                            break
                        edge = bounds and sg.horiz and min(abs(pt[0] - bounds[0]), abs(pt[0] - bounds[1])) <= 0.5 * tol
                        if edge or touches(pt) or any(_on_seg(pt, geom.Seg(*bs), tol)[0] for b in blocks for bs in b.bus):
                            segs.append(geom.Seg(q[0], q[1], pt[0], pt[1]))
                            break
                        t += 0.25
                    if nxt is None:
                        break
                    q = nxt
        pts = [q for s in segs for q in s.ends()]
        out.append(geom.Poly(segs, geom._bbox(pts), dashed=True, pid=pieces[ks[0]].pid))
        taken.update(id(pieces[k]) for k in ks)
    return out, [p for p in glyphs if id(p) not in taken]
