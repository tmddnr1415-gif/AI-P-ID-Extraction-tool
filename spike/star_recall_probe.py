"""47회차 [B] — 그 장이 인쇄한 별표 중 마크가 되지 못한 것을 센다.

46회차 [E] ㉣ 가 TC2 p9 에서 **별표 하나가 조용히 빠지는 것**을 찾았다
(TIT 세 버블 모두 위에 `*` 가 있는데 마크는 그중 둘만).  소유자 판정
(19회차 `_mark_gap`)의 문제가 아니라 **찾지 못한 것**이므로, 세는 채널은
검출기와 **다른 재료**여야 한다 — 26회차 `tests/test_star_marks.py` 의
재현율 채널(`_midpoint_clusters`)을 그대로 쓴다: 중점이 겹치고 방향이 셋
이상이며 팔 길이가 같은 짧은 획 무리.  `star_groups` 도 자유 끝점도 크기
학습도 보지 않는다.

    python3 spike/star_recall_probe.py <이름> <PDF> [장,장,...]

★ 실 DB 를 열지 않는다 (17회차 격리) — PDF 만 읽는다.
★ config 는 이 프로세스 안에서만 얹고 끝에 되돌린다 (22회차).
"""
from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))

from app.engine import detect_symbols as ds       # noqa: E402
from app.engine import pidcache                    # noqa: E402


def midpoint_clusters(pc, maxlen):
    """tests/test_star_marks.py 의 채널과 같은 규칙 (검출기 함수 0개)."""
    m = pc.page.rotation_matrix
    segs = []
    for d in pc.drawings():
        for it in d["items"]:
            if it[0] != "l":
                continue
            a, b = it[1] * m, it[2] * m
            ln = math.hypot(b.x - a.x, b.y - a.y)
            if 0 < ln <= maxlen:
                segs.append(((a.x + b.x) / 2, (a.y + b.y) / 2, ln,
                             int(math.degrees(math.atan2(b.y - a.y, b.x - a.x))
                                 % 180 // 15)))
    segs.sort()
    out, used = [], [False] * len(segs)
    for i, s in enumerate(segs):
        if used[i]:
            continue
        group = [i]
        for j in range(i + 1, len(segs)):
            if used[j] or segs[j][0] - s[0] > maxlen:
                break
            tol = 0.25 * min(s[2], segs[j][2])
            if math.hypot(segs[j][0] - s[0], segs[j][1] - s[1]) <= tol:
                group.append(j)
        if len(group) < 3:
            continue
        for j in group:
            used[j] = True
        lens = [segs[j][2] for j in group]
        if len({segs[j][3] for j in group}) >= 3 and max(lens) / min(lens) <= 1.1:
            out.append((round(s[0], 2), round(s[1], 2), len(group),
                        round(sum(lens) / len(lens), 2)))
    return out


def probe(name, pdf, wanted=None):
    import derive_layout as dl
    from app import pipeline

    snapshot = copy.deepcopy(pipeline.CFG.data)
    try:
        doc, pages = pidcache.load_pages(pdf)
        pipeline.CFG.overlay(dl.derive(pages, pipeline.CFG).values())
        pipeline._rebind_config()
        lay = ds.LAYOUT
        rows = []
        for pc in pages:
            if wanted and pc.page_no not in wanted:
                continue
            if not pc.analysis_scope:
                continue
            outlines = ds.bubble_outlines(pc, lay)
            bubbles = ds.find_bubbles(pc, lay)
            if not bubbles:
                ds.release_ink()
                continue
            dct, gsize = ds.read_mark_dictionary(pc, lay)
            marks = ds.find_marks(
                pc, lay, glyph_size=gsize if isinstance(gsize, tuple) else None,
                allow_sizes=ds.KNOWN_GLYPH_SIZES, bubbles=bubbles)
            short = sorted(min(b.width, b.height) for b in bubbles)
            printed = [c for c in midpoint_clusters(pc, short[len(short) // 2])
                       if any(ds.in_mark_window(b, c[0], c[1], lay) for b in bubbles)]
            # ★ 크기 투표의 실물 — 반올림 전 값을 그대로 적는다 (47회차 [B]).
            groups = ds.star_groups(pc, lay, short[len(short) // 2], min_dirs=3)
            votes = []
            for r, n, dirs in groups:
                gx, gy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
                if r.x1 > lay.drawing_area[2]:
                    continue
                if ds.on_bubble_face(gx, gy, outlines):
                    continue
                if not any(ds.in_mark_window(b, gx, gy, lay) for b in bubbles):
                    continue
                votes.append({"w": round(r.width, 4), "h": round(r.height, 4),
                              "key": [round(r.width, 1), round(r.height, 1)],
                              "x": round(gx, 2), "y": round(gy, 2)})
            missed = []
            for cx, cy, n, ln in printed:
                near = min((math.hypot(mk.x - cx, mk.y - cy) for mk in marks),
                           default=1e9)
                if near > 2.0:
                    missed.append({"x": cx, "y": cy, "arms": n, "arm_len": ln,
                                   "nearest_mark_pt": round(near, 2)})
            rows.append({"page": pc.page_no, "bubbles": len(bubbles),
                         "marks": len(marks), "printed": len(printed),
                         "missed": missed, "votes": votes})
            ds.release_ink()
        doc.close()
        return rows
    finally:
        if pipeline.CFG.data != snapshot:
            pipeline.CFG.data = snapshot
            pipeline._rebind_config()


def main() -> int:
    name, pdf = sys.argv[1], Path(sys.argv[2])
    wanted = {int(x) for x in sys.argv[3].split(",")} if len(sys.argv) > 3 else None
    rows = probe(name, pdf, wanted)
    total = sum(len(r["missed"]) for r in rows)
    out = {"project": name, "pages": len(rows),
           "printed": sum(r["printed"] for r in rows),
           "marks": sum(r["marks"] for r in rows),
           "missed_total": total,
           "pages_with_missed": [r for r in rows if r["missed"]],
           "votes_by_page": {r["page"]: r["votes"] for r in rows if r["votes"]}}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
