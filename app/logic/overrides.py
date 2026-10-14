"""사람이 정한 값 — 게이트 종류 · FM/TO 칸 · 타이머 시간 (L22).

  `{data}/logic/<job>/overrides.json` = {
      "blocks": {쪽: {블록: {choice, func, logic, label, param, author, at, was}}},
      "cells":  {쪽: {"L:12": {"fm": 값, author, at, was}, "R:30": {"to": 값, ...}}},
      "timers": {쪽: {블록: {t: 초, author, at}}},
      "marks":  {쪽: {id: {kind, rect, value, n, choice, param, author, at}}},     (L24 마크업)
      "history": [{kind, page, key, value, was, author, at}],
  }

  * 분석 결과(result.json)는 한 글자도 바꾸지 않는다 — 화면이 결과를 읽을 때(api._result) 이 파일을 얹는다.
    그래서 다시 분석해도 사람이 정한 값은 남고(같은 쪽 · 같은 블록 이름 · 같은 행), 지우면 도면 값으로 돌아간다.
  * 도면이 말하지 않는 것만 사람이 정한다 — 판정 못 한 블록의 종류 · 못 읽은 FM/TO · 도면에 없는 타이머 시간.
    (읽은 칸도 고칠 수는 있다 — 근거 패널이 '사람이 고침 (도면 값 …)' 으로 둘 다 말한다.)
  * 작성자는 자기신고(대시보드 로그인 · 기억된 이름).  비우면 저장하지 않는다.
"""
from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path

from . import store

_LOCK = threading.Lock()
MAX_CELL = 120

# 사람이 고를 수 있는 종류 → (func, logic, 기본 글자, param).  범례 G003 / ISA-S5.2 어휘 그대로.
CHOICES = {
    "AND": ("AND", "and", "AND", {}),
    "OR": ("OR", "or", "OR", {}),
    "NOT": ("NOT", "not", "NOT", {}),
    "NAND": ("NAND", "nand", "NAND", {}),
    "NOR": ("NOR", "nor", "NOR", {}),
    "VOTE": ("VOTE", "vote", "A/B", {}),                    # B 개 중 A 개 이상 (param a · b)
    "GT": ("GT", "delay_on", "ON DELAY", {}),
    "DT": ("DT", "delay_off", "OFF DELAY", {}),
    "PD": ("PD", "pulse", "PULSE", {}),
    "MEMORY": ("MEMORY", "memory", "S/R", {"dominant": ""}),
    "MEMORY_S": ("MEMORY", "memory", "S/R", {"dominant": "set"}),
    "MEMORY_R": ("MEMORY", "memory", "S/R", {"dominant": "reset"}),
    "PB": ("PB", "source", "PB", {}),                       # 누름단추 · 사람이 주는 입력
    "SIGNAL": ("SIGNAL", "source", "SIGNAL", {}),           # 이름 붙은 신호 상자 (입력)
    "CONST1": ("CONST", "source", "1", {}),                 # 언제나 1 (ACTIVATION · FORCED INPUT 1)
    "CONST0": ("CONST", "source", "0", {}),
    "ANN": ("ANN", "sink", "ANN", {}),                      # 경보 · 표시 · 기록 — 받기만
    "ANALOG": ("ANALOG", "unknown", "ANALOG", {}),          # 아날로그 연산 (이진 출력이 아니다)
}
CHOICE_KO = {
    "AND": "AND", "OR": "OR", "NOT": "NOT", "NAND": "NAND", "NOR": "NOR", "VOTE": "투표 (B 개 중 A 개)",
    "GT": "ON DELAY (GT)", "DT": "OFF DELAY (DT)", "PD": "PULSE (PD)", "MEMORY": "메모리 (기본)",
    "MEMORY_S": "메모리 (SET 우선)", "MEMORY_R": "메모리 (RESET 우선)", "PB": "누름단추 (입력)",
    "SIGNAL": "신호 상자 (입력)", "CONST1": "언제나 1", "CONST0": "언제나 0", "ANN": "경보 · 표시 (받기만)",
    "ANALOG": "아날로그 연산 (이진 아님)",
}


def _path(d: Path) -> Path:
    return d / "overrides.json"


def empty():
    return {"blocks": {}, "cells": {}, "timers": {}, "marks": {}, "history": []}


def load(d: Path) -> dict:
    try:
        data = json.loads(_path(d).read_text(encoding="utf-8"))
        if isinstance(data, dict):
            out = empty()
            for k in out:
                if isinstance(data.get(k), type(out[k])):
                    out[k] = data[k]
            return out
    except Exception:
        pass
    return empty()


def mtime(d: Path):
    try:
        return _path(d).stat().st_mtime_ns
    except OSError:
        return None


def has_any(ov: dict) -> bool:
    return any(ov.get(k) for k in ("blocks", "cells", "timers", "marks"))


def _save(d: Path, data: dict):
    store._atomic(_path(d), json.dumps(data, ensure_ascii=False, indent=1))


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _author(a):
    a = (a or "").strip()[:60]
    if not a:
        raise ValueError("작성자 이름이 없습니다 — 누가 정했는지 남깁니다.")
    return a


def _vote(param):
    try:
        a, b = int(param.get("a")), int(param.get("b"))
    except (TypeError, ValueError, AttributeError):
        raise ValueError("투표 블록은 A 와 B 가 필요합니다 (B 개 중 A 개 이상).")
    if not (0 < a <= b <= 32):
        raise ValueError("투표 블록은 0 < A ≤ B 여야 합니다.")
    return {"a": a, "b": b}


def set_block(d: Path, page: int, bid: str, choice, author, was="", param=None) -> dict:
    """블록 하나의 종류.  choice None 이면 사람이 정한 것을 지우고 도면 판정으로 돌아간다."""
    author = _author(author)
    with _LOCK:
        data = load(d)
        pg = data["blocks"].setdefault(str(page), {})
        if choice is None:
            old = pg.pop(str(bid), None)
            if not pg:
                data["blocks"].pop(str(page), None)
            data["history"].append({"kind": "block", "page": page, "key": bid, "value": None,
                                    "was": (old or {}).get("choice"), "author": author, "at": _now()})
            _save(d, data)
            return {"removed": bool(old)}
        if choice not in CHOICES:
            raise ValueError(f"모르는 종류입니다: {choice}")
        func, logic, label, prm = CHOICES[choice]
        prm = dict(prm)
        if choice == "VOTE":
            prm.update(_vote(param or {}))
            label = f"{prm['a']}/{prm['b']}"
        ent = {"choice": choice, "func": func, "logic": logic, "label": label, "param": prm,
               "author": author, "at": _now(), "was": str(was or "")[:40]}
        pg[str(bid)] = ent
        data["history"].append({"kind": "block", "page": page, "key": bid, "value": choice,
                                "was": ent["was"], "author": author, "at": ent["at"]})
        _save(d, data)
        return ent


def set_cell(d: Path, page: int, side: str, n: int, value, author, was="") -> dict:
    """왼쪽 행의 FM · 오른쪽 행의 TO.  value None 이면 사람 값을 지우고 도면 글자로 돌아간다."""
    author = _author(author)
    if side not in ("L", "R"):
        raise ValueError("side 는 L(입력 · FM) 또는 R(출력 · TO) 입니다.")
    field = "fm" if side == "L" else "to"
    key = f"{side}:{int(n)}"
    with _LOCK:
        data = load(d)
        pg = data["cells"].setdefault(str(page), {})
        if value is None:
            old = pg.pop(key, None)
            if not pg:
                data["cells"].pop(str(page), None)
            data["history"].append({"kind": field, "page": page, "key": key, "value": None,
                                    "was": (old or {}).get(field), "author": author, "at": _now()})
            _save(d, data)
            return {"removed": bool(old)}
        v = re.sub(r"\s+", " ", str(value)).strip().upper()[:MAX_CELL]
        ent = {field: v, "author": author, "at": _now(), "was": str(was or "")[:MAX_CELL]}
        pg[key] = ent
        data["history"].append({"kind": field, "page": page, "key": key, "value": v, "was": ent["was"],
                                "author": author, "at": ent["at"]})
        _save(d, data)
        return ent


def set_timer(d: Path, page: int, bid: str, sec, author) -> dict:
    author = _author(author)
    with _LOCK:
        data = load(d)
        pg = data["timers"].setdefault(str(page), {})
        if sec is None:
            old = pg.pop(str(bid), None)
            if not pg:
                data["timers"].pop(str(page), None)
            data["history"].append({"kind": "timer", "page": page, "key": bid, "value": None,
                                    "was": (old or {}).get("t"), "author": author, "at": _now()})
            _save(d, data)
            return {"removed": bool(old)}
        try:
            t = float(sec)
        except (TypeError, ValueError):
            raise ValueError("시간은 초(숫자)입니다.")
        if not (0 < t <= 86400):
            raise ValueError("시간은 0 보다 크고 하루(86400초) 이하입니다.")
        ent = {"t": t, "author": author, "at": _now()}
        pg[str(bid)] = ent
        data["history"].append({"kind": "timer", "page": page, "key": bid, "value": t, "author": author, "at": ent["at"]})
        _save(d, data)
        return ent


MARK_KINDS = {"FROM": "FROM (어디서 오는 신호)", "TO": "TO (어디로 가는 신호)", "SHEET": "시트 이름", "GATE": "게이트 종류"}


def _rect(rect):
    try:
        x0, y0, x1, y1 = (float(v) for v in rect)
    except (TypeError, ValueError):
        raise ValueError("사각형(x0, y0, x1, y1)이 없습니다 — 도면에서 끌어 그려 주세요.")
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    if x1 - x0 < 0.5 or y1 - y0 < 0.5:
        raise ValueError("사각형이 너무 작습니다.")
    return [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)]


def set_mark(d: Path, page: int, mid, kind, rect, value, author, n=None, choice=None, param=None) -> dict:
    """마크업 하나 (L24 · P&ID 마크업과 같은 생각) — 도면 위에 사람이 그은 사각형 + 값.

    FROM/TO: 그 사각형이 걸친 표 행(또는 사람이 적은 행 번호)의 FM/TO 를 그 값으로 — 표에 그 행이 없으면 행을 만든다.
    SHEET: 그 장의 시트 이름.  GATE: 사각형 안 블록의 종류 (블록 종류 정하기와 같은 어휘).
    value(·choice) None 이고 mid 가 있으면 지운다 (이력은 남는다)."""
    author = _author(author)
    with _LOCK:
        data = load(d)
        pg = data["marks"].setdefault(str(page), {})
        if mid and value is None and choice is None:
            old = pg.pop(str(mid), None)
            if not pg:
                data["marks"].pop(str(page), None)
            data["history"].append({"kind": "mark", "page": page, "key": mid, "value": None,
                                    "was": (old or {}).get("value") or (old or {}).get("choice"), "author": author, "at": _now()})
            _save(d, data)
            return {"removed": bool(old)}
        kind = str(kind or "").upper()
        if kind not in MARK_KINDS:
            raise ValueError(f"모르는 마크업 종류입니다: {kind}")
        ent = {"kind": kind, "rect": _rect(rect), "author": author, "at": _now()}
        if kind == "GATE":
            if choice not in CHOICES:
                raise ValueError("게이트 종류를 골라 주세요.")
            ent["choice"] = choice
            if choice == "VOTE":
                ent["param"] = _vote(param or {})
        else:
            v = re.sub(r"\s+", " ", str(value or "")).strip().upper()[:MAX_CELL]
            if not v:
                raise ValueError("값을 적어 주세요.")
            ent["value"] = v
        if kind in ("FROM", "TO") and n not in (None, ""):
            try:
                ent["n"] = int(n)
            except (TypeError, ValueError):
                raise ValueError("행 번호는 숫자입니다.")
            if not (0 < ent["n"] < 10000):
                raise ValueError("행 번호가 이상합니다.")
        mid = str(mid or "") or f"M{int(time.time() * 1000) % 10**10:010d}"
        was = pg.get(mid)
        pg[mid] = ent
        data["history"].append({"kind": "mark", "page": page, "key": mid, "value": ent.get("value") or ent.get("choice"),
                                "was": (was or {}).get("value") or (was or {}).get("choice"), "author": author, "at": ent["at"]})
        _save(d, data)
        return {"id": mid, **ent}


def timers_of(ov: dict) -> dict:
    """{쪽(int): {블록: 초}} — 시뮬레이터가 받는 꼴."""
    out = {}
    for pg, m in (ov.get("timers") or {}).items():
        if str(pg).isdigit() and isinstance(m, dict):
            c = {str(b): float(e["t"]) for b, e in m.items() if isinstance(e, dict) and isinstance(e.get("t"), (int, float))}
            if c:
                out[int(pg)] = c
    return out


# ------------------------------------------------------------------ 결과에 얹기

def _memory_roles(s, bid, b):
    """사람이 메모리로 정한 블록 — 단자 역할 (위 칸/위쪽 = SET · Q, 아래 칸/아래쪽 = RESET · /Q)."""
    x0, y0, x1, y1 = b["bbox"]
    mid = (y0 + y1) / 2
    two = len(b.get("cells") or []) >= 2
    outs = [p for p in s["ports"] if p["block"] == bid and p["dir"] == "out"]
    for p in s["ports"]:
        if p["block"] != bid:
            continue
        top = (p.get("cell", 0) == 0) if two else (p["at"][1] <= mid)
        if p["dir"] == "in":
            p["role"] = "set" if top else "reset"
        else:
            p["role"] = "q" if (top or len(outs) == 1) else "qn"


def apply(res: dict, ov: dict) -> dict:
    """결과(새로 읽은 사본)에 사람 값을 얹는다 — 제자리.  FM/TO 를 고쳤으면 from-to 연결을 다시 맞댄다."""
    from . import fromto
    from .analyse import _findings
    by_page = {s["page"]: s for s in res.get("sheets", [])}
    touched = set()
    gate_marks, cells_from_marks = _apply_marks(res, ov, by_page)
    blocks_ov = {k: dict(v) for k, v in (ov.get("blocks") or {}).items() if isinstance(v, dict)}
    for pg, m in gate_marks.items():
        blocks_ov.setdefault(pg, {}).update(m)            # 사각형으로 고른 게이트 종류 — 블록 종류 정하기와 같은 길
    for pg, m in blocks_ov.items():
        s = by_page.get(int(pg)) if str(pg).isdigit() else None
        if s is None:
            continue
        for bid, e in m.items():
            b = s["blocks"].get(bid)
            if b is None or not isinstance(e, dict) or e.get("choice") not in CHOICES:
                continue
            func, logic, label, prm = CHOICES[e["choice"]]
            b["user"] = {"choice": e["choice"], "author": e.get("author", ""), "at": e.get("at", ""),
                         "was_func": b.get("func", ""), "was_logic": b.get("logic", ""), "was_label": b.get("label", "")}
            b["func"], b["logic"] = func, logic
            if e["choice"] == "VOTE":
                b["label"] = e.get("label") or label
            elif logic in ("source", "sink") and e["choice"] not in ("CONST1", "CONST0"):
                b["label"] = b.get("label") or label
            else:
                b["label"] = label
            param = dict(b.get("param") or {})
            for k in ("dominant", "a", "b"):
                param.pop(k, None)
            param.update(e.get("param") or prm)
            b["param"] = param
            if logic == "memory":
                _memory_roles(s, bid, b)
            else:
                for p in s["ports"]:
                    if p["block"] == bid and p.get("role") in ("set", "reset", "q", "qn"):
                        p["role"] = ""
            touched.add(s["page"])
    for pg, m in (ov.get("timers") or {}).items():
        s = by_page.get(int(pg)) if str(pg).isdigit() else None
        if s is None:
            continue
        for bid, e in m.items():
            b = s["blocks"].get(bid)
            if b is not None and isinstance(e, dict) and isinstance(e.get("t"), (int, float)):
                b.setdefault("param", {})["t_user"] = float(e["t"])
                b["param"]["t_user_by"] = e.get("author", "")
    cells = False
    for pg, m in (ov.get("cells") or {}).items():
        s = by_page.get(int(pg)) if str(pg).isdigit() else None
        if s is None:
            continue
        for key, e in m.items():
            side, _, n = key.partition(":")
            if side not in ("L", "R") or not n.isdigit() or not isinstance(e, dict):
                continue
            field = "fm" if side == "L" else "to"
            if field not in e:
                continue
            for coll in (s.get("rows", []), s.get("table", [])):
                for r in coll:
                    if r["side"] == side and r["n"] == int(n):
                        r.setdefault("user", {})[field] = {"was": r.get(field) or "", "author": e.get("author", ""),
                                                           "at": e.get("at", "")}
                        r[field] = e[field]
            cells = True
    cells = cells or cells_from_marks
    for p in touched:
        by_page[p]["findings"] = _findings(by_page[p])
    if touched or cells:
        fromto.check(res["sheets"])
    res["_overrides"] = {"blocks": sum(len(v) for v in (ov.get("blocks") or {}).values()),
                         "cells": sum(len(v) for v in (ov.get("cells") or {}).values()),
                         "timers": sum(len(v) for v in (ov.get("timers") or {}).values()),
                         "marks": sum(len(v) for v in (ov.get("marks") or {}).values())}
    return res


def _overlap(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0.0


def _row_net(s, side, y0, y1):
    """사람이 만든 행이 이어질 선 — 그 행 높이 안에서 LOGIC 영역 그 쪽 가장자리 가까이 끝나는 선 (없으면 None)."""
    lg = s.get("logic") or [0, 0, 0, 0]
    P = s.get("pitch") or 11.5
    edge = lg[0] if side == "L" else lg[2]
    best = None
    for nid, segs in (s.get("order") or {}).items():
        for sg in segs:
            for x, y in ((sg[0], sg[1]), (sg[2], sg[3])):
                if y0 - 0.5 <= y <= y1 + 0.5 and abs(x - edge) <= 3 * P:
                    d = abs(x - edge)
                    if best is None or d < best[0]:
                        best = (d, nid, [x, y])
    return (best[1], best[2]) if best else (None, None)


def _apply_marks(res, ov, by_page):
    """마크업을 결과에 얹는다 — 장마다 `marks` (화면이 그린다) · 시트 이름 · FM/TO 칸 · 게이트 종류.
    → ({쪽: {블록: 블록 종류 항목}}, FM/TO 를 바꿨는가)."""
    gates, changed = {}, False
    for pg, m in (ov.get("marks") or {}).items():
        s = by_page.get(int(pg)) if str(pg).isdigit() else None
        if s is None or not isinstance(m, dict):
            continue
        out = []
        for mid, e in m.items():
            if not isinstance(e, dict) or e.get("kind") not in MARK_KINDS or not isinstance(e.get("rect"), list):
                continue
            rect = e["rect"]
            mk = {"id": mid, **e, "ok": True, "why": ""}
            if e["kind"] == "SHEET":
                mk["was"] = s.get("sheet_no") or ""
                s.setdefault("user_sheet", {"was": s.get("sheet_no") or "", "author": e.get("author", "")})
                s["sheet_no"] = e["value"]
                changed = True
            elif e["kind"] == "GATE":
                hit = max(((_overlap(rect, b["bbox"]), bid) for bid, b in s["blocks"].items()), default=(0, None))
                if not hit[1] or hit[0] <= 0:
                    mk["ok"], mk["why"] = False, "사각형 안에 블록이 없습니다 — 블록을 감싸게 그려 주세요"
                else:
                    func, logic, label, prm = CHOICES[e["choice"]]
                    gates.setdefault(str(pg), {})[hit[1]] = {"choice": e["choice"], "param": e.get("param") or {},
                                                             "label": f"{e['param']['a']}/{e['param']['b']}" if e.get("param") else label,
                                                             "author": e.get("author", ""), "at": e.get("at", "")}
                    mk["block"] = hit[1]
            else:
                side = "L" if e["kind"] == "FROM" else "R"
                field = "fm" if side == "L" else "to"
                cy = (rect[1] + rect[3]) / 2
                tab = [t for t in s.get("table", []) if t["side"] == side]
                t = None
                if e.get("n"):
                    t = next((x for x in tab if x["n"] == e["n"]), None)
                else:
                    t = next((x for x in tab if x.get("y0") is not None and x["y0"] <= cy <= x["y1"]), None)
                if t is None and not e.get("n"):
                    mk["ok"], mk["why"] = False, "이 자리에 표 행이 없습니다 — 행 번호를 적어 주세요"
                    out.append(mk)
                    continue
                if t is None:                      # 표가 그 행을 못 읽었다 — 사람이 적은 행을 만든다
                    t = {"n": e["n"], "side": side, "y0": rect[1], "y1": rect[3], "desc": "", "kks": "",
                         field + "_box": rect, field: "", "user_row": True}
                    s.setdefault("table", []).append(t)
                    s["table"].sort(key=lambda x: (x["side"], x["n"]))
                    mk["made_row"] = True
                n = t["n"]
                mk["n"] = n
                r = next((x for x in s["rows"] if x["side"] == side and x["n"] == n), None)
                if r is None:
                    net, at = _row_net(s, side, t.get("y0", rect[1]), t.get("y1", rect[3]))
                    lg = s.get("logic") or rect
                    r = {"n": n, "side": side, "net": net, "at": at or [lg[0] if side == "L" else lg[2], cy],
                         "y0": t.get("y0"), "y1": t.get("y1"), "desc": t.get("desc", ""), "kks": t.get("kks", ""),
                         "user_row": True}
                    s["rows"].append(r)
                    mk["net"] = net
                for x in (t, r):
                    x.setdefault("user", {})[field] = {"was": x.get(field) or "", "author": e.get("author", ""),
                                                       "at": e.get("at", ""), "mark": mid}
                    x[field] = e["value"]
                changed = True
            out.append(mk)
        s["marks"] = out
    return gates, changed
