"""hotfix50 — 부서 대시보드 안에 들어간 P&ID 화면을 띄워서 확인한다.

    python3 spike/ui_audit_embed.py <data_dir_to_copy> <job_id> <out_dir>

하는 일:
  1. 데이터 폴더를 **사본**으로 떠서(실 DB 를 열지 않는다) 서버를 사내망 모드(`PID_LAN=1` ·
     0.0.0.0)로 띄운다
  2. 대시보드를 흉내 낸 페이지(남색 메뉴 · 입찰 프로젝트 > P&ID 분석)를 **file://** 로 연다 —
     부서원이 dashboard.html 사본을 여는 것과 같은 출처(null)다
  3. 그 페이지가 `/version` 을 fetch 해 살아 있는지 묻고(CORS) iframe 에
     `http://<이 PC 주소>:<포트>/?embed=1&mode=bid&user=홍길동` 을 띄운다
  4. 첫 화면 · 결과 화면을 찍고 사실을 적는다 — 메뉴 숨김 · 결과 탭 자리 · 이름 · 모드 ·
     첫 화면으로 돌아와도 query 가 남는지 · 새 프로젝트가 입찰로 시작하는지 · 페이지 오류
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import lan  # noqa: E402

src, JOB, OUT = Path(sys.argv[1]).resolve(), sys.argv[2], Path(sys.argv[3]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
data = Path(tempfile.mkdtemp(prefix="embed_")) / "data"
shutil.copytree(src, data)

s = socket.socket(); s.bind(("0.0.0.0", 0)); port = s.getsockname()[1]; s.close()
ips = lan.local_ipv4()
host = ips[0] if ips else "127.0.0.1"
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT), PID_LAN="1")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0",
                        "--port", str(port)], cwd=str(ROOT), env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = f"http://{host}:{port}"
pid_url = f"{base}/?embed=1&mode=bid&user=%ED%99%8D%EA%B8%B8%EB%8F%99"   # 홍길동

DASH = OUT / "mock_dashboard.html"
DASH.write_text("""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<title>계장ENG그룹 주간업무 Dashboard (흉내)</title>
<style>
 body{margin:0;font-family:'Malgun Gothic',sans-serif;display:flex;height:100vh;background:#f4f6fb}
 nav{width:220px;background:linear-gradient(#1f2a5c,#19214b);color:#e6e9f5;padding:18px 10px;box-sizing:border-box}
 nav b{display:block;font-size:15px;margin:0 8px 18px}
 nav a{display:block;color:#e6e9f5;text-decoration:none;padding:8px 10px;border-radius:8px;font-size:13px}
 nav a.sub{padding-left:28px;font-size:12.5px}
 nav a.on{background:#2348e0}
 main{flex:1;display:flex;flex-direction:column;min-width:0}
 .bar{padding:8px 14px;font-size:12px;color:#5b6475;background:#fff;border-bottom:1px solid #e3e7ef}
 iframe{flex:1;border:0;width:100%}
 .down{padding:40px;color:#b42318}
</style></head><body>
<nav><b>계장ENG그룹<br>주간업무 Dashboard</b>
 <a href="#">📋 주간업무보고</a>
 <a href="#">📈 입찰 프로젝트</a><a class="sub on" href="#">P&amp;ID 분석</a>
 <a href="#">🏗 실행 프로젝트</a><a class="sub" href="#">P&amp;ID 분석</a>
 <a href="#">💬 익명게시판</a></nav>
<main><div class="bar" id="bar">P&amp;ID 분석 · 확인 중…</div><div id="slot" style="flex:1;display:flex"></div></main>
<script>
const URL_ = __URL__, BASE = __BASE__;
(async () => {
  const bar = document.getElementById('bar');
  try {
    const ctl = new AbortController(); setTimeout(() => ctl.abort(), 3000);
    const v = await (await fetch(BASE + '/version', {signal: ctl.signal})).json();
    window.__ver = v;
    bar.innerHTML = 'P&amp;ID 분석 · 서버 ' + (v.version || '?') + ' · <a href="' + URL_ + '" target="_blank">새 창으로 열기</a>';
    const f = document.createElement('iframe'); f.src = URL_; f.id = 'pid';
    document.getElementById('slot').appendChild(f);
  } catch (e) {
    window.__ver = 'ERR ' + e;
    document.getElementById('slot').innerHTML = '<div class="down">P&amp;ID 분석 서버에 연결할 수 없습니다.</div>';
  }
})();
</script></body></html>""".replace("__URL__", json.dumps(pid_url)).replace("__BASE__", json.dumps(base)), encoding="utf-8")

facts = {"pid_url": pid_url, "host_ip": host}
try:
    for _ in range(90):
        try:
            urllib.request.urlopen(f"{base}/home", timeout=2); break
        except Exception:
            time.sleep(1)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
        br = pw.chromium.launch(executable_path=exe if Path(exe).exists() else None)
        pg = br.new_page(viewport={"width": 1600, "height": 950})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
        pg.goto(DASH.as_uri())
        pg.wait_for_selector("iframe#pid", timeout=15000)
        facts["version_from_file_origin"] = pg.evaluate("() => typeof window.__ver === 'object' ? 'ok ' + window.__ver.version : String(window.__ver)")
        fr = pg.frame_locator("iframe#pid")
        frame = next(f for f in pg.frames if f.url.startswith(base))
        frame.wait_for_function("() => typeof EMBED !== 'undefined' && typeof DASH !== 'undefined' && DASH.home", timeout=60000)
        pg.wait_for_timeout(1500)
        facts["home"] = frame.evaluate("""() => ({
          embed: document.body.classList.contains('embed'),
          sidebar_shown: getComputedStyle(document.getElementById('sidebar')).display !== 'none',
          padding_left: getComputedStyle(document.body).paddingLeft,
          author: localStorage.getItem('pid.author'),
          mode_radio: (document.querySelector('input[name=mode]:checked')||{}).value,
          embed_from: document.getElementById('embed-from').textContent,
          hscroll: document.documentElement.scrollWidth > document.documentElement.clientWidth })""")
        pg.screenshot(path=str(OUT / "1_대시보드_안_첫화면.png"))
        # 결과 화면
        frame.evaluate(f"() => {{ location.hash = {json.dumps(JOB)}; }}")
        frame.wait_for_function("() => S.job && !S.loading && S.pages && S.pages.length > 0", timeout=180000)
        pg.wait_for_timeout(2500)
        facts["results"] = frame.evaluate("""() => ({
          url: location.href,
          tabs_parent: document.getElementById('tabs').parentElement.id,
          tabs_visible: getComputedStyle(document.getElementById('tabs')).display,
          tab_buttons: document.querySelectorAll('#tabs button').length,
          rows: (S.rows||[]).length,
          stage_w: document.getElementById('stage').clientWidth,
          hscroll: document.documentElement.scrollWidth > document.documentElement.clientWidth })""")
        pg.screenshot(path=str(OUT / "2_대시보드_안_결과.png"))
        # 결과 탭 하나 눌러 보기
        btns = frame.locator("#embed-tabs #tabs button")
        if btns.count() > 1:
            btns.nth(1).click(); pg.wait_for_timeout(800)
            facts["tab_click"] = frame.evaluate("() => ({tab: S.tab, on: (document.querySelector('#tabs button.on')||{}).textContent})")
        # 첫 화면으로 — query 가 남는가
        frame.locator("#to-home").click(); pg.wait_for_timeout(1500)
        facts["back_home"] = frame.evaluate("() => ({url: location.href, embed: document.body.classList.contains('embed')})")
        # 새 프로젝트 — 입찰로 시작하는가
        frame.locator("#proj-new-btn").click()
        frame.locator("#proj-name").fill("EMBED_TEST")
        frame.locator("#proj-save").click(); pg.wait_for_timeout(1500)
        projs = json.loads(urllib.request.urlopen(f"{base}/projects").read())
        p = next((x for x in projs if x["name"] == "EMBED_TEST"), None)
        facts["new_project_mode"] = p and p.get("mode")
        facts["mode_radio_after_create"] = frame.evaluate("() => (document.querySelector('input[name=mode]:checked')||{}).value")
        pg.screenshot(path=str(OUT / "3_새프로젝트_입찰.png"))
        # 대시보드 없이 직접 열면 예전 그대로 (메뉴 있음)
        p2 = br.new_page(viewport={"width": 1600, "height": 950})
        p2.goto(f"{base}/"); p2.wait_for_timeout(2000)
        facts["direct_open"] = p2.evaluate("() => ({embed: document.body.classList.contains('embed'), sidebar: getComputedStyle(document.getElementById('sidebar')).display !== 'none'})")
        facts["errors"] = errs
        br.close()
finally:
    srv.terminate()
    try:
        srv.wait(timeout=10)
    except Exception:
        srv.kill()
    shutil.rmtree(data.parent, ignore_errors=True)
(OUT / "facts.json").write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(facts, ensure_ascii=False, indent=1))
