"""전역 심볼 사전 — 범례에 없지만 업계 표준으로 통용되는 심볼 (18회차).

## 15회차 프로젝트 프로필과 무엇이 다른가

    프로젝트 프로필 (15회차)  그 프로젝트 **범례에서 유도한 값**.  프로젝트
                             단위.  다른 프로젝트와 공유하지 않는다
    전역 심볼 사전 (여기)      범례에 **없는데** 도면이 쓰는 심볼.  사람이
                             확인해 등록하고, 모든 프로젝트에 적용된다

## ⚠ 자동 등록을 하지 않는다

§2.2 는 "표준 사전에 프로젝트 표기 혼입" 을 금지한다.  전역 사전에 그
프로젝트에서만 통하는 심볼이 들어가면 **다음 프로젝트에서 오검출이 난다** —
그리고 오검출은 미검출보다 나쁘다(없는 것은 눈에 띄지만 있는 것은 안 띈다).

그래서 이 모듈에는 **자동으로 넣는 길이 없다.**  `register()` 는 `author` 를
요구하고, 부르는 곳은 사람이 누른 API 하나뿐이다.  파이프라인은 이 사전을
**읽기만** 한다.

## 우선순위

    ① 그 프로젝트 범례 (15회차 프로필 · `legend_profile`)
    ② 전역 심볼 사전 (여기)

범례가 정의한 것이 있으면 그것을 쓴다.  범례는 그 문서의 약속이고 전역
사전은 업계의 관행이므로, 둘이 다르면 **그 문서가 이긴다**.

## 자리

`app/_data/global_symbols.json` — **소스 트리가 아니다.**  갈음(코드 덮어쓰기)
때 사라지면 안 되기 때문이고, 15회차 프로젝트 프로필이 같은 이유로 같은
뿌리에 산다.

## 껐다 켤 수 있다

오염되면 되돌려야 한다.  `enabled: false` 한 줄로 전량 무시되고, 그때
결과는 사전이 없던 때와 **정확히 같다** (읽는 곳이 한 군데이므로).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

FILENAME = "global_symbols.json"
VERSION = 1

# 심볼이 무엇을 가리키는가.  이 목록은 **자리**를 정하는 것이지 뜻을 정하지
# 않는다 — 뜻은 등록할 때 사람이 적는다.
KINDS = ("VALVE_BODY", "INSTRUMENT_TAG", "ACTUATOR")


def path(data_dir: Path) -> Path:
    return Path(data_dir) / FILENAME


def empty() -> dict:
    return {"version": VERSION, "enabled": True, "symbols": {}}


def load(data_dir: Path) -> dict:
    """없으면 빈 사전.  **없는 것과 비어 있는 것은 같다** — 둘 다 아무 것도
    바꾸지 않는다."""
    p = path(data_dir)
    if not p.exists():
        return empty()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return empty()
    if not isinstance(data, dict) or "symbols" not in data:
        return empty()
    data.setdefault("version", VERSION)
    data.setdefault("enabled", True)
    return data


def save(data_dir: Path, data: dict) -> Path:
    """정렬 키를 고정해 쓴다 — 두 번 저장하면 같은 파일이어야 한다
    (15회차 `Registry.save` 와 같은 규칙)."""
    p = path(data_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                 encoding="utf-8")
    return p


def active(data_dir: Path) -> dict:
    """지금 적용되는 심볼들.  꺼져 있으면 **빈 것**을 돌려준다."""
    data = load(data_dir)
    return data["symbols"] if data.get("enabled", True) else {}


def register(data_dir: Path, *, symbol_id: str, kind: str, name: str,
             type_value: str = "", deliverable: str = "",
             signature: dict = None, author: str = "",
             source_page: int = 0, source_rect=None, note: str = "") -> dict:
    """사람이 확인한 심볼 하나를 넣는다.

    **`author` 없이 넣을 수 없다.**  13회차의 자기신고 그대로다 — 인증은
    없지만 누가 넣었는지는 남아야 한다.  비어 있으면 거절한다: 자동 등록이
    실수로라도 생기는 것을 막는 유일한 자물쇠이기 때문이다.
    """
    author = (author or "").strip()
    if not author:
        raise ValueError("등록자 이름이 필요합니다 — 자동 등록은 하지 않습니다")
    if kind not in KINDS:
        raise ValueError(f"알 수 없는 종류: {kind}")
    name = (name or "").strip()
    if not name:
        raise ValueError("이 심볼이 무엇인지 적어야 합니다")
    data = load(data_dir)
    data["symbols"][symbol_id] = {
        "id": symbol_id,
        "kind": kind,
        "name": name,
        "type": (type_value or "").strip(),
        "deliverable": (deliverable or "").strip(),
        "signature": signature or {},
        "registered_by": author,
        "registered_at": time.time(),
        "source_page": int(source_page or 0),
        "source_rect": [round(float(v), 1) for v in (source_rect or [])],
        "note": (note or "").strip(),
    }
    save(data_dir, data)
    return data["symbols"][symbol_id]


def remove(data_dir: Path, symbol_id: str) -> bool:
    data = load(data_dir)
    if symbol_id not in data["symbols"]:
        return False
    del data["symbols"][symbol_id]
    save(data_dir, data)
    return True


def set_enabled(data_dir: Path, on: bool) -> dict:
    data = load(data_dir)
    data["enabled"] = bool(on)
    save(data_dir, data)
    return data


def resolve(data_dir: Path, signature_key: str, legend_has: bool = False):
    """이 심볼을 무엇으로 볼 것인가 — **범례가 이긴다**.

    `legend_has` 가 참이면 전역 사전을 보지 않는다.  범례는 그 문서의
    약속이고 전역 사전은 업계의 관행이라, 둘이 다르면 그 문서가 맞다.
    """
    if legend_has:
        return None
    return active(data_dir).get(signature_key)
