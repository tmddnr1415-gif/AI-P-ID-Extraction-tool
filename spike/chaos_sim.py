"""hotfix74 — 프로세스 돌발상황 시뮬레이션.  실제 uvicorn 서버를 임시 데이터 폴더로 띄우고 사고를 낸다.

    python3 spike/chaos_sim.py out/hotfix74/chaos

  S1 동시 업로드 셋 — 줄을 서고 전부 끝나는가 · `/running` 이 앞뒤를 말하는가
  S2 분석 자식 프로세스 강제 종료(kill -9) — 그 분석만 실패로 적히고 문장이 사람 말인가 · 서버는 사는가 · 다음 분석은 도는가
  S3 대기 중 취소 · 분석 중 삭제(409) · 취소 뒤 삭제
  S4 서버 강제 종료(kill -9) 뒤 재시작 — 돌던 것은 실패(멈춘 단계와 함께) · 기다리던 것은 다시 줄에 서서 끝나는가
  S5 DB 를 다른 프로세스가 15초 동안 잠근다 — 읽기·쓰기가 멈추지 않고 끝나는가 (오류라면 사람 말인가)
  S6 같은 PDF 를 같은 프로젝트에 동시에 둘 — 리비전 번호가 겹치지 않는가
실 데이터는 건드리지 않는다.  자기 셸을 죽이지 않도록 자식은 이 스크립트가 띄운 서버의 자식만 찾는다.
"""
from __future__ import annotations

import json
import os
import random
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "out/hotfix74/chaos")
ONLY = set(sys.argv[2:])          # 비우면 전부 · 예: S2 S4


def want(tag):
    return not ONLY or tag in ONLY
OUT.mkdir(parents=True, exist_ok=True)
DATA = Path(tempfile.mkdtemp(prefix="chaos_"))
SYN = ROOT / "tests/data/synthetic"
PDF = (SYN / "08b_tagged_same_size.pdf").read_bytes()
LOG = []
DEFECTS = []


def note(s):
    print(s, flush=True)
    LOG.append(s)


def defect(s):
    note("★ " + s)
    DEFECTS.append(s)


class Server:
    def __init__(self):
        s = socket.socket(); s.bind(("127.0.0.1", 0)); self.port = s.getsockname()[1]; s.close()
        self.base = f"http://127.0.0.1:{self.port}"
        self.proc = None
        self.n = 0

    def start(self):
        self.n += 1
        env = dict(os.environ, PID_DATA_DIR=str(DATA), PYTHONPATH=str(ROOT), PID_PAGE_WARM="0")
        self.log = open(OUT / f"server{self.n}.log", "w")
        self.proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                                      "--port", str(self.port)], cwd=str(ROOT), env=env,
                                     stdout=self.log, stderr=subprocess.STDOUT)
        for _ in range(120):
            try:
                urllib.request.urlopen(self.base + "/version", timeout=2)
                return
            except Exception:                                          # noqa: BLE001
                time.sleep(0.5)
        raise SystemExit("server did not start")

    def kill(self):
        self.proc.send_signal(signal.SIGKILL)
        self.proc.wait()

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(20)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def children(self):
        """이 서버의 자식 프로세스 pid (분석 자식 · 렌더 일꾼)."""
        out = []
        for p in Path("/proc").iterdir():
            if not p.name.isdigit():
                continue
            try:
                st = (p / "stat").read_text().split()
                if int(st[3]) == self.proc.pid:
                    cmd = (p / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="ignore")
                    out.append((int(p.name), cmd))
            except Exception:                                          # noqa: BLE001
                pass
        return out


S = Server()


def req(method, path, data=None, form=None, files=None, timeout=60):
    if form is not None and files is None:
        body = urllib.parse.urlencode(form).encode()
        rq = urllib.request.Request(S.base + path, data=body, method=method,
                                    headers={"Content-Type": "application/x-www-form-urlencoded"})
        t0 = time.time()
        try:
            with urllib.request.urlopen(rq, timeout=timeout) as r:
                raw, code = r.read(), r.status
        except urllib.error.HTTPError as e:
            raw, code = e.read(), e.code
        try:
            return code, json.loads(raw), time.time() - t0
        except Exception:                                              # noqa: BLE001
            return code, raw[:200], time.time() - t0
    url = S.base + path
    body, headers = None, {}
    if files is not None:
        b = "----chaos" + str(random.randint(1, 10 ** 9))
        parts = [f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
                 for k, v in (form or {}).items()]
        for k, (fn, blob) in files.items():
            parts.append(f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{fn}\"\r\n"
                         f"Content-Type: application/pdf\r\n\r\n".encode() + blob + b"\r\n")
        parts.append(f"--{b}--\r\n".encode())
        body = b"".join(parts); headers["Content-Type"] = f"multipart/form-data; boundary={b}"
    elif data is not None:
        body = json.dumps(data).encode(); headers["Content-Type"] = "application/json"
    rq = urllib.request.Request(url, data=body, method=method, headers=headers)
    t0 = time.time()
    try:
        with urllib.request.urlopen(rq, timeout=timeout) as r:
            raw = r.read(); code = r.status
    except urllib.error.HTTPError as e:
        raw = e.read(); code = e.code
    except Exception as e:                                             # noqa: BLE001
        return -1, str(e), time.time() - t0
    try:
        return code, json.loads(raw), time.time() - t0
    except Exception:                                                  # noqa: BLE001
        return code, raw[:200], time.time() - t0


def upload(project="", name="chaos.pdf", blob=PDF):
    code, body, _ = req("POST", "/jobs", form={"project": project}, files={"pdf": (name, blob)})
    return code, body


def status(jid):
    code, body, _ = req("GET", f"/jobs/{jid}")
    return body if code == 200 else {"status": f"HTTP {code}"}


def wait(jid, want=("done", "failed", "cancelled"), limit=900):
    t0 = time.time()
    while time.time() - t0 < limit:
        st = status(jid)
        if st.get("status") in want:
            return st
        time.sleep(2)
    return status(jid)


def wait_status(jid, want, limit=300):
    return wait(jid, want=(want,), limit=limit)


def analysis_child(before=()):
    """분석 자식 — 업로드 **뒤에 새로 생긴** spawn 자식 (렌더 일꾼 · resource tracker 는 뺀다)."""
    for _ in range(120):
        kids = [(p, c) for p, c in S.children()
                if "spawn_main" in c and p not in before and "resource_tracker" not in c]
        if kids:
            return max(kids)[0]
        time.sleep(0.5)
    return None


def detail(jid):
    c, b, _ = req("GET", f"/jobs/{jid}/error_detail")
    return str(b)[-600:]


try:
    S.start()
    note(f"서버 {S.base} · 데이터 {DATA}")

    # ---------------------------------------------------------------- S1
    note("## S1 동시 업로드 셋")
    ids = []
    th = []
    lock = threading.Lock()

    def up(i):
        c, b = upload(name=f"동시{i}.pdf")
        with lock:
            ids.append((c, b))
    for i in range(3):
        t = threading.Thread(target=up, args=(i,)); t.start(); th.append(t)
    for t in th:
        t.join()
    jids = [b.get("job_id") for c, b in ids if c == 200 and isinstance(b, dict)]
    note(f"  업로드 응답 {[c for c, _ in ids]} · job {jids}")
    if len(jids) != 3:
        defect("S1 동시 업로드 셋 중 받지 못한 것이 있다")
    code, run, _ = req("GET", "/running")
    note(f"  /running → {code} · {[(r.get('id') or r.get('job_id'), r.get('status')) for r in (run if isinstance(run, list) else run.get('jobs', []) if isinstance(run, dict) else [])]}")
    finals = [wait(j) for j in jids]
    note(f"  끝 상태 {[f.get('status') for f in finals]}")
    if any(f.get("status") != "done" for f in finals):
        defect(f"S1 동시 업로드 중 끝나지 않은 것: {[(f.get('status'), f.get('message')) for f in finals]}")

    # ---------------------------------------------------------------- S2
    note("## S2 분석 자식 kill -9")
    before = {p for p, _ in S.children()}
    c, b = upload(name="자식종료.pdf")
    jid = b.get("job_id")
    wait_status(jid, "running")
    pid = analysis_child(before)
    note(f"  자식 pid {pid}")
    time.sleep(3)
    if pid:
        os.kill(pid, signal.SIGKILL)
    st = wait(jid, limit=120)
    note(f"  상태 {st.get('status')} · 문장 {str(st.get('message'))[:160]}")
    if st.get("status") != "failed":
        defect(f"S2 자식이 죽었는데 분석이 실패로 적히지 않았다: {st.get('status')}")
    msg = str(st.get("message") or "") + str(st.get("error") or "")
    if "Traceback" in msg or "exitcode" in msg.lower() or not any("가" <= ch <= "힣" for ch in msg):
        defect(f"S2 실패 문장이 사람 말이 아니다: {msg[:200]}")
    c2, b2 = upload(name="자식종료뒤.pdf")
    st2 = wait(b2.get("job_id"))
    note(f"  다음 분석 {st2.get('status')}")
    if st2.get("status") != "done":
        defect("S2 자식이 죽은 뒤 다음 분석이 안 돈다")

    # ---------------------------------------------------------------- S3
    note("## S3 대기 중 취소 · 분석 중 삭제 · 취소 뒤 삭제")
    _, a = upload(name="앞.pdf"); _, q = upload(name="대기.pdf")
    a, q = a.get("job_id"), q.get("job_id")
    wait_status(a, "running")
    sq = status(q).get("status")
    cc, cb, _ = req("POST", f"/jobs/{q}/cancel")
    note(f"  대기({sq}) 취소 → {cc} · 상태 {status(q).get('status')}")
    dc, db_, _ = req("DELETE", f"/jobs/{a}", form={"confirm": a, "author": "시뮬"})
    note(f"  분석 중 삭제 → {dc} {str(db_)[:100]}")
    if dc != 409:
        defect(f"S3 분석 중 삭제가 막히지 않았다: {dc}")
    fa = wait(a); fq = wait(q, limit=60)
    note(f"  앞 {fa.get('status')} · 대기 {fq.get('status')}")
    if fq.get("status") not in ("cancelled",):
        defect(f"S3 대기 중 취소한 분석이 {fq.get('status')}")
    dc2, _, _ = req("DELETE", f"/jobs/{q}", form={"confirm": q, "author": "시뮬"})
    note(f"  취소 뒤 삭제 → {dc2}")
    if dc2 != 200:
        defect(f"S3 취소한 분석을 지우지 못한다: {dc2}")

    # ---------------------------------------------------------------- S4
    note("## S4 서버 kill -9 → 재시작")
    _, r1 = upload(name="재시작중.pdf"); _, r2 = upload(name="재시작대기.pdf")
    r1, r2 = r1.get("job_id"), r2.get("job_id")
    wait_status(r1, "running")
    time.sleep(3)
    kids = S.children()
    note("  서버의 자식: " + " | ".join(f"{p}:{c[-60:]}" for p, c in kids))
    S.kill()
    for p, _c in kids:                                   # 고아가 된 분석 자식 — 서버가 죽으면 같이 죽어야 한다
        try:
            os.kill(p, 0)
            note(f"  ⚠ 서버가 죽은 뒤에도 자식 {p} 가 살아 있다")
        except ProcessLookupError:
            pass
    time.sleep(2)
    orphan = []
    for p, _c in kids:
        try:
            os.kill(p, 0); orphan.append(p)
        except ProcessLookupError:
            pass
    S.start()
    s1, s2 = status(r1), status(r2)
    note(f"  재시작 직후: 돌던 것 {s1.get('status')} ({str(s1.get('message'))[:100]}) · 기다리던 것 {s2.get('status')}")
    if s1.get("status") != "failed":
        defect(f"S4 재시작 뒤 돌던 분석이 {s1.get('status')}")
    f2 = wait(r2)
    note(f"  기다리던 것 끝 {f2.get('status')} · {str(f2.get('message'))[:200]}")
    if f2.get("status") == "failed":
        note("  error_detail: " + detail(r2))
    if f2.get("status") != "done":
        defect(f"S4 재시작 뒤 기다리던 분석이 끝나지 않았다: {f2.get('status')}")
    if orphan:
        time.sleep(5)
        still = []
        for p in orphan:
            try:
                os.kill(p, 0); still.append(p)
            except ProcessLookupError:
                pass
        if still:
            defect(f"S4 서버가 죽은 뒤 분석 자식 {still} 가 계속 돈다 (고아 프로세스 — CPU·메모리를 쥔다)")
            for p in still:
                try:
                    os.kill(p, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        else:
            note(f"  서버가 죽은 뒤 자식 {orphan} 은 몇 초 안에 스스로 끝났다")

    # ---------------------------------------------------------------- S5
    note("## S5 다른 프로세스가 DB 를 15초 잠금")
    any_job = jids[0]
    _c, _rows, _ = req("GET", f"/jobs/{any_job}/rows")
    ROWKEY = _rows[0]["key"] if isinstance(_rows, list) and _rows else "__none__"
    holder = subprocess.Popen([sys.executable, "-c",
                               "import sqlite3,time,sys;c=sqlite3.connect(sys.argv[1]);"
                               "c.execute('BEGIN EXCLUSIVE');time.sleep(15);c.rollback()",
                               str(DATA / "app.db")])
    time.sleep(1)
    for label, m, p, body in [("목록", "GET", f"/jobs/{any_job}/rows", None),
                              ("첫 화면", "GET", "/home", None),
                              ("편집", "PATCH", f"/jobs/{jids[0]}/rows/{ROWKEY}", {"field": "qty", "value": 2,
                                                                                   "author": "시뮬"})]:
        c, b, dt = req(m, p, data=body, timeout=40)
        note(f"  잠긴 동안 {label} → {c} · {dt:.1f}초 · {str(b)[:120]}")
        if c == -1 or (c >= 500 and "기록 번호" not in str(b)):
            defect(f"S5 DB 잠금 중 {label} 가 사람 말 없이 실패: {c} {str(b)[:120]}")
    holder.wait()

    # ---------------------------------------------------------------- S6
    note("## S6 같은 프로젝트에 동시에 둘")
    pc, pb, _ = req("POST", "/projects", form={"name": "CHAOS"})
    note(f"  프로젝트 만들기 → {pc}")
    res = []
    def up2(i):
        res.append(upload(project="CHAOS", name=f"rev{i}.pdf"))
    t1 = threading.Thread(target=up2, args=(1,)); t2 = threading.Thread(target=up2, args=(2,))
    t1.start(); t2.start(); t1.join(); t2.join()
    revs = [(c, (b.get("revision") if isinstance(b, dict) else b)) for c, b in res]
    note(f"  응답 {revs}")
    js = [b.get("job_id") for c, b in res if c == 200]
    for j in js:
        wait(j)
    code, home, _ = req("GET", "/home")
    proj = [p for p in (home.get("projects") or []) if p.get("name") == "CHAOS"] if isinstance(home, dict) else []
    rv = [r.get("revision") for r in (proj[0].get("revisions") or [])] if proj else []
    note(f"  장부 리비전 {rv}")
    if len(rv) != len(set(rv)):
        defect(f"S6 같은 리비전 이름이 둘: {rv}")

    code, au, _ = req("GET", "/audit")
    note(f"  위생 감사 → {code} · {str(au)[:300]}")
finally:
    S.stop()
    alive = [p for p, _ in (S.children() if S.proc else [])]
    (OUT / "README.md").write_text("# 프로세스 돌발상황\n\n결함 " + str(len(DEFECTS)) + "\n\n"
                                   + "\n".join(f"- {x}" for x in LOG) + "\n", encoding="utf-8")
    shutil.rmtree(DATA, ignore_errors=True)
    print(f"\n결함 {len(DEFECTS)}")
