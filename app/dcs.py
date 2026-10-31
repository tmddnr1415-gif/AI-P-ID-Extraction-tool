"""간략화 DCS 그래픽 — 식별이 끝난 **실행(태그 있는) P&ID** 를 HMI 화면 꼴로 (hotfix107).

무엇을 그리나 — 분석이 이미 **저장해 둔 것만** 옮겨 그린다 (판정 0 · 엔진 import 0 · PDF 를 다시 열지 않는다):

  · 계기  = FIELD 행.  자리는 버블 사각형, 이름은 그 행의 **태그 번호**(`values.tag_no` · 1급 태그),
            글자(TYPE) · 공급 주체 · 라인 번호 · 버블 가운데 선(ISA 위치 표기)까지.
  · 밸브  = MOV · PNEUMATIC … 행.  몸체 · 액추에이터 · 태그(태그 버블 자리).
  · 배관  = 판정축이 그 계기가 **탭한 런**(`evidence.axis.ev.run` · trunk · mid_runs)과 라인 번호 깃발이 선 런.
            전체 배관망이 아니라 **식별된 계기 · 밸브가 걸린 선**만 — 그래서 '간략화' 다.
  · 기기  = 판정 후보에 든 기기 라벨(`candidates[kind=EQUIPMENT]` — 도면이 인쇄한 이름 · 자리).
  · 커넥터 = 런 끝에서 읽은 `TO …` / `FROM …` (오프페이지).

좌표는 **그 장의 PDF 좌표 그대로** — 자리를 지어내지 않는다 (§9).  그래서 P&ID 와 같은 배치로 읽힌다.

왜 실행 P&ID 만인가 — 그래픽의 열쇠가 태그 번호다.  LOGIC 검토가 읽는 태그(`app/logic`)와 같은 글자이므로
나중에 로직 시뮬레이션 결과(태그 → 0/1 · 값)를 `paint()` 로 이 그림 위에 칠할 수 있다.  태그가 없는
입찰 P&ID 는 요소를 가리킬 이름이 없어 만들지 않고 그렇게 말한다.

SVG 는 서버가 글로 만든다(브라우저 없이 PNG 로도 — PyMuPDF 가 SVG 를 연다).  요소마다 `data-tag` 가 붙어
화면(`/dcs`)과 로직 쪽이 같은 이름으로 찾는다.
"""
from __future__ import annotations

import io
import json
import math
import re
import time
import zipfile
from html import escape
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from app import page_stamp, paths

router = APIRouter()

VALVE_TABS = ("MOV", "PNEUMATIC", "BFV", "REVIEW")
# 색 — 첨부(Yokogawa · PCS7)의 결: 어두운 판 · 노란 배관 · 검은 바탕 초록 숫자 칸
C = {"bg": "#2b3038", "grid": "#343a44", "pipe": "#d7c24a", "pipe_lbl": "#e8dc8a", "equip": "#5d6670",
     "equip_line": "#c9d1da", "equip_txt": "#f2f5f8", "face": "#101418", "face_line": "#8a97a8",
     "val": "#39e07a", "val_dim": "#6b7785", "tag": "#dfe6ee", "type": "#9fb2c8", "on": "#39e07a",
     "off": "#c8d0d8", "alarm": "#ff4d4d", "closed": "#ff5a5a", "open": "#39e07a", "act": "#9ad0ff",
     "conn": "#e6edf5", "conn_fill": "#3f4753", "vendor": "#f0b429", "title": "#f2f5f8", "sub": "#9fb2c8"}
FACE_W, FACE_H = 74.0, 26.0           # 계기 칸 (pt · 도면 좌표) — A1 도면의 버블(≈23pt)보다 조금 크다
VALVE_R = 9.0                         # 밸브 나비 반폭


# ---------------------------------------------------------------- 모델 (저장된 행 → 그릴 것)

def _run_seg(run) -> tuple | None:
    """`["H", coord, lo, hi]` → (x0, y0, x1, y1)."""
    if not run or len(run) != 4:
        return None
    ax, c, lo, hi = run
    try:
        c, lo, hi = float(c), float(lo), float(hi)
    except (TypeError, ValueError):
        return None
    return (lo, c, hi, c) if ax == "H" else (c, lo, c, hi)


def _rect(r):
    try:
        x0, y0, x1, y1 = [float(v) for v in r]
    except (TypeError, ValueError):
        return None
    return [round(min(x0, x1), 1), round(min(y0, y1), 1), round(max(x0, x1), 1), round(max(y0, y1), 1)]


def _alive(row: dict) -> bool:
    return not row.get("deleted") and not row.get("removed")


def build_sheet(page: dict, rows: list, equipment_labels: list | None = None) -> dict:
    """한 장의 그래픽 모델.  `page` 는 pid_page 한 줄(dict · width/height/drawing_no/title) · `rows` 는 그 장의 행 전부.
    hotfix111 — `equipment_labels` 는 분석이 그 장에서 찾은 **기기 이름 전부**(`engine_json["equipment_labels"]`) —
    설명 후보는 계기 가까이의 기기만 들고 있어 계기와 무관한 기기는 그려지지 않았다.  옛 분석(없음)은 후보만으로."""
    inst, valves, pipes, equips, conns, labels = [], [], {}, {}, {}, {}
    for e in equipment_labels or []:
        er = _rect(e.get("rect"))
        if er and e.get("name"):
            equips[(e["name"], tuple(er))] = {"name": e["name"], "rect": er, "noun": e.get("noun") or ""}
    for r in rows:
        if not _alive(r):
            continue
        v = r.get("values") or {}
        ev = r.get("evidence") or {}
        rect = _rect(r.get("rect"))
        if not rect:
            continue
        tag = str(v.get("tag_no") or "").strip()
        axis = ev.get("axis") or {}
        e = axis.get("ev") or {}
        tap = _run_seg(e.get("run")) or _run_seg((ev.get("line") or {}).get("run"))   # hotfix110 — 이 계기가 걸린 런
        for key in ("run",):
            s = _run_seg(e.get(key))
            if s:
                pipes[s] = "tap"
        for key in ("trunk", "mid_runs"):
            for run in e.get(key) or []:
                s = _run_seg(run)
                if s:
                    pipes.setdefault(s, "branch")
        ln = ev.get("line") or {}
        s = _run_seg(ln.get("run"))
        if s:
            pipes[s] = "line"
        if ln.get("line_no") and ln.get("rect"):
            lr = _rect(ln["rect"])
            if lr:
                labels[(ln["line_no"], tuple(lr))] = {"line_no": ln["line_no"], "size": ln.get("size") or "",
                                                       "rect": lr}
        for end in e.get("ends") or []:
            if end.get("kind") == "CONN" and end.get("name"):
                at = end.get("at") or [rect[0], rect[1]]
                conns[(end["name"], end.get("dir") or "", round(float(at[0])), round(float(at[1])))] = {
                    "name": end["name"], "dir": end.get("dir") or "", "at": [float(at[0]), float(at[1])]}
        for c in ev.get("candidates") or []:
            if c.get("kind") == "EQUIPMENT" and c.get("rect") and c.get("text"):
                cr = _rect(c["rect"])
                if cr:
                    equips[(c["text"], tuple(cr))] = {"name": c["text"], "rect": cr,
                                                      "noun": (c.get("equipment") or {}).get("noun", "")}
        scope = str(v.get("scope") or "")
        if r.get("tab") == "FIELD":
            inst.append({"key": r["key"], "tag": tag, "type": str(v.get("type") or ""), "rect": rect,
                         "scope": scope, "line_no": str(v.get("line_no") or ""),
                         "line_size": str(v.get("line_size") or ""),
                         "lines": int(((ev.get("detail") or {}).get("bubble_lines") or 0) or 0),
                         "equip": axis.get("equip") or "", "review": bool(r.get("needs_review")),
                         "tap": [round(c, 1) for c in tap] if tap else None})
        else:
            tr = _rect(ev.get("tag_rect")) if ev.get("tag_rect") else None
            valves.append({"key": r["key"], "tag": tag, "body": str(ev.get("body") or v.get("type") or ""),
                           "actuator": str(ev.get("actuator") or v.get("valve_type") or ""),
                           "state": str(ev.get("state") or ""), "rect": rect, "tag_rect": tr,
                           "scope": scope, "tab": r.get("tab") or ""})
    w, h = float(page.get("width") or 0), float(page.get("height") or 0)
    return {"page_no": int(page["page_no"]), "drawing_no": page.get("drawing_no") or "",
            "title": page.get("title") or "", "width": w, "height": h,
            "instruments": sorted(inst, key=lambda i: (i["rect"][1], i["rect"][0])),
            "valves": sorted(valves, key=lambda i: (i["rect"][1], i["rect"][0])),
            "pipes": [{"seg": [round(c, 1) for c in s], "role": role} for s, role in pipes.items()],
            "equipment": list(equips.values()), "connectors": list(conns.values()),
            "line_labels": list(labels.values()),
            "tagged": sum(1 for i in inst if i["tag"]) + sum(1 for i in valves if i["tag"])}


def tag_index(sheets: list) -> list:
    """태그 → 어느 장 · 어느 자리 · 무엇.  LOGIC 검토가 같은 태그로 찾는 표."""
    out = []
    for s in sheets:
        for i in s["instruments"]:
            if i["tag"]:
                out.append({"tag": i["tag"], "kind": "INSTRUMENT", "type": i["type"], "page_no": s["page_no"],
                            "drawing_no": s["drawing_no"], "rect": i["rect"], "key": i["key"]})
        for vv in s["valves"]:
            if vv["tag"]:
                out.append({"tag": vv["tag"], "kind": "VALVE", "type": vv["body"], "actuator": vv["actuator"],
                            "page_no": s["page_no"], "drawing_no": s["drawing_no"], "rect": vv["rect"],
                            "key": vv["key"]})
    return out


# ---------------------------------------------------------------- SVG

def _t(x, y, text, size=7.0, fill=C["tag"], anchor="middle", weight="normal", family="Arial, sans-serif"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
            f'font-family="{family}" font-weight="{weight}">{escape(str(text))}</text>')


def _state_of(states: dict, tag: str) -> dict:
    s = states.get(tag) if tag else None
    return s if isinstance(s, dict) else ({"s": s} if s is not None else {})


def _fmt_value(st: dict) -> tuple[str, str]:
    """칸에 보일 글자와 색.  값이 없으면 `----` (지어내지 않는다)."""
    if "v" in st and st["v"] is not None:
        v = st["v"]
        txt = f"{v:.2f}" if isinstance(v, float) else str(v)
        return txt + (f" {st['u']}" if st.get("u") else ""), (C["alarm"] if st.get("alarm") else C["val"])
    if "s" in st and st["s"] is not None:
        on = st["s"] in (1, True, "1", "ON", "on")
        return ("ON" if on else "OFF"), (C["on"] if on else C["val_dim"])
    return "----", C["val_dim"]


def _instrument_svg(i: dict, states: dict, above: bool = False) -> str:
    """`above` — 나란히 찍힌 좁은 버블은 태그를 위·아래로 번갈아 적는다 (글자가 서로 덮지 않게)."""
    x0, y0, x1, y1 = i["rect"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    # 칸은 **그 버블의 폭**을 넘지 않는다 — 나란히 찍힌 버블(LS 묶음 · 한 줄 다섯)이 서로 덮지 않게.
    # 작은 버블은 글자도 같은 비율로 줄인다 (하한 28pt — 그 아래는 글자가 안 읽힌다).
    fw = max(28.0, min(FACE_W, (x1 - x0) * 1.04))
    k = fw / FACE_W
    fh = FACE_H * max(k, 0.75)
    fx, fy = cx - fw / 2, cy - fh / 2
    st = _state_of(states, i["tag"])
    val, vc = _fmt_value(st)
    alarm = bool(st.get("alarm"))
    tag = i["tag"]
    vendor = i["scope"].upper().startswith("VENDOR")
    out = [f'<g class="inst" data-tag="{escape(tag)}" data-key="{escape(i["key"])}" data-type="{escape(i["type"])}">',
           f'<rect x="{fx:.1f}" y="{fy:.1f}" width="{fw:.1f}" height="{fh:.1f}" rx="2" fill="{C["face"]}" '
           f'stroke="{C["alarm"] if alarm else (C["vendor"] if vendor else C["face_line"])}" '
           f'stroke-width="{1.6 if alarm else 0.8}"' + ("" if tag else ' stroke-dasharray="2 1.5"') + "/>"]
    if alarm:
        out.append(f'<rect x="{fx:.1f}" y="{fy:.1f}" width="{fw:.1f}" height="{fh:.1f}" rx="2" fill="{C["alarm"]}" opacity="0.25">'
                   f'<animate attributeName="opacity" values="0.25;0.6;0.25" dur="1s" repeatCount="indefinite"/></rect>')
    # 왼쪽 위 TYPE · 가운데 선 표시(ISA 위치 — 1줄 DCS · 2줄 현장 패널) · 오른쪽 값
    out.append(_t(fx + 3 * k, fy + 8.5 * max(k, .75), i["type"], 6.5 * max(k, .75), C["type"], "start", "bold"))
    if i["lines"] and k > 0.6:
        out.append(_t(fx + 3 * k, fy + 17 * max(k, .75), "DCS" if i["lines"] == 1 else "LP", 5 * k, C["type"], "start"))
    out.append(_t(fx + fw - 3 * k, fy + 18 * max(k, .75), val, 9 * max(k, .6), vc, "end", "bold", "Consolas, monospace"))
    ty = (fy - 3) if above else (fy + fh + 8 * max(k, .75))
    if tag:                                       # 태그 없는 계기는 칸만 (점선) — 이름을 지어내지 않는다
        out.append(_t(cx, ty, tag, 6.5 * max(k, .7), C["tag"], "middle"))
    if i["line_no"] and tag:
        out.append(_t(cx, ty + 7 * max(k, .75), f'{i["line_no"]} {i["line_size"]}'.strip(), 5.2 * max(k, .7), C["pipe_lbl"]))
    out.append("</g>")
    return "".join(out)


def _valve_svg(vv: dict, states: dict) -> str:
    x0, y0, x1, y1 = vv["rect"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = max(VALVE_R, min(14.0, (x1 - x0) / 2))
    st = _state_of(states, vv["tag"])
    opened = st.get("open")
    if opened is None and "s" in st:
        opened = st["s"] in (1, True, "1", "ON", "on", "OPEN")
    fill = C["open"] if opened is True else C["closed"] if opened is False else C["off"]
    act = (vv["actuator"] or "")[:1].upper()
    tag = vv["tag"] or ""
    out = [f'<g class="valve" data-tag="{escape(tag)}" data-key="{escape(vv["key"])}" data-body="{escape(vv["body"])}">',
           f'<polygon points="{cx - r:.1f},{cy - r * .7:.1f} {cx:.1f},{cy:.1f} {cx - r:.1f},{cy + r * .7:.1f}" fill="{fill}"/>',
           f'<polygon points="{cx + r:.1f},{cy - r * .7:.1f} {cx:.1f},{cy:.1f} {cx + r:.1f},{cy + r * .7:.1f}" fill="{fill}"/>']
    if act and act != "N":
        out.append(f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{cx:.1f}" y2="{cy - r * 1.4:.1f}" stroke="{C["act"]}" stroke-width="1"/>'
                   f'<circle cx="{cx:.1f}" cy="{cy - r * 1.9:.1f}" r="{r * .55:.1f}" fill="{C["face"]}" stroke="{C["act"]}" stroke-width="0.8"/>'
                   + _t(cx, cy - r * 1.9 + 2.2, act, 6, C["act"], "middle", "bold"))
    if tag:
        out.append(_t(cx, cy + r + 8, tag, 6, C["tag"]))
    out.append("</g>")
    return "".join(out)


def _equip_svg(e: dict) -> str:
    x0, y0, x1, y1 = e["rect"]
    w, h = max(x1 - x0, 20.0), max(y1 - y0, 12.0)
    return (f'<g class="equip" data-name="{escape(e["name"])}">'
            f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{h:.1f}" rx="6" fill="{C["equip"]}" '
            f'stroke="{C["equip_line"]}" stroke-width="1" opacity="0.9"/>'
            + _t(x0 + w / 2, y0 + h / 2 + 2.5, e["name"], 7, C["equip_txt"], "middle", "bold") + "</g>")


def _conn_svg(c: dict) -> str:
    x, y = c["at"]
    w, h = 10 + 4.2 * len(c["name"]), 12.0
    left = c["dir"] == "FROM"
    x0 = x - w if not left else x
    pts = ([f"{x0:.1f},{y - h/2:.1f}", f"{x0 + w - 6:.1f},{y - h/2:.1f}", f"{x0 + w:.1f},{y:.1f}",
            f"{x0 + w - 6:.1f},{y + h/2:.1f}", f"{x0:.1f},{y + h/2:.1f}"] if not left else
           [f"{x0 + w:.1f},{y - h/2:.1f}", f"{x0 + 6:.1f},{y - h/2:.1f}", f"{x0:.1f},{y:.1f}",
            f"{x0 + 6:.1f},{y + h/2:.1f}", f"{x0 + w:.1f},{y + h/2:.1f}"])
    return (f'<g class="conn"><polygon points="{" ".join(pts)}" fill="{C["conn_fill"]}" stroke="{C["conn"]}" stroke-width="0.8"/>'
            + _t(x0 + w / 2 + (-3 if not left else 3), y + 2.5, c["name"], 6, C["conn"]) + "</g>")


def render_svg(sheet: dict, states: dict | None = None, title: bool = True) -> str:
    """모델 → SVG 글.  `states` 는 태그 → {"v": 값, "u": 단위, "s": 0/1, "open": bool, "alarm": bool}."""
    states = states or {}
    W, H = sheet["width"] or 2384.0, sheet["height"] or 1684.0
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}" '
           f'data-page="{sheet["page_no"]}" data-drawing="{escape(sheet["drawing_no"])}">',
           # MuPDF 의 SVG 는 `100%` 크기 · pattern 을 안 그린다 — 절대 크기로, 격자는 선으로
           f'<rect x="0" y="0" width="{W:.0f}" height="{H:.0f}" fill="{C["bg"]}"/>']
    out += [f'<line x1="{x}" y1="0" x2="{x}" y2="{H:.0f}" stroke="{C["grid"]}" stroke-width="0.6"/>' for x in range(80, int(W), 80)]
    out += [f'<line x1="0" y1="{y}" x2="{W:.0f}" y2="{y}" stroke="{C["grid"]}" stroke-width="0.6"/>' for y in range(80, int(H), 80)]
    for p in sheet["pipes"]:
        x0, y0, x1, y1 = p["seg"]
        sw = 2.2 if p["role"] in ("tap", "line") else 1.4
        out.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{C["pipe"]}" stroke-width="{sw}" stroke-linecap="round"/>')
    for e in sheet["equipment"]:
        out.append(_equip_svg(e))
    for c in sheet["connectors"]:
        out.append(_conn_svg(c))
    for L in sheet["line_labels"]:
        x0, y0, x1, y1 = L["rect"]
        out.append(_t((x0 + x1) / 2, y0 - 2, f'{L["line_no"]} {L["size"]}'.strip(), 6, C["pipe_lbl"]))
    for vv in sheet["valves"]:
        out.append(_valve_svg(vv, states))
    # 좁은 버블(칸이 그 폭을 못 넘는 것)이 한 줄에 나란히 서면 태그를 아래·위로 번갈아 — 한 줄 = 세로가 겹치는 이웃
    inst = sheet["instruments"]
    flip = {}
    for n, i in enumerate(inst):
        if (i["rect"][2] - i["rect"][0]) * 1.04 >= FACE_W * 0.7:
            continue
        prev = [m for m in flip if abs(inst[m]["rect"][1] - i["rect"][1]) < FACE_H
                and abs(inst[m]["rect"][2] - i["rect"][0]) < FACE_W]
        flip[n] = (not flip[prev[-1]]) if prev else False
    for n, i in enumerate(inst):
        out.append(_instrument_svg(i, states, above=flip.get(n, False)))
    if title:
        out.append(f'<rect x="0" y="0" width="{W:.0f}" height="34" fill="#1c2026"/>')
        out.append(_t(14, 22, f'{sheet["drawing_no"]}  ·  {sheet["title"]}', 16, C["title"], "start", "bold"))
        out.append(_t(W - 14, 22, f'계기 {len(sheet["instruments"])} · 밸브 {len(sheet["valves"])} · 태그 {sheet["tagged"]}  —  간략화 DCS 그래픽 (식별 결과 · 값은 로직 시뮬레이션 연동 전까지 ----)', 9, C["sub"], "end"))
    out.append("</svg>")
    return "".join(out)


def render_png(svg: str, dpi: int = 110) -> bytes:
    import pymupdf
    doc = pymupdf.open(stream=svg.encode("utf-8"), filetype="svg")
    try:
        return doc[0].get_pixmap(dpi=dpi).tobytes("png")
    finally:
        doc.close()


# ---------------------------------------------------------------- 서버에서 — 저장된 분석을 읽기만 한다

def _main():
    from app import main                 # main 이 이 라우터를 붙이므로 쓸 때 가져온다
    return main


def _eligibility(job_id: str) -> tuple[dict | None, dict]:
    m = _main()
    job = m.db.get_job(m.CON, job_id)
    if job is None:
        return None, {"error": "no such job", "status": 404}
    if job["status"] != "done":
        return job, {"eligible": False, "reason": "분석이 끝난 결과에서만 만들 수 있습니다"}
    facts = m._mode_facts(job)
    if facts.get("effective") != "epc":
        return job, {"eligible": False, "mode": facts.get("effective") or "",
                     "reason": "실행(태그 있는) P&ID 에서만 만듭니다 — 이 분석은 태그 번호가 없어 요소를 가리킬 이름이 없습니다"
                               + (" (입찰 모드)" if facts.get("effective") == "bid" else "")}
    if not facts.get("tagged_rows"):
        return job, {"eligible": False, "mode": "epc", "reason": "실행 모드인데 태그가 붙은 행이 없습니다"}
    return job, {"eligible": True, "mode": "epc", "tagged_rows": facts.get("tagged_rows")}


def _equipment_labels(job_id: str) -> dict:
    """hotfix111 — 그 분석이 장마다 찾은 기기 이름 전부 (`engine_json["equipment_labels"]`).  옛 분석은 빈 값."""
    m = _main()
    job = m.db.get_job(m.CON, job_id)
    try:
        eng = json.loads((job["engine_json"] if job else None) or "{}")
    except (TypeError, ValueError):
        eng = {}
    return eng.get("equipment_labels") or {}


def _sheets(job_id: str) -> list:
    m = _main()
    eq_labels = _equipment_labels(job_id)
    rows = m.db.merged_rows(m.CON, job_id)
    by_page = {}
    for r in rows:
        by_page.setdefault(int(r["page_no"]), []).append(r)
    out = []
    for p in m.CON.execute("SELECT page_no, drawing_no, title, page_kind, in_scope, width, height FROM pid_page "
                           "WHERE job_id=? ORDER BY page_no", (job_id,)).fetchall():
        p = dict(p)
        if p.get("page_kind") != "PID" or not by_page.get(int(p["page_no"])):
            continue
        out.append(build_sheet(p, by_page[int(p["page_no"])], eq_labels.get(str(p["page_no"]))))
    return out


def _layout_area(job_id: str) -> list | None:
    """분석이 그 문서에서 잰 도면 영역 (`applied_rules.layout` 의 `regions.drawing_area` — 적용되지 않았어도 기록은 남는다)."""
    m = _main()
    job = m.db.get_job(m.CON, job_id)
    try:
        eng = json.loads((job["engine_json"] if job else None) or "{}")
    except (TypeError, ValueError):
        return None
    for it in ((eng.get("applied_rules") or {}).get("layout") or {}).get("items") or []:
        if it.get("key") == "regions.drawing_area" and isinstance(it.get("value"), list) and len(it["value"]) == 4:
            return [float(v) for v in it["value"]]
    return None


def geom_hints(model: dict, area: list | None) -> dict:
    """hotfix113 — 도면 기하 읽기(`app.hmi.pidgeom`)에 줄 것: 도면 영역 · 버블 크기 · 비킬 사각형(계기 · 밸브 · 태그 버블)."""
    import statistics
    bub = [min(i["rect"][2] - i["rect"][0], i["rect"][3] - i["rect"][1]) for i in model.get("instruments") or []]
    bub = [b for b in bub if b > 2]
    avoid = [i["rect"] for i in model.get("instruments") or []] + [v["rect"] for v in model.get("valves") or []] \
        + [v["tag_rect"] for v in model.get("valves") or [] if v.get("tag_rect")]
    return {"area": area, "bubble": statistics.median(bub) if bub else None, "avoid": avoid,
            "bubbles": [i["rect"] for i in model.get("instruments") or []]}


GEOM_VERSION = 1


def attach_geom(job_id: str, models: list) -> None:
    """hotfix113 — 모델마다 그 장의 도면 기하(배관 전체 · 장비 외곽 · 커넥터 · 직경 글)를 `model["geom"]` 에.
    판정과 무관한 그래픽 재료다 — 분석 결과 · 지문에 닿지 않고 `{data}/hmi/<분석>/geom/p<장>.json` 에 기억한다
    (PDF 크기 · 시각 · 판이 같을 때만).  계산은 서버 밖 일꾼(`page_warm.call`)이 — 못 쓰면 서버 안에서."""
    from app.hmi import pidgeom
    m = _main()
    job = m.db.get_job(m.CON, job_id)
    pdf = Path(job["pdf_path"]) if job and job["pdf_path"] else None
    if not pdf or not pdf.exists() or pdf.suffix.lower() != ".pdf":
        return
    st = pdf.stat()
    stamp = f"{pidgeom.VERSION}.{GEOM_VERSION}:{st.st_size}:{int(st.st_mtime)}"
    folder = paths.data_dir() / "hmi" / job_id / "geom"
    area = _layout_area(job_id)
    todo = []
    for md in models:
        f = folder / f"p{int(md['page_no'])}.json"
        try:
            got = json.loads(f.read_text(encoding="utf-8"))
            if got.get("stamp") == stamp:
                md["geom"] = got["geom"]
                continue
        except (OSError, ValueError):
            pass
        todo.append(md)
    if not todo:
        return
    jobs = [(int(md["page_no"]), geom_hints(md, area)) for md in todo]
    try:
        from app import page_warm
        out = page_warm.call(pidgeom.read_pdf, (str(pdf), jobs), timeout=300)
    except Exception:                            # noqa: BLE001 — 일꾼이 없으면 서버 안에서
        try:
            out = pidgeom.read_pdf(str(pdf), jobs)
        except Exception:                        # noqa: BLE001 — 도면을 못 읽으면 기하 없이 (예전 장면)
            return
    folder.mkdir(parents=True, exist_ok=True)
    for md in todo:
        g = (out or {}).get(int(md["page_no"]))
        if g is None:
            continue
        md["geom"] = g
        try:
            from app import jsonstore
            jsonstore.write(folder / f"p{int(md['page_no'])}.json", {"stamp": stamp, "geom": g})
        except Exception:                        # noqa: BLE001 — 기억 못 해도 그림은 그린다
            pass


def _sheet(job_id: str, page_no: int) -> dict | None:
    return next((s for s in _sheets(job_id) if s["page_no"] == int(page_no)), None)


def _json(data, status=200):
    return JSONResponse(data, status_code=status, headers={"Cache-Control": "no-store"})


@router.get("/dcs")
def dcs_page():
    """hotfix110 — 화면은 LOGIC 브랜치 H1회차의 HMI 화면(`app/static/dcs.html` + `app/static/hmi/*`) 이다."""
    return page_stamp.page("dcs.html", badge=False)


@router.get("/dcs/demo")
def dcs_demo_page():
    """예시 화면(압축기 트레인) — 식별 P&ID 없이 HMI 부품을 본다.  같은 화면이 출처 '예시' 로 연다."""
    return page_stamp.page("dcs.html", badge=False)


@router.get("/hmi")
def hmi_page():
    """H1 인계 문서(`docs/hmi_handover.md`)가 적은 주소 — 같은 화면."""
    return page_stamp.page("dcs.html", badge=False)


@router.get("/dcs/api/example")
def api_example():
    """참고 DCS 화면(압축기 트레인)을 데이터로 다시 그린 예시 장면 — PNG 를 쓰지 않는다."""
    return _json(json.loads(paths.resource("config", "hmi_example_compressor_train.json").read_text(encoding="utf-8")))


@router.get("/dcs/api/sources")
def api_sources():
    """그래픽을 만들 수 있는 P&ID 분석 (끝났고 · 실행 모드이고 · 태그가 있는 것) — 화면의 출처 고르기."""
    return _json(pid_jobs_for_project("")["candidates"])


def _scene_store():
    from app.hmi import store
    return store


@router.get("/dcs/api/jobs/{job_id}/scene/{page_no}")
def api_scene(job_id: str, page_no: int, fresh: int = 0):
    """저장본이 있으면 그것, 없으면 그 장의 식별 결과에서 새로 만든 장면 (`app.hmi.scene.from_model`)."""
    job, el = _eligibility(job_id)
    if job is None or not el["eligible"]:
        return _json({"error": el.get("reason") or el.get("error")}, 404 if job is None else 400)
    store = _scene_store()
    saved = None if fresh else store.load(job_id, page_no)
    if saved:
        saved["saved"] = True
        return _json(saved)
    s = _sheet(job_id, page_no)
    if not s:
        return _json({"error": "그 장에는 식별된 행이 없습니다"}, 404)
    attach_geom(job_id, [s])
    from app.hmi import scene
    sc = scene.from_model(s, hmi_load(job_id))
    sc["saved"] = False
    return _json(sc)


@router.post("/dcs/api/jobs/{job_id}/scene/{page_no}")
async def api_scene_save(job_id: str, page_no: int, request: Request):
    """사람이 다듬은 장면 저장 — `{dcs 데이터}/hmi/<분석>/p<장>.json` (작성자 필수 · 분석 결과는 그대로)."""
    job, el = _eligibility(job_id)
    if job is None:
        return _json({"error": el["error"]}, 404)
    try:
        body = await request.json()
    except ValueError:
        body = {}
    sc = body.get("scene") if isinstance(body, dict) else None
    if not isinstance(sc, dict):
        return _json({"error": "scene 이 없습니다"}, 400)
    from urllib.parse import unquote
    author = unquote(request.headers.get("x-author") or "").strip() or str(body.get("author") or "").strip()
    try:
        out = _scene_store().save(job_id, page_no, sc, " ".join(author.split())[:40])
    except ValueError:
        return _json({"error": "작성자 이름이 필요합니다 — 대시보드에서 로그인한 뒤 다시 여세요 (?user=)"}, 401)
    except KeyError:
        return _json({"error": "분석 번호 꼴이 아닙니다"}, 400)
    return _json({"ok": True, "saved_at": out["saved_at"], "saved_by": out["saved_by"]})


@router.delete("/dcs/api/jobs/{job_id}/scene/{page_no}")
def api_scene_reset(job_id: str, page_no: int):
    """저장본을 지우고 식별 결과로 되돌린다."""
    job, el = _eligibility(job_id)
    if job is None:
        return _json({"error": el["error"]}, 404)
    return _json({"ok": True, "removed": _scene_store().delete(job_id, page_no)})


def _system_models(job_id: str, key: str) -> list:
    from app.hmi import scene
    return [s for s in _sheets(job_id) if scene.system_of(s["drawing_no"], s["page_no"])[0] == key]


@router.get("/dcs/api/jobs/{job_id}/system/{key}/scene")
def api_system_scene(job_id: str, key: str, fresh: int = 0):
    """hotfix111 — 같은 시스템(도면번호에서 일련번호를 뗀 것)의 장들을 한 장에 (`app.hmi.scene.from_system`).
    저장본이 있으면 그것 (`{data}/hmi/<분석>/s_<시스템>.json`)."""
    job, el = _eligibility(job_id)
    if job is None or not el["eligible"]:
        return _json({"error": el.get("reason") or el.get("error")}, 404 if job is None else 400)
    store = _scene_store()
    try:
        saved = None if fresh else store.load(job_id, f"sys:{key}")
    except KeyError:
        return _json({"error": "시스템 열쇠 꼴이 아닙니다"}, 400)
    if saved:
        saved["saved"] = True
        return _json(saved)
    models = _system_models(job_id, key)
    if not models:
        return _json({"error": "그 시스템에는 식별된 장이 없습니다"}, 404)
    attach_geom(job_id, models)
    from app.hmi import scene
    sc = scene.from_system(models, hmi_load(job_id), key)
    sc["saved"] = False
    return _json(sc)


@router.post("/dcs/api/jobs/{job_id}/system/{key}/scene")
async def api_system_scene_save(job_id: str, key: str, request: Request):
    """사람이 다듬은 시스템 한 장 저장 (작성자 필수 · 분석 결과는 그대로)."""
    job, el = _eligibility(job_id)
    if job is None:
        return _json({"error": el["error"]}, 404)
    try:
        body = await request.json()
    except ValueError:
        body = {}
    sc = body.get("scene") if isinstance(body, dict) else None
    if not isinstance(sc, dict):
        return _json({"error": "scene 이 없습니다"}, 400)
    from urllib.parse import unquote
    author = unquote(request.headers.get("x-author") or "").strip() or str(body.get("author") or "").strip()
    try:
        out = _scene_store().save(job_id, f"sys:{key}", sc, " ".join(author.split())[:40])
    except ValueError:
        return _json({"error": "작성자 이름이 필요합니다 — 대시보드에서 로그인한 뒤 다시 여세요 (?user=)"}, 401)
    except KeyError:
        return _json({"error": "분석 번호 · 시스템 열쇠 꼴이 아닙니다"}, 400)
    return _json({"ok": True, "saved_at": out["saved_at"], "saved_by": out["saved_by"]})


@router.delete("/dcs/api/jobs/{job_id}/system/{key}/scene")
def api_system_scene_reset(job_id: str, key: str):
    job, el = _eligibility(job_id)
    if job is None:
        return _json({"error": el["error"]}, 404)
    try:
        return _json({"ok": True, "removed": _scene_store().delete(job_id, f"sys:{key}")})
    except KeyError:
        return _json({"error": "시스템 열쇠 꼴이 아닙니다"}, 400)


@router.get("/dcs/api/jobs/{job_id}")
def api_job(job_id: str):
    job, el = _eligibility(job_id)
    if job is None:
        return _json({"error": el["error"]}, 404)
    if not el["eligible"]:
        return _json({**el, "job_id": job_id, "pdf_name": job["pdf_name"], "sheets": []})
    sheets = _sheets(job_id)
    from app.hmi import scene
    by = {s["page_no"]: s for s in sheets}
    return _json({**el, "job_id": job_id, "pdf_name": job["pdf_name"], "project": job["project"] or "",
                  "sheets": [{"page_no": s["page_no"], "drawing_no": s["drawing_no"], "title": s["title"],
                              "instruments": len(s["instruments"]), "valves": len(s["valves"]),
                              "tagged": s["tagged"], "pipes": len(s["pipes"]), "equipment": sum(1 for e in s["equipment"] if not scene.name_only(e.get("noun"))),
                              "saved": _scene_store().path(job_id, s["page_no"]).exists(),
                              "system": scene.system_of(s["drawing_no"], s["page_no"])[0]}
                             for s in sheets],
                  # hotfix111 — 같은 시스템의 장들은 한 장으로 (화면이 먼저 띄우는 것)
                  "systems": [{**g, "instruments": sum(len(by[p]["instruments"]) for p in g["pages"]),
                               "valves": sum(len(by[p]["valves"]) for p in g["pages"]),
                               "equipment": sum(1 for p in g["pages"] for e in by[p]["equipment"] if not scene.name_only(e.get("noun"))),
                               "saved": _scene_store().sys_path(job_id, g["key"]).exists()}
                              for g in scene.group_systems(sheets)]})


def _norm_name(s: str) -> str:
    return re.sub(r"[\s_\-]+", "", str(s or "")).upper()


def pid_jobs_for_project(name: str) -> dict:
    """hotfix109 — LOGIC 화면이 "같은 프로젝트의 P&ID 그래픽" 을 찾는 길.

    P&ID 프로젝트 장부와 LOGIC 프로젝트 장부는 따로라(각자 이름을 적는다) **이름**으로 맞댄다 — 띄어쓰기 · 밑줄 · 붙임표 ·
    대소문자는 무시.  맞는 프로젝트의 가장 최근에 끝난 **실행(태그 있는) P&ID** 가 `match`, 그래픽을 만들 수 있는 P&ID
    분석 전부가 `candidates` (이름이 안 맞으면 사람이 고른다 — 지어내지 않는다)."""
    m = _main()
    want = _norm_name(name)
    cands = []
    for job in m.db.list_jobs(m.CON):
        if job["status"] != "done":
            continue
        _, el = _eligibility(job["id"])
        if not el.get("eligible"):
            continue
        cands.append({"job_id": job["id"], "project": job["project"] or "", "pdf_name": job["pdf_name"],
                      "revision": job["revision"] if "revision" in job.keys() else "",
                      "analysed_at": job["created_at"] if "created_at" in job.keys() else None,
                      "tagged_rows": el.get("tagged_rows", 0),
                      "same_project": bool(want) and _norm_name(job["project"]) == want})
    match = next((c for c in cands if c["same_project"]), None)     # list_jobs 는 최근 것부터
    return {"project": name or "", "match": match, "candidates": cands}


@router.get("/dcs/api/for_project")
def api_for_project(name: str = ""):
    return _json(pid_jobs_for_project(name))


@router.get("/dcs/api/jobs/{job_id}/tags")
def api_tags(job_id: str):
    job, el = _eligibility(job_id)
    if job is None or not el["eligible"]:
        return _json({"error": el.get("reason") or el.get("error"), "tags": []}, 404 if job is None else 200)
    return _json({"job_id": job_id, "tags": tag_index(_sheets(job_id))})


@router.get("/dcs/api/jobs/{job_id}/sheet/{page_no}/model")
def api_sheet(job_id: str, page_no: int):
    job, el = _eligibility(job_id)
    if job is None or not el["eligible"]:
        return _json({"error": el.get("reason") or el.get("error")}, 404 if job is None else 400)
    s = _sheet(job_id, page_no)
    return _json(s) if s else _json({"error": "그 장에는 식별된 행이 없습니다"}, 404)


def _states_from(request: Request, body: dict | None) -> dict:
    raw = (body or {}).get("states") if body else None
    if raw is None:
        q = request.query_params.get("states")
        if q:
            try:
                raw = json.loads(q)
            except ValueError:
                raw = None
    return raw if isinstance(raw, dict) else {}


@router.get("/dcs/api/jobs/{job_id}/sheet/{page_no}.svg")
def api_sheet_svg(job_id: str, page_no: int, request: Request):
    job, el = _eligibility(job_id)
    if job is None or not el["eligible"]:
        return _json({"error": el.get("reason") or el.get("error")}, 404 if job is None else 400)
    s = _sheet(job_id, page_no)
    if not s:
        return _json({"error": "그 장에는 식별된 행이 없습니다"}, 404)
    return Response(render_svg(s, _states_from(request, None)), media_type="image/svg+xml",
                    headers={"Cache-Control": "no-store"})


@router.get("/dcs/api/jobs/{job_id}/sheet/{page_no}.png")
def api_sheet_png(job_id: str, page_no: int, request: Request):
    job, el = _eligibility(job_id)
    if job is None or not el["eligible"]:
        return _json({"error": el.get("reason") or el.get("error")}, 404 if job is None else 400)
    s = _sheet(job_id, page_no)
    if not s:
        return _json({"error": "그 장에는 식별된 행이 없습니다"}, 404)
    return Response(render_png(render_svg(s, _states_from(request, None))), media_type="image/png",
                    headers={"Cache-Control": "no-store"})


@router.post("/dcs/api/jobs/{job_id}/sheet/{page_no}/render")
async def api_render(job_id: str, page_no: int, request: Request):
    """로직 시뮬레이션 연동 자리 — `{"states": {태그: {...}}, "format": "svg"|"png"}` → 칠한 그림."""
    try:
        body = json.loads((await request.body()).decode("utf-8") or "{}")
    except ValueError:
        body = {}
    job, el = _eligibility(job_id)
    if job is None or not el["eligible"]:
        return _json({"error": el.get("reason") or el.get("error")}, 404 if job is None else 400)
    s = _sheet(job_id, page_no)
    if not s:
        return _json({"error": "그 장에는 식별된 행이 없습니다"}, 404)
    svg = render_svg(s, _states_from(request, body if isinstance(body, dict) else None))
    if (body or {}).get("format") == "png":
        return Response(render_png(svg), media_type="image/png", headers={"Cache-Control": "no-store"})
    return Response(svg, media_type="image/svg+xml", headers={"Cache-Control": "no-store"})


# ---------------------------------------------------------------- hotfix109 — HMI 화면의 사람 값 (태그 편집 · Key Parameters · Trend)

HMI_ID_RE = re.compile(r"^[A-Za-z0-9#/._ +()-]{0,40}$")


def _hmi_path(job_id: str) -> Path:
    return paths.data_dir() / "dcs" / re.sub(r"[^0-9a-f]", "", job_id) / "hmi.json"


def hmi_load(job_id: str) -> dict:
    from app import jsonstore
    d = jsonstore.read(_hmi_path(job_id), {}, what="HMI 사람 값")
    return d if isinstance(d, dict) else {}


def hmi_save(job_id: str, body: dict, author: str) -> dict:
    """사람이 고친 태그 · 기기 이름 · Key Parameters 목록 · Trend 태그를 분석 폴더 밖 `dcs/<job>/hmi.json` 에 둔다.
    분석 결과(행)는 건드리지 않는다 — 그래서 지문에 닿지 않고, 다시 분석해도 남는다.  지우지 않고 이력을 쌓는다."""
    from app import jsonstore
    if not author:
        raise ValueError("이름이 없어 저장할 수 없습니다 — 대시보드에서 로그인한 뒤 다시 여세요 (?user=)")
    cur = hmi_load(job_id)
    cur.setdefault("tags", {}); cur.setdefault("names", {}); cur.setdefault("history", [])
    for key, val in (body.get("tags") or {}).items():
        if not isinstance(val, str) or not HMI_ID_RE.match(val):
            raise ValueError(f"태그 꼴이 아닙니다: {val!r}")
        cur["history"].append({"at": time.strftime("%Y-%m-%d %H:%M:%S"), "by": author, "kind": "tag", "key": key, "from": cur["tags"].get(key), "to": val})
        if val == "" :
            cur["tags"].pop(key, None)
        else:
            cur["tags"][key] = val
    for key, val in (body.get("names") or {}).items():
        if not isinstance(val, str) or len(val) > 80:
            raise ValueError("기기 이름이 너무 깁니다")
        cur["history"].append({"at": time.strftime("%Y-%m-%d %H:%M:%S"), "by": author, "kind": "name", "key": key, "from": cur["names"].get(key), "to": val})
        if val == "":
            cur["names"].pop(key, None)
        else:
            cur["names"][key] = val
    if "params" in body:
        prm = body.get("params")
        if not isinstance(prm, dict):
            raise ValueError("params 는 {쪽: [태그…]} 꼴이어야 합니다")
        cur.setdefault("params", {}).update({str(k): [str(t)[:40] for t in (v or [])][:12] for k, v in prm.items()})
    if "trend" in body:
        tr = body.get("trend")
        if not isinstance(tr, dict):
            raise ValueError("trend 는 {쪽: 태그} 꼴이어야 합니다")
        cur.setdefault("trend", {}).update({str(k): str(v)[:40] for k, v in tr.items()})
    cur["history"] = cur["history"][-500:]
    cur["updated"] = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "by": author}
    jsonstore.write(_hmi_path(job_id), cur, sort_keys=False)
    return cur


@router.get("/dcs/api/jobs/{job_id}/hmi")
def api_hmi_get(job_id: str):
    job, el = _eligibility(job_id)
    if job is None:
        return _json(el, 404)
    return _json(hmi_load(job_id))


@router.post("/dcs/api/jobs/{job_id}/hmi")
async def api_hmi_post(job_id: str, request: Request):
    job, el = _eligibility(job_id)
    if job is None:
        return _json(el, 404)
    try:
        body = await request.json()
    except ValueError:
        body = {}
    if not isinstance(body, dict):
        return _json({"error": "JSON 꼴이 아닙니다"}, 400)
    from urllib.parse import unquote
    author = unquote(request.headers.get("x-author") or "").strip() or str(body.get("author") or "").strip()
    try:
        return _json(hmi_save(job_id, body, " ".join(author.split())[:40]))
    except ValueError as e:
        return _json({"error": str(e)}, 400 if "꼴" in str(e) or "깁니다" in str(e) else 401)


@router.get("/dcs/api/jobs/{job_id}/export.zip")
def api_export(job_id: str):
    """모든 장의 SVG · PNG · 모델 JSON · 태그 표를 한 zip 으로."""
    job, el = _eligibility(job_id)
    if job is None or not el["eligible"]:
        return _json({"error": el.get("reason") or el.get("error")}, 404 if job is None else 400)
    sheets = _sheets(job_id)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for s in sheets:
            stem = re.sub(r"[^A-Za-z0-9_-]+", "_", s["drawing_no"] or f"p{s['page_no']}")
            svg = render_svg(s)
            z.writestr(f"{stem}.svg", svg)
            z.writestr(f"{stem}.png", render_png(svg))
            z.writestr(f"{stem}.json", json.dumps(s, ensure_ascii=False, indent=1))
        z.writestr("tags.json", json.dumps(tag_index(sheets), ensure_ascii=False, indent=1))
        z.writestr("README.txt", "간략화 DCS 그래픽 — 식별 결과에서 만든 그림입니다.\n"
                   "값(----)은 로직 시뮬레이션 연동 전까지 비어 있습니다.  tags.json 의 태그가 그림의 data-tag 와 같습니다.\n")
    name = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(job["pdf_name"] or "dcs").stem)
    return Response(buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="DCS_{name}.zip"',
                             "Cache-Control": "no-store"})
