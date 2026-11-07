"""35회차 [E] 보조 — `_fit_layout` 이 낯선 프로필 경로에서 실제로 **얹는** 키 목록.

    PYTHONPATH=/tmp/r35_strip R35_NO_STRIP=1 R35_STRIP_AT_LOAD=project.code \
        PID_DATA_DIR=$(mktemp -d) python3 spike/r35_moved.py /tmp/r35_probe.pdf

재현 루프의 strip 훅은 이 키들을 **지우지 않는다**(유도가 이미 답했으므로).
그러므로 지울 목록과 이 목록의 교집합은 "지워 본 적이 없는 상수 = 유도가 덮는 상수(㉡)" 다.
"""
import json, sys
from pathlib import Path
from app import pipeline
from app.engine import pidcache
doc, pages = pidcache.load_pages(Path(sys.argv[1]))
layout = pipeline._fit_layout(pages)
moved = [m["key"] for m in (layout.get("moved") or []) if isinstance(m, dict)]
items = [(it.get("key") if isinstance(it, dict) else it) for it in (layout.get("items") or [])]
print("R35MOVED" + json.dumps({"moved": moved, "items": items, "item_values": {(it.get("key")): it.get("value") for it in (layout.get("items") or []) if isinstance(it, dict)}, "values": {m["key"]: [m.get("was"), m.get("now")] for m in (layout.get("moved") or [])}}, ensure_ascii=False, default=str))
