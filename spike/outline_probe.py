"""[30-B] 마크가 버블의 **그려진 윤곽** 안인가 밖인가 — 엔진을 고치기 전 실측.

버블은 스타디움이다 (`find_bubbles`: 마주 본 호 캡 둘 + 곧은 옆면).  그러니
윤곽은 **그 도면이 그린 캡**으로 정해진다 — 반지름을 가정하지 않는다
(AL NOUF1 캡 비율 ≈ 2.0 ↔ TC2 34x11 ≈ 3.1).

    가로 스타디움:  곧은 부분 [a.x1, b.x0] x [y0, y1]
                    + 왼쪽 캡 타원 (중심 a.x1, 반축 a.width x height/2)
                    + 오른쪽 캡 타원 (중심 b.x0, 반축 b.width x height/2)

bbox 의 네 모서리는 이 합집합 **밖**이고, 도면이 별표를 찍는 자리가 거기다
(§10-10 · AL NOUF1 p55 렌더).
"""
from __future__ import annotations
import collections, json, sys
sys.path.insert(0, 'app/engine')
import pymupdf, pidcache, detect_symbols as ds


def caps_of(pc, lay):
    """find_bubbles 와 **같은 조건**으로 호 캡을 모은다 (값을 새로 정하지 않는다)."""
    wide, tall = [], []
    for d in pc.drawings():
        items = d["items"]
        if not items or any(i[0] != "c" for i in items):
            continue
        r = d["bbox"]
        w, h = r.width, r.height
        if w <= 0 or h <= 0:
            continue
        short, long_ = min(w, h), max(w, h)
        if not lay.cap_ratio[0] <= long_ / short <= lay.cap_ratio[1]:
            continue
        (tall if h > w else wide).append(r)
    return wide, tall


def outline_of(rect, wide, tall, tol=0.6):
    """이 사각형의 스타디움 윤곽 → (축, 캡a, 캡b).  못 찾으면 None."""
    for axis, caps in (("H", tall), ("V", wide)):
        if axis == "H":
            ends = [c for c in caps if abs(c.y0 - rect.y0) < tol and abs(c.y1 - rect.y1) < tol]
            a = [c for c in ends if abs(c.x0 - rect.x0) < tol]
            b = [c for c in ends if abs(c.x1 - rect.x1) < tol]
        else:
            ends = [c for c in caps if abs(c.x0 - rect.x0) < tol and abs(c.x1 - rect.x1) < tol]
            a = [c for c in ends if abs(c.y0 - rect.y0) < tol]
            b = [c for c in ends if abs(c.y1 - rect.y1) < tol]
        if a and b:
            return axis, a[0], b[0]
    return None


def inside_outline(rect, x, y, shape) -> bool:
    axis, a, b = shape
    if axis == "H":
        cy, ry = (rect.y0 + rect.y1) / 2, (rect.y1 - rect.y0) / 2
        if a.x1 <= x <= b.x0:
            return rect.y0 <= y <= rect.y1
        for cx, rx in ((a.x1, a.width), (b.x0, b.width)):
            if rx > 0 and ry > 0 and ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                return True
        return False
    cx, rx = (rect.x0 + rect.x1) / 2, (rect.x1 - rect.x0) / 2
    if a.y1 <= y <= b.y0:
        return rect.x0 <= x <= rect.x1
    for cy, ry in ((a.y1, a.height), (b.y0, b.height)):
        if rx > 0 and ry > 0 and ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
            return True
    return False


def main(name, res_json, pdf):
    rows = json.load(open(res_json))["result"]["rows"]
    byp = collections.defaultdict(list)
    for r in rows:
        byp[r["page_no"]].append(r)
    doc, pages = pidcache.load_pages(pdf)
    lay = ds.LAYOUT
    stat = collections.Counter()
    hits = []
    for pc in pages:
        rs = byp.get(pc.page_no)
        if not rs:
            continue
        marks = ds.find_marks(pc)
        if not marks:
            continue
        wide, tall = caps_of(pc, lay)
        for r in rs:
            rect = pymupdf.Rect(*r["rect"])
            shape = outline_of(rect, wide, tall)
            for m in marks:
                x, y = m[0], m[1]
                if not ds.in_mark_window(rect, x, y, lay):
                    continue
                if shape is None:
                    stat["윤곽 못 찾음"] += 1
                    hits.append((pc.page_no, r.get("tag_no") or r["type"], r["scope"],
                                 "윤곽없음", round(x, 2), round(y, 2), m[2], m[3]))
                elif inside_outline(rect, x, y, shape):
                    stat["윤곽 안 (글자)"] += 1
                    hits.append((pc.page_no, r.get("tag_no") or r["type"], r["scope"],
                                 "안", round(x, 2), round(y, 2), m[2], m[3]))
                else:
                    stat["윤곽 밖 (마크)"] += 1
    print(f"== {name} ==", dict(stat))
    for h in hits:
        print("   ", h)


if __name__ == "__main__":
    main(*sys.argv[1:4])
