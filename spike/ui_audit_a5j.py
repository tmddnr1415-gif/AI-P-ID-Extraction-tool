"""L58 — 알다프라(1A5J) 양식 그림 묶음을 작도 화면에서 띄워 확인한다 (크롬 · 사본 데이터 폴더 · 실 DB 를 열지 않는다).

  python3 spike/ui_audit_a5j.py <그림 묶음이 든 데이터 폴더> <그림 출력 폴더>

묶음 목록 → 첫 장(FG_G-101)을 연다 → 양식 선택이 '알다프라' · 화면에 OR 원 · NOT ⊠ · LOGIC 머리글 · 삼성 타이틀블록이 선다 →
▶ 시뮬레이션 → 입력 8 · 13 · 21 · 25 · 26 행을 1 로 → 출력 79행이 1 → FG_G-201 로 옮겨 ◆ ■ 표시와 PB 칸 · 매크로 머리를 본다 →
화면 오류 0.  결과는 result.txt 와 PNG 로.
"""
from __future__ import annotations

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
    for _ in range(120):
        try:
            urllib.request.urlopen(base + "/version", timeout=2).read()
            break
        except Exception:
            time.sleep(0.5)
    import json
    sets = json.loads(urllib.request.urlopen(base + "/logic/api/drawings/sets").read())
    st = (sets.get("items") or [])[0]
    sheets = {q["sheet_no"]: q["id"] for q in st["sheets"]}
    note(f"묶음 {st['name']} · 장 {len(sheets)}")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        pg = br.new_page(viewport={"width": 1700, "height": 1000})
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" and "ERR_ABORTED" not in m.text else None)
        pg.goto(f"{base}/logic/draw#d={sheets['FG_G-101']}")
        pg.wait_for_selector("#svg g.blk", timeout=30000)
        time.sleep(0.8)
        form = pg.eval_on_selector("#f-form", "e => e.value")
        pname = pg.eval_on_selector("#f-pname", "e => e.value")
        n_circle = pg.evaluate("() => document.querySelectorAll('#svg g.blk circle').length")
        n_blk = pg.evaluate("() => document.querySelectorAll('#svg g.blk').length")
        logic_head = pg.evaluate("() => [...document.querySelectorAll('#svg .title text')].map(t => t.textContent).filter(t => ['LOGIC', 'PROJECT NAME', 'DRAWING TITLE', 'SHEET'].includes(t)).length")
        note(f"FG_G-101 양식 {form!r} · 프로젝트 이름 {pname!r} · 블록 {n_blk} · 원(OR) {n_circle} · 양식 글 4/{logic_head}")
        pg.screenshot(path=str(OUT / "1_fg_g_101.png"))
        pg.click("#simtoggle")
        time.sleep(1.2)
        L = pg.evaluate("layout()")

        def svg_pt(x, y):
            box = pg.eval_on_selector("#svg", "e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }")
            return box[0] + x / L["W"] * box[2], box[1] + y / L["H"] * box[3]

        def ry(n):
            return L["TOP"] + ((n - 1) % L["N"]) * L["PITCH"] + L["PITCH"] / 2
        for n in (8, 13, 21, 25, 26):
            x, y = svg_pt(L["LX0"], ry(n))
            pg.mouse.click(x, y)
            pg.wait_for_selector("#simmenu:not([hidden]) button")
            pg.click("#simmenu button:has-text('1')")
            pg.wait_for_timeout(700)
        time.sleep(1.0)
        on = pg.evaluate("() => document.querySelectorAll('#svg .wire.on').length")
        out79 = pg.evaluate("() => { const e = document.querySelector(\"#svg .rowstub[data-n='79']\"); return e ? e.classList.contains('v1') : null; }")
        note(f"시뮬레이션: 활성 선 {on} · 출력 79행 = {out79}")
        pg.screenshot(path=str(OUT / "2_fg_g_101_sim.png"))
        pg.goto(f"{base}/logic/draw#d={sheets['FG_G-201']}")
        pg.reload()                                         # 해시만 바뀐 이동은 같은 화면에 머문다 — 다시 읽어 그 장을 연다
        pg.wait_for_selector("#svg g.blk.macro", timeout=30000)
        time.sleep(0.8)
        marks = pg.evaluate("() => document.querySelectorAll('#svg polygon.mark').length")
        ell = pg.evaluate("() => document.querySelectorAll('#svg ellipse').length")
        pb = pg.evaluate("() => [...document.querySelectorAll('#svg g.blk text')].map(t => t.textContent).filter(t => ['AUTO', 'MAN', 'START', 'STOP'].includes(t)).length")
        head = pg.evaluate("() => [...document.querySelectorAll('#svg g.blk.macro text')].map(t => t.textContent).slice(0, 2)")
        note(f"FG_G-201: ◆■ 표시 {marks} · ANN 타원 {ell} · PB 칸 글자 {pb} · 매크로 머리 {head}")
        pg.screenshot(path=str(OUT / "3_fg_g_201.png"))
        note(f"페이지 오류 {len(errors)} {errors[:3]}")
        br.close()
finally:
    srv.terminate()
    (OUT / "result.txt").write_text("\n".join(FOUND) + "\n", encoding="utf-8")
