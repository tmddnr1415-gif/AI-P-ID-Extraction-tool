"""데이터 디렉터리를 세기만 한다.  아무것도 지우지 않는다.

방침은 `docs/db_hygiene.md` 에 있고, 그중 승인된 것은 **(가) 감사기 상시**
하나다.  (나) 자동 정리 버튼은 다음 회차이므로, 이 모듈에는 삭제가 없다 —
`os.remove` 도 `shutil.rmtree` 도 나오지 않는다.

무엇을 세는가는 두 갈래다.

산출물이 도면 근거를 갖는가
    · 사람이 도면 값을 덮어쓴 칸      user_json 값 ≠ ai_json 값
    · 도면 근거 없는 행               added=1
  둘 다 결함이 아니다 — 검토자는 도면을 덮어쓸 수 있다.  다만 **점검 흔적과
  구분되지 않으므로** 파일을 넘기기 전에 보여야 한다.  1회차에 산출물에서
  찾은 것이 정확히 이것이었고, `git status` 는 끝까지 깨끗했다.

무엇이 쌓였는가
    · 어떤 job 도 가리키지 않는 업로드
    · 대응 revision 이 없는 출력 디렉터리
    · 대응 job 이 없는 진단 zip
    · DB 파일 안의 죽은 페이지 (freelist)
  이번에 손으로 치우기 전 실측: 출력 43 · 업로드 3 · DB 168MB 중 91%가
  죽은 페이지였다.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

REV_DIR = re.compile(r"^rev(\d+)$")


def _dir_bytes(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def provenance(con) -> dict:
    """산출물에 들어갈 값 중 도면이 대지 못하는 것.  job 단위로 센다."""
    jobs = []
    for job in con.execute("SELECT id, pdf_name FROM job ORDER BY created_at"):
        over = added = live = 0
        for r in con.execute(
                "SELECT ai_json,user_json,added FROM item"
                " WHERE job_id=? AND removed=0 AND deleted=0", (job["id"],)):
            live += 1
            if r["added"]:
                added += 1
                continue
            ai = json.loads(r["ai_json"])
            for field, value in json.loads(r["user_json"]).items():
                if value != ai.get(field):
                    over += 1
        jobs.append({"job_id": job["id"], "pdf_name": job["pdf_name"],
                     "rows": live, "overridden_cells": over, "hand_added_rows": added})
    return {"jobs": jobs,
            "overridden_cells": sum(j["overridden_cells"] for j in jobs),
            "hand_added_rows": sum(j["hand_added_rows"] for j in jobs)}


def leftovers(con, data_dir: Path) -> dict:
    """참조가 끊긴 파일과 DB 안의 죽은 페이지.  세기만 한다."""
    referenced = {os.path.basename(r[0]) for r in con.execute("SELECT pdf_path FROM job")}
    jobs = {r[0] for r in con.execute("SELECT id FROM job")}
    revisions = {f"rev{r[0]}" for r in con.execute("SELECT id FROM revision")}

    uploads, upload_bytes = [], 0
    up = data_dir / "uploads"
    if up.is_dir():
        for f in sorted(up.iterdir()):
            if f.is_file() and f.name not in referenced:
                uploads.append(f.name)
                upload_bytes += f.stat().st_size

    outputs, output_bytes = [], 0
    out = data_dir / "outputs"
    if out.is_dir():
        for d in sorted(out.iterdir()):
            if d.is_dir() and REV_DIR.match(d.name) and d.name not in revisions:
                outputs.append(d.name)
                output_bytes += _dir_bytes(d)

    diags, diag_bytes = [], 0
    dg = data_dir / "diagnostics"
    if dg.is_dir():
        for f in sorted(dg.iterdir()):
            if f.is_file() and not any(j in f.name for j in jobs):
                diags.append(f.name)
                diag_bytes += f.stat().st_size

    page_size = con.execute("PRAGMA page_size").fetchone()[0]
    page_count = con.execute("PRAGMA page_count").fetchone()[0]
    free = con.execute("PRAGMA freelist_count").fetchone()[0]
    return {
        "orphan_uploads": uploads,
        "orphan_outputs": outputs,
        "orphan_diagnostics": diags,
        "reclaimable_bytes": upload_bytes + output_bytes + diag_bytes
                             + free * page_size,
        "db_bytes": page_count * page_size,
        "db_free_bytes": free * page_size,
    }


def run(con, data_dir: Path) -> dict:
    prov = provenance(con)
    left = leftovers(con, data_dir)
    return {"provenance": prov, "leftovers": left, "lines": summary(prov, left)}


def summary(prov: dict, left: dict) -> list[str]:
    """로그와 화면이 같은 문장을 쓰도록, 문장을 한 곳에서 만든다."""
    mb = lambda n: f"{n / 1024 / 1024:.1f} MB"
    lines = [
        f"산출 대상 {sum(j['rows'] for j in prov['jobs'])}행 / "
        f"job {len(prov['jobs'])}개 · "
        f"사람이 도면 값을 덮어쓴 칸 {prov['overridden_cells']} · "
        f"도면 근거 없는 행 {prov['hand_added_rows']}",
        f"고아 업로드 {len(left['orphan_uploads'])} · "
        f"고아 출력 {len(left['orphan_outputs'])} · "
        f"고아 진단 {len(left['orphan_diagnostics'])} · "
        f"DB {mb(left['db_bytes'])} 중 죽은 페이지 {mb(left['db_free_bytes'])} · "
        f"정리하면 되찾는 용량 {mb(left['reclaimable_bytes'])}",
    ]
    if prov["overridden_cells"] or prov["hand_added_rows"]:
        lines.append(
            "위 두 값이 0 이 아니면 산출물에 도면이 대지 못하는 값이 들어갑니다 — "
            "검토자가 넣은 것인지 시험 흔적인지 확인하세요.")
    return lines
