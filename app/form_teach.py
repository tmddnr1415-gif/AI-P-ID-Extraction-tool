"""도면 가르치기 — **새 양식에서 프로그램이 못 찾은 자리를 사람이 도면 위에서 한 번
짚어 두는 곳** (hotfix85 · §9 ⑤ · §10 3급).

## 왜 있는가

새 회사 양식이 오면 프로그램이 멈추거나(`TitleBlockUnreadable` · `LegendUnavailable` ·
`BubblesUnreadable`) 조용히 덜 읽는다(NOTES 자리).  hotfix84 까지는 그때마다 코드를
고쳤다 — 프로젝트마다 다르게 그리므로 끝이 없다.  여기서는 분석이 멈춘 화면에서
**사람이 도면을 보고 사각형을 그어** 그 자리를 알려 주고, 프로그램이 그 자리에서
읽는다.  지어내지 않는다: 사람은 *어디를 읽을지* 와 *어떻게 생겼는지(예시)* 만 주고,
값은 여전히 도면에서 읽는다.

## 가르치는 것

    drawing   도면 영역 한 칸 (테두리 안쪽 — 테두리를 프로그램이 못 찾았을 때)
    notes     NOTES 영역 한 칸 (별표 뜻 · 공급자 · "유닛 몇 개" 노트를 읽는 자리)
    legend_page  "이 장이 범례입니다" — 장 목록 `[{page_no, size}]` (범례가 여러 장인 문서 · 머리말은 그 장들에서
                 인쇄된 그대로 또는 핵심 낱말로 찾는다).  옛 꼴(장 하나 `{page_no, size}`)도 읽는다
    legend    범례 장의 칸 머리말 — `LINE VALVES` · `VALVES ACTUATORS` · `ELECTRIC SIGNAL`
              (프로그램이 그 낱말로 찾는 칸을 이 문서는 다른 말로 인쇄했을 때)
    bubbles   계기 버블 예시 2~3개 (그 모양과 크기로 나머지를 찾는다)

타이틀블록 칸은 hotfix29 의 `title_block_cells.json` 이 맡는다 (같은 화면에서 긋는다).

## 자리와 규율 — 31회차 승수 · 45회차 도면번호 · hotfix29 칸 지정과 같다

    {data_dir}/projects/{프로젝트}/form_teach.json

* 프로젝트 단위 · 리비전 사이에 그대로 간다.
* **좌표는 그 장의 종이 것이다** — 항목마다 그은 장의 쪽 크기를 적고, 같은 번호의 장이
  같은 크기일 때만 쓴다.
* **작성자 없이 저장할 수 없다** · `enabled: false` 면 이 파일이 없던 때와 같다.
* 읽는 곳은 `for_pipeline()` 하나다.  **사람 값이 없으면 빈 값**이고, 빈 값은 이 기능이
  없던 때와 정확히 같다 (회귀 하네스는 넘기지 않는다).
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.jsonstore import serialized as _serialized

FILENAME = "form_teach.json"
VERSION = 1
# 범례 칸 머리말 — 엔진이 찾는 **인쇄 낱말** 그대로가 열쇠다 (legend_rules · pipe_graph).
LEGEND_KEYS = ("LINE VALVES", "VALVES ACTUATORS", "ELECTRIC SIGNAL")
LEGEND_LABEL = {"LINE VALVES": "범례 — 밸브 칸 제목",
                "VALVES ACTUATORS": "범례 — 액추에이터 칸 제목",
                "ELECTRIC SIGNAL": "범례 — 전기 신호선 줄 이름"}
MAX_BUBBLES = 8


def path_for(data_dir, project: str) -> Path:
    from app import revisions
    return revisions.project_dir(Path(data_dir), project) / FILENAME


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _empty() -> dict:
    return {"version": VERSION, "enabled": True, "drawing": None, "notes": None, "legend": {},
            "legend_page": None, "bubbles": [],
            "author": "", "set_at": "", "origin_job": "", "note": ""}


def load(data_dir, project: str) -> dict:
    if not project:
        return _empty()
    p = path_for(data_dir, project)
    if not p.exists():
        return _empty()
    from app import jsonstore
    data = jsonstore.read(p, None, what="도면 가르치기")
    if not isinstance(data, dict):
        return _empty()
    base = _empty()
    base.update({k: v for k, v in data.items() if k in base})
    if not isinstance(base.get("legend"), dict):
        base["legend"] = {}
    if not isinstance(base.get("bubbles"), list):
        base["bubbles"] = []
    return base


def save(data_dir, project: str, data: dict) -> Path:
    from app import jsonstore
    return jsonstore.write(path_for(data_dir, project), data)


def _rect(v, what: str) -> list:
    try:
        x0, y0, x1, y1 = (float(t) for t in v)
    except Exception:
        raise ValueError(f"{what}: 사각형은 [x0, y0, x1, y1] 이어야 합니다")
    if x1 - x0 < 1.0 or y1 - y0 < 1.0:
        raise ValueError(f"{what}: 사각형의 크기가 너무 작습니다")
    return [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)]


def _item(v, what: str) -> dict:
    """{page_no, rect, size} 한 칸."""
    if not isinstance(v, dict):
        raise ValueError(f"{what}: {{page_no, rect, size}} 가 필요합니다")
    try:
        page_no = int(v.get("page_no"))
        W, H = (float(t) for t in v.get("size"))
    except Exception:
        raise ValueError(f"{what}: 그은 장의 번호와 쪽 크기가 필요합니다")
    return {"page_no": page_no, "rect": _rect(v.get("rect"), what),
            "size": [round(W, 1), round(H, 1)]}


def has_any(data: dict) -> bool:
    return bool(data.get("drawing") or data.get("notes") or data.get("legend") or data.get("legend_page")
                or data.get("bubbles"))


def for_pipeline(data_dir, project: str) -> dict:
    """파이프라인에 넘길 모양.  **읽는 곳은 여기 하나다.**  꺼져 있거나 비었으면 `{}`."""
    data = load(data_dir, project)
    if not data.get("enabled", True) or not has_any(data):
        return {}
    who = " · ".join(b for b in (data.get("author") or "이름 없음",
                                 (data.get("set_at") or "")[:10]) if b)
    return {"drawing": data.get("drawing"), "notes": data.get("notes"), "legend_page": data.get("legend_page"),
            "legend": dict(data.get("legend") or {}),
            "bubbles": list(data.get("bubbles") or []), "who": who,
            "author": data.get("author") or "", "set_at": data.get("set_at") or ""}


@_serialized
def set_items(data_dir, project: str, *, drawing=None, notes=None, legend_page=None, legend: dict | None = None,
              bubbles: list | None = None, author: str = "", note: str = "",
              job_id: str = "") -> dict:
    """가르친 칸을 적는다 — 넘긴 항목만 바꾸고 나머지는 둔다.

    * `notes` · `legend[키]` 에 `None` 이 아니라 **빈 dict `{}`** 를 넘기면 그 칸을 지운다.
    * `bubbles` 는 목록 전체를 바꾼다 (빈 목록이면 지운다).
    """
    project = (project or "").strip()
    if not project:
        raise ValueError("프로젝트에 묶이지 않은 분석에는 가르친 칸을 저장할 자리가 없습니다")
    author = (author or "").strip()
    if not author:
        raise ValueError("작성자를 적어야 저장됩니다 (팀이 공유하는 값입니다)")
    data = load(data_dir, project)
    if drawing is not None:
        data["drawing"] = _item(drawing, "도면 영역") if drawing else None
    if notes is not None:
        data["notes"] = _item(notes, "NOTES 영역") if notes else None
    if legend_page is not None:
        if legend_page:
            items = legend_page if isinstance(legend_page, list) else [legend_page]
            out = []
            try:
                for it in items:
                    W, H = (float(t) for t in it.get("size"))
                    n = int(it.get("page_no"))
                    if all(o["page_no"] != n for o in out):
                        out.append({"page_no": n, "size": [round(W, 1), round(H, 1)]})
            except Exception:
                raise ValueError("범례 장: 장 번호와 쪽 크기가 필요합니다")
            data["legend_page"] = out
        else:
            data["legend_page"] = None
    for key, v in (legend or {}).items():
        if key not in LEGEND_KEYS:
            raise ValueError(f"모르는 범례 칸: {key}")
        if v:
            data["legend"][key] = _item(v, LEGEND_LABEL[key])
        else:
            data["legend"].pop(key, None)
    if bubbles is not None:
        if len(bubbles) > MAX_BUBBLES:
            raise ValueError(f"버블 예시는 {MAX_BUBBLES}개까지입니다")
        data["bubbles"] = [_item(b, "버블 예시") for b in bubbles]
    data.update({"author": author, "note": (note or "").strip(), "set_at": _now(),
                 "origin_job": job_id or "", "enabled": True})
    save(data_dir, project, data)
    return data


@_serialized
def clear(data_dir, project: str) -> bool:
    p = path_for(data_dir, project) if project else None
    if not p or not p.exists():
        return False
    p.unlink()
    return True


@_serialized
def set_enabled(data_dir, project: str, enabled: bool) -> dict:
    data = load(data_dir, project)
    data["enabled"] = bool(enabled)
    save(data_dir, project, data)
    return data
