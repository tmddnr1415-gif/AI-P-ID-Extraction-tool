"""가상 광장 — 부서원이 캐릭터로 돌아다니며 말풍선으로 대화하는 작은 마을.

부서 대시보드의 '최근 변경 이력' 아래에 iframe 으로 들어간다 (`/plaza?embed=1&user=이름`).
P&ID · LOGIC 판정과 아무 관계가 없고, DB 도 파일도 쓰지 않는다 — 상태는 이 서버 프로세스의
메모리에만 있다 (서버를 다시 켜면 광장이 비고 대화도 사라진다).

길:
  GET  /plaza                  화면
  POST /plaza/api/join         {name, look} → {id, ...}
  POST /plaza/api/move         {id, x, y, dir}      (칸 좌표)
  POST /plaza/api/say          {id, text}           (최대 SAY_MAX 글자)
  POST /plaza/api/attack       {id}                 (스페이스 — 바라보는 앞 칸의 사람을 때린다)
  POST /plaza/api/leave        {id}                 (창을 닫을 때 sendBeacon)
  GET  /plaza/api/stream?id=   SSE — 바뀔 때마다 광장 전체 상태

사람이 적은 글은 화면이 textContent / canvas 글자로만 그린다 (HTML 로 넣지 않는다).
"""
from __future__ import annotations

import asyncio
import json
import re
import secrets
import threading
import time
from collections import deque
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

router = APIRouter()

STATIC = Path(__file__).resolve().parent / "static"

MAP_W, MAP_H = 56, 32        # plaza.js 의 지도 크기와 같다 (서버는 범위만 지킨다)
NAME_MAX = 20
SAY_MAX = 80
LOG_KEEP = 60
BUBBLE_S = 7.0               # 말풍선이 머리 위에 떠 있는 시간
IDLE_S = 45.0                # 이 시간 동안 소식이 없고 스트림도 없으면 광장에서 나간다
PLAYERS_MAX = 80
ATTACK_GAP_S = 0.3           # 한 번 휘두르는 시간 — 그보다 빨리 오면 무시한다
DIRV = {0: (0, 1), 1: (0, -1), 2: (-1, 0), 3: (1, 0)}   # 아래 · 위 · 왼쪽 · 오른쪽 (plaza.js 와 같다)

_LOCK = threading.Lock()
_STATE: dict = {"ver": 0, "players": {}, "log": deque(maxlen=LOG_KEEP), "seq": 0}
_CTRL = re.compile(r"[\x00-\x1f\x7f]")


def _clean(text, limit: int) -> str:
    s = _CTRL.sub(" ", str(text or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit]


def _bump() -> None:
    _STATE["ver"] += 1


def _prune(now: float) -> None:
    gone = [pid for pid, p in _STATE["players"].items()
            if p["streams"] <= 0 and now - p["seen"] > IDLE_S]
    for pid in gone:
        p = _STATE["players"].pop(pid)
        _log_system(f"{p['name']} 님이 광장을 떠났습니다.", now)
    if gone:
        _bump()


def _log_system(text: str, now: float) -> None:
    _STATE["seq"] += 1
    _STATE["log"].append({"seq": _STATE["seq"], "at": now, "name": "", "text": text, "sys": True})


def snapshot(now: float | None = None) -> dict:
    """광장 전체 — 스트림이 보내는 것과 같다 (시험이 직접 부른다)."""
    now = time.time() if now is None else now
    with _LOCK:
        _prune(now)
        players = []
        for pid, p in _STATE["players"].items():
            age = now - p["say_at"] if p["say"] else None
            players.append({
                "id": pid, "name": p["name"], "look": p["look"],
                "x": p["x"], "y": p["y"], "dir": p["dir"],
                "say": p["say"] if age is not None and age < BUBBLE_S else "",
                "say_seq": p["say_seq"],
                "act_seq": p["act_seq"], "act_age": round(now - p["act_at"], 2),
                "hit_seq": p["hit_seq"], "hit_age": round(now - p["hit_at"], 2), "hit_by": p["hit_by"],
                "say_left": round(BUBBLE_S - age, 2) if age is not None and age < BUBBLE_S else 0,
            })
        log = [{"seq": m["seq"], "name": m["name"], "text": m["text"], "sys": m["sys"],
                "at": time.strftime("%H:%M", time.localtime(m["at"]))} for m in _STATE["log"]]
        return {"ver": _STATE["ver"], "players": players, "log": log, "online": len(players)}


def reset() -> None:
    """시험용 — 광장을 비운다."""
    with _LOCK:
        _STATE["players"].clear()
        _STATE["log"].clear()
        _STATE["ver"] += 1


def _player(pid: str) -> dict:
    p = _STATE["players"].get(str(pid or ""))
    if p is None:
        raise HTTPException(404, "광장에 없는 캐릭터입니다 — 다시 들어오세요.")
    return p


@router.get("/plaza", include_in_schema=False)
def plaza_page():
    return FileResponse(STATIC / "plaza.html", headers={"Cache-Control": "no-store"})


@router.post("/plaza/api/join")
def plaza_join(body: dict):
    name = _clean((body or {}).get("name"), NAME_MAX)
    if not name:
        raise HTTPException(400, "이름을 적어 주세요.")
    try:
        look = int((body or {}).get("look") or 0) % 1000
    except (TypeError, ValueError):
        look = 0
    try:
        x = int((body or {}).get("x") or MAP_W // 2)
        y = int((body or {}).get("y") or MAP_H // 2)
    except (TypeError, ValueError):
        x, y = MAP_W // 2, MAP_H // 2
    now = time.time()
    with _LOCK:
        _prune(now)
        if len(_STATE["players"]) >= PLAYERS_MAX:
            raise HTTPException(503, "광장이 꽉 찼습니다 — 잠시 뒤에 들어오세요.")
        pid = secrets.token_hex(6)
        _STATE["players"][pid] = {
            "name": name, "look": look,
            "x": min(max(x, 0), MAP_W - 1), "y": min(max(y, 0), MAP_H - 1), "dir": 0,
            "say": "", "say_at": 0.0, "say_seq": 0, "seen": now, "streams": 0,
            "act_seq": 0, "act_at": 0.0, "hit_seq": 0, "hit_at": 0.0, "hit_by": "",
        }
        _log_system(f"{name} 님이 광장에 들어왔습니다.", now)
        _bump()
    return {"id": pid, "name": name, "look": look, "say_max": SAY_MAX}


@router.post("/plaza/api/move")
def plaza_move(body: dict):
    body = body or {}
    with _LOCK:
        p = _player(body.get("id"))
        try:
            x, y, d = int(body.get("x")), int(body.get("y")), int(body.get("dir") or 0)
        except (TypeError, ValueError):
            raise HTTPException(400, "칸 좌표는 정수입니다.")
        x, y = min(max(x, 0), MAP_W - 1), min(max(y, 0), MAP_H - 1)
        p["seen"] = time.time()
        if (x, y, d % 4) != (p["x"], p["y"], p["dir"]):
            p["x"], p["y"], p["dir"] = x, y, d % 4
            _bump()
    return {"ok": True}


@router.post("/plaza/api/say")
def plaza_say(body: dict):
    body = body or {}
    text = _clean(body.get("text"), SAY_MAX)
    if not text:
        raise HTTPException(400, "빈 말은 보내지 않습니다.")
    now = time.time()
    with _LOCK:
        p = _player(body.get("id"))
        p["say"], p["say_at"], p["seen"] = text, now, now
        p["say_seq"] += 1
        _STATE["seq"] += 1
        _STATE["log"].append({"seq": _STATE["seq"], "at": now, "name": p["name"],
                              "text": text, "sys": False})
        _bump()
    return {"ok": True, "text": text}


@router.post("/plaza/api/attack")
def plaza_attack(body: dict):
    """스페이스 — 휘두른다.  바라보는 앞 칸(또는 같은 칸)에 서 있는 사람이 맞는다."""
    now = time.time()
    with _LOCK:
        p = _player((body or {}).get("id"))
        p["seen"] = now
        if now - p["act_at"] < ATTACK_GAP_S:
            return {"ok": True, "hit": []}
        p["act_at"] = now
        p["act_seq"] += 1
        dx, dy = DIRV.get(p["dir"], (0, 1))
        front = {(p["x"] + dx, p["y"] + dy), (p["x"], p["y"])}
        hit = []
        for qid, q in _STATE["players"].items():
            if q is p or (q["x"], q["y"]) not in front:
                continue
            q["hit_seq"] += 1
            q["hit_at"], q["hit_by"] = now, p["name"]
            hit.append(q["name"])
        _bump()
    return {"ok": True, "hit": hit}


@router.post("/plaza/api/leave")
async def plaza_leave(request: Request):
    # sendBeacon 은 text/plain 으로 보내므로 본문을 직접 읽는다.
    try:
        body = json.loads((await request.body()) or b"{}")
    except ValueError:
        body = {}
    now = time.time()
    with _LOCK:
        p = _STATE["players"].pop(str(body.get("id") or ""), None)
        if p is not None:
            _log_system(f"{p['name']} 님이 광장을 떠났습니다.", now)
            _bump()
    return {"ok": True}


@router.get("/plaza/api/stream")
async def plaza_stream(request: Request, id: str = ""):
    with _LOCK:
        me = _STATE["players"].get(id)
        if me is not None:
            me["streams"] += 1

    async def gen():
        last, ticks = -1, 0
        try:
            while True:
                if await request.is_disconnected():
                    break
                ver = _STATE["ver"]
                # 말풍선이 떠 있는 동안은 1초마다 다시 보내 남은 시간이 줄어든다
                bubbling = any(p["say"] and time.time() - p["say_at"] < BUBBLE_S + 1
                               for p in list(_STATE["players"].values()))
                if ver != last or (bubbling and ticks % 12 == 0):
                    last = ver
                    data = json.dumps(snapshot(), ensure_ascii=False)
                    yield f"data: {data}\n\n"
                elif ticks % 150 == 0:
                    yield ": ping\n\n"
                ticks += 1
                await asyncio.sleep(0.08)
        finally:
            with _LOCK:
                p = _STATE["players"].get(id)
                if p is not None:
                    p["streams"] -= 1
                    p["seen"] = time.time()

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
