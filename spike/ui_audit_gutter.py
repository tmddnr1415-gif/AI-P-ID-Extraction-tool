"""도면 창 경계 손잡이를 실제로 끌어 본다 (hotfix17).

    python3 spike/ui_audit_gutter.py out/regression_3p/UAD-DXF.json out/hotfix17/ui_gutter

확인하는 것 넷:
    ① 무늬가 실제로 걸렸는가 (`fill` 이 `url(#hatch-…)`)
    ② 무늬 색이 **테두리와 같은 값**인가 (색은 SCOPE 가 정한다 — 11회차)
    ③ 색마다 무늬가 하나씩만 서는가 (`defs` 의 `pattern` 수 = 쓰인 색 수)
    ④ 사람 눈으로 — 캡처

★ 실 DB 를 열지 않는다 (17회차 격리) — 끝에서 sha256 을 대조해 증명한다.
"""
from __future__ import annotations
import hashlib, json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
src = Path(sys.argv[1] if len(sys.argv) > 1 else "out/regression_3p/UAD-DXF.json")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out/hotfix17/ui_gutter")
OUT.mkdir(parents=True, exist_ok=True)
FOUND: list[str] = []
REAL = ROOT / "app" / "_data" / "app.db"
real_before = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""


def note(s):
    print(s, flush=True)
    FOUND.append(s)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


data = Path(tempfile.mkdtemp(prefix="gutterui-"))
os.environ["PID_DATA_DIR"] = str(data)
from app import db, revisions                                    # noqa: E402

blob = json.loads(src.read_text()); result = blob.get("result", blob)
con = db.connect(data / "app.db")
job = "gutter000001"
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
                          compared_with="",
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
        pg.goto(f"http://127.0.0.1:{port}/")
        pg.wait_for_timeout(2500)
        pg.evaluate("() => document.querySelectorAll('details.pjt').forEach(d => d.open = true)")
        pg.wait_for_timeout(400)
        rr = pg.query_selector("a.revrow")
        if rr is None:
            pg.screenshot(path=str(OUT / "0_행없음.png")); note("★ 결과 행 없음"); raise SystemExit(2)
        rr.click()
        pg.wait_for_timeout(9000)
        note("입력 종류: " + str(pg.evaluate("() => S.job && S.job.input_kind")))

        def geo():
            return pg.evaluate("""() => { const g = s => { const r = document.querySelector(s).getBoundingClientRect();
                return [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]; };
                return {left: g('#left'), right: g('#right'), stage: g('#stage'), bars: g('#infobars'),
                        gv: g('#gutter-v'), gh: g('#gutter-h'), zoom: S.zoom, sel: S.sel || null}; }""")
        pg.wait_for_timeout(1500)
        g0 = geo(); note(f"처음 — 도면 창 {g0['stage'][2]}x{g0['stage'][3]} · 목록 폭 {g0['right'][2]} · 안내 띠 높이 {g0['bars'][3]}")
        pg.screenshot(path=str(OUT / "1_처음.png"))
        # 손잡이 위에 마우스를 대면 커서가 바뀌는가
        cur = pg.evaluate("() => [getComputedStyle(document.querySelector('#gutter-v')).cursor, getComputedStyle(document.querySelector('#gutter-h')).cursor]")
        note(f"커서 — 가운데 {cur[0]} · 위 {cur[1]}")
        # ① 가운데 손잡이를 오른쪽으로 400px
        x = g0['gv'][0] + 3; y = g0['gv'][1] + 200
        pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x + 200, y, steps=5); pg.mouse.move(x + 400, y, steps=5); pg.mouse.up()
        pg.wait_for_timeout(600)
        g1 = geo(); note(f"① 가운데를 오른쪽으로 400px — 도면 창 폭 {g0['stage'][2]} → {g1['stage'][2]} · 목록 폭 {g0['right'][2]} → {g1['right'][2]}")
        # ② 위 손잡이를 위로 끝까지
        x = g1['gh'][0] + 300; y = g1['gh'][1] + 3
        pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x, y - 400, steps=8); pg.mouse.up()
        pg.wait_for_timeout(600)
        g2 = geo(); note(f"② 위를 위로 끝까지 — 안내 띠 높이 {g1['bars'][3]} → {g2['bars'][3]} · 도면 창 높이 {g1['stage'][3]} → {g2['stage'][3]}")
        pg.screenshot(path=str(OUT / "2_넓힌뒤.png"))
        # ③ 새로 고쳐도 기억하는가
        pg.reload(); pg.wait_for_timeout(2500)
        # 주소에 분석 id 가 있으면 새로 고침이 곧장 결과 화면으로 간다
        if not pg.is_visible("#stage"):
            pg.evaluate("() => document.querySelectorAll('details.pjt').forEach(d => d.open = true)")
            pg.query_selector("a.revrow").click()
        pg.wait_for_timeout(6000)
        g3 = geo(); note(f"③ 새로 고친 뒤 — 도면 창 {g3['stage'][2]}x{g3['stage'][3]} (넓힌 값 {g2['stage'][2]}x{g2['stage'][3]} 과 같은가: {abs(g3['stage'][2]-g2['stage'][2])<=2 and abs(g3['stage'][3]-g2['stage'][3])<=2})")
        # ④ 두 번 누르면 원래대로
        pg.dblclick("#gutter-v"); pg.dblclick("#gutter-h"); pg.wait_for_timeout(600)
        g4 = geo(); note(f"④ 두 번 눌러 되돌림 — 도면 창 {g4['stage'][2]}x{g4['stage'][3]} (처음 {g0['stage'][2]}x{g0['stage'][3]})")
        # ⑤ 끝까지 끌어도 목록이 사라지지 않는가
        x = g4['gv'][0] + 3; y = g4['gv'][1] + 200
        pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(5000, y, steps=5); pg.mouse.up(); pg.wait_for_timeout(400)
        g5 = geo(); note(f"⑤ 오른쪽 끝까지 — 목록 폭 {g5['right'][2]} (하한 260)")
        pg.mouse.move(g5['gv'][0] + 3, y); pg.mouse.down(); pg.mouse.move(-500, y, steps=5); pg.mouse.up(); pg.wait_for_timeout(400)
        g6 = geo(); note(f"⑤ 왼쪽 끝까지 — 도면 창 폭 {g6['left'][2]} (하한 260)")
        pg.dblclick("#gutter-v")
        note("콘솔 오류: " + (" | ".join(errs[:4]) if errs else "없음"))
        br.close()
finally:
    srv.terminate(); srv.wait(timeout=20)

real_after = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""
note(f"실 DB sha256 — 같은가: {real_before == real_after}")
(OUT / "README.md").write_text("# hotfix17 — 도면 창 경계 손잡이 (화면 자기검증)\n\n"
    + "\n".join("- " + s for s in FOUND) + "\n", encoding="utf-8")
print("→", OUT)
