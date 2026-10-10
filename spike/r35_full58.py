"""35회차 [D] 마무리 — 전량 58장 확인 실행 (worktree).

    python3 spike/r35_full58.py

`groups.json` 에서 **완주하고 탐침 지문이 같은** 묶음의 상수만 지운 채(나머지는 전부 되살려)
`data/pid_total.pdf` 58장을 돈다.  결과 `out/round35/full58.json` · 행 덤프 `rows_full58.json`.
본선 `fb85b039 · 1037 · 1931` 과 대조하고, 다르면 열 단위로 가른다.
"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "spike"))
from r35_replay import run_once
lst = (ROOT / "out/round35_strip_list.md").read_text()
MOD = {"app/engine/detect_symbols.py": "ds", "app/engine/detect_valves.py": "dv", "app/engine/extract_titleblocks.py": "tb"}
dc = [f"{MOD[f]}.{field}" for f, _, field, _ in re.findall(r"^\| `([^:`]+):(\d+)` \| `([a-z_]+)` \| `(.+?)` \| ", lst, re.M)]
cfg = ["cfg." + k for k in json.load(open(ROOT / "out/round35/strip_keys.json")) if k != "project.code"]
ALL = dc + cfg
groups = json.load(open(ROOT / "out/round35/groups.json"))
stripped = sorted({m for g in groups.values() if g.get("ok") and g.get("fingerprint") == "0087c236" and g.get("rows") == 199 for m in g["members"]})
if "--all-restored" in sys.argv:      # 유도 overlay 만의 효과 — 지운 것 없이 낯선 프로필 경로
    stripped = []
tag = "overlay" if "--all-restored" in sys.argv else "full58"
restored = [n for n in ALL if n not in stripped]
print(json.dumps({"stripped": len(stripped), "restored": len(restored)}), flush=True)
r = run_once(str(ROOT / "data/pid_total.pdf"), restored, True)
dump = r.pop("rows_dump", None)
if dump is not None:
    (ROOT / f"out/round35/rows_{tag}.json").write_text(json.dumps(dump))
r["stripped"] = stripped; r["restored"] = restored
(ROOT / f"out/round35/{tag}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1))
print(json.dumps({k: v for k, v in r.items() if k in ("ok", "rows", "fingerprint", "qty", "missing", "seconds", "moved", "derived", "error")}, ensure_ascii=False), flush=True)
