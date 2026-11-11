"""3D 계측제어 화면 — `/ic3d` (세션 7 '3D 계측제어 도구 개발' 의 화면을 옮겨 온 것 · 판정과 무관).

세션 7 브랜치(`claude/practical-newton-n6bt58`)의 `app/index.html`(3D 엔진 내장 한 파일) · `app/viewer-real.html` 을
`app/static/ic3d/` 로 **옮겨 온다**(판넬 · 도서처럼 · 옮긴 커밋은 `config/release_sources.json` IC3D.imported).
세션 7 의 `app/server.py`(재무 · LLM)는 가져오지 않는다 — 화면은 서버 없이 '로컬 검색' 으로 돈다.

- 대시보드가 `http://<서버>:8000/ic3d?embed=1` 로 iframe 에 띄운다(먼저 `/version` 확인).  공통 셸(page_stamp 띠)은
  넣지 않는다 — 대시보드 안 화면이다.  파일은 고치지 않고 그대로 준다.
- `/ic3d` → `/ic3d/` (질의 그대로) — 화면이 옆 파일(`viewer-real.html`)을 상대 주소로 찾으므로 `/books` 와 같은 방식.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from app import paths

router = APIRouter()

_FILES = {"index.html", "viewer-real.html"}


def _file(name: str):
    return paths.resource("app", "static", "ic3d", name)


@router.get("/ic3d")
def ic3d_redirect(request: Request):
    qs = request.url.query
    return RedirectResponse("/ic3d/" + (f"?{qs}" if qs else ""), status_code=307)


@router.get("/ic3d/")
def ic3d_page():
    return FileResponse(_file("index.html"), media_type="text/html; charset=utf-8",
                        headers={"Cache-Control": "no-cache"})


@router.get("/ic3d/{name}")
def ic3d_file(name: str):
    if name not in _FILES:
        return JSONResponse({"error": "없는 파일", "detail": "없는 파일"}, status_code=404)
    return FileResponse(_file(name), media_type="text/html; charset=utf-8", headers={"Cache-Control": "no-cache"})
