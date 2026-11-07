"""L62 — FM/TO 칸 상태 표기(연결 · 미작성 · 불일치 · 설명 다름)와 미작성 시트를 만들면 저절로 이어지는지 (크롬 · 사본 데이터).

  python3 spike/ui_audit_l62.py <알다프라 그림 묶음이 든 데이터 폴더(사본)> <출력 폴더>
"""
from __future__ import annotations

import json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = Path(sys.argv[1]).resolve(); OUT = Path(sys.argv[2]).resolve(); OUT.mkdir(parents=True, exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT), PID_PAGE_WARM="0", PID_LOGIC_WARM="0", PID_ROWS_WARM="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = f"http://127.0.0.1:{port}"; LOG = []
def note(x): print(x, flush=True); LOG.append(x)
try:
    for _ in range(120):
        try: urllib.request.urlopen(base + "/version", timeout=2).read(); break
        except Exception: time.sleep(0.5)
    st = json.loads(urllib.request.urlopen(base + "/logic/api/drawings/sets").read())["items"][0]
    sheets = {q["sheet_no"]: q["id"] for q in st["sheets"]}
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        pg = br.new_page(viewport={"width": 1700, "height": 1000}); errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" and "ERR_ABORTED" not in m.text else None)
        pg.add_init_script("try { localStorage.setItem('pid.author', '홍길동'); } catch (e) {}")
        pg.goto(f"{base}/logic/draw#d={sheets['FG_G-201']}")
        pg.wait_for_function("typeof S !== 'undefined' && S.doc && S.setInfo", timeout=30000); time.sleep(0.8)
        cnt = lambda: pg.evaluate("() => { const c = {}; document.querySelectorAll('#svg .lnkbadge').forEach(g => { const k = [...g.classList].find(x => x.startsWith('st-')); c[k] = (c[k] || 0) + 1; }); return c; }")
        miss = pg.evaluate("() => Object.keys(S.setInfo.links.missing || {})")
        note(f"FG_G-201 칸 표기 {cnt()} · 미작성 시트 목록 {miss}")
        pg.screenshot(path=str(OUT / "1_states.png"))
        def zoom_shot(sel, fn, left=520, up=60, w=640, h=230):
            pg.evaluate("setZoom(3)"); time.sleep(0.3)
            e = pg.locator(sel).first; e.scroll_into_view_if_needed(); time.sleep(0.3); bb = e.bounding_box()
            pg.screenshot(path=str(OUT / fn), clip={"x": max(0, bb["x"] - left), "y": max(0, bb["y"] - up), "width": w, "height": h})
            pg.evaluate("fitZoom()"); time.sleep(0.2)
        zoom_shot("#svg .lnkbadge.st-miss", "2_badge_zoom.png", up=30, h=330)
        # 불일치 하나 만들기 — 62행 TO 를 FG_G-101-13 (그 행의 FM 은 이미 FG_G-201-61) 로
        pg.evaluate("() => { S.doc.right['62'] = {desc: 'TEST SIGNAL', kks: '', to: 'FG_G-101-13'}; markDirty(); render(); }")
        pg.fill("#who", "홍길동"); pg.click("#save"); pg.wait_for_function("() => !S.dirty", timeout=20000); time.sleep(1.0)
        note(f"62행 TO 를 FG_G-101-13 으로 (그 행 FM 은 61행) → 표기 {cnt()}")
        zoom_shot("#svg .lnkbadge.st-bad", "3_bad_zoom.png", left=420, w=820, h=140)
        pg.evaluate("() => { delete S.doc.right['62']; markDirty(); render(); }")
        pg.click("#save"); pg.wait_for_function("() => !S.dirty", timeout=20000); time.sleep(1.0)
        # 미작성 시트 하나를 목록에서 만든다
        name = "GT_G-111"
        pg.click(f"#set-list .dw-miss button[data-sheet='{name}']")
        pg.wait_for_selector("#modal:not([hidden])"); time.sleep(0.3)
        pg.screenshot(path=str(OUT / "4_make_modal.png"))
        pg.click("#m-ok")
        pg.wait_for_function(f"() => S.doc && S.doc.sheet_no === '{name}'", timeout=20000); time.sleep(1.2)
        left = pg.evaluate("() => S.doc.left")
        note(f"{name} 만듦 → 입력 행 저절로 채워짐 {left}")
        pg.screenshot(path=str(OUT / "5_new_sheet.png"))
        zoom_shot(".cell[data-side='left'][data-n='12'][data-f='fm']", "5b_new_sheet_zoom.png", left=40, up=60, w=640, h=140)
        pg.locator("#set-list li", has_text="FG_G-201").first.click()
        pg.wait_for_function("() => S.doc && S.doc.sheet_no === 'FG_G-201'", timeout=20000); time.sleep(1.0)
        miss2 = pg.evaluate("() => Object.keys(S.setInfo.links.missing || {})")
        note(f"FG_G-201 로 돌아옴 → 표기 {cnt()} · 미작성 시트 {len(miss)} → {len(miss2)} ({name} 빠짐 {name not in miss2})")
        pg.screenshot(path=str(OUT / "6_after.png"))
        zoom_shot(".cell[data-side='right'][data-n='102'][data-f='to']", "6b_after_zoom.png", left=420, up=40, w=820, h=150)
        note(f"페이지 오류 {len(errors)} {errors[:3]}")
        br.close()
finally:
    srv.terminate(); (OUT / "result.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
