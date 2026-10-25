"""L54 — LOGIC 작도 화면 자기검증 (크롬 · 사본 데이터 폴더 · 실 DB 를 열지 않는다).

  python3 spike/ui_audit_draw.py <비어 있는 데이터 폴더> <그림 출력 폴더>

새 그림 → 기호 셋 놓기 → 선 넷 긋기(행 ↔ 막대 · 출력 → 행) → 표 칸 적기 → 저장 → 되읽기 검증(전부 같게 읽혀야) →
PDF/DXF 내려받기 → 분석 시트에서 가져오기(묶음이 있을 때) → 화면 오류 0.
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
        # 화면을 떠나며 끊긴 요청(ERR_ABORTED · LOGIC 검토 화면에서 작도로 돌아올 때)은 결함이 아니다 — 그것만 뺀다
        pg.on("requestfailed", lambda r: errors.append(f"요청 실패 {r.url.split('/',3)[-1]} — {r.failure}") if "ABORTED" not in str(r.failure) else None)
        pg.goto(base + "/logic/draw?user=%ED%99%8D%EA%B8%B8%EB%8F%99")
        pg.wait_for_selector("#palette button")
        note(f"팔레트 기호 {pg.locator('#palette button').count()}개")
        pg.screenshot(path=str(OUT / "1_empty.png"))
        # 새 그림
        pg.click("#new")
        pg.fill("#m-name", "자기검증 로직")
        pg.fill("#m-sheet", "LD-001")
        pg.click("#m-ok")
        pg.wait_for_function("document.querySelector('#pick').value !== ''")
        did = pg.eval_on_selector("#pick", "e => e.value")
        note(f"새 그림 {did} · 시트 이름 {pg.input_value('#f-sheet')}")

        def svg_click(x, y, dbl=False, button="left"):
            box = pg.eval_on_selector("#svg", "e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }")
            W, H = 1191.0, 842.0
            cx, cy = box[0] + x / W * box[2], box[1] + y / H * box[3]
            (pg.mouse.dblclick if dbl else pg.mouse.click)(cx, cy, button=button)

        def ry(n):
            return 70.0 + ((n - 1) % 50) * 11.3 + 11.3 / 2
        # 기호 셋 — 팔레트를 누르면 가운데에 놓인다 → 속성 판에서 자리를 적는다
        def place(kind, x, y):
            pg.click(f"#palette button:has-text('{kind}')")
            pg.wait_for_selector("#props-card:not([hidden])")
            pg.fill("#p-x", str(x)); pg.dispatch_event("#p-x", "change")
            pg.fill("#p-y", str(y)); pg.dispatch_event("#p-y", "change")
        place("AND", 500, round((ry(2) + ry(3)) / 2 - 4.5, 2))
        place("켜짐 지연", 500, round(ry(6) - 4.5, 2))
        pg.fill("#p-t", "3"); pg.dispatch_event("#p-t", "change")
        place("누름단추", 500, round(ry(9) - 4.5, 2))
        pg.fill("#p-label", "START"); pg.dispatch_event("#p-label", "change")
        nblk = pg.evaluate("() => document.querySelectorAll('#blocks .blk').length")
        note(f"블록 {nblk}개 놓음")
        # 선 — 행 2 · 3 → AND 막대 · AND 출력 → 행 51 · 행 6 → GT · GT → 52 · PB → 53
        pg.keyboard.press("w")
        LX0, LX1 = 320.0, 870.0
        svg_click(LX0, ry(2)); svg_click(500, ry(2))                   # 막대 자리에서 저절로 끝난다
        svg_click(LX0, ry(3)); svg_click(500, ry(3))
        svg_click(516, (ry(2) + ry(3)) / 2); svg_click(700, (ry(2) + ry(3)) / 2); svg_click(700, ry(51)); svg_click(LX1, ry(51))
        svg_click(LX0, ry(6)); svg_click(500, ry(6))
        svg_click(516, ry(6)); svg_click(720, ry(6)); svg_click(720, ry(52)); svg_click(LX1, ry(52))
        svg_click(514, ry(9)); svg_click(740, ry(9)); svg_click(740, ry(53)); svg_click(LX1, ry(53))
        nw = pg.evaluate("() => document.querySelectorAll('#wires .wire').length")
        note(f"선 {nw}개 그음 (기대 6)")
        pg.keyboard.press("v")
        # 표 칸 — 두 번 눌러 적는다
        def cell(side, n, f, text):
            pg.dblclick(f".cell[data-side='{side}'][data-n='{n}'][data-f='{f}']")
            pg.wait_for_selector("#cellin:not([hidden])")
            pg.fill("#cellin", text)
            pg.keyboard.press("Escape") if False else pg.keyboard.press("Enter")
            pg.wait_for_timeout(80)
            pg.keyboard.press("Escape")
        cell("left", 2, "fm", "HMI"); cell("left", 2, "desc", "PUMP A RUN")
        cell("left", 3, "fm", "HMI"); cell("left", 3, "desc", "PUMP B RUN")
        cell("left", 6, "desc", "LEVEL LOW")
        cell("right", 51, "desc", "BOTH RUN"); cell("right", 51, "to", "LD-002/2")
        cell("right", 52, "desc", "LOW 3S"); cell("right", 53, "desc", "START CMD")
        pg.fill("#f-title", "SELF CHECK SHEET"); pg.dispatch_event("#f-title", "input")
        pg.screenshot(path=str(OUT / "2_drawn.png"))
        # L55 — 모눈 · 눈금자 · 정렬 안내선 (화면 전용)
        ng = pg.evaluate("() => document.querySelectorAll('#svg .grid line').length")
        rul = pg.evaluate("() => [!document.querySelector('#ruler-x').hidden, document.querySelector('#ruler-corner').textContent]")
        box = pg.eval_on_selector("#svg", "e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }")
        pg.mouse.move(box[0] + 600 / 1191 * box[2], box[1] + ry(20) / 842 * box[3])
        pg.wait_for_timeout(100)
        cross = pg.evaluate("() => document.querySelectorAll('#overlay .cross').length")
        corner = pg.text_content("#ruler-corner")
        note(f"모눈 선 {ng}개 · 눈금자 보임 {rul[0]} · 십자선 {cross}개 · 마우스 자리 '{corner}'")
        pg.screenshot(path=str(OUT / "2b_guides.png"), clip={"x": box[0] - 22, "y": box[1] - 22, "width": min(box[2] + 22, 1000), "height": min(box[3] + 22, 700)})
        # 블록을 끌어 다른 블록 변 · 행 가운데에 가까이 — 정렬 안내선이 선다 (자석을 끄고 1.5pt 만 끌어 본다)
        pg.uncheck("#snap")
        pg.mouse.move(box[0] + 505 / 1191 * box[2], box[1] + (ry(9) - 2) / 842 * box[3])
        pg.mouse.down()
        pg.mouse.move(box[0] + 505 / 1191 * box[2], box[1] + (ry(9) - 2 + 1.0) / 842 * box[3], steps=4)
        pg.mouse.move(box[0] + 505 / 1191 * box[2], box[1] + (ry(9) - 2 + 1.5) / 842 * box[3], steps=4)
        al = pg.evaluate("() => document.querySelectorAll('#overlay .align').length")
        pg.screenshot(path=str(OUT / "2c_align.png"), clip={"x": box[0] + 300, "y": box[1], "width": 500, "height": 200})
        pg.mouse.up()
        pg.keyboard.press("Control+z"); pg.check("#snap"); pg.focus("#stage")
        note(f"정렬 안내선 {al}개 (끄는 중 · 기대 2 — 왼쪽 변이 AND 와 같은 x · 가운데가 9행)")
        pg.keyboard.press("g"); ng2 = pg.evaluate("() => document.querySelectorAll('#svg .grid line').length")
        pg.keyboard.press("r"); rul2 = pg.evaluate("() => document.querySelector('#ruler-x').hidden")
        note(f"G 로 모눈 끔 → {ng2}개 · R 로 눈금자 끔 → 숨김 {rul2}")
        pg.keyboard.press("g"); pg.keyboard.press("r")
        pg.click("#save")
        pg.wait_for_function("document.querySelector('#status').textContent.includes('저장됨')")
        saved = json.loads(urllib.request.urlopen(f"{base}/logic/api/drawings/{did}").read())
        note(f"저장: 블록 {len(saved['blocks'])} · 선 {len(saved['wires'])} · 왼쪽 행 {len(saved['left'])} · 오른콩 행 {len(saved['right'])} · 작성자 {saved['author']}")
        # 되읽기 검증
        pg.click("#verify")
        pg.wait_for_selector("#verify-card:not([hidden])", timeout=120000)
        pg.wait_for_function("!document.querySelector('#verify').disabled", timeout=120000)
        vs = pg.text_content("#verify-sum")
        note(f"되읽기 검증: {vs} — {pg.text_content('#verify-out p')}")
        pg.screenshot(path=str(OUT / "3_verified.png"))
        # PDF · DXF
        pdf = urllib.request.urlopen(f"{base}/logic/api/drawings/{did}/export.pdf").read()
        dxf = urllib.request.urlopen(f"{base}/logic/api/drawings/{did}/export.dxf").read()
        note(f"PDF {len(pdf)} bytes (머리 {pdf[:5]!r}) · DXF {len(dxf)} bytes (SECTION {dxf.count(b'SECTION')}개)")
        (OUT / "export.pdf").write_bytes(pdf)
        (OUT / "export.dxf").write_bytes(dxf)
        # 검토로 보내기 — 그린 것이 LOGIC 검토 묶음으로 올라가 분석된다
        pg.on("dialog", lambda d: d.accept())
        pg.screenshot(path=str(OUT / "3b_before_send.png"))
        note("단추 자리: " + json.dumps(pg.evaluate("() => ['#analyse','#del','#pdf','.dw-head'].map(s => { const r = document.querySelector(s).getBoundingClientRect(); return [s, Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]; })")))
        note("단추 상태: " + json.dumps(pg.evaluate("() => { const b = document.querySelector('#analyse'); const cs = getComputedStyle(b); const r = b.getBoundingClientRect(); const e = document.elementFromPoint(r.left + r.width/2, r.top + r.height/2); return {disabled: b.disabled, pe: cs.pointerEvents, vis: cs.visibility, op: cs.opacity, z: cs.zIndex, pos: cs.position, at: e && e.tagName, hdr: getComputedStyle(b.parentElement).overflow, all: document.elementsFromPoint(r.left + r.width/2, r.top + r.height/2).map(x => x.tagName + (x.id ? '#' + x.id : '')).slice(0, 4)}; }")))
        pg.click("#analyse", timeout=8000)
        pg.wait_for_url("**/logic#job=*", timeout=30000)
        job = pg.url.split("job=")[-1]
        for _ in range(120):
            st = json.loads(urllib.request.urlopen(f"{base}/logic/api/jobs/{job}").read())
            if st.get("state") in ("done", "failed"):
                break
            time.sleep(1)
        note(f"검토로 보내기: 묶음 {job} · 상태 {st.get('state')} · 장 {st.get('total')}")
        pg.goto(base + "/logic/draw?user=%ED%99%8D%EA%B8%B8%EB%8F%99")
        pg.wait_for_selector("#palette button")
        # 가져오기 (묶음이 있을 때만)
        jobs = json.loads(urllib.request.urlopen(f"{base}/logic/api/jobs").read()).get("jobs") or []
        done = [j for j in jobs if j.get("state") == "done"]
        if done:
            pg.click("#import")
            try:
                pg.wait_for_selector("#m-sheets tr.pick", timeout=15000)
            except Exception:
                note("가져오기 판: " + pg.inner_html("#m-sheets")[:300] + " | 오류 " + " | ".join(errors[-3:]))
                raise
            pg.click("#m-sheets tr.pick >> nth=0")
            pg.click("#m-ok")
            pg.wait_for_function("document.querySelector('#pick').value !== ''")
            nb2 = pg.evaluate("() => document.querySelectorAll('#blocks .blk').length")
            nw2 = pg.evaluate("() => document.querySelectorAll('#wires .wire').length")
            note(f"가져오기: 블록 {nb2}개 · 선 {nw2}개 · 시트 {pg.input_value('#f-sheet')} · 제목 {pg.input_value('#f-title')}")
            pg.screenshot(path=str(OUT / "4_imported.png"))
        else:
            note("가져오기: 분석한 묶음이 없어 건너뜀")
        errors = [e for e in errors if e != "TypeError: Failed to fetch"]   # 떠나며 끊긴 fetch 의 메아리
        note(f"페이지 오류 {len(errors)}" + ("" if not errors else " — " + " | ".join(errors[:5])))
        br.close()
finally:
    srv.terminate()
    try:
        srv.wait(timeout=10)
    except Exception:
        srv.kill()
(OUT / "result.txt").write_text("\n".join(FOUND), encoding="utf-8")
