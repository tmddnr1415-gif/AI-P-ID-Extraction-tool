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
# hotfix111 — 범례 EQUIPMENT 표 밖에서 기기 이름으로 받는 명사(VALVE · HEADER · BOX — 18회차 어휘) 중 모양이 따로 없는 것.
# 밸브는 밸브 심볼이 이미 그리고 헤더는 배관이다 — 기기 모양을 지어내지 않고 이름만 적는다.
NAME_ONLY = ("VALVE", "HEADER")


def name_only(noun: str) -> bool:
    """이 명사의 기기는 모양 없이 이름만 적는가 (VALVE · HEADER)."""
    return any(w in str(noun or "").upper().split() for w in NAME_ONLY)
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


def sheet_scale(models: list) -> float:
    """배율 — 계기 버블 짧은 변의 중앙값이 화면 버블 지름과 같게 (여러 장이면 그 장들 전부의 중앙값 — 한 시스템은 한 배율).
    계기가 없으면 밸브 몸체로, 그것도 없으면 1."""
    sizes, vs = [], []
    for m in models:
        sizes += [min(i["rect"][2] - i["rect"][0], i["rect"][3] - i["rect"][1]) for i in m.get("instruments") or [] if i.get("rect")]
        vs += [max(v["rect"][2] - v["rect"][0], v["rect"][3] - v["rect"][1]) for v in m.get("valves") or [] if v.get("rect")]
    sizes = [x for x in sizes if x > 2]
    if sizes:
        sc = BUBBLE / statistics.median(sizes)
    else:
        sc = 40.0 / statistics.median(vs) if vs else 1.0
    return max(0.5, min(4.0, sc))


def from_model(model: dict, ov: dict | None = None, scale: float | None = None, prefix: str = "") -> dict:
    """`build_sheet` 모델 하나 → 장면.  `ov` 는 hotfix109 사람 값(`dcs/<job>/hmi.json` — tags · names · params · trend).
    hotfix111 — `scale` 을 주면 그 배율로 (시스템 한 장은 그 장들의 공통 배율) · `prefix` 는 배관 · 기기 id 앞에 (장끼리 겹치지 않게)."""
    ov = ov or {}
    tags_ov, names_ov = ov.get("tags") or {}, ov.get("names") or {}
    page = str(model.get("page_no") or "")
    insts, valves = model.get("instruments") or [], model.get("valves") or []
    sc = float(scale) if scale else sheet_scale([model])
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
        pid = f"{prefix}R{n + 1}"
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
        if name_only(e.get("noun")):
            x, y = P((r[0] + r[2]) / 2, r[1])
            scene["labels"].append({"text": names_ov.get(e["name"]) or e["name"], "x": x, "y": round(y - 4, 1), "kind": "equip"})
            continue
        sym = sym_of_noun(e.get("noun") or e.get("name"))
        lx0, ly0 = P(r[0], r[1])
        lx1, ly1 = P(r[2], r[3])
        base = max(80.0, min(160.0, (lx1 - lx0)))
        w, h = (base * 0.55, base * 1.0) if sym in TALL else (base, base * 0.7)
        cx = (lx0 + lx1) / 2
        eid = f"{prefix}EQ-{n + 1:02d}"
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
    set_panels(scene, ov, page)
    return scene


def set_panels(scene: dict, ov: dict, page: str) -> None:
    """패널 — 사람이 고른 것(hotfix109 params · trend) 먼저.  `page` 는 그 열쇠 (장 번호 · 시스템이면 `sys:<code>`)."""
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
                       "pipes": len([p for p in scene["pipes"] if p["kind"] not in ("signal", "link")])}


# ---------------------------------------------------------------- hotfix111 — 시스템 한 장
TILE_GAP = 160.0              # 장 사이 띠 (화면 px)
TILE_HEAD = 64.0              # 장 머리(도면번호 · 제목) 높이
KEY_RE = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
SERIAL_RE = re.compile(r"^\d{1,4}[A-Z]?$")
SYSCODE_RE = re.compile(r"^\d{0,2}[A-Z]{3}\d{0,3}$")


def system_of(drawing_no: str, page_no=None) -> tuple[str, str]:
    """도면번호 → (시스템 열쇠, 보이는 이름).  **도면번호에서 장 일련번호(마지막 숫자 마디)만 뗀 것**이 시스템이다 —
    `D00P-10LBA10-M05-0001` · `-0002` 는 같은 문서(같은 계통)의 1장 · 2장이다.  KKS 꼴을 외우지 않는다: 마디를 `-` 로 가르고
    마지막 마디가 숫자(뒤 글자 하나까지)일 때만 뗀다.  보이는 이름은 글자 셋을 품은 계통 마디(`10LBA10`)가 있으면 그것.
    도면번호를 못 읽은 장은 혼자 한 시스템 (`p<장>`)."""
    d = re.sub(r"\s+", "", str(drawing_no or "")).upper()
    if not d:
        k = f"p{page_no}"
        return k, k
    parts = [x for x in re.split(r"[-_]", d) if x]
    base = "-".join(parts[:-1]) if len(parts) > 1 and SERIAL_RE.match(parts[-1]) else "-".join(parts)
    key = re.sub(r"\.{2,}", ".", re.sub(r"[^A-Z0-9_.-]", "", base))[:80].strip(".") or f"p{page_no}"
    code = next((x for x in parts[:-1] if SYSCODE_RE.match(x) and len(re.sub(r"\d", "", x)) == 3), "") or key
    return key, code


def common_title(titles: list) -> str:
    """장 제목들의 앞 낱말 공통 부분 (`P&ID FOR HP STEAM SYSTEM (1/2)` · `(2/2)` → `P&ID FOR HP STEAM SYSTEM`).
    공통 부분이 가장 짧은 제목의 절반에 못 미치면(`P&ID FOR` 만 같음) 뜻이 없으므로 제목들을 ` / ` 로 잇는다."""
    ws = [str(t or "").split() for t in titles if t]
    if not ws:
        return ""
    head = []
    for col in zip(*ws):
        if len(set(col)) != 1:
            break
        head.append(col[0])
    if len(head) >= max(2, min(len(w) for w in ws) / 2):
        return " ".join(head)
    return " / ".join(dict.fromkeys(" ".join(w) for w in ws))


def group_systems(models: list) -> list:
    """`build_sheet` 모델들 → 시스템 목록 (도면번호 순 · 장 순)."""
    by = {}
    for m in models:
        k, code = system_of(m.get("drawing_no"), m.get("page_no"))
        g = by.setdefault(k, {"key": k, "code": code, "pages": [], "drawing_nos": [], "titles": []})
        g["pages"].append(int(m["page_no"]))
        g["drawing_nos"].append(m.get("drawing_no") or "")
        g["titles"].append(m.get("title") or "")
    out = []
    for g in by.values():
        g["title"] = common_title(g["titles"])
        out.append(g)
    return sorted(out, key=lambda g: (min(g["pages"]), g["key"]))


def _shift(sc: dict, dx: float, dy: float) -> None:
    for p in sc["pipes"]:
        p["pts"] = [[round(x + dx, 1), round(y + dy, 1)] for x, y in p["pts"]]
    for k in ("equipment", "valves", "instruments", "labels"):
        for o in sc[k]:
            o["x"] = round(o["x"] + dx, 1)
            o["y"] = round(o["y"] + dy, 1)


def _norm(t: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(t or "").upper())


def from_system(models: list, ov: dict | None = None, key: str = "") -> dict:
    """같은 시스템의 장들 → 한 장 (hotfix111).  장마다 `from_model` 을 **공통 배율**로 만들고 장 순서대로 격자에 놓는다 —
    장 안의 배치는 P&ID 그대로이고 장 사이는 띠로 떨어진다(이어 붙이지 않는다 — 도면이 두 장을 어떻게 잇는지는 커넥터가 말한다).
    장 사이 선은 **커넥터 글이 다른 장의 도면번호나 그 장이 인쇄한 기기 이름을 담을 때만** 긋는다 (지어내지 않는다)."""
    ov = ov or {}
    models = sorted(models, key=lambda m: (str(m.get("drawing_no") or ""), int(m["page_no"])))
    sc_k = sheet_scale(models)
    tiles = [from_model(m, ov, scale=sc_k, prefix=f"p{m['page_no']}-") for m in models]
    n = len(tiles)
    cols = max(1, int(round(n ** 0.5 + 0.49)))
    rows = [tiles[i:i + cols] for i in range(0, n, cols)]
    scene = {"title": "", "system": key, "drawing_no": "", "sheet_title": "", "page_no": None, "pages": [int(m["page_no"]) for m in models],
             "generated": True, "scale": round(sc_k, 4), "view": "system",
             "equipment": [], "pipes": [], "valves": [], "instruments": [], "labels": [], "frames": [],
             "panels": {"trend": None, "key": [], "control": None, "motor": None},
             "links": {"logic": None, "note": "LOGIC 검토와는 태그(KKS)로 잇는다 — 열린 LOGIC 창이 같은 태그 값을 보낸다"}}
    # 줌아웃 글자 배율 — 한 장 전체를 화면 폭(약 1800px)에 맞출 때 글자가 읽히도록 장 머리 · 기기 · 기기 이름을 키운다.
    # 기기만 키우고 계기 · 밸브 · 배관은 P&ID 배율 그대로다 (시스템 한 장의 주인공은 기기 — 사용자 요구).
    width0 = max(sum(t["size"][0] for t in row) + TILE_GAP * (len(row) - 1) for row in rows) + 2 * MARGIN if rows else 600
    zt = max(1.0, round(width0 / 1800.0, 2))
    head = round(TILE_HEAD * zt, 1)
    grow = max(1.0, zt * 0.7)
    for t in tiles:
        for e in t["equipment"]:
            cx, bottom = e["x"] + e["w"] / 2, e["y"] + e["h"]
            e["w"], e["h"] = round(e["w"] * grow, 1), round(e["h"] * grow, 1)
            e["x"], e["y"] = round(cx - e["w"] / 2, 1), round(bottom - e["h"], 1)
    y = MARGIN
    width = 0.0
    for row in rows:
        x = MARGIN
        rh = max(t["size"][1] for t in row)
        for t in row:
            w, h = t["size"]
            _shift(t, x, y + head)
            scene["frames"].append({"x": round(x, 1), "y": round(y, 1), "w": float(w), "h": round(h + head, 1), "head": head,
                                    "page_no": t["page_no"], "drawing_no": t["drawing_no"], "title": t["sheet_title"],
                                    "counts": t["counts"]})
            for k in ("equipment", "pipes", "valves", "instruments", "labels"):
                for o in t[k]:
                    o.setdefault("page_no", t["page_no"])
                    scene[k].append(o)
            x += w + TILE_GAP
        width = max(width, x - TILE_GAP + MARGIN)
        y += rh + head + TILE_GAP
    scene["size"] = [round(max(width, 600)), round(max(y - TILE_GAP + MARGIN, 400))]
    scene["zoom_text"] = zt
    # 장 사이 선 — 커넥터 글에 다른 장의 도면번호 · 그 장의 기기 이름이 들어 있을 때만
    frames = {f["page_no"]: f for f in scene["frames"]}
    dwg = {f["page_no"]: _norm(f["drawing_no"]) for f in scene["frames"] if f["drawing_no"]}
    eq_at = {}
    for e in scene["equipment"]:
        nm = _norm(e.get("orig_name") or e.get("tag"))
        if len(nm) >= 6:
            eq_at.setdefault(nm, []).append(e)
    links = 0
    for lb in [l for l in scene["labels"] if l.get("kind") == "conn"]:
        txt = _norm(lb["text"])
        src = lb.get("page_no")
        target = None
        for pno, d in dwg.items():
            if pno != src and d and d in txt:
                f = frames[pno]
                target = (pno, [f["x"] + f["w"] / 2, f["y"] + head / 2], "drawing_no")
                break
        if target is None:
            for nm, es in eq_at.items():
                e = next((q for q in es if q.get("page_no") != src), None)
                if e and nm in txt:
                    target = (e["page_no"], [e["x"] + e["w"] / 2, e["y"] + e["h"] / 2], "equipment")
                    break
        if target is None:
            continue
        a = [lb["x"], lb["y"]]
        pts = [a, target[1]] if lb.get("dir") != "FROM" else [target[1], a]
        links += 1
        scene["pipes"].append({"id": f"LK{links}", "kind": "link", "label": "", "pts": [[round(p[0], 1), round(p[1], 1)] for p in pts],
                               "arrow": lb.get("dir") in ("TO", "FROM"), "from_page": src, "to_page": target[0], "by": target[2]})
    titles = [f["title"] for f in scene["frames"]]
    code = system_of(models[0].get("drawing_no"), models[0]["page_no"])[1] if models else key
    scene["sheet_title"] = common_title(titles)
    scene["title"] = f"{code} — {scene['sheet_title']}" if scene["sheet_title"] else code
    scene["basis"] = (f"시스템 {code} 의 {n}장을 한 장에 — 장마다 P&ID 배치 그대로 · 공통 배율 · 기기는 그 장이 인쇄한 이름 전부 · "
                      f"장 사이 선은 커넥터 글이 다른 장의 도면번호·기기 이름을 담을 때만 ({links}개) · 값은 데모 (LOGIC 창이 붙으면 그 값)")
    set_panels(scene, ov, f"sys:{key}")
    scene["counts"]["sheets"] = n
    scene["counts"]["links"] = links
    return scene
