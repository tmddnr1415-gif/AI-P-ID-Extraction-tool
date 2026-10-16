"""가상 광장 — 부서 대시보드의 '최근 변경 이력' 아래에 넣은 모습을 띄워서 찍는다.

    python3 spike/ui_audit_plaza.py <out_dir>

하는 일 (실 DB 를 열지 않는다 — 빈 임시 데이터 폴더로 서버를 띄운다):
  1. 대시보드를 흉내 낸 페이지(지표 카드 · 그래프 · 최근 변경 이력 · 주간회의 메모)를 file:// 로 연다.
     최근 변경 이력은 '반으로 접기' 단추로 절반 높이가 되고, 그 아래 iframe 으로
     `http://127.0.0.1:<포트>/plaza?embed=1&user=홍길동` 을 띄운다.
  2. 다른 브라우저 셋(김철수 · 이영희 · 박민수)이 광장에 들어와 걷고 말한다.
  3. 대시보드 쪽 홍길동이 방향키로 걷고 Enter → 글 → Enter 로 말한다.
  4. 화면을 찍고 사실을 적는다 — 접힘 높이 · 접속 수 · 말풍선 · 채팅 기록 · 페이지 오류.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
data = Path(tempfile.mkdtemp(prefix="plaza_")) / "data"
data.mkdir(parents=True)

s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT), PID_PAGE_WARM="0",
           PID_ROWS_WARM="0", PID_LOGIC_WARM="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                        "--port", str(port)], cwd=str(ROOT), env=env,
                       stdout=open(OUT / "server.log", "w"), stderr=subprocess.STDOUT)
base = f"http://127.0.0.1:{port}"
for _ in range(120):
    try:
        urllib.request.urlopen(base + "/version", timeout=2); break
    except Exception:                                   # noqa: BLE001
        time.sleep(0.5)

ROWS = [("10-15 13:41", "백 담당", "삭제", "입찰", "ㄴㅁㄹ"), ("10-15 13:41", "백 담당", "추가", "입찰", "ㄴㅁㄹ"),
        ("10-15 12:39", "구 담당", "수정", "통합 업무", "Bypass and Letdown 설계 Guide - Warm-up"),
        ("10-15 11:11", "백 담당", "수정", "통합 업무", "사무환경 개선"), ("10-15 11:11", "백 담당", "수정", "통합 업무", "봉사활동"),
        ("10-15 11:11", "백 담당", "수정", "통합 업무", "ITER ECH 고전압전원장치 보고자료 작성"),
        ("10-15 11:11", "백 담당", "수정", "통합 업무", "QCO2 Compressor System Integration 진행현황"),
        ("10-15 11:11", "백 담당", "수정", "통합 업무", "QCO2 Compressor System Integration 팀장회의"),
        ("10-15 11:10", "백 담당", "수정", "통합 업무", "AIPEX 활용방안 설명"),
        ("10-15 11:10", "백 담당", "수정", "통합 업무", "QCO2 Compressor System Integration 사항 공유")]
rows_html = "".join(
    f'<div class="r"><span class="t">{t}</span><span class="w">{w}</span>'
    f'<span class="k {"del" if k == "삭제" else "add" if k == "추가" else "mod"}">{k}</span>'
    f'<span class="c">{c}</span><span class="x">{x}</span></div>' for t, w, k, c, x in ROWS)
plaza_url = f"{base}/plaza?embed=1&user=%ED%99%8D%EA%B8%B8%EB%8F%99"   # 홍길동

DASH = OUT / "mock_dashboard.html"
DASH.write_text("""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<title>계장ENG그룹 주간업무 Dashboard (흉내)</title>
<style>
 body{margin:0;font-family:'Malgun Gothic','WenQuanYi Zen Hei',sans-serif;display:flex;background:#eef0f8;color:#222}
 nav{width:64px;min-height:100vh;background:#1f2a5c;flex:none}
 main{flex:1;padding:16px 20px;min-width:0}
 .kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-bottom:14px}
 .kpi{background:#fff;border-radius:10px;padding:12px 16px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
 .kpi small{color:#666;font-size:12px}.kpi b{display:block;font-size:24px;margin:4px 0}.kpi a{color:#2348e0;font-size:12px}
 .row{display:grid;grid-template-columns:1fr 290px;gap:14px;align-items:start}
 .card{background:#fff;border-radius:10px;padding:12px 16px;box-shadow:0 1px 3px rgba(0,0,0,.06);margin-bottom:14px}
 .card h3{margin:0 0 8px;font-size:15px;display:flex;align-items:center;gap:8px}
 .card h3 small{font-weight:normal;color:#888;font-size:11.5px}
 .fold{margin-left:auto;font-size:12px;border:1px solid #c9cfe3;background:#f5f7fd;border-radius:6px;padding:3px 10px;cursor:pointer;color:#2348e0}
 .hist{position:relative;overflow:hidden;transition:max-height .25s}
 .hist.half{max-height:150px}
 .hist.half:after{content:"";position:absolute;left:0;right:0;bottom:0;height:34px;background:linear-gradient(rgba(255,255,255,0),#fff)}
 .r{display:grid;grid-template-columns:96px 70px 44px 78px 1fr;gap:8px;font-size:12.5px;padding:6px 0;border-bottom:1px solid #eceef4}
 .t{color:#666}.k{font-size:11px;border-radius:4px;text-align:center;padding:1px 0}
 .del{background:#fde4e2;color:#b42318}.add{background:#e3f6e6;color:#1d7a34}.mod{background:#e6edf9;color:#33508f}
 .memo{background:#fff8b8;border-radius:6px;padding:12px 14px;font-size:12.5px;box-shadow:0 2px 6px rgba(0,0,0,.12)}
 .memo b{color:#7a5a00}
 .plaza iframe{width:100%;height:470px;border:0;border-radius:8px;display:block;background:#24361b}
</style></head><body><nav></nav><main>
<div class="kpis">
 <div class="kpi"><small>수행 PJT 수 (진행 중)</small><b>14건</b><a>바로가기 →</a></div>
 <div class="kpi"><small>입찰 PJT 수 (진행 중)</small><b>13건</b><a>바로가기 →</a></div>
 <div class="kpi"><small>금주 업데이트 건수</small><b>112건</b><a>메뉴 선택 →</a></div>
 <div class="kpi"><small>종결 PJT (집계 제외)</small><b>16건</b><a>바로가기 →</a></div>
 <div class="kpi"><small>통합 업무</small><b>90건</b><a>바로가기 →</a></div>
</div>
<div class="row"><div>
 <div class="card"><h3>최근 변경 이력 <small>2026-W43(1021) (마지막 마감 2026-W42(1014) 수 11:59) 이후</small>
   <button id="fold" class="fold">펼치기 ▾</button></h3>
   <div id="hist" class="hist half">""" + rows_html + """</div></div>
 <div class="card plaza"><h3>가상 광장 <small>부서원이 캐릭터로 모이는 곳 — 방향키 이동 · Enter 대화</small></h3>
   <iframe id="pz" src=\"""" + plaza_url + """\" allow="fullscreen"></iframe></div>
</div>
<div class="memo"><b>📌 주간회의 전달사항 (최신)</b><br><br>2026-10-14 · 계장ENG그룹 주간회의<br>
 1. 조직건강도(SCI) 진단 (10/14~)<br>2. 하반기 조직개발 시행 (10/27)<br>3. 입찰 프로젝트 현황 공유</div>
</div></main>
<script>
 const h=document.getElementById('hist'),b=document.getElementById('fold');
 b.onclick=()=>{const half=h.classList.toggle('half');b.textContent=half?'펼치기 ▾':'반으로 접기 ▴';};
</script></body></html>""", encoding="utf-8")

facts: dict = {"errors": []}


def watch(page, who):
    page.on("pageerror", lambda e: facts["errors"].append(f"{who}: {e}"))


def walk(page, keys):
    for k, n in keys:
        for _ in range(n):
            page.keyboard.press(k, delay=90)      # 한 칸(190ms)보다 짧게 눌러 한 번에 한 칸
            time.sleep(0.16)


def chat(page, text):
    page.keyboard.press("Enter")
    page.keyboard.type(text, delay=15)
    page.keyboard.press("Enter")


with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path=os.environ.get("PW_CHROME", "/opt/pw-browsers/chromium"),
                            args=["--disable-features=IsolateOrigins,site-per-process"])
    others = []
    for name, keys in (("김철수", [("ArrowLeft", 4), ("ArrowDown", 1)]),
                       ("이영희", [("ArrowRight", 5), ("ArrowUp", 2)]),
                       ("박민수", [("ArrowRight", 3), ("ArrowDown", 1)])):
        c = br.new_context(viewport={"width": 900, "height": 600})
        p = c.new_page(); watch(p, name)
        p.goto(f"{base}/plaza?embed=1&user={urllib.request.quote(name)}")
        p.wait_for_function("window.__plaza && window.__plaza.id")
        p.click("#pz-map")
        walk(p, keys)
        others.append((name, p))

    ctx = br.new_context(viewport={"width": 1600, "height": 1000})
    dash = ctx.new_page(); watch(dash, "대시보드")
    dash.goto(DASH.as_uri())
    pz = None
    for _ in range(60):
        pz = next((f for f in dash.frames if "/plaza" in f.url), None)
        if pz is not None and "접속" in dash.frame_locator("#pz").locator("#pz-online").inner_text() \
                and "0명" not in dash.frame_locator("#pz").locator("#pz-online").inner_text():
            break
        time.sleep(0.5)
    print("frames", [f.url[:60] for f in dash.frames], flush=True)
    facts["hist_half_px"] = dash.eval_on_selector("#hist", "e => e.getBoundingClientRect().height")
    dash.click("#pz")
    walk(dash, [("ArrowUp", 2), ("ArrowRight", 1)])

    chat(others[0][1], "오 바람의나라 느낌 나네요 ㅋㅋ")
    time.sleep(0.6)
    chat(others[1][1], "점심 같이 드실 분~? 1시에 광장 우물 앞!")
    time.sleep(0.6)
    dash.click("#pz")
    chat(dash, "안녕하세요! 계장 마을 광장 첫 오픈입니다 🎉")
    time.sleep(0.6)
    chat(others[2][1], "P&ID 검토 끝나고 갈게요")
    time.sleep(1.2)

    # ── 스페이스 공격: 김철수가 홍길동 아래로 걸어가 위를 보고 휘두른다 ──────────
    kim = others[0][1]
    def pos():
        return kim.evaluate("""() => { const S = window.__plaza, h = [...S.others.values()].find(a => a.name === '홍길동');
          return {me: [S.me.tx, S.me.ty], hong: h ? [h.tx, h.ty] : null}; }""")
    time.sleep(0.8)
    pp = pos()
    hx, hy = pp["hong"]
    mx, my = pp["me"]
    kim.click("#pz-map")
    # 홍길동의 오른쪽 세 칸 → 왼쪽으로 두 칸 걸어 와서 왼쪽을 보고 선다
    walk(kim, [("ArrowRight" if hx + 3 > mx else "ArrowLeft", abs(hx + 3 - mx))])
    mx, my = pos()["me"]
    walk(kim, [("ArrowDown" if hy > my else "ArrowUp", abs(hy - my))])
    walk(kim, [("ArrowLeft", 2)])
    time.sleep(0.4)
    facts["attack_from"] = pos()
    import base64
    url = kim.evaluate("""() => new Promise(res => {
        document.dispatchEvent(new KeyboardEvent('keydown', {key: ' ', code: 'Space', bubbles: true}));
        setTimeout(() => res(document.querySelector('#pz-map').toDataURL('image/png')), 125); })""")
    (OUT / "5_공격_휘두르기.png").write_bytes(base64.b64decode(url.split(",", 1)[1]))
    time.sleep(0.15)
    dash.locator(".plaza").screenshot(path=str(OUT / "6_대시보드_맞음_퍽.png"))
    time.sleep(0.6)
    facts["hong_hit_log"] = kim.evaluate("[...window.__plaza.others.values()].filter(a => a.hit).map(a => a.name + ' ← ' + a.hit.by)")

    dash.evaluate("window.scrollTo(0, 0)")
    dash.screenshot(path=str(OUT / "1_대시보드_광장.png"))
    dash.locator(".plaza").screenshot(path=str(OUT / "2_광장_확대.png"))
    fl = dash.frame_locator("#pz")
    facts["online"] = fl.locator("#pz-online").inner_text()
    facts["who"] = fl.locator("#pz-who").inner_text()
    facts["log"] = fl.locator("#pz-log").inner_text()

    dash.click("#fold")
    time.sleep(0.5)
    facts["hist_full_px"] = dash.eval_on_selector("#hist", "e => e.getBoundingClientRect().height")
    dash.screenshot(path=str(OUT / "3_변경이력_펼침.png"), full_page=True)

    others[1][1].screenshot(path=str(OUT / "4_다른사람_화면_이영희.png"))
    br.close()

srv.terminate()
(OUT / "result.json").write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(facts, ensure_ascii=False, indent=1))
