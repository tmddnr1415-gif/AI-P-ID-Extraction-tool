"""P&ID 서버(포트 8000)만 다시 띄운다 — 운영 폴더에 업데이트를 얹은 뒤 (hotfix60 변경분 꾸러미).

    C:\\Claude\\PID\\.venv\\Scripts\\python restart_pid_server.py 8000

하는 일 (표준 라이브러리만 — 운영 .venv 에 무엇이 깔렸든 돈다):
  1. `netstat -ano` 에서 **그 포트를 LISTEN 하는 프로세스 하나**를 찾는다.
     ★ python 을 이름으로 끄지 않는다 — 부서 대시보드 서버(8080)도 python 이다.
  2. 분석이 돌고 있으면 묻는다 (끄면 그 분석은 '실패' 로 남는다 — 다시 올려야 한다).
  3. 그 PID 와 자식(분석 프로세스)만 끈다 (`taskkill /PID … /T /F`).
  4. `run_lan_service.bat` 의 반복이 10초 뒤 새 코드로 다시 띄운다.  60초 동안 `/version` 을
     물어 업데이트 딱지(hotfix 이름)를 보여 준다.  안 뜨면 무엇을 하라고 말한다.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import urllib.request

LISTEN_FOREIGN = ("0.0.0.0:0", "[::]:0", "*:*")


def listening_pids(port: int, netstat_text: str) -> list[int]:
    """`netstat -ano` 글에서 그 포트를 듣는 PID.  상태 낱말은 언어마다 달라(LISTENING · 수신 대기)
    쓰지 않고, **상대 주소가 0** 인 줄(= 듣는 소켓)로 가른다."""
    out = []
    for line in netstat_text.splitlines():
        cols = line.split()
        if len(cols) < 4 or cols[0].upper() != "TCP":
            continue
        local, foreign, pid = cols[1], cols[2], cols[-1]
        if not re.search(rf":{port}$", local) or foreign not in LISTEN_FOREIGN or not pid.isdigit():
            continue
        if int(pid) not in out and int(pid) != 0:
            out.append(int(pid))
    return out


def _get(url: str, timeout: float = 3.0):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def main(argv=None) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace")
        except Exception:                                     # noqa: BLE001
            pass
    argv = list(sys.argv[1:] if argv is None else argv)
    port = int(argv[0]) if argv and argv[0].isdigit() else 8000
    base = f"http://127.0.0.1:{port}"
    raw = subprocess.run(["netstat", "-ano"], capture_output=True).stdout
    text = raw.decode("utf-8", "replace") if raw.startswith(b"\xef\xbb\xbf") else raw.decode("mbcs" if sys.platform == "win32" else "utf-8", "replace")
    pids = listening_pids(port, text)
    if not pids:
        print(f"[알림] 포트 {port} 에 서버가 없습니다 — run_lan_service.bat 을 실행하면 새 코드로 뜹니다.")
        return 0
    try:
        running = [j for j in _get(f"{base}/running").get("jobs", []) if j.get("status") == "running"]
    except Exception:                                          # noqa: BLE001 — 옛 서버엔 /running 이 없다
        running = None
    if running:
        print(f"[주의] 지금 분석 {len(running)}건이 돌고 있습니다 — 다시 띄우면 그 분석은 '실패' 로 남고 다시 올려야 합니다.")
    elif running is None:
        print("[주의] 지금 분석 중인지 확인하지 못했습니다 (옛 서버). 분석 중이면 그 분석은 다시 올려야 합니다.")
    ans = input(f"포트 {port} 서버(PID {', '.join(map(str, pids))})를 다시 띄울까요? [Y/n] ").strip().lower()
    if ans not in ("", "y", "yes", "ㅛ"):
        print("다시 띄우지 않았습니다 — 새 코드는 서버를 다시 띄울 때 적용됩니다.")
        return 0
    for pid in pids:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
    print("껐습니다.  run_lan_service.bat 이 10초 뒤 새 코드로 다시 띄웁니다 — 기다리는 중…")
    t0 = time.time()
    time.sleep(3)
    while time.time() - t0 < 60:
        try:
            v = _get(f"{base}/version", timeout=2)
            up = (v.get("update") or {}).get("name") or "(딱지 없음)"
            print(f"[완료] 서버가 다시 떴습니다 — 업데이트 {up} · {int(time.time() - t0)}초")
            return 0
        except Exception:                                      # noqa: BLE001
            time.sleep(2)
    print("[확인 필요] 60초 안에 다시 뜨지 않았습니다.  run_lan_service.bat 을 더블클릭해 서버를 띄우세요.\n"
          "            그래도 안 되면 check_pid_server.bat 의 결과와 logs\\server.log 끝을 보여 주세요.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
