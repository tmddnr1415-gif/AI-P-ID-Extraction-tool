"""hotfix74 — 화면 돌발상황 시뮬레이션 (실제로 띄워서 누른다 · 실 DB 를 열지 않는다).

    python3 spike/ui_chaos.py <data_dir 사본> <job> out/hotfix74/ui_chaos

U1 결과 화면에서 새로고침 · 뒤로/앞으로 — 페이지 오류 없이 같은 결과로 돌아오는가
U2 서버가 죽은 동안 칸 편집 · 장 넘기기 — 사람 말로 알리는가 (조용히 사라지거나 멈추지 않는가) ·
   서버가 돌아오면 다시 쓸 수 있는가
U3 두 창이 같은 칸을 고친다 — 마지막 값이 서버에 남고 두 창이 그것을 보는가 (새로 읽으면)
U4 느린 망 (모든 요청 1.5초 지연) — 결과 열기가 끝나고 목록이 한 번만 그려지는가
U5 업로드 중 서버가 죽는다 — 업로드 단추가 영영 '올리는 중' 으로 남지 않는가
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data, JOB, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
base = f"http://127.0.0.1:{port}"
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT), PID_PAGE_WARM="0")
SRV = {"p": None}
FOUND, DEFECTS = [], []


def start():
    SRV["p"] = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                                 "--port", str(port)], cwd=str(ROOT), env=env,
                                stdout=open(OUT / "server.log", "a"), stderr=subprocess.STDOUT)
    for _ in range(120):
        try:
            urllib.request.urlopen(base + "/version", timeout=2); return
        except Exception:                                          # noqa: BLE001
            time.sleep(0.5)


def stop():
    if SRV["p"] and SRV["p"].poll() is None:
        SRV["p"].kill(); SRV["p"].wait()


def note(x):
    print(x, flush=True); FOUND.append(x)


def defect(x):
    note("★ " + x); DEFECTS.append(x)


def open_job(pg, timeout=180000):
    pg.evaluate(f"open('{JOB}')")
    pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.pages && S.pages.length > 0",
                         timeout=timeout)
    pg.wait_for_timeout(1500)
    pg.evaluate("() => { if (S.side) toggleSide(); }")


def first_key(pg):
    return pg.evaluate("() => { const r = S.rows.find(r => r.page_no === S.page.page_no && !r.removed && "
                       "!r.deleted && r.values.type); return r && r.key; }")


def edit(pg, key, col, value):
    pg.evaluate("() => { if (S.side) toggleSide(); }")
    pg.evaluate(f"() => select('{key}', true)"); pg.wait_for_timeout(800)
    td = pg.query_selector(f'#body tr[data-key="{key}"] td[data-col="{col}"]')
    td.scroll_into_view_if_needed(); td.click()
    pg.keyboard.press("Control+A"); pg.keyboard.type(value); pg.keyboard.press("Enter")
    pg.wait_for_timeout(1500)


def server_value(key, field):
    rows = json.loads(urllib.request.urlopen(f"{base}/jobs/{JOB}/rows?keys={key}").read())
    r = rows[0] if rows else {}
    return (r.get("user") or {}).get(field)


def visible_text(pg):
    return pg.evaluate("() => [...document.querySelectorAll('#net-banner, .notice, .toast, #edit-notice, .err, .alert, #modal')]"
                       ".filter(e => e.offsetParent).map(e => e.innerText).join(' | ')")


try:
    start()
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        ctx = br.new_context(viewport={"width": 1600, "height": 950})
        pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        dialogs = []
        pg.on("dialog", lambda d: (dialogs.append(d.message), d.accept()))
        pg.add_init_script("try{localStorage.setItem('pid.author','시뮬')}catch(e){}")
        pg.goto(base + "/"); pg.wait_for_timeout(1200)
        open_job(pg)
        n0 = pg.evaluate("() => S.rows.length")
        # ---------------- U1
        url = pg.url
        pg.reload(); pg.wait_for_timeout(2500)
        reopened = pg.evaluate("() => typeof S !== 'undefined' && S.job && S.job.id")
        note(f"U1 새로고침 → 주소 {url[-30:]} · 다시 연 결과 {reopened}")
        if not reopened:
            pg.wait_for_timeout(3000); open_job(pg)
        pg.go_back(); pg.wait_for_timeout(1500); pg.go_forward(); pg.wait_for_timeout(2500)
        note(f"U1 뒤로/앞으로 → 결과 {pg.evaluate('() => S.job && S.job.id')} · 행 {pg.evaluate('() => S.rows.length')} (처음 {n0})")
        if errs:
            defect(f"U1 페이지 오류 {errs[:3]}"); errs.clear()
        # ---------------- U2
        if not pg.evaluate("() => S.job"):
            open_job(pg)
        key = first_key(pg)
        stop()
        t0 = time.time()
        edit(pg, key, "qty", "9")
        said = visible_text(pg) + " | " + " / ".join(dialogs[-2:])
        note(f"U2 서버 꺼짐 중 편집 → 화면 말 '{said[:200]}' · {time.time() - t0:.1f}초 · 페이지 오류 {errs[:2]}")
        cell = pg.evaluate(f"() => {{ const td = document.querySelector('#body tr[data-key=\"{key}\"] td[data-col=\"qty\"]'); return td && td.innerText; }}")
        note(f"U2 그 칸에 보이는 값 '{cell}'")
        if "9" in (cell or "") and not any(w in said for w in ("저장", "연결", "서버", "실패", "못")):
            defect("U2 서버가 꺼졌는데 칸이 저장된 것처럼 보이고 아무 말도 없다")
        try:
            pg.evaluate("() => S.pages[1] && showPage(S.pages[1])")
        except Exception as e:                                     # noqa: BLE001
            note(f"U2 장 넘기기 예외 {str(e)[:120]}")
        pg.wait_for_timeout(2000)
        start()
        pg.wait_for_timeout(1500)
        edit(pg, key, "qty", "6")
        v = server_value(key, "qty")
        note(f"U2 서버 복귀 뒤 편집 → 서버 값 {v}")
        if str(v) != "6":
            defect(f"U2 서버가 돌아온 뒤 편집이 저장되지 않는다 ({v})")
        if errs:
            note(f"U2 페이지 오류 {errs[:3]}"); errs.clear()
        # ---------------- U3
        pg2 = ctx.new_page(); pg2.on("pageerror", lambda e: errs.append("2:" + str(e)))
        pg2.goto(base + "/"); pg2.wait_for_timeout(1000); open_job(pg2)
        edit(pg, key, "qty", "3"); edit(pg2, key, "qty", "4")
        v = server_value(key, "qty")
        pg.reload(); pg.wait_for_timeout(2000)
        if not pg.evaluate("() => S.job"):
            open_job(pg)
        pg.wait_for_timeout(1500)
        c1 = pg.evaluate(f"() => {{ const r = S.rows.find(r => r.key === '{key}'); return r && r.user && r.user.qty; }}")
        note(f"U3 두 창 3 → 4 · 서버 {v} · 첫 창 새로 읽은 값 {c1}")
        if str(v) != "4" or str(c1) != "4":
            defect(f"U3 마지막 값이 남지 않는다 (서버 {v} · 창 {c1})")
        pg2.close()
        # ---------------- U4
        ctx2 = br.new_context(viewport={"width": 1600, "height": 950})
        p3 = ctx2.new_page(); e3 = []
        p3.on("pageerror", lambda e: e3.append(str(e)))
        p3.add_init_script("try{localStorage.setItem('pid.author','시뮬')}catch(e){}")
        p3.route("**/*", lambda route: (time.sleep(1.5), route.continue_()))
        t0 = time.time()
        p3.goto(base + "/", timeout=120000); p3.wait_for_timeout(500)
        p3.evaluate("() => { window.__paints = 0; const o = window.renderGrid; if (o) window.renderGrid = function(){ window.__paints++; return o.apply(this, arguments); }; }")
        try:
            open_job(p3, timeout=240000)
            paints = p3.evaluate("() => window.__paints")
            note(f"U4 느린 망 결과 열기 {time.time() - t0:.0f}초 · 목록 그리기 {paints}번 · 오류 {e3[:2]}")
        except Exception as e:                                     # noqa: BLE001
            defect(f"U4 느린 망에서 결과가 안 열린다: {str(e)[:120]}")
        ctx2.close()
        # ---------------- U5
        p4 = ctx.new_page(); e4 = []; d4 = []
        p4.on("pageerror", lambda e: e4.append(str(e)))
        p4.on("dialog", lambda d: (d4.append(d.message), d.accept()))
        p4.goto(base + "/"); p4.wait_for_timeout(1500)
        pdf = ROOT / "tests/data/synthetic/08b_tagged_same_size.pdf"
        stop()
        inp = p4.query_selector("#file")
        if inp:
            try:
                inp.set_input_files(str(pdf))
            except Exception as e:                                 # noqa: BLE001
                note(f"U5 파일 넣기 예외 {str(e)[:100]}")
            p4.wait_for_timeout(6000)
            busy = p4.evaluate("() => { const b = document.querySelector('#drop'); return b ? b.className + ' ' + b.innerText.slice(0, 80) : ''; }")
            note(f"U5 서버 꺼진 채 업로드 → 대화상자 {d4[:2]} · 드롭 상자 '{busy}' · 오류 {e4[:2]}")
            if not d4 and "올리는 중" in busy:
                defect("U5 서버가 꺼졌는데 업로드가 '올리는 중' 으로 남는다")
        start()
        pg.screenshot(path=str(OUT / "end.png"))
        br.close()
finally:
    stop()
    (OUT / "README.md").write_text("# 화면 돌발상황\n\n결함 " + str(len(DEFECTS)) + "\n\n"
                                   + "\n".join(f"- {x}" for x in FOUND) + "\n", encoding="utf-8")
    print(f"\n결함 {len(DEFECTS)}")
