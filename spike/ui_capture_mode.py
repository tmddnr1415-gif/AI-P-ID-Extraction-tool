"""38회차 [B] 화면 캡처 — 첫 화면의 입찰/실행 라디오와 결과 화면의 모드 띠(선언≠실측).

저장된 UAD 결과로 임시 DB 를 세우고(실 DB 를 안 연다) 서버를 띄워 실제로 눌러 찍는다.
    python3 spike/ui_capture_mode.py
"""
import hashlib, json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
OUT = ROOT / "out" / "round38" / "10_캡처"; OUT.mkdir(parents=True, exist_ok=True)

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

data = Path(tempfile.mkdtemp(prefix="uimode-")); os.environ["PID_DATA_DIR"] = str(data)
from app import db, revisions
blob = json.loads((ROOT / "out/regression_3p/UAD.json").read_text()); result = blob["result"]
# [B] 게이트 실측(`out/round38/B_uad_bid.json`)과 같은 사실을 담는다 — 입찰 선언 · 실측 실행.
gate = json.loads((ROOT / "out/round38/B_uad_bid.json").read_text())["evidence_tier"]
result["evidence_tier"] = gate
meta = revisions.create_project(data, "UAD")
revisions.set_mode(data, "UAD", "bid", "캡처")
con = db.connect(data / "app.db"); job = "uimode000001"
pdf = ROOT / "data/UAD_binding.pdf"; sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
con.execute("INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, created_at, status, progress, message,"
            " fingerprint, project, revision) VALUES (?,?,?,?,?,'done',1.0,'',?,?,?)",
            (job, pdf.name, sha, str(pdf), time.time(), result.get("fingerprint", ""), "UAD", "Rev.A"))
con.commit(); db.store_result(con, job, result); con.commit(); con.close()
revisions.record_revision(data, "UAD", "Rev.A", job_id=job, pdf_name=pdf.name, compared_with="",
                          result={"counts": {}, "deleted_candidates": []})
port = free_port()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    import urllib.request
    for _ in range(60):
        try: urllib.request.urlopen(f"http://127.0.0.1:{port}/home", timeout=2); break
        except Exception: time.sleep(1)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
        br = pw.chromium.launch(executable_path=exe if Path(exe).exists() else None)
        pg = br.new_page(viewport={"width": 1500, "height": 950})
        pg.goto(f"http://127.0.0.1:{port}/"); pg.wait_for_timeout(2000)
        pg.select_option("#proj-pick", "UAD"); pg.wait_for_timeout(600)
        card = pg.query_selector(".intake-card")
        card.screenshot(path=str(OUT / "B1_첫화면_도면종류_입찰선언.png"))
        print("mode-note:", pg.inner_text("#mode-note")); print("checked:", pg.eval_on_selector('input[name="mode"]:checked', "e => e.value"))
        errs = []; pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        print("api /mode:", urllib.request.urlopen(f"http://127.0.0.1:{port}/jobs/{job}/mode").read()[:300])
        row = pg.query_selector("a.revrow"); row.click(); pg.wait_for_timeout(6000)
        print("console errors:", errs[:5])
        print("bar html:", pg.eval_on_selector("#mode-bar", "e => e.className + ' | ' + e.innerHTML.slice(0,300)"))
        bar = pg.query_selector("#mode-bar")
        if pg.eval_on_selector("#mode-bar", "e => !e.classList.contains('hidden')"):
            bar.scroll_into_view_if_needed(); pg.wait_for_timeout(300)
            bar.screenshot(path=str(OUT / "B2_결과화면_모드띠_선언≠실측.png"))
            print("mode-bar:", bar.inner_text())
        br.close()
finally:
    srv.terminate()
print("captured", sorted(p.name for p in OUT.iterdir()))
