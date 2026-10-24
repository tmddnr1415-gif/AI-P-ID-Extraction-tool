"""도면 가르치기의 **제안** — 사람이 누를 자리를 프로그램이 먼저 골라 둔다 (hotfix87).

## 왜 있는가

hotfix85 의 가르치기는 멈출 때마다 사람이 도면을 세 번 누르게 했다 (Symbol & Legend 장 ·
버블 하나 · NOTES 제목).  사용자 지시: *"사용자 직접 범위 지정의 포인트가 많지 않아야 한다."*
그런데 그 세 자리는 대개 프로그램도 짐작할 수 있다 — 짐작을 **판정에 바로 쓰지 않을** 뿐이다.
그래서 여기서 짐작을 **제안**으로 내고, 화면이 그것을 미리 채워 보인다.  사람은 초록 표시가
맞는지 눈으로 보고 [저장하고 다시 분석] 한 번만 누르면 된다.  틀린 것만 다시 고른다.

## 판정이 아니다

* 엔진은 이 모듈을 부르지 않는다 — 제안은 사람이 저장해야 `form_teach.json` 에 들어가고,
  그때부터는 사람이 가르친 값과 똑같다 (작성자 필수 · 다시 분석해야 반영).
* 자동 규칙(hotfix84 의 다른 낱말 · 곡선+짧은 직선 캡)보다 **넓게** 짐작한다.  넓은 짐작은
  틀릴 수 있으므로 판정에 바로 쓰지 않고 사람 눈을 한 번 거친다 — 그것이 자동과 다른 점이다.
* 새 상수를 두지 않는다 — 장 수·글자 높이·그 문서에서 센 비율만 쓴다.

## 세 제안

    legend_page  머리말(밸브 · 액추에이터 · 신호선 칸)을 인쇄된 그대로(2점) 또는 핵심 낱말(1점)로 가장 많이
                 담은 장부터, 빠진 칸은 이미 고른 장에 가까운 장으로 — 엔진이 가르친 장에서 칸을 찾는
                 길(`legend_rules._page_with` 의 인쇄된 그대로 → 핵심 낱말)과 같은 판정
    bubbles      계기 글자가 많은 장들에서 계기 글자 자리를 눌러 본 것처럼(`detect_symbols.bubble_at`) 윤곽을
                 모으고, 그 그림으로 찾은 버블이 계기 글자를 가장 많이 품는 모양부터 — 남은 글자를 더 품는
                 둘째·셋째 모양까지
    drawing      테두리를 선이 아니라 사각형으로 그린 양식에서 그 사각형 (`drawing_area`)
    notes        `NOTES` 제목이 여러 장에서 같은 자리에 인쇄된 곳 → 그 제목을 누른 것과 같은 영역
                 (`derive_layout.notes_from_heading` — 서버 `/teach/click` 과 같은 함수)
"""
from __future__ import annotations

import collections

# 버블 제안이 볼 장의 수 — 계기 글자가 많은 순.  모양을 배우는 데 장 몇 개면 넉넉하고(한 문서는 버블을
# 몇 가지 모양으로만 그린다), 더 보면 화면이 기다린다.  판정에 쓰지 않는 값이다.
BUSY_PAGES = 4
# 첫 모양이 못 감싼 계기 글자를 찾아볼 장의 수 — 계기 글자가 많은 순으로 여기까지.  한 문서가 버블을 두
# 번째 모양으로 그리는 장은 대개 한두 장이라(QFE p42 — 계기 글자 순위 16번째) 넉넉히 보되 전부는 안 본다.
SCAN_PAGES = 16
# 한 장에서 눌러 볼 계기 글자의 수 (같은 이유)
CLICKS_PER_PAGE = 30
# 버블 예시는 최대 셋 — 화면이 저장하는 상한(`form_teach.MAX_BUBBLES`)보다 작다.
MAX_EXAMPLES = 3


def _engine():
    import detect_symbols as ds
    import derive_layout
    import legend_rules
    import pidcache
    return ds, derive_layout, legend_rules, pidcache


# ---------------------------------------------------------------------------
# Symbol & Legend 장
# ---------------------------------------------------------------------------
def legend_pages(pages) -> dict:
    """Symbol & Legend 장 제안 — `{"pages": [번호…], "found": {머리말: 번호|None}}` 또는 None."""
    _ds, _dl, legend_rules, _pc = _engine()
    heads = legend_rules.TEACHABLE_HEADINGS
    cover: dict = {}
    for pc in pages:
        got = {}
        for h in heads:
            if legend_rules._line_with(pc, h.split()) is not None:
                got[h] = 2                               # 인쇄된 그대로
            elif legend_rules._keyword_heading(pc, h):
                got[h] = 1                               # 핵심 낱말 (가르친 장에서만 엔진이 받는 길)
        if got:
            cover[pc.page_no] = got
    if not cover:
        return None
    first = max(cover, key=lambda n: (sum(cover[n].values()), len(cover[n]), -n))
    chosen = [first]
    found = {h: (first if h in cover[first] else None) for h in heads}
    for h in heads:
        if found[h] is not None:
            continue
        cands = [n for n in cover if h in cover[n]]
        if not cands:
            continue
        best = min(cands, key=lambda n: (-cover[n][h], min(abs(n - c) for c in chosen), n))
        chosen.append(best)
        for hh in heads:
            if found[hh] is None and hh in cover[best]:
                found[hh] = best
    return {"pages": chosen, "found": found}


# ---------------------------------------------------------------------------
# 버블 예시
# ---------------------------------------------------------------------------
def _signature(t: dict) -> tuple:
    if t.get("mode") == "caps":
        return ("caps", tuple(t.get("cap_kinds") or ()), round(float(t["cap_ratio"]), 1), round(float(t["cap_long"])))
    return ("exact", tuple(p["kind"] for p in t.get("parts") or ()), round(t["size"][0]), round(t["size"][1]))


def bubbles(form, anchors) -> dict | None:
    """버블 예시 제안 — `{"examples": [{page_no, rect, click}], "covered", "total", "shapes"}` 또는 None.

    계기 글자(앵커 사전)가 든 자리를 눌러 본 것처럼 윤곽을 모으고(`bubble_at`), 그 윤곽에서 배운 그림
    (`learn_bubble_template`)으로 버블을 찾아(`taught_bubbles`) **계기 글자를 몇 개 품는지** 센다.
    가장 많이 품는 모양이 첫째이고, 첫째가 못 품은 글자를 더 품는 모양이 있으면 둘째·셋째.
    찾은 버블의 절반 넘게가 글자를 안 품으면 버블이 아니라 다른 기호의 윤곽이다 — 버린다.
    """
    ds, _dl, _lr, pidcache = _engine()
    count = {pc.page_no: sum(1 for _r, t in pc.words if t in anchors) for pc in form}
    ranked = [pc for pc in sorted(form, key=lambda pc: (-count[pc.page_no], pc.page_no)) if count[pc.page_no]]
    busy = ranked[:BUSY_PAGES]
    if not busy:
        return None
    import pymupdf
    words = {pc.page_no: [(pymupdf.Rect(r), t) for r, t in pc.words if t in anchors] for pc in ranked[:SCAN_PAGES]}
    total = sum(len(words[pc.page_no]) for pc in busy)
    cands: dict = {}                     # 모양 → (예시, 그 모양으로 눌린 횟수)
    for pc in busy:
        for r, _t in words[pc.page_no][:CLICKS_PER_PAGE]:
            x, y = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
            R = ds.bubble_at(pc, x, y)
            if R is None:                    # 누른 점(글자 가운데)을 품는 윤곽 — 글자 둘레가 윤곽에 닿아도 된다
                continue
            rect = [round(R.x0 - 1.5, 1), round(R.y0 - 1.5, 1), round(R.x1 + 1.5, 1), round(R.y1 + 1.5, 1)]
            t = ds.learn_bubble_template(pc, rect)
            if not t:
                continue
            sig = _signature(t)
            if sig in cands:
                cands[sig][2] += 1
            else:
                cands[sig] = [t, {"page_no": pc.page_no, "rect": rect, "click": [round(x, 1), round(y, 1)]}, 1]
    if not cands:
        return None
    top = sorted(cands.values(), key=lambda c: -c[2])[:6]

    def hits(t) -> set:
        got = set()
        found = 0
        with_word = 0
        for pc in busy:
            outs = ds.taught_bubbles(pc, [t])
            found += len(outs)
            for o in outs:
                inside = [i for i, (r, _t) in enumerate(words[pc.page_no])
                          if o.rect.contains(pymupdf.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2))]
                if inside:
                    with_word += 1
                got |= {(pc.page_no, i) for i in inside}
        return got if found and with_word * 2 >= found else set()

    scored = [(c, hits(c[0])) for c in top]
    chosen, covered = [], set()
    while scored and len(chosen) < MAX_EXAMPLES:
        c, h = max(scored, key=lambda s: len(s[1] - covered))
        new = h - covered
        # 둘째부터는 남은 글자를 의미 있게 더 품을 때만 — 둘 이상이고 전체의 1/20 이상
        if not new or (chosen and len(new) < max(2, total / 20)):
            break
        chosen.append(c)
        covered |= h
        scored = [s for s in scored if s[0] is not c]
    if not chosen:
        return None
    # 둘째 모양 — 첫 장들 밖에서 지금 모양이 감싸지 못한 계기 글자가 가장 많은 장을 찾아 거기서 다시 눌러 본다.
    temps = [c[0] for c in chosen]
    gap_page, gap = None, []
    for pc in ranked[BUSY_PAGES:SCAN_PAGES]:
        if len(chosen) >= MAX_EXAMPLES:
            break
        outs = ds.taught_bubbles(pc, temps)
        unc = [(r, t) for r, t in words[pc.page_no]
               if not any(o.rect.contains(pymupdf.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)) for o in outs)]
        if len(unc) > len(gap):
            gap_page, gap = pc, unc
    # 그 장 계기 글자의 절반 넘게를 못 감쌌으면 그 장은 다른 모양으로 그렸다 (QFE p42: 36/36)
    if gap_page is not None and len(gap) * 2 > len(words[gap_page.page_no]) >= 2 and len(chosen) < MAX_EXAMPLES:
        best = None
        for r, _t in gap[:CLICKS_PER_PAGE]:
            x, y = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
            R = ds.bubble_at(gap_page, x, y)
            if R is None:
                continue
            rect = [round(R.x0 - 1.5, 1), round(R.y0 - 1.5, 1), round(R.x1 + 1.5, 1), round(R.y1 + 1.5, 1)]
            t = ds.learn_bubble_template(gap_page, rect)
            if not t or any(_signature(t) == _signature(c) for c in temps):
                continue
            outs = ds.taught_bubbles(gap_page, [t])
            inside = {i for i, (rr, _tt) in enumerate(gap) for o in outs
                      if o.rect.contains(pymupdf.Point((rr.x0 + rr.x1) / 2, (rr.y0 + rr.y1) / 2))}
            with_word = sum(1 for o in outs if any(o.rect.contains(pymupdf.Point((rr.x0 + rr.x1) / 2, (rr.y0 + rr.y1) / 2))
                                                  for rr, _tt in words[gap_page.page_no]))
            if outs and with_word * 2 >= len(outs) and (best is None or len(inside) > best[0]):
                best = (len(inside), {"page_no": gap_page.page_no, "rect": rect, "click": [round(x, 1), round(y, 1)]})
        if best and best[0] * 2 > len(gap):
            chosen.append((None, best[1], 0))
            extra = best[0]
        else:
            extra = 0
    else:
        extra = 0
    total += len(words[gap_page.page_no]) if extra else 0
    return {"examples": [c[1] for c in chosen], "covered": len(covered) + extra, "total": total,
            "shapes": len(chosen), "pages": [pc.page_no for pc in busy]}


# ---------------------------------------------------------------------------
# NOTES
# ---------------------------------------------------------------------------
# NOTES 영역을 지을 때 테두리·노트 열을 재는 장의 수.  테두리는 양식이 정하므로 같은 크기의 장 몇 개로
# 같은 답이 나오고(`_frame` 의 다수 조건이 그 장들 안에서 선다), 전부 재면 A1 54장에서 94초가 걸린다
# (AL NOUF1 실측 — 화면이 그 동안 기다린다).  판정에 쓰지 않는 값이다.
FRAME_SAMPLE = 6


def _sample(form, first=None, prefer=()) -> list:
    """같은 종이 크기의 장 중 `FRAME_SAMPLE` 장 — 누른 장 · 이미 읽은 장 먼저, 그다음 고르게 띄엄띄엄."""
    if not form:
        return []
    ref = first or form[0]
    same = [p for p in form if abs(p.width - ref.width) <= 1 and abs(p.height - ref.height) <= 1] or [ref]
    order = ([ref] if first is not None else []) + [p for n in prefer for p in same if p.page_no == n and p is not first]
    step = max(1, len(same) // FRAME_SAMPLE)
    order += [p for p in same[::step] + same if p not in order]
    return order[:FRAME_SAMPLE]


def drawing_area(form) -> dict | None:
    """도면 영역(테두리 안쪽) 제안 — 테두리를 **선이 아니라 사각형 하나**로 그린 양식에서만.

    선으로 그린 테두리는 프로그램이 스스로 찾는다 (이 제안은 None).  선을 못 찾으면 프로그램은 종이를
    테두리로 보는데(hotfix85), 그러면 테두리 바깥 여백의 격자 번호(`7` · `C`)가 도면 글자로 읽혀
    Description 에 섞인다 (Takhiatash 이전 프로그램 기준 실측: 25행).  그래서 종이 크기만 한 사각형
    변(`derive_layout._box_edges` — 자동 새 양식 갈래가 쓰는 같은 함수)을 장 대부분에서 같은 자리에
    찾으면 그것을 제안한다.  종이 가장자리 위의 변은 종이다 (`PAPER_EDGE`)."""
    _ds, derive_layout, _lr, _pc = _engine()
    pick = _sample(form)
    if not pick:
        return None
    W, H = float(pick[0].width), float(pick[0].height)
    fr = derive_layout._frame(pick)
    edge = derive_layout.PAPER_EDGE
    if fr is not None and not (fr[0] <= edge and fr[1] <= edge and fr[2] >= W - edge and fr[3] >= H - edge):
        return None                                   # 프로그램이 테두리를 스스로 찾았다
    vx, hy = [], []
    for i, pc in enumerate(pick):
        bv, bh = derive_layout._box_edges(pc, W, H)
        vx += [(x, i) for x, _lo, _hi in bv]
        hy += [(y, i) for y, _lo, _hi in bh]
    need = derive_layout.FORM_PAGES * len(pick)

    def keep(vals, size):
        groups = []
        for v, i in sorted(vals):
            if groups and v - groups[-1][0][-1] <= 1.0:
                groups[-1][0].append(v); groups[-1][1].add(i)
            else:
                groups.append(([v], {i}))
        got = [g[len(g) // 2] for g, seen in groups if len(seen) >= need]
        return [v for v in got if edge < v < size - edge]
    xs, ys = keep(vx, W), keep(hy, H)
    if len(xs) < 2 or len(ys) < 2:
        return None
    return {"page_no": pick[0].page_no, "rect": [round(xs[0], 1), round(ys[0], 1), round(xs[-1], 1), round(ys[-1], 1)],
            "pages": len(pick)}


def _heading_at(pc, word, heading) -> bool:
    """그 장이 `word` 와 같은 자리(그 글자 높이 안)에 NOTES 제목을 인쇄했는가."""
    h = max(word.height, 1.0)
    return any(t.upper().rstrip(":") == heading and abs(r.x0 - word.x0) <= h and abs(r.y0 - word.y0) <= h
               for r, t in pc.words)


def notes_rect(form, pc, word, prefer=(), frame=None) -> list:
    """NOTES 제목 글자 `word`(그 장 `pc`)를 누른 자리 → NOTES 영역 사각형.

    서버의 `/teach/click` 과 제안이 **같은 함수**를 쓴다 (`derive_layout.notes_from_heading`).
    같은 종이 크기의 장 중 누른 장 + `prefer`(이미 읽은 장) 순으로 `FRAME_SAMPLE` 장만 넘긴다."""
    _ds, derive_layout, _lr, _pc = _engine()
    # 재는 장은 **같은 자리에 같은 NOTES 제목을 인쇄한 장** 먼저 — 같은 양식(같은 노트 열)이라는 증거다.
    # 고르게 띄엄띄엄 뽑으면 표지·목록 장이 섞여 노트 열 괘선이 다수 조건을 못 넘고(QFE 실측), 그러면
    # 노트 열을 못 알아봐 글 왼쪽의 별표 정의가 영역 밖으로 빠진다 (공급자 이름 356칸 · 수량 487칸).
    same_heading = [p.page_no for p in form if p is not pc and _heading_at(p, word, derive_layout.NOTES_HEADING)]
    pick = _sample(form, pc, list(same_heading) + [n for n in prefer if n not in same_heading])
    keep = derive_layout.TAUGHT_FRAME
    try:
        if frame is not None:                 # 사람이 정한(또는 제안한) 도면 영역 안에서 노트를 짓는다
            derive_layout.TAUGHT_FRAME = list(frame)
        return [round(v, 1) for v in derive_layout.notes_from_heading(pick, word, max(word.height, 1.0))]
    finally:
        derive_layout.TAUGHT_FRAME = keep


def notes(form, prefer_page: int | None = None, prefer=(), frame=None) -> dict | None:
    """NOTES 영역 제안 — 제목이 **두 장 이상**에서 같은 자리(그 글자 높이 안)에 인쇄된 곳.

    한 장에만 있는 `NOTES` 는 도면 안 주석일 수 있다.  자리는 그 제목을 누른 것과 같은 계산
    (`notes_rect`).  돌려주는 장은 `prefer_page`(계기가 가장 많은 장)에 그 제목이 있으면 그 장,
    아니면 그 제목이 있는 첫 장."""
    _ds, derive_layout, _lr, _pc = _engine()
    spots = []
    for pc in form:
        for r, t in pc.words:
            if t.upper().rstrip(":") == derive_layout.NOTES_HEADING:
                spots.append((pc, r))
                break
    groups: list = []
    for pc, r in spots:
        h = max(r.height, 1.0)
        for g in groups:
            g0 = g[0][1]
            if abs(g0.x0 - r.x0) <= h and abs(g0.y0 - r.y0) <= h:
                g.append((pc, r))
                break
        else:
            groups.append([(pc, r)])
    best = max(groups, key=len, default=None)
    if not best or len(best) < 2:
        return None
    pc, r = next(((p, w) for p, w in best if p.page_no == prefer_page), best[0])
    rect = notes_rect(form, pc, r, prefer=prefer, frame=frame)
    return {"page_no": pc.page_no, "rect": rect, "pages_with_heading": len(best),
            "click": [round((r.x0 + r.x1) / 2, 1), round((r.y0 + r.y1) / 2, 1)]}


def propose(pages, form, anchors, needs) -> dict:
    """할 일(`needs`)마다 제안 — 없는 것은 None.  NOTES 는 선택 항목이라 늘 짐작해 본다."""
    out = {"legend_page": None, "bubbles": None, "notes": None, "drawing": None}
    keys = {n.rstrip("?") for n in needs}
    if "legend" in keys:
        out["legend_page"] = legend_pages(pages)
    if "bubbles" in keys:
        out["bubbles"] = bubbles(form, anchors)
    best, seen = None, ()
    if out["bubbles"]:
        best, seen = out["bubbles"]["examples"][0]["page_no"], out["bubbles"]["pages"]
    out["drawing"] = drawing_area(form)
    out["notes"] = notes(form, best, prefer=seen, frame=(out["drawing"] or {}).get("rect"))
    return out


def propose_pdf(pdf: str, needs: list) -> dict:
    """서버 밖 일꾼(`page_warm.call`)이 부르는 입구 — PDF 를 스스로 열어 `propose` 를 돈다.

    큰 도면은 30~70초가 걸리고(곡선을 장마다 다시 읽는다) 그 동안 서버 프로세스가 붙들리면 대시보드의
    살아 있나 확인(3초)이 실패한다 (hotfix56).  그래서 분석이 멈춘 그 순간 일꾼에게 맡겨 두고, 사람이
    판을 열 때는 끝난 답을 받는다 (`main._prefetch_proposals`)."""
    ds, derive_layout, _lr, pages = _open(pdf)
    fp = derive_layout._form_pages(pages)
    form = (fp[0] if fp else None) or pages
    try:
        return propose(pages, form, ds.RULESET_V3.anchors, list(needs))
    finally:
        release_pages(pages)


# 일꾼 프로세스가 든 **마지막 PDF** 의 장들 — 같은 PDF 를 묻는 다음 호출이 다시 열지 않게 (A1 93장 6초).
# 그림(`_drawings` 등 lazy 값)은 쓰고 나서 놓는다 (`release_pages`) — 낱말만 남긴다.
_PAGES: dict = {}
_NEEDS: dict = {}


def _open(pdf: str, only=None):
    from app import pipeline  # noqa: F401  — 엔진 경로와 설정을 세운다
    import os
    ds, derive_layout, legend_rules, pidcache = _engine()
    if only:
        _doc, pages = pidcache.load_pages(pdf, only=only)
        return ds, derive_layout, legend_rules, pages
    key = (str(pdf), os.stat(pdf).st_mtime_ns)
    if _PAGES.get("key") != key:
        _PAGES.clear()
        doc, pages = pidcache.load_pages(pdf)
        _PAGES.update({"key": key, "doc": doc, "pages": pages})
    return ds, derive_layout, legend_rules, _PAGES["pages"]


def release_pages(pages) -> None:
    """장의 lazy 값(그림 · 선분 · 잉크 인덱스 …)을 놓는다 — 일꾼이 낱말만 들고 산다."""
    for pc in pages:
        for name in ("_drawings", "_rects", "_segments", "_ink_strokes", "_ink_index", "_star_segs", "_star_np",
                     "_stroke_memo", "_hist_rows"):
            if hasattr(pc, name):
                try:
                    setattr(pc, name, None)
                except Exception:                      # noqa: BLE001
                    pass


def suggest(pages, form) -> dict:
    """어느 장을 먼저 띄울지 — 화면 편의일 뿐 판정에 안 쓴다 (`main._teach_suggest` 와 같은 판정)."""
    ds, _dl, legend_rules, pidcache = _engine()
    anchors = ds.RULESET_V3.anchors
    score = {pc.page_no: sum(1 for _r, t in pc.words if t in anchors) for pc in form}
    drawing = max(score, key=lambda n: (score[n], -n)) if score else (form[0].page_no if form else 1)
    legend = None
    for pc in pages:
        words = {t.upper() for _r, t in pidcache.tokens(pc.words)}
        if {"LEGEND", "SYMBOL", "SYMBOLS"} & words and ({"VALVES", "ACTUATORS", "SIGNAL"} & words):
            legend = pc.page_no
            break
    if legend is None:
        pc = legend_rules._page_with(pages, "FIRST LETTER")
        legend = pc.page_no if pc is not None else (pages[0].page_no if pages else 1)
    return {"drawing": drawing, "legend": legend}


def needs_pdf(pdf: str, saved: dict) -> dict:
    """`main._teach_needs` 의 무거운 반(Symbol & Legend 칸 · 버블)과 먼저 띄울 장을 서버 밖 일꾼이 — 같은 판정.
    가르친 값(`saved`)을 모듈 전역(`TAUGHT*`)에 얹고 끝에 되돌린다 (일꾼 프로세스라 다른 요청과 안 겹친다).
    답은 (PDF · 시각 · 가르친 값)으로 기억한다."""
    import json
    import os
    key = (str(pdf), os.stat(pdf).st_mtime_ns, json.dumps(saved or {}, sort_keys=True, default=str))
    got = _NEEDS.get(key)
    if got is not None:
        return got
    ds, derive_layout, legend_rules, pages = _open(pdf)
    fp = derive_layout._form_pages(pages)
    form = (fp[0] if fp else None) or pages
    needs = []
    keep_page, keep_taught, keep_b = legend_rules.TAUGHT_PAGE, legend_rules.TAUGHT, ds.TAUGHT_BUBBLES
    try:
        lp = saved.get("legend_page") or []
        legend_rules.TAUGHT_PAGE = [int(x["page_no"]) for x in (lp if isinstance(lp, list) else [lp])] or None
        legend_rules.TAUGHT = {k: {"page_no": v["page_no"], "rect": v["rect"]}
                               for k, v in (saved.get("legend") or {}).items()}
        if any(legend_rules._page_with(pages, h) is None for h in legend_rules.TEACHABLE_HEADINGS):
            needs.append("legend")
        by = {pc.page_no: pc for pc in pages}
        temps = [t for t in (ds.learn_bubble_template(by[b["page_no"]], b["rect"])
                             for b in (saved.get("bubbles") or []) if b.get("page_no") in by) if t]
        ds.TAUGHT_BUBBLES = temps
        anchors = ds.RULESET_V3.anchors
        busy = sorted(form, key=lambda pc: -sum(1 for _r, t in pc.words if t in anchors))[:5]
        if busy and sum(1 for pc in busy for _r, t in pc.words if t in anchors) >= 3 \
                and not any(ds.bubble_outlines(pc) for pc in busy):
            needs.append("bubbles")
        got = {"needs": needs, "suggest": suggest(pages, form)}
    finally:
        legend_rules.TAUGHT_PAGE, legend_rules.TAUGHT, ds.TAUGHT_BUBBLES = keep_page, keep_taught, keep_b
        release_pages(pages)
    if len(_NEEDS) >= 8:
        _NEEDS.pop(next(iter(_NEEDS)))
    _NEEDS[key] = got
    return got


def preview_bubbles_pdf(pdf: str, templates: list, page_no: int, count_nos: list) -> tuple:
    """버블 미리보기의 무거운 부분 — 이 장에서 찾은 버블 사각형과 장마다의 수 (`main.teach_preview` 와 같은 함수)."""
    ds, _dl, _lr, pages = _open(pdf)
    by = {pc.page_no: pc for pc in pages}
    try:
        here = [[round(v, 1) for v in o.rect] for o in ds.taught_bubbles(by[int(page_no)], templates)] if int(page_no) in by else []
        per_page = {n: len(ds.taught_bubbles(by[n], templates)) for n in count_nos if n in by}
    finally:
        release_pages(pages)
    return here, per_page
