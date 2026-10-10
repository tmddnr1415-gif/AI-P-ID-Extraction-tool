import json, os, shutil, socket, subprocess, sys, time, urllib.request
from pathlib import Path
from urllib.parse import quote
S = Path(sys.argv[1]); OUT = S / "shots"; data = S / "q94"
shutil.rmtree(data, ignore_errors=True); shutil.copytree(S / "q75", data)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=os.getcwd(), PID_RENDER_POOL="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = f"http://127.0.0.1:{port}"; JOB = "48b5adbdd28c"
for _ in range(90):
    try: urllib.request.urlopen(base + "/version", timeout=2); break
    except Exception: time.sleep(1)
done = []
def step(name, fn):
    try: fn(); done.append("ok " + name)
    except Exception as e: done.append(f"FAIL {name}: {str(e)[:160]}")
    print(done[-1], flush=True)
from playwright.sync_api import sync_playwright
try:
  with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
    ctx = br.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
    ctx.add_init_script("try{localStorage.setItem('pid.side.off','1');localStorage.removeItem('pid.split');localStorage.setItem('pid.author','홍길동')}catch(e){}")
    pg = ctx.new_page(); pg.on("dialog", lambda d: d.accept())
    shot = lambda name, **k: pg.screenshot(path=str(OUT / name), **k)
    ready = "() => typeof S !== 'undefined' && S.job && !S.loading && S.vlist && S.vlist.length > 5"
    img = "() => { const i = document.querySelector('#sheet'); return i && i.complete && i.naturalWidth > 0; }"
    def home():
        pg.goto(f"{base}/?user={quote('홍길동')}"); pg.wait_for_timeout(2500); shot("01_home.png")
    step("home", home)
    def result():
        pg.evaluate(f"open('{JOB}')"); pg.wait_for_function(ready, timeout=180000); pg.wait_for_function(img, timeout=60000); pg.wait_for_timeout(1500)
        if pg.evaluate("() => !!S.side"): pg.evaluate("() => toggleSide(false)"); pg.wait_for_timeout(500)
        pg.evaluate("() => fit()"); pg.wait_for_timeout(800); shot("02_result.png")
    step("result", result)
    def evidence():
        key = pg.evaluate("() => (S.rows.find(r => r.page_no === S.page.page_no && !r.removed && r.values.description && r.values.tag_no) || S.rows.find(r => r.page_no === S.page.page_no && !r.removed)).key")
        pg.evaluate(f"() => select('{key}', false)"); pg.wait_for_timeout(1500); pg.evaluate("() => closeScopePop && closeScopePop()"); pg.wait_for_timeout(300)
        shot("03_evidence.png")
        ev = pg.evaluate("() => { const r = document.querySelector('#evidence').getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }")
        shot("03b_evidence_crop.png", clip={"x": ev[0], "y": ev[1], "width": ev[2], "height": min(ev[3], 1080 - ev[1])})
    step("evidence", evidence)
    def cells():
        key = pg.evaluate("() => S.sel || S.vlist[0].key")
        pg.evaluate(f"() => revealRow('{key}').scrollIntoView({{block:'center'}})"); pg.wait_for_timeout(300)
        pg.click(f'#body tr[data-key="{key}"] td[data-col="remark"]'); pg.keyboard.press("Shift+ArrowDown"); pg.keyboard.press("Shift+ArrowDown"); pg.wait_for_timeout(300)
        gw = pg.evaluate("() => { const r = document.querySelector('#right').getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }")
        shot("04_cells_range.png", clip={"x": gw[0], "y": gw[1], "width": gw[2], "height": gw[3]})
        pg.keyboard.press("Escape"); pg.dblclick(f'#body tr[data-key="{key}"] td[data-col="remark"]'); pg.wait_for_timeout(200); pg.keyboard.type("현장 확인 필요")
        pg.wait_for_timeout(200); shot("04b_cell_edit.png", clip={"x": gw[0], "y": gw[1], "width": gw[2], "height": gw[3]})
        pg.keyboard.press("Enter"); pg.wait_for_timeout(600)
        hd = pg.evaluate("() => { const r = document.querySelector('#who-chip').getBoundingClientRect(); return [r.x, r.y]; }")
        shot("04c_savestate.png", clip={"x": max(0, hd[0] - 420), "y": max(0, hd[1] - 20), "width": 1920 - max(0, hd[0] - 420), "height": 70})
    step("cells", cells)
    def scopepop():
        key = pg.evaluate("() => (S.rows.find(r => r.page_no === S.page.page_no && !r.removed && r.rect && r.rect.length === 4) || {}).key")
        pg.evaluate(f"() => {{ select('{key}', false); scopePop('{key}'); }}"); pg.wait_for_timeout(600)
        b = pg.evaluate("() => { const r = document.querySelector('.scopepop').getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }")
        shot("05_scopepop.png", clip={"x": max(0, b[0] - 260), "y": max(0, b[1] - 200), "width": 760, "height": 460})
        pg.evaluate("() => closeScopePop()")
    step("scopepop", scopepop)
    def qty():
        st = pg.evaluate("() => { const r = document.querySelector('#stage').getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }")
        pg.evaluate("() => { S.zoom = Math.max(S.zoom, 1.2); applyZoom(); }"); pg.wait_for_timeout(500)
        shot("06_qty_labels.png", clip={"x": st[0], "y": st[1], "width": st[2], "height": st[3]})
        pg.evaluate("() => fit()"); pg.wait_for_timeout(300)
    step("qty", qty)
    def mult():
        pg.evaluate("() => { const p = document.querySelector('#mult-panel'); if (p) { p.classList.remove('folded'); p.querySelectorAll('details').forEach(d => d.open = true); } }"); pg.wait_for_timeout(500)
        b = pg.evaluate("() => { const r = document.querySelector('#mult-panel').getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }")
        shot("07_mult_panel.png", clip={"x": b[0], "y": b[1], "width": b[2], "height": min(b[3], 1080 - b[1])})
    step("mult", mult)
    def markup():
        key = pg.evaluate("() => (S.rows.find(r => r.page_no === S.page.page_no && !r.removed && r.rect && r.rect.length === 4 && String(r.values.scope||'').startsWith('VENDOR')) || S.rows.find(r => r.page_no === S.page.page_no && r.rect && r.rect.length === 4)).key")
        pg.evaluate("() => setMarkup(true)"); pg.wait_for_timeout(7000)
        pg.evaluate(f"async () => {{ const r = S.rowByKey['{key}'].rect; await markupDialog([r[0]-4, r[1]-4, r[2]+4, r[3]+4]); }}"); pg.wait_for_timeout(1500)
        shot("08_markup_dialog.png")
        pg.evaluate("() => closeModal()"); pg.evaluate("() => setMarkup(false)"); pg.wait_for_timeout(300)
    step("markup", markup)
    def side():
        pno = pg.evaluate("""() => { const d = (S.rev && S.rev.deleted_candidates) || []; let best = null, n = -1;
            for (const p of S.pages) { if (!p.layers) continue; const c = pageChanges(p, d, S.prevRows || null); const k = (c.added||[]).length + (c.modified||[]).length + (c.deleted||[]).length; if (k > n) { n = k; best = p.page_no; } } return best; }""")
        pg.evaluate(f"() => showPage(S.pages.find(p => p.page_no === {pno}))"); pg.wait_for_timeout(1500)
        pg.evaluate("() => toggleSide(true, true)"); pg.wait_for_timeout(4000)
        pg.wait_for_function("() => { const i = document.querySelector('#cmp-sheet'); return i && i.complete && i.naturalWidth > 0; }", timeout=60000); pg.wait_for_timeout(1200)
        shot("09_side_by_side.png")
        pg.evaluate("() => toggleSide(false, true)"); pg.wait_for_timeout(500)
    step("side", side)
    def memo():
        pg.evaluate("() => showMemo(S.page.page_no)"); pg.wait_for_timeout(800)
        pg.fill("#memo-text", "p" + str(pg.evaluate("() => S.page.page_no")) + " — 드레인 라인 LIT 수량 재확인 요청 (발주처 회신 대기)")
        pg.click("#memo-save"); pg.wait_for_timeout(1200)
        b = pg.evaluate("() => { const r = document.querySelector('#memo').getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }")
        shot("10_memo.png", clip={"x": b[0], "y": max(0, b[1]), "width": b[2], "height": min(b[3], 1080 - max(0, b[1]))})
        # 핀
        row = pg.evaluate("() => { const r = S.rows.find(x => x.page_no === S.page.page_no && !x.removed && x.rect && x.rect.length === 4); return r ? r.rect : null; }")
        pg.evaluate(f"() => pinDialog([{row[0]}, {row[1]}, {row[0]}, {row[1]}])"); pg.wait_for_timeout(600)
        pg.fill(".pp-form textarea, #pin-text, .pp-form input[type=text]:not([readonly])", "이 LIT 는 벤더 스키드 공급 — 별표 확인") if pg.locator(".pp-form textarea").count() else None
        shot("11_pin_dialog.png")
        btn = pg.locator(".pp-form button").filter(has_text="저장")
        if btn.count(): btn.first.click(); pg.wait_for_timeout(1200)
        shot("11b_pin_on_drawing.png")
    step("memo+pin", memo)
    def review():
        pg.evaluate("() => { const b = [...document.querySelectorAll('#tabs button')].find(x => x.textContent.includes('검토')); if (b) b.click(); }"); pg.wait_for_timeout(1200)
        shot("12_review_tab.png")
        pg.evaluate("() => { const b = [...document.querySelectorAll('#tabs button')].find(x => x.textContent.trim().startsWith('전체') || x.dataset.tab === 'ALL'); if (b) b.click(); }"); pg.wait_for_timeout(800)
    step("review", review)
    def full():
        key = pg.evaluate("() => (S.rows.find(r => r.page_no === S.page.page_no && !r.removed && r.rect && r.rect.length === 4) || {}).key")
        pg.evaluate("() => setFull(true)"); pg.wait_for_timeout(800)
        pg.evaluate(f"() => select('{key}', false)"); pg.wait_for_timeout(1200); pg.evaluate("() => closeScopePop && closeScopePop()"); pg.wait_for_timeout(300)
        shot("13_fullscreen_edit.png"); pg.evaluate("() => setFull(false)"); pg.wait_for_timeout(500)
    step("full", full)
    def kbd():
        pg.evaluate("() => showShortcuts()"); pg.wait_for_timeout(500); shot("14_shortcuts.png"); pg.evaluate("() => closeModal()")
    step("kbd", kbd)
    def voc():
        pg.evaluate("() => vocDialog({})"); pg.wait_for_timeout(1200); shot("15_voc.png"); pg.evaluate("() => closeModal()")
    step("voc", voc)
    def popout():
        with ctx.expect_page() as pi: pg.click('.pop-btn[data-pane="drawing"]')
        dr = pi.value; dr.set_viewport_size({"width": 1920, "height": 1080})
        dr.wait_for_function(ready, timeout=180000); dr.wait_for_function(img, timeout=60000); dr.wait_for_timeout(1500)
        dr.screenshot(path=str(OUT / "16_popout_drawing.png")); pg.wait_for_timeout(800); shot("16b_popout_list.png")
        dr.close(); pg.wait_for_timeout(1500)
    step("popout", popout)
    def progress():
        r = json.loads(urllib.request.urlopen(urllib.request.Request(f"{base}/jobs/{JOB}/reanalyse", method="POST"), timeout=30).read())
        nid = r.get("job_id") or r.get("id")
        pg.goto(f"{base}/?user={quote('홍길동')}"); pg.wait_for_timeout(2500); shot("17_home_running.png")
        pg.evaluate(f"() => watch('{nid}')"); pg.wait_for_timeout(45000); shot("17b_progress.png")
        urllib.request.urlopen(urllib.request.Request(f"{base}/jobs/{nid}/cancel", method="POST"), timeout=30).read(); pg.wait_for_timeout(3000)
    step("progress", progress)
    br.close()
finally:
    srv.terminate(); srv.wait(10)
print("\n".join(done))
