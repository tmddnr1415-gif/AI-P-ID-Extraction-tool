"""시트 사이 from-to 맞대기 — 도면이 표에 적은 그대로 양쪽을 대조한다 (L5).

★ 식별 열쇠는 **FM 칸의 시트 번호 + 행 No.** 하나다 (사용자 확정) — KKS 는 맞대기에 쓰지 않는다.
  FM `G048-95` = G048 시트 95행에서 온 신호.  붉은 '불일치' 는 이 연결(FM ↔ 그 행 · 그 행의 TO)이 어긋날 때만이고,
  연결은 맞는데 두 쪽 설명이 다르면 주황 '설명 다름' 으로 따로 알린다.
받는 쪽: 왼쪽 행의 FM `G049-86` (보내는 장 · 그 장의 행).
보내는 쪽: 오른쪽 출력 행의 TO 칸.  한 출력이 여러 장으로 가면 TO 목록이 **아래 행으로 이어진다** —
  G049 85 `HP DRUM CBD MOV CLOSED` · TO `G035-31` / 86 (설명 없음) · TO `G023-8` / 87 · TO `G032-15`.
  그래서 FM 이 가리키는 행(86)에 설명이 없으면 위로 올라가 처음 설명이 있는 행(85)이 그 신호의 주인이다.

맞는다 = ① 보내는 장이 묶음에 있고 ② 그 행에 출력 신호가 있고 ③ 그 행의 TO 가 이 장-행을 가리키고
         (TO 가 NOTE · 빈칸이면 도면이 대조할 거리를 주지 않으므로 ③ 은 '확인 못 함')
         ④ 두 쪽 설명이 같다 (글자·숫자만 비교 — 띄어쓰기 · 문장부호 · 못 읽은 글자 ? 는 보지 않는다).
보내는 쪽에서도 같은 것을 거꾸로 본다 — TO 가 가리키는 행의 FM 이 이 장-행을 가리키는가.

판정은 읽은 글자 그대로이고 고치지 않는다.  못 읽은 칸(빈 설명 · 꼴이 아닌 FM)은 '확인 못 함' 이지 불일치가 아니다.
"""
from __future__ import annotations

import re

from .refs import REF_ANY, series


def _norm(t):
    return re.sub(r"[^A-Z0-9]", "", (t or "").upper())


def _refs(text):
    return [(m.group(1), int(m.group(2))) for m in REF_ANY.finditer((text or "").replace(" ", ""))]


def _owner(table_r, k):
    """출력 쪽 k 행의 신호 주인 — k 에 설명이 있으면 k, 없고 TO 만 있으면 위로 올라가 처음 설명이 있는 행."""
    r = table_r.get(k)
    if r is None:
        return None
    if r.get("desc"):
        return k
    if not r.get("to"):
        return None
    j = k - 1
    while j in table_r:
        rj = table_r[j]
        if rj.get("desc"):
            return j
        if not rj.get("to"):
            return None
        j -= 1
    return None


def _run(table_r, owner):
    """주인 행과 그 아래로 이어지는 TO 줄들 (설명 없고 TO 만 있는 행)."""
    out = [owner]
    j = owner + 1
    while j in table_r and not table_r[j].get("desc") and table_r[j].get("to"):
        out.append(j)
        j += 1
    return out


def check(sheets):
    """시트 목록을 제자리에서 고친다 — 행마다 `ref`(src_row) · `refs_in` · `ft`, 장마다 FT 찾은 것.  여러 번 불러도 같다."""
    by_no = {s["sheet_no"]: s for s in sheets if s.get("sheet_no")}
    prefixes = {series(s["sheet_no"]) for s in sheets if s.get("sheet_no")}
    tab = {}
    for s in sheets:
        tab[s["page"]] = {"L": {r["n"]: r for r in s.get("table", []) if r["side"] == "L"},
                          "R": {r["n"]: r for r in s.get("table", []) if r["side"] == "R"}}
        for r in s["rows"]:
            r.pop("refs_in", None)
            r.pop("ft", None)
        s["findings"] = [f for f in s.get("findings", []) if not f["code"].startswith("FT_")]

    def row_obj(s, side, n):
        for r in s["rows"]:
            if r["side"] == side and r["n"] == n:
                return r
        return None

    def add(s, n, side, ok, whys, peer, warn=(), back=None):
        r = row_obj(s, side, n)
        if r is not None:
            r["ft"] = {"ok": ok, "why": whys, "peer": peer, "warn": list(warn), "back": back}
        if warn and ok is not False:
            f = {"code": "FT_DESC_DIFF", "row": n, "side": side,
                 "text": f"{s['sheet_no']}-{n} ← {peer or '?'} 연결은 맞고 설명만 다릅니다 — " + " · ".join(warn)}
            if r is not None and r.get("at"):
                f["at"] = r["at"]
            s["findings"].append(f)
        if ok is False:
            f = {"code": "FT_MISMATCH", "row": n, "side": side,
                 "text": f"{s['sheet_no']}-{n} ↔ {peer or '?'} 일치하지 않습니다 — " + " · ".join(whys)}
            if r is not None and r.get("at"):
                f["at"] = r["at"]
            s["findings"].append(f)

    # 받는 쪽 (왼쪽 FM)
    for s in sheets:
        me = s.get("sheet_no")
        for r in s["rows"]:
            if r["side"] != "L":
                continue
            refs = _refs(r.get("fm"))
            if len(refs) != 1 or refs[0][0] == "" or not REF_ANY.fullmatch((r.get("fm") or "").replace(" ", "")):
                r.pop("ref", None)
                continue
            src, k = refs[0]
            other = series(src) not in prefixes
            t = by_no.get(src)
            r["ref"] = {"sheet": src, "row": k, "page": t["page"] if t else None, "other_bundle": other}
            if other:
                continue
            if t is None:
                add(s, r["n"], "L", False, [f"묶음에 {src} 장이 없습니다"], f"{src}-{k}")
                continue
            tr = tab[t["page"]]["R"]
            own = _owner(tr, k)
            whys = []
            if own is None:
                add(s, r["n"], "L", False, [f"{src} {k}행에 출력 신호가 없습니다"], f"{src}-{k}")
                continue
            r["ref"]["src_row"] = own
            to_refs = [x for x in _refs(tr[k].get("to")) if series(x[0]) in prefixes]
            recip = None
            if to_refs:
                recip = (me, r["n"]) in to_refs
                if not recip:
                    whys.append(f"{src}-{k} 의 TO 는 {', '.join(f'{a}-{b}' for a, b in to_refs)} 를 가리킵니다")
            a, b = _norm(r.get("desc")), _norm(tr[own].get("desc"))
            if a and b and a != b:
                warn = [f"설명이 다릅니다: '{r.get('desc')}' ↔ '{tr[own].get('desc')}'"]
            else:
                warn = []
            peer = f"{src}-{own}" + (f" (TO {k}행)" if own != k else "")
            # 정합성은 FM 의 시트 + 행이 정한다 — 그 행에 신호가 있고 상대 TO 가 다른 곳을 가리키지 않으면 맞다.
            # 설명이 다른 것은 연결 불일치가 아니라 따로 알린다 (주황).  상대 TO 가 NOTE 면 거꾸로는 확인 못 함(back None).
            ok = False if whys else True
            add(s, r["n"], "L", ok, whys, peer, warn, recip)
            o = row_obj(t, "R", own)
            if o is not None:
                o.setdefault("refs_in", []).append({"sheet": me, "page": s["page"], "row": r["n"]})

    # 보내는 쪽 (오른쪽 TO) — 거꾸로
    for s in sheets:
        me = s.get("sheet_no")
        tr = tab[s["page"]]["R"]
        for own, row in tr.items():
            if not row.get("desc"):
                continue
            run = _run(tr, own)
            targets = [x for j in run for x in _refs(tr[j].get("to")) if series(x[0]) in prefixes]
            if not targets:
                continue
            whys = []
            for sh, n in targets:
                t = by_no.get(sh)
                if t is None:
                    whys.append(f"TO {sh}-{n} — 묶음에 {sh} 장이 없습니다")
                    continue
                lr = tab[t["page"]]["L"].get(n)
                fm = (lr or {}).get("fm") or ""
                back = _refs(fm)
                if not lr or not fm:
                    whys.append(f"TO {sh}-{n} — 그 행의 FM 칸이 비어 있습니다")
                elif not REF_ANY.fullmatch(fm.replace(" ", "")):
                    continue                      # 꼴이 아닌 FM (못 읽은 글자) — 확인 못 함
                elif not (back[0][0] == me and back[0][1] in run):
                    whys.append(f"TO {sh}-{n} — 그 행의 FM 은 {fm} 를 가리킵니다")
            mine = row_obj(s, "R", own)
            prev = (mine or {}).get("ft")
            ok = False if whys else True
            if prev and prev.get("ok") is False:
                continue
            add(s, own, "R", ok, whys, ", ".join(f"{a}-{b}" for a, b in targets))
    return sheets
