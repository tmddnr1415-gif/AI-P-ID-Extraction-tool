"""HTTP surface: upload a PDF, watch it analyse, review the result, ship Excel.

Analysis runs in a background thread with a one-at-a-time queue - it is CPU
bound and holds a whole PDF's vector data in memory, so running two at once
would only make both slower.  Progress is pushed over SSE rather than polled.

The output gate is deliberately narrow: `POST /jobs/{id}/snapshot` is the only
way to make a revision, and `GET /revisions/{id}/excel` is the only way to get
a workbook.  Live rows are never exported.
"""

from __future__ import annotations

import hashlib
import io
import json
import queue
import sys
import threading
import time
import traceback
import uuid
import zipfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import (FileResponse, HTMLResponse, JSONResponse,
                               StreamingResponse)
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import db, excel_out, pipeline           # noqa: E402
from app.pipeline import CFG                       # noqa: E402

DATA_DIR = Path(__file__).resolve().parent / "_data"
UPLOADS = DATA_DIR / "uploads"
OUTPUTS = DATA_DIR / "outputs"
DB_PATH = DATA_DIR / "app.db"
STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(title="P&ID extraction")
CON = db.connect(DB_PATH)

# One analysis at a time; listeners get progress events per job.
_JOBS: "queue.Queue[str]" = queue.Queue()
_LISTENERS: dict[str, list] = {}
_LOCK = threading.Lock()


def _emit(job_id: str, payload: dict) -> None:
    with _LOCK:
        for q in _LISTENERS.get(job_id, []):
            q.put(payload)


def _worker() -> None:
    while True:
        job_id = _JOBS.get()
        row = db.get_job(CON, job_id)
        if row is None:
            continue
        try:
            db.set_progress(CON, job_id, 0.0, "starting")
            _emit(job_id, {"progress": 0.0, "message": "starting", "status": "running"})

            def progress(done, total, message):
                frac = done / max(total, 1)
                db.set_progress(CON, job_id, frac, message)
                _emit(job_id, {"progress": frac, "message": message,
                               "status": "running"})

            result = pipeline.analyse(Path(row["pdf_path"]), progress=progress)
            result["fingerprint"] = pipeline.fingerprint(result)
            summary = db.store_result(CON, job_id, result)
            _emit(job_id, {"progress": 1.0, "message": "done", "status": "done",
                           "summary": summary})
        except Exception as exc:                     # noqa: BLE001
            traceback.print_exc()
            db.set_progress(CON, job_id, 0.0, f"{type(exc).__name__}: {exc}", "failed")
            _emit(job_id, {"progress": 0.0, "status": "failed",
                           "message": f"{type(exc).__name__}: {exc}"})
        finally:
            _JOBS.task_done()


threading.Thread(target=_worker, daemon=True).start()


# --------------------------------------------------------------------------
# Upload and analysis
# --------------------------------------------------------------------------

@app.post("/jobs")
async def create_job(pdf: UploadFile = File(...)):
    raw = await pdf.read()
    if not raw[:5] == b"%PDF-":
        raise HTTPException(400, "that file is not a PDF")
    sha = hashlib.sha256(raw).hexdigest()
    job_id = uuid.uuid4().hex[:12]
    UPLOADS.mkdir(parents=True, exist_ok=True)
    path = UPLOADS / f"{job_id}_{Path(pdf.filename).name}"
    path.write_bytes(raw)
    db.create_job(CON, job_id, Path(pdf.filename).name, sha, path)
    _JOBS.put(job_id)
    return {"job_id": job_id, "pdf_name": Path(pdf.filename).name, "sha256": sha}


@app.post("/jobs/{job_id}/reanalyse")
def reanalyse(job_id: str):
    """Re-run the engine, keeping every reviewer edit."""
    if db.get_job(CON, job_id) is None:
        raise HTTPException(404, "no such job")
    db.set_progress(CON, job_id, 0.0, "queued", "queued")
    _JOBS.put(job_id)
    return {"job_id": job_id, "queued": True}


@app.get("/jobs")
def jobs():
    return [dict(r) for r in db.list_jobs(CON)]


@app.get("/jobs/{job_id}")
def job(job_id: str):
    row = db.get_job(CON, job_id)
    if row is None:
        raise HTTPException(404, "no such job")
    out = dict(row)
    out["engine"] = json.loads(out.pop("engine_json") or "{}")
    out["review_count"] = db.review_count(CON, job_id)
    out["revisions"] = [dict(r) for r in db.list_revisions(CON, job_id)]
    return out


@app.get("/jobs/{job_id}/events")
def events(job_id: str):
    """Server-sent progress.  Emits the current state first so a late listener
    is not left waiting for an analysis that has already finished."""
    q: "queue.Queue[dict]" = queue.Queue()
    with _LOCK:
        _LISTENERS.setdefault(job_id, []).append(q)

    def stream():
        row = db.get_job(CON, job_id)
        if row is not None:
            yield _sse({"progress": row["progress"], "message": row["message"],
                        "status": row["status"]})
        try:
            while True:
                try:
                    yield _sse(q.get(timeout=15))
                except queue.Empty:
                    yield ": keep-alive\n\n"
        finally:
            with _LOCK:
                _LISTENERS.get(job_id, []).remove(q)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------

@app.get("/jobs/{job_id}/rows")
def rows(job_id: str, tab: str = "ALL"):
    return db.merged_rows(CON, job_id, tab)


@app.get("/jobs/{job_id}/review")
def job_review(job_id: str):
    """Findings that belong to the document rather than to any single row."""
    job = db.get_job(CON, job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    engine = json.loads(job["engine_json"] or "{}")
    return {"job_review": engine.get("job_review", []),
            "row_review": db.review_count(CON, job_id)}


@app.get("/jobs/{job_id}/pages")
def pages(job_id: str):
    out = []
    for r in CON.execute("SELECT * FROM pid_page WHERE job_id=? ORDER BY page_no",
                         (job_id,)).fetchall():
        d = dict(r)
        d["layers"] = json.loads(d.pop("layers_json"))
        out.append(d)
    return out


@app.get("/jobs/{job_id}/page/{page_no}.png")
def page_png(job_id: str, page_no: int, zoom: float = 1.6):
    """The sheet rendered on demand - the viewer's background only.

    Kept separate from the overlay data on purpose: the boxes come from JSON
    (`/pages`), so a rule change means new JSON, not a re-render.
    """
    row = db.get_job(CON, job_id)
    if row is None:
        raise HTTPException(404, "no such job")
    import pymupdf
    doc = pymupdf.open(row["pdf_path"])
    if not 1 <= page_no <= doc.page_count:
        raise HTTPException(404, "no such page")
    page = doc[page_no - 1]
    pm = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
    data = pm.tobytes("png")
    doc.close()
    return StreamingResponse(io.BytesIO(data), media_type="image/png",
                             headers={"Cache-Control": "public, max-age=3600"})


@app.post("/jobs/{job_id}/rows")
async def add_row(job_id: str, payload: dict):
    """Create a row a reviewer wants that the engine did not propose."""
    if db.get_job(CON, job_id) is None:
        raise HTTPException(404, "no such job")
    key = db.add_row(CON, job_id,
                     int(payload.get("page_no") or 0),
                     payload.get("tab") or "FIELD",
                     payload.get("origin") or "",
                     payload.get("drawing_no") or "",
                     payload.get("values") or {})
    return {"key": key, "review_count": db.review_count(CON, job_id)}


@app.post("/jobs/{job_id}/rows/{key}/copy")
def copy_row(job_id: str, key: str):
    try:
        new_key = db.copy_row(CON, job_id, key)
    except KeyError:
        raise HTTPException(404, "no such row")
    return {"key": new_key, "review_count": db.review_count(CON, job_id)}


@app.delete("/jobs/{job_id}/rows/{key}")
def delete_row(job_id: str, key: str):
    try:
        out = db.remove_row(CON, job_id, key)
    except KeyError:
        raise HTTPException(404, "no such row")
    out["review_count"] = db.review_count(CON, job_id)
    return out


@app.post("/jobs/{job_id}/rows/{key}/restore")
def restore_row(job_id: str, key: str):
    db.restore_row(CON, job_id, key)
    return {"key": key, "review_count": db.review_count(CON, job_id)}


@app.patch("/jobs/{job_id}/rows/{key}")
async def patch_row(job_id: str, key: str, payload: dict):
    field = payload.get("field")
    value = payload.get("value")
    if field == "qty" and value not in (None, ""):
        try:
            value = int(value)
        except (TypeError, ValueError):
            raise HTTPException(400, "Q'ty must be a whole number")
    try:
        user = db.set_user_value(CON, job_id, key, field, value)
    except KeyError:
        raise HTTPException(404, "no such row")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"key": key, "user": user, "review_count": db.review_count(CON, job_id)}


# --------------------------------------------------------------------------
# Output gate
# --------------------------------------------------------------------------

@app.post("/jobs/{job_id}/snapshot")
def make_snapshot(job_id: str, payload: dict = None):
    """'Review complete' - freeze the current data as a revision.

    Allowed with outstanding review items, because a reviewer may knowingly
    ship a partial list; the count is recorded on the revision so the snapshot
    says what state it was taken in.
    """
    if db.get_job(CON, job_id) is None:
        raise HTTPException(404, "no such job")
    label = (payload or {}).get("label", "")
    origins = (payload or {}).get("origins") or list(db.ALL_ORIGINS)
    unknown = set(origins) - set(db.ALL_ORIGINS)
    if unknown:
        raise HTTPException(400, f"unknown origin(s): {sorted(unknown)}")
    rev = db.snapshot(CON, job_id, label, origins)
    snap = db.get_revision(CON, rev)
    return {"revision_id": rev, "origins": origins,
            "rows": len(snap["rows"]),
            "review_count": db.review_count(CON, job_id)}


@app.get("/jobs/{job_id}/revisions")
def revisions(job_id: str):
    return [dict(r) for r in db.list_revisions(CON, job_id)]


@app.get("/revisions/{revision_id}/excel")
def revision_excel(revision_id: int):
    """Deliverables built from a snapshot.  Never from live rows."""
    snap = db.get_revision(CON, revision_id)
    if snap is None:
        raise HTTPException(404, "no such revision")
    templates = _templates()
    out_dir = OUTPUTS / f"rev{revision_id}"
    result = excel_out.write_all(snap, templates, out_dir, CFG)
    if not result["written"]:
        raise HTTPException(
            400, {"error": "no deliverable had a template to fill",
                  "skipped": result["skipped"]})

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for item in result["written"]:
            z.write(item["path"], Path(item["path"]).name)
        z.writestr("MANIFEST.json", json.dumps({
            "revision_id": revision_id,
            "pdf_name": snap["pdf_name"],
            "pdf_sha256": snap["pdf_sha256"],
            "engine_fingerprint": snap["fingerprint"],
            "written": result["written"],
            "skipped": result["skipped"],
            "note": "unmapped_values lists edits with no column in that "
                    "deliverable's form; they are stored but not written",
        }, indent=1))
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="application/zip",
        headers={"Content-Disposition":
                 f'attachment; filename="rev{revision_id}_deliverables.zip"'})


@app.get("/templates")
def templates():
    return {k: (str(v) if v else None) for k, v in _templates().items()}


@app.post("/templates")
async def upload_template(kind: str = Form(...), file: UploadFile = File(...)):
    if kind not in excel_out.DELIVERABLES:
        raise HTTPException(400, f"unknown deliverable '{kind}'")
    TEMPLATES.mkdir(parents=True, exist_ok=True)
    path = TEMPLATES / f"{kind}.xlsx"
    path.write_bytes(await file.read())
    return {"kind": kind, "path": str(path)}


TEMPLATES = DATA_DIR / "templates"

# Templates the repository already ships, used when none has been uploaded.
_BUILTIN = {
    "FIELD": ROOT / "data" / "CZE_Field_Instrument.xlsx",
    "BFV": ROOT / "data" / "CZI_Butterfly_Valve.xlsx",
    "MOV": ROOT / "data" / "CZH_MOV_Gate_Globe.xlsx",
}


def _templates() -> dict:
    out = {}
    for kind in excel_out.DELIVERABLES:
        uploaded = TEMPLATES / f"{kind}.xlsx"
        if uploaded.exists():
            out[kind] = uploaded
        elif kind in _BUILTIN and _BUILTIN[kind].exists():
            out[kind] = _BUILTIN[kind]
        else:
            out[kind] = None
    return out


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC / "index.html").read_text(encoding="utf-8")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
