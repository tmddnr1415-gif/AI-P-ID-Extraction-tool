"""프로젝트 범례 프로필 — 한 번 유도하고, 그 프로젝트의 개정본에서 다시 쓴다 (15회차).

사용자 요구는 한 문장이다: *새 프로젝트면 Symbol & Legend 를 학습하고, 같은
프로젝트의 다른 Rev 는 그 학습 결과를 쓴다.*

**속도가 목적이 아니다.**  10·15 회차 실측에서 `legend_rules` 는 전체 분석의
1.5% 다 (6.10s / 406.2s).  건너뛴다고 눈에 띄게 빨라지지 않는다.  실익은 둘이다.

  1. **일관성** — Rev.A 와 Rev.B 가 같은 판정 기준으로 분석된다.  범례 유도가
     판마다 미세하게 달라지면 리비전 비교가 오염된다.
  2. **견고성** — 개정본 PDF 에 범례 장이 빠져 있어도 분석할 수 있다.  개정
     도면은 바뀐 장만 오는 경우가 많고, 범례가 없으면 지금은 값들이 조용히
     config 기본값으로 떨어진다 (`docs/round15_survey.md` §4 실측).

무엇을 담는가 — **범례 장에서 나온 값만** 담는다
------------------------------------------------
`pipeline.analyse` 의 `legend_rules` 단계는 열 가지를 유도하는데, 그중 범례
장을 읽는 것은 여덟이고 나머지는 도면이나 config 에서 나온다.  프로필은 앞의
여덟만 담는다 — 뒤의 것을 담으면 다음 리비전의 **도면**에서 나와야 할 값이
옛 도면 값으로 굳는다.

| 항목 | 어디서 | 프로필 |
| --- | --- | --- |
| `butterfly` | 범례 p2 LINE VALVES BUTTERFLY 행 | 담는다 |
| `actuator_stem` | 범례 p3 VALVES ACTUATORS | 담는다 |
| `pneumatic` | 범례 p3 PNEUMATIC 행 | 담는다 |
| `line_styles` | 범례 SIGNAL / ELECTRIC 행 | 담는다 |
| `isa_table` | 범례 p3 식별 문자 표 | 담는다 |
| `equipment_symbols` | 범례 p2 EQUIPMENT 표 | 담는다 |
| `component_words` | 범례 p≤5 가 인쇄한 STRAINER 계열 | 담는다 (범례 몫만) |
| `unit_multipliers` | 범례 p5 UNIT IDENTIFICATION NUMBERS | 담는다 |
| `connector_reach` | **도면** 218개 커넥터의 분포 | 담지 않는다 |
| `layout`(도면 영역·타이틀블록 칸) | **도면 58장** | 담지 않는다 |

`equipment_vocab` 은 `equipment_symbols` 의 순수 함수이므로 따로 담지 않고
복원한 심볼에서 다시 만든다 — 값을 두 곳에 두면 언젠가 갈린다.

지문에 대하여
-------------
`pipeline.fingerprint` 는 `result["legend"]` 의 `source`·`note`·`values` 를
그대로 해싱한다.  재사용이 `source` 를 `PROFILE` 로 바꾸면 **같은 값을 쓰고도
지문이 달라진다.**  그래서 재사용은 저장된 `source`·`note` 를 **그대로** 들고
온다 — 그 값이 어느 범례에서 나왔는지를 말하는 문장이고, 그 사실은 리비전이
바뀌어도 변하지 않기 때문이다.  "이번 분석이 재지 않고 물려받았다"는 것은
지문 밖의 `result["legend_profile"]` 이 말하고, 화면이 그것을 읽는다.

그래서 세 경로가 같은 지문을 낸다: 신규 유도 · 프로필 재사용 · 프로필 무시하고
강제 유도.  **셋이 갈리면 프로필이 유도 결과를 정확히 담지 못한 것이고**,
그것이 `tests/test_legend_profile.py` 가 지키는 것이다.

어디에 사는가
-------------
`{data_dir}/projects/{프로젝트}/legend_profile.json`.  `app/paths.data_dir()`
체계 그대로이므로 exe 로 돌 때는 **exe 옆 `pid_data/`** 이고 소스 트리가
아니다 — 갈음(코드 덮어쓰기)으로 사라지지 않는다.  프로젝트 폴더 안이므로
다른 프로젝트가 공유할 길이 없다.

프로젝트 고유 어휘(HRSG · ST SUPPLIER 등)는 여기에도 코드에도 없다.  프로필은
**데이터**이고, 그 데이터는 그 프로젝트의 범례가 인쇄한 것뿐이다.
"""

from __future__ import annotations

import importlib
import json
import re
import sys
import time
from pathlib import Path


def _engine(name):
    """엔진 모듈을 **파이프라인과 같은 이름으로** 가져온다.

    `app/engine` 의 모듈들은 서로를 맨 이름으로 import 하고 `pipeline` 도 그렇게
    한다 (`app/pipeline.py` 머리 주석).  여기서 `app.engine.x` 로 가져오면 같은
    파일이 **두 벌** 올라가고 `Derived` 가 서로 다른 클래스가 된다.  그래서
    같은 키(`sys.modules['legend_rules']`)를 쓴다.
    """
    root = str(Path(__file__).resolve().parent / "engine")
    if root not in sys.path:
        sys.path.insert(0, root)
    return importlib.import_module(name)


VERSION = 1

FILENAME = "legend_profile.json"

# 프로필이 담는 항목.  순서가 곧 화면과 문서의 순서다.
ITEMS = ("butterfly", "actuator_stem", "pneumatic", "line_styles",
         "isa_table", "equipment_symbols", "component_words",
         "unit_multipliers")

# 사람이 읽을 한 줄 설명 — "무엇을 저장했는지 사람이 읽을 수 있어야 한다".
LABELS = {
    "butterfly": "버터플라이 밸브 날개 눈금 (범례 p2 LINE VALVES)",
    "actuator_stem": "액추에이터 스템 규약 (범례 p3 VALVES ACTUATORS)",
    "pneumatic": "공압 액추에이터 외곽 치수 (범례 p3)",
    "line_styles": "계장 신호선 파선 주기와 최소 런 (범례 SIGNAL/ELECTRIC 행)",
    "isa_table": "ISA 식별 문자표 (범례 p3)",
    "equipment_symbols": "기기 표 (범례 p2 EQUIPMENT)",
    "component_words": "중간 부품 낱말 (범례가 인쇄한 STRAINER 계열)",
    "unit_multipliers": "유닛 번호별 수량 승수 (범례 p5)",
}

# 유도가 성공했다고 볼 출처.  나머지는 "유도 실패" 로 기록한다 - 기본값으로
# 채우고 성공한 척하지 않는다.
DERIVED_SOURCES = ("LEGEND",)


# --------------------------------------------------------------------------
# 자리
# --------------------------------------------------------------------------

def profile_path(data_dir, project: str) -> Path:
    """프로젝트 폴더 안.  `revisions.project_dir` 과 같은 규칙을 쓴다."""
    from app import revisions
    return revisions.project_dir(Path(data_dir), project) / FILENAME


def load(data_dir, project: str):
    """저장된 프로필, 없으면 `None`.  **없는 것을 지어내지 않는다.**"""
    if not project:
        return None
    path = profile_path(data_dir, project)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    if not isinstance(data, dict) or data.get("version") != VERSION:
        return None
    return data


def save(data_dir, project: str, profile: dict) -> Path:
    """프로필을 그 프로젝트 폴더에 적는다.  정렬 고정 - 같은 값이면 같은 파일."""
    path = profile_path(data_dir, project)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# 담기
# --------------------------------------------------------------------------

def _derived(d) -> dict:
    """`legend_rules.Derived` 하나를 담을 모양으로."""
    return {"source": getattr(d, "source", ""),
            "note": getattr(d, "note", ""),
            "values": dict(getattr(d, "values", {}) or {}),
            "evidence": {k: v for k, v in
                         (getattr(d, "evidence", {}) or {}).items()}}


def capture(*, butterfly, actuator_stem, pneumatic, line_styles, isa,
            equip_symbols, component_words, multipliers, meta=None) -> dict:
    """이번 분석이 범례에서 읽은 것을 프로필 한 벌로 묶는다.

    `line_styles` 는 **`connector_reach` 를 섞기 전** 값이어야 한다.  섞은 뒤
    담으면 도면에서 잰 값이 범례 값인 척 굳는다.
    """
    items = {
        "butterfly": _derived(butterfly),
        "actuator_stem": _derived(actuator_stem),
        "pneumatic": _derived(pneumatic),
        "line_styles": _derived(line_styles),
        "isa_table": {"source": isa.source, "note": isa.note,
                      "page_no": isa.page_no,
                      "first": {k: list(v) for k, v in sorted(isa.first.items())},
                      "succeeding": {k: list(v) for k, v
                                     in sorted(isa.succeeding.items())}},
        "equipment_symbols": {
            "source": "LEGEND" if equip_symbols else "MISSING",
            "note": (f"범례 p{equip_symbols[0].page_no} EQUIPMENT 표 "
                     f"{len(equip_symbols)}행" if equip_symbols
                     else "범례에서 EQUIPMENT 표를 찾지 못했습니다"),
            "rows": [{"name": s.name, "page_no": s.page_no,
                      "anchor": list(s.anchor), "kinds": [list(k) for k in s.kinds],
                      "footprint": list(s.footprint), "paths": s.paths}
                     for s in equip_symbols]},
        "component_words": {
            "source": "LEGEND" if any(v == "LEGEND" for v
                                      in (component_words or {}).values())
                      else "MISSING",
            "note": "범례가 인쇄한 중간 부품 낱말",
            "words": sorted(w for w, src in (component_words or {}).items()
                            if src == "LEGEND")},
        "unit_multipliers": {"source": multipliers.source,
                             "note": multipliers.note,
                             "table": {k: v for k, v
                                       in sorted(multipliers.table.items())},
                             "scopes": {k: v for k, v
                                        in sorted(multipliers.scopes.items())},
                             "labels": {k: v for k, v
                                        in sorted(multipliers.labels.items())}},
    }
    failed = [k for k in ITEMS if items[k].get("source") not in DERIVED_SOURCES]
    out = {"version": VERSION,
           "saved_at": round(time.time(), 3),
           "source_meta": dict(meta or {}),
           "items": items,
           # 유도 실패는 감추지 않는다.  이 목록이 비어 있지 않으면 화면이
           # 그대로 읽어 "이 항목은 범례에서 읽지 못했습니다" 라고 적는다.
           "failed": failed}
    # **파일에 적힐 모양 그대로** 돌려준다.  JSON 은 튜플을 배열로, dict 키를
    # 문자열로 바꾸므로(`dash_histogram` 의 7.2 -> "7.2"), 그 변환을 여기서
    # 한 번 겪게 해 두면 "저장한 것 == 다시 읽은 것" 이 성립한다.  성립하지
    # 않으면 프로필이 무엇을 담았는지 두 가지 답이 생긴다.
    return json.loads(json.dumps(out, ensure_ascii=False, sort_keys=True))


# --------------------------------------------------------------------------
# 되쓰기
# --------------------------------------------------------------------------

def restore_derived(profile: dict) -> dict:
    """`legend_rules.derive_all` 이 돌려주던 세 벌을 프로필에서 다시 세운다."""
    legend_rules = _engine("legend_rules")
    out = {}
    for key in ("butterfly", "actuator_stem", "pneumatic"):
        item = (profile.get("items") or {}).get(key) or {}
        out[key] = legend_rules.Derived(
            values=dict(item.get("values") or {}),
            source=item.get("source") or "MISSING",
            note=item.get("note") or "",
            evidence=dict(item.get("evidence") or {}))
    return out


def restore_line_styles(profile: dict):
    legend_rules = _engine("legend_rules")
    item = (profile.get("items") or {}).get("line_styles") or {}
    return legend_rules.Derived(values=dict(item.get("values") or {}),
                                source=item.get("source") or "MISSING",
                                note=item.get("note") or "",
                                evidence=dict(item.get("evidence") or {}))


def restore_isa(profile: dict):
    isa_table = _engine("isa_table")
    item = (profile.get("items") or {}).get("isa_table") or {}
    return isa_table.IsaTable(
        first={k: tuple(v) for k, v in (item.get("first") or {}).items()},
        succeeding={k: tuple(v) for k, v
                    in (item.get("succeeding") or {}).items()},
        page_no=int(item.get("page_no") or 0),
        source=item.get("source") or "MISSING",
        note=item.get("note") or "")


def restore_equipment(profile: dict) -> list:
    dequip = _engine("describe_equipment")
    item = (profile.get("items") or {}).get("equipment_symbols") or {}
    return [dequip.EquipSymbol(name=r["name"], page_no=int(r["page_no"]),
                               anchor=tuple(r["anchor"]),
                               kinds=tuple(tuple(k) for k in r["kinds"]),
                               footprint=tuple(r["footprint"]),
                               paths=int(r["paths"]))
            for r in (item.get("rows") or [])]


def restore_multipliers(profile: dict):
    projectconfig = _engine("projectconfig")
    item = (profile.get("items") or {}).get("unit_multipliers") or {}
    return projectconfig.UnitMultipliers(
        source=item.get("source") or "MISSING",
        table=dict(item.get("table") or {}),
        scopes=dict(item.get("scopes") or {}),
        labels=dict(item.get("labels") or {}),
        note=item.get("note") or "")


def merge_component_words(profile: dict, fresh: dict) -> dict:
    """범례 몫은 프로필에서, 도면 몫은 이번 도면에서.

    순서가 중요하다.  원래 코드는 쪽 순서로 훑으면서 `setdefault` 하므로
    범례 장(p≤5)이 먼저 낱말을 차지한다.  여기서도 프로필을 먼저 깔고
    이번 도면 것을 `setdefault` 로 얹으므로 같은 결과가 된다.
    """
    out = {w: "LEGEND" for w
           in ((profile.get("items") or {}).get("component_words") or {}
               ).get("words") or []}
    for word, src in (fresh or {}).items():
        out.setdefault(word, src)
    return out


# --------------------------------------------------------------------------
# 대조 — 조용히 옛 규칙을 쓰지 않게
# --------------------------------------------------------------------------

def _flat(item: dict, key: str) -> dict:
    """한 항목을 `{칸 이름: 값}` 으로 편다.  대조는 칸 단위로 한다."""
    if key in ("butterfly", "actuator_stem", "pneumatic", "line_styles"):
        out = {f"values.{k}": v for k, v in (item.get("values") or {}).items()}
    elif key == "isa_table":
        out = {f"first.{k}": list(v) for k, v in (item.get("first") or {}).items()}
        out.update({f"succeeding.{k}": list(v) for k, v
                    in (item.get("succeeding") or {}).items()})
    elif key == "equipment_symbols":
        out = {f"row.{r['name']}": [r["anchor"], r["kinds"], r["paths"]]
               for r in (item.get("rows") or [])}
    elif key == "component_words":
        out = {f"word.{w}": True for w in (item.get("words") or [])}
    elif key == "unit_multipliers":
        out = {f"table.{k}": v for k, v in (item.get("table") or {}).items()}
        out.update({f"labels.{k}": v for k, v
                    in (item.get("labels") or {}).items()})
    else:                                             # pragma: no cover
        out = {}
    out["source"] = item.get("source")
    return out


def read_pages(profile: dict) -> list:
    """이 프로필의 값이 **실제로 나온** 장 번호.

    페이지 종류(`page_kind`)로 세지 않는다.  15회차 캡처가 그 차이를 잡았다:
    범례 p2 를 다시 그린 PDF 에서 그 장의 타이틀블록이 밀려 `page_kind` 가
    LEGEND 가 아니게 됐는데, 유도는 **인쇄된 머리말**로 그 장을 찾아 값을
    제대로 읽었다.  "몇 장을 읽었나" 는 읽은 쪽이 답해야 한다.
    """
    items = (profile or {}).get("items") or {}
    pages = set()
    for key in ITEMS:
        item = items.get(key) or {}
        if item.get("source") not in DERIVED_SOURCES:
            continue
        page = (item.get("evidence") or {}).get("page_no")
        if page is None:
            page = item.get("page_no")
        if page is None:
            rows = item.get("rows") or []
            page = rows[0].get("page_no") if rows else None
        if page is None:
            # 유도 함수가 자기 근거 문장에 적어 둔 쪽 번호 (`legend p5: ...`).
            # 우리가 쓴 문장이므로 도면 텍스트를 추측하는 것이 아니다.
            hit = re.search(r"\blegend p(\d+)\b", str(item.get("note") or ""))
            page = int(hit.group(1)) if hit else None
        if isinstance(page, int):
            pages.add(page)
    return sorted(pages)


def uncompared(fresh: dict) -> list:
    """이번 PDF 에서 **읽지 못한** 항목.  "같다" 가 아니라 "모른다" 이다."""
    items = (fresh or {}).get("items") or {}
    return [k for k in ITEMS
            if (items.get(k) or {}).get("source") not in DERIVED_SOURCES]


def diff(stored: dict, fresh: dict) -> list:
    """프로필과 이번 범례의 차이.  **고치지 않는다 - 말하기만 한다.**

    돌려주는 것은 `{item, key, was, now}` 목록이고, 무엇이 무엇에서 무엇으로
    바뀌었는지 그대로 담는다.  갱신 여부는 사람이 고른다 (§7.3 의 삭제 후보와
    같은 철학 - 기계가 확정하지 않는다).
    """
    out = []
    a = (stored or {}).get("items") or {}
    b = (fresh or {}).get("items") or {}
    skip = set(uncompared(fresh))
    for key in ITEMS:
        # 이번 PDF 가 그 범례를 안 들고 왔으면 **대조하지 않는다.**  못 읽은
        # 것을 "바뀌었다" 로 세면 개정본마다 거짓 경보가 뜨고, 그러면 진짜
        # 변경이 그 안에 묻힌다.  못 읽었다는 사실은 `uncompared` 가 말한다.
        if key in skip:
            continue
        fa, fb = _flat(a.get(key) or {}, key), _flat(b.get(key) or {}, key)
        for cell in sorted(set(fa) | set(fb)):
            was, now = fa.get(cell, None), fb.get(cell, None)
            if was != now:
                out.append({"item": key, "label": LABELS.get(key, key),
                            "key": cell, "was": was, "now": now})
    return out


def describe(profile: dict) -> list:
    """사람이 읽을 줄.  항목명 · 값 · 유도 근거."""
    out = []
    for key in ITEMS:
        item = (profile.get("items") or {}).get(key) or {}
        src = item.get("source") or "?"
        head = f"{LABELS.get(key, key)} — {src}"
        if src not in DERIVED_SOURCES:
            head += " (유도 실패)"
        out.append(head)
        if item.get("note"):
            out.append(f"    근거: {item['note']}")
        flat = _flat(item, key)
        flat.pop("source", None)
        for cell in sorted(flat)[:12]:
            out.append(f"    {cell} = {flat[cell]}")
        if len(flat) > 12:
            out.append(f"    … 그 밖에 {len(flat) - 12}칸")
    return out


def summary(profile: dict) -> dict:
    """화면이 읽는 요약 — 몇 항목을 담았고 그중 몇이 유도 실패인가."""
    items = (profile or {}).get("items") or {}
    return {"version": (profile or {}).get("version"),
            "saved_at": (profile or {}).get("saved_at"),
            "source_meta": (profile or {}).get("source_meta") or {},
            "item_count": len(items),
            "items": [{"key": k, "label": LABELS.get(k, k),
                       "source": (items.get(k) or {}).get("source"),
                       "note": (items.get(k) or {}).get("note") or "",
                       "cells": max(0, len(_flat(items.get(k) or {}, k)) - 1)}
                      for k in ITEMS if k in items],
            "failed": list((profile or {}).get("failed") or [])}
