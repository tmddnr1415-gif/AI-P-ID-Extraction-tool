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

    _rects: list[pymupdf.Rect] | None = field(default=None, repr=False)
    _segments: list[tuple[pymupdf.Point, pymupdf.Point]] | None = field(default=None, repr=False)
    _drawings: list[dict] | None = field(default=None, repr=False)

    # -- lazily built views over the vector content -----------------------
    def drawings(self) -> list[dict]:
        """Raw drawings with an added display-space 'bbox' key."""
        if self._drawings is None:
            m = self.page.rotation_matrix
            out = []
            for d in self.page.get_drawings():
                d = dict(d)
                d["bbox"] = pymupdf.Rect(d["rect"]) * m
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
                self._segments = [
                    (pymupdf.Point(it[1]) * m, pymupdf.Point(it[2]) * m)
                    for d in drawings for it in d["items"] if it[0] == "l"]
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


def load_pages(pdf_path: str | Path) -> tuple[pymupdf.Document, list[PageCache]]:
    """Open the PDF and build a rotation-normalised, scope-tagged page cache."""
    doc = pymupdf.open(pdf_path)

    pages: list[PageCache] = []
    for i in range(doc.page_count):
        page = doc[i]
        m = page.rotation_matrix
        words = [(pymupdf.Rect(w[:4]) * m, w[4]) for w in page.get_text("words")]
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
