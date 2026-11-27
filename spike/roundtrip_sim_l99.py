"""L99 — 그리는 사람 · 올리는 사람의 길을 끝까지: 분석한 로직(A)을 똑같이 그리고(B), 그 그림을 PDF 로 내어 다시 올려 분석한 것(R)까지
**세 쪽을 같은 입력으로 시뮬레이션**해 오른쪽 행 값을 견준다.

  A  원본 PDF 를 분석한 장                         (검토 화면이 돌리는 것)
  B  그 장을 똑같이 그린 그림 → 시뮬레이터 꼴        (작도 화면의 시뮬레이션 · draw_sim)
  R  그 그림을 PDF 로 내어 다시 분석한 장            (그린 PDF 를 올리는 사람이 받는 것)

장마다 입력 조합: 모두 0 · 모두 1 · 무작위 K-2 개.  A≠B 는 그리기(들여오기 · 그림 시뮬레이터)의 차이, A≠R 는 그림 → PDF → 되읽기의 차이.
읽기만 한다 (분석 폴더 · 그림 저장소에 쓰지 않는다).

  PID_DATA_DIR=<데이터> python3 spike/roundtrip_sim_l99.py <job> <out.json> [K=4] [일꾼=3] [시트 이름,…]
"""
from __future__ import annotations

import json
import os
import random
import sys
import tempfile
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

JOB = OUT = None
K = 4
RES = FORM = None
EQ_DOC = False
_SRC = None


def _init(job):
    global RES, FORM
    from app.logic import api, draw_sets
    RES = api._result(job)
    FORM = draw_sets.source_form(RES)
    global EQ_DOC
    EQ_DOC = any(b.get("logic") == "vote" and (b.get("param") or {}).get("op") == "eq" for s in RES["sheets"] for b in s["blocks"].values())


def _row_map(a):
    """분석 행 번호 → 그림 행 번호 (draw.from_sheet 의 rn 과 같은 식 · spike/diff_sim_l85 와 같다)."""
    from app.logic import draw as D
    rows, table = a.get("rows") or [], a.get("table") or []
    nL = max([r["n"] for r in table if r.get("n") and r["side"] == "L"] + [r["n"] for r in rows if r.get("n") and r["side"] == "L"] + [0])
    nR0 = min([r["n"] for r in table if r.get("n") and r["side"] == "R"] + [r["n"] for r in rows if r.get("n") and r["side"] == "R"] + [10 ** 6])
    No = max(nL, nR0 - 1 if nR0 < 10 ** 6 else 0)
    N = max(D.N_MIN, min(D.N_MAX, No or D.N_DEFAULT))
    return lambda n: n if n <= No else n - No + N


def _as_uploaded(pdf_path, rr):
    """그린 PDF 를 **올린 사람이 받는 것** 그대로: 분석 결과를 임시 묶음으로 두고 앱이 읽는 길(`api._result` — 감시 블록 설정값 · 단자 이름 ·
    상수 · 안 그림을 PDF 에서 얹는다)로 꺼낸다.  묶음은 바로 지운다 (PID_DATA_DIR 은 버릴 폴더여야 한다).
    투표 `2=3` 은 묶음 전체를 올렸을 때처럼 본다 — 원본 문서가 '이상' 을 따로 적는 문서면 그린 묶음에도 `2/3` 이 있다."""
    import shutil
    from app.logic import analyse as AN, api, store
    job, d = store.new_job("roundtrip.pdf")
    try:
        shutil.copyfile(pdf_path, d / "source.pdf")
        store.write_result(d, rr)
        st = store.read_status(d)
        st.update({"state": "done", "sheets": len(rr["sheets"]), "seconds": 1})
        store.write_status(d, st)
        r = api._result(job)["sheets"][0]
        if EQ_DOC:
            AN._vote_equal_sign([r, {"blocks": {"evidence": {"logic": "vote", "label": "2/3"}}}])
        return r
    finally:
        shutil.rmtree(d, ignore_errors=True)
        for c in (api._SP, api._APPLIED, api._BUNDLE, store._RES):
            c.pop(job, None)


def _last(r):
    return ((r.get("frames") or [{}])[-1]).get("values") or {}


def one(i):
    global _SRC
    import pymupdf
    from app.logic import analyse as AN, aops, draw, draw_sim, sim
    a = RES["sheets"][i]
    out = {"sheet": a.get("sheet_no") or f"p{a['page']}", "page": a["page"], "runs": 0, "rows": 0, "ab": [], "ar": [], "only": {}}
    try:
        if _SRC is None:
            _SRC = pymupdf.open(str(Path(os.environ["PID_DATA_DIR"]) / "logic" / JOB / "source.pdf"))
        doc = draw.from_sheet(a, out["sheet"], "roundtrip", "", page=_SRC[a["page"] - 1])
        if FORM:
            doc["form"] = FORM
        doc = {**doc, **draw.clean(doc)}
        b = draw_sim.to_sheet(doc, a["page"])
        aops.identify([b])
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "d.pdf")
            Path(p).write_bytes(draw.to_pdf(doc))
            try:
                rr = AN.analyse(p)
                r = _as_uploaded(p, rr) if rr.get("sheets") else None
            except Exception as e:                         # noqa: BLE001
                r = None
                out["reread_error"] = repr(e)[:160]
        # L100 — 아날로그 연산자가 왕복에서 살아남는가: 장마다 (기능 이름 · 연산) 의 수를 A · B · R 에서 견준다
        import collections

        def kinds(sh):
            return collections.Counter(f"{x.get('func') or '?'}|{aops.op_of(x) or '-'}" for x in sh["blocks"].values() if x.get("logic") == "unknown")
        ka, kb, kr = kinds(a), kinds(b), (kinds(r) if r else collections.Counter())
        out["aop"] = {"n": sum(ka.values()), "b_lost": dict(ka - kb), "b_new": dict(kb - ka), "r_lost": dict(ka - kr), "r_new": dict(kr - ka)}
        rn = _row_map(a)
        rows = lambda s: {(x["side"], x["n"]): x for x in s["rows"] if x.get("net") is not None}
        ar_, br_, rr_ = rows(a), rows(b), (rows(r) if r else {})
        ins = [n for (sd, n) in ar_ if sd == "L"]
        outs = [n for (sd, n) in ar_ if sd == "R"]
        out["only"] = {"b_missing": sorted(f"{sd}{n}" for (sd, n) in ar_ if (sd, rn(n)) not in br_),
                       "r_missing": sorted(f"{sd}{n}" for (sd, n) in ar_ if (sd, rn(n)) not in rr_) if r else ["(되읽기 실패)"]}
        rng = random.Random(9900 + a["page"])
        trials = [{n: 0 for n in ins}, {n: 1 for n in ins}] + [{n: rng.randint(0, 1) for n in ins} for _ in range(max(0, K - 2))]
        for tr in trials:
            va = _last(sim.simulate(a, forces={f"row:{n}": v for n, v in tr.items()}))
            vb = _last(sim.simulate(b, forces={f"row:{rn(n)}": v for n, v in tr.items() if ("L", rn(n)) in br_}))
            vr = _last(sim.simulate(r, forces={f"row:{rn(n)}": v for n, v in tr.items() if ("L", rn(n)) in rr_})) if r else {}
            out["runs"] += 1
            for n in outs:
                x = va.get(str(ar_[("R", n)]["net"]))
                out["rows"] += 1
                if ("R", rn(n)) in br_:
                    y = vb.get(str(br_[("R", rn(n))]["net"]))
                    if x != y and len(out["ab"]) < 40:
                        out["ab"].append({"row": n, "a": x, "b": y, "on": sum(tr.values()), "of": len(tr)})
                if r and ("R", rn(n)) in rr_:
                    z = vr.get(str(rr_[("R", rn(n))]["net"]))
                    if x != z and len(out["ar"]) < 40:
                        out["ar"].append({"row": n, "a": x, "r": z, "on": sum(tr.values()), "of": len(tr)})
    except Exception as e:                                 # noqa: BLE001
        out["error"] = repr(e)[:200]
        out["tb"] = traceback.format_exc()[-600:]
    return out


def main():
    global JOB, OUT, K
    JOB, OUT = sys.argv[1], sys.argv[2]
    K = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    workers = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    only = set(sys.argv[5].split(",")) if len(sys.argv) > 5 and sys.argv[5] else None
    _init(JOB)
    idx = [i for i, s in enumerate(RES["sheets"]) if s.get("rows") and (not only or (s.get("sheet_no") or "") in only)]
    t0 = time.time()
    rows = []
    if workers > 1:
        import multiprocessing as mp
        with mp.get_context("fork").Pool(workers) as pool:
            for k, o in enumerate(pool.imap_unordered(one, idx, chunksize=4)):
                rows.append(o)
                if (k + 1) % 100 == 0:
                    print(f"{k + 1}/{len(idx)} · {time.time() - t0:.0f}s", flush=True)
    else:
        rows = [one(i) for i in idx]
    rows.sort(key=lambda o: o["page"])
    tot = {"sheets": len(rows), "runs": sum(o["runs"] for o in rows), "sim_runs": 3 * sum(o["runs"] for o in rows), "rows": sum(o["rows"] for o in rows),
           "ab_sheets": sum(1 for o in rows if o["ab"]), "ab_rows": len({(o["sheet"], d["row"]) for o in rows for d in o["ab"]}),
           "ar_sheets": sum(1 for o in rows if o["ar"]), "ar_rows": len({(o["sheet"], d["row"]) for o in rows for d in o["ar"]}),
           "b_missing_rows": sum(len(o["only"].get("b_missing") or []) for o in rows),
           "r_missing_rows": sum(len(o["only"].get("r_missing") or []) for o in rows),
           "errors": sum(1 for o in rows if o.get("error")), "reread_errors": sum(1 for o in rows if o.get("reread_error")),
           "seconds": round(time.time() - t0)}
    import collections
    agg = {k: collections.Counter() for k in ("b_lost", "b_new", "r_lost", "r_new")}
    for o in rows:
        for k in agg:
            agg[k].update((o.get("aop") or {}).get(k) or {})
    tot["aop"] = {"n": sum((o.get("aop") or {}).get("n", 0) for o in rows), **{k: sum(v.values()) for k, v in agg.items()}}
    tot["aop_detail"] = {k: dict(v.most_common(25)) for k, v in agg.items()}
    Path(OUT).write_text(json.dumps({"total": tot, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(tot, ensure_ascii=False))


if __name__ == "__main__":
    main()
