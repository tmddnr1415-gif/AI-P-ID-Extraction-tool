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

import re
from functools import lru_cache

NAME_MIN = 0.72          # 단자 이름 ↔ 약어 닮음 하한 (한 글자 다름까지 — OVRD1 ↔ OVRID1)
PAIR_MIN = 0.42          # 단자 ↔ 행 점수 하한


def _norm(t):
    return re.sub(r"[^A-Z0-9]", "", (t or "").upper())


def _skel(t):
    """O/0 · I/1 을 같은 글자로 — 선으로 그린 글자는 둘을 자주 바꿔 읽는다 (CMD0 ↔ CMDO)."""
    return _norm(t).replace("0", "O").replace("1", "I")


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
        lines = []
        for b in page.get_text("dict").get("blocks", []):
            for ln in b.get("lines", []):
                t = "".join(sp["text"] for sp in ln["spans"]).strip()
                if t:
                    lines.append((ln["bbox"], t))
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
    """pins = [(key, pin)] · rows = [(n, desc)] → {key: (n, desc, score)} — 점수 순으로 하나씩."""
    abbr = tuple(abbr)
    cand = []
    for key, pin in pins:
        if not pin:
            continue
        for n, desc in rows:
            s = _pin_row_score(pin, desc, abbr)
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


def _caption(page, bbox):
    """매크로 상자 안에 **진짜 글자**로 인쇄된 이름 (`MOV BLOCK (OPEN CLOSE) <TYPE-Ⅲ-1>`)."""
    ws = [w for w in page.get_text("words")
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


def link(doc, sheets):
    """시트 목록을 제자리에서 고친다 — 매크로 블록마다 `macro` = 그 Typical 시트 · 단자 ↔ 행."""
    abbr = tuple(dict.fromkeys(legend_abbr(doc)))       # 같은 줄은 한 번 — 점수 캐시의 열쇠가 된다
    tables = {}
    for s in sheets:
        L = [(t["n"], t.get("desc", "")) for t in s.get("table", []) if t["side"] == "L" and t.get("desc")]
        R = [(t["n"], t.get("desc", "")) for t in s.get("table", []) if t["side"] == "R" and t.get("desc")]
        if L and R:
            tables[s["page"]] = (L, R)
    for s in sheets:
        for bid, b in s["blocks"].items():
            if b.get("func") != "MACRO":
                continue
            ports = [p for p in s["ports"] if p["block"] == bid]
            cap = _caption(doc[s["page"] - 1], b["bbox"])
            b["caption"] = cap
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
                ranked.append((score, t, gi, go))
            ranked.sort(key=lambda r: -r[0])
            tc = _type_code(cap) or _type_code(b.get("read", ""))
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
            b["macro"] = {"sheet": t["sheet_no"], "page": t["page"], "title": t.get("title", ""), "score": round(score, 3),
                          "inputs": items(pin_in, gi), "outputs": items(pin_out, go),
                          "cands": [{"sheet": r[1]["sheet_no"], "page": r[1]["page"], "score": round(r[0], 3)} for r in ranked[:3]]}
