"""31회차 UI 자기검증 — 승수 패널의 네 상태를 **실제로 눌러서** 찍는다.

    python3 spike/ui_audit_multipliers.py <결과.json> <내보낼 폴더>
    AUDIT_PROJECT="" python3 …            # 프로젝트에 안 묶인 분석으로

★ 실 DB 를 열지 않는다 (17회차 격리) — 저장된 결과로 임시 DB 를 세우고
쓰는 뿌리를 버릴 폴더로 돌린 뒤 그 DB 로만 서버를 띄운다.

이 도구가 잡은 것은 `out/round31/8_UI검증/README.md` 에 있다.
"""
from __future__ import annotations
import hashlib, json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
src = Path(sys.argv[1])


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


data = Path(tempfile.mkdtemp(prefix="uiaudit-"))
os.environ["PID_DATA_DIR"] = str(data)
from app import db
blob = json.loads(src.read_text()); result = blob.get("result", blob)
con = db.connect(data / "app.db")
job = "uiaudit00001"
pdf = ROOT / "app/_data/uploads/2391ee0f1ea6_sadara_1A46.pdf"
sha = hashlib.sha256(pdf.read_bytes()).hexdigest() if pdf.exists() else ""
con.execute("INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, created_at, status,"
            " progress, message, fingerprint, project, revision)"
            " VALUES (?,?,?,?,?,'done',1.0,'',?,?,?)",
            (job, pdf.name, sha, str(pdf), time.time(),
             result.get("fingerprint", ""), os.environ.get("AUDIT_PROJECT", "SADARA"), "A"))
con.commit(); db.store_result(con, job, result); con.commit(); con.close()

port = free_port()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app",
                        "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    import urllib.request
    for _ in range(60):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/home", timeout=2); break
        except Exception:
            time.sleep(1)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
        br = pw.chromium.launch(executable_path=exe if Path(exe).exists() else None)
        pg = br.new_page(viewport={"width": 1600, "height": 1000})
        pg.goto(f"http://127.0.0.1:{port}/")
        pg.wait_for_timeout(2500)
        row = (pg.query_selector("a.revrow")
               or pg.query_selector("a.looserow, .loose a, .loose .row a")
               or pg.query_selector(f"text={pdf.name}"))
        if row is None:
            pg.screenshot(path=str(OUT / "0_첫화면.png"))
            print("첫화면 본문:", pg.inner_text("body")[:400])
            raise SystemExit("들어갈 행 없음")
        row.click()
        pg.wait_for_timeout(5000)
        mp = pg.query_selector("#mult-panel")
        mp.scroll_into_view_if_needed(); pg.wait_for_timeout(300)
        mp.screenshot(path=str(OUT / "A_지정전.png"))
        # 값을 넣고 '지정' 을 누른다 (작성자 줄까지 실제로 통과)
        v = pg.query_selector("#mult-panel .mval")
        if v is None:
            print("폼 없음 — 패널:", repr(pg.query_selector("#mult-panel").inner_text()))
            pg.query_selector("#mult-panel").screenshot(path=str(OUT / "E_프로젝트없음.png"))
            br.close(); raise SystemExit(0)
        v.fill("4")
        pg.query_selector("#mult-panel .mnote").fill("발주처 회신")
        pg.query_selector("#mult-panel .mset-btn").click()
        pg.wait_for_timeout(600)
        pg.screenshot(path=str(OUT / "B_작성자줄.png"))
        # askAuthor 의 확인 버튼을 찾는다
        ab = pg.query_selector(".author-bar")
        if ab:
            ab.query_selector("input").fill("승국")
            ab.query_selector("button.ok").click()
        else:
            print("작성자 줄 없음 (폼이 안 떴다는 뜻)")
        pg.wait_for_timeout(1500)
        pg.screenshot(path=str(OUT / "C_저장직후_전체.png"))
        note = pg.query_selector(".edit-note")
        if note:
            note.screenshot(path=str(OUT / "C2_안내.png"))
            print("안내문:", repr(note.inner_text()))
        mp = pg.query_selector("#mult-panel")
        mp.scroll_into_view_if_needed(); pg.wait_for_timeout(400)
        mp.screenshot(path=str(OUT / "D_지정후.png"))
        print("패널:", repr(mp.inner_text()))
        api = pg.evaluate(f"""async () => (await (await fetch('/jobs/{job}/multipliers')).json())""")
        print("API set:", json.dumps(api["groups"][0].get("set"), ensure_ascii=False))
        br.close()
finally:
    srv.terminate()
print("찍음:", sorted(p.name for p in OUT.glob("*.png")))
