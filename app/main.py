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
import re
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

from app import (audit, axis_overrides, db, excel_out, paths, pipeline,  # noqa: E402
                 revisions, version)
from app.pipeline import CFG                              # noqa: E402

# Two roots, and the difference matters once this is an exe: `paths.resource()`
# is inside the bundle and is deleted when the process ends, `paths.data_dir()`
# is the folder beside the exe that the user keeps.  See app/paths.py.
DATA_DIR = paths.data_dir()
UPLOADS = DATA_DIR / "uploads"
OUTPUTS = DATA_DIR / "outputs"
DB_PATH = DATA_DIR / "app.db"
STATIC = paths.resource("app", "static")

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


# What the screen says when an analysis fails.  Deliberately short: this list may
# only grow from causes that were measured on a real file that failed.
_FAILED_GENERIC = ("이 PDF 를 분석하지 못했습니다. 사유를 특정하지 못했습니다.")


def _count_pages(pdf: Path) -> int:
    """How many pages this PDF has, read from the file.  0 means "not readable".

    Measured on the 19 MB / 58-sheet set this tool was built against: 2.1-2.9 ms.
    That is why it happens on the upload request rather than being guessed from
    the file size - a page count shown to a person has to be the document's own.
    """
    import pymupdf                      # local, like the page renderer's import
    try:
        doc = pymupdf.open(pdf)
        n = doc.page_count
        doc.close()
        return int(n)
    except Exception:                                # noqa: BLE001
        return 0


def _failure_reason(pdf: Path) -> str:
    """A sentence built from what the file contains, not from the exception.

    A message derived from the exception is the exception, reworded - which is
    what the failure screen used to show.  So this ignores the exception entirely
    and re-opens the PDF read-only to count two things that a person can act on:
    how many pages it has, and whether any of them carry text at all.  When
    neither says anything definite the generic sentence is used; a plausible
    cause is never invented.
    """
    import pymupdf                      # local, like the page renderer's import
    try:
        doc = pymupdf.open(pdf)
        pages = doc.page_count
        # Twenty pages is enough to answer "does this document have text";
        # reading all of a 58-sheet set to say so would make a failed upload slow.
        looked = min(pages, 20)
        words = sum(len(doc[i].get_text("words")) for i in range(looked))
        doc.close()
    except Exception:                                # noqa: BLE001
        return "이 파일을 PDF 로 열지 못했습니다. 파일이 손상되었을 수 있습니다."
    if pages == 0:
        return "이 PDF 에는 쪽이 하나도 없습니다."
    if words == 0:
        return ("이 PDF 에는 읽을 수 있는 글자가 없습니다 — 스캔 이미지이거나 "
                "빈 문서로 보입니다. 이 도구는 글자가 들어 있는 벡터 PDF 만 읽습니다.")
    return _FAILED_GENERIC


def _plan(row):
    """저장된 장수 계획.  없으면 None - "아직 안 정해졌다"이지 "없다"가 아니다."""
    try:
        raw = row["sheet_plan"]
    except (KeyError, IndexError):
        return None
    return json.loads(raw) if raw else None


def _elapsed(row) -> float:
    """Seconds the analysis took, or 0 when it has not finished one yet."""
    try:
        a, b = row["started_at"], row["finished_at"]
    except (KeyError, IndexError):
        return 0.0
    return round(b - a, 1) if a and b and b >= a else 0.0


def _worker() -> None:
    while True:
        job_id = _JOBS.get()
        row = db.get_job(CON, job_id)
        if row is None:
            continue
        try:
            db.mark_started(CON, job_id)
            db.set_progress(CON, job_id, 0.0, "starting", sheets=(0, 0))
            _emit(job_id, {"progress": 0.0, "message": "starting",
                           "status": "running", "sheets_done": 0,
                           "sheets_total": 0})

            def progress(done, total, message, sheets=None, plan=None):
                frac = done / max(total, 1)
                db.set_progress(CON, job_id, frac, message, sheets=sheets)
                out = {"progress": frac, "message": message, "status": "running"}
                if sheets is not None:
                    out["sheets_done"], out["sheets_total"] = sheets
                if plan is not None:
                    db.set_sheet_plan(CON, job_id, plan)
                    out["sheet_plan"] = plan
                _emit(job_id, out)

            result = pipeline.analyse(Path(row["pdf_path"]), progress=progress,
                                      reference=VERIFY_AGAINST)
            result["fingerprint"] = pipeline.fingerprint(result)
            summary = db.store_result(CON, job_id, result)
            # 프로젝트에 묶인 분석이면 여기서 바로 대조한다.  묶이지 않았으면
            # 예전과 똑같이 동작한다 - 리비전은 얹는 것이지 대체하는 것이 아니다.
            try:
                summary["revision"] = _run_comparison(job_id)
            except Exception as exc:                 # noqa: BLE001
                traceback.print_exc()
                summary["revision"] = {"error": str(exc)}
            db.mark_finished(CON, job_id)
            fin = db.get_job(CON, job_id)
            _emit(job_id, {"progress": 1.0, "message": "done", "status": "done",
                           "summary": summary,
                           "sheet_plan": _plan(fin),
                           "page_count": fin["page_count"],
                           "sheets_done": fin["sheets_done"],
                           "sheets_total": fin["sheets_total"],
                           "elapsed_s": _elapsed(fin)})
        except Exception as exc:                     # noqa: BLE001
            # The original goes to the log untouched, and to `error_detail` for
            # the diagnostic export.  What reaches the screen is a sentence a
            # person can act on - never the exception, reworded.
            traceback.print_exc()
            detail = traceback.format_exc()
            reason = _failure_reason(Path(row["pdf_path"]))
            db.set_progress(CON, job_id, 0.0, reason, "failed", error_detail=detail)
            db.mark_finished(CON, job_id)
            fin = db.get_job(CON, job_id)
            # 어디까지 갔는지.  진행률은 0 으로 떨어뜨리지만 장수는 남긴다 -
            # "몇 장째에서 멈췄나" 가 사용자가 확인할 수 있는 유일한 단서다.
            _emit(job_id, {"progress": 0.0, "status": "failed",
                           "message": reason,
                           "sheet_plan": _plan(fin),
                           "page_count": fin["page_count"],
                           "sheets_done": fin["sheets_done"],
                           "sheets_total": fin["sheets_total"],
                           "elapsed_s": _elapsed(fin)})
        finally:
            _JOBS.task_done()


threading.Thread(target=_worker, daemon=True).start()


# --------------------------------------------------------------------------
# Upload and analysis
# --------------------------------------------------------------------------

@app.post("/jobs")
async def create_job(pdf: UploadFile = File(...), project: str = Form(""),
                     compared_with: str = Form("")):
    """PDF 하나를 받는다.  `project` 가 오면 그 프로젝트의 다음 리비전이 된다.

    프로젝트 없이 올려도 예전과 똑같이 동작한다 - 리비전은 기존 흐름 위에
    얹히는 것이지 그것을 대체하지 않는다.
    """
    raw = await pdf.read()
    if not raw[:5] == b"%PDF-":
        raise HTTPException(400, "that file is not a PDF")
    revision = ""
    if project:
        try:
            meta = revisions.load_project(DATA_DIR, project)
        except (KeyError, ValueError):
            raise HTTPException(404, f"프로젝트 '{project}' 가 없습니다")
        revision = revisions.next_revision(meta)
        choices = revisions.compare_choices(meta)
        if compared_with and compared_with not in choices:
            raise HTTPException(400, f"비교 대상 '{compared_with}' 는 이 프로젝트에 "
                                     f"없습니다 (있는 것: {choices})")
        if not compared_with:
            compared_with = revisions.default_compare_target(meta)
    sha = hashlib.sha256(raw).hexdigest()
    job_id = uuid.uuid4().hex[:12]
    UPLOADS.mkdir(parents=True, exist_ok=True)
    path = UPLOADS / f"{job_id}_{Path(pdf.filename).name}"
    path.write_bytes(raw)
    db.create_job(CON, job_id, Path(pdf.filename).name, sha, path)
    pages = _count_pages(path)
    db.set_page_count(CON, job_id, pages)
    if project:
        db.set_job_revision(CON, job_id, project, revision, compared_with)
    _JOBS.put(job_id)
    return {"job_id": job_id, "pdf_name": Path(pdf.filename).name, "sha256": sha,
            "project": project, "revision": revision,
            "compared_with": compared_with, "page_count": pages}


@app.post("/jobs/{job_id}/reanalyse")
def reanalyse(job_id: str):
    """Re-run the engine, keeping every reviewer edit."""
    if db.get_job(CON, job_id) is None:
        raise HTTPException(404, "no such job")
    db.set_progress(CON, job_id, 0.0, "queued", "queued", sheets=(0, 0))
    _JOBS.put(job_id)
    return {"job_id": job_id, "queued": True}


def _job_public(row) -> dict:
    """A job as the browser may see it: everything except the raw traceback.

    `error_detail` stays server-side.  Not rendering it would be enough to keep it
    off the screen, but it would still be in the response, one devtools tab away
    from being read as the answer - and the point of the message column is that
    the answer is the sentence, not the traceback.  It travels in the diagnostic
    export instead, which is what a developer asks for by name.
    """
    out = dict(row)
    out.pop("error_detail", None)
    # 걸린 시간은 두 시각의 차이지 별도 사실이 아니므로 여기서 만든다.
    out["elapsed_s"] = _elapsed(row)
    out["sheet_plan"] = _plan(row)
    out.pop("sheet_plan_json", None)
    return out


# --------------------------------------------------------------------------
# 프로젝트와 리비전
# --------------------------------------------------------------------------

def _run_comparison(job_id: str) -> dict:
    """이 분석을 그 프로젝트의 장부와 맞춘다.  프로젝트가 없으면 아무것도 안 한다."""
    job = db.get_job(CON, job_id)
    if job is None or not job["project"]:
        return {}
    name, revision = job["project"], job["revision"]
    compared = job["compared_with"] or ""
    reg_path = revisions.project_dir(DATA_DIR, name) / "id_registry.json"
    registry = revisions.Registry.load(reg_path)
    # 대조가 보는 것은 검토자가 보는 값이다 - 엔진 값에 편집이 얹힌 뒤.
    rows = [dict(r["values"], key=r["key"], tab=r["tab"],
                 drawing_no=r["drawing_no"], page_no=r["page_no"], rect=r["rect"])
            for r in db.merged_rows(CON, job_id, "ALL") if not r["removed"]]
    result = revisions.compare(rows, registry, revision, compared_with=compared)
    # 산출물의 NO 도 ID 와 같은 원리로 단조 증가한다.  ID 부여는 도면 단위
    # 좌표순이고 NO 는 산출물 단위 순서이므로, 번호는 따로 한 번 더 매긴다.
    for r in rows:
        st = result["states"].get(r["key"])
        if st:
            r["stable_id"] = st["id"]
    numbers = revisions.assign_excel_numbers(rows, registry)
    for key, st in result["states"].items():
        st["excel_no"] = numbers.get(key, 0)
    registry.save(reg_path)
    db.store_revision_result(CON, job_id, result)
    # ④ 행의 FROM/TO 확정 승계 - 같은 안정 ID 가 매칭되면 Rev.A 의 확정 문장을
    # 잇는다.  ID 가 안 물리면 승계하지 않고, 이 리비전에서 사람이 이미 고친
    # 행도 덮지 않는다 (axis_overrides.inherit 의 규칙).
    ov_path = axis_overrides.path_for(DATA_DIR, name)
    overrides = axis_overrides.load(ov_path)
    if overrides:
        rows_by_key = {r["key"]: r for r in db.merged_rows(CON, job_id, "ALL")}
        for key, ov in axis_overrides.inherit(
                overrides, result["states"], rows_by_key, job_id):
            db.set_user_value(CON, job_id, key, "description", ov["sentence"])
            db.set_user_value(CON, job_id, key, "description_grade",
                              "USER_ENTERED")
    entry = revisions.record_revision(
        DATA_DIR, name, revision, job_id=job_id, pdf_name=job["pdf_name"],
        compared_with=compared, result=result)
    return {"project": name, "revision": revision, "compared_with": compared,
            "label": entry["label"], "counts": result["counts"],
            "radii": result["radii"]}


@app.get("/projects")
def list_projects():
    return revisions.list_projects(DATA_DIR)


@app.post("/projects")
def create_project(name: str = Form(...)):
    """Rev.A 를 여는 자리.  같은 이름이 있으면 덮어쓰지 않고 거절한다."""
    try:
        meta = revisions.create_project(DATA_DIR, name)
    except FileExistsError:
        raise HTTPException(409, f"'{name}' 프로젝트가 이미 있습니다. "
                                 f"덮어쓰지 않습니다 - 다른 이름을 쓰거나 "
                                 f"그 프로젝트를 골라 다음 리비전으로 올리세요.")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return _project_public(meta)


def _project_public(meta: dict) -> dict:
    """화면이 필요한 것: 다음 리비전 이름과 고를 수 있는 비교 대상."""
    return {**meta,
            "next_revision": revisions.next_revision(meta),
            "compare_choices": revisions.compare_choices(meta),
            "default_compare": revisions.default_compare_target(meta)}


@app.get("/projects/{name}")
def get_project(name: str):
    try:
        return _project_public(revisions.load_project(DATA_DIR, name))
    except (KeyError, ValueError):
        raise HTTPException(404, f"프로젝트 '{name}' 가 없습니다")


@app.post("/jobs/{job_id}/revision")
def set_revision(job_id: str, project: str = Form(...),
                 compared_with: str = Form("")):
    """이미 분석된 결과를 프로젝트의 다음 리비전으로 얹고 바로 대조한다.

    비교 대상을 바꿔 다시 보고 싶을 때도 여기로 온다 - 재분석 없이 대조만
    다시 한다.  같은 job 을 다시 대조하면 이전 대조 결과는 갈아 끼워진다.
    """
    job = db.get_job(CON, job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    try:
        meta = revisions.load_project(DATA_DIR, project)
    except (KeyError, ValueError):
        raise HTTPException(404, f"프로젝트 '{project}' 가 없습니다")
    existing = [r for r in meta.get("revisions") or [] if r["job_id"] == job_id]
    revision = existing[0]["revision"] if existing else revisions.next_revision(meta)
    choices = [r for r in revisions.compare_choices(meta) if r != revision]
    if compared_with and compared_with not in choices:
        raise HTTPException(400, f"비교 대상 '{compared_with}' 는 이 프로젝트에 "
                                 f"없습니다 (있는 것: {choices})")
    if not compared_with and choices:
        compared_with = choices[-1]
    db.set_job_revision(CON, job_id, project, revision, compared_with)
    return _run_comparison(job_id)


@app.get("/jobs/{job_id}/revision")
def job_revision(job_id: str):
    """이 분석이 어느 리비전이고 무엇과 비교했는지, 그리고 삭제 후보."""
    job = db.get_job(CON, job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    cands = db.deleted_candidates(CON, job_id)
    states = db.revision_states(CON, job_id)
    counts = {}
    for st in states.values():
        counts[st["state"]] = counts.get(st["state"], 0) + 1
    counts[revisions.DELETED_CANDIDATE] = sum(1 for c in cands if not c["confirmed"])
    counts[revisions.DELETED] = sum(1 for c in cands if c["confirmed"])
    label = (f"{job['revision']} vs {job['compared_with']}"
             if job["compared_with"] else
             (f"{job['revision']} (비교 대상 없음)" if job["revision"] else ""))
    return {"project": job["project"], "revision": job["revision"],
            "compared_with": job["compared_with"], "label": label,
            "counts": counts, "deleted_candidates": cands}


@app.post("/jobs/{job_id}/deleted/{stable_id}/confirm")
def confirm_deleted(job_id: str, stable_id: str, confirmed: bool = True):
    """삭제 후보를 사람이 확정한다.  확정 전에는 Excel 에 삭제 표기가 안 나간다."""
    try:
        return db.confirm_deleted(CON, job_id, stable_id, confirmed)
    except KeyError:
        raise HTTPException(404, "그런 삭제 후보가 없습니다")


@app.get("/audit")
def audit_now():
    """세기만 한다.  아무것도 지우지 않는다 - `docs/db_hygiene.md` (가)."""
    return audit.run(CON, DATA_DIR)


@app.get("/jobs")
def jobs():
    return [_job_public(r) for r in db.list_jobs(CON)]


@app.get("/jobs/{job_id}")
def job(job_id: str):
    row = db.get_job(CON, job_id)
    if row is None:
        raise HTTPException(404, "no such job")
    out = _job_public(row)
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
                        "status": row["status"],
                        "page_count": row["page_count"],
                        "sheets_done": row["sheets_done"],
                        "sheets_total": row["sheets_total"],
                        "sheet_plan": _plan(row),
                        "elapsed_s": _elapsed(row)})
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
    rev = db.revision_states(CON, job_id)
    for row in out:
        row["review_codes"] = review_codes(row)
        row["review_state"] = states.get(row["key"], {})
        row["rev"] = rev.get(row["key"], {})
        # 화면에 보이는 TYPE 표기.  규칙은 서버에만 두고 화면은 결과만 읽는다
        # (`pipeline.type_display` — 판정값 `values["type"]` 은 불변).
        row["type_display"] = pipeline.type_display(row["values"],
                                                    row.get("evidence"))
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
# ④ 행의 FROM/TO 사용자 확정 (6회차)
# --------------------------------------------------------------------------
# 자동 추적의 세 실측(13.1% · 4.9% · 10.4%)이 막은 자리를 사람이 확정한다.
# 후보는 그 도면에서 이미 읽은 텍스트뿐이고(커넥터 문구 · 기기 라벨 · 도면
# 텍스트), 확정 전에는 현행 문장이 그대로 남는다.

_AXIS_PAGES: dict = {}          # job_id -> {page_no: PageCache}.  최근 1개 job 만.


def _axis_page(job, page_no: int):
    import pidcache
    jid = job["id"]
    if jid not in _AXIS_PAGES:
        _AXIS_PAGES.clear()          # 한 번에 한 job 이면 충분하다 - 화면도 그렇다
        doc, pages = pidcache.load_pages(job["pdf_path"])
        _AXIS_PAGES[jid] = {p.page_no: p for p in pages}
    return _AXIS_PAGES[jid].get(page_no)


# 도면 텍스트 층에서 거르는 것 — **이미 측정된 제거 패턴의 재사용**이다.
# `describe_equipment` 가 기기 라벨에서 떼는 것과 같은 것들(도면번호 · DN 치수 ·
# 그리드 셀 · NOTE 참조)이고, 여기에 이 페이지에서 실제로 본 두 가지를 더한다:
# 점선 리더(`.....`)와 심볼 글자(`PT PT` · `TT TT TT` — 버블 안의 ISA 문자).
# 거르기만 하고 아무것도 만들지 않는다: p6 은 38건 중 잡음을 뺀 나머지가 남고
# `HP TURBINE IP TURBINE` · `LP TURBINE` · `HRSG` · `STG#10` 은 그대로 남는다.
_AXIS_DIMENSION_IN = re.compile(r"\b\d{2,4}\s*[Xx]\s*\d{2,4}\b")
_AXIS_CODE_IN = re.compile(r"\b(ASME|ANSI|API|B31(\.\d+)?|SEC\.?\s?[IVX]+)\b")


def _axis_text_noise(text: str) -> bool:
    import describe_equipment as dequip
    t = " ".join(str(text or "").split())
    if not t:
        return True
    if dequip.DRAWING_NO.search(t) or dequip.NOTE_REF.search(t):
        return True
    # 패턴에 걸리는 부분을 떼어낸 뒤 남는 낱말로 판정한다 - `DN 50` 처럼 띄어
    # 쓴 형태도 그래야 걸린다.  남은 낱말이 전부 점선이거나 두 글자 이하
    # 알파벳(버블 안 ISA 글자)이면 이름이 아니다.  세 글자부터는 남긴다:
    # 이 문서의 `CEP` · `SCT` · `MOV` 가 그 길이의 실제 이름이다.
    for pat in (dequip.BORE, dequip.GRID_CELL, _AXIS_DIMENSION_IN, _AXIS_CODE_IN):
        t = pat.sub(" ", t)
    words = [w for w in t.split() if any(ch.isalnum() for ch in w)]
    if not words:
        return True
    return all(w.isalpha() and len(w) <= 2 for w in words)


def _axis_candidates(job, page_no: int) -> dict:
    """그 페이지에서 이미 읽은 텍스트 세 층.  없는 것을 만들지 않는다."""
    import describe_candidates as dcand
    pc = _axis_page(job, page_no)
    if pc is None:
        return {"connectors": [], "equipment": [], "texts": []}
    area = CFG.rect("regions.drawing_area")
    conns = sorted({t.strip() for _r, t in dcand._connector_lines(pc, area)})
    conn_set = set(conns)
    seen_texts = sorted({t.strip() for _r, t in dcand._line_text(pc, area)
                         if t.strip() and t.strip() not in conn_set})
    # 거른 것도 버리지 않고 따로 돌려준다 - 필터가 삼킨 후보를 볼 탈출구다.
    # p6 의 `HP TURBINE IP TURBINE` 처럼 정답이 덩어리로 인쇄되는 일이 있고,
    # 그런 덩어리가 언젠가 필터에 걸릴 수 있다.  화면의 "전체 후보 보기" 가
    # 이 목록을 펼친다.
    texts = [t for t in seen_texts if not _axis_text_noise(t)]
    hidden = [t for t in seen_texts if _axis_text_noise(t)]
    equip = set()
    for r in db.merged_rows(CON, job["id"], "ALL"):
        if r["page_no"] != page_no:
            continue
        ev = r.get("evidence") or {}
        for c in ev.get("candidates") or []:
            if c.get("kind") == "EQUIPMENT" and c.get("text"):
                equip.add(str(c["text"]).strip())
        ax = ev.get("axis") or {}
        for e in (ax.get("ev") or {}).get("ends") or []:
            if e and e.get("kind") == "EQUIP" and e.get("name"):
                equip.add(str(e["name"]).strip())
        if ax.get("equip"):
            equip.add(str(ax["equip"]).strip())
    return {"connectors": conns, "equipment": sorted(equip), "texts": texts,
            "texts_filtered": hidden}


def _axis_same_run(job_id: str, row: dict) -> list:
    """같은 런으로 판정된 다른 ④ 행 — 일괄 '제안' 대상.  런 판정 자체가 실패한
    행(run 없음)은 제안하지 않는다."""
    run = ((row.get("evidence") or {}).get("axis") or {}).get("ev", {}).get("run")
    if not run:
        return []
    out = []
    for r in db.merged_rows(CON, job_id, "ALL"):
        if (r["key"] == row["key"] or r["page_no"] != row["page_no"]
                or r.get("deleted") or r.get("removed")):
            continue
        ax = (r.get("evidence") or {}).get("axis") or {}
        if ax.get("axis") != "④" or (ax.get("ev") or {}).get("run") != run:
            continue
        if (r.get("user") or {}).get("description"):
            continue
        out.append({"key": r["key"], "type": r["values"].get("type")
                    or r["values"].get("valve_type") or "",
                    "description": r["values"].get("description") or ""})
    return out


@app.get("/jobs/{job_id}/rows/{key}/axis_candidates")
def axis_candidates(job_id: str, key: str):
    job = db.get_job(CON, job_id)
    row = db.get_row(CON, job_id, key)
    if job is None or row is None:
        raise HTTPException(404, "no such row")
    out = _axis_candidates(job, row["page_no"])
    out["same_run"] = _axis_same_run(job_id, row)
    return out


@app.get("/jobs/{job_id}/axis_overrides")
def axis_override_map(job_id: str):
    """이 job 의 행들에 걸린 확정 — {row_key: entry+inherited}.  근거 패널이
    "FROM/TO 확정"과 "Rev.A 확정 승계"를 이걸로 그린다."""
    job = db.get_job(CON, job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    if not job["project"]:
        return {}
    data = axis_overrides.load(
        axis_overrides.path_for(DATA_DIR, job["project"]))
    states = db.revision_states(CON, job_id)
    out = {}
    for key, st in states.items():
        entry = data.get(st.get("id") or "")
        if entry:
            out[key] = dict(entry, stable_id=st["id"],
                            inherited=entry.get("origin_job") != job_id)
    return out


@app.post("/jobs/{job_id}/rows/{key}/axis")
async def confirm_axis(job_id: str, key: str, payload: dict):
    """FROM/TO 확정 → ② 문형 생성 → user_values 저장 (+프로젝트 장부).

    빈 from/to 는 확정 해제다: 편집을 걷어내 현행(엔진) 문장으로 되돌린다.
    """
    job = db.get_job(CON, job_id)
    row = db.get_row(CON, job_id, key)
    if job is None or row is None:
        raise HTTPException(404, "no such row")
    states = db.revision_states(CON, job_id)
    stable_id = (states.get(key) or {}).get("id") or ""
    from_text = str(payload.get("from_text") or "").strip()
    to_text = str(payload.get("to_text") or "").strip()

    if not from_text and not to_text:
        db.set_user_value(CON, job_id, key, "description", None)
        db.set_user_value(CON, job_id, key, "description_grade", None)
        if stable_id and job["project"]:
            axis_overrides.clear(
                axis_overrides.path_for(DATA_DIR, job["project"]), stable_id)
        return {"cleared": True,
                "review_count": db.review_count(CON, job_id)}
    if not from_text or not to_text:
        raise HTTPException(400, "FROM 과 TO 를 모두 고르거나 둘 다 비우세요")

    cands = _axis_candidates(job, row["page_no"])
    # 출처 판정에는 걸러낸 텍스트까지 넣는다 - 토글로 고른 것도 도면이 인쇄한
    # 문구이므로 `자유입력` 이라고 적으면 사실이 아니다.
    pool = (cands["connectors"] + cands["equipment"] + cands["texts"]
            + cands.get("texts_filtered", []))
    source_from = axis_overrides.classify_source(from_text, pool)
    source_to = axis_overrides.classify_source(to_text, pool)
    type_ = (row["values"].get("type")
             or row["values"].get("valve_type") or "")

    # Suffix - 기존 규칙 그대로: 같은 페이지 · 같은 TYPE · 같은 (from, to) 가
    # 2행 이상일 때 위→아래 · 왼→오.  묶음은 이 확정과 같은 값의 기존 확정들.
    _d, src = pipeline.daxis._strip_conn(from_text)
    _d, dst = pipeline.daxis._strip_conn(to_text)
    group = [(key, tuple(row["rect"] or (0, 0, 0, 0)))]
    ovmap = {}
    if job["project"]:
        ovmap = axis_overrides.load(
            axis_overrides.path_for(DATA_DIR, job["project"]))
    ids_here = {k: (st.get("id") or "") for k, st in states.items()}
    for r in db.merged_rows(CON, job_id, "ALL"):
        if r["key"] == key or r["page_no"] != row["page_no"]:
            continue
        rt = r["values"].get("type") or r["values"].get("valve_type") or ""
        if rt != type_:
            continue
        e = ovmap.get(ids_here.get(r["key"], ""))
        if e:
            _d, es = pipeline.daxis._strip_conn(e.get("from", ""))
            _d, ed = pipeline.daxis._strip_conn(e.get("to", ""))
            if (es, ed) == (src, dst):
                group.append((r["key"], tuple(r["rect"] or (0, 0, 0, 0))))
            continue
        ax = (r.get("evidence") or {}).get("axis") or {}
        if (ax.get("axis") == "②" and ax.get("src") == src
                and ax.get("dst") == dst):
            group.append((r["key"], tuple(r["rect"] or (0, 0, 0, 0))))
    suffix = axis_overrides.suffix_for(group, key)
    sentence = axis_overrides.sentence_for(from_text, to_text, type_, suffix)

    before = db.get_row(CON, job_id, key)
    db.set_user_value(CON, job_id, key, "description", sentence)
    db.set_user_value(CON, job_id, key, "description_grade", "USER_ENTERED")
    db.record_feedback(
        CON, job_id, "EDITED", row_key=key, page_no=row["page_no"],
        drawing_no=row.get("drawing_no") or "", rect=row.get("rect"),
        field="description",
        ai_value=(before.get("ai") or {}).get("description"),
        user_value=sentence,
        reason=f"판정축 FROM/TO 확정 — FROM {source_from} · TO {source_to}",
        basis={"from": from_text, "to": to_text},
        pattern_args={"field": "description",
                      "ai": (before.get("ai") or {}).get("description"),
                      "user": sentence})
    saved = False
    if stable_id and job["project"]:
        axis_overrides.record(
            axis_overrides.path_for(DATA_DIR, job["project"]), stable_id,
            from_text=from_text, to_text=to_text, source_from=source_from,
            source_to=source_to, type_=type_, sentence=sentence,
            origin_job=job_id)
        saved = True
    return {"sentence": sentence, "suffix": suffix,
            "source_from": source_from, "source_to": source_to,
            "stable_id": stable_id, "saved_to_project": saved,
            "suggestions": _axis_same_run(job_id, row),
            "review_count": db.review_count(CON, job_id)}


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


# --------------------------------------------------------------------------
# Error reports
# --------------------------------------------------------------------------
#
# The reviewer is asked for two things and no more: which axis is wrong, and one
# line saying why or what the right value is.  Everything else that makes the
# report actionable - where the row is, what the engine decided, which rules it
# hit, what the reviewer had already changed - is gathered here, because it is
# all on the server already and re-typing it is how a report stops being filed.

REPORT_WHAT_LABELS = {
    "SCOPE": "Scope 판정",
    "QTY": "Q'ty",
    "TYPE": "Type / Valve Type",
    "DESCRIPTION": "Description",
    "OTHER": "기타",
}


def _capture_row(job_id: str, key: str) -> dict:
    """Everything the engine has to say about one row, as it stands right now."""
    row = db.get_row(CON, job_id, key)
    if row is None:
        return {}
    ev = row.get("evidence") or {}
    vals = row.get("values") or {}
    return {
        "identity": {
            "row_key": key, "tab": row.get("tab"), "page_no": row.get("page_no"),
            "drawing_no": row.get("drawing_no"), "rect": row.get("rect"),
            "type": vals.get("type"), "valve_type": vals.get("valve_type"),
            "tag_no": vals.get("tag_no"), "origin": row.get("origin"),
        },
        "ai_values": row.get("ai") or {},
        "user_values": {k: v for k, v in (row.get("user") or {}).items()
                        if v is not None},
        "evidence": ev,
        "applied_rules": list(ev.get("rules_hit") or []),
        "review_codes": review_codes(row),
        "review_state": db.review_states(CON, job_id).get(key, {}),
        "needs_review": row.get("needs_review") or "",
        "annotation": row.get("annotation") or "",
        "flags": {"deleted": row.get("deleted"), "added": row.get("added"),
                  "removed": row.get("removed")},
    }


def _capture_point(job_id: str, page_no: int, point) -> dict:
    """What is drawn where the reviewer says something was missed.

    The same probe the '＋행' flow already uses, so an undetected position is
    recorded in the one shape a later rule pass can read.
    """
    job = db.get_job(CON, job_id)
    if job is None or not page_no or len(point or []) != 2:
        return {}
    return {"point": [float(point[0]), float(point[1])],
            "geometry": pipeline.probe_point(Path(job["pdf_path"]), page_no,
                                             float(point[0]), float(point[1]))}


def _capture_context(job_id: str) -> dict:
    job = db.get_job(CON, job_id)
    engine = json.loads(job["engine_json"] or "{}") if job else {}
    return {
        "job_id": job_id,
        "pdf_name": job["pdf_name"] if job else "",
        "pdf_sha256": job["pdf_sha256"] if job else "",
        "fingerprint": job["fingerprint"] if job else "",
        "layout": engine.get("applied_rules", {}).get("layout", {}),
        "build": version.info(),
    }


@app.post("/jobs/{job_id}/reports")
def create_report(job_id: str, payload: dict):
    """File one report.  `what` and `detail` are the person's; the rest is taken."""
    if db.get_job(CON, job_id) is None:
        raise HTTPException(404, "no such job")
    kind = str(payload.get("kind") or "ROW").upper()
    what = str(payload.get("what") or "").upper()
    detail = str(payload.get("detail") or "").strip()
    key = str(payload.get("row_key") or "")
    page_no = int(payload.get("page_no") or 0) or None
    capture = dict(_capture_context(job_id))
    if key:
        capture["row"] = _capture_row(job_id, key)
        ident = capture["row"].get("identity") or {}
        page_no = page_no or ident.get("page_no")
    point = payload.get("point") or []
    if point:
        capture["missed"] = _capture_point(job_id, page_no or 0, point)
    rect = payload.get("rect") or (capture.get("row", {})
                                   .get("identity", {}).get("rect")) or point
    drawing_no = str(payload.get("drawing_no")
                     or (capture.get("row", {}).get("identity", {})
                         .get("drawing_no") or ""))
    if not drawing_no and page_no:
        # A report about a place rather than a row still belongs to a drawing,
        # and the sheet knows its own number - asking the reporter for it would
        # be the third question this dialog is not allowed to ask.
        found = CON.execute(
            "SELECT drawing_no FROM pid_page WHERE job_id=? AND page_no=?",
            (job_id, page_no)).fetchone()
        drawing_no = (found["drawing_no"] or "") if found else ""
    try:
        rid = db.add_report(CON, job_id, kind, what, detail, row_key=key,
                            page_no=page_no, drawing_no=drawing_no, rect=rect,
                            capture=capture)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"id": rid, "report_count": db.report_count(CON, job_id)}


@app.get("/jobs/{job_id}/reports")
def job_reports(job_id: str):
    if db.get_job(CON, job_id) is None:
        raise HTTPException(404, "no such job")
    return {"count": db.report_count(CON, job_id),
            "labels": REPORT_WHAT_LABELS,
            "reports": db.list_reports(CON, job_id)}


@app.patch("/reports/{report_id}")
def edit_report(report_id: int, payload: dict):
    try:
        out = db.update_report(
            CON, report_id,
            what=(str(payload["what"]).upper() if "what" in payload else None),
            detail=(str(payload["detail"]) if "detail" in payload else None))
    except KeyError:
        raise HTTPException(404, "no such report")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return out


@app.delete("/reports/{report_id}")
def remove_report(report_id: int):
    try:
        db.delete_report(CON, report_id)
    except KeyError:
        raise HTTPException(404, "no such report")
    return {"ok": True}


@app.get("/version")
def build_version():
    return version.info()


# --------------------------------------------------------------------------
# Diagnostic export
# --------------------------------------------------------------------------
#
# One button, one file, and a fixed answer to "what is in it".
#
# What goes in is everything needed to work out why this machine decided what it
# decided: the reports, the analysis as stored, the reviewer's edits, the
# correction history, the rules that were in force and - the part that only a
# remote run can supply - the layout values *derived from that PC's own PDF*.
# Two things stay out on purpose and are named in the manifest so their absence
# is visible rather than assumed: the drawing PDF and the client's workbook.
# Neither is ours to move, and neither is needed to read the decisions.

DIAGNOSTICS = DATA_DIR / "diagnostics"
DIAGNOSTIC_EXCLUDED = [
    "도면 원본 PDF (파일명과 SHA-256 만 기록)",
    "발주처 양식·리스트 원본 (.xlsx)",
]


def _log_tail(limit: int = 2_000_000) -> bytes:
    """The server log, newest end first if it is long.  Missing is not an error."""
    log = paths.log_path()
    if not log.exists():
        return b"(logs/server.log is not on this machine)\n"
    raw = log.read_bytes()
    if len(raw) <= limit:
        return raw
    return (f"(truncated: last {limit} of {len(raw)} bytes)\n"
            .encode("utf-8") + raw[-limit:])


def _diagnostic_zip(job_id: str) -> dict:
    job = db.get_job(CON, job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    info = version.info()
    engine = json.loads(job["engine_json"] or "{}")
    applied = engine.get("applied_rules") or {}
    layout = applied.get("layout") or {}
    rows = db.merged_rows(CON, job_id, "ALL")
    states = db.review_states(CON, job_id)
    for row in rows:
        row["review_codes"] = review_codes(row)
    edits = [{"key": r["key"], "page_no": r["page_no"],
              "drawing_no": r["drawing_no"],
              "user": {k: v for k, v in (r["user"] or {}).items() if v is not None},
              "ai": r["ai"], "review_state": states.get(r["key"], {}),
              "added": r["added"], "removed": r["removed"]}
             for r in rows
             if any(v is not None for v in (r["user"] or {}).values())
             or r["added"] or r["removed"] or states.get(r["key"])]
    reports = db.list_reports(CON, job_id)
    feedback = db.feedback_rows(CON, job_id, limit=100_000)
    pages = [dict(r) for r in CON.execute(
        "SELECT job_id,page_no,drawing_no,title,page_kind,in_scope,scope_reason,"
        "width,height FROM pid_page WHERE job_id=? ORDER BY page_no", (job_id,))]

    def dump(obj) -> str:
        return json.dumps(obj, ensure_ascii=False, indent=1, default=str)

    stamp = (info["built_at"] or "unknown").replace("-", "")
    name = f"pid_diag_v{info['version']}_{stamp}_{job_id}.zip"
    DIAGNOSTICS.mkdir(parents=True, exist_ok=True)
    path = DIAGNOSTICS / name

    files = {
        "reports.json": dump({"count": len(reports), "reports": reports,
                              "labels": REPORT_WHAT_LABELS}),
        "analysis/rows.json": dump(rows),
        "analysis/pages.json": dump(pages),
        "analysis/engine.json": dump(engine),
        "analysis/derived_layout.json": dump(layout),
        "analysis/applied_rules.json": dump(applied),
        "edits.json": dump(edits),
        "feedback.json": dump({"count": len(feedback), "records": feedback}),
    }
    # A failed analysis carries the traceback here rather than on screen.  It is
    # the one thing a developer needs and the one thing a reviewer cannot use, so
    # it goes in the export and not in the message.
    detail = job["error_detail"] if "error_detail" in job.keys() else ""
    if detail:
        files["error.txt"] = (
            f"status: {job['status']}\n"
            f"shown to the user: {job['message']}\n\n{detail}")
    manifest = {
        "build": info,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "job": {"id": job_id, "pdf_name": job["pdf_name"],
                "pdf_sha256": job["pdf_sha256"],
                "fingerprint": job["fingerprint"],
                "status": job["status"],
                "message": job["message"],
                "error_detail_included": bool(detail)},
        "counts": {"rows": len(rows), "reports": len(reports),
                   "edits": len(edits), "feedback": len(feedback),
                   "pages": len(pages),
                   "derived_layout_measured": sum(
                       1 for i in (layout.get("items") or [])
                       if i.get("source") == "DERIVED"),
                   "derived_layout_applied": len(layout.get("moved") or [])},
        "excluded": DIAGNOSTIC_EXCLUDED,
        "audit": audit.run(CON, DATA_DIR),
        "contents": sorted(list(files) + ["logs/server.log", "MANIFEST.json"]),
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("MANIFEST.json", dump(manifest))
        for inner, text in files.items():
            z.writestr(inner, text)
        z.writestr("logs/server.log", _log_tail())
    return {"filename": name, "bytes": path.stat().st_size,
            "counts": manifest["counts"], "excluded": DIAGNOSTIC_EXCLUDED,
            "contents": manifest["contents"], "build": info}


@app.post("/jobs/{job_id}/diagnostic")
def make_diagnostic(job_id: str):
    """Build the export and say how big it is; the browser fetches it after."""
    return _diagnostic_zip(job_id)


@app.get("/jobs/{job_id}/diagnostic/{filename}")
def get_diagnostic(job_id: str, filename: str):
    path = DIAGNOSTICS / Path(filename).name
    if not path.exists() or job_id not in path.name:
        raise HTTPException(404, "that export has not been built")
    return FileResponse(path, media_type="application/zip", filename=path.name)


@app.get("/jobs/{job_id}/drawings")
def job_drawings(job_id: str):
    """Drawings in this job with their row and review counts, grouped by system."""
    if db.get_job(CON, job_id) is None:
        raise HTTPException(404, "no such job")
    return db.drawings_of(CON, job_id)


@app.get("/jobs/{job_id}/revisions")
def job_snapshots(job_id: str):
    # 이름이 `revisions` 였다가 바뀌었다.  같은 모듈이 `app.revisions` 를
    # import 하므로 함수 이름이 모듈을 가려서, 프로젝트를 만들 때 500 이 났다.
    # 여기서 말하는 것은 개정 리비전이 아니라 **산출 스냅샷**이기도 하다.
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
            # 11회차 — 발주처 양식은 SCOPE=SCT 만 담는다.  뺀 행이 몇 개인지
            # 여기 적힌다 (조용히 사라지지 않는 것이 이 필터의 조건이다).
            "scope_filter": result.get("scope_filter"),
            "out_of_scope_rows": result.get("out_of_scope_rows", 0),
            "legacy_no_scope_rows": result.get("legacy_no_scope_rows", 0),
            "note": "unmapped_values lists edits with no column in that "
                    "deliverable's form; they are stored but not written. "
                    "out_of_scope_rows counts rows left out because their "
                    "SCOPE is not SCT; legacy_no_scope_rows counts rows with "
                    "no SCOPE at all (an analysis from before the column "
                    "existed) - those are still written, and a non-zero "
                    "number means the drawing set should be re-analysed",
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
# repository does not carry these - `data/` is gitignored - so on a fresh clone
# every deliverable starts out with no template and says so.  The packaged build
# carries none of them either: `build.bat` ships code and config and nothing of
# the client's, so on an exe every deliverable waits for an upload and says so.
#
# These are *blank* forms, not the client's filled-in lists.  Filling a filled-in
# form left the client's own values standing in every column the config does not
# map, under rows that are now different instruments - 14,121 cells on AL NOUF1,
# so an ACW pump row went out carrying 601.9 degC and P92 chrome steel.  The
# empty copy is made by `excel_out.blank_form`; `python3 -m app.forms` writes
# all three.
_BUILTIN = {
    "FIELD": ROOT / "data" / "blank" / "FIELD.xlsx",
    "BFV": ROOT / "data" / "blank" / "BFV.xlsx",
    "MOV": ROOT / "data" / "blank" / "MOV.xlsx",
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


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """The tab icon, served locally.

    `index.html` links `/static/favicon.svg`, so a browser that reads the link
    never asks for this.  Some ask anyway - which is where the 404 in the console
    came from - so the well-known path answers too, with the same file.  Nothing
    is fetched from anywhere: this build has to run with no network at all.
    """
    return FileResponse(STATIC / "favicon.svg", media_type="image/svg+xml")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


# 감사기 상시 실행 — `docs/db_hygiene.md` 의 (가).  세기만 하고 지우지 않는다.
# 기동 때 한 번 로그에 남기고, 산출물을 만들 때 MANIFEST 에 같은 값을 싣는다.
def _audit_on_start() -> None:
    try:
        report = audit.run(CON, DATA_DIR)
    except Exception as exc:                         # noqa: BLE001
        print(f"[감사] 실행하지 못했습니다: {exc}", flush=True)
        return
    for line in report["lines"]:
        print(f"[감사] {line}", flush=True)


_audit_on_start()
