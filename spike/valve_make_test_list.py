"""Make a TEST Instrument Index / IO List PDF: write test records under the header of a blank list (or of a plain page
drawn from app/valve/forms/lists.json).

    python3 spike/valve_make_test_list.py <blank list.pdf | -> <instrument_index|io_list> <records.json> <out.pdf>

records.json: [{"tag": .., "service": .., "pid_no": .., "range_min": .., "range_max": .., "range_unit": .., ...}]
Every page gets a red 'TEST DATA' stamp; the blank lists are client files and the test PDFs made from them stay outside
the repository.  '-' draws only the header captions from the card (no client content) — that is what the tests use.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.valve import instlists  # noqa: E402

STAMP = "TEST DATA - NOT A REAL LIST"
HDR_Y, PITCH = 146.0, 7.3


def synthetic(kind: str) -> pymupdf.Document:
    spec = instlists.SPEC[kind]
    doc = pymupdf.open()
    pg = doc.new_page(width=842, height=595)
    pg.insert_text((30, 70), "IO LIST" if kind == "io_list" else "Instrument Index", fontsize=12)
    for c in spec["columns"]:
        for k, ln in enumerate(c["lines"]):
            pg.insert_text((c["x0"] + 2, HDR_Y + 6 + k * PITCH), ln, fontsize=5.5)
    pg.draw_line((18, 144), (822, 144), width=0.6)
    pg.draw_line((18, 190), (822, 190), width=0.6)
    return doc


def fill(doc: pymupdf.Document, kind: str, records: list[dict], top: float = 196.0) -> pymupdf.Document:
    spec, slots = instlists.SPEC[kind], instlists.SLOTS[kind]
    pg = doc[0]
    pg.insert_text((300, 22), STAMP, fontsize=11, color=(0.85, 0.1, 0.1))
    h = PITCH * 4 + 4
    for n, r in enumerate(records):
        y0 = top + n * h
        for ci, slot in enumerate(slots):
            x = spec["columns"][ci]["x0"] + 2
            if slot == "range":
                slot = ["range_min", "range_max", "range_unit"]
            for k, f in enumerate(slot):
                if r.get(f):
                    pg.insert_text((x, y0 + 6 + k * PITCH), str(r[f])[:34], fontsize=5, color=(0, 0, 0.55))
        pg.draw_line((18, y0 + h - 1), (822, y0 + h - 1), width=0.3, color=(0.6, 0.6, 0.6))
    return doc


def main(argv):
    src, kind, rpath, out = argv
    recs = json.loads(Path(rpath).read_text(encoding="utf-8"))
    doc = synthetic(kind) if src == "-" else pymupdf.open(src)
    fill(doc, kind, recs)
    doc.save(out, garbage=3, deflate=True)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1:])
