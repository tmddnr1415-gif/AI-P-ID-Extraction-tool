"""Instrument sizing cross-checks (valve40) — the datasheet's own numbers checked with the standard equations.
Every row is a 'Review Required' / 'Mismatch' for an engineer to confirm (human=True); nothing is filled in.

Control valve (form 101) — IEC 60534-2-1
  IN-CV-01  rated Cv vs the datasheet's calculated / required Cv: max case above rated Cv (Mismatch), above 90 % of
            rated (little margin) or min case below 10 % of rated (low opening, poor control) — Review
  IN-CV-02  gas / vapour: Cv recomputed from the process lines (mass flow kg/h · P1 · P2 · T · M · k · Z · xT) differs
            from the datasheet's calculated Cv by more than 10 % — Review (piping factor Fp = 1 assumed and said)
              C = W / (N8 · Fp · P1 · Y) · √(T·Z / (x·M)),  N8 = 94.8 (Cv, kg/h, bar, K),
              x = ΔP/P1,  Fγ = k/1.40,  Y = 1 − x/(3·Fγ·xT),  choked when x ≥ Fγ·xT (then x = Fγ·xT, Y = 2/3)
  IN-CV-03  liquid: flashing (P2 ≤ Pv) or choked / cavitating flow (ΔP ≥ FL²·(P1 − FF·Pv), FF = 0.96 − 0.28·√(Pv/Pc));
            gas: choked flow (x ≥ Fγ·xT) — Review
  IN-CV-04  predicted noise above the allowable on the same sheet (Mismatch); above 85 dBA with no allowable given (Review)
PSV (form 701) — API 526 effective orifice areas · API 520 back pressure
  IN-PSV-01 selected area differs from the API 526 effective area of the orifice letter (> 2 %) — Review
  IN-PSV-02 calculated (required) area larger than the selected area — Mismatch
  IN-PSV-03 conventional valve with back pressure above 10 % of set pressure — Review (balanced bellows / pilot needed)
  IN-PSV-04 allowable overpressure above 21 % (fire case limit) — Review
"""
from __future__ import annotations

import math
import re

from app.valve import process as procmod
from app.valve.instreview import MISMATCH, OK, REVIEW, _row, nums

# API 526 effective orifice areas, in²
API526 = {"D": 0.110, "E": 0.196, "F": 0.307, "G": 0.503, "H": 0.785, "J": 1.287, "K": 1.838, "L": 2.853,
          "M": 3.60, "N": 4.34, "P": 6.38, "Q": 11.05, "R": 16.0, "T": 26.0}
N8 = 94.8
SRC_IEC = "IEC 60534-2-1 (같은 Datasheet 값)"
SRC_API = "API 526 / API 520 (같은 Datasheet 값)"


def _sub(v: dict | None) -> dict:
    """{'max','nor','min','unit'} numbers of a Max/Nor/Min/Unit row — only what is printed."""
    if not v:
        return {}
    sub = {k.lower(): x for k, x in (v.get("sub") or {}).items()}
    out = {}
    for k in ("max", "nor", "min"):
        n = nums(sub.get(k, ""))
        if n:
            out[k] = n[0]
    out["unit"] = sub.get("unit", "") or ""
    if not any(k in out for k in ("max", "nor", "min")):          # a single value cell
        n = nums(v.get("value") or "")
        if n:
            out["nor"] = n[0]
            out["unit"] = re.sub(r"[-\d.,\s/]+", " ", v.get("value") or "").strip()
    return out


def _one(v: dict | None) -> float | None:
    if not v:
        return None
    n = nums(v.get("value") or "") or nums(" ".join((v.get("sub") or {}).values()))
    return n[0] if n else None


def _bara(x: float, unit: str):
    dim, basis, f = procmod.unit_of(unit)
    if dim != "press" or f is None or basis is None:
        return None
    return x * f + (1.01325 if basis == "g" else 0.0)


def _kelvin(x: float, unit: str):
    u = (unit or "").lower().replace(" ", "").replace("°", "").replace("º", "")
    if u in ("k", "kelvin"):
        return x
    if u in ("c", "degc", "℃"):
        return x + 273.15
    if u in ("f", "degf"):
        return (x - 32) * 5 / 9 + 273.15
    return None


def gas_cv(w_kgh, p1_bara, p2_bara, t_k, mw, k, z, xt):
    """IEC 60534-2-1 Cv for gas, mass flow; returns (Cv, x used, choked)."""
    x = (p1_bara - p2_bara) / p1_bara
    fg = k / 1.40
    choked = x >= fg * xt
    if choked:
        x = fg * xt
    y = 1 - x / (3 * fg * xt)
    return w_kgh / (N8 * p1_bara * y) * math.sqrt(t_k * z / (x * mw)), x, choked


def cv_checks(vals: dict) -> list[dict]:
    out = []
    rated = _one(vals.get("rated_cv"))
    calc = _sub(vals.get("calculated_cv")) or _sub(vals.get("required_cv"))
    ckey = "calculated_cv" if _sub(vals.get("calculated_cv")) else "required_cv"
    if rated and calc:
        cmax = calc.get("max", calc.get("nor"))
        cmin = calc.get("min")
        if cmax is not None:
            r = cmax / rated
            res = MISMATCH if r > 1.0 else REVIEW if r > 0.9 else OK
            out.append(_row("IN-CV-01", "Rated Cv vs Max Cv", f"Max Cv {cmax:g}", f"Rated Cv {rated:g}", res,
                            f"Max Cv 가 Rated Cv 보다 큼 ({r:.0%}) — Valve 가 작음" if res == MISMATCH else
                            f"Max Cv 가 Rated Cv 의 {r:.0%} — 여유 10 % 미만" if res == REVIEW else f"Max Cv = Rated 의 {r:.0%}",
                            SRC_IEC, "rated_cv", human=True))
        if cmin is not None and cmin > 0:
            r = cmin / rated
            if r < 0.10:
                out.append(_row("IN-CV-01", "Rated Cv vs Min Cv", f"Min Cv {cmin:g}", f"Rated Cv {rated:g}", REVIEW,
                                f"Min Cv 가 Rated Cv 의 {r:.0%} — 낮은 개도에서 제어 · Rangeability 확인", SRC_IEC, "rated_cv", human=True))
    # process lines (columns Max / Nor / Min)
    F, P1, P2, T = (_sub(vals.get(k)) for k in ("flow", "upstream_pressure", "downstream_pressure", "temperature"))
    M, K, Z = (_sub(vals.get(k)) for k in ("mol_weight", "specific_heat_ratio", "compressibility_factor"))
    PV, PC = _sub(vals.get("vapour_pressure")), _sub(vals.get("critical_pressure"))
    FL, XT = _sub(vals.get("fl_liquid_pressure_recovery_factor")), _sub(vals.get("xt_pressure_drop_ratio_factor"))
    phase = " ".join([(vals.get("fluid_state") or {}).get("value", "")] + list(((vals.get("fluid_state") or {}).get("sub") or {}).values())).lower()
    gas = any(w in phase for w in ("gas", "vap", "steam"))
    liquid = "liq" in phase
    pick = lambda d, c: d.get(c, d.get("nor")) if d else None   # noqa: E731  one value of a column, or the single value
    for case in ("max", "nor", "min"):
        p1, p2 = pick(P1, case), pick(P2, case)
        if p1 is None or p2 is None:
            continue
        p1a, p2a = _bara(p1, P1.get("unit", "")), _bara(p2, P2.get("unit", "") or P1.get("unit", ""))
        if p1a is None or p2a is None or p1a <= p2a:
            continue
        if gas:
            w, t, mw, k, z, xt = pick(F, case), pick(T, case), pick(M, case), pick(K, case), pick(Z, case), pick(XT, case)
            tk = _kelvin(t, T.get("unit", "")) if t is not None else None
            fu = (F.get("unit") or "").lower().replace(" ", "")
            if None in (w, tk, mw, k, z, xt) or fu not in ("kg/h", "kg/hr"):
                continue
            cv, x, choked = gas_cv(w, p1a, p2a, tk, mw, k, z, xt)
            dc = pick(calc, case) if calc else None
            if dc:
                d = abs(cv - dc) / dc
                out.append(_row("IN-CV-02", f"Calculated Cv ({case.title()})", f"{dc:g}", f"{cv:.1f} (IEC 60534-2-1)", OK if d <= 0.10 else REVIEW,
                                (f"다시 계산한 Cv 와 {d:.0%} 차이" + (" — 계산 조건 · Fp 확인" if d > 0.10 else "")) + " · Fp = 1 가정",
                                SRC_IEC, ckey, human=True))
            if choked:
                out.append(_row("IN-CV-03", f"Choked flow ({case.title()})", f"x = ΔP/P1 = {(p1a - p2a) / p1a:.2f}", f"Fγ·xT = {k / 1.4 * xt:.2f}", REVIEW,
                                "기체 Choked flow — 소음 · 속도 확인", SRC_IEC, "downstream_pressure", human=True))
        elif liquid:
            pv, pc, fl = pick(PV, case), pick(PC, case), pick(FL, case)
            if pv is None or fl is None:
                continue
            pva = _bara(pv, PV.get("unit", ""))
            if pva is None:
                continue
            pca = _bara(pc, PC.get("unit", "")) if pc is not None else None
            ff = 0.96 - 0.28 * math.sqrt(pva / pca) if pca else 0.96
            dpc = fl ** 2 * (p1a - ff * pva)
            if p2a <= pva:
                out.append(_row("IN-CV-03", f"Flashing ({case.title()})", f"P2 {p2a:.2f} bara", f"Pv {pva:.2f} bara", REVIEW,
                                "출구압이 증기압 이하 — Flashing (Trim · 재질 · 출구 속도 확인)", SRC_IEC, "downstream_pressure", human=True))
            elif p1a - p2a >= dpc:
                out.append(_row("IN-CV-03", f"Choked / cavitation ({case.title()})", f"ΔP {p1a - p2a:.2f} bar", f"ΔP choked {dpc:.2f} bar", REVIEW,
                                "ΔP 가 FL²(P1 − FF·Pv) 이상 — Choked · 공동현상 (Anti-cavitation Trim 확인)", SRC_IEC, "downstream_pressure", human=True))
    pred, allow = _one(vals.get("predict_spl")), _one(vals.get("allowable_spl"))
    if pred is not None:
        if allow is not None:
            res = MISMATCH if pred > allow else OK
            out.append(_row("IN-CV-04", "Noise", f"{pred:g} dBA", f"Allowable {allow:g} dBA", res,
                            "예상 소음이 허용치보다 큼" if res == MISMATCH else "허용치 이내", "같은 Datasheet", "predict_spl", human=True))
        elif pred > 85:
            out.append(_row("IN-CV-04", "Noise", f"{pred:g} dBA", "85 dBA (흔한 기준)", REVIEW,
                            "허용치가 비어 있고 85 dBA 를 넘음 — 프로젝트 소음 기준 확인", "같은 Datasheet", "predict_spl", human=True))
    return out


def _area_in2(v: dict | None):
    if not v:
        return None
    text = (v.get("value") or "") + " " + " ".join((v.get("sub") or {}).values())
    n = nums(text)
    if not n:
        return None
    t = text.lower().replace(" ", "")
    if "mm2" in t or "mm²" in t:
        return n[0] / 645.16
    if "cm2" in t or "cm²" in t:
        return n[0] / 6.4516
    if "in2" in t or "in²" in t or "sq.in" in t or "sqin" in t:
        return n[0]
    return None                                            # no unit printed: not compared


def psv_checks(vals: dict, C: dict) -> list[dict]:
    out = []
    letter = ""
    od = (vals.get("orifice_designation") or {}).get("value", "")
    m = re.search(r"(?<![A-Z])([DEFGHJKLMNPQRT])(?![A-Z])", od.upper())
    if m:
        letter = m.group(1)
    sel, calc = _area_in2(vals.get("selected_area")), _area_in2(vals.get("calculated_area"))
    if letter and sel:
        std = API526[letter]
        d = abs(sel - std) / std
        out.append(_row("IN-PSV-01", "Selected area vs orifice", f"{sel:.3f} in² ('{letter}')", f"API 526 '{letter}' {std} in²", OK if d <= 0.02 else REVIEW,
                        "같음" if d <= 0.02 else f"API 526 표준 면적과 {d:.0%} 차이 — Orifice 문자 · 면적 확인", SRC_API, "selected_area", human=True))
    if calc and (sel or letter):
        a = sel or API526[letter]
        res = MISMATCH if calc > a * 1.0001 else OK
        out.append(_row("IN-PSV-02", "Required area vs selected", f"{calc:.3f} in²", f"{a:.3f} in²", res,
                        "필요 면적이 선택 면적보다 큼 — Orifice 를 키워야 함" if res == MISMATCH else "선택 면적이 필요 면적 이상", SRC_API, "calculated_area", human=True))
    sp = C.get("set_pressure") or {}
    bp = vals.get("max_back_pressure") or vals.get("superimposed_back_pressure")
    typ = " ".join([(vals.get(k) or {}).get("value", "") for k in ("valve_design_type", "bonnet_type")]).lower()
    if bp and sp.get("max") is not None and "conventional" in typ:
        n = nums(bp.get("value") or "")
        if n:
            ub = re.sub(r"[-\d.,\s]+", " ", bp.get("value") or "").strip() or sp.get("unit", "")
            dimb, _, fb = procmod.unit_of(ub)
            dims, _, fs = procmod.unit_of(sp.get("unit", ""))
            if dimb == dims == "press" and fb and fs:
                r = n[0] * fb / (sp["max"] * fs)
                if r > 0.10:
                    out.append(_row("IN-PSV-03", "Back pressure (conventional)", f"{n[0]:g} {ub}", f"10 % of set {sp['max'] * 0.1:g} {sp.get('unit', '')}", REVIEW,
                                    f"배압이 Set 의 {r:.0%} — Conventional 은 보통 10 % 이하 (Balanced bellows · Pilot 검토)", SRC_API, "max_back_pressure", human=True))
    op = vals.get("allowable_over_pressure")
    if op:
        n = nums(op.get("value") or "")
        if n and "%" in (op.get("value") or "") and n[0] > 21:
            out.append(_row("IN-PSV-04", "Allowable overpressure", op.get("value"), "≤ 21 % (Fire case)", REVIEW,
                            "API 521 허용 초과압(단일 10 % · 다중 16 % · 화재 21 %)보다 큼", SRC_API, "allowable_over_pressure", human=True))
    return out
