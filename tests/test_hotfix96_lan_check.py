"""hotfix96 — check_pid_server.bat 가 한국어 Windows 에서 죽던 것.

netstat 출력은 cp949 인데 PYTHONUTF8=1 이면 text=True 가 UTF-8 로 풀다 실패해 출력이 None 이 되고
`'NoneType' object has no attribute 'splitlines'` 로 멈췄다 (회사 PC 사진).  또 한국어 Windows 는 상태를
"수신 대기" 로 쓰므로 LISTENING 낱말로 거르면 아무것도 못 찾는다."""
import sys

from app import lan_check as L

NETSTAT = ("  TCP    0.0.0.0:8000   0.0.0.0:0   수신 대기   1234\r\n"
           "  TCP    127.0.0.1:8000 127.0.0.1:50000 ESTABLISHED 1234\r\n"
           "  TCP    [::]:8000      [::]:0      LISTENING   1234\r\n"
           "  TCP    0.0.0.0:18000  0.0.0.0:0   LISTENING   55\r\n").encode("cp949")


class _R:
    def __init__(self, out):
        self.stdout = out


def test_owners_reads_cp949_netstat_with_localized_state(monkeypatch):
    def fake(cmd, **kw):
        assert "text" not in kw            # 바이트로 받는다
        return _R(NETSTAT if cmd[0] == "netstat" else '"python.exe","1234","Console"'.encode("cp949"))
    monkeypatch.setattr(L.subprocess, "run", fake)
    monkeypatch.setattr(sys, "platform", "win32")
    got = L.owners(8000)
    assert [g["address"] for g in got] == ["0.0.0.0:8000", "[::]:8000"]
    assert {g["pid"] for g in got} == {"1234"} and got[0]["program"] == "python.exe"


def test_run_text_never_returns_none(monkeypatch):
    monkeypatch.setattr(L.subprocess, "run", lambda cmd, **kw: _R(None))
    assert L._run_text(["netstat"], 1) == ""
    monkeypatch.setattr(L.subprocess, "run", lambda cmd, **kw: _R(b"\xbc\xf6\xff\xfe"))
    assert isinstance(L._run_text(["netstat"], 1), str)
