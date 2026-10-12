"""블록의 뜻 — 안의 선 글자를 읽어 범례 어휘(config/logic_symbols.yaml)에 맞댄다.

읽기는 두 겹이다:
  1. 글자 사전으로 한 자씩 읽는다 (glyphs.py) — 사람이 보는 판독 결과.
  2. 판정은 어휘 낱말 중 **글자 수가 같은 것**에 맞대 고른다.  블록 글자는 작게 인쇄돼 한 자씩 읽으면
     D↔0 처럼 헷갈리지만, 낱말 단위로 맞대면 갈린다.  1·2위의 차가 없으면 UNKNOWN (사람이 정한다).
단자 역할(메모리의 S·R · STEP 상자의 단자 이름)도 같은 방식으로 정한다.
"""
from __future__ import annotations

import copy
from functools import lru_cache
from pathlib import Path

import yaml

from . import glyphs

MIN_SCORE = 0.30      # 낱말 평균 맞음 — 이보다 낮으면 그 낱말이 아니다 (같은 글꼴 글자끼리는 0.4 이상)
MIN_MARGIN = 0.03     # 1·2위 차


@lru_cache(maxsize=1)
def vocab():
    p = Path(__file__).resolve().parent.parent.parent / "config" / "logic_symbols.yaml"
    try:
        from app import paths
        p2 = paths.resource("config", "logic_symbols.yaml")
        if p2.exists():
            p = p2
    except Exception:
        pass
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def _char_score(D, ch, r):
    if not D.ex.get(ch):
        return None
    return D.scores(r).get(ch)


def decode(D, cs, words):
    """글자들(읽는 순서) ↔ 후보 낱말.  → (낱말, 평균, 2위와의 차)  · 맞는 것이 없으면 (None, 0, 0)."""
    n = len(cs)
    res = []
    for w in words:
        if len(w) != n:
            continue
        sc = []
        ok = True
        for ch, c in zip(w.upper(), cs):
            if ch == "*":
                sc.append(MIN_SCORE)          # 아무 글자 자리 — 가장 낮은 인정 점수로 센다 (빈자리로 이득을 보지 않게)
                continue
            s = _char_score(D, ch, c.raster)
            top = max(D.scores(c.raster).values(), default=0)
            # 그 글자로 읽히는 것이 그 자리에서 가장 그럴듯한 글자들과 겨룰 만해야 한다 (MAN 을 NOR 로 맞추지 않게)
            if s is None or s < 0.8 * top:
                ok = False
                break
            sc.append(s)
        if ok and sc:
            res.append((sum(sc) / len(sc), w))
    if not res:
        return None, 0.0, 0.0
    res.sort(reverse=True)
    best, w = res[0]
    second = res[1][0] if len(res) > 1 else 0.0
    return w, best, best - second


def _order(cs):
    """세로로 쌓았나 — 글자 가운데가 위아래로 더 퍼져 있고 글자 폭이 겹치면 세로쓰기."""
    if len(cs) < 2:
        return False
    xs = max(c.cx for c in cs) - min(c.cx for c in cs)
    ys = max(c.cy for c in cs) - min(c.cy for c in cs)
    return ys > xs and xs < max(c.w for c in cs)


def _on_edge(p, cell, tol):
    return all(min(abs(x - cell[0]), abs(x - cell[2])) <= tol or min(abs(y - cell[1]), abs(y - cell[3])) <= tol
               for s in p.segs for x, y in s.ends()) and all(s.vert or s.horiz for s in p.segs)


def _cell_chars(polys, cell):
    w, h = cell[2] - cell[0], cell[3] - cell[1]
    tol = 0.04 * min(w, h)
    ps = [p for p in polys if cell[0] <= (p.bbox[0] + p.bbox[2]) / 2 <= cell[2]
          and cell[1] <= (p.bbox[1] + p.bbox[3]) / 2 <= cell[3] and not _on_edge(p, cell, tol)]
    cs = glyphs.chars(ps)
    # 칸 폭 대부분을 가로지르는 납작한 획은 글자가 아니라 겹테두리 선이다
    cs = [c for c in cs if not ((c.h < 0.1 * c.w and c.w > 0.6 * w) or (c.w < 0.1 * c.h and c.h > 0.6 * h))]
    # 칠 자국 부스러기 (글자 크기의 15% 미만) 는 글자가 아니다
    if cs:
        big = max(max(c.w, c.h) for c in cs)
        cs = [c for c in cs if max(c.w, c.h) >= 0.25 * big]
    vert = _order(cs)
    cs.sort(key=(lambda c: c.cy) if vert else (lambda c: c.cx))
    return cs, vert


def _read_free(D, cs, vert):
    if not cs:
        return ""
    out = []
    for line in glyphs.lines(cs, vertical=vert):
        s, _ = glyphs.read(D, line, vertical=vert)
        out.append(s)
    return " ".join(out)


def classify(sheet, D):
    """sheet.blocks 의 func · label · role 을 채운다 (제자리)."""
    V = vocab()
    funcs = V["functions"]
    words = {w: name for name, f in funcs.items() for w in f["words"]}
    mem_set = V["memory_cells"]["set"]
    mem_reset = V["memory_cells"]["reset"]
    mark = V["memory_cells"]["dominant_mark"]
    byid = {p.pid: p for p in sheet.glyph_polys}
    split = []
    for b in sheet.blocks.values():
        polys = [byid[i] for i in b.glyphs if i in byid]
        b.read = ""
        b.score = 0.0
        b.roles = {}
        b.param = {}
        if b.kind == "RECT":
            cells = b.cells
            reads = []
            for cell in cells:
                cs, vert = _cell_chars(polys, cell)
                reads.append((cell, cs, vert))
            b.read = " | ".join(_read_free(D, cs, vert) for _, cs, vert in reads)
            # 메모리: 위·아래 두 칸, 각 칸이 S/SO · R/RO
            if len(cells) == 2 and abs(cells[0][0] - cells[1][0]) < 1 and cells[0][1] < cells[1][1]:
                w0, s0, m0 = decode(D, reads[0][1], mem_set + mem_reset)
                w1, s1, m1 = decode(D, reads[1][1], mem_set + mem_reset)
                if w0 in mem_set and w1 in mem_reset and min(s0, s1) >= MIN_SCORE:
                    dom = "set" if mark in w0[1:] else ("reset" if mark in w1[1:] else "")
                    b.func = "MEMORY"
                    b.logic = "memory"
                    b.param = {"dominant": dom}
                    b.label = f"{w0}/{w1}"
                    b.score = round(min(s0, s1), 3)
                    b.roles = {"set_cell": 0, "reset_cell": 1}
                    continue
            # PB 누름단추 · 이름 칸 (왼쪽 칸이 PB)
            if len(cells) >= 2:
                w0, s0, m0 = decode(D, reads[0][1], [w for w in words if funcs[words[w]]["logic"] == "source"])
                if w0 and s0 >= MIN_SCORE:
                    b.func = words[w0]
                    b.logic = "source"
                    b.label = (w0 + " " + " ".join(_read_free(D, r[1], r[2]) for r in reads[1:])).strip()
                    b.score = round(s0, 3)
                    continue
            if len(cells) == 1:
                cs, vert = reads[0][1], reads[0][2]
                lines = glyphs.lines(cs, vertical=vert) if cs else []
                if len(lines) == 1:
                    # 경보(ANN) · 기록(SOE) 은 범례에서 둥근 상자로 그린다 — 네모 칸에는 맞대지 않는다
                    w, s, m = decode(D, cs, [x for x in words if funcs[words[x]]["logic"] != "sink"])
                    if w and s >= MIN_SCORE and m >= MIN_MARGIN:
                        b.func = words[w]
                        b.logic = funcs[b.func]["logic"]
                        b.label = w.replace("*", "t")
                        b.score = round(s, 3)
                        continue
                # 큰 상자 — STEP 상자 (단자 이름이 안에 인쇄돼 있다)
                if len(lines) >= 3:
                    text = [_read_free(D, ln, vert) for ln in lines]
                    joined = " ".join(text)
                    if "STEP" in joined:
                        b.func = "STEP"
                        b.logic = "step"
                        b.label = text[0] if text else "STEP"
                        b.lines = []
                        for ln in lines:            # 한 줄 안의 왼쪽 글과 오른쪽 글을 가른다 (빈 틈 > 글자 높이 1.5배)
                            seg = [ln[0]]
                            for c in ln[1:]:
                                if c.bbox[0] - seg[-1].bbox[2] > 1.5 * max(c.h, seg[-1].h):
                                    b.lines.append(_seg_line(D, seg, vert))
                                    seg = []
                                seg.append(c)
                            b.lines.append(_seg_line(D, seg, vert))
                        continue
                # 큰 상자에 글줄이 여럿 — 단자 이름을 안에 인쇄한 매크로 블록 (MOV BLOCK · MCC BLOCK …, L12).
                # 내부 동작은 그 Typical 시트가 정의한다 (macro.py 가 단자 이름으로 시트와 행을 맞댄다).
                if len(lines) >= 3:
                    b.func = "MACRO"
                    b.logic = "macro"
                    b.label = b.read
                    b.lines = []
                    for ln in lines:
                        seg = [ln[0]]
                        for c in ln[1:]:
                            if c.bbox[0] - seg[-1].bbox[2] > 1.5 * max(c.h, seg[-1].h):
                                b.lines.append(_seg_line(D, seg, vert))
                                seg = []
                            seg.append(c)
                        b.lines.append(_seg_line(D, seg, vert))
                    continue
            # 맞닿아 그린 같은 게이트 둘 (GT 위·아래 · G021) — 칸마다 같은 기능 낱말 한 줄이면 칸마다 블록 하나
            if len(cells) >= 2 and all(abs(c[0] - cells[0][0]) < 1 and abs(c[2] - cells[0][2]) < 1 for c in cells):
                got = []
                for _, cs, vert in reads:
                    lines = glyphs.lines(cs, vertical=vert) if cs else []
                    w, s_, m = decode(D, cs, [x for x in words if funcs[words[x]]["logic"] not in ("sink", "source")]) \
                        if len(lines) == 1 else (None, 0, 0)
                    got.append((w, s_, m))
                if all(w and s_ >= MIN_SCORE and m >= MIN_MARGIN for w, s_, m in got) and len({words[w] for w, _, _ in got}) == 1:
                    split.append((b, got))
                    continue
            b.func = "UNKNOWN"
            b.logic = "unknown"
            b.label = b.read
        else:
            cs, vert = _cell_chars(polys, b.bbox)
            b.read = _read_free(D, cs, vert)
            gate_words = [w for w in words if funcs[words[w]]["logic"] in ("or", "nor", "sink")]
            w, s, m = decode(D, cs, gate_words) if (len(cs) >= 2 and b.kind != "CONNECTOR") else (None, 0, 0)
            if w and s >= MIN_SCORE and m >= MIN_MARGIN:
                b.func = words[w]
                b.logic = funcs[b.func]["logic"]
                b.label = w
                b.score = round(s, 3)
                continue
            # 램프 — 원 안 글자 하나 + 둘레의 빗살(대각선 획) (범례 G003 LIGHT: R G Y W)
            diag = [c for c in cs if all(not (sg.vert or sg.horiz) for sg in c.segs) and len(c.segs) <= 2]
            rest = [c for c in cs if c not in diag]
            if b.kind == "CIRCLE" and len(diag) >= 2 and len(rest) == 1:
                ch, s, m = D.classify(rest[0].raster)
                b.func = "LIGHT"
                b.logic = "sink"
                b.label = ch if s >= MIN_SCORE else "?"
                b.score = round(s, 3)
                continue
            if len(cs) == 1 or b.kind == "CONNECTOR":
                if cs:
                    c0 = max(cs, key=lambda c: c.w * c.h + c.h)       # 원 안 글자 — 가장 큰 무리
                    cs = [c0]
                ch, s, m = D.classify(cs[0].raster) if cs else ("?", 0, 0)
                b.func = "CONNECTOR"
                b.logic = "connector"
                b.label = ch if (cs and s >= MIN_SCORE) else "?"
                b.score = round(s, 3)
                b.raster = cs[0].raster if cs else None
                continue
            b.func = "UNKNOWN"
            b.logic = "unknown"
            b.label = b.read
    _split_stacked(sheet, split, funcs, words)
    # 들어오는 단자가 없는 판정 못 한 상자 = 이름 붙은 신호 상자 (FLASH · AUTO 칸 — 입력으로 쓴다)
    has_in = {pt.block for pt in sheet.ports if pt.dir == "in"}
    for b in sheet.blocks.values():
        if b.kind == "RECT" and getattr(b, "func", "") == "UNKNOWN" and b.id not in has_in:
            b.func, b.logic = "SIGNAL", "source"
    _connector_groups(sheet)
    _step_roles(sheet, D)
    _macro_pins(sheet)


def _split_stacked(sheet, split, funcs, words):
    """맞닿은 칸을 블록 하나씩으로 — 단자는 그 칸의 높이로 가른다 (위·아래 변 단자는 가까운 칸)."""
    for b, got in split:
        cells = list(b.cells)
        n = max(int(k[1:]) for k in sheet.blocks)
        ids = []
        for i, (cell, (w, s_, _)) in enumerate(zip(cells, got)):
            nb = b if i == 0 else copy.copy(b)
            if i:
                n += 1
                nb.id = f"B{n}"
                nb.glyphs = []
                sheet.blocks[nb.id] = nb
            ids.append(nb.id)
            nb.cells = [cell]
            nb.bbox = tuple(cell)
            nb.func = words[w]
            nb.logic = funcs[nb.func]["logic"]
            nb.label = w.replace("*", "t")
            nb.score = round(s_, 3)
            nb.roles = {}
            nb.param = {}
            nb.bus = [bs for bs in b.bus if min(bs[1], bs[3]) <= cell[3] and max(bs[1], bs[3]) >= cell[1]]
        for pt in sheet.ports:
            if pt.block != b.id:
                continue
            y = pt.at[1]
            k = min(range(len(cells)), key=lambda i: 0 if cells[i][1] <= y <= cells[i][3]
                    else min(abs(y - cells[i][1]), abs(y - cells[i][3])))
            pt.block = ids[k]
            pt.cell = 0


def _connector_groups(sheet):
    """같은 장의 연결 기호를 **그림이 같은 것끼리** 묶는다 (글자를 몰라도 같은 글자인지는 안다)."""
    cons = [b for b in sheet.blocks.values() if b.func == "CONNECTOR" and getattr(b, "raster", None)]
    groups = []
    for b in cons:
        for g in groups:
            same = (b.label == g[0].label) if (b.label != "?" and g[0].label != "?") else \
                glyphs.score(b.raster, g[0].raster) >= 0.75
            if same:
                g.append(b)
                break
        else:
            groups.append([b])
    for k, g in enumerate(groups):
        lab = max((x.label for x in g), key=lambda s: sum(1 for x in g if x.label == s))
        for x in g:
            x.group = f"C{k + 1}"
            x.label = lab


def _seg_line(D, cs, vert):
    return (min(c.bbox[1] for c in cs), max(c.bbox[3] for c in cs), min(c.bbox[0] for c in cs),
            max(c.bbox[2] for c in cs), _read_free(D, cs, vert).replace(" ", "").upper())


def _macro_pins(sheet):
    """매크로 블록의 단자 → 그 단자 높이·그 변 쪽에 인쇄된 상자 안 글줄 (단자 이름).  단자가 없는 상자는 매크로가 아니다."""
    P = sheet.layout.pitch
    for b in sheet.blocks.values():
        if getattr(b, "func", "") != "MACRO":
            continue
        pts = [pt for pt in sheet.ports if pt.block == b.id]
        if not any(pt.dir == "in" for pt in pts):
            b.func, b.logic = "SIGNAL", "source"       # 들어오는 단자가 없는 상자 = 이름 붙은 신호 상자 (예전 규칙)
            continue
        b.pins = {}
        half = (b.bbox[2] - b.bbox[0]) / 2
        for pt in pts:
            y = pt.at[1]
            side = []
            for y0, y1, x0, x1, t in getattr(b, "lines", []):
                on_side = (x0 - b.bbox[0] < half) if pt.side == "L" else (b.bbox[2] - x1 < half)
                if on_side and t.strip("-_"):         # 밑줄 획만 있는 조각(EN_CLOSE 의 '_')은 이름이 아니다
                    side.append((y0, y1, x0, t))
            best = None
            for y0, y1, x0, t in side:
                d = 0 if y0 <= y <= y1 else min(abs(y - y0), abs(y - y1))
                if d <= 0.8 * P and (best is None or d < best[0]):
                    best = (d, y0, y1)
            if best is None:
                b.pins[f"{pt.at[0]},{pt.at[1]}"] = ""
                continue
            # 같은 높이의 조각을 x 순으로 잇는다 — 밑줄(_)에서 글줄이 갈린다 (EN · CLOSE → ENCLOSE)
            _, by0, by1 = best
            parts = sorted((x0, t) for y0, y1, x0, t in side if y0 <= by1 and y1 >= by0)
            b.pins[f"{pt.at[0]},{pt.at[1]}"] = "".join(t for _, t in parts)


def _step_roles(sheet, D):
    """STEP 상자의 단자 → 이름 (그 단자 높이에 인쇄된 상자 안 글줄)."""
    for b in sheet.blocks.values():
        if b.func != "STEP":
            continue
        for pt in sheet.ports:
            if pt.block != b.id:
                continue
            y = pt.at[1]
            half = (b.bbox[2] - b.bbox[0]) / 2
            near = []
            for y0, y1, x0, x1, t in getattr(b, "lines", []):
                on_side = (x0 - b.bbox[0] < half) if pt.side == "L" else (b.bbox[2] - x1 < half)
                if on_side and y0 - 0.6 * sheet.layout.pitch <= y <= y1 + 0.6 * sheet.layout.pitch:
                    near.append(t)
            txt = " ".join(near)
            role = ""
            if pt.side == "L":
                role = "crit" if "CRIT" in txt else ("step_in" if ("IN" in txt or "PERVIOUS" in txt or "PREVIOUS" in txt) else "")
            elif pt.side == "R":
                if any(("OUT" in t or "OU-" in t or t.endswith("OU")) and "CMD" not in t for t in near):
                    role = "step_out"
                elif "CMD" in txt or "CSTEP" in txt or "C-STEP" in txt:
                    role = "c_step"
            b.roles[f"{pt.at[0]},{pt.at[1]}"] = role
        # 한쪽 변에 단자가 둘이고 하나만 이름을 얻었으면 다른 하나는 짝 이름이다 (STEP_IN↔CRIT · C_STEP↔STEP_OUT)
        pair = {"L": ("step_in", "crit"), "R": ("c_step", "step_out")}
        for side, (a_, b_) in pair.items():
            ks = [f"{pt.at[0]},{pt.at[1]}" for pt in sheet.ports if pt.block == b.id and pt.side == side]
            got = [b.roles.get(k, "") for k in ks]
            if len(ks) == 2 and got.count("") == 1:
                other = b_ if a_ in got else (a_ if b_ in got else "")
                b.roles[ks[got.index("")]] = other
