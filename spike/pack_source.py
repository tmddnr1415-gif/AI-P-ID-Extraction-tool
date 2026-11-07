"""회사 PC 로 개발을 옮길 때 쓰는 소스 꾸러미 (GitHub 가 막힌 곳용).

    python3 spike/pack_source.py [--out out/PID_source_<날짜>.zip]

hotfix 꾸러미(`pack_hotfix.py`)는 **운영 폴더에 덮어쓸 파일**만 담는다.  이것은 **개발을
이어받을 저장소 전체**를 담는다 — 코드 · 설정 · 시험 · spike 도구 · docs · CLAUDE.md ·
out/ 의 보고서(글).  커밋된 파일만 담고(`git ls-files`) 무거운 산출물은 뺀다:

  * out/ 아래 zip · db · pdf · 그림(png/jpg) — 지난 회차의 결과물이고 다시 만들 수 있다
  * out/ 아래 1MB 넘는 json — 전량 분석 결과(행 덤프).  회귀는 회사 PC 에서 다시 잰다

`app/_data/` · `data/` 는 처음부터 커밋되지 않으므로 들어가지 않는다 (코드가 한 번 더 막는다).
git 이력은 담지 않는다 — 받은 쪽에서 `git init` 으로 그 시점부터 시작한다 (README 머리에 적는다).
"""
from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEAVY_EXT = {".zip", ".db", ".db-wal", ".db-shm", ".pdf", ".png", ".jpg", ".jpeg", ".egg"}
BIG_JSON = 1_000_000
README = "0_먼저읽기_이관.txt"


def keep(rel: str) -> bool:
    p = ROOT / rel
    if rel.startswith(("app/_data/", "data/")):
        return False
    if rel.startswith("out/"):
        if p.suffix.lower() in HEAVY_EXT:
            return False
        if p.suffix.lower() == ".json" and p.stat().st_size > BIG_JSON:
            return False
    return p.is_file()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    files = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True,
                           text=True).stdout.split("\0")
    files = sorted(f for f in files if f and keep(f))
    today = dt.date.today().isoformat()
    out = Path(a.out) if a.out else ROOT / "out" / f"PID_source_{today}.zip"
    readme = (ROOT / "out" / "source_handover_readme.txt").read_text(encoding="utf-8")
    readme = readme.replace("{HEAD}", head).replace("{BRANCH}", branch) \
                   .replace("{DATE}", today).replace("{N}", str(len(files)))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(README, readme)
        for f in files:
            z.write(ROOT / f, f)
    print(f"{out} · {len(files)} files · {out.stat().st_size / 1e6:.1f} MB · HEAD {head} · {branch}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
