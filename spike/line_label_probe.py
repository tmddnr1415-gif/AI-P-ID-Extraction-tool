"""hotfix36 시제품 — 상자 안 두 줄 라벨(라인 번호)을 한 장에서 찾아 런에 붙여 본다.

    python3 spike/line_label_probe.py data/QFE_260326.pdf 46 [더 많은 쪽…]

파이프라인에 넣기 전 측정용.  규칙은 전부 **그 라벨 자신의 글자 높이** 배율이다.
"""
from __future__ import annotations

import collections
import pathlib
import sys

import pymupdf

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "app" / "engine"))
import pidcache, legend_rules, pipe_graph                      # noqa: E402
import describe_candidates as dcand                            # noqa: E402
import describe_axis as daxis                                  # noqa: E402
import projectconfig                                           # noqa: E402
from app.engine import tags as tagsys                          # noqa: E402

CFG = projectconfig.load()


def fragments(words):
    """같은 기준선 · 글자 높이의 1/4 보다 좁은 틈으로 이어진 낱말을 하나로 (조각 잇기)."""
    ws = sorted(((pymupdf.Rect(r), t) for r, t in words), key=lambda w: (round(w[0].y0, 1), w[0].x0))
    out, gaps_in, gaps_out = [], [], []
    for r, t in ws:
        if out:
            pr, pt = out[-1]
            h = max(pr.height, r.height)
            same = abs(r.y0 - pr.y0) < 0.3 * h and abs(r.y1 - pr.y1) < 0.3 * h
            gap = r.x0 - pr.x1
            if same:
                (gaps_in if gap <= 0.25 * h else gaps_out).append(round(gap / h, 2))
            if same and gap <= 0.25 * h:
                out[-1] = (pr | r, pt + t)
                continue
        out.append((r, t))
    return out, gaps_in, gaps_out


def boxed_pairs(frags, horiz, vert):
    """위·아래로 쌓인 두 조각이 **그려진 사각형** 안에 있는 것."""
    def hspan(y_lo, y_hi, x0, x1, tol):
        for y, segs in horiz.items():
            if y_lo <= y <= y_hi:
                for a, b in segs:
                    if a <= x0 + tol and b >= x1 - tol:
                        return y
        return None
    def vspan(x_lo, x_hi, y0, y1, tol):
        for x, segs in vert.items():
            if x_lo <= x <= x_hi:
                for a, b in segs:
                    if a <= y0 + tol and b >= y1 - tol:
                        return x
        return None
    out = []
    for i, (ra, ta) in enumerate(frags):
        if not tagsys._is_code(ta) and not ta.isalnum():
            continue
        h = ra.height
        for rb, tb in frags:
            if rb is ra:
                continue
            if not (0 <= rb.y0 - ra.y1 <= 1.2 * h and abs(rb.x0 - ra.x0) < 3 * h and min(rb.x1, ra.x1) - max(rb.x0, ra.x0) > 0):
                continue
            U = ra | rb
            top = hspan(U.y0 - h, U.y0, U.x0, U.x1, h)
            bot = hspan(U.y1, U.y1 + h, U.x0, U.x1, h)
            if top is None or bot is None:
                continue
            left = vspan(U.x0 - h, U.x0, top, bot, h)
            right = vspan(U.x1, U.x1 + h, top, bot, h)
            if left is None or right is None:
                continue
            box = pymupdf.Rect(left, top, right, bot)
            out.append({"text": ta + tb, "top": ta, "bottom": tb, "rect": U, "box": box, "h": h})
    return out


def attach_runs(labels, runs):
    for L in labels:
        B, h = L["box"], L["h"]
        hits = []
        for axis, coord, lo, hi in runs:
            if axis == "H":
                for edge, side in ((B.y1, "bottom"), (B.y0, "top")):
                    if abs(coord - edge) <= h and min(hi, B.x1) - max(lo, B.x0) > 0:
                        hits.append((abs(coord - edge), side, (axis, coord, lo, hi)))
            else:
                for edge, side in ((B.x0, "left"), (B.x1, "right")):
                    if abs(coord - edge) <= h and min(hi, B.y1) - max(lo, B.y0) > 0:
                        hits.append((abs(coord - edge), side, (axis, coord, lo, hi)))
        hits.sort(key=lambda t: t[0])
        L["run"] = hits[0][2] if hits else None
        L["side"] = hits[0][1] if hits else ""
        L["run_hits"] = len(hits)
    return labels


def main():
    pdf = sys.argv[1]; pages_wanted = [int(a) for a in sys.argv[2:]]
    _doc, pages = pidcache.load_pages(pdf)
    style = dict(pipe_graph.derive_line_styles(pages, CFG).values)
    print("style join_slack", style.get("join_slack"), "min_run", style.get("min_run"))
    by_no = {pc.page_no: pc for pc in pages}
    for pno in pages_wanted:
        pc = by_no[pno]
        frags, gi, go = fragments(pc.words)
        horiz, vert = legend_rules.stroke_index(pc.segments(), min_len=1.0)
        labels = boxed_pairs(frags, horiz, vert)
        runs = daxis.bridge_collinear(*dcand.local_runs(pc, style)[:1], style["join_slack"],
                                      daxis.standard_break(dcand.local_runs(pc, style)[0], style["join_slack"]))
        attach_runs(labels, runs)
        print(f"\n== p{pno}: 낱말 {len(pc.words)} → 조각 {len(frags)} · 상자 라벨 {len(labels)} · 런 {len(runs)}")
        print("   틈/높이 — 이은 것", collections.Counter(gi).most_common(6), "| 띄운 것 최소", sorted(set(go))[:6])
        for L in labels:
            print(f"   {L['text']:16s} box {[round(v,1) for v in L['box']]} run {L['run'] and [round(v,1) if isinstance(v,float) else v for v in L['run']]} {L['side']} hits {L['run_hits']}")
        shapes = collections.Counter(tagsys.shape(L["text"]) for L in labels)
        print("   모양", shapes.most_common(5))


if __name__ == "__main__":
    main()
