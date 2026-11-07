"""hotfix44 — 결과 화면의 `대조 다시` 버튼을 눌러 재분석 없이 개정 판정이 새 규칙으로 바뀌는지 확인한다.

    python3 spike/ui_audit_recompare.py <data_dir> <job_B> <out_dir>

data_dir 은 **옛 판정(hotfix42 · 수정 458)** 이 든 사본이어야 뜻이 있다.
① 스위치에 `대조 다시` 버튼 ② 누르기 전 머리줄 수정 N(옛) ③ 누르면 confirm → POST /revision 한 번 →
다시 열림 · 머리줄 수정이 태그만 센 값 ④ 같은 장에 머문다 ⑤ 페이지 오류 0.
"""
from __future__ import annotations
import json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data, JOB, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
FOUND = []
def note(s): print(s, flush=True); FOUND.append(s)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(90):
        try: urllib.request.urlopen(f"http://127.0.0.1:{port}/home", timeout=2); break
        except Exception: time.sleep(1)
    before = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/jobs/{JOB}/revision", timeout=60).read()).get("counts") or {}
    note(f"누르기 전 서버 counts — {before}")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
        br = pw.chromium.launch(executable_path=exe if Path(exe).exists() else None)
        pg = br.new_page(viewport={"width": 1800, "height": 1000})
        errs = []; posts = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
        pg.on("request", lambda r: posts.append(r.url) if r.method == "POST" and r.url.endswith("/revision") else None)
        pg.on("dialog", lambda d: d.accept())
        pg.goto(f"http://127.0.0.1:{port}/#{JOB}")
        pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.pages && S.pages.length > 0", timeout=120000); pg.wait_for_timeout(1500)
        if pg.evaluate("() => S.side"): pg.click("#rev-switch button.side"); pg.wait_for_timeout(600)
        has = pg.evaluate("() => !!document.querySelector('#rev-switch button.recmp')")
        note(f"① `대조 다시` 버튼 — {'있음' if has else '★ 없음'}")
        head0 = pg.inner_text("#rev-label")
        note(f"② 누르기 전 머리줄 — {head0!r}")
        # 수정 행이 있는 장으로 가 둔다 (다시 연 뒤 같은 장인지 본다)
        tgt = pg.evaluate("() => { const r = (S.rows || []).find(r => (r.rev || {}).state === 'MODIFIED'); return r ? r.page_no : null; }")
        if tgt: pg.select_option("#page-select", str(tgt)); pg.wait_for_timeout(1200)
        dwg0 = pg.evaluate("() => S.page && S.page.drawing_no")
        pg.screenshot(path=str(OUT / "1_누르기전.png"))
        t = time.time()
        pg.click("#rev-switch button.recmp")
        pg.wait_for_function("(h) => !S.loading && document.querySelector('#rev-label') && document.querySelector('#rev-label').innerText !== h", arg=head0, timeout=180000)
        pg.wait_for_timeout(1500)
        dt = round(time.time() - t, 1)
        head1 = pg.inner_text("#rev-label"); dwg1 = pg.evaluate("() => S.page && S.page.drawing_no")
        after = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/jobs/{JOB}/revision", timeout=60).read()).get("counts") or {}
        note(f"③ 누른 뒤 {dt}초 · POST /revision {len(posts)}회 · 머리줄 — {head1!r} · 서버 counts {after}")
        ok = len(posts) == 1 and f"수정 {after.get('MODIFIED', 0)}" in head1 and after.get("MODIFIED", 0) < before.get("MODIFIED", 0)
        note(f"   수정 {before.get('MODIFIED')} → {after.get('MODIFIED')} · 추가 {before.get('ADDED')} → {after.get('ADDED')} · 삭제 후보 {before.get('DELETED_CANDIDATE')} → {after.get('DELETED_CANDIDATE')} — {'맞음' if ok else '★ 틀림'}")
        note(f"④ 같은 장에 머묾 — {dwg0} → {dwg1} — {'맞음' if dwg0 == dwg1 else '★ 틀림'}")
        pg.screenshot(path=str(OUT / "2_누른뒤.png"))
        note(f"⑤ 페이지 오류 {len(errs)}" + (f" — {errs[:3]}" if errs else ""))
        br.close()
finally:
    srv.terminate(); srv.wait(timeout=30)
(OUT / "README.md").write_text("# hotfix44 대조 다시 — 화면 자기검증\n\n" + "\n".join(f"- {x}" for x in FOUND) + "\n", encoding="utf-8")
