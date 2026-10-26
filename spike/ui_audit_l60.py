"""L60 — 작도 화면의 Shift 정렬 안내선 · 정렬 · 균등 간격을 크롬으로 눌러 확인한다 (사본 데이터 · 실 DB 를 열지 않는다).

  python3 spike/ui_audit_l60.py <그림 묶음이 든 데이터 폴더> <그림 출력 폴더>

새 그림 → AND 둘을 놓고(위 · 아래 오른쪽으로 비킴) → 아래 것을 Shift 를 누른 채 끌어 위 것 바로 밑으로 → x 가 같아지고 안내선이 선다 →
선 하나를 그리고 Shift 끌기로 단자가 그 선 높이에 선다 → AND 셋을 고르고 세로 균등 간격 → 틈이 같다 · 왼쪽 맞춤 → x 가 같다 ·
되돌리기 → 제자리 · 화면 오류 0.
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
    req = urllib.request.Request(base + "/logic/api/drawings", data=json.dumps({"author": "검증", "title": "L60"}).encode(), headers={"Content-Type": "application/json"})
    did = json.loads(urllib.request.urlopen(req).read())["id"]
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        pg = br.new_page(viewport={"width": 1700, "height": 1000})
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" and "ERR_ABORTED" not in m.text else None)
        pg.goto(f"{base}/logic/draw#d={did}")
        pg.wait_for_selector("#svg", timeout=30000)
        pg.wait_for_function("() => typeof S !== 'undefined' && S.doc && S.sym")
        time.sleep(0.5)
        L = pg.evaluate("layout()")
        P = L["PITCH"]

        def svg_pt(x, y):
            box = pg.eval_on_selector("#svg", "e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }")
            return box[0] + x / L["W"] * box[2], box[1] + y / L["H"] * box[3]

        def ry(n):
            return L["TOP"] + ((n - 1) % L["N"]) * P + P / 2

        x0 = L["LX0"] + 120
        pg.evaluate(f"() => {{ addBlock('AND', {x0}, {ry(10)}); addBlock('AND', {x0 + 3 * P}, {ry(20)}); }}")
        blocks = pg.evaluate("() => S.doc.blocks.map(b => ({id: b.id, x: b.x, y: b.y, w: b.w, h: b.h}))")
        a, b = blocks[0], blocks[1]
        note(f"AND 둘 놓음 — 위 x {a['x']:.2f} · 아래 x {b['x']:.2f} (차 {b['x'] - a['x']:.2f})")
        # 아래 AND 를 Shift 를 누른 채 끌어 위 것의 x 근처(0.3P 비킴)로
        cx, cy = svg_pt(b["x"] + b["w"] / 2, b["y"] + b["h"] / 2)
        tx, ty = svg_pt(a["x"] + b["w"] / 2 + 0.3 * P, b["y"] + b["h"] / 2)
        pg.mouse.move(cx, cy); pg.mouse.down(); pg.mouse.move(cx + 3, cy, steps=2)
        pg.keyboard.down("Shift"); pg.mouse.move(tx, ty, steps=8)
        lines = pg.evaluate("() => (S.alignLines || []).map(a => a.axis + ':' + a.kind)")
        n_guide = pg.evaluate("() => document.querySelectorAll('#overlay line.align').length")
        pg.screenshot(path=str(OUT / "1_shift_align.png"))
        pg.mouse.up(); pg.keyboard.up("Shift")
        nb = pg.evaluate(f"() => S.doc.blocks.find(b => b.id === '{b['id']}')")
        note(f"Shift 끌기: 안내선 {n_guide} {lines} · 아래 AND x {nb['x']:.2f} (위 x {a['x']:.2f}) → {'같다' if abs(nb['x'] - a['x']) < 0.05 else '다르다'}")
        # 선 하나를 15행에서 가로로 긋고, AND 셋째를 Shift 끌기로 그 선 높이에 — 입력 단자가 선에 선다
        wy = ry(15) + 0.4 * P                      # 행 가운데에서 비킨 선 — 행 자석이 아니라 선 자석이 맞는지 본다
        pg.evaluate(f"() => {{ pushUndo(); S.doc.wires.push({{id: newId('w'), pts: [[{L['LX0']}, {wy}], [{x0 - 20}, {wy}]], dash: false}}); addBlock('AND', {x0 + 6 * P}, {ry(26)}); render(); }}")
        c = pg.evaluate("() => S.doc.blocks[S.doc.blocks.length - 1]")
        cx, cy = svg_pt(c["x"] + c["w"] / 2, c["y"] + c["h"] / 2)
        tx, ty = svg_pt(c["x"] + c["w"] / 2, wy + 0.3 * P)
        pg.mouse.move(cx, cy); pg.mouse.down(); pg.mouse.move(cx, cy + 3, steps=2)
        pg.keyboard.down("Shift"); pg.mouse.move(tx, ty, steps=8)
        lines2 = pg.evaluate("() => (S.alignLines || []).map(a => a.axis + ':' + a.kind)")
        pg.screenshot(path=str(OUT / "2_shift_wire.png"))
        pg.mouse.up(); pg.keyboard.up("Shift")
        pys = pg.evaluate(f"() => ports(S.doc.blocks.find(b => b.id === '{c['id']}')).filter(p => p[2] === 'in').map(p => p[1])")
        hit = any(abs(y - wy) < 0.05 for y in pys)
        note(f"Shift 끌기(선): 안내선 {lines2} · 입력 단자 높이 {[round(y, 2) for y in pys]} ↔ 선 {wy:.2f} → {'맞음' if hit else '안 맞음'}")
        # 셋을 고르고 세로 균등 간격 · 왼쳐 맞춤
        pg.evaluate("() => { S.sel = new Set(S.doc.blocks.map(b => b.id)); render(); }")
        pg.evaluate("() => { $('#snap').checked = false; S.snap = false; }")
        pg.click('.dw-arrange button[data-op="distv"]')
        bbs = pg.evaluate("() => S.doc.blocks.map(b => bboxOf(b)).sort((p, q) => p[1] - q[1])")
        gaps = [round(bbs[i + 1][1] - bbs[i][3], 2) for i in range(len(bbs) - 1)]
        pg.click('.dw-arrange button[data-op="left"]')
        xs = pg.evaluate("() => S.doc.blocks.map(b => bboxOf(b)[0])")
        pg.screenshot(path=str(OUT / "3_distribute.png"))
        note(f"세로 균등 간격: 틈 {gaps} → {'같다' if max(gaps) - min(gaps) < 0.05 else '다르다'} · 왼쪽 맞춤: x {[round(x, 2) for x in xs]} → {'같다' if max(xs) - min(xs) < 0.05 else '다르다'}")
        pg.evaluate("() => { $('#snap').checked = true; S.snap = true; }")
        pg.click('.dw-arrange button[data-op="distv"]')
        bbs = pg.evaluate("() => S.doc.blocks.map(b => bboxOf(b)).sort((p, q) => p[1] - q[1])")
        gaps2 = [round(bbs[i + 1][1] - bbs[i][3], 2) for i in range(len(bbs) - 1)]
        note(f"자석 켠 균등 간격: 틈 {gaps2} = 반 행({P / 2:.2f})의 배수 {all(abs(g / (P / 2) - round(g / (P / 2))) < 0.01 for g in gaps2)}")
        pg.keyboard.press("Control+z"); pg.keyboard.press("Control+z")
        xs2 = pg.evaluate("() => S.doc.blocks.map(b => bboxOf(b)[0])")
        note(f"되돌리기 두 번 → x {[round(x, 2) for x in xs2]} (왼쪽 맞춤 전으로 {'돌아옴' if max(xs2) - min(xs2) > 1 else '안 돌아옴'})")
        two = pg.evaluate("() => { S.sel = new Set([S.doc.blocks[0].id, S.doc.blocks[1].id]); render(); arrangeSel('distv'); return $('#status').textContent; }")
        note(f"둘만 골라 균등 간격 → '{two}'")
        note(f"페이지 오류 {len(errors)} {errors[:3]}")
        br.close()
finally:
    srv.terminate()
    (OUT / "result.txt").write_text("\n".join(FOUND) + "\n", encoding="utf-8")
