"""Valve Datasheet Review — /valve (screen) and /api/valve/* on the P&ID server (port 8000).

Same server, same rules as books · space · LOGIC: the dashboard opens /valve/?embed=1&user=<name>, the screen
sends that name back as X-Author, and every change is written under it (no separate login).

Batch upload runs in a background thread; the screen polls /api/valve/jobs/{id} for page progress.
Nothing here decides compliance: extraction is read from the PDF, comparisons are rule-based, and every
result carries the page and box it came from.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import re
import threading
import traceback
import uuid
from pathlib import Path
from urllib.parse import quote, unquote

import pymupdf
from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from starlette.concurrency import run_in_threadpool

from app import paths
from app.valve import exports, extract, issues as issuesmod, material, pms as pmsmod, schema, store, tbe

router = APIRouter()
_JOBS: dict[str, dict] = {}
_JLOCK = threading.Lock()
_STATIC = {"valve.js": "application/javascript", "valve.css": "text/css"}
KINDS = ("datasheet", "valvelist", "process", "pms")


def _user(request: Request) -> str:
    raw = request.headers.get("x-author") or ""
    return re.sub(r"\s+", " ", unquote(raw)).strip()[:40] or "(이름 없음)"


def _err(msg, code=400):
    return JSONResponse({"error": msg}, status_code=code)


# ── screen ──────────────────────────────────────────────────────────────────────

def _static(name: str) -> Path:
    return paths.resource("app", "static", "valve", name)


@router.get("/valve")
def valve_redirect(request: Request):
    qs = request.url.query
    return RedirectResponse("/valve/" + (f"?{qs}" if qs else ""), status_code=307)


@router.get("/valve/")
def valve_page():
    return FileResponse(_static("index.html"), media_type="text/html", headers={"Cache-Control": "no-store"})


@router.get("/valve/{name}")
def valve_file(name: str):
    if name not in _STATIC:
        return _err("없는 파일", 404)
    return FileResponse(_static(name), media_type=_STATIC[name], headers={"Cache-Control": "no-cache"})


# ── projects ────────────────────────────────────────────────────────────────────

@router.get("/api/valve/projects")
def projects():
    con = store.connect()
    out = store.rows(con, "SELECT p.*, (SELECT COUNT(DISTINCT tag_key) FROM datasheet d WHERE d.project_id=p.id) AS tags,"
                          " (SELECT COUNT(*) FROM document d WHERE d.project_id=p.id) AS docs FROM project p ORDER BY p.id")
    return {"projects": out}


@router.post("/api/valve/projects")
async def project_new(request: Request):
    body = await request.json()
    con = store.connect()
    try:
        return store.project_get_or_create(con, body.get("name", ""))
    except ValueError as e:
        return _err(str(e))


def _latest(dss: list[dict]) -> dict[str, dict]:
    """tag_key -> newest datasheet (revision order A<B<…<0<1…, then upload order)."""
    out = {}
    for d in sorted(dss, key=lambda d: (store.rev_key(d["rev"]), d["id"])):
        out[d["tag_key"]] = d
    return out


@router.get("/api/valve/projects/{pid}/summary")
def summary(pid: int):
    con = store.connect()
    p = store.one(con, "SELECT * FROM project WHERE id=?", pid)
    if not p:
        return _err("없는 프로젝트", 404)
    dss = store.rows(con, "SELECT id, tag, tag_key, valve_type, rev, review_status, doc_no, document_id, created_at"
                          " FROM datasheet WHERE project_id=?", pid)
    latest = _latest(dss)
    revs = {}
    for d in dss:
        revs.setdefault(d["tag_key"], set()).add(d["rev"])
    issues = {r["datasheet_id"]: r["n"] for r in store.rows(
        con, "SELECT datasheet_id, COUNT(*) AS n FROM field WHERE status IN ('review') AND edited_value IS NULL"
             " AND datasheet_id IN (SELECT id FROM datasheet WHERE project_id=?) GROUP BY datasheet_id", pid)}
    docs = store.rows(con, "SELECT id, kind, filename, pages, uploaded_by, uploaded_at, status, error, info FROM document"
                           " WHERE project_id=? ORDER BY id DESC", pid)
    for d in docs:
        d["info"] = store.unJ(d["info"], {})
    vl = next((d for d in docs if d["kind"] == "valvelist" and d["status"] == "done"), None)
    vl_tags = set()
    if vl:
        for s in vl["info"].get("sheets", []):
            vl_tags |= {schema.norm_tag(t) for t in s.get("tags", [])}
    done = sum(1 for d in latest.values() if d["review_status"] in ("Accepted", "Resolved"))
    has_pms = any(d["kind"] == "pms" and d["status"] == "done" for d in docs)
    irows = project_issues(con, pid) if latest else []
    ic = _issue_counts(irows)
    per_tag = {}
    for i in irows:
        if i["status"] != "Dismissed" and i["severity"] in ("Major", "Minor"):
            per_tag[i["ds_id"]] = per_tag.get(i["ds_id"], 0) + 1
    activity = store.rows(con, "SELECT a.*, d.tag, d.rev FROM audit a LEFT JOIN datasheet d ON d.id=a.datasheet_id"
                               " WHERE a.project_id=? ORDER BY a.id DESC LIMIT 30", pid)
    return {
        "project": p,
        "kpi": {"tags": len(latest), "datasheets": len(dss),
                "new_tags": len([k for k in latest if vl and k not in vl_tags]),
                "revision_changes": sum(1 for v in revs.values() if len(v) > 1),
                "process_mismatch": None,                              # Phase 3 engine not connected yet
                "pms_noncompliant": (ic.get("PMS Non-Compliance", 0) if has_pms else None),
                "data_errors": ic.get("Data Error", 0), "data_missing": ic.get("Data Missing", 0),
                "open_items": ic.get("Open Item", 0), "pms_review": ic.get("PMS Review", 0) if has_pms else None,
                "pending": len(latest) - done, "completed": done,
                "review_required": sum(issues.get(d["id"], 0) for d in latest.values())},
        "has_valvelist": bool(vl),
        "has_pms": has_pms,
        "tags": [dict(d, issues=issues.get(d["id"], 0), problems=per_tag.get(d["id"], 0), revs=sorted(revs[k], key=store.rev_key),
                      in_valvelist=(k in vl_tags) if vl else None) for k, d in sorted(latest.items())],
        "documents": docs,
        "activity": activity,
    }


# ── upload / batch ──────────────────────────────────────────────────────────────

def _job(jid, **kw):
    with _JLOCK:
        _JOBS[jid].update(kw)


def _process(jid: str, pid: int, items: list[tuple[int, str, str, Path]], by: str):
    con = store.connect()
    total = sum(max(1, it[4]) for it in items)
    done = 0
    for doc_id, kind, name, path, pages in items:
        _job(jid, file=name)
        try:
            con.execute("UPDATE document SET status='running' WHERE id=?", (doc_id,))
            con.commit()
            if kind == "datasheet":
                def prog(i, n, base=done):
                    _job(jid, done=base + i, msg=f"{name} · {i}/{n} 쪽")
                res = extract.read_pdf(str(path), progress=prog)
                dss = extract.group_datasheets(res)
                n_scan = sum(1 for o in res["other_pages"] if o.get("kind") == "scanned")
                with store._LOCK:
                    for ds in dss:
                        ds["form"] = "102" if any(r.get("row", 0) > 61 for r in ds["fields"].values()) else "on/off"
                        dup = store.one(con, "SELECT id FROM datasheet WHERE project_id=? AND tag_key=? AND rev=? AND"
                                             " document_id IN (SELECT id FROM document WHERE sha256=(SELECT sha256 FROM"
                                             " document WHERE id=?))", pid, ds["tag_key"], ds["rev"], doc_id)
                        if dup:
                            continue
                        store.insert_datasheet(con, pid, doc_id, ds)
                    info = {"datasheets": len(dss), "tags": sorted({d["tag"] for d in dss}),
                            "docs": {k: {"title": v.get("title"), "rev": v.get("rev"),
                                         "general_notes": v.get("general_notes", {})} for k, v in res["docs"].items()},
                            "scanned_pages": n_scan}
                    con.execute("UPDATE document SET status='done', info=? WHERE id=?", (store.J(info), doc_id))
                    store.audit(con, pid, None, None, "upload", None, name, by, f"{len(dss)} datasheets")
                    con.commit()
                if n_scan:
                    _job(jid, warn=f"{name}: 글자층이 없는 쪽 {n_scan}장 (스캔본) — 이 판에서는 읽지 못했습니다")
            elif kind == "valvelist":
                data = path.read_bytes()
                if path.suffix.lower() == ".xls":
                    data = tbe.xls_to_xlsx(data)
                    conv = path.with_suffix(".xlsx")
                    conv.write_bytes(data)
                    con.execute("UPDATE document SET path=? WHERE id=?", (str(conv), doc_id))
                info = tbe.describe(data)
                con.execute("UPDATE document SET status='done', info=? WHERE id=?", (store.J(info), doc_id))
                store.audit(con, pid, None, None, "upload", None, name, by, "valve list")
                con.commit()
            elif kind == "pms":                          # class sheets -> {data}/valve/pms/<doc>.json (pms.read_pms)
                def prog(i, n, base=done):
                    _job(jid, done=base + i, msg=f"{name} · PMS {i}/{n} 쪽")
                parsed = pmsmod.read_pms(str(path), progress=prog)
                store.write_json(store.root() / "pms" / f"{doc_id}.json", parsed)
                _PMS_CACHE.pop(doc_id, None)
                info = {"areas": {a: len(c) for a, c in parsed["areas"].items()},
                        "classes": sorted({k for c in parsed["areas"].values() for k in c}),
                        "note": f"Class {sum(len(c) for c in parsed['areas'].values())}개 읽음 — PMS Compliance 에 바로 쓰입니다"}
                con.execute("UPDATE document SET status='done', info=? WHERE id=?", (store.J(info), doc_id))
                store.audit(con, pid, None, None, "upload", None, name, by, "pms")
                con.commit()
            else:                                        # process: kept, indexed by page; engine is Phase 3
                info = {"note": "보관됨 — Process Data 비교 엔진은 다음 단계(Phase 3)에서 연결됩니다"}
                con.execute("UPDATE document SET status='done', info=? WHERE id=?", (store.J(info), doc_id))
                con.commit()
        except Exception as e:                           # noqa: BLE001 — one bad file must not stop the batch
            con.execute("UPDATE document SET status='error', error=? WHERE id=?", (f"{type(e).__name__}: {e}", doc_id))
            con.commit()
            with _JLOCK:
                _JOBS[jid]["errors"].append({"file": name, "error": str(e)[:300], "trace": traceback.format_exc()[-800:]})
        done += max(1, pages)
        _job(jid, done=done)
    if any(it[1] == "datasheet" for it in items) and _JOBS[jid].get("base") is not None:
        _auto_export(jid, pid, _JOBS[jid]["base"], by)
    _job(jid, status="done", msg="끝", total=total, done=total)


@router.post("/api/valve/projects/{pid}/upload")
async def upload(pid: int, request: Request, kind: str = Form(...), files: list[UploadFile] = File(...)):
    if kind not in KINDS:
        return _err("자료 종류가 잘못됐습니다")
    by = _user(request)
    con = store.connect()
    if not store.one(con, "SELECT id FROM project WHERE id=?", pid):
        return _err("없는 프로젝트", 404)
    items, skipped = [], []
    for f in files:
        data = await f.read()
        name = Path(f.filename or "file").name
        ext = Path(name).suffix.lower()
        ok = {"datasheet": (".pdf",), "valvelist": (".xlsx", ".xlsm", ".xls"), "process": (".pdf", ".xlsx", ".xls"),
              "pms": (".pdf",)}[kind]
        if ext not in ok:
            skipped.append(f"{name} — {kind} 칸에는 {' · '.join(ok)} 만 넣을 수 있습니다")
            continue
        sha, path = store.save_original(data, name)
        pages = 0
        if ext == ".pdf":
            try:
                with pymupdf.open(stream=data, filetype="pdf") as d:
                    pages = d.page_count
            except Exception:                            # noqa: BLE001
                skipped.append(f"{name} — PDF 를 열 수 없습니다 (손상되었거나 암호가 걸림)")
                continue
        cur = con.execute("INSERT INTO document(project_id, kind, filename, sha256, path, pages, uploaded_by, uploaded_at,"
                          " status) VALUES (?,?,?,?,?,?,?,?,'queued')",
                          (pid, kind, name, sha, str(path), pages, by, store.now()))
        items.append((cur.lastrowid, kind, name, path, pages))
    con.commit()
    if not items:
        return _err("올릴 파일이 없습니다 — " + "; ".join(skipped) if skipped else "올릴 파일이 없습니다")
    jid = uuid.uuid4().hex[:12]
    _JOBS[jid] = {"id": jid, "status": "running", "done": 0, "total": sum(max(1, it[4]) for it in items),
                  "msg": "", "file": "", "errors": [], "skipped": skipped, "warn": "", "base": _base(request), "exports": []}
    threading.Thread(target=_process, args=(jid, pid, items, by), daemon=True).start()
    return _JOBS[jid]


@router.get("/api/valve/jobs/{jid}")
def job(jid: str):
    j = _JOBS.get(jid)
    return j if j else _err("없는 작업", 404)


@router.post("/api/valve/documents/{doc_id}/retry")
def retry(doc_id: int, request: Request):
    con = store.connect()
    d = store.one(con, "SELECT * FROM document WHERE id=?", doc_id)
    if not d:
        return _err("없는 문서", 404)
    jid = uuid.uuid4().hex[:12]
    _JOBS[jid] = {"id": jid, "status": "running", "done": 0, "total": max(1, d["pages"] or 1), "msg": "", "file": "",
                  "errors": [], "skipped": [], "warn": "", "base": _base(request), "exports": []}
    item = (d["id"], d["kind"], d["filename"], Path(d["path"]), d["pages"] or 0)
    threading.Thread(target=_process, args=(jid, d["project_id"], [item], _user(request)), daemon=True).start()
    return _JOBS[jid]


# ── datasheets ──────────────────────────────────────────────────────────────────

_PMS_CACHE: dict[int, dict] = {}


def _pms_for(con, pid):
    """(parsed PMS, document row) of the project's newest PMS upload, or (None, None)."""
    doc = store.one(con, "SELECT id, filename FROM document WHERE project_id=? AND kind='pms' AND status='done'"
                         " ORDER BY id DESC", pid)
    if not doc:
        return None, None
    if doc["id"] not in _PMS_CACHE:
        p = store.root() / "pms" / f"{doc['id']}.json"
        if not p.exists():
            return None, None
        _PMS_CACHE[doc["id"]] = json.loads(p.read_text(encoding="utf-8"))
    return _PMS_CACHE[doc["id"]], doc


def _ds_full(con, dsid, deep=True):
    d = store.one(con, "SELECT * FROM datasheet WHERE id=?", dsid)
    if not d:
        return None
    for k in ("pages", "notes", "rev_history", "sheets"):
        d[k] = store.unJ(d.get(k), [])
    fs = store.rows(con, "SELECT * FROM field WHERE datasheet_id=? ORDER BY row, id", dsid)
    for f in fs:
        f["bbox"], f["ref"] = store.unJ(f["bbox"]), store.unJ(f["ref"])
    d["fields"] = fs
    doc = store.one(con, "SELECT id, filename, info FROM document WHERE id=?", d["document_id"])
    d["filename"] = doc["filename"] if doc else ""
    gn = (store.unJ(doc["info"], {}) or {}).get("docs", {}).get(d["doc_no"], {}) if doc else {}
    d["general_notes"] = gn.get("general_notes", {})
    d["revisions"] = store.rows(con, "SELECT id, rev, doc_no, document_id, created_at FROM datasheet WHERE project_id=?"
                                     " AND tag_key=? ORDER BY id", d["project_id"], d["tag_key"])
    d["revisions"].sort(key=lambda r: (store.rev_key(r["rev"]), r["id"]))
    d["comments"] = store.rows(con, "SELECT * FROM comment WHERE datasheet_id=? AND deleted=0 ORDER BY id", dsid)
    for c in d["comments"]:
        c["bbox"] = store.unJ(c["bbox"])
    d["history"] = store.rows(con, "SELECT * FROM audit WHERE datasheet_id=? ORDER BY id DESC", dsid)
    d["doc_title"] = (gn or {}).get("title", "")
    d["area"] = pmsmod.area_of_title(d["doc_title"])
    if not deep:
        return d
    pms, pdoc = _pms_for(con, d["project_id"])
    F = {f["key"]: f for f in fs}
    d["pms"] = pmsmod.check(F, pms, d["area"]) if pms else None
    d["pms_doc"] = pdoc
    prev = None
    i = next((n for n, r in enumerate(d["revisions"]) if r["id"] == d["id"]), 0)
    if i > 0:
        prev = compare(_ds_full(con, d["revisions"][i - 1]["id"], deep=False), d)
    states = {r["ikey"]: r for r in store.rows(con, "SELECT * FROM issue_state WHERE datasheet_id=?", dsid)}
    d["issues"] = issuesmod.compute(d, d["general_notes"], pms, d["area"], prev, states)
    return d


@router.get("/api/valve/datasheets/{dsid}")
def datasheet(dsid: int):
    d = _ds_full(store.connect(), dsid)
    return d if d else _err("없는 데이터시트", 404)


@router.put("/api/valve/datasheets/{dsid}/fields/{fid}")
async def field_edit(dsid: int, fid: int, request: Request):
    body = await request.json()
    by = _user(request)
    con = store.connect()
    f = store.one(con, "SELECT f.*, d.project_id FROM field f JOIN datasheet d ON d.id=f.datasheet_id"
                       " WHERE f.id=? AND f.datasheet_id=?", fid, dsid)
    if not f:
        return _err("없는 칸", 404)
    new = body.get("value")
    if new is not None:
        new = str(new)[:2000]
        if new == (f["value"] or ""):
            new = None                                   # back to what the sheet says
    before = store.field_value(f)
    with store._LOCK:
        con.execute("UPDATE field SET edited_value=?, edited_by=?, edited_at=? WHERE id=?",
                    (new, by if new is not None else None, store.now() if new is not None else None, fid))
        store.audit(con, f["project_id"], dsid, f["key"], "edit" if new is not None else "revert", before,
                    new if new is not None else f["value"], by, body.get("comment", ""))
        con.commit()
    return _ds_full(con, dsid)


@router.put("/api/valve/datasheets/{dsid}/status")
async def ds_status(dsid: int, request: Request):
    body = await request.json()
    st = body.get("status")
    if st not in store.REVIEW_STATUSES:
        return _err("상태 값이 잘못됐습니다")
    con = store.connect()
    d = store.one(con, "SELECT * FROM datasheet WHERE id=?", dsid)
    if not d:
        return _err("없는 데이터시트", 404)
    with store._LOCK:
        con.execute("UPDATE datasheet SET review_status=? WHERE id=?", (st, dsid))
        store.audit(con, d["project_id"], dsid, None, "status", d["review_status"], st, _user(request), body.get("comment", ""))
        con.commit()
    return _ds_full(con, dsid)


@router.post("/api/valve/datasheets/{dsid}/comments")
async def ds_comment(dsid: int, request: Request):
    body = await request.json()
    text = str(body.get("text", "")).strip()[:4000]
    if not text:
        return _err("내용이 비었습니다")
    con = store.connect()
    d = store.one(con, "SELECT project_id FROM datasheet WHERE id=?", dsid)
    if not d:
        return _err("없는 데이터시트", 404)
    by = _user(request)
    with store._LOCK:
        bbox = body.get("bbox")
        if bbox is not None and not (isinstance(bbox, list) and len(bbox) == 4):
            return _err("bbox 형식이 잘못됐습니다")
        con.execute("INSERT INTO comment(datasheet_id, field_key, text, by, at, page, bbox, category) VALUES (?,?,?,?,?,?,?,?)",
                    (dsid, body.get("field_key"), text, by, store.now(), body.get("page"), store.J(bbox), "comment"))
        store.audit(con, d["project_id"], dsid, body.get("field_key"), "comment", None, text, by)
        con.commit()
    return _ds_full(con, dsid)


@router.put("/api/valve/comments/{cid}")
async def comment_edit(cid: int, request: Request):
    body = await request.json()
    con = store.connect()
    c = store.one(con, "SELECT c.*, d.project_id FROM comment c JOIN datasheet d ON d.id=c.datasheet_id WHERE c.id=?", cid)
    if not c:
        return _err("없는 주석", 404)
    by = _user(request)
    with store._LOCK:
        if body.get("delete"):
            con.execute("UPDATE comment SET deleted=1 WHERE id=?", (cid,))
            store.audit(con, c["project_id"], c["datasheet_id"], c["field_key"], "comment-delete", c["text"], None, by)
        else:
            text = str(body.get("text", "")).strip()[:4000]
            if not text:
                return _err("내용이 비었습니다")
            con.execute("UPDATE comment SET text=? WHERE id=?", (text, cid))
            store.audit(con, c["project_id"], c["datasheet_id"], c["field_key"], "comment-edit", c["text"], text, by)
        con.commit()
    return _ds_full(con, c["datasheet_id"])


# ── issues (rule-based — app/valve/issues.py) ──────────────────────────────────

_ISSUE_CACHE: dict[int, tuple] = {}
ISSUE_STATUSES = ["Open", "Confirmed", "Dismissed", "Resolved"]


def project_issues(con, pid) -> list[dict]:
    """Issues of the newest revision of every tag, with tag · doc · file on each row.  Cached until the next write
    (every write leaves an audit row, so the newest audit id is the version)."""
    ver = (con.execute("SELECT COALESCE(MAX(id),0) FROM audit WHERE project_id=?", (pid,)).fetchone()[0],
           con.execute("SELECT COUNT(*) FROM document WHERE project_id=?", (pid,)).fetchone()[0])
    hit = _ISSUE_CACHE.get(pid)
    if hit and hit[0] == ver:
        return hit[1]
    latest = _latest(store.rows(con, "SELECT id, tag_key, rev FROM datasheet WHERE project_id=?", pid))
    out = []
    for d in sorted(latest.values(), key=lambda d: d["tag_key"]):
        x = _ds_full(con, d["id"])
        for i in x["issues"]:
            out.append(dict(i, ds_id=x["id"], tag=x["tag_key"], tag_raw=x["tag"], valve_type=x["valve_type"],
                            doc_no=x["doc_no"], rev=x["rev"], document_id=x["document_id"], filename=x["filename"],
                            review_status=x["review_status"]))
    _ISSUE_CACHE[pid] = (ver, out)
    return out


def _issue_counts(rows):
    c = {}
    for i in rows:
        if i["status"] == "Dismissed":
            continue
        c[i["type"]] = c.get(i["type"], 0) + 1
    return c


@router.get("/api/valve/projects/{pid}/issues")
async def issues_list(pid: int):
    con = store.connect()
    rows = await run_in_threadpool(project_issues, con, pid)
    return {"issues": rows, "counts": _issue_counts(rows), "types": issuesmod.CONTRACTOR_TYPES + ["Extraction Review"],
            "statuses": ISSUE_STATUSES}


@router.put("/api/valve/datasheets/{dsid}/issues/{ikey:path}")
async def issue_state(dsid: int, ikey: str, request: Request):
    body = await request.json()
    st = body.get("status", "Open")
    if st not in ISSUE_STATUSES:
        return _err("상태 값이 잘못됐습니다")
    con = store.connect()
    d = store.one(con, "SELECT project_id FROM datasheet WHERE id=?", dsid)
    if not d:
        return _err("없는 데이터시트", 404)
    by = _user(request)
    with store._LOCK:
        old = store.one(con, "SELECT * FROM issue_state WHERE datasheet_id=? AND ikey=?", dsid, ikey)
        con.execute("INSERT OR REPLACE INTO issue_state(datasheet_id, ikey, status, note, by, at) VALUES (?,?,?,?,?,?)",
                    (dsid, ikey, st, str(body.get("note", ""))[:2000], by, store.now()))
        store.audit(con, d["project_id"], dsid, ikey, "issue", (old or {}).get("status", "Open"), st, by, body.get("note", ""))
        con.commit()
    return {"ok": True, "status": st}


# ── revision comparison (deterministic, by extracted field) ─────────────────────

def compare(prev: dict, new: dict) -> list[dict]:
    pf = {f["key"]: f for f in prev["fields"]}
    nf = {f["key"]: f for f in new["fields"]}
    out = []
    for k in list(dict.fromkeys(list(pf) + list(nf))):
        a, b = pf.get(k), nf.get(k)
        va, vb = (store.field_value(a) if a else ""), (store.field_value(b) if b else "")
        ua, ub = (a or {}).get("unit") or "", (b or {}).get("unit") or ""
        if (va, ua) == (vb, ub) or (va and vb and ua == ub and material.same(va, vb)):
            kind = "Unchanged"                           # '316 SS / HF' -> 'SS 316/HF' is the same value
        elif not va and vb:
            kind = "Added"
        elif va and not vb:
            kind = "Deleted"
        else:
            kind = "Modified"
        ref = b or a
        out.append({"key": k, "display": ref.get("display") or k, "section": ref.get("section"), "row": ref.get("row"),
                    "previous": va, "new": vb, "unit": ub or ua, "change": kind,
                    "prev_page": (a or {}).get("page"), "prev_bbox": (a or {}).get("bbox"),
                    "new_page": (b or {}).get("page"), "new_bbox": (b or {}).get("bbox")})
    pn = {n["no"]: n for n in prev["notes"]}
    nn = {n["no"]: n for n in new["notes"]}
    for no in sorted(set(pn) | set(nn)):
        a, b = pn.get(no), nn.get(no)
        va, vb = (a or {}).get("text", ""), (b or {}).get("text", "")
        kind = "Unchanged" if va == vb else "Added" if not va else "Deleted" if not vb else "Modified"
        out.append({"key": f"note.{no}", "display": f"Note {no}", "section": "notes", "row": None, "previous": va,
                    "new": vb, "unit": "", "change": kind, "prev_page": (a or {}).get("page"), "prev_bbox": (a or {}).get("bbox"),
                    "new_page": (b or {}).get("page"), "new_bbox": (b or {}).get("bbox")})
    return out


@router.get("/api/valve/compare")
def compare_api(prev: int, new: int):
    con = store.connect()
    a, b = _ds_full(con, prev), _ds_full(con, new)
    if not a or not b:
        return _err("없는 데이터시트", 404)
    if a["tag_key"] != b["tag_key"]:
        return _err("같은 Tag 의 Revision 끼리만 비교합니다 (spec rule 7)")
    return {"prev": {k: a[k] for k in ("id", "tag", "rev", "doc_no", "document_id", "filename", "pages")},
            "new": {k: b[k] for k in ("id", "tag", "rev", "doc_no", "document_id", "filename", "pages")},
            "rows": compare(a, b)}


# ── PDF pages ───────────────────────────────────────────────────────────────────

_RENDER_LOCK = threading.Lock()


def _render(doc_id: int, page: int, zoom: float) -> bytes:
    con = store.connect()
    d = store.one(con, "SELECT path FROM document WHERE id=?", doc_id)
    if not d:
        raise FileNotFoundError("문서 없음")
    cache = store.root() / "cache" / f"{doc_id}_{page}_{int(zoom * 100)}.png"
    if cache.exists():
        return cache.read_bytes()
    with _RENDER_LOCK, pymupdf.open(d["path"]) as pdf:
        if not 1 <= page <= pdf.page_count:
            raise IndexError("쪽 번호가 범위 밖입니다")
        png = pdf[page - 1].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False).tobytes("png")
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(png)
    return png


@router.get("/api/valve/documents/{doc_id}/page/{page}.png")
async def page_png(doc_id: int, page: int, zoom: float = 2.0):
    zoom = max(0.5, min(4.0, zoom))
    try:
        png = await run_in_threadpool(_render, doc_id, page, zoom)
    except (FileNotFoundError, IndexError) as e:
        return _err(str(e), 404)
    return Response(png, media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})


@router.get("/api/valve/documents/{doc_id}/pageinfo")
def page_info(doc_id: int):
    con = store.connect()
    d = store.one(con, "SELECT path, pages FROM document WHERE id=?", doc_id)
    if not d:
        return _err("없는 문서", 404)
    with pymupdf.open(d["path"]) as pdf:
        sizes = [[round(p.rect.width, 1), round(p.rect.height, 1)] for p in pdf]
    return {"pages": len(sizes), "sizes": sizes}


@router.get("/api/valve/documents/{doc_id}/search")
def page_search(doc_id: int, q: str, page: int | None = None):
    con = store.connect()
    d = store.one(con, "SELECT path FROM document WHERE id=?", doc_id)
    if not d or not q.strip():
        return {"hits": []}
    hits = []
    with pymupdf.open(d["path"]) as pdf:
        rng = [page - 1] if page else range(pdf.page_count)
        for i in rng:
            for r in pdf[i].search_for(q.strip())[:50]:
                hits.append({"page": i + 1, "bbox": [round(r.x0, 1), round(r.y0, 1), round(r.x1, 1), round(r.y1, 1)]})
            if len(hits) > 300:
                break
    return {"hits": hits}


@router.get("/api/valve/documents/{doc_id}/file")
def doc_file(doc_id: int):
    con = store.connect()
    d = store.one(con, "SELECT path, filename FROM document WHERE id=?", doc_id)
    if not d:
        return _err("없는 문서", 404)
    return FileResponse(d["path"], filename=d["filename"], content_disposition_type="inline")


# ── Valve List grid (latest revision per tag) ─────────────────────────────────

GRID_KEYS = ["valve_type", "service", "pid_no", "line_no", "body_size", "rating", "body_type", "connections",
             "body_material", "ball_material", "stem_material", "seat_material", "packing_material", "piping_class",
             "tightness", "leakage_class", "fireproofing", "fire_safe", "nace", "sil", "act_type", "fail_position",
             "sov", "pos_tx", "afr", "manufacturer", "model"]


@router.get("/api/valve/projects/{pid}/grid")
def grid(pid: int):
    con = store.connect()
    latest = _latest(store.rows(con, "SELECT id, tag_key, rev FROM datasheet WHERE project_id=?", pid))
    ids = [d["id"] for d in latest.values()]
    if not ids:
        return {"columns": [], "rows": []}
    q = ",".join("?" * len(ids))
    meta = {d["id"]: d for d in store.rows(con, f"SELECT id, tag, tag_key, valve_type, rev, doc_no, review_status, pages,"
                                                f" document_id FROM datasheet WHERE id IN ({q})", *ids)}
    fields = store.rows(con, f"SELECT id, datasheet_id, key, display, value, unit, edited_value, status, page, bbox FROM field"
                             f" WHERE datasheet_id IN ({q})", *ids)
    disp, by = {}, {}
    for f in fields:
        by.setdefault(f["datasheet_id"], {})[f["key"]] = f
        disp.setdefault(f["key"], f["display"])
    notes = {d["id"]: len(store.unJ(store.one(con, "SELECT notes FROM datasheet WHERE id=?", d["id"])["notes"], []))
             for d in latest.values()}
    rows_ = []
    for i in ids:
        m, fs = meta[i], by.get(i, {})
        cells = {}
        for k in GRID_KEYS:
            if k == "valve_type":
                continue
            f = fs.get(k)
            if f:
                cells[k] = {"v": store.field_value(f), "u": f["unit"] or "", "id": f["id"], "st": f["status"],
                            "ed": f["edited_value"] is not None, "p": f["page"], "b": store.unJ(f["bbox"])}
        rows_.append({"id": i, "tag": m["tag_key"], "tag_raw": m["tag"], "valve_type": m["valve_type"], "rev": m["rev"],
                      "doc_no": m["doc_no"], "status": m["review_status"], "notes": notes.get(i, 0),
                      "document_id": m["document_id"], "page": store.unJ(m["pages"], [None])[0],
                      "pages": store.unJ(m["pages"], []), "cells": cells})
    rows_.sort(key=lambda r: r["tag"])
    cols = [{"key": k, "title": "Valve Type" if k == "valve_type" else disp.get(k, k)} for k in GRID_KEYS
            if k == "valve_type" or k in disp]
    return {"columns": cols, "rows": rows_}


# ── marked-up PDF (annotations on a copy — the original is never written) ───────

COLORS = {"revision": (1, 0.85, 0), "pms": (0.86, 0.15, 0.15), "process": (1, 0.55, 0), "comment": (0.18, 0.4, 0.9)}


@router.post("/api/valve/markup.pdf")
async def markup_pdf(request: Request):
    """Body: {document_id, pages?: [n…] (only these pages, in order), items: [{page, bbox, category, title, text}]}."""
    body = await request.json()
    con = store.connect()
    d = store.one(con, "SELECT path, filename, project_id FROM document WHERE id=?", body.get("document_id"))
    if not d:
        return _err("없는 문서", 404)
    items = body.get("items") or []

    def make():
        with pymupdf.open(d["path"]) as pdf:
            for it in items:
                pno, bb = int(it.get("page") or 0), it.get("bbox")
                if not (1 <= pno <= pdf.page_count) or not bb:
                    continue
                pg = pdf[pno - 1]
                r = pymupdf.Rect(*bb) + (-1.5, -1.5, 1.5, 1.5)
                col = COLORS.get(it.get("category"), COLORS["comment"])
                a = pg.add_rect_annot(r) if it.get("category") == "comment" else pg.add_highlight_annot(r)
                a.set_colors(stroke=col)
                a.set_info(title=str(it.get("title", ""))[:120], content=str(it.get("text", ""))[:2000])
                if it.get("category") == "comment":
                    a.set_border(width=1.2)
                a.update(opacity=0.45 if it.get("category") != "comment" else 1)
            keep = [p - 1 for p in body.get("pages") or [] if 1 <= int(p) <= pdf.page_count]
            if keep:
                pdf.select(keep)
            return pdf.tobytes(garbage=3, deflate=True)
    data = await run_in_threadpool(make)
    store.audit(con, d["project_id"], None, None, "markup-export", None, d["filename"], _user(request), f"{len(items)} items")
    con.commit()
    fn = f"{Path(d['filename']).stem}_markup_{store.now()[:10]}.pdf"
    return Response(data, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(fn)}"})


# ── exports ─────────────────────────────────────────────────────────────────────

def _base(request: Request) -> str:
    """Address the links in exported files point to (the server as the user reached it)."""
    return str(request.base_url).rstrip("/")


def _export_valvelist(pid: int, base: str = ""):
    con = store.connect()
    pname = (store.one(con, "SELECT name FROM project WHERE id=?", pid) or {}).get("name", "")
    dss = store.rows(con, "SELECT id, tag_key, rev FROM datasheet WHERE project_id=?", pid)
    latest = _latest(dss)
    full = []
    for d in latest.values():
        x = _ds_full(con, d["id"])
        x["fields"] = {f["key"]: f for f in x["fields"]}
        full.append(x)
    names = {r["id"]: r["filename"] for r in store.rows(con, "SELECT id, filename FROM document WHERE project_id=?", pid)}
    vl = store.one(con, "SELECT * FROM document WHERE project_id=? AND kind='valvelist' AND status='done' ORDER BY id DESC",
                   pid)
    template = Path(vl["path"]).read_bytes() if vl else None
    link = (lambda ds, key: exports.deep_link(base, pname, {"ds_id": ds["id"], "key": key,
                                                         "page": (ds["fields"].get(key) or {}).get("page")})) if base else None
    data, report = tbe.build(template, full, names, pname, link=link)
    return data, report, vl


@router.get("/api/valve/projects/{pid}/valvelist.xlsx")
async def valvelist_xlsx(pid: int, request: Request):
    data, report, vl = await run_in_threadpool(_export_valvelist, pid, _base(request))
    con = store.connect()
    store.audit(con, pid, None, None, "export", None, "valvelist.xlsx", _user(request),
                json.dumps({k: len(v) for k, v in report.items()}))
    con.commit()
    base = Path(vl["filename"]).stem if vl else "Valve_List"
    fn = f"{base}_{store.now()[:10]}.xlsx"
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(fn)}",
                             "X-Report": quote(json.dumps({k: len(v) for k, v in report.items()}))})


@router.get("/api/valve/projects/{pid}/valvelist/preview")
async def valvelist_preview(pid: int):
    data, report, vl = await run_in_threadpool(_export_valvelist, pid)
    return {"report": report, "template": vl["filename"] if vl else None}


def _select(rows, types: str = "", dismissed: int = 0, tag: str = "", severity: str = ""):
    want = [t for t in types.split(",") if t] or issuesmod.CONTRACTOR_TYPES
    sev = [x for x in severity.split(",") if x]
    tags = {schema.norm_tag(t) for t in tag.split(",") if t}
    return [i for i in rows if i["type"] in want and (dismissed or i["status"] != "Dismissed")
            and (not tags or i["tag"] in tags) and (not sev or i["severity"] in sev)]


def _issue_xlsx(pid, base, by, types="", dismissed=0, tag="", severity=""):
    con = store.connect()
    pname = store.one(con, "SELECT name FROM project WHERE id=?", pid)["name"]
    rows = _select(project_issues(con, pid), types, dismissed, tag, severity)
    srcs = sorted({i["filename"] for i in rows})
    return exports.issues_xlsx(rows, base, pname, by, srcs), len(rows), pname


def _markup_entries(con, rows):
    by_ds = {}
    for i in rows:
        by_ds.setdefault(i["ds_id"], []).append(i)
    out = []
    for dsid, iss in by_ds.items():
        d = _ds_full(con, dsid, deep=False)
        doc = store.one(con, "SELECT path, filename FROM document WHERE id=?", d["document_id"])
        out.append({"path": doc["path"], "pages": d["pages"], "tag": d["tag_key"], "doc_no": d["doc_no"], "rev": d["rev"],
                    "filename": doc["filename"], "issues": iss})
    out.sort(key=lambda e: e["tag"])
    return out


def _project_pms(con, pid):
    pms, pdoc = _pms_for(con, pid)
    if not pms:
        return None, []
    latest = _latest(store.rows(con, "SELECT id, tag_key, rev FROM datasheet WHERE project_id=?", pid))
    out = []
    for d in sorted(latest.values(), key=lambda d: d["tag_key"]):
        x = _ds_full(con, d["id"], deep=False)
        F = {f["key"]: f for f in x["fields"]}
        for r in pmsmod.check(F, pms, x["area"]):
            f = F.get(r["key"]) or {}
            out.append(dict(r, ds_id=x["id"], tag=x["tag_key"], doc_no=x["doc_no"], rev=x["rev"], area=x["area"],
                            document_id=x["document_id"], ds_page=f.get("page") or x["pages"][0], ds_bbox=f.get("bbox")))
    return pdoc, out


@router.get("/api/valve/projects/{pid}/pms")
async def pms_rows(pid: int):
    con = store.connect()
    pdoc, rows = await run_in_threadpool(_project_pms, con, pid)
    return {"pms_doc": pdoc, "rows": rows}


@router.get("/api/valve/projects/{pid}/issues.xlsx")
async def issues_xlsx(pid: int, request: Request, types: str = "", dismissed: int = 0, tag: str = "", severity: str = ""):
    data, n, pname = await run_in_threadpool(_issue_xlsx, pid, _base(request), _user(request), types, dismissed, tag, severity)
    con = store.connect()
    store.audit(con, pid, None, None, "export", None, "issues.xlsx", _user(request), f"{n} issues")
    con.commit()
    fn = f"{pname.replace(' ', '_')}_Valve_Datasheet_Issue_List_{store.now()[:10]}.xlsx"
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(fn)}", "X-Count": str(n)})


@router.get("/api/valve/projects/{pid}/markup.pdf")
async def issues_markup(pid: int, request: Request, types: str = "", dismissed: int = 0, tag: str = "", severity: str = "",
                        summary: int = 1):
    """Marked-up datasheet pages (issues in colour, numbered, printable) + an Issue Summary page per datasheet."""
    con = store.connect()
    pname = store.one(con, "SELECT name FROM project WHERE id=?", pid)["name"]
    rows = _select(project_issues(con, pid), types, dismissed, tag, severity)
    entries = _markup_entries(con, rows)
    data = await run_in_threadpool(exports.markup_pdf, entries, pname, "Valve Datasheet Review - Mark-up", bool(summary))
    store.audit(con, pid, None, None, "markup-export", None, "markup.pdf", _user(request), f"{len(rows)} issues · {len(entries)} datasheets")
    con.commit()
    one = entries[0]["tag"] + "_" if len(entries) == 1 else ""
    fn = f"{pname.replace(' ', '_')}_{one}Datasheet_Markup_{store.now()[:10]}.pdf"
    return Response(data, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(fn)}"})


@router.get("/api/valve/projects/{pid}/exports")
def export_list(pid: int):
    d = store.root() / "exports" / str(pid)
    files = sorted(d.glob("*.*"), key=lambda p: p.stat().st_mtime, reverse=True) if d.exists() else []
    return {"files": [{"name": p.name, "size": p.stat().st_size, "at": dt.datetime.fromtimestamp(p.stat().st_mtime)
                       .isoformat(timespec="seconds"), "url": f"/api/valve/projects/{pid}/exports/{quote(p.name)}"}
                      for p in files[:60]]}


@router.get("/api/valve/projects/{pid}/exports/{name}")
def export_file(pid: int, name: str):
    p = store.root() / "exports" / str(pid) / Path(name).name
    if not p.exists():
        return _err("없는 파일", 404)
    return FileResponse(p, filename=p.name)


def _auto_export(jid, pid, base, by):
    """After an analysis: Valve List (reference format, cells linked to the PDF) + Issue List, kept on the server."""
    try:
        _job(jid, msg="Excel 만드는 중…")
        con = store.connect()
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        out = store.root() / "exports" / str(pid)
        out.mkdir(parents=True, exist_ok=True)
        files = []
        vl_data, report, vl = _export_valvelist(pid, base)
        vname = f"{stamp}_{Path(vl['filename']).stem if vl else 'Valve_List'}.xlsx"
        (out / vname).write_bytes(vl_data)
        files.append({"name": vname, "kind": "Valve List", "url": f"/api/valve/projects/{pid}/exports/{quote(vname)}"})
        idata, n, pname = _issue_xlsx(pid, base, by)
        iname = f"{stamp}_{pname.replace(' ', '_')}_Issue_List.xlsx"
        (out / iname).write_bytes(idata)
        files.append({"name": iname, "kind": f"Issue List ({n})", "url": f"/api/valve/projects/{pid}/exports/{quote(iname)}"})
        store.audit(con, pid, None, None, "auto-export", None, ", ".join(f["name"] for f in files), by)
        con.commit()
        _job(jid, exports=files)
    except Exception as e:                               # noqa: BLE001 — the analysis itself is done; say what failed
        _job(jid, warn=f"Excel 자동 생성 실패: {type(e).__name__}: {e}")


@router.get("/api/valve/projects/{pid}/audit")
def audit_list(pid: int):
    con = store.connect()
    return {"audit": store.rows(con, "SELECT a.*, d.tag, d.rev FROM audit a LEFT JOIN datasheet d ON d.id=a.datasheet_id"
                                     " WHERE a.project_id=? ORDER BY a.id DESC LIMIT 2000", pid)}


@router.get("/api/valve/projects/{pid}/extracted.csv")
def extracted_csv(pid: int):
    """Every extracted field of the latest revision per tag, with page and status — the audit table as data."""
    import csv
    con = store.connect()
    latest = _latest(store.rows(con, "SELECT id, tag_key, rev FROM datasheet WHERE project_id=?", pid))
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Tag", "Rev", "Doc No.", "Section", "Field", "Row", "Value (as read)", "Unit", "Edited Value", "Edited By",
                "Status", "Page", "File"])
    for d in latest.values():
        x = _ds_full(con, d["id"])
        for f in x["fields"]:
            w.writerow([x["tag"], x["rev"], x["doc_no"], f["section"], f["display"], f["row"], f["value"], f["unit"],
                        f["edited_value"] or "", f["edited_by"] or "", f["status"], f["page"], x["filename"]])
    return Response("﻿" + buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=extracted_fields.csv"})
