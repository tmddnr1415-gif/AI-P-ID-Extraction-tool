"""어휘를 config 로 옮기고 범위 표기를 막은 것이 무엇을 바꾸는가 — 전 장 실측.

    python3 spike/note_vocab_delta.py <pdf>

27회차 첫 구현(코드에 박힌 `IDENTICAL|SIMILAR|SAME` · 범위 무시)과 지금
(`qty_note` 어휘 + 범위 표기 보류)을 **같은 장에서 나란히** 센다.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))

import pidcache                       # noqa: E402
import derive_layout as dl            # noqa: E402
import detect_symbols as ds           # noqa: E402
import projectconfig as pcfg          # noqa: E402
from app import pipeline              # noqa: E402


class Shim:
    def __init__(self, data):
        self.data = data


OLD = Shim({"qty_note": {"same_words": ["IDENTICAL", "SIMILAR", "SAME"],
                         "unit_words": ["GROUP", "UNIT", "TRAIN"],
                         "range_words": []}})


def main() -> int:
    pdf = sys.argv[1]
    _doc, pages = pidcache.load_pages(pdf)
    pipeline.CFG.overlay(dl.derive(pages, pipeline.CFG).values())
    pipeline._rebind_config()
    L = ds.LAYOUT
    moved = 0
    for pc in pages:
        a = pcfg.note_unit_span(pc, L.notes_area, L.notes_text_x_max, cfg=OLD)
        b = pcfg.note_unit_span(pc, L.notes_area, L.notes_text_x_max,
                                cfg=pipeline.CFG)
        if tuple(a) == tuple(b):
            continue
        moved += 1
        print("  p%-3d  옛 %s%s   →   새 %s%s"
              % (pc.page_no, a.count, "" if not a.ambiguous else "(범위)",
                 b.count, "" if not b.ambiguous else "(범위)"))
        print("        %s" % b.text[:150])
    print("%s — 달라진 장 %d / %d" % (Path(pdf).name, moved, len(pages)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
