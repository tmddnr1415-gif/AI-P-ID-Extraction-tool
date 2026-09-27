"""Shift + 누르기가 도면을 **브라우저 선택**으로 파랗게 덮는지 띄워서 본다 (hotfix12).

    python3 spike/ui_audit_shift_select.py out/regression_3p/UAD-DXF.json out/round56/ui_shift [앱뿌리]

현장 캡처: Shift 를 누른 채 도면을 누르면 장 전체가 파랗게 덮여 검출 상자가 안
보였다.  우리 띠(`rect.band`)가 아니라 브라우저가 "선택 넓히기" 로 그림(#sheet)을
통째로 고른 것이다.  재는 것:
    ① 평범한 클릭 뒤 Shift + 클릭 → 브라우저 선택이 남는가 (rangeCount · #sheet 포함)
    ② Shift + 끌기(띠) → 브라우저 선택이 남는가 · 묶음은 서는가
    ③ 그리드 Shift + 클릭 → 표 글자가 긁히는가
세 번째 인자로 **옛 코드 뿌리**를 주면 같은 절차로 고치기 전을 잰다.
★ 실 DB 를 열지 않는다 — 끝에서 sha256 을 대조한다.
"""
from __future__ import annotations
import hashlib, json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
src = Path(sys.argv[1] if len(sys.argv) > 1 else "out/regression_3p/UAD-DXF.json")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out/round56/ui_shift")
APP = Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else ROOT
OUT.mkdir(parents=True, exist_ok=True)
FOUND: list[str] = []
REAL = ROOT / "app" / "_data" / "app.db"
real_before = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""


def note(s):
    print(s, flush=True); FOUND.append(s)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


data = Path(tempfile.mkdtemp(prefix="shiftui-"))
os.environ["PID_DATA_DIR"] = str(data)
from app import db, revisions                                    # noqa: E402

blob = json.loads(src.read_text()); result = blob.get("result", blob)
con = db.connect(data / "app.db")
job = "shiftsel0001"
pack = ROOT / "data" / "uad_dxf.zip"
sha = hashlib.sha256(pack.read_bytes()).hexdigest()
revisions.create_project(data, "UAD-DXF")
con.execute("INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, created_at, status,"
            " progress, message, fingerprint, project, revision, input_kind)"
            " VALUES (?,?,?,?,?,'done',1.0,'',?,?,?,'DXF')",
            (job, pack.name, sha, str(pack.resolve()), time.time(),
             result.get("fingerprint", ""), "UAD-DXF", "A"))
con.commit(); db.store_result(con, job, result); con.commit(); con.close()
revisions.record_revision(data, "UAD-DXF", "A", job_id=job, pdf_name=pack.name,
                          compared_with="", result={"counts": {}, "states": {}, "radii": {},
                                                    "deleted_candidates": []})

SEL_JS = """() => { const s = window.getSelection();
  const sheet = document.querySelector('#sheet');
  return {ranges: s ? s.rangeCount : 0, collapsed: s ? s.isCollapsed : true,
          sheet: !!(s && sheet && s.rangeCount && s.containsNode(sheet, true)),
          text: s ? s.toString().length : 0, multi: S.multi ? S.multi.size : 0}; }"""

port = free_port()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(APP))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app",
                        "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(APP), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
        pg.goto(f"http://127.0.0.1:{port}/")
        pg.wait_for_timeout(2500)
        pg.evaluate("() => document.querySelectorAll('details.pjt').forEach(d => d.open = true)")
        pg.wait_for_timeout(400)
        pg.query_selector("a.revrow").click()
        pg.wait_for_timeout(8000)
        pg.select_option("#page-select", "6")
        pg.wait_for_selector("rect.det", timeout=120000)
        pg.wait_for_timeout(1500)
        st = pg.query_selector("#stage").bounding_box()
        cx, cy = st["x"] + st["width"] * 0.55, st["y"] + st["height"] * 0.55
        # ① 평범한 클릭 → Shift + 클릭 (현장에서 한 그대로)
        pg.mouse.click(st["x"] + st["width"] * 0.3, st["y"] + st["height"] * 0.3)
        pg.wait_for_timeout(300)
        pg.keyboard.down("Shift")
        pg.mouse.click(cx, cy)
        pg.keyboard.up("Shift")
        pg.wait_for_timeout(600)
        a = pg.evaluate(SEL_JS)
        note(f"① 클릭 → Shift+클릭: 브라우저 선택 {a['ranges']}개 · 비었나 {a['collapsed']} · "
             f"그림 포함 {a['sheet']} · 선택 글자 {a['text']}")
        pg.screenshot(path=str(OUT / "1_shift_click.png"))
        # ② Shift + 끌기
        pg.evaluate("() => { window.getSelection().removeAllRanges(); S.multi.clear(); drawOverlay(); }")
        pg.keyboard.down("Shift")
        pg.mouse.move(st["x"] + st["width"] * 0.35, st["y"] + st["height"] * 0.2)
        pg.mouse.down()
        pg.mouse.move(st["x"] + st["width"] * 0.6, st["y"] + st["height"] * 0.5, steps=8)
        pg.mouse.move(st["x"] + st["width"] * 0.85, st["y"] + st["height"] * 0.85, steps=8)
        pg.mouse.up()
        pg.keyboard.up("Shift")
        pg.wait_for_timeout(800)
        b = pg.evaluate(SEL_JS)
        note(f"② Shift+끌기: 브라우저 선택 {b['ranges']}개 · 비었나 {b['collapsed']} · "
             f"그림 포함 {b['sheet']} · 묶음 {b['multi']}개")
        pg.screenshot(path=str(OUT / "2_shift_drag.png"))
        # ③ 그리드 Shift + 클릭
        rows = pg.query_selector_all("#grid tbody tr")
        if len(rows) >= 3:
            rows[0].click(); pg.wait_for_timeout(300)
            pg.keyboard.down("Shift"); rows[2].click(); pg.keyboard.up("Shift")
            pg.wait_for_timeout(500)
            c = pg.evaluate(SEL_JS)
            note(f"③ 그리드 Shift+클릭: 선택 글자 {c['text']} · 묶음 {c['multi']}개")
        note("콘솔 오류: " + (" | ".join(errs[:4]) if errs else "없음"))
        br.close()
finally:
    srv.terminate(); srv.wait(timeout=20)

real_after = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""
note(f"실 DB sha256 — 같은가: {real_before == real_after}")
(OUT / "README.md").write_text("# hotfix12 — Shift 누르기의 브라우저 선택 (화면 자기검증)\n\n"
                               + "\n".join("- " + s for s in FOUND) + "\n", encoding="utf-8")
print("→", OUT)
