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
"""
from __future__ import annotations

import json
import os
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
