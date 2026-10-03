"""장 도면번호 — **도면이 우리가 읽을 수 있는 형태로 말하지 않을 때
사람이 한 번 적는 자리** (45회차 · §9 ⑤ · §10 3급).

## 왜 있는가 — 실측

UAD(AL DHAFRA) 32장 중 **여덟 장이 행 0**이고, 원인은 검출이 아니라
**그 장이 분석 대상이 아니었다**는 것이다.

    p11~p15   글자가 하나도 없다 (텍스트 0~28낱말 · SHX 주석 0 · 도형 1.6~2.1만)
    p16~p18   본문은 TrueType 945~1,039낱말인데 **타이틀블록 열만 획**이다
              (x > 984 의 낱말이 0개)

`parse_drawing_no` 는 그 칸의 **낱말**을 찾는다.  칸이 획으로 플롯돼 있으면
낱말이 없으므로 `None` 이고, `classify_page(title, None)` 이 `UNKNOWN` 을 내며,
파이프라인의 `targets` 에서 그 장이 빠진다.  **p16·p17·p18 은 본문을 읽을 수
있는데도 번호 한 칸 때문에 통째로 빠졌다.**

## 획을 읽어 보려 한 기록 (45회차 · 실패)

그 칸의 글자는 도면에 **인쇄돼 있다** — 사람 눈에는 보인다.  그래서 먼저
글리프로 읽으려 했고, 세 가지를 실측해 **전부 안 된다**는 결론을 냈다.

    ① 도면이 스스로 라벨한 획 글자로 사전을 세운다 (`AutoCAD SHX Text` 주석
       200개 → 38자 · 20초).  **사전은 선다.**
    ② 그 사전으로 타이틀블록 칸을 읽으면 — 같은 문서·같은 SHX 글꼴인데도
       21자 중 절반이 틀린다.  `_normalise` 가 종횡비를 버리고(0↔O), 획 굵기가
       크기에 따라 달라진다(본문 4pt ↔ 타이틀블록 10pt 인데 hairline 은 어느
       크기에서나 1px 이라 상대 굵기가 2.5배 다르다).
    ③ 문서가 **글자로** 인쇄한 도면번호 52종을 후보로 두고 칸을 그 후보들에
       맞춰 고르면 — 정답이 있는 아홉 장에서 **1/9**만 맞고, 1위와 2위의 점수
       차가 0.077 ↔ 0.080 으로 **의미가 없다**.

즉 이 문서에서 획으로 그린 타이틀블록 값은 지금 도구로 읽히지 않는다.
§9 ⑤ 그대로 — **①~④ 에서 못 읽으면 사람에게 묻고 프로젝트에 저장한다.**

## 읽는 순서 — 사람은 도면을 이기지 않는다

    ① 그 장의 타이틀블록 낱말 (`parse_drawing_no`)   ← 읽히면 여기서 끝
    ② **사람이 적은 값 (여기)**
    ③ 아무 것도 없으면 그 장은 예전처럼 대상에서 빠진다

그래서 **도면번호가 전부 읽히는 문서는 이 경로에 닿을 수 없다** — AL NOUF1
58장 · SADARA 9장 · TC2 60장은 빈 칸이 0개다(실측).  사람이 값을 넣어도
지문이 움직이지 않아야 하고 `tests/test_sheet_numbers.py` 가 못박는다.

## 자리와 규율 — 31회차 승수 지정과 같다

    {data_dir}/projects/{프로젝트}/sheet_drawing_no.json

* **소스 트리가 아니다** (갈음 때 사라지면 안 된다).
* **프로젝트 단위**이고 리비전 사이에 그대로 간다 — 도면번호는 개정으로
  바뀌는 값이 아니다.  ⚠ 다만 장 **순서**는 개정에서 바뀔 수 있으므로 값에
  `set_at`·`origin_job` 을 남기고, 화면이 그 장을 함께 보여 사람이 확인한다.
* **작성자 없이 저장할 수 없다** (팀이 공유하는 값이다).
* **끌 수 있다** — `enabled: false` 면 이 파일이 없던 때와 정확히 같아진다
  (읽는 곳이 `table()` 하나이므로).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

FILENAME = "sheet_drawing_no.json"
VERSION = 1

# 검토 사유 — 도면에서 읽은 번호와 구분한다.  산출물의 P&ID No. 가 사람이 적은
# 값이라는 사실은 그 행을 보는 사람이 알아야 한다.
REVIEW_CODE = "DRAWING_NO_BY_USER"
REASON = ("%d 장의 도면번호 '%s' 는 도면에서 읽은 값이 아니라 사람이 적은 "
          "값입니다 (%s · %s) — 이 장의 타이틀블록은 글자가 아니라 획으로 "
          "그려져 있어 읽히지 않습니다")


def path_for(data_dir, project: str) -> Path:
    from app import revisions
    return revisions.project_dir(Path(data_dir), project) / FILENAME


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load(data_dir, project: str) -> dict:
    """저장된 지정값 한 벌.  없으면 빈 구조 (파일을 만들지 않는다)."""
    if not project:
        return {"version": VERSION, "enabled": True, "sheets": {}}
    p = path_for(data_dir, project)
    if not p.exists():
        return {"version": VERSION, "enabled": True, "sheets": {}}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"version": VERSION, "enabled": True, "sheets": {}}
    data.setdefault("version", VERSION)
    data.setdefault("enabled", True)
    data.setdefault("sheets", {})
    return data


def save(data_dir, project: str, data: dict) -> Path:
    p = path_for(data_dir, project)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True,
                            indent=1) + "\n", encoding="utf-8")
    return p


def table(data_dir, project: str) -> dict:
    """파이프라인에 넘길 `{장번호: 도면번호}`.  **읽는 곳은 여기 하나다.**"""
    data = load(data_dir, project)
    if not data.get("enabled", True):
        return {}
    out = {}
    for page, rec in (data.get("sheets") or {}).items():
        try:
            no = int(page)
        except (TypeError, ValueError):
            continue
        val = str((rec or {}).get("drawing_no") or "").strip()
        if no >= 1 and val:
            out[no] = val
    return out


def set_sheet(data_dir, project: str, *, page: int, drawing_no: str,
              author: str = "", note: str = "", job_id: str = "") -> dict:
    """한 장의 도면번호를 적는다.  **`author` 없이 넣을 수 없다.**"""
    project = (project or "").strip()
    if not project:
        raise ValueError("프로젝트에 묶이지 않은 분석에는 도면번호를 적을 수 없습니다")
    no = int(page)
    if no < 1:
        raise ValueError("장 번호는 1 이상의 정수입니다")
    value = str(drawing_no or "").strip()
    if not value:
        raise ValueError("도면번호가 비어 있습니다")
    author = (author or "").strip()
    if not author:
        raise ValueError("작성자를 적어야 저장됩니다 (팀이 공유하는 값입니다)")
    data = load(data_dir, project)
    data["sheets"][str(no)] = {
        "drawing_no": value,
        "author": author,
        "note": (note or "").strip(),
        "set_at": _now(),
        "origin_job": job_id or "",
    }
    save(data_dir, project, data)
    return data["sheets"][str(no)]


def clear_sheet(data_dir, project: str, page) -> bool:
    """되돌린다.  지운 뒤에는 그 장이 지정되지 않았던 때와 같아진다."""
    data = load(data_dir, project)
    key = str(int(page))
    if key not in (data.get("sheets") or {}):
        return False
    data["sheets"].pop(key)
    save(data_dir, project, data)
    return True


def set_enabled(data_dir, project: str, enabled: bool) -> dict:
    data = load(data_dir, project)
    data["enabled"] = bool(enabled)
    save(data_dir, project, data)
    return data
