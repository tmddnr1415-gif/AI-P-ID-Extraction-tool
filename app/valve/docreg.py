"""Document · Revision register (valve40) — every document of one project family at a glance:
GET /api/valve/docreg?project=<base name>

A project family = the Ball project '<base>' and its kind projects '<base> · Globe Valve' · '· Butterfly Valve' · '· PSV'
(valve37); the Instrument datasheets live in the same projects (inst_sheet).  One row per document:
  Datasheet   one row per tag (Valve datasheet · Instrument datasheet): latest revision uploaded, latest revision whose
              review is finished (status Accepted · Resolved), revision history
  List        Instrument Index · IO List (one row per list kind / Doc. No.) · Valve List (TBE)
  PMS · Process Data · Line List    one row per uploaded file (same Doc. No. grouped: the newest upload is 'latest')
Nothing is computed that the documents or the review record do not say: an unread Rev / date / Doc. No. stays ''.
Read-only.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import Response

from app.valve import docrev, inst_api, instrument, schema, store

router = APIRouter()
DONE = ("Accepted", "Resolved")                            # review finished (Valve · Instrument use the same status words)
_KIND_SUFFIX = re.compile(r"\s*·\s*(Globe Valve|Butterfly Valve|PSV)$")
LABEL = {"ft": "FT · Flow Transmitter", "pt": "PT · Pressure / DP Tx", "lt": "LT · Level Tx (DP)", "gwr": "GWR · Level Tx (Radar)",
         "tt": "TT · Temperature Tx", "tg": "TG · Temperature Gauge", "pg": "PG · Pressure Gauge", "dpg": "DPG · DP Gauge",
         "mlg": "MLG · Mag. Level Gauge", "ro": "RO · Restriction Orifice", "analyzer": "AT · Analyzer", "cv": "CV · Control Valve",
         "onoff": "On-Off Valve", "psv": "PSV"}
DOC_KINDS = {"pms": ("PMS", "pms", "Piping Material Spec (PMS)"), "process": ("Process Data", "pds", "Process Data (PDS)"),
             "linelist": ("Line List", "linelist", "Process Line List"), "valvelist": ("List", "valvelist", "Valve List (TBE)")}


def base_name(name: str) -> str:
    return _KIND_SUFFIX.sub("", (name or "").strip())


def _audit_last(con, where: str, *args) -> dict:
    r = store.one(con, f"SELECT by, at FROM audit WHERE {where} ORDER BY id DESC", *args)
    return r or {}


def _doc(con, cache: dict, doc_id) -> dict:
    if doc_id not in cache:
        cache[doc_id] = store.one(con, "SELECT id, filename, uploaded_at, uploaded_by, path, info, kind FROM document WHERE id=?", doc_id) or {}
    return cache[doc_id]


def _by_rev(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: (store.rev_key(r["rev"]), r["id"]))


def _ds_row(con, cache, group_rows: list[dict], kind: str, kind_name: str, link, status_key: str, audit_where) -> dict:
    """One register row for one tag from all its revisions (already of one tag)."""
    revs = _by_rev(group_rows)
    top = revs[-1]
    d = _doc(con, cache, top["document_id"])
    done = [r for r in revs if r[status_key] in DONE]
    rv = None
    if done:
        r = done[-1]
        a = audit_where(r)
        rv = {"rev": r["rev"] or "", "status": r[status_key], "reviewed_at": a.get("at", ""), "reviewed_by": a.get("by", "")}
    return {"group": "Datasheet", "kind": kind, "kind_name": kind_name, "doc_no": top["doc_no"] or "", "title": top.get("title") or "", "tag": top["tag"],
            "latest": {"rev": top["rev"] or "", "date": top.get("rev_date") or "", "file": d.get("filename", ""), "uploaded_at": d.get("uploaded_at", ""),
                       "uploaded_by": d.get("uploaded_by", ""), "status": top[status_key]},
            "reviewed": rv, "revs": [r["rev"] or "" for r in revs], "pending": bool(not rv or rv["rev"] != (top["rev"] or "")),
            "link": link(top)}


def _doc_rev(con, d: dict) -> dict:
    """Doc. No. · header Rev · newest revision-table row of an uploaded PDF (kept in document.info['rev'] once read)."""
    info = d.get("info")
    info = json.loads(info) if isinstance(info, str) and info else (info or {})
    rv = info.get("rev") if isinstance(info.get("rev"), dict) else None
    if rv is None:
        rv = {}
        if str(d.get("filename", "")).lower().endswith(".pdf") and d.get("path") and Path(d["path"]).exists():
            rv = docrev.read(d["path"])
            rv.pop("parts", None)
    return {"info": info, "doc_no": rv.get("doc_no") or info.get("doc_no") or "", "rev": rv.get("rev") or rv.get("header_rev") or (info.get("rev") if isinstance(info.get("rev"), str) else "") or "",
            "date": rv.get("date") or ""}


def register(con, project: str) -> dict:
    base = base_name(project)
    projs = [p for p in store.rows(con, "SELECT id, name FROM project ORDER BY id") if base_name(p["name"]) == base]
    rows, cache = [], {}
    inst_api.con_ready()
    for p in projs:
        vk = schema.project_kind(p["name"])
        # Valve datasheets — one row per tag
        by_tag = {}
        for r in store.rows(con, "SELECT id, document_id, tag, tag_key, doc_no, rev, rev_date, title, review_status FROM datasheet WHERE project_id=?", p["id"]):
            by_tag.setdefault(r["tag_key"], []).append(r)
        for rs in by_tag.values():
            row = _ds_row(con, cache, rs, vk, schema.KINDS.get(vk, vk), lambda t, p=p, vk=vk: {"project": p["name"], "kind": vk, "ds": t["id"]}, "review_status",
                          lambda r: _audit_last(con, "datasheet_id=? AND action='status' AND after=?", r["id"], r["review_status"]))
            rows.append(row)
        # Instrument datasheets — one row per tag
        by_tag = {}
        for r in store.rows(con, "SELECT id, document_id, tag, tag_key, doc_no, rev, rev_date, kind, status FROM inst_sheet WHERE project_id=?", p["id"]):
            by_tag.setdefault((r["kind"], r["tag_key"]), []).append(r)
        for (k, _), rs in by_tag.items():
            row = _ds_row(con, cache, rs, k, LABEL.get(k, k.upper()), lambda t, p=p, k=k: {"project": p["name"], "kind": k, "sheet": t["id"]}, "status",
                          lambda r: _audit_last(con, "field_key=? AND action='inst-status' AND after=?", f"inst:{r['id']}", r["status"]))
            rows.append(row)
        # reference documents — PMS · Process Data · Line List · Valve List: one row per Doc. No. (or file), newest upload = latest
        docs = store.rows(con, "SELECT id, kind, filename, uploaded_at, uploaded_by, path, info FROM document WHERE project_id=? AND status='done' ORDER BY id", p["id"])
        groups = {}
        for d in docs:
            if d["kind"] in DOC_KINDS:
                x = _doc_rev(con, d)
                groups.setdefault((d["kind"], x["doc_no"] or d["filename"]), []).append((d, x))
            elif d["kind"] == "instlist":
                x = _doc_rev(con, d)
                lk = x["info"].get("list_kind") or "instrument_index"
                L = inst_api._load("instlist", d["id"]) or {}
                x["doc_no"], x["rev"] = L.get("doc_no") or x["doc_no"], L.get("rev") or x["info"].get("rev") or ""
                groups.setdefault(("instlist:" + lk, x["doc_no"] or lk), []).append((d, x))
        for (dk, _), items in groups.items():
            d, x = items[-1]
            if dk.startswith("instlist:"):
                lk = dk.split(":", 1)[1]
                grp, kind, name = "List", "iolist" if lk == "io_list" else "instindex", "IO List" if lk == "io_list" else "Instrument Index"
                link = {"project": p["name"], "kind": kind}
            else:
                grp, kind, name = DOC_KINDS[dk]
                link = {"project": p["name"], "kind": vk, "view": {"pms": "pms", "process": "proc", "linelist": "docs", "valvelist": "list"}[dk]}
            rows.append({"group": grp, "kind": kind, "kind_name": name, "doc_no": x["doc_no"], "title": d["filename"], "tag": "",
                         "latest": {"rev": x["rev"], "date": x["date"], "file": d["filename"], "uploaded_at": d["uploaded_at"], "uploaded_by": d["uploaded_by"], "status": ""},
                         "reviewed": None, "revs": [y["rev"] for _, y in items if y["rev"]] or [], "pending": False, "uploads": len(items),
                         "link": link})
    order = {"Datasheet": 0, "List": 1, "PMS": 2, "Process Data": 3, "Line List": 4}
    rows.sort(key=lambda r: (order.get(r["group"], 9), r["kind_name"], instrument.tag_key(r["tag"]), r["doc_no"]))
    n = {"rows": len(rows), "datasheets": sum(1 for r in rows if r["group"] == "Datasheet"),
         "pending": sum(1 for r in rows if r["group"] == "Datasheet" and r["pending"]),
         "reviewed": sum(1 for r in rows if r["group"] == "Datasheet" and not r["pending"])}
    return {"project": base, "projects": [p["name"] for p in projs], "at": store.now(), "done_status": list(DONE), "counts": n, "rows": rows}


@router.get("/api/valve/docreg")
def docreg(project: str = ""):
    con = inst_api.con_ready()
    return Response(json.dumps(register(con, project), ensure_ascii=False, default=str), media_type="application/json")
