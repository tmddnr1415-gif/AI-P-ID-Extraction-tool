"""hotfix68 — 도면 · 목록을 새 창으로 띄워 두 창이 서로 따라가는가 (눌러서 확인).

    python3 spike/ui_audit_dualpane.py <data_dir 사본> <job> out/hotfix68/ui

★ 실 DB 를 열지 않는다 — 넘긴 데이터 폴더(사본)를 PID_DATA_DIR 로 가리킨다.
대시보드처럼 `?embed=1&user=홍길동` 으로 연다 (이름은 묻지 않는다 — hotfix66).
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
FOUND, BAD = [], []
def note(x, ok=True):
    print(("  " if ok else "✗ ") + x, flush=True); FOUND.append(("" if ok else "✗ ") + x)
    if not ok: BAD.append(x)
def srow(key):
    return json.loads(urllib.request.urlopen(f"{base}/jobs/{JOB}/rows?tab=ALL&keys={quote(key)}").read())[0]
READY = "() => typeof S !== 'undefined' && S.job && !S.loading && S.rows && S.rows.length > 0 && document.querySelector('#body tr')"

try:
    for _ in range(90):
        try: urllib.request.urlopen(base + "/version", timeout=2); break
        except Exception: time.sleep(1)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        ctx = br.new_context(viewport={"width": 1600, "height": 950})
        errs = []
        def watch(pg, name):
            pg.on("pageerror", lambda e: errs.append(f"{name}: {e}"))
            pg.on("console", lambda m: errs.append(f"{name} console: {m.text}") if m.type == "error" else None)
        ctx.add_init_script("try{localStorage.removeItem('pid.split');localStorage.setItem('pid.side.off','1')}catch(e){}")
        main = ctx.new_page(); watch(main, "본 창")
        main.goto(f"{base}/?embed=1&user={quote('홍길동')}#{JOB}")
        main.wait_for_function(READY, timeout=180000); main.wait_for_timeout(1500)
        main.evaluate("() => { if (S.side) toggleSide(false); fit(); }"); main.wait_for_timeout(400)
        main.screenshot(path=str(OUT / "0_한창.png"))

        # ① 도면을 새 창으로
        t0 = time.time()
        with ctx.expect_page() as pi:
            main.click('.pop-btn[data-pane="drawing"]')
        dr = pi.value; watch(dr, "도면 창")
        dr.set_viewport_size({"width": 1600, "height": 950})
        dr.wait_for_function(READY, timeout=180000)
        dr.wait_for_function("() => document.querySelector('#sheet').complete && document.querySelector('#sheet').naturalWidth > 0", timeout=60000)
        t_pop = time.time() - t0
        dr.wait_for_timeout(1200)
        mcls = main.evaluate("document.body.className"); dcls = dr.evaluate("document.body.className")
        left_vis = main.evaluate("getComputedStyle(document.querySelector('#left')).display")
        right_vis = dr.evaluate("getComputedStyle(document.querySelector('#right')).display")
        note(f"① 도면 새 창 — 열려서 도면이 선 데까지 {t_pop:.1f}초 · 본 창 '{mcls}' (#left {left_vis}) · 새 창 '{dcls}' (#right {right_vis})",
             "pane-list" in mcls and "pane-drawing" in dcls and left_vis == "none" and right_vis == "none")
        img_main = main.evaluate("document.querySelector('#sheet').getAttribute('src') || ''")
        note(f"   본 창은 도면이 숨어 있다 — 장 그림 src '{img_main[-30:]}' (다른 장으로 옮겨도 그림을 받지 않는다)")
        main.screenshot(path=str(OUT / "1_본창_목록만.png")); dr.screenshot(path=str(OUT / "1_새창_도면만.png"))

        # ② 목록에서 다른 장의 행을 누르면 도면 창이 그 장 · 그 자리로
        cur = dr.evaluate("S.page.page_no")
        key, pno = main.evaluate(f"() => {{ const r = S.rows.find(r => r.page_no !== {cur} && !r.removed && !r.deleted && r.rect && r.rect.length === 4 && r.values.type); return [r.key, r.page_no]; }}")
        main.evaluate(f"() => document.querySelector('#body tr[data-key=\"{key}\"]').scrollIntoView({{block:'center'}})")
        main.click(f'#body tr[data-key="{key}"] td[data-col="type"]')
        dr.wait_for_function(f"() => S.sel === '{key}' && S.page.page_no === {pno} && document.querySelector('rect.det.sel[data-key=\"{key}\"]')", timeout=20000)
        note(f"② 목록에서 p{pno} 행을 누름 → 도면 창 p{cur} → p{dr.evaluate('S.page.page_no')} · 그 상자 선택됨")
        dr.wait_for_timeout(900)
        dr.screenshot(path=str(OUT / "2_목록에서누름_도면창.png"))

        # ③ 도면에서 상자를 누르면 목록 창이 그 행 · 근거
        k2 = dr.evaluate(f"() => S.rows.filter(r => r.page_no === S.page.page_no && r.key !== '{key}' && !r.removed && !r.deleted && r.values.type).map(r => r.key)[0]")
        dr.evaluate(f"() => centreOnSymbol('{k2}')"); dr.wait_for_timeout(700)
        dr.click(f'rect.det[data-key="{k2}"]', force=True); dr.wait_for_timeout(300)
        dr.evaluate("() => closeScopePop()")
        main.wait_for_function(f"() => S.sel === '{k2}' && document.querySelector('#body tr.sel[data-key=\"{k2}\"]')", timeout=20000)
        ev = main.inner_text("#evidence")[:60].replace("\n", " ")
        note(f"③ 도면 창에서 상자 누름 → 목록 창 그 행 선택 · 근거 '{ev}'")
        main.screenshot(path=str(OUT / "3_도면에서누름_목록창.png"))

        # ④ 목록 칸에서 Q'ty 고침 → 도면 창의 라벨
        q0 = main.evaluate(f"S.rowByKey['{k2}'].values.qty")
        newq = (int(q0) if str(q0).isdigit() else 1) + 4
        td = f'#body tr[data-key="{k2}"] td[data-col="qty"]'
        main.click(td); main.keyboard.press("Control+A"); main.keyboard.type(str(newq)); main.keyboard.press("Enter")
        dr.wait_for_function(f"() => String(S.rowByKey['{k2}'].values.qty) === '{newq}'", timeout=20000)
        dr.wait_for_timeout(500)
        lab = dr.evaluate(f"() => {{ const t = [...document.querySelectorAll('text.qtytag, .qtytag')].find(n => n.dataset && n.dataset.key === '{k2}'); return t ? t.textContent : ''; }}")
        dq = dr.evaluate("k => S.rowByKey[k].values.qty", k2)
        note(f"④ 목록에서 Q'ty {q0} → {newq} → 도면 창 행 값 {dq} · 라벨 '{lab}' · 서버 {srow(k2)['user'].get('qty')}",
             str(srow(k2)['user'].get('qty')) == str(newq))

        # ⑤ 도면 창의 편집 카드에서 Line No. 고침 → 목록 칸
        dr.wait_for_selector("#fedit:not(.hidden)", timeout=10000)
        dr.fill('#fedit [data-f="line_no"]', "DUAL68TEST"); dr.press('#fedit [data-f="line_no"]', "Enter")
        main.wait_for_function(f"() => (document.querySelector('#body tr[data-key=\"{k2}\"] td[data-col=\"line_no\"]') || {{}}).textContent === 'DUAL68TEST'", timeout=20000)
        cell_cls = main.get_attribute(f'#body tr[data-key="{k2}"] td[data-col="line_no"]', "class")
        note(f"⑤ 도면 창 편집 카드에서 Line No. → 목록 칸 'DUAL68TEST' (class '{cell_cls}') · 이력 작성자 {srow(k2)['edited_by'].get('line_no', {}).get('author')}",
             "edited" in (cell_cls or ""))
        dr.screenshot(path=str(OUT / "5_도면창_편집카드.png"))

        # ⑥ 도면 창에서 '둘 다 아님' → 목록 창 그 행이 지워짐 · 목록에서 되돌리기 → 도면 창 복원
        dr.click(f'rect.det[data-key="{k2}"]', force=True); dr.wait_for_timeout(500)
        dr.click('.scopepop .sp-b[data-sp="none"]')
        main.wait_for_function(f"() => (document.querySelector('#body tr[data-key=\"{k2}\"]') || {{className:''}}).className.includes('deleted')", timeout=20000)
        trc = main.get_attribute(f'#body tr[data-key="{k2}"]', 'class')
        note(f"⑥ 도면 창 '둘 다 아님' → 목록 창 행 '{trc}' · 서버 removed {srow(k2).get('removed')}")
        main.click(f'#body tr[data-key="{k2}"] button[data-act="restore"]')
        dr.wait_for_function(f"() => !S.rowByKey['{k2}'].removed", timeout=20000)
        drm = dr.evaluate("k => S.rowByKey[k].removed", k2)
        note(f"   목록 창 되돌리기 → 도면 창 removed {drm} · 서버 {srow(k2).get('removed')}")

        # ⑦ Shift 묶음 (도면 창) → 목록 창 묶음 판
        ks = dr.evaluate("() => S.rows.filter(r => r.page_no === S.page.page_no && !r.removed && !r.deleted && r.values.type).map(r => r.key).slice(0, 3)")
        dr.evaluate("() => deselect()"); dr.wait_for_timeout(300)
        for k in ks:
            # 화면 밖 상자도 있어 좌표로 누르지 않고 그 상자에 Shift 누르기를 보낸다 (같은 처리기를 탄다)
            dr.evaluate("k => document.querySelector(`rect.det[data-key=\"${k}\"]`).dispatchEvent(new MouseEvent('click', {bubbles: true, shiftKey: true}))", k)
            dr.wait_for_timeout(300)
        main.wait_for_function("() => S.multi.size >= 2", timeout=15000)
        main.wait_for_timeout(500)
        nmr = main.evaluate("document.querySelectorAll('#body tr.multi').length")
        note(f"⑦ 도면 창 Shift 묶음 {dr.evaluate('S.multi.size')}개 → 목록 창 묶음 {main.evaluate('S.multi.size')}개 · 묶음 줄 {nmr} · 판 '{main.inner_text('#evidence')[:40].replace(chr(10), ' ')}'")
        main.screenshot(path=str(OUT / "7_묶음_목록창.png"))
        dr.keyboard.press("Escape"); dr.wait_for_timeout(500)

        # ⑧ 도면 창에서 장 옮기기 → 목록 창의 "이 장"
        other = dr.evaluate("() => S.pages.find(p => p.page_no !== S.page.page_no && p.layers && Object.keys(p.layers).length).page_no")
        dr.select_option("#page-select", str(other)); dr.wait_for_timeout(1500)
        note(f"⑧ 도면 창 장 → p{other} · 목록 창 S.page p{main.evaluate('S.page.page_no')}", main.evaluate("S.page.page_no") == other)

        # ⑨ 한 창으로 (새 창에서) → 본 창 복원
        dr.click(".pane-join:not(.hidden)")
        main.wait_for_function("() => !document.body.classList.contains('pane-list')", timeout=10000)
        main.wait_for_function("() => document.querySelector('#sheet').complete && document.querySelector('#sheet').naturalWidth > 0 && (document.querySelector('#sheet').getAttribute('src')||'').includes('/page/')", timeout=30000)
        main.wait_for_timeout(800)
        note(f"⑨ 새 창 '한 창으로' → 새 창 닫힘 {dr.is_closed()} · 본 창 '{main.evaluate('document.body.className')}' · 도면 다시 그림 p{main.evaluate('S.page.page_no')}")
        main.screenshot(path=str(OUT / "9_합침.png"))

        # ⑩ 목록을 새 창으로 → 본 창은 도면만 · 목록 창 누름 → 본 창 도면 따라감 · 창을 닫으면 복원
        with ctx.expect_page() as pi2:
            main.click('.pop-btn[data-pane="list"]')
        ls = pi2.value; watch(ls, "목록 창"); ls.set_viewport_size({"width": 1600, "height": 950})
        ls.wait_for_function(READY, timeout=180000); ls.wait_for_timeout(1200)
        imgreq = ls.evaluate("document.querySelector('#sheet').getAttribute('src') || ''")
        note(f"⑩ 목록 새 창 — 본 창 '{main.evaluate('document.body.className')}' · 새 창 '{ls.evaluate('document.body.className')}' · 목록 창은 장 그림을 안 받음 (src '{imgreq}')",
             imgreq == "")
        k3, p3 = ls.evaluate(f"() => {{ const r = S.rows.find(r => r.page_no !== S.page.page_no && !r.removed && r.rect && r.rect.length === 4 && r.values.type); return [r.key, r.page_no]; }}")
        ls.evaluate(f"() => document.querySelector('#body tr[data-key=\"{k3}\"]').scrollIntoView({{block:'center'}})")
        ls.click(f'#body tr[data-key="{k3}"] td[data-col="type"]')
        main.wait_for_function(f"() => S.sel === '{k3}' && S.page.page_no === {p3}", timeout=20000)
        main.wait_for_timeout(1200)
        note(f"   목록 창에서 p{p3} 행 누름 → 본 창(도면) p{main.evaluate('S.page.page_no')} · 선택 {main.evaluate('S.sel') == k3}")
        main.screenshot(path=str(OUT / "10_본창_도면만.png")); ls.screenshot(path=str(OUT / "10_새창_목록만.png"))
        ls.close(); main.wait_for_function("() => !document.body.classList.contains('pane-drawing')", timeout=10000)
        note(f"   목록 창을 X 로 닫음 → 본 창 '{main.evaluate('document.body.className')}' (두 칸 다시)")
        ok = not errs
        note(f"페이지 오류 {len(errs)}" + (f" — {errs[:3]}" if errs else ""), ok)
        br.close()
finally:
    srv.terminate()
    (OUT / "result.txt").write_text("\n".join(FOUND) + "\n", encoding="utf-8")
sys.exit(1 if BAD else 0)
