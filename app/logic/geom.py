"""Logic 시트의 기하를 읽는다 — 선 · 상자 · 원 · 화살촉 · 연결점 · 표의 행.

판정을 하지 않는다.  그림 요소를 갈래로 나눌 뿐이다 (graph.py 가 잇는다).

허용치는 전부 그 시트에서 잰 **표 행 간격 P** 의 배율이다 (코드에 절대 pt 없음):
  * 글자 획      — 크기가 0.45·P 보다 작은 꺾은선 (P 는 표의 한 칸 높이, 글자는 그 안에 든다)
  * 연결점       — 지름이 0.35·P 보다 작은 원 (글자보다 작다 · 범례 G003 "DOT REPRESENTS LOGIC CONNECTION")
  * 맞닿음       — 0.08·P (CAD 좌표는 끝점이 정확히 겹친다 — 실측 0.00 · 여유만 둔다)
LOGIC 영역은 표의 세로 괘선 중 **가장 넓은 사이**다 (양쪽 표에 열이 둘 이상일 때만 — 아니면 Logic 시트가 아니다).
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

GLYPH_MAX = 0.45      # × P
DOT_MAX = 0.35        # × P
TOUCH = 0.08          # × P
RECT_MIN = 0.2        # × P — 이보다 작은 사각형은 상자가 아니다 (표 괘선 조각)


@dataclass
class Seg:
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def horiz(self):
        return abs(self.y0 - self.y1) <= 1e-6 * max(1.0, abs(self.x1 - self.x0)) or abs(self.y0 - self.y1) < 0.01

    @property
    def vert(self):
        return abs(self.x0 - self.x1) < 0.01

    @property
    def length(self):
        return math.hypot(self.x1 - self.x0, self.y1 - self.y0)

    def ends(self):
        return ((self.x0, self.y0), (self.x1, self.y1))


@dataclass
class Poly:                     # 꺾은선 한 path
    segs: list
    bbox: tuple
    dashed: bool = False
    pid: int = 0

    @property
    def size(self):
        return max(self.bbox[2] - self.bbox[0], self.bbox[3] - self.bbox[1])


@dataclass
class Arrow:
    tip: tuple
    base: tuple
    dir: tuple                  # 단위 벡터 (base → tip)
    bbox: tuple


@dataclass
class Circle:
    cx: float
    cy: float
    r: float
    bbox: tuple


@dataclass
class Rect:
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def w(self):
        return self.x1 - self.x0

    @property
    def h(self):
        return self.y1 - self.y0


@dataclass
class Prims:
    page: int
    width: float
    height: float
    polys: list = field(default_factory=list)
    arrows: list = field(default_factory=list)
    circles: list = field(default_factory=list)
    rects: list = field(default_factory=list)
    words: list = field(default_factory=list)
    markers: list = field(default_factory=list)   # 칠한 ◆ ■ (선 위의 신호 인터페이스 표시)
    blobs: list = field(default_factory=list)     # 칠한 작은 조각의 bbox (연결점을 조각으로 칠한 양식)
    frame: tuple | None = None                     # 도면 테두리 (굵게 칠한 큰 사각 띠) — 그 밖은 격자 번호


def _ink(c):
    """잉크(검정·회색)만 — 빨강 개정 클라우드는 도면의 표시가 아니다 (P&ID 엔진과 같은 생각)."""
    if c is None:
        return True
    r, g, b = c[:3]
    return abs(r - g) < 0.15 and abs(g - b) < 0.15


def _pt(p, m):
    q = p * m
    return (q.x, q.y)


def _bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def read(page, pno: int) -> Prims:
    """한 장의 그림 요소.  좌표는 표시 좌표 (회전 행렬을 곱한다)."""
    m = page.rotation_matrix
    out = Prims(pno, page.rect.width, page.rect.height)
    out.words = [(w[0], w[1], w[2], w[3], w[4]) for w in page.get_text("words")]
    pid = 0
    for d in page.get_drawings():
        items = d.get("items") or []
        if not items:
            continue
        typ = d.get("type") or ""
        if "f" in typ and not _ink(d.get("fill")):
            continue
        if "s" in typ and not _ink(d.get("color")):
            continue
        kinds = [it[0] for it in items]
        if d.get("fill") is not None and (d.get("width") or 0) == 0:
            # 칠한 도형.  화살촉(삼각형) · 굵게 칠한 고리(원) · 마커(◆ ■) 만 쓴다.
            # 연결점 안의 칠 조각 · 굵은 테두리 · 굵은 글자는 버린다.
            pts = _vertices(items, m)
            if pts:
                fb = _bbox(pts)
                if fb[2] - fb[0] > 0.8 * out.width and fb[3] - fb[1] > 0.8 * out.height:
                    out.frame = fb
                    continue
            if pts and len(pts) != 3:
                out.blobs.append(_bbox(pts))
            if kinds == ["l", "l", "l"] and len(pts) == 3:
                out.arrows.append(_arrow(pts))
            elif len(pts) >= 12:
                bb = _bbox(pts)
                w, h = bb[2] - bb[0], bb[3] - bb[1]
                if w > 0 and 0.8 < h / w < 1.25:
                    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
                    ds = [math.hypot(x - cx, y - cy) for x, y in pts]
                    if min(ds) > 0.6 * max(ds):        # 고리 — 안쪽 꼭짓점도 중심에서 멀다
                        out.circles.append(Circle(cx, cy, (w + h) / 4, bb))
            elif len(pts) == 4:
                bb = _bbox(pts)
                w, h = bb[2] - bb[0], bb[3] - bb[1]
                if min(w, h) * 8 < max(w, h):
                    # 가늘게 칠한 사각형 = 굵은 선 (입력 막대를 칠로 그린 양식) — 가운데 선으로
                    pid += 1
                    if w < h:
                        x = (bb[0] + bb[2]) / 2
                        sg = Seg(x, bb[1], x, bb[3])
                    else:
                        y = (bb[1] + bb[3]) / 2
                        sg = Seg(bb[0], y, bb[2], y)
                    out.polys.append(Poly([sg], (sg.x0, sg.y0, sg.x1, sg.y1), pid=pid))
                else:
                    out.markers.append(bb)
            continue
        pid += 1
        if all(k == "c" for k in kinds) and len(kinds) >= 4:
            pts = [_pt(it[1], m) for it in items] + [_pt(it[4], m) for it in items]
            bb = _bbox(pts)
            w, h = bb[2] - bb[0], bb[3] - bb[1]
            if w > 0 and 0.8 < h / w < 1.25:
                out.circles.append(Circle((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2, (w + h) / 4, bb))
                continue
        segs = []
        for it in items:
            k = it[0]
            if k == "l":
                a, b = _pt(it[1], m), _pt(it[2], m)
                segs.append(Seg(a[0], a[1], b[0], b[1]))
            elif k == "c":
                a, b = _pt(it[1], m), _pt(it[4], m)
                segs.append(Seg(a[0], a[1], b[0], b[1]))
            elif k == "re":
                r = it[1] * m
                out.rects.append(Rect(r.x0, r.y0, r.x1, r.y1))
            elif k == "qu":
                q = it[1]
                pts = [_pt(q.ul, m), _pt(q.ur, m), _pt(q.lr, m), _pt(q.ll, m)]
                bb = _bbox(pts)
                axis = all(min(abs(x - bb[0]), abs(x - bb[2])) < 0.05 and min(abs(y - bb[1]), abs(y - bb[3])) < 0.05
                           for x, y in pts)
                if axis:
                    out.rects.append(Rect(*bb))
                else:
                    out.markers.append(bb)        # 마름모 ◆ — 선 위의 신호 인터페이스 표시
        if not segs:
            continue
        rr = _closed_rect(segs)
        if rr is not None:
            out.rects.append(rr)
            continue
        pts = [p for s in segs for p in s.ends()]
        out.polys.append(Poly(segs, _bbox(pts), pid=pid))
    return out


def _vertices(items, m):
    pts = []
    for it in items:
        if it[0] != "l":
            continue
        for q in (_pt(it[1], m), _pt(it[2], m)):
            if not any(abs(q[0] - a) < 1e-3 and abs(q[1] - b) < 1e-3 for a, b in pts):
                pts.append(q)
    return pts


def _arrow(pts):
    # 꼭지 = 가장 짧은 변의 맞은편 꼭짓점.  밑변 가운데 → 꼭지가 방향이다.
    best = None
    for i in range(3):
        a, b = pts[(i + 1) % 3], pts[(i + 2) % 3]
        L = math.hypot(a[0] - b[0], a[1] - b[1])
        if best is None or L < best[0]:
            best = (L, i, a, b)
    _, i, a, b = best
    tip = pts[i]
    base = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    dx, dy = tip[0] - base[0], tip[1] - base[1]
    n = math.hypot(dx, dy) or 1.0
    return Arrow(tip, base, (dx / n, dy / n), _bbox(pts))


def _closed_rect(segs):
    """선 넷이 닫힌 축정렬 사각형이면 그 사각형."""
    if len(segs) != 4:
        return None
    if not all(s.horiz or s.vert for s in segs):
        return None
    pts = [p for s in segs for p in s.ends()]
    bb = _bbox(pts)
    if bb[2] - bb[0] < 0.01 or bb[3] - bb[1] < 0.01:
        return None
    on = all((abs(p[0] - bb[0]) < 0.05 or abs(p[0] - bb[2]) < 0.05) and
             (abs(p[1] - bb[1]) < 0.05 or abs(p[1] - bb[3]) < 0.05) for p in pts)
    if not on:
        return None
    return Rect(*bb)


# ---------------------------------------------------------------- 표 구조

@dataclass
class Layout:
    logic: tuple                 # (x0, y0, x1, y1) LOGIC 영역
    pitch: float                 # 표 행 간격 P
    left_rows: list              # [(n, y0, y1)]
    right_rows: list
    columns: list                # 세로 괘선 x
    note: str = ""


def _straight(prims):
    for p in prims.polys:
        for s in p.segs:
            yield s


def layout(prims: Prims):
    """표의 세로 괘선 · LOGIC 영역 · 행.  못 찾으면 None (Logic 표 시트가 아니다)."""
    H = prims.height
    vs = []
    for s in _straight(prims):
        if s.vert and abs(s.y1 - s.y0) > 0.6 * H:
            vs.append((s.x0, min(s.y0, s.y1), max(s.y0, s.y1)))
    for r in prims.rects:                     # 표 괘선을 사각형으로 그린 양식
        if r.h > 0.6 * H and r.w < 0.01:
            vs.append((r.x0, r.y0, r.y1))
    if len(vs) < 5:
        return None
    vs.sort()
    xs = []
    for x, a, b in vs:
        if xs and abs(x - xs[-1][0]) < 0.5:
            continue
        xs.append((x, a, b))
    gaps = [(xs[i + 1][0] - xs[i][0], i) for i in range(len(xs) - 1)]
    w, i = max(gaps)
    left_cols = [x for x, _, _ in xs[: i + 1]]
    right_cols = [x for x, _, _ in xs[i + 1:]]
    if len(left_cols) < 2 or len(right_cols) < 2:
        return None
    x0, x1 = xs[i][0], xs[i + 1][0]
    y0 = max(xs[i][1], xs[i + 1][1])
    y1 = min(xs[i][2], xs[i + 1][2])
    lrows = _rows(prims, left_cols[0], x0, y0, y1)
    rrows = _rows(prims, x1, right_cols[-1], y0, y1)
    if not lrows or not rrows:
        return None
    pitch = Counter(round(b - a, 1) for a, b in lrows + rrows).most_common(1)[0][0]
    # LOGIC 영역의 위·아래는 표의 첫 행 위 · 마지막 행 아래 (머리글 칸은 영역이 아니다)
    y0 = min(lrows[0][0], rrows[0][0])
    y1 = max(lrows[-1][1], rrows[-1][1])
    L = [(k + 1, a, b) for k, (a, b) in enumerate(lrows)]
    R = [(len(L) + k + 1, a, b) for k, (a, b) in enumerate(rrows)]
    return Layout((x0, y0, x1, y1), pitch, L, R, [x for x, _, _ in xs],
                  note="행 번호는 표의 위→아래 순서 (왼쪽 1부터, 오른쪽은 이어서)")


def _rows(prims, xa, xb, y0, y1):
    ys = set()
    span = xb - xa
    for s in _straight(prims):
        if s.horiz and min(s.x0, s.x1) <= xa + 0.1 * span and max(s.x0, s.x1) >= xb - 0.1 * span:
            if y0 - 1 <= s.y0 <= y1 + 1:
                ys.add(round(s.y0, 2))
    ys = sorted(ys)
    if len(ys) < 3:
        return []
    gaps = [ys[k + 1] - ys[k] for k in range(len(ys) - 1)]
    pitch = Counter(round(g, 1) for g in gaps).most_common(1)[0][0]
    rows = []
    for k, g in enumerate(gaps):
        if abs(g - pitch) <= 0.2 * pitch:
            rows.append((ys[k], ys[k + 1]))
    return rows
