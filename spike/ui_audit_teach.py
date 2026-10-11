"""hotfix85 — 띄워서 눌러 본다: **이전 프로그램 기준**으로 새 양식(Takhiatash)을 올리고,
분석이 멈출 때마다 진행 화면의 '도면 가르치기' 판에서 사각형만 그어 끝까지 가는지.

    python3 spike/ui_audit_teach.py data/newproj/binder.pdf OUTDIR

* 서버는 `PID_FORM_AUTO=0` — hotfix84 가 넣은 새 양식 자동 갈래(사각형 테두리 · 범례 제목
  다른 낱말 · 곡선+짧은 직선 버블 · NOTES 머리말)를 끈다.  그 전 프로그램처럼 멈춘다.
* 사람이 하는 일은 화면에서 사각형을 긋는 것뿐이다 (API 를 직접 부르지 않는다 — 업로드만 API).
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

# 사람이 그을 자리 (도면 pt)
DWG_NO = [1068.0, 820.0, 1142.0, 834.0]
DRAWING = [28.0, 7.0, 1184.0, 835.0]
NOTES = [968.0, 20.0, 1184.0, 834.0]
LEGEND = {"legend:VALVES ACTUATORS": [412.0, 137.0, 442.0, 154.0],
          "legend:ELECTRIC SIGNAL": [84.0, 201.0, 130.0, 212.0],
          "legend:LINE VALVES": [48.0, 663.0, 70.0, 681.0]}
BUBBLES = [[631.0, 656.5, 672.0, 672.5], [234.5, 458.5, 275.5, 474.0]]

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

        def drag(item, rect):
            pg.check(f'input[name="tbfix-cell"][value="{item}"]')
            z = pg.evaluate("() => TB.zoom")
            # 그을 자리가 보이게 굴린다
            pg.evaluate(f"""() => {{ const st = document.querySelector('#tbfix-stage');
                st.scrollLeft = Math.max(0, {rect[0]} * TB.zoom - 60); st.scrollTop = Math.max(0, {rect[1]} * TB.zoom - 60); }}""")
            pg.wait_for_timeout(200)
            box = pg.eval_on_selector("#tbfix-img", "e => { const b = e.getBoundingClientRect(); return [b.left, b.top]; }")
            x0, y0 = box[0] + rect[0] * z, box[1] + rect[1] * z
            x1, y1 = box[0] + rect[2] * z, box[1] + rect[3] * z
            pg.mouse.move(x0, y0); pg.mouse.down(); pg.mouse.move((x0 + x1) / 2, (y0 + y1) / 2, steps=4)
            pg.mouse.move(x1, y1, steps=4); pg.mouse.up()
            pg.wait_for_function("() => !/읽는 중/.test(document.querySelector('#tbfix-preview').textContent)", timeout=120000)
            pg.wait_for_timeout(300)
            return pg.text_content("#tbfix-preview")

        def save_and_rerun(tag):
            pg.fill("#tbfix-who", "홍길동")
            pg.click("#tbfix-save-run")
            pg.wait_for_function("() => document.querySelector('#tbfix').classList.contains('hidden')", timeout=30000)
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
            if "도면번호" in msg:
                zoom_to(0.5)
                pv = drag("dwg_no_region", DWG_NO)
                note(f"   도면번호 칸 → {pv.splitlines()[0][:110] if pv else ''}")
                pv = drag("drawing", DRAWING)
                note(f"   도면 영역 → {pv[:110]}")
                pv = drag("notes", NOTES)
                note(f"   NOTES 영역 → {pv[:110]}")
                pg.screenshot(path=str(OUT / f"{step}b_타이틀블록_도면영역_NOTES.png"), full_page=True)
                save_and_rerun("타이틀블록 · 도면 영역 · NOTES")
            elif "Legend" in msg:
                pg.click("#tbfix-go-legend")
                pg.wait_for_timeout(1500)
                note(f"   '범례 장으로' → p{pg.evaluate('() => TB.page')}")
                if pg.evaluate("() => TB.page") != 2:
                    goto_page(2)
                zoom_to(1)
                for item, rect in LEGEND.items():
                    pv = drag(item, rect)
                    note(f"   {item} → {' '.join(pv.split())[:150]}")
                pg.screenshot(path=str(OUT / f"{step}b_범례_칸제목_셋.png"), full_page=True)
                save_and_rerun("범례 칸 제목 셋")
            elif "버블" in msg:
                goto_page(6)
                zoom_to(1.5)
                for rect in BUBBLES:
                    pv = drag("bubbles", rect)
                    note(f"   버블 예시 → {' '.join(pv.split())[:170]}")
                pg.screenshot(path=str(OUT / f"{step}b_버블_예시_둘.png"), full_page=True)
                save_and_rerun("버블 예시 둘")
            else:
                note("   가르칠 수 없는 멈춤 — 끝냄")
                break
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
        note(f"④ 저장된 가르침: 작성자 {saved.get('author')} · 도면 영역 {bool(saved.get('drawing'))} · "
             f"NOTES {bool(saved.get('notes'))} · 범례 {sorted(saved.get('legend') or {})} · 버블 예시 {len(saved.get('bubbles') or [])}")
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
