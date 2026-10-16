"""hotfix26 — 새 편의 기능을 실제로 눌러 본다 (1366×768).

    python3 spike/ui_audit_hotfix26.py RESULT.json PDF OUTDIR

  ① 범례 판 접기 — 접으면 요약 한 줄 · 새로 고쳐도 접힘 유지
  ② 정보 띠 — 기본 한 줄 · "자세히" 로 펼침 · 새로 고쳐도 유지
  ③ 근거 패널 손잡이 — 위로 끌면 패널이 커진다 · 두 번 누르면 원래대로
  ④ ↑ ↓ — 목록의 다음/앞 행이 골라진다 · 검색칸에 커서가 있으면 잡지 않는다
  ⑤ 첫 두 열 고정 — 옆으로 밀어도 도면번호 칸이 제자리
★ 실 DB 를 열지 않는다 — sha256 대조.
"""
from __future__ import annotations
import hashlib, json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
src = Path(sys.argv[1]); pdf = Path(sys.argv[2]); OUT = Path(sys.argv[3])
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
data = Path(tempfile.mkdtemp(prefix="audit26-"))
os.environ["PID_DATA_DIR"] = str(data)
con = db.connect(data / "app.db")
job = "audit2600001"
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
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))

        def open_result():
            pg.goto(f"http://127.0.0.1:{port}/"); pg.wait_for_timeout(2500)
            if not pg.is_visible("#stage"):
                pg.evaluate("() => document.querySelectorAll('details.pjt').forEach(d => d.open = true)")
                pg.query_selector("a.revrow").click()
            pg.wait_for_timeout(8000)

        open_result()
        # ① 범례 접기
        h0 = pg.evaluate("() => Math.round(document.querySelector('#ovlegend').getBoundingClientRect().height)")
        pg.click("#ovl-fold"); pg.wait_for_timeout(300)
        h1 = pg.evaluate("() => Math.round(document.querySelector('#ovlegend').getBoundingClientRect().height)")
        summ = pg.text_content("#ovl-sum")
        note(f"① 범례 판 높이 {h0} → 접힘 {h1} · 요약 “{summ.strip()}”")
        pg.screenshot(path=str(OUT / "1_legend_folded.png"), clip={"x": 0, "y": 150, "width": 690, "height": 618})
        pg.reload(); pg.wait_for_timeout(2500)
        if not pg.is_visible("#stage"):
            pg.evaluate("() => document.querySelectorAll('details.pjt').forEach(d => d.open = true)")
            pg.query_selector("a.revrow").click()
        pg.wait_for_timeout(7000)
        kept = pg.evaluate("() => document.querySelector('#ovlegend').classList.contains('folded')")
        note(f"   새로 고친 뒤 접힘 유지: {kept}")
        pg.click("#ovl-fold"); pg.wait_for_timeout(200)
        # ② 정보 띠
        b0 = pg.evaluate("() => { const b = document.querySelector('#infobars'); return [b.classList.contains('compact'), Math.round(b.getBoundingClientRect().height), document.querySelector('#infobars-toggle').textContent]; }")
        pg.click("#infobars-toggle"); pg.wait_for_timeout(300)
        b1 = pg.evaluate("() => { const b = document.querySelector('#infobars'); return [b.classList.contains('compact'), Math.round(b.getBoundingClientRect().height), document.querySelector('#infobars-toggle').textContent]; }")
        note(f"② 정보 띠 기본 한 줄 {b0} → 펼침 {b1}")
        pg.screenshot(path=str(OUT / "2_infobars_open.png"), clip={"x": 0, "y": 85, "width": 1366, "height": 130})
        pg.click("#infobars-toggle"); pg.wait_for_timeout(300)
        # ③ 근거 패널 손잡이
        first = pg.evaluate("() => document.querySelector('#body tr[data-key]').dataset.key")
        pg.evaluate(f"() => select('{first}', true)"); pg.wait_for_timeout(2500)
        e0 = pg.evaluate("() => Math.round(document.querySelector('#evidence').getBoundingClientRect().height)")
        g = pg.evaluate("() => { const r = document.querySelector('#gutter-r').getBoundingClientRect(); return [r.left + r.width/2, r.top + r.height/2]; }")
        pg.mouse.move(g[0], g[1]); pg.mouse.down(); pg.mouse.move(g[0], g[1] - 120, steps=6); pg.mouse.move(g[0], g[1] - 200, steps=6); pg.mouse.up()
        pg.wait_for_timeout(400)
        e1 = pg.evaluate("() => Math.round(document.querySelector('#evidence').getBoundingClientRect().height)")
        rows_vis = pg.evaluate("() => Math.round(document.querySelector('#gridwrap').getBoundingClientRect().height)")
        note(f"③ 근거 패널 높이 {e0} → 위로 200px 끈 뒤 {e1} (목록 창 {rows_vis})")
        pg.screenshot(path=str(OUT / "3_evidence_taller.png"))
        pg.dblclick("#gutter-r"); pg.wait_for_timeout(300)
        e2 = pg.evaluate("() => Math.round(document.querySelector('#evidence').getBoundingClientRect().height)")
        note(f"   두 번 누른 뒤 {e2}")
        # ④ 화살표
        pg.evaluate("() => document.activeElement && document.activeElement.blur()")
        k0 = pg.evaluate("() => S.sel")
        pg.keyboard.press("ArrowDown"); pg.wait_for_timeout(1500)
        k1 = pg.evaluate("() => S.sel")
        pg.keyboard.press("ArrowDown"); pg.wait_for_timeout(1500)
        k2 = pg.evaluate("() => S.sel")
        pg.keyboard.press("ArrowUp"); pg.wait_for_timeout(1500)
        k3 = pg.evaluate("() => S.sel")
        order = pg.evaluate("() => [...document.querySelectorAll('#body tr[data-key]')].slice(0, 4).map(tr => tr.dataset.key)")
        note(f"④ ↓↓↑ — {k0[:8]} → {k1[:8]} → {k2[:8]} → {k3[:8]} (목록 순서 {[k[:8] for k in order]})")
        pg.click("#filter"); pg.keyboard.press("ArrowDown"); pg.wait_for_timeout(500)
        note(f"   검색칸에서 ↓: 선택 그대로 {pg.evaluate('() => S.sel') == k3}")
        # ⑤ 고정 열
        pg.evaluate("() => { document.querySelector('#gridwrap').scrollLeft = 900; }"); pg.wait_for_timeout(300)
        pos = pg.evaluate("""() => { const tr = document.querySelector('#body tr[data-key]'); const g = document.querySelector('#gridwrap').getBoundingClientRect();
            return [1, 2, 3].map(i => Math.round(tr.children[i-1].getBoundingClientRect().left - g.left)); }""")
        note(f"⑤ 옆으로 900px 민 뒤 1·2·3열의 왼쪽 자리: {pos} (1·2열이 0 근처면 고정)")
        pg.screenshot(path=str(OUT / "5_sticky_cols.png"), clip={"x": 688, "y": 150, "width": 678, "height": 400})
        note("페이지 오류: " + (" | ".join(errs) if errs else "없음"))
        br.close()
finally:
    srv.terminate()
real_after = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""
note(f"실 DB sha256 같음: {real_before == real_after}")
(OUT / "README.txt").write_text("\n".join(FOUND) + "\n", encoding="utf-8")
