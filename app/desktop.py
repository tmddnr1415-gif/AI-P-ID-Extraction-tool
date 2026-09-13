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


def _bindable(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
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
            except (ValueError, OSError):
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
    port_arg = next((a for a in argv if a.isdigit()), None)
    no_browser = "--no-browser" in argv

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
        if port_arg and not _bindable(int(port_arg)):
            _hold(f"포트 {port_arg} 은(는) 이미 다른 프로그램이 쓰고 있습니다.\n"
                  "인자 없이 실행하면 빈 포트를 자동으로 고릅니다.")
            return 1
        port = int(port_arg) if port_arg else _free_port()
        url = f"http://127.0.0.1:{port}"
        print(f"→ {url}\n")
        print("이 창을 닫으면 서버도 함께 종료됩니다.\n")
        if not no_browser:
            threading.Timer(1.0, lambda: webbrowser.open(url)).start()
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
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
