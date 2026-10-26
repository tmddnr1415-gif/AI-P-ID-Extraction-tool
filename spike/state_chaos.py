"""hotfix74 — 저장된 상태가 망가졌을 때 (정전 중 쓰기 · 누가 파일을 지움 · DB 손상).

    python3 spike/state_chaos.py /tmp/qfe72 out/hotfix74/state_chaos

실 데이터는 건드리지 않는다 — 원본 폴더를 임시 폴더로 복사해 `PID_DATA_DIR` 로 가리킨다.

K1 상태 파일(JSON)을 반쯤 자른다 · 비운다 · 목록으로 바꾼다 — 모든 GET 이 5xx 없이 답하는가
   (꼭 있어야 하는 장부는 사람 말 500 도 허용: 문장이 한국어이고 영문 예외가 아니어야 한다).
   그리고 저장(POST) 한 번 뒤 깨진 원본이 `.corrupt-…` 로 남는가 · 백업이 있으면 되살아나는가.
K2 업로드 PDF 가 사라졌다 — 장 그림 · 재분석 · Excel · 진단 · 마크업 제안이 사람 말로 답하는가.
K3 DB 파일이 깨졌다 — 서버가 기동하는가 / 기동 못 하면 사람 말을 남기는가 (별도 프로세스).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/qfe72")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out/hotfix74/state_chaos")
OUT.mkdir(parents=True, exist_ok=True)
tmp = Path(tempfile.mkdtemp(prefix="state_"))
shutil.copytree(SRC, tmp / "data")
DATA = tmp / "data"
os.environ["PID_DATA_DIR"] = str(DATA)
os.environ["PID_PAGE_WARM"] = "0"
os.environ["PID_RENDER_POOL"] = "0"
os.environ["PID_ANALYSIS_INPROCESS"] = "1"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402
from app import main  # noqa: E402

client = TestClient(main.app, raise_server_exceptions=False)
FOUND, DEFECTS = [], []


def note(x):
    print(x, flush=True)
    FOUND.append(x)


def defect(x):
    note("★ " + x)
    DEFECTS.append(x)


jobs = [dict(r) for r in main.CON.execute("select id, project, pdf_path from job where status='done' order by created_at")]
JOB = jobs[-1]["id"]
PROJ = jobs[-1]["project"] or "QFE"
PDIR = DATA / "projects" / PROJ
rows = json.loads(client.get(f"/jobs/{JOB}/rows?slim=1").content)
KEY = rows[0]["key"]
PAGE = rows[0]["page_no"]

GETS = ["/home", "/audit", "/version", "/jobs", f"/jobs/{JOB}", f"/jobs/{JOB}/rows?slim=1", f"/jobs/{JOB}/pages",
        f"/jobs/{JOB}/revision", f"/jobs/{JOB}/review", f"/jobs/{JOB}/multipliers", f"/jobs/{JOB}/sheet_numbers",
        f"/jobs/{JOB}/titleblock", f"/jobs/{JOB}/memo", f"/jobs/{JOB}/memo/{PAGE}", f"/jobs/{JOB}/legend_profile",
        f"/jobs/{JOB}/mode", f"/jobs/{JOB}/scope_summary", f"/jobs/{JOB}/anchors", f"/jobs/{JOB}/axis_overrides",
        f"/projects/{PROJ}", "/symbols/global", "/voc", f"/jobs/{JOB}/markup"]
# 실제로 있는 경로만 (없는 경로의 404 는 이 시험의 관심이 아니다)
paths = {r.path for r in main.app.routes if hasattr(r, "methods")}


def route_exists(url):
    u = url.split("?")[0]
    for p in paths:
        rx = "^" + re.sub(r"{[^}]+}", "[^/]+", p) + "$"
        if re.match(rx, u):
            return True
    return False


GETS = [g for g in GETS if route_exists(g)]
note(f"점검 경로 {len(GETS)}개 · job {JOB} · 프로젝트 {PROJ}")


def sweep(tag, recompare=False):
    bad = []
    calls = [("GET", u) for u in GETS] + ([("POST", f"/jobs/{JOB}/revision")] if recompare else [])
    for m, url in calls:
        r = (client.post(url, data={"project": PROJ}) if m == "POST" else client.request(m, url))
        if m == "POST" and r.status_code >= 400 and r.status_code < 500:
            note(f"{tag}: 대조 다시 → {r.status_code} {r.text[:120]}")
        if r.status_code >= 500:
            body = r.text[:300]
            human = any("가" <= ch <= "힣" for ch in body) and "Traceback" not in body
            bad.append((url, r.status_code, human, body[:160]))
    for url, code, human, body in bad:
        (note if human else defect)(f"{tag}: {code} {url} {'사람 말' if human else '영문/예외'} — {body}")
    return bad


sweep("K0 기준")

STATE = {
    "project.json": PDIR / "project.json",
    "id_registry.json": PDIR / "id_registry.json",
    "legend_profile.json": PDIR / "legend_profile.json",
}
# 사람 값 파일 — 없으면 하나씩 만들어 둔다 (저장 경로로)
main_author = {"author": "시뮬"}
client.post(f"/jobs/{JOB}/memo/{PAGE}", json={"text": "시뮬 메모", **main_author})
client.post(f"/jobs/{JOB}/sheet_numbers", json={"page_no": 1, "drawing_no": "X-0001", **main_author})
for f in sorted(PDIR.glob("*.json")):
    STATE.setdefault(f.name, f)
note("상태 파일: " + ", ".join(sorted(STATE)))

MODES = {
    "half": lambda b: b[: max(1, len(b) // 2)],
    "empty": lambda b: b"",
    "list": lambda b: b"[1, 2, 3]\n",
    "binary": lambda b: bytes(range(256)),
}

for name, path in sorted(STATE.items()):
    if not path.exists():
        continue
    orig = path.read_bytes()
    for mode, fn in MODES.items():
        # 깨지기 전 판이 백업으로 있어야 '되살림' 을 볼 수 있다 — 한 번은 백업 없이, 한 번은 있게
        for with_bak in (False, True):
            bak = path.with_name(path.name + ".bak")
            if bak.exists():
                bak.unlink()
            if with_bak:
                bak.write_bytes(orig)
            path.write_bytes(fn(orig))
            tag = f"K1 {name} {mode} {'백업있음' if with_bak else '백업없음'}"
            from app import jsonstore
            n0 = len(jsonstore.incidents())
            bad = sweep(tag, recompare=name.startswith("id_registry"))
            if len(jsonstore.incidents()) == n0 and mode != "list" and not bad:
                note(f"  {tag}: 이 파일을 읽는 경로가 점검 목록에 없음 — 판정 안 함")
                path.write_bytes(orig)
                continue
            after = path.read_bytes()
            if with_bak and mode != "list":
                if after != orig:
                    defect(f"{tag}: 백업이 있는데 되살리지 않았다")
            aside = list(path.parent.glob(path.name + ".corrupt-*"))
            if mode != "list" and not aside:
                defect(f"{tag}: 깨진 원본을 남기지 않았다")
            for a in aside:
                a.unlink()
            path.write_bytes(orig)
            if bak.exists():
                bak.unlink()
            if not bad:
                print(f"  {tag}: 5xx 0", flush=True)

# 저장이 원자적인가 — 저장 중 임시 파일이 남지 않는가 · .bak 이 생기는가
r = client.post(f"/jobs/{JOB}/memo/{PAGE}", json={"text": "두 번째", **main_author})
memo_files = [p.name for p in PDIR.iterdir() if "memo" in p.name or "notes" in p.name]
leftover_tmp = [p.name for p in PDIR.iterdir() if ".tmp" in p.name]
note(f"K1 저장 뒤 파일 {memo_files} · 남은 임시 파일 {leftover_tmp}")
if leftover_tmp:
    defect(f"K1 저장이 임시 파일을 남겼다 {leftover_tmp}")

# ---------------- K2 업로드 PDF 가 사라짐
# 원본 파일을 옮기지 않는다 (이 사본의 job 이 가리키는 PDF 가 사본 밖일 수 있다) — 이 사본 DB 에서
# 그 job 의 경로만 없는 곳으로 바꾼다.
pdf = Path(jobs[-1]["pdf_path"])
if True:
    main.CON.execute("UPDATE job SET pdf_path=? WHERE id=?", (str(DATA / "uploads" / "gone.pdf"), JOB))
    main.CON.commit()
    shutil.rmtree(DATA / "page_cache", ignore_errors=True)
    for m, url, body in [("GET", f"/jobs/{JOB}/pages/{PAGE}.png", None),
                         ("GET", f"/jobs/{JOB}/page/{PAGE}.png", None),
                         ("POST", f"/jobs/{JOB}/reanalyse", {"author": "시뮬"}),
                         ("POST", f"/jobs/{JOB}/diagnostic", {}),
                         ("GET", f"/jobs/{JOB}/feedback_export", None),
                         ("POST", f"/jobs/{JOB}/markup/propose", {"page_no": PAGE, "rect": [100, 100, 200, 200]}),
                         ("POST", f"/jobs/{JOB}/titleblock/preview", {"cells": {"dwg_no_region": [1, 1, 50, 50]}}),
                         ("GET", f"/jobs/{JOB}/notes/{PAGE}", None)]:
        if not route_exists(url):
            continue
        rr = client.request(m, url, json=body) if body is not None else client.request(m, url)
        txt = rr.text[:200] if not rr.headers.get("content-type", "").startswith(("image", "application/zip")) else rr.headers.get("content-type")
        human = any("가" <= ch <= "힣" for ch in rr.text[:400]) if rr.status_code >= 400 else True
        line = f"K2 PDF 없음 {m} {url} → {rr.status_code} {txt}"
        if rr.status_code >= 500 and not human:
            defect(line)
        else:
            note(line)
    main.CON.execute("UPDATE job SET pdf_path=? WHERE id=?", (str(pdf), JOB))
    main.CON.commit()
    # 재분석으로 줄 선 분석이 있으면 정리
    main.CON.execute("UPDATE job SET status='cancelled' WHERE status IN ('queued','running') AND id != ?", (JOB,))
    main.CON.commit()

# ---------------- K3 DB 손상 — 별도 프로세스로 기동해 본다
k3 = tmp / "k3"
shutil.copytree(SRC, k3, ignore=shutil.ignore_patterns("page_cache", "uploads"))
db = k3 / "app.db"
raw = db.read_bytes()
db.write_bytes(b"\0" * 100 + raw[100:4096])        # 머리(100바이트)가 깨진 DB
for w in k3.glob("app.db-*"):
    w.unlink()
env = dict(os.environ, PID_DATA_DIR=str(k3), PYTHONPATH=str(ROOT))
cp = subprocess.run([sys.executable, "-c", "import app.main as m; print('STARTED', m.DB_PATH)"],
                    cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=180)
started = "STARTED" in cp.stdout
tail = (cp.stdout + cp.stderr)[-600:]
human = any("가" <= ch <= "힣" for ch in tail)
note(f"K3 DB 머리 손상 → 기동 {'됨' if started else '안 됨'} · 마지막 출력: {tail[-300:]!r}")
if not started and not human:
    defect("K3 DB 가 깨지면 서버가 영문 예외로만 멈춘다 — 무엇을 하면 되는지 말하지 않는다")
if started:
    aside = [p.name for p in k3.iterdir() if p.name.startswith("app.db.")]
    note(f"K3 기동 뒤 DB 폴더 {aside}")

(OUT / "README.md").write_text("# 상태 손상 시뮬레이션\n\n결함 " + str(len(DEFECTS)) + "\n\n"
                               + "\n".join(f"- {x}" for x in FOUND) + "\n", encoding="utf-8")
print(f"\n결함 {len(DEFECTS)}")
shutil.rmtree(tmp, ignore_errors=True)
