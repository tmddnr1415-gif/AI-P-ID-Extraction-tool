"""L64c — 계기 리스트: Excel 올리기 → TAG NO. 칸 자동완성 · 설명 자동 → 다시 올리면 바뀐 설명 반영 · '변경' 표시 · 없어진 TAG 경고 (크롬 · 사본 데이터).

  python3 spike/ui_audit_l64c.py <알다프라 그림 묶음이 든 데이터 폴더(사본)> <출력 폴더>
"""
from __future__ import annotations

import io, json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
data = Path(sys.argv[1]).resolve(); OUT = Path(sys.argv[2]).resolve(); OUT.mkdir(parents=True, exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT), PID_PAGE_WARM="0", PID_LOGIC_WARM="0", PID_ROWS_WARM="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=open(OUT / "srv.log", "w"), stderr=subprocess.STDOUT)
base = f"http://127.0.0.1:{port}"; LOG = []
def note(x): print(x, flush=True); LOG.append(x)


def xlsx(path, rows):
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "INST LIST"
    ws.append(["AL DHAFRA — INSTRUMENT LIST"]); ws.append([]); ws.append(["NO.", "KKS NO.", "TYPE", "DESCRIPTION"])
    for i, (t, ty, d) in enumerate(rows, 1):
        ws.append([i, t, ty, d])
    wb.save(path)


try:
    for _ in range(120):
        try: urllib.request.urlopen(base + "/version", timeout=2).read(); break
        except Exception: time.sleep(0.5)
    st = json.loads(urllib.request.urlopen(base + "/logic/api/drawings/sets").read())["items"][0]
    sheets = {q["sheet_no"]: q["id"] for q in st["sheets"]}
    doc = json.loads(urllib.request.urlopen(f"{base}/logic/api/drawings/{sheets['FG_G-207']}").read())
    rows = [(r["kks"], "", r["desc"]) for side in ("left", "right") for n, r in sorted(doc[side].items(), key=lambda x: int(x[0])) if r.get("kks")]
    extra = [("10EKG10CP101", "PT", "FG SUPPLY HEADER PRESSURE"), ("10EKG10CT101", "TT", "FG SUPPLY HEADER TEMPERATURE"),
             ("10EKG10CF101", "FT", "FG SUPPLY FLOW")]
    v1 = OUT / "inst_v1.xlsx"; xlsx(v1, rows + extra)
    ch_tag, ch_old = rows[0][0], rows[0][2]
    v2rows = [(rows[0][0], "", rows[0][2] + " (REV)")] + rows[2:] + extra              # 첫 TAG 설명 바뀜 · 둘째 TAG 빠짐
    v2 = OUT / "inst_v2.xlsx"; xlsx(v2, v2rows)
    note(f"FG_G-207 의 TAG {len(rows)}개 + 새 TAG 3개로 리스트를 만듦")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        pg = br.new_page(viewport={"width": 1600, "height": 950}); errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.add_init_script("try { localStorage.setItem('pid.author', '홍길동'); } catch (e) {}")
        pg.goto(f"{base}/logic/draw#d={sheets['FG_G-207']}")
        pg.wait_for_function("typeof S !== 'undefined' && S.doc && S.setInfo", timeout=30000); time.sleep(0.6)
        pg.fill("#who", "홍길동")
        note("올리기 전: " + pg.inner_text("#inst-say").replace("\n", " / "))
        t0 = time.time(); pg.set_input_files("#inst-file", str(v1))
        pg.wait_for_function("() => S.inst && S.inst.n > 0", timeout=30000); time.sleep(0.4)
        note(f"Excel 올림 ({time.time() - t0:.2f}초) → " + pg.inner_text("#inst-say").replace("\n", " / "))
        pg.locator("#inst-card").screenshot(path=str(OUT / "1_card.png"))
        # 빈 행의 TAG NO. 칸에 글자를 치면 자동완성
        n = pg.evaluate("() => { for (let k = 1; k <= S.doc.N; k++) if (!S.doc.left[String(k)]) return k; }")
        cell = pg.locator(f".cell[data-side='left'][data-n='{n}'][data-f='kks']")
        pg.evaluate("setZoom(2.4)"); time.sleep(0.2); cell.scroll_into_view_if_needed(); cell.dblclick(); time.sleep(0.2)
        pg.keyboard.type("10EKG10C"); time.sleep(0.3)
        ac = pg.inner_text("#cellac"); note(f"{n}행 TAG NO. 에 '10EKG10C' → 자동완성: {ac.replace(chr(10), ' / ')}")
        pg.screenshot(path=str(OUT / "2_autocomplete.png"))
        pg.keyboard.press("ArrowDown"); pg.keyboard.press("Enter"); time.sleep(0.3)
        row = pg.evaluate(f"() => S.doc.left['{n}']")
        note(f"둘째 항목 고름 → {n}행 {row}")
        pg.screenshot(path=str(OUT / "3_desc_filled.png"))
        pg.click("#save"); pg.wait_for_function("() => !S.dirty", timeout=20000)
        # 다시 올리기 — 설명 바뀜 · TAG 빠짐
        t0 = time.time(); pg.set_input_files("#inst-file", str(v2))
        try:
            pg.wait_for_function("() => S.inst && S.inst.version === 2", timeout=30000); time.sleep(0.6)
        except Exception:
            note("기다림 실패: " + pg.evaluate("() => JSON.stringify({st: document.querySelector('#status').textContent, toast: (document.querySelector('.dw-toast')||{}).textContent, inst: S.inst && S.inst.version})") + str(errors)); raise
        note(f"다시 올림 ({time.time() - t0:.2f}초) → " + pg.inner_text("#inst-say").replace("\n", " / "))
        cs, cn = pg.evaluate(f"() => {{ for (const s of ['left', 'right']) for (const [k, r] of Object.entries(S.doc[s])) if (r.kks === '{ch_tag}') return [s, k]; }}")
        note(f"{ch_tag} 행 설명: {pg.evaluate(f'() => S.doc[{cs!r}][{cn!r}]')} · 붉은 칸 {pg.locator('#svg .cell.inst-miss').count()} · 변경 칸 {pg.locator('#svg .cell.inst-chg').count()}")
        pg.locator("#inst-card").screenshot(path=str(OUT / "4_card_v2.png"))
        pg.evaluate("setZoom(2.4)"); time.sleep(0.2)
        c2 = pg.locator(f".cell[data-side='{cs}'][data-n='{cn}'][data-f='desc']"); c2.scroll_into_view_if_needed(); time.sleep(0.2)
        bb = c2.bounding_box(); pg.screenshot(path=str(OUT / "5_marks.png"), clip={"x": max(0, bb["x"] - 260), "y": max(0, bb["y"] - 40), "width": 760, "height": 160})
        pg.locator("#inst-ack").click(); time.sleep(0.2)
        note(f"'표시 지우기' → 변경 칸 {pg.locator('#svg .cell.inst-chg').count()}")
        note(f"페이지 오류 {len(errors)} {errors[:3]}")
        br.close()
finally:
    srv.terminate(); (OUT / "result.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
