"""가상 광장 서버 자가 점검 — 표준 라이브러리만.  `python selftest.py`

빈 임시 폴더로 서버를 띄우고 들어오기 · 걷기 · 말하기 · 때리기 · 체력 · 유령 · 주간 마감 부활 · 얼굴 · 역할(운영자만) · 나가기를
API 로 한 번씩 해 본다.  마지막 줄이 "모두 통과" 면 된다.
"""
from __future__ import annotations

import http.client
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
root = Path(tempfile.mkdtemp(prefix="plaza_selftest_"))
data = root / "data" / "plaza"                      # 대시보드처럼 data/plaza — [금주 마감] 은 data/_meta/state.json
data.mkdir(parents=True)
sys.path.insert(0, str(HERE))
import plaza_server  # noqa: E402  (주차 계산만 빌려 씀)
plaza_server.DATA = data
week = plaza_server.plaza_week()
(data / "hp.json").write_text(json.dumps({"week": week, "hp": {"이몽룡": 1, "변학도": 1, "방자": 1}}, ensure_ascii=False), encoding="utf-8")
(data / "roles.json").write_text(json.dumps({"operators": ["홍길동"], "group_leader": ["이영희"]}, ensure_ascii=False), encoding="utf-8")
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(HERE / "plaza_server.py"), "--host", "127.0.0.1", "--port", str(port), "--data", str(data)])
base = f"http://127.0.0.1:{port}"


def call(path, body=None, src="127.0.0.1"):
    """src = 보내는 쪽 주소 — 한 PC(IP)에 캐릭터 하나라서 사람마다 다른 루프백 주소(127.0.0.N)로 보낸다"""
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=5, source_address=(src, 0))
    try:
        c.request("GET" if body is None else "POST", path, None if body is None else json.dumps(body).encode(), {"Content-Type": "application/json"})
        r = c.getresponse()
        return r.status, json.loads(r.read() or b"{}")
    finally:
        c.close()


try:
    for _ in range(50):
        try:
            if call("/version")[0] == 200:
                break
        except OSError:
            time.sleep(0.2)
    ok = []
    A, B, C = "127.0.0.2", "127.0.0.3", "127.0.0.4"     # 김철수 · 홍길동 · 박민수 의 PC
    _, a = call("/plaza/api/join", {"name": "김철수", "x": 29, "y": 15}, A)
    _, b = call("/plaza/api/join", {"name": "홍길동", "x": 28, "y": 15}, B)
    ok.append(("역할 — 운영자", b["role"] == "operator" and a["role"] == "member"))
    call("/plaza/api/move", {"id": a["id"], "x": 29, "y": 15, "dir": 2}, A)
    ok.append(("때리기 — 앞 칸 사람이 맞음", call("/plaza/api/attack", {"id": a["id"]}, A)[1]["hit"] == ["홍길동"]))
    ok.append(("말하기 — 80자", len(call("/plaza/api/say", {"id": a["id"], "text": "가" * 200})[1]["text"]) == 80))
    face = {"hair": 4, "hairc": 4, "skin": 1, "eyes": 2, "beard": 0, "cloth": 3, "pants": 1}
    call("/plaza/api/look", {"id": a["id"], "look": face})
    ok.append(("얼굴 — 파일에 남음 (예전 값만 보내면 고양이 기사 기본값이 붙음)", json.loads((data / "looks.json").read_text(encoding="utf-8"))["김철수"] == {**face, "kind": 0, "fur": 0, "armor": 0, "cape": 0}))
    cat = {**face, "kind": 0, "fur": 4, "armor": 1, "cape": 2}
    call("/plaza/api/look", {"id": a["id"], "look": cat})
    ok.append(("얼굴 — 고양이 기사 (호랑이 · 황금 갑옷 · 초록 망토)", json.loads((data / "looks.json").read_text(encoding="utf-8"))["김철수"] == cat))
    ok.append(("그림 파일 — 고양이 기사 (PNG)", urllib.request.urlopen(base + "/static/catknight.png").read()[:8] == b"\x89PNG\r\n\x1a\n"))
    ok.append(("역할 지정 — 부서원은 못 함", call("/plaza/api/role", {"id": a["id"], "target": "김철수", "role": "leader"})[0] == 403))
    ok.append(("역할 지정 — 운영자는 됨", call("/plaza/api/role", {"id": b["id"], "target": "김철수", "role": "unit"})[0] == 200))
    ok.append(("화면 파일", urllib.request.urlopen(base + "/plaza?embed=1&user=x").status == 200))
    # 2026-10-16 대시보드: 겹치지 않음 · 보는 화면 표시 · 판 · 끄기
    _, c = call("/plaza/api/join", {"name": "박민수", "x": 10, "y": 10}, C)
    call("/plaza/api/move", {"id": c["id"], "x": 10, "y": 10, "dir": 0})
    _, mv = call("/plaza/api/move", {"id": b["id"], "x": 10, "y": 10, "dir": 0})
    ok.append(("겹치지 않음 — 남이 선 칸으로 못 감", mv.get("blocked") is True))
    ok.append(("보는 화면 표시 — 24자", call("/plaza/api/status", {"id": c["id"], "text": "P&ID 분석 중..." + "x" * 40})[1]["status"] == ("P&ID 분석 중..." + "x" * 40)[:24]))
    ok.append(("판 번호", bool(call("/version")[1].get("ver"))))
    # 한 PC(IP)에 캐릭터 하나: 같은 PC 에서 대시보드를 하나 더 열면 같은 캐릭터 · 다른 이름이면 바뀜
    _, a2 = call("/plaza/api/join", {"name": "김철수", "x": 3, "y": 3}, A)
    ok.append(("한 PC 한 캐릭터 — 창을 더 열어도 같은 캐릭터", a2["id"] == a["id"] and a2["shared"] is True and (a2["x"], a2["y"]) == (29, 15)))
    _, d = call("/plaza/api/join", {"name": "최지우", "x": 5, "y": 5}, C)
    ok.append(("한 PC 한 캐릭터 — 같은 PC 에서 다른 사람이 들어오면 바뀜", d["id"] != c["id"] and call("/plaza/api/move", {"id": c["id"], "x": 1, "y": 1}, C)[0] == 404))
    # 2026-10-16 (7) 체력: 100 · 한 대에 -1 · 0 이면 유령 · 주간 마감에 부활
    E, F = "127.0.0.5", "127.0.0.6"
    _, m = call("/plaza/api/join", {"name": "이몽룡", "x": 41, "y": 20}, E)
    _, h = call("/plaza/api/join", {"name": "성춘향", "x": 42, "y": 20}, F)
    call("/plaza/api/move", {"id": h["id"], "x": 42, "y": 20, "dir": 2}, F)
    ok.append(("체력 — 남은 1 을 맞으면 유령", call("/plaza/api/attack", {"id": h["id"]}, F)[1]["hit"] == ["이몽룡"]))
    ok.append(("유령 — 공격 못 함", call("/plaza/api/attack", {"id": m["id"]}, E)[1].get("ghost") is True))
    time.sleep(0.35)
    ok.append(("유령 — 안 맞음", call("/plaza/api/attack", {"id": h["id"]}, F)[1]["hit"] == []))
    ok.append(("유령 — 남과 겹쳐 지나감", call("/plaza/api/move", {"id": m["id"], "x": 42, "y": 20, "dir": 3}, E)[1].get("ok") is True))
    # 2026-10-19 처치 수: 3명 쓰러뜨리면 killer
    G1, G2 = "127.0.0.7", "127.0.0.8"
    for nm, ip, x in (("변학도", G1, 46), ("방자", G2, 48)):
        call("/plaza/api/join", {"name": nm, "x": x, "y": 24}, ip)
        call("/plaza/api/move", {"id": h["id"], "x": x + 1, "y": 24, "dir": 2}, F)
        time.sleep(0.35)
        call("/plaza/api/attack", {"id": h["id"]}, F)
    time.sleep(2.5)
    saved = json.loads((data / "hp.json").read_text(encoding="utf-8"))
    ok.append(("처치 수 — 3명 쓰러뜨림 (killer)", saved.get("kills", {}).get("성춘향") == 3))
    ok.append(("체력 — 파일에 남음 (홍길동 99 · 이몽룡 0)", saved["hp"].get("홍길동") == 99 and saved["hp"].get("이몽룡") == 0 and saved["week"] == week))
    (root / "data" / "_meta").mkdir()
    (root / "data" / "_meta" / "state.json").write_text(json.dumps({"manualClosedWeek": week}), encoding="utf-8")   # [금주 마감]
    time.sleep(5.2)
    call("/plaza/api/move", {"id": m["id"], "x": 43, "y": 20, "dir": 3}, E)
    time.sleep(0.4)
    ok.append(("주간 마감 — 유령 부활 (다시 때릴 수 있음)", call("/plaza/api/attack", {"id": m["id"]}, E)[1].get("ghost") is None))
    time.sleep(2.5)
    saved = json.loads((data / "hp.json").read_text(encoding="utf-8"))
    ok.append(("주간 마감 — 모두 100 · 처치 수 0 · 새 주차", saved["hp"] == {} and saved.get("kills") == {} and saved["week"] > week))
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
