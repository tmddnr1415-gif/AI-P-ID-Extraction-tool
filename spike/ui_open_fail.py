"""hotfix74 — 결과를 여는 도중 요청 하나가 끊긴다 (/rows · /pages · /legend 를 한 번씩 끊음).

    python3 spike/ui_open_fail.py <data_dir 사본> <job>

옛 코드: 목록 0행 · S.loading 켜진 채 · 말 없음 → 고친 뒤: "결과를 다 받지 못했습니다" + [다시 열기] · 다시 열면 1991행.
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
try:
    for _ in range(120):
        try: urllib.request.urlopen(base + "/version", timeout=2); break
        except Exception: time.sleep(0.5)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        for which in ["/rows", "/pages", "/legend"]:
            pg = br.new_context(viewport={"width": 1600, "height": 950}).new_page(); errs = []; dl = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("dialog", lambda d: (dl.append(d.message), d.accept()))
            state = {"n": 0}
            def make(w):
                def handler(route, request=None):
                    if w in route.request.url and state["n"] == 0:
                        state["n"] += 1; return route.abort()
                    return route.continue_()
                return handler
            handler = make(which)
            def _unused(route):
                if False:
                    state["n"] += 1; return route.abort()
                return route.continue_()
            pg.route("**/jobs/**", handler)
            pg.goto(base + "/"); pg.wait_for_timeout(1500)
            pg.evaluate(f"open('{JOB}').catch(e => window.__openErr = String(e))")
            pg.wait_for_timeout(6000)
            st = pg.evaluate("() => ({loading: !!S.loading, job: S.job && S.job.id, rows: (S.rows||[]).length, pages: (S.pages||[]).length, err: (document.querySelector('#open-err')||{}).innerText || '', main: !document.querySelector('#main').classList.contains('hidden'), banner: (document.querySelector('#net-banner')||{}).innerText || '', status: (document.querySelector('#status')||{}).innerText || ''})")
            print(which, "1차", json.dumps(st, ensure_ascii=False), "dialogs", dl[:2], "errs", errs[:2])
            pg.evaluate(f"open('{JOB}').catch(e => window.__openErr2 = String(e))")
            try:
                pg.wait_for_function("() => S.job && !S.loading && S.rows && S.rows.length > 0 && S.pages && S.pages.length > 0", timeout=60000)
                ok = True
            except Exception:
                ok = False
            print(which, "2차 열림", ok, pg.evaluate("() => (S.rows||[]).length"))
            pg.screenshot(path=f"/tmp/openfail_{which.strip('/')}.png")
            pg.close()
        br.close()
finally:
    srv.terminate()
