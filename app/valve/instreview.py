"""Instrument datasheet review — the common checks (plan v2 §4) for every item kind read by app/valve/instrument.py.

  IN-REQ-01  a required row is blank                    (card 'required' = suggested list until the user confirms it)
  IN-PDS-00  the tag is not in the Process Data (PDS)   → shown as '없음'
  IN-PDS-01  fluid · phase · P · T · density · flow differ from the PDS row of the tag
  IN-PMS-01  the pipe class is not in the PMS
  IN-PMS-02  the datasheet rating differs from the PMS class flange rating
  IN-LL-00   the line number is not in the Process Line List
  IN-LL-01   pipe class differs from the Line List
  IN-LL-02   Line List design pressure is higher than the datasheet's
  IN-LL-03   Line List design temperature (max) is higher than the datasheet's
  IN-LL-04   Line List design temperature (min) is lower than the datasheet's
  IN-LL-05   line size differs from the Line List
  IN-ITM-01  (pressure/level/flow transmitters, gauges) range upper value below the max operating pressure — 사람 확인
  IN-ITM-02  (PSV) set pressure above the design pressure — 사람 확인
  IN-OPN-01  a cell still says HOLD · TBA · TBC · TBD (open item left on the datasheet)
  IN-UNIT-01 gauge and absolute pressure mixed in the same datasheet (operating vs design) — 사람 확인

Every row says where the reference value came from (document · page / sheet · row) and what both sides say.  A value
that is not on the page is never made up: the row is 'Review Required' or 'Datasheet Blank' with the reason.
Numbers are compared only when the unit is the same kind; gauge/absolute is not corrected (left to the reviewer).
"""
from __future__ import annotations

import re

from app.valve import instrument, linelist
from app.valve import process as procmod

OK, MISMATCH, MISSING, REVIEW, NOT_IN, BLANK = "OK", "Mismatch", "Missing", "Review Required", "없음", "Datasheet Blank"
RULE_VER = "IN-1.0 (2026-11-12)"
RULES = {
    "IN-REQ-01": "필수 칸이 비어 있음 (양식 카드의 제안 목록 — 사용자 확인 전)",
    "IN-PDS-00": "Process Data(PDS) 에 이 Tag 가 없음",
    "IN-PDS-01": "Process Data(PDS) 와 값이 다름 (유체 · 상 · 압력 · 온도 · 밀도 · 유량)",
    "IN-PMS-01": "Pipe Class 가 PMS 에 없음",
    "IN-PMS-02": "Rating 이 PMS Class 의 Flange Class 와 다름",
    "IN-LL-00": "Line No 가 Process Line List 에 없음",
    "IN-LL-01": "Pipe Class 가 Line List 와 다름",
    "IN-LL-02": "Line List 의 Design Pressure 가 Datasheet 보다 높음",
    "IN-LL-03": "Line List 의 Design Temperature(Max) 가 Datasheet 보다 높음",
    "IN-LL-04": "Line List 의 Design Temperature(Min) 가 Datasheet 보다 낮음",
    "IN-LL-05": "Line Size 가 Line List 와 다름",
    "IN-ITM-01": "Range 상한이 최대 운전압력보다 낮음 (사람 확인)",
    "IN-ITM-02": "Set Pressure 가 Design Pressure 보다 높음 (사람 확인)",
    "IN-OPN-01": "HOLD · TBA · TBC · TBD 가 남아 있음 (미결 항목)",
    "IN-UNIT-01": "같은 Datasheet 안에서 게이지압 · 절대압이 섞여 있음 (사람 확인)",
}
_OPEN = re.compile(r"(?<![A-Z])(HOLD|TBA|TBC|TBD|T\.B\.A\.?|T\.B\.C\.?|T\.B\.D\.?)(?![A-Z])", re.I)
_WORDS = {"equipment_no": ("equipment",), "vessel_no": ("vessel",), "line_size": ("size",), "fluid_state": ("phase",),
          "design_pressure": ("design pressure", "pressure"), "design_temp": ("design temp", "temperature"), "line_no": ("line no", "line number")}
SEVERITY = {MISMATCH: "Major", MISSING: "Minor", REVIEW: "Review", NOT_IN: "Info", BLANK: "Info", OK: ""}
_NUM = re.compile(r"(?<![A-Za-z\d.])-?\d+(?:\.\d+)?")          # not the 3 of 'm3/h' or the 300 of 'CL300'
ON_FORM = {"fluid": ("fluid",), "fluid_state": ("fluid_state", "fluid"), "op_pressure": ("op_pressure", "upstream_pressure"),
           "design_pressure": ("design_pressure", "op_pressure"), "op_temp": ("op_temp", "temperature"),
           "design_temp": ("design_temp", "op_temp"), "density": ("density",), "flow": ("flow",)}


def blank(v) -> bool:
    return procmod._blank(str(v or ""))


def nums(s: str) -> list[float]:
    s = re.sub(r"(?<=\d),(?=\d{3}\b)", "", str(s or ""))
    s = re.sub(r"(\d)\s*~\s*(-?\d)", r"\1 \2", s)
    s = re.sub(r"(\d)-(?=\d)|(\d)\s+-\s+(?=\d)", lambda m: (m.group(1) or m.group(2)) + " ", s)   # '0-25' · '0 - 25' = range; '85 -29' = two numbers
    return [float(x) for x in _NUM.findall(s)]


def unit_in(s: str) -> str:
    """The unit written after the numbers ('12 / 10 barg' → 'barg')."""
    m = re.search(r"(?:\d|\))\s*([A-Za-z°℃º][A-Za-z°℃º/0-9()\-\.]*)\s*$", str(s or "").strip())
    return m.group(1) if m else ""


def _sub_get(sub: dict, *names) -> str:
    low = {k.lower().rstrip(".:"): v for k, v in (sub or {}).items()}
    for n in names:
        for k, v in low.items():
            if k.startswith(n) and not blank(v):
                return v
    return ""


def quantity(v: dict | None, part: str = "") -> dict:
    """{max, nor, min, unit, text} of a P/T-like row.  'Max/Nor/Min/Unit' sub-columns are used as they are; a single
    cell ('12 / 10.5 / 8 barg') gives max = largest · min = smallest (order on the forms differs: max/nor/min ·
    min/nor/max); part='oper'|'design' takes that sub-label of a shared row."""
    if not v:
        return {}
    sub, text = v.get("sub") or {}, v.get("value") or ""
    if part:
        alt = _sub_get(sub, "oper") if part == "oper" else _sub_get(sub, "des")
        if alt:
            text, sub = alt, {}
        elif part == "design":
            return {}
    if any(k.lower() in ("max", "nor", "min") for k in sub):
        q = {k: (nums(_sub_get(sub, k)) or [None])[0] for k in ("max", "nor", "min")}
        unit = _sub_get(sub, "unit")
        if not unit:
            unit = unit_in(text)
        vals = [x for x in q.values() if x is not None]
        if not vals:
            n = nums(text)
            if not n:
                return {}
            q = {"max": max(n), "min": min(n), "nor": n[1] if len(n) == 3 else None}
        return dict(q, unit=unit, text=" / ".join(f"{k.title()} {_sub_get(sub, k)}" for k in ("max", "nor", "min") if _sub_get(sub, k)) + (f" {unit}" if unit else ""))
    n = nums(text)
    if not n:
        return {"text": text} if text.strip() else {}
    return {"max": max(n), "min": min(n), "nor": n[1] if len(n) == 3 else (n[0] if len(n) == 1 else None),
            "unit": unit_in(text), "text": text}


def canonical(vals: dict) -> dict:
    """Common items of one sheet, whatever the form: fluid · phase · op/design P · op/design T · density · flow · class · line."""
    g = lambda k: (vals.get(k) or {}).get("value", "") if vals.get(k) else ""   # noqa: E731
    out = {}
    fluid, phase = g("fluid"), g("fluid_state")
    if fluid and not phase and "phase" in (vals["fluid"].get("label") or "").lower():     # 'Fluid / Phase' in one row
        if "/" in fluid:
            fluid, phase = [x.strip() for x in fluid.split("/", 1)]
        else:                                              # the reader drops a lone '/': the phase is the last word
            w = fluid.split()
            if len(w) > 1 and _phase(w[-1]):
                fluid, phase = " ".join(w[:-1]), w[-1]
    out["fluid"], out["fluid_state"] = fluid, phase
    op = vals.get("op_pressure") or vals.get("upstream_pressure")      # a control valve gives the inlet (upstream) pressure
    out["op_pressure"] = quantity(op, "oper") or quantity(op)
    dsg = quantity(vals.get("design_pressure"))
    if not dsg and op:                                     # shared row 'Operating Pressure | Design Pressure' / 'Oper. | Design'
        dp = _sub_get(op.get("sub") or {}, "design pressure") or _sub_get(op.get("sub") or {}, "des")
        dsg = quantity({"value": dp}) if dp else {}
    out["design_pressure"] = dsg
    ot = vals.get("op_temp") or vals.get("temperature")
    out["op_temp"] = quantity(ot, "oper") or quantity(ot)
    dt = quantity(vals.get("design_temp"))
    if not dt and ot:
        d2 = _sub_get(ot.get("sub") or {}, "design temp") or _sub_get(ot.get("sub") or {}, "des")
        dt = quantity({"value": d2}) if d2 else {}
    out["design_temp"] = dt
    out["density"] = quantity(vals.get("density"))
    out["flow"] = quantity(vals.get("flow"))
    pc = vals.get("piping_class")
    out["piping_class"] = (pc.get("value") or _sub_get(pc.get("sub") or {}, "high", "inlet")) if pc else ""
    out["line_no"] = g("line_no")
    ls = vals.get("line_size_inlet") or vals.get("line_size")
    out["line_size"] = ls.get("value", "") if ls else ""
    rt = vals.get("rating")
    out["rating"] = rt.get("value", "") if rt else ""
    if not out["rating"]:
        for k in ("process_connection",):
            pcn = vals.get(k)
            if pcn:
                m = re.search(r"(?:CL(?:ASS)?\s*|#\s*)(\d{3,4})|(\d{3,4})\s*#|^\s*(\d{3,4})\s*$", _sub_get(pcn.get("sub") or {}, "rating") or (pcn.get("value") or ""), re.I)
                if m:
                    out["rating"] = m.group(1) or m.group(2) or m.group(3)
    rng = next((vals[k] for k in ("range", "calibration_range", "range_adj_range", "range_set_at", "element_range") if vals.get(k) and not blank(vals[k].get("value"))), None)
    out["range"] = quantity(rng) if rng else {}
    out["set_pressure"] = quantity(vals.get("set_pressure"))
    return out


def _row(rule, item, ds, ref, result, reason, source="", key="", page=None, human=False):
    return {"rule": rule, "item": item, "key": key, "ds": ds, "ref": ref, "result": result, "severity": SEVERITY.get(result, ""),
            "reason": reason, "source": source, "page": page, "human": human, "rule_ver": RULE_VER}


def _press_bar(q: dict) -> tuple[float | None, float | None, str]:
    """(max in bar, min in bar, basis) — None when the unit is not a pressure unit."""
    dim, basis, f = procmod.unit_of(q.get("unit", ""))
    if dim != "press" or q.get("max") is None:
        return None, None, ""
    return q["max"] * f, (q.get("min") if q.get("min") is not None else q["max"]) * f, basis or ""


def _temp_c(q: dict) -> tuple[float | None, float | None]:
    dim, basis, _ = procmod.unit_of(q.get("unit", ""))
    if dim != "temp" or q.get("max") is None:
        return None, None
    conv = (lambda x: (x - 32) * 5 / 9) if basis == "F" else (lambda x: x)   # noqa: E731
    return conv(q["max"]), conv(q["min"] if q.get("min") is not None else q["max"])


def required(sheet: dict, vals: dict, keys: list[str] | None = None, confirmed: bool = False) -> list[dict]:
    card = instrument.cards()[sheet["form_id"]]
    keys = keys if keys is not None else (card.get("required") or {}).get("keys", [])
    labels = {it.get("std_key"): (it["no"], it["label"]) for it in card["items"] if it.get("std_key")}
    labels.update({z.get("std_key"): (it["no"], z["text"]) for it in card["items"] for z in it.get("sublabels") or []
                   if isinstance(z, dict) and z.get("std_key") and z["std_key"] not in labels})
    out = []
    C = canonical(vals)
    for k in keys:
        v = vals.get(k)
        filled = v and (not blank(v.get("value")) or any(not blank(x) for x in (v.get("sub") or {}).values()))
        if k not in labels and not C.get(k):               # printed inside another row ('Line No. / Equipment No.')
            host = next((it for it in card["items"] if it.get("label") and any(p in it["label"].lower() for p in _WORDS.get(k, ()))), None)
            if not host:
                continue                                   # not on this form at all
            hv = vals.get(host.get("std_key")) or {}
            if not blank(hv.get("value")) or any(not blank(x) for x in (hv.get("sub") or {}).values()):
                continue
            out.append(_row("IN-REQ-01", f"{host['no']}. {host['label']}", "", "필수", MISSING,
                            "필수 칸이 비어 있음" + ("" if confirmed else " — 필수 목록은 제안값(사용자 확인 전)"),
                            f"양식 {sheet['form_id']} 카드", k, hv.get("page")))
            continue
        c = C.get(k)
        filled = filled or (bool(c) and (not isinstance(c, dict) or c.get("max") is not None or bool(c.get("text"))))   # 'Fluid / Phase' in one row
        if filled:
            continue
        no, lab = labels.get(k, ("", k))
        out.append(_row("IN-REQ-01", f"{no}. {lab}" if no else lab, "", "필수", MISSING,
                        "필수 칸이 비어 있음" + ("" if confirmed else " — 필수 목록은 제안값(사용자 확인 전)"),
                        f"양식 {sheet['form_id']} 카드", k, v.get("page") if v else None))
    return out


def _cmp_text(a: str, b: str) -> str:
    na, nb = linelist.key(a), linelist.key(b)
    if not na or not nb:
        return REVIEW
    if na == nb:
        return OK
    wa, wb = set(re.findall(r"[A-Z0-9]{2,}", a.upper())), set(re.findall(r"[A-Z0-9]{2,}", b.upper()))
    if wa and wb and (wa <= wb or wb <= wa):
        return OK
    return MISMATCH


def _phase(s: str) -> str:
    t = (s or "").lower()
    return next((v for k, v in procmod._PHASE.items() if k in t), "")


def pds_row(tag: str, pdoc: dict | None) -> dict | None:
    return (pdoc or {}).get("by_tag", {}).get(linelist.key(tag)) if pdoc else None


def pds(tag_key: str, C: dict, pdoc: dict | None, ref: dict | None, on_form: set | None = None) -> list[dict]:
    """IN-PDS-00 / IN-PDS-01 against the project's Process Data (PDS)."""
    src = (ref or {}).get("filename", "Process Data")
    if not pdoc:
        return [_row("IN-PDS-00", "Process Data", "", "", NOT_IN, "프로젝트에 Process Data(PDS) 가 올라와 있지 않음", src, "pds")]
    row = (pdoc.get("by_tag") or {}).get(linelist.key(tag_key))
    if not row:
        return [_row("IN-PDS-00", "Process Data", tag_key, "없음", NOT_IN, "PDS 에 이 Tag 가 없음 (공백 · 하이픈 무시하고 찾음)", src, "pds")]
    V = row.get("values", {})
    pv = lambda k: ((V.get(k) or {}).get("v") or "", (V.get(k) or {}).get("unit") or "")   # noqa: E731
    page, out = row.get("page"), []
    for key, item in (("fluid", "Fluid"), ("fluid_state", "Phase")):
        p, _ = pv(key)
        d = C.get(key, "")
        if blank(p) or (on_form is not None and blank(d) and not on_form & set(ON_FORM[key])):
            continue
        if blank(d):
            out.append(_row("IN-PDS-01", item, "", p, BLANK, "Datasheet 에 값이 없음", f"{src} p.{page}", key, None))
            continue
        res = (OK if _phase(d) == _phase(p) else MISMATCH) if key == "fluid_state" and _phase(d) and _phase(p) else _cmp_text(d, p)
        out.append(_row("IN-PDS-01", item, d, p, res, "같음" if res == OK else f"Datasheet '{d}' · PDS '{p}'", f"{src} p.{page}", key))
    for key, item, kind in (("op_pressure", "Operating Pressure", "p"), ("design_pressure", "Design Pressure", "p"),
                            ("op_temp", "Operating Temperature", "t"), ("design_temp", "Design Temperature", "t"),
                            ("density", "Density", "x"), ("flow", "Flow", "x")):
        p, pu = pv(key)
        if blank(p):
            continue
        q = C.get(key) or {}
        if on_form is not None and q.get("max") is None and not on_form & set(ON_FORM[key]):
            continue                                       # this form has no such row
        if q.get("max") is None:
            out.append(_row("IN-PDS-01", item, q.get("text", ""), f"{p} {pu}".strip(), BLANK, "Datasheet 에 숫자가 없음", f"{src} p.{page}", key))
            continue
        pq = quantity({"value": f"{p} {pu}".strip()})
        pq["unit"] = pu or pq.get("unit", "")
        ds_txt, pd_txt = q.get("text") or f"{q['max']} {q.get('unit', '')}", f"{p} {pu}".strip()
        if kind == "p":
            a, b = _press_bar(q), _press_bar(pq)
            if a[0] is None or b[0] is None:
                out.append(_row("IN-PDS-01", item, ds_txt, pd_txt, REVIEW, f"압력 단위를 알 수 없음 ('{q.get('unit', '')}' · '{pu}')", f"{src} p.{page}", key))
                continue
            if a[2] != b[2]:
                out.append(_row("IN-PDS-01", item, ds_txt, pd_txt, REVIEW, f"게이지/절대 기준이 다르거나 없음 ('{q.get('unit', '')}' · '{pu}') — 손으로 비교", f"{src} p.{page}", key))
                continue
            dvals, pvals = [x for x in (a[0], a[1]) if x is not None], [b[0]]
        elif kind == "t":
            a, b = _temp_c(q), _temp_c(pq)
            if a[0] is None or b[0] is None:
                out.append(_row("IN-PDS-01", item, ds_txt, pd_txt, REVIEW, f"온도 단위를 알 수 없음 ('{q.get('unit', '')}' · '{pu}')", f"{src} p.{page}", key))
                continue
            dvals, pvals = list(a), [b[0]]
            if q.get("nor") is not None:
                dvals.append(_temp_c({"max": q["nor"], "unit": q.get("unit", "")})[0])
        else:
            if (q.get("unit") or "").replace(" ", "").lower() != (pu or "").replace(" ", "").lower() and q.get("unit") and pu:
                out.append(_row("IN-PDS-01", item, ds_txt, pd_txt, REVIEW, f"단위가 다름 ('{q.get('unit')}' · '{pu}')", f"{src} p.{page}", key))
                continue
            dvals, pvals = [q["max"], q["min"]] + ([q["nor"]] if q.get("nor") is not None else []), [pq.get("max")]
        if kind != "t" and q.get("nor") is not None and kind == "p":
            dvals.append(q["nor"] * procmod.unit_of(q.get("unit", ""))[2])
        hit = any(abs(d - pvals[0]) <= max(0.01 * abs(pvals[0]), 0.05) for d in dvals if d is not None)
        out.append(_row("IN-PDS-01", item, ds_txt, pd_txt, OK if hit else MISMATCH,
                        "PDS 값이 Datasheet 의 Max/Nor/Min 중 하나와 같음" if hit else "PDS 값이 Datasheet 의 어느 값과도 다름", f"{src} p.{page}", key))
    return out


def pms_check(C: dict, pms: dict | None, ref: dict | None, area: str = "") -> list[dict]:
    from app.valve import pms as pmsmod
    cl = C.get("piping_class", "")
    if not pms or blank(cl):
        return []
    src = (ref or {}).get("filename", "PMS")
    c, how = pmsmod.find_class(pms, cl, C.get("line_no", ""), area)
    if not c:
        return [_row("IN-PMS-01", "Pipe Class", cl, "없음", REVIEW, how, src, "piping_class")]
    sure = not how or how.startswith(" (area unknown")     # found as written; only the area was not known
    out = [_row("IN-PMS-01", "Pipe Class", cl, c["code"], OK if sure else REVIEW, "PMS 에 있음" + (" — 구역을 몰라 QN 먼저 찾음" if how else "") if sure else how,
                f"{src} p.{c.get('header_page') or (c.get('pages') or [''])[0]}", "piping_class")]
    if c.get("rating") and not blank(C.get("rating")):
        n = [float(x) for x in re.findall(r"\d{3,4}", C["rating"])]
        if n:
            res = OK if int(n[0]) == int(c["rating"]) else MISMATCH
            out.append(_row("IN-PMS-02", "Rating", C["rating"], f"Class {c['rating']} ({c.get('flange_class', '')})", res,
                            "같음" if res == OK else "Datasheet Rating 이 PMS Flange Class 와 다름", f"{src} p.{c.get('header_page')}", "rating"))
    if c.get("material"):
        out.append(_row("IN-PMS-01", "PMS Material (참고)", "", c["material"], OK, "PMS Class 의 재질 — 접액부 재질은 사람이 확인",
                        f"{src} p.{c.get('header_page')}", "material", human=True))
    return out


def line_check(C: dict, ll: dict | None, ref: dict | None) -> list[dict]:
    ln = C.get("line_no", "")
    if not ll or blank(ln):
        return []
    src = (ref or {}).get("filename", "Process Line List")
    row, how = linelist.find(ll, ln)
    if not row:
        return [_row("IN-LL-00", "Line No", ln, "없음", REVIEW, how or "Process Line List 에 이 Line No 가 없음", src, "line_no")]
    where = f"{src} · {row['sheet']} {row['row']}행"
    from_pds = " (Datasheet 에 Line No 칸이 없어 PDS 의 Line No 사용)" if C.get("line_no_from") == "PDS" else ""
    out = [_row("IN-LL-00", "Line No", ln, row["line_no"], OK if not how else REVIEW, (how or "Line List 에 있음") + from_pds, where, "line_no")]
    cl = C.get("piping_class", "")
    if not blank(cl) and row.get("pipe_class"):
        a, b = linelist.key(cl), linelist.key(row["pipe_class"])
        res, why = (OK, "같음") if a == b else (REVIEW, "한쪽이 다른 쪽의 앞부분 (꼬리표 차이) — 확인") if a.startswith(b) or b.startswith(a) else (MISMATCH, "다름")
        out.append(_row("IN-LL-01", "Pipe Class", cl, row["pipe_class"], res, why, where, "piping_class"))
    dp = C.get("design_pressure") or {}
    lp = nums(row.get("design_p", ""))
    if lp:
        a = _press_bar(dp)
        if a[0] is None:
            out.append(_row("IN-LL-02", "Design Pressure", dp.get("text", ""), f"{row['design_p']} barg",
                            BLANK if not dp else REVIEW, "Datasheet Design Pressure 가 없거나 단위를 알 수 없음", where, "design_pressure"))
        elif a[2] and a[2] != "g":
            out.append(_row("IN-LL-02", "Design Pressure", dp.get("text", ""), f"{row['design_p']} barg", REVIEW,
                            "Datasheet 는 절대압 — Line List 는 barg (보정 안 함)", where, "design_pressure"))
        else:
            res = MISMATCH if lp[0] > a[0] + 1e-6 else OK
            out.append(_row("IN-LL-02", "Design Pressure", dp.get("text", ""), f"{row['design_p']} barg", res,
                            f"Line Design {lp[0]} barg > Datasheet {round(a[0], 3)} bar" if res == MISMATCH else "Datasheet 가 Line 이상", where, "design_pressure"))
    dt = C.get("design_temp") or {}
    tmax, tmin = nums(row.get("design_t_max", "")), nums(row.get("design_t_min", ""))
    if tmax or tmin:
        a = _temp_c(dt)
        if a[0] is None:
            out.append(_row("IN-LL-03", "Design Temperature", dt.get("text", ""), f"{row.get('design_t_max', '')} / {row.get('design_t_min', '')} °C",
                            BLANK if not dt else REVIEW, "Datasheet Design Temperature 가 없거나 단위를 알 수 없음", where, "design_temp"))
        else:
            if tmax:
                res = MISMATCH if tmax[0] > a[0] + 1e-6 else OK
                out.append(_row("IN-LL-03", "Design Temp (Max)", dt.get("text", ""), f"{tmax[0]:g} °C", res,
                                f"Line {tmax[0]:g} °C > Datasheet {a[0]:g} °C" if res == MISMATCH else "Datasheet 가 Line 이상", where, "design_temp"))
            if tmin:
                res = MISMATCH if tmin[0] < a[1] - 1e-6 else OK
                out.append(_row("IN-LL-04", "Design Temp (Min)", dt.get("text", ""), f"{tmin[0]:g} °C", res,
                                f"Line {tmin[0]:g} °C < Datasheet {a[1]:g} °C" if res == MISMATCH else "Datasheet 가 Line 이하", where, "design_temp"))
    ls = C.get("line_size", "")
    if not blank(ls) and row.get("size_inch"):
        a, b = nums(ls), nums(row["size_inch"])
        if a and b:
            res = OK if abs(a[0] - b[0]) < 1e-6 or (abs(a[0] - (nums(row.get('size_mm', '')) or [0])[0]) < 1e-6) else MISMATCH
            out.append(_row("IN-LL-05", "Line Size", ls, f"{row['size_inch']} ({row.get('size_mm', '')} mm)", res, "같음" if res == OK else "다름", where, "line_size"))
    return out


def item_rules(sheet: dict, C: dict) -> list[dict]:
    """Rules of one item kind — only where the datasheet itself gives both values; always marked for a human."""
    out, kind = [], sheet["kind"]
    if kind in ("pt", "pg", "dpg") and C.get("range") and C.get("op_pressure"):
        r, op = _press_bar(C["range"]), _press_bar(C["op_pressure"])
        if r[0] is not None and op[0] is not None and r[2] == op[2]:
            res = MISMATCH if r[0] < op[0] - 1e-6 else OK
            out.append(_row("IN-ITM-01", "Range vs Max Operating Pressure", C["range"].get("text", ""), C["op_pressure"].get("text", ""), res,
                            "Range 상한이 최대 운전압력보다 낮음 — 측정 범위 확인" if res == MISMATCH else "Range 가 운전압력을 덮음",
                            "같은 Datasheet", "range", human=True))
    if kind == "psv" and C.get("set_pressure") and C.get("design_pressure"):
        s, d = _press_bar(C["set_pressure"]), _press_bar(C["design_pressure"])
        if s[0] is not None and d[0] is not None and s[2] == d[2]:
            res = MISMATCH if s[0] > d[0] + 1e-6 else OK
            out.append(_row("IN-ITM-02", "Set Pressure vs Design Pressure", C["set_pressure"].get("text", ""), C["design_pressure"].get("text", ""), res,
                            "Set Pressure 가 Design Pressure 보다 높음 — 보호 대상 설계압력 확인" if res == MISMATCH else "Set ≤ Design",
                            "같은 Datasheet", "set_pressure", human=True))
    return out


def open_items(sheet: dict) -> list[dict]:
    """IN-OPN-01: every row whose value (or a sub-column) still says HOLD / TBA / TBC / TBD."""
    out = []
    card = {f"{it['block']}.{it['no']}" if it["block"] != 1 else str(it["no"]): it for it in instrument.cards()[sheet["form_id"]]["items"]}
    for no, v in sheet.get("rows", {}).items():
        texts = [v.get("value") or ""] + [f"{k}: {x}" for k, x in (v.get("sub") or {}).items() if x]
        hit = next((t for t in texts if _OPEN.search(t)), None)
        if not hit:
            continue
        it = card.get(no) or {}
        key = v.get("std_key") or it.get("std_key") or f"row:{no}"
        out.append(_row("IN-OPN-01", f"{no}. {v.get('label') or it.get('label', '')}", hit.strip(), "확정 값", REVIEW,
                        f"'{_OPEN.search(hit).group(1).upper()}' 로 남아 있음 — 값이 정해지면 다음 Rev 에 반영 필요", "같은 Datasheet", key, v.get("page")))
    return out


def unit_basis(C: dict) -> list[dict]:
    """IN-UNIT-01: operating pressure in gauge and design pressure in absolute (or the other way) on one datasheet."""
    a, b = C.get("op_pressure") or {}, C.get("design_pressure") or {}
    if not a.get("unit") or not b.get("unit"):
        return []
    ba, bb = procmod.unit_of(a["unit"])[1], procmod.unit_of(b["unit"])[1]
    if ba and bb and ba != bb:
        return [_row("IN-UNIT-01", "Pressure basis", f"Oper. {a['unit']} · Design {b['unit']}", "같은 기준", REVIEW,
                     "운전압과 설계압의 게이지/절대 기준이 다름 — 비교 · 확인 필요", "같은 Datasheet", "design_pressure", human=True)]
    return []


def review(sheet: dict, tag: str, ctx: dict) -> dict:
    """All rows for one tag of one sheet.  ctx: {pds, pds_ref, pms, pms_ref, ll, ll_ref, area, required{form:[keys]}}."""
    vals = instrument.values(sheet)
    C = canonical(vals)
    req_keys = (ctx.get("required") or {}).get(sheet["form_id"])
    rows = required(sheet, vals, req_keys, confirmed=req_keys is not None)
    on_form = {it.get("std_key") for it in instrument.cards()[sheet["form_id"]]["items"] if it.get("std_key")}
    rows += pds(tag, C, ctx.get("pds"), ctx.get("pds_ref"), on_form)
    prow = pds_row(tag, ctx.get("pds"))
    if blank(C.get("line_no")) and prow and not blank((prow.get("values", {}).get("line_no") or {}).get("v")):
        C["line_no"] = prow["values"]["line_no"]["v"]           # the form has no Line No row: the PDS row of the tag gives it
        C["line_no_from"] = "PDS"
    if blank(C.get("piping_class")) and prow and not blank((prow.get("values", {}).get("piping_class") or {}).get("v")):
        C["piping_class"] = prow["values"]["piping_class"]["v"]
        C["piping_class_from"] = "PDS"
    rows += pms_check(C, ctx.get("pms"), ctx.get("pms_ref"), ctx.get("area", ""))
    rows += line_check(C, ctx.get("ll"), ctx.get("ll_ref"))
    rows += item_rules(sheet, C)
    rows += open_items(sheet)
    rows += unit_basis(C)
    n = {r: sum(1 for x in rows if x["result"] == r) for r in (MISMATCH, MISSING, REVIEW, NOT_IN, BLANK, OK)}
    return {"canonical": C, "rows": rows, "counts": n,
            "issues": sum(1 for x in rows if x["result"] in (MISMATCH, MISSING, REVIEW)),
            "in_pds": not any(x["rule"] == "IN-PDS-00" for x in rows)}
