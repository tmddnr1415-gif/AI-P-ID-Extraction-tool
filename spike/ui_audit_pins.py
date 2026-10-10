"""hotfix76 — 위치 메모(도면의 한 자리에 붙는 메모)를 띄워서 눌러 확인한다.

    python3 spike/ui_audit_pins.py <data_dir 사본> <Rev.B job> <Rev.A job> out/hotfix76/ui

★ 실 DB 를 열지 않는다 — 넘긴 데이터 폴더(사본)를 PID_DATA_DIR 로 가리킨다.

  ① 📍 버튼 → 도면에서 사각형을 끌어 메모 · 점을 눌러 메모 (그 클릭이 아래 상자를 고르지 않는다)
  ② 도면을 다른 곳으로 옮긴 뒤 목록의 메모를 누르면 → 도면이 그 자리로 가서(확대·가운데) 깜빡이고 말풍선
  ③ 도면의 번호 깃발을 누르면 → 목록의 그 메모가 골라진다
  ④ 고치기(앞 글은 이력) · 완료(흐리게) · 숨김(목록·도면에서 감춤, 기록은 남음)
  ⑤ 같은 프로젝트의 Rev.A 같은 도면번호 장에서 그 메모가 '다른 Rev 에서' 로 보인다
"""
from __future__ import annotations
import json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
data, JOB_B, JOB_A, OUT = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
OUT.mkdir(parents=True, exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = f"http://127.0.0.1:{port}"
FOUND, BAD = [], []
def note(x): print(x, flush=True); FOUND.append(x)
def check(ok, what):
    note(("  ✔ " if ok else "  ✘ ") + what)
    if not ok: BAD.append(what)
try:
    for _ in range(90):
        try: urllib.request.urlopen(base + "/version", timeout=2); break
        except Exception: time.sleep(1)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        ctx = br.new_context(viewport={"width": 1920, "height": 1080})
        ctx.add_init_script("try{localStorage.setItem('pid.side.off','1');localStorage.removeItem('pid.split');"
                            "localStorage.setItem('pid.memo', JSON.stringify({open:true, h:260}))}catch(e){}")
        pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)

        def open_job(j):
            pg.goto(f"{base}/?embed=1&user={quote('홍길동')}"); pg.wait_for_timeout(1500)
            pg.evaluate(f"open('{j}')")
            pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.pages && S.pages.length > 0", timeout=180000)
            pg.wait_for_timeout(2000)
            if pg.evaluate("() => !!S.side"):
                pg.evaluate("() => toggleSide(false)"); pg.wait_for_timeout(500)

        def goto_page(n):
            pg.evaluate(f"() => showPage(S.pages.find(p => p.page_no === {n}))")
            pg.wait_for_function(f"() => S.page && S.page.page_no === {n} && S.memoPage === {n} && S.memoView", timeout=60000)
            pg.wait_for_timeout(1500)

        open_job(JOB_B)
        page_no = 10
        goto_page(page_no)
        dwg = pg.evaluate("() => S.page.drawing_no")
        pg.evaluate("() => { fit(); memoOpen(true); }"); pg.wait_for_timeout(600)
        st = pg.query_selector("#stage").bounding_box()
        note(f"Rev.B p{page_no} {dwg} · 도면 창 {round(st['width'])}×{round(st['height'])}")

        # ① 사각형 메모
        note("① 📍 → 사각형을 끌어 메모")
        pg.click("#memo-pin"); pg.wait_for_timeout(300)
        check(pg.evaluate("() => S.pinMode && document.querySelector('#stage').classList.contains('pinning')"), "자리 고르기 모드 · 십자 커서")
        x0, y0 = st["x"] + st["width"] * 0.40, st["y"] + st["height"] * 0.35
        x1, y1 = st["x"] + st["width"] * 0.55, st["y"] + st["height"] * 0.50
        pg.mouse.move(x0, y0); pg.mouse.down(); pg.mouse.move((x0 + x1) / 2, (y0 + y1) / 2, steps=5)
        pg.mouse.move(x1, y1, steps=5); pg.mouse.up(); pg.wait_for_timeout(500)
        check(pg.query_selector(".pinpop textarea") is not None, "자리 옆에 글 쓰는 말풍선")
        pg.screenshot(path=str(OUT / "1_자리_고름.png"))
        pg.fill(".pinpop textarea", "이 구역 MOV 두 개 — GTG 공급인지 발주처 회신 대기")
        pg.keyboard.press("Control+Enter"); pg.wait_for_timeout(1500)
        pins = pg.evaluate("() => pagePins().map(p => ({id: p.id, rect: p.rect, text: p.text}))")
        check(len(pins) == 1 and pins[0]["rect"][2] > pins[0]["rect"][0], f"저장 → 이 장 위치 메모 {len(pins)}개 · 자리 {pins and pins[0]['rect']}")
        check(pg.evaluate("() => document.querySelectorAll('#ov g.pinmark').length") == 1, "도면 위 번호 깃발 1")
        check(pg.evaluate("() => document.querySelectorAll('#ov .pinbox').length") >= 1, "도면 위 자리 사각형(파선)")

        # ① 점 메모 — 상자 위를 눌러도 그 상자가 골라지지 않는다
        note("① 📍 → 점을 눌러 메모 (행 상자 위)")
        # 행 상자 하나를 창 가운데로 데려온 뒤(범례 판 밑이 아니게) 그 위를 누른다
        pg.evaluate("""() => { const r = [...document.querySelectorAll('#ov rect.det')].find(e => +e.getAttribute('width') > 4);
            if (r) r.scrollIntoView({block: 'center', inline: 'center'}); }"""); pg.wait_for_timeout(400)
        box = pg.evaluate("""() => { const s = document.querySelector('#stage').getBoundingClientRect();
            const r = [...document.querySelectorAll('#ov rect.det')].find(e => { const b = e.getBoundingClientRect();
              if (!(b.width > 4 && b.left > s.left && b.right < s.right && b.top > s.top && b.bottom < s.bottom)) return false;
              return document.elementFromPoint(b.left + b.width*0.3, b.top + b.height*0.7) === e; });
            if (!r) return null; const b = r.getBoundingClientRect(); return {x: b.left + b.width*0.3, y: b.top + b.height*0.7, key: r.dataset.key}; }""")
        sel_before = pg.evaluate("() => S.sel")
        pg.click("#memo-pin"); pg.wait_for_timeout(300)
        if box:
            pg.mouse.click(box["x"], box["y"])
        else:
            pg.mouse.click(st["x"] + st["width"] * 0.7, st["y"] + st["height"] * 0.6)
        pg.wait_for_timeout(500)
        check(box is not None, "행 상자 위를 눌러 봄 (상자를 찾음)")
        check(pg.query_selector(".scopepop") is None and pg.evaluate("() => S.sel") == sel_before,
              f"그 클릭이 아래 상자({box and box['key']})를 고르거나 공급 주체 판을 띄우지 않음")
        pg.fill(".pinpop textarea", "이 계기 태그 번호 확인 필요")
        pg.click(".pinpop button[data-pa=save]"); pg.wait_for_timeout(1500)
        pins = pg.evaluate("() => pagePins().map(p => ({id: p.id, rect: p.rect}))")
        check(len(pins) == 2 and pins[1]["rect"][0] == pins[1]["rect"][2], f"점 메모 → 2개 (점 = 너비 0 사각형 {pins[-1]['rect']})")
        opt = pg.evaluate("() => document.querySelector('#page-select').selectedOptions[0].textContent")
        check("📍2" in opt, f"장 목록 '{opt.strip()}'")

        # ② 다른 곳으로 옮긴 뒤 목록에서 누르면 그 자리로
        note("② 목록의 메모 1 을 누르면 도면이 그 자리로")
        pg.evaluate("() => { closePinPop(); fit(); document.querySelector('#stage').scrollTo(0, 0); }"); pg.wait_for_timeout(500)
        z0 = pg.evaluate("() => S.zoom")
        pg.click(f"#pin-list li[data-pin='{pins[0]['id']}'] .memo-txt"); pg.wait_for_timeout(1200)
        z1 = pg.evaluate("() => S.zoom")
        # 메모 1 자리의 가운데가 도면 창 가운데 근처에 있는가
        centre = pg.evaluate(f"""() => {{ const b = document.querySelector('#ov .pinbox[data-pin="{pins[0]['id']}"]').getBoundingClientRect();
            const s = document.querySelector('#stage').getBoundingClientRect();
            return [Math.round(b.left + b.width/2 - (s.left + s.width/2)), Math.round(b.top + b.height/2 - (s.top + s.height/2))]; }}""")
        check(z1 > z0, f"확대 {z0:.3f} → {z1:.3f}")
        check(abs(centre[0]) < 40 and abs(centre[1]) < 40, f"자리 가운데가 창 가운데에서 {centre} px")
        check(pg.query_selector(".pinpop .pp-t") is not None, "자리 옆 말풍선에 글")
        check(pg.evaluate("() => !!document.querySelector('#ov .pinbox.flash')"), "자리 깜빡임")
        pg.screenshot(path=str(OUT / "2_목록에서_누름_자리로.png"))

        # ③ 도면 깃발을 누르면 목록의 그 메모
        note("③ 도면의 깃발 2 를 누르면 목록의 메모 2")
        pg.evaluate("() => { closePinPop(); S.pinSel = null; renderPins(); fit(); }"); pg.wait_for_timeout(800)
        fl = pg.evaluate(f"""() => {{ const c = document.querySelector('#ov g.pinmark[data-pin="{pins[1]['id']}"] circle');
            const b = c.getBoundingClientRect(); return {{x: b.left + b.width/2, y: b.top + b.height/2}}; }}""")
        pg.mouse.click(fl["x"], fl["y"]); pg.wait_for_timeout(700)
        check(pg.evaluate(f"() => S.pinSel === '{pins[1]['id']}' && !!document.querySelector('#pin-list li.sel[data-pin=\"{pins[1]['id']}\"]')"),
              "목록에서 메모 2 가 골라짐")
        check(pg.query_selector(".pinpop") is not None, "깃발 옆 말풍선")
        pg.screenshot(path=str(OUT / "3_깃발에서_누름.png"))

        # ④ 고치기 · 완료 · 숨김
        note("④ 고치기 · 완료 · 숨김")
        pg.evaluate("() => closePinPop()")
        pg.click(f"#pin-list li[data-pin='{pins[0]['id']}'] button[data-pa=edit]"); pg.wait_for_timeout(300)
        pg.fill(f"#pin-list li[data-pin='{pins[0]['id']}'] textarea.pin-edit", "MOV 두 개 — GTG 공급 확인함 (10/10)")
        pg.click(f"#pin-list li[data-pin='{pins[0]['id']}'] button[data-pa=save]"); pg.wait_for_timeout(1200)
        p1 = pg.evaluate(f"() => pagePins().find(p => p.id === '{pins[0]['id']}')")
        check(p1["text"].startswith("MOV 두 개 — GTG 공급 확인함") and len(p1["history"]) == 1
              and p1["history"][0]["text"].startswith("이 구역"), "고친 글 · 앞 글은 이력에")
        pg.click(f"#pin-list li[data-pin='{pins[0]['id']}'] button[data-pa=resolved]"); pg.wait_for_timeout(1000)
        check(pg.evaluate(f"() => document.querySelector('#pin-list li[data-pin=\"{pins[0]['id']}\"]').classList.contains('resolved')"
                          f" && document.querySelector('#ov .pinflag.resolved') !== null"), "완료 → 목록·깃발 흐리게")
        pg.click(f"#pin-list li[data-pin='{pins[1]['id']}'] button[data-pa=hidden]"); pg.wait_for_timeout(1000)
        check(pg.evaluate(f"() => !document.querySelector('#pin-list li[data-pin=\"{pins[1]['id']}\"]')"
                          f" && !document.querySelector('#ov g.pinmark[data-pin=\"{pins[1]['id']}\"]')"), "숨김 → 목록·도면에서 감춤")
        pg.check("#pin-showhidden"); pg.wait_for_timeout(500)
        check(pg.evaluate(f"() => !!document.querySelector('#pin-list li.hidden-state[data-pin=\"{pins[1]['id']}\"]')"),
              "'숨긴 것도' → 다시 보임 (기록은 남아 있음)")
        pg.uncheck("#pin-showhidden"); pg.wait_for_timeout(300)
        legend = pg.evaluate("() => { const r = [...document.querySelectorAll('#ovl-items .ovl-row')].find(x => x.querySelector('input').value === 'PIN'); return r ? r.textContent.replace(/\\s+/g, ' ').trim() : null; }")
        check(legend is not None, f"범례 자기 칸 '{legend}'")
        pg.query_selector("#memo").screenshot(path=str(OUT / "4_메모판.png"))

        # ⑤ Rev.A 같은 도면번호 장
        note("⑤ 같은 프로젝트 Rev.A 의 같은 도면번호 장")
        open_job(JOB_A)
        pa = pg.evaluate(f"() => (S.pages.find(p => p.drawing_no === {json.dumps(dwg)}) || {{}}).page_no")
        if pa:
            goto_page(pa)
            pg.evaluate("() => { fit(); memoOpen(true); }"); pg.wait_for_timeout(800)
            v = pg.evaluate("() => pagePins().map(p => ({here: p.here, other: p.other_rev, state: p.state}))")
            check(len(v) == 2 and all(not x["here"] for x in v), f"Rev.A p{pa} → 위치 메모 {len(v)}개 (다른 Rev 에서 단 것)")
            check(pg.evaluate("() => document.querySelectorAll('#pin-list .memo-other').length") >= 1, "'다른 Rev 에서' 표식")
            pg.click("#pin-list li[data-pin] .memo-txt"); pg.wait_for_timeout(1200)
            pg.screenshot(path=str(OUT / "5_RevA_같은도면.png"))
        else:
            check(False, f"Rev.A 에 같은 도면번호 {dwg} 장이 없음")
        check(not errs, f"페이지 오류 {len(errs)} {errs[:3]}")
        br.close()
finally:
    srv.terminate()
    note(f"결과: 실패 {len(BAD)}" + (f" — {BAD}" if BAD else ""))
    (OUT / "audit.txt").write_text("\n".join(FOUND) + "\n", encoding="utf-8")
