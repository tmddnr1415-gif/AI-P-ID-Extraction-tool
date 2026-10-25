"""L66 — 로직을 그리는 엔지니어처럼 처음부터 한 장을 그려 본다 (크롬 · 빈 데이터 폴더).

  python3 spike/ui_engineer_l66.py <빈 데이터 폴더> <출력 폴더>

그리는 것: 급수펌프 A 기동/정지 — 허가 AND(4) · 기동 AND · 정지 OR · 메모리 · 기동 실패 감시(AND + GT 10초 + 경보).
과정마다 스크린샷과 한 줄 기록.  눈금자 가이드선 · Shift 맞춤 · 점과 점 자동 경로 · 건너뛰기 · 색 · 시뮬레이션 · PDF 되읽기까지.
"""
from __future__ import annotations

import json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = Path(sys.argv[1]).resolve(); OUT = Path(sys.argv[2]).resolve(); OUT.mkdir(parents=True, exist_ok=True)
data.mkdir(parents=True, exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT), PID_PAGE_WARM="0", PID_LOGIC_WARM="0", PID_ROWS_WARM="0", PID_TYPICAL_SEED="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = f"http://127.0.0.1:{port}"; LOG = []; STEP = [0]
def note(x): print(x, flush=True); LOG.append(x)


def shot(pg, name, clip=None):
    STEP[0] += 1
    p = OUT / f"{STEP[0]:02d}_{name}.png"
    pg.screenshot(path=str(p), clip=clip)
    return p


try:
    for _ in range(120):
        try: urllib.request.urlopen(base + "/version", timeout=2).read(); break
        except Exception: time.sleep(0.5)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        ctx = br.new_context(viewport={"width": 1600, "height": 1000}); errors = []
        ctx.add_init_script("try { localStorage.setItem('pid.author', '홍길동'); } catch (e) {}")
        pg = ctx.new_page(); pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append("console: " + m.text) if m.type == "error" else None)
        pg.goto(f"{base}/logic/draw"); pg.wait_for_function("typeof S !== 'undefined' && S.sym", timeout=30000)

        # 1. 새 그림 — 학습 양식
        pg.click("#new"); pg.fill("#m-name", "급수펌프 A 기동"); pg.fill("#m-sheet", "FW_G-101"); pg.fill("#m-dtitle", "FEED WATER PUMP A START/STOP")
        pg.fill("#m-pname", "AL DHAFRA IWP"); pg.fill("#m-docno", "1A5J-00GEN00-J09-0102"); pg.fill("#m-rev", "0")
        pg.click("#m-ok"); pg.wait_for_function("S.doc && S.doc.sheet_no === 'FW_G-101'", timeout=20000); time.sleep(0.5)
        note(f"1 새 그림: 양식 {pg.evaluate('S.doc.form')} · 제목 {pg.evaluate('S.doc.title')!r} · 행 {pg.evaluate('S.doc.N')}")
        shot(pg, "새그림")

        # 화면 좌표 도우미 (도면 pt → 창)
        pg.evaluate("""() => { window.sc = (x, y) => { const r = $('#svg').getBoundingClientRect(), L = layout(); return [r.left + x / L.W * r.width, r.top + y / L.H * r.height]; };
          window.blkC = id => { const b = S.doc.blocks.find(b => b.id === id); const bb = bboxOf(b); return [(bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2]; }; }""")
        pg.evaluate("fitZoom()"); time.sleep(0.2)
        L = pg.evaluate("layout()")
        ry = lambda n: L["TOP"] + ((n - 1) % L["N"]) * L["PITCH"] + L["PITCH"] / 2

        # 2. 표 — 입력 · 출력 행 적기 (두 번 눌러 칸 고치기)
        def cell(side, n, f, text):
            sel = f"#svg rect.cell[data-side='{side}'][data-n='{n}'][data-f='{f}']"
            pg.locator(sel).scroll_into_view_if_needed(); pg.locator(sel).dblclick(); pg.keyboard.type(text); pg.keyboard.press("Escape" if False else "Enter")
            pg.keyboard.press("Escape"); time.sleep(0.05)
        rows_in = {2: ("HMI", "10LAC10AA001", "PUMP A REMOTE SELECTED"), 3: ("", "10LAB10AA001", "SUCTION VALVE OPENED"), 4: ("", "10LAC10CP001", "LUBE OIL PRESS NORMAL"),
                   5: ("", "10LAC10EB001", "PUMP A NO TRIP"), 7: ("HMI", "", "PB START"), 8: ("HMI", "", "PB STOP"), 10: ("", "10LAC10EE001", "PUMP A RUNNING")}
        for n, (fm, kks, desc) in rows_in.items():
            if fm: cell("left", n, "fm", fm)
            if kks: cell("left", n, "kks", kks)
            cell("left", n, "desc", desc)
        N = L["N"]
        rows_out = {N + 2: ("PUMP A START CMD", "10LAC10AA001", "MCC"), N + 3: ("PUMP A STOP CMD", "10LAC10AA001", "MCC"), N + 5: ("PUMP A START PERMISSIVE", "", "HMI"), N + 7: ("PUMP A START FAIL", "", "HMI")}
        for n, (desc, kks, to) in rows_out.items():
            cell("right", n, "desc", desc)
            if kks: cell("right", n, "kks", kks)
            cell("right", n, "to", to)
        pg.evaluate("() => { fitZoom(); const sc = $('#scroll'); sc.scrollLeft = 0; sc.scrollTop = 0; }"); time.sleep(0.3)
        note(f"2 표: 입력 {len(rows_in)} · 출력 {len(rows_out)} 행")
        shot(pg, "표")

        # 3. 눈금자를 눌러 가이드선 — 세로 셋(게이트 열) · 가로 하나
        def ruler_click(axis, v):
            if axis == "v":
                r = pg.evaluate("(() => { const c = $('#ruler-x').getBoundingClientRect(); return [c.left, c.top, c.height]; })()")
                x = pg.evaluate(f"sc({v}, 0)[0]"); pg.mouse.click(x, r[1] + r[2] / 2)
            else:
                r = pg.evaluate("(() => { const c = $('#ruler-y').getBoundingClientRect(); return [c.left, c.width]; })()")
                y = pg.evaluate(f"sc(0, {v})[1]"); pg.mouse.click(r[0] + r[1] / 2, y)
            time.sleep(0.15)
        for x in (440, 520, 600, 690):
            ruler_click("v", x)
        ruler_click("h", ry(13))
        g = pg.evaluate("S.rg"); note(f"3 가이드선: 세로 {g['v']} · 가로 {g['h']}")
        shot(pg, "가이드선")

        # 4. 기호 놓기 — 팔레트를 누르고, Shift 를 누른 채 가이드선 근처로 끌어 붙인다
        def place(kind, x, y, text=None, preset=None):
            if preset:
                pg.evaluate(f"addPreset(S.presets.find(p => p.text === {json.dumps(preset)}), 0, 0)")
            else:
                pg.evaluate(f"addBlock({json.dumps(kind)}, {(L['LX0'] + L['LX1']) / 2}, {L['TOP'] + L['PITCH'] * 6})")
            bid = pg.evaluate("S.doc.blocks[S.doc.blocks.length - 1].id")
            c = pg.evaluate(f"blkC('{bid}')"); s0 = pg.evaluate(f"sc({c[0]}, {c[1]})"); s1 = pg.evaluate(f"sc({x + 1.3}, {y + 1.1})")   # 일부러 조금 비켜서 놓는다
            pg.mouse.move(*s0); pg.mouse.down(); pg.keyboard.down("Shift")
            for k in range(1, 9): pg.mouse.move(s0[0] + (s1[0] - s0[0]) * k / 8, s0[1] + (s1[1] - s0[1]) * k / 8); time.sleep(0.02)
            pg.mouse.up(); pg.keyboard.up("Shift"); time.sleep(0.1)
            return bid
        perm = place("AND", 440, (ry(3) + ry(4)) / 2)
        pg.evaluate(f"(() => {{ const b = S.doc.blocks.find(b => b.id === '{perm}'); S.sel = new Set([b.id]); render(); }})()")
        pg.fill("#p-nin", "4"); pg.press("#p-nin", "Enter"); time.sleep(0.2)      # 속성 판에서 입력 수 4
        start = place("AND", 520, ry(7))
        stop = place("OR", 520, ry(9))
        notrip = place("NOT", 440, ry(5) + L["PITCH"] * 3)
        mem = place("MEMORY", 600, (ry(7) + ry(8)) / 2)
        notrun = place("NOT", 520, ry(13))
        fail = place("AND", 600, ry(13))
        tmr = place("GT", 690, ry(13))
        pg.evaluate(f"(() => {{ const b = S.doc.blocks.find(b => b.id === '{tmr}'); b.param.t = 10; markDirty(); render(); }})()")
        ann = place("ANN", 760, ry(13))
        xs = pg.evaluate("S.doc.blocks.map(b => [b.kind, +bboxOf(b)[0].toFixed(2), +((bboxOf(b)[1] + bboxOf(b)[3]) / 2).toFixed(2)])")
        note("4 기호 (Shift 로 가이드선에 붙임): " + " · ".join(f"{k} x{x}" for k, x, _ in xs))
        shot(pg, "기호")

        # 5. 선 — 점과 점: 출발 단자를 누르고 도착 단자를 누르면 자동 경로가 선이 된다
        pg.keyboard.press("w"); time.sleep(0.1)
        def port_of(bid, idx):
            return pg.evaluate(f"ports(S.doc.blocks.find(b => b.id === '{bid}'))[{idx}]")
        def wire(a, b):
            n0 = pg.evaluate("S.doc.wires.length")
            pg.mouse.click(*pg.evaluate(f"sc({a[0]}, {a[1]})")); time.sleep(0.08)
            pg.mouse.move(*pg.evaluate(f"sc({b[0]}, {b[1]})")); time.sleep(0.15)
            pg.mouse.click(*pg.evaluate(f"sc({b[0]}, {b[1]})")); time.sleep(0.1)
            if pg.evaluate("!!S.wip"): pg.keyboard.press("Enter"); time.sleep(0.05)
            w = pg.evaluate("S.doc.wires[S.doc.wires.length - 1]")
            return w if pg.evaluate("S.doc.wires.length") > n0 else None
        LX0, LX1 = L["LX0"], L["LX1"]
        ins = lambda bid: [p for p in pg.evaluate(f"ports(S.doc.blocks.find(b => b.id === '{bid}'))") if p[2] == "in"]
        outs = lambda bid: [p for p in pg.evaluate(f"ports(S.doc.blocks.find(b => b.id === '{bid}'))") if p[2] == "out"]
        made = []
        pi = ins(perm)
        made += [wire((LX0, ry(2)), pi[0]), wire((LX0, ry(3)), pi[1]), wire((LX0, ry(4)), pi[2])]
        made += [wire((LX0, ry(5)), pi[3])]
        made += [wire(outs(perm)[0], ins(start)[0]), wire((LX0, ry(7)), ins(start)[1])]
        made += [wire((LX0, ry(8)), ins(stop)[0])]
        made += [wire((LX0, ry(5)), ins(notrip)[0])]                    # 같은 행에서 갈라짐 — 연결점
        made += [wire(outs(notrip)[0], ins(stop)[1])]
        made += [wire(outs(start)[0], ins(mem)[0]), wire(outs(stop)[0], ins(mem)[1])]
        mo = outs(mem)
        made += [wire(mo[0], (LX1, ry(N + 2))), wire(mo[1], (LX1, ry(N + 3)))]
        made += [wire(outs(perm)[0], (LX1, ry(N + 5)))]
        made += [wire((LX0, ry(10)), ins(notrun)[0])]                   # 아래로 내려가며 다른 선을 건너뛴다
        made += [wire(mo[0], ins(fail)[0]), wire(outs(notrun)[0], ins(fail)[1])]
        made += [wire(outs(fail)[0], ins(tmr)[0]), wire(outs(tmr)[0], ins(ann)[0]), wire(outs(tmr)[0], (LX1, ry(N + 7)))]
        ok = sum(1 for m in made if m)
        diag = pg.evaluate("S.doc.wires.reduce((n, w) => n + w.pts.slice(1).filter((q, i) => Math.abs(q[0] - w.pts[i][0]) > 0.01 && Math.abs(q[1] - w.pts[i][1]) > 0.01).length, 0)")
        hops = pg.evaluate("S.doc.wires.reduce((n, w) => n + hopsOf(w).reduce((m, h) => m + h[1].length, 0), 0)")
        note(f"5 선: 그은 것 {ok}/{len(made)} · 사선 토막 {diag} · 건너뛰기 {hops}")
        pg.keyboard.press("v"); shot(pg, "선")
        pg.evaluate("setZoom(3)"); time.sleep(0.2)
        c = pg.evaluate(f"sc(560, {ry(9)})"); pg.evaluate(f"(() => {{ const sc = $('#scroll'); sc.scrollLeft += {c[0]} - 800; sc.scrollTop += {c[1]} - 450; }})()"); time.sleep(0.3)
        shot(pg, "확대_색과건너뛰기")
        pg.evaluate("fitZoom()"); time.sleep(0.2)

        # 6. 저장 · 되읽기 검증
        pg.click("#save"); pg.wait_for_function("!S.dirty", timeout=20000)
        pg.click("#verify"); pg.wait_for_function("S.verify", timeout=60000); time.sleep(0.4)
        v = pg.evaluate("S.verify")
        note(f"6 되읽기: 블록 {sum(1 for b in v['blocks'] if b['ok'])}/{len(v['blocks'])} · 행 {v['rows']['read']}/{v['rows']['drawn']} · 매달린 끝 {v.get('dangling')} · 그물 {v.get('nets')}")
        shot(pg, "되읽기")

        # 7. 시뮬레이션 — 허가 넷 + 기동 누름 → 기동 지령 · 래치
        pg.click("#simtoggle"); pg.wait_for_function("() => S.sim && S.sim.res", timeout=30000); time.sleep(0.4)
        for n in (2, 3, 4, 5):
            pg.evaluate(f"setForce(S.id, 'row:{n}', 1)"); time.sleep(0.25)
        pg.evaluate("setForce(S.id, 'row:7', 1)"); time.sleep(1.2)
        outs_ = pg.evaluate(f"(() => {{ const v = S.sim.res.pages ? null : null; return Object.entries(S.sim.values || {{}}).filter(([k, x]) => x === 1).length; }})()")
        out_rows = pg.evaluate("(((S.sim.res.pages || []).find(p => p.did === S.id) || {}).outputs || []).map(o => o.row + ' ' + o.desc)")
        note(f"7 시뮬레이션: 1 인 선 {outs_} · 나간 출력 {out_rows}")
        shot(pg, "시뮬레이션_기동")
        for _ in range(3):
            pg.click("#sim-step"); time.sleep(0.8)
        outt = pg.evaluate("(((S.sim.res.pages || []).find(p => p.did === S.id) || {}).outputs || []).map(o => o.row + ' ' + o.desc)")
        note(f"   운전 신호가 안 들어온 채 시간을 흘림 → 나간 출력 {outt} (기동 실패 10초)")
        shot(pg, "시뮬레이션_기동실패")
        pg.evaluate("setForce(S.id, 'row:7', 0)"); time.sleep(1.0)
        out2 = pg.evaluate("(((S.sim.res.pages || []).find(p => p.did === S.id) || {}).outputs || []).map(o => o.row + ' ' + o.desc)")
        note(f"   기동 누름을 놓음 → 나간 출력 {out2} (래치 유지)")
        pg.evaluate("setForce(S.id, 'row:8', 1)"); time.sleep(1.0)
        out3 = pg.evaluate("(((S.sim.res.pages || []).find(p => p.did === S.id) || {}).outputs || []).map(o => o.row + ' ' + o.desc)")
        note(f"   정지 누름 → 나간 출력 {out3}")
        shot(pg, "시뮬레이션_정지")
        pg.click("#simtoggle"); time.sleep(0.3)

        # 8. PDF — 흑백 · 같은 양식
        pdf = urllib.request.urlopen(base + pg.evaluate("$('#pdf').getAttribute('href')")).read()
        (OUT / "drawing.pdf").write_bytes(pdf)
        import pymupdf
        page = pymupdf.open(stream=pdf, filetype="pdf")[0]
        cols = {tuple(round(c, 2) for c in (d.get("color") or (0, 0, 0))) for d in page.get_drawings()} | {tuple(round(c, 2) for c in (d.get("fill") or (0, 0, 0))) for d in page.get_drawings() if d.get("fill")}
        page.get_pixmap(dpi=110).save(str(OUT / f"{STEP[0] + 1:02d}_pdf.png")); STEP[0] += 1
        note(f"8 PDF: 색 {sorted(cols)} (흑백이어야 한다)")
        note(f"화면 오류 {len(errors)}: {errors[:4]}")
        ctx.close(); br.close()
finally:
    srv.terminate()
    (OUT / "result.txt").write_text("\n".join(LOG), encoding="utf-8")
