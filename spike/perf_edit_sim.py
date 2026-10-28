"""hotfix75 — 고치는 일의 속도 (마크업 · 도면에서 범위로 고르기 · 고친 값이 목록에 서기까지).

    python3 spike/perf_edit_sim.py <data_dir 사본> <job> <out.json> [rounds=3] [--root <코드 폴더>]

★ 실 DB 를 열지 않는다 — 넘긴 데이터 폴더(사본)를 PID_DATA_DIR 로 가리킨다.  고치는 일이므로 **회마다 사본을
새로 뜬다** (앞 회가 고친 값이 다음 회를 바꾸지 않게).  `--root` 로 다른 코드(전 판 worktree)를 같은 자로 잰다.

한 회 = 행이 가장 많은 장에서:
  band        Shift 를 누른 채 도면 위를 끌어 상자 묶기 (띠를 놓은 뒤 묶음 판이 설 때까지)
  scope_multi 묶은 행 전부 공급 주체 바꾸기 (`applyScopeToMulti`)
  qty_page    승수 라벨 '이 페이지 전체' (`applyQtyToRows`)
  edit_one    칸 하나 고치기 (`saveField` — 저장 응답 · 목록 칸 · 도면까지)
  dismiss     묶은 행 전부 '둘 다 아님' (`dismissRows`)
  restore     지운 행 하나 되돌리기 (`restoreRow`)
  add_row     [+행] 을 누르고 2초 뒤 점을 고르면 행이 목록에 설 때까지 (`startPick` → `createRow`)
각 일마다 걸린 시간 · 그 사이 50ms 넘는 작업 수 · 요청 수와 받은 바이트를 적는다.
"""
from __future__ import annotations
import json, os, shutil, socket, statistics, subprocess, sys, time, urllib.request
from pathlib import Path
from urllib.parse import quote

args = [a for a in sys.argv[1:]]
root_arg = None
if "--root" in args:
    i = args.index("--root"); root_arg = Path(args[i + 1]); del args[i:i + 2]
ROOT = root_arg or Path(__file__).resolve().parent.parent
src, JOB, OUT = Path(args[0]), args[1], Path(args[2])
ROUNDS = int(args[3]) if len(args) > 3 and args[3].isdigit() else 3

PROBE = """(() => {
  window.__lt = [];
  try { new PerformanceObserver(l => { for (const e of l.getEntries()) window.__lt.push([e.startTime, e.duration]); })
          .observe({type: 'longtask', buffered: true}); } catch (e) {}
})()"""
HELP = """
window.__mark = () => [performance.now(), performance.getEntriesByType('resource').length];
window.__span = ([t0, n0]) => { const t1 = performance.now();
  const lt = window.__lt.filter(([s, d]) => s + d >= t0 && s <= t1);
  const res = performance.getEntriesByType('resource').slice(n0);
  return { ms: Math.round(t1 - t0), longtasks: lt.length, longtask_ms: Math.round(lt.reduce((a, [, d]) => a + d, 0)),
           requests: res.length, kb: Math.round(res.reduce((a, r) => a + (r.transferSize || 0), 0) / 1024),
           urls: res.map(r => r.name.replace(location.origin, '').split('?')[0].slice(0, 40)).slice(0, 12) }; };
window.__frame2 = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
"""
READY = "() => typeof S !== 'undefined' && S.job && !S.loading && S.rows && S.rows.length > 0 && document.querySelector('#body tr')"
res = {"rounds": [], "job": JOB, "root": str(ROOT)}
import tempfile  # noqa: E402
SP = Path(tempfile.mkdtemp(prefix="perf_edit_")) / "data"     # 사본은 저장소 밖에 (DB 사본이 커밋되지 않게)

try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        for r in range(ROUNDS):
            shutil.rmtree(SP, ignore_errors=True)
            shutil.copytree(src, SP, ignore=shutil.ignore_patterns("page_cache", "backups"))
            s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
            env = dict(os.environ, PID_DATA_DIR=str(SP), PYTHONPATH=str(ROOT))
            srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                                    "--port", str(port)], cwd=str(ROOT), env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            base = f"http://127.0.0.1:{port}"
            try:
                for _ in range(90):
                    try: urllib.request.urlopen(base + "/version", timeout=2); break
                    except Exception: time.sleep(1)
                ctx = br.new_context(viewport={"width": 1920, "height": 1080})
                ctx.add_init_script(PROBE)
                ctx.add_init_script("try{localStorage.removeItem('pid.split');localStorage.setItem('pid.side.off','1')}catch(e){}")
                pg = ctx.new_page(); errs = []
                pg.on("pageerror", lambda e: errs.append(str(e)))
                pg.on("dialog", lambda d: d.accept())
                pg.goto(f"{base}/?embed=1&user={quote('홍길동')}")
                pg.wait_for_function("() => typeof S !== 'undefined' && typeof open === 'function'", timeout=60000)
                pg.wait_for_timeout(1500)
                pg.evaluate(f"open('{JOB}')")
                pg.wait_for_function(READY, timeout=180000)
                pg.evaluate(HELP)
                pno = pg.evaluate("""() => { const c = {}; for (const r of S.rows) if (!r.removed && r.rect && r.rect.length === 4) c[r.page_no] = (c[r.page_no] || 0) + 1;
                    return +Object.entries(c).sort((a, b) => b[1] - a[1])[0][0]; }""")
                pg.evaluate("n => { if (S.side) toggleSide(false); const sel = document.querySelector('#page-select'); sel.value = String(n); sel.dispatchEvent(new Event('change', {bubbles: true})); }", pno)
                pg.wait_for_function("n => S.page && S.page.page_no === n && !S.loading", arg=pno, timeout=60000)
                pg.wait_for_timeout(1500)
                pg.evaluate("() => fit()"); pg.wait_for_timeout(500)
                rnd = {"page": pno, "rows_on_page": pg.evaluate("n => pageQtyRows(n).length", pno)}
                # band — 도면 위 왼쪽 위 1/2 를 Shift 끌기
                box = pg.evaluate("() => { const r = document.querySelector('#stage').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }")
                x0, y0 = box[0] + 10, box[1] + 10
                x1, y1 = box[0] + box[2] * 0.95, box[1] + box[3] * 0.95
                pg.keyboard.down("Shift")
                pg.mouse.move(x0, y0); pg.mouse.down(); pg.mouse.move((x0 + x1) / 2, (y0 + y1) / 2, steps=4)
                pg.mouse.move(x1, y1, steps=4)
                t = pg.evaluate("__mark()")
                pg.mouse.up(); pg.keyboard.up("Shift")
                rnd["band"] = pg.evaluate("t => __frame2().then(() => __span(t))", t)
                rnd["band"]["selected"] = pg.evaluate("() => S.multi.size")
                rnd["scope_multi"] = pg.evaluate("""async () => { const t = __mark(); await applyScopeToMulti('VENDOR');
                    await __frame2(); return __span(t); }""")
                rnd["scope_multi"]["ok"] = pg.evaluate("() => multiRows().every(r => r.values.scope === 'VENDOR')")
                pg.evaluate("() => { if (typeof clearMulti === 'function') clearMulti(); else S.multi.clear(); }")
                rnd["qty_page"] = pg.evaluate("""async (n) => { const t = __mark(); await applyQtyToRows(pageQtyRows(n), '7', '이 페이지 전체');
                    await __frame2(); return __span(t); }""", pno)
                rnd["qty_page"]["ok"] = pg.evaluate("n => pageQtyRows(n).every(r => String(cellValue(r, 'qty')) === '7')", pno)
                rnd["edit_one"] = pg.evaluate("""async (n) => { const row = pageQtyRows(n)[0]; const t = __mark();
                    await saveField(row, 'qty', '3'); await __frame2(); const out = __span(t);
                    const td = document.querySelector(`#body tr[data-key="${CSS.escape(row.key)}"] td[data-col="qty"]`);
                    out.ok = row.values.qty === 3 && (!td || td.textContent === '3'); return out; }""", pno)
                keys = pg.evaluate("n => pageQtyRows(n).slice(1, 21).map(r => r.key)", pno)
                pg.evaluate("ks => { S.multi = new Set(ks); }", keys)
                rnd["dismiss"] = pg.evaluate("""async (ks) => { const t = __mark(); await dismissRows(ks);
                    await __frame2(); const out = __span(t); out.n = ks.length; out.ok = ks.every(k => S.rowByKey[k] && S.rowByKey[k].removed); return out; }""", keys)
                rnd["restore"] = pg.evaluate("""async (k) => { const t = __mark(); await restoreRow(k);
                    await __frame2(); const out = __span(t); out.ok = !!(S.rowByKey[k] && !S.rowByKey[k].removed); return out; }""", keys[0])
                # 실제 흐름: [+행] 을 누르고(startPick) 사람이 점을 고르는 데 2초 → 그 점에 행이 선다
                rnd["add_row"] = pg.evaluate("""async () => { const n0 = S.rows.length; startPick();
                    await new Promise(r => setTimeout(r, 2000)); endPick(); const t = __mark();
                    await createRow([300, 300]); await __frame2(); const out = __span(t);
                    out.ok = S.rows.length === n0 + 1 && !!S.rowByKey[S.sel] && S.rowByKey[S.sel].added; return out; }""")
                rnd["errors"] = errs[:5]
                res["rounds"].append(rnd)
                print(json.dumps({k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if kk != "urls"})
                                  for k, v in rnd.items()}, ensure_ascii=False), flush=True)
                ctx.close()
            finally:
                srv.kill(); srv.wait(30)
        br.close()
finally:
    shutil.rmtree(SP, ignore_errors=True)
    summ = {}
    for k in ("band", "scope_multi", "qty_page", "edit_one", "dismiss", "restore", "add_row"):
        vals = [r[k]["ms"] for r in res["rounds"] if k in r]
        if vals:
            summ[k] = {"median_ms": statistics.median(vals), "max_ms": max(vals),
                       "requests": res["rounds"][-1][k].get("requests"), "kb": res["rounds"][-1][k].get("kb"),
                       "longtasks": res["rounds"][-1][k].get("longtasks")}
    res["summary"] = summ
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summ, ensure_ascii=False, indent=1))
