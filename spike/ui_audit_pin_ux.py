"""hotfix77 — 핀 메모를 띄워서 눌러 확인한다 (압정 · 작성칸 · 핀↔메모 · 두 번 깜박임).

    python3 spike/ui_audit_pin_ux.py <data_dir 사본> <job> out/hotfix77/ui

★ 실 DB 를 열지 않는다 — 넘긴 데이터 폴더(사본)를 PID_DATA_DIR 로 가리킨다.

  ① 📌 버튼 → 커서가 압정 · 도면을 한 번 누르면 그 점에 핀 · 작성칸에 날짜(오늘) · 작성자(로그인) · 메모 내용
  ② 저장하면 압정의 **바늘 끝이 누른 그 점**에 선다
  ③ 메모장의 메모를 누르면 → 도면이 그 자리로 가고 압정이 **정확히 두 번** 깜박인다 (불투명도를 시간으로 재서 센다)
  ④ 도면의 압정을 누르면 → 메모장이 그 메모로 굴러가고 그 메모가 두 번 깜박인다
  ⑤ 이름을 모르는 브라우저 — 작성칸의 작성자가 입력이 되고 한 번 적으면 다음부터 자동
"""
from __future__ import annotations
import datetime, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
data, JOB, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT), PID_PAGE_WARM="0", PID_RENDER_POOL="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = f"http://127.0.0.1:{port}"
FOUND, BAD = [], []
def note(x): print(x, flush=True); FOUND.append(x)
def check(ok, what):
    note(("  ✔ " if ok else "  ✘ ") + what)
    if not ok: BAD.append(what)

# 깜박임을 센다 — 불투명도를 25ms 마다 1.6초 동안 읽어 0.5 아래로 내려간 구간 수
COUNT_BLINKS = """async (sel) => {
  const seen = []; const t0 = performance.now();
  while (performance.now() - t0 < 1600) {
    const e = document.querySelector(sel);
    seen.push(e ? +getComputedStyle(e).opacity : 1);
    await new Promise(r => setTimeout(r, 25));
  }
  let n = 0, low = false;
  for (const o of seen) { if (o < 0.5 && !low) { n++; low = true; } else if (o >= 0.5) low = false; }
  return {n, min: Math.min(...seen), samples: seen.length};
}"""
COUNT_LI_BLINKS = """async (sel) => {
  const seen = []; const t0 = performance.now();
  while (performance.now() - t0 < 1600) {
    const e = document.querySelector(sel);
    const c = e ? getComputedStyle(e).backgroundColor : '';
    const m = c.match(/\\d+/g) || [255, 255, 255];
    seen.push(+m[2]);            // 파랑 성분 — #fffaf0(240) ↔ #ffd98a(138)
    await new Promise(r => setTimeout(r, 25));
  }
  let n = 0, low = false;
  for (const b of seen) { if (b < 190 && !low) { n++; low = true; } else if (b >= 190) low = false; }
  return {n, min: Math.min(...seen)};
}"""
try:
    for _ in range(90):
        try: urllib.request.urlopen(base + "/version", timeout=2); break
        except Exception: time.sleep(1)
    from playwright.sync_api import sync_playwright
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

        def new_page(user):
            ctx = br.new_context(viewport={"width": 1920, "height": 1080})
            ctx.add_init_script("try{localStorage.setItem('pid.side.off','1');localStorage.removeItem('pid.split');"
                                "localStorage.removeItem('pid.author');"
                                "localStorage.setItem('pid.memo', JSON.stringify({open:true, h:260}))}catch(e){}")
            pg = ctx.new_page(); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
            pg.goto(f"{base}/?embed=1" + (f"&user={quote(user)}" if user else "")); pg.wait_for_timeout(1500)
            pg.evaluate(f"open('{JOB}')")
            pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.pages && S.pages.length > 0", timeout=180000)
            pg.wait_for_timeout(1500)
            if pg.evaluate("() => !!S.side"):
                pg.evaluate("() => toggleSide(false)"); pg.wait_for_timeout(500)
            return pg, errs

        def goto_page(pg, n):
            pg.evaluate(f"() => showPage(S.pages.find(p => p.page_no === {n}))")
            pg.wait_for_function(f"() => S.page && S.page.page_no === {n} && S.memoPage === {n} && S.memoView && S.pinImgPage === {n}", timeout=60000)
            pg.wait_for_timeout(1200)

        pg, errs = new_page("홍길동")
        page_no = 10
        goto_page(pg, page_no)
        pg.evaluate("() => { fit(); memoOpen(true); }"); pg.wait_for_timeout(600)
        st = pg.query_selector("#stage").bounding_box()
        note(f"p{page_no} {pg.evaluate('() => S.page.drawing_no')} · 도면 창 {round(st['width'])}×{round(st['height'])}")

        # ① 버튼 → 압정 커서 → 한 번 누름 → 작성칸
        note("① 📌 핀 메모 달기 → 도면을 한 번 누름")
        pg.click("#memo-pin"); pg.wait_for_timeout(300)
        cur = pg.evaluate("() => getComputedStyle(document.querySelector('#stage')).cursor")
        check(cur.startswith("url("), f"커서가 압정 그림 ({cur[:40]}…)")
        cx, cy = st["x"] + st["width"] * 0.62, st["y"] + st["height"] * 0.42
        pg.mouse.click(cx, cy); pg.wait_for_timeout(500)
        hdr = pg.evaluate("() => { const p = document.querySelector('.pinpop'); return p ? {date: p.querySelector('.pp-date')?.textContent,"
                          " who: p.querySelector('.pp-who')?.textContent, ta: !!p.querySelector('textarea'), name: !!p.querySelector('.pp-name'),"
                          " labels: [...p.querySelectorAll('dt')].map(d => d.textContent)} : null; }")
        check(hdr is not None and hdr["labels"] == ["날짜", "작성자", "메모 내용"], f"작성칸 항목 {hdr and hdr['labels']}")
        check(hdr and (hdr["date"] or "").startswith(today), f"날짜 자동 '{hdr and hdr['date']}'")
        check(hdr and "홍길동" in (hdr["who"] or "") and not hdr["name"], f"작성자 자동 '{hdr and (hdr['who'] or '').strip()}' (입력 칸 없음)")
        check(pg.evaluate("() => !!document.querySelector('#ov g.pinmark.drop .pinneedle')"), "누른 자리에 임시 압정")
        pg.screenshot(path=str(OUT / "1_작성칸_날짜_작성자.png"))
        pg.fill(".pinpop textarea", "이 계기 태그 번호 발주처 회신 대기")
        pg.keyboard.press("Control+Enter"); pg.wait_for_timeout(1500)
        pins = pg.evaluate("() => pagePins().map(p => ({id: p.id, rect: p.rect, author: p.author, at: p.at}))")
        check(len(pins) == 1 and pins[0]["author"] == "홍길동", f"저장 → 위치 메모 {len(pins)} · 작성자 {pins and pins[0]['author']}")
        p1 = pins[0]["id"]

        # ② 바늘 끝 = 누른 점
        tip = pg.evaluate(f"""() => {{ const e = document.querySelector('#ov g.pinmark[data-pin="{p1}"] .pinshadow').getBoundingClientRect();
            return [e.left + e.width / 2, e.top + e.height / 2]; }}""")
        d = ((tip[0] - cx) ** 2 + (tip[1] - cy) ** 2) ** 0.5
        check(d < 3, f"바늘 끝이 누른 점에서 {d:.1f}px")
        parts = pg.evaluate(f"() => [...document.querySelector('#ov g.pinmark[data-pin=\"{p1}\"]').children].map(e => e.getAttribute('class') || e.tagName)")
        check([x.split()[0] for x in parts[:4]] == ["pinshadow", "pinneedle", "pincollar", "pinflag"], f"압정 모양 {parts}")
        pg.evaluate("() => closePinPop()")
        # 압정 확대 크롭
        hb = pg.evaluate(f"() => {{ const b = document.querySelector('#ov g.pinmark[data-pin=\"{p1}\"]').getBoundingClientRect(); return [b.left, b.top, b.width, b.height]; }}")
        pg.screenshot(path=str(OUT / "2_압정_확대.png"), clip={"x": hb[0] - 70, "y": hb[1] - 50, "width": hb[2] + 160, "height": hb[3] + 110})

        # 영역 메모 하나 더 (끌기)
        pg.click("#memo-pin"); pg.wait_for_timeout(300)
        x0, y0 = st["x"] + st["width"] * 0.38, st["y"] + st["height"] * 0.12
        pg.mouse.move(x0, y0); pg.mouse.down(); pg.mouse.move(x0 + 90, y0 + 70, steps=8); pg.mouse.up(); pg.wait_for_timeout(500)
        pg.fill(".pinpop textarea", "이 구역 MOV 두 개 — GTG 공급 확인")
        pg.click(".pinpop button[data-pa=save]"); pg.wait_for_timeout(1500)
        p2 = [p for p in pg.evaluate("() => pagePins().map(p => p.id)") if p != p1][0]

        # ③ 메모장의 메모를 누르면 → 그 자리로 · 압정 두 번 깜박
        note("③ 메모장의 메모 1 을 누름 → 도면이 그 자리로 · 압정이 두 번 깜박")
        pg.evaluate("() => { closePinPop(); fit(); document.querySelector('#stage').scrollTo(0, 0); }"); pg.wait_for_timeout(800)
        z0 = pg.evaluate("() => S.zoom")
        pg.click(f"#pin-list li[data-pin='{p1}'] .memo-txt")
        blinks = pg.evaluate(COUNT_BLINKS, f"#ov g.pinmark[data-pin='{p1}']")
        z1 = pg.evaluate("() => S.zoom")
        check(blinks["n"] == 2, f"압정 깜박임 {blinks['n']}번 (최저 불투명도 {blinks['min']:.2f} · 표본 {blinks['samples']})")
        centre = pg.evaluate(f"""() => {{ const b = document.querySelector('#ov g.pinmark[data-pin="{p1}"] .pinshadow').getBoundingClientRect();
            const s = document.querySelector('#stage').getBoundingClientRect();
            return [Math.round(b.left + b.width/2 - (s.left + s.width/2)), Math.round(b.top + b.height/2 - (s.top + s.height/2))]; }}""")
        check(z1 > z0 and abs(centre[0]) < 40 and abs(centre[1]) < 40, f"확대 {z0:.3f} → {z1:.3f} · 자리가 창 가운데에서 {centre}px")
        pg.wait_for_timeout(300)
        check(pg.evaluate(f"() => getComputedStyle(document.querySelector('#ov g.pinmark[data-pin=\"{p1}\"]')).opacity") == "1",
              "깜박임이 끝나면 그대로 보인다 (세 번째는 없다)")
        pg.screenshot(path=str(OUT / "3_메모에서_누름_자리로.png"))
        # 영역 메모도 압정 + 영역이 같이 깜박
        pg.evaluate("() => { closePinPop(); fit(); }"); pg.wait_for_timeout(600)
        pg.click(f"#pin-list li[data-pin='{p2}'] .memo-txt")
        b2 = pg.evaluate(COUNT_BLINKS, f"#ov g.pinmark[data-pin='{p2}']")
        check(b2["n"] == 2 and pg.evaluate(f"() => !!document.querySelector('#ov .pinbox[data-pin=\"{p2}\"]')"),
              f"영역 메모도 압정 {b2['n']}번 깜박 · 영역 표시")

        # ④ 도면의 압정을 누르면 → 메모장의 그 메모로 · 두 번 깜박
        note("④ 도면의 압정 1 을 누름 → 메모장의 그 메모로")
        pg.evaluate("""() => { closePinPop(); S.pinSel = null; renderPins(); fit();
            const l = document.querySelector('#pin-list'); l.style.maxHeight = '60px'; l.scrollTop = 9999; }"""); pg.wait_for_timeout(800)
        hd = pg.evaluate(f"() => {{ const b = document.querySelector('#ov g.pinmark[data-pin=\"{p1}\"] circle').getBoundingClientRect(); return [b.left + b.width/2, b.top + b.height/2]; }}")
        pg.mouse.click(hd[0], hd[1])
        lb = pg.evaluate(COUNT_LI_BLINKS, f"#pin-list li[data-pin='{p1}']")
        vis = pg.evaluate(f"""() => {{ const li = document.querySelector('#pin-list li[data-pin="{p1}"]').getBoundingClientRect();
            const L = document.querySelector('#pin-list'); const l = L.getBoundingClientRect();
            return {{ok: li.top >= l.top - 1 && li.top < l.bottom, li: [li.top, li.bottom], list: [l.top, l.bottom], st: L.scrollTop, sh: L.scrollHeight, ch: L.clientHeight}}; }}""")
        check(pg.evaluate(f"() => S.pinSel === '{p1}' && document.querySelector('#pin-list li[data-pin=\"{p1}\"]').classList.contains('sel')"),
              "메모장에서 메모 1 이 골라짐")
        check(vis["ok"], f"메모장이 그 메모로 굴러감 (목록 안에 보임) {vis}")
        check(lb["n"] == 2, f"메모 깜박임 {lb['n']}번")
        pg.evaluate("() => { document.querySelector('#pin-list').style.maxHeight = ''; }"); pg.wait_for_timeout(300)
        pg.screenshot(path=str(OUT / "4_압정에서_누름_메모로.png"))
        check(not errs, f"페이지 오류 {len(errs)} {errs[:3]}")

        # ⑤ 이름을 모르는 브라우저
        note("⑤ 이름 없는 브라우저 — 작성칸에서 한 번만 적는다")
        pg2, errs2 = new_page("")
        goto_page(pg2, page_no)
        pg2.evaluate("() => { fit(); memoOpen(true); }"); pg2.wait_for_timeout(600)
        pg2.click("#memo-pin"); pg2.wait_for_timeout(300)
        pg2.mouse.click(st["x"] + st["width"] * 0.8, st["y"] + st["height"] * 0.2); pg2.wait_for_timeout(500)
        check(pg2.query_selector(".pinpop .pp-name") is not None, "작성자 칸이 입력")
        pg2.fill(".pinpop textarea", "이름 없는 브라우저에서 단 메모")
        pg2.click(".pinpop button[data-pa=save]"); pg2.wait_for_timeout(600)
        check("작성자" in (pg2.evaluate("() => document.querySelector('.pinpop .pp-msg')?.textContent") or ""), "이름 없이 저장하면 막고 말함")
        pg2.fill(".pinpop .pp-name", "김철수")
        pg2.click(".pinpop button[data-pa=save]"); pg2.wait_for_timeout(1500)
        last = pg2.evaluate("() => pagePins().slice(-1)[0]")
        check(last and last["author"] == "김철수", f"저장 작성자 {last and last['author']}")
        pg2.click("#memo-pin"); pg2.wait_for_timeout(300)
        pg2.mouse.click(st["x"] + st["width"] * 0.5, st["y"] + st["height"] * 0.25); pg2.wait_for_timeout(500)
        who2 = pg2.evaluate("() => document.querySelector('.pinpop .pp-who')?.textContent || ''")
        check("김철수" in who2 and pg2.query_selector(".pinpop .pp-name") is None, f"다음부터 자동 '{who2.strip()}'")
        pg2.keyboard.press("Escape")
        check(not errs2, f"페이지 오류 {len(errs2)} {errs2[:3]}")
        br.close()
finally:
    srv.terminate()
    try: srv.wait(10)
    except Exception: srv.kill()
(OUT / "audit.txt").write_text("\n".join(FOUND) + f"\n\n결함 {len(BAD)}\n", encoding="utf-8")
print("BAD", len(BAD))
sys.exit(1 if BAD else 0)
