"""hotfix57 — 다른 메뉴로 갔다 와도 분석 화면이 이어진다.

분석은 서버에서 계속 돈다.  사라지던 것은 화면이었다 — 대시보드가 메뉴를 옮길 때 iframe 을
새로 만들고, 새 iframe 은 주소에 분석 번호가 없어 첫 화면으로 열렸다.
"""
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")


def _fn(name):
    i = JS.index(f"function {name}(")
    j = JS.index("\n}\n", i)
    return JS[i:j]


def test_watch_remembers_the_job_and_puts_it_in_the_address():
    body = _fn("watch")
    assert "rememberWatch(jobId)" in body
    assert 'location.search + "#" + jobId' in body          # query(?embed=1 …) 를 지키며


def test_boot_without_an_address_resumes_the_watched_job():
    assert re.search(r"if \(location\.hash\.length > 1\) open\(hashParts\(\)\[0\]\);\s*else resumeWatched\(\);", JS)
    body = _fn("resumeWatched")
    assert 'job.status === "done"' in body and "open(id)" in body
    assert "watch(id" in body
    assert 'job.status === "cancelled"' in body and "forgetWatch(id)" in body


def test_leaving_a_running_analysis_does_not_forget_it():
    body = _fn("toFirstScreen")
    assert "S.watchEnded" in body and "forgetWatch(S.watching)" in body
    assert body.index("S.watchEnded") < body.index("forgetWatch")


def test_seen_results_are_not_pulled_back():
    assert "forgetWatch(jobId)" in _fn("open")


def test_resumed_after_done_goes_to_results_not_an_empty_summary():
    body = _fn("watch")
    assert 'd.status === "done" && !d.summary' in body


def test_elapsed_continues_from_the_server_clock():
    assert "startElapsed((what || {}).running_s)" in _fn("watch")
    from app import main
    now = time.time()
    assert main._running_s({"started_at": now - 42, "status": "running"}) >= 41.9
    assert main._running_s({"started_at": now - 42, "status": "done"}) == 0.0
    assert main._running_s({"started_at": None, "status": "running"}) == 0.0
