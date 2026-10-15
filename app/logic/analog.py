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
"""
from __future__ import annotations

import re
import statistics

MONITOR_FUNC = "SIGNAL MONITOR"
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


def nets(s, given, idx):
    """사람이 준 아날로그 값 {"block:<id>"|"row:<n>": 수} → ({넷: 값}, {블록: 값}).

    선택 블록(MED …)은 값을 안 받았으면 입력이 **모두** 정해졌을 때만 범례 이름대로 계산한다 (하나라도 모르면 모름)."""
    ins, outs, drivers = idx[0], idx[1], idx[2]
    B = s["blocks"]
    net_v, blk_v = {}, {}
    rows = {r["n"]: r for r in s["rows"] if r["side"] == "L" and r.get("net") is not None}
    for k, v in (given or {}).items():
        f = num(v)
        if f is None or not isinstance(k, str):
            continue
        kind, _, x = k.partition(":")
        if kind == "row" and x.isdigit() and int(x) in rows:
            net_v[rows[int(x)]["net"]] = f
        elif kind == "block" and x in B:
            blk_v[x] = f
            for n, _, _ in outs[x]:
                net_v[n] = f
    for _ in range(len(B) + 1):
        moved = False
        for bid, b in B.items():
            if bid in blk_v:
                continue
            how = selector_of(b)
            if not how or not ins[bid]:
                continue
            vs = [net_v.get(n) for n, _, _ in ins[bid]]
            if any(v is None for v in vs):
                continue
            blk_v[bid] = round(_calc(how, vs), 6)
            for n, _, _ in outs[bid]:
                net_v[n] = blk_v[bid]
            moved = True
        if not moved:
            break
    return net_v, blk_v


def monitors(s, net_v, idx):
    """감시 블록마다 {block, label, kind, value, sp, sp_src, unit, out} — 값과 설정값이 다 있을 때만 out 이 1/0."""
    ins = idx[0]
    out = []
    for bid, b in s["blocks"].items():
        k = monitor_kind(b)
        if not k:
            continue
        v = next((net_v[n] for n, _, _ in ins[bid] if n in net_v), None)
        sp, src = setpoint(b)
        p = b.get("param") or {}
        out.append({"block": bid, "label": b.get("label") or "", "kind": k[0], "value": v, "sp": sp, "sp_src": src,
                    "sp_drawing": num(p.get("sp")) if p.get("sp") is not None else None,
                    "unit": p.get("sp_unit") or "",
                    "out": compare(k[0], v, sp) if (v is not None and sp is not None) else None})
    return out


# ------------------------------------------------------------------ 도면이 인쇄한 설정값

def read_drawing(pdf_path, sheets):
    """감시 블록 바로 위에 인쇄한 설정값(`202.4 barg` · `-830 mm`)을 블록 param 에 얹는다 (sp · sp_unit · sp_text).

    자리: 블록 위 변에서 블록 높이 두 배 안 · 가로로 블록과 겹치는(블록 폭만큼 넓힌) 진짜 글자 줄.  그 줄의 첫 낱말이
    수일 때만 — 수가 아니면 설정값이 아니다.  글자가 선으로 그려진 묶음(HRSG)은 낱말이 없어 아무것도 얹지 않는다.
    → 얹은 블록 수"""
    from . import geom
    want = {}
    for s in sheets:
        if s.get("page", 0) <= 0:
            continue
        mons = [(bid, b) for bid, b in s["blocks"].items() if monitor_kind(b) and b.get("bbox")]
        if mons:
            want[s["page"]] = (s, mons)
    if not want:
        return 0
    import pymupdf
    try:
        doc = pymupdf.open(str(pdf_path))
    except Exception:
        return 0
    n = 0
    with doc:
        for page, (s, mons) in want.items():
            if page - 1 >= len(doc):
                continue
            ws = geom.words(doc[page - 1])
            for bid, b in mons:
                x0, y0, x1, y1 = b["bbox"]
                h, w = max(1.0, y1 - y0), max(1.0, x1 - x0)
                cand = [t for t in ws if t[3] <= y0 + 0.5 and t[3] >= y0 - 2 * h
                        and t[2] >= x0 - w and t[0] <= x1 + w]
                if not cand:
                    continue
                yb = max(t[3] for t in cand)                  # 블록에 가장 가까운 줄
                line = sorted((t for t in cand if abs(t[3] - yb) < h * 0.4), key=lambda t: t[0])
                if not line or not _NUM.match(line[0][4]):
                    continue
                f = num(line[0][4])
                if f is None:
                    continue
                p = b.setdefault("param", {})
                p["sp"] = f
                p["sp_unit"] = " ".join(t[4] for t in line[1:3] if not _NUM.match(t[4]))[:12]
                p["sp_text"] = " ".join(t[4] for t in line)[:40]
                n += 1
    return n
