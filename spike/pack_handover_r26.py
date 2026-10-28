"""회사 PC 갈음 꾸러미 r26 를 만든다 (10~26회차 누적).

    python3 spike/pack_handover_r26.py

무엇을 담는가
    `git diff --name-status <기준>..HEAD` 의 A·M 중 **소스만** 담는다
    (`app/` `config/` `docs/` `spike/` `tests/` `conftest.py` `CLAUDE.md`
    `README.md`).  `out/` 은 회차 산출물이라 담지 않는다.

★ 절대 담지 않는 것
    `app/_data/` — 실 DB(`app.db` · `-wal` · `-shm`)와 `uploads/`.
    **목록 시점과 zip 시점 두 번 검사**하고, 하나라도 걸리면 멈춘다.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "aac64ba"                      # 회사 PC 가 마지막으로 맞춘 커밋
KEEP = ("app/", "config/", "docs/", "spike/", "tests/")
KEEP_FILES = ("conftest.py", "CLAUDE.md", "README.md")
FORBIDDEN = ("app/_data/", "app/_data")


def forbidden(paths, when: str) -> None:
    bad = [p for p in paths if any(str(p).startswith(f) for f in FORBIDDEN)]
    if bad:
        print("★ 멈춥니다 — %s 에 담기면 안 되는 것이 있습니다: %s" % (when, bad))
        raise SystemExit(2)


def main() -> int:
    out = subprocess.run(["git", "diff", "--name-status", "%s..HEAD" % BASE],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    files = []
    for line in out.splitlines():
        st, _, path = line.partition("\t")
        path = path.strip().strip('"')
        if st[0] not in "AM":
            print("★ 멈춥니다 — 손으로 봐야 하는 상태 %s: %s" % (st, path))
            return 2
        if path.startswith(KEEP) or path in KEEP_FILES:
            files.append((st[0], path))
    files.sort(key=lambda t: (t[0] != "M", t[1]))
    forbidden([p for _s, p in files], "목록")

    added = [p for s, p in files if s == "A"]
    modified = [p for s, p in files if s == "M"]
    print("담는 파일 %d개 — 새로 %d · 덮어쓰기 %d" % (len(files), len(added), len(modified)))

    inner = ROOT / "out" / "round26" / "3_FILES_TO_OVERWRITE.zip"
    inner.parent.mkdir(parents=True, exist_ok=True)
    if inner.exists():
        inner.unlink()
    with zipfile.ZipFile(inner, "w", zipfile.ZIP_DEFLATED) as z:
        for _s, path in sorted(files, key=lambda t: t[1]):
            src = ROOT / path
            if not src.exists():
                print("★ 멈춥니다 — 파일이 없습니다: %s" % path)
                return 2
            z.write(src, path)
        forbidden(z.namelist(), "zip")
    print("%s  %d bytes  sha256 %s" % (inner.name, inner.stat().st_size,
                                       hashlib.sha256(inner.read_bytes()).hexdigest()))
    (ROOT / "out" / "round26" / "_filelist.txt").write_text(
        "\n".join("%s %s" % (s, p) for s, p in files) + "\n")
    # [C] out/handover_final.txt — [A] [M] [D] [R] 구분. D·R 은 위에서 멈추므로 여기 오면 0 이다.
    lines = ["# 회사 PC 꾸러미 r26 — 파일 목록 (기준 %s..HEAD · 소스만)" % BASE,
             "# [A] 새로 %d · [M] 덮어쓰기 %d · [D] 삭제 0 · [R] 이동 0 — 수동 삭제 목록: 없음" % (len(added), len(modified)), ""]
    lines += ["[%s] %s" % (s, p) for s, p in files]
    (ROOT / "out" / "handover_final.txt").write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
