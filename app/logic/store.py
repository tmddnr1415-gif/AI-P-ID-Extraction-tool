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


def _atomic(path: Path, data: str):
    tmp = path.with_suffix(path.suffix + f".tmp{os.getpid()}")
    tmp.write_text(data, encoding="utf-8")
    os.replace(tmp, path)


def write_status(d: Path, st: dict):
    _atomic(d / "status.json", json.dumps(st, ensure_ascii=False))


def read_status(d: Path) -> dict:
    try:
        return json.loads((d / "status.json").read_text(encoding="utf-8"))
    except Exception:
        return {"state": "unknown"}


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
                                                             "error", "sheets", "seconds")}})
    return out
