"""8차 피드백 [B] 영향 범위 — 태그 버블이 붙었는데 산출물에서 빠지는 몸체.

    python3 spike/fb8_census.py                 # AL NOUF1
    python3 spike/fb8_census.py <pdf> <이름>

무엇을 세는가 (고치기 전에 잰다 — §9)
    ① 그 도면이 버블에 인쇄한 밸브 태그 수
    ② 그 태그가 몸체와 짝지어진 수 (`attach_tags` 그대로)
    ③ 짝지어졌는데 `deliverable_class` 가 EXCLUDED 인 수 ← **늘어날 행**
       그 사유(액추에이터 NONE / UNREAD / 그 밖)까지 가른다
    ④ 태그가 **없는** 몸체 중 EXCLUDED 인 수 ← 규칙이 이것을 건드리면 안 된다
    ⑤ 맞닿은 버블 묶음 중 밸브 태그를 품은 묶음 (ZSC·ZSO·XV 같은 스택)
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))

from app import pipeline as P                    # noqa: E402
import pidcache as pcmod                         # noqa: E402
import detect_valves as dv                       # noqa: E402
import detect_symbols as ds                      # noqa: E402


def main(pdf: str, name: str) -> int:
    doc, pcs = pcmod.load_pages(pdf)
    P._reconfigure(pcs)
    dv.LAYOUT, _prov = dv.derive_layout(pcs)
    lay = dv.LAYOUT
    scope = {p.page_no for p in pcs}

    printed = collections.Counter()
    paired_excluded = collections.Counter()
    paired_excluded_why = collections.Counter()
    paired_kept = collections.Counter()
    untagged_excluded = 0
    untagged_total = 0
    unpaired = collections.Counter()
    stacks = 0
    stack_detail = collections.Counter()
    rows_pages = []

    for pc in pcs:
        try:
            tags = dv.bubble_tags(pc, lay)
        except Exception as e:                    # 범례 장 등
            continue
        if not tags:
            pass
        bodies = dv.find_bodies(pc, lay)
        dv.attach_actuators(pc, bodies, lay)
        dv.attach_tags(pc, bodies, lay)
        for text, _b in tags:
            printed[text] += 1
        seen = set()
        for b in bodies:
            cls = dv.deliverable_class(b)
            if b.tag:
                seen.add(b.tag)
                if cls == dv.CLASS_EXCLUDED:
                    paired_excluded[b.tag] += 1
                    paired_excluded_why[b.actuator] += 1
                else:
                    paired_kept[b.tag] += 1
            else:
                untagged_total += 1
                if cls == dv.CLASS_EXCLUDED:
                    untagged_excluded += 1
        got = sum(1 for b in bodies if b.tag)
        if got < len(tags):
            unpaired["p%d" % pc.page_no] += len(tags) - got

        # ⑤ 맞닿은 버블 묶음에 밸브 태그가 섞여 있는가
        bubs = ds.find_bubbles(pc, ds.LAYOUT)
        words = pc.words
        def label(bub):
            top = [(r, t) for r, t in words
                   if bub.x0 - 2 <= r.x0 and r.x1 <= bub.x1 + 2
                   and bub.y0 - bub.height * 0.25 <= r.y0
                   and r.y1 <= bub.y0 + bub.height * 0.7]
            top.sort(key=lambda rt: rt[0].x0)
            return "".join(t for _, t in top).strip()
        lab = [(label(b), b) for b in bubs]
        for i, (t1, b1) in enumerate(lab):
            if t1 not in dv.TAG_ANCHORS:
                continue
            near = [t2 for t2, b2 in lab
                    if b2 is not b1 and t2
                    and abs((b1.x0 + b1.x1) / 2 - (b2.x0 + b2.x1) / 2) < b1.width * 0.5
                    and 0 < abs(b1.y0 - b2.y1) + 0 < b1.height * 0.6 + abs(b1.y0 - b2.y1) * 0
                    and min(abs(b1.y0 - b2.y1), abs(b2.y0 - b1.y1)) < b1.height * 0.4]
            if near:
                stacks += 1
                stack_detail[(t1, tuple(sorted(near)))] += 1
    doc.close()

    out = {
        "project": name,
        "printed_valve_tags": dict(printed), "printed_total": sum(printed.values()),
        "paired_kept": dict(paired_kept), "paired_kept_total": sum(paired_kept.values()),
        "paired_excluded": dict(paired_excluded),
        "paired_excluded_total": sum(paired_excluded.values()),
        "paired_excluded_why": dict(paired_excluded_why),
        "unpaired_by_page": dict(unpaired), "unpaired_total": sum(unpaired.values()),
        "untagged_bodies": untagged_total, "untagged_excluded": untagged_excluded,
        "tag_stacks": stacks,
        "tag_stack_detail": {"%s <- %s" % (k[0], ",".join(k[1])): v
                             for k, v in stack_detail.most_common(25)},
    }
    dest = ROOT / "out" / "round53" / ("census_%s.json" % name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    raise SystemExit(main(a[0] if a else "data/pid_total.pdf",
                          a[1] if len(a) > 1 else "AL_NOUF1"))
