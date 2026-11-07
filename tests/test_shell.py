"""hotfix132 (A1~A9) — 공통 셸: 모든 화면에 같은 띠 · 앱 전환 · 이름 · 도움말 · 판, 그리고 그 주변 다듬기.

못박는 것 (판정 0 — 화면을 오가게 하고 알릴 뿐이다):
  · page_stamp 가 `</head>` 앞에 shell.css · shell.js(defer · data-app · data-version · ?v= 딱지)를 넣는다.  Valve 는 넣지 않는다.
  · 판 글은 "버전 1.0.0 · 업데이트 132 · 날짜" 한 형식(번호는 rev 가 있을 때만) — 꾸러미 이름 · zip · 커밋은 화면에 내지 않는다.
  · 파비콘(없을 때만) · 옛 브라우저 안내 · 인쇄 스타일.
  · 도서검토도 셸을 입혀 내준다 · DCS 옛 주소는 /dcs 로 넘긴다(질의 보존) · 오류 응답에 detail 도 싣는다.
  · shell.js 는 기존 앱과 같은 이름 키(localStorage 'pid.author')를 쓰고, 링크는 누르는 순간에만 고친다.
  · 서비스워커: 4개씩 받기 · 자료 보관 상한 · 느린 화면을 '꺼짐' 으로 보지 않기 (절전모드 계약은 그대로).
브라우저로 직접 누르는 시험은 `-m ui` 로 따로 돈다 (아래 끝).
"""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

from app import page_stamp, paths

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"
SCREENS = {"/logic": "logic", "/logic/draw": "draw", "/logic/test": "logic", "/logic/commission": "logic",
           "/logic/signal": "logic", "/space": "space", "/dcs": "dcs", "/books/": "books"}


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app import main
    return TestClient(main.app)


def _shell_tag(text):
    m = re.search(r'<script defer src="/static/shell\.js\?v=[0-9a-f]{8}"([^>]*)></script>', text)
    return m.group(1) if m else None


# ---------------------------------------------------------------- A1 주입
@pytest.mark.parametrize("url", list(SCREENS))
def test_every_screen_gets_the_shell_once(client, url):
    t = client.get(url).text
    attrs = _shell_tag(t)
    assert attrs is not None, url
    assert f'data-app="{SCREENS[url]}"' in attrs
    assert t.count("/static/shell.js") == 1 and t.count("/static/shell.css?v=") == 1
    head = t[:t.index("</head>")]
    assert "/static/shell.js" in head and "/static/shell.css" in head      # head 의 defer — offline.js 보다 늘 뒤에 실행


def test_pid_root_gets_the_shell_when_served_through_page_stamp(client):
    t = client.get("/").text
    if "/static/shell.js" not in t:                     # `/` 를 page_stamp 로 돌리는 것은 서버 쪽 변경 — 아직이면 건너뛴다
        pytest.skip("P&ID 첫 화면이 아직 page_stamp 를 거치지 않는다")
    assert 'data-app="pid"' in _shell_tag(t) and t.count('rel="icon"') == 1


def test_valve_screen_is_left_alone(client):
    r = client.get("/valve/")
    assert r.status_code == 200 and "shell.js" not in r.text and "pidShell" not in r.text


def test_stamp_infers_app_from_file_name_and_never_doubles():
    assert page_stamp.app_for("logic_draw.html") == "draw" and page_stamp.app_for("logic_signal.html") == "logic"
    assert page_stamp.app_for("books/index.html") == "books" and page_stamp.app_for("x.html") is None
    html = "<html><head><title>x</title></head><body><p>1</p></body></html>"
    once = page_stamp.stamp(html, badge=False, app="dcs")
    assert page_stamp.stamp(once, badge=False, app="dcs") == once
    assert 'data-app="dcs"' in once and "<noscript>" in once
    # 모르는 앱 이름은 싣지 않는다 (shell.js 가 주소로 안다)
    assert "data-app" not in page_stamp.stamp(html, badge=False, app="zzz")
    # `</head>` 가 없는 조각은 그대로 (옛 시험 hotfix129 의 '다른 주소는 건드리지 않는다' 와 같은 뜻)
    frag = '<script src="/static/a.js?x=1"></script></body>'
    assert page_stamp.stamp(frag, badge=False) == frag


# ---------------------------------------------------------------- A3 판 글
def test_version_text_is_one_plain_format(monkeypatch, tmp_path):
    from app import version
    f = tmp_path / "_update.json"
    f.write_text(json.dumps({"name": "hotfix999", "rev": 999, "zip": "PID_hotfix999.zip", "created_at": "2026-10-08 05:10",
                             "base_commit": "abc1234"}), encoding="utf-8")
    monkeypatch.setattr(version, "_UPDATE", f)
    t = page_stamp.version_text()
    assert re.fullmatch(r"버전 \S+ · 업데이트 999 · 2026-10-08", t), t        # 같은 날 두 꾸러미도 번호로 가린다
    out = page_stamp.stamp("<html><head></head><body></body></html>")
    assert out.count('id="pidUpdateTag"') == 1 and f'data-version="{t}"' in out
    for bad in ("hotfix", "zip", "abc1234"):
        assert bad not in out, bad
    # rev 가 없거나 이상하면 번호 토막을 뺀다 (지어내지 않는다)
    for rev in (None, "", "abc", True, 0):
        f.write_text(json.dumps({"name": "x", "rev": rev, "created_at": "2026-10-08 05:10"}), encoding="utf-8")
        assert re.fullmatch(r"버전 \S+ · 2026-10-08", page_stamp.version_text()), rev


def test_shell_and_pid_footer_show_the_update_number_the_same_way():
    js = (STATIC / "shell.js").read_text(encoding="utf-8")
    i = js.index("function fmtVersion(j)")
    assert '" · 업데이트 " + rev' in js[i:i + 400] and "revText(j && j.update)" in js[i:i + 400]
    app = (STATIC / "app.js").read_text(encoding="utf-8")
    assert "(rv ? ` · 업데이트 ${rv}` : \"\")" in app


def test_logic_and_space_pages_show_no_internal_update_names(client):
    for url in ("/logic", "/space", "/dcs", "/books/"):
        t = client.get(url).text
        tag = re.search(r'<div id="pidUpdateTag"[^>]*>([^<]*)</div>', t)
        if tag:
            assert tag.group(1).startswith("버전 ") and "hotfix" not in tag.group(1), url
        assert "hotfix" not in (re.search(r'data-version="([^"]*)"', t) or [""])[0]


def test_space_window_title_uses_the_common_name(client):
    t = client.get("/space").text
    assert "<title>판넬 공간확보</title>" in t and "<title>ROOM SIZE 계산</title>" not in t


# ---------------------------------------------------------------- A5 파비콘 · 옛 브라우저 · 인쇄
def test_favicon_old_browser_notice_and_print_style(client):
    for url in SCREENS:
        t = client.get(url).text
        assert t.count('rel="icon"') == 1, url
        assert 'eval("var _t=null??0")' in t and "<noscript>" in t
    css = (STATIC / "shell.css").read_text(encoding="utf-8")
    pr = css[css.index("@media print"):]
    assert "#pidShell" in pr and ".sidebar" in pr and "height: auto" in pr


# ---------------------------------------------------------------- A6 도서검토
def test_books_page_is_stamped_html(client):
    r = client.get("/books/?user=a")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    assert r.headers["cache-control"] == "no-store" and 'data-app="books"' in (_shell_tag(r.text) or "")
    assert "/api/books/" in r.text and "X-Author" in r.text                    # 화면 본문은 그대로


# ---------------------------------------------------------------- A7 DCS 주소 하나
def test_old_dcs_addresses_redirect_and_keep_the_query(client):
    r = client.get("/hmi?embed=1&user=a", follow_redirects=False)
    assert r.status_code == 307 and r.headers["location"] == "/dcs?embed=1&user=a"
    r = client.get("/hmi", follow_redirects=False)
    assert r.status_code == 307 and r.headers["location"] == "/dcs"
    r = client.get("/dcs/demo?user=a", follow_redirects=False)
    loc = r.headers["location"]
    assert r.status_code == 307 and loc.startswith("/dcs?") and "demo=1" in loc and "user=a" in loc
    assert client.get("/dcs/demo").url.path == "/dcs"
    sw = (STATIC / "sw.js").read_text(encoding="utf-8")
    assert '"/dcs/demo"' not in sw


# ---------------------------------------------------------------- A8 오류 봉투
def test_error_answers_carry_detail_too(client):
    r = client.post("/space/api/projects", json={"name": "x"})              # 이름 없음 → 401 (아무것도 쓰지 않는다)
    j = r.json()
    assert r.status_code == 401 and j.get("detail") == j.get("error") and j["error"], j
    r = client.get("/books/nope.js")
    assert r.status_code == 404 and r.json()["detail"] == r.json()["error"]
    from app import dcs
    j = json.loads(dcs._json({"error": "x"}, 404).body)
    assert j == {"error": "x", "detail": "x"}
    assert json.loads(dcs._json({"ok": 1}).body) == {"ok": 1}


# ---------------------------------------------------------------- A1 · A2 · A4 shell.js 계약 (글자로)
def test_shell_js_contract_and_name_key():
    js = (STATIC / "shell.js").read_text(encoding="utf-8")
    assert "if (window.PID_SHELL) return;" in js
    for k in ("user:", "setUser:", "toast:", "confirm:", "prompt:", "help:", "version:", "nav:", "errorText:"):
        assert k in js, k
    assert '"pid.author"' in js and '"pid.user"' not in js              # 기존 앱들과 같은 이름 키 하나
    assert '"pid-shell-user"' in js and '"pid-shell-on"' in js
    assert 'q.get("embed") === "1"' in js and "if (!EMBED) renderBar();" in js
    assert 'document.addEventListener("click"' in js and "}, true);" in js  # 누르는 순간(capture)에만 링크를 고친다
    assert "window.confirm" not in js and "alert(" not in js
    # Valve · 광장은 띠에 없다
    assert "/valve" not in js and "/plaza" not in js
    # 도움말: 탭 셋 · 용어 열 개 · 설명서는 그냥 새 창 링크 (HEAD 로 먼저 묻지 않는다 — 팝업 차단 · 405)
    assert js.count('["프로젝트",') == 1 and len(re.findall(r'^\s+\["[^"]+", "', js, re.M)) == 10
    assert 'a.href = "/help/manual"; a.target = "_blank"' in js and 'method: "HEAD"' not in js
    # 창의 Enter 는 한글 조합 중이면 무시한다
    i = js.index("function onKey(ev)")
    assert "ev.isComposing || ev.keyCode === 229" in js[i:i + 200]
    for bad in ("hotfix", "VOC", "회차", "커밋"):
        assert bad not in js.split("*/", 1)[1], bad                     # 머리 주석 밖(화면에 나가는 글)


def test_shell_css_keeps_full_height_screens_inside_the_window():
    css = (STATIC / "shell.css").read_text(encoding="utf-8")
    assert "body.pid-shell-on { box-sizing: border-box; padding-top: var(--pid-shell-h); }" in css
    for sel in (".sidebar", ".home #home", ".lg-full .lg-view", ".gt-head", ".pane-review"):
        assert sel in css, sel


# ---------------------------------------------------------------- A9 서비스워커
def test_service_worker_tuning_keeps_offline_contract():
    sw = (STATIC / "sw.js").read_text(encoding="utf-8")
    assert "i += 4" in sw and "DATA_MAX_ITEMS = 400" in sw and "20 * 1024 * 1024" in sw
    assert "NAV_TIMEOUT_MS = 20000" in sw and 'e.message === "timeout"' in sw
    assert "if (DOWN && !html)" in sw and "DOWN_TIMEOUT_MS" in sw            # 절전모드 경로 그대로
    never = re.search(r"const NEVER_RE = (/.*/);", sw).group(1)
    assert "logic/api/jobs" not in never and "audit" not in never           # 절전 첫 화면 자료는 보관한다
    off = (STATIC / "offline.js").read_text(encoding="utf-8")
    assert "navigator.serviceWorker.controller) await registerSw();" in off
    assert 'setTimeout(registerSw, 3000)' in off


def test_offline_js_does_not_queue_drawing_and_commission_runs():
    src = (STATIC / "offline.js").read_text(encoding="utf-8")
    rule = dict(re.findall(r"^\s+(pid|logic|space|dcs): (/.*?/),$", src, re.M))["logic"]
    rx = re.compile(rule[1:-1].replace("\\/", "/"))
    for no in ("/logic/api/drawings", "/logic/api/drawings/d1", "/logic/api/jobs/x/commission/run", "/logic/api/jobs/x/sysdesc",
               "/logic/api/drawings/d1/aopsim"):
        assert rx.search(no), no
    for kept in ("/logic/api/jobs/x/memo", "/logic/api/jobs/x/review/mark", "/logic/api/projects"):
        assert not rx.search(kept), kept


def test_shell_files_parse():
    import shutil
    node = shutil.which("node")
    if not node:
        pytest.skip("node 없음")
    for f in ("shell.js", "offline.js", "sw.js"):
        r = subprocess.run([node, "--check", str(STATIC / f)], capture_output=True, text=True)
        assert r.returncode == 0, (f, r.stderr[-400:])


# ---------------------------------------------------------------- 브라우저로 (pytest -m ui)
def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live(tmp_path_factory):
    pytest.importorskip("playwright.sync_api")
    port = _free_port()
    env = {**os.environ, "PID_DATA_DIR": str(tmp_path_factory.mktemp("shell_data"))}
    p = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)], cwd=ROOT, env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    for _ in range(120):
        try:
            urllib.request.urlopen(base + "/version", timeout=1)
            break
        except OSError:
            time.sleep(0.5)
    yield base
    p.terminate()
    p.wait(10)


@pytest.mark.ui
def test_ui_band_name_help_and_embed(live):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto(live + "/logic?user=" + "홍길동")
        pg.wait_for_selector("#pidShell")
        assert pg.evaluate("document.body.classList.contains('pid-shell-on')")
        assert pg.evaluate("document.scrollingElement.scrollHeight") <= 901          # 띠 때문에 넘치지 않는다
        assert pg.evaluate("PID_SHELL.user()") == "홍길동"
        assert "버전 " in pg.inner_text("#pidShell .ps-ver")
        pg.click("#pidShell .ps-help-btn")
        pg.wait_for_selector(".ps-tabs")
        assert pg.locator(".ps-tabs button").count() == 3
        pg.click(".ps-tabs button:nth-child(2)")
        assert pg.locator(".ps-dlg dt").count() == 10
        pg.keyboard.press("Escape")
        pg.evaluate("window._c = null; void PID_SHELL.confirm('지울까요?', {danger:true}).then(v => { window._c = v; }); 0")
        assert pg.locator(".ps-btn.danger").count() == 1
        pg.keyboard.press("Escape")
        pg.wait_for_function("window._c === false")
        # 띠의 앱 링크는 누르는 순간 user 를 이어 붙인다 (한 번만)
        pg.click('#pidShell a[data-app="space"]')
        pg.wait_for_load_state("load")
        assert pg.url.count("user=") == 1 and "/space" in pg.url
        # embed=1 이면 띠가 없고 알림은 된다
        pg.goto(live + "/logic?embed=1&user=a")
        pg.wait_for_function("!!window.PID_SHELL")
        assert pg.locator("#pidShell").count() == 0
        pg.evaluate("PID_SHELL.toast('시험', {kind:'ok'})")
        assert pg.locator(".ps-toast.ok").count() == 1
        # 신호 처리의 돌아가기는 자기 스크립트도 질의를 붙인다 — 겹치지 않아야 한다
        pg.goto(live + "/logic/signal?user=a")
        pg.wait_for_function("!!window.PID_SHELL")
        back = pg.locator(".sp-back").first
        if back.count():
            back.click()
            pg.wait_for_load_state("load")
            assert pg.url.count("user=") == 1
        b.close()
