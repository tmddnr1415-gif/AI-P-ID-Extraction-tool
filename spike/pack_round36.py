"""36회차 출력 꾸러미 — `out/round36_result.zip`."""
from __future__ import annotations
import hashlib, json, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"; R = OUT / "round36"
PLAN = [("0_요약.md", R / "0_요약.md"), ("1_보고서.md", R / "1_보고서.md"), ("2_progress.md", OUT / "round36_progress.md"),
        ("3_type_map.md", R / "3_type_map.md"), ("4_gatekeeper.md", R / "4_gatekeeper.md"), ("5_unit_token.md", R / "5_unit_token.md"),
        ("6_delete.md", R / "6_delete.md"), ("7_remaining.md", R / "7_remaining.md"),
        ("8_regression_4p.json", R / "8_regression_4p.json"), ("8_regression_4p_start.json", R / "8_regression_4p_start.json"),
        ("8_regression_4p_BC.json", R / "8_regression_4p_BC.json"), ("8_regression_4p_E1.json", R / "8_regression_4p_E1.json"),
        ("8_regression_4p_E2.json", R / "8_regression_4p_E2.json"),
        ("기록/unit_token_survey.json", R / "unit_token_survey.json"), ("기록/unit_format_probe.json", R / "unit_format_probe.json"),
        ("기록/b2_anchors_probe.json", R / "b2_anchors_probe.json"), ("기록/lists.json", R / "lists.json"),
        ("기록/order_swap.json", R / "order_swap.json"), ("기록/synthetic_runs.json", OUT / "round32" / "synthetic_runs.json"),
        ("사전조사/round36_multiplier_vocab.md", OUT / "round36_multiplier_vocab.md")]
EXCLUDED = ["네 프로젝트 결과 json 전문 (`out/regression_3p/*.json`) — 행 내용이 들어 있다", "발주처 도면·리스트 (`data/`, `app/_data/`)",
            "35회차 worktree (`/tmp/r35_strip`) — [B-2] 탐침에 다시 썼다 · 남겨 둔다"]
def main() -> int:
    zpath = OUT / "round36_result.zip"
    shots = sorted((R / "9_캡처").rglob("*.png")) if (R / "9_캡처").exists() else []
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        names = []
        for arc, src in PLAN:
            if not src.exists(): raise SystemExit(f"없는 파일: {src}")
            z.write(src, arc); names.append(arc)
        for p in shots:
            arc = "9_캡처/" + str(p.relative_to(R / "9_캡처")); z.write(p, arc); names.append(arc)
        if not shots:
            z.writestr("9_캡처/README.md", "TC2 p33·p34·p35 Q'ty 전후는 `1_보고서.md` §D 의 표와 `기록/`(qty_basis 원문)로 대신한다 — 이 회차는 화면을 띄우지 않았다.\n"); names.append("9_캡처/README.md")
        man = ["# MANIFEST — 36회차 출력", "", f"담긴 파일 {len(names)}개", ""] + [f"* {n}" for n in names] + ["", "## 뺀 것", ""] + [f"* {e}" for e in EXCLUDED]
        z.writestr("MANIFEST.md", "\n".join(man) + "\n")
    sha = hashlib.sha256(zpath.read_bytes()).hexdigest()
    print(json.dumps({"zip": str(zpath), "bytes": zpath.stat().st_size, "files": len(names) + 1, "sha256": sha[:16]}, ensure_ascii=False))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
