"""hotfix79 — 편의 기능을 띄워서 눌러 확인한다 (되돌리기 · 칸 범위 · 여러 줄 붙이기 · Delete · 단축키).

    python3 spike/ui_audit_convenience.py <data_dir 사본> <job> <out_dir>

★ 실 DB 를 열지 않는다 — 넘긴 데이터 폴더(사본)를 PID_DATA_DIR 로 가리킨다.
값은 화면이 아니라 **서버**에서 다시 읽어 맞댄다 (`/rows?keys=`).
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

def srv_rows(keys):
    rows = json.loads(urllib.request.urlopen(f"{base}/jobs/{JOB}/rows?keys={quote(','.join(keys))}", timeout=30).read())
    rows = rows if isinstance(rows, list) else rows.get("rows", [])
    return {r["key"]: r for r in rows}

def user(keys, col):
    got = srv_rows(keys)
    return [(got[k].get("user") or {}).get(col) for k in keys]

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
        pg.on("dialog", lambda d: d.accept())
        pg.goto(f"{base}/?embed=1&user={quote('홍길동')}"); pg.wait_for_timeout(1500)
        pg.evaluate(f"open('{JOB}')")
        pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.vlist && S.vlist.length > 5", timeout=180000)
        pg.wait_for_timeout(1500)
        if pg.evaluate("() => !!S.side"):
            pg.evaluate("() => toggleSide(false)"); pg.wait_for_timeout(500)
        keys = pg.evaluate("""() => { const ok = r => !r.deleted && !r.removed && !r.delCand && !(r.user && 'line_no' in r.user); const L = S.vlist;
            for (let i = 0; i + 3 < L.length; i++) if ([0,1,2,3].every(j => ok(L[i+j]))) return [0,1,2,3].map(j => L[i+j].key);
            return null; }""")
        k0, k1, k2, k3 = keys
        td = lambda k, c: f'#body tr[data-key="{k}"] td[data-col="{c}"]'
        busy = lambda: pg.wait_for_function("() => !UNDO.busy", timeout=20000)
        drawing = pg.evaluate("ks => ks.map(k => String((S.rowByKey[k].ai || {}).line_no ?? ''))", keys)

        note("① 칸 하나 고치고 Ctrl+Z · Ctrl+Y")
        check(pg.evaluate("() => document.querySelector('#undo-btn').disabled"), "처음에는 되돌릴 것이 없다 (단추 꺼짐)")
        pg.evaluate(f"() => revealRow('{k0}').scrollIntoView({{block:'center'}})")
        pg.dblclick(td(k0, "line_no")); pg.wait_for_timeout(200)
        pg.keyboard.press("Control+A"); pg.keyboard.type("UNDO1"); pg.keyboard.press("Enter"); pg.wait_for_timeout(1500)
        check(user([k0], "line_no") == ["UNDO1"], "저장됨 UNDO1")
        check(not pg.evaluate("() => document.querySelector('#undo-btn').disabled"), "되돌리기 단추가 켜짐 · " + pg.get_attribute("#undo-btn", "title"))
        pg.keyboard.press("Control+z"); busy(); pg.wait_for_timeout(800)
        check(user([k0], "line_no") == [None], f"Ctrl+Z → 사람 값 없음 (도면 값으로) {user([k0], 'line_no')}")
        check(pg.text_content(td(k0, "line_no")).strip() == drawing[0], f"목록 칸도 도면 값 '{drawing[0]}'")
        pg.keyboard.press("Control+y"); busy(); pg.wait_for_timeout(800)
        check(user([k0], "line_no") == ["UNDO1"], "Ctrl+Y → 다시 UNDO1")

        note("② Shift+↓ 범위 · 복사 · Ctrl+Enter 채우기 · 되돌리기")
        pg.click(td(k0, "line_no")); pg.wait_for_timeout(300)
        pg.keyboard.press("Shift+ArrowDown"); pg.keyboard.press("Shift+ArrowDown"); pg.wait_for_timeout(300)
        n = pg.evaluate("() => document.querySelectorAll('#body td[data-rng]').length")
        check(n == 3, f"범위 3칸 표시 ({n})")
        pg.screenshot(path=str(OUT / "1_범위.png"), clip={"x": 960, "y": 300, "width": 960, "height": 500})
        pg.keyboard.press("Control+c"); pg.wait_for_timeout(200)
        clip = pg.evaluate("() => navigator.clipboard.readText()")
        check(clip.split("\n") == ["UNDO1", drawing[1], drawing[2]], f"Ctrl+C → 한 줄에 한 값 {clip!r}")
        pg.keyboard.type("RNG7"); pg.wait_for_timeout(150)
        pg.keyboard.press("Control+Enter"); busy(); pg.wait_for_timeout(1500)
        check(user([k0, k1, k2], "line_no") == ["RNG7"] * 3, f"Ctrl+Enter → 세 칸 모두 RNG7 {user([k0, k1, k2], 'line_no')}")
        check(all(pg.text_content(td(k, "line_no")).strip() == "RNG7" for k in (k0, k1, k2)), "목록 세 칸도 RNG7")
        pg.keyboard.press("Control+z"); busy(); pg.wait_for_timeout(1200)
        check(user([k0, k1, k2], "line_no") == ["UNDO1", None, None], f"Ctrl+Z → 각자 앞 값으로 {user([k0, k1, k2], 'line_no')}")

        note("③ Delete — 범위를 도면 값으로")
        pg.click(td(k0, "line_no")); pg.keyboard.press("Shift+ArrowDown"); pg.keyboard.press("Shift+ArrowDown")
        pg.keyboard.press("Delete"); busy(); pg.wait_for_timeout(1200)
        check(user([k0, k1, k2], "line_no") == [None] * 3, f"Delete → 사람 값 없음 {user([k0, k1, k2], 'line_no')}")
        pg.keyboard.press("Control+z"); busy(); pg.wait_for_timeout(1000)
        check(user([k0], "line_no") == ["UNDO1"], "Ctrl+Z → 지운 값이 돌아온다")

        note("④ 여러 줄 붙이기 (엑셀 열)")
        pg.keyboard.press("Escape")
        pg.click(td(k1, "line_no")); pg.wait_for_timeout(300)
        pg.evaluate("() => navigator.clipboard.writeText('P1\\nP2\\nP3\\n')")
        pg.keyboard.press("Control+v"); busy(); pg.wait_for_timeout(1500)
        check(user([k1, k2, k3], "line_no") == ["P1", "P2", "P3"], f"아래로 한 줄씩 {user([k1, k2, k3], 'line_no')}")
        check(not pg.evaluate("() => !!CELL.editing"), "편집 칸이 열린 채 남지 않는다")
        pg.keyboard.press("Control+z"); busy(); pg.wait_for_timeout(1200)
        check(user([k1, k2, k3], "line_no") == [None] * 3, "Ctrl+Z → 세 칸 다 앞으로")

        note("⑤ 지우기 되돌리기")
        pg.evaluate(f"() => deleteRows(['{k3}'], {{ reason: 'UNDO 시험' }})"); pg.wait_for_timeout(1500)
        check(srv_rows([k3])[k3].get("removed"), "지움")
        pg.locator("#gridwrap").focus()
        pg.keyboard.press("Control+z"); busy(); pg.wait_for_timeout(1500)
        check(not srv_rows([k3])[k3].get("removed"), "Ctrl+Z → 되살아남")
        pg.keyboard.press("Control+y"); busy(); pg.wait_for_timeout(1500)
        check(srv_rows([k3])[k3].get("removed"), "Ctrl+Y → 다시 지움")
        pg.keyboard.press("Control+z"); busy(); pg.wait_for_timeout(1500)

        note("⑥ 검색 칸의 Ctrl+Z 는 글자 되돌리기 (목록 값이 안 바뀐다)")
        before = user([k0], "line_no")
        pg.click("#filter"); pg.keyboard.type("abc"); pg.keyboard.press("Control+z"); pg.wait_for_timeout(600)
        check(user([k0], "line_no") == before, "검색 칸에서는 값 되돌리기가 돌지 않는다")
        pg.fill("#filter", ""); pg.wait_for_timeout(400)

        note("⑦ 단축키 도움말")
        modal = lambda: pg.evaluate("() => !document.querySelector('#modal').classList.contains('hidden') && document.querySelector('#modal-title').textContent")
        pg.click("#kbd-btn"); pg.wait_for_timeout(400)
        check(modal() == "단축키", f"⌨ 단추 → 단축키 창 ({modal()})")
        pg.screenshot(path=str(OUT / "2_단축키.png"))
        pg.evaluate("() => document.querySelector('#modal').classList.add('hidden')")
        # 칸이 골라져 있으면 ? 는 그 칸에 치는 글자다 (엑셀) — 도면에서 누르면 도움말
        pg.locator("#stage").focus(); pg.keyboard.press("?"); pg.wait_for_timeout(400)
        check(modal() == "단축키" and not pg.evaluate("() => !!CELL.editing"), "도면에서 ? → 단축키 창 (칸 편집은 안 열림)")
        check(not errs, f"페이지 오류 {len(errs)} {errs[:3]}")
        br.close()
finally:
    srv.terminate()
    try: srv.wait(10)
    except Exception: srv.kill()
(OUT / "audit.txt").write_text("\n".join(FOUND) + f"\n\n결함 {len(BAD)}\n", encoding="utf-8")
print("BAD", len(BAD))
sys.exit(1 if BAD else 0)
