"""hotfix132 (A10) — 전 화면 연기 시험: 주소마다 200 · 스크립트가 있다 · 화면이 부르는 정적 파일이 전부 200 ·
서버 오류 흔적(Traceback · Internal Server Error)이 없다 · Valve 에는 공통 띠를 넣지 않는다.

딱지(?v=) 자체는 hotfix126 · hotfix129 시험이 본다 — 여기서는 되풀이하지 않는다.
브라우저로 콘솔 오류까지 보는 눈 점검은 `spike/smoke_screens.js` (서버를 띄우고 node 로)."""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit

import pytest

URLS = ["/", "/logic", "/logic/draw", "/logic/test", "/logic/commission", "/logic/signal", "/space", "/space?view=3d",
        "/dcs", "/dcs/demo", "/hmi", "/books/", "/valve/"]
_REF = re.compile(r'(?:src|href)="([^"#]+\.(?:js|css)(?:\?[^"]*)?)"')


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app import main
    return TestClient(main.app)


def _refs(page_url: str, html: str):
    """화면이 부르는 같은 출처 js · css (절대 `/static/…` 과 도서검토의 상대 주소 `kb.js` · `vendor/…`)."""
    out = set()
    for raw in _REF.findall(html):
        if raw.startswith(("http:", "https:", "//", "data:")) or "${" in raw or "+" in raw:
            continue
        out.add(urljoin(page_url, raw))
    return sorted(out)


@pytest.mark.parametrize("embed", [False, True])
@pytest.mark.parametrize("url", URLS)
def test_screen_and_its_files_load(client, url, embed):
    if embed:
        url = url + ("&" if "?" in url else "?") + "embed=1&user=%ED%99%8D%EA%B8%B8%EB%8F%99"
    r = client.get(url, follow_redirects=True)
    assert r.status_code == 200, url
    t = r.text
    assert "<script" in t, url
    assert "Traceback" not in t and "Internal Server Error" not in t, url
    final = str(r.url)
    path = urlsplit(final).path
    if path.startswith("/valve"):
        assert "pidShell" not in t and "/static/shell.js" not in t
    for ref in _refs(final, t):
        sp = urlsplit(ref)
        g = client.get(sp.path + (f"?{sp.query}" if sp.query else ""))
        assert g.status_code == 200, f"{url} → {ref} {g.status_code}"
        assert "Traceback" not in g.text[:2000]


def test_version_answers(client):
    r = client.get("/version")
    assert r.status_code == 200 and "version" in r.json()
