"""hotfix56 — 분석은 다른 프로세스에서 돈다.  서버는 분석 중에도 대답한다.

현장: 대시보드(8080)가 P&ID 메뉴를 누를 때마다 `/version` 을 3초 안에 받아야 하는데, 분석의
`layout` 단계가 서버 프로세스의 GIL 을 쥐어 "P&ID 서버가 꺼져 있습니다" 가 떴다 (TC2 60장
실측: 120초 동안 3초 초과 5번).
"""
import ast
import os
import threading
import time
from pathlib import Path

import importlib

import pytest

from app import analysis_proc as _loaded  # noqa: F401  (아래 픽스처가 지금 것으로 바꾼다)

ROOT = Path(__file__).resolve().parents[1]
T = "tests._hotfix56_targets:"


@pytest.fixture(autouse=True)
def _child_mode(monkeypatch):
    # 다른 시험이 `app.*` 모듈을 다시 읽으면 위에서 가져온 모듈이 낡는다 — spawn 은 함수를
    # 이름으로 피클하므로 낡은 `_child` 를 거부한다.  지금 등록된 것을 쓴다.
    global analysis_proc
    analysis_proc = importlib.import_module("app.analysis_proc")
    monkeypatch.delenv("PID_ANALYSIS_INPROCESS", raising=False)


analysis_proc = _loaded


def test_runs_in_another_process_and_relays_progress(tmp_path):
    seen = []

    def progress(done, total, message, sheets=None, plan=None, drawing=None):
        seen.append((done, total, message, sheets, plan, drawing))

    out = analysis_proc.run(tmp_path / "x.pdf", progress, tmp_path / "work",
                            target=T + "ok", reference=None, declared_mode="epc")
    assert out["pid"] != os.getpid()                  # 서버 프로세스가 아니다
    assert out["kw"] == {"reference": None, "declared_mode": "epc"}
    assert out["rows"] == [{"a": (1, 2)}]             # 튜플까지 그대로 온다 (피클)
    assert seen[0] == (1, 3, "layout", (1, 3), [{"page": 1}], "D-1")
    assert seen[1][:3] == (2, 3, "detect")
    assert list((tmp_path / "work").iterdir()) == []  # 결과 파일은 지운다


def test_known_failures_keep_their_type_and_sentence(tmp_path):
    from app import pipeline
    with pytest.raises(pipeline.LegendUnavailable) as e:
        analysis_proc.run(tmp_path / "x.pdf", lambda *a, **k: None, tmp_path,
                          target=T + "legend_missing")
    assert str(e.value) == "범례도 프로필도 없습니다 — 시험"
    assert "legend_missing" in e.value.child_traceback


def test_unknown_failure_carries_the_child_traceback(tmp_path):
    with pytest.raises(analysis_proc.ChildFailed) as e:
        analysis_proc.run(tmp_path / "x.pdf", lambda *a, **k: None, tmp_path,
                          target=T + "boom")
    assert "zero-size array" in str(e.value)
    assert "ValueError" in e.value.detail and "boom" in e.value.detail


def test_a_dying_child_fails_the_job_not_the_server(tmp_path):
    with pytest.raises(analysis_proc.ChildFailed) as e:
        analysis_proc.run(tmp_path / "x.pdf", lambda *a, **k: None, tmp_path,
                          target=T + "dies")
    assert "종료 코드 3" in str(e.value)


def test_cancel_from_progress_stops_the_child(tmp_path):
    class Cancelled(Exception):
        pass

    calls = []

    def progress(done, total, message, **kw):
        calls.append(done)
        if len(calls) == 3:
            raise Cancelled()

    t = time.time()
    with pytest.raises(Cancelled):
        analysis_proc.run(tmp_path / "x.pdf", progress, tmp_path, target=T + "slow")
    assert time.time() - t < 20                       # 30초 걸릴 일을 기다리지 않는다
    import multiprocessing
    assert not [p for p in multiprocessing.active_children() if p.name == "pid-analysis"]


def test_parent_keeps_answering_while_the_child_is_busy(tmp_path):
    """자식이 CPU 를 쥐는 동안 부모의 다른 스레드가 제때 돈다 — 대시보드가 겪은 것의 반대."""
    worst = [0.0]
    stop = threading.Event()

    def ticker():
        while not stop.is_set():
            t = time.perf_counter()
            time.sleep(0.01)
            worst[0] = max(worst[0], time.perf_counter() - t)

    th = threading.Thread(target=ticker)
    th.start()
    try:
        out = analysis_proc.run(tmp_path / "x.pdf", lambda *a, **k: None, tmp_path,
                                target=T + "busy")
    finally:
        stop.set(); th.join()
    assert out["n"] > 0
    assert worst[0] < 1.0


def test_switch_runs_in_process(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_ANALYSIS_INPROCESS", "1")
    out = analysis_proc.run(tmp_path / "x.pdf", lambda *a, **k: None, tmp_path,
                            target=T + "ok")
    assert out["pid"] == os.getpid()


def test_worker_goes_through_the_child_process():
    """`main._worker` 는 `pipeline.analyse` 를 직접 부르지 않는다 (소스 검사 —
    `app.main` 을 import 하면 실 DB 를 연다)."""
    src = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    fn = next(n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.FunctionDef) and n.name == "_worker")
    calls = {ast.unparse(n.func) for n in ast.walk(fn) if isinstance(n, ast.Call)}
    assert "analysis_proc.run" in calls
    assert "pipeline.analyse" not in calls


def test_child_never_imports_the_server_module():
    """자식이 app.main 을 import 하면 DB 연결 · 작업 스레드 · 끊긴 분석 정리가 또 돈다."""
    src = (ROOT / "app" / "analysis_proc.py").read_text(encoding="utf-8")
    mods = set()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Import):
            mods |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            mods |= {f"{n.module}.{a.name}" for a in n.names}
    assert "app.main" not in mods
    assert analysis_proc.TARGET == "app.pipeline:analyse"


def test_exe_entry_calls_freeze_support_first():
    src = (ROOT / "app" / "desktop.py").read_text(encoding="utf-8")
    tail = src[src.index('if __name__ == "__main__":'):]
    assert tail.index("freeze_support()") < tail.index("main()")
