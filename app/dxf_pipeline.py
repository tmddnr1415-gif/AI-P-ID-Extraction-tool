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
import math
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
# 경보 신호는 계기 행이 아니다 — 버리지 않고 미판정으로 세어 화면에 남긴다.
ALARM_WHY = "경보 신호 — 그 도면 ISA 표가 뒤 글자에 경보 글자를 붙인 태그입니다 (계기 행으로 내지 않습니다)"
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
    # hotfix17 — **상태 기호는 그 밸브다.**  범례의 VALVE STATUS 구획은 밸브를
    # 열림/닫힘으로 칠만 달리해 다시 그리고, 도면은 그 블록을 **그대로 배관에
    # 놓는다** (UAD DXF p19 의 MOV 몸체가 `…(Open)` 상태 블록 — 그래서 지시선이
    # 몸체에 닿고도 "몸체 아님" 이 되어 검토로 갔다).  칠을 뺀 윤곽이 범례의 밸브
    # 블록 **하나의 몸체 종류**와 같을 때만 그 종류를 잇는다 — 여럿이 같으면
    # 고르지 않는다.  이름은 보지 않는다.
    by_outline = collections.defaultdict(set)
    for n, b in out.items():
        o = (b["geometry"] or {}).get("outline")
        if b["kind"] == "valve" and b["body"] and o:
            by_outline[o].add(b["body"])
    for n, b in out.items():
        o = (b["geometry"] or {}).get("outline")
        if (b["kind"] == "other" and o and any("STATUS" in sec for sec in b["sections"])
                and len(by_outline.get(o, ())) == 1):
            b["kind"] = "valve"
            b["body"] = next(iter(by_outline[o]))
            b["body_from"] = "STATUS_OUTLINE"
    return out


def isa_succeeding_from_cells(isa, legend_sheets: list):
    """★ SUCCEEDING 열의 다른 판 — `( ) X` 칸 한 줄 (UAD 범례 p4 · 55회차).

    `isa_table.derive` 는 AL NOUF1·SADARA·TC2 가 인쇄하는 `TYPICAL SYMBOL` 머리
    줄을 찾는다.  UAD 범례는 그 줄이 없고, 대신 succeeding 글자마다 `( ) AL` ·
    `( ) K` 꼴 칸을 한 줄로 인쇄한다 (50회차가 남긴 *first 25 · succeeding 0* 의
    원인이 이것이다 — 조각 문제가 아니라 **표의 판이 다르다**).

    hotfix31 — 읽는 규칙은 `isa_table.succeeding_from_cells` **하나**로 옮겼고
    (PDF 경로의 `derive` 가 같은 함수를 부른다), 여기는 DXF 낱말을 그 모양으로
    넘기는 자리만 남았다.  `derive` 가 이미 칸으로 채운 표는 그대로 돌려준다.
    """
    if isa is None or getattr(isa, "succeeding", None):
        return isa
    for sh in legend_sheets:
        ws = [(pymupdf.Rect(*w.rect), w.text) for w in R.words(sh)
              if not w.hidden and w.kind != "FRAME"]
        succ = isa_table.succeeding_from_cells(ws)
        if not succ:
            continue
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
    # `timings` 는 파이프라인의 `Timings` 이거나 하네스가 넘기는 빈 dict 다 (PDF 경로의
    # `clock = timings or Timings()` 와 같은 관용).  둘 다 받는다.
    log = getattr(timings, "log", None) or (lambda m: print(m, flush=True))

    def say(frac, msg, sheets=None):
        # 진행 콜백은 PDF 경로와 같은 서명이다 — `progress(done, total, message, sheets, plan, drawing)`.
        # (첫 판이 `(frac, msg)` 둘만 넘겨 화면 업로드가 6초 만에 죽었다 — 실측.)
        if progress:
            progress(frac, 1.0, msg, sheets, None, None)

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
    # hotfix74 — 돌발상황 시뮬레이션(`spike/dxf_variants.py`): 범례 없는 묶음 · 전부 깨진 묶음이 **행 0개로
    # 조용히 성공**했다.  PDF 경로와 같은 두 예외로, 같은 자리(분석 앞)에서 사람 말로 멈춘다.
    if not ok:
        bad = "; ".join(f"{sh.file}: {sh.error}" for sh in sheets[:3])
        raise P.NoTextLayer(f"DXF {len(sheets)}개를 하나도 열지 못했습니다 — DXF 가 아니거나 손상됐습니다 ({bad[:300]}).  "
                            f"CAD 에서 DXF 로 다시 내보내 올려 주세요.")
    if not targets:
        raise P.TitleBlockUnreadable(
            f"이 DXF 묶음({len(ok)}장)에서 P&ID 장을 찾지 못했습니다 — 도면번호를 읽은 장 "
            f"{sum(1 for r in tb_rows.values() if r['drawing_no'])}장 · 범례 장 {len(legend_sheets)}장.  "
            f"타이틀블록에 도면번호가 있는 P&ID DXF 를 넣어 주세요.")
    if not legend_sheets:
        raise P.LegendUnavailable(
            f"이 DXF 묶음({len(ok)}장)에 Symbol & Legend 장이 없습니다 — DXF 는 블록의 뜻(계기·밸브)을 범례 장에서 "
            f"읽으므로 범례 DXF 를 함께 넣어 주세요 (제목에 SYMBOL · LEGEND 가 든 장).")
    # 56회차 [G1] — 프로필은 도면이 고른다 (PDF 경로와 같은 함수).
    codes = collections.Counter(r["drawing_no"].split("-")[0]
                                for r in tb_rows.values() if r["drawing_no"])
    profile_info = P._select_profile(codes.most_common(1)[0][0] if codes else "")

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
    # hotfix17 — **모양은 무엇으로 그렸든 같다.**  작도자가 같은 버블을 줄마다 다른
    # 블록으로 그렸고(UAD DXF p19: `555`·`QQ` 는 호, `11` 은 스플라인, `A$C…` 는 타원),
    # 호의 반지름만 보던 판정이 스플라인·타원 버블을 떨어뜨렸다 — 같은 라벨의 한 줄만
    # 식별된 원인.  범례 계기 블록이 그린 **크기**(짧은 변 · 긴 변, 방향 무관)와 같고
    # 곡선을 가진 블록이면 버블 블록이다.  크기는 범례에서 읽고 코드에 숫자가 없다.
    legend_sizes = [tuple(sorted(blocks[n]["geometry"]["size"])) for n in inst_blocks
                    if (blocks[n].get("geometry") or {}).get("size")]
    _CURVES = ("ARC", "CIRCLE", "ELLIPSE", "SPLINE")

    def _bubble_shaped(g) -> bool:
        size = g.get("size")
        if not size or not legend_sizes or not any(k in (g.get("kinds") or {}) for k in _CURVES):
            return False
        a = tuple(sorted(size))
        return any(abs(a[0] - b[0]) <= 0.1 * b[0] and abs(a[1] - b[1]) <= 0.1 * b[1]
                   for b in legend_sizes)

    if bubble_r or legend_sizes:
        for sh in ok:
            for name in {s.block for s in R.symbols(sh) if not s.anonymous}:
                if name in blocks or name in outside:
                    continue
                g = R.block_geometry(sh.doc, name)
                if (bubble_r and any(abs(r - bubble_r) <= 0.25 * bubble_r
                                     for r in (g.get("radii") or []))) or _bubble_shaped(g):
                    outside[name] = g
    inst_outside = set(outside)
    # hotfix14 — **TYPE 역할 속성을 가진 블록은 그 자체로 계기 버블이다.**  문서가
    # 스스로 선언한 것이다 (그 블록 정의가 TYPE · 태그 속성 쌍을 갖는다 — 범례 p4
    # 구조).  값이 비어 있고 글자가 블록 밖 낱말로 따로 적힌 인스턴스도 있어
    # (UAD DXF p21 `MOV 00GHC02AA201`), 속성 경로도 범례 블록 경로도 못 잡았다.
    type_named = set(roles["type"])
    if type_named:
        for sh in ok:
            for s_ in R.symbols(sh):
                if (not s_.anonymous and s_.block not in inst_blocks
                        and any(t in type_named for t in s_.attrs)):
                    inst_outside.add(s_.block)
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
    user_mult, user_mult_note = P.user_multiplier_tables(unit_multipliers)

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
        if hasattr(timings, "page_done"):
            timings.page_done(sh.no)

    # ── hotfix83 — 사용자가 정한 '식별하지 않는 것' (PSV · 제어실 기능 버블) ────
    # 함수는 PDF 경로의 그것 하나다.  DXF 는 버블 가운데 선을 재지 않으므로 (나) 갈래
    # (선 있는 표시·경보)는 여기서 발동하지 않고 (가) 제어 기능 글자만 본다.
    rows, policy_facts = P.apply_policy(rows, isa if isa_ok else None, log=log)

    # ── 태그 (1급) — 속성이 준 것은 그대로, 나머지는 tags.assign ─────────
    tier_facts = _attach_tags(rows, targets, declared_mode)
    # hotfix39 — 태그 문법 · 교차 검증 (함수는 PDF 것 하나).  DXF 는 버블 밖 미판정 낱말을
    # 같은 꼴로 들지 않으므로 태그가 증거인 행은 여기서 만들지 않는다 (인자 빈 목록).
    tag_grammar = P._tag_grammar_pass(rows, [], isa if isa_ok else None, tier_facts, [])

    # ── hotfix33 — 한 라인의 PIT/PI · 게이지 (hotfix31 규칙을 DXF 에도) ─────
    # 함수는 PDF 경로의 그것 **하나**다 (`P._fold_readouts` · 태그 뒤 한 곳).  DXF 는
    # hotfix17 이 `_sheet_rows` 안에서 같은 태그의 기능 표시(`PI` ↔ `PIT`)를 이미
    # `SIGNAL_FUNCTION` 으로 거르므로 여기서 접히는 행은 보통 0 이고, 남는 몫은
    # **표시기만 있는 라인을 게이지로 부르는 것**이다 (`evidence["gauge"]` →
    # `type_display` 가 `PG`·`TG`).  태그 없는 행은 건드리지 않는다.
    readout_facts, folded_readouts = P._fold_readouts(rows, isa if isa_ok else None)
    if folded_readouts:
        rows = [r for r in rows if r.key not in folded_readouts]

    # ── 오버레이 층 ─────────────────────────────────────────────────────
    for r in rows:
        scope = (P.SCOPE_VENDOR if str(r.scope or "").startswith(P.COL_VENDOR) else
                 P.SCOPE_SCT if r.scope == P.COL_SCT else P.SCOPE_INCLUDED)
        layers.setdefault(r.page_no, collections.defaultdict(list))[r.tab].append({
            "key": r.key, "rect": [round(v, 1) for v in r.rect],
            "label": r.type or r.valve_type, "needs_review": bool(r.needs_review),
            "scope": scope, "kind": P.KIND_VALVE if r.evidence.get("body") else P.KIND_INSTRUMENT,
            "row": True, "reason": r.needs_review, "description_needed": r.description_needed})
    # 미판정 심볼은 오버레이 층에 넣지 않는다 — 넣으면 상자는 그려지는데 어느 색 칸에도
    # 안 세어져 33회차 등식(칸 합 = 상자 수)이 깨진다 (첫 캡처 p12: 행 17 · 상자 37).
    # 등록 화면은 `unjudged_symbols` 를 직접 읽는다 (18회차).
    say(0.95, "assembling the result", sheets=(len(sheets), len(sheets)))
    mult_table = {}
    for r in rows:
        q = r.evidence.get("multiplier")
        if q:
            mult_table[q["unit"]] = q["factor"]
    result = {
        "input_kind": INPUT_KIND,
        "profile": profile_info,
        "borrowed": P._borrowed_ledger(profile_info, {"moved": []}),
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
        "user_multipliers": {"table": dict(sorted(user_mult.items())),
                             "who": dict(sorted(user_mult_note.items()))},
        "user_sheet_numbers": {"table": {}, "who": {}},
        "legend_profile": {"mode": "dxf", "legend_sheets": [s.no for s in legend_sheets],
                           "measured": True, "compared": False, "uncompared": []},
        "evidence_tier": tier_facts,
        "tag_grammar": tag_grammar,
        "readouts": readout_facts,
        "policy_excluded": policy_facts,
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
                "drawing_no_pattern": pat or "",
                # hotfix74 — 속성 역할을 못 배웠으면 그 사실을 남긴다 (태그 모양은 두 장 이상에서 되풀이돼야
                # 배운다 — 장이 적은 묶음에서는 행이 크게 준다; 시뮬레이션: 6장 묶음 1행 ↔ 32장 묶음 507행).
                "roles_note": ("" if roles["tag"] and roles["type"] else
                               f"계기 블록의 TYPE·태그 속성을 배우지 못했습니다 — 같은 태그 모양이 두 장 이상에서 되풀이돼야 배웁니다 "
                               f"(P&ID 장 {len(targets)}장).  장이 적으면 계기 행이 크게 줄 수 있습니다 — "
                               f"같은 계통의 DXF 를 함께 넣어 주세요.")},
        "description_grades": dict(collections.Counter(r.description_grade for r in rows)),
        # 화면·저장이 읽는 PDF 결과의 나머지 열쇠 — 이 회차에 값이 없는 것은 **빈 값**으로 둔다
        # (`main.job_review` 가 `engine.get("job_review", [])` 를 돌리므로 None 이면 500).
        "job_review": [], "origins": {}, "equipment": {}, "candidates": {},
        "description_axis": {}, "description_build": {}, "description_scope": {},
        "pipe_trace": {}, "valve_layout": {},
        "applied_rules": {"layout": {"items": [], "moved": []}},
        "timings": {"total_seconds": round(time.perf_counter() - t0, 2)},
    }
    log(f"DXF: rows {len(rows)} · unjudged {len(unjudged)} · {result['timings']['total_seconds']}s")
    return result


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

    def scope_for(rect, _own_words=()):
        # 56회차 — **별표는 그 심볼의 이름이 아니다.**
        #
        # 예전에는 심볼 사각형 안에 든 낱말(`_own_words`)을 별표 후보에서 뺐다.
        # 그 장치는 *자기 라벨(ISA 글자 · 태그 코드)을 남의 표시로 읽지 않기*
        # 위한 것인데, `stars` 는 `STAR_RE`(`*` · `(*)`)만 담으므로 라벨이 섞일
        # 길이 애초에 없다.  그런데 도면은 별표를 **버블 모서리**에 찍고 그
        # 자리는 바깥 사각형 **안**이라(30회차 §10-10 의 반대 방향), 그 장치가
        # 진짜 별표를 삼켰다 — UAD p30 실측으로 `LS` 12행 **전부**가 자기
        # 별표를 잃고 SCT 로 나갔다 (같은 장 `PI` 24행은 별표가 사각형 밖이라
        # VENDOR 였다).  그래서 별표에는 그 장치를 걸지 않는다.
        near = [n for w, n in stars if _overlap(w.rect, rect, pad=w.height * 1.2)]
        if not near:
            return P.COL_SCT, {}, []
        n = max(near)
        meaning = marks.get(n, "")
        ev = {"vendor_mark": {"stars": n, "meaning": meaning, "rule": "VENDOR_MARK_TEXT"}}
        hit = ["VENDOR_MARK_TEXT"] if meaning else ["VENDOR_MARK_UNDEFINED"]
        return P._scope_of(types.SimpleNamespace(rules_hit=hit, evidence=ev)), ev, hit

    def qty_and_codes(kind_codes):
        codes, reasons = list(kind_codes), []
        default = P.unknown_multiplier() if undefined else None
        if undefined and default is not None:
            # hotfix21 — PDF 경로와 같은 규칙 (`pipeline._default_multiplier`)
            codes.append(P.DEFAULT_MULT_CODE)
            reasons.append(P.DEFAULT_MULT_REASON % unit)
            q = default
        elif undefined:
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
        # hotfix83 — 뜻 없는 별표는 사용자 확정으로 그냥 VENDOR (검토 사유 없음)
        evidence.update(sev)
        evidence["rules_hit"] = list(evidence.get("rules_hit", [])) + shit
        evidence["review_codes"] = codes
        evidence["multiplier"] = {"unit": unit, "factor": factor, "source": mult_src}
        evidence["qty_basis"] = (f"1 symbol x {factor} ({mult_src})" if factor else
                                 f"1 symbol x {q} (unit code {unit} — 승수 미상, 규칙 x{q})" if q else
                                 "1 symbol · 승수 없음")
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
        # hotfix14 — **칸 이름이 아니라 값으로 읽는다.**  작도자가 두 속성에 값을
        # 거꾸로 넣은 인스턴스가 있다 (UAD DXF p12: TYPE 칸에 `00EGD21CP501`,
        # 태그 칸에 `PI` — 화면에는 글자 위치대로 제대로 보인다).  칸 이름으로만
        # 읽으면 "TYPE 이 ISA 표로 안 풀린다" 며 버린다.  그 도면의 ISA 표가 TYPE
        # 칸 값을 못 풀고, 그 값이 코드 모양이며, 태그 칸 값을 ISA 표나 밸브·앵커
        # 사전이 풀면 둘을 바꿔 읽는다 — 도면이 적은 두 글자를 그대로 쓴다.
        swapped = False
        if (tagv and _isa_type(tv, isa) is None and tagsys._is_code(tv)
                and tv.split()[0].upper() not in rules.valves
                and tv.split()[0].upper() not in rules.anchors
                and (_isa_type(tagv, isa) is not None
                     or tagv.split()[0].upper() in rules.valves
                     or tagv.split()[0].upper() in rules.anchors)):
            tv, tagv, swapped = tagv, tv, True
        core = _isa_type(tv, isa)
        core_from = "ISA_TABLE" if core else ""
        anchor = tv.split()[0].upper()
        if anchor in rules.valves:
            tag_bubbles.append((s, anchor, tagv))
            valve_tags.append({"page_no": sh.no, "tag": anchor, "rect": list(s.rect)})
            continue
        if core is None and anchor in rules.anchors:
            # 그 도면의 ISA 문자표가 못 푸는 낱말이라도, **TYPE 자리에 인쇄된 그 낱말을
            # 앵커 사전이 알면** 계기다.  낱말을 만드는 것이 아니라 도면이 TYPE 속성에
            # 적어 둔 것을 읽는 것이고, PDF 경로가 같은 사전으로 같은 판정을 한다
            # (UAD 를 PDF 로 읽으면 `RO` 가 행이 된다).  ISA 표를 먼저 묻는 순서는
            # 그대로다 — 그 도면이 스스로 설명한 것이 사전보다 세다 (§9).
            #
            # 사전이 문을 넓히지 않는다는 증거는 실측이다: 이 문서에서 ISA 표가 거부한
            # TYPE 속성 64건 중 사전이 아는 것은 `RO` 8건뿐이고, 펌프 캡션(42) ·
            # ENDCAP(4) · EEE(2) · 태그 문자열(4) 은 그대로 미판정으로 남는다.
            core, core_from = anchor, "ANCHOR_DICT"
        if core is None:
            unjudged.append({"kind": "INSTRUMENT_TAG", "page_no": sh.no, "label": tv, "block": s.block,
                             "rect": list(s.rect), "center": list(_center(s.rect)),
                             "why": "속성 TYPE 이 이 문서 ISA 표로도 앵커 사전으로도 풀리지 않음"})
            continue
        if core in rules.not_field:
            unjudged.append({"kind": "INSTRUMENT_TAG", "page_no": sh.no, "label": tv, "block": s.block,
                             "rect": list(s.rect), "center": list(_center(s.rect)),
                             "why": "설정이 FIELD 가 아니라고 정한 낱말 (not_field)"})
            continue
        if P.is_alarm_tag(core, isa):
            unjudged.append({"kind": "ALARM_SIGNAL", "page_no": sh.no, "label": tv, "block": s.block,
                             "rect": list(s.rect), "center": list(_center(s.rect)),
                             "why": ALARM_WHY})
            continue
        type_ = rules.type_of(core)
        ev = {"anchor": tv, "tier": 1, "source": "DXF_ATTRIB", "block": s.block,
              "attrs": {k: v for k, v in s.attrs.items() if v},
              "rules_hit": ["DXF_BLOCK_ATTRIB"] + (["ANCHOR_FROM_DICT"] if core_from == "ANCHOR_DICT" else [])
                           + (["DXF_ATTRIB_ROLES_BY_VALUE"] if swapped else []),
              "isa": core, "type_source": core_from, "layer": s.layer,
              "attrs_swapped": swapped}
        make_row(P.TAB_FIELD, s.rect, type_, [], ev, tag_no=tagv)

    # ── 계기 (2급 · 범례 블록 + 안의 글자) ─────────────────────────────
    for s in syms:
        if s.block not in inst_blocks or any(t in type_attr and v for t, v in s.attrs.items()):
            continue
        if any(_overlap(s.rect, u, 0.0) for u in used_rects):
            continue
        inside = [w for w in ws if _inside(_center(w.rect), s.rect, pad=0.5)]
        # hotfix17 — 블록 정의 안에 든 글자도 그 버블에 인쇄된 글자다.
        inside += [w for w in R.insert_words(sh, s) if _inside(_center(w.rect), s.rect, pad=0.5)]
        tv = next((w for w in inside if _isa_type(w.text, isa)), None)
        if tv is None:
            # 밸브 태그(`MOV`·`PSV` …)는 ISA 표가 아니라 밸브 사전이 안다 — 1급
            # 속성 경로와 같은 순서로 묻는다.
            tv = next((w for w in inside if w.text.strip()
                       and w.text.split()[0].upper() in rules.valves), None)
        from_dict = False
        if tv is None:
            # hotfix17 — 1급 속성 경로와 **같은 순서**로 묻는다: ISA 표 → 밸브 사전 →
            # 앵커 사전.  UAD p19 의 세로 버블 `RO` 3개는 ISA 표가 못 푸는 낱말이라
            # 옆 줄의 같은 `RO`(속성으로 인쇄된 것)는 행이 되고 이 셋만 빠졌다 —
            # 같은 라벨인데 버블을 그린 방식(속성 ↔ 블록 밖 글자)에 따라 갈렸다.
            tv = next((w for w in inside if w.text.strip()
                       and w.text.split()[0].upper() in rules.anchors), None)
            from_dict = tv is not None
        if tv is None:
            unjudged.append({"kind": "INSTRUMENT_BLOCK", "page_no": sh.no, "label": s.block, "block": s.block,
                             "rect": list(s.rect), "center": list(_center(s.rect)),
                             "why": "범례가 계기로 그린 블록인데 안에 ISA 글자가 없음"})
            continue
        n_blk += 1
        anchor = _isa_type(tv.text, isa) or (tv.text.split()[0].upper() if from_dict else None)
        if from_dict and anchor in rules.not_field:
            unjudged.append({"kind": "INSTRUMENT_BLOCK", "page_no": sh.no, "label": tv.text, "block": s.block,
                             "rect": list(s.rect), "center": list(_center(s.rect)),
                             "why": "설정이 FIELD 가 아니라고 정한 낱말 (not_field)"})
            continue
        if tv.text.split()[0].upper() in rules.valves:
            tag_bubbles.append((s, tv.text.split()[0].upper(),
                                next((w.text for w in inside if tagsys._is_code(w.text)), "")))
            continue
        if P.is_alarm_tag(anchor, isa):
            unjudged.append({"kind": "ALARM_SIGNAL", "page_no": sh.no, "label": tv.text, "block": s.block,
                             "rect": list(s.rect), "center": list(_center(s.rect)), "why": ALARM_WHY})
            continue
        tagv = next((w.text for w in inside if w is not tv and tagsys._is_code(w.text)), "")
        ev = {"anchor": tv.text, "tier": 2, "source": "DXF_BLOCK_TEXT", "block": s.block,
              "rules_hit": ["DXF_BLOCK_TEXT"] + (["ANCHOR_FROM_DICT"] if from_dict else []),
              "isa": anchor, "layer": s.layer,
              "_own_words": tuple(inside), "in_legend": s.block in blocks}
        make_row(P.TAB_FIELD, s.rect, rules.type_of(anchor),
                 [] if s.block in blocks else [OUTSIDE_LEGEND_CODE], ev, tag_no=tagv)

    # ── 기하 폴백 — 범례 계기 원 크기의 닫힌 도형 + 안의 글자 ────────────
    if bubble_d > 0:
        for lp in R.loops(sh):
            if lp.hidden:
                continue
            w_ = lp.rect[2] - lp.rect[0]; h_ = lp.rect[3] - lp.rect[1]
            # ★ 방향을 가정하지 않는다 — **짧은 변**이 범례 계기 원만 하고 긴 변이
            # 그 몇 배 안이면 버블이다.  예전에는 높이를 Ø 로, 폭을 긴 변으로 보아
            # **세로로 선 버블**(8 × 24)이 전부 걸렸다 (UAD p6 에서 9개).
            # 43회차가 밸브 몸체에서 배운 "짧은 변" 과 같은 판단이다.
            short_, long_ = min(w_, h_), max(w_, h_)
            if not (0.75 * bubble_d <= short_ <= 1.35 * bubble_d and long_ <= 4.5 * bubble_d):
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
            if P.is_alarm_tag(anchor, isa):
                unjudged.append({"kind": "ALARM_SIGNAL", "page_no": sh.no, "label": tv.text,
                                 "rect": list(lp.rect), "center": list(_center(lp.rect)), "why": ALARM_WHY})
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
                ends.append((math.dist(a, b), b if ina else a))
        # hotfix14 — **짧은 선부터 본다 · 다른 심볼에 닿으면 거기서 멈춘다.**
        # 버블 모서리를 스치는 계장 신호선도 "테두리를 넘는 선" 이고, 그 먼 끝이
        # 다른 밸브 옆에 닿으면 태그가 남의 밸브로 갔다 (UAD DXF p11: PSV
        # `00EGD52AA191` 의 신호선 끝이 위쪽 게이트 밸브에 닿아 GATE 행이 됐고,
        # 진짜 지시선 6.6 은 안전밸브 심볼로 가고 있었다).  지시선은 버블에서
        # 그 심볼까지의 **한 걸음**이라 가장 짧고, 그 끝에 있는 것이 태그가
        # 이름 붙인 것이다 — 그것이 몸체 어휘에 없는 심볼이면 몸체를 **주지 않는다**
        # (53회차 [B-3] 버블 자리 행).  새 상수 없음: 넉넉함은 그 심볼 자신의 짧은 변.
        ends.sort(key=lambda t: t[0])
        ends = [pt for _len, pt in ends]
        stop, stop_sym = False, None
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
            # 몸체도 액추에이터도 아닌 **다른 심볼**에 닿았다 — 태그가 가리키는 것은
            # 그 심볼이다.  더 긴 선(신호선)으로 넘어가 남의 밸브를 집지 않는다.
            for o in syms:
                if o is s or o.anonymous:
                    continue
                opad = min(o.rect[2] - o.rect[0], o.rect[3] - o.rect[1])
                if _inside(pt, o.rect, pad=opad):
                    stop = True; stop_sym = o; break
            if stop:
                break
        if hit is None:
            # 53회차 [B-3] — 몸체를 못 읽은 태그 버블도 행이다.  모양 칸은 비운다.
            # hotfix17 — 지시선 끝 기호에 **액추에이터 글자**(범례 액추에이터 표의 `M` ·
            # `S` · `E/H` …)가 인쇄돼 있으면 그것은 도면이 말한 액추에이터다 (UAD DXF p19
            # MOV: 지시선 LEADER 끝이 `M` 원).  몸체 종류는 말하지 않으므로 탭은 여전히
            # 검토이고, VALVE TYPE 칸만 채운다 — 없는 몸체를 지어내지 않는다.
            act_letter = ""
            if stop_sym is not None:
                texts = [v for v in stop_sym.attrs.values() if v] + [
                    w.text for w in R.insert_words(sh, stop_sym)]
                act_letter = next((t.strip().upper() for t in texts
                                   if t.strip().upper() in dv.ACT_LETTERS), "")
            act_kind = dv.ACT_LETTERS.get(act_letter, "")
            ev = {"tag": anchor, "tier": 1, "source": "DXF_ATTRIB", "block": s.block,
                  "rules_hit": ["DXF_BLOCK_ATTRIB"] + (["DXF_LEADER_ACTUATOR_LETTER"] if act_kind else []),
                  "body": "", "body_basis": "no leader hit",
                  "actuator_letter": act_letter}
            make_row(P.TAB_REVIEW, s.rect, "", [P._TAGGED_NO_ACTUATOR_CODE], ev, tag_no=tagv,
                     valve_type=act_kind if act_kind not in ("", "UNCLASSIFIED") else "")
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

    # hotfix17 — **같은 태그를 인쇄한 버블 중 전송기가 있으면, 전송(T)도 검출(E)도 아닌
    # 나머지는 그 루프의 기능 표시다** (UAD DXF p19: `FIT 00GHB00CF001` 과 같은 태그의
    # `FIR` — 지시·기록은 DCS 가 하는 일이지 따로 있는 현장 계기가 아니다).  도면이 두
    # 버블에 **같은 태그**를 찍은 것이 근거이고, 글자 뜻은 ISA 규약(두째 글자부터가
    # 기능)을 그대로 쓴다.  경보(`A`)를 빼는 56회차 규칙과 같은 자리이고, 버리지 않고
    # 미판정(`SIGNAL_FUNCTION`)으로 세어 화면에 남긴다.
    by_tag = collections.defaultdict(list)
    for r in rows:
        if r.tab == P.TAB_FIELD and r.tag_no and r.type:
            by_tag[r.tag_no].append(r)
    drop = set()
    for tag, grp in by_tag.items():
        if len(grp) < 2:
            continue
        for r in grp:
            fn = r.type[1:]
            if "T" in fn or "E" in fn:
                continue
            owner = next((o for o in grp if o is not r and o.type[:1] == r.type[:1]
                          and "T" in o.type[1:]), None)
            if owner is None:
                continue
            drop.add(id(r))
            unjudged.append({"kind": "SIGNAL_FUNCTION", "page_no": sh.no, "label": f"{r.type} {tag}",
                             "block": (r.evidence or {}).get("block"), "rect": list(r.rect),
                             "center": list(_center(r.rect)),
                             "why": f"같은 태그 {tag} 의 {owner.type} 가 있는 루프의 기능 표시 "
                                    f"(전송·검출이 아님) — 계기 행으로 내지 않습니다"})
    if drop:
        rows[:] = [r for r in rows if id(r) not in drop]

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
    tag_map, facts = tagsys.assign(items, words_by_page, kinds=[P._tag_kind(r) for r in rows])
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
