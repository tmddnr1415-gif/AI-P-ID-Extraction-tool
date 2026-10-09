"""hotfix42 — 품질팀 시뮬레이션(`spike/qa_sim.py`)이 찾은 결함의 재발 방지.

① 분석을 지우면 장부의 그 리비전에 `deleted` 가 적히고, 첫 화면은 그 리비전을 **링크 없이** 보이며,
   다음 업로드의 비교 대상 선택지와 기본값에서 빠진다 (전에는 지워진 job 으로 가는 링크가 남아
   누르면 "no such job" 이었고, 기본 비교 대상이 지워진 리비전이었다).
"""
from __future__ import annotations

import json
from pathlib import Path

from app import revisions

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")


def _project(tmp_path):
    revisions.create_project(tmp_path, "QA")
    for rev, jid in (("Rev.A", "jobA"), ("Rev.B", "jobB")):
        revisions.record_revision(tmp_path, "QA", rev, job_id=jid, pdf_name=f"{rev}.pdf", compared_with="",
                                  result={"counts": {}, "deleted_candidates": [], "sheets": {}})
    return revisions.load_project(tmp_path, "QA")


def test_deleting_an_analysis_marks_the_ledger_and_hides_it_from_compare_targets(tmp_path):
    meta = _project(tmp_path)
    assert revisions.compare_choices(meta) == ["Rev.A", "Rev.B"]
    assert revisions.default_compare_target(meta) == "Rev.B"
    hit = revisions.mark_revision_deleted(tmp_path, "QA", "jobB", "QA팀")
    assert hit and hit["revision"] == "Rev.B"
    meta = revisions.load_project(tmp_path, "QA")
    entry = next(r for r in meta["revisions"] if r["revision"] == "Rev.B")
    assert entry["deleted"]["author"] == "QA팀" and entry["deleted"]["at"] > 0
    # 항목은 남는다 (ID 장부·대조 기록은 그 리비전의 사실) — 글자도 건너뛰지 않고 이어 간다
    assert [r["revision"] for r in meta["revisions"]] == ["Rev.A", "Rev.B"]
    assert revisions.next_revision(meta) == "Rev.C"
    assert revisions.compare_choices(meta) == ["Rev.A"]
    assert revisions.default_compare_target(meta) == "Rev.A"
    # 모르는 job 은 아무것도 안 적는다
    assert revisions.mark_revision_deleted(tmp_path, "QA", "nope") is None
    assert revisions.mark_revision_deleted(tmp_path, "NOPE", "jobA") is None


def test_delete_endpoint_marks_the_ledger_and_home_renders_no_dead_link():
    body = MAIN[MAIN.index("def delete_job("):MAIN.index("def delete_job(") + 2500]
    assert "revisions.mark_revision_deleted(" in body
    pub = MAIN[MAIN.index("def _project_public("):MAIN.index("def _project_public(") + 2000]
    assert '"missing": job is None' in pub
    row = JS[JS.index("function revRow("):JS.index("function delButton(")]
    assert "r.missing || r.deleted" in row and "분석 기록 지워짐" in row
    # 지워진 리비전 갈래에는 링크(href)도 삭제 버튼도 없다
    branch = row[row.index("r.missing || r.deleted"):row.index("return `<div class=\"revwrap rv-tl${")]   # hotfix61 카드
    assert "href" not in branch and "delButton" not in branch


def test_interrupted_analyses_are_recovered_at_startup(tmp_path, monkeypatch):
    """서버 재시작 — `running` 은 실패(사유·멈춘 단계)로, `queued` 는 다시 줄에."""
    import importlib, os
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    from app import db
    con = db.connect(tmp_path / "app.db")
    con.execute("INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, status, progress, message, created_at)"
                " VALUES ('r1','a.pdf','x','/x','running',0.4,'measuring sheet 3 of 6',1)")
    con.execute("INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, status, progress, message, created_at)"
                " VALUES ('q1','b.pdf','y','/y','queued',0.0,'',2)")
    con.commit()
    src = MAIN
    body = src[src.index("def _recover_interrupted("):src.index("# 끊긴 분석 정리와 작업 스레드는")]
    assert '"queued"' in body and '"running"' in body and "set_stopped_stage" in body and '"failed"' in body
    # 함수만 따로 돌려 본다 (실 모듈을 import 하면 실 DB 에 닿을 수 있다 — 17회차 격리)
    import queue
    ns = {"db": db, "CON": con, "_JOBS": queue.Queue(),
          "_stopped_stage": lambda jid: con.execute("SELECT message FROM job WHERE id=?", (jid,)).fetchone()[0],
          "print": lambda *a, **k: None}
    exec(body, ns)
    out = ns["_recover_interrupted"]()
    assert out == {"requeued": ["q1"], "failed": ["r1"]}
    r1 = con.execute("SELECT status, message, stopped_stage, error_detail FROM job WHERE id='r1'").fetchone()
    assert r1[0] == "failed" and "다시 시작" in r1[1] and r1[2] == "measuring sheet 3 of 6" and "interrupted" in r1[3]
    assert con.execute("SELECT status FROM job WHERE id='q1'").fetchone()[0] == "queued"
    assert ns["_JOBS"].get_nowait() == "q1"


def test_the_list_keeps_a_minimum_height_and_panels_start_folded_on_short_screens():
    """QA 시뮬레이션: 1700×1000 에서 QFE 를 열면 목록 높이가 0 이었다 (판 넷이 오른쪽을 다 먹음)."""
    css = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
    assert "#gridwrap { flex: 1 1 auto; overflow: auto; min-height: 160px; }" in css
    assert "flex: 0 1 auto; height: 232px; min-height: 96px;" in css          # 근거 패널은 줄어들 수 있다
    assert ".sheet-panel { margin-top: 6px; max-height: 120px; }" in css
    for fn in ("function _sheetFolded", "function _multFolded"):
        body = JS[JS.index(fn):JS.index(fn) + 500]
        assert "window.innerHeight < 860" in body and "v0 === null" in body
