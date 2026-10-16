"""새 프로젝트 점검표를 글로 낸다 (hotfix81) — 회귀 blob 또는 DB 의 분석에서.

    python3 spike/intake_report.py out/regression_3p/QFE.json            # 하네스 결과 json
    python3 spike/intake_report.py --db app/_data/app.db <분석ID>          # 저장된 분석 (읽기만)
    python3 spike/intake_report.py --db app/_data/app.db --latest          # 가장 최근에 끝난 분석

판정은 하지 않는다 — `app/intake.py` 하나가 저장된 사실만 읽는다 (서버 `GET /jobs/{id}/intake` 와 같은 함수).
DB 는 **읽기 전용 사본**으로 연다 (실 DB 를 건드리지 않는다 — 17회차 규율).
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import intake  # noqa: E402


def from_blob(path: Path) -> dict:
    blob = json.loads(path.read_text(encoding="utf-8"))
    result = blob.get("result") or blob
    tb = {int(t["page_no"]): t for t in (result.get("titleblocks") or []) if isinstance(t, dict)}
    pages = []
    for p in result.get("pages") or []:
        q = dict(p)
        q.setdefault("rev", (tb.get(int(p.get("page_no", 0)), {}) or {}).get("rev") or "")
        pages.append(q)
    rows = [dict(r) for r in result.get("rows") or []]
    job = {"input_kind": result.get("input_kind") or "PDF", "pdf_name": path.name}
    return intake.build(result, pages, rows, job=job)


def from_db(db_path: Path, job_id: str | None, latest: bool) -> dict:
    from app import db
    tmp = Path(tempfile.mkdtemp(prefix="intake-"))
    copy = tmp / "app.db"
    shutil.copy2(db_path, copy)
    con = db.connect(copy)
    if latest or not job_id:
        row = con.execute("SELECT id FROM job WHERE status='done' ORDER BY finished_at DESC, rowid DESC LIMIT 1").fetchone()
        if row is None:
            raise SystemExit("끝난 분석이 없습니다")
        job_id = row["id"]
    job = db.get_job(con, job_id)
    if job is None:
        raise SystemExit(f"분석 {job_id} 가 없습니다")
    engine = json.loads(job["engine_json"] or "{}")
    pages = [dict(p) for p in db.page_revisions(con, job_id)]
    rows = db.merged_rows(con, job_id)
    out = intake.build(engine, pages, rows, job=dict(job))
    out["job_id"] = job_id
    return out


def main(argv: list) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    if argv[0] == "--db":
        db_path = Path(argv[1])
        latest = "--latest" in argv[2:]
        job_id = next((a for a in argv[2:] if not a.startswith("--")), None)
        out = from_db(db_path, job_id, latest)
    else:
        out = from_blob(Path(argv[0]))
    print(out["text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
