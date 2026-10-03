"""배관 라인 번호 라벨 — 도면이 배관 위에 깃발처럼 세운 글자를 읽는다 (hotfix36).

무엇을 읽는가 (QFE p46 · p10 실측 · `out/hotfix36/p46_label_zoom.png`)
    ┌────────┐
    │12LBB50 │   ① 닫힌 작은 사각형 안의 **코드 한 줄** (계통 코드)
    │BR010         ② 그 사각형의 **아래**(글자 방향의 수직 아래쪽)에 붙은 코드 한 줄
    ──┴────────── ③ 그 아래 **글자 방향과 평행한 배관 런** — 사각형의 깃대가 닿는 선
      DN800H LBB1 ④ 런 건너편의 글줄 (관경·배관 등급 — 뜻은 읽지 않고 그대로 담는다)
    세로 배관에서는 같은 깃발이 90° 돌아 있다 — 글자 방향(`dir`)을 따라가므로 같은 규칙이다.

왜 이렇게 읽는가
    · `BR`·`AA` 같은 글자 뜻을 코드에 적지 않는다 (§9).  라인 라벨인지는 **사각형 +
      깃대 + 배관 런**의 관계가 말한다 — 같은 모양의 코드가 밸브 옆에도(태그) 버블
      안에도(계기) 인쇄되지만 그것들은 사각형 안에 있지 않다.
    · 글자는 조각으로 나뉘어 인쇄된다 (`12`·`LBB`·`50`).  같은 글줄에서 **글자 높이의
      0.15배 안**의 틈은 조각이고 그보다 넓으면 낱말 사이다 — QFE p46 실측: 조각 틈
      ≤ 0.09h · 낱말 사이 ≥ 0.24h, 그 사이가 비어 있다 (`spike/line_label_probe.py`).
    · 모든 허용치는 **그 라벨 자신의 글자 높이** 배율이다 — 절대 pt 없음 (§9 6).
    · 어느 모양이 라인 번호인지도 도면이 말한다 — 같은 모양(글자·숫자 달리기)의
      깃발이 **두 장 이상**에서 되풀이될 때만 받는다 (`tags.assign` 과 같은 규율).

읽기만 한다 — 행에 붙이는 것은 `pipeline` 이고, 지문 밖이다 (`tag_no` 와 같은 자리).
"""
from __future__ import annotations

import collections
import re
from dataclasses import dataclass, field

import pymupdf

import legend_rules
import tags as tagsys

FRAG_GAP = 0.15        # 조각 틈 상한 (글자 높이 배율) — QFE p46 빈 띠 0.09 ↔ 0.24 의 안
BELOW_GAP = 1.2        # 두 번째 줄이 사각형 아래 붙어 있다고 보는 거리 (글자 높이 배율)
RUN_REACH = 3.0        # 깃대가 닿는 런까지의 거리 상한 (글자 높이 배율 — 사각형 + 한 줄 + 틈)
SPEC_REACH = 2.5       # 런 건너편 글줄까지 (글자 높이 배율)


@dataclass
class Frag:
    rect: pymupdf.Rect
    text: str
    dir: tuple          # (1,0) 가로 · (0,-1) 위로 읽는 세로 · (0,1) · (-1,0)

    @property
    def h(self) -> float:
        return self.rect.height if self.dir[0] else self.rect.width


@dataclass
class LineLabel:
    text: str                 # "12LBB50 BR010" — 사각형 안 + 아래 줄
    box: pymupdf.Rect         # 닫힌 사각형
    rect: pymupdf.Rect        # 두 줄을 합친 사각형
    dir: tuple
    h: float
    run: tuple | None = None  # ('H', y, x0, x1) — 깃대가 닿은 배관 런
    spec: str = ""            # 런 건너편 글줄 (관경·보온·설계 코드), 글자 그대로
    parts: tuple = ()
    pole: bool = False        # 깃대가 런까지 그려져 있어 그것으로 런을 정했는가

    @property
    def line_no(self) -> str:
        """사용자 정의 — 라인 번호는 사각형 안의 코드다 (`12LBB50`).  둘째 줄은 배관 번호."""
        return self.parts[0] if self.parts else self.text.split(" ")[0]

    @property
    def pipe_no(self) -> str:
        return self.parts[1] if len(self.parts) > 1 else ""

    def shape(self) -> str:
        return tagsys.shape(self.text.replace(" ", ""))


def _lines(page, m) -> list[Frag]:
    """`get_text("dict")` 의 줄 — 표시 좌표로.  SHX 주석은 여기 없다 (한계 · UAD)."""
    out = []
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", ()):
            text = "".join(s["text"] for s in ln["spans"]).strip()
            if not text:
                continue
            d = pymupdf.Point(*ln["dir"]) * pymupdf.Matrix(m.a, m.b, m.c, m.d, 0, 0)
            dx, dy = (round(d.x), round(d.y))
            out.append(Frag(pymupdf.Rect(ln["bbox"]) * m, text, (dx, dy)))
    return out


def _along(f: Frag, r: pymupdf.Rect) -> tuple:
    """글자 방향을 따라 (시작, 끝) — 읽는 순서대로."""
    dx, dy = f.dir
    if dx == 1:
        return r.x0, r.x1
    if dx == -1:
        return -r.x1, -r.x0
    if dy == -1:
        return -r.y1, -r.y0
    return r.y0, r.y1


def join_fragments(frags: list[Frag]) -> list[Frag]:
    """같은 글줄 · 같은 방향 · 틈 ≤ FRAG_GAP×높이 인 조각을 읽는 순서로 잇는다.

    글줄은 먼저 **가로지르는 좌표**(가로 글자면 y)로 묶는다 — `12`(y0 391.1)·`LBB`(391.0)
    처럼 0.1pt 가 갈리는 조각을 좌표로 정렬하면 순서가 뒤집혀 안 이어진다 (QFE p46 실측).
    """
    out: list[Frag] = []
    by_dir = collections.defaultdict(list)
    for f in frags:
        by_dir[f.dir].append(f)
    for d, fs in by_dir.items():
        horiz = d[0] != 0
        cross = (lambda f: (f.rect.y0, f.rect.y1)) if horiz else (lambda f: (f.rect.x0, f.rect.x1))
        fs.sort(key=lambda f: cross(f)[0])
        clusters: list[list[Frag]] = []
        for f in fs:
            c0, c1 = cross(f)
            if clusters:
                last = clusters[-1]
                l0 = min(cross(x)[0] for x in last); l1 = max(cross(x)[1] for x in last)
                h = max(f.h, max(x.h for x in last))
                if abs(c0 - l0) < 0.3 * h and abs(c1 - l1) < 0.3 * h:
                    last.append(f)
                    continue
            clusters.append([f])
        for cl in clusters:
            cl.sort(key=lambda f: _along(f, f.rect)[0])
            cur = None
            for f in cl:
                if cur is not None:
                    h = max(cur.h, f.h)
                    gap = _along(f, f.rect)[0] - _along(cur, cur.rect)[1]
                    if -0.3 * h <= gap <= FRAG_GAP * h:
                        cur = Frag(cur.rect | f.rect, cur.text + f.text, d)
                        continue
                    out.append(cur)
                cur = f
            if cur is not None:
                out.append(cur)
    return out


def _closed_boxes(horiz, vert, frag: Frag):
    """조각 하나를 감싸는 닫힌 사각형 — 네 변이 전부 그려져 있어야 한다."""
    r, h = frag.rect, frag.h
    tol = h
    tops = [y for y, segs in horiz.items() if r.y0 - h <= y <= r.y0
            and any(a <= r.x0 + tol and b >= r.x1 - tol for a, b in segs)]
    bots = [y for y, segs in horiz.items() if r.y1 <= y <= r.y1 + h
            and any(a <= r.x0 + tol and b >= r.x1 - tol for a, b in segs)]
    if not tops or not bots:
        return None
    top, bot = max(tops), min(bots)
    lefts = [x for x, segs in vert.items() if r.x0 - h <= x <= r.x0
             and any(a <= top + tol and b >= bot - tol for a, b in segs)]
    rights = [x for x, segs in vert.items() if r.x1 <= x <= r.x1 + h
              and any(a <= top + tol and b >= bot - tol for a, b in segs)]
    if not lefts or not rights:
        return None
    return pymupdf.Rect(max(lefts), top, min(rights), bot)


def _down_side(f: Frag):
    """글자 방향의 '아래' 쪽 단위 벡터 (descender 쪽)."""
    dx, dy = f.dir
    return (-dy, dx) if (dx, dy) in ((1, 0), (-1, 0)) else (-dy, dx)


def _below(box: pymupdf.Rect, cand: Frag, ref: Frag):
    """cand 가 box 의 '아래'(ref 의 글자 방향 기준)에 붙어 있고 나란한가 → 거리 or None."""
    sx, sy = _down_side(ref)
    h = ref.h
    if sx == 0:                       # 가로 글자: 아래쪽 = +y
        gap = (cand.rect.y0 - box.y1) if sy > 0 else (box.y0 - cand.rect.y1)
        overlap = min(cand.rect.x1, box.x1) - max(cand.rect.x0, box.x0)
    else:                             # 세로 글자: 아래쪽 = ±x
        gap = (cand.rect.x0 - box.x1) if sx > 0 else (box.x0 - cand.rect.x1)
        overlap = min(cand.rect.y1, box.y1) - max(cand.rect.y0, box.y0)
    if -0.3 * h <= gap <= BELOW_GAP * h and overlap > 0:
        return gap
    return None


def find_labels(pc, runs, join_slack: float, area=None) -> list[LineLabel]:
    """한 장의 라인 라벨.  `runs` 는 `describe_axis` 가 쓰는 그 런 목록이다.

    `area` (도면 영역) 를 주면 그 밖(타이틀블록 · 개정 이력 표)은 보지 않는다.
    표 안의 칸도 "닫힌 사각형 안의 코드" 라서, **둘째 줄은 사각형 안에 있지
    않아야 한다** — 깃발의 둘째 줄은 열려 있고 표의 다음 행은 또 칸이다.
    """
    m = pc.page.rotation_matrix
    frags = join_fragments(_lines(pc.page, m))
    horiz, vert = legend_rules.stroke_index(pc.segments(), min_len=1.0)
    boxed = {}
    for f in frags:
        if tagsys._is_code(f.text) or f.text.isalnum():
            boxed[id(f)] = _closed_boxes(horiz, vert, f)
    out = []
    for f in frags:
        if not tagsys._is_code(f.text):
            continue
        box = boxed.get(id(f))
        if box is None:
            continue
        if area is not None and not pymupdf.Rect(area).contains(box):
            continue
        below = []
        for c in frags:
            if c is f or c.dir != f.dir or not c.text.isalnum():
                continue
            if boxed.get(id(c)) is not None:
                continue                      # 표의 다음 칸 — 깃발이 아니다
            g = _below(box, c, f)
            if g is not None:
                below.append((g, c))
        if not below:
            continue
        below.sort(key=lambda t: t[0])
        second = below[0][1]
        L = LineLabel(text=f"{f.text} {second.text}", box=box, rect=box | second.rect,
                      dir=f.dir, h=f.h, parts=(f.text, second.text))
        L.run = _flag_run(L, runs, horiz, vert, join_slack)
        if L.run is not None:
            L.spec = _spec_across(L, frags)
        out.append(L)
    return out


def _pole_end(L: LineLabel, horiz, vert):
    """깃대 — 사각형의 아래쪽 변에서 글자 방향과 **수직**으로 뻗어 나가는 선분의 먼 끝.

    QFE p46: 사각형 왼쪽 아래 모서리에서 세로선이 배관까지 내려간다.  p10(세로 글자):
    사각형 아래 변에서 가로선이 배관까지 간다.  없으면 None (거리로 폴백)."""
    sx, sy = _down_side(Frag(L.rect, "", L.dir))
    B, h = L.box, L.h
    best = None
    if sx == 0:                                           # 가로 글자 → 세로 깃대
        for x, segs in vert.items():
            if not (B.x0 - 0.3 * h <= x <= B.x1 + 0.3 * h):
                continue
            for a, b in segs:
                if sy > 0 and a <= B.y1 + 0.3 * h and b >= B.y1 + 0.5 * h:
                    end = b
                elif sy < 0 and b >= B.y0 - 0.3 * h and a <= B.y0 - 0.5 * h:
                    end = a
                else:
                    continue
                if best is None or abs(end - (B.y1 if sy > 0 else B.y0)) > best[0]:
                    best = (abs(end - (B.y1 if sy > 0 else B.y0)), end, x)
    else:                                                 # 세로 글자 → 가로 깃대
        for y, segs in horiz.items():
            if not (B.y0 - 0.3 * h <= y <= B.y1 + 0.3 * h):
                continue
            for a, b in segs:
                if sx > 0 and a <= B.x1 + 0.3 * h and b >= B.x1 + 0.5 * h:
                    end = b
                elif sx < 0 and b >= B.x0 - 0.3 * h and a <= B.x0 - 0.5 * h:
                    end = a
                else:
                    continue
                if best is None or abs(end - (B.x1 if sx > 0 else B.x0)) > best[0]:
                    best = (abs(end - (B.x1 if sx > 0 else B.x0)), end, y)
    if best is None:
        return None
    return best[1], best[2]          # (깃대 끝 좌표, 깃대 위치)


def _flag_run(L: LineLabel, runs, horiz=None, vert=None, join_slack: float = 0.8) -> tuple | None:
    """깃대가 닿는 런.  깃대가 있으면 **그 끝이 닿는 런**(글자와 평행 · 끝 좌표가 런의
    좌표와 join_slack 안 · 깃대 자리가 런 구간 안), 없으면 둘째 줄 쪽 RUN_REACH×h 안의
    가장 가까운 평행 런 — 나란한 두 선(배관과 신호선 3pt 차)이 있을 때 깃대만이 가른다."""
    sx, sy = _down_side(Frag(L.rect, "", L.dir))
    h = L.h
    want = "H" if sx == 0 else "V"
    pole = _pole_end(L, horiz, vert) if horiz is not None and vert is not None else None
    if pole is not None:
        end, at = pole
        tol = max(join_slack, 0.3 * h)
        hits = [(abs(coord - end), (axis, coord, lo, hi)) for axis, coord, lo, hi in runs
                if axis == want and abs(coord - end) <= tol and lo - tol <= at <= hi + tol]
        if hits:
            hits.sort(key=lambda t: t[0])
            L.pole = True
            return hits[0][1]
    best = None
    for axis, coord, lo, hi in runs:
        if axis != want:
            continue
        if sx == 0:
            d = (coord - L.rect.y1) if sy > 0 else (L.rect.y0 - coord)
            overlap = min(hi, L.rect.x1) - max(lo, L.rect.x0)
        else:
            d = (coord - L.rect.x1) if sx > 0 else (L.rect.x0 - coord)
            overlap = min(hi, L.rect.y1) - max(lo, L.rect.y0)
        if -0.5 * h <= d <= RUN_REACH * h and overlap > 0 and (best is None or d < best[0]):
            best = (d, (axis, coord, lo, hi))
    L.pole = False
    return best[1] if best else None


def _spec_across(L: LineLabel, frags) -> str:
    """런 건너편 글줄 — 뜻을 읽지 않고 글자 그대로."""
    axis, coord, lo, hi = L.run
    sx, sy = _down_side(Frag(L.rect, "", L.dir))
    h = L.h
    found = []
    for c in frags:
        if c.dir != L.dir or c.rect.intersects(L.rect):
            continue
        if axis == "H":
            d = (c.rect.y0 - coord) if sy > 0 else (coord - c.rect.y1)
            overlap = min(c.rect.x1, max(hi, L.rect.x1)) - max(c.rect.x0, min(lo, L.rect.x0))
            near = abs((c.rect.x0 + c.rect.x1) / 2 - (L.rect.x0 + L.rect.x1) / 2)
        else:
            d = (c.rect.x0 - coord) if sx > 0 else (coord - c.rect.x1)
            overlap = min(c.rect.y1, max(hi, L.rect.y1)) - max(c.rect.y0, min(lo, L.rect.y0))
            near = abs((c.rect.y0 + c.rect.y1) / 2 - (L.rect.y0 + L.rect.y1) / 2)
        if 0 <= d <= SPEC_REACH * h and overlap > 0 and near < 6 * h:
            found.append((near, c))
    if not found:
        return ""
    found.sort(key=lambda t: t[0])
    first = found[0][1]
    # 같은 글줄의 다른 조각(낱말 사이로 띄운 것)까지 붙인다
    same = [c for _n, c in found if abs(_along(c, c.rect)[0] - _along(first, first.rect)[0]) < 20 * h
            and (abs(c.rect.y0 - first.rect.y0) < 0.3 * h if axis == "H" else abs(c.rect.x0 - first.rect.x0) < 0.3 * h)]
    same.sort(key=lambda c: _along(c, c.rect)[0])
    return " ".join(c.text for c in same)


def systematic(labels_by_page: dict) -> set:
    """두 장 이상에서 되풀이되는 라벨 모양 — 그것만 라인 번호로 본다."""
    pages = collections.defaultdict(set)
    for pno, labels in labels_by_page.items():
        for L in labels:
            pages[L.shape()].add(pno)
    return {s for s, ps in pages.items() if len(ps) >= 2}


def _same_run(L: LineLabel, run, join_slack: float) -> bool:
    axis, coord, lo, hi = run
    if L.run is None or L.run[0] != axis or abs(L.run[1] - coord) > join_slack:
        return False
    a0, a1 = (L.rect.x0, L.rect.x1) if axis == "H" else (L.rect.y0, L.rect.y1)
    return not (a1 < lo - join_slack or a0 > hi + join_slack)


def nearest_on_run(rect, run, labels, join_slack: float):
    """탭한 런 위의 라벨 중 계기에 가장 가까운 것 — (라벨, 후보 수).  없으면 (None, 0).

    런의 좌표는 **같은 런 목록**에서 나온 것이라 join_slack 안이면 같은 런이다 —
    글자 높이로 느슨하게 보면 3pt 옆의 나란한 다른 선(신호선)의 라벨을 집는다 (QFE p46).
    """
    axis = run[0]
    cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
    cands = []
    for L in labels:
        if not _same_run(L, run, join_slack):
            continue
        a0, a1 = (L.rect.x0, L.rect.x1) if axis == "H" else (L.rect.y0, L.rect.y1)
        d = abs((a0 + a1) / 2 - (cx if axis == "H" else cy))
        cands.append((d, L))
    if not cands:
        return None, 0
    cands.sort(key=lambda t: t[0])
    return cands[0][1], len(cands)


def _extend_through_symbols(axis, coord, lo, hi, start_is_lo, leaders, runs, size, join_slack):
    """인출선이 **인라인 심볼**(뿌리 밸브)로 끊긴 것을 같은 직선으로 잇는다.

    QFE p46 PIT: 인출선 x=561 이 315→337 · 355→380 · 398→417 세 토막이고 사이의
    18pt 틈이 뿌리 밸브 둘이다.  같은 좌표의 다음 토막이 **심볼 크기(그 계기의 짧은
    변) 안**에 있고 틈을 **직교 획이 가로지르면**(심볼의 끝 바) 한 선이다 — 직선의
    복원이지 순회가 아니다 (§2.3 · `bridge_collinear` 와 같은 생각, 다리만 다르다).
    """
    pieces = sorted((l2, h2) for a2, c2, l2, h2 in leaders
                    if a2 == axis and abs(c2 - coord) <= join_slack)
    cross = [r for r in runs if r[0] != axis and r[2] - join_slack <= coord <= r[3] + join_slack]

    def inked(a, b):
        return any(a - join_slack <= r[1] <= b + join_slack for r in cross)
    for _ in range(len(pieces)):                     # 토막 수만큼만 — 끝이 있다
        moved = False
        if start_is_lo:                              # 상자가 lo 쪽 → hi 쪽으로 늘린다
            # 겹치거나(l2 ≤ hi) 심볼 크기 안의 틈 뒤에 있으면서 **더 멀리 가는** 토막
            nxt = [(l2, h2) for l2, h2 in pieces if h2 > hi + join_slack and l2 - hi <= size
                   and (l2 <= hi + join_slack or inked(hi, l2))]
            if nxt:
                hi, moved = max(h2 for _l2, h2 in nxt), True
        else:
            nxt = [(l2, h2) for l2, h2 in pieces if l2 < lo - join_slack and lo - h2 <= size
                   and (h2 >= lo - join_slack or inked(h2, lo))]
            if nxt:
                lo, moved = min(l2 for l2, _h2 in nxt), True
        if not moved:
            break
    return lo, hi


def via_leader(rect, leaders, runs, labels, join_slack: float):
    """탭한 런에 라벨이 없을 때 — 계기의 **인출선이 가로지르는** 런들(한 선분 · 순회 아님)
    가운데 라벨을 가진 가장 가까운 것.  (라벨, 후보 수, 런) 또는 (None, 0, None).

    QFE p46 PIT: 인출선이 뿌리 밸브 두 개를 지나 배관에 닿는데 판정축은 첫 교차
    (밸브의 10pt 가로 획)를 탭으로 잡는다 — 라인 번호는 그 인출선이 **마지막으로**
    가로지르는 배관의 것이고, 교차는 교차이지 따라가기가 아니다 (§2.3).
    """
    x0, y0, x1, y1 = rect
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    size = min(x1 - x0, y1 - y0)                      # 그 계기 심볼 자신의 짧은 변
    inside = lambda x, y: x0 - join_slack <= x <= x1 + join_slack and y0 - join_slack <= y <= y1 + join_slack  # noqa: E731
    best = None
    for axis, coord, lo, hi in leaders:
        ends = [(coord, lo), (coord, hi)] if axis == "V" else [(lo, coord), (hi, coord)]
        ins = [inside(x, y) for x, y in ends]
        if sum(ins) != 1:
            continue                                  # 한 끝만 상자 안인 것이 인출선이다
        lo, hi = _extend_through_symbols(axis, coord, lo, hi, ins[0], leaders, runs, size, join_slack)
        crossings = []
        for r in runs:
            if r[0] == axis:
                continue
            raxis, rc, rlo, rhi = r
            if not (rlo - join_slack <= coord <= rhi + join_slack and lo - join_slack <= rc <= hi + join_slack):
                continue                              # 가로지르지 않는다
            own = ((x0 - join_slack <= rlo and rhi <= x1 + join_slack) if raxis == "H"
                   else (y0 - join_slack <= rlo and rhi <= y1 + join_slack))
            if own:
                continue                              # 계기 자신의 몸통 획(버블 아랫변)
            crossings.append((abs(rc - (cy if axis == "V" else cx)), r))
        # 가까운 교차부터 본다.  라벨이 있으면 그것이고, 라벨 없는 **긴** 런(심볼보다
        # 긴 것 = 배관)을 먼저 만나면 거기서 멈춘다 — 진짜 탭에 깃발이 없는데 그
        # 너머 배관의 깃발을 집으면 안 된다.  심볼보다 짧은 런(뿌리 밸브의 획)은 지난다.
        for dist, r in sorted(crossings, key=lambda t: t[0]):
            raxis, rc, rlo, rhi = r
            on = [L for L in labels if _same_run(L, r, join_slack)]
            if on:
                if best is None or dist < best[0]:
                    on.sort(key=lambda L: abs(((L.rect.x0 + L.rect.x1) / 2 if raxis == "H"
                                               else (L.rect.y0 + L.rect.y1) / 2) - coord))
                    best = (dist, on[0], len(on), r)
                break
            if rhi - rlo >= size:
                break
    if best is None:
        return None, 0, None
    return best[1], best[2], best[3]


# ──────────────────────────────────────────────────────────────────────────
# 건너편 글줄 — 범례 "PIPING DESIGNATION FLAG" 가 정의하는 세 자리 (QFE p5 실측):
#   DN250H LAB1  =  PIPING DIAMETER(DN250) · PIPING INSULATION(H/P/N) · PROCESS DESIGN CODE(LAB1)
# 형식은 그 범례에서 **배운다** (`learn_flag_format`): 직경 접두(글자)는 범례 예시 글줄의
# 숫자 앞 글자, 보온 글자는 범례가 `- H :` 꼴로 나열한 것.  범례가 없으면 구조만으로 가른다
# (글자+숫자 · 숫자 바로 뒤 한 글자 · 나머지) — 출처를 `GENERIC` 으로 적는다.
# ──────────────────────────────────────────────────────────────────────────
# 구조만으로 가르는 토큰 — 글자(1~3) + 숫자(두 자리 이상 · `XX` 자리맡).  숫자 한 자리를
# 받지 않는 이유는 설계 코드(`LBB1` · `PCB1`)가 같은 꼴이기 때문이다.  범례가 접두를 주면
# `parse_spec` 은 그 접두로 찾으므로(`\d{1,4}`) 이 제한은 **GENERIC 에만** 걸린다.
_SIZE_RE = re.compile(r"(?<![A-Z0-9])(?P<prefix>[A-Z]{1,3})\s*(?P<size>\d{2,4}|X{1,3})(?![0-9])")


def parse_spec(spec: str, fmt: dict | None = None) -> dict:
    """`DN800H LBB1` / `DN 800 H LBB1` / `DN150NGKB4` / `NOTE 2 DN50H LBB1`
    → size `DN 800` · insulation `H` · design_code `LBB1`.

    사용자 정의: 라인 사이즈는 `DN 800` 꼴(접두 + 공백 + 수).  접두는 범례가 가르쳐 준
    것(`diameter_prefix`)을 먼저 찾고, 없으면 글줄 안의 `글자(1~3)+숫자` 토큰.  보온 글자는
    범례가 나열한 집합에 있을 때만 떼고, 범례가 없으면 숫자 바로 뒤 **홀로 선 한 글자**만
    보온으로 본다 — 붙어 있는 `NGKB4` 는 가르지 않는다 (지어내지 않는다).
    """
    out = {"size": "", "diameter_prefix": "", "insulation": "", "design_code": "", "raw": spec or ""}
    text = " ".join((spec or "").upper().split())
    if not text:
        return out
    want = (fmt or {}).get("diameter_prefix") or ""
    m = None
    if want:
        m = re.search(r"(?<![A-Z0-9])(?P<prefix>%s)\s*(?P<size>\d{1,4}|X{1,3})(?![0-9])" % re.escape(want), text)
    if m is None and not want:
        m = _SIZE_RE.search(text)
    if m is None:
        return out
    prefix, size = m.group("prefix"), m.group("size")
    out["diameter_prefix"], out["size"] = prefix, f"{prefix} {size}"
    rest = text[m.end():].strip()
    letters = set((fmt or {}).get("insulation") or ())
    if rest:
        head, _sp, tail = rest.partition(" ")
        if letters and head[:1] in letters:
            out["insulation"], rest = head[0], (head[1:] + (" " + tail if tail else "")).strip()
        elif not letters and len(head) == 1 and head.isalpha():
            out["insulation"], rest = head, tail.strip()
    # 설계 코드는 보온 글자 바로 뒤 **한 낱말**이다 — 뒤에 라인 번호를 덧붙인 글줄
    # (`DN200H LAB3 11LAB21`) 에서 그 꼬리를 코드에 섞지 않는다.
    out["design_code"] = (rest.split() or [""])[0]
    return out


def _word_lines(pc) -> list:
    """표시 좌표의 낱말을 글줄로 — 같은 좌표에 겹쳐 찍힌 낱말은 하나 (QFE 범례의 세 번 인쇄)."""
    seen, items = set(), []
    for r, t in pc.words:
        k = (round(r.x0, 1), round(r.y0, 1), t)
        if k in seen or not t.strip():
            continue
        seen.add(k); items.append((r, t))
    items.sort(key=lambda rt: ((rt[0].y0 + rt[0].y1) / 2, rt[0].x0))
    lines, cur, cy = [], [], None
    for r, t in items:
        c = (r.y0 + r.y1) / 2
        if cur and abs(c - cy) <= max(r.height, 1.0) / 2:
            cur.append((r, t))
        else:
            if cur:
                lines.append(sorted(cur, key=lambda rt: rt[0].x0))
            cur, cy = [(r, t)], c
    if cur:
        lines.append(sorted(cur, key=lambda rt: rt[0].x0))
    return lines


def learn_flag_format(pages) -> dict:
    """범례 장에서 깃발 형식을 배운다 — (보온 글자 집합 · 직경 접두 · 근거).

    보온 글자: 한 글줄에 `-` · 한 글자 · `:` 가 이 순서로 나란한 것 (QFE p5
    `- H : INSULATION FOR HEAT CONSERVATION`).  직경 접두: 같은 장의 글줄 중
    `글자+숫자+보온글자` 꼴(범례 예시 `DN250H LAB1`)의 글자 부분 — **QFE 는 그 예시를
    획으로 그려** 글자가 없으므로 접두는 비워 두고 본문에서 배운다
    (`learn_prefix_from_labels` · §9 ④).  보온 글자도 못 읽으면 `GENERIC`.
    """
    out = {"source": "GENERIC", "insulation": [], "diameter_prefix": "", "page_no": None,
           "prefix_source": ""}
    for pc in pages:
        lines = _word_lines(pc)
        letters = []
        for ln in lines:
            toks = [t for _r, t in ln] + ["", ""]
            for i in range(len(toks) - 2):
                if toks[i] != "-":
                    continue
                a, b = toks[i + 1], toks[i + 2]
                # `- H : …` (QFE · 셋이 따로) 또는 `- H: …` (낱말 추출이 `H:` 로 붙인 경우)
                if len(a) == 1 and a.isalpha() and b.startswith(":"):
                    letters.append(a.upper())
                elif len(a) == 2 and a[0].isalpha() and a[1] == ":":
                    letters.append(a[0].upper())
        if len(letters) < 2:
            continue
        out.update({"source": "LEGEND", "insulation": sorted(set(letters)), "page_no": pc.page_no})
        prefixes = collections.Counter()
        for ln in lines:
            text = " ".join(t for _r, t in ln).upper()
            for mm in _SIZE_RE.finditer(text):
                rest = text[mm.end():].strip()
                if rest[:1] in letters:
                    prefixes[mm.group("prefix")] += 1
        if prefixes:
            out.update({"diameter_prefix": prefixes.most_common(1)[0][0], "prefix_source": "LEGEND"})
        return out
    return out


def learn_prefix_from_labels(labels_by_page: dict, fmt: dict | None) -> dict:
    """직경 접두를 **본문 깃발 다수**에서 배운다 — 범례가 글자로 주지 않을 때만.

    규칙은 18·25회차와 같다: 그 문서가 **두 장 이상**에서 되풀이해 인쇄한 꼴만 받는다.
    후보는 건너편 글줄의 `글자(1~3)+숫자` 토큰이고, 범례가 보온 글자를 줬으면 숫자 뒤가
    그 글자인 것만 센다.  한 장뿐이면 배우지 않는다 (코드에 `DN` 을 적지 않는다).
    """
    out = dict(fmt or {})
    out.setdefault("insulation", []); out.setdefault("diameter_prefix", "")
    out.setdefault("source", "GENERIC"); out.setdefault("prefix_source", "")
    if out.get("diameter_prefix"):
        return out
    letters = set(out.get("insulation") or ())
    pages_of = collections.defaultdict(set)
    count = collections.Counter()
    for pno, labels in (labels_by_page or {}).items():
        for L in labels:
            text = " ".join((L.spec or "").upper().split())
            for mm in _SIZE_RE.finditer(text):
                rest = text[mm.end():].strip()
                if letters and rest[:1] not in letters:
                    continue
                pfx = mm.group("prefix")
                count[pfx] += 1
                pages_of[pfx].add(pno)
    best = [(n, p) for p, n in count.items() if len(pages_of[p]) >= 2]
    if not best:
        return out
    n, pfx = max(best)
    out.update({"diameter_prefix": pfx, "prefix_source": "BODY",
                "prefix_count": n, "prefix_pages": len(pages_of[pfx])})
    return out
