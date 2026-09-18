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

    ㉯ **그 도면이 버블에 인쇄한 밸브 태그** (`result["valve_tags"]`)
        `detect()` 가 밸브 태그 낱말도 버블로 검증해 `category="VALVE"` 검출을
        만들어 왔는데 파이프라인이 버리고 있었다 (51회차에 기록하게 했다).
        버블은 그 도면의 범례가 정의한 심볼이므로 *"여기 밸브가 있다"* 는
        **도면 자신의 선언**이다.
        분자 = 그 태그를 밸브 행이 실제로 가져간 것 (`evidence["tag"]`).

    ★ `unclassified_bodies`(미판정 `VALVE_BODY`)는 **분모가 아니다.**
        첫 정의에서 분모로 삼았다가 **렌더로 뒤집었다** — AL NOUF1 82건의
        표본을 열어 보니 `p6 [1279.0, 265.0, 1284.7, 289.9]` 은 `HP TURBINE`
        기기 심볼의 **노즐(플랜지) 사각형**이었다.  "배관 끝막대 둘을 갖춘
        중공 도형" 은 기기 노즐·플랜지·스펙 브레이크를 함께 담는 진단용
        바구니이고, 분모로 삼으면 *"UAD 가 밸브 144개를 내야 한다"* 는 거짓
        목표가 선다 (실제 밸브 행은 11).  따로 세어 보고만 한다.

    ★ 태그 없이 기하로만 선 밸브 행은 **분자·분모 어디에도 넣지 않는다.**
        대응하는 분모가 없다 (AL NOUF1 152행 중 68행).  따로 적는다 — 이
        축이 못 보는 몫이고, 그 사실을 감추지 않는다.

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

import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

STORED = [("AL NOUF1", "out/round20/run_base.json"),
          ("SADARA", "out/round20/run_sadara.json"),
          ("TC2", "out/round47/TC2_after.json"),
          ("UAD", "out/round45/UAD_before.json")]
VALVE_TABS = ("MOV", "BFV", "PNEUMATIC")


def is_valve_row(r) -> bool:
    """밸브 경로가 낸 행인가.

    ⚠ 53회차에 이 판별을 고쳤다 — **분모는 그대로다** (§8).  이전에는
    `valve_type`(액추에이터)이 차 있는가로 갈랐는데, 53회차부터 *도면이 이름은
    붙였지만 액추에이터를 안 그린* 밸브가 행이 되고 그 칸이 **비어 있다**.
    그대로 두면 그 행들이 계기로 세어져 채점기가 엔진이 옳게 한 일을 틀렸다고
    센다 (23회차 [2] 와 같은 실패).

    밸브 행은 `evidence["body"]` 를 갖는다 — 값이 빈 문자열이어도 **열쇠가
    있는 것**이 밸브 경로를 지났다는 표시다.  계기 행에는 그 열쇠가 없다.
    """
    ev = r.get("evidence") or {}
    return "body" in ev or bool(r.get("valve_type"))


def score(res: dict) -> dict:
    rows = res.get("rows", [])
    valve_rows = sum(1 for r in rows if is_valve_row(r))
    inst_rows = len(rows) - valve_rows

    miss_inst = outside = bodies = 0
    for u in res.get("unjudged_symbols", []):
        kind = u.get("kind")
        if kind == "VALVE_BODY":
            bodies += 1                      # ★ 분모가 아니다 — 세기만 한다
        elif kind == "INSTRUMENT_TAG":
            if "사전에 없" in (u.get("why") or ""):
                miss_inst += 1
            else:
                outside += 1

    den_i = inst_rows + miss_inst
    tags = res.get("valve_tags")
    tagged = sum(1 for r in rows
                 if is_valve_row(r) and ((r.get("evidence") or {}).get("tag")))
    out = {"계기_분자": inst_rows, "계기_분모": den_i,
           "축4_계기": round(100.0 * inst_rows / den_i, 1) if den_i else 0.0,
           "밸브행": valve_rows, "밸브행_태그있음": tagged,
           "밸브행_태그없음": valve_rows - tagged,
           "미판정몸체(분모아님)": bodies, "버블밖낱말(분모아님)": outside}
    if tags is None:                         # 51회차 이전 결과에는 이 칸이 없다
        out["밸브_분모"] = None
        out["축4_밸브"] = None
        out["축4"] = None
        return out
    den_v = len(tags)
    # ★ 분모에서 아무것도 빼지 않는다.  `PSV`·`PRV`·`BPRV`(자력식 안전밸브)는
    # 발주처 산출물 범위 밖이지만(23회차) **도면은 그것을 인쇄했다** — 빼면
    # 분모를 손봐 수치를 좋게 만드는 것이다 (§2.2).  대신 태그별로 갈라 적어
    # "안 뽑힌 것이 왜 안 뽑혔나" 를 보이게 한다.
    per = {}
    claimed = collections.Counter(
        str(((r.get("evidence") or {}).get("tag") or "")).upper()
        for r in rows if is_valve_row(r))
    for t, n in collections.Counter(x.get("tag") for x in tags).items():
        per[t] = [claimed.get(t, 0), n]
    out["밸브_태그별"] = dict(sorted(per.items(), key=lambda kv: -kv[1][1]))
    out["밸브_분모"] = den_v
    out["축4_밸브"] = round(100.0 * tagged / den_v, 1) if den_v else 0.0
    num, den = inst_rows + tagged, den_i + den_v
    out["분자"], out["분모"] = num, den
    out["축4"] = round(100.0 * num / den, 1) if den else 0.0
    return out


def main() -> int:
    args = sys.argv[1:]
    items = ([(pathlib.Path(a).stem, a) for a in args] if args else
             [(n, p) for n, p in STORED])
    print("%-10s %16s %16s %8s   %s"
          % ("프로젝트", "축4-계기", "축4-밸브태그", "축4", "태그없는 밸브행 · 미판정몸체"))
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
        v = ("%4d/%-4d %5.1f%%" % (s["밸브행_태그있음"], s["밸브_분모"], s["축4_밸브"])
             if s["밸브_분모"] is not None else "        (미측정)")
        tot = ("%6.1f%%" % s["축4"]) if s["축4"] is not None else "     —"
        print("%-10s %5d/%-5d %5.1f%% %s %s   %d · %d"
              % (name, s["계기_분자"], s["계기_분모"], s["축4_계기"], v, tot,
                 s["밸브행_태그없음"], s["미판정몸체(분모아님)"]))
    for name, s2 in out.items():
        if s2.get("밸브_태그별"):
            print("\n  %s 밸브 태그별 (가져간 행 / 버블에 인쇄된 태그)" % name)
            print("   " + "  ".join("%s %d/%d" % (t, v[0], v[1])
                                    for t, v in s2["밸브_태그별"].items()))
    print("\n계기 분모 = 버블이 선 계기 태그 · 밸브 분모 = 그 도면이 버블에 인쇄한 밸브 태그")
    print("★ 미판정 몸체는 분모가 아니다 (렌더 확인: 기기 노즐) · "
          "태그 없는 밸브 행은 대응 분모가 없어 축 밖이다")
    (ROOT / "out" / "round51").mkdir(parents=True, exist_ok=True)
    (ROOT / "out" / "round51" / "axis4.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
