"""LOGIC 작도 — 분석한 로직과 **같은 양식**으로 새 로직 시트를 그린다 (L54).

문서(그림) 하나 = JSON 하나 · 저장 자리 `{data}/logic/drawings/<id>/drawing.json` (jsonstore · 작성자 필수).
좌표는 전부 **PDF 포인트**(A3 가로 1191×842 · y 는 아래로)라 화면(SVG) · PDF · DXF 가 같은 수를 쓴다.

양식 — 분석기가 읽는 그 꼴 (tests/test_logic_l23_generic.py 의 합성 장과 같다):
  왼쪽 표  FROM | NO. | TAG NO. | SERVICE   (행 1..N)
  가운데   LOGIC 영역
  오른쪽 표 SERVICE | TAG NO. | NO. | TO   (행 N+1..2N)
  타이틀블록  문서 번호 · 제목 · 캡션 `SHEET NO.` 아래 시트 이름

기호는 범례 어휘(config/logic_symbols.yaml)의 **글자 상자**로 그린다 — AND · OR · NOT · NAND · NOR · GT · DT · PD 는
글자가 든 네모(AND/OR/NAND/NOR 는 왼쁜 입력 막대) · 메모리는 S/R 두 칸 · 투표는 `2/3` · 누름단추는 `PB` + 이름 ·
연결 기호는 글자 든 원.  **분석기가 글자 상자를 읽는 규칙(blocks.isa_word · _drawn)이 곧 이 작도기의 기호 정의**라,
그려서 내보낸 PDF 를 분석기에 다시 넣으면 같은 블록 · 같은 선 · 같은 행이 나온다 (verify 가 그것을 잰다).

판정 코드는 한 줄도 부르지 않는다 — 이 모듈은 그리기 · 내보내기 · 되읽기(검증)만 한다.
"""
from __future__ import annotations

import io
import json
import math
import re
import tempfile
import time
import uuid
from pathlib import Path

import pymupdf

from app import jsonstore

from . import store

W, H = 1191.0, 842.0            # A3 가로
TOP = 70.0                      # 표 첫 행 윗변
PITCH = 11.3                    # 행 간격 (합성 장과 같다 · 분석기는 장마다 다시 잰다)
N_DEFAULT = 50
N_MIN, N_MAX = 20, 64
LCOLS = [30.0, 90.0, 110.0, 180.0, 320.0]        # FROM | NO. | TAG | SERVICE
RCOLS = [870.0, 1010.0, 1080.0, 1100.0, 1160.0]  # SERVICE | TAG | NO. | TO
LX0, LX1 = LCOLS[-1], RCOLS[0]                   # LOGIC 영역 좌우
K = (0, 0, 0)
LW = 0.72
ID_RE = re.compile(r"^[0-9a-f]{12}$")
MAX_TEXT = 200

# 기호 사전 — 화면(팔레트 · 그리기) · PDF · DXF 가 같은 것을 읽는다.  logic 은 범례 어휘(logic_symbols.yaml)의 동작 이름.
#   text  : 상자 안에 인쇄하는 글자 (분석기 blocks.isa_word 가 그대로 읽는다)
#   bar   : 왼쪽 입력 막대 (여러 입력이 붙는 자리)
#   cells : 2 = 위·아래 두 칸 (메모리 S/R)
#   w · h : 기본 크기 (pt)
SYMBOLS = {
    "AND":    {"name": "AND",            "text": "AND",  "bar": True,  "w": 16, "h": 9,  "logic": "and"},
    "OR":     {"name": "OR",             "text": "OR",   "bar": True,  "w": 16, "h": 9,  "logic": "or"},
    "NAND":   {"name": "NAND",           "text": "NAND", "bar": True,  "w": 18, "h": 9,  "logic": "nand"},
    "NOR":    {"name": "NOR",            "text": "NOR",  "bar": True,  "w": 16, "h": 9,  "logic": "nor"},
    "NOT":    {"name": "NOT",            "text": "NOT",  "bar": False, "w": 16, "h": 9,  "logic": "not"},
    "GT":     {"name": "켜짐 지연 (GT)",  "text": "GT",   "bar": False, "w": 16, "h": 9,  "logic": "delay_on",  "time": True},
    "DT":     {"name": "꺼짐 지연 (DT)",  "text": "DT",   "bar": False, "w": 16, "h": 9,  "logic": "delay_off", "time": True},
    "PD":     {"name": "펄스 (PD)",       "text": "PD",   "bar": False, "w": 16, "h": 9,  "logic": "pulse",     "time": True},
    "VOTE":   {"name": "투표 A/B",        "text": "2/3",  "bar": True,  "w": 16, "h": 9,  "logic": "vote",      "ab": True},
    "MEMORY": {"name": "메모리 S-R",      "text": "S|R",  "bar": False, "w": 12, "h": 22, "logic": "memory",    "cells": 2},
    "PB":     {"name": "누름단추 PB",     "text": "PB",   "bar": False, "w": 14, "h": 9,  "logic": "source",    "label": True},
    "ANN":    {"name": "경보 ANN",        "text": "ANN",  "bar": False, "w": 18, "h": 9,  "logic": "sink"},
    "SOE":    {"name": "기록 SOE",        "text": "SOE",  "bar": False, "w": 18, "h": 9,  "logic": "sink"},
    "CONN":   {"name": "연결 기호 (원)",   "text": "A",    "bar": False, "w": 8,  "h": 8,  "logic": "connector", "circle": True},
    "TEXT":   {"name": "글 (주석)",       "text": "NOTE", "bar": False, "w": 40, "h": 8,  "logic": "",          "note": True},
}
BAR_EXTRA = 2.0 * PITCH          # 입력 막대 = 상자 높이 + 위아래 한 행씩 (상자보다 길어야 막대로 읽힌다 — graph._bar_gate)


def ry(n: int, N: int) -> float:
    """행 n (1..2N) 의 가운데 y — 오른쪽 표 행 N+k 는 왼쁜 k 와 같은 높이."""
    return TOP + ((n - 1) % N) * PITCH + PITCH / 2


def layout(N: int) -> dict:
    """화면이 표를 그릴 때 쓰는 수 — 서버와 같은 자."""
    N = max(N_MIN, min(N_MAX, int(N or N_DEFAULT)))
    return {"W": W, "H": H, "TOP": TOP, "PITCH": PITCH, "N": N, "LCOLS": LCOLS, "RCOLS": RCOLS,
            "LX0": LX0, "LX1": LX1, "bottom": TOP + N * PITCH, "bar_extra": BAR_EXTRA,
            "title": {"doc": [900.0, 805.0], "caption": [1100.0, 790.0], "sheet": [1098.0, 800.0], "name": [600.0, 805.0]}}


# ─────────────────────────── 문서 ───────────────────────────

def new_doc(name: str, author: str, project: str = "", N: int = N_DEFAULT) -> dict:
    N = max(N_MIN, min(N_MAX, int(N or N_DEFAULT)))
    now = time.time()
    return {
        "id": uuid.uuid4().hex[:12], "name": (name or "새 로직").strip()[:80], "project": (project or "").strip()[:80],
        "sheet_no": "", "title": "", "doc_no": "", "N": N,
        "left": {}, "right": {},            # 행 번호(str) → {"fm","kks","desc"} / {"desc","kks","to"}
        "blocks": [], "wires": [],
        "author": author, "created": now, "updated": now, "saves": 0, "history": [],
    }


def _num(v, lo=None, hi=None, default=0.0):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    if f != f or f in (float("inf"), float("-inf")):
        return default
    if lo is not None:
        f = max(lo, f)
    if hi is not None:
        f = min(hi, f)
    return round(f, 2)


def _txt(v, n=MAX_TEXT):
    return str(v if v is not None else "").replace("\n", " ").strip()[:n]


def clean(doc: dict) -> dict:
    """화면이 보낸 그림을 믿지 않고 모양을 맞춘다 (api_fuzz 규율) — 모르는 종류 · 밖으로 나간 좌표 · 긴 글."""
    N = max(N_MIN, min(N_MAX, int(_num(doc.get("N"), 1, 999, N_DEFAULT))))
    out = {"N": N, "sheet_no": _txt(doc.get("sheet_no"), 40), "title": _txt(doc.get("title"), 120),
           "doc_no": _txt(doc.get("doc_no"), 60), "left": {}, "right": {}, "blocks": [], "wires": []}
    for side, keys in (("left", ("fm", "kks", "desc")), ("right", ("desc", "kks", "to"))):
        rows = doc.get(side) if isinstance(doc.get(side), dict) else {}
        for k, v in rows.items():
            try:
                n = int(k)
            except (TypeError, ValueError):
                continue
            lo, hi = (1, N) if side == "left" else (N + 1, 2 * N)
            if not (lo <= n <= hi) or not isinstance(v, dict):
                continue
            cell = {kk: _txt(v.get(kk), 60) for kk in keys}
            if any(cell.values()):
                out[side][str(n)] = cell
    seen = set()
    for b in doc.get("blocks") if isinstance(doc.get("blocks"), list) else []:
        if not isinstance(b, dict) or b.get("kind") not in SYMBOLS:
            continue
        bid = _txt(b.get("id"), 16) or uuid.uuid4().hex[:6]
        if bid in seen:
            bid = uuid.uuid4().hex[:6]
        seen.add(bid)
        spec = SYMBOLS[b["kind"]]
        nb = {"id": bid, "kind": b["kind"],
              "x": _num(b.get("x"), 0, W), "y": _num(b.get("y"), 0, H),
              "w": _num(b.get("w"), 4, 400, spec["w"]), "h": _num(b.get("h"), 4, 300, spec["h"]),
              "text": _txt(b.get("text"), 40) or spec["text"], "label": _txt(b.get("label"), 60)}
        p = b.get("param") if isinstance(b.get("param"), dict) else {}
        param = {}
        if spec.get("time"):
            param["t"] = _num(p.get("t"), 0, 36000, 5)
        if spec.get("ab"):
            param["a"] = int(_num(p.get("a"), 1, 9, 2))
            param["b"] = int(_num(p.get("b"), 1, 9, 3))
            nb["text"] = f"{param['a']}/{param['b']}"
        if spec.get("cells") == 2:
            dom = str(p.get("dominant") or "")
            param["dominant"] = dom if dom in ("set", "reset") else ""
        nb["param"] = param
        out["blocks"].append(nb)
    for w in doc.get("wires") if isinstance(doc.get("wires"), list) else []:
        if not isinstance(w, dict) or not isinstance(w.get("pts"), list):
            continue
        pts = []
        for p in w["pts"]:
            if isinstance(p, (list, tuple)) and len(p) == 2:
                pts.append([_num(p[0], 0, W), _num(p[1], 0, H)])
        pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
        if len(pts) >= 2:
            out["wires"].append({"id": _txt(w.get("id"), 16) or uuid.uuid4().hex[:6], "pts": pts,
                                 "dashed": bool(w.get("dashed"))})
    return out


# ─────────────────────────── 저장 ───────────────────────────

def root() -> Path:
    p = store.root() / "drawings"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _dir(did: str) -> Path:
    if not ID_RE.match(did or ""):
        raise KeyError(did)
    return root() / did


def _path(did: str) -> Path:
    return _dir(did) / "drawing.json"


def load(did: str) -> dict:
    p = _path(did)
    if not p.exists():
        raise KeyError(did)
    return jsonstore.read(p, what="LOGIC 작도", expect=dict)


def save_new(doc: dict) -> dict:
    d = _dir(doc["id"])
    d.mkdir(parents=True, exist_ok=True)
    jsonstore.write(_path(doc["id"]), doc)
    return doc


@jsonstore.serialized
def save(did: str, body: dict, author: str) -> dict:
    """그림을 덮어쓴다 — 앞 판의 요약은 history 에 남는다 (지우지 않는다 · P&ID 메모 규율)."""
    author = _txt(author, 60)
    if not author:
        raise ValueError("작성자가 필요합니다.")
    cur = load(did)
    nd = clean(body)
    cur["history"] = (cur.get("history") or [])[-199:] + [{
        "author": cur.get("author", ""), "time": cur.get("updated"), "saves": cur.get("saves", 0),
        "blocks": len(cur.get("blocks") or []), "wires": len(cur.get("wires") or [])}]
    cur.update(nd)
    if "name" in body:
        cur["name"] = _txt(body.get("name"), 80) or cur["name"]
    if "project" in body:
        cur["project"] = _txt(body.get("project"), 80)
    cur["author"] = author
    cur["updated"] = time.time()
    cur["saves"] = int(cur.get("saves") or 0) + 1
    jsonstore.write(_path(did), cur)
    return cur


def delete(did: str, author: str) -> dict:
    import shutil
    cur = load(did)
    d = _dir(did)
    log = store.root() / "deletion_log.json"
    items = jsonstore.read(log, {"items": []}, expect=dict).get("items") or []
    items.append({"kind": "drawing", "id": did, "name": cur.get("name"), "project": cur.get("project"),
                  "author": _txt(author, 60), "time": time.time(), "blocks": len(cur.get("blocks") or [])})
    jsonstore.write(log, {"items": items[-5000:]})
    shutil.rmtree(d, ignore_errors=True)
    return cur


def listing() -> list:
    out = []
    for d in sorted(root().iterdir()):
        p = d / "drawing.json"
        if not d.is_dir() or not p.exists():
            continue
        doc = jsonstore.read(p, None, expect=dict)
        if not doc:
            continue
        out.append({k: doc.get(k) for k in ("id", "name", "project", "sheet_no", "title", "author", "created", "updated", "saves")}
                   | {"blocks": len(doc.get("blocks") or []), "wires": len(doc.get("wires") or []),
                      "rows": len(doc.get("left") or {}) + len(doc.get("right") or {})})
    out.sort(key=lambda x: -(x.get("updated") or 0))
    return out


# ─────────────────────────── 기호 기하 (화면과 같은 규칙) ───────────────────────────

def block_geometry(b: dict) -> dict:
    """상자 · 막대 · 칸 · 글자 자리 — 화면의 logic_draw.js `geom()` 과 같은 수를 내야 한다."""
    spec = SYMBOLS[b["kind"]]
    x, y, w, h = b["x"], b["y"], b["w"], b["h"]
    g = {"box": [x, y, x + w, y + h], "cells": [], "bar": None, "circle": None, "pointer": None, "texts": []}
    if spec.get("circle"):
        r = min(w, h) / 2
        cx, cy = x + w / 2, y + h / 2
        g["circle"] = [cx, cy, r]
        # 꼭지 삼각형 — 밑변이 원 위의 현 · 꼭지가 오른쪽 바깥 (분석기 graph.build 가 이것으로 연결 기호를 알아본다)
        a = 0.6
        g["pointer"] = [[cx + r * math.cos(a), cy - r * math.sin(a)], [cx + r * math.cos(a), cy + r * math.sin(a)], [cx + r * 2.2, cy]]
        g["texts"].append([cx, cy, b["text"], min(h * 0.7, 7)])
        return g
    if spec.get("bar"):
        L = h + BAR_EXTRA
        cy = y + h / 2
        g["bar"] = [x, cy - L / 2, x, cy + L / 2]
    if spec.get("cells") == 2:
        g["cells"] = [[x, y, x + w, y + h / 2], [x, y + h / 2, x + w, y + h]]
        s, r = ("SO", "R") if b["param"].get("dominant") == "set" else (("S", "RO") if b["param"].get("dominant") == "reset" else ("S", "R"))
        g["texts"].append([x + w / 2, y + h / 4, s, min(h / 2 * 0.7, 7)])
        g["texts"].append([x + w / 2, y + 3 * h / 4, r, min(h / 2 * 0.7, 7)])
        return g
    if spec.get("note"):
        g["box"] = None
        g["texts"].append([x + w / 2, y + h / 2, b["text"], min(h * 0.8, 8)])
        return g
    g["texts"].append([x + w / 2, y + h / 2, b["text"], min(h * 0.6, 7)])
    if spec.get("time"):
        g["texts"].append([x + w / 2, y + h + 6, f"{b['param'].get('t', 5):g} sec", 5])
    if spec.get("label") and b.get("label"):
        g["texts"].append([x + w / 2, y + h + 6, b["label"], 5])
    return g


def ports_of(b: dict) -> list:
    """붙일 자리 — 화면의 자석.  [x, y, dir, role]"""
    spec = SYMBOLS[b["kind"]]
    x, y, w, h = b["x"], b["y"], b["w"], b["h"]
    if spec.get("circle"):
        r = min(w, h) / 2
        return [[x + w / 2 - r, y + h / 2, "in", ""], [x + w / 2 + r * 2.2, y + h / 2, "out", ""]]
    if spec.get("cells") == 2:
        return [[x, y + h / 4, "in", "set"], [x, y + 3 * h / 4, "in", "reset"],
                [x + w, y + h / 4, "out", "q"], [x + w, y + 3 * h / 4, "out", "qn"]]
    if spec.get("note"):
        return []
    out = [[x + w, y + h / 2, "out", ""]]
    if spec.get("logic") == "source":
        return out
    if spec.get("bar"):
        L = h + BAR_EXTRA
        cy = y + h / 2
        k = int(L // PITCH)
        ys = [cy + (i - (k - 1) / 2) * PITCH for i in range(k)]
        return [[x, yy, "in", ""] for yy in ys] + out
    return [[x, y + h / 2, "in", ""]] + out


# ─────────────────────────── PDF ───────────────────────────

def _line(page, pts, dashes=None):
    sh = page.new_shape()
    for a, b in zip(pts, pts[1:]):
        sh.draw_line(pymupdf.Point(*a), pymupdf.Point(*b))
    sh.finish(color=K, width=LW, closePath=False, dashes=dashes)
    sh.commit()


def _rect(page, r):
    sh = page.new_shape()
    sh.draw_rect(pymupdf.Rect(*r))
    sh.finish(color=K, width=LW)
    sh.commit()


def _ctext(page, cx, cy, text, fs):
    """가운데 맞춘 글자 (helv)."""
    text = str(text)
    tw = pymupdf.get_text_length(text, fontname="helv", fontsize=fs)
    page.insert_text((cx - tw / 2, cy + fs * 0.35), text, fontsize=fs, fontname="helv")


def _table(page, doc):
    N = doc["N"]
    bottom = TOP + N * PITCH
    for x in LCOLS + RCOLS:
        _line(page, [(x, TOP - 2 * PITCH), (x, bottom)])
    for k in range(N + 1):
        _line(page, [(LCOLS[0], TOP + k * PITCH), (LX0, TOP + k * PITCH)])
        _line(page, [(LX1, TOP + k * PITCH), (RCOLS[-1], TOP + k * PITCH)])
    _line(page, [(LCOLS[0], TOP - 2 * PITCH), (LX0, TOP - 2 * PITCH)])
    _line(page, [(LX1, TOP - 2 * PITCH), (RCOLS[-1], TOP - 2 * PITCH)])
    heads = [((LCOLS[0] + LCOLS[1]) / 2, "FROM"), ((LCOLS[1] + LCOLS[2]) / 2, "NO."), ((LCOLS[2] + LCOLS[3]) / 2, "TAG NO."),
             ((LCOLS[3] + LCOLS[4]) / 2, "SERVICE"),
             ((RCOLS[0] + RCOLS[1]) / 2, "SERVICE"), ((RCOLS[1] + RCOLS[2]) / 2, "TAG NO."), ((RCOLS[2] + RCOLS[3]) / 2, "NO."),
             ((RCOLS[3] + RCOLS[4]) / 2, "TO")]
    for x, t in heads:
        _ctext(page, x, TOP - PITCH, t, 6)
    for k in range(N):
        _ctext(page, (LCOLS[1] + LCOLS[2]) / 2, TOP + k * PITCH + PITCH / 2, str(k + 1), 5)
        _ctext(page, (RCOLS[2] + RCOLS[3]) / 2, TOP + k * PITCH + PITCH / 2, str(N + k + 1), 5)
    for k, v in doc["left"].items():
        yy = ry(int(k), N) + 1.8
        page.insert_text((LCOLS[0] + 2, yy), v.get("fm", ""), fontsize=5, fontname="helv")
        page.insert_text((LCOLS[2] + 2, yy), v.get("kks", ""), fontsize=5, fontname="helv")
        page.insert_text((LCOLS[3] + 2, yy), v.get("desc", ""), fontsize=5, fontname="helv")
    for k, v in doc["right"].items():
        yy = ry(int(k), N) + 1.8
        page.insert_text((RCOLS[0] + 2, yy), v.get("desc", ""), fontsize=5, fontname="helv")
        page.insert_text((RCOLS[1] + 2, yy), v.get("kks", ""), fontsize=5, fontname="helv")
        page.insert_text((RCOLS[3] + 2, yy), v.get("to", ""), fontsize=5, fontname="helv")
    # 타이틀블록 — 문서 번호 · 제목 · 캡션 SHEET NO. 아래 시트 이름 (분석기는 캡션 아래 칸에서 시트 이름을 읽는다)
    lay = layout(N)["title"]
    _rect(page, (560, 780, 1170, 830))
    _line(page, [(1060, 780), (1060, 830)])
    _line(page, [(560, 795), (1170, 795)])
    # 제목은 문서 번호 **위** 같은 칸에 · 오른쪽 반(x > W/2)에 — 분석기(glyphs._title_lines)가 도면번호(숫자-숫자 꼴) 위 글줄을 제목으로 읽는다 (19VA 양식)
    page.insert_text((620, 808), doc.get("title") or "", fontsize=8, fontname="helv")
    page.insert_text((620, 824), doc.get("doc_no") or "", fontsize=7, fontname="helv")
    page.insert_text((lay["caption"][0] - 30, lay["caption"][1] + 2), "SHEET NO.", fontsize=5, fontname="helv")
    page.insert_text((lay["sheet"][0] - 30, lay["sheet"][1] + 15), doc.get("sheet_no") or "", fontsize=9, fontname="helv")


def _blocks(page, doc):
    for b in doc["blocks"]:
        g = block_geometry(b)
        if g["circle"]:
            sh = page.new_shape()
            sh.draw_circle(pymupdf.Point(g["circle"][0], g["circle"][1]), g["circle"][2])
            sh.finish(color=K, width=LW)
            sh.commit()
            sh = page.new_shape()
            sh.draw_polyline([pymupdf.Point(*p) for p in g["pointer"]])
            sh.finish(color=K, fill=K, width=LW, closePath=True)
            sh.commit()
        elif g["cells"]:
            for c in g["cells"]:
                _rect(page, c)
        elif g["box"]:
            _rect(page, g["box"])
        if g["bar"]:
            _line(page, [(g["bar"][0], g["bar"][1]), (g["bar"][2], g["bar"][3])])
        for cx, cy, t, fs in g["texts"]:
            if t:
                _ctext(page, cx, cy, t, fs)


def to_pdf(doc: dict) -> bytes:
    doc = {**doc, **clean(doc)}
    pdf = pymupdf.open()
    page = pdf.new_page(width=W, height=H)
    _table(page, doc)
    _blocks(page, doc)
    for w in doc["wires"]:
        _line(page, [tuple(p) for p in w["pts"]], dashes="[3 3] 0" if w.get("dashed") else None)
    pdf.set_metadata({"title": doc.get("title") or doc.get("name") or "LOGIC", "producer": "PID LOGIC 작도"})
    return pdf.tobytes()


# ─────────────────────────── DXF ───────────────────────────

def to_dxf(doc: dict) -> bytes:
    """같은 그림을 DXF 로 (ezdxf · 모델 공간 · y 는 위로 — PDF y 를 뒤집는다 · 1 단위 = 1 pt).
    층: TABLE · TEXT · LOGIC · SYMBOL · WIRE · DASHED · TITLE."""
    import ezdxf

    doc = {**doc, **clean(doc)}
    N = doc["N"]
    dwg = ezdxf.new("R2010")
    for name, color in (("TABLE", 7), ("TEXT", 7), ("SYMBOL", 7), ("WIRE", 7), ("DASHED", 7), ("TITLE", 7)):
        dwg.layers.add(name, color=color)
    if "DASHED" not in dwg.linetypes:
        dwg.linetypes.add("DASHED", pattern=[6.0, 3.0, -3.0])
    dwg.layers.get("DASHED").dxf.linetype = "DASHED"
    msp = dwg.modelspace()

    def P(x, y):
        return (x, H - y)

    def line(a, b, layer="WIRE", dashed=False):
        e = msp.add_line(P(*a), P(*b), dxfattribs={"layer": layer})
        if dashed:
            e.dxf.linetype = "DASHED"

    def rect(r, layer="SYMBOL"):
        x0, y0, x1, y1 = r
        msp.add_lwpolyline([P(x0, y0), P(x1, y0), P(x1, y1), P(x0, y1)], close=True, dxfattribs={"layer": layer})

    def text(x, y, t, h, layer="TEXT", align="LEFT"):
        if not t:
            return
        e = msp.add_text(str(t), dxfattribs={"layer": layer, "height": h})
        e.set_placement(P(x, y), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER if align == "CENTER"
                        else ezdxf.enums.TextEntityAlignment.LEFT)

    bottom = TOP + N * PITCH
    for x in LCOLS + RCOLS:
        line((x, TOP - 2 * PITCH), (x, bottom), "TABLE")
    for k in range(N + 1):
        line((LCOLS[0], TOP + k * PITCH), (LX0, TOP + k * PITCH), "TABLE")
        line((LX1, TOP + k * PITCH), (RCOLS[-1], TOP + k * PITCH), "TABLE")
    line((LCOLS[0], TOP - 2 * PITCH), (LX0, TOP - 2 * PITCH), "TABLE")
    line((LX1, TOP - 2 * PITCH), (RCOLS[-1], TOP - 2 * PITCH), "TABLE")
    for x, t in (((LCOLS[0] + LCOLS[1]) / 2, "FROM"), ((LCOLS[1] + LCOLS[2]) / 2, "NO."), ((LCOLS[2] + LCOLS[3]) / 2, "TAG NO."),
                 ((LCOLS[3] + LCOLS[4]) / 2, "SERVICE"), ((RCOLS[0] + RCOLS[1]) / 2, "SERVICE"),
                 ((RCOLS[1] + RCOLS[2]) / 2, "TAG NO."), ((RCOLS[2] + RCOLS[3]) / 2, "NO."), ((RCOLS[3] + RCOLS[4]) / 2, "TO")):
        text(x, TOP - PITCH, t, 5, "TEXT", "CENTER")
    for k in range(N):
        text((LCOLS[1] + LCOLS[2]) / 2, TOP + k * PITCH + PITCH / 2, str(k + 1), 4, "TEXT", "CENTER")
        text((RCOLS[2] + RCOLS[3]) / 2, TOP + k * PITCH + PITCH / 2, str(N + k + 1), 4, "TEXT", "CENTER")
    for k, v in doc["left"].items():
        yy = ry(int(k), N)
        text(LCOLS[0] + 2, yy, v.get("fm"), 4)
        text(LCOLS[2] + 2, yy, v.get("kks"), 4)
        text(LCOLS[3] + 2, yy, v.get("desc"), 4)
    for k, v in doc["right"].items():
        yy = ry(int(k), N)
        text(RCOLS[0] + 2, yy, v.get("desc"), 4)
        text(RCOLS[1] + 2, yy, v.get("kks"), 4)
        text(RCOLS[3] + 2, yy, v.get("to"), 4)
    rect((560, 780, 1170, 830), "TITLE")
    line((1060, 780), (1060, 830), "TITLE")
    line((560, 795), (1170, 795), "TITLE")
    text(620, 806, doc.get("title"), 7, "TITLE")
    text(620, 822, doc.get("doc_no"), 6, "TITLE")
    text(1070, 790, "SHEET NO.", 4, "TITLE")
    text(1070, 815, doc.get("sheet_no"), 8, "TITLE")
    for b in doc["blocks"]:
        g = block_geometry(b)
        if g["circle"]:
            cx, cy, r = g["circle"]
            msp.add_circle(P(cx, cy), r, dxfattribs={"layer": "SYMBOL"})
            hs = msp.add_solid([P(*p) for p in g["pointer"]], dxfattribs={"layer": "SYMBOL"})
        elif g["cells"]:
            for c in g["cells"]:
                rect(c)
        elif g["box"]:
            rect(g["box"])
        if g["bar"]:
            line((g["bar"][0], g["bar"][1]), (g["bar"][2], g["bar"][3]), "SYMBOL")
        for cx, cy, t, fs in g["texts"]:
            text(cx, cy, t, fs * 0.75, "TEXT", "CENTER")
    for w in doc["wires"]:
        pts = [P(*p) for p in w["pts"]]
        e = msp.add_lwpolyline(pts, dxfattribs={"layer": "DASHED" if w.get("dashed") else "WIRE"})
        if w.get("dashed"):
            e.dxf.linetype = "DASHED"
    buf = io.StringIO()
    dwg.write(buf)
    return buf.getvalue().encode("utf-8")


# ─────────────────────────── 되읽기 (검증) ───────────────────────────

def verify(doc: dict) -> dict:
    """그린 것을 PDF 로 내보내 **분석기에 다시 넣어** 같은 블록 · 선 · 행이 나오는지 센다.
    분석기(analyse.analyse)를 그대로 부른다 — 사본 규칙 없음.  판정은 그 결과의 수를 세는 것뿐이다."""
    from . import analyse as AN
    doc = {**doc, **clean(doc)}
    pdf = to_pdf(doc)
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "draw.pdf"
        p.write_bytes(pdf)
        try:
            res = AN.analyse(str(p))
        except AN.NotLogic as e:
            return {"ok": False, "why": str(e), "blocks": [], "rows": {"drawn": 0, "read": 0}, "nets": 0}
    s = res["sheets"][0]
    drawn = [b for b in doc["blocks"] if not SYMBOLS[b["kind"]].get("note")]
    read = [{**v, "id": k} for k, v in s["blocks"].items()]
    used = set()
    items = []
    for b in drawn:
        g = block_geometry(b)
        box = g["box"] or [g["circle"][0] - g["circle"][2], g["circle"][1] - g["circle"][2],
                           g["circle"][0] + g["circle"][2], g["circle"][1] + g["circle"][2]]
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        hit = None
        for i, rb in enumerate(read):
            if i in used:
                continue
            bb = rb["bbox"]
            if bb[0] - 2 <= cx <= bb[2] + 2 and bb[1] - 2 <= cy <= bb[3] + 2:
                hit = (i, rb)
                break
        want = SYMBOLS[b["kind"]]["logic"]
        if hit:
            used.add(hit[0])
            got = hit[1].get("logic") or ""
            if b["kind"] == "CONN":
                ok = hit[1].get("kind") == "CONNECTOR" or got == "connector"
            else:
                ok = got == want
            ports = [p for p in s["ports"] if p["block"] == hit[1]["id"]]
            items.append({"id": b["id"], "kind": b["kind"], "ok": ok, "read": hit[1].get("func", ""), "logic": got,
                          "inputs": sum(1 for p in ports if p["dir"] == "in"), "outputs": sum(1 for p in ports if p["dir"] == "out")})
        else:
            items.append({"id": b["id"], "kind": b["kind"], "ok": False, "read": "", "logic": "", "inputs": 0, "outputs": 0,
                          "why": "분석기가 이 자리에서 블록을 읽지 못했습니다"})
    extra = [rb for i, rb in enumerate(read) if i not in used]
    tab = {(r["side"], r["n"]): r for r in s.get("table") or []}
    rows_ok, rows_bad = 0, []
    for side, key, col in (("left", "L", "fm"), ("right", "R", "to")):
        for k, v in doc[side].items():
            r = tab.get((key, int(k)))
            want = (v.get(col) or "").strip().upper()
            got = ((r or {}).get(col) or "").strip().upper()
            desc_ok = (v.get("desc") or "").strip().upper() == ((r or {}).get("desc") or "").strip().upper()
            if r is not None and want == got and desc_ok:
                rows_ok += 1
            else:
                rows_bad.append({"side": key, "n": int(k), "want": want, "read": got, "desc_ok": desc_ok})
    nrows_drawn = len(doc["left"]) + len(doc["right"])
    wired_rows = {(r["side"], r["n"]) for r in s.get("rows") or []}
    return {
        "ok": all(i["ok"] for i in items) and not rows_bad and not extra and s.get("sheet_no", "") == doc.get("sheet_no", ""),
        "sheet_no": {"drawn": doc.get("sheet_no", ""), "read": s.get("sheet_no", "")},
        "blocks": items, "extra_blocks": [{"id": e["id"], "func": e.get("func"), "bbox": e["bbox"]} for e in extra],
        "rows": {"drawn": nrows_drawn, "read": rows_ok, "bad": rows_bad, "wired": len(wired_rows)},
        "nets": len(s.get("nets") or {}), "dangling": len(s.get("dangling") or []),
        "findings": s.get("findings") or [], "seconds": res.get("seconds"),
    }


# ─────────────────────────── 분석 결과 → 그림 ───────────────────────────

_FUNC_KIND = {"AND": "AND", "OR": "OR", "NAND": "NAND", "NOR": "NOR", "NOT": "NOT", "GT": "GT", "DT": "DT", "PD": "PD",
              "VOTE": "VOTE", "MEMORY": "MEMORY", "PB": "PB", "ANN": "ANN", "SOE": "SOE"}
_LOGIC_KIND = {"and": "AND", "or": "OR", "nand": "NAND", "nor": "NOR", "not": "NOT", "delay_on": "GT", "delay_off": "DT",
               "pulse": "PD", "vote": "VOTE", "memory": "MEMORY", "source": "PB", "sink": "ANN", "connector": "CONN"}


def from_sheet(s: dict, name: str, author: str, project: str = "") -> dict:
    """분석한 시트 하나를 이 양식의 그림으로 — 행 글은 그대로 · 블록은 종류와 자리 · 선은 그물의 선분.
    x 는 LOGIC 영역을 비례로, y 는 행 간격으로 옮긴다 (행 n 이 이 양식의 행 n 에 선다)."""
    rows = s.get("rows") or []
    table = s.get("table") or []
    nmax = max([r["n"] for r in table if r.get("n")] + [r["n"] for r in rows if r.get("n")] + [0])
    N = max(N_MIN, min(N_MAX, (nmax + 1) // 2 if nmax else N_DEFAULT))
    doc = new_doc(name, author, project, N)
    doc["sheet_no"] = s.get("sheet_no") or ""
    doc["title"] = s.get("title") or ""
    for r in table:
        n = r.get("n")
        if not n:
            continue
        if r["side"] == "L" and 1 <= n <= N:
            doc["left"][str(n)] = {"fm": _txt(r.get("fm"), 60), "kks": _txt(r.get("kks"), 60), "desc": _txt(r.get("desc"), 60)}
        elif r["side"] == "R" and N < n <= 2 * N:
            doc["right"][str(n)] = {"desc": _txt(r.get("desc"), 60), "kks": _txt(r.get("kks"), 60), "to": _txt(r.get("to"), 60)}
    lg = s.get("logic") or [LX0, TOP, LX1, TOP + N * PITCH]
    pitch = s.get("pitch") or PITCH
    r1 = next((r for r in rows if r["side"] == "L" and r["n"] == 1), None)
    y1 = r1["at"][1] if r1 else (min((r["at"][1] for r in rows), default=lg[1]) if rows else lg[1])
    sx = (LX1 - LX0) / max(1.0, lg[2] - lg[0])

    def X(x):
        return round(LX0 + (x - lg[0]) * sx, 2)

    def Y(y):
        return round(TOP + PITCH / 2 + (y - y1) / pitch * PITCH, 2)

    for bid, b in (s.get("blocks") or {}).items():
        kind = _FUNC_KIND.get(b.get("func") or "") or _LOGIC_KIND.get(b.get("logic") or "")
        if not kind:
            kind = "TEXT"
        x0, y0, x1, y1b = b["bbox"]
        nb = {"id": bid, "kind": kind, "x": X(x0), "y": Y(y0), "w": max(4, round((x1 - x0) * sx, 2)),
              "h": max(4, round((y1b - y0) / pitch * PITCH, 2)), "text": SYMBOLS[kind]["text"], "label": "", "param": {}}
        p = b.get("param") or {}
        if kind == "TEXT":
            nb["text"] = _txt(b.get("read") or b.get("func") or "?", 40)
        if kind in ("GT", "DT", "PD"):
            nb["param"]["t"] = _num(p.get("t_user", p.get("t")), 0, 36000, 5)
        if kind == "VOTE":
            nb["param"] = {"a": int(_num(p.get("a"), 1, 9, 2)), "b": int(_num(p.get("b"), 1, 9, 3))}
            nb["text"] = f"{nb['param']['a']}/{nb['param']['b']}"
        if kind == "MEMORY":
            nb["param"]["dominant"] = p.get("dominant") or ""
        if kind == "PB":
            nb["label"] = _txt((b.get("label") or "").replace("PB", "", 1), 60)
        if kind == "CONN":
            nb["text"] = _txt((b.get("label") or b.get("read") or "A")[:1] or "A", 2)
        doc["blocks"].append(nb)
    for nid, n in (s.get("nets") or {}).items():
        for sg in n.get("segs") or []:
            a, b = (sg[0], sg[1]), (sg[2], sg[3])
            doc["wires"].append({"id": f"n{nid}_{len(doc['wires'])}", "pts": [[X(a[0]), Y(a[1])], [X(b[0]), Y(b[1])]],
                                 "dashed": bool(n.get("dashed"))})
    doc.update(clean(doc))
    return doc
