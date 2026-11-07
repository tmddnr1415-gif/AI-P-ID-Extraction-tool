"""L84 화면 자기검증 — Logic 작성: 휠로 장 넘기기 · 같은 묶음이면 확대 그대로 · 프로젝트 · 묶음 · 그림 지우기 · 가벼움(SVG 수).
python3 spike/ui_audit_l84.py <데이터 폴더(씨앗 묶음이 든 사본 — 지우기를 하므로 버릴 사본)> <캡처 폴더>
(브라우저를 못 찾으면 PW_CHROME=<chrome 경로>)"""
import json, os, sys, socket, subprocess, time, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data, out = sys.argv[1:3]
os.makedirs(out, exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=data, PYTHONPATH=ROOT, PID_PAGE_WARM="0", PID_LOGIC_WARM="0", PID_ROWS_WARM="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
B = f"http://127.0.0.1:{port}"; ok = []; bad = []
def chk(c, t): (ok if c else bad).append(t); print(("✔ " if c else "✕ ") + t)
def get(u): return json.loads(urllib.request.urlopen(B + u, timeout=120).read())
def post(u, b):
    r = urllib.request.Request(B + u, data=json.dumps(b).encode(), headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(r, timeout=300).read())
try:
    for _ in range(120):
        try: urllib.request.urlopen(B + "/version", timeout=2).read(); break
        except Exception: time.sleep(0.5)
    items = get("/logic/api/drawings")["items"]
    am = sorted([i for i in items if (i.get("set_name") or "").startswith("AMIRAL")], key=lambda i: i.get("order") or 0)
    chk(len(am) > 100, f"씨앗 묶음 {len(am)}장")
    byname = {i["name"]: i for i in am}
    chk(byname["0007"]["wires"] < 2000, f"0007 선 {byname['0007']['wires']} (묶기 전 3,549)")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        kw = {"executable_path": os.environ["PW_CHROME"]} if os.environ.get("PW_CHROME") else {}
        br = pw.chromium.launch(**kw); pg = br.new_page(viewport={"width": 1600, "height": 950}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        first = byname["0006"]
        pg.goto(f"{B}/logic/draw?user=t#d={first['id']}")
        pg.wait_for_function("() => S.doc && S.setInfo && document.querySelectorAll('#svg #wires > g').length > 0", timeout=120000)
        n = pg.evaluate("() => document.querySelectorAll('#svg *').length")
        chk(n < 4000, f"0006 SVG 요소 {n} (묶기 전 7,426)")
        order = pg.evaluate("() => S.setInfo.sheets.map(s => s.id)")
        i0 = order.index(first["id"])
        # 휠: 맞춤 확대(스크롤 없음)면 두 눈금이면 다음 장
        pg.mouse.move(900, 500)
        z0 = pg.evaluate("() => S.zoom")
        for _ in range(3):
            pg.mouse.wheel(0, 120); time.sleep(0.05)
        pg.wait_for_function(f"() => S.id === {order[i0 + 1]!r}", timeout=10000)
        chk(True, "휠을 아래로 → 다음 장")
        chk(abs(pg.evaluate("() => S.zoom") - z0) < 1e-6, "같은 묶음이면 확대 그대로")
        pg.screenshot(path=f"{out}/flip_next.png")
        time.sleep(0.6)
        for _ in range(3):
            pg.mouse.wheel(0, -120); time.sleep(0.05)
        pg.wait_for_function(f"() => S.id === {order[i0]!r}", timeout=10000)
        chk(True, "휠을 위로 → 앞 장")
        # 확대해서 스크롤이 생기면: 끝에 닿기 전에는 넘기지 않는다
        time.sleep(0.6)
        pg.evaluate("() => { setZoom(2.5); const sc = document.querySelector('#scroll'); sc.scrollTop = 0; }")
        pg.mouse.wheel(0, 240); time.sleep(0.4)
        chk(pg.evaluate(f"() => S.id") == order[i0], "확대한 장은 굴리면 먼저 그 장 안에서 내려간다")
        pg.evaluate("() => { const sc = document.querySelector('#scroll'); sc.scrollTop = sc.scrollHeight; }"); time.sleep(0.2)
        pg.mouse.wheel(0, 100); time.sleep(0.1)
        chk(pg.evaluate("() => document.querySelector('#fliphint') && document.querySelector('#fliphint').classList.contains('on')"), "끝에서 굴리면 '다음 장' 표시가 찬다")
        pg.screenshot(path=f"{out}/flip_hint.png")
        for _ in range(3):
            pg.mouse.wheel(0, 120); time.sleep(0.05)
        pg.wait_for_function(f"() => S.id === {order[i0 + 1]!r}", timeout=10000)
        chk(pg.evaluate("() => document.querySelector('#scroll').scrollTop") < 5, "다음 장은 맨 위부터")
        time.sleep(0.6)
        pg.evaluate("() => { const sc = document.querySelector('#scroll'); sc.scrollTop = 0; }"); time.sleep(0.2)
        for _ in range(3):
            pg.mouse.wheel(0, -120); time.sleep(0.05)
        pg.wait_for_function(f"() => S.id === {order[i0]!r}", timeout=10000)
        sc = pg.evaluate("() => { const sc = document.querySelector('#scroll'); return [sc.scrollTop, sc.scrollHeight - sc.clientHeight]; }")
        chk(sc[0] >= sc[1] - 5, "앞 장은 맨 아래부터 (이어 읽기)")
        # 첫 장에서 위로 → 넘기지 않음
        pg.evaluate(f"() => openDoc({order[0]!r})"); pg.wait_for_function(f"() => S.id === {order[0]!r}")
        pg.evaluate("() => { const sc = document.querySelector('#scroll'); sc.scrollTop = 0; }"); time.sleep(0.6)
        for _ in range(4):
            pg.mouse.wheel(0, -120); time.sleep(0.05)
        time.sleep(0.3)
        chk(pg.evaluate("() => S.id") == order[0], "첫 장에서 위로 굴려도 그대로 ('첫 장입니다')")
        # 장 목록 표시가 따라온다
        chk(pg.evaluate(f"() => document.querySelector('#set-list li.on').dataset.id") == order[0], "장 목록의 표시가 연 장으로 옮겨 간다")
        # 지우기 — 그림 하나 · 묶음 · 프로젝트
        loose = post("/logic/api/drawings", {"name": "지울 그림", "author": "t", "project": "AMIRAL"})
        pg.goto(f"{B}/logic/draw?user=t"); pg.wait_for_selector("#h-projects .hm-proj", timeout=60000)
        pg.evaluate("() => renderHome()"); time.sleep(0.5)
        pg.screenshot(path=f"{out}/home.png")
        pg.locator(f'#home [data-deldoc="{loose["id"]}"]').click(force=True)
        pg.fill("#m-who", "검증"); pg.click("#m-ok"); time.sleep(1.0)
        chk(not any(i["id"] == loose["id"] for i in get("/logic/api/drawings")["items"]), "그림 ✕ → 그 그림만 지워진다")
        proj = am[0].get("project") or ""
        pg.locator(f'#home [data-delproj="{proj}"]').first.click(force=True)
        pg.wait_for_selector("#m-purge", timeout=10000)
        pg.screenshot(path=f"{out}/purge_ask.png")
        pg.fill("#m-purge", "틀린 이름"); pg.click("#m-ok"); time.sleep(0.3)
        chk(not pg.locator("#modal").is_hidden(), "확인 이름이 틀리면 지우지 않는다")
        pg.fill("#m-purge", proj); pg.fill("#m-who", "검증"); pg.click("#m-ok")
        pg.wait_for_function(f"() => !(S.allItems || []).some(i => (i.project || '') === {proj!r} && i.set !== '7e7e00000063')", timeout=180000)
        left = [i for i in get("/logic/api/drawings")["items"] if (i.get("project") or "") == proj and i.get("set") != "7e7e00000063"]
        chk(not left, f"프로젝트 {proj} 삭제 → 그림 {len(am)}장이 지워진다 (남은 것 {len(left)})")
        chk(not any(p["name"] == proj for p in get("/logic/api/projects")["projects"]), "검토 분석이 없는 프로젝트는 이름도 목록에서 빠진다")
        pg.screenshot(path=f"{out}/home_after.png")
        chk(not errs, f"화면 오류 0 {errs[:3]}")
        br.close()
finally:
    srv.terminate()
print(f"\n통과 {len(ok)} · 실패 {len(bad)}")
