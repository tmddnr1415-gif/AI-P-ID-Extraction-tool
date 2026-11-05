"""hotfix132 — 운영 배치 · 로그 회전 · 끄기 단추 · exe 창 제목."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "spike"))


def _bat(name: str) -> str:
    raw = (ROOT / name).read_bytes()
    raw.decode("ascii")
    assert raw.count(b"\n") == raw.count(b"\r\n"), name
    return raw.decode("ascii")


# ---------------------------------------------------------------- 배치
def test_every_start_bat_checks_python_311_first():
    for name in ("start.bat", "run_lan_service.bat", "check_pid_server.bat", "install_autostart_lan.bat", "setup.bat",
                 "backup_pid_data.bat", "stop_pid_server.bat", "restart_pid_server.bat"):
        body = _bat(name)
        assert "version_info>=(3,11)" in body, name
        assert "3.10" not in body, name


def test_service_checks_packages_and_slows_down_after_quick_failures():
    body = _bat("run_lan_service.bat")
    pkg, pre = body.index("find_spec"), body.index("--preflight")
    assert pkg < pre                                          # 패키지가 없으면 '포트를 누가 잡고 있다' 로 새지 않는다
    assert "server.fastfail" in body and "GEQ 5" in body and "timeout /t 60" in body
    assert "rem set PID_DATA_DIR=" in body


def test_start_bat_defaults():
    body = _bat("start.bat")
    assert "set RELOAD=\r\n" in body and '"%%a"=="--reload"' in body
    assert "set PYTHONUTF8=1" in body and "--no-access-log --no-server-header" in body
    assert "lan_check.preflight(%PORT%)" in body               # 다른 포트로 켤 때 8000 의 서버를 보고 멈추지 않는다
    assert "Delete the app\\_data folder" not in body


def test_build_never_leaves_the_build_stamp():
    body = _bat("build.bat")
    assert body.count("del app\\_build.json") >= 4             # 실패 셋 + 끝


def test_setup_installs_offline_first_and_checks_without_preflight():
    body = _bat("setup.bat")
    assert "--no-index --find-links wheels -r requirements-win.txt" in body
    assert "-r requirements.txt" in body and "-m venv .venv" in body
    assert "-m app.lan_check\r\n" in body and "--preflight" not in body


def test_autostart_says_logon_of_this_user():
    body = _bat("install_autostart_lan.bat")
    assert "THIS user (not at boot)" in body
    assert body.index("find_spec") < body.index("schtasks /Create")


# ---------------------------------------------------------------- 끄기 단추
def test_stop_kills_the_listener_and_does_not_wait_for_a_restart(monkeypatch, capsys):
    import restart_pid_server as r
    killed, waited = [], []
    monkeypatch.setattr(r, "_netstat_text", lambda: "  TCP    0.0.0.0:8000   0.0.0.0:0   LISTENING   4120\n")
    monkeypatch.setattr(r, "_kill", lambda pids: killed.extend(pids))
    monkeypatch.setattr(r, "_get", lambda *a, **k: {"jobs": []})
    monkeypatch.setattr(r.time, "sleep", lambda s: waited.append(s))
    assert r.main(["8000", "--stop", "--yes"]) == 0
    out = capsys.readouterr().out
    assert killed == [4120] and not waited
    assert "서비스 창" in out and "10초" in out


def test_stop_with_nothing_on_the_port(monkeypatch, capsys):
    import restart_pid_server as r
    monkeypatch.setattr(r, "_netstat_text", lambda: "")
    assert r.main(["8000", "--stop"]) == 0
    assert "이미 꺼져" in capsys.readouterr().out


def test_stop_bat_says_close_the_service_window():
    body = _bat("stop_pid_server.bat")
    assert "spike\\restart_pid_server.py 8000 --stop" in body
    assert "close it too" in body and "10 s" in body


# ---------------------------------------------------------------- 로그
def test_lan_serve_rotates_its_own_log(tmp_path):
    from app import lan_serve
    p = tmp_path / "server.log"
    log = lan_serve._RotatingLog(p, open(p, "ab", buffering=0), limit=1000, keep=3)
    for _ in range(50):
        log.write(b"x" * 99 + b"\n")
    log.close()
    sizes = [q.stat().st_size for q in sorted(tmp_path.glob("server.log*"))]
    assert (tmp_path / "server.log.1").exists() and (tmp_path / "server.log.3").exists()
    assert not (tmp_path / "server.log.4").exists() and max(sizes) <= 1000


def test_lan_serve_marks_a_quick_failure(tmp_path):
    from app import lan_serve
    lan_serve._mark_fastfail(tmp_path, 3.0)
    assert (tmp_path / lan_serve.FASTFAIL).exists()
    lan_serve._mark_fastfail(tmp_path, 600.0)
    assert not (tmp_path / lan_serve.FASTFAIL).exists()


def test_desktop_tees_share_one_rotating_file(tmp_path, monkeypatch):
    from app import desktop
    monkeypatch.setattr(desktop, "LOG_LIMIT", 500)
    monkeypatch.setattr(desktop._LogFile, "_open", {})
    p = tmp_path / "logs" / "server.log"
    lf = desktop._LogFile.shared(p)
    lf.limit = 500
    out, err = desktop._Tee(None, p), desktop._Tee(None, p)
    assert out.log is err.log is lf                            # 한 파일 객체 — 한쪽이 밀어도 다른 쪽이 옛 핸들을 쥐지 않는다
    for i in range(40):
        (out if i % 2 else err).write("한글 로그 줄 — %02d\n" % i)
    out.flush()
    assert (tmp_path / "logs" / "server.log.1").exists()
    assert out.file is err.file and not out.closed
    out.file.close()


def test_desktop_turns_off_access_log_and_reads_the_product_name():
    src = (ROOT / "app" / "desktop.py").read_text(encoding="utf-8")
    assert "access_log=False" in src and "server_header=False" in src
    assert "uvicorn.run(app, host=host" in src
    from app import desktop
    assert desktop._product().get("name") == "계장 설계 도구"
    desktop._set_title("x")                                    # 윈도우가 아니어도 조용히 넘긴다
