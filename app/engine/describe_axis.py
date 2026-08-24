"""FROM-TO / 기기 직결 Description 판정축 — 5회차 확정 판정 트리의 구현.

산출물 적용 범위는 config `description.axis_mode` 가 정한다:
  * ``mixed`` (AL NOUF1, 사용자 결정 (나)) — 판정이 선 행(①②③)만 이 모듈의
    문형으로 쓰고, ④ 는 현행 문장을 유지한다.
  * 비어 있으면 판정만 기록하고 문장은 바꾸지 않는다 (기본).

TYPE 풀네임은 ISA-5.1 기능문자 조립이며 **가안**이다 — 범례 p3 의 후속문자표는
낱말 원형(TRANSMIT·INDICAT)만 주므로 명사형(TRANSMITTER·GAUGE)은 표준 사전으로
조립한다.  1부 체크포인트의 시제(PIT→PRESSURE TRANSMITTER 등)로 사용자 확인을
받았다.

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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import describe_candidates as dcand  # noqa: E402

AX_VENDOR = "⓪"       # 벤더 공급 — 생략 (현행 유지)
AX_EQUIP = "①"        # 기기 직결
AX_FROMTO = "②"       # 라인 탭 · 양끝 성립
AX_FROM_ONLY = "②a"   # 라인 탭 · 출발만 읽힘
AX_TO_ONLY = "②b"     # 라인 탭 · 도착만 읽힘
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


def _run_pt_d(run, p) -> float:
    """점 → 런(선분) 체비쇼프 거리."""
    axis, coord, lo, hi = run
    if axis == "H":
        dx = max(lo - p[0], 0.0, p[0] - hi); dy = abs(coord - p[1])
    else:
        dy = max(lo - p[1], 0.0, p[1] - hi); dx = abs(coord - p[0])
    return max(dx, dy)


def _covers(run, other, slack) -> bool:
    """run 이 other(같은 축) 를 품는가 — 인출선 자신을 런 목록에서 걸러낼 때."""
    return (run[0] == other[0] and abs(run[1] - other[1]) <= slack
            and run[2] <= other[2] + slack and run[3] >= other[3] - slack)


def _own_body(item, rect, slack) -> bool:
    """심볼 자기 몸통 획 — rect 를 벗어나지 않는 획은 바깥 세계를 증언하지 못한다.

    p6 PIT 의 좌우 변(x=656.5 · 679.2, span 452.3~497.6)과 p16 RO 의 상하 변이
    런 목록에 그대로 들어와 "중심에 런 2개 동률" ④ 를 만들던 원인.  치수 상수
    없음 — 판정은 rect 포함 여부(±join_slack)뿐이다.
    """
    axis, coord, lo, hi = item
    if axis == "H":
        return (rect[1] - slack <= coord <= rect[3] + slack
                and lo >= rect[0] - slack and hi <= rect[2] + slack)
    return (rect[0] - slack <= coord <= rect[2] + slack
            and lo >= rect[1] - slack and hi <= rect[3] + slack)


def _crossings(L, runs, slack):
    """인출선 L 이 **가로지르는** 직교 런들 — (교차점, run).  근접이 아니라 교차다.

    인출선이 라인을 5pt 쯤 지나쳐 그려져도(측정: p16 RO 4.9pt) 교차는 교차다.
    """
    axis, c, lo, hi = L
    got = []
    for r in runs:
        if r[0] == axis:
            continue
        if (r[2] - slack <= c <= r[3] + slack
                and lo - slack <= r[1] <= hi + slack):
            pt = (c, r[1]) if axis == "V" else (r[1], c)
            got.append((pt, r))
    return got


def _gap_pair(runs, axis, at, cross, slack):
    """같은 축·같은 좌표의 두 런이 `at` 를 사이에 두고 마주보면 — 심볼/탭에서
    끊긴 **한 라인**이다.  병합해 돌려준다.  좌표 `cross` 는 그 라인의 위치."""
    for i, a in enumerate(runs):
        if a[0] != axis or abs(a[1] - cross) > slack:
            continue
        for b in runs[i + 1:]:
            if b[0] != axis or abs(b[1] - a[1]) > slack:
                continue
            left, right = (a, b) if a[3] <= b[3] else (b, a)
            if left[3] - slack <= at <= right[2] + slack:
                return (axis, (a[1] + b[1]) / 2,
                        min(a[2], b[2]), max(a[3], b[3]))
    return None


def standard_break(runs, join_slack):
    """표준 끊김 폭의 실측 — 교차 홉·흐름 화살표가 직선을 끊는 폭.

    같은 축·같은 좌표(±join_slack)의 마주보는 런 간격을 1pt 칸으로 세면
    이 문서는 17~18pt 에 2,644건(43%)의 봉우리가 서고 **19pt 칸이 0** 이다
    (두 번째 봉우리 35pt 는 인라인 밸브 몸통 — 다리를 놓지 않는다).
    다리 상한 = 최빈 칸 직후의 첫 빈 칸 경계.  분포에서 유도하므로 상수가 없고,
    문서마다 다시 잰다.  유도 실패(봉우리 없음)면 None — 다리를 놓지 않는다.
    """
    import collections
    hist = collections.Counter()
    by = collections.defaultdict(list)
    for a, c, lo, hi in runs:
        by[(a, round(c, 0))].append((lo, hi))
    for segs in by.values():
        segs.sort()
        for (l0, h0), (l1, h1) in zip(segs, segs[1:]):
            g = l1 - h0
            if 0 < g < 60:
                hist[round(g)] += 1
    if not hist:
        return None
    mode, n = max(hist.items(), key=lambda kv: (kv[1], -kv[0]))
    if n < 10:                       # 봉우리라 부를 수 없는 산발
        return None
    for g in range(mode + 1, 60):
        if hist.get(g, 0) == 0:
            return g - 0.5
    return None


def bridge_collinear(runs, join_slack, limit):
    """표준 끊김(< limit)으로 나뉜 콜리니어 런을 **한 직선**으로 병합한다.

    같은 축·같은 좌표의 직선이 홉·화살표로 끊긴 것은 같은 라인이다 — 그래프
    순회가 아니라 직선의 복원이다.  꺾임(엘보)은 병합하지 않는다.
    """
    if not limit:
        return list(runs)
    import collections
    by = collections.defaultdict(list)
    for r in runs:
        by[(r[0], round(r[1], 0))].append(r)
    out = []
    for segs in by.values():
        segs.sort(key=lambda r: r[2])
        cur = list(segs[0])
        for r in segs[1:]:
            if r[2] - cur[3] < limit and abs(r[1] - cur[1]) <= join_slack:
                cur[3] = max(cur[3], r[3])
            else:
                out.append(tuple(cur))
                cur = list(r)
        out.append(tuple(cur))
    return out


def pick_tap(rect, runs, leaders, join_slack, reach=None):
    """계기가 탭한 **그 런 하나**.  (run, how) 또는 (None, 사유).

    판정 트리의 "그 라인 런 하나만 따라간다"의 구현.  순서와 근거:
      0. 자기 몸통 획 제외 — rect 를 벗어나지 않는 획(_own_body).
      1. 인출선(한 끝만 rect) 이 가로지르는 직교 런 — 먼 끝에 가장 가까운 교차.
         라인이 탭에서 끊겨 있으면(같은 좌표 두 런이 인출선을 사이에 두고
         마주봄) 병합한 한 라인이 탭이다.
      2. 관통 라인 — 같은 좌표 두 런이 rect 를 사이에 두고 마주보면(인라인
         심볼·밸브) 그 병합 라인이 탭이다.
      3. rect 에 닿는 런 중 수직거리 최근접.  동률(join_slack 안)이 같은
         좌표의 콜리니어면 병합하고, 아니면 그때만 "둘 이상에 걸침" ④.
    모든 허용 오차는 join_slack(범례 유도) 하나다.
    """
    cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
    body = lambda r: _own_body(r, rect, join_slack)
    outs = [r for r in runs if not body(r)]

    # 1. 인출선 착지 — 교차 우선, 끊긴 라인 병합, 마지막으로 먼 끝 근접
    for L in sorted((l for l in leaders if not body(l)),
                    key=lambda l: min(_pt_rect_d(p, rect) for p in _ends(l))):
        p0, p1 = _ends(L)
        ins = [(_pt_rect_d(p, rect) <= join_slack) for p in (p0, p1)]
        if ins[0] == ins[1]:
            continue
        far = p1 if ins[0] else p0
        cross = [(pt, r) for pt, r in _crossings(L, outs, join_slack)
                 if not _covers(r, L, join_slack)]
        if cross:
            cross.sort(key=lambda x: (max(abs(x[0][0] - far[0]),
                                          abs(x[0][1] - far[1])),
                                      x[1][0], x[1][1]))
            return cross[0][1], "leader"
        at = L[1]                     # 인출선의 고정 좌표
        # 끊긴 라인: 인출선 span 안의 좌표에서 마주보는 콜리니어 쌍
        for r in outs:
            if r[0] == L[0]:
                continue
            if L[2] - join_slack <= r[1] <= L[3] + join_slack:
                pair = _gap_pair(outs, r[0], at, r[1], join_slack)
                if pair:
                    return pair, "leader-gap"
        cands = [r for r in outs
                 if _run_pt_d(r, far) <= join_slack and not _covers(r, L, join_slack)]
        if cands:
            cands.sort(key=lambda r: (_run_pt_d(r, far), r[0] != L[0], r[1]))
            return cands[0], "leader"

    # 2. 관통 라인 (인라인 심볼·밸브)
    for axis, at, c_lo, c_hi in (("H", (rect[0] + rect[2]) / 2, rect[1], rect[3]),
                                 ("V", (rect[1] + rect[3]) / 2, rect[0], rect[2])):
        best = None
        for r in outs:
            if r[0] != axis or not (c_lo - join_slack <= r[1] <= c_hi + join_slack):
                continue
            pair = _gap_pair(outs, axis, at, r[1], join_slack)
            if pair:
                d = abs(pair[1] - (c_lo + c_hi) / 2)
                if best is None or d < best[0]:
                    best = (d, pair)
        if best:
            return best[1], "inline"

    # 3. 닿는 런 최근접 — 콜리니어 동률은 병합
    touch = list({(r[0], round(r[1], 1), r[2], r[3]): r for r in outs
                  if _touch(r, rect, join_slack)}.values())
    if not touch and reach:
        # 스터브(< min_run)가 버려져 버블이 라인에서 떠 보일 수 있다 —
        # 그 길이 상한 안에서만 닿음을 다시 본다.  reach = min_run (범례 유도).
        touch = list({(r[0], round(r[1], 1), r[2], r[3]): r for r in outs
                      if _touch(r, rect, reach)}.values())
    if not touch:
        return None, "런 없음"
    touch.sort(key=lambda r: (_run_pt_d(r, (cx, cy)), r[0], r[1]))
    d0 = _run_pt_d(touch[0], (cx, cy))
    tied = [r for r in touch if _run_pt_d(r, (cx, cy)) - d0 <= join_slack]
    if len(tied) == 1:
        return tied[0], "run"
    if all(r[0] == tied[0][0] and abs(r[1] - tied[0][1]) <= join_slack
           for r in tied[1:]):
        merged = (tied[0][0], tied[0][1],
                  min(r[2] for r in tied), max(r[3] for r in tied))
        return merged, "run"
    return None, f"중심에 런 {len(tied)}개 동률"


def _strip_conn(text: str) -> tuple:
    """커넥터 원문 → (방향, 명칭).  선두 FROM/TO 를 벗긴다 (중복 제거 규칙)."""
    m = CONNECTOR_RE.match(text.upper().strip())
    if not m:
        return "", text.upper().strip()
    return m.group(1), m.group(2).strip()


# ---------------------------------------------------------------- 판정
def judge_row(rect, runs, leaders, connectors, equipment, *,
              join_slack, conn_reach, eq_reach, min_run=None) -> dict:
    """한 행의 판정.  국소: 이 페이지의 목록만 보고, 순회하지 않는다.

    `min_run` 은 런 병합이 버린 스터브의 길이 상한(범례 유도, 이 문서 16.97pt).
    끝점과 직교 런 사이 간격이 그보다 짧으면 "버려진 스터브가 있던 자리"와
    구별되지 않으므로, 승계 접합 판정의 허용치로 쓴다.  측정: 양끝 무명 행의
    끝점→직교 런 간격 p25=9.7 · p50=21.4pt — join_slack(0.8) 만으로는 17% 뿐.
    """
    junction = min_run if min_run else join_slack
    ev = {"how": "", "run": None, "ends": [], "touch": []}

    # 1. 탭한 런 — 그 하나를 정한다
    run, how = pick_tap(rect, runs, leaders, join_slack, junction)
    if run is None:
        if how == "런 없음":
            # 인출선이 런이 아니라 기기 라벨 근방에 떨어졌나 → 기기 직결
            for L in leaders:
                p0, p1 = _ends(L)
                ins = [(_pt_rect_d(p, rect) <= join_slack) for p in (p0, p1)]
                if ins[0] == ins[1]:
                    continue
                far = p1 if ins[0] else p0
                eqs = _near_equip(far, equipment, eq_reach)
                if eqs:
                    ev["how"] = "leader→equipment"
                    return {"axis": AX_EQUIP, "equip": eqs[0].label, "ev": ev}
            eqs = _near_equip(((rect[0]+rect[2])/2, (rect[1]+rect[3])/2),
                              equipment, eq_reach)
            if eqs:
                ev["how"] = "bubble→equipment"
                return {"axis": AX_EQUIP, "equip": eqs[0].label, "ev": ev}
        ev["why"] = how
        return {"axis": AX_UNKNOWN, "ev": ev}
    ev["how"] = how
    ev["run"] = [run[0], round(run[1], 1), round(run[2], 1), round(run[3], 1)]

    # 2. 런이 기기 라벨에 닿는가 (윤곽/직결 근사)
    run_eq = [e for e in equipment if _touch(run, e.rect, eq_reach)]

    # 3. 끝점 판정.  계기 쪽 끝(스템의 버블 쪽)은 계속하지 않는다.
    #    허공에 뜬 끝이 직교 런의 몸통에 닿으면(T 자) 그 런이 모선이다 —
    #    모선의 **두 끝**을 이어받는다 (딱 한 번, 더 걷지 않는다).
    def read_end(p):
        texts = _near_texts(p, connectors, conn_reach)
        if texts:
            d, name = _strip_conn(texts[0])
            return {"kind": "CONN", "dir": d, "name": name,
                    "at": [round(p[0]), round(p[1])]}
        eqs = _near_equip(p, equipment, eq_reach)
        if eqs:
            return {"kind": "EQUIP", "dir": "", "name": eqs[0].label,
                    "at": [round(p[0]), round(p[1])]}
        return None

    def trunk_at(p, exclude):
        cands = []
        for r2 in runs:
            if r2[0] == exclude[0] and _covers(exclude, r2, join_slack):
                continue
            if r2[0] == run[0]:
                continue
            d = _run_pt_d(r2, p)
            if d <= junction:
                cands.append((d, r2[3] - r2[2], r2))
        if not cands:
            return None
        cands.sort(key=lambda x: (x[0], -x[1]))     # 가깝고 긴 것이 모선
        return cands[0][2]

    named = []
    for p in _ends(run):
        if _pt_rect_d(p, rect) <= junction and how in ("run", "leader"):
            continue                                 # 계기 쪽 끝
        got = read_end(p)
        if got:
            named.append(got)
            continue
        trunk = trunk_at(p, run)
        if trunk is not None:
            ev.setdefault("trunk", []).append(
                [trunk[0], round(trunk[1], 1), round(trunk[2], 1), round(trunk[3], 1)])
            for q in _ends(trunk):
                got = read_end(q)
                if got:
                    got["inherited"] = True
                    named.append(got)
    ev["ends"] = named

    # 4. 다분기: 내 런(과 모선)의 **안쪽**에 끝점을 대는 직교 런 수 (T 자 분기)
    def tee_count(r):
        a0, a1 = _ends(r)
        n = 0
        for r2 in runs:
            if r2[0] == r[0]:
                continue
            for q in _ends(r2):
                if (_touch(r, (q[0] - junction, q[1] - junction,
                               q[0] + junction, q[1] + junction), 0)
                        and _pt_rect_d(q, (a0[0], a0[1], a0[0], a0[1])) > junction
                        and _pt_rect_d(q, (a1[0], a1[1], a1[0], a1[1])) > junction):
                    n += 1
                    break
        return n
    tees = tee_count(run)
    ev["tees"] = tees

    # 5. 분류
    # 중복 이름 정리 (모선 승계로 같은 커넥터가 두 번 잡힐 수 있음)
    named = list({(e["kind"], e["dir"], e["name"]): e for e in named}.values())
    conns = [e for e in named if e["kind"] == "CONN"]
    equips = [e for e in named if e["kind"] == "EQUIP"]
    froms = [e for e in conns if e["dir"] == "FROM"]
    tos = [e for e in conns if e["dir"] == "TO"]

    if run_eq and not conns:
        # 런이 라벨에 직접 닿고 끝점이 커넥터가 아니다 → 기기 직결.
        # 중첩(안쪽 라벨 우선): 닿은 라벨이 여럿이면 계기에 가장 가까운 것.
        cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
        run_eq.sort(key=lambda e: (max(abs((e.rect[0]+e.rect[2])/2 - cx),
                                       abs((e.rect[1]+e.rect[3])/2 - cy)),
                                   e.label))
        ev["touch"] = [e.label for e in run_eq[:3]]
        return {"axis": AX_EQUIP, "equip": run_eq[0].label, "ev": ev}

    if froms and len(tos) >= 2:
        return {"axis": AX_BRANCH, "up": froms[0]["name"], "ev": ev}
    if froms and tos:
        return {"axis": AX_FROMTO, "src": froms[0]["name"],
                "dst": tos[0]["name"], "ev": ev}
    if froms and (equips or run_eq):
        dst = equips[0]["name"] if equips else run_eq[0].label
        return {"axis": AX_FROMTO, "src": froms[0]["name"], "dst": dst, "ev": ev}
    if tos and (equips or run_eq):
        src = equips[0]["name"] if equips else run_eq[0].label
        return {"axis": AX_FROMTO, "src": src, "dst": tos[0]["name"], "ev": ev}
    if froms and tees >= 2:
        return {"axis": AX_BRANCH, "up": froms[0]["name"], "ev": ev}
    if len(equips) >= 1 and not conns:
        # 끝점이 기기뿐 — 방향 단서 없이 기기 하나면 직결로 본다
        if len(equips) == 1:
            return {"axis": AX_EQUIP, "equip": equips[0]["name"], "ev": ev}
        ev["why"] = "양끝 기기 — 방향 미상"
        return {"axis": AX_UNKNOWN, "ev": ev, "note": "②형이나 방향 단서 없음"}
    # 한쪽만 읽힌 경우 — 그 반쪽을 버리지 않는다 (7회차).  읽힌 이름은 도면이
    # 인쇄한 커넥터 문구이고, 없는 반대쪽을 지어내지 않는다.  실측: ④ 618행 중
    # 출발만 9 · 도착만 69 (`docs/from_to_axis.md`).
    if len(froms) == 1 and not tos:
        return {"axis": AX_FROM_ONLY, "src": froms[0]["name"], "ev": ev}
    if len(tos) == 1 and not froms:
        return {"axis": AX_TO_ONLY, "dst": tos[0]["name"], "ev": ev}
    if froms or tos:
        # 같은 방향 커넥터가 둘 — 두 끝이 다 `TO …` 이거나 다 `FROM …` 이다.
        # 하나를 고르는 것은 도면에 없는 선택이므로 고르지 않는다 (실측 4행:
        # p12 TIT 2 · p16 FE·FIT 2).  현행 문장을 유지한다.
        ev["why"] = (f"같은 방향 커넥터 {len(froms) or len(tos)}개 — 어느 쪽인지 "
                     f"도면이 말하지 않음")
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
    if ax == AX_FROM_ONLY:
        return f"FROM {verdict['src']} {full}{tail}"
    if ax == AX_TO_ONLY:
        return f"TO {verdict['dst']} {full}{tail}"
    if ax == AX_BRANCH:
        up = verdict["up"]
        # 이음매 중복 제거 - FROM 중복 제거와 같은 규칙: 문구가 이미 담고 있는
        # 낱말을 다시 붙이지 않는다 (`ACWP DISCHARGE` + DISCHARGE 실측 사례).
        mid = "" if up.upper().endswith("DISCHARGE") else " DISCHARGE"
        return f"{up}{mid} {full}{tail}"
    return ""


def attribution(verdict) -> str:
    ax = verdict["axis"]
    if ax == AX_EQUIP:
        return verdict["equip"]
    if ax == AX_FROMTO:
        return f"{verdict['src']}→{verdict['dst']}"
    if ax == AX_FROM_ONLY:
        return f"{verdict['src']}→"
    if ax == AX_TO_ONLY:
        return f"→{verdict['dst']}"
    if ax == AX_BRANCH:
        return f"{verdict['up']}→(다분기)"
    return ""


# ---------------------------------------------------------------- 페이지 판정
def judge_page(pc, triples, equipment, drawing_area, style,
               conn_reach, eq_reach) -> dict:
    """한 페이지의 `[(key, rect, type)]` 전부를 판정한다 → `{key: verdict}`.

    기하는 페이지당 한 번만 만든다: 병합 런(+표준 끊김 다리) · 인출선 ·
    커넥터 문구.  전부 이 페이지 것뿐이고, 페이지 사이를 잇는 것은 없다.
    """
    style = style or {}
    join_slack = style.get("join_slack", 0.8)
    runs, leaders = dcand.local_runs(pc, style)
    br = standard_break(runs, join_slack)
    runs = bridge_collinear(runs, join_slack, br)
    conns = dcand._connector_lines(pc, drawing_area)
    out = {}
    for key, rect, type_ in triples:
        v = judge_row(tuple(rect), runs, leaders, conns, equipment,
                      join_slack=join_slack, conn_reach=conn_reach,
                      eq_reach=eq_reach or join_slack,
                      min_run=style.get("min_run"))
        v["standard_break"] = br
        out[key] = v
    return out


def assign_suffixes(items) -> dict:
    """`[(key, page_no, type, rect, verdict)]` → `{key: "A"/"B"/…}`.

    같은 페이지 · 같은 귀속점 · 같은 TYPE 이 2행 이상일 때만, 위→아래 ·
    왼→오 (반올림 정수 좌표) 순서로 붙인다.  1행뿐이면 붙이지 않는다.
    """
    import collections
    groups = collections.defaultdict(list)
    for key, pno, type_, rect, v in items:
        att = attribution(v)
        if att and v["axis"] in (AX_EQUIP, AX_FROMTO, AX_FROM_ONLY,
                                 AX_TO_ONLY, AX_BRANCH):
            groups[(pno, att, type_)].append((key, rect))
    out = {}
    for members in groups.values():
        if len(members) < 2:
            continue
        members.sort(key=lambda kr: (round(kr[1][1]), round(kr[1][0])))
        for i, (key, _rect) in enumerate(members):
            out[key] = chr(ord("A") + i) if i < 26 else str(i + 1)
    return out
