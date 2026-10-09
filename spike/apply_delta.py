"""PID_dev delta update applier (hotfix56).

Usage (Windows, in the unpacked package folder):

    C:\\Claude\\PID_dev\\.venv\\Scripts\\python apply_delta.py C:\\Claude\\PID_dev
    ... apply_delta.py C:\\Claude\\PID_dev --dry-run     (show only, change nothing)

Per file in manifest.json:
  * target file == the version this package was made against (base)  -> overwrite
  * target file == the new version already                           -> skip
  * file is new and absent in target                                 -> create
  * anything else (someone edited it on the company PC)              -> CONFLICT:
        the target is NOT touched; the new version is written next to it as
        <file>.<package>.new so the company Claude can merge the two.
Originals are copied to <target>\\backup\\<package>_<time>\\ before overwriting.
Never touches app\\_data, data, .venv, logs.  Refuses the operating folder
(a folder named PID) unless --ops is given.  Exit code 0 = applied, 2 = conflicts.
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


def plan(target: Path, manifest: dict) -> list[dict]:
    out = []
    for f in manifest["files"]:
        rel = f["path"]
        if rel.startswith(NEVER) or ".." in Path(rel).parts:
            out.append({**f, "action": "refused"})
            continue
        now = sha(target / rel)
        if now == f["new_sha256"]:
            act = "same"
        elif f.get("always") or now == f["base_sha256"]:
            act = "create" if now is None else "overwrite"
        else:
            act = "conflict"
        out.append({**f, "now_sha256": now, "action": act})
    return out


def apply(target: Path, pkg: Path, manifest: dict, dry: bool = False) -> tuple[list[dict], Path | None]:
    steps = plan(target, manifest)
    name = manifest["name"]
    backup = None
    if not dry:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        for s in steps:
            src = pkg / "files" / s["path"]
            dst = target / s["path"]
            if s["action"] in ("overwrite", "create"):
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


def main(argv=None) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace")
        except Exception:                                   # noqa: BLE001
            pass
    argv = list(sys.argv[1:] if argv is None else argv)
    dry = "--dry-run" in argv
    ops = "--ops" in argv
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
    steps, backup = apply(target, HERE, manifest, dry)
    print(f"{manifest['name']}  ({manifest.get('summary', '')})")
    print(f"대상: {target}{'   [미리보기 - 아무것도 바꾸지 않음]' if dry else ''}\n")
    words = {"overwrite": "덮어씀", "create": "새로 만듦", "same": "이미 같음",
             "conflict": "충돌 - 안 덮음", "refused": "거부(보호 폴더)"}
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
