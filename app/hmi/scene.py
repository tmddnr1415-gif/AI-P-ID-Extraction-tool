"""식별된 P&ID 한 장(`app.dcs.build_sheet` 모델) → HMI 장면 JSON (hotfix110).

장면 꼴은 LOGIC 브랜치 H1회차가 정한 계약 그대로다 (`docs/hmi_handover.md` §3 · 보기 `config/hmi_example_compressor_train.json`):

  equipment[]   {id, sym, x, y, w, h, tag, label, status}
  pipes[]       {id, kind, label, pts[[x,y]…], arrow, dir}
  valves[]      {id, sym, tag, x, y, w, h, rot, state}
  instruments[] {id, func, tag, x, y, value, unit, on, kind, face}
  labels[]      {text, x, y, kind(line|conn), dir}          ← hotfix110 에서 더한 것 (라인 깃발 · 오프페이지 커넥터)
  panels        {trend, key[], control, motor}

H1 과 다른 점 — **자리를 지어내지 않는다** (§9):
  · 배관은 같은 라인 번호 항목을 x 순으로 이은 띠가 아니라, 분석이 그 계기에서 실제로 **탭한 런**과 라인 깃발이 선 런이다
    (`build_sheet` 의 `pipes` — 가로·세로 선분).  흐름 화살은 런 끝에 `TO`/`FROM` 커넥터가 있을 때만.
  · 좌표는 그 장 PDF 좌표를 **한 배율**로 옮긴 것 — 배율은 그 장 계기 버블의 중앙값이 화면 버블(지름 40)과 같게.
    그래서 P&ID 와 같은 배치이고 버블끼리 겹치지 않는다.
  · 기기 심볼은 도면이 인쇄한 이름(설명 후보의 기기 라벨) 자리 위에 선다 — 크기는 실제가 아니다.
  · 값은 데모다 (`value` = 머리글자별 기준값) — 화면이 '시뮬레이션' 이라 적고, LOGIC 창이 붙으면 그 값이 덮는다.

판정 0줄 · 엔진 import 0 (시험이 AST 로 못박는다)."""
from __future__ import annotations

import re
import statistics

BUBBLE = 40.0                 # 화면 버블 지름 (hmi.js drawInstrument 의 r=20)
MARGIN = 70.0
FACE_W, FACE_H, FACE_GAP = 76.0, 34.0, 10.0       # 값 상자 (hmi.js 와 같은 수)

# 계기 머리글자 → 데모 값의 단위와 기준 (H1 scene.py 와 같은 표 — 실제 공정값이 아니다)
UNITS = {"P": ("bar", 50.0), "T": ("°C", 80.0), "L": ("%", 60.0), "F": ("t/h", 120.0), "A": ("ppm", 10.0),
         "Z": ("%", 100.0), "S": ("rpm", 2980.0), "V": ("mm/s", 2.1), "H": ("", 0.0), "X": ("", 0.0)}
# 기기 명사 → 심볼 (H1 scene.py · 범례 EQUIPMENT 어휘)
NOUN_SYM = [("air_cooler", ("AIR COOLER",)), ("compressor", ("COMPRESSOR",)), ("pump", ("PUMP",)),
            ("turbine", ("TURBINE",)), ("fan", ("FAN",)), ("blower", ("BLOWER",)),
            ("heat_exchanger", ("COOLER", "EXCHANGER", "HEATER", "CONDENSER", "ECONOMIZER", "EVAPORATOR", "SUPERHEATER")),
            ("storage_tank", ("TANK",)), ("column", ("COLUMN", "TOWER", "DEAERATOR")),
            ("separator", ("DRUM", "SEPARATOR", "VESSEL", "BOX", "HRSG", "BOILER", "SILENCER"))]
TALL = {"separator", "column", "storage_tank"}
ROTATING = {"compressor", "pump", "fan", "blower", "turbine", "motor"}
# KKS 계통 글자 → 배관 종류 (hotfix109 어댑터의 표를 H1 배관 종류로) — 모르면 process
SVC_BY_SYS = {"LBA": "steam", "LBB": "steam", "LBC": "steam", "LBG": "steam", "LBQ": "steam",
              "LCA": "water", "LCB": "water", "LCH": "water", "LAB": "water", "LAE": "water", "LAC": "water", "LAA": "water",
              "PAB": "cooling", "PCB": "cooling", "PGB": "cooling", "PGA": "cooling", "PAC": "cooling",
              "GHC": "drain", "GHB": "drain", "GMA": "drain", "LCM": "drain",
              "GKB": "fuel", "EKG": "fuel", "EGB": "fuel", "QCA": "chem", "QUP": "chem", "GKC": "air", "QFB": "air"}
SVC_BY_LETTER = {"L": "steam", "P": "cooling", "G": "air", "H": "fuel", "Q": "chem", "N": "water", "W": "water"}
KIND_WORDS = [("cooling", ("COOLING", "CCW", "UTILITY")), ("drain", ("DRAIN", "BLOWDOWN", "WASTE", "VENT")),
              ("steam", ("STEAM",)), ("water", ("WATER", "FEED", "CONDENSATE"))]


def _letters(t):
    return re.sub(r"[^A-Z]", "", str(t or "").upper().split("(")[0])[:4]


def service_of(line_no: str, words: str = "") -> str:
    m = re.match(r"^\d{0,2}([A-Z]{3})", str(line_no or "").upper())
    if m:
        k = SVC_BY_SYS.get(m.group(1)) or SVC_BY_LETTER.get(m.group(1)[0])
        if k:
            return k
    up = f" {words or ''} ".upper()
    for kind, needles in KIND_WORDS:
        if any(n in up for n in needles):
            return kind
    return "process"


def sym_of_noun(noun: str) -> str:
    up = str(noun or "").upper()
    for sym, needles in NOUN_SYM:
        if any(n in up for n in needles):
            return sym
    return "separator"


def valve_sym(body: str, actuator: str, tag: str, tab: str) -> str:
    b, a, t = str(body or "").upper(), str(actuator or "").upper(), str(tag or "").upper()
    if "CHECK" in b:
        return "valve_check"
    if "THREE" in b or "3WAY" in b.replace("-", "").replace(" ", ""):
        return "valve_3way"
    if "MOTOR" in a or tab == "MOV" or "MOV" in b:
        return "valve_control_electric"
    if re.match(r"^\d*[A-Z]*XV", t) or "SOLENOID" in a:
        return "valve_block"
    if "PNEU" in a or "DIAPH" in a or "CYL" in a or tab == "PNEUMATIC":
        return "valve_control_pneumatic"
    return "valve_manual"


def instrument_kind(func: str, lines: int) -> str:
    """버블 가운데 선(ISA 위치 표기)이 있으면 DCS · 아니면 글자로 (H1 hmi_symbols.instrumentKind 와 같은 규칙)."""
    f = _letters(func)
    tail = f[1:]
    if lines and "T" not in tail:
        return "dcs"
    if "C" in tail:
        return "dcs"
    if "T" in tail:
        return "field"
    if tail in ("I", "G"):
        return "local"
    return "field"


def _hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def face_box(x, y, side):
    r = BUBBLE / 2
    if side == "below":
        return [x - FACE_W / 2, y + r + FACE_GAP, x + FACE_W / 2, y + r + FACE_GAP + FACE_H]
    if side == "right":
        return [x + r + 8, y - FACE_H / 2, x + r + 8 + FACE_W, y + FACE_H / 2]
    if side == "left":
        return [x - r - 8 - FACE_W, y - FACE_H / 2, x - r - 8, y + FACE_H / 2]
    return [x - FACE_W / 2, y - r - FACE_GAP - FACE_H, x + FACE_W / 2, y - r - FACE_GAP]


def place_faces(instruments: list, obstacles: list) -> None:
    """값 상자 자리 — 위 → 아래 → 오른쪽 → 왼쪽 중 다른 상자 · 버블 · 기기와 안 겹치는 첫 자리 (다 겹치면 위).
    자리(버블)는 P&ID 가 정한 것이라 옮기지 않는다 — 상자만 고른다."""
    placed = []
    bubbles = [[i["x"] - BUBBLE / 2, i["y"] - BUBBLE / 2, i["x"] + BUBBLE / 2, i["y"] + BUBBLE / 2] for i in instruments]
    for i in sorted(instruments, key=lambda q: (q["y"], q["x"])):
        own = [i["x"] - BUBBLE / 2, i["y"] - BUBBLE / 2, i["x"] + BUBBLE / 2, i["y"] + BUBBLE / 2]
        chosen = "above"
        for side in ("above", "below", "right", "left"):
            b = face_box(i["x"], i["y"], side)
            if any(_hit(b, q) for q in placed) or any(_hit(b, q) for q in bubbles if q != own) or any(_hit(b, q) for q in obstacles):
                continue
            chosen = side
            break
        i["face"] = chosen
        placed.append(face_box(i["x"], i["y"], chosen))


def from_model(model: dict, ov: dict | None = None) -> dict:
    """`build_sheet` 모델 하나 → 장면.  `ov` 는 hotfix109 사람 값(`dcs/<job>/hmi.json` — tags · names · params · trend)."""
    ov = ov or {}
    tags_ov, names_ov = ov.get("tags") or {}, ov.get("names") or {}
    page = str(model.get("page_no") or "")
    insts, valves = model.get("instruments") or [], model.get("valves") or []
    # 배율 — 이 장 계기 버블의 짧은 변 중앙값이 화면 버블 지름과 같게.  계기가 없으면 밸브 몸체로, 그것도 없으면 1.
    sizes = [min(i["rect"][2] - i["rect"][0], i["rect"][3] - i["rect"][1]) for i in insts if i.get("rect")]
    sizes = [s for s in sizes if s > 2]
    if sizes:
        sc = BUBBLE / statistics.median(sizes)
    else:
        vs = [max(v["rect"][2] - v["rect"][0], v["rect"][3] - v["rect"][1]) for v in valves if v.get("rect")]
        sc = 40.0 / statistics.median(vs) if vs else 1.0
    sc = max(0.5, min(4.0, sc))
    # 보이는 창 — 식별된 것 둘레 (종이 전체를 그리면 한구석에 모인다)
    xs, ys = [], []
    for i in insts:
        r = i["rect"]; xs += [r[0], r[2]]; ys += [r[1], r[3]]
    for v in valves:
        r = v["rect"]; xs += [r[0], r[2]]; ys += [r[1], r[3]]
    for p in model.get("pipes") or []:
        s = p["seg"]; xs += [s[0], s[2]]; ys += [s[1], s[3]]
    for e in model.get("equipment") or []:
        r = e["rect"]; xs += [r[0], r[2]]; ys += [r[1] - 60 / sc, r[3]]
    for c in model.get("connectors") or []:
        xs += [c["at"][0]]; ys += [c["at"][1]]
    if xs:
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    else:
        x0, y0, x1, y1 = 0.0, 0.0, float(model.get("width") or 1000), float(model.get("height") or 700)
    pad = (FACE_H + FACE_GAP + BUBBLE) / sc + MARGIN / sc

    def P(x, y):
        return [round(MARGIN + (x - x0 + pad) * sc, 1), round(MARGIN + (y - y0 + pad) * sc, 1)]

    W = round((x1 - x0 + 2 * pad) * sc + 2 * MARGIN)
    H = round((y1 - y0 + 2 * pad) * sc + 2 * MARGIN)
    scene = {"title": model.get("drawing_no") or f"p{page}", "drawing_no": model.get("drawing_no") or "",
             "sheet_title": model.get("title") or "", "page_no": model.get("page_no"),
             "size": [max(W, 600), max(H, 400)], "generated": True, "scale": round(sc, 4),
             "origin": [round(x0 - pad, 1), round(y0 - pad, 1)],
             "basis": "P&ID 식별 결과를 같은 배치로 옮긴 초안 — 배관은 그 계기가 탭한 런 · 화살은 도면의 TO/FROM 이 말할 때만 · "
                      "기기 심볼은 인쇄된 이름 자리(크기는 실제가 아님) · 값은 데모 (LOGIC 창이 붙으면 그 값)",
             "links": {"logic": None, "note": "LOGIC 검토와는 태그(KKS)로 잇는다 — 열린 LOGIC 창이 같은 태그 값을 보낸다"},
             "equipment": [], "pipes": [], "valves": [], "instruments": [], "labels": [],
             "panels": {"trend": None, "key": [], "control": None, "motor": None}}
    # 배관 — 런(선분) 하나가 배관 하나.  종류는 가장 가까운 라인 깃발 → 그 런을 탭한 계기의 라인 → 장의 도면번호 계통
    labels = model.get("line_labels") or []
    sheet_sys = (re.search(r"-\d{2}([A-Z]{3})\d{2}-", str(model.get("drawing_no") or "").upper()) or [None, ""])[1]
    conns = model.get("connectors") or []
    seg_id = {}
    for n, p in enumerate(model.get("pipes") or []):
        s = p["seg"]
        mx, my = (s[0] + s[2]) / 2, (s[1] + s[3]) / 2
        ln, bd = "", 1e18
        for lb in labels:
            r = lb.get("rect")
            if not r:
                continue
            d = (((r[0] + r[2]) / 2 - mx) ** 2 + ((r[1] + r[3]) / 2 - my) ** 2) ** 0.5
            if d < bd:
                bd, ln = d, lb["line_no"]
        if bd > 400:
            ln = ""
            for i in insts:
                if i.get("tap") and [round(c, 1) for c in i["tap"]] == [round(c, 1) for c in s] and i.get("line_no"):
                    ln = i["line_no"]
                    break
        a, b = [s[0], s[1]], [s[2], s[3]]
        flow = 0
        for c in conns:
            dA = ((c["at"][0] - a[0]) ** 2 + (c["at"][1] - a[1]) ** 2) ** 0.5
            dB = ((c["at"][0] - b[0]) ** 2 + (c["at"][1] - b[1]) ** 2) ** 0.5
            if min(dA, dB) > 40:
                continue
            at_b = dB <= dA
            if c.get("dir") == "TO":
                flow = 1 if at_b else -1
            elif c.get("dir") == "FROM":
                flow = -1 if at_b else 1
        pts = [P(*a), P(*b)]
        if flow == -1:
            pts.reverse()
        pid = f"R{n + 1}"
        seg_id[tuple(round(c, 1) for c in s)] = pid
        scene["pipes"].append({"id": pid, "kind": service_of(ln or (f"00{sheet_sys}" if sheet_sys else "")), "label": "",
                               "line": ln, "pts": pts, "arrow": bool(flow), "role": p.get("role") or "",
                               "pid_seg": list(s)})
    for lb in labels:
        r = lb.get("rect")
        if r:
            x, y = P(r[0], r[1])
            scene["labels"].append({"text": f"{lb['line_no']} {lb.get('size') or ''}".strip(), "x": x, "y": round(y - 4, 1), "kind": "line"})
    for c in conns:
        x, y = P(*c["at"])
        scene["labels"].append({"text": f"{'To' if c.get('dir') == 'TO' else 'From' if c.get('dir') == 'FROM' else ''} {c['name']}".strip(),
                                "x": x, "y": round(y - 8, 1), "kind": "conn", "dir": c.get("dir") or ""})
    # 기기 — 인쇄된 이름 자리 위에 심볼
    eq_by_name = {}
    obstacles = []
    for n, e in enumerate(model.get("equipment") or []):
        r = e["rect"]
        sym = sym_of_noun(e.get("noun") or e.get("name"))
        lx0, ly0 = P(r[0], r[1])
        lx1, ly1 = P(r[2], r[3])
        base = max(80.0, min(160.0, (lx1 - lx0)))
        w, h = (base * 0.55, base * 1.0) if sym in TALL else (base, base * 0.7)
        cx = (lx0 + lx1) / 2
        eid = f"EQ-{n + 1:02d}"
        name = names_ov.get(e["name"]) or e["name"]
        eq = {"id": eid, "sym": sym, "x": round(cx - w / 2, 1), "y": round(ly0 - h - 6, 1), "w": round(w, 1), "h": round(h, 1),
              "tag": name, "label": "", "status": "running", "noun": e.get("noun") or "", "orig_name": e["name"],
              "pid_rect": list(r)}
        if sym in ROTATING:
            eq["params"] = {"Current": [None, "A"], "Voltage": [None, "kV"], "Speed": [None, "rpm"], "Power": [None, "MW"]}
        scene["equipment"].append(eq)
        eq_by_name[e["name"]] = eid
        obstacles.append([eq["x"], eq["y"], eq["x"] + eq["w"], eq["y"] + eq["h"] + 40])
    # 밸브 — 몸체 사각형 · 태그 버블 자리의 태그
    for v in valves:
        r = v["rect"]
        cx, cy = P((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
        size = max(28.0, min(56.0, max(r[2] - r[0], r[3] - r[1]) * sc * 1.3))
        vertical = (r[3] - r[1]) > (r[2] - r[0]) * 1.3
        tag = tags_ov.get(v["key"], v.get("tag") or "")
        st = str(v.get("state") or "").upper()
        scene["valves"].append({"id": v["key"], "key": v["key"], "sym": valve_sym(v.get("body"), v.get("actuator"), tag, v.get("tab")),
                                "tag": tag, "x": round(cx - size / 2, 1), "y": round(cy - size / 2, 1), "w": round(size, 1), "h": round(size, 1),
                                "rot": 90 if vertical else 0, "state": "closed" if "CLOS" in st else "open",
                                "body": v.get("body") or "", "actuator": v.get("actuator") or "", "scope": v.get("scope") or "",
                                "pid_rect": list(r), "logic": None})
        obstacles.append([cx - size / 2, cy - size / 2 - 16, cx + size / 2, cy + size / 2 + 14])
    # 계기 — 버블 중심 그대로
    for i in insts:
        r = i["rect"]
        x, y = P((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
        func = _letters(i.get("type")) or "?"
        unit, basev = UNITS.get(func[:1], ("", 0.0))
        on = seg_id.get(tuple(round(c, 1) for c in i["tap"])) if i.get("tap") else None
        if not on and i.get("equip"):
            on = next((eid for nm, eid in eq_by_name.items() if nm == i["equip"] or i["equip"] in nm), None)
        scene["instruments"].append({"id": i["key"], "key": i["key"], "func": func, "tag": tags_ov.get(i["key"], i.get("tag") or ""),
                                     "x": x, "y": y, "value": basev, "unit": unit, "kind": instrument_kind(func, i.get("lines") or 0),
                                     "on": on or "", "scope": i.get("scope") or "", "line": i.get("line_no") or "",
                                     "line_size": i.get("line_size") or "", "loc": i.get("lines") or 0,
                                     "review": bool(i.get("review")), "pid_rect": list(r), "logic": None, "face": "above"})
    place_faces(scene["instruments"], obstacles)
    # 전송기 → 같은 태그의 제어기는 신호선 (H1 규칙 · 태그가 같을 때만 — 지어내지 않는다)
    for ins in scene["instruments"]:
        if ins["kind"] != "dcs" or not ins["tag"]:
            continue
        src = next((j for j in scene["instruments"] if j is not ins and j["kind"] == "field" and j["tag"] == ins["tag"]), None)
        if src:
            scene["pipes"].append({"id": f"S-{ins['id']}", "kind": "signal", "label": "", "pts": [[src["x"], src["y"]], [ins["x"], ins["y"]]], "arrow": True})
    # 패널 — 사람이 고른 것(hotfix109 params · trend) 먼저
    tagged = [i for i in scene["instruments"] if i["tag"]]
    uniq = list({i["tag"]: i for i in tagged}.values())
    chosen = (ov.get("params") or {}).get(page)
    scene["panels"]["key"] = [t for t in (chosen or [i["tag"] for i in uniq[:6]])]
    tr = (ov.get("trend") or {}).get(page)
    if not tr:
        p_ = next((i for i in uniq if i["func"].startswith("P") and i["kind"] == "field"), None) or (uniq[0] if uniq else None)
        tr = p_["tag"] if p_ else ""
    if tr:
        ti = next((i for i in uniq if i["tag"] == tr), None)
        scene["panels"]["trend"] = {"tag": tr, "min": 0, "max": max(10.0, (ti["value"] if ti else 10.0) * 2)}
    ctl = next((i for i in uniq if i["kind"] == "dcs"), None)
    scene["panels"]["control"] = {"tag": ctl["tag"], "mode": "AUTO"} if ctl else None
    mot = next((e for e in scene["equipment"] if e.get("params")), None)
    scene["panels"]["motor"] = mot["id"] if mot else None
    scene["counts"] = {"instruments": len(scene["instruments"]), "tagged": len(tagged), "valves": len(scene["valves"]),
                       "equipment": len(scene["equipment"]),
                       "pipes": len([p for p in scene["pipes"] if p["kind"] != "signal"])}
    return scene
