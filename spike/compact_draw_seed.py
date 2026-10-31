"""L84 — 씨앗 묶음(config/logic_draw_seed/*.json.gz)의 그림마다 선 토막을 연결 그대로 묶고 판(rev)을 하나 올린다.

  python3 spike/compact_draw_seed.py config/logic_draw_seed/amiral_19va_r1.json.gz

서버는 판이 오른 씨앗을 받으면 **사람이 손대지 않은** 그림만 새 판으로 바꾼다 (draw.install_seeds) — 고친 때 · 저장 횟수는 그대로 둔다.
묶은 결과는 장마다 draw_compact.compact 가 시뮬레이터 꼴로 견주어 연결이 같을 때만 남는다.
"""
from __future__ import annotations

import gzip
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.logic import draw_compact  # noqa: E402

f = Path(sys.argv[1])
pack = json.loads(gzip.decompress(f.read_bytes()).decode("utf-8"))
t = time.time()
before = after = fails = 0
for doc in pack["docs"]:
    n0 = len(doc.get("wires") or [])
    doc.pop("compact", None)
    rep = draw_compact.compact_doc(doc)
    before += n0
    after += len(doc.get("wires") or [])
    fails += 0 if rep.get("ok", True) else 1
pack["rev"] = int(pack.get("rev") or 1) + 1
f.write_bytes(gzip.compress(json.dumps(pack, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 9, mtime=0))
print(f"{f.name}: 선 {before} → {after} · 묶지 못한 장 {fails} · 판 {pack['rev']} · {time.time() - t:.0f}초")
