"""사람이 정한 값 — 게이트 종류 · FM/TO 칸 · 타이머 시간 (L22).

  `{data}/logic/<job>/overrides.json` = {
      "blocks": {쪽: {블록: {choice, func, logic, label, param, author, at, was}}},
      "cells":  {쪽: {"L:12": {"fm": 값, author, at, was}, "R:30": {"to": 값, ...}}},
      "timers": {쪽: {블록: {t: 초, author, at}}},
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
    return {"blocks": {}, "cells": {}, "timers": {}, "history": []}


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
    return any(ov.get(k) for k in ("blocks", "cells", "timers"))


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
    for pg, m in (ov.get("blocks") or {}).items():
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
    for p in touched:
        by_page[p]["findings"] = _findings(by_page[p])
    if touched or cells:
        fromto.check(res["sheets"])
    res["_overrides"] = {"blocks": sum(len(v) for v in (ov.get("blocks") or {}).values()),
                         "cells": sum(len(v) for v in (ov.get("cells") or {}).values()),
                         "timers": sum(len(v) for v in (ov.get("timers") or {}).values())}
    return res
