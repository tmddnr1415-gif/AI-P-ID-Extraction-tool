"""hotfix80 — 띄워서 눌러 확인한다: 검색 지연 · 목록 굴리기(새로 보이는 행만) · 저장 상태 칸 · Ctrl+F · 열 폭 고정.

    python3 spike/ui_audit_hotfix80.py <data_dir 사본> <job> <out_dir>

★ 실 DB 를 열지 않는다 — 넘긴 데이터 폴더(사본)를 PID_DATA_DIR 로 가리킨다.
"""
from __future__ import annotations
import json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
data, JOB, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT), PID_PAGE_WARM="0", PID_RENDER_POOL="0", PID_ROWS_WARM="0")
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
        ctx.add_init_script("try{localStorage.setItem('pid.side.off','1');localStorage.removeItem('pid.split')}catch(e){}")
        pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
        pg.on("dialog", lambda d: d.accept())
        pg.goto(f"{base}/?embed=1&user={quote('홍길동')}"); pg.wait_for_timeout(1200)
        pg.evaluate(f"open('{JOB}')")
        pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.vlist && S.vlist.length > 5", timeout=180000)
        pg.wait_for_timeout(1200)
        if pg.evaluate("() => !!S.side"): pg.evaluate("() => toggleSide(false)"); pg.wait_for_timeout(400)
        n_all = pg.evaluate("() => visibleRows().length")        # 삭제 후보 행까지 — 목록이 세우는 수

        note("① 검색 — 손이 멈춘 뒤 한 번")
        pg.click("#filter")
        before = pg.evaluate("() => S.vlist.length")
        # 글자 셋을 치면 목록은 **한 번**만 세워져야 한다 (글자마다가 아니라 손이 멈춘 뒤).  시각으로 재면 기계가 바쁠 때
        # 지연 안에 다음 글자가 못 들어가 흔들리므로, renderGrid 가 몇 번 불렸나를 센다.
        pg.evaluate("() => { window.__rg = 0; const f = renderGrid; window.renderGrid = function () { window.__rg++; return f.apply(this, arguments); }; }")
        pg.keyboard.type("PIT")
        pg.wait_for_timeout(500)
        renders = pg.evaluate("() => window.__rg")
        after = pg.evaluate("() => S.vlist.length")
        check(renders < 3 and after < before and after == pg.evaluate("() => visibleRows().length"),
              f"글자 셋에 목록 세우기 {renders}번 (글자마다 3번이 아니다) → {after} / {before}")
        check(pg.text_content("#count").startswith("표시 "), "행 수 칸이 '표시 N / 전체 M'")
        w_filtered = pg.evaluate("() => [...document.querySelectorAll('#head th')].map(th => Math.round(th.getBoundingClientRect().width))")
        pg.fill("#filter", ""); pg.wait_for_timeout(400)
        w_all = pg.evaluate("() => [...document.querySelectorAll('#head th')].map(th => Math.round(th.getBoundingClientRect().width))")
        # 고친 칸의 연필(✎)·고른 행 테두리로 1~2px 는 움직일 수 있다 — 거르기 전후 열이 뛰지 않으면 된다 (예전엔 수십 px)
        check(len(w_filtered) == len(w_all) and max(abs(a - b) for a, b in zip(w_filtered, w_all)) <= 4,
              f"열 폭이 거르기 전후 같다 (±4px) 차 {[b - a for a, b in zip(w_all, w_filtered)]}")
        check(pg.evaluate("() => S.vlist.length") == n_all, "지우면 전체로")

        note("② 목록 굴리기 — 보이는 창 = 기대한 창 · 새 행만 넣는다")
        r = pg.evaluate("""async () => {
          const gw = document.querySelector('#gridwrap'), body = document.querySelector('#body');
          let bad = 0, steps = 0, reused = 0;
          const px = v => parseFloat(v);
          for (let i = 0; i < 30; i++) {
            const firstRow = body.children[1];
            gw.scrollTop += gw.clientHeight * 0.6;
            await new Promise(r => requestAnimationFrame(r)); await new Promise(r => requestAnimationFrame(r));
            steps++;
            const keys = [...body.children].filter(t => t.dataset.key).map(t => t.dataset.key);
            const exp = S.vlist.slice(VROW.start, VROW.end).map(r => r.key);
            const first = body.firstElementChild, beforeMeasure = body.lastElementChild.previousElementSibling;
            const topH = first.classList.contains('vpad') ? px(first.firstElementChild.style.height) : 0;
            const botH = (beforeMeasure && beforeMeasure.classList.contains('vpad') && beforeMeasure !== first) ? px(beforeMeasure.firstElementChild.style.height)
                       : (beforeMeasure === first && first.classList.contains('vpad') && VROW.start === 0 ? topH : 0);
            const padsOk = Math.abs((VROW.start > 0 ? topH : 0) - VROW.start * VROW.h) < 0.5
                        && Math.abs((VROW.end < S.vlist.length ? botH : 0) - (S.vlist.length - VROW.end) * VROW.h) < 0.5
                        && (VROW.start > 0 || !first.classList.contains('vpad') || beforeMeasure === first);   // 맨 위가 빈 줄이면 안 된다
            if (JSON.stringify(keys) !== JSON.stringify(exp) || !padsOk) bad++;
            if (firstRow && firstRow.isConnected) reused++;        // 앞 걸음의 첫 행이 아직 살아 있으면 통째로 다시 그린 것이 아니다
          }
          gw.scrollTop = 0; await new Promise(r => requestAnimationFrame(r)); await new Promise(r => requestAnimationFrame(r));
          return { steps, bad, reused, h: VROW.h }; }""")
        check(r["bad"] == 0, f"굴리기 {r['steps']}걸음 · 어긋난 창 {r['bad']}")
        check(r["reused"] > 0, f"행을 통째로 다시 만들지 않는다 (앞 걸음의 행이 살아남은 걸음 {r['reused']})")
        check(pg.evaluate("() => document.querySelector('#body tr') && !!document.querySelector('#body tr').dataset.key"),
              "맨 위로 돌아오면 첫 줄은 행이다 (빈 줄이 아니다 — `#body tr` 로 찾는 곳이 있다)")

        note("③ 저장 상태 칸")
        key = pg.evaluate("() => S.vlist.find(r => !r.deleted && !r.removed).key")
        pg.evaluate(f"() => revealRow('{key}').scrollIntoView({{block:'center'}})")
        check(pg.evaluate("() => document.querySelector('#save-state').classList.contains('hidden')"), "저장 전에는 비어 있다")
        pg.dblclick(f'#body tr[data-key="{key}"] td[data-col="remark"]'); pg.wait_for_timeout(200)
        pg.keyboard.press("Control+A"); pg.keyboard.type("hf80"); pg.keyboard.press("Enter")
        seen = pg.evaluate("""() => new Promise(res => { const el = document.querySelector('#save-state'); const out = [];
            const t0 = performance.now(); const iv = setInterval(() => { const t = el.textContent; if (t && out[out.length-1] !== t) out.push(t);
            if (performance.now() - t0 > 2500) { clearInterval(iv); res(out); } }, 10); })""")
        check(any(x.startswith("저장 중") for x in seen) or any(x.startswith("저장됨") for x in seen), f"저장 중 → 저장됨 {seen}")
        check(seen and seen[-1].startswith("저장됨"), f"끝에는 '저장됨 HH:MM' ({seen[-1] if seen else ''})")
        pg.screenshot(path=str(OUT / "1_저장됨.png"), clip={"x": 1100, "y": 0, "width": 820, "height": 120})
        # 실패 — 없는 행에 PATCH
        pg.evaluate("() => fetch('/jobs/' + S.job.id + '/rows/nope-' + Date.now(), {method:'PATCH', headers:{'Content-Type':'application/json'}, body: JSON.stringify({field:'remark', value:'x', author:'t'})})")
        pg.wait_for_timeout(800)
        check(pg.text_content("#save-state").startswith("저장 실패"), f"거절되면 '저장 실패' ({pg.text_content('#save-state')})")
        pg.screenshot(path=str(OUT / "2_저장실패.png"), clip={"x": 1100, "y": 0, "width": 820, "height": 120})
        # 미리 읽기(POST propose)는 저장이 아니다
        pg.evaluate("() => { saveState('saved'); }")      # 상태를 되돌린 뒤
        pg.evaluate("() => fetch('/jobs/' + S.job.id + '/markup/propose', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({page_no: S.page.page_no, rect:[0,0,1,1]})})")
        pg.wait_for_timeout(300)
        check(not pg.text_content("#save-state").startswith("저장 중"), "미리 읽기는 '저장 중' 이 아니다")

        note("④ Ctrl+F")
        pg.locator("#stage").focus(); pg.keyboard.press("Control+f"); pg.wait_for_timeout(200)
        check(pg.evaluate("() => document.activeElement && document.activeElement.id === 'filter'"), "도면에서 Ctrl+F → 검색 칸")
        pg.keyboard.type("TIT"); pg.wait_for_timeout(400)
        check(pg.evaluate("() => S.filter") == "TIT" and pg.evaluate("() => S.vlist.length") < n_all, "바로 칠 수 있다 · 걸러진다")
        pg.fill("#filter", ""); pg.wait_for_timeout(300)
        pg.evaluate("() => toFirstScreen()"); pg.wait_for_timeout(800)
        pg.keyboard.press("Control+f"); pg.wait_for_timeout(200)
        check(pg.evaluate("() => !(document.activeElement && document.activeElement.id === 'filter')"), "첫 화면에서는 검색 칸으로 가지 않는다")
        errs = [e for e in errs if "404" not in e]           # 위에서 일부러 낸 없는 행 PATCH 의 404 는 뺀다
        check(not errs, f"페이지 오류 {len(errs)} {errs[:3]}")
        br.close()
finally:
    srv.terminate()
    try: srv.wait(10)
    except Exception: srv.kill()
(OUT / "audit.txt").write_text("\n".join(FOUND) + f"\n\n결함 {len(BAD)}\n", encoding="utf-8")
print("BAD", len(BAD))
sys.exit(1 if BAD else 0)
