"""valve42 — the project's Valve Specifications (On/Off Valve · Motor Operated Valve · Control Valve) as review basis.

User 2026-11-20: "Spec 3권을 학습해 이를 기반으로 코멘트 할 수 있어야 한다".

The specification is a reference document the user uploads on the 공통 자료 page (kind 'vspec' — never in the repository).
It is read into numbered clauses at upload (read_spec).  The checks below are templates: each looks for ITS clause in the
uploaded specification by the words the clause is written in, takes the required value from that clause's own text (rate,
class, limit, factor, temperature …) and compares the datasheet with it.  A check whose clause the specification does not
contain does not run — nothing is required that the specification does not say.  Every finding cites the specification,
the clause number, the page and the clause text.  No LLM — deterministic text matching.

Which specification a datasheet answers to (scope): Control Valve form (101 · ISA-20) or a control-valve tag → 'cv';
MOV tag / Form 102 → 'mov'; Ball / ESDV · SDV · BDV · XV → 'onoff'.
"""
from __future__ import annotations

import re
from collections import Counter

from app.valve import schema

TYPE = "Spec Compliance"
_NUM = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){1,3})\s+(\S.*)$")
_HEAD = re.compile(r"^(\d{1,2})\.0\s+([A-Z][A-Z /&,()-]{3,})$")
_BUL = re.compile(r"^[•➢▪●·\-–]\s*")
_PLACE = re.compile(r"^\s*(VTA|TBA|TBC|TBD|HOLD|N/?A|-|—)\s*$", re.I)


# ── reading ───────────────────────────────────────────────────────────────────────────────────────────────────────
def scope_of_title(title: str) -> str:
    t = (title or "").upper()
    if "MOTOR OPERATED" in t:
        return "mov"
    if "CONTROL VALVE" in t:
        return "cv"
    if re.search(r"ON[\s/-]*OFF", t):
        return "onoff"
    return ""


def read_spec(path: str) -> dict:
    """{doc_no, rev, date, title, scope, clauses: [{no, text, page}]} — the numbered clauses of the body (contents list,
    page headers and footers left out)."""
    from app.valve import extract
    with extract.PDF_LOCK, extract.open_pdf(path, tries=1) as doc:
        pages = [p.get_text() for p in doc]
    first = pages[0] if pages else ""
    later = pages[1] if len(pages) > 1 else ""
    m = (re.search(r"DOCUMENT NO\s*\n(?:[^\n]*\n){0,4}?\s*(\d{2,4}-\d{2}-[A-Z]{2}-[A-Z]{3}-\d{4,6})\s*\n\s*([A-Z0-9]{1,2})\s*\n", first)
         or re.search(r"Doc\.?\s*(?:ID|No)\.?:\s*\n?\s*(\d{2,4}-\d{2}-[A-Z]{2}-[A-Z]{3}-\d{4,6})", later))
    doc_no = m.group(1) if m else ""
    rev = m.group(2) if m and m.lastindex and m.lastindex >= 2 else ""
    md = re.search(r"\n\s*([A-Z0-9]{1,2})\s*\n\s*(\d{1,2}[-/.]\d{1,2}[-/.]\d{4})\s*\n", first)
    date = md.group(2) if md else ""
    rev = rev or (md.group(1) if md else "")
    head = " ".join(first.split("\n")[:12])
    title = ""
    m = re.search(r"((?:UNIT-\d+,\s*)?SPECIFICATION,?[^\n]{3,80}(?:\n[^\n]{3,60}){0,2})", first)
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip()
        title = re.split(r"\s{2,}|\s(?=[A-Z]\s*$)", title)[0]
    # lines printed on most pages = header / footer
    cnt = Counter()
    for t in pages:
        cnt.update({ln.strip() for ln in t.split("\n") if ln.strip()})
    common = {ln for ln, n in cnt.items() if n >= max(3, len(pages) * 0.5)}
    clauses, cur, sec, pend = [], None, "", False
    bullets = Counter()
    for pno, t in enumerate(pages, 1):
        if pno == 1 or sum(1 for ln in t.split("\n") if re.search(r"\.{6,}", ln)) >= 5:
            continue                                         # cover sheet · contents pages
        for ln in t.split("\n"):
            s = ln.strip()
            if s in ("•", "➢", "▪", "●", "·", "o", "-"):            # a bullet printed alone on its line: the item follows
                pend = bool(sec)                             # (checked before the header filter: '•' is on every page)
                continue
            if not s or s in common or re.search(r"\.{6,}", s) or re.fullmatch(r"\d+\s+of\s+\d+", s):
                continue
            if re.fullmatch(r"\d{1,2}(?:\.\d{1,2}){1,3}", s):  # a clause number alone on its line: its text follows
                sec, pend = s, False
                cur = {"no": s, "text": "", "page": pno}
                clauses.append(cur)
                continue
            if _BUL.match(s) and s[:1] in "•➢▪●·" and sec:
                bullets[sec] += 1
                cur = {"no": f"{sec} ({bullets[sec]})", "text": _BUL.sub("", s), "page": pno}
                clauses.append(cur)
                continue
            if pend:
                pend = False
                bullets[sec] += 1
                cur = {"no": f"{sec} ({bullets[sec]})", "text": s, "page": pno}
                clauses.append(cur)
                continue
            mh, mn = _HEAD.match(s), _NUM.match(s)
            if mh:
                sec = mh.group(1) + ".0"
                cur = {"no": sec, "text": mh.group(2), "page": pno, "head": True}
                clauses.append(cur)
                continue
            if mn and not re.match(r"^\d+(\.\d+)*\s+(of|x|mm|m/s|°C|barg?)\b", s, re.I):
                sec = mn.group(1)
                cur = {"no": sec, "text": mn.group(2), "page": pno}
                clauses.append(cur)
                continue
            if _BUL.match(s) and sec and s[:1] in "•➢▪●":
                bullets[sec] += 1
                cur = {"no": f"{sec} ({bullets[sec]})", "text": _BUL.sub("", s), "page": pno}
                clauses.append(cur)
                continue
            if cur is not None:
                cur["text"] += " " + s
    for c in clauses:
        c["text"] = re.sub(r"\s+", " ", c["text"]).strip()
    body = [c for c in clauses if not c.get("head") and len(c["text"]) > 12]
    return {"doc_no": doc_no, "rev": rev, "date": date, "title": title or head[:120], "scope": scope_of_title(title or head),
            "clauses": body, "v": 1}


# ── which specification a datasheet answers to ──────────────────────────────────────────────────────────────────────
_CV_TAG = re.compile(r"^(?:[A-Z]{0,2})CV$|^(?:F|L|P|T|PD|H|A|D)V$")


def scope_of(ds: dict) -> str:
    vt = (ds.get("valve_type") or "").upper()
    form = ds.get("form") or ""
    if vt == "MOV" or form == "102":
        return "mov"
    if form in ("101", "ISA20") or _CV_TAG.match(vt):
        return "cv"
    if vt in ("ESDV", "SDV", "BDV", "XV", "EBV", "HV") or ds.get("family") == "ball" or form in ("80", "on/off"):
        return "onoff"
    return ""


# ── helpers ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def _find(spec, pattern, flags=re.I):
    rx = re.compile(pattern, flags)
    for c in spec.get("clauses", []):
        m = rx.search(c["text"])
        if m:
            return c, m
    return None, None


def _val(F, *keys):
    for k in keys:
        f = F.get(k)
        if f:
            v = f.get("edited_value") if f.get("edited_value") is not None else f.get("value")
            if v and str(v).strip():
                return k, str(v).strip()
    return keys[0], ""


def _stated(v: str) -> bool:
    return bool(v) and not _PLACE.match(v)


def _num(v: str):
    m = re.search(r"-?\d+(?:\.\d+)?", (v or "").replace(",", "."))
    return float(m.group(0)) if m else None


def _inch(v: str):
    v = (v or "").replace("”", '"').replace("″", '"')
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:\"|in\b|inch)", v, re.I) or re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*", v)
    if m:
        return float(m.group(1))
    m = re.search(r"\b(\d{2,4})\s*mm\b|\bDN\s*(\d{2,4})", v, re.I)
    return round(float(m.group(1) or m.group(2)) / 25.4, 1) if m else None


_ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6}


def _leak_class(v: str):
    m = re.search(r"\bclass\s*(VI|IV|V|III|II|I)\b", v or "", re.I) or re.search(r"\b(VI|IV|V|III)\b", v or "")
    return _ROMAN.get(m.group(1).upper()) if m else None


def _cut(s, n=220):
    s = re.sub(r"\s+", " ", s or "").strip()
    return s if len(s) <= n else s[:n - 1] + "…"


def _text_all(ds) -> str:
    parts = [str((f.get("value") or "")) for f in (ds.get("fields") or [])]
    parts += [n.get("text", "") for n in ds.get("notes") or []]
    parts += [str(v) for v in (ds.get("general_notes") or {}).values()]
    return " ".join(parts)


# ── the checks ──────────────────────────────────────────────────────────────────────────────────────────────────────
# each: (id, scopes, function(spec, F, ds) -> list of finding dicts).  A finding: key (datasheet field), desc, expected,
# severity, clause, match.  Wording: what the specification requires, what the datasheet says, what to do.
def _fire_safe(spec, F, ds):
    if ds.get("family") not in ("ball", "") and scope_of(ds) == "onoff":
        return []
    c, m = _find(spec, r"(?:ball valves?|resilient seated valves?)[^.]{0,60}fire[ -]?safe[^.]{0,80}?(API\s*607(?:\s*(?:/|or|and)\s*API\s*6FA)?)")
    if not c:
        return []
    if "resilient" in m.group(0).lower() and not re.search(r"soft|ptfe|peek|rptfe|nylon|devlon|resilient", _val(F, "seat_material")[1], re.I):
        return []
    k, v = _val(F, "fire_safe")
    fire = r"API\s*6\s*0\s*7|API\s*6\s*FA|ISO\s*10497|fire[ -]?safe|fire[ -]?test"
    if re.search(fire, v, re.I) or (not v and re.search(fire, _text_all(ds), re.I)):    # the row, or the notes / general notes
        return []
    return [dict(key=k, clause=c, m=m, expected=f"Fire-safe per {m.group(1)}", severity="Minor" if not v else "Major",
                 desc=f"Spec §{c['no']}: fire-safe design per {m.group(1)} required; datasheet {('states ' + repr(v)) if v else 'does not state it'}. State fire-safe design / certificate.")]


def _rate(spec, F, ds):
    c, m = _find(spec, r"(API\s*598\s*/\s*ISO\s*5208|ISO\s*5208)\s*Rate\s*([A-G])\b")
    if not c:
        return []
    k, v = _val(F, "leakage_class", "tightness", "seat_tightness")
    if not _stated(v):
        return []
    got = re.search(r"Rate\s*([A-G])\b", v, re.I)
    if got and got.group(1).upper() == m.group(2).upper():
        return []
    if not got and not re.search(r"5208|598", v):
        return []
    return [dict(key=k, clause=c, m=m, expected=f"{m.group(1)} Rate {m.group(2)}", severity="Minor",
                 desc=f"Spec §{c['no']}: seat leakage {m.group(1)} Rate {m.group(2)} (zero leakage); datasheet {v!r}. Confirm the leakage rate (a different rate needs the process datasheet's basis).")]


def _cv_class(spec, F, ds):
    c, m = _find(spec, r"leakage class shall be minimum class\s*(VI|IV|V|III|II)\b")
    if not c:
        return []
    k, v = _val(F, "leakage_class", "tightness")
    got = _leak_class(v)
    need = _ROMAN[m.group(1).upper()]
    if got is None or got >= need:
        return []
    return [dict(key=k, clause=c, m=m, expected=f"Class {m.group(1)} minimum",
                 desc=f"Spec §{c['no']}: seat leakage class minimum Class {m.group(1)}; datasheet {v!r}. Raise the leakage class.")]


def _chrome(spec, F, ds):
    c, m = _find(spec, r"chrome[ -]plated balls? (?:are|is) not acceptable")
    if not c:
        return []
    k, v = _val(F, "ball_material")
    if not re.search(r"chrom|\bHCr\b|\bCr\s*plat", v, re.I):
        return []
    return [dict(key=k, clause=c, m=m, expected="No chrome-plated ball",
                 desc=f"Spec §{c['no']}: chrome-plated balls are not acceptable; datasheet ball {v!r}. Change the ball coating (other metallic plating needs COMPANY approval).")]


def _wafer(spec, F, ds):
    c, m = _find(spec, r"wafer[- ]type bod(?:y|ies) (?:are|is) not acceptable")
    if not c:
        return []
    k, v = _val(F, "connections", "body_type")
    if not re.search(r"wafer|flangeless", v, re.I):
        return []
    return [dict(key=k, clause=c, m=m, expected="Flanged (wafer not acceptable)",
                 desc=f"Spec §{c['no']}: flangeless / wafer-type bodies are not acceptable unless COMPANY approves; datasheet {v!r}. Use flanged ends or attach the approval.")]


def _diaphragm(spec, F, ds):
    c, m = _find(spec, r"diaphragm type actuators shall not be used")
    if not c:
        return []
    k, v = _val(F, "act_type")
    if not re.search(r"diaphragm", v, re.I):
        return []
    return [dict(key=k, clause=c, m=m, expected="Piston actuator (spring return / scotch yoke)",
                 desc=f"Spec §{c['no']}: pneumatic diaphragm actuators shall not be used; datasheet actuator {v!r}. Use a piston actuator.")]


def _limit_switch(spec, F, ds):
    c, m = _find(spec, r"limit switches shall not be used")
    if not c:
        return []
    out = []
    for key in ("limit_switch", "limit_switch_type", "ls_opened", "ls_closed"):
        k, v = _val(F, key)
        if _stated(v) and not re.search(r"^\s*(no|not required|none|n/?a)\b", v, re.I):
            out.append(dict(key=k, clause=c, m=m, expected="Position transmitter (no limit switches)",
                            desc=f"Spec §{c['no']}: limit switches shall not be used — position transmitters are the default; datasheet {v!r}. Replace by a position transmitter."))
            break
    return out


def _ip(spec, F, ds):
    c, m = _find(spec, r"\bIP\s*(\d{2})\s*(?:or better|minimum)|minimum\s+IP\s*(\d{2})|shall be IP\s*(\d{2})")
    if not c:
        return []
    need = int(next(g for g in m.groups() if g))
    out = []
    for key in ("ingress", "elec_protection", "ex_type"):
        k, v = _val(F, key)
        got = re.search(r"\bIP\s*(\d)(\d)\b", v or "", re.I)
        if got and int(got.group(1) + got.group(2)) < need:
            out.append(dict(key=k, clause=c, m=m, expected=f"IP{need} minimum",
                            desc=f"Spec §{c['no']}: enclosure IP{need} minimum; datasheet {v!r}. Raise the ingress protection."))
    return out


def _fugitive(spec, F, ds):
    c, m = _find(spec, r"(CO2|hazardous|toxic)[^.]{0,80}?(?:Class\s*([A-C])\s*)?[^.]{0,40}fugitive emission[^.]{0,60}ISO\s*15848-?1")
    if not c:
        return []
    cls = re.search(r"Class\s*([A-C])\b", c["text"])
    svc = " ".join(_val(F, k)[1] for k in ("fluid", "service", "toxic", "valve_function"))
    if not re.search(r"CO2|CO₂|toxic|H2S|sour|hazard", svc + " " + _val(F, "toxic")[1], re.I):
        return []
    allt = _text_all(ds)
    if re.search(r"15848", allt):
        if cls and not re.search(rf"15848[^.]{{0,120}}(?:class|cl\.?)\s*{cls.group(1)}\b|(?:class|cl\.?)\s*{cls.group(1)}\b[^.]{{0,120}}15848", allt, re.I):
            return [dict(key=_val(F, "packing_type", "packing_material")[0], clause=c, m=m, severity="Minor", expected=f"ISO 15848-1 Class {cls.group(1)}",
                         desc=f"Spec §{c['no']}: ISO 15848-1 Class {cls.group(1)} type-tested fugitive emission packing for CO2 / hazardous / toxic service; the datasheet names ISO 15848 without Class {cls.group(1)}. State the class.")]
        return []
    want = f"ISO 15848-1" + (f" Class {cls.group(1)}" if cls else "")
    return [dict(key=_val(F, "packing_type", "packing_material")[0], clause=c, m=m, expected=want, severity="Minor",
                 desc=f"Spec §{c['no']}: {want} type-tested fugitive emission packing for CO2 / hazardous / toxic service; not stated on the datasheet. Add the requirement.")]


def _stroke(spec, F, ds):
    c, m = _find(spec, r"(\d+)\s*inch and smaller:\s*Less than\s*(\d+(?:\.\d+)?)\s*second[^.;]{0,40}air fail")
    if not c:
        return []
    m2 = re.search(r"(\d+)\s*inch and larger:\s*Less than\s*(\d+(?:\.\d+)?)\s*second per inch[^.;]{0,40}air fail", c["text"], re.I)
    size = _inch(_val(F, "body_size")[1])
    k, v = _val(F, "stroke_closed", "stroke_time_s", "act_stroke_time")
    t = _num(v) if _stated(v) and re.search(r"\d", v) and not re.search(r"note", v, re.I) else None
    if size is None or t is None:
        return []
    if size <= float(m.group(1)):
        lim, how = float(m.group(2)), f"{m.group(1)}\" and smaller: < {m.group(2)} s"
    elif m2 and size >= float(m2.group(1)):
        lim, how = float(m2.group(2)) * size, f"{m2.group(1)}\" and larger: < {m2.group(2)} s per inch = {float(m2.group(2)) * size:g} s"
    else:
        return []
    if t < lim:
        return []
    return [dict(key=k, clause=c, m=m, expected=f"< {lim:g} s", severity="Minor",
                 desc=f"Spec §{c['no']}: air-fail stroke time {how}; datasheet {v!r} for {size:g}\". Confirm the actuator sizing or the process datasheet's stroke time.")]


def _safety_factor(spec, F, ds):
    c, m = _find(spec, r"actuator torque shall be\s*(\d+(?:\.\d+)?)\s*times|safety factor shall be\s*(\d+(?:\.\d+)?)\s*for actuator sizing")
    if not c:
        return []
    need = float(m.group(1) or m.group(2))
    k, v = _val(F, "act_safety_factor")
    got = _num(v) if _stated(v) else None
    if got is None or got >= need or got > 10:
        return []
    return [dict(key=k, clause=c, m=m, expected=f"≥ {need:g}",
                 desc=f"Spec §{c['no']}: actuator safety factor {need:g} on the valve torque; datasheet {v!r}. Resize the actuator.")]


def _ext_bonnet(spec, F, ds):
    c, m = _find(spec, r"Extension bonnets? for fluid operating temperature down to\s*(-\s*\d+)\s*°?\s*C or above\s*\+?\s*(\d+)\s*°?\s*C")
    if not c:
        return []
    lo, hi = float(m.group(1).replace(" ", "")), float(m.group(2))
    temps = [x for x in (_num(_val(F, k)[1]) for k in ("op_temp.min", "op_temp", "op_temp.max", "op_temp.nor")) if x is not None]
    if not temps or (min(temps) > lo and max(temps) < hi):
        return []
    k, v = _val(F, "bonnet_type")
    if re.search(r"exten|cryo", v, re.I):
        return []
    return [dict(key=k, clause=c, m=m, expected="Extension bonnet",
                 desc=f"Spec §{c['no']}: extension bonnet for operating temperature down to {lo:g} °C or above {hi:g} °C; datasheet operating {min(temps):g}…{max(temps):g} °C with bonnet {v!r}. Specify an extension bonnet.")]


def _noise(spec, F, ds):
    c, m = _find(spec, r"sound levels? shall not exceed(?:ed)?\s*(\d{2,3})\s*dBA")
    if not c:
        return []
    lim = float(m.group(1))
    out = []
    for key in ("spl_pred.max", "spl_pred.nor", "spl_pred", "spl_allow"):
        k, v = _val(F, key)
        x = _num(v) if _stated(v) else None
        if x is not None and x > lim:
            out.append(dict(key=k, clause=c, m=m, expected=f"≤ {lim:g} dBA",
                            desc=f"Spec §{c['no']}: predicted sound level ≤ {lim:g} dBA (1 m downstream, 1 m from the pipe); datasheet {v!r}. Use a low-noise trim / attenuation."))
            break
    return out


def _hart(spec, F, ds):
    c, m = _find(spec, r"positioners? shall have analog 4-20\s*mA output with HART")
    if not c:
        return []
    k, v = _val(F, "pos_signal", "positioner")
    if not re.search(r"4\s*-\s*20", v) or re.search(r"HART|FF\b|fieldbus", v, re.I):
        return []
    return [dict(key=k, clause=c, m=m, expected="4-20 mA + HART", severity="Minor",
                 desc=f"Spec §{c['no']}: positioner 4-20 mA with HART (FF where the specification says for a brownfield area); datasheet {v!r}. State the protocol.")]


def _aluminium(spec, F, ds):
    c, m = _find(spec, r"aluminium|aluminum")
    if not c or not re.search(r"housings? shall not be permitted|not (?:be )?permitted", c["text"], re.I):
        return []
    k, v = _val(F, "act_material", "act_yoke_material")
    if not re.search(r"alumin", v, re.I):
        return []
    return [dict(key=k, clause=c, m=m, expected="Ductile cast iron / cast steel housing",
                 desc=f"Spec §{c['no']}: aluminium operator housings are not permitted; datasheet {v!r}. Use ductile cast iron or cast steel.")]


CHECKS = [("SP-01", ("onoff", "cv"), _fire_safe), ("SP-02", ("onoff",), _rate), ("SP-03", ("cv",), _cv_class),
          ("SP-04", ("onoff",), _chrome), ("SP-05", ("onoff", "cv", "mov"), _wafer), ("SP-06", ("onoff",), _diaphragm),
          ("SP-07", ("onoff", "cv"), _limit_switch), ("SP-08", ("onoff", "cv", "mov"), _ip), ("SP-09", ("onoff", "mov", "cv"), _fugitive),
          ("SP-10", ("onoff",), _stroke), ("SP-11", ("onoff", "cv"), _safety_factor), ("SP-12", ("onoff",), _ext_bonnet),
          ("SP-13", ("cv",), _noise), ("SP-14", ("cv",), _hart), ("SP-15", ("mov",), _aluminium)]
TITLES = {"SP-01": "Fire-safe design", "SP-02": "Seat leakage rate (ISO 5208)", "SP-03": "Minimum leakage class (FCI 70-2)",
          "SP-04": "No chrome-plated ball", "SP-05": "No wafer / flangeless body", "SP-06": "No diaphragm actuator (on/off)",
          "SP-07": "Position transmitter instead of limit switches", "SP-08": "Enclosure IP rating", "SP-09": "Fugitive emission (ISO 15848-1)",
          "SP-10": "Stroke time limit", "SP-11": "Actuator safety factor", "SP-12": "Extension bonnet by temperature",
          "SP-13": "Sound level limit", "SP-14": "Positioner HART", "SP-15": "No aluminium operator housing"}


def findings(ds: dict, specs: list[dict]) -> list[dict]:
    """Spec-based findings for one datasheet: [{key, check, desc, expected, severity, evidence, basis}]."""
    sc = scope_of(ds)
    if not sc:
        return []
    F = {f["key"]: f for f in ds.get("fields") or []}
    out, seen = [], set()
    for spec in specs:
        if spec.get("scope") != sc:
            continue
        for cid, scopes, fn in CHECKS:
            if sc not in scopes:
                continue
            try:
                got = fn(spec, F, ds)
            except Exception:                                # noqa: BLE001  (one template must never stop the review)
                got = []
            for g in got:
                if (cid, g["key"]) in seen:
                    continue
                seen.add((cid, g["key"]))
                c, mm = g["clause"], g.get("m")
                snip = c["text"]
                if mm is not None and mm.re.search(c["text"]):  # the sentence that says it, not the start of the clause
                    m2 = mm.re.search(c["text"])
                    a = c["text"].rfind(". ", 0, m2.start()) + 2 if c["text"].rfind(". ", 0, m2.start()) >= 0 else 0
                    b = c["text"].find(". ", m2.end())
                    snip = c["text"][a:(b + 1 if b >= 0 else len(c["text"]))]
                out.append({"key": g["key"], "check": cid, "desc": g["desc"], "expected": g.get("expected", ""), "display": TITLES[cid],
                            "severity": g.get("severity", "Major"),
                            "basis": f"Project specification {spec.get('doc_no') or spec.get('filename', '')} §{c['no']} — {TITLES[cid]}",
                            "evidence": [{"doc": spec.get("doc_no") or spec.get("filename", "Specification"), "where": f"§{c['no']}",
                                          "page": c.get("page"), "text": _cut(snip, 300), "document_id": spec.get("document_id")}]})
    return out


def clauses_for(spec: dict, words: str, limit: int = 6) -> list[dict]:
    """The clauses of a specification that speak about a field ('Seat Material' → clauses with 'seat' and 'material'),
    best first — for the review screen's 'Spec' panel."""
    ws = [w for w in re.findall(r"[a-z0-9]{3,}", (words or "").lower()) if w not in ("the", "and", "for", "valve", "type", "max", "min", "nor")]
    if not ws:
        return []
    scored = []
    for c in spec.get("clauses", []):
        t = c["text"].lower()
        s = sum(1 for w in ws if w in t)
        if s:
            scored.append((s + (0.5 if "shall" in t else 0), c))
    scored.sort(key=lambda x: -x[0])
    return [dict(c, score=s) for s, c in scored[:limit] if s >= max(1, len(ws) * 0.5)]
