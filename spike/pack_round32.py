"""32회차 출력 꾸러미 — `out/round32_result.zip`.

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
R = OUT / "round32"

PLAN = [
    ("0_요약.md",            R / "0_요약.md"),
    ("1_결론.md",            R / "1_결론.md"),
    ("2_progress.md",        OUT / "round32_progress.md"),
    ("3_display.md",         R / "3_display.md"),
    ("4_audit.md",           R / "4_audit.md"),
    ("5_synthetic.md",       R / "5_synthetic.md"),
    ("6_regression_4p.json", OUT / "regression_3p.json"),
]

EXCLUDED = [
    "합성 PDF (`tests/data/synthetic/*.pdf`) — 발주처 도면의 쪽을 재료로 쓴다",
    "발주처 도면·리스트 (`data/`, `app/_data/`)",
    "네 프로젝트 결과 json 전문 (`out/regression_3p/*.json`) — 행 내용이 들어 있다",
]


def main() -> int:
    zpath = OUT / "round32_result.zip"
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
        man = ["# MANIFEST — 32회차 출력", "",
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
