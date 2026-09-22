"""8차 피드백 조사 — 밸브 태그 버블이 몸체와 왜 안 짝지어지나.

    python3 spike/fb8_probe.py 8 12 21

그 장만 열어(46회차 `only=`) 밸브 태그 버블과 몸체를 세고, 짝이 안 맞는
버블마다 **가장 가까운 몸체까지의 거리**를 적는다.  짝짓기 규칙은
`attach_tags` 그대로이고 사본을 두지 않는다.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))

from app import pipeline as P                    # noqa: E402
import pidcache as pcmod                         # noqa: E402
import detect_valves as dv                       # noqa: E402
import detect_symbols as ds                      # noqa: E402


def main(pages):
    pdf = ROOT / "data" / "pid_total.pdf"
    doc, pcs = pcmod.load_pages(str(pdf))
    P._reconfigure(pcs)
    lay, _prov = dv.derive_layout(pcs)
    dv.LAYOUT = lay
    for pc in pcs:
        if pc.page_no not in pages:
            continue
        tags = dv.bubble_tags(pc, lay)
        bodies = dv.find_bodies(pc, lay)
        dv.attach_actuators(pc, bodies, lay)
        paired = dv.attach_tags(pc, bodies, lay)   # 몸체에 tag 를 심는다
        got = {id(b) for b in bodies if b.tag}
        print("=" * 72)
        print("p%-3d 태그 버블 %2d · 몸체 %3d · 짝지어진 몸체 %2d"
              % (pc.page_no, len(tags), len(bodies), len(got)))
        for text, bub in tags:
            bx, by = (bub.x0 + bub.x1) / 2, (bub.y0 + bub.y1) / 2
            mine = [b for b in bodies if b.tag == text and b.tag_rect
                    and abs(b.tag_rect[0] - bub.x0) < 0.5]
            near = sorted(
                ((((b.rect.x0 + b.rect.x1) / 2 - bx) ** 2
                  + ((b.rect.y0 + b.rect.y1) / 2 - by) ** 2) ** 0.5, b)
                for b in bodies)
            d0, b0 = near[0] if near else (None, None)
            mark = "짝O" if mine else "짝X"
            print("  %s %-5s (%7.1f,%7.1f)  최근접 몸체 %s %s  거리 %s  (한계 %.0f)"
                  % (mark, text, bx, by,
                     getattr(b0, "kind", "-"), getattr(b0, "actuator", "-"),
                     ("%.1f" % d0) if d0 is not None else "-", lay.tag_reach))
    doc.close()


if __name__ == "__main__":
    main({int(a) for a in sys.argv[1:]} or {8, 12, 21})
