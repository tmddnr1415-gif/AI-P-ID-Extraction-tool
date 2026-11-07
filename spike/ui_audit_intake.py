"""hotfix81 — 새 프로젝트 점검표 화면 자기검증 (사본 데이터 · 실 DB 를 안 연다).

    PID_UI_SRC_DB=/path/app.db python3 spike/ui_audit_intake.py
띠의 점검표 칩 → 모달 · 더보기 메뉴의 단추 · ?format=text · 페이지 오류 0.
"""
from __future__ import annotations
import os, shutil, socket, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "hotfix81" / "ui"; OUT.mkdir(parents=True, exist_ok=True)
FOUND = []
def note(s): print(s, flush=True); FOUND.append(s)
def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p
src = Path(os.environ.get("PID_UI_SRC_DB") or "/tmp/hf81/qfe.db")
data = Path(tempfile.mkdtemp(prefix="intakeui-")); (data / "uploads").mkdir()
shutil.copy2(src, data / "app.db")
port = free_port()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT), PID_PAGE_WARM="0", PID_ROWS_WARM="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    import urllib.request
    for _ in range(90):
        try: urllib.request.urlopen(f"http://127.0.0.1:{port}/home", timeout=2); break
        except Exception: time.sleep(1)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
        br = pw.chromium.launch(executable_path=exe if Path(exe).exists() else None)
        pg = br.new_page(viewport={"width": 1700, "height": 1000})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
        pg.goto(f"http://127.0.0.1:{port}/"); pg.wait_for_timeout(2500)
        pg.evaluate("() => document.querySelectorAll('details.pjt').forEach(d => d.open = true)")
        pg.wait_for_timeout(400)
        rr = pg.query_selector("a.revrow")
        if rr is None: note("★ 결과로 들어갈 행이 없다"); raise SystemExit(2)
        rr.click(); pg.wait_for_timeout(9000)
        # ① 띠의 칩
        chip = pg.query_selector("#legend-bar .lb-intake button")
        note(f"① 띠 칩 {'있음' if chip else '없음'} · 글 {pg.inner_text('#legend-bar .lb-intake') if chip else ''!r}")
        pg.query_selector("#legend-bar").screenshot(path=str(OUT / "1_띠.png"))
        pg.evaluate("() => document.querySelector('#legend-bar .lb-intake button').click()"); pg.wait_for_timeout(800)
        vis = pg.evaluate("() => !document.querySelector('#modal').classList.contains('hidden')")
        title = pg.inner_text("#modal-title")
        n_todo = pg.evaluate("() => document.querySelectorAll('#modal .intake-todo li').length")
        n_sec = pg.evaluate("() => document.querySelectorAll('#modal details.intake-sec').length")
        head = pg.inner_text("#modal .intake-head")
        note(f"② 모달 {vis} · 제목 {title!r} · 사람 몫 {n_todo} · 구획 {n_sec} · 머리 {head!r}")
        pg.query_selector("#modal .modal-card, #modal").screenshot(path=str(OUT / "2_모달.png"))
        # ③ 닫고 더보기 메뉴에서 다시
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        closed = pg.evaluate("() => document.querySelector('#modal').classList.contains('hidden')")
        if not closed:
            pg.evaluate("() => document.querySelector('#modal').classList.add('hidden')")
        pg.evaluate("() => { document.querySelector('#more-actions').open = true; }"); pg.wait_for_timeout(300)
        pg.evaluate("() => document.querySelector('#intake-btn').click()"); pg.wait_for_timeout(500)
        vis2 = pg.evaluate("() => !document.querySelector('#modal').classList.contains('hidden')")
        note(f"③ Esc 로 닫힘 {closed} · 더보기 단추로 다시 열림 {vis2}")
        # ④ 글 형식
        job = pg.evaluate("() => S.job.id")
        txt = urllib.request.urlopen(f"http://127.0.0.1:{port}/jobs/{job}/intake?format=text").read().decode()
        note(f"④ ?format=text 첫 줄 {txt.splitlines()[0]!r}")
        note(f"⑤ 페이지 오류 {len(errs)} {errs[:3]}")
        br.close()
finally:
    srv.terminate()
    (OUT / "result.txt").write_text("\n".join(FOUND), encoding="utf-8")
