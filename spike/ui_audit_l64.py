"""L64 — FROM/TO 값을 누르면 '이동 / 새 창' 메뉴 · 새 창도 시뮬레이션 값이 같이 가는지 (크롬 · 사본 데이터).

  python3 spike/ui_audit_l64.py <알다프라 그림 묶음이 든 데이터 폴더(사본)> <출력 폴더>
"""
from __future__ import annotations

import json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = Path(sys.argv[1]).resolve(); OUT = Path(sys.argv[2]).resolve(); OUT.mkdir(parents=True, exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT), PID_PAGE_WARM="0", PID_LOGIC_WARM="0", PID_ROWS_WARM="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = f"http://127.0.0.1:{port}"; LOG = []
def note(x): print(x, flush=True); LOG.append(x)
try:
    for _ in range(120):
        try: urllib.request.urlopen(base + "/version", timeout=2).read(); break
        except Exception: time.sleep(0.5)
    st = json.loads(urllib.request.urlopen(base + "/logic/api/drawings/sets").read())["items"][0]
    sheets = {q["sheet_no"]: q["id"] for q in st["sheets"]}
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        ctx = br.new_context(viewport={"width": 1500, "height": 950}); errors = []
        ctx.add_init_script("try { localStorage.setItem('pid.author', '홍길동'); } catch (e) {}")
        pg = ctx.new_page()
        for p in (pg,):
            p.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(f"{base}/logic/draw#d={sheets['FG_G-101']}")
        pg.wait_for_function("typeof S !== 'undefined' && S.doc && S.setInfo", timeout=30000); time.sleep(0.8)
        sel = "#svg .lnkbadge.golink[data-side='right']:not(.st-miss)"
        n = pg.locator(sel).count(); note(f"FG_G-101 오른쪽 연결 표기 {n}개")
        badge = pg.locator(sel).first; row = badge.get_attribute("data-n")
        badge.scroll_into_view_if_needed(); badge.click(); time.sleep(0.3)
        menu = pg.locator("#simmenu").inner_text(); note(f"TO {row}행을 누름 → 메뉴: {menu.replace(chr(10), ' / ')}")
        pg.screenshot(path=str(OUT / "1_menu.png"))
        t0 = time.time(); pg.locator("#simmenu button", has_text="이동").first.click()
        pg.wait_for_function(f"() => S.doc && S.doc.sheet_no !== 'FG_G-101'", timeout=20000)
        note(f"이동 → {pg.evaluate('S.doc.sheet_no')} ({time.time() - t0:.2f}초)"); time.sleep(0.4)
        pg.screenshot(path=str(OUT / "2_moved.png"))
        target = pg.evaluate("S.doc.sheet_no")
        pg.locator("#set-list li", has_text="FG_G-101").first.click()
        pg.wait_for_function("() => S.doc && S.doc.sheet_no === 'FG_G-101'", timeout=20000); time.sleep(0.6)
        pg.click("#simtoggle"); pg.wait_for_function("() => S.sim && S.sim.res", timeout=30000); time.sleep(0.5)
        badge = pg.locator(sel).first; badge.scroll_into_view_if_needed(); badge.click(); time.sleep(0.3)
        with ctx.expect_page() as pi:
            t0 = time.time(); pg.locator("#simmenu button", has_text="새 창").first.click()
        cp = pi.value; cp.on("pageerror", lambda e: errors.append("새 창: " + str(e)))
        cp.wait_for_function("() => typeof S !== 'undefined' && S.doc && S.sim && S.sim.on && S.sim.res", timeout=30000)
        note(f"새 창 → {cp.evaluate('S.doc.sheet_no')} · 시뮬레이션 켜짐 ({time.time() - t0:.2f}초)")
        # 큰 창에서 입력 행 전부를 1 로 → 새 창 값이 따라 바뀌는가
        ones = lambda p: p.evaluate("() => Object.values(S.sim.values || {}).filter(v => v === 1).length")
        before = ones(cp); cp.evaluate("() => { window._r = S.sim.res; }")
        t0 = time.time()
        pg.evaluate("r => setForce(S.id, 'row:' + r, 1)", row)       # 79행(TO FG_G-102-17) 출력을 1 로 — 조건을 채워 켠다
        cp.wait_for_function("() => S.sim.res !== window._r", timeout=20000); time.sleep(0.3)
        lin = cp.evaluate("() => JSON.stringify((S.sim.res.linked || {})[S.id] || {})")
        note(f"FG_G-101 {row}행 출력을 1 로 → 새 창이 다시 돎 ({time.time() - t0:.2f}초) · 새 창 1 인 선 {before} → {ones(cp)} · 새 창이 받은 연결 {lin}")
        norm = "() => JSON.stringify(Object.entries(S.sim.forces).filter(([k, v]) => Object.keys(v).length).map(([k, v]) => [k, Object.entries(v).sort()]).sort())"
        same = cp.evaluate(norm) == pg.evaluate(norm)
        note(f"두 창의 준 신호가 같음 {same}")
        pg.screenshot(path=str(OUT / "3_main_sim.png")); cp.screenshot(path=str(OUT / "4_child_sim.png"))
        # 새 창에서 신호 하나를 준다 → 큰 창에도
        t0 = time.time()
        cp.evaluate("() => { const r = Object.keys(S.doc.left).find(k => (S.doc.left[k].desc || '').trim()); setForce(S.id, 'row:' + r, 1); }")
        cdid = cp.evaluate("S.id")
        pg.wait_for_function(f"() => S.sim.forces['{cdid}'] && Object.keys(S.sim.forces['{cdid}']).length", timeout=20000)
        cp.wait_for_function(f"() => S.sim.forces['{cdid}'] && Object.keys(S.sim.forces['{cdid}']).length", timeout=20000)
        note(f"새 창에서 신호 → 큰 창에 올라가고 다시 내려옴 ({time.time() - t0:.2f}초)")
        pg.click("#simtoggle"); cp.wait_for_function("() => !S.sim.on", timeout=10000)
        note("큰 창에서 시뮬레이션 끔 → 새 창도 꺼짐")
        note(f"페이지 오류 {len(errors)} {errors[:3]}")
        br.close()
finally:
    srv.terminate(); (OUT / "result.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
