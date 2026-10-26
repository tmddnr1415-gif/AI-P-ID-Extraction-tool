"""가르치기 — 최소한의 질문으로 전 장을 읽게 한다 (L25).

사용자 지시: *"최대한 코드로 식별 · 마크업은 최후의 보루 · 분석 중간에 사용자가 가이드라인에 따라 최소한의 정보를 넣었을 때
식별률이 올라간다면 그 길을 만들어라 · 단 모든 페이지에 대해서 하면 안 된다 — 최소한의 페이지로 최소한에 대해 라벨링하여
전 페이지가 제대로 식별되게."*

못 읽은 것은 대개 **같은 것의 되풀이**다 (1A5J 실측 — 판정 못 한 블록 73 = 같은 모양 무리 8개 · 연결 끊김 9 = 없는
시트 이름 6개).  그래서 하나하나 고치게 하지 않고 **무리마다 질문 하나**를 낸다:

  * GATE   — 같은 모양 · 같은 글자 · 같은 칸 수 · 같은 크기(행 간격 단위) · 같은 그림(16×16)의 판정 못 한 블록 무리.
             한 번 고르면 묶음 전체의 같은 블록에, 그리고 학습 사전에 남아 **다른 프로젝트**에도 (`learn_rule`).
  * SHEET  — 시트 이름을 못 읽은 장들.  한 장에서 시트 이름 자리를 두르면 **모든 장의 같은 자리**를 읽는다.
  * LINK   — 묶음에 없는 시트 이름(FM 이 가리키는 곳).  이름마다 한 번 — '다른 문서' 또는 '이 묶음의 시트 X'.
  * FM/TO  — FM(또는 TO) 칸을 못 읽은 행이 많은 묶음.  한 장에서 그 열을 두르면 모든 장의 같은 열을 읽는다.

질문 순서는 해결하는 건수가 많은 것부터이고, 보기를 보여 줄 장은 **질문들을 가장 적은 장에 몰아** 고른다 (집합 덮기).
사람이 답한 것은 `overrides.json` 의 `teach` 에 규칙으로 남는다 — 블록 하나가 아니라 **모양의 규칙**이라 다시 분석해도,
분석이 끝나기 전에 답했어도(분석 중 미리 본 장 · L25) 끝난 결과에 그대로 얹힌다.  사람이 그 블록 하나를 직접 정했으면
그것이 이긴다.  분석 결과 파일은 바꾸지 않는다.
"""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict

from . import refs as RF

FIG = 16
FIG_SAME = 0.85          # 같은 그림 — 범례 그림 맞대기(legend.match_figure 0.85 · blocks._stretch)와 같은 값
MIN_COL_ROWS = 5         # FM/TO 열 질문을 낼 만큼 못 읽은 칸이 많은가 (그보다 적으면 마크업이 빠르다)


# ------------------------------------------------------------------ 그림 · 서명

def fig_hex(pts):
    """16×16 점 집합 → 64 글자 16진 (결과 파일에 작게 싣는다)."""
    if not pts:
        return ""
    v = 0
    for x, y in pts:
        v |= 1 << (int(y) * FIG + int(x))
    return f"{v:064x}"


def fig_points(h):
    if not h:
        return None
    v = int(h, 16)
    return [(i % FIG, i // FIG) for i in range(FIG * FIG) if v >> i & 1]


def fig_score(a, b):
    from .legend import figure_score
    return figure_score(a, b)


def _ports(s):
    io = defaultdict(lambda: [0, 0])
    for p in s.get("ports", []):
        io[p["block"]][0 if p["dir"] == "in" else 1] += 1
    return io


def block_sig(s, b, io):
    """블록의 서명 — 모양 · 글자 · 칸 수 · 크기(행 간격 단위) · 들고 나는 선의 유무.  그림은 따로 (`fig`)."""
    x0, y0, x1, y1 = b["bbox"]
    w, h = max(x1 - x0, 0.01), max(y1 - y0, 0.01)
    P = s.get("pitch") or 11.5
    text = re.sub(r"\?+", "?", re.sub(r"\s+", " ", (b.get("read") or b.get("label") or "").upper())).strip()
    return {"kind": b.get("kind") or "", "shape": b.get("shape") or "", "text": text,
            "cells": len(b.get("cells") or []), "size": round(max(w, h) / P * 2) / 2,
            "aspect": round(w / h * 2) / 2, "ins": int(io[0] > 0), "outs": int(io[1] > 0)}


def sig_key(sig):
    """서명 → 글자 열쇠.  수는 같은 꼴로 적는다 — 화면(JSON)을 거치면 1.0 이 1 이 되어 열쇠가 갈렸다 (L25 자기검증)."""
    def f(k):
        v = sig.get(k, "")
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return f"{float(v):g}"
        return str(v if v is not None else "")
    return "|".join(f(k) for k in ("kind", "shape", "text", "cells", "size", "aspect", "ins", "outs"))


def _same(sig_a, fig_a, sig_b, fig_b):
    if sig_key(sig_a) != sig_key(sig_b):
        return False
    pa, pb = fig_points(fig_a), fig_points(fig_b)
    if not pa and not pb:
        return True
    if not pa or not pb:
        return False
    return fig_score(pa, pb) >= FIG_SAME


def _unknown_blocks(res):
    for s in res.get("sheets", []):
        if s.get("library"):
            continue
        io = _ports(s)
        for bid, b in s.get("blocks", {}).items():
            if b.get("func") == "UNKNOWN":
                yield s, bid, b, block_sig(s, b, io[bid])


def gate_groups(res):
    """판정 못 한 블록 → 무리 [{sig, fig, members:[(쪽, 블록)]}].  그림이 없거나 못 읽은 글자(?)뿐인데 그림이 없는 블록은
    무리를 짓지 않는다 (모양만으로 같다고 할 근거가 없다 — 하나씩 묻는다)."""
    groups = []
    for s, bid, b, sig in _unknown_blocks(res):
        fg = b.get("fig") or ""
        # 예전 결과(그림을 싣지 않은 분석)에서 못 읽은 글자 상자는 그림으로 가를 수 없다 — 하나씩 묻는다
        loose = "fig" not in b and ("?" in sig["text"] or not sig["text"]) and sig["kind"] == "RECT"
        hit = None
        if not loose:
            for g in groups:
                if _same(sig, fg, g["sig"], g["fig"]):
                    hit = g
                    break
        if hit is None:
            hit = {"sig": sig, "fig": fg, "members": []}
            groups.append(hit)
        hit["members"].append((s["page"], bid))
    return groups


def rule_matches(rule, sig, fig):
    return _same(sig, fig or "", rule.get("sig") or {}, rule.get("fig") or "")


# ------------------------------------------------------------------ 질문

def _qid(*parts):
    return "Q" + hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:10]


def _cover(questions):
    """보기 장 고르기 — 질문들을 가장 적은 장에 몰아 넣는다 (욕심쟁이 집합 덮기).  질문마다 `example` 이 그 장의 것이 된다."""
    left = {q["id"]: q for q in questions if q.get("pages_of")}
    chosen = []
    while left:
        cnt = defaultdict(int)
        for q in left.values():
            for p in q["pages_of"]:
                cnt[p] += 1
        page = max(cnt, key=lambda p: (cnt[p], -p))
        chosen.append(page)
        for qid in [k for k, q in left.items() if page in q["pages_of"]]:
            q = left.pop(qid)
            q["example"] = next((e for e in q["examples"] if e["page"] == page), q["examples"][0])
    for q in questions:
        q.pop("pages_of", None)
        q.pop("examples", None)
    return chosen


def questions(res, teach=None, measure=None):
    """지금 결과(사람 값 · 가르친 규칙을 얹은 것)에서 남은 질문.  → {questions, pages, gain}."""
    from . import idrate
    m = measure or idrate.measure(res)
    sheets = [s for s in res.get("sheets", []) if not s.get("library")]
    by_page = {s["page"]: s for s in sheets}
    tot = sum(v["all"] for v in m["counts"].values()) or 1
    got = sum(v["ok"] for v in m["counts"].values())
    qs = []
    # GATE
    for g in gate_groups(res):
        ex = []
        for pg, bid in g["members"]:
            b = by_page[pg]["blocks"][bid]
            ex.append({"page": pg, "block": bid, "at": b["bbox"], "sheet_no": by_page[pg].get("sheet_no") or ""})
        pages = sorted({pg for pg, _ in g["members"]})
        qs.append({"id": _qid("GATE", sig_key(g["sig"]), g["fig"]), "kind": "GATE", "count": len(g["members"]),
                   "sheets": len(pages), "sig": g["sig"], "fig": g["fig"], "text": g["sig"]["text"],
                   "members": [[pg, bid] for pg, bid in g["members"]], "pages_of": set(pages), "examples": ex})
    # SHEET
    miss = [s for s in sheets if not s.get("sheet_no")]
    if miss:
        named = [s for s in sheets if s.get("sheet_no")]
        qs.append({"id": _qid("SHEET"), "kind": "SHEET", "count": len(miss), "sheets": len(miss),
                   "pages_of": {s["page"] for s in miss},
                   "examples": [{"page": s["page"], "at": None, "sheet_no": ""} for s in miss],
                   "named_example": (named[0]["sheet_no"] if named else "")})
    # LINK — 묶음에 없는 시트 이름마다
    tgt = defaultdict(list)
    for s in sheets:
        for r in s.get("rows", []):
            ref = r.get("ref")
            if r["side"] == "L" and ref and not ref.get("other_bundle") and ref.get("page") is None:
                t = next((x for x in s.get("table", []) if x["side"] == "L" and x["n"] == r["n"]), {})
                tgt[ref["sheet"]].append({"page": s["page"], "row": r["n"], "at": t.get("fm_box"),
                                          "sheet_no": s.get("sheet_no") or "", "fm": r.get("fm") or ""})
    for name, ex in tgt.items():
        qs.append({"id": _qid("LINK", name), "kind": "LINK", "target": name, "count": len(ex),
                   "sheets": len({e["page"] for e in ex}), "pages_of": {e["page"] for e in ex}, "examples": ex,
                   "candidates": sorted({s["sheet_no"] for s in sheets if s.get("sheet_no")})[:400]})
    # FM / TO 열 — 신호가 있는데 칸을 못 읽은(비었거나 '?') 행이 많을 때
    for side, field, kind in (("L", "fm", "FROM"), ("R", "to", "TO")):
        ex = []
        boxed = {s["page"] for s in sheets for t in s.get("table", []) if t["side"] == side and t.get(field + "_box")}
        logic_pages = {s["page"] for s in sheets if any(b.get("func") != "CONNECTOR" for b in s.get("blocks", {}).values())}
        # 묻는 장: 그 열을 한 칸이라도 찾은 장(나머지 칸을 놓친 것) · 묶음 전체가 그 열을 못 찾았으면 블록이 있는 장.
        # 그 열을 한 칸도 안 그린 장(도면 목록 · Typical 시트 — NO · SERVICE · ABV 만 있는 표)은 묻지 않는다.
        ask = boxed or logic_pages
        for s in sheets:
            if s["page"] not in ask or s["page"] not in logic_pages:
                continue
            for t in s.get("table", []):
                if t["side"] != side or not (t.get("desc") or t.get("kks")):
                    continue
                v = (t.get(field) or "").strip()
                box = t.get(field + "_box")
                if v and (RF.find(v) or idrate._readable(v)):
                    continue
                if not v and box:
                    continue             # 칸은 찾았는데 비어 있다 — 도면이 안 적은 것이다 (묻지 않는다)
                ex.append({"page": s["page"], "row": t["n"], "at": t.get(field + "_box"), "sheet_no": s.get("sheet_no") or ""})
        sig_rows = sum(1 for s in sheets for t in s.get("table", []) if t["side"] == side and (t.get("desc") or t.get("kks")))
        per = defaultdict(int)
        for e in ex:
            per[e["page"]] += 1
        # 한 장뿐이면(도면 목록 장을 표로 읽은 것 · 1A1Y p2) 열을 묻지 않는다 — 여러 장에 걸친 실패일 때만
        if len(ex) >= MIN_COL_ROWS and len(ex) >= 0.1 * max(sig_rows, 1) and len(per) >= max(2, 0.1 * len(sheets)):
            best = max(per, key=per.get)
            qs.append({"id": _qid("COL", side), "kind": kind, "side": side, "count": len(ex), "sheets": len(per),
                       "pages_of": {best}, "examples": [e for e in ex if e["page"] == best]})
    done = set((teach or {}).get("skipped") or [])
    qs = [q for q in qs if q["id"] not in done]
    qs.sort(key=lambda q: (-q["count"], q["kind"]))
    pages = _cover(qs)
    order = {p: i for i, p in enumerate(pages)}
    qs.sort(key=lambda q: (order.get((q.get("example") or {}).get("page"), 99), -q["count"]))     # 장마다 몰아서 묻는다
    gain = round(min(1.0, (got + sum(q["count"] for q in qs if q["kind"] in ("GATE", "SHEET", "LINK"))) / tot), 4)
    return {"questions": qs, "pages": pages, "now": m.get("overall"), "gain": gain, "target": m.get("target")}


# ------------------------------------------------------------------ 규칙을 결과에 얹기

def gate_entries(res, rules, own_blocks):
    """가르친 게이트 규칙 → {쪽: {블록: 블록 종류 항목}}.  사람이 그 블록 하나를 직접 정한 것(own_blocks)은 건드리지 않는다."""
    out = defaultdict(dict)
    if not rules:
        return out
    for s, bid, b, sig in _unknown_blocks(res):
        if bid in (own_blocks.get(str(s["page"])) or {}):
            continue
        fg = b.get("fig") or ""
        for r in rules:
            if rule_matches(r, sig, fg):
                ent = {"choice": r["choice"], "param": r.get("param") or {}, "author": r.get("author", ""),
                       "at": r.get("at", ""), "taught": r.get("id", ""), "from": r.get("from", "job")}
                if r["choice"] == "VOTE" and r.get("param"):
                    ent["label"] = f"{r['param']['a']}/{r['param']['b']}"
                out[str(s["page"])][bid] = ent
                break
    return out


def apply_sheet_and_cols(res, teach):
    """시트 이름 자리 · FM/TO 열 — 사람이 한 장에서 두른 자리를 모든 장에서 읽어 둔 값(values)을 빈 칸에만 얹는다.
    → 바꿨는가."""
    changed = False
    by_page = {s["page"]: s for s in res.get("sheets", [])}
    les = (teach or {}).get("sheet")
    if isinstance(les, dict):
        for pg, v in (les.get("values") or {}).items():
            s = by_page.get(int(pg)) if str(pg).isdigit() else None
            if s is None or s.get("sheet_no") or not v:
                continue
            s["sheet_no"] = v
            s["user_sheet"] = {"was": "", "author": les.get("author", ""), "taught": True}
            changed = True
    for side in ("L", "R"):
        les = ((teach or {}).get("cols") or {}).get(side)
        if not isinstance(les, dict):
            continue
        field = "fm" if side == "L" else "to"
        for pg, rows in (les.get("values") or {}).items():
            s = by_page.get(int(pg)) if str(pg).isdigit() else None
            if s is None or not isinstance(rows, dict):
                continue
            for n, v in rows.items():
                if not str(n).isdigit() or not v:
                    continue
                for coll in (s.get("table", []), s.get("rows", [])):
                    for r in coll:
                        if r["side"] != side or r["n"] != int(n):
                            continue
                        cur = (r.get(field) or "").strip()
                        if cur and "?" not in cur and (RF.find(cur) or len(re.sub(r"[^A-Z0-9]", "", cur.upper())) >= 2):
                            continue                 # 도면이 읽힌 칸은 덮지 않는다
                        r.setdefault("user", {})[field] = {"was": cur, "author": les.get("author", ""), "taught": True}
                        r[field] = v
                        changed = True
    return changed


def links_of(teach):
    """→ {"external": [시트 이름], "aliases": {시트 이름: 이 묶음의 시트}} (fromto.check 가 받는다)."""
    ext, ali = [], {}
    for name, e in ((teach or {}).get("links") or {}).items():
        if not isinstance(e, dict):
            continue
        if e.get("mode") == "OTHER":
            ext.append(name)
        elif e.get("mode") == "ALIAS" and e.get("sheet"):
            ali[name] = e["sheet"]
    return {"external": ext, "aliases": ali}


# ------------------------------------------------------------------ 한 장에서 두른 자리 → 모든 장

def read_region(pdf_path, res, page, rect, side=None):
    """한 장에서 두른 사각형을 모든 Logic 장의 같은 자리(종이 크기 비례)에서 읽는다.
    side 없음 → {쪽: 글}(시트 이름) · side L/R → {쪽: {행: 글}} (그 사각형의 가로 띠 × 표 행 높이)."""
    import pymupdf
    from . import geom
    from .blocks import vocab
    caps = sorted({str(c).upper() for c in (vocab().get("sheet_captions") or ["SHEET"])}, key=len, reverse=True)
    doc = pymupdf.open(pdf_path)
    base = doc[page - 1].rect
    bw, bh = base.width, base.height
    out = {}
    for s in res.get("sheets", []):
        if s.get("library") or s["page"] > len(doc):
            continue
        pg = doc[s["page"] - 1]
        sx, sy = pg.rect.width / bw, pg.rect.height / bh
        x0, y0, x1, y1 = rect[0] * sx, rect[1] * sy, rect[2] * sx, rect[3] * sy
        ws = [w for w in geom.words(pg) if x0 <= (w[0] + w[2]) / 2 <= x1 and y0 <= (w[1] + w[3]) / 2 <= y1]
        if side is None:
            ws.sort(key=lambda w: (round((w[1] + w[3]) / 2), w[0]))
            v = _strip_caption(re.sub(r"\s+", " ", " ".join(w[4] for w in ws)).strip().upper(), caps)
            if v:
                out[s["page"]] = v[:60]
            continue
        rows = {}
        for t in s.get("table", []):
            if t["side"] != side or t.get("y0") is None:
                continue
            got = [w for w in ws if t["y0"] <= (w[1] + w[3]) / 2 <= t["y1"]]
            got.sort(key=lambda w: w[0])
            v = re.sub(r"\s+", " ", " ".join(w[4] for w in got)).strip().upper()
            if v:
                rows[str(t["n"])] = v[:120]
        if rows:
            out[s["page"]] = rows
    return out


def _strip_caption(v, caps):
    """사람이 두른 자리에 캡션(`SHEET` · `SHEET NO.` — config sheet_captions)까지 들어왔으면 떼고 값만 (`SHEET AB_G-101` → `AB_G-101`)."""
    for c in caps:
        if v == c:
            return ""
        if v.startswith(c + " ") or v.startswith(c + ":"):
            return v[len(c):].lstrip(" :")
    return v
