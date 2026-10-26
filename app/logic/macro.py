"""매크로 블록 → 그 내부 동작을 정의한 Typical 시트 (L12).

Logic 시트는 MOV · MCC · 스위치기어 같은 반복 동작을 **매크로 블록** 하나로 그린다 — 큰 상자 안에 단자 이름
(A-MD · EN_OPEN · CMD1 · READY …)을 인쇄하고, 그 상자의 내부 동작은 묶음 앞쪽의 Typical 시트
(`MOV BLOCK (OPEN-CLOSE) (TYPE-III-1)` 등)가 왼쪽 입력 행 · 오른쪽 출력 행으로 정의한다.

맞대기는 도면이 준 글자만 쓴다 (코드에 단자 이름 · 시트 이름이 없다):
  ① 범례의 약어표 (G004 처럼 진짜 글자로 인쇄된 `A_OPEN : AUTO OPEN` 꼴 줄) — 단자 이름 ↔ 뜻
  ② Typical 시트의 행 설명 (`AUTO OPEN` · `OPENED STATUS` …)
  ③ 매크로 상자 안 글자와 시트 제목이 겹치는 낱말 (같은 단자 구성의 Typical 이 둘 이상일 때 가른다)
단자 이름 → (①로) 뜻 → (②와) 행.  ①에 없으면 단자 이름 조각이 행 설명 낱말의 머리와 맞는지로 본다.
한 행에는 단자 하나 (점수 순으로 하나씩).  맞는 행이 없는 단자는 '연결 못 함' 으로 남긴다 (지어내지 않는다).
"""
from __future__ import annotations

import json

import re

from . import geom
from functools import lru_cache

NAME_MIN = 0.72          # 단자 이름 ↔ 약어 닮음 하한 (한 글자 다름까지 — OVRD1 ↔ OVRID1)
PAIR_MIN = 0.42          # 단자 ↔ 행 점수 하한


def _norm(t):
    return _norm_s(t or "") if isinstance(t, str) or not t else re.sub(r"[^A-Z0-9]", "", (t or "").upper())


@lru_cache(maxsize=65536)
def _norm_s(t):                 # L28 — 같은 단자 이름 · 행 설명을 수십만 번 다시 다듬었다 (값은 같다)
    return re.sub(r"[^A-Z0-9]", "", (t or "").upper())


def _skel(t):
    """O/0 · I/1 을 같은 글자로 — 선으로 그린 글자는 둘을 자주 바꿔 읽는다 (CMD0 ↔ CMDO)."""
    return _skel_s(t or "") if isinstance(t, str) or not t else _norm(t).replace("0", "O").replace("1", "I")


@lru_cache(maxsize=65536)
def _skel_s(t):
    return _norm_s(t).replace("0", "O").replace("1", "I")


def _lev(a, b):
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


@lru_cache(maxsize=200000)
def name_sim(a, b):
    a, b = _skel(a), _skel(b)
    if not a or not b:
        return 0.0
    s = 1.0 - _lev(a, b) / max(len(a), len(b))
    # 끝 글자 하나를 못 읽은 것 (FL- ↔ FLT · CMD ↔ CMD1) — 한쪽이 다른 쪽의 머리이고 한 글자만 모자라면
    if len(a) >= 2 and len(b) >= 2 and abs(len(a) - len(b)) == 1 and (a.startswith(b) or b.startswith(a)):
        s = max(s, 0.75)
    # 끝의 0/1(O/I)이 다르면 뜻이 반대다 — CMD1 ↔ CMD0 · OVRD1 ↔ OVRD0 은 닮은 것이 아니다
    if a[-1] in "OI" and b[-1] in "OI" and a[-1] != b[-1] and a[:-1] and b[:-1]:
        s *= 0.5
    return s


def _words(t):
    return [w for w in re.findall(r"[A-Z]+", (t or "").upper().split("(")[0]) if len(w) >= 2]


def _wmatch(a, b):
    """같은 낱말 — 같거나 · 한쪽이 다른 쪽의 머리(OPEN ↔ OPENED) · 긴 낱말의 오탈자 한 글자(OPENEND ↔ OPENED · CONDITON)."""
    if a == b:
        return True
    k = min(len(a), len(b))
    if k >= 4 and a[:4] == b[:4] and (a.startswith(b[:k]) or b.startswith(a[:k])):
        return True
    return k >= 5 and a[:4] == b[:4] and _lev(a, b) <= 1


@lru_cache(maxsize=400000)
def desc_sim(a, b):
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return 0.0
    hit = sum(1 for x in wa if any(_wmatch(x, y) for y in wb))
    hit2 = sum(1 for y in wb if any(_wmatch(x, y) for x in wa))
    return (hit + hit2) / (len(wa) + len(wb))


def legend_abbr(doc):
    """범례 약어표 — 진짜 글자로 인쇄된 `<약어>   : <뜻>` 줄 (같은 높이 · 약어가 바로 왼쪽).  → [(약어, 뜻)]"""
    out = []
    for page in doc:
        lines = geom.text_lines(page)
        defs = [(bb, t) for bb, t in lines if t.startswith(":") and len(t) > 2]
        if len(defs) < 3:
            continue
        names = [(bb, t) for bb, t in lines if not t.startswith(":") and " " not in t and len(t) <= 14]
        for bb, t in defs:
            h = bb[3] - bb[1]
            cand = [(nb, nt) for nb, nt in names if abs((nb[1] + nb[3]) / 2 - (bb[1] + bb[3]) / 2) < 0.5 * h
                    and nb[2] <= bb[0] + 0.5 * h and bb[0] - nb[2] < 12 * h]
            if cand:
                nb, nt = max(cand, key=lambda c: c[0][2])
                out.append((nt, t[1:].strip()))
    return out


@lru_cache(maxsize=400000)
def _pin_row_score(pin, desc, abbr):
    best = 0.0
    sk = _skel(pin)
    prefix = 0.0         # 그 행 뜻의 약어와 단자 이름의 머리가 같다 (FD_OPEN ↔ FDbk1 = OPENED STATUS)
    for a, d in abbr:
        ns = name_sim(pin, a)
        ds = desc_sim(d, desc)
        if ns >= NAME_MIN:
            best = max(best, ns * ds)
        if ds >= 0.75:
            ska = _skel(a)
            cp = 0
            while cp < min(len(sk), len(ska)) and sk[cp] == ska[cp]:
                cp += 1
            if cp >= 2:
                prefix = max(prefix, min(0.3, 0.1 * cp))
    # 범례에 없는 단자 — 단자 이름 조각이 설명 낱말의 머리와 맞는지 (FD_OPEN ↔ OPENED STATUS · A_STOP ↔ AUTO STOP)
    ws = _words(desc)
    if ws and sk:
        hits = [w for w in ws if len(w) >= 4 and _skel(w[:4]) in sk]
        if hits:
            best = max(best, 0.5 * len(hits) / len(ws) + 0.2 + prefix)
    return best


def _assign(pins, rows, abbr):
    """pins = [(key, pin)] · rows = [(n, desc, abv)] → {key: (n, desc, score)} — 점수 순으로 하나씩."""
    abbr = tuple(abbr)
    cand = []
    for key, pin in pins:
        if not pin:
            continue
        for row in rows:
            n, desc = row[0], row[1]
            abv = row[2] if len(row) > 2 else ""
            # 표가 단자 약어(ABV) 칸을 인쇄했으면 그 글자가 답이다 (19VA Typical · L21)
            s = 1.0 if abv and _skel(abv) == _skel(pin) else _pin_row_score(pin, desc, abbr)
            if s >= PAIR_MIN:
                cand.append((s, key, n, desc))
    cand.sort(key=lambda c: -c[0])
    got, used = {}, set()
    for s, key, n, desc in cand:
        if key in got or n in used:
            continue
        got[key] = (n, desc, round(s, 3))
        used.add(n)
    return got


def _name_fit(name, title):
    """매크로 이름의 번호 붙은 낱말(`PS4` · `MTS1`)이 시트 제목에 있나 (L23 · 1A5J MACRO-PS2~PS5).
    True = 같은 낱말이 있다 · False = 같은 글자에 다른 번호만 있다 · None = 말할 것이 없다."""
    tok = lambda t: set(re.findall(r"(?<![A-Z0-9])([A-Z]{1,4})(\d{1,3})(?![A-Z0-9])", (t or "").upper().replace("-", " ").replace("_", " ")))
    a, b = tok(name), tok(title)
    a = {x for x in a if x[0] not in ("TYPE",)}
    if not a or not b:
        return None
    if a & b:
        return True
    if {x[0] for x in a} & {x[0] for x in b}:
        return False
    return None


def _top_line(page, bbox, first_pin_y=None):
    """상자 안 첫 단자보다 위에 인쇄된 글 (단자가 없으면 맨 윗줄) — 매크로 이름."""
    ws = [w for w in geom.words(page)
          if bbox[0] - 1 <= (w[0] + w[2]) / 2 <= bbox[2] + 1 and bbox[1] - 1 <= (w[1] + w[3]) / 2 <= bbox[3] + 1]
    if not ws:
        return ""
    h = min(w[3] - w[1] for w in ws)
    if first_pin_y is not None:
        keep = [w for w in ws if (w[1] + w[3]) / 2 < first_pin_y - 0.5 * h]
    else:
        keep = []
    if not keep:
        top = min((w[1] + w[3]) / 2 for w in ws)
        keep = [w for w in ws if (w[1] + w[3]) / 2 - top <= 0.5 * h]
    return " ".join(w[4] for w in sorted(keep, key=lambda w: (round(w[1]), w[0])))


def _caption(page, bbox):
    """매크로 상자 안에 **진짜 글자**로 인쇄된 이름 (`MOV BLOCK (OPEN CLOSE) <TYPE-Ⅲ-1>`)."""
    ws = [w for w in geom.words(page)
          if bbox[0] - 1 <= (w[0] + w[2]) / 2 <= bbox[2] + 1 and bbox[1] - 1 <= (w[1] + w[3]) / 2 <= bbox[3] + 1]
    ws.sort(key=lambda w: (round(w[1]), w[0]))
    t = " ".join(w[4] for w in ws)
    return t.replace("Ⅲ", "III").replace("Ⅱ", "II").replace("Ⅰ", "I")


def _type_code(t):
    m = re.search(r"TYP\w?\W*([IVX]+)\W*(\d+)", (t or "").upper().replace("Ⅲ", "III").replace("Ⅱ", "II")
                  .replace("Ⅳ", "IV").replace("Ⅰ", "I"))
    return f"{m.group(1)}-{m.group(2)}" if m else ""


def _title_bonus(block, title, caption=""):
    """상자 안 글자 · 이름과 시트 제목이 겹치는 정도 (0~1.5).  이름의 TYPE 번호가 같으면 +0.5."""
    have = set(_words(block.get("read", ""))) | set(_words(caption))
    for ln in block.get("lines", []):
        have |= set(_words(ln[-1]))
    tw = [w for w in _words(title) if len(w) >= 3]
    frac = sum(1 for w in tw if any(_wmatch(w, h) for h in have)) / (len(tw) or 1)
    tc = _type_code(caption) or _type_code(block.get("read", ""))
    return frac + (0.5 if tc and tc == _type_code(title) else 0.0)


def link(doc, sheets, library=None):
    """시트 목록을 제자리에서 고친다 — 매크로 블록마다 `macro` = 그 Typical 시트 · 단자 ↔ 행.

    L22 — 그 묶음에 Typical 시트가 없으면 학습 사전(library.typicals — 다른 묶음에서 배운 Typical)을 단자 이름으로
    맞대 본다 (문턱 library.MATCH_MIN).  고르면 그 Typical 시트 사본을 돌려준다 (가짜 쪽 번호 · 결과의 library_sheets)."""
    from . import library as LB
    abbr = tuple(dict.fromkeys(legend_abbr(doc)))       # 같은 줄은 한 번 — 점수 캐시의 열쇠가 된다
    lib_typ = (library or {}).get("typicals") or {}
    lib_tables, lib_pages, lib_sheets = {}, {}, []
    for tid, ty in lib_typ.items():
        st = ty.get("sheet") or {}
        L_ = [(r["n"], r.get("desc", ""), r.get("abv", "") or r.get("kks", "")) for r in st.get("table", []) if r["side"] == "L" and r.get("desc")]
        R_ = [(r["n"], r.get("desc", ""), r.get("abv", "") or r.get("kks", "")) for r in st.get("table", []) if r["side"] == "R" and r.get("desc")]
        if L_ and R_:
            lib_tables[tid] = (L_, R_)

    def from_library(b, pin_in, pin_out, n_pins, cap, tc):
        best = None
        for tid, (L_, R_) in lib_tables.items():
            ty = lib_typ[tid]
            ttc = _type_code(ty.get("title", "")) or _type_code(ty.get("caption", ""))
            if tc and ttc and tc != ttc:
                continue
            gi, go = _assign(pin_in, L_, abbr), _assign(pin_out, R_, abbr)
            score = (sum(v[2] for v in gi.values()) + sum(v[2] for v in go.values())) / n_pins
            score += (0.6 if cap else 0.25) * _title_bonus(b, ty.get("title", ""), cap)
            if best is None or score > best[0]:
                best = (score, tid, gi, go)
        if best is None or best[0] < LB.MATCH_MIN:
            return None
        score, tid, gi, go = best
        if tid not in lib_pages:
            pg = LB.LIB_PAGE0 + len(lib_pages) + 1
            lib_pages[tid] = pg
            ty = lib_typ[tid]
            cp = json.loads(json.dumps(ty["sheet"]))
            cp["page"] = pg
            cp["sheet_no"] = f"LIB {ty.get('sheet_no', '')}".strip()   # 이 묶음의 시트 번호와 섞이지 않게 (FM/TO 로 안 맞는다)
            cp["library"] = {"id": tid, "from": ty.get("from", ""), "png": ty.get("png"), "sheet_no": ty.get("sheet_no", "")}
            lib_sheets.append(cp)
        return score, tid, gi, go
    tables = {}
    for s in sheets:
        L = [(t["n"], t.get("desc", ""), t.get("abv", "") or t.get("kks", "")) for t in s.get("table", []) if t["side"] == "L" and t.get("desc")]
        R = [(t["n"], t.get("desc", ""), t.get("abv", "") or t.get("kks", "")) for t in s.get("table", []) if t["side"] == "R" and t.get("desc")]
        if L and R:
            tables[s["page"]] = (L, R)
    for s in sheets:
        for bid, b in s["blocks"].items():
            if b.get("func") != "MACRO":
                continue
            ports = [p for p in s["ports"] if p["block"] == bid]
            cap = _caption(doc[s["page"] - 1], b["bbox"])
            b["caption"] = cap
            name = _top_line(doc[s["page"] - 1], b["bbox"], min((p["at"][1] for p in ports), default=None))   # 첫 단자 위 글 = 매크로 이름 (단자 이름 L_PS3 를 섞지 않는다)
            pin_in = [(f"{p['at'][0]},{p['at'][1]}", p.get("pin", "")) for p in ports if p["dir"] == "in"]
            pin_out = [(f"{p['at'][0]},{p['at'][1]}", p.get("pin", "")) for p in ports if p["dir"] == "out"]
            ranked = []
            for t in sheets:
                if t["page"] == s["page"] or t["page"] not in tables:
                    continue
                L, R = tables[t["page"]]
                gi, go = _assign(pin_in, L, abbr), _assign(pin_out, R, abbr)
                n_pins = len([p for p in pin_in + pin_out if p[1]]) or 1
                score = (sum(v[2] for v in gi.values()) + sum(v[2] for v in go.values())) / n_pins
                score += (0.6 if cap else 0.25) * _title_bonus(b, t.get("title", ""), cap)
                nm = _name_fit(name, t.get("title", ""))
                if nm is False:
                    continue                       # 이름이 같은 계열 다른 번호 (PS4 ↔ PS3) — 고르지 않는다 (L23)
                if nm:
                    score += 0.5
                ranked.append((score, t, gi, go))
            ranked.sort(key=lambda r: -r[0])
            tc = _type_code(cap) or _type_code(b.get("read", ""))
            n_pins_ = len([p for p in pin_in + pin_out if p[1]]) or 1
            no_typ = (tc and ranked and not any(_type_code(r[1].get("title", "")) == tc for r in ranked)) or \
                not ranked or ranked[0][0] < 0.3
            lib = from_library(b, pin_in, pin_out, n_pins_, cap, tc) if (no_typ and lib_tables) else None
            if lib:
                score, tid, gi, go = lib
                pmap = {f"{p['at'][0]},{p['at'][1]}": p for p in ports}
                ty = lib_typ[tid]

                def items_(pins, got, pmap=pmap):
                    return [{"at": key, "net": pmap[key]["net"], "pin": pin, "row": got[key][0] if key in got else None,
                             "desc": got[key][1] if key in got else "", "score": got[key][2] if key in got else 0}
                            for key, pin in pins]
                b["macro"] = {"sheet": ty.get("sheet_no", ""), "page": lib_pages[tid], "title": ty.get("title", ""),
                              "score": round(score, 3), "inputs": items_(pin_in, gi), "outputs": items_(pin_out, go),
                              "library": {"id": tid, "from": ty.get("from", "")},
                              "why": f"이 묶음에 Typical 시트가 없어 학습 사전의 '{ty.get('sheet_no', '')} {ty.get('title', '')}' "
                                     f"({ty.get('from', '')}) 로 맞댔습니다",
                              "cands": [{"sheet": r[1]["sheet_no"], "page": r[1]["page"], "score": round(r[0], 3)} for r in ranked[:3]]}
                continue
            if tc and ranked and not any(_type_code(r[1].get("title", "")) == tc for r in ranked):
                # 이름이 TYPE 번호를 말하는데 그 번호의 Typical 시트가 이 묶음에 없다 — 닮은 다른 시트를 고르지 않는다
                b["macro"] = {"sheet": "", "page": None,
                              "why": f"이 묶음에 '{cap or tc}' 의 Typical 시트가 없습니다 (TYPE-{tc})",
                              "cands": [{"sheet": r[1]["sheet_no"], "page": r[1]["page"], "score": round(r[0], 3)} for r in ranked[:3]]}
                continue
            if not ranked or ranked[0][0] < 0.3:
                b["macro"] = {"sheet": "", "page": None, "why": "단자 이름에 맞는 Typical 시트를 찾지 못했습니다",
                              "cands": [{"sheet": r[1]["sheet_no"], "page": r[1]["page"], "score": round(r[0], 3)} for r in ranked[:3]]}
                continue
            score, t, gi, go = ranked[0]
            pmap = {f"{p['at'][0]},{p['at'][1]}": p for p in ports}

            def items(pins, got):
                out = []
                for key, pin in pins:
                    p = pmap[key]
                    g = got.get(key)
                    out.append({"at": key, "net": p["net"], "pin": pin,
                                "row": g[0] if g else None, "desc": g[1] if g else "", "score": g[2] if g else 0})
                return out
            m_ = {"sheet": t["sheet_no"], "page": t["page"], "title": t.get("title", ""), "score": round(score, 3),
                  "inputs": items(pin_in, gi), "outputs": items(pin_out, go),
                  "cands": [{"sheet": r[1]["sheet_no"], "page": r[1]["page"], "score": round(r[0], 3)} for r in ranked[:3]]}
            fam = [q for q in sheets if q is not t and q is not s and q["page"] in tables and _family(t, q, name)
                   and not any(bb.get("func") == "MACRO" for bb in q["blocks"].values())]
            if fam:
                _spread(m_, fam, tables, pin_in, pin_out, abbr)
            b["macro"] = m_
    return lib_sheets


# L38 — 내부 동작을 여러 장에 나눠 그린 매크로 (1A5J MACRO-PS3 <PRESELECTION (1/4)> … (4/4) · PS4 · PS5 는 열 장 넘게).
# 예전에는 첫 장 하나에만 이어 PS3 단자 35개 중 22개가 '연결 못 함' 이었다.  같은 매크로의 다른 장(제목의 머리가 같고 ·
# (k/n) 이 붙었거나 매크로 이름의 번호 낱말이 같은 장 · TYPE 번호가 다르지 않은 장)도 단자와 맞대고, 시뮬레이션 · 순차
# 동작은 그 장들을 한 장으로 합친 본문(`body`)을 쓴다 — 장 사이 FM 연결은 그 본문 안의 한 선이 된다.
ROW_PAGE = 1000          # 합친 본문에서 다른 장 행의 번호 = 쪽 × 1000 + 행 (한 장의 행은 1000 을 넘지 않는다)
ALSO_MIN = 0.6           # 같은 입력 단자를 받는 다른 장의 입력 행 (같은 신호가 여러 장에 들어간다) — 이 점수 이상만


def _stem(title):
    return _norm((title or "").split("<")[0])


def _family(t, q, name):
    if not _stem(t.get("title")) or _stem(t.get("title")) != _stem(q.get("title")):
        return False
    a, b = _type_code(t.get("title", "")), _type_code(q.get("title", ""))
    if a and b and a != b:
        return False
    part = re.compile(r"\(\s*\d+\s*/\s*\d+\s*\)")
    return bool(part.search(t.get("title", "")) or part.search(q.get("title", ""))) or _name_fit(name, q.get("title", "")) is True


def _spread(m, fam, tables, pin_in, pin_out, abbr):
    """첫 장에서 못 이은 단자를 같은 매크로의 다른 장 행과 맞댄다 → 행 번호 = 쪽 × ROW_PAGE + 행 · `parts` = 그 장들."""
    enc = lambda pg, n: pg * ROW_PAGE + n
    used_parts = set()
    for side, pins, key in (("in", pin_in, "inputs"), ("out", pin_out, "outputs")):
        got = {}
        for q in fam:
            L, R = tables[q["page"]]
            for k, (n, desc, sc) in _assign(pins, L if side == "in" else R, abbr).items():
                got.setdefault(k, []).append((sc, q["page"], n, desc))
        for x in m[key]:
            cands = sorted(got.get(x["at"], []), key=lambda c: -c[0])
            if not cands:
                continue
            if x.get("row") is None:
                sc, pg, n, desc = cands[0]
                x.update(row=enc(pg, n), desc=desc, score=sc, page=pg)
                used_parts.add(pg)
                cands = cands[1:]
            if side == "in":
                also = [enc(pg, n) for sc, pg, n, _ in cands if sc >= ALSO_MIN and enc(pg, n) != x["row"]]
                if also:
                    x["also"] = also
                    used_parts.update(r // ROW_PAGE for r in also)
    if used_parts:
        m["parts"] = sorted(used_parts | {q["page"] for q in fam})


_BODY = {}


def body(by_page, m):
    """매크로의 내부 동작 본문 — 한 장이면 그 Typical 시트, 여러 장이면 합친 한 장 (다른 장의 블록 · 선 이름 앞에 `P<쪽>.`,
    행 번호는 쪽 × ROW_PAGE + 행).  장 사이 FM(같은 매크로의 다른 장 출력 행을 가리키는 입력 행)은 그 출력 선과 한 선이 되고
    그 입력 행은 본문에서 빠진다.  같은 단자를 받는 다른 장 입력 행(`also`)도 그 단자의 행과 한 선."""
    ts = by_page.get(m.get("page"))
    parts = [p for p in (m.get("parts") or []) if p in by_page and p != m.get("page")]
    if ts is None or not parts:
        return ts
    key = (id(ts), tuple(id(by_page[p]) for p in parts), json.dumps([[x.get("row"), x.get("also")] for x in m.get("inputs", [])]))
    hit = _BODY.get(key)
    if hit and hit[0] is ts:
        return hit[1]
    pages = [m["page"]] + parts
    pre = {pg: ("" if pg == m["page"] else f"P{pg}.") for pg in pages}
    enc = {pg: (0 if pg == m["page"] else pg * ROW_PAGE) for pg in pages}
    net_of = {}                                         # (쪽, 행) → 합친 본문의 선 이름 (R 행)
    for pg in pages:
        for r in by_page[pg]["rows"]:
            if r["side"] == "R" and r.get("net") is not None:
                net_of[(pg, r["n"])] = pre[pg] + str(r["net"])
    alias, drop = {}, set()
    pin_rows = {x.get("row") for x in m.get("inputs", [])} | {a for x in m.get("inputs", []) for a in (x.get("also") or [])}
    for pg in pages:
        for r in by_page[pg]["rows"]:
            ref = r.get("ref") or {}
            if r["side"] == "L" and r.get("net") is not None and ref.get("page") in pre and enc[pg] + r["n"] not in pin_rows:
                src = net_of.get((ref["page"], ref.get("src_row") or ref.get("row")))
                if src is not None:
                    alias[pre[pg] + str(r["net"])] = src
                    drop.add((pg, r["n"]))
    lrow = {}
    for pg in pages:
        for r in by_page[pg]["rows"]:
            if r["side"] == "L" and r.get("net") is not None:
                lrow[enc[pg] + r["n"]] = pre[pg] + str(r["net"])
    for x in m.get("inputs", []):
        prim = lrow.get(x.get("row"))
        for a in x.get("also") or []:
            if prim is not None and lrow.get(a) is not None and lrow[a] != prim:
                alias[lrow[a]] = prim

    def nm(n):
        seen = set()
        while n in alias and n not in seen:
            seen.add(n)
            n = alias[n]
        return n
    blocks, ports, nets, rows, table = {}, [], {}, [], []
    for pg in pages:
        s = by_page[pg]
        for k, v in s["blocks"].items():
            nb = dict(v)
            if pre[pg] and nb.get("group"):
                nb["group"] = pre[pg] + nb["group"]
            blocks[pre[pg] + k] = nb
        for p_ in s["ports"]:
            ports.append({**p_, "block": pre[pg] + p_["block"], "net": nm(pre[pg] + str(p_["net"]))})
        for n, v in (s.get("nets") or {}).items():
            nets.setdefault(nm(pre[pg] + str(n)), v if not pre[pg] else {"segs": []})
        for r in s["rows"]:
            if (pg, r["n"]) in drop:
                continue
            rr = {**r, "n": enc[pg] + r["n"]}
            if r.get("net") is not None:
                rr["net"] = nm(pre[pg] + str(r["net"]))
            if pre[pg]:
                rr["ref"] = None
            rows.append(rr)
        for r in s.get("table", []):
            if (pg, r["n"]) not in drop:
                table.append({**r, "n": enc[pg] + r["n"]})
    merged = {**ts, "blocks": blocks, "ports": ports, "nets": nets, "rows": rows, "table": table,
              "parts": pages, "dangling": [], "findings": []}
    if len(_BODY) > 64:
        _BODY.clear()
    _BODY[key] = (ts, merged)
    return merged
