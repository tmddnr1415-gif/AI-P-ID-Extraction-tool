"""핫픽스 꾸러미를 **직전 꾸러미 위에 얹어** 만든다 — 어느 PC 의 Claude Code 에서든 같은 방법.

    python3 spike/pack_hotfix.py --name hotfix33 --readme out/hotfix33/readme_head.txt \
        app/pipeline.py tests/test_hotfix33_x.py CLAUDE.md

규칙 (hotfix29~32 와 같다):
  · 직전 꾸러미 = `out/PID_hotfix*.zip` 중 번호가 가장 큰 것 (`--prev` 로 지정 가능).  그것을
    풀어 둔 위에 이번 파일을 **저장소 HEAD 상태 그대로** 복사한다 — 그래서 누적이다.
  · `1_먼저읽기.txt` 는 이번 머리글 + 직전 꾸러미의 것 (맨 위가 이번 내용).
  · 만든 뒤 zip 을 다시 풀어 **저장소와 바이트가 다른 파일이 0** 인지 센다 (readme 제외).
    0 이 아니면 직전 꾸러미에 든 파일이 그 뒤 저장소에서 바뀐 것이다 — 그 파일도 목록에 넣는다.
  · `app/_data/`(실 DB·업로드) · `data/`(발주처 자료) 는 어떤 경우에도 넣지 않는다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN = ("app/_data/", "data/")


def latest_prev() -> Path | None:
    zips = sorted(ROOT.glob("out/PID_hotfix*.zip"),
                  key=lambda p: int(re.search(r"hotfix(\d+)", p.name).group(1)))
    return zips[-1] if zips else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", help="이번 핫픽스에서 바뀐 저장소 파일 (상대 경로)")
    ap.add_argument("--name", required=True, help="hotfix33 처럼")
    ap.add_argument("--readme", required=True, help="이번 머리글 텍스트 파일")
    ap.add_argument("--prev", help="직전 꾸러미 zip (기본: out/PID_hotfix*.zip 중 최신)")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    a = ap.parse_args()

    for f in a.files:
        if any(f.startswith(x) for x in FORBIDDEN):
            sys.exit(f"넣을 수 없는 경로: {f}")
        if not (ROOT / f).is_file():
            sys.exit(f"저장소에 없는 파일: {f}")
    prev = Path(a.prev) if a.prev else latest_prev()
    stage = Path(tempfile.mkdtemp(prefix="pack-"))
    prev_readme = ""
    if prev and prev.exists():
        with zipfile.ZipFile(prev) as z:
            z.extractall(stage)
        rp = stage / "1_먼저읽기.txt"
        prev_readme = rp.read_text(encoding="utf-8") if rp.exists() else ""
        print(f"직전 꾸러미 {prev.name} 을 풀었다")
    else:
        print("직전 꾸러미 없음 — 이번 파일만으로 만든다")
    for f in a.files:
        dst = stage / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / f, dst)
    head = Path(a.readme).read_text(encoding="utf-8")
    (stage / "1_먼저읽기.txt").write_text(head.rstrip("\n") + "\n\n" + prev_readme, encoding="utf-8")

    out = ROOT / "out" / f"PID_{a.name}_{a.date}.zip"
    files = sorted(p for p in stage.rglob("*") if p.is_file())
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            rel = p.relative_to(stage).as_posix()
            if any(rel.startswith(x) for x in FORBIDDEN):
                continue
            z.write(p, rel)
    diff = [p.relative_to(stage).as_posix() for p in files
            if p.name != "1_먼저읽기.txt"
            and ((not (ROOT / p.relative_to(stage)).exists())
                 or (ROOT / p.relative_to(stage)).read_bytes() != p.read_bytes())]
    sha = hashlib.sha256(out.read_bytes()).hexdigest()[:12]
    print(f"{out} · {len(files)} files · {out.stat().st_size} bytes · sha256 {sha} · 저장소와 다른 파일 {len(diff)}")
    for d in diff:
        print("  DIFF", d)
    shutil.rmtree(stage, ignore_errors=True)
    return 1 if diff else 0


if __name__ == "__main__":
    sys.exit(main())
