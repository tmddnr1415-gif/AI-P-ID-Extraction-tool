import sys, json, time
from playwright.sync_api import sync_playwright
OUT = sys.argv[1]; JOB = sys.argv[2]; QUERY = sys.argv[3]; ACT = sys.argv[4]; SHEET = sys.argv[5] if len(sys.argv) > 5 else ""
errs = []
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome"); pg = b.new_page(viewport={"width": 1700, "height": 1000})
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"http://localhost:8070/logic#job={JOB}")
    pg.wait_for_selector("#seq-btn", timeout=60000); time.sleep(4)
    pg.evaluate("localStorage.removeItem('logic.seq.mode'); localStorage.setItem('logic.seq.path','1')")
    pg.evaluate("document.querySelectorAll('.lg-modal').forEach(m=>m.hidden=true); var t=document.querySelector('#teach'); if(t) t.hidden=true")
    pg.click("#seq-btn"); pg.wait_for_selector(".sq-list li", timeout=60000)
    pg.fill("#seq-q", QUERY); time.sleep(1.5)
    pg.screenshot(path=f"{OUT}/00_pick.png")
    eq = pg.locator(".sq-eq", has=pg.locator(".sq-name", has_text=QUERY)).first
    eq.locator(f"button.sq-act[data-act={ACT}]").click(); time.sleep(0.5)
    if pg.locator(".sq-rows li").count():
        li = pg.locator(".sq-rows li", has_text=SHEET).first if SHEET else pg.locator(".sq-rows li").first
        li.click()
    log = []
    for i in range(1, 90):
        time.sleep(0.5)
        for _ in range(600):
            busy = pg.evaluate("SEQ.busy || (SEQ.cur && SEQ.cur.choice && SEQ.tries[SEQ.cur.choice.id]==='busy')")
            if not busy and pg.locator("#seq-b .sq-card, #seq-b .sq-result").count(): break
            time.sleep(0.25)
        time.sleep(0.6)
        view = pg.evaluate("SEQ.view")
        if view == "err":
            pg.screenshot(path=f"{OUT}/{i:02d}_err.png"); log.append((i, "err")); pg.click("#seq-b button[data-a=errgo]"); continue
        if view != "step":
            pg.screenshot(path=f"{OUT}/{i:02d}_{view}.png"); log.append((i, view, pg.inner_text("#seq-b")[:400])); break
        st = pg.evaluate("({g: !!SEQ.cur.gateStep, ch: !!SEQ.cur.choice, kind: SEQ.cur.node.kind||SEQ.cur.node.t, follow: !!document.querySelector('#seq-b button[data-a=follow]'), title: (document.querySelector('#seq-b .sq-q-t')||{}).innerText})")
        pg.screenshot(path=f"{OUT}/{i:02d}_step.png")
        log.append((i, st))
        if st["follow"] and pg.locator("#seq-b button[data-a=follow].pri").count(): pg.click("#seq-b button[data-a=follow]")
        elif st["g"] and st["ch"]:
            rec = pg.locator("#seq-b button[data-a=gpick].rec")
            (rec if rec.count() else pg.locator("#seq-b button[data-a=gpick]").first).click()
        elif st["g"]: pg.click("#seq-b button[data-a=gack]")
        elif pg.locator("#seq-b button[data-a=pick]").count():
            rec = pg.locator("#seq-b button[data-a=pick].rec"); (rec if rec.count() else pg.locator("#seq-b button[data-a=pick]").first).click()
        elif pg.locator("#seq-b .sq-btns button.pri").count(): pg.locator("#seq-b .sq-btns button.pri").first.click()
        elif pg.locator("#seq-b button[data-a=yes]").count(): pg.click("#seq-b button[data-a=yes]")
        else: pg.locator("#seq-b .sq-btns button").first.click()
    pg.screenshot(path=f"{OUT}/zz_final.png", full_page=False)
    json.dump({"log": log, "errors": errs}, open(f"{OUT}/log.json", "w"), ensure_ascii=False, indent=1)
    b.close()
print(json.dumps(log, ensure_ascii=False)[:3000]); print("ERR", errs)
