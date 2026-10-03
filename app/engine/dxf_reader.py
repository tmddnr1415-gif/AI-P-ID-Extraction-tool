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
import math
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
    handle: str = ""       # 그 INSERT 의 핸들 — 블록 안 글자를 읽을 때 (`insert_words`)


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


def open_set(path: Path, only: int = None) -> tuple:
    """장 목록.  **한 장이 실패해도 나머지는 계속한다** — 실패 사유는 그 장에 붙는다.

    `only` 는 **그림 한 장을 그릴 때만** 쓴다 — 그 장만 파고 나머지는 이름·번호만
    가진 껍데기로 둔다.  32장짜리 묶음에서 첫 그림이 뜨기까지 32장을 전부 파느라
    몇 분이 걸리던 것을 한 장 값으로 줄인다.
    ⚠ **분석은 이 인자를 쓰지 않는다** — 장 종류·범례·프로젝트 범위가 전체를 보고
    정해지기 때문이다 (46회차 `load_pages(only=)` 와 같은 규율 · 시험이 강제한다).
    """
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
        if only is not None and i != only:
            sheets.append(sh)                     # 껍데기 — 번호와 파일명만
            continue
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

def _text_angle(e) -> float:
    """글자의 회전 (도).  TEXT 는 `rotation`, MTEXT 는 `text_direction` 또는 `rotation`."""
    try:
        if e.dxftype() == "MTEXT":
            return float(e.get_rotation())
        return float(e.dxf.rotation or 0.0)
    except Exception:                                      # noqa: BLE001
        return 0.0


def _text_rect(sh: Sheet, e, height: float, text: str, line: int = 0) -> tuple:
    """글자 사각형 추정 — 정렬점과 **회전**을 존중한다.  폭은 글자 수 × 높이 × 0.75.

    hotfix17 — 회전을 보지 않고 늘 가로로 놓고 있었다.  UAD DXF 글자의 31%(4,697개)가
    90°/270° 이고, 세로로 선 버블 안 글자가 버블 밖 가로 띠로 계산되어 태그가 버블에
    안 붙거나 옆 버블에 붙었다 (p19 FIT·PIT·TIT)."""
    w = max(len(text), 1) * height * 0.75
    h = height
    halign = int(getattr(e.dxf, "halign", 0) or 0)
    valign = int(getattr(e.dxf, "valign", 0) or 0)
    # 기준점(ax, ay) 과 그 점에 대한 가로 사각형 (lx0, ly0, lx1, ly1)
    if e.dxftype() == "MTEXT":
        ax, ay = e.dxf.insert.x, e.dxf.insert.y
        att = int(getattr(e.dxf, "attachment_point", 1) or 1)
        col = (att - 1) % 3
        row = (att - 1) // 3
        lx0 = -(w / 2 if col == 1 else w if col == 2 else 0)
        ly1 = (h / 2 if row == 1 else h if row == 2 else 0)
        box = (lx0, ly1 - h, lx0 + w, ly1)
    else:
        ap = getattr(e.dxf, "align_point", None)
        if halign in (1, 2, 4) and ap is not None and (ap.x or ap.y):
            ax, ay = ap.x, ap.y
            lx0 = -(w / 2 if halign in (1, 4) else w)
            ly0 = -(h / 2 if valign == 2 or halign == 4 else 0)
        else:
            ax, ay = e.dxf.insert.x, e.dxf.insert.y
            lx0 = 0.0
            ly0 = -(h / 2) if valign == 2 else (-h if valign == 3 else 0.0)
        box = (lx0, ly0, lx0 + w, ly0 + h)
    if line:
        # MTEXT 의 n 번째 줄 — 줄 간격은 글자 방향에 수직으로 (회전을 따라) 내려간다
        box = (box[0], box[1] - line * h * 1.4, box[2], box[3] - line * h * 1.4)
    a = math.radians(_text_angle(e))
    if abs(a) < 1e-9:
        return sh.rect_of(_Ext(ax + box[0], ay + box[1], ax + box[2], ay + box[3]))
    c, s_ = math.cos(a), math.sin(a)
    pts = [(ax + x * c - y * s_, ay + x * s_ + y * c)
           for x, y in ((box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3]))]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return sh.rect_of(_Ext(min(xs), min(ys), max(xs), max(ys)))


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
    arcs = []
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
                out.append(Word(_text_rect(sh, e, h, ln, line=i), ln, e.dxf.layer,
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
            hidden=e.dxf.layer in hidden, anonymous=name.startswith("*"),
            handle=str(e.dxf.handle or "")))
    sh._cache["symbols"] = out
    return out


def insert_words(sh: Sheet, sym: "Symbol") -> list:
    """그 INSERT 의 **블록 정의 안** 글자 (TEXT · MTEXT) — 삽입 변환을 거쳐 표시 좌표로.

    hotfix17 — 버블 블록이 글자를 속성이 아니라 블록 안 글자로 담는 경우가 있다
    (UAD DXF p19 `EEE`: `MOV` 가 블록 정의 안 MTEXT).  모델스페이스 글자만 읽으면
    그 버블은 "안에 ISA 글자가 없다" 가 된다."""
    if not sym.handle:
        return []
    try:
        e = sh.doc.entitydb.get(sym.handle)
    except Exception:                                      # noqa: BLE001
        e = None
    if e is None:
        return []
    out = []
    try:
        for v in e.virtual_entities():
            t = v.dxftype()
            if t == "TEXT":
                s_ = (v.dxf.text or "").strip()
                if s_:
                    out.append(Word(_text_rect(sh, v, float(v.dxf.height or 1.0), s_), s_,
                                    v.dxf.layer, "BLOCK", float(v.dxf.height or 1.0)))
            elif t == "MTEXT":
                h = float(v.dxf.char_height or 1.0)
                lines = [ln.strip() for ln in v.plain_text().splitlines() if ln.strip()]
                for i, ln in enumerate(lines):
                    out.append(Word(_text_rect(sh, v, h, ln, line=i), ln, v.dxf.layer, "BLOCK", h))
    except Exception:                                      # noqa: BLE001
        return out
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
    return {"radii": radii, "size": size, "outline": _outline(b),
            "kinds": dict(collections.Counter(x.dxftype() for x in b))}


def _outline(b) -> str:
    """블록이 그린 **윤곽** — 선분과 원만, 칠(HATCH·SOLID)은 뺀다 (hotfix17).

    범례의 VALVE STATUS 구획은 같은 밸브를 열림/닫힘으로 **칠만 달리해** 다시
    그린다.  칠을 빼면 두 블록의 윤곽이 같고, 그 같음이 "이것은 저 밸브의 다른
    상태" 라는 도면의 말이다.  좌표는 그 블록 자신의 크기로 나눠 두 자리로 적는다
    (정의가 같은지 묻는 것이지 비슷한지 묻는 것이 아니다 — 새 허용치 없음).
    """
    segs, circ = [], []
    for e in b:
        t = e.dxftype()
        try:
            if t == "LINE":
                segs.append(((e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)))
            elif t == "LWPOLYLINE":
                p = [(q[0], q[1]) for q in e.get_points("xy")]
                if e.closed and p:
                    p = p + [p[0]]
                segs += list(zip(p, p[1:]))
            elif t == "CIRCLE":
                circ.append(((e.dxf.center.x, e.dxf.center.y), float(e.dxf.radius)))
        except Exception:                                  # noqa: BLE001
            continue
    pts = [q for a, c in segs for q in (a, c)]
    pts += [(q[0] - r, q[1] - r) for q, r in circ] + [(q[0] + r, q[1] + r) for q, r in circ]
    if not pts:
        return ""
    x0 = min(q[0] for q in pts); y0 = min(q[1] for q in pts)
    sc = max(max(q[0] for q in pts) - x0, max(q[1] for q in pts) - y0) or 1.0

    def n(q):
        return (round((q[0] - x0) / sc, 2), round((q[1] - y0) / sc, 2))
    lines_ = sorted({tuple(sorted((n(a), n(c)))) for a, c in segs if n(a) != n(c)})
    rings = sorted({(n(q), round(r / sc, 2)) for q, r in circ})
    return repr((lines_, rings))


# --------------------------------------------------------------------------
# 닫힌 도형 — 폴백용
# --------------------------------------------------------------------------

def loops(sh: Sheet) -> list:
    if "loops" in sh._cache:
        return sh._cache["loops"]
    out = []
    arcs = []
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
                arcs.append(e)                     # 아래에서 **마주 본 짝**으로 세운다
        except Exception:                                  # noqa: BLE001
            continue
    out.extend(_arc_loops(sh, arcs, hidden))
    sh._cache["loops"] = out
    return out


def _arc_loops(sh: Sheet, arcs: list, hidden: set) -> list:
    """호를 **마주 본 캡 둘**로 짝지어 버블 하나로 세운다.

    ★ 호 하나의 bbox 는 버블의 반쪽이다.  계기 버블을 반원 둘 + 곧은 옆면으로
    그린 장에서, 호를 하나씩 보면 높이가 반으로 잡혀 크기 창에 못 든다.
    실측(UAD p6): 반지름 4.0 짜리 호 **34개가 정확히 17쌍**이고 각 쌍은 중심이
    한 축으로 나란히 16.0 떨어져 있다 — 24.0 × 8.0 짜리 버블 17개다.  짝을 못
    지은 호는 제 원(중심 ± 반지름)으로 둔다.

    **새 상수가 없다.**  짝의 조건은 모양뿐이다: 반지름이 같고(2%), 중심이 한
    축으로 나란하며(반지름의 5%), 두 호가 **서로 반대쪽을 보는 것**(각 호의
    가운데가 상대 중심의 반대편) — PDF 경로가 *마주 본 호 캡 둘*로 버블을
    세우는 것과 같은 판단이다 (§10-10).  크기는 그 문서 범례가 그린 계기 원이
    거른다.
    """
    import math
    got, used = [], set()
    info = []
    for e in arcs:
        try:
            c = e.dxf.center
            info.append((float(c.x), float(c.y), float(e.dxf.radius),
                         float(e.dxf.start_angle), float(e.dxf.end_angle), e))
        except Exception:                                  # noqa: BLE001
            continue

    def mid_dir(a):
        s_, t_ = a[3], a[4]
        if t_ < s_:
            t_ += 360.0
        m = math.radians((s_ + t_) / 2.0)
        return math.cos(m), math.sin(m)

    for i, a in enumerate(info):
        if i in used:
            continue
        for j in range(i + 1, len(info)):
            if j in used:
                continue
            b = info[j]
            if abs(a[2] - b[2]) > 0.02 * max(a[2], b[2]) or a[2] <= 0:
                continue
            dx, dy = b[0] - a[0], b[1] - a[1]
            tol = 0.05 * a[2]
            if abs(dy) <= tol and abs(dx) > tol:
                axis = (1.0, 0.0)
            elif abs(dx) <= tol and abs(dy) > tol:
                axis = (0.0, 1.0)
            else:
                continue
            sign = 1.0 if (dx * axis[0] + dy * axis[1]) > 0 else -1.0
            ma, mb = mid_dir(a), mid_dir(b)
            # a 는 짝의 반대쪽(-sign)을, b 는 그 반대(+sign)를 봐야 캡이다
            if (ma[0] * axis[0] + ma[1] * axis[1]) * sign > -0.5:
                continue
            if (mb[0] * axis[0] + mb[1] * axis[1]) * sign < 0.5:
                continue
            r = a[2]
            x0 = min(a[0], b[0]) - r; x1 = max(a[0], b[0]) + r
            y0 = min(a[1], b[1]) - r; y1 = max(a[1], b[1]) + r
            got.append(Loop(sh.rect_of(_Ext(x0, y0, x1, y1)), "ARC",
                            a[5].dxf.layer, 0, a[5].dxf.layer in hidden))
            used |= {i, j}
            break
    for i, a in enumerate(info):
        if i in used:
            continue
        r = a[2]
        got.append(Loop(sh.rect_of(_Ext(a[0] - r, a[1] - r, a[0] + r, a[1] + r)),
                        "ARC", a[5].dxf.layer, 0, a[5].dxf.layer in hidden))
    return got


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
                # hotfix17 — 꼭짓점이 Vec3 가 아니라 튜플로 오는 판이 있다.  `.x` 로 읽다
                # 예외가 아래 `except` 에 삼켜져 **모든 LEADER 가 조용히 빠졌다** (UAD DXF
                # p19 MOV 버블의 지시선이 LEADER 다).  인덱스로 읽는다.
                pts = [(float(v[0]), float(v[1])) for v in e.vertices]
                if len(pts) >= 2:
                    out.append((sh.to_page(*pts[0]), sh.to_page(*pts[-1]), e.dxf.layer))
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
