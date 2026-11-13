"""Every datasheet read, kept as a JSON file (valve40, user 2026-11-13: "입력되는 datasheet 를 json 파일로 저장").

    <data>/valve/datasheets/<project>/<kind>/<Tag>__<Rev>.json          one file per tag × revision (Valve and Instrument)
    <data>/valve/datasheets/<project>/<kind>/_documents/<doc id>__<file>.json   one bundle per uploaded PDF

What is in it: tag · revision · form · every cell as read (value, unit, page, bbox on the page, status, the reviewer's
edit if any) · notes · revision table · document no. · source file name · sha256 · who uploaded it and when · when it
was read and written.  The files stay in the company's data folder (never in the repository; updates never touch it).
The review itself already runs from the database (cells) and the parsed Process Data / PMS / List files — the stored PDF
is needed only to show a page and draw a mark-up; these files are the readable record of what was read.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from app.valve import store

VERSION = 1


def _safe(s: str, n: int = 80) -> str:
    s = re.sub(r"[^A-Za-z0-9._\-]+", "_", (s or "").strip()).strip("._") or "_"
    return s[:n]


def base_dir() -> Path:
    return store.root() / "datasheets"


def _project(con, pid) -> tuple[str, str]:
    """(family folder, kind folder) — 'CO2 PJT · Globe Valve' → ('CO2_PJT', 'globe')."""
    from app.valve import docreg, schema
    p = store.one(con, "SELECT name FROM project WHERE id=?", pid) or {"name": f"project{pid}"}
    return _safe(docreg.base_name(p["name"])), schema.project_kind(p["name"])


def _doc(con, doc_id) -> dict:
    d = store.one(con, "SELECT id, filename, sha256, pages, uploaded_by, uploaded_at FROM document WHERE id=?", doc_id) or {}
    return {"id": d.get("id"), "filename": d.get("filename", ""), "sha256": d.get("sha256", ""), "pages": d.get("pages"),
            "uploaded_by": d.get("uploaded_by", ""), "uploaded_at": d.get("uploaded_at", "")}


def valve_record(con, dsid) -> dict | None:
    d = store.one(con, "SELECT * FROM datasheet WHERE id=?", dsid)
    if not d:
        return None
    fs = store.rows(con, "SELECT key, section, display, label, row, value, unit, page, bbox, status, ref, edited_value, edited_by, edited_at"
                         " FROM field WHERE datasheet_id=? ORDER BY row, id", dsid)
    cells = [{"key": f["key"], "label": f["label"], "section": f["section"], "row": f["row"], "value": f["value"] or "",
              "unit": f["unit"] or "", "page": f["page"], "bbox": store.unJ(f["bbox"]), "status": f["status"], "ref": f["ref"] or "",
              **({"edited": {"value": f["edited_value"], "by": f["edited_by"], "at": f["edited_at"]}} if f["edited_value"] is not None else {})}
             for f in fs]
    fam, kind = _project(con, d["project_id"])
    return {"format": "valve-datasheet", "v": VERSION, "project": fam, "kind": kind, "tag": d["tag"], "tag_key": d["tag_key"],
            "rev": d["rev"], "rev_date": d["rev_date"], "doc_no": d["doc_no"], "title": d["title"], "form": d["form"],
            "valve_type": d["valve_type"], "pages": store.unJ(d["pages"], []), "review_status": d["review_status"],
            "notes": store.unJ(d["notes"], []), "rev_history": store.unJ(d["rev_history"], []), "cells": cells,
            "source": _doc(con, d["document_id"]), "read_at": d["created_at"], "parser": d.get("parser_version") or "",
            "written_at": store.now()}


def inst_record(con, sid) -> dict | None:
    s = store.one(con, "SELECT * FROM inst_sheet WHERE id=?", sid)
    if not s:
        return None
    fam, _ = _project(con, s["project_id"])
    sheet = store.unJ(s["sheet"], {}) or {}
    return {"format": "instrument-datasheet", "v": VERSION, "project": fam, "kind": s["kind"], "tag": s["tag"], "tag_key": s["tag_key"],
            "rev": s["rev"], "rev_date": s["rev_date"], "doc_no": s["doc_no"], "form": s["form_id"], "pages": store.unJ(s["pages"], []),
            "test_data": bool(s["test_data"]), "review_status": s["status"], "sheet": sheet,
            "source": _doc(con, s["document_id"]), "read_at": s["created_at"], "written_at": store.now()}


def _path(rec: dict) -> Path:
    return base_dir() / rec["project"] / _safe(rec["kind"] or "other") / f"{_safe(rec['tag'])}__{_safe(rec['rev'] or '-')}.json"


def _write(p: Path, rec: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.part")
    tmp.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


def write_document(con, doc_id) -> list[str]:
    """The JSON of every datasheet read from one uploaded PDF, and the bundle of that PDF.  Returns the files written."""
    recs = [valve_record(con, r["id"]) for r in store.rows(con, "SELECT id FROM datasheet WHERE document_id=? ORDER BY id", doc_id)]
    try:
        recs += [inst_record(con, r["id"]) for r in store.rows(con, "SELECT id FROM inst_sheet WHERE document_id=? ORDER BY id", doc_id)]
    except Exception:                                        # noqa: BLE001  (no Instrument table yet)
        pass
    recs = [r for r in recs if r]
    if not recs:
        return []
    out = []
    for r in recs:
        p = _path(r)
        _write(p, r)
        out.append(str(p))
    src = recs[0]["source"]
    b = base_dir() / recs[0]["project"] / _safe(recs[0]["kind"] or "other") / "_documents" / f"{doc_id}__{_safe(Path(src['filename']).stem, 60)}.json"
    _write(b, {"format": "datasheet-document", "v": VERSION, "source": src, "count": len(recs),
               "datasheets": [{"tag": r["tag"], "rev": r["rev"], "kind": r["kind"], "file": str(_path(r).relative_to(base_dir()))} for r in recs],
               "written_at": store.now()})
    out.append(str(b))
    return out


def export_all(con, only_missing: bool = True, pid: int | None = None) -> dict:
    """Write the JSON of every datasheet already in the database (server start: only the missing ones)."""
    q = "SELECT DISTINCT document_id FROM datasheet" + (" WHERE project_id=?" if pid else "")
    docs = [r["document_id"] for r in store.rows(con, q, *([pid] if pid else []))]
    try:
        docs += [r["document_id"] for r in store.rows(con, "SELECT DISTINCT document_id FROM inst_sheet" + (" WHERE project_id=?" if pid else ""),
                                                      *([pid] if pid else []))]
    except Exception:                                        # noqa: BLE001
        pass
    n = w = 0
    for doc_id in dict.fromkeys(d for d in docs if d):
        n += 1
        if only_missing and any((base_dir()).glob(f"*/*/_documents/{doc_id}__*.json")):
            continue
        w += len(write_document(con, doc_id))
    return {"documents": n, "written": w, "folder": str(base_dir())}
