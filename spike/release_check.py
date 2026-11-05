"""출시 전 검사 — 꾸러미(spike/pack_delta.py)를 만들기 전에 반드시 한 번 돌린다.

    python3 spike/release_check.py              시험 · JS 구문 · 서버 주소 스모크 (+ 화면 눈 점검이 되면)
    python3 spike/release_check.py --strict     회사 PC: 도면 자료가 없어 건너뛴 시험이 있으면 실패
    python3 spike/release_check.py --no-screens 화면 캡처 점검(spike/smoke_screens.js)은 건너뛴다

hotfix132 — 하는 일 (순서대로 · 하나라도 실패하면 ok=false):
  1. pytest  `-m "not slow and not ui" -rs` — tests/test_valve* 는 빼고 돌린다 (회사 소유 · 참고로 따로 돌려 valve_ok 에 적음)
  2. JS 구문  app/static/**/*.js (*.min.js · valve/ 제외) 를 `node --check`.  node 가 없으면 건너뜀으로 적는다.
  3. 서버 스모크  TestClient 로 13 주소가 200 인지 (화면 12 · /version · /help/manual · /running)
  4. 화면 눈 점검  node + playwright 가 있으면 임시 서버를 띄워 spike/smoke_screens.js (없으면 한 줄 남기고 건너뜀)
결과는 out/release_check.json {head, ok, at, strict, steps, skipped, failures, valve_ok}.
pack_delta 는 이 파일의 head 가 지금 HEAD(또는 문서만 다른 HEAD) 이고 ok 일 때만 꾸러미를 만든다.

★ 서버 스모크와 화면 점검은 **임시 자료 폴더**(PID_DATA_DIR)에서 돈다 — 실 자료(app\\_data)를 건드리지 않는다.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "release_check.json"
STATIC = ROOT / "app" / "static"
SMOKE_JS = ROOT / "spike" / "smoke_screens.js"

SMOKE_PATHS = ("/", "/logic", "/logic/draw", "/logic/test", "/logic/commission", "/logic/signal",
               "/space", "/space?view=3d", "/dcs", "/books/", "/version", "/help/manual", "/running")
# --strict 에서 실패로 보는 '자료가 없어 건너뜀' 사유 (회사 PC 에는 도면·결과가 있어야 한다)
STRICT_WORDS = ("PDF", "pdf", "결과 json", "워크북", "sample", "도면")
QUIET_ENV = {"PID_PAGE_WARM": "0", "PID_RENDER_POOL": "0", "PID_LOGIC_WARM": "0", "PID_ROWS_WARM": "0",
             "PID_TYPICAL_SEED": "0", "PID_DRAW_SEED": "0", "PID_BACKUP_EVERY_S": "86400"}


def _say(*a) -> None:
    print(*a, flush=True)


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


# ---------------------------------------------------------------- 1. pytest
_SKIP_LINE = re.compile(r"^SKIPPED \[\d+\] (.+?): (.*)$")


def parse_pytest(out: str) -> dict:
    lines = out.strip().splitlines()
    summary = next((ln.strip("= ").strip() for ln in reversed(lines) if re.search(r"\d+ (passed|failed|error)", ln)), "")
    skipped = [f"{m.group(1)}: {m.group(2)}" for ln in lines if (m := _SKIP_LINE.match(ln.strip()))]
    failed = [ln.split(" ", 1)[1].split(" - ")[0] for ln in lines if ln.startswith(("FAILED ", "ERROR "))]
    return {"summary": summary, "skipped": skipped, "failed": failed}


def run_pytest(env: dict, extra: list[str] | None = None) -> dict:
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-m", "not slow and not ui", "-rs",
           "--ignore-glob=tests/test_valve*", *(extra or [])]
    t0 = time.time()
    p = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    r = parse_pytest(p.stdout + "\n" + p.stderr)
    r.update(ok=p.returncode == 0, code=p.returncode, seconds=round(time.time() - t0))
    return r


def run_valve(env: dict) -> bool | None:
    tests = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "tests").glob("test_valve*.py"))
    if not tests:
        return None
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-m", "not slow and not ui", *tests],
                       cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode == 0


# ---------------------------------------------------------------- 2. JS 구문
def js_files() -> list[Path]:
    out = []
    for p in sorted(STATIC.rglob("*.js")):
        rel = p.relative_to(STATIC).as_posix()
        if p.name.endswith(".min.js") or rel.startswith("valve/") or "/vendor/" in "/" + rel:
            continue
        out.append(p)
    return out


def run_node_check() -> dict:
    node = shutil.which("node")
    if not node:
        return {"ok": True, "skipped": "node 없음 — JS 구문 검사를 건너뜀", "checked": 0, "failed": []}
    failed = []
    files = js_files()
    for p in files:
        r = subprocess.run([node, "--check", str(p)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode:
            failed.append(f"{p.relative_to(ROOT).as_posix()}: {(r.stderr.strip().splitlines() or ['?'])[-1][:200]}")
    return {"ok": not failed, "checked": len(files), "failed": failed}


# ---------------------------------------------------------------- 3. 서버 스모크
_SMOKE_CODE = r"""
import json, sys
from fastapi.testclient import TestClient
from app.main import app
paths = json.loads(sys.argv[1])
rows = []
with TestClient(app) as c:
    for p in paths:
        try:
            r = c.get(p)
            rows.append({"path": p, "status": r.status_code})
        except Exception as e:
            rows.append({"path": p, "status": 0, "error": str(e)[:200]})
print("SMOKE_JSON " + json.dumps(rows))
"""


def run_smoke(env: dict, paths=SMOKE_PATHS) -> dict:
    """TestClient 스모크 — 자식 프로세스에서 (임시 자료 폴더 · app.main 을 이 프로세스에 싣지 않는다)."""
    p = subprocess.run([sys.executable, "-c", _SMOKE_CODE, json.dumps(list(paths))], cwd=ROOT, env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    line = next((ln for ln in p.stdout.splitlines() if ln.startswith("SMOKE_JSON ")), None)
    if not line:
        tail = (p.stderr.strip().splitlines() or ["?"])[-1][:300]
        return {"ok": False, "pages": [], "failed": [f"서버를 띄우지 못함: {tail}"]}
    rows = json.loads(line[len("SMOKE_JSON "):])
    failed = [f"{r['path']} → {r['status']}" for r in rows if r["status"] != 200]
    return {"ok": not failed, "pages": rows, "failed": failed}


# ---------------------------------------------------------------- 4. 화면 눈 점검
def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_screens(env: dict, shots: Path) -> dict:
    node = shutil.which("node")
    if not SMOKE_JS.exists():
        return {"ok": True, "skipped": "spike/smoke_screens.js 없음 — 화면 점검을 건너뜀"}
    if not node:
        return {"ok": True, "skipped": "node 없음 — 화면 점검을 건너뜀"}
    npm_root = ""
    try:
        npm_root = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    except OSError:
        pass
    nenv = dict(env, NODE_PATH=os.pathsep.join(x for x in (env.get("NODE_PATH", ""), npm_root) if x))
    if subprocess.run([node, "-e", "require('playwright')"], env=nenv, capture_output=True).returncode:
        return {"ok": True, "skipped": "playwright 없음 — 화면 점검을 건너뜀"}
    port = _free_port()
    srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port), "--no-access-log"],
                           cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        t0 = time.time()
        while time.time() - t0 < 90:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=1):
                    break
            except OSError:
                time.sleep(0.5)
        else:
            return {"ok": False, "failed": ["임시 서버가 90초 안에 뜨지 않음"]}
        r = subprocess.run([node, str(SMOKE_JS), f"http://127.0.0.1:{port}", str(shots)], cwd=ROOT, env=nenv,
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
        tail = [ln for ln in (r.stdout + r.stderr).strip().splitlines() if ln][-5:]
        return {"ok": r.returncode == 0, "shots": str(shots), "failed": [] if r.returncode == 0 else tail}
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=10)
        except subprocess.TimeoutExpired:
            srv.kill()


# ---------------------------------------------------------------- 판정
def strict_failures(skipped: list[str]) -> list[str]:
    return [s for s in skipped if any(w in s for w in STRICT_WORDS)]


def judge(steps: dict, strict: bool) -> tuple[bool, list[str], list[str]]:
    failures, skipped = [], []
    for name, r in steps.items():
        if r is None:
            continue
        if isinstance(r.get("skipped"), str):
            skipped.append(f"{name}: {r['skipped']}")
        if not r.get("ok"):
            what = r.get("failed") or [r.get("summary") or "실패"]
            failures.append(f"{name}: " + "; ".join(map(str, what[:5])))
    skipped += (steps.get("pytest") or {}).get("skipped", [])
    if strict:
        need = strict_failures(skipped)
        if need:
            failures.append(f"--strict: 자료가 없어 건너뛴 시험 {len(need)}건 — 예: {need[0]}")
    return not failures, failures, skipped


def main(argv=None) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace")
        except Exception:                                    # noqa: BLE001
            pass
    argv = list(sys.argv[1:] if argv is None else argv)
    strict = "--strict" in argv
    screens = "--no-screens" not in argv
    out = OUT
    if "--out" in argv:
        out = Path(argv[argv.index("--out") + 1])
    head = git_head()
    tmp = Path(tempfile.mkdtemp(prefix="pid-release-"))
    env = dict(os.environ)
    env.update(QUIET_ENV)
    env["PID_DATA_DIR"] = str(tmp / "data")                # 실 자료(app\_data)를 건드리지 않는다
    env["PYTHONUTF8"] = "1"
    steps: dict = {}
    try:
        _say(f"[1/4] 시험 (pytest · valve 제외) — 2분쯤 걸립니다 · HEAD {head}")
        steps["pytest"] = run_pytest(env)
        _say(f"      {steps['pytest']['summary'] or '결과 줄 없음'}")
        valve_ok = run_valve(env)
        _say("[2/4] JS 구문 (node --check)")
        steps["node"] = run_node_check()
        _say(f"      {steps['node'].get('skipped') or str(steps['node']['checked']) + '개 · 실패 ' + str(len(steps['node']['failed']))}")
        _say("[3/4] 서버 주소 스모크 (13곳)")
        steps["smoke"] = run_smoke(env)
        _say(f"      실패 {len(steps['smoke']['failed'])}")
        if screens:
            _say("[4/4] 화면 눈 점검 (spike/smoke_screens.js)")
            steps["screens"] = run_screens(env, ROOT / "out" / "release_smoke")
            _say(f"      {steps['screens'].get('skipped') or ('통과' if steps['screens']['ok'] else '실패')}")
        else:
            steps["screens"] = {"ok": True, "skipped": "--no-screens"}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    ok, failures, skipped = judge(steps, strict)
    res = {"head": head, "ok": ok, "at": dt.datetime.now().isoformat(timespec="seconds"), "strict": strict,
           "steps": steps, "skipped": skipped, "failures": failures, "valve_ok": valve_ok}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    _say(("통과" if ok else "실패") + f" — {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
    for f in failures:
        _say("  ·", f)
    if skipped:
        _say(f"  건너뜀 {len(skipped)}건 (자세히: {out.name} 의 skipped)")
    if valve_ok is False:
        _say("  참고: Valve 시험이 빨갛습니다 (회사 소유 — 판정에는 넣지 않음)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
