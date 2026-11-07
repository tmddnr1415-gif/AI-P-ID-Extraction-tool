"""L61 — 알다프라 FG_G-201 을 LOGIC 작도로 처음부터 그리는 과정을 단계마다 찍는다 (크롬 · 사본 데이터 · 실 DB 안 연다).

빈 장 → 표(FROM/TO — 시트 · 행 자동완성) → 기호 → 매크로 → 선(자동 경로) → 저장 · 되읽기 → 시뮬레이션 → 매크로 새 창.
그림의 내용은 같은 묶음에 들여온 원본(FG_G-201)에서 가져오고, 사람이 하는 동작(팔레트 · 칸 입력 · 선 긋기 · 신호 주기)은 실제로 누른다.

  python3 spike/ui_shots_draw_a5j.py <알다프라 그림 묶음이 든 데이터 폴더(사본)> <출력 폴더>
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
for p in OUT.glob("*.png"):
    p.unlink()
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT), PID_PAGE_WARM="0", PID_LOGIC_WARM="0", PID_ROWS_WARM="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = f"http://127.0.0.1:{port}"
LOG = []
WHO = "홍길동"


def note(x):
    print(x, flush=True)
    LOG.append(x)


def req(method, path, body=None):
    r = urllib.request.Request(base + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                               headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r).read())


try:
    for _ in range(120):
        try:
            urllib.request.urlopen(base + "/version", timeout=2).read()
            break
        except Exception:
            time.sleep(0.5)
    st = req("GET", "/logic/api/drawings/sets")["items"][0]
    sheets = {q["sheet_no"]: q["id"] for q in st["sheets"]}
    src = req("GET", f"/logic/api/drawings/{sheets['FG_G-201']}")
    # 원본 FG_G-201 을 묶음에서 빼고, 같은 이름의 빈 장을 새로 만들어 그 자리에서 그린다
    req("DELETE", f"/logic/api/drawings/{sheets['FG_G-201']}?author={urllib.parse.quote(WHO)}")
    new = req("POST", "/logic/api/drawings", {"author": WHO, "name": "FG_G-201", "project": src.get("project", ""), "N": src["N"]})
    meta = {k: src.get(k) for k in ("sheet_no", "title", "doc_no", "N", "form", "project_name", "rev", "project")}
    doc = {**new, **meta, "left": {}, "right": {}, "blocks": [], "wires": [], "notes": []}
    req("PUT", f"/logic/api/drawings/{new['id']}", {"author": WHO, "doc": doc, "set": st["id"], "set_name": st["name"], "order": src.get("order", 3)})
    did = new["id"]
    note(f"원본 FG_G-201 — 블록 {len(src['blocks'])} · 선 {len(src['wires'])} · 입력 행 {len(src['left'])} · 출력 행 {len(src['right'])}")

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        ctx = br.new_context(viewport={"width": 1700, "height": 1000})
        pg = ctx.new_page()
        errors = []

        def hook(p):
            p.on("pageerror", lambda e: errors.append(str(e)))
            p.on("console", lambda m: errors.append(m.text) if m.type == "error" and "ERR_ABORTED" not in m.text else None)
        hook(pg)
        pg.add_init_script(f"try {{ localStorage.setItem('pid.author', {json.dumps(WHO)}); }} catch (e) {{}}")
        pg.goto(f"{base}/logic/draw#d={did}")
        pg.wait_for_function("typeof S !== 'undefined' && S.doc && S.sym && S.setInfo", timeout=30000)
        time.sleep(0.8)
        pg.evaluate(f"window.SRC = {json.dumps(src)}")
        L = pg.evaluate("layout()")
        shot_n = [0]

        def shot(name, what, p=None, clip=None):
            shot_n[0] += 1
            fn = f"{shot_n[0]:02d}_{name}.png"
            (p or pg).screenshot(path=str(OUT / fn), clip=clip)
            note(f"{fn} — {what}")

        def svg_pt(x, y):
            box = pg.eval_on_selector("#svg", "e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }")
            return box[0] + x / L["W"] * box[2], box[1] + y / L["H"] * box[3]

        def ry(n):
            return L["TOP"] + ((n - 1) % L["N"]) * L["PITCH"] + L["PITCH"] / 2

        shot("empty", "빈 장 — 삼성 양식(타이틀블록 · FROM/TO 표 · LOGIC 영역)")

        # ── 표: 입력 행 ──
        pg.evaluate("() => { pushUndo(); S.doc.left = JSON.parse(JSON.stringify(SRC.left)); markDirty(); render(); }")
        shot("table_left", f"입력 행 {len(src['left'])}개 — FM · KKS · 설명")

        # ── 표: 출력 행 61 의 TO 를 자동완성으로 ──
        right = dict(src["right"])
        r61 = dict(right.pop("61"))
        pg.evaluate(f"() => {{ S.doc.right = JSON.parse(JSON.stringify({json.dumps(right)})); S.doc.right['61'] = {{desc: {json.dumps(r61['desc'])}, kks: ''}}; markDirty(); render(); }}")
        cell = pg.locator('.cell[data-side="right"][data-n="61"][data-f="to"]')
        cell.scroll_into_view_if_needed()
        cell.dblclick(force=True)
        pg.wait_for_selector("#cellin:not([hidden])")
        pg.keyboard.type("FG", delay=60)
        pg.wait_for_selector("#cellac:not([hidden])")
        time.sleep(0.3)
        ib = pg.eval_on_selector("#cellin", "e => { const r = e.getBoundingClientRect(); return [r.left, r.top]; }")
        clip = {"x": max(0, ib[0] - 260), "y": max(0, ib[1] - 120), "width": 640, "height": 420}
        items = pg.evaluate("() => [...document.querySelectorAll('#cellac .ac-it b')].map(e => e.textContent)")
        shot("to_type_G", f"TO 칸에 'FG' — 시트 {len(items)}개가 주르륵: {', '.join(items[:8])}", clip=clip)
        pg.keyboard.type("_G-1", delay=60)
        time.sleep(0.4)
        items = pg.evaluate("() => [...document.querySelectorAll('#cellac .ac-it b')].map(e => e.textContent)")
        shot("to_type_FG_G-1", f"'FG_G-1' 까지 — 좁혀짐: {', '.join(items)}", clip=clip)
        pg.keyboard.press("Enter")                          # 첫 시트(FG_G-101) → 그 장의 입력 행이 뜬다
        pg.wait_for_function("() => (document.querySelector('#cellac .ac-head') || {}).textContent && document.querySelector('#cellac .ac-head').textContent.includes('행')")
        time.sleep(0.3)
        rows = pg.evaluate("() => [...document.querySelectorAll('#cellac .ac-it')].slice(0, 6).map(e => e.textContent)")
        shot("to_rows", f"시트를 고르면 그 장의 입력 행: {rows[:3]}", clip=clip)
        pg.keyboard.type("13", delay=80)
        time.sleep(0.4)
        pg.keyboard.press("Enter")
        time.sleep(0.4)
        v = pg.evaluate("() => S.doc.right['61'].to")
        note(f"   → 61행 TO = {v!r}")
        pg.evaluate(f"() => {{ S.doc.right['61'].kks = {json.dumps(r61.get('kks', ''))}; render(); }}")
        shot("table_right", f"출력 행 {len(src['right'])}개 — 61행 TO {v}")

        # ── 기호: 팔레트에서 AND 하나를 실제로 놓고, 원본 자리로 ──
        blocks = {b["id"]: b for b in src["blocks"]}
        pg.click("#palette button:has(span:text-is('AND'))") if pg.locator("#palette button:has(span:text-is('AND'))").count() else pg.locator("#palette button").first.click()
        time.sleep(0.3)
        shot("palette_and", "팔레트에서 AND 를 누름 — 가운데에 놓임")

        def put_blocks(ids):
            pg.evaluate(f"""() => {{ pushUndo(); const want = {json.dumps([blocks[i] for i in ids])};
                const ids = new Set(want.map(b => b.id));
                S.doc.blocks = S.doc.blocks.filter(b => !ids.has(b.id) && !/^b\\d+$/.test(b.id));
                S.doc.blocks.push(...JSON.parse(JSON.stringify(want))); S.sel = new Set(ids); markDirty(); render(); }}""")
        put_blocks(["B4"])
        shot("place_and", "끌어서 그 자리로 — 반 행 격자에 맞음")
        pbs = [i for i, b in blocks.items() if b["kind"] in ("PB", "LAMP", "BOX")]
        put_blocks(pbs)
        shot("place_pb_lamp", f"누름단추 AUTO · MAN · START · STOP · 표시등 · 상수 1 — {len(pbs)}개")
        gates = [i for i, b in blocks.items() if b["kind"] in ("AND", "OR", "NOT", "GT")]
        put_blocks(gates)
        shot("place_gates", f"AND · OR · NOT · ON DELAY — {len(gates)}개")
        # 매크로: 매크로 카드에서 Typical 0012 를 누르고 원본 자리로
        if pg.locator("#macro-list button").count():
            pg.locator("#macro-list button").first.click()
            time.sleep(0.4)
            shot("macro_card", "매크로 카드에서 Typical 0012 (FG COMPR SYS GRP) 를 누름 — 단자는 Typical 행에서")
        rest = [i for i in blocks if i not in ("B4", *pbs, *gates)]
        put_blocks(rest)
        shot("place_macro_ann", f"매크로 · 경보 ANN 자리 잡음 — 기호 {len(blocks)}개 전부")

        # ── 선: 하나를 실제로 그어 자동 경로 미리보기, 나머지는 원본 그대로 ──
        wires = src["wires"]
        demo = max(wires, key=lambda w: len(w["pts"]))
        p0, p1 = demo["pts"][0], demo["pts"][-1]
        pg.keyboard.press("w")
        pg.mouse.click(*svg_pt(*p0))
        pg.mouse.move(*svg_pt(*p1))
        time.sleep(0.3)
        n_alt = pg.evaluate("() => (S.wip && S.wip.routes || []).length")
        shot("wire_route", f"선 긋기 — 다음 점까지 꺾인 경로 {n_alt}가지를 점선으로 추천 (Tab 으로 바꿈 · 누르면 반영)")
        pg.mouse.click(*svg_pt(*p1))
        pg.keyboard.press("Enter")
        time.sleep(0.2)
        shot("wire_done", "누르니 추천 경로가 선이 됨")
        pg.keyboard.press("Escape")
        pg.evaluate("() => { S.doc.wires = []; render(); }")
        k = len(wires)
        for i, (a, b) in enumerate([(0, k // 3), (k // 3, 2 * k // 3), (2 * k // 3, k)]):
            pg.evaluate(f"() => {{ pushUndo(); S.doc.wires.push(...JSON.parse(JSON.stringify(SRC.wires.slice({a}, {b})))); markDirty(); render(); }}")
            shot(f"wires_{i + 1}", f"선 {b}/{k}")

        # ── 저장 · 되읽기 검증 ──
        pg.fill("#who", WHO)
        pg.click("#save")
        pg.wait_for_function("() => !S.dirty", timeout=20000)
        time.sleep(0.8)
        pg.click("#set-verify")                             # 묶음 검증 — 다른 장 · Typical 까지 한 PDF 로 되읽어 FROM/TO · 매크로를 맞댄다
        pg.wait_for_function("() => !document.querySelector('#verify-card').hidden && !document.querySelector('#set-verify').disabled", timeout=240000)
        time.sleep(0.8)
        vtxt = pg.eval_on_selector("#verify-card", "e => e.innerText").replace("\n", " · ")[:160]
        shot("saved_verify", f"저장 → 묶음 되읽기 검증: {vtxt}")

        # ── 시뮬레이션 ──
        pg.keyboard.press("v")
        pg.click("#simtoggle")
        time.sleep(1.5)
        shot("sim_start", "시뮬레이션 켬 — 고장 신호(GR_FLT)가 서 있어 FAULT 표시")

        def force_row(n):
            pg.mouse.click(*svg_pt(L["LX0"], ry(n)))
            pg.wait_for_selector("#simmenu:not([hidden]) button")
            pg.click("#simmenu button:has-text('1')")
            pg.wait_for_timeout(1200)

        def force_block(bid):
            b = blocks[bid]
            pg.mouse.click(*svg_pt(b["x"] + b["w"] / 2, b["y"] + b["h"] / 2))
            pg.wait_for_selector("#simmenu:not([hidden]) button")
            pg.click("#simmenu button:has-text('1')")
            pg.wait_for_timeout(1500)

        def val(net):
            return pg.evaluate(f"() => (S.sim && S.sim.values || {{}})[{json.dumps(net)}]")
        force_row(16); force_row(27)
        shot("sim_ready", f"입력 16행 REM & RDY · 27행 NO FLT = 1 → 고장 풀림 · 기동 허가 EN_STRT = {val('14')}")
        force_block("B22")
        shot("sim_man", f"PB MAN = 1 → 수동 선택 M_SEL = {val('1')}")
        force_block("B23")
        time.sleep(1.0)
        shot("sim_start_cmd", f"PB START = 1 → 매크로 출력 C_STRT = {val('8')} → 74행 GRP STR CMD")

        # ── 매크로 새 창 ──
        mb = blocks["B3"]
        pg.mouse.click(*svg_pt(mb["x"] + mb["w"] / 2, mb["y"] + 6))
        pg.wait_for_selector("#simmenu:not([hidden]) button")
        with ctx.expect_page() as pinfo:
            pg.click("#simmenu button:has-text('내부 동작')")
        child = pinfo.value; hook(child)
        child.set_viewport_size({"width": 1700, "height": 1000})
        child.wait_for_selector("#svg g.blk", timeout=30000)
        time.sleep(3.0)
        on = child.evaluate("() => Object.values(S.sim.values || {}).filter(v => v === 1).length")
        shot("macro_child", f"매크로 새 창 — Typical 0012 안쪽이 부모 값으로 동작 (1 인 선 {on})", p=child)
        # 부모에서 STOP 을 누르면 새 창이 따라간다
        pg.bring_to_front()
        force_block("B24")
        time.sleep(2.0)
        on2 = child.evaluate("() => Object.values(S.sim.values || {}).filter(v => v === 1).length")
        shot("sim_stop_parent", f"부모에서 PB STOP = 1 → C_STP = {val('9')}")
        child.bring_to_front()
        time.sleep(0.5)
        shot("macro_child_stop", f"새 창도 따라 바뀜 (1 인 선 {on} → {on2})", p=child)
        note(f"페이지 오류 {len(errors)} {errors[:3]}")
        br.close()
finally:
    srv.terminate()
    (OUT / "steps.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
