"""hotfix93 — 서비스 창(`run_lan_service.bat`)이 P&ID 서버를 띄우는 자리.

현장 (회사 PC 사진): 서버가 멈춘 뒤 10초 뒤 다시 띄우려는데 창에
*"다른 프로세스가 파일을 사용 중이기 때문에 프로세스가 액세스 할 수 없습니다"* 만 나오고
서버가 곧바로 멈췄다 — 대시보드는 *"P&ID 서버가 꺼져 있습니다"*.  hotfix52 의 배치 파일은
`… uvicorn … >> logs\\server.log 2>&1` 로 **cmd 가** 로그를 열었는데, 그 파일을 누가(앞 서버가 끝나는
중 · 다른 서비스 창 · 로그를 연 편집기) 쥐고 있으면 cmd 가 열지 못해 **서버를 띄우지도 않고** 끝난다.
그리고 이 창에서 Ctrl+C 를 누르면 (글을 복사하려다가도) 서버가 같이 꺼졌다 (사진의 `^C`).

여기서 하는 일 둘:
  1. 로그는 파이썬이 연다 — 다른 프로세스가 쥐고 있어도 함께 쓰는 방식으로.  그래도 안 열리면
     **새 이름**(`server_<시각>.log`)으로 쓰고 서버는 띄운다.  쓰는 파일 이름은 `logs\\server.current`
     에 적고, 서버가 멈추면 `python -m app.lan_serve --tail` 이 그 파일 끝을 보인다
     (`lan_check.py` 는 회사에서 고친 판이 있어 건드리지 않는다 — 그 `tail()` 을 부르기만 한다).
  2. 서버는 **Ctrl+C 를 받지 않는 프로세스 무리**로 띄운다 (Windows `CREATE_NEW_PROCESS_GROUP`).
     창을 닫으면 그대로 꺼진다 (창 닫기는 모든 프로세스에 간다).  업데이트 꾸러미의
     `restart_pid_server.py` 는 포트를 쥔 서버를 직접 끄므로 그대로 동작한다.

    python -m app.lan_serve [port]
    python -m app.lan_serve --tail       서버가 멈춘 뒤 — 지금 쓰던 로그의 끝

화면 글은 ASCII — 서비스 창은 한국어 Windows 콘솔(cp949)이다 (hotfix51 · hotfix54).
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"
MAIN_LOG = "server.log"
CURRENT = "server.current"
KEEP_SPARE = 3                       # 새 이름으로 쓴 로그는 최근 셋만 남긴다


def _prune(logs: Path, keep: int = KEEP_SPARE) -> None:
    spares = sorted(logs.glob("server_*.log"), key=lambda p: p.stat().st_mtime)
    for p in spares[:-keep] if keep else spares:
        try:
            p.unlink()
        except OSError:
            pass


def open_log(logs: Path | None = None):
    """(경로, 열린 파일).  server.log 를 함께 쓰는 방식으로 열고, 안 되면 새 이름으로."""
    logs = logs or LOGS
    logs.mkdir(parents=True, exist_ok=True)
    main = logs / MAIN_LOG
    try:
        return main, open(main, "ab", buffering=0)
    except OSError:
        pass
    _prune(logs, KEEP_SPARE - 1)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    for i in range(100):
        alt = logs / (f"server_{stamp}.log" if i == 0 else f"server_{stamp}_{i}.log")
        try:
            return alt, open(alt, "xb", buffering=0)
        except OSError:
            continue
    raise OSError(f"cannot open a log file in {logs}")


def current_log(logs: Path | None = None) -> Path:
    """지금 서버가 쓰는 로그 — `server.current` 에 적힌 것 (없거나 그 파일이 없으면 server.log)."""
    logs = logs or LOGS
    try:
        name = (logs / CURRENT).read_text(encoding="utf-8").strip()
        if name and (logs / name).exists():
            return logs / name
    except OSError:
        pass
    return logs / MAIN_LOG


def server_command(port: int) -> list[str]:
    return [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(port)]


def serve(port: int = 8000, logs: Path | None = None) -> int:
    logs = logs or LOGS
    path, log = open_log(logs)
    try:
        (logs / CURRENT).write_text(path.name + "\n", encoding="utf-8")
    except OSError:
        pass
    if path.name != MAIN_LOG:
        print(f"logs\\{MAIN_LOG} is held by another program - writing to logs\\{path.name} instead.")
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log.write(f"\n==== {stamp} PID server starting (port {port}) ====\n".encode("utf-8"))
    kw = {}
    if sys.platform == "win32":
        kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP    # Ctrl+C 가 서버에 닿지 않는다
    else:
        kw["start_new_session"] = True
    proc = subprocess.Popen(server_command(port), cwd=str(ROOT), stdin=subprocess.DEVNULL,
                            stdout=log, stderr=subprocess.STDOUT, **kw)
    log.close()                                   # 서버가 자기 몫을 들고 있다
    while True:
        try:
            return proc.wait(timeout=1.0)        # 짧게 기다려야 Ctrl+C 가 바로 잡힌다
        except subprocess.TimeoutExpired:
            continue
        except KeyboardInterrupt:
            print("Ctrl+C does not stop the server.  To stop it, close this window.")


def show_tail() -> int:
    from app import console, lan_check
    console.safe_stdio()
    path = current_log()
    print(f"---- logs\\{path.name} (end) ----")
    print("\n".join(lan_check.tail(path)))
    print("---------------------------------")
    return 0


def main(argv: list[str]) -> int:
    if "--tail" in argv:
        return show_tail()
    port = int(argv[0]) if argv and argv[0].isdigit() else 8000
    return serve(port)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
