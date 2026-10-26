"""hotfix91 — 마크업 판이 제안보다 먼저 뜨고, 사람이 적은 칸을 제안이 덮지 않는지 띄워서 누른다.

    python3 spike/ui_audit_markup_popup.py <data_dir 사본> <job> <out 폴더>
실 DB 를 열지 않는다 (사본 폴더를 PID_DATA_DIR 로).  적는 것: 판이 선 순간 제안 출처 줄이 '읽는 중' 이었는가 ·
읽는 중에 Type 에 적은 글자가 제안 뒤에도 남는가 · 손대지 않은 칸(Q'ty·SYSTEM)은 제안으로 찼는가 ·
행 추가 뒤 서버에 그 Type 이 적혔는가 · 페이지 오류.
"""
from __future__ import annotations
import json, os, shutil, socket, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
src, JOB, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
SP = Path(tempfile.mkdtemp(prefix="mkpop_")) / "data"
shutil.copytree(src, SP, ignore=shutil.ignore_patterns("page_cache", "backups"))
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(SP), PYTHONPATH=str(ROOT), PID_PAGE_WARM="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = f"http://127.0.0.1:{port}"
FREE_SPOT = """() => {
  const img = document.querySelector('#sheet'); const b = img.getBoundingClientRect();
  const rects = [...document.querySelectorAll('#ov rect')].map(r => r.getBoundingClientRect());
  const far = (x, y) => rects.every(r => x < r.left - 70 || x > r.right + 70 || y < r.top - 70 || y > r.bottom + 70);
  for (let y = b.top + 80; y < b.bottom - 80; y += 25) for (let x = b.left + 80; x < b.right - 80; x += 25)
    if (far(x, y)) return [x, y];
  return [b.left + b.width / 2, b.top + b.height / 2]; }"""
facts = {}
try:
    for _ in range(90):
        try: urllib.request.urlopen(base + "/version", timeout=2); break
        except Exception: time.sleep(1)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        ctx = br.new_context(viewport={"width": 1920, "height": 1080})
        ctx.add_init_script("try{localStorage.removeItem('pid.split');localStorage.setItem('pid.side.off','1')}catch(e){}")
        pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("dialog", lambda d: d.accept())
        pg.goto(f"{base}/?embed=1&user={quote('홍길동')}")
        pg.wait_for_function("() => typeof S !== 'undefined' && typeof open === 'function'", timeout=60000)
        pg.wait_for_timeout(1000)
        pg.evaluate(f"open('{JOB}')")
        pg.wait_for_function("() => S.job && !S.loading && S.rows && S.rows.length > 0 && document.querySelector('#body tr')", timeout=180000)
        pno = pg.evaluate("""() => { const c = {}; for (const r of S.rows) if (!r.removed && r.rect && r.rect.length === 4) c[r.page_no] = (c[r.page_no] || 0) + 1;
            return +Object.entries(c).sort((a, b) => b[1] - a[1])[0][0]; }""")
        pg.evaluate(f"showPage(S.pages.find(p => p.page_no === {pno}))")
        pg.wait_for_function("() => !S.pending && document.querySelector('#sheet').complete && document.querySelectorAll('#ov rect').length > 5", timeout=120000)
        pg.wait_for_timeout(800)
        pg.click("#markup-toggle"); pg.wait_for_timeout(250)          # 미리 읽기가 도는 중에 긋는다
        x, y = pg.evaluate(FREE_SPOT)
        pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x + 30, y + 20); pg.mouse.move(x + 48, y + 36)
        t0 = time.perf_counter(); pg.mouse.up()
        pg.wait_for_function("() => document.querySelector('#mk-type') && !document.querySelector('#modal').classList.contains('hidden')", timeout=60000)
        facts["popup_ms"] = round((time.perf_counter() - t0) * 1000)
        facts["reading_shown_when_opened"] = pg.evaluate("() => !!document.querySelector('#modal .mk-form .mk-reading') && (document.querySelector('#mk-status') || {textContent: ''}).textContent.includes('읽는 중')")
        pg.screenshot(path=str(OUT / "1_popup_opened_while_reading.png"))
        # 읽는 중에 Type 을 적는다
        pg.click("#mk-type"); pg.keyboard.type("ZZ9")
        pg.wait_for_function("() => !document.querySelector('#modal .mk-form .mk-reading')", timeout=60000)
        facts["filled_ms"] = round((time.perf_counter() - t0) * 1000)
        facts["type_kept_after_fill"] = pg.evaluate("() => document.querySelector('#mk-type').value") == "ZZ9"
        facts["qty_filled_by_proposal"] = pg.evaluate("() => document.querySelector('#mk-qty').value")
        facts["system_filled_by_proposal"] = pg.evaluate("() => document.querySelector('#mk-system').value")
        facts["status_cleared"] = pg.evaluate("() => (document.querySelector('#mk-status') || {textContent: ''}).textContent.trim()") == ""
        pg.screenshot(path=str(OUT / "2_proposal_filled_type_kept.png"))
        pg.fill("#mk-note", "hotfix91 자기검증")
        pg.click("#mk-save")
        pg.wait_for_function("() => document.querySelector('#modal').classList.contains('hidden')", timeout=60000)
        pg.wait_for_timeout(800)
        rows = json.load(urllib.request.urlopen(f"{base}/jobs/{JOB}/rows?tab=ALL"))
        added = [r for r in (rows if isinstance(rows, list) else rows.get("rows", [])) if (r.get("evidence") or {}).get("markup") and r.get("page_no") == pno]
        facts["added_row_type"] = (added[-1]["values"].get("type") if added else None)
        facts["added_row_user_qty_or_ai"] = (added[-1]["values"].get("qty") if added else None)
        pg.screenshot(path=str(OUT / "3_row_added.png"))
        facts["page_errors"] = errs
        ctx.close(); br.close()
finally:
    srv.terminate(); srv.wait(timeout=20); shutil.rmtree(SP.parent, ignore_errors=True)
(OUT / "result.json").write_text(json.dumps(facts, ensure_ascii=False, indent=1))
print(json.dumps(facts, ensure_ascii=False))
