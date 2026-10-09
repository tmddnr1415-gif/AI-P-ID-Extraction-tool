"""PID_dev delta update applier (hotfix56).

Usage (Windows, in the unpacked package folder):

    C:\\Claude\\PID_dev\\.venv\\Scripts\\python apply_delta.py C:\\Claude\\PID_dev
    ... apply_delta.py C:\\Claude\\PID_dev --dry-run     (show only, change nothing)

Per file in manifest.json:
  * target file == the version this package was made against (base),
    or any version an earlier package of ours delivered (known)      -> overwrite
  * target file == the new version already                           -> skip
  * file is new and absent in target                                 -> create
  * anything else (someone edited it on the company PC)              -> CONFLICT:
        the target is NOT touched; the new version is written next to it as
        <file>.<package>.new so the company Claude can merge the two.
Files the repository removed after an earlier package delivered them ("remove": true):
  * target file == a version we delivered (known)                   -> remove (backed up)
  * absent                                                           -> same
  * anything else (edited on the company PC)                         -> keep, reported
Originals are copied to <target>\\backup\\<package>_<time>\\ before overwriting.
Never touches app\\_data, data, .venv, logs.  Refuses the operating folder
(a folder named PID) unless --ops is given.  Exit code 0 = applied, 2 = conflicts.

hotfix60 - the operating folder (C:\\Claude\\PID, the server the dashboard shows):
    apply_delta.py C:\\Claude\\PID --ops --runtime --all-or-nothing
  --runtime         only the files the server runs (app/...); tests, docs, spike stay in PID_dev
  --all-or-nothing  if ANY file would conflict, change nothing at all (exit 3) - a running
                    server must never get half of an update (new app.js with old index.html)
    apply_delta.py C:\\Claude\\PID --ops --restore
  puts back the files this package replaced (from backup\\<package>_<time>\\, newest) and
  removes the files it created.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
NEVER = ("app/_data/", "data/", ".venv/", "logs/", "backup/")


def sha(p: Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return None


RUNTIME = ("app/",)


def plan(target: Path, manifest: dict, runtime_only: bool = False) -> list[dict]:
    out = []
    for f in manifest["files"]:
        rel = f["path"]
        if runtime_only and not rel.startswith(RUNTIME):
            continue
        if rel.startswith(NEVER) or ".." in Path(rel).parts:
            out.append({**f, "action": "refused"})
            continue
        now = sha(target / rel)
        if f.get("remove"):
            act = ("same" if now is None
                   else "remove" if (now in (f.get("known_sha256") or ()) or now == f.get("base_sha256"))
                   else "kept")
            out.append({**f, "now_sha256": now, "action": act})
            continue
        if now == f["new_sha256"]:
            act = "same"
        elif f.get("always") or now == f["base_sha256"] or now in (f.get("known_sha256") or ()):
            act = "create" if now is None else "overwrite"
        else:
            act = "conflict"
        out.append({**f, "now_sha256": now, "action": act})
    return out


def apply(target: Path, pkg: Path, manifest: dict, dry: bool = False, runtime_only: bool = False,
          all_or_nothing: bool = False) -> tuple[list[dict], Path | None]:
    steps = plan(target, manifest, runtime_only)
    name = manifest["name"]
    backup = None
    if all_or_nothing and any(s["action"] in ("conflict", "kept") for s in steps):
        for s in steps:
            s["aborted"] = True
        return steps, None                       # 한 파일도 안 바꾼다
    if not dry:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        created = [s["path"] for s in steps if s["action"] == "create"]
        if created:
            backup = target / "backup" / f"{name}_{stamp}"
            backup.mkdir(parents=True, exist_ok=True)
            (backup / "_created.txt").write_text("\n".join(created) + "\n", encoding="utf-8")
        for s in steps:
            src = pkg / "files" / s["path"]
            dst = target / s["path"]
            if s["action"] == "remove":
                backup = backup or (target / "backup" / f"{name}_{stamp}")
                b = backup / s["path"]
                b.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dst, b)
                dst.unlink()
            elif s["action"] in ("overwrite", "create"):
                if s["action"] == "overwrite":
                    backup = backup or (target / "backup" / f"{name}_{stamp}")
                    b = backup / s["path"]
                    b.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(dst, b)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
            elif s["action"] == "conflict":
                side = dst.with_name(dst.name + f".{name}.new")
                shutil.copyfile(src, side)
                s["new_copy"] = str(side)
        lines = [f"{name} applied {time.strftime('%Y-%m-%d %H:%M:%S')} to {target}"]
        lines += [f"{s['action']:9s} {s['path']}" for s in steps]
        (target / f"delta_{name}_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return steps, backup


def restore(target: Path, name: str) -> tuple[Path | None, int, int]:
    """이 꾸러미가 남긴 가장 최근 백업으로 되돌린다 — 덮은 파일은 원본으로, 만든 파일은 지운다."""
    root = target / "backup"
    cands = sorted(root.glob(f"{name}_*")) if root.is_dir() else []
    if not cands:
        return None, 0, 0
    b = cands[-1]
    back = gone = 0
    for f in b.rglob("*"):
        if f.is_file() and f.name != "_created.txt":
            rel = f.relative_to(b)
            dst = target / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)
            back += 1
    lst = b / "_created.txt"
    if lst.is_file():
        for rel in lst.read_text(encoding="utf-8").split():
            if rel.startswith(NEVER) or ".." in Path(rel).parts:
                continue
            p = target / rel
            if p.is_file():
                p.unlink()
                gone += 1
    return b, back, gone


def main(argv=None) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace")
        except Exception:                                   # noqa: BLE001
            pass
    argv = list(sys.argv[1:] if argv is None else argv)
    dry = "--dry-run" in argv
    ops = "--ops" in argv
    runtime = "--runtime" in argv
    aon = "--all-or-nothing" in argv
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        return 1
    target = Path(args[0]).resolve()
    manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
    if not (target / "app" / "main.py").is_file():
        print(f"[중단] {target} 에 app\\main.py 가 없습니다. PID_dev 폴더를 지정하세요.")
        return 1
    if target.name.lower() == "pid" and not ops:
        print(f"[중단] {target} 는 운영 폴더로 보입니다. 이 꾸러미는 PID_dev 에만 적용합니다.\n"
              "       운영 반영은 회사 Claude 에게 '운영에 반영해' 로 하세요.")
        return 1
    if ops and (target / "PID_Extract.exe").is_file():
        print(f"[중단] {target} 에 PID_Extract.exe 가 있습니다 — 서비스가 exe 로 돌아 소스 업데이트가 반영되지 않습니다.\n"
              "       exe 를 다시 빌드해야 합니다 (build.bat).  아무 파일도 바꾸지 않았습니다.")
        return 4
    if "--restore" in argv:
        b, back, gone = restore(target, manifest["name"])
        if b is None:
            print(f"[되돌릴 것 없음] {target}\\backup 에 {manifest['name']} 백업이 없습니다.")
            return 1
        print(f"되돌림: {b} 의 원본 {back}개를 다시 놓고, 이 꾸러미가 만든 파일 {gone}개를 지웠습니다.")
        return 0
    steps, backup = apply(target, HERE, manifest, dry, runtime_only=runtime, all_or_nothing=aon)
    print(f"{manifest['name']}  ({manifest.get('summary', '')})")
    if steps and steps[0].get("aborted"):
        bad = [s for s in steps if s["action"] in ("conflict", "kept")]
        print(f"대상: {target}\n")
        print(f"[중단 - 아무 파일도 바꾸지 않았습니다] 이 폴더에서 따로 고친 파일 {len(bad)}개가 있습니다:")
        for s in bad:
            print(f"    {s['path']}")
        print("\n돌고 있는 서버에 업데이트를 반쪽만 얹지 않으려고 멈췄습니다.  서버는 그대로 돕니다.")
        print("회사 Claude 가 돌아오면: 'PID 운영 폴더에 hotfix 적용이 충돌로 멈췄다 - PID_dev 와 맞춰 반영해줘'")
        return 3
    print(f"대상: {target}{'   [미리보기 - 아무것도 바꾸지 않음]' if dry else ''}\n")
    words = {"overwrite": "덮어씀", "create": "새로 만듦", "same": "이미 같음",
             "conflict": "충돌 - 안 덮음", "refused": "거부(보호 폴더)",
             "remove": "지움 (저장소에서 없앤 파일)", "kept": "안 지움 - 회사에서 고친 파일"}
    for s in steps:
        tail = f"   -> 새 버전: {Path(s['new_copy']).name}" if s.get("new_copy") else ""
        print(f"  [{words[s['action']]}] {s['path']}{tail}")
    conflicts = [s for s in steps if s["action"] == "conflict"]
    if backup:
        print(f"\n원본 백업: {backup}")
    if conflicts:
        print(f"\n충돌 {len(conflicts)}개: 회사에서 고친 파일이라 덮지 않았습니다.")
        print("회사 Claude 에게: '충돌 파일(.new)과 지금 파일을 비교해 둘 다 살려서 합쳐줘'")
        return 2
    if not dry:
        print("\n적용 끝. 다음: 회사 Claude 에게 변경 확인 + 시험 + 8001 미리보기를 맡기세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
