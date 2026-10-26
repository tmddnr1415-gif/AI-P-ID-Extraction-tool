"""L59 — 작도 화면 자기검증: 범례 보기 전부 · 선 자동 경로 · 매크로 새 창 (크롬 · 사본 데이터 · 실 DB 안 연다).

  python3 spike/ui_audit_l59.py <알다프라 그림 묶음이 든 데이터 폴더> <출력 폴더>
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
    sets = json.loads(urllib.request.urlopen(base + "/logic/api/drawings/sets").read())
    st = (sets.get("items") or [])[0]
    sheets = {q["sheet_no"]: q["id"] for q in st["sheets"]}
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
        pg.goto(f"{base}/logic/draw#d={sheets['FG_G-201']}")
        pg.wait_for_selector("#svg g.blk.macro", timeout=30000)
        time.sleep(0.8)
        # [1] 팔레트 — 보기 수 · 범례 기호
        n_pre = pg.evaluate("() => document.querySelectorAll('#palette .dw-preicon').length")
        icons = pg.evaluate("() => [...document.querySelectorAll('#palette .dw-preicon')].map(e => e.textContent)")
        note(f"팔레트 글자 상자 보기 {n_pre} · 감시 {sum(1 for t in icons if '/' in t and len(t) <= 4)} · 연산 {sum(1 for t in icons if t in ['Σ','AVG','△','|△|','ABS','K','-K','±','∫','D/DT','×','÷','√','Xⁿ','F(X)','F(T)','>','<','HL','LL','V>','LAG','T','PID','A','A/T','MED','I/P'])}")
        L = pg.evaluate("layout()")

        def svg_pt(x, y):
            box = pg.eval_on_selector("#svg", "e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }")
            return box[0] + x / L["W"] * box[2], box[1] + y / L["H"] * box[3]

        def ry(n):
            return L["TOP"] + ((n - 1) % L["N"]) * L["PITCH"] + L["PITCH"] / 2
        # [2] 선 자동 경로 — 빈 행 두 곳 사이에 블록을 놓고 선을 그으면 그 블록을 피해 꺾인다
        pg.evaluate("""() => { const L = layout(); addBlock('AND', 520, ry(44)); const b = S.doc.blocks[S.doc.blocks.length - 1]; b.id = 'obst'; b.y = +(ry(44) - b.h / 2).toFixed(2); render(); }""")
        pg.keyboard.press("w")
        x0, y0 = svg_pt(430, ry(44)); pg.mouse.click(x0, y0)
        x1, y1 = svg_pt(610, ry(44)); pg.mouse.move(x1, y1); time.sleep(0.2)
        ghost = pg.evaluate("() => { const e = document.querySelector('#overlay .wipline'); return e ? e.getAttribute('points') : null; }")
        n_alt = pg.evaluate("() => (S.wip && S.wip.routes || []).length")
        pg.mouse.click(x1, y1); pg.keyboard.press("Enter")
        w = pg.evaluate("() => S.doc.wires[S.doc.wires.length - 1]")
        bb = pg.evaluate("() => bboxOf(S.doc.blocks.find(b => b.id === 'obst'))")
        def hits(pts):
            for a, b in zip(pts, pts[1:]):
                xa, xb = sorted([a[0], b[0]]); ya, yb = sorted([a[1], b[1]])
                if xb > bb[0] and xa < bb[2] and yb > bb[1] and ya < bb[3]:
                    return True
            return False
        note(f"자동 경로: 후보 {n_alt} · 그어진 점 {len(w['pts'])} (직선이면 2) · 블록을 지남 {hits(w['pts'])} · 미리보기 {bool(ghost)}")
        pg.screenshot(path=str(OUT / "1_route.png"))
        # Tab 으로 다른 경로 — 새 선
        pg.keyboard.press("Escape")
        pg.keyboard.press("w")
        x0, y0 = svg_pt(430, ry(46)); pg.mouse.click(x0, y0)
        x1, y1 = svg_pt(610, ry(48)); pg.mouse.move(x1, y1); time.sleep(0.2)
        r0 = pg.evaluate("() => JSON.stringify(S.wip.routes[S.wip.ri || 0])")
        pg.keyboard.press("Tab"); time.sleep(0.1)
        r1 = pg.evaluate("() => JSON.stringify(S.wip.routes[S.wip.ri || 0])")
        note(f"Tab 다른 경로: 바뀜 {r0 != r1}")
        pg.keyboard.press("Escape")
        pg.evaluate("() => { S.doc.blocks = S.doc.blocks.filter(b => b.id !== 'obst'); S.doc.wires.pop(); S.dirty = false; render(); }")
        # [3] 매크로 새 창 — 시뮬레이션에서 매크로를 누르면 '내부 동작 보기' · 새 창이 부모 값으로 그린다
        pg.keyboard.press("v")
        pg.click("#simtoggle"); time.sleep(1.5)
        mid = pg.evaluate("() => S.doc.blocks.find(b => b.kind === 'MACRO').id")
        mb = pg.evaluate(f"() => {{ const b = S.doc.blocks.find(b => b.id === '{mid}'); return [b.x + b.w / 2, b.y + 6]; }}")
        mx, my = svg_pt(*mb); pg.mouse.click(mx, my)
        pg.wait_for_selector("#simmenu:not([hidden]) button")
        items = pg.evaluate("() => [...document.querySelectorAll('#simmenu button')].map(b => b.textContent)")
        has_open = any("내부 동작" in t for t in items)
        note(f"매크로 메뉴에 '내부 동작 보기' {has_open}")
        with ctx.expect_page() as pinfo:
            pg.click("#simmenu button:has-text('내부 동작')")
        child = pinfo.value; hook(child)
        child.wait_for_selector("#svg g.blk", timeout=30000)
        time.sleep(2.5)
        c_sheet = child.evaluate("() => S.doc.sheet_no")
        c_mp = child.evaluate("() => S.mparent ? [S.mparent.did, S.mparent.bid, !!S.mparent.inner] : null")
        c_banner = child.evaluate("() => (document.querySelector('#sim-out .grp b') || {}).textContent || ''")
        note(f"새 창: Typical {c_sheet} · 부모 {c_mp} · 띠 {c_banner[:40]!r}")
        # 부모에서 매크로 입력 단자에 1 을 주면 새 창의 그 Typical 입력 행이 1 로
        pin = pg.evaluate(f"() => {{ const sh = S.sim.res.sheet; const p = sh.ports.find(p => p.block === '{mid}' && p.dir === 'in'); return p ? [p.net, p.pin, p.at] : null; }}")
        before = child.evaluate("() => Object.values(S.sim.values || {}).filter(v => v === 1).length")
        pg.evaluate(f"() => setForce(S.id, 'net:{pin[0]}', 1)")
        time.sleep(2.5)
        after = child.evaluate("() => Object.values(S.sim.values || {}).filter(v => v === 1).length")
        link_rows = child.evaluate("() => ((S.mparent.inner || {}).links || []).filter(x => x.side === 'L' && ((x.rows || []).length || x.src)).length")
        note(f"부모 단자 {pin[1]} = 1 → 새 창 1 인 선 {before} → {after} · Typical 입력 행 ↔ 부모 행 연결 {link_rows}")
        child.screenshot(path=str(OUT / "2_macro_child.png"))
        pg.screenshot(path=str(OUT / "3_macro_parent.png"))
        # 새 창에서 선을 누르면 부모에게 간다 (부모 강제에 펼친 이름)
        cnet = child.evaluate("() => { const sh = S.sim.res.sheet; const p = sh.ports.find(p => p.dir === 'out'); return p ? String(p.net) : null; }")
        child.evaluate(f"() => setForce(S.id, 'net:{cnet}', 1)")
        time.sleep(2.0)
        pf = pg.evaluate("() => Object.keys(S.sim.forces[S.id] || {})")
        note(f"새 창 선 강제 → 부모 강제 열쇠 {[k for k in pf if '/' in k or k.startswith('net:')][:3]}")
        note(f"페이지 오류 {len(errors)} {errors[:3]}")
        br.close()
finally:
    srv.terminate()
    (OUT / "result.txt").write_text("\n".join(FOUND) + "\n", encoding="utf-8")
