"""L79 화면 자기검증 — Logic 작성 첫 화면 · Typical 팔레트(기호) · 누르면 놓기 · 두 번 누르면 내부(새 창) · 신호 처리 메뉴.
python3 spike/ui_audit_l79.py <빈 데이터 폴더> <캡처 폴더>   (사본 데이터 — 실 DB 를 안 연다)"""
import os, sys, socket, subprocess, time, urllib.request, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data, out = sys.argv[1], sys.argv[2]
shutil.rmtree(data, ignore_errors=True); os.makedirs(data); os.makedirs(out, exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=data, PYTHONPATH=ROOT, PID_PAGE_WARM="0", PID_LOGIC_WARM="0", PID_ROWS_WARM="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
B = f"http://127.0.0.1:{port}"; ok = []; bad = []
def chk(c, t): (ok if c else bad).append(t); print(("✔ " if c else "✕ ") + t)
def shot(pg, name, **k): pg.screenshot(path=f"{out}/{name}.png", **k)
try:
    for _ in range(120):
        try: urllib.request.urlopen(B + "/version", timeout=2).read(); break
        except Exception: time.sleep(0.5)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(); ctx = br.new_context(viewport={"width": 1700, "height": 980}); pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(B + "/logic/draw?user=홍길동")
        pg.wait_for_function("() => !document.querySelector('#home').hidden && document.querySelectorAll('#h-projects .hm-proj').length > 0", timeout=120000)
        time.sleep(1); shot(pg, "1_첫화면")
        chk(pg.evaluate("() => document.body.classList.contains('dw-homeon') && getComputedStyle(document.querySelector('.dw-side')).display==='none'"), "첫 화면 — 그리기 칸은 숨김")
        chk(pg.evaluate("() => document.querySelector('#h-projects').innerText.includes('AMIRAL')"), "저장된 프로젝트에 AMIRAL")
        chk(pg.evaluate("() => document.querySelectorAll('#h-recent li').length > 0"), "최근 그린 그림")
        chk(pg.evaluate("() => document.querySelector('[data-act=signal]').getAttribute('href').startsWith('/logic/signal')"), "시작하기 — 신호 처리 시뮬레이션")
        # 새 그림 (프로젝트 없이)
        pg.click("[data-act=new]"); pg.wait_for_selector("#m-name"); pg.fill("#m-name", "L79 시험"); pg.fill("#m-sheet", "T79_G001"); pg.click("#m-ok")
        pg.wait_for_function("() => S.doc && S.doc.sheet_no==='T79_G001'", timeout=30000); time.sleep(1)
        chk(pg.evaluate("() => !document.body.classList.contains('dw-homeon')"), "새 그림 — 첫 화면이 닫힘")
        pg.wait_for_function("() => document.querySelectorAll('#macro-list .mtile').length > 0", timeout=30000)
        n = pg.evaluate("() => document.querySelectorAll('#macro-list .mtile').length")
        grp = pg.evaluate("() => [...document.querySelectorAll('#macro-list .mg h4')].map(h=>h.innerText)")
        chk(n > 0 and "19VA" in " ".join(grp), f"묶음 없는 그림에도 Typical 팔레트 (보이는 타일 {n} · {grp})")
        card = pg.evaluate("() => { const r=document.querySelector('#macro-card').getBoundingClientRect(); return [r.x,r.y,r.width,r.height]; }")
        pg.evaluate("() => document.querySelector('#macro-card').scrollIntoView()"); time.sleep(0.4)
        card = pg.evaluate("() => { const r=document.querySelector('#macro-card').getBoundingClientRect(); return [r.x,r.y,r.width,Math.min(r.height,900)]; }")
        shot(pg, "2_Typical_팔레트", clip={"x": card[0], "y": max(0, card[1]), "width": card[2], "height": card[3]})
        # 누르면 놓기
        pg.fill("#macro-q", "MOV"); time.sleep(0.3)
        pg.click("#macro-list .mtile"); time.sleep(0.8)
        chk(pg.evaluate("() => S.doc.blocks.some(b=>b.kind==='MACRO')"), "타일 누름 → 그림에 매크로")
        pg.fill("#macro-q", ""); time.sleep(0.3)
        shot(pg, "3_매크로_놓음")
        # 그림의 매크로 두 번 누름 → 새 창 (내부 동작)
        with ctx.expect_page() as pi:
            pg.evaluate("() => { const b=S.doc.blocks.find(b=>b.kind==='MACRO'); const g=document.querySelector(`.blk[data-id='${b.id}']`); g.querySelector('rect').dispatchEvent(new MouseEvent('dblclick',{bubbles:true})); }")
        w = pi.value; w.set_viewport_size({"width": 1700, "height": 980}); w.on("pageerror", lambda e: errs.append("새창 " + str(e)))
        w.wait_for_function("() => typeof S!=='undefined' && S.doc && S.doc.blocks.length>0", timeout=60000); time.sleep(1.5)
        info = w.evaluate("() => [S.doc.set_name, S.doc.sheet_no, S.doc.title, S.doc.blocks.length, !document.querySelector('#typ-card').hidden]")
        chk(info[3] > 0 and info[4], f"두 번 누름 → 새 창에 내부 동작 (고칠 수 있음 · 사전 저장 카드) {info}")
        w.screenshot(path=f"{out}/4_매크로_내부동작_새창.png")
        # 고쳐 저장 가능
        w.evaluate("() => { const b=S.doc.blocks[0]; b.x+=5.65; markDirty(); render(); }"); w.click("#save"); time.sleep(1.5)
        chk(w.evaluate("() => !S.dirty && S.doc.saves>=1"), "내부 그림 고쳐 저장")
        w.close()
        # 팔레트 타일 두 번 누름 → 새 창
        with ctx.expect_page() as pi:
            pg.dblclick("#macro-list .mg:not(.shut) .mtile >> nth=1")
        w2 = pi.value; w2.wait_for_function("() => typeof S!=='undefined' && S.doc && S.doc.blocks.length>0", timeout=60000)
        chk(True, f"팔레트 타일 두 번 누름 → 새 창 {w2.evaluate('() => S.doc.title')}")
        chk(pg.evaluate("() => S.doc.blocks.filter(b=>b.kind==='MACRO').length") == 1, "두 번 누름은 그림에 놓지 않음")
        w2.close()
        # 첫 화면으로 · 신호 처리 링크
        pg.click("#save"); time.sleep(1)
        pg.click("#home-btn"); pg.wait_for_function("() => !document.querySelector('#home').hidden", timeout=20000); time.sleep(1)
        chk(pg.evaluate("() => document.querySelector('#h-recent').innerText.includes('T79_G001')"), "첫 화면 — 최근 그림에 방금 그림")
        shot(pg, "5_첫화면_다시")
        pg.click("#sig-link"); pg.wait_for_load_state(); time.sleep(1.5)
        chk("/logic/signal" in pg.url and "user=" in pg.url, f"머리줄 ∿ 신호 처리 → {pg.url}")
        shot(pg, "6_신호처리")
        pg.click("text=✎ Logic 작성"); pg.wait_for_function("() => typeof S!=='undefined' && !document.querySelector('#home').hidden", timeout=60000)
        chk(True, "신호 처리 → ✎ Logic 작성 → 첫 화면")
        # P&ID 화면 왼쪽 메뉴
        pg.goto(B + "/"); time.sleep(2)
        chk(pg.evaluate("() => !!document.querySelector('#nav-logic-signal')"), "P&ID 화면 왼쪽 메뉴 — 신호 처리 시뮬레이션")
        chk(not errs, f"화면 오류 0 {errs[:3]}")
        br.close()
finally:
    srv.terminate()
print(f"\n통과 {len(ok)} · 실패 {len(bad)}")
