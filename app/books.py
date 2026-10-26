"""계장도서검토(도서 검토) — P&ID · LOGIC · 판넬과 같은 서버(8000)의 /books 화면 · /api/books/* (hotfix115).

화면(`app/static/books/`)과 공용 도서관 API(`app/books_api.py`)는 브랜치 `claude/new-session-v23o67` 의
`dashboard/apps/books/` · `dashboard/books_api.py` 를 **그대로** 들여온 것이다.  그 API 는 대시보드 `server.py` 의
요청 처리기(Handler)를 받는 꼴이라, 여기서는 그 꼴을 흉내 내는 작은 어댑터(`_H`)로 감싸 부른다 — API 코드는
한 줄도 고치지 않는다 (다음에 그쪽이 바뀌면 파일만 바꿔 넣는다).

  저장: {data}/books/config.json (도서 폴더 경로 · 관리자 · 번역 설정)
        {data}/books/index/<id>.json.gz (책 1권 색인) · index/manifest.json (목록) · tcache/ (번역 보관)

권한은 대시보드와 같은 뜻으로 맞춘다:
  운영자   = 서버 PC 에서 연 화면 (127.0.0.1 · ::1)
  부서원   = 대시보드가 넘긴 로그인 이름 (`?user=` → 화면이 X-Author 머리로 보냄) — 이름을 그대로 믿는다 (P&ID · 판넬과 같다)
  그룹장   = 이 서버에는 명단이 없다 → 폴더 · 색인은 운영자와 config.json 의 managers(본명)만
판정 · 분석과 무관하다.
"""
from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from starlette.concurrency import run_in_threadpool

from app import books_api, jsonstore, paths

router = APIRouter()
_LOCK = threading.RLock()
_STATIC_FILES = {"kb.js": "application/javascript", "vendor/pdf.min.js": "application/javascript",
                 "vendor/pdf.worker.min.js": "application/javascript"}
_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


class ApiError(Exception):
    def __init__(self, code: int, msg: str):
        super().__init__(msg)
        self.code, self.msg = code, msg


def _P(*parts) -> str:
    return str(paths.data_dir().joinpath(*parts))


def _read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    jsonstore.write(p, obj)


books_api.setup(P=_P, LOCK=_LOCK, ApiError=ApiError, read_json=_read_json, write_json=_write_json)


class _H:
    """books_api.handle 이 부르는 대시보드 Handler 메서드만 흉내 낸다."""

    def __init__(self, request: Request, body: bytes):
        self.request, self.body, self.out = request, body, None

    def is_admin(self) -> bool:
        host = (self.request.client.host if self.request.client else "") or ""
        return host in _LOOPBACK

    def is_super(self) -> bool:
        return False

    def need_user(self, required: bool = True) -> dict:
        raw = self.request.headers.get("x-author") or ""
        name = re.sub(r"\s+", " ", unquote(raw)).strip()[:40] if raw else ""
        if name:
            return {"name": name}
        if required:
            raise ApiError(401, "이름이 없습니다 — 대시보드에서 로그인한 뒤 이 메뉴를 다시 여세요")
        return {}

    def json_body(self) -> dict:
        try:
            b = json.loads(self.body.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            raise ApiError(400, "JSON 형식이 아닙니다")
        if not isinstance(b, dict):
            raise ApiError(400, "JSON 객체가 아닙니다")
        return b

    def raw_body(self) -> bytes:
        return self.body

    def send(self, code, data, ctype, headers=None):
        self.out = Response(content=data, status_code=code, media_type=ctype, headers=headers or {})
        return None

    def cors(self):                       # 같은 출처에서만 쓴다 — 머리를 더하지 않는다
        return None


def _dispatch(request: Request, method: str, seg: list[str], q: dict, body: bytes):
    if method == "GET" and seg == ["file"]:          # 원본은 스트림으로 — books_api 의 wfile 길 대신 같은 검사 함수를 부른다
        r = books_api.root_dir()
        if not r:
            raise ApiError(404, "공용 도서관 폴더가 정해지지 않았습니다")
        full = books_api.safe_join(r, q.get("rel"))
        ext = os.path.splitext(full)[1].lower()
        return FileResponse(full, media_type=books_api.SUPPORTED[ext], content_disposition_type="inline",
                            filename=os.path.basename(full), headers={"Cache-Control": "private, max-age=300"})
    h = _H(request, body)
    res = books_api.handle(h, method, seg, q)
    if h.out is not None:
        return h.out
    return JSONResponse(res if res is not None else {"ok": True}, headers={"Cache-Control": "no-store"})


@router.api_route("/api/books/{path:path}", methods=["GET", "PUT", "POST"])
async def books_api_route(path: str, request: Request):
    seg = [s for s in path.split("/") if s]
    body = await request.body() if request.method != "GET" else b""
    q = dict(request.query_params)
    try:
        return await run_in_threadpool(_dispatch, request, request.method, seg, q, body)
    except ApiError as e:
        return JSONResponse({"error": e.msg}, status_code=e.code)


def _static(name: str) -> Path:
    return paths.resource("app", "static", "books", *name.split("/"))


@router.get("/books")
def books_redirect(request: Request):
    """화면은 kb.js · vendor/ 를 상대 주소로 읽는다 → 끝에 / 를 붙인 주소로 (질의는 그대로)."""
    qs = request.url.query
    return RedirectResponse("/books/" + (f"?{qs}" if qs else ""), status_code=307)


@router.get("/books/")
def books_page():
    return FileResponse(_static("index.html"), media_type="text/html", headers={"Cache-Control": "no-store"})


@router.get("/books/{name:path}")
def books_file(name: str):
    if name not in _STATIC_FILES:
        return JSONResponse({"error": "없는 파일"}, status_code=404)
    return FileResponse(_static(name), media_type=_STATIC_FILES[name], headers={"Cache-Control": "no-cache"})
