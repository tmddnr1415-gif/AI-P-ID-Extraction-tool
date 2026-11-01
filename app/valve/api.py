"""Valve Datasheet Review — /valve (screen) and /api/valve/* on the P&ID server (port 8000).

Same server, same rules as books · space · LOGIC: the dashboard opens /valve/?embed=1&user=<name>, the screen
sends that name back as X-Author, and every change is written under it (no separate login).

Batch upload runs in a background thread; the screen polls /api/valve/jobs/{id} for page progress.
Nothing here decides compliance: extraction is read from the PDF, comparisons are rule-based, and every
result carries the page and box it came from.
"""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
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
from app.valve import ruleperf, checks as chkmod, revisions as revmod, exports, extract, issues as issuesmod, expert as expmod, knowledge as kbmod, location as locmod, tagrules as tagmod, material, matreview as matmod, pms as pmsmod, process as procmod, requirements as reqmod, schema, store, tbe

router = APIRouter()
_JOBS: dict[str, dict] = {}
_JLOCK = threading.Lock()
_STATIC = {"valve.js": "application/javascript", "valve.css": "text/css"}
KINDS = ("datasheet", "valvelist", "process", "pms")


def _user(request: Request) -> str:
    raw = request.headers.get("x-author") or ""
    return re.sub(r"\s+", " ", unquote(raw)).strip()[:40] or "(이름 없음)"


def _json(obj) -> Response:
    """Pre-encoded JSON: skips FastAPI's jsonable_encoder walk (a 2,800-issue list took 200 ms there, 20 ms here)."""
    return Response(json.dumps(obj, ensure_ascii=False, default=str), media_type="application/json")


_BODY: dict[tuple, tuple] = {}               # (screen, pid, arg) -> (version, encoded body) — valve29 speed


def _wver(con, pid) -> tuple:
    """Everything a project screen can depend on: commits made by this server (store.WRITES) + the database's own
    newest rows, so a write by another process (a script on the same data folder) is also seen."""
    r = con.execute("SELECT (SELECT COALESCE(MAX(id),0) FROM audit WHERE project_id=?), (SELECT COUNT(*) || ':' || COALESCE(MAX(id),0) || ':' || "
                    "COALESCE(SUM(status='done'),0) FROM document WHERE project_id=?), (SELECT COUNT(*) FROM datasheet WHERE project_id=?)",
                    (pid, pid, pid)).fetchone()
    return (store.WRITES[0],) + tuple(r)


def _cached(name, pid, build, arg=None, request: Request | None = None) -> Response:
    """The same answer as build() — encoded and gzip-compressed ONCE, reused until the next write (summary 250 ms → 1 ms at
    990 DS).  The browser gets an ETag: an unchanged answer is a 304 with no body (a 3 MB list costs nothing to re-open)."""
    con = store.connect()
    ver = _wver(con, pid)
    hit = _BODY.get((name, pid, arg))
    if not (hit and hit[0] == ver):
        res = build(con)
        if not isinstance(res, Response) or res.status_code != 200:
            return res
        hit = (ver, gzip.compress(res.body, 5), f'W/"{hashlib.sha1(repr((name, arg, ver)).encode()).hexdigest()[:16]}"')
        if store.WRITES[0] == ver[0]:                        # nothing written while it was being computed
            _BODY[(name, pid, arg)] = hit
    return _gz_response(hit[1], hit[2], request)


def _gz_response(gz: bytes, etag: str, request: Request | None) -> Response:
    """A pre-compressed JSON body: 304 when the browser already holds it, gzip when it accepts it, plain otherwise."""
    h = {"ETag": etag, "Cache-Control": "no-cache", "Vary": "Accept-Encoding"}
    if request is not None:
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers=h)
        if "gzip" in request.headers.get("accept-encoding", ""):
            return Response(gz, media_type="application/json", headers=dict(h, **{"Content-Encoding": "gzip"}))
    return Response(gzip.decompress(gz), media_type="application/json", headers=h)


def _err(msg, code=400):
    return JSONResponse({"error": msg}, status_code=code)


# ── screen ──────────────────────────────────────────────────────────────────────

def _static(name: str) -> Path:
    return paths.resource("app", "static", "valve", name)


@router.get("/valve")
def valve_redirect(request: Request):
    qs = request.url.query
    return RedirectResponse("/valve/" + (f"?{qs}" if qs else ""), status_code=307)


_ASSET_H: dict[str, tuple] = {}


def _asset_hash(name: str) -> str:
    """Content hash of a static file (re-read when its mtime changes): the page links valve.js?v=<hash>, so the browser
    keeps it for a year and still gets a new one the moment a package changes it (valve29 lighter)."""
    p = _static(name)
    try:
        mt = p.stat().st_mtime_ns
    except OSError:
        return "0"
    hit = _ASSET_H.get(name)
    if not hit or hit[0] != mt:
        hit = (mt, hashlib.sha1(p.read_bytes()).hexdigest()[:12])
        _ASSET_H[name] = hit
    return hit[1]


@router.get("/valve/")
def valve_page():
    html = _static("index.html").read_text(encoding="utf-8")
    for name in _STATIC:
        html = html.replace(f'"{name}"', f'"{name}?v={_asset_hash(name)}"')
    return Response(html, media_type="text/html", headers={"Cache-Control": "no-store"})


@router.get("/valve/{name}")
def valve_file(name: str, v: str = ""):
    if name not in _STATIC:
        return _err("없는 파일", 404)
    cc = "public, max-age=31536000, immutable" if v and v == _asset_hash(name) else "no-cache"
    return FileResponse(_static(name), media_type=_STATIC[name], headers={"Cache-Control": cc})


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
def summary(pid: int, request: Request):
    return _cached("summary", pid, lambda con: _summary(pid), request=request)


def _summary(pid: int):
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
    has_process = any(d["kind"] == "process" and d["status"] == "done" and str(d["filename"]).lower().endswith(".pdf") for d in docs)
    irows = project_issues(con, pid) if latest else []
    ic = _issue_counts(irows)
    pv = _profile_ver(con, pid)
    loc_of = {d["id"]: ((_ds_full(con, d["id"], pv=pv) or {}).get("location") or {}) for d in latest.values()}
    ver = {"pass": 0, "fail": 0, "na": 0, "total": 0, "tags": 0, "na_reasons": {}}
    for d in latest.values():                                         # valve28: verification coverage of the project
        v = (_ds_full(con, d["id"], pv=pv) or {}).get("verification")
        if v:
            ver["tags"] += 1
            for k in ("pass", "fail", "na", "total"):
                ver[k] += v["summary"][k]
            for c in v["checks"]:
                if c["status"] == "n/a":
                    ver["na_reasons"][c["reason"]] = ver["na_reasons"].get(c["reason"], 0) + 1
    per_tag, still = {}, {}
    for i in irows:
        if i["status"] != "Dismissed" and i["severity"] in ("Major", "Minor"):
            per_tag[i["ds_id"]] = per_tag.get(i["ds_id"], 0) + 1
        if i.get("since") and i["status"] != "Dismissed":              # valve26: confirmed before, unchanged in the new revision
            still[i["ds_id"]] = still.get(i["ds_id"], 0) + 1
    activity = store.rows(con, "SELECT a.*, d.tag, d.rev FROM audit a LEFT JOIN datasheet d ON d.id=a.datasheet_id"
                               " WHERE a.project_id=? ORDER BY a.id DESC LIMIT 30", pid)
    return _json({
        "project": p,
        "kpi": {"tags": len(latest), "datasheets": len(dss),
                "new_tags": len([k for k in latest if vl and k not in vl_tags]),
                "revision_changes": sum(1 for v in revs.values() if len(v) > 1),
                "process_mismatch": (ic.get("Process Mismatch", 0) if has_process else None),
                "pms_noncompliant": (ic.get("PMS Non-Compliance", 0) if has_pms else None),
                "data_errors": ic.get("Data Error", 0), "data_missing": ic.get("Data Missing", 0),
                "open_items": ic.get("Open Item", 0), "pms_review": ic.get("PMS Review", 0) if has_pms else None,
                "pending": len(latest) - done, "completed": done, "not_addressed": sum(still.values()), "verification": ver,
                "review_required": sum(issues.get(d["id"], 0) for d in latest.values())},
        "has_valvelist": bool(vl),
        "has_pms": has_pms,
        "has_process": has_process,
        "by_area": _by_area(irows, latest, loc_of),
        "tags": [dict(d, area=loc_of.get(d["id"], {}).get("area", ""), unit=loc_of.get(d["id"], {}).get("unit", ""),
                      issues=issues.get(d["id"], 0), problems=per_tag.get(d["id"], 0), still=still.get(d["id"], 0), revs=sorted(revs[k], key=store.rev_key),
                      in_valvelist=(k in vl_tags) if vl else None) for k, d in sorted(latest.items())],
        "documents": docs,
        "activity": activity,
    })


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
                n_bad = sum(1 for o in res["other_pages"] if o.get("kind") == "damaged")
                if n_bad:
                    _job(jid, warn=f"{name}: 손상된 파일 — 복구해 읽었지만 {n_bad}쪽은 글자를 찾지 못했습니다. 원본 파일을 다시 받아 올려 주세요")
                new_ids = []
                with store._LOCK:
                    for ds in dss:
                        ds["form"] = "102" if any(r.get("row", 0) > 61 for r in ds["fields"].values()) else "on/off"
                        dup = store.one(con, "SELECT id, document_id FROM datasheet WHERE project_id=? AND tag_key=? AND rev=?"
                                             " AND document_id IN (SELECT id FROM document WHERE sha256=(SELECT sha256 FROM"
                                             " document WHERE id=?))", pid, ds["tag_key"], ds["rev"], doc_id)
                        if dup and dup["document_id"] == doc_id:     # re-read of this file: refresh, keep the review
                            r = store.refresh_datasheet(con, dup["id"], ds)
                            if r["changed"] or r["removed"]:
                                store.audit(con, pid, dup["id"], None, "re-read", None, None, by,
                                            f"{r['changed']} fields changed, {r['removed']} removed")
                            continue
                        if dup:
                            continue
                        new_ids.append(store.insert_datasheet(con, pid, doc_id, ds))
                    info = {"datasheets": len(dss), "tags": sorted({d["tag"] for d in dss}),
                            "docs": {k: {"title": v.get("title"), "rev": v.get("rev"),
                                         "general_notes": v.get("general_notes", {})} for k, v in res["docs"].items()},
                            "scanned_pages": n_scan}
                    con.execute("UPDATE document SET status='done', info=? WHERE id=?", (store.J(info), doc_id))
                    store.audit(con, pid, None, None, "upload", None, name, by, f"{len(dss)} datasheets")
                    con.commit()
                if n_scan:
                    _job(jid, warn=f"{name}: 글자층이 없는 쪽 {n_scan}장 (스캔본) — 이 판에서는 읽지 못했습니다")
                _carry_over(con, pid, new_ids, by, jid)        # valve26: Rev B inherits what Rev A's review decided
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
            else:                                        # process data tables -> {data}/valve/process/<doc>.json (process.read_process_data)
                if path.suffix.lower() != ".pdf":
                    raise extract.PdfError("Process Data 는 PDF 만 읽습니다 — Excel 은 보관만 됩니다 (PDF 로 올려 주세요)")
                parsed = procmod.read_process_data(str(path))
                store.write_json(store.root() / "process" / f"{doc_id}.json", parsed)
                _PROC_CACHE.pop(doc_id, None)
                info = {"doc_no": parsed["doc_no"], "tags": parsed["n_tags"], "tables": len(parsed["pages"]),
                        "note": f"Process Data 표 {len(parsed['pages'])}장 · Tag {parsed['n_tags']}개 읽음 — Process Data Verification 에 바로 쓰입니다"}
                con.execute("UPDATE document SET status='done', info=? WHERE id=?", (store.J(info), doc_id))
                store.audit(con, pid, None, None, "upload", None, name, by, "process")
                con.commit()
        except Exception as e:                           # noqa: BLE001 — one bad file must not stop the batch
            msg = str(e) if isinstance(e, extract.PdfError) else f"{type(e).__name__}: {e}"
            con.execute("UPDATE document SET status='error', error=? WHERE id=?", (msg, doc_id))
            con.commit()
            with _JLOCK:
                _JOBS[jid]["errors"].append({"file": name, "error": str(e)[:300], "trace": traceback.format_exc()[-800:]})
        done += max(1, pages)
        _job(jid, done=done)
    if any(it[1] == "datasheet" for it in items) and _JOBS[jid].get("base") is not None:
        _auto_export(jid, pid, _JOBS[jid]["base"], by)
    _job(jid, status="done", msg="끝", total=total, done=total)
    warm(pid)


_WARMING: set = set()


def warm(pid: int):
    """Compute every datasheet's review once, in a background thread, so the first screen never waits (valve20)."""
    if pid in _WARMING:
        return

    def run():
        _WARMING.add(pid)
        try:
            con = store.connect()
            project_issues(con, pid)
            _project_pms(con, pid)
            _project_process(con, pid)
            _cached("summary", pid, lambda c: _summary(pid))             # valve29: the first click of every screen
            _cached("grid", pid, lambda c: _json(_grid(c, pid)))         # after a restart is ready too
            _cached("requirements", pid, lambda c: _json(_req_rows(c, pid)))
            _cached("rules", pid, lambda c: _rules_performance(c, pid), arg=dt.date.today().isoformat())
            _cached("tagging", pid, lambda c: _tagging(c, pid))
            _cached("pms", pid, lambda c: _pms_body(c, pid))
            _cached("process", pid, lambda c: _process_body(c, pid))
            issues_json(pid, 1)
        except Exception as e:                           # noqa: BLE001  (warming must never break the server)
            print(f"[valve] warm-up of project {pid} failed: {e}")
        finally:
            _WARMING.discard(pid)
            _trim()
    threading.Thread(target=run, daemon=True, name=f"valve-warm-{pid})").start()


@router.on_event("startup")
async def _startup_warm():
    threading.Thread(target=warm_all, daemon=True, name="valve-warm-all").start()


def _rules_fingerprint() -> str:
    """valve29: the review code itself is part of the cache key — new or changed rules recompute every cached review even
    when VERSION is not bumped (a stale cache would hide a new rule's findings)."""
    import hashlib
    import importlib
    h = hashlib.sha1()
    for m in ("expert", "matreview", "issues", "checks", "knowledge", "requirements", "process", "pms", "material", "revisions"):
        try:
            h.update(Path(importlib.import_module(f"app.valve.{m}").__file__).read_bytes())
        except Exception:                                   # noqa: BLE001  (a frozen build without sources: VERSION alone)
            h.update(m.encode())
    return h.hexdigest()[:10]


_RULES_FP = _rules_fingerprint()
VERSION = "valve29"                       # shown in Settings › 정보 and the footer; bump with every package


@router.get("/api/valve/version")
def version():
    return {"version": VERSION, "data_dir": str(store.root())}


@router.get("/api/valve/health")
def health():
    """Support check: database, data folder, cache, disk, versions — one call for the help desk."""
    import shutil
    import sys
    out = {"version": VERSION, "python": sys.version.split()[0], "ok": True, "checks": {}}
    try:
        con = store.connect()
        n = store.one(con, "SELECT COUNT(*) n FROM datasheet")["n"]
        out["checks"]["db"] = {"ok": True, "datasheets": n, "path": str(store.root() / "valve.db")}
    except Exception as e:                                   # noqa: BLE001
        out["ok"] = False
        out["checks"]["db"] = {"ok": False, "error": str(e)[:200]}
    for name in ("files", "cache", "backups", "exports"):
        p = store.root() / name
        try:
            p.mkdir(parents=True, exist_ok=True)
            t = p / ".write_test"
            t.write_text("ok")
            t.unlink()
            out["checks"][name] = {"ok": True}
        except Exception as e:                               # noqa: BLE001
            out["ok"] = False
            out["checks"][name] = {"ok": False, "error": str(e)[:200]}
    try:
        u = shutil.disk_usage(str(store.root()))
        out["checks"]["disk"] = {"ok": u.free > 500 * 1024 * 1024, "free_mb": u.free // 1048576}
        out["ok"] = out["ok"] and out["checks"]["disk"]["ok"]
    except Exception as e:                                   # noqa: BLE001
        out["checks"]["disk"] = {"ok": False, "error": str(e)[:200]}
    b = sorted((store.root() / "backups").glob("valve.db.*.bak"))
    out["checks"]["last_backup"] = b[-1].name if b else None
    out["checks"]["review_cache"] = len(list((store.root() / "cache" / "review").glob("*.json"))) if (store.root() / "cache" / "review").exists() else 0
    out["checks"]["warming"] = sorted(_WARMING)
    return out


def warm_all():
    try:
        try:
            b = store.backup()
            if b:
                print(f"[valve] db backup: {b}")
        except Exception as e:                           # noqa: BLE001
            print(f"[valve] db backup skipped: {e}")
        con = store.connect()
        for p in store.rows(con, "SELECT id FROM project ORDER BY id DESC LIMIT 5"):
            warm(p["id"])
    except Exception as e:                               # noqa: BLE001
        print(f"[valve] warm-up skipped: {e}")


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
                    locked = d.needs_pass and not d.authenticate("")
                    pages = d.page_count
            except Exception:                            # noqa: BLE001
                skipped.append(f"{name} — PDF 를 열 수 없습니다 (손상된 파일)")
                continue
            if locked:
                skipped.append(f"{name} — 암호가 걸린 PDF 입니다. 암호를 풀어 저장한 뒤 다시 올려 주세요")
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


_PROC_CACHE: dict[int, dict] = {}


def _doc_ref(con, pid, kind, doc) -> dict:
    """valve29: the reference document a check used — the newest upload of its kind — and the earlier uploads, so the
    engineer sees WHICH Process Data / PMS a finding was checked against when a revised one has been loaded."""
    vs = store.rows(con, "SELECT id, filename, uploaded_at FROM document WHERE project_id=? AND kind=? AND status='done' ORDER BY id DESC", pid, kind)
    me = next((v for v in vs if v["id"] == doc["id"]), {"id": doc["id"], "filename": doc["filename"], "uploaded_at": ""})
    return {"id": doc["id"], "filename": doc["filename"], "uploaded_at": me.get("uploaded_at") or "", "kind": kind,
            "earlier": [v for v in vs if v["id"] != doc["id"]][:5]}


def _process_for(con, pid):
    """(parsed Process Data, document row) of the project's newest Process Data PDF, or (None, None)."""
    doc = store.one(con, "SELECT id, filename, path FROM document WHERE project_id=? AND kind='process' AND status='done'"
                         " ORDER BY id DESC", pid)
    if not doc or not str(doc["path"]).lower().endswith(".pdf"):
        return None, None
    if doc["id"] not in _PROC_CACHE:
        p = store.root() / "process" / f"{doc['id']}.json"
        if not p.exists():                               # uploaded before the Phase 3 engine (valve01~06): read it now
            if not Path(doc["path"]).exists():
                return None, None
            store.write_json(p, procmod.read_process_data(doc["path"]))
        _PROC_CACHE[doc["id"]] = json.loads(p.read_text(encoding="utf-8"))
    return _PROC_CACHE[doc["id"]], _doc_ref(con, pid, "process", doc)


def _pms_for(con, pid):
    """(parsed PMS, document row) of the project's newest PMS upload, or (None, None)."""
    doc = store.one(con, "SELECT id, filename, path FROM document WHERE project_id=? AND kind='pms' AND status='done'"
                         " ORDER BY id DESC", pid)
    if not doc:
        return None, None
    if doc["id"] not in _PMS_CACHE:
        p = store.root() / "pms" / f"{doc['id']}.json"
        if not p.exists():                               # uploaded before PMS reading existed (valve01): read it now
            if not Path(doc["path"]).exists():
                return None, None
            store.write_json(p, pmsmod.read_pms(doc["path"]))
        P = json.loads(p.read_text(encoding="utf-8"))
        if P.get("v", 1) < pmsmod.READER_VERSION and Path(doc["path"]).exists():   # read before valve10: no P-T / notes yet
            P = pmsmod.read_pms(doc["path"])
            store.write_json(p, P)
        _PMS_CACHE[doc["id"]] = P
    return _PMS_CACHE[doc["id"]], _doc_ref(con, pid, "pms", doc)


_PEER_CACHE: dict[int, tuple] = {}
_DEEP_CACHE: dict[int, tuple] = {}          # datasheet id -> (version, computed datasheet)   (valve20: no recompute per request)


def _profile_ver(con, pid) -> tuple:
    """Version of everything project-wide that a datasheet's review depends on: the set of datasheets, the documents
    (PMS / Process Data uploads) and the VALUE edits (peer / tag learning).  Issue states, comments and review
    statuses are per datasheet and do not move this."""
    return (tuple(store.one(con, "SELECT COUNT(*) n, MAX(id) m FROM datasheet WHERE project_id=?", pid).values())
            + tuple(store.one(con, "SELECT COUNT(*) n, MAX(id) m FROM document WHERE project_id=? AND status='done'", pid).values())
            + (store.one(con, "SELECT MAX(id) m FROM audit WHERE project_id=? AND action IN ('edit','revert','re-read','upload')", pid)["m"],))


def _peers_for(con, pid):
    """What the project's datasheets say, per piping class (expert.build_peers) — latest revision of each tag.
    Rebuilt when a datasheet is added or a value is corrected (the key follows datasheet / audit ids)."""
    k = _profile_ver(con, pid)
    if pid in _PEER_CACHE and _PEER_CACHE[pid][0] == k:
        return _PEER_CACHE[pid][1]
    latest = _latest(store.rows(con, "SELECT id, tag_key, rev FROM datasheet WHERE project_id=?", pid))
    ids = {d["id"]: d["tag_key"] for d in latest.values()}
    vals: dict[int, dict] = {i: {} for i in ids}
    for i in ids:
        for f in store.rows(con, "SELECT key, value, edited_value FROM field WHERE datasheet_id=?", i):
            vals[i][f["key"]] = f["edited_value"] if f["edited_value"] is not None else (f["value"] or "")
    prof = expmod.build_peers([{"tag": ids[i], "fields": vals[i]} for i in ids])
    _PEER_CACHE[pid] = (k, prof)
    return prof


_TAG_CACHE: dict[int, tuple] = {}


def _tag_item(d) -> dict:
    """What the tag rules need from one datasheet (tagrules.learn / check)."""
    F = {f["key"]: f for f in d["fields"]} if isinstance(d["fields"], list) else d["fields"]
    v = lambda k: store.field_value(F[k]) if k in F else ""          # noqa: E731
    loc = d.get("location") or {}
    return {"tag_raw": v("tag") or d.get("tag") or d["tag_key"], "tag_key": d["tag_key"], "area": loc.get("area", ""), "site": loc.get("site", ""),
            "unit": loc.get("unit", ""), "system": loc.get("system", ""), "pid_no": v("pid_no"), "doc_no": d["doc_no"],
            "valve_type": d.get("valve_type", ""), "fail": v("fail_position"), "page": (F.get("tag") or {}).get("page"), "bbox": (F.get("tag") or {}).get("bbox")}


def _tags_for(con, pid):
    """Tag numbering learned from every datasheet of the project (all revisions; tagrules.learn) — cached like the peers."""
    k = _profile_ver(con, pid)
    if pid in _TAG_CACHE and _TAG_CACHE[pid][0] == k:
        return _TAG_CACHE[pid][1]
    items = []
    for r in store.rows(con, "SELECT id FROM datasheet WHERE project_id=? ORDER BY id DESC", pid):   # newest revision first
        items.append(_tag_item(_ds_full(con, r["id"], deep=False)))
    prof = tagmod.learn(items)
    _TAG_CACHE[pid] = (k, prof)
    return prof


def _ds_full(con, dsid, deep=True, pv=None):
    """The datasheet with everything the screens need.  deep=True adds the review (PMS · Process · requirements ·
    expert · issues) from the per-datasheet cache; pv = project version from _profile_ver, computed once per request."""
    if deep:
        h = store.one(con, "SELECT project_id, review_status FROM datasheet WHERE id=?", dsid)
        if not h:
            return None
        pv = pv or _profile_ver(con, h["project_id"])
        ver = (store.one(con, "SELECT MAX(id) m FROM audit WHERE datasheet_id=?", dsid)["m"], h["review_status"]) + pv \
            + (VERSION, _RULES_FP)                           # valve25: a package with new rule wording recomputes the disk cache
        hit = _DEEP_CACHE.get(dsid)
        if hit and hit[0] == ver:
            return _with_history(con, dict(hit[1]))          # top-level copy: callers may swap keys, never edit nested lists
        disk = _deep_disk(dsid)                              # computed before a restart: read instead of recompute (valve20)
        if disk and tuple(disk.get("_ver") or ()) == tuple(ver):
            d = _slim_deep(disk["d"])
            _DEEP_CACHE[dsid] = (ver, d)
            return _with_history(con, dict(d))
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
    docs_info = (store.unJ(doc["info"], {}) or {}).get("docs", {}) if doc else {}
    gn = docs_info.get(d["doc_no"], {})
    d["general_notes"] = _intern_gn(d["document_id"], d["doc_no"], gn.get("general_notes", {}))
    d["revisions"] = store.rows(con, "SELECT id, rev, doc_no, document_id, created_at FROM datasheet WHERE project_id=?"
                                     " AND tag_key=? ORDER BY id", d["project_id"], d["tag_key"])
    d["revisions"].sort(key=lambda r: (store.rev_key(r["rev"]), r["id"]))
    d["comments"] = store.rows(con, "SELECT * FROM comment WHERE datasheet_id=? AND deleted=0 ORDER BY id", dsid)
    for c in d["comments"]:
        c["bbox"], c["points"], c["style"] = store.unJ(c["bbox"]), store.unJ(c.get("points")), store.unJ(c.get("style"))
    d["history"] = store.rows(con, "SELECT * FROM audit WHERE datasheet_id=? ORDER BY id DESC", dsid)
    d["doc_title"] = (gn or {}).get("title", "")
    d["area"] = pmsmod.area_of_title(d["doc_title"])
    F0 = {f["key"]: f for f in fs}
    title = locmod.title_for(d["doc_no"], docs_info)
    if not title:                                        # e.g. a one-sheet revision without cover: the same Doc. No. in another upload
        for o in store.rows(con, "SELECT info FROM document WHERE project_id=? AND id<>? AND info IS NOT NULL", d["project_id"], d["document_id"]):
            title = locmod.title_for(d["doc_no"], (store.unJ(o["info"], {}) or {}).get("docs", {}))
            if title:
                break
    d["location"] = locmod.locate(d["doc_no"], title, store.field_value(F0["pid_no"]) if "pid_no" in F0 else "",
                                  d["tag_key"], " ".join(n.get("text", "") for n in d["notes"]))
    if d.get("process_ref") is None:                     # not stored: 'For Process data refer to …' read from the notes
        d["process_ref"] = extract.process_reference(d.get("notes"), d.get("general_notes"))
    if not deep:
        return d
    d = _ds_deep(con, d, dsid)
    slim = _slim_deep({k: v for k, v in d.items() if k != "history"})    # the audit trail is cheap to re-read and big to keep (valve22)
    _DEEP_CACHE[dsid] = (ver, slim)
    try:
        store.write_json(store.root() / "cache" / "review" / f"{dsid}.json", {"_ver": list(ver), "d": slim})
    except Exception:                                        # noqa: BLE001  (disk cache is an optimisation only)
        pass
    if len(_DEEP_CACHE) > 2500:                              # bound memory on very large projects (disk cache keeps the rest)
        for k in list(_DEEP_CACHE)[:500]:
            _DEEP_CACHE.pop(k, None)
    return dict(d)


def _trim():
    """Give freed heap back to the OS after a big recomputation (glibc keeps it otherwise: 990 DS −44 MB).  No-op where
    there is no glibc (Windows)."""
    import gc
    gc.collect()
    try:
        import ctypes
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:                                       # noqa: BLE001
        pass


_GN_INTERN: dict[tuple, dict] = {}


def _intern_gn(document_id, doc_no, gn: dict) -> dict:
    """valve29 (lighter): the General Notes of a document are the same for all its datasheets — keep ONE dict object per
    document instead of 164 (990 DS: ~40 MB less)."""
    k = (document_id, doc_no)
    hit = _GN_INTERN.get(k)
    if hit is not None and hit == gn:
        return hit
    _GN_INTERN[k] = gn
    return gn


def _slim_deep(d: dict) -> dict:
    """What the review cache keeps per datasheet: the knowledge text behind a finding is looked up from knowledge.KB when
    the datasheet is served (`_fat`) instead of being stored 17,000 times; General Notes are shared per document."""
    for m in d.get("material_review") or []:
        m.pop("kb_text", None)
        m.pop("kb_title", None)
    if d.get("general_notes") is not None:
        d["general_notes"] = _intern_gn(d.get("document_id"), d.get("doc_no"), d["general_notes"])
    return d


def _fat(d: dict) -> dict:
    """The served datasheet: knowledge title / text back on every Expert finding (the screen shows them)."""
    if d and d.get("material_review"):
        d["material_review"] = [dict(m, kb_title=k["title"], kb_text=k["text"]) if (k := kbmod.KB.get(m.get("kb"))) else m
                                for m in d["material_review"]]
    return d


def _with_history(con, d):
    if "history" not in d:
        d["history"] = store.rows(con, "SELECT * FROM audit WHERE datasheet_id=? ORDER BY id DESC", d["id"])
    return d


def _deep_disk(dsid: int):
    p = store.root() / "cache" / "review" / f"{dsid}.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    except Exception:                                        # noqa: BLE001
        return None


def _prev_rev_of(con, d):
    """The datasheet row of the previous revision of the same tag (by EPC revision order), or None."""
    rv = sorted(store.rows(con, "SELECT id, rev FROM datasheet WHERE project_id=? AND tag_key=?", d["project_id"], d["tag_key"]),
                key=lambda r: (store.rev_key(r["rev"]), r["id"]))
    i = next((n for n, r in enumerate(rv) if r["id"] == d["id"]), 0)
    return rv[i - 1] if i > 0 else None


def _carry_over(con, pid, new_ids, by, jid=None):
    """valve26: for every newly inserted datasheet that has an earlier revision in the project, carry the review
    (Dismissed · Confirmed states on unchanged fields, field comments) and write an audit line with the counts."""
    n_done = 0
    for dsid in new_ids:
        try:
            d = _ds_full(con, dsid, deep=False)
            prev = _prev_rev_of(con, d)
            if not prev:
                continue
            pfull = _ds_full(con, prev["id"], deep=False)
            cmp_rows = compare(pfull, d)
            new = _ds_full(con, dsid)                            # reviewed by the rules (also warms the cache)
            pstates = {r["ikey"]: r for r in store.rows(con, "SELECT * FROM issue_state WHERE datasheet_id=?", prev["id"])}
            carried = revmod.carry_states(pstates, cmp_rows, {i["ikey"] for i in new["issues"]}, prev["rev"])
            pcm = store.rows(con, "SELECT * FROM comment WHERE datasheet_id=? AND deleted=0", prev["id"])
            cms = revmod.carry_comments(pcm, cmp_rows, {f["key"]: f for f in d["fields"]})
            with store._LOCK:
                for c in carried:
                    con.execute("INSERT OR REPLACE INTO issue_state(datasheet_id, ikey, status, note, by, at, since, decision, reason_cat,"
                                " conclusion, modified_text, modified_severity, rule_ver, modified_expected) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                (dsid, c["ikey"], c["status"], c["note"], by, store.now(), c["since"], c.get("decision") or c["status"],
                                 c.get("reason_cat") or "", c.get("conclusion") or "", c.get("modified_text") or "",
                                 c.get("modified_severity") or "", c.get("rule_ver") or "", c.get("modified_expected") or ""))
                for c in cms:
                    con.execute("INSERT INTO comment(datasheet_id, field_key, text, by, at, page, bbox, category, kind, origin)"
                                " VALUES (?,?,?,?,?,?,?,?,?,?)", (dsid, c["field_key"], c["text"], c["by"], store.now(), c["page"],
                                                                 store.J(c["bbox"]) if c["bbox"] else None, c["category"], c["kind"], f"Rev {prev['rev']}"))
                store.audit(con, pid, dsid, None, "carry", prev["rev"], d["rev"], by,
                            f"{sum(1 for c in carried if c['status'] == 'Dismissed')} dismissed · "
                            f"{sum(1 for c in carried if c['status'] == 'Confirmed')} confirmed (not addressed) · {len(cms)} comments carried")
                con.commit()
            _DEEP_CACHE.pop(dsid, None)                         # states changed: the next read recomputes
            n_done += 1
        except Exception as e:                                  # noqa: BLE001 — a carry failure must not fail the upload
            store.audit(con, pid, dsid, None, "carry-error", None, None, by, str(e)[:300])
            con.commit()
    if n_done and jid:
        _job(jid, msg=f"이전 Revision 의 검토를 이어받음: {n_done} Tag")


def _ds_deep(con, d, dsid):
    fs = d["fields"]
    pms, pdoc = _pms_for(con, d["project_id"])
    F = {f["key"]: f for f in fs}
    d["pms"] = pmsmod.check(F, pms, d["area"], d["notes"]) if pms else None
    d["pms_doc"] = pdoc
    d["requirements"] = reqmod.find(d, d["general_notes"])
    proc, procdoc = _process_for(con, d["project_id"])
    d["process"] = procmod.check(d, proc) if proc else None
    d["process_doc"] = procdoc
    cls = pmsmod.find_class(pms, schema.effective(F.get("piping_class")), schema.effective(F.get("line_no")), d["area"])[0] if pms else None
    d["material_review"] = matmod.review(d, d["general_notes"], cls, d["process"],
                                         ((proc or {}).get("by_tag") or {}).get(d["tag_key"]), d["requirements"])
    d["material_review"] += expmod.review(d, d["general_notes"], cls, d["process"], ((proc or {}).get("by_tag") or {}).get(d["tag_key"]),
                                          d["requirements"], _peers_for(con, d["project_id"]))
    d["material_review"] += tagmod.check(_tag_item(d), _tags_for(con, d["project_id"]))
    prev = None
    i = next((n for n, r in enumerate(d["revisions"]) if r["id"] == d["id"]), 0)
    if i > 0:
        prev = compare(_ds_full(con, d["revisions"][i - 1]["id"], deep=False), d)
    states = {r["ikey"]: r for r in store.rows(con, "SELECT * FROM issue_state WHERE datasheet_id=?", dsid)}
    d["issues"] = issuesmod.compute(d, d["general_notes"], pms, d["area"], prev, states, pms_rows=d["pms"], process_rows=d["process"],
                                   material_rows=d["material_review"])
    d["rev_review"] = None
    if i > 0:                                                   # valve26: what this revision resolved / left open / added
        pid_ = d["revisions"][i - 1]["id"]
        pfull = _ds_full(con, pid_, deep=True)
        pstates = {r["ikey"]: r for r in store.rows(con, "SELECT * FROM issue_state WHERE datasheet_id=?", pid_)}
        d["rev_review"] = revmod.rev_review((pfull or {}).get("issues") or [], d["issues"], pstates, prev, d["revisions"][i - 1]["rev"])
        still = set(d["rev_review"]["still"])
        for it in d["issues"]:
            if it["ikey"] in still:
                it["since"] = d["rev_review"]["prev_rev"]
                it["severity"] = "Major"
                it["description"] = f"Not addressed since Rev {it['since']}: {it['description']}"
    # valve28: the engine's own report — what was checked, what failed, what could not be judged and why
    peers = _peers_for(con, d["project_id"])
    pcls = schema.effective(F.get("piping_class")) or ""
    prof = _tags_for(con, d["project_id"])
    grp = next((g for g in prof["groups"] if (g["area"], g["site"], g["unit"]) == ((d.get("location") or {}).get("area") or "", (d.get("location") or {}).get("site") or "",
                                                                                   (d.get("location") or {}).get("unit") or "")), None)
    T = matmod.proc_value(F, d["process"], "design_temp")
    d["verification"] = chkmod.report(d["issues"], {
        "has_pms": pms is not None, "pms_class": bool(cls), "piping_class": pcls,
        "has_process": proc is not None, "pd_row": bool(((proc or {}).get("by_tag") or {}).get(d["tag_key"])),
        "design_temp": T["v"] if T else None, "has_prev": i > 0,
        "has_peers": any(k[1] == pcls and sum(v.values()) > 1 for k, v in (peers.get("groups") or {}).items()) if pcls else False,
        "has_tagrules": bool(grp and grp.get("learned_from", 0) >= tagmod.MIN_N)})
    return d


@router.get("/api/valve/projects/{pid}/tagging")
async def tagging(pid: int, request: Request):
    """Tag numbering learned per Area / Site / Unit from the project's datasheets."""
    return await run_in_threadpool(_cached, "tagging", pid, lambda con: _tagging(con, pid), None, request)


def _tagging(con, pid):
    prof = _tags_for(con, pid)
    return _json({"groups": prof["groups"], "duplicates": {k: v for k, v in prof["docs_by_tag"].items() if len([x for x in v if x]) > 1}})


@router.get("/api/valve/knowledge")
def knowledge_base():
    """The ball valve engineering knowledge the review rules rest on (knowledge.KB)."""
    return [{"key": k, **e} for k, e in kbmod.KB.items()]


@router.get("/api/valve/datasheets/{dsid}")
def datasheet(dsid: int):
    d = _ds_full(store.connect(), dsid)
    return _json(_fat(d)) if d else _err("없는 데이터시트", 404)


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


MARK_KINDS = {"rect", "cloud", "ellipse", "highlight", "line", "arrow", "pen", "text", "note",
              "underline", "strike", "squiggle", "stamp",                      # valve23: text mark-ups + stamps
              "typewriter", "callout", "polyline", "polygon"}                  # valve24: annotator tool set
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _style(v) -> dict | None:
    """Mark-up style {color '#rrggbb', width 0.5–8, opacity 0.05–1, size 6–48, stamp ≤ 40 chars} — only valid keys kept."""
    if v is None:
        return None
    if not isinstance(v, dict):
        raise ValueError
    out = {}
    if v.get("color") and _HEX.match(str(v["color"])):
        out["color"] = str(v["color"]).lower()
    for k, lo, hi in (("width", 0.5, 8), ("opacity", 0.05, 1), ("size", 6, 48)):
        if v.get(k) is not None:
            out[k] = min(hi, max(lo, float(v[k])))
    if v.get("stamp"):
        out["stamp"] = str(v["stamp"]).strip()[:40]
    return out or None
MARK_CATS = {"comment", "error", "missing", "question"}


def _num_list(v, n=None):
    if not isinstance(v, list) or (n is not None and len(v) != n):
        raise ValueError
    out = [round(float(x), 1) for x in v]
    if any(abs(x) > 20000 for x in out):
        raise ValueError
    return out


def _markup(body: dict, old: dict | None = None) -> dict:
    """Geometry of a mark-up from a request: {page, bbox, kind, points, category}.  Raises ValueError on bad input.
    Only the keys present in the body are returned (PUT changes just those)."""
    out = {}
    if "page" in body:
        out["page"] = None if body["page"] is None else int(body["page"])
    if "bbox" in body:
        out["bbox"] = None if body["bbox"] is None else _num_list(body["bbox"], 4)
        if out["bbox"]:
            x0, y0, x1, y1 = out["bbox"]
            out["bbox"] = [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]
    if "kind" in body:
        if body["kind"] not in MARK_KINDS:
            raise ValueError
        out["kind"] = body["kind"]
    if "category" in body:
        if body["category"] not in MARK_CATS:
            raise ValueError
        out["category"] = body["category"]
    if "style" in body:
        out["style"] = _style(body["style"])
    if "points" in body:
        pts = body["points"]
        if pts is not None:                                  # line/arrow: [[x,y],[x,y]] · pen: [[[x,y],…], …] strokes
            kind = out.get("kind") or (old or {}).get("kind")
            strokes = pts if kind == "pen" else [pts]
            if not isinstance(strokes, list) or not strokes or len(strokes) > 200:
                raise ValueError
            clean = [[_num_list(p, 2) for p in st] for st in strokes]
            if any(len(st) < 2 for st in clean) or sum(len(st) for st in clean) > 5000:
                raise ValueError
            pts = clean if kind == "pen" else clean[0]
        out["points"] = pts
    return out


@router.post("/api/valve/datasheets/{dsid}/comments")
async def ds_comment(dsid: int, request: Request):
    """A review comment — plain text, or a mark-up drawn on the PDF (page + bbox + kind [+ points])."""
    body = await request.json()
    text = str(body.get("text", "")).strip()[:4000]
    try:
        g = _markup(body)
    except (ValueError, TypeError):
        return _err("주석 모양(bbox/points/kind/category) 형식이 잘못됐습니다")
    if not text and not g.get("bbox"):
        return _err("내용이 비었습니다")
    con = store.connect()
    d = store.one(con, "SELECT project_id FROM datasheet WHERE id=?", dsid)
    if not d:
        return _err("없는 데이터시트", 404)
    by = _user(request)
    with store._LOCK:
        cur = con.execute("INSERT INTO comment(datasheet_id, field_key, text, by, at, page, bbox, category, kind, points, style)"
                          " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                          (dsid, body.get("field_key"), text, by, store.now(), g.get("page"), store.J(g.get("bbox")),
                           g.get("category") or "comment", g.get("kind") or ("rect" if g.get("bbox") else None),
                           store.J(g.get("points")), store.J(g.get("style")) if g.get("style") else None))
        store.audit(con, d["project_id"], dsid, body.get("field_key"), "comment", None,
                    text or f"[{g.get('kind') or 'rect'}] p.{g.get('page')}", by)
        con.commit()
    out = _ds_full(con, dsid)
    out["new_comment_id"] = cur.lastrowid
    return out


@router.put("/api/valve/comments/{cid}")
async def comment_edit(cid: int, request: Request):
    """{delete: true} · {restore: true} (undo of a delete) · {text?, bbox?, points?, page?, kind?, category?}."""
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
        elif body.get("restore"):
            con.execute("UPDATE comment SET deleted=0 WHERE id=?", (cid,))
            store.audit(con, c["project_id"], c["datasheet_id"], c["field_key"], "comment-restore", None, c["text"], by)
        else:
            try:
                g = _markup(body, c)
            except (ValueError, TypeError):
                return _err("주석 모양 형식이 잘못됐습니다")
            sets, vals = [], []
            if "text" in body:
                text = str(body.get("text", "")).strip()[:4000]
                if not text and not (g.get("bbox") or c["bbox"]):
                    return _err("내용이 비었습니다")
                sets.append("text=?"), vals.append(text)
            for k in ("page", "kind", "category"):
                if k in g:
                    sets.append(f"{k}=?"), vals.append(g[k])
            for k in ("bbox", "points", "style"):
                if k in g:
                    sets.append(f"{k}=?"), vals.append(store.J(g[k]) if g[k] is not None else None)
            if not sets:
                return _err("바꿀 것이 없습니다")
            con.execute(f"UPDATE comment SET {', '.join(sets)} WHERE id=?", (*vals, cid))
            what = "comment-edit" if "text" in body else "markup-edit"
            store.audit(con, c["project_id"], c["datasheet_id"], c["field_key"], what,
                        c["text"] if "text" in body else c["bbox"], body.get("text") if "text" in body else store.J(g.get("bbox")), by)
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
    out, pv = [], _profile_ver(con, pid)
    for d in sorted(latest.values(), key=lambda d: d["tag_key"]):
        x = _ds_full(con, d["id"], pv=pv)
        for i in x["issues"]:                                # the row IS the cached finding (tag fields added in place):
            i.update(ds_id=x["id"], tag=x["tag_key"], tag_raw=x["tag"], valve_type=x["valve_type"],   # no second copy of
                     area_name=x["location"]["area"], site=x["location"]["site"], plant_unit=x["location"]["unit"],   # 17k dicts
                     doc_no=x["doc_no"], rev=x["rev"], document_id=x["document_id"], filename=x["filename"],
                     review_status=x["review_status"])
            out.append(i)
    _ISSUE_CACHE[pid] = (ver, out)
    if len(out) > 5000:                                      # a big rebuild leaves a lot of freed heap behind
        _trim()
    return out


def _by_area(irows, latest, loc_of):
    """Dashboard card: tags · open issues · Major per Area (North · South · Brownfield · W15)."""
    order = {"North": 0, "South": 1, "Brownfield": 2, "W15": 3}
    out = {}
    for d in latest.values():
        a = loc_of.get(d["id"], {}).get("area") or "(not stated)"
        e = out.setdefault(a, {"area": a, "tags": 0, "issues": 0, "major": 0, "units": set()})
        e["tags"] += 1
        if loc_of.get(d["id"], {}).get("unit"):
            e["units"].add(loc_of[d["id"]]["unit"])
    for i in irows:
        if i["status"] == "Dismissed" or i["type"] == "Extraction Review":
            continue
        e = out.setdefault(i.get("area_name") or "(not stated)", {"area": i.get("area_name") or "(not stated)", "tags": 0, "issues": 0, "major": 0, "units": set()})
        e["issues"] += 1
        e["major"] += i["severity"] == "Major"
    return [dict(e, units=sorted(e["units"])) for e in sorted(out.values(), key=lambda e: order.get(e["area"], 9))]


def _issue_counts(rows):
    c = {}
    for i in rows:
        if i["status"] == "Dismissed":
            continue
        c[i["type"]] = c.get(i["type"], 0) + 1
    return c


_ISSUE_JSON: dict[tuple, tuple] = {}           # (pid, compact) -> (issue-cache version, encoded body, rows)  — valve29
_DS_KEYS = ("tag", "doc_no", "rev", "area_name", "site", "plant_unit", "valve_type", "document_id")


@router.get("/api/valve/projects/{pid}/issues")
async def issues_list(pid: int, compact: int = 0, request: Request = None):
    return await run_in_threadpool(issues_json, pid, compact, request)


def issues_json(pid: int, compact: int = 0, request: Request | None = None):
    """All findings of the newest revisions.  compact=1 (the screens, valve29): the proof fields (evidence · basis · op · tol ·
    original_*) stay out — the workbench reads them per datasheet — and the per-datasheet fields are sent once in `ds`
    instead of on every row (500 DS: 8.2 MB → about a third)."""
    con = store.connect()
    rows = project_issues(con, pid)
    ver = (_ISSUE_CACHE.get(pid) or (None,))[0]             # the version the rows were computed for (never an object id)
    hit = _ISSUE_JSON.get((pid, compact))
    if hit and ver is not None and hit[0] == ver and hit[2] is rows:      # rows kept alive in the tuple: `is` cannot alias
        return _gz_response(hit[1], hit[3], request)
    drop = {"filename", "tag_raw", "review_status", "unit", "pd_page", "pd_bbox", "rule", "level"}   # not used by the list screens
    if compact:
        drop |= {"evidence", "basis", "op", "tol", "original_description", "original_severity", "original_expected", "pms_bbox", "pms_page"} | set(_DS_KEYS)
    slim = [{k: ([round(x, 1) for x in v] if k == "bbox" and v else v) for k, v in i.items() if k not in drop and v not in (None, "", [])}
            for i in rows]
    out = {"issues": slim, "counts": _issue_counts(rows), "types": issuesmod.CONTRACTOR_TYPES + ["Extraction Review"],
           "statuses": ISSUE_STATUSES}
    if compact:
        out["ds"] = {i["ds_id"]: {k: i.get(k) for k in _DS_KEYS} for i in rows}
    gz = gzip.compress(json.dumps(out, ensure_ascii=False, separators=(",", ":"), default=str).encode(), 5)   # kept compressed: 15 MB → 2 MB at 990 DS
    etag = f'W/"{hashlib.sha1(repr(("issues", compact, ver)).encode()).hexdigest()[:16]}"'
    _ISSUE_JSON[(pid, compact)] = (ver, gz, rows, etag)
    return _gz_response(gz, etag, request)


@router.put("/api/valve/datasheets/{dsid}/issues/{ikey:path}")
async def issue_state(dsid: int, ikey: str, request: Request):
    """Engineer decision on a finding (valve29).  Body: {decision, reason_cat, note (= reason), conclusion,
    modified_text, modified_severity} — or the pre-valve29 {status, note}.  The decision maps onto the status the rest of
    the tool already uses (store.DECISION_STATUS); every change is appended to decision_log with a snapshot of the
    finding as the engineer saw it (rule · version · text · severity · values · evidence)."""
    body = await request.json()
    dec = body.get("decision") or ""
    if dec:
        if dec not in store.DECISIONS:
            return _err("결정 값이 잘못됐습니다")
        st = store.DECISION_STATUS[dec]
    else:
        st = body.get("status", "Open")
        if st not in ISSUE_STATUSES:
            return _err("상태 값이 잘못됐습니다")
        dec = st if st in ("Confirmed", "Dismissed") else ""          # a status-only call (bulk · old screen) is still a decision
    cat = body.get("reason_cat") or ""
    if cat and cat not in store.REASON_CATS:
        return _err("사유 분류 값이 잘못됐습니다")
    if body.get("decision") in store.NEEDS_REASON and not cat:
        return _err("Dismissed · Not Applicable · Modified 는 사유 분류를 골라야 합니다")
    msev = body.get("modified_severity") or ""
    if msev and msev not in ("Major", "Minor", "Info"):
        return _err("Severity 값이 잘못됐습니다")
    con = store.connect()
    d = store.one(con, "SELECT project_id, tag_key, rev FROM datasheet WHERE id=?", dsid)
    if not d:
        return _err("없는 데이터시트", 404)
    by = _user(request)
    hit = _DEEP_CACHE.get(dsid)                             # the finding as the engineer saw it (bulk changes: no recompute per item)
    full = (hit[1] if hit else None) or _ds_full(con, dsid) or {}
    it = next((i for i in full.get("issues") or [] if i["ikey"] == ikey), None) or {}
    rule = chkmod.rule_of(it.get("check") or "")
    note = str(body.get("note", ""))[:2000]
    with store._LOCK:
        old = store.one(con, "SELECT * FROM issue_state WHERE datasheet_id=? AND ikey=?", dsid, ikey)
        con.execute("INSERT OR REPLACE INTO issue_state(datasheet_id, ikey, status, note, by, at, since, decision, reason_cat, conclusion,"
                    " modified_text, modified_severity, rule_ver) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (dsid, ikey, st, note, by, store.now(), (old or {}).get("since"), dec, cat, str(body.get("conclusion", ""))[:2000],
                     str(body.get("modified_text", ""))[:1000] if body.get("decision") == "Modified" else (old or {}).get("modified_text") or "",
                     msev if body.get("decision") == "Modified" else (old or {}).get("modified_severity") or "", chkmod.RULE_VERSION.get(rule, "")))
        if old and old.get("modified_expected"):        # an edited Required text survives a later decision too
            con.execute("UPDATE issue_state SET modified_expected=? WHERE datasheet_id=? AND ikey=?", (old["modified_expected"], dsid, ikey))
        con.execute("INSERT INTO decision_log(project_id, datasheet_id, tag, rev, ikey, rule, rule_ver, issue_type, finding, severity, actual,"
                    " reference, source_doc, evidence, decision, status, reason_cat, reason, conclusion, modified_text, modified_severity, by, at)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (d["project_id"], dsid, d["tag_key"], d["rev"], ikey, rule or it.get("check") or "", chkmod.RULE_VERSION.get(rule, ""),
                     it.get("type", ikey.split(":")[0]), it.get("original_description") or it.get("description", ""),
                     it.get("original_severity") or it.get("severity", ""), str(it.get("value") or ""), str(it.get("expected") or ""),
                     "; ".join(sorted({e.get("doc") or "" for e in it.get("evidence") or [] if e})) or "Datasheet",
                     store.J(it.get("evidence") or []), dec or st, st, cat, note, str(body.get("conclusion", ""))[:2000],
                     str(body.get("modified_text", ""))[:1000], msev, by, store.now()))
        store.audit(con, d["project_id"], dsid, ikey, "issue", (old or {}).get("status", "Open"), st, by,
                    (f"[{dec}{' · ' + cat if cat else ''}] " if dec else "") + note)
        con.commit()
    return {"ok": True, "status": st, "decision": dec}


@router.put("/api/valve/datasheets/{dsid}/issues-text/{ikey:path}")
async def issue_text(dsid: int, ikey: str, request: Request):
    """valve29 — the engineer edits / supplements the tool's comment: {text, expected} (empty = back to the tool's own).
    The decision and status stay as they are; the tool's wording is kept (original_description) and the edit is logged."""
    body = await request.json()
    text, exp = str(body.get("text") or "").strip()[:1500], str(body.get("expected") or "").strip()[:500]
    con = store.connect()
    d = store.one(con, "SELECT project_id, tag_key, rev FROM datasheet WHERE id=?", dsid)
    if not d:
        return _err("없는 데이터시트", 404)
    by = _user(request)
    hit = _DEEP_CACHE.get(dsid)
    full = (hit[1] if hit else None) or _ds_full(con, dsid) or {}
    it = next((i for i in full.get("issues") or [] if i["ikey"] == ikey), None)
    if not it:
        return _err("없는 지적", 404)
    with store._LOCK:
        old = store.one(con, "SELECT * FROM issue_state WHERE datasheet_id=? AND ikey=?", dsid, ikey)
        if old:
            con.execute("UPDATE issue_state SET modified_text=?, modified_expected=?, by=?, at=? WHERE datasheet_id=? AND ikey=?",
                        (text, exp, by, store.now(), dsid, ikey))
        else:
            con.execute("INSERT INTO issue_state(datasheet_id, ikey, status, note, by, at, modified_text, modified_expected) VALUES (?,?,?,?,?,?,?,?)",
                        (dsid, ikey, "Open", "", by, store.now(), text, exp))
        rule = chkmod.rule_of(it.get("check") or "")
        con.execute("INSERT INTO decision_log(project_id, datasheet_id, tag, rev, ikey, rule, rule_ver, issue_type, finding, severity, actual,"
                    " reference, source_doc, evidence, decision, status, reason_cat, reason, conclusion, modified_text, modified_severity, by, at)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (d["project_id"], dsid, d["tag_key"], d["rev"], ikey, rule or it.get("check") or "", chkmod.RULE_VERSION.get(rule, ""),
                     it.get("type", ""), it.get("original_description") or it.get("description", ""), it.get("severity", ""), str(it.get("value") or ""),
                     str(it.get("original_expected") or it.get("expected") or ""), "", store.J(it.get("evidence") or []), "Edited",
                     (old or {}).get("status") or "Open", "", "comment text " + ("edited" if text or exp else "reset to the tool's"), "", text, "", by, store.now()))
        store.audit(con, d["project_id"], dsid, ikey, "issue-text", it.get("description", "")[:300], text[:300] or "(tool text)", by, exp[:200])
        con.commit()
    return {"ok": True}


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
def grid(pid: int, request: Request):
    return _cached("grid", pid, lambda con: _json(_grid(con, pid)), request=request)


def _grid(con, pid):
    pv = _profile_ver(con, pid)
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
        loc = (_ds_full(con, i, pv=pv) or {}).get("location") or {}
        rows_.append({"id": i, "tag": m["tag_key"], "tag_raw": m["tag"], "valve_type": m["valve_type"], "rev": m["rev"],
                      "area": loc.get("area", ""), "site": loc.get("site", ""), "unit": loc.get("unit", ""),
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
            return pdf.tobytes(garbage=4, deflate=True, use_objstms=1)
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
    full, pv = [], _profile_ver(con, pid)
    for d in latest.values():
        x = _ds_full(con, d["id"], pv=pv)
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
    pv = _profile_ver(con, pid)
    ver = []
    for d in _latest(store.rows(con, "SELECT id, tag_key, rev FROM datasheet WHERE project_id=?", pid)).values():   # valve28: tags × checks
        full = _ds_full(con, d["id"], pv=pv)
        if full and full.get("verification"):
            ver.append({"tag": full["tag"], "doc_no": full["doc_no"], "rev": full["rev"], "area": (full.get("location") or {}).get("area", ""),
                        "unit": (full.get("location") or {}).get("unit", ""), "verification": full["verification"]})
    ver.sort(key=lambda v: (exports.AREA_ORDER.get(v["area"], 9), v["unit"], v["tag"]))
    return exports.issues_xlsx(rows, base, pname, by, srcs, verification=ver), len(rows), pname


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
    out, pv = [], _profile_ver(con, pid)
    for d in sorted(latest.values(), key=lambda d: d["tag_key"]):
        x = _ds_full(con, d["id"], pv=pv)                # deep: the PMS rows come from the per-datasheet cache
        F = {f["key"]: f for f in x["fields"]}
        for r in x.get("pms") or []:
            f = F.get(r["key"]) or {}
            out.append(dict(r, ds_id=x["id"], tag=x["tag_key"], doc_no=x["doc_no"], rev=x["rev"], area=x["area"],
                            document_id=x["document_id"], ds_page=f.get("page") or x["pages"][0], ds_bbox=f.get("bbox")))
    return pdoc, out


def _project_process(con, pid):
    proc, pdoc = _process_for(con, pid)
    if not proc:
        return None, []
    latest = _latest(store.rows(con, "SELECT id, tag_key, rev FROM datasheet WHERE project_id=?", pid))
    out, pv = [], _profile_ver(con, pid)
    for d in sorted(latest.values(), key=lambda d: d["tag_key"]):
        x = _ds_full(con, d["id"], pv=pv)
        for r in x.get("process") or []:
            out.append(dict(r, ds_id=x["id"], tag=x["tag_key"], doc_no=x["doc_no"], rev=x["rev"], document_id=x["document_id"],
                            ds_page=r.get("ds_page") or x["pages"][0], process_ref=bool(x.get("process_ref"))))
    return dict(pdoc, doc_no=proc.get("doc_no"), tags=proc.get("n_tags")), out


@router.get("/api/valve/projects/{pid}/process")
async def process_rows(pid: int, request: Request):
    """Process Data Verification for every tag (Phase 3 engine, app/valve/process.py)."""
    return await run_in_threadpool(_cached, "process", pid, lambda con: _process_body(con, pid), None, request)


def _process_body(con, pid):
    pdoc, rows = _project_process(con, pid)
    return _json({"process_doc": pdoc, "rows": rows})


def _revisions_xlsx(pid: int, by: str):
    con = store.connect()
    pname = (store.one(con, "SELECT name FROM project WHERE id=?", pid) or {}).get("name", "")
    dss = store.rows(con, "SELECT id, tag_key, rev FROM datasheet WHERE project_id=?", pid)
    by_tag = {}
    for d in dss:
        by_tag.setdefault(d["tag_key"], []).append(d)
    entries = []
    for tag, L in sorted(by_tag.items()):
        if len(L) < 2:
            continue
        L.sort(key=lambda r: (store.rev_key(r["rev"]), r["id"]))
        for a, b in zip(L, L[1:]):
            x, y = _ds_full(con, a["id"], deep=False), _ds_full(con, b["id"], deep=False)
            entries.append({"tag": tag, "doc_no": y["doc_no"], "prev_rev": x["rev"], "new_rev": y["rev"], "rows": compare(x, y)})
    data, n = exports.revisions_xlsx(entries, pname, by)
    return data, n, pname


@router.get("/api/valve/projects/{pid}/revisions.xlsx")
async def revisions_xlsx(pid: int, request: Request):
    """Every changed cell between consecutive revisions of every tag (leftover item from the valve03 handoff)."""
    data, n, pname = await run_in_threadpool(_revisions_xlsx, pid, _user(request))
    con = store.connect()
    store.audit(con, pid, None, None, "export", None, "revisions.xlsx", _user(request), f"{n} changes")
    con.commit()
    fn = f"{pname.replace(' ', '_')}_Revision_Comparison_{store.now()[:10]}.xlsx"
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(fn)}", "X-Count": str(n)})


@router.get("/api/valve/projects/{pid}/pms")
async def pms_rows(pid: int, request: Request):
    return await run_in_threadpool(_cached, "pms", pid, lambda con: _pms_body(con, pid), None, request)


def _pms_body(con, pid):
    pdoc, rows = _project_pms(con, pid)
    return _json({"pms_doc": pdoc, "rows": rows})


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
                        summary: int = 1, margin: int = 1, flatten: int = 1):
    """Marked-up datasheet pages (issues in colour, numbered, printable) + an Issue Summary page per datasheet."""
    con = store.connect()
    pname = store.one(con, "SELECT name FROM project WHERE id=?", pid)["name"]
    rows = _select(project_issues(con, pid), types, dismissed, tag, severity)
    entries = _markup_entries(con, rows)
    data = await run_in_threadpool(exports.markup_pdf, entries, pname, "Valve Datasheet Review - Mark-up", bool(summary),
                                  bool(margin), bool(flatten))
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


def _settings(con, pid) -> dict:
    return {r["key"]: r["value"] for r in store.rows(con, "SELECT key, value FROM project_setting WHERE project_id=?", pid)}


@router.get("/api/valve/projects/{pid}/rules/performance")
def rules_performance(pid: int, request: Request):
    """valve29 — Rule Performance: findings per rule and how engineers decided them (statistics only)."""
    return _cached("rules", pid, lambda con: _rules_performance(con, pid), arg=dt.date.today().isoformat(), request=request)   # the 3-month trend moves by date


def _rules_performance(con, pid):
    rows = project_issues(con, pid)
    log = store.rows(con, "SELECT rule, decision, status, at FROM decision_log WHERE project_id=?", pid)
    out = ruleperf.performance(rows, log, _settings(con, pid))
    out["reason_cats"] = store.REASON_CATS
    out["decisions"] = store.DECISIONS
    return _json(out)


@router.put("/api/valve/projects/{pid}/settings")
async def put_settings(pid: int, request: Request):
    body = await request.json()
    con = store.connect()
    by = _user(request)
    ok = {}
    for k, v in (body or {}).items():
        if k == "rp_min_n" and str(v).isdigit() and 1 <= int(v) <= 10000:
            ok[k] = str(int(v))
        elif k == "rp_dismiss_rate":
            try:
                x = float(v)
            except (TypeError, ValueError):
                continue
            if 0 < x <= 1:
                ok[k] = str(x)
    with store._LOCK:
        for k, v in ok.items():
            con.execute("INSERT OR REPLACE INTO project_setting(project_id, key, value, by, at) VALUES (?,?,?,?,?)", (pid, k, v, by, store.now()))
            store.audit(con, pid, None, None, "setting", None, f"{k}={v}", by, "")
        con.commit()
    return {"ok": True, "saved": ok}


@router.get("/api/valve/projects/{pid}/rules/decisions")
def rule_decisions(pid: int, rule: str = "", limit: int = 200):
    """The decision log of one rule (newest first) — what was decided, why, on which finding."""
    con = store.connect()
    q = "SELECT id, tag, rev, ikey, rule, rule_ver, issue_type, finding, severity, actual, reference, source_doc, decision, status," \
        " reason_cat, reason, conclusion, modified_text, modified_severity, by, at FROM decision_log WHERE project_id=?"
    args = [pid]
    if rule:
        q += " AND rule=?"
        args.append(rule)
    q += " ORDER BY id DESC LIMIT ?"
    args.append(max(1, min(2000, int(limit))))
    return {"rows": store.rows(con, q, *args)}


@router.get("/api/valve/projects/{pid}/rule-changes")
def rule_changes(pid: int):
    con = store.connect()
    return {"rows": store.rows(con, "SELECT * FROM rule_change WHERE project_id=? ORDER BY id DESC", pid),
            "statuses": ruleperf.STATUSES, "versions": chkmod.RULE_VERSION}


@router.post("/api/valve/projects/{pid}/rule-changes")
async def rule_change_new(pid: int, request: Request):
    """Record a proposed change of a rule (directive §1.4).  The rule code is NOT changed here — a developer changes it
    after approval and bumps checks.RULE_VERSION; only then can the record be marked Applied."""
    b = await request.json()
    rule = b.get("rule") or ""
    if rule not in chkmod.RULE_VERSION:
        return _err("없는 Rule ID")
    row = {k: str(b.get(k) or "")[:4000] for k in ruleperf.STEPS}
    st, why = ruleperf.next_status(row, "Proposed")
    if not st:
        return _err(why)
    con = store.connect()
    by = _user(request)
    cur = chkmod.RULE_VERSION[rule]
    to = str(b.get("to_ver") or (int(cur) + 1 if cur.isdigit() else cur + "+1"))
    with store._LOCK:
        c = con.execute("INSERT INTO rule_change(project_id, rule, from_ver, to_ver, current_logic, proposed_logic, reason, regression,"
                        " simulation, status, created_by, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (pid, rule, cur, to, row["current_logic"], row["proposed_logic"], row["reason"], row["regression"],
                         row["simulation"], st, by, store.now(), store.now()))
        store.audit(con, pid, None, rule, "rule-change", None, st, by, row["reason"][:300])
        con.commit()
    return {"ok": True, "id": c.lastrowid, "status": st}


@router.put("/api/valve/rule-changes/{cid}")
async def rule_change_update(cid: int, request: Request):
    b = await request.json()
    con = store.connect()
    row = store.one(con, "SELECT * FROM rule_change WHERE id=?", cid)
    if not row:
        return _err("없는 변경 기록", 404)
    if row["status"] in ("Applied", "Rejected"):
        return _err("끝난 기록은 고칠 수 없습니다")
    upd = {k: str(b[k])[:4000] for k in ruleperf.STEPS if k in b}
    new = dict(row, **upd)
    st, why = row["status"], ""
    if b.get("status") and b["status"] != st:
        nst, why = ruleperf.next_status(new, b["status"])
        st = nst or st                                        # a refused move still keeps the text the engineer typed
    by = _user(request)
    with store._LOCK:
        sets = ", ".join(f"{k}=?" for k in upd) + (", " if upd else "") + "status=?, updated_at=?"
        args = list(upd.values()) + [st, store.now()]
        if st == "Approved" and row["status"] != "Approved":
            sets += ", approved_by=?, approved_at=?"
            args += [by, store.now()]
        con.execute(f"UPDATE rule_change SET {sets} WHERE id=?", (*args, cid))
        store.audit(con, row["project_id"], None, row["rule"], "rule-change", row["status"], st, by, "")
        con.commit()
    if why:
        return _err(why)
    return {"ok": True, "status": st}


def _req_rows(con, pid) -> dict:
    """valve29 — special requirements of every valve at a glance (newest revision): one row per tag with the requirement
    columns (requirements.columns — the datasheet row decides, notes add, sources in brackets) + Area / Site / Unit totals.
    A requirement 'applies' when its cell is filled and is not 'Not Required'."""
    latest = _latest(store.rows(con, "SELECT id, tag_key, rev FROM datasheet WHERE project_id=?", pid))
    pv = _profile_ver(con, pid)
    heads = [h for _, h in reqmod.COLUMNS]
    tags = []
    for d in latest.values():
        x = _ds_full(con, d["id"], pv=pv) or {}
        cells = reqmod.columns(x.get("requirements") or [])
        loc = x.get("location") or {}
        tags.append({"ds_id": x.get("id"), "tag": x.get("tag_key"), "valve_type": x.get("valve_type"), "rev": x.get("rev"), "doc_no": x.get("doc_no"),
                     "area": loc.get("area") or "(not stated)", "site": loc.get("site") or "", "unit": loc.get("unit") or "", "cells": cells,
                     "on": [h for h in heads if cells.get(h) and not str(cells[h]).startswith("Not Required")]})
    tags.sort(key=lambda t: (exports.AREA_ORDER.get(t["area"], 9), t["site"], t["unit"], t["tag"]))
    used = [h for h in heads if any(h in t["on"] or t["cells"].get(h) for t in tags)]

    def group(key):
        out = {}
        for t in tags:
            g = out.setdefault(key(t), {"tags": 0, "counts": {h: 0 for h in used}, "units": set()})
            g["tags"] += 1
            g["units"].add(t["unit"])
            for h in t["on"]:
                if h in g["counts"]:
                    g["counts"][h] += 1
        return out
    ba = group(lambda t: t["area"])
    by_area = [{"area": a, "units": sorted(u for u in ba[a]["units"] if u), "tags": ba[a]["tags"], "counts": ba[a]["counts"]}
               for a in sorted(ba, key=lambda a: exports.AREA_ORDER.get(a, 9))]
    bu = group(lambda t: (t["area"], t["site"], t["unit"]))
    by_unit = [{"area": k[0], "site": k[1], "unit": k[2], "tags": v["tags"], "counts": v["counts"]}
               for k, v in sorted(bu.items(), key=lambda kv: (exports.AREA_ORDER.get(kv[0][0], 9), kv[0][1], kv[0][2]))]
    total = {"tags": len(tags), "counts": {h: sum(1 for t in tags if h in t["on"]) for h in used}}
    return {"columns": used, "tags": tags, "by_area": by_area, "by_unit": by_unit, "total": total}


@router.get("/api/valve/projects/{pid}/requirements")
def requirements_summary(pid: int, request: Request):
    return _cached("requirements", pid, lambda con: _json(_req_rows(con, pid)), request=request)


@router.get("/api/valve/projects/{pid}/requirements.xlsx")
async def requirements_xlsx(pid: int, request: Request, area: str = "", req: str = ""):
    """Special Requirements Excel: Summary by Area · Summary by Unit · By Tag (filtered like the screen when area / req given)."""
    con = store.connect()
    pname = store.one(con, "SELECT name FROM project WHERE id=?", pid)["name"]
    data = await run_in_threadpool(lambda: exports.requirements_xlsx(_req_rows(con, pid), pname, _base(request), area, req))
    store.audit(con, pid, None, None, "export", None, "requirements.xlsx", _user(request), f"area={area} req={req}")
    con.commit()
    fn = f"{pname.replace(' ', '_')}_Valve_Special_Requirements_{store.now()[:10]}.xlsx"
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(fn)}"})


@router.get("/api/valve/projects/{pid}/feedback.json")
def feedback_json(pid: int, request: Request):
    """Review feedback for the developers (P&ID hotfix82 'VOC → 재학습 경로'): what reviewers decided about the tool's
    output.  verdicts = issue Confirmed / Dismissed / Resolved (+ note) · corrections = read value → corrected value ·
    missed = reviewer mark-ups in category error / missing (things the rules did not raise).  The rule code never reads
    this file; spike/valve_voc.py scores the tool against it (precision of each rule, reading errors, misses)."""
    con = store.connect()
    pname = (store.one(con, "SELECT name FROM project WHERE id=?", pid) or {}).get("name", "")
    latest = _latest(store.rows(con, "SELECT id, tag_key, rev FROM datasheet WHERE project_id=?", pid))
    shas = {r["id"]: r["sha256"] for r in store.rows(con, "SELECT id, sha256 FROM document WHERE project_id=?", pid)}
    out = {"kind": "valve-feedback", "version": 2, "project": pname, "generated": store.now(), "by": _user(request),
           "datasheets": 0, "issues_raised": 0, "verdicts": [], "corrections": [], "missed": []}
    for d in sorted(latest.values(), key=lambda d: d["tag_key"]):
        x = _ds_full(con, d["id"])
        base = {"tag": x["tag_key"], "doc_no": x["doc_no"], "rev": x["rev"], "file": x["filename"],
                "sha256": shas.get(x["document_id"])}
        out["datasheets"] += 1
        for i in x["issues"]:
            if i.get("comment_id"):
                continue
            out["issues_raised"] += 1
            if i["status"] != "Open":
                out["verdicts"].append(dict(base, ikey=i["ikey"], type=i["type"], key=i["key"], value=i["value"],
                                            description=i.get("original_description") or i["description"], verdict=i["status"], note=i.get("note", ""),
                                            page=i["page"], bbox=i["bbox"],
                                            # valve29 (version 2): the engineer decision as recorded
                                            rule=chkmod.rule_of(i.get("check") or ""), rule_ver=chkmod.RULE_VERSION.get(chkmod.rule_of(i.get("check") or ""), ""),
                                            decision=i.get("decision", ""), reason_cat=i.get("reason_cat", ""), conclusion=i.get("conclusion", ""),
                                            expected=i.get("expected", ""), evidence=i.get("evidence") or []))
        for f in x["fields"]:
            if f.get("edited_value") is not None:
                out["corrections"].append(dict(base, key=f["key"], label=f.get("label"), read=f["value"],
                                               corrected=f["edited_value"], page=f["page"], bbox=f["bbox"],
                                               by=f.get("edited_by")))
        for c in x["comments"]:
            if c.get("category") in ("error", "missing") and c.get("bbox"):
                out["missed"].append(dict(base, category=c["category"], text=c["text"], page=c["page"], bbox=c["bbox"],
                                          kind=c.get("kind")))
    fn = f"valve_feedback_{pname or pid}_{store.now()[:10]}.json"
    return Response(json.dumps(out, ensure_ascii=False, indent=1), media_type="application/json",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(fn)}"})


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
