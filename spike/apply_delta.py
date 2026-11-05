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

hotfix132 - safety around the copy loop:
  * if a copy fails half way (file locked, disk full ...) everything written so far is
    put back from the backup at once and the exit code is 5 - a server never keeps half
    an update.  The backup folder records the hash of every byte written (_applied.json).
  * --restore skips a file that was edited AFTER the update (hash differs from what we
    wrote) and reports it; --force overrides.  --restore --dry-run only shows.  --yes
    answers the question.
  * running inside the zip (no files\\ folder) is refused with a plain sentence.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
NEVER = ("app/_data/", "data/", ".venv/", "logs/", "backup/")
APPLIED = "_applied.json"            # hotfix132 — 백업 폴더에: {상대경로: 적용 때 실제로 쓴 바이트의 해시}
EXIT_ROLLED_BACK = 5


class ApplyFailed(OSError):
    """hotfix132 — 복사 도중 실패해 원래대로 되돌렸다.  rel · 원인 · 되돌림 여부를 든다."""

    def __init__(self, rel: str, cause: BaseException, rolled_back: bool):
        super().__init__(str(cause))
        self.rel, self.cause, self.rolled_back = rel, cause, rolled_back


def _why(exc: BaseException) -> str:
    """hotfix132 — OSError 를 계장 엔지니어가 읽는 한 줄로."""
    if isinstance(exc, PermissionError):
        return "권한이 없거나 다른 프로그램이 그 파일을 쓰고 있습니다 (서버·편집기를 닫고 다시 하세요)"
    if isinstance(exc, FileNotFoundError):
        return "파일이나 폴더를 찾을 수 없습니다"
    if getattr(exc, "errno", None) == 28:
        return "디스크가 가득 찼습니다"
    return str(exc) or type(exc).__name__


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
        applied: dict[str, str] = {}             # hotfix132 — 실제로 쓴 바이트의 해시 (merge 는 합친 글의 해시)
        failed: ApplyFailed | None = None

        def _note(rel: str, dst: Path) -> None:
            applied[rel] = sha(dst) or ""
            if backup is not None:
                backup.mkdir(parents=True, exist_ok=True)
                (backup / APPLIED).write_text(json.dumps(applied, indent=1), encoding="utf-8")

        try:
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
                    _note(s["path"], dst)
                elif s["action"] == "merge":
                    backup = backup or (target / "backup" / f"{name}_{stamp}")
                    b = backup / s["path"]
                    b.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(dst, b)
                    text = merged_text(target, s["path"])
                    dst.write_bytes(text.encode("utf-8"))
                    _note(s["path"], dst)
                    for side in dst.parent.glob(dst.name + ".hotfix*.new"):
                        side.unlink()                 # 앞선 적용들이 남긴 .new — 이제 합쳤다
                elif s["action"] == "conflict":
                    side = dst.with_name(dst.name + f".{name}.new")
                    shutil.copyfile(src, side)
                    s["new_copy"] = str(side)
        except OSError as exc:
            # hotfix132 — 반쪽 업데이트를 남기지 않는다: 방금 만든 백업으로 바로 되돌린다
            rel = s["path"]
            rolled = False
            if backup is not None and backup.is_dir():
                try:
                    restore(target, name, force=True, quiet=True)
                    rolled = True
                except OSError:
                    rolled = False
            failed = ApplyFailed(rel, exc, rolled)
        finally:
            lines = [f"{name} applied {time.strftime('%Y-%m-%d %H:%M:%S')} to {target}"]
            if failed is not None:
                lines[0] = (f"{name} FAILED {time.strftime('%Y-%m-%d %H:%M:%S')} at {failed.rel}"
                            f" ({_why(failed.cause)}) - "
                            + ("rolled back" if failed.rolled_back else "nothing to roll back"))
            lines += [f"{s['action']:9s} {s['path']}" for s in steps]
            try:
                (target / f"delta_{name}_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
            except OSError:
                pass
        if failed is not None:
            raise failed
    return steps, backup


def restore(target: Path, name: str, *, force: bool = False, dry: bool = False,
            quiet: bool = False) -> tuple[Path | None, int, int]:
    """이 꾸러미가 남긴 가장 최근 백업으로 되돌린다 — 덮은 파일은 원본으로, 만든 파일은 지운다.

    hotfix132 — 백업에 `_applied.json`(적용 때 쓴 바이트의 해시)이 있으면 파일마다 본다:
    지금 해시 == 적용 때 해시 → 되돌림 · 이미 백업본과 같음 → 조용히 넘김 · 둘 다 아님(그 뒤에 누가
    고침) → '[안 되돌림 - 그 뒤에 고친 파일]' 로 보고만 (force 면 덮음).  옛 백업(기록 없음)은 전처럼 덮는다.
    dry 면 세기만 하고 바꾸지 않는다.  반환은 (백업 폴더, 되돌린 수, 지운 수) 그대로.
    """
    root = target / "backup"
    cands = sorted(root.glob(f"{name}_*")) if root.is_dir() else []
    if not cands:
        return None, 0, 0
    b = cands[-1]
    applied: dict | None = None
    try:
        applied = json.loads((b / APPLIED).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        applied = None

    def _ours(rel: str, cur: str | None) -> bool:
        """지금 파일이 우리가 쓴 그대로인가 (기록이 없는 옛 백업은 그렇다고 본다)."""
        return force or applied is None or rel not in applied or applied.get(rel) == cur

    back = gone = 0
    for f in sorted(b.rglob("*")):
        if not f.is_file() or f.name in ("_created.txt", APPLIED):
            continue
        rel = f.relative_to(b).as_posix()
        dst = target / rel
        cur = sha(dst)
        if cur is not None and cur == sha(f):
            continue                                   # 이미 원본 그대로
        if not _ours(rel, cur):
            if not quiet:
                print(f"  [안 되돌림 - 그 뒤에 고친 파일] {rel}   (--force 면 덮습니다)")
            continue
        if not dry:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)
        back += 1
    lst = b / "_created.txt"
    if lst.is_file():
        for rel in lst.read_text(encoding="utf-8").split():
            if rel.startswith(NEVER) or ".." in Path(rel).parts:
                continue
            p = target / rel
            if not p.is_file():
                continue
            if not _ours(rel, sha(p)):
                if not quiet:
                    print(f"  [안 지움 - 그 뒤에 고친 파일] {rel}   (--force 면 지웁니다)")
                continue
            if not dry:
                p.unlink()
            gone += 1
    return b, back, gone


def _package_is_unpacked(manifest_path: Path) -> bool:
    """hotfix132 — zip 안에서 더블클릭하면 files\\ 가 없다 (manifest 에 실을 파일이 있을 때만 요구)."""
    if not manifest_path.is_file():
        return False
    try:
        man = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    needs_files = any(not f.get("remove") for f in man.get("files") or [])
    return (manifest_path.parent / "files").is_dir() or not needs_files


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
    force = "--force" in argv
    yes = "--yes" in argv or "-y" in argv
    args = [a for a in argv if a and not a.startswith("--") and a != "-y"]
    if len(args) != 1:
        print(__doc__)
        return 1
    target = Path(args[0]).resolve()
    if not _package_is_unpacked(HERE / "manifest.json"):
        print("[중단] 이 폴더에 꾸러미 파일(manifest.json · files 폴더)이 없습니다.\n"
              "       zip 을 먼저 전부 푼 뒤, 푼 폴더 안의 bat 를 실행하세요 (zip 안에서 바로 실행하면 안 됩니다).")
        return 1
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
        # hotfix132 — 먼저 세어 보여 주고(미리보기), 묻고, 그 다음에 되돌린다.  --dry-run 은 세기만.
        b, back, gone = restore(target, manifest["name"], force=force, dry=True)
        if b is None:
            print(f"[되돌릴 것 없음] {target}\\backup 에 {manifest['name']} 백업이 없습니다.")
            return 1
        print(f"백업: {b}\n되돌릴 파일 {back}개 · 지울 파일 {gone}개"
              + ("   [미리보기 - 아무것도 바꾸지 않음]" if dry else ""))
        if dry:
            return 0
        if not (back or gone):
            print("이미 원본 그대로입니다 — 바꿀 것이 없습니다.")
            return 0
        if not yes and sys.stdin is not None and sys.stdin.isatty():
            try:
                ans = input("계속할까요? [Y/n] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                ans = "n"
            if ans not in ("", "y", "yes", "ㅛ"):
                print("되돌리지 않았습니다.")
                return 0
        b, back, gone = restore(target, manifest["name"], force=force, quiet=True)
        print(f"되돌림: {b} 의 원본 {back}개를 다시 놓고, 이 꾸러미가 만든 파일 {gone}개를 지웠습니다.")
        return 0
    try:
        steps, backup = apply(target, HERE, manifest, dry, runtime_only=runtime, all_or_nothing=aon)
    except ApplyFailed as e:
        print(f"{manifest['name']}  ({manifest.get('summary', '')})\n대상: {target}\n")
        if e.rolled_back:
            print(f"[적용하지 못해 원래대로 되돌렸습니다] 파일: {e.rel}\n   사유: {_why(e.cause)}")
        else:
            print(f"[적용하지 못했습니다 - 바꾼 파일은 없습니다] 파일: {e.rel}\n   사유: {_why(e.cause)}")
        print("\n원인을 없앤 뒤(서버·편집기 닫기 · 디스크 비우기) 같은 bat 를 다시 실행하세요.  서버는 그대로 돕니다.")
        return EXIT_ROLLED_BACK
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
