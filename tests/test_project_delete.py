"""프로젝트 통째 삭제 — **첫 화면에서 사라지되 안정 ID 는 회수하지 않는다** (46회차 [C]).

지키는 것 다섯:
    ① 확인 값이 프로젝트 이름과 같아야 한다 (실수 방지)
    ② 지운 뒤 `/home` 에서 사라진다
    ③ **안정 ID 장부는 무덤에 남고**, 같은 이름으로 다시 만들면 이어받는다 (§7.3)
    ④ 누가 언제 지웠는지 `deletion_log` 에 분석마다 남는다
    ⑤ 지운 뒤 고아(출력·업로드)가 생기지 않는다 — [B] 경고가 다시 뜨면 안 된다
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _app(tmp_path):
    import os
    os.environ["PID_DATA_DIR"] = str(tmp_path)
    for mod in [m for m in list(sys.modules) if m.startswith("app")]:
        del sys.modules[mod]
    from fastapi.testclient import TestClient
    from app import main
    return TestClient(main.app), main


def _project_with_job(main, name="P1", rows=3):
    from app import db, revisions
    revisions.create_project(main.DATA_DIR, name)
    job = "j" + name.lower()
    up = main.UPLOADS
    up.mkdir(parents=True, exist_ok=True)
    pdf = up / f"{job}_x.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    main.CON.execute(
        "INSERT INTO job (id,pdf_name,pdf_sha256,pdf_path,created_at,status,"
        "progress,message,fingerprint,project,revision)"
        " VALUES (?,?,?,?,?,'done',1.0,'','',?,'A')",
        (job, "x.pdf", job, str(pdf), time.time(), revisions.safe_name(name)))
    for i in range(rows):
        db.add_row(main.CON, job, page_no=1, tab="FIELD", drawing_no="D-1",
                   values={"type": "PI"})
    main.CON.commit()
    return job, pdf


def test_the_confirm_value_must_match(tmp_path):
    c, main = _app(tmp_path)
    _project_with_job(main)
    r = c.request("DELETE", "/projects/P1", data={"confirm": "wrong", "author": "a"})
    assert r.status_code == 400
    assert c.get("/home").json()["projects"]


def test_it_disappears_from_the_first_screen(tmp_path):
    c, main = _app(tmp_path)
    job, pdf = _project_with_job(main)
    pre = c.get("/projects/P1/deletion_preview").json()
    assert pre["job_count"] == 1 and pre["rows"] == 3 and pre["id_registry_kept"]
    out = c.request("DELETE", "/projects/P1",
                    data={"confirm": "P1", "author": "sc.y"}).json()
    assert out["job_count"] == 1
    assert [p["name"] for p in c.get("/home").json()["projects"]] == []
    assert not pdf.exists()                     # 업로드도 함께 지운다


def test_the_id_ledger_survives_and_is_inherited(tmp_path):
    c, main = _app(tmp_path)
    from app import revisions
    _project_with_job(main)
    d = revisions.project_dir(main.DATA_DIR, "P1")
    reg = revisions.Registry.load(d / "id_registry.json")
    reg.data["ids"]["10ABC-007"] = {"id": "10ABC-007", "system_code": "10ABC",
                                    "system_code_basis": "t", "seq": 7,
                                    "first_revision": "A", "drawing_no": "D-1",
                                    "status": "active", "x": 0, "y": 0}
    reg.save(d / "id_registry.json")
    c.request("DELETE", "/projects/P1", data={"confirm": "P1", "author": "sc.y"})
    graves = revisions.tombstones(main.DATA_DIR, "P1")
    assert graves, "장부 무덤이 없다"
    assert json.loads((graves[0] / "deleted.json").read_text())["author"] == "sc.y"
    again = revisions.create_project(main.DATA_DIR, "P1")
    reg2 = revisions.Registry.load(
        revisions.project_dir(main.DATA_DIR, again["name"]) / "id_registry.json")
    assert reg2.next_seq("10ABC") == 8          # 1 로 돌아가지 않는다


def test_the_grave_is_not_a_project(tmp_path):
    c, main = _app(tmp_path)
    from app import revisions
    _project_with_job(main)
    c.request("DELETE", "/projects/P1", data={"confirm": "P1", "author": "a"})
    assert revisions.list_projects(main.DATA_DIR) == []


def test_who_deleted_it_is_recorded(tmp_path):
    c, main = _app(tmp_path)
    from app import db
    _project_with_job(main)
    c.request("DELETE", "/projects/P1", data={"confirm": "P1", "author": "hyomi"})
    log = db.deletion_log(main.CON)
    assert log and log[0]["author"] == "hyomi" and log[0]["project"] == "P1"


def test_no_orphans_are_left_behind(tmp_path):
    c, main = _app(tmp_path)
    from app import audit
    _project_with_job(main)
    (main.DATA_DIR / "outputs" / "rev999").mkdir(parents=True, exist_ok=True)
    c.request("DELETE", "/projects/P1", data={"confirm": "P1", "author": "a"})
    left = audit.run(main.CON, main.DATA_DIR)["leftovers"]
    assert left["orphan_uploads"] == [] and left["orphan_outputs"] == []


def test_a_running_analysis_blocks_the_delete(tmp_path):
    c, main = _app(tmp_path)
    job, _ = _project_with_job(main, "P2")
    main.CON.execute("UPDATE job SET status='running' WHERE id=?", (job,))
    main.CON.commit()
    r = c.request("DELETE", "/projects/P2", data={"confirm": "P2", "author": "a"})
    assert r.status_code == 409
