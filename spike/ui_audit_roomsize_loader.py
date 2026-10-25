"""hotfix116 — 대시보드(8080) 메뉴 'ROOM SIZE 계산' 이 여는 apps/space/index.html(넘겨 주는 파일)이
P&ID 서버(8000)의 /space 최신 화면을 띄우는지, 예전 대시보드 자료를 가져올 수 있는지 눌러 본다.

준비: 대시보드 서버를 8080 에 띄우고 그 폴더 apps/space/index.html 을 dashboard_apps/space/index.html 로,
apps/frame.html 을 대시보드처럼 iframe 으로 '/apps/space/index.html?embed=1&user=…' 을 여는 쪽으로 둔다.
    python3 spike/ui_audit_roomsize_loader.py out/hotfix116/loader
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "out/hotfix116/loader")
DATA = Path(tempfile.mkdtemp(prefix="roomsize_"))
ENV = {**os.environ, "PID_DATA_DIR": str(DATA), "PID_LOGIC_WARM": "0", "PID_PAGE_WARM": "0", "PID_ROWS_WARM": "0",
       "PID_RENDER_POOL": "0"}


def _get(url):
    return json.loads(urllib.request.urlopen(url, timeout=5).read().decode())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res, errs = [], []
    srv = None
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        pg = b.new_page(viewport={"width": 1600, "height": 950})
        pg.on("pageerror", lambda e: errs.append(str(e)))
        # ① P&ID 서버가 꺼져 있을 때
        pg.goto("http://localhost:8080/apps/frame.html"); pg.wait_for_timeout(4000)
        fr = pg.frame_locator("#f")
        res.append(("서버 꺼짐 안내", "꺼져 있습니다" in fr.locator("#msg").inner_text()))
        pg.screenshot(path=str(OUT / "1_pid_off.png"))
        # ② P&ID 서버를 켜고 다시 시도
        srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
                               cwd=ROOT, env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        try:
            for _ in range(120):
                try:
                    urllib.request.urlopen("http://127.0.0.1:8000/version", timeout=1); break
                except OSError:
                    time.sleep(0.5)
            fr.locator("#retry").click(); pg.wait_for_timeout(3000)
            f = pg.frame(url=lambda u: ":8000/space" in u)
            res.append(("P&ID 서버 /space 로 넘어감", bool(f)))
            res.append(("주소 뒤 값 유지", bool(f) and "embed=1" in f.url and "user=" in f.url))
            res.append(("최신 화면(룸 · Rev · 3D)", bool(f) and f.locator("#hmRoomNew").count() == 1 and f.locator("#b3d").count() == 1))
            res.append(("제목 ROOM SIZE 계산", bool(f) and "ROOM SIZE" in f.title()))
            pg.screenshot(path=str(OUT / "2_space_home.png"))
            # ③ 예전 대시보드 자료 가져오기
            f.locator("#hmImport").click(); pg.wait_for_timeout(2500)
            pj = _get("http://127.0.0.1:8000/space/api/projects")["projects"]
            res.append(("대시보드 자료 가져옴 (TEST 3)", [p["name"] for p in pj] == ["TEST 3"] and pj[0]["saves"] == 1))
            pg.screenshot(path=str(OUT / "3_imported.png"))
            # ④ 그 프로젝트에 룸 · Rev 를 만들고 예전 저장본 이어서 → 저장
            f.select_option("#hmProj", pj[0]["id"]); pg.wait_for_timeout(800)
            f.locator("#hmRoomNew").click(); f.fill("#hmRoomName", "CCR"); f.locator("#hmRoomCreate").click(); pg.wait_for_timeout(800)
            f.locator("#hmRevNew").click(); f.fill("#hmRevName", "B"); f.locator("#hmRevCreate").click(); pg.wait_for_timeout(800)
            pg.screenshot(path=str(OUT / "4_room_rev.png"))
            f.locator("#hmGo").click(); pg.wait_for_timeout(1500)
            f.locator("#bSrvOpen2").click(); pg.wait_for_timeout(700)
            f.fill("#hMemo", "대시보드에서 저장"); f.locator("#hSave").click(); pg.wait_for_timeout(1200)
            pj = _get("http://127.0.0.1:8000/space/api/projects")["projects"][0]
            res.append(("저장 2건 · 룸 CCR Rev B", pj["saves"] == 2 and pj["rooms"][0]["name"] == "CCR" and "B" in pj["rooms"][0]["revs"]))
            last = _get(f"http://127.0.0.1:8000/space/api/{pj['id']}")["saves"][0]
            res.append(("작성자 = 대시보드 로그인 이름", last["by"] == "백승욱"))
            f.locator("#hClose").click(); pg.wait_for_timeout(300)
            f.locator("#b3d").click(); pg.wait_for_timeout(1500)
            pg.screenshot(path=str(OUT / "5_3d.png"))
        finally:
            srv.terminate()
        b.close()
    shutil.rmtree(DATA, ignore_errors=True)
    res.append(("페이지 오류 0", not errs))
    lines = [f"{'✔' if v else '✘'} {k}: {v}" for k, v in res] + [f"오류: {e}" for e in errs]
    (OUT / "result.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
