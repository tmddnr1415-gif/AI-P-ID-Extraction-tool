"""hotfix91 — 마크업: 사각형을 놓은 뒤 속성 입력 판이 뜨기까지.

    python3 spike/perf_markup_popup.py <data_dir 사본> <job> <out.json> [rounds=2] [--root <코드 폴더>]

★ 실 DB 를 열지 않는다 — 넘긴 데이터 폴더(사본)를 PID_DATA_DIR 로 가리킨다.  `--root` 로 전 판 worktree 를
같은 자로 잰다.  회마다 서버를 새로 띄운다(그 장을 처음 읽는 경우를 재려고).

한 회 = 행이 가장 많은 장에서:
  cold      마크업을 켜고 0.3초 뒤(미리 읽기가 아직 도는 중) 사각형을 긋고 → 판(`#mk-type`)이 설 때까지
  version   마크업을 켠 직후 `/version` 한 번 — 서버가 그동안 답하는가 (예전에는 이벤트 루프가 막혔다)
  filled    같은 판에서 제안값(출처 줄)이 채워질 때까지
  warm      미리 읽기가 끝난 뒤 다시 그어 → 판이 설 때까지
"""
from __future__ import annotations
import json, os, shutil, socket, statistics, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
from urllib.parse import quote

args = list(sys.argv[1:])
root_arg = None
if "--root" in args:
    i = args.index("--root"); root_arg = Path(args[i + 1]); del args[i:i + 2]
ROOT = root_arg or Path(__file__).resolve().parent.parent
src, JOB, OUT = Path(args[0]), args[1], Path(args[2])
ROUNDS = int(args[3]) if len(args) > 3 and args[3].isdigit() else 2
READY = "() => typeof S !== 'undefined' && S.job && !S.loading && S.rows && S.rows.length > 0 && document.querySelector('#body tr')"
SP = Path(tempfile.mkdtemp(prefix="perf_mk_")) / "data"
res = {"rounds": [], "job": JOB, "root": str(ROOT)}

FREE_SPOT = """() => {
  const img = document.querySelector('#sheet'); const b = img.getBoundingClientRect();
  const rects = [...document.querySelectorAll('#ov rect')].map(r => r.getBoundingClientRect());
  const far = (x, y) => rects.every(r => x < r.left - 70 || x > r.right + 70 || y < r.top - 70 || y > r.bottom + 70);
  for (let y = b.top + 80; y < b.bottom - 80; y += 25) for (let x = b.left + 80; x < b.right - 80; x += 25)
    if (far(x, y)) return [x, y];
  return [b.left + b.width / 2, b.top + b.height / 2];
}"""


def drag_and_time(pg):
    x, y = pg.evaluate(FREE_SPOT)
    pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x + 20, y + 15); pg.mouse.move(x + 48, y + 36)
    pg.evaluate("window.__t0 = performance.now()")
    pg.mouse.up()
    pg.wait_for_function("() => document.querySelector('#mk-type') && !document.querySelector('#modal').classList.contains('hidden')", timeout=60000)
    popup = pg.evaluate("performance.now() - window.__t0")
    pg.wait_for_function("() => { const s = document.querySelector('#mk-scope-src'); return !s || !document.querySelector('#modal .mk-form .mk-reading'); }", timeout=60000)
    filled = pg.evaluate("performance.now() - window.__t0")
    pg.keyboard.press("Escape")
    pg.wait_for_function("() => document.querySelector('#modal').classList.contains('hidden')")
    return round(popup), round(filled)


try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        for r in range(ROUNDS):
            shutil.rmtree(SP, ignore_errors=True)
            shutil.copytree(src, SP, ignore=shutil.ignore_patterns("page_cache", "backups"))
            s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
            env = dict(os.environ, PID_DATA_DIR=str(SP), PYTHONPATH=str(ROOT), PID_PAGE_WARM="0")
            srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                                    "--port", str(port)], cwd=str(ROOT), env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            base = f"http://127.0.0.1:{port}"
            try:
                for _ in range(90):
                    try: urllib.request.urlopen(base + "/version", timeout=2); break
                    except Exception: time.sleep(1)
                ctx = br.new_context(viewport={"width": 1920, "height": 1080})
                ctx.add_init_script("try{localStorage.removeItem('pid.split');localStorage.setItem('pid.side.off','1')}catch(e){}")
                pg = ctx.new_page(); errs = []
                pg.on("pageerror", lambda e: errs.append(str(e)))
                pg.on("dialog", lambda d: d.accept())
                pg.goto(f"{base}/?embed=1&user={quote('홍길동')}")
                pg.wait_for_function("() => typeof S !== 'undefined' && typeof open === 'function'", timeout=60000)
                pg.wait_for_timeout(1000)
                pg.evaluate(f"open('{JOB}')")
                pg.wait_for_function(READY, timeout=180000)
                pno = pg.evaluate("""() => { const c = {}; for (const r of S.rows) if (!r.removed && r.rect && r.rect.length === 4) c[r.page_no] = (c[r.page_no] || 0) + 1;
                    return +Object.entries(c).sort((a, b) => b[1] - a[1])[0][0]; }""")
                pg.evaluate(f"showPage(S.pages.find(p => p.page_no === {pno}))")
                pg.wait_for_function("() => !S.pending && document.querySelector('#sheet').complete && document.querySelectorAll('#ov rect').length > 5", timeout=120000)
                pg.wait_for_timeout(800)
                one = {"page": pno}
                # 마크업 켜기 → 미리 읽기 시작 → 0.3초 뒤 긋기
                pg.click("#markup-toggle")
                pg.evaluate("""window.__v = (async () => { const t = performance.now(); try { await fetch('/version', {cache: 'no-store'}); } catch (e) {} return performance.now() - t; })()""")
                pg.wait_for_timeout(300)
                one["cold_popup_ms"], one["cold_filled_ms"] = drag_and_time(pg)
                one["version_during_prewarm_ms"] = round(pg.evaluate("window.__v"))
                pg.wait_for_function("() => !(document.querySelector('#markup-note') || {textContent: ''}).textContent.startsWith('도면을 읽는 중')", timeout=120000)
                pg.wait_for_timeout(300)
                one["warm_popup_ms"], one["warm_filled_ms"] = drag_and_time(pg)
                one["propose_requests_ms"] = pg.evaluate("() => performance.getEntriesByType('resource').filter(r => r.name.includes('/markup/propose')).map(r => Math.round(r.duration))")
                one["errors"] = errs
                res["rounds"].append(one)
                print(json.dumps(one, ensure_ascii=False))
                ctx.close()
            finally:
                srv.terminate(); srv.wait(timeout=20)
    keys = ["cold_popup_ms", "cold_filled_ms", "version_during_prewarm_ms", "warm_popup_ms", "warm_filled_ms"]
    res["median"] = {k: statistics.median(r[k] for r in res["rounds"]) for k in keys}
    print("median", json.dumps(res["median"]))
finally:
    shutil.rmtree(SP.parent, ignore_errors=True)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
