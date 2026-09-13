"""Typical 참조 — 라인 위의 원 표식이 같은 장의 상세 상자 한 벌을 가리킨다 (38회차 [D]).

도면이 그리는 것 (TC2 실측 · `out/round38_typical.md`):
  · 표식: 배관 라인 위 작은 원(호 4개 한 도형 · 정사각) 안에 짧은 낱말 하나 (`D` · `D1` · `D2`).
  · 상세: 같은 장에 같은 원 표식 + 제목이 붙은 사각 상자.  안에 계기 한 벌이 그려져 있다.
  · 뜻: 그 라인에는 상세에 그려진 한 벌이 있다 → 상자 안 계기의 수량 = 표식 수 × 1.

읽는 규칙 — 전부 모양이고 절대 pt 를 두지 않는다 (§9 6):
  · 원의 지름 상한은 **그 장 계기 버블의 짧은 변** (버블보다 작다).  글자는 낱말 하나 · 1~3자 · 글자로 시작.
    `D`·`D1` 같은 꼴을 나열하지 않는다 — 모터 `M` 원도 같은 모양으로 잡히고, **같은 장에 캡션이 있는
    id 만 참조**라는 짝 규칙이 거른다.
  · 캡션 표식 = 오른쪽으로 지름 두 배 안에서 같은 줄로 글이 이어지는 표식.  라인 표식은 오른쪽에 글이 없다.
    (p8 은 `:` 없이 `D HRH TYPICAL …` 이라 `:` 나 낱말로 찾지 않는다.)
  · 상자 = 캡션 x 를 덮는 가장 가까운 긴 가로선(지름의 10배 이상) 위·아래 하나씩과 그 x 겹침.
  · 참조 = 상자 밖의 같은 id 표식.  같은 id 의 캡션이 한 장에 둘이면 어느 상자인지 도면이 말하지 않으므로
    곱하지 않고 `ambiguous` 로 낸다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pymupdf

SHORT = re.compile(r"^[A-Z][A-Z0-9]{0,2}$")


@dataclass
class Mark:
    id: str
    rect: pymupdf.Rect
    d: float


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
                "refs": dict(self.refs), "ambiguous": sorted(self.ambiguous)}


def circle_marks(pc, area: pymupdf.Rect, ceiling: float) -> list[Mark]:
    """원 안에 짧은 낱말 하나 — 지름은 `ceiling`(그 장 버블 짧은 변) 미만."""
    words = [(pymupdf.Rect(r), t) for r, t in pc.words]
    out = []
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
        if len(inside) == 1 and SHORT.match(inside[0][1]):
            out.append(Mark(inside[0][1], pymupdf.Rect(cb), cb.width))
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

    def on_a_line(r: pymupdf.Rect) -> bool:
        """라인 표식은 배관 위에 앉는다 — 원의 중심을 지나는 선분이 있다.  캡션 표식은 없다."""
        cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
        for a, b in segs:
            if abs(a.y - b.y) < 0.4 and abs(a.y - cy) <= r.height / 2 \
                    and min(a.x, b.x) <= r.x0 and max(a.x, b.x) >= r.x1:
                return True
            if abs(a.x - b.x) < 0.4 and abs(a.x - cx) <= r.width / 2 \
                    and min(a.y, b.y) <= r.y0 and max(a.y, b.y) >= r.y1:
                return True
        return False

    # 캡션 — 오른쪽 지름 두 배 안에서 같은 줄로 글이 두 낱말 이상 이어지고, 배관 위가 아니다
    captions = []
    for m in t.marks:
        r, d = m.rect, m.d
        right = [(w, s) for w, s in words
                 if 0 <= w.x0 - r.x1 <= 2 * d and w.y0 < r.y1 and w.y1 > r.y0]
        if not right or on_a_line(r):
            continue
        line = sorted([(w.x0, s) for w, s in words
                       if w.y0 < r.y1 and w.y1 > r.y0 and r.x1 <= w.x0 <= area.x1],
                      key=lambda x: x[0])
        if len(line) < 2:
            continue
        text = " ".join(s for _x, s in line).strip()
        captions.append((m, text))
    if not captions:
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
        # 캡션을 담는 가장 작은 것이 상자다 — 시트 틀·큰 패키지 상자는 그보다 크다.
        box = min(cands, key=lambda q: q.get_area()) if cands else None
        t.details.append(Detail(m.id, text, r, box))
    ids = [det.id for det in t.details]
    t.ambiguous = {i for i in ids if ids.count(i) > 1}
    boxes = [det.box for det in t.details if det.box is not None]
    cap_rects = [det.mark for det in t.details]
    for m in t.marks:
        if m.id not in ids or m.rect in cap_rects:
            continue
        if any(b.contains(m.rect) for b in boxes):
            continue                         # 상자 안 표식은 그 상자의 것
        t.refs[m.id] = t.refs.get(m.id, 0) + 1
    return t
