"""hotfix74 — 프로세스 돌발상황 시뮬레이션(`spike/chaos_sim.py`)이 잡은 결함 넷."""
from __future__ import annotations

import ast
from pathlib import Path

from app import analysis_proc, db, main

SRC = Path(main.__file__).read_text(encoding="utf-8")


def test_background_threads_start_after_every_definition():
    """재시작 때 다시 줄 선 분석을 작업 스레드가 곧장 집어도 부를 함수가 다 있어야 한다 (S4 NameError)."""
    tree = ast.parse(SRC)
    defs = {n.name: n.lineno for n in tree.body if isinstance(n, ast.FunctionDef)}
    calls = [n for n in tree.body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
             and getattr(n.value.func, "id", "") == "_start_background"]
    assert len(calls) == 1
    start = calls[0].lineno
    for name in ("_worker", "_user_multipliers", "_user_sheet_numbers", "_user_title_block",
                 "_declared_mode", "_store_facts", "_run_comparison", "_backfill_facts"):
        assert defs[name] < start, name
    # 모듈 가운데에서 스레드를 띄우는 줄이 남아 있지 않다
    top = [n for n in tree.body if isinstance(n, ast.Expr) and "Thread" in ast.unparse(n)]
    assert top == []


def test_cancel_of_a_queued_job_is_immediate():
    jid = "q" + "0" * 11
    db.create_job(main.CON, jid, "x.pdf", "sha", Path("/nonexistent.pdf"))
    try:
        out = main.cancel_job(jid)
        assert out.get("cancelled") is True
        assert db.get_job(main.CON, jid)["status"] == "cancelled"
    finally:
        main.CON.execute("DELETE FROM job WHERE id=?", (jid,)); main.CON.commit()
        main._cancel_clear(jid)


def test_next_revision_counts_jobs_still_in_the_queue():
    main.CON.execute("DELETE FROM job WHERE project='RACE'"); main.CON.commit()
    meta = {"name": "RACE", "revisions": []}
    db.create_job(main.CON, "r" + "1" * 11, "a.pdf", "s", Path("/x.pdf"))
    db.set_job_revision(main.CON, "r" + "1" * 11, "RACE", "Rev.A", "")
    try:
        assert main._inflight_revisions("RACE", meta) == ["Rev.A"]
        pub = main._project_public(meta)
        assert pub["next_revision"] == "Rev.B"
        # 장부에 오르면 더 세지 않는다 (두 번 세지 않는다)
        meta2 = {"name": "RACE", "revisions": [{"revision": "Rev.A", "job_id": "r" + "1" * 11}]}
        assert main._inflight_revisions("RACE", meta2) == []
    finally:
        main.CON.execute("DELETE FROM job WHERE project='RACE'"); main.CON.commit()


def test_a_killed_analysis_process_says_so():
    src = Path(analysis_proc.__file__).read_text(encoding="utf-8")
    assert "err.process_died = True" in src and "도중에 끝났습니다" in src
    assert 'getattr(exc, "process_died", False)' in SRC


def test_children_follow_the_parent():
    src = Path(analysis_proc.__file__).read_text(encoding="utf-8")
    assert "mp.parent_process()" in src and "os._exit(3)" in src
    pw = (Path(main.__file__).parent / "page_warm.py").read_text(encoding="utf-8")
    assert "_follow_parent()" in pw


def test_db_waits_and_busy_answers_503():
    assert "timeout=30.0" in Path(db.__file__).read_text(encoding="utf-8")
    assert "@app.exception_handler(sqlite3.OperationalError)" in SRC


def test_screen_says_when_the_server_is_unreachable():
    js = (Path(main.__file__).parent / "static" / "app.js").read_text(encoding="utf-8")
    body = js[js.index("async function saveField("):js.index("function syncRowCell(")]
    assert "} catch (e) {" in body and "칸은 원래 값으로 돌아갑니다" in body and "return false;" in body
    # 띠 하나 — 어느 요청이 실패해도 같은 말 · 돌아오면 스스로 사라진다
    assert "function netDown()" in js and "function netUp()" in js and 'id = "net-banner"' in js
    hook = js[js.index("(function hookFetch()"):]
    assert "netDown()" in hook and "netUp()" in hook
