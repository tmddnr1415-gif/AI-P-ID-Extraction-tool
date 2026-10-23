"""hotfix108 — 절전모드 화면 시뮬레이션: 서버를 **실제로 끄고 켜며** P&ID · LOGIC · 판넬이 이어지는지 본다.

    PID_SRC=/path/to/data-copy python3 spike/ui_audit_offline.py <out_dir>

단계: ① 서버 켜고 결과를 연 뒤 [절전 대비 보관] ② 서버를 끈다 → 새로 열어도 화면이 뜨고 띠가 '절전모드' 를 말한다 →
P&ID 칸 편집 · 행 삭제 · LOGIC 메모 · 타이머 · 판넬 저장이 보관된다 ③ 서버를 켠다 → 보관한 순서대로 되보내 서버에 덮어쓴다 →
서버 API 로 값을 확인한다.  실 데이터는 안 연다 (사본 폴더 · 버릴 포트)."""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "out" / "hotfix108" / "ui")
OUT.mkdir(parents=True, exist_ok=True)
PORT = int(os.environ.get("PORT", "8812"))
BASE = f"http://127.0.0.1:{PORT}"
DATA = Path(os.environ.get("PID_DATA", str(OUT.parent / "data")))
USER = "%ED%99%8D%EA%B8%B8%EB%8F%99"            # 홍길동
ENV = {**os.environ, "PID_DATA_DIR": str(DATA), "PID_LOGIC_WARM": "0", "PID_PAGE_WARM": "0", "PID_ROWS_WARM": "0",
       "PID_ANALYSIS_INPROCESS": "1", "PYTHONUNBUFFERED": "1"}
SRV = {"p": None}


def start():
    log = open(OUT / "server.log", "ab")
    SRV["p"] = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
                                cwd=ROOT, env=ENV, stdout=log, stderr=subprocess.STDOUT)
    for _ in range(300):
        try:
            urllib.request.urlopen(f"{BASE}/version", timeout=1).read(); return
        except Exception:
            time.sleep(0.2)
    raise SystemExit("server did not start")


def stop():
    p = SRV["p"]
    if not p: return
    p.send_signal(signal.SIGTERM)
    try: p.wait(15)
    except subprocess.TimeoutExpired: p.kill(); p.wait()
    SRV["p"] = None
    for _ in range(50):          # 포트가 정말 닫힐 때까지
        try: urllib.request.urlopen(f"{BASE}/version", timeout=0.5).read(); time.sleep(0.2)
        except Exception: break


def http(method, path, body=None, headers=None):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode() or "null")


def prepare_logic_job():
    """합성 Logic PDF 를 올려 묶음 하나를 만든다 (tests 의 make_pdf)."""
    sys.path.insert(0, str(ROOT / "tests"))
    from test_logic_review import make_pdf                 # noqa: E402
    pdf = OUT / "logic_sample.pdf"; make_pdf(pdf)
    boundary = "----pidoffline"
    data = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"up.pdf\"\r\nContent-Type: application/pdf\r\n\r\n").encode() \
        + pdf.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(f"{BASE}/logic/api/jobs", method="POST", data=data, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    job = json.loads(urllib.request.urlopen(req, timeout=60).read())["id"]
    for _ in range(600):
        st = http("GET", f"/logic/api/jobs/{job}")
        if st.get("state") == "done": return job
        if st.get("state") == "failed": raise SystemExit(f"logic analyse failed: {st}")
        time.sleep(0.3)
    raise SystemExit("logic analyse timeout")


async def main():
    from playwright.async_api import async_playwright
    src = Path(os.environ["PID_SRC"])
    if DATA.exists(): shutil.rmtree(DATA)
    shutil.copytree(src, DATA, ignore=shutil.ignore_patterns("page_cache", "backups"))
    start()
    res = {"errors": []}
    job = http("GET", "/home")["projects"][0]["revisions"][0]["job_id"] if http("GET", "/home").get("projects") else None
    if not job:
        job = [j for j in http("GET", "/jobs") if j.get("status") == "done"][0]["id"]
    res["pid_job"] = job
    ljob = prepare_logic_job(); res["logic_job"] = ljob
    lsheet = http("GET", f"/logic/api/jobs/{ljob}/sheets")["sheets"][0]
    sp = http("POST", "/space/api/projects", {"name": "OFFLINE TEST"}, {"X-Author": USER}); res["space_pid"] = sp["id"]
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        ctx = await b.new_context(viewport={"width": 1500, "height": 900})
        pg = await ctx.new_page()
        pg.on("pageerror", lambda e: res["errors"].append("pid:" + str(e)))

        # ── ① 서버 켜진 채: 결과를 열고 보관
        await pg.goto(f"{BASE}/?user={USER}")
        await pg.wait_for_selector("a.revrow", timeout=30000)
        await pg.click("a.revrow")
        await pg.wait_for_function("typeof S !== 'undefined' && S.job && S.rows && S.rows.length > 0", timeout=30000)
        await pg.wait_for_function("navigator.serviceWorker && navigator.serviceWorker.controller && OFFLINE.sw", timeout=30000)
        await pg.evaluate("OFFLINE.prefetch()")
        await pg.wait_for_function("OFFLINE.prefetching && OFFLINE.prefetching.finished", timeout=120000)
        res["prefetch_pid"] = await pg.evaluate("OFFLINE.prefetching")
        await pg.screenshot(path=str(OUT / "1_prefetched.png"))
        rows_before = await pg.evaluate("S.rows.filter(r => !r.removed && r.tab === 'FIELD').slice(0, 3).map(r => r.key)")
        res["rows_before"] = len(await pg.evaluate("S.rows"))
        # LOGIC 묶음도 열어 보관
        lp = await ctx.new_page(); lp.on("pageerror", lambda e: res["errors"].append("logic:" + str(e)))
        await lp.goto(f"{BASE}/logic?user={USER}#job={ljob}")
        await lp.wait_for_function("typeof L !== 'undefined' && L.job && L.sheet", timeout=60000)
        await lp.evaluate("OFFLINE.prefetch()")
        await lp.wait_for_function("OFFLINE.prefetching && OFFLINE.prefetching.finished", timeout=60000)
        res["prefetch_logic"] = await lp.evaluate("OFFLINE.prefetching")
        # 판넬도 한 번 연다 (화면 뼈대는 설치 때 담겼다 · 프로젝트 목록을 담는다)
        spg = await ctx.new_page(); spg.on("pageerror", lambda e: res["errors"].append("space:" + str(e)))
        await spg.goto(f"{BASE}/space?embed=1&user={USER}")
        await spg.wait_for_function("window.OFFLINE && OFFLINE.ready", timeout=30000)
        await spg.evaluate("OFFLINE.prefetch()")
        await spg.wait_for_function("OFFLINE.prefetching && OFFLINE.prefetching.finished", timeout=60000)
        res["sw_stats"] = await pg.evaluate("new Promise(r => { navigator.serviceWorker.addEventListener('message', e => { if (e.data && e.data.type === 'stats') r(e.data); }, { once: true }); OFFLINE.sw.postMessage({type:'stats'}); })")

        # ── ② 서버를 끈다
        stop()
        res["server_off_at"] = time.strftime("%H:%M:%S")
        # 새 탭으로 P&ID 를 처음부터 — 보관된 화면으로 떠야 한다
        pg2 = await ctx.new_page(); pg2.on("pageerror", lambda e: res["errors"].append("pid-off:" + str(e)))
        t0 = time.time()
        await pg2.goto(f"{BASE}/?user={USER}", wait_until="domcontentloaded", timeout=60000)
        await pg2.wait_for_selector("a.revrow", timeout=60000)
        res["offline_first_screen_s"] = round(time.time() - t0, 1)
        await pg2.wait_for_function("window.OFFLINE && OFFLINE.down", timeout=30000)
        await pg2.click("a.revrow")
        await pg2.wait_for_function("typeof S !== 'undefined' && S.job && S.rows && S.rows.length > 0", timeout=60000)
        try:
            await pg2.wait_for_function("document.querySelector('#sheet') && document.querySelector('#sheet').complete && document.querySelector('#sheet').naturalWidth > 0", timeout=30000)
            res["offline_sheet_png"] = True
        except Exception as e:                                   # 그림이 안 떴으면 왜인지 적고 계속 간다
            res["offline_sheet_png"] = False
            res["sheet_diag"] = await pg2.evaluate("""(async () => { const img = document.querySelector('#sheet');
                const keys = await caches.open('pid-offline-v1-pages').then(c => c.keys()).then(ks => ks.map(k => k.url));
                return { src: img && img.src, complete: img && img.complete, nat: img && img.naturalWidth, down: OFFLINE.down,
                         pending: typeof S !== 'undefined' && !!S.pending, page: typeof S !== 'undefined' && S.page && S.page.page_no,
                         cached_png: keys.slice(0, 5), n_png: keys.length }; })()""")
            (OUT / "diag.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        res["rows_offline"] = len(await pg2.evaluate("S.rows"))
        res["banner_offline"] = await pg2.inner_text("#offline-banner")
        await pg2.screenshot(path=str(OUT / "2_offline_result.png"))
        k1, k2 = rows_before[0], rows_before[1]
        # 칸 편집 (목록·도면과 같은 길 saveField) · 행 삭제 · O/X 평가 · 장 메모
        await pg2.evaluate(f"saveField(S.rowByKey['{k1}'], 'qty', '7')")
        await pg2.evaluate(f"deleteRows(['{k2}'], {{reason: '절전 시험', klass: 'FALSE_POSITIVE'}})")
        await pg2.wait_for_function("OFFLINE.queue.length >= 2", timeout=15000)
        res["offline_edit"] = {"qty_in_memory": await pg2.evaluate(f"S.rowByKey['{k1}'].user && S.rowByKey['{k1}'].user.qty"),
                               "removed_in_memory": await pg2.evaluate(f"S.rowByKey['{k2}'].removed"),
                               "grid_cell": await pg2.evaluate(f"(document.querySelector('tr[data-key=\"{k1}\"] td[data-col=qty]')||{{}}).textContent"),
                               "queue": await pg2.evaluate("OFFLINE.queue.map(q => q.method + ' ' + q.url)")}
        await pg2.evaluate("OFFLINE.render()")
        res["banner_queued"] = await pg2.inner_text("#offline-banner")
        await pg2.screenshot(path=str(OUT / "3_offline_edit.png"))
        # 서버가 켜져야 하는 일은 그 자리에서 거절한다
        res["refused"] = await pg2.evaluate("fetch(`/jobs/${S.job.id}/reanalyse`, {method:'POST'}).then(r => r.status + ' ' + r.headers.get('X-Offline'))")
        # LOGIC — 보관된 시트로 열리고 메모 · 타이머가 보관된다
        lp2 = await ctx.new_page(); lp2.on("pageerror", lambda e: res["errors"].append("logic-off:" + str(e)))
        await lp2.goto(f"{BASE}/logic?user={USER}#job={ljob}", wait_until="domcontentloaded", timeout=60000)
        await lp2.wait_for_function("typeof L !== 'undefined' && L.job && L.sheet", timeout=60000)
        await lp2.wait_for_function("window.OFFLINE && OFFLINE.down", timeout=30000)
        res["logic_offline_sheet"] = await lp2.evaluate("L.sheet && L.sheet.sheet_no")
        m = await lp2.evaluate(f"post('/logic/api/jobs/{ljob}/memo', {{page: {lsheet['page']}, sheet_no: '{lsheet.get('sheet_no','')}', text: '절전모드 메모', author: '홍길동'}})")
        res["logic_memo_synth"] = {k: m.get(k) for k in ("id", "text", "offline")}
        await lp2.evaluate(f"post('/logic/api/jobs/{ljob}/overrides/timer', {{page: {lsheet['page']}, block: 'B1', sec: 3, author: '홍길동'}})")
        await lp2.screenshot(path=str(OUT / "4_logic_offline.png"))
        # 판넬 — 보관된 화면으로 뜨고 저장이 보관된다
        sp2 = await ctx.new_page(); sp2.on("pageerror", lambda e: res["errors"].append("space-off:" + str(e)))
        await sp2.goto(f"{BASE}/space?embed=1&user={USER}", wait_until="domcontentloaded", timeout=60000)
        await sp2.wait_for_function("window.OFFLINE && OFFLINE.ready && document.querySelector('#hmProj')", timeout=30000)
        sv = await sp2.evaluate(f"""fetch('/space/api/{sp["id"]}/saves', {{method:'POST', headers:{{'Content-Type':'application/json','X-Author':'{USER}'}},
            body: JSON.stringify({{data: {{room: {{w: 21000, l: 18000, spare: 0}}, types: [], panels: [{{id:'p1'}}], info: {{rev: 'B'}}}}, memo: '절전 저장', sum: {{}}}})}}).then(r => r.json())""")
        res["space_save_synth"] = {k: sv.get(k) for k in ("id", "offline", "memo", "panels")}
        res["queue_total"] = await sp2.evaluate("OFFLINE.queue.length")
        await sp2.screenshot(path=str(OUT / "5_space_offline.png"))

        # ── ③ 서버를 켠다 → 되보냄
        start()
        res["server_on_at"] = time.strftime("%H:%M:%S")
        t1 = time.time()
        await pg2.wait_for_function("!OFFLINE.down && OFFLINE.queue.length === 0 && OFFLINE.lastReplay", timeout=90000)
        res["replay_s"] = round(time.time() - t1, 1)
        res["last_replay"] = await pg2.evaluate("OFFLINE.lastReplay")
        res["failed"] = await pg2.evaluate("OFFLINE.failed")
        res["banner_after"] = await pg2.inner_text("#offline-banner")
        await pg2.screenshot(path=str(OUT / "6_replayed.png"))
        # 서버 값 확인
        rows = http("GET", f"/jobs/{job}/rows?tab=ALL&keys={k1},{k2}")
        byk = {r["key"]: r for r in rows}
        res["server_after"] = {"qty": (byk.get(k1, {}).get("user") or {}).get("qty"), "removed": byk.get(k2, {}).get("removed"),
                               "logic_memo": [x["text"] for x in http("GET", f"/logic/api/jobs/{ljob}/memo")["items"]],
                               "logic_timer": http("GET", f"/logic/api/jobs/{ljob}/overrides").get("timers"),
                               "space_saves": [(s["id"], s["memo"]) for s in http("GET", f"/space/api/{sp['id']}")["saves"]]}
        res["ids_match"] = {"logic_memo": m.get("id") in [x["id"] for x in http("GET", f"/logic/api/jobs/{ljob}/memo")["items"]],
                            "space_save": sv.get("id") in [s[0] for s in res["server_after"]["space_saves"]]}
        await lp2.wait_for_function("!OFFLINE.down", timeout=30000)
        res["logic_memo_after_replay"] = await lp2.evaluate("(L.memos || []).map(m => m.text)")
        await b.close()
    stop()
    (OUT / "result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        stop()
