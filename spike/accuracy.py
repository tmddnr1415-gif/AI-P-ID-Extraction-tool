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

축 (11회차부터 둘)
  · 전량  — 10회차까지의 정의 그대로.  삭제하지 않는다
  · SCT   — 우리 쪽 모수에서 SCOPE≠SCT 행(타사 공급분)을 뺀다.  정답지 쪽
            모수는 **건드리지 않는다** — 발주처가 세는 집합은 그대로다

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


# 축 — 우리 쪽 모수를 어떻게 자르는가.  **정답지 쪽은 어느 축에서도 같다**
# (취소선 제외 · P&ID No. 빈 행 제외 · 교집합 도면).  축이 바꾸는 것은
# `keep` 하나뿐이고, 그래서 두 축이 같은 `score()` 를 통과한다.
#
# 왜 축을 더하는가 (11회차): 10회차에 발주처 요구로 TW 15행과 벤더 공급분
# 204행을 리스트에 넣었는데, 발주처 CZE 는 그 219행을 계상하지 않는다
# (204행을 넣어 TP 594 → 595, FP 113 → 249).  그래서 전량 축의 정밀도는
# "우리가 얼마나 잘 읽었나"가 아니라 "발주처가 안 세는 것을 얼마나 넣었나"를
# 재게 된다.  **전량 축을 지우지 않고** SCT 축을 나란히 둔다 — 어느 쪽도
# 혼자서는 답이 아니기 때문이다.
AXES = (
    ("전량", lambda r: True),
    ("SCT", lambda r: strip(r.get("scope")) == "SCT"),
)


def score(rows, keep=lambda r: True):
    """한 축의 점수.  `keep` 만 축마다 다르고 나머지는 전부 같은 코드다."""
    rows = [r for r in rows if keep(r)]
    field = [(strip(r["drawing_no"]), strip(r["type"]))
             for r in rows if r["tab"] == "FIELD"]
    valve = {tab: [(strip(r["drawing_no"]), strip(r["valve_type"]))
                   for r in rows if r["tab"] == tab] for tab in ("MOV", "BFV")}
    out, fp, fn = [], collections.Counter(), collections.Counter()
    for kind in ("FIELD", "MOV", "BFV"):
        cl, _ = client_lists.load(kind)
        cl_keep = [r for r in cl if not r["strike"] and strip(r.get("pid"))]
        if kind == "FIELD":
            human = [(strip(r["pid"]), strip(r["type"])) for r in cl_keep]
            prog = field
        else:
            human = [(strip(r["pid"]), strip(r["actuator"])) for r in cl_keep]
            prog = valve[kind]
        out.append((kind, *counts(human, prog)))
        # FP/FN 내역 — 같은 모수 · 같은 칸에서 차이만 부호로 가른다.
        H, P = collections.Counter(human), collections.Counter(prog)
        both = {p for p, _ in H} & {p for p, _ in P}
        for k in {(p, i) for p, i in set(H) | set(P) if p in both}:
            d = P[k] - H[k]
            if d > 0:
                fp[f"{kind}:{k[1]}"] += d
            elif d < 0:
                fn[f"{kind}:{k[1]}"] += -d
    return out, fp, fn


def report(name, rows, keep):
    per, fp, fn = score(rows, keep)
    print(f"\n== 축 [{name}]  (우리 쪽 모수 {sum(1 for r in rows if keep(r))}행)")
    print(f"{'산출물':<8}{'도면':>5}{'사람':>6}{'프로그램':>8}{'TP':>6}"
          f"{'재현율':>9}{'정밀도':>9}")
    tot = [0, 0, 0]
    for kind, h, g, tp, pages in per:
        tot[0] += h; tot[1] += g; tot[2] += tp
        print(f"{kind:<8}{pages:>5}{h:>6}{g:>8}{tp:>6}"
              f"{100 * tp / max(h, 1):>8.1f}%{100 * tp / max(g, 1):>8.1f}%")
    print(f"{'전체':<8}{'':>5}{tot[0]:>6}{tot[1]:>8}{tot[2]:>6}"
          f"{100 * tot[2] / max(tot[0], 1):>8.1f}%"
          f"{100 * tot[2] / max(tot[1], 1):>8.1f}%")
    print(f"  FP {sum(fp.values()):>3}  {fp.most_common()}")
    print(f"  FN {sum(fn.values()):>3}  {fn.most_common()}")
    return tot, fp, fn


def main():
    if not (ROOT / "data" / "CZE_Field_Instrument.xlsx").exists():
        print("발주처 리스트가 없습니다 (data/*.xlsx 는 리포지터리에 없음). "
              "이 측정은 발주처 자료를 가진 기계에서만 됩니다.")
        return 1
    rows = our_rows()
    for name, keep in AXES:
        report(name, rows, keep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
