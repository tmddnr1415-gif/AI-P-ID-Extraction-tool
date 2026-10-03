"""축3 — 식별률.  **정답지 없이** "도면이 인쇄한 것 중 얼마를 읽어냈나" 를 잰다.

왜 필요한가
    축1(전량)·축2(SCT)는 발주처 리스트와 대조한다.  TC2·SADARA 는 그 리스트가
    없어 두 축이 서지 않는다.  그런데 목표는 "AL NOUF1 수준의 식별률" 이므로
    **정답지 없이 세 프로젝트에서 똑같이 잴 수 있는 축**이 하나 더 필요하다.
    축1·축2 는 건드리지 않는다 — 이것은 추가다.

무엇을 재는가 — 여섯 지표, 전부 "분모가 도면 안에 있는" 비율이다.

    ① 도면번호   그 칸에 번호가 인쇄된 장 중 읽어낸 장
    ② 개정(REV)  전체 장 중 개정을 신뢰도 HIGH 로 읽어낸 장
    ③ 태그→행    도면이 인쇄한 (장, 태그) 짝 중 그 장에 해당 행이 선 것
                 ⚠ 첫 정의는 인쇄된 낱말과 행의 TYPE 을 **글자 그대로** 비교했다.
                 도면은 `TT`·`PT`·`LSH` 로 쓰고 엔진은 `anchors.type_map` 으로
                 `TIT`·`PIT`·`LS` 로 바꿔 행을 내므로, 그 정의는 엔진이 아니라
                 채점기의 이름 대조를 재고 있었다 (AL NOUF1 185/336).
                 **엔진이 읽는 그 사전을 채점기도 읽는다.**  밸브 태그는 계기
                 갈래에서 빼고 밸브 갈래에서만 센다 (전에는 양쪽에서 세어
                 계기 쪽에서 반드시 틀렸다).
    ④ 수량       Q'ty 가 정해진 행 / 전체 행
    ⑤ 심볼 판정  행이 된 검출 / (행이 된 검출 + 판정 못 한 심볼)
    ⑥ 파라미터   그 도면에서 잰 파라미터 / 잴 수 있어야 하는 파라미터

가중
    **여섯 지표에 같은 무게(1/6)를 준다.**  근거는 지표의 성격이다 — 여섯이
    파이프라인의 서로 다른 단계(장 판독 · 개정 · 심볼 · 수량 · 판정 · 파라미터)를
    하나씩 대표하고, 어느 하나가 무너지면 산출물이 그만큼 못 쓰이게 된다.
    "무엇이 더 중요한가" 를 도면이 답해 주지 않으므로 순위를 매길 근거가 없고,
    근거 없는 순위는 임의값이다 (§2.1 ②).  **점수가 좋아 보이도록 무게를
    고르지 않았다** — 무게를 정한 뒤에 점수를 냈고, 그 뒤로 바꾸지 않는다.

읽는 것
    `pipeline.analyse` 의 결과 dict 하나뿐이다.  도면을 다시 열지 않는다 —
    ①의 분모만 예외로 타이틀블록 칸의 낱말을 봐야 해서, 그 값은 결과에 이미
    실려 있는 `applied_rules.layout` 과 페이지 낱말로 파이프라인이 아니라
    이 모듈이 따로 센다 (`denominators()`).
"""
from __future__ import annotations

import re

# 도면번호처럼 생긴 낱말 — **`formats.drawing_no` 를 쓰지 않는다.**
# 그 정규식이 못 읽는 것을 세는 것이 ①의 분모이므로, 분모를 그 정규식으로
# 정하면 언제나 100% 가 나온다 (자기 자신에게 묻는 검사 — 16·18회차).
# 그래서 "하이픈 둘 이상 + 숫자 넷 이상" 이라는 느슨한 모양만 본다.
LOOSE_DWG = re.compile(r"^(?=(?:[^-]*-){2,})(?=(?:\D*\d){4,}).{8,40}$")

# 밸브 태그 낱말 → 이 장에 밸브 행이 섰는가로 본다.  밸브 행은 몸체 갈래
# (GLOBE·GATE…)와 액추에이터를 싣지 태그 낱말을 싣지 않으므로, 태그 하나가
# 어느 행이 됐는지는 결과만으로 짝지을 수 없다.  **그 거친 정도를 그대로 적는다.**
VALVE_TAGS = ("MOV", "HOV", "XV", "FCV", "PCV", "TCV", "LCV", "CV", "NRV", "PSV")
VALVE_TABS = ("MOV", "BFV", "PNEUMATIC")

METRICS = ("도면번호", "개정", "태그→행", "수량", "심볼판정", "파라미터")


def _inside(rect, area):
    if not area:
        return True
    return (area[0] <= rect[0] and rect[2] <= area[2]
            and area[1] <= rect[1] and rect[3] <= area[3])


def _drawing_area(result):
    lay = (result.get("applied_rules") or {}).get("layout") or {}
    for it in lay.get("items") or []:
        if it.get("key") == "regions.drawing_area":
            return it.get("value")
    return None


def _dwg_cell(result):
    """유도된 도면번호 칸.  없으면 None."""
    lay = (result.get("applied_rules") or {}).get("layout") or {}
    for it in lay.get("items") or []:
        if it.get("key") == "title_block.dwg_no_region":
            return it.get("value")
    return None


def denominators(result, pages_words):
    """①의 분모 — 도면번호가 **인쇄된** 장.

    `pages_words` 는 `{page_no: [(rect, text), ...]}`.  칸을 모르면 전체 장을
    분모로 쓰고 그 사실을 함께 돌려준다 (모르는 것을 100% 로 세지 않는다).
    """
    cell = _dwg_cell(result)
    tbs = result["titleblocks"]
    if not cell:
        return len(tbs), "도면번호 칸을 못 찾아 전체 장을 분모로 썼습니다"
    x0, y0, x1, y1 = cell
    n = 0
    for tb in tbs:
        words = pages_words.get(tb["page_no"]) or []
        if any(LOOSE_DWG.match(t) and x0 <= r[0] and r[2] <= x1
               and y0 <= r[1] and r[3] <= y1 for r, t in words):
            n += 1
    return n, ""


def measure(result, pages_words, anchors, type_map=None):
    """여섯 지표와 총점.

    `anchors` 는 검출기가 아는 태그 낱말, `type_map` 은 **엔진이 쓰는 그
    사전**(`anchors.type_map`)이다 — 인쇄된 낱말이 어느 TYPE 의 행이 되어야
    하는지는 그 사전이 정하므로, 채점기도 같은 것을 읽어야 한다.
    """
    type_map = type_map or {}
    tbs = result["titleblocks"]
    rows = result["rows"]
    out = {}

    printed, note = denominators(result, pages_words)
    read = sum(1 for t in tbs if t["drawing_no"])
    out["도면번호"] = (read, printed, note)

    hi = sum(1 for t in tbs
             if t.get("rev") not in ("?", "", None)
             and t.get("rev_confidence") == "HIGH")
    out["개정"] = (hi, len(tbs), "")

    # ③ (장, 태그) 짝.  도면 영역 안의 낱말만 본다 — 검출기 자신이 그 밖은
    # 심볼이 아니라고 정하기 때문이다 (`detect` 의 `_inside(... drawing_area)`).
    field_by_page, valve_pages = {}, set()
    for r in rows:
        p = r.get("page_no")
        if r.get("tab") == "FIELD":
            field_by_page.setdefault(p, set()).add((r.get("type") or "").strip())
        elif r.get("tab") in VALVE_TABS:
            valve_pages.add(p)
    pid_pages = {t["page_no"] for t in tbs if t["page_kind"] == "PID"}
    area = _drawing_area(result)
    hit = tot = 0
    for p in sorted(pid_pages):
        seen = {t for r, t in (pages_words.get(p) or []) if _inside(r, area)}
        for t in sorted(seen & set(anchors) - set(VALVE_TAGS)):
            tot += 1
            hit += 1 if type_map.get(t, t) in field_by_page.get(p, ()) else 0
        for t in sorted(seen & set(VALVE_TAGS)):
            tot += 1
            hit += 1 if p in valve_pages else 0
    out["태그→행"] = (hit, tot, "밸브 태그는 그 장에 밸브 행이 있는지까지만 본다")

    out["수량"] = (sum(1 for r in rows if r.get("qty") is not None), len(rows), "")

    unj = len(result.get("unjudged_symbols") or [])
    out["심볼판정"] = (len(rows), len(rows) + unj, "")

    got, all_ = _parameters(result)
    out["파라미터"] = (got, all_, "")

    score = 0.0
    for k in METRICS:
        a, b, _n = out[k]
        score += (a / b if b else 0.0) / len(METRICS)
    return out, round(100 * score, 1)


def _parameters(result):
    """⑥ — 그 도면에서 잰 파라미터 / 잴 수 있어야 하는 파라미터.

    센다: 범례에서 유도하는 항목 · 승수표 · 도면틀에서 재는 항목.
    "쟀다" 는 출처가 LEGEND · MEASURED · DERIVED 인 것이고,
    CONFIG_FALLBACK · UNAVAILABLE 은 **남의 값을 쓴 것**이라 세지 않는다.
    """
    got = tot = 0
    for _k, v in (result.get("legend") or {}).items():
        if not isinstance(v, dict):
            continue
        tot += 1
        got += 1 if v.get("source") in ("LEGEND", "MEASURED") else 0
    m = result.get("multipliers") or {}
    if m:
        tot += 1
        got += 1 if m.get("source") == "LEGEND" else 0
    lay = (result.get("applied_rules") or {}).get("layout") or {}
    for it in lay.get("items") or []:
        tot += 1
        got += 1 if it.get("source") == "DERIVED" else 0
    return got, tot
