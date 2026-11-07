"""L82 화면 자기검증 — Logic 작성: 신호 처리 블록 두 번 누름 → 입력 넣기 → 식 · 값 넣은 식 · 출력.
python3 spike/ui_audit_l82.py <데이터 폴더(그림 있는 사본)> <캡처 폴더> <그림 id> <블록 id> <값1,값2,…> <기대 출력>"""
import os, sys, socket, subprocess, time, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data, out, did, bid, vals, want = sys.argv[1:7]
os.makedirs(out, exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=data, PYTHONPATH=ROOT, PID_PAGE_WARM="0", PID_LOGIC_WARM="0", PID_ROWS_WARM="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
B = f"http://127.0.0.1:{port}"; ok = []; bad = []
def chk(c, t): (ok if c else bad).append(t); print(("✔ " if c else "✕ ") + t)
try:
    for _ in range(120):
        try: urllib.request.urlopen(B + "/version", timeout=2).read(); break
        except Exception: time.sleep(0.5)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 1600, "height": 950}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"{B}/logic/draw?user=t#d={did}")
        pg.wait_for_selector(f'#svg .blk[data-id="{bid}"]', timeout=120000)
        pg.locator(f'#svg .blk[data-id="{bid}"]').first.dblclick(force=True)
        pg.wait_for_selector("#aoppanel #ap-res .ap-l", timeout=30000)
        chk(True, "두 번 누름 → 계산 판이 열린다")
        n = pg.locator("#aoppanel [data-in]").count()
        vs = vals.split(",")
        chk(n == len(vs), f"입력 칸 {n}개 (기대 {len(vs)})")
        for k, v in enumerate(vs[:n]):
            pg.locator(f'#aoppanel [data-in="{k}"]').fill(v)
        pg.wait_for_function(f"() => (document.querySelector('#aoppanel .ap-l.out b')||{{}}).textContent === {want!r}", timeout=10000)
        txt = pg.locator("#ap-res").inner_text()
        chk(True, f"출력 = {want}  ({' | '.join(txt.splitlines())})")
        pg.screenshot(path=f"{out}/aop_{bid}.png")
        pg.keyboard.press("Escape"); time.sleep(0.2)
        chk(pg.locator("#aoppanel").count() == 0, "Esc 로 닫힌다")
        chk(not errs, f"화면 오류 0 {errs[:3]}")
        br.close()
finally:
    srv.terminate()
print(f"\n통과 {len(ok)} · 실패 {len(bad)}")
