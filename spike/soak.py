"""hotfix74 — 오래 켜 둔 서버 · 여럿이 함께 쓰는 서버 (부하 · 메모리 누수).

    python3 spike/soak.py /tmp/qfe72 out/hotfix74/soak [분=10] [사용자=6]

실 데이터는 건드리지 않는다 — 원본 폴더를 임시 폴더로 복사해 진짜 uvicorn 을 띄운다.
사용자마다 한 바퀴: 첫 화면 → 결과 목록(slim) → 검토 → 장 그림(무작위 장) → 칸 편집(Q'ty) → 근거(그 행 온전히)
→ 메모 읽기.  10초마다 서버 RSS 를 적는다.  보는 것: 오류 0 · 응답 시간(p50/p95/최대) · RSS 가 끝없이 늘지 않는가.
"""
from __future__ import annotations

import json
import os
import random
import shutil
import socket
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/qfe72")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out/hotfix74/soak")
MINUTES = float(sys.argv[3]) if len(sys.argv) > 3 else 10
USERS = int(sys.argv[4]) if len(sys.argv) > 4 else 6
OUT.mkdir(parents=True, exist_ok=True)
ROOT = Path(__file__).resolve().parent.parent
tmp = Path(tempfile.mkdtemp(prefix="soak_"))
shutil.copytree(SRC, tmp / "data", ignore=shutil.ignore_patterns("page_cache"))
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
base = f"http://127.0.0.1:{port}"
env = dict(os.environ, PID_DATA_DIR=str(tmp / "data"), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=open(OUT / "server.log", "w"), stderr=subprocess.STDOUT)


def rss_mb(pid):
    try:
        for line in open(f"/proc/{pid}/status"):
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024
    except OSError:
        return 0.0
    return 0.0


def children_rss(pid):
    tot = 0.0
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            st = open(f"/proc/{d}/status").read()
        except OSError:
            continue
        if f"\nPPid:\t{pid}\n" in st:
            tot += rss_mb(int(d))
    return tot


def req(method, path, body=None, timeout=120):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(base + path, data=data, method=method,
                               headers={"content-type": "application/json"} if data else {})
    t0 = time.time()
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        payload = resp.read()
        return resp.status, time.time() - t0, payload


for _ in range(240):
    try:
        req("GET", "/version", timeout=2)
        break
    except Exception:                                          # noqa: BLE001
        time.sleep(0.5)

jobs = [j for j in json.loads(req("GET", "/jobs")[2]) if j.get("status") == "done"]
JOB = jobs[-1]["id"]
rows = json.loads(req("GET", f"/jobs/{JOB}/rows?tab=ALL&slim=1")[2])
pages = sorted({r["page_no"] for r in rows})
keys = [r["key"] for r in rows if not r.get("removed")][:400]
LAT: dict = {}
ERR: list = []
STOP = time.time() + MINUTES * 60
lock = threading.Lock()


def rec(name, dt):
    with lock:
        LAT.setdefault(name, []).append(dt)


def user(uid):
    rnd = random.Random(uid)
    while time.time() < STOP:
        steps = [("home", "GET", "/home", None),
                 ("rows", "GET", f"/jobs/{JOB}/rows?tab=ALL&slim=1", None),
                 ("review", "GET", f"/jobs/{JOB}/review", None),
                 ("page", "GET", f"/jobs/{JOB}/page/{rnd.choice(pages)}.png?zoom=1.6", None)]
        k = rnd.choice(keys)
        steps += [("edit", "PATCH", f"/jobs/{JOB}/rows/{k}",
                   {"field": "qty", "value": rnd.randint(1, 9), "author": f"부하{uid}"}),
                  ("evidence", "GET", f"/jobs/{JOB}/rows?keys={k}", None),
                  ("memo", "GET", f"/jobs/{JOB}/memo/{rnd.choice(pages)}", None)]
        for name, m, p, b in steps:
            try:
                code, dt, _ = req(m, p, b)
                rec(name, dt)
            except Exception as exc:                           # noqa: BLE001
                with lock:
                    ERR.append(f"{name} {m} {p[:60]}: {str(exc)[:120]}")


mem = []
threads = [threading.Thread(target=user, args=(i,), daemon=True) for i in range(USERS)]
t_start = time.time()
[t.start() for t in threads]
while any(t.is_alive() for t in threads):
    mem.append((round(time.time() - t_start), round(rss_mb(srv.pid)), round(children_rss(srv.pid))))
    print(f"{mem[-1][0]:5d}s  서버 RSS {mem[-1][1]} MB  자식 {mem[-1][2]} MB  요청 {sum(len(v) for v in LAT.values())}  오류 {len(ERR)}",
          flush=True)
    time.sleep(10)
srv.terminate()
try:
    srv.wait(20)
except subprocess.TimeoutExpired:
    srv.kill()

lines = [f"# 부하·장시간 (hotfix74)\n", f"사용자 {USERS} · {MINUTES:g}분 · job {JOB} ({len(rows)}행 · {len(pages)}장)\n",
         f"요청 {sum(len(v) for v in LAT.values())} · 오류 {len(ERR)}\n", "| 일 | 수 | p50 | p95 | 최대 |", "| --- | ---: | ---: | ---: | ---: |"]
for name, v in sorted(LAT.items()):
    v = sorted(v)
    lines.append(f"| {name} | {len(v)} | {statistics.median(v):.2f}s | {v[int(len(v) * 0.95) - 1]:.2f}s | {v[-1]:.2f}s |")
lines.append("\n## 서버 메모리 (10초마다)\n")
lines.append("| 초 | 서버 RSS MB | 자식 RSS MB |\n| ---: | ---: | ---: |")
lines += [f"| {a} | {b} | {c} |" for a, b, c in mem]
if ERR:
    lines.append("\n## 오류\n")
    lines += [f"- {e}" for e in ERR[:50]]
(OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines[:12]))
shutil.rmtree(tmp, ignore_errors=True)
