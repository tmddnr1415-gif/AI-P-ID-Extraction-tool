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
SKIP = ("out/", "data/", "app/_data/",
        # hotfix132 — 대시보드 세션 몫 (CLAUDE.md §3: 대시보드 zip 은 대시보드 쪽에서).  VALVE 라인을 병합하며 함께 들어온
        # 대시보드 기록 · 옛 대시보드 업데이트 zip(약 230MB)이 P&ID 꾸러미에 실리던 것.  dashboard_apps/ 는 예전부터 실음.
        "dashboard/", "dashboard_patches/", "dashboard_tools/",
        # hotfix134 — 오케스트레이터 기록(회사 업데이트 zip 보관 · 현황판 · 미리보기 그림)은 P&ID 서버에 필요 없음 (약 41MB 가 실리던 것)
        "company-pc-update/", "status/")


def company_owned() -> tuple:
    """Paths the company PC develops itself (config/release_sources.json 'company_owned') — never shipped from here."""
    try:
        cfg = json.loads((Path(__file__).resolve().parents[1] / "config" / "release_sources.json").read_text(encoding="utf-8"))
        return tuple(cfg.get("company_owned", {}).get("paths") or ())
    except Exception:                                       # noqa: BLE001
        return ()
STAMP = "app/_update.json"
BAT = ("@echo off\r\n"
       "rem Apply this delta to C:\\Claude\\PID_dev (never to the operating folder).\r\n"
       "rem   apply_to_PID_dev.bat                   -> C:\\Claude\\PID_dev\r\n"
       "rem   apply_to_PID_dev.bat D:\\x\\PID_dev       -> that folder (it must hold app\\main.py)\r\n"
       "rem   add --dry-run to see what would change without changing anything\r\n"
       "rem Unpack the whole zip first; this does not work from inside the zip.\r\n"
       "cd /d \"%~dp0\"\r\n"
       "setlocal enabledelayedexpansion\r\n"
       "set PYTHONUTF8=1\r\n"
       "set \"TARGET=C:\\Claude\\PID_dev\"\r\n"
       "set \"FIRST=\"\r\n"
       "if exist \"%~1\\app\\main.py\" (set \"TARGET=%~1\"& set \"FIRST=%~1\")\r\n"
       "set \"REST=\"\r\n"
       "for %%a in (%*) do if not \"%%~a\"==\"!FIRST!\" set \"REST=!REST! %%a\"\r\n"
       "set \"PY=%TARGET%\\.venv\\Scripts\\python.exe\"\r\n"
       "if not exist \"%PY%\" set \"PY=python\"\r\n"
       "\"%PY%\" apply_delta.py \"%TARGET%\" --overwrite !REST!\r\n"
       "pause\r\n")


# hotfix60 — 운영 폴더(C:\Claude\PID)용.  서버가 돌리는 파일(app/... · config/...)만 · 하나라도 충돌이면 아무것도
# 안 바꾼다 · 그 뒤 포트 8000 의 서버만 다시 띄운다 (python 을 이름으로 끄지 않는다 — 대시보드도 python).
OPS_BAT = ("@echo off\r\n"
           "rem Apply this update to the OPERATING folder C:\\Claude\\PID (the server the dashboard shows).\r\n"
           "rem Only the files the server runs (app\\... and config\\...).  hotfix133 overwrite rule: a file changed in that\r\n"
           "rem folder is backed up first and then replaced with the new version.  Then only the port 8000 server is restarted.\r\n"
           "cd /d \"%~dp0\"\r\n"
           "set PYTHONUTF8=1\r\n"
           "set \"TARGET=C:\\Claude\\PID\"\r\n"
           "if not \"%~1\"==\"\" set \"TARGET=%~1\"\r\n"
           "set \"PY=%TARGET%\\.venv\\Scripts\\python.exe\"\r\n"
           "if not exist \"%PY%\" set \"PY=python\"\r\n"
           "\"%PY%\" apply_delta.py \"%TARGET%\" --ops --runtime --all-or-nothing --overwrite\r\n"
           "if errorlevel 1 goto end\r\n"
           "\"%PY%\" restart_pid_server.py 8000\r\n"
           ":end\r\n"
           "pause\r\n")
ROLLBACK_BAT = ("@echo off\r\n"
                "rem Undo this update in the OPERATING folder C:\\Claude\\PID and restart the port 8000 server.\r\n"
                "cd /d \"%~dp0\"\r\n"
                "set PYTHONUTF8=1\r\n"
                "set \"TARGET=C:\\Claude\\PID\"\r\n"
                "if not \"%~1\"==\"\" set \"TARGET=%~1\"\r\n"
                "set \"PY=%TARGET%\\.venv\\Scripts\\python.exe\"\r\n"
                "if not exist \"%PY%\" set \"PY=python\"\r\n"
                "\"%PY%\" apply_delta.py \"%TARGET%\" --ops --restore\r\n"
                "if errorlevel 1 goto end\r\n"
                "\"%PY%\" restart_pid_server.py 8000\r\n"
                ":end\r\n"
                "pause\r\n")

# hotfix132 — 현장이 읽는 운영 적용 순서와 되돌리기 (설명서 config/user_manual.md §업데이트 와 같은 말)
OPS_README = ("\n운영 반영 순서 (설명서 config\\user_manual.md 의 '업데이트' 절과 같습니다):\n"
              "  ① 압축을 전부 푼다 (zip 안에서 바로 실행하면 멈춥니다)\n"
              "  ② apply_to_PID_dev.bat   — 개발 폴더(PID_dev)에 먼저\n"
              "  ③ apply_to_PID_ops.bat   — 운영 폴더(PID)에 · '다시 띄울까요?' 에 Enter\n"
              "  ④ 화면을 새로 고쳐 오른쪽 위/아래의 업데이트 번호(예: '버전 1.0.0 · 업데이트 132 · 날짜')가 바뀌었는지 본다\n"
              "  ⑤ 문제가 있으면 rollback_PID_ops.bat — 이 꾸러미가 바꾼 파일만 원래대로\n"
              "적용이 도중에 실패하면(파일 잠김 · 디스크 부족) 자동으로 원래대로 되돌리고 멈춥니다 — 원인을 없애고 다시 실행하세요.\n"
              "덮어쓰기 원칙(hotfix133~): 회사에서 따로 고친 파일도 backup\\<꾸러미>_<시각>\\ 에 원본을 둔 뒤 최신으로 덮습니다 — 화면 끝의 [덮어씀 - 회사에서 고친 파일] 목록을 보세요.\n"
              "운영 폴더에는 app\\ 와 config\\ 만 갱신됩니다 — 뿌리의 *.bat 와 spike\\ 의 도구는 PID_dev 에서 씁니다.\n")


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


SOURCES_FILE = ROOT / "config" / "release_sources.json"
CHECK_FILE = ROOT / "out" / "release_check.json"       # hotfix132 — spike/release_check.py 가 남기는 검사 결과
DOC_ONLY = ("out/", "docs/")                            # 이 경로·확장자만 다른 HEAD 는 "검사한 코드와 같다" 고 본다
DOC_EXT = (".md", ".txt")


def _doc_only(paths: list[str]) -> bool:
    return all(p.startswith(DOC_ONLY) or p.endswith(DOC_EXT) for p in paths)


def release_gate(head: str, check_file: Path | None = None) -> list[str]:
    """hotfix132 — 꾸러미를 만들기 전 `spike/release_check.py` 가 통과했는지 본다.  막을 이유의 목록 (빈 목록 = 통과).

    검사 결과의 head 가 지금 HEAD 와 같거나, 그 사이 차이가 문서(out/ · docs/ · *.md · *.txt)뿐이면 유효하다 —
    readme_head.txt 커밋 하나 때문에 2분 검사를 다시 돌리지 않게.  커밋하지 않은 변경 위에서 돈 검사(dirty)는 거부한다.
    """
    f = check_file or CHECK_FILE
    if not f.exists():
        return [f"{f.relative_to(ROOT) if f.is_relative_to(ROOT) else f} 가 없습니다 — 먼저 python3 spike/release_check.py 를 돌리세요"]
    try:
        r = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [f"검사 결과 파일을 읽지 못했습니다: {e}"]
    reasons = []
    if not r.get("ok"):
        reasons.append("마지막 검사가 통과하지 못했습니다 (" + "; ".join(map(str, r.get("failures") or ["사유 없음"])) + ")")
    if r.get("dirty") is None:
        reasons.append("검사 결과에 작업 트리 기록(dirty)이 없습니다 — python3 spike/release_check.py 를 다시 돌리세요")
    elif r.get("dirty"):
        files = [str(x) for x in (r.get("dirty_files") or [])]
        reasons.append(f"검사할 때 커밋하지 않은 변경이 있었습니다 ({len(files)}개"
                       + (f" — 예: {files[0]}" if files else "") + ") — 꾸러미는 커밋에서 만듭니다.  커밋한 뒤 다시 검사하세요")
    checked = str(r.get("head") or "")
    if not checked:
        reasons.append("검사 결과에 head 가 없습니다")
    elif not head.startswith(checked) and not checked.startswith(head):
        try:
            changed = [p for p in git("diff", "--name-only", checked, head).splitlines() if p]
        except subprocess.CalledProcessError:
            changed = ["?"]
        if not _doc_only(changed):
            code = [p for p in changed if not (p.startswith(DOC_ONLY) or p.endswith(DOC_EXT))]
            reasons.append(f"검사한 커밋 {checked} 뒤에 코드가 바뀌었습니다 ({len(code)}개 — 예: {code[0]}) — 다시 검사하세요")
    return reasons


def unmerged_sources() -> list[str]:
    """hotfix128 — 꾸러미에 함께 실리는 다른 세션의 브랜치가 HEAD 에 다 들어왔는지 본다.

    hotfix127 이 옛 LOGIC 브랜치(L72)만 합치고 새 LOGIC 세션의 L73~L78 을 빠뜨린 일이
    다시 없도록, `config/release_sources.json` 에 적힌 브랜치를 fetch 해서 HEAD 에 없는
    커밋이 있으면 그 목록을 돌려준다 (빈 목록이면 통과).  판넬처럼 파일만 옮겨 오는
    원본은 `paths` 를 적으면 그 경로를 건드린 커밋 중 `imported` 뒤의 것만 본다.
    """
    if not SOURCES_FILE.exists():
        return []
    problems = []
    for name, src in json.loads(SOURCES_FILE.read_text(encoding="utf-8")).get("sources", {}).items():
        branch = src["branch"]
        subprocess.run(["git", "fetch", "-q", "origin", branch], cwd=ROOT,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ref = f"origin/{branch}"
        if subprocess.run(["git", "rev-parse", "-q", "--verify", ref], cwd=ROOT,
                          stdout=subprocess.DEVNULL).returncode:
            problems.append(f"{name}: {ref} 를 찾지 못했습니다 (fetch 실패?)")
            continue
        if src.get("paths"):
            rng = f"{src['imported']}..{ref}" if src.get("imported") else ref
            log = git("log", "--format=%h %s", rng, "--", *src["paths"])
        else:
            log = git("log", "--format=%h %s", f"HEAD..{ref}")
        if log:
            lines = log.splitlines()
            problems.append(f"{name}: {ref} 에 아직 안 들어온 커밋 {len(lines)}개 — 예: {lines[0]}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--summary", default="")
    ap.add_argument("--readme", default="")
    ap.add_argument("--base", default="")
    ap.add_argument("--ops", action="store_true", help="운영 폴더용 단추(적용·되돌리기)와 서버 재시작 도구를 같이 싣는다")
    ap.add_argument("--only", default="",
                    help="쉼표로 나눈 경로 앞부분만 싣는다 (예: app/valve/,app/static/valve/,app/main.py). "
                         "다른 세션의 모듈 꾸러미용 — 딱지(app/_update.json)와 기준 파일(out/PID_dev_delta_base.txt)은 건드리지 않는다")
    ap.add_argument("--allow-unmerged", action="store_true",
                    help="다른 세션 브랜치가 덜 합쳐졌어도 만든다 (사용자가 그렇게 하라고 했을 때만)")
    ap.add_argument("--skip-checks", action="store_true",
                    help="hotfix132 — release_check 결과 없이도 만든다 (사유를 1_먼저읽기.txt 꼬리에 '검사 생략' 으로 남긴다)")
    a = ap.parse_args()
    missing = unmerged_sources()
    if missing and a.only:                     # 모듈 꾸러미는 --only 경로만 싣는다 — 다른 세션 파일은 어차피 안 실린다
        print("참고 (모듈 꾸러미라 멈추지 않음):", *missing, sep="\n  · ")
        missing = []
    if missing and not a.allow_unmerged:
        print("다른 세션의 최신 변경이 아직 합쳐지지 않았습니다 — 먼저 병합하세요:")
        for m in missing:
            print("  ·", m)
        print("(목록은 config/release_sources.json · 일부러 빼는 경우만 --allow-unmerged)")
        return 2
    if git("status", "--porcelain", "--untracked-files=no"):
        print("커밋하지 않은 변경이 있습니다 — 커밋한 뒤 만드세요 (꾸러미는 HEAD 를 담는다)")
        return 1
    base = a.base or (BASE_FILE.read_text().strip() if BASE_FILE.exists() else FIRST_BASE)
    head = git("rev-parse", "--short", "HEAD")
    # hotfix132 — 릴리스 게이트: 시험·JS 구문·화면 스모크가 이 HEAD 에서 통과했어야 한다 (unmerged 와 같은 꼴)
    gate = release_gate(head)
    skipped_note = ""
    if gate and a.only:
        print("참고 (모듈 꾸러미라 멈추지 않음):", *gate, sep="\n  · ")
    elif gate and a.skip_checks:
        print("검사 생략 (--skip-checks):", *gate, sep="\n  · ")
        skipped_note = "\n[검사 생략] 이 꾸러미는 릴리스 검사 없이 만들었습니다:\n" + "\n".join(f"  · {g}" for g in gate) + "\n"
    elif gate:
        print("릴리스 검사가 통과하지 않았습니다 — 꾸러미를 만들지 않습니다:")
        for g in gate:
            print("  ·", g)
        print("(python3 spike/release_check.py 를 돌린 뒤 다시 · 일부러 건너뛰는 경우만 --skip-checks)")
        return 3
    paths = [p for p in git("-c", "core.quotepath=off", "diff", "--name-only", base, "HEAD").splitlines()
             if p and not p.startswith(SKIP)]
    only = tuple(x.strip() for x in a.only.split(",") if x.strip())
    if only:
        paths = [p for p in paths if p.startswith(only)]
    owned = company_owned()
    if owned and not (only and any(o.startswith(owned) for o in only)):   # 2026-11-01: Valve 는 회사 PC 가 개발
        dropped = [p for p in paths if p.startswith(owned)]
        paths = [p for p in paths if not p.startswith(owned)]
        if dropped:
            print(f"회사 PC 소유 경로 {len(dropped)}개는 싣지 않음 (config/release_sources.json company_owned):", *dropped[:5], sep="\n  · ")
    deleted = [p for p in paths if blob("HEAD", p) is None]
    paths = [p for p in paths if p not in deleted]
    day = dt.date.today().isoformat()
    zname = f"PID_dev+ops_{a.name}_{day}.zip" if a.ops else f"PID_dev_{a.name}_{day}.zip"

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
    if not only:
        files.append({"path": STAMP, "base_sha256": h(blob(base, STAMP)), "new_sha256": h(stamp_bytes),
                      "always": True})
    # hotfix58 — 앞 꾸러미가 보냈다가 저장소가 없앤 파일 (기준판에도 HEAD 에도 없어 diff 에 안 잡힌다).
    # 우리가 보낸 판 그대로일 때만 지운다 — 회사에서 고친 판은 남기고 보고한다.
    gone = git("-c", "core.quotepath=off", "log", "--diff-filter=D", "--name-only", "--format=",
               f"{base}..HEAD").splitlines()
    for p in sorted({g for g in gone if g and not g.startswith(SKIP) and not (owned and g.startswith(owned) and not only)
                     and (not only or g.startswith(only))} | set(deleted)):
        if blob("HEAD", p) is not None:
            continue
        known = []
        for c in git("log", "--format=%H", f"{base}..HEAD", "--", p).splitlines():
            for rev in (c, c + "~1"):
                b = blob(rev, p)
                if b is not None and h(b) not in known:
                    known.append(h(b))
        files.append({"path": p, "base_sha256": h(blob(base, p)), "new_sha256": None,
                      "known_sha256": known, "remove": True})
    manifest = {"name": a.name, "summary": a.summary, "base_commit": base, "head_commit": head,
                "created_at": stamp["created_at"], "files": files, "deleted_upstream": deleted}

    readme = (Path(a.readme).read_text(encoding="utf-8") if a.readme else "") + (
        f"\n\n----\n{a.name} 변경분 꾸러미 · 기준 {base} → {head} · 파일 {len(files)}개\n"
        "적용: 이 폴더의 apply_to_PID_dev.bat 더블클릭 (PID_dev 에만 적용 · 운영 폴더는 거부)\n"
        "      먼저 보기만: apply_to_PID_dev.bat --dry-run\n"
        "충돌(회사에서 고친 파일)은 덮지 않고 <파일>.<이름>.new 로 옆에 둡니다.\n"
        "원본 백업: C:\\Claude\\PID_dev\\backup\\<이름>_<시각>\\\n\n"
        + "\n".join(f"  {'(지움) ' if f.get('remove') else ''}{f['path']}" for f in files) + "\n")
    if a.ops:
        readme += OPS_README
    readme += skipped_note
    out = ROOT / "out" / zname
    tmp = out.with_name(zname + ".tmp")          # hotfix132 — 검증을 통과한 뒤에만 제 이름이 된다
    rc = 0
    try:
        rc = _write_and_verify(a, files, stamp_bytes, manifest, readme, tmp, base, head)
        if rc == 0:
            import os as _os
            _os.replace(tmp, out)
            print(f"{out.relative_to(ROOT)}  {out.stat().st_size:,} bytes  · 파일 {len(files)} · 기준 {base} → {head}")
            if not a.only:
                BASE_FILE.write_text(head + "\n")
        else:
            print(f"꾸러미를 만들지 않았습니다 (검증 실패) — {zname}")
    finally:
        if tmp.exists():
            tmp.unlink()
    return rc


def _write_and_verify(a, files, stamp_bytes, manifest, readme, out: Path, base: str, head: str) -> int:
    """zip 을 쓰고 기준판 트리에 실제로 적용해 HEAD 와 같은지 센다.  0 이면 통과."""
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            if f.get("remove"):
                continue
            data = stamp_bytes if f["path"] == STAMP else blob("HEAD", f["path"])
            z.writestr(f"files/{f['path']}", data)
        z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        z.writestr("apply_delta.py", (ROOT / "spike" / "apply_delta.py").read_bytes())
        z.writestr("apply_to_PID_dev.bat", BAT.encode("ascii"))
        if a.ops:
            z.writestr("apply_to_PID_ops.bat", OPS_BAT.encode("ascii"))
            z.writestr("rollback_PID_ops.bat", ROLLBACK_BAT.encode("ascii"))
            z.writestr("restart_pid_server.py", (ROOT / "spike" / "restart_pid_server.py").read_bytes())
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
        diff = [f["path"] for f in files if f["path"] != STAMP and not f.get("remove")
                and h((tree / f["path"]).read_bytes()) != h(blob("HEAD", f["path"]))]
        diff += [f["path"] for f in files if f.get("remove") and (tree / f["path"]).exists()]
        if a.ops:
            # 운영 길도 같은 기준판에 실제로 걸어 본다 — 서버 파일만 · 전부 아니면 무
            ops_tree = td / "PID"
            tarfile.open(fileobj=io.BytesIO(tar)).extractall(ops_tree)
            osteps, _ = apply_delta.apply(ops_tree, pkg, json.loads((pkg / "manifest.json").read_text("utf-8")),
                                          runtime_only=True, all_or_nothing=True)
            bad += [s["path"] for s in osteps if s.get("aborted")]
            diff += [f["path"] for f in files if f["path"].startswith(apply_delta.RUNTIME) and f["path"] != STAMP
                     and not f.get("remove") and h((ops_tree / f["path"]).read_bytes()) != h(blob("HEAD", f["path"]))]
            diff += [f["path"] for f in files if not f["path"].startswith(apply_delta.RUNTIME)
                     and (ops_tree / f["path"]).exists() and not f.get("remove")
                     and h((ops_tree / f["path"]).read_bytes()) == h(blob("HEAD", f["path"]))
                     and h(blob(base, f["path"])) != h(blob("HEAD", f["path"]))]   # 운영에는 서버 파일만
    print(f"검증: 기준판에 적용 → 충돌 {len(bad)} · HEAD 와 다른 파일 {len(diff)}")
    rm = [f["path"] for f in files if f.get("remove")]
    if rm:
        print(f"저장소에서 없앤 파일 {len(rm)}개 — 우리가 보낸 판 그대로일 때만 지웁니다: {rm}")
    if bad or diff:
        print(bad, diff)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
