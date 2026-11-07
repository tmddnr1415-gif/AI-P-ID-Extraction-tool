"""hotfix129 — LOGIC · DCS 화면도 스크립트·스타일 주소에 **내용 딱지**를 붙이고, 오른쪽 아래에 이 서버의 판을 적는다.

P&ID 첫 화면(56회차 `main._asset_tag`)과 판넬 화면(hotfix126 `space.stamp_page`)은 이미 이렇게 한다.  LOGIC 화면들
(`/logic` · `/logic/draw` · `/logic/test` · `/logic/commission` · `/logic/signal`)과 DCS 화면은 `/static/logic.js` 처럼
늘 같은 주소를 불러, 꾸러미를 덮고 서버를 다시 켜도 브라우저가 캐시의 옛 스크립트로 옛 화면을 띄울 수 있었다
(hotfix127·128 뒤 "LOGIC 최신 변경이 반영 안 된 것 같다").  이제 파일이 바뀌면 주소가 바뀌어 반드시 새 파일을 받는다.

hotfix132 — 공통 셸.  `</head>` 앞에 파비콘(없을 때만) · 옛 브라우저 안내 · `shell.css` · `shell.js`(defer · data-app ·
data-version)를 넣는다.  띠가 판("버전 1.0.0 · 2026-10-08")을 보이므로 오른쪽 아래 딱지도 같은 글로 바꿨다 —
띠가 그려지면 shell.css 가 딱지를 숨기고, 대시보드 안(`?embed=1` · 띠 없음)에서만 딱지가 보인다.
내부 이름(꾸러미 이름 · zip · 커밋)은 화면에 내지 않는다.  Valve 화면에는 넣지 않는다(이 조각을 쓰지 않는다).
"""

from __future__ import annotations

import hashlib
import html as _html
import json
import re

from fastapi.responses import HTMLResponse

from app import paths

_ASSET_RE = re.compile(r'((?:src|href)=")/static/([^"?#]+\.(?:js|css))"')

# hotfix132 — 파일 이름 → 띠의 앱 (호출부를 고치지 않아도 되게 이름으로 안다)
_APP_BY_FILE = {
    "index.html": "pid",
    "logic.html": "logic", "logic_test.html": "logic", "logic_commission.html": "logic", "logic_signal.html": "logic",
    "logic_draw.html": "draw",
    "dcs.html": "dcs",
    "books/index.html": "books",
    "space/index.html": "space",
}
_APPS = {"pid", "logic", "draw", "space", "dcs", "books"}

# hotfix132 — Edge 의 IE 모드 같은 옛 브라우저면 빈 화면 대신 안내 한 줄 (ES5 로만 쓴다)
_OLD_BROWSER = ('<script>try{eval("var _t=null??0")}catch(e){document.addEventListener("DOMContentLoaded",function(){'
                'document.body.innerHTML=\'<p style="padding:40px;font:16px sans-serif">이 화면은 최신 Edge 또는 Chrome 에서 '
                '열어 주세요. (Edge 의 IE 모드라면 끄고 다시 여세요)</p>\'})}</script>')
_NOSCRIPT = ('<noscript><p style="padding:24px;font:15px sans-serif;background:#fff3cd;margin:0">이 화면은 JavaScript 가 '
             '켜져 있어야 동작합니다. 브라우저 설정에서 JavaScript 를 켜 주세요.</p></noscript>')


def _tag(rel: str) -> str:
    try:
        return hashlib.sha256(paths.resource("app", "static", *rel.split("/")).read_bytes()).hexdigest()[:8]
    except OSError:
        return "0"


def app_for(name: str | None) -> str | None:
    """hotfix132 — `app/static/<name>` 이 어느 앱 화면인가 (모르면 None — shell.js 가 주소로 안다)."""
    return _APP_BY_FILE.get((name or "").replace("\\", "/"))


def _product() -> dict:
    try:
        from app import version
        if hasattr(version, "product"):
            return version.product() or {}
    except Exception:                                                  # 못 읽으면 기본값
        pass
    try:
        d = json.loads(paths.resource("config", "product.json").read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _rev_text(rev) -> str:
    """업데이트 번호 — 정수(또는 숫자 글)일 때만.  없거나 이상하면 빈 글 (지어내지 않는다)."""
    if isinstance(rev, bool):
        return ""
    if isinstance(rev, int):
        return str(rev) if rev > 0 else ""
    r = str(rev or "").strip()
    return r if r.isdigit() and int(r) > 0 else ""


def version_text() -> str:
    """hotfix132 — 화면에 보이는 판 한 형식: `버전 1.0.0 · 업데이트 132 · 2026-11-05`.
    업데이트 번호는 `_update.json` 의 rev 가 있을 때만 · 날짜는 업데이트를 만든 날 → 없으면 프로그램 날짜."""
    try:
        from app import version
        v = str(_product().get("version") or "").strip() or str(version.info().get("version") or version.VERSION)
        u = version.update_info() or {}
        rev = _rev_text(u.get("rev"))
        d = str(u.get("created_at") or "")[:10]
        if not d:
            d = str(version.info().get("built_at") or "")[:10]
    except Exception:                                                  # 판을 못 읽으면 적지 않는다
        return ""
    return f"버전 {v}" + (f" · 업데이트 {rev}" if rev else "") + (f" · {d}" if d else "")


def badge_html(text: str | None = None) -> str:
    """오른쪽 아래 작은 판 딱지 (id 는 옛것 그대로 — 중복 주입 가드가 이 id 를 본다)."""
    text = version_text() if text is None else text
    if not text:
        return ""
    return ('<div id="pidUpdateTag" title="이 서버의 프로그램 판" style="position:fixed;right:6px;bottom:4px;'
            'font:12px/1.2 sans-serif;color:#5b6475;pointer-events:none;z-index:2">'
            f'{_html.escape(text)}</div>')


def inject_shell(html: str, app: str | None = None) -> str:
    """hotfix132 — `</head>` 앞에 공통 셸을 넣는다.  `</head>` 가 없거나 이미 들어 있으면 그대로."""
    i = html.find("</head>")
    if i < 0 or "/static/shell.js" in html:
        return html
    head = html[:i]
    bits = []
    if not re.search(r'rel="(?:shortcut )?icon"', head):
        bits.append('<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">')
    bits.append(_OLD_BROWSER)
    bits.append(f'<link rel="stylesheet" href="/static/shell.css?v={_tag("shell.css")}">')
    attrs = f' data-app="{app}"' if app in _APPS else ""
    ver = version_text()
    if ver:
        attrs += f' data-version="{_html.escape(ver, quote=True)}"'
    bits.append(f'<script defer src="/static/shell.js?v={_tag("shell.js")}"{attrs}></script>')
    html = head + "\n".join(bits) + "\n" + html[i:]
    m = re.search(r"<body\b[^>]*>", html)
    if m:
        html = html[:m.end()] + _NOSCRIPT + html[m.end():]
    return html


def stamp(html: str, badge: bool = True, app: str | None = None) -> str:
    """`/static/*.js|css` 주소마다 `?v=<내용 해시 8자>` — 이미 `?` 가 붙은 주소는 그대로 둔다.  + 공통 셸 · 판 딱지."""
    html = _ASSET_RE.sub(lambda m: f'{m.group(1)}/static/{m.group(2)}?v={_tag(m.group(2))}"', html)
    html = inject_shell(html, app)
    if badge and 'id="pidUpdateTag"' not in html and "</body>" in html:
        tag = badge_html()
        if tag:
            html = html.replace("</body>", tag + "\n</body>", 1)
    return html


def page(name: str, badge: bool = True, app: str | None = None) -> HTMLResponse:
    """`app/static/<name>` 을 딱지 붙여 돌려준다.  HTML 자체는 캐시하지 않는다 — 그 안에 딱지가 들어 있다."""
    html = paths.resource("app", "static", *name.split("/")).read_text(encoding="utf-8")
    return HTMLResponse(stamp(html, badge, app or app_for(name)), headers={"Cache-Control": "no-store"})
