"""L65 — LOGIC 작도 가볍게: 사용자가 하는 일을 되풀이해 잰다 (크롬 · 사본 데이터).

  python3 spike/draw_perf.py <데이터 폴더(사본)> <job id (분석한 묶음 · 들여올 것) | -> <출력 json> [--root <다른 코드 뿌리>]

열기 · 장 넘기기 · render() · 끌기(포인터 30번) · 칸 고치기 · 저장 · 시뮬레이션 켜기 · 신호 주기 · 묶음 정보 · 서버 응답을 잰다.
"""
from __future__ import annotations

import json, os, socket, statistics, subprocess, sys, time, urllib.request
from pathlib import Path

args = sys.argv[1:]
root = Path(__file__).resolve().parent.parent
if "--root" in args:
    i = args.index("--root"); root = Path(args[i + 1]).resolve(); del args[i:i + 2]
data, job, outp = Path(args[0]).resolve(), args[1], Path(args[2])
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(root), PID_PAGE_WARM="0", PID_LOGIC_WARM="0", PID_ROWS_WARM="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(root), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = f"http://127.0.0.1:{port}"; R = {}
def J(u, b=None, m=None):
    rq = urllib.request.Request(base + u, data=json.dumps(b).encode() if b is not None else None, headers={"Content-Type": "application/json"}, method=m or ("POST" if b is not None else "GET"))
    return json.loads(urllib.request.urlopen(rq, timeout=600).read())
med = lambda xs: round(statistics.median(xs), 1) if xs else None
try:
    for _ in range(120):
        try: urllib.request.urlopen(base + "/version", timeout=2).read(); break
        except Exception: time.sleep(0.5)
    sets = J("/logic/api/drawings/sets")["items"]
    if job != "-" and not sets:
        t = time.time(); J("/logic/api/drawings/sets/import", {"job": job, "author": "perf"}); R["import_s"] = round(time.time() - t, 2)
        sets = J("/logic/api/drawings/sets")["items"]
    st = max(sets, key=lambda x: len(x["sheets"]))
    ids = [q["id"] for q in sorted(st["sheets"], key=lambda q: q.get("order") or 0) if not q.get("typical")]
    R["sheets"] = len(st["sheets"])
    # 서버 응답 (화면 없이)
    tm = []
    for d in ids[:6]:
        t = time.time(); J(f"/logic/api/drawings/{d}"); tm.append((time.time() - t) * 1000)
    R["srv_get_drawing_ms"] = med(tm)
    t = time.time(); J(f"/logic/api/drawings/sets/{st['id']}"); R["srv_set_ms"] = round((time.time() - t) * 1000)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        pg = br.new_page(viewport={"width": 1600, "height": 950}); errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.add_init_script("try { localStorage.setItem('pid.author', 'perf'); } catch (e) {}")
        t = time.time(); pg.goto(f"{base}/logic/draw#d={ids[0]}")
        pg.wait_for_function("typeof S !== 'undefined' && S.doc && S.setInfo", timeout=120000); R["open_ms"] = round((time.time() - t) * 1000)
        pg.fill("#who", "perf")
        nav = []
        for d in ids[1:7]:
            t = time.time(); pg.evaluate(f"openDoc('{d}')"); pg.wait_for_function(f"() => S.id === '{d}' && S.setInfo", timeout=60000); nav.append((time.time() - t) * 1000)
        R["switch_sheet_ms"] = med(nav)
        big = max(ids, key=lambda d: next(q["blocks"] + q["wires"] for q in st["sheets"] if q["id"] == d))
        pg.evaluate(f"openDoc('{big}')"); pg.wait_for_function(f"() => S.id === '{big}'", timeout=60000); time.sleep(0.5)
        R["big_sheet"] = pg.evaluate("[S.doc.sheet_no, S.doc.blocks.length, S.doc.wires.length]")
        R["render_ms"] = pg.evaluate("() => { const ts = []; for (let i = 0; i < 12; i++) { const t = performance.now(); render(); ts.push(performance.now() - t); } ts.sort((a, b) => a - b); return +ts[6].toFixed(1); }")
        R["svg_nodes"] = pg.evaluate("document.querySelectorAll('#svg *').length")
        # 끌기 — 첫 블록을 30걸음
        bb = pg.locator("#svg .blk").first.bounding_box()
        x, y = bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2
        pg.evaluate("() => { window._lt = []; window._po = new PerformanceObserver(l => { for (const e of l.getEntries()) window._lt.push(e.duration); }); window._po.observe({entryTypes: ['longtask']}); }")
        pg.mouse.move(x, y); pg.mouse.down(); t = time.time()
        for k in range(30):
            pg.mouse.move(x + k * 3, y + (k % 5))
        pg.mouse.up(); R["drag30_ms"] = round((time.time() - t) * 1000)
        R["drag_longtasks"] = pg.evaluate("window._lt.length")
        pg.keyboard.press("Control+z"); time.sleep(0.2)
        # 칸 고치기 + 저장
        t = time.time(); pg.evaluate("() => { const r = S.doc.left['1'] || (S.doc.left['1'] = {}); r.desc = 'PERF ' + Date.now(); markDirty(); render(); }"); R["edit_ms"] = round((time.time() - t) * 1000)
        t = time.time(); pg.click("#save"); pg.wait_for_function("() => !S.dirty", timeout=60000); R["save_ms"] = round((time.time() - t) * 1000)
        # 시뮬레이션
        t = time.time(); pg.click("#simtoggle"); pg.wait_for_function("() => S.sim && S.sim.res", timeout=120000); R["sim_on_ms"] = round((time.time() - t) * 1000)
        rows = pg.evaluate("() => Object.keys(S.doc.left).slice(0, 6)")
        tf = []
        for r in rows:
            pg.evaluate("() => { window._r = S.sim.res; }"); t = time.time()
            pg.evaluate(f"setForce(S.id, 'row:{r}', 1)"); pg.wait_for_function("() => S.sim.res !== window._r", timeout=60000); tf.append((time.time() - t) * 1000)
        R["sim_force_ms"] = med(tf)
        R["errors"] = errors[:3]
        br.close()
finally:
    srv.terminate()
outp.parent.mkdir(parents=True, exist_ok=True); outp.write_text(json.dumps(R, ensure_ascii=False, indent=1)); print(json.dumps(R, ensure_ascii=False))
