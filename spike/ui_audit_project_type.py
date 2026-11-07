"""hotfix60 — 새 프로젝트를 입찰 / 실행으로 만들면 그 종류가 화면 곳곳에 분명히 적히는가 (눌러서 확인).

    python3 spike/ui_audit_project_type.py out/hotfix60/ui

★ 실 DB 를 열지 않는다 (빈 임시 데이터 폴더로 서버를 띄운다).
"""
from __future__ import annotations
import json, os, socket, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "out/hotfix60/ui"); OUT.mkdir(parents=True, exist_ok=True)
FOUND = []
def note(s): print(s, flush=True); FOUND.append(s)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
data = Path(tempfile.mkdtemp(prefix="ptype-"))
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(60):
        try: urllib.request.urlopen(f"http://127.0.0.1:{port}/version", timeout=2); break
        except Exception: time.sleep(1)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        pg = br.new_page(viewport={"width": 1600, "height": 1000}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"http://127.0.0.1:{port}/"); pg.wait_for_timeout(2000)

        def author():
            ab = pg.query_selector(".author-bar")
            if ab and ab.is_visible():
                ab.query_selector("input").fill("홍길동"); ab.query_selector("button.ok").click()
                pg.wait_for_timeout(800)

        def state():
            return pg.evaluate("""() => ({
                type: document.querySelector('#proj-type').innerText,
                pick: [...document.querySelectorAll('#proj-pick option')].map(o => o.textContent),
                list: [...document.querySelectorAll('details.pjt summary')].map(s => s.innerText.replace(/\\s+/g,' ')),
                nav: [...document.querySelectorAll('#nav-projects a.nav-item')].map(a => a.innerText.replace(/\\s+/g,' ')),
                radio: (document.querySelector('input[name=mode]:checked')||{}).value })""")

        def make(name, mode_label):
            pg.click("#proj-new-btn"); pg.wait_for_timeout(300)
            if mode_label:
                pg.check(f'input[name=mode][value={mode_label}]'); pg.wait_for_timeout(300)
            mid = state()
            pg.fill("#proj-name", name); pg.click("#proj-save"); pg.wait_for_timeout(1500)
            author()
            return mid, state()

        mid, after = make("TEST BID", "bid")
        note(f"① 새 프로젝트 → 입찰 고름 (만들기 전): {mid['type']!r}")
        pg.query_selector(".intake-card").screenshot(path=str(OUT / "1_만들기전_입찰.png"))
        note(f"① 만든 뒤: 표기 {after['type']!r} · 라디오 {after['radio']!r} · 고르는 상자 {after['pick'][2:]}")
        pg.query_selector(".intake-card").screenshot(path=str(OUT / "1_만든뒤_입찰.png"))
        mid, after = make("TEST EPC", "epc")
        note(f"② 실행으로 만든 뒤: 표기 {after['type']!r} · 라디오 {after['radio']!r}")
        pg.query_selector(".intake-card").screenshot(path=str(OUT / "2_만든뒤_실행.png"))
        mid, after = make("TEST AUTO", None)
        note(f"③ 고르지 않고 만든 뒤: 표기 {after['type']!r}")
        # ④ 선택한 프로젝트의 종류를 라디오로 바꾸면 곳곳이 따라가는가
        pg.select_option("#proj-pick", "TEST BID"); pg.wait_for_timeout(500)
        b = state(); note(f"④ TEST BID 고름: 표기 {b['type']!r} · 라디오 {b['radio']!r}")
        pg.check('input[name=mode][value=epc]'); pg.wait_for_timeout(300); author(); pg.wait_for_timeout(1200)
        c = state()
        note(f"④ 실행으로 바꿈: 표기 {c['type']!r} · 상자 {c['pick'][2:]} · 목록 {c['list']} · 메뉴 {c['nav']}")
        pg.screenshot(path=str(OUT / "4_첫화면_전체.png"))
        meta = {n: json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/projects/{urllib.request.quote(n)}")).get("mode")
                for n in ("TEST BID", "TEST EPC", "TEST AUTO")}
        note(f"⑤ 서버 장부의 선언: {meta}")
        note("화면 오류: " + (" | ".join(errs) if errs else "없음"))
        br.close()
finally:
    srv.terminate(); srv.wait(timeout=10)
(OUT / "README.md").write_text("# hotfix60 화면 자기검증 — 프로젝트 도면 종류 표기\n\n" + "\n".join("- " + x for x in FOUND) + "\n", encoding="utf-8")
