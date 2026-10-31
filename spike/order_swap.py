"""36회차 [F] — 한 프로세스에서 순서를 바꿔 이어 분석해도 지문이 같은가 (§4 ⑨ 전역 누출).

    python3 spike/order_swap.py SADARA "AL NOUF1" TC2

22회차 방법 그대로: 낯선 프로필 문서(SADARA · TC2 — `_fit_layout` 이 overlay 한다) 뒤에
AL NOUF1 을 같은 프로세스에서 돌려 `fb85b039` 가 그대로인지 본다.  36회차가 `_rebind_config`
에 넣은 값(룰셋 · formats.unit_code_* · dedup)이 `_own_config` 로 되돌아오는지가 여기서 드러난다.
★ 엔진을 고치지 않는다.  재는 도구다.
"""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import pipeline
PDFS = {"AL NOUF1": "data/pid_total.pdf", "SADARA": "app/_data/uploads/2391ee0f1ea6_sadara_1A46.pdf",
        "TC2": "data/TC2_260821.pdf", "UAD": "data/UAD_binding.pdf"}
out = []
for name in sys.argv[1:]:
    t = time.time()
    r = pipeline.analyse(str(ROOT / PDFS[name]))
    fp = pipeline.fingerprint(r)[:8]
    rec = {"name": name, "rows": len(r["rows"]), "fingerprint": fp,
           "qty": sum(int(x.get("qty") or 0) for x in r["rows"]), "seconds": round(time.time() - t, 1),
           "unit_forms": r.get("unit_forms"), "anchors": len(pipeline.ds.RULESET_V3.field_type_map)}
    out.append(rec); print(json.dumps(rec, ensure_ascii=False), flush=True)
    del r
Path(ROOT / "out/round36/order_swap.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
