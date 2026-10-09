"""hotfix66 — 도면 상자를 눌러 SCT · VENDOR · 둘 다 아님(식별 지우기)을 고르는가 (눌러서 확인).

    python3 spike/ui_audit_dismiss.py <data_dir 사본> <job> out/hotfix66/ui_dismiss

★ 실 DB 를 열지 않는다 — 넘긴 데이터 폴더(사본)를 PID_DATA_DIR 로 가리킨다.
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
FOUND = []
def note(x): print(x, flush=True); FOUND.append(x)
def srow(key):
    return next(r for r in json.loads(urllib.request.urlopen(f"{base}/jobs/{JOB}/rows?tab=ALL").read()) if r["key"] == key)
def summary():
    return json.loads(urllib.request.urlopen(f"{base}/jobs/{JOB}/scope_summary").read())

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
        pg.add_init_script("try{localStorage.removeItem('pid.split')}catch(e){}")
        pg.goto(base + "/?embed=1&mode=epc&user=" + quote("홍길동")); pg.wait_for_timeout(1500)
        pg.evaluate(f"open('{JOB}')")
        pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.pages && S.pages.length > 0", timeout=180000)
        pg.wait_for_timeout(2500)
        pg.evaluate("() => { if (S.side) toggleSide(); }"); pg.wait_for_timeout(500)
        pg.evaluate("() => fit()"); pg.wait_for_timeout(600)
        keys = pg.evaluate("() => S.rows.filter(r => r.page_no === S.page.page_no && !r.removed && !r.deleted && r.values.type).map(r => r.key)")
        k1, k2 = keys[0], keys[1]
        before = summary()
        # ① 상자를 누르면 판
        pg.click(f'rect.det[data-key="{k1}"]', force=True); pg.wait_for_timeout(700)
        vis = pg.query_selector(".scopepop") is not None
        txt = pg.inner_text(".scopepop") if vis else ""
        note(f"① 상자 누름 → 판 {vis} · '{txt.splitlines()[0] if txt else ''}' · 단추 {[b.inner_text() for b in pg.query_selector_all('.scopepop .sp-b')]}")
        bb = pg.query_selector(f'rect.det[data-key="{k1}"]').bounding_box(); pb = pg.query_selector(".scopepop").bounding_box()
        pg.screenshot(path=str(OUT / "1_판.png"), clip={"x": max(0, bb["x"] - 200), "y": max(0, min(bb["y"], pb["y"]) - 80),
                                                        "width": 760, "height": 300})
        # ② 둘 다 아님 — 식별 지우기
        pg.click('.scopepop .sp-b[data-sp="none"]'); pg.wait_for_timeout(2500)
        r1 = srow(k1)
        after = summary()
        note(f"② 둘 다 아님 → 서버 removed {r1.get('removed')} · 사유 {(r1.get('reject') or {}).get('class') if isinstance(r1.get('reject'), dict) else r1.get('reject')}"
             f" · 작성자 {(r1.get('reject') or {}).get('author') if isinstance(r1.get('reject'), dict) else ''}"
             f" · 양식에 나가는 행 {before.get('delivered', before)} → {after.get('delivered', after)}")
        tr_cls = pg.get_attribute(f'#body tr[data-key="{k1}"]', "class") or ""
        box_cls = pg.get_attribute(f'rect.det[data-key="{k1}"]', "class")
        note(f"   목록 행 class '{tr_cls}' · 도면 상자 class '{box_cls}'")
        pg.screenshot(path=str(OUT / "2_지운뒤.png"), clip={"x": max(0, bb["x"] - 200), "y": max(0, bb["y"] - 120), "width": 760, "height": 300})
        # ③ 다시 누르면 되돌리기
        pg.click(f'rect.det[data-key="{k1}"]', force=True); pg.wait_for_timeout(700)
        btns = [b.inner_text() for b in pg.query_selector_all('.scopepop .sp-b')]
        pg.click('.scopepop .sp-b[data-sp="restore"]'); pg.wait_for_timeout(2500)
        note(f"③ 다시 누름 → 단추 {btns} → 되돌리기 → 서버 removed {srow(k1).get('removed')}")
        # ④ SCT / VENDOR 고르기
        pg.click(f'rect.det[data-key="{k2}"]', force=True); pg.wait_for_timeout(700)
        names = pg.evaluate("() => [...document.querySelectorAll('.scopepop .sp-name option')].map(o => o.value)")
        if len(names) > 1:
            pg.select_option(".scopepop .sp-name", names[1])
        pg.click('.scopepop .sp-b[data-sp="vendor"]'); pg.wait_for_timeout(2000)
        r2 = srow(k2)
        note(f"④ VENDOR 고름 → 서버 user.scope '{(r2.get('user') or {}).get('scope')}' · 작성자 {(r2.get('edited_by') or {}).get('scope', {}).get('author')} · 판 닫힘 {pg.query_selector('.scopepop') is None}")
        # ⑤ Esc 로 닫힘 · 근거 패널 단추
        pg.click(f'rect.det[data-key="{k2}"]', force=True); pg.wait_for_timeout(900)
        evb = pg.query_selector('#evidence button.sc-none') is not None
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        note(f"⑤ Esc → 판 닫힘 {pg.query_selector('.scopepop') is None} · 근거 패널 '둘 다 아님' 단추 {evb}")
        # ⑥ 묶음 — Shift 로 둘 고르고 묶음 판에서 지우기
        k3, k4 = keys[2], keys[3]
        pg.click(f'rect.det[data-key="{k3}"]', force=True); pg.wait_for_timeout(500)
        pg.click(f'rect.det[data-key="{k4}"]', force=True, modifiers=["Shift"]); pg.wait_for_timeout(600)
        pg.click("#mc-none"); pg.wait_for_timeout(3000)
        note(f"⑥ 묶음 2개 → 서버 removed {srow(k3).get('removed')} / {srow(k4).get('removed')}")
        note(f"페이지 오류 {len(errs)} {errs[:3]}")
        br.close()
finally:
    srv.terminate()
(OUT / "audit.txt").write_text("\n".join(FOUND), encoding="utf-8")
