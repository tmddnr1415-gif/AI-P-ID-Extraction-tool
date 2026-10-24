"""P&ID 도면 기하 → HMI 그래픽 재료 (hotfix113).

식별(행)과 **별개로** 그 장의 도면이 그린 것을 그래픽용으로만 읽는다 — 판정 0줄 · 엔진 import 0 · 분석 결과 · 지문에 닿지 않는다.
사용자 요구: *"P&ID 가 입력되고 계기가 식별되고 나면, 그 P&ID 이미지를 기준으로 예시(압축기 트레인 Overview)처럼
장비 · 계기를 그래픽으로"* — hotfix110 장면은 계기가 **탭한 런**만 그려 배관이 조각이고 장비는 이름 자리에 고정 크기로 섰다.

읽는 것 (전부 그 장의 PDF 에서 · 좌표는 표시 좌표 = 행 사각형과 같은 틀):

  · 배관  — 잉크로 그린 곧은 가로 · 세로 선.  짧은 토막(파선 · 쇄선 신호선 · 글자 획 · 밸브 몸체)은 버리고,
            같은 줄의 토막은 잇는다.  틈이 짧으면 그냥 · 길면 그 틈에 무언가(밸브 · 계기 뿌리)가 그려져 있을 때만.
            계기 버블 · 밸브 사각형에 끝이 닿는 선은 인출선이라 뺀다.  도면 영역(분석이 잰 `regions.drawing_area`) 밖과
            그 테두리 위 선은 뺀다.
  · 장비  — 배관으로 쓰지 않은 획(곧은 선 · 곡선)을 맞닿음으로 묶어, 버블보다 충분히 큰 무리.  이름은 그 무리 안
            (없으면 바로 위 · 아래)에 인쇄된 글줄 중 기기 명사가 든 것.  한 무리에 이름이 여럿이면(터빈 HP · IP · LP)
            이름 사이 가운데에서 가른다.  이름이 없으면 외곽선만 (지어내지 않는다).
  · 라벨  — `TO …` / `FROM …` 로 시작하는 글줄(오프페이지 커넥터) · `DN350` 꼴(배관 직경).

허용치는 전부 그 장 계기 버블 크기의 배수다 (§9 — 절대 pt 없음).
"""
from __future__ import annotations

import math
import re

VERSION = 2  # hotfix114: 회전 기기(펌프) — 옛 기억은 다시 읽는다

# 기기 명사 (scene.NOUN_SYM 의 낱말 + 범례 EQUIPMENT 에 흔한 것) — 이름을 고르는 데만 쓴다
NOUNS = ("COMPRESSOR", "PUMP", "TURBINE", "FAN", "BLOWER", "COOLER", "EXCHANGER", "HEATER", "CONDENSER",
         "ECONOMIZER", "EVAPORATOR", "SUPERHEATER", "TANK", "COLUMN", "TOWER", "DEAERATOR", "DRUM",
         "SEPARATOR", "VESSEL", "HRSG", "BOILER", "SILENCER", "FILTER", "STRAINER", "MOTOR", "GENERATOR",
         "EJECTOR", "SCRUBBER", "REACTOR", "KNOCKOUT", "DESUPERHEATER", "ATTEMPERATOR", "SKID", "PACKAGE")
CONN_RE = re.compile(r"^(TO|FROM)\s+\S", re.I)
DN_RE = re.compile(r"^(DN|NB)\s?\d{2,4}(X\d{2,4})?$", re.I)


# ---------------------------------------------------------------- 좌표
def _xf(m):
    a, b, c, d, e, f = m
    return lambda x, y: (a * x + c * y + e, b * x + d * y + f)


def _is_ink(col) -> bool:
    """검정 · 회색 계열 · 진한 색은 잉크.  붉은 개정 구름 · 연한 색은 아니다 (16회차 `_is_ink` 와 같은 생각)."""
    if col is None:
        return False
    r, g, b = col[:3]
    if r > 0.6 and g < 0.45 and b < 0.45:
        return False
    return max(r, g, b) < 0.75


def _bez(p0, p1, p2, p3, n=6):
    out = []
    for k in range(n + 1):
        t = k / n
        u = 1 - t
        out.append((u * u * u * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t * t * t * p3[0],
                    u * u * u * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t * t * t * p3[1]))
    return out


def _pt(p):
    return (p.x, p.y) if hasattr(p, "x") else (float(p[0]), float(p[1]))


def strokes(page) -> list:
    """그 장의 잉크 획 — [(x0, y0, x1, y1, 곡선?)] 표시 좌표.  곡선은 꺾은선 토막으로 · 닫힌 path 는 닫는 변까지."""
    T = _xf(tuple(page.rotation_matrix))
    get = getattr(page, "get_cdrawings", None) or page.get_drawings      # 날 튜플이 빠르다 (객체 30만 개를 안 만든다)
    out = []
    for d in get():
        if not _is_ink(d.get("color")):
            continue
        first = last = None
        for it in d.get("items") or []:
            k = it[0]
            if k == "l":
                a, b = T(*_pt(it[1])), T(*_pt(it[2]))
                out.append((a[0], a[1], b[0], b[1], 0))
                first = first or a
                last = b
            elif k == "re":
                r = it[1]
                x0, y0, x1, y1 = (r.x0, r.y0, r.x1, r.y1) if hasattr(r, "x0") else tuple(r)
                q = [T(x0, y0), T(x1, y0), T(x1, y1), T(x0, y1)]
                for i in range(4):
                    out.append((q[i][0], q[i][1], q[(i + 1) % 4][0], q[(i + 1) % 4][1], 0))
            elif k == "qu":
                qd = it[1]
                pts4 = [qd.ul, qd.ur, qd.lr, qd.ll] if hasattr(qd, "ul") else [qd[0], qd[1], qd[3], qd[2]]   # Quad 는 (ul, ur, ll, lr)
                q = [T(*_pt(p)) for p in pts4]
                for i in range(4):
                    out.append((q[i][0], q[i][1], q[(i + 1) % 4][0], q[(i + 1) % 4][1], 0))
            elif k == "c":
                pts = _bez(*[T(*_pt(p)) for p in it[1:5]])
                for i in range(len(pts) - 1):
                    out.append((pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], 1))
                first = first or pts[0]
                last = pts[-1]
        if d.get("closePath") and first and last and first != last:
            out.append((last[0], last[1], first[0], first[1], 0))
    return out


def words(page) -> list:
    """[(x0, y0, x1, y1, 글자)] 표시 좌표."""
    T = _xf(tuple(page.rotation_matrix))
    out = []
    for w in page.get_text("words"):
        a, b = T(w[0], w[1]), T(w[2], w[3])
        out.append((min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]), w[4]))
    return out


def _vertical(w) -> bool:
    return len(str(w[4])) >= 3 and (w[3] - w[1]) > 1.6 * (w[2] - w[0])     # 두 글자(`IP`)는 좁아서 세로로 보일 수 있다


def phrases(ws: list) -> list:
    """낱말 → 글줄 (같은 줄 · 글자 높이만큼 안 떨어짐).  세로로 쓴 낱말(세로 배관의 직경 글 · 돌린 장)은 세로로 잇는다.
    [(x0, y0, x1, y1, 글)]"""
    out = []
    for vert in (False, True):
        sel = [w for w in ws if _vertical(w) == vert]
        # 세로 글은 x · y 를 바꿔 같은 규칙으로 (글자 높이 = 낱말 폭)
        sw = [(w[1], w[0], w[3], w[2], w[4]) for w in sel] if vert else sel
        rows = sorted(sw, key=lambda w: ((w[1] + w[3]) / 2, w[0]))
        lines = []
        for w in rows:
            h = max(1.0, w[3] - w[1])
            cy = (w[1] + w[3]) / 2
            hit = None
            for ln in lines:
                if abs(ln["cy"] - cy) <= h * 0.45 and -h * 0.3 <= w[0] - ln["x1"] <= h * 1.2:
                    hit = ln
                    break
            if hit is None:
                lines.append({"cy": cy, "x0": w[0], "y0": w[1], "x1": w[2], "y1": w[3], "t": [w[4]]})
            else:
                hit["x1"] = max(hit["x1"], w[2]); hit["y0"] = min(hit["y0"], w[1]); hit["y1"] = max(hit["y1"], w[3])
                hit["t"].append(w[4])
        for ln in lines:
            r = (ln["y0"], ln["x0"], ln["y1"], ln["x1"]) if vert else (ln["x0"], ln["y0"], ln["x1"], ln["y1"])
            out.append((*r, " ".join(ln["t"])))
    return out


def _inside(px, py, r, pad=0.0):
    return r[0] - pad <= px <= r[2] + pad and r[1] - pad <= py <= r[3] + pad


def _merge(lines: list, gap_free: float, gap_max: float, bridge) -> list:
    """한 줄(같은 좌표) 위 토막 [(lo, hi)] → 이은 런.  `bridge(lo, hi)` 가 참이면 긴 틈도 잇는다."""
    lines = sorted(lines)
    out = []
    for lo, hi in lines:
        if out:
            g = lo - out[-1][1]
            if g <= gap_free or (g <= gap_max and bridge(out[-1][1], lo)):
                out[-1][1] = max(out[-1][1], hi)
                continue
        out.append([lo, hi])
    return out


def _bbox(segs):
    return [min(min(s[0], s[2]) for s in segs), min(min(s[1], s[3]) for s in segs),
            max(max(s[0], s[2]) for s in segs), max(max(s[1], s[3]) for s in segs)]


class _Raster:
    """도면 영역의 획을 칸(1pt 안팎)에 찍은 벽 지도 — 장비 이름 글자에서 시작해 막힌 데까지 채워 그 장비의 안쪽을 잰다.
    글자는 찍지 않는다(이름 글자가 씨앗 자리다).  벽은 한 칸 두껍게 — 외곽선의 미세한 틈으로 새지 않게."""

    def __init__(self, st: list, area: list, px: float):
        import numpy as np
        self.np, self.px, self.ox, self.oy = np, px, area[0], area[1]
        w = int(math.ceil((area[2] - area[0]) * px)) + 2
        h = int(math.ceil((area[3] - area[1]) * px)) + 2
        wall = np.zeros((h, w), dtype=bool)
        if st:
            a = np.asarray([s[:4] for s in st], dtype=float)
            L = np.hypot(a[:, 2] - a[:, 0], a[:, 3] - a[:, 1]) * px
            n = np.maximum(2, np.ceil(L * 2).astype(int) + 1)
            idx = np.repeat(np.arange(len(a)), n)
            t = np.concatenate([np.linspace(0, 1, k) for k in n])
            xs = ((a[idx, 0] + (a[idx, 2] - a[idx, 0]) * t) - self.ox) * px
            ys = ((a[idx, 1] + (a[idx, 3] - a[idx, 1]) * t) - self.oy) * px
            xi = np.clip(np.round(xs).astype(int), 0, w - 1)
            yi = np.clip(np.round(ys).astype(int), 0, h - 1)
            wall[yi, xi] = True
        thick = wall.copy()
        thick[1:, :] |= wall[:-1, :]; thick[:-1, :] |= wall[1:, :]
        thick[:, 1:] |= wall[:, :-1]; thick[:, :-1] |= wall[:, 1:]
        self.wall = thick

    def fill(self, x: float, y: float, limit: list):
        """(x, y) pt 에서 채움 — `limit` 창 [x0, y0, x1, y1] 을 넘으면(막히지 않음) None.  막혔으면 채운 칸의 bbox(pt)."""
        np, px = self.np, self.px
        H, W = self.wall.shape
        c0 = max(0, int((limit[0] - self.ox) * px)); c1 = min(W, int((limit[2] - self.ox) * px) + 1)
        r0 = max(0, int((limit[1] - self.oy) * px)); r1 = min(H, int((limit[3] - self.oy) * px) + 1)
        sx, sy = int(round((x - self.ox) * px)) - c0, int(round((y - self.oy) * px)) - r0
        free = ~self.wall[r0:r1, c0:c1]
        if not (0 <= sy < free.shape[0] and 0 <= sx < free.shape[1]) or not free[sy, sx]:
            return None
        reg = np.zeros_like(free)
        reg[sy, sx] = True
        R0, R1, C0, C1 = sy, sy + 1, sx, sx + 1          # 채운 곳 둘레 — 그 둘레만 불린다 (영역 크기에 비례)
        prev = 1
        Hh, Ww = free.shape
        for _ in range(2000):
            a0, a1, b0, b1 = max(0, R0 - 9), min(Hh, R1 + 9), max(0, C0 - 9), min(Ww, C1 + 9)
            sub, fr = reg[a0:a1, b0:b1], free[a0:a1, b0:b1]
            for _k in range(8):
                g = sub.copy()
                g[1:, :] |= sub[:-1, :]; g[:-1, :] |= sub[1:, :]
                g[:, 1:] |= sub[:, :-1]; g[:, :-1] |= sub[:, 1:]
                g &= fr
                sub = g
            reg[a0:a1, b0:b1] = sub
            rr, cc = np.nonzero(sub)
            if not len(rr):
                break
            R0, R1, C0, C1 = a0 + rr.min(), a0 + rr.max() + 1, b0 + cc.min(), b0 + cc.max() + 1
            if R0 == 0 or C0 == 0 or R1 == Hh or C1 == Ww:
                return None
            n = len(rr)
            if n == prev:
                break
            prev = n
        rows, cols = np.nonzero(reg)
        return [float((cols.min() + c0) / px + self.ox), float((rows.min() + r0) / px + self.oy),
                float((cols.max() + c0 + 1) / px + self.ox), float((rows.max() + r0 + 1) / px + self.oy), n / (px * px)]


def read_page(page, hints: dict) -> dict:
    """한 장 → {pipes, shapes, conns, sizes}.  `hints`: area(도면 영역) · bubble(계기 버블 짧은 변 중앙값) ·
    avoid(계기 버블 · 밸브 사각형 — 그 안의 획은 뺀다) · bubbles(계기 버블 — 거기 끝이 닿는 곧은 선은 인출선이라 뺀다)."""
    W, H = float(page.rect.width), float(page.rect.height)
    area = hints.get("area") or [0.02 * W, 0.02 * H, 0.98 * W, 0.98 * H]
    bub = float(hints.get("bubble") or 22.0)
    avoid = [list(r) for r in hints.get("avoid") or []]
    leads = [list(r) for r in hints.get("bubbles") or []]     # 계기 버블 — 거기 끝이 닿는 곧은 선은 인출선
    edge = max(1.0, bub * 0.1)
    st = [s for s in strokes(page)
          if _inside(s[0], s[1], area, -edge) and _inside(s[2], s[3], area, -edge)
          and (s[0] != s[2] or s[1] != s[3])]
    ws = [w for w in words(page) if _inside((w[0] + w[2]) / 2, (w[1] + w[3]) / 2, area)]
    phr = phrases(ws)
    # 1) 장비 — 기기 명사가 든 글줄에서 채워 막힌 영역 (그 글줄이 외곽선 안에 인쇄돼 있을 때)
    shapes = _shapes(st, area, bub, phr, avoid)
    shapes += _rotating(page, area, bub, phr, avoid, shapes, ws)
    # 2) 배관 — 장비 영역 밖의 곧은 가로 · 세로 선
    lmin = bub * 0.9                           # 이보다 짧은 곧은 토막은 배관이 아니다 (쇄선 긴 획 · 글자 획 · 밸브 몸체)
    ax = 0.25
    horiz, vert, small = {}, {}, []
    dh, dv = {}, {}                            # 짧은 곧은 토막 — 점선으로 그린 배관 후보
    cell = bub
    eq = [sh["rect"] for sh in shapes]
    for s in st:
        x0, y0, x1, y1, curve = s
        L = math.hypot(x1 - x0, y1 - y0)
        if any(_inside((x0 + x1) / 2, (y0 + y1) / 2, r, bub * 0.3) for r in eq):
            continue                                      # 장비 외곽선 · 안쪽 획 (채움은 안쪽이라 외곽선은 그 둘레에 선다)
        straight = not curve and (abs(y1 - y0) <= ax or abs(x1 - x0) <= ax)
        if any(_inside(x0, y0, r, 0.5) and _inside(x1, y1, r, 0.5) for r in avoid):
            continue                                      # 밸브 · 버블 안의 획
        if straight and L >= lmin and not any(_inside(x0, y0, r, 2) or _inside(x1, y1, r, 2) for r in leads):
            if abs(y1 - y0) <= ax:
                horiz.setdefault(round((y0 + y1) / 2 * 2) / 2, []).append((min(x0, x1), max(x0, x1)))
            else:
                vert.setdefault(round((x0 + x1) / 2 * 2) / 2, []).append((min(y0, y1), max(y0, y1)))
        else:
            if L < lmin * 2:
                small.append(s)
            if straight and bub * 0.08 <= L < lmin and not any(_inside((x0 + x1) / 2, (y0 + y1) / 2, r, 1) for r in avoid):
                if abs(y1 - y0) <= ax:
                    dh.setdefault(round((y0 + y1) / 2 * 2) / 2, []).append((min(x0, x1), max(x0, x1)))
                else:
                    dv.setdefault(round((x0 + x1) / 2 * 2) / 2, []).append((min(y0, y1), max(y0, y1)))
    sgrid = {}
    for s in small:
        for gx in range(int(min(s[0], s[2]) // cell), int(max(s[0], s[2]) // cell) + 1):
            for gy in range(int(min(s[1], s[3]) // cell), int(max(s[1], s[3]) // cell) + 1):
                sgrid.setdefault((gx, gy), []).append(s)

    def bridged(a, b, c, horizontal):
        """가로 줄 y=c 의 [a, b] 틈(세로면 x=c) 에 무언가 그려져 있는가."""
        lo, hi = (int(a // cell), int(b // cell))
        ci = int(c // cell)
        for k in range(lo, hi + 1):
            for d in (-1, 0, 1):
                for s in sgrid.get((k, ci + d) if horizontal else (ci + d, k), ()):
                    if horizontal and min(s[0], s[2]) < b and max(s[0], s[2]) > a \
                            and min(s[1], s[3]) - bub * 0.5 <= c <= max(s[1], s[3]) + bub * 0.5:
                        return True
                    if not horizontal and min(s[1], s[3]) < b and max(s[1], s[3]) > a \
                            and min(s[0], s[2]) - bub * 0.5 <= c <= max(s[0], s[2]) + bub * 0.5:
                        return True
        return False
    gap_free, gap_max = bub * 0.35, bub * 2.5
    pipes = []
    for y, segs in horiz.items():
        for lo, hi in _merge(segs, gap_free, gap_max, lambda a, b, y=y: bridged(a, b, y, True)):
            if hi - lo >= bub * 1.2:
                pipes.append([round(lo, 1), y, round(hi, 1), y])
    for x, segs in vert.items():
        for lo, hi in _merge(segs, gap_free, gap_max, lambda a, b, x=x: bridged(a, b, x, False)):
            if hi - lo >= bub * 1.2:
                pipes.append([x, round(lo, 1), x, round(hi, 1)])
    pipes = _twin(pipes, bub * 0.35)
    pipes = [p for p in pipes if not _on_border(p, area, edge * 3)
             and (p[2] - p[0]) < (area[2] - area[0]) * 0.9 and (p[3] - p[1]) < (area[3] - area[1]) * 0.9]
    conns, sizes = [], []
    for ph in phr:
        t = ph[4].strip()
        if CONN_RE.match(t) and len(t) <= 60:
            conns.append({"name": t.split(None, 1)[1], "dir": t.split()[0].upper(), "rect": [round(v, 1) for v in ph[:4]]})
        elif DN_RE.match(t.replace(" ", "")):
            sizes.append({"text": t.replace(" ", ""), "rect": [round(v, 1) for v in ph[:4]]})
    # 커넥터 상자 테두리는 배관이 아니다 — 글줄 둘레 위 · 아래 가로선 중 그 상자 폭 안에 갇힌 것
    def in_box(p):
        for c in conns:
            r = c["rect"]
            if (r[3] - r[1]) <= (r[2] - r[0]):         # 가로로 쓴 커넥터 — 위 · 아래 변
                if p[1] == p[3] and r[1] - bub * 1.2 <= p[1] <= r[3] + bub * 1.2 and p[0] >= r[0] - bub * 3 and p[2] <= r[2] + bub * 3:
                    return True
            elif p[0] == p[2] and r[0] - bub * 1.2 <= p[0] <= r[2] + bub * 1.2 and p[1] >= r[1] - bub * 3 and p[3] <= r[3] + bub * 3:
                return True                            # 세로로 쓴 커넥터 — 왼 · 오른 변
        return False
    pipes = [p for p in pipes if not in_box(p)]
    # 어디에도 안 닿는 짧은 선(공급 범위 표시 · 글자 밑줄 따위)은 배관이 아니다
    def touch_any(p, others):
        for q in others:
            if q is p:
                continue
            for x, y in ((p[0], p[1]), (p[2], p[3])):
                if min(q[0], q[2]) - bub * 0.5 <= x <= max(q[0], q[2]) + bub * 0.5 and min(q[1], q[3]) - bub * 0.5 <= y <= max(q[1], q[3]) + bub * 0.5:
                    return True
        return False
    pipes = [p for p in pipes if max(p[2] - p[0], p[3] - p[1]) >= bub * 3 or touch_any(p, pipes)
             or any(_inside(p[0], p[1], r, bub * 0.6) or _inside(p[2], p[3], r, bub * 0.6) for r in avoid + eq)]
    # 글 없는 커넥터 상자도 — 끝이 같은 두 가로선이 상자 높이(버블 0.4~1.3배)만큼 떨어져 있으면 상자의 위 · 아래 변이다
    drop = set()
    for k in (0, 1):                                   # 가로 상자 · 세로 상자
        same = [p for p in pipes if (p[1] == p[3]) == (k == 0) and max(p[2] - p[0], p[3] - p[1]) <= bub * 10]
        lo, hi, c = (0, 2, 1) if k == 0 else (1, 3, 0)
        for i, a in enumerate(same):
            for b in same[i + 1:]:
                if abs(a[lo] - b[lo]) <= 2 and abs(a[hi] - b[hi]) <= 2 and bub * 0.4 <= abs(a[c] - b[c]) <= bub * 1.3:
                    drop.add(tuple(a)); drop.add(tuple(b))
    pipes = [p for p in pipes if tuple(p) not in drop]
    # 점선으로 그린 배관 (협력사 범위 · 장래) — 고른 토막이 다섯 개 넘게 이어지고 한쪽 끝이 실선 배관 · 커넥터에 닿을 때만.
    # 계장 신호선 · 패키지 경계 쇄선도 같은 꼴이라, 닿는 데가 없으면 배관으로 보지 않는다.
    dashed = []
    for vert_, groups in ((False, dh), (True, dv)):
        for c, segs in groups.items():
            for lo, hi in _merge(segs, bub * 0.4, gap_max, lambda a, b, c=c, v=vert_: bridged(a, b, c, not v)):
                n = sum(1 for a, b in segs if a >= lo - 0.1 and b <= hi + 0.1)
                dashed.append((vert_, c, (lo, hi, n)))

    def touches(x, y, vert_):
        """점선 배관의 끝이 닿을 수 있는 것 — 커넥터 · 장비 외곽 · 같은 방향 실선 배관의 **끝**(이어 그린 연장).
        실선 배관 몸통에 T 로 닿기만 하는 점선은 구조물 · 패키지 경계일 수 있어 배관으로 보지 않는다."""
        if any(c["rect"][0] - bub * 4 <= x <= c["rect"][2] + bub * 4 and c["rect"][1] - bub <= y <= c["rect"][3] + bub for c in conns):
            return True
        if any(_inside(x, y, r, bub * 0.6) for r in eq):
            return True
        for q in pipes:
            if (q[0] == q[2]) != vert_:
                continue
            for ex, ey in ((q[0], q[1]), (q[2], q[3])):
                if abs(ex - x) <= bub * 0.6 and abs(ey - y) <= bub * 0.6:
                    return True
        return False
    for vert_, c, (lo, hi, n) in dashed:
        if n < 6 or hi - lo < bub * 3:
            continue
        a, b = ((c, lo), (c, hi)) if vert_ else ((lo, c), (hi, c))
        if not (touches(*a, vert_) or touches(*b, vert_)):
            continue
        q = [c, round(lo, 1), c, round(hi, 1)] if vert_ else [round(lo, 1), c, round(hi, 1), c]
        if in_box(q) or any(_inside((q[0] + q[2]) / 2, (q[1] + q[3]) / 2, r, 0.5) for r in eq):
            continue
        pipes.append(q + ["dashed"])
    return {"version": VERSION, "pipes": pipes, "shapes": shapes, "conns": conns, "sizes": sizes,
            "bubble": round(bub, 2), "area": [round(v, 1) for v in area]}


SHORT_RE = re.compile(r"^[A-Z0-9]$")          # 상자 안 한 글자 (A · B · 1) — 두 글자 이상은 계기 · 밸브 머리글자일 수 있다


def _region(ras, p, lim, bub):
    """글줄 p 자리 몇 곳에서 채워 막힌 영역의 합 (막힌 것이 없으면 None)."""
    cy = (p[1] + p[3]) / 2
    boxes = []
    for t in (0.5, 0.15, 0.85, 0.02, 0.98):
        f = ras.fill(p[0] + (p[2] - p[0]) * t, cy, lim)
        if f and f[4] >= (bub * 1.2) ** 2:
            boxes.append(f)
    if not boxes:
        return None
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]


def _shapes(st: list, area: list, bub: float, phr: list, avoid: list) -> list:
    """장비 외곽 — 글줄에서 채워 **막힌** 영역 = 그 장비의 안쪽 (외곽선이 그 글을 둘러쌌다).
      · 기기 명사가 든 글줄(`HP TURBINE` · `FUEL OIL STORAGE TANK A`) — 이름은 그 글 그대로.
      · 짧은 글(`A` · `B` · `1`)이 든 상자 — 이름은 그 글, 기기 명사는 가까이(버블 8개 안) 인쇄된 명사 글줄에서
        (`FEEDWATER PUMP … (A/B)` 상자 둘).  명사 글줄이 없으면 이름만 · 모양은 장면이 일반 상자로.
    안 막혔으면(글이 외곽선 밖에 인쇄됨) 장비 모양을 지어내지 않는다 — 장면이 이름 자리 규칙으로 돌아간다."""
    named = [p for p in label_blocks(phr) if _noun_of(p[4]) and not CONN_RE.match(p[4].strip())]
    shorts = [p for p in phr if SHORT_RE.match(p[4].strip()) and not any(_inside((p[0] + p[2]) / 2, (p[1] + p[3]) / 2, q, 1) for q in avoid)]
    if not named and not shorts:
        return []
    px = 1.0 if bub >= 15 else 2.0
    ras = _Raster(st, area, px)
    aw, ah = area[2] - area[0], area[3] - area[1]
    out = []

    def good(r):
        w, h = r[2] - r[0], r[3] - r[1]
        if max(w, h) < bub * 2.4:
            return False
        if min(w, h) <= bub * 1.4 and max(w, h) / max(1.0, min(w, h)) >= 2.5:
            return False                      # 납작한 띠 — 계기 · 태그 버블 안쪽이나 두 배관 사이 틈
        # 계기 버블 · 밸브 안쪽이면 장비가 아니다
        return not any(r[0] >= q[0] - 2 and r[2] <= q[2] + 2 and r[1] >= q[1] - 2 and r[3] <= q[3] + 2 for q in avoid)

    def segs_in(r):
        return [[round(v, 1) for v in s[:4]] for s in st if _inside(s[0], s[1], r, bub * 0.15) and _inside(s[2], s[3], r, bub * 0.15)]
    for p in named:
        cx, cy = (p[0] + p[2]) / 2, (p[1] + p[3]) / 2
        lim = [max(area[0], cx - aw * 0.25), max(area[1], cy - ah * 0.25), min(area[2], cx + aw * 0.25), min(area[3], cy + ah * 0.25)]
        r = _region(ras, p, lim, bub)
        if not r or not good(r):
            continue
        sg = segs_in(r)
        out.append({"rect": [round(v, 1) for v in r], "name": p[4], "noun": _noun_of(p[4]),
                    "label_rect": [round(v, 1) for v in p[:4]], "segs": sg[:4000], "n": len(sg)})
    for p in shorts:
        cx, cy = (p[0] + p[2]) / 2, (p[1] + p[3]) / 2
        lim = [max(area[0], cx - bub * 12), max(area[1], cy - bub * 12), min(area[2], cx + bub * 12), min(area[3], cy + bub * 12)]
        r = _region(ras, p, lim, bub)
        if not r or not good(r) or any(o["rect"] == [round(v, 1) for v in r] for o in out):
            continue
        # 같은 상자 안에 다른 글(태그 · 명사)이 있으면 그 글이 주인이다 — 짧은 글 상자는 비어 있는 상자만
        if any(_inside((q[0] + q[2]) / 2, (q[1] + q[3]) / 2, r) and q is not p for q in phr):
            continue
        cap = None
        for q in named:
            d = max(0.0, max(q[0] - r[2], r[0] - q[2])) + max(0.0, max(q[1] - r[3], r[1] - q[3]))
            if d <= bub * 8 and (cap is None or d < cap[0]):
                cap = (d, q)
        sg = segs_in(r)
        name = f"{cap[1][4]} ({p[4]})" if cap else p[4]
        out.append({"rect": [round(v, 1) for v in r], "name": name, "noun": _noun_of(cap[1][4]) if cap else "",
                    "label_rect": [round(v, 1) for v in p[:4]], "segs": sg[:4000], "n": len(sg), "token": p[4]})
    # 명사 글줄이 한쪽 상자에만 가까우면(`… PUMP (A/B)` 가 B 상자 밑에) 크기가 같은 형제 상자도 그 명사를 쓴다
    for o in out:
        if o.get("token") and not o["noun"]:
            w, h = o["rect"][2] - o["rect"][0], o["rect"][3] - o["rect"][1]
            sib = next((q for q in out if q.get("token") and q["noun"] and q is not o
                        and abs((q["rect"][2] - q["rect"][0]) - w) <= w * 0.1 and abs((q["rect"][3] - q["rect"][1]) - h) <= h * 0.1), None)
            if sib:
                base = sib["name"][: -len(f" ({sib['token']})")]
                o["name"], o["noun"] = f"{base} ({o['token']})", sib["noun"]
    # 같은 영역을 여러 이름이 가리키면 — 위아래로 붙은 글줄(두 줄 이름)은 잇고, 떨어진 이름은 가운데로 가른다
    merged = []
    for sh in out:
        twin = next((m for m in merged if m["rect"] == sh["rect"]), None)
        if twin is None:
            merged.append(dict(sh, names=[sh]))
        else:
            twin["names"].append(sh)
    final = []
    for m in merged:
        names = m.pop("names")
        if len(names) == 1:
            final.append(m)
            continue
        names.sort(key=lambda n: (n["label_rect"][1], n["label_rect"][0]))
        h = max(1.0, min(n["label_rect"][3] - n["label_rect"][1] for n in names))
        stacked = all(-h * 0.2 <= b["label_rect"][1] - a["label_rect"][3] <= h * 2.0
                      and min(a["label_rect"][2], b["label_rect"][2]) > max(a["label_rect"][0], b["label_rect"][0])
                      for a, b in zip(names, names[1:]))
        if stacked:
            text = " ".join(n["name"] for n in names)
            final.append(dict(m, name=text, noun=_noun_of(names[0]["name"]) or _noun_of(text),
                              label_rect=[min(n["label_rect"][0] for n in names), names[0]["label_rect"][1],
                                          max(n["label_rect"][2] for n in names), names[-1]["label_rect"][3]]))
            continue
        r = m["rect"]
        cs = [((n["label_rect"][0] + n["label_rect"][2]) / 2, (n["label_rect"][1] + n["label_rect"][3]) / 2, n) for n in names]
        horiz = (max(c[0] for c in cs) - min(c[0] for c in cs)) >= (max(c[1] for c in cs) - min(c[1] for c in cs))
        cs.sort(key=lambda c: c[0] if horiz else c[1])
        cuts = [r[0] if horiz else r[1]] + [((a[0] + b[0]) / 2 if horiz else (a[1] + b[1]) / 2) for a, b in zip(cs, cs[1:])] + [r[2] if horiz else r[3]]
        for k, c in enumerate(cs):
            sub = [cuts[k], r[1], cuts[k + 1], r[3]] if horiz else [r[0], cuts[k], r[2], cuts[k + 1]]
            n = c[2]
            final.append(dict(n, rect=[round(v, 1) for v in sub], split_of=r,
                              segs=[q for q in n["segs"] if _inside((q[0] + q[2]) / 2, (q[1] + q[3]) / 2, sub)]))
    return final


ROTATING_NOUNS = ("PUMP", "FAN", "BLOWER", "COMPRESSOR", "MOTOR", "TURBINE")


def round_bodies(page, area: list, bub: float, avoid: list) -> list:
    """곡선으로 그린 둥근 몸통(펌프 · 팬 · 압축기의 원) — 곡선이 둘 이상인 잉크 path 중 버블 0.7~5배 크기 · 납작하지 않은 것.
    겹치거나 맞닿은 path 는 한 몸통 (펌프 원 + 토출구 + 받침).  계기 버블 · 밸브 안 · 안에 글자가 든 원(`M` 전동기 표시)은 뺀다."""
    T = _xf(tuple(page.rotation_matrix))
    get = getattr(page, "get_cdrawings", None) or page.get_drawings
    parts = []
    for d in get():
        if not _is_ink(d.get("color")):
            continue
        items = d.get("items") or []
        nc = sum(1 for it in items if it[0] == "c")
        if nc < 2:
            continue
        r = d.get("rect")
        x0, y0, x1, y1 = (r.x0, r.y0, r.x1, r.y1) if hasattr(r, "x0") else tuple(r)
        a, b = T(x0, y0), T(x1, y1)
        bb = [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]
        w, h = bb[2] - bb[0], bb[3] - bb[1]
        if not (bub * 0.7 <= max(w, h) <= bub * 5) or max(w, h) > 1.7 * max(1.0, min(w, h)):
            continue
        if not _inside((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2, area):
            continue
        if any(bb[0] >= q[0] - 2 and bb[2] <= q[2] + 2 and bb[1] >= q[1] - 2 and bb[3] <= q[3] + 2 for q in avoid):
            continue
        parts.append({"bb": bb, "sig": (nc, sum(1 for it in items if it[0] == "l"))})
    bodies = []
    for pt in sorted(parts, key=lambda q: -(q["bb"][2] - q["bb"][0]) * (q["bb"][3] - q["bb"][1])):
        hit = next((b for b in bodies if b["bb"][0] - 1 <= pt["bb"][2] and pt["bb"][0] <= b["bb"][2] + 1
                    and b["bb"][1] - 1 <= pt["bb"][3] and pt["bb"][1] <= b["bb"][3] + 1), None)
        if hit is None:
            bodies.append({"bb": list(pt["bb"]), "sig": [pt["sig"]]})
        else:
            hit["bb"] = [min(hit["bb"][0], pt["bb"][0]), min(hit["bb"][1], pt["bb"][1]),
                         max(hit["bb"][2], pt["bb"][2]), max(hit["bb"][3], pt["bb"][3])]
            hit["sig"].append(pt["sig"])
    for b in bodies:
        b["sig"] = tuple(sorted(b["sig"]))
    return bodies


def label_blocks(phr: list) -> list:
    """위아래로 붙어 쓴 글줄을 한 이름표로 (`FUEL OIL / UNLOADING / PUMP A`) — 가운데가 겹치고 줄 사이가 글자 높이 1.2배 안
    (글줄 상자는 위아래 여백까지라 줄끼리 조금 겹칠 수 있다)."""
    lines = sorted([p for p in phr if p[3] - p[1] < (p[2] - p[0]) * 3], key=lambda p: (p[1], p[0]))
    upright = [p for p in phr if not (p[3] - p[1] < (p[2] - p[0]) * 3)]     # 세로 글은 묶지 않고 그대로
    blocks = []
    for p in lines:
        h = max(1.0, p[3] - p[1])
        cx = (p[0] + p[2]) / 2
        hit = next((b for b in blocks if -h * 0.35 <= p[1] - b["r"][3] <= h * 1.2 and abs(cx - (b["last"][0] + b["last"][2]) / 2) <= max(p[2] - p[0], b["last"][2] - b["last"][0]) / 2
                    and abs((p[3] - p[1]) - (b["last"][3] - b["last"][1])) <= h * 0.3), None)
        if hit is None:
            blocks.append({"r": list(p[:4]), "t": [p[4]], "last": p})
        else:
            hit["r"] = [min(hit["r"][0], p[0]), hit["r"][1], max(hit["r"][2], p[2]), p[3]]
            hit["t"].append(p[4]); hit["last"] = p
    return [(*b["r"], " ".join(b["t"])) for b in blocks] + upright


def _rotating(page, area: list, bub: float, phr: list, avoid: list, shapes: list, ws: list) -> list:
    """펌프 · 팬 · 압축기 — 이름이 몸통 **밖**(대개 바로 아래)에 인쇄돼 채움으로는 못 잡는 회전기기.
    이름표(위아래로 붙은 글줄 묶음)에 회전기기 명사가 있으면, 그 위(또는 아래) 몸통 높이 3배 안 · 가로로 겹치는 둥근 몸통 중
    가장 가까운 것.  같은 이름표가 둘 이상의 같은 몸통을 가리키는 그림(`CLEAN DRAIN PUMP (2X100%)` 아래 펌프 둘)은
    **path 구성까지 같은** 몸통이 버블 10개 안에 있을 때만 형제로 잇는다 — 지어내지 않는다."""
    bodies = round_bodies(page, area, bub, avoid)
    if not bodies:
        return []
    taken = [s["rect"] for s in shapes]
    bodies = [b for b in bodies if not any(_inside((b["bb"][0] + b["bb"][2]) / 2, (b["bb"][1] + b["bb"][3]) / 2, r, 1) for r in taken)]
    # 안에 글자가 든 원은 전동기 표시(`M`) · 계기 — 몸통이 아니다
    bodies = [b for b in bodies if not any(_inside((w[0] + w[2]) / 2, (w[1] + w[3]) / 2, b["bb"]) for w in ws)]
    used_names = {s["name"] for s in shapes}
    out, used = [], set()
    for blk in label_blocks(phr):
        text = blk[4]
        noun = next((n for n in ROTATING_NOUNS if re.search(r"\b" + n + r"S?\b", text.upper())), "")
        if not noun or CONN_RE.match(text.strip()) or text in used_names:
            continue
        best = None
        for k, b in enumerate(bodies):
            if k in used:
                continue
            bb = b["bb"]
            bw, bh = bb[2] - bb[0], bb[3] - bb[1]
            if bb[2] < blk[0] - bw or bb[0] > blk[2] + bw:
                continue
            below = blk[1] - bb[3]                 # 이름이 몸통 아래
            above = bb[1] - blk[3]                 # 이름이 몸통 위
            gap = min([g for g in (below, above) if -bh * 0.3 <= g <= bh * 3] or [None]) if any(
                -bh * 0.3 <= g <= bh * 3 for g in (below, above)) else None
            if gap is None:
                continue
            dx = abs((bb[0] + bb[2]) / 2 - (blk[0] + blk[2]) / 2)
            d = max(gap, 0) + dx * 0.5
            if best is None or d < best[0]:
                best = (d, k)
        if best is None:
            continue
        used.add(best[1])
        b = bodies[best[1]]
        out.append({"rect": [round(v, 1) for v in b["bb"]], "name": text, "noun": noun, "label_rect": [round(v, 1) for v in blk[:4]],
                    "segs": [], "n": 0, "by": "round_body", "_k": best[1]})
    # 형제 — 이름표가 다 제 몸통을 고른 **뒤에** 남은 몸통만 (그래야 `WATER PUMP B` 가 제 이름을 잃지 않는다).
    # path 구성 · 크기가 같은 몸통을 가장 가까운 무리부터 하나씩 잇는다 (무리 안 아무 몸통에서 버블 10개 안).
    groups = []
    for o in out:
        k = o.pop("_k")
        groups.append({"o": o, "sig": bodies[k]["sig"], "members": [bodies[k]["bb"]]})
    while True:
        best = None
        for k, s2 in enumerate(bodies):
            if k in used:
                continue
            w2, h2 = s2["bb"][2] - s2["bb"][0], s2["bb"][3] - s2["bb"][1]
            for gi, g in enumerate(groups):
                if s2["sig"] != g["sig"]:
                    continue
                m0 = g["members"][0]
                if abs((m0[2] - m0[0]) - w2) > w2 * 0.05 or abs((m0[3] - m0[1]) - h2) > h2 * 0.05:
                    continue
                d = min(max(abs(s2["bb"][0] - m[0]), abs(s2["bb"][1] - m[1])) for m in g["members"])
                if d <= bub * 10 and (best is None or d < best[0]):
                    best = (d, k, gi)
        if best is None:
            break
        _, k, gi = best
        used.add(k)
        g = groups[gi]
        g["members"].append(bodies[k]["bb"])
        out.append(dict(g["o"], rect=[round(v, 1) for v in bodies[k]["bb"]], sibling=True))
    return out


def _twin(pipes: list, tol: float) -> list:
    out = []
    used = [False] * len(pipes)
    for i, p in enumerate(pipes):
        if used[i]:
            continue
        hz = p[1] == p[3]
        for j in range(i + 1, len(pipes)):
            q = pipes[j]
            if used[j] or (q[1] == q[3]) != hz:
                continue
            if hz and 0 < abs(q[1] - p[1]) <= tol and min(p[2], q[2]) - max(p[0], q[0]) > 0.8 * min(p[2] - p[0], q[2] - q[0]):
                used[j] = True
                y = round((p[1] + q[1]) / 2, 1)
                p = [min(p[0], q[0]), y, max(p[2], q[2]), y]
            elif not hz and 0 < abs(q[0] - p[0]) <= tol and min(p[3], q[3]) - max(p[1], q[1]) > 0.8 * min(p[3] - p[1], q[3] - q[1]):
                used[j] = True
                x = round((p[0] + q[0]) / 2, 1)
                p = [x, min(p[1], q[1]), x, max(p[3], q[3])]
        out.append(p)
    return out


def _on_border(p, area, tol) -> bool:
    if p[1] == p[3]:
        return abs(p[1] - area[1]) <= tol or abs(p[1] - area[3]) <= tol
    return abs(p[0] - area[0]) <= tol or abs(p[0] - area[2]) <= tol


def _noun_of(text: str) -> str:
    """이름의 머리 명사 — `FOR` 앞에서 가장 뒤에 나오는 기기 명사 (`SLOP OIL TANK FOR … PUMP AREA` 는 TANK ·
    `COGENERATION FEEDWATER PUMP A MOTOR` 는 MOTOR)."""
    up = text.upper()
    head = re.split(r"\bFOR\b", up)[0] or up
    best = ("", -1)
    for part in (head, up):
        for n in NOUNS:
            for m in re.finditer(r"\b" + n + r"S?\b", part):
                if m.start() > best[1]:
                    best = (n, m.start())
        if best[0]:
            return best[0]
    return ""


def read_pdf(pdf_path: str, jobs: list) -> dict:
    """서버 밖 일꾼(`page_warm.call`)이 부르는 입구 — `jobs` = [(장 번호, hints)] → {장: 결과}."""
    import pymupdf
    out = {}
    with pymupdf.open(pdf_path) as doc:
        for page_no, hints in jobs:
            if 1 <= int(page_no) <= doc.page_count:
                out[int(page_no)] = read_page(doc[int(page_no) - 1], hints or {})
    return out
