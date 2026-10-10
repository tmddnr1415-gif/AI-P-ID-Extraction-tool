"""hotfix78 — 목록 칸을 엑셀처럼 고치는지 띄워서 눌러 확인한다.

    python3 spike/ui_audit_excel_cell.py <data_dir 사본> <job> out/hotfix78/ui

★ 실 DB 를 열지 않는다 — 넘긴 데이터 폴더(사본)를 PID_DATA_DIR 로 가리킨다.

  ① 한 번 누름 → 칸이 골라질 뿐 편집이 아니다 (글자를 쳐도 바로 들어가지 않고 '입력' 으로 시작)
  ② 두 번 누름 → 편집 (커서) · Enter → 저장되고 아래 칸으로 · 서버 값 · ✎
  ③ F2 → 끝에 커서 · Esc → 되돌리고 그 칸에 남는다 (서버 값 그대로)
  ④ 골라진 칸에서 글자를 바로 치면 → 칸을 비우고 그 글자부터 · Tab → 저장하고 오른쪽 칸
  ⑤ 화살표로 칸 이동 (편집 아님) · 행도 같이 골라진다
  ⑥ Ctrl+C / Ctrl+V — 한 칸 복사 · 붙이기 저장
"""
from __future__ import annotations
import json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
data, JOB, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT), PID_PAGE_WARM="0", PID_RENDER_POOL="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = f"http://127.0.0.1:{port}"
FOUND, BAD = [], []
def note(x): print(x, flush=True); FOUND.append(x)
def check(ok, what):
    note(("  ✔ " if ok else "  ✘ ") + what)
    if not ok: BAD.append(what)

def server_val(key, col):
    rows = json.loads(urllib.request.urlopen(f"{base}/jobs/{JOB}/rows?keys={quote(key)}", timeout=30).read())
    rows = rows if isinstance(rows, list) else rows.get("rows", [])
    r = rows[0]
    return (r.get("user") or {}).get(col), r["values"].get(col)

try:
    for _ in range(90):
        try: urllib.request.urlopen(base + "/version", timeout=2); break
        except Exception: time.sleep(1)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        ctx = br.new_context(viewport={"width": 1920, "height": 1080})
        ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=base)
        ctx.add_init_script("try{localStorage.setItem('pid.side.off','1');localStorage.removeItem('pid.split')}catch(e){}")
        pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
        pg.goto(f"{base}/?embed=1&user={quote('홍길동')}"); pg.wait_for_timeout(1500)
        pg.evaluate(f"open('{JOB}')")
        pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.vlist && S.vlist.length > 3", timeout=180000)
        pg.wait_for_timeout(1500)
        if pg.evaluate("() => !!S.side"):
            pg.evaluate("() => toggleSide(false)"); pg.wait_for_timeout(500)
        # 이어진 살아 있는 행 셋 — 지운 행(사본에 남은 앞 측정의 것)은 편집이 열리지 않는 것이 맞다
        keys = pg.evaluate("""() => { const ok = r => !r.deleted && !r.removed; const L = S.vlist;
            for (let i = 0; i + 2 < L.length; i++) if (ok(L[i]) && ok(L[i+1]) && ok(L[i+2])) return [L[i].key, L[i+1].key, L[i+2].key];
            return null; }""")
        k0, k1, k2 = keys[0], keys[1], keys[2]
        td = lambda k, c: f'#body tr[data-key="{k}"] td[data-col="{c}"]'
        cur = lambda: pg.evaluate("() => S.cell ? [S.cell.key, S.cell.col] : null")
        editing = lambda: pg.evaluate("() => !!CELL.editing")

        note("① 한 번 누름")
        pg.click(td(k0, "line_no")); pg.wait_for_timeout(300)
        check(cur() == [k0, "line_no"] and not editing(), f"칸이 골라짐 {cur()} · 편집 아님")
        check(pg.evaluate(f"() => getComputedStyle(document.querySelector('{td(k0, 'line_no')}')).boxShadow.includes('33, 115, 70')"),
              "골라진 칸 녹색 테두리")
        check(pg.evaluate("() => document.activeElement && document.activeElement.id === 'gridwrap'"), "자판은 목록 틀이 받는다")
        check(pg.get_attribute(td(k0, "line_no"), "contenteditable") is None, "편집 상태가 아니다 (contenteditable 없음)")
        pg.screenshot(path=str(OUT / "1_칸_고름.png"), clip={"x": 960, "y": 560, "width": 960, "height": 380})

        note("② 두 번 누름 → 편집 → Enter")
        pg.dblclick(td(k0, "line_no")); pg.wait_for_timeout(300)
        check(editing() and pg.evaluate("() => document.activeElement === CELL.editing"), "두 번 누르면 편집 (커서)")
        pg.screenshot(path=str(OUT / "2_두번_누름_편집.png"), clip={"x": 960, "y": 560, "width": 960, "height": 380})
        pg.keyboard.press("Control+A"); pg.keyboard.type("XL78A")
        pg.keyboard.press("Enter"); pg.wait_for_timeout(1500)
        uv, v = server_val(k0, "line_no")
        check(uv == "XL78A", f"서버 저장 {uv}")
        check(cur() == [k1, "line_no"] and not editing(), f"Enter → 아래 칸으로 {cur()}")
        check("edited" in (pg.get_attribute(td(k0, "line_no"), "class") or "")
              and pg.text_content(td(k0, "line_no")).strip() == "XL78A", "목록 칸 새 값 · ✎")

        note("③ F2 → Esc 되돌리기")
        before = pg.text_content(td(k1, "line_no"))
        pg.keyboard.press("F2"); pg.wait_for_timeout(200)
        check(editing(), "F2 → 편집")
        pg.keyboard.type("ZZZ"); pg.keyboard.press("Escape"); pg.wait_for_timeout(800)
        check(not editing() and pg.text_content(td(k1, "line_no")) == before and cur() == [k1, "line_no"],
              f"Esc → 원래 글자 '{before}' · 그 칸에 남음")
        check(server_val(k1, "line_no")[0] is None, "서버에 저장 안 됨")

        note("④ 바로 타자 → Tab")
        pg.keyboard.type("777"); pg.wait_for_timeout(200)
        check(editing() and pg.text_content(td(k1, "line_no")) == "777", "글자를 바로 치면 비우고 그 글자부터")
        pg.keyboard.press("Tab"); pg.wait_for_timeout(1500)
        check(server_val(k1, "line_no")[0] == "777", "Tab → 저장")
        nxt = pg.evaluate("() => { const c = gridCols().map(c => c[0]); return c[c.indexOf('line_no') + 1]; }")
        check(cur() == [k1, nxt], f"Tab → 오른쪽 칸 {cur()}")

        note("⑤ 화살표 이동")
        pg.keyboard.press("ArrowDown"); pg.wait_for_timeout(500)
        check(cur() == [k2, nxt] and pg.evaluate(f"() => S.sel === '{k2}'"), f"↓ → 아래 칸 · 행도 골라짐 {cur()}")
        pg.keyboard.press("ArrowLeft"); pg.wait_for_timeout(300)
        check(cur() == [k2, "line_no"] and not editing(), f"← → 왼쪽 칸 (편집 아님) {cur()}")

        note("⑥ 복사 · 붙이기")
        pg.keyboard.press("ArrowUp"); pg.keyboard.press("ArrowUp"); pg.wait_for_timeout(300)   # k0 line_no = XL78A
        pg.keyboard.press("Control+C"); pg.wait_for_timeout(200)
        clip = pg.evaluate("() => navigator.clipboard.readText()")
        check(clip == "XL78A", f"Ctrl+C → '{clip}'")
        pg.keyboard.press("ArrowDown"); pg.keyboard.press("ArrowDown"); pg.wait_for_timeout(300)
        pg.keyboard.press("Control+V"); pg.wait_for_timeout(1500)
        check(server_val(k2, "line_no")[0] == "XL78A", "Ctrl+V → 그 칸에 저장")
        check(cur() == [k2, "line_no"] and not editing() and pg.text_content(td(k2, "line_no")).strip() == "XL78A",
              "붙인 뒤 그 칸에 남고 새 값이 보인다")
        # 지운 행의 칸은 골라지기만 하고 편집이 열리지 않는다
        dk = pg.evaluate("() => (S.vlist.find(r => r.deleted || r.removed) || {}).key || null")
        if dk:
            pg.evaluate(f"() => revealRow('{dk}')"); pg.wait_for_timeout(300)
            pg.dblclick(td(dk, "line_no")); pg.wait_for_timeout(300)
            check(not editing(), "지운 행의 칸은 두 번 눌러도 편집이 열리지 않는다")
        # 고칠 수 없는 칸은 두 번 눌러도 편집이 안 열린다
        pg.dblclick(td(k2, "page_no")); pg.wait_for_timeout(300)
        check(not editing() and cur() == [k2, "page_no"], "고칠 수 없는 칸(장)은 골라지기만")
        pg.screenshot(path=str(OUT / "3_완료.png"), clip={"x": 960, "y": 560, "width": 960, "height": 380})
        check(not errs, f"페이지 오류 {len(errs)} {errs[:3]}")
        br.close()
finally:
    srv.terminate()
    try: srv.wait(10)
    except Exception: srv.kill()
(OUT / "audit.txt").write_text("\n".join(FOUND) + f"\n\n결함 {len(BAD)}\n", encoding="utf-8")
print("BAD", len(BAD))
sys.exit(1 if BAD else 0)
