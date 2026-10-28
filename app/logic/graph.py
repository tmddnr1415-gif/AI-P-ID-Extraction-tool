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


# ------------------------------------------------------------------ L28 — 점 근처 후보만 (같은 판정 · 덜 센다)

class _BoxIndex:
    """(사각형, 물건) 목록을 격자 칸에 넣어 둔다 — 점 하나에 닿을 수 있는 물건만 돌려준다.  사각형은 부르는 쪽이
    판정 허용치만큼 넓혀 넣는다 (그 밖의 물건은 판정이 언제나 거짓이다 — 그래서 결과가 같다)."""

    def __init__(self, items, cell=40.0):
        self.cell, self.items, self.g = cell, items, defaultdict(list)
        for k, (b, _) in enumerate(items):
            for gx in range(math.floor(b[0] / cell), math.floor(b[2] / cell) + 1):
                for gy in range(math.floor(b[1] / cell), math.floor(b[3] / cell) + 1):
                    self.g[(gx, gy)].append(k)

    def near(self, q):
        ks = self.g.get((math.floor(q[0] / self.cell), math.floor(q[1] / self.cell)))
        return [self.items[k][1] for k in ks] if ks else []


def _edge_box(b, tol):
    """_block_edge 가 참일 수 있는 자리 — 상자는 칸들을 감싼 사각형, 원은 원을 감싼 사각형 (허용치만큼 넓힘)."""
    if b.kind == "RECT":
        if not b.cells:
            return None
        return (min(c[0] for c in b.cells) - tol, min(c[1] for c in b.cells) - tol,
                max(c[2] for c in b.cells) + tol, max(c[3] for c in b.cells) + tol)
    c = b.circle
    return (c.cx - c.r - tol, c.cy - c.r - tol, c.cx + c.r + tol, c.cy + c.r + tol)


def _block_index(blocks, tol):
    return _BoxIndex([(bx, b) for b in blocks for bx in [_edge_box(b, tol)] if bx is not None])


def _seg_index(segs, tol):
    return _BoxIndex([((min(w.x0, w.x1) - tol, min(w.y0, w.y1) - tol, max(w.x0, w.x1) + tol, max(w.y0, w.y1) + tol), w)
                      for w in segs])


def _rect_index(rects_of, tol):
    return _BoxIndex([((r[0] - tol, r[1] - tol, r[2] + tol, r[3] + tol), a) for a, r in rects_of])


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
    markers: list = field(default_factory=list)      # L58 — 선 위의 인터페이스 표시 [(bbox, "diamond"|"square")] (재현용 · 판정에 안 쓴다)


# ------------------------------------------------------------------ 만들기

DASH_JOIN_MAX = 0.8      # 파선 끝끼리 잇는 틈 · 모서리 거리 상한 (행 간격 배수) — 1A5J 끊긴 파선 끝 짝 0~0.75P (L39)
BREAK_GAP_MAX = 2.5      # 끊어 그린 교차의 틈 상한 (행 간격 배수) — 1A1Y 실측 1.06~2.23 · HRSG 0.3~1.4 (L39)


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
    def clip_logic(p):
        """L48 — LOGIC 영역 바깥으로 **조금**(1P 안) 삐져나간 꺾은선은 버리지 않고 영역 안 토막만 남긴다.
        19VA Typical 0015 의 M_SEL · LOCK · RESET 행 선이 표 경계 1.5pt 안쪽(x=253.84)에서 시작해 path 전체가
        '영역 밖' 으로 버려졌고, MTS 매크로 56개가 그 입력을 잃었다.  남긴 토막의 끝은 경계 x 에 둔다 (행 붙이기 규칙 그대로)."""
        bb = p.bbox
        if inside(bb):
            return p
        if bb[1] < LY0 - tol or bb[3] > LY1 + tol or bb[0] < LX0 - P or bb[2] > LX1 + P:
            return None
        segs = []
        for s in p.segs:
            if s.horiz:
                lo, hi = min(s.x0, s.x1), max(s.x0, s.x1)
                lo, hi = max(lo, LX0), min(hi, LX1)
                if hi - lo <= 0.01:
                    continue
                segs.append(geom.Seg(lo if s.x0 <= s.x1 else hi, s.y0, hi if s.x0 <= s.x1 else lo, s.y1))
            elif min(s.x0, s.x1) >= LX0 - tol and max(s.x0, s.x1) <= LX1 + tol:
                segs.append(s)
        if not segs:
            return None
        nb = (min(min(s.x0, s.x1) for s in segs), min(min(s.y0, s.y1) for s in segs),
              max(max(s.x0, s.x1) for s in segs), max(max(s.y0, s.y1) for s in segs))
        q = geom.Poly(segs, nb, p.dashed, p.pid, getattr(p, "curved", False))
        return q
    polys = [q for q in (clip_logic(p) for p in prims.polys) if q is not None and not on_border(q)]
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
    wires, glyphs = _normalise_hops(wires, glyphs, P, tol)
    # L71 — 칠한 다각형 하나로 그린 연결점은 글자 크기까지 점이다 (속이 찬 원판은 블록 기호가 아니다)
    polydot = lambda c: getattr(c, "poly_dot", False) and 2 * c.r < GLYPH_MAX * P
    dots = [c for c in circles if 2 * c.r < DOT_MAX * P or polydot(c)]
    dots += _blob_dots([b for b in prims.blobs if inside(b)], P)
    bigc = [c for c in circles if 2 * c.r >= DOT_MAX * P and not polydot(c)]
    arrows = [a for a in prims.arrows if inside(a.bbox)]

    # ---- 상자: 겹친 사각형(이중 테두리)은 하나로, 변을 나눈 사각형(S/Ro · PB|START)은 한 블록의 칸으로
    rects = [r for r in prims.rects if inside((r.x0, r.y0, r.x1, r.y1))
             and r.w >= RECT_MIN * P and r.h >= RECT_MIN * P] + ovals
    rects, split_by = _split_by_divider(rects, wires + glyphs, P, tol)
    if split_by:
        wires = [p for p in wires if id(p) not in split_by]
        glyphs = [p for p in glyphs if id(p) not in split_by]
    assembled, used = _assemble_rects(wires + glyphs, rects, P, tol, dots)
    if assembled:
        rects += assembled
        wires = [p for p in wires if id(p) not in used]
        glyphs = [p for p in glyphs if id(p) not in used]
    rects = _dedupe_nested(rects, tol * 4)
    frames = _group_frames(rects, bigc, wires, tol)
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
        blocks[-1].round_side = "".join(sorted({c for r in g for c in getattr(r, "round_side", "")}))

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

    # L52 — 한 path 에 신호선과 블록 테두리가 함께 든 꺾은선 (HRSG G043 의 AND: 입력 버스 → 상자 네 변 → 되돌아옴).
    # 상자는 이미 블록으로 섰는데 테두리 토막이 선으로 남아 입력 선과 출력 선을 한 선으로 묶었다 (AND 의 R90 출력이
    # 입력 L6 와 같은 선 → AND(x, NOT x) 로 영영 0).  블록 칸의 변 위에 **통째로** 놓인 축 토막은 테두리다 — 선은
    # 변에서 끝나지 변을 따라 달리지 않는다.  나머지 토막은 그대로 선이다.
    def _on_cell_edge(sg):
        if not (sg.vert or sg.horiz):
            return False
        lo_x, hi_x = min(sg.x0, sg.x1), max(sg.x0, sg.x1)
        lo_y, hi_y = min(sg.y0, sg.y1), max(sg.y0, sg.y1)
        for b in blocks:
            if b.kind != "RECT":
                continue
            for c in b.cells:
                if sg.horiz and (abs(sg.y0 - c[1]) <= tol or abs(sg.y0 - c[3]) <= tol) and \
                        lo_x >= c[0] - tol and hi_x <= c[2] + tol:
                    return True
                if sg.vert and (abs(sg.x0 - c[0]) <= tol or abs(sg.x0 - c[2]) <= tol) and \
                        lo_y >= c[1] - tol and hi_y <= c[3] + tol:
                    return True
        return False
    for p in list(wires):
        if len(p.segs) < 2:
            continue
        keep = [sg for sg in p.segs if not _on_cell_edge(sg)]
        if len(keep) == len(p.segs):
            continue
        wires.remove(p)
        if keep:
            nb = (min(min(s.x0, s.x1) for s in keep), min(min(s.y0, s.y1) for s in keep),
                  max(max(s.x0, s.x1) for s in keep), max(max(s.y0, s.y1) for s in keep))
            wires.append(geom.Poly(keep, nb, p.dashed, p.pid, getattr(p, "curved", False)))

    # ---- 빗금으로 칠한 상자(■) · 마름모(◆) = 선 위의 인터페이스 표시 (범례 G003) — 블록이 아니다
    markers = [m for m in prims.markers if inside(m) and max(m[2] - m[0], m[3] - m[1]) >= DOT_MAX * P]

    def hatch_in(bb, any_segs=False):
        hs = [p for p in glyphs + wires if (any_segs or len(p.segs) == 1) and p.bbox[0] >= bb[0] - tol and p.bbox[2] <= bb[2] + tol
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
        hs = set(id(p) for p in hatch_in(m, any_segs=True))     # L53 — 표시의 둘레 획(꺾은선)도 선이 아니다
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

    # ---- L23b 삼각형 게이트 (ANSI 의 ▷ · ▷○) — 축에 선 밑변 하나 + 오른쪽 꼭지로 모이는 사선 둘, 닫힌 세 변.
    # 꼭지에 붙은 속 빈 작은 원은 부정 표시다.  상자처럼 다룬다 (밑변 = 입력 변 L · 꼭지(원) = 출력 변 R).
    for p in list(wires + glyphs):
        tb = _triangle(p, P)
        if tb is None:
            continue
        bb, apex = tb
        if any(_in_rect(((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2), bl.bbox, 0) for bl in blocks):
            continue                    # 상자 안의 그림(글자 · 범례 그림)
        neg = None
        for c in dots:
            if abs(_d((c.cx, c.cy), apex) - c.r) <= max(tol, c.r) and c.cx > apex[0]:
                neg = c
                break
        if neg is not None:
            dots.remove(neg)
            bb = (bb[0], bb[1], neg.cx + neg.r, bb[3])
        b = Block(nid(), "RECT", bb, cells=[bb])
        b.tri = True
        if neg is not None:
            b.neg = {"R"}
        blocks.append(b)
        if p in wires:
            wires.remove(p)
        else:
            glyphs.remove(p)

    # 블록 사이를 잇는 짧은 토막 — 글자 크기라도 두 끝이 다 블록 · 화살촉 · 선에 닿으면 선이다
    wire_segs0 = [sg for p in wires for sg in p.segs]

    bix, aix, wix = _block_index(blocks, tol), _rect_index([(a, a.bbox) for a in arrows], tol), _seg_index(wire_segs0, tol)

    def anchored(q):
        return (any(_block_edge(q, b, tol) for b in bix.near(q)) or
                any(_in_rect(q, a.bbox, tol) for a in aix.near(q)) or
                any(_on_seg(q, w, tol)[0] for w in wix.near(q)))
    for p in list(glyphs):
        if len(p.segs) != 1 or not (p.segs[0].vert or p.segs[0].horiz):
            continue
        a, b = p.segs[0].ends()
        if any(p.bbox[0] >= bl.bbox[0] - tol and p.bbox[2] <= bl.bbox[2] + tol and
               p.bbox[1] >= bl.bbox[1] - tol and p.bbox[3] <= bl.bbox[3] + tol for bl in blocks):
            continue                    # 블록 안의 글자 획
        if anchored(a) and anchored(b):
            # L53 — 두 끝을 **같은 선분 하나**가 받치면 그 선 옆에 나란히 놓인 글자 획이다 (HRSG G008 `ST/BY-A` 의
            # A 가로획이 선 끝 0.6pt 옆에 놓여 선이 되고, 그 선의 끝을 '닿은 끝' 으로 만들어 단추 출력 단자가 안 섰다).
            # 블록 사이를 잇는 토막은 두 끝이 서로 다른 것에 닿는다.
            wa = [id(w) for w in wix.near(a) if _on_seg(a, w, tol)[0]]
            wb = [id(w) for w in wix.near(b) if _on_seg(b, w, tol)[0]]
            others = (any(_block_edge(a, bl, tol) for bl in bix.near(a)) or any(_in_rect(a, ar.bbox, tol) for ar in aix.near(a)),
                      any(_block_edge(b, bl, tol) for bl in bix.near(b)) or any(_in_rect(b, ar.bbox, tol) for ar in aix.near(b)))
            if set(wa) & set(wb) and not (others[0] and others[1]):
                continue
            glyphs.remove(p)
            wires.append(p)
    _promote_gap_stubs(glyphs, wires, blocks, P, tol)

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
        # L53 — LOGIC 경계(표의 행)에 닿는 선은 막대가 아니라 행 신호선이다.  HRSG G067: 출력 행 선 위에 연결 기호 원이
        # 앉고 그 원으로 가는 토막에 화살이 있어, 493pt 행 선이 그 원의 '입력 막대' 로 먹혀 두 행이 통째로 사라졌다.
        if min(s.x0, s.x1) <= LX0 + tol * 3 or max(s.x0, s.x1) >= LX1 - tol * 3:
            continue
        b = _block_touching_bus(s, blocks, tol)
        if b is not None:
            bus_of[id(p)] = b
            b.bus.append((s.x0, s.y0, s.x1, s.y1))
    wires = [p for p in wires if id(p) not in bus_of]

    # ---- 파선: 글자 크기 조각 중 한 줄로 늘어선 것 (끝이 선이나 단자에 닿는 줄만)
    # L71 — 홉(고친 반원)과 그 홉에 끝이 맞닿은 짧은 토막은 파선이 아니다 — 끊김 없이 이어진 실선 조각이다
    # (홉 → 3pt → 홉 → 3pt → 틈 이 같은 길이로 늘어서 파선으로 읽혀 마지막 끝이 매달렸다 · 퍼징 10192)
    hop_ends = [q for p in wires if getattr(p, "hop", False) for q in (p.segs[0].ends()[0], p.segs[-1].ends()[1])]
    hx = _seg_index([geom.Seg(q[0], q[1], q[0], q[1]) for q in hop_ends], tol)

    def on_hop(p):
        return getattr(p, "hop", False) or any(min(_d(e, h.ends()[0]) for h in hx.near(e)) <= tol
                                               for e in (p.segs[0].ends()[0], p.segs[-1].ends()[1]) if hx.near(e))
    short = [p for p in wires if p.size < P and not on_hop(p)]
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
    # L53 — 화살촉 **안**에 통째로 든 짧은 축 토막은 화살촉의 꼬리다 (파선의 마지막 토막이 칠한 화살촉 밑에 깔린 1A1Y HR_P007).
    # 선으로 두면 그 토막만의 그물이 행에 한 번 더 붙어 '몰이 없는 선' 으로 센다.
    tip_ix = _rect_index([(a, a.bbox) for a in tip_arrows], tol)

    def arrow_tail(s):
        if not (s.vert or s.horiz):
            return False                     # 길이는 화살촉 사각형이 가른다 (두 끝이 다 그 안)
        e0, e1 = s.ends()
        return any(_in_rect(e0, a.bbox, tol) and _in_rect(e1, a.bbox, tol) for a in tip_ix.near(e0))
    for p in wires:
        for s in p.segs:
            if arrow_tail(s):
                continue
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
        o = max(si.ends(), key=lambda q: _d(e, q))       # 먼 쪽 끝 (토막이 tol 보다 짧아도)
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
                # L71 — 작은 홉 · 좁은 틈: 끝이 몸통에 닿는 거리(tol) 안에서 끊겼고 건너편에 같은 직선이 몸통에서
                # 같은 만큼 떨어져 이어지면 지나가는 교차다 (홉 반지름 ≤ tol 이면 두 끝이 다 '닿은 끝' 이 되어 T 로 이었다)
                if not ((si.vert and sj.horiz) or (si.horiz and sj.vert)):
                    continue
                if si.vert:
                    ok = abs(q[0] - e[0]) <= tol and (q[1] - sj.y0) * (e[1] - sj.y0) < 0
                    side = abs(q[1] - sj.y0)
                else:
                    ok = abs(q[1] - e[1]) <= tol and (q[0] - sj.x0) * (e[0] - sj.x0) < 0
                    side = abs(q[0] - sj.x0)
                if ok and side <= tol and (r[0] - e[0]) * out[0] + (r[1] - e[1]) * out[1] > 0:
                    return True
        return False

    # L53 — 블록 변(원 둘레)에 닿는 끝은 단자다.  그 자리에 다른 선이 **지나가도**(연결 기호 원이 행 선 바로 위에 앉은
    # HRSG G067 — 원 바닥과 행 선이 0.4pt) 그 선에 잇지 않는다: 이으면 두 행 선이 한 그물이 되고 단자도 안 선다.
    bix2 = _block_index(blocks, tol)

    def at_block(e):
        return any(_block_edge(e, bl, tol) for bl in bix2.near(e))
    for i, (s, p) in enumerate(segs):
        for e in s.ends():
            if not joinable(e, p):
                continue
            if at_block(e):
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

    def axial(s):
        # 거의 곧은 선 — CAD 가 0.1pt 남짓 기울게 낸 세로선도 (1A1Y HR_P011 · 60pt 에 0.12pt) 같은 직선으로 본다
        dx, dy = abs(s.x1 - s.x0), abs(s.y1 - s.y0)
        if s.vert or dx <= max(0.15, 0.004 * dy) and dy > dx:
            return "v"
        if s.horiz or dy <= max(0.15, 0.004 * dx) and dx > dy:
            return "h"
        return None
    for i, (s, p) in enumerate(segs):
        ax_ = axial(s)
        if ax_ is None:
            continue
        for e in s.ends():
            if not joinable(e, p):
                continue
            if any(j != i and _on_seg(e, segs[j][0], tol)[0] and not passes_through(i, e, j) for j in near(e)):
                continue
            if any(_d(e, (c.cx, c.cy)) <= c.r + tol for c in dots):
                continue
            if any(_block_edge(e, b, tol * 2) for b in blocks) or any(_in_rect(e, a.bbox, tol) for a in arrows):
                continue
            # 게이트 입력 막대 위의 끝 — 막대에 붙을 끝이다 (L39 · 19VA BL11_P303: 파선 잇기가 이 끝을 가져가 입력을 잃었다)
            if any(_on_seg(e, geom.Seg(*bs), tol * 2)[0] for b in blocks for bs in getattr(b, "bus", ()) or ()):
                continue
            # 바깥쪽 방향 (선분 안쪽 → 끝)
            o = s.ends()[1] if e == s.ends()[0] else s.ends()[0]
            loose.append((e, i, ax_, (e[0] - o[0], e[1] - o[1])))
    _clen = {}

    def comp_len(j):
        # 그 선이 속한 (이미 이은) 선 전체 길이 — 두 선 사이 짧은 꺾임 토막도 긴 선의 일부다 (퍼징 11680)
        if not _clen:
            for k, (t, _) in enumerate(segs):
                r = find(k)
                _clen[r] = _clen.get(r, 0.0) + t.length
        return _clen.get(find(j), segs[j][0].length)

    _slen = {}

    def straight_len(j):
        # L71 — 지나가는 선의 길이는 한 직선으로 맞닿아 이어진 토막 전부 (홉 · 꺾임점에서 끊겨 그 조각이 틈보다 짧아도)
        if j in _slen:
            return _slen[j]
        t0 = segs[j][0]
        vert = t0.vert
        key = (lambda q: q[0]) if vert else (lambda q: q[1])
        c = key(t0.ends()[0])
        seen, stack = {j}, [j]
        lo = hi = None
        while stack:
            k = stack.pop()
            for q in segs[k][0].ends():
                a_ = q[1] if vert else q[0]
                lo = a_ if lo is None else min(lo, a_)
                hi = a_ if hi is None else max(hi, a_)
                for m in near(q):
                    if m in seen:
                        continue
                    t = segs[m][0]
                    if (t.vert if vert else t.horiz) and abs(key(t.ends()[0]) - c) <= tol and \
                            min(_d(q, e) for e in t.ends()) <= tol:
                        seen.add(m)
                        stack.append(m)
        for k in seen:
            _slen[k] = hi - lo
        return hi - lo

    def facing(a, b):
        ea, ia, axa, va = loose[a]
        eb, ib, axb, vb = loose[b]
        if axa != axb or ia == ib:
            return None
        if axa == "v" and abs(ea[0] - eb[0]) > 0.3:
            return None
        if axa == "h" and abs(ea[1] - eb[1]) > 0.3:
            return None
        g = _d(ea, eb)
        if g == 0 or g > BREAK_GAP_MAX * P:
            return None
        # 서로를 향하는가
        if (eb[0] - ea[0]) * va[0] + (eb[1] - ea[1]) * va[1] <= 0:
            return None
        if (ea[0] - eb[0]) * vb[0] + (ea[1] - eb[1]) * vb[1] <= 0:
            return None
        mid = ((ea[0] + eb[0]) / 2, (ea[1] + eb[1]) / 2)
        # 틈이 행 간격보다 넓으면 (1A1Y — CAD 가 교차 자리를 1~2.2 행 간격 비운다 · L39) 지나가는 선이 틈 한가운데
        # (틈의 1/4 안)를 지나고 그 선이 틈보다 길거나 파선이어야 한다 — 글자 획 · 짧은 표시가 사이에 있는 것과 가른다
        wide = g > P
        for j in near(mid):
            t, tp = segs[j]
            if not (axa == "v" and t.horiz or axa == "h" and t.vert):
                continue
            if wide and ((straight_len(j) < g and comp_len(j) < g and not tp.dashed) or not _on_seg(mid, t, g / 4)[0]):
                continue
            if _on_seg(mid, t, g / 2)[0]:
                return g
        return None
    # 좁은 틈 (행 간격 안) — 가까운 짝부터 · 끝마다 하나 (L71: 교차 둘을 연달아 끊어 그린 자리에서 바깥 두 끝이
    # 가운데 토막을 건너뛰어 서로 이으면 그 토막의 두 끝이 매달린다)
    near_c = []
    for a in range(len(loose)):
        for b in range(a + 1, len(loose)):
            g = facing(a, b)
            if g is not None and g <= P:
                near_c.append((g, a, b))
    taken = set()
    for g, a, b in sorted(near_c):
        ea, ia, _, _ = loose[a]
        eb, ib, _, _ = loose[b]
        if ea in taken or eb in taken or find(ia) == find(ib):
            continue
        taken.update((ea, eb))
        union(ia, ib)
        bridged.append((ea, eb))
    # 넓은 틈 — 끝마다 가장 가까운 짝 하나만 (먼 짝을 이으면 홉 여럿을 건너뛴 다리가 생긴다 · 1A5J 0008)
    used = {q for br in bridged for q in br}
    cand = []
    for a in range(len(loose)):
        if loose[a][0] in used:
            continue
        for b in range(a + 1, len(loose)):
            if loose[b][0] in used:
                continue
            g = facing(a, b)
            if g is not None and g > P:
                cand.append((g, a, b))
    for g, a, b in sorted(cand):
        ea, ia, _, _ = loose[a]
        eb, ib, _, _ = loose[b]
        if ea in used or eb in used or find(ia) == find(ib):
            continue
        used.update((ea, eb))
        union(ia, ib)
        bridged.append((ea, eb))

    # 파선끼리 — 같은 직선 위의 틈 · 꺾이는 모서리에서 끊긴 채 그린 파선 신호선 (1A5J 0001/0002 · L39).
    # 두 끝이 모두 파선의 끝이고, 같은 직선이면 마주 보며 틈이, 직각이면 두 직선이 만나는 모서리까지가 각각
    # DASH_JOIN_MAX 행 간격 안일 때 잇는다.  끝마다 가장 가까운 짝 하나만.  이은 자리에는 선분을 그려 넣는다 (화면 · 흐름)
    dl = [k for k in range(len(loose)) if segs[loose[k][1]][1].dashed and loose[k][0] not in used]
    R = DASH_JOIN_MAX * P
    cand = []
    for x in range(len(dl)):
        ea, ia, axa, va = loose[dl[x]]
        for y in range(x + 1, len(dl)):
            eb, ib, axb, vb = loose[dl[y]]
            if ia == ib or _d(ea, eb) > 2 * R:
                continue
            if axa == axb:
                if (axa == "v" and abs(ea[0] - eb[0]) > 0.3) or (axa == "h" and abs(ea[1] - eb[1]) > 0.3):
                    continue
                g = _d(ea, eb)
                if g == 0 or g > R:
                    continue
                if (eb[0] - ea[0]) * va[0] + (eb[1] - ea[1]) * va[1] <= 0 or (ea[0] - eb[0]) * vb[0] + (ea[1] - eb[1]) * vb[1] <= 0:
                    continue
                cand.append((g, ea, eb, ia, ib, None))
            else:
                C = (eb[0], ea[1]) if axa == "h" else (ea[0], eb[1])
                da, db = _d(ea, C), _d(eb, C)
                if da > R or db > R:
                    continue
                # 각 끝이 모서리를 바라본다 (모서리가 끝 바깥쪽에 있다 · 끝 위면 됨)
                if da > 0.01 and (C[0] - ea[0]) * va[0] + (C[1] - ea[1]) * va[1] <= 0:
                    continue
                if db > 0.01 and (C[0] - eb[0]) * vb[0] + (C[1] - eb[1]) * vb[1] <= 0:
                    continue
                cand.append((da + db, ea, eb, ia, ib, C))
    dash_links = []
    for g, ea, eb, ia, ib, C in sorted(cand, key=lambda t: t[0]):
        if ea in used or eb in used or find(ia) == find(ib):
            continue
        used.update((ea, eb))
        union(ia, ib)
        dash_links.append((ea, eb, ia, C))

    # 파선 끝이 블록 · 화살촉 · 입력 막대 앞에서 틈 하나를 두고 끝나면 그 틈까지 늘인다 (1A5J — 마지막 토막이 기호에
    # 안 닿는다 · L21 은 긴 파선에서만 했다 · L39).  끝이 바라보는 방향으로만 · DASH_JOIN_MAX 행 간격까지.
    forced = set()                                  # 늘여서 변 · 막대에 닿게 한 끝 — 그 자리의 다른 토막과 맞물려도 단자로 붙는다
    for k in dl:
        e, i, ax_, v = loose[k]
        if e in used:
            continue
        L_ = math.hypot(*v) or 1.0
        ux, uy = v[0] / L_, v[1] / L_
        t, hit = 0.25, None
        while t <= R:
            q = (e[0] + ux * t, e[1] + uy * t)
            ar = next((a for a in arrows if _in_rect(q, a.bbox, tol)), None)
            if ar is not None:
                if _d(ar.base, e) <= R + tol:                             # 화살촉이면 그 밑동까지 (화살 선이 끝나는 자리)
                    hit = (ar.base[0], e[1]) if abs(ux) > abs(uy) else (e[0], ar.base[1])   # L53 — 축 위로 (기운 선분은 획으로 버려진다)
                else:
                    hit = q
                break
            if any(_block_edge(q, b, tol) for b in blocks) or \
                    any(_on_seg(q, geom.Seg(*bs), tol)[0] for b in blocks for bs in getattr(b, "bus", ()) or ()):
                # 변 · 막대 바로 위까지 (허용치만큼 앞에서 멈추면 그 자리에 이미 붙은 다른 토막과 맞물려 단자를 잃는다)
                while t <= R + tol and not (any(_block_edge(q, b, 0.05) for b in blocks) or
                                            any(_on_seg(q, geom.Seg(*bs), 0.05)[0] for b in blocks for bs in getattr(b, "bus", ()) or ())):
                    t += 0.05
                    q = (e[0] + ux * t, e[1] + uy * t)
                hit = (round(q[0], 2), round(q[1], 2))
                forced.add(hit)
                break
            t += 0.25
        if hit is None:
            continue
        sg, sp = segs[i]
        a0, a1 = sg.ends()
        segs[i] = (geom.Seg(hit[0], hit[1], a1[0], a1[1]) if _d(a0, e) < 1e-6 else geom.Seg(a0[0], a0[1], hit[0], hit[1]), sp)
        f = free_of.get(id(sp))
        if f is not None:                           # 늘인 끝도 파선의 바깥 끝이다
            f.add((round(hit[0], 2), round(hit[1], 2)))
        used.add(e)

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

    for ea, eb, ia, C in dash_links:
        pts = [ea, C, eb] if C else [ea, eb]
        for q0, q1 in zip(pts, pts[1:]):
            if _d(q0, q1) > 0.01:
                sh.nets[seg_net[ia]]["segs"].append((round(q0[0], 2), round(q0[1], 2), round(q1[0], 2), round(q1[1], 2)))
    linked_ends = [q for ea, eb, _, _ in dash_links for q in (ea, eb)]

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
    # L23b — 상자 변 **바깥**에 붙은 작은 원 = 부정 표시(IEC · ANSI 의 bubble).  단자 원(L13)은 변 위에 중심이 있다.
    for c in dots:
        pd = pin_dot.get(id(c))
        if pd is None:
            continue
        b_, ci_, side_ = pd
        cell_ = b_.cells[ci_]
        out_by = (c.cx - cell_[2]) if side_ == "R" else (cell_[0] - c.cx)
        if out_by >= 0.5 * c.r:
            neg = getattr(b_, "neg", None) or set()
            neg.add(side_)
            b_.neg = neg
    pin_ports = []
    for i, (s, p) in enumerate(segs):
        for e in s.ends():
            if not joinable(e, p):
                continue
            touched = False
            for j in near(e):
                if (round(e[0], 2), round(e[1], 2)) in forced:
                    break
                if j != i and (segs[j][1] is p or joinable(e, p)) and _on_seg(e, segs[j][0], tol)[0] and not at_block(e):
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
            if not touched and (any(_d(e, q) < 1e-6 for br in bridged for q in br) or
                                any(_d(e, q) < 1e-6 for q in linked_ends)):
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
        span = max(max(xs) - min(xs), max(ys) - min(ys))
        # 행 옆의 펄스 표시(⎍ · 1A5J 0001/0002 — 입력 신호 종류 표시)처럼 실선으로 그린 작은 외톨이 기호도 신호가 아니다:
        # 아무 데도 안 닿고 · 2 행 간격 안 · 파선 아님 · 끝이 둘뿐 (꺾인 한 줄) (L39)
        de = [d for d in sh.dangling if d[2] == nid]
        sg_ = sh.nets[nid]["segs"]
        glyph = (span < 2 * P and not sh.nets[nid].get("dashed") and len(de) == 2 and 3 <= len(sg_) <= 6 and
                 # 양 끝이 한 바닥선 위 (⎍ · ⎎) — 꺾인 신호선 조각(ㄱ · ㄴ)은 끝이 대각으로 놓인다
                 (abs(de[0][1] - de[1][1]) < 0.5 or abs(de[0][0] - de[1][0]) < 0.5) and
                 math.hypot(de[0][0] - de[1][0], de[0][1] - de[1][1]) >= 0.4 * span)
        if span < P or glyph:
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
    # L48 — 단자 방향을 '확실한 것부터' 정한다.  ① 들어오는 단자(입력 막대 · 화살)를 이미 가진 블록의 **하나 남은** 미정 단자는
    # 출력이다 (OR 의 오른쪽 변).  순서대로 풀면 그 선 위의 다른 블록(세로 선 위의 NOT)이 먼저 '나가는 쪽' 을 차지해 OR 출력이
    # 들어오는 쪽이 되고 NOT 은 입력 없는 게이트가 됐다 (19VA Typical 0009 — 펌프 그룹 STOP 명령이 전부 그 NOT 에서 막혔다).
    # ② 위·아래 변 단자만 둘인 작은 상자(세로 선 위의 NOT · 타이머): 한쪽 선만 확실한 받는 쪽(다른 블록의 들어오는 단자 ·
    # 오른쪽 행)에 닿으면 닿는 쪽이 출력, 다른 쪽이 입력.
    by_block = defaultdict(list)
    for pt in sh.ports:
        by_block[pt.block].append(pt)
    for pts in by_block.values():
        q = [pt for pt in pts if pt.dir == "?"]
        if len(q) == 1 and any(pt.dir == "in" for pt in pts) and not any(pt.dir == "out" for pt in pts):
            q[0].dir = "out"
            drivers[q[0].net] += 1
    consumers = defaultdict(int)
    for pt in sh.ports:
        if pt.dir == "in":
            consumers[pt.net] += 1
    for r in sh.rows:
        if r["side"] == "R":
            consumers[r["net"]] += 1
    for pts in by_block.values():
        if len(pts) != 2 or any(pt.dir != "?" for pt in pts) or pts[0].net == pts[1].net:
            continue
        a, b = pts
        ca, cb = consumers[a.net] > 0, consumers[b.net] > 0
        if ca != cb and not drivers[a.net] and not drivers[b.net]:
            out_pt, in_pt = (a, b) if ca else (b, a)
            out_pt.dir, in_pt.dir = "out", "in"
            drivers[out_pt.net] += 1
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
    sh.markers = [(tuple(m), (prims.marker_kind.get(tuple(round(v, 2) for v in m)) or "square")) for m in markers]
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
    if getattr(b, "tri", False):
        return "TRIANGLE"
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


def _assemble_rects(polys, rects, P, tol, dots=()):
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
    axs = _seg_index([sg for p in polys for sg in p.segs if (sg.horiz or sg.vert) and sg.length > 0], tol)
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
        # L69 — 변 위에 연결점이 있으면 상자가 아니라 배선이다.  게이트 입력 막대에 들어가는 두 신호선 + 그 둘을
        # 잇는 세로선이 막대와 함께 닫힌 네모를 만든다 (19VA 0017 MIT 의 OR — 안을 지나는 선이 글자로 먹혀 끊겼다).
        # 상자의 변은 연결점을 갖지 않는다 (범례 G003 · 연결점 = 선이 갈라지는 자리).
        if any(_dot_on_edge(c, bb, tol) for c in dots):
            continue
        # L71 — 모서리에서 두 선이 다 상자 바깥으로 이어지면 모서리가 아니라 교차다.  홉 · 끊어 그린 틈으로 끊긴 네 선의
        # 가운데 토막이 맞물려 상자처럼 보인다 (합성 퍼징: 가짜 AND · UNKNOWN 블록이 서고 안을 지나는 선이 끊겼다).
        corners = [_corner_out(axs, cx, cy, hx, vy, P, max(tol, g)) for cx, cy, hx, vy in
                   ((bb[0], bb[1], -1, -1), (bb[2], bb[1], 1, -1), (bb[0], bb[3], -1, 1), (bb[2], bb[3], 1, 1))]
        if sum(h and v for h, v in corners) >= 2:
            continue
        # 모서리 셋 이상에서 선이 바깥으로 이어지면 (T · 꺾여 나가는 선 · 교차) 네 선이 우연히 둘러싼 배선이다.
        # 상자 변은 모서리에서 끝난다 — 입력 막대를 변으로 겸한 게이트도 막대 쪽 두 모서리뿐이다.
        if sum(h or v for h, v in corners) >= 3:
            continue
        area = (bb[2] - bb[0]) * (bb[3] - bb[1])
        if any(_overlap_frac(bb, q) > 0.5 and (q[2] - q[0]) * (q[3] - q[1]) < 3 * area for q in have):
            continue
        rr = geom.Rect(*bb)
        rr.rounded = rounded
        rr.round_side = ("L" if sides[0][4] != sides[0][2] else "") + ("R" if sides[1][4] != sides[1][2] else "")
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


def _crossing_corner(axs, cx, cy, hx, vy, P, tol):
    """모서리 (cx, cy) 에서 가로선이 hx 쪽(바깥)으로, 세로선이 vy 쪽(바깥)으로 같은 직선을 따라 이어지나 (틈 · 홉 건너 포함)."""
    h, v = _corner_out(axs, cx, cy, hx, vy, P, tol)
    return h and v


def _corner_out(axs, cx, cy, hx, vy, P, tol):
    """(가로선이 바깥으로 이어지나, 세로선이 바깥으로 이어지나) — 틈 · 홉 건너 포함."""
    lim = BREAK_GAP_MAX * P
    pt = (cx, cy)
    h = v = False
    step = max(tol, 0.5)
    n = int(lim / step) + 1
    cand = {id(s): s for k in range(n + 1) for q in ((cx + hx * k * step, cy), (cx, cy + vy * k * step)) for s in axs.near(q)}
    for s in cand.values():
        if s.horiz and abs(s.y0 - cy) <= tol:
            far = max(s.x0, s.x1) if hx > 0 else min(s.x0, s.x1)
            near_ = min(s.x0, s.x1) if hx > 0 else max(s.x0, s.x1)
            if (far - cx) * hx > tol and (near_ - cx) * hx <= lim:
                h = True
        elif s.vert and abs(s.x0 - cx) <= tol:
            far = max(s.y0, s.y1) if vy > 0 else min(s.y0, s.y1)
            near_ = min(s.y0, s.y1) if vy > 0 else max(s.y0, s.y1)
            if (far - cy) * vy > tol and (near_ - cy) * vy <= lim:
                v = True
    return h, v


def _dot_on_edge(c, bb, tol):
    """연결점 c 가 사각형 bb 의 변(모서리 포함) 위에 있나."""
    x, y, t = c.cx, c.cy, tol + c.r
    on_v = (abs(x - bb[0]) <= t or abs(x - bb[2]) <= t) and bb[1] - t <= y <= bb[3] + t
    on_h = (abs(y - bb[1]) <= t or abs(y - bb[3]) <= t) and bb[0] - t <= x <= bb[2] + t
    return on_v or on_h


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


def _hop_shape(a, b, pts, P, tol):
    """두 끝 a · b 와 그 사이 점들이 홉(한쪽으로 부푼 반원) 꼴이면 축 'v' | 'h', 아니면 None."""
    dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
    L = max(dx, dy)
    if not (0.5 * tol <= L <= P):
        return None
    ax = "v" if dx <= tol and dy > dx else "h" if dy <= tol and dx > dy else None
    if ax is None:
        return None
    base = (a[0] + b[0]) / 2 if ax == "v" else (a[1] + b[1]) / 2
    offs = [(q[0] - base) if ax == "v" else (q[1] - base) for q in pts]
    far = max(offs, key=abs)
    if abs(far) < 0.25 * L or abs(far) > 1.5 * L + tol:
        return None
    if any(o * far < 0 and abs(o) > tol for o in offs):
        return None
    return ax


def _hop_cross(a, b, ax, wx, tol):
    """현 a-b 안쪽을 직각으로 지나는 선의 자리 (가운데에 가장 가까운 것) · 없으면 None."""
    base = (a[0] + b[0]) / 2 if ax == "v" else (a[1] + b[1]) / 2
    lo, hi = (min(a[1], b[1]), max(a[1], b[1])) if ax == "v" else (min(a[0], b[0]), max(a[0], b[0]))
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    cross = None
    for w in wx.near(mid):
        if ax == "v" and w.horiz and lo < w.y0 < hi and min(w.x0, w.x1) - tol <= base <= max(w.x0, w.x1) + tol:
            c = w.y0
        elif ax == "h" and w.vert and lo < w.x0 < hi and min(w.y0, w.y1) - tol <= base <= max(w.y0, w.y1) + tol:
            c = w.x0
        else:
            continue
        if cross is None or abs(c - (lo + hi) / 2) < abs(cross - (lo + hi) / 2):
            cross = c
    return cross


def _hop_segs(a, b, ax, cross):
    base = (a[0] + b[0]) / 2 if ax == "v" else (a[1] + b[1]) / 2
    c = (base, cross) if ax == "v" else (cross, base)
    a2 = (base, a[1]) if ax == "v" else (a[0], base)
    b2 = (base, b[1]) if ax == "v" else (b[0], base)
    return [geom.Seg(*a2, *c), geom.Seg(*c, *b2)]


def _hops_in_paths(wires, glyphs, P, tol):
    """한 path 안에 선 조각과 홉을 같이 그린 꼴 — 이어진 비스듬한 토막 무리(꺾은선 반원 · 사분원 현)가 홉이면 그 무리를
    교차점에서 맞닿는 곧은 두 토막으로 바꾼다 (그대로 두면 반원의 꼭짓점이 지나는 선 위에 놓여 그 선과 이어진다)."""
    wx = _seg_index([s for p in wires for s in p.segs if (s.vert or s.horiz) and s.length > 0], tol)

    def fix(p):
        segs = p.segs
        if len(segs) < 3:
            return None
        out, i, changed = [], 0, False
        while i < len(segs):
            s = segs[i]
            if s.vert or s.horiz:
                out.append(s)
                i += 1
                continue
            j = i
            while j < len(segs) and not (segs[j].vert or segs[j].horiz) and \
                    (j == i or _d(segs[j - 1].ends()[1], segs[j].ends()[0]) <= 1e-3):
                j += 1
            run = segs[i:j]
            a, b = run[0].ends()[0], run[-1].ends()[1]
            pts = [q for sg in run for q in sg.ends()]
            ax = _hop_shape(a, b, pts, P, tol)
            # 같은 축의 곧은 선 끝이 홉 끝에 닿는다 (같은 path 안 · 밖 어디든 — CAD 는 조각을 먼저 다 그리고 호를 나중에 그리기도 한다)
            near_axis = bool(ax) and any((sg.vert if ax == "v" else sg.horiz) and min(_d(q, e) for e in sg.ends()) <= tol
                                         for q in (a, b) for sg in segs + wx.near(q))
            cross = _hop_cross(a, b, ax, wx, tol) if ax and near_axis else None
            if cross is not None:
                out.extend(_hop_segs(a, b, ax, cross))
                changed = True
            else:
                out.extend(run)
            i = j
        if not changed:
            return None
        pts = [q for sg in out for q in sg.ends()]
        q = geom.Poly(out, (min(x for x, _ in pts), min(y for _, y in pts), max(x for x, _ in pts), max(y for _, y in pts)),
                      p.dashed, p.pid, False)
        return q
    nw = []
    for p in wires:
        q = fix(p)
        nw.append(q if q is not None else p)
    ng = []
    for p in glyphs:
        q = fix(p)
        # 고친 홉은 선이다 (지나는 직각 선 · 같은 축 선 끝을 다 확인했다) — 글자 크기라도 글자 무리에 두면
        # 홉 → 짧은 토막 → 모서리처럼 글자 둘이 이어질 때 어느 쪽도 양 끝이 선에 닿지 않아 끊긴다.
        (nw if q is not None else ng).append(q if q is not None else p)
    return nw, ng


def _normalise_hops(wires, glyphs, P, tol):
    """L70·L71 — 홉(건너뛰기 반원)을 **교차점에서 맞닿는 곧은 두 토막**으로 바꾼다.

    도면은 선이 다른 선을 지날 때 그 자리를 반원으로 건너뛰어 그린다.  그 반원을 곡선(베지어 하나 · 사분원 둘) 으로도,
    짧은 직선 여럿으로도 그리고, 홉 바로 뒤 몇 pt 에서 연결점 · 블록 변에 닿기도 한다 (19VA 0015 MTS).  반원은 글자 크기라
    글자 획으로 버려지거나(뒤 토막이 매달림) 꺾은선의 꼭짓점이 지나는 선 위에 놓여 그 선과 이어졌다.
    알아본 홉은 현(두 끝을 잇는 곧은 선)으로 펴고 지나는 선이 가로지르는 점에서 둘로 나눈다 — 'CAD 가 교차점에서 선을
    끊어 그린 것' 과 같은 꼴이 되어 그 뒤의 규칙(지나가는 교차 · 짧은 토막 · 단자)이 그대로 읽는다.

    홉 = 열린 무리 하나 · 두 끝이 한 축 위 · 현 길이 ≤ GLYPH_MAX 행 · 한쪽으로 현의 1/4 이상 부풂 · 지나는 직각 선이 현
    안쪽을 지난다 · 한 끝 이상이 같은 축의 곧은 선 끝에 닿는다 (글자 'C' · '(' 를 거른다).  새 상수 0.
    """
    def free_ends(segs):
        out = []
        for i, s in enumerate(segs):
            for q in s.ends():
                if not any(j != i and min(_d(q, e) for e in t.ends()) <= 1e-3 for j, t in enumerate(segs)):
                    out.append(q)
        return out

    lim = P
    wires, glyphs = _hops_in_paths(wires, glyphs, P, tol)
    cands = [p for p in wires + glyphs if p.size <= 1.6 * lim and not p.dashed and
             (getattr(p, "curved", False) or any(not (s.vert or s.horiz) for s in p.segs))]
    if not cands:
        return wires, glyphs
    # 사분원 둘처럼 따로 그린 조각은 끝끼리 묶는다
    par = list(range(len(cands)))

    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    keyed = defaultdict(list)
    for i, p in enumerate(cands):
        for q in (p.segs[0].ends()[0], p.segs[-1].ends()[1]):
            keyed[(round(q[0] * 10), round(q[1] * 10))].append(i)
    for (kx, ky), ids in keyed.items():
        for dx in (0, 1):
            for dy in (-1, 0, 1):
                for j in keyed.get((kx + dx, ky + dy), ()):
                    for i in ids:
                        if i != j:
                            par[f(j)] = f(i)
    groups = defaultdict(list)
    for i in range(len(cands)):
        groups[f(i)].append(cands[i])
    cand_ids = {id(p) for p in cands}
    sx = _seg_index([s for p in wires + glyphs if id(p) not in cand_ids for s in p.segs
                     if (s.vert or s.horiz) and s.length > 0], tol)
    wx = _seg_index([s for p in wires for s in p.segs if (s.vert or s.horiz)], tol)
    drop, add = set(), []
    for grp in groups.values():
        segs = [s for p in grp for s in p.segs]
        fe = free_ends(segs)
        if len(fe) != 2:
            continue
        a, b = fe
        pts = [q for s in segs for q in s.ends()]
        for p in grp:
            cb = getattr(p, "cbbox", None)
            if cb:
                pts += [(cb[0], cb[1]), (cb[2], cb[3])]
        ax = _hop_shape(a, b, pts, P, tol)
        if ax is None:
            continue
        cross = _hop_cross(a, b, ax, wx, tol)
        if cross is None:
            continue
        mine = {id(p) for p in grp}

        def touches(q):
            for s in sx.near(q):
                if (s.vert if ax == "v" else s.horiz) and min(_d(q, e) for e in s.ends()) <= tol:
                    return True
            return False
        if not (touches(a) or touches(b)):
            continue
        hs = _hop_segs(a, b, ax, cross)
        e0, e1 = hs[0].ends()[0], hs[1].ends()[1]
        pl = geom.Poly(hs, (min(e0[0], e1[0]), min(e0[1], e1[1]), max(e0[0], e1[0]), max(e0[1], e1[1])), pid=grp[0].pid)
        pl.hop = True
        drop |= mine
        add.append(pl)
    if not add:
        return wires, glyphs
    return [p for p in wires if id(p) not in drop] + add, [p for p in glyphs if id(p) not in drop]


def _promote_gap_stubs(glyphs, wires, blocks, P, tol):
    """L71 — 홉 · 끊어 그린 교차 사이에 낀 짧은 토막도 선이다.

    글자 크기 토막은 '두 끝이 다 무언가에 닿을 때만' 선으로 쳤다.  그런데 홉 바로 뒤에서 다른 선을 끊어 건너는 자리
    (홉 → 3pt → 틈 → 다음 토막)는 한 끝이 틈에 떠 있다.  그 토막이 버려지면 틈이 넓어져 건너편과 마주 보지 못하고
    선이 끊긴다.  한 끝이 같은 직선의 선 끝에 맞닿아 이어지고(곧게 · 바깥으로), 다른 끝이 같은 직선의 다음 선 끝과
    마주 보며 그 사이를 직각 선이 지나면 선이다.  두 틈 사이에 낀 토막(두 끝 다 마주 봄)도 선이다.
    새로 선 토막에도 다시 본다 (토막이 이어질 수 있다).
    """
    lim = BREAK_GAP_MAX * P
    while True:
        wsegs = [(s, p) for p in wires for s in p.segs if s.vert or s.horiz]
        wx = _seg_index([s for s, _ in wsegs], tol)
        moved = []
        for p in glyphs:
            if len(p.segs) != 1 or p.dashed:
                continue
            g = p.segs[0]
            if not (g.vert or g.horiz) or g.length <= 0:
                continue
            if any(p.bbox[0] >= bl.bbox[0] - tol and p.bbox[2] <= bl.bbox[2] + tol and
                   p.bbox[1] >= bl.bbox[1] - tol and p.bbox[3] <= bl.bbox[3] + tol for bl in blocks):
                continue
            off = (lambda q: q[0]) if g.vert else (lambda q: q[1])
            along = (lambda q: q[1]) if g.vert else (lambda q: q[0])
            base = off(g.ends()[0])
            same = lambda s: (s.vert if g.vert else s.horiz) and abs(off(s.ends()[0]) - base) <= 0.4 * tol

            def joined(q, o):
                # q 가 같은 직선 선 끝에 맞닿고 그 선은 q 의 반대쪽(o 쪽이 아닌 쪽)으로 뻗는다
                for s in wx.near(q):
                    if not same(s):
                        continue
                    for e, f in ((s.ends()[0], s.ends()[1]), (s.ends()[1], s.ends()[0])):
                        if _d(q, e) <= tol and (along(f) - along(q)) * (along(q) - along(o)) > 0:
                            return True
                return False

            def facing(q, o):
                # q 바깥쪽 lim 안에 같은 직선의 다음 선 끝이 있고 그 사이를 직각 선이 지난다
                sgn = 1 if along(q) > along(o) else -1
                best = None
                for s, _ in wsegs:
                    if not same(s):
                        continue
                    for e in s.ends():
                        d = (along(e) - along(q)) * sgn
                        if tol < d <= lim and (best is None or d < best[0]):
                            best = (d, e)
                if best is None:
                    return False
                lo, hi = sorted((along(q), along(best[1])))
                for s, _ in wsegs:
                    if (s.horiz if g.vert else s.vert) and lo < (s.y0 if g.vert else s.x0) < hi:
                        a0, a1 = sorted(((s.x0, s.x1) if g.vert else (s.y0, s.y1)))
                        if a0 - tol <= base <= a1 + tol:
                            return True
                return False
            a, b = g.ends()
            fa, fb = facing(a, b), facing(b, a)
            if (fb and (joined(a, b) or fa)) or (fa and joined(b, a)):
                moved.append(p)
        if not moved:
            return
        for p in moved:
            glyphs.remove(p)
            wires.append(p)


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


def _group_frames(rects, circles, wires=(), tol=0.0):
    frames = set()
    for r in rects:
        n = sum(1 for o in rects if o is not r and o.x0 >= r.x0 and o.x1 <= r.x1 and o.y0 >= r.y0 and o.y1 <= r.y1)
        n += sum(1 for c in circles if r.x0 <= c.cx <= r.x1 and r.y0 <= c.cy <= r.y1)
        if n >= 3 and (_edge_pins(r, wires, tol) < 2 or _inner_wires(r, wires, tol) >= 3):
            frames.add(id(r))
    return frames


def _inner_wires(r, wires, tol):
    """사각형 안쪽에 통째로 들어 있는 배선 토막 수 — 묶음 틀은 안에 게이트를 잇는 선을 품고, 매크로 상자는 글자 ·
    운전 버튼 칸뿐이다 (HRSG Typical 의 'MOTOR SUB-GROUP BLOCK' 틀 ↔ 1A1Y MTS MACRO · L39)."""
    n = 0
    for p in wires:
        for sg in p.segs:
            if (r.x0 + tol < min(sg.x0, sg.x1) and max(sg.x0, sg.x1) < r.x1 - tol and
                    r.y0 + tol < min(sg.y0, sg.y1) and max(sg.y0, sg.y1) < r.y1 - tol and sg.length > 0):
                n += 1
    return n


def _edge_pins(r, wires, tol):
    """사각형의 왼쪽 · 오른쪽 변에 바깥에서 들어와 끝나는 가로선 수 — 단자다.  묶음 틀은 선이 변을 지나가거나 닿지 않는다.
    (1A1Y MTS MACRO — 안에 운전 버튼 칸 다섯을 품은 매크로 상자가 '묶음 틀' 로 버려졌다 · L39)"""
    n = 0
    tol = max(tol * 2, 1.5 * tol + 1.2)       # 단자 원(반지름 약 1pt) 바깥에서 끝나는 선도 단자다
    for p in wires:
        for sg in p.segs:
            if not sg.horiz:
                continue
            y = sg.y0
            if not (r.y0 + tol < y < r.y1 - tol):
                continue
            a, b = min(sg.x0, sg.x1), max(sg.x0, sg.x1)
            if abs(b - r.x0) <= tol and a < r.x0 - tol or abs(a - r.x1) <= tol and b > r.x1 + tol:
                n += 1
    return n


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
        elif b.kind == "CONNECTOR":
            continue                    # L53 — 연결 기호(원 + 꼭지)는 범례에 입력 막대가 없다
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
        # L53 — 0.1pt 남짓 기운 긴 선(1A5J FG_G-101: 207pt 에 0.09pt)도 축 선분이다.  엄격히 보면 그 선 끝의 열린 화살촉
        # 획이 남아 끝이 '닿은 끝' 이 되고 입력 막대 단자가 서지 않았다 (같은 장의 곧은 선은 섰다).
        dx, dy = abs(t.x1 - t.x0), abs(t.y1 - t.y0)
        near_axial = t.vert or t.horiz or (dx <= max(0.15, 0.004 * dy) and dy > dx) or (dy <= max(0.15, 0.004 * dx) and dx > dy)
        if t is s or not near_axial or t.length <= s.length or t.length < wire_min:
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
            # L23b — 원 안쪽 왼쪽 절반에서 끝나는 선 = 그 원의 입력 (ANSI OR 은 오목한 등 안쪽까지 선을 긋는다)
            if b.kind == "CIRCLE" and _d(e, (c.cx, c.cy)) < c.r - tol * 2 and e[0] < c.cx - 0.3 * c.r:
                return "port", (b, "in", "", 0, e, None)
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


def _triangle(p, P):
    """닫힌 세 변 삼각형 — 세로 밑변 하나(왼쪽) + 오른쪽 꼭지로 모이는 사선 둘 → (bbox, 꼭지) | None.
    크기는 한 행 높이 ~ 3P (선 끝 화살촉보다 크다)."""
    segs = [sg for sg in p.segs if sg.length > 0]
    if len(segs) != 3:
        return None
    cnt = defaultdict(int)
    for sg in segs:
        for q in sg.ends():
            cnt[(round(q[0], 1), round(q[1], 1))] += 1
    if len(cnt) != 3 or any(v != 2 for v in cnt.values()):
        return None
    vert = [sg for sg in segs if sg.vert]
    diag = [sg for sg in segs if not (sg.vert or sg.horiz)]
    if len(vert) != 1 or len(diag) != 2:
        return None
    base = vert[0]
    apex = next((q for q in cnt if abs(q[0] - base.x0) > 0.5), None)
    if apex is None:
        return None
    h = base.length
    w = apex[0] - base.x0
    # 게이트 삼각형은 한 행 높이 이상이고 납작하지 않다 — 선 끝의 속 빈 화살촉(19VA · 높이 7 · 폭 3.5)은 아니다
    if not (P <= h <= 3 * P and 0.6 * h <= w <= 2 * h):
        return None
    ya, yb = sorted((base.y0, base.y1))
    if not (ya + 0.3 * h <= apex[1] <= yb - 0.3 * h):
        return None
    return (base.x0, ya, apex[0], yb), apex


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
    # L28 — 모든 짝의 모든 끝을 견주지 않는다: P 칸 격자에서 이웃 칸의 끝만 (같은 판정 식 · 같은 무리)
    egrid = defaultdict(set)
    for i, es in enumerate(ends):
        for a in es:
            egrid[(math.floor(a[0] / P), math.floor(a[1] / P))].add(i)
    for i in range(len(dashed)):
        near = set()
        for a in ends[i]:
            gx, gy = math.floor(a[0] / P), math.floor(a[1] / P)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    near |= egrid.get((gx + dx, gy + dy), set())
        for j in sorted(near):
            if j <= i:
                continue
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
    tix, tbx, tmemo = _rect_index([(a, a.bbox) for a in arrows], tol), _block_index(blocks, tol), {}

    def term(q):
        # 화살촉 · 블록 변에 닿은 끝은 거기서 끝난다 — 건너뛰어 잇지 않는다
        k = (q[0], q[1])
        if k not in tmemo:
            tmemo[k] = (any(_in_rect(q, a.bbox, tol) for a in tix.near(q)) or
                        any(_block_edge(q, b, tol) for b in tbx.near(q)))
        return tmemo[k]

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
        to_base = set()
        for q in free:
            for a in arrows:
                if _in_rect(q, a.bbox, tol):
                    break                           # L53 — 끝이 이미 화살촉 안(꼭지 위)이다: 밑동으로 되돌아가는 다리를 긋지 않는다
                if _d(q, a.base) <= 1.5 * Lmed and (abs(q[0] - a.base[0]) < tol or abs(q[1] - a.base[1]) < tol):
                    # L53 — 다리는 파선의 축 위에 긋는다.  밑동 좌표 그대로 이으면 0.06pt 기운 선분이 되어
                    # 화살촉 획(`_flick`)으로 버려지고 끝이 단자에 안 붙었다 (1A1Y HR_P001 AND 입력 둘)
                    bx, by = (a.base[0], q[1]) if abs(q[1] - a.base[1]) < tol else (q[0], a.base[1])
                    segs.append(geom.Seg(q[0], q[1], bx, by))
                    to_base.add((round(q[0], 2), round(q[1], 2)))
                    break
        # 파선이 블록 · 막대 · 실선 앞에서 틈 하나를 두고 끝나면 그 틈을 잇는다 (19VA — 마지막 토막이 기호에 안 닿는다 · L21)
        if long_run:
            reach = 1.2 * max(gaps_ + [Lmed])        # 틈 하나 또는 토막 하나 길이까지
            for q0 in free:
                if (round(q0[0], 2), round(q0[1], 2)) in to_base:
                    continue                          # L53 — 화살촉 밑동까지 이미 이었다 (짧은 토막을 또 두면 그 끝이 '닿은 끝' 이 된다)
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
