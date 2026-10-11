"""LOGIC 검토 API — /logic (화면) · /logic/api/* (데이터).  main.py 는 이 라우터를 붙이기만 한다."""
from __future__ import annotations

import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pymupdf
from fastapi import APIRouter, Body, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response

from app import paths

from . import sim, store

router = APIRouter()
ZOOM = 2.5                      # 장 그림 배율 (A3 1191pt → 약 2980px)


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
    return store.read_result(d)


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
                    "unknown": funcs.get("UNKNOWN", 0)})
    return {"sheets": out, "pdf_pages": res["pdf_pages"], "note": res.get("note", ""),
            "dictionary": res.get("dictionary", {}), "seconds": res.get("seconds")}


@router.get("/logic/api/jobs/{job}/sheet/{page}")
def sheet(job: str, page: int):
    s = _sheet(job, page)
    d = _dir(job)
    try:
        doc = pymupdf.open(d / "source.pdf")
        r = doc[page - 1].rect
        size = [r.width, r.height]
    except Exception:
        size = None
    return JSONResponse({**s, "size": size, "zoom": ZOOM})


@router.get("/logic/api/jobs/{job}/page/{page}.png")
def page_png(job: str, page: int):
    d = _dir(job)
    cache = d / "pages" / f"p{page}_z{ZOOM}.png"
    if not cache.exists():
        cache.parent.mkdir(exist_ok=True)
        doc = pymupdf.open(d / "source.pdf")
        if not (1 <= page <= len(doc)):
            raise HTTPException(404, "그 쪽이 없습니다.")
        pix = doc[page - 1].get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM), alpha=False)
        tmp = cache.with_suffix(".tmp.png")
        pix.save(tmp)
        tmp.replace(cache)
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
    return Response(status_code=204)
