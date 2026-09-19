"""증거 등급 — 그 장이 태그를 주는가.  **저장된 결과 + 원본 PDF 로 잰다.**

    python3 spike/tier_survey.py

§10.  등급 판정은 도면에서 잰다 — 프로젝트 이름·크기·파일명으로 가르지 않는다.

무엇을 보는가
    행마다 그 검출의 사각형이 있다 (버블/몸체).  그 안에 인쇄된 낱말을 원본
    PDF 에서 그대로 읽어, **글자와 숫자가 함께 든 낱말**(= 코드)이 있으면 그
    검출은 "태그가 붙어 있다" 고 센다.  기능 코드(`LIT`·`PICA+,++,-,--`)는
    숫자가 없어 걸리지 않고, AL NOUF1 이 태그 자리에 찍는 `.....` 는 글자도
    숫자도 없어 걸리지 않는다.

    ★ KKS 정규식을 박지 않는다.  "코드가 인쇄돼 있는가" 만 보고, 그 코드가
    어떤 모양인지는 그 도면이 말한다 (모양은 `_shape` 로 세어 함께 낸다).
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))

import pidcache  # noqa: E402

DOCS = [
    ("AL NOUF1", "data/pid_total.pdf", "out/regression_3p/AL_NOUF1.json"),
    ("SADARA", "app/_data/uploads/2391ee0f1ea6_sadara_1A46.pdf", "out/regression_3p/SADARA.json"),
    ("TC2", "data/TC2_260821.pdf", "out/regression_3p/TC2.json"),
    ("UAD", "data/UAD_binding.pdf", "out/round28/uad.json"),
]


def _is_code(t: str) -> bool:
    """글자와 숫자가 함께 든 낱말 — 도면이 코드로 쓰는 모양."""
    return any(c.isalpha() for c in t) and any(c.isdigit() for c in t)


# ★ 코드가 전부 태그인 것은 아니다 (28회차 실측).  첫 규칙("글자+숫자")으로 세니
# AL NOUF1 에서 `DN150`·`DN2400`(관경)이 태그로 잡혔다 — 9행.  도면은 둘을
# **쓰는 방식**으로 가른다:
#
#   태그는 한 항목의 이름이다 — 그 항목 하나에만 붙는다
#   관경·등급은 여러 항목이 함께 쓰는 값이다 — 여러 검출 안에 같은 글자가 나온다
#
# 실측 (검출 사각형 안에 든 코드의 문서 전체 등장 횟수):
#   AL NOUF1  최소 **8** · 중앙 97 · 최대 261   (DN2400 8 · DN50 261)
#   UAD       최소 1 · **중앙 1** · 최대 120    (`00EKG30CP001A` 1 · DN25 120)
#
# 그래서 **두 검출 이상에 나오는 코드는 태그가 아니다** 로 가른다.  이것은 횟수
# 문턱이 아니라 구조다 — 두 항목이 같은 이름을 가질 수 없다.


def _shape(t: str) -> str:
    """`00GKB01CL001A` → `D2L3D2L2D3L1` — 그 도면의 태그 모양을 세기 위한 것."""
    out, run, kind = [], 0, None
    for c in t:
        k = "D" if c.isdigit() else ("L" if c.isalpha() else "X")
        if k != kind:
            if kind:
                out.append("%s%d" % (kind, run))
            kind, run = k, 1
        else:
            run += 1
    if kind:
        out.append("%s%d" % (kind, run))
    return "".join(out)


def survey(name, pdf, result):
    rows = json.load(open(ROOT / result))["result"]["rows"]
    doc = pymupdf.open(ROOT / pdf)
    words = {}
    for i in range(doc.page_count):
        p = doc[i]
        m = p.rotation_matrix
        w = [(pymupdf.Rect(x[:4]) * m, x[4]) for x in p.get_text("words")]
        w += pidcache._shx_words(pidcache._shx_entries(p, m))
        words[i + 1] = [(r, t) for r, t in w]
    # 1차: 검출마다 그 안에 인쇄된 코드를 모은다
    codes_of = {}
    owners = collections.Counter()
    for n, r in enumerate(rows):
        rect = pymupdf.Rect(*r["rect"])
        got = [t for rr, t in words.get(r["page_no"], []) if rect.intersects(rr) and _is_code(t)]
        codes_of[n] = got
        for t in set(got):
            owners[t] += 1
    # 2차: 두 검출 이상에 나오는 코드는 이름이 아니다 (관경·등급)
    # 3차: ★ 태그는 사고가 아니라 **체계**다 — 같은 모양이 여러 장에서 되풀이된다.
    #      이 걸림이 없으면 AL NOUF1 의 `DN150`·`DN80` 두 개가 "1급" 을 만든다
    #      (우연히 한 검출에만 든 관경).  체계의 조건은 **두 검출 이상 · 두 장
    #      이상** 이고, 이것은 문턱이 아니라 "되풀이되는가" 다.  실측 격차:
    #      UAD 으뜸 모양이 검출 100개 · 14장 ↔ AL NOUF1 은 1개 · 1장.
    shape_rows = collections.Counter()
    shape_pages = collections.defaultdict(set)
    for n, r in enumerate(rows):
        for t in {t for t in codes_of[n] if owners[t] == 1}:
            shape_rows[_shape(t)] += 1
            shape_pages[_shape(t)].add(r["page_no"])
    system = {sh for sh, c in shape_rows.items() if c >= 2 and len(shape_pages[sh]) >= 2}

    per_page = collections.defaultdict(lambda: [0, 0])     # [검출, 태그 붙은 검출]
    shapes = collections.Counter()
    tagged_rows = []
    for n, r in enumerate(rows):
        pg = r["page_no"]
        per_page[pg][0] += 1
        tags = [t for t in codes_of[n] if owners[t] == 1 and _shape(t) in system]
        if tags:
            tag = max(tags, key=len)
            per_page[pg][1] += 1
            shapes[_shape(tag)] += 1
            tagged_rows.append((pg, r["type"], tag))
    doc.close()
    return per_page, shapes, tagged_rows, len(rows)


def main() -> int:
    out = ["# [D] 증거 등급 — 네 프로젝트 장별", "",
           "판정: 그 검출의 사각형 안에 **글자+숫자 낱말(코드)** 이 인쇄돼 있는가.",
           "기능 코드(`LIT`)는 숫자가 없고 AL NOUF1 의 `.....` 는 둘 다 없다.", ""]
    for name, pdf, result in DOCS:
        if not (ROOT / result).exists() or not (ROOT / pdf).exists():
            out.append("## %s — 파일 없음 (%s)" % (name, result))
            continue
        per_page, shapes, tagged, total = survey(name, pdf, result)
        tag_rows = sum(v[1] for v in per_page.values())
        pages1 = sum(1 for v in per_page.values() if v[1] > 0)
        out += ["## %s" % name, "",
                "행 %d · 태그 붙은 행 **%d (%.1f%%)** · 행이 있는 장 %d 중 태그 있는 장 **%d**"
                % (total, tag_rows, 100.0 * tag_rows / max(total, 1), len(per_page), pages1), "",
                "등급: **%s**" % ("1급 (태그 있음)" if tag_rows else "2급 (태그 없음 — 기하로 간다)"), ""]
        if shapes:
            out.append("태그 모양 상위: %s" % ", ".join(
                "`%s`×%d" % (s, n) for s, n in shapes.most_common(4)))
            out.append("예: %s" % ", ".join("p%d %s `%s`" % t for t in tagged[:4]))
            out.append("")
        rows_line = " · ".join("p%d %d/%d" % (p, v[1], v[0])
                               for p, v in sorted(per_page.items()))
        out += ["장별 (태그/검출): %s" % rows_line, ""]
    (ROOT / "out" / "round29" / "4_tier_by_page.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out[:80]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
