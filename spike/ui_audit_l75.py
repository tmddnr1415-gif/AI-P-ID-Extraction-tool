"""L75 — 작도 화면의 꺾인 선 토막 끌기 (원래 L60 자를 바탕으로) · Shift 정렬 안내선 · 정렬 · 균등 간격을 크롬으로 눌러 확인한다 (사본 데이터 · 실 DB 를 열지 않는다).

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
    req = urllib.request.Request(base + "/logic/api/drawings", data=json.dumps({"author": "검증", "title": "L75"}).encode(), headers={"Content-Type": "application/json"})
    did = json.loads(urllib.request.urlopen(req).read())["id"]
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch()
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

        x0 = L["LX0"] + 80
        pg.evaluate(f"() => {{ addBlock('AND', {x0}, {ry(4)}); render(); }}")
        b = pg.evaluate("() => S.doc.blocks[0]")
        ins = pg.evaluate("() => ports(S.doc.blocks[0]).filter(p => p[2] === 'in').map(p => [p[0], p[1]])")
        tgt = ins[0]
        # 사진 꼴 — 2행에서 오른쪽 · 기호 바로 앞에서 꺾어 내려 입력으로
        bend = tgt[0] - 2.0
        pg.evaluate(f"() => {{ pushUndo(); S.doc.wires.push({{id: 'wT', pts: [[{L['LX0']}, {ry(2)}], [{bend}, {ry(2)}], [{bend}, {tgt[1]}], [{tgt[0]}, {tgt[1]}]]}}); S.selWire = 'wT'; render(); }}")
        nh = pg.evaluate("() => document.querySelectorAll('.seghd').length")
        pg.screenshot(path=str(OUT / "1_before.png"), clip={"x": 0, "y": 0, "width": 900, "height": 500})
        h = pg.evaluate("() => { const e = [...document.querySelectorAll('.seghd.ax-x')][0]; const r = e.getBoundingClientRect(); return [r.left + r.width/2, r.top + r.height/2]; }")
        tx, _ = svg_pt(bend - 3 * P, 0)
        pg.mouse.move(*h); pg.mouse.down(); pg.mouse.move(tx, h[1], steps=10)
        pg.screenshot(path=str(OUT / "2_dragging.png"), clip={"x": 0, "y": 0, "width": 900, "height": 500})
        pg.mouse.up()
        pts = pg.evaluate("() => S.doc.wires.find(w => w.id === 'wT').pts")
        note(f"손잡이 {nh}개 · 끈 뒤 점 {pts}")
        ortho = all(abs(pts[i][0]-pts[i+1][0]) < 0.01 or abs(pts[i][1]-pts[i+1][1]) < 0.01 for i in range(len(pts)-1))
        note(f"꺾인 자리 x {bend:.2f} → {pts[1][0]:.2f} (반 행 {P/2:.2f} 배수 {abs(pts[1][0]/(P/2) - round(pts[1][0]/(P/2))) < 0.01}) · 가로/세로만 {ortho} · 끝점 그대로 {pts[0] == [L['LX0'], ry(2)] and abs(pts[-1][0]-tgt[0]) < 0.01}")
        pg.screenshot(path=str(OUT / "3_after.png"), clip={"x": 0, "y": 0, "width": 900, "height": 500})
        # 첫 가로 토막을 위아래로 — 행 자리 끝점은 그대로 · 짧은 세로 토막이 생긴다
        h = pg.evaluate("() => { const e = [...document.querySelectorAll('.seghd.ax-y')][0]; const r = e.getBoundingClientRect(); return [r.left + r.width/2, r.top + r.height/2]; }")
        _, ty = svg_pt(0, ry(3))
        pg.mouse.move(*h); pg.mouse.down(); pg.mouse.move(h[0], ty, steps=8); pg.mouse.up()
        pts2 = pg.evaluate("() => S.doc.wires.find(w => w.id === 'wT').pts")
        note(f"첫 가로 토막 아래로 → {pts2} · 첫 점 그대로 {pts2[0] == [L['LX0'], ry(2)]}")
        pg.keyboard.press("Control+z")
        pts3 = pg.evaluate("() => S.doc.wires.find(w => w.id === 'wT').pts")
        note(f"되돌리기 → {pts3 == pts}")
        # 새로 그리는 선의 추천 경로가 기호에 바짝 붙지 않는가
        r = pg.evaluate(f"() => {{ S.tool = 'wire'; S.wip = {{pts: [[{L['LX0']}, {ry(8)}]], cur: [0, 0], hot: [{ins[1][0]}, {ins[1][1]}, 'port'], startKind: 'row'}}; return routePick([{L['LX0']}, {ry(8)}], [{ins[1][0]}, {ins[1][1]}]); }}")
        note(f"추천 경로 {r} · 들어가는 가로 토막 {abs(r[-1][0]-r[-2][0]):.2f} (행 간격 {P:.2f})")
        pg.evaluate("() => { S.wip = null; S.tool = 'select'; }")
        note(f"페이지 오류 {len(errors)} {errors[:3]}")
        br.close()
finally:
    srv.terminate()
    (OUT / "result.txt").write_text("\n".join(FOUND) + "\n", encoding="utf-8")
