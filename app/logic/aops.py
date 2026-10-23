"""L30 — 아날로그 연산자: 무엇인가(식별) · 입력 선 끝에 인쇄된 이름(IN1 · IN2 : -1 · + · − · Flag · Tr · A) · 계산.

  * 식별은 범례 이름(FUNCTION 칸) 또는 상자 안 기호 — 어휘는 config/logic_analog.yaml (ISA-S5.2 · 범례 'SIGNAL PROCESSING
    SYMBOLS').  판정 못 한 블록(UNKNOWN)과 이름만 붙은 아날로그 블록(logic unknown)만 본다 — 게이트는 건드리지 않는다.
  * 계산은 범례 MATH EQUATION 그대로 (sum · mean · diff · mul · div · max · min · …).  계수 · 부호는 도면이 입력 선 끝에
    인쇄한 것(`IN2 : -1` · `+` · `-`)이 정하고, 상수는 블록 옆에 인쇄한 것(`A : 5%`)이 정한다.  도면이 말하지 않는 값
    (K · b · H · L · F(X) 표 · PID 출력 …)은 사람이 블록을 눌러 넣는다 — 지어내지 않는다 (없으면 그 출력은 '모름').
  * 시간이 흐르는 연산(적분 · 지연 · 변화율 제한)은 시뮬레이터가 값만 다룬다 — 멈춘 값에서의 결과(정상 상태)를 내고 그렇게 말한다.
"""
from __future__ import annotations

import ast
import math
import operator
import re
from functools import lru_cache
from pathlib import Path

import yaml


@lru_cache(maxsize=1)
def vocab():
    p = Path(__file__).resolve().parent.parent.parent / "config" / "logic_analog.yaml"
    try:
        from app import paths
        p2 = paths.resource("config", "logic_analog.yaml")
        if p2.exists():
            p = p2
    except Exception:
        pass
    v = yaml.safe_load(p.read_text(encoding="utf-8"))
    by_name, by_label = {}, {}
    for group in ("ops", "digital_ops"):
        for op, e in (v.get(group) or {}).items():
            for n in e.get("names") or []:
                by_name[_key(n)] = op
            for lab in e.get("labels") or []:
                by_label[_lab(lab)] = op
    v["_by_name"], v["_by_label"] = by_name, by_label
    return v


def _key(t):
    return re.sub(r"\s+", " ", str(t or "").upper()).strip()


def _lab(t):
    return re.sub(r"\s+", "", str(t or "").upper()).replace("−", "-")


def info(op):
    v = vocab()
    return (v.get("ops") or {}).get(op) or (v.get("digital_ops") or {}).get(op) or {}


def is_digital(op):
    return op in (vocab().get("digital_ops") or {})


def op_of(b):
    """블록 → 연산 이름 | None.  게이트 · 메모리 · 타이머 · 감시 블록은 아니다 (logic 이 unknown 인 것만)."""
    if b.get("logic") != "unknown" or b.get("func") in ("MACRO", "XOR"):
        return None
    if b.get("aop"):
        return b["aop"]
    p = b.get("param") or {}
    if isinstance(p.get("a_user"), dict) and p["a_user"].get("op"):
        return p["a_user"]["op"]                      # 사람이 고른 연산
    if isinstance(p.get("aop_fig"), dict) and p["aop_fig"].get("op"):
        return p["aop_fig"]["op"]                     # 안 그림이 범례 그림과 맞음 (△ · ∫ …)
    v = vocab()
    lab = (b.get("label") or b.get("read") or "").strip()
    L = _lab(lab)
    if re.match(r"^OUT\s*=", lab.upper()):
        return "formula"
    f = _key(b.get("func"))
    if f and f != "UNKNOWN" and f in v["_by_name"]:
        return v["_by_name"][f]
    if not L:
        return None
    if L in v["_by_label"]:
        return v["_by_label"][L]
    if L.startswith("÷"):
        return "div"
    if re.fullmatch(r"T\d{0,2}", L):                    # T · T1 · T2 — TRANSFER (19VA 는 아래 첨자 번호를 붙인다)
        return "transfer"
    if re.fullmatch(r"[∑Σ]/N\d*", L):
        return "mean"
    return None


# ------------------------------------------------------------------ 입력 선 끝의 이름 · 블록 옆의 상수 (도면에서 읽는다)

_PIN = re.compile(r"^(IN\d{1,2}|X\d{1,2}|TR|TRK|FLAG|C|COND|SP|PV|FF|AT|[A-H]|\+|-|−|±)$", re.I)
_NUMTXT = re.compile(r"^[-+−]?\d+(?:[.,]\d+)?")
_CONST = re.compile(r"^([A-Z]{1,2})\s*[:=]\s*([-+−]?\d+(?:[.,]\d+)?)\s*([^\s\d][^\s]*)?(?=\s|$)", re.I)


def _num(t):
    try:
        return float(str(t).replace("−", "-").replace(",", "."))
    except (TypeError, ValueError):
        return None


def read_pins(s, ws):
    """그 장의 아날로그 연산 블록마다 입력 선 끝 이름 · 계수, 블록 옆 상수 · 매개변수를 param 에 얹는다.
    → 얹은 블록 수.  ws = geom.words(page) (표시 좌표).
    이름 낱말 하나는 단자 하나에만 붙는다 — 장 전체에서 가까운 짝부터 (위 블록의 출력 단자가 아래 블록 입력 이름을 가져가지 않게)."""
    P = s.get("pitch") or 10.0
    n = 0
    boxes = [b["bbox"] for b in s["blocks"].values() if b.get("bbox")]

    def inside(w):
        cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
        return any(x0 < cx < x1 and y0 < cy < y1 for x0, y0, x1, y1 in boxes)
    ws = [w for w in ws if not inside(w)]             # 상자 안 글자(블록 이름)는 옆 글줄에 붙지 않는다
    lines = _lines(ws)
    ops = {bid: op_of(b) for bid, b in s["blocks"].items() if b.get("bbox")}
    ops = {bid: op for bid, op in ops.items() if op}
    cand = []
    for p in s["ports"]:
        if p["block"] in ops and p.get("at"):
            for d, w in _pin_cands(p, s["blocks"][p["block"]]["bbox"], ws, P):
                cand.append((d, id(p), p, w))
    pins, used_p, used_w = {}, set(), set()
    for d, pid, p, w in sorted(cand, key=lambda c: c[0]):
        if pid in used_p or id(w) in used_w:
            continue
        used_p.add(pid)
        used_w.add(id(w))
        pins.setdefault(p["block"], {})[str(p["net"])] = _pin_info(w, lines)
    for bid, op in ops.items():
        b = s["blocks"][bid]
        x0, y0, x1, y1 = b["bbox"]
        prm = {}
        # 블록 옆 'A : 5%' · 'K : 2' · 'H : 100' — 블록 위 · 오른쪽 · 왼쪽 몇 행 간격 안의 한 줄
        best = None
        for ln in lines:
            lx0, ly0, lx1, ly1, text = ln
            m = _CONST.match(text)
            if not m:
                continue
            cx, cy = (lx0 + lx1) / 2, (ly0 + ly1) / 2
            if not (lx0 <= x1 + 4 * P and lx1 >= x0 - 4 * P and y0 - 2.5 * P <= cy <= y1 + 1.5 * P):
                continue
            if x0 - 0.5 <= cx <= x1 + 0.5 and y0 - 0.5 <= cy <= y1 + 0.5:
                continue                                  # 상자 안 글자는 이름이다
            d = max(0.0, x0 - lx1, lx0 - x1) + max(0.0, y0 - ly1, ly0 - y1)
            key = m.group(1).upper()
            if best is None or d < best[0]:
                best = (d, key, _num(m.group(2)), (m.group(3) or "").strip(), m.group(0).strip())
            prm.setdefault(key.lower(), {"v": _num(m.group(2)), "unit": (m.group(3) or "").strip(), "text": m.group(0).strip(), "d": d})
        if op == "const" and best:
            b.setdefault("param", {})["a_const"] = {"v": best[2], "unit": best[3], "text": best[4]}
        par = {k: {"v": e["v"], "unit": e["unit"], "text": e["text"]} for k, e in prm.items()
               if k in ("k", "b", "h", "l", "d", "n", "t") and e["d"] <= 3 * P}
        if pins.get(bid) or par or (op == "const" and best):
            b.setdefault("param", {})
            if pins.get(bid):
                b["param"]["pins"] = pins[bid]
            if par:
                b["param"]["a_drawing"] = par
            n += 1
    return n


def _lines(ws):
    """같은 줄(가운데 높이가 글자 높이 반 안)에서 왼쪽부터 이어진 낱말(틈이 글자 높이 1.2 배 안)을 한 줄로 — (x0, y0, x1, y1, 글)."""
    rows = []
    for w in sorted(ws, key=lambda w: (w[1] + w[3]) / 2):
        cy, h = (w[1] + w[3]) / 2, max(1.0, w[3] - w[1])
        if rows and abs(cy - rows[-1][0]) < h * 0.5:
            rows[-1][1].append(w)
        else:
            rows.append([cy, [w]])
    out = []
    for _, band in rows:
        cur = None
        for w in sorted(band, key=lambda w: w[0]):
            h = max(1.0, w[3] - w[1])
            if cur and -h * 0.3 <= w[0] - cur[2] < h * 1.2:
                cur = [cur[0], min(cur[1], w[1]), max(cur[2], w[2]), max(cur[3], w[3]), cur[4] + " " + w[4]]
            else:
                if cur:
                    out.append(tuple(cur))
                cur = [w[0], w[1], w[2], w[3], w[4]]
        if cur:
            out.append(tuple(cur))
    return out


def _pin_cands(p, bbox, ws, P):
    """단자 하나 둘레(행 간격 2.5 배) · 상자 바깥쪽의 입력 이름 낱말 → [(점수, 낱말)].
    점수는 선을 따라가는 방향보다 가로지르는 방향을 두 배로 센다 — 이름은 선 옆에 붙어 인쇄된다 (위 단자의 이름이
    왼쪽 단자에 붙지 않게)."""
    x, y = p["at"]
    x0, y0, x1, y1 = bbox
    side = p.get("side") or ""
    R = 2.5 * P
    out = []
    for w in ws:
        t = w[4].strip()
        if not _PIN.match(t):
            continue
        cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
        if x0 + 0.5 < cx < x1 - 0.5 and y0 + 0.5 < cy < y1 - 0.5:
            continue
        if side == "L" and cx > x0 + 1 or side == "R" and cx < x1 - 1 or side == "T" and cy > y0 + 1 or \
                side == "B" and cy < y1 - 1:
            continue
        d = math.hypot(cx - x, cy - y)
        if d <= R:
            dx, dy = abs(cx - x), abs(cy - y)
            out.append((dx + 2 * dy if side in ("L", "R") else dy + 2 * dx if side in ("T", "B") else d, w))
    return out


def _pin_info(w, lines):
    """입력 이름 낱말 → {name, coef} — 같은 줄 오른쪽 ': -1' 은 그 입력의 계수 · '+' '−' 는 ±1."""
    name = w[4].strip().upper().replace("−", "-")
    out = {"name": name}
    if name in ("+", "-"):
        out["coef"] = 1.0 if name == "+" else -1.0
    for ln in lines:
        if ln[0] <= w[0] + 0.5 <= ln[2] and abs((ln[1] + ln[3]) / 2 - (w[1] + w[3]) / 2) < (w[3] - w[1]) * 0.6:
            m = re.match(r"^\S+\s*:\s*([-+−]?\d+(?:[.,]\d+)?)$", ln[4].strip())
            if m and ln[4].strip().upper().startswith(name):
                out["coef"] = _num(m.group(1))
            break
    return out


# ------------------------------------------------------------------ 계산

def params(b):
    """사람이 넣은 값이 도면 값을 이긴다 → {k: 값}."""
    p = b.get("param") or {}
    out = {k: e.get("v") for k, e in (p.get("a_drawing") or {}).items() if isinstance(e, dict)}
    if isinstance(p.get("a_const"), dict) and p["a_const"].get("v") is not None:
        out["value"] = p["a_const"]["v"]
    for k, v in (p.get("a_user") or {}).items():
        if k in ("by", "at"):
            continue
        out[k] = v
    return out


def _name_order(pin):
    m = re.match(r"^(IN|X)(\d+)$", (pin or {}).get("name") or "")
    return int(m.group(2)) if m else None


def _inputs(s, bid, idx):
    """아날로그 입력 [(넷, 이름 정보)] — 들어오는 단자 + 화살 방향을 잘못 읽었어도 입력 이름(IN · + · −)이 붙은 단자.
    순서: IN1 · IN2 … 이름 순 → 이름 없는 것은 단자 순."""
    ins, outs = idx[0], idx[1]
    if op_of(s["blocks"][bid]) == "const":
        return []                                     # 상수는 들어오는 것이 없다 — 화살을 거꾸로 읽은 단자도 출력이다
    pins = (s["blocks"][bid].get("param") or {}).get("pins") or {}
    got, seen = [], set()
    for n, _, _ in ins[bid]:
        if n not in seen:
            seen.add(n)
            got.append((n, pins.get(str(n))))
    on = list(dict.fromkeys(n for n, _, _ in outs[bid]))
    cn = _const_nets(s)
    for n in on:
        # 화살을 거꾸로 읽은 입력: 상수(A)가 모는 선 · 또는 나가는 단자가 둘 이상인데 입력 이름(IN · + · −)이 붙은 것
        pn = pins.get(str(n))
        if n in seen:
            continue
        if n in cn and cn[n] != bid or (len(on) >= 2 and pn and (_name_order(pn) or pn["name"] in ("+", "-")) and
                                         len([m for m in on if m not in seen]) >= 2):
            seen.add(n)
            got.append((n, pn))
    got.sort(key=lambda x: (_name_order(x[1]) is None, _name_order(x[1]) or 0))
    return got


def _io(s, bid, idx):
    """(입력 [(넷, 이름)], 출력 [넷]).  나가는 선이 하나도 없는데 이름 붙은 입력(IN1 · IN2 …) 옆에 이름 없는 들어오는 단자가
    꼭 하나 남으면 그것이 출력이다 (19VA T 블록 — 아래로 나가는 선의 화살을 들어오는 것으로 읽었다)."""
    ii = _inputs(s, bid, idx)
    if op_of(s["blocks"][bid]) == "const":
        return ii, _const_outs(idx, bid)
    seen = {n for n, _ in ii}
    oo = list(dict.fromkeys(n for n, _, _ in idx[1][bid] if n not in seen))
    if not oo and any(pn for _, pn in ii):
        nameless = [n for n, pn in ii if not pn]
        has_cond = any(pn and pn["name"] in ("FLAG", "C", "COND") for _, pn in ii)
        if len(nameless) == 1 and (op_of(s["blocks"][bid]) != "transfer" or has_cond):
            oo = nameless
            ii = [x for x in ii if x[0] != nameless[0]]
    return ii, oo


def inputs(s, bid, idx):
    return _io(s, bid, idx)[0]


def _const_outs(idx, bid):
    seen = []
    for n, _, _ in idx[1][bid] + idx[0][bid]:
        if n not in seen:
            seen.append(n)
    return seen


_CN = {}


def _const_nets(s):
    """상수(A) 블록이 닿은 선 → 그 상수 블록 — 상수에는 들어오는 것이 없으므로 그 선은 상수가 몬다 (장마다 한 번)."""
    k = id(s["ports"])
    hit = _CN.get(k)
    if hit is not None and hit[0] is s["ports"]:
        return hit[1]
    m = {}
    for p in s["ports"]:
        b = s["blocks"].get(p["block"])
        if b is not None and b.get("logic") == "unknown" and op_of(b) == "const":
            m.setdefault(p["net"], p["block"])
    if len(_CN) > 256:
        _CN.clear()
    _CN[k] = (s["ports"], m)
    return m


def outputs(s, bid, idx):
    return _io(s, bid, idx)[1]


_SAFE = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
         ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos}
_FUNCS = {"SQRT": math.sqrt, "LOG": math.log10, "LOG10": math.log10, "LN": math.log, "EXP": math.exp, "ABS": abs,
          "MIN": min, "MAX": max}


def formula_expr(label):
    m = re.match(r"^\s*OUT\s*=\s*(.+)$", label or "", re.I)
    return m.group(1).strip() if m else None


def formula_vars(expr):
    try:
        tree = ast.parse(expr.replace("^", "**"), mode="eval")
    except SyntaxError:
        return None
    return sorted({n.id.upper() for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id.upper() not in _FUNCS})


def eval_formula(expr, env):
    """도면 수식을 안전하게 계산 — 사칙 · 거듭제곱(^) · 괄호 · sqrt/log/exp/abs/min/max 만."""
    tree = ast.parse(expr.replace("^", "**"), mode="eval")

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.BinOp) and type(n.op) in _SAFE:
            return _SAFE[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _SAFE:
            return _SAFE[type(n.op)](ev(n.operand))
        if isinstance(n, ast.Name):
            v = env.get(n.id.upper())
            if v is None:
                raise KeyError(n.id)
            return float(v)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id.upper() in _FUNCS:
            return float(_FUNCS[n.func.id.upper()](*[ev(a) for a in n.args]))
        raise ValueError("허용하지 않는 식")
    return ev(tree)


def _interp(table, x):
    pts = sorted((float(a), float(b)) for a, b in table)
    if not pts:
        return None
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        if xa <= x <= xb:
            return ya if xb == xa else ya + (yb - ya) * (x - xa) / (xb - xa)
    return None


def compute(op, b, ins, net_v, dig=None):
    """→ (값 | None, 이유 글 | "").  ins = [(넷, 이름 정보)] · net_v = 아날로g 값 · dig = 디지털 값 (TRANSFER 조건)."""
    pr = params(b)
    if pr.get("out") is not None and op not in ("const",):
        return float(pr["out"]), "사람이 정한 출력값"
    lab = (b.get("label") or b.get("read") or "")
    if op == "count":
        # L48 — BIT COUNTER: 입력은 디지털(1/0) 선이고 출력은 1 인 입력의 수 (범례: COUNTS THE NUMBER OF BOOLEAN INPUTS
        # THAT ARE CURRENTLY SET TO 1).  하나라도 모르면 세지 않는다.
        dv = [(dig or {}).get(n) for n, _ in ins]
        if not dv or any(v is None for v in dv):
            return None, "디지털 입력 값을 다 알아야 셉니다"
        return float(sum(1 for v in dv if v == 1)), ""
    analog_ins = [(n, pn) for n, pn in ins if not (pn and pn["name"] in ("FLAG", "C", "COND", "TR", "TRK"))]
    vals = [net_v.get(n) for n, _ in analog_ins]
    coefs = []
    user_coef = pr.get("coef") or {}
    for n, pn in analog_ins:
        c = user_coef.get(str(n))
        if c is None:
            c = (pn or {}).get("coef")
        if c is None and (pn or {}).get("name") in ("+", "-", "−"):
            c = 1.0 if pn["name"] == "+" else -1.0    # L51 — 범례: INPUTS MAY BE LABELED WITH POSITIVE OR NEGATIVE SIGNS
        coefs.append(1.0 if c is None else float(c))
    known = [v for v in vals if v is not None]
    full = vals and len(known) == len(vals)
    if op == "const":
        v = pr.get("value")
        return (float(v), "") if v is not None else (None, "도면에 값이 없습니다 — 눌러서 값을 넣어 주세요")
    if op in ("sum", "mean", "max", "min", "median", "mul") and not full:
        return None, "입력 값을 다 모르면 계산하지 않습니다"
    if op == "sum":
        return sum(c * v for c, v in zip(coefs, vals)), ""
    if op == "mean":
        return sum(c * v for c, v in zip(coefs, vals)) / len(vals), ""
    if op == "max":
        return max(vals), ""
    if op == "min":
        return min(vals), ""
    if op == "median":
        import statistics
        return statistics.median(vals), ""
    if op == "mul":
        r = 1.0
        for c, v in zip(coefs, vals):
            r *= c * v
        return r, ""
    if op in ("diff", "absdiff", "div") or (op == "abs" and len(analog_ins) >= 2):
        if len(vals) < 2 or not full:
            return None, "입력 둘의 값을 다 알아야 합니다"
        a, bb = _two(analog_ins, vals, lab, op, pr)
        if a is None:
            return None, "어느 입력에서 어느 입력을 빼는지(+ · −) 도면에 없습니다 — 눌러서 정해 주세요"
        if op == "div":
            return (a / bb, "") if bb else (None, "0 으로 나눌 수 없습니다")
        d = a - bb
        return (abs(d) if op in ("absdiff", "abs") else d), ""
    x = vals[0] if vals else None
    if op in ("gain", "rgain", "abs", "sqrt", "pow", "fx", "hilim", "lolim", "velim", "lag", "bias", "convert",
              "integral", "deriv", "ft") and x is None and op not in ("integral", "ft"):
        return None, "입력 값을 모릅니다"
    if op == "gain":
        k = pr.get("k")
        return (float(k) * x, "") if k is not None else (None, "비례 상수 K 가 도면에 없습니다 — 눌러서 넣어 주세요")
    if op == "rgain":
        k = pr.get("k")
        return (-float(k) * x, "") if k is not None else (None, "비례 상수 K 가 도면에 없습니다 — 눌러서 넣어 주세요")
    if op == "abs":
        return abs(x), ""
    if op == "sqrt":
        return (math.sqrt(x), "") if x >= 0 else (None, "음수의 제곱근")
    if op == "pow":
        n = pr.get("n")
        return (x ** float(n), "") if n is not None else (None, "지수 n 이 도면에 없습니다 — 눌러서 넣어 주세요")
    if op == "fx":
        tb = pr.get("table")
        if tb:
            return _interp(tb, x), ""
        return x, "F(X) 꺾은선 표가 도면에 없어 입력을 그대로 넘겼습니다 (눌러서 표를 넣을 수 있습니다)"
    if op == "hilim":
        h = pr.get("h")
        return (min(x, float(h)), "") if h is not None else (x, "상한 H 가 도면에 없어 입력을 그대로 넘겼습니다")
    if op == "lolim":
        lo = pr.get("l")
        return (max(x, float(lo)), "") if lo is not None else (x, "하한 L 이 도면에 없어 입력을 그대로 넘겼습니다")
    if op == "velim":
        return x, "멈춘 값에서는 입력과 같습니다 (변화율 제한은 시간 동안만 작동)"
    if op == "lag":
        k = pr.get("k")
        return (float(k) if k is not None else 1.0) * x, "멈춘 값(정상 상태)의 값입니다"
    if op == "bias":
        bv = pr.get("b")
        if bv is None:
            return None, "바이어스 b 가 도면에 없습니다 — 눌러서 넣어 주세요"
        sgn = -1.0 if _lab(lab) == "-" else 1.0
        return x + sgn * float(bv), ""
    if op == "convert":
        return x, ""
    if op == "deriv":
        return 0.0, "값이 멈춰 있으면 미분은 0 입니다"
    if op in ("integral", "ft"):
        return None, "시간에 따라 쌓이는 값이라 정해지지 않습니다 — 눌러서 출력값을 넣어 주세요"
    if op == "transfer":
        cond = _cond(ins)
        cands = [(n, pn) for n, pn in ins if (pn or {}).get("name") in ("IN1", "IN2")]
        c = (dig or {}).get(cond) if cond is not None else None
        if pr.get("c") is not None:
            c = int(pr["c"])
        if c is None:
            return None, "전환 조건(C · Flag)의 1/0 을 모릅니다"
        want = "IN1" if c == 1 else "IN2"
        src = next((n for n, pn in cands if pn["name"] == want), None)
        if src is None:
            return None, "IN1 · IN2 이름을 도면에서 읽지 못했습니다"
        v = net_v.get(src)
        return (v, f"조건 {c} → {want}") if v is not None else (None, f"조건 {c} → {want} 의 값을 모릅니다")
    if op == "pid":
        tr = next((n for n, pn in ins if pn and pn["name"] in ("TR", "TRK")), None)
        if tr is not None and net_v.get(tr) is not None:
            return net_v[tr], "추종(Tr) 입력 값을 그대로 냅니다"
        return None, "PID 출력은 제어 계산이라 정해지지 않습니다 — 눌러서 수동 출력값을 넣어 주세요"
    if op == "formula":
        expr = formula_expr(lab)
        if not expr:
            return None, "수식을 읽지 못했습니다"
        names = formula_vars(expr) or []
        env = {}
        for n, pn in analog_ins:
            nm = (pn or {}).get("name")
            if nm and re.fullmatch(r"[A-H]", nm):
                env[nm] = net_v.get(n)
        if len(names) == 1 and len(analog_ins) == 1 and names[0] not in env:
            env[names[0]] = vals[0]
        for k, v in (pr.get("vars") or {}).items():
            env[k.upper()] = v
        missing = [nm for nm in names if env.get(nm) is None]
        if missing:
            return None, f"수식의 {', '.join(missing)} 값을 모릅니다"
        try:
            return eval_formula(expr, env), ""
        except Exception as e:  # noqa: BLE001
            return None, f"수식을 계산하지 못했습니다 ({e})"
    return None, ""


def _cond(ins):
    """전환(TRANSFER) 조건 넷 — 이름 Flag · C · COND, 없으면 IN1 · IN2 둘 말고 이름 없는 단자가 하나뿐일 때 그것."""
    cond = next((n for n, pn in ins if pn and pn["name"] in ("FLAG", "C", "COND")), None)
    if cond is None:
        cands = [n for n, pn in ins if (pn or {}).get("name") in ("IN1", "IN2")]
        unnamed = [n for n, pn in ins if not pn]
        cond = unnamed[0] if len(unnamed) == 1 and len(cands) == 2 else None
    return cond


def cond_net(s, bid, idx):
    return _cond(inputs(s, bid, idx))


def _two(analog_ins, vals, lab, op, pr):
    """두 입력 (앞 − 뒤 · 분자 ÷ 분모): + · − 부호 → 'IN1 / IN2' 글자 → IN1 · IN2 이름 → 사람이 정한 순서."""
    order = pr.get("order")                           # 사람이 정한 [넷 앞, 넷 뒤]
    if order and len(order) == 2:
        m = {str(n): v for (n, _), v in zip(analog_ins, vals)}
        if all(str(x) in m for x in order):
            return m[str(order[0])], m[str(order[1])]
    if op != "div":
        plus = [v for (n, pn), v in zip(analog_ins, vals) if pn and pn["name"] == "+"]
        minus = [v for (n, pn), v in zip(analog_ins, vals) if pn and pn["name"] == "-"]
        if len(plus) == 1 and len(minus) == 1:
            return plus[0], minus[0]
    named = {pn["name"]: v for (n, pn), v in zip(analog_ins, vals) if pn and _name_order(pn)}
    if op == "div":
        m = re.search(r"(IN\d)\s*/\s*(IN\d)", (lab or "").upper())
        if m and m.group(1) in named and m.group(2) in named:
            return named[m.group(1)], named[m.group(2)]
    if "IN1" in named and "IN2" in named:
        return named["IN1"], named["IN2"]
    if "X1" in named and "X2" in named:
        return named["X1"], named["X2"]
    return None, None


# ------------------------------------------------------------------ 식별 (결과를 읽을 때 한 번 · 분석 결과 파일은 그대로)

IDENT_VERSION = 3                     # 식별 규칙을 바꾸면 올린다 (도면 값 캐시 열쇠에 들어간다)


def _ports(s):
    from collections import defaultdict
    d = defaultdict(lambda: [0, 0])
    for p in s["ports"]:
        d[p["block"]][0 if p["dir"] == "in" else 1] += 1
    return d


def lamp_of(b, io):
    """표시등 — 색 글자 하나(G R W B …) · 들어오는 선만 있고 나가는 선이 없다."""
    if b.get("func") != "UNKNOWN" or b.get("logic") != "unknown":
        return False
    lab = _lab(b.get("label") or b.get("read") or "")
    return lab in (vocab().get("lamp_labels") or []) and io[0] >= 1 and io[1] == 0


def identify(sheets):
    """판정 못 한 블록(UNKNOWN) 중 범례 기호 · 이름으로 아날로그 연산자인 것에 이름을 붙이고(`aop` · func),
    표시등은 받는 쪽(sink)으로.  이름만 붙은 아날로그 블록(SUMMING …)에도 `aop` 를 단다.
    상수(A)는 들어오는 선이 없고 나가는 선이 있을 때만 · 나머지 연산은 나가는 선이 있을 때만 — 모양이 안 맞으면 고르지 않는다.
    → 이름을 바꾼 장 쪽 번호 집합."""
    changed = set()
    for s in sheets:
        io = None
        for bid, b in s["blocks"].items():
            if b.get("logic") != "unknown" or b.get("func") in ("MACRO", "XOR"):
                continue
            if io is None:
                io = _ports(s)
            nio = io[bid]
            if b.get("func") == "UNKNOWN":
                if lamp_of(b, nio):
                    b["aop_was"] = {"func": b["func"], "logic": b["logic"]}
                    b["func"], b["logic"] = "INDICATION", "sink"
                    changed.add(s["page"])
                    continue
                op = op_of(b)
                if not op or (op == "const" and (nio[0] > 0 or nio[1] == 0)) or (op != "const" and nio[0] == 0) or \
                        (op not in ("const", "pid") and nio[1] == 0):
                    continue                              # PID 는 출력 화살을 잘못 읽은 그림이 있어 이름만 붙인다
                names = info(op).get("names") or []
                b["aop"] = op
                b["aop_was"] = {"func": b["func"], "logic": b["logic"]}
                b["func"] = names[0] if names else op.upper()
                changed.add(s["page"])
            else:
                from . import analog as A
                if A.monitor_kind(b):
                    continue
                op = op_of(b)
                if op:
                    b["aop"] = op
    return changed


# ------------------------------------------------------------------ 글자 없이 그림만 든 연산자 (△ · ∫ · √ …)

def _segs_of(page):
    """그 쪽의 모든 그림 획 — 표시 좌표 직선 토막 [(x0, y0, x1, y1)].  곡선은 네 점 꺾은선으로."""
    m = page.rotation_matrix if page.rotation else None

    def tp(p):
        q = p * m if m is not None else p
        return (q.x, q.y)
    out = []
    for d in page.get_drawings():
        for it in d.get("items", []):
            k = it[0]
            if k == "l":
                out.append((*tp(it[1]), *tp(it[2])))
            elif k == "c":
                pts = [tp(it[i]) for i in (1, 2, 3, 4)]
                for a, b in zip(pts, pts[1:]):
                    out.append((*a, *b))
            elif k == "re":
                r = it[1]
                cs = [tp(r.tl), tp(r.tr), tp(r.br), tp(r.bl)]
                for a, b in zip(cs, cs[1:] + cs[:1]):
                    out.append((*a, *b))
            elif k == "qu":
                q = it[1]
                cs = [tp(q.ul), tp(q.ur), tp(q.lr), tp(q.ll)]
                for a, b in zip(cs, cs[1:] + cs[:1]):
                    out.append((*a, *b))
    return out


def figure_in(bbox, segs, grid=16):
    """상자 안(변에서 6% 안쪽)에 들어 있는 획으로 16×16 그림 — legend.figure 와 같은 칸 매기기.  없으면 None."""
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0
    ix0, iy0, ix1, iy1 = x0 + 0.06 * w, y0 + 0.06 * h, x1 - 0.06 * w, y1 - 0.06 * h
    inner = [s for s in segs if all(ix0 <= x <= ix1 for x in (s[0], s[2])) and all(iy0 <= y <= iy1 for y in (s[1], s[3]))]
    if not inner:
        return None
    xs = [v for s in inner for v in (s[0], s[2])]
    ys = [v for s in inner for v in (s[1], s[3])]
    fx0, fy0, fx1, fy1 = min(xs), min(ys), max(xs), max(ys)
    side = max(fx1 - fx0, fy1 - fy0)
    if side < 0.15 * min(w, h):
        return None
    ox, oy = fx0 - (side - (fx1 - fx0)) / 2, fy0 - (side - (fy1 - fy0)) / 2
    pts = set()
    for s in inner:
        ln = math.hypot(s[2] - s[0], s[3] - s[1])
        n = max(2, int(ln / side * grid * 2) + 2)
        for k in range(n + 1):
            t = k / n
            x = s[0] + (s[2] - s[0]) * t
            y = s[1] + (s[3] - s[1]) * t
            pts.add((min(grid - 1, int((x - ox) / side * grid)), min(grid - 1, int((y - oy) / side * grid))))
    return sorted(pts)


def name_op(name):
    """범례 이름(FUNCTION) → 연산 이름 | None."""
    return vocab()["_by_name"].get(_key(name))


def read_figures(s, page, figures):
    """글자도 이름도 없는 판정 못 한 상자의 안 그림을 범례 그림(△ DIFFERENCE · ∫ INTEGRAL …)과 맞대어
    `param.aop_fig` 에 연산 이름을 단다 (그림이 맞는 정도 0.85 이상 · 2위와 갈릴 때만).  → 단 블록 수."""
    from .legend import figure_score
    from .blocks import _stretch
    want = [(bid, b) for bid, b in s["blocks"].items()
            if b.get("func") == "UNKNOWN" and not (b.get("label") or b.get("read")) and b.get("kind") == "RECT" and b.get("bbox")]
    figs = [{**f, "fig": _stretch(f["fig"])} for f in figures or [] if f.get("fig") and name_op(f.get("name"))]
    if not want or not figs:
        return 0
    segs = _segs_of(page)
    n = 0
    for bid, b in want:
        fg = figure_in(b["bbox"], segs)
        m = _best_fig(_stretch(fg), figs) if fg else None
        if m:
            b.setdefault("param", {})["aop_fig"] = m
            n += 1
    return n


def _best_fig(fg, figs, floor=0.85, tie=0.02):
    """가장 닮은 범례 그림 → {op, name, score} | None.  같은 그림을 두 이름이 쓰면(사전에 △ 가 DIFFERENCE 와
    ABSOLUTE VALUE 둘로 들어 있다) 그 그림 하나를 기호로 쓰는 연산(어휘 labels 에 그 한 글자 기호가 있는 것)을 고르고,
    그래도 갈리지 않으면 고르지 않는다."""
    from .legend import figure_score
    sc = sorted(((figure_score(fg, f["fig"]), f["name"]) for f in figs), reverse=True)
    if not sc or sc[0][0] < floor:
        return None
    top = {name_op(nm): nm for s_, nm in sc if s_ >= sc[0][0] - tie}
    if len(top) > 1:
        glyph = {op: nm for op, nm in top.items()
                 if any(len(x) == 1 and not x.isalnum() for x in (info(op).get("labels") or []))}
        if len(glyph) != 1:
            return None
        top = glyph
    op, nm = next(iter(top.items()))
    return {"op": op, "name": nm, "score": round(sc[0][0], 3)}


# 출력이 입력과 같은 단위인 연산 — 공학 범위(4~20 mA ↔ 값)를 입력에서 물려받는다.  곱 · 나눗셈 · 수식 같은 것은 단위가 바뀌어 물려받지 않는다.
SAME_UNIT = {"sum", "mean", "diff", "absdiff", "max", "min", "median", "hilim", "lolim", "abs", "velim", "lag", "bias",
             "transfer", "fx", "convert", "pid"}

# 연산자 판(화면)이 묻는 값 — (열쇠, 이름).  모든 연산에 '출력값 고정'(out)이 더 있다 (정해지지 않는 연산 · 시험용).
NEEDS = {
    "const": [["value", "상수 A"]],
    "gain": [["k", "비례 상수 K"]], "rgain": [["k", "비례 상수 K"]], "lag": [["k", "이득 k (멈춘 값)"]],
    "bias": [["b", "바이어스 b"]], "hilim": [["h", "상한 H"]], "lolim": [["l", "하한 L"]], "pow": [["n", "지수 n"]],
    "dev": [["d", "편차 D"]],
    "transfer": [["c", "전환 조건 C (비우면 Flag 신호대로)"]],
    "pid": [["out", "수동 출력값"]], "integral": [["out", "출력값"]], "ft": [["out", "출력값"]],
    "fx": [["table", "F(X) 꺾은선 표 (X, Y)"]],
    "formula": [["vars", "수식 글자 값"]],
    "diff": [["order", "앞 · 뒤 입력 (앞 − 뒤)"]], "absdiff": [["order", "앞 · 뒤 입력"]],
    "div": [["order", "분자 · 분모 입력"]],
    "sum": [["coef", "입력 계수 (+1 · −1 …)"]], "mean": [["coef", "입력 계수"]], "mul": [["coef", "입력 계수"]],
}
