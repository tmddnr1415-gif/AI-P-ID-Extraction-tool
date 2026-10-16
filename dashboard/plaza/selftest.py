"""가상 광장 서버 자가 점검 — 표준 라이브러리만.  `python selftest.py`

빈 임시 폴더로 서버를 띄우고 들어오기 · 걷기 · 말하기 · 때리기 · 얼굴 · 역할(운영자만) · 나가기를
API 로 한 번씩 해 본다.  마지막 줄이 "모두 통과" 면 된다.
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
data = Path(tempfile.mkdtemp(prefix="plaza_selftest_"))
(data / "roles.json").write_text(json.dumps({"operators": ["홍길동"], "group_leader": ["이영희"]}, ensure_ascii=False), encoding="utf-8")
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(HERE / "plaza_server.py"), "--host", "127.0.0.1", "--port", str(port), "--data", str(data)])
base = f"http://127.0.0.1:{port}"


def call(path, body=None):
    req = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


try:
    for _ in range(50):
        try:
            if call("/version")[0] == 200:
                break
        except OSError:
            time.sleep(0.2)
    ok = []
    _, a = call("/plaza/api/join", {"name": "김철수", "x": 29, "y": 15})
    _, b = call("/plaza/api/join", {"name": "홍길동", "x": 28, "y": 15})
    ok.append(("역할 — 운영자", b["role"] == "operator" and a["role"] == "member"))
    call("/plaza/api/move", {"id": a["id"], "x": 29, "y": 15, "dir": 2})
    ok.append(("때리기 — 앞 칸 사람이 맞음", call("/plaza/api/attack", {"id": a["id"]})[1]["hit"] == ["홍길동"]))
    ok.append(("말하기 — 80자", len(call("/plaza/api/say", {"id": a["id"], "text": "가" * 200})[1]["text"]) == 80))
    face = {"hair": 4, "hairc": 4, "skin": 1, "eyes": 2, "beard": 0, "cloth": 3, "pants": 1}
    call("/plaza/api/look", {"id": a["id"], "look": face})
    ok.append(("얼굴 — 파일에 남음", json.loads((data / "looks.json").read_text(encoding="utf-8"))["김철수"] == face))
    ok.append(("역할 지정 — 부서원은 못 함", call("/plaza/api/role", {"id": a["id"], "target": "김철수", "role": "leader"})[0] == 403))
    ok.append(("역할 지정 — 운영자는 됨", call("/plaza/api/role", {"id": b["id"], "target": "김철수", "role": "unit"})[0] == 200))
    ok.append(("화면 파일", urllib.request.urlopen(base + "/plaza?embed=1&user=x").status == 200))
    # 2026-10-16 대시보드: 겹치지 않음 · 보는 화면 표시 · 판 · 끄기
    _, c = call("/plaza/api/join", {"name": "박민수", "x": 10, "y": 10})
    call("/plaza/api/move", {"id": c["id"], "x": 10, "y": 10, "dir": 0})
    _, mv = call("/plaza/api/move", {"id": b["id"], "x": 10, "y": 10, "dir": 0})
    ok.append(("겹치지 않음 — 남이 선 칸으로 못 감", mv.get("blocked") is True))
    ok.append(("보는 화면 표시 — 24자", call("/plaza/api/status", {"id": c["id"], "text": "P&ID 분석 중..." + "x" * 40})[1]["status"] == ("P&ID 분석 중..." + "x" * 40)[:24]))
    ok.append(("판 번호", bool(call("/version")[1].get("ver"))))
    ok.append(("나가기", call("/plaza/api/leave", {"id": a["id"]})[0] == 200))
    for name, good in ok:
        print(("통과 " if good else "실패 ") + name)
    print("모두 통과" if all(g for _, g in ok) else "실패가 있습니다")
    sys.exit(0 if all(g for _, g in ok) else 1)
finally:
    try:
        call("/plaza/api/quit", {})                 # 이 PC 에서 끄기
        srv.wait(5)
    except Exception:
        srv.terminate()
