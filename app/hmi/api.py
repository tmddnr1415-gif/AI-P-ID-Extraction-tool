"""HMI 그래픽 라우터 — `/hmi` 화면 · 예시 장면 · 분석 결과에서 만든 장면 · 사람이 다듬은 장면 저장.

P&ID 판정 코드는 부르지 않는다.  DB 는 `main` 이 `bind(CON)` 으로 넘긴 연결 하나를 읽기만 한다.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse

from app import db, paths
from app.hmi import scene as scene_mod, store

router = APIRouter()
_DB = {"con": None}          # main 이 bind() 로 넣는 읽기용 연결 — 판정 config 와 무관한 자리 (global 문을 두지 않는다)


def bind(con):
    _DB["con"] = con


def _con():
    if _DB["con"] is None:
        raise HTTPException(503, "HMI: DB 연결이 아직 없습니다")
    return _DB["con"]


def _static(name):
    return paths.resource("app", "static", "hmi", name)


@router.get("/hmi")
def hmi_page():
    return FileResponse(_static("hmi.html"), headers={"Cache-Control": "no-store"})


@router.get("/hmi/api/example")
def example():
    p = paths.resource("config", "hmi_example_compressor_train.json")
    return json.loads(p.read_text(encoding="utf-8"))


@router.get("/hmi/api/jobs")
def jobs():
    """끝난 P&ID 분석 목록 — 장면을 만들 수 있는 것."""
    con = _con()
    out = []
    for j in con.execute("SELECT id, pdf_name AS filename, project, revision, created_at FROM job WHERE status='done' ORDER BY rowid DESC LIMIT 200").fetchall():
        d = dict(j)
        n = con.execute("SELECT COUNT(*) FROM pid_page WHERE job_id=? AND layers_json != '{}'", (d["id"],)).fetchone()[0]
        d["pages"] = n
        out.append(d)
    return out


@router.get("/hmi/api/jobs/{job}/pages")
def pages(job: str):
    con = _con()
    if db.get_job(con, job) is None:
        raise HTTPException(404, "no such job")
    out = []
    for p in con.execute("SELECT page_no, drawing_no, title, width, height FROM pid_page WHERE job_id=? ORDER BY page_no", (job,)).fetchall():
        d = dict(p)
        d["rows"] = con.execute("SELECT COUNT(*) FROM item WHERE job_id=? AND page_no=? AND deleted=0 AND removed=0",
                                (job, d["page_no"])).fetchone()[0]
        d["saved"] = store.path(job, d["page_no"]).exists()
        out.append(d)
    return out


def _page_info(con, job, page):
    row = con.execute("SELECT page_no, drawing_no, title, width, height FROM pid_page WHERE job_id=? AND page_no=?", (job, page)).fetchone()
    return dict(row) if row else {}


@router.get("/hmi/api/jobs/{job}/scene/{page}")
def get_scene(job: str, page: int, fresh: int = 0):
    con = _con()
    if db.get_job(con, job) is None:
        raise HTTPException(404, "no such job")
    saved = None if fresh else store.load(job, page)
    if saved:
        saved["saved"] = True
        return saved
    rows = [r for r in db.merged_rows_cached(con, job, "ALL", slim=False) if r.get("page_no") == page]
    pi = _page_info(con, job, page)
    sc = scene_mod.build(rows, pi, pi.get("drawing_no") or "", pi.get("title") or "")
    sc["saved"] = False
    return sc


@router.post("/hmi/api/jobs/{job}/scene/{page}")
def save_scene(job: str, page: int, body: dict = Body(...)):
    con = _con()
    if db.get_job(con, job) is None:
        raise HTTPException(404, "no such job")
    sc = body.get("scene")
    if not isinstance(sc, dict):
        raise HTTPException(400, "scene 이 없습니다")
    try:
        out = store.save(job, page, sc, body.get("author") or "")
    except ValueError:
        raise HTTPException(400, "작성자 이름이 필요합니다")
    return {"ok": True, "saved_at": out["saved_at"], "saved_by": out["saved_by"]}


@router.delete("/hmi/api/jobs/{job}/scene/{page}")
def reset_scene(job: str, page: int):
    con = _con()
    if db.get_job(con, job) is None:
        raise HTTPException(404, "no such job")
    return {"ok": True, "removed": store.delete(job, page)}
