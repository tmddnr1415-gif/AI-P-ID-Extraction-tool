"""hotfix85 — 글자를 한 글자도 읽을 수 없는 PDF 를 올리면 **DXF 로 올려 달라는 안내창**이 뜨는가.

    python3 spike/ui_audit_dxf_guide.py data/newproj/1_HAC.pdf OUTDIR

Takhiatash 의 HRSG 단장(글자가 전부 선으로 그려진 PDF)을 실제 업로드 경로로 올려 실패 화면에서
① 안내창이 저절로 뜨는가 ② 단계가 적혀 있는가 ③ [첫 화면에서 DXF 올리기] 를 누르면 첫 화면이 열리고
입력 종류가 DXF 로 바뀌는가 ④ 실패 화면의 [DXF 로 올리는 법] 으로 다시 열리는가 를 눌러서 본다.
셋째 인자 `partial` — 몇 장만 선으로 그려진 PDF(Takhiatash + HRSG 단장 넷).  분석은 끝나고, 결과 화면의
'장 도면번호' 판이 그 장들을 짚어 DXF 안내를 내는가를 본다.
실 DB 는 열지 않는다 (임시 데이터 폴더 · sha256 대조).
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
PDF = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
PARTIAL = len(sys.argv) > 3 and sys.argv[3] == "partial"
REAL = ROOT / "app" / "_data" / "app.db"
real_before = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""
LOG: list[str] = []


def note(s):
    print(s, flush=True)
    LOG.append(s)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


data = Path(tempfile.mkdtemp(prefix="auditdxf-"))
os.environ["PID_DATA_DIR"] = str(data)
from app import revisions  # noqa: E402
PROJECT = "HRSG"
revisions.create_project(data, PROJECT)
port = free_port()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT), PID_PAGE_WARM="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                        "--port", str(port)], cwd=str(ROOT), env=env,
                       stdout=open(OUT / "server.log", "w"), stderr=subprocess.STDOUT)
base = f"http://127.0.0.1:{port}"
ok = {}
try:
    for _ in range(90):
        try:
            urllib.request.urlopen(base + "/home", timeout=2); break
        except Exception:
            time.sleep(1)
    boundary = "----auditdxf"
    body = b""
    for k, v in (("project", PROJECT), ("compared_with", ""), ("input_kind", "PDF")):
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"pdf\"; filename=\"{PDF.name}\"\r\n"
             f"Content-Type: application/pdf\r\n\r\n").encode() + PDF.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(base + "/jobs", data=body, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    job = json.loads(urllib.request.urlopen(req, timeout=60).read())["job_id"]
    note(f"업로드 → 분석 {job} ({PDF.name})")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
        br = pw.chromium.launch(executable_path=exe if Path(exe).exists() else None)
        pg = br.new_page(viewport={"width": 1440, "height": 960})
        errs: list[str] = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"{base}/#{job}")
        if PARTIAL:
            t0 = time.time()
            while time.time() - t0 < 900:
                st = json.loads(urllib.request.urlopen(f"{base}/jobs/{job}", timeout=10).read())
                if st.get("status") in ("done", "failed", "cancelled"):
                    break
                time.sleep(3)
            note(f"   분석 {st.get('status')}")
            pg.goto(f"{base}/")
            pg.wait_for_selector("a.revrow", timeout=60000)
            pg.click("a.revrow")
            pg.wait_for_function("() => !document.querySelector('#main').classList.contains('hidden')", timeout=120000)
            pg.wait_for_function("() => !document.querySelector('#sheet-panel').classList.contains('hidden')", timeout=60000)
            pg.wait_for_timeout(800)
            if pg.evaluate("() => document.querySelector('#sheet-panel').classList.contains('folded')"):
                pg.click("#sheet-panel .mfold"); pg.wait_for_timeout(800)
            line = " ".join((pg.text_content("#sheet-panel .dxf-line") or "").split())
            note(f"① 장 도면번호 판: {line}")
            ok["판에 DXF 줄"] = "p61, p62, p63, p64" in line
            pg.screenshot(path=str(OUT / "1_결과_장도면번호판_DXF.png"), full_page=False)
            pg.click("#sheet-panel .sdxf")
            pg.wait_for_function("() => !document.querySelector('#modal').classList.contains('hidden')", timeout=5000)
            pg.wait_for_timeout(300)
            body_t = " ".join(pg.text_content("#modal-body").split())
            ok["안내창 — 그 장들"] = "p61, p62, p63, p64" in body_t
            note(f"② 안내창: {body_t[:200]}")
            pg.screenshot(path=str(OUT / "2_몇장만_DXF_안내창.png"), full_page=False)
            pg.click("#dxf-close")
        else:
            pg.wait_for_function("() => /실패/.test((document.querySelector('#prog-title') || {}).textContent || '')", timeout=180000)
            pg.wait_for_function("() => !document.querySelector('#modal').classList.contains('hidden')", timeout=30000)
            pg.wait_for_timeout(500)
            title = pg.text_content("#modal-title")
            body_t = " ".join(pg.text_content("#modal-body").split())
            ok["안내창 저절로 뜸"] = title == "DXF 파일로 올려 주세요"
            ok["단계 넷"] = pg.evaluate("() => document.querySelectorAll('#modal-body .dxf-steps li').length") == 4
            ok["가르치기 판은 안 뜸"] = pg.evaluate("() => document.querySelector('#tbfix').classList.contains('hidden')")
            note(f"① 안내창: {title} — {body_t[:220]}")
            pg.screenshot(path=str(OUT / "1_실패와_DXF_안내창.png"), full_page=False)
            pg.click("#dxf-close")
            pg.wait_for_timeout(300)
            ok["닫기"] = pg.evaluate("() => document.querySelector('#modal').classList.contains('hidden')")
            ok["실패 화면에 버튼"] = pg.is_visible("#prog-dxf")
            hint = " ".join((pg.text_content("#prog-hint") or "").split())
            note(f"② 실패 화면 안내: {hint}")
            pg.screenshot(path=str(OUT / "2_실패화면_버튼.png"), full_page=False)
            pg.click("#prog-dxf")
            pg.wait_for_function("() => !document.querySelector('#modal').classList.contains('hidden')", timeout=5000)
            pg.click("#dxf-go")
            pg.wait_for_timeout(800)
            ok["첫 화면"] = pg.is_visible("#drop")
            ok["입력 종류 DXF"] = pg.evaluate("() => (document.querySelector('input[name=input_kind]:checked') || {}).value") == "DXF"
            note(f"③ 첫 화면으로: 보임 {ok['첫 화면']} · 입력 종류 DXF {ok['입력 종류 DXF']} · 안내 '{pg.text_content('#drop-head')}'")
            pg.screenshot(path=str(OUT / "3_첫화면_DXF선택.png"), full_page=False)
        ok["페이지 오류 0"] = not errs
        note(f"④ 페이지 오류 {len(errs)} {errs[:2]}")
        br.close()
finally:
    srv.terminate()
    try:
        srv.wait(timeout=20)
    except Exception:
        srv.kill()
    ok["실 DB 같음"] = (hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else "") == real_before
    note("결과: " + " · ".join(f"{k} {'✔' if v else '✖'}" for k, v in ok.items()))
    (OUT / "log.txt").write_text("\n".join(LOG), encoding="utf-8")
