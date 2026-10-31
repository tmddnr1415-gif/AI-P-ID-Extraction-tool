"""L64c — LOGIC 작도의 계기 리스트 (Instrument List Excel).

프로젝트마다 하나.  TAG(KKS) → DESCRIPTION 을 읽어 두고, 작도 화면의 TAG NO. 칸 자동완성과 설명 자동 채우기에 쓴다.
다시 올리면 앞 판과 맞대어 ① 같은 TAG 의 설명이 바뀐 것은 그 TAG 를 쓰는 행의 설명을 바꾸고 표시를 남긴다
(사람이 따로 고친 설명은 건드리지 않는다) ② 없어진 TAG 는 화면이 "리스트에서 식별되지 않음" 으로 경고한다 (그림은 그대로).

판정 코드가 아니다 — 그림의 글자만 바꾼다.  저장은 `{data}/logic/instruments/<프로젝트 열쇠>.json`.
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
import time

from .. import jsonstore
from . import store

# 머리글 낱말 (영어 계장 어휘 — 프로젝트 값이 아니다)
TAG_HEAD = re.compile(r"^(KKS|TAG|INSTRUMENT\s*TAG|INST\.?\s*TAG|LOOP\s*TAG)\b|\bTAG\s*(NO|NUMBER|#)|\bKKS\s*(NO|CODE|TAG|NUMBER)", re.I)
DESC_HEAD = re.compile(r"\b(DESCRIPTION|SERVICE|DESC\.?|NAME)\b", re.I)
TYPE_HEAD = re.compile(r"^(INSTRUMENT\s*TYPE|INST\.?\s*TYPE|TYPE|DEVICE\s*TYPE)$", re.I)
HEAD_ROWS = 40
MAX_TAGS = 50000


def norm(tag) -> str:
    """TAG 맞대기 열쇠 — 대문자 · 공백 없음 (10 MAA 10 CP001 = 10MAA10CP001)."""
    return re.sub(r"\s+", "", str(tag or "")).upper()


def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return re.sub(r"\s+", " ", str(v)).strip()


def _rows_of(data: bytes, filename: str):
    """(시트 이름, 행 목록) — xlsx/xlsm 은 openpyxl, csv 는 그대로."""
    name = (filename or "").lower()
    if name.endswith(".csv") or name.endswith(".txt"):
        text = data.decode("utf-8-sig", errors="replace")
        yield "csv", [list(r) for r in csv.reader(io.StringIO(text))]
        return
    import openpyxl
    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as e:
        raise ValueError(f"엑셀 파일을 열지 못했습니다 ({type(e).__name__}) — .xlsx 로 저장해 다시 올려 주세요.")
    try:
        for ws in wb.worksheets:
            yield ws.title, [list(r) for r in ws.iter_rows(values_only=True)]
    finally:
        wb.close()


def parse(data: bytes, filename: str = "") -> dict:
    """→ {"tags": {열쇠: {"tag", "desc", "type", "sheet", "row"}}, "found": [(시트, 머리글 행, TAG 열, 설명 열)]}.
    시트마다 처음 40행 안에서 TAG 열과 설명 열이 같은 줄에 선 머리글을 찾는다.  못 찾으면 사유와 함께 멈춘다."""
    tags, found = {}, []
    for sheet, rows in _rows_of(data, filename):
        head = None
        for i, r in enumerate(rows[:HEAD_ROWS]):
            cells = [_cell(c) for c in r]
            ti = next((j for j, c in enumerate(cells) if c and TAG_HEAD.search(c)), None)
            di = next((j for j, c in enumerate(cells) if c and j != ti and DESC_HEAD.search(c) and not TAG_HEAD.search(c)), None)
            if ti is not None and di is not None:
                yi = next((j for j, c in enumerate(cells) if c and TYPE_HEAD.match(c)), None)
                head = (i, ti, di, yi)
                break
        if head is None:
            continue
        i0, ti, di, yi = head
        found.append({"sheet": sheet, "row": i0 + 1, "tag_col": ti + 1, "desc_col": di + 1})
        for k, r in enumerate(rows[i0 + 1:], start=i0 + 2):
            tag = _cell(r[ti]) if ti < len(r) else ""
            if not tag or TAG_HEAD.search(tag):
                continue
            key = norm(tag)
            if len(key) < 2 or key in tags:
                continue
            tags[key] = {"tag": tag[:60], "desc": (_cell(r[di]) if di < len(r) else "")[:160],
                         "type": (_cell(r[yi]) if yi is not None and yi < len(r) else "")[:40], "sheet": sheet, "row": k}
            if len(tags) >= MAX_TAGS:
                break
    if not found:
        raise ValueError("TAG(KKS) 열과 DESCRIPTION 열이 같은 줄에 있는 머리글을 찾지 못했습니다 (처음 40행).")
    return {"tags": tags, "found": found}


def _key(project: str) -> str:
    return hashlib.sha1((project or "").strip().encode("utf-8")).hexdigest()[:16]


def _path(project: str):
    d = store.root() / "instruments"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{_key(project)}.json"


def load(project: str) -> dict | None:
    p = _path(project)
    if not p.exists():
        return None
    return jsonstore.read(p, what="계기 리스트", expect=dict)


def public(project: str) -> dict:
    """화면이 받는 것 — 작게: {TAG 열쇠: [TAG, 설명, 종류]}."""
    cur = load(project)
    if not cur:
        return {"project": project, "n": 0, "tags": {}}
    return {"project": project, "n": len(cur.get("tags") or {}), "file": cur.get("file", ""), "at": cur.get("at"),
            "author": cur.get("author", ""), "version": len(cur.get("versions") or []),
            "tags": {k: [v["tag"], v.get("desc", ""), v.get("type", "")] for k, v in (cur.get("tags") or {}).items()},
            "changes": cur.get("changes") or {}}


def diff(old: dict, new: dict) -> dict:
    changed = [{"tag": new[k]["tag"], "key": k, "old": old[k].get("desc", ""), "new": new[k].get("desc", "")}
               for k in new if k in old and (old[k].get("desc") or "") != (new[k].get("desc") or "")]
    removed = [{"tag": old[k]["tag"], "key": k, "desc": old[k].get("desc", "")} for k in old if k not in new]
    added = [k for k in new if k not in old]
    return {"changed": changed, "removed": removed, "added": len(added)}


def apply_to_drawings(project: str, changed: list, author: str) -> dict:
    """설명이 바뀐 TAG 를 쓰는 행 — 지금 설명이 앞 판 리스트의 설명(또는 빈칸)이면 새 설명으로 바꾸고 `inst` 표시를 남긴다.
    사람이 따로 고친 설명(앞 판과도 새 판과도 다름)은 그대로 두고 센다."""
    from . import draw
    if not changed:
        return {"rows": 0, "drawings": 0, "kept": 0}
    ch = {c["key"]: c for c in changed}
    rows = drawings = kept = 0
    now = time.time()
    for it in draw.listing():
        if (it.get("project") or "") != (project or ""):
            continue
        try:
            doc = draw.load(it["id"])
        except Exception:
            continue
        hit = False
        for side in ("left", "right"):
            for n, row in (doc.get(side) or {}).items():
                c = ch.get(norm(row.get("kks")))
                if not c:
                    continue
                cur = row.get("desc") or ""
                if cur in ("", c["old"]):
                    row["desc"] = c["new"][:60]
                    row["inst"] = {"old": c["old"][:60], "at": now}
                    rows += 1
                    hit = True
                elif cur != c["new"]:
                    kept += 1
        if hit:
            draw.save(it["id"], doc, author)
            drawings += 1
    return {"rows": rows, "drawings": drawings, "kept": kept}


@jsonstore.serialized
def upload(project: str, data: bytes, filename: str, author: str) -> dict:
    author = (author or "").strip()[:60]
    if not author:
        raise ValueError("작성자가 필요합니다.")
    got = parse(data, filename)
    cur = load(project) or {"project": project, "versions": [], "tags": {}}
    d = diff(cur.get("tags") or {}, got["tags"]) if cur.get("tags") else {"changed": [], "removed": [], "added": len(got["tags"])}
    upd = apply_to_drawings(project, d["changed"], author)
    now = time.time()
    rec = {"file": (filename or "")[:120], "at": now, "author": author, "n": len(got["tags"]),
           "changed": len(d["changed"]), "removed": len(d["removed"]), "added": d["added"]}
    out = {"project": project, "file": rec["file"], "at": now, "author": author, "tags": got["tags"], "found": got["found"],
           "versions": (cur.get("versions") or [])[-49:] + [rec],
           "changes": {"changed": d["changed"][:500], "removed": d["removed"][:500], "added": d["added"], "at": now,
                       "rows": upd["rows"], "drawings": upd["drawings"], "kept": upd["kept"]}}
    jsonstore.write(_path(project), out)
    return {"n": rec["n"], "found": got["found"], **out["changes"]}
