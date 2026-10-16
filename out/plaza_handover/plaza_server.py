"""가상 광장 (부여성 남쪽) — 표준 라이브러리만 쓰는 서버.

대시보드처럼 pip 없이 돈다.  P&ID 서버(app/plaza.py, FastAPI)와 **같은 길 · 같은 응답**이라
화면(static/plaza.html · plaza.js · plaza.css)은 한 글자도 안 고치고 그대로 쓴다.

    python plaza_server.py                       # http://<이 PC>:8100/plaza?embed=1&user=이름
    python plaza_server.py --port 8100 --data ./plaza_data

길:
  GET  /plaza                  화면 (static/plaza.html)
  GET  /static/plaza.js|css    화면 스크립트 · 모양
  POST /plaza/api/join         {name, look, face, x, y} → {id, name, face, role, ...}
  POST /plaza/api/move         {id, x, y, dir}
  POST /plaza/api/say          {id, text}            (80자)
  POST /plaza/api/attack       {id}                  (Space — 앞 칸 · 같은 칸 사람을 때림 · 0.3초에 한 번)
  POST /plaza/api/look         {id, look}            (얼굴 — 이름마다 looks.json 에 남음)
  POST /plaza/api/role         {id, target, role}    (운영자만)
  GET  /plaza/api/roles?id=    (운영자만)
  POST /plaza/api/leave        {id}                  (창을 닫을 때 sendBeacon — text/plain)
  GET  /plaza/api/stream?id=   SSE — 바뀔 때마다 광장 전체
  GET  /version                {"ok": true} (살아 있나 — 다른 출처 허용)

상태(사람 · 말)는 메모리에만 있다.  파일은 둘 — `<data>/roles.json` (역할 · 없으면 빈 틀) ·
`<data>/looks.json` (얼굴).  사내망(사설 주소 · 루프백) 밖에서 오면 403.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import secrets
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"

MAP_W, MAP_H = 56, 32        # plaza.js 의 지도 크기와 같다
NAME_MAX, SAY_MAX, LOG_KEEP = 20, 80, 60
BUBBLE_S, IDLE_S, PLAYERS_MAX = 7.0, 45.0, 80
ATTACK_GAP_S = 0.3
DIRV = {0: (0, 1), 1: (0, -1), 2: (-1, 0), 3: (1, 0)}       # 아래 · 위 · 왼쪽 · 오른쪽
LOOK_RANGES = {"hair": 10, "hairc": 8, "skin": 4, "eyes": 5, "beard": 4, "cloth": 12, "pants": 6}
ROLES = ("member", "unit", "leader", "operator")
ROLE_KEYS = {"leader": "group_leader", "unit": "unit_leaders", "operator": "operators"}
ROLE_TEMPLATE = {
    "_설명": "가상 광장 역할.  이름은 대시보드 로그인 이름 그대로.  group_leader = 왕관 · unit_leaders = 사모(날개 관모) · "
             "operators = 노비 차림.  적지 않은 사람은 부서원(관모).  운영자는 광장의 '역할 지정' 판에서 바꿀 수 있다.",
    "group_leader": [], "unit_leaders": [], "operators": [],
}

DATA = HERE / "plaza_data"
LOCK = threading.Lock()
FILE_LOCK = threading.Lock()
STATE: dict = {"ver": 0, "players": {}, "log": deque(maxlen=LOG_KEEP), "seq": 0}
_CTRL = re.compile(r"[\x00-\x1f\x7f]")


class ApiError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status, self.detail = status, detail


# ── 글 · 파일 ───────────────────────────────────────────────────────────
def clean(text, limit: int) -> str:
    s = _CTRL.sub(" ", str(text or ""))
    return re.sub(r"\s+", " ", s).strip()[:limit]


def read_json(path: Path, default):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, type(default)) else default
    except (OSError, ValueError):
        return default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp{os.getpid()}-{threading.get_ident()}")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    for attempt in range(6):                       # Windows 에서 다른 프로그램이 잠깐 잡고 있으면 몇 번 더
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(0.05 * (attempt + 1))


_ROLE_CACHE: dict = {"mtime": None, "data": None}


def roles() -> dict:
    f = DATA / "roles.json"
    if not f.exists():
        try:
            write_json(f, ROLE_TEMPLATE)
        except OSError:
            return {k: [] for k in ROLE_KEYS.values()}
    try:
        mt = f.stat().st_mtime
    except OSError:
        mt = None
    if mt is not None and mt == _ROLE_CACHE["mtime"] and _ROLE_CACHE["data"] is not None:
        return _ROLE_CACHE["data"]
    raw = read_json(f, {})
    data = {k: [clean(n, NAME_MAX) for n in (raw.get(k) or []) if clean(n, NAME_MAX)] for k in ROLE_KEYS.values()}
    _ROLE_CACHE.update(mtime=mt, data=data)
    return data


def role_of(name: str) -> str:
    r = roles()
    for role in ("leader", "unit", "operator"):
        if name in r[ROLE_KEYS[role]]:
            return role
    return "member"


def set_role(name: str, role: str) -> None:
    with FILE_LOCK:
        r = {k: [n for n in v if n != name] for k, v in roles().items()}
        if role in ROLE_KEYS:
            r[ROLE_KEYS[role]].append(name)
        raw = read_json(DATA / "roles.json", {})
        write_json(DATA / "roles.json", {**ROLE_TEMPLATE, **raw, **r})
        _ROLE_CACHE["mtime"] = None


def clean_look(look):
    if not isinstance(look, dict):
        return None
    out = {}
    for k, n in LOOK_RANGES.items():
        try:
            out[k] = int(look.get(k)) % n
        except (TypeError, ValueError):
            return None
    return out


def saved_look(name: str):
    return clean_look(read_json(DATA / "looks.json", {}).get(name))


def save_look(name: str, look: dict) -> None:
    with FILE_LOCK:
        data = read_json(DATA / "looks.json", {})
        data[name] = look
        write_json(DATA / "looks.json", data)


# ── 광장 상태 ──────────────────────────────────────────────────────────
def log_system(text: str, now: float) -> None:
    STATE["seq"] += 1
    STATE["log"].append({"seq": STATE["seq"], "at": now, "name": "", "text": text, "sys": True})


def prune(now: float) -> None:
    gone = [pid for pid, p in STATE["players"].items() if p["streams"] <= 0 and now - p["seen"] > IDLE_S]
    for pid in gone:
        log_system(f"{STATE['players'].pop(pid)['name']} 님이 광장을 떠났습니다.", now)
    if gone:
        STATE["ver"] += 1


def snapshot(now: float | None = None) -> dict:
    now = time.time() if now is None else now
    with LOCK:
        prune(now)
        players = []
        for pid, p in STATE["players"].items():
            age = now - p["say_at"] if p["say"] else None
            live = age is not None and age < BUBBLE_S
            players.append({
                "id": pid, "name": p["name"], "look": p["look"], "face": p["face"], "role": p["role"],
                "x": p["x"], "y": p["y"], "dir": p["dir"],
                "say": p["say"] if live else "", "say_seq": p["say_seq"], "say_left": round(BUBBLE_S - age, 2) if live else 0,
                "act_seq": p["act_seq"], "act_age": round(now - p["act_at"], 2),
                "hit_seq": p["hit_seq"], "hit_age": round(now - p["hit_at"], 2), "hit_by": p["hit_by"],
            })
        log = [{"seq": m["seq"], "name": m["name"], "text": m["text"], "sys": m["sys"],
                "at": time.strftime("%H:%M", time.localtime(m["at"]))} for m in STATE["log"]]
        return {"ver": STATE["ver"], "players": players, "log": log, "online": len(players)}


def player(pid) -> dict:
    p = STATE["players"].get(str(pid or ""))
    if p is None:
        raise ApiError(404, "광장에 없는 캐릭터입니다 — 다시 들어오세요.")
    return p


def api_join(body: dict) -> dict:
    name = clean(body.get("name"), NAME_MAX)
    if not name:
        raise ApiError(400, "이름을 적어 주세요.")
    try:
        look = int(body.get("look") or 0) % 1000
    except (TypeError, ValueError):
        look = 0
    try:
        x, y = int(body.get("x") or MAP_W // 2), int(body.get("y") or MAP_H // 2)
    except (TypeError, ValueError):
        x, y = MAP_W // 2, MAP_H // 2
    face, role, now = saved_look(name) or clean_look(body.get("face")), role_of(name), time.time()
    with LOCK:
        prune(now)
        if len(STATE["players"]) >= PLAYERS_MAX:
            raise ApiError(503, "광장이 꽉 찼습니다 — 잠시 뒤에 들어오세요.")
        pid = secrets.token_hex(6)
        STATE["players"][pid] = {
            "name": name, "look": look, "face": face, "role": role,
            "x": min(max(x, 0), MAP_W - 1), "y": min(max(y, 0), MAP_H - 1), "dir": 0,
            "say": "", "say_at": 0.0, "say_seq": 0, "seen": now, "streams": 0,
            "act_seq": 0, "act_at": 0.0, "hit_seq": 0, "hit_at": 0.0, "hit_by": "",
        }
        log_system(f"{name} 님이 광장에 들어왔습니다.", now)
        STATE["ver"] += 1
    return {"id": pid, "name": name, "look": look, "face": face, "role": role, "say_max": SAY_MAX}


def api_move(body: dict) -> dict:
    with LOCK:
        p = player(body.get("id"))
        try:
            x, y, d = int(body.get("x")), int(body.get("y")), int(body.get("dir") or 0)
        except (TypeError, ValueError):
            raise ApiError(400, "칸 좌표는 정수입니다.")
        x, y = min(max(x, 0), MAP_W - 1), min(max(y, 0), MAP_H - 1)
        p["seen"] = time.time()
        if (x, y, d % 4) != (p["x"], p["y"], p["dir"]):
            p["x"], p["y"], p["dir"] = x, y, d % 4
            STATE["ver"] += 1
    return {"ok": True}


def api_say(body: dict) -> dict:
    text = clean(body.get("text"), SAY_MAX)
    if not text:
        raise ApiError(400, "빈 말은 보내지 않습니다.")
    now = time.time()
    with LOCK:
        p = player(body.get("id"))
        p["say"], p["say_at"], p["seen"] = text, now, now
        p["say_seq"] += 1
        STATE["seq"] += 1
        STATE["log"].append({"seq": STATE["seq"], "at": now, "name": p["name"], "text": text, "sys": False})
        STATE["ver"] += 1
    return {"ok": True, "text": text}


def api_attack(body: dict) -> dict:
    now = time.time()
    with LOCK:
        p = player(body.get("id"))
        p["seen"] = now
        if now - p["act_at"] < ATTACK_GAP_S:
            return {"ok": True, "hit": []}
        p["act_at"] = now
        p["act_seq"] += 1
        dx, dy = DIRV.get(p["dir"], (0, 1))
        front = {(p["x"] + dx, p["y"] + dy), (p["x"], p["y"])}
        hit = []
        for q in STATE["players"].values():
            if q is not p and (q["x"], q["y"]) in front:
                q["hit_seq"] += 1
                q["hit_at"], q["hit_by"] = now, p["name"]
                hit.append(q["name"])
        STATE["ver"] += 1
    return {"ok": True, "hit": hit}


def api_look(body: dict) -> dict:
    face = clean_look(body.get("look"))
    if face is None:
        raise ApiError(400, "외형 값을 읽지 못했습니다.")
    with LOCK:
        p = player(body.get("id"))
        p["face"], p["seen"] = face, time.time()
        name = p["name"]
        STATE["ver"] += 1
    save_look(name, face)
    return {"ok": True, "face": face}


def need_operator(pid) -> dict:
    with LOCK:
        p = player(pid)
    if role_of(p["name"]) != "operator":
        raise ApiError(403, "운영자만 역할을 바꿀 수 있습니다.")
    return p


def api_role(body: dict) -> dict:
    me = need_operator(body.get("id"))
    target, role = clean(body.get("target"), NAME_MAX), str(body.get("role") or "")
    if not target or role not in ROLES:
        raise ApiError(400, "이름과 역할(member · unit · leader · operator)을 주세요.")
    set_role(target, role)
    label = {"member": "부서원", "unit": "유닛장", "leader": "그룹장", "operator": "운영자"}[role]
    now = time.time()
    with LOCK:
        for q in STATE["players"].values():
            if q["name"] == target:
                q["role"] = role
        log_system(f"{me['name']} 님이 {target} 님을 {label}(으)로 정했습니다.", now)
        STATE["ver"] += 1
    return {"ok": True, "roles": roles()}


def api_leave(body: dict) -> dict:
    now = time.time()
    with LOCK:
        p = STATE["players"].pop(str(body.get("id") or ""), None)
        if p is not None:
            log_system(f"{p['name']} 님이 광장을 떠났습니다.", now)
            STATE["ver"] += 1
    return {"ok": True}


POSTS = {"/plaza/api/join": api_join, "/plaza/api/move": api_move, "/plaza/api/say": api_say,
         "/plaza/api/attack": api_attack, "/plaza/api/look": api_look, "/plaza/api/role": api_role,
         "/plaza/api/leave": api_leave}
FILES = {"/plaza": ("plaza.html", "text/html; charset=utf-8"),
         "/static/plaza.js": ("plaza.js", "text/javascript; charset=utf-8"),
         "/static/plaza.css": ("plaza.css", "text/css; charset=utf-8")}


def allowed(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host.split("%")[0])
    except ValueError:
        return False
    if getattr(ip, "ipv4_mapped", None):
        ip = ip.ipv4_mapped
    return ip.is_loopback or ip.is_private or ip.is_link_local


class Handler(BaseHTTPRequestHandler):
    server_version = "PlazaServer/1"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):            # 조용히 — 걸음마다 한 줄씩 찍히면 창이 넘친다
        pass

    def _send(self, status: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, data, extra: dict | None = None) -> None:
        self._send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json", extra)

    def _gate(self) -> bool:
        if allowed(self.client_address[0]):
            return True
        self._json(403, {"detail": "사내망에서만 열립니다."})
        return False

    def do_GET(self):
        if not self._gate():
            return
        url = urlparse(self.path)
        q = parse_qs(url.query)
        if url.path == "/version":
            return self._json(200, {"ok": True, "app": "plaza"}, {"Access-Control-Allow-Origin": "*"})
        if url.path in FILES:
            name, ctype = FILES[url.path]
            try:
                return self._send(200, (STATIC / name).read_bytes(), ctype)
            except OSError:
                return self._json(404, {"detail": f"{name} 이 없습니다."})
        if url.path == "/plaza/api/roles":
            try:
                need_operator((q.get("id") or [""])[0])
                return self._json(200, roles())
            except ApiError as e:
                return self._json(e.status, {"detail": e.detail})
        if url.path == "/plaza/api/stream":
            return self._stream((q.get("id") or [""])[0])
        self._json(404, {"detail": "없는 길입니다."})

    def do_POST(self):
        if not self._gate():
            return
        fn = POSTS.get(urlparse(self.path).path)
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(min(n, 64 * 1024)) if n else b""
        if fn is None:
            return self._json(404, {"detail": "없는 길입니다."})
        try:
            body = json.loads(raw or b"{}")
            if not isinstance(body, dict):
                body = {}
        except ValueError:
            body = {}
        try:
            self._json(200, fn(body))
        except ApiError as e:
            self._json(e.status, {"detail": e.detail})

    def _stream(self, pid: str) -> None:
        with LOCK:
            me = STATE["players"].get(pid)
            if me is not None:
                me["streams"] += 1
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Connection", "close")
        self.end_headers()
        last, ticks = -1, 0
        try:
            while True:
                ver = STATE["ver"]
                bubbling = any(p["say"] and time.time() - p["say_at"] < BUBBLE_S + 1 for p in list(STATE["players"].values()))
                if ver != last or (bubbling and ticks % 12 == 0):
                    last = ver
                    self.wfile.write(f"data: {json.dumps(snapshot(), ensure_ascii=False)}\n\n".encode("utf-8"))
                    self.wfile.flush()
                elif ticks % 150 == 0:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                ticks += 1
                time.sleep(0.08)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        finally:
            self.close_connection = True
            with LOCK:
                p = STATE["players"].get(pid)
                if p is not None:
                    p["streams"] -= 1
                    p["seen"] = time.time()


def main(argv=None) -> None:
    global DATA
    ap = argparse.ArgumentParser(description="가상 광장 서버 (표준 라이브러리만)")
    ap.add_argument("--port", type=int, default=8100)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--data", default=str(HERE / "plaza_data"), help="roles.json · looks.json 을 둘 폴더")
    a = ap.parse_args(argv)
    DATA = Path(a.data).resolve()
    roles()                                        # 역할 파일 빈 틀을 만들어 둔다
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    srv.daemon_threads = True
    print(f"가상 광장 — http://localhost:{a.port}/plaza?embed=1&user=이름   (데이터 {DATA})", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
