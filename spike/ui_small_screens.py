"""hotfix74 — 작은 화면 · 배율을 키운 노트북 (Windows 125% · 150%) 에서 화면이 쓸 만한가.

    python3 spike/ui_small_screens.py <data_dir 사본> <job> out/hotfix74/small_screens

회사 노트북은 1920×1080 을 150% 로 쓰면 CSS 화면이 1280×720 이고, 1366×768 을 125% 로 쓰면 1093×614 다.
보는 것: 페이지 오류 0 · 가로 스크롤 없음 · 도면 창과 목록이 0 높이로 밀리지 않음 · 머리줄의 주요 단추
(Excel 출력 · 더보기 · 최종 저장)가 화면 안에 있고 눌린다 · 업로드 상자가 화면 안에 있다.
실 DB 를 열지 않는다 (PID_DATA_DIR 로 사본).
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data, JOB, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
base = f"http://127.0.0.1:{port}"
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT), PID_PAGE_WARM="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=open(OUT / "server.log", "w"), stderr=subprocess.STDOUT)
SIZES = [(1280, 720, 1.5, "1920x1080_150pct"), (1093, 614, 1.25, "1366x768_125pct"),
         (1024, 700, 1.0, "1024x700"), (1536, 864, 1.25, "1920x1080_125pct"), (960, 540, 2.0, "1920x1080_200pct"), (800, 600, 1.0, "800x600")]
FACTS, DEFECTS = {}, []
CHECK = """() => {
  const inView = sel => { const e = document.querySelector(sel); if (!e) return 'none';
    const st = getComputedStyle(e); if (st.display === 'none' || st.visibility === 'hidden') return 'hidden';
    const r = e.getBoundingClientRect(); if (r.width < 2 || r.height < 2) return 'zero';
    const x = r.left + r.width / 2, y = r.top + r.height / 2;
    if (x < 0 || y < 0 || x > innerWidth || y > innerHeight) return 'offscreen';
    const hit = document.elementFromPoint(x, y); return (hit === e || e.contains(hit)) ? 'ok' : 'covered'; };
  const h = sel => { const e = document.querySelector(sel); return e ? Math.round(e.getBoundingClientRect().height) : -1; };
  return { hscroll: document.documentElement.scrollWidth > innerWidth + 1,
           excel: inView('#excel'), more: inView('#more-actions > summary, #more-actions > button, #more-actions'),
           grid_h: h('#gridwrap'), stage_h: h('#stage'), head_h: h('header.head'),
           // 목록이 칸 밖에 있으면 닿을 수 있어야 한다 — 오른쪽 칸이 굴러가거나 목록이 칸 안에 보이거나
           grid_reach: (() => { const R = document.querySelector('#right'), G = document.querySelector('#gridwrap');
             if (!R || !G) return false; const r = R.getBoundingClientRect(), g = G.getBoundingClientRect();
             if (g.top < r.bottom - 60) return 'visible';
             const oy = getComputedStyle(R).overflowY; return (oy === 'auto' || oy === 'scroll') && R.scrollHeight > R.clientHeight ? 'scroll' : false; })(),
           build_over_memo: (() => { const b = document.querySelector('#build'), m = document.querySelector('#memo');
             if (!b || !m) return false; const x = b.getBoundingClientRect(), y = m.getBoundingClientRect();
             const ox = Math.min(x.right, y.right) - Math.max(x.left, y.left), oy = Math.min(x.bottom, y.bottom) - Math.max(x.top, y.top);
             return ox > 0 && oy > 0 ? Math.round(ox * oy) : 0; })() };
}"""
try:
    for _ in range(120):
        try:
            urllib.request.urlopen(base + "/version", timeout=2); break
        except Exception:                                          # noqa: BLE001
            time.sleep(0.5)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        for w, h, scale, tag in SIZES:
            ctx = br.new_context(viewport={"width": w, "height": h}, device_scale_factor=scale)
            pg = ctx.new_page(); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("dialog", lambda d: d.accept())
            pg.goto(base + "/"); pg.wait_for_timeout(2500)
            home = pg.evaluate("""() => { const d = document.querySelector('#drop'); const r = d && d.getBoundingClientRect();
                return { drop_visible: !!r && r.width > 50 && r.top < innerHeight,
                         hscroll: document.documentElement.scrollWidth > innerWidth + 1 }; }""")
            pg.screenshot(path=str(OUT / f"{tag}_1_home.png"))
            pg.evaluate(f"open('{JOB}')")
            pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.pages && S.pages.length > 0",
                                 timeout=180000)
            pg.wait_for_timeout(2000)
            pg.evaluate("() => { if (S.side) toggleSide(); }"); pg.wait_for_timeout(800)
            res = pg.evaluate(CHECK)
            pg.screenshot(path=str(OUT / f"{tag}_2_result.png"))
            pg.evaluate("() => { const R = document.querySelector('#right'); R.scrollTop = R.scrollHeight; }")
            pg.wait_for_timeout(500)
            pg.screenshot(path=str(OUT / f"{tag}_3_right_scrolled.png"))
            f = {"home": home, "result": res, "errors": errs[:3]}
            FACTS[tag] = f
            bad = []
            if errs: bad.append(f"페이지 오류 {errs[:2]}")
            if home["hscroll"] or res["hscroll"]: bad.append("가로 스크롤")
            if not home["drop_visible"]: bad.append("업로드 상자가 첫 화면에 안 보임")
            if res["excel"] != "ok": bad.append(f"Excel 출력 단추 {res['excel']}")
            if res["grid_h"] < 120: bad.append(f"목록 높이 {res['grid_h']}px")
            if not res["grid_reach"]: bad.append("목록이 칸 밖으로 잘려 닿을 수 없음")
            if res["build_over_memo"] > 8000: bad.append(f"업데이트 딱지가 메모 줄을 덮음 ({res['build_over_memo']}px²)")
            if res["stage_h"] < 200: bad.append(f"도면 창 높이 {res['stage_h']}px")
            if bad:
                DEFECTS.append(f"{tag}: " + " · ".join(bad))
            print(tag, json.dumps(f, ensure_ascii=False), flush=True)
            ctx.close()
        br.close()
finally:
    srv.terminate()
    (OUT / "README.md").write_text("# 작은 화면 · 배율 키운 노트북\n\n결함 " + str(len(DEFECTS)) + "\n\n"
                                   + "\n".join(f"- {d}" for d in DEFECTS) + "\n\n```\n"
                                   + json.dumps(FACTS, ensure_ascii=False, indent=1) + "\n```\n", encoding="utf-8")
    print("결함", len(DEFECTS), DEFECTS)
