"""L85 — 차등 시뮬레이션: 같은 장을 **분석 결과 시트**(검토 화면이 돌리는 것)와 **다시 그린 그림**(Logic 작성이 돌리는 것)으로
같은 입력을 넣어 돌리고 출력 행 값을 견준다.  둘은 같은 도면이므로 다르면 들여오기(draw.from_sheet) · 작성 시뮬레이션(draw_sim) ·
선 묶기(draw_compact) 중 하나의 결함이다.  예외 · 느린 장도 함께 적는다.

  PID_DATA_DIR=<데이터> python3 spike/diff_sim_l85.py <job id> <묶음 id> [시도 수=8] [out.json] [시트 이름,…]
"""
from __future__ import annotations

import json
import random
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.logic import aops, draw_sets, draw_sim, sim, library  # noqa: E402
from app.logic import api as A  # noqa: E402

job, sid = sys.argv[1], sys.argv[2]
K = int(sys.argv[3]) if len(sys.argv) > 3 else 8
OUT = sys.argv[4] if len(sys.argv) > 4 else "diff_sim.json"
ONLY = set(sys.argv[5].split(",")) if len(sys.argv) > 5 and sys.argv[5] else None

res = A._result(job)
A_by_page = {s["page"]: s for s in res["sheets"] if not s.get("library") and s["page"] < library.LIB_PAGE0}
if sid == "-":                                   # 묶음 없이 — 분석 결과에서 그림을 바로 짓는다 (draw_sets.import_bundle 과 같은 길 · 저장 안 함)
    from app.logic import draw
    form = draw_sets.source_form(res)
    docs = []
    for i, s_ in enumerate(sorted(A_by_page.values(), key=lambda q: q["page"])):
        if ONLY and (s_.get("sheet_no") or f"p{s_['page']}") not in ONLY:
            continue
        d_ = draw.from_sheet(s_, s_.get("sheet_no") or f"p{s_['page']}", "diff", "")
        if form:
            d_["form"] = form
        d_.update({"set": "diffset", "order": i + 1, "source": {"job": job, "page": s_["page"]}})
        docs.append(d_)
else:
    docs = draw_sets.set_docs(sid)
t0 = time.time()
B_sheets = draw_sim.sheets_of(docs)
aops.identify(B_sheets)
print(f"그림 → 시트 {len(B_sheets)}장 {time.time() - t0:.1f}초", flush=True)
did_doc = {d["id"]: d for d in docs}


def row_map(a):
    """분석 행 번호 → 그림 행 번호 (draw.from_sheet 의 rn 과 같은 식)."""
    from app.logic import draw as D
    rows, table = a.get("rows") or [], a.get("table") or []
    nL = max([r["n"] for r in table if r.get("n") and r["side"] == "L"] + [r["n"] for r in rows if r.get("n") and r["side"] == "L"] + [0])
    nR0 = min([r["n"] for r in table if r.get("n") and r["side"] == "R"] + [r["n"] for r in rows if r.get("n") and r["side"] == "R"] + [10 ** 6])
    No = nL if nR0 == 10 ** 6 else min(nL, nR0 - 1) if nL else nR0 - 1
    N = max(D.N_MIN, min(D.N_MAX, No or D.N_DEFAULT))
    return lambda n: n if n <= No else n - No + N


def last_values(r):
    fr = (r.get("frames") or [{}])[-1]
    return fr.get("values") or {}


rng = random.Random(85)
report = {"sheets": 0, "runs": 0, "mismatch_sheets": [], "errors": [], "slow": [], "rows_compared": 0, "rows_diff": 0}
for b in B_sheets:
    doc = did_doc[b["did"]]
    a = A_by_page.get((doc.get("source") or {}).get("page"))
    if a is None or (ONLY and doc["name"] not in ONLY):
        continue
    rn = row_map(a)
    a_rows = {(r["side"], r["n"]): r for r in a["rows"] if r.get("net") is not None}
    b_rows = {(r["side"], r["n"]): r for r in b["rows"] if r.get("net") is not None}
    ins = [n for (sd, n) in a_rows if sd == "L" and ("L", rn(n)) in b_rows]
    outs = [n for (sd, n) in a_rows if sd == "R" and ("R", rn(n)) in b_rows]
    only_a = sorted(f"{sd}{n}" for (sd, n) in a_rows if (sd, rn(n)) not in b_rows)
    only_b = sorted(f"{sd}{n}" for (sd, n) in b_rows if (sd, n) not in {(s2, rn(n2)) for (s2, n2) in a_rows})
    report["sheets"] += 1
    trials = [{n: 0 for n in ins}, {n: 1 for n in ins}] + [{n: rng.randint(0, 1) for n in ins} for _ in range(K)]
    diffs = []
    ta = tb = 0.0
    for tr in trials:
        try:
            t = time.time(); ra = sim.simulate(a, forces={f"row:{n}": v for n, v in tr.items()}); ta += time.time() - t
            t = time.time(); rb = sim.simulate(b, forces={f"row:{rn(n)}": v for n, v in tr.items()}); tb += time.time() - t
        except Exception as e:
            report["errors"].append({"sheet": doc["name"], "err": repr(e)[:300], "tb": traceback.format_exc()[-800:]})
            break
        report["runs"] += 1
        va, vb = last_values(ra), last_values(rb)
        for n in outs:
            x, y = va.get(str(a_rows[("R", n)]["net"])), vb.get(str(b_rows[("R", rn(n))]["net"]))
            report["rows_compared"] += 1
            if x != y:
                report["rows_diff"] += 1
                diffs.append({"row": n, "a": x, "b": y, "inputs": {k: v for k, v in tr.items()}})
    if ta + tb > 2.0:
        report["slow"].append({"sheet": doc["name"], "a": round(ta, 2), "b": round(tb, 2), "trials": len(trials)})
    if diffs or only_a or only_b:
        report["mismatch_sheets"].append({"sheet": doc["name"], "page": a["page"], "did": doc["id"], "rows_only_analysis": only_a,
                                          "rows_only_drawing": only_b, "n_diff": len(diffs), "diff_rows": sorted({d["row"] for d in diffs}),
                                          "example": diffs[:2]})
    if report["sheets"] % 100 == 0:
        print(f"{report['sheets']}장 · 실행 {report['runs']} · 다른 장 {len(report['mismatch_sheets'])} · 오류 {len(report['errors'])}", flush=True)
Path(OUT).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in report.items()}, ensure_ascii=False))
