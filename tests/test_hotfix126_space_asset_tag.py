"""hotfix126 — 판넬 화면의 ref.js · offline.js 주소에 내용 딱지 (업데이트 뒤 옛 판이 캐시에서 나오지 않게)."""
import hashlib
import re

from app import paths, space


def test_space_page_tags_scripts_with_content_hash():
    html = paths.resource("app", "static", "space", "index.html").read_text(encoding="utf-8")
    out = space.stamp_page(html)
    ref = hashlib.sha256(paths.resource("app", "static", "space", "ref.js").read_bytes()).hexdigest()[:8]
    off = hashlib.sha256(paths.resource("app", "static", "offline.js").read_bytes()).hexdigest()[:8]
    assert f'src="/static/space/ref.js?v={ref}"' in out
    assert f'src="/static/offline.js?v={off}"' in out
    assert not re.search(r'src="/static/space/ref\.js"', out)


def test_space_route_serves_tagged_page():
    from fastapi.testclient import TestClient
    from app import main
    r = TestClient(main.app).get("/space?embed=1&user=x")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    assert "/static/space/ref.js?v=" in r.text
