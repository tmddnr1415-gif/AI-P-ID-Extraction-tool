"""hotfix49 — 화면 재배치(대시보드형) 전/후를 같은 자로 찍는다.

    python3 spike/ui_shots_redesign.py <data_dir> <job_id> <out_dir>

첫 화면 · 결과 화면(첫 장 · 목록) · 나란히 보기 · 좁은 창(1366x768) 을 찍고,
페이지 오류 · 목록 높이 · 행 수 · 사이드바 유무를 적는다.  실 DB 를 열지 않는다
(PID_DATA_DIR 로 사본을 가리킨다).
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
facts = {}
try:
    for _ in range(90):
        try: urllib.request.urlopen(f"http://127.0.0.1:{port}/home", timeout=2); break
        except Exception: time.sleep(1)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
        br = pw.chromium.launch(executable_path=exe if Path(exe).exists() else None)
        for (w, h, tag) in ((1920, 1080, "wide"), (1366, 768, "narrow")):
            pg = br.new_page(viewport={"width": w, "height": h})
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_timeout(2500)
            pg.screenshot(path=str(OUT / f"1_첫화면_{tag}.png"))
            pg.goto(f"http://127.0.0.1:{port}/#{JOB}")
            pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.pages && S.pages.length > 0", timeout=180000)
            pg.wait_for_timeout(2500)
            if pg.evaluate("() => !!S.side"):
                pg.click("#rev-switch button.side"); pg.wait_for_timeout(1200)
            pg.screenshot(path=str(OUT / f"2_결과_{tag}.png"))
            f = pg.evaluate("""() => ({
                rows: document.querySelectorAll('#grid tbody tr').length,
                grid_h: Math.round((document.querySelector('#gridwrap')||{getBoundingClientRect:()=>({height:0})}).getBoundingClientRect().height),
                stage_w: Math.round(document.querySelector('#stage').getBoundingClientRect().width),
                stage_h: Math.round(document.querySelector('#stage').getBoundingClientRect().height),
                sidebar: !!document.querySelector('#sidebar') && getComputedStyle(document.querySelector('#sidebar')).display !== 'none',
                hscroll: document.documentElement.scrollWidth > window.innerWidth + 1,
            })""")
            pg.click("#rev-switch button.side"); pg.wait_for_timeout(2500)
            pg.screenshot(path=str(OUT / f"3_나란히_{tag}.png"))
            f["side_on"] = pg.evaluate("() => !!S.side")
            pg.click("#rev-switch button.side"); pg.wait_for_timeout(800)
            f["errors"] = errs[:5]
            facts[tag] = f
            pg.close()
        # 눌러서 확인 — 메뉴 접기 · 그래프 툴팁 · 메뉴의 프로젝트 → 결과 · 홈 단추
        pg = br.new_page(viewport={"width": 1920, "height": 1080})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"http://127.0.0.1:{port}/"); pg.wait_for_timeout(2500)
        act = {}
        act["collapsed_at_start"] = pg.evaluate("() => document.body.classList.contains('nav-collapsed')")
        pg.click("#home .nav-toggle, .intake .nav-toggle"); pg.wait_for_timeout(400)
        act["collapsed_after_click"] = pg.evaluate("() => document.body.classList.contains('nav-collapsed')")
        act["remembered"] = pg.evaluate("() => localStorage.getItem('pid.nav.collapsed')")
        bar = pg.query_selector("#home-charts .bar")
        if bar:
            bar.hover(); pg.wait_for_timeout(300)
            act["tooltip"] = pg.evaluate("() => { const t = document.querySelector('#chart-tip'); return t && !t.classList.contains('hidden') ? t.textContent : null }")
        pg.screenshot(path=str(OUT / "4_접은메뉴_툴팁.png"))
        pg.click(".intake .nav-toggle"); pg.wait_for_timeout(400)
        link = pg.query_selector("#nav-projects .nav-item")
        if link:
            link.click()
            pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.pages && S.pages.length > 0", timeout=180000)
            pg.wait_for_timeout(1500)
            act["nav_project_opens"] = pg.evaluate("() => S.job.id")
            act["tabs_visible"] = pg.evaluate("() => getComputedStyle(document.querySelector('#tabs')).display !== 'none'")
            pg.click("#nav-home"); pg.wait_for_timeout(1500)
            act["home_back"] = pg.evaluate("() => document.querySelector('#main').classList.contains('hidden')")
            act["tabs_hidden_on_home"] = pg.evaluate("() => getComputedStyle(document.querySelector('#tabs')).display === 'none'")
        act["errors"] = errs[:5]
        facts["actions"] = act
        pg.close()
        br.close()
finally:
    srv.terminate()
    try: srv.wait(10)
    except Exception: srv.kill()
(OUT / "facts.json").write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(facts, ensure_ascii=False))
