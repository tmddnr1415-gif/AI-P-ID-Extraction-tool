"""hotfix29 — 띄워서 눌러 본다: 실패 화면 → 타이틀블록 칸 지정 → 저장하고 다시 분석.

    python3 spike/ui_audit_hotfix29.py OUTDIR

합성 PDF(캡션 없음 · 번호가 장마다 같아 구조로도 안 갈림)를 **실제 업로드 경로**로 올려
`TitleBlockUnreadable` 로 멈추게 한 뒤,
  ① 실패 화면에 `타이틀블록 칸 지정` 버튼이 뜨는가
  ② 도면 위에서 번호를 끌어 그으면 미리보기가 6장 중 6장에서 읽는가 · 형식이 나오는가
  ③ 작성자 없이 저장이 막히는가
  ④ `저장하고 다시 분석` 뒤 타이틀블록 단계를 지나 **범례 단계**에서 멈추는가 (버튼은 사라진다)
  ⑤ 프로젝트 폴더에 `title_block_cells.json` 이 작성자와 함께 남는가
★ 실 DB 는 열지 않는다 — sha256 대조.  캡처는 OUTDIR 에.
"""
from __future__ import annotations
import hashlib, json, os, socket, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
FOUND: list[str] = []
REAL = ROOT / "app" / "_data" / "app.db"
real_before = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""


def note(s):
    print(s, flush=True); FOUND.append(s)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


from test_hotfix28_new_form import _new_form, A1     # noqa: E402
data = Path(tempfile.mkdtemp(prefix="audit29-"))
pdf = _new_form(data / "qfe_noform.pdf", numbers=["QFE-P1-PID-001"] * 6, caption="", title_caption="")
os.environ["PID_DATA_DIR"] = str(data)
from app import revisions                             # noqa: E402
revisions.create_project(data, "QFE")

port = free_port()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                        "--port", str(port)], cwd=str(ROOT), env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    base = f"http://127.0.0.1:{port}"
    for _ in range(90):
        try:
            urllib.request.urlopen(base + "/home", timeout=2); break
        except Exception:
            time.sleep(1)
    # 실제 업로드 경로로 올린다 (프로젝트 QFE · Rev.A)
    boundary = "----audit29"
    body = b""
    for k, v in (("project", "QFE"), ("compared_with", ""), ("input_kind", "PDF")):
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"pdf\"; filename=\"{pdf.name}\"\r\n"
             f"Content-Type: application/pdf\r\n\r\n").encode() + pdf.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(base + "/jobs", data=body, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    job = json.loads(urllib.request.urlopen(req, timeout=30).read())["job_id"]
    note(f"업로드 → job {job}")

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
        br = pw.chromium.launch(executable_path=exe if Path(exe).exists() else None)
        pg = br.new_page(viewport={"width": 1366, "height": 900})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"{base}/#{job}")
        pg.wait_for_function("() => document.querySelector('#prog-title') && document.querySelector('#prog-title').textContent === '분석 실패'", timeout=120000)
        pg.wait_for_timeout(500)
        msg1 = pg.text_content("#prog-msg")
        btn = pg.evaluate("() => { const b = document.querySelector('#prog-tbfix'); return b && !b.classList.contains('hidden'); }")
        note(f"① 실패 문장: {msg1[:90]}…")
        note(f"① `타이틀블록 칸 지정` 버튼 보임: {btn}")
        pg.screenshot(path=str(OUT / "1_failure.png"), full_page=True)

        pg.click("#prog-tbfix")
        pg.wait_for_function("() => { const i = document.querySelector('#tbfix-img'); return i && i.complete && i.naturalWidth > 0 && TB.state; }", timeout=60000)
        pg.wait_for_timeout(300)
        st = pg.evaluate("() => ({page: TB.page, zoom: TB.zoom, sizes: document.querySelector('#tbfix-sizes').textContent})")
        note(f"② 패널 열림 — 보이는 장 p{st['page']} · {st['sizes']}")
        # 번호 글자 상자(1984.0, 1391.8, 2105.8, 1413.8)를 감싸는 사각형을 도면 pt 로 정해 화면 px 로 끈다
        R = [A1[0] - 410.0, A1[1] - 296.0, A1[0] - 150.0, A1[1] - 264.0]
        pg.evaluate("() => document.querySelector('#tbfix-stage').scrollIntoView({block: 'start'})")
        pg.evaluate("() => { const s = document.querySelector('#tbfix-stage'); s.scrollLeft = s.scrollWidth; s.scrollTop = s.scrollHeight; }")
        pg.wait_for_timeout(200)
        b = pg.evaluate("() => { const r = document.querySelector('#tbfix-img').getBoundingClientRect(); return [r.left, r.top]; }")
        z = st["zoom"]
        p0 = (b[0] + R[0] * z, b[1] + R[1] * z); p1 = (b[0] + R[2] * z, b[1] + R[3] * z)
        pg.mouse.move(*p0); pg.mouse.down(); pg.mouse.move(p1[0], p1[1], steps=8); pg.mouse.up()
        pg.wait_for_function("() => /장 중/.test(document.querySelector('#tbfix-preview').textContent)", timeout=30000)
        pv = " ".join(pg.text_content("#tbfix-preview").split())
        rect = pg.evaluate("() => TB.cells.dwg_no_region")
        note(f"② 그은 칸 {rect} → 미리보기: {pv[:160]}")
        pg.screenshot(path=str(OUT / "2_drawn_preview.png"), full_page=True)

        pg.fill("#tbfix-who", "")
        pg.click("#tbfix-save")
        pg.wait_for_timeout(400)
        m = pg.text_content("#tbfix-msg")
        note(f"③ 작성자 없이 저장 → “{m}”")
        saved_file = data / "projects" / "QFE" / "title_block_cells.json"
        note(f"③ 파일 생김: {saved_file.exists()} (없어야 한다)")

        pg.fill("#tbfix-who", "검증")
        pg.click("#tbfix-save-run")
        pg.wait_for_function("() => document.querySelector('#tbfix').classList.contains('hidden')", timeout=30000)
        note(f"④ 저장 파일: {saved_file.exists()} · " + (json.dumps({k: json.loads(saved_file.read_text())[k] for k in ('author', 'size', 'page_no', 'cells')}, ensure_ascii=False) if saved_file.exists() else "없음"))
        pg.wait_for_function("() => document.querySelector('#prog-title').textContent === '분석 실패' && /Legend/.test(document.querySelector('#prog-msg').textContent)", timeout=180000)
        pg.wait_for_timeout(500)
        msg2 = pg.text_content("#prog-msg")
        btn2 = pg.evaluate("() => { const b = document.querySelector('#prog-tbfix'); return b && !b.classList.contains('hidden'); }")
        note(f"④ 다시 분석 뒤 문장: {msg2[:100]}…")
        note(f"④ 타이틀블록 단계를 지났다(범례에서 멈춤): {'Symbol & Legend' in msg2} · 칸 지정 버튼 보임: {btn2} (거짓이어야 한다)")
        pg.screenshot(path=str(OUT / "3_after_rerun.png"), full_page=True)
        note("페이지 오류: " + (" | ".join(errs) if errs else "없음"))
        br.close()
finally:
    srv.terminate()
real_after = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""
note(f"실 DB sha256 같음: {real_before == real_after}")
(OUT / "README.txt").write_text("\n".join(FOUND) + "\n", encoding="utf-8")
