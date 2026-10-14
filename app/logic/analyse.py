"""Logic PDF 한 묶음 → 결과 JSON (시트마다 신호 연결도 · 블록 뜻 · 행 글자 · 시트 간 참조 · 찾은 것).

P&ID 엔진을 부르지 않는다.  판정에 LLM 을 쓰지 않는다.
"""
from __future__ import annotations

import math
import re
import time
from collections import defaultdict

import pymupdf

from . import blocks as B
from . import fromto, geom, glyphs, graph, legend, library, macro
from . import refs as RF                              # 시트-행 (설계 S6 · L21 계통 접두 · L23 일반 꼴)


def analyse(pdf_path, progress=None):
    t0 = time.time()
    say = progress or (lambda *a, **k: None)
    doc = pymupdf.open(pdf_path)
    sheets = {}
    kinds = {}
    for i in range(len(doc)):
        say("reading", i + 1, len(doc))
        pr = geom.read(doc[i], i + 1)
        sh = graph.build(pr)
        if sh is None:
            kinds[i + 1] = "OTHER"
            continue
        sheets[i + 1] = sh
        kinds[i + 1] = "LOGIC"
    if not sheets:
        raise NotLogic("Logic 표(왼쪽 입력 · 가운데 LOGIC · 오른쪽 출력)를 그린 장을 한 장도 찾지 못했습니다.")
    say("glyphs", 0, 1)
    D = glyphs.learn(doc, sheets)
    # 범례 표(FUNCTION | SYMBOL | DEFINITION) — 모양으로 그린 게이트의 뜻 (L21 · 없으면 빈 사전)
    pitch = _modal_pitch(sheets)
    leg = legend.read(doc, kinds, pitch, B.vocab()) if pitch else {"map": {}, "names": {}, "figures": [], "rows": [], "pages": []}
    # L22 — 학습 사전: 묶음 범례가 말하지 않은 열쇠만 보태고, 범례 표가 없으면 진짜 글자가 열쇠와 맞을 때만 쓴다
    lib = library.load()
    lib_leg = library.as_legend(lib)
    if leg["map"] or leg["figures"]:
        use = library.merge(leg, lib_leg)
    elif lib_leg["map"] or lib_leg["names"]:
        use = {**lib_leg, "library_only": True}
    else:
        use = None
    for sh in sheets.values():
        sh.legend = use
    out_sheets = []
    for pno, sh in sorted(sheets.items()):
        say("blocks", pno, len(doc))
        B.classify(sh, D)
        sheet_no, sub = glyphs._title_words(doc[pno - 1])
        sheet_no = (sheet_no or "").upper()                  # 소문자로 인쇄한 양식도 같은 이름 (L23b)
        rows = _rows(sh, D)
        _printed_numbers(sh, rows)
        timers = _timer_params(sh, D)
        out_sheets.append(_export(sh, pno, sheet_no, " ".join(sub), rows, timers))
        if not sub:
            out_sheets[-1]["_title_lines"] = glyphs._title_lines(doc[pno - 1])
    # 세 장 이상이 같은 '시트 이름' 이면 그것은 시트 이름이 아니라 문서 번호다 (DWG. NO. 칸이 장마다 같은 양식 · L23b)
    seen = defaultdict(int)
    for s_ in out_sheets:
        if s_["sheet_no"]:
            seen[s_["sheet_no"]] += 1
    for s_ in out_sheets:
        if seen.get(s_["sheet_no"], 0) >= 3:
            s_["sheet_no"] = ""
    _titles_from_lines(out_sheets)
    _cross_refs(out_sheets)
    for s in out_sheets:
        s["findings"] = _findings(s)
    fromto.check(out_sheets)                 # FM ↔ TO 양쪽 대조 (L5)
    say("macros", 0, 1)
    lib_sheets = macro.link(doc, out_sheets, library=lib)   # 매크로 블록 → Typical 시트 · 단자 ↔ 행 (L12 · L22 사전)
    return {
        "pdf_pages": len(doc),
        "sheets": out_sheets,
        "kinds": kinds,
        "dictionary": D.to_json(),
        "legend": {"pages": leg["pages"], "symbols": {k: v["name"] for k, v in leg["map"].items()},
                   "figures": sorted({f["name"] for f in leg["figures"]}),
                   # L22 — 학습 사전에 남길 것 (이 묶음 범례가 말한 것만)
                   "learn": {"map": {k: {kk: v[kk] for kk in ("name", "logic", "label", "page")} for k, v in leg["map"].items()},
                             "names": dict(leg.get("names") or {}),
                             "figures": [{kk: f[kk] for kk in ("fig", "name", "logic", "label")} for f in leg["figures"]]},
                   "library": {"used": use is not None and not (leg["map"] or leg["figures"]),
                               "symbols": len(lib_leg["map"]) + len(lib_leg["names"]), "typicals": len(lib["typicals"])}},
        "library_sheets": lib_sheets or [],
        "seconds": round(time.time() - t0, 1),
        "note": _no_text_note(doc, out_sheets) +
                "글자는 묶음 안의 짝(표의 행 번호 · 도면 목록 ↔ 타이틀블록)으로 배운 사전으로 읽었습니다. "
                "블록 종류는 범례 G003 어휘에 맞대 골랐고, 맞는 낱말이 없으면 UNKNOWN 으로 남겼습니다.",
    }


def _no_text_note(doc, sheets):
    """L23b — 글자 층이 한 장에도 없고 시트 이름도 하나 못 읽었으면 먼저 그렇게 말한다 (FM/TO · 시트 사이 연결이 빈 이유)."""
    if any(s.get("sheet_no") for s in sheets):
        return ""
    if any(pg.get_text("text").strip() for pg in doc):
        return ""
    return ("⚠ 이 PDF 에는 글자 층이 없습니다 (글자를 그림이나 선으로 내보냈습니다) — 시트 이름 · FM/TO 를 읽지 못해 "
            "시트 사이 연결은 되지 않습니다.  선 · 게이트는 읽었습니다.  CAD 에서 글자를 TrueType 으로 다시 내보내면 됩니다.  ")


def _modal_pitch(sheets):
    from collections import Counter
    c = Counter(round(sh.layout.pitch, 1) for sh in sheets.values())
    return c.most_common(1)[0][0] if c else 0


class NotLogic(Exception):
    pass


# ------------------------------------------------------------------ 행 글자

def _rows(sh, D):
    """표 행마다 칸 글자 (왼쪽: FM · DESCRIPTION · KKS · 오른쪽: KKS · DESCRIPTION · TO)."""
    lay = sh.layout
    cols = sorted(lay.columns)
    LX0, _, LX1, _ = lay.logic
    left = [x for x in cols if x <= LX0 + 0.1]
    right = [x for x in cols if x >= LX1 - 0.1]
    # 표 바깥 테두리 — 장 테두리(굵은 칠 선)가 표의 바깥 변이다
    page_left = min((p.bbox[0] for p in sh.all_glyphs), default=left[0] - 60)
    out = []
    grid = defaultdict(list)
    for p in sh.all_glyphs:
        grid[int(((p.bbox[1] + p.bbox[3]) / 2) // max(lay.pitch, 1))].append(p)

    # 표의 행 번호를 진짜 글자로 인쇄한 장은 표 전체가 글자다 (19VA · L21) — 빈 칸을 선 글자로 읽지 않는다
    nums = {str(n) for n, _, _ in lay.left_rows + lay.right_rows}
    t_y0 = min((a for _, a, _ in lay.left_rows + lay.right_rows), default=0)
    t_y1 = max((b for _, _, b in lay.left_rows + lay.right_rows), default=0)
    real_table = len(nums) >= 10 and \
        len({w[4] for w in sh.words if w[4] in nums and t_y0 < (w[1] + w[3]) / 2 < t_y1}) >= 0.8 * len(nums)

    def cell_text(x0, x1, a, b):
        # 진짜 글자로 인쇄한 칸이 먼저다 (G005 처럼 표를 글자로 내보낸 장) — 선 글자 사전으로 읽을 일이 없다
        ws = sorted((w for w in sh.words if x0 < (w[0] + w[2]) / 2 < x1 and a < (w[1] + w[3]) / 2 < b),
                    key=lambda w: (round((w[1] + w[3]) / 2), w[0]))
        if ws:
            return " ".join(w[4] for w in ws).strip()
        if real_table:
            return ""
        ps = []
        for k in range(int(a // lay.pitch) - 1, int(b // lay.pitch) + 2):
            for p in grid.get(k, []):
                cx, cy = (p.bbox[0] + p.bbox[2]) / 2, (p.bbox[1] + p.bbox[3]) / 2
                if x0 < cx < x1 and a < cy < b:
                    ps.append(p)
        cs = glyphs.chars(ps)
        if not cs:
            return ""
        big = sorted(max(c.w, c.h) for c in cs)[len(cs) // 2]
        cs = [c for c in cs if max(c.w, c.h) >= 0.15 * big]
        cs.sort(key=lambda c: c.cx)
        txt = []
        prev = None
        for c in cs:
            ch, s, m = D.classify(c.raster)
            if s < B.MIN_SCORE:
                ch = "?"
            if prev is not None and c.bbox[0] - prev.bbox[2] > 0.6 * max(c.h, prev.h):
                txt.append(" ")
            txt.append(ch)
            prev = c
        return _fix_o0("".join(txt).strip())

    page_right = max((p.bbox[2] for p in sh.all_glyphs), default=right[-1] + 60) + 1
    fr = getattr(sh, "frame", None)
    # 표 바깥 변을 장 테두리가 겸하고 글자를 진짜 글자로 인쇄한 양식 (1A1Y · L23) — 선 글자가 FROM 칸 안쪽에만 있어
    # 바깥 변을 못 잡으면 FROM · TO 칸이 통째로 빠진다.  그때만 장 테두리 안쪽 변을 표 바깥 변으로 쓴다.
    V = B.vocab().get("table_headers") or {}
    t_top = min((a for _, a, _ in lay.left_rows + lay.right_rows), default=0)
    head = [w for w in sh.words if t_top - 3 * lay.pitch <= (w[1] + w[3]) / 2 < t_top]
    hw = lambda role: {x.upper() for x in V.get(role, [])}
    fm_h = [w for w in head if w[4].upper() in hw("fm") and (w[0] + w[2]) / 2 < (left[0] if left else 0)]
    to_h = [w for w in head if w[4].upper() in hw("to") and (w[0] + w[2]) / 2 > (right[-1] if right else 1e9)]
    if fm_h:
        # FROM 머리글이 읽은 열보다 바깥이다 — 그 칸의 바깥 변은 장 테두리(있으면) 또는 머리글 글자 왼쪽 끝 너머
        edge = fr[0] + 1 if fr and fr[0] < left[0] - lay.pitch else min(w[0] for w in fm_h) - lay.pitch
        page_left = min(page_left, edge)
    if to_h:
        edge = fr[2] - 1 if fr and fr[2] > right[-1] + lay.pitch else max(w[2] for w in to_h) + lay.pitch
        page_right = max(page_right, edge)
    lcols = [page_left - 1] + left if left and page_left < left[0] else left
    for side, cs, rows in (("L", lcols, lay.left_rows), ("R", right + [page_right], lay.right_rows)):
        for n, a, b in rows:
            cells = []
            for i in range(len(cs) - 1):
                cells.append(cell_text(cs[i], cs[i + 1], a, b))
            out.append({"n": n, "side": side, "y0": a, "y1": b, "cells": cells, "xs": list(cs)})
    # 칸 이름 — 머리글을 진짜 글자로 인쇄했으면 머리글이 정한다 (L21 · 양식마다 칸 순서가 다르다).
    # 못 읽으면 행 번호 칸(글자가 행 번호와 같은 칸)을 기준으로 앞뒤를 정한다 (HRSG).
    for side in ("L", "R"):
        rs = [r for r in out if r["side"] == side]
        if not rs:
            continue
        ncell = len(rs[0]["cells"])
        roles = _header_roles(sh, rs[0]["xs"], min(r["y0"] for r in rs), lay.pitch)
        if roles:
            _apply_roles(rs, roles, side)
            continue
        hit = [sum(1 for r in rs if r["cells"][k].replace(" ", "") == str(r["n"])) for k in range(ncell)]
        k_no = max(range(ncell), key=lambda k: hit[k]) if hit else None
        for r in rs:
            c = r["cells"]
            xs = r.pop("xs")

            def box(k, r=r, xs=xs):
                return [round(xs[k], 2), round(r["y0"], 2), round(xs[k + 1], 2), round(r["y1"], 2)] \
                    if k is not None and 0 <= k < len(xs) - 1 else None
            r["no_box"] = box(k_no)
            if side == "L":
                r["fm_box"] = box(k_no - 1 if k_no else None)
            else:
                r["to_box"] = box(k_no + 1 if k_no is not None else None)
            r["no_read"] = c[k_no] if k_no is not None else ""
            if side == "L":
                r["fm"] = c[k_no - 1] if k_no and k_no >= 1 else ""
                r["desc"] = c[k_no + 1] if k_no is not None and k_no + 1 < ncell else ""
                r["kks"] = c[k_no + 2] if k_no is not None and k_no + 2 < ncell else ""
            else:
                r["kks"] = c[k_no - 2] if k_no is not None and k_no >= 2 else ""
                r["desc"] = c[k_no - 1] if k_no is not None and k_no >= 1 else ""
                r["to"] = c[k_no + 1] if k_no is not None and k_no + 1 < ncell else ""
            del r["cells"]
    return out


def _printed_numbers(sh, rows):
    """NO. 칸에 인쇄된 번호가 센 순서와 **한결같이** 어긋나면(0 부터 · 앞 장에 이어 101 부터) 인쇄된 번호를 쓴다 (L23b).
    FM · TO 는 인쇄된 번호를 가리키기 때문이다.  쪽마다 · 쪽(왼쪽/오른쪽)마다, 읽힌 번호의 8할 이상이 같은 차이일 때만."""
    for side in ("L", "R"):
        diffs = [int(r["no_read"]) - r["n"] for r in rows
                 if r["side"] == side and re.fullmatch(r"\d{1,4}", (r.get("no_read") or "").strip())]
        if len(diffs) < 5:
            continue
        c = max(set(diffs), key=diffs.count)
        if c == 0 or diffs.count(c) < 0.8 * len(diffs):
            continue
        for r in rows:
            if r["side"] == side:
                r["n"] += c
        for r in sh.rows:
            if r["side"] == side:
                r["n"] += c


def _header_roles(sh, xs, top, pitch):
    """표 머리글(첫 행 위 세 칸 높이 안)의 진짜 글자 → 칸 번호별 역할 {k: role}.  역할 둘 이상을 못 읽으면 None."""
    V = B.vocab().get("table_headers") or {}
    if not V:
        return None
    words = [w for w in sh.words if top - 3 * pitch <= (w[1] + w[3]) / 2 < top]
    roles = {}
    for k in range(len(xs) - 1):
        toks = [w[4].upper() for w in words if xs[k] < (w[0] + w[2]) / 2 < xs[k + 1]]
        if not toks:
            continue
        for role, keys in V.items():               # 순서가 우선순위 — 'TAG NO.' 는 NO. 보다 TAG 가 먼저
            if any(t in [x.upper() for x in keys] for t in toks):
                roles[k] = str(role)
                break
    got = set(roles.values())
    return roles if len(got) >= 2 and ("no" in got or "fm" in got or "to" in got) else None


def _apply_roles(rs, roles, side):
    by = {}
    for k, role in roles.items():
        by.setdefault(role, k)
    for r in rs:
        c = r["cells"]
        xs = r.pop("xs")

        def box(k, r=r, xs=xs):
            return [round(xs[k], 2), round(r["y0"], 2), round(xs[k + 1], 2), round(r["y1"], 2)] \
                if k is not None and 0 <= k < len(xs) - 1 else None
        get = lambda role: c[by[role]] if role in by and by[role] < len(c) else ""
        r["no_box"] = box(by.get("no"))
        r["no_read"] = get("no")
        r["desc"] = get("desc")
        r["kks"] = get("kks")
        if "abv" in by:
            r["abv"] = get("abv")                  # 단자 약어 (Typical 시트 · 매크로 단자와 글자 그대로 맞댄다)
        if side == "L":
            r["fm_box"] = box(by.get("fm"))
            r["fm"] = get("fm")
        else:
            r["to_box"] = box(by.get("to"))
            r["to"] = get("to")
        del r["cells"]


def _titles_from_lines(sheets):
    """제목 칸 글줄 중 묶음 대부분(절반 넘게)에 같은 줄은 프로젝트 이름 · 문서 이름이다 — 빼고 남은 줄이 그 장의 제목."""
    got = [s for s in sheets if s.get("_title_lines")]
    if not got:
        for s in sheets:
            s.pop("_title_lines", None)
        return
    cnt = defaultdict(int)
    for s in got:
        for ln in set(s["_title_lines"]):
            cnt[ln] += 1
    common = {ln for ln, c in cnt.items() if c > 0.5 * len(got) and len(got) >= 3}
    for s in sheets:
        lines_ = s.pop("_title_lines", None)
        if lines_ and not s.get("title"):
            s["title"] = " ".join(ln for ln in lines_ if ln not in common)


def _fix_o0(t):
    """O 와 0 은 그림이 같다 — 낱말 안의 다른 글자가 정한다 (글자 낱말이면 O · 숫자 낱말이면 0)."""
    out = []
    for w in re.split(r"(\s+)", t):
        letters = sum(ch.isalpha() and ch != "O" for ch in w)
        digits = sum(ch.isdigit() and ch != "0" for ch in w)
        if letters > digits:
            # 시트-행 꼴(G031-81)의 숫자 자리는 숫자다
            m = re.match(r"^([A-Z])([0O]{0,3}\d*[0O]*)(-[\dO]+)?$", w)
            if m and len(w) >= 4 and sum(ch.isdigit() or ch == "O" for ch in w[1:]) >= len(w[1:]) - 1:
                w = w[0] + w[1:].replace("O", "0")
            else:
                w = w.replace("0", "O")
        elif digits > letters:
            w = w.replace("O", "0")
        out.append(w)
    return "".join(out)


def _timer_params(sh, D):
    """타이머 블록 위·아래의 `t= 3sec` — 숫자는 읽고, 단위는 SEC/MIN 중 맞는 쪽."""
    out = {}
    for b in sh.blocks.values():
        if getattr(b, "logic", "") not in ("delay_on", "delay_off", "pulse"):
            continue
        x0, y0, x1, y1 = b.bbox
        h = y1 - y0
        # 진짜 글자로 인쇄한 시간 (19VA `1 SEC` · `T = 10 SEC` — 블록 바로 아래·위, L21)
        near = sorted((w for w in sh.words if w[2] > x0 - h and w[0] < x1 + h and
                       ((y1 - 0.5 <= w[1] < y1 + 1.3 * h) or (y0 - 1.3 * h < w[3] <= y0 + 0.5))),
                      key=lambda w: (round(w[1]), w[0]))
        m = re.search(r"(\d+(?:\.\d+)?)\s*(SEC|S|MIN|M)\b", " ".join(w[4] for w in near).upper())
        if m:
            v = float(m.group(1)) * (60 if m.group(2).startswith("M") else 1)
            out[b.id] = {"t": int(v) if v == int(v) else v, "text": f"t={m.group(1)}{m.group(2).lower()}"}
            continue
        ps = [p for p in sh.glyph_polys if p.bbox[2] > x0 - h and p.bbox[0] < x1 + h and
              ((y0 - 1.3 * h < p.bbox[3] <= y0 + 0.5) or (y1 - 0.5 <= p.bbox[1] < y1 + 1.3 * h))]
        cs = sorted(glyphs.chars(ps), key=lambda c: c.cx)
        if not cs:
            continue
        reads = [D.classify(c.raster) for c in cs]
        # 단위 자리: 연달은 세 글자가 SEC / MIN 에 가장 잘 맞는 곳.  숫자는 그 바로 앞의 연달은 숫자 판독
        best = None
        for j in range(1, len(cs) - 2):
            w, sc, _ = B.decode(D, cs[j:j + 3], ["SEC", "MIN"])
            if w and (best is None or sc > best[1]):
                best = (j, sc, w)
        if best is None:
            continue
        j, _, unit = best
        k = j
        while k > 0 and reads[k - 1][0].isdigit() and reads[k - 1][1] >= 0.45:
            k -= 1
        digits = "".join(r[0] for r in reads[k:j])
        if not digits:
            continue
        mult = 60 if unit == "MIN" else 1
        out[b.id] = {"t": int(digits) * mult, "text": f"t={digits}{unit.lower()}"}
    return out


# ------------------------------------------------------------------ 내보내기

def _export(sh, pno, sheet_no, title, rows, timers):
    nets = {}
    for nid, n in sh.nets.items():
        nets[str(nid)] = {"segs": n["segs"], "jumps": n.get("jumps", []), "dashed": n["dashed"]}
    blks = {}
    for b in sh.blocks.values():
        blks[b.id] = {
            "kind": b.kind, "func": getattr(b, "func", ""), "logic": getattr(b, "logic", "unknown"),
            "label": getattr(b, "label", ""), "read": getattr(b, "read", ""), "score": getattr(b, "score", 0),
            "bbox": [round(v, 2) for v in b.bbox], "cells": [[round(v, 2) for v in c] for c in b.cells],
            "param": dict(getattr(b, "param", {})), "group": getattr(b, "group", ""),
            "pointer": b.pointer, "roles": getattr(b, "roles", {}),
        }
        if b.kind in ("RECT", "CIRCLE"):
            blks[b.id]["key"] = legend.keys_of(b, sh.words)[0]      # L22 — 모양|안 글자 (사람이 종류를 정하면 사전 열쇠)
        if getattr(b, "learned", ""):
            blks[b.id]["learned"] = b.learned
        if getattr(b, "func", "") == "MACRO":
            blks[b.id]["pins"] = dict(getattr(b, "pins", {}))
            blks[b.id]["lines"] = [list(ln) for ln in getattr(b, "lines", [])]
        if b.id in timers:
            blks[b.id]["param"].update(timers[b.id])
    ports = []
    for pt in sh.ports:
        b = sh.blocks[pt.block]
        role = ""
        if getattr(b, "func", "") == "MEMORY":
            role = "set" if pt.cell == 0 else "reset"
            if pt.dir == "out":
                role = "q" if pt.cell == 0 else "qn"
        elif getattr(b, "func", "") == "STEP":
            role = b.roles.get(f"{pt.at[0]},{pt.at[1]}", "")
        d = pt.dir
        if getattr(b, "logic", "") == "sink" and pt.side == "":
            d = "in"                                    # 램프 · 경보 · 기록은 받기만 한다 (범례 G003)
        pd = {"block": pt.block, "net": str(pt.net), "dir": d, "at": list(pt.at),
              "side": pt.side, "cell": pt.cell, "role": role}
        if getattr(b, "func", "") == "MACRO":
            pd["pin"] = b.pins.get(f"{pt.at[0]},{pt.at[1]}", "")
        ports.append(pd)
    rmap = {(r["side"], r["n"]): r for r in rows}
    srows = []
    for r in sh.rows:
        if r["n"] is None:
            continue
        info = rmap.get((r["side"], r["n"]), {})
        srows.append({"n": r["n"], "side": r["side"], "net": str(r["net"]), "at": list(r["at"]),
                      **{k: v for k, v in info.items() if k in ("fm", "desc", "kks", "abv", "to", "no_read", "y0", "y1", "fm_box", "to_box", "no_box")}})
    lay = sh.layout
    out = {
        "page": pno, "sheet_no": sheet_no or "", "title": title,
        "logic": [round(v, 2) for v in lay.logic], "pitch": lay.pitch,
        "frame": [round(v, 2) for v in sh.frame] if sh.frame else None,
        "nets": nets, "blocks": blks, "ports": ports, "rows": srows, "table": rows,
        "dangling": [list(d) for d in sh.dangling], "stray_arrows": [list(d) for d in sh.stray_arrows],
    }
    out["order"] = _net_order(out)
    return out


def _net_order(s):
    """넷마다 몰이 자리에서 바깥으로 선분 순서 · 시작 거리 (그림 위에서 신호가 흘러가는 모습)."""
    drv = defaultdict(list)
    for p in s["ports"]:
        if p["dir"] == "out":
            drv[p["net"]].append(tuple(p["at"]))
    for r in s["rows"]:
        if r["side"] == "L":
            drv[r["net"]].append(tuple(r["at"]))
    order = {}
    for nid, n in s["nets"].items():
        segs = [tuple(x) for x in n["segs"]] + [tuple(x) for x in n.get("jumps", [])]
        if not segs:
            continue
        pts = defaultdict(list)            # 점 → [(seg 번호, 반대 끝)]
        key = lambda q: (round(q[0], 1), round(q[1], 1))
        for k, sg in enumerate(segs):
            a, b = (sg[0], sg[1]), (sg[2], sg[3])
            pts[key(a)].append((k, b))
            pts[key(b)].append((k, a))
        roots = drv.get(nid) or [(segs[0][0], segs[0][1])]
        # 몰이 자리에 가장 가까운 선분 끝에서 시작
        start = min(pts, key=lambda q: min(math.hypot(q[0] - r[0], q[1] - r[1]) for r in roots))
        dist = {start: 0.0}
        seen = set()
        res = []
        frontier = [(0.0, start)]
        import heapq
        while frontier:
            d0, q = heapq.heappop(frontier)
            if d0 > dist.get(q, 1e18):
                continue
            for k, other in pts[q]:
                if k in seen:
                    continue
                seen.add(k)
                L = math.hypot(other[0] - q[0], other[1] - q[1])
                res.append([round(q[0], 2), round(q[1], 2), round(other[0], 2), round(other[1], 2), round(d0, 1)])
                ok = key(other)
                if d0 + L < dist.get(ok, 1e18):
                    dist[ok] = d0 + L
                    heapq.heappush(frontier, (d0 + L, ok))
        # T 로 붙은 선분(끝이 다른 선분 몸통 위) — 위에서 못 닿은 것은 끝에 붙인다
        for k, sg in enumerate(segs):
            if k not in seen:
                res.append([sg[0], sg[1], sg[2], sg[3], round(max(dist.values()), 1)])
        order[nid] = res
    return order


# ------------------------------------------------------------------ 시트 간 참조

def _cross_refs(sheets):
    """왼쪽 행의 FM `G031-81` → G031 장의 81행 (오른쪽 출력).  읽은 글자 그대로 맞댄다."""
    by_no = {s["sheet_no"]: s for s in sheets if s["sheet_no"]}
    bundle = RF.Bundle(by_no)
    for s in sheets:
        for r in s["rows"]:
            if r["side"] != "L":
                continue
            m = RF.full(r.get("fm"), by_no)
            if not m:
                continue
            sh, rn = m
            tgt = by_no.get(sh)
            r["ref"] = {"sheet": sh, "row": rn, "page": tgt["page"] if tgt else None,
                        "other_bundle": bundle.other(sh)}   # 다른 묶음 (Logic 의 P… = Loop 장 · 다른 문서)
            if tgt:
                for tr in tgt["rows"]:
                    if tr["side"] == "R" and tr["n"] == rn:
                        tr.setdefault("refs_in", []).append({"sheet": s["sheet_no"], "page": s["page"], "row": r["n"]})


def _findings(s):
    """연결 적합성 — 끊긴 선 끝 · 가리키는 곳 없는 화살촉 · 짝 없는 연결 기호 · 판독 못 한 블록 · 시트 참조."""
    f = []
    for x, y, net in s["dangling"]:
        f.append({"code": "C1_DANGLING", "at": [x, y], "net": str(net), "text": "선 끝이 아무 데도 닿지 않습니다"})
    for x, y, net in s["stray_arrows"]:
        f.append({"code": "C1_ARROW_NOWHERE", "at": [x, y], "net": str(net), "text": "화살촉이 가리키는 블록이 없습니다"})
    groups = defaultdict(list)
    for bid, b in s["blocks"].items():
        if b["func"] == "CONNECTOR":
            groups[b["group"] or bid].append(bid)
    pdir = defaultdict(set)
    for p in s["ports"]:
        pdir[p["block"]].add(p["dir"])
    for g, ids in groups.items():
        ins = [i for i in ids if "in" in pdir[i]]
        outs = [i for i in ids if "out" in pdir[i]]
        lab = s["blocks"][ids[0]]["label"]
        if ins and not outs:
            for i in ins:
                f.append({"code": "C7_CONNECTOR_NO_SOURCE_OUT", "block": i,
                          "text": f"연결 기호 '{lab}' 로 들어가는 신호를 이 장 안에서 받는 곳이 없습니다"})
        if outs and not ins:
            for i in outs:
                f.append({"code": "C7_CONNECTOR_NO_SOURCE", "block": i,
                          "text": f"연결 기호 '{lab}' 가 내보내는 신호의 출처가 이 장 안에 없습니다"})
    for bid, b in s["blocks"].items():
        if b["func"] == "UNKNOWN" and ("in" in pdir[bid]):
            f.append({"code": "BLOCK_UNKNOWN", "block": bid,
                      "text": f"블록 글자를 범례 어휘로 판정하지 못했습니다 (읽은 글자: {b['read'] or '없음'})"})
        if b["logic"] in ("and", "or", "nand", "nor", "not") and "in" not in pdir[bid] and pdir[bid]:
            f.append({"code": "C3_GATE_NO_INPUT", "block": bid,
                      "text": f"{b['func']} 게이트에 들어오는 선을 찾지 못했습니다 (도면을 확인하세요)"})
        if not pdir[bid] and b["func"] not in ("CONNECTOR",):
            f.append({"code": "C3_BLOCK_UNCONNECTED", "block": bid, "text": "선이 하나도 닿지 않은 블록입니다"})
    return f
