"""Make a TEST instrument datasheet: write test values onto a blank form (or onto a synthetic page drawn from the card).

    python3 spike/valve_make_test_ds.py <blank form.pdf | -> <form_id> <values.json> <out.pdf>

values.json: {"title": {"doc_no", "rev", "date"}, "rows": {"<std_key or row no>": "value" | {"Max": .., "Unit": ..}}}

Every page gets a red 'TEST DATA — NOT A REAL DATASHEET' stamp.  The blank forms are client files: they are never copied
into the repository, and neither are the test PDFs made from them (they stay in a scratch folder).  With '-' instead of a
blank form a plain page is drawn from the card (row numbers, labels, sub-column captions) — that is what the tests use.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.valve import instrument  # noqa: E402

STAMP = "TEST DATA - NOT A REAL DATASHEET"
SIZES = {"A4": (595.3, 841.9), "Letter": (612, 792)}


def synthetic(card: dict) -> pymupdf.Document:
    """A plain page per items block, drawn from the card: no client content at all."""
    doc = pymupdf.open()
    pages = sorted({i.get("page", 1) for i in card["items"]})
    for p in pages:
        w, h = SIZES.get(card.get("page_size"), SIZES["A4"])
        pg = doc.new_page(width=w, height=h)
        pg.insert_text((60, 50), f"Form No : {card.get('form_no_printed') or card['form_id']}", fontsize=9)
        if card.get("printed_title"):
            pg.insert_text((220, 70), card["printed_title"], fontsize=10)
        pg.insert_text((420, 90), "DOCUMENT NO.", fontsize=7)
        pg.insert_text((420, 120), "REV.", fontsize=7)
        pg.insert_text((420, 135), "DATE", fontsize=7)
        sec = ""
        for it in card["items"]:
            if it.get("page", 1) != p:
                continue
            if it.get("section") and it["section"] != sec:          # vertical section letters like the forms
                sec = it["section"]
                y = (it.get("label_bbox") or it.get("value_bbox"))[1]
                for k, ch in enumerate(sec.replace(" ", "")[:12]):
                    pg.insert_text((40, y + 7 + k * 6), ch, fontsize=5)
            if it.get("label_bbox"):
                b = it["label_bbox"]
                pg.insert_text((b[0], b[3] - 1.5), it["label"], fontsize=6.5)
            vb = it.get("value_bbox")
            if vb:
                pg.draw_rect(pymupdf.Rect(vb), color=(0.6, 0.6, 0.6), width=0.3)
                pg.insert_text((max(20, (it.get("label_bbox") or vb)[0] - 24), vb[3] - 2), str(it["no"]), fontsize=6)
                subs = it.get("subcols") or []
                sls = [z for z in (it.get("sublabels") or []) if isinstance(z, dict) and z.get("bbox")]
                for z in sls:                                    # a second caption in the row: where the form prints it
                    pg.insert_text((z["bbox"][0], z["bbox"][3] - 1.5), z["text"], fontsize=6.5)
                if sls:
                    subs = []
                if it.get("pair_cells"):                         # the rules that split a two-label row
                    for x in [it["pair_cells"]["main"][0] - 1] + [c[0] - 1 for c in it["pair_cells"]["subs"].values()]:
                        pg.draw_line((x, vb[1]), (x, vb[3]), color=(0.6, 0.6, 0.6), width=0.3)
                if subs and (it.get("role") == "header" or not it.get("subcols_from")):
                    span = (vb[2] - vb[0]) / len(subs)
                    for k, s in enumerate(subs):
                        x = vb[0] + k * span + (span / 2 - len(s) * 1.6 if it.get("role") == "header" else 2)
                        pg.insert_text((x, vb[3] - 2), s, fontsize=6)
        pg.insert_text((w - 120, h - 20), card.get("footer_tag") or "", fontsize=6)
    return doc


def fill(doc: pymupdf.Document, card: dict, vals: dict, font: float = 6.5) -> pymupdf.Document:
    rows = vals.get("rows", {})
    first = min(i.get("page", 1) for i in card["items"])
    for pg in doc:
        pg.insert_text((150, 22), STAMP, fontsize=11, color=(0.85, 0.1, 0.1))
    for it in card["items"]:
        v = rows.get(str(it["no"]), rows.get(it.get("std_key") or "\0"))
        if v is None or not it.get("value_bbox") or it.get("page", 1) > len(doc):
            continue
        pg, vb = doc[it.get("page", 1) - 1], it["value_bbox"]
        y = vb[3] - 2
        if isinstance(v, dict):                                  # sub-columns
            subs = it.get("subcols") or []
            words = pg.get_text("words")
            hdr = None
            if it.get("subcols_from"):
                hdr = next((i for i in card["items"] if i["no"] == it["subcols_from"] and i.get("block") == it.get("block")), None)
            for s, x in v.items():
                pc = it.get("pair_cells")
                if s == "_":                                     # the row's own value (before its second label)
                    pg.insert_text(((pc["main"][0] if pc else vb[0]) + 3, y), str(x), fontsize=font, color=(0, 0, 0.55))
                    continue
                if pc and s in pc["subs"]:
                    pg.insert_text((pc["subs"][s][0] + 3, y), str(x), fontsize=font, color=(0, 0, 0.55))
                    continue
                if hdr and hdr.get("value_bbox"):
                    hb = hdr["value_bbox"]
                    caps = [w for w in words if w[4].lower() == s.lower() and hb[1] - 2 <= (w[1] + w[3]) / 2 <= hb[3] + 2]
                    cx = (caps[0][0] + caps[0][2]) / 2 if caps else vb[0] + (subs.index(s) + 0.5) * (vb[2] - vb[0]) / len(subs)
                    pg.insert_text((cx - len(str(x)) * 1.6, y), str(x), fontsize=font, color=(0, 0, 0.55))
                else:
                    sl = [z for z in (it.get("sublabels") or []) if isinstance(z, dict) and z.get("text") == s and z.get("bbox")]
                    if sl:
                        x0 = sl[0]["bbox"][2] + 4
                    else:                                        # the caption printed in the row: write after its last word
                        line = sorted([w for w in words if vb[1] - 2 <= (w[1] + w[3]) / 2 <= vb[3] + 2 and vb[0] - 2 <= w[0] <= vb[2]], key=lambda w: w[0])
                        parts = [q.lower() for q in s.split()]
                        low = [w[4].strip(":").lower() for w in line]
                        hit = next((i for i in range(len(line) - len(parts) + 1) if low[i:i + len(parts)] == parts), None)
                        x0 = line[hit + len(parts) - 1][2] + 4 if hit is not None else vb[0] + subs.index(s) * (vb[2] - vb[0]) / len(subs) + 3
                    pg.insert_text((x0, y), str(x), fontsize=font, color=(0, 0, 0.55))
        else:
            x0 = it["pair_cells"]["main"][0] if it.get("pair_cells") else vb[0]
            pg.insert_text((x0 + 3, y), str(v), fontsize=font, color=(0, 0, 0.55))
    t = vals.get("title") or {}
    pg = doc[first - 1]
    words = pg.get_text("words")
    for cap, key, dxy in (("DOCUMENT", "doc_no", (0, 16)), ("REV.", "rev", (40, 0)), ("DATE", "date", (40, 0))):
        if not t.get(key):
            continue
        c = [w for w in words if w[4].upper() == cap]
        if cap == "DATE":
            c = [w for w in c if w[0] > pg.rect.width * 0.6] or c
        if c:
            w0 = c[0]
            pg.insert_text((w0[0] + dxy[0] if key == "doc_no" else w0[2] + 8, w0[3] + dxy[1] - (0 if key == "doc_no" else 1)),
                           t[key], fontsize=7, color=(0, 0, 0.55))
    return doc


def main(argv):
    src, fid, vpath, out = argv
    card = instrument.cards()[fid]
    vals = json.loads(Path(vpath).read_text(encoding="utf-8"))
    doc = synthetic(card) if src == "-" else pymupdf.open(src)
    fill(doc, card, vals)
    doc.save(out, garbage=3, deflate=True)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1:])
