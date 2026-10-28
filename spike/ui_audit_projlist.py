"""hotfix61·62 — 첫 화면 '저장된 프로젝트' 카드 · 리비전 타임라인을 찍고 눌러서 확인한다.

    python3 spike/ui_audit_projlist.py <data_dir 사본> out/hotfix61/ui

★ 실 DB 를 열지 않는다 — 넘긴 데이터 폴더(사본)를 PID_DATA_DIR 로 가리킨다.
   빈 프로젝트(입찰)를 하나 더 만들어 '분석 없음' 카드도 찍는다.
"""
from __future__ import annotations
import json, os, socket, subprocess, sys, time, urllib.request, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data, OUT = Path(sys.argv[1]), Path(sys.argv[2] if len(sys.argv) > 2 else "out/hotfix61/ui")
OUT.mkdir(parents=True, exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
FOUND = []
def note(x): print(x, flush=True); FOUND.append(x)
base = f"http://127.0.0.1:{port}"
try:
    for _ in range(90):
        try: urllib.request.urlopen(base + "/home", timeout=2); break
        except Exception: time.sleep(1)
    for name, mode in (("EMPTY BID", "bid"), ("QFE", "epc")):
        try:
            urllib.request.urlopen(urllib.request.Request(base + "/projects", data=urllib.parse.urlencode({"name": name}).encode(), method="POST"))
        except Exception: pass
        urllib.request.urlopen(urllib.request.Request(base + f"/projects/{urllib.parse.quote(name)}/mode",
            data=urllib.parse.urlencode({"mode": mode, "author": "홍길동"}).encode(), method="PATCH"))
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        for (w, h, tag) in ((1920, 1080, "wide"), (1366, 768, "narrow")):
            pg = br.new_page(viewport={"width": w, "height": h}); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
            pg.goto(base + "/"); pg.wait_for_selector("details.pj-card", timeout=20000)
            # hotfix62 — 예전 분석의 도면 사실은 서버가 뒤에서 채운다 (분석 하나 2~5초) — 다 찰 때까지
            for _ in range(40):
                if not pg.evaluate("() => /읽는 중/.test(document.querySelector('#joblist').innerText)"): break
                pg.wait_for_timeout(1500)
            pg.wait_for_timeout(800)
            card = pg.query_selector(".list-card"); card.scroll_into_view_if_needed()
            card.screenshot(path=str(OUT / f"1_목록_{tag}.png"))
            facts = pg.evaluate("""() => ({
              cards: [...document.querySelectorAll('details.pj-card')].map(d => ({
                 cls: d.className, open: d.open,
                 head: d.querySelector('summary').innerText.replace(/\\s+/g,' '),
                 revs: [...d.querySelectorAll('.rv-tl')].map(r => r.innerText.replace(/\\s+/g,' ')) })),
              hscroll: document.documentElement.scrollWidth > window.innerWidth + 1,
              listOverflowX: (() => { const j = document.querySelector('#joblist'); return j.scrollWidth > j.clientWidth + 1; })(),
            })""")
            note(f"[{tag}] 카드 {len(facts['cards'])} · 가로 스크롤 {facts['hscroll']} · 목록 가로 넘침 {facts['listOverflowX']}")
            for c in facts["cards"]:
                note(f"   {c['cls']} open={c['open']} :: {c['head']}")
                for r in c["revs"]: note(f"      - {r}")
            a = pg.query_selector("details.pj-card a.revrow")
            if a:
                a.hover(); pg.wait_for_timeout(400)
                op = pg.evaluate("(el) => getComputedStyle(el.querySelector('.rv-open')).opacity", a)
                note(f"[{tag}] 마우스 올림 → '열기 →' 불투명도 {op}")
                card.screenshot(path=str(OUT / f"2_마우스_{tag}.png"))
            # 접기 / 펼치기
            pg.click("details.pj-card summary .pj-name"); pg.wait_for_timeout(300)
            opened = pg.evaluate("() => document.querySelector('details.pj-card').open")
            note(f"[{tag}] 첫 카드 접힘 → open={opened}")
            pg.click("details.pj-card summary .pj-name"); pg.wait_for_timeout(300)
            if tag == "wide" and a:
                pg.click("details.pj-card a.revrow >> nth=0")
                pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.pages && S.pages.length > 0", timeout=180000)
                nrows = pg.evaluate("() => S.rows ? S.rows.length : 0")
                note(f"[{tag}] 리비전 누름 → 결과 열림 (행 {nrows})")
            note(f"[{tag}] 페이지 오류 {len(errs)} {errs[:3]}")
            pg.close()
        br.close()
finally:
    srv.terminate()
    (OUT / "audit.txt").write_text("\n".join(FOUND) + "\n", encoding="utf-8")
