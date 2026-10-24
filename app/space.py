"""판넬 공간확보 — P&ID · LOGIC 과 같은 서버(8000)의 /space 화면 · /space/api/* (hotfix106).

판넬 화면(`app/static/space/index.html`)은 대시보드 브랜치 `ccr-d82d97fa-bb3ty3` 의
`dashboard/apps/space/index.html` 을 들여온 것이고, 저장 API 는 그 대시보드 `server.py` 의
`api_space_*` 를 같은 꼴(같은 경로 · 같은 응답 · 같은 파일 구조)로 옮겼다:

  {data}/space/<프로젝트ID>/index.json        = {project, saves:[메타 …], notes:[…]}
  {data}/space/<프로젝트ID>/saves/<저장ID>.json = {meta, data}

저장은 덮어쓰지 않고 매번 새 파일 — 누가 · 언제 · 어떤 메모로 저장했는지가 그대로 이력이다.
보기는 누구나(사내망 문지기 안), 쓰기는 **이름이 있을 때만** — P&ID · LOGIC 과 같은 방식으로
대시보드가 넘긴 로그인 이름(`?user=` → 화면이 `X-Author` 머리로 보냄)을 작성자로 적는다.

대시보드 서버에 이미 저장해 둔 판넬 자료는 `POST /space/api/import_dashboard` 가 그 서버의
보기 API(GET 은 누구나)로 읽어 와 **같은 ID 로** 들인다.  이미 있는 저장본 · 노트는 건너뛰므로
여러 번 눌러도 한 벌이다.  판정·분석과 무관하다.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

from app import jsonstore, paths

router = APIRouter()

SPACE_ID_RE = re.compile(r"^[a-z0-9]{6,32}$")
SPACE_MAX = 5 * 1024 * 1024                 # 배치안 하나 최대 (판넬 수천 개도 1MB 안팎) — 대시보드와 같은 값
DASHBOARD_URL = "http://127.0.0.1:8080"     # 같은 PC 의 대시보드 서버 (가져오기 기본값)
_LOCK = threading.RLock()


class _Err(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status, self.msg = status, msg


def _root() -> Path:
    return paths.data_dir() / "space"


def _stamp() -> str:
    """브라우저 new Date().toISOString() 과 같은 형식 (UTC · 밀리초 · Z) — 대시보드 stamp() 와 같다."""
    t = dt.datetime.now(dt.timezone.utc)
    return t.strftime("%Y-%m-%dT%H:%M:%S.") + f"{t.microsecond // 1000:03d}Z"


def _new_id() -> str:
    return format(int(time.time() * 1000), "x") + os.urandom(3).hex()


def _client_id(body: dict, key: str = "id"):
    """hotfix108 — 절전모드에서 화면이 미리 정한 id.  꼴이 맞을 때만 받는다 (같은 요청을 다시 보내도 같은 id)."""
    v = body.get(key) if isinstance(body, dict) else None
    return v if isinstance(v, str) and SPACE_ID_RE.match(v) else None


def _check(pid: str, what: str = "프로젝트") -> str:
    if not SPACE_ID_RE.match(pid or ""):
        raise _Err(400, f"잘못된 {what} ID")
    return pid


def _idx_path(pid: str) -> Path:
    return _root() / _check(pid) / "index.json"


def _read(path: Path):
    return jsonstore.read(path, None)


def _idx(pid: str) -> dict:
    d = _read(_idx_path(pid))
    if not isinstance(d, dict) or not isinstance(d.get("project"), dict):
        raise _Err(404, "없는 프로젝트입니다 (다른 사람이 지웠거나 다른 서버의 프로젝트)")
    return d


def _name(v, what: str, n: int) -> str:
    v = re.sub(r"\s+", " ", str(v or "")).strip()
    if not v:
        raise _Err(400, f"{what}을(를) 적으세요")
    return v[:n]


def _author(request: Request, body: dict | None = None) -> str:
    """작성자 = 대시보드 로그인 이름.  화면이 X-Author 머리(URL 인코딩)로 보낸다."""
    raw = request.headers.get("x-author") or ""
    name = unquote(raw).strip() if raw else ""
    if not name and isinstance(body, dict):
        name = str(body.get("author") or "").strip()
    name = re.sub(r"\s+", " ", name)[:40]
    if not name:
        raise _Err(401, "이름이 없어 저장할 수 없습니다 — 대시보드에서 로그인한 뒤 이 메뉴를 다시 여세요 "
                        "(직접 열었다면 위 '작성자' 칸에 이름을 적으세요)")
    return name


def _ok(data, status: int = 200):
    return JSONResponse(data, status_code=status, headers={"Cache-Control": "no-store"})


def _guard(fn):
    try:
        return fn()
    except _Err as e:
        return _ok({"error": e.msg}, e.status)
    except jsonstore.StateFileCorrupt as e:
        return _ok({"error": str(e)}, 500)


# ---------------------------------------------------------------- 저장 함수 (대시보드 api_space_* 와 같은 일)

def projects() -> dict:
    out = []
    root = _root()
    for pid in sorted(os.listdir(root)) if root.is_dir() else []:
        d = _read(root / pid / "index.json") if SPACE_ID_RE.match(pid) else None
        if not isinstance(d, dict) or not isinstance(d.get("project"), dict):
            continue
        sv = d.get("saves") or []
        last = sv[-1] if sv else {}
        out.append({**d["project"], "saves": len(sv), "notes": len(d.get("notes") or []),
                    "lastAt": last.get("at", ""), "lastBy": last.get("by", "")})
    out.sort(key=lambda x: x.get("lastAt") or x.get("createdAt") or "", reverse=True)
    return {"projects": out}


def recent(n) -> dict:
    try:
        n = max(1, min(200, int(n or 30)))
    except (TypeError, ValueError):
        n = 30
    out = []
    root = _root()
    for pid in os.listdir(root) if root.is_dir() else []:
        d = _read(root / pid / "index.json") if SPACE_ID_RE.match(pid) else None
        if isinstance(d, dict) and isinstance(d.get("project"), dict):
            out += [{**m, "pid": pid, "pname": d["project"].get("name", "")} for m in d.get("saves") or []]
    out.sort(key=lambda m: m.get("at") or "", reverse=True)
    return {"saves": out[:n]}


def project_new(author: str, body: dict) -> dict:
    name = _name(body.get("name"), "프로젝트 이름", 60)
    want = _client_id(body)
    with _LOCK:
        for x in projects()["projects"]:
            if want and x.get("id") == want:
                return x                                   # 절전모드 보관본을 다시 보낸 것 — 이미 만들어져 있다
            if str(x.get("name", "")).lower() == name.lower():
                if body.get("replay"):
                    return x
                raise _Err(409, f'같은 이름의 프로젝트가 이미 있습니다: {x["name"]} — 목록에서 고르세요')
        pid = want or _new_id()
        proj = {"id": pid, "name": name, "createdAt": _stamp(), "createdBy": author}
        jsonstore.write(_idx_path(pid), {"project": proj, "saves": [], "notes": []}, sort_keys=False)
    return proj


def project_get(pid: str) -> dict:
    d = _idx(pid)
    return {"project": d["project"], "saves": list(reversed(d.get("saves") or [])),
            "notes": list(reversed(d.get("notes") or []))}


def save_get(pid: str, sid: str) -> dict:
    _idx(pid)
    _check(sid, "저장")
    d = _read(_root() / pid / "saves" / f"{sid}.json")
    if not d:
        raise _Err(404, "없는 저장본입니다")
    return d


def _num(v):
    return round(float(v), 1) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def save_new(author: str, pid: str, raw: bytes) -> dict:
    if len(raw) > SPACE_MAX:
        raise _Err(413, f"배치안이 너무 큽니다 ({len(raw) // 1024} KB > {SPACE_MAX // 1024 // 1024} MB)")
    try:
        b = json.loads(raw.decode("utf-8"))
    except ValueError:
        raise _Err(400, "JSON 형식 오류")
    if not isinstance(b, dict):
        raise _Err(400, "JSON 형식 오류")
    data = b.get("data")
    if (not isinstance(data, dict) or not isinstance(data.get("room"), dict)
            or not isinstance(data.get("types"), list) or not isinstance(data.get("panels"), list)):
        raise _Err(400, "배치안이 아닙니다 (room · types · panels 항목이 필요)")
    sm = b.get("sum") if isinstance(b.get("sum"), dict) else {}
    info = data.get("info") if isinstance(data.get("info"), dict) else {}
    with _LOCK:
        d = _idx(pid)
        sid = _client_id(b, "sid") or _new_id()
        if any(m.get("id") == sid for m in d.get("saves") or []):
            return next(m for m in d["saves"] if m.get("id") == sid)   # 같은 보관본을 두 번 보냈다
        meta = {"id": sid, "at": _stamp(), "by": author,
                "memo": re.sub(r"\s+", " ", str(b.get("memo") or "")).strip()[:200],
                "rev": str(info.get("rev") or "")[:20], "panels": len(data["panels"]),
                "sum": {k: _num(sm.get(k)) for k in ("envW", "envH", "recW", "recH", "spare")}}
        jsonstore.write(_root() / pid / "saves" / f"{sid}.json", {"meta": meta, "data": data},
                        indent=None, sort_keys=False)
        d.setdefault("saves", []).append(meta)
        jsonstore.write(_idx_path(pid), d, sort_keys=False)
    return meta


def note_add(author: str, pid: str, body: dict) -> dict:
    text = str(body.get("text") or "").strip()
    if not text:
        raise _Err(400, "노트 내용을 적으세요")
    with _LOCK:
        d = _idx(pid)
        nid = _client_id(body) or _new_id()
        if any(x.get("id") == nid for x in d.get("notes") or []):
            return next(x for x in d["notes"] if x.get("id") == nid)
        n = {"id": nid, "at": _stamp(), "by": author, "text": text[:2000],
             "save": str(body.get("save") or "")[:32]}
        d.setdefault("notes", []).append(n)
        jsonstore.write(_idx_path(pid), d, sort_keys=False)
    return n


def note_del(author: str, pid: str, nid: str) -> dict:
    with _LOCK:
        d = _idx(pid)
        n = next((x for x in d.get("notes") or [] if x.get("id") == nid), None)
        if not n:
            raise _Err(404, "없는 노트입니다")
        if n.get("by") != author:
            raise _Err(403, "자기가 쓴 노트만 지울 수 있습니다")
        d["notes"] = [x for x in d["notes"] if x is not n]
        jsonstore.write(_idx_path(pid), d, sort_keys=False)
    return {"status": "ok"}


# ---------------------------------------------------------------- 대시보드 서버에서 가져오기

def _fetch(base: str, path: str, timeout: float = 15.0):
    req = urllib.request.Request(base.rstrip("/") + "/api/space" + path, headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=timeout) as r:     # noqa: S310 — 같은 PC · 사내망 주소만 받는다
        return json.loads(r.read().decode("utf-8"))


def _local_base(url: str) -> str:
    url = (url or DASHBOARD_URL).strip().rstrip("/")
    m = re.match(r"^https?://([^/:]+|\[[^\]]+\])(:\d+)?$", url)
    if not m:
        raise _Err(400, "대시보드 서버 주소 꼴이 아닙니다 (예: http://127.0.0.1:8080)")
    from app import lan
    host = m.group(1).strip("[]")
    if host != "localhost" and not lan.client_allowed(host, lan.allowed_networks):
        raise _Err(400, "같은 PC 또는 사내망의 대시보드 서버만 가져올 수 있습니다")
    return url


def import_dashboard(author: str, url: str = "", fetch=None) -> dict:
    """대시보드 서버의 판넬 프로젝트 · 저장본 · 노트를 같은 ID 로 들인다.  이미 있는 것은 건너뛴다."""
    base = _local_base(url)
    get = fetch or (lambda p: _fetch(base, p))
    try:
        plist = get("/projects").get("projects") or []
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise _Err(502, f"대시보드 서버({base})에서 판넬 자료를 읽지 못했습니다 — 대시보드 서버가 켜져 있는지 확인하세요 ({e})")
    got = {"projects_new": 0, "projects_seen": 0, "saves_new": 0, "saves_seen": 0, "notes_new": 0,
           "skipped": [], "by": author, "at": _stamp(), "from": base}
    for p in plist:
        pid = str(p.get("id") or "")
        if not SPACE_ID_RE.match(pid):
            got["skipped"].append(f"ID 꼴이 아님: {pid!r}")
            continue
        try:
            remote = get("/" + pid)
        except (urllib.error.URLError, OSError, ValueError) as e:
            got["skipped"].append(f"{p.get('name') or pid}: 읽지 못함 ({e})")
            continue
        proj = remote.get("project") if isinstance(remote.get("project"), dict) else None
        if not proj:
            continue
        with _LOCK:
            cur = _read(_idx_path(pid))
            if isinstance(cur, dict) and isinstance(cur.get("project"), dict):
                got["projects_seen"] += 1
            else:
                cur = {"project": {k: proj.get(k) for k in ("id", "name", "createdAt", "createdBy")},
                       "saves": [], "notes": []}
                cur["project"]["id"] = pid
                got["projects_new"] += 1
            have = {m.get("id") for m in cur.get("saves") or []}
            # 대시보드는 최신이 앞(reversed) — 오래된 것부터 붙여야 우리 index 의 순서(오래된 → 최신)가 같다
            for m in reversed(remote.get("saves") or []):
                sid = str(m.get("id") or "")
                if not SPACE_ID_RE.match(sid):
                    continue
                if sid in have:
                    got["saves_seen"] += 1
                    continue
                try:
                    body = get(f"/{pid}/saves/{sid}")
                except (urllib.error.URLError, OSError, ValueError) as e:
                    got["skipped"].append(f"{proj.get('name')} 저장 {sid}: 읽지 못함 ({e})")
                    continue
                if not isinstance(body, dict) or not isinstance(body.get("data"), dict):
                    got["skipped"].append(f"{proj.get('name')} 저장 {sid}: 배치안이 아님")
                    continue
                jsonstore.write(_root() / pid / "saves" / f"{sid}.json",
                                {"meta": body.get("meta") or m, "data": body["data"]}, indent=None, sort_keys=False)
                cur.setdefault("saves", []).append(body.get("meta") or m)
                have.add(sid)
                got["saves_new"] += 1
            cur["saves"].sort(key=lambda m: m.get("at") or "")
            nhave = {n.get("id") for n in cur.get("notes") or []}
            for n in reversed(remote.get("notes") or []):
                if n.get("id") and n.get("id") not in nhave:
                    cur.setdefault("notes", []).append(n)
                    got["notes_new"] += 1
            cur["notes"].sort(key=lambda n: n.get("at") or "")
            jsonstore.write(_idx_path(pid), cur, sort_keys=False)
    log = _root() / "import_log.json"
    hist = _read(log) or []
    if not isinstance(hist, list):
        hist = []
    hist.append(got)
    jsonstore.write(log, hist[-200:], sort_keys=False)
    return got


# ---------------------------------------------------------------- 길

@router.get("/space")
@router.get("/space/")
def space_page():
    return FileResponse(paths.resource("app", "static", "space", "index.html"),
                        headers={"Cache-Control": "no-store"})


@router.get("/space/api/projects")
def api_projects():
    return _guard(projects)


@router.get("/space/api/recent")
def api_recent(n: int = 30):
    return _guard(lambda: recent(n))


@router.post("/space/api/projects")
async def api_project_new(request: Request):
    body = await _json(request)
    body["replay"] = bool(request.headers.get("x-offline-replay"))     # hotfix108 — 절전모드 보관본을 되보낸 것
    return _guard(lambda: project_new(_author(request, body), body))


@router.post("/space/api/import_dashboard")
async def api_import(request: Request):
    body = await _json(request)
    # 네트워크로 다른 서버를 읽으므로 이벤트 루프 밖에서 (그동안 대시보드의 /version 확인이 막히지 않게)
    return await run_in_threadpool(
        lambda: _guard(lambda: import_dashboard(_author(request, body), str(body.get("url") or ""))))


@router.get("/space/api/{pid}")
def api_project(pid: str):
    return _guard(lambda: project_get(pid))


@router.get("/space/api/{pid}/saves/{sid}")
def api_save_get(pid: str, sid: str):
    return _guard(lambda: save_get(pid, sid))


@router.post("/space/api/{pid}/saves")
async def api_save(pid: str, request: Request):
    raw = await request.body()
    return _guard(lambda: save_new(_author(request), pid, raw))


@router.post("/space/api/{pid}/notes")
async def api_note_add(pid: str, request: Request):
    body = await _json(request)
    return _guard(lambda: note_add(_author(request, body), pid, body))


@router.delete("/space/api/{pid}/notes/{nid}")
def api_note_del(pid: str, nid: str, request: Request):
    return _guard(lambda: note_del(_author(request), pid, nid))


async def _json(request: Request) -> dict:
    try:
        b = json.loads((await request.body()).decode("utf-8") or "{}")
    except ValueError:
        b = {}
    return b if isinstance(b, dict) else {}
