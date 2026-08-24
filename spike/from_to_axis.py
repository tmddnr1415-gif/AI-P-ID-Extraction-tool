"""FROM-TO / 기기 직결 Description 판정기 — 사용자 확정 판정 트리의 구현.

전역 자료구조가 없다는 것의 코드상 의미:
  * 입력은 **한 페이지**의 (계기 행 · 병합 런 · 커넥터 문구 · 기기 라벨) 뿐이다.
  * 페이지 사이를 잇는 구조가 없고, 한 페이지 안에서도 런에서 런으로 걷는
    순회가 없다 — 계기가 탭한 런 하나에서 끝점을 보고, 끝점이 아무것도 안
    닿았을 때 **딱 한 번** 직교 런으로 승계(모선 FROM)한다.  재귀·큐·방문
    집합이 코드에 존재하지 않는다.
  * 모든 허용 오차는 이 문서에서 잰 값이다: join_slack(범례 유도) ·
    connector_reach 70.2pt(이 문서의 커넥터 218개 실측) ·
    equipment_reach(이 문서의 기기 라벨-런 간격 실측).  상수 없음.
"""
from __future__ import annotations

import re

AX_VENDOR = "⓪"       # 벤더 공급 — 생략 (현행 유지)
AX_EQUIP = "①"        # 기기 직결
AX_FROMTO = "②"       # 라인 탭 · TO 단일
AX_BRANCH = "③"       # 라인 탭 · TO 다분기 → 상류 DISCHARGE
AX_UNKNOWN = "④"      # 판정 불가 — 공란

CONNECTOR_RE = re.compile(r"^(TO|FROM)\b\s*(.+)$")

# ---------------------------------------------------------------- ISA 풀네임
# ISA-5.1 기능문자로 **조립**한다 - 프로젝트 무관.  첫 글자(+D)는 변수,
# 꼬리 글자가 기기를 정한다.  사용자 확정 예: PI=PRESSURE GAUGE ·
# TI=TEMPERATURE GAUGE · PT/PIT=PRESSURE TRANSMITTER · LIT=LEVEL TRANSMITTER ·
# FIT=FLOW TRANSMITTER · FE=FLOW ELEMENT.
_VARIABLE = {"P": "PRESSURE", "T": "TEMPERATURE", "L": "LEVEL", "F": "FLOW",
             "A": "ANALYSIS", "S": "SPEED", "V": "VIBRATION", "Z": "POSITION"}
_DEVICE = {"T": "TRANSMITTER", "I": "GAUGE", "G": "GAUGE", "E": "ELEMENT",
           "S": "SWITCH", "W": "WELL", "V": "VALVE", "O": "ORIFICE"}
_SPECIAL = {"RO": "RESTRICTION ORIFICE", "TW": "THERMOWELL",
            "PSV": "PRESSURE SAFETY VALVE", "PRV": "PRESSURE RELIEF VALVE"}
# 밸브 몸통 TYPE (산출물 MOV/BFV/PNEUMATIC 의 TYPE 열) — ISA 태그가 아니므로
# 기계적으로 "<TYPE> VALVE".  **가안** — 보고에 명시.
_VALVE_BODIES = ("GATE", "GLOBE", "CHECK", "BALL", "BUTTERFLY", "PLUG")


def isa_fullname(type_: str) -> str:
    t = (type_ or "").upper().strip()
    if not t:
        return ""
    if t in _SPECIAL:
        return _SPECIAL[t]
    if t in _VALVE_BODIES:
        return f"{t} VALVE"
    var, rest = t[0], t[1:]
    if var not in _VARIABLE:
        return t
    words = [_VARIABLE[var]]
    if rest[:1] == "D":                     # PD.. = DIFFERENTIAL PRESSURE ..
        words.insert(0, "DIFFERENTIAL")
        rest = rest[1:]
    dev = rest[-1:] if rest else ""
    if dev in _DEVICE:
        words.append(_DEVICE[dev])
        return " ".join(words)
    if not rest:                            # 한 글자 태그는 그대로
        return t
    return t


# ---------------------------------------------------------------- 기하 유틸
def _touch(run, rect, slack) -> bool:
    axis, coord, lo, hi = run
    if axis == "H":
        return (rect[1] - slack <= coord <= rect[3] + slack
                and lo - slack <= rect[2] and hi + slack >= rect[0])
    return (rect[0] - slack <= coord <= rect[2] + slack
            and lo - slack <= rect[3] and hi + slack >= rect[1])


def _pt_rect_d(p, rect) -> float:
    dx = max(rect[0] - p[0], 0, p[0] - rect[2])
    dy = max(rect[1] - p[1], 0, p[1] - rect[3])
    return max(dx, dy)


def _ends(run):
    axis, coord, lo, hi = run
    return (((lo, coord), (hi, coord)) if axis == "H"
            else ((coord, lo), (coord, hi)))


def _near_texts(p, items, reach):
    """점 p 에서 reach 안의 (rect, text) 들 — 가까운 순."""
    got = [(d, t) for rect, t in items
           if (d := _pt_rect_d(p, rect)) <= reach]
    return [t for _d, t in sorted(got, key=lambda x: (x[0], x[1]))]


def _near_equip(p, equipment, reach):
    got = [(d, e) for e in equipment
           if (d := _pt_rect_d(p, e.rect)) <= reach]
    got.sort(key=lambda x: (x[0], getattr(x[1], "label", "")))
    return [e for _d, e in got]


def _strip_conn(text: str) -> tuple:
    """커넥터 원문 → (방향, 명칭).  선두 FROM/TO 를 벗긴다 (중복 제거 규칙)."""
    m = CONNECTOR_RE.match(text.upper().strip())
    if not m:
        return "", text.upper().strip()
    return m.group(1), m.group(2).strip()


# ---------------------------------------------------------------- 판정
def judge_row(rect, runs, leaders, connectors, equipment, *,
              join_slack, conn_reach, eq_reach) -> dict:
    """한 행의 판정.  국소: 이 페이지의 목록만 보고, 순회하지 않는다."""
    ev = {"how": "", "run": None, "ends": [], "touch": []}

    # 1. 탭한 런
    mine = [r for r in runs if _touch(r, rect, join_slack)]
    ev["how"] = "run"
    if not mine:                               # 인출선 한 단계
        for axis, coord, lo, hi in leaders:
            p0, p1 = _ends((axis, coord, lo, hi))
            ins = [(_pt_rect_d(p, rect) <= join_slack) for p in (p0, p1)]
            if ins[0] == ins[1]:
                continue
            far = p1 if ins[0] else p0
            box = (far[0] - join_slack, far[1] - join_slack,
                   far[0] + join_slack, far[1] + join_slack)
            mine = [r for r in runs if _touch(r, box, join_slack)]
            if mine:
                ev["how"] = "leader"
                break
            # 인출선이 런이 아니라 기기 라벨 근방에 떨어짐 → 기기 직결
            eqs = _near_equip(far, equipment, eq_reach)
            if eqs:
                ev["how"] = "leader→equipment"
                return {"axis": AX_EQUIP, "equip": eqs[0].label, "ev": ev}
    if not mine:
        eqs = _near_equip(((rect[0]+rect[2])/2, (rect[1]+rect[3])/2),
                          equipment, eq_reach)
        if eqs:
            ev["how"] = "bubble→equipment"
            return {"axis": AX_EQUIP, "equip": eqs[0].label, "ev": ev}
        ev["why"] = "런 없음"
        return {"axis": AX_UNKNOWN, "ev": ev}
    if len({(r[0], round(r[1])) for r in mine}) > 1:
        ev["why"] = f"런 {len(mine)}개에 걸침"
        return {"axis": AX_UNKNOWN, "ev": ev}
    run = mine[0]
    ev["run"] = [run[0], round(run[1], 1), round(run[2], 1), round(run[3], 1)]

    # 2. 런이 기기 라벨에 닿는가 (윤곽/직결 근사)
    run_eq = [e for e in equipment if _touch(run, e.rect, eq_reach)]

    # 3. 끝점 판정 (+ 직교 런 1단계 승계)
    ends = []
    for p in _ends(run):
        found = None
        texts = _near_texts(p, connectors, conn_reach)
        if texts:
            d, name = _strip_conn(texts[0])
            found = {"kind": "CONN", "dir": d, "name": name,
                     "at": [round(p[0]), round(p[1])]}
        else:
            eqs = _near_equip(p, equipment, eq_reach)
            if eqs:
                found = {"kind": "EQUIP", "dir": "", "name": eqs[0].label,
                         "at": [round(p[0]), round(p[1])]}
            else:
                # 직교 런 1단계 — 모선 승계.  걷지 않는다: 그 런의 두 끝만 본다.
                for r2 in runs:
                    if r2[0] == run[0]:
                        continue
                    if _pt_rect_d(p, (r2[1], r2[2], r2[1], r2[3])
                                  if r2[0] == "V" else
                                  (r2[2], r2[1], r2[3], r2[1])) > join_slack:
                        continue
                    for q in _ends(r2):
                        texts = _near_texts(q, connectors, conn_reach)
                        if texts:
                            d, name = _strip_conn(texts[0])
                            found = {"kind": "CONN", "dir": d, "name": name,
                                     "at": [round(q[0]), round(q[1])],
                                     "inherited": True}
                            break
                        eqs = _near_equip(q, equipment, eq_reach)
                        if eqs:
                            found = {"kind": "EQUIP", "dir": "",
                                     "name": eqs[0].label,
                                     "at": [round(q[0]), round(q[1])],
                                     "inherited": True}
                            break
                    if found:
                        break
        ends.append(found)
    ev["ends"] = ends

    # 4. 다분기: 내 런의 **안쪽**에 끝점을 대는 직교 런 수 (T 자 분기)
    a0, a1 = _ends(run)
    tees = 0
    for r2 in runs:
        if r2[0] == run[0]:
            continue
        for q in _ends(r2):
            if (_touch(run, (q[0] - join_slack, q[1] - join_slack,
                             q[0] + join_slack, q[1] + join_slack), 0)
                    and _pt_rect_d(q, (a0[0], a0[1], a0[0], a0[1])) > join_slack
                    and _pt_rect_d(q, (a1[0], a1[1], a1[0], a1[1])) > join_slack):
                tees += 1
                break
    ev["tees"] = tees

    # 5. 분류
    named = [e for e in ends if e]
    conns = [e for e in named if e["kind"] == "CONN"]
    if run_eq and not conns:
        # 런이 라벨에 직접 닿고 끝점이 커넥터가 아니다 → 기기 직결.
        # 중첩(안쪽 라벨 우선): 닿은 라벨이 여럿이면 계기에 가장 가까운 것.
        cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
        run_eq.sort(key=lambda e: (max(abs((e.rect[0]+e.rect[2])/2 - cx),
                                       abs((e.rect[1]+e.rect[3])/2 - cy)),
                                   e.label))
        ev["touch"] = [e.label for e in run_eq[:3]]
        return {"axis": AX_EQUIP, "equip": run_eq[0].label, "ev": ev}
    if len(named) == 2:
        d0, d1 = named[0]["dir"], named[1]["dir"]
        if d0 == "FROM" or d1 == "TO":
            src, dst = named[0], named[1]
        elif d1 == "FROM" or d0 == "TO":
            src, dst = named[1], named[0]
        else:
            # 두 끝 다 기기 — 방향 단서 없음.  지어내지 않는다.
            ev["why"] = "양끝 기기 — 방향 미상"
            return {"axis": AX_UNKNOWN, "ev": ev,
                    "note": "②형이나 방향 단서 없음"}
        return {"axis": AX_FROMTO, "src": src["name"], "dst": dst["name"],
                "ev": ev}
    if len(named) == 1:
        e = named[0]
        up = e["dir"] in ("", "FROM")        # FROM 커넥터거나 기기면 상류로
        if tees >= 2 and up:
            return {"axis": AX_BRANCH, "up": e["name"], "ev": ev}
        if e["dir"] == "TO" and run_eq:
            # 한쪽 TO + 런이 기기 라벨에 닿음 → FROM 은 그 기기
            return {"axis": AX_FROMTO, "src": run_eq[0].label,
                    "dst": e["name"], "ev": ev}
        if e["dir"] == "FROM" and run_eq:
            return {"axis": AX_FROMTO, "src": e["name"],
                    "dst": run_eq[0].label, "ev": ev}
        ev["why"] = f"한쪽 끝만 판정 (분기 {tees})"
        return {"axis": AX_UNKNOWN, "ev": ev}
    ev["why"] = "양끝 모두 무명"
    return {"axis": AX_UNKNOWN, "ev": ev}


def sentence(verdict, type_: str, suffix: str = "") -> str:
    full = isa_fullname(type_)
    tail = f" {suffix}" if suffix else ""
    ax = verdict["axis"]
    if ax == AX_EQUIP:
        return f"{verdict['equip']} {full}{tail}"
    if ax == AX_FROMTO:
        return f"FROM {verdict['src']} TO {verdict['dst']} {full}{tail}"
    if ax == AX_BRANCH:
        return f"{verdict['up']} DISCHARGE {full}{tail}"
    return ""


def attribution(verdict) -> str:
    ax = verdict["axis"]
    if ax == AX_EQUIP:
        return verdict["equip"]
    if ax == AX_FROMTO:
        return f"{verdict['src']}→{verdict['dst']}"
    if ax == AX_BRANCH:
        return f"{verdict['up']}→(다분기)"
    return ""
