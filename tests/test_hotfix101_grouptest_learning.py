"""hotfix101 — 새 프로젝트에서 그룹 시험이 '학습 중' 에 갇히던 것.

동작 학습이 실패해도 조용히 지나가 화면이 3초마다 다시 띄운 학습이 같은 자리에서 또 죽었고, 분석 프로세스가 끝 정리
(장 그림 · 학습 사전)를 하는 동안에는 '배우는 중' 표시가 없어 서버가 두 번째 학습을 띄웠다."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from app.logic import api, behavior, store
from tests.test_logic_l32_sequence import _client, _job
from tests.test_logic_l36_grouptest import _fan_bundle

ROOT = Path(__file__).resolve().parents[1]
TJS = (ROOT / "app/static/logic_test.js").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _own_data(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PID_LOGIC_WARM", "0")
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear(); api._LEARNING.clear()
    yield
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear(); api._LEARNING.clear()


def test_learning_failure_is_reported_not_looped(monkeypatch):
    job = _job(_fan_bundle())
    calls = []
    real = behavior.learn

    def boom(sheets, *a, **k):
        calls.append(1)
        raise ValueError("이 묶음에서 깨짐")
    monkeypatch.setattr(behavior, "learn", boom)
    c = _client()
    d = c.get(f"/logic/api/jobs/{job}/groups").json()
    assert d["state"] == "failed" and "이 묶음에서 깨짐" in d["error"] and d["groups"] == []
    # 같은 결과로는 저절로 다시 띄우지 않는다 (예전에는 3초마다 다시 띄워 또 죽었다)
    for _ in range(3):
        assert c.get(f"/logic/api/jobs/{job}/groups").json()["state"] == "failed"
    assert len(calls) == 1
    assert not (api._dir(job) / behavior.RUNNING).exists()
    # '다시 배우기' — 고쳐졌으면 선다
    monkeypatch.setattr(behavior, "learn", real)
    r = c.get(f"/logic/api/jobs/{job}/behavior", params={"start": 2}).json()
    assert r["state"] == "done"
    assert not (api._dir(job) / behavior.ERROR).exists()
    assert c.get(f"/logic/api/jobs/{job}/groups").json()["groups"]


def test_beat_marks_learning_before_the_first_command(monkeypatch):
    """분석이 끝 정리 중이면(표시 + 박동) 서버가 두 번째 학습을 띄우지 않는다."""
    job = _job(_fan_bundle())
    d = api._dir(job)
    hb = behavior.Beat(d, phase="prepare").start()
    started = []
    monkeypatch.setattr(api, "_start_learning", lambda j, dd: started.append(j))
    try:
        r = _client().get(f"/logic/api/jobs/{job}/groups").json()
        assert r["state"] == "running" and r["progress"]["phase"] == "prepare" and not started
    finally:
        hb.stop()
    assert not (d / behavior.RUNNING).exists()
    # 박동이 끊긴 표시(프로세스가 죽음)는 '배우는 중' 이 아니다
    store._atomic(d / behavior.RUNNING, json.dumps({"done": 0, "total": None, "beat": 20, "at": time.time() - 500}))
    assert behavior.running(d) is None
    _client().get(f"/logic/api/jobs/{job}/groups")
    assert started == [job]


def test_learn_dir_survives_unserialisable_values(monkeypatch):
    job = _job(_fan_bundle())
    real = behavior.learn

    def odd(*a, **k):
        out = real(*a, **k)
        out["items"][0]["odd"] = {1, 2}
        return out
    monkeypatch.setattr(behavior, "learn", odd)
    out = behavior.learn_dir(api._dir(job))
    assert out and behavior.load(api._dir(job))["items"][0]["odd"] == [1, 2]


def test_screen_polls_stale_and_shows_failure():
    assert '["running", "none", "stale"].includes(d.state)' in TJS
    assert 'd.state === "failed"' in TJS and "start=2" in TJS and "relearn" in TJS


def test_dead_learner_process_leaves_its_reason(monkeypatch):
    """서버가 띄운 학습 프로세스가 사유를 남기지 못하고 죽으면(가져오기 오류 · 메모리) 로그 끝을 사유로 말한다."""
    job = _job(_fan_bundle())
    d = api._dir(job)
    (d / "behavior.log").write_text("Traceback ...\nMemoryError\n", encoding="utf-8")
    api._LEARNING[job] = type("P", (), {"poll": lambda self: 1})()
    monkeypatch.setattr(api, "_start_learning", lambda j, dd: None)
    r = _client().get(f"/logic/api/jobs/{job}/groups").json()
    assert r["state"] == "failed" and "종료 코드 1" in r["error"]
    assert "MemoryError" in behavior.load_error(d)["trace"]
