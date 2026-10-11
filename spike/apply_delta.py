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
  * a company-edited file with a merge recipe (MERGERS, e.g. app/lan_check.py)  -> MERGE:
        the company version is kept as is and only what we added is inserted;
        if the recipe cannot find its place it stays a CONFLICT.
Originals are copied to <target>\\backup\\<package>_<time>\\ before overwriting.
Never touches app\\_data, data, .venv, logs.  Refuses the operating folder
(a folder named PID) unless --ops is given.  Exit code 0 = applied, 2 = conflicts.

hotfix60 - the operating folder (C:\\Claude\\PID, the server the dashboard shows):
    apply_delta.py C:\\Claude\\PID --ops --runtime --all-or-nothing
  --runtime         only the files the server runs (app/..., config/...); tests, docs, spike stay in PID_dev
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


# 서버가 실행 중에 읽는 것 — 코드(app/)와 설정(config/).  hotfix89 전에는 app/ 만이라
# hotfix83 의 방침(config policy: PSV 제외 · 제어실 기능 제외)이 운영 서버에 닿지 않았다.
RUNTIME = ("app/", "config/")


# ── 회사에서 고친 파일을 합치는 조리법 (hotfix89b) ─────────────────────────────
# 회사 판은 한 글자도 지우지 않고, 우리가 기준판 뒤에 **더한 것만** 끼워 넣는다.
# 조리법이 끼울 자리를 못 찾으면 None — 예전처럼 충돌로 남는다 (지어서 합치지 않는다).
# 결과는 반드시 컴파일되어야 하고 필요한 이름이 있어야 한다.  이미 다 들어 있으면 원문 그대로.

_LAN_ADD = """LOG_LIMIT = 20 * 1024 * 1024
LOG_KEEP = 3


def tail_bytes(path: Path, n: int) -> bytes:
    \"\"\"Read only the LAST n bytes (hotfix74 - server.log can grow to GB).\"\"\"
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - n))
        return f.read()


def rotate(path: Path | None = None, limit: int = LOG_LIMIT, keep: int = LOG_KEEP) -> bool:
    \"\"\"Move server.log to server.log.1 ... .keep when it is over limit (hotfix74).
    Called only right before the server starts, when nobody holds the file open.\"\"\"
    path = path or ROOT / "logs" / "server.log"
    try:
        if not path.exists() or path.stat().st_size <= limit:
            return False
        oldest = path.with_name(f"{path.name}.{keep}")
        if oldest.exists():
            oldest.unlink()
        for i in range(keep - 1, 0, -1):
            src = path.with_name(f"{path.name}.{i}")
            if src.exists():
                src.replace(path.with_name(f"{path.name}.{i + 1}"))
        path.replace(path.with_name(f"{path.name}.1"))
        return True
    except OSError:
        return False


"""


def _merge_lan_check(text: str) -> str | None:
    import re
    nl = "\r\n" if "\r\n" in text else "\n"
    t = text.replace("\r\n", "\n")
    if "def tail_bytes(" not in t or "def rotate(" not in t:
        if "def tail_bytes(" in t or "def rotate(" in t or "LOG_LIMIT" in t:
            return None                                   # 반쯤 있다 — 손으로 합칠 일
        if t.count("\ndef preflight(") != 1 or "ROOT" not in t or "Path" not in t:
            return None
        t = t.replace("\ndef preflight(", "\n" + _LAN_ADD + "def preflight(", 1)
    m = re.search(r"\ndef preflight\([^\n]*\n(.*?)(?=\ndef |\Z)", t, re.S)
    if m and "rotate(" not in m.group(1):
        body = m.group(1)
        hit = re.search(r"^( +)if not listening\(port\):\n", body, re.M)
        if hit:
            ind = hit.group(1)
            add = f"{ind}    rotate()                       # hotfix74 - before start, nobody holds the log\n"
            body2 = body[:hit.end()] + add + body[hit.end():]
            t = t[:m.start(1)] + body2 + t[m.end(1):]
    t = t.replace("path.read_bytes()[-64_000:]", "tail_bytes(path, 64_000)")
    try:
        compile(t, "lan_check.py", "exec")
    except SyntaxError:
        return None
    if "def tail_bytes(" not in t or "def rotate(" not in t:
        return None
    return t.replace("\n", nl)


MERGERS = {"app/lan_check.py": _merge_lan_check}


def merged_text(target: Path, rel: str) -> str | None:
    """조리법이 있는 파일이면 합친 글을, 없거나 못 합치면 None."""
    fn = MERGERS.get(rel)
    if fn is None:
        return None
    try:
        text = (target / rel).read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return fn(text)


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
            m = merged_text(target, rel)
            if m is not None:
                cur = (target / rel).read_bytes().decode("utf-8")
                act = "same_merged" if m == cur else "merge"
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
            elif s["action"] == "merge":
                backup = backup or (target / "backup" / f"{name}_{stamp}")
                b = backup / s["path"]
                b.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dst, b)
                text = merged_text(target, s["path"])
                dst.write_bytes(text.encode("utf-8"))
                for side in dst.parent.glob(dst.name + ".hotfix*.new"):
                    side.unlink()                 # 앞선 적용들이 남긴 .new — 이제 합쳤다
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
             "remove": "지움 (저장소에서 없앤 파일)", "kept": "안 지움 - 회사에서 고친 파일",
             "merge": "합침 - 회사 판 + 이번 추가분", "same_merged": "이미 합쳐짐"}
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
    if not dry and ops:
        print("\n운영 폴더에 얹었습니다 — 서버를 다시 띄워야 새 코드가 돕니다 (이어서 묻습니다).")
    elif not dry:
        print("\n적용 끝. 다음: 회사 Claude 에게 변경 확인 + 시험 + 8001 미리보기를 맡기세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
