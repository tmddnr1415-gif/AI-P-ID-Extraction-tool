"""hotfix66 — 편집마다 이름을 묻지 않고 대시보드 로그인 이름으로 자동 기록 · 표시되는가 (눌러서 확인).

    python3 spike/ui_audit_login_author.py <data_dir 사본> <job> out/hotfix66/ui

A) 대시보드 안 (`?embed=1&user=홍길동`) · 이 브라우저에 기억된 이름 없음 → 이름 줄이 한 번도 안 뜬다 ·
   서버 이력 작성자 = 홍길동 · 목록 칸 툴팁 · 도면 라벨 `x7 ✎홍길동` · 머리 칩.
B) 대시보드 밖 · 이름 없음 → 첫 편집에서만 한 번 묻고 둘째부터는 안 묻는다.
★ 실 DB 를 열지 않는다 — 넘긴 데이터 폴더(사본)를 PID_DATA_DIR 로 가리킨다.
"""
from __future__ import annotations
import json, os, socket, subprocess, sys, time, urllib.request
from urllib.parse import quote
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data, JOB, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = f"http://127.0.0.1:{port}"
FOUND = []
def note(x): print(x, flush=True); FOUND.append(x)
def history(key):
    return json.loads(urllib.request.urlopen(f"{base}/jobs/{JOB}/rows/{quote(key)}/history").read())["history"]

def open_job(pg):
    pg.evaluate(f"open('{JOB}')")
    pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.pages && S.pages.length > 0", timeout=180000)
    pg.wait_for_timeout(2500)
    pg.evaluate("() => { if (S.side) toggleSide(); }"); pg.wait_for_timeout(500)

def edit_cell(pg, key, col, value):
    """목록 칸을 사람처럼 고친다 — 누르고 · 지우고 · 치고 · Enter.  이름 줄이 떴는지 돌려준다."""
    pg.evaluate(f"() => select('{key}', true)"); pg.wait_for_timeout(1200)
    td = pg.query_selector(f'#body tr[data-key="{key}"] td[data-col="{col}"]')
    td.scroll_into_view_if_needed(); td.click()
    pg.keyboard.press("Control+A"); pg.keyboard.type(value); pg.keyboard.press("Enter")
    try:
        pg.wait_for_selector(".author-bar", timeout=1500); return True
    except Exception:
        return False

try:
    for _ in range(90):
        try: urllib.request.urlopen(base + "/version", timeout=2); break
        except Exception: time.sleep(1)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        # ---------- A) 대시보드 안 ----------
        ctx = br.new_context(viewport={"width": 1920, "height": 1080}); pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
        pg.add_init_script("try{localStorage.removeItem('pid.author');localStorage.removeItem('pid.split')}catch(e){}")
        pg.goto(base + "/?embed=1&mode=epc&user=" + quote("홍길동")); pg.wait_for_timeout(1500)
        open_job(pg)
        chip = pg.inner_text("#who-chip"); chip_t = pg.get_attribute("#who-chip", "title")
        note(f"A① 머리 칩 '{chip}' · 툴팁 '{chip_t}'")
        key = pg.evaluate("() => { const r = S.rows.find(r => r.page_no === S.page.page_no && !r.removed && !r.deleted && r.values.type); return r.key; }")
        asked1 = edit_cell(pg, key, "qty", "7"); pg.wait_for_timeout(800)
        asked2 = edit_cell(pg, key, "line_no", "99LOGIN01"); pg.wait_for_timeout(800)
        note(f"A② 칸 두 번 고침 → 이름 줄 뜸 {asked1} / {asked2} (둘 다 False 여야)")
        h = history(key)
        note(f"A③ 서버 편집 이력 {[(x['field'], x['author'], x['to']) for x in h[:2]]}")
        td_t = pg.get_attribute(f'#body tr[data-key="{key}"] td[data-col="qty"]', "title") or ""
        note(f"A④ 목록 Q'ty 칸 툴팁 '{td_t.replace(chr(10), ' / ')}'")
        lab = pg.evaluate(f"() => {{ const g = document.querySelector('g.qtytag[data-key=\"{key}\"] text'); return g && g.textContent; }}")
        note(f"A⑤ 도면 라벨 '{lab}'")
        ev = pg.inner_text("#evidence") if pg.query_selector("#evidence") else ""
        note(f"A⑥ 근거 패널에 '홍길동 고침' 있음 {'홍길동 고침' in ev}")
        box = pg.query_selector(f'g.qtytag[data-key="{key}"]')
        if box:
            bb = box.bounding_box()
            pg.screenshot(path=str(OUT / "1_대시보드_라벨.png"),
                          clip={"x": max(0, bb["x"] - 260), "y": max(0, bb["y"] - 160), "width": 620, "height": 340})
        pg.screenshot(path=str(OUT / "2_대시보드_전체.png"))
        # 다시 열어도(새로 읽어도) 이름이 서버에서 온다
        pg.reload(); pg.wait_for_timeout(1500); open_job(pg)
        td_t2 = pg.get_attribute(f'#body tr[data-key="{key}"] td[data-col="line_no"]', "title") or ""
        note(f"A⑦ 새로 연 뒤 Line No. 칸 툴팁 '{td_t2.replace(chr(10), ' / ')}'")
        note(f"A 페이지 오류 {len(errs)} {errs[:3]}")
        ctx.close()
        # ---------- B) 대시보드 밖 · 이름 없음 ----------
        ctx = br.new_context(viewport={"width": 1920, "height": 1080}); pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "/"); pg.evaluate("() => { localStorage.removeItem('pid.author'); }")
        pg.reload(); pg.wait_for_timeout(1500); open_job(pg)
        key2 = pg.evaluate(f"() => S.rows.filter(r => r.page_no === S.page.page_no && !r.removed && !r.deleted && r.values.type && r.key !== '{key}')[0].key")
        asked = edit_cell(pg, key2, "line_no", "99DIRECT01")
        if asked:
            pg.screenshot(path=str(OUT / "3_직접열기_처음한번.png"))
            pg.fill(".author-bar input", "김철수"); pg.click(".author-bar button.ok"); pg.wait_for_timeout(1000)
        asked_b = edit_cell(pg, key2, "qty", "3"); pg.wait_for_timeout(800)
        h2 = history(key2)
        note(f"B① 첫 편집 이름 줄 {asked} · 둘째 편집 이름 줄 {asked_b} · 이력 {[(x['field'], x['author']) for x in h2[:2]]}")
        note(f"B 페이지 오류 {len(errs)} {errs[:3]}")
        br.close()
finally:
    srv.terminate()
(OUT / "audit.txt").write_text("\n".join(FOUND), encoding="utf-8")
