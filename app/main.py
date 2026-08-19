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
import os
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

# Verification mode.  Attributing a drawing to MATCHED or PDF_ONLY needs a
# *finished* instrument list to attribute it against, and in real use no such
# file exists - the inputs are the drawings and an empty output form.  So the
# answer key is opt-in through the environment and off by default:
#
#   PID_VERIFY_EXCEL=data/CZE_Field_Instrument.xlsx ./run.sh
#
# With it unset every drawing is DRAWING, the origin column and its filter stay
# out of the way, and nothing reads anything out of data/.
VERIFY_AGAINST = (Path(os.environ["PID_VERIFY_EXCEL"]).expanduser()
                  if os.environ.get("PID_VERIFY_EXCEL") else None)

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

            result = pipeline.analyse(Path(row["pdf_path"]), progress=progress,
                                      reference=VERIFY_AGAINST)
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
    """The grid's rows, each carrying the review codes it is flagged under.

    The codes ride on the row rather than being fetched separately, because the
    screen filters on them on every click and a second round trip per click is
    latency the reviewer feels.
    """
    out = db.merged_rows(CON, job_id, tab)
    states = db.review_states(CON, job_id)
    for row in out:
        row["review_codes"] = review_codes(row)
        row["review_state"] = states.get(row["key"], {})
    return out


@app.get("/jobs/{job_id}/review")
def job_review(job_id: str):
    """Every reason a person has to look, filed under the axis it belongs to.

    The axis answers "what am I being asked to decide", which is a different
    question from "which deliverable is this row in" - the tabs already answer
    that one.  Counts come with `done` so the screen can show progress rather
    than a number that never moves.
    """
    job = db.get_job(CON, job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    engine = json.loads(job["engine_json"] or "{}")
    rows = db.merged_rows(CON, job_id, "ALL")
    states = db.review_states(CON, job_id)
    axes = pipeline.CFG.data.get("review_axes") or {}
    by_code = {str(k).upper(): str(v).upper()
               for k, v in (axes.get("codes") or {}).items()}
    order = [str(a).upper() for a in (axes.get("order") or ())]
    labels = {str(k).upper(): str(v) for k, v in (axes.get("labels") or {}).items()}

    counts: dict = {}
    for row in rows:
        for code in review_codes(row):
            axis = by_code.get(code, "OTHER")
            slot = counts.setdefault((axis, code), {"open": 0, "done": 0,
                                                    "states": {}, "keys": []})
            st = (states.get(row["key"], {}).get(code) or {}).get("state") or ""
            if st:
                slot["done"] += 1
                slot["states"][st] = slot["states"].get(st, 0) + 1
            else:
                slot["open"] += 1
            slot["keys"].append(row["key"])
    # Reviewer markup is one fact per drawing, not one per row: 534 rows on the
    # marked-up sheets would drown every other reason on the screen, and there is
    # only one thing to decide per drawing - what the client meant by it.
    marked = sorted({row.get("drawing_no") or "" for row in rows
                     if row.get("annotation")} - {""})
    for drawing in marked:
        axis = by_code.get("REVIEWER_MARKUP", "OTHER")
        slot = counts.setdefault((axis, "REVIEWER_MARKUP"),
                                 {"open": 0, "done": 0, "states": {}, "keys": []})
        slot["open"] += 1
    # the document-level findings are their own axis entries, one per finding
    for finding in engine.get("job_review", []):
        code = str(finding.get("kind") or "OTHER").upper()
        axis = by_code.get(code, "OTHER")
        slot = counts.setdefault((axis, code), {"open": 0, "done": 0,
                                                "states": {}, "keys": []})
        slot["open"] += 1

    seen = [a for a in order if any(k[0] == a for k in counts)]
    seen += sorted({k[0] for k in counts} - set(seen))
    out = []
    for axis in seen:
        codes = [{"code": c, "label": REVIEW_LABELS.get(c, c), **v}
                 for (a, c), v in sorted(counts.items()) if a == axis]
        out.append({"axis": axis, "label": labels.get(axis, axis),
                    "open": sum(c["open"] for c in codes),
                    "done": sum(c["done"] for c in codes),
                    "codes": codes})
    return {"axes": out,
            "labels": REVIEW_LABELS,
            "job_review": engine.get("job_review", []),
            "row_review": db.review_count(CON, job_id),
            "states": states}


# What each code asks of the reviewer, in one line.  Kept beside the API rather
# than in the browser so a caller that is not the app sees the same wording.
REVIEW_LABELS = {
    "VENDOR_MARK_UNDEFINED": "벤더마크가 이 도면 NOTES 에 정의되지 않음 — 포함/제외 판단",
    "SCOPE_OVERRIDE_UNRESOLVED": "시트 승수의 예외 문구가 있음 — 어느 항목이 예외인지 판단",
    "MULTI_SIGNAL_BUNDLE": "맞닿은 신호 버블 — 물리 수량 합산 여부 판단",
    "MULTIPLIER_UNDEFINED": "unit code 에 승수가 없어 Q'ty 를 비워 둠",
    "DESCRIPTION_INCOMPLETE": "Description 중간 서술이 도면에서 확인되지 않음",
    "DESC_BETWEEN_SYMBOL": "중간 심볼(SUCTION STRAINER)이 도면에 낱말로 없음 — 직접 입력",
    "DESC_CCW_DIRECTION": "CCW SUPPLY/RETURN 을 도면 기하로 구분할 수 없음 — 직접 입력",
    "DESC_GRADE_PARTIAL": "단위·계통·변수만 확정 — 중간 서술을 직접 입력",
    "DESC_GRADE_LOW": "후보에서 골랐으나 근거가 약함 — 확인 필요",
    "DESC_GRADE_NONE": "근거 없음 — 직접 입력",
    "IP_TOKEN_AS_ACTUATOR": "'I/P' 토큰을 액추에이터로 읽음 — 확인 필요",
    "ACTUATOR_LETTER_UNREAD": "액추에이터 외함은 찾았으나 문자를 읽지 못함",
    "ACTUATOR_ON_UNEXPECTED_BODY": "그 몸체 계열을 다루는 산출물이 없음 — 검출 확인",
    "UNLABELED_GLYPH_CLUSTER": "글리프 무리에 라벨이 없음",
    "MIXED_TAG_GLYPH_CLUSTER": "한 글리프 무리에 태그가 섞임",
    "ROW_DELETED": "사용자가 지운 행",
    "ORIGIN_REFERENCE_MISSING": "검증용 대조 리스트가 그 경로에 없음",
    "REVIEWER_MARKUP": "도면에 개정 표기가 있음 — 발주처 확인 대상",
}


def review_axis_map() -> dict:
    axes = pipeline.CFG.data.get("review_axes") or {}
    return {str(k).upper(): str(v).upper()
            for k, v in (axes.get("codes") or {}).items()}


def review_codes(row: dict) -> list:
    """The codes one row is flagged under, including the ones read off its grade.

    A grade is a review reason in its own right - `PARTIAL` means a person still
    has to write the middle of the sentence - but it is stored as a grade rather
    than as a code, so it is turned into one here instead of being duplicated
    into the engine's output.
    """
    ev = row.get("evidence") or {}
    out = list(ev.get("review_codes") or [])
    grade = (row.get("values") or {}).get("description_grade") or ""
    # The engine now raises `DESCRIPTION_INCOMPLETE` from the final grade, so the
    # screen no longer has to second-guess it; the grade code is the finer-grained
    # name for the same question and is what the panel groups on.
    if grade in ("PARTIAL", "LOW", "NONE"):
        code = f"DESC_GRADE_{grade}"
        if code not in out:
            out.append(code)
    out = [c for c in out if c != "DESCRIPTION_INCOMPLETE"]
    if row.get("deleted"):
        out.append("ROW_DELETED")
    return list(dict.fromkeys(out))


@app.patch("/jobs/{job_id}/rows/{key}/review/{code}")
def set_review(job_id: str, key: str, code: str, payload: dict):
    """Record what the reviewer decided about one flagged reason."""
    try:
        db.set_review_state(CON, job_id, key, code,
                            str(payload.get("state") or ""),
                            str(payload.get("note") or ""))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True}


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
    """Create a row a reviewer wants that the engine did not propose.

    When the reviewer also points at where it is on the drawing (`point`), the
    geometry around that spot is captured with the record - see
    `pipeline.probe_point`.  That is the whole reason this endpoint takes a
    coordinate: a missed item is only useful to a later rule pass if what was
    drawn there was written down at the time.
    """
    job = db.get_job(CON, job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    page_no = int(payload.get("page_no") or 0)
    values = payload.get("values") or {}
    key = db.add_row(CON, job_id, page_no,
                     payload.get("tab") or "FIELD",
                     payload.get("origin") or "",
                     payload.get("drawing_no") or "",
                     values)
    point = payload.get("point") or []
    geometry = {}
    if len(point) == 2 and page_no:
        geometry = pipeline.probe_point(Path(job["pdf_path"]), page_no,
                                        float(point[0]), float(point[1]))
    db.record_feedback(
        CON, job_id, "ADDED", row_key=key, page_no=page_no,
        drawing_no=payload.get("drawing_no") or "",
        rect=payload.get("rect") or point,
        user_value=json.dumps(values, ensure_ascii=False, sort_keys=True),
        reason=payload.get("reason") or "", geometry=geometry,
        pattern_args={"tab": payload.get("tab") or "FIELD",
                      "near": geometry.get("nearest_text", "")})
    return {"key": key, "review_count": db.review_count(CON, job_id),
            "feedback_count": db.feedback_count(CON, job_id),
            "geometry": {k: geometry.get(k) for k in
                         ("path_count", "segment_count", "nearest_text")}}


@app.post("/jobs/{job_id}/rows/{key}/copy")
def copy_row(job_id: str, key: str):
    try:
        new_key = db.copy_row(CON, job_id, key)
    except KeyError:
        raise HTTPException(404, "no such row")
    return {"key": new_key, "review_count": db.review_count(CON, job_id)}


@app.delete("/jobs/{job_id}/rows/{key}")
def delete_row(job_id: str, key: str, reason: str = ""):
    """Strike out a detection.  Records which rule produced it and on what."""
    before = db.get_row(CON, job_id, key)
    try:
        out = db.remove_row(CON, job_id, key)
    except KeyError:
        raise HTTPException(404, "no such row")
    if before is not None:
        ev = before.get("evidence") or {}
        rules = ev.get("rules_hit") or []
        db.record_feedback(
            CON, job_id, "REMOVED", row_key=key, page_no=before["page_no"],
            drawing_no=before.get("drawing_no") or "", rect=before.get("rect"),
            ai_value=json.dumps(before.get("ai") or {}, ensure_ascii=False,
                                sort_keys=True),
            reason=reason, basis=ev,
            pattern_args={"what": (before["values"].get("type")
                                   or ev.get("body") or ""),
                          "rule": (ev.get("excluded_by") or ev.get("anchor")
                                   or (rules[0] if rules else ""))})
    out["review_count"] = db.review_count(CON, job_id)
    out["feedback_count"] = db.feedback_count(CON, job_id)
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
    before = db.get_row(CON, job_id, key)
    try:
        user = db.set_user_value(CON, job_id, key, field, value)
    except KeyError:
        raise HTTPException(404, "no such row")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if before is not None:
        db.record_feedback(
            CON, job_id, "EDITED", row_key=key, page_no=before["page_no"],
            drawing_no=before.get("drawing_no") or "", rect=before.get("rect"),
            field=field, ai_value=(before.get("ai") or {}).get(field),
            user_value=value, reason=payload.get("reason") or "",
            basis=before.get("evidence") or {},
            pattern_args={"field": field,
                          "ai": (before.get("ai") or {}).get(field),
                          "user": value})
    return {"key": key, "user": user, "review_count": db.review_count(CON, job_id),
            "feedback_count": db.feedback_count(CON, job_id)}


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
    payload = payload or {}
    label = payload.get("label", "")
    origins = payload.get("origins") or list(db.ALL_ORIGINS)
    unknown = set(origins) - set(db.ALL_ORIGINS)
    if unknown:
        raise HTTPException(400, f"unknown origin(s): {sorted(unknown)}")
    drawings = payload.get("drawings")
    if drawings is not None:
        known = {d["drawing_no"] for d in db.drawings_of(CON, job_id)}
        unknown_d = set(drawings) - known
        if unknown_d:
            raise HTTPException(400, f"unknown drawing(s): {sorted(unknown_d)}")
        if not drawings:
            raise HTTPException(400, "no drawing selected, so nothing to deliver")
    hold = bool(payload.get("hold_review"))
    rev = db.snapshot(CON, job_id, label, origins, drawings, hold)
    snap = db.get_revision(CON, rev)
    # The workbook's REMARK column needs the codes and the axis they belong to,
    # and both are computed here rather than stored on the row, so they are
    # written into the frozen payload while it is being made.
    axis_of = review_axis_map()
    for row in snap["rows"]:
        row["review_codes"] = review_codes(row)
        row["review_axis"] = {c: axis_of.get(c, "OTHER") for c in row["review_codes"]}
        row["review_label"] = {c: REVIEW_LABELS.get(c, c) for c in row["review_codes"]}
    db.replace_revision(CON, rev, snap)
    return {"revision_id": rev, "origins": origins,
            "drawings": snap["drawings_included"],
            "review_held_back": hold,
            "rows": len(snap["rows"]),
            "review_count": db.review_count(CON, job_id)}


@app.get("/jobs/{job_id}/feedback")
def job_feedback(job_id: str, limit: int = 200):
    """The correction history.  Stored, counted, and not interpreted."""
    if db.get_job(CON, job_id) is None:
        raise HTTPException(404, "no such job")
    return {"count": db.feedback_count(CON, job_id),
            "records": db.feedback_rows(CON, job_id, limit)}


@app.get("/jobs/{job_id}/drawings")
def job_drawings(job_id: str):
    """Drawings in this job with their row and review counts, grouped by system."""
    if db.get_job(CON, job_id) is None:
        raise HTTPException(404, "no such job")
    return db.drawings_of(CON, job_id)


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

# Output forms found beside the project, used when none has been uploaded.  The
# repository does not carry these - `data/*.xlsx` is gitignored - so on a fresh
# clone every deliverable starts out with no template and says so.  An *empty*
# form is enough: only the layout is read, and the data area is rewritten.
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
