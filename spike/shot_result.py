"""식별 결과 화면을 실제로 띄워 스크린샷을 남긴다 (31회차 — 어느 프로젝트든).

    python3 spike/shot_result.py <프로젝트명> <결과.json> <내보낼 폴더>

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


PDFS = {p["name"]: p["pdf"] for p in
        json.loads((ROOT / "spike" / "projects_3p.json").read_text())["projects"]}


def main() -> int:
    name = sys.argv[1]
    src = Path(sys.argv[2])
    outdir = Path(sys.argv[3])
    outdir.mkdir(parents=True, exist_ok=True)
    data = Path(tempfile.mkdtemp(prefix="shot-"))
    os.environ["PID_DATA_DIR"] = str(data)
    db_path = data / "app.db"
    from app import db

    blob = json.loads(src.read_text())
    result = blob.get("result", blob)
    con = db.connect(db_path)
    job = "shot" + name.replace(" ", "").lower()[:8].ljust(8, "0")
    pdf = ROOT / PDFS[name]
    import hashlib
    sha = hashlib.sha256(pdf.read_bytes()).hexdigest() if pdf.exists() else ""
    con.execute(
        "INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, created_at, status,"
        " progress, message, fingerprint, project, revision)"
        " VALUES (?,?,?,?,?,'done',1.0,'',?,?,?)",
        (job, pdf.name, sha, str(pdf), time.time(),
         result.get("fingerprint", ""), name, "A"))
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
            # 이 환경의 브라우저는 `/opt/pw-browsers` 에 있다 (내려받지 않는다)
            exe = None
            for cand in ("/opt/pw-browsers/chromium/chrome-linux/chrome",
                         "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"):
                if Path(cand).exists():
                    exe = cand
                    break
            br = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
            pg = br.new_page(viewport={"width": 1600, "height": 1000})
            pg.goto("http://127.0.0.1:%d/" % port)
            pg.wait_for_timeout(1500)
            pg.screenshot(path=str(outdir / "1_첫화면.png"))
            row = (pg.query_selector("a.revrow")
                   or pg.query_selector(f"text={pdf.name}"))
            if row:
                row.click()
                pg.wait_for_timeout(6000)
                pg.screenshot(path=str(outdir / "2_결과화면.png"))
                # TAG·SCOPE 열은 오른쪽에 있다 — 그 열의 bounding box 를 읽어
                # 가로 스크롤을 맞춘다 (§8 — 화면 비율로 어림해 자르지 않는다)
                hdr = pg.query_selector("th:has-text('TAG')")
                if hdr:
                    pg.evaluate("el => el.scrollIntoView({inline:'center'})", hdr)
                    pg.wait_for_timeout(600)
                    pg.screenshot(path=str(outdir / "3_TAG열.png"))
                sc = pg.query_selector("th:has-text('SCOPE')")
                if sc:
                    pg.evaluate("el => el.scrollIntoView({inline:'center'})", sc)
                    pg.wait_for_timeout(600)
                    pg.screenshot(path=str(outdir / "4_SCOPE열.png"))
                mp = pg.query_selector("#mult-panel:not(.hidden)")
                if mp:
                    pg.evaluate("el => el.scrollIntoView({block:'center'})", mp)
                    pg.wait_for_timeout(400)
                    mp.screenshot(path=str(outdir / "5_수량승수_패널.png"))
                    val = pg.query_selector("#mult-panel .mval")
                    if val:
                        val.fill("4")
                        val.dispatch_event("input")
                        pg.wait_for_timeout(300)
                        mp.screenshot(path=str(outdir / "6_수량승수_전후미리보기.png"))
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
