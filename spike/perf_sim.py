"""hotfix69 — 사용자가 실제로 하는 일을 여러 번 되풀이하며 잰다 (가볍게 만들기의 자).

    python3 spike/perf_sim.py <data_dir 사본> <job> <out.json> [rounds=3] [--lan]

★ 실 DB 를 열지 않는다 — 넘긴 데이터 폴더(사본)를 PID_DATA_DIR 로 가리킨다.  서버를 새로 띄우고 장 그림
디스크 캐시(`page_cache/<job>`)를 비운 채 시작한다 — 사용자가 처음 여는 결과와 같은 조건이다.
`--lan` 이면 브라우저 망을 사내망 정도(100Mbps · 지연 2ms)로 좁힌다.

되풀이하는 일 (한 회 = 아래 전부):
  open        결과 열기 (목록이 서고 첫 장 그림이 뜰 때까지)
  page×8      장 옮기기 (다음 장 · 그림이 다 뜰 때까지)
  zoom        +3번 · 맞춤 (각각 다음 그리기까지)
  pan         도면 끌기 20걸음 (가장 긴 프레임)
  rowclick×8  목록에서 다른 장의 행 누르기 (그 장 그림 · 선택 상자까지)
  boxclick×5  도면에서 상자 누르기 (근거 패널까지)
  search      검색창에 'PIT' 타자 (글자마다 목록이 다시 설 때까지)
  gridscroll  목록 끝까지 굴리기 (가장 긴 프레임)
  edit        칸 하나 고치기 (저장 응답 · 칸 갱신까지)
  popout      도면 새 창 (새 창 그림이 설 때까지 · 1회만)
각 일마다 걸린 시간 · 그 사이 50ms 넘는 작업(longtask) 수와 합 · 힙을 적는다.
"""
from __future__ import annotations
import json, os, shutil, socket, statistics, subprocess, sys, time, urllib.request
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
data, JOB, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
ROUNDS = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else 3
LAN = "--lan" in sys.argv
shutil.rmtree(data / "page_cache" / JOB, ignore_errors=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = f"http://127.0.0.1:{port}"

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
  const fr = window.__frames.filter(([t]) => t >= t0 && t <= t1).map(([, d]) => d);
  return { ms: Math.round(t1 - t0), longtasks: lt.length, longtask_ms: Math.round(lt.reduce((a, [, d]) => a + d, 0)),
           worst_frame: Math.round(fr.length ? Math.max(...fr) : 0),
           heap_mb: performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1048576) : null }; };
window.__imgReady = (n) => new Promise(res => { const img = document.querySelector('#sheet');
  const ok = () => img.complete && img.naturalWidth > 0 && (img.getAttribute('src') || '').includes(`/page/${n}.png`);
  const iv = setInterval(() => { if (ok()) { clearInterval(iv); requestAnimationFrame(() => requestAnimationFrame(res)); } }, 4); });
window.__frame2 = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
"""
READY = "() => typeof S !== 'undefined' && S.job && !S.loading && S.rows && S.rows.length > 0 && document.querySelector('#body tr')"
res = {"rounds": [], "lan": LAN, "job": JOB}

def act(pg, name, rnd, js, arg=None):
    out = pg.evaluate(js, arg) if arg is not None else pg.evaluate(js)
    rnd.setdefault(name, []).append(out)
    return out

try:
    for _ in range(90):
        try: urllib.request.urlopen(base + "/version", timeout=2); break
        except Exception: time.sleep(1)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
                                args=["--enable-precise-memory-info"])
        for r in range(ROUNDS):
            ctx = br.new_context(viewport={"width": 1920, "height": 1080})
            ctx.add_init_script(PROBE)
            ctx.add_init_script("try{localStorage.removeItem('pid.split');localStorage.setItem('pid.side.off','1')}catch(e){}")
            pg = ctx.new_page(); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            if LAN:
                cdp = ctx.new_cdp_session(pg)
                cdp.send("Network.enable")
                cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 2,
                         "downloadThroughput": 100e6 / 8, "uploadThroughput": 100e6 / 8})
            rnd = {}
            t0 = time.time()
            pg.goto(f"{base}/?embed=1&user={quote('홍길동')}#{JOB}")
            pg.wait_for_function(READY, timeout=180000)
            pg.evaluate(JS_HELP)
            first = pg.evaluate("() => S.page.page_no")
            pg.evaluate("n => __imgReady(n)", first)
            rnd["open"] = [{"ms": round((time.time() - t0) * 1000)}]
            # 무엇이 열기를 잡았나 — 요청마다 시작 · 걸린 시간 (가장 늦게 끝난 것부터)
            rnd["open_resources"] = pg.evaluate("""() => performance.getEntriesByType('resource')
                .map(r => [r.name.replace(location.origin, '').slice(0, 60), Math.round(r.startTime), Math.round(r.duration)])
                .sort((a, b) => (b[1] + b[2]) - (a[1] + a[2])).slice(0, 12)""")
            rnd["open_ready_ms"] = pg.evaluate("() => Math.round(performance.now())")
            pg.evaluate("() => { if (S.side) toggleSide(false); fit(); }"); pg.wait_for_timeout(400)
            pages = pg.evaluate("() => S.pages.filter(p => p.layers && Object.keys(p.layers).length).map(p => p.page_no)")
            i0 = pages.index(first) if first in pages else 0
            # 장 옮기기
            for k in range(1, 9):
                n = pages[(i0 + k * (1 + r)) % len(pages)]
                act(pg, "page", rnd, """async (n) => { const t0 = __mark(); const sel = document.querySelector('#page-select');
                    sel.value = String(n); sel.dispatchEvent(new Event('change', {bubbles: true})); await __imgReady(n); return __span(t0); }""", n)
            # 확대 · 맞춤
            for z in ("1", "1", "1", "0"):
                act(pg, "zoom", rnd, """async (z) => { const t0 = __mark(); document.querySelector(`button[data-z="${z}"]`).click();
                    await __frame2(); return __span(t0); }""", z)
            # 도면 끌기
            act(pg, "pan", rnd, """async () => { const st = document.querySelector('#stage'); const t0 = __mark();
                for (let i = 0; i < 20; i++) { st.scrollLeft += 40; st.scrollTop += 25; await new Promise(r => requestAnimationFrame(r)); }
                await __frame2(); return __span(t0); }""")
            pg.evaluate("() => fit()"); pg.wait_for_timeout(200)
            # 목록에서 다른 장의 행 누르기
            keys = pg.evaluate("""() => { const out = []; const seen = new Set([S.page.page_no]);
                for (const r of S.rows) { if (!r.removed && r.rect && r.rect.length === 4 && !seen.has(r.page_no)) { seen.add(r.page_no); out.push([r.key, r.page_no]); }
                  if (out.length >= 8) break; } return out; }""")
            for key, pno in keys:
                act(pg, "rowclick", rnd, """async ([k, n]) => { const tr = window.revealRow ? revealRow(k) : document.querySelector(`#body tr[data-key="${k}"]`);
                    tr.scrollIntoView({block: 'center'}); const t0 = __mark();
                    tr.querySelector('td[data-col="type"]').click();
                    await __imgReady(n);
                    await new Promise(res => { const iv = setInterval(() => { if (document.querySelector(`rect.det.sel[data-key="${k}"]`)) { clearInterval(iv); res(); } }, 4); });
                    await __frame2(); return __span(t0); }""", [key, pno])
            # 도면에서 상자 누르기
            bkeys = pg.evaluate("() => S.rows.filter(r => r.page_no === S.page.page_no && !r.removed && r.values.type).map(r => r.key).slice(0, 5)")
            for k in bkeys:
                act(pg, "boxclick", rnd, """async (k) => { const el = document.querySelector(`rect.det[data-key="${k}"]`); const t0 = __mark();
                    el.dispatchEvent(new MouseEvent('click', {bubbles: true})); await __frame2();
                    if (typeof closeScopePop === 'function') closeScopePop(); return __span(t0); }""", k)
            # 검색 타자
            pg.click("#filter")
            for ch in ("P", "I", "T"):
                t0 = pg.evaluate("__mark()")
                pg.keyboard.type(ch)
                pg.wait_for_timeout(30)
                rnd.setdefault("search_key", []).append(pg.evaluate("t0 => __frame2().then(() => __span(t0))", t0))
            for _ in range(3):
                t0 = pg.evaluate("__mark()")
                pg.keyboard.press("Backspace"); pg.wait_for_timeout(30)
                rnd.setdefault("search_key", []).append(pg.evaluate("t0 => __frame2().then(() => __span(t0))", t0))
            pg.wait_for_timeout(300)
            # 목록 굴리기
            act(pg, "gridscroll", rnd, """async () => { const gw = document.querySelector('#gridwrap'); gw.scrollTop = 0; const t0 = __mark();
                for (let i = 0; i < 40; i++) { gw.scrollTop += gw.clientHeight * 0.8; await new Promise(r => requestAnimationFrame(r)); }
                await __frame2(); return __span(t0); }""")
            # 칸 고치기
            ek = pg.evaluate("() => S.rows.find(r => !r.removed && !r.deleted).key")
            pg.evaluate("k => (window.revealRow ? revealRow(k) : document.querySelector(`#body tr[data-key=\"${k}\"]`)).scrollIntoView({block:'center'})", ek)
            td = f'#body tr[data-key="{ek}"] td[data-col="remark"]'
            pg.click(td); pg.keyboard.press("Control+A"); pg.keyboard.type(f"perf{r}")
            t0 = pg.evaluate("__mark()")
            pg.keyboard.press("Enter")
            pg.wait_for_function(f"() => (S.rowByKey['{ek}'].user || {{}}).remark === 'perf{r}'", timeout=20000)
            rnd["edit"] = [pg.evaluate("t0 => __frame2().then(() => __span(t0))", t0)]
            if r == 0:
                # 도면 새 창
                t0 = time.time()
                with ctx.expect_page() as pi:
                    pg.click('.pop-btn[data-pane="drawing"]')
                dr = pi.value; dr.set_viewport_size({"width": 1920, "height": 1080})
                dr.wait_for_function(READY, timeout=180000)
                dr.wait_for_function("() => document.querySelector('#sheet').complete && document.querySelector('#sheet').naturalWidth > 0", timeout=60000)
                rnd["popout"] = [{"ms": round((time.time() - t0) * 1000)}]
                dr.close(); pg.wait_for_timeout(1200)
            rnd["errors"] = errs
            rnd["heap_mb_end"] = pg.evaluate("performance.memory ? Math.round(performance.memory.usedJSHeapSize/1048576) : null")
            res["rounds"].append(rnd)
            print(f"round {r}: open {rnd['open'][0]['ms']}ms · page med {statistics.median(x['ms'] for x in rnd['page'])}ms"
                  f" · rowclick med {statistics.median(x['ms'] for x in rnd['rowclick'])}ms · errors {len(errs)}", flush=True)
            ctx.close()
        br.close()
finally:
    srv.terminate()

# 요약 — 일마다 회를 넘어 모은 중앙값 · 최댓값
summ = {}
for rnd in res["rounds"]:
    for k, v in rnd.items():
        if not isinstance(v, list) or not v or not isinstance(v[0], dict):
            continue
        summ.setdefault(k, []).extend(v)
table = {}
for k, v in summ.items():
    ms = [x["ms"] for x in v]
    table[k] = {"n": len(v), "median_ms": statistics.median(ms), "max_ms": max(ms),
                "longtasks": sum(x.get("longtasks", 0) for x in v),
                "longtask_ms": sum(x.get("longtask_ms", 0) for x in v),
                "worst_frame": max((x.get("worst_frame", 0) for x in v), default=0)}
res["summary"] = table
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
for k, t in table.items():
    print(f"  {k:11s} n={t['n']:3d}  중앙 {t['median_ms']:7.0f}ms  최대 {t['max_ms']:7.0f}ms  long {t['longtasks']:3d}건/{t['longtask_ms']:6d}ms  최악프레임 {t['worst_frame']}ms")
