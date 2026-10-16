"""hotfix63 — 좌/우 경계를 끝까지 · 장별 메모(휠로 열기 · 저장 · 다른 Rev 에서 이력과 함께)를 눌러서 확인한다.

    python3 spike/ui_audit_memo.py <data_dir 사본> <Rev.B job> <Rev.A job> out/hotfix63/ui

★ 실 DB 를 열지 않는다 — 넘긴 데이터 폴더(사본)를 PID_DATA_DIR 로 가리킨다.
"""
from __future__ import annotations
import json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data, JOB_B, JOB_A, OUT = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
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
        pg.add_init_script("try{localStorage.setItem('pid.author','홍길동');if(!sessionStorage.getItem('x')){localStorage.removeItem('pid.split');localStorage.removeItem('pid.memo');sessionStorage.setItem('x','1')}}catch(e){}")
        def open_job(j):
            pg.goto(base + "/"); pg.wait_for_timeout(1500)
            pg.evaluate(f"open('{j}')")
            pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.pages && S.pages.length > 0", timeout=180000)
            pg.wait_for_timeout(2500)
        open_job(JOB_B)
        if pg.evaluate("() => !!S.side"):
            pg.click("#rev-switch button.side"); pg.wait_for_timeout(800)
        # ① 경계를 오른쪽 끝까지 · 왼쪽 끝까지
        gv = pg.query_selector("#gutter-v").bounding_box()
        sp = pg.query_selector("#split").bounding_box()
        def drag_to(x):
            pg.mouse.move(gv["x"] + 3, gv["y"] + 200); pg.mouse.down(); pg.mouse.move(x, gv["y"] + 200, steps=12); pg.mouse.up()
            pg.wait_for_timeout(500)
            return pg.evaluate("() => [Math.round(document.querySelector('#left').getBoundingClientRect().width), Math.round(document.querySelector('#right').getBoundingClientRect().width)]")
        w_right = drag_to(sp["x"] + sp["width"] - 1)
        pg.screenshot(path=str(OUT / "1_경계_오른쪽끝.png"))
        gv = pg.query_selector("#gutter-v").bounding_box()
        w_left = drag_to(sp["x"] + 1)
        pg.screenshot(path=str(OUT / "2_경계_왼쪽끝.png"))
        note(f"① 오른쪽 끝까지 → [도면 폭, 목록 폭] = {w_right} · 왼쪽 끝까지 → {w_left} (split {round(sp['width'])})")
        pg.dblclick("#gutter-v"); pg.wait_for_timeout(600)
        note("   두 번 누름 → " + str(pg.evaluate("() => [Math.round(document.querySelector('#left').getBoundingClientRect().width), Math.round(document.querySelector('#right').getBoundingClientRect().width)]")))
        # ② 휠로 메모 열기
        pg.evaluate("() => fit()"); pg.wait_for_timeout(400)
        folded0 = pg.evaluate("() => document.querySelector('#memo').classList.contains('folded')")
        st = pg.query_selector("#stage").bounding_box()
        pg.mouse.move(st["x"] + st["width"] / 2, st["y"] + st["height"] / 2)
        for _ in range(4):
            pg.mouse.wheel(0, 400); pg.wait_for_timeout(250)
        folded1 = pg.evaluate("() => document.querySelector('#memo').classList.contains('folded')")
        note(f"② 휠 아래로 → 메모 접힘 {folded0} → {folded1}")
        page_b = pg.evaluate("() => S.page.page_no"); dwg = pg.evaluate("() => S.page.drawing_no")
        pg.fill("#memo-text", "Rev.B 확인: PI 2개 발주처 회신 대기\n- 유닛 11/12 공통")
        pg.click("#memo-save"); pg.wait_for_timeout(600)
        ab = pg.query_selector(".author-bar")
        if ab: ab.query_selector("button.ok").click()
        pg.wait_for_timeout(1500)
        msg = pg.inner_text("#memo-msg")
        hist = pg.evaluate("() => (S.memoView && S.memoView.history || []).length")
        opt = pg.evaluate("() => document.querySelector('#page-select').selectedOptions[0].textContent")
        note(f"   p{page_b} {dwg} 저장 → '{msg}' · 이력 {hist}판 · 장 목록 '{opt}'")
        pg.screenshot(path=str(OUT / "3_RevB_메모저장.png"))
        # 두 번째 판
        pg.fill("#memo-text", "Rev.B 확인: PI 2개 발주처 회신 받음 (10/09)")
        pg.keyboard.press("Control+Enter"); pg.wait_for_timeout(500)
        ab = pg.query_selector(".author-bar")
        if ab: ab.query_selector("button.ok").click()
        pg.wait_for_timeout(1500)
        note(f"   두 번째 판 (Ctrl+Enter) → 이력 {pg.evaluate('() => S.memoView.history.length')}판")
        # ③ 같은 프로젝트의 Rev.A 에서 같은 도면번호 장
        open_job(JOB_A)
        pa = pg.evaluate(f"() => (S.pages.find(p => p.drawing_no === {json.dumps(dwg)}) || {{}}).page_no")
        if pa:
            pg.evaluate(f"() => showPage(S.pages.find(p => p.page_no === {pa}))"); pg.wait_for_timeout(2000)
        pg.evaluate("() => memoOpen(true)"); pg.wait_for_timeout(600)
        v = pg.evaluate("() => S.memoView && {n: S.memoView.history.length, cur: S.memoView.current && S.memoView.current.text, rev: S.memoView.current && S.memoView.current.revision}")
        other = pg.evaluate("() => document.querySelectorAll('#memo-list .memo-other').length")
        note(f"③ Rev.A p{pa} (같은 도면번호 {dwg}) → 이력 {v and v['n']}판 · 지금 메모 '{v and v['cur']}' ({v and v['rev']} 에서) · '다른 Rev 에서' 표식 {other}")
        pg.screenshot(path=str(OUT / "4_RevA_같은도면_메모.png"))
        pg.query_selector("#memo").screenshot(path=str(OUT / "5_메모판_확대.png"))
        note(f"페이지 오류 {len(errs)} {errs[:3]}")
        br.close()
finally:
    srv.terminate()
    (OUT / "audit.txt").write_text("\n".join(FOUND) + "\n", encoding="utf-8")
