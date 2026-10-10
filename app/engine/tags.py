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

hotfix35 — 한 루프가 공유하는 태그
    2차 규칙("두 검출 이상에 나오면 이름이 아니다")이 **같은 루프의 두 버블**을
    버리고 있었다.  QFE p46 은 `PI 11LBB50CP001` 과 `PIT 11LBB50CP001` 을 신호선으로
    잇고 **같은 태그를 두 버블에** 찍는다 — 그것이 "한 라인" 이라는 도면의 말인데
    (hotfix31 `_fold_readouts` 의 전제), 그 태그는 두 검출에 나오므로 둘 다 태그를
    못 받았고, 접기는 태그가 있어야 돌므로 PI·PIT 가 각각 행으로 남았다.
    DXF 경로는 블록 속성이 태그를 주어 hotfix17 이 같은 태그의 두 행을 이미 루프로
    읽는다 — PDF 경로만 거꾸로였다.

    루프 공유 = 같은 장 · 서로 **다른 종류**(앵커 글자)의 검출이 같은 코드를 든다.
    같은 종류 둘이 같은 코드를 들면 그것은 두 항목이 한 이름을 가진 것이라 2차
    규칙 그대로 이름이 아니고(배관 번호 · 관경), 다른 장에 걸친 공유도 그렇다.
    `kinds` 가 없으면 공유를 가르지 않아 **옛 판정과 글자 그대로 같다**.
"""
from __future__ import annotations

import collections
import re


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


def assign(items, words_by_page, kinds=None):
    """`(행별 태그, 판정 근거)`.

    `items` 는 `(page_no, rect)` 목록이고 순서가 곧 행 순서다.
    `words_by_page` 는 `{쪽: [(사각형, 글자)]}`.
    `kinds` 는 행마다 그 검출의 종류(버블 앵커 글자 · 밸브 몸체)이고, 있으면
    같은 장의 서로 다른 종류가 공유하는 코드를 **한 루프의 이름**으로 본다.
    """
    codes_of = {}
    owners = collections.defaultdict(list)
    for i, (page_no, rect) in enumerate(items):
        got = [t for r, t in words_by_page.get(page_no, ())
               if _is_code(t) and rect.intersects(r)]
        codes_of[i] = got
        for t in set(got):
            owners[t].append(i)

    def is_name(t: str) -> bool:
        """한 검출만 들거나, 한 장의 서로 다른 종류가 같이 드는 코드(루프)."""
        own = owners[t]
        if len(own) == 1:
            return True
        if kinds is None:
            return False
        if len({items[i][0] for i in own}) != 1:
            return False
        ks = [str(kinds[i] or "").strip().upper() for i in own]
        return all(ks) and len(set(ks)) == len(ks)

    names = {t for t in owners if is_name(t)}
    loop_shared = {t for t in names if len(owners[t]) > 1}

    rows_with, pages_with = collections.Counter(), collections.defaultdict(set)
    for t in names:
        page_no = items[owners[t][0]][0]
        rows_with[shape(t)] += 1
        pages_with[shape(t)].add(page_no)
    system = {sh for sh, n in rows_with.items()
              if n >= 2 and len(pages_with[sh]) >= 2}

    tags = {}
    for i, (_page_no, _rect) in enumerate(items):
        cand = [t for t in codes_of[i] if t in names and shape(t) in system]
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
        "loop_shared": sorted(t for t in loop_shared if shape(t) in system),
        "rule": ("코드가 한 검출에만 나오거나 한 장의 서로 다른 종류가 같이 들고, "
                 "그 모양이 두 이름·두 장 이상에서 되풀이될 때만 태그로 본다"),
    }
    return tags, facts


# ---------------------------------------------------------------------------
# hotfix39 — 태그 문법: 태그 안의 어느 자리가 계기 변수를 말하는가를 **그 도면에서** 배운다
# ---------------------------------------------------------------------------
#
# 사용자: *"실행 프로젝트 출력 시에는 tag number 가 우선시 되어야 하며 tag number 에
# 계기 타입이 명시되어 있다."*  KKS 라면 `11LBB50CP001` 의 `CP` 가 압력, `CT` 가 온도다.
# 그러나 그 표를 코드에 적지 않는다 (§9 — 회사마다 다르다).  대신 **같은 행에 버블 글자
# (ISA 머리글자)와 태그가 함께 있는 행들**에서, 태그의 글자 자리마다 "그 자리의 글자가
# 머리글자를 얼마나 결정하는가" 를 세어 가장 잘 가르는 자리를 고른다.  QFE 실측:
# 셋째 글자 묶음이 CP→P 721 · CT→T 263 · CL→L 312 · CF→F 105 · BP→RO 31 · CQ→A 7 로
# 갈린다 (순도 0.98).  배운 것은 ① 그 자리 ② 자리의 글자 → 머리글자 과반 ③ 계기 코드의
# 첫 글자(과반) 이고, 셋 다 **지문 밖**이며 행을 만들거나 지우는 데 혼자 쓰이지 않는다.

def _letter_runs(t: str) -> list:
    return re.findall(r"[A-Z]+", t or "")


def grammar(samples) -> dict:
    """`samples` = [(태그, 머리글자)].  돌려주는 것: 자리 · 글자→머리 집계 · 과반 · 순도.

    자리는 **글자 묶음의 순번**이다 (`11LBB50CP001` → `LBB`·`CP` → 0·1).  모든 자리를
    재서 순도(자리 글자마다 과반 머리의 몫)가 가장 높은 자리를 고른다 — 표본의 절반
    이상이 그 자리를 가질 때만.  표본이 둘 미만이면 배우지 않는다.
    """
    samples = [(str(t or "").strip().upper(), str(h or "").strip().upper())
               for t, h in samples if t and h]
    out = {"learned": False, "samples": len(samples)}
    if len(samples) < 2:
        return out
    best = None
    for k in range(max(len(_letter_runs(t)) for t, _h in samples)):
        pairs = [(_letter_runs(t)[k], h) for t, h in samples if len(_letter_runs(t)) > k]
        if len(pairs) < len(samples) / 2:
            continue
        by = collections.defaultdict(collections.Counter)
        for code, h in pairs:
            by[code][h] += 1
        pure = sum(c.most_common(1)[0][1] for c in by.values()) / len(pairs)
        cand = (pure, len(pairs), k, by)
        if best is None or cand[:2] > best[:2]:
            best = cand
    if best is None:
        return out
    pure, n, k, by = best
    majority = {}
    for code, c in by.items():
        head, m = c.most_common(1)[0]
        if m * 2 > sum(c.values()):              # 과반일 때만 — 갈리면 말하지 않는다
            majority[code] = {"head": head, "n": m, "of": sum(c.values())}
    # 계기 코드의 첫 글자 — 그 도면이 계기 코드에 공통으로 쓰는 글자 (KKS 라면 `C`)
    first = collections.Counter()
    for code, c in by.items():
        first[code[0]] += sum(c.values())
    cls, m = first.most_common(1)[0]
    out.update({"learned": True, "run_index": k, "purity": round(pure, 3), "covered": n,
                "map": {code: dict(c) for code, c in sorted(by.items())},
                "majority": majority,
                "class_letter": cls if m * 2 > sum(first.values()) else "",
                "class_share": round(m / sum(first.values()), 3)})
    return out


def code_of(tag: str, g: dict) -> str:
    """배운 자리의 글자 묶음.  문법이 없거나 그 자리가 없으면 빈 문자열."""
    if not g or not g.get("learned"):
        return ""
    runs = _letter_runs(str(tag or "").upper())
    k = g["run_index"]
    return runs[k] if len(runs) > k else ""
