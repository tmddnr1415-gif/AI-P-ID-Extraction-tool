"""hotfix64 — 도면 전체화면에서 상자를 눌러 고치면 목록에 저절로 반영되는가 (눌러서 확인).

    python3 spike/ui_audit_fullscreen.py <data_dir 사본> <job> out/hotfix64/ui

★ 실 DB 를 열지 않는다 — 넘긴 데이터 폴더(사본)를 PID_DATA_DIR 로 가리킨다.
"""
from __future__ import annotations
import json, os, socket, subprocess, sys, time, urllib.request
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
try:
    for _ in range(90):
        try: urllib.request.urlopen(base + "/version", timeout=2); break
        except Exception: time.sleep(1)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        pg = br.new_page(viewport={"width": 1920, "height": 1080}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
        pg.add_init_script("try{localStorage.setItem('pid.author','홍길동');if(!sessionStorage.getItem('x')){localStorage.removeItem('pid.split');sessionStorage.setItem('x','1')}}catch(e){}")
        pg.goto(base + "/"); pg.wait_for_timeout(1500)
        pg.evaluate(f"open('{JOB}')")
        pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.pages && S.pages.length > 0", timeout=180000)
        pg.wait_for_timeout(2500)
        pg.evaluate("() => { if (S.side) toggleSide(); }"); pg.wait_for_timeout(600)

        def ok_author():
            ab = pg.query_selector(".author-bar")
            if ab and ab.is_visible(): ab.query_selector("button.ok").click()
            pg.wait_for_timeout(1200)

        # ① 전체화면
        pg.click("#full-toggle"); pg.wait_for_timeout(1200)
        lw = pg.evaluate("() => [Math.round(document.querySelector('#left').getBoundingClientRect().width), Math.round(document.querySelector('#left').getBoundingClientRect().height)]")
        note(f"① 전체화면 → 도면 창 {lw} (화면 1920×1080)")
        pg.evaluate("() => fit()"); pg.wait_for_timeout(500)
        key = pg.evaluate("() => { const r = S.rows.find(r => r.page_no === S.page.page_no && !r.removed && !r.deleted && r.values.type); return r && r.key; }")
        box = pg.query_selector(f'rect.det[data-key="{key}"]')
        box.click(force=True); pg.wait_for_timeout(900)
        vis = pg.evaluate("() => !document.querySelector('#fedit').classList.contains('hidden')")
        head = pg.inner_text("#fedit .fe-head") if vis else ""
        note(f"② 상자 누름 → 편집 카드 보임 {vis} · '{head.splitlines()[0] if head else ''}'")
        pg.screenshot(path=str(OUT / "1_전체화면_편집카드.png"))
        before = pg.evaluate(f"() => {{ const r = S.rowByKey ? S.rowByKey['{key}'] : S.rows.find(x => x.key === '{key}'); return [r.values.qty, r.values.line_no || ''] }}")
        # ③ Q'ty · Line No. 고치기
        pg.fill('#fedit input[data-f="qty"]', "7"); pg.keyboard.press("Enter"); ok_author()
        pg.fill('#fedit input[data-f="line_no"]', "99TEST01"); pg.keyboard.press("Enter"); ok_author()
        st = pg.evaluate(f"""() => {{
          const tr = document.querySelector('#body tr[data-key="{key}"]');
          const q = tr && tr.querySelector('td[data-col="qty"]'), l = tr && tr.querySelector('td[data-col="line_no"]');
          const r = S.rows.find(x => x.key === '{key}');
          const lab = document.querySelector('g.qtytag[data-key="{key}"]');
          return {{ grid_qty: q && q.textContent, grid_qty_edited: q && q.classList.contains('edited'),
                   grid_line: l && l.textContent, user: r.user, label: lab && lab.textContent }}; }}""")
        note(f"③ 카드에서 Q'ty {before[0]}→7 · Line No. '{before[1]}'→99TEST01 → 목록 칸 Q'ty '{st['grid_qty']}' (✎ {st['grid_qty_edited']}) · "
             f"목록 칸 Line No. '{st['grid_line']}' · 행 user {st['user']} · 도면 라벨 '{st['label']}'")
        srv_row = json.loads(urllib.request.urlopen(f"{base}/jobs/{JOB}/rows?tab=ALL").read())
        srv_row = next(r for r in srv_row if r["key"] == key)
        note(f"   서버 user = {srv_row.get('user')}")
        pg.screenshot(path=str(OUT / "2_전체화면_저장뒤.png"))
        # ④ ▶ 다음 항목
        pg.click('#fedit [data-nav="1"]'); pg.wait_for_timeout(1200)
        k2 = pg.evaluate("() => S.sel"); note(f"④ ▶ → 다음 항목으로 (선택 {k2 != key})")
        # ⑤ Esc 두 번 → 선택 풀고 전체화면 나감 → 목록에 같은 값
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300); pg.keyboard.press("Escape"); pg.wait_for_timeout(1000)
        full = pg.evaluate("() => document.body.classList.contains('pid-full')")
        pg.evaluate(f"() => select('{key}', true)"); pg.wait_for_timeout(1500)
        g = pg.evaluate(f"() => {{ const tr = document.querySelector('#body tr[data-key=\"{key}\"]'); return tr && [tr.querySelector('td[data-col=\"qty\"]').textContent, tr.querySelector('td[data-col=\"line_no\"]').textContent]; }}")
        cardvis = pg.evaluate("() => !document.querySelector('#fedit').classList.contains('hidden')")
        note(f"⑤ Esc 두 번 → 전체화면 {full} · 목록 그 행 [Q'ty, Line No.] = {g} · 목록이 보이니 편집 카드 {cardvis}")
        pg.screenshot(path=str(OUT / "3_전체화면끝_목록반영.png"))
        # ⑥ 경계를 끝까지 밀어 목록을 접은 경우
        gv = pg.query_selector("#gutter-v").bounding_box(); sp = pg.query_selector("#split").bounding_box()
        pg.mouse.move(gv["x"] + 3, gv["y"] + 200); pg.mouse.down(); pg.mouse.move(sp["x"] + sp["width"] - 1, gv["y"] + 200, steps=10); pg.mouse.up()
        pg.wait_for_timeout(800)
        pg.evaluate(f"() => select('{key}', true)"); pg.wait_for_timeout(1200)
        cardvis2 = pg.evaluate("() => !document.querySelector('#fedit').classList.contains('hidden')")
        note(f"⑥ 목록을 끝까지 접음 → 편집 카드 {cardvis2}")
        pg.screenshot(path=str(OUT / "4_목록접음_편집카드.png"))
        note(f"페이지 오류 {len(errs)} {errs[:3]}")
        br.close()
finally:
    srv.terminate()
    (OUT / "audit.txt").write_text("\n".join(FOUND) + "\n", encoding="utf-8")
