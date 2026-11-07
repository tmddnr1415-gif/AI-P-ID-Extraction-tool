"""Description From/To 마크업 · 최종 저장을 실제로 띄워 눌러 본다 (hotfix23).

    python3 spike/ui_audit_desc_markup.py RESULT.json PDF OUTDIR

① 행 하나를 고르고 From 범위를 도면에 끌어 긋는다 → Description 이 `FROM … <TYPE>` 이 되는가
② To 범위를 긋는다 → `FROM … TO … <TYPE>` 이 되는가
③ 최종 저장을 누른다 → 첫 화면에 "최종 저장 · 이름" 이 보이는가

★ 실 DB 를 열지 않는다 (17회차 격리) — 끝에서 sha256 을 대조해 증명한다.
"""
from __future__ import annotations
import hashlib, json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
src = Path(sys.argv[1]); pdf = Path(sys.argv[2]); OUT = Path(sys.argv[3])
KEY = sys.argv[4] if len(sys.argv) > 4 else "eda6baea91937792"
FROM_BOX = [90, 535, 200, 565]            # AL NOUF1 p6 `FROM HRSG#12`
TO_BOX = [450, 690, 560, 720]             # AL NOUF1 p6 `TO HRSG#12 BD TANK`
OUT.mkdir(parents=True, exist_ok=True)
FOUND: list[str] = []
REAL = ROOT / "app" / "_data" / "app.db"
real_before = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""


def note(s):
    print(s, flush=True); FOUND.append(s)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


data = Path(tempfile.mkdtemp(prefix="descmk-"))
os.environ["PID_DATA_DIR"] = str(data)
from app import db, revisions                                    # noqa: E402

blob = json.loads(src.read_text()); result = blob.get("result", blob)
con = db.connect(data / "app.db")
job = "descmk000001"
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
        pg = br.new_page(viewport={"width": 1700, "height": 1000})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("request", lambda rq: note("  요청 " + rq.url.split(str(port))[-1] + " " + (rq.post_data or "")[:160]) if "axis" in rq.url else None)
        pg.goto(f"http://127.0.0.1:{port}/"); pg.wait_for_timeout(2500)
        pg.evaluate("() => document.querySelectorAll('details.pjt').forEach(d => d.open = true)")
        pg.query_selector("a.revrow").click(); pg.wait_for_timeout(8000)
        pg.evaluate(f"() => select('{KEY}', true)"); pg.wait_for_timeout(3000)
        note("고른 행: " + str(pg.evaluate(f"() => {{ const r = S.rows.find(x => x.key === '{KEY}'); return [r.page_no, r.values.type, r.values.description]; }}")))

        def drag(box):
            pt = pg.evaluate("""(b) => { const img = document.querySelector('#sheet'); const r = img.getBoundingClientRect();
                const fx = x => r.left + x / S.page.width * r.width, fy = y => r.top + y / S.page.height * r.height;
                return [fx(b[0]), fy(b[1]), fx(b[2]), fy(b[3])]; }""", box)
            pg.evaluate("""(b) => { const st = document.querySelector('#stage'); const sr = st.getBoundingClientRect();
                st.scrollLeft += ((b[0]+b[2])/2 - (sr.left + sr.width/2));
                st.scrollTop += ((b[1]+b[3])/2 - (sr.top + sr.height/2)); }""", pt)
            pg.wait_for_timeout(500)
            pt = pg.evaluate("""(b) => { const img = document.querySelector('#sheet'); const r = img.getBoundingClientRect();
                const fx = x => r.left + x / S.page.width * r.width, fy = y => r.top + y / S.page.height * r.height;
                return [fx(b[0]), fy(b[1]), fx(b[2]), fy(b[3])]; }""", box)
            note("  끌기 좌표 " + str([round(v) for v in pt]) + " · 그 자리 요소 " + str(pg.evaluate("(p) => { const e = document.elementFromPoint(p[0], p[1]); return e ? e.tagName + '#' + e.id + '.' + e.className : null; }", pt)) + " · 대기 " + str(pg.evaluate("() => S.ftMark")))
            pg.mouse.move(pt[0], pt[1]); pg.mouse.down()
            pg.mouse.move((pt[0] + pt[2]) / 2, (pt[1] + pt[3]) / 2, steps=5)
            pg.mouse.move(pt[2], pt[3], steps=5); pg.mouse.up()
            pg.wait_for_timeout(2500)

        def author(name):
            pg.wait_for_selector(".author-bar input", timeout=8000)
            pg.fill(".author-bar input", name); pg.click(".author-bar .ok"); pg.wait_for_timeout(2500)

        # ① From
        pg.click("#dm-from"); pg.wait_for_timeout(500)
        note("From 대기 안내: " + (pg.text_content("#dm-note") or ""))
        drag(FROM_BOX)
        pg.screenshot(path=str(OUT / "0_after_drag.png"))
        note("끈 뒤 대기: " + str(pg.evaluate("() => S.ftMark")) + " · 안내 " + str(pg.evaluate("() => [...document.querySelectorAll('.edit-note,.author-bar')].map(e => e.textContent)")))
        note("이름 묻는 줄의 안내: " + (pg.text_content(".author-bar .ab-hint", timeout=5000) or "(없음)"))
        author("감사자")
        d1 = pg.evaluate(f"() => S.rows.find(x => x.key === '{KEY}').values.description")
        note(f"① From 만 — Description: {d1}")
        pg.screenshot(path=str(OUT / "1_from.png"))
        # ② To
        pg.click("#dm-to"); pg.wait_for_timeout(500)
        drag(TO_BOX); author("감사자")
        d2 = pg.evaluate(f"() => S.rows.find(x => x.key === '{KEY}').values.description")
        note(f"② From+To — Description: {d2}")
        grid = pg.evaluate(f"() => [...document.querySelectorAll('#grid tbody tr')].map(tr => tr.textContent).filter(t => t.includes('HRSG#12 BD TANK')).length")
        note(f"   목록에 그 문장이 보이는 줄: {grid}")
        pg.screenshot(path=str(OUT / "2_from_to.png"))
        # ③ 최종 저장
        pg.click("#save-final"); author("감사자")
        note("저장 안내: " + (pg.text_content(".edit-note") or "(없음)"))
        pg.click("#to-home"); pg.wait_for_timeout(2500)
        head = pg.evaluate("() => [...document.querySelectorAll('details.pjt summary')].map(s => s.textContent).join(' | ')")
        rev = pg.evaluate("() => [...document.querySelectorAll('a.revrow')].map(s => s.textContent).join(' | ')")
        note(f"③ 첫 화면 프로젝트 줄: {head}")
        note(f"   리비전 줄: {rev}")
        pg.screenshot(path=str(OUT / "3_home.png"))
        # 새로 고쳐도 남는가 (DB)
        pg.reload(); pg.wait_for_timeout(2500)
        head2 = pg.evaluate("() => [...document.querySelectorAll('details.pjt summary')].map(s => s.textContent).join(' | ')")
        note(f"   새로 고친 뒤: {'최종 저장' in head2}")
        note("페이지 오류: " + (" | ".join(errs) if errs else "없음"))
        br.close()
finally:
    srv.terminate()
real_after = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""
note(f"실 DB sha256 같음: {real_before == real_after}")
(OUT / "README.txt").write_text("\n".join(FOUND) + "\n", encoding="utf-8")
