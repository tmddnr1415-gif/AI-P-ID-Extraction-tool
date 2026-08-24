"""④ 행의 FROM/TO 사용자 확정 — 저장 · 문형 · 승계 (6회차).

자동 추적으로 ④ 를 더 줄이는 길은 세 번의 실측(배관 그래프 13.1% · 국소 연결
4.9% · 무제한 순회 10.4%)으로 막혀 있다.  그래서 사람이 한 번 확정하고 그것을
리비전 사이에 재사용한다.

파일: {데이터 디렉터리}/projects/{프로젝트}/axis_overrides.json
  · 키 = 안정 ID (`10LBA10-001`) — 좌표가 아니라 ID 로 묶는다.
  · 값 = from · to · 출처(후보선택/후보선택(부분)/자유입력) · type ·
    sentence(확정 당시 문장) · confirmed_at · origin_job.
  · 정렬 키 고정(sort_keys) + 같은 값 재저장은 confirmed_at 을 건드리지
    않으므로, 두 번 저장하면 같은 파일이다.

확정값은 user_values 계열이다 — ai_values 를 덮지 않고, 감사기의
"사람이 도면 값을 덮어쓴 칸" 집계(user_json ≠ ai_json)에 자동으로 잡힌다.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "engine"))
import describe_axis as daxis  # noqa: E402

FILE_NAME = "axis_overrides.json"

SOURCE_PICK = "후보선택"
SOURCE_PICK_PART = "후보선택(부분)"
SOURCE_FREE = "자유입력"


def path_for(data_dir: Path, project: str) -> Path:
    from app import revisions
    return revisions.project_dir(data_dir, project) / FILE_NAME


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True,
                               indent=1) + "\n", encoding="utf-8")


def classify_source(text: str, candidates: list) -> str:
    """확정 문구의 출처.  후보 그대로 = 후보선택, 후보의 일부만 = 후보선택(부분),
    어느 후보에도 없으면 자유입력.  후보는 전부 도면에서 읽은 텍스트이므로
    앞의 둘은 '도면에 인쇄된 문구'라는 뜻이다."""
    t = " ".join(str(text or "").upper().split())
    if not t:
        return ""
    for c in candidates:
        cu = " ".join(str(c).upper().split())
        if t == cu:
            return SOURCE_PICK
    for c in candidates:
        cu = " ".join(str(c).upper().split())
        if t in cu:
            return SOURCE_PICK_PART
    return SOURCE_FREE


def sentence_for(from_text: str, to_text: str, type_: str,
                 suffix: str = "") -> str:
    """판정 트리 ② 문형.  선두 FROM/TO 는 벗겨 중복을 막는다 (엔진과 같은 규칙)."""
    _d, src = daxis._strip_conn(str(from_text or ""))
    _d, dst = daxis._strip_conn(str(to_text or ""))
    v = {"axis": daxis.AX_FROMTO, "src": src, "dst": dst}
    return daxis.sentence(v, type_, suffix)


def suffix_for(rows_same_group: list, this_key: str) -> str:
    """Suffix 는 확정 후에도 기존 규칙: 같은 귀속점 · 같은 TYPE 이 2행 이상일 때
    위→아래 · 왼→오.  `rows_same_group` 은 [(key, rect)] — 이미 같은 페이지 ·
    같은 TYPE · 같은 (from, to) 로 걸러져 있다."""
    if len(rows_same_group) < 2:
        return ""
    members = sorted(rows_same_group,
                     key=lambda kr: (round(kr[1][1]), round(kr[1][0])))
    for i, (key, _rect) in enumerate(members):
        if key == this_key:
            return chr(ord("A") + i) if i < 26 else str(i + 1)
    return ""


def record(path: Path, stable_id: str, *, from_text: str, to_text: str,
           source_from: str, source_to: str, type_: str, sentence: str,
           origin_job: str) -> dict:
    """한 확정을 장부에 적는다.  같은 값의 재확정은 confirmed_at 을 유지한다 —
    두 번 저장하면 같은 파일이라는 결정성 요건이 여기서 성립한다."""
    data = load(path)
    entry = {"from": from_text, "to": to_text,
             "source_from": source_from, "source_to": source_to,
             "type": type_, "sentence": sentence, "origin_job": origin_job}
    old = data.get(stable_id)
    if old and all(old.get(k) == v for k, v in entry.items()
                   if k != "origin_job"):
        return old
    entry["confirmed_at"] = datetime.now(timezone.utc).isoformat(
        timespec="seconds")
    data[stable_id] = entry
    save(path, data)
    return entry


def clear(path: Path, stable_id: str) -> bool:
    data = load(path)
    if stable_id not in data:
        return False
    del data[stable_id]
    save(path, data)
    return True


def inherit(overrides: dict, states: dict, rows_by_key: dict,
            job_id: str) -> list:
    """리비전 승계 — 같은 안정 ID 가 매칭된 행에 확정 문장을 잇는다.

    반환: [(row_key, entry)] — 적용 대상.  적용하지 않는 경우:
      · ID 가 안 물리면 (states 에 없음) — 지어내지 않는다.
      · 그 행을 이 리비전에서 사람이 이미 고쳤으면 — 사람의 최신 판단이 이긴다.
      · 확정이 이 job 에서 난 것이면 — 승계가 아니라 원본이다.
    """
    out = []
    for key, st in states.items():
        entry = overrides.get(st.get("id") or "")
        if not entry or entry.get("origin_job") == job_id:
            continue
        row = rows_by_key.get(key)
        if row is None:
            continue
        if (row.get("user") or {}).get("description"):
            continue
        out.append((key, entry))
    return out
