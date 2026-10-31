"""hotfix74 — 기록을 만드는 단추를 두 번 누른다 (느린 망 0.8초 · 더블클릭 + 한 번 더).

    python3 spike/ui_double_click.py <data_dir 사본> <job>

옛 코드: VOC 2건 · 메모 2판 → 고친 뒤: 1건 · 1판 (`guarded` · `saveMemo` 재진입 막기).
"""
import os, socket, subprocess, sys, time, urllib.request, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
data, JOB = sys.argv[1], sys.argv[2]
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
base = f"http://127.0.0.1:{port}"
env = dict(os.environ, PID_DATA_DIR=data, PYTHONPATH=str(ROOT), PID_PAGE_WARM="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)], cwd=str(ROOT), env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
def get(p): return json.loads(urllib.request.urlopen(base + p, timeout=30).read())
try:
    for _ in range(120):
        try: urllib.request.urlopen(base + "/version", timeout=2); break
        except Exception: time.sleep(0.5)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        pg = br.new_context(viewport={"width": 1600, "height": 950}).new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("dialog", lambda d: d.accept())
        # 느린 망 — 서버 응답을 0.8초 늦춰 두 번째 누름이 첫 요청이 끝나기 전에 닿게 한다
        pg.route("**/voc", lambda r: (time.sleep(0.8), r.continue_()))
        pg.route("**/memo/*", lambda r: (time.sleep(0.8) if r.request.method == "POST" else None, r.continue_()))
        pg.goto(base + "/?user=시뮬"); pg.wait_for_timeout(2000)
        pg.evaluate(f"open('{JOB}')")
        pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.pages && S.pages.length > 0", timeout=180000)
        pg.wait_for_timeout(1500)
        n0 = get("/voc")["counts"]["total"]
        pg.evaluate("() => vocDialog({})"); pg.wait_for_timeout(1200)
        pg.fill("#vc-note", "두 번 눌러 보기")
        pg.dblclick("#vc-save"); pg.click("#vc-save", force=True, no_wait_after=True)
        pg.wait_for_timeout(4000)
        n1 = get("/voc")["counts"]["total"]
        pg.evaluate("() => closeModal && closeModal()")
        page_no = pg.evaluate("() => S.page.page_no")
        m0 = len(get(f"/jobs/{JOB}/memo/{page_no}").get("history", []))
        pg.evaluate("() => memoOpen && memoOpen(true)"); pg.wait_for_timeout(800)
        pg.fill("#memo-text", "두 번 저장")
        pg.dblclick("#memo-save"); pg.keyboard.press("Control+Enter")
        pg.wait_for_timeout(4000)
        mm = get(f"/jobs/{JOB}/memo/{page_no}")
        m1 = len(mm.get("history", []))
        print(json.dumps({"voc_added": n1 - n0, "memo_added": m1 - m0, "memo_keys": list(mm)[:6], "errors": errs[:3]}, ensure_ascii=False))
        br.close()
finally:
    srv.terminate()
