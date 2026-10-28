"""L71 — 선 연결 퍼징: 축척 · 굵기 · 홉 모양 · 연결점 모양 · 짧은 토막을 무작위로 바꾼 합성 LOGIC 장을 만들어 돌린다.

정답은 만든 쪽이 안다 — 경로마다 왼쪽 행 하나에서 오른쪽 행(들)로 간다.  그 사이 다른 경로와 교차하는 자리는
홉(곡선 · 꺾은선 · 반원 둘) · 끊어 그린 틈 · 그냥 지남 중 하나로, 갈라지는 자리는 연결점(부채꼴 · 원 · 다각형) 또는
맨 T 로, 경로 몇은 오른쪽 끝 앞에 NOT 상자를 지난다.  일부러 홉을 연결점 · 상자 변 바로 옆(0.5~6pt)에 둔다.

본다: ① 경로마다 왼쪽 행 그물 = 그 경로의 오른쪽 행 그물(상자 앞까지) ② 서로 다른 경로는 다른 그물 ③ 선 끝 매달림 0 ·
입력 없는 게이트 0 ④ 블록은 NOT 상자뿐(배선이 만든 네모 · 홉 호를 블록으로 읽지 않음) ⑤ NOT 입력 = 상자 앞 그물 · 출력 = 뒤.

    PID_DATA_DIR=<빈 폴더> python3 spike/logic_wire_fuzz.py --runs 200 [--seed 1] [--keep 실패 PDF 폴더]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import tempfile
import traceback
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

K = (0, 0, 0)
# 기본 양식 (tests/test_logic_l23_generic 와 같은 표) — 전부 축척 s 를 곱해 그린다
BW, BH = 1191.0, 842.0
BP = 11.3
BTOP = 70.0
NROW = 50
BLCOLS = [30.0, 90.0, 110.0, 180.0, 320.0]
BRCOLS = [870.0, 1010.0, 1080.0, 1100.0, 1160.0]


class Sheet:
    def __init__(self, rng: random.Random, s: float):
        self.r = rng
        self.s = s
        self.lw = rng.choice([0.25, 0.5, 0.72, 1.0, 1.4, 2.0]) * s
        self.P = BP * s
        self.LX0 = BLCOLS[-1] * s
        self.LX1 = BRCOLS[0] * s
        self.top = BTOP * s
        self.doc = pymupdf.open()
        self.page = self.doc.new_page(width=BW * s, height=BH * s)
        self.notes = []

    def ry(self, n):
        return self.top + (n - 1) * self.P + self.P / 2

    def begin(self):
        self._sh = self.page.new_shape()

    def end(self):
        if getattr(self, "_sh", None) is not None:
            self._sh.finish(color=K, width=self.lw, closePath=False)
            self._sh.commit()
        self._sh = None

    def _shape(self):
        return getattr(self, "_sh", None)

    def line(self, *pts, width=None):
        if self._shape() is not None and width is None:
            for a, b in zip(pts, pts[1:]):
                self._sh.draw_line(pymupdf.Point(*a), pymupdf.Point(*b))
            return
        sh = self.page.new_shape()
        for a, b in zip(pts, pts[1:]):
            sh.draw_line(pymupdf.Point(*a), pymupdf.Point(*b))
        sh.finish(color=K, width=self.lw if width is None else width, closePath=False)
        sh.commit()

    def text(self, x, y, t, fs):
        self.page.insert_text((x * self.s, y * self.s), t, fontsize=fs * self.s)

    def table(self, sheet_no, rows_l, rows_r):
        s = self.s
        bottom = BTOP + NROW * BP
        for x in BLCOLS + BRCOLS:
            self.line((x * s, (BTOP - 2 * BP) * s), (x * s, bottom * s), width=0.72 * s)
        for k in range(NROW + 1):
            y = (BTOP + k * BP) * s
            self.line((BLCOLS[0] * s, y), (self.LX0, y), width=0.72 * s)
            self.line((self.LX1, y), (BRCOLS[-1] * s, y), width=0.72 * s)
        for x, t in ((40, "FROM"), (92, "NO."), (120, "TAG"), (140, "NO."), (220, "SERVICE"),
                     (900, "SERVICE"), (1020, "TAG"), (1040, "NO."), (1082, "NO."), (1120, "TO")):
            self.text(x, BTOP - 8, t, 7)
        for k in range(NROW):
            self.text(95, BTOP + k * BP + 8, str(k + 1), 5)
            self.text(1083, BTOP + k * BP + 8, str(NROW + k + 1), 5)
        for n, desc in rows_l.items():
            self.text(182, BTOP + (n - 1) * BP + BP / 2 + 2, desc, 5)
        for n, desc in rows_r.items():
            self.text(872, BTOP + (n - NROW - 1) * BP + BP / 2 + 2, desc, 5)
        self.text(950, 805, "1Z9Z-00GEN00-J09-0003", 8)
        self.text(1100, 790, "SHEET", 5)
        self.text(1098, 800, sheet_no, 7)

    # ---- 그림 요소
    def arc(self, a, b, axis, side, style):
        """a→b 를 건너는 반원 (axis 'v' 세로선 · 'h' 가로선 · side ±1 볼록한 쪽)."""
        r = abs((b[1] - a[1]) if axis == "v" else (b[0] - a[0])) / 2
        if style == "bezier":
            k = 1.9 * r * side
            c1 = (a[0] + k, a[1]) if axis == "v" else (a[0], a[1] + k)
            c2 = (b[0] + k, b[1]) if axis == "v" else (b[0], b[1] + k)
            if self._shape() is not None:
                self._sh.draw_bezier(pymupdf.Point(*a), pymupdf.Point(*c1), pymupdf.Point(*c2), pymupdf.Point(*b))
                return
            sh = self.page.new_shape()
            sh.draw_bezier(pymupdf.Point(*a), pymupdf.Point(*c1), pymupdf.Point(*c2), pymupdf.Point(*b))
            sh.finish(color=K, width=self.lw, closePath=False); sh.commit()
            return
        cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if style == "quarters":                      # 사분원 둘 (따로 그린 곡선)
            ux, uy = (b[0] - a[0]) / (2 * r), (b[1] - a[1]) / (2 * r)
            nx, ny = (side, 0.0) if axis == "v" else (0.0, side)
            m = (cx + r * nx, cy + r * ny)
            k = 0.5523 * r
            for p0, c1, c2, p3 in ((a, (a[0] + k * nx, a[1] + k * ny), (m[0] - k * ux, m[1] - k * uy), m),
                                   (m, (m[0] + k * ux, m[1] + k * uy), (b[0] + k * nx, b[1] + k * ny), b)):
                sh = self.page.new_shape()
                sh.draw_bezier(pymupdf.Point(*p0), pymupdf.Point(*c1), pymupdf.Point(*c2), pymupdf.Point(*p3))
                sh.finish(color=K, width=self.lw, closePath=False); sh.commit()
            return
        # polyline — 짧은 직선 n 개로 그린 반원
        n = self.r.choice([4, 6, 8, 12])
        pts = []
        for i in range(n + 1):
            t = math.pi * i / n
            if axis == "v":
                pts.append((cx + side * r * math.sin(t), a[1] + r - r * math.cos(t) if b[1] > a[1] else a[1] - r + r * math.cos(t)))
            else:
                pts.append((a[0] + r - r * math.cos(t) if b[0] > a[0] else a[0] - r + r * math.cos(t), cy + side * r * math.sin(t)))
        self.line(*pts)

    def dot(self, x, y, rad, style):
        if style == "fan":
            n = 12
            for k in range(n):
                a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
                sh = self.page.new_shape()
                sh.draw_polyline([pymupdf.Point(x, y), pymupdf.Point(x + rad * math.cos(a0), y + rad * math.sin(a0)),
                                  pymupdf.Point(x + rad * math.cos(a1), y + rad * math.sin(a1))])
                sh.finish(color=None, fill=K, width=0, closePath=True); sh.commit()
        elif style == "circle":
            sh = self.page.new_shape()
            sh.draw_circle(pymupdf.Point(x, y), rad)
            sh.finish(color=K, fill=K, width=0); sh.commit()
        else:                                        # 칠한 팔각형
            sh = self.page.new_shape()
            sh.draw_polyline([pymupdf.Point(x + rad * math.cos(2 * math.pi * k / 8), y + rad * math.sin(2 * math.pi * k / 8))
                              for k in range(8)])
            sh.finish(color=None, fill=K, width=0, closePath=True); sh.commit()

    def not_box(self, x, y, w, h):
        sh = self.page.new_shape()
        sh.draw_rect(pymupdf.Rect(x, y - h / 2, x + w, y + h / 2))
        sh.finish(color=K, width=self.lw); sh.commit()
        self.page.insert_text((x + 1.5 * self.s, y + 2 * self.s), "NOT", fontsize=5 * self.s)


class Net:
    """선분 장부 — 다른 그물끼리 나란히 겹치거나 끝이 남의 몸통에 닿지 않게 (실제 도면처럼)."""

    def __init__(self, P, s):
        self.P, self.s = P, s
        self.segs = []          # [net, (ax, c, a, b), cuts]

    def ok(self, net, g):
        ax, c, a, b = g
        lo, hi = sorted((a, b))
        m = 0.35 * self.P
        for n, (ax2, c2, a2, b2), _ in self.segs:
            if n == net:
                # 같은 그물이라도 한 직선 위에 겹쳐 그리지 않는다 (실제 도면에 없는 꼴)
                lo2, hi2 = sorted((a2, b2))
                if ax2 == ax and abs(c2 - c) < m and min(hi, hi2) - max(lo, lo2) > 1e-6:
                    return False
                continue
            lo2, hi2 = sorted((a2, b2))
            if ax2 == ax:
                if abs(c2 - c) < m and min(hi, hi2) - max(lo, lo2) > -m:
                    return False
                continue
            # 수직: 내 끝 (축 좌표 e) 이 남의 몸통 근처 · 남의 끝이 내 몸통 근처
            if lo2 - m <= c <= hi2 + m and any(abs(e - c2) < m for e in (a, b)):
                return False
            if lo - m <= c2 <= hi + m and any(abs(e - c) < m for e in (a2, b2)):
                return False
        return True

    def add(self, net, g, cuts=None):
        if not self.ok(net, g):
            return False
        self.segs.append([net, g, list(cuts or [])])
        return True


def build(seed: int, out: Path):
    rng = random.Random(seed)
    s = rng.choice([0.55, 0.7, 0.85, 1.0, 1.25, 1.6, 2.0])
    sh = Sheet(rng, s)
    P = sh.P
    L = Net(P, s)
    hop_r = max(rng.choice([0.5, 0.9, 1.2, 1.4, 1.8, 2.5, 3.2]) * s, 1.5 * sh.lw, 0.6)   # 홉은 선 굵기보다 크게 보인다
    gap = rng.choice([0.25, 0.5, 0.9, 1.5]) * P
    arc_style = rng.choice(["bezier", "bezier", "quarters", "polyline"])
    dot_style = rng.choice(["fan", "circle", "oct"])
    dot_r = rng.choice([1.0, 1.2, 1.56, 1.8]) * s
    free_r = list(range(52, 99))
    rng.shuffle(free_r)
    used_ry = set()

    def new_rrow():
        while free_r:
            r = free_r.pop()
            if r not in used_ry:
                used_ry.add(r)
                return r
        return None

    def half(y):                                   # 행 사이 높이로
        k = round((y - sh.top) / P - 1.0)
        return sh.top + (k + 1.0) * P

    npath = rng.randint(3, 7)
    xs = rng.sample([sh.LX0 + (6 + k) * P for k in range(int(0.62 * (sh.LX1 - sh.LX0) / P) - 6)], npath)
    xbr = sh.LX0 + 0.70 * (sh.LX1 - sh.LX0)
    box_x0 = sh.LX0 + 0.82 * (sh.LX1 - sh.LX0)
    paths = []
    dots = []
    joints = []
    boxes = []
    used_l = set()
    for i in range(npath):
        for _try in range(40):
            lr = rng.randint(2, 45)
            if lr in used_l:
                continue
            ya = sh.ry(lr)
            rb = new_rrow()
            if rb is None:
                break
            yb = sh.ry(rb - NROW)
            x = xs[i]
            if abs(yb - ya) < 2 * P:
                continue
            p = {"id": i, "lrow": lr, "rrows": [rb], "box": None, "v": ("v", x, ya, yb)}
            n0 = len(L.segs)
            ok = L.add(i, ("h", ya, sh.LX0, x)) and L.add(i, p["v"])
            box = None
            if ok and rng.random() < 0.4:
                bw = rng.choice([14.0, 16.0, 20.0]) * s
                bx = box_x0 + rng.uniform(0, 2 * P)
                box = (bx, yb, bw, 9.0 * s)
                ok = L.add(i, ("h", yb, x, bx)) and L.add(1000 + i, ("h", yb, bx + bw, sh.LX1))
            elif ok:
                ok = L.add(i, ("h", yb, x, sh.LX1))
            if not ok:
                del L.segs[n0:]
                continue
            used_l.add(lr)
            p["box"] = box
            if box:
                boxes.append(box)
            paths.append(p)
            break

    def route_out(net, x0, y0, xv):
        """(x0,y0) 에서 가로로 xv 까지 · 세로로 빈 행까지 · 가로로 LX1 — 새 오른쪽 행."""
        for _ in range(8):
            r = new_rrow()
            if r is None:
                return None
            yc = sh.ry(r - NROW)
            g1 = ("h", y0, x0, xv)
            g2 = ("v", xv, y0, yc)
            g3 = ("h", yc, xv, sh.LX1)
            if any(abs(yc - bx[1]) < P and xv < bx[0] + bx[2] for bx in boxes):
                continue
            # 세로선이 상자 변을 따라 달리지 않게 (상자 둘레 한 행 안에 세로선을 두지 않는다)
            if any(bx[0] - P <= xv <= bx[0] + bx[2] + P and min(y0, yc) - P <= bx[1] <= max(y0, yc) + P for bx in boxes):
                continue
            n0 = len(L.segs)
            if L.add(net, g1) and L.add(net, g2) and L.add(net, g3):
                return r
            del L.segs[n0:]
        return None

    # 갈래 — 세로선 위 행 사이 높이에서 오른쪽 새 행으로 (연결점)
    for p in paths:
        if rng.random() < 0.5:
            _, x, ya, yb = p["v"]
            lo, hi = sorted((ya, yb))
            if hi - lo < 4 * P:
                continue
            yd = half(rng.uniform(lo + 1.5 * P, hi - 1.5 * P))
            xb = xbr + round(rng.uniform(-2, 2)) * P + 0.5 * P
            r = route_out(p["id"], x, yd, xb)
            if r:
                p["rrows"].append(r)
                plain = rng.random() < 0.12
                if not plain:
                    dots.append((x, yd))
                joints.append((x, yd))
                p["branch"] = (x, yd)
    near = 0
    # 일부러 ① 상자 변 바로 앞의 홉 (가로선이 홉으로 건너고 짧은 토막 뒤 상자) — 다른 경로의 세로선
    for p in paths:
        if not p["box"] or rng.random() > 0.75:
            continue
        bx, yb, bw, bh = p["box"]
        d = rng.choice([0.0, rng.uniform(0.3, 6.0)]) * s
        xq = bx - d - hop_r
        q = rng.choice([o for o in paths if o is not p])
        _, qx, qa, qb = q["v"]
        lo, hi = sorted((qa, qb))
        yj = half(rng.uniform(lo + P, hi - P)) if hi - lo > 2.5 * P else None
        if yj is None:
            continue
        n0 = len(L.segs)
        r = new_rrow()
        if r is None:
            continue
        yc = sh.ry(r - NROW)
        if abs(yc - yb) < 2 * P:
            continue
        if any(ob is not p["box"] and ob[0] - P <= xq <= ob[0] + ob[2] + P and min(yj, yc) - P <= ob[1] <= max(yj, yc) + P
               for ob in boxes):
            continue                                # 다른 상자의 변을 따라 달리지 않게
        ok = (L.add(q["id"], ("h", yj, qx, xq)) and L.add(q["id"], ("v", xq, yj, yc)) and
              L.add(q["id"], ("h", yc, xq, sh.LX1)))
        lo2, hi2 = sorted((yj, yc))
        if not ok or not (lo2 < yb < hi2):
            del L.segs[n0:]
            continue
        for g in L.segs:                            # p 의 상자 앞 가로선에 홉
            if g[0] == p["id"] and g[1][0] == "h" and abs(g[1][1] - yb) < 1e-6:
                g[2].append(("hop", xq, hop_r, "forced"))
        q["rrows"].append(r)
        dots.append((qx, yj))
        near += 1
    # 일부러 ② 연결점 바로 옆의 홉 — 다른 경로의 가로선이 지나가고 세로선이 홉으로 건넌다
    for p in paths:
        if "branch" not in p or rng.random() > 0.7:
            continue
        x, yd = p["branch"]
        d = rng.choice([0.0, rng.uniform(0.3, 6.0)]) * s
        yh = yd + rng.choice([-1, 1]) * (d + hop_r + dot_r)
        q = rng.choice([o for o in paths if o is not p])
        _, qx, qa, qb = q["v"]
        lo, hi = sorted((qa, qb))
        if not (lo + P < yh < hi - P) or qx > x:
            continue
        xv = x + 2.5 * P
        n0 = len(L.segs)
        r = route_out(q["id"], qx, yh, xv)
        if not r:
            del L.segs[n0:]
            continue
        hit = False
        for g in L.segs:
            if g[0] == p["id"] and g[1][0] == "v" and abs(g[1][1] - x) < 1e-6:
                lo3, hi3 = sorted((g[1][2], g[1][3]))
                if lo3 < yh < hi3:
                    g[2].append(("hop", yh, hop_r, "forced"))
                    hit = True
        if not hit:
            del L.segs[n0:]
            continue
        q["rrows"].append(r)
        dots.append((qx, yh))
        near += 1
    # ③ 홉 바로 뒤 꺾임 (연결점 없이) — 다른 경로의 세로선을 가로로 홉으로 건넌 뒤 0.36P 쯤에서 아래/위로 꺾는다
    for p in paths:
        if rng.random() > 0.5:
            continue
        _, px, pa, pb = p["v"]
        q = rng.choice([o for o in paths if o is not p])
        _, qx, qa, qb = q["v"]
        if qx >= px:
            continue
        lo, hi = sorted((pa, pb))
        lo2, hi2 = sorted((qa, qb))
        cand = [y for y in (half(v) for v in (lo + 1.5 * P, (lo + hi) / 2, hi - 1.5 * P)) if lo2 + P < y < hi2 - P and lo + P < y < hi - P]
        if not cand:
            continue
        yj = rng.choice(cand)
        xc = px + hop_r + 0.36 * P + rng.uniform(0, 0.1 * P)
        r = new_rrow()
        if r is None:
            continue
        yc = sh.ry(r - NROW)
        if any(bx[0] - P <= xc <= bx[0] + bx[2] + P and min(yj, yc) - P <= bx[1] <= max(yj, yc) + P for bx in boxes):
            continue
        n0 = len(L.segs)
        if (L.add(q["id"], ("h", yj, qx, xc), [("hop", px, hop_r, "forced")]) and L.add(q["id"], ("v", xc, yj, yc))
                and L.add(q["id"], ("h", yc, xc, sh.LX1))):
            q["rrows"].append(r)
            dots.append((qx, yj))
            near += 1
        else:
            del L.segs[n0:]
    # 교차 — 강제한 자리 밖은 무작위 스타일 (끝 · 꺾임 · 연결점 근처는 그냥 지남)
    def near_end(g, c, m):
        return abs(g[2] - c) < m or abs(g[3] - c) < m

    xat = {}                                       # 선분마다 그것을 가로지르는 남의 선 자리
    for a in L.segs:
        for b in L.segs:
            if a[1][0] == b[1][0] or a is b:      # 같은 그물의 갈래도 센다 (틈 끝이 갈래 몸통 옆에 서면 T 로 읽힌다)
                continue
            v, h = (a, b) if a[1][0] == "v" else (b, a)
            x, y = v[1][1], h[1][1]
            lo, hi = sorted((v[1][2], v[1][3]))
            lo2, hi2 = sorted((h[1][2], h[1][3]))
            if lo - P < y < hi + P and lo2 - P < x < hi2 + P:
                xat.setdefault(id(a), []).append(y if a is v else x)
    crowded = lambda seg, c, rr: any(abs(o - c) > 1e-6 and abs(o - c) < rr + 0.3 * P for o in xat.get(id(seg), []))
    crossings = 0
    for a in L.segs:
        for b in L.segs:
            if a[1][0] != "v" or b[1][0] != "h" or (a[0] % 1000) == (b[0] % 1000):
                continue
            x, y = a[1][1], b[1][1]
            lo, hi = sorted((a[1][2], a[1][3]))
            lo2, hi2 = sorted((b[1][2], b[1][3]))
            if not (lo < y < hi and lo2 < x < hi2):
                continue
            crossings += 1
            if any(abs(c[1] - y) < 1e-6 for c in a[2]) or any(abs(c[1] - x) < 1e-6 for c in b[2]):
                continue
            m = hop_r + 0.4 * P
            busy = lambda cuts, c, rr: any(abs(cc - c) < rr + r0 + 0.3 * P for _, cc, r0, _ in cuts)
            st = rng.choice(["hop_v", "hop_v", "hop_h", "gap_v", "gap_h", "plain"])
            if st.endswith("_v") and (near_end(a[1], y, m + gap) or any(abs(dy - y) < m + gap and abs(dx - x) < 1e-6 for dx, dy in dots + joints)):
                st = "plain"
            if st.endswith("_h") and (near_end(b[1], x, m + gap) or any(abs(dx - x) < m + gap and abs(dy - y) < 1e-6 for dx, dy in dots + joints)
                                      or any(abs(y - bx[1]) < 1e-6 and x > bx[0] - m - gap for bx in boxes)):
                st = "plain"
            rr_ = gap / 2 if st.startswith("gap") else hop_r
            if st.endswith("_v") and crowded(a, y, rr_):
                st = "plain"
            if st.endswith("_h") and crowded(b, x, rr_):
                st = "plain"
            if st.endswith("_v") and busy(a[2], y, gap / 2 if st.startswith("gap") else hop_r):
                st = "plain"
            if st.endswith("_h") and busy(b[2], x, gap / 2 if st.startswith("gap") else hop_r):
                st = "plain"
            if st == "hop_v":
                a[2].append(("hop", y, hop_r, ""))
            elif st == "hop_h":
                b[2].append(("hop", x, hop_r, ""))
            elif st == "gap_v":
                a[2].append(("gap", y, gap / 2, ""))
            elif st == "gap_h":
                b[2].append(("gap", x, gap / 2, ""))
    merge = rng.random() < 0.4                     # 한 선분(조각 · 홉)을 한 path 로
    # 그리기
    for net, g, cuts in L.segs:
        if merge:
            sh.begin()
        ax, c0, a0, b0 = g
        sgn = 1 if b0 > a0 else -1
        pos = [a0]
        cs = sorted(cuts, key=lambda t: t[1] * sgn)
        for kind, c, r, _ in cs:
            pos += [c - r * sgn, c + r * sgn]
        pos.append(b0)
        for i in range(0, len(pos), 2):
            u, v = pos[i], pos[i + 1]
            if (v - u) * sgn > 1e-6:
                sh.line((c0, u), (c0, v)) if ax == "v" else sh.line((u, c0), (v, c0))
        for kind, c, r, _ in cs:
            if kind != "hop":
                continue
            if ax == "v":
                sh.arc((c0, c - r * sgn), (c0, c + r * sgn), "v", rng.choice([1, -1]), arc_style)
            else:
                sh.arc((c - r * sgn, c0), (c + r * sgn, c0), "h", -1, arc_style)
        if merge:
            sh.end()
    for bx in boxes:
        sh.not_box(*bx)
    for d in dots:
        sh.dot(*d, dot_r, dot_style)
    rows_l = {p["lrow"]: f"SIG {p['id']}" for p in paths}
    rows_r = {r: f"OUT {p['id']}" for p in paths for r in p["rrows"]}
    sh.table("FZ_G-%03d" % (seed % 1000), rows_l, rows_r)
    pdf = out / f"fz{seed}.pdf"
    rot = rng.choice([0, 0, 0, 90, 180, 270])
    if rot:
        doc = pymupdf.open()
        w, h = sh.page.rect.width, sh.page.rect.height
        pg = doc.new_page(width=h, height=w) if rot in (90, 270) else doc.new_page(width=w, height=h)
        pg.show_pdf_page(pg.rect, sh.doc, 0, rotate=rot)
        pg.set_rotation(rot)
        doc.save(pdf)
    else:
        sh.doc.save(pdf)
    meta = {"seed": seed, "scale": s, "rot": rot, "merge": merge, "lw": round(sh.lw, 2), "hop_r": round(hop_r, 2), "gap": round(gap, 2), "arc": arc_style,
            "dot": dot_style, "crossings": crossings, "near": near, "paths": [
                {"id": p["id"], "lrow": p["lrow"], "rrows": p["rrows"], "box": bool(p["box"])} for p in paths]}
    return pdf, meta


def check(pdf: Path, meta: dict):
    from app.logic import analyse
    res = analyse.analyse(str(pdf))
    sheets = [s for s in res["sheets"] if s.get("rows")]
    if not sheets:
        return ["시트 없음"]
    s = sheets[0]
    errs = []
    net = {(r["side"], r["n"]): r.get("net") for r in s["rows"]}
    seen = {}
    for p in meta["paths"]:
        a = net.get(("L", p["lrow"]))
        if a is None:
            errs.append(f"경로{p['id']} 왼쪽 {p['lrow']}행 그물 없음")
            continue
        targets = p["rrows"] if not p["box"] else p["rrows"][1:]
        for r in targets:
            b = net.get(("R", r))
            if b != a:
                errs.append(f"경로{p['id']} L{p['lrow']}({a}) ≠ R{r}({b})")
        if a in seen:
            errs.append(f"경로{p['id']} 와 경로{seen[a]} 가 한 그물 {a}")
        seen[a] = p["id"]
    codes = [f["code"] for f in s.get("findings", [])]
    for c in ("C1_DANGLING", "C3_GATE_NO_INPUT", "C3_BLOCK_UNCONNECTED", "BLOCK_UNKNOWN"):
        n = codes.count(c)
        if n:
            errs.append(f"{c} {n}")
    nbox = sum(1 for p in meta["paths"] if p["box"])
    blocks = s.get("blocks", {})
    nots = [b for b in blocks.values() if b.get("logic") == "not"]
    others = [b for b in blocks.values() if b.get("logic") != "not"]
    if len(nots) != nbox:
        errs.append(f"NOT {len(nots)} ≠ {nbox}")
    if others:
        errs.append(f"다른 블록 {len(others)}: " + ",".join(f"{b.get('func')}{[round(v) for v in b['bbox']]}" for b in others[:4]))
    if nbox and len(nots) == nbox:
        from app.logic import sim
        ins, outs, *_ = sim._index(s)
        for p in meta["paths"]:
            if not p["box"]:
                continue
            a = net.get(("L", p["lrow"]))
            b = net.get(("R", p["rrows"][0]))
            ok = any({n for n, _, _ in ins.get(k, [])} == {a} and b in {n for n, _, _ in outs.get(k, [])}
                     for k, bl in blocks.items() if bl.get("logic") == "not")
            if not ok:
                errs.append(f"경로{p['id']} NOT 입력/출력이 L{p['lrow']}→R{p['rrows'][0]} 와 다름")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=50)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--keep", default="")
    ap.add_argument("--only", type=int, nargs="*")
    a = ap.parse_args()
    keep = Path(a.keep) if a.keep else None
    if keep:
        keep.mkdir(parents=True, exist_ok=True)
    seeds = a.only or list(range(a.seed, a.seed + a.runs))
    fails = 0
    tally = {}
    with tempfile.TemporaryDirectory() as td:
        for sd in seeds:
            out = keep or Path(td)
            try:
                pdf, meta = build(sd, out)
                errs = check(pdf, meta)
            except Exception:
                errs = ["예외 " + traceback.format_exc(limit=3).replace("\n", " | ")]
                meta = {"seed": sd}
            if errs:
                fails += 1
                for e in errs:
                    k = e.split(" ")[0] if e.startswith(("C", "NOT", "다른", "예외")) else "그물"
                    tally[k] = tally.get(k, 0) + 1
                print(json.dumps({k: meta.get(k) for k in ("seed", "scale", "rot", "merge", "lw", "hop_r", "arc", "dot", "crossings", "near")},
                                 ensure_ascii=False), "→", "; ".join(errs[:6]), flush=True)
            elif keep:
                (out / f"fz{sd}.pdf").unlink(missing_ok=True)
    print(f"\n{len(seeds)}장 중 실패 {fails} · {tally}")


if __name__ == "__main__":
    main()
