"""hotfix39 — 직전/현재 결과 전환 스위치를 **실제로 띄워서** 확인한다.

    python3 spike/ui_audit_revswitch.py <data_dir> <job_B> <out_dir>

① Rev.B 를 열면 오른쪽 위에 '이전 Rev.A · 현재 Rev.B' 스위치 ② '이전' 을 누르면 행 수·머리줄·
도면이 Rev.A 것으로 (같은 도면번호 장) ③ '현재' 로 돌아오면 서버 요청 없이(메모리) 빠르게
④ 다시 '이전' 도 메모리 ⑤ 페이지 오류 0.  시간을 잰다.
"""
from __future__ import annotations
import json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data, JOB, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
FOUND = []
def note(s): print(s, flush=True); FOUND.append(s)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(90):
        try: urllib.request.urlopen(f"http://127.0.0.1:{port}/home", timeout=2); break
        except Exception: time.sleep(1)
    rev = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/jobs/{JOB}/revision", timeout=60).read())
    prev = rev.get("previous_job_id"); note(f"서버 — previous_job_id {prev!r} · next_jobs {rev.get('next_jobs')}")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
        br = pw.chromium.launch(executable_path=exe if Path(exe).exists() else None)
        pg = br.new_page(viewport={"width": 1700, "height": 1000})
        errs = []; reqs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
        pg.on("request", lambda r: reqs.append(r.url))
        pg.goto(f"http://127.0.0.1:{port}/#{JOB}")
        pg.wait_for_function("() => window.S && S.job && !S.loading && S.pages && S.pages.length > 0", timeout=120000); pg.wait_for_timeout(1500)
        if errs: note("★ 열기 중 오류: " + errs[0][:300])
        sw = pg.inner_text("#rev-switch") if pg.query_selector("#rev-switch") else ""
        note(f"① 스위치: {sw!r} — {'맞음' if '이전' in sw and '현재' in sw else '★ 없음'}")
        pg.screenshot(path=str(OUT / "1_스위치.png"), clip={"x": 850, "y": 180, "width": 850, "height": 120})
        def state():
            return pg.evaluate("() => ({job: S.job.id, rows: S.rows.length, page: S.page && S.page.page_no, dwg: S.page && S.page.drawing_no, label: document.querySelector('#rev-label').textContent, grid: document.querySelectorAll('#grid tbody tr').length})")
        s0 = state(); note(f"현재: {s0}")
        pg.select_option("#page-select", "51"); pg.wait_for_timeout(2000); s0 = state()
        n0 = len(reqs); t = time.time(); pg.click("#rev-switch button.prev"); 
        pg.wait_for_function("() => S.job && S.job.id !== %r && !S.loading" % s0["job"], timeout=60000); pg.wait_for_timeout(1500)
        s1 = state(); dt1 = round((time.time() - t) * 1000)
        note(f"② 이전으로 (처음 읽음) — {dt1}ms · 요청 {len(reqs) - n0} · {s1} — {'맞음' if s1['job'] == prev and s1['dwg'] == s0['dwg'] else '★ 틀림'}")
        pg.screenshot(path=str(OUT / "2_이전결과.png"))
        n0 = len(reqs); t = time.time(); pg.click("#rev-switch button.cur"); pg.wait_for_timeout(1500)
        s2 = state(); dt2 = round((time.time() - t) * 1000); xhr = [u for u in reqs[n0:] if any(k in u for k in ("/rows", "/review", "/revision", "/pages", "/scope", "/unjudged", "/mode", "/legend"))]
        note(f"③-요청 {[u.split(str(port))[-1] for u in reqs[n0:]]}")
        note(f"③ 현재로 (메모리) — {dt2}ms · 결과 요청 {len(xhr)} · {s2} — {'맞음' if s2['job'] == JOB and s2['rows'] == s0['rows'] and s2['dwg'] == s0['dwg'] and not xhr else '★ 틀림'}")
        n0 = len(reqs); t = time.time(); pg.click("#rev-switch button.prev"); pg.wait_for_timeout(1500)
        s3 = state(); dt3 = round((time.time() - t) * 1000); xhr = [u for u in reqs[n0:] if any(k in u for k in ("/rows", "/review", "/revision", "/pages", "/scope", "/unjudged", "/mode", "/legend"))]
        note(f"④ 다시 이전으로 (메모리) — {dt3}ms · 결과 요청 {len(xhr)} · rows {s3['rows']} — {'맞음' if s3['job'] == prev and s3['rows'] == s1['rows'] and not xhr else '★ 틀림'}")
        note("⑤ 스위치 문구: " + repr(pg.inner_text("#rev-switch")))
        pg.screenshot(path=str(OUT / "3_다시이전_전환시간.png"), clip={"x": 850, "y": 180, "width": 850, "height": 120})
        note(f"⑥ 페이지 오류 {len(errs)}" + (" — " + errs[0][:200] if errs else ""))
        br.close()
finally:
    srv.terminate()
    (OUT / "README.md").write_text("# hotfix39 UI 자기검증 — 직전/현재 결과 전환\n\n" + "\n".join(f"- {s}" for s in FOUND) + "\n", encoding="utf-8")
