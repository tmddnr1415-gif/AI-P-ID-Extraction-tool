"""그 장 NOTES 가 "이 도면은 유닛 몇 개에 같이 쓰인다" 고 말하는가 — 전 장 실측.

    python3 spike/unit_notes.py <pdf> [최대 장수]

§9 ② — 도면이 스스로 말하는 자리다.  **세는 것이지 해석하지 않는다**: 그 노트가
열거한 유닛·그룹 표기를 모아 개수를 낸다.

세 가지를 실측으로 다뤘다 (전부 TC2 에서 나온 것):
  · `_notes_lines` 의 7pt 버킷이 **두 줄을 한 줄로 묶어** 낱말을 섞는다
    (p7: `5. UNIT THIS 5-2, P&ID UNIT IS FOR 6-1, ...`).  줄 간격 중앙값이 9.3~11.2pt
    인데 버킷이 7pt 라서다.  여기서는 **같은 y** 끼리만 묶는다.
  · p10·p12 는 같은 글자를 **두 번 인쇄**한다 (`GENERAL GENERAL NOTES NOTES`).
    같은 자리의 같은 낱말은 하나로 본다.
  · 문형이 둘이다 — `THIS P&ID IS FOR UNIT 3-1. AND, SIMILAR SCHEME IS APPLICABLE
    TO UNIT 3-2, …` (p7) 와 `UNITS … SHALL BE IDENTICAL TO UNIT 3-1 AS SHOWN IN
    THIS P&ID` (p11).  그래서 문장 모양이 아니라 **문단 단위로 센다**.
"""
from __future__ import annotations

import collections
import re
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

# "같다" 를 말하는 낱말.  영어 어휘이지 프로젝트 값이 아니다 (`projectconfig._PLANT`
# ·`_GROUP`·`_UNIT` 과 같은 성격).
SAME = re.compile(r"\b(IDENTICAL|SIMILAR|SAME)\b")
# 유닛 표기.  낱말 뒤의 **꼬리까지** 읽는다 — 옛 스파이크(`parse_notes.GROUP_REF`)가
# 주석으로 경고해 둔 자리다: `UNIT#12,21,22` 에서 꼬리를 버리면 4를 2로 센다.
# 두 모양을 다 본다: `#10`·`12,21,22` (AL NOUF1) · `3-1`·`3 & 4` (TC2).
_NUM = r"\d{1,2}(?:\s*-\s*\d{1,2})?"
UNIT_HEAD = re.compile(r"(?:GROUP|UNIT|TRAIN)S?\s*#?\s*(%s)" % _NUM)
UNIT_TAIL = re.compile(r"\s*(?:,|&|AND)\s*#?\s*(%s)" % _NUM)


def unit_tokens(text: str):
    """그 문단이 열거한 유닛 표기 — 낱말 하나에 이어지는 목록까지."""
    out = []
    for m in UNIT_HEAD.finditer(text):
        out.append(m.group(1))
        pos = m.end()
        while True:
            t = UNIT_TAIL.match(text, pos)   # `^` 를 쓰면 안 된다 — match(pos) 가 이미 그 자리다
            if not t:
                break
            out.append(t.group(1))
            pos = t.end()
    return [re.sub(r"\s+", "", t) for t in out]
NUMBERED = re.compile(r"^\d+\.")


def notes_paragraphs(pc, lay):
    """그 장 NOTES 를 문단으로 — 줄은 **같은 y**, 겹쳐 인쇄된 낱말은 하나로."""
    x0, y0, _x1, y1 = lay.notes_area
    sel = [(r, t) for r, t in pc.words
           if x0 <= r.x0 <= lay.notes_text_x_max and y0 <= r.y0 <= y1]
    rows, seen = collections.defaultdict(list), set()
    for r, t in sel:
        key = (round(r.x0, 1), round(r.y0, 1), t)
        if key in seen:                      # 같은 자리에 같은 낱말 = 덧인쇄
            continue
        seen.add(key)
        rows[round(r.y0, 1)].append((r.x0, t))
    lines = [" ".join(t for _x, t in sorted(rows[y])) for y in sorted(rows)]
    paras, cur = [], ""
    for ln in lines:
        if NUMBERED.match(ln.strip()):
            if cur:
                paras.append(cur)
            cur = ln
        elif cur:
            cur += " " + ln
        else:
            cur = ln
    if cur:
        paras.append(cur)
    return paras


def page_units(pc, lay):
    """`(유닛 표기 목록, 그 문단)` — 같다는 낱말과 표기 둘 이상이 한 문단에 있을 때."""
    best = ([], "")
    for p in notes_paragraphs(pc, lay):
        up = re.sub(r"\s+", " ", p.upper())
        if not SAME.search(up):
            continue
        toks = list(dict.fromkeys(unit_tokens(up)))
        if len(toks) >= 2 and len(toks) > len(best[0]):
            best = (toks, up)
    return best


def main() -> int:
    pdf = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10**9
    doc, pages = pidcache.load_pages(pdf)
    pipeline.CFG.overlay(dl.derive(pages, pipeline.CFG).values())
    pipeline._rebind_config()
    L = ds.LAYOUT
    um = pcfg.derive_unit_multipliers(pages, pipeline.CFG)
    print("## %s — 승수표 %s %s" % (Path(pdf).name, um.source, um.table))
    seen = collections.Counter()
    import extract_titleblocks as tb
    agree = collections.Counter()
    for pc in pages[:limit]:
        toks, para = page_units(pc, L)
        if not toks:
            continue
        seen[len(toks)] += 1
        # 그 장 도면번호의 유닛 코드로 범례 승수를 뽑아 나란히 놓는다
        code = ""
        for r, t in pc.words:
            m = re.match(r"^[A-Z0-9]+-(\d\d)[A-Z]", t)
            if m:
                code = m.group(1)
                break
        legend = um.table.get(code)
        agree[(len(toks), legend)] += 1
        print("  p%-3d 유닛 %d개 %-44s 범례 %s(코드 %s)"
              % (pc.page_no, len(toks), toks, legend, code or "?"))
    print("노트가 있는 장 %d · 개수 분포 %s" % (sum(seen.values()), dict(seen)))
    print("(노트 개수, 범례 승수) → 장수:", dict(agree))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
