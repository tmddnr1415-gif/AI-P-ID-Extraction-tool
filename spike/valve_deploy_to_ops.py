"""회사 PC: 개발 폴더에서 고친 Valve 분석 툴을 운영 서버에 올린다 (2026-11-01 사용자 결정 — Valve 는 회사 PC 가 개발).

    C:\\Claude\\PID_dev\\.venv\\Scripts\\python spike\\valve_deploy_to_ops.py            (= valve_deploy_to_ops.bat)
    ... valve_deploy_to_ops.py --rollback                                               (= valve_rollback_ops.bat)

하는 일 (표준 라이브러리만):
  1. 개발 폴더에서 Valve 시험(pytest -k valve)을 돌린다 — 하나라도 실패하면 아무것도 바꾸지 않는다.
  2. 개발 ↔ 운영의 Valve 파일(app/valve · app/static/valve)을 비교해 바뀜 · 새 파일 · 없앨 파일을 보여 주고 묻는다.
  3. 운영 폴더의 해당 파일을 backup\\valve_<시각>\\ 에 먼저 복사한 뒤 바꾼다.  Valve 밖의 파일은 건드리지 않는다.
  4. 8000 서버만 다시 띄운다 (restart_pid_server.py — 대시보드 8080 은 그대로).
되돌리기: --rollback = 가장 최근 backup\\valve_* 를 운영 폴더에 되돌리고 서버 재시작.
"""
from __future__ import annotations

import argparse
import datetime as dt
import filecmp
import json
import shutil
import subprocess
import sys
from pathlib import Path

OWNED = ("app/valve", "app/static/valve")                 # 운영 서버가 실제로 돌리는 Valve 파일
SKIP_PARTS = {"__pycache__"}


def files_under(root: Path) -> dict[str, Path]:
    out = {}
    for d in OWNED:
        base = root / d
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_file() and not (SKIP_PARTS & set(p.parts)) and p.suffix not in (".pyc",):
                out[p.relative_to(root).as_posix()] = p
    return out


def plan(dev: Path, ops: Path) -> dict:
    D, O = files_under(dev), files_under(ops)
    return {"add": sorted(k for k in D if k not in O),
            "change": sorted(k for k in D if k in O and not filecmp.cmp(D[k], O[k], shallow=False)),
            "remove": sorted(k for k in O if k not in D)}


def run_tests(dev: Path) -> bool:
    py = dev / ".venv" / "Scripts" / "python.exe"
    py = str(py) if py.exists() else sys.executable
    print("1) Valve 시험을 돌립니다 (개발 폴더) …")
    r = subprocess.run([py, "-m", "pytest", "-q", "tests", "-k", "valve"], cwd=dev)
    return r.returncode == 0


def restart(ops: Path, port: int, here: Path) -> None:
    tool = here / "restart_pid_server.py"
    if not tool.exists():
        print(f"   (restart_pid_server.py 가 없어 서버를 직접 다시 켜세요 — 포트 {port})")
        return
    py = ops / ".venv" / "Scripts" / "python.exe"
    subprocess.run([str(py) if py.exists() else sys.executable, str(tool), str(port)], cwd=ops)


def deploy(dev: Path, ops: Path, port: int, yes: bool, skip_tests: bool, here: Path) -> int:
    if not (dev / "app" / "valve").exists() or not (ops / "app").exists():
        print(f"폴더를 찾지 못했습니다: 개발 {dev} · 운영 {ops}")
        return 2
    if not skip_tests and not run_tests(dev):
        print("시험이 실패해 운영에 올리지 않았습니다. 먼저 고치세요.")
        return 1
    P = plan(dev, ops)
    n = sum(len(v) for v in P.values())
    print(f"2) 운영에 반영할 Valve 파일: 바뀜 {len(P['change'])} · 새 파일 {len(P['add'])} · 없앨 파일 {len(P['remove'])}")
    for k in ("change", "add", "remove"):
        for f in P[k][:30]:
            print(f"   {dict(change='바뀜', add='새', remove='없앰')[k]:3s} {f}")
    if not n:
        print("운영과 같습니다 — 할 일이 없습니다.")
        return 0
    if not yes and input("운영 서버에 올릴까요? (y/N) ").strip().lower() != "y":
        print("취소했습니다.")
        return 0
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    bk = ops / "backup" / f"valve_{stamp}"
    for f in P["change"] + P["remove"]:                    # 바꾸거나 지울 운영 파일을 먼저 보관
        (bk / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ops / f, bk / f)
    (bk.mkdir(parents=True, exist_ok=True))
    (bk / "_plan.json").write_text(json.dumps(P, ensure_ascii=False, indent=1), encoding="utf-8")
    for f in P["change"] + P["add"]:
        (ops / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dev / f, ops / f)
    for f in P["remove"]:
        (ops / f).unlink(missing_ok=True)
    print(f"3) 반영했습니다. 되돌릴 때: valve_rollback_ops.bat  (보관: {bk})")
    print("4) 8000 서버를 다시 띄웁니다 …")
    restart(ops, port, here)
    return 0


def rollback(ops: Path, port: int, here: Path) -> int:
    bks = sorted((ops / "backup").glob("valve_*")) if (ops / "backup").exists() else []
    if not bks:
        print("되돌릴 보관본이 없습니다.")
        return 1
    bk = bks[-1]
    P = json.loads((bk / "_plan.json").read_text(encoding="utf-8"))
    for f in P["change"] + P["remove"]:
        (ops / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bk / f, ops / f)
    for f in P["add"]:                                      # 그때 새로 넣었던 파일은 뺀다
        (ops / f).unlink(missing_ok=True)
    bk.rename(bk.with_name(bk.name + "_rolledback"))
    print(f"{bk.name} 로 되돌렸습니다. 8000 서버를 다시 띄웁니다 …")
    restart(ops, port, here)
    return 0


def main() -> int:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", default=str(here.parent))
    ap.add_argument("--ops", default=r"C:\Claude\PID")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--skip-tests", action="store_true")
    ap.add_argument("--rollback", action="store_true")
    a = ap.parse_args()
    if a.rollback:
        return rollback(Path(a.ops), a.port, here)
    return deploy(Path(a.dev), Path(a.ops), a.port, a.yes, a.skip_tests, here)


if __name__ == "__main__":
    sys.exit(main())
