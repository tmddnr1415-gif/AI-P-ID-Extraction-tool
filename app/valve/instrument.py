"""Instrument datasheets (FT · PT/PDT · LT · GWR · TT · TG · PG · DPG · Mag LG · RO · Analyzer …) — the generic
numbered-row reader that uses the form cards in app/valve/forms/ (made from the blank forms by spike/valve_form_learn.py).

* identify(doc, filename)  → which form a PDF is (Form No · footer tag · title · section letters · labels · file name)
* read_pdf(path)           → one sheet per datasheet: {form_id, kind, pages, title block, values by row number, tags}
* split_tags(raw, qty)     → 'FT-1001A/B' → ['FT1001A', 'FT1001B'] (one review row per tag)

Only the PDF text layer is used (no OCR, no LLM).  A value the page does not print stays '' — never filled in.
The card's positions are those of the blank form; a filled page may be shifted a little (printer · re-saved PDF), so the
shift is measured on each page from the printed row labels and applied to every value cell.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from statistics import median

FORMS = Path(__file__).with_name("forms")
_SEP = re.compile(r"[\s\-_]+")


def tag_key(s: str) -> str:
    """Tag compare key (plan v2): uppercase, spaces · hyphens · underscores removed — FT-1001A = FT 1001 A → FT1001A."""
    return _SEP.sub("", (s or "").upper())


@lru_cache(maxsize=1)
def cards() -> dict[str, dict]:
    idx = json.loads((FORMS / "index.json").read_text(encoding="utf-8"))
    idx = idx if isinstance(idx, list) else idx.get("forms", [])
    return {f["form_id"]: json.loads((FORMS / f"{f['form_id']}.json").read_text(encoding="utf-8")) for f in idx}


def kinds() -> dict[str, str]:
    """kind key → form id (ft → 313 …)."""
    return {c["item_kind"]: fid for fid, c in cards().items()}


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text or "")


def _letters(text: str) -> str:
    """Vertical section captions are printed one letter per line ('M\\nE\\nT\\nE\\nR') — joined without spaces."""
    return re.sub(r"[^A-Z/.&]", "", (text or "").upper())


def _score(card: dict, text: str, filename: str) -> tuple[int, list[str]]:
    flat, letters, why, s = _flat(text), _letters(text), [], 0
    for r in card.get("identify", []):
        k = r["kind"]
        if k == "text" and re.search(r["regex"], flat, re.I):
            s += 4
            why.append(f"글 '{r['regex']}'")
        elif k == "file_name" and filename and re.search(r["regex"], Path(filename).name, re.I):
            s += 1
            why.append("파일 이름")
        elif k == "label" and r["text"].lower() in flat.lower():
            s += 1
            why.append(f"칸 '{r['text']}'")
        elif k == "section" and _letters(r["text"]) in letters:
            s += 2
            why.append(f"구역 '{r['text']}'")
    # row labels of the card found on the page (forms 313 / 506 / 601 share most rows — the text rules separate them)
    labels = [i["label"] for i in card["items"] if i.get("label") and i.get("page", 1) == 1 and len(i["label"]) > 5]
    if labels:
        hit = sum(1 for lb in labels if lb.lower() in flat.lower()) / len(labels)
        s += int(hit * 6)
        if hit >= 0.6:
            why.append(f"칸 이름 {hit:.0%} 일치")
    return s, why


def identify_text(text: str, filename: str = "") -> dict:
    """{form_id, kind, score, why, runner_up} — form_id '' when no form scores well enough or two tie."""
    sc = sorted(((*_score(c, text, filename), fid) for fid, c in cards().items()), key=lambda t: -t[0])
    best, nxt = sc[0], (sc[1] if len(sc) > 1 else (0, [], ""))
    ok = best[0] >= 7 and best[0] > nxt[0]
    return {"form_id": best[2] if ok else "", "kind": cards()[best[2]]["item_kind"] if ok else "", "score": best[0],
            "why": best[1], "runner_up": nxt[2], "runner_up_score": nxt[0]}


# ── reading one items page ───────────────────────────────────────────────────────────────────────────────────────────
def _shift(page, items) -> tuple[float, float, int]:
    """Median (dx, dy) between the card's label positions and the same labels on this page; n = labels matched."""
    dxs, dys = [], []
    for it in items:
        lb, bb = it.get("label"), it.get("label_bbox")
        if not lb or not bb or len(lb) < 4:
            continue
        hits = page.search_for(lb)
        if not hits:
            continue
        h = min(hits, key=lambda r: abs(r.x0 - bb[0]) + abs(r.y0 - bb[1]))
        if abs(h.x0 - bb[0]) < 60 and abs(h.y0 - bb[1]) < 60:
            dxs.append(h.x0 - bb[0])
            dys.append(h.y0 - bb[1])
    if len(dys) < 3:
        return 0.0, 0.0, len(dys)
    return median(dxs), median(dys), len(dys)


_JUNK = {"/", "-", "~", ":", "|"}


def _in(w, box) -> bool:
    cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
    return box[0] - 1 <= cx <= box[2] + 1 and box[1] - 0.5 <= cy <= box[3] + 0.5


def _join(ws) -> str:
    ws = sorted(ws, key=lambda w: (round(w[1] / 3), w[0]))
    return " ".join(w[4] for w in ws).strip()


def _cell_values(it, ws, header_ws) -> dict:
    """Split a row's words into its sub-columns.  Max/Nor/Min/Unit (captions on a header row above): a word belongs to the
    caption whose centre is nearest.  Captions printed inside the row ('Class … Type … Certificate'): a word belongs to
    the caption printed left of it."""
    subs = it.get("subcols") or []
    if not subs:
        return {}
    if header_ws:                                           # centred captions on the header row
        cap = {}
        for w in header_ws:
            for s in subs:
                if w[4].strip(":").lower() == s.lower() and s not in cap:
                    cap[s] = (w[0] + w[2]) / 2
        if len(cap) >= 2:
            out = {s: [] for s in cap}
            for w in ws:
                if w[4] in _JUNK:
                    continue
                c = (w[0] + w[2]) / 2
                out[min(cap, key=lambda s: abs(cap[s] - c))].append(w)
            return {s: _join(v) for s, v in out.items()}
        return {}
    cap, capw = [], set()
    line = sorted(ws, key=lambda w: w[0])
    low = [w[4].strip(":").lower() for w in line]
    for s in sorted(subs, key=lambda s: -len(s.split())):      # longest captions first ('Max/Min Temperature')
        parts = [x.lower() for x in s.split()]
        for i in range(len(line) - len(parts) + 1):
            if low[i:i + len(parts)] == parts and not any(id(line[i + k]) in capw for k in range(len(parts))):
                cap.append((line[i][0], s, line[i]))
                capw |= {id(line[i + k]) for k in range(len(parts))}
                break
    if not cap:
        return {}
    cap.sort(key=lambda c: c[0])
    out = {s: [] for _, s, _ in cap}
    lead = []
    for w in ws:
        if id(w) in capw or w[4] in _JUNK:
            continue
        left = [c for c in cap if c[0] <= w[0] + 1]
        (out[left[-1][1]] if left else lead).append(w)
    return {s: _join(v) for s, v in out.items()}


def read_items_page(page, card: dict, block: int, card_page: int | None = None) -> dict:
    """{no: {label, std_key, section, value, sub{}, bbox}} for one items page of a card block (form 80: block 1 goes on
    over two pages — card_page picks the rows printed on this page)."""
    items = [i for i in card["items"] if i.get("block") == block and (card_page is None or i.get("page", 1) == card_page)]
    dx, dy, n = _shift(page, items)
    words = page.get_text("words")
    # printed captions that sit inside another row's value cell (form 101 prints two label columns): never a value
    labs = [(b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy) for i in items for b in [i.get("label_bbox")] + [x.get("bbox") for x in (i.get("sublabels") or []) if isinstance(x, dict)] if b]
    words = [w for w in words if not any(_in(w, lb) for lb in labs)]
    out = {}
    by_no = {i["no"]: i for i in items}
    for it in items:
        vb = it.get("value_bbox")
        if not vb or it.get("role") == "header" or vb[2] - vb[0] < 4:      # header rows · empty rows of no width
            continue
        box = (vb[0] + dx, vb[1] + dy, vb[2] + dx, vb[3] + dy)
        ws = [w for w in words if _in(w, box)]
        hdr = []
        if it.get("subcols_from") and by_no.get(it["subcols_from"], {}).get("value_bbox"):
            hb = by_no[it["subcols_from"]]["value_bbox"]
            hdr = [w for w in words if _in(w, (hb[0] + dx, hb[1] + dy, hb[2] + dx, hb[3] + dy))]
        sls = [x for x in (it.get("sublabels") or []) if isinstance(x, dict) and x.get("bbox")]
        pc = it.get("pair_cells")
        if sls and pc:                                      # two labels side by side, each with its own cell (form 80)
            cell = lambda c: [w for w in words if c[0] + dx - 1 <= (w[0] + w[2]) / 2 <= c[1] + dx + 1 and box[1] - 0.5 <= (w[1] + w[3]) / 2 <= box[3] + 0.5 and w[4] not in _JUNK]   # noqa: E731
            sub = {t: _join(cell(c)) for t, c in pc["subs"].items()}
            ws = cell(pc["main"])
        elif sls:                                           # a second label printed in the same row ('Tag No. … Item No.')
            sub = {x["text"]: _join([w for w in ws if w[0] >= x["bbox"][2] + dx - 1 and w[4] not in _JUNK
                                     and all(w[0] < y["bbox"][0] + dx for y in sls if y["bbox"][0] > x["bbox"][0])]) for x in sls}
            ws = [w for w in ws if w[0] < min(x["bbox"][0] for x in sls) + dx]
        else:
            sub = _cell_values(it, ws, hdr)
        subs = {s.lower() for s in (it.get("subcols") or [])} | {p.lower() for s in (it.get("subcols") or []) for p in s.split()}
        val_ws = [w for w in ws if w[4] not in _JUNK and w[4].strip(":").lower() not in subs]
        out[it["no"]] = {"label": it.get("label", ""), "std_key": it.get("std_key", ""), "section": it.get("section", ""),
                         "process": bool(it.get("process")), "value": _join(val_ws), "sub": {k: v for k, v in sub.items() if v},
                         "sub_keys": {x["text"]: x.get("std_key", "") for x in sls},
                         "bbox": [round(x, 1) for x in box]}
    return {"shift": [round(dx, 1), round(dy, 1)], "anchors": n, "rows": out}


# ── title block: document no · rev · date · revision table ─────────────────────────────────────────────────────────────
def _right_of(words, cap: str, width: float = 160) -> str:
    c = [w for w in words if w[4].upper().rstrip(".:") == cap]
    if not c:
        return ""
    w0 = max(c, key=lambda w: w[0])                         # the title-block caption (the revision table has its own 'DATE')
    ws = [w for w in words if abs((w[1] + w[3]) / 2 - (w0[1] + w0[3]) / 2) < 4 and w0[2] + 2 < w[0] < w0[2] + width]
    return _join([w for w in ws if w[4] not in ("!", ":")])


def title_block(page) -> dict:
    words = page.get_text("words")
    out = {"rev": _right_of(words, "REV"), "date": _right_of(words, "DATE", 110)}
    d = [w for w in words if w[4].upper() == "DOCUMENT"]
    if d:
        w0 = d[0]                                           # 'DOCUMENT NO.' caption; the number is printed under it
        ws = [w for w in words if w0[3] < (w[1] + w[3]) / 2 < w0[3] + 26 and w0[0] - 4 <= w[0] < w0[0] + 200]
        out["doc_no"] = _join([w for w in ws if w[4].upper().rstrip(".:") not in ("REV", "DATE", "SHEET", "OF", "NO")])
    return {k: v for k, v in out.items() if v}


# ── whole PDF ───────────────────────────────────────────────────────────────────────────────────────────────────────
_SUFFIX = re.compile(r"^(.*?\d)([A-Z])((?:/[A-Z])+)$")


def split_tags(raw: str, qty: str = "") -> list[str]:
    """'FT-1001A/B' → [FT1001A, FT1001B] · 'PT-1001, PT-1002' → two tags.  Tag keys (no spaces · hyphens · underscores)."""
    out = []
    for part in re.split(r"[,;&]|\s{2,}|\band\b", raw or ""):
        k = tag_key(part)
        if not k:
            continue
        m = _SUFFIX.match(k)
        if m:
            out += [m.group(1) + x for x in [m.group(2)] + m.group(3).split("/")[1:]]
        else:
            out.append(k)
    seen = []
    for k in out:
        if k not in seen:
            seen.append(k)
    return seen


def read_pdf(path: str, filename: str = "") -> dict:
    """Every datasheet in the PDF: one sheet per items page 1 (a block-2 page joins the sheet before it)."""
    import pymupdf
    doc = pymupdf.open(path, filetype="pdf")
    try:
        sheets, forms = [], {}
        for i, page in enumerate(doc):
            text = page.get_text()
            ident = identify_text(text, filename or Path(path).name)
            fid = ident["form_id"]
            if not fid:
                continue
            card = cards()[fid]
            roles = [r for r in card.get("page_roles", []) if r.get("role") == "items"]
            # which items block is this page?  the block whose labels this page prints most
            best, bscore = None, 0
            for r in roles:
                labs = [it["label"] for it in card["items"] if it.get("block") == r["block"] and it.get("page", 1) == r["page"] and it.get("label")]
                sc = sum(1 for lb in labs if lb in text) / max(1, len(labs))
                if sc > bscore:
                    best, bscore = r, sc
            if not best or bscore < 0.5:
                continue
            got = read_items_page(page, card, best["block"], best["page"])
            if best["page"] == roles[0]["page"] or not sheets or sheets[-1]["form_id"] != fid:
                sheets.append({"form_id": fid, "kind": card["item_kind"], "title": card.get("title", ""), "pages": [],
                               "identify": ident, "title_block": title_block(page), "rows": {}, "shift": got["shift"]})
            sh = sheets[-1]
            sh["pages"].append(i + 1)
            for no, v in got["rows"].items():
                sh["rows"][f"{best['block']}.{no}" if best["block"] != 1 else str(no)] = v | {"page": i + 1}
            forms[fid] = forms.get(fid, 0) + 1
        for sh in sheets:
            by = {v["std_key"]: v for v in sh["rows"].values() if v.get("std_key")}
            raw = (by.get("tag") or {}).get("value", "")
            sh["tag_raw"] = raw
            if not raw.strip() and by.get("tag"):                # the Tag row's only value sits after its second caption (form 80 'Item No.')
                subs = [v for v in (by["tag"].get("sub") or {}).values() if v.strip()]
                raw = subs[0] if len(subs) == 1 else ""
                sh["tag_raw"] = raw
            sh["tags"] = split_tags(raw, (by.get("tag_qty") or {}).get("value", ""))
            sh["test_data"] = "TEST DATA" in " ".join(doc[p - 1].get_text() for p in sh["pages"][:1]).upper()
        return {"pages": len(doc), "sheets": sheets, "forms": forms}
    finally:
        doc.close()


def values(sheet: dict) -> dict:
    """std_key → {value, sub, no, page} (first row with that key)."""
    out = {}
    for no, v in sheet["rows"].items():
        k = v.get("std_key")
        if k and k not in out:
            out[k] = {"value": v["value"], "sub": v.get("sub", {}), "no": no, "page": v.get("page"), "label": v["label"]}
        for lab, sk in (v.get("sub_keys") or {}).items():       # the second label of a shared row has its own key
            if sk and sk not in out:
                out[sk] = {"value": v.get("sub", {}).get(lab, ""), "sub": {}, "no": no, "page": v.get("page"), "label": lab}
    return out
