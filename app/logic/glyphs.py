"""선으로 그린 글자를 읽는다 — 같은 묶음 안의 짝으로 배운 사전 (설계 §1-2).

LLM · OCR 을 쓰지 않는다.  CAD 글꼴은 같은 글자를 같은 선으로 그리므로, 묶음 안에서 **진짜 글자로 같은
말을 한 자리**를 찾아 선 글자의 모양을 배우고, 그 모양에 맞대 읽는다.

짝 (구조가 정답을 준다):
  ① 표의 NO. 열 — k 번째 행의 글자는 k (숫자 0~9)
  ② 도면 목록 — 목록 k 번째 행 (선 글자: 번호 · 제목 · 쪽 번호) ↔ PDF k 번째 장의 타이틀블록 (진짜 글자)
     짝은 글자 수가 맞을 때만 맺는다 (맞지 않으면 그 행을 쓰지 않는다 — 추측하지 않는다).

판독마다 일치도와 2위 글자와의 차를 남기고, 차가 없으면 `?` 로 둔다.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np

N = 32                      # 래스터 한 변


@dataclass
class Char:
    bbox: tuple
    segs: list
    raster: frozenset = field(default=frozenset())

    @property
    def h(self):
        return self.bbox[3] - self.bbox[1]

    @property
    def w(self):
        return self.bbox[2] - self.bbox[0]

    @property
    def cx(self):
        return (self.bbox[0] + self.bbox[2]) / 2

    @property
    def cy(self):
        return (self.bbox[1] + self.bbox[3]) / 2


def _bb(segs):
    xs = [v for s in segs for v in (s.x0, s.x1)]
    ys = [v for s in segs for v in (s.y0, s.y1)]
    return (min(xs), min(ys), max(xs), max(ys))


THIN = 0.3                  # 폭/높이가 이보다 작으면 가는 글자(I 1 -) — 늘리지 않고 가운데에 둔다


def raster(segs, bbox=None):
    """글자 상자를 N×N 에 채운다 — 가로·세로를 따로 늘린다.

    같은 글꼴이라도 칸마다 글자 폭 비율(width factor)이 다르다 (실측: 표 칸 H 2.28×4.92 ↔ 도면 목록 H
    4.9 폭) — 비를 지키면 같은 글자가 안 맞는다.  가는 글자만 늘리지 않는다.
    """
    bb = bbox or _bb(segs)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    sx = w if w >= THIN * h else max(h, 1e-6)
    sy = h if h >= THIN * w else max(w, 1e-6)
    sx, sy = max(sx, 1e-6), max(sy, 1e-6)
    ox = (sx - w) / 2
    oy = (sy - h) / 2
    cells = set()
    for s in segs:
        L = max(abs(s.x1 - s.x0) / sx, abs(s.y1 - s.y0) / sy) * N
        steps = max(2, int(L * 2) + 1)
        for t in range(steps + 1):
            x = s.x0 + (s.x1 - s.x0) * t / steps
            y = s.y0 + (s.y1 - s.y0) * t / steps
            cx = min(N - 1, int((x - bb[0] + ox) / sx * N))
            cy = min(N - 1, int((y - bb[1] + oy) / sy * N))
            cells.add((cx, cy))
    return frozenset(cells)


CAP = 10                    # 거리 지도 상한 (칸) — 그보다 먼 획은 다 같이 '멀다'


def _mask(r):
    m = np.zeros(N * N, dtype=np.float32)
    if r:
        idx = np.fromiter((y * N + x for x, y in r), dtype=np.int64)
        m[idx] = 1.0
    return m


_DT = {}


def _dt(r):
    """체스판 거리 지도 (상한 CAP) — numpy 팽창을 CAP 번.  같은 래스터는 한 번만 잰다."""
    hit = _DT.get(r)
    if hit is not None:
        return hit
    cur = _mask(r).reshape(N, N) > 0
    d = np.full((N, N), CAP, dtype=np.float32)
    d[cur] = 0
    for k in range(1, CAP):
        nxt = cur.copy()
        nxt[1:, :] |= cur[:-1, :]
        nxt[:-1, :] |= cur[1:, :]
        nxt[:, 1:] |= nxt[:, :-1].copy()
        nxt[:, :-1] |= nxt[:, 1:].copy()
        new = nxt & ~cur
        if not new.any():
            break
        d[new] = k
        cur = nxt
    d = d.reshape(-1)
    if len(_DT) > 50000:
        _DT.clear()
    _DT[r] = d
    return d


def score(a, b):
    """두 래스터의 맞음 (0~1) — 서로의 획에서 상대 획까지 평균 거리(칸)의 역수.  1 = 같은 그림."""
    if not a or not b:
        return 0.0
    ma, mb = _mask(a), _mask(b)
    m1 = float(_dt(b) @ ma) / len(a)
    m2 = float(_dt(a) @ mb) / len(b)
    return 1.0 / (1.0 + 0.5 * (m1 + m2))


def chars(polys, gap=0.15):
    """글자 획 path 들을 글자로 — 서로 닿는(gap pt 안) 획끼리 한 글자.

    가로로 쓴 글자든 세로로 쌓은 글자(AND 게이트)든 같은 규칙이다 — 글자 사이에는 틈이 있다.
    """
    segs_of = [p.segs for p in polys]
    bbs = [p.bbox for p in polys]
    n = len(polys)
    par = list(range(n))

    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i

    def touch(i, j):
        a, b = bbs[i], bbs[j]
        if a[0] > b[2] + gap or b[0] > a[2] + gap or a[1] > b[3] + gap or b[1] > a[3] + gap:
            return False
        for s in segs_of[i]:
            for t in segs_of[j]:
                if _seg_dist(s, t) <= gap:
                    return True
        return False
    order = sorted(range(n), key=lambda i: bbs[i][0])
    for ii, i in enumerate(order):
        for j in order[ii + 1:]:
            if bbs[j][0] > bbs[i][2] + gap:
                break
            if f(i) != f(j) and touch(i, j):
                par[f(j)] = f(i)
    # 상자가 겹치는 무리는 한 글자 (소문자 t 의 가로획처럼 닿지 않고 걸친 획)
    while True:
        boxes = defaultdict(lambda: [1e9, 1e9, -1e9, -1e9])
        for i in range(n):
            r = f(i)
            b = boxes[r]
            a = bbs[i]
            boxes[r] = [min(b[0], a[0]), min(b[1], a[1]), max(b[2], a[2]), max(b[3], a[3])]
        roots = list(boxes)
        merged = False
        for x in range(len(roots)):
            for y in range(x + 1, len(roots)):
                a, b = boxes[roots[x]], boxes[roots[y]]
                ow = min(a[2], b[2]) - max(a[0], b[0])
                oh = min(a[3], b[3]) - max(a[1], b[1])
                if ow > 0 and oh > 0 and ow * oh > 0.25 * min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])):
                    par[f(roots[y])] = f(roots[x])
                    merged = True
        if not merged:
            break
    grp = defaultdict(list)
    for i in range(n):
        grp[f(i)].extend(segs_of[i])
    out = []
    for segs in grp.values():
        bb = _bb(segs)
        out.append(Char(bb, segs, raster(segs, bb)))
    return out


def _seg_dist(s, t):
    # 끝점-선분 거리의 최솟값 (교차는 0)
    def pd(px, py, a):
        vx, vy = a.x1 - a.x0, a.y1 - a.y0
        L2 = vx * vx + vy * vy
        if L2 == 0:
            return ((px - a.x0) ** 2 + (py - a.y0) ** 2) ** 0.5
        u = max(0.0, min(1.0, ((px - a.x0) * vx + (py - a.y0) * vy) / L2))
        qx, qy = a.x0 + u * vx, a.y0 + u * vy
        return ((px - qx) ** 2 + (py - qy) ** 2) ** 0.5
    if _cross(s, t):
        return 0.0
    return min(pd(s.x0, s.y0, t), pd(s.x1, s.y1, t), pd(t.x0, t.y0, s), pd(t.x1, t.y1, s))


def _cross(s, t):
    def o(ax, ay, bx, by, cx, cy):
        return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    d1 = o(t.x0, t.y0, t.x1, t.y1, s.x0, s.y0)
    d2 = o(t.x0, t.y0, t.x1, t.y1, s.x1, s.y1)
    d3 = o(s.x0, s.y0, s.x1, s.y1, t.x0, t.y0)
    d4 = o(s.x0, s.y0, s.x1, s.y1, t.x1, t.y1)
    return d1 * d2 < 0 and d3 * d4 < 0


def lines(cs, vertical=False):
    """글자를 줄로 — 가운데 높이(세로쓰기면 가운데 x)가 글자 높이의 절반 안이면 한 줄."""
    key = (lambda c: c.cx) if vertical else (lambda c: c.cy)
    along = (lambda c: c.cy) if vertical else (lambda c: c.cx)
    size = (lambda c: max(c.w, c.h))
    rows = []
    for c in sorted(cs, key=key):
        for r in rows:
            if abs(key(r[0]) - key(c)) <= 0.5 * max(size(r[0]), size(c)):
                r.append(c)
                break
        else:
            rows.append([c])
    return [sorted(r, key=along) for r in rows]


# ------------------------------------------------------------------ 사전

class Dictionary:
    def __init__(self):
        self.ex = defaultdict(list)          # 글자 → [raster]
        self.source = defaultdict(set)       # 글자 → {"NO 열 p27", "도면 목록 p2 27행 제목"}
        self._arr = None

    def add(self, ch, r, src, cap=12):
        if len(self.ex[ch]) < cap:
            self.ex[ch].append(r)
            self._arr = None
        self.source[ch].add(src)

    def _build(self):
        labels, masks, dts, cnt = [], [], [], []
        for ch, rs in self.ex.items():
            for r in rs:
                if not r:
                    continue
                labels.append(ch)
                masks.append(_mask(r))
                dts.append(_dt(r))
                cnt.append(len(r))
        self._arr = (labels, np.array(masks), np.array(dts), np.array(cnt, dtype=np.float32))

    def scores(self, r):
        """글자마다 가장 잘 맞는 보기의 맞음 {글자: 0~1}."""
        if not r or not self.ex:
            return {}
        if self._arr is None:
            self._build()
            self._memo = {}
        hit = self._memo.get(r)
        if hit is not None:
            return hit
        labels, masks, dts, cnt = self._arr
        q, qd = _mask(r), _dt(r)
        m1 = (dts @ q) / len(r)
        m2 = (masks @ qd) / cnt
        sc = 1.0 / (1.0 + 0.5 * (m1 + m2))
        best = {}
        for ch, v in zip(labels, sc.tolist()):
            if v > best.get(ch, -1):
                best[ch] = v
        if len(self._memo) > 50000:
            self._memo.clear()
        self._memo[r] = best
        return best

    def classify(self, r):
        """(글자, 일치도, 2위와의 차).  사전이 비면 ('?', 0, 0)."""
        best = self.scores(r)
        if not best:
            return "?", 0.0, 0.0
        ranked = sorted(best.items(), key=lambda kv: -kv[1])
        top, s1 = ranked[0]
        s2 = ranked[1][1] if len(ranked) > 1 else 0.0
        return top, s1, s1 - s2

    def to_json(self):
        return {ch: {"n": len(v), "from": sorted(self.source[ch])[:6]} for ch, v in sorted(self.ex.items())}


SHEET_WORD = re.compile(r"^[A-Z]\d{3}[A-Z]?$")


def _title_words(page):
    """타이틀블록의 진짜 글자: (쪽 번호, 부제 낱말들).

    쪽 번호 = 종이 아래쪽의 `글자+숫자3` 낱말 (설계 S8 — 묶음 안 되풀이 꼴 L1D3).
    부제 = 쪽 번호 칸 높이 안 · 쪽 번호 왼쪽 · 도면번호(숫자-숫자 꼴) 오른쪽에 있는 줄 중 **가장 아래 줄**
    (부제는 큰 제목 밑에 인쇄된다).
    """
    words = page.get_text("words")
    W, H = page.rect.width, page.rect.height
    cand = [w for w in words if SHEET_WORD.match(w[4]) and w[1] > 0.85 * H]
    if not cand:
        return None, []
    sw = max(cand, key=lambda w: w[1])
    h = sw[3] - sw[1]
    left = W / 2
    for w in words:
        if re.search(r"\d+-\d+", w[4]) and w[1] > 0.85 * H and w[2] < sw[0]:
            left = max(left, w[2])
    pool = [w for w in words if w is not sw and w[0] >= left and w[2] <= sw[0]
            and sw[1] - 2 * h <= (w[1] + w[3]) / 2 <= sw[3] + 2 * h and not re.fullmatch(r"[\d.]+", w[4]) and len(w[4]) > 1]   # 한 글자 = 테두리 격자 표시
    if not pool:
        return sw[4], []
    lines_ = []
    for w in sorted(pool, key=lambda w: (w[1] + w[3]) / 2):
        cy = (w[1] + w[3]) / 2
        if lines_ and abs(lines_[-1][0] - cy) <= 0.5 * (w[3] - w[1]):
            lines_[-1][1].append(w)
        else:
            lines_.append([cy, [w]])
    last = sorted(lines_[-1][1], key=lambda w: w[0])
    return sw[4], [w[4] for w in last]


def learn(doc, sheets):
    """묶음에서 사전을 만든다.  sheets = {쪽(1부터): graph.Sheet} (Logic 표 시트만)."""
    D = Dictionary()
    # ① NO. 열: 왼쪽 표의 첫 열 — 표 행 안의 글자 무리 중 가장 왼쪽
    for pno, sh in sheets.items():
        lay = sh.layout
        if not lay:
            continue
        _learn_row_numbers(D, sh, pno)
    # ② 도면 목록
    _learn_drawing_list(D, doc)
    return D


def _row_number_cells(sh):
    """두 표의 NO. 열 칸 — 행 번호가 든 열은 표 머리 쪽 바깥 둘째 열이다 (FM | NO. · NO. | TO).

    구조로만 찾는다: 그 행들의 글자 수가 행 번호의 자릿수와 맞는 열을 고른다.
    """
    lay = sh.layout
    cols = sorted(lay.columns)
    LX0, _, LX1, _ = lay.logic
    left = [x for x in cols if x <= LX0 + 0.1]
    right = [x for x in cols if x >= LX1 - 0.1]
    out = []
    for side, cs, rows in (("L", left, lay.left_rows), ("R", right, lay.right_rows)):
        for i in range(len(cs) - 1):
            out.append((side, cs[i], cs[i + 1], rows))
    return out


def _learn_row_numbers(D, sh, pno):
    polys = sh.all_glyphs
    best = None
    for side, x0, x1, rows in _row_number_cells(sh):
        col = [p for p in polys if x0 < p.bbox[0] and p.bbox[2] < x1]
        if not col:
            continue
        hits = 0
        per_row = []
        for n, a, b in rows:
            ps = [p for p in col if a < (p.bbox[1] + p.bbox[3]) / 2 < b]
            cs = sorted(chars(ps), key=lambda c: c.cx)
            per_row.append((n, cs))
            if cs and len(cs) == len(str(n)):
                hits += 1
        if best is None or hits > best[0]:
            best = (hits, side, per_row)
        # 두 표 모두 배운다
        if hits >= 0.9 * len(rows):
            for n, cs in per_row:
                lab = str(n)
                if len(cs) == len(lab):
                    for ch, c in zip(lab, cs):
                        D.add(ch, c.raster, f"NO 열 p{pno}")


def _learn_drawing_list(D, doc):
    """도면 목록 장 = 표에 선 글자가 가득하고, 행 수가 PDF 장 수와 맞는 장 (G001)."""
    from . import geom
    titles = []
    for i in range(len(doc)):
        sw, sub = _title_words(doc[i])
        titles.append((sw, sub))
    for i in range(min(4, len(doc))):
        page = doc[i]
        pr = geom.read(page, i + 1)
        if len(pr.polys) < 500:
            continue
        cs = chars([p for p in pr.polys if p.size < 8])
        if len(cs) < 200:
            continue
        rows = lines(cs)
        # 세로 괘선으로 칸 나누기
        vs = sorted({round(s.x0, 1) for p in pr.polys for s in p.segs
                     if s.vert and abs(s.y1 - s.y0) > 0.3 * page.rect.height})
        if len(vs) < 4:
            continue
        table_rows = []
        for r in rows:
            cells = defaultdict(list)
            for c in r:
                k = sum(1 for v in vs if v < c.cx)
                cells[k].append(c)
            table_rows.append((r[0].cy, cells))
        # 표 하나 = 연속 세 칸 [NO][TITLE][PAGE]; 행 번호는 위→아래 순서, 왼쪽 표 먼저
        _pair_list_rows(D, table_rows, vs, titles, i + 1)


def _pair_list_rows(D, table_rows, vs, titles, pno):
    """목록 표의 [번호][제목][쪽] 세 칸을 PDF 장의 타이틀블록과 맞댄다.

    어느 칸 셋이 그 표인지, 몇 번째 줄이 1행인지는 **세 칸 글자 수가 모두 맞는 행이 가장 많은**
    조합으로 정한다 (머리글 줄 수 · 표 위치를 외우지 않는다).  다 맞는 행만 배운다.
    """
    def want(k):
        if not (1 <= k <= len(titles)):
            return None
        sw, sub = titles[k - 1]
        if not sw:
            return None
        return str(k), "".join(sub).replace(" ", ""), sw

    ks = sorted({k for _, cells in table_rows for k in cells})
    plans = []
    for a in ks:
        b, c = a + 1, a + 2
        seq = []
        for y, cells in sorted(table_rows, key=lambda t: t[0]):
            if cells.get(a) and cells.get(b):
                seq.append((sorted(cells.get(a, []), key=lambda ch: ch.cx),
                            sorted(cells.get(b, []), key=lambda ch: ch.cx),
                            sorted(cells.get(c, []), key=lambda ch: ch.cx)))
        if not seq:
            continue

        def fits(i, off, seq=seq):
            w = want(i + 1 + off)
            if w is None:
                return False
            g = seq[i]
            return len(g[0]) == len(w[0]) and len(g[1]) == len(w[1]) and len(g[2]) == len(w[2])
        best = max(range(-len(seq), len(titles)), key=lambda off: sum(fits(i, off) for i in range(len(seq))))
        n = sum(fits(i, best) for i in range(len(seq)))
        if n >= 3:
            plans.append((n, a, best, seq, fits))
    for n, a, best, seq, fits in plans:
        for i, g in enumerate(seq):
            if not fits(i, best):
                continue
            k = i + 1 + best
            for lab, got, what in zip(want(k), g, ("번호", "제목", "쪽 번호")):
                for ch, gl in zip(lab, got):
                    D.add(ch, gl.raster, f"도면 목록 p{pno} {k}행 {what}")


def read(D, cs, vertical=False):
    """글자들을 한 줄로 읽는다 → (글자열, [(글자, 일치도, 차)])."""
    out = []
    for c in sorted(cs, key=(lambda c: c.cy) if vertical else (lambda c: c.cx)):
        out.append(D.classify(c.raster))
    return "".join(ch for ch, _, _ in out), out
