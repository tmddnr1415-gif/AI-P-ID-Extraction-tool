"""hotfix74 — 사람이 적는 글자에 HTML 이 섞이면 (이름 · 메모 · 사유 · 칸 값).

    python3 spike/ui_xss.py <data_dir 사본> <job> out/hotfix74/xss

부서원이 남긴 글은 다른 사람의 화면에 그대로 뜬다 (VOC · 메모 · 편집 이력 · 승수 근거 …).  그 글에 `<img onerror>` 나
따옴표가 섞이면 남의 화면에서 스크립트가 돌거나 속성이 깨질 수 있다.  사람이 쓸 수 있는 칸 전부에 독을 넣고, 그 글을 보이는
화면을 전부 열어 (a) 스크립트가 돌았는가 (b) 독이 속성이나 태그로 DOM 에 들어갔는가를 센다.  실 DB 를 열지 않는다.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.parse
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
MARK = "window.__xss=(window.__xss||[]).concat([%s])"
P = ('<img src=x onerror="' + MARK % "'IMG'" + '">"\'><svg onload="' + MARK % "'SVG'" + '">'
     + '" onmouseover="' + MARK % "'ATTR'" + '" x="')
FOUND, DEFECTS = [], []


def req(method, path, body=None, form=None):
    if form is not None:
        data_ = urllib.parse.urlencode(form).encode()
        headers = {"content-type": "application/x-www-form-urlencoded"}
    elif body is not None:
        data_ = json.dumps(body).encode()
        headers = {"content-type": "application/json"}
    else:
        data_, headers = None, {}
    r = urllib.request.Request(base + path, data=data_, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:200]


try:
    for _ in range(120):
        try:
            urllib.request.urlopen(base + "/version", timeout=2); break
        except Exception:                                          # noqa: BLE001
            time.sleep(0.5)
    rows = req("GET", f"/jobs/{JOB}/rows?slim=1")[1]
    page = rows[0]["page_no"]
    keys = [r["key"] for r in rows if r["page_no"] == page][:4]
    wrote = {}
    for k, field in zip(keys, ["description", "remark", "tag_no", "line_no"]):
        wrote[f"row.{field}"] = req("PATCH", f"/jobs/{JOB}/rows/{k}", {"field": field, "value": P, "author": P})[0]
    wrote["memo"] = req("POST", f"/jobs/{JOB}/memo/{page}", {"text": P, "author": P})[0]
    wrote["voc"] = req("POST", "/voc", {"category": "UI", "reason": P, "author": P, "job_id": JOB})[0]
    wrote["report"] = req("POST", f"/jobs/{JOB}/reports", {"kind": "ROW", "what": "TYPE", "detail": P,
                                                          "row_key": keys[0], "author": P})[0]
    wrote["save"] = req("POST", f"/jobs/{JOB}/save", {"author": P})[0]
    m = req("GET", f"/jobs/{JOB}/multipliers")[1]
    groups = (m or {}).get("groups") if isinstance(m, dict) else None
    if groups:
        wrote["multiplier"] = req("POST", f"/jobs/{JOB}/multipliers",
                                  form={"unit": groups[0]["unit"], "multiplier": 3, "author": P, "note": P})[0]
    sn = req("GET", f"/jobs/{JOB}/sheet_numbers")[1]
    pages = (sn or {}).get("sheets") if isinstance(sn, dict) else None
    if pages:
        wrote["sheet_no"] = req("POST", f"/jobs/{JOB}/sheet_numbers",
                                form={"page": pages[0]["page_no"], "drawing_no": "X-0001", "author": P, "note": P})[0]
    wrote["symbol"] = req("POST", "/symbols/global", form={"symbol_id": "XSS1", "kind": "INSTRUMENT_TAG", "name": P,
                                                           "type_value": "PI", "author": P, "note": P})[0]
    FOUND.append(f"독을 넣은 칸: {wrote}")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        pg = br.new_context(viewport={"width": 1600, "height": 950}).new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("dialog", lambda d: d.accept())
        pg.goto(base + "/?embed=1&user=" + urllib.parse.quote(P)); pg.wait_for_timeout(3000)
        steps = ["첫 화면"]
        pg.evaluate(f"open('{JOB}')")
        pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.pages && S.pages.length > 0",
                             timeout=180000)
        pg.wait_for_timeout(2000); pg.evaluate("() => { if (S.side) toggleSide(); }")
        steps.append("결과")
        for k in keys:
            pg.evaluate(f"() => select('{k}', true)"); pg.wait_for_timeout(700)
        steps.append("근거 패널 4행")
        for js, name in [("() => { const b = document.querySelector('#mult-panel .fold, #mult-panel button'); if (typeof _multFolded === 'function') { _multFolded(false); loadMultipliers && loadMultipliers(); } }", "승수 판"),
                         ("() => { if (typeof _sheetFolded === 'function') { _sheetFolded(false); loadSheetNumbers && loadSheetNumbers(); } }", "장 도면번호 판"),
                         ("() => memoOpen && memoOpen(true)", "메모"),
                         ("() => vocDialog({})", "VOC 창"),
                         ("() => { closeModal && closeModal(); return showReportList(); }", "신고 목록"),
                         ("() => { closeModal && closeModal(); return showSymbolRegister(); }", "심볼 사전")]:
            try:
                pg.evaluate(js); pg.wait_for_timeout(1500); steps.append(name)
            except Exception as e:                             # noqa: BLE001
                steps.append(f"{name} 예외 {str(e)[:80]}")
        # 모든 요소의 제목(툴팁)을 한 번씩 훑는다 — 속성 주입은 마우스를 올려야 돈다
        injected = pg.evaluate("""() => {
          const bad = [];
          for (const el of document.querySelectorAll('*')) {
            for (const a of el.getAttributeNames()) {
              if (/^on/i.test(a) && (el.getAttribute(a) || '').includes('__xss')) {
                let p = el, path = [];
                while (p && path.length < 4) { if (p.id || p.className) path.push((p.id ? '#' + p.id : '') + (typeof p.className === 'string' && p.className ? '.' + p.className.split(' ')[0] : '')); p = p.parentElement; }
                bad.push(el.tagName + '[' + a + '] in ' + path.join(' < '));
              }
            }
          }
          return bad.slice(0, 20);
        }""")
        ran = pg.evaluate("() => window.__xss || []")
        pg.screenshot(path=str(OUT / "xss.png"))
        FOUND.append(f"열어 본 화면: {' · '.join(steps)}")
        FOUND.append(f"돈 스크립트 {ran} · DOM 에 들어간 처리기 {injected} · 페이지 오류 {errs[:3]}")
        if ran or injected:
            DEFECTS.append(f"사람이 적은 글자가 HTML 로 들어갔다 — 돈 것 {ran} · 들어간 것 {injected}")
        br.close()
finally:
    srv.terminate()
    (OUT / "README.md").write_text("# 사람이 적는 글자에 HTML\n\n결함 " + str(len(DEFECTS)) + "\n\n"
                                   + "\n".join(f"- {x}" for x in FOUND + DEFECTS) + "\n", encoding="utf-8")
    print("\n".join(FOUND + DEFECTS)); print("결함", len(DEFECTS))
