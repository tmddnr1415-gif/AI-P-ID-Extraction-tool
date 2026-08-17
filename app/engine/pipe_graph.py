"""Pipe connectivity as a graph, and nothing more.

Description is the column Phase 0 called the highest-risk module, because writing
it needs to know what a symbol is connected to.  This builds that connectivity
and stops there: nodes, edges, and for each detected symbol the terminals reached
in each direction.  **No sentence is generated and no wording is inferred** - the
terminals are reported as the drawing's own words and the caller decides what, if
anything, to do with them.

What is derived rather than chosen
----------------------------------

* **What a signal line is.**  Legend page 3's ELECTRIC SIGNAL row is drawn as 13
  pieces of 7.2 pt separated by 3.6 pt gaps; page 2's MAIN PROCESS LINE is one
  continuous 138.8 pt run.  So the distinction is measurable: a chain of collinear
  pieces at the legend's dash and gap is a signal line, a continuous run is pipe.
  Signal lines are kept in their own layer, never traced as pipe.

* **The shortest run that can connect anything.**  Legend page 2 draws its line
  valve 17.0 pt long; a run shorter than the valve it feeds cannot join two
  things, and below that everything is glyph and hatching tessellation - a single
  sheet carries 150k segments, of which 383 are longer than the valve.

* **How close two runs must be to be joined.**  The coordinate slack the stroke
  index already carries, as `legend_rules.covers` uses it.  Not a new allowance.

Node kinds
----------

    CONNECTOR   an off-page reference the drawing prints as `TO <name>` or
                `FROM <name>`.  These carry direction: FROM is upstream and TO is
                downstream, in the drawing's own words rather than by inference.
    EQUIPMENT   a closed box larger than any symbol the legend draws
    SYMBOL      a detection handed in by the caller
    JUNCTION    a point where pipe runs meet

No LLM, no NOTES prose.
"""

from __future__ import annotations

import collections
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import legend_rules  # noqa: E402
import projectconfig  # noqa: E402

# The legend sheets these are measured from, by their printed words.
SIGNAL_ROW = "ELECTRIC SIGNAL"
PROCESS_ROW = "MAIN PROCESS LINE"

# An off-page reference starts with the drawing's own preposition.  Direction
# comes from the word itself, which is why nothing here has to guess flow.
CONNECTOR_RE = re.compile(r"^(TO|FROM)\b(.+)$")
UPSTREAM_WORD, DOWNSTREAM_WORD = "FROM", "TO"

# How far a walk may go before it is called ambiguous rather than followed
# forever.  This is a budget, not a measurement, and it is reported as one: a
# trace that hits it is classified FAILED with `reason="budget"` rather than
# silently truncated.
WALK_BUDGET = 600
MAX_CANDIDATES = 4


@dataclass
class Graph:
    page_no: int
    nodes: dict = field(default_factory=dict)       # id -> node dict
    edges: list = field(default_factory=list)       # (a_id, b_id, run)
    adj: dict = field(default_factory=lambda: collections.defaultdict(list))
    signal_runs: list = field(default_factory=list)
    style: dict = field(default_factory=dict)

    def stats(self) -> dict:
        kinds = collections.Counter(n["kind"] for n in self.nodes.values())
        return {"page_no": self.page_no, "nodes": len(self.nodes),
                "edges": len(self.edges), "by_kind": dict(kinds),
                "signal_runs": len(self.signal_runs)}


def derive_line_styles(pages, cfg=None) -> "legend_rules.Derived":
    """Measure what a signal line looks like, off the legend that draws one."""
    cfg = cfg or projectconfig.load()
    pc = legend_rules._page_with(pages, SIGNAL_ROW)
    if pc is None:
        return legend_rules._fallback(
            cfg, "line_styles", f"no legend sheet prints '{SIGNAL_ROW}'")
    label = None
    for r, t in pc.words:
        if t == "SIGNAL":
            row = [w for _r, w in pc.words
                   if abs((_r.y0 + _r.y1) / 2 - (r.y0 + r.y1) / 2) < 6]
            if "ELECTRIC" in row:
                label = r
                break
    if label is None:
        return legend_rules._fallback(
            cfg, "line_styles", f"'{SIGNAL_ROW}' row not found on p{pc.page_no}")

    horiz, _vert = legend_rules.stroke_index(pc.segments(), min_len=0.4)
    yc = (label.y0 + label.y1) / 2
    pieces = sorted((a, b) for y, runs in horiz.items() if abs(y - yc) < 6
                    for a, b in runs if b < label.x0 and label.x0 - a < 200)
    lens = [b - a for a, b in pieces]
    gaps = [pieces[i + 1][0] - pieces[i][1] for i in range(len(pieces) - 1)]
    dashes = sorted(L for L in lens if L > 1.0)
    spaces = sorted(g for g in gaps if g > 1.0)
    if len(dashes) < 3 or not spaces:
        return legend_rules._fallback(
            cfg, "line_styles",
            f"the {SIGNAL_ROW} row on p{pc.page_no} has {len(dashes)} dash(es) "
            f"and {len(spaces)} gap(s), too few to measure a pattern")

    # The shortest run that can join two things: the legend's own line valve.
    bf = legend_rules.derive_butterfly(pages, cfg)
    valve = float(bf.values.get("circle_diameter") or 0) * 2.8 if bf.values else 0.0
    def repeated(values):
        """The length that repeats.  A dashed line is defined by its repetition,
        so the mode is the measurement - a mean is dragged off by the row's
        lead-in stroke and a median by however many short pieces share the band."""
        counts = collections.Counter(round(v, 1) for v in values)
        return max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]

    return legend_rules.Derived(
        values={
            "dash_len": repeated(dashes),
            "dash_gap": repeated(spaces),
            # Legend p2 draws the bowtie between end bars 2.8 radii apart, which
            # is the same 17.0 pt `detect_valves` measures for the body.
            "min_run": round(valve, 3) if valve else round(
                sum(dashes) / len(dashes) * 2.4, 3),
            "join_slack": legend_rules.INDEX_SLACK,
        },
        evidence={"page_no": pc.page_no,
                  "dash_histogram": dict(collections.Counter(
                      round(v, 1) for v in dashes).most_common(5)),
                  "gap_histogram": dict(collections.Counter(
                      round(v, 1) for v in spaces).most_common(5)),
                  "min_run_from": "legend p2 line-valve length"
                                  if valve else "2.4 x the signal dash"})


def derive_connector_reach(pages, style, drawing_area, cfg=None):
    """How far a connector's text sits from the pipe that feeds it, measured.

    The legend does not draw the off-page connector at all: pages 2-5 print no
    OFF-PAGE, CONTINUATION, MATCH LINE or CONNECTOR row, and the only interface
    symbol they do define (SUPPLIER INTERFACE) is a solid line crossed by a
    31.2 pt bar, which is a different thing.  So the contact point cannot be
    derived from the legend, and the flag has no closed outline to measure either
    - its edges are separate dashed strokes.

    What *is* measurable is the drawing's own habit: on every connector in the
    document, how far the printed text is from the nearest pipe-run endpoint.
    That distribution is measured here and the reach is its high end, so the
    number is a measurement of this document rather than a radius someone picked.
    A connector whose flag is longer than that stays unattached, and the rows
    that needed it report FAILED - which is the honest outcome, not a silent one.
    """
    cfg = cfg or projectconfig.load()
    seen = []
    for pc in pages:
        if not pc.analysis_scope:
            continue
        labels = _connector_labels(pc, drawing_area)
        if not labels:
            continue
        horiz, vert = legend_rules.stroke_index(pc.segments(), min_len=1.0)
        ends = []
        for axis, index in (("H", horiz), ("V", vert)):
            for coord, runs in index.items():
                for a, b in runs:
                    if b - a < style["min_run"]:
                        continue
                    ends += ([(a, coord), (b, coord)] if axis == "H"
                             else [(coord, a), (coord, b)])
        for rect, _text in labels:
            cx, cy = (rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2
            d = min((max(abs(px - cx), abs(py - cy)) for px, py in ends),
                    default=None)
            if d is not None:
                seen.append(d)
    if not seen:
        return legend_rules._fallback(
            cfg, "connector_reach",
            "no connector text and pipe run appear on the same page")
    seen.sort()
    # The high end of the measured distribution, not the maximum: one connector
    # printed far from its flag would otherwise set the reach for all of them.
    reach = seen[int(len(seen) * 0.9)]
    hist = collections.Counter(int(d // 5) * 5 for d in seen)
    return legend_rules.Derived(
        values={"connector_reach": round(reach, 1)},
        source="MEASURED",
        note=f"the legend draws no off-page connector, so this is measured from "
             f"{len(seen)} connectors in this document",
        evidence={"connectors": len(seen),
                  "min": round(seen[0], 1), "median": round(seen[len(seen) // 2], 1),
                  "p90": round(reach, 1), "max": round(seen[-1], 1),
                  "histogram_5pt": dict(sorted(hist.items()))})


def _merge_runs(index, min_len: float, slack: float):
    """Collinear pieces unioned into runs, and the dashed chains kept apart.

    Returns `(runs, chains)` where a run is `(coord, lo, hi)` and a chain is the
    list of pieces that made up a dashed line.
    """
    runs, chains = [], []
    for coord, pieces in index.items():
        pieces = sorted(pieces)
        group = [pieces[0]]
        for a, b in pieces[1:]:
            if a - group[-1][1] <= slack:
                group.append((min(a, group[-1][0]), max(b, group[-1][1]))
                             if a <= group[-1][1] else (a, b))
            else:
                _emit(coord, group, runs, chains, min_len)
                group = [(a, b)]
        _emit(coord, group, runs, chains, min_len)
    return runs, chains


def _emit(coord, group, runs, chains, min_len):
    lo = min(a for a, _b in group)
    hi = max(b for _a, b in group)
    if hi - lo >= min_len:
        runs.append((coord, lo, hi))


def _dashed_chains(index, style, min_len):
    """Collinear pieces at the legend's dash and gap: a signal line."""
    dash, gap = style["dash_len"], style["dash_gap"]
    tol = style["join_slack"]
    out = []
    for coord, pieces in index.items():
        pieces = sorted(pieces)
        run = [pieces[0]]
        for a, b in pieces[1:]:
            prev_gap = a - run[-1][1]
            if abs(prev_gap - gap) <= dash * 0.5 and abs((b - a) - dash) <= dash * 0.5:
                run.append((a, b))
                continue
            if len(run) >= 3:
                out.append((coord, run[0][0], run[-1][1], len(run)))
            run = [(a, b)]
        if len(run) >= 3:
            out.append((coord, run[0][0], run[-1][1], len(run)))
    return [c for c in out if c[2] - c[1] >= min_len and abs(tol) >= 0]


def build(pc, symbols, style: dict, drawing_area) -> Graph:
    """Graph for one page.  `symbols` is `[(key, rect, label)]` from the caller."""
    g = Graph(page_no=pc.page_no, style=dict(style))
    min_run, slack = style["min_run"], style["join_slack"]
    horiz, vert = legend_rules.stroke_index(pc.segments(), min_len=1.0)

    # 1. signal lines first, so their pieces are not also read as pipe
    h_chains = _dashed_chains(horiz, style, min_run)
    v_chains = _dashed_chains(vert, style, min_run)
    g.signal_runs = [{"axis": axis, "coord": round(c, 1), "lo": round(lo, 1),
                      "hi": round(hi, 1), "pieces": n}
                     for axis, chains in (("H", h_chains), ("V", v_chains))
                     for c, lo, hi, n in chains]
    covered = {(axis, round(c, 1), round(lo, 1), round(hi, 1))
               for axis, chains in (("H", h_chains), ("V", v_chains))
               for c, lo, hi, _n in chains}

    def inside(x, y):
        return (drawing_area[0] <= x <= drawing_area[2]
                and drawing_area[1] <= y <= drawing_area[3])

    # A node table with a tolerant lookup.  Rounding coordinates to a grid is not
    # enough on its own: two runs meeting at the same corner can sit either side
    # of a bucket boundary and become two nodes, which is what left the graph in
    # 400 fragments and every trace failing after ten steps.
    grid = {}

    def add_node(x, y, kind, label="", rect=None):
        if kind == "JUNCTION":
            gx, gy = int(x / slack), int(y / slack)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for nid in grid.get((gx + dx, gy + dy), ()):
                        n = g.nodes[nid]
                        if abs(n["x"] - x) <= slack and abs(n["y"] - y) <= slack:
                            return nid
            nid = f"j{len(g.nodes)}"
            grid.setdefault((gx, gy), []).append(nid)
        else:
            nid = f"{kind[0]}{len(g.nodes)}"
        g.nodes[nid] = {"id": nid, "kind": kind, "label": label,
                        "x": round(x, 1), "y": round(y, 1),
                        "rect": [round(v, 1) for v in rect] if rect else []}
        return nid

    # 2. pipe runs.  A run is one edge only if nothing lands in the middle of it;
    #    where another run *ends* on it the drawing means a tee, so it is split
    #    there.  Where two runs merely cross, the drawing means one passing over
    #    the other and nothing is joined - that distinction is the whole reason
    #    this is built from endpoints rather than from every intersection.
    runs = []
    for axis, index in (("H", horiz), ("V", vert)):
        for coord, lo, hi in _merge_runs(index, min_run, slack)[0]:
            if (axis, round(coord, 1), round(lo, 1), round(hi, 1)) in covered:
                continue                     # a signal line, not pipe
            p0 = (lo, coord) if axis == "H" else (coord, lo)
            p1 = (hi, coord) if axis == "H" else (coord, hi)
            if not (inside(*p0) or inside(*p1)):
                continue
            runs.append({"axis": axis, "coord": coord, "lo": lo, "hi": hi,
                         "cuts": {lo, hi}})

    by_coord = {"H": collections.defaultdict(list), "V": collections.defaultdict(list)}
    for i, r in enumerate(runs):
        by_coord[r["axis"]][int(r["coord"] / slack)].append(i)

    def ends_on(axis, coord, pos):
        """Runs of the other axis whose interior this endpoint lands on."""
        other = "V" if axis == "H" else "H"
        out = []
        for d in (-1, 0, 1):
            for i in by_coord[other].get(int(pos / slack) + d, ()):
                r = runs[i]
                if abs(r["coord"] - pos) > slack:
                    continue
                if r["lo"] - slack <= coord <= r["hi"] + slack:
                    out.append(i)
        return out

    for r in runs:
        for pos in (r["lo"], r["hi"]):
            for i in ends_on(r["axis"], r["coord"], pos):
                runs[i]["cuts"].add(r["coord"])

    for r in runs:
        cuts = sorted(c for c in r["cuts"] if r["lo"] - slack <= c <= r["hi"] + slack)
        prev = None
        for c in cuts:
            x, y = (c, r["coord"]) if r["axis"] == "H" else (r["coord"], c)
            nid = add_node(x, y, "JUNCTION")
            if prev is not None and prev != nid:
                run = [g.nodes[prev]["x"], g.nodes[prev]["y"],
                       g.nodes[nid]["x"], g.nodes[nid]["y"]]
                g.edges.append((prev, nid, run))
                g.adj[prev].append((nid, run))
                g.adj[nid].append((prev, run))
            prev = nid

    # 3. terminals: off-page connectors and equipment boxes
    for rect, text in _connector_labels(pc, drawing_area):
        cx, cy = (rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2
        nid = add_node(cx, cy, "CONNECTOR", text, rect)
        near = _nearest_node(g, cx, cy, "JUNCTION",
                             limit=style.get("connector_reach") or 0.0)
        if near:
            run = [round(cx, 1), round(cy, 1), g.nodes[near]["x"], g.nodes[near]["y"]]
            g.edges.append((nid, near, run))
            g.adj[nid].append((near, run))
            g.adj[near].append((nid, run))

    for rect in _equipment_boxes(pc, style, drawing_area):
        cx, cy = (rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2
        # The label is the raw text inside the box.  Which of those words is the
        # equipment's name is not derivable: a box holds the name, its duty
        # ("(2X50%)"), supplier notes, line sizes and the tags of instruments
        # mounted on it, and neither the legend nor any measurable convention
        # separates them.  It is passed through unedited and marked as raw so
        # nothing downstream mistakes it for a name.
        nid = add_node(cx, cy, "EQUIPMENT", _box_label(pc, rect), rect)
        g.nodes[nid]["label_is_raw"] = True
        for jid, node in list(g.nodes.items()):
            if node["kind"] != "JUNCTION":
                continue
            if (rect.x0 - slack <= node["x"] <= rect.x1 + slack
                    and rect.y0 - slack <= node["y"] <= rect.y1 + slack):
                run = [round(cx, 1), round(cy, 1), node["x"], node["y"]]
                g.edges.append((nid, jid, run))
                g.adj[nid].append((jid, run))
                g.adj[jid].append((nid, run))

    # 4. the symbols themselves.  A valve sits *on* the pipe, so a run passes
    #    through its box; an instrument bubble sits *off* it and is joined by a
    #    leader, which is shorter than the shortest pipe run and so is not in the
    #    graph.  Both are attached here, and the leader is followed one step.
    leaders = ([("H", c, lo, hi) for c, lo, hi in
                _merge_runs(horiz, style["dash_len"], slack)[0]]
               + [("V", c, lo, hi) for c, lo, hi in
                  _merge_runs(vert, style["dash_len"], slack)[0]])
    for key, rect, label in symbols:
        cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
        nid = add_node(cx, cy, "SYMBOL", label, rect)
        g.nodes[nid]["row_key"] = key
        attached = 0
        for a, b, run in list(g.edges):
            if _inside_rect(run, rect, slack):
                # The symbol's own outline.  An instrument bubble is a 68 x 22.6
                # stadium whose long sides are four times the shortest pipe run,
                # so they are in the graph as runs - and attaching the symbol to
                # them made every walk start and end inside the bubble.
                continue
            if _touches(run, rect, slack):
                for end in (a, b):
                    if g.nodes[end]["kind"] != "JUNCTION":
                        continue
                    _link(g, nid, end)
                    attached += 1
        if attached:
            g.nodes[nid]["attached_by"] = "on the run"
            continue
        for axis, coord, lo, hi in leaders:
            p0 = (lo, coord) if axis == "H" else (coord, lo)
            p1 = (hi, coord) if axis == "H" else (coord, hi)
            near = _in_rect(p0, rect, slack), _in_rect(p1, rect, slack)
            if not any(near):
                continue
            far = p1 if near[0] else p0
            for jid in _nodes_at(g, far, slack * 3):
                _link(g, nid, jid)
                attached += 1
            if not attached:
                # the leader lands in the middle of a run, not on its end
                for a, b, run in g.edges:
                    if _on_run(run, far, slack):
                        _link(g, nid, a)
                        _link(g, nid, b)
                        attached += 2
                        break
            if attached:
                g.nodes[nid]["attached_by"] = "leader"
                break
        if not attached:
            g.nodes[nid]["attached_by"] = ""
    return g


def _link(g: Graph, a: str, b: str) -> None:
    link = [g.nodes[a]["x"], g.nodes[a]["y"], g.nodes[b]["x"], g.nodes[b]["y"]]
    g.adj[a].append((b, link))
    g.adj[b].append((a, link))


def _inside_rect(run, rect, slack) -> bool:
    """Both ends of the run are within the box: it is part of the symbol."""
    return (_in_rect((run[0], run[1]), rect, slack)
            and _in_rect((run[2], run[3]), rect, slack))


def _in_rect(p, rect, slack) -> bool:
    return (rect[0] - slack <= p[0] <= rect[2] + slack
            and rect[1] - slack <= p[1] <= rect[3] + slack)


def _nodes_at(g: Graph, p, radius):
    return [nid for nid, n in g.nodes.items()
            if n["kind"] == "JUNCTION"
            and abs(n["x"] - p[0]) <= radius and abs(n["y"] - p[1]) <= radius]


def _on_run(run, p, slack) -> bool:
    x0, y0, x1, y1 = run
    if abs(y0 - y1) < slack:
        return (abs(p[1] - y0) <= slack
                and min(x0, x1) - slack <= p[0] <= max(x0, x1) + slack)
    return (abs(p[0] - x0) <= slack
            and min(y0, y1) - slack <= p[1] <= max(y0, y1) + slack)


def _touches(run, rect, slack) -> bool:
    x0, y0, x1, y1 = run
    rx0, ry0, rx1, ry1 = rect
    if abs(y0 - y1) < slack:                     # horizontal
        return (ry0 - slack <= y0 <= ry1 + slack
                and min(x0, x1) - slack <= rx1 and max(x0, x1) + slack >= rx0)
    return (rx0 - slack <= x0 <= rx1 + slack
            and min(y0, y1) - slack <= ry1 and max(y0, y1) + slack >= ry0)


def _nearest_node(g: Graph, x, y, kind, limit):
    best, best_d = None, limit
    for nid, n in g.nodes.items():
        if n["kind"] != kind:
            continue
        d = abs(n["x"] - x) + abs(n["y"] - y)
        if d < best_d:
            best, best_d = nid, d
    return best


def _connector_labels(pc, drawing_area):
    """Text lines the drawing prints as `TO <name>` / `FROM <name>`."""
    lines = collections.defaultdict(list)
    for r, t in pc.words:
        if not (drawing_area[0] <= r.x0 and r.x1 <= drawing_area[2]):
            continue
        lines[round(r.y0 / 5)].append((r.x0, r, t))
    out = []
    for k in sorted(lines):
        items = sorted(lines[k], key=lambda it: it[0])
        text = " ".join(t for _x, _r, t in items).strip()
        m = CONNECTOR_RE.match(text.upper())
        if not m:
            continue
        import pymupdf
        rect = pymupdf.Rect(items[0][1])
        for _x, r, _t in items[1:]:
            rect |= r
        out.append((rect, text))
    return out


def _equipment_boxes(pc, style, drawing_area):
    """Closed boxes bigger than any symbol the legend draws."""
    floor = style["min_run"] * 2.5
    out = []
    for d in pc.drawings():
        b = d["bbox"]
        if b.width < floor or b.height < floor:
            continue
        if not (drawing_area[0] <= b.x0 and b.x1 <= drawing_area[2]
                and drawing_area[1] <= b.y0 and b.y1 <= drawing_area[3]):
            continue
        items = d["items"]
        if items and all(i[0] in ("l", "qu", "re") for i in items):
            out.append(b)
    return out


def _box_label(pc, rect) -> str:
    inside = [(r.x0, t) for r, t in pc.words
              if rect.x0 <= r.x0 and r.x1 <= rect.x1
              and rect.y0 <= r.y0 and r.y1 <= rect.y1]
    return " ".join(t for _x, t in sorted(inside))[:60]


# --------------------------------------------------------------------------
# Tracing
# --------------------------------------------------------------------------

TRACED = "TRACED"          # exactly one terminal in that direction
MULTIPLE = "MULTIPLE"      # several, all reported
FAILED = "FAILED"          # none reachable, or the walk ran out of budget


def trace(g: Graph, node_id: str) -> dict:
    """Terminals reachable from one symbol, per direction, with the path.

    Direction is not inferred from geometry: it is the drawing's own preposition.
    A terminal printed `FROM ...` is upstream and one printed `TO ...` is
    downstream.  An equipment box carries no preposition, so it is reported under
    `undirected` rather than guessed at.
    """
    found, path_runs, budget = [], [], WALK_BUDGET
    seen = {node_id}
    queue = collections.deque((nb, run, 0) for nb, run in g.adj[node_id])
    while queue and budget > 0:
        nid, run, depth = queue.popleft()
        budget -= 1
        if nid in seen:
            continue
        seen.add(nid)
        node = g.nodes[nid]
        path_runs.append(run)
        if node["kind"] in ("CONNECTOR", "EQUIPMENT"):
            found.append({"kind": node["kind"], "label": node["label"],
                          "rect": node["rect"], "depth": depth})
            continue                       # a terminal ends the walk
        if node["kind"] == "SYMBOL":
            continue                       # another symbol is not our terminal
        for nb, nrun in g.adj[nid]:
            if nb not in seen:
                queue.append((nb, nrun, depth + 1))

    up, down, other = [], [], []
    for f in found:
        head = f["label"].split()[0].upper() if f["label"] else ""
        if head == UPSTREAM_WORD:
            up.append(f)
        elif head == DOWNSTREAM_WORD:
            down.append(f)
        else:
            other.append(f)
    for bucket in (up, down, other):
        bucket.sort(key=lambda f: f["depth"])
        del bucket[MAX_CANDIDATES:]

    def status(bucket):
        return FAILED if not bucket else (TRACED if len(bucket) == 1 else MULTIPLE)

    overall = (FAILED if not found else
               MULTIPLE if len(up) > 1 or len(down) > 1 or len(other) > 1 else
               TRACED)
    return {
        "status": overall,
        "upstream": up, "downstream": down, "undirected": other,
        "upstream_status": status(up), "downstream_status": status(down),
        "budget_exhausted": budget <= 0,
        "nodes_walked": len(seen),
        "path": path_runs[:60],
    }
