"""LOGIC 검토 API — /logic (화면) · /logic/api/* (데이터).  main.py 는 이 라우터를 붙이기만 한다."""
from __future__ import annotations

import shutil
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import quote

import pymupdf
from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response

from app import paths

from . import fromto, memo, projects, report, sim, store

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
    jobs = store.jobs()
    for j in jobs:
        if j.get("state") in ("queued", "running"):
            j["progress"] = _progress(j, jobs)
    return {"jobs": jobs, "samples": _samples()}


# 분석 진행 — 단계마다 몫(전체 시간 중 그 단계가 쓰는 비율)을 두고 단계 안은 쪽 수로 나눈다.  몫은 HRSG Logic 53장
# 실측(선 읽기 20.4초 · 글자 배우기 7.2초 · 블록 판정 8.7초 · 매크로·대조 1초)이고 **표시에만** 쓴다 (판정과 무관).
STAGES = [("reading", 0.55, "선 읽는 중"), ("glyphs", 0.19, "글자 배우는 중"),
          ("blocks", 0.24, "블록 판정 중"), ("macros", 0.02, "매크로 · from-to 맞대는 중")]


def _progress(st, jobs=None):
    """→ {percent, stage, detail, elapsed, remaining, basis} — 남은 시간은 이 서버에서 끝난 분석의 장당 시간 중앙값 × 장수."""
    import time as _t
    stage, done, total = st.get("stage") or "", st.get("done") or 0, st.get("total") or 0
    pct, label = 0.0, ("기다리는 중" if st.get("state") == "queued" else "시작하는 중")
    acc = 0.0
    for key, w, ko in STAGES:
        if key == stage:
            frac = (done / total) if total else 0.0
            pct = acc + w * min(1.0, frac)
            label = ko + (f" — {done}/{total}쪽" if key in ("reading", "blocks") and total else "")
            break
        acc += w
    started = st.get("started")
    elapsed = (_t.time() - started) if started and st.get("state") == "running" else 0.0
    pace = []
    for j in jobs if jobs is not None else store.jobs():
        if j.get("state") == "done" and j.get("seconds") and j.get("pages"):
            pace.append(j["seconds"] / j["pages"])
    remaining, basis = None, ""
    if pace and st.get("pages"):
        pace.sort()
        per = pace[len(pace) // 2]
        remaining = max(0.0, per * st["pages"] - elapsed)
        basis = f"이 서버에서 끝난 분석 {len(pace)}건의 장당 {per:.1f}초 × {st['pages']}장"
    elif pct >= 0.05 and elapsed:
        remaining = elapsed / pct * (1 - pct)
        basis = "지금까지 걸린 시간 ÷ 진행률"
    return {"percent": round(100 * min(0.99, pct)), "stage": label, "elapsed": round(elapsed),
            "remaining": None if remaining is None else round(remaining), "basis": basis}


def _samples():
    d = paths.resource("data", "logic")
    if not d.is_dir():
        return []
    return sorted(p.name for p in d.glob("*.pdf"))


def _safe_file(name: str) -> str:
    n = Path(name or "file").name
    n = "".join("_" if c in '\\/:*?"<>|' or ord(c) < 32 else c for c in n).strip() or "file"
    while len(n.encode("utf-8")) > 150:
        n = n[:-1]
    return n


@router.get("/logic/api/projects")
def list_projects():
    """LOGIC 프로젝트 (실행 전용) 와 자료 종류 — 첫 화면이 읽는다."""
    return {"projects": projects.load(),
            "materials": [{"kind": k, "label": lb, "required": req, "ext": list(ex)} for k, lb, req, ex in projects.MATERIALS]}


@router.post("/logic/api/projects")
def create_project(body: dict = Body(...)):
    try:
        return projects.create(str(body.get("name", "")), str(body.get("author", "")))
    except projects.NameError_ as e:
        raise HTTPException(400, str(e))
    except FileExistsError as e:
        raise HTTPException(409, f"같은 이름의 프로젝트가 있습니다: {e}")


@router.post("/logic/api/jobs")
async def upload(file: UploadFile | None = File(None), logic: UploadFile | None = File(None),
                 loop: UploadFile | None = File(None), sysdesc: UploadFile | None = File(None),
                 iolist: UploadFile | None = File(None), logictable: UploadFile | None = File(None),
                 project: str = Form(""), author: str = Form("")):
    """자료를 받아 분석을 시작한다.  Logic Diagram(`logic`, 옛 이름 `file`)은 필수이고 지금은 그것만 분석한다 —
    나머지 넷은 분석 폴더의 materials/ 에 그대로 보관한다 (교차 분석은 추후)."""
    lg = logic or file
    if lg is None or not (lg.filename or "").strip():
        raise HTTPException(400, "Logic Diagram PDF 는 필수입니다.")
    project = (project or "").strip()
    if project and not projects.exists(project):
        raise HTTPException(400, f"그런 LOGIC 프로젝트가 없습니다: {project}")
    extra = {"loop": loop, "sysdesc": sysdesc, "iolist": iolist, "logictable": logictable}
    allowed = {k: ex for k, _, _, ex in projects.MATERIALS}
    for k, f in extra.items():
        if f is not None and (f.filename or "").strip():
            if not Path(f.filename).suffix.lower() in allowed[k]:
                raise HTTPException(400, f"{dict((a, b) for a, b, *_ in projects.MATERIALS)[k]} 는 "
                                         f"{' · '.join(allowed[k])} 파일만 받습니다: {f.filename}")
    name = Path(lg.filename or "logic.pdf").name
    job, d = store.new_job(name)
    with open(d / "source.pdf", "wb") as f:
        shutil.copyfileobj(lg.file, f)
    try:
        _check_pdf(d / "source.pdf")
    except HTTPException:
        shutil.rmtree(d, ignore_errors=True)
        raise
    mats = {"logic": name}
    for k, f in extra.items():
        if f is None or not (f.filename or "").strip():
            continue
        md = d / "materials"
        md.mkdir(exist_ok=True)
        fn = _safe_file(f.filename)
        with open(md / f"{k}__{fn}", "wb") as out:
            shutil.copyfileobj(f.file, out)
        mats[k] = fn
    st = store.read_status(d)
    st.update({"project": project, "materials": mats, "author": (author or "").strip()[:60]})
    store.write_status(d, st)
    _start(d)
    return {"id": job, "materials": mats}


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
    if st.get("state") in ("queued", "running"):
        st["progress"] = _progress(st)
    return {"id": job, **st}


@router.get("/logic/api/jobs/{job}/fromto")
def fromto_report(job: str):
    """From-To 점검 보고 — 신호를 주기 전에 먼저 본다 (사용자 규칙 1).  행마다 L5 대조(`ft`)를 그대로 모은다."""
    res = _result(job)
    items, n = [], {"checked": 0, "ok": 0, "mismatch": 0, "desc": 0, "unchecked": 0, "other": 0}
    for s in res["sheets"]:
        for r in s["rows"]:
            fm, to = (r.get("fm") or "").strip(), (r.get("to") or "").strip()
            if r["side"] == "L" and not fm or r["side"] == "R" and not to:
                continue
            if r["side"] == "L" and (r.get("ref") or {}).get("other_bundle"):
                n["other"] += 1
                continue
            ft = r.get("ft")
            if not ft or ft.get("ok") is None:
                n["unchecked"] += 1
                continue
            n["checked"] += 1
            base = {"page": s["page"], "sheet_no": s.get("sheet_no", ""), "row": r["n"], "side": r["side"],
                    "desc": r.get("desc") or "", "ref": fm if r["side"] == "L" else to, "peer": ft.get("peer") or ""}
            if ft["ok"] is False:
                n["mismatch"] += 1
                items.append({**base, "kind": "mismatch", "why": " · ".join(ft.get("why") or [])})
            else:
                n["ok"] += 1
                if ft.get("warn"):
                    n["desc"] += 1
                    items.append({**base, "kind": "desc", "why": " · ".join(ft["warn"])})
    items.sort(key=lambda x: (x["kind"] != "mismatch", x["sheet_no"], x["side"], x["row"]))
    return {"counts": n, "items": items}


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


@router.post("/logic/api/jobs/{job}/sheet/{page}/scenario")
def scenario(job: str, page: int, body: dict = Body(default={})):
    """L14 — 이 출력까지 모든 신호가 서는 입력 조합 (범례 G003 정의를 거꾸로 · 앞으로 돌려 확인)."""
    res = _result(job)
    s = _sheet(job, page)
    target = str(body.get("target", ""))
    if not (target.startswith("row:") and target[4:].isdigit() or target.startswith("net:")):
        raise HTTPException(400, "target 은 row:<n> · net:<id> 입니다.")
    return sim.scenario(s, target, 1, sheets=res["sheets"])


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
