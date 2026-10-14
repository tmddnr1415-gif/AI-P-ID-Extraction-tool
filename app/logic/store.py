"""LOGIC 묶음의 저장 자리 — `{data}/logic/<job>/` (P&ID 의 uploads · DB 와 따로).

  source.pdf     올린 PDF (그대로)
  status.json    상태 · 진행 (분석 프로세스가 쓴다)
  result.json    analyse.py 결과
  pages/p<n>_z<zoom>.png   장 그림 캐시

DB 를 쓰지 않는다 — 기존 표에 손대지 않고(지시문 §3), 이 회차에 필요한 것은 파일로 충분하다.
"""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from pathlib import Path

from app import paths

JOB_RE = re.compile(r"^[0-9a-f]{12}$")
ZOOM = 2.5                      # 장 그림 배율 (A3 1191pt → 약 2980px) — api · run 이 같은 값을 쓴다


def root() -> Path:
    p = paths.data_dir() / "logic"
    p.mkdir(parents=True, exist_ok=True)
    return p


def job_dir(job: str) -> Path:
    if not JOB_RE.match(job or ""):
        raise KeyError(job)
    d = root() / job
    if not d.is_dir():
        raise KeyError(job)
    return d


def new_job(name: str) -> tuple[str, Path]:
    job = uuid.uuid4().hex[:12]
    d = root() / job
    d.mkdir(parents=True)
    write_status(d, {"state": "queued", "name": name, "created": time.time(), "stage": "", "done": 0, "total": 0})
    return job, d


REPLACE_TRIES = 12             # Windows: 다른 프로세스(화면이 진행을 읽는 서버 · 백신)가 그 파일을 잠깐 열고 있으면
REPLACE_WAIT = 0.05            # os.replace 가 WinError 5 로 거절된다 — 잠깐 기다렸다 다시 (P&ID jsonstore 와 같은 길)


def _replace(tmp: Path, path: Path):
    wait = REPLACE_WAIT
    for i in range(REPLACE_TRIES):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if i == REPLACE_TRIES - 1:
                raise
            time.sleep(wait)
            wait = min(wait * 2, 0.5)


def _atomic(path: Path, data: str):
    tmp = path.with_suffix(path.suffix + f".tmp{os.getpid()}")
    tmp.write_text(data, encoding="utf-8")
    try:
        _replace(tmp, path)
    except PermissionError:
        tmp.unlink(missing_ok=True)
        raise


def write_status(d: Path, st: dict):
    """진행 상태 — 표시용이라 못 써도 분석을 멈추지 않는다 (L20 · 현장 WinError 5)."""
    text = json.dumps(st, ensure_ascii=False)
    try:
        _atomic(d / "status.json", text)
        return
    except PermissionError:
        pass
    try:                        # 바꿔 넣기가 끝내 막히면 그 자리에 바로 쓴다 (읽는 쪽은 깨진 글을 견딘다)
        (d / "status.json").write_text(text, encoding="utf-8")
    except OSError:
        pass                    # 이번 진행 한 줄은 건너뛴다 — 다음 진행이 다시 쓴다


_LAST_STATUS: dict = {}


def read_status(d: Path) -> dict:
    """쓰는 중이라 못 읽거나(잠김 · 반쯤 쓴 글) 깨졌으면 직전에 읽은 상태를 돌려준다."""
    key = str(d)
    try:
        st = json.loads((d / "status.json").read_text(encoding="utf-8"))
    except Exception:
        return dict(_LAST_STATUS.get(key) or {"state": "unknown"})
    if len(_LAST_STATUS) > 256:
        _LAST_STATUS.clear()
    _LAST_STATUS[key] = st
    return st


def write_result(d: Path, res: dict):
    _atomic(d / "result.json", json.dumps(res, ensure_ascii=False))


_RES = {}


def read_result(d: Path) -> dict:
    p = d / "result.json"
    st = p.stat().st_mtime
    hit = _RES.get(str(p))
    if hit and hit[0] == st:
        return hit[1]
    res = json.loads(p.read_text(encoding="utf-8"))
    if len(_RES) > 4:
        _RES.clear()
    _RES[str(p)] = (st, res)
    return res


def jobs() -> list:
    out = []
    for d in sorted(root().iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not d.is_dir() or not JOB_RE.match(d.name):
            continue
        st = read_status(d)
        out.append({"id": d.name, **{k: st.get(k) for k in ("state", "name", "created", "stage", "done", "total",
                                                             "error", "sheets", "seconds", "project", "materials",
                                                             "pages", "author")}})
    return out


def page_png(d: Path, page: int) -> Path:
    """장 그림 캐시 파일 — 없으면 그린다 (api 가 요청 때, run 이 분석 끝에 미리).  임시 파일 → replace."""
    import pymupdf
    cache = d / "pages" / f"p{page}_z{ZOOM}.png"
    if cache.exists():
        return cache
    cache.parent.mkdir(exist_ok=True)
    doc = pymupdf.open(d / "source.pdf")
    if not (1 <= page <= len(doc)):
        raise IndexError(page)
    pix = doc[page - 1].get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM), alpha=False)
    tmp = cache.with_suffix(f".tmp{os.getpid()}.png")
    pix.save(tmp)
    try:
        _replace(tmp, cache)
    except PermissionError:
        tmp.unlink(missing_ok=True)
        if not cache.exists():
            raise
    return cache
