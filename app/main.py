"""HTTP surface: upload a PDF, watch it analyse, review the result, ship Excel.

Analysis runs in a background thread with a one-at-a-time queue - it is CPU
bound and holds a whole PDF's vector data in memory, so running two at once
would only make both slower.  Progress is pushed over SSE rather than polled.

The output gate is deliberately narrow: `POST /jobs/{id}/snapshot` is the only
way to make a revision, and `GET /revisions/{id}/excel` is the only way to get
a workbook.  Live rows are never exported.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import sqlite3
import os
import queue
import shutil
import re
import sys
import threading
import time
import traceback
import uuid
import zipfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import (FileResponse, HTMLResponse, JSONResponse,
                               Response, StreamingResponse)
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import DEFAULT_EXCLUDED_CONTENT_TYPES, GZipMiddleware

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import console                                   # noqa: E402

# hotfix54 — 아래 import 와 기동 출력 전에.  cp949 로 돌린 로그에 `—` 하나를 못 써 서버가
# 켜지다 죽던 것 (app/console.py).
console.safe_stdio()

from app import (analysis_proc, audit, axis_overrides, db, excel_out, page_warm,  # noqa: E402
                 global_symbols,
                 lan, legend_profile, markup, paths, pdf_facts, pipeline, revisions, sheet_memo,
                 unit_multipliers, sheet_numbers, title_block_cells, version, voc)
from app.pipeline import CFG                              # noqa: E402

# Two roots, and the difference matters once this is an exe: `paths.resource()`
# is inside the bundle and is deleted when the process ends, `paths.data_dir()`
# is the folder beside the exe that the user keeps.  See app/paths.py.
DATA_DIR = paths.data_dir()
UPLOADS = DATA_DIR / "uploads"
OUTPUTS = DATA_DIR / "outputs"
DB_PATH = DATA_DIR / "app.db"
# hotfix45 — 장 그림(PNG)의 디스크 캐시.  `page_png` 가 요청마다 PDF 를 열어 다시 그리던
# 것(QFE A1 한 장 0.65~0.96초)을 한 번만 그리고 둔다.  파생물이라 지워도 된다 —
# 분석을 지우면 같이 지우고(`delete_job`), 고아는 위생 감사가 센다.
PAGE_CACHE = DATA_DIR / "page_cache"
STATIC = paths.resource("app", "static")

app = FastAPI(title="P&ID extraction")
# hotfix50 — 사내망 모드(`--lan` · PID_LAN=1)에서만 주소를 본다: 루프백 · 사설망 · 이 PC 의
# /16 · PID_ALLOW.  꺼져 있으면(127.0.0.1) 아무것도 하지 않는다 (app/lan.py).
app.add_middleware(lan.Gate)
# hotfix68 — 큰 응답(JSON · JS · CSS)을 압축한다.  QFE `/rows` 13.7MB → 1.2MB (수준 5 · 0.13초) 라
# 사내망으로 대시보드에서 열 때 전송이 열에 하나로 준다.  이미 압축된 것(PNG · zip · xlsx)과
# 진행 소식(SSE)은 건드리지 않는다 — 하는 일이 없거나 소식이 늦게 간다.  수준 9(기본)는 같은
# 크기에 시간만 두 배라 5 로 둔다 (실측 1.23MB/0.125초 ↔ 수준 6 1.15MB/0.138초).
app.add_middleware(
    GZipMiddleware, minimum_size=2048, compresslevel=5,
    exclude_content_types=DEFAULT_EXCLUDED_CONTENT_TYPES + (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/x-zip-compressed", "application/octet-stream"))
CON = db.connect(DB_PATH)


# hotfix74 — 돌발 입력이 서버 내부 오류(500 · 영문 한 줄)로 끝나지 않게 한다 (spike/api_fuzz.py 가 잡은 자리).
@app.exception_handler(revisions.ProjectNameError)
async def _project_name_error(_request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=400)


@app.exception_handler(sqlite3.OperationalError)
async def _db_busy(request, exc):
    """DB 가 잠겨 30초를 기다려도 쓰지 못했다 — 다시 하면 되는 일이라 503 과 그 말로 답한다 (hotfix74)."""
    if "disk is full" in str(exc) or "disk I/O error" in str(exc):
        return _disk_full_response(request, exc)
    if "locked" in str(exc) or "busy" in str(exc):
        print(f"[DB 잠김] {request.method} {request.url.path}: {exc}", flush=True)
        return JSONResponse({"detail": "다른 작업이 데이터를 쓰는 중이라 지금 저장하지 못했습니다 — "
                                       "잠시 뒤 다시 해 주세요 (서버가 두 번 켜져 있지 않은지도 확인해 주세요)"},
                            status_code=503)
    return await _unexpected_error(request, exc)


from app import jsonstore  # noqa: E402


def _disk_full_response(request, exc):
    """서버 디스크가 가득 찼다 — 다시 해도 같다.  무엇을 하면 되는지 말한다 (hotfix74)."""
    print(f"[디스크 가득 참] {request.method} {request.url.path}: {exc}", flush=True)
    try:
        free = shutil.disk_usage(DATA_DIR).free
    except Exception:                                    # noqa: BLE001
        free = None
    left = f" (남은 공간 {free / 1024 / 1024:.0f} MB)" if free is not None else ""
    return JSONResponse({"detail": f"서버 디스크가 가득 차서 저장하지 못했습니다{left} — 관리자에게 알려 "
                                   f"주세요.  첫 화면의 '데이터 위생' 이 정리하면 되찾는 용량을 보여 줍니다."},
                        status_code=507)


@app.exception_handler(jsonstore.StateFileCorrupt)
async def _state_corrupt(request, exc):
    """상태 파일이 깨졌고 백업도 없다 — 문장은 `jsonstore` 가 만든 것 그대로 (hotfix74)."""
    return JSONResponse({"detail": str(exc)}, status_code=500)


@app.exception_handler(Exception)
async def _unexpected_error(request, exc):
    """예상하지 못한 오류 — 사람이 읽을 문장과 **기록 번호**를 준다.  원문은 서버 로그에만 남긴다
    (예외 원문을 화면에 내지 않는 21회차 규칙 그대로)."""
    import traceback
    import uuid
    import errno as _errno
    if isinstance(exc, OSError) and getattr(exc, "errno", None) == _errno.ENOSPC:
        return _disk_full_response(request, exc)
    if isinstance(exc, FileNotFoundError) or type(exc).__name__ == "FileNotFoundError":
        # 원본 PDF 가 사라진 뒤의 장 그림 · 마크업 제안 (hotfix74 · state_chaos K2)
        text = str(getattr(exc, "filename", "") or "")
        if not text and "'" in str(exc):
            text = str(exc).split("'")[-2]                  # pymupdf: "no such file: '<경로>'"
        name = Path(text).name
        return JSONResponse({"detail": f"필요한 파일이 서버에 없습니다 ({name or '이름 모름'}) — 업로드 폴더가 정리됐거나 "
                                       f"옮겨졌습니다.  같은 파일로 새로 분석해 주세요."}, status_code=410)
    ref = uuid.uuid4().hex[:8]
    print(f"[오류 {ref}] {request.method} {request.url.path}\n"
          + "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)), flush=True)
    return JSONResponse({"detail": f"서버가 이 요청을 처리하지 못했습니다 (기록 번호 {ref}). "
                                   f"다시 시도해도 같으면 VOC 로 이 번호와 함께 알려 주세요.",
                         "error_ref": ref}, status_code=500)


def _known_cause(detail: str) -> str:
    """예외 원문에 **환경** 문제가 적혀 있으면 그것을 사람 말로 (hotfix74).  PDF 탓이 아닌데
    `_failure_reason` 이 PDF 를 다시 열어 "사유를 특정하지 못했습니다" 라고만 말하던 자리다."""
    d = detail or ""
    if "No space left on device" in d or "disk is full" in d or "Errno 28" in d:
        return ("서버 디스크가 가득 차서 분석 결과를 쓰지 못했습니다 — 관리자에게 알려 주세요 (첫 화면의 "
                "'데이터 위생' 이 정리하면 되찾는 용량을 보여 줍니다).  공간을 비운 뒤 [다시 분석] 하면 됩니다.")
    if "MemoryError" in d or "Cannot allocate memory" in d:
        return ("분석 중 메모리가 모자랐습니다 — 다른 분석이 끝난 뒤 [다시 분석] 하거나, 같으면 PDF 를 "
                "나눠 올려 주세요.")
    return ""


def _require_source(job) -> Path:
    """그 분석의 원본 파일이 서버에 있어야 하는 요청 — 없으면 410 과 사람 말 (hotfix74).

    돌발상황 시뮬레이션(`spike/state_chaos.py` K2): 업로드 폴더를 누가 정리하면 재분석은 줄을 섰다가
    분석 단계에서 영문 예외로 실패했고, 장 그림·마크업 제안은 일반 500 이었다.
    """
    p = Path(job["pdf_path"] or "")
    if not str(job["pdf_path"] or "") or not p.exists():
        raise HTTPException(410, f"이 분석의 원본 파일({p.name or '이름 없음'})이 서버에 없습니다 — 업로드 폴더가 "
                                 f"정리됐거나 옮겨졌습니다.  결과 목록·편집·Excel 은 그대로 쓸 수 있고, 도면 그림·"
                                 f"재분석·마크업 제안은 같은 파일로 새로 분석해야 합니다.")
    return p


def _int_field(payload, name: str, default=0):
    """본문의 정수 칸 — 글자·소수·목록이 오면 400 과 칸 이름으로 말한다 (hotfix74)."""
    v = (payload or {}).get(name) if isinstance(payload, dict) else None
    if v in (None, ""):
        return default
    try:
        if isinstance(v, bool):
            raise ValueError
        f = float(v)
        if f != f or f in (float("inf"), float("-inf")) or f != int(f):
            raise ValueError
        return int(f)
    except (TypeError, ValueError):
        raise HTTPException(400, f"'{name}' 는 정수여야 합니다 (받은 값: {str(v)[:40]!r})")


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
    from app.engine import dxf_reader
    if dxf_reader.is_dxf_input(pdf):           # 55회차 — DXF 는 장 수
        try:
            return len(dxf_reader.list_inputs(pdf)[0])
        except Exception:                            # noqa: BLE001
            return 0
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


def _running_s(row) -> float:
    """hotfix57 — 지금 돌고 있는 분석이 시작한 지 몇 초인가.  다시 붙은 화면의 경과 표시가
    0 부터 다시 세지 않게 한다.  돌고 있지 않으면 0."""
    try:
        a, st = row["started_at"], row["status"]
    except (KeyError, IndexError):
        return 0.0
    return round(max(0.0, time.time() - a), 1) if a and st == "running" else 0.0


def _pace_history(jobs) -> dict:
    """hotfix58 — 이 서버에서 **끝난 분석이 장당 몇 초 걸렸나** (입력 종류별 중앙값).

    진행률을 단계 수로 세면 쓸모가 없다 — `layout`(도면 치수 재기)이 전체 시간의
    절반을 넘게 쓰는데 그동안 단계 번호는 0 에 머문다 (TC2 실측 55.9%).  그래서
    퍼센트와 남은 시간은 **이 서버가 실제로 걸린 시간**에서 낸다.  지어낸 속도는 없다 —
    끝난 분석이 없으면 비어 있고, 화면이 "아직 예상할 기록이 없다" 고 말한다.
    """
    per = {}
    for j in jobs:
        try:
            a, b, n = j["started_at"], j["finished_at"], j["page_count"]
            kind = j["input_kind"] or "PDF"
        except (KeyError, IndexError):
            continue
        if j["status"] != "done" or not (a and b and n and b > a):
            continue
        per.setdefault(kind, []).append((b - a) / n)
    out = {}
    for kind, xs in per.items():
        xs.sort()
        out[kind] = {"sec_per_page": xs[len(xs) // 2], "n": len(xs)}
    return out


def _run_status(row, pace: dict, queue_ahead: int = 0) -> dict:
    """한 분석의 지금 — 단계 · 장수 · 경과 · 예상 퍼센트 · 남은 시간 (첫 화면과 진행 화면이 같이 읽는다)."""
    kind = row["input_kind"] or "PDF"
    hist = pace.get(kind)
    running = _running_s(row)
    pages = row["page_count"] or 0
    out = {"id": row["id"], "status": row["status"], "message": row["message"] or "",
           "sheets_done": row["sheets_done"] or 0, "sheets_total": row["sheets_total"] or 0,
           "page_count": pages, "running_s": running, "queue_ahead": queue_ahead,
           "percent": None, "eta_s": None, "expected_s": None, "basis": None,
           "over": False}
    if hist and pages:
        expected = hist["sec_per_page"] * pages
        out["expected_s"] = round(expected)
        out["basis"] = {"jobs": hist["n"], "sec_per_page": round(hist["sec_per_page"], 1)}
        if row["status"] == "running":
            out["percent"] = min(99, int(running / expected * 100)) if expected else None
            left = expected - running
            out["eta_s"] = round(left) if left > 0 else None
            out["over"] = left <= 0
    return out


@app.get("/running")
def running_jobs():
    """hotfix58 — 돌고 있거나 기다리는 분석과 그 진행 — 첫 화면의 '최근 분석 이력' 이 읽는다."""
    jobs = db.list_jobs(CON)
    pace = _pace_history(jobs)
    live = [j for j in jobs if j["status"] in ("running", "queued")]
    live.sort(key=lambda j: j["created_at"] or 0)
    out, ahead = [], 0
    for j in live:
        out.append(_run_status(j, pace, queue_ahead=ahead if j["status"] == "queued" else 0))
        ahead += 1
    return {"jobs": out, "pace": pace}


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
        if row["status"] == "cancelled":           # hotfix74 — 줄에 있는 동안 취소된 것
            _cancel_clear(job_id)
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
            # 31회차 — 그 프로젝트에서 **사람이 지정한 승수**가 있으면 넘긴다.
            # 없으면 빈 값이고, 빈 값은 이 기능이 없던 때와 정확히 같다.
            # 파이프라인은 파일을 읽지 않는다 (15회차 프로필과 같은 모양).
            # hotfix56 — 분석은 **다른 프로세스**가 돈다 (`app/analysis_proc.py`).
            # 이 스레드는 진행 소식을 받아 위 `progress` 를 부르기만 하므로 서버가
            # 분석 중에도 대답한다 (대시보드의 `/version` 3초 확인 — 현장 실패).
            result = analysis_proc.run(Path(row["pdf_path"]), progress,
                                      DATA_DIR / "work",
                                      reference=VERIFY_AGAINST,
                                      legend_profile=profile,
                                      unit_multipliers=_user_multipliers(
                                          row["project"]),
                                      sheet_numbers=_user_sheet_numbers(
                                          row["project"]),
                                      title_block_cells=_user_title_block(
                                          row["project"]),
                                      declared_mode=_declared_mode(row))
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
            # hotfix62 — 첫 화면 카드의 도면 사실 (프로젝트 제목 · 개정 날짜 · 최상위 개정).
            # 판정이 아니고 실패해도 분석은 성공이다 — 안 읽힌 칸은 시작 때 다시 채운다.
            try:
                _store_facts(job_id)
            except Exception:                        # noqa: BLE001
                traceback.print_exc()
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
                pipeline.TitleBlockUnreadable,
                pipeline.NoTextLayer,
                pipeline.NoPidSheets) as exc:
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
                            error_detail=(getattr(exc, "child_traceback", "")
                                          or traceback.format_exc()))
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
            # hotfix56 — 자식 프로세스의 트레이스 원문을 붙인다 (부모 쪽 스택만으로는 어디서
            # 났는지 모른다).
            child = getattr(exc, "detail", "") or getattr(exc, "child_traceback", "")
            if child:
                print(child, flush=True)
                detail = child + "\n--- (분석 프로세스를 기다리던 서버 쪽) ---\n" + detail
            stage = _stopped_stage(job_id)          # 덮기 전에 읽는다
            if isinstance(exc, analysis_proc.ChildFailed) and getattr(exc, "process_died", False):
                # hotfix74 — 분석 프로세스가 **결과 없이** 끝났다 (강제 종료 · 메모리 부족).  PDF 를 다시
                # 열어 사유를 찾는 `_failure_reason` 은 "사유를 특정하지 못했습니다" 라고만 말한다 —
                # 아는 것을 말한다 (돌발상황 시뮬레이션 S2).
                reason = str(exc)
            elif _known_cause(detail):
                reason = _known_cause(detail)
            else:
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


def _recover_interrupted() -> dict:
    """hotfix42 — 서버가 꺼졌다 켜질 때 **끊긴 분석**을 정리한다 (QA 시뮬레이션: 분석 중 재시작).

    분석은 이 프로세스의 스레드 하나가 돌리므로 프로세스가 죽으면 `running` 인 job 은 영원히
    `running` 으로 남는다 — 화면은 끝없이 기다리고, 삭제는 "분석 중" 이라 409 로 막힌다.
    `queued` 였던 것은 시작조차 안 했으니 **다시 줄에 세우고**, `running` 이던 것은 **실패**로
    적되 사유와 멈춘 단계를 남긴다 (21회차 실패 기록과 같은 칸 — 화면이 '다시 분석' 을 낸다).
    """
    out = {"requeued": [], "failed": []}
    for row in db.list_jobs(CON):
        if row["status"] == "queued":
            _JOBS.put(row["id"]); out["requeued"].append(row["id"])
        elif row["status"] == "running":
            stage = _stopped_stage(row["id"])
            db.set_progress(CON, row["id"], 0.0,
                            "서버가 다시 시작되어 분석이 끊겼습니다 — 다시 분석하세요", "failed",
                            error_detail="interrupted: the server process restarted while this analysis was running")
            db.set_stopped_stage(CON, row["id"], stage)
            db.mark_finished(CON, row["id"])
            out["failed"].append(row["id"])
    if out["requeued"] or out["failed"]:
        print(f"[시작] 끊긴 분석 정리 — 다시 줄 세움 {len(out['requeued'])} · 실패로 적음 {len(out['failed'])}",
              flush=True)
    return out


# 끊긴 분석 정리와 작업 스레드는 **이 모듈 끝**에서 시작한다 (hotfix74 — 아래 `_start_background`).


# --------------------------------------------------------------------------
# Upload and analysis
# --------------------------------------------------------------------------

@app.post("/jobs")
async def create_job(pdf: list[UploadFile] = File(...), project: str = Form(""),
                     compared_with: str = Form(""), mode: str = Form(""),
                     input_kind: str = Form("")):
    """PDF 하나, 또는 DXF(zip 하나 · 개별 .dxf 여러 장)를 받는다 (55회차).

    `project` 가 오면 그 프로젝트의 다음 리비전이 된다.  프로젝트 없이 올려도
    예전과 똑같이 동작한다 - 리비전은 기존 흐름 위에 얹히는 것이지 그것을
    대체하지 않는다.

    입력 종류는 **파일이 말한다** (`%PDF-` · `PK` · .dxf) — 화면의 선택은 힌트다.
    DXF 여러 장은 zip 하나로 묶어 저장한다: 저장 경로 하나가 곧 분석 하나라는
    옛 구조를 그대로 두기 위해서다.  같은 프로젝트에 PDF 와 DXF 를 섞지 않는다 —
    그 프로젝트의 첫 입력 종류와 다르면 400.
    """
    files = [f for f in (pdf or []) if f is not None and f.filename]
    if not files:
        raise HTTPException(400, "파일이 없습니다")
    blobs = [(_display_name(f.filename), await f.read()) for f in files]
    kind, raw, name = _pack_input(blobs, input_kind)
    if kind == "PDF":
        problem = _pdf_problem(raw)
        if problem:
            raise HTTPException(400, problem)
    revision = ""
    if project:
        try:
            meta = revisions.load_project(DATA_DIR, project)
        except (KeyError, ValueError):
            raise HTTPException(404, f"프로젝트 '{project}' 가 없습니다")
        # hotfix74 — 장부에 아직 오르지 않은 **분석 중·대기 중** 리비전도 센다.  장부는 분석이 끝나야
        # 리비전을 적으므로, Rev.A 가 도는 동안 다음 PDF 를 올리면 둘 다 'Rev.A' 가 됐다 (돌발상황
        # 시뮬레이션 S6 — 현장에서는 "앞 분석이 끝나기 전에 개정본을 올린다" 가 흔하다).
        inflight = _inflight_revisions(project, meta)
        revision = revisions.next_revision(
            dict(meta, revisions=list(meta.get("revisions") or []) + [{"revision": r} for r in inflight]))
        choices = revisions.compare_choices(meta) + inflight
        if compared_with and compared_with not in choices:
            raise HTTPException(400, f"비교 대상 '{compared_with}' 는 이 프로젝트에 "
                                     f"없습니다 (있는 것: {choices})")
        if not compared_with:
            compared_with = inflight[-1] if inflight else revisions.default_compare_target(meta)
    sha = hashlib.sha256(raw).hexdigest()
    job_id = uuid.uuid4().hex[:12]
    # hotfix74 — 같은 파일을 다시 올렸는지 (바이트까지 같다).  막지 않는다 — 다시 분석하고 싶을 수도 있다.
    # 다만 개정본을 올린다며 **직전 판을 또 올리는** 실수는 흔하므로 그 사실을 응답에 싣고 화면이 말한다.
    same = CON.execute("SELECT id, pdf_name, project, revision FROM job WHERE pdf_sha256=? "
                       "AND status != 'cancelled' ORDER BY created_at DESC LIMIT 1", (sha,)).fetchone()
    duplicate_of = ({"job_id": same["id"], "pdf_name": same["pdf_name"], "project": same["project"] or "",
                     "revision": same["revision"] or ""} if same else None)
    if project:
        prev = _project_input_kind(project)
        if prev and prev != kind:
            raise HTTPException(400, f"프로젝트 '{project}' 는 {prev} 로 시작했습니다 — "
                                     f"같은 프로젝트에 {kind} 를 섞지 않습니다")
    UPLOADS.mkdir(parents=True, exist_ok=True)
    path = UPLOADS / f"{job_id}_{_safe_name(name)}"
    path.write_bytes(raw)
    db.create_job(CON, job_id, name, sha, path)
    CON.execute("UPDATE job SET input_kind=? WHERE id=?", (kind, job_id)); CON.commit()
    pages = _count_pages(path)
    db.set_page_count(CON, job_id, pages)
    if project:
        db.set_job_revision(CON, job_id, project, revision, compared_with)
    elif mode:
        # 프로젝트 없이 올린 분석의 선언.  프로젝트가 있으면 장부의 선언을 쓴다.
        if mode not in revisions.MODES:
            raise HTTPException(400, f"mode 는 {revisions.MODES} 중 하나입니다")
        db.set_job_mode(CON, job_id, mode)
    _JOBS.put(job_id)
    return {"job_id": job_id, "pdf_name": name, "sha256": sha,
            "project": project, "revision": revision, "input_kind": kind,
            "compared_with": compared_with, "page_count": pages, "duplicate_of": duplicate_of}


def _inflight_revisions(project: str, meta: dict) -> list:
    """그 프로젝트에서 **줄에 있거나 도는** 분석의 리비전 중 장부에 아직 없는 것 (올린 순서)."""
    known = {r.get("revision") for r in (meta.get("revisions") or [])}
    rows = CON.execute("SELECT revision FROM job WHERE project=? AND status IN ('queued','running') "
                       "AND revision IS NOT NULL AND revision != '' ORDER BY created_at",
                       (project,)).fetchall()
    out = []
    for (rev,) in rows:
        if rev not in known and rev not in out:
            out.append(rev)
    return out


def _probe_or_none(path: Path, page_no: int, *args, **kw) -> dict:
    """`pipeline.probe_point` — DXF 입력이면 기하를 다시 세지 않고 그 사실만 적는다 (55회차)."""
    from app.engine import dxf_reader
    if dxf_reader.is_dxf_input(path):
        return {"input_kind": "DXF", "note": "DXF 입력 — 지점 주변 기하 채집은 이 회차에 없다"}
    return pipeline.probe_point(path, page_no, *args, **kw)


# hotfix74 — zip 폭탄 막이.  분석은 zip 을 메모리에서 통째로 펴므로 풀린 크기가 곧 메모리다.  실측 UAD
# DXF 32장: 압축 12.3MB → 풀면 76.0MB · 한 장 최대 5.4MB · 압축비 약 6배.  한도는 그 20배(1.5GB)와
# 한 파일 압축비 100배 — 정상 도면 묶음은 닿지 않고, 몇 KB 가 수 GB 로 풀리는 파일만 걸린다.
ZIP_MAX_BYTES = 1_500_000_000
ZIP_MAX_RATIO = 100


def _zip_problem(z) -> str:
    total = 0
    for i in z.infolist():
        total += i.file_size
        if i.file_size > 1_000_000 and i.compress_size and i.file_size / i.compress_size > ZIP_MAX_RATIO:
            return (f"zip 안의 {i.filename[:60]} 이(가) {i.file_size / i.compress_size:.0f}배로 풀립니다 — "
                    f"정상 도면 파일이 아닙니다 (압축 폭탄 막이 · 한도 {ZIP_MAX_RATIO}배)")
    if total > ZIP_MAX_BYTES:
        return (f"zip 을 풀면 {total / 1e9:.1f}GB 입니다 — 한 번에 {ZIP_MAX_BYTES / 1e9:.1f}GB 까지 받습니다. "
                f"도면을 나눠서 올려 주세요")
    return ""


def _pack_input(blobs: list, hint: str = "") -> tuple:
    """`(종류, 바이트, 저장 이름)`.  파일이 말하는 것으로 가른다."""
    import zipfile
    if len(blobs) == 1 and blobs[0][1][:5] == b"%PDF-":
        return "PDF", blobs[0][1], blobs[0][0]
    if len(blobs) == 1 and blobs[0][1][:2] == b"PK":
        try:
            with zipfile.ZipFile(io.BytesIO(blobs[0][1])) as z:
                if not any(n.lower().endswith(".dxf") for n in z.namelist()):
                    raise HTTPException(400, "zip 안에 .dxf 가 없습니다")
                problem = _zip_problem(z)
                if problem:
                    raise HTTPException(400, problem)
        except zipfile.BadZipFile:
            raise HTTPException(400, "zip 을 열 수 없습니다")
        return "DXF", blobs[0][1], blobs[0][0]
    dxf = [(n, b) for n, b in blobs if n.lower().endswith(".dxf")]
    if dxf and len(dxf) == len(blobs):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for n, b in dxf:
                z.writestr(n, b)
        stem = Path(dxf[0][0]).stem[:40]
        return "DXF", buf.getvalue(), (f"{stem}_and_{len(dxf)}_dxf.zip" if len(dxf) > 1
                                       else f"{stem}.zip")
    if hint.upper() == "DXF":
        raise HTTPException(400, "DXF 로 골랐는데 .dxf 나 zip 이 아닙니다")
    if len(blobs) == 1 and not blobs[0][1]:
        raise HTTPException(400, "빈 파일입니다 (0 바이트) — 올리는 중에 끊겼을 수 있습니다. 다시 올려 주세요.")
    if len(blobs) > 1:
        raise HTTPException(400, "PDF 는 한 번에 하나만 올립니다 (여러 파일은 DXF 장들일 때만 받습니다).")
    raise HTTPException(400, "PDF 파일이 아닙니다 — PDF 하나 · DXF zip 하나 · .dxf 여러 장만 받습니다.")


# hotfix73 — 저장 파일 이름.  화면에 보이는 이름(`pdf_name`)은 사람이 올린 그대로 두고,
# 디스크에 쓰는 이름만 어느 운영체제에서나 쓸 수 있게 고른다.  비정상 입력 시뮬레이션이
# 잡았다: 한글 200자 이름이 500 을 냈고(파일 이름 255바이트 상한), `a:b*c?"<>|` 는 운영
# 서버(Windows)에서 쓰기가 실패한다.  `..\\..\\` 꼴은 Linux 에서 `Path.name` 이 못 떼어 낸다.
_UNSAFE_NAME = re.compile(r'[\x00-\x1f<>:"/\\|?*]+')
_NAME_BYTES = 150          # job id 접두와 합쳐도 255바이트 아래 (UTF-8 한글 한 자 3바이트)


def _display_name(name: str) -> str:
    """화면에 보일 이름 — 경로 조각과 제어 문자만 뗀다 (어느 쪽 구분자든)."""
    base = re.split(r"[\\/]", name or "")[-1]
    base = re.sub(r"[\x00-\x1f]+", " ", base).strip()
    return base or "upload.pdf"


def _safe_name(name: str) -> str:
    """디스크에 쓸 이름 — 금지 글자는 `_` · 끝의 점·공백 제거 · 바이트 상한 (확장자는 지킨다)."""
    base = _UNSAFE_NAME.sub("_", _display_name(name)).strip(" .") or "upload"
    stem, dot, ext = base.rpartition(".")
    if not dot or len(ext) > 8:
        stem, ext = base, ""
    ext = ("." + ext) if ext else ""
    raw = stem.encode("utf-8")[:_NAME_BYTES - len(ext.encode("utf-8"))]
    stem = raw.decode("utf-8", "ignore").strip(" .") or "upload"
    return stem + ext


def _pdf_problem(raw: bytes) -> str:
    """올린 PDF 를 **열어 보고** 분석이 시작도 못 할 사유를 한 문장으로 (없으면 빈 문자열).

    hotfix73 비정상 입력 시뮬레이션: 암호 걸린 PDF 가 *"파일이 손상되었을 수 있습니다"*,
    중간에 잘린 PDF 가 *"쪽이 하나도 없습니다"* 로 끝났다 — 둘 다 원인이 아니다.  그리고
    둘 다 줄에 들어가 분석 하나를 차지했다.  여기서 막으면 줄도 기록도 남지 않는다.
    """
    import pymupdf
    try:
        doc = pymupdf.open(stream=raw, filetype="pdf")
    except Exception:                                   # noqa: BLE001
        return ("이 파일을 PDF 로 열 수 없습니다 — 손상되었거나 PDF 가 아닙니다. "
                "원본에서 다시 내보내 올려 주세요.")
    try:
        if doc.needs_pass:
            return ("암호가 걸린 PDF 입니다. 암호를 풀어 저장한 PDF 로 올려 주세요 "
                    "(PDF 뷰어에서 '인쇄 → PDF 로 저장' 또는 원본에서 다시 내보내기).")
        if doc.page_count == 0:
            if doc.is_repaired:
                return ("PDF 가 손상돼 쪽을 하나도 읽지 못했습니다 — 파일이 중간에 잘렸을 수 "
                        "있습니다. 다시 내려받거나 원본에서 다시 내보내 올려 주세요.")
            return "이 PDF 에는 쪽이 하나도 없습니다."
    finally:
        doc.close()
    return ""


def _project_input_kind(project: str) -> str:
    """그 프로젝트의 첫 분석이 무엇으로 시작했나 — 섞지 않기 위해 본다."""
    row = CON.execute("SELECT input_kind FROM job WHERE project=? AND input_kind<>'' "
                      "ORDER BY created_at LIMIT 1", (project,)).fetchone()
    return (row["input_kind"] if row else "") or ""


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
    if row["status"] == "queued":
        # hotfix74 — 아직 시작하지 않은 분석은 **지금** 취소로 적는다.  돌발상황 시뮬레이션(S3):
        # 앞 분석이 끝날 때까지 '대기' 로 남아, 그동안 지우려 하면 "분석 중" 이라 409 였다.
        # 작업 스레드는 줄에서 꺼낼 때 취소 표시를 보고 건너뛴다 (그 갈래는 그대로 둔다).
        db.set_progress(CON, job_id, 0.0, "사용자가 분석을 취소했습니다", "cancelled", sheets=(0, 0))
        db.mark_finished(CON, job_id)
        _emit(job_id, {"progress": 0.0, "status": "cancelled", "message": "사용자가 분석을 취소했습니다"})
        return {"job_id": job_id, "cancelling": True, "cancelled": True}
    return {"job_id": job_id, "cancelling": True}


@app.post("/jobs/{job_id}/reanalyse")
def reanalyse(job_id: str):
    """Re-run the engine, keeping every reviewer edit."""
    job = db.get_job(CON, job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    # hotfix74 — 두 창에서 [다시 분석] 을 함께 누르거나 분석 중에 또 누르면 같은 분석이 줄에 두 번 서고,
    # 도는 분석의 상태가 "대기" 로 덮였다.  이미 대기·분석 중이면 그렇다고 말한다.
    if job["status"] in ("queued", "running"):
        raise HTTPException(409, "이미 분석을 기다리거나 분석하는 중입니다 — 끝난 뒤 다시 누르세요")
    _require_source(job)
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


def _store_facts(job_id: str) -> dict:
    """PDF 의 프로젝트 제목 · 장별 개정 날짜 · 최상위 개정을 읽어 job 에 적는다 (hotfix62).

    값은 전부 그 PDF 가 인쇄한 것이고(`app/pdf_facts.py`), 판정에 쓰이지 않는다.  DXF 입력은
    글자층이 없으므로 그렇다고 적는다 (빈 문자열로 두면 시작 때마다 다시 읽으려 한다).
    """
    job = db.get_job(CON, job_id)
    if job is None:
        return {}
    if (job["input_kind"] or "PDF") != "PDF":
        facts = {"kind": job["input_kind"], "error": "DXF 입력은 PDF 글자층이 없습니다"}
    else:
        revs = db.page_revisions(CON, job_id)
        try:
            # hotfix69 — PDF 를 다시 읽는 2~5초를 서버 밖 일꾼이 한다 (그동안 화면 요청이 기다리지 않게)
            facts = page_warm.call(pdf_facts.read, (job["pdf_path"], revs))
        except RuntimeError:
            facts = pdf_facts.read(job["pdf_path"], revs)
        facts["top"] = pdf_facts.top_revision(facts, job["doc_rev"] or "")
    db.set_facts(CON, job_id, facts)
    return facts


def _facts_of(job) -> dict:
    try:
        return json.loads(job["facts_json"] or "{}") if job is not None else {}
    except (TypeError, ValueError):
        return {}


def _backfill_facts() -> None:
    """예전 분석(hotfix62 이전)의 도면 사실을 **재분석 없이** 한 번 채운다 — 분석 하나 2~5초."""
    try:
        todo = [r["id"] for r in CON.execute(
            "SELECT id FROM job WHERE status='done' AND facts_json='' ORDER BY created_at DESC")]
    except Exception:                                # noqa: BLE001
        return
    for jid in todo:
        try:
            _store_facts(jid)
        except Exception as exc:                     # noqa: BLE001
            try:
                db.set_facts(CON, jid, {"error": f"{type(exc).__name__}: {exc}"})
            except Exception:                        # noqa: BLE001
                pass


# 시작 때 한 번, 뒤에서 — 첫 화면은 기다리지 않는다 (안 채워진 카드는 "읽는 중" 이라고 말한다).
# 시작은 모듈 끝 `_start_background` 에서 (hotfix74).


def _output_qty(job_id: str) -> dict:
    """발주처 양식에 실제로 나가는 계기·밸브의 Q'ty 합 (사람이 고친 값 반영).

    나가는 탭과 SCOPE 판정은 Excel 출력과 **같은 것**을 쓴다 (`excel_out.DELIVERABLES` ·
    `in_client_scope`) — 화면이 말하는 수와 파일이 갈리지 않게."""
    tabs = {t for spec in excel_out.DELIVERABLES.values() for t in spec["tabs"]}
    keep = lambda scope: excel_out.in_client_scope({"values": {"scope": scope}})   # noqa: E731
    return db.output_qty(CON, job_id, tabs, keep)


def _json(data) -> Response:
    """큰 목록은 `jsonable_encoder` 를 거치지 않고 바로 적는다 (hotfix45).

    `/rows` 2,041행(13MB)에서 FastAPI 의 기본 변환기가 0.97초, `json.dumps` 가 0.45초였다 —
    값은 전부 `json.loads` 로 읽은 평범한 dict·list 라 변환할 것이 없다.  띄어쓰기도
    뺀다 (같은 내용 · 바이트만 준다).  내용은 같다 — 시험이 두 길의 `json.loads` 를 대조한다.
    """
    return Response(json.dumps(data, ensure_ascii=False, separators=(",", ":")),
                    media_type="application/json")


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
    out["running_s"] = _running_s(row)
    out["sheet_plan"] = _plan(row)
    out.pop("sheet_plan_json", None)
    return out


# --------------------------------------------------------------------------
# 프로젝트와 리비전
# --------------------------------------------------------------------------

@jsonstore.serialized          # hotfix74 — 안정 ID 장부를 읽고-고치고-쓴다 (§7.3: 두 쪽이 겹치면 ID 가 겹친다)
def _run_comparison(job_id: str) -> dict:
    """이 분석을 그 프로젝트의 장부와 맞춘다.  프로젝트가 없으면 아무것도 안 한다."""
    job = db.get_job(CON, job_id)
    if job is None or not job["project"]:
        return {}
    name, revision = job["project"], job["revision"]
    compared = job["compared_with"] or ""
    reg_path = revisions.project_dir(DATA_DIR, name) / "id_registry.json"
    # hotfix38 — **같은 리비전을 다시 대조하면 장부를 대조 전으로 되돌린다.**
    # compare() 는 장부에 쓰면서 간다 (짝지은 기록의 last_anchor·values 갱신 ·
    # 추가 행에 새 ID).  되돌리지 않고 한 번 더 대조하면 직전 대조가 만든 "추가"
    # ID 가 장부에 살아 있어 같은 행이 이번엔 "변경 없음" 이 된다 (실측 — 재대조
    # 결과가 첫 대조와 달랐다).  첫 대조 전의 장부를 리비전 이름으로 떠 두고,
    # 그 리비전을 다시 대조할 때는 거기서 시작한다.  ID 재부여는 없다 —
    # 되돌린 장부에는 이 리비전이 만든 ID 가 아직 없다.
    before = revisions.registry_snapshot_path(reg_path, revision)
    if before.exists():
        registry = revisions.Registry.load(before)
    else:
        registry = revisions.Registry.load(reg_path)
        registry.save(before)
    # 대조가 보는 것은 검토자가 보는 값이다 - 엔진 값에 편집이 얹힌 뒤.
    rows = [dict(r["values"], key=r["key"], tab=r["tab"],
                 drawing_no=r["drawing_no"], page_no=r["page_no"], rect=r["rect"])
            for r in db.merged_rows(CON, job_id, "ALL") if not r["removed"]]
    # hotfix46 — 대조의 열쇠는 태그다.  실행 프로젝트(`effective == "epc"`)만 대조하고
    # 입찰 프로젝트는 대조하지 않는다 (위치로는 비교하지 않는다 · 사용자 확정).  판정은
    # `_mode_facts` 하나 — 화면 띠가 읽는 것과 같은 함수다.
    tagged = _mode_facts(job).get("effective") == "epc"
    result = revisions.compare(rows, registry, revision, compared_with=compared,
                               tagged=tagged)
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
    listed = {p.get("name") for p in projects}
    loose = [_job_public(j) for j in db.list_jobs(CON) if j["id"] not in claimed]
    for j in loose:
        # hotfix74 — 프로젝트에 묶였던 분석인데 그 프로젝트 장부를 읽지 못하면(깨짐 · 지워짐) "묶이지 않은
        # 분석" 으로 떨어진다.  그렇게만 보이면 왜 프로젝트가 사라졌는지 알 길이 없다 — 그 사실을 행에 싣는다.
        pj = (db.get_job(CON, j["id"]) or {})
        pname = pj["project"] if pj and "project" in pj.keys() else ""
        if pname and pname not in listed:
            j["ledger_missing"] = pname
        j["rows"] = db.row_count(CON, j["id"])
        j["edits"] = db.edited_cell_count(CON, j["id"])
        j["last_save"] = db.last_save(CON, j["id"])
        job = db.get_job(CON, j["id"])
        if job is not None and job["status"] == "done":
            j.update(_card_facts(job))
    return {"projects": projects, "loose": loose}


@app.post("/jobs/{job_id}/save")
def save_job(job_id: str, payload: dict = None):
    """hotfix23 — 최종 저장.  편집은 칸마다 이미 DB 에 있다; 이것은 누가 · 언제 이 상태를
    "저장했다" 고 선언했는지를 남긴다 (첫 화면이 프로젝트마다 마지막 것을 보인다).
    이름은 자기신고다 (13회차) — 비우면 비운 채로 적고 화면이 "이름 없음" 이라고 쓴다."""
    job = db.get_job(CON, job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    author = str((payload or {}).get("author") or "")
    return db.record_save(CON, job_id, author)


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
    inflight = _inflight_revisions(meta.get("name") or "", meta) if meta.get("name") else []
    out = {**meta,
           "next_revision": revisions.next_revision(
               dict(meta, revisions=list(meta.get("revisions") or []) + [{"revision": r} for r in inflight])),
           "inflight_revisions": inflight,
           "compare_choices": revisions.compare_choices(meta),
           "default_compare": revisions.default_compare_target(meta)}
    if not deep:
        return out
    revs = []
    for r in out.get("revisions") or []:
        job = db.get_job(CON, r.get("job_id") or "")
        # hotfix42 — 분석이 지워진 리비전은 그렇게 말한다 (링크를 내지 않는다)
        extra = {"missing": job is None}
        if job is not None:
            extra = {"status": job["status"],
                     "analysed_at": job["finished_at"] or job["created_at"],
                     "page_count": job["page_count"],
                     "elapsed_s": _elapsed(job),
                     "fingerprint": job["fingerprint"],
                     "doc_rev": job["doc_rev"],
                     "rows": db.row_count(CON, job["id"]),
                     "edits": db.edited_cell_count(CON, job["id"]),
                     "last_save": db.last_save(CON, job["id"])}
            if job["status"] == "done":
                extra.update(_card_facts(job))
        revs.append({**r, **extra})
    # 최근순.  같은 프로젝트 안에서도 사람이 마지막에 만진 것이 위에 온다.
    revs.sort(key=lambda r: r.get("analysed_at") or 0, reverse=True)
    _verdicts(revs)
    out["revisions"] = revs
    out["latest"] = revs[0] if revs else None
    out.update(_project_card(revs))
    saves = [dict(r["last_save"], revision=r.get("revision"), job_id=r.get("job_id"))
             for r in revs if r.get("last_save")]
    out["last_save"] = max(saves, key=lambda x: x["at"]) if saves else None
    return out


def _card_facts(job) -> dict:
    """첫 화면 카드 한 줄의 도면 사실 (hotfix62) — 프로젝트 제목 · 최상위 개정과 날짜 · 나가는 Q'ty."""
    f = _facts_of(job)
    top = f.get("top") or {}
    return {"pdf_title": f.get("project_title") or "",
            "top_rev": top.get("rev") or "", "top_date": top.get("date") or "",
            "top_iso": top.get("iso") or "", "top_basis": top.get("basis") or "",
            "facts_state": ("pending" if not job["facts_json"] else
                            "error" if f.get("error") else "ok"),
            "facts_error": f.get("error") or "",
            "rev_before": f.get("rev_before") or [],
            "output": _output_qty(job["id"])}


def _verdicts(revs: list) -> None:
    """리비전마다 바로 앞(더 오래된) 리비전과 견준 개정 판정 — 서버 한 곳에서 (hotfix62).

    Rev 가 같으면 **PDF 에 인쇄된 날짜**가 정한다 (사용자 확정).  판정은
    `revisions.compare_document_revision` 하나이고 화면은 결과만 그린다."""
    live = [r for r in revs if r.get("status") == "done"]
    for i, r in enumerate(live):
        prev = live[i + 1] if i + 1 < len(live) else None
        if prev is None:
            continue
        order = pdf_facts.order_pairs({"rev_before": r.get("rev_before")},
                                      {"rev_before": prev.get("rev_before")})
        r["verdict"] = revisions.compare_document_revision(
            r.get("top_rev") or r.get("doc_rev") or "", prev.get("top_rev") or prev.get("doc_rev") or "",
            now_date=r.get("top_iso") or "", before_date=prev.get("top_iso") or "", order=order)


def _project_card(revs: list) -> dict:
    """프로젝트 카드 머리 — **분석된 모든 PDF 중** 최상위 개정 · PDF 의 프로젝트 제목 · 최신 리비전의 Q'ty."""
    live = [r for r in revs if r.get("status") == "done"]
    if not live:
        return {"pdf_title": "", "top": None}
    order = pdf_facts.order_pairs(*({"rev_before": r.get("rev_before")} for r in live))
    best = live[0]
    for r in live[1:]:
        v = revisions.compare_document_revision(
            r.get("top_rev") or r.get("doc_rev") or "", best.get("top_rev") or best.get("doc_rev") or "",
            now_date=r.get("top_iso") or "", before_date=best.get("top_iso") or "", order=order)
        if v["verdict"] == "NEWER":
            best = r
    titles = [r.get("pdf_title") for r in live if r.get("pdf_title")]
    return {"pdf_title": titles[0] if titles else "",
            "top": {"rev": best.get("top_rev") or best.get("doc_rev") or "",
                    "date": best.get("top_date") or "", "basis": best.get("top_basis") or "",
                    "revision": best.get("revision") or "", "job_id": best.get("job_id")},
            "facts_pending": any(r.get("facts_state") == "pending" for r in live)}


@app.patch("/projects/{name}/mode")
def set_project_mode(name: str, mode: str = Form(""), author: str = Form("")):
    """입찰/실행 선언.  작성자와 시각을 함께 적는다 (13회차 자기신고).

    적용은 **다음 분석부터**다 — 이미 돈 분석은 그대로다.  빈 `mode` 는
    선언을 지운다(자동 판정).
    """
    try:
        meta = revisions.set_mode(DATA_DIR, name, mode, author)
    except KeyError:
        raise HTTPException(404, f"프로젝트 '{name}' 가 없습니다")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return _project_public(meta)


@app.get("/jobs/{job_id}/mode")
def job_mode(job_id: str):
    """이 분석이 어느 모드로 돌았나 (선언 · 실측 · 불일치)."""
    job = db.get_job(CON, job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    out = _mode_facts(job)
    out["project"] = job["project"]
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
    # hotfix47 — 짝 없는 기록은 둘로 갈린다: 같은 도면에 새 태그가 섰으면 **변경(이전 태그)**
    # (`state: MODIFIED`), 아니면 삭제 후보.  옛 대조의 payload 에는 `state` 가 없다 → 삭제 후보.
    counts[revisions.DELETED_CANDIDATE] = sum(
        1 for c in cands if not c["confirmed"] and c.get("state") != revisions.MODIFIED)
    counts["MODIFIED_BEFORE"] = sum(
        1 for c in cands if not c["confirmed"] and c.get("state") == revisions.MODIFIED)
    counts[revisions.DELETED] = sum(1 for c in cands if c["confirmed"])
    # hotfix38 — 짝을 태그로 지은 행 수 · hotfix46 — 대조하지 않은 행 수(태그 없음).
    # GEOMETRY 는 hotfix46 이전 판정에만 남아 있다 (위치로는 더 비교하지 않는다).
    matched_by = {"TAG": 0, "GEOMETRY": 0, "NOT_COMPARED": counts.get(revisions.NOT_COMPARED, 0)}
    for st in states.values():
        if st["state"] in (revisions.UNCHANGED, revisions.MODIFIED):
            b = st.get("basis") or "GEOMETRY"
            matched_by[b] = matched_by.get(b, 0) + 1
    # hotfix46 — 이 대조가 무엇으로 섰나.  실행(태그) / 입찰(대조 안 함).  판정은
    # `_mode_facts` 하나이고 `_run_comparison` 이 compare 에 넘긴 것과 같은 식이다.
    compare_basis = "TAG" if _mode_facts(job).get("effective") == "epc" else "NONE"
    label = (f"{job['revision']} vs {job['compared_with']}"
             if job["compared_with"] else
             (f"{job['revision']} (비교 대상 없음)" if job["revision"] else ""))
    # hotfix38 — 도면번호가 바뀐 장 · 한쪽에만 있는 장.  장부(`project.json`)의
    # 이 리비전 항목이 든 사실이고 여기서 다시 판정하지 않는다.
    sheets = {}
    # hotfix39 — **직전 리비전과 다음 리비전의 분석 id.**  화면이 "이전 P&ID 결과 ↔ 현재
    # 결과" 를 오가는 데 쓴다 (사용자 요구).  장부(`project.json`)의 사실이고 여기서
    # 판정하지 않는다: 직전 = 이 분석이 비교한 리비전의 job, 다음 = 이 리비전을 비교
    # 대상으로 삼은 리비전들의 job.
    previous_job = ""
    next_jobs = []
    if job["project"]:
        try:
            meta = revisions.load_project(DATA_DIR, job["project"])
            for r in meta.get("revisions") or []:
                if r.get("job_id") == job_id:
                    sheets = r.get("sheets") or {}
                if job["compared_with"] and r.get("revision") == job["compared_with"]:
                    previous_job = r.get("job_id") or ""
                if job["revision"] and r.get("compared_with") == job["revision"] \
                        and r.get("job_id") and r.get("job_id") != job_id:
                    next_jobs.append({"job_id": r["job_id"], "revision": r.get("revision", "")})
        except (KeyError, ValueError):
            sheets = {}
    return {"project": job["project"], "revision": job["revision"],
            "compared_with": job["compared_with"], "label": label,
            "counts": counts, "matched_by": matched_by, "sheets": sheets,
            "compare_basis": compare_basis,
            "previous_job_id": previous_job, "next_jobs": next_jobs,
            "deleted_candidates": cands}


# --------------------------------------------------------------------------
# 장별 메모 (hotfix63) — 같은 프로젝트의 모든 Rev 에서 이력과 함께.
# ⚠ `/notes/{page}` 는 53회차의 NOTES 판독(도면이 인쇄한 NOTES) 자리라 사람 메모는 `/memo` 다.
# --------------------------------------------------------------------------

def _note_aliases(project: str) -> dict:
    """도면번호 → 같은 장의 다른 번호들 (장부의 `sheets.renumbered` — hotfix38 이 태그로 이은 것)."""
    links: dict = {}
    if not project:
        return links
    try:
        meta = revisions.load_project(DATA_DIR, project)
    except (KeyError, ValueError, OSError):
        return links
    for r in meta.get("revisions") or []:
        for e in ((r.get("sheets") or {}).get("renumbered") or []):
            a, b = str(e.get("before") or ""), str(e.get("now") or "")
            if a and b:
                links.setdefault(a, set()).add(b)
                links.setdefault(b, set()).add(a)
    return links


def _note_keys(project: str, drawing_no: str, page_no: int, aliases: dict) -> list:
    key = sheet_memo.key_of(drawing_no, page_no)
    seen, todo = [key], [key]
    while todo:
        for k in sorted(aliases.get(todo.pop(), ())):
            if k not in seen:
                seen.append(k)
                todo.append(k)
    return seen


def _note_view(e: dict) -> dict:
    return {k: e.get(k) for k in ("seq", "text", "author", "at", "revision", "job_id", "page_no", "drawing_no", "key")}


@app.get("/jobs/{job_id}/memo")
def job_memos(job_id: str):
    """이 분석의 장마다 메모가 몇 판 있고 지금 메모가 무엇인지 (장 목록·도면 아래 판이 읽는다)."""
    job = db.get_job(CON, job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    project = job["project"] or ""
    data = sheet_memo.load(DATA_DIR, project, job_id)
    aliases = _note_aliases(project)
    pages = {}
    for p in db.page_revisions(CON, job_id):
        keys = _note_keys(project, p.get("drawing_no") or "", p["page_no"], aliases)
        es = sheet_memo.entries(data, keys)
        if es:
            pages[str(p["page_no"])] = {"count": len(es), "latest": _note_view(es[-1])}
    return {"scope": "project" if project else "job", "project": project, "pages": pages}


@app.get("/jobs/{job_id}/memo/{page_no}")
def page_memo(job_id: str, page_no: int):
    job = db.get_job(CON, job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    project = job["project"] or ""
    page = next((p for p in db.page_revisions(CON, job_id) if p["page_no"] == page_no), None)
    if page is None:
        raise HTTPException(404, "no such page")
    keys = _note_keys(project, page.get("drawing_no") or "", page_no, _note_aliases(project))
    es = sheet_memo.entries(sheet_memo.load(DATA_DIR, project, job_id), keys)
    return {"scope": "project" if project else "job", "project": project,
            "revision": job["revision"] or "", "drawing_no": page.get("drawing_no") or "",
            "key": keys[0], "keys": keys,
            "current": _note_view(es[-1]) if es else None,
            "history": [_note_view(e) for e in reversed(es)]}


@app.post("/jobs/{job_id}/memo/{page_no}")
def save_page_memo(job_id: str, page_no: int, payload: dict = None):
    """메모 한 판을 쌓는다 (지우지 않는다 — 비워서 저장해도 앞 판은 남는다)."""
    job = db.get_job(CON, job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    page = next((p for p in db.page_revisions(CON, job_id) if p["page_no"] == page_no), None)
    if page is None:
        raise HTTPException(404, "no such page")
    payload = payload or {}
    project = job["project"] or ""
    key = sheet_memo.key_of(page.get("drawing_no") or "", page_no)
    try:
        rec = sheet_memo.add(DATA_DIR, project, job_id, key=key, text=str(payload.get("text") or ""),
                              author=str(payload.get("author") or ""), revision=job["revision"] or "",
                              page_no=page_no, drawing_no=page.get("drawing_no") or "")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return page_memo(job_id, page_no) | {"saved": _note_view(rec)}


@app.get("/jobs/{job_id}/revision/changes.xlsx")
def revision_changes_xlsx(job_id: str):
    """hotfix41 — 개정 변경 내역 Excel (추가 · 수정 · 삭제 · 장 · 요약).

    화면의 개정 열·필터·나란히 보기가 보여 주는 것을 파일로.  판정은 저장된 그대로이고
    (`revision_state` · `deleted_candidate` · 장부 `sheets`) 여기서 다시 하지 않는다.
    비교 대상이 없는 분석(Rev.A)에는 변경이 없으므로 400.
    """
    from app import revision_export
    job = db.get_job(CON, job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    if not job["compared_with"]:
        raise HTTPException(400, "비교 대상이 없는 분석입니다 — 변경 내역이 없습니다")
    info = job_revision(job_id)
    rows = db.merged_rows(CON, job_id, "ALL")
    rev = db.revision_states(CON, job_id)
    for row in rows:
        row["rev"] = rev.get(row["key"], {})
    pages = {r["page_no"]: r["drawing_no"] for r in CON.execute(
        "SELECT page_no, drawing_no FROM pid_page WHERE job_id=?", (job_id,)).fetchall()}
    data = revision_export.build(dict(job), rows, rev, info["deleted_candidates"], pages,
                                 info["sheets"], info["matched_by"])
    name = f"changes_{job['revision'] or 'rev'}_vs_{job['compared_with']}.xlsx".replace(" ", "_")
    return StreamingResponse(io.BytesIO(data),
                             media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": _attachment(name)})


def _attachment(name: str) -> str:
    """`Content-Disposition` — 한글 이름도 500 없이 (hotfix73).  헤더는 latin-1 이라 그대로
    넣으면 인코딩 예외가 난다.  ASCII 대체 이름 + RFC 5987 `filename*` 를 같이 보낸다."""
    from urllib.parse import quote
    ascii_name = name.encode("ascii", "replace").decode("ascii").replace("?", "_").replace('"', "_")
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(name)}"


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


def _drop_page_cache(job_id: str) -> bool:
    if page_warm.running_job() == job_id:       # hotfix69 — 지울 폴더에 미리 그리기가 다시 쓰지 않게
        page_warm.stop()
    d = PAGE_CACHE / job_id
    if not d.is_dir():
        return False
    shutil.rmtree(d, ignore_errors=True)
    return not d.exists()


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
    # hotfix45 — 그 분석의 장 그림 캐시도 지운다 (파생물 · 남기면 고아).
    summary["page_cache_removed"] = _drop_page_cache(job_id)
    # hotfix42 — 장부에도 적는다.  안 적으면 첫 화면이 지워진 분석으로 가는 링크를 계속 내고
    # (누르면 "no such job"), 다음 업로드의 기본 비교 대상이 지워진 리비전이 된다 (QA 시뮬레이션).
    if summary.get("project") and summary.get("revision"):
        summary["ledger_marked"] = revisions.mark_revision_deleted(
            DATA_DIR, summary["project"], job_id, author.strip()) is not None
    return summary


# 프로젝트 통째 삭제 (46회차 [C]).
#
# 17회차는 이 길을 **일부러 만들지 않았다** — 프로젝트 폴더에 안정 ID 장부가
# 있고 그것이 사라지면 같은 이름으로 다시 만든 프로젝트가 번호를 1부터 다시
# 내어 §7.3 이 깨지기 때문이다.  사용자가 "첫 화면에서 완전히 사라지게" 를
# 요구했으므로 **그 불변식을 지키면서** 연다:
#
#   · 분석·행·편집·마크업·리비전·업로드 PDF·출력 폴더는 지운다
#   · **안정 ID 장부만 `projects/_deleted/<이름>-<시각>/` 로 옮긴다**
#     (그 폴더에는 `project.json` 이 없으므로 첫 화면에 보이지 않는다)
#   · 같은 이름으로 다시 만들면 그 장부를 **이어받는다**
#   · 누가 언제 지웠는지는 분석마다 `deletion_log` 에 남는다
@app.get("/projects/{name}/deletion_preview")
def project_deletion_preview(name: str):
    """지우기 전에 보여 줄 것.  **아무것도 바꾸지 않는다.**"""
    try:
        revisions.load_project(DATA_DIR, name)
    except KeyError:
        raise HTTPException(404, "no such project")
    pre = db.project_deletion_preview(CON, revisions.safe_name(name))
    pre["id_registry_kept"] = True
    pre["note"] = ("안정 ID 장부는 남깁니다 — 같은 이름으로 다시 만들어도 번호가 "
                   "겹치지 않게 하기 위해서입니다 (§7.3). 그 밖의 것은 전부 "
                   "지워지고 되돌릴 수 없습니다.")
    return pre


@app.delete("/projects/{name}")
def delete_project(name: str, author: str = Form(""), confirm: str = Form("")):
    """프로젝트를 지운다.  `confirm` 이 프로젝트 이름과 같아야 한다."""
    try:
        revisions.load_project(DATA_DIR, name)
    except KeyError:
        raise HTTPException(404, "no such project")
    safe = revisions.safe_name(name)
    if confirm.strip() != safe:
        raise HTTPException(
            400, "확인 값이 프로젝트 이름과 다릅니다 — 실수로 지워지지 않게 "
                 "하는 장치입니다")
    running = [r["id"] for r in db.list_jobs(CON)
               if (r["project"] or "") == safe
               and r["status"] in ("queued", "running")]
    if running:
        raise HTTPException(409, "분석 중인 것이 있습니다. 먼저 취소하세요")
    summary = db.delete_project(CON, safe, author=author.strip())
    # 업로드 PDF — 다른 분석이 같은 파일을 가리키면 남긴다 (분석 삭제와 같은 규칙).
    removed = []
    for path in summary["uploads_to_remove"]:
        p = Path(path)
        try:
            if p.exists() and p.parent.resolve() == UPLOADS.resolve():
                p.unlink()
                removed.append(p.name)
        except OSError:
            pass
    summary["uploads_removed"] = removed
    # 출력 폴더 — 이제 어느 리비전도 가리키지 않으므로 고아가 된다.  남기면
    # [B] 위생 경고가 그대로 뜬다.
    gone = []
    outs = DATA_DIR / "outputs"
    live = {f"rev{r[0]}" for r in CON.execute("SELECT id FROM revision")}
    if outs.is_dir():
        for d in sorted(outs.iterdir()):
            if d.is_dir() and audit.REV_DIR.match(d.name) and d.name not in live:
                shutil.rmtree(d, ignore_errors=True)
                gone.append(d.name)
    summary["outputs_removed"] = gone
    # hotfix45 — 지운 분석들의 장 그림 캐시
    summary["page_cache_removed"] = [j["job_id"] for j in summary["jobs"]
                                     if _drop_page_cache(j["job_id"])]
    summary["registry"] = revisions.bury_project(DATA_DIR, safe,
                                                 author=author.strip())
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

# --------------------------------------------------------------------------
# 유닛 승수 — 도면이 말하지 않을 때 **사람이 한 번 답하는 자리** (31회차)
# --------------------------------------------------------------------------
def _declared_mode(row) -> str:
    """이 분석의 입찰/실행 선언 — 프로젝트 장부가 먼저, 없으면 job 의 칸.

    둘 다 비면 `""` 이고, 그러면 파이프라인이 도면 실측으로 정한다 (선언을
    강제하지 않는다 — 지금까지 쓰던 사람이 막히면 안 된다).
    """
    project = row["project"] if row else ""
    if project:
        try:
            return revisions.declared_mode(revisions.load_project(DATA_DIR, project))
        except (KeyError, ValueError):
            return ""
    try:
        return str(row["mode"] or "")
    except (KeyError, IndexError):
        return ""


def _mode_facts(job) -> dict:
    """이 분석이 어느 모드로 돌았나 — **화면에서 이 판정을 하는 곳은 여기 하나.**"""
    engine = json.loads(job["engine_json"] or "{}") if job else {}
    t = engine.get("evidence_tier") or {}
    declared = t.get("declared") if "declared" in t else _declared_mode(job)
    measured = t.get("measured") or ("epc" if t.get("tier") == 1 else "bid" if t else "")
    effective = t.get("effective") or declared or measured
    conflict = t.get("conflict") or ""
    pages = t.get("pages_tagged") or []
    words = {"bid": "입찰", "epc": "실행", "": "기록 없음"}
    if not t:
        line = "이 분석은 입찰/실행 모드가 생기기 전에 돌았습니다 — 기록이 없습니다"
    elif conflict == "declared_bid_tags_found":
        line = (f"입찰로 고르셨는데 {len(pages)}장에서 태그가 보입니다 "
                f"(태그 후보 {t.get('tags_available', 0)}행). 선언대로 태그 없이 "
                f"읽었습니다 — 실측대로 가려면 프로젝트 모드를 실행으로 바꾸고 다시 분석하세요")
    elif conflict == "declared_epc_no_tags":
        line = ("실행으로 고르셨는데 태그를 찾지 못했습니다. 범례·NOTES·기하로 "
                "식별합니다 (2급)")
    elif declared:
        line = (f"{words[declared]}(선언)으로 읽었습니다 — 실측도 같습니다"
                + (f" (태그 {len(pages)}장 · {t.get('tagged_rows', 0)}행)" if effective == "epc" else ""))
    else:
        line = (f"자동 판정: {words[measured]}"
                + (f" (태그 {len(pages)}장 · {t.get('tagged_rows', 0)}행)" if measured == "epc"
                   else " (태그가 인쇄된 장이 없습니다)"))
    # hotfix39 — 태그 문법 한 줄.  배운 사실만 적는다 (자리 · 코드→변수 · 교차 검증 · 증거 행).
    tg = engine.get("tag_grammar") or {}
    g = tg.get("grammar") or {}
    if tg.get("enabled") and g.get("learned"):
        top = sorted(g.get("majority", {}).items(), key=lambda kv: -kv[1]["n"])[:6]
        line += (" · 태그 문법: " + " ".join(f"{c}→{m['head']}({m['n']})" for c, m in top)
                 + f" · 어긋남 {len(tg.get('mismatch') or [])}행 · 태그가 증거인 행 {len(tg.get('evidence_rows') or [])}")
    return {"declared": declared or "", "measured": measured, "effective": effective,
            "conflict": conflict, "pages_tagged": pages,
            "tag_grammar": tg,
            "tagged_rows": t.get("tagged_rows", 0), "tags_available": t.get("tags_available", 0),
            "line": line, "recorded": bool(t)}


def _user_sheet_numbers(project: str) -> dict:
    """파이프라인에 넘길 모양 `{"table": {장: 도면번호}, "who": ..., "when": ...}`.

    **읽는 곳은 여기 하나다** (31회차 `_user_multipliers` 와 같은 규율).
    프로젝트에 안 묶인 분석이면 빈 값이고, 빈 값은 이 기능이 없던 때와
    **정확히 같다** — 도면에서 읽힌 장은 어차피 덮지 않는다.
    """
    project = (project or "").strip()
    if not project:
        return {}
    data = sheet_numbers.load(DATA_DIR, project)
    table = sheet_numbers.table(DATA_DIR, project)
    who, when = {}, {}
    for page, rec in (data.get("sheets") or {}).items():
        try:
            no = int(page)
        except (TypeError, ValueError):
            continue
        if no not in table:
            continue
        bits = [rec.get("author") or "이름 없음"]
        if rec.get("note"):
            bits.append(rec["note"])
        who[no] = " · ".join(bits)
        when[no] = (rec.get("set_at") or "")[:10]
    return {"table": table, "who": who, "when": when}


def _user_multipliers(project: str) -> dict:
    """파이프라인에 넘길 모양 `{"table": {유닛: 배수}, "who": {유닛: "이름 · 메모"}}`.

    **읽는 곳은 여기 하나다.**  프로젝트에 안 묶인 분석이면 빈 값이고,
    빈 값은 이 기능이 없던 때와 **정확히 같다**.
    """
    project = (project or "").strip()
    if not project:
        return {}
    data = unit_multipliers.load(DATA_DIR, project)
    table = unit_multipliers.table(DATA_DIR, project)
    who = {}
    for unit, rec in (data.get("units") or {}).items():
        if unit not in table:
            continue
        bits = [rec.get("author") or "이름 없음", rec.get("set_at", "")[:10]]
        if rec.get("note"):
            bits.append(rec["note"])
        who[unit] = " · ".join(b for b in bits if b)
    return {"table": table, "who": who}


def _multiplier_targets(job_id: str) -> dict:
    """이 분석에서 **승수를 묻고 있는 행**을 유닛코드로 묶는다.

    행마다 묻지 않는다 — SADARA 는 유닛 `10` 하나에 82행이다.
    """
    job = db.get_job(CON, job_id)
    if not job:
        raise HTTPException(404, "no such job")
    # 유닛코드는 **도면번호에서 나온다** — 엔진이 쓰는 그 함수를 그대로 쓴다
    # (`engine_json` 은 타이틀블록을 담지 않는다.  두 벌을 두면 언젠가 갈린다).
    pages = {int(p["page_no"]): (pipeline.tb.parse_unit_code(p["drawing_no"]) or "")
             for p in db.page_revisions(CON, job_id)}
    rows = db.merged_rows_cached(CON, job_id)        # 읽기만 한다 (hotfix45)
    want = {"MULTIPLIER_UNDEFINED", "MULTIPLIER_FROM_CONFIG", "MULTIPLIER_DEFAULT_ONE",
            "MULTIPLIER_NOTE_RANGE", unit_multipliers.REVIEW_CODE}
    groups: dict = {}
    for r in rows:
        ev = r.get("evidence") or {}
        if isinstance(ev, str):
            ev = json.loads(ev or "{}")
        codes = set(ev.get("review_codes") or [])
        if not (codes & want):
            continue
        unit = pages.get(r["page_no"], "")
        g = groups.setdefault(unit, {"unit": unit, "rows": 0, "pages": set(),
                                     "codes": set(), "qty_now": 0})
        g["rows"] += 1
        g["pages"].add(r["page_no"])
        g["codes"] |= (codes & want)
        try:
            g["qty_now"] += int((r.get("values") or {}).get("qty") or 0)
        except (TypeError, ValueError):
            pass
    saved = unit_multipliers.load(DATA_DIR, job["project"] or "")
    out = []
    for unit, g in sorted(groups.items()):
        rec = (saved.get("units") or {}).get(unit) or {}
        out.append({"unit": unit, "rows": g["rows"],
                    "pages": sorted(g["pages"]),
                    "sheets": len(g["pages"]),
                    "codes": sorted(g["codes"]),
                    "qty_now": g["qty_now"],
                    "set": rec or None})
    return {"project": job["project"] or "", "groups": out,
            "enabled": saved.get("enabled", True),
            "note": "범례나 그 장 NOTES 가 답한 유닛은 여기 없습니다 — "
                    "사람은 도면을 이기지 않습니다."}


@app.get("/jobs/{job_id}/multipliers")
def multiplier_targets(job_id: str):
    return _multiplier_targets(job_id)


@app.post("/jobs/{job_id}/multipliers")
def multiplier_set(job_id: str, unit: str = Form(...),
                   multiplier: int = Form(...), author: str = Form(""),
                   note: str = Form("")):
    """한 유닛코드의 승수를 지정한다.  **다시 분석해야 반영된다.**

    지금 결과를 그 자리에서 고치지 않는 이유는 15회차 `adopt_legend_profile`
    과 같다 — 수량은 검출 결과이지 편집 칸이 아니고, 바꿨다고 말하면서
    바꾸지 않으면 화면이 거짓말을 한다.
    """
    job = db.get_job(CON, job_id)
    if not job:
        raise HTTPException(404, "no such job")
    try:
        rec = unit_multipliers.set_unit(DATA_DIR, job["project"] or "",
                                        unit=unit, multiplier=multiplier,
                                        author=author, note=note, job_id=job_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"unit": unit, "record": rec,
            "targets": _multiplier_targets(job_id),
            "applies": "다시 분석하면 이 유닛의 모든 행에 적용됩니다"}


@app.delete("/jobs/{job_id}/multipliers/{unit}")
def multiplier_clear(job_id: str, unit: str):
    """되돌린다 — 지운 뒤에는 지정하지 않았던 때와 같아진다."""
    job = db.get_job(CON, job_id)
    if not job:
        raise HTTPException(404, "no such job")
    if not unit_multipliers.clear_unit(DATA_DIR, job["project"] or "", unit):
        raise HTTPException(404, "no such unit")
    return {"cleared": unit, "targets": _multiplier_targets(job_id)}


def _sheet_number_targets(job_id: str) -> dict:
    """도면번호가 비어 있는 장 — **사람이 적을 자리**만 낸다 (45회차).

    읽힌 장은 목록에 넣지 않는다.  사람은 도면을 이기지 않으므로 적어도
    쓰이지 않고, 자리를 내면 "고칠 수 있다" 는 거짓말이 된다.
    """
    job = db.get_job(CON, job_id)
    if not job:
        raise HTTPException(404, "no such job")
    engine = json.loads(job["engine_json"] or "{}")
    # hotfix33 — 장 목록은 `pid_page` 표에서 읽는다 (`/pages` 와 같은 자리).  45회차는
    # `engine_json["pages"]` 를 읽었는데 그 열쇠는 `store_result` 화이트리스트에 **없어**
    # 실제 분석에서는 언제나 빈 목록이었다 — 화면 자기검증이 잡았다 (38회차 `evidence_tier`
    # · 53회차 `unit_notes` 와 같은 결함).  표에 없는 옛 분석은 engine_json 으로 되돌아간다.
    pages = [dict(r) for r in CON.execute(
        "SELECT page_no, drawing_no, page_kind FROM pid_page WHERE job_id=? ORDER BY page_no",
        (job_id,)).fetchall()] or (engine.get("pages") or [])
    saved = sheet_numbers.load(DATA_DIR, job["project"] or "")
    applied = (engine.get("user_sheet_numbers") or {}).get("table") or {}
    out = []
    for p in pages:
        no = int(p.get("page_no") or 0)
        if p.get("drawing_no") and str(no) not in {str(k) for k in applied}:
            continue
        if p.get("drawing_no") and str(no) in {str(k) for k in applied}:
            pass                      # 사람이 적어 채워진 장 — 되돌릴 수 있게 낸다
        rec = (saved.get("sheets") or {}).get(str(no)) or {}
        out.append({"page_no": no,
                    "drawing_no": p.get("drawing_no") or "",
                    "page_kind": p.get("page_kind") or "",
                    "from_user": str(no) in {str(k) for k in applied},
                    "set": rec or None})
    return {"project": job["project"] or "", "sheets": out,
            "enabled": saved.get("enabled", True),
            "note": "도면에서 읽힌 장은 여기 없습니다 — 사람은 도면을 이기지 "
                    "않습니다.  적은 값은 **다시 분석해야** 반영됩니다."}


def _user_title_block(project: str) -> dict:
    """파이프라인에 넘길 사람이 그은 타이틀블록 칸.  **읽는 곳은 여기 하나다** — 프로젝트에
    안 묶인 분석이면 빈 값이고, 빈 값은 이 기능이 없던 때와 정확히 같다."""
    project = (project or "").strip()
    if not project:
        return {}
    return title_block_cells.cells(DATA_DIR, project)


_TB_PAGES: dict = {}          # job_id -> pages (낱말만 · 한 job)


def _tb_pages(job):
    """그 PDF 의 낱말 — 칸 지정 미리보기가 장마다 읽는다.  한 job 만 든다."""
    import pidcache
    jid = job["id"]
    if _TB_PAGES.get("id") != jid:
        _doc, pages = pidcache.load_pages(job["pdf_path"])
        _TB_PAGES.clear()
        _TB_PAGES.update({"id": jid, "doc": _doc, "pages": pages})
    return _TB_PAGES["pages"]


def _tb_sizes(job):
    """쪽 크기만 — 칸 지정 화면을 여는 데는 낱말이 필요 없다 (hotfix73 · QA 실측 6.2초 → 수십 ms).
    낱말을 이미 읽어 둔 job 이면 그것을 쓴다.  크기는 `PageCache` 와 같은 표시 좌표(회전 반영)."""
    if _TB_PAGES.get("id") == job["id"]:
        return _TB_PAGES["pages"]
    import types
    import pymupdf
    doc = pymupdf.open(job["pdf_path"])
    try:
        return [types.SimpleNamespace(page_no=i + 1, width=float(pg.rect.width),
                                      height=float(pg.rect.height))
                for i, pg in enumerate(doc)]
    finally:
        doc.close()


def _tb_form(pages):
    """다수 크기의 장과 크기 표 — `derive_layout._form_pages` 와 같은 정의."""
    import derive_layout
    form, sizes = derive_layout._form_pages(pages)
    return form, [{"size": [k[0], k[1]], "pages": v} for k, v in sorted(sizes.items(), key=lambda t: -t[1])]


def _tb_read(pages, rect, codes_only=False):
    """장마다 그 사각형 안 글자 (줄 순 · x 순).  코드 낱말만 볼 수도 있다."""
    import derive_layout
    from pidcache import in_region
    out = []
    for pc in pages:
        ws = [(r, t) for r, t in pc.words if in_region(r, rect)
              and (not codes_only or derive_layout._code_shape(t))]
        ws.sort(key=lambda w: (round(w[0].y0), w[0].x0))
        out.append({"page_no": pc.page_no, "text": " ".join(t for _r, t in ws)})
    return out


@app.get("/jobs/{job_id}/titleblock")
def titleblock_state(job_id: str):
    """칸 지정 화면이 읽는 것 하나 — 저장된 칸 · 쪽 크기 · 다수 크기의 첫 장 · 이번 분석이
    도면에서 답한 칸."""
    job = db.get_job(CON, job_id)
    if not job:
        raise HTTPException(404, "no such job")
    from app.engine import dxf_reader
    if dxf_reader.is_dxf_input(Path(job["pdf_path"])):
        return {"supported": False, "note": "DXF 는 타이틀 캡션 아래 칸을 읽으므로 이 지정이 없습니다"}
    pages = _tb_sizes(job)
    form, sizes = _tb_form(pages)
    engine = json.loads(job["engine_json"] or "{}") if "engine_json" in job.keys() and job["engine_json"] else {}
    lay = (engine.get("applied_rules") or {}).get("layout") or {}
    derived = {m["key"].split(".", 1)[1]: m["now"] for m in (lay.get("moved") or [])
               if m.get("key", "").startswith("title_block.") and m.get("source") != "USER"
               and m["key"].split(".", 1)[1] in title_block_cells.CELLS}
    saved = title_block_cells.load(DATA_DIR, job["project"] or "")
    return {"supported": True, "project": job["project"] or "",
            "page_count": len(pages), "sizes": sizes,
            "form_size": [round(float(form[0].width), 1), round(float(form[0].height), 1)],
            "form_pages": [pc.page_no for pc in form],
            "suggested_page": form[0].page_no,
            "saved": saved if saved.get("cells") else None,
            "derived": derived,
            "note": "그은 칸은 프로젝트에 저장되고 **다시 분석해야** 반영됩니다.  좌표는 그은 장의 "
                    "종이 크기에서만 쓰입니다."}


@app.post("/jobs/{job_id}/titleblock/preview")
def titleblock_preview(job_id: str, payload: dict):
    """그은 사각형을 같은 크기의 모든 장에서 읽어 본다 — 저장 전에 무엇이 읽히는지 보인다."""
    job = db.get_job(CON, job_id)
    if not job:
        raise HTTPException(404, "no such job")
    try:
        cell = str(payload.get("cell"))
        rect = tuple(float(v) for v in payload.get("rect"))
        assert len(rect) == 4 and cell in title_block_cells.CELLS
    except Exception:                                    # noqa: BLE001
        raise HTTPException(400, "cell 과 rect [x0,y0,x1,y1] 가 필요합니다")
    import derive_layout
    pages = _tb_pages(job)
    form, _sizes = _tb_form(pages)
    codes = cell == "dwg_no_region"
    got = _tb_read(form, rect, codes_only=codes)
    read = [g for g in got if g["text"]]
    out = {"cell": cell, "pages": got, "read": len(read), "total": len(form),
           "distinct": len({g["text"] for g in read})}
    if codes:
        shapes = derive_layout._drawing_no_shapes(form, rect)
        out["pattern"] = derive_layout._drawing_no_pattern(shapes)
        out["shapes"] = {k: len(v) for k, v in shapes.items()}
    return out


@app.post("/jobs/{job_id}/titleblock")
def titleblock_save(job_id: str, payload: dict):
    """칸을 프로젝트에 적는다.  **다시 분석해야 반영된다.**"""
    job = db.get_job(CON, job_id)
    if not job:
        raise HTTPException(404, "no such job")
    pages = _tb_sizes(job)
    form, _sizes = _tb_form(pages)
    try:
        data = title_block_cells.set_cells(
            DATA_DIR, job["project"] or "", cells_in=payload.get("cells") or {},
            size=[form[0].width, form[0].height], page_no=_int_field(payload, "page_no"),
            author=payload.get("author") or "", note=payload.get("note") or "", job_id=job_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"saved": data, "applies": "다시 분석하면 이 칸으로 타이틀블록을 읽습니다"}


@app.delete("/jobs/{job_id}/titleblock")
def titleblock_clear(job_id: str):
    job = db.get_job(CON, job_id)
    if not job:
        raise HTTPException(404, "no such job")
    return {"cleared": title_block_cells.clear(DATA_DIR, job["project"] or "")}


@app.get("/jobs/{job_id}/sheet_numbers")
def sheet_number_targets(job_id: str):
    return _sheet_number_targets(job_id)


@app.post("/jobs/{job_id}/sheet_numbers")
def sheet_number_set(job_id: str, page: int = Form(...),
                     drawing_no: str = Form(...), author: str = Form(""),
                     note: str = Form("")):
    """한 장의 도면번호를 적는다.  **다시 분석해야 반영된다.**"""
    job = db.get_job(CON, job_id)
    if not job:
        raise HTTPException(404, "no such job")
    try:
        rec = sheet_numbers.set_sheet(DATA_DIR, job["project"] or "",
                                      page=page, drawing_no=drawing_no,
                                      author=author, note=note, job_id=job_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"page": page, "record": rec,
            "targets": _sheet_number_targets(job_id),
            "applies": "다시 분석하면 이 장이 분석 대상이 됩니다"}


@app.delete("/jobs/{job_id}/sheet_numbers/{page}")
def sheet_number_clear(job_id: str, page: int):
    """되돌린다 — 지운 뒤에는 적지 않았던 때와 같아진다."""
    job = db.get_job(CON, job_id)
    if not job:
        raise HTTPException(404, "no such job")
    if not sheet_numbers.clear_sheet(DATA_DIR, job["project"] or "", page):
        raise HTTPException(404, "no such sheet")
    return {"cleared": page, "targets": _sheet_number_targets(job_id)}


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


@app.get("/jobs/{job_id}/notes/{page_no}")
def sheet_notes(job_id: str, page_no: int):
    """그 장의 NOTES 에서 **무엇을 읽었고 그것을 어떻게 해석했는가** (53회차 [E]).

    8차 피드백 s3 원문: *"식별 값도 표기한다.  해석된 내용을 표기 한다."*
    27회차가 이 사실을 이미 읽어 `result["unit_notes"]` 에 담고 있었는데
    **저장 화이트리스트에 없어 화면이 볼 수 없었다** — 38회차 [B] 의
    `evidence_tier` 와 같은 결함이다.

    돌려주는 것은 사실 셋이고 문장은 화면이 만든다 (15회차 규율):
      `text`   도면이 인쇄한 원문
      `units`  거기서 읽은 유닛 표기 (식별 값)
      `factor` 그 개수 = 이 장의 수량 배수 (해석)
    그리고 그 해석을 **실제로 썼는지** — 범례 승수표가 답한 문서에서는
    노트를 쓰지 않는다 (§9 읽는 순서: ①범례 → ②NOTES).  `counted` 가 그것이다.
    """
    row = db.get_job(CON, job_id)
    if row is None:
        raise HTTPException(404, "no such job")
    eng = json.loads(row["engine_json"] or "{}")
    if "unit_notes" not in eng:
        return {"known": False,
                "note": "이 분석은 NOTES 판독을 저장하기 전(53회차 이전)의 "
                        "것입니다. 다시 분석하면 보입니다."}
    got = (eng["unit_notes"] or {}).get(str(page_no)) \
        or (eng["unit_notes"] or {}).get(page_no)
    if not got:
        return {"known": True, "found": False,
                "note": "이 장의 NOTES 에는 '이 도면이 유닛 몇 개에 같이 쓰이는가' "
                        "를 말하는 문단이 없습니다."}
    # ★ 읽은 것과 **쓴 것**은 다르다.  `unit_notes.counted` 는 *그 문단에서 수를
    # 셌다* 는 뜻이지 *그 값을 수량에 썼다* 가 아니다 — §9 읽는 순서가
    # ①범례 → ②NOTES 라서, 범례 승수표가 답한 문서(AL NOUF1)는 노트를 읽고도
    # 쓰지 않는다.  둘을 같이 적으면 화면이 사실과 다른 말을 한다 (53회차
    # 자기검증이 잡았다).  **쓴 것은 행이 말한다** — `qty_basis` 에 `NOTES:` 가
    # 들어가면 그 장은 노트로 곱한 것이다 (`_note_factor` 가 그때만 그렇게 적는다).
    used = any("NOTES:" in str((r.get("evidence") or {}).get("qty_basis") or "")
               for r in db.merged_rows(CON, job_id)
               if r.get("page_no") == page_no)
    return {"known": True, "found": True,
            "text": got.get("text") or "",
            "units": got.get("units") or [],
            "factor": got.get("units_count"),
            "counted": bool(got.get("counted")),
            "used": used,
            "source": (eng.get("multipliers") or {}).get("source") or ""}


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
                        "stopped_stage": row["stopped_stage"],
                        "running_s": _running_s(row),
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

# hotfix68 — `/rows` 응답 본문의 메모.  같은 결과를 두 창(도면 · 목록)이 따로 열고, 창 사이 연동이
# 바뀐 행만 다시 받으므로, **바뀐 것이 없는 한** 같은 본문을 다시 만들 이유가 없다 (QFE 0.3초 +
# 압축 0.13초).  열쇠의 도장은 `merged_rows_cached` 와 같은 `db._db_stamp` 라 편집 한 칸 · 다른
# 연결의 커밋에도 다시 만든다.  압축본은 요청이 gzip 을 받을 때 한 번 만들어 둔다 (미들웨어는
# `Content-Encoding` 이 이미 있으면 다시 압축하지 않는다).
_ROWS_BODY: dict = {}

# hotfix69 — 목록이 처음 받는 행에서 뺄 근거 칸.  셋이 `/rows` 13.8MB 의 7.4MB 다 (QFE Rev.B 실측:
# candidates 4.6MB · trace 2.0MB · axis 0.8MB) — 화면은 이 셋을 **고른 행 하나**에만 쓴다 (근거 패널의 후보 ·
# From/To · 판정축, 도면의 경로 선).  그래서 목록은 `?slim=1` 로 빼고 받고, 행을 고를 때 그 행만
# `?keys=` 로 온전히 받는다 (app.js `ensureFull`).  행에 `_slim: 1` 이 붙어 화면이 그것을 안다.
SLIM_DROP = ("candidates", "trace", "axis")


def _slim_row(row: dict) -> dict:
    ev = row.get("evidence")
    if isinstance(ev, dict) and any(k in ev for k in SLIM_DROP):
        row["evidence"] = {k: v for k, v in ev.items() if k not in SLIM_DROP}
    row["_slim"] = 1
    return row


def _rows_payload(job_id: str, tab: str, keys: set | None) -> list:
    if keys is not None and len(keys) <= 2000:
        # hotfix74 — 몇 행이면 그 행만 읽는다 (편집이 메모를 풀 때마다 전체를 파싱하던 것 · 부하 시뮬레이션)
        out = db.merged_rows_by_keys(CON, job_id, sorted(keys), tab)
    else:
        src = db.merged_rows_cached(CON, job_id, tab)
        out = [dict(r) for r in src if keys is None or r["key"] in keys]
    states = db.review_states(CON, job_id)
    rev = db.revision_states(CON, job_id)
    editors = db.last_editors(CON, job_id)      # hotfix66 — 고친 칸마다 누가 · 언제
    for row in out:
        row["edited_by"] = editors.get(row["key"], {})
        row["review_codes"] = review_codes(row)
        row["review_state"] = states.get(row["key"], {})
        row["rev"] = rev.get(row["key"], {})
        # 화면에 보이는 TYPE 표기.  규칙은 서버에만 두고 화면은 결과만 읽는다
        # (`pipeline.type_display` — 판정값 `values["type"]` 은 불변).
        row["type_display"] = pipeline.type_display(row["values"],
                                                    row.get("evidence"))
    return out


@app.get("/jobs/{job_id}/rows")
def rows(job_id: str, tab: str = "ALL", keys: str = "", slim: int = 0, request: Request = None):
    """The grid's rows, each carrying the review codes it is flagged under.

    The codes ride on the row rather than being fetched separately, because the
    screen filters on them on every click and a second round trip per click is
    latency the reviewer feels.
    """
    # hotfix45 — 파싱한 목록은 다른 읽기 전용 엔드포인트와 나눠 쓴다.  여기는 열을 더하므로
    # 행마다 얕은 복사를 뜬다 (값 dict 는 공유해도 된다 — 아무도 안 고친다).
    # hotfix68 — `keys=a,b,c` 면 그 행만 (창 사이 연동이 바뀐 행만 다시 받는다 · 메모 안 함).
    if keys:
        return _json(_rows_payload(job_id, tab, {k for k in keys.split(",") if k}))
    _path, stamp = db._db_stamp(CON)
    memo_key = (job_id, tab, bool(slim))
    hit = _ROWS_BODY.get(memo_key)
    if hit is None or hit["stamp"] != stamp:
        payload = _rows_payload(job_id, tab, None)
        if slim:
            payload = [_slim_row(r) for r in payload]
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        hit = {"stamp": stamp, "raw": body, "gz": None}
        _ROWS_BODY[memo_key] = hit
        while len(_ROWS_BODY) > 4:              # 두 결과(이전 · 현재) × 두 탭이면 넉넉하다
            _ROWS_BODY.pop(next(iter(_ROWS_BODY)))
    accepts = request.headers.get("accept-encoding", "") if request is not None else ""
    if "gzip" in accepts and len(hit["raw"]) >= 2048:
        if hit["gz"] is None:
            hit["gz"] = gzip.compress(hit["raw"], 5)
        return Response(hit["gz"], media_type="application/json",
                        headers={"Content-Encoding": "gzip", "Vary": "Accept-Encoding"})
    return Response(hit["raw"], media_type="application/json")


@app.get("/jobs/{job_id}/anchors")
def anchors(job_id: str):
    """hotfix45 — 안정 ID → 그 행의 장과 사각형만.  나란히 보기가 **수정된 행의 이전
    자리**(MOD 고리)를 찾는 데 쓴다.

    hotfix40 은 그것을 위해 직전 결과의 `/rows?tab=ALL` 을 통째로 읽었다 — QFE 에서
    13.7MB(그중 `evidence` 가 82%)이고 브라우저가 그것을 풀어 들고 있어 켤 때 4.6초 ·
    힙 +30MB 였다.  필요한 것은 ID 마다 사각형 하나다 (약 60KB).  판정은 없다 —
    `revision_state` 와 `item` 을 이어 적기만 한다.
    """
    if db.get_job(CON, job_id) is None:
        raise HTTPException(404, "no such job")
    out = {}
    for r in CON.execute(
            "SELECT s.stable_id, i.page_no, i.rect_json, i.key FROM revision_state s"
            " JOIN item i ON i.job_id = s.job_id AND i.key = s.row_key"
            " WHERE s.job_id=? AND s.stable_id<>''", (job_id,)):
        out[r[0]] = {"page_no": r[1], "rect": json.loads(r[2] or "[]"), "key": r[3]}
    return _json(out)


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
            for r in db.merged_rows(CON, job_id)
            if not r.get("deleted") and not r.get("removed")]
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
        line = "범례 기록이 없는 옛 분석입니다 (15회차 이전)"
    elif mode == "derived":
        # "범례 4장" 이 아니라 "값을 읽은 3장" 이다.  이 문서는 범례가 4장인데
        # 값을 내놓은 장은 3장이고(p4 는 어느 항목의 근거도 아니다), 4라고
        #적으면 화면이 세지 않은 것을 세었다고 말하게 된다.
        line = ("이 문서의 범례를 직접 읽었습니다"
                + (f" (값을 읽은 범례 {len(lp.get('legend_sheets') or [])}장)"
                   if lp.get("legend_sheets") else ""))
    else:
        # 왜 대조를 못 했는지는 바로 옆 `compare_note` 가 말한다.  같은 사실을
        # 두 번 적으면 띠가 길어지고 읽는 사람은 두 문장을 대조하게 된다
        # (14회차 "한 번에 한 줄만" 과 같은 이유).
        line = "이 프로젝트에 저장된 범례를 그대로 썼습니다"
    sheets = lp.get("legend_sheets") or []
    missing = lp.get("uncompared") or []
    if mode != "reused":
        note = ""
    elif not lp.get("compared"):
        note = "이 PDF 에는 범례가 없어 대조하지 못했습니다 (같다고 보지 않습니다)"
    else:
        note = f"이 PDF 의 범례 {len(sheets)}장과 대조했습니다"
        if missing:
            note += f" · {len(missing)}항목은 이 PDF 에 없어 대조하지 못했습니다"
    # 56회차 [G1] — 프로필 문장.  저장된 것은 사실(`profile`·`borrowed`)이고
    # 문장은 **여기서** 만든다 (15회차 규율 — 문장을 저장하면 고칠 수 없다).
    prof = engine.get("profile") or {}
    bor = engine.get("borrowed") or {}
    if not prof:
        profile_line = "이 분석에는 프로필 기록이 없습니다 (56회차 이전)"
    elif prof.get("matched"):
        how = ("환경변수로 지정" if prof.get("env_pinned")
               else "도면번호의 프로젝트 코드와 일치해 자동으로 골랐습니다")
        profile_line = f"프로필 {prof.get('name') or prof.get('path')} ({prof.get('code')}) — {how}"
    else:
        who = prof.get("document_code") or ""
        head = (f"코드 {who} 에 맞는 프로필이 없어 새 프로젝트로 봤습니다" if who
                else "도면번호에서 프로젝트 코드를 읽지 못해 프로필을 고르지 못했습니다")
        n, rep = int(bor.get("count") or 0), len(bor.get("replaced_by_sheet") or [])
        profile_line = (f"{head} — 기본 설정({prof.get('borrowed_from') or prof.get('path')}) "
                        f"{n}칸을 빌려 썼습니다"
                        + (f" · 도면이 직접 답한 {rep}칸은 제외" if rep else ""))
    # hotfix74 — DXF 묶음에서 건너뛴 파일(같은 내용 · macOS 찌꺼기 · .dxf 아닌 것)과 태그 속성을 못
    # 배운 사실.  조용히 빠지면 "왜 행이 적지?" 에 답할 길이 없다 — 사실은 엔진이 적고 문장도 엔진 것이다.
    dx = engine.get("dxf") or {}
    input_notes = [x for x in [dx.get("roles_note") or ""] if x]
    if dx.get("skipped_inputs"):
        sk = list(dx["skipped_inputs"])
        input_notes.append(f"묶음에서 건너뛴 파일 {len(sk)}개 — " + " · ".join(str(x) for x in sk[:6])
                           + (f" 외 {len(sk) - 6}개" if len(sk) > 6 else ""))
    return {"mode": mode, "input_notes": input_notes,
            "profile": prof, "borrowed": bor, "profile_line": profile_line,
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
    rows = db.merged_rows_cached(CON, job_id, "ALL")     # 읽기만 한다 (hotfix45)
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
    # hotfix39 — 실행 프로젝트의 태그 우선
    "TAG_TYPE_MISMATCH": "태그 기능코드가 말하는 변수와 버블 글자가 다름 — 도면이 두 말을 함",
    "TAG_EVIDENCE_ROW": "태그가 증거인 행 — 버블 글자가 ISA 표로 안 풀리거나 버블이 흔들림 · 공급 주체 미판정",
    "VENDOR_MARK_UNDEFINED": "벤더마크가 이 도면 NOTES 에 정의되지 않음 — 포함/제외 판단",
    "SCOPE_OVERRIDE_UNRESOLVED": "시트 승수의 예외 문구가 있음 — 어느 항목이 예외인지 판단",
    "MULTI_SIGNAL_BUNDLE": "맞닿은 신호 버블 — 물리 수량 합산 여부 판단",
    "MULTIPLIER_UNDEFINED": "unit code 에 승수가 없어 Q'ty 를 비워 둠",
    "MULTIPLIER_FROM_CONFIG": "Q'ty 승수가 이 도면의 범례가 아니라 프로젝트 설정에서 왔음 — 확인 필요",
    "MULTIPLIER_DEFAULT_ONE": "도면이 승수를 말하지 않아 Q'ty 를 x1 로 셌음 — 승수 패널에서 답하면 그 값이 이김",
    "BUBBLE_DASHED": "버블이 파선으로 그려짐 — 범례가 뜻을 정의하지 않음 · 공급 범위 확인",
    "MULTIPLIER_NOTE_RANGE": "이 장 NOTES 가 유닛을 범위로 적어 몇 개인지 열거하지 않음 — 수량 확인 필요",
    "TYPICAL_AMBIGUOUS": "같은 Typical 표식의 상세 상자가 한 장에 둘 이상 — 어느 상자인지 확인 필요",
    "TYPICAL_POINT": "Typical 부품 점 (예: 스팀 트랩) — 본문 표식 하나를 한 행으로 셌음 · 공급 범위 확인",
    "TYPICAL_POINT_UNLABELLED": "Typical 표식마다 낸 행인데 그 표식 아래 이름표가 없음 — 어느 자리인지 도면에서 확인",
    "MULTIPLIER_BY_USER": "도면이 승수를 말하지 않아 사람이 지정한 값 — 누가·언제는 근거 패널에 있음",
    # 53회차 [B] — 8차 피드백 s4·s5·s6 (한 뿌리)
    "TAGGED_VALVE_NO_ACTUATOR":
        "도면이 버블에 이름을 붙인 밸브인데 액추에이터를 그리지 않아 어느 산출물인지 "
        "도면이 말하지 않음 — 탭을 고르지 않고 올림",
    "VALVE_TAG_NO_BODY":
        "도면이 밸브 태그 버블을 인쇄했는데 그 밸브 몸체를 못 찾음 — 품목은 있고 모양을 못 읽음",
    "VALVE_TAG_SIGNALS":
        "이 밸브 버블에 맞닿은 신호 버블(ZSC·ZSO·ZT 등)을 이 행으로 접음 — 물리 품목은 하나",

    "DRAWING_NO_BY_USER": "이 장의 타이틀블록이 획으로 그려져 도면번호를 사람이 적었음 — 누가·언제는 근거 패널에 있음",
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
    # 44회차 — 사람이 만든 행 · 사람이 오검출로 표시한 행.  둘 다 검토 사유가
    # 아니라 **사람이 이미 본 행**이라는 표시다 (`needs_review` 는 비어 있다).
    "MANUAL_ADD": "사용자가 도면에서 추가한 행 — 검출이 아니라 사람의 값",
    "MANUAL_REJECT": "사용자가 오검출로 표시한 행 — 사유는 근거 패널에 있음",
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
    # 44회차 — 사람이 만든 행과 오검출 표시.  저장된 코드가 아니라 행의 상태에서
    # 매번 만든다 (`ROW_DELETED` 와 같은 방식) — 되돌리면 같이 사라진다.
    if row.get("added"):
        out.append(markup.CODE_ADD)
    if row.get("reject") or row.get("removed"):
        out.append(markup.CODE_REJECT)
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
    _warm_pages(job_id, out)
    return _json(out)


def _warm_pages(job_id: str, pages_out: list) -> None:
    """hotfix69 — 이 결과의 장 그림을 뒤에서 미리 그린다 (`app/page_warm.py`).  사람이 처음 넘기는 장도
    디스크에서 바로 나오게.  화면이 먼저 여는 장(층이 있는 첫 장)부터 앞뒤로.  DXF 는 제 캐시가 따로 있다."""
    try:
        row = db.get_job(CON, job_id)
        if row is None or row["status"] != "done" or not row["pdf_path"]:
            return
        from app.engine import dxf_reader
        pdf = Path(row["pdf_path"])
        if dxf_reader.is_dxf_input(pdf):
            return
        nos = [p["page_no"] for p in pages_out]
        first = next((p["page_no"] for p in pages_out if p.get("layers")), nos[0] if nos else 1)
        page_warm.prime()
        page_warm.start(pdf, PAGE_CACHE, job_id, nos, first)
    except Exception:       # 미리 그리기는 빠르게 할 뿐 — 실패해도 화면은 그때그때 그린다
        pass


def _page_cache_file(job_id: str, page_no: int, zoom: float) -> Path:
    return PAGE_CACHE / job_id / f"p{page_no}_z{zoom:g}.png"


@app.get("/jobs/{job_id}/page/{page_no}.png")
def page_png(job_id: str, page_no: int, zoom: float = 1.6):
    """The sheet rendered on demand - the viewer's background only.

    Kept separate from the overlay data on purpose: the boxes come from JSON
    (`/pages`), so a rule change means new JSON, not a re-render.
    """
    row = db.get_job(CON, job_id)
    if row is None:
        raise HTTPException(404, "no such job")
    from app.engine import dxf_reader
    if dxf_reader.is_dxf_input(Path(row["pdf_path"])):
        data = _dxf_page_png(job_id, Path(row["pdf_path"]), page_no)
        return StreamingResponse(io.BytesIO(data), media_type="image/png",
                                 headers={"Cache-Control": "public, max-age=3600"})
    # hotfix45 — 한 번 그린 장은 디스크에 둔다.  같은 분석의 같은 장은 PDF 가 바뀌지
    # 않으므로(업로드 파일 고정) 그림도 바뀌지 않는다.  캐시가 없거나 못 쓰면 전처럼
    # 그린다 — 캐시는 빠르게 할 뿐 결과를 바꾸지 않는다.
    cached = _page_cache_file(job_id, page_no, zoom)
    if cached.is_file():
        return FileResponse(str(cached), media_type="image/png",
                            headers={"Cache-Control": "public, max-age=3600"})
    # hotfix69 — 서버 밖 일꾼이 그린다 (그리는 동안 다른 요청이 기다리지 않게 · app/page_warm.render_now)
    done = page_warm.render_now(Path(row["pdf_path"]), cached, page_no, zoom)
    if done is False:
        raise HTTPException(404, "no such page")
    if done and cached.is_file():
        return FileResponse(str(cached), media_type="image/png",
                            headers={"Cache-Control": "public, max-age=3600"})
    import pymupdf
    doc = pymupdf.open(row["pdf_path"])
    if not 1 <= page_no <= doc.page_count:
        raise HTTPException(404, "no such page")
    page = doc[page_no - 1]
    pm = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
    data = pm.tobytes("png")
    doc.close()
    try:
        cached.parent.mkdir(parents=True, exist_ok=True)
        tmp = cached.with_name(cached.name + f".{uuid.uuid4().hex[:8]}.tmp")
        tmp.write_bytes(data)
        os.replace(tmp, cached)          # 쓰다 만 파일이 캐시로 읽히지 않게
    except OSError:
        pass
    return StreamingResponse(io.BytesIO(data), media_type="image/png",
                             headers={"Cache-Control": "public, max-age=3600"})


_DXF_RENDER_LOCK = threading.Lock()
_DXF_SET: dict = {}          # 마지막으로 연 DXF 세트 하나 — {"path": str, "sheets": [...]}


def _dxf_sheets(path: Path, page_no: int = None) -> list:
    """그림에 쓸 장.  **그 한 장만 판다** — 세트 전체를 파는 데 몇 분이 걸리고,
    그림은 한 장만 있으면 된다 (현장 실측: 첫 그림이 60초를 넘겨 안 떴다).
    판 장은 그대로 들고 있다가 다시 요청되면 그냥 준다."""
    key = (str(path), page_no)
    if _DXF_SET.get("key") != key:
        from app.engine import dxf_reader
        sheets, _meta = dxf_reader.open_set(path, only=page_no)
        _DXF_SET.clear()
        _DXF_SET.update({"key": key, "sheets": sheets})
    return _DXF_SET["sheets"]


def _dxf_page_png(job_id: str, path: Path, page_no: int) -> bytes:
    """DXF 장 배경 — 한 번 그려 디스크에 둔다 (장당 약 6초 · `app/engine/dxf_render.py`).

    좌표 변환은 렌더러 하나에 있고, 화면은 이미지 폭 ↔ `page.width` 의 비로만 놓는다.
    """
    from app.engine import dxf_reader, dxf_render
    cache = OUTPUTS / "dxf_render" / job_id
    cache.mkdir(parents=True, exist_ok=True)
    f = cache / f"p{page_no}.png"
    if f.exists():
        return f.read_bytes()
    with _DXF_RENDER_LOCK:
        if f.exists():
            return f.read_bytes()
        sheet = next((sh for sh in _dxf_sheets(path, page_no) if sh.no == page_no), None)
        if sheet is None:
            raise HTTPException(404, "no such page")
        if sheet.error:
            raise HTTPException(422, f"이 장은 읽지 못했습니다 — {sheet.error}")
        data = dxf_render.render_png(sheet)
        f.write_bytes(data)
        return data


def _engine_near(job_id: str, page_no: int) -> tuple:
    """엔진이 그 장에서 **실제로 낸 것** — 다시 세지 않고 저장된 것을 읽는다.

    53회차 [G].  `pipeline.probe_point` 가 이것을 `ds.detect` 재실행으로 구하고
    있었고 A1 장에서 5.1~9.8초였다 (8차 피드백 s8 의 남은 원인).  같은 답이
    이미 두 곳에 있다 — 그 장의 행과 18회차 `unjudged_symbols` — 그리고 그것이
    *엔진이 낸 것*이라 다시 돌린 값보다 정확하다.
    """
    dets = []
    for r in db.merged_rows(CON, job_id):
        if r.get("page_no") != page_no or not r.get("rect"):
            continue
        ev = r.get("evidence") or {}
        dets.append({"anchor": ev.get("anchor") or ev.get("tag") or "",
                     "excel_type": r.get("type") or "",
                     "included": True,
                     "rect": [round(float(v), 1) for v in r["rect"]],
                     "rules": list(ev.get("rules_hit") or []),
                     "review_codes": list(ev.get("review_codes") or [])})
    eng = json.loads((db.get_job(CON, job_id) or {"engine_json": "{}"})["engine_json"] or "{}")
    un = [u for u in (eng.get("unjudged_symbols") or [])
          if u.get("page_no") == page_no and u.get("center")]
    # ★ 제안(`markup.propose`)이 쓰는 것과 **같은 값**이어야 한다 — 그 장 캐시의
    # 열쇠에 이것이 들어가므로, 다르면 제안이 데워 둔 캐시를 못 쓰고 그 장을
    # 처음부터 다시 읽는다 (실측 5.3초).  53회차 자기검증이 그것을 잡았다.
    moved = ((eng.get("applied_rules") or {}).get("layout") or {}).get("moved") or []
    return dets, un, moved


@app.post("/jobs/{job_id}/rows")
async def add_row(job_id: str, payload: dict):
    """Create a row a reviewer wants that the engine did not propose.

    When the reviewer also points at where it is on the drawing (`point`), the
    geometry around that spot is captured with the record - see
    `pipeline.probe_point`.  That is the whole reason this endpoint takes a
    coordinate: a missed item is only useful to a later rule pass if what was
    drawn there was written down at the time.

    44회차 — 마크업.  `rect`(표시 좌표 pt) 가 오면 그 행은 **도면 위 사각형**을
    갖고 오버레이에 그려진다.  값은 사람이 확정한 것이고, 무엇을 도면에서
    읽어 제안했는지(`proposal`)와 어느 칸이 사람 값인지(`scope_source` ·
    `qty_source`)를 근거에 남긴다.  안정 ID 는 프로젝트가 있을 때 같은 장부에서
    받는다 (`markup.assign_stable_id`).  추출값 층(`ai_json`)은 전부 None 이다.
    """
    job = db.get_job(CON, job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    page_no = _int_field(payload, "page_no")
    values = payload.get("values") or {}
    rect = payload.get("rect") or []
    author = " ".join(str(payload.get("author") or "").split())[:60]
    tab = payload.get("tab") or "FIELD"
    evidence, needs_review = None, None
    if len(rect) == 4 and page_no:
        if values.get("qty") not in (None, ""):
            try:
                values["qty"] = int(values["qty"])
            except (TypeError, ValueError):
                raise HTTPException(400, "Q'ty must be a whole number")
        klass = str(payload.get("reason_class") or "MISSING").upper()
        if klass not in markup.CLASSES:
            raise HTTPException(400, f"unknown reason class {klass!r}")
        evidence = {"markup": {
            "rect": [round(float(v), 1) for v in rect],
            "author": author, "at": time.time(), "class": klass,
            "note": str(payload.get("note") or "")[:500],
            "scope_source": (str(payload.get("scope_source") or markup.SOURCE_USER)
                             .upper()),
            "qty_source": (str(payload.get("qty_source") or markup.SOURCE_USER)
                           .upper()),
            "proposal": payload.get("proposal") or {},
        }}
        needs_review = ""          # 사람이 만든 행은 사람이 이미 본 행이다
    key = db.add_row(CON, job_id, page_no, tab,
                     payload.get("origin") or "",
                     payload.get("drawing_no") or "",
                     values, rect=rect if len(rect) == 4 else None,
                     evidence=evidence, needs_review=needs_review)
    ident = {}
    if evidence is not None:
        ident = markup.assign_stable_id(
            DATA_DIR, CON, job, key,
            dict(values, tab=tab, page_no=page_no, rect=rect,
                 drawing_no=payload.get("drawing_no") or ""))
        if ident.get("stable_id"):
            row = db.get_row(CON, job_id, key)
            ev = dict(row["evidence"]); ev["markup"]["stable_id"] = ident["stable_id"]
            CON.execute("UPDATE item SET evidence_json=? WHERE job_id=? AND key=?",
                        (json.dumps(ev, sort_keys=True, default=str), job_id, key))
            CON.commit()
    point = payload.get("point") or []
    if len(rect) == 4 and not point:
        point = [(float(rect[0]) + float(rect[2])) / 2,
                 (float(rect[1]) + float(rect[3])) / 2]
    geometry = {}
    if len(point) == 2 and page_no:
        _dets, _un, _moved = _engine_near(job_id, page_no)
        geometry = _probe_or_none(Path(job["pdf_path"]), page_no,
                                        float(point[0]), float(point[1]),
                                        layout_moved=_moved,
                                        near_detections=_dets, near_unmapped=_un)
    db.record_feedback(
        CON, job_id, "ADDED", row_key=key, page_no=page_no,
        drawing_no=payload.get("drawing_no") or "",
        rect=rect or point,
        user_value=json.dumps(values, ensure_ascii=False, sort_keys=True),
        reason=payload.get("reason") or payload.get("note") or "",
        geometry=geometry, author=author,
        pattern_args={"tab": tab, "near": geometry.get("nearest_text", "")})
    return {"key": key, "review_count": db.review_count(CON, job_id),
            "feedback_count": db.feedback_count(CON, job_id),
            "stable_id": ident.get("stable_id", ""), "excel_no": ident.get("excel_no", 0),
            "id_note": ident.get("why", ""),
            "markup": markup.summary(CON, job_id) if evidence is not None else None,
            "geometry": {k: geometry.get(k) for k in
                         ("path_count", "segment_count", "nearest_text")}}


@app.post("/jobs/{job_id}/markup/propose")
async def markup_propose(job_id: str, payload: dict):
    """마크업 사각형 하나의 제안값 — **아무것도 쓰지 않는다** (§9 ①②).

    별표·NOTES 는 `pipeline.propose_at` 이 파이프라인과 같은 함수로 읽고,
    수량은 같은 장의 행이 받은 값을 옮기며, TYPE 은 사각형 안 낱말이 앵커
    사전에 있을 때만 낸다.  못 읽은 칸은 빈칸이고 화면이 사람에게 묻는다.
    """
    job = db.get_job(CON, job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    page_no = _int_field(payload, "page_no")
    rect = payload.get("rect") or []
    if not page_no or len(rect) != 4:
        raise HTTPException(400, "page_no and a 4-number rect are required")
    return markup.propose(CON, job, page_no, rect)


@app.get("/jobs/{job_id}/markup")
def markup_summary(job_id: str):
    if db.get_job(CON, job_id) is None:
        raise HTTPException(404, "no such job")
    return {"classes": markup.CLASSES, **markup.summary(CON, job_id)}


FEEDBACK_DIR = DATA_DIR / "feedback"


@app.get("/jobs/{job_id}/feedback_export")
def feedback_export(job_id: str, by: str = ""):
    """피드백 zip — `feedback.json` · `feedback.md` · `조각/` · `장/` (44회차 [F]).

    있는 표(`item` 의 추가·오검출 · `feedback` 의 편집 · `report`)를 꺼내는
    것이고 새 사실을 만들지 않는다.  마크업은 내보낸 뒤에도 그대로 남는다.
    도면 내용이 들어가므로 저장소에 커밋하지 않는다.
    """
    job = db.get_job(CON, job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    info = markup.export_zip(CON, job, FEEDBACK_DIR, DATA_DIR, by=by)
    return FileResponse(info["path"], media_type="application/zip",
                        filename=info["name"],
                        headers={"X-Feedback-Items": str(info["items"]),
                                 "X-Feedback-Clips": str(info["clips"])})


@app.post("/jobs/{job_id}/rows/{key}/copy")
def copy_row(job_id: str, key: str):
    try:
        new_key = db.copy_row(CON, job_id, key)
    except KeyError:
        raise HTTPException(404, "no such row")
    return {"key": new_key, "review_count": db.review_count(CON, job_id)}


@app.delete("/jobs/{job_id}/rows/{key}")
def delete_row(job_id: str, key: str, reason: str = "", reason_class: str = "",
               author: str = "", exclude: bool = True):
    """Strike out a detection.  Records which rule produced it and on what.

    44회차 — 오검출 표시.  `reason_class` 는 ㉢ 오검출 · ㉣ 값 틀림 · 미지정
    심볼 · 기타 중 하나이고 `exclude=false` 면 Excel 에는 그대로 두고 표시만
    남긴다.  **행은 지워지지 않는다** (검출 행은 `removed` 표시뿐이고 되돌릴
    수 있다).  사람이 만든 행(`added`)만 실제로 없어진다.
    """
    before = db.get_row(CON, job_id, key)
    klass = str(reason_class or "").upper()
    if klass and klass not in markup.CLASSES:
        raise HTTPException(400, f"unknown reason class {klass!r}")
    author = " ".join(str(author or "").split())[:60]
    reject = ({"class": klass or "FALSE_POSITIVE", "note": reason[:500],
               "author": author, "at": time.time()}
              if (klass or author or not exclude) else None)
    try:
        out = db.remove_row(CON, job_id, key, reject=reject, exclude=exclude)
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
            reason=(f"{klass}: " if klass else "") + reason, basis=ev, author=author,
            pattern_args={"what": (before["values"].get("type")
                                   or ev.get("body") or ""),
                          "rule": (ev.get("excluded_by") or ev.get("anchor")
                                   or (rules[0] if rules else ""))})
    out["review_count"] = db.review_count(CON, job_id)
    out["feedback_count"] = db.feedback_count(CON, job_id)
    out["markup"] = markup.summary(CON, job_id)
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


@app.post("/jobs/{job_id}/qty_bulk")
async def qty_bulk(job_id: str, payload: dict):
    """hotfix65 — 여러 행의 Q'ty 를 한 번에 (수량 승수 판의 '페이지별 승수').

    **하는 일은 `patch_row` 와 같다** — 행마다 같은 `db.set_user_value` · 같은
    `record_feedback`(작성자 · 사유) 이고, 다른 것은 요청이 하나라는 것뿐이다.  여러
    장 수백 행을 행마다 요청하면 화면이 그동안 멈춰 있다.  값은 화면이 정한다
    (그 행의 기본 개수 × 사람이 적은 승수) — 서버는 받은 정수를 적기만 하고
    아무것도 다시 계산하지 않는다.  빈 값이면 도면 값으로 되돌린다 (PATCH 와 같다)."""
    if db.get_job(CON, job_id) is None:
        raise HTTPException(404, "no such job")
    items = payload.get("items") or []
    if not isinstance(items, list) or not items:
        raise HTTPException(400, "no rows")
    author = " ".join(str(payload.get("author") or "").split())[:60]
    reason = str(payload.get("reason") or "")[:200]
    clean = []
    if not all(isinstance(it, dict) for it in items):
        raise HTTPException(400, "items 는 {key, value} 목록이어야 합니다")
    for it in items:
        key = str((it or {}).get("key") or "")
        value = (it or {}).get("value")
        if value not in (None, ""):
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise HTTPException(400, "Q'ty must be a whole number")
            if value < 0:
                raise HTTPException(400, "Q'ty must not be negative")
        else:
            value = ""
        clean.append((key, value, str((it or {}).get("reason") or reason)[:200]))
    out = {}
    for key, value, why in clean:
        before = db.get_row(CON, job_id, key)
        if before is None:
            continue
        user = db.set_user_value(CON, job_id, key, "qty", value)
        db.record_feedback(
            CON, job_id, "EDITED", row_key=key, page_no=before["page_no"],
            drawing_no=before.get("drawing_no") or "", rect=before.get("rect"),
            field="qty", ai_value=(before.get("ai") or {}).get("qty"),
            user_value=value, reason=why,
            basis=before.get("evidence") or {}, author=author,
            pattern_args={"field": "qty",
                          "ai": (before.get("ai") or {}).get("qty"),
                          "user": value})
        out[key] = user
    return {"users": out, "review_count": db.review_count(CON, job_id),
            "feedback_count": db.feedback_count(CON, job_id)}


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
    """그 **한 장**만 연다 (hotfix27).

    예전에는 첫 호출에 PDF 전체를 열어(TC2 60장 3.2초) ④ 행을 처음 누를 때마다 근거 패널이
    멈춘 듯했다.  후보는 그 장의 글자만 쓰므로 그 장만 열면 된다 — 마크업 제안 · 범위 읽기가
    이미 쓰는 `load_pages(only=)` 와 같은 길이다.  DXF 는 이 경로가 없다(PDF 쪽 캐시다)."""
    import pidcache
    if "input_kind" in job.keys() and job["input_kind"] == "DXF":
        return None
    jid = job["id"]
    if jid not in _AXIS_PAGES:
        _AXIS_PAGES.clear()          # 한 번에 한 job 이면 충분하다 - 화면도 그렇다
        _AXIS_PAGES[jid] = {}
    got = _AXIS_PAGES[jid]
    if page_no not in got:
        if len(got) >= 4:            # 장을 오가도 메모리가 쌓이지 않게
            got.clear()
        _doc, pages = pidcache.load_pages(job["pdf_path"], only=(int(page_no),))
        got[page_no] = pages[0] if pages else None
    return got[page_no]


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
    states = db.revision_states(CON, job_id)
    out = {}
    if job["project"]:
        data = axis_overrides.load(
            axis_overrides.path_for(DATA_DIR, job["project"]))
        for key, st in states.items():
            entry = data.get(st.get("id") or "")
            if entry:
                out[key] = dict(entry, stable_id=st["id"],
                                inherited=entry.get("origin_job") != job_id)
    # hotfix25 — 안정 ID 가 없는 행(프로젝트 밖 · 대조 전)의 마크업 범위는 장부에 못 적히므로
    # 마지막 FROM/TO 확정의 근거(`feedback.basis`)에서 돌려준다.  **지금 사람 값이 그 문장일
    # 때만** — 확정을 해제했거나 칸을 다시 고친 뒤에는 옛 범위를 되살리지 않는다.
    rows_by_key = {r["key"]: r for r in db.merged_rows_cached(CON, job_id, "ALL")}   # 읽기만 (hotfix45)
    for fb in db.feedback_rows(CON, job_id, limit=5000):
        key = fb.get("row_key") or ""
        if fb.get("kind") != "EDITED" or fb.get("field") != "description" or key in out:
            continue
        basis = fb.get("basis") or {}
        if not (basis.get("from_rect") or basis.get("to_rect")):
            continue
        r = rows_by_key.get(key)
        if not r or (r.get("user") or {}).get("description") != fb.get("user_value"):
            continue
        out[key] = {"from": basis.get("from", ""), "to": basis.get("to", ""),
                    "from_rect": basis.get("from_rect"), "to_rect": basis.get("to_rect"),
                    "source_from": "마크업 범위" if basis.get("from") else "",
                    "source_to": "마크업 범위" if basis.get("to") else "",
                    "stable_id": (states.get(key) or {}).get("id") or "",
                    "inherited": False, "from_feedback": True}
    return out


_AXIS_TEXT_PAGE: dict = {}


def _page_words(job, page_no: int) -> list:
    """그 장의 낱말 [(사각형, 글자)] — PDF 는 그 한 장만 열고, DXF 는 그 한 장만 판다.

    좌표는 행 사각형과 같은 **표시 좌표**다 (PDF `pidcache` · DXF `Sheet.to_page`)."""
    key = (job["id"], int(page_no))
    if _AXIS_TEXT_PAGE.get("key") == key:
        return _AXIS_TEXT_PAGE["words"]
    path = Path(job["pdf_path"])
    words = []
    if ("input_kind" in job.keys() and job["input_kind"] == "DXF"):
        from app.engine import dxf_reader
        for sh in _dxf_sheets(path, page_no):
            if sh.no == page_no:
                words = [(tuple(w.rect), w.text) for w in dxf_reader.words(sh)
                         if not getattr(w, "hidden", False)]
    else:
        import pidcache
        _doc, pages = pidcache.load_pages(path, only=(page_no,))
        if pages:
            words = [(tuple(r), t) for r, t in pages[0].words]
    _AXIS_TEXT_PAGE.clear()
    _AXIS_TEXT_PAGE.update({"key": key, "words": words})
    return words


def _text_in_rect(words, rect) -> dict:
    """범위 안(가운데가 안) 낱말을 줄로 묶어 읽는 순서로.  주석 줄(도면번호 · NOTE · 치수 ·
    그리드)은 빼되 버리지 않고 `dropped` 로 돌려준다 — `_axis_text_noise` 와 같은 거름망."""
    x0, y0, x1, y1 = rect
    inside = []
    for r, t in words:
        cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        if x0 <= cx <= x1 and y0 <= cy <= y1 and str(t).strip():
            inside.append((r, str(t).strip()))
    if not inside:
        return {"text": "", "lines": [], "dropped": []}
    hs = sorted(max(r[3] - r[1], 0.1) for r, _t in inside)
    tol = 0.5 * hs[len(hs) // 2]
    lines = []
    for r, t in sorted(inside, key=lambda w: ((w[0][1] + w[0][3]) / 2, w[0][0])):
        cy = (r[1] + r[3]) / 2
        if lines and abs(lines[-1][0] - cy) <= tol:
            lines[-1][1].append((r[0], t))
        else:
            lines.append([cy, [(r[0], t)]])
    texts = [" ".join(t for _x, t in sorted(ws)) for _cy, ws in lines]
    keep = [t for t in texts if not _axis_text_noise(t)]
    return {"text": " ".join(keep).strip(), "lines": keep,
            "dropped": [t for t in texts if t not in keep]}


@app.post("/jobs/{job_id}/axis_text")
def axis_text(job_id: str, payload: dict):
    """hotfix23 — 사람이 도면에 그은 범위 안의 글자.  Description From/To 마크업이 읽는다."""
    job = db.get_job(CON, job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    try:
        page_no = int(payload.get("page_no"))
        rect = [float(v) for v in payload.get("rect")]
        assert len(rect) == 4
    except Exception:                                    # noqa: BLE001
        raise HTTPException(400, "page_no 와 rect [x0,y0,x1,y1] 가 필요합니다")
    out = _text_in_rect(_page_words(job, page_no), rect)
    out["page_no"] = page_no
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
    author = str(payload.get("author") or "").strip()
    via = str(payload.get("via") or "")
    # hotfix27 — 한 쪽은 긋고 한 쪽은 **직접 입력**할 수 있으므로 출처는 쪽마다 따로 온다
    # (`via_from` · `via_to`).  없으면 옛 `via` 하나가 두 쪽을 말한다.
    #   markup — 도면에 그은 범위 안의 글자 (서버가 `axis_text` 로 읽은 것)
    #   manual — 사람이 친 글자.  도면에 없을 수 있으므로 **"직접 입력"** 이라고 적는다
    #   keep   — 앞서 확정한 값을 안 건드렸다.  장부의 출처를 그대로 잇는다
    # 셋 다 후보 목록과 대조하지 않는다 — 대조하려면 그 장을 통째로 읽어야 하고(TC2 3.2초)
    # 출처가 이미 정해져 있다.
    via_from = str(payload.get("via_from") or via)
    via_to = str(payload.get("via_to") or via)
    _SIDE_VIAS = ("markup", "manual", "keep")
    if via == "markup" or (via_from in _SIDE_VIAS and via_to in _SIDE_VIAS):
        # hotfix23 — 사람이 도면에 그은 범위 안의 글자를 서버가 읽은 것이다 (`axis_text`).
        # 후보 목록과 대조할 필요가 없다 — 도면이 인쇄한 글자 그대로이므로 출처는 범위다.
        prev = {}
        if stable_id and job["project"]:
            prev = axis_overrides.load(
                axis_overrides.path_for(DATA_DIR, job["project"])).get(stable_id) or {}

        def _side_source(text, side_via, side):
            if not text:
                return ""
            if side_via == "markup":
                return "마크업 범위"
            if side_via == "keep" and prev.get(side) == text and prev.get(f"source_{side}"):
                return prev[f"source_{side}"]
            return "직접 입력"
        source_from = _side_source(from_text, via_from, "from")
        source_to = _side_source(to_text, via_to, "to")
    else:
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
        reason=f"판정축 FROM/TO 확정 — FROM {source_from or '없음'} · TO {source_to or '없음'}",
        basis={"from": from_text, "to": to_text,
               **({"from_rect": payload.get("from_rect")}
                  if payload.get("from_rect") and source_from == "마크업 범위" else {}),
               **({"to_rect": payload.get("to_rect")}
                  if payload.get("to_rect") and source_to == "마크업 범위" else {})},
        author=author,
        pattern_args={"field": "description",
                      "ai": (before.get("ai") or {}).get("description"),
                      "user": sentence})
    saved = False
    if stable_id and job["project"]:
        axis_overrides.record(
            axis_overrides.path_for(DATA_DIR, job["project"]), stable_id,
            from_text=from_text, to_text=to_text, source_from=source_from,
            source_to=source_to, type_=type_, sentence=sentence,
            origin_job=job_id,
            from_rect=payload.get("from_rect") if source_from == "마크업 범위" else None,
            to_rect=payload.get("to_rect") if source_to == "마크업 범위" else None)
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
    _dets, _un, _moved = _engine_near(job_id, page_no)
    return {"point": [float(point[0]), float(point[1])],
            "geometry": _probe_or_none(Path(job["pdf_path"]), page_no,
                                             float(point[0]), float(point[1]),
                                             layout_moved=_moved,
                                             near_detections=_dets,
                                             near_unmapped=_un)}


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
    page_no = _int_field(payload, "page_no") or None
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
    # hotfix71 — 같은 신고를 개발 쪽이 읽는 VOC 함에도 한 건.  신고는 이 분석의 DB 에 남고
    # (화면의 '신고' 목록), VOC 는 운영 폴더 `voc/inbox/` 에 남는다 (회사 Claude Code 가 읽는다).
    vid = ""
    try:
        category = ("MISSING" if kind == "MISSED" and what == "OTHER"
                    else what if what in voc.CATEGORIES else "OTHER")
        vid = _write_voc({"source": "ROW_REPORT", "category": category, "reason": detail,
                          "author": payload.get("author") or "",
                          "job_id": job_id, "page_no": page_no, "drawing_no": drawing_no,
                          "rect": rect if len(rect or []) == 4 else None,
                          "row_keys": [key] if key else [],
                          "point": point or None, "report_id": rid,
                          "screen": payload.get("screen") or {}})["id"]
    except (ValueError, OSError) as exc:          # VOC 함에 못 써도 신고 자체는 접수됐다
        print(f"[voc] report {rid}: {exc}", file=sys.stderr)
    return {"id": rid, "report_count": db.report_count(CON, job_id), "voc_id": vid}


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


# --------------------------------------------------------------------------
# VOC — 부서원의 오류·요청을 개발 쪽이 읽는 함에 쌓는다 (hotfix71 · app/voc.py)
# --------------------------------------------------------------------------
#
# 사람이 적는 것은 셋뿐이다 — 무엇이 틀렸나(분류) · 왜(사유) · 누가(로그인 이름).
# 나머지 — 어느 분석 · 어느 PDF · 어느 장 · 어느 사각형 · 그 행을 엔진이 어떻게 판정했나 ·
# 이 서버가 어느 업데이트인가 — 는 서버가 이미 갖고 있으므로 여기서 담는다.
# 회사 Claude Code 는 이 함을 `python spike/voc.py list` 로 읽고, 반영하면 `resolve` 로
# 장부에 적는다 (반영된 VOC 는 다시 안 보인다 — 중복 반영 방지).

VOC_CROP_PAD = 48.0          # 사각형 둘레에 보탤 여백 (pt) — 그 자리가 무엇 옆인지 보이게
VOC_CROP_ZOOM = 3.0


def _voc_crop(job, page_no: int, rect) -> bytes | None:
    """그 자리의 도면 조각 — 사각형을 붉게 두른다.  PDF 만 (DXF 는 그림이 따로라 건너뛴다)."""
    if not job or not page_no or not rect or len(rect) != 4:
        return None
    from app.engine import dxf_reader
    path = Path(job["pdf_path"])
    if not path.is_file() or dxf_reader.is_dxf_input(path):
        return None
    import pymupdf
    try:
        doc = pymupdf.open(str(path))
    except Exception:  # noqa: BLE001 — 조각은 덤이다, 못 그리면 없이 간다
        return None
    try:
        if not 1 <= page_no <= doc.page_count:
            return None
        page = doc[page_no - 1]
        x0, y0, x1, y1 = (float(v) for v in rect)
        x0, x1 = min(x0, x1), max(x0, x1)
        y0, y1 = min(y0, y1), max(y0, y1)
        clip = pymupdf.Rect(x0 - VOC_CROP_PAD, y0 - VOC_CROP_PAD,
                            x1 + VOC_CROP_PAD, y1 + VOC_CROP_PAD) & page.rect
        if clip.is_empty:
            return None
        z = VOC_CROP_ZOOM
        pm = page.get_pixmap(matrix=pymupdf.Matrix(z, z), clip=clip, alpha=False)
        ox, oy = pm.x, pm.y
        def px(x, y):
            return int(round(x * z)) - ox, int(round(y * z)) - oy
        a, b = px(x0, y0)
        c, d = px(x1, y1)
        red, t = (220, 30, 30), 3
        for r in ((a - t, b - t, c + t, b), (a - t, d, c + t, d + t),
                  (a - t, b, a, d), (c, b, c + t, d)):
            ir = pymupdf.IRect(r[0] + ox, r[1] + oy, r[2] + ox, r[3] + oy) & pm.irect
            if not ir.is_empty:
                pm.set_rect(ir, red)
        return pm.tobytes("png")
    except Exception:  # noqa: BLE001
        return None
    finally:
        doc.close()


def _voc_context(job_id: str, page_no, drawing_no: str = "") -> dict:
    job = db.get_job(CON, job_id) if job_id else None
    out = {"server": {"build": version.info(), "update": version.update_info(),
                      "voc_dir": str(voc.voc_root())}}
    if job is None:
        return out
    if page_no and not drawing_no:
        found = CON.execute("SELECT drawing_no FROM pid_page WHERE job_id=? AND page_no=?",
                            (job_id, page_no)).fetchone()
        drawing_no = (found["drawing_no"] or "") if found else ""
    keys = job.keys()
    out.update({
        "job_id": job_id, "pdf_name": job["pdf_name"], "pdf_sha256": job["pdf_sha256"],
        # 회사 Claude Code 는 운영 PC 에서 돈다 — 같은 PDF 를 그 자리에서 열 수 있게 경로도 적는다.
        "pdf_path": job["pdf_path"], "fingerprint": job["fingerprint"],
        "status": job["status"],
        "project": job["project"] if "project" in keys else "",
        "revision": job["revision"] if "revision" in keys else "",
        "input_kind": job["input_kind"] if "input_kind" in keys else "",
        "page_no": page_no or None, "drawing_no": drawing_no or "",
    })
    if job["status"] == "failed":
        out["failure"] = {"message": job["message"],
                          "stopped_stage": job["stopped_stage"] if "stopped_stage" in keys else "",
                          "error_detail": (job["error_detail"] or "")[-6000:]}
    return out


def _write_voc(payload: dict) -> dict:
    """한 건 쓰기 — 화면의 모든 입구(일반 VOC · 마크업 · 신고 · 실패 화면)가 여기 하나로 온다."""
    job_id = str(payload.get("job_id") or "")
    job = db.get_job(CON, job_id) if job_id else None
    if job_id and job is None:
        raise ValueError("no such job")
    page_no = _int_field(payload, "page_no") or None
    keys = [str(k) for k in (payload.get("row_keys") or []) if k][:50]
    rows = [_capture_row(job_id, k) for k in keys] if job else []
    rows = [r for r in rows if r]
    rect = payload.get("rect")
    if (not rect or len(rect) != 4) and rows:
        rect = (rows[0].get("identity") or {}).get("rect")
    if not page_no and rows:
        page_no = (rows[0].get("identity") or {}).get("page_no")
    drawing_no = str(payload.get("drawing_no") or "")
    if not drawing_no and rows:
        drawing_no = str((rows[0].get("identity") or {}).get("drawing_no") or "")
    ctx = _voc_context(job_id, page_no, drawing_no)
    rec = {
        "source": payload.get("source") or "GENERAL",
        "category": payload.get("category") or "OTHER",
        "reason": payload.get("reason") or "",
        "author": payload.get("author") or "",
        "context": ctx,
        "rect": [round(float(v), 1) for v in rect] if rect and len(rect) == 4 else None,
        "point": payload.get("point") or None,
        "rows": rows,
        "markup": payload.get("markup") or None,
        "report_id": payload.get("report_id"),
        "screen": payload.get("screen") or {},
    }
    crop = _voc_crop(job, page_no, rec["rect"]) if job else None
    return voc.write(rec, crop_png=crop)


@app.post("/voc")
def create_voc(payload: dict):
    try:
        rec = _write_voc(payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except OSError as exc:
        raise HTTPException(500, f"VOC 함에 쓰지 못했습니다: {exc}")
    return {"id": rec["id"], "has_crop": rec["has_crop"], "voc_dir": str(voc.voc_root())}


@app.get("/voc")
def list_voc(job_id: str = "", limit: int = 200):
    """이 서버의 VOC 함 — 최근 것부터.  반영 상태는 장부 · inbox 의 반영 표시에서 읽는다."""
    items = voc.scan([voc.inbox_dir()])
    try:
        ledger = voc.load_ledger()
    except ValueError:
        ledger = None
    upd = version.update_info()
    out = [voc.public(r, ledger, upd) for r in items.values()
           if not job_id or (r.get("context") or {}).get("job_id") == job_id]
    out.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    counts = {"total": len(out), "open": sum(1 for r in out if r["state"] == "OPEN")}
    return {"voc_dir": str(voc.voc_root()), "counts": counts, "items": out[:max(1, limit)],
            "categories": voc.CATEGORIES, "sources": voc.SOURCES}


@app.get("/voc/{voc_id}/crop.png")
def voc_crop(voc_id: str):
    if not voc.ID_RE.match(voc_id):
        raise HTTPException(404, "no such VOC")
    f = voc.inbox_dir() / voc_id / "crop.png"
    if not f.is_file():
        raise HTTPException(404, "no crop")
    return FileResponse(str(f), media_type="image/png")


@app.get("/version")
def build_version():
    """버전 + **지금 브라우저가 받은 화면 파일의 딱지** (56회차).

    꾸러미를 덮어썼는데 화면이 옛것이면 그것을 알 길이 없었다.  이제 바닥줄이
    딱지를 같이 적으므로, 캡처 한 장으로 *서버 파일이 새것인가* 와 *화면이
    그것을 받았는가* 를 가를 수 있다.
    """
    out = dict(version.info())
    out["ui"] = {"app_js": _asset_tag("app.js"), "styles_css": _asset_tag("styles.css")}
    # hotfix34 — 적용된 꾸러미 (없으면 null · 화면이 "기록 없음" 으로 말한다)
    out["update"] = version.update_info()
    # hotfix50 — 부서 대시보드(다른 출처 · file:// 사본은 null)가 "P&ID 서버가 살아 있나" 를
    # 이것으로 묻는다.  버전 정보만 담긴 이 응답 하나만 출처를 가리지 않는다 — 다른 경로에는
    # 이 머리말이 없어 대시보드가 데이터를 읽어 가는 길은 열리지 않는다.
    return JSONResponse(out, headers={"Access-Control-Allow-Origin": "*",
                                      "Cache-Control": "no-store"})


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
    try:
        result = excel_out.write_all(snap, templates, out_dir, CFG)
    except PermissionError:
        # hotfix74 — Windows 에서 지난번 결과 파일을 서버 PC 에서 엑셀로 열어 두면 같은 이름으로 덮어쓰지
        # 못한다.  지난 파일은 그대로 두고 새 폴더에 쓴다 (내려받는 사람에게는 같은 zip 이다).
        out_dir = OUTPUTS / f"rev{revision_id}_{time.strftime('%Y%m%d-%H%M%S')}"
        result = excel_out.write_all(snap, templates, out_dir, CFG)
    if not result["written"]:
        raise HTTPException(
            400, {"error": "채울 발주처 양식이 하나도 없습니다 — 양식(.xlsx)을 올리거나 data/ 에 두어야 "
                           "Excel 을 만들 수 있습니다 (no deliverable had a template to fill)",
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
    raw = await file.read()
    # hotfix74 — 엑셀이 아닌 파일(이름만 .xlsx · 구형 .xls · 손상)을 그대로 받아 두면 다음 Excel 출력이
    # 일반 500 으로 죽었다 (돌발상황 시뮬레이션).  받기 전에 열어 보고, 쓰기는 원자적으로 한다.
    why = _template_problem(raw)
    if why:
        raise HTTPException(400, f"{kind} 양식으로 쓸 수 없는 파일입니다 — {why}.  "
                                 f"발주처 양식을 엑셀에서 .xlsx 로 저장해 다시 올려 주세요.")
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(raw)
    os.replace(tmp, path)
    return {"kind": kind, "path": str(path)}


def _template_problem(raw: bytes) -> str:
    """양식 파일이 열리는 .xlsx 인가.  열리면 빈 문자열, 아니면 사람 말 한 마디."""
    if not raw:
        return "빈 파일입니다"
    if raw[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return "구형 엑셀(.xls) 파일입니다"
    if raw[:2] != b"PK":
        return "엑셀(.xlsx) 파일이 아닙니다"
    try:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True)
        wb.close()
    except Exception as exc:                             # noqa: BLE001
        return f"엑셀로 열리지 않습니다 ({type(exc).__name__})"
    return ""


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
        # hotfix74 — 예전에 받아 둔 깨진 양식은 없는 것처럼 (그 산출물만 사유와 함께 건너뛴다)
        if uploaded.exists() and not _template_problem(uploaded.read_bytes()):
            out[kind] = uploaded
        elif kind in _BUILTIN and _BUILTIN[kind].exists():
            out[kind] = _BUILTIN[kind]
        else:
            out[kind] = None
    return out


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------

def _asset_tag(name: str) -> str:
    """그 파일의 내용으로 만든 짧은 딱지 — 바뀌면 주소가 바뀐다."""
    try:
        return hashlib.sha256((STATIC / name).read_bytes()).hexdigest()[:8]
    except OSError:
        return "0"


@app.get("/", response_class=HTMLResponse)
def index():
    """화면.  ★ 56회차 — **자바스크립트·스타일 주소에 내용 딱지를 붙인다.**

    붙이기 전에는 `/static/app.js` 가 언제나 같은 주소였다.  브라우저는 그것을
    캐시하고, 꾸러미를 덮어써도 **예전 화면이 그대로 도는 일**이 실제로 있었다
    (현장 보고 두 번: 빗금이 안 그려진다 · Shift 끌기가 안 된다 — 서버 파일은
    새것인데 화면이 옛것이었다).  `Ctrl+Shift+R` 로 풀리지만, 그것을 사람이
    기억해야 한다는 것이 결함이다.

    이제 파일이 바뀌면 **주소가 바뀌므로** 캐시가 구조적으로 비켜간다.  HTML
    자체는 캐시하지 않는다 — 그 안에 딱지가 들어 있기 때문이다.
    """
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    html = html.replace("/static/app.js", f"/static/app.js?v={_asset_tag('app.js')}")
    html = html.replace("/static/styles.css",
                        f"/static/styles.css?v={_asset_tag('styles.css')}")
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


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


def _daily_backup() -> None:
    """하루 한 번 DB 를 떠 둔다 (hotfix74 · `db.backup_daily`).  실패해도 서버는 계속한다."""
    try:
        made = db.backup_daily(DB_PATH)
        if made:
            print(f"DB 백업: {made}", flush=True)
    except Exception as exc:                             # noqa: BLE001
        print(f"DB 백업 실패 (서버는 계속): {type(exc).__name__}: {exc}", flush=True)


def _start_background() -> None:
    """hotfix74 — 백그라운드 스레드는 **모듈을 다 읽은 뒤에** 시작한다.

    돌발상황 시뮬레이션(S4 · 서버 강제 종료 뒤 재시작): 끊긴 분석 정리가 기다리던 분석을 다시 줄에 세우고
    작업 스레드가 모듈 가운데에서 시작해 곧장 그 분석을 집었는데, 그 스레드가 부르는 함수
    (`_user_multipliers` 등)가 **아직 정의되기 전**이라 `NameError` 로 실패했다 — 재시작할 때마다 기다리던
    분석이 하나씩 사라졌다.  보통 기동에서는 줄이 비어 있어 드러나지 않았다."""
    _recover_interrupted()
    threading.Thread(target=_daily_backup, daemon=True, name="db-backup").start()
    threading.Thread(target=_worker, daemon=True, name="analysis-worker").start()
    threading.Thread(target=_backfill_facts, daemon=True, name="facts-backfill").start()


_start_background()
