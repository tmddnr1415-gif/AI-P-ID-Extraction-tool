"""축4 (완전 추출) — **도면에 인쇄된 것을 얼마나 뽑았나** (51회차 신설).

왜 필요한가
    사용자가 목표를 바꿨다 — *"발주처 List 에 딱 맞출 필요는 없다. 참고만 하고,
    P&ID 에서 식별된다면 모두 식별하고 추출한다."*  축1·축2 는 발주처 정답지로만
    재므로 이 목표를 못 잰다.  축3(식별률)은 여섯 지표의 평균이라 "얼마나
    뽑았나" 를 직접 말하지 않는다.

★ 분모를 어떻게 정하는가 — 이 축의 전부다.  한 번 정하면 바꾸지 않는다 (§8).

    분모 = ㉮ 버블이 선 계기 태그 + ㉯ 그 도면이 그린 밸브 몸체
    분자 = 그중 행이 된 것

    ㉮ **버블이 선 계기 태그**
        행이 된 계기  +  `unjudged` 중 "사전에 없음" 항목.
        뒤엣것은 `detect()` 가 `len(hit) == 1` 로 **버블 검증을 이미 통과시킨**
        낱말이다 — 그 도면의 범례가 정의한 계기 심볼 안에 인쇄된 글자이므로
        "그 도면이 계기로 인쇄했다" 는 것이 도면 자신의 증거로 선다.

    ㉯ **밸브 몸체**
        행이 된 밸브  +  `unjudged` 중 `VALVE_BODY`(= `unclassified_bodies` —
        배관 끝막대 둘을 갖췄는데 몸체 어휘에 없는 중공 도형).

    ★ 분모에 **넣지 않는** 것 — 버블이 0개이거나 2개 이상인 낱말
        `bubbles_matched == 0` 은 버블 밖 낱말일 수 있고(실측: TC2 의
        `CHEMICAL SUMP PIT` 47건이 그렇다), `2 이상`은 버블이 겹쳐 어느 것의
        글자인지 도면이 갈라 주지 않는다.  넣으면 계기가 아닌 낱말이 분모를
        오염시킨다.
        ⚠ **이 결정의 한계를 그대로 적는다** — 버블을 *검출기가 못 세운* 경우도
        여기 들어가므로(40회차 UAD 파선 버블 48행이 그랬다) **축4 는 그 실패를
        못 본다.**  그래서 따로 세어 `밖` 으로 함께 보고한다.

    ⚠ 묶인 행(LS 다중 신호 34묶음 102버블 → 34행)은 분자·분모에서 **같이**
    빠지므로 왜곡되지 않는다 — 묶인 버블은 `unjudged` 에 없다.

    python3 spike/axis4.py                       # 저장된 결과로
    python3 spike/axis4.py out/regression_3p/AL_NOUF1.json
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

STORED = [("AL NOUF1", "out/round20/run_base.json"),
          ("SADARA", "out/round20/run_sadara.json"),
          ("TC2", "out/round47/TC2_after.json"),
          ("UAD", "out/round45/UAD_before.json")]
VALVE_TABS = ("MOV", "BFV", "PNEUMATIC")


def score(res: dict) -> dict:
    rows = res.get("rows", [])
    valve_rows = sum(1 for r in rows if r.get("valve_type"))
    inst_rows = len(rows) - valve_rows

    miss_inst = miss_valve = outside = 0
    for u in res.get("unjudged_symbols", []):
        kind = u.get("kind")
        if kind == "VALVE_BODY":
            miss_valve += 1
        elif kind == "INSTRUMENT_TAG":
            if "사전에 없" in (u.get("why") or ""):
                miss_inst += 1
            else:
                outside += 1

    den_i, den_v = inst_rows + miss_inst, valve_rows + miss_valve
    den = den_i + den_v
    num = inst_rows + valve_rows
    return {"계기_분자": inst_rows, "계기_분모": den_i,
            "밸브_분자": valve_rows, "밸브_분모": den_v,
            "분자": num, "분모": den,
            "축4": round(100.0 * num / den, 1) if den else 0.0,
            "밖": outside}


def main() -> int:
    args = sys.argv[1:]
    items = ([(pathlib.Path(a).stem, a) for a in args] if args else
             [(n, p) for n, p in STORED])
    print("%-10s %7s %7s %7s  %7s %7s  %6s   %s"
          % ("프로젝트", "분자", "분모", "축4", "계기", "밸브", "밖", ""))
    out = {}
    for name, p in items:
        f = ROOT / p
        if not f.exists():
            print("%-10s  (저장된 결과 없음: %s)" % (name, p))
            continue
        res = json.loads(f.read_text())
        res = res.get("result", res)
        s = score(res)
        out[name] = s
        print("%-10s %7d %7d %6.1f%%  %3d/%-3d %3d/%-3d  %6d"
              % (name, s["분자"], s["분모"], s["축4"],
                 s["계기_분자"], s["계기_분모"], s["밸브_분자"], s["밸브_분모"], s["밖"]))
    print("\n분모 = 버블이 선 계기 태그 + 그 도면이 그린 밸브 몸체 · "
          "`밖` = 버블이 0개이거나 2개 이상인 낱말 (분모에 안 넣음)")
    (ROOT / "out" / "round51").mkdir(parents=True, exist_ok=True)
    (ROOT / "out" / "round51" / "axis4.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
