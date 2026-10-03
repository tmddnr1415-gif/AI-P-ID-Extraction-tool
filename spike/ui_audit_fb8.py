"""8차 피드백 화면 항목을 **실제로 눌러서** 확인한다 (53회차).

    python3 spike/ui_audit_fb8.py out/round53/after_B3.json out/round53/ui

확인하는 것 넷 — 코드가 도는 것과 화면이 그렇게 말하는 것은 다른 일이다:
    s1  분석/프로젝트를 지우면 **고르는 상자**에서도 사라지는가
    s3  그 장 NOTES 에서 읽은 **식별 값과 해석**이 보이는가
    s7  SCOPE 를 바꾸면 **색이 따라가는가** · VENDOR 이름을 고를 수 있는가
    s8  마크업 제안·행추가가 **얼마나 걸리는가** · 녹색 선/음영 · 추가 행으로 이동

★ 실 DB 를 열지 않는다 (17회차 격리).
"""
from __future__ import annotations
import hashlib, json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out/round53/ui")
OUT.mkdir(parents=True, exist_ok=True)
src = Path(sys.argv[1] if len(sys.argv) > 1 else "out/round53/after_B3.json")
FOUND: list[str] = []


def note(s):
    print(s, flush=True)
    FOUND.append(s)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


data = Path(tempfile.mkdtemp(prefix="fb8ui-"))
os.environ["PID_DATA_DIR"] = str(data)
from app import db, revisions                                    # noqa: E402

blob = json.loads(src.read_text()); result = blob.get("result", blob)
con = db.connect(data / "app.db")
job = "fb8audit0001"
pdf = ROOT / "data" / "pid_total.pdf"
sha = hashlib.sha256(pdf.read_bytes()).hexdigest() if pdf.exists() else ""
revisions.create_project(data, "AL NOUF1")
con.execute("INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, created_at, status,"
            " progress, message, fingerprint, project, revision)"
            " VALUES (?,?,?,?,?,'done',1.0,'',?,?,?)",
            (job, pdf.name, sha, str(pdf.resolve()), time.time(),
             result.get("fingerprint", ""), "AL NOUF1", "A"))
con.commit(); db.store_result(con, job, result); con.commit(); con.close()
# ★ 31회차 [9] 와 같은 픽스처 결함을 피한다 — `GET /home` 은 `job.project` 열이
# 아니라 **프로젝트 장부**를 읽는다.  열만 채우면 "묶이지 않은 분석" 으로 뜨고
# `a.revrow` 가 없어 결과 화면에 못 들어간다.
revisions.record_revision(data, "AL NOUF1", "A", job_id=job,
                          pdf_name=pdf.name, compared_with="",
                          result={"counts": {}, "states": {}, "radii": {},
                                  "deleted_candidates": []})

port = free_port()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app",
                        "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env,
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
        pg.on("console", lambda m: errs.append("console:" + m.text)
              if m.type == "error" else None)
        pg.goto(f"http://127.0.0.1:{port}/")
        pg.wait_for_timeout(2500)

        # ── s1 ────────────────────────────────────────────────────────────
        before = pg.eval_on_selector("#proj-pick", "el => el.options.length")
        pg.evaluate("""async () => {
            const fd = new FormData(); fd.append('name', 'ZZ 지울 프로젝트');
            await fetch('/projects', {method:'POST', body: fd});
        }""")
        pg.evaluate("() => loadProjects()")
        pg.wait_for_timeout(600)
        mid = pg.eval_on_selector("#proj-pick", "el => el.options.length")
        pg.evaluate("""async () => {
            const fd = new FormData();
            fd.append('confirm', 'ZZ 지울 프로젝트'); fd.append('author', '감사');
            await fetch('/projects/' + encodeURIComponent('ZZ 지울 프로젝트'),
                        {method:'DELETE', body: fd});
            await afterDelete();
        }""")
        pg.wait_for_timeout(900)
        after = pg.eval_on_selector("#proj-pick", "el => el.options.length")
        txt = pg.eval_on_selector("#proj-pick", "el => el.innerText")
        note(f"s1 고르는 상자 항목 {before} → 만든 뒤 {mid} → 지운 뒤 {after}"
             f" · 지운 이름이 남아 있나: {'ZZ 지울' in txt}")
        pg.screenshot(path=str(OUT / "s1_첫화면.png"))

        # 결과 화면으로 — `a.revrow` 하나뿐이다 (20회차 [12]).
        # `<details>` 가 접혀 있으면 눌러도 안 되므로 먼저 전부 편다.
        pg.evaluate("() => document.querySelectorAll('details.pjt')"
                    ".forEach(d => d.open = true)")
        pg.wait_for_timeout(400)
        rr = pg.query_selector("a.revrow")
        if rr is None:
            pg.screenshot(path=str(OUT / "0_첫화면_행없음.png"))
            note("★ 결과로 들어갈 행이 없다: " + pg.inner_text("#joblist")[:300])
            raise SystemExit(2)
        rr.click()
        pg.wait_for_timeout(8000)

        # ── s3 ────────────────────────────────────────────────────────────
        pg.select_option("#page-select", "6")
        pg.wait_for_timeout(2500)
        band = pg.query_selector("#notes-band")
        vis = band and band.is_visible()
        if vis:
            pg.evaluate("() => document.querySelector('#notes-band').open = true")
            pg.wait_for_timeout(300)
            note("s3 NOTES 띠: " + repr(band.inner_text()[:240]))
            band.screenshot(path=str(OUT / "s3_notes.png"))
        else:
            note("s3 ★ NOTES 띠가 안 보인다")

        # ── s7 ────────────────────────────────────────────────────────────
        key = pg.evaluate("""() => {
            const r = (S.rows||[]).find(r => r.page_no === 6 && (r.values.scope||'') === 'SCT');
            return r ? r.key : null; }""")
        if not key:
            note("s7 ★ p6 에 SCT 행이 없어 시험 못 함")
        else:
            pg.evaluate(f"() => select({json.dumps(key)}, false)")
            pg.wait_for_timeout(900)
            col0 = pg.evaluate(f"""() => {{
                const n = document.querySelector('rect.det[data-key={json.dumps(key)}]');
                return n ? n.getAttribute('stroke') : null; }}""")
            ed = pg.query_selector("#evidence .scopeed")
            if not ed:
                note("s7 ★ 근거 패널에 공급 주체 편집 자리가 없다")
            else:
                ed.screenshot(path=str(OUT / "s7_편집자리.png"))
                names = pg.eval_on_selector("#sc-name", "el => el.options.length")
                pg.query_selector("#evidence .scopeed button[data-sc='VENDOR']").click()
                pg.wait_for_timeout(500)
                ab = pg.query_selector(".author-bar")
                if ab:
                    ab.query_selector("input").fill("감사")
                    ab.query_selector("button.ok").click()
                pg.wait_for_timeout(1200)
                col1 = pg.evaluate(f"""() => {{
                    const n = document.querySelector('rect.det[data-key={json.dumps(key)}]');
                    return n ? n.getAttribute('stroke') : null; }}""")
                note(f"s7 VENDOR 후보 {names-2}종 · 상자 색 {col0} → {col1}"
                     f" · 바뀌었나: {col0 != col1}")
                pg.screenshot(path=str(OUT / "s7_색변경.png"))

        # ── s8 ────────────────────────────────────────────────────────────
        # 마크업을 실제로 켜서 미리 읽기가 도는지 본다 (53회차 [G])
        tw0 = time.time()
        pg.click("#markup-toggle")
        pg.wait_for_timeout(300)
        note("s8 마크업 켠 직후 안내: "
             + repr(pg.inner_text("#markup-note")[:60]))
        for _ in range(60):
            if not pg.inner_text("#markup-note").startswith("도면을 읽는 중"):
                break
            pg.wait_for_timeout(500)
        note("s8 미리 읽기 %.1f초" % (time.time() - tw0))
        t = pg.evaluate("""async () => {
            const t0 = performance.now();
            const r = await fetch(`/jobs/${S.job.id}/markup/propose`, {
              method:'POST', headers:{'Content-Type':'application/json'},
              body: JSON.stringify({page_no: 6, rect: [300, 300, 360, 330]})});
            const a = performance.now() - t0;
            const t1 = performance.now();
            await fetch(`/jobs/${S.job.id}/markup/propose`, {
              method:'POST', headers:{'Content-Type':'application/json'},
              body: JSON.stringify({page_no: 6, rect: [400, 400, 460, 430]})});
            return {first: Math.round(a), second: Math.round(performance.now() - t1)};
        }""")
        note(f"s8 제안 1회 {t['first']}ms · 같은 장 2회째 {t['second']}ms")
        added = pg.evaluate("""async () => {
            const t0 = performance.now();
            const r = await fetch(`/jobs/${S.job.id}/rows`, {
              method:'POST', headers:{'Content-Type':'application/json'},
              body: JSON.stringify({page_no: 6, tab: 'FIELD', drawing_no: '',
                rect: [500, 500, 560, 530], values: {type: 'PIT', scope: 'SCT'},
                author: '감사', reason_class: 'MISSING'})});
            const ms = Math.round(performance.now() - t0);
            const out = await r.json();
            await refreshRows(out.key, {toGrid: true});
            return {ms, key: out.key};
        }""")
        pg.wait_for_timeout(1200)
        vis2 = pg.evaluate(f"""() => {{
            const tr = document.querySelector(`#body tr[data-key="${{CSS.escape({json.dumps(added['key'])})}}"]`);
            if (!tr) return {{row: false}};
            const rect = tr.getBoundingClientRect();
            const box = document.querySelector('#body').getBoundingClientRect();
            const n = document.querySelector('rect.det[data-key={json.dumps(added['key'])}]');
            return {{row: true, added: tr.classList.contains('added'),
                    bg: getComputedStyle(tr).backgroundColor,
                    inview: rect.top > box.top - 40 && rect.bottom < box.bottom + 40,
                    stroke: n ? n.getAttribute('stroke') : null}};
        }}""")
        note(f"s8 행추가 {added['ms']}ms · {vis2}")
        pg.screenshot(path=str(OUT / "s8_추가후.png"))
        leg = pg.query_selector("#ovl-items")
        if leg:
            leg.screenshot(path=str(OUT / "s8_범례.png"))
            note("s8 범례: " + repr(leg.inner_text()[:200]))
        if errs:
            note("★ 화면 오류: " + " | ".join(errs[:5]))
        else:
            note("화면 오류 없음")
        br.close()
finally:
    srv.terminate(); srv.wait(timeout=10)

(OUT / "README.md").write_text(
    "# 8차 피드백 화면 자기검증 (53회차)\n\n"
    + "\n".join("- " + x for x in FOUND) + "\n", encoding="utf-8")
print("\n=> " + str(OUT / "README.md"))
