"""hotfix33 — 장 도면번호 지정 판을 **실제로 눌러서** 확인한다.

    python3 spike/ui_audit_sheetno.py out/regression_3p/AL_NOUF1.json out/hotfix33/ui

AL NOUF1 은 빈 도면번호 칸이 0개라(45회차 실측) 이 판이 뜨지 않는다.  그래서 저장된
결과의 **두 장(p16·p17)의 `drawing_no` 를 비워** 픽스처를 만든다 — 판이 보는 것은
`engine_json.pages` 의 그 칸이고, 그 장의 그림은 PDF 에서 그대로 온다.

확인하는 것: ① 판이 뜨고 못 읽은 장만 센다 ② 보기 → 그 장으로 간다 ③ 지정 → 작성자
→ 파일에 적힌다 · 판이 "다시 분석하면" 을 상주로 말한다 ④ 되돌리기 → 파일에서 사라진다.
★ 실 DB 를 열지 않는다 (17회차 격리).
"""
from __future__ import annotations
import hashlib, json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out/hotfix33/ui")
OUT.mkdir(parents=True, exist_ok=True)
src = Path(sys.argv[1] if len(sys.argv) > 1 else "out/regression_3p/AL_NOUF1.json")
FOUND: list[str] = []
BLANK = (16, 17)


def note(s):
    print(s, flush=True); FOUND.append(s)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


data = Path(tempfile.mkdtemp(prefix="sheetui-"))
os.environ["PID_DATA_DIR"] = str(data)
from app import db, revisions, sheet_numbers                     # noqa: E402

blob = json.loads(src.read_text()); result = blob.get("result", blob)
for p in result["pages"]:
    if p["page_no"] in BLANK:
        p["drawing_no"] = ""; p["page_kind"] = "UNKNOWN"
con = db.connect(data / "app.db")
job = "sheetaudit01"
pdf = ROOT / "data" / "pid_total.pdf"
sha = hashlib.sha256(pdf.read_bytes()).hexdigest() if pdf.exists() else ""
revisions.create_project(data, "AL NOUF1")
con.execute("INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, created_at, status,"
            " progress, message, fingerprint, project, revision)"
            " VALUES (?,?,?,?,?,'done',1.0,'',?,?,?)",
            (job, pdf.name, sha, str(pdf.resolve()), time.time(),
             result.get("fingerprint", ""), "AL NOUF1", "A"))
con.commit(); db.store_result(con, job, result); con.commit(); con.close()
revisions.record_revision(data, "AL NOUF1", "A", job_id=job, pdf_name=pdf.name, compared_with="",
                          result={"counts": {}, "states": {}, "radii": {}, "deleted_candidates": []})
sfile = sheet_numbers.path_for(data, "AL NOUF1")

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
        pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
        pg.goto(f"http://127.0.0.1:{port}/"); pg.wait_for_timeout(2500)
        pg.evaluate("() => document.querySelectorAll('details.pjt').forEach(d => d.open = true)")
        pg.wait_for_timeout(400)
        rr = pg.query_selector("a.revrow")
        if rr is None:
            note("★ 결과로 들어갈 행이 없다"); raise SystemExit(2)
        rr.click(); pg.wait_for_timeout(8000)

        # ① 판이 뜨고 못 읽은 장만 센다
        panel = pg.query_selector("#sheet-panel")
        vis = pg.evaluate("() => !document.querySelector('#sheet-panel').classList.contains('hidden')")
        pages = pg.evaluate("() => [...document.querySelectorAll('#sheet-panel .sgroup')].map(e => +e.dataset.page)")
        head = pg.inner_text("#sheet-panel .mtop") if vis else ""
        note(f"① 판 보임 {vis} · 장 {pages} (픽스처 {list(BLANK)}) · 머리줄 {head!r}")
        pg.evaluate("() => document.querySelector('#sheet-panel').scrollIntoView()")
        panel.screenshot(path=str(OUT / "1_판.png"))

        # ② 보기 → 그 장으로
        pg.click(f'#sheet-panel .sgroup[data-page="{BLANK[0]}"] .sview'); pg.wait_for_timeout(2500)
        sel = pg.evaluate("() => document.querySelector('#page-select').value")
        pnote = pg.inner_text("#page-note")
        note(f"② 보기 → page-select {sel!r} · 장 안내 {pnote!r}")
        pg.screenshot(path=str(OUT / "2_보기.png"))

        # ③ 지정 → 작성자 → 파일
        val = "D00P-10LBG10-M05-9901"
        grp = f'#sheet-panel .sgroup[data-page="{BLANK[0]}"]'
        pg.fill(f"{grp} .sval", val); pg.fill(f"{grp} .mnote", "자기검증")
        pg.click(f"{grp} .sset-btn"); pg.wait_for_timeout(500)
        ab = pg.query_selector(".author-bar")
        if not ab:
            note("③ ★ 작성자 확인 줄이 안 뜬다"); raise SystemExit(3)
        ab.screenshot(path=str(OUT / "3_작성자.png"))
        ab.query_selector("input").fill("감사"); ab.query_selector("button.ok").click()
        pg.wait_for_timeout(1500)
        saved = json.loads(sfile.read_text(encoding="utf-8")) if sfile.exists() else {}
        rec = (saved.get("sheets") or {}).get(str(BLANK[0]))
        txt = pg.inner_text(grp)
        note(f"③ 파일 {sfile.name} 의 p{BLANK[0]}: {rec and {k: rec[k] for k in ('drawing_no','author','note')}} · "
             f"판에 '지정됨' {'지정됨' in txt} · '다시 분석하면' 상주 {'다시 분석하면' in txt}")
        head2 = pg.inner_text("#sheet-panel .mtop")
        note(f"③ 머리줄 {head2!r}")
        pg.query_selector("#sheet-panel").screenshot(path=str(OUT / "3_지정뒤.png"))
        # 서버 쪽 — 다음 분석이 받을 표
        tbl = sheet_numbers.table(data, "AL NOUF1")
        note(f"③ 다음 분석이 받을 표 table(): {tbl}")

        # ④ 되돌리기
        pg.click(f"{grp} .mclear"); pg.wait_for_timeout(1200)
        saved = json.loads(sfile.read_text(encoding="utf-8")) if sfile.exists() else {}
        note(f"④ 되돌린 뒤 파일의 sheets: {saved.get('sheets')} · table(): {sheet_numbers.table(data, 'AL NOUF1')}")
        pg.query_selector("#sheet-panel").screenshot(path=str(OUT / "4_되돌린뒤.png"))
        note("화면 오류 없음" if not errs else "★ 화면 오류: " + " | ".join(errs[:5]))
        br.close()
except Exception as exc:                                     # noqa: BLE001
    note(f"★ 중단: {type(exc).__name__}: {str(exc)[:300]}")
finally:
    srv.terminate(); srv.wait(timeout=10)

(OUT / "README.md").write_text("# hotfix33 화면 자기검증 — 장 도면번호 지정 판\n\n"
                               + "\n".join("- " + x for x in FOUND) + "\n", encoding="utf-8")
print("\n=> " + str(OUT / "README.md"))
