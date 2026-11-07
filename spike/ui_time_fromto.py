"""From/To 마크업이 왜 무거운가 — 한 번 긋는 동안 무엇이 얼마나 걸리는지 잰다 (hotfix27).

    python3 spike/ui_time_fromto.py RESULT.json PDF OUTDIR KEY FROM_BOX TO_BOX

FROM_BOX · TO_BOX 는 "x0,y0,x1,y1" (도면 좌표).  서버 요청마다 걸린 시간 · 화면이 다시 그려지는 시간 ·
사람이 누르는 횟수를 적는다.  ★ 실 DB 를 열지 않는다 — sha256 대조.
"""
from __future__ import annotations
import hashlib, json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
src = Path(sys.argv[1]); pdf = Path(sys.argv[2]); OUT = Path(sys.argv[3])
KEY = sys.argv[4]
FROM_BOX = [float(v) for v in sys.argv[5].split(",")]
TO_BOX = [float(v) for v in sys.argv[6].split(",")]
OUT.mkdir(parents=True, exist_ok=True)
FOUND: list[str] = []
REAL = ROOT / "app" / "_data" / "app.db"
real_before = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""


def note(s):
    print(s, flush=True); FOUND.append(s)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


blob = json.loads(src.read_text()); result = blob.get("result", blob)
from app import db, revisions                                    # noqa: E402
data = Path(tempfile.mkdtemp(prefix="timeft-"))
os.environ["PID_DATA_DIR"] = str(data)
con = db.connect(data / "app.db")
job = "timeft000001"
sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
revisions.create_project(data, "AUDIT")
con.execute("INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, created_at, status,"
            " progress, message, fingerprint, project, revision, input_kind)"
            " VALUES (?,?,?,?,?,'done',1.0,'',?,?,?,'PDF')",
            (job, pdf.name, sha, str(pdf.resolve()), time.time(),
             result.get("fingerprint", ""), "AUDIT", "A"))
con.commit(); db.store_result(con, job, result); con.commit(); con.close()
revisions.record_revision(data, "AUDIT", "A", job_id=job, pdf_name=pdf.name, compared_with="",
                          result={"counts": {}, "states": {}, "radii": {}, "deleted_candidates": []})

port = free_port()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                        "--port", str(port)], cwd=str(ROOT), env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    import urllib.request
    for _ in range(90):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/home", timeout=2); break
        except Exception:
            time.sleep(1)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
        br = pw.chromium.launch(executable_path=exe if Path(exe).exists() else None)
        pg = br.new_page(viewport={"width": 1366, "height": 768})
        errs, reqs = [], {}
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("request", lambda r: reqs.__setitem__(r, time.time()))

        def done(r):
            t0 = reqs.get(r.request)
            if t0 and ("/axis" in r.url or "/rows/" in r.url or "/history" in r.url):
                FOUND.append(f"   요청 {r.request.method} {r.url.split(str(port))[-1][:70]} {time.time() - t0:.2f}s")
                print(FOUND[-1], flush=True)
        pg.on("response", done)
        # 브라우저 안의 시각 — 놓기(pointerup)부터 요청 시작·끝까지 어디서 시간이 가는지
        pg.add_init_script("""(() => { window.__t = []; const f0 = window.fetch;
            window.fetch = async (...a) => { const u = String(a[0]); const t0 = performance.now();
              window.__t.push(['start ' + u.slice(-40), t0]); const r = await f0(...a);
              window.__t.push(['end ' + u.slice(-40), performance.now()]); return r; };
            window.addEventListener('pointerup', () => window.__t.push(['pointerup', performance.now()]), true);
          })();""")
        pg.goto(f"http://127.0.0.1:{port}/"); pg.wait_for_timeout(2500)
        pg.evaluate("() => document.querySelectorAll('details.pjt').forEach(d => d.open = true)")
        pg.query_selector("a.revrow").click(); pg.wait_for_timeout(9000)

        def centre_on(box):
            pg.evaluate("""(b) => { const st = document.querySelector('#stage');
                const cx = (b[0]+b[2])/2 / S.page.width * S.natural.w * S.zoom;
                const cy = (b[1]+b[3])/2 / S.page.height * S.natural.h * S.zoom;
                st.scrollTo({left: Math.max(0, cx - st.clientWidth/2), top: Math.max(0, cy - st.clientHeight/2), behavior: 'instant'}); }""", box)

        t = time.time()
        pg.evaluate(f"() => select('{KEY}', true)")
        pg.wait_for_selector("#dm-from", timeout=60000)
        NEW = bool(pg.query_selector("#dm-who"))
        if NEW:
            pg.fill("#dm-who", "검증")
        note(f"행 고르기 → From 버튼이 뜰 때까지 {time.time() - t:.2f}s")
        pg.wait_for_timeout(4000)
        note(f"   (4초 더 기다린 동안 끝난 요청은 위에)")

        def mark(side, box):
            pg.evaluate("() => window.scrollTo(0, 0)")
            pg.evaluate("() => { const l = document.querySelector('#ovlegend'); if (l) l.style.visibility = 'hidden'; }")
            t0 = time.time()
            pg.click(f"#dm-{side}")
            pg.wait_for_function("() => !!S.ftMark", timeout=20000)
            note(f"[{side}] 버튼 → 대기 상태 {time.time() - t0:.2f}s")
            pg.evaluate("() => window.scrollTo(0, 0)")
            centre_on(box); pg.wait_for_timeout(400)
            pt = pg.evaluate("""(b) => { const st = document.querySelector('#stage'); const sr = st.getBoundingClientRect();
                const fx = x => sr.left + x / S.page.width * S.natural.w * S.zoom - st.scrollLeft;
                const fy = y => sr.top + y / S.page.height * S.natural.h * S.zoom - st.scrollTop;
                return [fx(b[0]), fy(b[1]), fx(b[2]), fy(b[3])]; }""", box)
            pg.mouse.move(pt[0], pt[1]); pg.mouse.down()
            pg.mouse.move((pt[0] + pt[2]) / 2, (pt[1] + pt[3]) / 2, steps=4); pg.mouse.move(pt[2], pt[3], steps=4)
            t1 = time.time(); pg.mouse.up()
            # hotfix27 뒤에는 판 안의 작성자 칸이 채워져 있으면 이름 줄이 안 뜬다 —
            # 이름 줄이 뜨거나 Description 이 바뀌거나, 먼저 오는 쪽을 기다린다
            word = 'FROM' if side == 'from' else 'TO'
            pg.wait_for_function(f"() => !!document.querySelector('.author-bar input') || /{word}/.test((S.rows.find(x => x.key === '{KEY}') || {{values:{{}}}}).values.description || '')", timeout=60000)
            has_author = bool(pg.query_selector(".author-bar input"))
            if has_author:
                note(f"[{side}] 놓기 → 이름 묻는 줄 {time.time() - t1:.2f}s")
                t2 = time.time(); pg.click(".author-bar .ok")
            else:
                t2 = t1
            pg.wait_for_function(f"() => /{'FROM' if side == 'from' else 'TO'}/.test((S.rows.find(x => x.key === '{KEY}') || {{values:{{}}}}).values.description || '')", timeout=60000)
            note(f"[{side}] {'확인' if has_author else '놓기'} → Description 바뀜 {time.time() - t2:.2f}s")
            tl = pg.evaluate("() => { const t = window.__t; const i = t.map(x => x[0]).lastIndexOf('pointerup'); const b = t[i][1]; return t.slice(i).map(x => x[0] + ' +' + Math.round(x[1] - b) + 'ms'); }")
            note("   브라우저 시각: " + " · ".join(tl))
            pg.wait_for_selector("#dm-from", timeout=60000)
            note(f"[{side}] 끝 → 패널 다시 그려짐 {time.time() - t2:.2f}s · 누른 횟수 {'3 (버튼 · 끌기 · 확인)' if has_author else '2 (버튼 · 끌기)'}")
            pg.wait_for_timeout(3000)

        mark("from", FROM_BOX)
        mark("to", TO_BOX)
        if NEW:
            # 직접 입력 — 칸에 치고 Enter 한 번
            pg.fill("#dm-to-in", "TO HAND TYPED HEADER")
            t0 = time.time(); pg.press("#dm-to-in", "Enter")
            pg.wait_for_function(f"() => /HAND TYPED/.test(S.rows.find(x => x.key === '{KEY}').values.description || '')", timeout=60000)
            note(f"[직접 입력] Enter → Description 바뀜 {time.time() - t0:.2f}s · 누른 횟수 1 (Enter)")
            src = pg.evaluate(f"async () => (await (await fetch(`/jobs/${{S.job.id}}/rows/{KEY}/history`)).json()).history[0]")
            note(f"[직접 입력] 이력 맨 위: {src.get('reason')} · 작성자 {src.get('author')}")
            pg.wait_for_timeout(1500)
        note("Description: " + pg.evaluate(f"() => S.rows.find(x => x.key === '{KEY}').values.description"))
        pg.screenshot(path=str(OUT / "after_fromto.png"))
        note("페이지 오류: " + (" | ".join(errs) if errs else "없음"))
        br.close()
finally:
    srv.terminate()
real_after = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""
note(f"실 DB sha256 같음: {real_before == real_after}")
(OUT / "README.txt").write_text("\n".join(FOUND) + "\n", encoding="utf-8")
