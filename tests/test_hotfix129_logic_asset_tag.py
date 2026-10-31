"""hotfix129 — LOGIC · DCS 화면의 스크립트·스타일 주소에 내용 딱지 · 오른쪽 아래 업데이트 이름.

hotfix127·128 뒤 "LOGIC 최신 변경이 반영 안 된 것 같다" — LOGIC 화면만 `/static/logic.js` 같은 고정 주소라
업데이트 뒤에도 브라우저가 옛 스크립트를 캐시에서 쓸 수 있었다."""
import hashlib
import json
import re

import pytest

from app import page_stamp, paths

PAGES = {"/logic": ["logic.js", "logic.css", "offline.js"],
         "/logic/draw": ["logic_draw.js", "logic_draw.css"],
         "/logic/test": ["logic_test.js", "logic_test.css"],
         "/logic/commission": ["logic_commission.js", "logic_commission.css"],
         "/logic/signal": ["logic_signal.js", "logic_signal.css"],
         "/dcs": ["hmi/hmi.js", "hmi/hmi.css"]}


def _h(rel):
    return hashlib.sha256(paths.resource("app", "static", *rel.split("/")).read_bytes()).hexdigest()[:8]


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app import main
    return TestClient(main.app)


@pytest.mark.parametrize("url", list(PAGES))
def test_page_tags_every_static_asset(client, url):
    r = client.get(url)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    for rel in PAGES[url]:
        assert f"/static/{rel}?v={_h(rel)}" in r.text, rel
    assert not re.search(r'(?:src|href)="/static/[^"?]+\.(?:js|css)"', r.text)


def test_stamp_keeps_existing_query_and_other_urls():
    html = '<script src="/static/a.js?x=1"></script><img src="/static/p.png"><a href="/logic">x</a></body>'
    assert page_stamp.stamp(html, badge=False) == html


def test_badge_shows_applied_update(monkeypatch, tmp_path):
    from app import version
    f = tmp_path / "_update.json"
    f.write_text(json.dumps({"name": "hotfix999"}), encoding="utf-8")
    monkeypatch.setattr(version, "_UPDATE", f)
    out = page_stamp.stamp("<body></body>")
    assert "업데이트 hotfix999" in out and out.count('id="pidUpdateTag"') == 1
    assert "pidUpdateTag" not in page_stamp.stamp("<body></body>", badge=False)


def test_service_worker_asks_server_first_for_screens_while_down():
    sw = paths.resource("app", "static", "sw.js").read_text(encoding="utf-8")
    assert "if (DOWN && !html)" in sw and "DOWN_TIMEOUT_MS" in sw
    assert "ignoreSearch: true }))" in sw
