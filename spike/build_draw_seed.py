"""L77 — 작도 그림 묶음을 업데이트에 실을 씨앗으로 만든다 (config/logic_draw_seed/<이름>.json.gz).

  PID_DATA_DIR=<데이터 폴더> python3 spike/build_draw_seed.py <묶음 id> <씨앗 이름>

그 묶음의 그림을 그대로(id · 묶음 · 순서 · Typical 표시까지) 한 파일에 담는다.  서버는 처음 목록을 열 때 한 번 들인다 (draw.install_seeds).
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.logic import draw, draw_sets  # noqa: E402

sid, name = sys.argv[1], sys.argv[2]
docs = sorted(draw_sets.set_docs(sid), key=lambda d: d.get("order") or 0)
if not docs:
    sys.exit(f"묶음 {sid} 에 그림이 없습니다")
pack = {"set": sid, "name": docs[0].get("set_name"), "docs": docs}
out = ROOT / "config" / "logic_draw_seed" / f"{name}.json.gz"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_bytes(gzip.compress(json.dumps(pack, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 9, mtime=0))
print(out, len(docs), "장", out.stat().st_size, "bytes")
