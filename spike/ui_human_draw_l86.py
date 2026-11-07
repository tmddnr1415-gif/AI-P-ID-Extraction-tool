"""L86 — 사람이 프로그램에서 처음부터 한 프로젝트를 그리는 흐름을 그대로 흉내 낸다 (마우스 · 키보드만).
  새 프로젝트 → 새 그림 → 팔레트에서 기호 놓고 끌어 옮김 → 표 칸에 글 → W 로 선 긋기(행 자리 ↔ 단자 · 갈라짐) →
  속성(시간 · 이름) → 저장 → 새로 고침 뒤 같은가 → 되읽기 검증 → 시뮬레이션(행을 눌러 1/0 · 타이머) → 묶음으로 만들고 둘째 장 · FROM/TO →
  되돌리기 · 복사 · PDF/DXF.  단계마다 걸린 시간과 어긋난 것을 적는다.

  python3 spike/ui_human_draw_l86.py <버릴 데이터 폴더> <캡처 폴더>   (PW_CHROME=<chrome> 으로 브라우저 지정)"""
import json, os, sys, socket, subprocess, time, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data, out = sys.argv[1:3]
os.makedirs(out, exist_ok=True); os.makedirs(data, exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=data, PYTHONPATH=ROOT, PID_PAGE_WARM="0", PID_LOGIC_WARM="0", PID_ROWS_WARM="0", PID_DRAW_SEED="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
B = f"http://127.0.0.1:{port}"; ok = []; bad = []; steps = []
def chk(c, t): (ok if c else bad).append(t); print(("✔ " if c else "✕ ") + t)
def get(u): return urllib.request.urlopen(B + u, timeout=120).read()
T0 = time.time()
def step(name):
    now = time.time(); steps.append((name, round(now - T0, 2))); T0_[0] = now
T0_ = [T0]
def lap(name):
    now = time.time(); steps.append((name, round(now - T0_[0], 3))); T0_[0] = now

HELP = """() => { window.__h = {
  L: () => layout(),
  cl(x, y) { const r = document.querySelector('#svg').getBoundingClientRect(), L = layout(); return [r.left + x / L.W * r.width, r.top + y / L.H * r.height]; },
  see(x, y) { const sc = document.querySelector('#scroll'), L = layout(), r = document.querySelector('#svg').getBoundingClientRect(); const z = r.width / L.W;
    sc.scrollLeft = Math.max(0, x * z - sc.clientWidth / 2); sc.scrollTop = Math.max(0, y * z - sc.clientHeight / 2); },
  blk(id) { return S.doc.blocks.find(b => b.id === id); },
  last() { return S.doc.blocks[S.doc.blocks.length - 1]; },
  ports(id) { return ports(S.doc.blocks.find(b => b.id === id)); },
  ry: n => ry(n),
}; return true; }"""

try:
    for _ in range(120):
        try: get("/version"); break
        except Exception: time.sleep(0.5)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        kw = {"executable_path": os.environ["PW_CHROME"]} if os.environ.get("PW_CHROME") else {}
        br = pw.chromium.launch(**kw); pg = br.new_context(viewport={"width": 1600, "height": 950}).new_page(); errs = []; cons = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: cons.append(m.text) if m.type in ("error", "warning") else None)
        try:
            pg.goto(f"{B}/logic/draw?user=t")
            pg.wait_for_function("() => S.sym && !document.querySelector('#home').hidden", timeout=60000)
            pg.evaluate(HELP)
            lap("첫 화면")
            # ① 새 프로젝트 (첫 화면)
            pg.fill("#h-who", "홍길동")
            pg.click("#h-newproj"); pg.wait_for_selector("#modal:not([hidden])")
            pg.fill("#m-pjname", "L86 PUMP"); pg.click("#m-ok")
            pg.wait_for_function("() => document.querySelector('#modal').hidden && document.querySelector('#h-project').value === 'L86 PUMP'", timeout=10000)
            chk(True, "첫 화면에서 새 프로젝트 'L86 PUMP' 가 골라진다")
            lap("새 프로젝트")
            # ② 새 그림
            pg.click("#home .hm-actions [data-act=new]"); pg.wait_for_selector("#modal:not([hidden])")
            pg.fill("#m-name", "급수펌프 A 기동"); pg.fill("#m-sheet", "FG_G-301"); pg.fill("#m-dtitle", "BFP A START")
            pg.fill("#m-pname", "L86 PUMP"); pg.fill("#m-docno", "L86-LOGIC-001"); pg.fill("#m-rev", "0")
            pg.click("#m-ok")
            pg.wait_for_function("() => S.doc && S.id && document.querySelector('#home').hidden", timeout=20000)
            chk(pg.evaluate("() => S.doc.project") == "L86 PUMP", "새 그림이 프로젝트 'L86 PUMP' 에 들어간다")
            chk(pg.evaluate("() => S.doc.sheet_no") == "FG_G-301", "시트 이름이 그림에 적힌다")
            lap("새 그림")
            pg.evaluate("() => setZoom(1.6)")
            L = pg.evaluate("() => layout()")
            LX0, LX1, P = L["LX0"], L["LX1"], L["PITCH"]
            def ry(n): return pg.evaluate("n => ry(n)", n)
            def at(x, y):
                pg.evaluate("([x, y]) => __h.see(x, y)", [x, y]); time.sleep(0.03)
                return pg.evaluate("([x, y]) => __h.cl(x, y)", [x, y])
            def click_at(x, y, **kw):
                c = at(x, y); pg.mouse.click(c[0], c[1], **kw)
            def drag(x0, y0, x1, y1, steps_=8, shift=False):
                c0 = at(x0, y0); pg.mouse.move(c0[0], c0[1]); pg.mouse.down()
                if shift: pg.keyboard.down("Shift")
                for i in range(1, steps_ + 1):
                    xi = x0 + (x1 - x0) * i / steps_; yi = y0 + (y1 - y0) * i / steps_
                    c = pg.evaluate("([x, y]) => __h.cl(x, y)", [xi, yi]); pg.mouse.move(c[0], c[1]); time.sleep(0.01)
                pg.mouse.up()
                if shift: pg.keyboard.up("Shift")
            # ③ 팔레트에서 기호 놓고 끌어 옮김: 첫 입력 단자가 row 행 가운데 · 왼쪽 변이 x 에 오게
            def place(kind, x, row, nin=None):
                pg.evaluate("() => { const d = document.querySelector('#pal-inline'); if (d) d.open = true; }")   # L88 — 옆 칸 기호는 접혀 있다 (기호 창이 따로)
                pg.click(f"#palette button:has(span:text-is('{pg.evaluate('k => S.sym[k].name', kind)}'))")
                pg.wait_for_function("() => S.sel.size === 1")
                b = pg.evaluate("() => __h.last()")
                if nin:
                    pg.fill("#p-nin", str(nin)); pg.keyboard.press("Tab")
                    pg.wait_for_function("([id, k]) => __h.ports(id).filter(p => p[2] === 'in').length === k", [b["id"], nin])
                    b = pg.evaluate("() => __h.last()")
                ps = pg.evaluate("id => __h.ports(id)", b["id"])
                pin = next((p for p in ps if p[2] == "in"), ps[0])
                cx, cy = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
                dx, dy = x - b["x"], ry(row) - pin[1]
                drag(cx, cy, cx + dx, cy + dy)
                b2 = pg.evaluate("id => __h.blk(id)", b["id"]); ps2 = pg.evaluate("id => __h.ports(id)", b["id"])
                pin2 = next((p for p in ps2 if p[2] == "in"), ps2[0])
                chk(abs(pin2[1] - ry(row)) < 0.05 and abs(b2["x"] - x) <= P / 4 + 0.01, f"{kind} 를 끌어 놓으면 단자가 {row}행 가운데(어긋남 {abs(pin2[1] - ry(row)):.2f}) · x {b2['x']:.1f}≈{x}")
                return b["id"]
            t = time.time()
            and1 = place("AND", LX0 + 60, 1)                       # 입력 1·2행
            not1 = place("NOT", LX0 + 60, 3)                       # 입력 3행
            and2 = place("AND", LX0 + 130, 1)                      # AND1 · NOT
            gt1 = place("GT", LX0 + 200, 1)
            mem = place("MEMORY", LX0 + 270, 1)                    # S = GT · R = 3행 (두 칸)
            pd1 = place("PD", LX0 + 130, 5)                        # 3행에서 갈라져
            ann = place("ANN", LX0 + 200, 5)
            lamp = place("LAMP", LX0 + 340, 7)
            lap("기호 8개 놓고 옮김")
            pg.screenshot(path=f"{out}/01_blocks.png")
            # 단자 자리 (선 긋기에 쓴다)
            def port(id, kind, i=0): return [p for p in pg.evaluate("id => __h.ports(id)", id) if p[2] == kind][i]
            # ④ 표 칸 (왼쪽 KKS · 설명 · 오른쪽 설명) — 두 번 눌러 쓰고 Enter 로 다음 행
            def cell(side, n, f, text, enter=True):
                if side == "right": n = L["N"] + n                       # 오른쪽 행은 N+1 부터
                sel = f'#svg rect.cell[data-side="{side}"][data-n="{n}"][data-f="{f}"]'
                pg.wait_for_selector(sel, state="attached")
                r = pg.evaluate("s => { const e = document.querySelector(s); const x = +e.getAttribute('x') + e.getAttribute('width') / 2, y = +e.getAttribute('y') + e.getAttribute('height') / 2; return [x, y]; }", sel)
                c = at(r[0], r[1]); pg.mouse.dblclick(c[0], c[1])
                pg.wait_for_selector("#cellin:not([hidden])", timeout=5000)
                pg.fill("#cellin", text); pg.keyboard.press("Enter" if enter else "Escape")
            cell("left", 1, "kks", "10LAC10CP001"); pg.keyboard.press("Escape")
            cell("left", 1, "desc", "BFP A START PB"); cell("left", 2, "desc", "SUCTION PRESS OK", enter=False)
            cell("left", 3, "desc", "BFP A TRIP", enter=False)
            cell("right", 1, "desc", "BFP A START CMD", enter=False); cell("right", 2, "desc", "BFP A TRIP ALARM", enter=False)
            got = pg.evaluate("() => [S.doc.left[1], S.doc.left[2], S.doc.left[3], S.doc.right[S.doc.N + 1], S.doc.right[S.doc.N + 2]]")
            chk(got[0] and got[0].get("kks") == "10LAC10CP001" and got[0].get("desc") == "BFP A START PB" and (got[1] or {}).get("desc") == "SUCTION PRESS OK" and (got[4] or {}).get("desc") == "BFP A TRIP ALARM", f"표 칸에 적은 글이 그대로 — {got}")
            lap("표 칸 5개")
            # ⑤ 선 — W, 행 자리 → 단자 (단자에 닿으면 끝) · 단자 → 행 자리 · 갈라짐 (선 몸통에서 시작)
            def wire(p0, p1, dashed=False, expect_dot=False):
                n0 = pg.evaluate("() => S.doc.wires.length")
                pg.keyboard.press("d" if dashed else "w")
                click_at(p0[0], p0[1]); click_at(p1[0], p1[1])
                if pg.evaluate("() => !!S.wip"): pg.keyboard.press("Enter")   # 단자 · 행이 아니면 Enter 로 끝
                pg.wait_for_function(f"() => S.doc.wires.length === {n0 + 1} && !S.wip", timeout=5000)
                w = pg.evaluate("() => S.doc.wires[S.doc.wires.length - 1]")
                a, z = w["pts"][0], w["pts"][-1]
                d0 = min(abs(a[0] - p0[0]) + abs(a[1] - p0[1]), 99); d1 = abs(z[0] - p1[0]) + abs(z[1] - p1[1])
                orth = all(abs(w["pts"][i][0] - w["pts"][i + 1][0]) < 0.01 or abs(w["pts"][i][1] - w["pts"][i + 1][1]) < 0.01 for i in range(len(w["pts"]) - 1))
                chk(d1 < 0.05 and orth and (not expect_dot or (w.get("dots") or [])), f"선 {w['id']}: 끝이 단자에 정확히 ({d1:.2f}) · 직각 {orth}{' · 갈라진 점 ' + str(bool(w.get('dots'))) if expect_dot else ''} · 점 {len(w['pts'])}")
                pg.keyboard.press("v")
                return w["id"]
            wire([LX0, ry(1)], port(and1, "in", 0))
            wire([LX0, ry(2)], port(and1, "in", 1))
            w3 = wire([LX0, ry(3)], port(not1, "in"))
            wire(port(and1, "out"), port(and2, "in", 0))
            wire(port(not1, "out"), port(and2, "in", 1))
            wire(port(and2, "out"), port(gt1, "in"))
            wire(port(gt1, "out"), port(mem, "in", 0))
            wire(port(mem, "out", 0), [LX1, ry(1)])
            # 갈라짐: 3행 선 몸통(행 가운데 · 격자 위) 에서 PD 로
            wire([LX0 + 30, ry(3)], port(pd1, "in"), expect_dot=True)
            wire(port(pd1, "out"), port(ann, "in"))
            wire([LX0 + 30, ry(3)], port(mem, "in", 1), expect_dot=True)      # R
            wire(port(mem, "out", 0), port(lamp, "in", 0), expect_dot=True)   # 출력 선에서 갈라져 램프
            wire(port(pd1, "out"), [LX1, ry(2)], expect_dot=True)
            lap("선 13개")
            pg.screenshot(path=f"{out}/02_wired.png")
            # ⑥ 속성 — GT 시간 2초 · PB 는 없음 · 위 글
            pg.evaluate(f"() => {{ S.sel = new Set(['{gt1}']); S.selWire = null; render(); }}")
            pg.fill("#p-t", "2"); pg.keyboard.press("Tab")
            chk(pg.evaluate(f"() => __h.blk('{gt1}').param.t") == 2, "GT 시간을 2초로")
            pg.fill("#p-above", "T = 2 s"); pg.keyboard.press("Tab")
            lap("속성")
            # ⑥b 기호를 옮기면 붙은 선이 따라간다 (L86) — 끌기 · 화살표 · 입력 수 · 묶어 끌기
            def attached(wid, end, bid, kind, i=0):
                w = pg.evaluate(f"() => S.doc.wires.find(w => w.id === '{wid}')"); pt = w["pts"][end]; pp = port(bid, kind, i)
                orth = all(abs(w["pts"][k][0] - w["pts"][k + 1][0]) < 0.01 or abs(w["pts"][k][1] - w["pts"][k + 1][1]) < 0.01 for k in range(len(w["pts"]) - 1))
                return abs(pt[0] - pp[0]) < 0.05 and abs(pt[1] - pp[1]) < 0.05 and orth
            def loose(): return pg.evaluate("() => looseEnds().length")
            chk(loose() == 0, f"다 이은 그림 — 매달린 선 끝 {loose()}")
            bb = pg.evaluate(f"() => __h.blk('{and1}')")
            drag(bb["x"] + bb["w"] / 2, bb["y"] + bb["h"] / 2, bb["x"] + bb["w"] / 2 - 10, bb["y"] + bb["h"] / 2 + 10 * P)   # 빈 자리(11·12행)로
            bb2 = pg.evaluate(f"() => __h.blk('{and1}')")
            chk(abs(bb2["y"] - bb["y"] - 10 * P) < 0.05, f"AND1 을 열 행 아래로 끌었다 (y {bb['y']} → {bb2['y']})")
            chk(attached("w1", -1, and1, "in", 0) and attached("w2", -1, and1, "in", 1) and attached("w4", 0, and1, "out"), "끌어 옮긴 AND1 의 세 선이 단자에 붙은 채 직각으로 따라온다")
            chk(loose() == 0, f"옮긴 뒤 매달린 선 끝 {loose()}")
            chk(pg.evaluate("() => S.doc.wires.filter(w => crossesBlock(w.pts)).length") == 0, "옮긴 뒤 다른 기호 속을 지나는 선 0 (지나게 되면 경로를 다시 잡는다)")
            pg.keyboard.press("Control+z")
            chk(attached("w1", -1, and1, "in", 0) and pg.evaluate(f"() => __h.blk('{and1}').y") == bb["y"], "Ctrl+Z — 기호도 선도 되돌아온다")
            pg.evaluate(f"() => {{ S.sel = new Set(['{gt1}']); S.selWire = null; render(); }}")
            pg.keyboard.press("Shift+ArrowDown"); pg.keyboard.press("Shift+ArrowDown")
            chk(attached("w6", -1, gt1, "in") and attached("w7", 0, gt1, "out"), "화살표로 GT 를 두 행 내려도 앞뒤 선이 따라온다")
            pg.keyboard.press("Control+z"); pg.keyboard.press("Control+z")
            # L87 — 선 몸통에서 갈라진 선(T 이음 · 연결점)도 따라온다: PD 를 내리면 PD 출력선(w10) 몸통에서 갈라진 w13 이 · MEMORY 를 옮기면 w12 가
            def on_body(wid_branch, wid_body):
                return pg.evaluate(f"() => {{ const o = S.doc.wires.find(w => w.id === '{wid_branch}'), w = S.doc.wires.find(w => w.id === '{wid_body}'); return [o.pts[0], o.pts[o.pts.length - 1]].some(e => !!onBodySeg(w.pts, e)) && (o.dots || []).every(d => !!onBodySeg(w.pts, d) || w.pts.some(q => Math.hypot(q[0] - d[0], q[1] - d[1]) < .6)); }}")
            chk(on_body("w13", "w10") and on_body("w12", "w8"), "처음: w13 은 w10 몸통 · w12 는 w8 몸통에서 갈라진다")
            pg.evaluate(f"() => {{ S.sel = new Set(['{pd1}']); S.selWire = null; render(); document.querySelector('#stage').focus(); }}")
            pg.keyboard.press("Shift+ArrowDown"); pg.keyboard.press("Shift+ArrowDown")
            chk(on_body("w13", "w10") and loose() == 0, f"PD 를 두 행 내리면 갈라진 선 w13 · 연결점도 새 몸통 위로 (매달림 {loose()})")
            pg.keyboard.press("Control+z"); pg.keyboard.press("Control+z")
            bm = pg.evaluate(f"() => __h.blk('{mem}')")
            drag(bm["x"] + bm["w"] / 2, bm["y"] + bm["h"] / 4, bm["x"] + bm["w"] / 2 + 2 * P, bm["y"] + bm["h"] / 4 + 3 * P)
            chk(pg.evaluate("() => S.doc.wires.filter(w => crossesBlock(w.pts)).length") == 0, "MEMORY 를 옮긴 뒤 다른 기호 속을 지나는 선 0")
            chk(on_body("w12", "w8") and attached("w8", 0, mem, "out", 0) and loose() == 0, f"MEMORY 를 끌어 옮기면 출력선 w8 과 거기서 갈라진 w12 가 함께 (매달림 {loose()})")
            pg.screenshot(path=f"{out}/02c_branch_follow.png")
            pg.keyboard.press("Control+z")
            chk(on_body("w12", "w8") and loose() == 0, "Ctrl+Z")
            pg.evaluate(f"() => {{ S.sel = new Set(['{and2}']); S.selWire = null; render(); }}")
            pg.fill("#p-nin", "3"); pg.keyboard.press("Tab")
            chk(pg.evaluate(f"() => __h.ports('{and2}').filter(p => p[2] === 'in').length") == 3, "AND2 입력 수 2 → 3")
            chk(attached("w4", -1, and2, "in", 0) and attached("w5", -1, and2, "in", 1) and attached("w6", 0, and2, "out") and loose() == 0, "입력 수를 늘려 막대가 길어져도 두 입력 선은 입력 단자에 · 출력 선은 출력 단자에 붙은 채")
            pg.evaluate("() => document.querySelector('#stage').focus()"); pg.keyboard.press("Control+z")   # 속성 칸에 초점이 남으면 Ctrl+Z 가 안 듣는다 — 사람은 그림을 누른다
            chk(pg.evaluate(f"() => __h.ports('{and2}').filter(p => p[2] === 'in').length") == 2 and attached("w5", -1, and2, "in", 1), "Ctrl+Z — 입력 수도 선도 되돌아온다")
            # 묶어 끌기: AND2 · GT 를 사각형으로 고르고 함께 끌면 둘 사이 선은 통째로, 바깥 선은 끝만
            a2 = pg.evaluate(f"() => bboxOf(__h.blk('{and2}'))"); g1 = pg.evaluate(f"() => bboxOf(__h.blk('{gt1}'))")
            mq = [min(a2[0], g1[0]) - 8, min(a2[1], g1[1]) - 8, max(a2[2], g1[2]) + 6, max(a2[3], g1[3]) + 6]
            hit = pg.evaluate("([x, y]) => { const c = __h.cl(x, y); const e = document.elementFromPoint(c[0], c[1]); return e && (e.id || e.tagName + '.' + e.getAttribute('class')); }", mq[:2])
            drag(*mq)
            chk(pg.evaluate(f"() => S.sel.has('{and2}') && S.sel.has('{gt1}') && S.sel.size === 2"), f"사각형으로 AND2 · GT 둘을 골랐다 (고른 것 {pg.evaluate('() => [...S.sel]')} · 시작점 요소 {hit} · 사각형 {[round(v, 1) for v in mq]} · AND2 {a2} GT {g1})")
            w6b = pg.evaluate("() => S.doc.wires.find(w => w.id === 'w6').pts")
            c0 = pg.evaluate(f"() => {{ const b = __h.blk('{and2}'); return [b.x + b.w / 2, b.y + b.h / 2]; }}")
            drag(c0[0], c0[1], c0[0], c0[1] + 10 * P)                 # 빈 자리(11·12행)로 — 다른 기호와 겹치면 비켜 놓느라 둘이 다르게 움직인다
            w6a = pg.evaluate("() => S.doc.wires.find(w => w.id === 'w6').pts")
            chk(len(w6a) == len(w6b) and all(abs(q[1] - p[1] - 10 * P) < 0.05 and abs(q[0] - p[0]) < 0.05 for p, q in zip(w6b, w6a)), f"둘을 함께 끌면 사이 선(w6)은 통째로 따라온다 ({w6b} → {w6a})")
            chk(attached("w5", -1, and2, "in", 1) and attached("w7", 0, gt1, "out") and loose() == 0, "바깥 선(w5 · w7)은 끝만 따라와 붙은 채")
            pg.keyboard.press("Control+z")
            # 매달린 끝: NOT 을 지우면 두 선 끝이 붉은 고리 · 되돌리면 사라짐 · 빈 자리에 끝낸 선도 고리
            pg.evaluate(f"() => {{ S.sel = new Set(['{not1}']); S.selWire = null; render(); }}"); pg.keyboard.press("Delete")
            chk(loose() == 2 and pg.evaluate("() => document.querySelectorAll('#svg #loose circle.loose').length") == 2, f"NOT 을 지우면 매달린 선 끝 2 (붉은 고리 {pg.evaluate("() => document.querySelectorAll('#svg circle.loose').length")})")
            pg.screenshot(path=f"{out}/02b_loose.png")
            pg.keyboard.press("Control+z"); chk(loose() == 0, "되돌리면 고리가 사라진다")
            n0 = pg.evaluate("() => S.doc.wires.length"); pg.keyboard.press("w"); click_at(LX0 + 100, ry(12)); click_at(LX0 + 160, ry(12)); pg.keyboard.press("Enter"); pg.keyboard.press("v")
            chk(pg.evaluate("() => S.doc.wires.length") == n0 + 1 and loose() == 2, f"빈 자리에서 빈 자리로 그은 선 — 양 끝 고리 ({loose()})")
            pg.evaluate("() => { S.selWire = S.doc.wires[S.doc.wires.length - 1].id; S.sel = new Set(); render(); }"); pg.keyboard.press("Delete")
            chk(pg.evaluate("() => S.doc.wires.length") == n0 and loose() == 0, "그 선을 지우면 고리 0")
            lap("선 따라오기 · 고리")
            # 사람이 흔히 하는 일: 막대를 세 칸으로 늘려 두고 선은 둘만 — 검증 · 시뮬레이션이 그래도 읽어야 한다
            pg.evaluate(f"() => {{ S.sel = new Set(['{and2}']); S.selWire = null; render(); }}")
            pg.fill("#p-nin", "3"); pg.keyboard.press("Tab"); pg.evaluate("() => document.querySelector('#stage').focus()")
            pg.click("#verify"); pg.wait_for_function("() => S.verify", timeout=120000)
            v3 = pg.evaluate("() => S.verify"); b3 = next((b for b in v3.get("blocks") or [] if b["id"] == and2), {})
            chk(b3.get("ok") and b3.get("inputs") == 2, f"세 칸 막대에 선 둘 — 되읽기: {b3.get('read')} 입력 {b3.get('inputs')} {b3.get('why') or ''} · 매달림 {v3.get('dangling')}")
            pg.evaluate("() => { S.verify = null; document.querySelector('#verify-card').hidden = true; }")
            pg.keyboard.press("Control+z"); chk(pg.evaluate(f"() => __h.ports('{and2}').filter(p => p[2] === 'in').length") == 2, "막대를 두 칸으로 되돌림")
            # ⑦ 저장 (Ctrl+S) → 새로 고침 → 같은가
            SNAP = "() => { const t = o => Object.fromEntries(Object.entries(o).map(([k, r]) => [k, Object.fromEntries(Object.entries(r).filter(([q, v]) => v))])); return JSON.stringify({b: S.doc.blocks, w: S.doc.wires, l: t(S.doc.left), r: t(S.doc.right)}); }"
            snap = pg.evaluate(SNAP)
            pg.keyboard.press("Control+s")
            pg.wait_for_function("() => !S.dirty && document.querySelector('#status').textContent.startsWith('저장됨')", timeout=15000)
            lap("저장")
            did = pg.evaluate("() => S.id")
            pg.reload(); pg.wait_for_function("() => S.doc && S.id", timeout=30000); pg.evaluate(HELP)
            snap2 = pg.evaluate(SNAP)
            if snap != snap2:
                a, b2 = json.loads(snap), json.loads(snap2)
                for k in a:
                    if a[k] != b2[k]:
                        if isinstance(a[k], list):
                            for i, (x, y) in enumerate(zip(a[k], b2[k])):
                                if len(a[k]) != len(b2[k]) and i == 0: print(f"   다름 {k}: 수 {len(a[k])} → {len(b2[k])}")
                                if x != y: print(f"   다름 {k}[{i}]:", {q: (x.get(q), y.get(q)) for q in set(x) | set(y) if x.get(q) != y.get(q)}); break
                        else: print(f"   다름 {k}:", a[k], b2[k])
            chk(json.loads(snap) == json.loads(snap2), "저장 뒤 새로 고쳐도 블록 · 선 · 표가 그대로")
            chk(pg.evaluate("() => S.id") == did, "새로 고치면 같은 그림이 열린다")
            lap("새로 고침")
            # ⑧ 되읽기 검증 (PDF → 분석기)
            pg.click("#verify"); pg.wait_for_function("() => S.verify", timeout=120000)
            v = pg.evaluate("() => S.verify")
            bl = v.get("blocks") or []
            chk(v.get("ok") is True, f"되읽기 검증 — ok={v.get('ok')} 블록 {sum(1 for b in bl if b.get('ok'))}/{len(bl)} 행 {v.get('rows', {}).get('read')}/{v.get('rows', {}).get('drawn')} 매달림 {v.get('dangling')} {v.get('why') or ''}")
            for b in bl:
                if not b.get("ok"): print("   ✕", b)
            lap("되읽기 검증")
            pg.screenshot(path=f"{out}/03_verify.png")
            # ⑨ 시뮬레이션 — 1·2행 1 → AND1 1 · 3행 0 → NOT 1 → AND2 1 → GT 2초 뒤 → MEMORY S → 오른쪽 1행
            pg.click("#simtoggle"); pg.wait_for_function("() => S.sim && S.sim.on && S.sim.res", timeout=30000)
            def force_row(n, v):
                st = pg.evaluate(f"() => {{ const e = document.querySelector('#svg .rowstub[data-n=\"{n}\"]'); return [+e.getAttribute('cx'), +e.getAttribute('cy')]; }}")
                click_at(st[0], st[1]); pg.wait_for_selector("#simmenu:not([hidden])")
                seq = pg.evaluate("() => S.sim.seq || 0")
                pg.click(f"#simmenu button.v{v}")
                pg.wait_for_function(f"() => S.sim.seq > {seq} && S.sim.res && S.sim.res.seq !== undefined || S.sim.res", timeout=15000)
                time.sleep(0.5)
            def net_val(wid):
                return pg.evaluate(f"() => {{ const sh = S.sim.res.sheet; const k = Object.keys(sh.nets).find(k => sh.nets[k].wires.includes('{wid}')); return [k, S.sim.values[k]]; }}")
            force_row(1, 1); force_row(2, 1)
            w_and1 = pg.evaluate("() => S.doc.wires[3].id")
            chk(net_val(w_and1)[1] == 1, f"1·2행에 1 → AND 출력 선 {net_val(w_and1)}")
            w_out = pg.evaluate("() => S.doc.wires[7].id"); w_gt = pg.evaluate("() => S.doc.wires[6].id")
            k_gt = net_val(w_gt)[0]
            fr = pg.evaluate(f"() => S.sim.frames.map(f => [f.t, f.values['{k_gt}']])")
            chk(fr and fr[0][1] == 0 and fr[-1][1] == 1 and fr[-1][0] >= 2, f"GT 2초 — 누른 순간 0, 2초 뒤 1 (틀 {fr})")
            chk(net_val(w_out)[1] == 1, f"MEMORY SET → 오른쪽 1행 출력 선 = {net_val(w_out)[1]}")
            force_row(3, 1)
            chk(net_val(w_out)[1] == 0, f"3행(TRIP) 1 → RESET → 출력 0 (= {net_val(w_out)[1]})")
            pg.screenshot(path=f"{out}/04_sim.png")
            pg.click("#simtoggle")
            lap("시뮬레이션")
            # ⑩ 묶음으로 만들고 둘째 장 · FROM/TO
            pg.click("#set-make"); pg.wait_for_function("() => S.doc.set && S.setInfo && S.setInfo.sheets.length === 1", timeout=20000)
            chk(True, "묶음으로 만들기 → 묶음 카드에 1장")
            pg.click("#set-add"); pg.wait_for_selector("#modal:not([hidden])"); pg.fill("#m-sheet", "FG_G-302"); pg.fill("#m-name", "급수펌프 A 보호"); pg.click("#m-ok")
            pg.wait_for_function("() => S.doc && S.doc.sheet_no === 'FG_G-302' && S.setInfo && S.setInfo.sheets.length === 2", timeout=20000)
            chk(True, "묶음에 둘째 장 FG_G-302")
            pg.evaluate(HELP)
            # 둘째 장: 왼쪽 1행 FROM = FG_G-301 1행 (자동완성) → 오른쪽 1행
            # FROM 칸: 'FG_G' 까지 치면 시트 목록 → Enter 로 시트 → 그 장의 출력 행 목록 → Enter 로 행 (자동완성)
            sel = f'#svg rect.cell[data-side="left"][data-n="1"][data-f="fm"]'
            r = pg.evaluate("s => { const e = document.querySelector(s); return [+e.getAttribute('x') + e.getAttribute('width') / 2, +e.getAttribute('y') + e.getAttribute('height') / 2]; }", sel)
            c = at(r[0], r[1]); pg.mouse.dblclick(c[0], c[1]); pg.wait_for_selector("#cellin:not([hidden])")
            pg.type("#cellin", "FG_G"); pg.wait_for_function("() => !document.querySelector('#cellac').hidden && document.querySelector('#cellac .ac-it')", timeout=5000)
            pg.keyboard.press("Enter")
            pg.wait_for_function("() => document.querySelector('#cellac .ac-head') && document.querySelector('#cellac .ac-head').textContent.includes('출력')", timeout=5000)
            acs = pg.evaluate("() => [...document.querySelectorAll('#cellac .ac-it')].map(e => e.textContent)")
            pg.keyboard.press("Enter"); pg.wait_for_function("() => document.querySelector('#cellin').hidden", timeout=5000)
            chk(pg.evaluate("() => (S.doc.left[1] || {}).fm") == "FG_G-301-60", f"FROM 자동완성 — 시트 → 출력 행 ({acs}) → {pg.evaluate('() => (S.doc.left[1] || {}).fm')}")
            cell("left", 1, "desc", "BFP A START CMD", enter=False)
            n1 = place("NOT", LX0 + 60, 1)
            wire([LX0, ry(1)], port(n1, "in")); wire(port(n1, "out"), [LX1, ry(1)])
            pg.keyboard.press("Control+s"); pg.wait_for_function("() => !S.dirty && document.querySelector('#status').textContent.startsWith('저장됨')", timeout=15000)
            time.sleep(0.8)
            fm = pg.evaluate("() => S.doc.left[1]")
            print("   둘째 장 1행:", fm)
            # 첫 장으로 돌아가 오른쪽 1행 TO 가 채워졌나 (autolink)
            first_li = pg.evaluate("() => S.setInfo.sheets[0].id")
            pg.click(f"#set-list li[data-id='{first_li}']"); pg.wait_for_function(f"() => S.id === '{first_li}'", timeout=15000)
            r1 = pg.evaluate("() => S.doc.right[S.doc.N + 1]")
            chk(bool((r1 or {}).get("to")), f"첫 장 오른쪽 1행 TO 가 둘째 장으로 이어진다 — {r1}")
            # 묶음 시뮬레이션: 첫 장에서 1 · 2행을 켜고 둘째 장으로 넘어가면 FROM 으로 받은 1행이 1 · NOT 출력 0
            pg.click("#simtoggle"); pg.wait_for_function("() => S.sim && S.sim.on && S.sim.res", timeout=30000)
            pg.click("#sim-reset"); time.sleep(0.6)                   # 앞서 준 3행(TRIP) 1 이 남아 있다 — 사람도 '처음으로' 를 누른다
            force_row(1, 1); force_row(2, 1)
            for _ in range(3): pg.click("#sim-step"); time.sleep(0.5)
            second = pg.evaluate("() => S.setInfo.sheets[1].id")
            pg.evaluate("() => { S.sim.res.__old = true; window.__simlog = []; const _api = api; api = async (u, o) => { const r = await _api(u, o); if (u.includes('/simulate')) { const b = JSON.parse(o.body); __simlog.push({ u: u.slice(-30), state: Object.keys(b.state || {}), forces: b.forces, doc: !!b.doc, sig: r.sig, frames: ((r.focus && r.focus.frames) || []).map(f => f.t), rstate: Object.keys(r.state || {}) }); } return r; }; }")
            print("   첫 장 sig", pg.evaluate("() => [S.sim.sig, Object.keys(S.sim.states)]"))
            pg.click(f"#set-list li[data-id='{second}']"); pg.wait_for_function(f"() => S.id === '{second}' && S.sim.res && !S.sim.res.__old && S.sim.res.sheet", timeout=20000); time.sleep(0.3)
            pg.evaluate(HELP)
            vin = net_val(pg.evaluate("() => S.doc.wires[0].id")); vout = net_val(pg.evaluate("() => S.doc.wires[1].id"))
            chk(vin[1] == 1 and vout[1] == 0, f"둘째 장 — FROM 으로 받은 1행 {vin[1]} · NOT 출력 {vout[1]} (첫 장의 누름단추가 건너온다)")
            if vin[1] != 1: print("   simlog", pg.evaluate("() => __simlog"))
            pg.screenshot(path=f"{out}/04b_sim_sheet2.png")
            pg.click("#simtoggle")
            pg.click(f"#set-list li[data-id='{first_li}']"); pg.wait_for_function(f"() => S.id === '{first_li}'", timeout=15000)
            lap("묶음 · 둘째 장 · FROM/TO")
            # ⑪ 되돌리기 · 복사 · 붙이기 · 지우기
            pg.evaluate(HELP)
            nb = pg.evaluate("() => S.doc.blocks.length")
            pg.evaluate(f"() => {{ S.sel = new Set(['{and1}']); S.selWire = null; render(); }}")
            pg.keyboard.press("Delete"); chk(pg.evaluate("() => S.doc.blocks.length") == nb - 1, "Delete 로 기호 지움")
            pg.keyboard.press("Control+z"); chk(pg.evaluate("() => S.doc.blocks.length") == nb, "Ctrl+Z 되돌림")
            bb = pg.evaluate(f"() => __h.blk('{and1}')"); click_at(bb["x"] + bb["w"] / 2, bb["y"] + bb["h"] / 2)
            chk(pg.evaluate(f"() => S.sel.has('{and1}')"), "되돌린 기호를 눌러 고름")
            pg.keyboard.press("Control+c"); pg.keyboard.press("Control+v")
            chk(pg.evaluate("() => S.doc.blocks.length") == nb + 1, "Ctrl+C · V 붙이기")
            pg.keyboard.press("Control+z")
            pg.keyboard.press("Control+s"); pg.wait_for_function("() => !S.dirty", timeout=15000)
            lap("되돌리기 · 복사")
            # ─── L87 — draw.io 에서 배운 것 : 찾기 · 장 넘기기 · 끌어 선 · ＋ 잇기 · 두 번 눌러 넣기 · Ctrl+끌기 · 메뉴 · 임시 저장 · 미니맵 ───
            def ov_center(sel):
                return pg.evaluate("s => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }", sel)
            def pick(q):
                pg.wait_for_selector("#qpick", timeout=5000); pg.fill("#qpick-q", q); pg.keyboard.press("Enter")
                pg.wait_for_function("() => !document.querySelector('#qpick')", timeout=5000)
            # 찾기 — 'START CMD' 는 첫 장 오른쪽 1행 · 둘째 장 왼쪽 1행
            pg.evaluate("() => document.querySelector('#stage').focus()"); pg.keyboard.press("Control+f")
            pg.wait_for_selector("#find:not([hidden])", timeout=5000); pg.type("#find-q", "start cmd")
            pg.wait_for_function("() => S.find && S.find.hits.length >= 2", timeout=10000)
            fh = pg.evaluate("() => S.find.hits.map(h => [h.sheet_no, h.where])")
            chk(any(h[0] == "FG_G-301" for h in fh) and any(h[0] == "FG_G-302" for h in fh), f"Ctrl+F 'start cmd' — 묶음 두 장에서 찾음 {fh}")
            i2 = next(i for i, h in enumerate(fh) if h[0] == "FG_G-302")
            pg.click(f"#find-list .fd-it[data-i='{i2}']"); pg.wait_for_function("() => S.doc && S.doc.sheet_no === 'FG_G-302'", timeout=15000)
            chk(True, "찾은 줄을 누르면 그 장(FG_G-302)이 열리고 그 행이 깜빡인다")
            pg.screenshot(path=f"{out}/06_find.png")
            pg.keyboard.press("Escape"); pg.evaluate("() => document.querySelector('#stage').focus()")
            pg.keyboard.press("PageUp"); pg.wait_for_function("() => S.doc && S.doc.sheet_no === 'FG_G-301'", timeout=15000)
            chk(True, "PgUp — 앞 장으로")
            pg.keyboard.press("PageDown"); pg.wait_for_function("() => S.doc && S.doc.sheet_no === 'FG_G-302'", timeout=15000)
            chk(True, "PgDn — 다음 장으로")
            lap("찾기 · 장 넘기기")
            # 셋째 장 — 새 방법으로만 그린다
            pg.click("#set-add"); pg.wait_for_selector("#modal:not([hidden])"); pg.fill("#m-sheet", "FG_G-303"); pg.fill("#m-name", "급수펌프 A 경보"); pg.click("#m-ok")
            pg.wait_for_function("() => S.doc && S.doc.sheet_no === 'FG_G-303'", timeout=20000); pg.evaluate(HELP); pg.evaluate("() => setZoom(1.6)")
            d3 = pg.evaluate("() => S.id")
            # 빈 곳 두 번 누름 → 고르개 → AND
            c = at(LX0 + 60, ry(2)); pg.mouse.dblclick(c[0], c[1]); pick("and")
            a3 = pg.evaluate("() => __h.last()")
            chk(a3["kind"] == "AND", f"빈 곳 두 번 누름 → 고르개에서 'and' Enter → AND 를 그 자리에 ({a3['kind']})")
            # 행 자리에서 단자로 끌어 선 (도구를 바꾸지 않고)
            def drag_wire(p0, p1):
                n0 = pg.evaluate("() => S.doc.wires.length")
                c0 = at(p0[0], p0[1]); pg.mouse.move(c0[0] + 0.3, c0[1] + 0.3); time.sleep(0.05)
                hov = pg.evaluate("() => !!S.hoverPort")
                pg.mouse.down()
                for i in range(1, 9):
                    c = pg.evaluate("([x, y]) => __h.cl(x, y)", [p0[0] + (p1[0] - p0[0]) * i / 8, p0[1] + (p1[1] - p0[1]) * i / 8]); pg.mouse.move(c[0], c[1]); time.sleep(0.01)
                pg.mouse.up(); time.sleep(0.05)
                ok_ = pg.evaluate(f"() => S.doc.wires.length === {n0 + 1} && !S.wip")
                w = pg.evaluate("() => S.doc.wires[S.doc.wires.length - 1]")
                z = w["pts"][-1]
                return hov, ok_ and abs(z[0] - p1[0]) < 0.05 and abs(z[1] - p1[1]) < 0.05, pg.evaluate("() => S.tool")
            r1 = drag_wire([LX0, ry(1)], port(a3["id"], "in", 0)); r2 = drag_wire([LX0, ry(2)], port(a3["id"], "in", 1))
            chk(r1[0] and r1[1] and r2[1] and r1[2] == "select", f"행 자리에 가져가면 파란 고리 · 끌어 놓으면 단자에 붙은 선 (도구는 그대로 '{r1[2]}') {r1} {r2}")
            # 기호를 누르면 '＋' — 누르면 고르개 → GT 를 오른쪽 같은 행에 놓고 이음
            bb = pg.evaluate(f"() => __h.blk('{a3['id']}')"); click_at(bb["x"] + bb["w"] / 2, bb["y"] + bb["h"] / 2)
            qc = ov_center("#overlay circle.qc"); chk(qc is not None, "기호를 고르면 출력 옆에 '＋' 손잡이")
            pg.mouse.click(qc[0], qc[1]); pick("GT")
            g3 = pg.evaluate("() => __h.last()"); wl = pg.evaluate("() => S.doc.wires[S.doc.wires.length - 1]")
            ao, gi = port(a3["id"], "out"), port(g3["id"], "in")
            chk(g3["kind"] == "GT" and abs(ao[1] - gi[1]) < 0.05 and gi[0] > ao[0] and max(abs(wl["pts"][0][0] - ao[0]), abs(wl["pts"][0][1] - ao[1]), abs(wl["pts"][-1][0] - gi[0]), abs(wl["pts"][-1][1] - gi[1])) < 0.05 and pg.evaluate(f"() => S.sel.has('{g3['id']}')"),
                f"'＋' → GT 가 같은 행 오른쪽에 놓이고 AND 출력과 이어짐 (그리고 GT 가 골라져 다시 ＋) — {g3['kind']} out {ao} in {gi} 선 {wl['pts']} 고름 {pg.evaluate('() => [...S.sel]')}")
            qc = ov_center("#overlay circle.qc"); pg.mouse.click(qc[0], qc[1]); pick("ann")
            n3 = pg.evaluate("() => __h.last()")
            chk(n3["kind"] == "ANN" and pg.evaluate("() => looseEnds().length") == 0, f"한 번 더 '＋' → 경보(ANN) — 매달린 끝 {pg.evaluate('() => looseEnds().length')}")
            # GT 출력 → 오른쪽 1행 (끌어서)
            r3 = drag_wire(port(g3["id"], "out"), [LX1, ry(1)])
            chk(r3[1], f"GT 출력에서 오른쪽 1행 자리로 끌어 선 {r3}")
            pg.screenshot(path=f"{out}/07_quick_connect.png")
            lap("두 번 눌러 넣기 · 끌어 선 · ＋ 잇기")
            # Ctrl+끌기 = 복사해 옮기기
            nb3 = pg.evaluate("() => S.doc.blocks.length")
            bb = pg.evaluate(f"() => __h.blk('{n3['id']}')")
            pg.keyboard.down("Control"); drag(bb["x"] + bb["w"] / 2, bb["y"] + bb["h"] / 2, bb["x"] + bb["w"] / 2, bb["y"] + bb["h"] / 2 + 4 * P); pg.keyboard.up("Control")
            bb2 = pg.evaluate(f"() => __h.blk('{n3['id']}')"); cp = pg.evaluate("() => __h.last()")
            chk(pg.evaluate("() => S.doc.blocks.length") == nb3 + 1 and bb2["y"] == bb["y"] and abs(cp["y"] - bb["y"] - 4 * P) <= P / 2 + 0.05, f"Ctrl+끌기 — 원본은 제자리 · 복사본이 네 행 아래 (수 {nb3}→{pg.evaluate('() => S.doc.blocks.length')} · 원본 y {bb['y']}→{bb2['y']} · 복사 {cp['kind']} y {cp['y']})")
            pg.keyboard.press("Delete"); chk(pg.evaluate("() => S.doc.blocks.length") == nb3, "복사본 지우기")
            # 끌어 묶기에 선도 · 복사 → 오른쪽 누름 '여기에 붙이기'
            gb, nbx = pg.evaluate(f"() => fullBox(__h.blk('{g3['id']}'))"), pg.evaluate(f"() => fullBox(__h.blk('{n3['id']}'))")
            drag(min(gb[0], nbx[0]) - 4, min(gb[1], nbx[1]) - 3, max(gb[2], nbx[2]) + 3, max(gb[3], nbx[3]) + 3)
            sw = pg.evaluate("() => [S.sel.size, S.selW.size]")
            chk(sw[0] == 2 and sw[1] >= 1, f"끌어 묶으면 블록 둘과 그 사이 선도 골라진다 (블록 {sw[0]} · 선 {sw[1]})")
            pg.keyboard.press("Control+c")
            nb0, nw0 = pg.evaluate("() => [S.doc.blocks.length, S.doc.wires.length]")
            c = at(LX0 + 150, ry(20)); pg.mouse.click(c[0], c[1], button="right")
            pg.wait_for_selector("#ctxmenu:not([hidden])", timeout=5000)
            items = pg.evaluate("() => [...document.querySelectorAll('#ctxmenu button')].map(b => b.textContent)")
            pg.screenshot(path=f"{out}/08_context_menu.png")
            pg.click("#ctxmenu button:has-text('여기에 붙이기')")
            nb1, nw1 = pg.evaluate("() => [S.doc.blocks.length, S.doc.wires.length]")
            top = pg.evaluate("() => Math.min(...[...S.sel].map(id => bboxOf(S.doc.blocks.find(b => b.id === id))[1]))")
            chk(nb1 == nb0 + 2 and nw1 >= nw0 + 1 and abs(top - ry(20)) < 2 * P, f"오른쪽 누름 메뉴({len(items)}개) '여기에 붙이기' — 누른 자리(20행 근처)에 블록 2 · 선 {nw1 - nw0}")
            pg.keyboard.press("Control+z"); chk(pg.evaluate("() => S.doc.blocks.length") == nb0, "Ctrl+Z")
            c = at(LX0 + 150, ry(30)); pg.mouse.click(c[0], c[1], button="right"); pg.wait_for_selector("#ctxmenu:not([hidden])")
            pg.click("#ctxmenu button:has-text('모두 고르기')")
            chk(pg.evaluate("() => S.sel.size === S.doc.blocks.length && S.selW.size === S.doc.wires.length"), "메뉴 '모두 고르기' — 블록 · 선 전부")
            pg.keyboard.press("Escape")
            lap("Ctrl+끌기 · 끌어 묶기 · 메뉴")
            # 선 자동 경로 다시 — GT 를 두 행 내려 선이 꺾인 뒤
            pg.evaluate(f"() => {{ S.sel = new Set(['{g3['id']}']); S.selW = new Set(); S.selWire = null; render(); document.querySelector('#stage').focus(); }}")
            pg.keyboard.press("Shift+ArrowDown"); pg.keyboard.press("Shift+ArrowDown")
            wid = pg.evaluate(f"() => {{ const p = __h.ports('{g3['id']}').find(q => q[2] === 'in'); const w = S.doc.wires.find(w => {{ const z = w.pts[w.pts.length - 1]; return Math.abs(z[0] - p[0]) < .05 && Math.abs(z[1] - p[1]) < .05; }}); return w && w.id; }}")
            wpt = pg.evaluate(f"() => S.doc.wires.find(w => w.id === '{wid}').pts")
            mid = [(wpt[0][0] + wpt[1][0]) / 2, (wpt[0][1] + wpt[1][1]) / 2]
            c = at(*mid); pg.mouse.click(c[0], c[1], button="right"); pg.wait_for_selector("#ctxmenu:not([hidden])")
            pg.click("#ctxmenu button:has-text('자동 경로로 다시')")
            w2 = pg.evaluate(f"() => S.doc.wires.find(w => w.id === '{wid}').pts")
            orth = all(abs(w2[k][0] - w2[k + 1][0]) < 0.01 or abs(w2[k][1] - w2[k + 1][1]) < 0.01 for k in range(len(w2) - 1))
            chk(w2[0] == wpt[0] and w2[-1] == wpt[-1] and orth and pg.evaluate("() => looseEnds().length") == 0, f"메뉴 '자동 경로로 다시' — 두 끝 그대로 · 직각 · 매달림 0 ({len(wpt)}점 → {len(w2)}점)")
            pg.keyboard.press("Control+z"); pg.keyboard.press("Control+z"); pg.keyboard.press("Control+z")   # 다시 그리기 · 화살표 두 번
            lap("자동 경로")
            # 되읽기 · 시뮬레이션 (셋째 장)
            pg.keyboard.press("Control+s"); pg.wait_for_function("() => !S.dirty", timeout=15000)
            pg.click("#verify"); pg.wait_for_function("() => S.verify", timeout=120000)
            v3 = pg.evaluate("() => S.verify"); bl3 = v3.get("blocks") or []
            chk(v3.get("ok") is True, f"셋째 장 되읽기 — ok={v3.get('ok')} 블록 {sum(1 for b in bl3 if b.get('ok'))}/{len(bl3)} 매달림 {v3.get('dangling')}")
            pg.evaluate("() => { S.verify = null; document.querySelector('#verify-card').hidden = true; render(); }")
            pg.click("#simtoggle"); pg.wait_for_function("() => S.sim && S.sim.on && S.sim.res", timeout=30000)
            pg.click("#sim-reset"); time.sleep(0.5); force_row(1, 1); force_row(2, 1)
            wout = pg.evaluate(f"() => {{ const L = layout(); return S.doc.wires.find(w => w.pts.some(p => Math.abs(p[0] - L.LX1) < .05)).id; }}")
            kk = net_val(wout)[0]; fr = pg.evaluate(f"() => S.sim.frames.map(f => [f.t, f.values['{kk}']])")
            chk(fr and fr[0][1] == 0 and fr[-1][1] == 1, f"셋째 장 시뮬레이션 — 1 · 2행 1 → AND → GT 5초 → 오른쪽 1행 1 (틀 {fr})")
            pg.click("#simtoggle")
            lap("셋째 장 검증 · 시뮬레이션")
            # 임시 저장 — 고치고 저장하지 않은 채 다른 창(브라우저가 꺼졌다 다시 연 것과 같다)에서 열면 되살릴지 묻는다
            pg.evaluate(f"() => {{ S.sel = new Set(['{n3['id']}']); S.selW = new Set(); render(); document.querySelector('#stage').focus(); }}")
            y0 = pg.evaluate(f"() => __h.blk('{n3['id']}').y")
            pg.keyboard.press("Shift+ArrowDown"); time.sleep(1.6)
            chk(pg.evaluate(f"() => !!localStorage.getItem('logic.draw.draft.{d3}')"), "고치면 1초 뒤 이 브라우저에 임시 판")
            pg2 = pg.context.new_page()
            pg2.on("pageerror", lambda e: errs.append(str(e)))
            pg2.on("console", lambda m: cons.append(m.text) if m.type in ("error", "warning") else None)
            pg2.goto(f"{B}/logic/draw?user=t#d={d3}")
            pg2.wait_for_selector("#modal:not([hidden])", timeout=30000)
            mt = pg2.inner_text("#m-title"); pg2.screenshot(path=f"{out}/09_draft.png")
            pg2.click("#m-ok"); pg2.wait_for_function("() => S.dirty", timeout=10000)
            y2 = pg2.evaluate(f"() => S.doc.blocks.find(b => b.id === '{n3['id']}').y")
            chk("되살리기" in mt and abs(y2 - y0 - P) < 0.05, f"다시 열면 '{mt}' — 되살리면 옮긴 자리 그대로 (y {y0} → {y2})")
            pg2.keyboard.press("Control+s"); pg2.wait_for_function("() => !S.dirty", timeout=15000)
            chk(not pg2.evaluate(f"() => localStorage.getItem('logic.draw.draft.{d3}')"), "저장하면 임시 판은 지운다")
            pg.close(); pg = pg2; pg.evaluate(HELP)
            lap("임시 저장 되살리기")
            # 미니맵 · 팔레트 찾기 · 단축키 창
            pg.evaluate("() => { setZoom(3.2); render(); }"); time.sleep(0.4)
            chk(pg.evaluate("() => !!document.querySelector('#mini') && !document.querySelector('#mini').hidden"), "확대하면 미니맵이 나온다")
            st0 = pg.evaluate("() => [document.querySelector('#scroll').scrollLeft, document.querySelector('#scroll').scrollTop]")
            mc = pg.evaluate("() => { const r = document.querySelector('#mini canvas').getBoundingClientRect(); return [r.left + r.width * 0.8, r.top + r.height * 0.8]; }")
            pg.mouse.click(mc[0], mc[1]); time.sleep(0.2)
            st1 = pg.evaluate("() => [document.querySelector('#scroll').scrollLeft, document.querySelector('#scroll').scrollTop]")
            pg.screenshot(path=f"{out}/10_minimap.png")
            chk(st1[0] > st0[0] and st1[1] > st0[1], f"미니맵 오른쪽 아래를 누르면 그 자리로 ({st0} → {st1})")
            pg.evaluate("() => document.querySelector('#stage').focus()"); pg.keyboard.press("Control+Shift+O"); time.sleep(0.2)
            chk(pg.evaluate("() => document.querySelector('#mini').hidden"), "Ctrl+Shift+O 로 미니맵 끄기")
            pg.keyboard.press("Control+Shift+O"); pg.keyboard.press("Control+0"); time.sleep(0.3)
            chk(pg.evaluate("() => document.querySelector('#mini').hidden"), "Ctrl+0 맞춤 보기면 (다 보이니) 미니맵은 숨는다")
            pg.fill("#pal-q", "타이머"); n_vis = pg.evaluate("() => [...document.querySelectorAll('#palette button')].filter(b => !b.hidden).length")
            pg.fill("#pal-q", "and"); n_and = pg.evaluate("() => [...document.querySelectorAll('#palette button')].filter(b => !b.hidden).map(b => b.textContent.trim())")
            pg.fill("#pal-q", "")
            chk(0 < len(n_and) <= 4 and any("AND" in t for t in n_and), f"팔레트 찾기 'and' → {n_and} · '타이머' → {n_vis}개")
            pg.evaluate("() => document.querySelector('#stage').focus()"); pg.keyboard.press("?")
            pg.wait_for_selector("#modal:not([hidden])", timeout=5000)
            chk("단축키" in pg.inner_text("#m-title") and "Ctrl+F" in pg.inner_text("#m-body"), "? — 단축키 창")
            pg.screenshot(path=f"{out}/11_keys.png"); pg.click("#m-ok")
            lap("미니맵 · 팔레트 찾기 · 단축키")
            def wf(page, expr, ms):
                try: page.wait_for_function(expr, timeout=ms)
                except Exception:
                    print("   ✕ 기다림 실패:", expr[:90], "| 그림:", pg.evaluate("() => [S.doc.blocks.length, S.placing && S.placing.key, [...S.sel], document.querySelector('#status').textContent]"), "| 기호 창:", pal.evaluate("() => [document.querySelector('#conn-t').textContent, P.target]") if pal else None)
                    raise
            pal = None
            # ─── L88 — 기호 · 매크로 창 (새 창): 누르고 그림에서 놓을 자리 · 이어 놓기 · 두 번 = 가운데 · 매크로 ───
            pal = next((q for q in pg.context.pages if "/logic/draw/palette" in q.url), None)
            chk(pal is not None, f"그림을 열면 기호 · 매크로 창이 함께 열린다 ({'열림' if pal else '안 열림 — 단추로 연다'})")
            if pal is None:
                with pg.context.expect_page() as pi: pg.click("#pal-open")
                pal = pi.value
            pal.on("pageerror", lambda e: errs.append("기호 창: " + str(e)))
            pal.wait_for_load_state(); pal.wait_for_selector(".pl-tile[data-key='k:OR']", timeout=20000)
            wf(pal, "() => document.querySelector('#tgt').textContent.includes('FG_G-303')", 10000)
            chk(True, f"기호 창 — 대상 '{pal.inner_text('#tgt')}' · 기호 {pal.evaluate('() => document.querySelectorAll(\"#s-sym .pl-tile\").length')} · 글자 상자 {pal.evaluate('() => document.querySelectorAll(\"#s-pre .pl-tile\").length')} · 매크로 {pal.evaluate('() => document.querySelectorAll(\"#s-mac .pl-tile\").length')}")
            pal.screenshot(path=f"{out}/12_palette_window.png", full_page=False)
            pg.evaluate("() => { fitZoom(); setZoom(1.6); S.sel = new Set(); S.selW = new Set(); render(); }")
            nb = pg.evaluate("() => S.doc.blocks.length")
            pal.click(".pl-tile[data-key='k:OR']")
            wf(pg, "() => S.placing && S.placing.key === 'k:OR'", 5000)
            tx, ty = LX0 + 120, ry(30)
            c = at(tx, ty); pg.mouse.move(c[0] - 20, c[1] - 10); pg.mouse.move(c[0], c[1]); time.sleep(0.1)
            gh = pg.evaluate("() => !!document.querySelector('#overlay rect.placeghost')")
            pg.mouse.click(c[0], c[1])
            orb = pg.evaluate("() => __h.last()")
            cx, cy = orb["x"] + orb["w"] / 2, orb["y"] + orb["h"] / 2
            chk(pg.evaluate("() => S.doc.blocks.length") == nb + 1 and orb["kind"] == "OR" and abs(cx - tx) < P and abs(cy - ty) < P and gh,
                f"기호 창에서 OR 누름 → 그림에 놓을 자리 미리보기 → 누른 자리에 OR ({cx:.1f},{cy:.1f} ≈ {tx:.1f},{ty:.1f})")
            wf(pal, "() => document.querySelector('#conn-t').textContent.includes('OR')", 5000)
            pal.click(".pl-tile[data-key='k:NOT']")
            wf(pg, f"() => S.doc.blocks.length === {nb + 2}", 5000)
            nt = pg.evaluate("() => __h.last()"); wl = pg.evaluate("() => S.doc.wires[S.doc.wires.length - 1]")
            oo, ni = port(orb["id"], "out"), port(nt["id"], "in")
            chk(nt["kind"] == "NOT" and max(abs(wl["pts"][0][0] - oo[0]), abs(wl["pts"][0][1] - oo[1]), abs(wl["pts"][-1][0] - ni[0]), abs(wl["pts"][-1][1] - ni[1])) < 0.05,
                "OR 을 고른 채 기호 창에서 NOT 누름 → OR 출력 옆에 놓고 이어짐 (이어 놓기)")
            vc = pg.evaluate("() => viewCenter()")
            pal.dblclick(".pl-tile[data-key='k:PD']")
            wf(pg, f"() => S.doc.blocks.length === {nb + 3}", 5000)
            pdb = pg.evaluate("() => __h.last()")
            chk(pdb["kind"] == "PD" and abs(pdb["x"] + pdb["w"] / 2 - vc[0]) < P and abs(pdb["y"] + pdb["h"] / 2 - vc[1]) < 2 * P, f"기호 창에서 두 번 누름 → 그림 창 화면 가운데에 PD")
            pg.evaluate("() => { S.sel = new Set(); render(); }"); wf(pal, "() => document.querySelector('#conn').classList.contains('off')", 5000)   # 고른 것이 없으면 이어 놓기는 꺼진다
            pal.click(".pl-tile[data-key='k:GT']"); wf(pg, "() => !!S.placing", 5000)
            pg.evaluate("() => document.querySelector('#stage').focus()"); pg.keyboard.press("Escape")
            chk(pg.evaluate("() => !S.placing") and pal.evaluate("() => document.querySelector('#placing').hidden"), "놓기 상태에서 Esc → 그만 (기호 창 표시도 꺼짐)")
            pal.fill("#q", "MOV"); time.sleep(0.2)
            mk = pal.evaluate("() => { const t = document.querySelector('#s-mac .pl-tile'); return t && t.dataset.key; }")
            chk(bool(mk), f"기호 창 찾기 'MOV' → 매크로 {mk}")
            pal.click(f".pl-tile[data-key='{mk}']"); wf(pg, "() => S.placing && S.placing.macro", 5000)
            c = at(LX0 + 300, ry(35)); pg.mouse.move(c[0], c[1]); pg.mouse.click(c[0], c[1])
            wf(pg, f"() => S.doc.blocks.length === {nb + 4}", 20000)
            mb = pg.evaluate("() => __h.last()")
            chk(mb["kind"] == "MACRO" and (mb.get("param") or {}).get("pins_in"), f"매크로를 기호 창에서 골라 그림에 놓음 — {mb['param'].get('title')} · 입력 {len(mb['param'].get('pins_in') or [])} · 출력 {len(mb['param'].get('pins_out') or [])}")
            pg.screenshot(path=f"{out}/13_placed_from_palette.png")
            pal.fill("#q", "")
            pg.keyboard.press("Control+s"); wf(pg, "() => !S.dirty", 15000)
            lap("기호 · 매크로 창")
            # ⑫ PDF · DXF
            for ext in ("pdf", "dxf"):
                t = time.time(); b = get(f"/logic/api/drawings/{did}/export.{ext}")
                chk(len(b) > 1000, f"{ext.upper()} 내보내기 {len(b):,} B · {time.time() - t:.2f}s")
            lap("내보내기")
            # ⑬ 첫 화면에 프로젝트 · 묶음이 보인다
            pg.click("#home-btn"); pg.wait_for_function("() => !document.querySelector('#home').hidden", timeout=10000)
            txt = pg.inner_text("#h-projects")
            chk("L86 PUMP" in txt and "FG_G-301" in txt or "급수펌프" in txt, "첫 화면에 프로젝트 · 묶음 · 그림이 보인다")
            pg.screenshot(path=f"{out}/05_home.png")
            chk(not errs, f"화면 오류 {len(errs)} {errs[:3]}")
            pg.screenshot(path=f"{out}/zz_end.png")
            chk(not cons, f"콘솔 오류 · 경고 {len(cons)} {cons[:3]}")
        except Exception as ex:
            print('!! 멈춤:', repr(ex)[:300]); bad.append('멈춤 ' + repr(ex)[:120])
            try:
                pg.screenshot(path=f'{out}/fail.png')
                print('   fail.png · 상태:', pg.evaluate("() => ({id: S.id, set: S.doc && S.doc.set, sheets: S.setInfo && S.setInfo.sheets.length, modal: document.querySelector('#modal').hidden, status: document.querySelector('#status').textContent, toast: document.querySelector('#toast').textContent})"))
            except Exception as e2: print('   (캡처 실패)', repr(e2)[:120])
        br.close()
finally:
    srv.terminate()
print("\n걸린 시간:", " · ".join(f"{n} {t}s" for n, t in steps))
print(f"\n통과 {len(ok)} · 실패 {len(bad)}")
json.dump({"ok": ok, "bad": bad, "steps": steps}, open(f"{out}/report.json", "w"), ensure_ascii=False, indent=1)
sys.exit(1 if bad else 0)
