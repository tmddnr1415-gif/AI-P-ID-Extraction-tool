"""hotfix45 — 나란히 보기 · 이전/현재 전환이 **얼마나 걸리고 얼마나 무거운가**를 띄워서 잰다.

    python3 spike/ui_audit_side_speed.py <data_dir> <job_B> <out_dir> [label]

재는 것 (전부 실제 브라우저 · 실제 서버 · 요청 수와 바이트까지):
  ① 결과 열기 (S.job 뜰 때까지)
  ② 나란히 켬 — 오른쪽 장 그림이 뜰 때까지 · 그동안의 요청 수 · 받은 바이트
  ③ 나란히 켠 채 장 바꾸기 세 번 — 오른쪽이 따라올 때까지
  ④ 왼쪽을 40번 스크롤 — 걸린 시간과 가장 긴 프레임 (렉)
  ⑤ 나란히 끄고 다시 켬 (캐시)
  ⑥ 이전 결과로 전환 → 현재로 복귀 (switchView)
  ⑦ JS 힙 (performance.memory)
  ⑧ 페이지 오류 0
결과는 <out_dir>/<label>.json 과 README 한 줄.  판정은 없다 — 전/후를 같은 자로 잰다.
"""
from __future__ import annotations
import json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data, JOB, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
LABEL = sys.argv[4] if len(sys.argv) > 4 else "run"
OUT.mkdir(parents=True, exist_ok=True)
R = {"label": LABEL}
def note(k, v): print(f"{k}: {v}", flush=True); R[k] = v
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(90):
        try: urllib.request.urlopen(f"http://127.0.0.1:{port}/home", timeout=2); break
        except Exception: time.sleep(1)
    rev = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/jobs/{JOB}/revision", timeout=60).read())
    prev = rev.get("previous_job_id")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
        br = pw.chromium.launch(executable_path=exe if Path(exe).exists() else None, args=["--enable-precise-memory-info"])
        pg = br.new_page(viewport={"width": 1800, "height": 1000})
        # 자동 켜짐(autoSide)을 끈 채로 연다 — 켜는 비용을 따로 재려고 (사람이 끈 것과 같은 상태)
        pg.add_init_script("try { localStorage.setItem('pid.side.off', '1'); } catch (e) {}")
        errs = []; reqs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
        timed = []
        def on_resp(r):
            try: reqs.append((r.url, int(r.headers.get("content-length") or 0)))
            except Exception: reqs.append((r.url, 0))
            try:
                tm = r.request.timing; ms = int(tm.get("responseEnd", 0) - tm.get("requestStart", 0)) if tm else -1
            except Exception: ms = -1
            timed.append((r.url, reqs[-1][1], ms))
        pg.on("response", on_resp)
        t0 = time.time()
        pg.goto(f"http://127.0.0.1:{port}/#{JOB}")
        pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.pages && S.pages.length > 0", timeout=180000)
        note("open_ms", int((time.time() - t0) * 1000))
        pg.wait_for_timeout(1500)
        # 자동으로 켜졌으면 끈다 — 켜는 시간을 따로 재려고
        pg.evaluate("() => { if (S.side) toggleSide(false, false); }")
        pg.wait_for_timeout(500)
        # 삭제 후보가 가장 많은 장 (이번 결과에 있는 장)
        pages = pg.evaluate("() => S.pages.map(p => ({n: p.page_no, d: p.drawing_no}))")
        by_dwg = {}
        for d in rev.get("deleted_candidates") or []: by_dwg[d.get("drawing_no")] = by_dwg.get(d.get("drawing_no"), 0) + 1
        have = {p["d"] for p in pages}
        cand = sorted(((n, d) for d, n in by_dwg.items() if d in have), reverse=True)
        target = next((p["n"] for p in pages if cand and p["d"] == cand[0][1]), pages[0]["n"])
        pg.select_option("#page-select", str(target))
        pg.wait_for_function("() => S.page && !S.pending && document.querySelector('#sheet').complete && document.querySelector('#sheet').naturalWidth > 0", timeout=60000)
        pg.wait_for_timeout(300)
        # ② 나란히 켬
        n0 = len(reqs); t = time.time()
        pg.evaluate("() => toggleSide(true, true)")
        pg.wait_for_function("() => S.side && S.cmpPage && document.querySelector('#cmp-sheet').complete && document.querySelector('#cmp-sheet').naturalWidth > 0 && !document.querySelector('#cmp-head').textContent.includes('읽는 중')", timeout=180000)
        note("side_on_ms", int((time.time() - t) * 1000))
        got = reqs[n0:]
        note("side_on_requests", len(got))
        note("side_on_bytes", sum(b for _, b in got))
        note("side_on_urls", [u.split(f":{port}")[-1][:60] for u, _ in got])
        note("side_page", target)
        # ③ 장 바꾸기 세 번
        idx = [i for i, p in enumerate(pages) if p["n"] == target][0]
        nxt = [pages[(idx + k) % len(pages)]["n"] for k in (1, 2, 3)]
        ms = []
        for n in nxt:
            n1 = len(reqs); t = time.time()
            pg.select_option("#page-select", str(n))
            pg.wait_for_function(f"() => S.page && S.page.page_no === {n} && !S.pending && document.querySelector('#sheet').complete && document.querySelector('#sheet').naturalWidth > 0 && ((S.cmpPage && document.querySelector('#cmp-sheet').complete && document.querySelector('#cmp-sheet').naturalWidth > 0) || document.querySelector('#cmp-sheet').style.display === 'none') && !document.querySelector('#cmp-head').textContent.includes('읽는 중')", timeout=120000)
            ms.append(int((time.time() - t) * 1000))
            pg.wait_for_timeout(200)
        note("page_switch_ms", ms)
        # ④ 스크롤 40번 — 가장 긴 프레임
        pg.evaluate("() => { S.zoom = 2; applyZoom(); }"); pg.wait_for_timeout(300)
        lag = pg.evaluate("""async () => {
            const st = document.querySelector('#stage');
            st.scrollLeft = 0; st.scrollTop = 0;
            let last = performance.now(), worst = 0, frames = 0;
            const t0 = performance.now();
            for (let i = 0; i < 40; i++) {
              st.scrollLeft += 25; st.scrollTop += 12;
              await new Promise(r => requestAnimationFrame(r));
              const now = performance.now(); worst = Math.max(worst, now - last); last = now; frames++;
            }
            const cs = document.querySelector('#cmp-stage');
            return {total_ms: Math.round(performance.now() - t0), worst_frame_ms: Math.round(worst),
                    synced: cs.scrollLeft === st.scrollLeft && cs.scrollTop === st.scrollTop,
                    left: [st.scrollLeft, st.scrollTop], right: [cs.scrollLeft, cs.scrollTop]};
        }""")
        pg.wait_for_timeout(200)
        lag["synced_after"] = pg.evaluate("() => { const st = document.querySelector('#stage'), cs = document.querySelector('#cmp-stage'); return cs.scrollLeft === st.scrollLeft && cs.scrollTop === st.scrollTop; }")
        note("scroll", lag)
        # ⑤ 끄고 다시 켬
        pg.evaluate("() => toggleSide(false, true)"); pg.wait_for_timeout(300)
        n0 = len(reqs); t = time.time()
        pg.evaluate("() => toggleSide(true, true)")
        pg.wait_for_function("() => S.side && document.querySelector('#cmp-sheet').complete && document.querySelector('#cmp-sheet').naturalWidth > 0", timeout=60000)
        note("side_reon_ms", int((time.time() - t) * 1000)); note("side_reon_requests", len(reqs) - n0)
        pg.evaluate("() => toggleSide(false, true)"); pg.wait_for_timeout(300)
        # ⑥ 전환
        if prev:
            n0 = len(reqs); t = time.time(); pg.evaluate(f"() => switchView('{prev}')")
            pg.wait_for_function(f"() => S.job && S.job.id === '{prev}' && !S.loading", timeout=180000)
            note("switch_prev_ms", int((time.time() - t) * 1000))
            # 그동안의 요청과 각 요청이 걸린 시간 — 어디서 시간이 가는지
            note("switch_prev_requests", [(u.split(f":{port}")[-1][:48], b, ms) for u, b, ms in timed[n0:]])
            note("switch_prev_js_ms", pg.evaluate("() => S.lastSwitchMs"))
            pg.wait_for_timeout(500)
            t = time.time(); pg.evaluate(f"() => switchView('{JOB}')")
            pg.wait_for_function(f"() => S.job && S.job.id === '{JOB}' && !S.loading", timeout=180000)
            note("switch_back_ms", int((time.time() - t) * 1000))
        # ⑦ 힙
        mem = pg.evaluate("() => performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1048576) : null")
        note("js_heap_mb", mem)
        pg.evaluate("() => toggleSide(true, true)")
        pg.wait_for_function("() => S.side && document.querySelector('#cmp-sheet').complete", timeout=60000); pg.wait_for_timeout(800)
        pg.screenshot(path=str(OUT / f"{LABEL}_side.png"))
        note("page_errors", errs[:5])
        br.close()
finally:
    srv.terminate()
(OUT / f"{LABEL}.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
print("saved", OUT / f"{LABEL}.json")
