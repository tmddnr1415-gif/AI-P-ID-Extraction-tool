"""후보 병렬 워크북 → 확정 장부 (10회차의 받는 쪽).

워크북만 만들면 사람이 채워도 반영되지 않는다.  이 스크립트가 "선택 후보" 열을
읽어 6회차의 `axis_overrides` 저장소에 적는다 — **새 저장소를 만들지 않는다.**

  · '작성 예시' 메모가 있는 행은 건너뛴다 (예시가 확정으로 새지 않게).
  · 선택이 비었거나 '보류' 면 건너뛴다.
  · 키는 워크북의 `key` 열 → 안정 ID 로 바꿔 적는다.  매핑은 그 job 의
    리비전 상태에서 온다 (없으면 그 행은 적을 곳이 없으므로 건너뛰고 센다).
  · 출처는 `후보선택(워크북)` — 자유입력과 구분된다.
  · 시트3 '규칙 후보' 를 다시 채운다 (사람이 '전 페이지 규칙 후보' 로 표시한 행).

    python3 spike/read_candidates.py out/candidates_nouf1.xlsx PROJECT [JOB_ID]
"""
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import axis_overrides as ov  # noqa: E402

EXAMPLE_NOTE = "작성 예시"
COL = {"page": 3, "type": 5, "desc": 7, "axis": 8, "c1": 9, "c6": 14,
       "pick": 23, "direct": 24, "scope": 25, "reason": 26, "memo": 27,
       "key": 28}
HOLD = "보류"


def selections(ws) -> list:
    """워크북에서 사람이 고른 것들.  예시·빈칸·보류는 뺀다."""
    out = []
    for i in range(2, ws.max_row + 1):
        memo = str(ws.cell(i, COL["memo"]).value or "")
        if EXAMPLE_NOTE in memo:
            continue
        pick = str(ws.cell(i, COL["pick"]).value or "").strip()
        if not pick or pick == HOLD:
            continue
        if pick.isdigit():
            sentence = ws.cell(i, COL["c1"] + int(pick) - 1).value
        else:
            sentence = ws.cell(i, COL["direct"]).value
        sentence = str(sentence or "").strip()
        if not sentence:
            continue
        out.append({"row": i, "key": str(ws.cell(i, COL["key"]).value or ""),
                    "pick": pick, "sentence": sentence,
                    "type": str(ws.cell(i, COL["type"]).value or ""),
                    "scope": str(ws.cell(i, COL["scope"]).value or ""),
                    "reason": str(ws.cell(i, COL["reason"]).value or "")})
    return out


def apply(wb_path, data_dir: Path, project: str, id_map: dict,
          origin_job: str = "workbook") -> dict:
    """고른 것을 장부에 적는다.  `id_map` 은 {row key: 안정 ID}."""
    wb = openpyxl.load_workbook(wb_path)
    ws = wb[wb.sheetnames[1]] if wb.sheetnames[0].startswith("0.") else wb.active
    picks = selections(ws)
    path = ov.path_for(data_dir, project)
    wrote, skipped = 0, 0
    for p in picks:
        sid = id_map.get(p["key"])
        if not sid:
            skipped += 1
            continue
        ov.record(path, sid, from_text="", to_text="",
                  source_from=ov.SOURCE_WORKBOOK, source_to=ov.SOURCE_WORKBOOK,
                  type_=p["type"], sentence=p["sentence"],
                  origin_job=origin_job, candidate=p["pick"],
                  applies_to=p["scope"], reason=p["reason"])
        wrote += 1
    return {"selected": len(picks), "written": wrote, "no_stable_id": skipped}


def id_map_from_db(data_dir: Path, job_id: str) -> dict:
    """{row key: 안정 ID} — 그 job 의 리비전 대조 결과에서."""
    from app import db, paths                       # noqa: F401
    con = db.connect(data_dir / "app.db")
    try:
        return {k: (st or {}).get("id", "")
                for k, st in db.revision_states(con, job_id).items()}
    finally:
        con.close()


if __name__ == "__main__":
    wb_path = sys.argv[1]
    project = sys.argv[2] if len(sys.argv) > 2 else ""
    job_id = sys.argv[3] if len(sys.argv) > 3 else ""
    from app import paths
    data_dir = paths.data_dir()
    id_map = id_map_from_db(data_dir, job_id) if job_id else {}
    print(apply(wb_path, data_dir, project, id_map, origin_job=job_id or "workbook"))
