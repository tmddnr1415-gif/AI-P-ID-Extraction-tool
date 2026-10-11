"""hotfix85 — 띄워서 눌러 본다: **이전 프로그램 기준**으로 새 양식(Takhiatash)을 올리고,
분석이 멈추면 진행 화면의 '도면 가르치기' 판에 뜬 **할 일 목록**만 보고 도면을 **눌러** 끝까지 가는지.

    python3 spike/ui_audit_teach.py data/newproj/binder.pdf OUTDIR

* 서버는 `PID_FORM_AUTO=0` — hotfix84 가 넣은 새 양식 자동 갈래(사각형 테두리 · 범례 제목
  다른 낱말 · 곡선+짧은 직선 버블 · NOTES 머리말)를 끈다.  그 전 프로그램처럼 멈춘다.
* 사람이 하는 일은 할 일 목록대로 도면을 한 번씩 누르는 것뿐이다 (사각형 긋기 없음 · API 는 업로드만).
* 실 DB 는 열지 않는다 (임시 데이터 폴더 · sha256 대조).  캡처와 결과는 OUTDIR 에.

좌표는 이 문서에서 사람이 눈으로 보고 그을 자리다 (도면번호 칸 · 테두리 안쪽 · NOTES ·
범례 p2 의 칸 제목 셋 · p6 의 버블 둘).
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
PDF = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
REAL = ROOT / "app" / "_data" / "app.db"
real_before = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""
LOG: list[str] = []


def note(s):
    print(s, flush=True)
    LOG.append(s)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


data = Path(tempfile.mkdtemp(prefix="audit85-"))
os.environ["PID_DATA_DIR"] = str(data)
from app import revisions  # noqa: E402
PROJECT = "TAKHIATASH"
revisions.create_project(data, PROJECT)

port = free_port()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT), PID_FORM_AUTO="0",
           PID_PAGE_WARM="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                        "--port", str(port)], cwd=str(ROOT), env=env,
                       stdout=open(OUT / "server.log", "w"), stderr=subprocess.STDOUT)
base = f"http://127.0.0.1:{port}"

# 사람이 누를 자리 — **화면이 띄운 장**에서 사람이 눈으로 보고 누를 곳 (도면 pt).
# 버블은 기준선 결과(hotfix84 · 자동으로 읽은 1139행)의 그 장 계기 하나의 한가운데,
# NOTES 는 그 장에 인쇄된 `NOTES` 글자, 도면번호는 그 장의 도면번호 글자.
BASE = json.loads((ROOT / "out" / "regression_3p" / "TAKHIATASH.json").read_text())["result"]["rows"]


def eye(page_no, what):
    """사람의 눈 — 그 장에서 무엇이 어디 있는지 (분석 결과가 아니라 인쇄된 것)."""
    if what == "bubble":
        r = next(r for r in BASE if r["page_no"] == page_no and r["tab"] == "FIELD" and r.get("rect"))["rect"]
        return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
    sys.path.insert(0, str(ROOT / "app" / "engine"))
    import pidcache
    _d, pp = pidcache.load_pages(PDF, only={page_no})
    for r, t in pp[0].words:
        if what == "notes" and t.upper() == "NOTES":
            return ((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)
        if what == "dwg_no" and t.count("-") >= 3 and r.y0 > pp[0].height * 0.8:
            return ((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)
    raise LookupError(f"p{page_no} 에 {what} 없음")

try:
    for _ in range(90):
        try:
            urllib.request.urlopen(base + "/home", timeout=2); break
        except Exception:
            time.sleep(1)
    boundary = "----audit85"
    body = b""
    for k, v in (("project", PROJECT), ("compared_with", ""), ("input_kind", "PDF")):
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"pdf\"; filename=\"{PDF.name}\"\r\n"
             f"Content-Type: application/pdf\r\n\r\n").encode() + PDF.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(base + "/jobs", data=body, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    job = json.loads(urllib.request.urlopen(req, timeout=60).read())["job_id"]
    note(f"업로드 → 분석 {job} (프로젝트 {PROJECT} · 이전 프로그램 기준 PID_FORM_AUTO=0)")

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
        br = pw.chromium.launch(executable_path=exe if Path(exe).exists() else None)
        pg = br.new_page(viewport={"width": 1440, "height": 960})
        errs: list[str] = []
        pg.on("pageerror", lambda e: errs.append(str(e)))

        def wait_end(timeout_s=600):
            """분석이 끝날 때까지 — 실패면 실패 문장, 성공이면 None."""
            t0 = time.time()
            while time.time() - t0 < timeout_s:
                st = json.loads(urllib.request.urlopen(f"{base}/jobs/{job}", timeout=10).read())
                if st.get("status") in ("failed", "done", "cancelled"):
                    return st
                time.sleep(2)
            raise TimeoutError("분석이 끝나지 않음")

        def zoom_to(z):
            while True:
                cur = pg.evaluate("() => TB.zoom")
                if abs(cur - z) < 1e-6:
                    return
                pg.click("#tbfix-zoom-in" if cur < z else "#tbfix-zoom-out")
                pg.wait_for_timeout(700)

        def goto_page(n):
            pg.fill("#tbfix-page", str(n))
            pg.dispatch_event("#tbfix-page", "change")
            pg.wait_for_function(f"() => TB.page === {n} && document.querySelector('#tbfix-img').complete", timeout=30000)
            pg.wait_for_timeout(500)

        def click_at(x, y, zoom=1.0):
            zoom_to(zoom)
            pg.evaluate("() => document.querySelector('#tbfix-stage').scrollIntoView({block: 'center'})")
            pg.evaluate(f"""() => {{ const st = document.querySelector('#tbfix-stage');
                st.scrollLeft = Math.max(0, {x} * TB.zoom - st.clientWidth / 2);
                st.scrollTop = Math.max(0, {y} * TB.zoom - st.clientHeight / 2); }}""")
            pg.wait_for_timeout(200)
            box = pg.eval_on_selector("#tbfix-img", "e => { const b = e.getBoundingClientRect(); return [b.left, b.top]; }")
            z = pg.evaluate("() => TB.zoom")
            before = pg.text_content("#tbfix-preview")
            pg.mouse.click(box[0] + x * z, box[1] + y * z)
            pg.wait_for_function("(b) => { const t = document.querySelector('#tbfix-preview').textContent; return t !== b && !/읽는 중|찾는 중/.test(t); }",
                                 arg=before, timeout=120000)
            pg.wait_for_timeout(300)
            return " ".join(pg.text_content("#tbfix-preview").split())

        def tasks():
            return pg.evaluate("() => [...document.querySelectorAll('#tbfix-tasks li.tb-task')].map(li => "
                               "({k: li.dataset.task, done: li.classList.contains('done'), on: li.classList.contains('on'),"
                               " text: li.querySelector('b').textContent}))")

        def save_and_rerun(tag):
            pg.fill("#tbfix-who", "홍길동")
            pg.click("#tbfix-save-run")
            pg.wait_for_function("() => document.querySelector('#tbfix').classList.contains('hidden')", timeout=30000)
            # 다시 분석이 **시작된 것**을 본 뒤에 끝을 기다린다 — 바로 물으면 앞 분석의 '실패' 를 읽는다
            t0 = time.time()
            while time.time() - t0 < 60:
                st = json.loads(urllib.request.urlopen(f"{base}/jobs/{job}", timeout=10).read())
                if st.get("status") in ("queued", "running", "done"):
                    break
                time.sleep(0.5)
            note(f"[{tag}] 저장하고 다시 분석")

        pg.goto(f"{base}/#{job}")
        rounds = []
        for step in range(1, 6):
            st = wait_end()
            if st.get("status") == "done":
                note(f"② {step}번째 분석: 끝까지 갔습니다 — 행 {st.get('rows') or st.get('row_count')}")
                rounds.append({"step": step, "status": "done"})
                break
            msg = st.get("message") or ""
            pg.wait_for_function("() => document.querySelector('#prog-title') && /실패/.test(document.querySelector('#prog-title').textContent)", timeout=60000)
            pg.wait_for_function("() => !document.querySelector('#tbfix').classList.contains('hidden') && TB.state", timeout=60000)
            pg.wait_for_timeout(800)
            guide = pg.text_content("#tbfix-guide")
            note(f"② {step}번째 분석: 멈춤 — {msg[:70]}…")
            note(f"   판이 저절로 열림 · 안내: {guide[:80]}…")
            rounds.append({"step": step, "status": "failed", "message": msg, "guide": guide})
            pg.screenshot(path=str(OUT / f"{step}a_멈춤과_가르치기판.png"), full_page=True)
            head = " ".join(pg.text_content("#tbfix-tasks li.tb-head").split())
            ts = tasks()
            note(f"   할 일 목록: {head}")
            for t in ts:
                note(f"     · {t['text']}")
            rounds[-1]["tasks"] = [t["k"] for t in ts]
            clicks = 0
            if not ts:
                note("   가르칠 것이 없는 멈춤 — 끝냄")
                break
            for t in ts:
                k = t["k"]
                pg.click(f'#tbfix-tasks li[data-task="{k}"]')
                pg.wait_for_function("() => document.querySelector('#tbfix-img').complete", timeout=30000)
                pg.wait_for_timeout(600)
                if k == "legend":
                    note(f"   [범례] 목록을 누르니 p{pg.evaluate('() => TB.page')} 가 떴습니다 → [이 장이 범례입니다]")
                    before = pg.text_content("#tbfix-preview")
                    pg.click("#tbfix-tasks button.tb-do")
                    pg.wait_for_function("(b) => { const t = document.querySelector('#tbfix-preview').textContent; return t !== b && !/찾는 중/.test(t); }",
                                         arg=before, timeout=120000)
                    clicks += 1
                    note(f"     → {' '.join(pg.text_content('#tbfix-preview').split())[:170]}")
                    pg.screenshot(path=str(OUT / f"{step}b_범례장_한번누름.png"), full_page=True)
                elif k == "bubbles":
                    pno = pg.evaluate("() => TB.page")
                    pv = click_at(*eye(pno, "bubble"), 1.0); clicks += 1
                    note(f"   [버블] 목록이 띄운 p{pno} 에서 버블 하나 누름 → {pv[:170]}")
                    pg.screenshot(path=str(OUT / f"{step}c_버블_한번누름.png"), full_page=True)
                elif k in ("dwg_no", "notes"):
                    pno = pg.evaluate("() => TB.page")
                    try:
                        xy = eye(pno, k)
                    except LookupError as e:
                        note(f"   [{k}] {e} — 건너뜀 (선택 항목)"); continue
                    pv = click_at(*xy, 0.75); clicks += 1
                    note(f"   [{k}] p{pno} 에서 누름 → {pv[:170]}")
                    pg.screenshot(path=str(OUT / f"{step}d_{k}_한번누름.png"), full_page=True)
            head = " ".join(pg.text_content("#tbfix-tasks li.tb-head").split())
            note(f"   누른 횟수 {clicks} · 목록: {head}")
            rounds[-1]["clicks"] = clicks
            pg.screenshot(path=str(OUT / f"{step}e_다_알려줌.png"), full_page=True)
            save_and_rerun(f"{step}번째")
        # 결과 화면
        res = json.loads(urllib.request.urlopen(f"{base}/jobs/{job}", timeout=10).read())
        rows = json.loads(urllib.request.urlopen(f"{base}/jobs/{job}/rows?tab=ALL&slim=1", timeout=60).read())
        if isinstance(rows, dict):
            rows = rows.get("rows") or []
        styles = {}
        for r in rows:
            s = ((r.get("evidence") or {}).get("detail") or {}).get("bubble_style") or (r.get("evidence") or {}).get("bubble_style") or "-"
            styles[s] = styles.get(s, 0) + 1
        note(f"③ 최종: 상태 {res.get('status')} · 행 {len(rows)} · 버블 출처 {styles}")
        try:
            pg.wait_for_function("() => !document.querySelector('#main').classList.contains('hidden')", timeout=60000)
            pg.wait_for_timeout(3000)
        except Exception:
            pg.goto(f"{base}/")
            pg.wait_for_timeout(2000)
        pg.screenshot(path=str(OUT / "9_결과화면.png"), full_page=False)
        saved = json.loads((data / "projects" / PROJECT / "form_teach.json").read_text())
        note(f"④ 저장된 가르침: 작성자 {saved.get('author')} · 범례 장 {[x['page_no'] for x in (saved.get('legend_page') or [])]} · "
             f"NOTES {bool(saved.get('notes'))} · 범례 칸 {sorted(saved.get('legend') or {})} · 버블 예시 {len(saved.get('bubbles') or [])}")
        note(f"⑤ 페이지 오류 {len(errs)} {errs[:3]}")
        br.close()
    (OUT / "result.json").write_text(json.dumps({"log": LOG, "rounds": rounds, "rows": len(rows)},
                                                ensure_ascii=False, indent=1))
finally:
    srv.terminate()
    try:
        srv.wait(timeout=20)
    except Exception:
        srv.kill()
    after = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""
    note(f"⑥ 실 DB sha256 같음: {after == real_before}")
    (OUT / "log.txt").write_text("\n".join(LOG), encoding="utf-8")
