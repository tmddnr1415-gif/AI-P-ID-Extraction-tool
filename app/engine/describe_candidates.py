"""Text that could be an instrument's middle description, collected by rule.

The previous round measured why a radius does not work: half the client's
Description tokens sit more than 240 pt from their symbol on a 2384 pt sheet, and
widening the circle to catch them drops token precision from 57.3% to 17.6%,
because a 240 pt circle holds drawing numbers, DN sizes, grid references and ASME
codes.  So this does not use a radius.

It uses the drawing's own connectivity instead: an instrument hangs off a leader,
the leader lands on a pipe run, and what the drawing writes *about that run* -
its label, the off-page connector it goes to, the equipment box it ends at, the
local unit marking beside it - is what the client's middle segment names.  The
run comes from `pipe_graph`, which is measured off the legend; the only tolerance
here is how far a label sits from the line it labels, and that is taken as the
median text height of the page it is on, which is a measurement of that page.

Nothing here selects, ranks by preference or writes a sentence.  It hands every
candidate over with its distance, its direction and where it came from, and the
caller decides - see `describe_llm` for the selector and `pipeline` for the
grading.  A symbol whose run carries no text at all yields nothing, and that is a
reportable outcome rather than a reason to widen anything.
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipe_graph  # noqa: E402

# Where a candidate came from.  The kind matters to the grading: a connector or an
# equipment box *names a thing*, which is what the client's middle segment does; a
# line label may be a size or a spec instead.
PIPE_LABEL = "PIPE_LABEL"
CONNECTOR = "CONNECTOR"
EQUIPMENT = "EQUIPMENT"
UNIT_MARK = "UNIT_MARK"
NAMED_KINDS = (CONNECTOR, EQUIPMENT)

# A local unit marking - `HRSG#11`, `#12`.  The client writes `UNIT #11` where the
# sheet's own unit code says 10, so this is the only place that number can come
# from; it is recognised by the mark the drawing prints, not by a list of names.
UNIT_MARK_CHAR = "#"


def band_width(pc) -> float:
    """How far a label sits from the line it labels: this page's text height.

    Measured, not chosen.  A drawing sets its labels a line's height off the run,
    so the page's own median glyph height is the distance that matters, and it
    varies between sheets - which is why it is measured per page rather than once.
    """
    heights = sorted(r.y1 - r.y0 for r, _t in pc.words if r.y1 > r.y0)
    return heights[len(heights) // 2] if heights else 0.0


def collect(pc, g, drawing_area, traces=None) -> dict:
    """`{row_key: [candidate, ...]}` for every symbol in the graph.

    A candidate is `{"text", "kind", "distance", "direction", "rect", "run"}`.
    Distances are Chebyshev from the symbol's centre, in points, so a caller can
    order them without another measurement.

    `traces` is `{row_key: trace}` from `pipe_graph.trace`, and it is the second
    way a terminal reaches a symbol: the run the instrument sits on may reach an
    off-page connector several junctions away, which is the same evidence as one
    that touches it directly - the drawing says the pipe goes there.  Passing it is
    optional; without it only terminals on the first run are offered.
    """
    half = band_width(pc)
    words = [(r, t) for r, t in pc.words
             if drawing_area[0] <= r.x0 and r.x1 <= drawing_area[2]
             and drawing_area[1] <= r.y0 and r.y1 <= drawing_area[3]]
    # A coarse grid so the band test does not walk 2,000 words per run.
    cell = 64.0
    grid = collections.defaultdict(list)
    for r, t in words:
        grid[int((r.x0 + r.x1) / 2 / cell), int((r.y0 + r.y1) / 2 / cell)].append((r, t))

    terminals = [(n["rect"], n["label"],
                  CONNECTOR if n["kind"] == "CONNECTOR" else EQUIPMENT)
                 for n in g.nodes.values()
                 if n["kind"] in ("CONNECTOR", "EQUIPMENT") and n["rect"]]

    out = {}
    for nid, node in g.nodes.items():
        if node["kind"] != "SYMBOL" or not node.get("row_key"):
            continue
        cx, cy = node["x"], node["y"]
        # The first pipe runs: the edges of the junctions this symbol is on.
        runs = []
        for jid, _link in g.adj[nid]:
            if g.nodes[jid]["kind"] != "JUNCTION":
                continue
            for nb, run in g.adj[jid]:
                if g.nodes[nb]["kind"] == "SYMBOL":
                    continue
                runs.append(run)
        seen, cands = set(), []
        for run in runs:
            for r, t in _in_band(run, half, grid, cell):
                key = (t, round(r.x0, 1), round(r.y0, 1))
                if key in seen or not any(c.isalnum() for c in t):
                    continue
                seen.add(key)
                cands.append({
                    "text": t,
                    "kind": UNIT_MARK if UNIT_MARK_CHAR in t else PIPE_LABEL,
                    "distance": round(max(abs((r.x0 + r.x1) / 2 - cx),
                                          abs((r.y0 + r.y1) / 2 - cy)), 1),
                    "direction": _direction((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2, cx, cy),
                    "rect": [round(v, 1) for v in (r.x0, r.y0, r.x1, r.y1)],
                    "run": [round(v, 1) for v in run],
                })
            # a terminal whose own box the run reaches
            for rect, label, kind in terminals:
                if not label or not _rect_near_run(rect, run, half):
                    continue
                key = (label, round(rect[0], 1), round(rect[1], 1))
                if key in seen:
                    continue
                seen.add(key)
                cands.append({
                    "text": label, "kind": kind,
                    "distance": round(max(abs((rect[0] + rect[2]) / 2 - cx),
                                          abs((rect[1] + rect[3]) / 2 - cy)), 1),
                    "direction": _direction((rect[0] + rect[2]) / 2,
                                            (rect[1] + rect[3]) / 2, cx, cy),
                    "rect": [round(v, 1) for v in rect],
                    "run": [round(v, 1) for v in run],
                })
        # Terminals the walk reached along this pipe, if the caller traced it.
        for t in _traced_terminals(traces, node.get("row_key")):
            if not t.get("label"):
                continue
            rect = t.get("rect") or [cx, cy, cx, cy]
            key = (t["label"], round(rect[0], 1), round(rect[1], 1))
            if key in seen:
                continue
            seen.add(key)
            cands.append({
                "text": t["label"],
                "kind": CONNECTOR if t["kind"] == "CONNECTOR" else EQUIPMENT,
                "distance": round(max(abs((rect[0] + rect[2]) / 2 - cx),
                                      abs((rect[1] + rect[3]) / 2 - cy)), 1),
                "direction": _direction((rect[0] + rect[2]) / 2,
                                        (rect[1] + rect[3]) / 2, cx, cy),
                "rect": [round(v, 1) for v in rect],
                "run": [],
            })
        cands.sort(key=lambda c: c["distance"])
        out[node["row_key"]] = cands
    return out


def _traced_terminals(traces, row_key) -> list:
    tr = (traces or {}).get(row_key) or {}
    return [t for bucket in ("upstream", "downstream", "undirected")
            for t in (tr.get(bucket) or [])]


def _in_band(run, half, grid, cell):
    """Words lying along a run, within a label's height of it."""
    x0, y0, x1, y1 = run
    lo_x, hi_x = min(x0, x1) - half, max(x0, x1) + half
    lo_y, hi_y = min(y0, y1) - half, max(y0, y1) + half
    out = []
    for gx in range(int(lo_x / cell), int(hi_x / cell) + 1):
        for gy in range(int(lo_y / cell), int(hi_y / cell) + 1):
            for r, t in grid.get((gx, gy), ()):
                mx, my = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
                if lo_x <= mx <= hi_x and lo_y <= my <= hi_y:
                    out.append((r, t))
    return out


def _rect_near_run(rect, run, half) -> bool:
    x0, y0, x1, y1 = run
    return not (rect[2] < min(x0, x1) - half or rect[0] > max(x0, x1) + half
                or rect[3] < min(y0, y1) - half or rect[1] > max(y0, y1) + half)


def _direction(x, y, cx, cy) -> str:
    """Which way the text lies from the symbol, in the drawing's own axes."""
    dx, dy = x - cx, y - cy
    if abs(dx) >= abs(dy):
        return "RIGHT" if dx > 0 else "LEFT"
    return "BELOW" if dy > 0 else "ABOVE"


def group_lines(cands) -> list:
    """Adjacent words on one line joined, so a candidate is a phrase not a word.

    The drawing writes `TO CLEAN DRAIN TANK` as four words on one baseline; asking
    a selector to pick words one at a time would let it assemble a phrase the
    drawing never printed.  Words are joined only when they share a baseline and
    sit within a space of each other, both read off the words themselves.
    """
    by_line = collections.defaultdict(list)
    for c in cands:
        by_line[c["kind"], round(c["rect"][1], 0)].append(c)
    out = []
    for (kind, _y), group in by_line.items():
        group.sort(key=lambda c: c["rect"][0])
        run = [group[0]]
        for c in group[1:]:
            gap = c["rect"][0] - run[-1]["rect"][2]
            width = max(1.0, run[-1]["rect"][2] - run[-1]["rect"][0])
            per_char = width / max(1, len(run[-1]["text"]))
            if gap <= per_char * 1.5:
                run.append(c)
            else:
                out.append(_join(run, kind))
                run = [c]
        out.append(_join(run, kind))
    out.sort(key=lambda c: c["distance"])
    return out


def _join(run, kind) -> dict:
    return {
        "text": " ".join(c["text"] for c in run),
        "kind": kind,
        "distance": min(c["distance"] for c in run),
        "direction": run[0]["direction"],
        "rect": [min(c["rect"][0] for c in run), min(c["rect"][1] for c in run),
                 max(c["rect"][2] for c in run), max(c["rect"][3] for c in run)],
        "run": run[0]["run"],
    }
