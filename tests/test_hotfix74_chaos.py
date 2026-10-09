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


def test_open_tab_learns_that_the_server_was_updated():
    """서버에 꾸러미를 적용해도 열어 둔 탭은 옛 app.js 다 — 딱지가 다르면 노란 띠와 [새로고침]."""
    js = (Path(main.__file__).resolve().parent / "static" / "app.js").read_text(encoding="utf-8")
    assert "const MY_UI_TAG" in js and "async function checkStaleUi()" in js
    assert "setInterval(checkStaleUi, 120000)" in js
    up = js.split("function netUp() {", 1)[1].split("\n}", 1)[0]
    assert "checkStaleUi()" in up


def test_short_screens_keep_the_list_reachable():
    """1366×768 을 125% 로 쓰는 노트북(CSS 614px)에서 오른쪽 칸의 목록·근거가 칸 밖으로 잘려 닿을 수 없었다
    (`spike/ui_small_screens.py`).  키 작은 화면에서는 오른쪽 칸이 굴러가고, 나란히 보기는 예외다."""
    import re
    css = (Path(__file__).resolve().parent.parent / "app/static/styles.css").read_text(encoding="utf-8")
    m = re.search(r"@media \(max-height: 760px\) \{(.*?)\n\}", css, re.S)
    assert m, "키 작은 화면 규칙이 없다"
    body = m.group(1)
    assert "#right { overflow-y: auto; }" in body
    assert "#right.compare { overflow-y: hidden; }" in body
    assert ".build {" in body and "text-overflow: ellipsis" in body
    # 아주 키 작은 화면(200% 확대 · 800×600)은 페이지가 굴러가고 도면·목록 칸이 화면 한 장 높이를 갖는다
    m2 = re.search(r"@media \(max-height: 620px\) \{(.*?)\n\}", css, re.S)
    assert m2 and "#split { flex: none; height: max(420px, calc(100vh - 16px)); }" in m2.group(1)


def test_enter_while_composing_hangul_does_not_reach_handlers():
    """한글 조합 중의 Enter 는 글자를 확정하는 키다 — 창의 캡처 단계에서 한 번 걸러 처리기 열한 곳에 닿지 않게 한다
    (브라우저 실측: 조합 중 Enter 뒤에도 칸이 편집 중 · 보통 Enter 는 저장)."""
    js = (Path(__file__).resolve().parent.parent / "app/static/app.js").read_text(encoding="utf-8")
    i = js.index('if (ev.key === "Enter" && (ev.isComposing || ev.keyCode === 229)) ev.stopImmediatePropagation();')
    head = js[max(0, i - 200):i]
    assert 'window.addEventListener("keydown"' in head
    tail = js[i:i + 120]
    assert "}, true);" in tail                     # 캡처 단계 — 다른 어떤 처리기보다 먼저
    assert "preventDefault" not in js[i - 200:i + 120]   # 입력기가 글자를 확정해야 하므로 기본 동작은 막지 않는다


def test_excel_export_is_serialised_per_snapshot():
    """두 요청이 같은 스냅샷 폴더의 같은 파일에 양식을 복사·재열기 하다 서로의 반쯤 쓴 파일을 읽었다
    (`spike/excel_race.py`: 잠금 전 24회 중 17~22회 500 → 잠금 뒤 0)."""
    import importlib
    main = importlib.import_module("app.main")
    assert main._excel_lock(7) is main._excel_lock(7)
    assert main._excel_lock(7) is not main._excel_lock(8)
    src = (Path(__file__).resolve().parent.parent / "app/main.py").read_text(encoding="utf-8")
    i = src.index("def revision_excel(revision_id: int):")
    assert "with _excel_lock(revision_id):" in src[i:i + 300]


def test_record_making_buttons_ignore_a_second_press():
    """VOC 접수 · 마크업 저장 · 신고 접수 · 메모 저장 — 처리 중의 두 번째 누름은 무시한다
    (`spike/ui_double_click.py`: 옛 코드 VOC 2건 · 메모 2판 → 1 · 1)."""
    js = (Path(__file__).resolve().parent.parent / "app/static/app.js").read_text(encoding="utf-8")
    assert "function guarded(fn)" in js
    for needle in ('$("#vc-save").onclick = guarded(', '$("#mk-save").onclick = guarded(', "const save = guarded("):
        assert needle in js, needle
    i = js.index("async function saveMemo() {")
    assert "if (S._memoBusy) return;" in js[i:i + 400]
