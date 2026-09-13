"""증거 등급 1급 — 도면이 태그를 인쇄했으면 그것으로 읽는다 (§10, 28회차).

무엇을 하는가
    검출(버블·몸체)의 사각형 안에 인쇄된 **코드**를 모으고, 그중 어느 것이
    그 도면의 **태그 체계**인지를 도면에서 판정한 뒤 행에 붙인다.

왜 정규식을 박지 않는가
    KKS·ISA·회사 규칙은 프로젝트마다 다르다.  대신 **쓰이는 방식**을 본다 —
    실측이 규칙을 두 번 좁혔고 두 번 다 도면이 시켰다:

      1차  "글자와 숫자가 함께 든 낱말" → AL NOUF1 의 `DN150`·`DN2400`(관경)
           9행이 태그로 잡혔다.
      2차  "두 검출 이상에 나오면 이름이 아니다" (두 항목이 같은 이름을 가질 수
           없다) → 2행으로 줄었지만 0 이 아니다 (우연히 한 검출에만 든 관경).
      3차  "태그는 사고가 아니라 **체계**다" — 같은 **모양**이 두 검출 이상 ·
           두 장 이상에서 되풀이되어야 한다.
           → AL NOUF1 0 · SADARA 0 · TC2 0 · UAD 128.

    모양은 글자·숫자 run 의 길이 열이다 (`00GKB01CL001A` → `D2L3D2L2D3L1`).
    **그 모양이 무엇인지는 도면이 말한다** — 코드에 적힌 것은 "모양을 센다" 뿐이다.

실측 (28회차)
    UAD   으뜸 모양 `D2L3D2L2D3` 103행 + 접미 변형 `…L1` 25행 · 14/14장
    AL NOUF1 · SADARA · TC2  체계 없음 → 2급 (기하 경로 그대로)
"""
from __future__ import annotations

import collections


def _is_code(t: str) -> bool:
    """글자와 숫자가 함께 든 낱말 — 도면이 코드로 쓰는 모양."""
    return any(c.isalpha() for c in t) and any(c.isdigit() for c in t)


def shape(t: str) -> str:
    """`00GKB01CL001A` → `D2L3D2L2D3L1`."""
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


def assign(items, words_by_page):
    """`(행별 태그, 판정 근거)`.

    `items` 는 `(page_no, rect)` 목록이고 순서가 곧 행 순서다.
    `words_by_page` 는 `{쪽: [(사각형, 글자)]}`.
    """
    codes_of = {}
    owners = collections.Counter()
    for i, (page_no, rect) in enumerate(items):
        got = [t for r, t in words_by_page.get(page_no, ())
               if _is_code(t) and rect.intersects(r)]
        codes_of[i] = got
        for t in set(got):
            owners[t] += 1

    rows_with, pages_with = collections.Counter(), collections.defaultdict(set)
    for i, (page_no, _rect) in enumerate(items):
        for t in {t for t in codes_of[i] if owners[t] == 1}:
            rows_with[shape(t)] += 1
            pages_with[shape(t)].add(page_no)
    system = {sh for sh, n in rows_with.items()
              if n >= 2 and len(pages_with[sh]) >= 2}

    tags = {}
    for i, (_page_no, _rect) in enumerate(items):
        cand = [t for t in codes_of[i] if owners[t] == 1 and shape(t) in system]
        if cand:
            tags[i] = max(cand, key=len)
    facts = {
        "tier": 1 if tags else 2,
        "tagged_rows": len(tags),
        "rows": len(items),
        "shapes": sorted(system, key=lambda s: -rows_with[s])[:6],
        "shape_counts": {s: rows_with[s] for s in sorted(
            system, key=lambda s: -rows_with[s])[:6]},
        "pages_tagged": sorted({items[i][0] for i in tags}),
        "rule": ("코드가 한 검출에만 나오고, 그 모양이 두 검출·두 장 이상에서 "
                 "되풀이될 때만 태그로 본다"),
    }
    return tags, facts
