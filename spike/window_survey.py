"""37회차 — 창 상수 셋(`ds.cap_span` · `dv.seg_span` · `tb.zoom`)을 유도할 근거가
있는지 네 문서에서 재는 도구.  엔진을 고치지 않는다.

무엇을 세나
  · 호(arc)만으로 된 도형의 긴 변 분포 — `bubble_outlines` 가 캡 후보로 받는 것.
    창 (7, 50) 안/밖 · 비율 창 (1.6, 2.4) 안/밖을 함께 센다.
  · 선분 길이 분포 — `_index_segments` 가 `seg_span` (1, 60) 으로 거르는 것.
  · 저장된 결과의 행 사각형 — 계기 버블 짧은 변(= 캡의 긴 변) · 밸브 몸체 변.
  · 타이틀블록 셀·글자 높이 × zoom(24) 의 픽셀 값 — 픽셀 문턱(min_ink_px 20 ·
    char_gap_px 6)이 어느 글자 크기에서 걸리는지.

실행:  python3 spike/window_survey.py  →  out/round37_window_survey.json
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.engine import pidcache  # noqa: E402

PROJECTS = json.loads((ROOT / "spike" / "projects_3p.json").read_text())["projects"]
RUNS = ROOT / "out" / "regression_3p"
CAP_SPAN = (7.0, 50.0)
CAP_RATIO = (1.6, 2.4)
SEG_SPAN = (1.0, 60.0)
ZOOM = 24.0
LEN_BINS = [1, 2, 5, 10, 20, 40, 60, 100, 200, 1e9]
CAP_BINS = [3, 5, 7, 10, 15, 20, 30, 40, 50, 70, 100, 1e9]


def _bin(v, edges):
    lo = 0
    for e in edges:
        if v < e:
            return f"[{lo},{e if e < 1e8 else '∞'})"
        lo = e
    return f"[{lo},∞)"


def _pct(xs, q):
    if not xs:
        return None
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(q * len(xs)))], 2)


def survey(proj):
    name = proj["name"]
    stored = json.loads((RUNS / (name.replace(" ", "_") + ".json")).read_text())["result"]
    kinds = {p["page_no"]: p.get("page_kind") for p in stored["pages"]}
    pid_pages = {p["page_no"] for p in stored["pages"] if p.get("in_scope") and p.get("page_kind") == "PID"}
    legend_pages = {p["page_no"] for p in stored["pages"] if p.get("page_kind") == "LEGEND"}

    # --- 행 사각형 (저장된 결과) ---
    bub_short, body_long, body_short = [], [], []
    for r in stored["rows"]:
        x0, y0, x1, y1 = r["rect"]
        w, h = x1 - x0, y1 - y0
        if r["tab"] == "FIELD":
            bub_short.append(round(min(w, h), 2))
        else:
            body_long.append(round(max(w, h), 2))
            body_short.append(round(min(w, h), 2))

    # --- 도형 (PDF) ---
    doc, pages = pidcache.load_pages(ROOT / proj["pdf"])
    cap_hist = collections.Counter()      # (scope, bin) -> n   scope: pid | legend
    cap_ratio_ok = collections.Counter()  # (scope, bin) -> n with ratio in window
    cap_out = collections.Counter()       # (scope, 'below'|'above') -> n
    seg_hist = collections.Counter()
    seg_n = collections.Counter()
    legend_caps = []                      # legend pages: (long, short) of ratio-ok arcs
    for pc in pages:
        scope = "pid" if pc.page_no in pid_pages else ("legend" if pc.page_no in legend_pages else None)
        if scope is None:
            continue
        for d in pc.drawings():
            items = d["items"]
            if not items or any(i[0] != "c" for i in items):
                continue
            r = d["bbox"]
            w, h = r.width, r.height
            if w <= 0 or h <= 0:
                continue
            short, long_ = min(w, h), max(w, h)
            ratio_ok = CAP_RATIO[0] <= long_ / short <= CAP_RATIO[1]
            b = _bin(long_, CAP_BINS)
            cap_hist[(scope, b)] += 1
            if ratio_ok:
                cap_ratio_ok[(scope, b)] += 1
                if scope == "legend":
                    legend_caps.append((round(long_, 2), round(short, 2), pc.page_no))
            if long_ < CAP_SPAN[0]:
                cap_out[(scope, "below")] += 1
            elif long_ > CAP_SPAN[1]:
                cap_out[(scope, "above")] += 1
        if scope == "pid":
            for a, b_ in pc.segments():
                L = ((a.x - b_.x) ** 2 + (a.y - b_.y) ** 2) ** 0.5
                seg_hist[_bin(L, LEN_BINS)] += 1
                seg_n["total"] += 1
                if L < SEG_SPAN[0]:
                    seg_n["below"] += 1
                elif L > SEG_SPAN[1]:
                    seg_n["above"] += 1
    doc.close()

    # --- 타이틀블록 픽셀 ---
    lay = {i["key"]: i["value"] for i in (stored.get("applied_rules") or {}).get("layout", {}).get("items", [])
           if isinstance(i, dict)}
    rev_box = lay.get("title_block.rev_box")
    title_h = lay.get("title_block.title_min_height")
    px = {
        "rev_box_height_pt": round(rev_box[3] - rev_box[1], 2) if rev_box else None,
        "rev_box_height_px": round((rev_box[3] - rev_box[1]) * ZOOM) if rev_box else None,
        "title_min_height_pt": title_h,
        "title_min_height_px": round(title_h * ZOOM) if title_h else None,
        "char_gap_px_6_in_pt": round(6 / ZOOM, 3),
        "min_ink_px_20_as_square_pt": round((20 ** 0.5) / ZOOM, 3),
    }
    revs = [t.get("rev") for t in (stored.get("titleblocks") or {}).values()] \
        if isinstance(stored.get("titleblocks"), dict) else []

    def fmt(counter, key_scope):
        out = {}
        for (s, b), n in counter.items():
            if s == key_scope:
                out[b] = n
        return dict(sorted(out.items(), key=lambda kv: float(kv[0].split(",")[0][1:])))

    return {
        "name": name,
        "pages": {"pid": len(pid_pages), "legend": len(legend_pages)},
        "rows": {
            "bubble_short": {"n": len(bub_short), "min": min(bub_short) if bub_short else None,
                              "p50": _pct(bub_short, 0.5), "max": max(bub_short) if bub_short else None},
            "body_long": {"n": len(body_long), "min": min(body_long) if body_long else None,
                           "p50": _pct(body_long, 0.5), "max": max(body_long) if body_long else None},
            "body_short": {"min": min(body_short) if body_short else None,
                            "max": max(body_short) if body_short else None},
        },
        "caps_pid": {"all": fmt(cap_hist, "pid"), "ratio_ok": fmt(cap_ratio_ok, "pid"),
                     "below_7": cap_out[("pid", "below")], "above_50": cap_out[("pid", "above")]},
        "caps_legend": {"all": fmt(cap_hist, "legend"), "ratio_ok": fmt(cap_ratio_ok, "legend"),
                        "ratio_ok_list": sorted(legend_caps)},
        "segments_pid": {"hist": dict(sorted(seg_hist.items(), key=lambda kv: float(kv[0].split(",")[0][1:]))),
                         "total": seg_n["total"], "below_1": seg_n["below"], "above_60": seg_n["above"]},
        "titleblock_px": px,
        "rev_filled": f"{sum(1 for v in revs if v)}/{len(revs)}",
    }


def main():
    out = {"_": __doc__.strip().splitlines()[0], "cap_span": CAP_SPAN, "cap_ratio": CAP_RATIO,
           "seg_span": SEG_SPAN, "zoom": ZOOM, "projects": []}
    for proj in PROJECTS:
        print("==", proj["name"], flush=True)
        s = survey(proj)
        out["projects"].append(s)
        print(json.dumps({k: s[k] for k in ("rows", "caps_pid", "segments_pid", "titleblock_px", "rev_filled")},
                         ensure_ascii=False), flush=True)
    (ROOT / "out" / "round37_window_survey.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("written out/round37_window_survey.json")


if __name__ == "__main__":
    main()
