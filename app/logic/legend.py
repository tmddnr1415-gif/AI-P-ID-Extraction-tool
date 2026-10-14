"""범례 표(SIGNAL PROCESSING SYMBOLS 같은 FUNCTION | SYMBOL | DEFINITION 표)에서 블록의 뜻을 읽는다 (L21).

19VA 양식은 게이트 이름을 블록 안에 쓰지 않고 **모양**으로 그린다 — AND = 입력 막대 + 작은 네모,
OR = 입력 막대 + 작은 원, NOT = ⊠.  어느 모양이 어느 기능인지는 그 묶음의 범례 표가 말한다.  그래서
범례 표의 행마다 SYMBOL 칸의 그림을 **시트와 같은 코드(graph.build)** 로 읽어 모양 열쇠를 만들고,
그 행의 FUNCTION 칸 이름과 짝짓는다.  코드는 기능 이름 → 동작(and/or/…)만 안다 (config logic_symbols.yaml
`legend_functions` — ISA-S5.2 어휘).  범례가 없으면 빈 사전이고 블록 판정은 예전 길(블록 안 글자)로 간다.

열쇠 = "모양|블록 안 글자"  (예 `BAR_BOX|` · `ROUND_BOX|ON` · `|ABS` · `|1`).  여러 칸 상자는 첫 칸 글자로도 적는다
(`CELL0|P B` — 누름단추 상자는 둘째 칸에 단추 이름이 들어간다).
"""
from __future__ import annotations

import re
from collections import defaultdict

from . import geom, graph

HEAD = ("FUNCTION", "SYMBOL", "DEFINITION")


def _norm_name(text):
    t = re.sub(r"\([^)]*\)?", " ", (text or "").upper())
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9/ ]", " ", t)).strip()


def block_text(b, words):
    """블록 안(가운데가 블록 안)에 인쇄된 진짜 글자 — 칸마다 (위→아래 · 왼→오)."""
    cells = b.cells if getattr(b, "cells", None) else [b.bbox]
    out = []
    for c in cells:
        ws = [w for w in words if c[0] <= (w[0] + w[2]) / 2 <= c[2] and c[1] <= (w[1] + w[3]) / 2 <= c[3]]
        ws.sort(key=lambda w: (round((w[1] + w[3]) / 2), w[0]))
        out.append(" ".join(w[4] for w in ws).strip().upper())
    return out


FIG = 16                  # 그림 비교 격자 (16×16)


def figure(b, polys):
    """글자 없는 상자 안의 그림(⎍ · △ · ∫ …) — 획을 그림 크기로 맞춘 16×16 점 집합.  그림이 없으면 None."""
    x0, y0, x1, y1 = b.bbox
    w, h = x1 - x0, y1 - y0
    ids = set(getattr(b, "glyphs", []))
    segs = []
    for p in polys:
        if p.pid not in ids:
            continue
        for sg in p.segs:
            # 상자 변 위의 선은 그림이 아니다
            if sg.horiz and (abs(sg.y0 - y0) < 0.05 * h or abs(sg.y0 - y1) < 0.05 * h):
                continue
            if sg.vert and (abs(sg.x0 - x0) < 0.05 * w or abs(sg.x0 - x1) < 0.05 * w):
                continue
            segs.append(sg)
    if not segs:
        return None
    xs = [v for sg in segs for v in (sg.x0, sg.x1)]
    ys = [v for sg in segs for v in (sg.y0, sg.y1)]
    fx0, fy0, fx1, fy1 = min(xs), min(ys), max(xs), max(ys)
    side = max(fx1 - fx0, fy1 - fy0)
    if side < 0.15 * min(w, h):
        return None
    ox, oy = fx0 - (side - (fx1 - fx0)) / 2, fy0 - (side - (fy1 - fy0)) / 2
    pts = set()
    for sg in segs:
        n = max(2, int(sg.length / side * FIG * 2) + 2)
        for k in range(n + 1):
            t = k / n
            x = sg.x0 + (sg.x1 - sg.x0) * t
            y = sg.y0 + (sg.y1 - sg.y0) * t
            pts.add((min(FIG - 1, int((x - ox) / side * FIG)), min(FIG - 1, int((y - oy) / side * FIG))))
    return sorted(pts)


def figure_score(a, b):
    """두 그림의 닮음 — 한 칸 번진 겹침 (0~1)."""
    A, Bs = set(map(tuple, a)), set(map(tuple, b))
    grow = lambda S: {(x + dx, y + dy) for x, y in S for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    ga, gb = grow(A), grow(Bs)
    hit = sum(1 for q in A if q in gb) + sum(1 for q in Bs if q in ga)
    return hit / (len(A) + len(Bs))


def keys_of(b, words):
    """블록의 모양 열쇠들 (가장 구체적인 것부터)."""
    shape = getattr(b, "shape", "") or ""
    cells = block_text(b, words)
    whole = " ".join(t for t in cells if t)
    ks = [f"{shape}|{whole}"]
    if len(cells) >= 2 and cells[0]:
        ks.append(f"CELL0|{cells[0]}")
    return ks


def read(doc, kinds, pitch, vocab):
    """묶음의 범례 표 → {"map": {열쇠: {"name", "logic", "page"}}, "rows": [...], "pages": [...]}."""
    names = {_norm_name(k): v for k, v in (vocab.get("legend_functions") or {}).items()}
    phrases = vocab.get("legend_definitions") or {}
    out = {"map": {}, "names": {}, "rows": [], "pages": [], "figures": []}
    for i in range(len(doc)):
        if kinds.get(i + 1) == "LOGIC":
            continue
        page = doc[i]
        words = page.get_text("words")
        heads = _headers(words)
        if not heads:
            continue
        pr = geom.read(page, i + 1)
        for hd in heads:
            got = _table(pr, words, hd, pitch, names, phrases, i + 1)
            if got:
                out["pages"].append(i + 1)
                out["rows"].extend(got)
    for r in out["rows"]:
        for k in r["keys"]:
            if k.split("|", 1)[1] == "" and not k.split("|", 1)[0]:
                continue                       # 모양도 글자도 없는 열쇠 — 아무 상자에나 맞는다 (그림으로 가른다)
            # 같은 열쇠를 두 행이 다른 뜻으로 쓰면(동작이 없는 아날로그 행 포함) 그 열쇠는 쓰지 않는다 (지어내지 않는다)
            cur = out["map"].get(k)
            if cur and cur["logic"] != r["logic"]:
                cur["conflict"] = True
                continue
            out["map"].setdefault(k, {"name": r["name"], "logic": r["logic"], "page": r["page"], "label": r["label"]})
        for fg in r.pop("_figs", []):
            out["figures"].append({"fig": fg, "name": r["name"], "logic": r["logic"], "page": r["page"], "label": r["label"]})
    out["names"] = {k: v["name"] for k, v in out["map"].items() if not v.get("conflict") and not v["logic"]}
    out["map"] = {k: v for k, v in out["map"].items() if not v.get("conflict") and v["logic"]}
    out["pages"] = sorted(set(out["pages"]))
    return out


def match_figure(fig, figures, floor=0.6, margin=0.08):
    """그림 → 가장 닮은 범례 그림.  2위(다른 이름)와 차가 없으면 None."""
    if not fig or not figures:
        return None
    sc = sorted(((figure_score(fig, f["fig"]), i) for i, f in enumerate(figures)), reverse=True)
    best, i = sc[0]
    if best < floor:
        return None
    second = next((s_ for s_, j in sc[1:] if figures[j]["name"] != figures[i]["name"]), 0.0)
    if best - second < margin:
        return None
    return {**figures[i], "score": round(best, 3)}


def _headers(words):
    """같은 줄에 FUNCTION · SYMBOL · DEFINITION 이 다 있는 머리글 (표 하나에 하나)."""
    by = defaultdict(list)
    for w in words:
        if w[4].upper() in HEAD:
            by[w[4].upper()].append(w)
    out = []
    for s in by.get("SYMBOL", []):
        cy = (s[1] + s[3]) / 2
        h = s[3] - s[1]
        pick = {}
        for k in ("FUNCTION", "DEFINITION"):
            cand = [w for w in by.get(k, []) if abs((w[1] + w[3]) / 2 - cy) <= 0.5 * h]
            if not cand:
                break
            pick[k] = min(cand, key=lambda w: abs((w[0] + w[2]) / 2 - (s[0] + s[2]) / 2))
        else:
            out.append({"SYMBOL": s, **pick})
    return out


def _table(pr, words, hd, pitch, names, phrases, pno):
    sym, fun, dfn = hd["SYMBOL"], hd["FUNCTION"], hd["DEFINITION"]
    top = sym[3]
    # 세로 괘선 — 머리글 바로 위에서 시작해 아래로 긴 것
    vs = sorted({round(s.x0, 1) for p in pr.polys for s in p.segs
                 if s.vert and min(s.y0, s.y1) <= top and max(s.y0, s.y1) > top + 3 * pitch})
    if len(vs) < 3:
        return []

    def col(w):
        cx = (w[0] + w[2]) / 2
        for a, b in zip(vs, vs[1:]):
            if a < cx < b:
                return a, b
        return None
    cs, cf, cd = col(sym), col(fun), col(dfn)
    if not (cs and cf and cd):
        return []
    bottom = max(max(s.y0, s.y1) for p in pr.polys for s in p.segs if s.vert and round(s.x0, 1) in (cs[0], cs[1]))

    def bands(c):
        ys = sorted({round(s.y0, 1) for p in pr.polys for s in p.segs
                     if s.horiz and min(s.x0, s.x1) <= c[0] + 0.1 * (c[1] - c[0])
                     and max(s.x0, s.x1) >= c[1] - 0.1 * (c[1] - c[0]) and top < s.y0 <= bottom + 0.5})
        out = []
        for a, b in zip(ys, ys[1:]):
            if b - a > 0.5 * pitch:
                out.append((a, b))
        return out
    sb, fb = bands(cs), bands(cf)
    rows = []
    for a, b in sb:
        cy = (a + b) / 2
        fband = next(((x, y) for x, y in fb if x - 0.5 <= cy <= y + 0.5), (a, b))
        fwords = [w for w in words if cf[0] < (w[0] + w[2]) / 2 < cf[1] and fband[0] < (w[1] + w[3]) / 2 < fband[1]]
        fwords.sort(key=lambda w: (round((w[1] + w[3]) / 2), w[0]))
        label = " ".join(w[4] for w in fwords)
        dwords = [w for w in words if cd[0] < (w[0] + w[2]) / 2 < cd[1] and a < (w[1] + w[3]) / 2 < b]
        dwords.sort(key=lambda w: (round((w[1] + w[3]) / 2), w[0]))
        definition = " ".join(w[4] for w in dwords)
        name = _norm_name(label)
        logic = names.get(name)
        if logic is None:                          # 묶음 칸(SPECIAL) — 정의 문장의 구절로
            up = definition.upper()
            for lg, ps in phrases.items():
                if any(ph.upper() in up for ph in ps):
                    logic, name = lg, name or lg.upper()
                    break
        region = (cs[0] + 0.5, a + 0.5, cs[1] - 0.5, b - 0.5)
        lay = geom.Layout(region, pitch, [], [], [cs[0], cs[1]], note="범례 SYMBOL 칸")
        sh = graph.build(pr, lay)
        keys = []
        figs = []
        lab = ""
        if sh is not None:
            for bl in sh.blocks.values():
                if bl.kind not in ("RECT", "CIRCLE"):
                    continue
                ks = keys_of(bl, words)
                keys.extend(ks)
                lab = lab or ks[0].split("|", 1)[1]
                if ks[0] == "|":
                    fg = figure(bl, sh.glyph_polys)
                    if fg:
                        figs.append(fg)
        keys = list(dict.fromkeys(keys))
        rows.append({"page": pno, "name": name, "label": label, "logic": logic, "keys": keys, "_figs": figs,
                     "text": lab, "definition": definition[:160], "box": [round(v, 1) for v in region]})
    return rows
