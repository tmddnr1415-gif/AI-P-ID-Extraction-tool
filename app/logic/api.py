"""LOGIC 검토 API — /logic (화면) · /logic/api/* (데이터).  main.py 는 이 라우터를 붙이기만 한다."""
from __future__ import annotations

import shutil
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import quote

import pymupdf
from fastapi import APIRouter, Body, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response

from app import paths

from . import fromto, memo, report, sim, store

router = APIRouter()
ZOOM = store.ZOOM
_SIZES = {}                     # job → {page: [w, h]} — 쪽 크기는 PDF 를 한 번만 연다 (L7)


def _static(name):
    return paths.resource("app", "static", name)


@router.get("/logic")
def logic_page():
    return FileResponse(_static("logic.html"), headers={"Cache-Control": "no-store"})


def _start(d: Path):
    if paths.frozen():
        from .run import run
        threading.Thread(target=run, args=(d,), daemon=True).start()
        return
    root = Path(__file__).resolve().parent.parent.parent
    subprocess.Popen([sys.executable, "-m", "app.logic.run", str(d)], cwd=str(root),
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _check_pdf(path: Path):
    try:
        doc = pymupdf.open(path)
    except Exception:
        raise HTTPException(400, "PDF 로 열리지 않는 파일입니다.")
    if doc.needs_pass:
        raise HTTPException(400, "암호가 걸린 PDF 입니다 — 암호를 푼 판으로 올려 주세요.")
    if len(doc) == 0:
        raise HTTPException(400, "쪽이 하나도 없는 PDF 입니다.")


@router.get("/logic/api/jobs")
def list_jobs():
    return {"jobs": store.jobs(), "samples": _samples()}


def _samples():
    d = paths.resource("data", "logic")
    if not d.is_dir():
        return []
    return sorted(p.name for p in d.glob("*.pdf"))


@router.post("/logic/api/jobs")
async def upload(file: UploadFile = File(...)):
    name = Path(file.filename or "logic.pdf").name
    job, d = store.new_job(name)
    with open(d / "source.pdf", "wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        _check_pdf(d / "source.pdf")
    except HTTPException:
        shutil.rmtree(d, ignore_errors=True)
        raise
    _start(d)
    return {"id": job}


@router.post("/logic/api/jobs/sample")
def from_sample(body: dict = Body(...)):
    name = Path(str(body.get("name", ""))).name
    src = paths.resource("data", "logic") / name
    if not name.endswith(".pdf") or not src.is_file():
        raise HTTPException(404, "그런 샘플이 없습니다.")
    job, d = store.new_job(name)
    shutil.copyfile(src, d / "source.pdf")
    _start(d)
    return {"id": job}


def _dir(job):
    try:
        return store.job_dir(job)
    except KeyError:
        raise HTTPException(404, "그런 분석이 없습니다.")


@router.get("/logic/api/jobs/{job}")
def job_status(job: str):
    d = _dir(job)
    st = store.read_status(d)
    st.pop("trace", None)
    return {"id": job, **st}


def _result(job):
    d = _dir(job)
    if not (d / "result.json").exists():
        raise HTTPException(409, "아직 분석이 끝나지 않았습니다.")
    res = store.read_result(d)
    if not res.get("_ft"):                   # 예전 결과도 다시 분석 없이 FM ↔ TO 대조 (L5) — 캐시된 결과에는 한 번만 (L7)
        fromto.check(res["sheets"])
        res["_ft"] = True
    return res


def _size(job, d, page):
    sz = _SIZES.get(job)
    if sz is None:
        sz = {}
        try:
            doc = pymupdf.open(d / "source.pdf")
            for i, pg in enumerate(doc):
                r = pg.rect
                sz[i + 1] = [r.width, r.height]
        except Exception:
            pass
        _SIZES[job] = sz
    return sz.get(page)


def _sheet(job, page):
    for s in _result(job)["sheets"]:
        if s["page"] == page:
            return s
    raise HTTPException(404, "그 쪽은 Logic 표 시트가 아닙니다.")


@router.get("/logic/api/jobs/{job}/sheets")
def sheets(job: str):
    res = _result(job)
    out = []
    for s in res["sheets"]:
        funcs = {}
        for b in s["blocks"].values():
            funcs[b["func"]] = funcs.get(b["func"], 0) + 1
        out.append({"page": s["page"], "sheet_no": s["sheet_no"], "title": s["title"],
                    "nets": len(s["nets"]), "blocks": len(s["blocks"]), "funcs": funcs,
                    "findings": len(s["findings"]),
                    "mismatch": sum(1 for f in s["findings"] if f["code"] == "FT_MISMATCH"),
                    "descdiff": sum(1 for f in s["findings"] if f["code"] == "FT_DESC_DIFF"),
                    "unknown": funcs.get("UNKNOWN", 0)})
    return {"sheets": out, "pdf_pages": res["pdf_pages"], "note": res.get("note", ""),
            "dictionary": res.get("dictionary", {}), "seconds": res.get("seconds")}


@router.get("/logic/api/jobs/{job}/sheet/{page}")
def sheet(job: str, page: int):
    s = _sheet(job, page)
    return JSONResponse({**s, "size": _size(job, _dir(job), page), "zoom": ZOOM})


@router.get("/logic/api/jobs/{job}/findings")
def findings(job: str):
    """묶음 전체의 점검 목록 — 장마다의 `findings` 를 한 줄로 편다 (새 판정 0 · 화면의 '묶음 점검' 이 읽는다)."""
    res = _result(job)
    return report.findings(res["sheets"])


@router.get("/logic/api/jobs/{job}/report.xlsx")
def report_xlsx(job: str):
    res = _result(job)
    d = _dir(job)
    name = store.read_status(d).get("name") or "logic"
    data = report.workbook(res, name)
    fn = Path(name).stem + "_logic_review.xlsx"
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment; filename*=UTF-8''" + quote(fn)})


@router.get("/logic/api/jobs/{job}/page/{page}.png")
def page_png(job: str, page: int):
    d = _dir(job)
    try:
        cache = store.page_png(d, page)
    except IndexError:
        raise HTTPException(404, "그 쪽이 없습니다.")
    return FileResponse(cache, media_type="image/png", headers={"Cache-Control": "private, max-age=86400"})


@router.post("/logic/api/jobs/{job}/sheet/{page}/simulate")
def simulate(job: str, page: int, body: dict = Body(default={})):
    s = _sheet(job, page)
    forces = body.get("forces") or {}
    if not isinstance(forces, dict):
        raise HTTPException(400, "forces 는 {키: 0|1} 이어야 합니다.")
    clean = {}
    for k, v in forces.items():
        if v in (0, 1) and isinstance(k, str) and k.split(":", 1)[0] in ("net", "row", "block"):
            clean[k] = int(v)
    state = body.get("state") if isinstance(body.get("state"), dict) else None
    return sim.simulate(s, clean, state)


@router.post("/logic/api/jobs/{job}/sheet/{page}/trace")
def trace(job: str, page: int, body: dict = Body(default={})):
    s = _sheet(job, page)
    start = str(body.get("start", ""))
    direction = "up" if body.get("direction") == "up" else "down"
    if not start.split(":", 1)[0] in ("net", "row", "block"):
        raise HTTPException(400, "start 는 net:<id> · row:<n> · block:<id> 입니다.")
    return sim.trace(s, start, direction)


@router.delete("/logic/api/jobs/{job}")
def delete(job: str):
    d = _dir(job)
    shutil.rmtree(d, ignore_errors=True)
    _SIZES.pop(job, None)
    return Response(status_code=204)


@router.post("/logic/api/jobs/{job}/simulate")
def simulate_bundle(job: str, body: dict = Body(default={})):
    """묶음 전체 — 출력 행이 1 이면 그 행을 FM 으로 받는 다른 장의 입력 행도 1 (도면이 적은 FM 연결)."""
    res = _result(job)
    raw = body.get("forces") or {}
    if not isinstance(raw, dict):
        raise HTTPException(400, "forces 는 {쪽: {키: 0|1}} 이어야 합니다.")
    forces = {}
    for pg, fs in raw.items():
        if not isinstance(fs, dict) or not str(pg).isdigit():
            raise HTTPException(400, "forces 는 {쪽: {키: 0|1}} 이어야 합니다.")
        clean = {k: int(v) for k, v in fs.items()
                 if v in (0, 1) and isinstance(k, str) and k.split(":", 1)[0] in ("net", "row", "block")}
        if clean:
            forces[int(pg)] = clean
    state = body.get("state") if isinstance(body.get("state"), dict) else None
    focus = body.get("page")
    focus = int(focus) if isinstance(focus, int) or (isinstance(focus, str) and focus.isdigit()) else None
    return sim.simulate_bundle(res["sheets"], forces, state, focus)


@router.get("/logic/api/jobs/{job}/memo")
def memo_list(job: str):
    """이 묶음의 메모 전부 (L8) — 화면이 장마다 거른다."""
    return memo.load(_dir(job))


@router.post("/logic/api/jobs/{job}/memo")
def memo_add(job: str, body: dict = Body(...)):
    d = _dir(job)
    page = body.get("page")
    if not isinstance(page, int):
        raise HTTPException(400, "page 는 쪽 번호(정수)여야 합니다.")
    try:
        return memo.add(d, page, str(body.get("sheet_no") or ""), str(body.get("text") or ""),
                        str(body.get("author") or ""), body.get("at"))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.patch("/logic/api/jobs/{job}/memo/{mid}")
def memo_update(job: str, mid: str, body: dict = Body(...)):
    d = _dir(job)
    def flag(k):
        v = body.get(k)
        return v if isinstance(v, bool) else None
    text = body.get("text")
    try:
        return memo.update(d, mid, str(body.get("author") or ""),
                           text=str(text) if text is not None else None, done=flag("done"), hidden=flag("hidden"))
    except KeyError:
        raise HTTPException(404, "그런 메모가 없습니다.")
    except ValueError as e:
        raise HTTPException(400, str(e))
