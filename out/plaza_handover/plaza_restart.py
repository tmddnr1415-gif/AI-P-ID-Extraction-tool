"""가상 광장 서버를 다시 켠다 (업데이트를 푼 뒤) — 표준 라이브러리만.

    python plaza\\plaza_restart.py            (포트 8100)

포트를 **LISTEN 하는 프로그램 하나만** PID 로 끈다 — python 을 이름으로 끄지 않는다
(대시보드 서버도 python 이다).  run_plaza_server.bat 의 반복이 10초 뒤 새 코드로 다시 띄우고,
이 스크립트는 /version 이 돌아올 때까지 기다렸다가 적용된 업데이트 이름을 보여 준다.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request


def listening_pids(text: str, port: int) -> set[int]:
    """netstat -ano 글에서 그 포트를 잡고 기다리는 PID.

    상태 낱말(LISTENING · 수신 대기 …)은 Windows 언어마다 달라 보지 않는다 —
    로컬 주소가 :<port> 로 끝나고 상대 주소가 0 (0.0.0.0:0 · [::]:0) 인 TCP 줄만.
    """
    out = set()
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 4 or parts[0].upper() != "TCP":
            continue
        local, remote, pid = parts[1], parts[2], parts[-1]
        if not local.endswith(f":{port}") or remote.rsplit(":", 1)[-1] != "0" or not pid.isdigit():
            continue
        if int(pid) > 0:
            out.add(int(pid))
    return out


def version(port: int):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/version", timeout=2) as r:
            return json.loads(r.read() or b"{}")
    except Exception:
        return None


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8100
    raw = subprocess.run(["netstat", "-ano"], capture_output=True).stdout
    pids = listening_pids(raw.decode("ascii", errors="replace"), port)
    if not pids:
        print(f"포트 {port} 에서 도는 광장 서버가 없습니다.  run_plaza_server.bat 을 켜 주세요.")
        return 1
    v = version(port)
    if not (v and v.get("app") == "plaza"):
        print(f"포트 {port} 의 프로그램(PID {sorted(pids)})이 광장 서버가 아닙니다.  끄지 않습니다.")
        return 2
    for pid in sorted(pids):
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
        print(f"광장 서버(PID {pid})를 껐습니다 — 10초쯤 뒤 새 코드로 다시 뜹니다.")
    for _ in range(40):
        time.sleep(1)
        v = version(port)
        if v:
            up = (v.get("update") or {}).get("name") or "(딱지 없음)"
            print(f"다시 떴습니다 — 적용된 업데이트: {up}")
            return 0
    print("40초 안에 다시 뜨지 않았습니다.  run_plaza_server.bat 창(또는 plaza\\logs\\plaza_server.log)을 보세요.")
    return 3


if __name__ == "__main__":
    sys.exit(main())
