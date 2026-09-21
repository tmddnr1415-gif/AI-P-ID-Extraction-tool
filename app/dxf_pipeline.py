"""DXF 입력의 판정 — 읽은 사실(`dxf_reader`)을 **기존 행·화면·Excel 이 먹는 결과**로 (55회차).

방법론은 하나다 (§9 · §10).  바뀌는 것은 읽는 재료뿐이다:

  등급   무엇이 있나                        어떻게 읽나
  ----   --------------------------------   -------------------------------------------
  1급    블록 + TYPE·태그 속성               속성 값을 그대로 (역할은 값의 분포에서 유도)
  2급    범례가 계기라고 그린 블록만          블록 사각형 안의 글자 — TYPE 은 ISA 표로, 태그는 모양으로
  기하   블록이 풀린 장 (PDF 임포트)          범례 계기 원 크기의 닫힌 도형 + 안의 글자  (근거 "DXF 기하")

★ 블록 이름 · 레이어 이름을 코드에 적지 않는다.  뜻은 범례 장(SYMBOL & LEGEND)의
  블록 옆 캡션에서, 계기 여부는 블록 정의의 속성 역할에서, 거를 층은 레이어 표의
  off/frozen/noplot 플래그에서 온다.  (`tests/test_dxf.py` 가 AST 로 못박는다.)
★ SCOPE 는 별표 + 그 장 NOTES 정의줄이다 (§10-7 — 속성의 태그로 판정하지 않는다).
  스코프 경계선 블록(좌/우 두 속성)의 값은 **사실로만** 남긴다 (실무 판단 대기).
★ 판정 함수는 PDF 경로의 것을 **부른다** — `pipeline._scope_of` · `_supplier_name` ·
  `type_display` · `detect_valves.deliverable_class` · `tags.assign` · `isa_table.derive`.
"""
from __future__ import annotations

import collections
import re
import time
import types
from pathlib import Path

import pymupdf

from app import pipeline as P
from app.engine import detect_symbols as ds
from app.engine import detect_valves as dv
from app.engine import dxf_reader as R
from app.engine import extract_titleblocks as tb
from app.engine import isa_table
from app.engine import tags as tagsys
from app.engine import derive_layout as dl

INPUT_KIND = "DXF"
GEOMETRY_CODE = "DXF_GEOMETRY_FALLBACK"
OUTSIDE_LEGEND_CODE = "DXF_BLOCK_NOT_IN_LEGEND"
STAR_RE = re.compile(r"^\(?(\*{1,4})\)?$")
_LETTER_STRIP = re.compile(r"[^A-Z()/]")


# --------------------------------------------------------------------------
# 결과에 남길 작은 것들
# --------------------------------------------------------------------------

class _Word:
    """`tags.assign` · `isa_table.derive` 가 읽는 `(Rect, text)` 낱말."""
    __slots__ = ()


def _rects_words(sh) -> list:
    return [(pymupdf.Rect(*w.rect), w.text) for w in R.words(sh) if not w.hidden]


class _ShimPage:
    """`isa_table.derive` 가 요구하는 만큼의 쪽 — 낱말과 범위."""
    def __init__(self, sh, kind):
        self.page_no = sh.no
        self.words = _rects_words(sh)
        self.analysis_scope = True
        self.page_kind = kind
        self.width, self.height = sh.width, sh.height


def _center(r):
    return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)


def _inside(pt, r, pad=0.0):
    return r[0] - pad <= pt[0] <= r[2] + pad and r[1] - pad <= pt[1] <= r[3] + pad


def _overlap(a, b, pad=0.0):
    return not (a[2] + pad < b[0] or b[2] + pad < a[0] or a[3] + pad < b[1] or b[3] + pad < a[1])


# --------------------------------------------------------------------------
# 범례 — 블록 사전
# --------------------------------------------------------------------------

def _headings(sh) -> list:
    """범례 장의 구획 머리말 — **그 장에서 가장 큰 글자**(세 번 이상 인쇄된 크기)."""
    ws = [w for w in R.words(sh) if w.kind == "TEXT" and not w.hidden]
    hs = collections.Counter(round(w.height, 1) for w in ws)
    big = [h for h, n in hs.items() if n >= 3]
    if not big:
        return []
    top = max(big)
    return [w for w in ws if round(w.height, 1) == top]


def _section_of(heads, cx, cy):
    """심볼이 든 구획 — 같은 열(머리말 x 기준 왼쪽 20 · 오른쪽 125)에서 바로 위 머리말."""
    cand = [h for h in heads if h.rect[0] - 20 <= cx <= h.rect[0] + 125 and h.rect[3] <= cy]
    return max(cand, key=lambda h: h.rect[3]).text.upper() if cand else ""


def legend_dictionary(legend_sheets: list) -> dict:
    """범례 장의 블록 ↔ 구획 머리말 ↔ 옆 캡션.  **뜻은 머리말과 캡션이 말한다.**

    캡션은 심볼 중심을 품는 줄에서 오른쪽으로 가장 가까운 글자들이다 (범례는
    심볼 | 캡션 두 열).  구획은 그 장에서 가장 큰 글자로 인쇄된 머리말 아래다.
    """
    out = {}
    for sh in legend_sheets:
        ws = [w for w in R.words(sh) if not w.hidden and w.kind != "FRAME"]
        heads = _headings(sh)
        for s in R.symbols(sh):
            if s.anonymous:
                continue
            x0, y0, x1, y1 = s.rect
            h_ = max(y1 - y0, 1.0)
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            line = [w for w in ws if w.rect[1] - h_ * 0.6 <= cy <= w.rect[3] + h_ * 0.6
                    and w.rect[0] >= x1 - 1 and w.rect[0] <= x1 + 80]
            line.sort(key=lambda w: w.rect[0])
            caption = " ".join(w.text for w in line[:3]).strip()
            sec = _section_of(heads, cx, cy)
            d = out.setdefault(s.block, {"captions": collections.Counter(), "sheets": set(),
                                        "attdefs": [], "geometry": {}, "count": 0,
                                        "sections": collections.Counter(),
                                        "section_captions": collections.defaultdict(collections.Counter)})
            d["count"] += 1
            d["sheets"].add(sh.no)
            d["sections"][sec] += 1
            if caption:
                d["captions"][caption] += 1
                d["section_captions"][sec][caption] += 1
        atts = R.block_attdefs(sh.doc)
        for name, d in out.items():
            if name in atts and not d["attdefs"]:
                d["attdefs"] = list(atts[name])
            if not d["geometry"]:
                d["geometry"] = R.block_geometry(sh.doc, name)
    return out


_VALVE_WORD = "VALVE"
# 액추에이터 캡션 낱말 → 판정값.  범례 ACTUATORS 표가 인쇄하는 낱말이고 PDF 경로의
# `ACT_LETTERS`(글자)와 같은 자리의 어휘다 — 새 판정값을 만들지 않는다.
_ACT_WORDS = (("MOTOR", "MOTOR"), ("ELECTRO-HYDRAULIC", "HYDRAULIC"),
              ("HYDRAULIC", "HYDRAULIC"), ("SOLENOID", "SOLENOID"),
              ("DIAPHRAGM", "PNEUMATIC"), ("PISTON", "PNEUMATIC"),
              ("CYLINDER", "PNEUMATIC"), ("PNEUMATIC", "PNEUMATIC"),
              ("MANUAL", "NONE"), ("HAND", "NONE"))


def _section_kind(sec: str) -> str:
    """구획 머리말 → 종류.  머리말은 그 범례가 인쇄한 낱말이다."""
    if not sec:
        return ""
    if "ACTUATORS" in sec and "SELF" not in sec:
        return "actuator"
    if "VALVE BODIES" in sec:
        return "valve"
    if "STATUS" in sec or "TYPICAL" in sec:
        return ""
    if "VALVES" in sec:
        return "valve"
    if ("INSTRUMENT" in sec or sec.startswith("SENSOR") or "SELF-ACTUATED" in sec
            or sec.startswith("DEVICES")):
        return "instrument"
    if sec.startswith("EQUIPMENT"):
        return "equipment"
    return ""


_KIND_PRIORITY = ("actuator", "valve", "instrument", "equipment")


def classify_blocks(legend: dict, roles: dict) -> dict:
    """블록 → {"kind": instrument|valve|actuator|equipment|other, "body": …, "actuator": …}.

    TYPE·태그 역할 속성을 **선언한 블록은 계기**다 (구획과 무관 — 그것이 1급의 근거).
    나머지는 구획의 **다수결**이고 동점은 액추에이터 > 밸브 > 계기 > 기기.
    계기 구획의 블록은 범례 계기 원과 같은 반지름(±25%)의 원/호를 그려야 계기다 —
    같은 구획에 놓인 갭 표식·다이어프램 실은 원이 없거나 크기가 다르다.
    """
    out = {}
    type_attr = roles.get("type") or set()
    typed = {n for n, d in legend.items() if any(t in type_attr for t in d["attdefs"])}
    radii = [r for n in typed for r in (legend[n]["geometry"].get("radii") or [])]
    bubble_r = collections.Counter(radii).most_common(1)[0][0] if radii else 0.0
    for name, d in legend.items():
        kinds = collections.Counter()
        for sec, n in d["sections"].items():
            k = _section_kind(sec)
            if k:
                kinds[k] += n
        rr = d["geometry"].get("radii") or []
        round_ = bool(bubble_r and any(abs(r - bubble_r) <= 0.25 * bubble_r for r in rr))
        kind, body, act = "other", "", ""
        if name in typed:
            kind = "instrument"
        elif kinds:
            top = max(kinds.values())
            kind = next(k for k in _KIND_PRIORITY if kinds.get(k) == top)
            if kind == "instrument" and not round_:
                kind = "other"
        caps = []
        for sec, c in d["section_captions"].items():
            if _section_kind(sec) == kind:
                caps += [cap for cap, _n in c.most_common()]
        caps += [cap for cap, _n in d["captions"].most_common() if cap not in caps]
        caps.sort(key=lambda c: (len(c.split()) != 1, ))          # 한 낱말 캡션 먼저 (안정 정렬)
        if kind == "valve":
            for cap in caps:
                ws = cap.upper().replace("(", " ").replace(")", " ").replace("/", " ").split()
                if not ws:
                    continue
                if _VALVE_WORD in ws and ws.index(_VALVE_WORD) > 0:
                    body = ws[ws.index(_VALVE_WORD) - 1].strip(".,")
                elif len(ws) == 1:
                    body = ws[0].strip(".,")
                if body:
                    break
        if kind == "actuator":
            joined = " ".join(caps).upper()
            for word, val in _ACT_WORDS:
                if word in joined:
                    act = val
                    break
        out[name] = {"kind": kind, "body": body, "actuator": act,
                     "captions": caps[:4], "sections": dict(d["sections"]),
                     "attdefs": d["attdefs"], "geometry": d["geometry"],
                     "bubble_radius": bubble_r}
    return out


_SUCC_CELL = re.compile(r"^\(\s*\)\s*([A-Z]{1,4})$")


def isa_succeeding_from_cells(isa, legend_sheets: list):
    """★ SUCCEEDING 열의 다른 판 — `( ) X` 칸 한 줄 (UAD 범례 p4 · 55회차).

    `isa_table.derive` 는 AL NOUF1·SADARA·TC2 가 인쇄하는 `TYPICAL SYMBOL` 머리
    줄을 찾는다.  UAD 범례는 그 줄이 없고, 대신 succeeding 글자마다 `( ) AL` ·
    `( ) K` 꼴 칸을 한 줄로 인쇄한다 (50회차가 남긴 *first 25 · succeeding 0* 의
    원인이 이것이다 — 조각 문제가 아니라 **표의 판이 다르다**).

    ⚠ 이 규칙은 `isa_table.derive` 로 옮겨야 한다 (PDF 의 UAD 도 같은 표).  이
    회차는 **PDF 경로 불변**이 게이트라 DXF 쪽에 두었다 — 대기 목록에 적는다.
    """
    if isa is None or getattr(isa, "succeeding", None):
        return isa
    for sh in legend_sheets:
        ws = [w for w in R.words(sh) if not w.hidden and w.kind != "FRAME"]
        cells = [(w, _SUCC_CELL.match(w.text.strip())) for w in ws]
        cells = [(w, m.group(1)) for w, m in cells if m]
        if len(cells) < 3:
            continue
        rows = collections.defaultdict(list)
        for w, letter in cells:
            rows[round((w.rect[1] + w.rect[3]) / 2)].append((w, letter))
        y, best = max(rows.items(), key=lambda kv: len(kv[1]))
        if len(best) < 3:
            continue
        succ = {}
        top = min(w.rect[1] for w, _l in best)
        for w, letter in best:
            cx = (w.rect[0] + w.rect[2]) / 2
            half = (w.rect[2] - w.rect[0]) / 2 + w.height
            words_ = [x.text for x in ws if x.rect[3] <= top and x.rect[3] >= top - w.height * 6
                      and abs((x.rect[0] + x.rect[2]) / 2 - cx) <= half and x.text.isalpha()]
            succ.setdefault(letter, tuple(words_))
            for ch in letter:
                succ.setdefault(ch, tuple(words_))
        return isa_table.IsaTable(first=dict(isa.first), succeeding=succ, page_no=sh.no,
                                  source=isa.source,
                                  note=isa.note + f" · succeeding {len(succ)} from '( ) X' cells on p{sh.no}")
    return isa


# --------------------------------------------------------------------------
# 속성 역할 — 값의 분포에서
# --------------------------------------------------------------------------

def attribute_roles(sheets: list, isa) -> dict:
    """어느 속성 이름이 TYPE 이고 어느 것이 태그인가 — **값이 답한다**.

    태그: 비어 있지 않은 값의 절반 이상이 코드 모양이고, 그 모양이 두 장 이상에서
          되풀이된다 (29회차 규칙).
    TYPE: 절반 이상이 그 문서 ISA 표로 풀리고, **같은 블록이 태그 역할 속성을 함께
          선언**한다 — 범례 p4 의 계기 블록이 ATTDEF 둘(TYPE · 태그)을 한 쌍으로
          갖는 그 구조다.  (스코프 선의 `SCT`·`AG` 도 글자로는 풀리므로 이 조건이
          없으면 선이 계기가 된다 — 실측.)
    """
    vals = collections.defaultdict(list)
    pages = collections.defaultdict(lambda: collections.defaultdict(set))
    siblings = collections.defaultdict(set)        # 속성 이름 → 같은 블록의 다른 속성 이름들
    for sh in sheets:
        if sh.error:
            continue
        for s in R.symbols(sh):
            names = [t for t, v in s.attrs.items()]
            for t, v in s.attrs.items():
                siblings[t].update(n for n in names if n != t)
                if v:
                    vals[t].append(v)
                    if tagsys._is_code(v):
                        pages[t][tagsys.shape(v)].add(sh.no)
    facts, tag_attr = {}, set()
    for t, vs in vals.items():
        n = len(vs)
        shapes = collections.Counter(tagsys.shape(v) for v in vs if tagsys._is_code(v))
        top = shapes.most_common(1)[0] if shapes else ("", 0)
        tag_ok = top[1] / n if n else 0.0
        repeats = len(pages[t].get(top[0], ())) >= 2
        facts[t] = {"n": n, "tag_share": round(tag_ok, 2), "top_shape": top[0],
                    "shape_sheets": len(pages[t].get(top[0], ()))}
        if tag_ok >= 0.5 and repeats:
            tag_attr.add(t)
    # 두 장에 안 걸치는 속성(이름을 바꿔 복사한 블록 — p25 의 다섯)도, 그 값의 모양이
    # **이미 두 장 이상에서 선 태그 체계**와 같으면 태그다 (29회차 규칙의 "체계").
    system = {facts[t]["top_shape"] for t in tag_attr}
    for t, f in facts.items():
        if t not in tag_attr and f["tag_share"] >= 0.5 and f["top_shape"] in system:
            tag_attr.add(t)
    type_attr = set()
    for t, vs in vals.items():
        n = len(vs)
        isa_ok = sum(1 for v in vs if _isa_type(v, isa)) / n
        facts[t]["isa_share"] = round(isa_ok, 2)
        facts[t]["paired_with_tag"] = bool(siblings[t] & tag_attr)
        if isa_ok >= 0.5 and (siblings[t] & tag_attr):
            type_attr.add(t)
    return {"type": type_attr, "tag": tag_attr, "facts": facts}


def _isa_type(v: str, isa) -> str | None:
    """값을 ISA 표로 검증한 TYPE — 경보 수식자(`+ - ,`)는 떼고 본다.  못 풀면 None."""
    if not v or isa is None:
        return None
    head = v.upper().split()[0] if v.strip() else ""
    if any(c.isdigit() for c in head):
        return None
    core = _LETTER_STRIP.sub("", head)
    core = core.replace("(", "").replace(")", "").replace("/", "")
    if not (2 <= len(core) <= 5):
        return None
    try:
        return core if isa.decompose(core) else None
    except Exception:                                      # noqa: BLE001
        return None


# --------------------------------------------------------------------------
# 분석
# --------------------------------------------------------------------------

def analyse(path: Path, progress=None, timings=None, declared_mode: str = None,
            unit_multipliers: dict = None, sheet_numbers: dict = None, **_ignored) -> dict:
    t0 = time.perf_counter()
    log = (timings.log if timings is not None else (lambda m: print(m, flush=True)))

    def say(frac, msg, sheets=None):
        if progress:
            progress(frac, msg, sheets=sheets) if _accepts_sheets(progress) else progress(frac, msg)

    say(0.0, "opening the DXF set")
    sheets, meta = R.open_set(Path(path))
    ok = [s for s in sheets if not s.error]
    log(f"DXF: {len(sheets)} sheets · readable {len(ok)} · order {meta['order_rule']}")

    # ── 타이틀블록 · 장 종류 ─────────────────────────────────────────────
    say(0.05, "reading title blocks", sheets=(0, len(sheets)))
    titles = {}
    shapes = collections.defaultdict(set)
    for sh in ok:
        f = R.title_fields(sh)
        titles[sh.no] = f
        v = f.get("drawing_no") or ""
        if v:
            shapes[_shape(v)].add(sh.no)
    pat = dl._drawing_no_pattern({k: v for k, v in shapes.items()})
    dwg_re = re.compile(pat) if pat else None
    user_sheets = dict(sheet_numbers or {})
    tb_rows = {}
    for sh in sheets:
        f = titles.get(sh.no, {})
        dwg = (f.get("drawing_no") or "").strip()
        if dwg_re is not None and dwg and not dwg_re.match(dwg):
            dwg = ""
        method = "TITLE_TEXT" if dwg else ""
        if not dwg and str(sh.no) in {str(k) for k in user_sheets}:
            dwg = str(user_sheets.get(sh.no) or user_sheets.get(str(sh.no)) or "")
            method = "USER" if dwg else ""
        title = (f.get("title") or "").strip()
        kind = "UNKNOWN" if sh.error else tb.classify_page(title, dwg)
        tb_rows[sh.no] = {
            "page_no": sh.no, "drawing_no": dwg, "drawing_title": title,
            "page_kind": kind, "unit_code": tb.parse_unit_code(dwg) or "",
            "rev": (f.get("rev") or "").strip(), "rev_method": "TEXT" if f.get("rev") else "NONE",
            "rev_confidence": "HIGH" if f.get("rev") else "", "rev_date": "",
            "sheet": (f.get("sheet") or "").strip(), "drawing_no_method": method,
            "issues": [] if dwg else ["drawing_no"], "file": sh.file, "error": sh.error,
        }
    legend_sheets = [sh for sh in ok if tb_rows[sh.no]["page_kind"] == "LEGEND"]
    targets = [sh for sh in ok if tb_rows[sh.no]["page_kind"] == "PID"]
    log(f"DXF: legend sheets {[s.no for s in legend_sheets]} · PID sheets {len(targets)}")

    # ── 범례 — ISA 표 · 블록 사전 · 속성 역할 ────────────────────────────
    say(0.1, "reading the legend")
    isa = None
    try:
        isa = isa_table.derive([_ShimPage(sh, "LEGEND") for sh in legend_sheets], P.CFG)
    except Exception as exc:                               # noqa: BLE001
        log(f"DXF: isa table failed — {type(exc).__name__}: {exc}")
    isa = isa_succeeding_from_cells(isa, legend_sheets)
    isa_ok = isa is not None and getattr(isa, "source", "MISSING") != "MISSING"
    roles = attribute_roles(ok, isa if isa_ok else None)
    legend = legend_dictionary(legend_sheets)
    blocks = classify_blocks(legend, roles)
    rules = ds.ruleset_v3(P.CFG)
    inst_blocks = {n for n, b in blocks.items() if b["kind"] == "instrument"}
    # 범례 밖 블록인데 **범례 계기 원과 같은 반지름**을 그린 것 — p16~p18 의
    # `LOCAL_MOUNTED`·`MOUNTED ON MCP` 가 그렇다 (같은 문서 안의 둘째 체계).
    # 이름이 아니라 블록 정의의 기하로 가르고, 행에는 사유를 단다.
    bubble_r = next((b.get("bubble_radius") for b in blocks.values() if b.get("bubble_radius")), 0.0)
    outside = {}
    if bubble_r:
        for sh in ok:
            for name in {s.block for s in R.symbols(sh) if not s.anonymous}:
                if name in blocks or name in outside:
                    continue
                g = R.block_geometry(sh.doc, name)
                if any(abs(r - bubble_r) <= 0.25 * bubble_r for r in (g.get("radii") or [])):
                    outside[name] = g
    inst_outside = set(outside)
    valve_blocks = {n: b for n, b in blocks.items() if b["kind"] == "valve"}
    act_blocks = {n: b for n, b in blocks.items() if b["kind"] == "actuator"}
    # 범례 계기 원의 크기 — 기하 폴백의 자 (범례가 그린 값 · 코드에 숫자 없음)
    radii = [r for n in inst_blocks for r in (blocks[n]["geometry"].get("radii") or [])]
    bubble_d = 2 * collections.Counter(radii).most_common(1)[0][0] if radii else 0.0
    log(f"DXF: ISA {getattr(isa, 'source', 'MISSING')} · roles type={sorted(roles['type'])[:2]} "
        f"tag={sorted(roles['tag'])[:2]} · legend blocks {len(legend)} · instrument {len(inst_blocks)} "
        f"· valve {len(valve_blocks)} · actuator {len(act_blocks)} · bubble Ø {bubble_d}")

    # ── 승수 — ①범례표 없음 → ②NOTES(미구현) → ③사람 → ④설정 폴백 ─────
    fallback = {str(k): int(v) for k, v in (P.CFG.get("unit_multiplier_fallback") or {}).items()}
    user_mult = {str(k): int(v["value"] if isinstance(v, dict) else v)
                 for k, v in (unit_multipliers or {}).items()}

    # ── 장마다 행 ────────────────────────────────────────────────────────
    rows, layers, unjudged, tiers, breaker, inv = [], {}, [], {}, [], []
    valve_tags = []
    for i, sh in enumerate(sheets):
        inv.append(R.inventory(sh))
        if sh.error or sh not in targets:
            continue
        say(0.1 + 0.8 * i / max(1, len(sheets)), f"reading sheet {sh.no} of {len(sheets)}",
            sheets=(i, len(sheets)))
        meta_ = tb_rows[sh.no]
        unit = meta_["unit_code"]
        factor, undefined, borrowed = None, True, False
        if unit in user_mult:
            factor, undefined, borrowed = user_mult[unit], False, False
            mult_src = "USER"
        elif unit in fallback:
            factor, undefined, borrowed = fallback[unit], False, True
            mult_src = "CONFIG"
        else:
            mult_src = "NONE"
        out = _sheet_rows(sh, meta_, blocks, inst_blocks | inst_outside, valve_blocks, act_blocks, roles,
                          isa if isa_ok else None, rules, bubble_d, factor, undefined,
                          borrowed, mult_src, unit)
        rows.extend(out["rows"]); unjudged.extend(out["unjudged"])
        tiers[sh.no] = out["tier"]; breaker.extend(out["breaker"])
        valve_tags.extend(out["valve_tags"])
        if timings is not None:
            timings.page_done(sh.no)

    # ── 태그 (1급) — 속성이 준 것은 그대로, 나머지는 tags.assign ─────────
    tier_facts = _attach_tags(rows, targets, declared_mode)

    # ── 오버레이 층 ─────────────────────────────────────────────────────
    for r in rows:
        scope = (P.SCOPE_VENDOR if str(r.scope or "").startswith(P.COL_VENDOR) else
                 P.SCOPE_SCT if r.scope == P.COL_SCT else P.SCOPE_INCLUDED)
        layers.setdefault(r.page_no, collections.defaultdict(list))[r.tab].append({
            "key": r.key, "rect": [round(v, 1) for v in r.rect],
            "label": r.type or r.valve_type, "needs_review": bool(r.needs_review),
            "scope": scope, "kind": P.KIND_VALVE if r.evidence.get("body") else P.KIND_INSTRUMENT,
            "row": True, "reason": r.needs_review, "description_needed": r.description_needed})
    for u in unjudged:
        layers.setdefault(u["page_no"], collections.defaultdict(list))["EXCLUDED"].append({
            "key": P._key(u["page_no"], "UNJUDGED", *u["rect"]), "rect": [round(v, 1) for v in u["rect"]],
            "label": u.get("label") or u.get("block") or "?", "needs_review": False,
            "scope": "EXCLUDED", "kind": P.KIND_INSTRUMENT, "row": False, "reason": u["why"]})

    say(0.95, "assembling the result", sheets=(len(sheets), len(sheets)))
    mult_table = {}
    for r in rows:
        q = r.evidence.get("multiplier")
        if q:
            mult_table[q["unit"]] = q["factor"]
    result = {
        "input_kind": INPUT_KIND,
        "pdf": str(path),
        "pages": [{"page_no": sh.no, "width": round(sh.width, 2), "height": round(sh.height, 2),
                   "drawing_no": tb_rows[sh.no]["drawing_no"], "title": tb_rows[sh.no]["drawing_title"],
                   "page_kind": tb_rows[sh.no]["page_kind"],
                   "in_scope": bool(tb_rows[sh.no]["page_kind"] == "PID" and not sh.error),
                   "scope_reason": (sh.error or ("" if tb_rows[sh.no]["page_kind"] == "PID"
                                                 else f"page kind {tb_rows[sh.no]['page_kind']}"))}
                  for sh in sheets],
        "titleblocks": [tb_rows[sh.no] for sh in sheets],
        "rows": [r.as_dict() for r in rows],
        "layers": {str(k): {kk: vv for kk, vv in v.items()} for k, v in layers.items()},
        "multipliers": {"source": "CONFIG_FALLBACK" if mult_table else "NONE",
                        "note": "DXF — 범례 승수표 없음 · 설정 폴백 (§9 ④ · 사람 지정이 이긴다)",
                        "table": dict(sorted(mult_table.items()))},
        "legend": {"dxf_blocks": {"source": "DXF_LEGEND" if legend else "MISSING",
                                  "note": f"legend sheets {[s.no for s in legend_sheets]}",
                                  "values": {n: b["kind"] for n, b in sorted(blocks.items())}},
                   "isa_table": {"source": getattr(isa, "source", "MISSING"),
                                 "note": getattr(isa, "note", ""),
                                 "values": {"first": sorted(getattr(isa, "first", {}) or {}),
                                            "succeeding": sorted(getattr(isa, "succeeding", {}) or {})}
                                 if isa_ok else {}}},
        "glyphs": {"letters": {}},
        "unit_notes": {}, "unit_forms": {}, "typical": {}, "typical_stats": {},
        "face_marks": {}, "signal_groups": [],
        "user_multipliers": {"table": dict(sorted(user_mult.items())), "who": {}},
        "user_sheet_numbers": {"table": {}, "who": {}},
        "legend_profile": {"mode": "dxf", "legend_sheets": [s.no for s in legend_sheets],
                           "measured": True, "compared": False, "uncompared": []},
        "evidence_tier": tier_facts,
        "unjudged_symbols": unjudged,
        "valve_tags": valve_tags,
        "isa_anchors": {"total": 0},
        "dxf": {"order_rule": meta["order_rule"], "skipped_inputs": meta["skipped"],
                "sheets": inv, "tiers": {str(k): v for k, v in tiers.items()},
                "attribute_roles": {"type": sorted(roles["type"]), "tag": sorted(roles["tag"]),
                                    "facts": roles["facts"]},
                "blocks": {n: {k: v for k, v in b.items() if k != "geometry"} for n, b in blocks.items()},
                "bubble_diameter": bubble_d,
                "blocks_outside_legend_round": sorted(outside),
                "scope_breaks": breaker,
                "drawing_no_pattern": pat or ""},
        "description_grades": dict(collections.Counter(r.description_grade for r in rows)),
        "applied_rules": {"layout": {"items": [], "moved": []}},
        "timings": {"total_seconds": round(time.perf_counter() - t0, 2)},
    }
    log(f"DXF: rows {len(rows)} · unjudged {len(unjudged)} · {result['timings']['total_seconds']}s")
    return result


def _accepts_sheets(fn) -> bool:
    try:
        import inspect
        return "sheets" in inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return False


def _shape(v: str) -> str:
    """도면번호 모양 (`derive_layout` 이 쓰는 것과 같은 글자·숫자 달리기)."""
    out, cur, n = [], "", 0
    for seg in v.split("-"):
        parts = []
        k, cnt = None, 0
        for c in seg:
            kk = "D" if c.isdigit() else "L" if c.isalpha() else "A"
            if kk == k:
                cnt += 1
            else:
                if k:
                    parts.append(f"{k}{cnt}")
                k, cnt = kk, 1
        if k:
            parts.append(f"{k}{cnt}")
        # derive_layout 의 모양은 세그먼트마다 한 종류다 — 섞이면 A(영숫자)
        if len(parts) > 1:
            parts = [f"A{len(seg)}"]
        out.append(parts[0] if parts else "A0")
    return "-".join(out)


# --------------------------------------------------------------------------
# 장 하나
# --------------------------------------------------------------------------

def _sheet_rows(sh, meta_, blocks, inst_blocks, valve_blocks, act_blocks, roles, isa, rules,
                bubble_d, factor, undefined, borrowed, mult_src, unit) -> dict:
    syms = [s for s in R.symbols(sh) if not s.hidden]
    ws = [w for w in R.words(sh) if not w.hidden and w.kind != "FRAME"]
    dwg = meta_["drawing_no"]
    rows, unjudged, breaker, valve_tags = [], [], [], []
    type_attr, tag_attr = roles["type"], roles["tag"]

    # 별표 사전 — 그 장 NOTES 정의줄 (`* BY TANK SUPPLIER.`)  PDF 와 같은 규칙
    marks = {}
    for w in ws:
        m = ds.MARK_TEXT_RE.match(w.text)
        if m and len(w.text) > len(m.group(0)) + 1 and P._supplier_name(w.text):
            marks.setdefault(len(m.group(1)), w.text)
    stars = [(w, len(STAR_RE.match(w.text.strip()).group(1))) for w in ws
             if STAR_RE.match(w.text.strip())]

    used_rects = []
    n_attr = n_blk = n_geom = 0

    def scope_for(rect, own_words=()):
        near = [n for w, n in stars if _overlap(w.rect, rect, pad=w.height * 1.2)
                and w not in own_words]
        if not near:
            return P.COL_SCT, {}, []
        n = max(near)
        meaning = marks.get(n, "")
        ev = {"vendor_mark": {"stars": n, "meaning": meaning, "rule": "VENDOR_MARK_TEXT"}}
        hit = ["VENDOR_MARK_TEXT"] if meaning else ["VENDOR_MARK_UNDEFINED"]
        return P._scope_of(types.SimpleNamespace(rules_hit=hit, evidence=ev)), ev, hit

    def qty_and_codes(kind_codes):
        codes, reasons = list(kind_codes), []
        if undefined:
            codes.append("MULTIPLIER_UNDEFINED")
            reasons.append(f"유닛코드 {unit!r} 의 승수를 이 문서 어디에서도 읽지 못했습니다")
            q = None
        else:
            q = int(factor)
            if borrowed:
                codes.append("MULTIPLIER_FROM_CONFIG")
                reasons.append(P._BORROWED_MULTIPLIER % (unit, factor))
        return q, codes, reasons

    def make_row(tab, page_rect, type_, kind_codes, evidence, tag_no="", valve_type=""):
        q, codes, reasons = qty_and_codes(kind_codes)
        scope, sev, shit = scope_for(page_rect, evidence.pop("_own_words", ()))
        if "VENDOR_MARK_UNDEFINED" in shit:
            codes.append("VENDOR_MARK_UNDEFINED")
            reasons.append("별표는 있는데 이 장 NOTES 가 그 별표를 정의하지 않습니다")
        evidence.update(sev)
        evidence["rules_hit"] = list(evidence.get("rules_hit", [])) + shit
        evidence["review_codes"] = codes
        evidence["multiplier"] = {"unit": unit, "factor": factor, "source": mult_src}
        evidence["qty_basis"] = (f"1 symbol x {factor} ({mult_src})" if factor else "1 symbol · 승수 없음")
        evidence["page_no"] = sh.no
        r = P.Row(key=P._key(dwg, sh.no, tab, type_, *[round(v, 1) for v in page_rect]),
                  tab=tab, page_no=sh.no, drawing_no=dwg, origin="DRAWING", type=type_, qty=q,
                  system=meta_["drawing_title"], valve_type=valve_type,
                  vendor_supply=("VENDOR" if scope.startswith(P.COL_VENDOR) else ""),
                  scope=scope, description="", tag_no=tag_no,
                  description_needed=False,
                  description_note="DXF 경로 — Description 은 이 회차에 만들지 않았습니다",
                  description_grade="NONE", remark="",
                  needs_review="; ".join(reasons), rect=tuple(round(v, 1) for v in page_rect),
                  evidence=evidence)
        rows.append(r)
        used_rects.append(page_rect)
        return r

    # ── 밸브 몸체·액추에이터 (블록) ─────────────────────────────────────
    bodies = [s for s in syms if s.block in valve_blocks]
    acts = [s for s in syms if s.block in act_blocks]
    body_rows = {}
    for b in bodies:
        bw = max(b.rect[2] - b.rect[0], b.rect[3] - b.rect[1], 1.0)
        near = [a for a in acts if _overlap(a.rect, b.rect, pad=bw)]
        actuator = "NONE"
        act_ev = ""
        if near:
            a = min(near, key=lambda a: abs(_center(a.rect)[0] - _center(b.rect)[0])
                    + abs(_center(a.rect)[1] - _center(b.rect)[1]))
            letter = next((v for t, v in a.attrs.items() if v and len(v) <= 3 and v.isalpha()), "")
            actuator = dv.ACT_LETTERS.get(letter, "") or act_blocks[a.block]["actuator"] or "UNREAD"
            act_ev = f"{a.block} {'letter ' + letter if letter else ''}".strip()
        body_kind = valve_blocks[b.block]["body"] or "OTHER"
        body_rows[id(b)] = (b, body_kind, actuator, act_ev)

    # ── 계기 · 밸브 태그 버블 (1급 · 속성) ───────────────────────────────
    tag_bubbles = []
    for s in syms:
        tv = next((v for t, v in s.attrs.items() if t in type_attr and v), "")
        if not tv:
            continue
        n_attr += 1
        tagv = next((v for t, v in s.attrs.items() if t in tag_attr and v and v != "-"), "")
        core = _isa_type(tv, isa)
        anchor = tv.split()[0].upper()
        if anchor in rules.valves:
            tag_bubbles.append((s, anchor, tagv))
            valve_tags.append({"page_no": sh.no, "tag": anchor, "rect": list(s.rect)})
            continue
        if core is None:
            unjudged.append({"kind": "INSTRUMENT_TAG", "page_no": sh.no, "label": tv, "block": s.block,
                             "rect": list(s.rect), "center": list(_center(s.rect)),
                             "why": "속성 TYPE 이 이 문서 ISA 표로 풀리지 않음"})
            continue
        if core in rules.not_field:
            unjudged.append({"kind": "INSTRUMENT_TAG", "page_no": sh.no, "label": tv, "block": s.block,
                             "rect": list(s.rect), "center": list(_center(s.rect)),
                             "why": "설정이 FIELD 가 아니라고 정한 낱말 (not_field)"})
            continue
        type_ = rules.type_of(core)
        ev = {"anchor": tv, "tier": 1, "source": "DXF_ATTRIB", "block": s.block,
              "attrs": {k: v for k, v in s.attrs.items() if v}, "rules_hit": ["DXF_BLOCK_ATTRIB"],
              "isa": core, "layer": s.layer}
        make_row(P.TAB_FIELD, s.rect, type_, [], ev, tag_no=tagv)

    # ── 계기 (2급 · 범례 블록 + 안의 글자) ─────────────────────────────
    for s in syms:
        if s.block not in inst_blocks or any(t in type_attr and v for t, v in s.attrs.items()):
            continue
        if any(_overlap(s.rect, u, 0.0) for u in used_rects):
            continue
        inside = [w for w in ws if _inside(_center(w.rect), s.rect, pad=0.5)]
        tv = next((w for w in inside if _isa_type(w.text, isa)), None)
        if tv is None:
            unjudged.append({"kind": "INSTRUMENT_BLOCK", "page_no": sh.no, "label": s.block, "block": s.block,
                             "rect": list(s.rect), "center": list(_center(s.rect)),
                             "why": "범례가 계기로 그린 블록인데 안에 ISA 글자가 없음"})
            continue
        n_blk += 1
        anchor = _isa_type(tv.text, isa)
        if tv.text.split()[0].upper() in rules.valves:
            tag_bubbles.append((s, tv.text.split()[0].upper(),
                                next((w.text for w in inside if tagsys._is_code(w.text)), "")))
            continue
        tagv = next((w.text for w in inside if w is not tv and tagsys._is_code(w.text)), "")
        ev = {"anchor": tv.text, "tier": 2, "source": "DXF_BLOCK_TEXT", "block": s.block,
              "rules_hit": ["DXF_BLOCK_TEXT"], "isa": anchor, "layer": s.layer,
              "_own_words": tuple(inside), "in_legend": s.block in blocks}
        make_row(P.TAB_FIELD, s.rect, rules.type_of(anchor),
                 [] if s.block in blocks else [OUTSIDE_LEGEND_CODE], ev, tag_no=tagv)

    # ── 기하 폴백 — 범례 계기 원 크기의 닫힌 도형 + 안의 글자 ────────────
    if bubble_d > 0:
        for lp in R.loops(sh):
            if lp.hidden:
                continue
            w_ = lp.rect[2] - lp.rect[0]; h_ = lp.rect[3] - lp.rect[1]
            if not (0.75 * bubble_d <= h_ <= 1.35 * bubble_d and 0.75 * bubble_d <= w_ <= 4.5 * bubble_d):
                continue
            if any(_overlap(lp.rect, u, 0.0) for u in used_rects):
                continue
            inside = [w for w in ws if _inside(_center(w.rect), lp.rect, pad=0.3)]
            tv = next((w for w in inside if _isa_type(w.text, isa)), None)
            if tv is None:
                continue
            n_geom += 1
            anchor = _isa_type(tv.text, isa)
            if tv.text.split()[0].upper() in rules.valves:
                continue
            tagv = next((w.text for w in inside if w is not tv and tagsys._is_code(w.text)), "")
            ev = {"anchor": tv.text, "tier": 2, "source": "DXF_GEOMETRY", "loop": lp.kind,
                  "rules_hit": ["DXF_GEOMETRY"], "isa": anchor, "layer": lp.layer,
                  "_own_words": tuple(inside)}
            make_row(P.TAB_FIELD, lp.rect, rules.type_of(anchor),
                     [GEOMETRY_CODE], ev, tag_no=tagv)

    # ── 밸브 행 — 태그 버블은 지시선 한 걸음으로 몸체에 (54회차 규칙) ────
    lines_ = R.lines(sh)
    claimed = set()
    for s, anchor, tagv in tag_bubbles:
        hit = None
        h_ = max(s.rect[3] - s.rect[1], 1.0)
        ends = []
        for a, b, _layer in lines_:
            ina, inb = _inside(a, s.rect, pad=h_ * 0.3), _inside(b, s.rect, pad=h_ * 0.3)
            if ina != inb:
                ends.append(b if ina else a)
        for pt in ends:
            for key, (b, bk, act, aev) in body_rows.items():
                if key in claimed:
                    continue
                pad = min(b.rect[2] - b.rect[0], b.rect[3] - b.rect[1])
                if _inside(pt, b.rect, pad=pad):
                    hit = key; break
            if hit is None:
                for a in acts:
                    pad = min(a.rect[2] - a.rect[0], a.rect[3] - a.rect[1])
                    if _inside(pt, a.rect, pad=pad):
                        cand = [k for k, (b, *_r) in body_rows.items()
                                if k not in claimed and _overlap(a.rect, b.rect, pad=pad)]
                        if cand:
                            hit = cand[0]; break
            if hit is not None:
                break
        if hit is None:
            # 53회차 [B-3] — 몸체를 못 읽은 태그 버블도 행이다.  모양 칸은 비운다.
            ev = {"tag": anchor, "tier": 1, "source": "DXF_ATTRIB", "block": s.block,
                  "rules_hit": ["DXF_BLOCK_ATTRIB"], "body": "", "body_basis": "no leader hit"}
            make_row(P.TAB_REVIEW, s.rect, "", [P._TAGGED_NO_ACTUATOR_CODE], ev, tag_no=tagv)
            continue
        claimed.add(hit)
        b, bk, act, aev = body_rows[hit]
        klass = dv.deliverable_class(types.SimpleNamespace(kind=bk, actuator=act, tag=anchor))
        tab = P._VALVE_TAB.get(klass, P.TAB_REVIEW)
        codes = [] if tab != P.TAB_REVIEW else [P._TAGGED_NO_ACTUATOR_CODE]
        ev = {"tag": anchor, "tier": 1, "source": "DXF_ATTRIB", "block": b.block, "body": bk,
              "body_basis": {"tag_leader": True, "actuator": aev}, "rules_hit": ["DXF_BLOCK"],
              "actuator_rect": list(b.rect)}
        make_row(tab, b.rect, bk, codes, ev, tag_no=tagv, valve_type=act if act != "NONE" else "")
    # 태그 없는 액추에이터 밸브 — PDF 와 같은 규칙 (액추에이터가 있어야 산출물)
    for key, (b, bk, act, aev) in body_rows.items():
        if key in claimed:
            continue
        klass = dv.deliverable_class(types.SimpleNamespace(kind=bk, actuator=act, tag=""))
        if klass == dv.CLASS_EXCLUDED:
            continue
        ev = {"tier": 2, "source": "DXF_BLOCK", "block": b.block, "body": bk,
              "body_basis": {"actuator": aev}, "rules_hit": ["DXF_BLOCK"], "actuator_rect": list(b.rect)}
        make_row(P._VALVE_TAB[klass], b.rect, bk, [], ev, valve_type=act)

    # ── 범례에 없는 블록 — 미판정으로 센다 (18회차 등록 화면) ────────────
    seen = collections.Counter()
    for s in syms:
        if s.anonymous or s.block in blocks or any(_overlap(s.rect, u, 0.0) for u in used_rects):
            continue
        seen[s.block] += 1
        if seen[s.block] <= 3:
            unjudged.append({"kind": "BLOCK", "page_no": sh.no, "label": s.block, "block": s.block,
                             "rect": list(s.rect), "center": list(_center(s.rect)),
                             "why": "범례 장에 없는 블록"})
    # 스코프 경계선 후보 — TYPE·태그 역할이 아닌 속성을 **둘** 가진 블록 (좌/우 값).
    # 이름을 보지 않는다.  판정에 쓰지 않고 사실로만 남긴다 (§10-7).
    for s in syms:
        other = {t: v for t, v in s.attrs.items() if t not in type_attr and t not in tag_attr and v}
        if len(other) == 2 and all(len(v) <= 12 and v.isupper() for v in other.values()):
            breaker.append({"page_no": sh.no, "rect": list(s.rect), "block": s.block,
                            "values": other})

    tier = ("1급" if n_attr and n_attr >= n_blk + n_geom else
            "2급" if n_blk and n_blk >= n_geom else
            "기하" if n_geom else ("1급" if n_attr else "빈 장"))
    return {"rows": rows, "unjudged": unjudged, "breaker": breaker, "valve_tags": valve_tags,
            "tier": {"tier": tier, "attr": n_attr, "block": n_blk, "geometry": n_geom,
                     "pdf_import_share": R.inventory(sh).get("pdf_import_share", 0)}}


def _attach_tags(rows, targets, declared_mode):
    """1급 태그 — 속성이 준 것은 그대로 (`DXF_ATTRIB`), 나머지는 `tags.assign`."""
    items = [(r.page_no, pymupdf.Rect(*r.rect)) for r in rows]
    words_by_page = {sh.no: _rects_words(sh) for sh in targets}
    tag_map, facts = tagsys.assign(items, words_by_page)
    measured = "epc" if facts.get("tier") == 1 or any(r.tag_no for r in rows) else "bid"
    declared = (declared_mode or "").strip().lower() or ""
    effective = declared or measured
    conflict = ""
    if declared and declared != measured:
        conflict = "declared_bid_tags_found" if declared == "bid" else "declared_epc_no_tags"
    n_attr = sum(1 for r in rows if r.tag_no)
    facts.update({"declared": declared, "measured": measured, "effective": effective,
                  "conflict": conflict, "tags_available": len(tag_map) + n_attr,
                  "source": "DXF"})
    if effective != "epc":
        for r in rows:
            r.tag_no = ""
        facts["tagged_rows"] = 0
        return facts
    for i, r in enumerate(rows):
        if r.tag_no:
            r.evidence["tag_no"] = {"value": r.tag_no, "source": "DXF_ATTRIB", "shape": tagsys.shape(r.tag_no)}
            continue
        t = tag_map.get(i)
        if t:
            r.tag_no = t
            r.evidence["tag_no"] = {"value": t, "source": "DRAWING", "shape": tagsys.shape(t),
                                    "rule": facts.get("rule")}
    facts["tagged_rows"] = sum(1 for r in rows if r.tag_no)
    return facts
