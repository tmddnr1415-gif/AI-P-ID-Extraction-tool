"""LOGIC 화면 — 브라우저에서 사용자가 하는 일의 시간 · 긴 작업 · 받은 바이트 (L47).

    python3 spike/logic_ui_perf.py <job> <port> [--out <json>]   (서버는 사본 데이터로 미리 띄운다)

재는 것: 묶음 열기(결과 화면이 설 때까지) · 보기 모드 시트 옮기기 ×12 · 시뮬레이션 켜기 · 시뮬레이션 모드 시트 옮기기 ×12 ·
입력 하나 켜기(흐름 그림 끝까지) · 묶음 점검 · From-To 보고 · 정합성 검토 창 · 순차 동작 창 · 50ms 넘는 작업 수 · JS 힙 · 받은 바이트.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from playwright.sync_api import sync_playwright

CHROME = "/opt/pw-browsers/chromium"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job"); ap.add_argument("port"); ap.add_argument("--out", default="")
    ap.add_argument("--rounds", type=int, default=3)
    a = ap.parse_args()
    J, PORT = a.job, a.port
    res = {}
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME, args=["--js-flags=--expose-gc"])
        ctx = b.new_context(viewport={"width": 1600, "height": 950})
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errs.append(str(e)))
        got = {"bytes": 0, "n": 0}
        pg.on("response", lambda r: got.__setitem__("n", got["n"] + 1))
        pg.add_init_script("try{localStorage.setItem('logic.ftseen.%s','1');localStorage.setItem('logic.teachclosed.%s','1');localStorage.setItem('pid.author','홍길동')}catch(e){}" % (J, J))
        pg.add_init_script("window.__lt=[]; new PerformanceObserver(l=>{for(const e of l.getEntries()) window.__lt.push(Math.round(e.duration))}).observe({entryTypes:['longtask']});")

        def longtasks():
            return pg.evaluate("() => { const x=window.__lt.slice(); window.__lt=[]; return x; }")

        def heap():
            return pg.evaluate("() => (performance.memory ? Math.round(performance.memory.usedJSHeapSize/1e6) : -1)")

        def xfer():
            return pg.evaluate("() => performance.getEntriesByType('resource').reduce((a,e)=>a+(e.transferSize||0),0)")

        def mark(name, dt, extra=None):
            lt = longtasks()
            row = {"name": name, "ms": round(dt * 1000), "longtasks": len(lt), "longest": max(lt) if lt else 0, "heap_mb": heap()}
            if extra: row.update(extra)
            res.setdefault("rows", []).append(row)
            print(f"{name:40s} {row['ms']:7d} ms  long {row['longtasks']:3d} (max {row['longest']})  heap {row['heap_mb']} MB", *(f"{k}={v}" for k, v in (extra or {}).items()), flush=True)

        t = time.time()
        pg.goto(f"http://localhost:{PORT}/logic#job={J}")
        pg.wait_for_function("() => typeof L!=='undefined' && L.sheet && document.querySelector('#page').complete && document.querySelector('#page').naturalWidth>0", timeout=240000)
        mark("묶음 열기 (첫 시트가 설 때까지)", time.time() - t, {"kb": round(xfer() / 1024), "req": got["n"]})
        pg.wait_for_timeout(2500)
        mark("열고 2.5초 뒤 (뒤따르는 요청)", 0, {"kb": round(xfer() / 1024), "req": got["n"]})
        pages = pg.evaluate("() => L.sheets.map(s=>s.page)")
        start = pages[0]
        seq = pages[len(pages) // 3:: max(1, len(pages) // 36)][:12]

        def go(q, sim=False):
            t = time.time()
            pg.evaluate(f"() => {{ window.__sd=0; openSheet({q}); }}")
            pg.wait_for_function(f"() => L.sheet && L.sheet.page==={q} && document.querySelector('#page').complete && document.querySelector('#page').naturalWidth>0 && document.querySelector('#page').src.includes('/page/{q}.') && document.querySelector('#page').style.visibility!=='hidden'", timeout=60000)
            if sim:
                pg.wait_for_function("() => window.__sd>0", timeout=60000)
            return time.time() - t

        ts = [go(q) for q in seq]
        mark("보기 모드 시트 옮기기 ×12 (중앙값)", sorted(ts)[len(ts) // 2])
        ts = [go(q) for q in seq[:4]]
        mark("보기 모드 다시 ×4 (중앙값)", sorted(ts)[len(ts) // 2])
        # 시뮬레이션 켜기
        pg.evaluate("() => { const o=runSim; window.runSim=async function(a,b){ const r=await o(a,b); window.__sd=(window.__sd||0)+1; return r; }; }")
        t = time.time()
        pg.evaluate("() => { window.__sd=0; setMode('sim'); }")
        pg.wait_for_function("() => window.__sd>0", timeout=120000)
        mark("시뮬레이션 켜기", time.time() - t)
        ts = [go(q, True) for q in reversed(seq)]
        mark("시뮬 모드 시트 옮기기 ×12 (중앙값)", sorted(ts)[len(ts) // 2])
        # 입력 하나 켜기 — 입력 행이 있는 시트로
        go(seq[0], True)
        row = pg.evaluate("() => { const r=(L.sheet.rows||[]).find(r=>r.side==='L'&&r.net!=null); return r? r.n : null; }")
        if row is None:
            for q in seq[1:]:
                go(q, True)
                row = pg.evaluate("() => { const r=(L.sheet.rows||[]).find(r=>r.side==='L'&&r.net!=null); return r? r.n : null; }")
                if row is not None:
                    break
        for i in range(a.rounds):
            v = 1 if i % 2 == 0 else 0
            t = time.time()
            pg.evaluate(f"() => {{ window.__sd=0; setForce('row:{row}', {v}); }}")
            pg.wait_for_function("() => window.__sd>0", timeout=120000)
            pg.wait_for_function("() => Date.now() >= (L.animUntil||0)", timeout=120000)
            mark(f"입력 행 {row} = {v} (흐름 끝까지)", time.time() - t)
        # 신호 현황 · 패널들
        for name, js, wait in (
            ("묶음 점검 (renderAll)", "renderAll()", "() => true"),
            ("From-To 보고", f"showFromTo('{J}')", "() => document.querySelector('#ft') && !document.querySelector('#ft').hidden"),
            ("정합성 검토 창", "renderReview()", "() => RV.data"),
            ("순차 동작 창", "seqOpen && seqOpen()", "() => document.querySelector('#seq') && !document.querySelector('#seq').hidden"),
        ):
            t = time.time()
            try:
                pg.evaluate(f"() => {{ try {{ {js} }} catch(e) {{ window.__e=String(e) }} }}")
                pg.wait_for_function(wait, timeout=60000)
                mark(name, time.time() - t)
            except Exception as ex:
                print(name, "skip", str(ex)[:80])
        res["errors"] = errs
        res["kb_total"] = round(xfer() / 1024)
        print("errors", errs[:3], "total kb", res["kb_total"])
        b.close()
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
