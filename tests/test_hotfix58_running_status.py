"""hotfix58 — P&ID 분석 메뉴는 언제나 첫 화면으로 열고, 첫 화면이 분석 중 현황을 보인다.

hotfix57 은 지켜보던 분석의 진행 화면으로 끌고 갔다.  사용자 요구는 반대 — *다른 메뉴에
다녀오거나 · 진행 화면에서 나가거나 · 메뉴를 다시 불러도 첫 화면* 이고, 대신 '최근 분석
이력' 에서 진행 막대 · % · 남은 시간을 보인다.  남은 시간은 이 서버에서 끝난 분석의 장당
시간 중앙값 × 장수로 낸 추정이고 근거를 함께 적는다 (없으면 없다고 말한다).
"""
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")


def _fn(name):
    i = JS.index(f"function {name}(")
    j = JS.index("\n}\n", i)
    return JS[i:j]


def _job(**kw):
    base = {"id": "j", "status": "done", "message": "", "sheets_done": 0, "sheets_total": 0,
            "page_count": 10, "input_kind": "PDF", "started_at": 0.0, "finished_at": 0.0,
            "created_at": 0.0}
    base.update(kw)
    return base


def test_no_auto_resume_on_boot():
    for gone in ("resumeWatched", "rememberWatch", "forgetWatch", "pid.watching"):
        assert gone not in JS
    assert re.search(r"if \(location\.hash\.length > 1\) open\(hashParts\(\)\[0\]\);\n", JS)
    assert '"#" + jobId' not in _fn("watch")                 # 진행 화면이 주소에 분석을 적지 않는다


def test_progress_screen_can_leave_while_running():
    assert 'id="prog-leave"' in HTML and "분석은 계속됩니다" in HTML
    assert '$req("#prog-leave").addEventListener("click", toFirstScreen)' in JS
    body = _fn("toFirstScreen")
    assert "S.watchSrc.close()" in body and "stopElapsed()" in body
    nav = JS[JS.index('$req("#nav-home")'):JS.index('$req("#nav-projects")')]
    assert "toFirstScreen()" in nav and "return;" not in nav   # 분석 중에도 첫 화면으로


def test_recent_list_shows_live_rows_first_with_a_bar():
    body = _fn("renderDashboard")
    assert 'runs.filter(r => r.status === "running").concat(' in body and 'data-live=' in body and "run-live" in body
    assert "renderLive()" in body
    assert 'role="progressbar"' in _fn("liveBar")
    assert 'fetch("/running")' in _fn("pollRunning")


def test_pace_is_the_median_seconds_per_page_of_finished_jobs():
    from app import main
    T = 1_700_000_000.0
    jobs = [_job(started_at=T, finished_at=T+100, page_count=10),     # 10 s/page
            _job(started_at=T, finished_at=T+300, page_count=10),     # 30
            _job(started_at=T, finished_at=T+200, page_count=10),     # 20
            _job(status="failed", started_at=T, finished_at=T+9, page_count=10),
            _job(input_kind="DXF", started_at=T, finished_at=T+50, page_count=10)]
    pace = main._pace_history(jobs)
    assert pace["PDF"] == {"sec_per_page": 20.0, "n": 3}
    assert pace["DXF"]["n"] == 1


def test_run_status_estimates_from_history_and_says_when_it_cannot():
    from app import main
    now = time.time()
    run = _job(status="running", started_at=now - 50, page_count=10)
    st = main._run_status(run, {"PDF": {"sec_per_page": 20.0, "n": 3}})
    assert st["expected_s"] == 200 and 24 <= st["percent"] <= 25 and 149 <= st["eta_s"] <= 150
    assert st["basis"] == {"jobs": 3, "sec_per_page": 20.0} and not st["over"]
    late = main._run_status(_job(status="running", started_at=now - 500, page_count=10),
                            {"PDF": {"sec_per_page": 20.0, "n": 3}})
    assert late["percent"] == 99 and late["over"] and late["eta_s"] is None
    blind = main._run_status(run, {})
    assert blind["percent"] is None and blind["eta_s"] is None and blind["basis"] is None


def test_running_endpoint_orders_queue(tmp_path):
    from app import main
    from fastapi.testclient import TestClient
    c = TestClient(main.app)
    r = c.get("/running")
    assert r.status_code == 200 and set(r.json()) == {"jobs", "pace"}
