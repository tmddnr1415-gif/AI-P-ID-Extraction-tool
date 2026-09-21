"""DXF 입력 — 읽기만 한다 (55회차 · 판정은 `app/dxf_pipeline.py`).

무엇을 읽는가 — 그 문서가 자기 설명서로 들고 온 것을 **그대로**:

  * 장(sheet)   zip 하나 · 폴더 · 개별 .dxf 여러 장.  순서는 파일명 앞 번호
                (없으면 타이틀블록 도면번호 · 그것도 없으면 이름순) — 결과에 적는다.
  * 낱말        TEXT · MTEXT(줄마다) · 블록 속성(ATTRIB) — 표시 좌표(y 아래로) 사각형.
  * 심볼        INSERT — 블록 이름 · 자리 · **글자 없는 기하만의 사각형** · 속성 사전 ·
                층.  (블록 정의의 ATTDEF 자리표시 글자가 228단위 폭이라 글자까지 넣으면
                계기 하나가 시트 4분의 1을 덮는다.)
  * 층          레이어 표가 스스로 "안 그린다" 고 적은 층 — off · frozen · noplot.
                **이름으로 거르지 않는다** (§9 · `REV.*` 를 코드에 적지 않는다).
  * 닫힌 도형   CIRCLE · 닫힌 LWPOLYLINE · ARC — 블록이 풀린 장(PDF 임포트)의 기하 폴백용.
  * 타이틀블록  시트를 덮는 블록(프레임) 정의 안의 글자와 모델스페이스 글자 — 캡션
                (`PROJECT DWG NO.` · `REV.` · `SHEET`) 아래 칸을 읽는다 (§9 ③).

좌표계: DXF 는 y 가 위로 자란다.  화면·행·태그 짝짓기가 전부 PDF 와 같은
**y 아래** 사각형을 쓰므로, 여기서 한 번만 뒤집는다 (`Sheet.to_page`).
33·41·54회차가 회전 좌표로 세 번 틀렸다 — 변환은 **이 한 곳**에만 있다.
"""
from __future__ import annotations

import collections
import dataclasses
import io
import re
import zipfile
from pathlib import Path

import ezdxf
from ezdxf import bbox as _bbox
from ezdxf import recover

DXF_EXT = ".dxf"
LEADING_NO = re.compile(r"^\s*(\d+)\s*\.")
# 타이틀블록 캡션 — 이 문서가 **인쇄한** 낱말이다 (범례 머리말을 찾는 것과 같은
# 방식).  다른 회사 양식이 다른 캡션을 쓰면 config 로 늘린다 (27회차 `qty_note` 와
# 같은 자리) — 코드에 좌표는 없다.
TITLE_CAPTIONS = {
    "drawing_no": ("PROJECT DWG NO.", "DWG NO.", "DRAWING NO."),
    "rev": ("REV.", "REV"),
    "sheet": ("SHEET",),
    "title": ("DRAWING TITLE",),
}
TEXT_KINDS = ("TEXT", "MTEXT", "ATTRIB")


@dataclasses.dataclass
class Word:
    rect: tuple            # (x0, y0, x1, y1) 표시 좌표 · y 아래
    text: str
    layer: str
    kind: str              # TEXT | MTEXT | ATTRIB | ATTDEF(풀린 속성) | FRAME (프레임 블록 정의 안)
    height: float
    hidden: bool = False   # 그 층이 off/frozen/noplot


@dataclasses.dataclass
class Symbol:
    block: str
    rect: tuple            # 글자 없는 기하만의 사각형 (표시 좌표)
    full_rect: tuple       # 글자까지 넣은 사각형
    layer: str
    attrs: dict            # 속성 태그 이름 → 값 (빈 값 포함)
    rotation: float
    hidden: bool = False
    anonymous: bool = False


@dataclasses.dataclass
class Loop:
    rect: tuple
    kind: str              # CIRCLE | POLY | ARC
    layer: str
    points: int = 0
    hidden: bool = False


@dataclasses.dataclass
class Sheet:
    no: int                # 장 번호 (1부터 · 정렬 뒤)
    order_key: str         # 어떻게 정렬됐나
    file: str
    doc: object = None
    msp: object = None
    version: str = ""
    audit_errors: int = 0
    error: str = ""
    extents: tuple = (0.0, 0.0, 0.0, 0.0)   # (minx, miny, maxx, maxy) 모델 좌표
    hidden_layers: set = dataclasses.field(default_factory=set)
    _cache: dict = dataclasses.field(default_factory=dict)

    @property
    def width(self) -> float:
        return self.extents[2] - self.extents[0]

    @property
    def height(self) -> float:
        return self.extents[3] - self.extents[1]

    def to_page(self, x: float, y: float) -> tuple:
        """모델 좌표 → 표시 좌표 (y 아래).  **뒤집는 곳은 여기 하나다.**"""
        return (x - self.extents[0], self.extents[3] - y)

    def rect_of(self, ext) -> tuple:
        x0, y0 = self.to_page(ext.extmin.x, ext.extmax.y)
        x1, y1 = self.to_page(ext.extmax.x, ext.extmin.y)
        return (round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2))


# --------------------------------------------------------------------------
# 입력 — zip · 폴더 · 개별 파일
# --------------------------------------------------------------------------

def is_dxf_input(path: Path) -> bool:
    p = Path(path)
    if p.is_dir():
        return any(p.rglob(f"*{DXF_EXT}")) or any(p.rglob("*.DXF"))
    suf = p.suffix.lower()
    if suf == DXF_EXT:
        return True
    if suf == ".zip" and p.exists():
        try:
            with zipfile.ZipFile(p) as z:
                return any(n.lower().endswith(DXF_EXT) for n in z.namelist())
        except zipfile.BadZipFile:
            return False
    return False


def list_inputs(path: Path) -> tuple:
    """`(dxf 목록 [(이름, 바이트)], 건너뛴 이름 목록)`.  zip 은 하위 폴더까지."""
    p = Path(path)
    got, skipped = [], []
    if p.is_dir():
        for f in sorted(p.rglob("*")):
            if f.is_file():
                if f.suffix.lower() == DXF_EXT:
                    got.append((f.name, f.read_bytes()))
                else:
                    skipped.append(f.name)
    elif p.suffix.lower() == ".zip":
        with zipfile.ZipFile(p) as z:
            for info in z.infolist():
                if info.is_dir():
                    continue
                name = Path(info.filename).name
                if name.lower().endswith(DXF_EXT):
                    got.append((name, z.read(info)))
                else:
                    skipped.append(info.filename)
    else:
        got.append((p.name, p.read_bytes()))
    return got, skipped


def _order(name: str) -> tuple:
    m = LEADING_NO.match(name)
    return (0, int(m.group(1)), name) if m else (1, 0, name)


def open_set(path: Path) -> tuple:
    """장 목록.  **한 장이 실패해도 나머지는 계속한다** — 실패 사유는 그 장에 붙는다."""
    items, skipped = list_inputs(path)
    numbered = sum(1 for n, _ in items if LEADING_NO.match(n))
    if numbered == len(items) and items:
        rule = "파일명 앞 번호"
    elif numbered:
        rule = "파일명 앞 번호 (번호 없는 것은 뒤에 이름순)"
    else:
        rule = "이름순 (파일명에 번호가 없다)"
    sheets = []
    for i, (name, raw) in enumerate(sorted(items, key=lambda it: _order(it[0])), 1):
        sh = Sheet(no=i, order_key=rule, file=name)
        try:
            doc, auditor = recover.read(io.BytesIO(raw))
            sh.doc, sh.msp = doc, doc.modelspace()
            sh.version = doc.dxfversion
            sh.audit_errors = len(auditor.errors)
            sh.hidden_layers = hidden_layers(doc)
            sh.extents = _extents(sh)
        except Exception as exc:                          # noqa: BLE001
            sh.error = f"{type(exc).__name__}: {exc}"
        sheets.append(sh)
    return sheets, {"order_rule": rule, "skipped": skipped}


def hidden_layers(doc) -> set:
    """레이어 표가 스스로 '안 그린다' 고 적은 층 — off · frozen · plot=0."""
    out = set()
    for layer in doc.layers:
        try:
            if layer.is_off() or layer.is_frozen() or not layer.dxf.plot:
                out.add(layer.dxf.name)
        except Exception:                                  # noqa: BLE001
            continue
    return out


def _extents(sh: Sheet) -> tuple:
    """장의 범위.  시트를 덮는 프레임 블록이 있으면 그것이 종이다."""
    frame = frame_inserts(sh)
    if frame:
        e = _bbox.extents(frame, fast=True)
    else:
        e = _bbox.extents(sh.msp, fast=True)
    if not e.has_data:
        return (0.0, 0.0, 1.0, 1.0)
    return (float(e.extmin.x), float(e.extmin.y), float(e.extmax.x), float(e.extmax.y))


def frame_inserts(sh: Sheet) -> list:
    """종이 틀(타이틀블록을 품는 블록) — 그 장에서 **가장 큰 INSERT**.

    모델 범위의 80% 로 두면 틀 밖에 흘린 도형(p17·p18 은 틀 왼쪽 171 단위 · p21·p25
    는 4배 너비)이 있는 장에서 틀을 놓쳐 타이틀블록을 못 읽는다 (실측 6장).  틀은
    언제나 그 장에서 가장 큰 블록이므로 "가장 큰 것 하나" 로 가른다.
    """
    if "frame" in sh._cache:
        return sh._cache["frame"]
    whole = _bbox.extents(sh.msp, fast=True)
    out = []
    if whole.has_data:
        area = max(whole.size.x * whole.size.y, 1e-9)
        best, best_area = None, 0.0
        for e in sh.msp.query("INSERT"):
            try:
                ext = _bbox.extents([e], fast=True)
            except Exception:                              # noqa: BLE001
                continue
            if not ext.has_data:
                continue
            a = ext.size.x * ext.size.y
            if a > best_area:
                best, best_area = e, a
        # 모델 범위와의 비로 가르지 않는다 — 틀 밖에 흘린 도형이 4배 너비를 만드는
        # 장(p21·p25)이 있다.  종이 크기 이상(두 변 200 단위 이상)인 가장 큰 블록이 틀이다.
        if best is not None and min(_bbox.extents([best], fast=True).size.x,
                                    _bbox.extents([best], fast=True).size.y) >= 200:
            out.append(best)
    sh._cache["frame"] = out
    return out


# --------------------------------------------------------------------------
# 낱말
# --------------------------------------------------------------------------

def _text_rect(sh: Sheet, e, height: float, text: str) -> tuple:
    """글자 사각형 추정 — 정렬점을 존중한다.  폭은 글자 수 × 높이 × 0.75."""
    w = max(len(text), 1) * height * 0.75
    h = height
    halign = int(getattr(e.dxf, "halign", 0) or 0)
    valign = int(getattr(e.dxf, "valign", 0) or 0)
    if e.dxftype() == "MTEXT":
        x, y = e.dxf.insert.x, e.dxf.insert.y
        att = int(getattr(e.dxf, "attachment_point", 1) or 1)
        col = (att - 1) % 3
        row = (att - 1) // 3
        x0 = x - (w / 2 if col == 1 else w if col == 2 else 0)
        y1 = y + (h / 2 if row == 1 else h if row == 2 else 0)
        return sh.rect_of(_Ext(x0, y1 - h, x0 + w, y1))
    ap = getattr(e.dxf, "align_point", None)
    if halign in (1, 2, 4) and ap is not None and (ap.x or ap.y):
        x, y = ap.x, ap.y
        x0 = x - (w / 2 if halign in (1, 4) else w)
        y0 = y - (h / 2 if valign == 2 or halign == 4 else 0)
    else:
        x0, y0 = e.dxf.insert.x, e.dxf.insert.y
        if valign == 2:
            y0 -= h / 2
        elif valign == 3:
            y0 -= h
    return sh.rect_of(_Ext(x0, y0, x0 + w, y0 + h))


class _Ext:
    """`bbox.extents` 결과와 같은 얼굴의 작은 상자."""
    class _P:
        def __init__(self, x, y): self.x, self.y = x, y

    def __init__(self, x0, y0, x1, y1):
        self.extmin = self._P(min(x0, x1), min(y0, y1))
        self.extmax = self._P(max(x0, x1), max(y0, y1))


def words(sh: Sheet) -> list:
    """TEXT · MTEXT(줄마다) · ATTRIB · 프레임 블록 정의 안의 글자."""
    if "words" in sh._cache:
        return sh._cache["words"]
    out = []
    hidden = sh.hidden_layers
    for e in sh.msp:
        t = e.dxftype()
        if t == "TEXT":
            s = (e.dxf.text or "").strip()
            if s:
                out.append(Word(_text_rect(sh, e, float(e.dxf.height or 1.0), s), s,
                                e.dxf.layer, "TEXT", float(e.dxf.height or 1.0),
                                e.dxf.layer in hidden))
        elif t == "MTEXT":
            h = float(e.dxf.char_height or 1.0)
            lines = [ln.strip() for ln in e.plain_text().splitlines() if ln.strip()]
            for i, ln in enumerate(lines):
                r = _text_rect(sh, e, h, ln)
                dy = i * h * 1.4
                out.append(Word((r[0], r[1] + dy, r[2], r[3] + dy), ln, e.dxf.layer,
                                "MTEXT", h, e.dxf.layer in hidden))
        elif t == "INSERT":
            for a in e.attribs:
                s = (a.dxf.text or "").strip()
                if s:
                    out.append(Word(_text_rect(sh, a, float(a.dxf.height or 1.0), s), s,
                                    a.dxf.layer, "ATTRIB", float(a.dxf.height or 1.0),
                                    a.dxf.layer in hidden))
        elif t == "ATTDEF":
            # 모델스페이스의 ATTDEF 는 **풀린(EXPLODE) 속성**이다 — AutoCAD 는 그 자리에
            # 태그 이름을 그린다 (p11 에 317개 · p21 의 `PDIT`·`00GHC13CP001A`).  보이는
            # 글자가 곧 태그 이름이므로 그것을 낱말로 읽는다.  값(`text`)은 기본값이라
            # 보지 않는다.
            s = (e.dxf.tag or "").strip()
            if s:
                out.append(Word(_text_rect(sh, e, float(e.dxf.height or 1.0), s), s,
                                e.dxf.layer, "ATTDEF", float(e.dxf.height or 1.0),
                                e.dxf.layer in hidden))
    # 프레임 블록 정의 안의 글자 (타이틀블록) — 삽입 변환을 거쳐 표시 좌표로
    for ins in frame_inserts(sh):
        try:
            for v in ins.virtual_entities():
                if v.dxftype() == "TEXT":
                    s = (v.dxf.text or "").strip()
                    if s:
                        out.append(Word(_text_rect(sh, v, float(v.dxf.height or 1.0), s), s,
                                        v.dxf.layer, "FRAME", float(v.dxf.height or 1.0)))
                elif v.dxftype() == "MTEXT":
                    s = " ".join(v.plain_text().split())
                    if s:
                        out.append(Word(_text_rect(sh, v, float(v.dxf.char_height or 1.0), s),
                                        s, v.dxf.layer, "FRAME", float(v.dxf.char_height or 1.0)))
        except Exception:                                  # noqa: BLE001
            continue
    sh._cache["words"] = out
    return out


# --------------------------------------------------------------------------
# 심볼 (INSERT)
# --------------------------------------------------------------------------

_TEXTY = ("TEXT", "MTEXT", "ATTRIB", "ATTDEF")


def symbols(sh: Sheet) -> list:
    if "symbols" in sh._cache:
        return sh._cache["symbols"]
    out = []
    frames = {id(e) for e in frame_inserts(sh)}
    hidden = sh.hidden_layers
    for e in sh.msp.query("INSERT"):
        if id(e) in frames:
            continue
        name = e.dxf.name
        try:
            full = _bbox.extents([e], fast=True)
        except Exception:                                  # noqa: BLE001
            continue
        geom = None
        try:
            parts = [v for v in e.virtual_entities() if v.dxftype() not in _TEXTY]
            if parts:
                geom = _bbox.extents(parts, fast=True)
        except Exception:                                  # noqa: BLE001
            geom = None
        if geom is None or not geom.has_data:
            geom = full
        if not full.has_data:
            continue
        out.append(Symbol(
            block=name, rect=sh.rect_of(geom), full_rect=sh.rect_of(full),
            layer=e.dxf.layer,
            attrs={a.dxf.tag: (a.dxf.text or "").strip() for a in e.attribs},
            rotation=float(e.dxf.rotation or 0.0),
            hidden=e.dxf.layer in hidden, anonymous=name.startswith("*")))
    sh._cache["symbols"] = out
    return out


def block_attdefs(doc) -> dict:
    """블록 정의 → ATTDEF 태그 이름 목록 (그 블록이 '어떤 칸을 갖는가' 의 선언)."""
    out = {}
    for b in doc.blocks:
        if b.name.startswith("*"):
            continue
        tags = [x.dxf.tag for x in b if x.dxftype() == "ATTDEF"]
        if tags:
            out[b.name] = tags
    return out


def block_geometry(doc, name: str) -> dict:
    """블록 정의의 기하 요약 — 원/호 반지름 · 글자 없는 크기."""
    b = doc.blocks.get(name)
    if b is None:
        return {}
    radii = [round(float(x.dxf.radius), 3) for x in b if x.dxftype() in ("CIRCLE", "ARC")]
    parts = [x for x in b if x.dxftype() not in _TEXTY]
    size = None
    if parts:
        try:
            ext = _bbox.extents(parts, fast=True)
            if ext.has_data:
                size = (round(float(ext.size.x), 3), round(float(ext.size.y), 3))
        except Exception:                                  # noqa: BLE001
            size = None
    return {"radii": radii, "size": size,
            "kinds": dict(collections.Counter(x.dxftype() for x in b))}


# --------------------------------------------------------------------------
# 닫힌 도형 — 폴백용
# --------------------------------------------------------------------------

def loops(sh: Sheet) -> list:
    if "loops" in sh._cache:
        return sh._cache["loops"]
    out = []
    hidden = sh.hidden_layers
    for e in sh.msp:
        t = e.dxftype()
        try:
            if t == "CIRCLE":
                c, r = e.dxf.center, float(e.dxf.radius)
                out.append(Loop(sh.rect_of(_Ext(c.x - r, c.y - r, c.x + r, c.y + r)),
                                "CIRCLE", e.dxf.layer, 0, e.dxf.layer in hidden))
            elif t == "LWPOLYLINE" and e.closed:
                pts = list(e.get_points("xy"))
                xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
                out.append(Loop(sh.rect_of(_Ext(min(xs), min(ys), max(xs), max(ys))),
                                "POLY", e.dxf.layer, len(pts), e.dxf.layer in hidden))
            elif t == "ARC":
                ext = _bbox.extents([e], fast=True)
                if ext.has_data:
                    out.append(Loop(sh.rect_of(ext), "ARC", e.dxf.layer, 0,
                                    e.dxf.layer in hidden))
        except Exception:                                  # noqa: BLE001
            continue
    sh._cache["loops"] = out
    return out


def lines(sh: Sheet) -> list:
    """LINE 과 열린 LWPOLYLINE 의 끝점 쌍 (표시 좌표) — 지시선 한 걸음용."""
    if "lines" in sh._cache:
        return sh._cache["lines"]
    out = []
    for e in sh.msp:
        t = e.dxftype()
        try:
            if t == "LINE":
                a, b = e.dxf.start, e.dxf.end
                out.append((sh.to_page(a.x, a.y), sh.to_page(b.x, b.y), e.dxf.layer))
            elif t == "LWPOLYLINE" and not e.closed:
                pts = list(e.get_points("xy"))
                if len(pts) >= 2:
                    out.append((sh.to_page(*pts[0]), sh.to_page(*pts[-1]), e.dxf.layer))
            elif t == "LEADER":
                pts = list(e.vertices)
                if len(pts) >= 2:
                    out.append((sh.to_page(pts[0].x, pts[0].y),
                                sh.to_page(pts[-1].x, pts[-1].y), e.dxf.layer))
        except Exception:                                  # noqa: BLE001
            continue
    sh._cache["lines"] = out
    return out


# --------------------------------------------------------------------------
# 타이틀블록 — 캡션 아래 칸
# --------------------------------------------------------------------------

def title_fields(sh: Sheet) -> dict:
    """캡션 바로 아래(같은 칸)의 글자.  못 찾으면 빈 문자열 — 지어내지 않는다.

    타이틀 띠는 프레임 블록 정의 안(`FRAME`)이거나, 블록이 풀린 장에서는
    모델스페이스 글자다 — 둘 다 같은 규칙으로 본다.
    """
    ws = [w for w in words(sh) if not w.hidden]
    out = {}
    for field_name, captions in TITLE_CAPTIONS.items():
        caps = [w for w in ws if w.text.strip().upper() in captions]
        # 표 머리(`REV.` 가 개정 이력표 머리에도 있다) 가 아니라 **값이 바로 아래
        # 있는** 캡션을 고른다 — 아래 한 줄 안에 글자가 하나 있는 것.
        best = None
        for c in caps:
            ch = c.rect[3] - c.rect[1]
            below = [w for w in ws if w is not c
                     and w.rect[1] >= c.rect[1] - ch * 0.2
                     and w.rect[1] <= c.rect[3] + ch * 2.5
                     and w.rect[0] >= c.rect[0] - ch * 6
                     and w.rect[0] <= c.rect[2] + ch * 25      # 제목 칸은 캡션보다 훨씬 넓다
                     and w.text.strip().upper() not in _ALL_CAPTIONS]
            below = [w for w in below if w.rect[1] > c.rect[1]]
            if below:
                w = min(below, key=lambda w: (w.rect[1] - c.rect[3], abs(w.rect[0] - c.rect[0])))
                cand = (w.rect[1] - c.rect[3], w.text)
                if best is None or cand[0] < best[0]:
                    best = cand
        out[field_name] = (best[1] if best else "")
        out[field_name + "_found"] = bool(caps)
    return out


_ALL_CAPTIONS = {c for caps in TITLE_CAPTIONS.values() for c in caps} | {
    "PROJECT NO.", "REF. DRAWING NO.", "SCALE", "REF.CODE", "PROJECT NAME",
    "OWNER", "OWNER'S ENGINEER", "CONTRACTOR", "DATE", "DESCRIPTION",
    "PREPARED", "REVIEWED", "APPROVED"}


def inventory(sh: Sheet) -> dict:
    """장 하나의 판독 사실 — [B] 표의 한 줄."""
    if sh.error:
        return {"no": sh.no, "file": sh.file, "error": sh.error}
    ents = collections.Counter(e.dxftype() for e in sh.msp)
    syms = symbols(sh)
    attr = [s for s in syms if any(v for v in s.attrs.values())]
    layers = collections.Counter(e.dxf.layer for e in sh.msp)
    return {
        "no": sh.no, "file": sh.file, "version": sh.version,
        "audit_errors": sh.audit_errors,
        "entities": dict(ents), "insert": len(syms), "insert_with_attribs": len(attr),
        "block_kinds": len({s.block for s in syms}),
        "blocks": dict(collections.Counter(s.block for s in syms).most_common()),
        "attr_tags": dict(collections.Counter(t for s in attr for t, v in s.attrs.items() if v)),
        "layers": dict(layers.most_common()),
        "hidden_layers": sorted(sh.hidden_layers),
        "pdf_import_share": round(sum(n for l, n in layers.items()
                                      if l.upper().startswith("PDF")) / max(1, sum(layers.values())), 3),
        "width": round(sh.width, 2), "height": round(sh.height, 2),
    }
