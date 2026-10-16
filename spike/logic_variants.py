"""LOGIC — 처음 보는 양식의 Logic Diagram 을 흉내 낸 묶음을 만들어 분석 · 시뮬레이션이 버티는지 본다 (L24).

한 변형 = 두 장짜리 묶음 (A 장: 게이트 다섯 · B 장: A 의 출력을 FM 으로 받음).  변형마다 한 가지(또는 몇 가지)를
기준 양식에서 바꾼다 — 회전 · 선 색 · 머리글 낱말 · 참조 꼴 · 게이트 기호(글자/모양/IEC/ANSI) · 종이 크기 · 소문자 ·
행 번호 없음 · 칸 순서 · 글자 없는 PDF · 표 없는 PDF …

검사 (변형마다): ① 분석이 끝나거나 사람이 알아들을 사유로 멈춘다 ② 시트 이름 ③ 표 칸(FM · 설명 · TO) ④ B 장 FM 이 A 장
출력 행에 이어진다 ⑤ 게이트 판정 ⑥ 시뮬레이션: 2·3행 → AND 출력 1 · 2행만 → 0 · B 장으로 넘어감 ⑦ 게이트가 입력과
어긋나지 않음.

    python3 spike/logic_variants.py [이름 …]        # 결과 표 · 실패 사유
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pymupdf  # noqa: E402

W0, H0 = 1191.0, 842.0
N = 50
LCOLS = [30.0, 90.0, 110.0, 180.0, 320.0]
RCOLS = [870.0, 1010.0, 1080.0, 1100.0, 1160.0]

BASE = dict(rot=0, color=(0, 0, 0), headers=("FROM", "NO.", "TAG NO.", "SERVICE", "SERVICE", "TAG NO.", "NO.", "TO"),
            sep="-", sheets=("AB_G-101", "AB_G-102"), gates="text", scale=1.0, lower=False, numbers=True,
            order="std", text=True, table=True, width=0.72, cap="SHEET", dash=None, frame_table=False,
            row_start=1, ref_fmt="{s}{sep}{n}")


class V:
    def __init__(self, name, **kw):
        self.name = name
        self.o = dict(BASE, **kw)


VARIANTS = [
    V("base"),
    V("rot90", rot=90), V("rot180", rot=180), V("rot270", rot=270),
    V("blue_lines", color=(0.1, 0.1, 0.6)),
    V("green_lines", color=(0.0, 0.5, 0.0)),
    V("thick_lines", width=1.6),
    V("hdr_source", headers=("SOURCE", "NO", "TAG", "DESCRIPTION", "DESCRIPTION", "TAG", "NO", "DESTINATION")),
    V("hdr_fromsheet", headers=("FROM SHEET", "LINE", "INSTRUMENT", "SIGNAL NAME", "SIGNAL NAME", "INSTRUMENT", "LINE", "TO SHEET")),
    V("hdr_io", headers=("INPUT FROM", "NO.", "KKS", "DESCRIPTION", "DESCRIPTION", "KKS", "NO.", "OUTPUT TO")),
    V("ref_slash", sep="/"), V("ref_dot", sep="."), V("ref_colon", sep=":"), V("ref_space", ref_fmt="{s} / {n}"),
    V("ref_paren", ref_fmt="({s}-{n})"), V("ref_sheetword", ref_fmt="SH.{s} NO.{n}"),
    V("sheet_plain", sheets=("101", "102")), V("sheet_dotted", sheets=("LD.01.001", "LD.01.002")),
    V("sheet_long", sheets=("1A9Z-10ABC-LGC-0101", "1A9Z-10ABC-LGC-0102")),
    V("cap_sheetno", cap="SHEET NO."), V("cap_page", cap="PAGE"), V("cap_dwgno", cap="DWG. NO."),
    V("gate_shape", gates="shape"), V("gate_iec", gates="iec"), V("gate_ansi", gates="ansi"),
    V("lower", lower=True), V("a1_paper", scale=2.0), V("small_text", scale=0.7),
    V("no_numbers", numbers=False), V("row_start0", row_start=0),
    V("cols_reversed", order="rev"),
    V("frame_table", frame_table=True),
    V("dashed_signal", dash="[4 2] 0"),
    V("no_text", text=False), V("no_table", table=False),
    V("mixed", rot=90, color=(0.1, 0.1, 0.6), sep="/", gates="iec", sheets=("101", "102"), cap="PAGE",
      headers=("SOURCE", "NO", "TAG", "DESCRIPTION", "DESCRIPTION", "TAG", "NO", "DESTINATION")),
]


# ------------------------------------------------------------------ 그리기

class Pen:
    def __init__(self, page, o):
        self.p, self.o = page, o
        self.k = o["scale"]

    def X(self, v):
        return v * self.k

    def line(self, *pts, dash=None):
        sh = self.p.new_shape()
        for a, b in zip(pts, pts[1:]):
            sh.draw_line(pymupdf.Point(self.X(a[0]), self.X(a[1])), pymupdf.Point(self.X(b[0]), self.X(b[1])))
        sh.finish(color=self.o["color"], width=self.o["width"] * self.k, closePath=False, dashes=dash)
        sh.commit()

    def rect(self, r, fill=None):
        sh = self.p.new_shape()
        sh.draw_rect(pymupdf.Rect(*(self.X(v) for v in r)))
        sh.finish(color=self.o["color"], width=self.o["width"] * self.k, fill=fill)
        sh.commit()

    def circle(self, c, r, fill=None):
        sh = self.p.new_shape()
        sh.draw_circle(pymupdf.Point(self.X(c[0]), self.X(c[1])), r * self.k)
        sh.finish(color=self.o["color"], width=self.o["width"] * self.k, fill=fill)
        sh.commit()

    def curve(self, p0, p1, p2, p3):
        sh = self.p.new_shape()
        sh.draw_bezier(*(pymupdf.Point(self.X(a), self.X(b)) for a, b in (p0, p1, p2, p3)))
        sh.finish(color=self.o["color"], width=self.o["width"] * self.k, closePath=False)
        sh.commit()

    def text(self, x, y, t, size=5):
        if not self.o["text"] or not t:
            return
        if self.o["lower"]:
            t = t.lower()
        self.p.insert_text((self.X(x), self.X(y)), t, fontsize=size * self.k)


def P_(o):
    return 11.3


def TOP(o):
    return 70.0


def ry(n):
    return 70.0 + ((n - 1) % N) * 11.3 + 11.3 / 2


def _table(pen, o, sheet_no, rows_l, rows_r):
    P, T = 11.3, 70.0
    bottom = T + N * P
    lc, rc = list(LCOLS), list(RCOLS)
    if o["frame_table"]:
        lc, rc = lc[1:], rc[:-1]
    if o["table"]:
        for x in lc + rc:
            pen.line((x, T - 2 * P), (x, bottom))
        for k in range(N + 1):
            pen.line((LCOLS[0], T + k * P), (LCOLS[-1], T + k * P))
            pen.line((RCOLS[0], T + k * P), (RCOLS[-1], T + k * P))
        if o["frame_table"]:
            sh = pen.p.new_shape()
            sh.draw_rect(pymupdf.Rect(10 * pen.k, 10 * pen.k, (W0 - 10) * pen.k, (H0 - 10) * pen.k))
            sh.draw_rect(pymupdf.Rect((LCOLS[0] - 2) * pen.k, 12 * pen.k, (RCOLS[-1] + 2) * pen.k, (H0 - 12) * pen.k))
            sh.finish(color=None, fill=(0, 0, 0), even_odd=True, width=0)
            sh.commit()
    hx = [32, 92, 112, 182, 872, 1012, 1082, 1102]
    hd = list(o["headers"])
    if o["order"] == "rev":                       # 왼쪽 표 칸 순서를 뒤집음 (SERVICE | TAG | NO. | FROM)
        hd = [hd[3], hd[2], hd[1], hd[0]] + hd[4:]
    for x, t in zip(hx, hd):
        pen.text(x, T - 8, t, 6)
    pen.text(560, T - 8, "LOGIC", 7)
    # 칸 x (왼쪽: FM · NO · TAG · DESC)
    if o["order"] == "rev":
        cx = {"desc": 32, "tag": 92, "no": 112, "fm": 182}
    else:
        cx = {"fm": 32, "no": 95, "tag": 112, "desc": 182}
    for k in range(N):
        if o["numbers"]:
            pen.text(cx["no"], T + k * P + 8, str(k + o["row_start"]), 5)
            pen.text(1083, T + k * P + 8, str(N + k + o["row_start"]), 5)
    for n, (fm, desc) in rows_l.items():
        pen.text(cx["fm"], ry(n) + 2, fm)
        pen.text(cx["desc"], ry(n) + 2, desc)
    for n, (desc, to) in rows_r.items():
        pen.text(872, ry(n) + 2, desc)
        pen.text(1102, ry(n) + 2, to)
    pen.text(950, 805, "1Z9Z-00GEN00-J09-0099", 8)
    pen.text(1098, 790, o["cap"], 5)
    pen.text(1098, 800, sheet_no, 7)


def _gate(pen, o, kind, x, y):
    """게이트 하나 → (입력 x, 출력 점).  kind: AND · OR · NOT · ON · VOTE"""
    g, P = o["gates"], 11.3
    if g == "text" or (g == "shape" and kind in ("ON", "VOTE")):
        word = {"AND": "AND", "OR": "OR", "NOT": "NOT", "ON": "DI", "VOTE": "2/3"}[kind]
        if kind in ("AND", "OR", "VOTE"):
            pen.line((x, y - 1.25 * P), (x, y + 1.25 * P))
        pen.rect((x, y - 4.5, x + 14, y + 4.5))
        pen.text(x + 1.5, y + 2, word)
        if kind == "ON":
            pen.text(x + 2, y + 11, "3 sec")
        return x, (x + 14, y)
    if g == "shape":                                   # 19VA 모양 — 막대 + 네모(AND) · 막대 + 원(OR) · ⊠(NOT)
        if kind == "AND":
            pen.line((x, y - 1.25 * P), (x, y + 1.25 * P))
            pen.rect((x, y - 4.5, x + 8.5, y + 4.5))
            return x, (x + 8.5, y)
        if kind == "OR":
            pen.line((x, y - 1.25 * P), (x, y + 1.25 * P))
            pen.circle((x + 4.8, y), 4.8)
            return x, (x + 9.6, y)
        pen.rect((x, y - 4, x + 8, y + 4))
        pen.line((x, y - 4), (x + 8, y + 4))
        pen.line((x, y + 4), (x + 8, y - 4))
        return x, (x + 8, y)
    if g == "iec":                                     # IEC 60617 — 네모 안 '&' · '≥1' · '1' + 출력 원 · 'T 0'
        word = {"AND": "&", "OR": ">=1", "NOT": "1", "ON": "T  0", "VOTE": ">=2"}[kind]
        pen.rect((x, y - 1.25 * P, x + 16, y + 1.25 * P))
        pen.text(x + 4, y + 2, word, 6)
        if kind == "NOT":
            pen.circle((x + 17.5, y), 1.5)
            return x, (x + 19, y)
        if kind == "ON":
            pen.text(x + 2, y + 1.25 * P + 7, "3 s")
        return x, (x + 16, y)
    # ANSI distinctive — D 모양 AND · 구부린 OR · 삼각형+원 NOT
    h = 1.25 * P
    if kind in ("AND", "VOTE"):
        pen.line((x + 8, y - h), (x, y - h), (x, y + h), (x + 8, y + h))
        pen.curve((x + 8, y - h), (x + 8 + 1.1 * h, y - h), (x + 8 + 1.1 * h, y + h), (x + 8, y + h))
        if kind == "VOTE":
            pen.text(x + 3, y + 2, "2/3")
        return x, (x + 8 + 0.83 * h, y)
    if kind == "OR":
        pen.curve((x, y - h), (x + 5, y - h / 2), (x + 5, y + h / 2), (x, y + h))
        pen.curve((x, y - h), (x + 14, y - h), (x + 22, y - 2), (x + 24, y))
        pen.curve((x, y + h), (x + 14, y + h), (x + 22, y + 2), (x + 24, y))
        return x + 3, (x + 24, y)
    if kind == "NOT":
        pen.line((x, y - 6), (x, y + 6), (x + 10, y), (x, y - 6))
        pen.circle((x + 11.5, y), 1.5)
        return x, (x + 13, y)
    pen.rect((x, y - 4.5, x + 14, y + 4.5))
    pen.text(x + 2, y + 2, "TON")
    pen.text(x + 2, y + 11, "3 sec")
    return x, (x + 14, y)


def _ref(o, s, n):
    return o["ref_fmt"].format(s=s, n=n, sep=o["sep"])


def sheet_a(pen, o):
    s1, s2 = o["sheets"]
    rs = o["row_start"] - 1
    _table(pen, o, s1,
           {2: ("HMI", "PUMP A RUN"), 3: ("HMI", "PUMP B RUN"), 5: ("FIELD", "LEVEL LOW"),
            6: ("", "TX A HIGH"), 7: ("", "TX B HIGH"), 8: ("", "TX C HIGH"), 12: ("", "TRIP")},
           {51: ("BOTH RUN", _ref(o, s2, 2 + rs)), 52: ("LOW 3S", ""), 53: ("2OO3 HIGH", ""), 54: ("ANY RUN", ""),
            55: ("NOT TRIP", "")})
    LX0, LX1 = LCOLS[-1], RCOLS[0]
    dash = o["dash"]
    # AND 2·3 → 51
    ym = (ry(2) + ry(3)) / 2
    xin, out = _gate(pen, o, "AND", 500, ym)
    pen.line((LX0, ry(2)), (xin, ry(2)), dash=dash)
    pen.line((LX0, ry(3)), (xin, ry(3)), dash=dash)
    pen.line(out, (700, out[1]), (700, ry(51)), (LX1, ry(51)), dash=dash)
    # ON delay 5 → 52
    xin, out = _gate(pen, o, "ON", 500, ry(5))
    pen.line((LX0, ry(5)), (xin, ry(5)), dash=dash)
    pen.line(out, (710, out[1]), (710, ry(52)), (LX1, ry(52)), dash=dash)
    # VOTE 6·7·8 → 53
    xin, out = _gate(pen, o, "VOTE", 520, ry(7))
    for n in (6, 7, 8):
        pen.line((LX0, ry(n)), (xin, ry(n)), dash=dash)
    pen.line(out, (720, out[1]), (720, ry(53)), (LX1, ry(53)), dash=dash)
    # OR 2·3 (갈라짐 · 연결점) → 54
    oy = ry(10)
    for y, x in ((ry(2), 420.0), (ry(3), 440.0)):
        pen.circle((x, y), 1.2, fill=o["color"])
    xin, out = _gate(pen, o, "OR", 560, oy)
    pen.line((420, ry(2)), (420, oy - 4), (xin, oy - 4), dash=dash)
    pen.line((440, ry(3)), (440, oy + 4), (xin, oy + 4), dash=dash)
    pen.line(out, (730, out[1]), (730, ry(54)), (LX1, ry(54)), dash=dash)
    # NOT 12 → 55
    xin, out = _gate(pen, o, "NOT", 600, ry(12))
    pen.line((LX0, ry(12)), (xin, ry(12)), dash=dash)
    pen.line(out, (740, out[1]), (740, ry(55)), (LX1, ry(55)), dash=dash)


def sheet_b(pen, o):
    s1, s2 = o["sheets"]
    rs = o["row_start"] - 1
    _table(pen, o, s2, {2: (_ref(o, s1, 51 + rs), "BOTH RUN")}, {51: ("GO", "")})
    pen.line((LCOLS[-1], ry(2)), (600, ry(2)), (600, ry(51)), (RCOLS[0], ry(51)), dash=o["dash"])


def make(v, path):
    o = v.o
    k = o["scale"]
    src = pymupdf.open()
    for fn in (sheet_a, sheet_b):
        pg = src.new_page(width=W0 * k, height=H0 * k)
        fn(Pen(pg, o), o)
    if not o["rot"]:
        src.save(path)
        return path
    doc = pymupdf.open()
    for i in range(len(src)):
        w, h = W0 * k, H0 * k
        if o["rot"] in (90, 270):
            p = doc.new_page(width=h, height=w)
        else:
            p = doc.new_page(width=w, height=h)
        p.show_pdf_page(p.rect, src, i, rotate=o["rot"])
        p.set_rotation(o["rot"])
    doc.save(path)
    return path


# ------------------------------------------------------------------ 검사

def check(v, res):
    from app.logic import fromto, sim
    o = v.o
    s1, s2 = o["sheets"]
    rs = o["row_start"] - 1
    out = {}
    sh = {s.get("sheet_no"): s for s in res["sheets"]}
    A, B = sh.get(s1), sh.get(s2)
    out["sheet_ids"] = bool(A and B)
    if not (A and B):
        out["got_ids"] = [s.get("sheet_no") for s in res["sheets"]]
        return out
    t = {(r["side"], r["n"]): r for r in A["table"]}
    want_fm = "HMI"
    r2 = t.get(("L", 2 + rs)) or {}
    out["cells"] = (r2.get("fm", "").upper() == want_fm and "PUMP A RUN" in (r2.get("desc") or "").upper())
    if not out["cells"]:
        out["cell_got"] = (r2.get("fm"), r2.get("desc"), r2.get("no_read"))
    fromto.check(res["sheets"])
    rb = next((r for r in B["rows"] if r["side"] == "L" and r["n"] == 2 + rs), None)
    out["link"] = bool(rb and (rb.get("ref") or {}).get("page") == A["page"])
    if not out["link"]:
        tb = {(r["side"], r["n"]): r for r in B["table"]}
        out["link_got"] = ((tb.get(("L", 2 + rs)) or {}).get("fm"), rb and rb.get("ref"))
    funcs = sorted(b["func"] for b in A["blocks"].values())
    logics = {b["logic"] for b in A["blocks"].values()}
    out["gates"] = {"and", "or", "not", "delay_on", "vote"} <= logics
    out["funcs"] = funcs

    def outs(forces, s=A):
        r = sim.simulate_bundle(res["sheets"], {A["page"]: forces}, focus=s["page"])
        vals = r["focus"]["frames"][-1]["values"]
        return {x["n"]: vals.get(str(x["net"]), vals.get(x["net"])) for x in s["rows"] if x["side"] == "R"}
    try:
        n51 = 51 + rs
        a = outs({f"row:{2 + rs}": 1, f"row:{3 + rs}": 1})
        b = outs({f"row:{2 + rs}": 1})
        c = outs({f"row:{2 + rs}": 1, f"row:{3 + rs}": 1}, s=B)
        out["sim"] = a.get(n51) == 1 and b.get(n51) == 0 and c.get(n51) == 1
        if not out["sim"]:
            out["sim_got"] = (a.get(n51), b.get(n51), c.get(n51))
    except Exception as e:  # noqa: BLE001
        out["sim"] = False
        out["sim_err"] = repr(e)
    # 게이트가 입력과 어긋나는 틀이 없는가 (L18)
    bad = 0
    idx = sim._index(A)
    for force in ({}, {f"row:{2 + rs}": 1}, {f"row:{2 + rs}": 1, f"row:{3 + rs}": 1, f"row:{6 + rs}": 1, f"row:{8 + rs}": 1}):
        r = sim.simulate(A, force)
        for fr in r["frames"]:
            ins, outs_, drivers = idx[0], idx[1], idx[2]
            unread = set(fr.get("unread", []))
            val = lambda n: None if n in unread else fr["values"].get(n, 0)
            for bid, b in A["blocks"].items():
                lg = b["logic"]
                vt = sim._vote_of(b)
                if lg not in sim.MIN_INPUTS and not vt:
                    continue
                iv = [val(n) for n, _, _ in ins[bid]]
                exp = sim._vote3(iv, *vt) if vt else sim.gate3(lg, iv)
                exp = 0 if exp is None else exp
                for n, _, _ in outs_[bid]:
                    if len(drivers.get(n, [])) == 1 and fr["values"].get(n, 0) != exp:
                        bad += 1
    out["logical"] = bad == 0
    return out


def run(names=None):
    from app.logic import analyse
    rows = []
    tmp = tempfile.mkdtemp(prefix="lv_")
    for v in VARIANTS:
        if names and v.name not in names:
            continue
        path = os.path.join(tmp, v.name + ".pdf")
        make(v, path)
        t = time.time()
        rec = {"name": v.name}
        try:
            res = analyse.analyse(path)
            rec.update(check(v, res))
        except Exception as e:  # noqa: BLE001
            rec["stopped"] = f"{type(e).__name__}: {e}"
            rec["clean_stop"] = type(e).__name__ in ("NotLogic",)
            if not rec["clean_stop"]:
                rec["trace"] = traceback.format_exc().splitlines()[-4:]
        rec["s"] = round(time.time() - t, 1)
        rows.append(rec)
        keys = ("sheet_ids", "cells", "link", "gates", "sim", "logical")
        flag = "STOP" if "stopped" in rec else " ".join(("o" if rec.get(k) else "X") for k in keys)
        print(f"{v.name:16s} {flag:24s} {json.dumps({k: rec[k] for k in rec if k not in keys + ('name', 'funcs')}, ensure_ascii=False)[:260]}",
              flush=True)
    return rows


if __name__ == "__main__":
    run(sys.argv[1:] or None)
