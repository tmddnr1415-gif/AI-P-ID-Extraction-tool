"""35회차 출력 꾸러미 — `out/round35_result.zip`.

프롬프트가 지정한 이름 그대로 담는다.  담은 것과 **뺀 것**을 MANIFEST 에 적는다.
"""
from __future__ import annotations
import hashlib, json, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"; R = OUT / "round35"
PLAN = [
    ("0_요약.md", R / "0_요약.md"), ("1_보고서.md", R / "1_보고서.md"),
    ("2_progress.md", OUT / "round35_progress.md"), ("3_strip_list.md", OUT / "round35_strip_list.md"),
    ("4_replay.md", OUT / "round35_replay.md"), ("5_classified.md", OUT / "round35_classified.md"),
    ("6_remaining.md", OUT / "round35_remaining.md"), ("7_human_vs_rule.md", OUT / "round35_human_vs_rule.md"),
    ("8_regression_4p.json", R / "8_regression_4p.json"),
    ("8_regression_4p_start.json", R / "8_regression_4p_start.json"),
    ("기록/groups.json", R / "groups.json"), ("기록/moved.json", R / "moved.json"),
    ("기록/replay_late_pass1.json", R / "replay_late_pass1.json"), ("기록/replay_pass2_final.json", R / "replay_pass2_final.json"),
    ("기록/replay_probe.json", R / "replay_probe.json"), ("기록/pass2_prerestored.json", R / "pass2_prerestored.json"),
    ("기록/strip_keys.json", R / "strip_keys.json"), ("기록/judgements.json", R / "judgements.json"), ("기록/lists.json", R / "lists.json"),
    ("기록/full58.json", R / "full58.json"), ("기록/overlay.json", R / "overlay.json"),
    ("worktree.diff", R / "worktree.diff"),
]
EXCLUDED = [
    "행 덤프 (`out/round35/rows_*.json`) — 행 좌표·판정 전문이라 뺀다 (필요하면 저장소에 있다)",
    "탐침 PDF (`/tmp/r35_probe.pdf`) 와 발주처 도면·리스트 (`data/`, `app/_data/`)",
    "worktree 자체 (`/tmp/r35_strip`) — 남겨 두었고 diff 만 담는다",
]
def main() -> int:
    zpath = OUT / "round35_result.zip"
    shots = sorted((R / "9_캡처").rglob("*.png")) if (R / "9_캡처").exists() else []
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        names = []
        for arc, src in PLAN:
            if not src.exists(): raise SystemExit(f"없는 파일: {src}")
            z.write(src, arc); names.append(arc)
        for p in shots:
            arc = "9_캡처/" + str(p.relative_to(R / "9_캡처")); z.write(p, arc); names.append(arc)
        if not shots:
            z.writestr("9_캡처/README.md", "㉢(유도가 대신하고 지문이 다름)가 0건이라 렌더로 가릴 자리가 없었다 — 캡처 없음.\n"); names.append("9_캡처/README.md")
        man = ["# MANIFEST — 35회차 출력", "", f"담긴 파일 {len(names)}개", ""] + [f"* {n}" for n in names] + ["", "## 뺀 것", ""] + [f"* {e}" for e in EXCLUDED]
        z.writestr("MANIFEST.md", "\n".join(man) + "\n")
    sha = hashlib.sha256(zpath.read_bytes()).hexdigest()
    print(json.dumps({"zip": str(zpath), "bytes": zpath.stat().st_size, "files": len(names) + 1, "sha256": sha[:16]}, ensure_ascii=False))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
