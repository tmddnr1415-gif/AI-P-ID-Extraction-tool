"""LOGIC 작도 API (L54) — /logic/draw (화면) · /logic/api/drawings/* (데이터).  api.py 가 이 라우터를 붙인다.

판정 코드는 부르지 않는다 — verify 만 분석기(analyse)를 **그대로** 불러 그린 것을 되읽는다.
"""
from __future__ import annotations

import shutil
from urllib.parse import quote

import json
from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response

from app import paths

from . import draw, draw_sets, store

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
    return {"symbols": draw.SYMBOLS, "layout": draw.layout(draw.N_DEFAULT), "style": draw.load_style(), "presets": draw.BOX_PRESETS}


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


# ─────────────────────────── 묶음 (L56) ───────────────────────────

@router.get("/logic/api/drawings/sets")
def list_sets():
    return {"items": draw_sets.sets_listing()}


@router.post("/logic/api/drawings/sets/import")
def import_set(body: dict = Body(default={})):
    """분석한 묶음(job)의 모든 시트를 이 양식의 그림 묶음으로."""
    from . import api as A
    author = _author(body.get("author"))
    job = str(body.get("job") or "").strip()
    if not job:
        raise HTTPException(400, "job 이 필요합니다.")
    res = A._result(job)
    st = store.read_status(store.root() / job) if (store.root() / job).exists() else {}
    name = str(body.get("name") or st.get("name") or job).strip()[:80]
    return draw_sets.import_bundle(res, name, author, str(body.get("project") or st.get("project") or "")[:80], job)


def _set(sid: str) -> list:
    if not draw.ID_RE.match(sid or ""):
        raise HTTPException(404, "그런 묶음이 없습니다.")
    docs = draw_sets.set_docs(sid)
    if not docs:
        raise HTTPException(404, "그런 묶음이 없습니다.")
    return docs


@router.get("/logic/api/drawings/sets/{sid}")
def get_set(sid: str):
    docs = _set(sid)
    return {"id": sid, "name": docs[0].get("set_name") or "", "project": docs[0].get("project") or "",
            "sheets": [{k: d.get(k) for k in ("id", "sheet_no", "title", "typical", "order")} | {"blocks": len(d["blocks"]), "wires": len(d["wires"])} for d in docs],
            "links": draw_sets.links(docs), "macros": draw_sets.macro_types(docs)}


@router.post("/logic/api/drawings/sets/{sid}/sheet")
def add_sheet(sid: str, body: dict = Body(default={})):
    """묶음에 빈 장 하나 (또는 사전 Typical 시트를 들여온다: `library`)."""
    docs = _set(sid)
    author = _author(body.get("author"))
    order = max(d.get("order") or 0 for d in docs) + 1
    if body.get("library"):
        doc = draw_sets.typical_doc_from_library(str(body["library"]), str(body.get("name") or "")[:80], author,
                                                 docs[0].get("project") or "", sid, order)
        if doc is None:
            raise HTTPException(404, "학습 사전에 그 Typical 이 없습니다.")
        return doc
    try:
        n = int(body.get("N") or docs[0]["N"])
    except (TypeError, ValueError):
        n = docs[0]["N"]
    doc = draw.new_doc(str(body.get("name") or "새 장")[:80], author, docs[0].get("project") or "", n)
    doc.update({"set": sid, "set_name": docs[0].get("set_name") or "", "order": order, "typical": bool(body.get("typical")),
                "sheet_no": str(body.get("sheet_no") or "")[:40]})
    draw.save_new(doc)
    # L62 — 다른 장이 이미 이 시트 이름을 가리키고 있으면(미작성이던 참조) 새 장의 칸을 바로 채운다
    if doc["sheet_no"]:
        r = draw_sets.autolink(docs + [doc], doc["id"], author)
        if r["changed"]:
            doc = _load(doc["id"])
            doc["autolinked"] = r["changed"]
    return doc


@router.get("/logic/api/drawings/sets/{sid}/links")
def set_links(sid: str):
    return draw_sets.links(_set(sid))


@router.post("/logic/api/drawings/sets/{sid}/link")
def set_link(sid: str, body: dict = Body(default={})):
    """보내는 장의 오른쪽 행 ↔ 받는 장의 왼쪽 행을 서로 가리키게 적는다 (FROM/TO 자동 잇기)."""
    docs = {d["id"]: d for d in _set(sid)}
    author = _author(body.get("author"))
    try:
        f, t = docs[str(body.get("from_did"))], docs[str(body.get("to_did"))]
        n_out, n_in = int(body.get("n_out")), int(body.get("n_in"))
    except (KeyError, TypeError, ValueError):
        raise HTTPException(400, "from_did · n_out · to_did · n_in 이 필요합니다.")
    try:
        return draw_sets.link_rows(f, n_out, t, n_in, author)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/logic/api/drawings/sets/{sid}/autolink")
def set_autolink(sid: str, body: dict = Body(default={})):
    """저장 직후 — 이 장의 FM/TO 참조가 가리키는 상대 장의 빈 칸을 채운다."""
    docs = _set(sid)
    return draw_sets.autolink(docs, str(body.get("did") or ""), _author(body.get("author")))


@router.get("/logic/api/drawings/sets/{sid}/export.pdf")
def export_set_pdf(sid: str):
    docs = _set(sid)
    name = quote(f"{docs[0].get('set_name') or sid}.pdf")
    return Response(draw_sets.to_pdf_set(docs), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{name}"})


@router.post("/logic/api/drawings/sets/{sid}/verify")
def verify_set(sid: str):
    return draw_sets.verify_set(_set(sid))


@router.post("/logic/api/drawings/sets/{sid}/analyse")
def analyse_set(sid: str, body: dict = Body(default={})):
    """묶음을 한 PDF 로 내보내 LOGIC 검토 묶음으로 올린다."""
    from . import api as A
    docs = _set(sid)
    author = str(body.get("author") or docs[0].get("author") or "").strip()[:60]
    name = f"{docs[0].get('set_name') or sid} (작도).pdf"
    job, d = store.new_job(name)
    (d / "source.pdf").write_bytes(draw_sets.to_pdf_set(docs))
    st = store.read_status(d)
    st.update({"project": docs[0].get("project") or "", "materials": {"logic": name}, "author": author, "drawing_set": sid})
    store.write_status(d, st)
    A._start(d)
    return {"id": job}


@router.get("/logic/api/drawings/{did}")
def get_drawing(did: str):
    return _load(did)


@router.put("/logic/api/drawings/{did}")
def put_drawing(did: str, body: dict = Body(...)):
    _load(did)
    author = _author(body.get("author"))
    doc = body.get("doc") if isinstance(body.get("doc"), dict) else body
    if doc is not body:                       # L56 — 묶음 칸은 바깥 몸통에 실려 올 수 있다 (화면 `set-make`)
        doc = {**doc, **{k: body[k] for k in ("set", "set_name", "order") if k in body}}
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


_SIM_CACHE: dict = {}          # L57 — 묶음 지문 → sim 캐시 (그림이 바뀌면 지문이 바뀐다 · 한 개만 든다)


def _sim_docs(did: str, live: dict | None) -> list:
    """시뮬레이션에 넣을 그림들 — 그 그림이 묶음에 들면 묶음 전체 · 아니면 그 그림 하나.  live(저장 전 화면 그림)가 있으면 그것으로 바꿔 넣는다."""
    saved = _load(did)
    docs = draw_sets.set_docs(saved["set"]) if saved.get("set") else [saved]
    if live is not None:
        cur = {**saved, **draw.clean(live), "sheet_no": str(live.get("sheet_no") or saved.get("sheet_no") or "")[:40],
               "title": str(live.get("title") or saved.get("title") or "")[:120], "typical": bool(live.get("typical", saved.get("typical")))}
        docs = [cur if d["id"] == did else d for d in docs]
        if not any(d["id"] == did for d in docs):
            docs.append(cur)
    return docs


@router.post("/logic/api/drawings/{did}/simulate")
def simulate_drawing(did: str, body: dict = Body(default={})):
    """L57 — 그린 로직을 **PDF 로 내보내지 않고** 바로 시뮬레이션한다 (draw_sim.to_sheet → sim.simulate_bundle).
    body: doc(저장 전 그림 · 선택) · forces {그림 id: {row:n|net:k|block:id: 0|1}} · state · timers {그림 id: {블록: 초}} · analog.
    묶음에 든 그림이면 묶음 전체가 함께 돈다 (FROM/TO · 매크로 ↔ Typical)."""
    from . import draw_sim
    import hashlib
    live = body.get("doc") if isinstance(body.get("doc"), dict) else None
    docs = _sim_docs(did, live)
    sig = hashlib.sha1(json.dumps([{k: d.get(k) for k in ("id", "N", "sheet_no", "typical", "left", "right", "blocks", "wires")} for d in docs],
                                  sort_keys=True, default=str).encode()).hexdigest()
    cache = _SIM_CACHE.get(sig)
    if cache is None:
        _SIM_CACHE.clear()
        cache = _SIM_CACHE[sig] = {}
    def _d(v):
        return v if isinstance(v, dict) else {}
    try:
        out = draw_sim.simulate(docs, did, forces=_d(body.get("forces")), state=_d(body.get("state")), timers=_d(body.get("timers")),
                                analog=_d(body.get("analog")), cache=cache,
                                inner=body.get("inner") if isinstance(body.get("inner"), list) else None)
    except Exception as e:                       # 그림이 아직 덜 그려져 있어도 화면이 멈추지 않는다 — 사유를 말한다
        return {"error": f"시뮬레이션하지 못했습니다 — {type(e).__name__}: {e}"[:300]}
    out["sig"] = sig[:12]
    return out


@router.get("/logic/api/drawings/{did}/sheet")
def drawing_sheet(did: str):
    """그림을 분석 결과 시트 꼴로 (판정 없이 꼴만 — 시험 · 점검용)."""
    from . import draw_sim
    docs = _sim_docs(did, None)
    sheets = draw_sim.sheets_of(docs)
    return next((s for s in sheets if s.get("did") == did), sheets[0] if sheets else {})


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

