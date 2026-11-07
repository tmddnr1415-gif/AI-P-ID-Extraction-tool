"""Visual check packs — every page of a datasheet PDF as images + what the reader took from it, for a person (or a
reviewing agent) to compare by eye.  The packs hold client values: write them outside the repository.

    python3 spike/valve_visual_pack.py --ds Datasheet.pdf --out /tmp/vis [--zoom 2]

Per page N:
  pNNN_1.png, pNNN_2.png   the page in two overlapping halves (top / bottom) at --zoom (2 = 144 dpi)
  pNNN.txt                 what the reader took from that page:
       datasheet sheet → header (tag · doc no · rev · sheet x of y) and every field read there:
                         F<id> | row | label | value | unit | status | bbox
                         and the notes read there (N<no> | text)
       other page      → document no · title · rev, and (for the page that carries them) the General Notes
  index.json               page → kind, datasheet tag, number of fields
The verdicts come back as JSON (see spike/valve_visual_score.py); the reader never reads them.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pymupdf  # noqa: E402

from app.valve import extract  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ds", required=True)
    ap.add_argument("--out", default="/tmp/vis")
    ap.add_argument("--zoom", type=float, default=2.0)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    res = extract.read_pdf(a.ds)
    dss = extract.group_datasheets(res)
    by_page, index = {}, {}
    for d in dss:
        for p in d["pages"]:
            by_page.setdefault(p, []).append(d)
    gn_page = {}                                           # the page whose text holds a document's General Notes
    doc = pymupdf.open(a.ds)
    for o in res["other_pages"]:
        t = doc[o["page"] - 1].get_text()
        if "GENERAL NOTE" in t.upper():
            gn_page.setdefault(o.get("doc_no") or "", []).append(o["page"])
    for i, page in enumerate(doc, 1):
        pix = page.get_pixmap(matrix=pymupdf.Matrix(a.zoom, a.zoom))
        h = pix.height
        for k, (y0, y1) in enumerate(((0, h // 2 + 40), (h // 2 - 40, h)), 1):
            page.get_pixmap(matrix=pymupdf.Matrix(a.zoom, a.zoom),
                            clip=pymupdf.Rect(0, y0 / a.zoom, page.rect.width, y1 / a.zoom)).save(out / f"p{i:03d}_{k}.png")
        lines = [f"PAGE {i} of {doc.page_count} · page size {page.rect.width:.0f}×{page.rect.height:.0f} pt · "
                 f"image zoom {a.zoom} (pixel = pt × {a.zoom}; half 2 starts at y = {(h // 2 - 40) / a.zoom:.0f} pt)"]
        if i in by_page:
            for d in by_page[i]:
                sh = next((s for s in d.get("sheets") or [] if s[0] == i), None)
                lines.append(f"DATASHEET tag={d['tag']!r} doc_no={d['doc_no']!r} rev={d['rev']!r} "
                             f"sheet={sh[1] if sh else '?'} of {sh[2] if sh else '?'}")
                fs = [(k, f) for k, f in d["fields"].items() if f.get("page") == i]
                fs.sort(key=lambda kf: ((kf[1].get("row") or 0), (kf[1].get("bbox") or [0])[0]))
                lines.append(f"FIELDS ({len(fs)}): id | row | label | value | unit | status | bbox[x0,y0,x1,y1] pt")
                for n, (k, f) in enumerate(fs):
                    bb = [round(v) for v in f["bbox"]] if f.get("bbox") else None
                    lines.append(f"F{n} | {f.get('row')} | {f.get('label') or k} | {f.get('value') or ''} | "
                                 f"{f.get('unit') or ''} | {f.get('status')} | {bb}")
                ns = [n for n in d["notes"] if n.get("page") == i]
                if ns:
                    lines.append(f"NOTES ({len(ns)}):")
                    lines += [f"N{n['no']}{' (' + n['section'] + ')' if n.get('section') else ''} | {n['text']}" for n in ns]
            index[i] = {"kind": "datasheet", "tags": [d["tag"] for d in by_page[i]],
                        "fields": sum(1 for d in by_page[i] for f in d["fields"].values() if f.get("page") == i)}
        else:
            o = next((o for o in res["other_pages"] if o["page"] == i), {})
            dn = o.get("doc_no") or ""
            info = res["docs"].get(dn, {})
            lines.append(f"OTHER PAGE doc_no={dn!r} title={info.get('title')!r} rev={info.get('rev')!r}")
            if i in gn_page.get(dn, []):
                gn = info.get("general_notes") or {}
                lines.append(f"GENERAL NOTES read for this document ({len(gn)}) — they may continue on the next page:")
                lines += [f"G{no} | {t}" for no, t in sorted(gn.items(), key=lambda kv: int(kv[0]))]
            index[i] = {"kind": "other", "doc_no": dn, "general_notes_here": i in gn_page.get(dn, [])}
        (out / f"p{i:03d}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=0))
    print(f"{doc.page_count} pages → {out}")


if __name__ == "__main__":
    main()
