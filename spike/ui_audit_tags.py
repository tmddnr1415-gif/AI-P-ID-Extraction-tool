"""hotfix39 — 태그 문법 띠 · 태그가 증거인 행 · 교차 검증을 **실제로 띄워서** 확인한다.

    python3 spike/ui_audit_tags.py out/regression_3p/QFE.json data/QFE_260326.pdf out/hotfix39/ui

확인하는 것: ① 그리드 머리글에 Type · Tag No. · Line No. 가 **그 순서**로 있는가
② 그 장의 행 중 line_no 가 있는 행의 칸에 그 글자가 보이는가 ③ 행을 누르면 근거 패널이
`Line No. 근거` 를 적는가 ④ 페이지 오류 0.  ★ 실 DB 를 열지 않는다 (17회차 격리).
"""
from __future__ import annotations
import hashlib, json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
src = Path(sys.argv[1]); pdf = Path(sys.argv[2]); OUT = Path(sys.argv[3]); PAGE = sys.argv[4] if len(sys.argv) > 4 else "46"
OUT.mkdir(parents=True, exist_ok=True)
FOUND: list[str] = []


def note(s):
    print(s, flush=True); FOUND.append(s)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


data = Path(tempfile.mkdtemp(prefix="linenoui-"))
os.environ["PID_DATA_DIR"] = str(data)
from app import db, revisions                                    # noqa: E402

blob = json.loads(src.read_text()); result = blob.get("result", blob)
con = db.connect(data / "app.db")
job = "lineaudit001"
sha = hashlib.sha256(pdf.read_bytes()).hexdigest() if pdf.exists() else ""
revisions.create_project(data, "QFE")
con.execute("INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, created_at, status,"
            " progress, message, fingerprint, project, revision)"
            " VALUES (?,?,?,?,?,'done',1.0,'',?,?,?)",
            (job, pdf.name, sha, str(pdf.resolve()), time.time(), result.get("fingerprint", ""), "QFE", "A"))
con.commit(); db.store_result(con, job, result); con.commit(); con.close()
revisions.record_revision(data, "QFE", "A", job_id=job, pdf_name=pdf.name, compared_with="",
                          result={"counts": {}, "states": {}, "radii": {}, "deleted_candidates": []})
port = free_port()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
        pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
        pg.goto(f"http://127.0.0.1:{port}/"); pg.wait_for_timeout(2500)
        pg.evaluate("() => document.querySelectorAll('details.pjt').forEach(d => d.open = true)")
        pg.wait_for_timeout(400)
        rr = pg.query_selector("a.revrow")
        if rr is None:
            pg.screenshot(path=str(OUT / "0_첫화면_행없음.png")); note("★ 결과로 들어갈 행이 없다"); raise SystemExit(2)
        rr.click(); pg.wait_for_timeout(8000)
        # hotfix39 — ① 모드 띠에 태그 문법 한 줄 ② 검토 사유 TAG_EVIDENCE_ROW / TAG_TYPE_MISMATCH 행이
        # 목록에 서고 ③ 그 행을 누르면 근거 패널이 '태그가 증거' / '태그 교차 검증' 을 적는다
        bar = pg.inner_text("#mode-bar") if pg.query_selector("#mode-bar") else ""
        note("① 모드 띠: " + repr(bar[:200]) + (" — 맞음" if "태그 문법" in bar and "어긋남" in bar else " — ★ 태그 문법 줄 없음"))
        rows_srv = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/jobs/{job}/rows?tab=ALL", timeout=300).read())
        ev_rows = [r for r in rows_srv if "TAG_EVIDENCE_ROW" in (r.get("needs_review") or "")]
        mm_rows = [r for r in rows_srv if "TAG_TYPE_MISMATCH" in (r.get("needs_review") or "")]
        note(f"② 서버 — 태그가 증거인 행 {len(ev_rows)} · 어긋남 행 {len(mm_rows)} · 예 {[(r['page_no'], r['values'].get('type'), r['values'].get('tag_no')) for r in ev_rows[:3]]}")
        for kind, rr in (("태그가 증거", ev_rows), ("태그 교차 검증", mm_rows)):
            if not rr:
                note(f"③ {kind}: 행 없음"); continue
            r = rr[0]
            pg.select_option("#page-select", str(r["page_no"])); pg.wait_for_timeout(2500)
            pg.evaluate(f"() => select({json.dumps(r['key'])}, false)"); pg.wait_for_timeout(800)
            panel = pg.inner_text("#evidence")
            has = kind in panel
            cell = pg.evaluate(f"""() => {{ const tr = document.querySelector('#grid tbody tr[data-key="{r['key']}"]'); return tr ? [(tr.querySelector('td[data-col=type]')||{{}}).textContent, (tr.querySelector('td[data-col=tag_no]')||{{}}).textContent] : null; }}""")
            note(f"③ {kind} — p{r['page_no']} {r['values'].get('type')} {r['values'].get('tag_no')} · 목록 칸 {cell} · 근거 패널 {'있음' if has else '★ 없음'} — "
                 + repr([l for l in panel.splitlines() if kind in l or '태그' in l][:3]))
            pg.screenshot(path=str(OUT / f"3_{kind}_p{r['page_no']}.png"))
            ev = pg.query_selector("#evidence")
            if ev: ev.screenshot(path=str(OUT / f"4_{kind}_근거패널.png"))
        note(f"④ 페이지 오류 {len(errs)}" + (" — " + errs[0][:200] if errs else ""))
        br.close()
finally:
    srv.terminate()
    (OUT / "README.md").write_text("# hotfix39 UI 자기검증 — 태그 문법 · 태그가 증거인 행 · 교차 검증\n\n" + "\n".join(f"- {s}" for s in FOUND) + "\n", encoding="utf-8")
