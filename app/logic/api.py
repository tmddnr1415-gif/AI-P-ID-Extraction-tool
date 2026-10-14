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

from . import fromto, idrate, library, memo, overrides, projects, report, sim, store, teach

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
    library.backfill_async()
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


_APPLIED = {}                    # job → (결과 mtime, 사람 값 mtime, 사람 값을 얹은 결과) — L22


def _result(job):
    d = _dir(job)
    if not (d / "result.json").exists():
        raise HTTPException(409, "아직 분석이 끝나지 않았습니다.")
    res = store.read_result(d)
    if not res.get("_ft"):                   # 예전 결과도 다시 분석 없이 FM ↔ TO 대조 (L5) — 캐시된 결과에는 한 번만 (L7)
        fromto.check(res["sheets"])
        res["_ft"] = True
    # L22 — 사람이 정한 값(게이트 종류 · FM/TO · 타이머)을 얹는다.  분석 결과 파일은 그대로이고 사본에 얹는다.
    # L25 — 다른 묶음에서 사람이 가르친 게이트 규칙(학습 사전)도 얹는다 (그 묶음의 규칙이 이기고, 블록 하나를 정한 것이 더 이긴다)
    lm = library.mtime()
    lib_rules = _lib_rules(lm, job)
    om = overrides.mtime(d)
    if om is None and not lib_rules:
        _APPLIED.pop(job, None)
        return res
    rm = (d / "result.json").stat().st_mtime_ns
    hit = _APPLIED.get(job)
    if hit and hit[0] == rm and hit[1] == om and hit[3] == lm:
        return hit[2]
    ov = overrides.load(d) if om is not None else overrides.empty()
    if not overrides.has_any(ov) and not _lib_hits(res, lib_rules):
        return res
    import json as _json
    fresh = _json.loads((d / "result.json").read_text(encoding="utf-8"))
    overrides.apply(fresh, ov, lib_rules)
    fresh["_ft"] = True
    if len(_APPLIED) > 3:
        _APPLIED.clear()
    _APPLIED[job] = (rm, om, fresh, lm)
    return fresh


_LIB_RULES = {}


def _lib_rules(lm, job):
    if lm is None:
        return []
    hit = _LIB_RULES.get(job)
    if hit and hit[0] == lm:
        return hit[1]
    try:
        rules = library.taught_rules(exclude_bundle=job)
    except Exception:
        rules = []
    if len(_LIB_RULES) > 8:
        _LIB_RULES.clear()
    _LIB_RULES[job] = (lm, rules)
    return rules


def _lib_hits(res, rules):
    """사전 규칙이 이 묶음의 블록에 하나라도 맞는가 (안 맞으면 캐시된 결과를 그대로 쓴다)."""
    return bool(rules) and bool(teach.gate_entries(res, rules, {}))


def _size(job, d, page):
    if page >= library.LIB_PAGE0:
        try:
            pm = pymupdf.Pixmap(str(_lib_png(job, page)))
            return [pm.width / ZOOM, pm.height / ZOOM]
        except HTTPException:
            return None
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


def _all_sheets(res):
    """묶음 시트 + 학습 사전에서 가져온 Typical 시트 (L22 · 가짜 쪽 번호 library.LIB_PAGE0+)."""
    return res["sheets"] + list(res.get("library_sheets") or [])


def _sheet(job, page):
    for s in _all_sheets(_result(job)):
        if s["page"] == page:
            return s
    raise HTTPException(404, "그 쪽은 Logic 표 시트가 아닙니다.")


def _lib_png(job, page):
    """학습 사전 Typical 시트의 그림 (분석한 묶음이 아니라 사전에 남은 그림)."""
    s = _sheet(job, page)
    png = (s.get("library") or {}).get("png")
    f = library.typ_dir() / png if png else None
    if not f or not f.is_file():
        raise HTTPException(404, "학습 사전에 그 Typical 시트의 그림이 없습니다.")
    return f


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
    if page >= library.LIB_PAGE0:
        return FileResponse(_lib_png(job, page), media_type="image/png", headers={"Cache-Control": "private, max-age=86400"})
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
    return sim.simulate(s, clean, state, timers=_timers(body.get("timers")).get(page))


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
    return sim.scenario(s, target, 1, sheets=_all_sheets(res))


@router.delete("/logic/api/jobs/{job}")
def delete(job: str, author: str = ""):
    """L22 — 첫 화면에서 분석 하나를 지운다 (부서원).  분석 중이면 거절 · 누가 언제 무엇을 지웠는지 남긴다."""
    d = _dir(job)
    st = store.read_status(d)
    if st.get("state") in ("queued", "running"):
        raise HTTPException(409, "분석 중인 묶음은 지울 수 없습니다 — 끝난 뒤에 지우세요.")
    who = (author or "").strip()[:60]
    if not who:
        raise HTTPException(400, "지운 사람 이름이 없습니다 — 누가 지웠는지 남깁니다.")
    store.log_deletion({"job": job, "name": st.get("name"), "project": st.get("project"), "sheets": st.get("sheets"),
                        "created": st.get("created"), "author": who})
    shutil.rmtree(d, ignore_errors=True)
    _SIZES.pop(job, None)
    _APPLIED.pop(job, None)
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
    timers = _timers(body.get("timers"))
    out = sim.simulate_bundle(_all_sheets(res), forces, state, focus, timers=timers)
    out["default_t"] = sim.DEFAULT_T
    return out


def _timers(raw):
    """L15 — 사람이 바꾼 타이머 시간 {쪽: {블록: 초}}.  틀린 값은 버린다 (도면 값 · 기본 5초로 돈다)."""
    if not isinstance(raw, dict):
        return {}
    out = {}
    for pg, d in raw.items():
        if not str(pg).isdigit() or not isinstance(d, dict):
            continue
        c = {str(b): float(v) for b, v in d.items() if sim._secs(v) is not None}
        if c:
            out[int(pg)] = c
    return out


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


# ------------------------------------------------------------------ L22 — 사람이 정한 값 (게이트 종류 · FM/TO · 타이머)

@router.get("/logic/api/jobs/{job}/overrides")
def overrides_get(job: str):
    d = _dir(job)
    ov = overrides.load(d)
    return {**ov, "choices": [{"key": k, "label": overrides.CHOICE_KO[k], "logic": v[1]} for k, v in overrides.CHOICES.items()],
            "mark_kinds": overrides.MARK_KINDS,
            "timers_flat": {str(p): v for p, v in overrides.timers_of(ov).items()}, "default_t": sim.DEFAULT_T}


def _ov_call(fn, *a, **k):
    try:
        return fn(*a, **k)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/logic/api/jobs/{job}/overrides/block")
def overrides_block(job: str, body: dict = Body(...)):
    """게이트 종류 — {page, block, choice | null, author, same_shape?, param?}.  same_shape 면 이 묶음에서 같은
    모양·같은 글자(범례 열쇠)의 판정 못 한 블록에도 같이 정하고, 그 열쇠를 학습 사전에 남긴다 (다른 프로젝트에서도 쓰인다)."""
    d = _dir(job)
    page, bid = body.get("page"), str(body.get("block") or "")
    if not isinstance(page, int) or not bid:
        raise HTTPException(400, "page(정수) 와 block 이 필요합니다.")
    s = _sheet(job, page)
    b = s["blocks"].get(bid)
    if b is None:
        raise HTTPException(404, "그 블록이 없습니다.")
    choice = body.get("choice")
    author = str(body.get("author") or "")
    was = (b.get("user") or {}).get("was_func") or b.get("func", "")
    done = [{"page": page, "block": bid}]
    _ov_call(overrides.set_block, d, page, bid, choice, author, was, body.get("param"))
    key = b.get("key") or ""
    if body.get("same_shape") and choice and library.specific(key):
        for s2 in _result(job)["sheets"]:
            for k2, b2 in s2["blocks"].items():
                if (s2["page"], k2) == (page, bid) or b2.get("key") != key:
                    continue
                if (b2.get("user") or {}).get("was_func", b2.get("func")) != "UNKNOWN":
                    continue
                _ov_call(overrides.set_block, d, s2["page"], k2, choice, author, "UNKNOWN", body.get("param"))
                done.append({"page": s2["page"], "block": k2})
    learned = None
    if choice and library.specific(key):
        func, logic, label, prm = overrides.CHOICES[choice]
        if choice == "VOTE":
            prm = overrides._vote(body.get("param") or {})
        learned = library.learn_user(key, func, logic, label if choice in ("CONST1", "CONST0") else "", author,
                                     store.read_status(d).get("name") or job, param=prm or None)
    return {"set": done, "learned": learned}


@router.post("/logic/api/jobs/{job}/overrides/cell")
def overrides_cell(job: str, body: dict = Body(...)):
    """FM(왼쪽 행) · TO(오른쪽 행) 칸 — {page, side, row, value | null, author}.  저장하면 from-to 연결을 다시 맞댄다."""
    d = _dir(job)
    page, side, n = body.get("page"), body.get("side"), body.get("row")
    if not isinstance(page, int) or not isinstance(n, int):
        raise HTTPException(400, "page · row 는 정수입니다.")
    s = _sheet(job, page)
    row = next((r for r in s.get("table", []) if r["side"] == side and r["n"] == n), None)
    if row is None:
        raise HTTPException(404, "그 행이 없습니다.")
    field = "fm" if side == "L" else "to"
    was = ((row.get("user") or {}).get(field) or {}).get("was", row.get(field) or "")
    v = body.get("value")
    ent = _ov_call(overrides.set_cell, d, page, side, n, None if v is None else str(v), str(body.get("author") or ""), was)
    r2 = next((r for r in _sheet(job, page)["rows"] if r["side"] == side and r["n"] == n), None)
    return {"saved": ent, "ft": (r2 or {}).get("ft"), "ref": (r2 or {}).get("ref")}


@router.get("/logic/api/jobs/{job}/idrate")
def job_idrate(job: str):
    """식별률 (L24) — 시트 이름 · FROM/TO 칸 · 연결 · 게이트 를 얼마나 읽었나 + 못 읽은 것 목록 (사람이 마크업으로 넣는다).
    사람이 얹은 값(마크업 · 칸 · 게이트 종류)까지 반영한 결과로 센다."""
    res = _result(job)
    hit = res.get("_idrate")
    if hit is None:
        hit = res["_idrate"] = idrate.measure(res)
    return hit


@router.post("/logic/api/jobs/{job}/overrides/mark")
def overrides_mark(job: str, body: dict = Body(...)):
    """마크업 (L24) — {page, id?, kind: FROM|TO|SHEET|GATE, rect: [x0,y0,x1,y1], value?, row?, choice?, param?, author}.
    id 와 value·choice 가 모두 없으면 그 마크업을 지운다.  저장 뒤 그 장에서 이 마크업이 어디에 닿았는지 돌려준다."""
    d = _dir(job)
    page = body.get("page")
    if not isinstance(page, int):
        raise HTTPException(400, "page(정수) 가 필요합니다.")
    _sheet(job, page)
    v = body.get("value")
    ent = _ov_call(overrides.set_mark, d, page, body.get("id"), body.get("kind"), body.get("rect"),
                   None if v is None else str(v), str(body.get("author") or ""), body.get("row"),
                   body.get("choice"), body.get("param"))
    s2 = _sheet(job, page)
    mk = next((m for m in s2.get("marks") or [] if m.get("id") == ent.get("id")), None)
    row = None
    if mk and mk.get("n") and mk["kind"] in ("FROM", "TO"):
        side = "L" if mk["kind"] == "FROM" else "R"
        row = next((r for r in s2["rows"] if r["side"] == side and r["n"] == mk["n"]), None)
    return {"saved": ent, "mark": mk, "ft": (row or {}).get("ft"), "ref": (row or {}).get("ref"),
            "sheet_no": s2.get("sheet_no")}


@router.post("/logic/api/jobs/{job}/overrides/timer")
def overrides_timer(job: str, body: dict = Body(...)):
    """타이머 시간 — {page, block, sec | null, author}.  기본은 도면 값 · 도면에 없으면 sim.DEFAULT_T(5초)."""
    d = _dir(job)
    page, bid = body.get("page"), str(body.get("block") or "")
    if not isinstance(page, int) or not bid:
        raise HTTPException(400, "page(정수) 와 block 이 필요합니다.")
    if _sheet(job, page)["blocks"].get(bid) is None:
        raise HTTPException(404, "그 블록이 없습니다.")
    return _ov_call(overrides.set_timer, d, page, bid, body.get("sec"), str(body.get("author") or ""))


@router.get("/logic/api/library")
def library_get():
    """학습 사전 — 모양 열쇠 → 기능 · Typical 시트 (어느 묶음 · 누가 가르쳤는지)."""
    return library.summary()


# ------------------------------------------------------------------ L25 가르치기

_REGION = {}                      # (job, kind, page, rect) → 모든 장에서 읽은 값 (미리보기 → 저장이 같은 값을 쓴다)


def _teach_source(job):
    """질문을 만들 결과 — 끝난 분석이면 사람 값을 얹은 결과, 분석 중이면 지금까지 읽은 장(partial.json · L25)."""
    d = _dir(job)
    if (d / "result.json").exists():
        return _result(job), True
    part = store.read_partial(d)
    if not part:
        raise HTTPException(409, "아직 질문을 낼 만큼 읽은 장이 없습니다 — 잠시 뒤에 다시 보세요.")
    ov = overrides.load(d)
    if overrides.has_any(ov):
        overrides.apply(part, ov, [])
    return part, False


@router.get("/logic/api/jobs/{job}/teach")
def teach_get(job: str):
    """남은 질문 — 무리마다 하나 · 해결하는 건수 순 · 보기 장은 가장 적은 장에 몰아서.  이미 답한 규칙도 함께."""
    res, done = _teach_source(job)
    q = teach.questions(res, overrides.load(_dir(job)).get("teach"))
    q["final"] = done
    q["partial"] = None if done else {"sheets": len(res.get("sheets", [])), "pages": res.get("pdf_pages")}
    ov = overrides.load(_dir(job))
    t = ov.get("teach") or {}
    q["answered"] = {"gates": [{"id": r.get("id"), "choice": r.get("choice"), "text": (r.get("sig") or {}).get("text"),
                                "sig": r.get("sig"), "fig": r.get("fig"),
                                "author": r.get("author"), "at": r.get("at"), "example": r.get("example")}
                               for r in t.get("gates") or []],
                     "sheet": bool(t.get("sheet")), "cols": sorted((t.get("cols") or {}).keys()),
                     "links": t.get("links") or {}, "skipped": t.get("skipped") or []}
    q["choices"] = [{"id": k, "ko": overrides.CHOICE_KO.get(k, k)} for k in overrides.CHOICES]
    # 학습 사전(다른 묶음에서 사람이 가르친 답)으로 읽은 블록 — 질문에 안 나오므로 몇 개인지 말한다
    q["from_library"] = sum(1 for s in res.get("sheets", []) for b in s.get("blocks", {}).values()
                            if (b.get("user") or {}).get("from") == "library")
    return q


def _region_values(job, kind, page, rect):
    d = _dir(job)
    res, _ = _teach_source(job)
    try:
        r = [round(float(v), 1) for v in rect]
    except (TypeError, ValueError):
        raise HTTPException(400, "사각형(x0, y0, x1, y1)이 없습니다.")
    key = (job, kind, int(page), tuple(r), len(res.get("sheets", [])))
    if key not in _REGION:
        if len(_REGION) > 16:
            _REGION.clear()
        side = None if kind == "SHEET" else ("L" if kind == "FROM" else "R")
        _REGION[key] = teach.read_region(str(d / "source.pdf"), res, int(page), r, side)
    return _REGION[key], res


@router.post("/logic/api/jobs/{job}/teach/preview")
def teach_preview(job: str, body: dict = Body(...)):
    """한 장에서 두른 자리를 모든 장에서 읽어 보여 준다 — 저장 전에 무엇이 들어갈지 본다.  {kind: SHEET|FROM|TO, page, rect}."""
    kind = str(body.get("kind") or "").upper()
    if kind not in ("SHEET", "FROM", "TO") or not isinstance(body.get("page"), int):
        raise HTTPException(400, "kind(SHEET · FROM · TO) 와 page 가 필요합니다.")
    vals, res = _region_values(job, kind, body["page"], body.get("rect"))
    by_page = {s["page"]: s for s in res.get("sheets", [])}
    if kind == "SHEET":
        empty = [s["page"] for s in res["sheets"] if not s.get("library") and not s.get("sheet_no")]
        fill = [p for p in empty if vals.get(p)]
        names = [vals[p] for p in fill]
        dup = sorted({n for n in names if names.count(n) >= 3})
        return {"read": len(vals), "fills": len(fill), "missing": len(empty), "same_everywhere": dup,
                "sample": [{"page": p, "value": vals[p], "now": by_page[p].get("sheet_no") or ""} for p in sorted(vals)[:40]]}
    n = sum(len(v) for v in vals.values())
    return {"read": n, "pages": len(vals),
            "sample": [{"page": p, "row": int(k), "value": v} for p in sorted(vals)[:6] for k, v in sorted(vals[p].items(), key=lambda x: int(x[0]))[:6]]}


@router.post("/logic/api/jobs/{job}/teach")
def teach_post(job: str, body: dict = Body(...)):
    """질문 하나에 답한다 — {kind: GATE|SHEET|FROM|TO|LINK|SKIP, author, …}.
    GATE {qid, sig, fig, choice | null, param?} · SHEET/FROM/TO {page, rect | null} · LINK {target, mode: OTHER|ALIAS|null, sheet?} ·
    SKIP {qid, undo?}.  답한 뒤의 식별률과 남은 질문 수를 돌려준다."""
    d = _dir(job)
    kind = str(body.get("kind") or "").upper()
    author = str(body.get("author") or "")
    if kind == "GATE":
        ex = body.get("example") if isinstance(body.get("example"), dict) else {}
        ent = _ov_call(overrides.teach_gate, d, body.get("qid"), body.get("sig"), body.get("fig"), body.get("choice"),
                       author, body.get("param"), ex)
        if body.get("choice") and body.get("learn", True):
            try:
                library.learn_rule(ent, job)
            except Exception:
                pass
        elif body.get("choice") is None:
            try:
                library.learn_rule({"sig": body.get("sig") or {}, "fig": body.get("fig") or "", "choice": None}, job)
            except Exception:
                pass
    elif kind in ("SHEET", "FROM", "TO"):
        side = None if kind == "SHEET" else ("L" if kind == "FROM" else "R")
        if body.get("rect") is None:
            ent = _ov_call(overrides.teach_region, d, kind, None, None, None, author, side)
        else:
            if not isinstance(body.get("page"), int):
                raise HTTPException(400, "page(정수) 가 필요합니다.")
            vals, _ = _region_values(job, kind, body["page"], body["rect"])
            ent = _ov_call(overrides.teach_region, d, kind, body["page"], body["rect"], vals, author, side)
    elif kind == "LINK":
        ent = _ov_call(overrides.teach_link, d, body.get("target"), body.get("mode"), body.get("sheet"), author)
    elif kind == "SKIP":
        ent = _ov_call(overrides.teach_skip, d, str(body.get("qid") or ""), author, bool(body.get("undo")))
    else:
        raise HTTPException(400, "kind 는 GATE · SHEET · FROM · TO · LINK · SKIP 입니다.")
    out = {"saved": ent}
    if (d / "result.json").exists():
        res = _result(job)
        m = res.get("_idrate") or idrate.measure(res)
        res["_idrate"] = m
        out["idrate"] = {"overall": m["overall"], "rate": m["rate"], "low": m["low"], "unread": m["unread"]}
    return out


@router.get("/logic/api/jobs/{job}/teach/crop.png")
def teach_crop(job: str, page: int, x0: float, y0: float, x1: float, y1: float):
    """질문의 보기 그림 — 그 장의 한 자리를 잘라 보인다 (분석이 끝나기 전에도 · 원본 PDF 에서)."""
    d = _dir(job)
    if not (x1 > x0 and y1 > y0) or x1 - x0 > 2000 or y1 - y0 > 2000:
        raise HTTPException(400, "자리가 이상합니다.")
    try:
        doc = pymupdf.open(d / "source.pdf")
        pg = doc[page - 1]
        z = max(1.5, min(5.0, 260 / max(x1 - x0, y1 - y0)))
        pix = pg.get_pixmap(matrix=pymupdf.Matrix(z, z), clip=pymupdf.Rect(x0, y0, x1, y1))
        return Response(pix.tobytes("png"), media_type="image/png", headers={"Cache-Control": "max-age=3600"})
    except (IndexError, RuntimeError, ValueError):
        raise HTTPException(404, "그 장을 그리지 못했습니다.")
