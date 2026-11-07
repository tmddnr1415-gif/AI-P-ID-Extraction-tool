"""L57 — LOGIC 작도 실시간 시뮬레이션 화면 자기검증 (크롬 · 사본 데이터 폴더 · 실 DB 를 열지 않는다).

  python3 spike/ui_audit_draw_sim.py <비어 있는 데이터 폴더> <그림 출력 폴더>

API 로 세 장 묶음(주 장 · Typical · 받는 장)을 만들고 → 화면에서 ▶ 시뮬레이션 → 입력 5 · 6 행을 1 로 → 매크로(Typical AND)를 지나
출력 51행 · 선이 파랗게 → 받는 장으로 옮기면 FM 으로 받은 입력이 1 · NOT 뒤 0 → 블록을 끌어 옮겨도 바로 다시 돈다 →
선을 지우면 출력이 꺼진다 → 리셋 → 화면 오류 0.
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
sys.path.insert(0, str(ROOT))
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


def req(path, body=None, method=None):
    dat = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(base + path, data=dat, method=method or ("POST" if dat else "GET"), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r).read())


try:
    for _ in range(90):
        try:
            urllib.request.urlopen(base + "/version", timeout=2)
            break
        except Exception:
            time.sleep(1)
    from app.logic import draw as D
    N = D.N_DEFAULT
    ry = lambda n: D.ry(n, N)
    W = lambda pts, **kw: {"id": "", "pts": [list(p) for p in pts], **kw}
    main = req("/logic/api/drawings", {"name": "MAIN", "author": "홍길동"})
    sid = "abc123def457"
    main["sheet_no"], main["title"], main["doc_no"] = "G001", "MAIN SHEET", "1-1"
    main = req(f"/logic/api/drawings/{main['id']}", {"author": "홍길동", "doc": main, "set": sid, "set_name": "시뮬 묶음", "order": 1}, "PUT")
    typ = req(f"/logic/api/drawings/sets/{sid}/sheet", {"author": "홍길동", "name": "MOV TYPICAL", "sheet_no": "T001", "typical": True})
    typ["title"], typ["doc_no"] = "MOV BLOCK (OPEN CLOSE) <TYPE-III-1>", "1-2"
    typ["left"] = {"1": {"fm": "", "kks": "AOPEN", "desc": "AUTO OPEN"}, "2": {"fm": "", "kks": "ACLOSE", "desc": "AUTO CLOSE"}}
    typ["right"] = {str(N + 1): {"desc": "OPEN COMMAND", "kks": "CMD", "to": ""}}
    ymid = (ry(1) + ry(2)) / 2
    sp = D.SYMBOLS["AND"]
    typ["blocks"] = [{"id": "a1", "kind": "AND", "x": 500, "y": round(ymid - sp["h"] / 2, 2), "w": sp["w"], "h": sp["h"], "text": "AND", "param": {}}]
    typ["wires"] = [W([(320, ry(1)), (500, ry(1))]), W([(320, ry(2)), (500, ry(2))]), W([(500 + sp["w"], ymid), (700, ymid), (700, ry(N + 1)), (870, ry(N + 1))])]
    typ = req(f"/logic/api/drawings/{typ['id']}", {"author": "홍길동", "doc": typ}, "PUT")
    info = req(f"/logic/api/drawings/sets/{sid}")
    m = [x for x in info["macros"] if x["typ"] == "T001"][0]
    mb = D.macro_block(m["title"], "T001", m["pins_in"], m["pins_out"], 480, ry(5) - D.MACRO_TOP - 0.5 * D.PITCH)
    main["left"] = {"5": {"fm": "", "kks": "", "desc": "PB OPEN"}, "6": {"fm": "", "kks": "", "desc": "PB CLOSE"}}
    main["right"] = {str(N + 1): {"desc": "MOV OPEN CMD", "kks": "", "to": "G002-2"}}
    ports = {p[3]: p for p in D.ports_of(mb)}
    gt = D.SYMBOLS["GT"]
    gtb = {"id": "g1", "kind": "GT", "x": 500, "y": round(ry(10) - gt["h"] / 2, 2), "w": gt["w"], "h": gt["h"], "text": "GT", "param": {"t": 2}}
    main["blocks"] = [mb, gtb]
    main["wires"] = [W([(320, ry(5)), (ports["AOPEN"][0], ports["AOPEN"][1])]), W([(320, ry(6)), (ports["ACLOSE"][0], ports["ACLOSE"][1])]),
                     W([(ports["CMD"][0], ports["CMD"][1]), (800, ports["CMD"][1]), (800, ry(N + 1)), (870, ry(N + 1))]),
                     W([(320, ry(10)), (500, ry(10))]), W([(500 + gt["w"], ry(10)), (870, ry(10 + N))])]
    main["left"]["10"] = {"fm": "", "kks": "", "desc": "DELAYED SIGNAL"}
    main["right"][str(N + 10)] = {"desc": "DELAYED OUT", "kks": "", "to": ""}
    main = req(f"/logic/api/drawings/{main['id']}", {"author": "홍길동", "doc": main}, "PUT")
    rx = req(f"/logic/api/drawings/sets/{sid}/sheet", {"author": "홍길동", "name": "RECEIVER", "sheet_no": "G002"})
    rx["doc_no"] = "1-3"
    rx["left"] = {"2": {"fm": "G001-%d" % (N + 1), "kks": "", "desc": "MOV OPEN CMD"}}
    g = D.SYMBOLS["NOT"]
    rx["blocks"] = [{"id": "n1", "kind": "NOT", "x": 500, "y": round(ry(2) - g["h"] / 2, 2), "w": g["w"], "h": g["h"], "text": "NOT", "param": {}}]
    rx["right"] = {str(N + 1): {"desc": "NOT OPEN", "kks": "", "to": ""}}
    rx["wires"] = [W([(320, ry(2)), (500, ry(2))]), W([(500 + g["w"], ry(2)), (700, ry(2)), (700, ry(N + 1)), (870, ry(N + 1))])]
    rx = req(f"/logic/api/drawings/{rx['id']}", {"author": "홍길동", "doc": rx}, "PUT")

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        pg = br.new_page(viewport={"width": 1600, "height": 950})
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" and "ERR_ABORTED" not in m.text else None)
        pg.on("dialog", lambda d: d.accept())
        pg.goto(base + f"/logic/draw?user=%ED%99%8D%EA%B8%B8%EB%8F%99#d={main['id']}")
        pg.wait_for_selector("#palette button")
        pg.wait_for_function("!document.querySelector('#simtoggle').disabled")

        def svg_pt(x, y):
            box = pg.eval_on_selector("#svg", "e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }")
            L = pg.evaluate("layout()")
            return box[0] + x / L["W"] * box[2], box[1] + y / L["H"] * box[3]

        def click_stub(n, choice):
            x, y = svg_pt(320 if n <= N else 870, ry(n))
            pg.mouse.click(x, y)
            pg.wait_for_selector("#simmenu:not([hidden]) button")
            pg.click(f"#simmenu button:has-text('{choice}')")
            pg.wait_for_timeout(500)

        def on_wires():
            return pg.evaluate("Array.from(document.querySelectorAll('.wire.on')).map(e => e.dataset.id)")

        pg.click("#simtoggle"); pg.wait_for_timeout(700)
        note(f"1 sim on: body.sim={pg.evaluate('document.body.classList.contains(\"sim\")')} card={not pg.is_hidden('#sim-card')} on_wires={on_wires()}")
        pg.screenshot(path=str(OUT / "1_sim_on.png"))
        click_stub(5, "1 활성")
        note(f"2 row5=1: on_wires={len(on_wires())} (AOPEN 선만 · AND 는 아직 0) given={pg.inner_text('#sim-out')[:80]!r}")
        click_stub(6, "1 활성")
        pg.wait_for_timeout(600)
        ow = on_wires()
        v51 = pg.evaluate(f"document.querySelector('.rowstub[data-n=\"{N + 1}\"]').classList.contains('v1')")
        note(f"3 row6=1: on_wires={len(ow)} (셋 다) out51 v1={v51} summary={pg.inner_text('#sim-sum')!r}")
        pg.screenshot(path=str(OUT / "2_macro_cmd.png"))
        note(f"   pins shown={pg.evaluate('document.querySelectorAll(\"#simov .simbox\").length')}")
        # 타이머 — 10행 1 → GT 2초 → 카운트다운 뒤 60행 1
        click_stub(10, "1 활성")
        t0 = pg.evaluate("document.querySelector('#simov .simtimer') && document.querySelector('#simov .simtimer').textContent")
        pg.wait_for_timeout(2600)
        v60 = pg.evaluate(f"document.querySelector('.rowstub[data-n=\"{N + 10}\"]').classList.contains('v1')")
        note(f"4 GT: timer text during={t0!r} → after 2.6s out{N + 10} v1={v60}")
        pg.screenshot(path=str(OUT / "3_timer.png"))
        # 받는 장
        pg.click(f"#set-list [data-id='{rx['id']}'], #set-list a:has-text('G002'), #set-list li:has-text('G002')")
        pg.wait_for_function(f"S.id === '{rx['id']}'"); pg.wait_for_timeout(900)
        linked = pg.evaluate("document.querySelector('.rowstub[data-n=\"2\"]').className.baseVal")
        ow2 = on_wires()
        v51r = pg.evaluate(f"document.querySelector('.rowstub[data-n=\"{N + 1}\"]').classList.contains('v1')")
        note(f"5 receiver: row2 class={linked!r} on_wires={ow2} NOT out v1={v51r} (0 이어야)")
        pg.screenshot(path=str(OUT / "4_receiver.png"))
        # 돌아와서 블록을 끌어 옮기면 바로 다시 돈다 · 선을 지우면 출력이 꺼진다
        pg.click(f"#set-list [data-id='{main['id']}'], #set-list li:has-text('G001')")
        pg.wait_for_function(f"S.id === '{main['id']}'"); pg.wait_for_timeout(900)
        before = len(on_wires())
        pg.evaluate("S.sel = new Set(['g1']); moveSel(0, layout().PITCH); render()")
        pg.wait_for_timeout(700)
        after_move = len(on_wires())
        pg.evaluate(f"S.selWire = S.doc.wires[2].id; deleteSel()")      # CMD → 51행 선
        pg.wait_for_timeout(700)
        v51b = pg.evaluate(f"document.querySelector('.rowstub[data-n=\"{N + 1}\"]').classList.contains('v1')")
        note(f"6 live edit: on before={before} after move={after_move} · CMD 선 지운 뒤 out51 v1={v51b} (False 이어야) status={pg.inner_text('#status')[:60]!r}")
        pg.evaluate("undo()"); pg.wait_for_timeout(700)
        v51c = pg.evaluate(f"document.querySelector('.rowstub[data-n=\"{N + 1}\"]').classList.contains('v1')")
        note(f"7 undo: out51 v1={v51c} (True 이어야)")
        # 글자 상자 보기 — 상수 1 을 놓고 선 없이도 활성(1) 으로 선다 (뜻은 글자가 정한다)
        npre = pg.evaluate("document.querySelectorAll('#palette .dw-preicon').length")
        pg.click("#palette button:has(.dw-preicon):has-text('상수 1')"); pg.wait_for_timeout(700)
        c1 = pg.evaluate("(() => { const b = S.doc.blocks[S.doc.blocks.length-1]; const g = document.querySelector(`.blk[data-id=\"${b.id}\"]`); return [b.kind, b.text, g && g.classList.contains('act'), S.sim.res.sheet.blocks[b.id].func]; })()")
        note(f"7b presets={npre} · 상수 1 놓음 → {c1} (act 는 나가는 선이 없어 False · func CONST)")
        pg.evaluate("undo()"); pg.wait_for_timeout(500)
        pg.click("#sim-reset"); pg.wait_for_timeout(600)
        note(f"8 reset: on_wires={len(on_wires())} given={pg.inner_text('#sim-out')[:60]!r}")
        pg.click("#simtoggle"); pg.wait_for_timeout(300)
        note(f"9 sim off: body.sim={pg.evaluate('document.body.classList.contains(\"sim\")')} simov={pg.evaluate('!!document.querySelector(\"#simov\")')}")
        note(f"page errors: {errors}")
        br.close()
finally:
    srv.terminate()
    (OUT / "result.txt").write_text("\n".join(FOUND), encoding="utf-8")
