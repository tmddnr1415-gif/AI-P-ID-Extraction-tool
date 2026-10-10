"""hotfix62 — 첫 화면 카드가 말하는 **도면 사실** 셋: 프로젝트 제목 · 장마다 현재 개정의 날짜 · 최상위 개정.

판정 엔진이 아니다.  분석이 끝난 뒤(또는 예전 분석에 대해 한 번) PDF 의 글자층을 다시 읽어
**그 도면이 인쇄한 것만** 옮겨 적는다.  지문·행·Q'ty 에 닿지 않는다 (`job.facts_json` 에만 산다).

* **프로젝트 제목** — 타이틀블록 캡션 `PROJECT NAME` / `PROJECT TITLE` (낱말은 `derive_layout.
  CAPTION_VOCAB["project_name"]` 과 같은 것) 바로 아래, 캡션보다 **큰 글자**로 인쇄된 첫 줄.
  장마다 읽고 다수결 (`pidcache._scope_by_project` 와 같은 생각 — 다수가 그 프로젝트다).
  실측: AL NOUF1 `AL NOUF1 PROJECT` · TC2 `TAICHUNG CCPP PHASE II` · QFE `QATAR FACILITY E IWPP`.
* **개정 날짜** — 개정 이력 표에서 **그 장의 현재 Rev 와 같은 줄**에 인쇄된 날짜.  Rev 는 엔진이 이미
  읽어 `pid_page.rev` 에 둔 값을 받는다 (여기서 다시 읽지 않는다).  같은 Rev 가 서로 다른 날짜의 줄
  여럿에 걸리면 **고르지 않는다** (빈칸).  표가 획으로 그려진 장은 글자가 없어 빈칸이다 — 지어내지 않는다.
* **최상위 개정** — 날짜를 읽은 장 중 **가장 늦은 날짜**의 Rev.  QFE 처럼 `A · B · C · 0 · 1A · 1B`
  순으로 매기는 양식은 글자 순서가 개정 순서가 아니다 (사전순 최댓값은 `C` 지만 도면의 이력 표는
  `1B` 가 가장 나중이다).  날짜를 하나도 못 읽으면 예전 규칙(`job.doc_rev`, config
  `revision.document_rule`)으로 돌아가고 그렇게 말한다.
"""
from __future__ import annotations

import collections
import datetime as _dt
import re
from pathlib import Path

# 월 이름은 영어 달력이지 프로젝트 값이 아니다.
_MON = {m: i for i, m in enumerate(
    ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"), 1)}
_D_MON_Y = re.compile(r"^(\d{1,2})[.\-/ ]?\s?([A-Z]{3})[A-Z]*[.\-/ ]?\s?(\d{4}|\d{2})$")
_Y_M_D = re.compile(r"^(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})$")
_N_N_Y4 = re.compile(r"^(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})$")
_N_N_N2 = re.compile(r"^(\d{2})[.\-/](\d{2})[.\-/](\d{2})$")

_PROJECT = {"PROJECT"}
_NAME = {"NAME", "TITLE", "NAME:", "TITLE:"}


def parse_date(text: str):
    """(날짜처럼 생겼는가, ISO 날짜 | None).  모양이 모호하면 ISO 를 지어내지 않는다.

    `26.08.21` 은 날짜이지만 YY.MM.DD 인지 DD.MM.YY 인지 글자가 말하지 않으므로 ISO 가 없다.
    `03.04.2026` 도 일·월이 갈리지 않으면 ISO 가 없다 (13 이상인 칸이 있을 때만 정한다).
    """
    t = (text or "").strip().upper().rstrip(",;")
    m = _D_MON_Y.match(t)
    if m and m.group(2) in _MON:
        d, mon, y = int(m.group(1)), _MON[m.group(2)], int(m.group(3))
        y = y + 2000 if y < 100 else y
        return True, _iso(y, mon, d)
    m = _Y_M_D.match(t)
    if m:
        return True, _iso(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = _N_N_Y4.match(t)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if a > 12 >= b:
            return True, _iso(y, b, a)
        if b > 12 >= a:
            return True, _iso(y, a, b)
        return (a <= 31 and b <= 31), None
    m = _N_N_N2.match(t)
    if m:
        return True, None
    return False, None


def _iso(y, m, d):
    try:
        return _dt.date(y, m, d).isoformat()
    except ValueError:
        return None


def _page_words(page):
    """표시 좌표의 낱말 (회전 장도 같은 축) · 같은 자리에 겹쳐 찍힌 글자는 하나로."""
    import pymupdf
    m = page.rotation_matrix
    seen, out = set(), []
    for w in page.get_text("words"):
        r = pymupdf.Rect(w[:4]) * m
        key = (round(r.x0, 1), round(r.y0, 1), w[4])
        if key in seen:
            continue
        seen.add(key)
        out.append((r, w[4]))
    return out


def _same_line(a, b) -> bool:
    ca, cb = (a.y0 + a.y1) / 2, (b.y0 + b.y1) / 2
    return abs(ca - cb) <= max(a.height, b.height) / 2


def project_title(words) -> str:
    """캡션 `PROJECT NAME|TITLE` 아래, 캡션보다 큰 글자의 첫 줄."""
    best = ""
    for i, (r, t) in enumerate(words):
        if t.upper() not in _PROJECT:
            continue
        nxt = [(rr, tt) for rr, tt in words
               if tt.upper() in _NAME and _same_line(r, rr) and 0 <= rr.x0 - r.x1 <= r.height * 2]
        if not nxt:
            continue
        cap_h = r.height
        below = [(rr, tt) for rr, tt in words
                 if rr.height > cap_h * 1.1 and rr.y0 >= r.y0 + cap_h * 0.5
                 and rr.y0 - r.y1 <= cap_h * 3 and rr.x0 >= r.x0 - cap_h]
        if not below:
            continue
        top = min(below, key=lambda w: w[0].y0)[0]
        line = sorted((w for w in below if _same_line(w[0], top)), key=lambda w: w[0].x0)
        text = " ".join(tt for _rr, tt in line).strip()
        if len(text) > len(best):
            best = text
    return best


def _date_tokens(words):
    """날짜 낱말 — `19.` + `SEP.2025` 처럼 두 조각으로 인쇄된 것은 이어 읽는다."""
    out = []
    by_line = sorted(words, key=lambda w: (round((w[0].y0 + w[0].y1) / 2), w[0].x0))
    for i, (r, t) in enumerate(by_line):
        ok, iso = parse_date(t)
        if ok:
            out.append((r, t, iso))
            continue
        if i + 1 < len(by_line):
            r2, t2 = by_line[i + 1]
            if _same_line(r, r2) and 0 <= r2.x0 - r.x1 <= r.height:
                ok, iso = parse_date(t + t2)
                if ok:
                    out.append((r | r2, f"{t} {t2}", iso))
    return out


_SHORT = re.compile(r"^[A-Z0-9]{1,3}$")


def history(words, rev: str) -> list:
    """이력 표의 줄들 — [(Rev, 날짜 원문, ISO | None)].

    Rev 열은 **그 장의 현재 Rev 낱말이 선 자리**로 찾는다 (엔진이 읽은 값 · 날짜 줄 위에 있는 것).
    다른 날짜 줄에서는 그 열에 선 짧은 낱말이 그 줄의 Rev 다.  열을 못 찾으면 빈 목록.
    """
    rev = (rev or "").strip()
    dates = _date_tokens(words)
    if not rev or not dates:
        return []
    cols = [rr for r, _t, _i in dates for rr, tt in words
            if tt.strip() == rev and _same_line(r, rr) and not rr.intersects(r)]
    if not cols:
        return []
    out = []
    for r, text, iso in dates:
        for col in cols:
            cx = (col.x0 + col.x1) / 2
            got = [tt.strip() for rr, tt in words
                   if _SHORT.match(tt.strip()) and _same_line(r, rr) and not rr.intersects(r)
                   and abs((rr.x0 + rr.x1) / 2 - cx) <= max(col.width, col.height)]
            if len(got) == 1:
                out.append((got[0], text, iso))
                break
    return sorted(set(out))


def rev_date(rows, rev: str):
    """그 장의 현재 Rev 의 날짜 — (원문, ISO | None, 사유).  같은 Rev 가 여러 번 발행됐으면
    가장 늦은 날짜 (지금 그 장은 마지막 발행본이다)."""
    rev = (rev or "").strip()
    if not rev:
        return "", None, "개정 못 읽음"
    hits = [(text, iso) for r, text, iso in rows if r == rev]
    if not hits:
        return "", None, "이력 표에 그 개정 줄의 날짜가 글자로 없음"
    if len({t for t, _i in hits}) == 1:
        return hits[0][0], hits[0][1], ""
    dated = [h for h in hits if h[1]]
    if len(dated) == len(hits):
        text, iso = max(dated, key=lambda h: h[1])
        return text, iso, f"같은 개정이 {len(hits)}번 발행됨 — 가장 늦은 것"
    return "", None, f"그 개정이 날짜 {len(hits)}개 줄에 걸려 고르지 않음"


def read(pdf_path, pages: list) -> dict:
    """`pages` = `db.page_revisions` 그대로 (page_no · page_kind · rev · rev_date)."""
    import pymupdf
    path = Path(pdf_path or "")
    if not path.is_file():
        return {"error": "PDF 파일이 없습니다"}
    doc = pymupdf.open(str(path))
    titles = collections.Counter()
    per_page = {}
    before = set()           # (앞 Rev, 뒤 Rev) — 장마다의 이력 표 순서를 모은 것
    try:
        for p in pages:
            pn = int(p.get("page_no") or 0)
            if not 1 <= pn <= doc.page_count:
                continue
            words = _page_words(doc[pn - 1])
            t = project_title(words)
            if t:
                titles[t] += 1
            rows = history(words, p.get("rev") or "")
            seq = []
            for r, _text, iso in sorted((x for x in rows if x[2]), key=lambda x: x[2]):
                if not seq or seq[-1] != r:
                    seq.append(r)
            for i, a in enumerate(seq):           # 한 장의 이력 표가 말하는 앞뒤
                for b in seq[i + 1:]:
                    if a != b:
                        before.add((a, b))
            text, iso, why = rev_date(rows, p.get("rev") or "")
            if not text and p.get("rev_date"):          # 엔진이 이력 표 순서로 이미 읽은 값
                text = str(p["rev_date"])
                iso = parse_date(text)[1]
                why = ""
            per_page[pn] = {"rev": str(p.get("rev") or ""), "kind": p.get("page_kind") or "",
                            "date": text, "iso": iso, "why": why}
    finally:
        doc.close()
    title = titles.most_common(1)[0][0] if titles else ""
    return {"project_title": title,
            "project_title_pages": titles.get(title, 0),
            "project_title_variants": dict(titles),
            "pages": per_page,
            "rev_before": sorted([a, b] for a, b in before)}


def _closure(pairs):
    later = collections.defaultdict(set)
    for a, b in pairs:
        later[a].add(b)
    changed = True
    while changed:
        changed = False
        for a in list(later):
            add = set().union(*(later.get(b, set()) for b in later[a])) - later[a]
            if add:
                later[a] |= add
                changed = True
    return later


def top_revision(facts: dict, doc_rev: str = "") -> dict:
    """최상위 개정 — **이 문서의 이력 표가 말하는 순서**에서 뒤에 선 현재 Rev, 날짜는 그 Rev 의 가장 늦은 발행.

    순서는 장마다의 이력 표(날짜순)에서 모은 앞뒤 관계다.  QFE 실측: `A < B < C < 0 < 1A < 1B < 1C`
    — 글자 순서가 개정 순서가 아니고(사전순 최댓값은 `C`), 새로 그린 장은 늦은 날짜에 `A` 로 처음
    나오므로 "가장 늦은 날짜의 Rev" 도 답이 아니다.  어느 표에도 함께 나오지 않아 앞뒤를 모르는 둘
    (`1A` ↔ `0A` — 다른 장 계열)은 **날짜가 정한다**.  현재 Rev 중 하나라도 어느 이력 표에도 없으면
    (표가 획이라 글자가 없는 장) 순서를 모르는 것이므로 예전 규칙(`doc_rev`)으로 돌아가고 그렇게 말한다.
    """
    pages = (facts or {}).get("pages") or {}
    pool = [v for v in pages.values() if v.get("kind") == "PID"] or list(pages.values())
    later = _closure(tuple(x) for x in ((facts or {}).get("rev_before") or []))
    known = set(later) | {b for v in later.values() for b in v}
    current = {v["rev"] for v in pool if v.get("rev")}

    def latest(rev):
        isos = [v["iso"] for v in pool if v.get("rev") == rev and v.get("iso")]
        return max(isos) if isos else ""

    if current and current <= known:
        top = [r for r in current if not (later.get(r, set()) & current)]
        rev = max(top, key=lambda r: (latest(r), r))
        basis = "HISTORY" if len(top) == 1 else "HISTORY+DATE"
    else:
        rev = (doc_rev or "").strip()
        basis = "RULE" if rev else "NONE"
    mine = [v for v in pool if v.get("rev") == rev]
    dated = [v for v in mine if v.get("iso")]
    if dated:
        best = max(dated, key=lambda v: v["iso"])
        date, iso = best["date"], best["iso"]
    else:
        date = next((v["date"] for v in mine if v.get("date")), "")
        iso = None
    return {"rev": rev, "date": date, "iso": iso, "basis": basis,
            "sheets": len(mine), "unordered": sorted(current - known)}


def order_pairs(*facts) -> list:
    """여러 문서의 이력 표 앞뒤를 합쳐 이어진 것까지 편 목록 — `compare_document_revision(order=)` 용."""
    pairs = set()
    for f in facts:
        pairs |= {tuple(x) for x in ((f or {}).get("rev_before") or [])}
    later = _closure(pairs)
    return sorted([a, b] for a, bs in later.items() for b in bs)
