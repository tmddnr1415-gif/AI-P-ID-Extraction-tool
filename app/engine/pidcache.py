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
PROJECT_NAME_REGION = _CFG.rect("title_block.project_name_region")
PROJECT_NAME_MIN_HEIGHT = float(_CFG.get("title_block.project_name_min_height"))


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
        """
        if self._segments is None:
            m = self.page.rotation_matrix
            segs = []
            for d in self.page.get_drawings():
                for item in d["items"]:
                    if item[0] == "l":
                        segs.append((pymupdf.Point(item[1]) * m, pymupdf.Point(item[2]) * m))
            self._segments = segs
        return self._segments

    def pixmap(self, clip: pymupdf.Rect, zoom: float = 2.0, **kw):
        """Render a display-space clip (get_pixmap already honours rotation)."""
        return self.page.get_pixmap(clip=clip, matrix=pymupdf.Matrix(zoom, zoom), **kw)


def _project_name(words) -> str:
    x0, y0, x1, y1 = PROJECT_NAME_REGION
    cand = [
        (r, t) for r, t in words
        if x0 <= r.x0 and r.x1 <= x1 and y0 <= r.y0 and r.y1 <= y1
        and r.height >= PROJECT_NAME_MIN_HEIGHT
    ]
    cand.sort(key=lambda rt: rt[0].x0)
    return " ".join(t for _, t in cand).strip()


def load_pages(pdf_path: str | Path) -> tuple[pymupdf.Document, list[PageCache]]:
    """Open the PDF and build a rotation-normalised, scope-tagged page cache."""
    doc = pymupdf.open(pdf_path)

    pages: list[PageCache] = []
    for i in range(doc.page_count):
        page = doc[i]
        m = page.rotation_matrix
        words = [(pymupdf.Rect(w[:4]) * m, w[4]) for w in page.get_text("words")]
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

    # Majority PROJECT NAME defines the project; anything else is out of scope.
    counts: dict[str, int] = {}
    for pc in pages:
        if pc.project_name:
            counts[pc.project_name] = counts.get(pc.project_name, 0) + 1
    if counts:
        main = max(counts, key=counts.get)
        for pc in pages:
            if pc.project_name and pc.project_name != main:
                pc.analysis_scope = False
                pc.scope_reason = f"FOREIGN_PROJECT:{pc.project_name}"

    return doc, pages


def in_region(r: pymupdf.Rect, region: tuple) -> bool:
    x0, y0, x1, y1 = region
    return x0 <= r.x0 and r.x1 <= x1 and y0 <= r.y0 and r.y1 <= y1
