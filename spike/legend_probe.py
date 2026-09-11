"""그 문서의 범례에서 무엇이 읽히고 무엇이 안 읽히는가 — 한 번에 진단한다.

    python3 spike/legend_probe.py <pdf>

28회차.  범례 유도는 항목이 여러 개인데 파이프라인은 그중 하나(`min_run`)가
비면 멈춘다.  어느 항목이 왜 안 읽혔는지 한 번의 적재로 전부 본다.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))

import pidcache            # noqa: E402
import legend_rules as lr  # noqa: E402
import pipe_graph          # noqa: E402
import isa_table           # noqa: E402
import describe_equipment as dequip   # noqa: E402
import projectconfig as pcfg          # noqa: E402
from app import pipeline              # noqa: E402


def main() -> int:
    pdf = sys.argv[1]
    _doc, pages = pidcache.load_pages(pdf)
    cfg = pipeline.CFG
    print("## %s — %d장" % (Path(pdf).name, len(pages)))
    for head in (lr.LINE_VALVE_HEADING, lr.ACTUATOR_HEADING, pipe_graph.SIGNAL_ROW):
        pc = lr._page_with(pages, head)
        print("  머리말 %-18s → %s" % (head, ("p%d" % pc.page_no) if pc else "★ 못 찾음"))
    checks = [
        ("butterfly", lambda: lr.derive_butterfly(pages, cfg)),
        ("actuator_stem", lambda: lr.derive_actuator_stem(pages, cfg)),
        ("pneumatic", lambda: lr.derive_pneumatic(pages, cfg)),
        ("line_styles", lambda: pipe_graph.derive_line_styles(pages, cfg)),
    ]
    for name, fn in checks:
        try:
            d = fn()
        except Exception as exc:                       # noqa: BLE001
            print("  %-14s ★ 예외 %s" % (name, exc))
            continue
        print("  %-14s %-8s %s" % (name, d.source, (d.note or "")[:96]))
        if d.values:
            print("      값: %s" % {k: v for k, v in list(d.values.items())[:5]})
    try:
        isa = isa_table.derive(pages, cfg)
        print("  isa_table      %-8s 첫문자 %d · 후속문자 %d · %s"
              % (isa.source, len(isa.first or {}), len(isa.succeeding or {}), (isa.note or "")[:80]))
        if isa.first:
            print("      예: %s" % list(isa.first.items())[:4])
    except Exception as exc:                            # noqa: BLE001
        print("  isa_table      ★ 예외 %s" % exc)
    try:
        eq = dequip.derive_symbols(pages, cfg)
        print("  equipment      %d행 · 예 %s" % (len(eq), [getattr(x, "label", x) for x in eq[:3]]))
        print("  머리말 불일치  %s" % (dequip.heading_mismatch(pages) or "없음"))
    except Exception as exc:                            # noqa: BLE001
        print("  equipment      ★ 예외 %s" % exc)
    try:
        um = pcfg.derive_unit_multipliers(pages, cfg)
        print("  승수표         %s %s" % (um.source, um.table))
    except Exception as exc:                            # noqa: BLE001
        print("  승수표         ★ 예외 %s" % exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
