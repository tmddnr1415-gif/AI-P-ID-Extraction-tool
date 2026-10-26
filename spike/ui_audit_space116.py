"""hotfix116 — 판넬 공간확보 최신판을 /space 에서 띄워 눌러 본다 (빈 데이터 폴더 · 실 DB 를 안 연다).

프로젝트 → 룸 → Rev 만들기 → 배치 시작 → 서버에 저장 → 3D → Rev 지우기(화면 안 확인창) → 프로젝트 지우기(이름 옮겨 적기).
    python3 spike/ui_audit_space116.py out/hotfix116/ui
"""
from __future__ import annotations

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
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "out/hotfix116/ui")
PORT = 8765
DATA = Path(tempfile.mkdtemp(prefix="space116_"))
ENV = {**os.environ, "PID_DATA_DIR": str(DATA), "PID_LOGIC_WARM": "0", "PID_PAGE_WARM": "0", "PID_ROWS_WARM": "0",
       "PID_RENDER_POOL": "0"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
                           cwd=ROOT, env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    res, errs = [], []
    try:
        for _ in range(120):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/version", timeout=1)
                break
            except OSError:
                time.sleep(0.5)
        with sync_playwright() as pw:
            b = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium")
            pg = b.new_page(viewport={"width": 1600, "height": 950})
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(f"http://127.0.0.1:{PORT}/space?embed=1&user=%ED%99%8D%EA%B8%B8%EB%8F%99")
            pg.wait_for_timeout(1500)
            pg.screenshot(path=str(OUT / "1_home.png"))
            pg.click("#hmNewBtn"); pg.fill("#hmNewName", "AMIRAL 시험"); pg.click("#hmCreate"); pg.wait_for_timeout(800)
            pg.click("#hmRoomNew"); pg.fill("#hmRoomName", "CER-1"); pg.click("#hmRoomCreate"); pg.wait_for_timeout(800)
            pg.click("#hmRevNew"); pg.fill("#hmRevName", "A"); pg.click("#hmRevCreate"); pg.wait_for_timeout(800)
            pg.screenshot(path=str(OUT / "2_room_rev.png"))
            res.append(("룸 선택 = CER-1", pg.eval_on_selector("#hmRoomSel", "s=>s.options[s.selectedIndex]?.text||''")))
            res.append(("Rev 선택 = A", pg.eval_on_selector("#hmRevSel", "s=>s.value")))
            res.append(("배치 시작 가능", not pg.is_disabled("#hmGo")))
            pg.click("#hmGo"); pg.wait_for_timeout(1200)
            if pg.is_visible("#autodlg"):            # hotfix121 — 새 룸은 Option A(자동 배치) 창부터 연다
                res.append(("새 룸 → Option A 창", True)); pg.click("#aClose"); pg.wait_for_timeout(300)
            pg.screenshot(path=str(OUT / "3_editor.png"))
            pg.click("#bSrvOpen2"); pg.wait_for_timeout(800)
            pg.fill("#hMemo", "첫 배치"); pg.click("#hSave"); pg.wait_for_timeout(1000)
            pg.screenshot(path=str(OUT / "4_saved.png"))
            pj = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/space/api/projects").read().decode()
            res.append(("서버 목록에 룸 · Rev", '"CER-1"' in pj and '"A"' in pj))
            res.append(("저장 1건", '"saves": 1' in pj or '"saves":1' in pj))
            pg.click("#hClose"); pg.wait_for_timeout(300)
            pg.click("#b3d"); pg.wait_for_timeout(1500)
            pg.screenshot(path=str(OUT / "5_3d.png"))
            pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
            # 첫 화면으로 — Rev 지우기 (화면 안 확인창)
            pg.goto(f"http://127.0.0.1:{PORT}/space?embed=1&user=%ED%99%8D%EA%B8%B8%EB%8F%99"); pg.wait_for_timeout(1500)
            pid = pg.eval_on_selector("#hmProj", "s=>s.value")
            if not pid:
                pg.select_option("#hmProj", index=1); pg.wait_for_timeout(800)
            pg.wait_for_timeout(500)
            pg.click("#hmRevDel"); pg.wait_for_timeout(300)
            res.append(("Rev 지우기 확인창", pg.is_visible(".askyes")))
            pg.screenshot(path=str(OUT / "6_del_rev_ask.png"))
            pg.click(".askyes [data-y]"); pg.wait_for_timeout(1000)
            pj = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/space/api/projects").read().decode()
            res.append(("Rev 지워짐 · 저장 0", '"revs": []' in pj.replace('"revs":[]', '"revs": []')))
            pg.click("#hmProjDel"); pg.wait_for_timeout(300)
            pg.fill(".askyes input", "AMIRAL 시험"); pg.screenshot(path=str(OUT / "7_del_proj_ask.png"))
            pg.click(".askyes [data-y]"); pg.wait_for_timeout(1000)
            pj = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/space/api/projects").read().decode()
            res.append(("프로젝트 지워짐", '"projects": []' in pj.replace('"projects":[]', '"projects": []')))
            res.append(("휴지통", any((DATA / "space" / "_trash").glob("*_project"))))
            pg.screenshot(path=str(OUT / "8_after.png"))
            b.close()
    finally:
        srv.terminate()
        shutil.rmtree(DATA, ignore_errors=True)
    res.append(("페이지 오류 0", not errs))
    lines = [f"{'✔' if v not in (False, '', None) else '✘'} {k}: {v}" for k, v in res] + [f"오류: {e}" for e in errs]
    (OUT / "result.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
