"""회사 PC 갈음 꾸러미 r55 를 만든다 (10~53회차 누적).

    python3 spike/pack_handover_r55.py

무엇을 담는가
    `git diff --name-status <기준>..HEAD` 의 A·M 중 **소스만** 담는다
    (`app/` `config/` `docs/` `spike/` `tests/` `conftest.py` `CLAUDE.md`
    `README.md`).  `out/` 은 회차 산출물이라 담지 않는다.  D·R 이 하나라도
    있으면 멈춘다 (손으로 봐야 한다).

바깥 zip (`out/PID_update_<날짜>_r55.zip`) 에는 셋이 들어간다
    1_먼저읽기_README.txt   <- out/round55/1_먼저읽기_README.txt
    2_파일목록.txt          <- [A]/[M] 목록
    3_덮어쓸파일.zip        <- 소스 파일 (저장소 뿌리에 푼다 · 재압축하지 않는다)

★ 설치 파일(wheel)은 **따로** 나간다 — 합치면 메일 한도(20MB)를 넘는다.
    4_설치파일_wheels_part00.zip   ezdxf 계열 (도면을 **읽는** 데 필요)
    4_설치파일_wheels_part01.zip   matplotlib 계열 (화면에 **그리는** 데 필요)
  둘을 같은 폴더에 풀고 한 번에 설치한다.  9/3 이관 때 이미 들어간 것
  (numpy · packaging · typing_extensions)은 담지 않는다 —
  `requirements-win.lock.txt` 와 버전이 같은 것을 확인했다.

★ 절대 담지 않는 것
    `app/_data/` — 실 DB(`app.db` · `-wal` · `-shm`)와 `uploads/`.
    **목록 시점과 zip 시점 두 번 검사**하고, 하나라도 걸리면 멈춘다.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "aac64ba"                      # 회사 PC 가 마지막으로 맞춘 커밋
ROUND = "r55"
KEEP = ("app/", "config/", "docs/", "spike/", "tests/")
KEEP_FILES = ("conftest.py", "CLAUDE.md", "README.md")
FORBIDDEN = ("app/_data/", "app/_data")
OUT = ROOT / "out" / "round55"


def forbidden(paths, when: str) -> None:
    bad = [p for p in paths if any(str(p).startswith(f) for f in FORBIDDEN)]
    if bad:
        print("★ 멈춥니다 — %s 에 담기면 안 되는 것이 있습니다: %s" % (when, bad))
        raise SystemExit(2)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    out = subprocess.run(["git", "diff", "--name-status", "%s..HEAD" % BASE],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    files = []
    for line in out.splitlines():
        st, _, path = line.partition("\t")
        path = path.strip().strip('"')
        if not (path.startswith(KEEP) or path in KEEP_FILES):
            continue
        if st[0] not in "AM":
            print("★ 멈춥니다 — 손으로 봐야 하는 상태 %s: %s" % (st, path))
            return 2
        files.append((st[0], path))
    files.sort(key=lambda t: (t[0] != "M", t[1]))
    forbidden([p for _s, p in files], "목록")

    added = [p for s, p in files if s == "A"]
    modified = [p for s, p in files if s == "M"]
    print("담는 파일 %d개 — 새로 %d · 덮어쓰기 %d" % (len(files), len(added), len(modified)))

    OUT.mkdir(parents=True, exist_ok=True)
    inner = OUT / "3_FILES_TO_OVERWRITE.zip"
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
    print("%s  %d bytes  sha256 %s" % (inner.name, inner.stat().st_size, sha(inner)))

    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True, check=True).stdout.strip()
    lines = ["# 회사 PC 꾸러미 %s — 파일 목록 (기준 %s..%s · 소스만)" % (ROUND, BASE, head),
             "# [A] 새로 %d · [M] 덮어쓰기 %d · [D] 삭제 0 · [R] 이동 0 — 수동 삭제 목록: 없음"
             % (len(added), len(modified)), ""]
    lines += ["[%s] %s" % (s, p) for s, p in files]
    listing = OUT / "2_파일목록.txt"
    listing.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (ROOT / "out" / "handover_final.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    readme = OUT / "1_먼저읽기_README.txt"
    if not readme.exists():
        print("★ 멈춥니다 — 없습니다: %s" % readme)
        return 2
    outer = ROOT / "out" / ("PID_update_%s_%s.zip" % (dt.date.today().isoformat(), ROUND))
    if outer.exists():
        outer.unlink()
    with zipfile.ZipFile(outer, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(readme, "1_먼저읽기_README.txt")
        z.write(listing, "2_파일목록.txt")
        z.write(inner, "3_덮어쓸파일.zip")
        forbidden(z.namelist(), "바깥 zip")
    print("%s  %d bytes  sha256 %s" % (outer.name, outer.stat().st_size, sha(outer)))

    # ── 설치 파일 두 꾸러미.  나누는 기준은 **무엇에 쓰이는가** 다 (크기가 아니다):
    #    part00 이 없으면 DXF 를 **읽지 못하고**, part01 이 없으면 읽은 도면을
    #    화면에 **그리지 못한다** (`app/engine/dxf_render.py` 는 함수 안에서
    #    matplotlib 을 부르므로, 없어도 서버는 뜨고 분석·Excel 은 된다).
    src = Path("/tmp/wheels_r55_all")
    parts = {"part00": ["ezdxf-", "pyparsing-", "fonttools-"],
             "part01": ["matplotlib-", "pillow-", "contourpy-", "cycler-",
                        "kiwisolver-", "python_dateutil-", "six-"]}
    if src.exists():
        for name, heads in parts.items():
            zp = ROOT / "out" / ("4_설치파일_wheels_%s.zip" % name)
            if zp.exists():
                zp.unlink()
            with zipfile.ZipFile(zp, "w", zipfile.ZIP_STORED) as z:   # whl 은 이미 압축돼 있다
                for w in sorted(src.glob("*.whl")):
                    if any(w.name.startswith(h) for h in heads):
                        z.write(w, "wheels_r55/" + w.name)
                n = len(z.namelist())
            print("%s  %d bytes  sha256 %s  (%d개)" % (zp.name, zp.stat().st_size, sha(zp), n))
    else:
        print("⚠ %s 가 없어 설치 파일 꾸러미를 만들지 않았습니다" % src)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
