"""hotfix80 — 옛 코드와 새 코드를 **번갈아** 재는 A/B 자 (같은 기계의 흔들림을 상쇄한다).

    python3 spike/perf_ab.py <옛 코드 폴더> <새 코드 폴더> <data_dir 사본 A> <data_dir 사본 B> <job> <out.json> [rounds=4]

두 서버를 같이 띄워 두고(장 그림 미리 그리기 · 일꾼은 둘 다 끈다 — CPU 를 나눠 쓰면 수치가 서로 섞인다) 한 브라우저가
회마다 A → B 순으로 같은 일을 한다: 결과 열기 · 목록 끝까지 굴리기(40걸음) · 검색 타자 6번 · 다른 장의 행 누르기 6번 ·
칸 하나 고치기 · 고친 뒤 목록 다시 받기.  값은 걸린 시간과 50ms 넘는 작업 수.  회마다 새 브라우저 문맥(캐시 없음).
★ 실 DB 를 열지 않는다 — 두 데이터 사본을 PID_DATA_DIR 로 가리킨다.
★ `perf_sim.py` 를 **import 하지 않는다** — 그 스크립트는 모듈 수준에서 제 argv 를 읽어 서버를 띄우고 캐시를 지운다
  (처음 판이 그렇게 했다가 저장소를 지웠다).  필요한 탐침은 여기 그대로 베껴 둔다.
"""
from __future__ import annotations
import json, os, socket, statistics, subprocess, sys, time, urllib.request
from pathlib import Path
from urllib.parse import quote

OLD, NEW, DA, DB = (Path(a) for a in sys.argv[1:5])
JOB, OUT = sys.argv[5], sys.argv[6]
ROUNDS = int(sys.argv[7]) if len(sys.argv) > 7 else 4

PROBE = """(() => {
  window.__lt = []; window.__frames = [];
  try { new PerformanceObserver(l => { for (const e of l.getEntries()) window.__lt.push([e.startTime, e.duration]); })
          .observe({type: 'longtask', buffered: true}); } catch (e) {}
  let last = performance.now();
  const tick = (t) => { window.__frames.push([t, t - last]); last = t; if (window.__frames.length > 20000) window.__frames.splice(0, 10000); requestAnimationFrame(tick); };
  requestAnimationFrame(tick);
})()"""
JS_HELP = """
window.__mark = () => performance.now();
window.__span = (t0) => { const t1 = performance.now();
  const lt = window.__lt.filter(([s, d]) => s + d >= t0 && s <= t1);
  return { ms: Math.round(t1 - t0), longtasks: lt.length, longtask_ms: Math.round(lt.reduce((a, [, d]) => a + d, 0)) }; };
window.__imgReady = (n) => new Promise(res => { const img = document.querySelector('#sheet');
  const ok = () => img.complete && img.naturalWidth > 0 && (img.getAttribute('src') || '').includes(`/page/${n}.png`);
  const iv = setInterval(() => { if (ok()) { clearInterval(iv); requestAnimationFrame(() => requestAnimationFrame(res)); } }, 4); });
window.__frame2 = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
"""
READY = "() => typeof S !== 'undefined' && S.job && !S.loading && S.rows && S.rows.length > 0 && document.querySelector('#body tr')"

def port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

def serve(root, data):
    p = port()
    env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(root), PID_PAGE_WARM="0", PID_RENDER_POOL="0", PID_ROWS_WARM="0")
    pr = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(p)],
                          cwd=str(root), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{p}"
    for _ in range(90):
        try: urllib.request.urlopen(base + "/version", timeout=2); break
        except Exception: time.sleep(1)
    return pr, base

srvA, baseA = serve(OLD, DA); srvB, baseB = serve(NEW, DB)
res = {"old": str(OLD), "new": str(NEW), "rounds": []}
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        for r in range(ROUNDS):
            rnd = {}
            for name, base in (("A", baseA), ("B", baseB)):
                ctx = br.new_context(viewport={"width": 1920, "height": 1080})
                ctx.add_init_script(PROBE)
                ctx.add_init_script("try{localStorage.removeItem('pid.split');localStorage.setItem('pid.side.off','1')}catch(e){}")
                pg = ctx.new_page(); errs = []
                pg.on("pageerror", lambda e: errs.append(str(e)))
                t0 = time.time()
                pg.goto(f"{base}/?embed=1&user={quote('홍길동')}#{JOB}")
                pg.wait_for_function(READY, timeout=180000)
                pg.evaluate(JS_HELP)
                first = pg.evaluate("() => S.page.page_no")
                pg.evaluate("n => __imgReady(n)", first)
                m = {"open_ms": round((time.time() - t0) * 1000)}
                m["rows_ms"] = pg.evaluate("() => { const e = performance.getEntriesByType('resource').find(x => x.name.includes('/rows?tab=ALL')); return e ? Math.round(e.duration) : null; }")
                pg.evaluate("() => { if (S.side) toggleSide(false); fit(); }"); pg.wait_for_timeout(500)
                m["gridscroll"] = pg.evaluate("""async () => { const gw = document.querySelector('#gridwrap'); gw.scrollTop = 0; await __frame2(); const t0 = __mark();
                    for (let i = 0; i < 40; i++) { gw.scrollTop += gw.clientHeight * 0.8; await new Promise(r => requestAnimationFrame(r)); }
                    await __frame2(); return __span(t0); }""")
                pg.evaluate("() => { document.querySelector('#gridwrap').scrollTop = 0; }"); pg.wait_for_timeout(300)
                pg.click("#filter"); keys = []
                for ch in ("P", "I", "T"):
                    t = pg.evaluate("__mark()"); pg.keyboard.type(ch); pg.wait_for_timeout(250)
                    keys.append(pg.evaluate("t0 => __frame2().then(() => __span(t0))", t))
                for _ in range(3):
                    t = pg.evaluate("__mark()"); pg.keyboard.press("Backspace"); pg.wait_for_timeout(250)
                    keys.append(pg.evaluate("t0 => __frame2().then(() => __span(t0))", t))
                m["search_key"] = {"ms": round(statistics.median(k["ms"] for k in keys)), "longtasks": sum(k["longtasks"] for k in keys)}
                pg.wait_for_timeout(300)
                rows = pg.evaluate("""() => { const out = []; const seen = new Set([S.page.page_no]);
                    for (const r of S.rows) { if (!r.removed && r.rect && r.rect.length === 4 && !seen.has(r.page_no)) { seen.add(r.page_no); out.push([r.key, r.page_no]); } if (out.length >= 6) break; } return out; }""")
                clicks = []
                for key, pno in rows:
                    clicks.append(pg.evaluate("""async ([k, n]) => { const tr = revealRow(k); tr.scrollIntoView({block: 'center'}); const t0 = __mark();
                        tr.querySelector('td[data-col="type"]').click(); await __imgReady(n);
                        await new Promise(res => { const iv = setInterval(() => { if (document.querySelector(`rect.det.sel[data-key="${k}"]`)) { clearInterval(iv); res(); } }, 4); });
                        await __frame2(); return __span(t0); }""", [key, pno]))
                m["rowclick"] = {"ms": round(statistics.median(c["ms"] for c in clicks)), "longtasks": sum(c["longtasks"] for c in clicks)}
                ek = pg.evaluate("() => S.rows.find(r => !r.removed && !r.deleted).key")
                pg.evaluate("k => revealRow(k).scrollIntoView({block:'center'})", ek)
                td = f'#body tr[data-key="{ek}"] td[data-col="remark"]'
                pg.dblclick(td); pg.wait_for_timeout(150); pg.keyboard.press("Control+A"); pg.keyboard.type(f"ab{r}")
                t = pg.evaluate("__mark()"); pg.keyboard.press("Enter")
                pg.wait_for_function(f"() => (S.rowByKey['{ek}'].user || {{}}).remark === 'ab{r}'", timeout=20000)
                m["edit"] = pg.evaluate("t0 => __frame2().then(() => __span(t0))", t)
                # 편집 뒤 목록을 다시 받는 시간 (새 창 · 다시 열기가 겪는 것)
                m["rows_after_edit_ms"] = pg.evaluate("""async () => { const t0 = performance.now(); const r = await fetch(`/jobs/${S.job.id}/rows?tab=ALL&slim=1`); await r.arrayBuffer(); return Math.round(performance.now() - t0); }""")
                m["errors"] = errs[:3]
                rnd[name] = m
                ctx.close()
            res["rounds"].append(rnd)
            print(json.dumps(rnd, ensure_ascii=False), flush=True)
        br.close()
finally:
    for p in (srvA, srvB):
        p.terminate()
        try: p.wait(10)
        except Exception: p.kill()

def med(name, f):
    vals = [f(r[name]) for r in res["rounds"] if r.get(name)]
    return statistics.median(vals) if vals else None
summ = {}
for k, f in (("open_ms", lambda m: m["open_ms"]), ("rows_ms", lambda m: m["rows_ms"] or 0), ("gridscroll_ms", lambda m: m["gridscroll"]["ms"]),
             ("gridscroll_long", lambda m: m["gridscroll"]["longtasks"]), ("search_ms", lambda m: m["search_key"]["ms"]),
             ("search_long", lambda m: m["search_key"]["longtasks"]), ("rowclick_ms", lambda m: m["rowclick"]["ms"]),
             ("rowclick_long", lambda m: m["rowclick"]["longtasks"]), ("edit_ms", lambda m: m["edit"]["ms"]),
             ("rows_after_edit_ms", lambda m: m["rows_after_edit_ms"])):
    summ[k] = {"A": med("A", f), "B": med("B", f)}
res["summary"] = summ
Path(OUT).parent.mkdir(parents=True, exist_ok=True)
Path(OUT).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print("\n== 중앙값 (회 %d · A=옛 · B=새)" % len(res["rounds"]))
for k, v in summ.items():
    print(f"  {k:20s} A {v['A']!s:>8}   B {v['B']!s:>8}")
