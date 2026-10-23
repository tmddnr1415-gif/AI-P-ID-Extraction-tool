"""사람이 다듬은 HMI 장면의 저장 자리 — `{data}/hmi/<분석>/p<장>.json` (jsonstore · 원자적 · 앞 판 .bak)."""
from __future__ import annotations

import re
import time
from pathlib import Path

from app import jsonstore, paths

JOB_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def root() -> Path:
    p = paths.data_dir() / "hmi"
    p.mkdir(parents=True, exist_ok=True)
    return p


def path(job: str, page: int) -> Path:
    if not JOB_RE.match(job or ""):
        raise KeyError(job)
    return root() / job / f"p{int(page)}.json"


def load(job: str, page: int):
    p = path(job, page)
    return jsonstore.read(p, None, what="HMI 장면", expect=dict) if p.exists() else None


def save(job: str, page: int, scene: dict, author: str) -> dict:
    if not (author or "").strip():
        raise ValueError("author")
    scene = dict(scene)
    scene["generated"] = False
    scene["saved_by"] = author.strip()
    scene["saved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    p = path(job, page)
    p.parent.mkdir(parents=True, exist_ok=True)
    jsonstore.write(p, scene)
    return scene


def delete(job: str, page: int) -> bool:
    p = path(job, page)
    if p.exists():
        p.unlink()
        return True
    return False
