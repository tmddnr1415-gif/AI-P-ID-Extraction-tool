"""hotfix74 — API 퍼징: 모든 경로에 잘못된 입력을 넣어 **5xx 가 나오는 자리**를 찾는다.

실 데이터는 건드리지 않는다 — 원본 데이터 폴더를 임시 폴더로 복사하고 `PID_DATA_DIR` 로 가리킨 뒤
같은 프로세스 안의 TestClient 로 부른다 (`raise_server_exceptions=False` — 500 을 예외가 아니라 응답으로 센다).

    python3 spike/api_fuzz.py /tmp/qfe72 out/hotfix74/fuzz

경로 인자는 넷으로 바꿔 넣는다: 실제 값 · 없는 값 · 경로 조작(`../x`) · 이상한 글자.
본문은 열 가지: {} · [] · "x" · null · 숫자 · 실제 열쇠에 틀린 형 · 거대한 글 · 깊은 중첩 · 음수 · 빈 글.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/qfe72")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out/hotfix74/fuzz")
OUT.mkdir(parents=True, exist_ok=True)
tmp = Path(tempfile.mkdtemp(prefix="fuzz_"))
shutil.copytree(SRC, tmp / "data")
os.environ["PID_DATA_DIR"] = str(tmp / "data")
os.environ["PID_PAGE_WARM"] = "0"
os.environ["PID_RENDER_POOL"] = "0"
os.environ["PID_ANALYSIS_INPROCESS"] = "1"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402
from app import main, db  # noqa: E402

client = TestClient(main.app, raise_server_exceptions=False)
jobs = [dict(r) for r in main.CON.execute("select id, project from job where status='done'")]
JOB = jobs[-1]["id"] if jobs else "nojob"
PROJ = jobs[-1]["project"] if jobs else "QFE"
rows = json.loads(client.get(f"/jobs/{JOB}/rows").content or b"[]") if jobs else []
ROWKEY = (rows[0]["key"] if rows else "nokey")
rev = client.get(f"/jobs/{JOB}/revision").json() if jobs else {}
REVID = (rev or {}).get("revision_id") or (rev or {}).get("id") or "rev"

VALUES = {
    "job_id": [JOB, "nonexistent1", "..%2F..%2Fetc", "%E2%98%83", "a" * 300],
    "key": [ROWKEY, "nokey", "..%2Fx", "%00", "k" * 300],
    "page_no": ["6", "0", "-1", "99999", "abc", "1.5"],
    "page": ["6", "0", "-1", "99999", "abc"],
    "name": [PROJ, "없는프로젝트", "..%2F..%2Fx", "%2E%2E", "n" * 300, "%20"],
    "project": [PROJ, "없는", "..%2Fx"],
    "rev_id": [str(REVID), "x", "-1"],
    "revision_id": [str(REVID), "x", "-1"],
    "report_id": ["1", "999999", "x", "-1"],
    "symbol_id": ["1", "x", "999999"],
    "unit": ["10", "x", "..%2F"],
    "voc_id": ["VOC-x", "..%2F..%2Fx", "z" * 300],
    "asset": ["x.png", "..%2F..%2Fapp.db"],
    "path": ["index.html", "..%2F..%2Fapp.db", "..%2F..%2F..%2Fetc%2Fpasswd"],
}
DEFAULT_VALUES = ["x", "..%2Fx", "0"]

BIG = "가" * 200_000
DEEP: dict = {}
d = DEEP
for _ in range(200):
    d["a"] = {}
    d = d["a"]

BODIES = [
    ("empty-obj", {}), ("list", []), ("string", "x"), ("null", None), ("number", 7),
    ("neg", {"page_no": -1, "qty": -5, "value": -1, "rect": [-1, -1, -2, -2]}),
    ("wrong-types", {"field": 7, "value": {"a": 1}, "author": ["x"], "rect": "abc", "keys": "abc",
                     "page_no": "x", "items": "x", "cells": "x", "cell": 5, "mode": 3, "qty": "x",
                     "multiplier": "x", "drawing_no": 3, "text": 9, "klass": 1, "reason": [],
                     "enabled": "x", "note": {}, "kind": [], "state": 7}),
    ("big", {"author": BIG, "note": BIG, "text": BIG, "value": BIG, "reason": BIG, "detail": BIG}),
    ("deep", DEEP),
    ("nan", {"rect": [float("nan")] * 4, "qty": float("inf")}),
    ("bad-rect", {"rect": [1, 2], "page_no": 6, "author": "퍼징"}),
    ("empty-strings", {"author": "", "field": "", "value": "", "key": "", "keys": [], "items": []}),
    ("bad-names", {"name": "n" * 300, "project": "../x", "confirm": "n" * 300, "author": "퍼징",
                   "kind": "x", "text": "x"}),
    ("ctrl-names", {"name": "a\tb\x00", "project": " ", "confirm": "", "author": "퍼징"}),
    ("keys-junk", {"keys": ["nokey", None, 7, {"a": 1}], "items": [{"key": None, "qty": "x"}, 5, None],
                   "value": "7", "field": "qty", "author": "퍼징"}),
]


def concrete(path: str):
    params = re.findall(r"{(\w+)(?::\w+)?}", path)
    if not params:
        yield path
        return
    # 첫 값은 전부 '실제' 로, 나머지는 한 자리씩만 바꾼다 (조합 폭발 막기)
    base = {p: (VALUES.get(p) or DEFAULT_VALUES)[0] for p in params}
    seen = set()
    for p in params:
        for v in (VALUES.get(p) or DEFAULT_VALUES):
            vals = dict(base, **{p: v})
            s = path
            for k, val in vals.items():
                s = re.sub(r"{%s(?::\w+)?}" % k, val, s)
            if s not in seen:
                seen.add(s)
                yield s


SKIP = {"/jobs/{job_id}/events", "/running",          # 흐름(SSE) — 따로 본다
        "/jobs/{job_id}/reanalyse"}                    # 분석을 실제로 띄운다 — 따로 본다
DESTRUCTIVE_LAST = ("DELETE",)

results = []
t0 = time.time()
routes = [r for r in main.app.routes if hasattr(r, "methods")]
order = sorted(routes, key=lambda r: ("DELETE" in r.methods, r.path))
for r in order:
    if r.path in SKIP or r.path.startswith("/static") or r.path in ("/docs", "/redoc", "/openapi.json"):
        continue
    for m in sorted(r.methods - {"HEAD", "OPTIONS"}):
        for url in concrete(r.path):
            bodies = BODIES if m in ("POST", "PATCH", "PUT", "DELETE") else [("none", None), ("junk-query", None)]
            for bname, body in bodies:
                try:
                    if m == "GET":
                        q = ("?zoom=abc&page=-1&page_no=x&tab=%00&keys=..,%2F&limit=-5&scope=zz&kind=%E2%98%83"
                             "&slim=maybe&q=" + "x" * 3000) if bname == "junk-query" else ""
                        resp = client.get(url + q)
                    else:
                        kw = {}
                        if bname == "string":
                            kw = {"content": b"not json", "headers": {"content-type": "application/json"}}
                        elif body is not None or bname == "null":
                            kw = {"content": json.dumps(body, allow_nan=True).encode(),
                                  "headers": {"content-type": "application/json"}}
                        resp = client.request(m, url, **kw)
                    code = resp.status_code
                    text = resp.text[:300]
                except Exception as exc:                       # noqa: BLE001
                    code, text = -1, "".join(traceback.format_exception_only(type(exc), exc))[:300]
                if code >= 500 or code < 0:
                    results.append({"method": m, "route": r.path, "url": url[:160], "body": bname,
                                    "status": code, "text": text})
                    print(f"  ✗ {code} {m} {url[:90]} [{bname}] {text[:120]}")
print(f"\n{len(results)} 건 5xx/예외 · {time.time() - t0:.0f}초")
(OUT / "result.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
# 요약 — 경로별
by = {}
for x in results:
    by.setdefault((x["method"], x["route"]), []).append(x["body"])
with open(OUT / "README.md", "w", encoding="utf-8") as f:
    f.write(f"# API 퍼징\n\n5xx/예외 {len(results)} 건 · 경로 {len(by)}\n\n")
    for (m, p), bs in sorted(by.items()):
        f.write(f"- {m} {p} — {len(bs)} ({', '.join(sorted(set(bs)))})\n")
shutil.rmtree(tmp, ignore_errors=True)
