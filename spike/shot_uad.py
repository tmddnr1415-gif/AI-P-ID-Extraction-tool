"""UAD 결과 화면을 실제로 띄워 스크린샷을 남긴다 (28·29회차 진행 현황).

    python3 spike/shot_uad.py <결과.json> <내보낼 폴더>

★ 실 DB 를 열지 않는다 — 저장된 결과로 임시 DB 를 세우고, 쓰는 뿌리를 버릴
폴더로 돌린 뒤 그 DB 로만 서버를 띄운다 (17회차 격리).
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def main() -> int:
    src = Path(sys.argv[1])
    outdir = Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    data = Path(tempfile.mkdtemp(prefix="shot-"))
    os.environ["PID_DATA_DIR"] = str(data)
    db_path = data / "app.db"
    from app import db

    blob = json.loads(src.read_text())
    result = blob.get("result", blob)
    con = db.connect(db_path)
    job = "shotuad00001"
    con.execute("INSERT INTO job(id, filename, pdf_path, status, created_at, project,"
                " revision) VALUES(?,?,?,?,datetime('now'),?,?)",
                (job, "UAD_binding.pdf", str(ROOT / "data" / "UAD_binding.pdf"),
                 "done", "UAD", "A"))
    con.commit()
    db.store_result(con, job, result)
    con.commit()
    con.close()

    port = free_port()
    env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
    srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app",
                            "--host", "127.0.0.1", "--port", str(port)],
                           cwd=str(ROOT), env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        import urllib.request
        for _ in range(60):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/home" % port, timeout=2)
                break
            except Exception:
                time.sleep(1)
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            br = pw.chromium.launch()
            pg = br.new_page(viewport={"width": 1600, "height": 1000})
            pg.goto("http://127.0.0.1:%d/" % port)
            pg.wait_for_timeout(1500)
            pg.screenshot(path=str(outdir / "1_첫화면.png"))
            row = pg.query_selector("a.revrow")
            if row:
                row.click()
                pg.wait_for_timeout(6000)
                pg.screenshot(path=str(outdir / "2_결과화면.png"))
                cell = pg.query_selector("td.col-tag_no, td.col-tag")
                if cell:
                    cell.click()
                    pg.wait_for_timeout(1200)
                    pg.screenshot(path=str(outdir / "3_근거패널.png"))
            br.close()
    finally:
        srv.terminate()
    print("찍은 파일:", sorted(p.name for p in outdir.glob("*.png")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
