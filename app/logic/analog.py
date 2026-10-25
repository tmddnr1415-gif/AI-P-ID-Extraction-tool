"""L26 — 아날로그 값과 신호 감시(HHH · HH · H · /L · /LL …) 설정값.

  * 시뮬레이터는 1/0 이다.  그런데 MED(중간값 선택) 같은 아날로그 블록 뒤에 **신호 감시 블록**(범례 'SIGNAL
    MONITOR' — 글자 `HHH/` `HH/` `H/` `/L` `/LL`)이 서고, 그 출력은 값이 설정값을 넘는지(넘지 못하는지)로 정해지는
    1/0 이다.  사람이 MED 값을 주면 감시 블록마다 그 값과 설정값을 맞대어 1/0 을 낸다 —
    HH 는 넘지만 HHH 보다 낮으면 HH 만 1 · HHH 보다 높으면 HH · HHH 둘 다 1 (사용자 지시).
  * 높고 낮음은 글자가 정한다 — `/` 왼쪽 H 는 '넘으면' · 오른쪽 L 은 '못 미치면'.  H 의 개수(단계)는 이름일 뿐
    비교에 쓰지 않는다 (같은 단계라도 설정값은 장마다 다르다).
  * 설정값은 ① 사람이 정한 값(overrides · 작성자) → ② 도면이 감시 블록 바로 위에 인쇄한 값(`202.4 barg`) →
    ③ 없음(그 블록은 예전처럼 사람이 1/0 을 준다).  값은 지어내지 않는다.
  * 아날로그 값은 시뮬레이션 입력이다 (사람이 준 1/0 강제와 같은 자리) — 블록(`block:B16`) 이나 입력 행(`row:34`).
    MED 에 값을 안 주고 그 앞 블록 · 입력 행에 값을 주면 MED 는 범례 이름대로 **중간값**을 낸다.
  * L27 — 사람이 주는 값은 **4~20 mA** 다 (디지털 1/0 과 다르다 · 사용자 지시).  기본 **8 mA**.  공학값으로 바꾸는 범위는
    도면이 그 입력선 바로 아래에 인쇄한 것(`0~250 barg`)을 읽고, 없으면 사람이 적는다 (`ranges` · 작성자).
    범위를 모르는 입력은 공학값이 없어 감시 블록이 맞대지 않는다 (예전처럼 1/0).
"""
from __future__ import annotations

import re
import statistics

MONITOR_FUNC = "SIGNAL MONITOR"
MA_LO, MA_HI, DEFAULT_MA = 4.0, 20.0, 8.0          # L27 — 계장 신호 4~20 mA · 기본 8 mA (사용자 지시)
_MON = re.compile(r"^\s*(H+)\s*/\s*$|^\s*/\s*(L+)\s*$")
_NUM = re.compile(r"^[-+−]?\d+(?:[.,]\d+)?$")
# 범례 이름이 값을 어떻게 고르는지 말하는 아날로그 블록 (이름 → 계산).  이름은 범례(학습 사전)가 붙인 것.
SELECTORS = {
    "MEDIAN SELECTION": "median",
    "AVERAGE": "mean", "AVERAGE SELECTION": "mean", "MEAN": "mean",
    "HIGH SELECTION": "max", "HIGH SELECT": "max", "MAXIMUM SELECTION": "max",
    "LOW SELECTION": "min", "LOW SELECT": "min", "MINIMUM SELECTION": "min",
}


def monitor_kind(b):
    """감시 블록이면 ("high"|"low", 단계 글자) · 아니면 None."""
    lab = (b.get("label") or b.get("read") or "").upper()
    m = _MON.match(lab)
    if not m:
        return None
    if b.get("func") != MONITOR_FUNC and b.get("logic") not in ("source", "unknown"):
        return None
    return ("high", m.group(1)) if m.group(1) else ("low", m.group(2))


def selector_of(b):
    f = (b.get("func") or "").upper()
    if f in SELECTORS:
        return SELECTORS[f]
    lab = re.sub(r"[^A-Z]", "", (b.get("label") or "").upper())
    return {"MED": "median", "AVG": "mean", "MAX": "max", "MIN": "min"}.get(lab) if b.get("logic") == "unknown" else None


def num(v):
    try:
        f = float(str(v).replace("−", "-").replace(",", "."))
    except (TypeError, ValueError):
        return None
    return f if abs(f) < 1e12 else None


def setpoint(b):
    """(값, 출처 'user'|'drawing') | (None, None)."""
    p = b.get("param") or {}
    for k, src in (("sp_user", "user"), ("sp", "drawing")):
        f = num(p.get(k)) if p.get(k) is not None else None
        if f is not None:
            return f, src
    return None, None


def compare(kind, v, sp):
    """범례 '넘는다' — HH 는 넘지만 HHH 보다 낮으면 HH 만.  같은 값은 넘은 것이 아니다."""
    return 1 if (v > sp if kind == "high" else v < sp) else 0


def _calc(how, vs):
    if how == "median":
        return statistics.median(vs)
    if how == "mean":
        return sum(vs) / len(vs)
    return max(vs) if how == "max" else min(vs)


def ma_ok(v):
    f = num(v)
    return f if f is not None and MA_LO <= f <= MA_HI else None


def to_eng(ma, rng):
    lo, hi = float(rng["lo"]), float(rng["hi"])
    return round(lo + (ma - MA_LO) / (MA_HI - MA_LO) * (hi - lo), 6)


def to_ma(v, rng):
    lo, hi = float(rng["lo"]), float(rng["hi"])
    return None if hi == lo else round(MA_LO + (v - lo) / (hi - lo) * (MA_HI - MA_LO), 3)


def _rng(x):
    """사람이 적은 범위가 도면 범위를 이긴다."""
    for k in ("range_user", "range"):
        r = x.get(k) if isinstance(x, dict) else None
        if isinstance(r, dict) and num(r.get("lo")) is not None and num(r.get("hi")) is not None and \
                num(r.get("lo")) != num(r.get("hi")):
            return {"lo": num(r["lo"]), "hi": num(r["hi"]), "unit": r.get("unit") or "", "src": "user" if k == "range_user" else "drawing"}
    return None


def is_analog_block(b):
    return b.get("logic") == "unknown" and b.get("func") not in ("UNKNOWN", "MACRO", "XOR") and not monitor_kind(b)


def consumers(s, idx):
    return _topo(s, idx)["feeds"]


def _consumers(s, idx):
    """아날로그 값을 받는 넷 — 감시 블록 · 아날로그 블록(MED · f(x) …)의 입력."""
    from . import aops
    ins = idx[0]
    out, dig = set(), set()
    for bid, b in s["blocks"].items():
        if monitor_kind(b) or is_analog_block(b):
            out.update(n for n, _, _ in ins[bid])
            if b.get("logic") == "unknown" and aops.op_of(b) == "transfer":
                c = aops.cond_net(s, bid, idx)          # L30 — 전환(T)의 조건(Flag)은 1/0 이다 (아날로그 입력이 아니다)
                if c is not None:
                    dig.add(c)
    return out - dig


_TOPO = {}


def _topo(s, idx):
    """장마다 한 번 — 아날로그 배선(범위 · 값을 받는 선 · 연산자와 그 입출력).  장 사본(사람 값을 얹은 새 결과)이면
    새로 센다 — 열쇠는 그 장의 블록 · 단자 객체 (L28 기억과 같은 규칙: 맞음에는 닿지 않고 같은 계산을 다시 안 한다)."""
    from . import aops
    B = s["blocks"]
    # 범위 · 연산 판정이 읽는 칸의 지문 — 같은 장 객체를 제자리에서 고쳐도(범위를 적음 · 사람 값) 다시 센다
    fp = repr(([(r["n"], r.get("net"), r.get("range"), r.get("range_user")) for r in s["rows"] if r["side"] == "L"],
               [(bid, b.get("func"), b.get("logic"), b.get("label"), b.get("aop"),
                 {k: v for k, v in (b.get("param") or {}).items() if k in _TOPO_PARAMS}) for bid, b in B.items()]))
    k = (id(B), id(s["ports"]), id(s["rows"]))
    hit = _TOPO.get(k)
    if hit is not None and hit[0] is B and hit[1] is s["ports"] and hit[2] is s["rows"] and hit[4] == fp:
        return hit[3]
    ops = {bid: aops.op_of(b) for bid, b in B.items() if b.get("logic") == "unknown"}
    ops = {bid: op for bid, op in ops.items() if op}
    io = {bid: aops._io(s, bid, idx) for bid in ops}
    data = {"nr": _ranges(s, idx), "feeds": _consumers(s, idx), "ops": ops, "io": io,
            "side": {(p["block"], p["net"]): p.get("side") for p in s["ports"]},
            "sel": {bid: selector_of(b) for bid, b in B.items()}}
    if len(_TOPO) > 512:
        _TOPO.clear()
    _TOPO[k] = (B, s["ports"], s["rows"], data, fp)
    return data


_TOPO_PARAMS = ("range", "range_user", "sp_unit", "a_user", "aop_fig", "pins")


def ranges(s, idx):
    return _topo(s, idx)["nr"]


def _ranges(s, idx):
    """넷마다 공학 범위 — 입력 행(도면 · 사람) · 블록(사람)에서 시작해 아날로그 블록을 지나 퍼진다."""
    ins, outs = idx[0], idx[1]
    B = s["blocks"]
    side = {(p["block"], p["net"]): p.get("side") for p in s["ports"]}
    nr = {}
    for r in s["rows"]:
        if r["side"] == "L" and r.get("net") is not None and _rng(r):
            nr[r["net"]] = _rng(r)
    for bid, b in B.items():
        rg = _rng(b.get("param") or {})
        if rg:
            for n, _, _ in outs[bid]:
                nr[n] = rg
    # 설정값을 % 로 적은 감시 블록(19VA `L : 14%`)에 들어오는 값은 범위를 몰라도 % 다 — 4 mA = 0 % · 20 mA = 100 %
    for bid, b in B.items():
        if monitor_kind(b) and str((b.get("param") or {}).get("sp_unit") or "").strip() == "%":
            for n, _, _ in ins[bid]:
                nr.setdefault(n, {"lo": 0.0, "hi": 100.0, "unit": "%", "src": "percent"})
    from . import aops

    def spread():
        for _ in range(len(B) + 1):
            moved = False
            for bid, b in B.items():
                if not is_analog_block(b) or any(n in nr for n, _, _ in outs[bid]):
                    continue
                op = aops.op_of(b) if b.get("logic") == "unknown" else None
                if op and op not in aops.SAME_UNIT:
                    continue                                 # L30 — 곱 · 나눗셈 · 수식 … 은 단위가 바뀐다
                got = [(nr[n], side.get((bid, n))) for n, _, _ in ins[bid] if n in nr]
                if not got:
                    continue
                same = all((g[0]["lo"], g[0]["hi"]) == (got[0][0]["lo"], got[0][0]["hi"]) for g in got)
                rg = got[0][0] if same else next((g[0] for g in got if g[1] == "L"), got[0][0])
                for n, _, _ in outs[bid]:
                    nr[n] = rg
                moved = True
            if not moved:
                break
    spread()
    # L30 — 연산자(Σ · ÷ · × · T · 수식 …)에 들어오는 값의 범위를 도면이 말하지 않으면 4~20 mA 의 정의대로 신호 % (0~100 %).
    # 계장 신호의 뜻 그 자체라 지어낸 값이 아니다 — 'span' 으로 표시하고, 단위가 다른 감시 설정값과는 맞대지 않는다.
    more = False
    driven = {n for bid in B for n, _, _ in outs[bid]}          # 블록이 모는 선은 그 블록이 범위를 정한다 (물려받거나 없음)
    for bid, b in B.items():
        op = aops.op_of(b) if b.get("logic") == "unknown" else None
        if op and op != "const" and not selector_of(b):
            cn = aops.cond_net(s, bid, idx) if op == "transfer" else None
            for n, _, _ in ins[bid]:
                if n == cn or n in driven:
                    continue
                if n not in nr:
                    nr[n] = dict(SPAN)
                    more = True
    if more:
        spread()
    return nr


SPAN = {"lo": 0.0, "hi": 100.0, "unit": "%", "src": "span"}


def nets(s, given, idx, dig=None, detail=None):
    """사람이 준 값 {"block:<id>"|"row:<n>": mA | {"eng": 공학값}} → ({넷: 공학값}, {블록: 공학값}, {키: 정보}).

    아날로그 값을 받는 입력 행은 사람이 안 주면 기본 8 mA (범위를 알 때만 공학값이 선다).
    선택 블록(MED …)은 값을 안 받았으면 입력이 **모두** 정해졌을 때만 범례 이름대로 계산한다 (하나라도 모르면 모름).
    L30 — 그 밖의 아날로그 연산자(Σ · ÷ · × · A · T · 수식 …)는 aops.compute 가 범례 식대로 계산한다.
    dig = {넷: 1/0} — 전환(TRANSFER) 조건 · detail = {} 를 주면 연산자마다 입력 · 출력 · 이유를 담는다 (화면 근거)."""
    from . import aops
    ins, outs = idx[0], idx[1]
    B = s["blocks"]
    given = dict(given or {})
    tp = _topo(s, idx)
    nr, feeds, side, sel = tp["nr"], tp["feeds"], tp["side"], tp["sel"]
    net_v, blk_v, keys = {}, {}, {}

    def put(key, raw, rg, src):
        if isinstance(raw, dict) and num(raw.get("eng")) is not None:
            eng = num(raw["eng"])
            keys[key] = {"ma": to_ma(eng, rg) if rg else None, "eng": eng, "range": rg, "src": "linked"}
            return eng
        ma = ma_ok(raw)
        if ma is None:
            return None
        eng = to_eng(ma, rg) if rg else None
        keys[key] = {"ma": ma, "eng": eng, "range": rg, "src": src}
        return eng

    for r in s["rows"]:
        if r["side"] != "L" or r.get("net") is None:
            continue
        k = f"row:{r['n']}"
        rg = nr.get(r["net"])
        if k in given:
            v = put(k, given[k], rg, "user")
        elif r["net"] in feeds:
            v = put(k, DEFAULT_MA, rg, "default")
        else:
            continue
        if v is not None:
            net_v[r["net"]] = v
    for k, raw in given.items():
        kind, _, x = str(k).partition(":")
        if kind != "block" or x not in B:
            continue
        rg = next((nr[n] for n, _, _ in outs[x] if n in nr), None)
        v = put(k, raw, rg, "user")
        if v is not None:
            blk_v[x] = v
            for n, _, _ in outs[x]:
                net_v[n] = v
    for k, raw in given.items():
        kind, _, x = str(k).partition(":")
        if kind != "net" or x not in s["nets"]:
            continue
        eng = num(raw.get("eng")) if isinstance(raw, dict) else num(raw)
        if eng is not None:                                 # L30 — 연산자 판에서 사람이 그 입력선에 공학값을 바로 넣음
            rg = nr.get(x)
            keys[k] = {"ma": to_ma(eng, rg) if rg else None, "eng": eng, "range": rg, "src": "user"}
            net_v[x] = eng
    ops, io = tp["ops"], tp["io"]
    dig_out = {}
    default_nets = {r["net"] for r in s["rows"] if r["side"] == "L" and r.get("net") is not None
                    and keys.get(f"row:{r['n']}", {}).get("src") == "default"}     # L48 — 기본 8 mA 만 받은 입력 행의 선

    user_nets = {str(k)[4:] for k in given if str(k).startswith("net:")}

    def emit(bid, v, src, out_nets):
        out_nets = [n for n in out_nets if n not in user_nets]      # 사람이 그 선에 넣은 값이 이긴다
        blk_v[bid] = round(v, 6)
        rg = next((nr[n] for n in out_nets if n in nr), None)
        ma = to_ma(blk_v[bid], rg) if rg else None
        if src == "op" and ma is not None and not (MA_LO - 0.8 <= ma <= MA_HI + 0.8):
            ma = None                                   # 연산 결과가 신호 범위를 벗어났다 — mA 로 말하지 않는다
        keys[f"block:{bid}"] = {"ma": ma, "eng": blk_v[bid], "range": rg, "src": src}
        for n in out_nets:
            net_v[n] = blk_v[bid]

    for _ in range(len(B) + 1):
        moved = False
        for bid, b in B.items():
            if bid in blk_v or bid in dig_out:
                continue
            how = sel[bid]
            op = ops.get(bid)
            if not how and op and not (op == "fx" and not aops.params(b).get("table")):
                ii = io[bid][0]
                if aops.is_digital(op):
                    d = _digital(op, b, ii, net_v, dig, default_nets)
                    if d is not None:
                        dig_out[bid] = d
                        moved = True
                    continue
                v, _why = aops.compute(op, b, ii, net_v, dig)
                if v is not None and isinstance(v, float) and (v != v or abs(v) >= 1e12):
                    v = None                                 # 너무 큰 값 · 계산 불가 — 근거 패널이 말한다
                if v is not None:
                    emit(bid, v, "op", io[bid][1])
                    moved = True
                continue
            if not how and is_analog_block(b) and ins[bid]:
                # 보정 함수(f(x)) 같은 블록 — 계산식은 도면이 말하지 않는다.  왼쪽(주 입력) 값이 하나뿐이면 그대로 넘긴다
                main = [net_v.get(n) for n, _, _ in ins[bid] if side.get((bid, n)) == "L"]
                if len(main) == 1 and main[0] is not None:
                    emit(bid, main[0], "pass", [n for n, _, _ in outs[bid]])
                    moved = True
                continue
            if not how or not ins[bid]:
                continue
            vs = [net_v.get(n) for n, _, _ in ins[bid]]
            if any(v is None for v in vs):
                continue
            emit(bid, _calc(how, vs), "calc", [n for n, _, _ in outs[bid]])
            moved = True
        if not moved:
            break
    if detail is not None:
        for bid, op in ops.items():
            b = B[bid]
            ii = io[bid][0]
            if aops.is_digital(op):
                why = "" if bid in dig_out else ("입력 둘의 값과 편차 D 를 알아야 합니다" if op == "dev" and aops.params(b).get("d") is None
                                                  else "입력 둘의 값을 다 알아야 합니다")
            elif bid in blk_v:
                why = aops.compute(op, b, ii, net_v, dig)[1] if not selector_of(b) else ""
                if keys.get(f"block:{bid}", {}).get("src") == "user":
                    why = "사람이 넣은 값 (mA)"
            else:
                v0, why = aops.compute(op, b, ii, net_v, dig) if not selector_of(b) else (None, "입력 값을 다 모르면 계산하지 않습니다")
                if v0 is not None and not why:
                    why = "계산 값이 너무 큽니다 — 입력 값 · 범위를 확인해 주세요 (값 %.3g)" % v0
            nfo = aops.info(op)
            detail[bid] = {"op": op, "ko": nfo.get("ko", op), "eq": nfo.get("eq", ""),
                           "inputs": [{"net": str(n), "pin": (pn or {}).get("name", ""), "coef": (pn or {}).get("coef"),
                                       "value": net_v.get(n)} for n, pn in ii],
                           "outputs": [str(n) for n in io[bid][1]],
                           "out": blk_v.get(bid), "dig": dig_out.get(bid), "why": why,
                           "params": aops.params(b), "cond": aops._cond(ii) if op == "transfer" else None,
                           # L48 — 디지털 값을 읽는 연산(BIT_CNT · EQUAL): 그 입력선이 바뀌면 시뮬레이터가 아날로그를 다시 센다
                           "conds": [n for n, _ in ii] if op in ("count", "equal") else None}
    return net_v, blk_v, keys


def _dev(b, ii, net_v):
    """범례 DEVIATION — |X1 − X2| > D 이면 1 (같으면 0).  D 는 도면(옆 'D : 5') · 사람 값.  모르면 None."""
    from . import aops
    vals = [net_v.get(n) for n, pn in ii if not (pn and pn["name"] in ("FLAG", "C", "COND", "TR", "TRK"))]
    d = aops.params(b).get("d")
    if len(vals) < 2 or any(v is None for v in vals[:2]) or d is None:
        return None
    return 1 if abs(vals[0] - vals[1]) > float(d) else 0


def _equal(ii, net_v, dig, defaults=()):
    """L48 — EQUAL (IN1 · IN2 → OUT): 두 입력이 같으면 1.  **사람이 넣었거나 계산된** 아날로그 값 둘이 다 있으면 그 값으로,
    아니면(기본 8 mA 만 있거나 값이 없으면) 디지털 값 둘로.  둘 다 모르면 None (출력 없음) — 기본값끼리 같다고 1 을 내지 않는다."""
    nets = [n for n, _ in ii][:2]
    if len(nets) < 2:
        return None
    a, b = net_v.get(nets[0]), net_v.get(nets[1])
    if a is not None and b is not None and nets[0] not in defaults and nets[1] not in defaults:
        return 1 if abs(a - b) <= 1e-6 * max(1.0, abs(a), abs(b)) else 0
    da, db = (dig or {}).get(nets[0]), (dig or {}).get(nets[1])
    if da is None or db is None:
        return None
    return 1 if da == db else 0


def _digital(op, b, ii, net_v, dig, defaults=()):
    """1/0 을 내는 연산자 하나의 출력 — DEV · EQUAL."""
    if op == "dev":
        return _dev(b, ii, net_v)
    if op == "equal":
        return _equal(ii, net_v, dig, defaults)
    return None


def monitors(s, net_v, idx, nr=None):
    """감시 블록마다 {block, label, kind, value, sp, sp_src, unit, out} — 값과 설정값이 다 있을 때만 out 이 1/0."""
    ins = idx[0]
    nr = nr if nr is not None else ranges(s, idx)
    out = []
    for bid, b in s["blocks"].items():
        k = monitor_kind(b)
        if not k:
            continue
        v = next((net_v[n] for n, _, _ in ins[bid] if n in net_v), None)
        sp, src = setpoint(b)
        p = b.get("param") or {}
        rg = next((nr[n] for n, _, _ in ins[bid] if n in nr), None)
        unit = str(p.get("sp_unit") or "").strip()
        if rg and rg.get("src") == "span" and unit not in ("", "%"):
            v = None                                     # 신호 % 와 barg 같은 단위는 맞대지 않는다 — 범위를 적으면 맞댄다
        out.append({"block": bid, "label": b.get("label") or "", "kind": k[0], "value": v, "sp": sp, "sp_src": src,
                    "sp_drawing": num(p.get("sp")) if p.get("sp") is not None else None,
                    "sp_label": p.get("sp_label") or "", "level": p.get("sp_level") or k[1],
                    "sp_ma": to_ma(sp, rg) if (rg and sp is not None) else None, "range": rg,
                    "unit": p.get("sp_unit") or (rg or {}).get("unit") or "",
                    "out": compare(k[0], v, sp) if (v is not None and sp is not None) else None})
    return out


# ------------------------------------------------------------------ 도면이 인쇄한 설정값

_RANGE = re.compile(r"(?<![\w.])\(?([-+−]?\d+(?:[.,]\d+)?)\s*~\s*([-+−]?\d+(?:[.,]\d+)?)(?![\w.,])\)?(?:\s+([^\s~]{1,8}))?")


def _read_ranges(s, ws):
    """L27 — 아날로그 입력 행의 공학 범위: 그 행의 선(가로 토막) 바로 아래에 인쇄한 `0~250 barg`.
    선 아래 행 간격 1.5 배 안 · 가로로 그 토막 위에 있는 글줄만.  `4~20mA` 처럼 단위가 붙은 것은 신호 범위라 안 받는다."""
    idx = _idx(s)
    feeds = consumers(s, idx)
    P = s.get("pitch") or 10.0
    n = 0
    for r in s["rows"]:
        if r["side"] != "L" or r.get("net") not in feeds:
            continue
        best = None
        for x0, y0, x1, y1 in (s["nets"].get(r["net"]) or {}).get("segs") or []:
            if abs(y1 - y0) > 0.5:
                continue
            lo, hi = min(x0, x1), max(x0, x1)
            cand = [w for w in ws if y0 < w[1] <= y0 + 1.5 * P and w[0] >= lo - 2 and w[0] <= hi]
            for w in cand:
                if "~" not in w[4]:
                    continue
                line = sorted((u for u in cand if abs(u[3] - w[3]) < 1.0 and u[0] >= w[0] - 1), key=lambda u: u[0])
                m = _RANGE.match(" ".join(u[4] for u in line))
                if not m:
                    continue
                gap = w[1] - y0
                if best is None or gap < best[0]:
                    best = (gap, m)
        if best:
            m = best[1]
            unit = (m.group(3) or "")
            if re.fullmatch(r"\d.*", unit):
                unit = ""
            r["range"] = {"lo": num(m.group(1)), "hi": num(m.group(2)), "unit": unit, "text": m.group(0).strip()}
            n += 1
    return n


def _idx(s):
    from collections import defaultdict
    ins, outs = defaultdict(list), defaultdict(list)
    for p in s["ports"]:
        (ins if p["dir"] == "in" else outs)[p["block"]].append((p["net"], p.get("role", ""), p.get("cell", 0)))
    return ins, outs


_TAGGED = re.compile(r"^(H+\d?|L+\d?)?\s*[:=]\s*([-+−]?\d+(?:[.,]\d+)?)\s*(\S{0,8})")
_LEAD = re.compile(r"^([-+−]?\d+(?:[.,]\d+)?)\s*(\S{0,8})")


def _lines(ws, h):
    """낱말을 글줄로 (바닥이 행 높이 0.4 배 안이면 한 줄 · 왼쪽부터)."""
    out = []
    for w in sorted(ws, key=lambda t: (t[3], t[0])):
        for ln in out:
            if abs(ln[0][3] - w[3]) < h * 0.4:
                ln.append(w)
                break
        else:
            out.append([w])
    return [sorted(ln, key=lambda t: t[0]) for ln in out]


def _read_setpoint(b, ws):
    """감시 블록 하나의 설정값 — 두 꼴을 읽는다 (그 밖은 지어내지 않는다).
    ① 그 블록의 글자를 이름으로 단 값 `L : 14%` · `HH = 191` — 블록 위 · 오른쪽 위 (19VA)
    ② 블록 바로 위의 수 `202.4 barg` (1A1Y) · 수가 아닌 이름 `N2` 은 이름만 (1A5J)."""
    x0, y0, x1, y1 = b["bbox"]
    h, w = max(1.0, y1 - y0), max(1.0, x1 - x0)
    letters = re.sub(r"[^HL]", "", (b.get("label") or "").upper())
    near = [t for t in ws if t[3] <= (y0 + y1) / 2 and t[3] >= y0 - 2 * h and t[2] >= x0 - w and t[0] <= x1 + 3 * w]
    p = b.setdefault("param", {})
    best = None
    for ln in _lines(near, h):
        m = _TAGGED.match(" ".join(t[4] for t in ln))
        # 같은 쪽 글자면 그 블록의 값 — 19VA 는 상자를 `H/` 하나로 그리고 단계를 글자에 적는다 (`HH : 95degC`)
        # · `: 0` (글자 없이 · 19VA p59) 도 그 블록의 값
        if m and (m.group(1) is None or m.group(1)[0] == letters[:1]):
            d = abs(ln[0][3] - y0)
            if best is None or d < best[0]:
                best = (d, m, ln)
    if best:
        _, m, ln = best
        p["sp"], p["sp_unit"] = num(m.group(2)), m.group(3)
        if m.group(1) and m.group(1) != letters:
            p["sp_level"] = m.group(1)                  # 도면이 글자로 적은 경보 단계 (HH · LL …)
        p["sp_text"] = " ".join(t[4] for t in ln)[:40]
        return 1
    cand = [t for t in near if t[3] <= y0 + 0.5 and t[0] <= x1 + w]
    if not cand:
        return 0
    yb = max(t[3] for t in cand)                      # 블록에 가장 가까운 줄
    line = sorted((t for t in cand if abs(t[3] - yb) < h * 0.4), key=lambda t: t[0])
    if not line:
        return 0
    m = _LEAD.match(" ".join(t[4] for t in line))
    if not m:
        # 1A5J — `N2` 처럼 수가 아닌 이름을 인쇄한 설정값: 이름만 남기고 값은 사람이 적는다
        if len(line) == 1 and re.fullmatch(r"[A-Z][A-Z0-9_.\-]{0,7}", line[0][4]):
            p["sp_label"] = line[0][4]
        return 0
    if num(m.group(1)) is None:
        return 0
    p["sp"], p["sp_unit"] = num(m.group(1)), m.group(2)
    p["sp_text"] = " ".join(t[4] for t in line)[:40]
    return 1


def read_drawing(pdf_path, sheets):
    """감시 블록 바로 위에 인쇄한 설정값(`202.4 barg` · `-830 mm`)을 블록 param 에 얹는다 (sp · sp_unit · sp_text).

    자리: 블록 위 변에서 블록 높이 두 배 안 · 가로로 블록과 겹치는(블록 폭만큼 넓힌) 진짜 글자 줄.  그 줄의 첫 낱말이
    수일 때만 — 수가 아니면 설정값이 아니다.  글자가 선으로 그려진 묶음(HRSG)은 낱말이 없어 아무것도 얹지 않는다.
    → 얹은 블록 수"""
    from . import geom, aops
    want = {}
    for s in sheets:
        if s.get("page", 0) <= 0:
            continue
        mons = [(bid, b) for bid, b in s["blocks"].items() if monitor_kind(b) and b.get("bbox")]
        if mons or any(is_analog_block(b) or aops.op_of(b) or (b.get("func") == "UNKNOWN" and not (b.get("label") or b.get("read")))
                       for b in s["blocks"].values()):
            want[s["page"]] = (s, mons)
    if not want:
        return 0
    import pymupdf
    try:
        doc = pymupdf.open(str(pdf_path))
    except Exception:
        return 0
    n = 0
    figs = None
    with doc:
        for page, (s, mons) in want.items():
            if page - 1 >= len(doc):
                continue
            if any(b.get("func") == "UNKNOWN" and not (b.get("label") or b.get("read")) for b in s["blocks"].values()):
                if figs is None:
                    from . import library
                    try:
                        figs = library.load()["figures"]
                    except Exception:
                        figs = []
                n += aops.read_figures(s, doc[page - 1], figs)   # L30 — 글자 없이 그림만 든 연산자 (△ · ∫ …)
            ws = geom.words(doc[page - 1])
            n += _read_ranges(s, ws)
            for bid, b in mons:
                n += _read_setpoint(b, ws)
            n += aops.read_pins(s, ws)                  # L30 — 연산자 입력 이름(IN1 · IN2 : -1 · + · −) · 옆 상수(A : 5%)
    return n
