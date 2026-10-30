"""L85 — 씨앗 묶음을 **지금 분석기 · 들여오기**로 다시 만든다 (같은 원본 PDF 를 다시 분석해 들인 묶음에서).

  PID_DATA_DIR=<데이터> python3 spike/rebuild_draw_seed_l85.py config/logic_draw_seed/<씨앗>.json.gz <새로 들인 묶음 id>

장마다(시트 이름으로 맞대어) 옛 씨앗의 id · 묶음 · 차례 · 프로젝트 · 타이틀블록 칸 · 고친 때 · 저장 횟수를 그대로 두고
그림(블록 · 선 · 글 · 행)만 새것으로 바꾼다 — 서버는 판(rev)이 오르면 사람이 손대지 않은 장(저장 횟수 · 고친 때가 같은 장)만 바꾼다.
19VA: 옛 씨앗(L77 분석기)은 못 읽은 기호(UNKNOWN 207 · ?) 294개 · 감시 블록이 운전 버튼 · 연산 입력 이름이 없었다."""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.logic import draw_sets  # noqa: E402

KEEP = ("id", "set", "set_name", "project", "project_name", "doc_no", "rev", "order", "created", "updated", "saves", "author",
        "history", "source", "name", "typical")
f, sid = Path(sys.argv[1]), sys.argv[2]
pack = json.loads(gzip.decompress(f.read_bytes()).decode("utf-8"))
new = {d["name"]: d for d in draw_sets.set_docs(sid)}
out, miss = [], []
for o in pack["docs"]:
    n = new.get(o["name"])
    if n is None:
        miss.append(o["name"])
        out.append(o)
        continue
    d = {k: v for k, v in n.items() if k not in KEEP}
    d.update({k: o[k] for k in KEEP if k in o})
    out.append(d)
pack["docs"] = out
pack["rev"] = int(pack.get("rev") or 1) + 1
f.write_bytes(gzip.compress(json.dumps(pack, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 9, mtime=0))
print(f"{f.name}: {len(out)}장 · 새 그림 {len(out) - len(miss)} · 그대로 {len(miss)} · 판 {pack['rev']} · {f.stat().st_size // 1024}KB")
