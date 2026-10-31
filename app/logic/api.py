"""LOGIC 검토 API — /logic (화면) · /logic/api/* (데이터).  main.py 는 이 라우터를 붙이기만 한다."""
from __future__ import annotations

import json
import os

import shutil
import time
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import quote

import pymupdf
from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response

from app import page_stamp, paths

from . import analog, aop_trace, aops, fromto, idrate, library, memo, overrides, projects, report, sim, store, teach

router = APIRouter()
ZOOM = store.ZOOM
_SIZES = {}                     # job → {page: [w, h]} — 쪽 크기는 PDF 를 한 번만 연다 (L7)


def _static(name):
    return paths.resource("app", "static", name)


@router.get("/logic")
def logic_page():
    return page_stamp.page("logic.html")


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


def _project_jobs(name: str) -> list:
    return [j for j in store.jobs() if (j.get("project") or "") == name]


@router.get("/logic/api/projects/{name}/delete_preview")
def project_delete_preview(name: str):
    """프로젝트를 지우기 전에 — 함께 지워질 분석 수 · 분석 중인 것."""
    if not projects.exists(name):
        raise HTTPException(404, f"프로젝트가 없습니다: {name}")
    js = _project_jobs(name)
    return {"name": name, "jobs": len(js), "sheets": sum(j.get("sheets") or 0 for j in js),
            "running": [j["id"] for j in js if j.get("state") in ("queued", "running")],
            "authors": sorted({j.get("author") for j in js if j.get("author")})}


@router.delete("/logic/api/projects/{name}")
def delete_project(name: str, author: str = "", confirm: str = ""):
    """프로젝트 하나와 그 분석 전부를 지운다.  이름을 옮겨 적어야 하고(실수 방지) 분석 중이면 거절 ·
    누가 언제 무엇을 지웠는지 남긴다.  학습 사전(다른 프로젝트도 쓰는 기호 · Typical)은 남긴다."""
    if not projects.exists(name):
        raise HTTPException(404, f"프로젝트가 없습니다: {name}")
    who = (author or "").strip()[:60]
    if not who:
        raise HTTPException(400, "지운 사람 이름이 없습니다 — 누가 지웠는지 남깁니다.")
    if confirm.strip() != name:
        raise HTTPException(400, "확인 칸에 프로젝트 이름을 그대로 적어야 지웁니다.")
    js = _project_jobs(name)
    if any(j.get("state") in ("queued", "running") for j in js):
        raise HTTPException(409, "이 프로젝트에 분석 중인 묶음이 있습니다 — 끝난 뒤에 지우세요.")
    for j in js:
        store.log_deletion({"job": j["id"], "name": j.get("name"), "project": name, "sheets": j.get("sheets"),
                            "created": j.get("created"), "author": who, "with_project": True})
        shutil.rmtree(store.job_dir(j["id"]), ignore_errors=True)
        _SIZES.pop(j["id"], None)
        _APPLIED.pop(j["id"], None)
    projects.remove(name)
    store.log_deletion({"project": name, "kind": "project", "jobs": len(js), "author": who})
    return {"deleted": name, "jobs": len(js)}


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


_RESULT_LOCK = threading.RLock()   # L28 — 화면이 열 때 요청 대여섯을 함께 보낸다 · 같은 결과를 동시에 준비(설정값 · from-to · 사람 값)하지 않게


_LAST_REQ = [0.0]                 # L68 — 화면 요청이 마지막으로 결과를 찾은 때 (뒤에서 도는 미리 계산이 그 사이에 끼지 않게)


def _result(job):
    _LAST_REQ[0] = time.monotonic()
    with _RESULT_LOCK:
        return _result_locked(job)


WARM_QUIET = 1.2                  # L68 — 묶음을 연 뒤 화면 요청이 이만큼(초) 조용해지면 미리 계산을 시작한다
WARM_WAIT_MAX = 15.0              # 그래도 이만큼 지나면 시작한다


def _wait_quiet():
    """묶음을 열면 화면이 요청 열 개 남짓(시트 · 그림 · 점검 · 가르치기 · 식별률 …)을 함께 보낸다.  미리 계산(827장
    시뮬레이션 · 1~2초)이 그 사이에 같은 파이썬을 쥐면 첫 시트가 늦게 선다 — 요청이 잦아든 뒤에 돈다.  답은 그대로다."""
    t0 = time.monotonic()
    while time.monotonic() - t0 < WARM_WAIT_MAX and time.monotonic() - _LAST_REQ[0] < WARM_QUIET:
        time.sleep(0.2)


def _lru_put(cache, key, value, keep=3):
    cache.pop(key, None)
    cache[key] = value
    while len(cache) > keep:
        cache.pop(next(iter(cache)))


def _result_locked(job):
    d = _dir(job)
    if not (d / "result.json").exists():
        raise HTTPException(409, "아직 분석이 끝나지 않았습니다.")
    res = store.read_result(d, (_prepared_load, lambda r: _prepare(job, d, r)))
    _drawing_sp(job, d, res)                 # L26 — 감시 블록 위에 인쇄한 설정값 (다시 분석 없이) · L30 연산자 입력 이름 · 안 그림
    _identify(res)                           # L30 — 아날로그 연산자 · 표시등 이름 (다시 분석 없이 · 결과마다 한 번)
    if not res.get("_ft"):                   # 예전 결과도 다시 분석 없이 FM ↔ TO 대조 (L5) — 캐시된 결과에는 한 번만 (L7)
        fromto.check(res["sheets"])
        res["_ft"] = True
    # L22 — 사람이 정한 값(게이트 종류 · FM/TO · 타이머)을 얹는다.  분석 결과 파일은 그대로이고 사본에 얹는다.
    # L25 — 다른 묶음에서 사람이 가르친 게이트 규칙(학습 사전)도 얹는다 (그 묶음의 규칙이 이기고, 블록 하나를 정한 것이 더 이긴다)
    lm = library.mtime()
    lib_rules = _lib_rules(lm, job)
    # L29 — 사전 파일이 바뀌어도(다른 묶음을 배움) 이 묶음에 닿는 규칙이 같으면 캐시를 버리지 않는다 — 열쇠는 규칙 내용
    lm = _rules_key(lib_rules)
    om = overrides.mtime(d)
    if om is None and not lib_rules:
        _APPLIED.pop(job, None)
        return res
    rm = (d / "result.json").stat().st_mtime_ns
    hit = _APPLIED.get(job)
    if hit and hit[0] == rm and hit[1] == om and hit[3] == lm:
        return hit[2]
    ov = overrides.load(d) if om is not None else overrides.empty()
    if not overrides.has_any(ov) and not _memo(res, "libhits", lambda: _lib_hits(res, lib_rules), lm):
        return res
    # L28 — 37MB 결과를 통째로 다시 읽지 않는다: 사람 값이 고치는 칸(블록 · 단자 · 행 · 점검)만 복사한 사본에 얹는다
    # (원본 캐시는 그대로 — 시험이 원본 불변과 '다시 읽어 얹은 것과 같음' 을 못박는다)
    fresh = overrides.working_copy(res)
    overrides.apply(fresh, ov, lib_rules)
    fresh["_ft"] = True
    _lru_put(_APPLIED, job, (rm, om, fresh, lm))
    _warm_bundle(job, fresh)                 # L68 — 사람 값을 고친 뒤 첫 시뮬레이션도 기다리지 않게 (바뀐 장만 다시 센다 — L28)
    return fresh


_LIB_RULES = {}
_SP = {}

# ------------------------------------------------------------------ L68 — 준비한 결과 사본 (다시 열 때 가볍게)
# 결과를 처음 읽으면 37MB JSON 을 풀고(0.7초) 도면 설정값 · 연산자 이름 · from-to 대조를 얹는다(0.7초) — 서버를 다시
# 켤 때마다 · 결과 기억(3개)에서 밀려날 때마다 · 회사 PC 에서는 몇 배로.  얹은 뒤의 결과를 분석 폴더에 marshal 로
# 남기고(파이썬 내장 · 코드를 실행하지 않는 형식) 다음에는 그것을 읽는다 (0.25초).  열쇠는 result.json(시각 · 크기) ·
# 설정값 규칙 판 · 이 판단에 닿는 코드 · 설정 파일 내용 · 파이썬 판 — 하나라도 다르면 예전처럼 JSON 을 읽고 다시 남긴다.
# 사람 값은 얹지 않는다 (그것은 늘 사본에 얹는다 — L28).  답은 같다 (시험이 JSON 길과 맞댄다).
PREPARED = "prepared.bin"


def _code_fp():
    import hashlib
    h = hashlib.blake2b(digest_size=12)
    here = Path(__file__).resolve().parent
    for p in sorted(here.glob("*.py")) + sorted(paths.resource("config").glob("logic_*")):
        try:
            h.update(p.name.encode()); h.update(p.read_bytes())
        except OSError:
            pass
    h.update(sys.version.encode())
    if paths.frozen():                      # exe 에는 .py 가 디스크에 없다 — exe 자신(크기 · 시각)이 코드 판이다
        try:
            st = Path(sys.executable).stat()
            h.update(f"{sys.executable}:{st.st_size}:{st.st_mtime_ns}".encode())
        except OSError:
            h.update(os.urandom(8))         # 모르면 매번 다르게 — 사본을 쓰지 않는다 (예전처럼 JSON 을 읽는다)
    return h.hexdigest()


def _prepared_key(d):
    fp = _code_fp_cached()
    st = (d / "result.json").stat()
    return f"{st.st_mtime_ns}:{st.st_size}:{SP_VERSION}:{fp}".encode()


def _code_fp_cached(_box=[]):
    if not _box:
        _box.append(_code_fp())
    return _box[0]


def _prepared_load(d):
    import marshal
    try:
        key = _prepared_key(d)
        b = (d / PREPARED).read_bytes()
    except OSError:
        return None
    if not b.startswith(key + b"\n"):
        return None
    try:
        res = marshal.loads(b[len(key) + 1:])
    except Exception:
        return None
    return res if isinstance(res, dict) and res.get("_ft") else None


def _prepare(job, d, res):
    """처음 읽은 결과에 얹을 것을 얹고(아래 _result_locked 와 같은 함수 · 같은 순서) 사본을 남긴다.  못 남겨도 그만이다."""
    import marshal
    _drawing_sp(job, d, res)
    _identify(res)
    fromto.check(res["sheets"])
    res["_ft"] = True
    sz = _read_sizes(d)
    if sz:
        res["_page_sizes"] = [sz.get(i + 1, [0.0, 0.0]) for i in range(max(sz))]
    try:
        key = _prepared_key(d)
        data = marshal.dumps(res)
    except Exception:
        return

    def write():
        tmp = d / (PREPARED + f".tmp{os.getpid()}.{threading.get_ident()}")
        try:
            with open(tmp, "wb") as f:
                f.write(key + b"\n"); f.write(data)
            store._replace(tmp, d / PREPARED)
        except OSError:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
    threading.Thread(target=write, daemon=True).start()


def _identify(res):
    if res.get("_aop"):
        return
    from .analyse import _findings
    by_page = {s["page"]: s for s in res["sheets"]}
    for pg in aops.identify(res["sheets"]):
        by_page[pg]["findings"] = _findings(by_page[pg])
    res["_aop"] = True


def _drawing_sp(job, d, res):
    """L26 — 감시 블록(HHH · HH …) 바로 위에 도면이 인쇄한 설정값을 블록 param 에 얹는다.  PDF 는 결과마다 한 번만 읽는다."""
    if res.get("_sp"):
        return
    try:
        rm = (d / "result.json").stat().st_mtime_ns
    except OSError:
        rm = None
    hit = _SP.get(job)
    if hit is None or hit[0] != rm:
        got = _sp_disk(d, rm)                # L28 — 한 번 읽은 설정값은 분석 폴더에 남긴다 (서버를 다시 켜도 PDF 를 다시 안 읽는다)
        if got is None:
            got = _sp_read(d, res) if rm else {}
            _sp_save(d, rm, got)
        if len(_SP) > 6:
            _SP.clear()
        _SP[job] = hit = (rm, got)
    for s in res["sheets"]:
        for bid, b in s["blocks"].items():
            e = hit[1].get((s["page"], bid))
            if e:
                b.setdefault("param", {}).update(e)
        for coll in (s.get("rows", []), s.get("table", [])):
            for r in coll:
                e = hit[1].get((s["page"], "row:%d" % r["n"])) if r["side"] == "L" else None
                if e:
                    r["range"] = dict(e)
    res["_sp"] = True


SP_VERSION = "2.%d" % aops.IDENT_VERSION                   # L28 — analog.read_drawing 규칙을 바꾸면 올린다 (분석 폴더의 drawing_sp.json 을 다시 만든다)


def _sp_read(d, res):
    """감시 블록 · 입력 행에 도면이 인쇄한 값을 읽는다.  결과는 건드리지 않는다 — read_drawing 이 고치는
    칸(블록 param · 행)만 얕게 복사한 가벼운 사본에 읽는다 (예전에는 result.json 을 통째로 다시 읽었다)."""
    probe = []
    for s in res["sheets"]:
        probe.append({**s, "blocks": {k: {**b, "param": dict(b.get("param") or {})} for k, b in s["blocks"].items()},
                      "rows": [dict(r) for r in s.get("rows", [])]})
    analog.read_drawing(d / "source.pdf", probe)
    got = {}
    for s in probe:
        for bid, b in s["blocks"].items():
            p = b.get("param") or {}
            if analog.monitor_kind(b) and ("sp" in p or "sp_label" in p):
                got[(s["page"], bid)] = {k: p[k] for k in ("sp", "sp_unit", "sp_text", "sp_label", "sp_level") if k in p}
            elif any(k in p for k in ("pins", "a_const", "a_drawing", "aop_fig")):
                got[(s["page"], bid)] = {k: p[k] for k in ("pins", "a_const", "a_drawing", "aop_fig") if k in p}
        for r in s["rows"]:
            if r.get("range"):
                got[(s["page"], "row:%d" % r["n"])] = r["range"]
    return got


def _sp_disk(d, rm):
    try:
        x = __import__("json").loads((d / "drawing_sp.json").read_text(encoding="utf-8"))
    except Exception:
        return None
    if x.get("rm") != rm or x.get("v") != SP_VERSION:
        return None
    return {(int(pg), k): v for pg, k, v in x.get("got") or []}


def _sp_save(d, rm, got):
    try:
        store._atomic(d / "drawing_sp.json", __import__("json").dumps(
            {"rm": rm, "v": SP_VERSION, "got": [[pg, k, v] for (pg, k), v in sorted(got.items(), key=lambda x: (x[0][0], x[0][1]))]},
            ensure_ascii=False))
    except Exception:
        pass


def _rules_key(rules):
    return __import__("hashlib").blake2b(json.dumps(rules, sort_keys=True, default=str).encode(), digest_size=12).hexdigest() \
        if rules else ""


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
        got = _result(job).get("_page_sizes")      # L68 — 준비한 결과 사본에 함께 남긴 쪽 크기 (846쪽을 다시 열지 않는다 · 0.2초)
        sz = {i + 1: list(v) for i, v in enumerate(got)} if isinstance(got, list) else _read_sizes(d)
        _SIZES[job] = sz
    return sz.get(page)


def _read_sizes(d):
    sz = {}
    try:
        doc = pymupdf.open(d / "source.pdf")
        for i, pg in enumerate(doc):
            r = pg.rect
            sz[i + 1] = [r.width, r.height]
    except Exception:
        pass
    return sz


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
    if (not f or not f.is_file()) and (s.get("library") or {}).get("id"):
        f = library.ensure_png(s["library"]["id"])       # L63 — 씨앗 Typical 은 그림을 싣지 않는다 → 처음 볼 때 그 그림을 그린다
    if not f or not f.is_file():
        raise HTTPException(404, "학습 사전에 그 Typical 시트의 그림이 없습니다.")
    return f


def _memo(res, name, fn, *key):
    """L28 — 결과 하나에 한 번만 센다 (사람 값을 고치면 결과가 새 사본이 되어 다시 센다)."""
    m = res.setdefault("_memo", {})
    k = json.dumps([name, *key], default=str)
    if k not in m:
        m[k] = fn()
    return m[k]


@router.get("/logic/api/jobs/{job}/sheets")
def sheets(job: str):
    res = _result(job)
    _warm_bundle(job, res)
    _warm_pages(job, res)
    return _memo(res, "sheets", lambda: _sheets_body(res))


_PAGES_WARM = {}                  # job → 미리 그리기 프로세스 (서버 하나에 묶음마다 한 번)


def _warm_pages(job, res):
    """L31 — 그림이 아직 없는 시트가 있으면 따로 된 프로세스가 미리 그린다 — 시트를 처음 열 때 서버가 그 자리에서
    그리느라(A3 한 장 0.2~0.3초) 기다리지 않게.  분석이 끝날 때 이미 다 그렸으면(L7) 아무 일도 안 한다."""
    import os
    if os.environ.get("PID_LOGIC_WARM", "1") == "0" or job in _PAGES_WARM:
        return
    d = _dir(job)
    have = {f.name for f in (d / "pages").glob("p*_z*.png")} if (d / "pages").is_dir() else set()
    missing = [s for s in res["sheets"] if f"p{s['page']}_z{ZOOM}.png" not in have]
    _PAGES_WARM[job] = None
    if not missing:
        return
    if paths.frozen():
        from .run import prerender_missing
        threading.Thread(target=prerender_missing, args=(d,), daemon=True).start()
        return
    root = Path(__file__).resolve().parent.parent.parent
    try:
        _PAGES_WARM[job] = subprocess.Popen([sys.executable, "-m", "app.logic.run", "--pages", str(d)], cwd=str(root),
                                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def _warm_bundle(job, res):
    """L28 — 묶음을 열면 시뮬레이션 첫 계산(모든 장을 한 번)을 뒤에서 미리 해 둔다 — '동작 시뮬레이션' 을 처음
    누를 때 기다리지 않게.  결과는 같은 기억에 들어갈 뿐이라 답은 그대로다."""
    import os
    if os.environ.get("PID_LOGIC_WARM", "1") == "0":
        return
    cache = _bundle_cache(job, res)
    if cache.get("topo") is not None or cache.get("_warming"):
        return
    cache["_warming"] = True

    def go():
        try:
            _wait_quiet()
            with cache.setdefault("_lock", threading.Lock()):
                if cache.get("topo") is None:
                    sim.simulate_bundle(_all_sheets(res), {}, {}, None, cache=cache)
        except Exception:
            pass
    threading.Thread(target=go, daemon=True).start()


def _sheets_body(res):
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
    return _memo(res, "findings", lambda: report.findings(res["sheets"]))


@router.get("/logic/test")
def logic_test_page():
    """L36 — 블록 그룹 시험 대시보드."""
    return page_stamp.page("logic_test.html")


def _learned(job, start=True):
    from . import behavior
    d = _dir(job)
    cur = behavior.load(d)
    fresh = bool(cur) and cur.get("key") == behavior.key_of(d)
    if not fresh and start:
        behavior_get(job, 1)
        cur = behavior.load(d)
        fresh = bool(cur) and cur.get("key") == behavior.key_of(d)
    return cur, fresh


@router.get("/logic/api/jobs/{job}/groups")
def groups_get(job: str):
    """L36 — 장비(블록 그룹)마다 배운 동작과 마지막 시험 결과.  배운 것이 없거나 낡았으면 뒤에서 다시 배운다."""
    from . import behavior, grouptest
    d = _dir(job)
    if not (d / "result.json").exists():
        raise HTTPException(409, "아직 분석이 끝나지 않았습니다.")
    st = behavior_get(job, 1)
    cur = st["result"]
    tested = grouptest.load(d)
    gs = grouptest.groups(cur)
    key = cur.get("key") if cur else None
    for g in gs:
        r = (tested.get("groups") or {}).get(g["equip"])
        g["test"] = None if not r else {k: r.get(k) for k in ("status", "counts", "author", "at", "seconds")} | {
            "stale": r.get("key") != key}
    status = store.read_status(d)
    return {"state": st["state"], "progress": st["progress"], "error": st.get("error"),
            "name": status.get("name"), "project": status.get("project"),
            "summary": (cur or {}).get("summary"), "learned_at": (cur or {}).get("learned_at"),
            "groups": gs, "history": (tested.get("history") or [])[-30:]}


@router.post("/logic/api/jobs/{job}/grouptest")
def grouptest_run(job: str, body: dict = Body(default={})):
    """L36 — 장비 하나 원 버튼 시험.  지금 결과(사람이 고친 값까지)로 배운 것을 다시 돌린다."""
    from . import grouptest
    equip = str(body.get("equip") or "")
    if not equip:
        raise HTTPException(400, "equip 가 필요합니다.")
    cur, fresh = _learned(job, start=False)
    if not cur:
        raise HTTPException(409, "아직 동작을 배우는 중입니다 — 잠시 뒤 다시 누르세요.")
    items = grouptest.items_of(cur, equip)
    if not items:
        raise HTTPException(404, f"'{equip}' 장비를 배운 것이 없습니다.")
    res = _result(job)
    sheets = _all_sheets(res)
    cache = _bundle_cache(job, res)
    with cache.setdefault("_lock", threading.Lock()):
        out = grouptest.test_group(sheets, items, cache, _timers(body.get("timers")))
        cache.pop("_last_results", None)
    out = grouptest.save(_dir(job), equip, out, str(body.get("author") or "")[:60], cur.get("key"))
    out["learned_fresh"] = fresh
    return out


@router.get("/logic/api/jobs/{job}/grouptest")
def grouptest_get(job: str, equip: str):
    from . import grouptest
    r = (grouptest.load(_dir(job)).get("groups") or {}).get(equip)
    if not r:
        raise HTTPException(404, "아직 시험하지 않았습니다.")
    return r


@router.get("/logic/api/jobs/{job}/grouptest.xlsx")
def grouptest_xlsx(job: str):
    from . import grouptest
    d = _dir(job)
    cur, _ = _learned(job, start=False)
    name = store.read_status(d).get("name") or "logic"
    data = grouptest.workbook(cur, grouptest.load(d), name)
    fn = Path(name).stem + "_group_test.xlsx"
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment; filename*=UTF-8''" + quote(fn)})


# ───────────────── L78 — 시운전 단계 · System Description (Word) ─────────────────

_SYSDESC = {}                       # 분석 → {"state", "done", "total", "error", "key", "at"}
_SYSDESC_LOCK = threading.Lock()


@router.get("/logic/commission")
def logic_commission_page():
    """L78 — 시운전 단계별 동작 · 단계마다 시뮬레이션."""
    return page_stamp.page("logic_commission.html")


def _dangling_text(res):
    """연결 안 된 선 끝 — 로직(G) · 루프(P) · Typical 시트로 갈라 센다 (분석의 C1 점검 그대로)."""
    from . import refs as _refs
    n = {"G": 0, "P": 0, "T": 0}
    for s in res.get("sheets") or []:
        k = _refs.series(s.get("sheet_no") or "") or "T"
        k = k if k in n else "T"
        n[k] += sum(1 for f in s.get("findings") or [] if f.get("code") == "C1_DANGLING")
    return f"로직(G) 시트 {n['G']} · 루프(P) 시트 {n['P']} · Typical/범례 시트 {n['T']}"


@router.get("/logic/api/jobs/{job}/commission")
def commission_get(job: str):
    from . import commission
    d = _dir(job)
    res = _result(job)
    st = behavior_get(job, 1)
    cur = st["result"]
    status = store.read_status(d)
    out = {"state": st["state"], "progress": st["progress"], "name": status.get("name"), "project": status.get("project"),
           "summary": (cur or {}).get("summary"), "dangling": _dangling_text(res), "systems": []}
    if cur:
        out["systems"] = _memo(res, "commission:" + str(cur.get("key")), lambda: commission.overview(res, cur))
    with _SYSDESC_LOCK:
        out["sysdesc"] = dict(_SYSDESC.get(job) or {}) or None
    if (d / "sysdesc.docx").exists():
        out["sysdesc_file"] = (d / "sysdesc.docx").stat().st_mtime
    return out


def _commission_steps(job, equip):
    from . import commission
    cur, _ = _learned(job, start=False)
    if not cur:
        raise HTTPException(409, "아직 동작을 배우는 중입니다 — 잠시 뒤 다시 누르세요.")
    res = _result(job)
    st = _memo(res, "commission-structure:" + str(cur.get("key")), lambda: commission.structure(res, cur))
    e = st["equips"].get(equip)
    if not e:
        raise HTTPException(404, f"'{equip}' 장비를 배운 것이 없습니다.")
    sheets = _all_sheets(res)
    cache = _bundle_cache(job, res)
    rk = "commission-resolver:" + str(cur.get("key"))
    with cache.setdefault("_lock", threading.Lock()):
        resolve = _memo(res, rk, lambda: commission.resolver(res, cur, sheets, cache, 20.0))
        steps = commission.steps_of(e["items"], None, resolve)
    return res, sheets, cache, e, steps


@router.get("/logic/api/jobs/{job}/commission/steps")
def commission_steps(job: str, equip: str):
    _, _, _, e, steps = _commission_steps(job, equip)
    return {"equip": equip, "sheets": e["sheets"], "deps": e["deps"], "steps": steps}


@router.post("/logic/api/jobs/{job}/commission/run")
def commission_run(job: str, body: dict = Body(default={})):
    """단계마다 시뮬레이션 — upto 가 있으면 그 단계까지 (앞 단계의 상태를 이어서)."""
    from . import commission
    equip = str(body.get("equip") or "")
    if not equip:
        raise HTTPException(400, "equip 가 필요합니다.")
    res, sheets, cache, e, steps = _commission_steps(job, equip)
    upto = body.get("upto")
    upto = int(upto) if isinstance(upto, (int, float)) or (isinstance(upto, str) and upto.isdigit()) else None
    t0 = time.time()
    with cache.setdefault("_lock", threading.Lock()):
        out = commission.run_steps(sheets, steps, cache, _timers(body.get("timers")), upto)
        cache.pop("_last_results", None)
    out.update(equip=equip, seconds=round(time.time() - t0, 2))
    return out


@router.post("/logic/api/jobs/{job}/sysdesc")
def sysdesc_start(job: str):
    """System Description(Word) 만들기 — 뒤에서 (장비마다 시운전 단계까지 · AMIRAL 약 1분)."""
    from . import commission
    d = _dir(job)
    cur, _ = _learned(job, start=False)
    if not cur:
        raise HTTPException(409, "아직 동작을 배우는 중입니다 — 끝나면 만들 수 있습니다.")
    with _SYSDESC_LOCK:
        now = _SYSDESC.get(job) or {}
        if now.get("state") == "running":
            return now
        _SYSDESC[job] = {"state": "running", "done": 0, "total": 0, "at": time.time()}
    res = _result(job)

    def go():
        try:
            def prog(i, n):
                with _SYSDESC_LOCK:
                    _SYSDESC[job].update(done=i, total=n)
            status = store.read_status(d)
            rv = status.get("review") or {}
            cache = _bundle_cache(job, res)
            with cache.setdefault("_lock", threading.Lock()):
                data = commission.docx_bytes(res, cur, status, review=rv if isinstance(rv, dict) else None,
                                             dangling=_dangling_text(res), progress=prog)
                cache.pop("_last_results", None)
            tmp = d / f"sysdesc.docx.tmp{os.getpid()}"
            tmp.write_bytes(data)
            store._replace(tmp, d / "sysdesc.docx")
            with _SYSDESC_LOCK:
                _SYSDESC[job].update(state="done", at=time.time(), size=len(data))
        except Exception as ex:
            with _SYSDESC_LOCK:
                _SYSDESC[job].update(state="failed", error=str(ex))
    threading.Thread(target=go, daemon=True).start()
    return _SYSDESC[job]


@router.get("/logic/api/jobs/{job}/sysdesc.docx")
def sysdesc_file(job: str):
    d = _dir(job)
    p = d / "sysdesc.docx"
    if not p.exists():
        raise HTTPException(404, "아직 만들지 않았습니다 — '시스템 설명서 만들기' 를 누르세요.")
    name = store.read_status(d).get("name") or "logic"
    fn = Path(name).stem + "_System_Description.docx"
    return FileResponse(p, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        headers={"Content-Disposition": "attachment; filename*=UTF-8''" + quote(fn)})


@router.get("/logic/api/jobs/{job}/report.xlsx")
def report_xlsx(job: str):
    res = _result(job)
    d = _dir(job)
    name = store.read_status(d).get("name") or "logic"
    data = report.workbook(res, name)
    fn = Path(name).stem + "_logic_review.xlsx"
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment; filename*=UTF-8''" + quote(fn)})


def _review(job, start=True):
    """L39 — 정합성 검토 결과.  결과 · 사람 값 · 동작 학습이 같으면 저장한 것을, 바뀌었으면 다시 모은다 (1~2초).
    동작 학습이 아직이면 뒤에서 배우게 하고 정적 검토(from-to · 선 · 게이트 · 읽기)만으로 먼저 낸다."""
    from . import review
    d = _dir(job)
    if not (d / "result.json").exists():
        raise HTTPException(409, "아직 분석이 끝나지 않았습니다.")
    beh = behavior_get(job, 1 if start else 0)
    cur = review.load(d)
    if cur and cur.get("key") == review.key_of(d):
        return cur, beh
    with _REVIEW_LOCK.setdefault(job, threading.Lock()):
        cur = review.load(d)
        if cur and cur.get("key") == review.key_of(d):
            return cur, beh
        res = _result(job)
        cache = _bundle_cache(job, res)
        with cache.setdefault("_lock", threading.Lock()):
            try:
                cur = review.build_dir(d, res, cache)
            finally:
                cache.pop("_last_results", None)
    try:
        st = store.read_status(d)
        st["review"] = review.summary_of(cur)
        store.write_status(d, st)
    except Exception:
        pass
    return cur, beh


_REVIEW_LOCK = {}


@router.get("/logic/api/jobs/{job}/review")
def review_get(job: str):
    """L39 — 정합성 검토 결과 한 장 (설계 오류 · 설계 확인 · 읽기 빈틈 · 툴 판정율)."""
    cur, beh = _review(job)
    out = review_mod().with_marks(cur, review_mod().load_marks(_dir(job)))
    out["learning"] = {"state": beh["state"], "progress": beh["progress"]}
    out["name"] = store.read_status(_dir(job)).get("name")
    return _dumps_resp(out)


def review_mod():
    from . import review
    return review


@router.post("/logic/api/jobs/{job}/review/mark")
def review_mark(job: str, body: dict = Body(...)):
    """검토 항목에 사람 판단 — {keys: [...], verdict: OK|WRONG|HOLD|null, author, note}.  지우는 길은 없다 (이력)."""
    d = _dir(job)
    try:
        m = review_mod().set_marks(d, body.get("keys") or [], body.get("verdict"), body.get("author"), body.get("note") or "")
    except ValueError as ex:
        raise HTTPException(400, str(ex))
    cur = review_mod().load(d)
    return {"ok": True, "marks": review_mod().mark_stats(cur, m) if cur else None,
            "set": {k: m["marks"].get(k) for k in body.get("keys") or []}}


def _dumps_resp(x):
    return Response(_dumps(x), media_type="application/json")


@router.get("/logic/api/jobs/{job}/review.pdf")
def review_pdf(job: str, info: int = 0, author: str = ""):
    """L39 — 검토 결과를 입력 PDF 에 마크업한 파일 (맨 앞 요약 장 · 쪽마다 색 상자 · 번호 · 주석 · 책갈피)."""
    from . import review
    cur, _ = _review(job)
    d = _dir(job)
    try:
        out = review.pdf_dir(d, cur, include_info=bool(info), author=author[:60])
    except Exception as ex:
        raise HTTPException(500, f"PDF 를 만들지 못했습니다 — {ex}")
    if not out:
        raise HTTPException(409, "검토 결과가 아직 없습니다.")
    name = store.read_status(d).get("name") or "logic"
    fn = Path(name).stem + "_정합성검토.pdf"
    return FileResponse(out, media_type="application/pdf",
                        headers={"Content-Disposition": "attachment; filename*=UTF-8''" + quote(fn), "Cache-Control": "no-store"})


@router.get("/logic/api/jobs/{job}/review.xlsx")
def review_xlsx(job: str):
    from . import review
    cur, _ = _review(job)
    d = _dir(job)
    name = store.read_status(d).get("name") or "logic"
    data = review.workbook(review.with_marks(cur, review.load_marks(d)), name)
    fn = Path(name).stem + "_정합성검토.xlsx"
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
    return sim.simulate(s, clean, state, timers=_timers(body.get("timers")).get(page),
                        analog=_analog(body.get("analog")).get(page))


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
    # L68 — 묶음 기억을 넘긴다 (조합마다 827장을 처음부터 돌리던 것 · 같은 답 — L28) · 같은 출력은 다시 찾지 않는다
    cache = _bundle_cache(job, res)
    with cache.setdefault("_lock", threading.Lock()):
        return _memo(res, "scenario", lambda: sim.scenario(s, target, 1, sheets=_all_sheets(res), cache=cache), page, target)


@router.get("/logic/api/jobs/{job}/commands")
def commands(job: str):
    """L32 — 순차 동작 시뮬레이션: 묶음의 START · STOP · RUN · OPEN · CLOSE · TRIP 행을 장비마다."""
    res = _result(job)
    from . import sequence
    return {"items": _memo(res, "commands", lambda: sequence.commands(_all_sheets(res)))}


@router.get("/logic/api/jobs/{job}/outputs")
def outputs(job: str, q: str = "", limit: int = 60):
    """L70 — 출력 행 찾기 (동작 낱말이 없는 출력도 거슬러 올라가 보게)."""
    res = _result(job)
    from . import sequence
    return sequence.outputs(_all_sheets(res), q, max(1, min(int(limit or 60), 300)))


@router.post("/logic/api/jobs/{job}/sequence")
def sequence_plan(job: str, body: dict = Body(default={})):
    """L32 — 그 출력 행이 서려면 무엇이 필요한지 조건 나무 (묻는 순서 · 판정 0줄)."""
    res = _result(job)
    from . import sequence
    try:
        page, row = int(body.get("page")), int(body.get("row"))
    except (TypeError, ValueError):
        raise HTTPException(400, "page · row 가 필요합니다.")
    value = 0 if body.get("value") in (0, "0") else 1
    cache = _bundle_cache(job, res)
    with cache.setdefault("_lock", threading.Lock()):   # L50 — 권하는 갈래를 시뮬레이터로 시험한다 (묶음 기억 공유 · 한 번에 하나)
        return _memo(res, "sequence", lambda: sequence.plan(_all_sheets(res), page, row, value, cache=cache), page, row, value)


@router.post("/logic/api/jobs/{job}/needs")
def needs(job: str, body: dict = Body(default={})):
    """L49 — 게이트 · 매크로 · 선을 누르면: 그 출력이 켜지려면 앞쪽 어떤 신호가 켜져야 하는지 (출력마다 조건 나무 · 판정 0줄)."""
    res = _result(job)
    from . import sequence
    try:
        page = int(body.get("page"))
    except (TypeError, ValueError):
        raise HTTPException(400, "page 가 필요합니다.")
    target = str(body.get("target") or "")
    if not (target.startswith("block:") or target.startswith("net:")):
        raise HTTPException(400, "target 은 block:<id> · net:<id> 입니다.")
    value = 0 if body.get("value") in (0, "0") else 1
    cache = _bundle_cache(job, res)
    with cache.setdefault("_lock", threading.Lock()):
        return _memo(res, "needs", lambda: sequence.needs(_all_sheets(res), page, target, value, cache=cache), page, target, value)


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
    _BUNDLE.pop(job, None)
    return Response(status_code=204)


FORCE_KINDS = ("net", "row", "block", "hold")     # L32 hold — 입력을 다 읽지 못한 게이트의 출력에 사람이 답한 값


def _clean_forces(raw):
    if not isinstance(raw, dict):
        raise HTTPException(400, "forces 는 {쪽: {키: 0|1}} 이어야 합니다.")
    forces = {}
    for pg, fs in raw.items():
        if not isinstance(fs, dict) or not str(pg).isdigit():
            raise HTTPException(400, "forces 는 {쪽: {키: 0|1}} 이어야 합니다.")
        clean = {k: int(v) for k, v in fs.items()
                 if v in (0, 1) and isinstance(k, str) and k.split(":", 1)[0] in FORCE_KINDS}
        if clean:
            forces[int(pg)] = clean
    return forces


_LEARNING = {}


@router.get("/logic/api/jobs/{job}/behavior")
def behavior_get(job: str, start: int = 1, equip: str = ""):
    """L33 — 배운 동작 (명령마다 선다/안 선다 · 꼭 필요한 신호 · 막는 자리).  없거나 결과 · 사람 값이 바뀌었으면 뒤에서 다시 배운다.

    hotfix101 — 배우다 죽은 것은 사유와 함께 `failed` 로 말하고 저절로 다시 띄우지 않는다 (같은 자리에서 또 죽어 화면이
    '학습 중' 에 갇혔다).  start=2 는 사람이 누른 '다시 배우기'.  L42 — equip 이면 그 장비 하나만 돌려준다."""
    from . import behavior
    d = _dir(job)
    if not (d / "result.json").exists():
        raise HTTPException(409, "아직 분석이 끝나지 않았습니다.")
    cur = behavior.load(d)
    key = behavior.key_of(d)
    fresh = bool(cur) and cur.get("key") == key
    running = behavior.running(d)
    if not running and _learner_alive(job, d):
        running = {"done": 0, "total": None, "phase": "start"}
    err = behavior.load_error(d)
    failed = bool(err) and err.get("key") == key and not fresh and not running
    if start == 2 and not running:
        try:
            (d / behavior.ERROR).unlink()
        except OSError:
            pass
        failed, err = False, None
    if not fresh and not running and not failed and start:
        _start_learning(job, d)
        cur = behavior.load(d)                   # 그 자리에서 배운 경우 (PID_LOGIC_WARM=0)
        fresh = bool(cur) and cur.get("key") == behavior.key_of(d)
        err = behavior.load_error(d)
        failed = bool(err) and err.get("key") == behavior.key_of(d) and not fresh
        running = None if (fresh or failed) else (behavior.running(d) or {"done": 0, "total": None, "phase": "start",
                                                                           "started": time.time()})
    if equip and cur:                            # L42 — 그룹 시험 창은 펼친 장비 하나만 받는다 (19VA 전체는 수 MB)
        cur = {k: v for k, v in cur.items() if k not in ("items", "pairs")} | {
            "items": [x for x in cur.get("items") or [] if x.get("equip") == equip],
            "pairs": [x for x in cur.get("pairs") or [] if x.get("equip") == equip]}
    state = "done" if fresh else ("running" if running else ("failed" if failed else ("stale" if cur else "none")))
    return {"state": state, "progress": running, "result": cur,
            "error": (err or {}).get("error") if state == "failed" else None}


def _learner_alive(job, d):
    """서버가 띄운 학습 프로세스가 살아 있나.  죽었는데 사유를 못 남겼으면(가져오기 오류 · 메모리) 그 로그 끝을 사유로 남긴다."""
    from . import behavior
    p = _LEARNING.get(job)
    if p is None:
        return False
    rc = getattr(p, "poll", lambda: 0)()
    if rc is None:
        return True
    _LEARNING[job] = None
    if rc and not (behavior.load(d) or {}).get("key") == behavior.key_of(d) and not behavior.load_error(d):
        tail = ""
        try:
            tail = (d / "behavior.log").read_text(encoding="utf-8", errors="replace")[-1500:]
        except OSError:
            pass
        try:
            store._atomic(d / behavior.ERROR, json.dumps({"key": behavior.key_of(d), "at": time.time(), "trace": tail,
                                                           "error": f"학습 프로세스가 멈췄습니다 (종료 코드 {rc})"}, ensure_ascii=False))
        except Exception:
            pass
    return False


def _start_learning(job, d):
    import os
    from . import behavior
    if _learner_alive(job, d):
        return
    if os.environ.get("PID_LOGIC_WARM", "1") == "0":
        behavior.learn_dir(d)                    # 시험 — 그 자리에서
        _LEARNING[job] = None
        return
    if paths.frozen():
        th = threading.Thread(target=lambda: (behavior.wait_quiet(d), behavior.learn_dir(d)), daemon=True)
        th.start()
        _LEARNING[job] = type("T", (), {"poll": lambda self: None if th.is_alive() else 0})()
        return
    root = Path(__file__).resolve().parent.parent.parent
    try:
        log = open(d / "behavior.log", "wb")
        _LEARNING[job] = subprocess.Popen([sys.executable, "-m", "app.logic.run", "--behavior", str(d)], cwd=str(root),
                                          stdout=log, stderr=subprocess.STDOUT)
        log.close()
    except Exception as e:
        _LEARNING[job] = None
        try:
            store._atomic(d / behavior.ERROR, json.dumps({"key": behavior.key_of(d), "at": time.time(),
                                                           "error": f"학습 프로세스를 띄우지 못했습니다 — {e}"[:400]}, ensure_ascii=False))
        except Exception:
            pass


@router.post("/logic/api/jobs/{job}/sequence/try")
def sequence_try(job: str, body: dict = Body(default={})):
    """L32 — 갈래 고르기에서 갈래마다 '그 갈래의 조건을 다 주면 목표가 서는가' 를 같은 시뮬레이터로 미리 돌려 본다.
    판정은 시뮬레이터가 한다 (나무의 짐작이 아니라) — 화면은 선 갈래를 권한다."""
    res = _result(job)
    try:
        page = int(body.get("page"))
    except (TypeError, ValueError):
        raise HTTPException(400, "page 가 필요합니다.")
    net = str(body.get("net") or "")
    want = 0 if body.get("want") in (0, "0") else 1
    base = _clean_forces(body.get("forces") or {})
    opts = body.get("options") or []
    if not isinstance(opts, list) or len(opts) > 48:
        raise HTTPException(400, "options 는 갈래마다 forces 목록입니다 (48개까지).")
    timers = _timers(body.get("timers"))
    sheets = _all_sheets(res)
    cache = _bundle_cache(job, res)               # 장마다 같은 입력이면 지난 계산 — 갈래가 바꾸는 장만 다시 센다 (L28)
    out = []
    for o in opts:
        f = {p: dict(v) for p, v in base.items()}
        for p, v in _clean_forces(o).items():
            f.setdefault(p, {}).update(v)
        with cache.setdefault("_lock", __import__("threading").Lock()):
            r = sim.simulate_bundle(sheets, f, None, page, timers=timers, cache=cache, light=True)["focus"] or {"frames": []}
        vals = [fr["values"].get(net) for fr in r["frames"]]
        out.append({"reached": want in vals, "steady": bool(vals) and vals[-1] == want})
    return {"options": out}


@router.post("/logic/api/jobs/{job}/sequence/effect")
def sequence_effect(job: str, body: dict = Body(default={})):
    """L37 — 안내: 지금까지의 답(forces)에 이 신호(add)를 더하면 무엇이 1 이 되나 · 목표 출력이 서나 · 이 신호가 들어가는
    게이트의 입력이 몇 개 찼나.  같은 묶음 시뮬레이터로 앞뒤를 돌린 차이다 (판정 0줄)."""
    from . import sequence
    res = _result(job)
    try:
        page = int(body.get("page"))
    except (TypeError, ValueError):
        raise HTTPException(400, "page 가 필요합니다.")
    want = 0 if body.get("want") in (0, "0") else 1
    gate = body.get("gate") if isinstance(body.get("gate"), dict) else None
    if gate is not None:
        try:
            gate = {"block": str(gate.get("block") or ""), "page": int(gate.get("page"))}
        except (TypeError, ValueError):
            gate = None
    cache = _bundle_cache(job, res)
    with cache.setdefault("_lock", __import__("threading").Lock()):
        return sequence.effect(_all_sheets(res), page, str(body.get("net") or ""), want,
                               _clean_forces(body.get("forces") or {}), _clean_forces(body.get("add") or {}),
                               timers=_timers(body.get("timers")), gate=gate, cache=cache)


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
                 if v in (0, 1) and isinstance(k, str) and k.split(":", 1)[0] in FORCE_KINDS}
        if clean:
            forces[int(pg)] = clean
    state = body.get("state") if isinstance(body.get("state"), dict) else None
    focus = body.get("page")
    focus = int(focus) if isinstance(focus, int) or (isinstance(focus, str) and focus.isdigit()) else None
    timers = _timers(body.get("timers"))
    analog = _analog(body.get("analog"))
    cache = _bundle_cache(job, res)
    with cache.setdefault("_lock", __import__("threading").Lock()):
        hit = _bundle_reuse(cache, forces, state, timers, analog)
        if hit is None:
            out = sim.simulate_bundle(_all_sheets(res), forces, state, focus, timers=timers, analog=analog, cache=cache)
            hit = _bundle_keep(cache, forces, state, timers, analog, out)
    body_json, results, inner = hit
    f = results.get(focus) if focus is not None else None
    # L44 — 열린 매크로 새 창마다 부모 장에 펼쳐 같이 돈 값 (body 의 inner: ["쪽:상자", …])
    want = {}
    for k in (body.get("inner") or []) if isinstance(body.get("inner"), list) else []:
        pg, _, bid = str(k).partition(":")
        if pg.isdigit() and bid and bid in (inner.get(int(pg)) or {}):
            want[f"{pg}:{bid}"] = inner[int(pg)][bid]
    extra = b'"macro_inner":' + _dumps(want) + b"," if want else b""
    # 묶음 몸통은 한 번만 글로 바꿔 두고 화면이 보는 장의 결과만 그때 붙인다 (L31 — 846쪽 묶음 몸통 약 220KB)
    return Response(b'{"focus":' + _dumps(f) + b"," + extra + body_json[1:], media_type="application/json")


@router.post("/logic/api/jobs/{job}/sheet/{page}/press")
def sheet_press(job: str, page: int, body: dict = Body(default={})):
    """L34 — 누름단추를 누른다 {block, forces, state, timers, analog} → 그 신호가 어디까지 갔나 · 어디서 왜 멈췄나 ·
    누른 채로 그 동작이 나가려면 더 켤 입력 (sim.press).  판정은 화면과 같은 묶음 시뮬레이션이다."""
    res = _result(job)
    s = _sheet(job, page)
    bid = str(body.get("block") or "")
    b = s["blocks"].get(bid)
    if b is None:
        raise HTTPException(404, "그 블록이 없습니다.")
    if any(p_["block"] == bid and p_["dir"] == "in" for p_ in s["ports"]) and b.get("logic") != "source":
        raise HTTPException(400, "들어오는 선이 없는 신호원(누름단추 · HMI)만 누를 수 있습니다.")
    raw = body.get("forces") or {}
    forces = {}
    for pg, fs in (raw.items() if isinstance(raw, dict) else ()):
        if isinstance(fs, dict) and str(pg).isdigit():
            clean = {k: int(v) for k, v in fs.items()
                     if v in (0, 1) and isinstance(k, str) and k.split(":", 1)[0] in FORCE_KINDS}
            if clean:
                forces[int(pg)] = clean
    state = body.get("state") if isinstance(body.get("state"), dict) else None
    cache = _bundle_cache(job, res)
    with cache.setdefault("_lock", __import__("threading").Lock()):
        out = sim.press(_all_sheets(res), page, bid, forces, state, timers=_timers(body.get("timers")),
                        analog=_analog(body.get("analog")), cache=cache)
        cache.pop("_last_results", None)
    return out


BUNDLE_LAST = 4                   # L31 — 기억하는 묶음 계산 (입력 조합) 수


def _bundle_inputs_key(forces, state, timers, analog):
    return json.dumps([forces, state, timers, analog], sort_keys=True, separators=(",", ":"), default=str)


def _dumps(x) -> bytes:
    """JSONResponse 와 같은 꼴 (FastAPI 의 jsonable_encoder 를 거치지 않는다 — 큰 dict 에서 수십 ms)."""
    return json.dumps(x, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")


def _bundle_keep(cache, forces, state, timers, analog, out):
    """L31 — 시트를 옮길 때마다 묶음 전체를 다시 돌리지 않는다.  같은 입력(강제 · 상태 · 타이머 · 아날로그)이면 묶음의
    답은 같고 달라지는 것은 화면이 보는 장(focus) 하나뿐이다 — 그 장의 결과는 지난 계산이 장마다 이미 냈다."""
    results = cache.pop("_last_results", None) or {}
    body = {k: v for k, v in out.items() if k not in ("focus", "macro_inner")}
    body["default_t"] = sim.DEFAULT_T
    # 글로 바꿀 때 dict 열쇠(쪽 번호)가 글이 되는 것은 JSONResponse 와 같다.  장마다의 결과는 꺼낼 때 그때 글로 바꾼다 —
    # 그래서 기억 안의 객체를 아무도 고치지 않는다.
    hit = (_dumps(body), results, out.get("macro_inner") or {})
    _lru_put(cache.setdefault("_last", {}), _bundle_inputs_key(forces, state, timers, analog), hit, keep=BUNDLE_LAST)
    return hit


def _bundle_reuse(cache, forces, state, timers, analog):
    return (cache.get("_last") or {}).get(_bundle_inputs_key(forces, state, timers, analog))


_BUNDLE = {}                      # job → (결과 객체, 묶음 계산 기억) — L28 · 결과가 바뀌면(사람 값 · 다시 분석) 새로


def _bundle_cache(job, res):
    hit = _BUNDLE.get(job)
    if hit is None or hit[0] is not res:
        # 사람 값을 고쳐 결과가 새 사본이 되어도 장마다의 계산 기억은 넘겨준다 — 열쇠에 그 장의 내용 지문이 들어 있어
        # 바뀐 장만 다시 센다 (sim._sheet_fp)
        hit = (res, {"pages": hit[1].get("pages", {})} if hit else {})
        _lru_put(_BUNDLE, job, hit, keep=2)
    return hit[1]


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


def _analog(raw):
    """L26 · L27 — 사람이 준 아날로그 값 {쪽: {"block:<id>"|"row:<n>": mA}} (4~20 mA).  그 밖은 버린다."""
    if not isinstance(raw, dict):
        return {}
    out = {}
    for pg, d in raw.items():
        if not str(pg).isdigit() or not isinstance(d, dict):
            continue
        c = {}
        for k, v in d.items():
            if isinstance(k, str) and k.split(":", 1)[0] in ("block", "row") and analog.ma_ok(v) is not None:
                c[k] = analog.ma_ok(v)                      # L27 — 4~20 mA 밖의 값은 버린다
            elif isinstance(k, str) and k.startswith("net:") and isinstance(v, dict) and analog.num(v.get("eng")) is not None:
                c[k] = {"eng": analog.num(v["eng"])}         # L30 — 연산자 판에서 그 입력선에 공학값을 바로
        if c:
            out[int(pg)] = c
    return out


@router.get("/logic/api/jobs/{job}/memo")
def memo_list(job: str):
    """이 묶음의 메모 전부 (L8) — 화면이 장마다 거른다.
    L30 — 같은 프로젝트의 다른 분석(다른 Rev)에서 같은 시트 이름에 단 메모도 `others` 로 (P&ID hotfix63 — 장 메모는
    도면번호로 Rev 사이에 이어진다).  읽기만 — 고치는 것은 그 분석에서."""
    d = _dir(job)
    out = memo.load(d)
    st = store.read_status(d)
    proj = st.get("project")
    others = []
    if proj:
        for j in store.jobs():
            if j.get("id") == job or j.get("project") != proj:
                continue
            for it in memo.load(store.job_dir(j["id"]))["items"]:
                if it.get("sheet_no") and not it.get("hidden"):
                    others.append({**it, "from_job": j["id"], "from_name": j.get("name") or j["id"],
                                   "from_created": j.get("created") or ""})
    out["others"] = others
    return out


@router.post("/logic/api/jobs/{job}/memo")
def memo_add(job: str, body: dict = Body(...)):
    d = _dir(job)
    page = body.get("page")
    if not isinstance(page, int):
        raise HTTPException(400, "page 는 쪽 번호(정수)여야 합니다.")
    try:
        return memo.add(d, page, str(body.get("sheet_no") or ""), str(body.get("text") or ""),
                        str(body.get("author") or ""), body.get("at"), body.get("rect"), body.get("block"), body.get("id"))
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


@router.post("/logic/api/jobs/{job}/overrides/setpoint")
def overrides_setpoint(job: str, body: dict = Body(...)):
    """L26 — 감시 블록 설정값 {page, block, sp | null, author}.  기본은 도면이 블록 위에 인쇄한 값."""
    d = _dir(job)
    page, bid = body.get("page"), str(body.get("block") or "")
    if not isinstance(page, int) or not bid:
        raise HTTPException(400, "page(정수) 와 block 이 필요합니다.")
    b = _sheet(job, page)["blocks"].get(bid)
    if b is None:
        raise HTTPException(404, "그 블록이 없습니다.")
    if not analog.monitor_kind(b):
        raise HTTPException(400, "설정값은 감시 블록(HHH · HH · H · /L · /LL …)에만 적습니다.")
    sp = body.get("sp")
    if sp is not None and analog.num(sp) is None:
        raise HTTPException(400, "설정값은 수입니다.")
    return _ov_call(overrides.set_setpoint, d, page, bid, sp, str(body.get("author") or ""))


@router.post("/logic/api/jobs/{job}/overrides/range")
def overrides_range(job: str, body: dict = Body(...)):
    """L27 — 아날로그 입력 범위 {page, key: "row:<n>"|"block:<id>", lo, hi, unit, author}.  lo null 이면 도면 범위로."""
    d = _dir(job)
    page, key = body.get("page"), str(body.get("key") or "")
    if not isinstance(page, int):
        raise HTTPException(400, "page(정수) 가 필요합니다.")
    s = _sheet(job, page)
    kind, _, x = key.partition(":")
    if not ((kind == "row" and x.isdigit() and any(r["side"] == "L" and r["n"] == int(x) for r in s["rows"]))
            or (kind == "block" and x in s["blocks"])):
        raise HTTPException(400, "key 는 이 시트의 입력 행(row:<n>) 이나 블록(block:<id>) 입니다.")
    return _ov_call(overrides.set_range, d, page, key, body.get("lo"), body.get("hi"), body.get("unit"),
                    str(body.get("author") or ""))


@router.post("/logic/api/jobs/{job}/sheet/{page}/aop")
def sheet_aop(job: str, page: int, body: dict = Body(default={})):
    """L30 — 아날로그 연산자 하나의 지금 계산 (입력 · 계수 · 출력 · 이유).  시뮬레이션을 돌리지 않고 그 장만 센다
    (동작 시뮬레이션 중이면 화면이 시뮬레이션 결과를 쓴다 — 다른 장에서 이어진 값까지)."""
    s = _sheet(job, page)
    bid = str(body.get("block") or "")
    if bid not in s["blocks"]:
        raise HTTPException(404, "그 블록이 없습니다.")
    idx = sim._index(s)[:4]
    sd = body.get("detail")
    if isinstance(sd, dict) and sd.get("op"):
        d, key = sd, sd.get("key")                       # L71 — 동작 시뮬레이션 결과 (다른 장에서 이어진 값까지) 그대로 · 과정만 더한다
    else:
        given = _analog({str(page): body.get("analog") or {}}).get(page, {})
        det = {}
        nv, bv, keys = analog.nets(s, given, idx, None, det)
        d = det.get(bid)
        if d is None:
            return {"op": None, "block": bid}
        key = keys.get(f"block:{bid}")
    return {**d, "block": bid, "key": key, **_aop_trace(s, bid, d, idx, body.get("dig") or {})}


def _aop_trace(s, bid, d, idx, dig):
    """L71 — 계산 과정(값을 넣은 식)과 입력마다 어디서 오나 (입력 행 · 계기까지 거슬러)."""
    b = s["blocks"][bid]
    tp = analog._topo(s, idx)
    cv = dig.get(str(d.get("cond"))) if d.get("cond") is not None else None
    tr = aop_trace.trace(d.get("op"), d.get("params") or aops.params(b), d.get("inputs") or [], d.get("out"), d.get("dig"),
                         d.get("why") or "", b.get("label") or b.get("read") or "", cond_value=cv)
    byname = {str(n): n for n in s["nets"]}
    src = {str(i["net"]): aop_trace.sources(s, byname.get(str(i["net"]), i["net"]), bid, idx, tp["ops"], tp["io"]) for i in d.get("inputs") or []}
    return {"trace": tr, "sources": src}


@router.post("/logic/api/jobs/{job}/overrides/aparam")
def overrides_aparam(job: str, body: dict = Body(...)):
    """L30 — 아날로그 연산자 값 {page, block, params | null, author}.  params 는 overrides.clean_aparams 를 보라."""
    d = _dir(job)
    page, bid = body.get("page"), str(body.get("block") or "")
    if not isinstance(page, int) or not bid:
        raise HTTPException(400, "page(정수) 와 block 이 필요합니다.")
    b = _sheet(job, page)["blocks"].get(bid)
    if b is None:
        raise HTTPException(404, "그 블록이 없습니다.")
    params = body.get("params")
    if params is not None and not (aops.op_of(b) or (params or {}).get("op") or b.get("func") in ("UNKNOWN", "ANALOG")):
        raise HTTPException(400, "아날로그 연산자에만 값을 넣습니다.")
    return _ov_call(overrides.set_aparam, d, page, bid, params, str(body.get("author") or ""))


@router.get("/logic/api/aops")
def aops_vocab():
    """L30 — 아날로그 연산자 어휘 (이름 · 식 · 화면이 물을 값)."""
    v = aops.vocab()
    return {"ops": {k: {"ko": e.get("ko"), "eq": e.get("eq")} for k, e in (v.get("ops") or {}).items()},
            "digital_ops": {k: {"ko": e.get("ko"), "eq": e.get("eq")} for k, e in (v.get("digital_ops") or {}).items()},
            "needs": aops.NEEDS}


@router.get("/logic/signal")
def logic_signal_page():
    """L72 — 신호 처리(아날로그 연산자) 시뮬레이션 페이지."""
    return page_stamp.page("logic_signal.html")


@router.get("/logic/api/aopsim")
def aopsim_meta():
    """L72 — 페이지가 쓰는 연산 목록 (범례 어휘 + 시간 블록 Lead/Lag) · 시간 그래프 블록의 설정값과 기본값."""
    v = aops.vocab()
    ops = {k: {"ko": e.get("ko"), "eq": e.get("eq")} for g in ("ops", "digital_ops") for k, e in (v.get(g) or {}).items()}
    ops.update(aop_trace.EXTRA_OPS)
    return {"ops": ops, "needs": aops.NEEDS, "time_ops": aop_trace.TIME_OPS}


@router.post("/logic/api/aopsim")
def aopsim_run(body: dict = Body(...)):
    """L72 — 사람이 넣은 입력 · 설정값으로 연산자 하나를 센다 (도면 판과 같은 aops.compute) → 출력 · 계산 과정."""
    op = str(body.get("op") or "")
    if op not in aop_trace.EXTRA_OPS and not aops.info(op):
        raise HTTPException(400, "모르는 연산입니다.")
    ins = body.get("inputs") or []
    if not isinstance(ins, list) or len(ins) > 16:
        raise HTTPException(400, "입력은 16개까지입니다.")
    return aop_trace.run_static(op, ins, body.get("params") or {}, str(body.get("label") or "")[:200], body.get("cond"))


@router.post("/logic/api/aopsim/timeline")
def aopsim_timeline(body: dict = Body(...)):
    """L72 — 시간에 따라 변하는 블록(Lag · Lead/Lag · 변화율 제한 · 적분 · 미분)의 응답 → {t, x, y}."""
    try:
        return aop_trace.timeline(str(body.get("op") or ""), body.get("params") or {}, body.get("input") or {}, body.get("T") or 60)
    except (ValueError, TypeError) as e:
        raise HTTPException(400, str(e))


@router.get("/logic/api/functions")
def functions_get():
    """기능 책 — 기능마다 범례가 정한 동작 한 줄 (화면 '동작 (범례)' 줄이 읽는다)."""
    from app.logic import functions
    return functions.book()


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
    tc = overrides.load(_dir(job)).get("teach")
    q = dict(_memo(res, "teach", lambda: teach.questions(res, tc), json.dumps(tc, sort_keys=True, default=str))
             if done else teach.questions(res, tc))
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


from . import draw_api as _draw_api          # L54 — LOGIC 작도 (/logic/draw · /logic/api/drawings/*)
router.include_router(_draw_api.router)
