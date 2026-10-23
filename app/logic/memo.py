"""LOGIC 시트 메모 — P&ID 의 장별 메모 · 핀 메모(hotfix63 · 76 · 77)와 같은 규율 (L8).

  `{data}/logic/<job>/memo.json` = {"items": [...]}
  항목 = {id, page, sheet_no, text, author, time, at: [x, y] | None, done, hidden, history: [{text, author, time}]}
         L30 — rect: [x0, y0, x1, y1] (끌어서 두른 영역 · at 은 그 오른쪽 위) · block: 블록 이름 (연산자 판에서 단 메모)

  * 지우지 않는다 — 글을 고치면 앞 글이 history 로 · '완료'·'숨김' 은 표시뿐.
  * 자리(at)는 그 장의 PDF 좌표 (오버레이와 같은 좌표계).  없으면 장 메모.
  * 작성자는 자기신고 (대시보드 로그인 이름 · 이 브라우저에 기억된 이름).  비우면 저장하지 않는다.
  * 판정에 닿지 않는다 — 분석 결과(result.json)는 한 글자도 안 바뀐다.
"""
from __future__ import annotations

import json
import threading
import time
import re
import uuid
from pathlib import Path

from . import store

_LOCK = threading.Lock()
MAX_TEXT = 4000


def _path(d: Path) -> Path:
    return d / "memo.json"


def load(d: Path) -> dict:
    try:
        data = json.loads(_path(d).read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            return data
    except Exception:
        pass
    return {"items": []}


def _save(d: Path, data: dict):
    store._atomic(_path(d), json.dumps(data, ensure_ascii=False, indent=1))


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _clean_at(at):
    if at is None:
        return None
    if (isinstance(at, (list, tuple)) and len(at) == 2
            and all(isinstance(v, (int, float)) and v == v and abs(v) < 1e6 for v in at)):
        return [round(float(at[0]), 2), round(float(at[1]), 2)]
    raise ValueError("자리(at)는 [x, y] 숫자 둘이어야 합니다.")


def _clean_rect(rect):
    if rect is None:
        return None
    if isinstance(rect, (list, tuple)) and len(rect) == 4 and all(isinstance(v, (int, float)) and v == v and abs(v) < 1e6 for v in rect):
        x0, x1 = sorted((float(rect[0]), float(rect[2])))
        y0, y1 = sorted((float(rect[1]), float(rect[3])))
        return [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)]
    raise ValueError("영역(rect)은 [x0, y0, x1, y1] 숫자 넷이어야 합니다.")


def add(d: Path, page: int, sheet_no: str, text: str, author: str, at=None, rect=None, block=None, mid=None) -> dict:
    text = (text or "").strip()
    author = (author or "").strip()
    if not text:
        raise ValueError("메모 내용이 비어 있습니다.")
    if not author:
        raise ValueError("작성자 이름이 없습니다.")
    # hotfix108 — 절전모드에서 화면이 미리 정한 id (꼴이 맞을 때만 · 같은 보관본을 두 번 보내면 하나)
    mid = mid if isinstance(mid, str) and re.match(r"^[0-9a-z]{8,24}$", mid) else uuid.uuid4().hex[:10]
    item = {"id": mid, "page": int(page), "sheet_no": str(sheet_no or ""),
            "text": text[:MAX_TEXT], "author": author[:80], "time": _now(), "at": _clean_at(at),
            "done": False, "hidden": False, "history": []}
    rect = _clean_rect(rect)
    if rect:
        item["rect"] = rect
        if item["at"] is None:
            item["at"] = [rect[2], rect[1]]
    if block:
        item["block"] = str(block)[:24]
    with _LOCK:
        data = load(d)
        for old in data["items"]:
            if old.get("id") == item["id"]:
                return old
        data["items"].append(item)
        _save(d, data)
    return item


def update(d: Path, mid: str, author: str, text=None, done=None, hidden=None) -> dict:
    author = (author or "").strip()
    if not author:
        raise ValueError("작성자 이름이 없습니다.")
    with _LOCK:
        data = load(d)
        for it in data["items"]:
            if it.get("id") != mid:
                continue
            if text is not None:
                text = str(text).strip()
                if not text:
                    raise ValueError("메모 내용이 비어 있습니다 — 지우지 않습니다 (숨김을 쓰세요).")
                if text != it["text"]:
                    it.setdefault("history", []).append({"text": it["text"], "author": it["author"], "time": it["time"]})
                    it.update(text=text[:MAX_TEXT], author=author[:80], time=_now())
            if done is not None:
                it["done"] = bool(done)
            if hidden is not None:
                it["hidden"] = bool(hidden)
            _save(d, data)
            return it
    raise KeyError(mid)
