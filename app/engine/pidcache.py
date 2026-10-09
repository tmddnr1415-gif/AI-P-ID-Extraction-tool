"""Shared page cache for the P&ID spikes (docs/design.md §5 step [0]).

Two jobs, both done once at cache-build time so that no downstream module has
to think about them:

1. **Rotation normalisation.**  Two of the 58 pages (7 and 48) are stored
   rotated 270 degrees.  PyMuPDF returns text and vector coordinates in the
   *unrotated* frame, which puts them outside the visible page box and breaks
   every fixed-region rule.  `PageCache` multiplies everything through
   `page.rotation_matrix` up front, so all coordinates a caller ever sees are
   display-space and the same rules apply to all 58 pages.  The original angle
   is kept in `source_rotation` for the record only.

2. **Analysis scope.**  Page 48 is a drawing carried over from a different
   project (`PORT DICKSON 1400MW CCGT`; the other 57 are `AL NOUF1 PROJECT`).
   It is flagged `analysis_scope = False` with a reason rather than dropped —
   it really is in the source PDF, so removing it would break page-number
   cross-checks and hide why it was skipped.  Scope is decided by majority
   PROJECT NAME, not by hardcoded page numbers.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import projectconfig  # noqa: E402


# Title block PROJECT NAME cell.  Project-dependent (out/project_deps.md P5),
# so it comes from the project config rather than a constant here.
_CFG = projectconfig.load()
# A profile that leaves the cell out is saying the sheet states it, and it does -
# `derive_layout` finds it by the form's own `PROJECT NAME` caption.  Until the
# pages are open there is nothing to measure, so the name is left unread and
# `rename_projects` fills it in once the cell is known.
PROJECT_NAME_REGION = _CFG.get_or("title_block.project_name_region", None)
PROJECT_NAME_MIN_HEIGHT = _CFG.get_or("title_block.project_name_min_height", None)


def rename_projects(pages, region, min_height) -> None:
    """Re-read every page's PROJECT NAME once the cell has been measured.

    Same rule as at load: the name most pages carry is the project, and a page
    naming a different one is out of scope.  Run again rather than duplicated,
    so a document whose cell was measured is judged exactly as one whose cell was
    configured.
    """
    global PROJECT_NAME_REGION, PROJECT_NAME_MIN_HEIGHT
    PROJECT_NAME_REGION, PROJECT_NAME_MIN_HEIGHT = region, min_height
    for pc in pages:
        pc.project_name = _project_name(pc.words)
        pc.analysis_scope, pc.scope_reason = True, ""
    _scope_by_project(pages)

# A page whose /Rotate is 0 has this as its rotation matrix, and multiplying a
# point by it is a no-op.  Compared as a tuple because Matrix has no __eq__ that
# says so.
_IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


# hotfix70 — 회전 행렬 곱을 PyMuPDF 를 거치지 않고 같은 값으로.
#
# `Point * m` · `Rect * m` 은 한 번에 Point/Matrix 래퍼를 서넛 만들고 swig 를 두 번 건넌다.  TC2(60장 ·
# 전부 /Rotate 270) 프로파일에서 이 곱이 2천만 번 · 분석의 4분의 1을 썼다 (out/hotfix70/tc2_prof).
# 페이지 회전 행렬은 성분이 0 · ±1 뿐이라 MuPDF 가 float 로 하는 계산(`fz_transform_point` ·
# `fz_transform_rect`)을 double 로 한 뒤 float 로 한 번 반올림하면 **비트까지 같다** — 0·±1 곱은 정확하고
# 남는 덧셈 한 번은 double 에서 정확하므로 반올림이 한 번뿐이다.  그 밖의 행렬이면 예전 길(`p * m`)로 간다.
# 같은지는 import 때 PyMuPDF 와 맞대 보고(`_ROT_OK`), 다르면 이 길을 끈다 — 판본이 바뀌어도 값은 안 바뀐다.
import struct as _struct

_F32 = _struct.Struct("f")


def _f32(v: float) -> float:
    return _F32.unpack(_F32.pack(v))[0]


_PT, _RC = pymupdf.Point, pymupdf.Rect


def _mkpt(x: float, y: float):
    """`pymupdf.Point(x, y)` 과 같은 객체 — 범용 생성자(인자 모양 가리기)를 건너뛴다.  값은 이미 float 다."""
    p = _PT.__new__(_PT)
    p.x = x
    p.y = y
    return p


def _mkrect(x0: float, y0: float, x1: float, y1: float):
    r = _RC.__new__(_RC)
    r.x0, r.y0, r.x1, r.y1 = x0, y0, x1, y1
    return r


class Rot:
    """한 장의 회전 행렬 — `pt(p)` 는 `p * m`, `rect(r)` 은 `Rect(r) * m`, `segs(쌍들)` 은 쌍마다 두 점을
    `* m` 한 것과 같은 값을 낸다."""
    __slots__ = ("m", "fast", "a", "b", "c", "d", "e", "f", "ident")

    def __init__(self, m):
        self.m = m
        t = tuple(float(v) for v in m)
        self.a, self.b, self.c, self.d, self.e, self.f = t
        self.ident = t == _IDENTITY
        self.fast = _ROT_OK and all(v in (0.0, 1.0, -1.0) for v in t[:4]) and t[4] == _f32(t[4]) \
            and t[5] == _f32(t[5])

    def xy(self, x: float, y: float) -> tuple[float, float]:
        return (_f32(x * self.a + y * self.c + self.e), _f32(x * self.b + y * self.d + self.f))

    def pt(self, p):
        if not self.fast:
            return pymupdf.Point(p) * self.m
        if self.ident:
            return _mkpt(float(p.x), float(p.y))
        return _mkpt(*self.xy(p.x, p.y))

    def segs(self, pairs: list) -> list:
        """`[(Point(a) * m, Point(b) * m) for a, b in pairs]` 와 같은 값 — 한 장의 선분 전부를 한 번에 옮긴다
        (numpy 로 같은 순서의 double 계산 → float 반올림 한 번)."""
        if not self.fast:
            m = self.m
            return [(pymupdf.Point(a) * m, pymupdf.Point(b) * m) for a, b in pairs]
        if not pairs:
            return []
        import numpy as np
        xy = np.array([(a.x, a.y, b.x, b.y) for a, b in pairs], dtype=np.float64)
        A, B, C, D, E, F = self.a, self.b, self.c, self.d, self.e, self.f

        def f32(v):
            return v.astype(np.float32).astype(np.float64).tolist()
        ax, ay = f32(xy[:, 0] * A + xy[:, 1] * C + E), f32(xy[:, 0] * B + xy[:, 1] * D + F)
        bx, by = f32(xy[:, 2] * A + xy[:, 3] * C + E), f32(xy[:, 2] * B + xy[:, 3] * D + F)
        return [(_mkpt(p, q), _mkpt(r, s)) for p, q, r, s in zip(ax, ay, bx, by)]

    def rect(self, r):
        if not self.fast:
            return pymupdf.Rect(r) * self.m
        x0, y0, x1, y1 = r
        x0, y0, x1, y1 = float(x0), float(y0), float(x1), float(y1)
        if self.ident:
            return _mkrect(x0, y0, x1, y1)
        if max(abs(x0), abs(y0), abs(x1), abs(y1)) >= 2.0e9:     # 무한 사각형 — MuPDF 가 그대로 돌려준다
            return pymupdf.Rect(r) * self.m
        # fz_transform_rect 의 축 정렬 두 갈래 — 뒤집히는 축이면 먼저 끝을 바꾸고 두 모서리만 옮긴다
        if self.b == 0.0 and self.c == 0.0:
            if self.a < 0:
                x0, x1 = x1, x0
            if self.d < 0:
                y0, y1 = y1, y0
        elif self.a == 0.0 and self.d == 0.0:
            if self.b < 0:
                x0, x1 = x1, x0
            if self.c < 0:
                y0, y1 = y1, y0
        else:                                     # pragma: no cover — fast 는 이 둘만 받는다
            return pymupdf.Rect(r) * self.m
        sx, sy = self.xy(x0, y0)
        tx, ty = self.xy(x1, y1)
        return _mkrect(sx, sy, tx, ty)


def _rot_self_check() -> bool:
    """이 PyMuPDF 판본에서 `Rot` 가 `* m` 과 같은 값을 내는가 — 다르면 빠른 길을 쓰지 않는다."""
    import random
    rng = random.Random(70)
    mats = [pymupdf.Matrix(1, 0, 0, 1, 0, 0), pymupdf.Matrix(0, -1, 1, 0, 0, 842),
            pymupdf.Matrix(0, 1, -1, 0, 1190.5511474609375, 0), pymupdf.Matrix(-1, 0, 0, -1, 595.2755737304688, 841.8897705078125)]
    for m in mats:
        R = Rot.__new__(Rot)
        Rot.__init__(R, m)
        R.fast = True
        for _ in range(200):
            x, y = _f32(rng.uniform(-50, 2500)), _f32(rng.uniform(-50, 2500))
            q = pymupdf.Point(x, y) * m
            got = R.pt(pymupdf.Point(x, y))
            if type(got) is not type(q) or vars(got) != vars(q) or (repr(got.x), repr(got.y)) != (repr(q.x), repr(q.y)):
                return False
            w, h = _f32(rng.uniform(-3, 80)), _f32(rng.uniform(-3, 80))
            r = pymupdf.Rect(x, y, _f32(x + w), _f32(y + h))
            a, b = R.rect(r), pymupdf.Rect(r) * m
            if type(a) is not type(b) or vars(a) != vars(b) or tuple(map(repr, a)) != tuple(map(repr, b)):
                return False
        pts = [pymupdf.Point(_f32(rng.uniform(-50, 2500)), _f32(rng.uniform(-50, 2500))) for _ in range(200)]
        pairs = list(zip(pts[::2], pts[1::2])) + [(pymupdf.Point(0, 0), pymupdf.Point(-0.0, 842))]
        for (p, q), (u, v) in zip(R.segs(pairs), [(pymupdf.Point(p) * m, pymupdf.Point(q) * m) for p, q in pairs]):
            for a, b in ((p, u), (q, v)):
                if type(a) is not type(b) or vars(a) != vars(b) or (repr(a.x), repr(a.y)) != (repr(b.x), repr(b.y)):
                    return False
    return True


_ROT_OK = False
_ROT_OK = _rot_self_check()


@dataclass
class PageCache:
    """One page with every coordinate already in display space."""

    page: pymupdf.Page
    page_no: int                      # 1-based
    source_rotation: int              # original /Rotate value, informational
    width: float
    height: float
    words: list[tuple[pymupdf.Rect, str]]
    project_name: str
    analysis_scope: bool = True
    scope_reason: str = ""
    memo_words_dropped: int = 0       # hotfix41 — 검토 메모(FreeText) 안이라 뺀 낱말 수

    _rects: list[pymupdf.Rect] | None = field(default=None, repr=False)
    _segments: list[tuple[pymupdf.Point, pymupdf.Point]] | None = field(default=None, repr=False)
    _drawings: list[dict] | None = field(default=None, repr=False)

    # -- lazily built views over the vector content -----------------------
    def drawings(self) -> list[dict]:
        """Raw drawings with an added display-space 'bbox' key."""
        if self._drawings is None:
            R = Rot(self.page.rotation_matrix)
            out = []
            for d in self.page.get_drawings():
                d = dict(d)
                d["bbox"] = R.rect(d["rect"])
                out.append(d)
            self._drawings = out
        return self._drawings

    def rects(self) -> list[pymupdf.Rect]:
        """Bounding boxes of every vector drawing, display space."""
        if self._rects is None:
            self._rects = [d["bbox"] for d in self.drawings()]
        return self._rects

    def segments(self) -> list[tuple[pymupdf.Point, pymupdf.Point]]:
        """Every straight line segment, display space.

        Note these sheets carry ~150k segments each, most of them glyph and
        curve tessellation — callers should filter by length.

        **The points are the drawing cache's own objects on unrotated pages.**
        Building two `pymupdf.Point`s per segment and multiplying each by the
        rotation matrix was the single largest cost in the analysis — 300k to
        660k objects per page — and on 56 of these 58 pages the matrix is the
        identity, so the multiplication changed nothing.  Measured over six
        pages: 30.8s to build them, 1.3s to hand back the points already in the
        cache.  Every caller only reads coordinates (`detect_symbols` x3,
        `detect_valves` x2, `legend_rules`), which `tests/test_determinism.py
        ::test_segments_are_not_mutated_by_the_engine` pins; a caller that
        wanted to move a point would now be moving the cached drawing with it.
        """
        if self._segments is None:
            m = self.page.rotation_matrix
            drawings = self.drawings()
            if tuple(m) == _IDENTITY:
                self._segments = [(it[1], it[2]) for d in drawings
                                  for it in d["items"] if it[0] == "l"]
            else:
                self._segments = Rot(m).segs(
                    [(it[1], it[2]) for d in drawings for it in d["items"] if it[0] == "l"])
        return self._segments

    def pixmap(self, clip: pymupdf.Rect, zoom: float = 2.0, **kw):
        """Render a display-space clip (get_pixmap already honours rotation)."""
        return self.page.get_pixmap(clip=clip, matrix=pymupdf.Matrix(zoom, zoom), **kw)


def _project_name(words) -> str:
    if PROJECT_NAME_REGION is None or PROJECT_NAME_MIN_HEIGHT is None:
        return ""
    x0, y0, x1, y1 = PROJECT_NAME_REGION
    cand = [
        (r, t) for r, t in words
        if x0 <= r.x0 and r.x1 <= x1 and y0 <= r.y0 and r.y1 <= y1
        and r.height >= PROJECT_NAME_MIN_HEIGHT
    ]
    cand.sort(key=lambda rt: rt[0].x0)
    return " ".join(t for _, t in cand).strip()


# Some CAD exports stamp the sheet's frame more than once, so the same word
# arrives several times at the same coordinates.  Dropping the repeats is not a
# judgement about the drawing - two words at identical coordinates *are* one word
# - but it is still off unless a project asks for it, because a project whose
# repeats are meaningful must not have them silently removed.  With the key
# absent this is a no-op and the word list is byte-for-byte what PyMuPDF returned.
_DEDUP_WORDS = bool((_CFG.data.get("text") or {}).get("dedup_exact_duplicates"))


def _dedup(words):
    """Keep the first of each (rounded rect, text); order is otherwise unchanged."""
    seen, out = set(), []
    for r, t in words:
        key = (round(r.x0, 2), round(r.y0, 2), round(r.x1, 2), round(r.y1, 2), t)
        if key in seen:
            continue
        seen.add(key)
        out.append((r, t))
    return out


# --------------------------------------------------------------------------
# 획(SHX) 글꼴로 그린 글자 — 도형으로 인쇄되고, 같은 자리에 주석으로 남는다
# --------------------------------------------------------------------------
# AutoCAD 는 TrueType 글자만 PDF 텍스트로 내보내고 **SHX(획) 글꼴은 선으로
# 그린다**.  그러면서 그 글자를 담은 주석을 같은 자리에 함께 남기고, 그
# 주석의 **작성자 칸에 `AutoCAD SHX Text` 라고 적는다** — 즉 도면이 "이건
# 내가 그린 글자다" 라고 스스로 말한다 (§9 ①~③).
#
# 사람이 붙인 검토 메모와는 **그 칸 하나로 갈린다**: 실측 네 문서 —
#   AL NOUF1  FreeText · 작성자 `sc.y`        · 64건 (`I/O 만 반영` 따위)
#   SADARA    FreeText · 작성자 `hyomi.kang`  · 24건
#   TC2       Square   · 작성자 `AutoCAD SHX Text` · 909건
#   UAD       Square   · 작성자 `AutoCAD SHX Text` · 10,729건
# 종류(Square/FreeText)로 가르지 않는다 — **작성자가 누구인지**가 답이고,
# 사람 이름으로 적힌 메모를 도면의 글자로 읽으면 검토 메모가 태그가 된다.
#
# ⚠ UAD 는 32장 중 29장이 이 갈래다 (텍스트 낱말 3,590 ↔ 주석 글자 10,729).
# 이것을 안 읽으면 도면번호도 태그도 한 글자도 못 읽는다 — 28회차가 고친 것.
SHX_AUTHOR = "AutoCAD SHX Text"


def _shx_entries(page, m) -> list:
    """`(사각형, 글자)` — 그 장이 SHX 주석으로 남긴 글자.  없으면 빈 목록."""
    out = []
    try:
        annots = list(page.annots() or [])
    except Exception:
        return out
    for a in annots:
        info = a.info or {}
        if (info.get("title") or "").strip() != SHX_AUTHOR:
            continue
        text = " ".join((info.get("content") or "").split())
        if not text:
            continue
        out.append((Rot(m).rect(a.rect), text))
    return out


def _hide_memos(page) -> int:
    """hotfix41 — **사람이 붙인 검토 메모(FreeText)를 메모리에서 숨긴다.**  숨긴 수를 돌려준다.

    QFE 는 검토자가 `ESDV OUTLET TAG 중복 확인.` 같은 메모를 FreeText 로 올려 두었고, 그
    글자가 `get_text("words")` 에 **도면 글자와 같은 얼굴로** 들어와 기기 라벨이 되어
    Description 에 섞였다 (실측 QFE 260326: 13장 · 메모 61 · AL NOUF1 39장 · 64).
    §9 — 메모는 도면이 말한 것이 아니다.  **종류가 아니라 작성자**로 가른다(SHX 주석과
    같은 기준): SHX 는 도면 자신이 남긴 글자이고, 사람 이름이 적힌 FreeText 는 메모다.

    ★ 사각형 안의 낱말을 빼는 방식은 쓰지 않는다 — 메모 상자는 도면 위에 놓이고 그 밑의
    심볼 글자까지 삼킨다 (첫 판이 AL NOUF1 p16 `FE ….. VS RO` · p26 `PI` 를 지워 1137 →
    1102행이 됐다).  대신 주석에 **숨김 깃발**을 세우면 렌더러가 그 겉모양을 그리지 않아
    `get_text` 에서 **메모가 그린 글자만** 정확히 빠진다 — 판정이 아니라 PDF 자신의 규칙이다.
    실측 AL NOUF1 p16 RO 14 → 12(메모 둘) · FE 2 → 2 · `…..` 63 → 63 · p26 PI 7 → 7 (메모 상자
    밑의 진짜 PI 가 산다) · QFE p6 `중복` 4 → 0 · `ESDV` 4 → 2(진짜 둘).
    문서는 저장하지 않는다 — 깃발은 이 프로세스의 메모리에만 있다.  SHX 주석(Square)과
    도면 PNG(`main.page_png` 는 제 문서를 따로 연다)에는 닿지 않는다.
    """
    n = 0
    try:
        annots = list(page.annots() or [])
    except Exception:
        return 0
    for a in annots:
        if a.type[1] != "FreeText":
            continue
        if ((a.info or {}).get("title") or "").strip() == SHX_AUTHOR:
            continue
        try:
            a.set_flags(a.flags | pymupdf.PDF_ANNOT_IS_HIDDEN)
            n += 1
        except Exception:
            continue
    return n


def _shx_words(entries) -> list:
    """SHX 주석을 낱말로 — **쪼개지 않는다.**

    주석이 주는 것은 덩어리 사각형 **하나**뿐이다.  여러 낱말을 낱말 길이에
    비례해 나눠 놓을 수는 있지만 그 자리는 잰 값이 아니라 **지어낸 값**이고
    (§2.1 ③), 한 줄인지 여러 줄로 접힌 덩어리인지를 가를 근거도 이 문서에
    없다 — 한 낱말짜리 주석으로 글자폭을 재어 갈라 보면 한 줄 캡션(1.25~1.54)과
    접힌 덩어리가 **1.3~3.0 구간에서 576건 겹친다** (빈 띠가 없으므로 문턱을
    그 안에 두면 임의값이다 · §2.2).

    그래서 덩어리는 덩어리로 둔다.  캡션을 낱말 단위로 찾는 쪽
    (`derive_layout._caption_rows`)이 낱말로 쪼개 읽는다 — 글자를 읽는 쪽이
    쪼개는 것은 판정이 아니라 읽기다.
    """
    return list(entries)


def tokens(words):
    """낱말 조각을 **낱말 단위로** 읽는다 — 자리는 그 조각의 사각형 그대로.

    획(SHX) 글꼴 주석은 `VALVES ACTUATORS` 처럼 여러 낱말을 한 조각에 담는다.
    쪼개서 자리를 나누면 그 자리는 지어낸 값이 되고(§2.1 ③), 한 줄인지 접힌
    덩어리인지 가를 빈 띠도 이 문서들에 없다 — 짧은 변으로 갈라도 한 줄짜리
    `1A5J-…-0002 (C-2)`(두 줄 15pt)와 한 낱말(최대 14pt)이 겹친다.

    그래서 **자리는 조각의 것을 그대로 쓰고 글자만 낱말로 읽는다.**  이름으로
    무언가를 찾는 쪽(범례 머리말 · 행 라벨)이 쓰는 함수이고, 자리를 재는 쪽은
    조각 사각형이 곧 그 낱말이 인쇄된 자리의 상한이라는 것을 알고 쓴다.
    """
    for r, t in words:
        parts = t.split()
        if len(parts) == 1:
            yield r, t
            continue
        for part in parts:
            yield r, part


def load_pages(pdf_path: str | Path, only=None
               ) -> tuple[pymupdf.Document, list[PageCache]]:
    """Open the PDF and build a rotation-normalised, scope-tagged page cache.

    `only` 는 46회차에 늘었다 — **그 장만** 캐시로 세운다 (장 번호 1부터).
    쓰는 곳은 마크업 제안(`pipeline.propose_at`) 하나다: 사람이 사각형을 하나
    그릴 때마다 58~60장을 다 여는 것이 실측 1.9~8.6초였다.

    ⚠ **분석 경로는 절대 쓰지 않는다.**  `_scope_by_project` 는 *다수결*이라
    한 장만 넣으면 그 장이 곧 다수가 되어 44회차 [C](남의 프로젝트 장 빼기)가
    무력해진다.  제안은 이미 분석이 받아들인 장 위에서만 도는 일이므로
    그것으로 충분하지만, 분석에 쓰면 조용히 틀린다.
    `tests/test_markup_speed.py` 가 `_analyse` 에 `only=` 가 없음을 강제한다.
    """
    doc = pymupdf.open(pdf_path)

    want = None if only is None else {int(x) for x in only}
    pages: list[PageCache] = []
    for i in range(doc.page_count):
        if want is not None and (i + 1) not in want:
            continue
        page = doc[i]
        # hotfix41 — 사람이 붙인 검토 메모(FreeText)의 글자는 도면의 글자가 아니다.  숨긴 뒤
        # 다시 읽는다 (숨김은 메모리에만 · 메모가 그린 글자만 빠진다).
        memo_dropped = 0
        if any(a.type[1] == "FreeText" for a in (page.annots() or [])):
            before = len(page.get_text("words"))          # 숨기기 **전**에 센다
            if _hide_memos(page):
                page = doc.reload_page(page)
                memo_dropped = before - len(page.get_text("words"))
        m = page.rotation_matrix
        R = Rot(m)
        words = [(R.rect(w[:4]), w[4]) for w in page.get_text("words")]
        words += _shx_words(_shx_entries(page, m))
        if _DEDUP_WORDS:
            words = _dedup(words)
        pages.append(
            PageCache(
                page=page,
                page_no=i + 1,
                source_rotation=page.rotation,
                width=page.rect.width,
                height=page.rect.height,
                words=words,
                project_name=_project_name(words),
                memo_words_dropped=memo_dropped,
            )
        )

    _scope_by_project(pages)
    return doc, pages


def _scope_by_project(pages) -> None:
    """Majority PROJECT NAME defines the project; anything else is out of scope."""
    counts: dict[str, int] = {}
    for pc in pages:
        if pc.project_name:
            counts[pc.project_name] = counts.get(pc.project_name, 0) + 1
    if not counts:
        return
    main = max(counts, key=counts.get)
    for pc in pages:
        if pc.project_name and pc.project_name != main:
            pc.analysis_scope = False
            pc.scope_reason = f"FOREIGN_PROJECT:{pc.project_name}"


def in_region(r: pymupdf.Rect, region: tuple) -> bool:
    x0, y0, x1, y1 = region
    return x0 <= r.x0 and r.x1 <= x1 and y0 <= r.y0 and r.y1 <= y1
