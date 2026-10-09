"""hotfix50 — 부서 대시보드 안에 들어가기 (사내망 실행 · 접근 제한 · ?embed · ?user · ?mode).

사용자: *"입찰/실행 프로젝트를 누르면 하위 메뉴로 P&ID 분석이 뜨고 그 P&ID 분석은 내가 개발한
프로그램을 돌리고 싶다."*  대시보드(포트 8080 · 표준 라이브러리 서버)는 이 프로그램을 담을 수
없으므로(pip 금지) 이 서버를 iframe 으로 띄운다 — 그러려면 이쪽이 넷을 해야 한다.

  ① 사내망 주소로 연다 (`--lan` · 고정 포트) — 지금은 127.0.0.1 이라 다른 PC 가 못 들어온다
  ② 연 순간 사라지는 "루프백만" 제한을 대시보드와 같은 규칙으로 되살린다
  ③ 대시보드가 "살아 있나" 를 물을 `/version` 하나만 출처를 가리지 않는다
  ④ ?embed=1 은 이 화면의 메뉴를 숨기고, ?user · ?mode 는 이름과 새 프로젝트 종류를 미리 채운다
"""
from __future__ import annotations

import asyncio
import os
import pathlib
import re
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import lan  # noqa: E402

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")


# ---------------------------------------------------------------- ② 접근 규칙
def test_client_allowed_follows_the_dashboard_rule():
    nets = lan.allowed_networks(local=["65.3.30.234"], extra=[])
    ok = ["127.0.0.1", "::1", "10.20.30.40", "172.16.5.5", "192.168.0.7",
          "65.3.1.2", "65.3.255.254", "::ffff:65.3.9.9", "::ffff:192.168.1.1"]
    no = ["8.8.8.8", "65.4.0.1", "1.1.1.1", "", None, "testclient", "not-an-ip"]
    for h in ok:
        assert lan.client_allowed(h, nets), h
    for h in no:
        assert not lan.client_allowed(h, nets), h


def test_extra_ranges_are_read_and_bad_ones_dropped():
    nets = lan.extra_networks("65.4.0.0/16, bogus ;10.9.0.0/16,,")
    assert [str(n) for n in nets] == ["65.4.0.0/16", "10.9.0.0/16"]
    allowed = lan.allowed_networks(local=[], extra=nets)
    assert lan.client_allowed("65.4.7.7", allowed)
    assert not lan.client_allowed("65.5.7.7", allowed)


def _call(gate, host):
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(msg):
        sent.append(msg)

    scope = {"type": "http", "method": "GET", "path": "/", "headers": [],
             "client": (host, 5000) if host else None}
    asyncio.run(gate(scope, receive, send))
    return sent


def test_gate_only_checks_in_lan_mode(monkeypatch):
    reached = []

    async def inner(scope, receive, send):
        reached.append(scope["client"])
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    gate = lan.Gate(inner, nets=lan.allowed_networks(local=["65.3.30.234"], extra=[]))
    monkeypatch.delenv(lan.ENV_ON, raising=False)
    # 꺼져 있으면(127.0.0.1 로 연 예전 실행) 아무것도 보지 않는다 — 가짜 주소도 통과
    assert _call(gate, "testclient")[0]["status"] == 200
    monkeypatch.setenv(lan.ENV_ON, "1")
    assert _call(gate, "65.3.40.1")[0]["status"] == 200
    assert _call(gate, "10.0.0.5")[0]["status"] == 200
    out = _call(gate, "8.8.8.8")
    assert out[0]["status"] == 403
    assert "사내망에서만" in out[1]["body"].decode("utf-8")
    assert _call(gate, None)[0]["status"] == 403
    assert len(reached) == 3


# ---------------------------------------------------------------- ③ /version 만 출처를 가리지 않는다
def test_only_version_answers_other_origins(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    monkeypatch.delenv(lan.ENV_ON, raising=False)
    for mod in [m for m in list(sys.modules) if m.startswith("app")]:
        del sys.modules[mod]
    from fastapi.testclient import TestClient
    from app import main
    c = TestClient(main.app)
    v = c.get("/version", headers={"Origin": "null"})
    assert v.status_code == 200 and "version" in v.json()
    assert v.headers.get("access-control-allow-origin") == "*"
    p = c.get("/projects", headers={"Origin": "http://dash:8080"})
    assert p.status_code == 200
    assert "access-control-allow-origin" not in p.headers
    # 사내망 모드에서 바깥 주소는 /version 도 못 받는다 (문지기가 앞에 선다)
    monkeypatch.setenv(lan.ENV_ON, "1")
    far = TestClient(main.app, client=("8.8.8.8", 1234))
    assert far.get("/version").status_code == 403
    near = TestClient(main.app, client=("10.1.2.3", 1234))
    assert near.get("/version").status_code == 200


# ---------------------------------------------------------------- ① 실행기
def test_launchers_open_on_the_lan_only_when_asked():
    bat = (ROOT / "start.bat").read_text(encoding="utf-8")
    sh = (ROOT / "run.sh").read_text(encoding="utf-8")
    desk = (ROOT / "app/desktop.py").read_text(encoding="utf-8")
    assert "set HOST=127.0.0.1" in bat and '"%%a"=="--lan"' in bat and "--host %HOST%" in bat
    assert "HOST=127.0.0.1" in sh and "--lan) HOST=0.0.0.0; export PID_LAN=1" in sh
    assert '--host "$HOST"' in sh
    # exe: 사내망이면 포트를 고정한다 (대시보드가 적어 둔 주소 — 빈 포트를 고르지 않는다)
    assert 'port_arg = port_arg or "8000"' in desk
    assert "uvicorn.run(app, host=host" in desk
    assert 'os.environ["PID_LAN"] = "1"' in desk


def test_service_scripts_never_kill_python_wholesale():
    # 대시보드 서버도 python 이다 — 일괄 종료하면 대시보드가 죽는다
    for name in ("run_lan_service.bat", "install_autostart_lan.bat",
                 "uninstall_autostart_lan.bat", "open_firewall_8000.bat"):
        src = (ROOT / name).read_bytes()
        assert b"\r\n" in src, f"{name} — cmd 의 goto 는 CRLF 에서 안전하다"
        low = src.decode("utf-8").lower()
        assert "taskkill" not in low, name
    svc = (ROOT / "run_lan_service.bat").read_text(encoding="utf-8")
    assert "--lan" in svc and "8000" in svc and "PID_NO_HOLD=1" in svc and "goto loop" in svc
    assert 'if os.environ.get("PID_NO_HOLD") == "1"' in (ROOT / "app/desktop.py").read_text(encoding="utf-8")


# ---------------------------------------------------------------- ④ 화면
def test_embed_params_are_read_once_and_only_read():
    head = JS[:JS.index("const EMBED")]
    assert "const S = {" in head                       # S 다음, 다른 무엇보다 앞
    block = JS[JS.index("const EMBED"):JS.index("})();", JS.index("const EMBED"))]
    assert 'q.get("embed") === "1"' in block
    assert 'm === "bid"' in block and '(m === "epc" || m === "run")' in block
    assert ".slice(0, 40)" in block
    tail = JS[JS.index("(function applyEmbed()"):]
    assert "rememberAuthor(EMBED.user)" in tail
    assert 'slot.appendChild(tabs)' in tail
    # 대시보드 쪽으로 무엇도 보내지 않는다 (postMessage · 다른 주소 fetch 없음)
    assert "postMessage" not in JS
    assert not re.search(r'fetch\(\s*["`]https?://', JS)


def test_first_screen_keeps_the_embed_query():
    assert 'history.replaceState(null, "", location.pathname + location.search)' in JS
    assert 'history.replaceState(null, "", location.pathname);' not in JS


def test_new_project_starts_with_the_dashboard_menus_mode():
    # hotfix60 — 이름을 적는 동안 라디오에서 고른 종류가 먼저이고, 없으면 대시보드 메뉴의 종류다.
    i = JS.index("const chosen = (modeRadio() && modeRadio().value) || EMBED.mode")
    seg = JS[i:i + 900]
    assert "/mode`" in seg and 'method: "PATCH"' in seg and "lastAuthor()" in seg
    assert seg.index("PATCH") < JS[i:].index("await loadProjects(out.name)")


def test_embed_hides_the_menu_and_moves_the_tabs():
    assert 'id="embed-tabs"' in HTML and 'id="embed-from"' in HTML
    hdr = HTML[HTML.index('<header class="head">'):HTML.index("</header>")]
    assert 'id="embed-tabs"' in hdr
    assert "body.embed #sidebar" in CSS and "body.embed .embed-tabs #tabs" in CSS
    assert re.search(r"body\.embed, body\.embed\.nav-collapsed \{ padding-left: 0; \}", CSS)
