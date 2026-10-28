"""hotfix51 — Windows 배치 파일은 ASCII · CRLF 만 쓴다.

현장(회사 PC): hotfix50 의 `install_autostart_lan.bat` 는 등록에 성공했는데 서버가 뜨지 않았다
(`localhost:8000` ERR_CONNECTION_REFUSED).  서버 창에는 `'twork' is not recognized` ·
`'loopback'` · `'data\\CZE_Field_Instrument.xlsx'` · `'uble-click'` · `'HOST'` · `'ho'` 가 줄줄이
찍혔다 — 전부 `start.bat` **주석의 조각**이다 (network · loopback · double-click · echo).

원인: `run_lan_service.bat` 가 `chcp 65001` 을 한 뒤 `call start.bat` 했고, `start.bat` 은
UTF-8 한글이 든 LF 파일이었다.  cmd.exe 는 배치 파일을 바이트 위치로 다시 찾아 읽는데, 그
코드페이지에서 여러 바이트 글자가 든 줄을 지나면 위치가 어긋나 **줄 가운데부터** 읽는다.
예전에 `start.bat` 을 그냥 더블클릭했을 때는 코드페이지가 cp949 라 어긋나지 않았다.

그래서 배치 파일에는 한글을 쓰지 않고(화면 문장은 영어 · 한국어는 Python 쪽이 말한다),
줄 끝은 CRLF 로 둔다.  서비스 파일은 `start.bat` 을 부르지 않고 서버를 직접 띄운다.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
BATS = sorted(ROOT.glob("*.bat"))


def test_every_batch_file_is_ascii_with_crlf():
    assert {p.name for p in BATS} >= {"start.bat", "build.bat", "run_lan_service.bat",
                                      "install_autostart_lan.bat", "uninstall_autostart_lan.bat",
                                      "open_firewall_8000.bat"}
    for p in BATS:
        raw = p.read_bytes()
        bad = [i for i, b in enumerate(raw) if b > 0x7F]
        assert not bad, f"{p.name}: non-ASCII byte at {bad[:3]}"
        lone_lf = raw.count(b"\n") - raw.count(b"\r\n")
        assert lone_lf == 0, f"{p.name}: {lone_lf} line(s) end with LF only"


def test_no_batch_file_switches_the_codepage():
    for p in BATS:
        code = [ln for ln in p.read_text(encoding="ascii").splitlines()
                if not ln.strip().lower().startswith("rem")]
        assert not any("chcp" in ln.lower() for ln in code), p.name


def test_the_service_starts_the_server_itself():
    svc = (ROOT / "run_lan_service.bat").read_text(encoding="ascii")
    code = [ln for ln in svc.splitlines() if not ln.strip().lower().startswith("rem")]
    body = "\n".join(code)
    assert "start.bat" not in body                    # 다른 배치 파일을 거치지 않는다
    assert "set PID_LAN=1" in body
    assert "-m uvicorn app.main:app --host 0.0.0.0 --port 8000" in body
    assert '"PID_Extract.exe" --lan --no-browser 8000' in body
    assert "goto loop" in body and "taskkill" not in body.lower()
