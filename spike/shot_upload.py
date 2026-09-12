"""33회차 — PDF 를 **화면으로 올려** 끝 화면을 찍는다 (실패 화면 · 완료 화면).

    python3 spike/shot_upload.py <저장소 뿌리> <PDF> <내보낼 png> [프로젝트명]

저장소 뿌리를 인자로 받는 이유: 고치기 **전** 코드(worktree)와 **후** 코드를 같은
절차로 찍어 나란히 놓기 위해서다.  ★ 실 DB 를 열지 않는다 (PID_DATA_DIR 임시).
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


def main() -> int:
    root, pdf, png = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), Path(sys.argv[3])
    project = sys.argv[4] if len(sys.argv) > 4 else "SYN"
    png.parent.mkdir(parents=True, exist_ok=True)
    data = Path(tempfile.mkdtemp(prefix="shotup-"))
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(root))
    srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app",
                            "--host", "127.0.0.1", "--port", str(port)],
                           cwd=str(root), env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/home", timeout=2); break
            except Exception:
                time.sleep(1)
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            br = pw.chromium.launch(executable_path=CHROME if Path(CHROME).exists() else None)
            pg = br.new_page(viewport={"width": 1500, "height": 1000})
            pg.goto(f"http://127.0.0.1:{port}/"); pg.wait_for_timeout(2000)
            pg.click("#proj-new-btn"); pg.fill("#proj-name", project); pg.click("#proj-save")
            pg.wait_for_timeout(1200)
            pg.set_input_files("#file", str(pdf))
            t0 = time.time(); state = "timeout"
            while time.time() - t0 < 900:
                title = pg.eval_on_selector("#prog-title", "e => e.textContent") or ""
                main_on = pg.eval_on_selector("#main", "e => !e.classList.contains('hidden')")
                if "실패" in title:
                    state = "failed"; break
                if main_on:
                    state = "done"; break
                pg.wait_for_timeout(2000)
            pg.wait_for_timeout(1500)
            pg.screenshot(path=str(png), full_page=False)
            title = pg.eval_on_selector("#prog-title", "e => e.textContent")
            msg = pg.eval_on_selector("#prog-msg", "e => e.textContent")
            print({"state": state, "seconds": round(time.time() - t0, 1),
                   "title": title, "message": (msg or "")[:300], "png": str(png)})
            br.close()
    finally:
        srv.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
