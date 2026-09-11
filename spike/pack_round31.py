"""31회차 결과 꾸러미.  담은 것만 담고, 담지 않은 것은 MANIFEST 에 적는다."""
from __future__ import annotations
import hashlib, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "round31"
ZIP = ROOT / "out" / "round31_result.zip"

FILES = ["0_요약.md", "1_보고서.md", "2_progress.md", "3_기존구조_조사.md",
         "4_승수_대상행.md", "5_alarm_suffix.md", "6_regression_4p.json"]


def main() -> int:
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for n in FILES:
            p = OUT / n
            assert p.exists(), p
            z.write(p, n)
        for p in sorted((OUT / "7_캡처").rglob("*")):
            if p.is_file():
                z.write(p, str(p.relative_to(OUT)))
        for n in ("program_overview.md", "state_and_roadmap.md"):
            z.write(ROOT / "docs" / n, "docs/" + n)
        z.writestr("MANIFEST.txt",
                   "31회차 결과 꾸러미\n\n"
                   "담은 것: 요약·보고서·진행기록·조사·대상행·경보접미 측정·회귀 json·캡처\n"
                   "         docs/program_overview.md (구조·성능·범용성)\n"
                   "         docs/state_and_roadmap.md (현황과 방향)\n\n"
                   "담지 않은 것: 원본 PDF · 발주처 Excel · DB · 업로드 파일\n")
    print(ZIP, ZIP.stat().st_size,
          hashlib.sha256(ZIP.read_bytes()).hexdigest()[:8])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
