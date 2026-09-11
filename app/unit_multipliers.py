"""유닛 승수 — **도면이 말하지 않을 때 사람이 한 번 답하는 자리** (31회차).

## 왜 있는가

30회차까지 재 보니 사람 몫(검토 사유가 붙은 행)의 1위가 **세 프로젝트에서
전부 승수**였다.

    SADARA  MULTIPLIER_UNDEFINED    82행 (전량)   축3 수량 16.67점 손실
    TC2     MULTIPLIER_FROM_CONFIG 203행
    UAD     MULTIPLIER_FROM_CONFIG 149행 (전량)

셋 다 **검출의 문제가 아니다** — 그 도면에 UNIT IDENTIFICATION NUMBERS 표가
없거나(TC2·UAD) 표가 그 유닛코드를 정의하지 않는다(SADARA 는 `PLANT×1` 만
정의하는데 도면 4장이 전부 유닛 `10` 이다).  26회차가 *"확인 필요"* 라고 적어
두었지만 **확인할 자리를 만들지 않았다.**  이 파일이 그 자리다.

## 읽는 순서 — §9 그대로.  사람은 범례를 못 이긴다

    ① 그 문서의 범례 UNIT IDENTIFICATION 표      ← 이기면 여기서 끝
    ② 그 장의 NOTES (27회차 `note_unit_span`)
    ③ **사람이 지정한 값 (여기)**
    ④ 프로젝트 설정 폴백 (= 남의 도면에서 잰 값)
    ⑤ 아무 것도 없으면 빈칸 + 사유

그래서 **AL NOUF1 은 이 경로에 닿지 않는다** — 그 문서의 범례가 코드 일곱을
전부 덮는다.  사람이 값을 넣어도 `Q'ty 1931` 과 지문 `fb85b039` 가 움직이지
않아야 하고, `tests/test_unit_multipliers.py` 가 그것을 못박는다.

## 자리와 모양 — 있는 것을 반쪽씩 가져왔다 (31회차 [B-0])

    자리·범위  ← `axis_overrides`(6회차)   {data_dir}/projects/{프로젝트}/unit_multipliers.json
    모양·규율  ← 전역 심볼 사전(18회차)     author 필수 · 읽는 곳 하나 ·
                                           범례가 이긴다 · enabled 스위치

* **소스 트리가 아니다.**  갈음(코드 덮어쓰기) 때 사라지면 안 된다.
* **프로젝트 단위다.**  승수는 그 플랜트의 사실이지 업계 관행이 아니므로
  전역 사전과 달리 다른 프로젝트가 공유하지 않는다.
* **범례 프로필과 다른 파일이다.**  프로필은 *범례가 말한 것*만 담는다 —
  섞으면 프로필이 범례 값을 정확히 담았는지 확인할 길이 사라진다 (15회차 [4]).
* **작성자 없이 저장할 수 없다.**  팀이 공유하는 값이므로 누가 넣었는지가
  값의 일부다 (13회차 자기신고 — 서버도 화면도 이름을 지어내지 않는다).
* **끌 수 있다.**  `enabled: false` 한 줄로 전량 무시되고, 그때 결과는 이
  파일이 없던 때와 **정확히 같다** (읽는 곳이 `table()` 하나이므로).

## 리비전 사이에는 그대로 간다 — 근거

승수는 **그 플랜트에 유닛이 몇 벌인가**이고, 도면 개정(선 몇 개가 바뀌는 일)
과는 다른 사실이다.  네 문서 실측으로도 유닛코드는 도면번호에서 오고 개정과
무관하다.  그래서 **프로젝트 단위로 승계**한다 — 리비전마다 다시 묻지 않는다.
⚠ 다만 *유닛이 실제로 늘거나 줄어드는 개정*은 있을 수 있으므로, 값에
`set_at` 과 `origin_job` 을 남겨 **언제 어느 분석에서 넣었는지**를 보이게 한다.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

FILENAME = "unit_multipliers.json"
VERSION = 1

# 검토 사유 — 범례에서 온 것과 구분한다 (`MULTIPLIER_FROM_CONFIG` 와 나란히).
REVIEW_CODE = "MULTIPLIER_BY_USER"
REASON = ("unit code '%s' 의 승수 x%s 는 도면이 아니라 **사람이 지정한 값**"
          "입니다 (%s · %s) — 근거를 함께 보관합니다")


def path_for(data_dir, project: str) -> Path:
    from app import revisions
    return revisions.project_dir(Path(data_dir), project) / FILENAME


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load(data_dir, project: str) -> dict:
    """저장된 지정값 한 벌.  없으면 빈 구조 (파일을 만들지 않는다)."""
    if not project:
        return {"version": VERSION, "enabled": True, "units": {}}
    p = path_for(data_dir, project)
    if not p.exists():
        return {"version": VERSION, "enabled": True, "units": {}}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"version": VERSION, "enabled": True, "units": {}}
    data.setdefault("version", VERSION)
    data.setdefault("enabled", True)
    data.setdefault("units", {})
    return data


def save(data_dir, project: str, data: dict) -> Path:
    p = path_for(data_dir, project)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True,
                            indent=1) + "\n", encoding="utf-8")
    return p


def table(data_dir, project: str) -> dict:
    """파이프라인에 넘길 `{유닛코드: 배수}`.  **읽는 곳은 여기 하나다.**

    꺼져 있으면 빈 dict 를 돌려준다 — 그러면 이 파일이 없던 때와 정확히 같다.
    """
    data = load(data_dir, project)
    if not data.get("enabled", True):
        return {}
    out = {}
    for unit, rec in (data.get("units") or {}).items():
        try:
            n = int(rec.get("multiplier"))
        except (TypeError, ValueError):
            continue
        if n >= 1:
            out[str(unit)] = n
    return out


def set_unit(data_dir, project: str, *, unit: str, multiplier: int,
             author: str = "", note: str = "", job_id: str = "") -> dict:
    """한 유닛코드의 승수를 지정한다.  **`author` 없이 넣을 수 없다.**

    18회차 전역 심볼 사전의 등록 함수와 **같은 규율**이다 — 인증을 만들 자리가
    아니므로 자기신고이되, **비워 두고 저장되지는 않는다.**
    """
    project = (project or "").strip()
    if not project:
        raise ValueError("프로젝트에 묶이지 않은 분석에는 승수를 지정할 수 없습니다")
    unit = str(unit or "").strip()
    if not unit:
        raise ValueError("유닛코드가 비어 있습니다")
    author = (author or "").strip()
    if not author:
        raise ValueError("작성자를 적어야 저장됩니다 (팀이 공유하는 값입니다)")
    n = int(multiplier)
    if n < 1:
        raise ValueError("승수는 1 이상의 정수입니다")
    data = load(data_dir, project)
    data["units"][unit] = {
        "multiplier": n,
        "author": author,
        "note": (note or "").strip(),
        "set_at": _now(),
        "origin_job": job_id or "",
    }
    save(data_dir, project, data)
    return data["units"][unit]


def clear_unit(data_dir, project: str, unit: str) -> bool:
    """되돌린다.  지운 뒤에는 그 유닛이 지정되지 않았던 때와 같아진다."""
    data = load(data_dir, project)
    if str(unit) not in (data.get("units") or {}):
        return False
    data["units"].pop(str(unit))
    save(data_dir, project, data)
    return True


def set_enabled(data_dir, project: str, enabled: bool) -> dict:
    data = load(data_dir, project)
    data["enabled"] = bool(enabled)
    save(data_dir, project, data)
    return data
