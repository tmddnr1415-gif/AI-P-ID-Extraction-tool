"""38회차 [B] 게이트 — 선언이 지문을 움직이지 않는가.

    python3 spike/mode_gate.py data/UAD_binding.pdf bid out/round38/B_uad_bid.json

`declared_mode` 를 넣고 분석해 지문 · 행 · Q'ty · evidence_tier 를 적는다.  태그는 지문
밖이므로 선언이 무엇이든 지문은 같아야 하고, 다른 것은 `tagged_rows` 와 `conflict` 뿐이어야 한다.
"""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from app import pipeline  # noqa: E402

pdf, mode, dest = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
t0 = time.time()
r = pipeline.analyse(pdf, declared_mode=mode or None)
r["fingerprint"] = pipeline.fingerprint(r)
rows = r["rows"]
out = {"pdf": str(pdf), "declared_mode": mode, "fingerprint": r["fingerprint"], "rows": len(rows),
       "qty_sum": sum(x["qty"] for x in rows if x.get("qty")),
       "tagged_rows": sum(1 for x in rows if x.get("tag_no")),
       "evidence_tier": r["evidence_tier"], "seconds": round(time.time() - t0, 1)}
dest.write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps({k: out[k] for k in ("fingerprint", "rows", "qty_sum", "tagged_rows")}), out["evidence_tier"].get("conflict"), out["evidence_tier"].get("effective"))
