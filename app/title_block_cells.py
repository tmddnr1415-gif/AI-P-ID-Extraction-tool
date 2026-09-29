"""타이틀블록 칸 — **도면이 캡션으로도 구조로도 말하지 않을 때 사람이 도면 위에서
한 번 그어 두는 자리** (hotfix29 · §9 ⑤ · §10 3급).

## 왜 있는가

새 회사 양식이 올 때마다 `TitleBlockUnreadable` 로 멈추면 프로그램의 실효성이
없다 (현장: QFE 93장).  엔진은 이제 캡션 표기 여러 벌(`derive_layout.CAPTION_VOCAB`)과
구조(되풀이 번호 · 되풀이 제목)로 칸을 찾지만, 글자가 획으로만 그려졌거나 양식이
그 어느 규칙에도 안 맞는 문서는 남는다.  그때 사람이 실패 화면에서 **도면 위에
사각형 하나를 끌면** 그 칸이 그 프로젝트의 사실로 저장되고, 다음 분석부터 그 칸을
읽는다 — `project_*.yaml` 에 `title_block.*` 좌표를 손으로 적던 일(22회차
`measured_config`)을 화면에서 한 번에 하는 것이다.

## 읽는 순서

    ① 그 도면이 답한 칸 (캡션 · 구조)      ← `derive_layout.derive`
    ② **사람이 그은 칸 (여기)**            ← 같은 종이 크기에서만 · 도면이 답한 칸을 덮는다
    ③ 프로젝트 설정 `title_block.*`

②가 ①을 덮는 이유: 이 값은 행의 값이 아니라 **어디를 읽을지**이고, 프로젝트가
적은 `title_block.*` 좌표가 이기는 것과 같은 자격이다 (`_fit_layout` — 프로필이
적은 기하는 그대로 선다).  다만 도면이 답한 칸이 있으면 화면이 그것을 먼저
보여 주고, 사람이 그어야 덮인다.

## 자리와 규율 — 31회차 승수 · 45회차 도면번호 지정과 같다

    {data_dir}/projects/{프로젝트}/title_block_cells.json

* 프로젝트 단위 · 리비전 사이에 그대로 간다 (양식은 개정으로 바뀌지 않는다).
* **좌표는 그 종이의 것이다** — 그은 장의 쪽 크기를 같이 적고, 다른 크기의 문서에는
  얹지 않는다 (hotfix20: 같은 프로젝트라도 A1↔A0 좌표는 다른 것).
* **작성자 없이 저장할 수 없다** · `enabled: false` 면 이 파일이 없던 때와 같다.
* 읽는 곳은 `cells()` 하나다.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

FILENAME = "title_block_cells.json"
VERSION = 1
# 사람이 그을 수 있는 칸 — 파이프라인이 실제로 읽는 네 자리.  (이력 표는 모양으로
# 유도되므로 여기 없다.)
CELLS = ("dwg_no_region", "title_region", "rev_box", "sheet_box")


def path_for(data_dir, project: str) -> Path:
    from app import revisions
    return revisions.project_dir(Path(data_dir), project) / FILENAME


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _empty() -> dict:
    return {"version": VERSION, "enabled": True, "cells": {}, "size": None,
            "author": "", "note": "", "set_at": "", "origin_job": "", "page_no": None}


def load(data_dir, project: str) -> dict:
    if not project:
        return _empty()
    p = path_for(data_dir, project)
    if not p.exists():
        return _empty()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return _empty()
    base = _empty()
    base.update({k: v for k, v in data.items() if k in base})
    return base


def save(data_dir, project: str, data: dict) -> Path:
    p = path_for(data_dir, project)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
                 encoding="utf-8")
    return p


def cells(data_dir, project: str) -> dict:
    """파이프라인에 넘길 모양 — `{"cells": {이름: [x0,y0,x1,y1]}, "size": [W,H], "who": …}`.
    **읽는 곳은 여기 하나다.**  꺼져 있거나 비어 있으면 `{}`."""
    data = load(data_dir, project)
    if not data.get("enabled", True):
        return {}
    out = {}
    for name in CELLS:
        v = (data.get("cells") or {}).get(name)
        if v and len(v) == 4:
            out[name] = [float(x) for x in v]
    if not out or not data.get("size"):
        return {}
    who = " · ".join(b for b in (data.get("author") or "이름 없음",
                                 (data.get("set_at") or "")[:10], data.get("note") or "") if b)
    return {"cells": out, "size": [float(v) for v in data["size"]], "who": who,
            "author": data.get("author") or "", "set_at": data.get("set_at") or ""}


def set_cells(data_dir, project: str, *, cells_in: dict, size, page_no: int,
              author: str = "", note: str = "", job_id: str = "") -> dict:
    """칸을 적는다.  도면번호 칸은 필수이고 **`author` 없이 넣을 수 없다.**"""
    project = (project or "").strip()
    if not project:
        raise ValueError("프로젝트에 묶이지 않은 분석에는 타이틀블록 칸을 저장할 자리가 없습니다")
    author = (author or "").strip()
    if not author:
        raise ValueError("작성자를 적어야 저장됩니다 (팀이 공유하는 값입니다)")
    clean = {}
    for name in CELLS:
        v = (cells_in or {}).get(name)
        if not v:
            continue
        try:
            x0, y0, x1, y1 = (float(t) for t in v)
        except Exception:
            raise ValueError(f"{name}: 사각형은 [x0, y0, x1, y1] 이어야 합니다")
        if x1 <= x0 or y1 <= y0:
            raise ValueError(f"{name}: 사각형의 크기가 0 입니다")
        clean[name] = [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)]
    if "dwg_no_region" not in clean:
        raise ValueError("도면번호 칸은 반드시 그어야 합니다")
    try:
        W, H = (float(v) for v in size)
    except Exception:
        raise ValueError("그은 장의 쪽 크기가 필요합니다")
    data = load(data_dir, project)
    data.update({"cells": clean, "size": [round(W, 1), round(H, 1)], "author": author,
                 "note": (note or "").strip(), "set_at": _now(), "origin_job": job_id or "",
                 "page_no": int(page_no) if page_no else None, "enabled": True})
    save(data_dir, project, data)
    return data


def clear(data_dir, project: str) -> bool:
    p = path_for(data_dir, project) if project else None
    if not p or not p.exists():
        return False
    p.unlink()
    return True


def set_enabled(data_dir, project: str, enabled: bool) -> dict:
    data = load(data_dir, project)
    data["enabled"] = bool(enabled)
    save(data_dir, project, data)
    return data
