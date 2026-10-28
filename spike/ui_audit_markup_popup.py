"""hotfix85 자기검증 — 마크업 사각형 뒤 팝업이 바로 뜨는가 · 제안이 나중에 채워지는가 · 적은 값은 안 덮는가 · 그동안 서버가 응답하는가.

사본 데이터(`PID_DATA_DIR`)로 띄운 서버 8766 · AL NOUF1 분석 · p6 에서 긋는다.  실 DB 를 열지 않는다.
    python3 spike/ui_audit_markup_popup.py out/hotfix85/ui
"""
import json, sys, time, threading, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
PORT = 8766; JOB = "0f7cde48ec7a"; OUT = Path(sys.argv[1]); OUT.mkdir(exist_ok=True)
notes = []
def note(s): print(s, flush=True); notes.append(s)

def ping_loop(stop, lat):
    while not stop.is_set():
        t = time.time()
        try: urllib.request.urlopen(f"http://127.0.0.1:{PORT}/version", timeout=10)
        except Exception as e: lat.append(("err", str(e)))
        else: lat.append(("ok", time.time() - t))
        time.sleep(0.2)

with sync_playwright() as p:
    br = p.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
    pg = br.new_page(viewport={"width": 1700, "height": 1000})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e) + " @ " + str(getattr(e, "stack", ""))[:400]))
    pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
    pg.goto(f"http://127.0.0.1:{PORT}/"); pg.wait_for_timeout(1500)
    pg.evaluate(f"() => open('{JOB}')"); pg.wait_for_timeout(6000)
    pg.select_option("#page-select", "6"); pg.wait_for_timeout(2500)
    n0 = pg.evaluate("() => (S.rows||[]).length")
    # 서버 캐시를 비운다 — 다른 장을 한 번 읽히면 p6 이 '처음 읽는 장' 이 된다
    pg.evaluate(f"""async () => {{ await fetch('/jobs/{JOB}/markup/propose', {{method:'POST',
        headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{page_no: 7, rect:[0,0,1,1]}})}}); }}""")
    pg.evaluate("() => { _prewarmed = null; }")
    stop = threading.Event(); lat = []
    th = threading.Thread(target=ping_loop, args=(stop, lat), daemon=True); th.start()
    pg.click("#markup-toggle")          # 미리 읽기가 시작된다 — 기다리지 않고 바로 긋는다
    st = pg.query_selector("#stage").bounding_box()
    opened = None
    for dx, dy in [(0.15, 0.15), (0.3, 0.2), (0.5, 0.5), (0.2, 0.6), (0.7, 0.3), (0.6, 0.7), (0.4, 0.35)]:
        x, y = st["x"] + st["width"] * dx, st["y"] + st["height"] * dy
        pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x + 30, y + 20, steps=4); pg.mouse.move(x + 60, y + 40, steps=4)
        t0 = time.time(); pg.mouse.up()
        try:
            pg.wait_for_selector("#mk-save", timeout=1500); opened = time.time() - t0; break
        except Exception:
            pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
    if opened is None:
        note("★ 빈 자리를 못 찾아 팝업이 안 떴다"); pg.screenshot(path=str(OUT / "fail.png")); raise SystemExit(2)
    pend0 = pg.evaluate("() => !!document.getElementById('mk-pending')")
    pg.screenshot(path=str(OUT / "1_팝업_바로.png"))
    # 제안이 오기 전에 사람이 적는다
    pg.fill("#mk-qty", "7"); pg.fill("#mk-tag", "ZZ-TEST")
    # 제안이 채워질 때까지
    t1 = time.time()
    try: pg.wait_for_selector("#mk-pending", state="detached", timeout=30000); filled = time.time() - t1
    except Exception: filled = None
    stop.set(); th.join(2)
    pg.screenshot(path=str(OUT / "2_제안_채워짐.png"))
    vals = pg.evaluate("""() => ({qty: document.getElementById('mk-qty').value, tag: document.getElementById('mk-tag').value,
        type: document.getElementById('mk-type').value, scope: document.getElementById('mk-scope').value,
        system: document.getElementById('mk-system').value, head: document.getElementById('mk-head').textContent,
        qsrc: document.getElementById('mk-qty-src').textContent, ssrc: document.getElementById('mk-scope-src').textContent})""")
    oks = [v for k, v in lat if k == "ok"]; bad = [v for k, v in lat if k != "ok"]
    note(f"팝업까지 {opened*1000:.0f}ms · 읽는 중 표시 {pend0} · 제안 채워짐 {None if filled is None else f'{filled:.2f}초'}")
    note(f"적은 값 보존: qty={vals['qty']} tag={vals['tag']} · 제안이 채운 칸: type={vals['type']!r} system={vals['system']!r} scope={vals['scope']!r}")
    note(f"근거 줄: {vals['head'][:80]} / qty: {vals['qsrc'][:60]} / scope: {vals['ssrc'][:60]}")
    note(f"읽는 동안 /version {len(oks)}번 · 최대 {max(oks)*1000:.0f}ms · 실패 {len(bad)}")
    # 저장
    pg.fill("#mk-author", "홍길동")
    pg.evaluate("() => { const c = document.getElementById('mk-voc'); if (c) c.checked = false; }")
    pg.click("#mk-save"); pg.wait_for_timeout(2500)
    n1 = pg.evaluate("() => (S.rows||[]).length")
    last = pg.evaluate("""() => { const r = (S.rows||[]).filter(r => r.page_no === 6 && (r.values.tag_no||'') === 'ZZ-TEST')[0];
        return r ? {qty: r.values.qty, tag: r.values.tag_no, mk: (r.evidence && r.evidence.markup) ? {qs: r.evidence.markup.qty_source, ss: r.evidence.markup.scope_source, prop: !!r.evidence.markup.proposal} : null} : null; }""")
    note(f"저장: 행 {n0} → {n1} · 새 행 {json.dumps(last, ensure_ascii=False)}")
    note(f"페이지 오류 {len(errs)} " + "\n".join(errs))
    pg.screenshot(path=str(OUT / "3_저장뒤.png"))
    br.close()
(OUT / "result.txt").write_text("\n".join(notes), encoding="utf-8")
