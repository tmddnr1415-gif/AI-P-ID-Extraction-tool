"""Instrument review → mark-up PDF (valve40).  Each finding is written INTO the datasheet PDF the way a reviewer marks it
in Acrobat: the cell is shaded (Square annotation, coloured fill) and a numbered Callout (FreeText 'FreeTextCallout' with
a leader line ending in an arrow) carries the reason.  The page is widened on the right so the callout boxes never cover
the form; they are stacked there in the order of the cells they point at.

The annotations stay editable (Acrobat / Bluebeam: move, reword, reply) unless flatten=True bakes them into the page.
Colours: red = Mismatch · orange = Missing · yellow = Review Required.
"""
from __future__ import annotations

import html
import math

import pymupdf

from app.valve import extract

MARGIN = 236                                             # pt added to the right of each page for the callout boxes
COL = {"Mismatch": (0.80, 0.08, 0.08), "Missing": (0.85, 0.42, 0.0), "Review Required": (0.72, 0.56, 0.0)}
FILL = {"Mismatch": (1.0, 0.55, 0.55), "Missing": (1.0, 0.78, 0.45), "Review Required": (1.0, 0.92, 0.45)}
BOX = {"Mismatch": (1.0, 0.95, 0.95), "Missing": (1.0, 0.96, 0.90), "Review Required": (1.0, 0.99, 0.88)}
SHOW = tuple(COL)


def _units(s: str) -> float:
    """Text width in 'em' (Hangul ≈ 1, Latin ≈ 0.5, capitals a little wider)."""
    return sum(1.0 if ord(c) > 0x2E80 else 0.6 if c.isupper() else 0.54 if c.isdigit() else 0.46 for c in s)


def _height(text: str, width: float, fs: float) -> float:
    lines = sum(max(1, math.ceil(_units(ln) * fs / (width - 6))) for ln in text.split("\n"))
    return lines * fs * 1.2 + 5


RULE_EN = {
    "IN-REQ-01": "Required field is blank.",
    "IN-PDS-00": "Tag is not found in the Process Data Sheet.",
    "IN-PDS-01": "Value differs from the Process Data Sheet.",
    "IN-PMS-01": "Pipe class is not found in the PMS.",
    "IN-PMS-02": "Rating differs from the PMS flange class.",
    "IN-LL-00": "Line No. is not found in the Process Line List.",
    "IN-LL-01": "Pipe class differs from the Process Line List.",
    "IN-LL-02": "Line List design pressure is higher than the datasheet design pressure.",
    "IN-LL-03": "Line List max. design temperature is higher than the datasheet.",
    "IN-LL-04": "Line List min. design temperature is lower than the datasheet.",
    "IN-LL-05": "Line size differs from the Process Line List.",
    "IN-ITM-01": "Range upper value is below the max. operating pressure.",
    "IN-ITM-02": "Set pressure is above the design pressure.",
    "IN-OPN-01": "Open item (HOLD / TBA / TBC / TBD) is left on the datasheet. Please confirm the value.",
    "IN-UNIT-01": "Operating and design pressures use different gauge/absolute bases. Please check.",
}
REVIEW_EN = {"IN-PDS-01": "Cannot be compared automatically (unit or gauge/absolute basis unclear). Please verify.",
             "IN-PMS-01": "Pipe class could not be matched exactly in the PMS. Please confirm.",
             "IN-LL-00": "Line No. matched only partly in the Process Line List. Please confirm.",
             "IN-LL-01": "Pipe class differs only in its suffix from the Process Line List. Please confirm.",
             "IN-LL-02": "Design pressure cannot be compared (blank, unit unclear or absolute basis). Please verify.",
             "IN-LL-03": "Design temperature cannot be compared (blank or unit unclear). Please verify."}
REF_EN = {"IN-REQ": "Required", "IN-PDS": "PDS", "IN-PMS": "PMS", "IN-LL": "Line List", "IN-ITM": "Same datasheet", "IN-OPN": "Expected", "IN-UNIT": "Expected"}
WORD_EN_EXTRA = {"확정 값": "Firm value", "같은 기준": "Same basis"}
WORD_EN = {"없음": "Not found", "필수": "Required", "같은 Datasheet": "Same datasheet", "행": " row", "양식": "Form", "카드": "card"}


def _en(s: str) -> str:
    """Korean fixed words of the review rows → English; anything else non-ASCII is dropped (values stay as read)."""
    s = str(s or "")
    for k, v in list(WORD_EN_EXTRA.items()) + list(WORD_EN.items()):
        s = s.replace(k, v)
    return "".join(c if ord(c) < 0x2E80 else "" for c in s).replace("  ", " ").strip()


def reason_en(f: dict) -> str:
    d = f.get("decision") or {}
    if d.get("decision") == "Modified" and d.get("text") and all(ord(c) < 0x2E80 for c in d["text"]):
        return d["text"]                                   # the engineer's own wording, when it is in English
    r = str(f.get("reason") or "")
    if r and all(ord(c) < 0x2E80 for c in r):            # the rule already said it in English (numbers · PMS text)
        return r
    if f["result"] == "Review Required" and f["rule"] in REVIEW_EN:
        return REVIEW_EN[f["rule"]]
    return RULE_EN.get(f["rule"], f["rule"])


def callout_text(n: int, f: dict) -> str:
    import re
    ds, ref = _en(f.get("ds")) or "(blank)", _en(f.get("ref")) or "-"
    lab = REF_EN.get(f["rule"].rsplit("-", 1)[0], "Reference")
    item = re.sub(r"^(\d+(?:\.\d+)?)\.\s+", r"Row \1 ", str(f["item"]))
    second = f"Datasheet: {ds}" if f["rule"] == "IN-REQ-01" else f"Datasheet: {ds}  |  {lab}: {ref}"
    lines = [f"{n}. {item} - {f['result']}  [{f['rule']}]", second, reason_en(f)]
    if f.get("source"):
        lines.append("Source: " + re.sub(r"\b(\S+) (\d+) row\b", r"\1 row \2", _en(f["source"])).replace("·", "-"))
    if f.get("human"):
        lines.append("To be checked by the engineer.")
    return "\n".join(lines)


def _target(rows: list[dict], key: str):
    """(page, bbox, note) of the cell a finding is about; the Tag row when the form has no such cell."""
    alias = {"line_size": ("line_no",), "pds": ("tag",), "material": ("piping_class",),
             "range": ("range", "range_adj_range", "calibration_range", "range_set_at", "element_range"),
             "design_pressure": ("design_pressure", "op_pressure"), "design_temp": ("design_temp", "op_temp"),
             "op_pressure": ("op_pressure", "upstream_pressure"), "op_temp": ("op_temp", "temperature")}
    if (key or "").startswith("row:"):                    # an open item on a row without a standard key
        r = next((x for x in rows if x.get("no") == key[4:] and x.get("bbox")), None)
        if r:
            return r["page"], r["bbox"], ""
    for k in (key,) + alias.get(key, ()):
        r = next((x for x in rows if k and x.get("std_key") == k and x.get("bbox")), None)
        if r:
            return r["page"], r["bbox"], ""
    r = next((x for x in rows if x.get("std_key") == "tag" and x.get("bbox")), None)
    return (r["page"], r["bbox"], "\n(This form has no such field - marked on the Tag row.)") if r else (None, None, "")


def mark_sheet(out: pymupdf.Document, src: pymupdf.Document, sheet: dict, rows: list[dict], findings: list[dict], head: str) -> int:
    """Append this sheet's pages to out with shading + callouts.  Returns the number of findings marked."""
    first = out.page_count
    pmap = {}
    for p in sheet["pages"]:
        if 1 <= p <= src.page_count:
            out.insert_pdf(src, from_page=p - 1, to_page=p - 1)
            pmap[p] = out.page_count - 1
    if not pmap:
        return 0
    todo = [f for f in findings if f["result"] in SHOW]
    placed, tmp = {}, []
    for f in todo:
        page, bbox, note = _target(rows, f.get("key", ""))
        if page not in pmap:
            page, bbox = min(pmap), None
        tmp.append((page, bbox[1] if bbox else 0.0, f, bbox, note))
    for n, (page, _, f, bbox, note) in enumerate(sorted(tmp, key=lambda t: (t[0], t[1])), 1):
        placed.setdefault(page, []).append((n, f, bbox, note))
    for p, k in pmap.items():
        pg = out[k]
        W = pg.rect.width
        items = placed.get(p, [])
        mb = pg.mediabox
        pg.set_mediabox(pymupdf.Rect(mb.x0, mb.y0, mb.x1 + MARGIN, mb.y1))
        pr = pg.rect
        pg.draw_rect(pymupdf.Rect(W, pr.y0, pr.x1, pr.y1), color=None, fill=(0.965, 0.972, 0.985), overlay=False)
        pg.draw_line((W, pr.y0 + 10), (W, pr.y1 - 10), color=(0.62, 0.66, 0.74), width=0.6)
        pg.insert_htmlbox(pymupdf.Rect(W + 10, pr.y0 + 12, pr.x1 - 8, pr.y0 + 30),
                          f"<b>{html.escape(head)}</b> - page {p} - {len(items)} comment{'s' if len(items) != 1 else ''}", css="*{font-family:sans-serif;font-size:7.5pt;color:#1f2d4d;}")
        x0, x1 = W + 10, pr.x1 - 8
        fs = 7.0 if len(items) <= 8 else 6.2
        texts = [callout_text(n, f) + note for n, f, _, note in items]
        hs = [_height(t, x1 - x0, fs) for t in texts]
        room = pr.y1 - 40 - (pr.y0 + 32)
        while sum(hs) + 6 * len(hs) > room and fs > 5.0:   # many findings: smaller text so every box fits beside the page
            fs -= 0.4
            hs = [_height(t, x1 - x0, fs) for t in texts]
        y = pr.y0 + 34                                     # one tidy column: same width, same gap, 1 → n top to bottom
        for (n, f, bbox, note), text, h in zip(items, texts, hs):
            box = pymupdf.Rect(x0, y, x1, y + h)
            col = COL[f["result"]]
            if bbox:                                       # shading on the cell
                r = pymupdf.Rect(bbox) + (-1, -1, 1, 1)
                s = pg.add_rect_annot(r)
                s.set_colors(stroke=col, fill=FILL[f["result"]])
                s.set_border(width=0.9)
                s.set_opacity(0.38)
                s.set_info(title="Instrument Review", subject=f"{f['rule']} shading", content=f"{n}. {f['item']}")
                s.update()
                tip = pymupdf.Point(r.x1, (r.y0 + r.y1) / 2)
            else:
                tip = pymupdf.Point(W - 6, box.y0 + 6)
            knee = pymupdf.Point(W + 4, box.y0 + min(h / 2, 8))
            hexc = "#%02x%02x%02x" % tuple(int(c * 255) for c in col)
            body = "".join(f"<div>{'<b>' if k == 0 else ''}{html.escape(ln)}{'</b>' if k == 0 else ''}</div>" for k, ln in enumerate(text.split("\n")))
            a = pg.add_freetext_annot(box, body, fontsize=fs, fill_color=BOX[f["result"]], border_color=col, richtext=True,
                                      callout=[tip, knee, pymupdf.Point(box.x0, knee.y)], line_end=pymupdf.PDF_ANNOT_LE_OPEN_ARROW,
                                      border_width=0.9, style=f"font-size:{fs}pt;color:{hexc};font-family:sans-serif;")
            # the leader line and the frame take the default-appearance colour: make it the finding's colour
            out.xref_set_key(a.xref, "DA", f"(/Helv {fs:g} Tf {col[0]:g} {col[1]:g} {col[2]:g} rg)")
            a.set_info(title="Instrument Review", subject=f"{f['rule']} · {f['result']}", content=text)
            a.update()
            y = box.y1 + 6
    return len(todo)


def cover(entries: list[dict], project: str) -> pymupdf.Document:
    rows = "".join(f"<tr><td>{html.escape(e['tag'])}</td><td>{html.escape(e['kind'])}</td><td>{html.escape(e['doc_no'] or '')}</td>"
                   f"<td>{html.escape(e['rev'] or '')}</td><td>{e['n']}</td><td>{e['mis']}</td><td>{e['miss']}</td><td>{e['rev_req']}</td></tr>"
                   for e in entries)
    body = (f"<h2>Instrument Datasheet Review - Mark-up</h2><p>{html.escape(_en(project))} - {len(entries)} datasheets - "
            f"{sum(e['n'] for e in entries)} comments</p>"
            "<p>Each comment is a shaded field with a numbered arrow callout giving the reason: <b style='color:#cc1414'>red</b> mismatch, "
            "<b style='color:#d96b00'>orange</b> missing, <b style='color:#b88f00'>yellow</b> review required. "
            "The callouts are PDF comments: they can be moved, edited or replied to in Acrobat.</p>"
            "<table border='1' cellpadding='3' style='border-collapse:collapse;font-size:9pt'><tr><th>Tag</th><th>Kind</th><th>Doc No</th><th>Rev</th>"
            f"<th>Comments</th><th>Mismatch</th><th>Missing</th><th>Review</th></tr>{rows}</table>")
    d = pymupdf.open()
    story = pymupdf.Story(html=body, user_css="*{font-family:sans-serif;font-size:10pt;} h2{font-size:15pt;}")
    import io
    buf = io.BytesIO()
    w = pymupdf.DocumentWriter(buf)
    more, r = 1, pymupdf.Rect(0, 0, 595, 842)
    while more:
        dev = w.begin_page(r)
        more, _ = story.place(r + (36, 36, -36, -36))
        story.draw(dev)
        w.end_page()
    w.close()
    d.insert_pdf(pymupdf.open("pdf", buf.getvalue()))
    return d


def build(entries: list[dict], project: str, flatten: bool = False) -> bytes:
    """entries: [{path, sheet, rows, findings, tag, kind, doc_no, rev}] → PDF bytes."""
    out = pymupdf.open()
    srcs = {}
    marked = []
    for e in entries:
        if e["path"] not in srcs:
            try:
                srcs[e["path"]] = extract.open_stored(e["path"])
            except extract.PdfError:
                continue
        todo = [f for f in e["findings"] if f["result"] in SHOW]
        e = dict(e, n=len(todo), mis=sum(f["result"] == "Mismatch" for f in todo), miss=sum(f["result"] == "Missing" for f in todo),
                 rev_req=sum(f["result"] == "Review Required" for f in todo))
        marked.append((e, out.page_count))
        mark_sheet(out, srcs[e["path"]], e["sheet"], e["rows"], e["findings"], f"{e['tag']} · Rev {e['rev'] or '-'}")
    toc = [[1, f"{e['tag']} ({e['n']})", start + 1] for e, start in marked]
    if len(entries) > 1:
        cv = cover([e for e, _ in marked], project)
        out.insert_pdf(cv, start_at=0)
        toc = [[1, "Summary", 1]] + [[1, t, p + cv.page_count] for _, t, p in toc]
    if toc:
        out.set_toc(toc)
    if flatten:
        out.bake(annots=True, widgets=True)
    data = out.tobytes(garbage=3, deflate=True)
    for s in srcs.values():
        s.close()
    return data
