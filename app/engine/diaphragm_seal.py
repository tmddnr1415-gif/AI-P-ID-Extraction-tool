"""Diaphragm seal — 계기 임펄스 라인 위의 격막 씰을 읽는다 (hotfix22).

사용자 요청 (2026-09-28): *"PIT, PT, PG, PI Line 에 첨부와 같이 Diaphragm Seal symbol
이 있으면 Remark 에 'Diaphragm Seal' 을 표기해줘."*

§9 — 모양은 **그 문서의 범례**가 정한다.  외워둔 치수는 없다:
  · 범례 장에서 캡션 낱말(config `diaphragm_seal.caption`, 기본 `DIAPHRAGM SEAL`)이
    **그 줄에 그것만** 인쇄된 자리를 찾고, 그 왼쪽 같은 줄의 **닫힌 사각형 + 그 안의
    곡선 물결**을 심볼로 읽는다.  AL NOUF1 p2 실측: 사각형 19.8×9.9pt(`qu` 하나) 안에
    곡선 조각 셋이 폭 전체(1642.8~1662.7)를 잇는다.  TC2 p2 도 같은 항목을 인쇄한다.
  · 도면에서는 **그 크기**(긴 변·짧은 변, ±15% — Typical 표식과 같은 모양 허용치)의
    닫힌 사각형 안에 곡선이 **긴 변의 절반 이상**을 가로지르는 것을 씰로 본다.
    가로·세로 어느 방향으로 놓여도 같다 (긴 변·짧은 변으로 비교).
  · 계기와 잇는 것은 **곧은 선 하나 또는 꺾임 하나**다 — 씰에서 한 걸음, 그 끝에서 한 걸음.
    그 너머로 따라가지 않는다 (§2.3 순회 금지).  닿지 않으면 붙이지 않는다 (§2.1 ③).

범례가 그 항목을 인쇄하지 않으면 아무것도 찾지 않는다 — 다른 문서의 모양을 빌리지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pymupdf

SIZE_TOL = 0.15          # 크기 허용치 — `typical.circle_marks` 의 정사각 ±15% 와 같은 값
WAVE_SPAN = 0.5          # 곡선이 가로지르는 몫의 하한 (범례 실측 1.0 · 절반이면 다른 기호와 갈린다)


@dataclass
class Shape:
    long: float
    short: float
    page_no: int
    rect: tuple
    caption: str


@dataclass
class Seal:
    rect: pymupdf.Rect
    bubbles: list = field(default_factory=list)


def _closed_rect(items) -> bool:
    """닫힌 사각 테두리 — `re`·`qu` 하나, 또는 가로·세로 선 넷이 모서리마다 두 번 만난다."""
    if len(items) == 1 and items[0][0] in ("re", "qu"):
        return True
    if len(items) != 4 or any(i[0] != "l" for i in items):
        return False
    pts = []
    for _k, a, b in items:
        if abs(a.x - b.x) > 0.3 and abs(a.y - b.y) > 0.3:
            return False
        pts += [(round(a.x, 1), round(a.y, 1)), (round(b.x, 1), round(b.y, 1))]
    return all(pts.count(p) == 2 for p in pts)


def _curves(pc):
    return [pymupdf.Rect(d["bbox"]) for d in pc.drawings()
            if d["items"] and all(i[0] == "c" for i in d["items"]) and d.get("fill") is None]


def _wave_span(rect: pymupdf.Rect, curves) -> float:
    """사각형 안 곡선이 긴 변 방향으로 덮는 몫 (0~1)."""
    pad = 0.1 * min(rect.width, rect.height)
    box = pymupdf.Rect(rect.x0 - pad, rect.y0 - pad, rect.x1 + pad, rect.y1 + pad)
    inside = [c for c in curves if box.contains(c) and c != rect]
    if not inside:
        return 0.0
    if rect.width >= rect.height:
        lo, hi, full = min(c.x0 for c in inside), max(c.x1 for c in inside), rect.width
    else:
        lo, hi, full = min(c.y0 for c in inside), max(c.y1 for c in inside), rect.height
    return (hi - lo) / full if full > 0 else 0.0


def legend_shape(pages, caption: str) -> Shape | None:
    """그 문서 범례가 인쇄한 씰 모양 — 캡션 줄 왼쪽의 사각형+물결.  없으면 None."""
    want = caption.upper().split()
    if not want:
        return None
    for pc in pages:
        words = [(pymupdf.Rect(r), str(t).upper()) for r, t in pc.words]
        for i, (r0, t0) in enumerate(words):
            if t0 != want[0]:
                continue
            line = sorted([(r, t) for r, t in words
                           if abs((r.y0 + r.y1) / 2 - (r0.y0 + r0.y1) / 2) <= 0.5 * r0.height
                           and r.x0 >= r0.x0 - 0.1],
                          key=lambda x: x[0].x0)
            # 그 줄에 캡션 낱말만 (WITH DIAPHRAGM SEAL PIPED 같은 다른 항목의 문장을 거른다)
            left = [t for r, t in words
                    if abs((r.y0 + r.y1) / 2 - (r0.y0 + r0.y1) / 2) <= 0.5 * r0.height
                    and r0.x0 - 3 * r0.height < r.x1 <= r0.x0 - 0.1]
            if [t for _r, t in line[:len(want)]] != want or left:
                continue
            nxt = line[len(want)] if len(line) > len(want) else None
            if nxt is not None and nxt[0].x0 - line[len(want) - 1][0].x1 < 2 * r0.height:
                continue
            h = r0.height
            curves = _curves(pc)
            best = None
            for d in pc.drawings():
                if not d["items"] or not _closed_rect(d["items"]):
                    continue
                b = pymupdf.Rect(d["bbox"])
                # 같은 줄, 캡션 왼쪽, 그 사이에 다른 낱말이 없다 — 범례의 "심볼 열 | 캡션 열"
                # 간격은 문서마다 다르다 (AL NOUF1 110pt · TC2 55pt) 그래서 거리로 막지 않는다.
                if not (b.x1 <= r0.x0 and b.y0 < r0.y1 and b.y1 > r0.y0):
                    continue
                if any(b.x1 < r.x0 and r.x1 < r0.x0 and r.y0 < b.y1 and r.y1 > b.y0
                       for r, _t in words):
                    continue
                if _wave_span(b, curves) < WAVE_SPAN:
                    continue
                if best is None or b.x1 > best.x1:
                    best = b
            if best is not None:
                return Shape(max(best.width, best.height), min(best.width, best.height),
                             pc.page_no, tuple(round(v, 1) for v in best), " ".join(want))
    return None


def find(pc, shape: Shape) -> list[Seal]:
    """그 장에서 범례 크기의 사각형+물결."""
    if shape is None:
        return []
    curves = _curves(pc)
    out = []
    for d in pc.drawings():
        if not d["items"] or not _closed_rect(d["items"]):
            continue
        b = pymupdf.Rect(d["bbox"])
        lo, sh = max(b.width, b.height), min(b.width, b.height)
        if abs(lo - shape.long) > SIZE_TOL * shape.long or abs(sh - shape.short) > SIZE_TOL * shape.short:
            continue
        if _wave_span(b, curves) < WAVE_SPAN:
            continue
        out.append(Seal(b))
    return out


def _near(p: pymupdf.Point, r: pymupdf.Rect, slack: float) -> bool:
    return r.x0 - slack <= p.x <= r.x1 + slack and r.y0 - slack <= p.y <= r.y1 + slack


def link(pc, seals, bubbles) -> dict:
    """씰 → 선으로 이어진 버블.  `bubbles` 는 {열쇠: 사각형}.  반환 {열쇠: [씰 사각형]}.

    잇는 것은 **곧은 선 하나, 또는 꺾임 하나(두 토막이 한 점에서 만남)** 다.  AL NOUF1 p33
    의 FIT 는 버블 옆에서 가로로 나와 한 번 꺾여 씰로 내려간다.  두 토막을 넘어 따라가지
    않는다 (§2.3 — 순회가 아니다: 씰에서 한 걸음, 그 끝에서 한 걸음이고 더는 없다).
    허용치는 그 도형 자신의 짧은 변의 1/4 — 선 끝이 테두리 위나 바로 앞에서 멈춘다."""
    out: dict = {}
    if not seals or not bubbles:
        return out
    segs = pc.segments()
    brs = {k: (pymupdf.Rect(r), 0.25 * min(pymupdf.Rect(r).width, pymupdf.Rect(r).height))
           for k, r in bubbles.items()}
    for s in seals:
        ss = 0.25 * min(s.rect.width, s.rect.height)
        far_ends = []
        for a, b in segs:
            if _near(a, s.rect, ss) and not _near(b, s.rect, ss):
                far_ends.append(b)
            elif _near(b, s.rect, ss) and not _near(a, s.rect, ss):
                far_ends.append(a)
        # 첫 토막의 먼 끝 → 버블이면 곧은 선 하나.  아니면 그 끝에서 시작하는 토막 **하나**.
        reach = list(far_ends)
        for e in far_ends:
            for a, b in segs:
                if abs(a.x - e.x) <= ss and abs(a.y - e.y) <= ss:
                    reach.append(b)
                elif abs(b.x - e.x) <= ss and abs(b.y - e.y) <= ss:
                    reach.append(a)
        for key, (br, bs) in brs.items():
            if any(_near(p, br, bs) for p in reach):
                out.setdefault(key, []).append(tuple(round(v, 1) for v in s.rect))
                s.bubbles.append(key)
    return out
