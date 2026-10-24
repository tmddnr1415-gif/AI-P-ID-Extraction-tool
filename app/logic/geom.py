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
import re
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
    curved: bool = False         # 곡선(c)만으로 그린 열린 호 — 둥근 상자의 끝 (L21 · 19VA ON/OFF DELAY)

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
    rings: list = field(default_factory=list)     # 호 조각들이 닫힌 원 후보 [(Circle, {pid})] (L21)
    frame: tuple | None = None                     # 도면 테두리 (굵게 칠한 큰 사각 띠) — 그 밖은 격자 번호


def _ink(c, inks=()):
    """잉크(검정·회색)만 — 빨강 개정 클라우드는 도면의 표시가 아니다 (P&ID 엔진과 같은 생각).
    L23b — 그 장이 선을 **그 색으로 그린** 양식(파랑 신호선 등)이면 그 색도 잉크다 (`_page_inks`)."""
    if c is None:
        return True
    r, g, b = c[:3]
    return (abs(r - g) < 0.15 and abs(g - b) < 0.15) or _ckey(c) in inks


def _ckey(c):
    return tuple(round(v, 2) for v in c[:3])


def _page_inks(drawings):
    """그 장에서 곧은 선을 많이 그린 회색 아닌 색 — 곧은 선만으로 된 path 의 2할 이상이고 20개 이상.
    개정 표시(빨간 구름 · 삼각형)는 곡선이거나 몇 개뿐이다 (네 묶음 실측: 장당 곧은 빨간 선 0~5)."""
    cnt = {}
    total = 0
    for d in drawings:
        c = d.get("color")
        items = d.get("items") or []
        if not items or "s" not in (d.get("type") or "") or any(it[0] != "l" for it in items):
            continue
        total += 1
        if c is not None and not (abs(c[0] - c[1]) < 0.15 and abs(c[1] - c[2]) < 0.15):
            k = _ckey(c)
            cnt[k] = cnt.get(k, 0) + 1
    return {k for k, n in cnt.items() if n >= 20 and n >= 0.2 * total}


def _f32(v):
    return _F32.unpack(_F32.pack(v))[0]


def _rot_fast(m):
    """회전 · 이동뿐인 행렬(성분 0 · ±1 · 이동이 float 로 정확)이면 (a, b, c, d, e, f) — 아니면 None."""
    a, b, c, d, e, f = m.a, m.b, m.c, m.d, m.e, m.f
    if a in _UNIT and b in _UNIT and c in _UNIT and d in _UNIT and e == _f32(e) and f == _f32(f):
        return (a, b, c, d, e, f)
    return None


def _pt(p, m):
    # L28 — 쪽 회전 행렬은 성분이 0 · ±1 이라 MuPDF 의 float 계산을 double 로 한 뒤 float 로 한 번 반올림하면 같은 값이다
    # (P&ID hotfix70 과 같은 길 · 엔진은 가져오지 않는다).  PyMuPDF 를 부르는 것이 장마다 수만 번이라 분석의 1할이었다.
    # 처음 한 번 PyMuPDF 와 맞대 보고(_PT_OK) 다르면 예전 길로 간다.
    if _PT_OK:
        if _LAST_M[0] is m:                      # 한 장의 점은 같은 행렬 하나를 쓴다
            r = _LAST_M[1]
        else:
            r = _rot_fast(m)
            _LAST_M[0], _LAST_M[1] = m, r
        if r is not None:
            a, b, c, d, e, f = r
            x, y = p.x, p.y
            return (_f32(x * a + y * c + e), _f32(x * b + y * d + f))
    q = p * m
    return (q.x, q.y)


def _pt_selfcheck():
    import random

    import pymupdf
    rnd = random.Random(5)
    try:
        for rot in (0, 90, 180, 270):
            for w, h in ((1191.0, 842.0), (842.0, 1191.0), (2384.0, 1684.0)):
                doc = pymupdf.open()
                pg = doc.new_page(width=w, height=h)
                pg.set_rotation(rot)
                m = pg.rotation_matrix
                if _rot_fast(m) is None:
                    continue
                for _ in range(400):
                    pt = pymupdf.Point(_f32(rnd.uniform(-50, w + 50)), _f32(rnd.uniform(-50, h + 50)))
                    q = pt * m
                    a, b, c, d, e, f = _rot_fast(m)
                    if (q.x, q.y) != (_f32(pt.x * a + pt.y * c + e), _f32(pt.x * b + pt.y * d + f)):
                        return False
        return True
    except Exception:
        return False


import struct as _struct  # noqa: E402

_F32 = _struct.Struct("f")
_UNIT = (0.0, 1.0, -1.0)
_LAST_M = [None, None]
_PT_OK = _pt_selfcheck()


def _bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def _rot_box(b, m):
    r = fitz_rect(b) * m
    return (r.x0, r.y0, r.x1, r.y1)


def fitz_rect(b):
    import pymupdf
    return pymupdf.Rect(b[0], b[1], b[2], b[3])


def words(page):
    """그 장의 진짜 글자 낱말 — **표시 좌표** (L23).

    `get_text` 는 회전 전 좌표를 준다.  그림 요소는 `rotation_matrix` 를 곱해 표시 좌표로 읽으므로
    글자도 같은 자로 옮긴다 — 안 옮기면 270° 로 저장된 장(1A5J)에서 글자가 하나도 표 칸에 안 든다.
    회전 0 이면 받은 그대로다 (HRSG · 19VA 불변)."""
    ws = _one_print(page.get_text("words"))
    if not page.rotation:
        return [(w[0], w[1], w[2], w[3], w[4]) for w in ws]
    m = page.rotation_matrix
    out = []
    for w in ws:
        b = _rot_box(w[:4], m)
        out.append((b[0], b[1], b[2], b[3], w[4]))
    return out


def _one_print(ws):
    """같은 자리에 같은 글자를 겹쳐 찍은 것은 한 낱말이다 (L24 — 1A1Y 는 `AND` 를 같은 자리에 두 번 찍어 블록 글자가
    `AND AND` 가 되어 판정을 못 했다 · P&ID QFE 도 세 번 겹쳐 찍는다).  자리는 0.1pt 로 반올림 — 나란히 쓴 같은 낱말은 남는다."""
    seen = set()
    out = []
    for w in ws:
        k = (round(w[0], 1), round(w[1], 1), round(w[2], 1), round(w[3], 1), w[4])
        if k in seen:
            continue
        seen.add(k)
        out.append(w)
    return out


def text_lines(page):
    """진짜 글자 줄 [(bbox, 글)] — 표시 좌표 (L23 · `words` 와 같은 자)."""
    m = page.rotation_matrix if page.rotation else None
    out = []
    for b in page.get_text("dict").get("blocks", []):
        for ln in b.get("lines", []):
            t = "".join(sp["text"] for sp in ln["spans"]).strip()
            if t:
                bb = tuple(ln["bbox"])
                out.append((_rot_box(bb, m) if m is not None else bb, t))
    return out


def _pdf_dashed(d):
    """PDF 의 선 무늬(dash pattern)로 그린 파선 (L23).  지금까지의 네 묶음은 파선을 토막으로 따로 그려 무늬가 비어 있다
    (`[] 0`) — 무늬로 그리는 양식이 오면 같은 파선으로 읽는다."""
    t = str(d.get("dashes") or "")
    return bool(re.match(r"\[\s*\d", t.strip()))


def read(page, pno: int) -> Prims:
    """한 장의 그림 요소.  좌표는 표시 좌표 (회전 행렬을 곱한다)."""
    m = page.rotation_matrix
    out = Prims(pno, page.rect.width, page.rect.height)
    out.words = words(page)
    pid = 0
    arcs = []
    tris = []
    drawings = page.get_drawings()
    inks = _page_inks(drawings)
    for d in drawings:
        items = d.get("items") or []
        if not items:
            continue
        typ = d.get("type") or ""
        if "f" in typ and not _ink(d.get("fill"), inks):
            continue
        if "s" in typ and not _ink(d.get("color"), inks):
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
            # L53 — 삼각형을 한 path 에 두 번 그린 화살촉(선 6개 · 꼭짓점 3)도 화살촉이다 (HRSG G053 AND 입력 막대의
            # 위쪽 화살 — 못 읽어 그 행이 막대에 안 붙고 AND 가 입력 하나로 섰다)
            if kinds and all(k == "l" for k in kinds) and len(pts) == 3:
                out.arrows.append(_arrow(pts))
                tris.append(pts)
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
        if all(k == "c" for k in kinds) and len(kinds) < 4 and not ("f" in typ):
            # 호 조각 — 원을 사분원 넷으로 따로 그린 양식(19VA)은 아래에서 다시 모은다
            arcs.append((pid, [(_pt(it[1], m), _pt(it[2], m), _pt(it[3], m), _pt(it[4], m)) for it in items]))
            continue
        if all(k == "c" for k in kinds) and len(kinds) >= 4:
            pts = [_pt(it[1], m) for it in items] + [_pt(it[4], m) for it in items]
            bb = _bbox(pts)
            w, h = bb[2] - bb[0], bb[3] - bb[1]
            if w > 0 and 0.8 < h / w < 1.25:
                out.circles.append(Circle((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2, (w + h) / 4, bb))
                continue
            st, en = _pt(items[0][1], m), _pt(items[-1][4], m)
            if w > 0 and h > 0 and abs(st[0] - en[0]) < 0.05 and abs(st[1] - en[1]) < 0.05:
                # 닫힌 납작한 고리(타원) — 범례 ALM 'ANN' (L21).  원 후보와 같이 graph.py 가 크기로 정한다
                c = Circle((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2, (w + h) / 4, bb)
                c.oval = True
                out.rings.append((c, {pid}))
                segs = [Seg(*_pt(it[1], m), *_pt(it[4], m)) for it in items]
                pl = Poly(segs, _bbox(pts), pid=pid, curved=True)
                pl.cbbox = bb
                out.polys.append(pl)
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
        diag = _crossed_rect(segs)
        if diag is not None:                       # 축 변 넷 + 대각선 — ⊠ (19VA NOT · L21): 상자와 그 안의 획
            rr, rest = diag
            out.rects.append(rr)
            out.polys.append(Poly(rest, _bbox([q for sg in rest for q in sg.ends()]), pid=pid))
            continue
        pts = [p for s in segs for p in s.ends()]
        pl = Poly(segs, _bbox(pts), pid=pid, dashed=_pdf_dashed(d))
        if len(segs) >= 12 and not all(sg.horiz or sg.vert for sg in segs) and \
                abs(segs[0].x0 - segs[-1].x1) < 0.05 and abs(segs[0].y0 - segs[-1].y1) < 0.05:
            # 잘게 꺾은선으로 그린 닫힌 고리 (범례 ALM 타원 · L21) — 원 후보 (graph.py 가 크기로 정한다)
            bb = pl.bbox
            w, h = bb[2] - bb[0], bb[3] - bb[1]
            if w > 0 and h > 0:
                c = Circle((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2, (w + h) / 4, bb)
                c.oval = not (0.8 < h / w < 1.25)
                out.rings.append((c, {pid}))
                pl.curved = True
                pl.cbbox = bb
        out.polys.append(pl)
    _gather_arcs(out, arcs)
    _drop_fans(out, tris)
    _diamonds(out, tris)
    return out


def _diamonds(out, tris):
    """L53 — 칠한 삼각형 둘이 **같은 밑변을 공유**하고 셋째 꼭짓점이 밑변의 양쪽에 있으면 그 둘은 화살촉이 아니라
    칠한 마름모 ◆(선 위의 신호 인터페이스 표시)다.  HRSG G067 은 행마다 ◆ 를 위아래 반쪽 삼각형으로 그리고, 네 행의
    ◆ 가 꼭짓점끼리 0.36pt 로 맞닿아 그 둘레 획이 선이 되자 네 행이 한 그물이 되었다."""
    if len(tris) < 2:
        return
    key = lambda q: (round(q[0], 2), round(q[1], 2))
    by_edge = {}
    for t in tris:
        pts = [key(q) for q in t]
        for i in range(3):
            a, b = pts[i], pts[(i + 1) % 3]
            by_edge.setdefault(tuple(sorted((a, b))), []).append((t, pts[(i + 2) % 3]))
    found = []
    for (a, b), lst in by_edge.items():
        if len(lst) != 2:
            continue
        (t1, c1), (t2, c2) = lst
        if t1 is t2:
            continue
        # 셋째 꼭짓점이 밑변 ab 의 서로 다른 쪽
        vx, vy = b[0] - a[0], b[1] - a[1]
        s1 = vx * (c1[1] - a[1]) - vy * (c1[0] - a[0])
        s2 = vx * (c2[1] - a[1]) - vy * (c2[0] - a[0])
        if s1 * s2 >= 0:
            continue
        L = math.hypot(vx, vy)
        if L <= 0:
            continue
        # 마름모 — 두 꼭짓점이 밑변 가운데쯤에서 밑변과 비슷한 높이로 (화살촉 둘이 밑변을 맞댄 것이 아니다)
        ok = True
        for c in (c1, c2):
            t = ((c[0] - a[0]) * vx + (c[1] - a[1]) * vy) / (L * L)
            h = abs(s1 if c is c1 else s2) / L
            if not (0.3 <= t <= 0.7 and 0.3 * L <= h <= 0.8 * L):
                ok = False
        if ok:
            found.append((t1, t2, _bbox(t1 + t2)))
    if not found:
        return
    drop = {id(t) for t1, t2, _ in found for t in (t1, t2)}
    same = lambda a, bb: all(abs(u - v) < 1e-6 for u, v in zip(a, bb))
    dropped_bb = [_bbox(t) for t1, t2, _ in found for t in (t1, t2)]
    out.arrows = [ar for ar in out.arrows if not any(same(ar.bbox, bb) for bb in dropped_bb)]
    for _, _, bb in found:
        out.markers.append(bb)


def _drop_fans(out, tris):
    """한 점에 꼭짓점을 모은 칠한 삼각형 여럿(부채꼴)은 화살촉이 아니라 연결점을 조각내 칠한 것 (19VA · L21).
    화살촉은 혼자 있다 — 서로 다른 삼각형 여섯 이상이 한 꼭짓점을 나눠 가지면 점의 조각(blob)으로 돌린다."""
    if len(tris) < 6:
        return
    key = lambda q: (round(q[0], 2), round(q[1], 2))
    uniq = list({tuple(sorted(key(q) for q in t)): t for t in tris}.values())
    grid = {}
    for i, t in enumerate(uniq):
        for q in t:
            grid.setdefault((int(q[0] * 4), int(q[1] * 4)), []).append((q, i))

    def sharers(q):
        gx, gy = int(q[0] * 4), int(q[1] * 4)
        return {i for dx in (-1, 0, 1) for dy in (-1, 0, 1) for p_, i in grid.get((gx + dx, gy + dy), [])
                if abs(p_[0] - q[0]) < 0.05 and abs(p_[1] - q[1]) < 0.05}
    fan = [t for t in uniq if any(len(sharers(q)) >= 6 for q in t)]
    if not fan:
        return
    boxes = [_bbox(t) for t in fan]
    same = lambda a, b: all(abs(u - v) < 1e-6 for u, v in zip(a, b))
    bgrid = {}                                   # L28 — 화살촉마다 모든 부채꼴과 견주지 않는다 (0.001 칸 이웃만)
    for bb in boxes:
        bgrid.setdefault((math.floor(bb[0] * 1000), math.floor(bb[1] * 1000)), []).append(bb)

    def fanned(a):
        gx, gy = math.floor(a.bbox[0] * 1000), math.floor(a.bbox[1] * 1000)
        return any(same(a.bbox, bb) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for bb in bgrid.get((gx + dx, gy + dy), ()))
    out.arrows = [a for a in out.arrows if not fanned(a)]
    out.blobs.extend(boxes)

def _gather_arcs(out, arcs):
    """따로 그린 호 조각들 (L21 · 19VA 는 원을 사분원 넷으로 따로 그린다).

    조각은 예전처럼 꺾은선(현)으로 남기되 곡선 표시(curved)를 단다.  끝끼리 이어 닫히고 정사각 둘레인 무리는
    원 **후보**(rings)로 따로 적는다 — 원으로 쓸지는 행 간격을 아는 graph.py 가 크기로 정한다 (글자 O 는 원이 아니다).
    """
    if not arcs:
        return
    n = len(arcs)
    par = list(range(n))

    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    ends = [(cs[0][0], cs[-1][3]) for _, cs in arcs]
    close = lambda a, b: abs(a[0] - b[0]) < 0.05 and abs(a[1] - b[1]) < 0.05
    for i in range(n):
        for j in range(i + 1, n):
            if any(close(a, b) for a in ends[i] for b in ends[j]):
                par[f(j)] = f(i)
    groups = {}
    for i in range(n):
        groups.setdefault(f(i), []).append(i)
    # 구름 무리는 따로 묶는다 — 구름 조각은 끝이 정확히 닿지 않는다 (1A1Y 실측 틈 0.02~0.1pt).  틈 허용은 조각 크기(현)의
    # 0.3 배 — 원을 이루는 호 묶기(정확히 닿음)와 섞지 않는다.
    chords = [math.hypot(cs[-1][3][0] - cs[0][0][0], cs[-1][3][1] - cs[0][0][1]) for _, cs in arcs]
    cpar = list(range(n))

    def cf(i):
        while cpar[i] != i:
            cpar[i] = cpar[cpar[i]]
            i = cpar[i]
        return i
    cell = max(max(chords, default=1.0), 1e-3)
    grid = {}
    for i, (a, b) in enumerate(ends):
        for q in (a, b):
            grid.setdefault((int(q[0] // cell), int(q[1] // cell)), []).append(i)
    for i, (a, b) in enumerate(ends):
        for q in (a, b):
            gx, gy = int(q[0] // cell), int(q[1] // cell)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for j in grid.get((gx + dx, gy + dy), ()):
                        if j <= i:
                            continue
                        t = 0.3 * min(chords[i], chords[j])
                        if any(math.hypot(q[0] - e[0], q[1] - e[1]) <= t for e in ends[j]):
                            cpar[cf(j)] = cf(i)
    cgroups = {}
    for i in range(n):
        cgroups.setdefault(cf(i), []).append(i)
    cloud = set()
    for g in cgroups.values():
        # 개정 구름 — 작은 호 여덟 이상을 끝끼리 이은 줄이고 무리 전체가 호 하나보다 훨씬 크다 (1A1Y 의 검은 개정
        # 구름 · L23).  원은 호 넷쯤이고 무리 크기가 호 크기와 같은 자리수다.  구름은 도면의 표시가 아니다 (잉크 색으로
        # 거르는 빨간 구름과 같은 생각) — 신호선으로 두면 선 끝 수십 개가 매달린다.
        if len(g) < 8:
            continue
        chord = max(math.hypot(arcs[i][1][-1][3][0] - arcs[i][1][0][0][0], arcs[i][1][-1][3][1] - arcs[i][1][0][0][1])
                    for i in g)
        pts = [q for i in g for c in arcs[i][1] for q in (c[0], c[3])]
        bb = _bbox(pts)
        if max(bb[2] - bb[0], bb[3] - bb[1]) >= 4 * chord and \
                sum(1 for i in g if _bulge(arcs[i][1]) >= 0.25) >= 0.8 * len(g):
            # 조각마다 크게 부푼다 (구름 한 조각은 반달) — 원을 잘게 나눈 호(램프 원 · 1A5J)는 거의 곧다
            cloud.update(g)
    for i in range(n):
        if i in cloud:
            continue
        pid, cs = arcs[i]
        segs = [Seg(c[0][0], c[0][1], c[3][0], c[3][1]) for c in cs]
        pl = Poly(segs, _bbox([q for sg in segs for q in sg.ends()]), pid=pid, curved=True)
        pl.cbbox = _bbox([q for c in cs for q in (c[0], c[3], _arc_mid(c))])      # 곡선이 실제로 닿는 둘레
        out.polys.append(pl)
    todo = []
    for g in groups.values():
        if len(g) < 3 or cloud.intersection(g):
            continue
        es = [e for i in g for e in ends[i]]
        # 닫힘 = 끝마다 맞닿은 끝이 꼭 하나 (반올림 칸으로 세면 524.55 ↔ 524.5499 가 갈린다)
        if all(sum(1 for q in es if close(e, q)) == 2 for e in es):
            todo.append(g)
            continue
        # L38 — 맞닿게 쌓아 그린 원들(1A5J 표시등 R·G·R·G·Y 세로 줄)은 위 원의 아래 끝이 아래 원의 위 끝이라 끝으로
        # 묶으면 한 무리가 되고 닫힘이 깨진다.  그때만 조각마다 자기 원의 중심(시작·가운데·끝 세 점의 외심)으로 다시
        # 가르고 갈래마다 닫힘을 본다 — 닫힌 무리는 이 갈래에 오지 않으므로 이미 읽히던 원은 그대로다.
        cen = {}
        for i in g:
            cc = _arc_centre(arcs[i][1])
            if cc is not None:
                cen[i] = cc
        sub = {}
        for i, (cx, cy, r) in cen.items():
            for k, (kx, ky, kr) in list(sub.items()):
                if math.hypot(cx - kx, cy - ky) < 0.15 * max(r, kr) and abs(r - kr) < 0.15 * max(r, kr):
                    sub[k + (i,)] = sub.pop(k)
                    break
            else:
                sub[(i,)] = (cx, cy, r)
        for part in sub:
            if len(part) < 3:
                continue
            ps = [e for i in part for e in ends[i]]
            if all(sum(1 for q in ps if close(e, q)) == 2 for e in ps):
                todo.append(list(part))
    for g in todo:
        bb = _bbox([q for i in g for c in arcs[i][1] for q in (c[0], c[3])] +
                   [_arc_mid(c) for i in g for c in arcs[i][1]])
        w, h = bb[2] - bb[0], bb[3] - bb[1]
        if w > 0 and h > 0:
            c = Circle((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2, (w + h) / 4, bb)
            c.oval = not (0.8 < h / w < 1.25)          # 납작한 고리(타원) — 범례 ALM 'ANN' 처럼 둥근 상자
            out.rings.append((c, {arcs[i][0] for i in g}))


def _arc_centre(cs):
    """호 조각이 놓인 원의 (중심 x, 중심 y, 반지름) — 시작 · 가운데 · 끝 세 점의 외심.  곧으면 None."""
    a, b = cs[0][0], cs[-1][3]
    mid = _arc_mid(cs[len(cs) // 2]) if len(cs) % 2 else cs[len(cs) // 2][0]
    ax, ay, bx, by, cx, cy = a[0], a[1], mid[0], mid[1], b[0], b[1]
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-9:
        return None
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    return ux, uy, math.hypot(ax - ux, ay - uy)


def _bulge(cs):
    """호 조각이 얼마나 부풀었나 — 현에서 가장 먼 곡선 위 점까지의 거리 ÷ 현 길이."""
    a, b = cs[0][0], cs[-1][3]
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    if L <= 0:
        return 0.0
    pts = [q for c in cs for q in (c[3], _arc_mid(c))]
    return max(abs((b[0] - a[0]) * (a[1] - q[1]) - (a[0] - q[0]) * (b[1] - a[1])) / L for q in pts) / L


def _arc_mid(c):
    """3차 베지어의 가운데 점 (t=0.5)."""
    p0, p1, p2, p3 = c
    return ((p0[0] + 3 * p1[0] + 3 * p2[0] + p3[0]) / 8, (p0[1] + 3 * p1[1] + 3 * p2[1] + p3[1]) / 8)


def _crossed_rect(segs):
    """축 선분 넷이 닫힌 사각형이고 나머지가 그 안의 대각선이면 (사각형, 대각선들)."""
    ax = [sg for sg in segs if sg.horiz or sg.vert]
    dg = [sg for sg in segs if not (sg.horiz or sg.vert)]
    if len(ax) != 4 or not dg:
        return None
    rr = _closed_rect(ax)
    if rr is None:
        return None
    t = 0.05
    if all(rr.x0 - t <= x <= rr.x1 + t and rr.y0 - t <= y <= rr.y1 + t for sg in dg for x, y in sg.ends()):
        return rr, dg
    return None


def _vertices(items, m):
    # L28 — 이미 받은 점과 1e-3 안이면 같은 점.  예전에는 받은 점 전부와 견줘(점 수의 제곱) 큰 path 하나에 수 초를
    # 썼다 — 0.001 칸 격자에서 이웃 칸만 본다 (판정 식은 그대로 · 같은 순서 · 같은 결과).
    pts = []
    grid = {}
    for it in items:
        if it[0] != "l":
            continue
        for q in (_pt(it[1], m), _pt(it[2], m)):
            gx, gy = math.floor(q[0] * 1000), math.floor(q[1] * 1000)
            if any(abs(q[0] - a) < 1e-3 and abs(q[1] - b) < 1e-3
                   for dx in (-2, -1, 0, 1, 2) for dy in (-2, -1, 0, 1, 2) for a, b in grid.get((gx + dx, gy + dy), ())):
                continue
            pts.append(q)
            grid.setdefault((gx, gy), []).append(q)
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
        return _cell_layout(prims) or _coverage_layout(prims)
    vs.sort()
    xs = []
    for x, a, b in vs:
        if xs and abs(x - xs[-1][0]) < 0.5:
            continue
        xs.append((x, a, b))
    if len(xs) < 2:
        # 긴 세로선이 다섯 이상인데 x 가 하나뿐 — 표 괘선이 아니라 한 자리에 겹쳐 그린 선이다 (1A1Y · L23).
        # 예전엔 여기서 `max()` 가 빈 목록으로 죽어 분석 전체가 멈췄다 → 다른 양식의 표 읽기로 넘긴다.
        return _cell_layout(prims) or _coverage_layout(prims)
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
    if x0 - left_cols[0] < 2 * pitch or right_cols[-1] - x1 < 2 * pitch:
        return None              # 양쪽 표가 글자 한 칸도 못 담는다 — 도면 테두리 띠다 (19VA 표지 · L21)
    # LOGIC 영역의 위·아래는 표의 첫 행 위 · 마지막 행 아래 (머리글 칸은 영역이 아니다)
    y0 = min(lrows[0][0], rrows[0][0])
    y1 = max(lrows[-1][1], rrows[-1][1])
    L = [(k + 1, a, b) for k, (a, b) in enumerate(lrows)]
    R = [(len(L) + k + 1, a, b) for k, (a, b) in enumerate(rrows)]
    return Layout((x0, y0, x1, y1), pitch, L, R, [x for x, _, _ in xs],
                  note="행 번호는 표의 위→아래 순서 (왼쪽 1부터, 오른쪽은 이어서)")


def _cell_layout(prims):
    """표를 긴 괘선이 아니라 **칸마다 사각형**으로 그린 양식 (19VA · L21).

    같은 크기의 칸이 같은 x 에 여러 번(행마다) 되풀이되는 사각형만 표 칸으로 본다 — 블록 상자는 되풀이되지 않는다.
    칸 높이의 최빈값이 P 이고, LOGIC 영역은 표 칸 경계 사이의 가장 넓은 틈이다 (긴 괘선 양식과 같은 정의).
    """
    H = prims.height
    cnt = Counter((round(r.x0, 1), round(r.w, 1), round(r.h, 1)) for r in prims.rects
                  if 1 < r.h < 0.1 * H and r.w > 1)          # 점 크기 사각형(0.1pt — CAD 의 삽입점 흔적)은 칸이 아니다
    if not cnt:
        return None
    reps = sorted(cnt.values(), reverse=True)
    need = max(5, reps[0] // 2)                 # 표의 열은 행 수만큼 되풀이된다 — 가장 많은 열의 절반 이상
    cols = {k for k, v in cnt.items() if v >= need}
    if len(cols) < 4:
        return None
    cells = [r for r in prims.rects if (round(r.x0, 1), round(r.w, 1), round(r.h, 1)) in cols]
    pitch = Counter(round(r.h, 1) for r in cells).most_common(1)[0][0]
    edges = sorted({round(r.x0, 1) for r in cells} | {round(r.x1, 1) for r in cells})
    xs = []
    for x in edges:
        if not xs or x - xs[-1] > 0.5:
            xs.append(x)
    gaps = [(xs[i + 1] - xs[i], i) for i in range(len(xs) - 1)]
    w, i = max(gaps)
    left_cols, right_cols = xs[: i + 1], xs[i + 1:]
    if len(left_cols) < 2 or len(right_cols) < 2:
        return None
    x0, x1 = xs[i], xs[i + 1]

    def side_rows(a, b):
        ys = sorted({(round(r.y0, 2), round(r.y1, 2)) for r in cells
                     if a - 0.5 <= r.x0 and r.x1 <= b + 0.5 and abs(r.h - pitch) <= 0.2 * pitch})
        out = []
        for y0, y1 in ys:
            if out and y0 < out[-1][1] - 0.2 * pitch:
                continue
            gap = y0 - out[-1][1] if out else 0
            m = round(gap / pitch) if pitch > 0 else 0
            if 1 <= m <= 4 and abs(gap - m * pitch) <= 0.2 * pitch:
                # 칸 하나가 다른 모양(합친 칸 · 빠진 칸)이라 그 행이 안 잡혔다 — 그 아래 행 번호가 밀리지 않게 채운다 (1A5J · L23)
                a, step = out[-1][1], gap / m
                for j in range(m):
                    out.append((a + j * step, a + (j + 1) * step))
            out.append((y0, y1))
        return out
    lrows = side_rows(left_cols[0], x0)
    rrows = side_rows(x1, right_cols[-1])
    if len(lrows) < 3 or len(rrows) < 3:
        return None
    y0 = min(lrows[0][0], rrows[0][0])
    y1 = max(lrows[-1][1], rrows[-1][1])
    L = [(k + 1, a, b) for k, (a, b) in enumerate(lrows)]
    R = [(len(L) + k + 1, a, b) for k, (a, b) in enumerate(rrows)]
    return Layout((x0, y0, x1, y1), pitch, L, R, xs,
                  note="표 칸을 사각형으로 그린 양식 — 칸 경계로 열을, 칸 높이로 행을 읽었다")


def _coverage_layout(prims):
    """표의 세로 괘선을 **행마다 끊어** 그린 양식 (19VA 의 Typical 시트 · L21).

    같은 x 의 세로 토막을 모아 그 길이 합이 종이 높이의 0.6 이상이면 괘선이다 (긴 괘선 양식과 같은 문턱).
    파선 테두리(묶음 틀)는 토막이 많아도 합이 표 높이에 못 미친다.  행은 칸 하나를 가로지르는 가로선의 높이다.
    """
    H = prims.height
    cov = {}
    pieces = Counter()
    for s in _straight(prims):
        if s.vert:
            x = round(s.x0, 1)
            cov[x] = cov.get(x, 0.0) + abs(s.y1 - s.y0)
            pieces[x] += 1
    # 칸 몇 개를 사각형으로 그린 줄도 같은 괘선이다 — 그 칸의 세로 변도 길이에 더한다 (1A5J 0034 · SERVICE 칸 오른쪽
    # 괘선이 선 토막 + 칸 사각형으로 섞여 길이 합 0.58H 로 문턱에 못 미쳐 LOGIC 영역 왼쪽 경계가 틀렸다 · L39)
    for r in prims.rects:
        if 1 < r.h < 0.1 * H and r.w > 1:
            for x in (round(r.x0, 1), round(r.x1, 1)):
                cov[x] = cov.get(x, 0.0) + r.h
                pieces[x] += 1
    # 표 괘선은 **행마다** 끊겨 토막이 행 수만큼이다.  LOGIC 영역의 긴 신호선도 길이 합은 넘지만 토막이 몇 개뿐이다
    # (1A5J · L23: 신호선 넷이 괘선으로 읽혀 LOGIC 영역이 엉뚱한 틈으로 잡히고 행 번호가 밀렸다).
    most = max(pieces.values(), default=0)
    core = [x for x, c in cov.items() if c > 0.6 * H and pieces[x] >= 0.25 * most]
    lo, hi = (min(core), max(core)) if core else (0.0, 0.0)
    fr = prims.frame
    xs = []
    # 표 바깥 변(긴 선 하나로 그린 테두리)은 토막이 적어도 괘선이다 — 걸러 내는 것은 표 **안쪽** 열 사이의 신호선뿐
    for x in sorted(x for x, c in cov.items() if c > 0.6 * H and (pieces[x] >= 0.25 * most or x < lo or x > hi)
                    and (fr is None or fr[0] - 1 <= x <= fr[2] + 1) and 1 < x < prims.width - 1):     # 종이 가장자리 선은 표가 아니다
        if not xs or x - xs[-1] > 0.5:
            xs.append(x)
    if len(xs) < 5:
        return None
    gaps = [(xs[i + 1] - xs[i], i) for i in range(len(xs) - 1)]
    w, i = max(gaps)
    left_cols, right_cols = xs[: i + 1], xs[i + 1:]
    if len(left_cols) < 2 or len(right_cols) < 2:
        return None
    x0, x1 = xs[i], xs[i + 1]
    lrows = _rows_cols(prims, left_cols)
    rrows = _rows_cols(prims, right_cols)
    if len(lrows) < 3 or len(rrows) < 3:
        return None
    pitch = Counter(round(b - a, 1) for a, b in lrows + rrows).most_common(1)[0][0]
    y0 = min(lrows[0][0], rrows[0][0])
    y1 = max(lrows[-1][1], rrows[-1][1])
    L = [(k + 1, a, b) for k, (a, b) in enumerate(lrows)]
    R = [(len(L) + k + 1, a, b) for k, (a, b) in enumerate(rrows)]
    return Layout((x0, y0, x1, y1), pitch, L, R, xs,
                  note="표 괘선을 행마다 끊어 그린 양식 — 토막 길이 합으로 열을, 칸 가로선으로 행을 읽었다")


def _rows_cols(prims, cols):
    """칸(이웃한 두 괘선 사이) 하나 이상을 가로지르는 가로선의 높이 → 행."""
    ys = Counter()
    for s in _straight(prims):
        if not s.horiz:
            continue
        a, b = min(s.x0, s.x1), max(s.x0, s.x1)
        for k in range(len(cols) - 1):
            w = cols[k + 1] - cols[k]
            if a <= cols[k] + 0.1 * w and b >= cols[k + 1] - 0.1 * w:
                ys[round(s.y0, 1)] += 1             # 칸마다 센다 — 표 아래 테두리처럼 한 선이 여러 칸을 덮는다
    need = max(1, (len(cols) - 1) // 2)
    y = sorted(v for v, c in ys.items() if c >= need)
    if len(y) < 3:
        return []
    gaps = [y[k + 1] - y[k] for k in range(len(y) - 1)]
    pitch = Counter(round(g, 1) for g in gaps).most_common(1)[0][0]
    return _pitch_rows(y, gaps, pitch)


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
    return _pitch_rows(ys, gaps, pitch)


def _pitch_rows(ys, gaps, pitch):
    """가로선 사이마다 한 행.  틈이 P 의 정수배(둘 이상)면 그 사이의 행 괘선이 빠진 것이다 — 행을 그 수만큼 나눈다
    (1A5J · L23: 격자 표시 눈금 자리에서 행 괘선이 끊겨 그 아래 행 번호가 하나씩 밀렸다).  정수배가 아닌 틈은 행이 아니다."""
    rows = []
    for k, g in enumerate(gaps):
        if abs(g - pitch) <= 0.2 * pitch:
            rows.append((ys[k], ys[k + 1]))
            continue
        m = round(g / pitch) if pitch > 0 else 0
        if 2 <= m <= 4 and abs(g - m * pitch) <= 0.2 * pitch and _between_rows(rows, ys, gaps, k, pitch):
            step = g / m
            for j in range(m):
                rows.append((ys[k] + j * step, ys[k] + (j + 1) * step))
    return rows


def _between_rows(rows, ys, gaps, k, pitch):
    """그 틈이 표 행 사이에 끼어 있는가 — 바로 앞 틈도 바로 뒤 틈도 P 간격 행이다 (표 끝 너머 · 범례 칸 사이는 아니다)."""
    return bool(rows) and rows[-1][1] == ys[k] and k + 1 < len(gaps) and abs(gaps[k + 1] - pitch) <= 0.2 * pitch
