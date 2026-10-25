"""LOGIC 작도 API (L54) — /logic/draw (화면) · /logic/api/drawings/* (데이터).  api.py 가 이 라우터를 붙인다.

판정 코드는 부르지 않는다 — verify 만 분석기(analyse)를 **그대로** 불러 그린 것을 되읽는다.
"""
from __future__ import annotations

import shutil
from urllib.parse import quote

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response

from app import paths

from . import draw, store

router = APIRouter()


def _static(name):
    return paths.resource("app", "static", name)


@router.get("/logic/draw")
def draw_page():
    return FileResponse(_static("logic_draw.html"), headers={"Cache-Control": "no-store"})


def _load(did: str) -> dict:
    try:
        return draw.load(did)
    except KeyError:
        raise HTTPException(404, "그런 그림이 없습니다.")


def _author(v) -> str:
    a = str(v or "").strip()[:60]
    if not a:
        raise HTTPException(400, "작성자 이름이 필요합니다.")
    return a


@router.get("/logic/api/drawings/symbols")
def symbols():
    """팔레트 — 서버의 기호 사전 그대로 (화면이 따로 외우지 않는다)."""
    return {"symbols": draw.SYMBOLS, "layout": draw.layout(draw.N_DEFAULT)}


@router.get("/logic/api/drawings")
def list_drawings():
    return {"items": draw.listing()}


@router.post("/logic/api/drawings")
def create_drawing(body: dict = Body(default={})):
    """새 그림.  `from_job` + `from_page` 를 주면 분석한 그 시트를 이 양식으로 옮겨 시작한다."""
    author = _author(body.get("author"))
    name = str(body.get("name") or "").strip()[:80]
    project = str(body.get("project") or "").strip()[:80]
    job, page = body.get("from_job"), body.get("from_page")
    if job:
        from . import api as A
        res = A._result(str(job))
        try:
            pno = int(page)
        except (TypeError, ValueError):
            raise HTTPException(400, "from_page 는 쪽 번호입니다.")
        s = next((s for s in res["sheets"] if s["page"] == pno), None)
        if s is None:
            raise HTTPException(404, "그 묶음에 그 쪽의 LOGIC 시트가 없습니다.")
        doc = draw.from_sheet(s, name or (s.get("sheet_no") or f"p{pno}"), author, project)
        doc["source"] = {"job": str(job), "page": pno, "sheet_no": s.get("sheet_no", "")}
    else:
        try:
            n = int(body.get("N") or draw.N_DEFAULT)
        except (TypeError, ValueError):
            n = draw.N_DEFAULT
        doc = draw.new_doc(name or "새 로직", author, project, n)
    draw.save_new(doc)
    return doc


@router.get("/logic/api/drawings/{did}")
def get_drawing(did: str):
    return _load(did)


@router.put("/logic/api/drawings/{did}")
def put_drawing(did: str, body: dict = Body(...)):
    _load(did)
    author = _author(body.get("author"))
    doc = body.get("doc") if isinstance(body.get("doc"), dict) else body
    try:
        return draw.save(did, doc, author)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/logic/api/drawings/{did}")
def delete_drawing(did: str, author: str = ""):
    _load(did)
    return {"deleted": draw.delete(did, _author(author)).get("name")}


@router.get("/logic/api/drawings/{did}/export.pdf")
def export_pdf(did: str):
    doc = _load(did)
    name = quote(f"{doc.get('sheet_no') or doc.get('name') or 'logic'}.pdf")
    return Response(draw.to_pdf(doc), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{name}"})


@router.get("/logic/api/drawings/{did}/export.dxf")
def export_dxf(did: str):
    doc = _load(did)
    name = quote(f"{doc.get('sheet_no') or doc.get('name') or 'logic'}.dxf")
    return Response(draw.to_dxf(doc), media_type="application/dxf",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{name}"})


@router.post("/logic/api/drawings/{did}/verify")
def verify_drawing(did: str, body: dict = Body(default={})):
    """저장 전 그림(body.doc)이 있으면 그것을, 없으면 저장된 것을 분석기에 되읽혀 비교한다."""
    saved = _load(did)
    doc = body.get("doc") if isinstance(body.get("doc"), dict) else saved
    return draw.verify({**saved, **draw.clean(doc), "sheet_no": str(doc.get("sheet_no") or "")[:40]})


@router.post("/logic/api/drawings/{did}/analyse")
def analyse_drawing(did: str, body: dict = Body(default={})):
    """그린 것을 PDF 로 내보내 **LOGIC 검토 묶음**으로 올린다 — 시뮬레이션 · 정합성 검토를 그대로 쓴다."""
    from . import api as A
    doc = _load(did)
    author = str(body.get("author") or doc.get("author") or "").strip()[:60]
    name = f"{doc.get('sheet_no') or doc.get('name') or 'logic'} (작도).pdf"
    job, d = store.new_job(name)
    (d / "source.pdf").write_bytes(draw.to_pdf(doc))
    st = store.read_status(d)
    st.update({"project": doc.get("project") or "", "materials": {"logic": name}, "author": author,
               "drawing": did})
    store.write_status(d, st)
    A._start(d)
    return {"id": job}
