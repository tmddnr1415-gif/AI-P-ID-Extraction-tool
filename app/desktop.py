"""The exe's entry point: start the server, open the browser, stay up.

Written for someone who double-clicks a file.  That sets three requirements the
`uvicorn` command line does not meet:

  * the window must not close on an error.  A console that vanishes takes the
    reason with it, and the reason is the only thing that was worth having.  So
    every failure is caught, printed in Korean with the traceback under it, and
    the window waits for a keypress.
  * the port must not be a guess.  8000 is often taken; a free one is asked of
    the OS and the browser is sent to whichever was actually bound.
  * closing the window must stop the server.  There is no service to leave
    behind, and a stray process holding the database is worse than no app.

Nothing here reaches the network beyond binding 127.0.0.1: the browser is opened
on a loopback URL and the analysis is entirely local.

hotfix50 — `--lan` opens it on the company network (0.0.0.0) so the department
dashboard can show it in an iframe.  Then the port is **fixed** (8000, or the
one given): the dashboard has the address written down, so a free port picked
by the OS would be a port nobody can find.  A taken port stops with the reason
instead.  Who may come in is app/lan.py (loopback / private / this PC's /16 /
PID_ALLOW) — the same rule as the dashboard server.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import traceback
import webbrowser
from pathlib import Path

BANNER = "P&ID 계기·밸브 리스트 추출"


def _bindable(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
        except OSError:
            return False
    return True


def _free_port(preferred: int = 8000) -> int:
    """`preferred` if it is free, otherwise whatever the OS hands out."""
    for port in (preferred, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
            except OSError:
                continue
            return s.getsockname()[1]
    return preferred


def _hold(message: str = "") -> None:
    """Keep the window open so the reason can be read."""
    if message:
        print(message)
    # hotfix50 — 자동 시작(run_lan_service.bat)은 사람이 없는 창이다.  Enter 를 기다리면 다시
    # 켜지 못하므로 사유만 남기고 돌아간다 (사유는 같은 로그에 남는다).
    if os.environ.get("PID_NO_HOLD") == "1":
        return
    try:
        input("\n창을 닫으려면 Enter 를 누르세요. ")
    except (EOFError, KeyboardInterrupt):
        pass


class _Tee:
    """Everything printed also goes to the log the diagnostic export ships.

    It has to be a *stream*, not just something with `write`: uvicorn asks
    `sys.stdout.isatty()` while configuring its log formatter, and a stand-in
    that does not answer takes the whole server down before it binds - which is
    exactly the failure this class exists to make readable.  So the console's own
    answers are forwarded, and there is a plain fallback for the windowed build
    where `sys.stdout` is None.
    """

    encoding = "utf-8"
    errors = "replace"

    def __init__(self, stream, path: Path):
        self.stream = stream
        path.parent.mkdir(parents=True, exist_ok=True)
        self.file = open(path, "a", encoding="utf-8", buffering=1)

    def write(self, text):
        if self.stream is not None:
            try:
                self.stream.write(text)
            except (ValueError, OSError, UnicodeError):
                # hotfix54 — 창/파일이 cp949 면 `—` 를 못 쓴다.  서버를 죽이지 않고 바꿔 쓴다
                try:
                    enc = getattr(self.stream, "encoding", None) or "utf-8"
                    self.stream.write(text.encode(enc, "replace").decode(enc, "replace"))
                except (ValueError, OSError, UnicodeError, LookupError):
                    pass
        self.file.write(text)
        return len(text)

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def flush(self):
        for f in (self.stream, self.file):
            try:
                f.flush()
            except (ValueError, OSError, AttributeError):
                pass

    def isatty(self) -> bool:
        try:
            return bool(self.stream is not None and self.stream.isatty())
        except (ValueError, OSError, AttributeError):
            return False

    def fileno(self):
        if self.stream is None:
            raise OSError("no console")
        return self.stream.fileno()

    @property
    def closed(self) -> bool:
        return self.file.closed


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:                                       # hotfix54 — 못 쓰는 글자로 죽지 않게
        from app import console
        console.safe_stdio()
    except Exception:                          # noqa: BLE001
        pass
    port_arg = next((a for a in argv if a.isdigit()), None)
    no_browser = "--no-browser" in argv
    lan_mode = "--lan" in argv
    host = "0.0.0.0" if lan_mode else "127.0.0.1"
    if lan_mode:
        os.environ["PID_LAN"] = "1"           # app/lan.py 의 문지기가 이것을 본다
        port_arg = port_arg or "8000"         # 대시보드가 적어 둔 주소 — 빈 포트를 고르지 않는다

    try:
        from app import paths, version
        log = paths.log_path()
        sys.stdout = _Tee(sys.stdout, log)
        sys.stderr = _Tee(sys.stderr, log)
        print(f"\n{BANNER}  {version.label()}")
        print(f"데이터 폴더: {paths.data_dir()}")
        print(f"로그: {log}")

        import uvicorn
        from app.main import app                    # noqa: F401  (builds the app)

        # A port given by hand is used as given, so a taken one has to be said
        # out loud: uvicorn logs "address already in use" and then *returns
        # normally*, which would close the window with no reason on it - the one
        # failure mode this launcher exists to prevent.  Without an argument the
        # OS picks a free port, so a double-click cannot hit this.
        if port_arg and not _bindable(int(port_arg), host):
            _hold(f"포트 {port_arg} 은(는) 이미 다른 프로그램이 쓰고 있습니다.\n"
                  + ("사내망 모드는 대시보드가 적어 둔 포트를 써야 해서 다른 포트로 바꾸지 않습니다.\n"
                     "이미 켜 둔 P&ID 분석 창이 있는지 확인하세요."
                     if lan_mode else "인자 없이 실행하면 빈 포트를 자동으로 고릅니다."))
            return 1
        port = int(port_arg) if port_arg else _free_port()
        url = f"http://127.0.0.1:{port}"
        print(f"→ {url}\n")
        if lan_mode:
            from app import lan
            print("사내망 모드: 다른 PC 는 아래 주소로 들어옵니다 (사내망 · 이 PC 의 /16 만 허용)")
            for u in lan.urls(port):
                print(f"   → {u}")
            print()
        print("이 창을 닫으면 서버도 함께 종료됩니다.\n")
        if not no_browser:
            threading.Timer(1.0, lambda: webbrowser.open(url)).start()
        uvicorn.run(app, host=host, port=port, log_level="info")
        return 0
    except KeyboardInterrupt:
        print("\n종료합니다.")
        return 0
    except Exception:                                # noqa: BLE001
        print("\n실행하지 못했습니다. 아래 내용을 그대로 신고해 주세요.\n")
        traceback.print_exc()
        _hold()
        return 1


if __name__ == "__main__":
    sys.exit(main())
