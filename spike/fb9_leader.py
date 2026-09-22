"""9차 [A] — 태그 버블의 **지시선**이 어느 몸체를 가리키나 (54회차).

도면은 버블에서 그 밸브까지 선을 하나 긋는다.  지금 `attach_tags` 는 그 선을
읽지 않고 **가장 가까운 몸체**를 준다 (`tag_reach` 190.0pt — AL NOUF1 p6 에서
잰 절대 pt · §9 위반).  이 도구는 두 답을 나란히 낸다.  측정만 한다.

읽는 방법은 한 걸음이다 (§2.3 순회 아님 — `describe_axis.pick_tap` 과 같다):
버블 테두리에 한쪽 끝이 있고 다른 끝이 밖에 있는 **선분 하나**를 고르고,
그 먼 끝이 **들어 있는** 몸체를 본다.  허용치를 새로 두지 않는다 —
'들어 있다' 는 포함 판정이다.

    python3 spike/fb9_leader.py data/TC2_260821.pdf
"""
from __future__ import annotations

import collections
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app" / "engine"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pymupdf                                           # noqa: E402
import pidcache                                          # noqa: E402
import detect_valves as dv                               # noqa: E402


def leaders(pc, bub, slack=0.0) -> list:
    """버블 테두리를 한 번 넘는 선분 — 긴 것부터.

    `slack` 은 **그려진 테두리와 캡 사각형의 차이**다 (실측 0.14~0.24pt — 선 굵기
    때문이다).  `bubble_outlines` 가 같은 차이를 `side_slack` 으로 이미 다룬다.
    """
    m = pc.page.rotation_matrix
    r = pymupdf.Rect(bub.x0 - slack, bub.y0 - slack, bub.x1 + slack, bub.y1 + slack)
    out = []
    for d in pc.drawings():
        for it in d["items"]:
            if it[0] != "l":
                continue
            a, c = it[1] * m, it[2] * m
            a_in, c_in = r.contains(a), r.contains(c)
            if a_in == c_in:
                continue
            far = c if a_in else a
            ln = math.hypot(c.x - a.x, c.y - a.y)
            if ln < 1.0:
                continue
            out.append((ln, far))
    out.sort(key=lambda t: -t[0])
    return out


def main() -> int:
    pdf = sys.argv[1]
    doc, pages = pidcache.load_pages(pdf)
    lay, _ = dv.derive_layout(pages)
    dv.LAYOUT = lay
    tot = collections.Counter()
    lines = []
    for pc in pages:
        tags = dv.bubble_tags(pc, lay)
        if not tags:
            continue
        bodies = dv.find_bodies(pc, lay)
        dv.attach_actuators(pc, bodies, lay)
        for text, bub in tags:
            tot["tags"] += 1
            led = leaders(pc, bub, slack=lay.side_slack)
            bx = (bub.x0 + bub.x1) / 2
            by = (bub.y0 + bub.y1) / 2
            near, near_d = None, None
            for b in bodies:
                cx = (b.rect.x0 + b.rect.x1) / 2
                cy = (b.rect.y0 + b.rect.y1) / 2
                d = math.hypot(cx - bx, cy - by)
                if d > lay.tag_reach:
                    continue
                if near_d is None or d < near_d:
                    near, near_d = b, d
            hit = None
            if led:
                far = led[0][1]
                for b in bodies:
                    if b.rect.contains(far):
                        hit = b
                        break
            if not led:
                tot["no_leader"] += 1
            elif hit is None:
                tot["leader_hits_nothing"] += 1
            elif near is hit:
                tot["same"] += 1
            else:
                tot["differ"] += 1
            lines.append((pc.page_no, text, len(led),
                          round(led[0][0], 1) if led else None,
                          (near.kind if near else None),
                          (hit.kind if hit else None),
                          round(near_d, 1) if near_d is not None else None))
    print(pdf, dict(tot))
    for ln in lines:
        print("   p%-3d %-5s leaders=%d len=%s  nearest=%s  leader=%s  neard=%s" % ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
