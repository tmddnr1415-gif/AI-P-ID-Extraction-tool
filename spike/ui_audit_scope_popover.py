"""머리줄 펼침 판(출력 범위 · 적용 규칙 · 템플릿)이 화면 안에 서는가 (hotfix22).

    python3 spike/ui_audit_gutter.py out/regression_3p/UAD-DXF.json out/hotfix18/ui_gutter

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
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out/hotfix22/ui_scope")
OUT.mkdir(parents=True, exist_ok=True)
FOUND: list[str] = []
REAL = ROOT / "app" / "_data" / "app.db"
real_before = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""


def note(s):
    print(s, flush=True)
    FOUND.append(s)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


data = Path(tempfile.mkdtemp(prefix="scopeui-"))
os.environ["PID_DATA_DIR"] = str(data)
from app import db, revisions                                    # noqa: E402

blob = json.loads(src.read_text()); result = blob.get("result", blob)
con = db.connect(data / "app.db")
job = "scopeui00001"
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

        for w in (1700, 1280, 1000):
            pg.set_viewport_size({"width": w, "height": 900}); pg.wait_for_timeout(500)
            for did in ("scope", "rules", "tmpl"):
                pg.evaluate(f"() => document.querySelectorAll('details.scope').forEach(d => d.open = false)")
                pg.click(f"#{did} > summary"); pg.wait_for_timeout(400)
                r = pg.evaluate(f"() => {{ const b = document.querySelector('#{did} > .scope-body').getBoundingClientRect(); return [Math.round(b.left), Math.round(b.right), innerWidth]; }}")
                ok = r[0] >= 0 and r[1] <= r[2]
                note(f"폭 {w} · #{did} 판 left {r[0]} right {r[1]} (창 {r[2]}) → {'화면 안' if ok else '★ 잘림'}")
                if did == "scope":
                    pg.screenshot(path=str(OUT / f"scope_{w}.png"))
        note("페이지 오류: " + (" | ".join(errs) if errs else "없음"))
        br.close()
finally:
    srv.terminate()
real_after = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""
note(f"실 DB sha256 같음: {real_before == real_after}")
(OUT / "README.txt").write_text("\n".join(FOUND) + "\n", encoding="utf-8")
