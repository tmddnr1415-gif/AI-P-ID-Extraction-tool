"""정확도 회귀 — 재현율 · 정밀도를 (도면 · 항목) 개수로 잰다.

회귀 블록에 숫자를 적어 두는 것만으로는 UI 를 고치다 파이프라인이 흔들려도
알아차릴 수 없다.  그래서 그 숫자를 만드는 절차를 여기 둔다.

모수
  · 교집합 도면만          — 양쪽에 다 있는 도면
  · 취소선 행 제외          — 발주처가 지운 행
  · P&ID No. 가 빈 행 제외  — 어느 도면에도 속하지 않는다 (SPARE 등)
  · 항목: FIELD 는 정답지 TYPE 열 그대로, MOV·BFV 는 액추에이터 계층

1:1 대응은 성립하지 않는다 (발주처 리스트에 좌표가 없고 우리 행에 발주처 NO 가
없다).  그래서 일치 수는 칸마다 min(사람, 프로그램) 을 더한 값이고, 어느 행이
틀렸다고는 말하지 않는다.

    python3 spike/accuracy.py                     # 기본: 파이프라인을 직접 돌린다
    python3 spike/accuracy.py run.json            # 이미 있는 결과 json 으로
"""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))
sys.path.insert(0, str(ROOT / "spike"))
import client_lists


def our_rows():
    if len(sys.argv) > 1:
        return json.load(open(sys.argv[1]))["rows"]
    from app import pipeline
    return pipeline.analyse(ROOT / "data" / "pid_total.pdf")["rows"]


def strip(v):
    return v.strip() if isinstance(v, str) else v


def counts(human_pairs, prog_pairs):
    H, P = collections.Counter(human_pairs), collections.Counter(prog_pairs)
    both = {p for p, _ in H} & {p for p, _ in P}
    keys = {(p, i) for p, i in set(H) | set(P) if p in both}
    h = sum(H[k] for k in keys)
    g = sum(P[k] for k in keys)
    tp = sum(min(H[k], P[k]) for k in keys)
    return h, g, tp, len(both)


def main():
    if not (ROOT / "data" / "CZE_Field_Instrument.xlsx").exists():
        print("발주처 리스트가 없습니다 (data/*.xlsx 는 리포지터리에 없음). "
              "이 측정은 발주처 자료를 가진 기계에서만 됩니다.")
        return 1
    rows = our_rows()
    field = [(strip(r["drawing_no"]), strip(r["type"]))
             for r in rows if r["tab"] == "FIELD"]
    valve = {tab: [(strip(r["drawing_no"]), strip(r["valve_type"]))
                   for r in rows if r["tab"] == tab] for tab in ("MOV", "BFV")}

    tot = [0, 0, 0]
    print(f"{'산출물':<8}{'도면':>5}{'사람':>6}{'프로그램':>8}{'TP':>6}"
          f"{'재현율':>9}{'정밀도':>9}")
    for kind in ("FIELD", "MOV", "BFV"):
        cl, _ = client_lists.load(kind)
        keep = [r for r in cl if not r["strike"] and strip(r.get("pid"))]
        if kind == "FIELD":
            human = [(strip(r["pid"]), strip(r["type"])) for r in keep]
            prog = field
        else:
            human = [(strip(r["pid"]), strip(r["actuator"])) for r in keep]
            prog = valve[kind]
        h, g, tp, pages = counts(human, prog)
        tot[0] += h; tot[1] += g; tot[2] += tp
        print(f"{kind:<8}{pages:>5}{h:>6}{g:>8}{tp:>6}"
              f"{100 * tp / max(h, 1):>8.1f}%{100 * tp / max(g, 1):>8.1f}%")
    print(f"{'전체':<8}{'':>5}{tot[0]:>6}{tot[1]:>8}{tot[2]:>6}"
          f"{100 * tot[2] / tot[0]:>8.1f}%{100 * tot[2] / tot[1]:>8.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
