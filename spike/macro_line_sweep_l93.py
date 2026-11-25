"""L93 — 매크로 안쪽(Typical 시트)의 **모든 선**을 신호를 줘 가며 켜 보고, 장마다 그림으로 남긴다 (눈으로 보는 점검).

장마다: 아무것도 안 줌 · 입력 하나씩 1 / 0 · 모두 1 · 모두 1 에서 하나씩 0 (L52 `logic_line_sweep` 의 조합 그대로) →
한 번도 1 이 안 된 선은 범례 정의로 거꾸로 풀어 본다 (`sim.scenario` — 순서 · 시간이 있어야 서는 선).  선마다 갈래:
  on          조합만으로 1 이 됨                       (초록)
  reachable   순서 · 시간 · 다른 조합을 주면 1 이 됨      (연두 · 점검 조합이 모자랐을 뿐)
  const0      도면이 0 으로 묶어 둔 선 (정상)             (회색)
  analog      아날로그 값 선 (상수 A · 연산 블록 출력 — 0/1 로 서는 선이 아니다)   (파랑)
  seq         타이머 · 메모리 뒤 — 풀이가 조합을 못 찾음   (주황)
  dead        몰이가 없는 선 · 판정 못 한 블록 · 덜 읽은 게이트 · 그 뒤의 선 (읽기 빈틈)   (빨강)
그림: 원본 쪽 위에 선을 그 색으로 덧칠.  읽기만 한다 (분석 폴더에 쓰지 않는다).

  PID_DATA_DIR=<데이터> python3 spike/macro_line_sweep_l93.py <job> <out 폴더> [시트 이름,…]
"""
from __future__ import annotations

import collections
import json
import random
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "spike"))
import logic_line_sweep as LS  # noqa: E402
from app.logic import api, sim, store  # noqa: E402

RANDOM_RUNS = 150            # 장마다 무작위 순서 시도 수 (한 번 = 세 걸음)
ANALOG_FUNCS = {"ANALOG SIGNAL GENERATOR", "AUTO/MANUAL CONTROL STATION", "TRANSFER", "PID", "DIFFERENCE", "SUMMER", "INTEGRAL"}
COL = {"on": (0.0, 0.62, 0.25), "reachable": (0.45, 0.75, 0.1), "const0": (0.55, 0.55, 0.55), "analog": (0.2, 0.45, 0.9), "seq": (0.95, 0.55, 0.0), "dead": (0.9, 0.1, 0.1)}
KIND = {"reachable": "reachable", "reachable_direct": "dead", "const0": "const0", "source0": "const0", "timer": "seq", "memory_seq": "seq",
        "not_always1": "seq", "logic_dead": "seq", "sink": "const0"}


def sweep(s, sheets, cache):
    ins, outs, drivers, sinks, groups = sim._index(s)
    rows_in = [r["n"] for r in s["rows"] if r["side"] == "L" and r.get("net") is not None]
    # 신호원 — 누름단추 · 신호 상자(들어오는 선 없음) + 감시 블록(B.Q · H/ … — 아날로그 값을 받아 0/1 을 낸다 · 검토 화면에서 사람이 켜고 끈다)
    srcs = [bid for bid, b in s["blocks"].items() if b.get("logic") == "source" and not LS._is_const0(s, bid)
            and (not ins.get(bid) or b.get("func") == "SIGNAL MONITOR")]
    keys = [f"row:{n}" for n in rows_in] + [f"block:{b}" for b in srcs]
    cases = [{}] + [{k: 1} for k in keys] + [{k: 0} for k in keys]
    if keys:
        allon = {k: 1 for k in keys}
        cases += [allon] + [{**allon, k: 0} for k in keys]
    ever1, short_all, floating_all = set(), set(), set()
    runs = errs = 0
    for f in cases:
        runs += 1
        try:
            r = sim.simulate_bundle(sheets, {s["page"]: f} if f else {}, None, s["page"], cache=cache, light=True)["focus"]
        except Exception:                                  # noqa: BLE001
            errs += 1
            continue
        short_all.update(r.get("short_gates") or [])
        for fr in r["frames"]:
            floating_all.update(fr.get("unread") or ())
            ever1.update(n for n, v in fr["values"].items() if v == 1 and n in s["nets"])
    # 2단계 — 무작위 조합 · 두 걸음 순서 (앞 걸음의 상태를 이어 준다): 메모리 · 타이머 · 되먹임 · 매크로 출력처럼 '하나씩 · 모두' 로는 안 서는 선
    rng = random.Random(93)
    seq1 = set()
    if keys and len(ever1) < len(s["nets"]):
        for _ in range(RANDOM_RUNS):
            a = {k: rng.randint(0, 1) for k in keys}
            b = {k: (v if rng.random() < 0.7 else 1 - v) for k, v in a.items()}
            st = None
            for f in (a, b, a):
                runs += 1
                try:
                    rr = sim.simulate_bundle(sheets, {s["page"]: f}, st, s["page"], cache=cache, light=True)
                except Exception:                          # noqa: BLE001
                    errs += 1
                    break
                st = rr.get("state")
                for fr in rr["focus"]["frames"]:
                    seq1.update(n for n, v in fr["values"].items() if v == 1 and n in s["nets"] and n not in ever1)
            if len(ever1) + len(seq1) >= len(s["nets"]):
                break
    dead = [n for n in s["nets"] if n not in ever1 and n not in seq1]
    cls = LS.classify_dead(s, dead, ever1 | seq1, short_all, floating_all)
    for n, v in cls.items():
        if v["kind"] in ("logic_dead", "timer", "memory_seq", "not_always1"):
            try:
                sc = sim.scenario(s, f"net:{n}", 1, sheets=sheets, cache=cache)
                runs += 1
                if sc.get("ok"):
                    v["kind"] = "reachable_direct" if [k for k in sc.get("direct_nets") or () if (sc.get("forces") or {}).get(k) == 1] else "reachable"
            except Exception:                              # noqa: BLE001
                pass
    status = {n: "on" for n in ever1}
    status.update({n: "reachable" for n in seq1})
    why = {}
    for n, v in cls.items():
        k = v["kind"] if v["kind"] != "upstream" else v["root_kind"]
        if v["kind"] == "upstream" and k in ("timer", "memory_seq", "not_always1", "logic_dead"):
            # 뿌리가 순서로 서는 선이면 그 뒤도 선다 — 뿌리의 풀이 결과를 따른다
            k = cls.get(v["root"], {}).get("kind", k)
        status[n] = KIND.get(k, "dead")
        if k == "unknown":                                   # 아날로그 값 선(상수 A · 연산 블록의 출력)은 0/1 로 서는 선이 아니다
            drv = drivers.get(v["root"], [])
            if drv and all(kind_ == "block" and (s["blocks"][x].get("aop") or s["blocks"][x].get("func") in ANALOG_FUNCS) for kind_, x, _ in drv):
                status[n] = "analog"
        why[n] = (v["kind"], v["root_kind"], v["root"])
    return status, why, runs, errs, len(keys)


def paint(pdf, s, status, out):
    import pymupdf
    pg = pdf[s["page"] - 1]
    sh = pg.new_shape()
    for kind in ("on", "reachable", "const0", "analog", "seq", "dead"):
        n = 0
        for nid, st in status.items():
            if st != kind:
                continue
            for sg in s["nets"][nid].get("segs") or []:
                sh.draw_line(pymupdf.Point(sg[0], sg[1]), pymupdf.Point(sg[2], sg[3]))
                n += 1
        if n:
            sh.finish(color=COL[kind], width=1.6 if kind != "dead" else 2.2, stroke_opacity=0.8, closePath=False)   # 닫지 않는다 — 이어진 토막의 끝과 처음을 잇는 헛선이 그려진다
    sh.commit()
    lg = s.get("logic") or [0, 0, pg.rect.width, pg.rect.height]
    pg.get_pixmap(dpi=120, clip=pymupdf.Rect(lg[0] - 250, lg[1] - 30, lg[2] + 250, lg[3] + 10)).save(out)


def main():
    import pymupdf
    job, out = sys.argv[1], Path(sys.argv[2])
    only = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else None
    out.mkdir(parents=True, exist_ok=True)
    res = api._result(job)
    sheets = api._all_sheets(res)
    typ = [s for s in res["sheets"] if re.fullmatch(r"\d{4}", s.get("sheet_no") or "") and s.get("rows") and (not only or s["sheet_no"] in only)]
    cache = {}
    rows, tot = [], collections.Counter()
    t0 = time.time()
    for s in typ:
        status, why, runs, errs, nkeys = sweep(s, sheets, cache)
        c = collections.Counter(status.values())
        pdf = pymupdf.open(str(store.root() / job / "source.pdf"))
        paint(pdf, s, status, str(out / f"{s['sheet_no']}.png"))
        pdf.close()
        dead = [{"net": n, "kind": why[n][0], "root_kind": why[n][1], "root": why[n][2], "at": LS._label(s, n),
                 "seg": (s["nets"][n].get("segs") or [[0, 0, 0, 0]])[0]} for n, st in status.items() if st in ("dead", "seq")]
        rows.append({"sheet": s["sheet_no"], "page": s["page"], "title": s.get("title") or "", "inputs": nkeys, "runs": runs, "errors": errs,
                     "nets": len(s["nets"]), **{k: c.get(k, 0) for k in COL}, "dead_list": dead})
        tot.update({k: c.get(k, 0) for k in COL})
        tot["nets"] += len(s["nets"]); tot["runs"] += runs; tot["errors"] += errs
        print(f"{s['sheet_no']} {(s.get('title') or '')[:34]:34} 입력 {nkeys:3} 실행 {runs:4} 선 {len(s['nets']):4} 켜짐 {c.get('on', 0):4} +순서 {c.get('reachable', 0):3} "
              f"0묶음 {c.get('const0', 0):3} 아날 {c.get('analog', 0):3} 순서못품 {c.get('seq', 0):3} 못켬 {c.get('dead', 0):3}", flush=True)
    work = tot["nets"] - tot["const0"] - tot["analog"]
    summ = {"sheets": len(typ), "seconds": round(time.time() - t0, 1), **dict(tot), "work": work,
            "pct_on": round(100 * (tot["on"] + tot["reachable"]) / max(1, work), 2)}
    (out / "summary.json").write_text(json.dumps({"summary": summ, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summ, ensure_ascii=False))


if __name__ == "__main__":
    main()
