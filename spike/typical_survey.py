"""38회차 [D-2] — Typical 참조 전수 실측 (구현 전).

무엇을 세나 (전부 그 도면에서 읽는다 — 정규식으로 D·D1·D2 를 나열하지 않는다)
  · 표식: 호(arc)만으로 그린 작은 원(4 'c' · 정사각에 가까움) 안에 짧은 낱말(1~3자 · 글자로
    시작)이 하나 들어 있는 것.  계기 버블(캡 둘 + 옆면 · 두 줄 글자)과 모양이 다르다.
  · 캡션: 표식 낱말 바로 오른쪽에 ':' 가 오는 줄 → 상세 상자의 제목.
  · 상세 상자: 캡션 x 범위를 덮는 가장 가까운 긴 가로선(위·아래)과 그 끝을 잇는 세로선.
  · 상자 안의 기존 행(저장된 결과) · 장별 표식 수(캡션 제외) · 짝이 안 맞는 것.

실행: python3 spike/typical_survey.py TC2 → out/round38/typical_TC2.json
"""
from __future__ import annotations
import collections, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "engine")); sys.path.insert(0, str(ROOT))
import pidcache, pymupdf  # noqa: E402

PROJECTS = {p["name"]: p for p in json.loads((ROOT / "spike" / "projects_3p.json").read_text())["projects"]}
SHORT = re.compile(r"^[A-Z][A-Z0-9]{0,2}$")


def survey(name):
    proj = PROJECTS[name]
    stored = json.loads((ROOT / "out" / "regression_3p" / (name.replace(" ", "_") + ".json")).read_text())
    res, rows = stored["result"], stored["result"]["rows"]
    lay = {i["key"]: i["value"] for i in res["applied_rules"]["layout"]["items"] if isinstance(i, dict)}
    da = pymupdf.Rect(*lay["regions.drawing_area"])
    pid = {p["page_no"] for p in res["pages"] if p.get("page_kind") == "PID"}
    doc, pages = pidcache.load_pages(ROOT / proj["pdf"])
    out = {"project": name, "drawing_area": list(da), "pages": []}
    for pc in pages:
        if pc.page_no not in pid:
            continue
        words = [(pymupdf.Rect(r), t) for r, t in pc.words]
        circles = [d["bbox"] for d in pc.drawings()
                   if len(d["items"]) == 4 and all(i[0] == "c" for i in d["items"])
                   and 0.85 <= d["bbox"].width / max(d["bbox"].height, 0.01) <= 1.15
                   and 4 <= d["bbox"].width <= 14 and da.contains(d["bbox"])]
        marks = []
        for cb in circles:
            inside = [(r, t) for r, t in words if cb.contains(r.tl) and cb.contains(r.br)]
            if len(inside) == 1 and SHORT.match(inside[0][1]):
                marks.append({"id": inside[0][1], "rect": [round(v, 1) for v in cb],
                              "d": round(cb.width, 2)})
        caps = []
        for m in marks:
            r = pymupdf.Rect(m["rect"])
            colon = [w for w, t in words if t == ":" and abs(w.y0 - r.y0) < 4 and 0 <= w.x0 - r.x1 <= 12]
            if colon:
                line = sorted([(w.x0, t) for w, t in words if abs(w.y0 - r.y0) < 3 and r.x1 <= w.x0 <= r.x1 + 260], key=lambda x: x[0])
                m["caption"] = " ".join(t for _x, t in line)
                caps.append(m)
        segs = pc.segments()
        hs = [(a, b) for a, b in segs if abs(a.y - b.y) < 0.4 and abs(a.x - b.x) > 60]
        vs = [(a, b) for a, b in segs if abs(a.x - b.x) < 0.4 and abs(a.y - b.y) > 40]
        details = []
        for m in caps:
            r = pymupdf.Rect(m["rect"]); cx = (r.x0 + r.x1) / 2
            span = [h for h in hs if min(h[0].x, h[1].x) <= cx <= max(h[0].x, h[1].x)]
            above = sorted([h for h in span if h[0].y < r.y0], key=lambda h: -h[0].y)[:1]
            below = sorted([h for h in span if h[0].y > r.y1], key=lambda h: h[0].y)[:1]
            box = None
            if above and below:
                x0 = max(min(above[0][0].x, above[0][1].x), min(below[0][0].x, below[0][1].x))
                x1 = min(max(above[0][0].x, above[0][1].x), max(below[0][0].x, below[0][1].x))
                y0, y1 = above[0][0].y, below[0][0].y
                sides = [v for v in vs if (abs(v[0].x - x0) < 1.5 or abs(v[0].x - x1) < 1.5)
                         and min(v[0].y, v[1].y) <= y0 + 1.5 and max(v[0].y, v[1].y) >= y1 - 1.5]
                if x1 - x0 > 40 and y1 - y0 > 30:
                    box = {"rect": [round(v, 1) for v in (x0, y0, x1, y1)], "sides": len(sides)}
            inside = [x for x in rows if x["page_no"] == pc.page_no and box
                      and pymupdf.Rect(*box["rect"]).contains(pymupdf.Rect(*x["rect"]))]
            details.append({"id": m["id"], "caption": m.get("caption", ""), "box": box,
                            "rows_inside": [(x["type"], x["tab"], x["qty"]) for x in inside]})
        cap_ids = {id(m) for m in caps}
        line_marks = [m for m in marks if id(m) not in cap_ids]
        boxes = [pymupdf.Rect(*d["box"]["rect"]) for d in details if d["box"]]
        refs = [m for m in line_marks if not any(b.contains(pymupdf.Rect(m["rect"])) for b in boxes)]
        per = collections.Counter(m["id"] for m in refs)
        ids_detail = {d["id"] for d in details}
        out["pages"].append({
            "page_no": pc.page_no, "circles": len(circles), "marks": len(marks),
            "refs": dict(per), "ref_rects": [(m["id"], m["rect"]) for m in refs], "details": details,
            "refs_without_detail": sorted(set(per) - ids_detail),
            "details_without_ref": sorted(ids_detail - set(per)),
            "mark_diameters": sorted({m["d"] for m in marks}),
        })
        print(pc.page_no, "circles", len(circles), "marks", len(marks), "refs", dict(per),
              "details", [(d["id"], bool(d["box"]), len(d["rows_inside"])) for d in details], flush=True)
    doc.close()
    dest = ROOT / "out" / "round38" / f"typical_{name.replace(' ', '_')}.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("written", dest)


if __name__ == "__main__":
    survey(sys.argv[1] if len(sys.argv) > 1 else "TC2")
