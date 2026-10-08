"""hotfix52 — 사내망 서버(포트 8000)가 **응답하는지** 재고 사람에게 말한다.

현장: hotfix51 서버 창에 `Uvicorn running on http://0.0.0.0:8000` 이 떴는데
`http://localhost:8000/?embed=1&mode=bid` 가 끝없이 로딩만 했다.  "떠 있다" 와
"응답한다" 는 다른 사실이다.  멈추는 길은 셋이다:

  ① 서버 창을 마우스로 누르면 Windows 콘솔이 '선택' 모드가 되고, 그 창에 글을 쓰는
     프로그램은 **글을 쓰는 순간 멈춘다** — uvicorn 은 요청마다 한 줄을 쓰므로 첫 요청에서
     서버 전체가 멈춘다 (창 제목이 "선택 ..." 으로 바뀐다)
  ② 예전에 켜 둔 다른 서버(옛 start.bat · 다른 창)가 8000 을 같이 잡고 있으면 요청이
     그쪽으로 간다 (`--reload` 로 켠 uvicorn 은 SO_REUSEADDR 로 묶는다)
  ③ 첫 화면 자료(`/home`)가 느리다

    python -m app.lan_check              진단 — 화면에 쓰고 logs/lan_check.txt 에도 남긴다
    python -m app.lan_check --preflight  서비스가 켜기 전에: 0 비어 있음 · 3 이 서버가 이미
                                         응답 중 · 4 누군가 잡았는데 응답이 없음
                                         (1·2 는 쓰지 않는다 — 파이썬 자체가 실패한 코드와
                                          겹치면 서비스가 영영 기다린다)

판정만 하고 아무것도 끄지 않는다 (대시보드 서버도 python 이다).
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PORT = 8000
ROOT = Path(__file__).resolve().parent.parent


def listening(port: int = PORT, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
    """누군가 그 포트에서 연결을 받는가 (연결만 하고 아무것도 보내지 않는다)."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def probe(url: str, timeout: float) -> dict:
    """GET 한 번 — 상태 · 걸린 시간 · 이 서버인지 (`/version` 의 JSON)."""
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            body = r.read()
            out = {"ok": True, "status": r.status, "ms": round((time.monotonic() - t0) * 1000)}
            if url.endswith("/version"):
                try:
                    v = json.loads(body.decode("utf-8"))
                    out["ours"] = isinstance(v, dict) and "version" in v
                    out["update"] = ((v.get("update") or {}).get("name")
                                     if isinstance(v, dict) else None)
                except ValueError:
                    out["ours"] = False
            return out
    except Exception as e:  # noqa: BLE001 — 사람에게 그대로 보인다
        return {"ok": False, "error": f"{type(e).__name__}: {e}",
                "ms": round((time.monotonic() - t0) * 1000)}


def owners(port: int = PORT) -> list[dict]:
    """Windows `netstat -ano` 에서 그 포트를 LISTENING 하는 (주소, PID, 프로그램 이름).
    다른 운영체제에서는 빈 목록이다 (현장은 Windows 다)."""
    if sys.platform != "win32":
        return []
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                             timeout=20).stdout
    except Exception:  # noqa: BLE001
        return []
    found = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0].upper() != "TCP" or parts[3].upper() != "LISTENING":
            continue
        if not parts[1].endswith(f":{port}"):
            continue
        found.append({"address": parts[1], "pid": parts[4]})
    for f in found:
        try:
            row = subprocess.run(["tasklist", "/FI", f"PID eq {f['pid']}", "/FO", "CSV", "/NH"],
                                 capture_output=True, text=True, timeout=10).stdout.strip()
            f["program"] = row.split('","')[0].strip('"') if row.startswith('"') else "?"
        except Exception:  # noqa: BLE001
            f["program"] = "?"
    return found


FREE, ALREADY, BUSY = 0, 3, 4


def preflight(port: int = PORT) -> int:
    """서비스가 켜기 전에 묻는다.  0 비어 있음 · 3 이 서버가 이미 응답 · 4 잡혔는데 응답 없음."""
    if not listening(port):
        return FREE
    v = probe(f"http://127.0.0.1:{port}/version", timeout=5)
    return ALREADY if v.get("ok") and v.get("ours") else BUSY


def report(port: int = PORT) -> list[str]:
    from app import lan
    lines = [f"P&ID 서버 점검 — 포트 {port} · {time.strftime('%Y-%m-%d %H:%M:%S')}", ""]
    own = owners(port)
    pids = sorted({o["pid"] for o in own})
    if sys.platform == "win32":
        lines.append(f"[1] 포트 {port} 을 잡은 프로그램: {len(pids)}개")
        for o in own:
            lines.append(f"      {o['address']:<22} PID {o['pid']:<7} {o.get('program', '?')}")
    v = probe(f"http://127.0.0.1:{port}/version", timeout=8)
    lines.append(f"[2] http://127.0.0.1:{port}/version → "
                 + (f"응답 {v['ms']} ms · {v.get('update') or '업데이트 기록 없음'}" if v["ok"]
                    else f"응답 없음 ({v['ms']} ms · {v['error']})"))
    h = probe(f"http://127.0.0.1:{port}/home", timeout=60) if v["ok"] else None
    if h is not None:
        lines.append(f"[3] 첫 화면 자료 /home → "
                     + (f"{h['ms'] / 1000:.1f} 초" if h["ok"] else f"응답 없음 ({h['error']})"))
    lan_ok = []
    for ip in lan.local_ipv4():
        p = probe(f"http://{ip}:{port}/version", timeout=5)
        lan_ok.append(p["ok"])
        lines.append(f"[4] http://{ip}:{port}/version → "
                     + (f"응답 {p['ms']} ms" if p["ok"] else f"응답 없음 ({p['error']})"))
    lines += ["", "판정:"]
    if not listening(port) and not own:
        lines += ["  서버가 떠 있지 않습니다.",
                  "  run_lan_service.bat 을 더블클릭하거나 install_autostart_lan.bat 으로 등록하세요.",
                  "  창이 바로 닫히면 logs\\server.log 끝부분을 보내 주세요."]
    elif len(pids) > 1:
        lines += [f"  포트 {port} 을 프로그램 {len(pids)}개가 함께 잡고 있습니다 — 요청이 멈춘 쪽으로 갈 수 있습니다.",
                  "  열려 있는 P&ID 서버 창(검은 창)을 전부 닫으세요.  자동 시작을 등록했다면 10초 뒤 하나만 다시 뜹니다.",
                  "  창이 안 보이면 아래 명령으로 끕니다 (대시보드 서버 PID 는 끄지 마세요 — 그것은 포트 8080 입니다):"]
        lines += [f"      taskkill /PID {pid} /F" for pid in pids]
    elif not v["ok"]:
        lines += ["  서버가 포트를 잡고 있는데 응답하지 않습니다.",
                  "  가장 흔한 원인: 서버 창을 마우스로 눌러 창이 '선택' 모드로 멈춘 것입니다",
                  "  (창 제목이 '선택' 으로 시작합니다).  그 창을 누르고 Esc 를 누르면 바로 풀립니다.",
                  "  hotfix52 부터 서비스 창은 글을 쓰지 않아(로그는 logs\\server.log) 이렇게 멈추지 않습니다."]
    elif h is not None and not h["ok"]:
        lines += ["  서버는 응답하는데 첫 화면 자료(/home)가 60초 안에 오지 않습니다.",
                  "  logs\\server.log 끝부분과 이 결과(logs\\lan_check.txt)를 보내 주세요."]
    else:
        lines += ["  서버는 정상입니다.  브라우저에서 Ctrl+F5 (강력 새로 고침) 후 다시 열어 보세요."]
        if lan_ok and not any(lan_ok):
            lines += ["  다만 이 PC 의 사내망 주소로는 응답하지 않습니다 — 다른 PC 에서 열려면",
                      "  open_firewall_8000.bat 을 관리자 권한으로 한 번 실행하세요."]
    return lines


def main(argv: list[str]) -> int:
    if "--preflight" in argv:
        return preflight()
    lines = report()
    text = "\n".join(lines)
    print(text)
    try:
        (ROOT / "logs").mkdir(exist_ok=True)
        (ROOT / "logs" / "lan_check.txt").write_text(text + "\n", encoding="utf-8")
        print("\n(이 내용은 logs\\lan_check.txt 에도 남겼습니다)")
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
