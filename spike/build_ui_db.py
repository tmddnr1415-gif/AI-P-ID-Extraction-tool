"""UI 스위트가 돌 수 있는 DB 를 **저장된 분석 결과**로 세운다.

왜 필요한가
    UI 스위트는 **SCOPE 있는 데이터**에서만 뜻이 있다 (14회차).  이 PC 의 실 DB
    (`app/_data/app.db`)에는 10회차 이전 분석 넷(824·824·824·75행)뿐이고 SCOPE 가
    전부 빈칸이라, 시험이 설계대로 **건너뛰지 않고 실패**한다.

무엇을 하는가
    회귀 하네스가 남긴 결과 json 을 `db.store_result` 로 새 DB 에 넣는다.
    **다시 분석하지 않는다** (AL NOUF1 전량 분석은 8분).  실 DB 는 열지 않는다.

    python3 spike/build_ui_db.py <결과.json> <만들 DB 경로>
    PID_UI_DB=<그 경로> python3 -m pytest -q -m ui
"""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    src, dest = Path(sys.argv[1]), Path(sys.argv[2])
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    # 옛 분석(SCOPE 가 빈 `legacy` 행)도 있어야 14회차의 세 갈래가 전부 걸린다.
    # 그래서 실 DB 를 **읽어서 복사**하고 그 위에 이번 결과를 한 건 더 넣는다.
    # 복사는 읽기이고, 원본은 열지 않는다 (`shutil.copyfile` 은 쓰기를 하지 않는다).
    real = ROOT / "app" / "_data" / "app.db"
    if real.exists():
        import shutil
        shutil.copyfile(real, dest)
    # 실 DB 를 건드리지 않는다 — 쓰는 뿌리를 버릴 폴더로 돌린다.
    os.environ["PID_DATA_DIR"] = tempfile.mkdtemp(prefix="uidb-")
    from app import db

    blob = json.loads(src.read_text())
    result = blob.get("result", blob)
    con = db.connect(dest)
    job = "uidb%012x" % (abs(hash(str(src))) & 0xFFFFFFFFFFFF)
    con.execute(
        "INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, created_at, status,"
        " progress, message, fingerprint, project, revision)"
        " VALUES (?,?,?,?,datetime('now'),'done',1.0,'',?,?,?)",
        (job, Path(result["pdf"]).name if result.get("pdf") else "analysis.pdf",
         "", "", result.get("fingerprint") or "", "UIDB", "A"))
    con.commit()
    summary = db.store_result(con, job, result)
    con.commit()
    rows = con.execute("SELECT COUNT(*) FROM item WHERE job_id=?", (job,)).fetchone()[0]
    scoped = sum(1 for r in con.execute(
        "SELECT ai_json FROM item WHERE job_id=?", (job,))
        if (json.loads(r[0] or "{}").get("scope") or ""))
    print("%s  행 %d  SCOPE 채워진 행 %d  (%s)" % (dest, rows, scoped, summary.get("stored", "")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
