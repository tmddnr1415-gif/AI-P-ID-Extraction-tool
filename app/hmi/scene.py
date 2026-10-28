"""식별된 P&ID 행 → HMI 장면(JSON).  판정은 하지 않는다 — 분석 결과의 자리·태그·라인을 옮겨 놓을 뿐이다.

장면 모양 (화면 `hmi_scene.js` 와 같은 꼴 · `config/hmi_example_compressor_train.json` 이 보기):
  equipment[]  {id, sym, x, y, w, h, tag, label, status}
  pipes[]      {id, kind(process|discharge|cooling|drain|signal), label, pts[[x,y]…], arrow}
  valves[]     {id, sym, tag, x, y, w, h, rot, state}
  instruments[] {id, func, tag, x, y, value, unit, on, kind}
  panels       {trend, key[], control, motor}

**배관은 실제 경로가 아니다** — 같은 라인 번호의 계기·밸브를 x 순으로 이은 것이고 그렇게 말한다 (`basis`).
좌표는 그 장의 PDF 좌표를 화면 크기로 비례해 옮긴 것이라 사람이 끌어 다듬는다 (저장은 `store.py`).
"""
from __future__ import annotations

import math
import re

W, H = 1400, 800            # 장면 캔버스 (화면이 맞춰 보인다)
MARGIN = 60

# 계기 머리글자 → 데모 값의 단위와 기준 (실제 공정값이 아니다 — 화면이 '시뮬레이션' 이라고 적는다)
UNITS = {"P": ("bar", 50.0), "T": ("°C", 80.0), "L": ("%", 60.0), "F": ("t/h", 120.0), "A": ("ppm", 10.0),
         "Z": ("%", 100.0), "S": ("rpm", 2980.0), "V": ("mm/s", 2.1), "H": ("", 0.0), "X": ("", 0.0)}
# 라인 번호·계통 낱말 → 배관 종류 (낱말이 없으면 공정)
KIND_WORDS = [("cooling", ("COOLING", "CCW", "CW ", "UTILITY")), ("drain", ("DRAIN", "BLOWDOWN", "BD ", "WASTE", "VENT")),
              ("discharge", ("DISCHARGE", "HEADER"))]
# 기기 명사 → 심볼 (describe_candidates 의 equipment.noun · 범례 EQUIPMENT 어휘)
NOUN_SYM = [("compressor", ("COMPRESSOR",)), ("pump", ("PUMP",)), ("turbine", ("TURBINE",)), ("fan", ("FAN",)),
            ("blower", ("BLOWER",)), ("heat_exchanger", ("COOLER", "EXCHANGER", "HEATER", "CONDENSER", "ECONOMIZER", "EVAPORATOR", "SUPERHEATER")),
            ("air_cooler", ("AIR COOLER",)), ("storage_tank", ("TANK",)), ("column", ("COLUMN", "TOWER", "DEAERATOR")),
            ("separator", ("DRUM", "SEPARATOR", "VESSEL", "BOX", "HRSG", "BOILER", "SILENCER"))]
VALVE_SYM = {"MOV": "valve_control_electric", "PNEUMATIC": "valve_control_pneumatic", "BFV": "valve_manual"}
TAG_SEQ_RE = re.compile(r"(\d+)")


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _kind_of(words):
    up = " ".join(w for w in words if w).upper() + " "
    for kind, needles in KIND_WORDS:
        if any(n in up for n in needles):
            return kind
    return "process"


def _sym_of_noun(noun):
    up = (noun or "").upper()
    for sym, needles in NOUN_SYM:
        if any(n in up for n in needles):
            return sym
    return "separator"


def _letters(t):
    """TYPE 에서 머리글자 — `PIT` → `PIT` 그대로 · `MOV(GLOBE)` → `MOV`."""
    return re.sub(r"[^A-Z]", "", (t or "").upper().split("(")[0])[:4]


def build(rows, page, drawing_no="", title=""):
    """rows = 그 장의 식별 행(merged rows · `values` · `rect` · `tab` · `evidence`) · page = {width, height}."""
    # 행(과 그 기기 후보)이 차지하는 범위를 캔버스에 비례해 맞춘다 — 종이 전체를 맞추면 한구석에 작게 모인다.
    rects = [r.get("rect") for r in rows if r.get("rect") and len(r["rect"]) == 4 and not (r.get("deleted") or r.get("removed"))]
    for r in rows:
        for c in ((r.get("evidence") or {}).get("candidates") or []):
            if isinstance(c, dict) and c.get("kind") == "EQUIPMENT" and c.get("rect"):
                rects.append(c["rect"])
    if rects:
        x0, y0 = min(rc[0] for rc in rects), min(rc[1] for rc in rects)
        x1, y1 = max(rc[2] for rc in rects), max(rc[3] for rc in rects)
    else:
        x0, y0, x1, y1 = 0.0, 0.0, _f((page or {}).get("width")) or 1000.0, _f((page or {}).get("height")) or 700.0
    pad = 0.12 * max(x1 - x0, y1 - y0, 1.0)
    x0, y0, x1, y1 = x0 - pad, y0 - pad * 1.6, x1 + pad, y1 + pad      # 위는 값 상자 몫으로 더
    sc = min((W - 2 * MARGIN) / max(x1 - x0, 1.0), (H - 2 * MARGIN) / max(y1 - y0, 1.0))

    def P(x, y):
        return [round(MARGIN + (x - x0) * sc, 1), round(MARGIN + (y - y0) * sc, 1)]

    scene = {"title": title or drawing_no or "P&ID", "drawing_no": drawing_no, "size": [W, H], "generated": True,
             "basis": "P&ID 식별 결과의 자리를 옮겨 그린 초안 — 배관은 라인 번호가 같은 계기를 이은 것이며 실제 경로가 아닙니다. 끌어서 다듬고 저장하세요.",
             "links": {"logic": None, "note": "LOGIC 검토와는 태그(KKS)로 잇는다 — instruments/valves 의 `tag` · `logic` 자리 (추후)"},
             "equipment": [], "pipes": [], "valves": [], "instruments": [],
             "panels": {"trend": None, "key": [], "control": None, "motor": None}}
    seen_tag = {}
    equip_seen = {}
    by_line = {}
    seq = 0
    for r in rows:
        if r.get("deleted") or r.get("removed"):
            continue
        v = r.get("values") or {}
        rc = r.get("rect")
        if not rc or len(rc) != 4:
            continue
        cx, cy = (rc[0] + rc[2]) / 2, (rc[1] + rc[3]) / 2
        x, y = P(cx, cy)
        tab = r.get("tab") or ""
        typ = _letters(v.get("type"))
        tag = (v.get("tag_no") or "").strip()
        seq += 1
        base = tag or f"{typ or tab}-{seq:03d}"
        n = seen_tag.get(base, 0) + 1
        seen_tag[base] = n
        rid = base if n == 1 else f"{base}#{n}"
        line = (v.get("line_no") or "").strip()
        ev = r.get("evidence") or {}
        if tab in VALVE_SYM or (tab == "REVIEW" and (ev.get("tag") or typ in ("MOV", "XV", "PCV", "TCV", "FCV", "LCV", "HV"))):
            sym = VALVE_SYM.get(tab) or ("valve_control_electric" if typ == "MOV" else "valve_control_pneumatic")
            scene["valves"].append({"id": rid, "sym": sym, "tag": tag or base, "x": x - 20, "y": y - 20, "w": 40, "h": 40,
                                    "rot": 0, "state": "open", "key": r.get("key"), "line": line, "pid_rect": list(rc), "logic": None})
            if line:
                by_line.setdefault(line, []).append(("valve", x, y, v))
            continue
        if tab == "REVIEW" and not typ:
            continue
        unit, basev = UNITS.get(typ[:1], ("", 0.0))
        kind = "dcs" if "C" in typ[1:] else ("local" if typ[1:] in ("I", "G") else "field")
        ins = {"id": rid, "func": typ or "?", "tag": tag or base, "x": x, "y": y, "value": basev, "unit": unit,
               "kind": kind, "on": line or "", "key": r.get("key"), "scope": v.get("scope") or "",
               "qty": v.get("qty"), "description": v.get("description") or "", "pid_rect": list(rc), "logic": None}
        scene["instruments"].append(ins)
        if line:
            by_line.setdefault(line, []).append(("inst", x, y, v))
        # 기기 — P&ID 가 인쇄한 기기 라벨과 그 자리 (설명 근거의 기기 후보 · `candidates` 의 EQUIPMENT).  문장이 고른 것을
        # 먼저, 없으면 후보 중 가장 가까운 것.  태그는 도면이 인쇄한 라벨 그대로 (지어내지 않는다).
        sel = ev.get("description_selected") or {}
        cands = [c for c in (ev.get("candidates") or []) if isinstance(c, dict) and c.get("kind") == "EQUIPMENT" and c.get("rect")]
        pick = None
        if sel.get("equipment") and sel.get("distance") is not None:
            pick = next((c for c in cands if _f(c.get("distance"), -1) == _f(sel.get("distance"), -2)), None)
        if pick is None and cands:
            pick = min(cands, key=lambda c: _f(c.get("distance"), 1e9))
        if pick is not None:
            er = pick["rect"]
            key = (pick.get("text") or "", round(er[0]), round(er[1]))
            if key not in equip_seen:
                noun = ((pick.get("equipment") or {}).get("noun")) or (pick.get("text") or "").split(" ")[-1]
                ex0, ey0 = P(er[0], er[1])
                ex1, ey1 = P(er[2], er[3])
                ew, eh = max(70.0, ex1 - ex0), max(70.0, ey1 - ey0)
                eid = f"EQ-{len(equip_seen) + 1:02d}"
                equip_seen[key] = eid
                scene["equipment"].append({"id": eid, "sym": _sym_of_noun(noun), "x": round((ex0 + ex1) / 2 - ew / 2, 1),
                                           "y": round((ey0 + ey1) / 2 - eh / 2, 1), "w": round(ew, 1), "h": round(eh, 1),
                                           "tag": (pick.get("text") or noun).strip(), "label": "", "status": "running",
                                           "noun": noun, "pid_rect": list(er)})
                eq_id = eid
            else:
                eq_id = equip_seen[key]
            if not ins["on"]:
                ins["on"] = eq_id
    # 배관 — 같은 라인 번호의 항목을 x 순으로 (버블 아래 띠로) · 종류는 라인·계통 낱말
    for line, items in by_line.items():
        items.sort(key=lambda it: it[1])
        pts = [[it[1], it[2] + 44] for it in items]
        if len(pts) == 1:
            pts = [[pts[0][0] - 60, pts[0][1]], [pts[0][0] + 60, pts[0][1]]]
        words = [line] + [str(it[3].get("system") or "") for it in items] + [str(it[3].get("description") or "") for it in items]
        size = next((it[3].get("line_size") for it in items if it[3].get("line_size")), "")
        scene["pipes"].append({"id": line, "kind": _kind_of(words), "label": f"{line} {size}".strip(), "pts": pts, "arrow": True})
    # 전송기 → 같은 태그의 제어기 신호선
    byid = {i["tag"]: i for i in scene["instruments"]}
    for i in scene["instruments"]:
        if i["kind"] != "dcs":
            continue
        src = next((j for j in scene["instruments"] if j is not i and j["kind"] == "field" and j["tag"] == i["tag"]), None)
        if src:
            scene["pipes"].append({"id": f"S-{i['id']}", "kind": "signal", "label": "", "pts": [[src["x"], src["y"]], [i["x"], i["y"]]], "arrow": True})
    # 패널 — 압력 전송기를 트렌드로 · 처음 여섯을 Key · 제어기 하나 · 전동 밸브 하나
    pts_ = [i for i in scene["instruments"] if i["func"].startswith("P") and i["kind"] == "field"] or scene["instruments"]
    if pts_:
        scene["panels"]["trend"] = {"tag": pts_[0]["tag"], "min": 0, "max": max(10.0, pts_[0]["value"] * 2)}
    scene["panels"]["key"] = [i["tag"] for i in scene["instruments"][:6]]
    ctl = next((i for i in scene["instruments"] if i["kind"] == "dcs"), None)
    scene["panels"]["control"] = {"tag": ctl["tag"], "mode": "AUTO"} if ctl else None
    mov = next((e for e in scene["equipment"] if e["sym"] in ("compressor", "pump", "fan", "blower", "turbine")), None)
    if mov:
        mov["params"] = {"Current": [156, "A"], "Voltage": [4.5, "kV"], "Speed": [2980, "rpm"], "Power": [1.2, "MW"]}
        scene["panels"]["motor"] = mov["id"]
    scene["counts"] = {"instruments": len(scene["instruments"]), "valves": len(scene["valves"]),
                       "equipment": len(scene["equipment"]), "pipes": len([p for p in scene["pipes"] if p["kind"] != "signal"])}
    return scene
