"""hotfix129 — LOGIC · DCS 화면도 스크립트·스타일 주소에 **내용 딱지**를 붙이고, 오른쪽 아래에 적용된 업데이트 이름을 적는다.

P&ID 첫 화면(56회차 `main._asset_tag`)과 판넬 화면(hotfix126 `space.stamp_page`)은 이미 이렇게 한다.  LOGIC 화면들
(`/logic` · `/logic/draw` · `/logic/test` · `/logic/commission` · `/logic/signal`)과 DCS 화면은 `/static/logic.js` 처럼
늘 같은 주소를 불러, 꾸러미를 덮고 서버를 다시 켜도 브라우저가 캐시의 옛 스크립트로 옛 화면을 띄울 수 있었다
(hotfix127·128 뒤 "LOGIC 최신 변경이 반영 안 된 것 같다").  이제 파일이 바뀌면 주소가 바뀌어 반드시 새 파일을 받고,
화면 오른쪽 아래 "업데이트 hotfixNNN" 으로 어느 판이 도는지 LOGIC 에서도 바로 보인다.
"""

from __future__ import annotations

import hashlib
import re

from fastapi.responses import HTMLResponse

from app import paths

_ASSET_RE = re.compile(r'((?:src|href)=")/static/([^"?#]+\.(?:js|css))"')


def _tag(rel: str) -> str:
    try:
        return hashlib.sha256(paths.resource("app", "static", *rel.split("/")).read_bytes()).hexdigest()[:8]
    except OSError:
        return "0"


def stamp(html: str, badge: bool = True) -> str:
    """`/static/*.js|css` 주소마다 `?v=<내용 해시 8자>` — 이미 `?` 가 붙은 주소는 그대로 둔다."""
    html = _ASSET_RE.sub(lambda m: f'{m.group(1)}/static/{m.group(2)}?v={_tag(m.group(2))}"', html)
    if not badge:
        return html
    try:
        from app import version
        name = (version.update_info() or {}).get("name") or ""
    except Exception:                                                  # 딱지가 없거나 못 읽으면 적지 않는다
        name = ""
    if name and 'id="pidUpdateTag"' not in html:
        tag = ('<div id="pidUpdateTag" title="이 서버에 적용된 업데이트" style="position:fixed;right:6px;bottom:4px;'
               'font:11px/1.2 sans-serif;color:#8a93a3;opacity:.75;pointer-events:none;z-index:2">'
               f'업데이트 {name}</div>')
        html = html.replace("</body>", tag + "\n</body>", 1)
    return html


def page(name: str, badge: bool = True) -> HTMLResponse:
    """`app/static/<name>` 을 딱지 붙여 돌려준다.  HTML 자체는 캐시하지 않는다 — 그 안에 딱지가 들어 있다."""
    html = paths.resource("app", "static", name).read_text(encoding="utf-8")
    return HTMLResponse(stamp(html, badge), headers={"Cache-Control": "no-store"})
