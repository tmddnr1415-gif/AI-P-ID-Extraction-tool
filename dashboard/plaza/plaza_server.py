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

PLAZA_VERSION = '2026-10-22.11'   # 대시보드 server.py 가 이 줄을 읽어, 돌고 있는 광장 서버가 옛 판이면 바꿔 띄움
HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"

MAP_W, MAP_H = 96, 60        # plaza.js 의 지도 크기와 같다 (2026-10-22 판10: 동쪽 복지 구역 + 아래 실내 식당 · 헬스장)
NAME_MAX, SAY_MAX, LOG_KEEP, STATUS_MAX = 20, 80, 60, 24
BUBBLE_S, IDLE_S, PLAYERS_MAX = 7.0, 45.0, 80
ATTACK_GAP_S = 0.3
HP_MAX = 100                 # Lv 1 체력 — 맞을 때마다 1, 0 이면 유령 (주간 마감에 부활) · 레벨마다 +HP_PER_LV
HP_PER_LV = 10               # 2026-10-22 판4: 레벨이 오르면 최대 체력 · 마나도 오름 (Lv 30 까지)
MP_BASE, MP_PER_LV = 50, 5   # 마나 — Lv 1 은 50, 레벨마다 +5
MP_REGEN = 1                 # 1초마다 마나 +1 (유령은 안 참)
LV_CAP = 30
SKILLS = {                   # 키: (이름, 마나, 재사용 초) — 1 강타 · 2 응급 처치 · 3 현장 지원
    "strike": ("강타", 10, 3.0),      # 앞 칸 한 사람 체력 -(STRIKE_DMG + 공격력/4)  (평타는 1 + 공격력/10)
    "aid": ("응급 처치", 20, 8.0),     # 내 체력 +AID_HEAL
    "support": ("현장 지원", 30, 15.0),  # 둘레 SUPPORT_R 칸 안 팀원 체력 +(SUPPORT_HEAL + 마법/4) · 기력 회복은 화면이 함
    "bolt": ("전기 충격", 15, 4.0),    # 2026-10-22 판5 마법 공격 — 보는 쪽 BOLT_R 칸 안 첫 사람 체력 -(BOLT_DMG + 마법 공격력/3)
}
STRIKE_DMG, AID_HEAL, SUPPORT_HEAL, SUPPORT_R = 5, 25, 15, 3.0
BOLT_DMG, BOLT_R = 4, 4         # 응급 처치도 +마법/3
def dmg_basic(atk: int) -> int: return 1 + atk // 10          # 평타 (Space)
def dmg_strike(atk: int) -> int: return STRIKE_DMG + atk // 4
def dmg_bolt(matk: int) -> int: return BOLT_DMG + matk // 3
def heal_aid(matk: int) -> int: return AID_HEAL + matk // 3
def heal_support(matk: int) -> int: return SUPPORT_HEAL + matk // 4
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
    if out.get("kind") == 1:                       # 2026-10-22 판7: '사람' 캐릭터 없앰 → EPC 안전모 (동물)
        out["kind"] = 7
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
        if 0 <= n < HP_MAX + HP_PER_LV * LV_CAP and clean(k, NAME_MAX):
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
    MP.clear()
    if not first:
        log_system(f"주간 마감 — 새 주차 {week}. 모두 체력 · 마나가 가득 찼습니다." + (f" (유령 {revived}명 부활)" if revived else ""), now)
        STATE["ver"] += 1


def lv_of(name: str) -> int:
    return min(LV_CAP, level_of(XP["xp"].get(name, 0)))


def hp_max(name: str) -> int:
    return HP_MAX + HP_PER_LV * (lv_of(name) - 1)


def mp_max(name: str) -> int:
    return MP_BASE + MP_PER_LV * (lv_of(name) - 1)


def hp_of(name: str) -> int:                       # 기록이 없으면 가득 (레벨이 오르면 최대치도 함께 오름)
    return min(HP["hp"].get(name, 10 ** 6), hp_max(name))


def mp_of(name: str) -> int:
    return min(MP.get(name, 10 ** 6), mp_max(name))


def set_hp(name: str, v: int) -> None:             # LOCK 안에서
    if v >= hp_max(name):
        HP["hp"].pop(name, None)
    else:
        HP["hp"][name] = max(0, v)
    HP["dirty"] = True


def hp_p(p: dict) -> int:                          # 광장에 있는 사람의 체력 — 운영자는 무적(늘 가득)
    return hp_max(p["name"]) if p.get("role") == "operator" else hp_of(p["name"])


def save_hp() -> None:
    with LOCK:
        if not HP["dirty"]:
            return
        data = {"week": HP["week"], "hp": dict(HP["hp"]), "kills": dict(HP["kills"]),
                "_설명": f"계장 광장 체력 (이름 → 남은 체력, 없으면 가득 = {HP_MAX} + 레벨마다 {HP_PER_LV}). 0 = 유령. kills = 이번 주에 쓰러뜨린 수. "
                         f"주차가 바뀌면(주간 마감) 모두 가득 · kills 0."}
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
            mp_tick()
            if n % 10 == 0:
                stay_tick(time.time())
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
HEAL_PER_SEC = 1                # 1초마다 체력 +1 (최대치까지, 유령은 회복 안 됨 — 부활은 주간 마감 · 운영자)
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
MP: dict = {}                    # 이름 → 남은 마나 (없으면 가득 · 서버를 다시 켜면 가득 · 주간 마감에 가득)
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
    raw_xp = read_json(DATA / "xp.json", {})
    XP["pres"] = {clean(k, NAME_MAX): v for k, v in (raw_xp.get("pres") or {}).items() if isinstance(v, dict) and clean(k, NAME_MAX)}
    XP["streak"] = {clean(k, NAME_MAX): v for k, v in (raw_xp.get("streak") or {}).items() if isinstance(v, dict) and clean(k, NAME_MAX)}
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
        if name in done or hp_p(q) <= 0 or hp_p(q) >= hp_max(name):
            continue
        if any(h is not q and h["name"] != name and ((h["x"] - q["x"]) ** 2 + (h["y"] - q["y"]) ** 2) ** .5 <= HEAL_RADIUS for h in healers):
            done.add(name)
            set_hp(name, hp_of(name) + HEAL_PER_SEC)
            for r in STATE["players"].values():
                if r["name"] == name:
                    r["heal_seq"] = r.get("heal_seq", 0) + 1
                    r["heal_at"], r["heal_amt"] = now, HEAL_PER_SEC
    if done:
        STATE["ver"] += 1


# ── 접속 경험치 (2026-10-22 판9): 하루 첫 접속 · 연속 접속일 · 접속 유지 시간 → XP (레벨이 오르면 최대 체력 · 마나 늘고 가득 참) ──
VISIT_XP = 10                   # 하루 첫 접속
STREAK_XP, STREAK_CAP = 4, 7    # 연속 접속일마다 +4 (7 일까지 → 최대 +28)
STAY_EVERY, STAY_XP = 300, 2    # 접속 유지 5 분마다 +2
STAY_LONG = 3600                # 오늘 1 시간 넘게 머물면 5 분마다 +3 (오래 있을수록 조금 더)
STAY_CAP = 60                   # 접속 유지로 하루 최대 60 XP (켜 두기만 해서 끝없이 오르지 않게)


def today_str(now: float) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(now))


def pres_of(name: str, now: float) -> dict:      # LOCK 안에서 — 오늘 기록 (날이 바뀌면 새로)
    d = XP.setdefault("pres", {}).setdefault(name, {})
    t = today_str(now)
    if d.get("day") != t:
        d.update(day=t, sec=0, got=0, bank=0)
    return d


def add_xp(p_or_name, n: int, why: str, now: float, log: bool = False) -> int:   # LOCK 안에서 — 경험치 + 레벨 업(체력 · 마나 가득 · 알림)
    name = p_or_name if isinstance(p_or_name, str) else p_or_name["name"]
    old = XP["xp"].get(name, 0)
    XP["xp"][name] = old + n
    XP["dirty"] = True
    lv0, lv1 = min(LV_CAP, level_of(old)), min(LV_CAP, level_of(old + n))
    for q in STATE["players"].values():
        if q["name"] == name:
            q["xp_seq"] = q.get("xp_seq", 0) + 1
            q["xp_gain"], q["xp_why"], q["xp_at"] = n, why, now
            if lv1 > lv0:
                q["lvup_at"] = now
    if lv1 > lv0:
        if hp_of(name) > 0:                       # 유령은 그대로 (부활은 주간 마감 · 운영자)
            HP["hp"].pop(name, None); HP["dirty"] = True
        MP.pop(name, None)
        log_system(f"🎉 {name} 님 Lv {lv1} 달성! 최대 체력 {hp_max(name)} (+{HP_PER_LV * (lv1 - lv0)}) · 마나 {mp_max(name)} (+{MP_PER_LV * (lv1 - lv0)}) — 가득 찼습니다.", now)
    elif log:
        log_system(f"{name} 님 {why} +{n} XP", now)
    STATE["ver"] += 1
    return lv1


def visit_xp(name: str, now: float) -> None:     # LOCK 안에서 — 들어올 때: 하루 첫 접속 + 연속 접속일 보너스
    d = pres_of(name, now)
    if d.get("visited"):
        return
    st = XP.setdefault("streak", {}).setdefault(name, {"last": "", "n": 0, "visits": 0})
    yday = today_str(now - 86400)
    st["n"] = st["n"] + 1 if st.get("last") == yday else 1
    st["last"], st["visits"] = d["day"], st.get("visits", 0) + 1
    d["visited"] = True
    bonus, days = STREAK_XP * min(STREAK_CAP, st["n"] - 1), st["n"]
    add_xp(name, VISIT_XP + bonus, "오늘 첫 접속" + (f" · 연속 {days}일" if days > 1 else ""), now, log=True)


def stay_tick(now: float) -> None:               # LOCK 안에서 — 10초마다: 광장에 연결된 사람의 오늘 머문 시간 + 5분마다 XP
    for name in {q["name"] for q in STATE["players"].values() if q["streams"] > 0}:
        d = pres_of(name, now)
        d["sec"] += 10
        d["bank"] = d.get("bank", 0) + 10
        XP["dirty"] = True
        if d["bank"] >= STAY_EVERY and d["got"] < STAY_CAP:
            d["bank"] -= STAY_EVERY
            n = min(STAY_CAP - d["got"], STAY_XP + (1 if d["sec"] > STAY_LONG else 0))
            d["got"] += n
            add_xp(name, n, f"접속 유지 {d['sec'] // 60}분", now)


def save_xp() -> None:
    with LOCK:
        if not XP["dirty"]:
            return
        data = {"xp": dict(XP["xp"]), "pres": {k: dict(v) for k, v in XP.get("pres", {}).items()}, "streak": {k: dict(v) for k, v in XP.get("streak", {}).items()},
                "_설명": "계장 광장 경험치 (이름 → XP). 설비 점검 · 교정 · 수리 · 접속(하루 첫 접속 · 연속 접속일 · 접속 유지 5분마다)으로 쌓임. 레벨 = sqrt(XP/25)+1. "
                         "pres = 오늘 머문 초 · 접속 유지 XP · streak = 연속 접속일 · 총 접속일."}
        XP["dirty"] = False
    try:
        with FILE_LOCK:
            write_json(DATA / "xp.json", data)
    except OSError:
        with LOCK:
            XP["dirty"] = True


# ── 아이템 (2026-10-22 판3 · 판5): 들어오면 무작위 3 개 · 쓰러지면 그 자리에 떨어뜨림 · 곁에서 Z 로 주움 · 서로 교환 ──────
# 아이템마다 공격력(atk) · 마법 공격력(matk) · 등급(r 0 일반 · 1 고급 · 2 희귀 · 3 전설)이 무작위로 붙는다. 가방에 든 것의 합이 내 공격력 · 마법 공격력.
ITEM_NAMES = {"HART": "HART 통신기", "MULTI": "멀티미터", "CALIB": "루프 교정기", "SPOOL": "케이블 드럼", "ICABLE": "계장 케이블",
              "GLAND": "케이블 글랜드", "TB": "단자대", "AIRTUBE": "에어 튜브", "IMPULSE": "임펄스 튜브", "POSITIONER": "포지셔너",
              "CALPUMP": "교정 펌프", "HELMET": "안전모", "VEST": "안전 조끼", "WRENCH": "렌치", "SCREW": "드라이버",
              "LAPTOP": "노트북", "CHECK": "점검표", "RADIO": "무전기", "PG": "압력계", "DCSCARD": "DCS 카드"}   # 그림 = EPC 시트 i_<키>
ITEM_W = {   # 종류별 (공격 · 마법) 성향 — 공구는 공격, 계측 · 통신 · 전자는 마법
    "HART": (.4, 1.2), "MULTI": (.5, 1.0), "CALIB": (.5, 1.0), "SPOOL": (1.2, .2), "ICABLE": (.9, .5), "GLAND": (.8, .2),
    "TB": (.7, .6), "AIRTUBE": (.7, .3), "IMPULSE": (.8, .3), "POSITIONER": (.6, .9), "CALPUMP": (1.0, .4), "HELMET": (.5, .3),
    "VEST": (.4, .4), "WRENCH": (1.5, .1), "SCREW": (1.2, .2), "LAPTOP": (.2, 1.5), "CHECK": (.2, .8), "RADIO": (.3, 1.3),
    "PG": (.9, .4), "DCSCARD": (.2, 1.5)}
RARITY = ((70, 1.0, "일반"), (22, 1.6, "고급"), (7, 2.4, "희귀"), (1, 3.5, "전설"))   # (확률 % · 배수 · 이름)
ITEM_START = 3                  # 처음(그리고 빈 가방으로 부활할 때) 받는 개수
ITEM_MAX = 8                    # 가방 칸
GROUND_MAX = 80                 # 바닥에 남는 수 상한 (넘으면 오래된 것부터 사라짐)
PICK_DIST = 1                   # Z 로 주울 수 있는 거리 (선 칸 + 둘레 8 칸)
REVIVE_DIST = 2.5               # 운영자가 부활시킬 수 있는 거리 (칸)
TRADE_DIST = 3.0                # 교환 제안 · 수락 거리 (칸)
TRADE_S = 60                    # 교환 제안이 남는 시간 (초)
ITEMS: dict = {"inv": {}, "ground": [], "seq": 0, "iseq": 0, "dirty": False, "eq": {}}   # inv: 이름 → [아이템] · ground: [{id, item, x, y, at}] (<data>/items.json)
TRADES: dict = {}               # tid → {from, to, give: [아이템 id], want: [아이템 id], at}


def make_item(k: str, rnd=None) -> dict:          # LOCK 안에서 — 종류 k 의 새 아이템 (공격력 · 마법 공격력 · 등급 무작위)
    import random
    r = rnd or random
    roll, tier = r.uniform(0, 100), 0
    for i, (pct, _m, _n) in enumerate(RARITY):
        if roll < pct:
            tier = i
            break
        roll -= pct
    mult, base = RARITY[tier][1], r.randint(2, 5)
    wp, wm = ITEM_W.get(k, (.5, .5))
    ITEMS["iseq"] += 1
    return {"id": ITEMS["iseq"], "k": k, "atk": max(0, round(wp * base * mult)), "matk": max(0, round(wm * base * mult)), "r": tier}


def fix_item(v):                                   # 파일에서 읽은 값 → 아이템 (판3 의 '키' 만 있는 것은 새로 굴림)
    if isinstance(v, str) and v in ITEM_NAMES:
        return make_item(v)
    if isinstance(v, dict) and v.get("k") in ITEM_NAMES:
        try:
            it = {"id": int(v["id"]), "k": v["k"], "atk": max(0, min(999, int(v["atk"]))), "matk": max(0, min(999, int(v["matk"]))),
                  "r": max(0, min(3, int(v.get("r") or 0)))}
            ITEMS["iseq"] = max(ITEMS["iseq"], it["id"])
            return it
        except (KeyError, TypeError, ValueError):
            return make_item(v["k"])
    return None


def load_items() -> None:
    raw = read_json(DATA / "items.json", {})
    ITEMS.update(inv={}, ground=[], seq=0, iseq=int(raw.get("iseq") or 0) if str(raw.get("iseq") or "0").isdigit() else 0, dirty=False, eq={})
    for k, v in (raw.get("eq") or {}).items() if isinstance(raw.get("eq"), dict) else []:
        if clean(k, NAME_MAX) and isinstance(v, dict):
            ITEMS["eq"][clean(k, NAME_MAX)] = {sl: int(i) for sl, i in v.items() if sl in SLOTS and str(i).isdigit()}
    for k, v in (raw.get("inv") or {}).items() if isinstance(raw.get("inv"), dict) else []:
        if clean(k, NAME_MAX) and isinstance(v, list):
            ITEMS["inv"][clean(k, NAME_MAX)] = [i for i in map(fix_item, v) if i][:ITEM_MAX]
    for g in raw.get("ground") or [] if isinstance(raw.get("ground"), list) else []:
        try:
            it = fix_item(g.get("item") or g.get("it"))
            if it:
                ITEMS["ground"].append({"id": int(g["id"]), "item": it, "x": int(g["x"]) % MAP_W, "y": int(g["y"]) % MAP_H, "at": float(g.get("at") or 0)})
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    del ITEMS["ground"][:-GROUND_MAX]
    ITEMS["seq"] = max([g["id"] for g in ITEMS["ground"]] + [0])


def save_items() -> None:
    with LOCK:
        if not ITEMS["dirty"]:
            return
        data = {"inv": {k: [dict(i) for i in v] for k, v in ITEMS["inv"].items()}, "ground": [{**g, "item": dict(g["item"])} for g in ITEMS["ground"]],
                "iseq": ITEMS["iseq"], "eq": {k: dict(v) for k, v in ITEMS.get("eq", {}).items() if v},
                "_설명": "계장 광장 아이템. inv = 이름 → 가방 [{id, k 종류, atk 공격력, matk 마법 공격력, r 등급 0~3}] (처음 무작위 3 개). "
                         "ground = 쓰러진 사람이 떨어뜨린 것 (곁에서 Z 로 주움). 주간 마감에 바닥은 치우고 빈 가방은 새로 채움."}
        ITEMS["dirty"] = False
    try:
        with FILE_LOCK:
            write_json(DATA / "items.json", data)
    except OSError:
        with LOCK:
            ITEMS["dirty"] = True


def bag(name: str) -> list:
    return ITEMS["inv"].get(name) or []


# 착용 (2026-10-22 판7): 가방의 아이템을 손 · 머리 · 몸 칸에 낌 — 외형에 보이고, 낀 아이템은 공격력 · 마법이 두 배로 셈
SLOTS = ("hand", "head", "body")
SLOT_NAME = {"hand": "손", "head": "머리", "body": "몸"}
def slot_of(k: str) -> str:
    return "head" if k == "HELMET" else "body" if k == "VEST" else "hand"


def equipped(name: str) -> dict:                   # 칸 → 아이템 (가방에서 빠진 것은 빼고 돌려줌)
    ids = ITEMS.setdefault("eq", {}).get(name) or {}
    by = {i["id"]: i for i in bag(name)}
    return {sl: by[i] for sl, i in ids.items() if i in by}


def power(name: str) -> tuple:                     # (공격력, 마법 공격력) = 가방의 합 + 낀 아이템 한 번 더
    b, e = bag(name), equipped(name).values()
    return sum(i["atk"] for i in b) + sum(i["atk"] for i in e), sum(i["matk"] for i in b) + sum(i["matk"] for i in e)


def api_equip(body: dict) -> dict:                # 더블클릭 · F — 고른 아이템을 그 칸에 끼기 (이미 꼈으면 벗기)
    with LOCK:
        p = player(body.get("id"))
        p["seen"] = time.time()
        it = next((i for i in bag(p["name"]) if i["id"] == body.get("item")), None)
        if it is None:
            raise ApiError(404, "가방에 없는 아이템입니다.")
        sl = slot_of(it["k"])
        eq = ITEMS.setdefault("eq", {}).setdefault(p["name"], {})
        on = eq.get(sl) != it["id"]
        if on:
            eq[sl] = it["id"]
        else:
            eq.pop(sl, None)
        ITEMS["dirty"] = True
        STATE["ver"] += 1
        atk, matk = power(p["name"])
    return {"ok": True, "on": on, "slot": sl, "slot_name": SLOT_NAME[sl], "item": it, "atk": atk, "matk": matk}


def item_txt(it: dict) -> str:
    return f"{ITEM_NAMES[it['k']]}({RARITY[it['r']][2]} 공{it['atk']}·마{it['matk']})"


def give_items(name: str, force: bool = False) -> None:   # LOCK 안에서 — 처음 오거나(가방 없음) force 이면서 빈 가방이면 무작위로
    import random
    have = ITEMS["inv"].get(name)
    if have is None or (force and not have):
        ITEMS["inv"][name] = [make_item(k) for k in random.sample(list(ITEM_NAMES), ITEM_START)]
        ITEMS["dirty"] = True


def drop_items(q: dict, now: float) -> list:       # LOCK 안에서 — 가방을 그 자리 바닥에 (걸린 교환은 취소)
    lost = bag(q["name"])
    for it in lost:
        ITEMS["seq"] += 1
        ITEMS["ground"].append({"id": ITEMS["seq"], "item": it, "x": q["x"], "y": q["y"], "at": now})
    del ITEMS["ground"][:-GROUND_MAX]
    ITEMS["inv"][q["name"]] = []
    ITEMS["dirty"] = True
    for tid in [t for t, v in TRADES.items() if q["name"] in (v["from"], v["to"])]:
        TRADES.pop(tid)
    return list(lost)


def api_hold(body: dict) -> dict:                 # 가방에서 아이템 하나를 '들기' (손에 보임 · 모두에게) — item 없으면 내려놓음
    with LOCK:
        p = player(body.get("id"))
        p["seen"] = time.time()
        iid = body.get("item")
        held = next((i for i in bag(p["name"]) if iid is not None and i["id"] == iid), None)
        p["held"] = held["id"] if held else None
        STATE["ver"] += 1
    return {"ok": True, "held": held}


def api_drop(body: dict) -> dict:                 # X — 든(고른) 아이템을 선 자리에 떨어뜨림 (남이 Z 로 주울 수 있음)
    now = time.time()
    with LOCK:
        p = player(body.get("id"))
        p["seen"] = now
        if hp_p(p) <= 0:
            raise ApiError(400, "유령은 떨어뜨릴 수 없습니다.")
        b = ITEMS["inv"].setdefault(p["name"], [])
        it = next((i for i in b if i["id"] == body.get("item")), None)
        if it is None:
            raise ApiError(404, "가방에 없는 아이템입니다.")
        b.remove(it)
        ITEMS["seq"] += 1
        ITEMS["ground"].append({"id": ITEMS["seq"], "item": it, "x": p["x"], "y": p["y"], "at": now})
        del ITEMS["ground"][:-GROUND_MAX]
        ITEMS["dirty"] = True
        if p.get("held") == it["id"]:
            p["held"] = None
        for tid in [t for t, v in TRADES.items() if p["name"] in (v["from"], v["to"])]:
            TRADES.pop(tid)
        log_system(f"{p['name']} 님이 {item_txt(it)} 을(를) 내려놓았습니다.", now)
        STATE["ver"] += 1
    return {"ok": True, "item": it}


def api_pickup(body: dict) -> dict:               # Z — 선 칸과 둘레(PICK_DIST)의 아이템을 가까운 것부터, 가방이 찰 때까지
    now = time.time()
    with LOCK:
        p = player(body.get("id"))
        p["seen"] = now
        if hp_p(p) <= 0:
            raise ApiError(400, "유령은 주울 수 없습니다.")
        near = sorted((g for g in ITEMS["ground"] if max(abs(g["x"] - p["x"]), abs(g["y"] - p["y"])) <= PICK_DIST and now - g["at"] >= 0.8),
                      key=lambda g: (abs(g["x"] - p["x"]) + abs(g["y"] - p["y"]), g["id"]))
        if not near:
            raise ApiError(400, "곁에 주울 아이템이 없습니다.")
        b = ITEMS["inv"].setdefault(p["name"], [])
        if len(b) >= ITEM_MAX:
            raise ApiError(400, f"가방이 가득 찼습니다 ({ITEM_MAX} 칸).")
        got = []
        for g in near:
            if len(b) >= ITEM_MAX:
                break
            ITEMS["ground"].remove(g)
            b.append(g["item"])
            got.append(g["item"])
        ITEMS["dirty"] = True
        log_system(f"{p['name']} 님이 {' · '.join(item_txt(i) for i in got)} 을(를) 주웠습니다.", now)
        STATE["ver"] += 1
    return {"ok": True, "picked": got, "full": len(b) >= ITEM_MAX, "left": sum(1 for g in ITEMS["ground"] if max(abs(g["x"] - p["x"]), abs(g["y"] - p["y"])) <= PICK_DIST)}


def dist(p: dict, q: dict) -> float:
    return ((p["x"] - q["x"]) ** 2 + (p["y"] - q["y"]) ** 2) ** .5


def api_trade(body: dict) -> dict:                # 교환 — offer(제안) · accept(수락) · decline(거절/취소)
    now, op = time.time(), str(body.get("op") or "")
    with LOCK:
        p = player(body.get("id"))
        p["seen"] = now
        for t in [t for t, v in TRADES.items() if now - v["at"] > TRADE_S]:
            TRADES.pop(t)
        if op == "offer":
            target = clean(body.get("target"), NAME_MAX)
            qs = [q for q in STATE["players"].values() if q["name"] == target]
            if not qs or target == p["name"]:
                raise ApiError(404, "광장에 없는 사람입니다.")
            if hp_p(p) <= 0 or hp_p(qs[0]) <= 0:
                raise ApiError(400, "유령과는 교환할 수 없습니다.")
            if min(dist(p, q) for q in qs) > TRADE_DIST:
                raise ApiError(400, f"교환은 {TRADE_DIST:g} 칸 안에서 합니다.")
            give, want = [int(i) for i in body.get("give") or []], [int(i) for i in body.get("want") or []]
            mine, theirs = {i["id"] for i in bag(p["name"])}, {i["id"] for i in bag(target)}
            if not give and not want:
                raise ApiError(400, "주거나 받을 아이템을 하나 이상 고르세요.")
            if not set(give) <= mine or not set(want) <= theirs or len(set(give)) != len(give) or len(set(want)) != len(want):
                raise ApiError(400, "가방에 없는 아이템이 있습니다.")
            if len(mine) - len(give) + len(want) > ITEM_MAX or len(theirs) - len(want) + len(give) > ITEM_MAX:
                raise ApiError(400, f"교환하면 가방({ITEM_MAX} 칸)이 넘칩니다.")
            for t in [t for t, v in TRADES.items() if v["from"] == p["name"] or v["to"] == target]:
                TRADES.pop(t)                       # 한 사람에게 걸린 제안은 하나 — 새 제안이 옛 것을 대신함
            tid = secrets.token_hex(4)
            TRADES[tid] = {"from": p["name"], "to": target, "give": give, "want": want, "at": now}
            STATE["ver"] += 1
            return {"ok": True, "tid": tid}
        tid = str(body.get("tid") or "")
        t = TRADES.get(tid)
        if t is None:
            raise ApiError(404, "끝났거나 없는 교환입니다.")
        if op == "decline":
            if p["name"] not in (t["from"], t["to"]):
                raise ApiError(403, "내 교환이 아닙니다.")
            TRADES.pop(tid)
            log_system(f"{t['to']} 님이 {t['from']} 님의 교환 제안을 거절했습니다." if p["name"] == t["to"]
                       else f"{t['from']} 님이 {t['to']} 님에게 한 교환 제안을 거두었습니다.", now)
            STATE["ver"] += 1
            return {"ok": True}
        if op == "accept":
            if p["name"] != t["to"]:
                raise ApiError(403, "받는 사람만 수락할 수 있습니다.")
            fs = [q for q in STATE["players"].values() if q["name"] == t["from"]]
            if not fs or hp_p(fs[0]) <= 0 or hp_p(p) <= 0:
                TRADES.pop(tid)
                raise ApiError(400, "상대가 광장에 없거나 유령이라 교환이 취소되었습니다.")
            if min(dist(p, q) for q in fs) > TRADE_DIST + 1:
                raise ApiError(400, f"상대가 멀리 있습니다 ({TRADE_DIST:g} 칸 안으로).")
            fb, tb = ITEMS["inv"].setdefault(t["from"], []), ITEMS["inv"].setdefault(t["to"], [])
            give = [i for i in fb if i["id"] in t["give"]]
            want = [i for i in tb if i["id"] in t["want"]]
            if len(give) != len(t["give"]) or len(want) != len(t["want"]):
                TRADES.pop(tid)
                raise ApiError(400, "그사이 아이템이 바뀌어 교환이 취소되었습니다.")
            if len(fb) - len(give) + len(want) > ITEM_MAX or len(tb) - len(want) + len(give) > ITEM_MAX:
                raise ApiError(400, f"교환하면 가방({ITEM_MAX} 칸)이 넘칩니다.")
            ITEMS["inv"][t["from"]] = [i for i in fb if i not in give] + want
            ITEMS["inv"][t["to"]] = [i for i in tb if i not in want] + give
            ITEMS["dirty"] = True
            TRADES.pop(tid)
            for q in fs + [p]:
                q["trade_at"] = now
            log_system(f"🤝 {t['from']} ↔ {t['to']} 교환 — " + (" · ".join(item_txt(i) for i in give) or "없음") + " ↔ "
                       + (" · ".join(item_txt(i) for i in want) or "없음"), now)
            STATE["ver"] += 1
            return {"ok": True, "got": give, "gave": want}
    raise ApiError(400, "op 는 offer · accept · decline 입니다.")


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
        MP.pop(target, None)
        log_system(f"✨ 운영자 {p['name']} 님이 {target} 님을 부활시켰습니다. (체력 {hp_max(target)})", now)
        STATE["ver"] += 1
    return {"ok": True, "target": target, "hp": hp_max(target)}


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
            p.pop("work", None)
            p["cheer_at"] = now
            if before != "ok":
                log_system(f"{p['name']} 님이 {eid} {e[5]} {WORK[before][3]} 완료 (+{gained} XP)", now)
            lv1 = add_xp(p, gained, WORK[before][3], now)
            STATE["ver"] += 1
            return {"ok": True, "gained": gained, "xp": old + gained, "lv": lv1, "was": before, "label": WORK[before][3], "name": e[5]}
    raise ApiError(400, "phase 는 start · done · cancel 입니다.")


def equip_defs() -> dict:
    return {"equip": [{"id": i, "t": t, "x": x, "y": y, "w": w, "name": n} for i, t, x, y, w, n in EQUIP],
            "jobs": list(JOBS), "heal_radius": HEAL_RADIUS, "heal_per_sec": HEAL_PER_SEC,
            "items": ITEM_NAMES, "revive_dist": REVIVE_DIST, "rarity": [r[2] for r in RARITY], "trade_dist": TRADE_DIST,
            "skills": {k: {"name": v[0], "mp": v[1], "cd": v[2]} for k, v in SKILLS.items()},
            "skill_vals": {"strike": STRIKE_DMG, "aid": AID_HEAL, "support": SUPPORT_HEAL, "support_r": SUPPORT_R, "bolt": BOLT_DMG, "bolt_r": BOLT_R},
            "hp_per_lv": HP_PER_LV, "mp_base": MP_BASE, "mp_per_lv": MP_PER_LV, "mp_regen": MP_REGEN}


# ── 광장 상태 ──────────────────────────────────────────────────────────
# ── 박병두 프로님 동상 · NPC 말 (2026-10-22 판10) ─────────────────────────────────────────
# 동상: 광장 가운데 받침대(STATUE_HOME). 때리면 깨어나 때린 사람이 걸은 칸을 그대로 밟아 따라가며 STATUE_HITS 번 때리고,
# 걸어온 길을 되짚어 제자리로 돌아와 다시 동상이 된다. 지도의 막힌 칸을 몰라도 사람이 걸은 칸만 밟으므로 벽을 뚫지 않는다.
STATUE_NAME = "박병두 프로님"
STATUE_HOME = (78, 31)          # plaza.js STATUE_HOME 과 같다
STATUE_HITS, STATUE_DMG = 10, 3
STATUE_STEP_S, STATUE_HIT_S, STATUE_WAKE_S, STATUE_MAX_S = 0.14, 0.8, 0.9, 120.0
STATUE: dict = {"x": STATUE_HOME[0], "y": STATUE_HOME[1], "dir": 0, "mode": "stone", "target": "", "tname": "", "hits": 0,
                "since": 0.0, "step_at": 0.0, "hit_at": 0.0, "trail": [], "hist": [], "act_seq": 0, "act_at": 0.0,
                "say": "", "say_at": 0.0, "say_seq": 0}
STATUE_ATTACKER = {"name": "박병두 프로"}   # damage() 가 쓰러뜨린 사람으로 적음 ("… 박병두 프로 님에게 쓰러져")
NPC_N = 16
NPC_LINES = {"hit": "{name} 프로님 그만좀 때리세요!!", "click": "아!! 프로님 왜 불러요!! 바쁜데"}
NPC_SAY: dict = {}              # NPC 번호(plaza.js NPC_DEF 순서) → {text, at, seq, kind}
NPC_SAY_S = 3.5


def statue_say(text: str, now: float) -> None:     # LOCK 안에서
    STATUE["say"], STATUE["say_at"] = text, now
    STATUE["say_seq"] += 1


def statue_wake(p: dict, now: float) -> bool:      # LOCK 안에서 — p 가 받침대 위 동상을 때림
    if STATUE["mode"] != "stone":
        return False
    STATUE.update(mode="wake", target=next((pid for pid, q in STATE["players"].items() if q is p), ""), tname=p["name"], hits=0,
                  since=now, step_at=now, hit_at=now, trail=[(p["x"], p["y"])], hist=[STATUE_HOME])
    statue_say(f"누가 감히 나를 때려?! {p['name']} 프로님 거기 서!!", now)
    log_system(f"🗿 {STATUE_NAME} 동상이 깨어나 {p['name']} 님을 쫓아갑니다! ({STATUE_HITS}대 맞으면 돌아갑니다)", now)
    STATE["ver"] += 1
    return True


def statue_front(p: dict) -> bool:                 # 받침대 위 동상이 p 의 앞 칸(또는 같은 칸)에 있나
    dx, dy = DIRV.get(p["dir"], (0, 1))
    return STATUE["mode"] == "stone" and (STATUE["x"], STATUE["y"]) in {(p["x"] + dx, p["y"] + dy), (p["x"], p["y"])}


def statue_trail(p: dict) -> None:                 # LOCK 안에서 (api_move) — 쫓기는 사람이 밟은 칸을 줄에 적음
    if STATUE["mode"] in ("wake", "chase") and STATUE["tname"] == p["name"]:
        t = STATUE["trail"]
        if not t or t[-1] != (p["x"], p["y"]):
            t.append((p["x"], p["y"]))
            del t[:-400]


def statue_step(nx: int, ny: int) -> None:         # LOCK 안에서 — 한 칸 (걸어온 길에 같은 칸이 있으면 그 뒤를 잘라 돌아갈 길을 짧게)
    x, y = STATUE["x"], STATUE["y"]
    if (nx, ny) == (x, y):
        return
    STATUE["dir"] = 3 if nx > x else 2 if nx < x else 0 if ny > y else 1
    STATUE["x"], STATUE["y"] = nx, ny
    h = STATUE["hist"]
    if (nx, ny) in h:
        del h[h.index((nx, ny)) + 1:]
    else:
        h.append((nx, ny))


def statue_home(now: float, why: str = "") -> None:   # LOCK 안에서 — 돌아가기 시작
    STATUE.update(mode="back", trail=[])
    statue_say(why or "에휴… 이제 됐다. 제자리로 돌아간다.", now)


def statue_tick(now: float) -> None:               # LOCK 안에서 (0.07초마다)
    m = STATUE["mode"]
    if m == "stone":
        return
    changed = False
    if m == "wake":
        if now - STATUE["since"] >= STATUE_WAKE_S:
            STATUE["mode"] = m = "chase"
            changed = True
    if m == "chase":
        q = STATE["players"].get(STATUE["target"]) or next((r for r in STATE["players"].values() if r["name"] == STATUE["tname"]), None)
        if q is None or hp_p(q) <= 0 or now - STATUE["since"] > STATUE_MAX_S:
            statue_home(now, "어디 갔어?! …돌아간다." if q is None else "쓰러졌군. 돌아간다." if hp_p(q) <= 0 else "헉헉… 오늘은 여기까지.")
            STATE["ver"] += 1
            return
        x, y = STATUE["x"], STATUE["y"]
        if abs(q["x"] - x) + abs(q["y"] - y) <= 1 and (q["x"], q["y"]) != (x, y):   # 곁 — 바라보고 때림
            STATUE["dir"] = 3 if q["x"] > x else 2 if q["x"] < x else 0 if q["y"] > y else 1
            if now - STATUE["hit_at"] >= STATUE_HIT_S:
                STATUE["hit_at"] = now
                STATUE["hits"] += 1
                STATUE["act_seq"] += 1
                STATUE["act_at"] = now
                q["hit_seq"] += 1
                q["hit_at"], q["hit_by"], q["hit_dmg"] = now, STATUE_NAME, 0
                if q.get("role") != "operator":    # 운영자는 무적 (맞는 시늉만)
                    damage(STATUE_ATTACKER, q, STATUE_DMG, now)
                n = STATUE["hits"]
                statue_say(f"{n}대!" + (" 이제 됐다." if n >= STATUE_HITS else ""), now)
                if n >= STATUE_HITS:
                    log_system(f"🗿 {STATUE_NAME} 동상이 {q['name']} 님을 {n}대 때리고 제자리로 돌아갑니다.", now)
                    STATUE.update(mode="back", trail=[])
            changed = True
        elif now - STATUE["step_at"] >= STATUE_STEP_S:   # 따라감 — 그 사람이 밟은 칸을 차례로 (곁에 닿으면 멈춤)
            t = STATUE["trail"]
            while t and t[0] == (x, y):
                t.pop(0)
            if t and t[0] != (q["x"], q["y"]):
                nx, ny = t.pop(0)                  # 문으로 순간 이동한 칸이면 같이 건너뜀
                statue_step(nx, ny)
                STATUE["step_at"] = now
                changed = True
    elif m == "back":
        if now - STATUE["step_at"] >= STATUE_STEP_S:
            h = STATUE["hist"]
            if len(h) > 1:
                h.pop()
                nx, ny = h[-1]
                STATUE["dir"] = 3 if nx > STATUE["x"] else 2 if nx < STATUE["x"] else 0 if ny > STATUE["y"] else 1
                STATUE["x"], STATUE["y"] = nx, ny
            else:
                STATUE.update(x=STATUE_HOME[0], y=STATUE_HOME[1], dir=0, mode="stone", target="", tname="", hist=[])
                statue_say("…(다시 동상이 되었다)", now)
            STATUE["step_at"] = now
            changed = True
    if changed:
        STATE["ver"] += 1


def statue_loop() -> None:
    while True:
        time.sleep(0.07)
        with LOCK:
            statue_tick(time.time())


def statue_snap(now: float) -> dict:               # LOCK 안에서
    age = now - STATUE["say_at"]
    return {"x": STATUE["x"], "y": STATUE["y"], "dir": STATUE["dir"], "mode": STATUE["mode"], "hits": STATUE["hits"], "max": STATUE_HITS,
            "target": STATUE["tname"], "act_seq": STATUE["act_seq"], "act_age": round(now - STATUE["act_at"], 2),
            "say": STATUE["say"] if age < BUBBLE_S else "", "say_seq": STATUE["say_seq"], "say_left": round(BUBBLE_S - age, 2) if age < BUBBLE_S else 0,
            "home": list(STATUE_HOME), "name": STATUE_NAME}


def api_npc(body: dict) -> dict:                  # NPC 를 때리거나(hit) 마우스로 누름(click) → 그 NPC 가 모두에게 보이는 말을 함
    kind = str(body.get("kind") or "")
    if kind not in NPC_LINES:
        raise ApiError(400, "없는 동작입니다.")
    try:
        i = int(body.get("npc"))
    except (TypeError, ValueError):
        raise ApiError(400, "NPC 번호는 정수입니다.")
    if not 0 <= i < NPC_N:
        raise ApiError(400, "없는 NPC 입니다.")
    now = time.time()
    with LOCK:
        p = player(body.get("id"))
        p["seen"] = now
        if kind == "hit" and hp_p(p) <= 0:
            return {"ok": False}
        o = NPC_SAY.get(i)
        if o and now - o["at"] < 0.4:              # 꾹 누르기 · 연타는 0.4초에 한 번만
            return {"ok": True}
        NPC_SAY[i] = {"text": NPC_LINES[kind].format(name=p["name"]), "at": now, "seq": (o["seq"] + 1) if o else 1, "kind": kind}
        STATE["ver"] += 1
    return {"ok": True}


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
                "hit_seq": p["hit_seq"], "hit_age": round(now - p["hit_at"], 2), "hit_by": p["hit_by"], "hit_dmg": p.get("hit_dmg", 0),
                "status": p.get("status", ""),
                "hp": hp_p(p), "hp_max": hp_max(p["name"]), "ghost": hp_p(p) <= 0, "inf": p.get("role") == "operator",
                "mp": mp_of(p["name"]), "mp_max": mp_max(p["name"]),
                "skill": p.get("skill", ""), "skill_seq": p.get("skill_seq", 0), "skill_age": round(now - p.get("skill_at", 0), 2),
                "kills": HP["kills"].get(p["name"], 0), "killer": HP["kills"].get(p["name"], 0) >= KILLER_AT,
                "xp": XP["xp"].get(p["name"], 0), "lv": min(LV_CAP, level_of(XP["xp"].get(p["name"], 0))), "job": job_of(p),
                "xp_seq": p.get("xp_seq", 0), "xp_gain": p.get("xp_gain", 0), "xp_why": p.get("xp_why", ""), "xp_age": round(now - p.get("xp_at", 0), 2),
                "lvup_age": round(now - p.get("lvup_at", 0), 2),
                "pres": {"min": (XP.get("pres", {}).get(p["name"], {}).get("sec", 0) // 60) if XP.get("pres", {}).get(p["name"], {}).get("day") == today_str(now) else 0,
                         "got": XP.get("pres", {}).get(p["name"], {}).get("got", 0) if XP.get("pres", {}).get(p["name"], {}).get("day") == today_str(now) else 0,
                         "streak": XP.get("streak", {}).get(p["name"], {}).get("n", 0), "visits": XP.get("streak", {}).get(p["name"], {}).get("visits", 0), "cap": STAY_CAP},
                "healer": p.get("role") in HEAL_ROLES and hp_p(p) > 0,
                "heal_seq": p.get("heal_seq", 0), "heal_age": round(now - p.get("heal_at", 0), 2), "heal_amt": p.get("heal_amt", 1),
                "cheer_age": round(now - p.get("cheer_at", 0), 2),
                "items": [dict(i) for i in bag(p["name"])], "atk": power(p["name"])[0], "matk": power(p["name"])[1],
                "held": next((dict(i) for i in bag(p["name"]) if i["id"] == p.get("held")), None),
                "equip": {sl: dict(i) for sl, i in equipped(p["name"]).items()},
                "trade_age": round(now - p.get("trade_at", 0), 2), "skill_to": p.get("skill_to"), "revive_age": round(now - p.get("revive_at", 0), 2), "revive_by": p.get("revive_by", ""),
                "work": ({k: p["work"][k] for k in ("eq", "kind", "need", "label")} | {"age": round(now - p["work"]["at"], 2)}) if p.get("work") else None,
            })
        log = [{"seq": m["seq"], "name": m["name"], "text": m["text"], "sys": m["sys"],
                "at": time.strftime("%H:%M", time.localtime(m["at"]))} for m in STATE["log"]]
        eq = {k: [v["st"], v["busy"]] for k, v in EQ.items()}
        ground = [[g["id"], g["item"]["k"], g["x"], g["y"], round(now - g["at"], 2), g["item"]["r"], g["item"]["atk"], g["item"]["matk"]] for g in ITEMS["ground"]]
        trades = [{"tid": t, "from": v["from"], "to": v["to"], "left": round(TRADE_S - (now - v["at"]), 1),
                   "give": [dict(i) for i in bag(v["from"]) if i["id"] in v["give"]], "want": [dict(i) for i in bag(v["to"]) if i["id"] in v["want"]]}
                  for t, v in TRADES.items() if now - v["at"] <= TRADE_S]
        npc_say = {str(i): [v["seq"], v["text"], round(NPC_SAY_S - (now - v["at"]), 2), v["kind"], round(now - v["at"], 2)]
                   for i, v in NPC_SAY.items() if now - v["at"] < NPC_SAY_S}
        return {"ver": STATE["ver"], "players": players, "log": log, "online": len(players), "week": HP["week"], "eq": eq, "heal_r": HEAL_RADIUS,
                "ground": ground, "trades": trades, "statue": statue_snap(now), "npc_say": npc_say}


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
                visit_xp(name, now)
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
        visit_xp(name, now)
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
            statue_trail(p)
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
        if statue_front(p) and statue_wake(p, now):
            hit.append(STATUE_NAME)
        for q in STATE["players"].values():
            if q is p or (q["x"], q["y"]) not in front or q["name"] == p["name"] or hp_p(q) <= 0:
                continue
            q["hit_seq"] += 1
            q["hit_at"], q["hit_by"] = now, p["name"]
            if q["name"] in done or q.get("role") == "operator":   # 같은 이름이 둘이어도 체력은 한 번만 · 운영자는 무적
                q["hit_dmg"] = 0
                continue
            done.add(q["name"])
            damage(p, q, dmg_basic(power(p["name"])[0]), now)   # 평타 = 1 + 공격력/10
            hit.append(q["name"])
        STATE["ver"] += 1
    return {"ok": True, "hit": hit}


def damage(p: dict, q: dict, n: int, now: float) -> int:   # LOCK 안에서 — p 가 q 에게 n · 쓰러지면 처치 수 · 아이템 떨어뜨림
    left = hp_of(q["name"]) - n
    set_hp(q["name"], left)
    q["hit_dmg"] = n
    if left <= 0:
        k = HP["kills"][p["name"]] = min(HP["kills"].get(p["name"], 0) + 1, 9999)   # 처치 수
        lost = drop_items(q, now)
        log_system(f"{q['name']} 님이 {p['name']} 님에게 쓰러져 유령이 되었습니다. (주간 마감 · 운영자가 부활)"
                   + (f" — {' · '.join(item_txt(i) for i in lost)} 을(를) 떨어뜨렸습니다." if lost else ""), now)
        if k == KILLER_AT:
            log_system(f"⚔ {p['name']} 님이 이번 주 {k}명을 쓰러뜨려 killer 가 되었습니다!", now)
    return max(0, left)


def mp_tick() -> None:                             # LOCK 안에서 — 1초마다 마나 +MP_REGEN (광장에 있는 산 사람)
    for name in {q["name"] for q in STATE["players"].values() if hp_p(q) > 0}:
        if name in MP:
            v = MP[name] + MP_REGEN
            if v >= mp_max(name):
                MP.pop(name)
            else:
                MP[name] = v
            STATE["ver"] += 1


def api_skill(body: dict) -> dict:                 # 1 강타 · 2 응급 처치 · 3 현장 지원 — 마나를 쓰고 재사용 시간이 있음
    now, key = time.time(), str(body.get("skill") or "")
    if key not in SKILLS:
        raise ApiError(400, "없는 기술입니다.")
    label, cost, cd = SKILLS[key]
    with LOCK:
        p = player(body.get("id"))
        p["seen"] = now
        check_week(now)
        if hp_p(p) <= 0:
            raise ApiError(400, "유령은 기술을 쓸 수 없습니다.")
        left_cd = p.setdefault("cd", {}).get(key, 0) - now
        if left_cd > 0:
            raise ApiError(429, f"{label} — {left_cd:.1f}초 뒤에 다시 쓸 수 있습니다.")
        if mp_of(p["name"]) < cost:
            raise ApiError(400, f"마나가 모자랍니다 ({label} {cost} 필요 · 지금 {mp_of(p['name'])}).")
        res: dict = {"ok": True, "skill": key, "label": label}
        if key == "strike":
            dx, dy = DIRV.get(p["dir"], (0, 1))
            front = [(p["x"] + dx, p["y"] + dy), (p["x"], p["y"])]
            q = next((q for c in front for q in STATE["players"].values()
                      if q is not p and q["name"] != p["name"] and (q["x"], q["y"]) == c and hp_p(q) > 0), None)
            if q is None and statue_front(p) and statue_wake(p, now):
                p["act_at"] = now
                p["act_seq"] += 1
                STATE["ver"] += 1
                return {"ok": True, "skill": key, "label": label, "target": STATUE_NAME, "dmg": 0, "mp": mp_of(p["name"]), "cd": 0}
            if q is None:
                raise ApiError(400, "앞 칸에 사람이 없습니다 (마나는 그대로).")
            q["hit_seq"] += 1
            q["hit_at"], q["hit_by"] = now, p["name"]
            res["target"], res["dmg"] = q["name"], 0 if q.get("role") == "operator" else dmg_strike(power(p["name"])[0])
            q["hit_dmg"] = 0
            if q.get("role") != "operator":
                res["left"] = damage(p, q, res["dmg"], now)
            p["act_at"] = now
            p["act_seq"] += 1
        elif key == "aid":
            if hp_p(p) >= hp_max(p["name"]):
                raise ApiError(400, "체력이 가득합니다 (마나는 그대로).")
            set_hp(p["name"], hp_of(p["name"]) + heal_aid(power(p["name"])[1]))
            res["hp"] = hp_of(p["name"])
        elif key == "bolt":
            dx, dy = DIRV.get(p["dir"], (0, 1))
            q, end = None, (p["x"] + dx * BOLT_R, p["y"] + dy * BOLT_R)
            for n in range(1, BOLT_R + 1):
                c = (p["x"] + dx * n, p["y"] + dy * n)
                q = next((q for q in STATE["players"].values() if q["name"] != p["name"] and (q["x"], q["y"]) == c and hp_p(q) > 0), None)
                if q:
                    end = c
                    break
            if q is None:
                raise ApiError(400, f"보는 쪽 {BOLT_R} 칸 안에 사람이 없습니다 (마나는 그대로).")
            q["hit_seq"] += 1
            q["hit_at"], q["hit_by"], q["hit_dmg"] = now, p["name"], 0
            res["target"], res["dmg"] = q["name"], 0 if q.get("role") == "operator" else dmg_bolt(power(p["name"])[1])
            if q.get("role") != "operator":
                res["left"] = damage(p, q, res["dmg"], now)
            p["skill_to"] = list(end)
        else:
            near = {q["name"] for q in STATE["players"].values()
                    if q["name"] != p["name"] and hp_p(q) > 0 and ((q["x"] - p["x"]) ** 2 + (q["y"] - p["y"]) ** 2) ** .5 <= SUPPORT_R}
            if not near:
                raise ApiError(400, f"둘레 {SUPPORT_R:g} 칸 안에 팀원이 없습니다 (마나는 그대로).")
            for name in near:
                set_hp(name, hp_of(name) + heal_support(power(p["name"])[1]))
                for r in STATE["players"].values():
                    if r["name"] == name:
                        r["heal_seq"] = r.get("heal_seq", 0) + 1
                        r["heal_at"], r["heal_amt"] = now, heal_support(power(p["name"])[1])
            res["healed"] = sorted(near)
            log_system(f"💚 {p['name']} 님의 현장 지원 — {' · '.join(sorted(near))} 체력 +{heal_support(power(p['name'])[1])}", now)
        MP[p["name"]] = mp_of(p["name"]) - cost
        p["cd"][key] = now + cd
        p["skill"], p["skill_at"], p["skill_seq"] = key, now, p.get("skill_seq", 0) + 1
        STATE["ver"] += 1
        res.update(mp=mp_of(p["name"]), cd=cd)
    return res


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
         "/plaza/api/revive": api_revive, "/plaza/api/skill": api_skill, "/plaza/api/pickup": api_pickup, "/plaza/api/hold": api_hold, "/plaza/api/equip": api_equip, "/plaza/api/drop": api_drop,
         "/plaza/api/trade": api_trade, "/plaza/api/npc": api_npc}
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
    threading.Thread(target=statue_loop, daemon=True).start()
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
