"""hotfix68 — 결과 화면을 여는 데 무엇이 얼마나 걸리나 (전/후 같은 자).

    python3 spike/ui_measure_open.py <base_url> <job> <out.json> [pane]

서버는 따로 띄운다 (실 DB 를 열지 않는다 — 사본의 PID_DATA_DIR).  세 번 열어 각 요청의
시간·전송 바이트(압축 뒤)·open() 전체 시간·가장 긴 작업을 적는다.
"""
from __future__ import annotations
import json, sys
base, JOB, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
pane = sys.argv[4] if len(sys.argv) > 4 else ""
from playwright.sync_api import sync_playwright
res = []
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
    for i in range(3):
        ctx = br.new_context(viewport={"width": 1920, "height": 1080})
        pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        cdp = ctx.new_cdp_session(pg); cdp.send("Network.enable")
        enc = {}
        cdp.on("Network.loadingFinished", lambda e: enc.__setitem__(e["requestId"], e["encodedDataLength"]))
        urls = {}
        cdp.on("Network.responseReceived", lambda e: urls.__setitem__(e["requestId"], e["response"]["url"]))
        pg.add_init_script("""(() => { const iv = setInterval(() => { try { if (S && S.job && !S.loading && S.rows && S.rows.length && document.querySelector('#body tr')) { window.__openDone = performance.now(); clearInterval(iv); } } catch (e) {} }, 10);
          try { new PerformanceObserver(l => { for (const e of l.getEntries()) window.__longTask = Math.max(window.__longTask || 0, Math.round(e.duration)); }).observe({type: 'longtask', buffered: true}); } catch (e) {} })()""")
        q = f"?pane={pane}" if pane else ""
        pg.goto(f"{base}/{q}#{JOB}")
        pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.rows && S.rows.length > 0", timeout=180000)
        pg.wait_for_timeout(1500)
        t = pg.evaluate("""() => {
          const nav = performance.getEntriesByType('navigation')[0];
          const rs = performance.getEntriesByType('resource').map(r => ({u: r.name.replace(location.origin,''), d: Math.round(r.duration), s: Math.round(r.startTime)}));
          return {ready: Math.round(window.__openDone || 0), rs, longest: window.__longTask || 0};
        }""")
        by = {}
        for rid, n in enc.items():
            u = urls.get(rid, "?").replace(base, "")
            by[u] = by.get(u, 0) + n
        t["bytes_total"] = sum(enc.values()); t["bytes_by"] = dict(sorted(by.items(), key=lambda kv: -kv[1])[:8])
        t["errors"] = errs
        res.append(t)
        print(i, "ready", t["ready"], "ms · bytes", t["bytes_total"], "· errors", len(errs), flush=True)
        ctx.close()
    br.close()
json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
