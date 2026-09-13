"""Typical 참조 — 도면이 스스로 선언한 짝을 읽는다 (38회차 [D] · 보정 프롬프트).

    상세 상자 캡션   (글자) …제목…        ← 상자가 먼저 선언한다.  글자가 무엇이든 상관없다
    본문 라인 표식   동그라미 안에 같은 글자  ← 같은 장에서 짝이 맞으면 그것이 표식이다

★ 표식 목록을 코드가 갖지 않는다 — 장마다 그 장에서 만든다.  글자를 판정 조건으로 쓰지 않고
  (정규식도 없다 · `tests/test_typical.py` 가 소스에서 그 글자들을 찾으면 실패한다), 다른 장의
  같은 글자는 다른 뜻일 수 있으므로 짝은 장 단위다.  낱말(TYPICAL · DETAIL …)도 판정에 쓰지 않는다 —
  근거로 기록만 한다.

읽는 규칙 — 전부 모양·관계이고 절대 pt 를 두지 않는다 (§9 6):
  · 표식 후보 = 호 4개로 그린 정사각(±15%) 원 안에 **낱말 하나가 통째로** 들어 있고, 지름이 **그 장
    계기 버블의 짧은 변보다 작은** 것.  계기 버블(두 줄 · 배관에 붙음)과 가르는 것도 글자가 아니라 구조다.
  · 캡션 표식 = **아무 선도 닿지 않는** 원 + 오른쪽 지름 두 배 안에서 같은 줄로 글이 두 낱말 이상.
    선이 닿는 원은 캡션이 아니다 — AL NOUF1 의 모터 `M` 원은 스템이 닿고 오른쪽에 글이 있어 이 조건이
    없으면 캡션이 된다 (첫 [H] 가 그렇게 움직였다).
  · 라인 표식 = 선이 닿는 원 (TC2 실측: 배관에서 내려온 리더 하나 · 지나가는 선 0).  모터 원도 같은
    모양이지만 **같은 장에 그 글자의 캡션이 없으므로** 참조가 되지 않는다.
  · 상자 = 캡션 표식을 담는 후보(한 도형 사각·사변형 / 긴 가로선 둘) 중 **독립 섬인 것 중 가장 작은 것**.
    독립 섬 = 안에서 시작해 밖으로 나가는 선분이 하나도 없다 (본문 배관과 이어지지 않는다).
    TC2 p11 실측: 선 기반 후보 하나가 배관 13개에 가로질려 있었고 진짜 상자는 그 옆의 사변형이었다.
    16회차 PACKAGE_BOX 는 재사용하지 못한다 — 그것은 **체인 파선**(brk_* · 마크 6개 이상)만 잡고 상세
    상자는 실선 사변형/실선 넷이다 (TC2 p6~p11 에서 0개 반환 실측).
  · 참조 = 상자 밖의 같은 글자 라인 표식.  같은 글자의 캡션이 한 장에 둘이면 어느 상자인지 도면이
    말하지 않으므로 곱하지 않고 `ambiguous` 로 낸다.
  · 짝이 안 맞는 것은 버리지 않고 낸다 — 캡션 없는 라인 표식(`unpaired`) · 본문 표식 0 인 캡션
    (`refs` 0).  사람이 보게 한다.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import pymupdf



@dataclass
class Mark:
    id: str
    rect: pymupdf.Rect
    d: float
    kind: str = "free"          # free — 아무 선도 안 닿는다(캡션 자리) · line — 배관이 지나간다(참조 자리)


@dataclass
class Detail:
    id: str
    caption: str
    mark: pymupdf.Rect
    box: pymupdf.Rect | None


@dataclass
class Typical:
    marks: list = field(default_factory=list)
    details: list = field(default_factory=list)
    refs: dict = field(default_factory=dict)        # id -> 참조 표식 수 (캡션이 있는 id 만)
    ambiguous: set = field(default_factory=set)     # 같은 장에 캡션이 둘 이상인 id
    unpaired: dict = field(default_factory=dict)    # id -> 캡션이 없는 라인 표식 수 (짝 없음 — 기록만)

    def factor_for(self, rect: pymupdf.Rect):
        """`rect` 가 어느 상세 상자 안이면 (상세, 참조 수) — 아니면 None."""
        for det in self.details:
            if det.box is not None and det.box.contains(rect):
                return det, self.refs.get(det.id, 0)
        return None

    def as_dict(self) -> dict:
        return {"marks": [(m.id, [round(v, 1) for v in m.rect]) for m in self.marks],
                "details": [{"id": d.id, "caption": d.caption,
                             "box": [round(v, 1) for v in d.box] if d.box else None}
                            for d in self.details],
                "refs": dict(self.refs), "ambiguous": sorted(self.ambiguous),
                "unpaired": dict(self.unpaired)}


def _dist(p: pymupdf.Point, a: pymupdf.Point, b: pymupdf.Point) -> float:
    """점 p 에서 선분 ab 까지의 거리."""
    dx, dy = b.x - a.x, b.y - a.y
    l2 = dx * dx + dy * dy
    if l2 == 0:
        return math.hypot(p.x - a.x, p.y - a.y)
    t = max(0.0, min(1.0, ((p.x - a.x) * dx + (p.y - a.y) * dy) / l2))
    return math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy))


def is_island(box: pymupdf.Rect, segs) -> bool:
    """안에서 시작해 밖으로 나가는 선분이 없다 — 본문 배관과 이어지지 않은 상자.

    상자 변 위의 선분(자기 테두리)은 어느 쪽 끝도 *엄격히* 안이 아니므로 걸리지 않는다."""
    def strictly_in(p):
        return box.x0 < p.x < box.x1 and box.y0 < p.y < box.y1
    def strictly_out(p):
        return p.x < box.x0 or p.x > box.x1 or p.y < box.y0 or p.y > box.y1
    return not any((strictly_in(a) and strictly_out(b)) or (strictly_in(b) and strictly_out(a))
                   for a, b in segs)


def circle_marks(pc, area: pymupdf.Rect, ceiling: float) -> list[Mark]:
    """원 안에 낱말 하나가 통째로 — 지름은 `ceiling`(그 장 버블 짧은 변) 미만.  글자는 보지 않는다."""
    words = [(pymupdf.Rect(r), t) for r, t in pc.words]
    out = []
    segs = pc.segments()
    for d in pc.drawings():
        items = d["items"]
        if len(items) != 4 or any(i[0] != "c" for i in items):
            continue
        cb = d["bbox"]
        if cb.height <= 0 or not 0.85 <= cb.width / cb.height <= 1.15:
            continue
        if not (cb.width < ceiling and area.contains(cb)):
            continue
        inside = [(r, t) for r, t in words if cb.contains(r.tl) and cb.contains(r.br)]
        if len(inside) != 1:
            continue
        # 원에 선이 닿는가로 둘을 가른다 (25회차 별표의 "자유 끝점" 과 같은 눈):
        #   · 아무 선도 안 닿는다 → 캡션 자리 (free)
        #   · 선이 닿는다 → 라인 표식 자리 (line).  TC2 실측(p6·p7): 라인 표식은 배관에서 내려온
        #     리더 **하나**가 닿고 지나가는 선은 없다 — 모터 `M` 원(스템 하나)과 모양이 같아서
        #     "양쪽에서 들어오는 선" 으로는 갈리지 않는다 (그 규칙은 참조를 0 으로 만들었다).
        #     둘을 가르는 것은 모양이 아니라 **짝**이다 — 같은 장에 같은 id 의 캡션이 있어야 참조다.
        #   AL NOUF1 p18·p20 의 `M` 원은 스템이 닿으므로 캡션이 될 수 없다 (Q'ty 가 움직였던 원인).
        #   닿는다 = 한 끝이 원 안에 있다(리더) **또는** 원 가운데를 지나간다(원을 선 위에 그린 문서).
        pad = pymupdf.Rect(cb.x0 - 0.5, cb.y0 - 0.5, cb.x1 + 0.5, cb.y1 + 0.5)
        centre, rad = pymupdf.Point((cb.x0 + cb.x1) / 2, (cb.y0 + cb.y1) / 2), cb.width / 2
        touched = any(pad.contains(a) != pad.contains(b) or _dist(centre, a, b) < rad
                      for a, b in segs)
        kind = "line" if touched else "free"
        out.append(Mark(inside[0][1], pymupdf.Rect(cb), cb.width, kind))
    return out


def analyse(pc, area, ceiling: float | None) -> Typical:
    t = Typical()
    if not ceiling or ceiling <= 0:
        return t
    area = pymupdf.Rect(*area) if not isinstance(area, pymupdf.Rect) else area
    t.marks = circle_marks(pc, area, ceiling)
    if not t.marks:
        return t
    words = [(pymupdf.Rect(r), s) for r, s in pc.words]
    segs = pc.segments()


    # 캡션 — 오른쪽 지름 두 배 안에서 같은 줄로 글이 두 낱말 이상 이어지고, 배관 위가 아니다
    captions = []
    for m in t.marks:
        r, d = m.rect, m.d
        right = [(w, s) for w, s in words
                 if 0 <= w.x0 - r.x1 <= 2 * d and w.y0 < r.y1 and w.y1 > r.y0]
        if not right or m.kind != "free":
            continue
        line = sorted([(w.x0, s) for w, s in words
                       if w.y0 < r.y1 and w.y1 > r.y0 and r.x1 <= w.x0 <= area.x1],
                      key=lambda x: x[0])
        if len(line) < 2:
            continue
        text = " ".join(s for _x, s in line).strip()
        captions.append((m, text))
    if not captions:
        # 상자(캡션)가 없는 장 — 본문에 글자 원이 있어도 Typical 이 아니다.  그 사실을 기록한다 (보정 프롬프트 ④).
        for m in t.marks:
            if m.kind == "line":
                t.unpaired[m.id] = t.unpaired.get(m.id, 0) + 1
        return t
    hs = [(a, b) for a, b in segs if abs(a.y - b.y) < 0.4]
    # 상자를 한 도형(사각형·사변형)으로 그린 문서와 선 넷으로 그린 문서가 있다 — TC2 는
    # 한 장 안에서도 섞여 있다 (p7 D2 는 사변형 하나 · D1 은 선 넷).  도형이 있으면 그것이
    # 상자이고(캡션 표식을 담는 가장 작은 것), 없으면 긴 가로선 둘로 세운다.
    quads = [d["bbox"] for d in pc.drawings()
             if d["items"] and all(i[0] in ("qu", "re", "l") for i in d["items"])
             and any(i[0] in ("qu", "re") for i in d["items"])]
    for m, text in captions:
        r, d = m.rect, m.d
        cx = (r.x0 + r.x1) / 2
        cands = [pymupdf.Rect(q) for q in quads
                 if q.contains(r) and q.width >= 6 * d and q.height >= 4 * d
                 and q.width <= area.width * 0.7 and q.height <= area.height * 0.7]
        long_ = [h for h in hs if abs(h[0].x - h[1].x) >= 10 * d
                 and min(h[0].x, h[1].x) <= cx <= max(h[0].x, h[1].x)]
        above = sorted([h for h in long_ if h[0].y < r.y0], key=lambda h: -h[0].y)[:1]
        below = sorted([h for h in long_ if h[0].y > r.y1], key=lambda h: h[0].y)[:1]
        if above and below:
            x0 = max(min(above[0][0].x, above[0][1].x), min(below[0][0].x, below[0][1].x))
            x1 = min(max(above[0][0].x, above[0][1].x), max(below[0][0].x, below[0][1].x))
            y0, y1 = above[0][0].y, below[0][0].y
            if x1 - x0 >= 6 * d and y1 - y0 >= 4 * d:
                cands.append(pymupdf.Rect(x0, y0, x1, y1))
        # 캡션을 담는 **독립 섬** 중 가장 작은 것이 상자다 — 시트 틀·큰 패키지 상자는 그보다 크고,
        # 배관이 가로지르는 후보는 섬이 아니다 (TC2 p11 실측 — 선 기반 후보에 13개 선이 걸쳤다).
        islands = [q for q in cands if is_island(q, segs)]
        box = min(islands, key=lambda q: q.get_area()) if islands else None
        t.details.append(Detail(m.id, text, r, box))
    ids = [det.id for det in t.details]
    t.ambiguous = {i for i in ids if ids.count(i) > 1}
    boxes = [det.box for det in t.details if det.box is not None]
    cap_rects = [det.mark for det in t.details]
    for m in t.marks:
        if m.rect in cap_rects or m.kind != "line":
            continue
        if m.id not in ids:
            t.unpaired[m.id] = t.unpaired.get(m.id, 0) + 1     # 짝 없는 라인 표식 — 기록만
            continue
        if any(b.contains(m.rect) for b in boxes):
            continue                         # 상자 안 표식은 그 상자의 것
        t.refs[m.id] = t.refs.get(m.id, 0) + 1
    return t
