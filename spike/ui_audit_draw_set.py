"""L56 — LOGIC 작도 묶음 화면 자기검증 (크롬 · 사본 데이터 폴더 · 실 DB 를 열지 않는다).

  python3 spike/ui_audit_draw_set.py <비어 있는 데이터 폴더> <그림 출력 폴더>

새 그림(묶음으로 만들기) → Typical 장 더하기(행에 약어 · AND 하나) → 매크로 카드에서 그 타입을 놓기 → 받는 장 더하기 →
TO 칸에 참조를 적고 저장 → 상대 장 FM 이 저절로 채워짐(↗) → 묶음 검증(매크로 → Typical · FROM/TO 일치) → 화면 오류 0.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
data.mkdir(parents=True, exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT), PID_PAGE_WARM="0", PID_LOGIC_WARM="0", PID_ROWS_WARM="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = f"http://127.0.0.1:{port}"
FOUND = []


def note(x):
    print(x, flush=True)
    FOUND.append(x)


def get(path):
    return json.loads(urllib.request.urlopen(base + path).read())


try:
    for _ in range(90):
        try:
            urllib.request.urlopen(base + "/version", timeout=2)
            break
        except Exception:
            time.sleep(1)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        pg = br.new_page(viewport={"width": 1600, "height": 950})
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.on("dialog", lambda d: d.accept())
        pg.goto(base + "/logic/draw?user=%ED%99%8D%EA%B8%B8%EB%8F%99")
        pg.wait_for_selector("#palette button")
        N = 50

        def ry(n):
            return 70.0 + ((n - 1) % N) * 11.3 + 11.3 / 2

        def svg_click(x, y, dbl=False):
            box = pg.eval_on_selector("#svg", "e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }")
            cx, cy = box[0] + x / 1191.0 * box[2], box[1] + y / 842.0 * box[3]
            (pg.mouse.dblclick if dbl else pg.mouse.click)(cx, cy)

        def cell(side, n, f, text):
            pg.dblclick(f".cell[data-side='{side}'][data-n='{n}'][data-f='{f}']")
            pg.wait_for_selector("#cellin:not([hidden])")
            pg.fill("#cellin", text)
            pg.keyboard.press("Enter"); pg.wait_for_timeout(60); pg.keyboard.press("Escape")

        def place(kind, x, y):
            pg.click(f"#palette button:has-text('{kind}')")
            pg.wait_for_selector("#props-card:not([hidden])")
            pg.fill("#p-x", str(x)); pg.dispatch_event("#p-x", "change")
            pg.fill("#p-y", str(y)); pg.dispatch_event("#p-y", "change")

        def save():
            pg.click("#save"); pg.wait_for_function("document.querySelector('#status').textContent.includes('저장됨')")
        # 1) 주 장 (G001) → 묶음으로
        pg.click("#new"); pg.fill("#m-name", "묶음 자기검증"); pg.fill("#m-sheet", "G001"); pg.click("#m-ok")
        pg.wait_for_function("document.querySelector('#pick').value !== ''")
        main_id = pg.eval_on_selector("#pick", "e => e.value")
        pg.fill("#f-doc", "1-1"); pg.dispatch_event("#f-doc", "input"); pg.fill("#f-title", "MAIN SHEET"); pg.dispatch_event("#f-title", "input"); save()
        pg.click("#set-make"); pg.wait_for_selector("#set-list li[data-id]")
        sid = get(f"/logic/api/drawings/{main_id}")["set"]
        note(f"묶음 만듦 {sid} · 장 {pg.locator('#set-list li[data-id]').count()}")
        # 2) Typical 장 (T001)
        pg.click("#set-add"); pg.fill("#m-sheet", "T001"); pg.fill("#m-name", "MOV TYPICAL"); pg.check("#m-typ"); pg.click("#m-ok")
        pg.wait_for_function(f"document.querySelector('#pick').value !== '{main_id}'")
        typ_id = pg.eval_on_selector("#pick", "e => e.value")
        pg.fill("#f-title", "MOV BLOCK (OPEN CLOSE) <TYPE-III-1>"); pg.dispatch_event("#f-title", "input"); pg.fill("#f-doc", "1-2"); pg.dispatch_event("#f-doc", "input")
        cell("left", 1, "kks", "AOPEN"); cell("left", 1, "desc", "AUTO OPEN"); cell("left", 2, "kks", "ACLOSE"); cell("left", 2, "desc", "AUTO CLOSE")
        cell("right", N + 1, "kks", "CMD"); cell("right", N + 1, "desc", "OPEN COMMAND")
        place("AND", 500, round(ry(1) - 4.5 + 5.65, 2))     # 1 · 2 행 사이
        pg.keyboard.press("w")
        svg_click(320, ry(1)); svg_click(500, ry(1)); svg_click(320, ry(2)); svg_click(500, ry(2))
        svg_click(516, (ry(1) + ry(2)) / 2); svg_click(700, (ry(1) + ry(2)) / 2); svg_click(700, ry(N + 1)); svg_click(870, ry(N + 1))
        pg.keyboard.press("v")
        save()
        note(f"Typical 장 {typ_id} · 블록 {len(get(f'/logic/api/drawings/{typ_id}')['blocks'])} · 선 {len(get(f'/logic/api/drawings/{typ_id}')['wires'])} · typical {get(f'/logic/api/drawings/{typ_id}')['typical']}")
        # 3) 주 장으로 돌아가 매크로 카드에서 타입을 놓는다
        pg.click(f"#set-list li[data-id='{main_id}']")
        pg.wait_for_function(f"document.querySelector('#pick').value === '{main_id}'")
        pg.wait_for_selector("#macro-list button")
        mtext = pg.text_content("#macro-list button")
        pg.click("#macro-list button >> nth=0")
        pg.wait_for_selector("#blocks .blk.macro")
        mac = pg.evaluate("() => { const b = S.doc.blocks.find(b => b.kind === 'MACRO'); return [b.param.typ, b.param.pins_in.map(p => p.name), b.param.pins_out.map(p => p.name), b.x, b.y, b.w, b.h, b.id]; }")
        note(f"매크로 카드 '{mtext.strip()[:40]}' → 블록 typ {mac[0]} · 입력 {mac[1]} · 출력 {mac[2]}")
        # 행 5 · 6 → 매크로 입력 · 출력 → 행 N+1
        ports = pg.evaluate("() => { const b = S.doc.blocks.find(b => b.kind === 'MACRO'); return ports(b); }")
        pin = {p[3]: p for p in ports}
        cell("left", 5, "desc", "PB OPEN"); cell("left", 6, "desc", "PB CLOSE"); cell("right", N + 1, "desc", "MOV OPEN CMD")
        pg.keyboard.press("w")
        svg_click(320, ry(5)); svg_click(pin["AOPEN"][0], pin["AOPEN"][1])
        svg_click(320, ry(6)); svg_click(pin["ACLOSE"][0], pin["ACLOSE"][1])
        svg_click(pin["CMD"][0], pin["CMD"][1]); svg_click(800, pin["CMD"][1]); svg_click(800, ry(N + 1)); svg_click(870, ry(N + 1))
        pg.keyboard.press("v")
        # 4) 받는 장 (G002) 과 TO 참조 → 자동 잇기
        save()
        pg.click("#set-add"); pg.fill("#m-sheet", "G002"); pg.fill("#m-name", "RECEIVER"); pg.click("#m-ok")
        pg.wait_for_function(f"document.querySelector('#pick').value !== '{main_id}'")
        rx_id = pg.eval_on_selector("#pick", "e => e.value")
        pg.fill("#f-doc", "1-3"); pg.dispatch_event("#f-doc", "input"); save()
        pg.click(f"#set-list li[data-id='{main_id}']")
        pg.wait_for_function(f"document.querySelector('#pick').value === '{main_id}'")
        cell("right", N + 1, "to", "G002-2")
        save()
        pg.wait_for_timeout(300)
        rx = get(f"/logic/api/drawings/{rx_id}")
        note(f"자동 잇기: G002 2행 FM = '{(rx['left'].get('2') or {}).get('fm')}' · 설명 '{(rx['left'].get('2') or {}).get('desc')}'")
        linked = pg.evaluate("() => document.querySelectorAll('.cell.linked').length")
        go = pg.evaluate("() => document.querySelectorAll('.golink').length")
        note(f"연결 표시: linked 칸 {linked} · ↗ {go}")
        pg.screenshot(path=str(OUT / "1_main.png"))
        # ↗ 누르면 G002 2행으로
        pg.click(".golink >> nth=0")
        pg.wait_for_function(f"document.querySelector('#pick').value === '{rx_id}'")
        flash = pg.evaluate("() => document.querySelectorAll('#overlay .rowflash').length")
        note(f"↗ 이동: 지금 장 {pg.input_value('#f-sheet')} · 행 깜박임 {flash}")
        pg.screenshot(path=str(OUT / "2_receiver.png"))
        # 5) 묶음 검증
        pg.click("#set-verify")
        pg.wait_for_function("!document.querySelector('#set-verify').disabled", timeout=180000)
        note("묶음 검증: " + pg.text_content("#verify-sum") + " — " + " ".join(pg.text_content("#verify-out").split())[:300])
        pg.screenshot(path=str(OUT / "3_verified.png"))
        vs = json.loads(urllib.request.urlopen(urllib.request.Request(f"{base}/logic/api/drawings/sets/{sid}/verify", data=b"{}", headers={"Content-Type": "application/json"})).read())
        macs = [b.get("macro") for sh in vs["sheets"] for b in sh.get("blocks", []) if b["kind"] == "MACRO"]
        note(f"서버 검증: ok {vs['ok']} · 장 {vs['read']}/{vs['drawn']} · FROM/TO 불일치 {vs['fromto_bad']} · 매크로 {macs}")
        note(f"페이지 오류 {len(errors)}" + ("" if not errors else " — " + " | ".join(errors[:5])))
        br.close()
finally:
    srv.terminate()
    try:
        srv.wait(timeout=10)
    except Exception:
        srv.kill()
(OUT / "result.txt").write_text("\n".join(FOUND), encoding="utf-8")
