"""LOGIC 프로젝트 — `{data}/logic/projects.json` (P&ID 프로젝트 장부와 따로).

Logic 검토는 **실행 프로젝트만** 있다 (사용자 확정 — 입찰 Logic 은 없다).  그래서 종류 칸은 언제나 "epc" 이고
고르는 자리가 없다.  프로젝트는 분석(묶음)을 모으는 이름일 뿐이고 판정에 쓰이지 않는다.

자료 다섯 가지 (MATERIALS) — Logic Diagram 은 필수, 나머지는 선택이다.  지금은 Logic 만 분석하고 나머지는
분석 폴더에 그대로 보관한다 (다른 자료와의 교차 분석은 추후 개발).
"""
from __future__ import annotations

import re
import time

from app import jsonstore

from . import store

MATERIALS = [
    ("logic", "Logic Diagram", True, (".pdf",)),
    ("loop", "Loop Diagram", False, (".pdf",)),
    ("sysdesc", "System Description", False, (".pdf", ".doc", ".docx")),
    ("iolist", "IO List", False, (".xlsx", ".xls", ".xlsm", ".csv", ".pdf")),
    ("logictable", "Logic Table", False, (".xlsx", ".xls", ".xlsm", ".csv", ".pdf")),
]
KINDS = {k for k, *_ in MATERIALS}
_BAD = re.compile(r'[\x00-\x1f/\\:*?"<>|]')


class NameError_(ValueError):
    pass


def _path():
    return store.root() / "projects.json"


def load() -> list:
    d = jsonstore.read(_path(), {"projects": []}, what="LOGIC 프로젝트 장부", expect=dict)
    return list(d.get("projects", []))


def check_name(name: str) -> str:
    n = " ".join(str(name or "").split())
    if not n:
        raise NameError_("프로젝트명을 적으세요.")
    if len(n.encode("utf-8")) > 150:
        raise NameError_("프로젝트명이 너무 깁니다 (150바이트 안).")
    if _BAD.search(n) or n in (".", "..") or n.endswith("."):
        raise NameError_("프로젝트명에 쓸 수 없는 글자가 있습니다 ( / \\ : * ? \" < > | 와 끝의 점).")
    return n


@jsonstore.serialized
def create(name: str, author: str = "") -> dict:
    n = check_name(name)
    ps = load()
    if any(p["name"].casefold() == n.casefold() for p in ps):
        raise FileExistsError(n)
    p = {"name": n, "mode": "epc", "author": (author or "").strip()[:60], "created": time.time()}
    ps.append(p)
    jsonstore.write(_path(), {"projects": ps})
    return p


def exists(name: str) -> bool:
    return any(p["name"] == name for p in load())


@jsonstore.serialized
def remove(name: str) -> dict | None:
    """장부에서 그 프로젝트를 뺀다 (분석 폴더는 api 가 지운다) — 뺀 항목, 없으면 None."""
    ps = load()
    hit = next((p for p in ps if p["name"] == name), None)
    if hit is None:
        return None
    jsonstore.write(_path(), {"projects": [p for p in ps if p["name"] != name]})
    return hit
