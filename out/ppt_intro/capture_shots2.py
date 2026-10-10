import json, os, shutil, socket, subprocess, sys, time, urllib.request
from pathlib import Path
from urllib.parse import quote
S = Path(sys.argv[1]); OUT = S / "shots"; data = S / "q95"
shutil.rmtree(data, ignore_errors=True); shutil.copytree(S / "q75", data)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=os.getcwd(), PID_RENDER_POOL="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = f"http://127.0.0.1:{port}"; JOB = "48b5adbdd28c"
for _ in range(90):
    try: urllib.request.urlopen(base + "/version", timeout=2); break
    except Exception: time.sleep(1)
from playwright.sync_api import sync_playwright
done = []
def step(name, fn):
    try: fn(); done.append("ok " + name)
    except Exception as e: done.append(f"FAIL {name}: {str(e)[:200]}")
    print(done[-1], flush=True)
try:
  with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
    ctx = br.new_context(viewport={"width": 1920, "height": 1080})
    ctx.add_init_script("try{localStorage.removeItem('pid.side.off');localStorage.removeItem('pid.split');localStorage.setItem('pid.author','홍길동')}catch(e){}")
    pg = ctx.new_page(); pg.on("dialog", lambda d: d.accept())
    shot = lambda name, **k: pg.screenshot(path=str(OUT / name), **k)
    pg.goto(f"{base}/?user={quote('홍길동')}"); pg.wait_for_timeout(1500)
    pg.evaluate(f"open('{JOB}')")
    pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.pages && S.pages.length > 0", timeout=180000); pg.wait_for_timeout(2500)
    def side():
        dels = json.loads(urllib.request.urlopen(f"{base}/jobs/{JOB}/revision").read()).get("deleted_candidates", [])
        by = {}
        for d in dels: by[d.get("drawing_no") or ""] = by.get(d.get("drawing_no") or "", 0) + 1
        pages = pg.evaluate("() => S.pages.map(p => ({n: p.page_no, d: p.drawing_no}))")
        have = {p["d"] for p in pages}
        cand = sorted(((n, d) for d, n in by.items() if d in have), reverse=True)
        target = next((p["n"] for p in pages if cand and p["d"] == cand[0][1]), None)
        pg.select_option("#page-select", str(target)); pg.wait_for_timeout(2500)
        if not pg.evaluate("() => S.side"): pg.click("#rev-switch button.side")
        pg.wait_for_function("() => S.side && document.querySelector('#cmp-sheet') && document.querySelector('#cmp-sheet').complete && document.querySelector('#cmp-sheet').naturalWidth > 0", timeout=90000)
        pg.wait_for_timeout(2000); shot("09_side_by_side.png")
        pg.click("#rev-switch button.side"); pg.wait_for_timeout(600)
    step("side", side)
    def memo():
        pg.evaluate("() => memoOpen(true)"); pg.wait_for_timeout(800)
        pg.fill("#memo-text", "Rev.B 확인: 드레인 라인 LIT 수량 재확인 요청\n- 발주처 회신 대기 (10/09)")
        pg.click("#memo-save"); pg.wait_for_timeout(600)
        ab = pg.query_selector(".author-bar")
        if ab: ab.query_selector("button.ok").click()
        pg.wait_for_timeout(1500)
        b = pg.evaluate("() => { const r = document.querySelector('#memo').getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }")
        shot("10_memo.png", clip={"x": b[0], "y": max(0, b[1]), "width": b[2], "height": min(b[3], 1080 - max(0, b[1]))})
        row = pg.evaluate("() => { const r = S.rows.find(x => x.page_no === S.page.page_no && !x.removed && x.rect && x.rect.length === 4); return r ? r.rect : null; }")
        pg.evaluate(f"() => pinDialog([{row[0]}, {row[1]}, {row[0]}, {row[1]}])"); pg.wait_for_timeout(800)
        ta = pg.locator(".pp-form textarea")
        if ta.count(): ta.first.fill("이 LIT 는 벤더 스키드 공급 — 별표 확인")
        shot("11_pin_dialog.png")
        btn = pg.locator(".pp-form button").filter(has_text="저장")
        if btn.count(): btn.first.click(); pg.wait_for_timeout(1500)
        pg.evaluate("() => memoOpen(true)"); pg.wait_for_timeout(600)
        shot("11b_pin_on_drawing.png")
    step("memo+pin", memo)
    br.close()
finally:
    srv.terminate(); srv.wait(10)
print("\n".join(done))
