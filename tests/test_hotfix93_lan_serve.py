"""hotfix93 — 서비스 창이 서버를 다시 띄우지 못하던 것.

현장: 서버가 멈춘 뒤 다시 띄울 때 *"다른 프로세스가 파일을 사용 중"* 만 나오고 서버가 곧바로
멈췄다.  cmd 의 `>> logs\\server.log` 가 누가 쥔 로그를 열지 못해 서버를 아예 띄우지 않았다.
이제 `app.lan_serve` 가 로그를 연다 — 못 열면 새 이름으로 쓰고 **서버는 띄운다**.
"""
from __future__ import annotations

import inspect
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import lan_serve  # noqa: E402


def test_the_log_opens_in_shared_mode_and_falls_back_to_a_new_name(tmp_path):
    path, f = lan_serve.open_log(tmp_path)
    assert path.name == "server.log"
    path2, f2 = lan_serve.open_log(tmp_path)          # 이미 열려 있어도 함께 연다
    assert path2.name == "server.log"
    f.close(); f2.close()

    held = tmp_path / "held"
    (held / "server.log").mkdir(parents=True)         # 열 수 없는 server.log
    path3, f3 = lan_serve.open_log(held)
    f3.close()
    assert path3.name.startswith("server_") and path3.suffix == ".log"


def test_spare_logs_are_pruned(tmp_path):
    (tmp_path / "server.log").mkdir()
    made = []
    for _ in range(6):
        p, f = lan_serve.open_log(tmp_path)
        f.close()
        made.append(p)
    assert len(list(tmp_path.glob("server_*.log"))) <= lan_serve.KEEP_SPARE


def test_serve_writes_the_server_output_to_the_log_and_records_its_name(tmp_path, monkeypatch):
    monkeypatch.setattr(lan_serve, "server_command",
                        lambda port: [sys.executable, "-c", f"print('served on {port}'); raise SystemExit(7)"])
    rc = lan_serve.serve(8123, logs=tmp_path)
    assert rc == 7
    text = (tmp_path / "server.log").read_text(encoding="utf-8")
    assert "PID server starting (port 8123)" in text and "served on 8123" in text
    assert lan_serve.current_log(tmp_path) == tmp_path / "server.log"


def test_serve_still_starts_when_the_log_is_held(tmp_path, monkeypatch):
    (tmp_path / "server.log").mkdir()
    monkeypatch.setattr(lan_serve, "server_command",
                        lambda port: [sys.executable, "-c", "print('up')"])
    assert lan_serve.serve(8000, logs=tmp_path) == 0
    cur = lan_serve.current_log(tmp_path)
    assert cur.name.startswith("server_") and "up" in cur.read_text(encoding="utf-8")


def test_ctrl_c_does_not_reach_the_server_and_the_window_text_is_ascii():
    src = inspect.getsource(lan_serve.serve)
    assert "CREATE_NEW_PROCESS_GROUP" in src
    assert "except KeyboardInterrupt" in src and "timeout=1.0" in src
    for ln in inspect.getsource(lan_serve).splitlines():
        if "print(" in ln:
            ln.encode("ascii")                      # 서비스 창은 cp949 콘솔이다
