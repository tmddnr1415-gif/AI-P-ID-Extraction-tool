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
  POST /plaza/api/attack       {id}                  (Space — 앞 칸 · 같은 칸 사람을 때림 · 0.3초에 한 번 · 맞으면 체력 -1)
  POST /plaza/api/look         {id, look}            (얼굴 — 이름마다 looks.json 에 남음)
  POST /plaza/api/role         {id, target, role}    (운영자만)
  GET  /plaza/api/roles?id=    (운영자만)
  POST /plaza/api/leave        {id}                  (창을 닫을 때 sendBeacon — text/plain)
  POST /plaza/api/status       {id, text}            (대시보드에서 지금 보는 화면 — 'P&ID 분석 중...' 등, 머리 위에 표시 · 24자)
  GET  /plaza/api/stream?id=   SSE — 바뀔 때마다 광장 전체
  GET  /version                {"ok": true} (살아 있나 — 다른 출처 허용)

상태(사람 · 말)는 메모리에만 있다.  파일은 셋 — `<data>/roles.json` (역할 · 없으면 빈 틀) ·
`<data>/looks.json` (얼굴) · `<data>/hp.json` (체력 · 이번 주차).

처치 수 (2026-10-19): 상대를 0 으로 만들면 1 — 이번 주 3명부터 [killer n], 이름은 1명부터 점점 짙은 붉은색 · 주간 마감에 0.
체력 (2026-10-16 대시보드): 모두 100 에서 시작, 한 대 맞을 때마다 1 씩 줄고 0 이 되면 유령(공격 못 함 · 안 맞음 ·
남과 겹쳐 지나감).  주간 마감(수요일 12:00, 대시보드에서 [금주 마감] 을 누르면 그때)이 지나 주차가 바뀌면 모두 100 으로
부활.  주차 계산은 대시보드 server.py `iso_week` 와 같고, [금주 마감] 은 `<data>/../_meta/state.json` 의
manualClosedWeek 로 안다 (대시보드가 띄우면 --data = 대시보드 data/plaza).  사내망(사설 주소 · 루프백) 밖에서 오면 403.

대시보드에서 (2026-10-16): 대시보드 server.py 가 이 서버를 함께 띄운다 (`--nets-file` = 대시보드가 기억하는
사내 대역 파일 data/_meta/server-nets.json · `--allow` = 대시보드 --allow 대역).  회사 대역이 사설 주소가 아니어도
(예: 165.244.x.x) 대시보드에 들어오는 부서원은 광장에도 들어온다.
"""
from __future__ import annotations

import argparse
import datetime
import ipaddress
import json
import os
import re
import secrets
import sys
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PLAZA_VERSION = '2026-10-22.3'   # 대시보드 server.py 가 이 줄을 읽어, 돌고 있는 광장 서버가 옛 판이면 바꿔 띄움
HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"

MAP_W, MAP_H = 64, 44        # plaza.js 의 지도 크기와 같다 (2026-10-19 조선 마을로 넓힘)
NAME_MAX, SAY_MAX, LOG_KEEP, STATUS_MAX = 20, 80, 60, 24
BUBBLE_S, IDLE_S, PLAYERS_MAX = 7.0, 45.0, 80
ATTACK_GAP_S = 0.3
HP_MAX = 100                 # 체력 — 맞을 때마다 1, 0 이면 유령 (주간 마감에 부활)
KILLER_AT = 3                # 이번 주에 이만큼 쓰러뜨리면 이름 앞에 [killer n] (이름 붉은색은 1명부터 점점 짙게 · 화면이 정함)
CUTOFF_WEEKDAY, CUTOFF_HOUR = 2, 12   # 대시보드 server.py 와 같은 주간 마감 (수요일 12:00)
DIRV = {0: (0, 1), 1: (0, -1), 2: (-1, 0), 3: (1, 0)}       # 아래 · 위 · 왼쪽 · 오른쪽
LOOK_RANGES = {"hair": 10, "hairc": 8, "skin": 4, "eyes": 5, "beard": 4, "cloth": 12, "pants": 6}
# 2026-10-19 고양이 기사: 종류(0 고양이 기사 · 1 사람) · 털(동물) · 갑옷 · 망토 — 예전에 저장한 얼굴엔 없으므로 없으면 0 (= 원본 고양이 기사)
LOOK_EXTRA = {"kind": 8, "fur": 6, "armor": 6, "cape": 7, "job": 5, "v": 4}   # kind 7 = EPC 안전모 직무 캐릭터 (2026-10-22 판2) · v = 얼굴 저장 판 (2 이상이면 새 기본값 옮김을 다시 하지 않음)   # job = EPC 직무 (2026-10-22: 0 계장 · 1 DCS · 2 시운전 리드 · 3 현장 기술 · 4 케이블)   # kind 2~6 = 마을 시트 캐릭터 (고양이 양반 · 팬더 학자 · 사자 무관 · 호랑이 무관 · 노비)
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
HP: dict = {"week": "", "hp": {}, "kills": {}, "dirty": False, "checked": 0.0}   # 이름 → 체력 (100 이 아닌 사람만) · 그 주차
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
    for k, n in LOOK_EXTRA.items():
        try:
            out[k] = int(look.get(k) or 0) % n
        except (TypeError, ValueError):
            out[k] = 0
    return out


def saved_look(name: str):
    return clean_look(read_json(DATA / "looks.json", {}).get(name))


def save_look(name: str, look: dict) -> None:
    with FILE_LOCK:
        data = read_json(DATA / "looks.json", {})
        data[name] = look
        write_json(DATA / "looks.json", data)


# ── 체력 · 주간 마감 부활 ──────────────────────────────────────────────
_WEEK_CACHE: dict = {"mtime": None, "closed": ""}


def manual_closed_week() -> str:
    """대시보드에서 [금주 마감] 으로 앞당겨 마감한 주차 (대시보드 data/_meta/state.json) — 없으면 ''"""
    f = DATA.parent / "_meta" / "state.json"
    try:
        mt = f.stat().st_mtime
    except OSError:
        return ""
    if mt != _WEEK_CACHE["mtime"]:
        _WEEK_CACHE.update(mtime=mt, closed=str(read_json(f, {}).get("manualClosedWeek") or ""))
    return _WEEK_CACHE["closed"]


def plaza_week(now: datetime.datetime | None = None) -> str:
    """지금 주차 — 대시보드 server.py iso_week 와 같은 규칙 (수요일 12:00 이 지나면 다음 주 · [금주 마감] 한 주는 끝난 주)"""
    now = now or datetime.datetime.now()
    wed = now.date() - datetime.timedelta(days=now.weekday() - CUTOFF_WEEKDAY)
    if now >= datetime.datetime.combine(wed, datetime.time(CUTOFF_HOUR)):
        wed += datetime.timedelta(days=7)
    closed = manual_closed_week()
    for _ in range(60):
        y, w, _d = wed.isocalendar()
        wid = f"{y}-W{w:02d}"
        if not closed or wid > closed:
            return wid
        wed += datetime.timedelta(days=7)
    return wid


def load_hp() -> None:
    raw = read_json(DATA / "hp.json", {})
    hp = {}
    for k, v in (raw.get("hp") or {}).items() if isinstance(raw.get("hp"), dict) else []:
        try:
            n = int(v)
        except (TypeError, ValueError):
            continue
        if 0 <= n < HP_MAX and clean(k, NAME_MAX):
            hp[clean(k, NAME_MAX)] = n
    kills = {}
    for k, v in (raw.get("kills") or {}).items() if isinstance(raw.get("kills"), dict) else []:
        try:
            n = int(v)
        except (TypeError, ValueError):
            continue
        if n > 0 and clean(k, NAME_MAX):
            kills[clean(k, NAME_MAX)] = min(n, 9999)
    HP.update(week=str(raw.get("week") or ""), hp=hp, kills=kills, dirty=False, checked=0.0)


def check_week(now: float, force: bool = False) -> None:
    """주차가 바뀌었으면(주간 마감) 모두 부활 — LOCK 안에서 부름 · 5초에 한 번만 봄"""
    if not force and now - HP["checked"] < 5:
        return
    HP["checked"] = now
    week = plaza_week()
    if week == HP["week"]:
        return
    first = not HP["week"]
    revived = sum(1 for v in HP["hp"].values() if v <= 0)
    HP.update(week=week, hp={}, kills={}, dirty=True)   # 처치 수도 주마다 새로
    items_new_week(now)                                 # 바닥 아이템 치우고 빈 가방은 새로 채움
    if not first:
        log_system(f"주간 마감 — 새 주차 {week}. 모두 체력 {HP_MAX} 으로 돌아왔습니다." + (f" (유령 {revived}명 부활)" if revived else ""), now)
        STATE["ver"] += 1


def hp_of(name: str) -> int:
    return HP["hp"].get(name, HP_MAX)


def hp_p(p: dict) -> int:                          # 광장에 있는 사람의 체력 — 운영자는 무적(늘 가득)
    return HP_MAX if p.get("role") == "operator" else hp_of(p["name"])


def save_hp() -> None:
    with LOCK:
        if not HP["dirty"]:
            return
        data = {"week": HP["week"], "hp": dict(HP["hp"]), "kills": dict(HP["kills"]),
                "_설명": f"계장 광장 체력 (이름 → 남은 체력, 없으면 {HP_MAX}). 0 = 유령. kills = 이번 주에 쓰러뜨린 수. "
                         f"주차가 바뀌면(주간 마감) 모두 {HP_MAX} 으로 부활 · kills 0."}
        HP["dirty"] = False
    try:
        with FILE_LOCK:
            write_json(DATA / "hp.json", data)
    except OSError:
        with LOCK:
            HP["dirty"] = True


def hp_loop() -> None:                             # 1초마다 회복 오라 · 2초마다 저장 · 15초마다 설비 · 30초마다 주간 마감(부활) 확인
    n = 0
    while True:
        time.sleep(1)
        n += 1
        with LOCK:
            heal_tick(time.time())
            if n % EQ_BREAK_S == 0:
                eq_tick(time.time())
            if n % 30 == 0:
                check_week(time.time(), force=True)
        if n % 2 == 0:
            save_hp()
            save_xp()
            save_items()


# ── EPC 발전플랜트 (2026-10-22): 계장 설비 · 점검/수리 · 경험치 · 유닛장 회복 오라 ─────────────
# 모든 값은 광장 안의 놀이일 뿐 — 실제 DCS · 계장 설비와는 아무 연결이 없다.
HEAL_ROLES = ("unit",)          # 회복 오라를 내는 역할 (유닛장 = 시운전 리드)
HEAL_RADIUS = 4.0               # 칸 (가운데에서 거리)
HEAL_PER_SEC = 1                # 1초마다 체력 +1 (최대 HP_MAX, 유령은 회복 안 됨 — 부활은 주간 마감)
EQ_MAX_BAD = 7                  # 동시에 '경고 · 고장' 인 설비 수 상한
EQ_BREAK_S = 15                 # 이만큼마다 정상 설비 하나가 경고로 바뀔 수 있음 (확률 1/2)
EQ_WARN_TO_FAULT_S = 180        # 경고를 이만큼 두면 고장
JOBS = ("계장 엔지니어", "DCS 엔지니어", "시운전 리드", "현장 기술자", "케이블 기술자")
JOB_CATS = {0: {"PT", "DPT", "TT", "FT", "LT", "PG"}, 1: {"DCS", "IO", "PLC", "CON", "MC"}, 3: {"CV", "PT", "TT", "PG", "FT"}, 4: {"JB", "TRAY", "MC"}}
WORK = {"ok": ("loop", 3.0, 5, "Loop Check"), "warn": ("calib", 5.0, 10, "교정"), "fault": ("repair", 7.0, 20, "수리")}
# 설비 (plaza.js 지도와 같은 칸) — id · 종류 · 칸 x · y · 폭 · 이름
EQUIP = [
    ("PT-101", "PT", 6, 10, 1, "보일러 급수 압력 전송기"), ("TT-102", "TT", 11, 10, 1, "주증기 온도 전송기"), ("FT-103", "FT", 16, 10, 1, "급수 유량계"),
    ("CV-104", "CV", 24, 10, 1, "터빈 바이패스 제어밸브"),
    ("CV-201", "CV", 37, 6, 1, "냉각수 펌프 토출 제어밸브"), ("PT-202", "PT", 41, 6, 1, "냉각수 헤더 압력 전송기"), ("FT-203", "FT", 45, 6, 1, "냉각수 유량계"),
    ("TT-204", "TT", 47, 8, 1, "열교환기 출구 온도 전송기"), ("LT-205", "LT", 50, 10, 1, "냉각탑 수조 레벨 전송기"),
    ("JB-151", "JB", 12, 15, 1, "랙 정션 박스 JB-151"), ("TRAY-152", "TRAY", 26, 15, 1, "계장 케이블 트레이 구간 A"),
    ("JB-153", "JB", 40, 15, 1, "랙 정션 박스 JB-153"), ("TRAY-154", "TRAY", 52, 15, 1, "계장 케이블 트레이 구간 B"),
    ("JB-301", "JB", 14, 29, 1, "전기실 정션 박스"), ("MC-302", "MC", 16, 29, 1, "마샬링 캐비닛 MC-302"),
    ("CON-401", "CON", 22, 26, 2, "DCS 운전 콘솔 1"), ("CON-402", "CON", 25, 26, 2, "DCS 운전 콘솔 2"),
    ("DCS-403", "DCS", 21, 30, 1, "DCS 컨트롤러"), ("IO-404", "IO", 22, 30, 1, "I/O 모듈 캐비닛"), ("PLC-405", "PLC", 27, 30, 1, "보조설비 PLC"),
    ("PT-501", "PT", 35, 25, 1, "시운전 시험 압력 전송기"), ("DPT-502", "DPT", 38, 25, 1, "차압 전송기 (유량)"), ("TT-503", "TT", 41, 25, 1, "시험 온도 전송기"),
    ("CV-504", "CV", 44, 25, 1, "시험 제어밸브 (포지셔너)"), ("LT-505", "LT", 36, 29, 1, "시험 레벨 전송기"), ("FT-506", "FT", 40, 29, 1, "시험 유량계"),
    ("JB-601", "JB", 49, 25, 1, "정비동 정션 박스"), ("PG-602", "PG", 51, 25, 1, "압력계 (교정 대기)"),
]
EQ: dict = {}                    # id → {st: ok|warn|fault, since, busy(이름), busy_at}
XP: dict = {"xp": {}, "dirty": False}   # 이름 → 경험치 (주간 마감과 상관없이 계속 쌓임, <data>/xp.json)


def level_of(xp: int) -> int:
    return int((max(0, xp) / 25) ** 0.5) + 1          # 25 XP → Lv2 · 100 → Lv3 · 225 → Lv4 …


def eq_init() -> None:
    import random
    r = random.Random(int(time.time()) // 86400)
    now = time.time()
    for e in EQUIP:
        EQ[e[0]] = {"st": "ok", "since": now, "busy": "", "busy_at": 0.0}
    ids = [e[0] for e in EQUIP]
    for i in r.sample(ids, 6):                          # 처음부터 할 일이 있게 — 경고 4 · 고장 2
        EQ[i]["st"] = "warn" if sum(1 for v in EQ.values() if v["st"] != "ok") < 4 else "fault"
    XP["xp"] = {clean(k, NAME_MAX): int(v) for k, v in read_json(DATA / "xp.json", {}).get("xp", {}).items()
                if isinstance(v, (int, float)) and clean(k, NAME_MAX)}


def eq_tick(now: float) -> None:                   # LOCK 안에서 — 경고 → 고장, 가끔 새 경고
    import random
    changed = False
    for v in EQ.values():
        if v["busy"] and now - v["busy_at"] > 30:
            v["busy"] = ""
        if v["st"] == "warn" and now - v["since"] > EQ_WARN_TO_FAULT_S and not v["busy"]:
            v["st"], v["since"], changed = "fault", now, True
    bad = sum(1 for v in EQ.values() if v["st"] != "ok")
    if bad < EQ_MAX_BAD and random.random() < .5:
        ok = [k for k, v in EQ.items() if v["st"] == "ok" and not v["busy"]]
        if ok:
            k = random.choice(ok)
            EQ[k].update(st="warn", since=now)
            changed = True
    if changed:
        STATE["ver"] += 1


def job_of(p: dict) -> int:
    if p.get("role") in HEAL_ROLES:
        return 2
    try:
        j = int((p.get("face") or {}).get("job", 0)) % len(JOBS)
    except (TypeError, ValueError):
        j = 0
    return 0 if j == 2 else j


def eq_near(p: dict, e) -> bool:
    _, _, ex, ey, w, _ = e
    return any(max(abs(p["x"] - (ex + i)), abs(p["y"] - ey)) <= 1 for i in range(w))


def heal_tick(now: float) -> None:                 # LOCK 안에서 — 유닛장 둘레 HEAL_RADIUS 칸 안 팀원 체력 +HEAL_PER_SEC
    healers = [p for p in STATE["players"].values() if p.get("role") in HEAL_ROLES and hp_p(p) > 0]
    if not healers:
        return
    done = set()
    for q in STATE["players"].values():
        name = q["name"]
        if name in done or hp_p(q) <= 0 or hp_p(q) >= HP_MAX:
            continue
        if any(h is not q and h["name"] != name and ((h["x"] - q["x"]) ** 2 + (h["y"] - q["y"]) ** 2) ** .5 <= HEAL_RADIUS for h in healers):
            done.add(name)
            v = min(HP_MAX, hp_of(name) + HEAL_PER_SEC)
            if v >= HP_MAX:
                HP["hp"].pop(name, None)
            else:
                HP["hp"][name] = v
            HP["dirty"] = True
            for r in STATE["players"].values():
                if r["name"] == name:
                    r["heal_seq"] = r.get("heal_seq", 0) + 1
                    r["heal_at"] = now
    if done:
        STATE["ver"] += 1


def save_xp() -> None:
    with LOCK:
        if not XP["dirty"]:
            return
        data = {"xp": dict(XP["xp"]), "_설명": "계장 광장 경험치 (이름 → XP). 설비 점검 · 교정 · 수리로 쌓임. 레벨 = sqrt(XP/25)+1."}
        XP["dirty"] = False
    try:
        with FILE_LOCK:
            write_json(DATA / "xp.json", data)
    except OSError:
        with LOCK:
            XP["dirty"] = True


# ── 아이템 (2026-10-22 판3): 들어오면 무작위 3 개 · 쓰러지면 그 자리에 떨어뜨림 · 산 사람이 그 칸을 밟으면 주움 ──────
ITEM_NAMES = {"HART": "HART 통신기", "MULTI": "멀티미터", "CALIB": "루프 교정기", "SPOOL": "케이블 드럼", "ICABLE": "계장 케이블",
              "GLAND": "케이블 글랜드", "TB": "단자대", "AIRTUBE": "에어 튜브", "IMPULSE": "임펄스 튜브", "POSITIONER": "포지셔너",
              "CALPUMP": "교정 펌프", "HELMET": "안전모", "VEST": "안전 조끼", "WRENCH": "렌치", "SCREW": "드라이버",
              "LAPTOP": "노트북", "CHECK": "점검표", "RADIO": "무전기", "PG": "압력계", "DCSCARD": "DCS 카드"}   # 그림 = EPC 시트 i_<키>
ITEM_START = 3                  # 처음(그리고 빈 가방으로 부활할 때) 받는 개수
ITEM_MAX = 8                    # 가방 칸
GROUND_MAX = 80                 # 바닥에 남는 수 상한 (넘으면 오래된 것부터 사라짐)
REVIVE_DIST = 2.5               # 운영자가 부활시킬 수 있는 거리 (칸)
ITEMS: dict = {"inv": {}, "ground": [], "seq": 0, "dirty": False}   # inv: 이름 → [키] · ground: [{id, it, x, y, at}] (<data>/items.json)


def load_items() -> None:
    raw = read_json(DATA / "items.json", {})
    inv = {}
    for k, v in (raw.get("inv") or {}).items() if isinstance(raw.get("inv"), dict) else []:
        if clean(k, NAME_MAX) and isinstance(v, list):
            inv[clean(k, NAME_MAX)] = [i for i in v if i in ITEM_NAMES][:ITEM_MAX]
    ground = []
    for g in raw.get("ground") or [] if isinstance(raw.get("ground"), list) else []:
        try:
            if g["it"] in ITEM_NAMES:
                ground.append({"id": int(g["id"]), "it": g["it"], "x": int(g["x"]) % MAP_W, "y": int(g["y"]) % MAP_H, "at": float(g.get("at") or 0)})
        except (KeyError, TypeError, ValueError):
            continue
    ITEMS.update(inv=inv, ground=ground[-GROUND_MAX:], seq=max([g["id"] for g in ground] + [0]), dirty=False)


def save_items() -> None:
    with LOCK:
        if not ITEMS["dirty"]:
            return
        data = {"inv": {k: list(v) for k, v in ITEMS["inv"].items()}, "ground": [dict(g) for g in ITEMS["ground"]],
                "_설명": "계장 광장 아이템. inv = 이름 → 가방 (처음 무작위 3 개). ground = 쓰러진 사람이 떨어뜨린 것 (밟으면 주움). 주간 마감에 바닥은 치우고 빈 가방은 새로 채움."}
        ITEMS["dirty"] = False
    try:
        with FILE_LOCK:
            write_json(DATA / "items.json", data)
    except OSError:
        with LOCK:
            ITEMS["dirty"] = True


def give_items(name: str, force: bool = False) -> None:   # LOCK 안에서 — 처음 오거나(가방 없음) force 이면서 빈 가방이면 무작위로
    import random
    have = ITEMS["inv"].get(name)
    if have is None or (force and not have):
        ITEMS["inv"][name] = random.sample(list(ITEM_NAMES), ITEM_START)
        ITEMS["dirty"] = True


def drop_items(q: dict, now: float) -> list:       # LOCK 안에서 — 가방을 그 자리 바닥에
    lost = ITEMS["inv"].get(q["name"]) or []
    for it in lost:
        ITEMS["seq"] += 1
        ITEMS["ground"].append({"id": ITEMS["seq"], "it": it, "x": q["x"], "y": q["y"], "at": now})
    del ITEMS["ground"][:-GROUND_MAX]
    ITEMS["inv"][q["name"]] = []
    ITEMS["dirty"] = True
    return list(lost)


def pick_up(p: dict, now: float) -> list:         # LOCK 안에서 — 선 칸의 아이템을 가방이 찰 때까지
    bag = ITEMS["inv"].setdefault(p["name"], [])
    got = []
    for g in [g for g in ITEMS["ground"] if (g["x"], g["y"]) == (p["x"], p["y"])]:
        if len(bag) >= ITEM_MAX:
            break
        if now - g["at"] < 0.8:                    # 떨어지는 중(그림이 튀는 동안)은 못 주움
            continue
        ITEMS["ground"].remove(g)
        bag.append(g["it"])
        got.append(g["it"])
    if got:
        ITEMS["dirty"] = True
        log_system(f"{p['name']} 님이 {' · '.join(ITEM_NAMES[i] for i in got)} 을(를) 주웠습니다.", now)
        STATE["ver"] += 1
    return got


def items_new_week(now: float) -> None:            # LOCK 안에서 (check_week)
    ITEMS["ground"].clear()
    for name in [k for k, v in ITEMS["inv"].items() if not v]:
        del ITEMS["inv"][name]
    for q in STATE["players"].values():
        give_items(q["name"])
    ITEMS["dirty"] = True


def api_revive(body: dict) -> dict:               # 운영자가 곁(REVIVE_DIST 칸 안)의 유령을 부활
    now = time.time()
    target = clean(body.get("target"), NAME_MAX)
    with LOCK:
        p = player(body.get("id"))
        p["seen"] = now
        if p.get("role") != "operator":
            raise ApiError(403, "운영자만 부활시킬 수 있습니다.")
        qs = [q for q in STATE["players"].values() if q["name"] == target]
        if not qs:
            raise ApiError(404, "광장에 없는 사람입니다.")
        if hp_of(target) > 0:
            raise ApiError(400, f"{target} 님은 유령이 아닙니다.")
        if min(((q["x"] - p["x"]) ** 2 + (q["y"] - p["y"]) ** 2) ** .5 for q in qs) > REVIVE_DIST:
            raise ApiError(400, "유령 곁(두 칸 안)으로 가서 하세요.")
        HP["hp"].pop(target, None)
        HP["dirty"] = True
        give_items(target, force=True)
        for q in qs:
            q["revive_at"], q["revive_by"] = now, p["name"]
        log_system(f"✨ 운영자 {p['name']} 님이 {target} 님을 부활시켰습니다. (체력 {HP_MAX})", now)
        STATE["ver"] += 1
    return {"ok": True, "target": target, "hp": HP_MAX}


def api_work(body: dict) -> dict:
    eid, phase, now = str(body.get("eq") or ""), str(body.get("phase") or ""), time.time()
    e = next((x for x in EQUIP if x[0] == eid), None)
    if e is None:
        raise ApiError(404, "없는 설비입니다.")
    with LOCK:
        p = player(body.get("id"))
        p["seen"] = now
        st = EQ[eid]
        if phase == "cancel":
            if p.get("work") and p["work"]["eq"] == eid:
                p.pop("work", None)
                if st["busy"] == p["name"]:
                    st["busy"] = ""
                STATE["ver"] += 1
            return {"ok": True}
        if hp_p(p) <= 0:
            raise ApiError(400, "유령은 작업할 수 없습니다 — 주간 마감 때 부활합니다.")
        if not eq_near(p, e):
            raise ApiError(400, "설비 바로 옆(한 칸 안)으로 가서 하세요.")
        job = job_of(p)
        if phase == "start":
            if st["busy"] and st["busy"] != p["name"] and now - st["busy_at"] < 30:
                raise ApiError(409, f"{st['busy']} 님이 작업 중입니다.")
            kind, need, xp, label = WORK[st["st"]]
            if e[1] in JOB_CATS.get(job, set()):
                need, xp = round(need * .6, 1), int(round(xp * 1.5))     # 내 직무의 설비 — 빨리 · 더 많이
            elif job == 2:
                need = round(need * .8, 1)                                # 시운전 리드는 무엇이든 조금 빨리
            p["work"] = {"eq": eid, "kind": kind, "need": need, "xp": xp, "label": label, "st": st["st"], "at": now}
            st["busy"], st["busy_at"] = p["name"], now
            STATE["ver"] += 1
            return {"ok": True, "kind": kind, "need": need, "label": label, "state": st["st"], "name": e[5]}
        if phase == "done":
            w = p.get("work")
            if not w or w["eq"] != eid or now - w["at"] < w["need"] - .4:
                raise ApiError(400, "작업이 아직 끝나지 않았습니다.")
            before = st["st"]
            gained = w["xp"] if before == w["st"] else WORK["ok"][2]       # 그사이 남이 고쳤으면 점검 몫만
            st.update(st="ok", since=now, busy="")
            old = XP["xp"].get(p["name"], 0)
            XP["xp"][p["name"]] = old + gained
            XP["dirty"] = True
            p.pop("work", None)
            p["cheer_at"] = now
            lv0, lv1 = level_of(old), level_of(old + gained)
            if before != "ok":
                log_system(f"{p['name']} 님이 {eid} {e[5]} {WORK[before][3]} 완료 (+{gained} XP)", now)
            if lv1 > lv0:
                log_system(f"🎉 {p['name']} 님 Lv {lv1} 달성!", now)
            STATE["ver"] += 1
            return {"ok": True, "gained": gained, "xp": old + gained, "lv": lv1, "was": before, "label": WORK[before][3], "name": e[5]}
    raise ApiError(400, "phase 는 start · done · cancel 입니다.")


def equip_defs() -> dict:
    return {"equip": [{"id": i, "t": t, "x": x, "y": y, "w": w, "name": n} for i, t, x, y, w, n in EQUIP],
            "jobs": list(JOBS), "heal_radius": HEAL_RADIUS, "heal_per_sec": HEAL_PER_SEC,
            "items": ITEM_NAMES, "revive_dist": REVIVE_DIST}


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
        check_week(now)
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
                "status": p.get("status", ""),
                "hp": hp_p(p), "hp_max": HP_MAX, "ghost": hp_p(p) <= 0, "inf": p.get("role") == "operator",
                "kills": HP["kills"].get(p["name"], 0), "killer": HP["kills"].get(p["name"], 0) >= KILLER_AT,
                "xp": XP["xp"].get(p["name"], 0), "lv": level_of(XP["xp"].get(p["name"], 0)), "job": job_of(p),
                "healer": p.get("role") in HEAL_ROLES and hp_p(p) > 0,
                "heal_seq": p.get("heal_seq", 0), "heal_age": round(now - p.get("heal_at", 0), 2),
                "cheer_age": round(now - p.get("cheer_at", 0), 2),
                "items": list(ITEMS["inv"].get(p["name"], [])), "revive_age": round(now - p.get("revive_at", 0), 2), "revive_by": p.get("revive_by", ""),
                "work": ({k: p["work"][k] for k in ("eq", "kind", "need", "label")} | {"age": round(now - p["work"]["at"], 2)}) if p.get("work") else None,
            })
        log = [{"seq": m["seq"], "name": m["name"], "text": m["text"], "sys": m["sys"],
                "at": time.strftime("%H:%M", time.localtime(m["at"]))} for m in STATE["log"]]
        eq = {k: [v["st"], v["busy"]] for k, v in EQ.items()}
        ground = [[g["id"], g["it"], g["x"], g["y"], round(now - g["at"], 2)] for g in ITEMS["ground"]]
        return {"ver": STATE["ver"], "players": players, "log": log, "online": len(players), "week": HP["week"], "eq": eq, "heal_r": HEAL_RADIUS,
                "ground": ground}


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
    ip = str(body.get("_ip") or "")                # 서버가 넣는 접속 주소 (화면이 보낸 값은 do_POST 에서 덮어씀)
    with LOCK:
        prune(now)
        # 한 PC(IP)에 캐릭터 하나 (2026-10-16 대시보드): 대시보드 창을 여러 개 열어도 같은 캐릭터를 함께 씀 · 같은 PC 에서 다른 이름으로 들어오면 그 사람으로 바뀜
        same = [pid for pid, q in STATE["players"].items() if ip and q.get("ip") == ip]
        for pid in same:
            q = STATE["players"][pid]
            if q["name"] == name:
                q["seen"] = now
                if "status" in body:
                    q["status"] = clean(body.get("status"), STATUS_MAX)
                STATE["ver"] += 1
                return {"id": pid, "name": name, "look": q["look"], "face": q["face"], "role": q["role"], "say_max": SAY_MAX,
                        "x": q["x"], "y": q["y"], "dir": q["dir"], "shared": True}
        for pid in same:
            log_system(f"{STATE['players'].pop(pid)['name']} 님이 광장을 떠났습니다.", now)
        if len(STATE["players"]) >= PLAYERS_MAX:
            raise ApiError(503, "광장이 꽉 찼습니다 — 잠시 뒤에 들어오세요.")
        pid = secrets.token_hex(6)
        STATE["players"][pid] = {
            "name": name, "look": look, "face": face, "role": role,
            "x": min(max(x, 0), MAP_W - 1), "y": min(max(y, 0), MAP_H - 1), "dir": 0,
            "say": "", "say_at": 0.0, "say_seq": 0, "seen": now, "streams": 0,
            "act_seq": 0, "act_at": 0.0, "hit_seq": 0, "hit_at": 0.0, "hit_by": "",
            "status": clean(body.get("status"), STATUS_MAX), "ip": ip,
        }
        log_system(f"{name} 님이 광장에 들어왔습니다.", now)
        give_items(name)
        STATE["ver"] += 1
    return {"id": pid, "name": name, "look": look, "face": face, "role": role, "say_max": SAY_MAX,
            "x": STATE["players"][pid]["x"], "y": STATE["players"][pid]["y"], "dir": 0, "shared": False}


def api_move(body: dict) -> dict:
    with LOCK:
        p = player(body.get("id"))
        try:
            x, y, d = int(body.get("x")), int(body.get("y")), int(body.get("dir") or 0)
        except (TypeError, ValueError):
            raise ApiError(400, "칸 좌표는 정수입니다.")
        x, y = min(max(x, 0), MAP_W - 1), min(max(y, 0), MAP_H - 1)
        p["seen"] = time.time()
        # 캐릭터끼리 겹치지 않음 (2026-10-16 대시보드): 다른 사람이 선 칸으로는 못 감 → 제자리 칸을 돌려줌 (화면이 되돌아감)
        # 유령은 남과 겹쳐 지나가고, 남도 유령 칸은 지나감
        if (x, y) != (p["x"], p["y"]) and hp_p(p) > 0 and any(
                q is not p and (q["x"], q["y"]) == (x, y) and hp_p(q) > 0 for q in STATE["players"].values()):
            if d % 4 != p["dir"]:
                p["dir"] = d % 4
                STATE["ver"] += 1
            return {"ok": False, "blocked": True, "x": p["x"], "y": p["y"]}
        if (x, y) != (p["x"], p["y"]) and p.get("work"):    # 걸어가면 하던 작업은 그만
            st = EQ.get(p["work"]["eq"])
            if st and st["busy"] == p["name"]:
                st["busy"] = ""
            p.pop("work", None)
        if (x, y, d % 4) != (p["x"], p["y"], p["dir"]):
            p["x"], p["y"], p["dir"] = x, y, d % 4
            STATE["ver"] += 1
        got = pick_up(p, time.time()) if hp_p(p) > 0 else []
    return {"ok": True, "picked": got}


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
        check_week(now)
        if hp_p(p) <= 0:                           # 유령은 못 때림
            return {"ok": True, "hit": [], "ghost": True}
        if now - p["act_at"] < ATTACK_GAP_S:
            return {"ok": True, "hit": []}
        p["act_at"] = now
        p["act_seq"] += 1
        dx, dy = DIRV.get(p["dir"], (0, 1))
        front = {(p["x"] + dx, p["y"] + dy), (p["x"], p["y"])}
        hit, done = [], set()
        for q in STATE["players"].values():
            if q is p or (q["x"], q["y"]) not in front or q["name"] == p["name"] or hp_p(q) <= 0:
                continue
            q["hit_seq"] += 1
            q["hit_at"], q["hit_by"] = now, p["name"]
            if q["name"] in done or q.get("role") == "operator":   # 같은 이름이 둘이어도 체력은 한 번만 · 운영자는 무적
                continue
            done.add(q["name"])
            left = hp_of(q["name"]) - 1             # 한 대에 1
            HP["hp"][q["name"]] = left
            HP["dirty"] = True
            hit.append(q["name"])
            if left <= 0:
                k = HP["kills"][p["name"]] = min(HP["kills"].get(p["name"], 0) + 1, 9999)   # 처치 수
                lost = drop_items(q, now)
                log_system(f"{q['name']} 님이 {p['name']} 님에게 쓰러져 유령이 되었습니다. (주간 마감 · 운영자가 부활)"
                           + (f" — {' · '.join(ITEM_NAMES[i] for i in lost)} 을(를) 떨어뜨렸습니다." if lost else ""), now)
                if k == KILLER_AT:
                    log_system(f"⚔ {p['name']} 님이 이번 주 {k}명을 쓰러뜨려 killer 가 되었습니다!", now)
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


def api_status(body: dict) -> dict:
    text = clean(body.get("text"), STATUS_MAX)
    with LOCK:
        p = player(body.get("id"))
        p["seen"] = time.time()
        if p.get("status", "") != text:
            p["status"] = text
            STATE["ver"] += 1
    return {"ok": True, "status": text}


def api_leave(body: dict) -> dict:
    now = time.time()
    with LOCK:
        pid = str(body.get("id") or "")
        q = STATE["players"].get(pid)
        if q is not None and q["streams"] > 1:        # 같은 캐릭터를 쓰는 다른 대시보드 창이 아직 열려 있음 → 남김
            q["left_at"] = now                        # 그 창들도 곧 닫히면(연결이 모두 끊기면) 바로 나감 (_stream finally)
            return {"ok": True, "kept": True}
        p = STATE["players"].pop(pid, None)
        if p is not None:
            log_system(f"{p['name']} 님이 광장을 떠났습니다.", now)
            STATE["ver"] += 1
    return {"ok": True}


POSTS = {"/plaza/api/join": api_join, "/plaza/api/move": api_move, "/plaza/api/say": api_say,
         "/plaza/api/attack": api_attack, "/plaza/api/look": api_look, "/plaza/api/role": api_role,
         "/plaza/api/leave": api_leave, "/plaza/api/status": api_status, "/plaza/api/work": api_work,
         "/plaza/api/revive": api_revive}
FILES = {"/plaza": ("plaza.html", "text/html; charset=utf-8"),
         "/static/plaza.js": ("plaza.js", "text/javascript; charset=utf-8"),
         "/static/plaza.css": ("plaza.css", "text/css; charset=utf-8"),
         "/static/catknight.png": ("catknight.png", "image/png"),
         "/static/village_chars.png": ("village_chars.png", "image/png"),  # 마을 시트에서 뽑은 캐릭터 5종
         "/static/epc.png": ("epc.png", "image/png")}  # EPC 시트 (직무 캐릭터 · 초상 · 장비 · 효과 아이콘)


EXTRA_NETS: list = []                              # --allow 대역
NETS_FILE: Path | None = None                       # 대시보드의 사내 대역 파일 ({"nets": ["165.244.0.0/16", …]})
_NETS_CACHE: dict = {"mtime": None, "nets": []}


def file_nets() -> list:
    if NETS_FILE is None:
        return []
    try:
        mt = NETS_FILE.stat().st_mtime
    except OSError:
        return []
    if mt != _NETS_CACHE["mtime"]:                    # 대시보드가 새 대역을 기억하면(유선 ↔ Wi-Fi) 바로 따라감
        nets = []
        for n in read_json(NETS_FILE, {}).get("nets") or []:
            try:
                nets.append(ipaddress.ip_network(str(n), strict=False))
            except ValueError:
                pass
        _NETS_CACHE.update(mtime=mt, nets=nets)
    return _NETS_CACHE["nets"]


def allowed(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host.split("%")[0])
    except ValueError:
        return False
    if getattr(ip, "ipv4_mapped", None):
        ip = ip.ipv4_mapped
    return ip.is_loopback or ip.is_private or ip.is_link_local or any(ip in n for n in EXTRA_NETS + file_nets())


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
            return self._json(200, {"ok": True, "app": "plaza", "ver": PLAZA_VERSION}, {"Access-Control-Allow-Origin": "*"})
        if url.path in FILES:
            name, ctype = FILES[url.path]
            try:
                return self._send(200, (STATIC / name).read_bytes(), ctype)
            except OSError:
                return self._json(404, {"detail": f"{name} 이 없습니다."})
        if url.path == "/plaza/api/equip":                   # 설비 목록 (지도에 그릴 자리 · 이름) — 누구나
            return self._json(200, equip_defs())
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
        if urlparse(self.path).path == "/plaza/api/quit":       # 대시보드 서버가 새 판으로 바꿀 때 — 이 PC(루프백)에서만
            if not ipaddress.ip_address(self.client_address[0].split("%")[0]).is_loopback:
                return self._json(403, {"detail": "이 PC 에서만 됩니다."})
            self._json(200, {"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
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
        ip = ipaddress.ip_address(self.client_address[0].split("%")[0])
        body["_ip"] = str(getattr(ip, "ipv4_mapped", None) or ip)   # 접속 주소 = 서버가 정함
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
                elif ticks % 25 == 0:                 # 2초마다 — 창이 닫혀 끊긴 연결을 빨리 알아챔 (같은 PC 의 창 수 세기)
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
                    if p["streams"] <= 0 and p.get("left_at") and p["seen"] - p["left_at"] < 30:   # 창을 모두 닫음 → 바로 나감
                        STATE["players"].pop(pid, None)
                        log_system(f"{p['name']} 님이 광장을 떠났습니다.", p["seen"])
                        STATE["ver"] += 1


def main(argv=None) -> None:
    global DATA, NETS_FILE
    ap = argparse.ArgumentParser(description="가상 광장 서버 (표준 라이브러리만)")
    ap.add_argument("--port", type=int, default=8100)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--data", default=str(HERE / "plaza_data"), help="roles.json · looks.json 을 둘 폴더")
    ap.add_argument("--allow", action="append", default=[], help="더 허용할 사내망 대역 (예: 165.244.0.0/16), 여러 번 가능")
    ap.add_argument("--nets-file", help="허용 대역 목록 파일 (대시보드 data/_meta/server-nets.json)")
    a = ap.parse_args(argv)
    DATA = Path(a.data).resolve()
    EXTRA_NETS[:] = [ipaddress.ip_network(n, strict=False) for n in a.allow]
    NETS_FILE = Path(a.nets_file).resolve() if a.nets_file else None
    roles()                                        # 역할 파일 빈 틀을 만들어 둔다
    load_hp()
    load_items()
    eq_init()
    with LOCK:
        check_week(time.time(), force=True)        # 꺼져 있는 동안 마감이 지났으면 바로 부활
    save_hp()
    threading.Thread(target=hp_loop, daemon=True).start()
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    srv.daemon_threads = True
    try:                                           # 한글 Windows(cp949) 출력에서 '—' 같은 글자로 멈추지 않게 (2026-10-16 실제로 겪음: 시작하자마자 꺼짐)
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(f"계장 광장 - http://localhost:{a.port}/plaza?embed=1&user=이름   (데이터 {DATA})", flush=True)
    except Exception:
        pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
