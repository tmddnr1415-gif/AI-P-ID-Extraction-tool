"""PID_dev 용 **변경분 꾸러미**를 만든다 (hotfix56 부터).

    python3 spike/pack_delta.py --name hotfix56 --summary "분석을 자식 프로세스로" \
        --readme out/hotfix56/readme_head.txt

왜 누적 꾸러미(`pack_hotfix.py`)가 아닌가 — 개발이 두 곳(이 저장소 · 회사 PC 의 PID_dev)에서
일어난다.  누적 꾸러미를 풀면 회사 Claude 가 고친 파일(시험 26건 · lan_check · start.bat …)이
옛것으로 돌아간다.  그래서 이 꾸러미는:

  · **기준 커밋 이후 바뀐 파일만** 담는다 (`git diff --name-only <base> HEAD`, 커밋된 것만).
  · 파일마다 **기준판 해시(base)와 새 해시(new)** 를 manifest 에 적는다.  적용기
    (`apply_delta.py`, 꾸러미 안)가 PID_dev 의 파일이 base 와 같을 때만 덮고, 다르면(회사에서
    고침) 덮지 않고 `.new` 로 옆에 둔다.
  · 기준 커밋은 직전 꾸러미가 남긴 `out/PID_dev_delta_base.txt` (처음은 r3 소스 = 97a8732).
  · `app/_update.json`(첫 화면 오른쪽 아래 딱지)만은 늘 덮는다.
  · `out/` · `data/` · `app/_data/` 는 넣지 않는다.

만든 뒤 **기준판 트리에 실제로 적용해 HEAD 와 바이트가 같은지** 센다 (다른 파일 0 이어야 한다).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_FILE = ROOT / "out" / "PID_dev_delta_base.txt"
FIRST_BASE = "97a8732"            # out/PID_source_2026-10-08_r3.zip 을 만든 커밋
SKIP = ("out/", "data/", "app/_data/")
STAMP = "app/_update.json"
BAT = ("@echo off\r\n"
       "rem Apply this delta to C:\\Claude\\PID_dev (never to the operating folder).\r\n"
       "cd /d \"%~dp0\"\r\n"
       "set PYTHONUTF8=1\r\n"
       "set \"PY=C:\\Claude\\PID_dev\\.venv\\Scripts\\python.exe\"\r\n"
       "if not exist \"%PY%\" set \"PY=python\"\r\n"
       "\"%PY%\" apply_delta.py C:\\Claude\\PID_dev %*\r\n"
       "pause\r\n")


def git(*args, binary=False):
    out = subprocess.check_output(["git", *args], cwd=ROOT)
    return out if binary else out.decode("utf-8").strip()


def blob(rev: str, path: str) -> bytes | None:
    try:
        return subprocess.check_output(["git", "show", f"{rev}:{path}"], cwd=ROOT,
                                       stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return None


def h(b: bytes | None) -> str | None:
    return hashlib.sha256(b).hexdigest() if b is not None else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--summary", default="")
    ap.add_argument("--readme", default="")
    ap.add_argument("--base", default="")
    a = ap.parse_args()
    if git("status", "--porcelain", "--untracked-files=no"):
        print("커밋하지 않은 변경이 있습니다 — 커밋한 뒤 만드세요 (꾸러미는 HEAD 를 담는다)")
        return 1
    base = a.base or (BASE_FILE.read_text().strip() if BASE_FILE.exists() else FIRST_BASE)
    head = git("rev-parse", "--short", "HEAD")
    paths = [p for p in git("-c", "core.quotepath=off", "diff", "--name-only", base, "HEAD").splitlines()
             if p and not p.startswith(SKIP)]
    deleted = [p for p in paths if blob("HEAD", p) is None]
    paths = [p for p in paths if p not in deleted]
    day = dt.date.today().isoformat()
    zname = f"PID_dev_{a.name}_{day}.zip"

    # 딱지 — 이 꾸러미가 적용됐다는 표시 (첫 화면 오른쪽 아래).  HEAD 에 커밋하지 않고 꾸러미에만.
    m = "".join(ch for ch in a.name if ch.isdigit())
    stamp = {"name": a.name, "rev": int(m) if m else None, "zip": zname,
             "created_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
             "base_commit": head, "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
             "kind": "delta", "delta_base": base}
    stamp_bytes = (json.dumps(stamp, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    files = []
    for p in paths:
        if p == STAMP:
            continue
        # 기준과 HEAD 사이에 저장소가 거친 판 전부 — 앞 꾸러미를 이미 적용한 PID_dev 도 "우리가 보낸 판"
        # 으로 알아보고 덮는다 (회사에서 고친 판만 충돌).  그래서 꾸러미를 건너뛰어도, 차례로 적용해도 된다.
        known = []
        for c in git("log", "--format=%H", f"{base}..HEAD", "--", p).splitlines():
            b = blob(c, p)
            if b is not None and h(b) not in known:
                known.append(h(b))
        files.append({"path": p, "base_sha256": h(blob(base, p)), "new_sha256": h(blob("HEAD", p)),
                      "known_sha256": known})
    files.append({"path": STAMP, "base_sha256": h(blob(base, STAMP)), "new_sha256": h(stamp_bytes),
                  "always": True})
    manifest = {"name": a.name, "summary": a.summary, "base_commit": base, "head_commit": head,
                "created_at": stamp["created_at"], "files": files, "deleted_upstream": deleted}

    readme = (Path(a.readme).read_text(encoding="utf-8") if a.readme else "") + (
        f"\n\n----\n{a.name} 변경분 꾸러미 · 기준 {base} → {head} · 파일 {len(files)}개\n"
        "적용: 이 폴더의 apply_to_PID_dev.bat 더블클릭 (PID_dev 에만 적용 · 운영 폴더는 거부)\n"
        "      먼저 보기만: apply_to_PID_dev.bat --dry-run\n"
        "충돌(회사에서 고친 파일)은 덮지 않고 <파일>.<이름>.new 로 옆에 둡니다.\n"
        "원본 백업: C:\\Claude\\PID_dev\\backup\\<이름>_<시각>\\\n\n"
        + "\n".join(f"  {f['path']}" for f in files) + "\n")
    out = ROOT / "out" / zname
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            data = stamp_bytes if f["path"] == STAMP else blob("HEAD", f["path"])
            z.writestr(f"files/{f['path']}", data)
        z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        z.writestr("apply_delta.py", (ROOT / "spike" / "apply_delta.py").read_bytes())
        z.writestr("apply_to_PID_dev.bat", BAT.encode("ascii"))
        z.writestr("1_먼저읽기.txt", readme.encode("utf-8"))

    # 검증 — 기준판 트리를 만들고 실제로 적용해 HEAD 와 같은지 센다.
    sys.path.insert(0, str(ROOT / "spike"))
    import apply_delta
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        tree, pkg = td / "PID_dev", td / "pkg"
        tree.mkdir()
        tar = subprocess.check_output(["git", "archive", base], cwd=ROOT)
        import io
        import tarfile
        tarfile.open(fileobj=io.BytesIO(tar)).extractall(tree)
        zipfile.ZipFile(out).extractall(pkg)
        steps, _ = apply_delta.apply(tree, pkg, json.loads((pkg / "manifest.json").read_text("utf-8")))
        bad = [s["path"] for s in steps if s["action"] in ("conflict", "refused")]
        diff = [f["path"] for f in files if f["path"] != STAMP
                and h((tree / f["path"]).read_bytes()) != h(blob("HEAD", f["path"]))]
    print(f"{out.relative_to(ROOT)}  {out.stat().st_size:,} bytes  · 파일 {len(files)} · 기준 {base} → {head}")
    print(f"검증: 기준판에 적용 → 충돌 {len(bad)} · HEAD 와 다른 파일 {len(diff)}")
    if deleted:
        print(f"⚠ 저장소에서 지운 파일 {len(deleted)}개는 꾸러미가 지우지 않습니다: {deleted}")
    if bad or diff:
        print(bad, diff)
        return 1
    BASE_FILE.write_text(head + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
