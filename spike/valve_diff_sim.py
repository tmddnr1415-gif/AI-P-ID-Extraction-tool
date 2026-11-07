"""Differential simulation (LOGIC L85 borrowed): read → redraw → read again, and list where the reader disagrees
with itself.

    python3 spike/valve_diff_sim.py --ds Datasheet.pdf [--out /tmp/valve_sim]

Every On/Off datasheet the reader finds is redrawn on a clean ruled form — same row numbers, same labels, the values
it read (value + unit in one cell) — and read again.  On a clean form the only thing that can differ is how the
reader treats the value text itself (a colon, a 'Note-8', a unit, a label word inside the value …), so each
disagreement is a reader fragility, not a drawing problem.  Long values are drawn smaller to fit their cell (as a
form does).  The report holds client values (keep it out of the repository); the counts print to the console.
"""
from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pymupdf  # noqa: E402

from app.valve import extract  # noqa: E402

X_NUM, X_L1, X_L2, X_V, X_MID, X_R, H = 122, 136, 222, 313, 438, 572, 11


_PLAIN = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"})   # the base font has no curly quotes


def _put(pg, x0, x1, y, text):
    text = text.translate(_PLAIN)
    size = 7.0
    while size > 3.5 and pymupdf.get_text_length(text, fontsize=size) > x1 - x0 - 5:
        size -= 0.25
    pg.insert_text((x0 + 3, y + 8.5), text, fontsize=size)


def redraw(ds: dict, drawn: set | None = None) -> bytes:
    """drawn (out): (row, label) of the cells put on the form — rows with more than two labels keep the first two."""
    rows = collections.defaultdict(list)
    for k, f in ds["fields"].items():
        if f.get("row") and f.get("label") and not k.startswith("raw."):
            rows[f["row"]].append(f)
    doc = pymupdf.open()
    pg = doc.new_page(width=595, height=842)
    pg.insert_text((400, 110), "ON / OFF VALVE", fontsize=14)
    pg.insert_text((420, 125), ds["doc_no"] or "00-00-IN-DTS-00000", fontsize=8)
    pg.insert_text((410, 140), "SHEET 1 OF 1", fontsize=8)
    pg.insert_text((410, 150), "REV.", fontsize=8)
    pg.insert_text((470, 150), ds["rev"] or "A", fontsize=8)
    y, top = 150, 150
    for no in sorted(rows)[:62]:                      # 62 rows × 11 pt fit under the header
        fs = sorted(rows[no], key=lambda f: (f.get("bbox") or [0])[0])[:2]
        pg.draw_rect(pymupdf.Rect(43, y, X_R, y + H), width=0.5)
        two = len(fs) == 2
        for x in [X_NUM, X_L1, X_V] + ([X_L2, X_MID] if two else []):
            pg.draw_line((x, y), (x, y + H), width=0.5)
        pg.insert_text((X_NUM + 4, y + 8.5), str(no), fontsize=7)
        for i, f in enumerate(fs):
            if drawn is not None:
                drawn.add((no, f["label"]))
            lx0, lx1 = (X_L1, X_L2) if i == 0 else (X_L2, X_V)
            _put(pg, lx0, lx1 if two else X_V, y, f["label"])
            v = " ".join(x for x in (f.get("value") or "", f.get("unit") or "") if x)
            if v:
                vx0, vx1 = (X_V, X_MID) if i == 0 and two else (X_MID, X_R) if two else (X_V, X_R)
                _put(pg, vx0, vx1, y, v)
        y += H
    for a in (top, y):
        pg.draw_line((43, a), (X_NUM, a), width=0.5)
    pg.insert_text((50, (top + y) / 2), "GENERAL", fontsize=7)
    return doc.tobytes()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ds", required=True)
    ap.add_argument("--out", default="/tmp/valve_sim")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    dss = [d for d in extract.group_datasheets(extract.read_pdf(a.ds))
           if not any((f.get("row") or 0) > 61 for f in d["fields"].values())]
    kinds, ex, n = collections.Counter(), collections.defaultdict(list), 0
    for d in dss:
        tmp = out / "sim.pdf"
        drawn = set()
        tmp.write_bytes(redraw(d, drawn))
        back = {(f.get("row"), f.get("label")): f for x in extract.group_datasheets(extract.read_pdf(str(tmp)))
                for f in x["fields"].values()}
        for k, f in d["fields"].items():
            if (f.get("row"), f.get("label")) not in drawn:
                continue
            n += 1
            want = " ".join(x for x in (f.get("value") or "", f.get("unit") or "") if x)
            g = back.get((f["row"], f["label"]))
            if not g:
                kinds["label not found again"] += 1
                ex["label not found again"].append((d["tag_key"], f["row"], f["label"], want))
                continue
            got = " ".join(x for x in (g.get("value") or "", g.get("unit") or "") if x)
            if " ".join(got.split()) != " ".join(want.translate(_PLAIN).split()):
                kinds["value differs"] += 1
                ex["value differs"].append((d["tag_key"], f["row"], f["label"], f"{want!r} → {got!r}"))
    rep = [f"# Differential simulation — {len(dss)} On/Off datasheets · {n} cells", ""]
    rep += [f"- {k}: {v}" for k, v in kinds.items()] or ["- no disagreement"]
    for k, L in ex.items():
        rep += ["", f"## {k}"] + [f"- {t} row {r} `{lab}`: {v}" for t, r, lab, v in L[:60]]
    (out / "report.md").write_text("\n".join(rep) + "\n", encoding="utf-8")
    print(f"{len(dss)} datasheets · {n} cells · " + (", ".join(f"{k} {v}" for k, v in kinds.items()) or "no disagreement"))


if __name__ == "__main__":
    main()
