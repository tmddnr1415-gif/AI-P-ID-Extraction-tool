"""33회차 출력 꾸러미 — `out/round33_result.zip`.

프롬프트가 지정한 이름 그대로 담는다.  ★ 담은 것과 **뺀 것**을 MANIFEST 에
적는다 (진단 zip 규율과 같다) — 합성 PDF 와 발주처 도면은 안 담는다.
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
R = OUT / "round33"

PLAN = [
    ("0_요약.md",            R / "0_요약.md"),
    ("1_보고서.md",          R / "1_보고서.md"),
    ("2_progress.md",        OUT / "round33_progress.md"),
    ("3_죽는버그.md",        R / "3_죽는버그.md"),
    ("4_색.md",              R / "4_색.md"),
    ("5_메모리.md",          R / "5_메모리.md"),
    ("6_regression_4p.json", R / "6_regression_4p.json"),
]

EXCLUDED = [
    "메모리 실측 json (`out/round33/mem_*.json`) — 보고서 표에 옮겨 적었다",
    "합성 PDF (`tests/data/synthetic/*.pdf`) — 발주처 도면의 쪽을 재료로 쓴다",
    "발주처 도면·리스트 (`data/`, `app/_data/`)",
    "네 프로젝트 결과 json 전문 (`out/regression_3p/*.json`) — 행 내용이 들어 있다",
]


def main() -> int:
    zpath = OUT / "round33_result.zip"
    shots = sorted((R / "7_캡처").rglob("*.png"))
    facts = sorted((R / "7_캡처").rglob("facts.json"))
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        names = []
        for arc, src in PLAN:
            if not src.exists():
                raise SystemExit(f"없는 파일: {src}")
            z.write(src, arc)
            names.append(arc)
        for p in shots + facts:
            arc = "7_캡처/" + str(p.relative_to(R / "7_캡처"))
            z.write(p, arc)
            names.append(arc)
        man = ["# MANIFEST — 33회차 출력", "",
               f"담긴 파일 {len(names)}개 (캡처 {len(shots)}장)", ""]
        man += [f"* {n}" for n in names[:len(PLAN)]]
        man += ["", "## 뺀 것", ""] + [f"* {e}" for e in EXCLUDED]
        z.writestr("MANIFEST.md", "\n".join(man) + "\n")
    sha = hashlib.sha256(zpath.read_bytes()).hexdigest()
    print(json.dumps({"zip": str(zpath), "bytes": zpath.stat().st_size,
                      "files": len(names) + 1, "shots": len(shots),
                      "sha256": sha[:16]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
