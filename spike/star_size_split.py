"""47회차 [B] — 같은 크기가 반올림 칸에서 갈려 "두 번 그려졌다" 를 못 세는 것.

`star_marks` 는 크기를 **배울 때**는 `(round(w,1), round(h,1))` 이라는 반올림 칸을
쓰고, `find_marks` 는 크기를 **맞출 때** `±0.6pt` 를 쓴다.  즉 같은 자에 대해
재는 곳과 맞추는 곳의 눈금이 12배 다르다.  한 물리 크기(TC2 p9 의 2.88)가
(2.8,2.9)·(2.8,2.8)·(2.9,2.8)·(2.9,2.9) 네 칸으로 갈리면, 11번 그려진 별표가
"한 번뿐" 인 칸을 하나 만들고 그 별표만 조용히 빠진다 (46회차 [E] ㉣).

이 도구는 **세기만 한다** — 그 장의 마크 창에 든 `star_groups` 결과를 모아
칸별로 세고, `n==1` 인 칸이 배운 칸과 맞추기 허용치 안인지 본다.

    python3 spike/star_size_split.py <이름> <PDF>

★ 실 DB 를 열지 않는다 · config 는 끝에 되돌린다.
"""
from __future__ import annotations

import collections
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))

from app.engine import detect_symbols as ds       # noqa: E402
from app.engine import pidcache                    # noqa: E402

MATCH_TOL = 0.6          # find_marks 가 "같은 크기" 라고 부르는 허용치


def main() -> int:
    name, pdf = sys.argv[1], Path(sys.argv[2])
    import derive_layout as dl
    from app import pipeline

    snap = copy.deepcopy(pipeline.CFG.data)
    pages_out, doc = [], None
    try:
        doc, pages = pidcache.load_pages(pdf)
        pipeline.CFG.overlay(dl.derive(pages, pipeline.CFG).values())
        pipeline._rebind_config()
        lay = ds.LAYOUT
        for pc in pages:
            if not pc.analysis_scope:
                continue
            outlines = ds.bubble_outlines(pc, lay)
            bubbles = [o.rect for o in outlines]
            if not bubbles:
                ds.release_ink()
                continue
            short = sorted(min(b.width, b.height) for b in bubbles)
            groups = ds.star_groups(pc, lay, short[len(short) // 2], min_dirs=3)
            votes = []
            for r, _n, _d in groups:
                if r.x1 > lay.drawing_area[2]:
                    continue
                cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
                if ds.on_bubble_face(cx, cy, outlines):
                    continue
                if not any(ds.in_mark_window(b, cx, cy, lay) for b in bubbles):
                    continue
                votes.append((round(r.width, 4), round(r.height, 4),
                              round(cx, 2), round(cy, 2)))
            ds.release_ink()
            if not votes:
                continue
            seen = collections.Counter((round(w, 1), round(h, 1))
                                       for w, h, _x, _y in votes)
            learned = {k for k, n in seen.items() if n >= 2}
            # 배운 칸과 **맞추기 허용치 안**인데 칸이 갈려 버려진 것
            split = []
            for w, h, x, y in votes:
                key = (round(w, 1), round(h, 1))
                if key in learned:
                    continue
                if any(abs(key[0] - a) <= MATCH_TOL and abs(key[1] - b) <= MATCH_TOL
                       for a, b in learned):
                    split.append({"x": x, "y": y, "w": w, "h": h, "key": list(key)})
            pages_out.append({
                "page": pc.page_no, "votes": len(votes),
                "buckets": {f"{a}x{b}": n for (a, b), n in sorted(seen.items())},
                "learned": [list(k) for k in sorted(learned)],
                "split_lost": split,
            })
        print(json.dumps({
            "project": name,
            "pages_with_votes": len(pages_out),
            "votes_total": sum(p["votes"] for p in pages_out),
            "split_lost_total": sum(len(p["split_lost"]) for p in pages_out),
            "pages": [p for p in pages_out if p["split_lost"]],
            "all_pages": pages_out,
        }, ensure_ascii=False, indent=1))
    finally:
        if doc is not None:
            doc.close()
        if pipeline.CFG.data != snap:
            pipeline.CFG.data = snap
            pipeline._rebind_config()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
