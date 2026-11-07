"""hotfix94 — Shift 로 띠를 그어 고른 뒤 Shift + 왼쪽 클릭하면 판이 뜨고 결과가 묶음 전체 · 목록에 반영되는가.

    python3 spike/ui_audit_shift_group.py <data_dir 사본> <job> out/hotfix94/ui

★ 실 DB 를 열지 않는다 — 넘긴 데이터 폴더(사본)를 PID_DATA_DIR 로 가리킨다.
"""
from __future__ import annotations
import json, os, socket, subprocess, sys, time, urllib.request
from urllib.parse import quote
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data, JOB, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT), PID_PAGE_WARM="0", PID_ROWS_WARM="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = f"http://127.0.0.1:{port}"
FOUND, BAD = [], []
def note(x, ok=True):
    print(("  " if ok else "✗ ") + x, flush=True); FOUND.append(x)
    if not ok: BAD.append(x)
def srows():
    return {r["key"]: r for r in json.loads(urllib.request.urlopen(f"{base}/jobs/{JOB}/rows?tab=ALL").read())}
def scope_of(r):
    return (r.get("user") or {}).get("scope") or (r.get("values") or {}).get("scope") or ""

try:
    for _ in range(90):
        try: urllib.request.urlopen(base + "/version", timeout=2); break
        except Exception: time.sleep(1)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        pg = br.new_page(viewport={"width": 1920, "height": 1080}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
        pg.add_init_script("try{localStorage.removeItem('pid.split')}catch(e){}")
        pg.goto(base + "/?embed=1&mode=epc&user=" + quote("홍길동")); pg.wait_for_timeout(1500)
        pg.evaluate(f"open('{JOB}')")
        pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.pages && S.pages.length > 0", timeout=180000)
        pg.wait_for_timeout(2000)
        pg.evaluate("() => { if (S.side) toggleSide(); }"); pg.wait_for_timeout(500)
        # 행이 많은 장으로
        pno = pg.evaluate("""() => { const c = {}; for (const r of S.rows) if (!r.removed && !r.deleted) c[r.page_no] = (c[r.page_no]||0)+1;
                                     return +Object.entries(c).sort((a,b)=>b[1]-a[1])[0][0]; }""")
        pg.evaluate(f"() => showPage(S.pages.find(p => p.page_no === {pno}))"); pg.wait_for_timeout(2500)
        pg.wait_for_function(f"() => S.page && S.page.page_no === {pno} && !S.pending && document.querySelectorAll('rect.det').length > 0", timeout=60000)
        pg.evaluate("() => fit()"); pg.wait_for_timeout(800)
        print("page", pno, "boxes", pg.evaluate("() => document.querySelectorAll('rect.det').length"), flush=True)
        # 상자 넷 이상을 덮는 띠 — 화면 좌표로 계산
        boxes = pg.evaluate("""() => [...document.querySelectorAll('rect.det')].filter(r => S.rowByKey[r.dataset.key]
                     && !S.rowByKey[r.dataset.key].removed).map(r => { const b = r.getBoundingClientRect();
                     return {k: r.dataset.key, x: b.x, y: b.y, w: b.width, h: b.height}; })""")
        boxes.sort(key=lambda b: (b["y"], b["x"]))
        b0 = boxes[0]
        near = sorted(boxes, key=lambda b: abs(b["x"] - b0["x"]) + abs(b["y"] - b0["y"]))[:4]
        x0 = min(b["x"] for b in near) - 4; y0 = min(b["y"] for b in near) - 4
        x1 = max(b["x"] + b["w"] for b in near) + 4; y1 = max(b["y"] + b["h"] for b in near) + 4
        pg.keyboard.down("Shift")
        pg.mouse.move(x0, y0); pg.mouse.down(); pg.mouse.move((x0 + x1) / 2, (y0 + y1) / 2, steps=5)
        pg.mouse.move(x1, y1, steps=5); pg.mouse.up()
        pg.wait_for_timeout(600)
        multi = pg.evaluate("() => [...S.multi]")
        note(f"① Shift 띠 → 고른 {len(multi)}개", len(multi) >= 2)
        # ② Shift 를 누른 채 묶음 안 상자를 왼쪽 클릭
        k = multi[0]
        bb = pg.query_selector(f'rect.det[data-key="{k}"]').bounding_box()
        pg.mouse.click(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2)
        pg.wait_for_timeout(700)
        pop = pg.query_selector(".scopepop")
        txt = pg.inner_text(".scopepop") if pop else ""
        still = pg.evaluate("() => S.multi.size")
        note(f"② Shift + 클릭 → 판 {pop is not None} · '{txt.splitlines()[0] if txt else ''}' · 묶음 유지 {still}",
             pop is not None and still == len(multi) and f"선택 {len(multi)}개" in txt)
        pb = pop.bounding_box() if pop else bb
        cx = max(0, min(x0, pb["x"]) - 60); cy = max(0, min(y0, pb["y"]) - 60)
        pg.screenshot(path=str(OUT / "1_판.png"), clip={"x": cx, "y": cy, "width": 900, "height": 420})
        # ③ VENDOR (이름 하나) — 묶음 전부 · 목록 칸까지
        names = pg.evaluate("() => [...document.querySelectorAll('.scopepop .sp-name option')].map(o => o.value)")
        want = "VENDOR"
        if len(names) > 1:
            pg.select_option(".scopepop .sp-name", names[1]); want = f"VENDOR({names[1]})"
        pg.click('.scopepop .sp-b[data-sp="vendor"]')
        pg.keyboard.up("Shift")
        pg.wait_for_timeout(2500)
        rows = srows()
        got = [scope_of(rows[k]) for k in multi]
        grid = []
        for kk in multi:
            pg.evaluate("(k) => revealRow(k)", kk); pg.wait_for_timeout(250)
            grid.append(pg.evaluate("""(k) => { const td = document.querySelector(`#body tr[data-key="${CSS.escape(k)}"] td[data-col=scope]`);
                                return td ? td.innerText.replace('✎','').trim() : null; }""", kk))
        note(f"③ VENDOR → 서버 {got} · 목록 칸 {grid}",
             all(g == want for g in got) and all((g or "").startswith(want) for g in grid))
        who = {(rows[k].get("edited_by") or {}).get("scope", {}).get("author") for k in multi}
        note(f"   고친 사람 {who}", who == {"홍길동"})
        pg.screenshot(path=str(OUT / "2_VENDOR뒤.png"), clip={"x": cx, "y": cy, "width": 900, "height": 420})
        # ④ 다시 Shift + 클릭 → SCT 공급
        pg.keyboard.down("Shift")
        bb = pg.query_selector(f'rect.det[data-key="{multi[-1]}"]').bounding_box()
        pg.mouse.click(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2); pg.wait_for_timeout(600)
        pg.click('.scopepop .sp-b[data-sp="sct"]'); pg.keyboard.up("Shift"); pg.wait_for_timeout(2500)
        rows = srows()
        note(f"④ SCT → 서버 {[scope_of(rows[k]) for k in multi]}", all(scope_of(rows[k]) == "SCT" for k in multi))
        # ⑤ Ctrl + 클릭으로 하나 빼기
        drop = multi[1]
        bb = pg.query_selector(f'rect.det[data-key="{drop}"]').bounding_box()
        pg.keyboard.down("Control"); pg.mouse.click(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2)
        pg.keyboard.up("Control"); pg.wait_for_timeout(500)
        now = pg.evaluate("() => [...S.multi]")
        note(f"⑤ Ctrl + 클릭 → 묶음 {len(multi)} → {len(now)} (뺀 것 없음 {drop not in now})",
             drop not in now and len(now) == len(multi) - 1 or (len(multi) == 2 and len(now) == 0))
        keep = now if now else multi
        # ⑥ 둘 다 아님 — 남은 묶음 전부 지움
        if now:
            pg.keyboard.down("Shift")
            bb = pg.query_selector(f'rect.det[data-key="{now[0]}"]').bounding_box()
            pg.mouse.click(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2); pg.wait_for_timeout(600)
            pg.click('.scopepop .sp-b[data-sp="none"]'); pg.keyboard.up("Shift"); pg.wait_for_timeout(3000)
            rows = srows()
            rm = [rows[k].get("removed") for k in now]
            trs = []
            for kk in now:
                pg.evaluate("(k) => revealRow(k)", kk); pg.wait_for_timeout(250)
                trs.append(pg.evaluate("""(k) => (document.querySelector(`#body tr[data-key="${CSS.escape(k)}"]`)||{}).className||''""", kk))
            note(f"⑥ 둘 다 아님 → 서버 removed {rm} · 뺀 것 {rows[drop].get('removed')} · 목록 class {trs}",
                 all(rm) and not rows[drop].get("removed"))
            pg.screenshot(path=str(OUT / "3_지운뒤.png"), clip={"x": cx, "y": cy, "width": 900, "height": 420})
            # ⑦ 되돌리기 (Ctrl+Z)
            pg.click("#gridwrap", position={"x": 5, "y": 5}) if False else None
            pg.evaluate("() => undoStep(true)"); pg.wait_for_timeout(3000)
            rows = srows()
            note(f"⑦ 되돌리기 → removed {[rows[k].get('removed') for k in now]}", not any(rows[k].get("removed") for k in now))
        # ⑧ Shift + 묶음 밖 상자 = 더하기 (판 없음)
        outside = next(b["k"] for b in boxes if b["k"] not in pg.evaluate("() => [...S.multi]"))
        pg.evaluate("() => clearMulti()")
        bb = pg.query_selector(f'rect.det[data-key="{multi[0]}"]').bounding_box()
        pg.mouse.click(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2); pg.wait_for_timeout(500)
        pg.evaluate("() => closeScopePop()")
        pg.keyboard.down("Shift")
        bb = pg.query_selector(f'rect.det[data-key="{outside}"]').bounding_box()
        pg.mouse.click(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2); pg.keyboard.up("Shift"); pg.wait_for_timeout(500)
        note(f"⑧ Shift + 묶음 밖 상자 → 더하기 {pg.evaluate('() => S.multi.size')}개 · 판 {pg.query_selector('.scopepop') is not None}",
             pg.evaluate("() => S.multi.size") == 2 and pg.query_selector(".scopepop") is None)
        note(f"페이지 오류 {len(errs)} {errs[:3]}", not errs)
        br.close()
finally:
    srv.terminate()
    (OUT / "result.txt").write_text("\n".join(FOUND) + f"\n\n실패 {len(BAD)}\n", encoding="utf-8")
    print("실패", len(BAD))
