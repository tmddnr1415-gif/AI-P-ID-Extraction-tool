"""hotfix52 — 서버가 "떠 있는데" 페이지가 끝없이 로딩만 하던 것.

현장(회사 PC): hotfix51 서비스 창에 `Uvicorn running on http://0.0.0.0:8000` 이 떴는데
`http://localhost:8000/?embed=1&mode=bid` 가 열리지 않고 로딩만 했다.  "떠 있다" 와
"응답한다" 는 다른 사실이다.  멈추는 길과 막은 것:

  ① 콘솔 '선택' 모드 — 서버 창을 누르면 그 창에 글을 쓰는 프로그램이 멈추고 uvicorn 은
     요청마다 한 줄을 쓴다 → 서비스 창은 글을 쓰지 않는다 (logs\\server.log 로)
  ② 다른 서버가 8000 을 같이 잡음 → 켜기 전에 묻고(`--preflight`), 점검 파일이 PID 를 보인다
  ③ 사내망 문지기가 첫 요청에서 이 PC 이름을 DNS 로 풂 → 루프백·사설망은 재기 전에 받는다
"""
from __future__ import annotations

import asyncio
import pathlib
import socket
import sys
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import lan, lan_check  # noqa: E402


def _code(name: str) -> str:
    text = (ROOT / name).read_text(encoding="ascii")
    return "\n".join(ln for ln in text.splitlines() if not ln.strip().lower().startswith("rem"))


# ---------------------------------------------------------------- ① 창에 쓰지 않는다
def test_the_service_never_writes_the_server_to_its_window():
    body = _code("run_lan_service.bat")
    srv = [ln for ln in body.splitlines() if "uvicorn app.main:app" in ln or "PID_Extract.exe\" --lan" in ln]
    assert len(srv) == 2
    for ln in srv:
        assert ln.rstrip().endswith(">> logs\\server.log 2>&1"), ln


# ---------------------------------------------------------------- ② 켜기 전에 묻는다
def test_the_service_asks_before_it_starts():
    body = _code("run_lan_service.bat")
    pre = body.index("-m app.lan_check --preflight")
    assert pre < body.index("uvicorn app.main:app")
    # 1·2 는 파이썬이 실패한 코드와 겹친다 — 그때 영영 기다리지 않게 3·4 를 쓴다
    assert "if errorlevel 4 goto busy" in body and "if errorlevel 3 goto already" in body
    assert (lan_check.FREE, lan_check.ALREADY, lan_check.BUSY) == (0, 3, 4)
    assert "taskkill" not in body.lower()


def _free_port() -> int:
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


def test_preflight_tells_free_from_silent():
    port = _free_port()
    assert lan_check.preflight(port) == lan_check.FREE
    # 연결은 받는데 아무 말도 하지 않는 서버 — 멈춘 창과 같다
    srv = socket.socket(); srv.bind(("127.0.0.1", port)); srv.listen(8)
    held = []
    stop = threading.Event()

    def accept():
        srv.settimeout(0.2)
        while not stop.is_set():
            try:
                held.append(srv.accept()[0])
            except OSError:
                continue
    t = threading.Thread(target=accept, daemon=True); t.start()
    try:
        t0 = time.monotonic()
        assert lan_check.preflight(port) == lan_check.BUSY
        assert time.monotonic() - t0 < 15          # 기다림에 끝이 있다
    finally:
        stop.set(); t.join(2); srv.close()
        for c in held:
            c.close()


def test_preflight_knows_this_server(monkeypatch):
    monkeypatch.setattr(lan_check, "listening", lambda port: True)
    monkeypatch.setattr(lan_check, "probe",
                        lambda url, timeout: {"ok": True, "ours": True, "status": 200, "ms": 3})
    assert lan_check.preflight(1) == lan_check.ALREADY
    monkeypatch.setattr(lan_check, "probe",
                        lambda url, timeout: {"ok": True, "ours": False, "status": 200, "ms": 3})
    assert lan_check.preflight(1) == lan_check.BUSY      # 8000 에 남의 웹 서버


def test_report_says_what_to_do(monkeypatch):
    monkeypatch.setattr(lan_check.sys, "platform", "win32")
    monkeypatch.setattr(lan.socket, "gethostbyname_ex", lambda h: (h, [], []))
    monkeypatch.setattr(lan_check, "listening", lambda *a, **k: True)
    two = [{"address": "0.0.0.0:8000", "pid": "111", "program": "python.exe"},
           {"address": "127.0.0.1:8000", "pid": "222", "program": "python.exe"}]
    monkeypatch.setattr(lan_check, "owners", lambda port=8000: two)
    monkeypatch.setattr(lan_check, "probe", lambda url, timeout: {"ok": False, "error": "timeout", "ms": 8000})
    text = "\n".join(lan_check.report())
    assert "2개" in text and "taskkill /PID 111 /F" in text and "taskkill /PID 222 /F" in text
    monkeypatch.setattr(lan_check, "owners", lambda port=8000: two[:1])
    text = "\n".join(lan_check.report())
    assert "응답하지 않습니다" in text and "Esc" in text


def test_check_file_only_looks():
    body = _code("check_pid_server.bat")
    assert "-m app.lan_check" in body and "--preflight" not in body
    assert "taskkill" not in body.lower() and "pause" in body


# ---------------------------------------------------------------- ③ 재기 전에 받는다
def test_loopback_and_private_never_wait_for_the_network_lookup():
    calls = []

    def nets():
        calls.append(1)
        raise AssertionError("이 주소는 대역을 재지 않고 받아야 한다")
    for h in ("127.0.0.1", "::1", "10.1.2.3", "192.168.0.5", "::ffff:127.0.0.1"):
        assert lan.client_allowed(h, nets)
    assert not calls
    assert lan.client_allowed("65.3.1.2", lambda: lan.allowed_networks(local=["65.3.30.234"], extra=[]))
    assert not lan.client_allowed("8.8.8.8", lambda: [])


def test_gate_does_not_measure_for_localhost(monkeypatch):
    monkeypatch.setenv(lan.ENV_ON, "1")
    seen = []

    async def app(scope, receive, send):
        seen.append(scope["path"])
    gate = lan.Gate(app)
    monkeypatch.setattr(lan, "allowed_networks",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("measured")))

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(msg):
        pass
    asyncio.run(gate({"type": "http", "path": "/", "client": ("127.0.0.1", 5)}, receive, send))
    assert seen == ["/"] and gate._nets is None
