"""장별 메모 (hotfix63) — 도면 한 장마다 사람이 적는 메모장.  **같은 프로젝트의 모든 Rev 에서 이력과 함께 보인다.**

사용자: *"P&ID 각 Page 별로 사용자가 Note 를 입력할 수 있도록 메모장 Type 의 Note 칸을 만들고 이 Note 는 같은
Project 의 다른 Rev. 에 모두 이력관리와 볼 수 있도록 한다."*

## 열쇠는 쪽 번호가 아니라 도면번호

개정 때 장 순서가 바뀌는 것이 개정의 흔한 모습이다 (13회차) — 쪽 번호로 붙이면 Rev.B 에서 남의 장 메모가 뜬다.
그래서 열쇠는 그 장의 **도면번호**이고, 도면번호를 못 읽은 장만 `page:<n>` 이다 (그 열쇠는 그 분석 안에서만
뜻이 있다 — 화면이 그렇게 말한다).  hotfix38 이 찾은 **도면번호가 바뀐 장**(`30GKC10-M05-0003` → `-0203`)은
장부(`sheets.renumbered`)의 옛 번호로도 찾아 함께 보인다.

## 이력 — 지우지 않고 쌓는다

저장 한 번이 판 하나다 (`{text, author, at, revision, job_id, page_no}`).  지금 메모는 가장 늦은 판이고, 비워서
저장하면 "비움" 판이 하나 더 쌓일 뿐 앞 판은 남는다.  작성자는 자기신고다 (13회차) — 비우면 비운 채로 적고 화면이
"이름 없음" 이라고 쓴다.

## 자리

    {data_dir}/projects/{프로젝트}/sheet_notes.json        프로젝트에 묶인 분석
    {data_dir}/loose_notes/{job_id}.json                    묶이지 않은 분석 (그 분석에서만)

소스 트리가 아니다 (갈음 때 사라지면 안 된다).  판정·지문·Excel 에 닿지 않는다.

## 위치 메모 (hotfix76) — 도면의 한 자리에 붙는 메모

사용자: *"메모가 pdf 상에 어떤 곳에 대한 메모인지, 마이크로소프트 프로그램의 메모 기능과 같이 메모를 클릭하면
pdf 위치를 보여주고 메모표기를 하는 기능."*  메모장(위)은 장 하나에 한 판씩 쌓이는 글이고, 위치 메모는 **장 안의
자리 하나**에 붙는 글이다 — Word 의 메모처럼 여럿이 나란히 산다.  같은 파일의 `pins` 아래 같은 열쇠(도면번호)로
두므로 다른 Rev 에서도 보이고, 도면번호가 바뀐 장도 같은 길로 따라간다.

* 자리는 **그 장의 PDF 좌표(pt)** 다 — 오버레이 상자(`rect`)와 같은 좌표계.  그 장의 종이 크기(`page_w`·`page_h`)를
  함께 적어, 다른 Rev 의 종이 크기가 다르면 비례로 옮겨 그린다.  다른 Rev 에서 단 메모는 도면이 바뀌었을 수
  있으므로 화면이 그렇게 말한다 (자리를 지어내지 않는다 — 옮기지도 않는다).
* **지우지 않는다** — 글을 고치면 앞 글이 `history` 에 남고, '완료' 와 '숨김' 은 표시(`resolved`·`hidden`)일
  뿐 기록은 그대로다 (위 메모장과 같은 규율).
"""
from __future__ import annotations

import json
import os
import secrets
import threading
import time
from pathlib import Path

_LOCK = threading.Lock()
MAX_TEXT = 20000            # 메모장 한 판의 상한 (글자) — 실수로 붙인 거대한 글을 막는 자리일 뿐


def _path(data_dir: Path, project: str, job_id: str) -> Path:
    if project:
        from app import revisions
        return revisions.project_dir(Path(data_dir), project) / "sheet_notes.json"
    return Path(data_dir) / "loose_notes" / f"{job_id}.json"


def key_of(drawing_no: str, page_no: int) -> str:
    d = (drawing_no or "").strip()
    return d if d else f"page:{int(page_no)}"


def load(data_dir: Path, project: str, job_id: str) -> dict:
    p = _path(data_dir, project, job_id)
    from app import jsonstore
    try:
        data = jsonstore.read(p, {}, what="장별 메모")
    except OSError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("sheets", {})
    return data


def _save(data_dir: Path, project: str, job_id: str, data: dict) -> None:
    p = _path(data_dir, project, job_id)
    from app import jsonstore
    jsonstore.write(p, data)


def entries(data: dict, keys) -> list:
    """열쇠 여럿(지금 도면번호 + 옛 도면번호)의 판을 시각순으로 (가장 늦은 것이 맨 뒤)."""
    out = []
    for k in keys:
        for e in (data.get("sheets") or {}).get(k) or []:
            out.append({**e, "key": k})
    return sorted(out, key=lambda e: (e.get("at") or 0, e.get("seq") or 0))


def add(data_dir: Path, project: str, job_id: str, *, key: str, text: str, author: str,
        revision: str, page_no: int, drawing_no: str) -> dict:
    text = (text or "").replace("\r\n", "\n")
    if len(text) > MAX_TEXT:
        raise ValueError(f"메모가 너무 깁니다 ({len(text)}자 — {MAX_TEXT}자까지)")
    with _LOCK:
        data = load(data_dir, project, job_id)
        lst = data["sheets"].setdefault(key, [])
        seq = (max((e.get("seq") or 0) for e in lst) + 1) if lst else 1
        rec = {"seq": seq, "text": text, "author": (author or "").strip(), "at": time.time(),
               "revision": revision or "", "job_id": job_id, "page_no": int(page_no),
               "drawing_no": drawing_no or ""}
        lst.append(rec)
        _save(data_dir, project, job_id, data)
    return rec


# --------------------------------------------------------------------------
# 위치 메모 (hotfix76)
# --------------------------------------------------------------------------

PIN_STATES = ("open", "resolved", "hidden")


def _clean_rect(rect, page_w: float, page_h: float) -> list:
    """사람이 그은 사각형을 그 장 안으로 · 순서 맞춤.  숫자 넷이 아니면 ValueError."""
    try:
        x0, y0, x1, y1 = (float(v) for v in rect)
    except (TypeError, ValueError):
        raise ValueError("메모 자리는 숫자 넷 [x0, y0, x1, y1] 이어야 합니다")
    if any(v != v or v in (float("inf"), float("-inf")) for v in (x0, y0, x1, y1)):
        raise ValueError("메모 자리에 숫자가 아닌 값이 있습니다")
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    if page_w and page_h:
        x0, x1 = max(0.0, min(x0, page_w)), max(0.0, min(x1, page_w))
        y0, y1 = max(0.0, min(y0, page_h)), max(0.0, min(y1, page_h))
    return [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)]


def pins(data: dict, keys) -> list:
    """열쇠 여럿의 위치 메모를 단 순서대로."""
    out = []
    for k in keys:
        for e in (data.get("pins") or {}).get(k) or []:
            out.append({**e, "key": k})
    return sorted(out, key=lambda e: (e.get("at") or 0, e.get("id") or ""))


def add_pin(data_dir: Path, project: str, job_id: str, *, key: str, rect, text: str, author: str,
            revision: str, page_no: int, drawing_no: str, page_w: float, page_h: float) -> dict:
    text = (text or "").replace("\r\n", "\n").strip()
    if not text:
        raise ValueError("메모 글이 비어 있습니다")
    if len(text) > MAX_TEXT:
        raise ValueError(f"메모가 너무 깁니다 ({len(text)}자 — {MAX_TEXT}자까지)")
    rect = _clean_rect(rect, page_w, page_h)
    with _LOCK:
        data = load(data_dir, project, job_id)
        lst = data.setdefault("pins", {}).setdefault(key, [])
        now = time.time()
        rec = {"id": f"P{int(now * 1000):x}{secrets.token_hex(2)}", "rect": rect,
               "page_w": float(page_w or 0), "page_h": float(page_h or 0),
               "text": text, "author": (author or "").strip(), "at": now,
               "revision": revision or "", "job_id": job_id, "page_no": int(page_no),
               "drawing_no": drawing_no or "", "state": "open", "history": []}
        lst.append(rec)
        _save(data_dir, project, job_id, data)
    return {**rec, "key": key}


def update_pin(data_dir: Path, project: str, job_id: str, *, keys, pin_id: str, author: str,
               revision: str, text=None, state=None) -> dict:
    """글을 고치거나(앞 글은 `history` 로) 상태를 바꾼다 (open · resolved · hidden).  없으면 KeyError."""
    if state is not None and state not in PIN_STATES:
        raise ValueError(f"상태는 {', '.join(PIN_STATES)} 중 하나입니다")
    if text is not None:
        text = str(text).replace("\r\n", "\n").strip()
        if not text:
            raise ValueError("메모 글이 비어 있습니다 — 지우려면 '숨김' 을 쓰세요 (기록은 남습니다)")
        if len(text) > MAX_TEXT:
            raise ValueError(f"메모가 너무 깁니다 ({len(text)}자 — {MAX_TEXT}자까지)")
    with _LOCK:
        data = load(data_dir, project, job_id)
        for k in keys:
            for rec in (data.get("pins") or {}).get(k) or []:
                if rec.get("id") != pin_id:
                    continue
                now = time.time()
                if text is not None and text != rec.get("text"):
                    rec.setdefault("history", []).append(
                        {"text": rec.get("text"), "author": rec.get("author"), "at": rec.get("edited_at") or rec.get("at"),
                         "revision": rec.get("edited_revision") or rec.get("revision")})
                    rec["text"] = text
                    rec["edited_at"], rec["edited_by"], rec["edited_revision"] = now, (author or "").strip(), revision or ""
                if state is not None and state != rec.get("state", "open"):
                    rec.setdefault("history", []).append(
                        {"state": rec.get("state", "open"), "to": state, "author": (author or "").strip(),
                         "at": now, "revision": revision or ""})
                    rec["state"] = state
                    rec["state_at"], rec["state_by"] = now, (author or "").strip()
                _save(data_dir, project, job_id, data)
                return {**rec, "key": k}
    raise KeyError(pin_id)
