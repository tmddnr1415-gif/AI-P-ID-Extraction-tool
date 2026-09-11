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

from app import (audit, axis_overrides, db, excel_out, global_symbols,  # noqa: E402
                 legend_profile, paths, pipeline, revisions, version)
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


def _stopped_stage(job_id: str) -> str:
    """실패 직전에 파이프라인이 마지막으로 말한 **단계 이름** (21회차).

    새로 만드는 값이 아니다.  파이프라인은 단계마다 `set_progress` 로 그 이름을
    `job.message` 에 적고 있었고(`measuring sheet 37 of 60` 처럼), 실패 처리가
    같은 칸을 사유 문장으로 덮어써서 **그 사실이 사라지고 있었다.**  17분을
    기다린 끝에 "사유를 특정하지 못했습니다" 만 남은 화면이 그것이다.

    그래서 덮기 **전에** 한 번 읽어 둔다.  옮겨 적는 것은 파이프라인이 쓴 원문
    그대로이고 화면 문장이 아니다 — 한국어로 옮기는 것은 `stageWords()` 가
    이미 하고 있고, 모르는 값은 그대로 쓴다 (§8 · 15회차 `compare_note`).
    """
    row = db.get_job(CON, job_id)
    if row is None:
        return ""
    try:
        return str(row["message"] or "")
    except (KeyError, IndexError):
        return ""


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


def _scope_summary(rows: list) -> dict:
    """완료 화면이 읽는 결과 요약 (12회차).

    "분석이 끝났다" 만으로는 사람이 무엇을 받았는지 알 수 없고, 11회차부터는
    **화면에 있는 행과 발주처 양식에 나가는 행이 다르다**.  그 차이를 여기서
    세어 완료 화면이 사유까지 말할 수 있게 한다.

    세는 기준은 산출 필터와 **같은 함수**다 (`excel_out.in_client_scope`) —
    화면이 말하는 수와 파일에 들어가는 수가 갈리면 안 된다.

    18회차에 **두 사실이 갈렸다.**  전량 모드에서는 "양식에 나가는가"와
    "누가 공급하는가"가 더 이상 같은 질문이 아니다 — 벤더 공급분도 나간다.
    그래서 세 가지를 따로 센다:

        delivered / held   양식에 나가는가          (`in_client_scope`)
        vendor             공급 주체가 타사인가      (SCOPE 열 값)
        legacy_no_scope    판정한 적이 없는가

    한 숫자로 접으면 완료 화면이 "260행이 빠집니다"라고 거짓말을 한다.
    """
    out = {"total": len(rows), "delivered": 0, "held": 0,
           "by_reason": {}, "by_tab": {}, "held_types": {},
           "form_scope": excel_out.form_scope_mode(),
           "vendor": 0, "vendor_by_reason": {}}
    for r in rows:
        scope = str(r.get("scope") or "").strip()
        wrapped = {"values": {"scope": scope}}
        if excel_out.scope_state(wrapped) == "out_of_scope":
            out["vendor"] += 1
            out["vendor_by_reason"][scope] = out["vendor_by_reason"].get(scope, 0) + 1
        if excel_out.in_client_scope(wrapped):
            out["delivered"] += 1
            out["by_tab"][r["tab"]] = out["by_tab"].get(r["tab"], 0) + 1
        else:
            out["held"] += 1
            out["by_reason"][scope] = out["by_reason"].get(scope, 0) + 1
            t = str(r.get("type") or "")
            out["held_types"][t] = out["held_types"].get(t, 0) + 1
    out["legacy_no_scope"] = sum(
        1 for r in rows if not str(r.get("scope") or "").strip())
    return out


class Cancelled(Exception):
    """사람이 분석을 취소했다.  `progress()` 에서 올라온다."""


# 취소를 기다리는 job 들.  화면이 버튼을 누르면 여기 들어오고, 진행 보고
# 콜백이 다음 장으로 넘어갈 때 그것을 보고 멈춘다.
#
# **부분 결과가 남지 않는다** — `pipeline.analyse` 는 아무것도 저장하지 않고,
# 행을 쓰는 것은 그 뒤의 `db.store_result` 하나뿐이며, 안정 ID 를 부여하는
# `_run_comparison` 은 그보다 더 뒤다.  그래서 취소한 분석은 행 0 · 안정 ID
# 소비 0 이고, 리비전 이름도 프로젝트 장부에 남지 않는다(`next_revision` 은
# 장부 길이에서 계산되고 장부는 `_run_comparison` 에서만 늘어난다).
# §7.3 의 "Rev.A 에서 한 번만 부여하고 회수하지 않는다" 와 충돌하지 않는다.
_CANCEL: set = set()
_CANCEL_LOCK = threading.Lock()


def _cancel_requested(job_id: str) -> bool:
    with _CANCEL_LOCK:
        return job_id in _CANCEL


def _cancel_clear(job_id: str) -> None:
    with _CANCEL_LOCK:
        _CANCEL.discard(job_id)


def _worker() -> None:
    while True:
        job_id = _JOBS.get()
        row = db.get_job(CON, job_id)
        if row is None:
            continue
        try:
            # 큐에서 기다리는 동안 취소했을 수 있다 - 시작하기 전에 본다.
            if _cancel_requested(job_id):
                raise Cancelled()
            db.mark_started(CON, job_id)
            db.set_progress(CON, job_id, 0.0, "starting", sheets=(0, 0))
            _emit(job_id, {"progress": 0.0, "message": "starting",
                           "status": "running", "sheets_done": 0,
                           "sheets_total": 0})

            def progress(done, total, message, sheets=None, plan=None,
                         drawing=None):
                # 취소는 여기서만 걸린다.  파이프라인은 장마다 이 콜백을 부르고,
                # 그 사이에는 아무것도 저장하지 않으므로 여기서 끊으면 DB 는
                # 손대지 않은 상태 그대로다.
                if _cancel_requested(job_id):
                    raise Cancelled()
                frac = done / max(total, 1)
                db.set_progress(CON, job_id, frac, message, sheets=sheets)
                out = {"progress": frac, "message": message, "status": "running"}
                if sheets is not None:
                    out["sheets_done"], out["sheets_total"] = sheets
                if drawing:
                    out["drawing_no"] = drawing
                if plan is not None:
                    db.set_sheet_plan(CON, job_id, plan)
                    out["sheet_plan"] = plan
                _emit(job_id, out)

            # 15회차 — 그 프로젝트가 이미 읽어 둔 범례가 있으면 넘긴다.
            # **없으면 `None` 이고, `None` 이면 파이프라인이 반드시 유도한다.**
            # 프로젝트에 안 묶인 분석은 언제나 `None` 이다 - 프로필은 프로젝트
            # 폴더 안에만 살고, 다른 프로젝트가 공유할 길이 없다.
            profile = legend_profile.load(DATA_DIR, row["project"])
            result = pipeline.analyse(Path(row["pdf_path"]), progress=progress,
                                      reference=VERIFY_AGAINST,
                                      legend_profile=profile)
            result["fingerprint"] = pipeline.fingerprint(result)
            # 새 프로젝트면 이번에 읽은 범례를 그 프로젝트 것으로 남긴다.
            # 이미 프로필이 있으면 **덮지 않는다** - 범례가 달라졌다면 그것은
            # `legend_profile.changes` 로 사람에게 가고, 갱신은 사람이 고른다.
            lp_out = result.get("legend_profile") or {}
            if row["project"] and profile is None and lp_out.get("profile"):
                saved = dict(lp_out["profile"])
                saved.setdefault("source_meta", {})
                saved["source_meta"].update({"job_id": job_id,
                                             "revision": row["revision"],
                                             "project": row["project"]})
                legend_profile.save(DATA_DIR, row["project"], saved)
                lp_out["saved"] = True
            summary = db.store_result(CON, job_id, result)
            # 도면이 스스로 말한 개정을 문서 하나로 접어 둔다 (13회차 [E]).
            # 접기 전 장별 값은 `pid_page` 에 그대로 남아 있고, 화면은 둘 다
            # 보인다 - 대표값만 두면 "53장 중 3장만 C" 라는 사실이 사라진다.
            summary["doc_rev"] = _store_doc_rev(job_id)
            # 프로젝트에 묶인 분석이면 여기서 바로 대조한다.  묶이지 않았으면
            # 예전과 똑같이 동작한다 - 리비전은 얹는 것이지 대체하는 것이 아니다.
            try:
                summary["revision"] = _run_comparison(job_id)
            except Exception as exc:                 # noqa: BLE001
                traceback.print_exc()
                summary["revision"] = {"error": str(exc)}
            db.mark_finished(CON, job_id)
            fin = db.get_job(CON, job_id)
            summary["scope"] = _scope_summary(result["rows"])
            # 15회차 — 이 결과가 어느 범례로 나왔나.  완료 화면도 말한다:
            # 방금 분석을 건 사람은 결과 화면을 먼저 보고, 재사용 여부를
            # 거기서 못 보면 다음에 볼 자리가 없다.
            summary["legend"] = _legend_facts(fin)
            _emit(job_id, {"progress": 1.0, "message": "done", "status": "done",
                           "summary": summary,
                           "sheet_plan": _plan(fin),
                           "page_count": fin["page_count"],
                           "sheets_done": fin["sheets_done"],
                           "sheets_total": fin["sheets_total"],
                           "elapsed_s": _elapsed(fin)})
        except Cancelled:
            # 취소는 실패가 아니다.  사유도 트레이스도 없고, 남은 것도 없다.
            _cancel_clear(job_id)
            db.set_progress(CON, job_id, 0.0, "사용자가 분석을 취소했습니다",
                            "cancelled", sheets=(0, 0))
            db.mark_finished(CON, job_id)
            fin = db.get_job(CON, job_id)
            _emit(job_id, {"progress": 0.0, "status": "cancelled",
                           "message": "사용자가 분석을 취소했습니다",
                           "page_count": fin["page_count"],
                           "elapsed_s": _elapsed(fin)})
        except (pipeline.LegendUnavailable,
                pipeline.TitleBlockUnreadable) as exc:
            # 15회차 — 이 실패는 파이프라인이 **직접 검사한 조건**이고 문장도
            # 거기서 썼다.  그래서 `_failure_reason` 을 거치지 않는다: 그 함수는
            # *알 수 없는* 실패에 쓰는 것이고, 아는 실패까지 일반 문구로 덮으면
            # 사람이 무엇을 하면 되는지 알 수 없다.
            #
            # 21회차에 `TitleBlockUnreadable` 이 같은 자리에 붙었다.  두 예외의
            # 처리가 글자 그대로 같으므로 갈래를 늘리지 않고 튜플로 받는다 —
            # 처리가 갈리면 그때 나눈다.
            traceback.print_exc()
            reason = str(exc)
            stage = _stopped_stage(job_id)          # 덮기 전에 읽는다
            db.set_progress(CON, job_id, 0.0, reason, "failed",
                            error_detail=traceback.format_exc())
            db.set_stopped_stage(CON, job_id, stage)
            db.mark_finished(CON, job_id)
            fin = db.get_job(CON, job_id)
            _emit(job_id, {"progress": 0.0, "status": "failed",
                           "message": reason,
                           "sheet_plan": _plan(fin),
                           "stopped_stage": stage,
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
            stage = _stopped_stage(job_id)          # 덮기 전에 읽는다
            reason = _failure_reason(Path(row["pdf_path"]))
            db.set_progress(CON, job_id, 0.0, reason, "failed", error_detail=detail)
            db.set_stopped_stage(CON, job_id, stage)
            db.mark_finished(CON, job_id)
            fin = db.get_job(CON, job_id)
            # 어디까지 갔는지.  진행률은 0 으로 떨어뜨리지만 장수는 남긴다 -
            # "몇 장째에서 멈췄나" 가 사용자가 확인할 수 있는 유일한 단서다.
            _emit(job_id, {"progress": 0.0, "status": "failed",
                           "message": reason,
                           "sheet_plan": _plan(fin),
                           "stopped_stage": stage,
                           "page_count": fin["page_count"],
                           "sheets_done": fin["sheets_done"],
                           "sheets_total": fin["sheets_total"],
                           "elapsed_s": _elapsed(fin)})
        finally:
            _cancel_clear(job_id)
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


@app.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    """분석을 취소한다 (12회차).

    표시만 해 두고, 실제로 멈추는 것은 진행 보고 콜백이다 — 파이프라인이
    다음 장으로 넘어갈 때 이 표시를 보고 예외를 올린다.  그 사이에 DB 에
    쓰이는 것은 진행률뿐이라, 취소한 분석은 **행 0 · 안정 ID 소비 0** 이다.

    이미 끝난 분석은 취소할 수 없다 — 지우는 것과 다른 일이다.
    """
    row = db.get_job(CON, job_id)
    if row is None:
        raise HTTPException(404, "no such job")
    if row["status"] not in ("queued", "running"):
        raise HTTPException(409, f"이 분석은 '{row['status']}' 상태라 "
                                 f"취소할 수 없습니다")
    with _CANCEL_LOCK:
        _CANCEL.add(job_id)
    return {"job_id": job_id, "cancelling": True}


@app.post("/jobs/{job_id}/reanalyse")
def reanalyse(job_id: str):
    """Re-run the engine, keeping every reviewer edit."""
    if db.get_job(CON, job_id) is None:
        raise HTTPException(404, "no such job")
    db.set_progress(CON, job_id, 0.0, "queued", "queued", sheets=(0, 0))
    _JOBS.put(job_id)
    return {"job_id": job_id, "queued": True}


DOC_REV_RULE = CFG.get_or("revision.document_rule", "max")


def _store_doc_rev(job_id: str) -> dict:
    """장별 개정을 문서 하나로 접어 job 에 적는다.

    규칙은 config 에서 온다 (`revision.document_rule`).  **도면에서 유도되지
    않는 값이므로** 그 사실이 config 주석에 실측 분포와 함께 적혀 있고, 여기서는
    고르지 않는다.  접은 값과 분포를 함께 돌려준다.
    """
    pages = db.page_revisions(CON, job_id)
    folded = revisions.document_revision(pages, DOC_REV_RULE)
    db.set_doc_rev(CON, job_id, folded.get("rev") or "")
    return folded


def _job_public(row) -> dict:
    """A job as the browser may see it: everything except the raw traceback.

    `error_detail` stays server-side.  Not rendering it would be enough to keep it
    off the screen, but it would still be in the response, one devtools tab away
    from being read as the answer - and the point of the message column is that
    the answer is the sentence, not the traceback.  It travels in the diagnostic
    export instead, which is what a developer asks for by name.

    21회차에 **접어 둔 채로 볼 수 있는 길**이 하나 늘었다
    (`GET /jobs/{id}/error_detail`).  이 함수는 그대로다 - 기본 응답에는 여전히
    안 실린다.  펼치는 것은 사람이 누르는 행위이고, 그때만 따로 받아 온다.
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
    carried = _carry_edits(job_id, name, compared, result["states"])
    entry = revisions.record_revision(
        DATA_DIR, name, revision, job_id=job_id, pdf_name=job["pdf_name"],
        compared_with=compared, result=result)
    return {"project": name, "revision": revision, "compared_with": compared,
            "label": entry["label"], "counts": result["counts"],
            "radii": result["radii"], "carried": carried,
            "sheet_revisions": _sheet_rev_compare(job_id, name, compared)}


def _job_of_revision(name: str, revision: str) -> str:
    """그 프로젝트의 그 리비전을 분석한 job.  장부에서 찾는다."""
    if not revision:
        return ""
    try:
        meta = revisions.load_project(DATA_DIR, name)
    except (KeyError, ValueError):
        return ""
    for r in meta.get("revisions") or []:
        if r["revision"] == revision:
            return r.get("job_id") or ""
    return ""


def _carry_edits(job_id: str, project: str, compared_with: str,
                 states: dict) -> dict:
    """이전 리비전의 편집을 이 리비전으로 잇는다 (13회차 [D]).

    **짝은 안정 ID 로 짓는다** — 좌표나 행 키가 아니다.  §7.3 이 ID 를
    "Rev.A 에서 한 번만 부여하고 재정렬하지 않는" 것으로 정의해 둔 이유가
    그것이고, 여기서 그 ID 를 쓰는 것이지 새로 매기지 않는다.

    세 가지를 지킨다:
      · 추출값(`ai_json`)은 건드리지 않는다.  지문·축1·축2·Q'ty 축은 그 층만
        읽으므로 승계가 측정에 새지 않는다.
      · **이번 리비전에서 사람이 이미 고친 칸은 덮지 않는다.**  승계는 빈
        자리를 채우는 것이다.
      · 이어받은 칸에서 **엔진의 답이 그 사이 달라졌으면** 값을 고르지 않고
        둘 다 들고 검토로 올린다 — 재분석이 하는 것과 같은 규칙이다.
    """
    prev_job = _job_of_revision(project, compared_with)
    if not prev_job or prev_job == job_id:
        return {"from": compared_with, "matched": 0, "filled": 0, "conflicts": 0}
    prev_user = db.user_values_of(CON, prev_job)
    if not prev_user:
        return {"from": compared_with, "matched": 0, "filled": 0, "conflicts": 0}
    prev_ai = db.ai_values_of(CON, prev_job)
    now_ai = db.ai_values_of(CON, job_id)
    # 이전 리비전의 행 키 -> 안정 ID.  이번 리비전의 안정 ID -> 행 키.
    prev_ids = {key: st.get("id") or ""
                for key, st in db.revision_states(CON, prev_job).items()}
    now_by_id = {}
    for key, st in states.items():
        if st.get("id"):
            now_by_id[st["id"]] = key
    carry, conflicts, matched = {}, {}, 0
    for prev_key, fields in prev_user.items():
        sid = prev_ids.get(prev_key)
        key = now_by_id.get(sid) if sid else None
        if not key:
            continue
        matched += 1
        carry[key] = fields
        was, now = prev_ai.get(prev_key, {}), now_ai.get(key, {})
        clash = {f: {"was_ai": was.get(f), "now_ai": now.get(f), "user": v}
                 for f, v in fields.items() if was.get(f) != now.get(f)}
        if clash:
            conflicts[key] = clash
    filled = db.carry_user_values(CON, job_id, carry) if carry else 0
    # 이어받은 칸도 **이력에 남긴다** (13회차 캡처가 잡은 결함).
    #
    # 승계만 하고 이력을 안 남기면 새 리비전의 행은 ✎ 로 "사람이 고쳤다" 고
    # 말하면서 **누가 언제 고쳤는지는 말하지 못한다** — 화면이 아는 것보다
    # 적게 말하는 것이고, 팀 공유 중에는 그것이 곧 되짚을 수 없다는 뜻이다.
    # 원래 고친 사람의 이름을 그대로 잇고, 사유에 어느 리비전에서 왔는지 적는다.
    # 지어내는 값이 없다 - 이름도 값도 이전 리비전의 것 그대로다.
    for prev_key, fields in prev_user.items():
        sid = prev_ids.get(prev_key)
        key = now_by_id.get(sid) if sid else None
        if not key or key not in carry:
            continue
        who = db.last_authors(CON, prev_job, prev_key)
        row = db.get_row(CON, job_id, key)
        for field, value in fields.items():
            if field not in db.EDITABLE:
                continue
            db.record_feedback(
                CON, job_id, "EDITED", row_key=key,
                page_no=(row or {}).get("page_no"),
                drawing_no=(row or {}).get("drawing_no") or "",
                rect=(row or {}).get("rect"), field=field,
                ai_value=(now_ai.get(key) or {}).get(field), user_value=value,
                reason=f"{compared_with} 에서 이어받음",
                author=(who.get(field) or {}).get("author") or "",
                pattern_args={"field": field,
                              "ai": (now_ai.get(key) or {}).get(field),
                              "user": value})
    if conflicts:
        db.flag_carry_conflicts(CON, job_id, conflicts)
    return {"from": compared_with, "matched": matched, "filled": filled,
            "conflicts": len(conflicts)}


def _sheet_rev_compare(job_id: str, project: str, compared_with: str) -> dict:
    """장 단위 개정 대조.  도면번호로 짝을 짓는다 — 임의값이 없다."""
    prev_job = _job_of_revision(project, compared_with)
    if not prev_job or prev_job == job_id:
        return {}
    return revisions.compare_sheet_revisions(
        db.page_revisions(CON, job_id), db.page_revisions(CON, prev_job))


@app.get("/projects")
def list_projects(deep: bool = False):
    return [_project_public(m, deep=deep) for m in revisions.list_projects(DATA_DIR)]


@app.get("/home")
def home():
    """첫 화면이 읽는 것 하나 — 프로젝트와, 프로젝트에 안 묶인 분석.

    단위가 **프로젝트**다 (13회차 [C]).  이전에는 job 목록뿐이라 한 프로젝트의
    Rev.A·B·C 가 평평하게 흩어졌고, 목록이 PDF 파일명만 말해서 같은 파일로
    올린 두 분석을 구분할 수 없었다.  프로젝트에 안 묶인 분석은 버리지 않고
    따로 묶어 그대로 보인다 - "프로젝트 없이 한 번만 분석" 은 지금도 있는
    선택지이고, 그렇게 만든 결과가 목록에서 사라지면 안 된다.
    """
    projects = [_project_public(m, deep=True)
                for m in revisions.list_projects(DATA_DIR)]
    projects.sort(key=lambda p: (p.get("latest") or {}).get("analysed_at") or 0,
                  reverse=True)
    claimed = {r.get("job_id") for p in projects for r in p["revisions"]}
    loose = [_job_public(j) for j in db.list_jobs(CON) if j["id"] not in claimed]
    for j in loose:
        j["rows"] = db.row_count(CON, j["id"])
        j["edits"] = db.edited_cell_count(CON, j["id"])
    return {"projects": projects, "loose": loose}


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


def _project_public(meta: dict, *, deep: bool = False) -> dict:
    """화면이 필요한 것: 다음 리비전 이름과 고를 수 있는 비교 대상.

    `deep` 이면 각 리비전에 그 분석의 실물(분석 일시 · 행 수 · 지문 · 문서
    개정 · 상태)을 붙인다.  첫 화면 목록이 그것을 쓴다 — 13회차 조사에서
    같은 `pid_total.pdf` 두 분석을 화면에서 구분할 수 없었던 것이 그 이유다.
    장부(`project.json`)에는 job_id 밖에 없으므로 값은 job 표에서 읽는다.
    """
    out = {**meta,
           "next_revision": revisions.next_revision(meta),
           "compare_choices": revisions.compare_choices(meta),
           "default_compare": revisions.default_compare_target(meta)}
    if not deep:
        return out
    revs = []
    for r in out.get("revisions") or []:
        job = db.get_job(CON, r.get("job_id") or "")
        extra = {}
        if job is not None:
            extra = {"status": job["status"],
                     "analysed_at": job["finished_at"] or job["created_at"],
                     "page_count": job["page_count"],
                     "elapsed_s": _elapsed(job),
                     "fingerprint": job["fingerprint"],
                     "doc_rev": job["doc_rev"],
                     "rows": db.row_count(CON, job["id"]),
                     "edits": db.edited_cell_count(CON, job["id"])}
        revs.append({**r, **extra})
    # 최근순.  같은 프로젝트 안에서도 사람이 마지막에 만진 것이 위에 온다.
    revs.sort(key=lambda r: r.get("analysed_at") or 0, reverse=True)
    out["revisions"] = revs
    out["latest"] = revs[0] if revs else None
    return out


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


# 이전 기록 삭제 (17회차 [E]).
#
# ⚠ **되돌릴 수 없고, 이 호스트에는 팀원 여러 명의 프로젝트가 함께 있다.**
# 그래서 세 가지를 지킨다:
#   1. 지우기 전에 무엇이 사라지는지 먼저 보여 준다 (`deletion_preview`)
#   2. 확인을 두 번 받는다 — 화면의 확인 + 요청 본문의 `confirm` 문자열
#   3. 누가 언제 무엇을 지웠는지 남긴다 (`deletion_log`, 13회차 자기신고 그대로)
#
# **지우는 단위는 분석 하나(job)뿐이다.**  프로젝트 전체를 지우는 길은 만들지
# 않았다 — 그 폴더에 안정 ID 장부가 있고, 그것이 사라지면 같은 이름으로 다시
# 만든 프로젝트가 번호를 1부터 다시 발급해 §7.3("Rev.A 에서 한 번만 부여")이
# 깨진다.  분석 하나를 지우는 것은 그 불변식을 깨지 않는다: `Registry.next_seq`
# 가 장부 전체의 최대 순번 + 1 을 쓰고 상태를 보지 않기 때문이다.
# 근거와 실측은 `docs/round17_delete.md`.
@app.get("/jobs/{job_id}/deletion_preview")
def deletion_preview(job_id: str):
    try:
        return db.deletion_preview(CON, job_id)
    except KeyError:
        raise HTTPException(404, "no such job")


@app.delete("/jobs/{job_id}")
def delete_job(job_id: str, author: str = Form(""), confirm: str = Form("")):
    """분석 하나를 지운다.  `confirm` 이 그 분석의 id 와 같아야 한다."""
    row = db.get_job(CON, job_id)
    if row is None:
        raise HTTPException(404, "no such job")
    if confirm.strip() != job_id:
        raise HTTPException(
            400, "확인 값이 분석 id 와 다릅니다 — 실수로 지워지지 않게 하는 "
                 "장치입니다")
    if row["status"] in ("queued", "running"):
        raise HTTPException(409, "분석 중인 것은 지울 수 없습니다. 먼저 취소하세요")
    summary = db.delete_job(CON, job_id, author=author.strip())
    # 업로드 PDF 는 그 분석만 쓰고 있을 때에만 지운다 - 다른 분석이 같은 파일을
    # 가리키면 그 분석이 도면을 못 연다.  지웠는지는 응답이 말한다.
    removed_pdf = False
    if not summary["pdf_shared_with"]:
        pdf = Path(summary["pdf_path"])
        try:
            if pdf.exists() and pdf.parent.resolve() == UPLOADS.resolve():
                pdf.unlink()
                removed_pdf = True
        except OSError:
            removed_pdf = False
    summary["pdf_removed"] = removed_pdf
    return summary


# --------------------------------------------------------------------------
# 전역 심볼 사전 (18회차)
# --------------------------------------------------------------------------
#
# ★ 여기가 **유일한 등록 경로**다.  파이프라인은 이 사전을 읽기만 하고,
# 어디에도 자동으로 넣는 코드가 없다 (`global_symbols.register` 가 `author` 를
# 요구하고, 그것을 부르는 곳이 아래 하나뿐이다).
#
# 왜 그렇게까지 하나: 전역 사전에 그 프로젝트에서만 통하는 심볼이 들어가면
# **다음 프로젝트에서 오검출이 난다**.  오검출은 미검출보다 나쁘다 — 없는
# 것은 눈에 띄지만 있는 것은 안 띈다.  §2.2 "표준 사전에 프로젝트 표기
# 혼입" 금지가 이 이야기다.

@app.get("/symbols/global")
def global_symbol_list():
    """등록된 것과 켜짐/꺼짐."""
    data = global_symbols.load(DATA_DIR)
    return {"enabled": data.get("enabled", True),
            "symbols": list(data["symbols"].values()),
            "path": str(global_symbols.path(DATA_DIR)),
            "note": "프로젝트 범례가 정의한 것이 있으면 그것이 이깁니다. "
                    "이 사전은 범례에 **없는** 심볼만 채웁니다."}


@app.post("/symbols/global")
def global_symbol_register(symbol_id: str = Form(...), kind: str = Form(...),
                           name: str = Form(...), type_value: str = Form(""),
                           deliverable: str = Form(""), author: str = Form(""),
                           source_page: int = Form(0), note: str = Form(""),
                           signature: str = Form("{}")):
    """사람이 확인한 심볼 하나를 넣는다.  **이름 없이는 들어가지 않는다.**"""
    try:
        sig = json.loads(signature or "{}")
    except ValueError:
        sig = {}
    try:
        return global_symbols.register(
            DATA_DIR, symbol_id=symbol_id, kind=kind, name=name,
            type_value=type_value, deliverable=deliverable, signature=sig,
            author=author, source_page=source_page, note=note)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@app.delete("/symbols/global/{symbol_id}")
def global_symbol_remove(symbol_id: str):
    if not global_symbols.remove(DATA_DIR, symbol_id):
        raise HTTPException(404, "no such symbol")
    return {"removed": symbol_id}


@app.post("/symbols/global/enabled")
def global_symbol_toggle(on: bool = Form(...)):
    """오염되면 되돌려야 한다 — 끄면 사전이 없던 때와 **정확히 같아진다**."""
    data = global_symbols.set_enabled(DATA_DIR, on)
    return {"enabled": data["enabled"], "symbols": len(data["symbols"])}


@app.get("/jobs/{job_id}/unjudged")
def unjudged_symbols(job_id: str):
    """이 분석이 **판정하지 못한** 심볼들 — 등록 화면이 읽는 목록.

    분석할 때 모아 둔 것을 그대로 돌려준다.  여기서 다시 세지 않는다:
    58장을 다시 읽으면 3분이 걸리고, 그러면 화면이 열리지 않는다.
    옛 분석에는 이 칸이 없으므로 **빈 목록과 "모른다" 를 구분해서** 말한다.
    """
    row = db.get_job(CON, job_id)
    if row is None:
        raise HTTPException(404, "no such job")
    eng = json.loads(row["engine_json"] or "{}")
    if "unjudged_symbols" not in eng:
        return {"known": False, "items": [],
                "note": "이 분석은 미판정 심볼을 모으기 전(18회차 이전)의 것입니다. "
                        "다시 분석하면 목록이 생깁니다."}
    return {"known": True, "items": eng["unjudged_symbols"]}


@app.get("/deletions")
def deletions():
    """지운 기록의 기록.  행은 사라져도 이것은 남는다."""
    out = []
    for r in db.deletion_log(CON):
        r = dict(r)
        r["summary"] = json.loads(r.pop("summary_json") or "{}")
        out.append(r)
    return out


@app.get("/jobs/{job_id}")
def job(job_id: str):
    row = db.get_job(CON, job_id)
    if row is None:
        raise HTTPException(404, "no such job")
    out = _job_public(row)
    out["engine"] = json.loads(out.pop("engine_json") or "{}")
    out["review_count"] = db.review_count(CON, job_id)
    out["revisions"] = [dict(r) for r in db.list_revisions(CON, job_id)]
    # 발주처 양식에 무엇이 담기는가 — 그리드가 그려지기 **전에** 알아야 한다
    # (`scopeFacts` 가 행마다 이 문장을 만든다).  값은 지금 설정이고 저장된
    # 것이 아니다: 산출은 지금 일어나므로 지금 설정이 맞는 답이다.
    out["form_scope"] = excel_out.form_scope_mode()
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


@app.get("/jobs/{job_id}/measured_config")
def measured_config(job_id: str):
    """이 분석이 **그 도면에서 잰** 기하를 프로젝트 설정 조각으로 돌려준다 (22회차).

    ## 왜 필요한가

    새 회사 양식(예: TC2)을 이 도구로 읽으려면 그 양식의 좌표를 담은
    `config/project_<이름>.yaml` 이 있어야 한다.  그런데 그 좌표를 **재는 코드는
    이미 있다** — `derive_layout` 이 도면번호·제목·프로젝트명 칸을 그 도면이
    인쇄한 캡션으로 찾고, 종이 크기와 도면 영역도 잰다.

    없던 것은 **사람이 그 값을 볼 길**이었다.  22회차 현장 사고 때 그 값이
    예외 문장에 우연히 섞여 나온 것이 유일한 통로였다.  여기서 제대로 낸다.

    ## 무엇을 내지 않는가

    **잰 것만 낸다.**  이력 표 기하(`hist_*`)는 `derive_layout` 이 재지 않는다 —
    그 표는 칸마다 캡션이 없어 앵커가 없기 때문이다 (`project_sadara.yaml` 의
    주석이 그렇게 적어 두었다).  그래서 여기서도 내지 않고, **사람이 재야 하는
    항목**으로 이름만 적어 둔다.  없는 값을 지어내지 않는다 (§2.1 ③).
    """
    job = db.get_job(CON, job_id)
    if job is None:
        raise HTTPException(404, "그런 분석이 없습니다")
    engine = json.loads(job["engine_json"] or "{}")
    # ★ 저장은 **이미 되고 있었다** — `applied_rules` 안이다 (`pipeline` 의
    # `applied` dict).  없던 것은 그것을 꺼내 보는 길뿐이었다.
    # 13·15·16·18회차와 같다 — 없는 것을 만들기 전에 있는 것을 찾는다.
    layout = (engine.get("applied_rules") or {}).get("layout") or {}
    # `items` 가 이 분석이 **잰** 것 전부다 (`key`/`value`/`source`/`evidence`).
    # `moved` 는 그중 프로필과 달랐던 것만이라, 프로필과 우연히 같은 값이 빠진다 —
    # 설정을 만들 때는 **잰 것 전부**가 필요하므로 `items` 를 쓴다.
    values = {it["key"]: it["value"] for it in (layout.get("items") or [])
              if isinstance(it, dict) and "key" in it}
    if not layout:
        raise HTTPException(
            404, "이 분석에는 잰 기하가 없습니다. 다시 분석하면 담깁니다.")

    # 프로젝트 설정 파일에 그대로 붙일 수 있는 모양으로 접는다.
    tree: dict = {}
    for dotted, value in sorted(values.items()):
        node = tree
        parts = dotted.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    return {
        "job_id": job_id,
        "pdf_name": job["pdf_name"],
        "document_code": layout.get("document_code"),
        "profile": layout.get("profile"),
        "profile_code": layout.get("profile_code"),
        "applied": layout.get("applied"),
        "reason": layout.get("reason"),
        "measured": tree,
        "measured_yaml": _as_yaml(tree),
        "evidence": {it["key"]: it.get("evidence")
                     for it in (layout.get("items") or [])
                     if isinstance(it, dict) and "key" in it},
        "notes": layout.get("notes") or [],
        "must_measure_by_hand": [
            "title_block.hist_rule_x0_max", "title_block.hist_rule_x1_min",
            "title_block.hist_rule_y", "title_block.hist_rev_col",
            "title_block.hist_date_col", "title_block.hist_row_inset",
        ],
        "note": ("`measured` 는 이 도면에서 **잰** 값입니다. "
                 "`must_measure_by_hand` 는 이 도구가 재지 못하는 항목이라 "
                 "사람이 도면에서 재어 넣어야 합니다 — 개정 이력 표는 칸마다 "
                 "캡션이 없어 앵커가 없습니다."),
    }


def _as_yaml(tree: dict, indent: int = 0) -> str:
    """설정 파일에 붙일 수 있는 최소 YAML.  **값을 바꾸지 않고 줄만 만든다.**

    라이브러리를 쓰지 않는 이유는 하나다 - 이 함수가 내는 것은 사람이 눈으로
    확인하고 붙일 조각이지 다시 읽어들일 문서가 아니고, 숫자 표기가 조용히
    바뀌면(1.0 -> 1) 그것이 곧 값의 변형이다.
    """
    out = []
    pad = "  " * indent
    for key, value in tree.items():
        if isinstance(value, dict):
            out.append(f"{pad}{key}:")
            out.append(_as_yaml(value, indent + 1))
        elif isinstance(value, (list, tuple)):
            out.append(f"{pad}{key}: [{', '.join(repr(v) for v in value)}]")
        else:
            out.append(f"{pad}{key}: {value!r}")
    return "\n".join(x for x in out if x)


@app.get("/jobs/{job_id}/error_detail")
def error_detail(job_id: str):
    """실패한 분석의 **예외 원문**.  화면이 접어 둔 채로 두고, 펼칠 때만 받는다.

    21회차 — 그 전에는 이 값이 진단 내보내기 zip 안에만 있었다.  그것은
    "그대로 노출하지 않는다" 는 뜻으로는 맞았지만, 회사 PC 에서 실패한 사람이
    개발자에게 보낼 것을 만들려면 zip 을 내려받아 풀어야 했다 — 실제로 이번
    회차의 원본 예외도 사용자가 **터미널에서** 떠다 준 것이다.

    그래서 길만 하나 열되 기본 응답(`_job_public`)은 그대로 둔다: 이 값은
    누르지 않으면 오지 않고, 화면의 답은 여전히 사유 문장이다.
    """
    row = db.get_job(CON, job_id)
    if row is None:
        raise HTTPException(404, "그런 분석이 없습니다")
    detail = row["error_detail"] if "error_detail" in row.keys() else ""
    return {"job_id": job_id, "status": row["status"], "detail": detail or ""}


@app.get("/jobs/{job_id}/scope_summary")
def scope_summary_now(job_id: str):
    """지금 이 순간 발주처 양식에 나가는 행 수 — **사람이 고친 값까지 반영**한다.

    완료 화면의 숫자는 분석이 끝난 순간의 것이라, 그 뒤에 누가 SCOPE 를 고치면
    화면과 파일이 갈린다.  편집 안내가 "780행 → 779행" 이라고 말하려면 그 값이
    산출 필터와 같은 판정에서 나와야 하므로, 완료 화면이 쓰는 `_scope_summary`
    를 **그대로** 부른다 (그 함수가 `excel_out.in_client_scope` 를 쓴다).

    삭제 표시된 행은 뺀다 — `excel_out.write_all` 이 그 행을 먼저 거르므로,
    빼지 않으면 이 수와 실제 파일의 행수가 갈린다.
    """
    if db.get_job(CON, job_id) is None:
        raise HTTPException(404, "no such job")
    rows = [{"scope": r["values"].get("scope"), "tab": r["tab"],
             "type": r["values"].get("type")}
            for r in db.merged_rows(CON, job_id) if not r.get("deleted")]
    return _scope_summary(rows)


# --------------------------------------------------------------------------
# 범례 프로필 — 무엇으로 분석했나, 그리고 범례가 달라졌나 (15회차)
# --------------------------------------------------------------------------

def _legend_facts(job) -> dict:
    """이 분석이 어느 범례로 나왔는지.  **화면에서 이 판정을 하는 곳은 여기 하나.**

    옛 분석(15회차 이전)에는 이 칸이 없다.  없는 것을 "유도했음" 으로 읽으면
    그것이 곧 지어내기이므로, `mode: unknown` 으로 그대로 말한다.
    """
    engine = json.loads(job["engine_json"] or "{}") if job else {}
    lp = engine.get("legend_profile") or {}
    stored = legend_profile.load(DATA_DIR, job["project"]) if job else None
    mode = lp.get("mode") or "unknown"
    changes = lp.get("changes") or []
    if mode == "unknown":
        line = ("이 분석은 범례 프로필이 생기기 전(15회차 이전)에 돌았습니다 — "
                "범례를 재서 왔는지 기록이 없습니다")
    elif mode == "derived":
        # "범례 4장" 이 아니라 "값을 읽은 3장" 이다.  이 문서는 범례가 4장인데
        # 값을 내놓은 장은 3장이고(p4 는 어느 항목의 근거도 아니다), 4라고
        #적으면 화면이 세지 않은 것을 세었다고 말하게 된다.
        line = ("이 문서의 범례를 직접 읽어 분석했습니다"
                + (f" (값을 읽은 범례 {len(lp.get('legend_sheets') or [])}장)"
                   if lp.get("legend_sheets") else ""))
    else:
        # 왜 대조를 못 했는지는 바로 옆 `compare_note` 가 말한다.  같은 사실을
        # 두 번 적으면 띠가 길어지고 읽는 사람은 두 문장을 대조하게 된다
        # (14회차 "한 번에 한 줄만" 과 같은 이유).
        line = "이 프로젝트가 앞서 읽어 둔 범례를 그대로 썼습니다"
    sheets = lp.get("legend_sheets") or []
    missing = lp.get("uncompared") or []
    if mode != "reused":
        note = ""
    elif not lp.get("compared"):
        note = ("이 PDF 에 범례가 없어 **대조하지 못했습니다** — "
                "프로필과 같다고 단정하지 않습니다")
    else:
        note = f"이 PDF 에서 값을 읽은 범례 {len(sheets)}장과 대조했습니다"
        if missing:
            note += (f" — {len(missing)}항목은 이 PDF 에 없어 "
                     f"**대조하지 못했습니다**")
    return {"mode": mode,
            "measured": bool(lp.get("measured")),
            "compared": bool(lp.get("compared")),
            # 이번 PDF 가 읽지 못해 대조하지 못한 항목.  "같다" 가 아니다.
            "uncompared": lp.get("uncompared") or [],
            # 문장은 **여기서** 만든다 (파이프라인에 저장하지 않는다).
            "compare_note": note,
            "legend_sheets": lp.get("legend_sheets") or [],
            "summary": lp.get("summary") or {},
            "changes": changes,
            "change_count": len(changes),
            "can_adopt": bool(changes and lp.get("measured_profile")),
            "has_stored_profile": stored is not None,
            "stored_summary": legend_profile.summary(stored) if stored else {},
            # 무엇을 저장했는지 사람이 읽을 수 있어야 한다 ([C]).  항목명 · 값 ·
            # 유도 근거를 그대로 편 줄이고, 화면은 접어 두었다가 펼친다.
            "stored_lines": legend_profile.describe(stored) if stored else [],
            "stored_path": (str(legend_profile.profile_path(
                DATA_DIR, job["project"])) if stored else ""),
            "line": line}


@app.get("/jobs/{job_id}/legend_profile")
def job_legend_profile(job_id: str):
    """이 분석이 어느 범례로 나왔나 + 프로필과 다른 곳."""
    job = db.get_job(CON, job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    out = _legend_facts(job)
    out["project"] = job["project"]
    out["revision"] = job["revision"]
    return out


@app.post("/jobs/{job_id}/legend_profile/adopt")
def adopt_legend_profile(job_id: str, keys: str = Form("")):
    """범례가 달라진 곳을 프로필에 반영한다 — **사람이 눌렀을 때만.**

    `keys` 가 비면 달라진 항목 전부, 아니면 쉼표로 나눈 항목만 갱신한다
    (§7.3 의 삭제 후보와 같은 철학: 기계가 확정하지 않는다).  갱신하지 않은
    항목은 옛 값 그대로 남고, 무엇을 갱신했는지 돌려준다.
    """
    job = db.get_job(CON, job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    if not job["project"]:
        raise HTTPException(400, "이 분석은 프로젝트에 묶여 있지 않아 "
                                 "프로필이 없습니다")
    engine = json.loads(job["engine_json"] or "{}")
    lp = engine.get("legend_profile") or {}
    fresh = lp.get("measured_profile")
    if not fresh:
        raise HTTPException(400, "이 분석에는 프로필과 다른 범례가 없습니다 — "
                                 "갱신할 것이 없습니다")
    stored = legend_profile.load(DATA_DIR, job["project"])
    if stored is None:
        raise HTTPException(404, "이 프로젝트에 저장된 범례 프로필이 없습니다")
    changed = sorted({c["item"] for c in (lp.get("changes") or [])})
    want = [k.strip() for k in keys.split(",") if k.strip()] or changed
    taken = [k for k in want if k in changed]
    if not taken:
        raise HTTPException(400, f"갱신할 항목이 없습니다 (달라진 항목: "
                                 f"{', '.join(changed) or '없음'})")
    merged = json.loads(json.dumps(stored))
    for key in taken:
        merged["items"][key] = fresh["items"][key]
    merged["failed"] = [k for k in legend_profile.ITEMS
                        if (merged["items"].get(k) or {}).get("source")
                        not in legend_profile.DERIVED_SOURCES]
    merged["saved_at"] = time.time()
    meta = dict(merged.get("source_meta") or {})
    meta.update({"adopted_from_job": job_id, "adopted_items": taken,
                 "adopted_revision": job["revision"]})
    merged["source_meta"] = meta
    legend_profile.save(DATA_DIR, job["project"], merged)
    return {"adopted": taken, "kept": [k for k in changed if k not in taken],
            "summary": legend_profile.summary(merged),
            "note": "다음 분석부터 이 값을 씁니다. 이번 분석 결과는 "
                    "바뀌지 않습니다 — 다시 분석해야 반영됩니다"}


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
    "MULTIPLIER_FROM_CONFIG": "Q'ty 승수가 이 도면의 범례가 아니라 프로젝트 설정에서 왔음 — 확인 필요",
    "MULTIPLIER_NOTE_RANGE": "이 장 NOTES 가 유닛을 범위로 적어 몇 개인지 열거하지 않음 — 수량 확인 필요",
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
    # 누가 고쳤나 (13회차 [D]).  인증이 아니라 자기신고다 - 이 앱에는 로그인도
    # 사용자 테이블도 없고, 없는 신원을 지어내지 않는다.  비어 있으면 비어 있는
    # 채로 적고 화면이 "이름 없음" 이라고 쓴다 - 서버가 이름을 만들지 않는다.
    author = " ".join(str(payload.get("author") or "").split())[:60]
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
            basis=before.get("evidence") or {}, author=author,
            pattern_args={"field": field,
                          "ai": (before.get("ai") or {}).get(field),
                          "user": value})
    return {"key": key, "user": user, "review_count": db.review_count(CON, job_id),
            "feedback_count": db.feedback_count(CON, job_id),
            "history": db.row_edit_history(CON, job_id, key)}


@app.get("/jobs/{job_id}/rows/{key}/history")
def row_history(job_id: str, key: str):
    """이 행을 누가 · 언제 · 무엇에서 무엇으로 고쳤나 (13회차 [D]).

    `feedback` 은 편집을 처음부터 전부 남기고 있었다 - 없던 것은 **누구**
    하나뿐이다.  되읽지 않는 표라고 적혀 있었으나, 그것은 "집계해서 규칙을
    고치는 데 쓰지 않는다"는 뜻이고 한 행의 이력을 사람에게 보이는 것은
    그 판단과 어긋나지 않는다.
    """
    if db.get_job(CON, job_id) is None:
        raise HTTPException(404, "no such job")
    return {"key": key, "history": db.row_edit_history(CON, job_id, key)}


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
            # 18회차 — 담는 범위가 설정이다 (`client_form.scope_filter`).
            # `all` 이면 뺀 행이 없고, `sct` 면 11회차대로 SCT 만 담는다.
            # **뺀 행이 조용히 사라지지 않는 것**이 두 모드 공통의 조건이라
            # 세 숫자를 그대로 싣는다.
            "form_scope": result.get("form_scope"),
            "scope_filter": result.get("scope_filter"),
            "held_rows": result.get("held_rows", 0),
            "out_of_scope_rows": result.get("out_of_scope_rows", 0),
            "legacy_no_scope_rows": result.get("legacy_no_scope_rows", 0),
            "note": "unmapped_values lists edits with no column in that "
                    "deliverable's form; they are stored but not written. "
                    "form_scope is what the client form carries: 'all' (every "
                    "row, the default from round 18 - the client asked for the "
                    "vendor-supplied rows too, because SCT still supplies the "
                    "bulk material to install them) or 'sct'. held_rows is how "
                    "many rows were actually left out, which is 0 under 'all'. "
                    "out_of_scope_rows counts rows whose SCOPE is not SCT - a "
                    "count of the supplier, not of what was dropped. "
                    "legacy_no_scope_rows counts rows with no SCOPE at all (an "
                    "analysis from before the column existed) - those are "
                    "always written, and a non-zero number means the drawing "
                    "set should be re-analysed",
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
