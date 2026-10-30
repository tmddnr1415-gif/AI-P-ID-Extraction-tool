"""L71 — 아날로그 연산자의 계산 과정: 들어오는 값 → 범례 식 → 값을 넣은 식 → 출력.

  * 판정이 아니다 — 값은 `aops.compute` (디지털은 `analog._digital`) 가 낸 그대로이고, 여기서는 그 계산을 사람이 읽는 식으로
    옮겨 적을 뿐이다 (예: `IN1 + IN2×(−1) = 12 + 3.5×(−1) = 8.5`).  두 입력의 앞 · 뒤(차 · 나눗셈)는 `aops._two` 가 정한 순서 그대로.
  * 입력이 어디서 오는지(`sources`)는 그 장의 선을 거슬러 올라가 입력 행(계기 · 설명)까지 — 중간 연산자는 지나온 길로.
  * L72 시뮬레이션 페이지가 같은 함수를 쓴다(`run_static` · `timeline`) — 도면 판과 페이지의 계산이 어긋나지 않게.
"""
from __future__ import annotations

import math
import re

from . import aops

_NOT_ANALOG = ("FLAG", "C", "COND", "TR", "TRK")


def fmt(v):
    """화면 fmtNum 과 같은 모양 — 1000 이상은 정수, 그 밖은 소수 셋째 자리."""
    if v is None or isinstance(v, float) and not math.isfinite(v):
        return "?"
    v = float(v)
    r = round(v) if abs(v) >= 1000 else round(v * 1000) / 1000
    s = ("%d" % r) if float(r).is_integer() else repr(float(r))
    return s.replace("-", "−")


def _c(v):
    """계수 · 음수 값은 괄호로 — 12 × (−1)."""
    s = fmt(v)
    return f"({s})" if s.startswith("−") else s


def _pn(i):
    return {"name": i["pin"]} if i.get("pin") else None


def _names(ins):
    """입력마다 식에 쓸 이름 — 도면 이름(IN1 · + · A …), 없으면 X1 · X2 …  (+ · − 는 이름이 아니라 부호라 X 로)."""
    out = []
    for k, i in enumerate(ins):
        p = i.get("pin") or ""
        out.append(p if p and p not in ("+", "-", "−", "±") else ("X" if len(ins) == 1 else f"X{k + 1}"))
    return out


def _coef(i, pr):
    c = (pr.get("coef") or {}).get(str(i.get("net")))
    if c is None:
        c = i.get("coef")
    if c is None and i.get("pin") in ("+", "-", "−"):
        c = 1.0 if i["pin"] == "+" else -1.0
    return 1.0 if c is None else float(c)


def _lin(terms):
    """[(계수, 글)] → 'A + B×0.5 − C'."""
    s = ""
    for k, (c, t) in enumerate(terms):
        if c == 1:
            s += t if k == 0 else f" + {t}"
        elif c == -1:
            s += f"−{t}" if k == 0 else f" − {t}"
        else:
            s += (f"{t}×{_c(c)}" if k == 0 else f" + {t}×{_c(c)}")
    return s


def _two_idx(ins, pr, label, op):
    """aops._two 와 같은 규칙으로 (앞, 뒤) 입력의 자리 — 값 대신 자리 번호를 넣어 돌린다."""
    ai = [(i.get("net"), _pn(i)) for i in ins]
    a, b = aops._two(ai, list(range(len(ins))), label, op, pr)
    return (a, b) if a is not None else (None, None)


def trace(op, params, inputs, out=None, dig=None, why="", label="", cond_value=None):
    """→ {"sym": 기호 식, "sub": 값을 넣은 식, "res": 출력 글, "params": [[이름, 값]], "note": 사유}.

    inputs = [{"net", "pin", "coef", "value"}] (analog.nets detail 의 모양) · params = aops.params(b) ·
    out/dig = 그 블록의 출력 (계산은 하지 않는다 — 받은 값을 적는다) · cond_value = 전환 조건 1/0."""
    pr = dict(params or {})
    allin = list(inputs or [])
    ins = [i for i in allin if (i.get("pin") or "") not in _NOT_ANALOG]
    nm = _names(ins)
    vs = [i.get("value") for i in ins]
    res = fmt(out) if out is not None else (str(dig) if dig is not None else "?")
    ps = []

    def P(k, name):
        v = pr.get(k)
        if v is not None:
            ps.append([name, fmt(v) if isinstance(v, (int, float)) else str(v)])
        return v

    sym = sub = ""
    if pr.get("out") is not None and op != "const":
        return {"sym": "M = 사람이 정한 출력값", "sub": fmt(pr["out"]), "res": fmt(pr["out"]), "params": [["출력값 고정", fmt(pr["out"])]],
                "note": why or "사람이 정한 출력값"}
    if op in ("sum", "mean"):
        cs = [_coef(i, pr) for i in ins]
        sym = _lin(list(zip(cs, nm)))
        sub = _lin([(c, _c(v)) for c, v in zip(cs, vs)])
        if op == "mean":
            sym, sub = f"({sym}) / {len(ins)}", f"({sub}) / {len(ins)}"
    elif op == "mul":
        cs = [_coef(i, pr) for i in ins]
        sym = " × ".join(n if c == 1 else f"{_c(c)}×{n}" for c, n in zip(cs, nm))
        sub = " × ".join(_c(v) if c == 1 else f"{_c(c)}×{_c(v)}" for c, v in zip(cs, vs))
    elif op in ("max", "min", "median"):
        f = {"max": "MAX", "min": "MIN", "median": "MED"}[op]
        sym, sub = f"{f}({', '.join(nm)})", f"{f}({', '.join(fmt(v) for v in vs)})"
    elif op in ("diff", "absdiff", "div") or (op == "abs" and len(ins) >= 2) or op == "dev":
        a, b = _two_idx(ins, pr, label, "div" if op == "div" else "diff") if len(ins) >= 2 else (None, None)
        if a is None and op == "dev" and len(ins) >= 2:
            a, b = 0, 1                                     # analog._dev 는 단자 순서대로
        if a is None:
            sym = " ? ".join(nm) or "X1 ? X2"
            sub = "앞 · 뒤 입력을 정해야 합니다"
        else:
            sg = "÷" if op == "div" else "−"
            sym, sub = f"{nm[a]} {sg} {nm[b]}", f"{_c(vs[a])} {sg} {_c(vs[b])}"
            if op in ("absdiff", "abs", "dev"):
                sym, sub = f"|{sym}|", f"|{sub}|"
            if op == "dev":
                d = P("d", "편차 D")
                sym, sub = f"{sym} > D", f"{sub} > {fmt(d)}"
                if vs[a] is not None and vs[b] is not None:
                    sub += f"  ({fmt(abs(vs[a] - vs[b]))} {'>' if dig == 1 else '≤'} {fmt(d)})"
    elif op == "equal":
        sym = f"{' = '.join(nm[:2]) or 'IN1 = IN2'} ?"
        sub = f"{' = '.join(fmt(v) for v in vs[:2])} ?"
    elif op == "count":
        sym = "1 인 디지털 입력의 수"
        sub = "Σ(입력 = 1)"
    else:
        x, xn = (vs[0] if vs else None), (nm[0] if nm else "X")
        if op == "gain":
            k = P("k", "K")
            sym, sub = f"K × {xn}", f"{_c(k)} × {_c(x)}"
        elif op == "rgain":
            k = P("k", "K")
            sym, sub = f"−K × {xn}", f"−{_c(k)} × {_c(x)}"
        elif op == "lag":
            k = pr.get("k")
            ps.append(["k (멈춘 값)", fmt(k if k is not None else 1.0)])
            sym, sub = f"k × {xn}  (정상 상태)", f"{_c(k if k is not None else 1.0)} × {_c(x)}"
        elif op == "leadlag":
            k = pr.get("k") if pr.get("k") is not None else 1.0
            ps.append(["k (멈춘 값)", fmt(k)])
            sym, sub = f"k × {xn}  (정상 상태)", f"{_c(k)} × {_c(x)}"
        elif op == "abs":
            sym, sub = f"|{xn}|", f"|{fmt(x)}|"
        elif op == "sqrt":
            sym, sub = f"√{xn}", f"√{_c(x)}"
        elif op == "pow":
            n = P("n", "n")
            sym, sub = f"{xn} ^ n", f"{_c(x)} ^ {_c(n)}"
        elif op == "hilim":
            h = P("h", "상한 H")
            sym, sub = f"MIN({xn}, H)", f"MIN({fmt(x)}, {fmt(h)})"
        elif op == "lolim":
            lo = P("l", "하한 L")
            sym, sub = f"MAX({xn}, L)", f"MAX({fmt(x)}, {fmt(lo)})"
        elif op == "bias":
            bv = P("b", "바이어스 b")
            neg = aops._lab(label) == "-"
            sym, sub = f"{xn} {'−' if neg else '+'} b", f"{_c(x)} {'−' if neg else '+'} {_c(bv)}"
        elif op in ("velim", "convert"):
            sym, sub = xn, fmt(x)
        elif op == "deriv":
            sym, sub = f"Td × d{xn}/dt", "Td × 0  (값이 멈춰 있음)"
        elif op == "const":
            v = pr.get("value")
            sym, sub = "A", fmt(v)
            if v is not None:
                ps.append(["상수 A", fmt(v)])
        elif op == "fx":
            tb = pr.get("table")
            if tb:
                pts = sorted((float(a), float(b)) for a, b in tb)
                ps.append(["F(X) 표", " · ".join(f"({fmt(a)}, {fmt(b)})" for a, b in pts)])
                seg = next(((p, q) for p, q in zip(pts, pts[1:]) if x is not None and p[0] <= x <= q[0]), None)
                if x is None:
                    sym, sub = f"f({xn})", f"f(?)"
                elif seg and seg[1][0] != seg[0][0]:
                    (xa, ya), (xb, yb) = seg
                    sym = f"Ya + (Yb − Ya) × ({xn} − Xa) / (Xb − Xa)"
                    sub = f"{_c(ya)} + ({_c(yb)} − {_c(ya)}) × ({_c(x)} − {_c(xa)}) / ({_c(xb)} − {_c(xa)})"
                else:
                    end = pts[0] if x <= pts[0][0] else pts[-1]
                    sym, sub = f"f({xn}) — 표 끝 값", f"f({fmt(x)}) = {fmt(end[1])}"
            else:
                sym, sub = f"f({xn}) = {xn}", f"{fmt(x)}  (표 없음 — 그대로)"
        elif op == "transfer":
            c = pr.get("c") if pr.get("c") is not None else cond_value
            m = re.match(r"조건 ([01]) →", why or "")
            if c is None and m:
                c = int(m.group(1))                         # compute 가 읽은 조건 (시뮬레이션의 디지털 값)
            sym = "C = 1 → IN1 · C = 0 → IN2"
            if c is None:
                sub = "C = ?"
            else:
                want = "IN1" if int(c) == 1 else "IN2"
                v = next((i.get("value") for i in allin if i.get("pin") == want), None)
                sub = f"C = {int(c)} → {want} = {fmt(v)}"
        elif op == "pid":
            tr = next((i for i in allin if i.get("pin") in ("TR", "TRK")), None)
            sym = "제어기 계산 (추종 Tr · 수동 출력)"
            sub = f"Tr = {fmt(tr.get('value'))}" if tr and tr.get("value") is not None else "수동 출력값을 넣어 주세요"
        elif op == "formula":
            expr = aops.formula_expr(label) or "?"
            env = {n: v for n, v in zip(nm, vs)}
            names = aops.formula_vars(expr) or []
            if len(names) == 1 and len(ins) == 1 and names[0] not in env:
                env[names[0]] = vs[0]
            for k, v in (pr.get("vars") or {}).items():
                env[k.upper()] = v
            for k, v in (pr.get("vars") or {}).items():
                ps.append([k.upper(), fmt(v)])               # 사람이 넣은 수식 글자 값 (입력선 값은 ① 에 있다)
            sym = expr
            sub = re.sub(r"\b([A-Za-z]\w*)\b", lambda m: _c(env[m.group(1).upper()]) if m.group(1).upper() in env
                         and m.group(1).upper() in names else m.group(1), expr)
        elif op in ("integral", "ft", "counter"):
            sym, sub = (aops.info(op).get("eq") or op), "시간에 따라 정해지는 값"
        else:
            sym, sub = (aops.info(op).get("eq") or op or "?"), ""
    if op in ("sum", "mean", "mul") and pr.get("coef"):
        ps.append(["입력 계수", " · ".join(f"{nm[k]} {_c(_coef(i, pr))}" for k, i in enumerate(ins))])
    if sym.startswith("M = ") or sym.startswith("M ="):
        sym = sym[3:].lstrip("= ").strip()                  # 범례 식(eq)을 그대로 쓴 것 — M = 를 두 번 적지 않는다
    return {"sym": f"M = {sym}" if op not in ("dev", "equal", "count") else sym,
            "sub": sub, "res": res, "params": ps, "note": why or ""}


def _blk_name(b):
    return (b.get("label") or b.get("func") or "").strip()


def sources(s, net, self_bid, idx, ops, io, depth=6):
    """그 선이 어디서 오나 → {"kind": "row" | "op" | "block" | "none", "text", "row", "block", "via": [블록 이름], "origins": [입력 행 글]}.
    중간 연산자를 지나 그 장의 입력 행(계기)까지 거슬러 올라간다 (최대 depth 단 · 같은 블록 두 번 안 감)."""
    rows_by_net = {}
    for r in s["rows"]:
        if r["side"] == "L" and r.get("net") is not None:
            rows_by_net.setdefault(r["net"], r)
    drivers = {}
    for bid, oo in idx[1].items():
        for n, _, _ in oo:
            drivers.setdefault(n, bid)
    for bid in ops:
        for n in io[bid][1]:
            drivers[n] = bid

    def row_txt(r):
        return f"입력 {r['n']}행" + (f" · {r['desc']}" if r.get("desc") else "") + (f" · {r['fm']}" if r.get("fm") else "")

    r = rows_by_net.get(net)
    if r is not None:
        return {"kind": "row", "text": row_txt(r), "row": r["n"], "desc": r.get("desc") or "", "via": [], "origins": [row_txt(r)]}
    bid = drivers.get(net)
    if bid is None or bid == self_bid:
        return {"kind": "none", "text": f"선 {net}", "via": [], "origins": []}
    b = s["blocks"][bid]
    head = {"kind": "op" if bid in ops else "block", "text": f"{_blk_name(b) or bid} ({bid})", "block": bid,
            "op": ops.get(bid), "via": [], "origins": []}
    seen, todo, origins = {self_bid, bid}, [(bid, 0)], []
    while todo:
        cur, dep = todo.pop(0)
        if dep >= depth:
            continue
        nets_in = [n for n, _ in io[cur][0]] if cur in ops else [n for n, _, _ in idx[0].get(cur, [])]
        for n in nets_in:
            if n in rows_by_net:
                t = row_txt(rows_by_net[n])
                if t not in origins:
                    origins.append(t)
                continue
            up = drivers.get(n)
            if up is not None and up not in seen:
                seen.add(up)
                head["via"].append(f"{_blk_name(s['blocks'][up]) or up} ({up})")
                todo.append((up, dep + 1))
    head["origins"] = origins[:8]
    return head


# ------------------------------------------------------------------ L72 시뮬레이션 페이지 — 같은 계산

def run_static(op, inputs, params=None, label="", cond=None):
    """페이지에서 사람이 넣은 값으로 한 블록을 센다 → {"out", "dig", "why", "trace"}.
    inputs = [{"pin", "coef", "value"}] · cond = 전환 조건 1/0 (TRANSFER) · 디지털 입력(BIT COUNT)은 value 0/1."""
    from . import analog
    pr = {k: v for k, v in (params or {}).items() if v is not None and v != ""}
    ins = []
    for k, i in enumerate(inputs or []):
        net = str(i.get("net") or f"n{k}")
        pin = (i.get("pin") or "").strip().upper() or None
        pn = {"name": pin} if pin else None
        if pn and i.get("coef") is not None:
            pn["coef"] = float(i["coef"])
        ins.append({"net": net, "pin": pin or "", "coef": i.get("coef"), "value": _f(i.get("value")), "pn": pn})
    if op == "transfer" and not any(i["pin"] in ("FLAG", "C", "COND") for i in ins):
        ins.append({"net": "cond", "pin": "FLAG", "coef": None, "value": None, "pn": {"name": "FLAG"}})
    ii = [(i["net"], i["pn"]) for i in ins]
    net_v = {i["net"]: i["value"] for i in ins if i["value"] is not None}
    dig = {}
    if op == "transfer" and cond is not None:
        dig["cond"] = int(cond)
    if op in ("count", "equal"):
        dig.update({i["net"]: (1 if (i["value"] or 0) >= 0.5 else 0) for i in ins})
    b = {"label": label or "", "param": {"a_user": pr}}
    out = dg = None
    why = ""
    if op == "leadlag":
        x = ins[0]["value"] if ins else None
        k = _f(pr.get("k"))
        k = 1.0 if k is None else k
        out, why = (k * x, "멈춘 값(정상 상태)의 값입니다") if x is not None else (None, "입력 값을 모릅니다")
    elif aops.is_digital(op):
        dg = analog._digital(op, b, ii, net_v, dig)
        if dg is None:
            why = "입력 둘의 값과 편차 D 를 알아야 합니다" if op == "dev" else "입력 값을 다 알아야 합니다"
    else:
        out, why = aops.compute(op, b, ii, net_v, dig)
    tr = trace(op, aops.params(b), [{k: i[k] for k in ("net", "pin", "coef", "value")} for i in ins], out, dg, why, label,
               cond_value=dig.get("cond"))
    return {"out": out, "dig": dg, "why": why, "trace": tr}


def _f(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


# 범례 어휘(config/logic_analog.yaml)에 없는 시험용 블록 — 식별에는 쓰지 않는다 (페이지 전용)
EXTRA_OPS = {"leadlag": {"ko": "앞섬/지연 (LEAD/LAG)", "eq": "M = k·(1 + T₁s)/(1 + T₂s)·X — 멈춘 값에서는 M = k·X"}}

TIME_OPS = {
    "lag": [["k", "이득 k", 1.0], ["t", "시정수 T (s)", 5.0]],
    "leadlag": [["k", "이득 k", 1.0], ["tlead", "앞섬 T₁ (s)", 2.0], ["tlag", "지연 T₂ (s)", 5.0]],
    "velim": [["r", "변화율 한도 (단위/s)", 2.0]],
    "integral": [["t", "적분 시간 T₁ (s)", 10.0]],
    "deriv": [["t", "미분 시간 Td (s)", 2.0]],
}
MAX_PTS = 2000


def profile(kind, x0, x1, t1, T, t):
    """시험 입력: step (t1 에서 x0 → x1) · ramp (t1 부터 T 까지 x0 → x1) · sine (가운데 x0 · 진폭 x1 · 주기 t1)."""
    if kind == "ramp":
        if t <= t1:
            return x0
        return x0 + (x1 - x0) * min(1.0, (t - t1) / max(1e-9, T - t1))
    if kind == "sine":
        return x0 + x1 * math.sin(2 * math.pi * t / max(1e-9, t1))
    return x0 if t < t1 else x1


def timeline(op, params, inp, T=60.0, dt=None):
    """시간에 따라 변하는 블록의 응답 → {"t", "x", "y", "eq"}.  처음엔 x0 에서 정상 상태(멈춘 값)로 둔다."""
    if op not in TIME_OPS:
        raise ValueError("시간 그래프가 없는 연산입니다")
    pr = {k: d for k, _, d in TIME_OPS[op]}
    for k, v in (params or {}).items():
        fv = _f(v)
        if k in pr and fv is not None:
            pr[k] = fv
    T = max(1.0, min(3600.0, float(T)))
    n = MAX_PTS if dt is None else max(2, min(MAX_PTS, int(T / max(1e-6, float(dt)))))
    dt = T / n
    kind = (inp or {}).get("kind", "step")
    x0, x1 = _f((inp or {}).get("x0")) or 0.0, _f((inp or {}).get("x1"))
    x1 = 100.0 if x1 is None else x1
    t1 = _f((inp or {}).get("t1"))
    t1 = 5.0 if t1 is None else t1
    sub = 20                                              # 점 사이 작은 걸음 (빠른 시정수에도 안정)
    h = dt / sub
    k = pr.get("k", 1.0)
    xs, ys, ts = [], [], []
    x_prev = profile(kind, x0, x1, t1, T, 0.0)
    z = x_prev                                            # 지연 상태
    y = {"lag": k * x_prev, "leadlag": k * x_prev, "velim": x_prev, "integral": 0.0, "deriv": 0.0}[op]
    tf = max(1e-6, pr.get("t", 1.0) / 8.0)                # 미분은 걸러 낸다 (Td/8)
    for i in range(n + 1):
        t = i * dt
        if i:
            for j in range(sub):
                tt = t - dt + (j + 1) * h
                x = profile(kind, x0, x1, t1, T, tt)
                if op == "lag":
                    tau = max(1e-6, pr["t"])
                    y += (k * x - y) * (1 - math.exp(-h / tau))
                elif op == "leadlag":
                    tau = max(1e-6, pr["tlag"])
                    z += (x - z) * (1 - math.exp(-h / tau))
                    a = pr["tlead"] / tau
                    y = k * (a * x + (1 - a) * z)
                elif op == "velim":
                    r = abs(pr["r"])
                    y += max(-r * h, min(r * h, x - y))
                elif op == "integral":
                    y += x * h / max(1e-6, pr["t"])
                elif op == "deriv":
                    z += (x - z) * (1 - math.exp(-h / tf))
                    y = pr["t"] * (x - z) / tf
                x_prev = x
        ts.append(round(t, 6))
        xs.append(profile(kind, x0, x1, t1, T, t))
        ys.append(y)
    eq = {"lag": "M(s) = k / (1 + T·s) · X(s)", "leadlag": "M(s) = k · (1 + T₁·s) / (1 + T₂·s) · X(s)",
          "velim": "|dM/dt| ≤ r — 그 안에서 M → X", "integral": "M = (1/T₁) ∫ X dt", "deriv": "M = Td · dX/dt (Td/8 로 걸러 냄)"}[op]
    return {"t": ts, "x": xs, "y": ys, "eq": eq, "params": pr}
