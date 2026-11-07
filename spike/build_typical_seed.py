"""L63 — 공통 Typical 사전 씨앗 `config/logic_typicals.json.gz` 를 만든다.

분석 결과 json(지금 코드로 · 빈 학습 사전에서 분석한 것)마다 매크로가 이어진 Typical 시트를 모은다 (library.learn_from_result 와
같은 고르기).  제목 · 시트 이름이 같은 Typical 은 앞 묶음의 것 하나 (`from` 에 다른 묶음 이름을 더한다).
분석기 시트 꼴(`sheet` — 매크로 맞대기 · 시뮬레이션)과 작도 그림(`doc` — 사람이 고치는 것)을 함께 싣는다.

  python3 spike/build_typical_seed.py 19VA=<19va.json> AL_DHAFRA=<a5j.json> HRSG=<hrsg.json> 1A1Y=<a1y.json>
"""
from __future__ import annotations

import gzip
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.logic import draw, library  # noqa: E402

out, seen, stats = {}, {}, []
for arg in sys.argv[1:]:
    bundle, path = arg.split("=", 1)
    res = json.loads(Path(path).read_text(encoding="utf-8"))
    by_page = {s["page"]: s for s in res["sheets"]}
    used = {}
    for s in res["sheets"]:
        for b in s["blocks"].values():
            m = b.get("macro") or {}
            if b.get("func") == "MACRO" and m.get("page") in by_page and not m.get("library"):
                used.setdefault(m["page"], b.get("caption") or b.get("label") or "")
    n_new = 0
    for page, cap in sorted(used.items()):
        s = by_page[page]
        ty = {"sheet_no": s.get("sheet_no", ""), "title": s.get("title", "")}
        k = library._title_key(ty)
        if k in seen:
            out[seen[k]]["also"] = sorted(set(out[seen[k]].get("also", []) + [bundle]))
            continue
        tid = library._tid(bundle, s)
        doc = draw.from_sheet(s, s.get("sheet_no") or tid, "사전", "")
        doc = {kk: v for kk, v in doc.items() if kk not in ("id", "history", "author", "created", "updated", "saves", "set", "set_name", "order", "source")}
        out[tid] = {**ty, "caption": (cap or "")[:200], "from": bundle, "png": None, "zoom": 2.5,
                    "sheet": library._typical_copy(s), "doc": doc, "at": time.strftime("%Y-%m-%d")}
        seen[k] = tid
        n_new += 1
    stats.append(f"{bundle}: Typical {len(used)} · 새로 {n_new}")
blob = json.dumps({"_about": "공통 Typical 사전 씨앗 (L63) — spike/build_typical_seed.py 가 만든다 · 손으로 고치지 말 것 (작도 화면 'Typical 사전' 에서 고친다)",
                   "typicals": out}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
p = ROOT / "config" / "logic_typicals.json.gz"
p.write_bytes(gzip.compress(blob, 9, mtime=0))
print("\n".join(stats))
print(f"Typical {len(out)} · {len(blob) // 1024}KB → {p.stat().st_size // 1024}KB")
