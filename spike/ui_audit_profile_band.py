"""[G1] 프로필 띠가 **사실대로** 말하는지 띄워서 본다 (56회차).

    python3 spike/ui_audit_profile_band.py out/regression_3p/TC2.json out/round56/ui_profile

두 경우를 같은 서버에서 본다:
    ① 맞는 프로필이 없는 문서(TC2 · 코드 D02J) — "프로필 없음 · 새 프로젝트 · 빌려 쓴
       N칸" 과 접힌 목록이 뜨는가, 그 N 이 저장된 `borrowed.count` 와 같은가
    ② 자기 프로필 문서(AL NOUF1 · D00P) — "프로필 일치" 이고 빌린 목록이 **없는가**

★ 실 DB 를 열지 않는다 — 끝에서 sha256 을 대조한다.
"""
from __future__ import annotations
import hashlib, json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out/round56/ui_profile")
OUT.mkdir(parents=True, exist_ok=True)
CASES = [("TC2", Path(sys.argv[1] if len(sys.argv) > 1 else "out/regression_3p/TC2.json"),
          ROOT / "data" / "TC2_260821.pdf"),
         ("AL NOUF1", ROOT / "out" / "regression_3p" / "AL_NOUF1.json",
          ROOT / "data" / "pid_total.pdf")]
FOUND: list[str] = []
REAL = ROOT / "app" / "_data" / "app.db"
real_before = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""


def note(s):
    print(s, flush=True); FOUND.append(s)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


data = Path(tempfile.mkdtemp(prefix="profui-"))
os.environ["PID_DATA_DIR"] = str(data)
from app import db, revisions                                    # noqa: E402

con = db.connect(data / "app.db")
expect = {}
for i, (name, src, pdf) in enumerate(CASES):
    blob = json.loads(src.read_text()); result = blob.get("result", blob)
    job = f"prof{i:08d}"
    sha = hashlib.sha256(pdf.read_bytes()).hexdigest() if pdf.exists() else ""
    revisions.create_project(data, name)
    con.execute("INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, created_at, status,"
                " progress, message, fingerprint, project, revision)"
                " VALUES (?,?,?,?,?,'done',1.0,'',?,?,?)",
                (job, pdf.name, sha, str(pdf.resolve()), time.time() - i,
                 result.get("fingerprint", ""), name, "A"))
    con.commit(); db.store_result(con, job, result); con.commit()
    revisions.record_revision(data, name, "A", job_id=job, pdf_name=pdf.name,
                              compared_with="", result={"counts": {}, "states": {},
                                                        "radii": {}, "deleted_candidates": []})
    expect[name] = {"profile": result.get("profile") or {}, "borrowed": result.get("borrowed") or {}}
con.close()

port = free_port()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app",
                        "--host", "127.0.0.1", "--port", str(port)],
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
        errs = []
        for name, _src, _pdf in CASES:
            pg = br.new_page(viewport={"width": 1700, "height": 1000})
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_timeout(2000)
            pg.evaluate("() => document.querySelectorAll('details.pjt').forEach(d => d.open = true)")
            pg.wait_for_timeout(300)
            row = next((r for r in pg.query_selector_all("a.revrow")
                        if name in (r.evaluate("e => e.closest('details.pjt')?.innerText") or "")), None)
            if row is None:
                note(f"★ {name}: 결과 행을 못 찾았다"); pg.close(); continue
            row.click()
            pg.wait_for_timeout(6000)
            band = pg.inner_text("#legend-bar")
            tags = pg.evaluate("() => [...document.querySelectorAll('#legend-bar .lb-tag')].map(t => t.className + ':' + t.textContent)")
            ex = expect[name]
            n_saved = int((ex["borrowed"] or {}).get("count") or 0)
            shown = pg.evaluate("() => { const d = [...document.querySelectorAll('#legend-bar details summary')]"
                                ".map(s => s.textContent).find(t => t.includes('빌려 쓴 설정'));"
                                " return d || ''; }")
            note(f"[{name}] 저장된 profile.matched={ex['profile'].get('matched')} · "
                 f"borrowed.count={n_saved} · 띠 태그 {tags}")
            note(f"[{name}] 띠 문장: " + " | ".join(l for l in band.splitlines() if l.strip())[:300])
            note(f"[{name}] 접힌 목록 요약: {shown or '(없음)'} · "
                 f"숫자 일치: {(str(n_saved) in shown) if n_saved else (shown == '')}")
            pg.screenshot(path=str(OUT / f"{name.replace(' ', '_')}_띠.png"), clip={"x": 0, "y": 0, "width": 1700, "height": 420})
            pg.close()
        note("콘솔 오류: " + (" | ".join(errs[:4]) if errs else "없음"))
        br.close()
finally:
    srv.terminate(); srv.wait(timeout=20)

real_after = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""
note(f"실 DB sha256 — 같은가: {real_before == real_after}")
(OUT / "README.md").write_text("# 56회차 [G1] — 프로필 띠 (화면 자기검증)\n\n"
                               + "\n".join("- " + s for s in FOUND) + "\n", encoding="utf-8")
print("→", OUT)
