"""L63 — 공통 Typical 사전 화면: 빈 서버에서도 목록이 있고 · 꺼내 고치고 · 사전에 저장 · 매크로 카드에 보임 · 원래대로 (크롬 · 빈 데이터).

  python3 spike/ui_audit_l63.py <빈 데이터 폴더> <출력 폴더>
"""
from __future__ import annotations

import json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = Path(sys.argv[1]).resolve(); OUT = Path(sys.argv[2]).resolve(); OUT.mkdir(parents=True, exist_ok=True); data.mkdir(parents=True, exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT), PID_PAGE_WARM="0", PID_LOGIC_WARM="0", PID_ROWS_WARM="0", PID_TYPICAL_SEED="1")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = f"http://127.0.0.1:{port}"; LOG = []
def note(x): print(x, flush=True); LOG.append(x)
try:
    for _ in range(120):
        try: urllib.request.urlopen(base + "/version", timeout=2).read(); break
        except Exception: time.sleep(0.5)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        pg = br.new_page(viewport={"width": 1700, "height": 1000}); errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" and "ERR_ABORTED" not in m.text else None)
        pg.add_init_script("try { localStorage.setItem('pid.author', '홍길동'); } catch (e) {}")
        pg.goto(f"{base}/logic/draw"); pg.wait_for_function("typeof S !== 'undefined' && S.sym", timeout=30000); time.sleep(0.5)
        pg.click("#typlib"); pg.wait_for_selector(".dw-typtable tbody tr"); time.sleep(0.3)
        n = pg.locator(".dw-typtable tbody tr").count()
        note(f"빈 서버 — Typical 사전 {n}개 (처음부터 들어 있음)")
        pg.screenshot(path=str(OUT / "1_list.png"))
        pg.fill("#typ-q", "MOV BLOCK (OPEN"); time.sleep(0.3)
        vis = pg.evaluate("() => [...document.querySelectorAll('.dw-typtable tbody tr')].filter(t => !t.hidden).map(t => t.cells[1].textContent)")
        note(f"찾기 'MOV BLOCK (OPEN' → {vis}")
        pg.locator(".dw-typtable tbody tr:not([hidden]) .t-open").first.click()
        pg.wait_for_function("() => S.doc && S.doc.set === '7e7e00000063'", timeout=20000); time.sleep(1.0)
        note(f"꺼냄 → {pg.evaluate('S.doc.sheet_no')} {pg.evaluate('S.doc.title')} · 블록 {pg.evaluate('S.doc.blocks.length')} · 카드 보임 {pg.is_visible('#typ-card')}")
        pg.screenshot(path=str(OUT / "2_opened.png"))
        # 고치기 — 입력 행 하나의 설명을 바꾸고 기호 하나 더함
        k = pg.evaluate("() => Object.keys(S.doc.left).find(k => S.doc.left[k].desc)")
        pg.evaluate(f"() => {{ pushUndo(); S.doc.left['{k}'].desc = 'LOCAL/REMOTE (EDITED)'; markDirty(); render(); }}")
        pg.click("#typ-save")
        pg.wait_for_function("() => (document.querySelector('#status').textContent || '').includes('사전에 저장됨')", timeout=60000); time.sleep(0.5)
        note(f"사전에 저장 → 카드: {pg.inner_text('#typ-say')[:120]!r}")
        pg.screenshot(path=str(OUT / "3_saved.png"))
        pg.click("#typlib"); pg.wait_for_selector(".dw-typtable tbody tr"); time.sleep(0.3)
        users = pg.evaluate("() => [...document.querySelectorAll('.dw-typtable .t-user')].map(e => e.closest('tr').cells[1].textContent + ' · ' + e.textContent)")
        note(f"목록에 고침 표시 → {users}")
        pg.screenshot(path=str(OUT / "4_list_edited.png"))
        pg.click("#m-ok"); time.sleep(0.2)
        # 새 프로젝트 묶음 — 매크로 카드에 사전 Typical 이 처음부터 보인다
        pg.click("#new"); pg.wait_for_selector("#modal:not([hidden])"); time.sleep(0.2)
        try: pg.fill("#m-name", "새 프로젝트 장")
        except Exception: pass
        pg.click("#m-ok"); pg.wait_for_function("() => S.doc && S.doc.set !== '7e7e00000063'", timeout=20000); time.sleep(0.5)
        pg.click("#set-make"); pg.wait_for_function("() => S.setInfo", timeout=20000); time.sleep(0.5)
        mc = pg.evaluate("() => [...document.querySelectorAll('#macro-list button')].map(b => b.textContent)")
        note(f"새 묶음의 매크로 카드 → {len(mc)}개 (예: {mc[:3]})")
        pg.locator("#macro-list button", has_text="MOV BLOCK (OPEN").first.click(); time.sleep(1.5)
        mb = pg.evaluate("() => { const b = S.doc.blocks.find(b => b.kind === 'MACRO'); return b ? [b.param.typ, b.param.pins_in.map(p => p.name)] : null; }")
        note(f"그 매크로를 놓음 → Typical {mb[0]} · 입력 단자 {mb[1]}")
        pg.screenshot(path=str(OUT / "5_new_project_macro.png"))
        # 원래대로
        pg.click("#typlib"); pg.wait_for_selector(".dw-typtable .t-rev"); pg.locator(".dw-typtable .t-rev").first.click(); time.sleep(1.0)
        left = pg.evaluate("async () => (await api('/logic/api/drawings/typicals')).items.filter(i => i.origin === 'user').length")
        note(f"원래대로 → 고친 Typical {left}개")
        note(f"페이지 오류 {len(errors)} {errors[:3]}")
        br.close()
finally:
    srv.terminate(); (OUT / "result.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
