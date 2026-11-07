"""hotfix79 — 화면 동작 하나를 CPU 프로파일로 잰다 (어느 함수가 시간을 먹나).

    python3 spike/ui_profile.py <data_dir 사본> <job> <out.txt> [--root <코드 폴더>]

★ 실 DB 를 열지 않는다 — 넘긴 데이터 폴더(사본)를 PID_DATA_DIR 로 가리킨다.
잰다: 목록에서 다른 장의 행 누르기 ×6 · 도면 상자 누르기 ×5 · 목록 끝까지 굴리기 · 화살표 ↓ 20번(칸 이동) ·
칸 하나 고치기(Enter).  각 동작 묶음마다 함수별 self 시간 상위 25 를 적는다 (Chrome DevTools 프로토콜 Profiler).
"""
from __future__ import annotations
import collections, json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path
from urllib.parse import quote

args = sys.argv[1:]
root_arg = None
if "--root" in args:
    i = args.index("--root"); root_arg = Path(args[i + 1]); del args[i:i + 2]
ROOT = root_arg or Path(__file__).resolve().parent.parent
data, JOB, OUT = Path(args[0]), args[1], Path(args[2])
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = f"http://127.0.0.1:{port}"
LINES = []


def summarise(name, prof, wall):
    nodes = {n["id"]: n for n in prof["nodes"]}
    dt = prof.get("timeDeltas") or []
    samples = prof.get("samples") or []
    self_us = collections.Counter()
    for sid, d in zip(samples, dt):
        n = nodes.get(sid)
        if not n:
            continue
        cf = n["callFrame"]
        fn = cf.get("functionName") or "(anon)"
        url = (cf.get("url") or "").rsplit("/", 1)[-1].split("?")[0]
        key = f"{fn} {url}:{cf.get('lineNumber', 0) + 1}" if url else fn
        self_us[key] += d
    total = sum(self_us.values()) / 1000
    LINES.append(f"\n== {name} — 걸린 시간 {wall:.0f}ms · 표본 합 {total:.0f}ms")
    for k, us in self_us.most_common(25):
        LINES.append(f"  {us / 1000:8.1f}ms  {k}")
    print("\n".join(LINES[-27:]), flush=True)


try:
    for _ in range(90):
        try: urllib.request.urlopen(base + "/version", timeout=2); break
        except Exception: time.sleep(1)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        ctx = br.new_context(viewport={"width": 1920, "height": 1080})
        ctx.add_init_script("try{localStorage.setItem('pid.side.off','1');localStorage.removeItem('pid.split')}catch(e){}")
        pg = ctx.new_page()
        pg.goto(f"{base}/?embed=1&user={quote('홍길동')}"); pg.wait_for_timeout(1500)
        pg.evaluate(f"open('{JOB}')")
        pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.vlist && S.vlist.length > 3", timeout=180000)
        pg.wait_for_timeout(2500)
        if pg.evaluate("() => !!S.side"):
            pg.evaluate("() => toggleSide(false)"); pg.wait_for_timeout(500)
        cdp = ctx.new_cdp_session(pg)
        cdp.send("Profiler.enable")
        cdp.send("Profiler.setSamplingInterval", {"interval": 200})

        def prof(name, fn):
            # 1) 렌더러 주 스레드의 브라우저 일(스타일 · 배치 · 칠하기 · 그림 풀기)을 이름별로 — JS 프로파일의
            #    "(program)" 이 무엇인지 가른다.  2) 그다음 JS 함수별 self 시간.
            br.start_tracing(page=pg, categories=["devtools.timeline", "disabled-by-default-devtools.timeline"])
            fn()
            raw = br.stop_tracing()
            ev = json.loads(raw).get("traceEvents", [])
            tids = collections.Counter(e.get("tid") for e in ev if e.get("name") == "RunTask")
            main = None
            for e in ev:
                if e.get("name") == "thread_name" and (e.get("args") or {}).get("name") == "CrRendererMain":
                    main = (e.get("pid"), e.get("tid"))
            by = collections.Counter()
            for e in ev:
                if e.get("ph") != "X" or (e.get("pid"), e.get("tid")) != main:
                    continue
                if e.get("name") in ("UpdateLayoutTree", "Layout", "Paint", "PrePaint", "Layerize", "UpdateLayer",
                                     "Decode Image", "ImageDecodeTask", "HitTest", "ParseHTML", "FunctionCall",
                                     "EvaluateScript", "RecalculateStyles", "ScheduleStyleRecalculation",
                                     "Commit", "PaintImage", "GPUTask", "TimerFire", "EventDispatch", "FireAnimationFrame"):
                    by[e["name"]] += e.get("dur", 0)
            LINES.append(f"\n== {name} — 주 스레드 브라우저 일 (겹침 포함 · ms)")
            for k, us in by.most_common(14):
                LINES.append(f"  {us / 1000:8.1f}ms  {k}")
            print("\n".join(LINES[-15:]), flush=True)
            cdp.send("Profiler.start")
            t0 = time.time()
            fn()
            wall = (time.time() - t0) * 1000
            p = cdp.send("Profiler.stop")["profile"]
            summarise(name, p, wall)

        keys = pg.evaluate("""() => { const out = []; const seen = new Set([S.page.page_no]);
            for (const r of S.rows) { if (!r.removed && r.rect && r.rect.length === 4 && !seen.has(r.page_no)) { seen.add(r.page_no); out.push([r.key, r.page_no]); }
              if (out.length >= 6) break; } return out; }""")

        def rowclicks():
            for k, n in keys:
                pg.evaluate("""async ([k, n]) => { const tr = revealRow(k); tr.scrollIntoView({block: 'center'});
                    tr.querySelector('td[data-col="type"]').click();
                    await new Promise(res => { const iv = setInterval(() => { if (document.querySelector(`rect.det.sel[data-key="${k}"]`)) { clearInterval(iv); res(); } }, 4); });
                    await new Promise(r => setTimeout(r, 400)); }""", [k, n])
        prof("목록 행 누르기 ×6 (다른 장)", rowclicks)

        bkeys = pg.evaluate("() => S.rows.filter(r => r.page_no === S.page.page_no && !r.removed && r.values.type).map(r => r.key).slice(0, 5)")

        def boxclicks():
            for k in bkeys:
                pg.evaluate("""async (k) => { const el = document.querySelector(`rect.det[data-key="${k}"]`);
                    el.dispatchEvent(new MouseEvent('click', {bubbles: true}));
                    await new Promise(r => setTimeout(r, 250)); if (typeof closeScopePop === 'function') closeScopePop(); }""", k)
        prof("도면 상자 누르기 ×5", boxclicks)

        def scroll():
            pg.evaluate("""async () => { const gw = document.querySelector('#gridwrap'); gw.scrollTop = 0;
                for (let i = 0; i < 40; i++) { gw.scrollTop += gw.clientHeight * 0.8; await new Promise(r => requestAnimationFrame(r)); } }""")
        prof("목록 끝까지 굴리기", scroll)

        k0 = pg.evaluate("() => S.vlist[5].key")
        pg.evaluate("k => revealRow(k).scrollIntoView({block:'center'})", k0)
        pg.click(f'#body tr[data-key="{k0}"] td[data-col="line_no"]'); pg.wait_for_timeout(400)

        def arrows():
            for _ in range(20):
                pg.keyboard.press("ArrowDown")
            pg.wait_for_timeout(800)
        prof("화살표 ↓ 20번 (칸 이동)", arrows)

        k1 = pg.evaluate("() => S.cell && S.cell.key")

        def edit():
            pg.keyboard.type("PROF1"); pg.keyboard.press("Enter")
            pg.wait_for_function(f"() => (S.rowByKey['{k1}'].user || {{}}).line_no === 'PROF1'", timeout=20000)
            pg.wait_for_timeout(300)
        prof("칸 하나 고치기 (Enter)", edit)
        br.close()
finally:
    srv.terminate()
    try: srv.wait(10)
    except Exception: srv.kill()
OUT.write_text("\n".join(LINES) + "\n", encoding="utf-8")
