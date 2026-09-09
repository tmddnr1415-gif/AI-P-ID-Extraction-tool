"""꾸러미 r25 — 회사 PC 조건 재현 적용 검증 (14단계).

    python3 spike/verify_r25.py <단계>

`git worktree`(aac64ba) + `PID_DATA_DIR` 격리로 회사 PC 조건을 만들고,
**꾸러미를 실제로 풀어** 확인한다.  ★ 실 DB(`app/_data/`)는 어느 단계에서도
열지 않는다 — 시작·끝 sha256 을 대조해 증명한다.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = Path("/tmp/v25")
DATA = Path("/tmp/v25_data")
OUT = ROOT / "out" / "round25" / "verify"
BASE = "aac64ba"
PDF = ROOT / "data" / "pid_total.pdf"
REALDB = ROOT / "app" / "_data" / "app.db"


def say(*a):
    print(*a, flush=True)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "(없음)"


def save(name, obj):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
    say("→", OUT / name)


def load(name):
    return json.loads((OUT / name).read_text())


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class Server:
    def __init__(self, port):
        self.port = port
        env = dict(os.environ)
        env["PID_DATA_DIR"] = str(DATA)
        env.pop("PID_PROJECT_CONFIG", None)
        self.log = open(OUT / "server.log", "ab")
        self.p = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app",
             "--host", "127.0.0.1", "--port", str(port)],
            cwd=WORK, env=env, stdout=self.log, stderr=subprocess.STDOUT)
        for _ in range(120):
            try:
                # 준비 확인은 `/jobs` 로 한다 — `/home` 은 13회차에 생긴 것이라
                # 옛 코드(aac64ba)에는 없다 (404 를 "안 떴다" 로 읽으면 안 된다).
                self.get("/jobs")
                return
            except Exception:
                time.sleep(1.0)
        raise SystemExit("서버가 뜨지 않았습니다")

    def url(self, path):
        return "http://127.0.0.1:%d%s" % (self.port, path)

    def get(self, path):
        with urllib.request.urlopen(self.url(path), timeout=120) as r:
            return json.loads(r.read().decode())

    def send(self, path, payload, method="POST"):
        req = urllib.request.Request(
            self.url(path), data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}, method=method)
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())

    def form(self, path, fields):
        """폼 한 벌만 보내는 자리 (`/projects` 는 Form 을 받는다)."""
        body = "&".join("%s=%s" % (k, urllib.parse.quote(str(v))) for k, v in fields.items())
        req = urllib.request.Request(
            self.url(path), data=body.encode(), method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())

    def upload(self, pdf: Path, project: str = "", compared_with: str = ""):
        boundary = "----v25"
        parts = []
        for k, v in (("project", project), ("compared_with", compared_with)):
            parts.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n"
                          % (boundary, k, v)).encode())
        parts.append(("--%s\r\nContent-Disposition: form-data; name=\"pdf\"; "
                      "filename=\"%s\"\r\nContent-Type: application/pdf\r\n\r\n"
                      % (boundary, pdf.name)).encode())
        parts.append(pdf.read_bytes())
        parts.append(("\r\n--%s--\r\n" % boundary).encode())
        body = b"".join(parts)
        req = urllib.request.Request(
            self.url("/jobs"), data=body, method="POST",
            headers={"Content-Type": "multipart/form-data; boundary=%s" % boundary})
        with urllib.request.urlopen(req, timeout=600) as r:
            return json.loads(r.read().decode())

    def wait(self, job_id, limit=1800):
        t0 = time.time()
        while time.time() - t0 < limit:
            j = self.get("/jobs/%s" % job_id)
            if j.get("status") in ("done", "failed", "cancelled"):
                return j, round(time.time() - t0, 1)
            time.sleep(5)
        raise SystemExit("분석이 %d초 안에 끝나지 않았습니다" % limit)

    def peak_rss_gb(self):
        """`/proc/<pid>/status` 의 VmHWM — 프로세스 생애 최고 RSS (kB)."""
        for line in Path("/proc/%d/status" % self.p.pid).read_text().splitlines():
            if line.startswith("VmHWM:"):
                return round(int(line.split()[1]) / 1024 / 1024, 2)
        return None

    def stop(self):
        self.p.terminate()
        try:
            self.p.wait(20)
        except Exception:
            self.p.kill()
        self.log.close()


# --------------------------------------------------------------------------
def stage1234():
    """1 격리 · 2 옛 코드로 분석 · 3 편집 5칸 · 4 백업."""
    OUT.mkdir(parents=True, exist_ok=True)
    if WORK.exists():
        subprocess.run(["git", "worktree", "remove", "--force", str(WORK)], cwd=ROOT)
    if DATA.exists():
        shutil.rmtree(DATA)
    subprocess.run(["git", "worktree", "add", "--detach", str(WORK), BASE],
                   cwd=ROOT, check=True)
    DATA.mkdir(parents=True)
    before = sha(REALDB)
    say("1 worktree %s · PID_DATA_DIR %s · 실 DB %s" % (BASE, DATA, before[:12]))

    srv = Server(free_port())
    try:
        srv.form("/projects", {"name": "AL NOUF1"})     # Rev.A 를 연다
        j = srv.upload(PDF, project="AL NOUF1")
        job = j["job_id"]
        done, secs = srv.wait(job)
        rows = srv.get("/jobs/%s/rows" % job)
        say("2 옛 코드 분석 — 상태 %s · %d행 · %.1f초" % (done["status"], len(rows), secs))
        field = [r for r in rows if r.get("tab") == "FIELD"][:5]
        edits = []
        for i, r in enumerate(field):
            res = srv.send("/jobs/%s/rows/%s" % (job, r["key"]),
                           {"field": "description",
                            "value": "검증 편집 %d" % (i + 1),
                            "author": "검증자"}, method="PATCH")
            edits.append({"key": r["key"], "value": "검증 편집 %d" % (i + 1),
                          "ok": bool(res.get("user"))})
        say("3 편집 %d칸 (작성자 검증자)" % len(edits))
    finally:
        srv.stop()

    backup = OUT / "db_backup"
    if backup.exists():
        shutil.rmtree(backup)
    backup.mkdir(parents=True)
    for f in DATA.rglob("*"):
        if f.is_file() and f.suffix in (".db", ".db-wal", ".db-shm") or f.name.startswith("app.db"):
            shutil.copy2(f, backup / f.name)
    say("4 백업 %s" % sorted(p.name for p in backup.iterdir()))
    save("stage1234.json", {
        "worktree_base": BASE, "job": job, "rows_old": len(rows),
        "seconds": secs, "edits": edits,
        "realdb_sha_before": before,
        "backup": sorted(p.name for p in backup.iterdir()),
        "scope_counts": _scope_counts(rows)})


def _scope_counts(rows):
    out = {}
    for r in rows:
        s = (r.get("values") or {}).get("scope") or "(빈칸)"
        out[s] = out.get(s, 0) + 1
    return out


def stage5():
    """5 꾸러미를 실제로 풀고 HEAD 와 바이트 대조."""
    import zipfile
    pkg = ROOT / "out" / "round25" / "3_FILES_TO_OVERWRITE.zip"
    with zipfile.ZipFile(pkg) as z:
        names = z.namelist()
        bad = [n for n in names if "app/_data" in n or n.startswith("out/")]
        assert not bad, bad
        z.extractall(WORK)
    diff = []
    for n in names:
        a = (WORK / n).read_bytes()
        b = (ROOT / n).read_bytes()
        if a != b:
            diff.append(n)
    say("5 %d파일 풀었습니다 · HEAD 와 다른 파일 %d개" % (len(names), len(diff)))
    save("stage5.json", {"files": len(names), "different": diff,
                         "package_sha256": sha(pkg)})


def stage678():
    """6 첫 화면·편집 생존 · 7 결과 화면 · 8 새 분석과 승계."""
    prev = load("stage1234.json")
    srv = Server(free_port())
    try:
        home = srv.get("/home")
        rows = srv.get("/jobs/%s/rows" % prev["job"])
        alive = 0
        for e in prev["edits"]:
            row = next((r for r in rows if r["key"] == e["key"]), None)
            if row and (row.get("values") or {}).get("description") == e["value"]:
                alive += 1
        say("6 첫 화면 프로젝트 %d개 · 옛 분석 %d행 · 편집 생존 %d/%d"
            % (len(home.get("projects") or []), len(rows), alive, len(prev["edits"])))

        j = srv.upload(PDF, project="AL NOUF1")
        job2 = j["job_id"]
        done, secs = srv.wait(job2)
        rows2 = srv.get("/jobs/%s/rows" % job2)
        qty = sum(int((r.get("values") or {}).get("qty") or 0) for r in rows2)
        carried = 0
        for e in prev["edits"]:
            if any((r.get("values") or {}).get("description") == e["value"] for r in rows2):
                carried += 1
        summary = srv.get("/jobs/%s/scope_summary" % job2)
        rss = srv.peak_rss_gb()
        say("8 새 분석 %d행 · Q'ty %d · 지문 %s · %.1f초 · 승계 %d/%d"
            % (len(rows2), qty, (done.get("fingerprint") or "")[:8], secs,
               carried, len(prev["edits"])))
        say("14 ★ 8단계 분석 프로세스의 최대 RSS %.2fGB (VmHWM)" % rss)
        save("stage14.json", {"job": job2, "max_rss_gb": rss,
                              "how": "uvicorn 프로세스 /proc/<pid>/status VmHWM — 분석은 그 프로세스의 스레드"})
        save("stage678.json", {
            "home_projects": len(home.get("projects") or []),
            "old_rows": len(rows), "edits_alive": alive,
            "job2": job2, "rows_new": len(rows2), "qty_sum": qty,
            "fingerprint": done.get("fingerprint"), "seconds": secs,
            "carried": carried, "scope_summary": summary,
            "max_rss_gb": rss,
            "revision": done.get("revision"),
            "compared_with": done.get("compared_with")})
    finally:
        srv.stop()


def stage7():
    """7 첫 화면 → 결과 → 첫 화면 (실제 화면).

    ★ 진입 경로는 `a.revrow` 다 — `?job=` 로 URL 을 직접 열면 결과 화면이 뜨지
    않는다 (13회차 설계 그대로, 20회차 검증이 그것을 몰라 0행을 냈다).
    """
    from playwright.sync_api import sync_playwright
    srv = Server(free_port())
    shots = {}
    try:
        with sync_playwright() as pw:
            # 브라우저 자리는 시험과 같은 값을 쓴다 (`playwright install` 하지 않는다)
            br = pw.chromium.launch(executable_path=os.environ.get(
                "CHROMIUM_PATH", "/opt/pw-browsers/chromium"))
            pg = br.new_page(viewport={"width": 1400, "height": 900})
            pg.goto(srv.url("/"), wait_until="networkidle")
            pg.wait_for_selector("a.revrow", timeout=30000)
            pg.screenshot(path=str(OUT / "s7_1_home.png"))
            home_text = pg.inner_text("body")[:400]
            pg.click("a.revrow")
            pg.wait_for_selector("#main:not([hidden])", timeout=120000)
            pg.wait_for_timeout(2000)
            pg.screenshot(path=str(OUT / "s7_2_rows.png"))
            rows_seen = pg.eval_on_selector_all("#grid tbody tr", "els => els.length")
            pg.click("#to-home")
            pg.wait_for_selector("a.revrow", timeout=30000)
            pg.wait_for_timeout(1000)
            pg.screenshot(path=str(OUT / "s7_3_back.png"))
            # ★ 화면은 `hidden` 속성이 아니라 `hidden` **클래스**로 감춘다
            # (`toFirstScreen`).  속성으로 물으면 언제나 False 라 통과로 읽힌다.
            main_hidden = pg.eval_on_selector(
                "#main", "el => el.classList.contains('hidden')")
            drop_shown = pg.eval_on_selector(
                "#drop", "el => !el.classList.contains('hidden')")
            br.close()
        for n in ("s7_1_home.png", "s7_2_rows.png", "s7_3_back.png"):
            shots[n] = hashlib.md5((OUT / n).read_bytes()).hexdigest()[:12]
        say("7 첫 화면 → 결과(%d행 보임) → 첫 화면 (#main 감춤=%s · #drop 보임=%s)"
            % (rows_seen, main_hidden, drop_shown))
        say("  캡처 md5 %s" % shots)
        save("stage7.json", {"rows_in_grid": rows_seen, "main_hidden": main_hidden,
                             "drop_shown": drop_shown,
                             "home_text": home_text, "shots": shots})
    finally:
        srv.stop()


def stage9():
    """9 발주처 양식 — **서버가 만든 실제 xlsx 를 열어** 센다.

    빈 양식(`data/blank/`)은 발주처 자료라 저장소에 없다 (gitignore).  회사 PC
    에는 그 폴더가 있으므로, 검증에서는 이 저장소의 것을 worktree 로 **복사만**
    한다 — 꾸러미에는 들어가지 않는다.
    """
    import io
    import zipfile
    import openpyxl
    blank_src = ROOT / "data" / "blank"
    blank_dst = WORK / "data" / "blank"
    blank_dst.mkdir(parents=True, exist_ok=True)
    for f in blank_src.glob("*.xlsx"):
        shutil.copy2(f, blank_dst / f.name)

    prev = load("stage678.json")
    srv = Server(free_port())
    try:
        snap = srv.send("/jobs/%s/snapshot" % prev["job2"], {"label": "검증 r25"})
        rev_id = snap.get("id") or snap.get("revision_id")
        with urllib.request.urlopen(srv.url("/revisions/%s/excel" % rev_id),
                                    timeout=600) as r:
            blob = r.read()
    finally:
        srv.stop()
    zpath = OUT / "deliverables.zip"
    zpath.write_bytes(blob)
    counts = {}
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for name in z.namelist():
            if not name.endswith(".xlsx"):
                continue
            wb = openpyxl.load_workbook(io.BytesIO(z.read(name)))
            ws = wb[wb.sheetnames[0]]
            n = 0
            for row in ws.iter_rows(min_row=1, values_only=True):
                if row and str(row[0] or "").strip().isdigit():
                    n += 1
            counts[name] = n
    say("9 양식 %s" % counts)
    save("stage9.json", {"revision_id": rev_id, "rows": counts,
                         "zip_sha256": hashlib.sha256(blob).hexdigest()})


def stage13():
    """13 21회차 합성 PDF · 24회차 TC2 REV."""
    import pymupdf
    synth = OUT / "synthetic_hist.pdf"
    doc = pymupdf.open()
    for _ in range(12):                     # A1 12장 · 이력 괘선 간격 2.0pt
        page = doc.new_page(width=2384, height=1684)
        for y in (1210.0, 1212.0, 1240.0):
            page.draw_line(pymupdf.Point(1900, y), pymupdf.Point(2340, y), width=0.3)
        page.draw_line(pymupdf.Point(1969.5, 100), pymupdf.Point(1969.5, 1600), width=0.3)
    doc.save(synth)
    doc.close()

    srv = Server(free_port())
    try:
        j = srv.upload(synth)
        done, secs = srv.wait(j["job_id"], limit=1200)
        rows = srv.get("/jobs/%s/rows" % j["job_id"])
        detail = ""
        try:
            detail = srv.get("/jobs/%s/error_detail" % j["job_id"])
        except Exception as exc:
            detail = "(없음: %s)" % exc
        say("13a 합성 PDF — 상태 %s · %d행 · %.1f초" % (done["status"], len(rows), secs))
        say("    사유: %s" % (done.get("message") or "")[:160])
        save("stage13.json", {
            "status": done["status"], "rows": len(rows), "seconds": secs,
            "message": done.get("message"), "stopped_stage": done.get("stopped_stage"),
            "error_detail_head": str(detail)[:400]})
    finally:
        srv.stop()


def stage10():
    """10 두 축 — 검증 DB 가 들고 있는 **그 분석의 행**으로 잰다."""
    import sqlite3
    prev = load("stage678.json")
    con = sqlite3.connect(DATA / "app.db")
    con.row_factory = sqlite3.Row
    # `accuracy.py` 는 파이프라인 행의 **values** 를 본다 (drawing_no · type ·
    # valve_type · scope) 그리고 `tab` 을 함께 본다.  DB 는 그 둘을 다른 칸에
    # 들고 있으므로 여기서 합친다 — 값은 만들지 않는다.
    rows = []
    for r in con.execute("SELECT tab, drawing_no, ai_json FROM item"
                         " WHERE job_id=? AND deleted=0", (prev["job2"],)):
        v = json.loads(r["ai_json"])
        v.setdefault("drawing_no", r["drawing_no"])
        v["tab"] = r["tab"]
        rows.append(v)
    con.close()
    run = OUT / "verify_rows.json"
    run.write_text(json.dumps({"rows": rows}, ensure_ascii=False))
    out = subprocess.run([sys.executable, str(ROOT / "spike" / "accuracy.py"), str(run)],
                         cwd=ROOT, capture_output=True, text=True)
    say(out.stdout.strip()[-1200:] or out.stderr.strip()[-800:])
    save("stage10.json", {"rows": len(rows), "stdout": out.stdout,
                          "returncode": out.returncode})


def stage12():
    """12 실 DB sha256 — 시작·끝 동일."""
    prev = load("stage1234.json")
    now = sha(REALDB)
    same = now == prev["realdb_sha_before"]
    say("12 실 DB %s ↔ %s — %s" % (prev["realdb_sha_before"][:12], now[:12],
                                   "동일" if same else "★ 달라졌습니다"))
    save("stage12.json", {"before": prev["realdb_sha_before"], "after": now,
                          "same": same})


STAGES = {"1234": stage1234, "5": stage5, "678": stage678, "7": stage7,
          "10": stage10,
          "9": stage9, "12": stage12, "13": stage13}

if __name__ == "__main__":
    STAGES[sys.argv[1]]()
