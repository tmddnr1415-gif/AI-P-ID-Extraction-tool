"""hotfix132 (D1) — 분석 프로세스가 죽거나 서버가 다시 뜨면 '분석 중' 에 영원히 멈추던 것.

store._stale 이 ① 따로 도는 분석 pid 가 없거나 ② 지금 서버가 뜨기 전 것이거나 ③ 10분 조용하면 failed 로 적어 돌려준다 ·
그러면 지울 수 있다.  살아 있는 분석(기록 최신 · 이 서버가 띄움)은 running 그대로 · 409 그대로 (test_logic_l22_user 규칙)."""
from __future__ import annotations

import json
import os
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.logic import api, store


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def _job(st: dict, mtime_ago: float = 0):
    job, d = store.new_job("toy.pdf")
    cur = store.read_status(d)
    cur.update(st)
    store.write_status(d, cur)
    if mtime_ago:
        t = time.time() - mtime_ago
        os.utime(d / "status.json", (t, t))
    return job, d


def test_dead_pid_becomes_failed_and_can_be_deleted(client):
    job, d = _job({"state": "running", "pid": 999999, "started": time.time() - 3600}, mtime_ago=3600)
    r = client.get(f"/logic/api/jobs/{job}").json()
    assert r["state"] == "failed" and "끊겼습니다" in r["error"] and "KeyError" not in r["error"]
    assert json.loads((d / "status.json").read_text(encoding="utf-8"))["state"] == "failed"
    assert any(j["id"] == job and j["state"] == "failed" for j in client.get("/logic/api/jobs").json()["jobs"])
    assert client.delete(f"/logic/api/jobs/{job}", params={"author": "홍길동"}).status_code == 204
    assert not d.exists()


def test_live_pid_from_this_server_stays_running(client):
    job, d = _job({"state": "running", "pid": os.getpid(), "boot": api._BOOT, "started": time.time()})
    assert client.get(f"/logic/api/jobs/{job}").json()["state"] == "running"
    assert client.delete(f"/logic/api/jobs/{job}", params={"author": "홍길동"}).status_code == 409


def test_running_without_pid_but_fresh_keeps_409(client):
    """기존 test_logic_l22_user 꼴 — pid 없이 state=running 만 적어도 기록이 최신 · 기동 뒤 생성이면 분석 중으로 본다."""
    job, d = _job({"state": "running"})
    assert client.get(f"/logic/api/jobs/{job}").json()["state"] == "running"
    assert client.delete(f"/logic/api/jobs/{job}", params={"author": "홍길동"}).status_code == 409


def test_started_before_this_server_booted_is_failed(client, monkeypatch):
    """exe(스레드) 꼴 — pid 가 서버 자신이라도 다른 기동(boot) 의 것이면 끊긴 것."""
    job, d = _job({"state": "running", "pid": os.getpid(), "boot": api._BOOT - 100, "started": time.time()})
    assert client.get(f"/logic/api/jobs/{job}").json()["state"] == "failed"
    job2, d2 = _job({"state": "queued"}, mtime_ago=0)
    # boot 도 pid 도 없고 기록이 서버 기동보다 오래됐으면 (옛 서버의 것)
    old = store.BOOT - 50
    st = store.read_status(d2)
    st["created"] = old
    store.write_status(d2, st)
    os.utime(d2 / "status.json", (old, old))
    assert client.get(f"/logic/api/jobs/{job2}").json()["state"] == "failed"


def test_quiet_too_long_is_failed_even_with_boot(client):
    job, d = _job({"state": "running", "boot": api._BOOT, "started": time.time() - 1000}, mtime_ago=store.STALE_SEC + 5)
    assert client.get(f"/logic/api/jobs/{job}").json()["state"] == "failed"


def test_alive_check_is_monkeypatchable_for_windows(client, monkeypatch):
    monkeypatch.setattr(store, "_alive", lambda pid: True)
    job, d = _job({"state": "running", "pid": 999999, "started": time.time()})
    assert client.get(f"/logic/api/jobs/{job}").json()["state"] == "running"
    monkeypatch.setattr(store, "_alive", lambda pid: False)
    assert client.get(f"/logic/api/jobs/{job}").json()["state"] == "failed"


def test_start_writes_boot_token(client, monkeypatch, tmp_path):
    started = []
    monkeypatch.setattr(api.subprocess, "Popen", lambda *a, **k: started.append(a))
    job, d = store.new_job("toy.pdf")
    api._start(d)
    assert store.read_status(d)["boot"] == api._BOOT and started


def test_run_records_pid(tmp_path, monkeypatch):
    from app.logic import run as run_mod
    job, d = store.new_job("toy.pdf")
    seen = {}

    def fake_analyse(path, progress=None, partial=None):
        seen.update(store.read_status(d))
        raise RuntimeError("stop")
    import app.logic.analyse as analyse
    monkeypatch.setattr(analyse, "analyse", fake_analyse)
    run_mod.run(d)
    assert seen.get("pid") == os.getpid() and seen.get("state") == "running"
    assert store.read_status(d)["state"] == "failed"


def test_windows_alive_never_uses_os_kill(monkeypatch):
    """Windows 의 os.kill 은 살아 있는 분석을 죽인다 — 그 길을 타지 않는다."""
    calls = []
    monkeypatch.setattr(store.os, "name", "nt")
    monkeypatch.setattr(store.os, "kill", lambda *a: calls.append(a))
    try:
        store._alive(12345)
    except Exception:
        pass
    assert calls == []
