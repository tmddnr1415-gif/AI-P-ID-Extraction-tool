#!/usr/bin/env python3
"""Phase 0 verification spike #1 — title block parsing (docs/design.md 부록 A).

Extracts, for every page of the P&ID PDF:
    drawing_no    e.g. D00P-10LBA10-M05-0001
    drawing_title e.g. P&ID FOR HP STEAM SYSTEM GROUP 10
    unit_code     KKS unit code, chars 5-6 of the drawing number ('00'|'10'|'11'|...)
    rev           title block REV cell ('A'|'B'|'C'|'D'|'A1'|...)

Why this is not just a text scrape
----------------------------------
The PDF is 100% vector (docs/design.md §0 발견 1) so no OCR is used, but the
title block has two variants in this document set:

* On 10 of 58 pages the small title block text — labels, REV cell, revision
  history — is a real text layer.
* On the other 48 it was plotted in a monoline CAD stroke font, i.e. *vector
  polylines carrying no text at all*.

Drawing number, title and project name are always real Arial text, so those
three fields parse from the text layer on every page.  The REV cell does not.

Two further traps this code is built around:

1. Counting revision history rows is NOT a safe way to derive the revision.
   Pages 7, 9 and 20 carry two history rows (A and B) while the authoritative
   REV cell still reads "A" — those source drawings are internally
   inconsistent.  So the REV cell is *read*, never inferred from row count.

2. Revisions are not always a single letter.  Page 48 — a drawing carried over
   from a different project (PORT DICKSON 1400MW CCGT, not AL NOUF1) — is at
   revision "A1".  The REV cell is therefore segmented into characters rather
   than treated as one glyph.

Reading the stroke font without a font file or OCR
--------------------------------------------------
Glyph shapes are bootstrapped from the document itself:

* Letters come from revision-history REV cells that contain exactly one
  character.  Those rows are filled bottom-up, so row 0 is 'A', row 1 is 'B',
  and so on.
* The digit '1' comes from the SHEET cell, which reads "1/1" on every sheet
  (confirmed against the pages where that cell is real text).

Each glyph is rasterised, cropped to its ink, and area-averaged onto a fixed
grid, which makes matching independent of position, size and stroke weight.
Classification is nearest-template by mean absolute difference.

Usage
-----
    python spike/extract_titleblocks.py --pdf data/pid_total.pdf \
                                        --out out/titleblocks.csv \
                                        --rev-sheet out/rev_cells.png
"""

from __future__ import annotations

import argparse
import csv
import re
import string
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import pymupdf
except ImportError:  # pragma: no cover
    sys.exit("PyMuPDF is required:  pip install pymupdf")

try:
    import numpy as np
except ImportError:  # pragma: no cover
    sys.exit("numpy is required:  pip install numpy")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pidcache import PageCache, in_region, load_pages  # noqa: E402


# --------------------------------------------------------------------------
# Layout
#
# All coordinates are in *display* space (page rotation already applied) for
# the A1 sheet this project uses: 2384 x 1684 pt.  Two pages (7 and 48) are
# stored rotated 270 degrees; page.rotation_matrix maps them into the same
# frame, so no coordinate here needs a special case.
#
# Kept in one dataclass so retargeting to another drawing template is a config
# change rather than a code change (docs/design.md §16).
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Layout:
    # PROJECT DWG NO. cell.
    dwg_no_region: tuple = (1950.0, 1560.0, 2384.0, 1600.0)

    # DRAWING TITLE cell.  The value is set at 15pt+, the "DRAWING TITLE"
    # label at 7pt, so a glyph-height floor separates them.  The lower bound
    # must clear the second line of a wrapped title (descends to y=1570.1 on
    # page 55) while staying above the PROJECT DWG NO. row (y=1576.1 on
    # page 48, the highest that row sits anywhere in the set).
    title_region: tuple = (1960.0, 1500.0, 2384.0, 1574.0)
    title_min_height: float = 15.0
    title_line_tol: float = 6.0

    # REV and SHEET cells, inset to exclude the cell borders
    # (rule at y=1580.7, frame at x=2330.4, dividers at x=2245.8 / 2287.9).
    rev_box: tuple = (2296.0, 1583.0, 2326.0, 1597.0)
    sheet_box: tuple = (2248.0, 1583.0, 2286.0, 1597.0)

    # Revision history table: full-width horizontal rules bound the rows.
    hist_rule_x0_max: float = 1975.0
    hist_rule_x1_min: float = 2320.0
    hist_rule_y: tuple = (1200.0, 1390.0)
    hist_rev_col: tuple = (1971.0, 1988.0)
    hist_date_col: tuple = (1992.0, 2070.0)
    hist_row_inset: float = 1.2

    # Rasterisation and segmentation.
    zoom: float = 24.0
    grid: tuple = (28, 20)          # rows, cols of the normalised bitmap
    ink_frac: float = 0.75          # threshold between darkest pixel and white
    blank_above: int = 245          # cell counts as empty if nothing darker
    min_ink_px: int = 20
    char_gap_px: int = 6            # column gap that separates two characters

    # Confidence from (second-best distance / best distance).
    ratio_high: float = 2.5
    ratio_medium: float = 1.5


LAYOUT = Layout()

DWG_NO_RE = re.compile(r"^[A-Z0-9]{4}-[A-Z0-9]{7}-[A-Z0-9]{3}-\d{4}$")
DATE_RE = re.compile(r"^\d{1,2}\.\s?[A-Z]{3}\.\d{4}$")
REV_TEXT_RE = re.compile(r"^[A-Z][0-9]?$")


# --------------------------------------------------------------------------
# Page access
#
# Coordinates arrive already normalised for page rotation from pidcache
# (docs/design.md §4 설계결정 5), so nothing below needs a rotated-page case.
# --------------------------------------------------------------------------
_HIST_ROWS: dict[int, list[tuple[float, float]]] = {}


def history_rows(pd: PageCache, lay: Layout = LAYOUT) -> list[tuple[float, float]]:
    """Revision history row bands (y0, y1), bottom-most row first."""
    if pd.page_no not in _HIST_ROWS:
        ys = {
            round(r.y0, 1) for r in pd.rects()
            if abs(r.height) < 1.0
            and r.x0 < lay.hist_rule_x0_max
            and r.x1 > lay.hist_rule_x1_min
            and lay.hist_rule_y[0] < r.y0 < lay.hist_rule_y[1]
        }
        rules = sorted(ys)
        _HIST_ROWS[pd.page_no] = list(zip(rules, rules[1:]))[::-1]
    return _HIST_ROWS[pd.page_no]


# --------------------------------------------------------------------------
# Glyph rasterisation, segmentation and matching
# --------------------------------------------------------------------------
def _ink_mask(page, clip: pymupdf.Rect, lay: Layout):
    """Binary ink mask for a cell.

    The stroke font plots in light grey (darkest pixel ~182) while real text is
    black, so the threshold is taken relative to the darkest pixel present.  A
    generous fraction (0.75) is needed: at 0.5 the faintest strokes break up and
    a single 'B' fragments into two apparent characters.
    """
    pm = page.get_pixmap(
        clip=clip,
        matrix=pymupdf.Matrix(lay.zoom, lay.zoom),
        colorspace=pymupdf.csGRAY,
        alpha=False,
    )
    a = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width)
    darkest = int(a.min())
    if darkest > lay.blank_above:
        return None
    mask = a < darkest + lay.ink_frac * (255 - darkest)
    return mask if int(mask.sum()) >= lay.min_ink_px else None


def _normalise(mask, lay: Layout):
    """Crop to ink and area-average onto the fixed grid."""
    ys, xs = np.where(mask)
    if len(ys) == 0:
        return None
    crop = mask[ys.min(): ys.max() + 1, xs.min(): xs.max() + 1].astype(np.float32)
    gh, gw = lay.grid
    yi = (np.arange(gh + 1) * crop.shape[0] / gh).astype(int)
    xi = (np.arange(gw + 1) * crop.shape[1] / gw).astype(int)
    out = np.zeros((gh, gw), np.float32)
    for i in range(gh):
        for j in range(gw):
            blk = crop[yi[i]: max(yi[i] + 1, yi[i + 1]), xi[j]: max(xi[j] + 1, xi[j + 1])]
            if blk.size:
                out[i, j] = float(blk.mean())
    return out


def segment_chars(page, clip: pymupdf.Rect, lay: Layout = LAYOUT) -> list:
    """Split a cell into character bitmaps, left to right."""
    mask = _ink_mask(page, clip, lay)
    if mask is None:
        return []
    cols = mask.any(axis=0)
    groups, start, gap = [], None, 0
    for i, filled in enumerate(cols):
        if filled:
            if start is None:
                start = i
            gap = 0
        elif start is not None:
            gap += 1
            if gap >= lay.char_gap_px:
                groups.append((start, i - gap + 1))
                start, gap = None, 0
    if start is not None:
        groups.append((start, len(cols)))

    out = []
    for a, b in groups:
        sub = mask[:, a:b]
        if int(sub.sum()) < lay.min_ink_px:
            continue
        bm = _normalise(sub, lay)
        if bm is not None:
            out.append(bm)
    return out


def has_titleblock_text(pd: PageCache, lay: Layout = LAYOUT) -> str | None:
    """REV cell contents when the title block carries a real text layer."""
    x0, y0, x1, y1 = lay.rev_box
    for r, t in pd.words:
        if x0 - 2 <= r.x0 <= x1 and y0 - 6 <= r.y0 <= y1 and REV_TEXT_RE.match(t):
            return t
    return None


def build_glyph_library(pages: list[PageCache], lay: Layout = LAYOUT) -> dict:
    """Bootstrap glyph templates from the document itself.

    Templates are kept as a *list per character* rather than one average,
    because this document mixes typefaces: the light monoline stroke font on
    most sheets, plain Arial on the ten text-layer sheets, and a heavier face
    on page 48 (a drawing carried over from another project).  Averaging those
    together would blur every template; keeping them separate and scoring by
    nearest sample lets one character be recognised in any of its faces.
    """
    samples: dict[str, list] = {}

    def add(label: str, bitmap) -> None:
        samples.setdefault(label, []).append(bitmap)

    for pd in pages:
        text_rev = has_titleblock_text(pd, lay)

        if text_rev:
            # Text-layer page: the REV cell string labels its own glyphs.
            chars = segment_chars(pd.page, pymupdf.Rect(*lay.rev_box), lay)
            if len(chars) == len(text_rev):
                for ch, bm in zip(text_rev, chars):
                    add(ch, bm)
        else:
            # Stroke-font page: single-character revision-history cells,
            # labelled by row order (rows fill bottom-up as A, B, C, ...).
            # Rows holding more than one character cannot be labelled this way
            # and are skipped.
            rank = 0
            for y0, y1 in history_rows(pd, lay):
                clip = pymupdf.Rect(
                    lay.hist_rev_col[0], y0 + lay.hist_row_inset,
                    lay.hist_rev_col[1], y1 - lay.hist_row_inset,
                )
                chars = segment_chars(pd.page, clip, lay)
                if not chars:
                    continue
                if len(chars) == 1:
                    add(string.ascii_uppercase[rank], chars[0])
                rank += 1

        # Digit '1': the SHEET cell reads "1/1" on every sheet of this set,
        # which the text-layer pages confirm.
        sheet = segment_chars(pd.page, pymupdf.Rect(*lay.sheet_box), lay)
        if len(sheet) == 3:
            add("1", sheet[0])
            add("1", sheet[2])

    return samples


def classify(bitmap, library: dict, lay: Layout = LAYOUT):
    """Nearest-sample match over all templates of each character.

    Returns (label, best_d, ratio), where ratio is best_d of the runner-up
    *character* over best_d — a margin, not a distance, so it stays meaningful
    across the different stroke weights in this document.
    """
    if not library:
        return None, float("nan"), 0.0
    scored = sorted(
        (min(float(np.abs(bitmap - tpl).mean()) for tpl in tpls), lab)
        for lab, tpls in library.items()
    )
    best_d, best = scored[0]
    if len(scored) == 1:
        return best, best_d, float("inf")
    ratio = scored[1][0] / best_d if best_d > 0 else float("inf")
    return best, best_d, ratio


def read_rev_glyphs(pd: PageCache, library: dict, lay: Layout = LAYOUT):
    """Read the REV cell character by character.  Returns (rev, conf, detail)."""
    chars = segment_chars(pd.page, pymupdf.Rect(*lay.rev_box), lay)
    if not chars:
        return None, "NONE", "REV cell is empty"

    labels, ratios, dists = [], [], []
    for bm in chars:
        lab, d, ratio = classify(bm, library, lay)
        labels.append(lab or "?")
        ratios.append(ratio)
        dists.append(d)

    worst = min(ratios) if ratios else 0.0
    if "?" in labels:
        conf = "LOW"
    elif worst >= lay.ratio_high:
        conf = "HIGH"
    elif worst >= lay.ratio_medium:
        conf = "MEDIUM"
    else:
        conf = "LOW"
    detail = "%d char(s); d=%s ratio=%s" % (
        len(chars),
        ",".join(f"{x:.4f}" for x in dists),
        ",".join("inf" if x == float("inf") else f"{x:.2f}" for x in ratios),
    )
    return "".join(labels), conf, detail


# --------------------------------------------------------------------------
# Field parsers
# --------------------------------------------------------------------------
def parse_drawing_no(pd: PageCache, lay: Layout = LAYOUT) -> str | None:
    """Drawing number from the PROJECT DWG NO. cell.

    Region-anchored on purpose: the same pattern appears all over the sheet in
    off-page connectors (docs/design.md §7), so a page-wide regex would happily
    return the wrong drawing.
    """
    hits = [
        (r.x0, t) for r, t in pd.words
        if DWG_NO_RE.match(t) and in_region(r, lay.dwg_no_region)
    ]
    return min(hits)[1] if hits else None


def parse_title(pd: PageCache, lay: Layout = LAYOUT) -> str | None:
    """Drawing title, joined across lines when the cell wraps (e.g. page 48)."""
    cand = [
        (r, t) for r, t in pd.words
        if in_region(r, lay.title_region)
        and r.height >= lay.title_min_height
        and not DWG_NO_RE.match(t)   # belt and braces: never absorb the DWG NO. row
    ]
    if not cand:
        return None
    cand.sort(key=lambda rt: (round(rt[0].y0 / lay.title_line_tol), rt[0].x0))
    return " ".join(t for _, t in cand).strip()


def parse_unit_code(drawing_no: str | None) -> str | None:
    """KKS unit code — chars 5-6 of the drawing number (docs/design.md §4).

    'D00P-10LBA10-M05-0001' -> '10'.  Ignoring separators the number reads
    D00P 10LBA10 ..., so the unit code is the first two characters of the
    second segment.
    """
    if not drawing_no:
        return None
    parts = drawing_no.split("-")
    if len(parts) < 2 or len(parts[1]) < 2:
        return None
    return parts[1][:2]


def parse_rev_date(pd: PageCache, rev: str | None, lay: Layout = LAYOUT) -> str | None:
    """Date of the current revision, where the history table is real text."""
    if not rev:
        return None
    rank = 0
    for y0, y1 in history_rows(pd, lay):
        clip = pymupdf.Rect(
            lay.hist_rev_col[0], y0 + lay.hist_row_inset,
            lay.hist_rev_col[1], y1 - lay.hist_row_inset,
        )
        if not segment_chars(pd.page, clip, lay):
            continue
        if string.ascii_uppercase[rank] == rev:
            for r, t in pd.words:
                if (
                    lay.hist_date_col[0] <= r.x0 <= lay.hist_date_col[1]
                    and y0 < r.y0 < y1
                    and DATE_RE.match(t)
                ):
                    return t
        rank += 1
    return None


def classify_page(title: str | None, drawing_no: str | None) -> str:
    t = (title or "").upper()
    if "DRAWING LIST" in t:
        return "DRAWING_LIST"
    if "SYMBOL" in t or "LEGEND" in t:
        return "LEGEND"
    return "PID" if drawing_no else "UNKNOWN"


# --------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------
def extract_page(pd: PageCache, library: dict, lay: Layout = LAYOUT) -> dict:
    drawing_no = parse_drawing_no(pd, lay)
    title = parse_title(pd, lay)
    unit_code = parse_unit_code(drawing_no)

    rev = has_titleblock_text(pd, lay)
    if rev:
        rev_method, rev_conf, rev_detail = "TEXT", "HIGH", "read from text layer"
    else:
        rev, rev_conf, rev_detail = read_rev_glyphs(pd, library, lay)
        rev_method = "GLYPH" if rev else "NONE"

    rev_date = parse_rev_date(pd, rev, lay)

    issues = []
    for name, val in (("drawing_no", drawing_no), ("drawing_title", title),
                      ("unit_code", unit_code), ("rev", rev)):
        if not val:
            issues.append(name)
    if rev and rev_conf == "LOW":
        issues.append("rev_low_confidence")

    if not (drawing_no and title and unit_code and rev):
        status = "FAIL"
    elif rev_conf == "LOW":
        status = "REVIEW"
    else:
        status = "OK"

    return {
        "page_no": pd.page_no,
        "drawing_no": drawing_no or "",
        "drawing_title": title or "",
        "unit_code": unit_code or "",
        "rev": rev or "",
        "rev_date": rev_date or "",
        "rev_method": rev_method,
        "rev_confidence": rev_conf,
        "rev_detail": rev_detail,
        "page_kind": classify_page(title, drawing_no),
        "project_name": pd.project_name,
        "analysis_scope": pd.analysis_scope,
        "scope_reason": pd.scope_reason,
        "rotation": pd.source_rotation,
        "status": status,
        "issues": ";".join(issues),
    }


FIELDNAMES = [
    "page_no", "drawing_no", "drawing_title", "unit_code", "rev", "rev_date",
    "rev_method", "rev_confidence", "rev_detail", "page_kind", "project_name",
    "analysis_scope", "scope_reason", "rotation", "status", "issues",
]


def dump_rev_sheet(pages: list[PageCache], rows, path: Path, lay: Layout = LAYOUT) -> None:
    """Contact sheet of every REV cell, labelled with what was read.

    Phase 0 is a verification spike, and the REV cell is the one field that
    cannot be cross-checked against the text layer on most pages — so it gets
    laid out for a human to confirm in one glance.
    """
    cols, cw, ch = 10, 110, 80
    out = pymupdf.open()
    sheet = out.new_page(width=cols * cw, height=((len(rows) + cols - 1) // cols) * ch)
    for i, row in enumerate(rows):
        pm = pages[i].page.get_pixmap(
            clip=pymupdf.Rect(lay.rev_box[0] + 2, lay.rev_box[1] + 1,
                              lay.rev_box[2] - 6, lay.rev_box[3] - 1),
            matrix=pymupdf.Matrix(8, 8), colorspace=pymupdf.csGRAY, alpha=False,
        )
        cx, cy = (i % cols) * cw, (i // cols) * ch
        box = pymupdf.Rect(cx + 5, cy + 18, cx + cw - 5, cy + ch - 5)
        sheet.insert_image(box, pixmap=pm)
        sheet.draw_rect(box, width=0.4)
        sheet.insert_text(
            (cx + 6, cy + 13),
            "p%d -> %s %s" % (row["page_no"], row["rev"] or "?", row["rev_confidence"][:1]),
            fontsize=8,
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.get_pixmap(matrix=pymupdf.Matrix(2, 2)).save(str(path))


def report(rows, library: dict, out_path: Path) -> None:
    n = len(rows)
    # Aggregates cover in-scope pages only (docs/design.md §4 설계결정 6);
    # out-of-scope pages are still parsed, stored and listed, just not counted.
    scoped = [r for r in rows if r["analysis_scope"]]
    out_of_scope = [r for r in rows if not r["analysis_scope"]]
    ns = len(scoped)
    pct = lambda k: 100.0 * k / ns if ns else 0.0            # noqa: E731
    filled = lambda f: sum(1 for r in scoped if r[f])        # noqa: E731

    print(f"\n=== Title block parsing — {n} pages ({ns} in scope) -> {out_path} ===\n")
    lib_desc = ", ".join(f"{k}x{len(v)}" for k, v in sorted(library.items()))
    print(f"glyph library bootstrapped: {lib_desc}\n")
    print("field           parsed      rate")
    print("-" * 36)
    for f in ("drawing_no", "drawing_title", "unit_code", "rev", "rev_date"):
        c = filled(f)
        print(f"{f:<15} {c:>3}/{ns:<3}  {pct(c):6.1f}%")

    print("\nrev source:")
    for m in ("TEXT", "GLYPH", "NONE"):
        pgs = [r["page_no"] for r in scoped if r["rev_method"] == m]
        if pgs:
            print(f"  {m:<6} {len(pgs):>3}")

    print("\nrev confidence:")
    for c_ in ("HIGH", "MEDIUM", "LOW", "NONE"):
        pgs = [str(r["page_no"]) for r in scoped if r["rev_confidence"] == c_]
        if pgs:
            extra = f"   pages {', '.join(pgs)}" if c_ != "HIGH" else ""
            print(f"  {c_:<6} {len(pgs):>3}{extra}")

    print("\nrev distribution:")
    dist: dict[str, int] = {}
    for r in scoped:
        dist[r["rev"] or "(none)"] = dist.get(r["rev"] or "(none)", 0) + 1
    for k in sorted(dist):
        print(f"  {k:<8} {dist[k]:>3}")

    print("\nunit_code distribution:")
    dist = {}
    for r in scoped:
        dist[r["unit_code"] or "(none)"] = dist.get(r["unit_code"] or "(none)", 0) + 1
    for k in sorted(dist):
        print(f"  {k:<8} {dist[k]:>3}")

    print("\npage_kind:")
    dist = {}
    for r in scoped:
        dist[r["page_kind"]] = dist.get(r["page_kind"], 0) + 1
    for k in sorted(dist):
        print(f"  {k:<14} {dist[k]:>3}")

    if out_of_scope:
        print("\nOUT OF SCOPE (parsed and stored, excluded from the counts above):")
        for r in out_of_scope:
            print(f"  page {r['page_no']:>3}  {r['scope_reason']}")
            print(f"           {r['drawing_no']}  rev {r['rev']}  {r['drawing_title']}")

    # Duplicate drawing numbers are why pid_page keys off page_no, not
    # drawing_no (docs/design.md §4 설계결정 4).
    seen: dict[str, list] = {}
    for r in rows:
        if r["drawing_no"]:
            seen.setdefault(r["drawing_no"], []).append(r["page_no"])
    dupes = {k: v for k, v in seen.items() if len(v) > 1}

    fails = [r for r in rows if r["status"] == "FAIL"]
    review = [r for r in rows if r["status"] == "REVIEW"]

    print("\n" + "-" * 36)
    if fails:
        print(f"PARSE FAILURES: {len(fails)} page(s)")
        for r in fails:
            print(f"  page {r['page_no']:>3}  missing: {r['issues']}")
    else:
        print(f"PARSE FAILURES: none — {n}/{n} pages fully parsed")

    if review:
        print(f"\nNEEDS REVIEW: {len(review)} page(s)")
        for r in review:
            print(f"  page {r['page_no']:>3}  {r['issues']}  [{r['rev_detail']}]")

    if dupes:
        print(f"\nDUPLICATE drawing_no: {len(dupes)}")
        for k, v in sorted(dupes.items()):
            print(f"  {k}  pages {v}")
            for pno in v:
                print(f"      p{pno}: {rows[pno - 1]['drawing_title']}")
    print()


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 0 spike 1 — title block parsing")
    ap.add_argument("--pdf", default="data/pid_total.pdf")
    ap.add_argument("--out", default="out/titleblocks.csv")
    ap.add_argument("--rev-sheet", default=None,
                    help="write a PNG contact sheet of every REV cell for visual check")
    args = ap.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        sys.exit(f"PDF not found: {pdf_path}")

    doc, pages = load_pages(pdf_path)

    library = build_glyph_library(pages)
    rows = [extract_page(pd, library) for pd in pages]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)

    if args.rev_sheet:
        dump_rev_sheet(pages, rows, Path(args.rev_sheet))

    report(rows, library, out_path)
    return 0 if all(r["status"] != "FAIL" for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
